package com.ndgerman.android

import android.app.Application
import com.ndgerman.android.data.DictionaryDatabase
import com.ndgerman.android.grammar.GermanGrammar
import com.ndgerman.android.sync.DictionarySyncManager

class GermanApplication : Application() {
    val database by lazy { DictionaryDatabase(this) }
    val grammar by lazy { GermanGrammar(this) }
    val syncManager by lazy { DictionarySyncManager(this, database) }
}
