from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote, unquote

import app_base as base
import dictionary_core
import language_enrichment as enrichment
import language_patch_v4 as patch
import noun_core

FIELD_RE = re.compile(r"^([^:]{1,48}):\s*(.*)$")
PERSIAN_QUERY_RE = re.compile(r"[\u0600-\u06ff]")
ORIGINAL_INDEX_SEARCH = dictionary_core.DictionaryIndex.search
ORIGINAL_WINDOW_INIT_FACTORY = base.window_init
ORIGINAL_LINK_HANDLER_FACTORY = base.link_handler


def _exact_only_search(self, normalized_query: str, limit: int):
    scored = []
    for entry in self.entries:
        score = self._exact_score(entry, normalized_query)
        if score:
            scored.append(dictionary_core.SearchResult(entry, score))
    scored.sort(
        key=lambda result: (
            -result.score,
            result.entry.headword_norm,
            result.entry.first_line,
        )
    )
    return scored[:limit]


def fast_index_search(self, query: str, limit: int = 20, fuzzy_threshold: int = 58):
    """Keep interactive Persian/short searches cheap; reserve fuzzy matching for longer Latin queries."""
    normalized_query = dictionary_core.normalize_text(query)
    if not normalized_query:
        return [dictionary_core.SearchResult(entry, 0.0) for entry in self.entries[:limit]]

    compact_length = len(normalized_query.replace(" ", ""))
    if PERSIAN_QUERY_RE.search(query):
        if compact_length < 3:
            limit = min(limit, 8)
        return _exact_only_search(self, normalized_query, limit)

    if compact_length < 3:
        return _exact_only_search(self, normalized_query, min(limit, 12))

    return ORIGINAL_INDEX_SEARCH(
        self,
        query,
        limit=limit,
        fuzzy_threshold=fuzzy_threshold,
    )


def _detail_line(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""
    if stripped.casefold().startswith("ex:"):
        return (
            "<div class='example-line' dir='ltr'>"
            "<span class='field-label'>ex:</span> "
            + html.escape(stripped[3:].strip())
            + "</div>"
        )
    match = FIELD_RE.match(stripped)
    if match:
        return (
            "<div class='detail-line'>"
            f"<span class='field-label'>{html.escape(match.group(1))}:</span> "
            f"{html.escape(match.group(2))}</div>"
        )
    return f"<div class='detail-line'>{html.escape(stripped)}</div>"


def _action(scheme: str, payload: str, icon: str, label: str) -> str:
    return (
        f"<a class='action-link' href='{scheme}:{payload}'>"
        f"<span class='action-icon'>{icon}</span>&nbsp;{html.escape(label)}</a>"
    )


def render_results(self, entries) -> None:
    if not entries:
        self.results.setHtml(
            "<p style='font-size:14pt'><b>No matching entry found.</b></p>"
            "<p>Try fewer characters or a different spelling.</p>"
        )
        return

    positions = (
        {id(entry): index for index, entry in enumerate(self.index.entries)}
        if self.index
        else {}
    )
    css = """
    <style>
      body { font-family:sans-serif; font-size:11pt; line-height:1.62; }
      .entry-card { margin:30px 42px; padding:16px 18px; border:1px solid #b8bec7; border-radius:8px; line-height:1.62; }
      .head-row { font-size:16pt; font-weight:700; margin-bottom:13px; line-height:1.5; direction:ltr; text-align:left; }
      .speaker { text-decoration:none; font-size:12pt; vertical-align:middle; }
      .headword { vertical-align:middle; }
      .meaning-box { background:#fff7cf; border-radius:4px; padding:8px 10px; margin:5px 0; line-height:1.62; direction:ltr; text-align:left; }
      .persian-value { display:inline-block; direction:rtl; text-align:right; unicode-bidi:embed; margin-left:7px; }
      .field-label { color:#6f42c1; font-weight:700; }
      .meta-line { margin-top:9px; line-height:1.62; }
      .example-line { background:#dcecff; padding:8px 10px; margin:4px 0; line-height:1.62; }
      .detail-line { margin:7px 0; line-height:1.62; }
      .actions { margin-top:17px; font-size:9.5pt; line-height:1.9; white-space:nowrap; }
      .action-link { text-decoration:none; }
      .action-icon { font-size:9pt; font-weight:bold; }
    </style>
    """
    cards: list[str] = []

    for entry in entries:
        word = patch.clean_german_word(entry.first_line) or entry.headword.strip()
        raw_values = patch.language_values(entry.raw)
        patch.prioritize(entry.raw)
        values = {
            key: value if not enrichment.is_missing(value) else "-"
            for key, value in raw_values.items()
        }

        role = enrichment.infer_role(entry)
        ipa_match = re.search(r"\[([^\]]+)\]", entry.first_line)
        ipa = ipa_match.group(1).strip() if ipa_match else "-"

        speaker = ""
        if self.settings.get("pronunciation_enabled", True):
            speaker = (
                f"<a class='speaker' href='speak:{quote(word, safe='')}' "
                "title='German pronunciation'>&#128266;</a>"
            )
        speaker_gap = "&nbsp;&nbsp;&nbsp;" if speaker else ""

        meanings = (
            f"<div class='meaning-box'><span class='field-label'>English:</span> "
            f"{html.escape(values['English'])}</div>"
            "<div class='meaning-box'><span class='field-label'>Persian:</span> "
            f"<span class='persian-value' dir='rtl'>{html.escape(values['Persian'])}</span></div>"
            f"<div class='meaning-box'><span class='field-label'>Penglish:</span> "
            f"{html.escape(values['Penglish'])}</div>"
        )
        meta = (
            "<div class='meta-line'><span class='field-label'>Pronunciation:</span> "
            f"[{html.escape(ipa)}]</div>"
            "<div class='meta-line'><span class='field-label'>Grammatical role:</span> "
            f"{html.escape(role)}</div>"
        )
        details = "".join(
            _detail_line(line)
            for line in entry.raw.splitlines()[1:]
            if not enrichment.EXPLICIT_MEANING_RE.match(line.strip())
        )

        links: list[str] = []
        encoded = quote(word, safe="")
        if role == "verb":
            links.append(_action("conjugate", encoded, "&#8635;", "Conjugate"))
        if role == "adjective":
            links.append(_action("adjective", encoded, "&#9398;", "Endungen"))
        if role == "noun":
            links.append(_action("noun", encoded, "&#9419;", "Endungen"))

        index = positions.get(id(entry), -1)
        if index >= 0:
            links.extend(
                [
                    _action("edit", str(index), "&#9998;", "Edit"),
                    _action("delete", str(index), "&#128465;", "Delete"),
                ]
            )

        actions = (
            "<div class='actions'>"
            + "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;".join(links)
            + "</div>"
            if links
            else ""
        )
        cards.append(
            "<div class='entry-card'>"
            f"<div class='head-row'>{speaker}{speaker_gap}<span class='headword'>{html.escape(word)}</span></div>"
            f"{meanings}{meta}{details}{actions}</div>"
        )

    self.results.setHtml(css + "".join(cards))
    self.results.verticalScrollBar().setValue(0)


def _find_noun_entry(window, text: str):
    if not window.index:
        return None
    base_word, _ = noun_core.noun_and_gender(text)
    normalized = dictionary_core.normalize_text(base_word)
    if not normalized:
        return None
    for entry in window.index.entries:
        if entry.lexeme_norm == normalized and enrichment.infer_role(entry) == "noun":
            return entry
    return None


def _noun_table_html(result: dict[str, object]) -> str:
    rows = result["rows"]
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td><b>{html.escape(row['case'])}</b></td>"
            f"<td class='form'>{html.escape(row['singular'])}</td>"
            f"<td>{html.escape(row['singular_ending'])}</td>"
            f"<td class='form'>{html.escape(row['plural'])}</td>"
            f"<td>{html.escape(row['plural_ending'])}</td>"
            "</tr>"
        )
    note = str(result.get("note", "") or "")
    note_html = f"<p class='hint'><b>Hinweis:</b> {html.escape(note)}</p>" if note else ""
    source = html.escape(str(result.get("source", "")))
    return (
        base.legacy.DictionaryWindow.GRAMMAR_CSS
        + "<style>.form{font-size:12pt;font-weight:700}.source{color:#667;margin-top:8px}</style>"
        + f"<h2>{html.escape(str(result['base']))} — {html.escape(str(result['gender']))}</h2>"
        + "<p class='hint'>Die Tabelle zeigt die Nomenformen mit bestimmtem Artikel. "
          "Dictionary-Angaben für Genitiv/Plural werden bevorzugt; danach gelten Regeln und Sonderfälle.</p>"
        + "<table><thead><tr><th>Kasus</th><th>Singular</th><th>Nomenendung</th>"
          "<th>Plural</th><th>Pluraländerung</th></tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
        + note_html
        + f"<p class='source'><b>Quelle der Form:</b> {source}</p>"
    )


def _render_noun(window) -> None:
    text = window.noun_search.text().strip()
    if not text:
        window.noun_results.setHtml(
            window.GRAMMAR_CSS
            + "<p class='hint'>Nomen eingeben, z. B. <b>der Hund</b>, <b>die Gelegenheit</b>, "
              "<b>das Herz</b> oder im Dictionary auf <b>Endungen</b> klicken.</p>"
        )
        window.noun_status.setText("")
        return

    entry = _find_noun_entry(window, text)
    raw = entry.raw if entry is not None else ""
    result = noun_core.decline_noun(
        text,
        raw=raw,
        irregular_nouns=getattr(window, "irregular_nouns", {}),
    )
    window.noun_results.setHtml(_noun_table_html(result))
    if getattr(window, "irregular_noun_error", None):
        window.noun_status.setText(f"Irregular noun DB error: {window.irregular_noun_error}")
    elif entry is None:
        window.noun_status.setText(
            "Kein exakter Dictionary-Eintrag gefunden; Regel/Exception-DB verwendet."
        )
    else:
        window.noun_status.setText("Dictionary-Eintrag gefunden.")


def _install_noun_tab(window, settings_path: Path, settings: dict) -> None:
    if hasattr(window, "noun_tab"):
        return

    configured = settings.get(
        "irregular_nouns_path",
        str(Path(__file__).resolve().parent / "data" / "irregular_nouns.yaml"),
    )
    window.irregular_nouns_path = base.legacy.resolve_configured_path(configured, settings_path)
    try:
        window.irregular_nouns = noun_core.load_irregular_nouns(window.irregular_nouns_path)
        window.irregular_noun_error = None
    except (FileNotFoundError, OSError, UnicodeError, ValueError) as exc:
        window.irregular_nouns = {}
        window.irregular_noun_error = str(exc)

    tab = base.legacy.QWidget(window)
    outer = base.legacy.QVBoxLayout(tab)
    top = base.legacy.QHBoxLayout()

    window.noun_search = base.legacy.QLineEdit(tab)
    window.noun_search.setClearButtonEnabled(True)
    window.noun_search.setPlaceholderText(
        "Nomen, z. B. der Hund, die Gelegenheit, das Herz, der Name …"
    )
    window.noun_search.setAccessibleName("Noun endings search")
    top.addWidget(window.noun_search, 1)
    outer.addLayout(top)

    window.noun_results = base.legacy.QTextBrowser(tab)
    window.noun_results.setOpenExternalLinks(False)
    window.noun_results.setReadOnly(True)
    window.noun_results.setFont(base.legacy.QFont("Sans Serif", 10))
    window.noun_results.setMinimumWidth(0)
    outer.addWidget(window.noun_results, 1)

    window.noun_status = base.legacy.QLabel(tab)
    window.noun_status.setTextInteractionFlags(base.legacy.Qt.TextSelectableByMouse)
    outer.addWidget(window.noun_status)

    window.noun_tab = tab
    window.tabs.addTab(tab, "Nomenendungen")
    window.noun_search.returnPressed.connect(lambda: _render_noun(window))
    _render_noun(window)


def noun_aware_link_handler(original):
    wrapped = ORIGINAL_LINK_HANDLER_FACTORY(original)

    def handler(self, url) -> None:
        if url.scheme() == "noun":
            word = unquote(url.toString().split(":", 1)[-1]).strip()
            if word and hasattr(self, "noun_tab"):
                index = self.tabs.indexOf(self.noun_tab)
                if index >= 0:
                    self.tabs.setCurrentIndex(index)
                self.noun_search.setText(word)
                self.noun_search.setFocus()
                _render_noun(self)
            return
        wrapped(self, url)

    return handler


def refresh_generated(window, force: bool = False) -> None:
    revision = getattr(window, "_meaning_generation_revision", 0)
    if revision == getattr(window, "_meaning_generation_seen_revision", 0):
        return

    if not force and window.search_box.hasFocus():
        return

    try:
        with enrichment.DB_LOCK:
            new_index = dictionary_core.DictionaryIndex.from_file(window.database_path)
    except Exception:
        return

    window.index = new_index
    window._meaning_generation_seen_revision = revision
    window.perform_search()


def idle_window_init(original_init):
    wrapped_init = ORIGINAL_WINDOW_INIT_FACTORY(original_init)

    def init(self, settings_path, settings) -> None:
        wrapped_init(self, settings_path, settings)
        _install_noun_tab(self, settings_path, settings)
        self.search_timer.setInterval(max(220, int(settings.get("search_debounce_ms", 80))))
        self.search_box.editingFinished.connect(lambda: refresh_generated(self, force=True))
        self.search_box.returnPressed.connect(lambda: refresh_generated(self, force=True))

    return init


def main() -> int:
    dictionary_core.DictionaryIndex.search = fast_index_search
    base.generate_missing_meanings = patch.generate_missing_meanings
    base.refresh_generated = refresh_generated
    base.render_results = render_results
    base.link_handler = noun_aware_link_handler
    base.window_init = idle_window_init
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
