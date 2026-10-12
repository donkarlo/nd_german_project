from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication

from app_legacy import AddEntryDialog
from entry_paste import (
    EntryPlainTextEdit,
    entry_text_from_mime,
    normalize_entry_paste,
    repair_flattened_entry,
)


class EntryPasteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_multiline_plain_text_is_preserved(self) -> None:
        entry = (
            "anfragen [ˈanˌfʁaːɡn̩]: to inquire\n"
            "English: to inquire\n"
            "Persian: استعلام گرفتن\n"
            "Grammatical role: Verb, trennbar\n"
            "Bedeutung: um Auskunft bitten.\n"
            "ex: Ich frage nach.: I inquire."
        )
        data = QMimeData()
        data.setText(entry)
        data.setHtml("<p>Unrelated formatting must not overwrite clipboard text</p>")
        editor = EntryPlainTextEdit()
        editor.insertFromMimeData(data)
        self.assertEqual(editor.toPlainText(), entry)
        dialog = AddEntryDialog(initial_text=editor.toPlainText())
        self.assertEqual(dialog.entry_text(), entry)
        self.assertEqual(dialog.editor.toPlainText().count("\n"), 5)

    def test_only_html_yields_real_lines(self) -> None:
        data = QMimeData()
        data.setHtml(
            "<div>anfragen: to inquire</div>"
            "<div>English: to inquire</div>"
            "<div>Persian: استعلام گرفتن</div>"
            "<div>ex: Ich frage an.: I inquire.</div>"
        )
        self.assertEqual(
            entry_text_from_mime(data),
            "anfragen: to inquire\nEnglish: to inquire\n"
            "Persian: استعلام گرفتن\nex: Ich frage an.: I inquire.",
        )

    def test_flattened_dictionary_fields_are_restored(self) -> None:
        entry = (
            "anfragen: inquire English: inquire Persian: استعلام گرفتن "
            "Penglish: estelam gereftan Grammatical role: Verb "
            "Bedeutung: sich erkundigen. ex: Ich frage an.: I inquire. "
            "Präsens: ich frage an"
        )
        data = QMimeData()
        data.setText(entry)
        expected = (
            "anfragen: inquire\nEnglish: inquire\nPersian: استعلام گرفتن\n"
            "Penglish: estelam gereftan\nGrammatical role: Verb\n"
            "Bedeutung: sich erkundigen.\nex: Ich frage an.: I inquire.\n"
            "Präsens: ich frage an"
        )
        self.assertEqual(entry_text_from_mime(data), expected)
        editor = EntryPlainTextEdit()
        editor.insertFromMimeData(data)
        self.assertEqual(editor.toPlainText(), expected)

    def test_normalize_unicode_separators(self) -> None:
        self.assertEqual(normalize_entry_paste("A\r\nB\rC\u2028D\u2029E"), "A\nB\nC\nD\nE")

    def test_single_line_unstructured_text_unchanged(self) -> None:
        text = "Wie sagt man English: in German?"
        self.assertEqual(repair_flattened_entry(text), text)

    def test_clipboard_paste_command(self) -> None:
        entry = "anfragen: inquire\nEnglish: inquire\nPersian: استعلام گرفتن"
        data = QMimeData()
        data.setText(entry)
        QApplication.clipboard().setMimeData(data)
        editor = EntryPlainTextEdit()
        editor.paste()
        self.assertEqual(editor.toPlainText(), entry)


if __name__ == "__main__":
    unittest.main()
