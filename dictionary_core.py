from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - exercised only without optional dependency
    fuzz = None


ENTRY_SEPARATOR_RE = re.compile(r"\n\s*\n+")
WHITESPACE_RE = re.compile(r"\s+")
NON_WORD_RE = re.compile(r"[^\w\u0600-\u06ff]+", re.UNICODE)
IPA_RE = re.compile(r"\s*\[[^\]]*\]")
PAREN_RE = re.compile(r"\s*\([^)]*\)")

PERSIAN_TRANSLATION = str.maketrans(
    {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "ۀ": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
        "ٱ": "ا",
        "‌": " ",  # zero-width non-joiner
        "ـ": "",
    }
)


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    raw: str
    first_line: str
    headword: str
    role: str
    translation: str
    headword_norm: str
    translation_norm: str
    search_norm: str
    trigrams: frozenset[str]

    @property
    def lexeme_norm(self) -> str:
        return re.sub(r"^(?:der|die|das|ein|eine)\s+", "", self.headword_norm)

    @property
    def duplicate_key(self) -> tuple[str, str]:
        return self.headword_norm, self.role


@dataclass(frozen=True, slots=True)
class SearchResult:
    entry: DictionaryEntry
    score: float


def normalize_text(text: str) -> str:
    """Normalize German, Latin/Penglish and Persian text for fast matching."""
    text = text.translate(PERSIAN_TRANSLATION).casefold()
    text = (
        text.replace("ß", "ss")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
    )
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    without_punctuation = NON_WORD_RE.sub(" ", without_marks)
    return WHITESPACE_RE.sub(" ", without_punctuation).strip()


def make_trigrams(text: str) -> frozenset[str]:
    compact = text.replace(" ", "_")
    if len(compact) < 3:
        return frozenset({compact}) if compact else frozenset()
    return frozenset(compact[i : i + 3] for i in range(len(compact) - 2))


def split_entries(text: str) -> list[str]:
    return [chunk.strip() for chunk in ENTRY_SEPARATOR_RE.split(text) if chunk.strip()]


def extract_headword(first_line: str) -> str:
    left = first_line.split(":", 1)[0].strip()
    left = IPA_RE.sub("", left)
    left = PAREN_RE.sub("", left)
    # Remove frequent grammatical labels that may follow the headword.
    left = re.sub(
        r"\s+(?:trennbar|untrennbar|nicht trennbar|transitiv|intransitiv|reflexiv|"
        r"regelmäßig|unregelmäßig|stark|schwach|adjektiv|adverb|pronom|"
        r"konjunktion|präposition|substantiv|verb)(?:\s.*)?$",
        "",
        left,
        flags=re.IGNORECASE,
    )
    return WHITESPACE_RE.sub(" ", left).strip(" -")


def extract_translation(first_line: str) -> str:
    if ":" not in first_line:
        return ""
    return first_line.split(":", 1)[1].strip()


def detect_role(first_line: str, headword: str) -> str:
    line = first_line.casefold()
    head = headword.casefold().strip()

    if "konjunktion" in line:
        return "conjunction"
    if "präposition" in line:
        return "preposition"
    if "pronom" in line:
        return "pronoun"
    if "adverb" in line:
        return "adverb"
    if "adjektiv" in line:
        return "adjective"
    if "partizip" in line:
        return "participle"
    if "phrase" in line or "redewendung" in line:
        return "phrase"

    noun_prefixes = (
        "der ",
        "die ",
        "das ",
        "ein ",
        "eine ",
    )
    if head.startswith(noun_prefixes) or "substantiv" in line or "plural:" in line:
        return "noun"

    verb_markers = (
        "transitiv",
        "intransitiv",
        "reflexiv",
        "trennbar",
        "untrennbar",
        "verb",
        "präsens:",
        "perfekt:",
    )
    if any(marker in line for marker in verb_markers) or head.startswith("sich "):
        return "verb"

    if "adjektiv" in head or "adverb" in head:
        return "other"

    # A conservative fallback for infinitives while avoiding article-led nouns.
    first_token = head.split()[0] if head else ""
    if first_token.endswith(("en", "eln", "ern")) and not head.startswith(noun_prefixes):
        return "verb"

    if len(head.split()) > 1:
        return "phrase"
    return "unknown"


def parse_entry(raw: str) -> DictionaryEntry:
    # Be tolerant of BOMs, accidental separator lines, comments, or other
    # harmless formatting at the beginning of an entry.  A single unusual
    # entry must never prevent the whole dictionary from opening.
    cleaned = raw.replace("\ufeff", "").strip()
    if not cleaned:
        raise ValueError("The entry is empty.")

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        raise ValueError("The entry must have a non-empty line.")

    first_line = lines[0]
    headword = extract_headword(first_line)

    # If the physical first line is only a marker (for example ':' or a
    # decoration), look for the first later line that has a usable left side.
    if not headword:
        for candidate in lines[1:]:
            candidate_headword = extract_headword(candidate)
            if candidate_headword:
                first_line = candidate
                headword = candidate_headword
                break

    # Last-resort fallback: keep the entry editable/deletable instead of
    # aborting application startup.  The raw text remains completely intact.
    if not headword:
        fallback = re.sub(r"^[\s:;|=_\-–—]+|[\s:;|=_\-–—]+$", "", lines[0])
        headword = WHITESPACE_RE.sub(" ", fallback).strip()
    if not headword:
        headword = "[unrecognized entry]"

    translation = extract_translation(first_line)
    role = detect_role(first_line, headword)
    headword_norm = normalize_text(headword)
    translation_norm = normalize_text(translation)
    search_norm = normalize_text(cleaned)
    compact_index = search_norm

    return DictionaryEntry(
        raw=cleaned,
        first_line=first_line,
        headword=headword,
        role=role,
        translation=translation,
        headword_norm=headword_norm,
        translation_norm=translation_norm,
        search_norm=search_norm,
        trigrams=make_trigrams(compact_index),
    )


def _fallback_similarity(query: str, candidate: str) -> float:
    from difflib import SequenceMatcher

    return SequenceMatcher(None, query, candidate).ratio() * 100.0


def _similarity(query: str, candidate: str) -> float:
    if not candidate:
        return 0.0
    if fuzz is not None:
        return float(fuzz.ratio(query, candidate, score_cutoff=0))
    return _fallback_similarity(query, candidate)


class DictionaryIndex:
    def __init__(self, entries: Iterable[DictionaryEntry]) -> None:
        self.entries = list(entries)
        self._duplicate_keys = {entry.duplicate_key for entry in self.entries}
        self._trigram_map: dict[str, set[int]] = {}
        for idx, entry in enumerate(self.entries):
            for trigram in entry.trigrams:
                self._trigram_map.setdefault(trigram, set()).add(idx)

    @classmethod
    def from_file(cls, path: str | os.PathLike[str]) -> "DictionaryIndex":
        database_path = Path(path)
        text = database_path.read_text(encoding="utf-8")
        entries = [parse_entry(raw) for raw in split_entries(text)]
        return cls(entries)

    def contains_duplicate(self, entry: DictionaryEntry) -> bool:
        return entry.duplicate_key in self._duplicate_keys

    def _candidate_indices(self, query: str) -> set[int]:
        if len(query.replace(" ", "")) < 3:
            return set(range(len(self.entries)))
        query_trigrams = make_trigrams(query)
        counts: dict[int, int] = {}
        for trigram in query_trigrams:
            for idx in self._trigram_map.get(trigram, ()):
                counts[idx] = counts.get(idx, 0) + 1
        if not counts:
            return set(range(len(self.entries)))
        # Keep the best overlap candidates; exact substring checks are still done globally.
        return {idx for idx, _ in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:700]}

    @staticmethod
    def _exact_score(entry: DictionaryEntry, query: str) -> float:
        if entry.headword_norm == query or entry.lexeme_norm == query:
            return 1000.0
        if entry.lexeme_norm.startswith(query):
            return 960.0 - min(40.0, len(entry.lexeme_norm) - len(query))
        if entry.headword_norm.startswith(query):
            return 940.0 - min(40.0, len(entry.headword_norm) - len(query))
        lexeme_tokens = entry.lexeme_norm.split()
        if query in lexeme_tokens:
            return 925.0
        if query in entry.lexeme_norm:
            return 900.0
        if entry.translation_norm == query:
            return 875.0
        if entry.translation_norm.startswith(query):
            return 850.0
        if query in entry.translation_norm:
            return 825.0
        if query in entry.search_norm:
            return 775.0
        return 0.0

    def search(self, query: str, limit: int = 20, fuzzy_threshold: int = 58) -> list[SearchResult]:
        normalized_query = normalize_text(query)
        if not normalized_query:
            return [SearchResult(entry, 0.0) for entry in self.entries[:limit]]

        scored: dict[int, float] = {}

        # Cheap exact/substring scan over all entries to guarantee complete direct matches.
        for idx, entry in enumerate(self.entries):
            score = self._exact_score(entry, normalized_query)
            if score:
                scored[idx] = score

        # Fuzzy scoring is limited to trigram-overlap candidates for speed.
        for idx in self._candidate_indices(normalized_query):
            if idx in scored and scored[idx] >= 825:
                continue
            entry = self.entries[idx]
            head_score = max(
                _similarity(normalized_query, entry.headword_norm),
                _similarity(normalized_query, entry.lexeme_norm),
            )
            translation_score = _similarity(normalized_query, entry.translation_norm)
            token_score = 0.0
            for token in entry.search_norm.split()[:120]:
                if abs(len(token) - len(normalized_query)) <= max(3, len(normalized_query) // 2):
                    token_score = max(token_score, _similarity(normalized_query, token))
                    if token_score >= 96:
                        break
            fuzzy_score = max(head_score * 1.25, translation_score * 1.08, token_score)
            if fuzzy_score >= fuzzy_threshold:
                scored[idx] = max(scored.get(idx, 0.0), 500.0 + fuzzy_score)

        ranked = sorted(
            (SearchResult(self.entries[idx], score) for idx, score in scored.items()),
            key=lambda result: (-result.score, result.entry.headword_norm, result.entry.first_line),
        )
        return ranked[:limit]

    @staticmethod
    def _write_entries_atomic(
        database_path: str | os.PathLike[str], entries: Iterable[DictionaryEntry]
    ) -> None:
        path = Path(database_path)
        if not path.exists():
            raise FileNotFoundError(f"Dictionary database not found: {path}")
        content = "\n\n".join(entry.raw.strip() for entry in entries if entry.raw.strip())
        if content:
            content += "\n"
        temp_path = path.with_name(f".{path.name}.tmp")
        try:
            with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            try:
                temp_path.unlink()
            except FileNotFoundError:
                pass

    def replace_entry(
        self,
        database_path: str | os.PathLike[str],
        entry_index: int,
        raw_entry: str,
    ) -> DictionaryEntry:
        if not 0 <= entry_index < len(self.entries):
            raise IndexError("Dictionary entry no longer exists.")
        replacement = parse_entry(raw_entry)
        for idx, existing in enumerate(self.entries):
            if idx != entry_index and existing.duplicate_key == replacement.duplicate_key:
                raise DuplicateEntryError(replacement.headword, replacement.role)
        updated = list(self.entries)
        updated[entry_index] = replacement
        self._write_entries_atomic(database_path, updated)
        self.__init__(updated)
        return replacement

    def delete_entry(
        self, database_path: str | os.PathLike[str], entry_index: int
    ) -> DictionaryEntry:
        if not 0 <= entry_index < len(self.entries):
            raise IndexError("Dictionary entry no longer exists.")
        removed = self.entries[entry_index]
        updated = list(self.entries)
        del updated[entry_index]
        self._write_entries_atomic(database_path, updated)
        self.__init__(updated)
        return removed

    def add_entry(self, database_path: str | os.PathLike[str], raw_entry: str) -> DictionaryEntry:
        entry = parse_entry(raw_entry)
        if self.contains_duplicate(entry):
            raise DuplicateEntryError(entry.headword, entry.role)

        path = Path(database_path)
        if not path.exists():
            raise FileNotFoundError(f"Dictionary database not found: {path}")

        with path.open("rb+") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            separator = b""
            if size:
                read_size = min(size, 4)
                handle.seek(-read_size, os.SEEK_END)
                tail = handle.read(read_size)
                if tail.endswith(b"\n\n"):
                    separator = b""
                elif tail.endswith(b"\n"):
                    separator = b"\n"
                else:
                    separator = b"\n\n"
            handle.seek(0, os.SEEK_END)
            handle.write(separator + entry.raw.encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())

        # Update the in-memory index without reparsing the full file.
        new_index = len(self.entries)
        self.entries.append(entry)
        self._duplicate_keys.add(entry.duplicate_key)
        for trigram in entry.trigrams:
            self._trigram_map.setdefault(trigram, set()).add(new_index)
        return entry


class DuplicateEntryError(ValueError):
    def __init__(self, headword: str, role: str) -> None:
        self.headword = headword
        self.role = role
        super().__init__(f'"{headword}" already exists with role "{role}".')
