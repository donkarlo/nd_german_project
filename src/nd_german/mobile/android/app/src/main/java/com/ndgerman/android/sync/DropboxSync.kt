package com.ndgerman.android.sync

import android.content.Context
import com.dropbox.core.DbxRequestConfig
import com.dropbox.core.android.Auth
import com.dropbox.core.oauth.DbxCredential
import com.dropbox.core.v2.DbxClientV2
import com.dropbox.core.v2.files.FileMetadata
import com.dropbox.core.v2.files.WriteMode
import com.ndgerman.android.BuildConfig
import com.ndgerman.android.data.DictionaryDatabase
import com.ndgerman.android.data.SyncState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream

private const val REMOTE_DATABASE = "/repo/data/nd_german_project/dictionary.sqlite3"

class DropboxCredentialStore(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("nd_german_dropbox_auth", Context.MODE_PRIVATE)
    fun credential(): DbxCredential? {
        val raw = prefs.getString("credential", null) ?: return null
        return runCatching { DbxCredential.Reader.readFully(raw) }.getOrElse {
            prefs.edit().remove("credential").apply(); null
        }
    }
    fun store(value: DbxCredential) = prefs.edit().putString("credential", DbxCredential.Writer.writeToString(value)).apply()
    fun clear() = prefs.edit().clear().apply()
}

class DropboxGateway(private val context: Context) {
    private val store = DropboxCredentialStore(context)
    private var awaitingAuth = false
    @Volatile private var cachedClient: DbxClientV2? = null

    fun configured() = BuildConfig.DROPBOX_APP_KEY.isNotBlank() && BuildConfig.DROPBOX_APP_KEY != "missing_nd_german_dropbox_app_key"
    fun authenticated() = store.credential() != null

    fun startAuthentication() {
        check(configured()) { "Set ND_GERMAN_DROPBOX_APP_KEY in local.properties first." }
        val config = DbxRequestConfig("nd-german-android/0.1")
        Auth.startOAuth2PKCE(
            context,
            BuildConfig.DROPBOX_APP_KEY,
            config,
            listOf("account_info.read", "files.metadata.read", "files.content.read", "files.content.write"),
        )
        awaitingAuth = true
    }

    fun finishAuthenticationIfAvailable(): Boolean {
        if (!awaitingAuth) return false
        val credential = Auth.getDbxCredential()
        awaitingAuth = false
        if (credential != null) {
            store.store(credential)
            cachedClient = null
            return true
        }
        return false
    }

    fun signOut() {
        runCatching { if (authenticated()) client().auth().tokenRevoke() }
        store.clear(); cachedClient = null; awaitingAuth = false
    }

    private fun client(): DbxClientV2 {
        cachedClient?.let { return it }
        return synchronized(this) {
            cachedClient ?: run {
                val credential = store.credential() ?: error("Dropbox is not connected")
                DbxClientV2(DbxRequestConfig("nd-german-android/0.1"), credential).also { cachedClient = it }
            }
        }
    }

    fun remoteMetadata(): FileMetadata = client().files().getMetadata(REMOTE_DATABASE) as FileMetadata

    fun downloadDatabase(destination: File): FileMetadata {
        destination.parentFile?.mkdirs()
        // Verify that the revision did not change while downloading.
        repeat(2) { attempt ->
            val before = remoteMetadata()
            FileOutputStream(destination).use { out -> client().files().download(REMOTE_DATABASE).download(out) }
            val after = remoteMetadata()
            if (before.rev == after.rev) return after
            if (attempt == 1) error("The desktop database changed while Android was downloading it. Try Pull again.")
        }
        error("Could not obtain a stable remote dictionary revision")
    }

    fun uploadDatabaseRevisionSafe(source: File, expectedRevision: String): FileMetadata =
        source.inputStream().use { input ->
            client().files().uploadBuilder(REMOTE_DATABASE)
                .withMode(WriteMode.update(expectedRevision))
                .uploadAndFinish(input)
        }
}

class DictionarySyncManager(
    context: Context,
    private val database: DictionaryDatabase,
    val gateway: DropboxGateway = DropboxGateway(context),
) {
    private val prefs = context.applicationContext.getSharedPreferences("nd_german_sync", Context.MODE_PRIVATE)

    fun initialState(): SyncState = SyncState(
        connected = gateway.authenticated(),
        pendingLocalChanges = prefs.getBoolean("pending", false),
        lastRemoteRevision = prefs.getString("rev", null),
        message = if (gateway.authenticated()) "Dropbox connected" else "Offline database ready",
    )

    suspend fun pull(discardLocalChanges: Boolean = false): SyncState = withContext(Dispatchers.IO) {
        check(gateway.authenticated()) { "Connect Dropbox first." }
        val pending = prefs.getBoolean("pending", false)
        if (pending && !discardLocalChanges) error("Local edits are pending. Push them or explicitly discard them before Pull.")
        val temp = File.createTempFile("nd-german-pull-", ".sqlite3", database.databaseFile.parentFile)
        try {
            val metadata = gateway.downloadDatabase(temp)
            database.replaceFrom(temp)
            prefs.edit().putString("rev", metadata.rev).putBoolean("pending", false).apply()
            SyncState(true, false, false, metadata.rev, "Pulled desktop dictionary · rev ${metadata.rev.take(8)}")
        } finally {
            temp.delete()
        }
    }

    suspend fun markLocalChangeAndPushIfPossible(): SyncState = withContext(Dispatchers.IO) {
        prefs.edit().putBoolean("pending", true).apply()
        if (!gateway.authenticated()) return@withContext initialState().copy(message = "Saved locally · Dropbox not connected")
        val expected = prefs.getString("rev", null)
            ?: return@withContext initialState().copy(message = "Saved locally · Pull once before first Dropbox push")
        push(expected)
    }

    suspend fun pushCurrent(): SyncState = withContext(Dispatchers.IO) {
        check(gateway.authenticated()) { "Connect Dropbox first." }
        val expected = prefs.getString("rev", null) ?: error("Pull the Dropbox database once before the first Push.")
        push(expected)
    }

    private suspend fun push(expectedRevision: String): SyncState {
        val snapshot = File.createTempFile("nd-german-push-", ".sqlite3", database.databaseFile.parentFile)
        return try {
            database.snapshotTo(snapshot)
            val metadata = gateway.uploadDatabaseRevisionSafe(snapshot, expectedRevision)
            prefs.edit().putString("rev", metadata.rev).putBoolean("pending", false).apply()
            SyncState(true, false, false, metadata.rev, "Synced Android edit · rev ${metadata.rev.take(8)}")
        } catch (t: Throwable) {
            prefs.edit().putBoolean("pending", true).apply()
            throw IllegalStateException(
                "Dropbox did not accept this revision. The desktop database may have changed. Your Android edit is safe locally; Pull/resolve before retrying Push.",
                t,
            )
        } finally {
            snapshot.delete()
        }
    }

    fun clearRevisionAfterSignOut(): SyncState {
        gateway.signOut()
        return initialState().copy(connected = false, message = "Dropbox disconnected")
    }
}
