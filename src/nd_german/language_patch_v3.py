from __future__ import annotations

import queue
import re
import threading
import time
from pathlib import Path

import dictionary_core
import language_enrichment as legacy

_PRIORITY_QUEUE: queue.Queue[str] = queue.Queue()
_PRIORITY_LOCK = threading.Lock()
_PRIORITY_SEEN: set[str] = set()


def clean_german_word(raw_or_first_line: str) -> str:
    """Return only the German headword, without IPA or grammatical metadata."""
    if not raw_or_first_line:
        return ""
    first_line = raw_or_first_line.splitlines()[0].strip()
    left = first_line.split(":", 1)[0].strip()
    left = re.sub(r"\s*\[[^\]]*\].*$", "", left).strip()
    left = re.sub(r"\s*\(.*$", "", left).strip()
    return re.sub(r"\s+", " ", left).strip()


def _first_line_translation(raw: str) -> str:
    """Extract the translation after the grammatical metadata, not colons inside it."""
    first_line = raw.splitlines()[0].strip() if raw else ""
    if not first_line:
        return ""

    matches = list(re.finditer(r"\)\s*:\s*", first_line))
    if matches:
        return first_line[matches[-1].end():].strip()

    matches = list(re.finditer(r"\]\s*:\s*", first_line))
    if matches:
        return first_line[matches[-1].end():].strip()

    if ":" in first_line:
        return first_line.split(":", 1)[1].strip()
    return ""


def _suspicious_english(value: str) -> bool:
    text = (value or "").casefold()
    return any(
        token in text
        for token in (
            "komparativ:",
            "superlativ:",
            "präsens:",
            "präteritum:",
            "genitiv:",
            "plural:",
            "adjektiv,",
            "akk. +",
            "dat. +",
        )
    )


def language_values(raw: str) -> dict[str, str]:
    values = legacy.language_values(raw)
    first_line_english = _first_line_translation(raw)
    if first_line_english and (
        legacy.is_missing(values["English"]) or _suspicious_english(values["English"])
    ):
        values["English"] = first_line_english
    return values


def prioritize(raw: str) -> None:
    key = legacy.entry_key(raw)
    if not key:
        return
    with _PRIORITY_LOCK:
        if key in _PRIORITY_SEEN:
            return
        _PRIORITY_SEEN.add(key)
    _PRIORITY_QUEUE.put(key)


def _drain_priority() -> list[str]:
    keys: list[str] = []
    while True:
        try:
            key = _PRIORITY_QUEUE.get_nowait()
        except queue.Empty:
            break
        keys.append(key)
    with _PRIORITY_LOCK:
        for key in keys:
            _PRIORITY_SEEN.discard(key)
    return keys


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
    original = legacy.language_values(raw)
    changed = completed != original

    if legacy.is_missing(completed["English"]):
        first_line_english = _first_line_translation(raw)
        if first_line_english:
            completed["English"] = first_line_english
            changed = True
        else:
            german = clean_german_word(raw)
            if german:
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
        values = language_values(raw)
        legacy_values = legacy.language_values(raw)
        needs_repair = values != legacy_values
        if needs_repair or any(
            legacy.is_missing(values[label]) for label in legacy.LANGUAGE_LABELS
        ):
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

            priority = _drain_priority()
            priority_order = {key: index for index, key in enumerate(priority)}
            candidates.sort(
                key=lambda item: (
                    priority_order.get(item[0], len(priority_order)),
                    0 if _suspicious_english(legacy.language_values(item[1])["English"]) else 1,
                )
            )

            batch = candidates[:12]
            updates: dict[str, dict[str, str]] = {}
            failures = 0

            for key, raw, values in batch:
                try:
                    completed, changed = _complete_values(raw, values)
                except Exception:
                    failures += 1
                    continue

                still_missing = any(
                    legacy.is_missing(completed[label]) for label in legacy.LANGUAGE_LABELS
                )
                if changed:
                    updates[key] = completed
                elif still_missing:
                    failures += 1
                time.sleep(0.08)

            if updates and _apply_updates(path, updates):
                window._meaning_generation_revision = (
                    getattr(window, "_meaning_generation_revision", 0) + 1
                )
                retry_delay = 8.0

            window._meaning_generation_last_failures = failures
            if not updates and failures:
                time.sleep(retry_delay)
                retry_delay = min(60.0, retry_delay * 1.7)
            elif failures:
                time.sleep(1.5)
            else:
                time.sleep(0.2)
        except Exception:
            window._meaning_generation_last_failures = (
                getattr(window, "_meaning_generation_last_failures", 0) + 1
            )
            time.sleep(retry_delay)
            retry_delay = min(60.0, retry_delay * 1.7)
