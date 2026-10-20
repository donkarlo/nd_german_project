#!/usr/bin/env python3
"""Batch import complete dictionary entries to the primary SQLite database.

Usage:
  python3 bulk_import_dictionary.py entries.txt --batch-size 250
  python3 bulk_import_dictionary.py entries.txt --dry-run

Input: entries in the established dictionary format, separated by blank lines.
Uses the application's parser and FTS normalization, skips existing headword+role,
and commits bounded transactions without rebuilding the GUI model for every word.
"""
import argparse
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src" / "nd_german"))
import dictionary_core
import sqlite_search_patch as backend

DB = Path("/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or args.batch_size > 1000:
        parser.error("--batch-size must be between 1 and 1000")
    blocks = [part.strip() for part in args.input.read_text(encoding="utf-8-sig").split("\n\n") if part.strip()]
    parsed = [dictionary_core.parse_entry(part) for part in blocks]
    conn = sqlite3.connect(str(DB), timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store=FILE")
    try:
        existing = set(conn.execute("SELECT headword_norm,role FROM entries"))
        idx = conn.execute("SELECT COALESCE(MAX(entry_index),-1)+1 FROM entries").fetchone()[0]
        pending = []
        duplicates = 0
        for ent in parsed:
            key = (ent.headword_norm, ent.role)
            if key in existing:
                duplicates += 1
                continue
            existing.add(key)
            pending.append((idx, ent))
            idx += 1
        print(f"input={len(parsed)}, new={len(pending)}, already_present={duplicates}", flush=True)
        if args.dry_run:
            return
        start = time.monotonic()
        for offset in range(0, len(pending), args.batch_size):
            chunk = pending[offset:offset + args.batch_size]
            with conn:
                conn.executemany("""INSERT INTO entries
                    (entry_index,raw,first_line,headword,role,translation,
                     headword_norm,lexeme_norm,translation_norm,search_norm)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    [(i,e.raw,e.first_line,e.headword,e.role,e.translation,
                      e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm) for i,e in chunk])
                conn.executemany("""INSERT INTO entries_fts
                    (rowid,headword_norm,lexeme_norm,translation_norm,search_norm)
                    VALUES (?,?,?,?,?)""",
                    [(i,e.headword_norm,e.lexeme_norm,e.translation_norm,e.search_norm)
                     for i,e in chunk])
            print(f"committed={min(offset+len(chunk), len(pending))}/{len(pending)} "
                  f"elapsed={time.monotonic()-start:.1f}s", flush=True)
        print("integrity:", conn.execute("PRAGMA quick_check").fetchone()[0], flush=True)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
