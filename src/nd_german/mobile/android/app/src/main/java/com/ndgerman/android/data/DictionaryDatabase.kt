package com.ndgerman.android.data

import android.content.Context
import androidx.sqlite.SQLiteConnection
import androidx.sqlite.SQLiteStatement
import androidx.sqlite.execSQL
import androidx.sqlite.driver.bundled.BundledSQLiteDriver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import java.io.File
import kotlin.math.max

class DictionaryDatabase(private val context: Context) {
    private val driver = BundledSQLiteDriver()
    private val mutex = Mutex()
    val databaseFile: File = File(context.filesDir, "dictionary.sqlite3")

    suspend fun ensureSeeded() = withContext(Dispatchers.IO) {
        mutex.withLock {
            if (!databaseFile.isFile || databaseFile.length() < 4096L) {
                val temp = File(context.cacheDir, "dictionary.seed.tmp")
                context.assets.open("dictionary.sqlite3").use { input ->
                    temp.outputStream().use(input::copyTo)
                }
                temp.copyTo(databaseFile, overwrite = true)
                temp.delete()
            }
            open().use { conn ->
                conn.prepare("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='entries'").use { stmt ->
                    check(stmt.step() && stmt.getLong(0) == 1L) { "dictionary.sqlite3 does not contain the desktop entries table." }
                }
            }
        }
    }

    private fun open(): SQLiteConnection = driver.open(databaseFile.absolutePath)

    suspend fun count(): Int = withContext(Dispatchers.IO) {
        mutex.withLock {
            open().use { conn ->
                conn.prepare("SELECT COUNT(*) FROM entries").use { stmt ->
                    if (stmt.step()) stmt.getLong(0).toInt() else 0
                }
            }
        }
    }

    suspend fun search(query: String, limit: Int = 20): List<DictionaryEntry> = withContext(Dispatchers.IO) {
        mutex.withLock {
            val q = DictionaryText.normalize(query)
            open().use { conn ->
                if (q.isBlank()) return@use selectEntries(conn, "SELECT ${columns()} FROM entries ORDER BY entry_index LIMIT ?") {
                    it.bindLong(1, limit.toLong())
                }

                val found = linkedMapOf<Int, DictionaryEntry>()
                val prefix = "$q%"
                selectEntries(
                    conn,
                    """
                    SELECT ${columns()} FROM entries
                    WHERE headword_norm = ? OR lexeme_norm = ? OR translation_norm = ?
                       OR headword_norm LIKE ? OR lexeme_norm LIKE ? OR translation_norm LIKE ?
                    ORDER BY
                      CASE WHEN headword_norm = ? OR lexeme_norm = ? THEN 0
                           WHEN headword_norm LIKE ? OR lexeme_norm LIKE ? THEN 1
                           WHEN translation_norm = ? THEN 2 ELSE 3 END,
                      length(lexeme_norm), headword_norm
                    LIMIT ?
                    """.trimIndent(),
                ) { stmt ->
                    stmt.bindText(1, q); stmt.bindText(2, q); stmt.bindText(3, q)
                    stmt.bindText(4, prefix); stmt.bindText(5, prefix); stmt.bindText(6, prefix)
                    stmt.bindText(7, q); stmt.bindText(8, q); stmt.bindText(9, prefix); stmt.bindText(10, prefix)
                    stmt.bindText(11, q); stmt.bindLong(12, limit.toLong())
                }.forEach { found[it.index] = it }

                if (found.size < limit && q.length >= 2 && hasFts(conn)) {
                    val fts = q.split(' ').filter(String::isNotBlank).joinToString(" AND ") { token ->
                        "\"${token.replace("\"", "\"\"")}\"*"
                    }
                    runCatching {
                        selectEntries(
                            conn,
                            """
                            SELECT ${columns("e")} FROM entries_fts f
                            JOIN entries e ON e.entry_index = f.rowid
                            WHERE entries_fts MATCH ?
                            LIMIT ?
                            """.trimIndent(),
                        ) { stmt ->
                            stmt.bindText(1, fts)
                            stmt.bindLong(2, (limit * 3).toLong())
                        }
                    }.getOrDefault(emptyList()).forEach { found.putIfAbsent(it.index, it) }
                }

                if (found.size < max(8, limit / 2) && q.length >= 3) {
                    fuzzyFallback(conn, q, limit * 4).forEach { found.putIfAbsent(it.index, it) }
                }
                found.values.take(limit)
            }
        }
    }

    suspend fun entry(index: Int): DictionaryEntry? = withContext(Dispatchers.IO) {
        mutex.withLock {
            open().use { conn ->
                selectEntries(conn, "SELECT ${columns()} FROM entries WHERE entry_index = ? LIMIT 1") {
                    it.bindLong(1, index.toLong())
                }.firstOrNull()
            }
        }
    }

    suspend fun findExactLexeme(text: String, role: String? = null): DictionaryEntry? = withContext(Dispatchers.IO) {
        mutex.withLock {
            val q = DictionaryText.normalize(text.replace(Regex("^(der|die|das|ein|eine)\\s+", RegexOption.IGNORE_CASE), ""))
            open().use { conn ->
                val sql = if (role == null)
                    "SELECT ${columns()} FROM entries WHERE lexeme_norm = ? LIMIT 1"
                else
                    "SELECT ${columns()} FROM entries WHERE lexeme_norm = ? AND role = ? LIMIT 1"
                selectEntries(conn, sql) {
                    it.bindText(1, q)
                    if (role != null) it.bindText(2, role)
                }.firstOrNull()
            }
        }
    }

    suspend fun add(raw: String): DictionaryEntry = withContext(Dispatchers.IO) {
        mutex.withLock {
            val p = DictionaryText.parse(raw)
            open().use { conn ->
                ensureNotDuplicate(conn, p, null)
                val next = conn.prepare("SELECT COALESCE(MAX(entry_index), -1) + 1 FROM entries").use { stmt ->
                    if (stmt.step()) stmt.getLong(0).toInt() else 0
                }
                transaction(conn) {
                    insertEntry(conn, next, p)
                    insertFts(conn, next, p)
                }
                p.toEntry(next)
            }
        }
    }

    suspend fun replace(index: Int, raw: String): DictionaryEntry = withContext(Dispatchers.IO) {
        mutex.withLock {
            val p = DictionaryText.parse(raw)
            open().use { conn ->
                ensureNotDuplicate(conn, p, index)
                transaction(conn) {
                    conn.prepare(
                        """
                        UPDATE entries SET raw=?, first_line=?, headword=?, role=?, translation=?,
                          headword_norm=?, lexeme_norm=?, translation_norm=?, search_norm=?
                        WHERE entry_index=?
                        """.trimIndent(),
                    ).use { stmt ->
                        bindParsed(stmt, p, offset = 0)
                        stmt.bindLong(10, index.toLong())
                        stmt.step()
                    }
                    if (hasFts(conn)) {
                        conn.prepare("DELETE FROM entries_fts WHERE rowid=?").use { it.bindLong(1, index.toLong()); it.step() }
                        insertFts(conn, index, p)
                    }
                }
                p.toEntry(index)
            }
        }
    }

    suspend fun delete(index: Int) = withContext(Dispatchers.IO) {
        mutex.withLock {
            open().use { conn ->
                transaction(conn) {
                    conn.prepare("DELETE FROM entries WHERE entry_index=?").use { it.bindLong(1, index.toLong()); it.step() }
                    val later = mutableListOf<Int>()
                    conn.prepare("SELECT entry_index FROM entries WHERE entry_index > ? ORDER BY entry_index").use { stmt ->
                        stmt.bindLong(1, index.toLong())
                        while (stmt.step()) later += stmt.getLong(0).toInt()
                    }
                    later.forEach { old ->
                        conn.prepare("UPDATE entries SET entry_index=? WHERE entry_index=?").use { stmt ->
                            stmt.bindLong(1, (old - 1).toLong()); stmt.bindLong(2, old.toLong()); stmt.step()
                        }
                    }
                    rebuildFts(conn)
                }
            }
        }
    }

    suspend fun snapshotTo(destination: File) = withContext(Dispatchers.IO) {
        mutex.withLock {
            destination.parentFile?.mkdirs()
            databaseFile.copyTo(destination, overwrite = true)
        }
    }

    suspend fun replaceFrom(source: File) = withContext(Dispatchers.IO) {
        mutex.withLock {
            // Validate before replacing the working copy.
            driver.open(source.absolutePath).use { conn ->
                conn.prepare("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='entries'").use { stmt ->
                    check(stmt.step() && stmt.getLong(0) == 1L) { "Remote file is not an ND German dictionary database." }
                }
            }
            val temp = File(databaseFile.parentFile, ".dictionary.sqlite3.pull.tmp")
            source.copyTo(temp, overwrite = true)
            if (databaseFile.exists() && !databaseFile.delete()) error("Could not replace local dictionary database")
            if (!temp.renameTo(databaseFile)) {
                temp.copyTo(databaseFile, overwrite = true)
                temp.delete()
            }
        }
    }

    private fun columns(alias: String? = null): String {
        val p = alias?.let { "$it." }.orEmpty()
        return listOf("entry_index", "raw", "first_line", "headword", "role", "translation", "headword_norm", "lexeme_norm", "translation_norm", "search_norm")
            .joinToString(", ") { p + it }
    }

    private fun selectEntries(conn: SQLiteConnection, sql: String, bind: (SQLiteStatement) -> Unit): List<DictionaryEntry> {
        val out = mutableListOf<DictionaryEntry>()
        conn.prepare(sql).use { stmt ->
            bind(stmt)
            while (stmt.step()) out += row(stmt)
        }
        return out
    }

    private fun row(stmt: SQLiteStatement) = DictionaryEntry(
        index = stmt.getLong(0).toInt(), raw = stmt.getText(1), firstLine = stmt.getText(2),
        headword = stmt.getText(3), role = stmt.getText(4), translation = stmt.getText(5),
        headwordNorm = stmt.getText(6), lexemeNorm = stmt.getText(7), translationNorm = stmt.getText(8), searchNorm = stmt.getText(9),
    )

    private fun fuzzyFallback(conn: SQLiteConnection, q: String, candidateLimit: Int): List<DictionaryEntry> {
        val first = q.firstOrNull()?.toString().orEmpty()
        val candidates = selectEntries(
            conn,
            "SELECT ${columns()} FROM entries WHERE lexeme_norm LIKE ? OR translation_norm LIKE ? LIMIT 1800",
        ) { stmt ->
            stmt.bindText(1, "$first%")
            stmt.bindText(2, "$first%")
        }
        return candidates.map { entry ->
            val score = maxOf(similarity(q, entry.lexemeNorm), similarity(q, entry.headwordNorm), similarity(q, entry.translationNorm))
            score to entry
        }.filter { it.first >= 0.60 }.sortedByDescending { it.first }.take(candidateLimit).map { it.second }
    }

    private fun similarity(a: String, b: String): Double {
        if (a.isBlank() || b.isBlank()) return 0.0
        if (a == b) return 1.0
        val aa = a.take(80); val bb = b.take(80)
        val prev = IntArray(bb.length + 1) { it }
        val curr = IntArray(bb.length + 1)
        for (i in aa.indices) {
            curr[0] = i + 1
            for (j in bb.indices) {
                curr[j + 1] = minOf(curr[j] + 1, prev[j + 1] + 1, prev[j] + if (aa[i] == bb[j]) 0 else 1)
            }
            for (j in prev.indices) prev[j] = curr[j]
        }
        return 1.0 - prev[bb.length].toDouble() / maxOf(aa.length, bb.length).toDouble()
    }

    private fun hasFts(conn: SQLiteConnection): Boolean = conn.prepare(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='entries_fts'"
    ).use { stmt -> stmt.step() && stmt.getLong(0) > 0 }

    private fun ensureNotDuplicate(conn: SQLiteConnection, p: ParsedEntry, exclude: Int?) {
        val sql = buildString {
            append("SELECT 1 FROM entries WHERE headword_norm=? AND role=?")
            if (exclude != null) append(" AND entry_index<>?")
            append(" LIMIT 1")
        }
        conn.prepare(sql).use { stmt ->
            stmt.bindText(1, p.headwordNorm); stmt.bindText(2, p.role)
            if (exclude != null) stmt.bindLong(3, exclude.toLong())
            require(!stmt.step()) { "Duplicate entry: ${p.headword} (${p.role})" }
        }
    }

    private fun insertEntry(conn: SQLiteConnection, index: Int, p: ParsedEntry) {
        conn.prepare(
            "INSERT INTO entries(entry_index,raw,first_line,headword,role,translation,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES(?,?,?,?,?,?,?,?,?,?)"
        ).use { stmt ->
            stmt.bindLong(1, index.toLong()); bindParsed(stmt, p, 1); stmt.step()
        }
    }

    private fun bindParsed(stmt: SQLiteStatement, p: ParsedEntry, offset: Int) {
        stmt.bindText(1 + offset, p.raw); stmt.bindText(2 + offset, p.firstLine); stmt.bindText(3 + offset, p.headword)
        stmt.bindText(4 + offset, p.role); stmt.bindText(5 + offset, p.translation); stmt.bindText(6 + offset, p.headwordNorm)
        stmt.bindText(7 + offset, p.lexemeNorm); stmt.bindText(8 + offset, p.translationNorm); stmt.bindText(9 + offset, p.searchNorm)
    }

    private fun insertFts(conn: SQLiteConnection, index: Int, p: ParsedEntry) {
        if (!hasFts(conn)) return
        conn.prepare("INSERT INTO entries_fts(rowid,headword_norm,lexeme_norm,translation_norm,search_norm) VALUES(?,?,?,?,?)").use { stmt ->
            stmt.bindLong(1, index.toLong()); stmt.bindText(2, p.headwordNorm); stmt.bindText(3, p.lexemeNorm)
            stmt.bindText(4, p.translationNorm); stmt.bindText(5, p.searchNorm); stmt.step()
        }
    }

    private fun rebuildFts(conn: SQLiteConnection) {
        if (!hasFts(conn)) return
        conn.execSQL("DELETE FROM entries_fts")
        conn.execSQL(
            "INSERT INTO entries_fts(rowid,headword_norm,lexeme_norm,translation_norm,search_norm) " +
                "SELECT entry_index,headword_norm,lexeme_norm,translation_norm,search_norm FROM entries ORDER BY entry_index"
        )
    }

    private inline fun transaction(conn: SQLiteConnection, block: () -> Unit) {
        conn.execSQL("BEGIN IMMEDIATE")
        try {
            block()
            conn.execSQL("COMMIT")
        } catch (t: Throwable) {
            runCatching { conn.execSQL("ROLLBACK") }
            throw t
        }
    }

    private fun ParsedEntry.toEntry(index: Int) = DictionaryEntry(
        index, raw, firstLine, headword, role, translation, headwordNorm, lexemeNorm, translationNorm, searchNorm
    )
}
