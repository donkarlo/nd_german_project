from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import dictionary_core

LANGUAGE_LABELS = ("English", "Persian", "Penglish")
EXPLICIT_MEANING_RE = re.compile(r"^(English|Persian|Penglish)\s*:\s*(.*)$", re.I)
PERSIAN_RE = re.compile(r"[\u0600-\u06ff]")
PENGLISH_HINT_RE = re.compile(r"\b(?:kardan|shodan|dashtan|dadan|gereftan|zadan|khordan|raftan|amadan|goftan|didan|fahmidan|khastan|budan|hastan|nist|yani|baraye)\b", re.I)
TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
DB_LOCK = threading.RLock()
ORIGINAL_PARSE_ENTRY = dictionary_core.parse_entry


def is_missing(value: str | None) -> bool:
    return not value or value.strip() in {"", "-", "--", "---", "—", "–"}


def split_existing_translation(text: str) -> tuple[str, str, str]:
    value = text.strip()
    if not value:
        return "", "", ""
    chunks = [p.strip(" ;") for p in re.split(r"\s+\.\s+", value) if p.strip(" ;")]
    chunks = chunks or [value]
    english, persian, penglish = [], [], []
    for chunk in chunks:
        if PERSIAN_RE.search(chunk):
            persian.append(chunk)
        elif len(chunks) > 1 and PENGLISH_HINT_RE.search(chunk):
            penglish.append(chunk)
        else:
            english.append(chunk)
    return "; ".join(english), "; ".join(persian), "; ".join(penglish)


def language_values(raw: str) -> dict[str, str]:
    values = {label: "" for label in LANGUAGE_LABELS}
    lines = raw.splitlines()
    for line in lines[1:]:
        m = EXPLICIT_MEANING_RE.match(line.strip())
        if m:
            values[m.group(1).capitalize()] = m.group(2).strip()
    if not lines:
        return values
    try:
        translation = ORIGINAL_PARSE_ENTRY(raw).translation
    except Exception:
        translation = lines[0].split(":", 1)[1].strip() if ":" in lines[0] else ""
    en, fa, pe = split_existing_translation(translation)
    if is_missing(values["English"]): values["English"] = en
    if is_missing(values["Persian"]): values["Persian"] = fa
    if is_missing(values["Penglish"]): values["Penglish"] = pe
    return values


def set_language_fields(raw: str, values: dict[str, str]) -> str:
    lines = raw.splitlines()
    if not lines:
        return raw
    retained = [line for line in lines[1:] if not EXPLICIT_MEANING_RE.match(line.strip())]
    fields = [f"{label}: {values.get(label, '').strip() or '-'}" for label in LANGUAGE_LABELS]
    return "\n".join([lines[0], *fields, *retained]).strip()


def normalize_database(path: Path) -> None:
    if not path.exists():
        return
    with DB_LOCK:
        text = path.read_text(encoding="utf-8")
        entries, changed = [], False
        for raw in dictionary_core.split_entries(text):
            rebuilt = set_language_fields(raw, language_values(raw))
            entries.append(rebuilt)
            changed = changed or rebuilt != raw.strip()
        if not changed:
            return
        temp = path.with_name(f".{path.name}.language.tmp")
        temp.write_text("\n\n".join(entries).rstrip() + "\n", encoding="utf-8", newline="\n")
        temp.replace(path)


def _http_json(params: list[tuple[str, str]], timeout: float = 7.0):
    req = Request(
        f"{TRANSLATE_ENDPOINT}?{urlencode(params)}",
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"},
    )
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read(1_000_000).decode("utf-8"))


def translate_to_persian(text: str) -> str:
    payload = _http_json([("client", "gtx"), ("sl", "en"), ("tl", "fa"), ("dt", "t"), ("q", text)])
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        return ""
    return "".join(item[0] for item in payload[0] if isinstance(item, list) and item and isinstance(item[0], str)).strip()


def _ascii_romanization(text: str) -> str:
    replacements = {"š":"sh","č":"ch","ž":"zh","ḵ":"kh","ġ":"gh","ğ":"gh","ā":"a","ī":"i","ū":"u","ḥ":"h","ʿ":"'","ʾ":"'"}
    for src, dst in replacements.items():
        text = text.replace(src, dst).replace(src.upper(), dst.upper())
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).strip()


def _fallback_penglish(text: str) -> str:
    m = {"آ":"a","ا":"a","ب":"b","پ":"p","ت":"t","ث":"s","ج":"j","چ":"ch","ح":"h","خ":"kh","د":"d","ذ":"z","ر":"r","ز":"z","ژ":"zh","س":"s","ش":"sh","ص":"s","ض":"z","ط":"t","ظ":"z","ع":"'","غ":"gh","ف":"f","ق":"gh","ک":"k","ك":"k","گ":"g","ل":"l","م":"m","ن":"n","و":"v","ه":"h","ی":"y","ي":"y","ئ":"y","ؤ":"o","ء":"'","‌":" ","ـ":""}
    return re.sub(r"\s+", " ", "".join(m.get(ch, ch) for ch in text)).strip()


def romanize_persian(text: str) -> str:
    payload = _http_json([("client","gtx"),("sl","fa"),("tl","en"),("dt","t"),("dt","rm"),("q",text)])
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        for item in reversed(payload[0]):
            if isinstance(item, list):
                strings = [x.strip() for x in item if isinstance(x, str) and x.strip()]
                for candidate in reversed(strings):
                    if not PERSIAN_RE.search(candidate) and candidate.casefold() != text.casefold():
                        return _ascii_romanization(candidate)
    return _fallback_penglish(text)


def entry_key(raw: str) -> str:
    lines = raw.splitlines()
    return lines[0].strip() if lines else ""


def apply_updates(path: Path, updates: dict[str, tuple[str, str]]) -> bool:
    if not updates:
        return False
    with DB_LOCK:
        text = path.read_text(encoding="utf-8")
        entries, changed = [], False
        for raw in dictionary_core.split_entries(text):
            update = updates.get(entry_key(raw))
            if not update:
                entries.append(raw.strip()); continue
            values = language_values(raw)
            fa, pe = update
            if is_missing(values["Persian"]) and not is_missing(fa): values["Persian"] = fa
            if is_missing(values["Penglish"]) and not is_missing(pe): values["Penglish"] = pe
            rebuilt = set_language_fields(raw, values)
            entries.append(rebuilt); changed = changed or rebuilt != raw.strip()
        if not changed:
            return False
        temp = path.with_name(f".{path.name}.generated.tmp")
        temp.write_text("\n\n".join(entries).rstrip() + "\n", encoding="utf-8", newline="\n")
        temp.replace(path)
        return True


def generate_missing_meanings(window) -> None:
    path = Path(window.database_path)
    try:
        with DB_LOCK:
            text = path.read_text(encoding="utf-8")
        candidates = []
        for raw in dictionary_core.split_entries(text):
            values = language_values(raw)
            if not is_missing(values["English"]) and (is_missing(values["Persian"]) or is_missing(values["Penglish"])):
                candidates.append((entry_key(raw), values))
        pending, failures = {}, 0
        for key, values in candidates:
            fa, pe = values["Persian"], values["Penglish"]
            try:
                if is_missing(fa): fa = translate_to_persian(values["English"])
                if is_missing(pe) and not is_missing(fa): pe = romanize_persian(fa)
            except Exception:
                failures += 1
                if failures >= 8: break
                continue
            failures = 0
            pending[key] = (fa, pe)
            if len(pending) >= 16:
                if apply_updates(path, pending):
                    window.index = dictionary_core.DictionaryIndex.from_file(path)
                    window._meaning_generation_revision = getattr(window, "_meaning_generation_revision", 0) + 1
                pending.clear()
            time.sleep(0.12)
        if pending and apply_updates(path, pending):
            window.index = dictionary_core.DictionaryIndex.from_file(path)
            window._meaning_generation_revision = getattr(window, "_meaning_generation_revision", 0) + 1
    except Exception:
        return


def infer_role(entry) -> str:
    role = (entry.role or "").strip().casefold()
    if role not in {"", "unknown", "other"}:
        return entry.role
    raw_cf, head = entry.raw.casefold(), entry.headword.strip()
    head_cf, trans = head.casefold(), entry.translation.strip().casefold()
    lexeme = re.sub(r"^(?:der|die|das|ein|eine)\s+", "", head_cf).strip()
    if "genitiv:" in raw_cf or "plural:" in raw_cf or (head[:1].isupper() and " " not in head): return "noun"
    if any(x in raw_cf for x in ("präsens:","prasens:","präteritum:","prateritum:","perfekt:","futur i:","konjunktiv i:","konjunktiv ii:")): return "verb"
    if trans.startswith("to ") or (lexeme.split()[0] if lexeme else "").endswith(("en","eln","ern")) or head_cf.startswith("sich "): return "verb"
    if any(x in raw_cf for x in ("adjektiv","komparativ:","superlativ:","attributiv verwendbar","prädikativ","steigerbar")): return "adjective"
    examples = "\n".join(line[3:].strip() for line in entry.raw.splitlines() if line.strip().casefold().startswith("ex:")).casefold()
    if lexeme and re.search(rf"(?<!\w){re.escape(lexeme)}(?:e|en|er|es|em)(?!\w)", examples): return "adjective"
    if lexeme.endswith(("ig","lich","isch","bar","sam","los","voll","haft","end","nd")): return "adjective"
    n = dictionary_core.normalize_text(head)
    if n in {"ich","du","er","sie","es","wir","ihr","man","jemand","niemand","etwas","nichts","wer","was"}: return "pronoun"
    if n in {"aber","als","dass","denn","oder","und","weil","wenn","obwohl","damit"}: return "conjunction"
    if n in {"an","auf","aus","bei","durch","gegen","in","mit","nach","ohne","seit","um","unter","von","vor","zu","zwischen"}: return "preposition"
    if trans.endswith("ly"): return "adverb"
    if len(head.split()) > 1: return "phrase"
    return "word"


def enhanced_parse_entry(raw: str):
    entry = ORIGINAL_PARSE_ENTRY(raw)
    role = infer_role(entry)
    return entry if role == entry.role else replace(entry, role=role)
