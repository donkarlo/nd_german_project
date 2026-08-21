from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from urllib.parse import quote, unquote

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

import app_legacy as legacy
import dictionary_core


LANGUAGE_LABELS = ("English", "Persian", "Penglish")
PERSIAN_RE = re.compile(r"[\u0600-\u06ff]")
EXPLICIT_MEANING_RE = re.compile(r"^(English|Persian|Penglish)\s*:\s*(.*)$", re.IGNORECASE)
FIELD_RE = re.compile(r"^([^:]{1,48}):\s*(.*)$")
PENGLISH_HINT_RE = re.compile(
    r"\b(?:kardan|shodan|dashtan|dadan|gereftan|zadan|khordan|raftan|amadan|"
    r"goftan|didan|fahmidan|khastan|tavanestan|bordan|avardan|budan|hastan|"
    r"nist|yani|baraye|maniye?)\b",
    re.IGNORECASE,
)


def _make_language_icon() -> QIcon:
    """Return a language/dictionary icon for the Ubuntu taskbar and window."""
    for theme_name in ("accessories-dictionary", "preferences-desktop-locale"):
        icon = QIcon.fromTheme(theme_name)
        if not icon.isNull():
            return icon

    pixmap = QPixmap(96, 96)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor("#5b3fa8"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(8, 10, 80, 72, 16, 16)
    painter.setPen(QColor("white"))
    painter.setFont(QFont("Sans Serif", 24, QFont.Weight.Bold))
    painter.drawText(8, 10, 80, 72, int(Qt.AlignmentFlag.AlignCenter), "DE")
    painter.end()
    return QIcon(pixmap)


def _split_existing_translation(text: str) -> tuple[str, str, str]:
    """Conservatively reuse translations already present on the legacy first line."""
    value = text.strip()
    if not value:
        return "", "", ""

    english: list[str] = []
    persian: list[str] = []
    penglish: list[str] = []
    chunks = [part.strip(" ;") for part in re.split(r"\s+\.\s+", value) if part.strip(" ;")]
    if not chunks:
        chunks = [value]

    for chunk in chunks:
        if PERSIAN_RE.search(chunk):
            persian.append(chunk)
        elif len(chunks) > 1 and PENGLISH_HINT_RE.search(chunk):
            penglish.append(chunk)
        else:
            english.append(chunk)
    return "; ".join(english), "; ".join(persian), "; ".join(penglish)


def _normalize_database_language_fields(database_path: Path) -> None:
    """Add English/Persian/Penglish lines without changing the entry-block format."""
    if not database_path.exists():
        return

    original = database_path.read_text(encoding="utf-8")
    normalized_entries: list[str] = []
    changed = False

    for raw in dictionary_core.split_entries(original):
        lines = raw.splitlines()
        if not lines:
            continue

        explicit: dict[str, str] = {}
        retained: list[str] = []
        for line in lines[1:]:
            match = EXPLICIT_MEANING_RE.match(line.strip())
            if match:
                explicit.setdefault(match.group(1).capitalize(), match.group(2).strip())
            else:
                retained.append(line)

        try:
            translation = legacy.parse_entry(raw).translation
        except Exception:
            translation = lines[0].split(":", 1)[1].strip() if ":" in lines[0] else ""

        english, persian, penglish = _split_existing_translation(translation)
        values = {
            "English": explicit.get("English", english),
            "Persian": explicit.get("Persian", persian),
            "Penglish": explicit.get("Penglish", penglish),
        }
        language_lines = [f"{label}: {values[label] or '-'}" for label in LANGUAGE_LABELS]
        rebuilt = "\n".join([lines[0], *language_lines, *retained]).strip()
        normalized_entries.append(rebuilt)
        if rebuilt != "\n".join(lines).strip():
            changed = True

    if not changed:
        return

    backup = database_path.with_name(f"{database_path.stem}.before_language_fields.bak")
    if not backup.exists():
        shutil.copy2(database_path, backup)

    temp = database_path.with_name(f".{database_path.name}.language-fields.tmp")
    temp.write_text("\n\n".join(normalized_entries).rstrip() + "\n", encoding="utf-8", newline="\n")
    temp.replace(database_path)


def _meaning_fields(entry) -> dict[str, str]:
    values = {label: "" for label in LANGUAGE_LABELS}
    for line in entry.raw.splitlines()[1:]:
        match = EXPLICIT_MEANING_RE.match(line.strip())
        if match:
            values[match.group(1).capitalize()] = match.group(2).strip()

    if not values["English"]:
        english, persian, penglish = _split_existing_translation(entry.translation)
        values["English"] = english
        values["Persian"] = values["Persian"] or persian
        values["Penglish"] = values["Penglish"] or penglish
    return {key: value or "-" for key, value in values.items()}


def _extract_ipa(first_line: str) -> str:
    match = re.search(r"\[([^\]]+)\]", first_line)
    return match.group(1).strip() if match else "-"


def _render_detail_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.casefold().startswith("ex:"):
        return (
            "<div class='example-line' dir='ltr'>"
            "<span class='field-label'>ex:</span> "
            f"{html.escape(stripped[3:].strip())}</div>"
        )
    match = FIELD_RE.match(stripped)
    if match:
        label, value = match.groups()
        return (
            "<div class='detail-line'>"
            f"<span class='field-label'>{html.escape(label)}:</span> "
            f"{html.escape(value)}</div>"
        )
    return f"<div class='detail-line'>{html.escape(stripped)}</div>"


def _custom_render_results(self, entries) -> None:
    if not entries:
        self.results.setHtml(
            "<p style='font-size:14pt'><b>No matching entry found.</b></p>"
            "<p>Try fewer characters or a different spelling.</p>"
        )
        return

    positions = {id(entry): idx for idx, entry in enumerate(self.index.entries)} if self.index else {}
    cards: list[str] = []
    css = """
    <style>
      body { font-family: sans-serif; font-size: 11pt; }
      .entry-card { margin: 30px 42px; padding: 14px 16px; border: 1px solid #b8bec7; border-radius: 8px; }
      .head-row { font-size: 16pt; font-weight: 700; margin-bottom: 10px; }
      .speaker { text-decoration: none; font-size: 12pt; margin-left: 8px; }
      .meaning-box { background: #fff7cf; border-radius: 4px; padding: 6px 9px; margin: 2px 0; }
      .meaning-fa { direction: rtl; text-align: right; }
      .field-label { color: #6f42c1; font-weight: 700; }
      .meta-line { margin-top: 6px; }
      .example-line { background: #dcecff; padding: 6px 9px; margin: 0; }
      .detail-line { margin: 4px 0; }
      .actions { margin-top: 12px; font-size: 9.5pt; }
      .actions a { text-decoration: none; margin-right: 15px; }
    </style>
    """

    for entry in entries:
        word = entry.headword.strip() or entry.first_line.split(":", 1)[0].strip()
        meanings = _meaning_fields(entry)
        ipa = _extract_ipa(entry.first_line)
        index = positions.get(id(entry), -1)

        if bool(self.settings.get("pronunciation_enabled", True)):
            speaker = (
                f"<a class='speaker' href='speak:{quote(word, safe='')}' "
                "title='German pronunciation'>&#128266;</a>"
            )
        else:
            speaker = ""

        meaning_html = (
            f"<div class='meaning-box'><span class='field-label'>English:</span> {html.escape(meanings['English'])}</div>"
            f"<div class='meaning-box meaning-fa'><span class='field-label'>Persian:</span> {html.escape(meanings['Persian'])}</div>"
            f"<div class='meaning-box'><span class='field-label'>Penglish:</span> {html.escape(meanings['Penglish'])}</div>"
        )
        meta_html = (
            f"<div class='meta-line'><span class='field-label'>Pronunciation:</span> [{html.escape(ipa)}]</div>"
            f"<div class='meta-line'><span class='field-label'>Grammatical role:</span> {html.escape(entry.role)}</div>"
        )
        details = "".join(
            _render_detail_line(line)
            for line in entry.raw.splitlines()[1:]
            if not EXPLICIT_MEANING_RE.match(line.strip())
        )

        actions: list[str] = []
        if entry.role == "verb":
            actions.append(f"<a href='conjugate:{quote(word, safe='')}'>Conjugate</a>")
        elif entry.role == "adjective":
            actions.append(f"<a href='adjective:{quote(word, safe='')}'>Endungen</a>")
        if index >= 0:
            actions.extend(
                [
                    f"<a href='edit:{index}'>Edit</a>",
                    f"<a href='delete:{index}'>Delete</a>",
                ]
            )
        actions_html = f"<div class='actions'>{''.join(actions)}</div>" if actions else ""

        cards.append(
            "<div class='entry-card'>"
            f"<div class='head-row' dir='ltr'>{html.escape(word)} {speaker}</div>"
            f"{meaning_html}{meta_html}{details}{actions_html}</div>"
        )

    self.results.setHtml(css + "".join(cards))
    self.results.verticalScrollBar().setValue(0)


def _dictionary_link_handler(original_handler):
    def handler(self, url: QUrl) -> None:
        scheme = url.scheme()
        payload = url.toString().split(":", 1)[-1]

        if scheme == "conjugate":
            verb = unquote(payload).strip()
            if verb:
                self.tabs.setCurrentIndex(1)
                self.conjugation_search_box.setText(verb)
                self.conjugation_search_box.setFocus()
                self.perform_conjugation_search()
            return

        if scheme == "adjective":
            adjective = unquote(payload).strip()
            if adjective:
                self.tabs.setCurrentIndex(4)
                self.adj_search.setText(adjective)
                self.adj_determiner.clear()
                for combo in (self.adj_type, self.adj_case, self.adj_gender):
                    all_index = combo.findText("Alle")
                    if all_index >= 0:
                        combo.setCurrentIndex(all_index)
                self.adj_search.setFocus()
                self._render_adjective()
            return

        original_handler(self, url)

    return handler


def _window_init(original_init):
    def init(self, settings_path: Path, settings: dict) -> None:
        database_path = legacy.resolve_configured_path(settings["database_path"], settings_path)
        _normalize_database_language_fields(database_path)
        original_init(self, settings_path, settings)
        icon = _make_language_icon()
        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)

    return init


def _install_patches() -> None:
    legacy.DictionaryWindow._render_results = _custom_render_results
    legacy.DictionaryWindow._open_dictionary_link = _dictionary_link_handler(
        legacy.DictionaryWindow._open_dictionary_link
    )
    legacy.DictionaryWindow.__init__ = _window_init(legacy.DictionaryWindow.__init__)


def main() -> int:
    _install_patches()
    return legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
