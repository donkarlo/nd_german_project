from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import dictionary_core


_LOCK = threading.RLock()
_SOURCE_PATH: Path | None = None
_SQLITE_PATH: Path | None = None
_FALLBACK_SEARCH = None
_ENABLED = False
_FTS5 = False

_SCHEMA_VERSION = "2"
_PRIMARY_MODE_KEY = "sqlite_primary"
_PRIMARY_MODE_VALUE = "1"


def configure(source_path: Path, sqlite_path: Path) -> None:
    global _SOURCE_PATH, _SQLITE_PATH
    _SOURCE_PATH = Path(source_path).expanduser().resolve()
    _SQLITE_PATH = Path(sqlite_path).expanduser().resolve()


def _require_paths() -> tuple[Path, Path]:
    if _SOURCE_PATH is None or _SQLITE_PATH is None:
        raise RuntimeError("SQLite dictionary backend is not configured.")
    return _SOURCE_PATH, _SQLITE_PATH


def _open_connection(*, write: bool = False) -> sqlite3.Connection:
    _, sqlite_path = _require_paths()
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(sqlite_path), timeout=0.35, isolation_level=None)
    connection.execute("PRAGMA busy_timeout=300")
    if write:
        connection.execute("PRAGMA synchronous=NORMAL")
    return connection


@contextmanager
def _connection(*, write: bool = False):
    connection = _open_connection(write=write)
    try:
        yield connection
    finally:
        connection.close()


def _create_schema(connection: sqlite3.Connection) -> bool:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS entries (
            entry_index INTEGER PRIMARY KEY,
            raw TEXT NOT NULL,
            first_line TEXT NOT NULL,
            headword TEXT NOT NULL,
            role TEXT NOT NULL,
            translation TEXT NOT NULL,
            headword_norm TEXT NOT NULL,
            lexeme_norm TEXT NOT NULL,
            translation_norm TEXT NOT NULL,
            search_norm TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_entries_headword_norm
            ON entries(headword_norm);
        CREATE INDEX IF NOT EXISTS idx_entries_lexeme_norm
            ON entries(lexeme_norm);
        CREATE INDEX IF NOT EXISTS idx_entries_translation_norm
            ON entries(translation_norm);
        """
    )

    try:
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                headword_norm,
                lexeme_norm,
                translation_norm,
                search_norm,
                tokenize='unicode61 remove_diacritics 2'
            )
            """
        )
        return True
    except sqlite3.OperationalError:
        return False


def _meta_get(connection: sqlite3.Connection, key: str) -> str | None:
    row = connection.execute(
        "SELECT value FROM meta WHERE key = ?",
        (key,),
    ).fetchone()
    return None if row is None else str(row[0])


def _meta_set(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        (key, value),
    )


def _source_signature(path: Path) -> tuple[str, str]:
    stat = path.stat()
    return str(stat.st_size), str(stat.st_mtime_ns)


def _stored_source_signature(connection: sqlite3.Connection) -> tuple[str, str] | None:
    size = _meta_get(connection, "source_size")
    mtime = _meta_get(connection, "source_mtime_ns")
    if size is None or mtime is None:
        return None
    return size, mtime


def _remember_source_signature(connection: sqlite3.Connection, source_path: Path) -> None:
    size, mtime = _source_signature(source_path)
    _meta_set(connection, "source_size", size)
    _meta_set(connection, "source_mtime_ns", mtime)


def _entry_values(index: int, entry) -> tuple:
    return (
        index,
        entry.raw,
        entry.first_line,
        entry.headword,
        entry.role,
        entry.translation,
        entry.headword_norm,
        entry.lexeme_norm,
        entry.translation_norm,
        entry.search_norm,
    )


def _insert_entry(connection: sqlite3.Connection, index: int, entry) -> None:
    connection.execute(
        """
        INSERT INTO entries(
            entry_index, raw, first_line, headword, role, translation,
            headword_norm, lexeme_norm, translation_norm, search_norm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _entry_values(index, entry),
    )
    if _FTS5:
        connection.execute(
            """
            INSERT INTO entries_fts(
                rowid, headword_norm, lexeme_norm, translation_norm, search_norm
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                index,
                entry.headword_norm,
                entry.lexeme_norm,
                entry.translation_norm,
                entry.search_norm,
            ),
        )


def _replace_entry_row(connection: sqlite3.Connection, index: int, entry) -> None:
    connection.execute(
        """
        UPDATE entries
        SET raw = ?,
            first_line = ?,
            headword = ?,
            role = ?,
            translation = ?,
            headword_norm = ?,
            lexeme_norm = ?,
            translation_norm = ?,
            search_norm = ?
        WHERE entry_index = ?
        """,
        (
            entry.raw,
            entry.first_line,
            entry.headword,
            entry.role,
            entry.translation,
            entry.headword_norm,
            entry.lexeme_norm,
            entry.translation_norm,
            entry.search_norm,
            index,
        ),
    )
    if _FTS5:
        connection.execute("DELETE FROM entries_fts WHERE rowid = ?", (index,))
        connection.execute(
            """
            INSERT INTO entries_fts(
                rowid, headword_norm, lexeme_norm, translation_norm, search_norm
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                index,
                entry.headword_norm,
                entry.lexeme_norm,
                entry.translation_norm,
                entry.search_norm,
            ),
        )


def _rebuild_fts(connection: sqlite3.Connection) -> None:
    if not _FTS5:
        return
    connection.execute("DELETE FROM entries_fts")
    connection.execute(
        """
        INSERT INTO entries_fts(
            rowid, headword_norm, lexeme_norm, translation_norm, search_norm
        )
        SELECT
            entry_index, headword_norm, lexeme_norm, translation_norm, search_norm
        FROM entries
        ORDER BY entry_index
        """
    )


def _load_entries_from_sqlite() -> list:
    with _connection() as connection:
        rows = connection.execute(
            "SELECT raw FROM entries ORDER BY entry_index"
        ).fetchall()
    return [dictionary_core.parse_entry(str(raw)) for (raw,) in rows]


def _import_text_database(source_path: Path) -> None:
    global _FTS5, _ENABLED

    text = source_path.read_text(encoding="utf-8")
    entries = [
        dictionary_core.parse_entry(raw)
        for raw in dictionary_core.split_entries(text)
    ]

    with _connection(write=True) as connection:
        _FTS5 = _create_schema(connection)
        connection.execute("BEGIN IMMEDIATE")
        try:
            connection.execute("DELETE FROM entries")
            if _FTS5:
                connection.execute("DELETE FROM entries_fts")
            for index, entry in enumerate(entries):
                _insert_entry(connection, index, entry)
            _remember_source_signature(connection, source_path)
            _meta_set(connection, "schema_version", _SCHEMA_VERSION)
            _meta_set(connection, _PRIMARY_MODE_KEY, _PRIMARY_MODE_VALUE)
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    _ENABLED = True


def ensure_primary_database() -> None:
    """Migrate once from the text database, then make SQLite authoritative."""
    global _FTS5, _ENABLED

    source_path, sqlite_path = _require_paths()
    if not source_path.is_file():
        raise FileNotFoundError(f"Dictionary source not found: {source_path}")

    with _LOCK:
        if not sqlite_path.exists():
            _import_text_database(source_path)
            return

        with _connection(write=True) as connection:
            _FTS5 = _create_schema(connection)
            primary = _meta_get(connection, _PRIMARY_MODE_KEY) == _PRIMARY_MODE_VALUE
            if primary:
                _meta_set(connection, "schema_version", _SCHEMA_VERSION)
                connection.commit()
                _ENABLED = True
                return

            # Upgrade the previous hybrid SQLite cache. If the text source changed
            # after that cache was built, import it once before switching authority.
            cached_signature = _stored_source_signature(connection)
            current_signature = _source_signature(source_path)
            needs_import = cached_signature != current_signature

        if needs_import:
            _import_text_database(source_path)
            return

        with _connection(write=True) as connection:
            _FTS5 = _create_schema(connection)
            _meta_set(connection, "schema_version", _SCHEMA_VERSION)
            _meta_set(connection, _PRIMARY_MODE_KEY, _PRIMARY_MODE_VALUE)
            connection.commit()

        _ENABLED = True


def _export_text_mirror() -> None:
    """Keep woerterbuch.txt as a readable backup/export, not as the live database."""
    source_path, _ = _require_paths()

    with _connection() as connection:
        rows = connection.execute(
            "SELECT raw FROM entries ORDER BY entry_index"
        ).fetchall()

    content = "\n\n".join(str(raw).strip() for (raw,) in rows if str(raw).strip())
    if content:
        content += "\n"

    temp_path = source_path.with_name(f".{source_path.name}.sqlite-export.tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, source_path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    with _connection(write=True) as connection:
        _remember_source_signature(connection, source_path)
        connection.commit()


def _duplicate_exists(
    connection: sqlite3.Connection,
    entry,
    *,
    exclude_index: int | None = None,
) -> bool:
    sql = """
        SELECT 1
        FROM entries
        WHERE headword_norm = ? AND role = ?
    """
    params: list[object] = [entry.headword_norm, entry.role]
    if exclude_index is not None:
        sql += " AND entry_index <> ?"
        params.append(exclude_index)
    sql += " LIMIT 1"
    return connection.execute(sql, tuple(params)).fetchone() is not None


def sqlite_from_file(cls, _path):
    ensure_primary_database()
    return cls(_load_entries_from_sqlite())


def sqlite_add(self, _database_path, raw_entry: str):
    ensure_primary_database()
    entry = dictionary_core.parse_entry(raw_entry)

    with _LOCK:
        with _connection(write=True) as connection:
            global _FTS5
            _FTS5 = _create_schema(connection)
            if _duplicate_exists(connection, entry):
                raise dictionary_core.DuplicateEntryError(entry.headword, entry.role)
            row = connection.execute(
                "SELECT COALESCE(MAX(entry_index), -1) + 1 FROM entries"
            ).fetchone()
            index = int(row[0])
            connection.execute("BEGIN IMMEDIATE")
            try:
                _insert_entry(connection, index, entry)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        updated = list(self.entries)
        updated.append(entry)
        self.__init__(updated)
        _export_text_mirror()

    return entry


def sqlite_replace(self, _database_path, entry_index: int, raw_entry: str):
    ensure_primary_database()
    if not 0 <= entry_index < len(self.entries):
        raise IndexError("Dictionary entry no longer exists.")

    replacement = dictionary_core.parse_entry(raw_entry)

    with _LOCK:
        with _connection(write=True) as connection:
            global _FTS5
            _FTS5 = _create_schema(connection)
            if _duplicate_exists(
                connection,
                replacement,
                exclude_index=entry_index,
            ):
                raise dictionary_core.DuplicateEntryError(
                    replacement.headword,
                    replacement.role,
                )

            connection.execute("BEGIN IMMEDIATE")
            try:
                _replace_entry_row(connection, entry_index, replacement)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        updated = list(self.entries)
        updated[entry_index] = replacement
        self.__init__(updated)
        _export_text_mirror()

    return replacement


def sqlite_delete(self, _database_path, entry_index: int):
    ensure_primary_database()
    if not 0 <= entry_index < len(self.entries):
        raise IndexError("Dictionary entry no longer exists.")

    removed = self.entries[entry_index]

    with _LOCK:
        with _connection(write=True) as connection:
            global _FTS5
            _FTS5 = _create_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute(
                    "DELETE FROM entries WHERE entry_index = ?",
                    (entry_index,),
                )
                # The UI uses the position in self.entries as the edit/delete id.
                # Keep SQLite indices contiguous so both representations stay aligned.
                rows = connection.execute(
                    """
                    SELECT entry_index
                    FROM entries
                    WHERE entry_index > ?
                    ORDER BY entry_index
                    """,
                    (entry_index,),
                ).fetchall()
                for (old_index,) in rows:
                    connection.execute(
                        "UPDATE entries SET entry_index = ? WHERE entry_index = ?",
                        (int(old_index) - 1, int(old_index)),
                    )

                _rebuild_fts(connection)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        updated = list(self.entries)
        del updated[entry_index]
        self.__init__(updated)
        _export_text_mirror()

    return removed


def _fts_expression(normalized_query: str) -> str:
    tokens = [token for token in normalized_query.split() if token]
    escaped = [token.replace('"', '""') for token in tokens]
    return " AND ".join(f'"{token}"*' for token in escaped)


def _candidate_indices(normalized_query: str, candidate_limit: int) -> list[int]:
    q = normalized_query
    upper = q + "\uffff"
    candidates: list[int] = []
    seen: set[int] = set()

    with _connection() as connection:
        # Equality/prefix matching is index-backed. The old instr(search_norm)
        # full-table scan is intentionally gone from the keystroke path.
        rows = connection.execute(
            """
            SELECT entry_index
            FROM entries
            WHERE
                headword_norm = ? OR
                lexeme_norm = ? OR
                (lexeme_norm >= ? AND lexeme_norm < ?) OR
                (headword_norm >= ? AND headword_norm < ?) OR
                translation_norm = ? OR
                (translation_norm >= ? AND translation_norm < ?)
            ORDER BY
                CASE
                    WHEN headword_norm = ? OR lexeme_norm = ? THEN 0
                    WHEN lexeme_norm >= ? AND lexeme_norm < ? THEN 1
                    WHEN headword_norm >= ? AND headword_norm < ? THEN 2
                    WHEN translation_norm = ? THEN 3
                    ELSE 4
                END,
                length(headword_norm),
                headword_norm
            LIMIT ?
            """,
            (
                q,
                q,
                q,
                upper,
                q,
                upper,
                q,
                q,
                upper,
                q,
                q,
                q,
                upper,
                q,
                upper,
                q,
                candidate_limit,
            ),
        )
        for (index,) in rows:
            index = int(index)
            if index not in seen:
                seen.add(index)
                candidates.append(index)

        if _FTS5 and len(candidates) < candidate_limit:
            expression = _fts_expression(q)
            if expression:
                try:
                    rows = connection.execute(
                        """
                        SELECT rowid
                        FROM entries_fts
                        WHERE entries_fts MATCH ?
                        ORDER BY bm25(entries_fts)
                        LIMIT ?
                        """,
                        (expression, candidate_limit),
                    )
                    for (index,) in rows:
                        index = int(index)
                        if index not in seen:
                            seen.add(index)
                            candidates.append(index)
                            if len(candidates) >= candidate_limit:
                                break
                except sqlite3.OperationalError:
                    pass

        # Preserve typo tolerance, but only score a bounded, index-backed group.
        compact_length = len(q.replace(" ", ""))
        if compact_length >= 3 and len(candidates) < min(70, candidate_limit):
            first = q[:1]
            first_upper = first + "\uffff"
            qlen = len(q)
            rows = connection.execute(
                """
                SELECT entry_index
                FROM entries
                WHERE lexeme_norm >= ? AND lexeme_norm < ?
                  AND length(lexeme_norm) BETWEEN ? AND ?
                ORDER BY abs(length(lexeme_norm) - ?), lexeme_norm
                LIMIT ?
                """,
                (
                    first,
                    first_upper,
                    max(1, qlen - 4),
                    qlen + 8,
                    qlen,
                    min(220, candidate_limit),
                ),
            )
            for (index,) in rows:
                index = int(index)
                if index not in seen:
                    seen.add(index)
                    candidates.append(index)
                    if len(candidates) >= candidate_limit:
                        break

    return candidates


def sqlite_search(self, query: str, limit: int = 20, fuzzy_threshold: int = 58):
    normalized_query = dictionary_core.normalize_text(query)
    if not normalized_query:
        return [
            dictionary_core.SearchResult(entry, 0.0)
            for entry in self.entries[:limit]
        ]

    if not _ENABLED:
        try:
            ensure_primary_database()
        except Exception:
            if _FALLBACK_SEARCH is not None:
                return _FALLBACK_SEARCH(
                    self,
                    query,
                    limit=limit,
                    fuzzy_threshold=fuzzy_threshold,
                )
            return []

    try:
        compact_length = len(normalized_query.replace(" ", ""))
        candidate_limit = 120 if compact_length < 3 else max(150, min(260, limit * 12))
        indices = _candidate_indices(normalized_query, candidate_limit)
    except (sqlite3.Error, OSError):
        if _FALLBACK_SEARCH is not None:
            return _FALLBACK_SEARCH(
                self,
                query,
                limit=limit,
                fuzzy_threshold=fuzzy_threshold,
            )
        return []

    persian_query = any("\u0600" <= char <= "\u06ff" for char in query)
    scored: list = []

    for index in indices:
        if not 0 <= index < len(self.entries):
            continue

        entry = self.entries[index]
        score = self._exact_score(entry, normalized_query)

        if score <= 0 and not persian_query and compact_length >= 3:
            head_score = max(
                dictionary_core._similarity(normalized_query, entry.headword_norm),
                dictionary_core._similarity(normalized_query, entry.lexeme_norm),
            )
            translation_score = dictionary_core._similarity(
                normalized_query,
                entry.translation_norm,
            )
            fuzzy_score = max(head_score * 1.25, translation_score * 1.08)
            if fuzzy_score >= fuzzy_threshold:
                score = 500.0 + fuzzy_score

        if score > 0:
            scored.append(dictionary_core.SearchResult(entry, score))

    scored.sort(
        key=lambda result: (
            -result.score,
            result.entry.headword_norm,
            result.entry.first_line,
        )
    )
    return scored[:limit]


def _sqlite_generate_missing_meanings(application, window) -> None:
    """Run the existing enrichment logic against SQLite, then export the text mirror."""
    patch = application.patch
    legacy = application.enrichment
    source_path, _ = _require_paths()

    done_path = source_path.with_name(patch.MIGRATION_NAME)
    progress_path = source_path.with_name(patch.PROGRESS_NAME)
    processed = patch._load_processed(progress_path)
    retry_delay = 6.0

    while True:
        try:
            with _connection() as connection:
                rows = connection.execute(
                    "SELECT entry_index, raw FROM entries ORDER BY entry_index"
                ).fetchall()

            force_iranian = not done_path.exists()
            candidates: list[tuple[int, str, str, dict[str, str], bool]] = []

            for entry_index, raw_value in rows:
                raw = str(raw_value)
                key = legacy.entry_key(raw)
                values = patch.language_values(raw)
                legacy_values = legacy.language_values(raw)
                needs_repair = values != legacy_values
                missing = any(
                    legacy.is_missing(values[label])
                    for label in legacy.LANGUAGE_LABELS
                )
                needs_iranian = force_iranian and key not in processed
                if needs_repair or missing or needs_iranian:
                    candidates.append(
                        (int(entry_index), key, raw, values, needs_iranian)
                    )

            window._meaning_generation_remaining = len(candidates)

            if not candidates:
                if force_iranian:
                    done_path.write_text(
                        "iranian-penglish-v1\n",
                        encoding="utf-8",
                    )
                    try:
                        progress_path.unlink()
                    except FileNotFoundError:
                        pass
                window._meaning_generation_finished = True
                return

            priority = patch._drain_priority()
            priority_order = {key: index for index, key in enumerate(priority)}
            candidates.sort(
                key=lambda item: (
                    priority_order.get(item[1], len(priority_order)),
                    0
                    if any(
                        legacy.is_missing(item[3][label])
                        for label in legacy.LANGUAGE_LABELS
                    )
                    else 1,
                    0
                    if application.patch.previous._suspicious_english(
                        legacy.language_values(item[2])["English"]
                    )
                    else 1,
                )
            )

            first_is_missing = any(
                legacy.is_missing(candidates[0][3][label])
                for label in legacy.LANGUAGE_LABELS
            )
            batch_size = 12 if priority or first_is_missing else 60

            updates: list[tuple[int, object]] = []
            newly_processed: list[str] = []
            failures = 0

            for entry_index, key, raw, values, needs_iranian in candidates[:batch_size]:
                try:
                    completed, changed, iranian_done = patch._complete_values(
                        raw,
                        values,
                        force_iranian_penglish=needs_iranian,
                    )
                except Exception:
                    failures += 1
                    continue

                if changed:
                    rebuilt = legacy.set_language_fields(raw, completed)
                    updates.append(
                        (entry_index, dictionary_core.parse_entry(rebuilt))
                    )

                if needs_iranian and iranian_done:
                    newly_processed.append(key)

                if any(
                    legacy.is_missing(completed[label])
                    for label in legacy.LANGUAGE_LABELS
                ):
                    failures += 1

                time.sleep(0.03)

            if updates:
                with _LOCK:
                    with _connection(write=True) as connection:
                        global _FTS5
                        _FTS5 = _create_schema(connection)
                        connection.execute("BEGIN IMMEDIATE")
                        try:
                            for entry_index, entry in updates:
                                _replace_entry_row(connection, entry_index, entry)
                            connection.commit()
                        except Exception:
                            connection.rollback()
                            raise
                    _export_text_mirror()

                window._meaning_generation_revision = (
                    getattr(window, "_meaning_generation_revision", 0) + 1
                )

            if newly_processed:
                patch._append_processed(progress_path, newly_processed)
                processed.update(newly_processed)

            window._meaning_generation_last_failures = failures

            if updates or newly_processed:
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


def install(application, base, *, source_path: Path, sqlite_path: Path) -> None:
    """Make SQLite authoritative while preserving the existing paste/edit UI."""
    global _FALLBACK_SEARCH

    configure(source_path, sqlite_path)
    _FALLBACK_SEARCH = application.ORIGINAL_INDEX_SEARCH

    try:
        ensure_primary_database()
    except Exception:
        # The application can still fall back to its old text-file behavior
        # if migration cannot complete.
        return

    # SQLite is now the source of truth. The text file is only an exported mirror.
    dictionary_core.DictionaryIndex.from_file = classmethod(sqlite_from_file)
    base.ORIGINAL_ADD = sqlite_add
    base.ORIGINAL_REPLACE = sqlite_replace
    base.ORIGINAL_DELETE = sqlite_delete

    # Prevent app_base's startup normalizer from treating the text mirror as live data.
    base.normalize_database = lambda _path: None

    # language_application.main() assigns DictionaryIndex.search to this symbol.
    application.fast_index_search = sqlite_search

    # language_application.main() also assigns base.generate_missing_meanings from
    # application.patch.generate_missing_meanings. Replace that target beforehand.
    def generate_missing_meanings(window):
        return _sqlite_generate_missing_meanings(application, window)

    application.patch.generate_missing_meanings = generate_missing_meanings

    # The old UI enforced >=220 ms. Keep a small debounce to coalesce very fast typing,
    # while letting SQLite/FTS respond nearly immediately.
    original_idle_factory = application.idle_window_init

    def sqlite_idle_factory(original_init):
        wrapped = original_idle_factory(original_init)

        def init(window, settings_path, settings):
            wrapped(window, settings_path, settings)
            requested = int(settings.get("search_debounce_ms", 80))
            window.search_timer.setInterval(max(45, min(90, requested)))

        return init

    application.idle_window_init = sqlite_idle_factory
