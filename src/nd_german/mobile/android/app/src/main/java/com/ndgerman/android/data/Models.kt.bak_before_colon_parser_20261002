package com.ndgerman.android.data

import java.text.Normalizer
import java.util.Locale

data class DictionaryEntry(
    val index: Int,
    val raw: String,
    val firstLine: String,
    val headword: String,
    val role: String,
    val translation: String,
    val headwordNorm: String,
    val lexemeNorm: String,
    val translationNorm: String,
    val searchNorm: String,
) {
    val ipa: String get() = Regex("\\[([^]]+)]").find(firstLine)?.groupValues?.getOrNull(1)?.trim().orEmpty()
    val english: String get() = explicitField("English").ifBlank { translation }
    val persian: String get() = explicitField("Persian")
    val penglish: String get() = explicitField("Penglish")

    fun explicitField(label: String): String {
        val wanted = label.lowercase(Locale.ROOT)
        return raw.lineSequence().drop(1).mapNotNull { line ->
            val p = line.indexOf(':')
            if (p <= 0) null else line.substring(0, p).trim().lowercase(Locale.ROOT) to line.substring(p + 1).trim()
        }.firstOrNull { it.first == wanted }?.second.orEmpty()
    }

    fun detailLines(): List<String> = raw.lineSequence().drop(1)
        .map(String::trim)
        .filter(String::isNotBlank)
        .filterNot {
            val label = it.substringBefore(':', "").trim().lowercase(Locale.ROOT)
            label == "english" || label == "persian" || label == "penglish"
        }
        .toList()
}

data class ParsedEntry(
    val raw: String,
    val firstLine: String,
    val headword: String,
    val role: String,
    val translation: String,
    val headwordNorm: String,
    val lexemeNorm: String,
    val translationNorm: String,
    val searchNorm: String,
)

object DictionaryText {
    private val ipa = Regex("\\s*\\[[^]]*]")
    private val paren = Regex("\\s*\\([^)]*\\)")
    private val spaces = Regex("\\s+")
    private val roleSplitter = Regex(
        "\\s+(?=(?:nicht trennbar|trennbar|untrennbar|transitiv|intransitiv|reflexiv|regelmäßig|unregelmäßig|stark|schwach|adjektiv|adverb|pronom|konjunktion|präposition|substantiv|verb)\\b)",
        RegexOption.IGNORE_CASE,
    )

    private val persianMap = mapOf(
        'ي' to 'ی', 'ى' to 'ی', 'ك' to 'ک', 'ة' to 'ه', 'ۀ' to 'ه',
        'ؤ' to 'و', 'إ' to 'ا', 'أ' to 'ا', 'ٱ' to 'ا', '‌' to ' ', 'ـ' to '\u0000',
    )

    fun normalize(text: String): String {
        var value = buildString {
            text.forEach { ch ->
                val mapped = persianMap[ch]
                if (mapped != null && mapped != '\u0000') append(mapped)
                else if (mapped == null) append(ch)
            }
        }.lowercase(Locale.ROOT)
            .replace("ß", "ss")
            .replace("ä", "a")
            .replace("ö", "o")
            .replace("ü", "u")
        value = Normalizer.normalize(value, Normalizer.Form.NFKD)
            .filterNot { Character.getType(it) == Character.NON_SPACING_MARK.toInt() }
        value = value.replace(Regex("[^\\p{L}\\p{N}_\\u0600-\\u06ff]+"), " ")
        return spaces.replace(value, " ").trim()
    }

    fun inflectionStems(text: String): List<String> {
        val query = normalize(text)
        if (
            query.length < 4 ||
            ' ' in query ||
            !query.all(Char::isLetter)
        ) {
            return emptyList()
        }

        val suffixes =
            listOf(
                "ern",
                "nen",
                "en",
                "em",
                "er",
                "es",
                "e",
                "n",
                "s",
            )
        val seen = linkedSetOf(query)
        val stems = mutableListOf<String>()
        suffixes.forEach { suffix ->
            if (!query.endsWith(suffix)) return@forEach
            val stem = query.dropLast(suffix.length)
            if (stem.length < 3 || !seen.add(stem)) return@forEach
            stems += stem
        }
        return stems
    }

    fun parse(rawText: String): ParsedEntry {
        val cleaned = rawText.replace("\uFEFF", "").trim()
        require(cleaned.isNotBlank()) { "The entry is empty." }
        val lines = cleaned.lineSequence().map(String::trim).filter(String::isNotBlank).toList()
        require(lines.isNotEmpty()) { "The entry must have a non-empty line." }

        var first = lines.first()
        var head = extractHeadword(first)
        if (head.isBlank()) {
            for (candidate in lines.drop(1)) {
                val candidateHead = extractHeadword(candidate)
                if (candidateHead.isNotBlank()) {
                    first = candidate
                    head = candidateHead
                    break
                }
            }
        }
        if (head.isBlank()) head = lines.first().trim(' ', ':', ';', '|', '=', '_', '-', '–', '—')
        if (head.isBlank()) head = "[unrecognized entry]"

        val translation = first.substringAfter(':', "").trim()
        val role = detectRole(first, head)
        val headNorm = normalize(head)
        val lexemeNorm = headNorm.replace(Regex("^(?:der|die|das|ein|eine)\\s+"), "")
        return ParsedEntry(
            raw = cleaned,
            firstLine = first,
            headword = head,
            role = role,
            translation = translation,
            headwordNorm = headNorm,
            lexemeNorm = lexemeNorm,
            translationNorm = normalize(translation),
            searchNorm = normalize(cleaned),
        )
    }

    fun extractHeadword(firstLine: String): String {
        var cleaned = ipa.replace(firstLine, "")
        cleaned = paren.replace(cleaned, "")
        cleaned = cleaned.substringBefore(':').trim()
        cleaned = roleSplitter.split(cleaned, 2).firstOrNull().orEmpty()
        return spaces.replace(cleaned, " ").trim(' ', '-')
    }

    fun detectRole(firstLine: String, headword: String): String {
        val line = firstLine.lowercase(Locale.ROOT)
        val head = headword.lowercase(Locale.ROOT).trim()
        return when {
            "konjunktion" in line -> "conjunction"
            "präposition" in line -> "preposition"
            "pronom" in line -> "pronoun"
            "adverb" in line -> "adverb"
            "adjektiv" in line -> "adjective"
            "partizip" in line -> "participle"
            "phrase" in line || "redewendung" in line -> "phrase"
            listOf("der ", "die ", "das ", "ein ", "eine ").any(head::startsWith) ||
                "substantiv" in line || "plural:" in line -> "noun"
            listOf("transitiv", "intransitiv", "reflexiv", "trennbar", "untrennbar", "verb", "präsens:", "perfekt:")
                .any { it in line } || head.startsWith("sich ") -> "verb"
            head.split(' ').firstOrNull().orEmpty().endsWith("en") ||
                head.split(' ').firstOrNull().orEmpty().endsWith("eln") ||
                head.split(' ').firstOrNull().orEmpty().endsWith("ern") -> "verb"
            head.contains(' ') -> "phrase"
            else -> "unknown"
        }
    }
}

data class SyncState(
    val connected: Boolean = false,
    val busy: Boolean = false,
    val pendingLocalChanges: Boolean = false,
    val lastRemoteRevision: String? = null,
    val message: String = "Offline database ready",
)
