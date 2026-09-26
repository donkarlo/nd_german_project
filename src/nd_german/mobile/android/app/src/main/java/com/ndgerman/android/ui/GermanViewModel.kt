package com.ndgerman.android.ui

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ndgerman.android.GermanApplication
import com.ndgerman.android.data.DictionaryEntry
import com.ndgerman.android.data.SyncState
import com.ndgerman.android.grammar.AdjectiveRow
import com.ndgerman.android.grammar.ConjugationResult
import com.ndgerman.android.grammar.NounResult
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

private const val AUTO_SYNC_INTERVAL_MS = 10_000L

data class GermanUiState(
    val ready: Boolean = false,
    val busy: Boolean = false,
    val databaseCount: Int = 0,
    val query: String = "",
    val results: List<DictionaryEntry> = emptyList(),
    val searchHistory: List<String> = emptyList(),
    val status: String = "Loading dictionary…",
    val error: String? = null,
    val sync: SyncState = SyncState(),
    val verbQuery: String = "",
    val conjugation: ConjugationResult? = null,
    val conjugationError: String? = null,
    val nounQuery: String = "",
    val nounResult: NounResult? = null,
)

class GermanViewModel(private val app: GermanApplication) : ViewModel() {
    private val database = app.database
    private val grammar = app.grammar
    private val syncManager = app.syncManager
    private val prefs = app.getSharedPreferences("nd_german_ui", Context.MODE_PRIVATE)

    private val _state = MutableStateFlow(
        GermanUiState(
            sync = syncManager.initialState(),
            searchHistory = prefs.getStringSet("history", emptySet()).orEmpty().toList(),
        )
    )
    val state: StateFlow<GermanUiState> = _state.asStateFlow()

    private var searchJob: Job? = null
    private var autoSyncJob: Job? = null

    val dropboxConfigured: Boolean get() = syncManager.gateway.configured()

    init {
        viewModelScope.launch {
            runCatching {
                database.ensureSeeded()

                val sync = if (syncManager.initialState().connected) {
                    runCatching { syncManager.syncAutomatically() }
                        .getOrElse {
                            syncManager.initialState().copy(
                                message = "Dropbox connected · automatic sync will retry",
                            )
                        }
                } else {
                    syncManager.initialState()
                }

                refreshDictionaryState(sync = sync)
                startAutoSync()
            }.onFailure(::showError)
        }
    }

    private fun startAutoSync() {
        if (autoSyncJob?.isActive == true) return

        autoSyncJob = viewModelScope.launch {
            while (isActive) {
                delay(AUTO_SYNC_INTERVAL_MS)
                if (!_state.value.ready || !_state.value.sync.connected || _state.value.busy) continue
                automaticSync(showTransientErrors = false)
            }
        }
    }

    private suspend fun refreshDictionaryState(
        sync: SyncState = _state.value.sync,
        statusOverride: String? = null,
    ) {
        val count = database.count()
        val results = database.search(_state.value.query)
        _state.update {
            it.copy(
                ready = true,
                databaseCount = count,
                results = results,
                status = statusOverride
                    ?: if (it.query.isBlank()) "$count dictionary entries" else "${results.size} result(s)",
                sync = sync,
            )
        }
    }

    private suspend fun automaticSync(showTransientErrors: Boolean): SyncState {
        if (!syncManager.initialState().connected) {
            val offline = syncManager.initialState()
            _state.update { it.copy(sync = offline) }
            return offline
        }

        _state.update { it.copy(sync = it.sync.copy(busy = true)) }

        return runCatching { syncManager.syncAutomatically() }
            .onSuccess { sync ->
                refreshDictionaryState(sync = sync)
            }
            .getOrElse { t ->
                val fallback = syncManager.initialState().copy(
                    busy = false,
                    message = "Dropbox sync retry pending",
                )
                _state.update { it.copy(sync = fallback) }
                if (showTransientErrors) showError(t)
                fallback
            }
    }

    fun setQuery(value: String) {
        _state.update { it.copy(query = value, error = null) }
        searchJob?.cancel()
        searchJob = viewModelScope.launch {
            delay(80)
            performSearch(recordHistory = false)
        }
    }

    fun chooseHistory(value: String) {
        _state.update { it.copy(query = value) }
        performSearch(recordHistory = true)
    }

    fun performSearch(recordHistory: Boolean = true) {
        searchJob?.cancel()
        viewModelScope.launch {
            val query = _state.value.query.trim()
            runCatching { database.search(query) }
                .onSuccess { results ->
                    if (recordHistory && query.isNotBlank()) addHistory(query)
                    _state.update {
                        it.copy(
                            results = results,
                            status = if (query.isBlank()) {
                                "${it.databaseCount} dictionary entries"
                            } else {
                                "${results.size} result(s)"
                            },
                            error = null,
                        )
                    }
                }
                .onFailure(::showError)
        }
    }

    private fun addHistory(query: String) {
        val updated =
            (listOf(query) + _state.value.searchHistory.filterNot { it.equals(query, true) })
                .take(10)
        prefs.edit().putStringSet("history", LinkedHashSet(updated)).apply()
        _state.update { it.copy(searchHistory = updated) }
    }

    fun saveEntry(index: Int?, raw: String, onDone: (() -> Unit)? = null) {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }

            runCatching {
                // Capture the entry the user actually edited before a possible remote pull.
                // If Ubuntu changed indexes, resolve the same lexeme again after the pull
                // instead of blindly writing to the old numeric index.
                val original = index?.let { database.entry(it) }
                var targetIndex = index

                if (syncManager.initialState().connected &&
                    !syncManager.initialState().pendingLocalChanges
                ) {
                    syncManager.syncAutomatically()

                    if (original != null) {
                        val latest = database.findExactLexeme(original.headword, original.role)
                            ?: error("This entry was removed or renamed on Ubuntu while you were editing it.")
                        check(latest.raw == original.raw) {
                            "This entry changed on Ubuntu while you were editing it. Your Android edit was not applied, so neither side was overwritten."
                        }
                        targetIndex = latest.index
                    }
                }

                if (targetIndex == null) database.add(raw) else database.replace(targetIndex, raw)

                val sync = syncManager.markLocalChangeAndPushIfPossible()
                val count = database.count()
                val results = database.search(_state.value.query)
                Triple(sync, count, results)
            }.onSuccess { (sync, count, results) ->
                _state.update {
                    it.copy(
                        busy = false,
                        sync = sync,
                        databaseCount = count,
                        results = results,
                        status = "$count dictionary entries",
                    )
                }
                onDone?.invoke()
            }.onFailure { t ->
                _state.update { it.copy(busy = false, sync = syncManager.initialState()) }
                showError(t)
            }
        }
    }

    fun deleteEntry(index: Int, onDone: (() -> Unit)? = null) {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }

            runCatching {
                val original = database.entry(index)
                    ?: error("The selected dictionary entry no longer exists.")
                var targetIndex: Int? = index

                if (syncManager.initialState().connected &&
                    !syncManager.initialState().pendingLocalChanges
                ) {
                    syncManager.syncAutomatically()

                    val latest = database.findExactLexeme(original.headword, original.role)
                    if (latest == null) {
                        // Ubuntu already deleted the same entry. Nothing else to delete.
                        targetIndex = null
                    } else {
                        check(latest.raw == original.raw) {
                            "This entry changed on Ubuntu while you were deleting it. The Ubuntu change was kept and Android did not delete it."
                        }
                        targetIndex = latest.index
                    }
                }

                if (targetIndex != null) database.delete(targetIndex)

                val sync = if (targetIndex != null) {
                    syncManager.markLocalChangeAndPushIfPossible()
                } else {
                    syncManager.syncAutomatically()
                }
                val count = database.count()
                val results = database.search(_state.value.query)
                Triple(sync, count, results)
            }.onSuccess { (sync, count, results) ->
                _state.update {
                    it.copy(
                        busy = false,
                        sync = sync,
                        databaseCount = count,
                        results = results,
                        status = "Deleted · $count entries",
                    )
                }
                onDone?.invoke()
            }.onFailure { t ->
                _state.update { it.copy(busy = false, sync = syncManager.initialState()) }
                showError(t)
            }
        }
    }

    fun startDropboxAuthentication() {
        runCatching { syncManager.gateway.startAuthentication() }.onFailure(::showError)
    }

    fun finishDropboxAuthentication() {
        val finished =
            runCatching { syncManager.gateway.finishAuthenticationIfAvailable() }.getOrDefault(false)
        if (!finished) return

        viewModelScope.launch {
            _state.update {
                it.copy(
                    sync = syncManager.initialState().copy(
                        connected = true,
                        busy = true,
                        message = "Dropbox connected · starting automatic sync…",
                    )
                )
            }

            automaticSync(showTransientErrors = true)
            startAutoSync()
        }
    }

    fun pullRemote(discardLocalChanges: Boolean) {
        viewModelScope.launch {
            _state.update { it.copy(sync = it.sync.copy(busy = true), error = null) }

            runCatching {
                val sync = syncManager.pull(discardLocalChanges)
                val count = database.count()
                val results = database.search(_state.value.query)
                Triple(sync, count, results)
            }.onSuccess { (sync, count, results) ->
                _state.update {
                    it.copy(
                        sync = sync,
                        databaseCount = count,
                        results = results,
                        status = "$count dictionary entries",
                    )
                }
            }.onFailure { t ->
                _state.update { it.copy(sync = it.sync.copy(busy = false)) }
                showError(t)
            }
        }
    }

    fun pushRemote() {
        viewModelScope.launch {
            _state.update { it.copy(sync = it.sync.copy(busy = true), error = null) }

            runCatching { syncManager.pushCurrent() }
                .onSuccess { sync -> _state.update { it.copy(sync = sync) } }
                .onFailure { t ->
                    _state.update {
                        it.copy(
                            sync = syncManager.initialState().copy(
                                busy = false,
                                pendingLocalChanges = true,
                            )
                        )
                    }
                    showError(t)
                }
        }
    }

    fun disconnectDropbox() {
        _state.update { it.copy(sync = syncManager.clearRevisionAfterSignOut()) }
    }

    fun setVerbQuery(value: String) {
        _state.update { it.copy(verbQuery = value, conjugationError = null) }
    }

    fun conjugate(value: String = _state.value.verbQuery) {
        val q = value.trim()
        _state.update { it.copy(verbQuery = q) }

        if (q.isBlank()) {
            _state.update { it.copy(conjugation = null, conjugationError = null) }
            return
        }

        runCatching { grammar.conjugate(q) }
            .onSuccess { result ->
                _state.update { it.copy(conjugation = result, conjugationError = null) }
            }
            .onFailure { t ->
                _state.update {
                    it.copy(
                        conjugation = null,
                        conjugationError = t.message ?: "Conjugation failed",
                    )
                }
            }
    }

    fun openVerbFromDictionary(word: String) {
        setVerbQuery(word.removePrefix("sich "))
        conjugate(word)
    }

    fun adjectiveRows(
        word: String,
        determiner: String,
        type: String,
    ): List<AdjectiveRow> = grammar.adjectiveRows(word, determiner, type)

    fun detectedAdjectiveType(determiner: String): String? =
        grammar.detectAdjectiveType(determiner)

    fun setNounQuery(value: String) {
        _state.update { it.copy(nounQuery = value) }
    }

    fun declineNoun(value: String = _state.value.nounQuery) {
        val q = value.trim()
        _state.update { it.copy(nounQuery = q) }

        if (q.isBlank()) {
            _state.update { it.copy(nounResult = null) }
            return
        }

        viewModelScope.launch {
            runCatching {
                val entry = database.findExactLexeme(q, "noun")
                grammar.declineNoun(q, entry)
            }.onSuccess { result ->
                _state.update { it.copy(nounResult = result, error = null) }
            }.onFailure(::showError)
        }
    }

    fun clearError() = _state.update { it.copy(error = null) }

    private fun showError(t: Throwable) =
        _state.update {
            it.copy(
                error = t.message ?: t::class.java.simpleName,
                status = "Error",
            )
        }

    class Factory(private val app: GermanApplication) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            GermanViewModel(app) as T
    }
}
