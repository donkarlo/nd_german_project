package com.ndgerman.android.sync

import android.content.Context
import com.ndgerman.android.data.DictionaryDatabase
import com.ndgerman.android.data.SyncState

class DictionarySyncManager(
    context: Context,
    private val database: DictionaryDatabase,
) {
    fun configured() = false
    fun startAuthentication() = Unit
    fun finishAuthenticationIfAvailable() = false

    fun initialState() =
        SyncState(
            connected = false,
            busy = false,
            pendingLocalChanges = false,
            lastRemoteRevision = null,
            message = "Local database",
        )

    suspend fun syncAutomatically(): SyncState = initialState()

    suspend fun pull(discardLocalChanges: Boolean = false): SyncState = initialState()

    suspend fun markLocalChangeAndPushIfPossible(): SyncState =
        initialState().copy(message = "Saved locally")

    suspend fun pushCurrent(): SyncState = initialState()

    fun clearRevisionAfterSignOut(): SyncState = initialState()
}
