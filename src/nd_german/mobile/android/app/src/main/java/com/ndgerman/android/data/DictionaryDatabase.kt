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
            val nounPreferred =
                query.trimStart()
                    .firstOrNull()
                    ?.isUpperCase() == true
            open().use { conn ->
                if (q.isBlank()) return@use selectEntries(
                    conn,
                    "SELECT ${columns()} FROM entries ORDER BY entry_index LIMIT ?",
                ) { it.bindLong(1, limit.toLong()) }

                val candidateLimit = max(180, minOf(320, limit * 16))
                val found = linkedMapOf<Int, DictionaryEntry>()
                val prefix = "$q%"
                val inflectionStems =
                    DictionaryText.inflectionStems(q)

                // Fast indexed German headword candidates plus first-line English.
                selectEntries(
                    conn,
                    """
                    SELECT ${columns()} FROM entries
                    WHERE headword_norm = ? OR lexeme_norm = ? OR translation_norm = ?
                       OR headword_norm LIKE ? OR lexeme_norm LIKE ? OR translation_norm LIKE ?
                    ORDER BY
                      CASE WHEN headword_norm = ? OR lexeme_norm = ? THEN 0
                           WHEN lexeme_norm LIKE ? THEN 1
                           WHEN headword_norm LIKE ? THEN 2
                           WHEN translation_norm = ? THEN 3 ELSE 4 END,
                      length(lexeme_norm), headword_norm
                    LIMIT ?
                    """.trimIndent(),
                ) { stmt ->
                    stmt.bindText(1, q); stmt.bindText(2, q); stmt.bindText(3, q)
                    stmt.bindText(4, prefix); stmt.bindText(5, prefix); stmt.bindText(6, prefix)
                    stmt.bindText(7, q); stmt.bindText(8, q)
                    stmt.bindText(9, prefix); stmt.bindText(10, prefix)
                    stmt.bindText(11, q); stmt.bindLong(12, candidateLimit.toLong())
                }.forEach { found[it.index] = it }

                if (
                    inflectionStems.isNotEmpty() &&
                    found.size < candidateLimit
                ) {
                    val placeholders =
                        List(inflectionStems.size) { "?" }
                            .joinToString(",")
                    val sql =
                        """
                        SELECT ${columns()} FROM entries
                        WHERE role IN ('noun','adjective','participle','unknown')
                          AND lexeme_norm IN ($placeholders)
                        LIMIT ?
                        """.trimIndent()
                    selectEntries(conn, sql) { stmt ->
                        inflectionStems.forEachIndexed {
                                index,
                                stem,
                            ->
                            stmt.bindText(index + 1, stem)
                        }
                        stmt.bindLong(
                            inflectionStems.size + 1,
                            (candidateLimit - found.size)
                                .toLong(),
                        )
                    }.forEach {
                        found.putIfAbsent(
                            it.index,
                            it,
                        )
                    }
                }

                // FTS supplies Penglish, Persian and explicit English candidates.
                if (found.size < candidateLimit && q.length >= 2 && hasFts(conn)) {
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
                            stmt.bindLong(2, candidateLimit.toLong())
                        }
                    }.getOrDefault(emptyList()).forEach { found.putIfAbsent(it.index, it) }
                }

                // Relax the FTS token to its first 3-4 chars so small internal
                // misspellings can still become candidates without scanning all rows.
                if (found.size < candidateLimit && q.length >= 4 && hasFts(conn)) {
                    val firstToken = q.split(' ').firstOrNull(String::isNotBlank).orEmpty()
                    val relaxed = firstToken.take(minOf(4, firstToken.length))
                    if (relaxed.length >= 3) {
                        val fts = "\"${relaxed.replace("\"", "\"\"")}\"*"
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
                                stmt.bindLong(2, minOf(180, candidateLimit).toLong())
                            }
                        }.getOrDefault(emptyList()).forEach { found.putIfAbsent(it.index, it) }
                    }
                }

                // Always reserve a German fuzzy path; FTS candidates must not crowd
                // out a near spelling such as "behörd"/"behrde" -> "Behörde".
                if (q.length >= 3 && found.size < candidateLimit) {
                    fuzzyGermanCandidates(conn, q, candidateLimit - found.size)
                        .forEach { found.putIfAbsent(it.index, it) }
                }

                found.values
                    .map {
                        searchScore(
                            q,
                            it,
                            inflectionStems,
                            nounPreferred,
                        ) to it
                    }
                    .filter { it.first > 0.0 }
                    .sortedWith(
                        compareByDescending<Pair<Double, DictionaryEntry>> { it.first }
                            .thenBy { it.second.lexemeNorm.length }
                            .thenBy { it.second.headwordNorm },
                    )
                    .take(limit)
                    .map { it.second }
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

    private fun fieldScore(
        q: String,
        value: String,
        base: Double,
        fuzzyCutoff: Double?,
    ): Double {
        if (value.isBlank()) return 0.0
        if (value == q) return base + 400.0
        if (value.startsWith(q)) return base + 320.0 - minOf(40.0, (value.length - q.length).toDouble())
        if (q in value.split(' ')) return base + 260.0
        if (q in value) return base + 220.0

        if (fuzzyCutoff != null && q.length >= 3) {
            val score = similarity(q, value)
            if (score >= fuzzyCutoff) return base + score * 100.0
        }
        return 0.0
    }

    private fun searchScore(
        q: String,
        entry: DictionaryEntry,
        inflectionStems: List<String>,
        nounPreferred: Boolean,
    ): Double {
        val inflectionScore =
            if (
                entry.role == "noun" ||
                entry.role == "adjective" ||
                entry.role == "participle" ||
                entry.role == "unknown"
            ) {
                val rolePenalty =
                    if (nounPreferred) {
                        when (entry.role) {
                            "noun" -> 0.0
                            "adjective" -> 18.0
                            "participle" -> 18.0
                            else -> 20.0
                        }
                    } else {
                        when (entry.role) {
                            "noun" -> 22.0
                            "adjective" -> 0.0
                            "participle" -> 8.0
                            else -> 6.0
                        }
                    }
                inflectionStems
                    .mapIndexedNotNull { index, stem ->
                        if (entry.lexemeNorm == stem) {
                            4350.0 -
                                rolePenalty -
                                minOf(
                                    30.0,
                                    index * 3.0,
                                )
                        } else {
                            null
                        }
                    }
                    .maxOrNull()
                    ?: 0.0
            } else {
                0.0
            }

        return maxOf(
            inflectionScore,
            // Deliberate priority: German > Penglish > Persian > English.
            fieldScore(q, entry.lexemeNorm, 4000.0, 0.72),
            fieldScore(q, entry.headwordNorm, 3990.0, 0.72),
            fieldScore(q, DictionaryText.normalize(entry.penglish), 3000.0, 0.74),
            fieldScore(q, DictionaryText.normalize(entry.persian), 2000.0, null),
            fieldScore(q, DictionaryText.normalize(entry.english), 1000.0, 0.78),
        )
    }

    private fun fuzzyGermanCandidates(
        conn: SQLiteConnection,
        q: String,
        candidateLimit: Int,
    ): List<DictionaryEntry> {
        if (candidateLimit <= 0 || q.isBlank()) return emptyList()
        val first = q.first().toString()
        val candidates = selectEntries(
            conn,
            """
            SELECT ${columns()} FROM entries
            WHERE lexeme_norm LIKE ?
              AND length(lexeme_norm) BETWEEN ? AND ?
            ORDER BY abs(length(lexeme_norm) - ?), lexeme_norm
            LIMIT ?
            """.trimIndent(),
        ) { stmt ->
            stmt.bindText(1, "$first%")
            stmt.bindLong(2, maxOf(1, q.length - 4).toLong())
            stmt.bindLong(3, (q.length + 8).toLong())
            stmt.bindLong(4, q.length.toLong())
            stmt.bindLong(5, minOf(220, candidateLimit).toLong())
        }
        return candidates
            .map { entry -> maxOf(similarity(q, entry.lexemeNorm), similarity(q, entry.headwordNorm)) to entry }
            .filter { it.first >= 0.60 }
            .sortedByDescending { it.first }
            .take(candidateLimit)
            .map { it.second }
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
