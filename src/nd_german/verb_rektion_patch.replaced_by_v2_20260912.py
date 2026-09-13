from __future__ import annotations

import html
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import dictionary_core


SCHEMA_VERSION = "1"
META_SCHEMA_KEY = "verb_rektion_schema_version"
META_COUNT_KEY = "verb_rektion_migrated_entries"

CASE_ROWS = (
    ("NOM", "Nominativ"),
    ("AKK", "Akkusativ"),
    ("DAT", "Dativ"),
    ("GEN", "Genitiv"),
    ("UNK", "Unbestimmt"),
)
ROLE_ROWS = (
    ("subject", "Subjekt"),
    ("object", "Objekt"),
    ("indirect_object", "indirektes Objekt"),
    ("prepositional", "Präpositionalergänzung"),
    ("reflexive", "Reflexivergänzung"),
    ("predicate", "Prädikativ"),
    ("complement", "Ergänzung"),
)
PREPOSITIONS = (
    "an", "auf", "aus", "bei", "durch", "für", "gegen", "gegenüber", "in",
    "mit", "nach", "ohne", "über", "um", "unter", "von", "vor", "zu", "zwischen",
)

REKTION_LINE_RE = re.compile(r"^\s*Rektion(?:\s+\d+)?\s*:\s*(.*?)\s*$", re.IGNORECASE)
CASE_RE = re.compile(
    r"(?<![\w])(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?![\w])",
    re.IGNORECASE,
)
PREP_CASE_RE = re.compile(
    r"(?<![\w])(?P<prep>an|auf|aus|bei|durch|für|gegen|gegenüber|in|mit|nach|ohne|über|um|unter|von|vor|zu|zwischen)\s*\+\s*"
    r"(?P<case>Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?![\w])",
    re.IGNORECASE,
)
JDN_RE = re.compile(r"\b(?:jdn|jmdn|jemanden)(?:\.)?\b", re.IGNORECASE)
JDM_RE = re.compile(r"\b(?:jdm|jemandem)(?:\.)?\b", re.IGNORECASE)
ETW_CASE_RE = re.compile(
    r"\betw(?:as)?(?:\.)?\s*(?:\[\s*)?(Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?)(?:\.)?(?:\s*\])?",
    re.IGNORECASE,
)
GRAMMAR_MARKER_RE = re.compile(
    r"\b(transitiv|intransitiv|reflexiv|trennbar|untrennbar|nicht\s+trennbar|verb)\b",
    re.IGNORECASE,
)
TENSE_MARKER_RE = re.compile(
    r"(?im)^\s*(Präsens|Präteritum|Perfekt|Futur\s+I|Konjunktiv\s+[Ii]{1,2})\s*:",
)
INFINITIVE_TOKEN_RE = re.compile(r"^[a-zäöüß][a-zäöüß-]*(?:en|eln|ern)$", re.IGNORECASE)


@dataclass(frozen=True)
class ArgumentSpec:
    role: str
    case_code: str
    preposition: str | None = None
    placeholder: str | None = None
    required: bool = True


@dataclass(frozen=True)
class PatternSpec:
    arguments: tuple[ArgumentSpec, ...]
    source: str
    confidence: float

    @property
    def display(self) -> str:
        pieces: list[str] = []
        for arg in self.arguments:
            if arg.role == "subject":
                pieces.append("Nom")
                continue
            case = _display_case(arg.case_code)
            if arg.preposition:
                pieces.append(f"{arg.preposition} + {case}")
            elif arg.role == "reflexive":
                pieces.append(f"sich [{case}]")
            else:
                pieces.append(case)
        return " · ".join(pieces) if pieces else "Nom"


def _display_case(code: str) -> str:
    return {
        "NOM": "Nom",
        "AKK": "Akk",
        "DAT": "Dat",
        "GEN": "Gen",
        "UNK": "?",
    }.get(code.upper(), "?")


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
    last = re.sub(r"[^A-Za-zÄÖÜäöüß-]", "", head.split()[-1]) if head.split() else ""
    # German infinitives inside phrase headwords are normally lower-case; requiring
    # that avoids treating plural nouns such as "Armen" as verbs.
    return bool(last and last[:1].islower() and INFINITIVE_TOKEN_RE.match(last))


def _candidate_annotation(first_line: str) -> str:
    candidates: list[str] = []
    for value in re.findall(r"\(([^()]*)\)", first_line):
        if CASE_RE.search(value) or PREP_CASE_RE.search(value) or JDN_RE.search(value) or JDM_RE.search(value):
            candidates.append(value)
    if candidates:
        return " ; ".join(candidates)

    # Some older entries put jdn./jdm./etw.Akk directly before the colon.
    before_colon = first_line.split(":", 1)[0]
    if (
        CASE_RE.search(before_colon)
        or PREP_CASE_RE.search(before_colon)
        or JDN_RE.search(before_colon)
        or JDM_RE.search(before_colon)
    ):
        return before_colon
    return ""


def _make_arg(case_code: str, *, prep: str | None = None, placeholder: str | None = None, reflexive: bool = False) -> ArgumentSpec:
    if prep:
        role = "prepositional"
    elif reflexive:
        role = "reflexive"
    elif case_code == "DAT":
        role = "indirect_object"
    elif case_code == "NOM":
        role = "predicate"
    else:
        role = "object"
    return ArgumentSpec(role=role, case_code=case_code, preposition=prep, placeholder=placeholder)


def _parse_pattern_text(text: str, *, first_line: str, headword: str) -> PatternSpec:
    cleaned = text.strip()
    lowered = f"{first_line} {headword}".casefold()
    reflexive = (
        "reflexiv" in lowered
        or headword.casefold().startswith("sich ")
        or bool(re.search(r"\bsich\b", cleaned, re.IGNORECASE))
    )
    transitive = "transitiv" in lowered and "intransitiv" not in lowered
    intransitive = "intransitiv" in lowered and "transitiv" not in lowered.replace("intransitiv", "")

    found: list[tuple[int, int, ArgumentSpec]] = []
    occupied: list[tuple[int, int]] = []

    def add(span: tuple[int, int], arg: ArgumentSpec) -> None:
        start, end = span
        if any(start < other_end and end > other_start for other_start, other_end in occupied):
            return
        occupied.append((start, end))
        found.append((start, end, arg))

    for match in PREP_CASE_RE.finditer(cleaned):
        add(
            match.span(),
            _make_arg(_case_code(match.group("case")), prep=match.group("prep").casefold()),
        )

    for match in ETW_CASE_RE.finditer(cleaned):
        add(match.span(), _make_arg(_case_code(match.group(1)), placeholder="etw."))

    for match in JDN_RE.finditer(cleaned):
        add(match.span(), _make_arg("AKK", placeholder="jdn."))
    for match in JDM_RE.finditer(cleaned):
        add(match.span(), _make_arg("DAT", placeholder="jdm."))

    # Add bare case annotations not already consumed by a preposition or placeholder.
    for match in CASE_RE.finditer(cleaned):
        add(match.span(), _make_arg(_case_code(match.group("case")), reflexive=reflexive and not found))

    found.sort(key=lambda item: item[0])
    # In canonical/explicit notation an initial Nom is the subject. The subject is
    # stored separately below, so consume only that first Nom and preserve any
    # later Nom as a predicative complement (e.g. sein/werden/bleiben).
    if found and found[0][0] <= 2 and found[0][2].case_code == "NOM" and found[0][2].preposition is None:
        found = found[1:]
    args = [item[2] for item in found]

    # Slash notation such as jdn./etw.Akk denotes alternatives, not two simultaneous objects.
    if "/" in cleaned and len(args) > 1:
        collapsed: list[ArgumentSpec] = []
        seen_simple: set[tuple[str, str | None]] = set()
        for arg in args:
            key = (arg.case_code, arg.preposition)
            if key in seen_simple and arg.preposition is None:
                continue
            seen_simple.add(key)
            collapsed.append(arg)
        args = collapsed

    # Preserve explicit repeated cases when written as Akk. + Akk.; otherwise remove
    # accidental duplicate matches caused by mixed old notation.
    if "+" not in cleaned:
        unique: list[ArgumentSpec] = []
        seen: set[tuple[str, str | None, str]] = set()
        for arg in args:
            key = (arg.case_code, arg.preposition, arg.role)
            if key not in seen:
                seen.add(key)
                unique.append(arg)
        args = unique

    inferred_source = None
    inferred_confidence = None
    if not args:
        norm_head = dictionary_core.normalize_text(headword)
        head_lower = headword.casefold().strip()
        article_cases = {"einen": "AKK", "einem": "DAT", "eines": "GEN", "dem": "DAT", "des": "GEN"}
        prep_article = re.search(
            r"\b(an|auf|aus|bei|durch|für|gegen|gegenüber|in|mit|nach|ohne|über|um|unter|von|vor|zu|zwischen)\s+"
            r"(einen|einem|eines|dem|des)\b",
            head_lower,
            re.IGNORECASE,
        )
        first_word = head_lower.split()[0] if head_lower.split() else ""
        if prep_article:
            args.append(_make_arg(article_cases[prep_article.group(2).casefold()], prep=prep_article.group(1).casefold()))
            inferred_source, inferred_confidence = "phrase-form", 0.90
        elif first_word in article_cases:
            args.append(_make_arg(article_cases[first_word]))
            inferred_source, inferred_confidence = "phrase-form", 0.88
        elif norm_head in {"sein", "werden", "bleiben"}:
            args.append(ArgumentSpec("predicate", "NOM", placeholder="Prädikativ"))
            inferred_source, inferred_confidence = "lexical", 0.98
        elif transitive:
            args.append(_make_arg("AKK"))
        elif reflexive:
            args.append(_make_arg("UNK", placeholder="sich", reflexive=True))
        elif intransitive:
            pass
        else:
            args.append(ArgumentSpec("complement", "UNK", placeholder="?"))

    confidence = 1.0 if cleaned else (inferred_confidence if inferred_confidence is not None else (0.78 if (transitive or intransitive or reflexive) else 0.35))
    source = "explicit" if cleaned else (inferred_source or ("grammar-marker" if confidence >= 0.7 else "unknown"))
    return PatternSpec(
        arguments=(ArgumentSpec("subject", "NOM", placeholder="Subjekt"), *args),
        source=source,
        confidence=confidence,
    )


def _patterns_for_entry(raw: str, first_line: str, headword: str) -> list[PatternSpec]:
    explicit_values: list[str] = []
    for line in raw.splitlines():
        match = REKTION_LINE_RE.match(line)
        if match and match.group(1).strip():
            explicit_values.append(match.group(1).strip())

    if explicit_values:
        patterns: list[PatternSpec] = []
        for value in explicit_values:
            # Double bars deliberately mean separate valency patterns. A semicolon is
            # kept inside one pattern because older dictionary lines use it as prose.
            for part in [chunk.strip() for chunk in value.split("||") if chunk.strip()]:
                patterns.append(_parse_pattern_text(part, first_line=first_line, headword=headword))
        return patterns

    annotation = _candidate_annotation(first_line)
    return [_parse_pattern_text(annotation, first_line=first_line, headword=headword)]


def _canonical_rektion_raw(raw: str, displays: Iterable[str]) -> str:
    lines = [line.rstrip() for line in raw.strip().splitlines()]
    lines = [line for line in lines if not REKTION_LINE_RE.match(line)]
    rendered = [display.strip() for display in displays if display.strip()]
    if not rendered:
        return "\n".join(lines).strip()

    insertion = 1 if lines else 0
    for index, line in enumerate(lines[1:], start=1):
        label = line.split(":", 1)[0].strip().casefold() if ":" in line else ""
        if label in {"english", "persian", "penglish"}:
            insertion = index + 1
        elif insertion > 1:
            break

    rection_lines = [
        ("Rektion:" if index == 0 else f"Rektion {index + 1}:") + f" {display}"
        for index, display in enumerate(rendered)
    ]
    lines[insertion:insertion] = rection_lines
    return "\n".join(lines).strip()


def _schema(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
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
            case_id INTEGER NOT NULL REFERENCES grammatical_cases(case_id),
            preposition_id INTEGER REFERENCES prepositions(preposition_id),
            placeholder TEXT,
            required INTEGER NOT NULL DEFAULT 1 CHECK(required IN (0,1)),
            UNIQUE(pattern_id, argument_order)
        );
        CREATE INDEX IF NOT EXISTS idx_vve_headword_norm ON verb_valency_entries(headword_norm);
        CREATE INDEX IF NOT EXISTS idx_vvp_entry_key ON verb_valency_patterns(entry_key, pattern_order);
        CREATE INDEX IF NOT EXISTS idx_vva_pattern ON verb_valency_arguments(pattern_id, argument_order);
        """
    )
    connection.executemany(
        "INSERT OR IGNORE INTO grammatical_cases(code, label_de) VALUES (?, ?)",
        CASE_ROWS,
    )
    connection.executemany(
        "INSERT OR IGNORE INTO verb_argument_roles(code, label_de) VALUES (?, ?)",
        ROLE_ROWS,
    )
    connection.executemany(
        "INSERT OR IGNORE INTO prepositions(lemma) VALUES (?)",
        ((value,) for value in PREPOSITIONS),
    )


def _lookup_id(connection: sqlite3.Connection, table: str, id_column: str, key_column: str, value: str) -> int:
    row = connection.execute(
        f"SELECT {id_column} FROM {table} WHERE {key_column} = ?",
        (value,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Missing lookup {table}.{key_column}={value!r}")
    return int(row[0])


def _replace_valency(
    connection: sqlite3.Connection,
    *,
    entry_index: int,
    headword: str,
    headword_norm: str,
    role: str,
    patterns: list[PatternSpec],
) -> str:
    key = _entry_key(role, headword_norm)
    connection.execute(
        """
        INSERT INTO verb_valency_entries(
            entry_key, headword_norm, headword, dictionary_role, entry_index_snapshot, is_phrase
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(entry_key) DO UPDATE SET
            headword_norm=excluded.headword_norm,
            headword=excluded.headword,
            dictionary_role=excluded.dictionary_role,
            entry_index_snapshot=excluded.entry_index_snapshot,
            is_phrase=excluded.is_phrase
        """,
        (key, headword_norm, headword, role, entry_index, 1 if role == "phrase" else 0),
    )
    connection.execute("DELETE FROM verb_valency_patterns WHERE entry_key = ?", (key,))

    for order, pattern in enumerate(patterns):
        cursor = connection.execute(
            """
            INSERT INTO verb_valency_patterns(entry_key, pattern_order, display_text, source, confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, order, pattern.display, pattern.source, pattern.confidence),
        )
        pattern_id = int(cursor.lastrowid)
        for argument_order, argument in enumerate(pattern.arguments):
            role_id = _lookup_id(connection, "verb_argument_roles", "role_id", "code", argument.role)
            case_id = _lookup_id(connection, "grammatical_cases", "case_id", "code", argument.case_code)
            prep_id = None
            if argument.preposition:
                prep_id = _lookup_id(connection, "prepositions", "preposition_id", "lemma", argument.preposition)
            connection.execute(
                """
                INSERT INTO verb_valency_arguments(
                    pattern_id, argument_order, role_id, case_id, preposition_id, placeholder, required
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pattern_id,
                    argument_order,
                    role_id,
                    case_id,
                    prep_id,
                    argument.placeholder,
                    1 if argument.required else 0,
                ),
            )
    return key


def _refresh_fts(connection: sqlite3.Connection) -> None:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries_fts'"
    ).fetchone()
    if not exists:
        return
    connection.execute("DELETE FROM entries_fts")
    connection.execute(
        """
        INSERT INTO entries_fts(rowid, headword_norm, lexeme_norm, translation_norm, search_norm)
        SELECT entry_index, headword_norm, lexeme_norm, translation_norm, search_norm
        FROM entries ORDER BY entry_index
        """
    )


def _export_text_mirror(connection: sqlite3.Connection, text_path: Path) -> None:
    rows = connection.execute("SELECT raw FROM entries ORDER BY entry_index").fetchall()
    content = "\n\n".join(str(row[0]).strip() for row in rows if str(row[0]).strip())
    if content:
        content += "\n"
    text_path.parent.mkdir(parents=True, exist_ok=True)
    temp = text_path.with_name(f".{text_path.name}.verb-rektion.tmp")
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
        _schema(connection)
        connection.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        connection.commit()
        current = connection.execute(
            "SELECT value FROM meta WHERE key = ?", (META_SCHEMA_KEY,)
        ).fetchone()
        if current and str(current[0]) == SCHEMA_VERSION and not force:
            count_row = connection.execute(
                "SELECT COUNT(*) FROM verb_valency_entries"
            ).fetchone()
            return {"migrated": int(count_row[0] if count_row else 0), "changed": 0, "unknown": 0}

        rows = connection.execute(
            """
            SELECT entry_index, raw, first_line, headword, role, headword_norm
            FROM entries ORDER BY entry_index
            """
        ).fetchall()

        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM verb_valency_entries")
            for entry_index, raw, first_line, headword, role, headword_norm in rows:
                raw = str(raw)
                first_line = str(first_line)
                headword = str(headword)
                role = str(role)
                headword_norm = str(headword_norm)
                if not _is_verbish(role, headword, raw, first_line):
                    continue

                patterns = _patterns_for_entry(raw, first_line, headword)
                _replace_valency(
                    connection,
                    entry_index=int(entry_index),
                    headword=headword,
                    headword_norm=headword_norm,
                    role=role,
                    patterns=patterns,
                )
                migrated += 1
                if any(pattern.source == "unknown" for pattern in patterns):
                    unknown += 1

                canonical_raw = _canonical_rektion_raw(raw, [p.display for p in patterns])
                if canonical_raw != raw:
                    changed_rows += 1
                    connection.execute(
                        "UPDATE entries SET raw = ?, search_norm = ? WHERE entry_index = ?",
                        (canonical_raw, dictionary_core.normalize_text(canonical_raw), int(entry_index)),
                    )

            if changed_rows:
                _refresh_fts(connection)
            connection.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                (META_SCHEMA_KEY, SCHEMA_VERSION),
            )
            connection.execute(
                "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
                (META_COUNT_KEY, str(migrated)),
            )
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
            """
            SELECT entry_index, raw, first_line, headword, role, headword_norm
            FROM entries WHERE entry_index = ?
            """,
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
                connection.execute(
                    "DELETE FROM verb_valency_entries WHERE entry_key = ?",
                    (_entry_key(role, headword_norm),),
                )
                connection.commit()
                return raw

            patterns = _patterns_for_entry(raw, first_line, headword)
            _replace_valency(
                connection,
                entry_index=int(index),
                headword=headword,
                headword_norm=headword_norm,
                role=role,
                patterns=patterns,
            )
            canonical = _canonical_rektion_raw(raw, [p.display for p in patterns])
            if canonical != raw:
                connection.execute(
                    "UPDATE entries SET raw = ?, search_norm = ? WHERE entry_index = ?",
                    (canonical, dictionary_core.normalize_text(canonical), int(index)),
                )
                _refresh_fts(connection)
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
        connection.execute("PRAGMA foreign_keys=ON")
        _schema(connection)
        connection.execute(
            "DELETE FROM verb_valency_entries WHERE entry_key = ?",
            (_entry_key(role, headword_norm),),
        )
        connection.commit()
    finally:
        connection.close()


def _badge_html(value: str) -> str:
    styles = {
        "nom": ("#eaf2fb", "#245d87", "Nominativ"),
        "akk": ("#fff3ea", "#8a4f2f", "Akkusativ"),
        "dat": ("#eef9f2", "#356b49", "Dativ"),
        "gen": ("#f3efff", "#58458e", "Genitiv"),
    }
    bg, fg, label = styles[value.casefold()]
    return (
        f"<span style='background:{bg}; color:{fg}; border:1px solid {fg}; "
        "padding:2px 6px; font-weight:800;'>"
        f"{label}</span>"
    )


def _render_rektion_line(line: str) -> str | None:
    match = REKTION_LINE_RE.match(line)
    if not match:
        return None
    label = line.split(":", 1)[0].strip()
    value = match.group(1).strip()
    escaped = html.escape(value)
    escaped = re.sub(r"\b(Nom|Akk|Dat|Gen)\b", lambda m: _badge_html(m.group(1)), escaped, flags=re.IGNORECASE)
    escaped = escaped.replace("?", "<span style='color:#9a6428; font-weight:800'>?</span>")
    return (
        "<div style='margin:10px 0 8px 0; padding:9px 11px; "
        "background:#f7f9fc; border:1px solid #cbd7e5; border-radius:7px; line-height:1.75'>"
        f"<span style='color:#315f88; font-weight:800'>{html.escape(label)}:</span>&nbsp;&nbsp;"
        f"{escaped}</div>"
    )


def _patch_detail_renderer(application) -> None:
    original = application._detail_line
    if getattr(original, "_nd_verb_rektion", False):
        return

    def detail_line(line: str) -> str:
        rendered = _render_rektion_line(line)
        if rendered is not None:
            return rendered
        return original(line)

    detail_line._nd_verb_rektion = True
    application._detail_line = detail_line


def _patch_add_dialog(base) -> None:
    legacy = base.legacy
    cls = legacy.AddEntryDialog
    if getattr(cls, "_nd_verb_rektion_editor", False):
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
                existing.append(match.group(1).strip())
            else:
                kept.append(line)
        if existing:
            self.editor.setPlainText("\n".join(kept).strip())

        title = legacy.QLabel("Verb-Rektion / Valenz (optional)", self)
        font = title.font(); font.setBold(True); title.setFont(font)
        hint = legacy.QLabel(
            "One pattern per line, e.g.  Dat + Akk   |   auf + Akk   |   Akk + um + Akk. "
            "Leave empty to infer from the entry; uncertain complements are shown as ?.",
            self,
        )
        hint.setWordWrap(True)
        self.rektion_editor = legacy.QTextEdit(self)
        self.rektion_editor.setAcceptRichText(False)
        self.rektion_editor.setFixedHeight(76)
        self.rektion_editor.setPlaceholderText("Dat + Akk\nauf + Akk")
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
            value = re.sub(r"^Rektion(?:\s+\d+)?\s*:\s*", "", value, flags=re.IGNORECASE)
            label = "Rektion" if index == 0 else f"Rektion {index + 1}"
            lines.append(f"{label}: {value}")
        return "\n".join(lines).strip()

    cls.__init__ = init
    cls.entry_text = entry_text
    cls._nd_verb_rektion_editor = True


def install(application, base, sqlite_backend, *, sqlite_path: Path, text_path: Path | None = None) -> dict[str, int]:
    """Install normalized verb-valency storage, migration and compact result rendering."""
    sqlite_path = Path(sqlite_path).expanduser().resolve()
    text_path = None if text_path is None else Path(text_path).expanduser().resolve()

    # Ensure the authoritative SQLite database exists before extending it.
    sqlite_backend.ensure_primary_database()
    stats = migrate_all(sqlite_path, text_path)

    # Wrap the SQLite mutations before app_base installs its locking facade.
    original_add = base.ORIGINAL_ADD
    original_replace = base.ORIGINAL_REPLACE
    original_delete = base.ORIGINAL_DELETE

    if not getattr(original_add, "_nd_verb_rektion", False):
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

        add._nd_verb_rektion = True
        replace._nd_verb_rektion = True
        delete._nd_verb_rektion = True
        base.ORIGINAL_ADD = add
        base.ORIGINAL_REPLACE = replace
        base.ORIGINAL_DELETE = delete

    _patch_detail_renderer(application)

    current_install = base.install
    if not getattr(current_install, "_nd_verb_rektion_wrapper", False):
        original_install = current_install

        def install_then_rektion_ui() -> None:
            original_install()
            _patch_add_dialog(base)

        install_then_rektion_ui._nd_verb_rektion_wrapper = True
        base.install = install_then_rektion_ui

    return stats
