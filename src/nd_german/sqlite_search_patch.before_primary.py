from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import dictionary_core


_LOCK = threading.RLock()
_SOURCE_PATH: Path | None = None
_SQLITE_PATH: Path | None = None
_FALLBACK_SEARCH = None
_ENABLED = False
_FTS5 = False


def configure(source_path: Path, sqlite_path: Path) -> None:
    global _SOURCE_PATH, _SQLITE_PATH
    _SOURCE_PATH = Path(source_path).expanduser().resolve()
    _SQLITE_PATH = Path(sqlite_path).expanduser().resolve()


def _connect() -> sqlite3.Connection:
    if _SQLITE_PATH is None:
        raise RuntimeError("SQLite dictionary path is not configured.")
    _SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(_SQLITE_PATH), timeout=0.35)
    connection.execute("PRAGMA journal_mode=DELETE")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA busy_timeout=300")
    return connection


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


def _signature(path: Path) -> tuple[str, str]:
    stat = path.stat()
    return str(stat.st_size), str(stat.st_mtime_ns)


def _stored_signature(connection: sqlite3.Connection) -> tuple[str, str] | None:
    rows = dict(connection.execute("SELECT key, value FROM meta"))
    size = rows.get("source_size")
    mtime = rows.get("source_mtime_ns")
    if size is None or mtime is None:
        return None
    return size, mtime


def _set_signature(connection: sqlite3.Connection, source_path: Path) -> None:
    size, mtime = _signature(source_path)
    connection.executemany(
        "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)",
        [
            ("source_size", size),
            ("source_mtime_ns", mtime),
            ("schema_version", "1"),
        ],
    )


def _entry_row(index: int, entry) -> tuple:
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


def rebuild(source_path: Path | None = None) -> None:
    global _FTS5, _ENABLED

    path = Path(source_path or _SOURCE_PATH or "").expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"Dictionary source not found: {path}")

    with _LOCK:
        text = path.read_text(encoding="utf-8")
        parsed = [
            dictionary_core.parse_entry(raw)
            for raw in dictionary_core.split_entries(text)
        ]

        with _connect() as connection:
            _FTS5 = _create_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.execute("DELETE FROM entries")
                if _FTS5:
                    connection.execute("DELETE FROM entries_fts")

                rows = [_entry_row(index, entry) for index, entry in enumerate(parsed)]
                connection.executemany(
                    """
                    INSERT INTO entries(
                        entry_index, raw, first_line, headword, role, translation,
                        headword_norm, lexeme_norm, translation_norm, search_norm
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )

                if _FTS5:
                    connection.executemany(
                        """
                        INSERT INTO entries_fts(
                            rowid, headword_norm, lexeme_norm,
                            translation_norm, search_norm
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        [
                            (row[0], row[6], row[7], row[8], row[9])
                            for row in rows
                        ],
                    )

                _set_signature(connection, path)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

        _ENABLED = True


def ensure_fresh(source_path: Path | None = None, *, force: bool = False) -> None:
    global _FTS5, _ENABLED

    path = Path(source_path or _SOURCE_PATH or "").expanduser()
    if not path.is_file():
        return

    with _LOCK:
        if _SQLITE_PATH is None or not _SQLITE_PATH.exists():
            rebuild(path)
            return

        try:
            with _connect() as connection:
                _FTS5 = _create_schema(connection)
                stale = force or _stored_signature(connection) != _signature(path)
        except (sqlite3.Error, OSError):
            stale = True

        if stale:
            rebuild(path)
        else:
            _ENABLED = True


def _fts_expression(normalized_query: str) -> str:
    tokens = [token for token in normalized_query.split() if token]
    escaped = [token.replace('"', '""') for token in tokens]
    return " AND ".join(f'"{token}"*' for token in escaped)


def _candidate_indices(normalized_query: str, candidate_limit: int) -> list[int]:
    q = normalized_query
    prefix = q + "%"
    candidates: list[int] = []
    seen: set[int] = set()

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT entry_index
            FROM entries
            WHERE
                headword_norm = ? OR
                lexeme_norm = ? OR
                headword_norm LIKE ? OR
                lexeme_norm LIKE ? OR
                translation_norm = ? OR
                translation_norm LIKE ? OR
                instr(search_norm, ?) > 0
            ORDER BY
                CASE
                    WHEN headword_norm = ? OR lexeme_norm = ? THEN 0
                    WHEN lexeme_norm LIKE ? THEN 1
                    WHEN headword_norm LIKE ? THEN 2
                    WHEN translation_norm = ? THEN 3
                    WHEN translation_norm LIKE ? THEN 4
                    ELSE 5
                END,
                length(headword_norm),
                headword_norm
            LIMIT ?
            """,
            (
                q, q, prefix, prefix, q, prefix, q,
                q, q, prefix, prefix, q, prefix,
                candidate_limit,
            ),
        )
        for (index,) in rows:
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
                        if index not in seen:
                            seen.add(index)
                            candidates.append(index)
                            if len(candidates) >= candidate_limit:
                                break
                except sqlite3.OperationalError:
                    pass

        if len(q.replace(" ", "")) >= 3 and len(candidates) < min(80, candidate_limit):
            first = q[:1]
            qlen = len(q)
            rows = connection.execute(
                """
                SELECT entry_index
                FROM entries
                WHERE substr(headword_norm, 1, 1) = ?
                  AND length(headword_norm) BETWEEN ? AND ?
                ORDER BY abs(length(headword_norm) - ?), headword_norm
                LIMIT ?
                """,
                (
                    first,
                    max(1, qlen - 4),
                    qlen + 8,
                    qlen,
                    min(260, candidate_limit),
                ),
            )
            for (index,) in rows:
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
            ensure_fresh()
        except Exception:
            if _FALLBACK_SEARCH is not None:
                return _FALLBACK_SEARCH(
                    self, query, limit=limit, fuzzy_threshold=fuzzy_threshold
                )
            return []

    try:
        candidate_limit = max(180, min(420, limit * 20))
        indices = _candidate_indices(normalized_query, candidate_limit)
    except (sqlite3.Error, OSError):
        if _FALLBACK_SEARCH is not None:
            return _FALLBACK_SEARCH(
                self, query, limit=limit, fuzzy_threshold=fuzzy_threshold
            )
        return []

    scored: list = []
    persian_query = any("\u0600" <= char <= "\u06ff" for char in query)

    for index in indices:
        if not 0 <= index < len(self.entries):
            continue
        entry = self.entries[index]
        score = self._exact_score(entry, normalized_query)

        if score <= 0 and not persian_query:
            head_score = max(
                dictionary_core._similarity(normalized_query, entry.headword_norm),
                dictionary_core._similarity(normalized_query, entry.lexeme_norm),
            )
            translation_score = dictionary_core._similarity(
                normalized_query, entry.translation_norm
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


def install(application, base, *, source_path: Path, sqlite_path: Path) -> None:
    global _FALLBACK_SEARCH

    configure(source_path, sqlite_path)
    _FALLBACK_SEARCH = application.ORIGINAL_INDEX_SEARCH

    try:
        ensure_fresh()
    except Exception:
        pass

    application.fast_index_search = sqlite_search

    original_idle_factory = application.idle_window_init

    def sqlite_idle_factory(original_init):
        wrapped = original_idle_factory(original_init)

        def init(window, settings_path, settings):
            wrapped(window, settings_path, settings)
            requested = int(settings.get("search_debounce_ms", 80))
            window.search_timer.setInterval(max(60, min(110, requested)))

        return init

    application.idle_window_init = sqlite_idle_factory

    original_add = base.ORIGINAL_ADD
    original_replace = base.ORIGINAL_REPLACE
    original_delete = base.ORIGINAL_DELETE

    def synced_add(index, path, raw):
        result = original_add(index, path, raw)
        ensure_fresh(Path(path), force=True)
        return result

    def synced_replace(index, path, entry_index, raw):
        result = original_replace(index, path, entry_index, raw)
        ensure_fresh(Path(path), force=True)
        return result

    def synced_delete(index, path, entry_index):
        result = original_delete(index, path, entry_index)
        ensure_fresh(Path(path), force=True)
        return result

    base.ORIGINAL_ADD = synced_add
    base.ORIGINAL_REPLACE = synced_replace
    base.ORIGINAL_DELETE = synced_delete

    original_refresh = application.refresh_generated

    def sqlite_refresh(window, force: bool = False):
        original_refresh(window, force=force)
        try:
            ensure_fresh(Path(window.database_path))
        except Exception:
            pass

    application.refresh_generated = sqlite_refresh
