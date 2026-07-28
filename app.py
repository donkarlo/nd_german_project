from __future__ import annotations

import argparse
import html
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import yaml
from PySide6.QtCore import (
    QObject,
    QRunnable,
    QStringListModel,
    QThreadPool,
    QTimer,
    Qt,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QFont, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCompleter,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from conjugation_core import (
    ConjugationResult,
    GermanConjugator,
    IrregularVerbDatabase,
    is_plausible_infinitive,
    normalize_verb,
)
from dictionary_core import DictionaryEntry, DictionaryIndex, DuplicateEntryError, parse_entry
from grammar_core import (ADJECTIVE_ENDINGS, ARTICLES, CASES, GENDERS, PERSONAL, PERSONS, POSSESSIVE_STEMS, PRONOUN_DECLENSIONS, REFLEXIVE, decline_adjective, possessive_form)
from pronunciation_core import (
    PronunciationDownloadError,
    build_pronunciation_url,
    download_pronunciation,
)


APP_DIR = Path(__file__).resolve().parent
DEFAULT_SETTINGS = {
    "database_path": "/absolute/path/to/woerterbuch.txt",
    "irregular_verbs_path": str(APP_DIR / "irregular_verbs.yaml"),
    "max_results": 20,
    "fuzzy_threshold": 58,
    "search_debounce_ms": 80,
    "conjugation_search_debounce_ms": 60,
    "conjugation_suggestion_count": 14,
    "pronunciation_enabled": True,
    "pronunciation_api_url": "https://translate.google.com/translate_tts",
    "pronunciation_language": "de",
    "pronunciation_timeout_ms": 12000,
    "pronunciation_max_download_bytes": 5000000,
    "window_title": "Deutsch–English–Persian Dictionary",
}


def load_settings(settings_path: Path) -> dict[str, Any]:
    if not settings_path.exists():
        settings_path.write_text(
            yaml.safe_dump(DEFAULT_SETTINGS, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    loaded = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}
    settings = dict(DEFAULT_SETTINGS)
    settings.update(loaded)
    settings["max_results"] = max(1, int(settings["max_results"]))
    settings["fuzzy_threshold"] = max(0, min(100, int(settings["fuzzy_threshold"])))
    settings["search_debounce_ms"] = max(0, int(settings["search_debounce_ms"]))
    settings["conjugation_search_debounce_ms"] = max(
        0, int(settings["conjugation_search_debounce_ms"])
    )
    settings["conjugation_suggestion_count"] = max(
        1, int(settings["conjugation_suggestion_count"])
    )
    settings["pronunciation_enabled"] = bool(settings["pronunciation_enabled"])
    settings["pronunciation_timeout_ms"] = max(
        1000, int(settings["pronunciation_timeout_ms"])
    )
    settings["pronunciation_max_download_bytes"] = max(
        100000, int(settings["pronunciation_max_download_bytes"])
    )
    return settings


def resolve_configured_path(value: Any, settings_path: Path) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = settings_path.parent / path
    return path.resolve()


class PronunciationWorkerSignals(QObject):
    succeeded = Signal(int, str, object)
    failed = Signal(int, str, str)


class PronunciationDownloadTask(QRunnable):
    def __init__(
        self,
        request_id: int,
        word: str,
        url: str,
        timeout_seconds: float,
        max_bytes: int,
    ) -> None:
        super().__init__()
        self.request_id = request_id
        self.word = word
        self.url = url
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.signals = PronunciationWorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            audio = download_pronunciation(
                self.url,
                timeout_seconds=self.timeout_seconds,
                max_bytes=self.max_bytes,
            )
        except PronunciationDownloadError as exc:
            self.signals.failed.emit(self.request_id, self.word, str(exc))
            return
        except Exception as exc:  # Defensive boundary around the worker thread.
            self.signals.failed.emit(
                self.request_id, self.word, f"Unexpected pronunciation error: {exc}"
            )
            return
        self.signals.succeeded.emit(self.request_id, self.word, audio)


class AddEntryDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        initial_text: str = "",
        window_title: str = "Add dictionary entry",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(window_title)
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        instruction = QLabel(
            "Paste the complete entry. The first line is used to detect the word spelling and grammatical role."
        )
        instruction.setWordWrap(True)
        layout.addWidget(instruction)

        self.editor = QTextEdit(self)
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText(
            "Example:\n\nder Begriff [bəˈɡʁɪf]: term\nBedeutung: ...\nex: ..."
        )
        layout.addWidget(self.editor, 1)

        self.preview = QLabel("Detected word: —    Role: —", self)
        self.preview.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.preview)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.editor.textChanged.connect(self._update_preview)
        if initial_text:
            self.editor.setPlainText(initial_text)
            self.editor.moveCursor(self.editor.textCursor().MoveOperation.Start)
        self.editor.setFocus()

    def entry_text(self) -> str:
        return self.editor.toPlainText().strip()

    def _update_preview(self) -> None:
        text = self.entry_text()
        if not text:
            self.preview.setText("Detected word: —    Role: —")
            return
        try:
            entry = parse_entry(text)
        except ValueError:
            self.preview.setText("Detected word: invalid entry")
            return
        self.preview.setText(f"Detected word: {entry.headword}    Role: {entry.role}")

    def _validate_and_accept(self) -> None:
        try:
            parse_entry(self.entry_text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid entry", str(exc))
            return
        self.accept()


class DictionaryWindow(QMainWindow):
    def __init__(self, settings_path: Path, settings: dict[str, Any]) -> None:
        super().__init__()
        self.settings_path = settings_path
        self.settings = settings
        self.database_path = resolve_configured_path(settings["database_path"], settings_path)
        self.irregular_verbs_path = resolve_configured_path(
            settings["irregular_verbs_path"], settings_path
        )
        self.index: DictionaryIndex | None = None
        self.conjugation_database: IrregularVerbDatabase | None = None
        self.conjugator: GermanConjugator | None = None
        # Pronunciation download and playback are both lazy. Dictionary indexing
        # and searching therefore never performs web I/O or initializes multimedia.
        self._tts_thread_pool = QThreadPool(self)
        self._tts_thread_pool.setMaxThreadCount(2)
        self._tts_request_id = 0
        self._tts_tasks: dict[int, PronunciationDownloadTask] = {}
        self._tts_player: Any = None
        self._tts_audio_output: Any = None
        self._tts_temp_path: str | None = None

        self.setWindowTitle(str(settings["window_title"]))
        self.resize(1040, 820)
        self.setMinimumSize(320, 240)

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(False)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)
        self.tabs.addTab(self._build_dictionary_tab(), "Dictionary")
        self.tabs.addTab(self._build_conjugation_tab(), "Conjugation")
        self.tabs.addTab(self._build_article_tab(), "Artikel")
        self.tabs.addTab(self._build_pronoun_tab(), "Pronomen")
        self.tabs.addTab(self._build_adjective_tab(), "Adjektivendungen")
        self.setCentralWidget(self.tabs)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(int(settings["search_debounce_ms"]))
        self.search_timer.timeout.connect(self.perform_search)

        self.conjugation_timer = QTimer(self)
        self.conjugation_timer.setSingleShot(True)
        self.conjugation_timer.setInterval(int(settings["conjugation_search_debounce_ms"]))
        self.conjugation_timer.timeout.connect(self.perform_conjugation_search)

        self.search_box.textChanged.connect(self._schedule_search)
        self.search_box.returnPressed.connect(self.perform_search)
        self.add_button.clicked.connect(self.open_add_dialog)
        self.results.anchorClicked.connect(self._open_dictionary_link)
        self.conjugation_search_box.textChanged.connect(self._schedule_conjugation_search)
        self.conjugation_search_box.returnPressed.connect(self.perform_conjugation_search)
        self.conjugation_results.anchorClicked.connect(self._open_conjugation_link)

        focus_action = QAction(self)
        focus_action.setShortcut(QKeySequence.Find)
        focus_action.triggered.connect(self._focus_current_search)
        self.addAction(focus_action)

        add_action = QAction(self)
        add_action.setShortcut(QKeySequence.New)
        add_action.triggered.connect(self.open_add_dialog)
        self.addAction(add_action)

        self._load_database()
        self._load_conjugation_database()
        self.search_box.setFocus()

    def _build_dictionary_tab(self) -> QWidget:
        # This is the original dictionary interface and behavior, placed unchanged inside its own tab.
        tab = QWidget(self)
        outer = QVBoxLayout(tab)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        top = QHBoxLayout()
        top.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.search_box = QLineEdit(tab)
        self.search_box.setClearButtonEnabled(True)
        self.search_box.setPlaceholderText("Search German, English, Penglish or Persian…")
        self.search_box.setAccessibleName("Dictionary search")
        top.addWidget(self.search_box, 1)

        self.add_button = QPushButton("Add", tab)
        self.add_button.setAccessibleName("Add dictionary entry")
        top.addWidget(self.add_button)
        outer.addLayout(top)

        self.results = QTextBrowser(tab)
        self.results.setOpenExternalLinks(False)
        self.results.setOpenLinks(False)
        self.results.setReadOnly(True)
        self.results.setFont(QFont("Sans Serif", 11))
        self.results.setMinimumWidth(0)
        outer.addWidget(self.results, 1)

        self.status = QLabel(tab)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.status)
        return tab

    def _build_conjugation_tab(self) -> QWidget:
        tab = QWidget(self)
        outer = QVBoxLayout(tab)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        top = QHBoxLayout()
        top.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

        self.conjugation_search_box = QLineEdit(tab)
        self.conjugation_search_box.setClearButtonEnabled(True)
        self.conjugation_search_box.setPlaceholderText(
            "German infinitive, for example: haben, gehen, aufstehen, arbeiten…"
        )
        self.conjugation_search_box.setAccessibleName("Verb conjugation search")
        top.addWidget(self.conjugation_search_box, 1)
        outer.addLayout(top)

        self.conjugation_results = QTextBrowser(tab)
        self.conjugation_results.setOpenExternalLinks(False)
        self.conjugation_results.setReadOnly(True)
        self.conjugation_results.setFont(QFont("Sans Serif", 10))
        self.conjugation_results.setMinimumWidth(0)
        outer.addWidget(self.conjugation_results, 1)

        self.conjugation_status = QLabel(tab)
        self.conjugation_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        outer.addWidget(self.conjugation_status)
        return tab


    GRAMMAR_CSS = """
    <style>
      body { font-family: sans-serif; font-size: 11pt; }
      h2 { color: #2f527f; margin-bottom: 8px; }
      .hint { color: #445; margin: 4px 0 12px 0; }
      table { border-collapse: collapse; width: 100%; margin: 8px 0 18px 0; }
      th { background: #466eaa; color: white; font-weight: bold; padding: 8px; border: 1px solid #365786; }
      td { padding: 7px; border: 1px solid #aebfd6; }
      tr:nth-child(odd) td { background: #ebf3ff; }
      tr:nth-child(even) td { background: #dce9fa; }
      .group { background: #365786; color: white; font-weight: bold; }
      .form { font-size: 13pt; font-weight: bold; }
      .dash { color: #777; }
    </style>
    """

    def _make_combo(self, items, parent, *, allow_all: bool = True):
        combo = QComboBox(parent)
        if allow_all:
            combo.addItem("Alle")
        combo.addItems(list(items))
        return combo

    @staticmethod
    def _table(headers: list[str], rows: list[list[str]]) -> str:
        head = "".join(f"<th>{html.escape(str(x))}</th>" for x in headers)
        body = []
        for row in rows:
            cells = "".join(f"<td>{html.escape(str(x))}</td>" for x in row)
            body.append(f"<tr>{cells}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    @staticmethod
    def _selected(combo: QComboBox, all_values) -> list[str]:
        value = combo.currentText()
        return list(all_values) if value == "Alle" else [value]

    def _build_article_tab(self) -> QWidget:
        tab = QWidget(self)
        outer = QVBoxLayout(tab)
        top = QHBoxLayout()
        top.addWidget(QLabel("Artikeltyp:"))
        self.article_type = self._make_combo(ARTICLES.keys(), tab)
        top.addWidget(self.article_type)
        top.addWidget(QLabel("Kasus:"))
        self.article_case = self._make_combo(CASES, tab)
        top.addWidget(self.article_case)
        top.addWidget(QLabel("Genus/Numerus:"))
        self.article_gender = self._make_combo(GENDERS, tab)
        top.addWidget(self.article_gender)
        top.addStretch(1)
        outer.addLayout(top)
        self.article_results = QTextBrowser(tab)
        self.article_results.setFont(QFont("Sans Serif", 10))
        outer.addWidget(self.article_results, 1)
        for combo in (self.article_type, self.article_case, self.article_gender):
            combo.currentTextChanged.connect(self._render_article)
        self._render_article()
        return tab

    def _render_article(self) -> None:
        types = self._selected(self.article_type, ARTICLES.keys())
        cases = self._selected(self.article_case, CASES)
        genders = self._selected(self.article_gender, GENDERS)
        rows: list[list[str]] = []
        for typ in types:
            for case in cases:
                values = ARTICLES[typ][case]
                rows.append([typ, case] + [values[GENDERS.index(g)] for g in genders])
        headers = ["Artikeltyp", "Kasus", *genders]
        note = "Leere/Alle Filter zeigen alle passenden Formen."
        content = f"<h2>Artikel in den vier Kasus</h2><p class='hint'>{note}</p>" + self._table(headers, rows)
        self.article_results.setHtml(self.GRAMMAR_CSS + content)

    def _build_pronoun_tab(self) -> QWidget:
        tab = QWidget(self)
        outer = QVBoxLayout(tab)
        top = QHBoxLayout()
        pronoun_types = [
            "Personalpronomen", "Possessivpronomen / Possessivartikel",
            "Reflexivpronomen", *PRONOUN_DECLENSIONS.keys()
        ]
        self.pronoun_type = self._make_combo(pronoun_types, tab)
        self.pronoun_case = self._make_combo(CASES, tab)
        self.pronoun_person = self._make_combo(PERSONS, tab)
        self.pronoun_owner = self._make_combo(POSSESSIVE_STEMS.keys(), tab)
        self.pronoun_gender = self._make_combo(GENDERS, tab)
        controls = (
            ("Typ:", self.pronoun_type), ("Kasus:", self.pronoun_case),
            ("Person:", self.pronoun_person), ("Besitzer/Subjekt:", self.pronoun_owner),
            ("Bezugswort:", self.pronoun_gender),
        )
        self.pronoun_labels = {}
        for label, widget in controls:
            lab = QLabel(label)
            self.pronoun_labels[label] = lab
            top.addWidget(lab)
            top.addWidget(widget)
        outer.addLayout(top)
        self.pronoun_results = QTextBrowser(tab)
        self.pronoun_results.setFont(QFont("Sans Serif", 10))
        outer.addWidget(self.pronoun_results, 1)
        for combo in (self.pronoun_type, self.pronoun_case, self.pronoun_person,
                      self.pronoun_owner, self.pronoun_gender):
            combo.currentTextChanged.connect(self._render_pronoun)
        self._render_pronoun()
        return tab

    def _render_pronoun(self) -> None:
        selected_type = self.pronoun_type.currentText()
        all_types = [
            "Personalpronomen", "Possessivpronomen / Possessivartikel",
            "Reflexivpronomen", *PRONOUN_DECLENSIONS.keys()
        ]
        types = all_types if selected_type == "Alle" else [selected_type]
        cases = self._selected(self.pronoun_case, CASES)
        persons = self._selected(self.pronoun_person, PERSONS)
        owners = self._selected(self.pronoun_owner, POSSESSIVE_STEMS.keys())
        genders = self._selected(self.pronoun_gender, GENDERS)

        show_person = selected_type in ("Alle", "Personalpronomen", "Reflexivpronomen")
        show_owner = selected_type in ("Alle", "Possessivpronomen / Possessivartikel")
        show_gender = selected_type == "Alle" or selected_type.startswith("Possessiv") or selected_type in PRONOUN_DECLENSIONS
        self.pronoun_person.setVisible(show_person)
        self.pronoun_labels["Person:"].setVisible(show_person)
        self.pronoun_owner.setVisible(show_owner)
        self.pronoun_labels["Besitzer/Subjekt:"].setVisible(show_owner)
        self.pronoun_gender.setVisible(show_gender)
        self.pronoun_labels["Bezugswort:"].setVisible(show_gender)

        sections: list[str] = []
        for typ in types:
            rows: list[list[str]] = []
            if typ == "Personalpronomen":
                valid_cases = [c for c in cases if c in PERSONAL]
                for case in valid_cases:
                    for person in persons:
                        rows.append([case, person, PERSONAL[case][PERSONS.index(person)]])
                headers = ["Kasus", "Person", "Form"]
            elif typ == "Reflexivpronomen":
                valid_cases = [c for c in cases if c in REFLEXIVE]
                for case in valid_cases:
                    for person in persons:
                        rows.append([case, person, REFLEXIVE[case][PERSONS.index(person)]])
                headers = ["Kasus", "Person", "Form"]
            elif typ == "Possessivpronomen / Possessivartikel":
                for owner in owners:
                    for case in cases:
                        for gender in genders:
                            rows.append([owner, case, gender, possessive_form(owner, case, gender)])
                headers = ["Besitzer/Subjekt", "Kasus", "Genus/Numerus des Bezugsworts", "Form"]
            else:
                for case in cases:
                    for gender in genders:
                        form = PRONOUN_DECLENSIONS[typ][case][GENDERS.index(gender)]
                        rows.append([case, gender, form])
                headers = ["Kasus", "Genus/Numerus", "Form"]
            if rows:
                sections.append(f"<h2>{html.escape(typ)}</h2>" + self._table(headers, rows))
        self.pronoun_results.setHtml(
            self.GRAMMAR_CSS + "<p class='hint'>Alle Filter sind optional. Nicht anwendbare Kasus werden automatisch ausgelassen.</p>" + "".join(sections)
        )

    def _build_adjective_tab(self) -> QWidget:
        tab = QWidget(self)
        outer = QVBoxLayout(tab)
        top = QHBoxLayout()
        self.adj_search = QLineEdit(tab)
        self.adj_search.setClearButtonEnabled(True)
        self.adj_search.setPlaceholderText("Optionales Adjektiv, z. B. gut, hoch, dunkel …")
        self.adj_type = self._make_combo(ADJECTIVE_ENDINGS.keys(), tab)
        self.adj_case = self._make_combo(CASES, tab)
        self.adj_gender = self._make_combo(GENDERS, tab)
        for label, widget in (("Adjektiv:", self.adj_search), ("Deklination:", self.adj_type),
                              ("Kasus:", self.adj_case), ("Genus/Numerus:", self.adj_gender)):
            top.addWidget(QLabel(label))
            top.addWidget(widget)
        outer.addLayout(top)
        self.adj_results = QTextBrowser(tab)
        self.adj_results.setFont(QFont("Sans Serif", 10))
        outer.addWidget(self.adj_results, 1)
        self.adj_search.textChanged.connect(self._render_adjective)
        for combo in (self.adj_type, self.adj_case, self.adj_gender):
            combo.currentTextChanged.connect(self._render_adjective)
        self._render_adjective()
        return tab

    def _render_adjective(self) -> None:
        adjective = self.adj_search.text().strip()
        declensions = self._selected(self.adj_type, ADJECTIVE_ENDINGS.keys())
        cases = self._selected(self.adj_case, CASES)
        genders = self._selected(self.adj_gender, GENDERS)
        rows: list[list[str]] = []
        for declension in declensions:
            for case in cases:
                row = [declension, case]
                for gender in genders:
                    form, ending = decline_adjective(adjective, declension, case, gender)
                    row.append(form if adjective else "-" + ending)
                rows.append(row)
        headers = ["Deklination", "Kasus", *genders]
        title = f"Adjektivdeklination: {html.escape(adjective)}" if adjective else "Adjektivendungen"
        note = "Ohne eingegebenes Adjektiv werden nur die Endungen gezeigt."
        self.adj_results.setHtml(
            self.GRAMMAR_CSS + f"<h2>{title}</h2><p class='hint'>{note}</p>" + self._table(headers, rows)
        )

    def _focus_current_search(self) -> None:
        if self.tabs.currentIndex() == 1:
            self.conjugation_search_box.setFocus()
            self.conjugation_search_box.selectAll()
        else:
            self.search_box.setFocus()
            self.search_box.selectAll()

    # ------------------------ Original dictionary behavior ------------------------
    def _load_database(self) -> None:
        try:
            self.index = DictionaryIndex.from_file(self.database_path)
        except FileNotFoundError:
            self._handle_missing_database()
            return
        except (OSError, UnicodeError, ValueError) as exc:
            self.index = None
            self.results.setPlainText(f"Could not load the dictionary database:\n{exc}")
            self.status.setText("Database unavailable")
            QMessageBox.critical(self, "Database error", str(exc))
            return

        self.status.setText(
            f"Loaded {len(self.index.entries):,} entries from {self.database_path}"
        )
        self.perform_search()

    def _handle_missing_database(self) -> None:
        self.index = None
        message = (
            f"The configured database does not exist:\n{self.database_path}\n\n"
            "Choose the uploaded woerterbuch.txt file or edit settings.yaml."
        )
        answer = QMessageBox.question(
            self,
            "Dictionary database not found",
            message,
            QMessageBox.Open | QMessageBox.Cancel,
            QMessageBox.Open,
        )
        if answer != QMessageBox.Open:
            self.results.setPlainText(message)
            self.status.setText("Database not found")
            return
        chosen, _ = QFileDialog.getOpenFileName(
            self,
            "Select dictionary database",
            str(Path.home()),
            "Text files (*.txt);;All files (*)",
        )
        if not chosen:
            self.results.setPlainText(message)
            self.status.setText("Database not found")
            return
        self.database_path = Path(chosen).resolve()
        self.settings["database_path"] = str(self.database_path)
        self.settings_path.write_text(
            yaml.safe_dump(self.settings, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        self._load_database()

    def _schedule_search(self) -> None:
        self.search_timer.start()

    def perform_search(self) -> None:
        if self.index is None:
            return
        query = self.search_box.text()
        matches = self.index.search(
            query,
            limit=int(self.settings["max_results"]),
            fuzzy_threshold=int(self.settings["fuzzy_threshold"]),
        )
        self._render_results([match.entry for match in matches])
        if query.strip():
            self.status.setText(
                f"{len(matches)} result(s) for “{query}” — {len(self.index.entries):,} entries indexed"
            )
        else:
            self.status.setText(
                f"Showing the first {len(matches)} of {len(self.index.entries):,} entries"
            )

    def _render_results(self, entries: list[DictionaryEntry]) -> None:
        if not entries:
            self.results.setHtml(
                "<p style='font-size:14pt'><b>No matching entry found.</b></p>"
                "<p>Try fewer characters or a different spelling.</p>"
            )
            return

        cards: list[str] = []
        entry_positions = {id(entry): idx for idx, entry in enumerate(self.index.entries)} if self.index else {}
        for entry in entries:
            lines = entry.raw.splitlines()
            title = html.escape(lines[0])
            body = html.escape("\n".join(lines[1:]))
            direction = "rtl" if any("\u0600" <= ch <= "\u06ff" for ch in entry.raw) else "ltr"
            body_html = f"<pre style='white-space:pre-wrap; margin:8px 0 0 0'>{body}</pre>" if body else ""
            if bool(self.settings.get("pronunciation_enabled", True)):
                speak_target = quote(entry.headword, safe="")
                speaker = (
                    f"<a href='speak:{speak_target}' title='German pronunciation' "
                    "style='text-decoration:none; font-size:11pt'>🔊</a>&nbsp;"
                )
            else:
                speaker = ""
            entry_index = entry_positions.get(id(entry))
            actions = ""
            if entry_index is not None:
                actions = (
                    "<div dir='ltr' style='margin-top:10px; padding-top:8px; "
                    "border-top:1px solid #d6dae0'>"
                    f"<a href='edit:{entry_index}' style='text-decoration:none'>✏️ Edit</a>"
                    "&nbsp;&nbsp;&nbsp;&nbsp;"
                    f"<a href='delete:{entry_index}' style='text-decoration:none'>🗑️ Delete</a>"
                    "</div>"
                )
            cards.append(
                "<div style='margin:50px 50px 50px 50px; padding:12px; border:1px solid #b8bec7; "
                "border-radius:7px' dir='{}'>"
                "<div dir='ltr' style='font-size:13pt'>{}<b>{}</b></div>{}{}</div>".format(
                    direction, speaker, title, body_html, actions
                )
            )
        self.results.setHtml("".join(cards))
        self.results.verticalScrollBar().setValue(0)

    def _open_dictionary_link(self, url: QUrl) -> None:
        scheme = url.scheme()
        payload = url.toString().split(":", 1)[-1]
        if scheme == "speak":
            word = unquote(payload).strip()
            if word:
                self._speak_word(word)
            return
        if scheme not in {"edit", "delete"}:
            return
        try:
            entry_index = int(payload)
        except ValueError:
            return
        if scheme == "edit":
            self.open_edit_dialog(entry_index)
        else:
            self.delete_dictionary_entry(entry_index)

    def _ensure_tts_player(self) -> None:
        if self._tts_player is not None:
            return
        # Multimedia is initialized only after valid audio has been downloaded.
        from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

        self._tts_audio_output = QAudioOutput(self)
        self._tts_player = QMediaPlayer(self)
        self._tts_player.setAudioOutput(self._tts_audio_output)
        self._tts_audio_output.setVolume(1.0)
        self._tts_player.errorOccurred.connect(self._on_tts_player_error)

    def _speak_word(self, word: str) -> None:
        if not bool(self.settings.get("pronunciation_enabled", True)):
            return
        api_url = str(self.settings.get("pronunciation_api_url", "")).strip()
        if not api_url:
            QMessageBox.warning(
                self,
                "Pronunciation unavailable",
                "Set pronunciation_api_url in settings.yaml.",
            )
            return

        try:
            url = build_pronunciation_url(
                api_url,
                word,
                str(self.settings.get("pronunciation_language", "de")),
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Pronunciation unavailable", str(exc))
            return

        self._tts_request_id += 1
        request_id = self._tts_request_id
        timeout_seconds = int(
            self.settings.get("pronunciation_timeout_ms", 12000)
        ) / 1000.0
        max_bytes = int(
            self.settings.get("pronunciation_max_download_bytes", 5_000_000)
        )

        task = PronunciationDownloadTask(
            request_id=request_id,
            word=word,
            url=url,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        task.signals.succeeded.connect(self._on_tts_downloaded)
        task.signals.failed.connect(self._on_tts_download_failed)
        self._tts_tasks[request_id] = task
        self.status.setText(f"Loading pronunciation for “{word}”…")
        self._tts_thread_pool.start(task)

    @Slot(int, str, object)
    def _on_tts_downloaded(self, request_id: int, word: str, audio: bytes) -> None:
        self._tts_tasks.pop(request_id, None)
        if request_id != self._tts_request_id:
            return

        try:
            self._ensure_tts_player()
        except ImportError as exc:
            self.status.setText(f"Qt Multimedia is unavailable: {exc}")
            QMessageBox.warning(
                self,
                "Pronunciation unavailable",
                f"Qt Multimedia is unavailable:\n{exc}",
            )
            return

        if self._tts_player is not None:
            self._tts_player.stop()
        self._remove_tts_temp_file()
        try:
            with tempfile.NamedTemporaryFile(
                prefix="deutsch_dictionary_tts_", suffix=".mp3", delete=False
            ) as handle:
                handle.write(audio)
                self._tts_temp_path = handle.name
        except OSError as exc:
            self.status.setText(f"Could not save pronunciation audio: {exc}")
            return

        self._tts_player.setSource(QUrl.fromLocalFile(self._tts_temp_path))
        self._tts_player.play()
        self.status.setText(f"Playing pronunciation: {word}")

    @Slot(int, str, str)
    def _on_tts_download_failed(
        self, request_id: int, word: str, error_message: str
    ) -> None:
        self._tts_tasks.pop(request_id, None)
        if request_id != self._tts_request_id:
            return
        self.status.setText(
            f"Could not load pronunciation for “{word}”: {error_message}"
        )

    def _on_tts_player_error(self, _error: Any, error_string: str) -> None:
        if error_string:
            self.status.setText(f"Could not play pronunciation: {error_string}")

    def _remove_tts_temp_file(self) -> None:
        if not self._tts_temp_path:
            return
        try:
            os.remove(self._tts_temp_path)
        except FileNotFoundError:
            pass
        except OSError:
            return
        self._tts_temp_path = None

    def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt naming convention
        self._tts_request_id += 1
        self._tts_thread_pool.clear()
        if self._tts_player is not None:
            self._tts_player.stop()
        self._remove_tts_temp_file()
        super().closeEvent(event)

    def open_add_dialog(self) -> None:
        if self.index is None:
            QMessageBox.warning(self, "Database unavailable", "Load a dictionary database first.")
            return
        dialog = AddEntryDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            added = self.index.add_entry(self.database_path, dialog.entry_text())
        except DuplicateEntryError as exc:
            QMessageBox.warning(
                self,
                "Duplicate entry",
                f'“{exc.headword}” already exists with grammatical role “{exc.role}”.',
            )
            return
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.critical(self, "Could not add entry", str(exc))
            return

        self.tabs.setCurrentIndex(0)
        self.search_box.setText(added.headword)
        self.perform_search()
        QMessageBox.information(
            self,
            "Entry added",
            f'Added “{added.headword}” ({added.role}) to the dictionary.',
        )

    def open_edit_dialog(self, entry_index: int) -> None:
        if self.index is None or not 0 <= entry_index < len(self.index.entries):
            QMessageBox.warning(self, "Entry unavailable", "This dictionary entry no longer exists.")
            return
        original = self.index.entries[entry_index]
        dialog = AddEntryDialog(
            self,
            initial_text=original.raw,
            window_title=f"Edit dictionary entry: {original.headword}",
        )
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            updated = self.index.replace_entry(
                self.database_path, entry_index, dialog.entry_text()
            )
        except DuplicateEntryError as exc:
            QMessageBox.warning(
                self,
                "Duplicate entry",
                f'“{exc.headword}” already exists with grammatical role “{exc.role}”.',
            )
            return
        except (OSError, UnicodeError, ValueError, IndexError) as exc:
            QMessageBox.critical(self, "Could not edit entry", str(exc))
            return
        self.search_box.setText(updated.headword)
        self.perform_search()
        QMessageBox.information(self, "Entry updated", f'Updated “{updated.headword}”.')

    def delete_dictionary_entry(self, entry_index: int) -> None:
        if self.index is None or not 0 <= entry_index < len(self.index.entries):
            QMessageBox.warning(self, "Entry unavailable", "This dictionary entry no longer exists.")
            return
        entry = self.index.entries[entry_index]
        answer = QMessageBox.question(
            self,
            "Delete dictionary entry",
            f'Delete “{entry.headword}” ({entry.role}) permanently?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return
        try:
            removed = self.index.delete_entry(self.database_path, entry_index)
        except (OSError, UnicodeError, ValueError, IndexError) as exc:
            QMessageBox.critical(self, "Could not delete entry", str(exc))
            return
        self.perform_search()
        QMessageBox.information(self, "Entry deleted", f'Deleted “{removed.headword}”.')

    # ----------------------------- Conjugation tab -----------------------------
    def _load_conjugation_database(self) -> None:
        try:
            self.conjugation_database = IrregularVerbDatabase.from_file(
                self.irregular_verbs_path
            )
            self.conjugator = GermanConjugator(self.conjugation_database)
        except (FileNotFoundError, OSError, UnicodeError, ValueError) as exc:
            self.conjugation_database = None
            self.conjugator = None
            self.conjugation_results.setPlainText(
                f"Could not load the irregular verb database:\n{exc}\n\n"
                "Set irregular_verbs_path in settings.yaml."
            )
            self.conjugation_status.setText("Irregular verb database unavailable")
            return

        words = sorted(self.conjugation_database.records)
        completer = QCompleter(words, self.conjugation_search_box)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.activated.connect(self._choose_conjugation)
        self.conjugation_search_box.setCompleter(completer)
        self.conjugation_status.setText(
            f"Loaded {len(words)} irregular base verbs from {self.irregular_verbs_path}. "
            "Regular verbs are generated by rules."
        )
        self._render_conjugation_welcome()

    def _schedule_conjugation_search(self) -> None:
        self.conjugation_timer.start()

    def _choose_conjugation(self, verb: str) -> None:
        self.conjugation_search_box.setText(verb)
        self.perform_conjugation_search()

    def _open_conjugation_link(self, url: QUrl) -> None:
        if url.scheme() != "verb":
            return
        verb = url.path().lstrip("/") or url.host()
        if not verb:
            verb = url.toString().split(":", 1)[-1]
        self._choose_conjugation(verb)

    def perform_conjugation_search(self) -> None:
        if self.conjugator is None or self.conjugation_database is None:
            return
        query = self.conjugation_search_box.text().strip()
        if not query:
            self._render_conjugation_welcome()
            return

        normalized, _ = normalize_verb(query)
        exact_irregular = normalized in self.conjugation_database.records
        if exact_irregular or is_plausible_infinitive(query):
            try:
                result = self.conjugator.conjugate(query)
            except ValueError as exc:
                self._render_conjugation_suggestions(query, str(exc))
                return
            self._render_conjugation(result)
            self.conjugation_status.setText(
                f"{result.infinitive} · {result.source} · auxiliary: {result.auxiliary} · "
                f"Partizip II: {result.participle}"
            )
            return

        self._render_conjugation_suggestions(query)

    def _render_conjugation_welcome(self) -> None:
        self.conjugation_results.setHtml(
            "<div style='padding:18px'>"
            "<h2 style='color:#2452a4'>German verb conjugation</h2>"
            "<p>Enter an infinitive. Regular verbs are generated immediately; irregular and mixed verbs use the bundled YAML database.</p>"
            "<p><b>Examples:</b> "
            "<a href='verb:haben'>haben</a> · <a href='verb:gehen'>gehen</a> · "
            "<a href='verb:aufstehen'>aufstehen</a> · <a href='verb:arbeiten'>arbeiten</a></p>"
            "<p>The result includes Indikativ, Konjunktiv I, Konjunktiv II, the three imperative forms "
            "<b>du / ihr / Sie</b>, participles and infinitives.</p>"
            "</div>"
        )

    def _render_conjugation_suggestions(self, query: str, message: str = "") -> None:
        assert self.conjugation_database is not None
        suggestions = self.conjugation_database.suggestions(
            query, limit=int(self.settings["conjugation_suggestion_count"])
        )
        links = "".join(
            f"<li style='margin:5px 0'><a href='verb:{html.escape(verb)}'>{html.escape(verb)}</a></li>"
            for verb in suggestions
        )
        warning = f"<p>{html.escape(message)}</p>" if message else ""
        self.conjugation_results.setHtml(
            "<div style='padding:18px'>"
            f"<h3 style='color:#2452a4'>Search results for “{html.escape(query)}”</h3>"
            f"{warning}"
            + (f"<ul>{links}</ul>" if links else "<p>No similar irregular verb was found.</p>")
            + "<p>A regular verb can also be entered directly as a complete infinitive ending in <b>-en</b> or <b>-n</b>.</p>"
            "</div>"
        )
        self.conjugation_status.setText(f"Suggestions for: {query}")

    @staticmethod
    def _format_conjugation_line(line: str) -> str:
        escaped = html.escape(line)
        for pronoun in ("er/sie/es", "ich", "du", "wir", "ihr", "Sie"):
            prefix = html.escape(pronoun) + " "
            if escaped.startswith(prefix):
                return (
                    f"<span style='color:#66758a'>{html.escape(pronoun)}</span> "
                    f"<span style='color:#2452a4'>{escaped[len(prefix):]}</span>"
                )
        return f"<span style='color:#2452a4'>{escaped}</span>"

    @classmethod
    def _conjugation_card(cls, title: str, lines: list[str]) -> str:
        body = "".join(
            f"<div style='margin:0 0 7px 0; white-space:normal'>{cls._format_conjugation_line(line)}</div>"
            for line in lines
        )
        return (
            "<td valign='top' style='padding:6px; min-width:0'>"
            "<div style='background:#f3f6fa; border:1px solid #e2e7ee; padding:10px'>"
            f"<div align='center' style='margin-bottom:10px; color:#1f2937'><b>{html.escape(title)}</b></div>"
            f"{body}</div></td>"
        )

    @classmethod
    def _conjugation_section(cls, title: str, cards: list[tuple[str, list[str]]]) -> str:
        rows: list[str] = []
        for start in range(0, len(cards), 3):
            chunk = cards[start : start + 3]
            cells = "".join(cls._conjugation_card(card_title, lines) for card_title, lines in chunk)
            cells += "<td></td>" * (3 - len(chunk))
            rows.append(f"<tr>{cells}</tr>")
        return (
            f"<div align='center' style='color:#2452a4; margin:12px 0 4px 0'><b>{html.escape(title)}</b></div>"
            "<table width='100%' cellspacing='0' cellpadding='0'>"
            + "".join(rows)
            + "</table>"
        )

    def _render_conjugation(self, result: ConjugationResult) -> None:
        sections = "".join(
            self._conjugation_section(section_name, cards)
            for section_name, cards in result.sections.items()
        )
        imperative = self._conjugation_section(
            "IMPERATIV PRÄSENS", [("du · ihr · Sie", result.imperatives)]
        )
        participles = self._conjugation_section(
            "PARTIZIP", [(name, [form]) for name, form in result.participles]
        )
        infinitives = self._conjugation_section(
            "INFINITIV", [(name, [form]) for name, form in result.infinitives]
        )
        note = (
            "<div style='margin:12px 8px; padding:9px; background:#fff8e7; border:1px solid #eedca7'>"
            f"<b>Note:</b> {html.escape(result.note)}</div>"
            if result.note
            else ""
        )
        self.conjugation_results.setHtml(
            "<div style='padding:8px; border:1px solid #d7dde7'>"
            f"<h2 align='center' style='color:#2452a4; margin:5px 0'>{html.escape(result.infinitive)}</h2>"
            f"<div align='center' style='color:#66758a'>Partizip II: <b>{html.escape(result.participle)}</b> · "
            f"Hilfsverb: <b>{html.escape(result.auxiliary)}</b> · {html.escape(result.source)}</div>"
            f"{note}{sections}{imperative}{participles}{infinitives}</div>"
        )
        self.conjugation_results.verticalScrollBar().setValue(0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search a dictionary and conjugate German verbs.")
    parser.add_argument(
        "--settings",
        type=Path,
        default=Path(__file__).with_name("settings.yaml"),
        help="Path to the YAML settings file.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="Temporarily override database_path from settings.yaml.",
    )
    parser.add_argument(
        "--irregular-verbs",
        type=Path,
        help="Temporarily override irregular_verbs_path from settings.yaml.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings_path = args.settings.expanduser().resolve()
    settings = load_settings(settings_path)
    if args.database:
        settings["database_path"] = str(args.database.expanduser().resolve())
    if args.irregular_verbs:
        settings["irregular_verbs_path"] = str(args.irregular_verbs.expanduser().resolve())

    app = QApplication(sys.argv)
    app.setApplicationName("Deutsch Dictionary")
    window = DictionaryWindow(settings_path, settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
