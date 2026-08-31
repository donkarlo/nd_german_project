from __future__ import annotations

import queue
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path

import dictionary_core
import language_enrichment as legacy
import language_patch_v3 as previous

clean_german_word = previous.clean_german_word
language_values = previous.language_values
translate_to_english = previous.translate_to_english

_PRIORITY_QUEUE: queue.Queue[str] = queue.Queue()
_PRIORITY_LOCK = threading.Lock()
_PRIORITY_SEEN: set[str] = set()

MIGRATION_NAME = ".penglish_ir_v1.done"
PROGRESS_NAME = ".penglish_ir_v1.progress"


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
            keys.append(_PRIORITY_QUEUE.get_nowait())
        except queue.Empty:
            break
    with _PRIORITY_LOCK:
        for key in keys:
            _PRIORITY_SEEN.discard(key)
    return keys


def _espeak_executable() -> str | None:
    return shutil.which("espeak-ng") or shutil.which("espeak")


def _persian_ipa(text: str) -> str:
    executable = _espeak_executable()
    if not executable:
        return ""
    ipa_flag = "--ipa=3" if Path(executable).name == "espeak-ng" else "--ipa"
    result = subprocess.run(
        [executable, "-q", ipa_flag, "-v", "fa", text],
        check=False,
        capture_output=True,
        text=True,
        timeout=5.0,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _ipa_to_iranian_penglish(ipa: str) -> str:
    text = ipa.strip()
    if not text:
        return ""

    replacements = (
        ("dʒ", "j"),
        ("tʃ", "ch"),
        ("uː", "oo"),
        ("iː", "i"),
        ("eː", "e"),
        ("oː", "o"),
        ("ɑː", "a"),
        ("ɒː", "a"),
        ("æː", "a"),
        ("ʃ", "sh"),
        ("ʒ", "zh"),
        ("x", "kh"),
        ("ɣ", "gh"),
        ("ɢ", "gh"),
        ("ʁ", "gh"),
        ("q", "gh"),
        ("ɾ", "r"),
        ("ɹ", "r"),
        ("ɽ", "r"),
        ("j", "y"),
        ("ɑ", "a"),
        ("ɒ", "a"),
        ("æ", "a"),
        ("ə", "e"),
        ("ɛ", "e"),
        ("ɪ", "i"),
        ("ʊ", "o"),
        ("ɯ", "u"),
        ("θ", "s"),
        ("ð", "z"),
        ("ħ", "h"),
        ("ʕ", ""),
        ("ʔ", ""),
        ("ˈ", ""),
        ("ˌ", ""),
        ("ː", ""),
    )
    for source, target in replacements:
        text = text.replace(source, target)

    text = re.sub(r"[^A-Za-z0-9' ;,./!?()\-]+", "", text)
    text = text.replace("'", "")
    return re.sub(r"\s+", " ", text).strip().casefold()


_FALLBACK_WORD_FIXES = {
    "mafrad": "mofrad",
    "jenob": "jonoob",
    "shmal": "shomal",
    "fanpamidan": "fahmidan",
    "garaftan": "gereftan",
    "ghtaei": "ghatei",
    "nanpehar": "nahar",
}


def _fix_fallback_iranian(text: str) -> str:
    words = re.split(r"(\W+)", text.casefold())
    return "".join(_FALLBACK_WORD_FIXES.get(word, word) for word in words).strip()


def romanize_persian_iran(text: str) -> str:
    ipa = _persian_ipa(text)
    if ipa:
        result = _ipa_to_iranian_penglish(ipa)
        if result:
            return result
    return _fix_fallback_iranian(legacy.romanize_persian(text))


def _complete_values(
    raw: str,
    values: dict[str, str],
    *,
    force_iranian_penglish: bool,
) -> tuple[dict[str, str], bool, bool]:
    completed = dict(values)
    original = legacy.language_values(raw)
    changed = completed != original

    if legacy.is_missing(completed["English"]):
        first_line_english = previous._first_line_translation(raw)
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

    iranian_done = False
    if not legacy.is_missing(completed["Persian"]) and (
        force_iranian_penglish or legacy.is_missing(completed["Penglish"])
    ):
        penglish = romanize_persian_iran(completed["Persian"])
        if not legacy.is_missing(penglish):
            iranian_done = True
            if completed.get("Penglish", "").strip().casefold() != penglish.casefold():
                completed["Penglish"] = penglish
                changed = True

    return completed, changed, iranian_done


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
        temp = path.with_name(f".{path.name}.iranian-penglish.tmp")
        temp.write_text(
            "\n\n".join(entries).rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temp.replace(path)
        return True


def _load_processed(progress_path: Path) -> set[str]:
    try:
        return {
            line.strip()
            for line in progress_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except FileNotFoundError:
        return set()


def _append_processed(progress_path: Path, keys: list[str]) -> None:
    if not keys:
        return
    with progress_path.open("a", encoding="utf-8", newline="\n") as handle:
        for key in keys:
            handle.write(key.replace("\n", " ").strip() + "\n")


def _load_candidates(
    path: Path,
    *,
    force_iranian: bool,
    processed: set[str],
) -> list[tuple[str, str, dict[str, str], bool]]:
    with legacy.DB_LOCK:
        text = path.read_text(encoding="utf-8")

    candidates: list[tuple[str, str, dict[str, str], bool]] = []
    for raw in dictionary_core.split_entries(text):
        key = legacy.entry_key(raw)
        values = language_values(raw)
        legacy_values = legacy.language_values(raw)
        needs_repair = values != legacy_values
        missing = any(legacy.is_missing(values[label]) for label in legacy.LANGUAGE_LABELS)
        needs_iranian = force_iranian and key not in processed
        if needs_repair or missing or needs_iranian:
            candidates.append((key, raw, values, needs_iranian))
    return candidates


def generate_missing_meanings(window) -> None:
    """Fill all language fields and migrate Penglish to Iranian Persian pronunciation."""
    path = Path(window.database_path)
    done_path = path.with_name(MIGRATION_NAME)
    progress_path = path.with_name(PROGRESS_NAME)
    processed = _load_processed(progress_path)
    retry_delay = 6.0

    while True:
        try:
            force_iranian = not done_path.exists()
            candidates = _load_candidates(
                path,
                force_iranian=force_iranian,
                processed=processed,
            )
            window._meaning_generation_remaining = len(candidates)

            if not candidates:
                if force_iranian:
                    done_path.write_text("iranian-penglish-v1\n", encoding="utf-8")
                    try:
                        progress_path.unlink()
                    except FileNotFoundError:
                        pass
                window._meaning_generation_finished = True
                return

            priority = _drain_priority()
            priority_order = {key: index for index, key in enumerate(priority)}
            candidates.sort(
                key=lambda item: (
                    priority_order.get(item[0], len(priority_order)),
                    0 if any(legacy.is_missing(item[2][label]) for label in legacy.LANGUAGE_LABELS) else 1,
                    0 if previous._suspicious_english(legacy.language_values(item[1])["English"]) else 1,
                )
            )

            updates: dict[str, dict[str, str]] = {}
            newly_processed: list[str] = []
            failures = 0

            first_is_missing = any(
                legacy.is_missing(candidates[0][2][label])
                for label in legacy.LANGUAGE_LABELS
            )
            batch_size = 12 if priority or first_is_missing else 60

            for key, raw, values, needs_iranian in candidates[:batch_size]:
                try:
                    completed, changed, iranian_done = _complete_values(
                        raw,
                        values,
                        force_iranian_penglish=needs_iranian,
                    )
                except Exception:
                    failures += 1
                    continue

                if changed:
                    updates[key] = completed
                if needs_iranian and iranian_done:
                    newly_processed.append(key)
                if any(legacy.is_missing(completed[label]) for label in legacy.LANGUAGE_LABELS):
                    failures += 1

                time.sleep(0.03)

            wrote = bool(updates) and _apply_updates(path, updates)
            if wrote:
                window._meaning_generation_revision = (
                    getattr(window, "_meaning_generation_revision", 0) + 1
                )

            if newly_processed:
                _append_processed(progress_path, newly_processed)
                processed.update(newly_processed)

            window._meaning_generation_last_failures = failures
            if wrote or newly_processed:
                retry_delay = 6.0
                time.sleep(0.15)
            elif failures:
                time.sleep(retry_delay)
                retry_delay = min(60.0, retry_delay * 1.6)
            else:
                time.sleep(0.5)
        except Exception:
            window._meaning_generation_last_failures = (
                getattr(window, "_meaning_generation_last_failures", 0) + 1
            )
            time.sleep(retry_delay)
            retry_delay = min(60.0, retry_delay * 1.6)
