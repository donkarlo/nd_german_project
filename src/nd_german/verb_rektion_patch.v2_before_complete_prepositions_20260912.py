from __future__ import annotations

import html
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import dictionary_core


SCHEMA_VERSION = "2"
META_SCHEMA_KEY = "verb_rektion_schema_version"
META_COUNT_KEY = "verb_rektion_migrated_entries"
META_DIRTY_KEY = "verb_rektion_dirty"

CASE_ROWS = (
    ("NOM", "Nominativ"),
    ("AKK", "Akkusativ"),
    ("DAT", "Dativ"),
    ("GEN", "Genitiv"),
    ("UNK", "Unbestimmt"),
)
ROLE_ROWS = (
    ("direct_object", "Akkusativobjekt"),
    ("dative_object", "Dativobjekt"),
    ("genitive_object", "Genitivobjekt"),
    ("prepositional", "Präpositionalergänzung"),
    ("reflexive", "Reflexivergänzung"),
    ("predicate", "Prädikativ"),
    ("clause", "Satzergänzung"),
    ("infinitive", "Infinitivergänzung"),
    ("complement", "Ergänzung"),
)
PREPOSITIONS = (
    "an", "auf", "aus", "bei", "durch", "für", "gegen", "gegenüber", "in",
    "mit", "nach", "ohne", "über", "um", "unter", "von", "vor", "zu", "zwischen",
)

REKTION_LINE_RE = re.compile(
    r"^\s*Rektion(?:\s+\d+)?(?:\s*\[(?P<sense>[^\]]+)\])?\s*:\s*(?P<value>.*?)\s*$",
    re.IGNORECASE,
)
CASE_RE = re.compile(
    r"(?<![\w])(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?![\w])",
    re.IGNORECASE,
)
PREP_CASE_RE = re.compile(
    r"(?<![\w])(?P<prep>an|auf|aus|bei|durch|für|gegen|gegenüber|in|mit|nach|ohne|über|um|unter|von|vor|zu|zwischen)\s*\+\s*"
    r"(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?![\w])",
    re.IGNORECASE,
)
NATURAL_SLOT_RE = re.compile(
    r"(?:(?P<prep>an|auf|aus|bei|durch|für|gegen|gegenüber|in|mit|nach|ohne|über|um|unter|von|vor|zu|zwischen)\s+)?"
    r"(?P<placeholder>jemanden/etwas|jemandem/etwas|jemandes/einer\s+Sache|jemand/etwas|jemanden|jemandem|jemandes|jemand|etwas|jdn\.?|jdm\.?|etw\.?)"
    r"\s*\[\s*(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?\s*\]",
    re.IGNORECASE,
)
REFLEXIVE_SLOT_RE = re.compile(
    r"\bsich\s*\[\s*(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?|\?)(?:\.)?\s*\]",
    re.IGNORECASE,
)
JDN_RE = re.compile(r"\b(?:jdn|jmdn|jemanden)(?:\.)?\b", re.IGNORECASE)
JDM_RE = re.compile(r"\b(?:jdm|jemandem)(?:\.)?\b", re.IGNORECASE)
ETW_CASE_RE = re.compile(
    r"\betw(?:as)?(?:\.)?\s*(?:\[\s*)?(Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?:\s*\])?",
    re.IGNORECASE,
)
ALT_PLACEHOLDER_CASE_RE = re.compile(
    r"\b(?P<person>jdn|jmdn|jemanden|jdm|jemandem)(?:\.)?\s*/\s*"
    r"(?P<thing>etw|etwas)(?:\.)?\s*(?:\[\s*)?"
    r"(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?:\s*\])?",
    re.IGNORECASE,
)
CLAUSE_RE = re.compile(r"\b(dass|ob|wenn|als|wie|warum|wer|was|wo|wann|w)-?Satz\b", re.IGNORECASE)
INFINITIVE_RE = re.compile(r"\bzu\s*\+\s*Infinitiv\b|\bInfinitiv\s+mit\s+zu\b", re.IGNORECASE)
GRAMMAR_MARKER_RE = re.compile(
    r"\b(transitiv|intransitiv|reflexiv|trennbar|untrennbar|nicht\s+trennbar|verb)\b",
    re.IGNORECASE,
)
TENSE_MARKER_RE = re.compile(
    r"(?im)^\s*(Präsens|Präteritum|Perfekt|Futur\s+I|Konjunktiv\s+[Ii]{1,2})\s*:",
)
INFINITIVE_TOKEN_RE = re.compile(r"^[a-zäöüß][a-zäöüß-]*(?:en|eln|ern)$", re.IGNORECASE)
LEGACY_V1_RE = re.compile(r"^\s*(?:Nom(?:inativ)?)(?:\s*[·+]\s*.*)?$", re.IGNORECASE)


@dataclass(frozen=True)
class ArgumentSpec:
    role: str
    case_code: str | None = None
    preposition: str | None = None
    placeholder: str | None = None
    required: bool = True
    reflexive: bool = False
    complementizer: str | None = None
    infinitive_marker: str | None = None

    @property
    def display(self) -> str:
        if self.role == "clause":
            return self.placeholder or (f"{self.complementizer}-Satz" if self.complementizer else "Satz")
        if self.role == "infinitive":
            return self.placeholder or self.infinitive_marker or "zu + Infinitiv"
        if self.role == "complement" and self.case_code in (None, "UNK"):
            return self.placeholder or "?"

        case = _display_case(self.case_code or "UNK")
        if self.reflexive or self.role == "reflexive":
            core = f"sich [{case}]"
        else:
            placeholder = self.placeholder or _default_placeholder(self.case_code, self.role)
            core = f"{placeholder} [{case}]"
            if self.preposition:
                core = f"{self.preposition} {core}"
        return core if self.required else f"({core})"


@dataclass(frozen=True)
class PatternSpec:
    arguments: tuple[ArgumentSpec, ...]
    source: str
    confidence: float
    sense_label: str | None = None

    @property
    def display(self) -> str:
        return " + ".join(arg.display for arg in self.arguments) if self.arguments else "?"


def _display_case(code: str) -> str:
    return {"NOM": "Nom.", "AKK": "Akk.", "DAT": "Dat.", "GEN": "Gen.", "UNK": "?"}.get(code.upper(), "?")


def _case_code(text: str) -> str:
    value = text.casefold().rstrip(".")
    if value.startswith("nom"):
        return "NOM"
    if value.startswith("akk"):
        return "AKK"
    if value.startswith("dat"):
        return "DAT"
    if value.startswith("gen"):
        return "GEN"
    return "UNK"


def _default_placeholder(case_code: str | None, role: str = "") -> str:
    code = (case_code or "UNK").upper()
    if code == "AKK":
        return "jemanden/etwas"
    if code == "DAT":
        return "jemandem/etwas"
    if code == "GEN":
        return "jemandes/einer Sache"
    if code == "NOM":
        return "jemand/etwas"
    if role == "reflexive":
        return "sich"
    return "?"


def _prepositional_placeholder(preposition: str, case_code: str) -> str:
    """Return a neutral but idiomatic placeholder for compact Prep + Kasus notation."""
    prep = preposition.casefold()
    code = case_code.upper()
    if code == "DAT":
        if prep in {"mit", "von", "bei", "zu", "gegenüber"}:
            return "jemandem/etwas"
        return "etwas"
    if code == "AKK":
        if prep == "um":
            return "etwas"
        return "jemanden/etwas"
    if code == "GEN":
        return "etwas"
    return _default_placeholder(code)


def _role_for(case_code: str | None, *, prep: str | None = None, reflexive: bool = False) -> str:
    if prep:
        return "prepositional"
    if reflexive:
        return "reflexive"
    return {
        "AKK": "direct_object",
        "DAT": "dative_object",
        "GEN": "genitive_object",
        "NOM": "predicate",
    }.get(case_code or "UNK", "complement")


def _entry_key(role: str, headword_norm: str) -> str:
    return f"{role}|{headword_norm}"


def _is_verbish(role: str, headword: str, raw: str, first_line: str) -> bool:
    if role == "verb":
        return True
    if role != "phrase":
        return False
    if TENSE_MARKER_RE.search(raw) or GRAMMAR_MARKER_RE.search(first_line):
        return True
    head = headword.strip()
    if head.casefold().startswith("sich "):
        return True
    words = head.split()
    if not words:
        return False
    last = re.sub(r"[^A-Za-zÄÖÜäöüß-]", "", words[-1])
    return bool(last and last[:1].islower() and INFINITIVE_TOKEN_RE.match(last))


def _candidate_annotation(first_line: str) -> str:
    candidates: list[str] = []
    for value in re.findall(r"\(([^()]*)\)", first_line):
        if CASE_RE.search(value) or PREP_CASE_RE.search(value) or JDN_RE.search(value) or JDM_RE.search(value) or CLAUSE_RE.search(value) or INFINITIVE_RE.search(value):
            candidates.append(value)
    if candidates:
        return " + ".join(candidates)
    before_colon = first_line.split(":", 1)[0]
    if CASE_RE.search(before_colon) or PREP_CASE_RE.search(before_colon) or JDN_RE.search(before_colon) or JDM_RE.search(before_colon):
        return before_colon
    return ""


def _inside_parentheses(text: str, start: int, end: int) -> bool:
    left = text.rfind("(", 0, start)
    right = text.find(")", end)
    if left < 0 or right < 0:
        return False
    close_before = text.rfind(")", 0, start)
    open_after = text.find("(", end)
    return left > close_before and (open_after < 0 or right < open_after)


def _append_unique(found: list[tuple[int, int, ArgumentSpec]], occupied: list[tuple[int, int]], span: tuple[int, int], arg: ArgumentSpec) -> None:
    start, end = span
    if any(start < other_end and end > other_start for other_start, other_end in occupied):
        return
    occupied.append((start, end))
    found.append((start, end, arg))


def _normalize_placeholder(value: str, case_code: str) -> str:
    v = value.strip().casefold().rstrip(".")
    if v in {"jdn", "jmdn"}:
        return "jemanden"
    if v in {"jdm"}:
        return "jemandem"
    if v in {"etw"}:
        return "etwas"
    return value.strip().rstrip(".")


def _parse_pattern_text(text: str, *, first_line: str, headword: str, sense_label: str | None = None) -> PatternSpec:
    cleaned = text.strip()
    lowered = f"{first_line} {headword}".casefold()
    reflexive_entry = "reflexiv" in lowered or headword.casefold().startswith("sich ")
    transitive = "transitiv" in lowered and "intransitiv" not in lowered
    intransitive = "intransitiv" in lowered

    found: list[tuple[int, int, ArgumentSpec]] = []
    occupied: list[tuple[int, int]] = []

    # Natural canonical notation, e.g. "mit jemandem [Dat.]".
    for match in NATURAL_SLOT_RE.finditer(cleaned):
        code = _case_code(match.group("case"))
        prep = match.group("prep")
        placeholder = _normalize_placeholder(match.group("placeholder"), code)
        arg = ArgumentSpec(
            role=_role_for(code, prep=prep),
            case_code=code,
            preposition=prep.casefold() if prep else None,
            placeholder=placeholder,
            required=not _inside_parentheses(cleaned, *match.span()),
        )
        _append_unique(found, occupied, match.span(), arg)

    for match in REFLEXIVE_SLOT_RE.finditer(cleaned):
        code = _case_code(match.group("case")) if match.group("case") != "?" else "UNK"
        arg = ArgumentSpec(
            role="reflexive", case_code=code, placeholder="sich", reflexive=True,
            required=not _inside_parentheses(cleaned, *match.span()),
        )
        _append_unique(found, occupied, match.span(), arg)

    # Clause complements.
    for match in CLAUSE_RE.finditer(cleaned):
        token = match.group(1).casefold()
        label = "W-Satz" if token == "w" else f"{token}-Satz"
        _append_unique(
            found, occupied, match.span(),
            ArgumentSpec("clause", placeholder=label, complementizer=token, required=not _inside_parentheses(cleaned, *match.span())),
        )

    for match in INFINITIVE_RE.finditer(cleaned):
        _append_unique(
            found, occupied, match.span(),
            ArgumentSpec("infinitive", placeholder="zu + Infinitiv", infinitive_marker="zu", required=not _inside_parentheses(cleaned, *match.span())),
        )

    # Old compact notation, e.g. "mit + Dat." or "Akk. + um + Akk.".
    for match in PREP_CASE_RE.finditer(cleaned):
        code = _case_code(match.group("case"))
        prep = match.group("prep").casefold()
        _append_unique(
            found, occupied, match.span(),
            ArgumentSpec(_role_for(code, prep=prep), code, prep, _prepositional_placeholder(prep, code), not _inside_parentheses(cleaned, *match.span())),
        )

    # Alternative person/thing shorthand, e.g. jdn./etw.Akk, is one slot.
    for match in ALT_PLACEHOLDER_CASE_RE.finditer(cleaned):
        code = _case_code(match.group("case"))
        placeholder = {
            "AKK": "jemanden/etwas",
            "DAT": "jemandem/etwas",
            "GEN": "jemandes/einer Sache",
            "NOM": "jemand/etwas",
        }.get(code, "?")
        _append_unique(
            found, occupied, match.span(),
            ArgumentSpec(_role_for(code), code, placeholder=placeholder),
        )

    for match in ETW_CASE_RE.finditer(cleaned):
        code = _case_code(match.group(1))
        _append_unique(found, occupied, match.span(), ArgumentSpec(_role_for(code), code, placeholder="etwas"))
    for match in JDN_RE.finditer(cleaned):
        _append_unique(found, occupied, match.span(), ArgumentSpec("direct_object", "AKK", placeholder="jemanden"))
    for match in JDM_RE.finditer(cleaned):
        _append_unique(found, occupied, match.span(), ArgumentSpec("dative_object", "DAT", placeholder="jemandem"))

    for match in CASE_RE.finditer(cleaned):
        code = _case_code(match.group("case"))
        _append_unique(
            found, occupied, match.span(),
            ArgumentSpec(_role_for(code, reflexive=reflexive_entry and not found), code, placeholder=_default_placeholder(code), reflexive=reflexive_entry and not found),
        )

    found.sort(key=lambda item: item[0])
    args = [item[2] for item in found]

    # If the lexical entry is reflexive but the source only annotated another
    # complement (e.g. "sich erinnern (an + Akk.)"), keep the reflexive slot visible.
    # Its case stays unknown unless the source explicitly states it.
    inferred_reflexive_case = False
    if reflexive_entry and args and not any(a.role == "reflexive" or a.reflexive for a in args):
        # Standard reflexive-case heuristic: Akkusativ unless another direct
        # Akkusativobjekt occupies that slot, in which case the reflexive pronoun is Dativ.
        reflexive_case = "DAT" if any(a.role == "direct_object" and a.case_code == "AKK" for a in args) else "AKK"
        args.insert(0, ArgumentSpec("reflexive", reflexive_case, placeholder="sich", reflexive=True))
        inferred_reflexive_case = True

    # Slash notation in old data denotes alternatives in one slot rather than two objects.
    if "/" in cleaned and len(args) > 1:
        collapsed: list[ArgumentSpec] = []
        seen: set[tuple[str | None, str | None, str]] = set()
        for arg in args:
            key = (arg.case_code, arg.preposition, arg.role)
            if key in seen and arg.preposition is None:
                continue
            seen.add(key)
            collapsed.append(arg)
        args = collapsed

    # Bare Dat + Akk is conventionally easier to scan in recipient + theme order.
    if (
        len(args) == 2
        and {a.case_code for a in args} == {"DAT", "AKK"}
        and all(a.preposition is None and a.role not in {"reflexive", "predicate"} for a in args)
    ):
        dat_arg = next(a for a in args if a.case_code == "DAT")
        akk_arg = next(a for a in args if a.case_code == "AKK")
        dat_arg = ArgumentSpec(**{**dat_arg.__dict__, "placeholder": "jemandem"})
        akk_arg = ArgumentSpec(**{**akk_arg.__dict__, "placeholder": "etwas"})
        args = [dat_arg, akk_arg]

    # Common compact frame "Akk. + um + Akk." (e.g. bitten):
    # person in the direct slot, requested matter in the um-complement.
    if (
        len(args) == 2
        and args[0].case_code == "AKK" and args[0].preposition is None
        and args[1].case_code == "AKK" and args[1].preposition == "um"
    ):
        args = [
            ArgumentSpec(**{**args[0].__dict__, "placeholder": "jemanden"}),
            ArgumentSpec(**{**args[1].__dict__, "placeholder": "etwas"}),
        ]

    inferred_source: str | None = None
    inferred_confidence: float | None = None
    if not args:
        norm_head = dictionary_core.normalize_text(headword)
        head_lower = headword.casefold().strip()
        article_cases = {
            "einen": "AKK", "eine": "AKK", "einem": "DAT", "einer": "DAT",
            "eines": "GEN", "dem": "DAT", "des": "GEN",
        }
        words = head_lower.split()
        first_word = words[0] if words else ""
        if role := ("predicate" if norm_head in {"sein", "werden", "bleiben"} else None):
            args.append(ArgumentSpec(role, "NOM", placeholder="jemand/etwas"))
            inferred_source, inferred_confidence = "lexical", 0.98
        elif len(words) >= 2 and first_word in article_cases:
            code = article_cases[first_word]
            original_words = headword.strip().split()
            fixed_words = original_words[:-1] if original_words and INFINITIVE_TOKEN_RE.match(words[-1]) else original_words
            fixed = " ".join(fixed_words)
            args.append(ArgumentSpec(_role_for(code), code, placeholder=fixed))
            inferred_source, inferred_confidence = "phrase-form", 0.88
        elif transitive:
            args.append(ArgumentSpec("direct_object", "AKK", placeholder="jemanden/etwas"))
            inferred_source, inferred_confidence = "grammar-marker", 0.76
        elif reflexive_entry:
            args.append(ArgumentSpec("reflexive", "UNK", placeholder="sich", reflexive=True))
            inferred_source, inferred_confidence = "grammar-marker", 0.65
        elif intransitive:
            # "intransitiv" only tells us that there is no direct Akkusativobjekt;
            # it does not rule out a prepositional complement, so do not invent one.
            args.append(ArgumentSpec("complement", "UNK", placeholder="?"))
            inferred_source, inferred_confidence = "unknown", 0.35
        else:
            args.append(ArgumentSpec("complement", "UNK", placeholder="?"))
            inferred_source, inferred_confidence = "unknown", 0.30

    confidence = 1.0 if cleaned else (inferred_confidence if inferred_confidence is not None else 0.35)
    if inferred_reflexive_case:
        confidence = min(confidence, 0.88)
    source = "explicit" if cleaned else (inferred_source or "unknown")
    return PatternSpec(tuple(args), source, confidence, sense_label=sense_label)


def _looks_like_legacy_v1(value: str) -> bool:
    value = value.strip()
    return bool(LEGACY_V1_RE.match(value))


def _patterns_for_entry(raw: str, first_line: str, headword: str) -> list[PatternSpec]:
    explicit: list[tuple[str | None, str]] = []
    legacy: list[str] = []
    for line in raw.splitlines():
        match = REKTION_LINE_RE.match(line)
        if not match:
            continue
        value = match.group("value").strip()
        if not value:
            continue
        if _looks_like_legacy_v1(value):
            legacy.append(value)
        else:
            explicit.append((match.group("sense"), value))

    if explicit:
        return [_parse_pattern_text(value, first_line=first_line, headword=headword, sense_label=sense) for sense, value in explicit]

    annotation = _candidate_annotation(first_line)
    if annotation:
        return [_parse_pattern_text(annotation, first_line=first_line, headword=headword)]

    # Fall back to useful content from v1-generated lines after removing the subject Nom.
    # Keep every old line: separate lines represent alternative patterns.
    migrated_legacy: list[PatternSpec] = []
    for value in legacy:
        stripped = re.sub(r"^\s*Nom(?:inativ)?\.?\s*(?:[·+]\s*)?", "", value, flags=re.IGNORECASE).strip()
        if stripped and stripped.casefold() not in {"nom", "nominativ"}:
            migrated_legacy.append(_parse_pattern_text(stripped, first_line=first_line, headword=headword))
    if migrated_legacy:
        return migrated_legacy

    return [_parse_pattern_text("", first_line=first_line, headword=headword)]


def _canonical_rektion_raw(raw: str, patterns: Iterable[PatternSpec]) -> str:
    lines = [line.rstrip() for line in raw.strip().splitlines()]
    lines = [line for line in lines if not REKTION_LINE_RE.match(line)]
    patterns = [pattern for pattern in patterns if pattern.display.strip()]
    if not patterns:
        return "\n".join(lines).strip()

    insertion = 1 if lines else 0
    for index, line in enumerate(lines[1:], start=1):
        label = line.split(":", 1)[0].strip().casefold() if ":" in line else ""
        if label in {"english", "persian", "penglish"}:
            insertion = index + 1
        elif insertion > 1:
            break

    rendered: list[str] = []
    for index, pattern in enumerate(patterns):
        label = "Rektion" if index == 0 else f"Rektion {index + 1}"
        if pattern.sense_label:
            label += f" [{pattern.sense_label}]"
        rendered.append(f"{label}: {pattern.display}")
    lines[insertion:insertion] = rendered
    return "\n".join(lines).strip()


def _meta(connection: sqlite3.Connection) -> None:
    connection.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")


def _drop_derived_tables(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TRIGGER IF EXISTS trg_rektion_entries_insert")
    connection.execute("DROP TRIGGER IF EXISTS trg_rektion_entries_update")
    connection.execute("DROP TRIGGER IF EXISTS trg_rektion_entries_delete")
    connection.execute("DROP TABLE IF EXISTS verb_valency_arguments")
    connection.execute("DROP TABLE IF EXISTS verb_valency_patterns")
    connection.execute("DROP TABLE IF EXISTS verb_valency_entries")
    connection.execute("DROP TABLE IF EXISTS verb_argument_roles")


def _schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    _meta(connection)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS grammatical_cases (
            case_id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            label_de TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS verb_argument_roles (
            role_id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            label_de TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS prepositions (
            preposition_id INTEGER PRIMARY KEY,
            lemma TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS verb_valency_entries (
            entry_key TEXT PRIMARY KEY,
            headword_norm TEXT NOT NULL,
            headword TEXT NOT NULL,
            dictionary_role TEXT NOT NULL,
            entry_index_snapshot INTEGER NOT NULL,
            is_phrase INTEGER NOT NULL CHECK(is_phrase IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS verb_valency_patterns (
            pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_key TEXT NOT NULL REFERENCES verb_valency_entries(entry_key) ON DELETE CASCADE,
            pattern_order INTEGER NOT NULL,
            sense_label TEXT,
            display_text TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            UNIQUE(entry_key, pattern_order)
        );
        CREATE TABLE IF NOT EXISTS verb_valency_arguments (
            argument_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_id INTEGER NOT NULL REFERENCES verb_valency_patterns(pattern_id) ON DELETE CASCADE,
            argument_order INTEGER NOT NULL,
            role_id INTEGER NOT NULL REFERENCES verb_argument_roles(role_id),
            case_id INTEGER REFERENCES grammatical_cases(case_id),
            preposition_id INTEGER REFERENCES prepositions(preposition_id),
            placeholder TEXT,
            required INTEGER NOT NULL DEFAULT 1 CHECK(required IN (0,1)),
            reflexive INTEGER NOT NULL DEFAULT 0 CHECK(reflexive IN (0,1)),
            complementizer TEXT,
            infinitive_marker TEXT,
            UNIQUE(pattern_id, argument_order)
        );
        CREATE INDEX IF NOT EXISTS idx_vve_headword_norm ON verb_valency_entries(headword_norm);
        CREATE INDEX IF NOT EXISTS idx_vvp_entry_key ON verb_valency_patterns(entry_key, pattern_order);
        CREATE INDEX IF NOT EXISTS idx_vva_pattern ON verb_valency_arguments(pattern_id, argument_order);
        """
    )
    connection.executemany("INSERT OR IGNORE INTO grammatical_cases(code, label_de) VALUES (?, ?)", CASE_ROWS)
    connection.executemany("INSERT OR IGNORE INTO verb_argument_roles(code, label_de) VALUES (?, ?)", ROLE_ROWS)
    connection.executemany("INSERT OR IGNORE INTO prepositions(lemma) VALUES (?)", ((value,) for value in PREPOSITIONS))
    connection.executescript(
        f"""
        CREATE TRIGGER IF NOT EXISTS trg_rektion_entries_insert AFTER INSERT ON entries BEGIN
            INSERT OR REPLACE INTO meta(key,value) VALUES ('{META_DIRTY_KEY}','1');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_rektion_entries_update AFTER UPDATE OF raw,first_line,headword,role,headword_norm ON entries BEGIN
            INSERT OR REPLACE INTO meta(key,value) VALUES ('{META_DIRTY_KEY}','1');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_rektion_entries_delete AFTER DELETE ON entries BEGIN
            INSERT OR REPLACE INTO meta(key,value) VALUES ('{META_DIRTY_KEY}','1');
        END;
        """
    )


def _lookup_id(connection: sqlite3.Connection, table: str, id_column: str, key_column: str, value: str) -> int:
    row = connection.execute(f"SELECT {id_column} FROM {table} WHERE {key_column} = ?", (value,)).fetchone()
    if row is None:
        raise RuntimeError(f"Missing lookup {table}.{key_column}={value!r}")
    return int(row[0])


def _replace_valency(connection: sqlite3.Connection, *, entry_index: int, headword: str, headword_norm: str, role: str, patterns: list[PatternSpec]) -> str:
    key = _entry_key(role, headword_norm)
    connection.execute(
        """
        INSERT INTO verb_valency_entries(entry_key,headword_norm,headword,dictionary_role,entry_index_snapshot,is_phrase)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(entry_key) DO UPDATE SET
          headword_norm=excluded.headword_norm, headword=excluded.headword,
          dictionary_role=excluded.dictionary_role, entry_index_snapshot=excluded.entry_index_snapshot,
          is_phrase=excluded.is_phrase
        """,
        (key, headword_norm, headword, role, entry_index, 1 if role == "phrase" else 0),
    )
    connection.execute("DELETE FROM verb_valency_patterns WHERE entry_key = ?", (key,))
    for order, pattern in enumerate(patterns):
        cursor = connection.execute(
            """
            INSERT INTO verb_valency_patterns(entry_key,pattern_order,sense_label,display_text,source,confidence)
            VALUES (?,?,?,?,?,?)
            """,
            (key, order, pattern.sense_label, pattern.display, pattern.source, pattern.confidence),
        )
        pattern_id = int(cursor.lastrowid)
        for argument_order, argument in enumerate(pattern.arguments):
            role_id = _lookup_id(connection, "verb_argument_roles", "role_id", "code", argument.role)
            case_id = None
            if argument.case_code:
                case_id = _lookup_id(connection, "grammatical_cases", "case_id", "code", argument.case_code)
            prep_id = None
            if argument.preposition:
                prep_id = _lookup_id(connection, "prepositions", "preposition_id", "lemma", argument.preposition)
            connection.execute(
                """
                INSERT INTO verb_valency_arguments(
                  pattern_id,argument_order,role_id,case_id,preposition_id,placeholder,required,reflexive,complementizer,infinitive_marker
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    pattern_id, argument_order, role_id, case_id, prep_id, argument.placeholder,
                    1 if argument.required else 0, 1 if argument.reflexive else 0,
                    argument.complementizer, argument.infinitive_marker,
                ),
            )
    return key


def _refresh_fts(connection: sqlite3.Connection) -> None:
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries_fts'").fetchone():
        return
    connection.execute("DELETE FROM entries_fts")
    connection.execute(
        "INSERT INTO entries_fts(rowid,headword_norm,lexeme_norm,translation_norm,search_norm) "
        "SELECT entry_index,headword_norm,lexeme_norm,translation_norm,search_norm FROM entries ORDER BY entry_index"
    )


def _export_text_mirror(connection: sqlite3.Connection, text_path: Path) -> None:
    rows = connection.execute("SELECT raw FROM entries ORDER BY entry_index").fetchall()
    content = "\n\n".join(str(row[0]).strip() for row in rows if str(row[0]).strip())
    if content:
        content += "\n"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    temp = text_path.with_name(f".{text_path.name}.verb-rektion-v2.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, text_path)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def migrate_all(sqlite_path: Path, text_path: Path | None = None, *, force: bool = False) -> dict[str, int]:
    sqlite_path = Path(sqlite_path).expanduser().resolve()
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"Dictionary SQLite database not found: {sqlite_path}")

    connection = sqlite3.connect(str(sqlite_path), timeout=5.0)
    changed_rows = 0
    migrated = 0
    unknown = 0
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        _meta(connection)
        current_row = connection.execute("SELECT value FROM meta WHERE key=?", (META_SCHEMA_KEY,)).fetchone()
        current_version = str(current_row[0]) if current_row else ""
        dirty_row = connection.execute("SELECT value FROM meta WHERE key=?", (META_DIRTY_KEY,)).fetchone()
        dirty = str(dirty_row[0]) == "1" if dirty_row else True

        if current_version != SCHEMA_VERSION:
            connection.execute("PRAGMA foreign_keys=OFF")
            _drop_derived_tables(connection)
            connection.commit()
            connection.execute("PRAGMA foreign_keys=ON")

        _schema(connection)
        connection.commit()

        if current_version == SCHEMA_VERSION and not dirty and not force:
            count = connection.execute("SELECT COUNT(*) FROM verb_valency_entries").fetchone()
            return {"migrated": int(count[0] if count else 0), "changed": 0, "unknown": 0}

        rows = connection.execute(
            "SELECT entry_index,raw,first_line,headword,role,headword_norm FROM entries ORDER BY entry_index"
        ).fetchall()
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM verb_valency_entries")
            for entry_index, raw, first_line, headword, role, headword_norm in rows:
                raw = str(raw); first_line = str(first_line); headword = str(headword)
                role = str(role); headword_norm = str(headword_norm)
                if not _is_verbish(role, headword, raw, first_line):
                    continue
                patterns = _patterns_for_entry(raw, first_line, headword)
                _replace_valency(
                    connection, entry_index=int(entry_index), headword=headword,
                    headword_norm=headword_norm, role=role, patterns=patterns,
                )
                migrated += 1
                if any(p.source == "unknown" or p.confidence < 0.5 for p in patterns):
                    unknown += 1
                canonical = _canonical_rektion_raw(raw, patterns)
                if canonical != raw:
                    changed_rows += 1
                    connection.execute(
                        "UPDATE entries SET raw=?, search_norm=? WHERE entry_index=?",
                        (canonical, dictionary_core.normalize_text(canonical), int(entry_index)),
                    )
            if changed_rows:
                _refresh_fts(connection)
            connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_SCHEMA_KEY, SCHEMA_VERSION))
            connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_COUNT_KEY, str(migrated)))
            connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_DIRTY_KEY, "0"))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

        if changed_rows and text_path is not None:
            _export_text_mirror(connection, Path(text_path).expanduser().resolve())
        return {"migrated": migrated, "changed": changed_rows, "unknown": unknown}
    finally:
        connection.close()


def _sync_one(sqlite_path: Path, text_path: Path | None, entry_index: int) -> str | None:
    connection = sqlite3.connect(str(sqlite_path), timeout=5.0)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        _schema(connection)
        connection.commit()
        row = connection.execute(
            "SELECT entry_index,raw,first_line,headword,role,headword_norm FROM entries WHERE entry_index=?",
            (entry_index,),
        ).fetchone()
        if row is None:
            return None
        index, raw, first_line, headword, role, headword_norm = row
        raw = str(raw); first_line = str(first_line); headword = str(headword)
        role = str(role); headword_norm = str(headword_norm)
        connection.execute("BEGIN IMMEDIATE")
        try:
            if not _is_verbish(role, headword, raw, first_line):
                connection.execute("DELETE FROM verb_valency_entries WHERE entry_key=?", (_entry_key(role, headword_norm),))
                connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_DIRTY_KEY, "0"))
                connection.commit()
                return raw
            patterns = _patterns_for_entry(raw, first_line, headword)
            _replace_valency(connection, entry_index=int(index), headword=headword, headword_norm=headword_norm, role=role, patterns=patterns)
            canonical = _canonical_rektion_raw(raw, patterns)
            if canonical != raw:
                connection.execute(
                    "UPDATE entries SET raw=?, search_norm=? WHERE entry_index=?",
                    (canonical, dictionary_core.normalize_text(canonical), int(index)),
                )
                _refresh_fts(connection)
            connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_DIRTY_KEY, "0"))
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        if canonical != raw and text_path is not None:
            _export_text_mirror(connection, Path(text_path))
        return canonical
    finally:
        connection.close()


def _delete_key(sqlite_path: Path, role: str, headword_norm: str) -> None:
    connection = sqlite3.connect(str(sqlite_path), timeout=5.0)
    try:
        _schema(connection)
        connection.execute("DELETE FROM verb_valency_entries WHERE entry_key=?", (_entry_key(role, headword_norm),))
        connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (META_DIRTY_KEY, "1"))
        connection.commit()
    finally:
        connection.close()


def _badge_html(case_value: str) -> str:
    styles = {
        "nom": ("#eaf2fb", "#245d87"),
        "akk": ("#fff3ea", "#8a4f2f"),
        "dat": ("#eef9f2", "#356b49"),
        "gen": ("#f3efff", "#58458e"),
    }
    key = case_value.casefold().rstrip(".")
    bg, fg = styles[key]
    short = {"nom": "Nom.", "akk": "Akk.", "dat": "Dat.", "gen": "Gen."}[key]
    return (
        f"<span style='background:{bg}; color:{fg}; border:1px solid {fg}; "
        "padding:2px 6px; font-weight:800;'>"
        f"{short}</span>"
    )


def _render_rektion_line(line: str) -> str | None:
    match = REKTION_LINE_RE.match(line)
    if not match:
        return None
    label = line.split(":", 1)[0].strip()
    value = match.group("value").strip()
    escaped = html.escape(value)
    escaped = re.sub(
        r"\[\s*(Nom|Akk|Dat|Gen)\.?\s*\]",
        lambda m: _badge_html(m.group(1)),
        escaped,
        flags=re.IGNORECASE,
    )
    escaped = escaped.replace("?", "<span style='background:#fff8df; color:#8a651d; padding:1px 5px; font-weight:800;'>?</span>")
    return (
        "<div style='margin:9px 0 7px 0; padding:9px 11px; "
        "background:#f7f9fc; border:1px solid #cbd7e5; border-radius:7px; line-height:1.8'>"
        f"<span style='color:#315f88; font-weight:800'>{html.escape(label)}:</span>&nbsp;&nbsp;"
        f"{escaped}</div>"
    )


def _patch_detail_renderer(application) -> None:
    original = application._detail_line
    if getattr(original, "_nd_verb_rektion_v2", False):
        return

    def detail_line(line: str) -> str:
        rendered = _render_rektion_line(line)
        return rendered if rendered is not None else original(line)

    detail_line._nd_verb_rektion_v2 = True
    application._detail_line = detail_line


def _patch_add_dialog(base) -> None:
    legacy = base.legacy
    cls = legacy.AddEntryDialog
    if getattr(cls, "_nd_verb_rektion_editor_v2", False):
        return
    original_init = cls.__init__
    original_entry_text = cls.entry_text

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        raw = self.editor.toPlainText()
        existing: list[str] = []
        kept: list[str] = []
        for line in raw.splitlines():
            match = REKTION_LINE_RE.match(line)
            if match:
                value = match.group("value").strip()
                sense = match.group("sense")
                existing.append(f"{sense} => {value}" if sense else value)
            else:
                kept.append(line)
        if existing:
            self.editor.setPlainText("\n".join(kept).strip())

        title = legacy.QLabel("Verb-Rektion / Valenz (optional)", self)
        font = title.font(); font.setBold(True); title.setFont(font)
        hint = legacy.QLabel(
            "One alternative pattern per line. Examples:  jemandem [Dat.] + etwas [Akk.]   |   "
            "auf jemanden/etwas [Akk.]   |   dass-Satz   |   zu + Infinitiv.  "
            "Optional: (mit jemandem [Dat.]). For a meaning label: Thema => über etwas [Akk.].",
            self,
        )
        hint.setWordWrap(True)
        self.rektion_editor = legacy.QTextEdit(self)
        self.rektion_editor.setAcceptRichText(False)
        self.rektion_editor.setFixedHeight(92)
        self.rektion_editor.setPlaceholderText("jemandem [Dat.] + etwas [Akk.]\nauf jemanden/etwas [Akk.]")
        if existing:
            self.rektion_editor.setPlainText("\n".join(existing))
        layout = self.layout()
        insert_at = max(0, layout.count() - 1)
        layout.insertWidget(insert_at, title)
        layout.insertWidget(insert_at + 1, hint)
        layout.insertWidget(insert_at + 2, self.rektion_editor)

    def entry_text(self) -> str:
        base_text = original_entry_text(self).strip()
        values = [line.strip() for line in self.rektion_editor.toPlainText().splitlines() if line.strip()]
        if not values:
            return base_text
        lines = [base_text]
        for index, value in enumerate(values):
            value = re.sub(r"^Rektion(?:\s+\d+)?(?:\s*\[[^\]]+\])?\s*:\s*", "", value, flags=re.IGNORECASE)
            sense = None
            if "=>" in value:
                left, right = value.split("=>", 1)
                if left.strip() and right.strip():
                    sense, value = left.strip(), right.strip()
            label = "Rektion" if index == 0 else f"Rektion {index + 1}"
            if sense:
                label += f" [{sense}]"
            lines.append(f"{label}: {value}")
        return "\n".join(lines).strip()

    cls.__init__ = init
    cls.entry_text = entry_text
    cls._nd_verb_rektion_editor_v2 = True


def install(application, base, sqlite_backend, *, sqlite_path: Path, text_path: Path | None = None) -> dict[str, int]:
    """Install normalized verb valency v2, migration, editor and compact search rendering."""
    sqlite_path = Path(sqlite_path).expanduser().resolve()
    text_path = None if text_path is None else Path(text_path).expanduser().resolve()
    sqlite_backend.ensure_primary_database()
    stats = migrate_all(sqlite_path, text_path)

    original_add = base.ORIGINAL_ADD
    original_replace = base.ORIGINAL_REPLACE
    original_delete = base.ORIGINAL_DELETE
    if not getattr(original_add, "_nd_verb_rektion_v2", False):
        def add(self, database_path, raw_entry: str):
            result = original_add(self, database_path, raw_entry)
            index = len(self.entries) - 1
            canonical = _sync_one(sqlite_path, text_path, index)
            if canonical:
                parsed = dictionary_core.parse_entry(canonical)
                updated = list(self.entries); updated[index] = parsed; self.__init__(updated)
                return parsed
            return result

        def replace(self, database_path, entry_index: int, raw_entry: str):
            old = self.entries[entry_index] if 0 <= entry_index < len(self.entries) else None
            result = original_replace(self, database_path, entry_index, raw_entry)
            if old is not None:
                _delete_key(sqlite_path, old.role, old.headword_norm)
            canonical = _sync_one(sqlite_path, text_path, entry_index)
            if canonical:
                parsed = dictionary_core.parse_entry(canonical)
                updated = list(self.entries); updated[entry_index] = parsed; self.__init__(updated)
                return parsed
            return result

        def delete(self, database_path, entry_index: int):
            old = self.entries[entry_index] if 0 <= entry_index < len(self.entries) else None
            result = original_delete(self, database_path, entry_index)
            if old is not None:
                _delete_key(sqlite_path, old.role, old.headword_norm)
            return result

        add._nd_verb_rektion_v2 = True
        replace._nd_verb_rektion_v2 = True
        delete._nd_verb_rektion_v2 = True
        base.ORIGINAL_ADD = add
        base.ORIGINAL_REPLACE = replace
        base.ORIGINAL_DELETE = delete

    _patch_detail_renderer(application)
    current_install = base.install
    if not getattr(current_install, "_nd_verb_rektion_wrapper_v2", False):
        original_install = current_install

        def install_then_rektion_ui() -> None:
            original_install()
            _patch_add_dialog(base)

        install_then_rektion_ui._nd_verb_rektion_wrapper_v2 = True
        base.install = install_then_rektion_ui
    return stats
