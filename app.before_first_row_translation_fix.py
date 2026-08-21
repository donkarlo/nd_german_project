from __future__ import annotations

import html
import re
import threading
from pathlib import Path
from urllib.parse import quote, unquote

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

import app_legacy as legacy
import dictionary_core
from language_enrichment import (
    DB_LOCK, EXPLICIT_MEANING_RE, enhanced_parse_entry, generate_missing_meanings,
    infer_role, is_missing, language_values, normalize_database,
)

FIELD_RE = re.compile(r"^([^:]{1,48}):\s*(.*)$")
ORIGINAL_ADD = dictionary_core.DictionaryIndex.add_entry
ORIGINAL_REPLACE = dictionary_core.DictionaryIndex.replace_entry
ORIGINAL_DELETE = dictionary_core.DictionaryIndex.delete_entry


def language_icon() -> QIcon:
    for name in ("accessories-dictionary", "preferences-desktop-locale"):
        icon = QIcon.fromTheme(name)
        if not icon.isNull(): return icon
    pixmap = QPixmap(96, 96); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor("#5b3fa8")); painter.setPen(Qt.PenStyle.NoPen); painter.drawRoundedRect(8, 10, 80, 72, 16, 16)
    painter.setPen(QColor("white")); painter.setFont(QFont("Sans Serif", 24, QFont.Weight.Bold))
    painter.drawText(8, 10, 80, 72, int(Qt.AlignmentFlag.AlignCenter), "DE"); painter.end()
    return QIcon(pixmap)


def locked_add(self, path, raw):
    with DB_LOCK: return ORIGINAL_ADD(self, path, raw)

def locked_replace(self, path, index, raw):
    with DB_LOCK: return ORIGINAL_REPLACE(self, path, index, raw)

def locked_delete(self, path, index):
    with DB_LOCK: return ORIGINAL_DELETE(self, path, index)


def detail_line(line: str) -> str:
    s = line.strip()
    if not s: return ""
    if s.casefold().startswith("ex:"):
        return "<div class='example-line' dir='ltr'><span class='field-label'>ex:</span> " + html.escape(s[3:].strip()) + "</div>"
    m = FIELD_RE.match(s)
    if m:
        return f"<div class='detail-line'><span class='field-label'>{html.escape(m.group(1))}:</span> {html.escape(m.group(2))}</div>"
    return f"<div class='detail-line'>{html.escape(s)}</div>"


def action(scheme: str, payload: str, icon: str, label: str) -> str:
    return f"<a class='action-link' href='{scheme}:{payload}'><span class='action-icon'>{icon}</span>&nbsp;{html.escape(label)}</a>"


def render_results(self, entries) -> None:
    if not entries:
        self.results.setHtml("<p style='font-size:14pt'><b>No matching entry found.</b></p><p>Try fewer characters or a different spelling.</p>")
        return
    positions = {id(e): i for i, e in enumerate(self.index.entries)} if self.index else {}
    css = """
    <style>
      body { font-family:sans-serif; font-size:11pt; line-height:1.58; }
      .entry-card { margin:30px 42px; padding:15px 17px; border:1px solid #b8bec7; border-radius:8px; line-height:1.58; }
      .head-row { font-size:16pt; font-weight:700; margin-bottom:12px; line-height:1.45; }
      .speaker { text-decoration:none; font-size:12pt; margin-left:8px; }
      .meaning-box { background:#fff7cf; border-radius:4px; padding:8px 10px; margin:4px 0; line-height:1.58; direction:ltr; text-align:left; }
      .persian-value { display:inline-block; direction:rtl; text-align:right; unicode-bidi:embed; margin-left:7px; }
      .field-label { color:#6f42c1; font-weight:700; }
      .meta-line { margin-top:8px; line-height:1.58; }
      .example-line { background:#dcecff; padding:8px 10px; margin:3px 0; line-height:1.58; }
      .detail-line { margin:6px 0; line-height:1.58; }
      .actions { margin-top:16px; font-size:9.5pt; line-height:1.8; white-space:nowrap; }
      .action-link { text-decoration:none; } .action-icon { font-size:9pt; font-weight:bold; }
    </style>"""
    cards = []
    for entry in entries:
        word = entry.headword.strip() or entry.first_line.split(":",1)[0].strip()
        values = language_values(entry.raw)
        values = {k:(v if not is_missing(v) else "-") for k,v in values.items()}
        role = infer_role(entry)
        ipa_m = re.search(r"\[([^\]]+)\]", entry.first_line); ipa = ipa_m.group(1).strip() if ipa_m else "-"
        speaker = f"<a class='speaker' href='speak:{quote(word, safe='')}' title='German pronunciation'>&#128266;</a>" if self.settings.get("pronunciation_enabled", True) else ""
        meanings = (
            f"<div class='meaning-box'><span class='field-label'>English:</span> {html.escape(values['English'])}</div>"
            "<div class='meaning-box'><span class='field-label'>Persian:</span> "
            f"<span class='persian-value' dir='rtl'>{html.escape(values['Persian'])}</span></div>"
            f"<div class='meaning-box'><span class='field-label'>Penglish:</span> {html.escape(values['Penglish'])}</div>"
        )
        meta = f"<div class='meta-line'><span class='field-label'>Pronunciation:</span> [{html.escape(ipa)}]</div><div class='meta-line'><span class='field-label'>Grammatical role:</span> {html.escape(role)}</div>"
        details = "".join(detail_line(line) for line in entry.raw.splitlines()[1:] if not EXPLICIT_MEANING_RE.match(line.strip()))
        links, encoded = [], quote(word, safe="")
        if role == "verb": links.append(action("conjugate", encoded, "&#8635;", "Conjugate"))
        if role == "adjective": links.append(action("adjective", encoded, "&#9398;", "Endungen"))
        idx = positions.get(id(entry), -1)
        if idx >= 0:
            links += [action("edit", str(idx), "&#9998;", "Edit"), action("delete", str(idx), "&#128465;", "Delete")]
        actions = "<div class='actions'>" + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(links) + "</div>" if links else ""
        cards.append(f"<div class='entry-card'><div class='head-row' dir='ltr'>{html.escape(word)} {speaker}</div>{meanings}{meta}{details}{actions}</div>")
    self.results.setHtml(css + "".join(cards)); self.results.verticalScrollBar().setValue(0)


def link_handler(original):
    def handler(self, url: QUrl) -> None:
        scheme, payload = url.scheme(), url.toString().split(":",1)[-1]
        if scheme == "conjugate":
            word = unquote(payload).strip()
            if word:
                self.tabs.setCurrentIndex(1); self.conjugation_search_box.setText(word); self.conjugation_search_box.setFocus(); self.perform_conjugation_search()
            return
        if scheme == "adjective":
            word = unquote(payload).strip()
            if word:
                self.tabs.setCurrentIndex(4); self.adj_search.setText(word); self.adj_determiner.clear()
                for combo in (self.adj_type, self.adj_case, self.adj_gender):
                    i = combo.findText("Alle")
                    if i >= 0: combo.setCurrentIndex(i)
                self.adj_search.setFocus(); self._render_adjective()
            return
        original(self, url)
    return handler


def refresh_generated(window) -> None:
    revision = getattr(window, "_meaning_generation_revision", 0)
    if revision == getattr(window, "_meaning_generation_seen_revision", 0): return
    window._meaning_generation_seen_revision = revision
    if window.search_box.text().strip(): window.perform_search()


def window_init(original):
    def init(self, settings_path: Path, settings: dict) -> None:
        path = legacy.resolve_configured_path(settings["database_path"], settings_path)
        normalize_database(path); original(self, settings_path, settings)
        icon = language_icon(); self.setWindowIcon(icon)
        app = QApplication.instance()
        if app is not None: app.setWindowIcon(icon)
        self._meaning_generation_revision = 0; self._meaning_generation_seen_revision = 0
        self._meaning_refresh_timer = legacy.QTimer(self); self._meaning_refresh_timer.setInterval(900)
        self._meaning_refresh_timer.timeout.connect(lambda: refresh_generated(self)); self._meaning_refresh_timer.start()
        self._meaning_generation_thread = threading.Thread(target=generate_missing_meanings, args=(self,), name="dictionary-meaning-generator", daemon=True)
        self._meaning_generation_thread.start()
    return init


def install() -> None:
    dictionary_core.parse_entry = enhanced_parse_entry; legacy.parse_entry = enhanced_parse_entry
    dictionary_core.DictionaryIndex.add_entry = locked_add; dictionary_core.DictionaryIndex.replace_entry = locked_replace; dictionary_core.DictionaryIndex.delete_entry = locked_delete
    legacy.DictionaryWindow._render_results = render_results
    legacy.DictionaryWindow._open_dictionary_link = link_handler(legacy.DictionaryWindow._open_dictionary_link)
    legacy.DictionaryWindow.__init__ = window_init(legacy.DictionaryWindow.__init__)


def main() -> int:
    install(); return legacy.main()

if __name__ == "__main__":
    raise SystemExit(main())
