from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dictionary_core import (
    DictionaryIndex,
    DuplicateEntryError,
    german_inflection_stems,
    normalize_text,
    parse_entry,
    split_entries,
)


SAMPLE = """der Tisch [tɪʃ]: table
Bedeutung: Möbelstück.
ex: Das Buch liegt auf dem Tisch: The book is on the table.

zurechtweisen (jdn.) transitiv: to reprimand; sarzanesh kardan
ex: Der Lehrer weist den Schüler zurecht: The teacher reprimands the student.

die Gelegenheit [ɡəˈleːɡn̩haɪ̯t]: opportunity
Bedeutung: eine gute Möglichkeit.
"""


class DictionaryCoreTests(unittest.TestCase):
    def test_split_entries(self) -> None:
        self.assertEqual(len(split_entries(SAMPLE)), 3)

    def test_normalization(self) -> None:
        self.assertEqual(normalize_text("Schöpfen"), "schopfen")
        self.assertEqual(normalize_text("كیف"), "کیف")

    def test_parse_role_and_headword(self) -> None:
        entry = parse_entry(split_entries(SAMPLE)[0])
        self.assertEqual(entry.headword, "der Tisch")
        self.assertEqual(entry.role, "noun")

    def test_search_german_english_penglish_and_typo(self) -> None:
        index = DictionaryIndex(parse_entry(raw) for raw in split_entries(SAMPLE))
        self.assertEqual(index.search("Tisch", 1)[0].entry.headword, "der Tisch")
        self.assertEqual(index.search("opportunity", 1)[0].entry.headword, "die Gelegenheit")
        self.assertEqual(index.search("sarzanesh", 1)[0].entry.headword, "zurechtweisen")
        self.assertEqual(index.search("Gelegenhait", 1)[0].entry.headword, "die Gelegenheit")

    def test_inflected_nouns_and_adjectives_find_base_form(self) -> None:
        sample = """der Hund: dog

das Haus: house

die Frau: woman

der Name: name

golden (Adjektiv): golden

klein: small

groß: big

die Größe: size
"""
        index = DictionaryIndex(
            parse_entry(raw)
            for raw in split_entries(sample)
        )

        self.assertEqual(
            index.search("Hunde", 1)[0].entry.headword,
            "der Hund",
        )
        self.assertEqual(
            index.search("Häuser", 1)[0].entry.headword,
            "das Haus",
        )
        self.assertEqual(
            index.search("Frauen", 1)[0].entry.headword,
            "die Frau",
        )
        self.assertEqual(
            index.search("Namen", 1)[0].entry.headword,
            "der Name",
        )
        self.assertEqual(
            index.search("goldenen", 1)[0].entry.headword,
            "golden",
        )
        self.assertEqual(
            index.search("kleinen", 1)[0].entry.headword,
            "klein",
        )
        self.assertEqual(
            index.search("großen", 1)[0].entry.headword,
            "groß",
        )
        self.assertEqual(
            index.search("Größen", 1)[0].entry.headword,
            "die Größe",
        )
        self.assertIn(
            "haus",
            german_inflection_stems("Häuser"),
        )

    def test_duplicate_prevention_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.txt"
            path.write_text(SAMPLE, encoding="utf-8")
            index = DictionaryIndex.from_file(path)
            with self.assertRaises(DuplicateEntryError):
                index.add_entry(path, "der Tisch: desk\nBedeutung: duplicate noun")

            index.add_entry(path, "tischen transitiv: to serve\nex: Wir tischen das Essen auf: We serve food.")
            self.assertIn("tischen transitiv", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
