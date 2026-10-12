from __future__ import annotations

import re

from PySide6.QtCore import QMimeData
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import QPlainTextEdit


# Fallback for clipboard providers that send a single paragraph even though
# the copied dictionary entry is visually divided into labelled fields.
_ENTRY_FIELD_BOUNDARY = re.compile(
    r" +(?=(?:English|Persian|Penglish|Pronunciation|Grammatical role|"
    r"Verwendung|Bedeutung|Gebrauch|Synonyme|Genitiv|Plural|Kollokation|"
    r"Imperativ|Rektion(?:\s+\d+)?|Präsens|Präteritum|Perfekt|Futur I|"
    r"Konjunktiv II|Konjunktiv I|ex):\s)",
    re.IGNORECASE,
)


def normalize_entry_paste(text: str) -> str:
    """Preserve real line boundaries, including Unicode paragraph separators."""
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\u2028", "\n")
        .replace("\u2029", "\n")
    )


def repair_flattened_entry(text: str) -> str:
    """Restore field lines only when a clearly structured entry was flattened."""
    if "\n" in text:
        return text
    matches = list(_ENTRY_FIELD_BOUNDARY.finditer(text))
    if len(matches) < 3:
        return text
    return _ENTRY_FIELD_BOUNDARY.sub("\n", text)


def entry_text_from_mime(source: QMimeData) -> str | None:
    """Prefer unformatted, multiline clipboard text to Qt's HTML paste path."""
    if source.hasText():
        plain = normalize_entry_paste(source.text())
        if "\n" in plain:
            return plain
    else:
        plain = ""

    # Some rich clipboard providers carry line breaks only in the HTML.
    if source.hasHtml():
        document = QTextDocument()
        document.setHtml(source.html())
        rich_as_plain = normalize_entry_paste(document.toPlainText())
        if "\n" in rich_as_plain:
            return rich_as_plain

    if source.hasText():
        return repair_flattened_entry(plain)
    return None


class EntryPlainTextEdit(QPlainTextEdit):
    """Dictionary entry input that never interprets pasted text as rich text."""

    def insertFromMimeData(self, source: QMimeData) -> None:
        text = entry_text_from_mime(source)
        if text is None:
            super().insertFromMimeData(source)
        else:
            self.insertPlainText(text)
