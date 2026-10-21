#!/usr/bin/env python3
"""Audit and conservatively repair the primary SQLite German dictionary.

Uses a transactional migration with SQLite's online backup API, repairs only
high-confidence grammatical errors and reviewed lexical entries, then refreshes
FTS and derived valency tables.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "nd_german"))

import dictionary_core
from dictionary_quality import DictionaryQuality

DEFAULT_DATABASE = Path("/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3")
DUPLICATE_NOUNS = {
    "das": ("das Verb", "das Verb"),
    "Mittagessen": ("Mittagessen (das,", "das Mittagessen"),
    "Abendessen": ("Abendessen (das,", "das Abendessen"),
    "Eltern": ("Eltern (Plural)", "die Eltern"),
}


class SQLiteDictionaryRepair:
    def __init__(self, database: Path):
        self.database = database
        self.quality = DictionaryQuality()

    @staticmethod
    def _values(index: int, entry: dictionary_core.DictionaryEntry) -> tuple:
        return (entry.raw, entry.first_line, entry.headword, entry.role,
                entry.translation, entry.headword_norm, entry.lexeme_norm,
                entry.translation_norm, entry.search_norm, index)

    def prepare(self, connection: sqlite3.Connection):
        rows = connection.execute("SELECT entry_index,headword,role,raw FROM entries ORDER BY entry_index").fetchall()
        existing_nouns = {headword for _,headword,role,_ in rows if role == "noun"}
        noun_lexemes = {dictionary_core.normalize_text(dictionary_core.parse_entry(raw).lexeme_norm)
                        for _,headword,role,raw in rows if role == "noun"}
        changed = []
        duplicates = []
        counts = Counter()
        seen_canonical: set[tuple[str, str, str]] = set()
        for index,headword,role,raw in rows:
            if headword in DUPLICATE_NOUNS and role == "verb":
                prefix, proper_noun = DUPLICATE_NOUNS[headword]
                if raw.startswith(prefix) and proper_noun in existing_nouns:
                    duplicates.append(index)
                    counts["duplicate_wrong_role"] += 1
                    continue
            if (role == "unknown" and headword and headword[0].isupper()
                    and headword not in {"Nordafrika"}
                    and dictionary_core.normalize_text(headword) in noun_lexemes):
                duplicates.append(index)
                counts["duplicate_unclassified_noun"] += 1
                continue
            fixed, reasons = self.quality.normalize(raw, headword)
            parsed = dictionary_core.parse_entry(fixed)
            canonical_key = (parsed.headword_norm, parsed.role, fixed)
            if canonical_key in seen_canonical:
                duplicates.append(index)
                counts["duplicate_identical_entry"] += 1
                continue
            seen_canonical.add(canonical_key)
            if fixed == raw:
                continue
            if parsed.headword != headword and headword not in {"Regen", "inwieweit"}:
                raise ValueError(f"Unexpected headword change for {headword}: {parsed.headword}")
            changed.append((index, parsed))
            counts.update(reasons)
        return rows, changed, duplicates, counts

    def run(self, apply: bool) -> Counter:
        if not self.database.exists():
            raise FileNotFoundError(self.database)
        connection = sqlite3.connect(str(self.database), timeout=30)
        try:
            connection.execute("PRAGMA busy_timeout=30000")
            rows, changed, duplicates, counts = self.prepare(connection)
            print(f"total_entries={len(rows)}")
            print(f"rows_to_correct={len(changed)} duplicate_wrong_role_to_remove={len(duplicates)}")
            print("correction_categories:", dict(counts))
            if not apply:
                print("dry_run=true")
                return counts

            backup_dir = self.database.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / (
                "dictionary.before_quality_repair_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".sqlite3"
            )
            if backup_path.exists():
                raise FileExistsError(f"Refusing to overwrite existing backup: {backup_path}")
            with sqlite3.connect(str(backup_path)) as backup:
                connection.backup(backup)
            print("backup:", backup_path, flush=True)

            connection.execute("BEGIN IMMEDIATE")
            try:
                connection.executemany(
                    """UPDATE entries SET raw=?,first_line=?,headword=?,role=?,translation=?,
                       headword_norm=?,lexeme_norm=?,translation_norm=?,search_norm=?
                       WHERE entry_index=?""",
                    (self._values(index, entry) for index, entry in changed),
                )
                for index in duplicates:
                    connection.execute("DELETE FROM entries WHERE entry_index=?", (index,))

                if duplicates:
                    # Preserve the UI invariant: entry_index == position in search model.
                    duplicate_ids = set(duplicates)
                    active_ids = [idx for idx,_,_,_ in rows if idx not in duplicate_ids]
                    highest_index = max(active_ids) + 100000
                    connection.execute("UPDATE entries SET entry_index=entry_index+?", (highest_index,))
                    connection.executemany(
                        "UPDATE entries SET entry_index=? WHERE entry_index=?",
                        ((new_id, old_id + highest_index) for new_id, old_id in enumerate(active_ids)),
                    )

                connection.execute("DELETE FROM entries_fts")
                connection.execute(
                    """INSERT INTO entries_fts
                       (rowid,headword_norm,lexeme_norm,translation_norm,search_norm)
                       SELECT entry_index,headword_norm,lexeme_norm,translation_norm,search_norm
                       FROM entries ORDER BY entry_index"""
                )
                remaining = connection.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
                indexed = connection.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0]
                if remaining != len(rows)-len(duplicates) or indexed != remaining:
                    raise RuntimeError("Row/FTS count mismatch")
                indices = connection.execute(
                    "SELECT MIN(entry_index),MAX(entry_index) FROM entries").fetchone()
                if indices != (0, remaining-1):
                    raise RuntimeError(f"Non-contiguous entry indices: {indices}, count={remaining}")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            print(f"primary_update_completed={len(changed)} remaining_entries={remaining}", flush=True)
        finally:
            connection.close()
        # The Rektion tables are derived from primary entry rows, and contain
        # entry_index_snapshot; rebuild after deleting duplicate records.
        import verb_valency
        result = verb_valency.migrate_all(self.database, text_path=None, force=True)
        print("rektion_index:", result, flush=True)

        with sqlite3.connect(str(self.database)) as verify:
            integrity = verify.execute("PRAGMA integrity_check").fetchone()[0]
            print("integrity_check:", integrity)
            if integrity != "ok":
                raise RuntimeError(f"SQLite integrity check failed: {integrity}")
            bad_aux = verify.execute(
                "SELECT COUNT(*) FROM entries WHERE role='verb' AND "
                "(raw LIKE '%Perfekt: ich haben %' OR raw LIKE '%Perfekt: ich sein %')"
            ).fetchone()[0]
            if bad_aux:
                raise RuntimeError(f"Uncorrected verb auxiliary patterns: {bad_aux}")
        return counts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--apply", action="store_true",
                        help="Back up and modify the primary database")
    args = parser.parse_args()
    SQLiteDictionaryRepair(args.database).run(args.apply)


if __name__ == "__main__":
    main()
