from __future__ import annotations

import re
import time
from pathlib import Path

import dictionary_core
import language_enrichment as legacy


def clean_german_word(raw_or_first_line: str) -> str:
    """Return only the German headword, without IPA or grammatical metadata."""
    if not raw_or_first_line:
        return ""
    first_line = raw_or_first_line.splitlines()[0].strip()
    left = first_line.split(":", 1)[0].strip()
    left = re.sub(r"\s*\[[^\]]*\].*$", "", left).strip()
    left = re.sub(r"\s*\(.*$", "", left).strip()
    return re.sub(r"\s+", " ", left).strip()


def translate_to_english(german: str) -> str:
    payload = legacy._http_json(
        [
            ("client", "gtx"),
            ("sl", "de"),
            ("tl", "en"),
            ("dt", "t"),
            ("q", german),
        ]
    )
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        return ""
    return "".join(
        item[0]
        for item in payload[0]
        if isinstance(item, list) and item and isinstance(item[0], str)
    ).strip()


def _complete_values(raw: str, values: dict[str, str]) -> tuple[dict[str, str], bool]:
    completed = dict(values)
    changed = False
    german = clean_german_word(raw)

    if legacy.is_missing(completed["English"]) and german:
        english = translate_to_english(german)
        if not legacy.is_missing(english):
            completed["English"] = english
            changed = True

    if legacy.is_missing(completed["Persian"]) and not legacy.is_missing(completed["English"]):
        persian = legacy.translate_to_persian(completed["English"])
        if not legacy.is_missing(persian):
            completed["Persian"] = persian
            changed = True

    if legacy.is_missing(completed["Penglish"]) and not legacy.is_missing(completed["Persian"]):
        penglish = legacy.romanize_persian(completed["Persian"])
        if not legacy.is_missing(penglish):
            completed["Penglish"] = penglish
            changed = True

    return completed, changed


def _apply_updates(path: Path, updates: dict[str, dict[str, str]]) -> bool:
    if not updates:
        return False

    with legacy.DB_LOCK:
        text = path.read_text(encoding="utf-8")
        entries: list[str] = []
        changed = False

        for raw in dictionary_core.split_entries(text):
            values = updates.get(legacy.entry_key(raw))
            if values is None:
                entries.append(raw.strip())
                continue
            rebuilt = legacy.set_language_fields(raw, values)
            entries.append(rebuilt)
            changed = changed or rebuilt != raw.strip()

        if not changed:
            return False

        temp = path.with_name(f".{path.name}.full-meaning-backfill.tmp")
        temp.write_text(
            "\n\n".join(entries).rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(path)
        return True


def _load_candidates(path: Path) -> list[tuple[str, str, dict[str, str]]]:
    with legacy.DB_LOCK:
        text = path.read_text(encoding="utf-8")

    candidates: list[tuple[str, str, dict[str, str]]] = []
    for raw in dictionary_core.split_entries(text):
        values = legacy.language_values(raw)
        if any(legacy.is_missing(values[label]) for label in legacy.LANGUAGE_LABELS):
            candidates.append((legacy.entry_key(raw), raw, values))
    return candidates


def generate_missing_meanings(window) -> None:
    """Keep retrying until English, Persian and Penglish are populated."""
    path = Path(window.database_path)
    retry_delay = 8.0

    while True:
        try:
            candidates = _load_candidates(path)
            window._meaning_generation_remaining = len(candidates)
            if not candidates:
                window._meaning_generation_finished = True
                return

            pending: dict[str, dict[str, str]] = {}
            failures = 0
            successes = 0

            for key, raw, values in candidates:
                try:
                    completed, changed = _complete_values(raw, values)
                except Exception:
                    failures += 1
                    continue

                if changed:
                    pending[key] = completed
                    successes += 1

                if len(pending) >= 12:
                    if _apply_updates(path, pending):
                        window._meaning_generation_revision = (
                            getattr(window, "_meaning_generation_revision", 0) + 1
                        )
                    pending.clear()

                window._meaning_generation_remaining = max(
                    0,
                    getattr(window, "_meaning_generation_remaining", 1) - 1,
                )
                time.sleep(0.08)

            if pending and _apply_updates(path, pending):
                window._meaning_generation_revision = (
                    getattr(window, "_meaning_generation_revision", 0) + 1
                )

            window._meaning_generation_last_failures = failures
            if failures == 0:
                retry_delay = 8.0
                continue

            if successes == 0:
                time.sleep(retry_delay)
                retry_delay = min(60.0, retry_delay * 1.7)
            else:
                retry_delay = 8.0
                time.sleep(2.0)
        except Exception:
            window._meaning_generation_last_failures = (
                getattr(window, "_meaning_generation_last_failures", 0) + 1
            )
            time.sleep(retry_delay)
            retry_delay = min(60.0, retry_delay * 1.7)
