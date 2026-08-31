from __future__ import annotations

import html
import re
from urllib.parse import quote

import app_base as base
import dictionary_core
import language_enrichment as enrichment
import language_patch_v3 as patch

FIELD_RE = re.compile(r"^([^:]{1,48}):\s*(.*)$")


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
      .speaker { text-decoration:none; font-size:12pt; margin-right:9px; vertical-align:middle; }
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
        if any(enrichment.is_missing(raw_values[label]) for label in enrichment.LANGUAGE_LABELS):
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
            f"<div class='head-row'>{speaker}<span class='headword'>{html.escape(word)}</span></div>"
            f"{meanings}{meta}{details}{actions}</div>"
        )

    self.results.setHtml(css + "".join(cards))
    self.results.verticalScrollBar().setValue(0)


def refresh_generated(window) -> None:
    revision = getattr(window, "_meaning_generation_revision", 0)
    if revision == getattr(window, "_meaning_generation_seen_revision", 0):
        return

    window._meaning_generation_seen_revision = revision
    try:
        with enrichment.DB_LOCK:
            window.index = dictionary_core.DictionaryIndex.from_file(window.database_path)
    except Exception:
        return
    window.perform_search()


def main() -> int:
    base.generate_missing_meanings = patch.generate_missing_meanings
    base.refresh_generated = refresh_generated
    base.render_results = render_results
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
