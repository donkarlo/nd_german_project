package com.ndgerman.android.ui

import android.content.ClipData
import android.text.Html

// Dictionary-entry fields are line-oriented in the desktop SQLite database.
// Keep the raw newline characters instead of treating clipboard text as rich text.
internal object DictionaryEntryPaste {
    private val fieldBoundary = Regex(
        """ +(?=(?:English|Persian|Penglish|Pronunciation|Grammatical role|Verwendung|Bedeutung|Gebrauch|Synonyme|Genitiv|Plural|Kollokation|Imperativ|Rektion(?:\s+\d+)?|Präsens|Präteritum|Perfekt|Futur I|Konjunktiv II|Konjunktiv I|ex):\s)""",
        RegexOption.IGNORE_CASE,
    )

    fun normalize(text: String): String = text
        .replace("\r\n", "\n")
        .replace('\r', '\n')
        .replace('\u2028', '\n')
        .replace('\u2029', '\n')

    fun restoreLines(text: String): String {
        val normalized = normalize(text)
        if ('\n' in normalized) return normalized

        // Only fix entries that clearly contain several recognized fields.
        // Do not break arbitrary prose, examples, or a short search expression.
        val boundaries = fieldBoundary.findAll(normalized).toList()
        if (boundaries.size < 3) return normalized
        return fieldBoundary.replace(normalized, "\n")
    }

    fun fromClip(clip: ClipData?): String? {
        val item = clip?.takeIf { it.itemCount > 0 }?.getItemAt(0) ?: return null
        val plain = item.text?.toString()?.let(::normalize).orEmpty()
        if ('\n' in plain) return plain

        // Some providers keep paragraph boundaries in text/html but flatten
        // text/plain. Interpret HTML only when it supplies real newlines.
        val richText = item.htmlText
            ?.let { Html.fromHtml(it, Html.FROM_HTML_MODE_COMPACT).toString() }
            ?.let(::normalize)
            .orEmpty()
        if ('\n' in richText.trimEnd('\n')) return richText.trimEnd('\n')

        val candidate = plain.ifBlank { richText }
        return candidate.takeIf { it.isNotBlank() }?.let(::restoreLines)
    }
}
