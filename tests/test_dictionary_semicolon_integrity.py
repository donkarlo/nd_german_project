"""Regression tests for canonical multilingual segmentation and SQLite consistency.

No missing Rektion is asserted here: verbs without lexically governed complements
must not be given invented frames.
"""
import sqlite3
import re
import unittest
from pathlib import Path

DB = Path('/home/donkarlo/Dropbox/repo/data/nd_german_project/dictionary.sqlite3')


class DictionarySemanticSeparatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = sqlite3.connect(str(DB))
        cls.entries = cls.db.execute('SELECT entry_index, headword, role, raw FROM entries').fetchall()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_sqlite_integrity(self):
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertFalse(self.db.execute('PRAGMA foreign_key_check').fetchall())

    def test_fulltext_count(self):
        self.assertEqual(len(self.entries), self.db.execute('SELECT COUNT(*) FROM entries_fts').fetchone()[0])

    def test_canonical_semicolons_and_penglish_alignment(self):
        bad=[]
        for idx, head, _role, raw in self.entries:
            fields={}
            for line in raw.splitlines():
                if line.startswith(('English:', 'Persian:', 'Penglish:')):
                    name,val=line.split(':',1)
                    fields[name]=val.strip()
            for name in ('English', 'Persian', 'Penglish'):
                s=fields.get(name,'')
                if not s or '؛' in s or re.search(r'\s;|;\S|;\s*;',s):
                    bad.append((idx,head,name,'wrong separator'))
            if fields.get('Persian','').count(';')!=fields.get('Penglish','').count(';'):
                bad.append((idx,head,'Penglish','meaning count mismatch'))
            if re.search('[\u0600-\u06ff]', fields.get('Penglish','')):
                bad.append((idx,head,'Penglish','not romanized'))
        self.assertFalse(bad, f'Found {len(bad)} multilingual errors. First ten: {bad[:10]}')

    def test_no_synthetic_intransitive_rektion(self):
        bad=[(idx,head) for idx,head,role,raw in self.entries if
             'Rektion: (intransitiv; kein obligatorisches Objekt)' in raw]
        self.assertFalse(bad, f'Synthetic Rektion must be omitted: {bad[:10]}')


if __name__=='__main__':
    unittest.main()
