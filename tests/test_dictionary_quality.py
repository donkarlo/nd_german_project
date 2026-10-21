from __future__ import annotations

import unittest

from dictionary_core import parse_entry
from dictionary_quality import DictionaryQuality


class DictionaryQualityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.quality = DictionaryQuality()

    def test_impossible_auxiliaries_corrected_without_changing_participle(self) -> None:
        for raw, expected in (
            ("lernen [x] (Verb): learn\nPerfekt: ich haben gelernt", "Perfekt: ich habe gelernt"),
            ("kommen [x] (Verb): come\nPerfekt: ich sein gekommen", "Perfekt: ich bin gekommen"),
        ):
            repaired, categories = self.quality.normalize(raw)
            self.assertIn(expected, repaired)
            self.assertEqual(categories, ("perfect_auxiliary",))

    def test_correct_forms_remain_unchanged(self) -> None:
        raw = "verstehen [x] (Verb): understand\nPerfekt: ich habe verstanden"
        self.assertEqual(self.quality.normalize(raw), (raw, ()))

    def test_all_curated_entries_have_required_translations_and_examples(self) -> None:
        for headword, raw in self.quality.CURATED.items():
            with self.subTest(headword=headword):
                parsed = parse_entry(raw)
                self.assertTrue(parsed.headword)
                for label in ("English:", "Persian:", "Penglish:", "Bedeutung:"):
                    self.assertIn("\n" + label, raw)
                self.assertGreaterEqual(sum(line.startswith("ex:") for line in raw.splitlines()), 2)
                self.assertEqual(self.quality.normalize(raw, headword), (raw, ()))
                self.assertEqual(self.quality.issues(raw, parsed.role), ())

    def test_spassen_means_joking_not_having_fun(self) -> None:
        raw = self.quality.CURATED["spaßen"]
        self.assertIn("شوخی کردن", raw)
        self.assertIn("You're just joking", raw)
        self.assertNotIn("gonna let you have fun", raw)
        self.assertIn("Perfekt: ich habe gespaßt", raw)

    def test_verb_persian_noun_is_reported(self) -> None:
        self.assertIn("persian_infinitive",
                      self.quality.issues("spaßen: joke\nPersian: شوخی\nex: one\nex: two", "verb"))
