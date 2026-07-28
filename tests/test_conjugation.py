from __future__ import annotations

import unittest
from pathlib import Path

from conjugation_core import GermanConjugator, IrregularVerbDatabase


ROOT = Path(__file__).resolve().parents[1]


class ConjugationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = IrregularVerbDatabase.from_file(ROOT / "irregular_verbs.yaml")
        cls.conjugator = GermanConjugator(cls.database)

    def card(self, result, section: str, tense: str) -> list[str]:
        return dict(result.sections[section])[tense]

    def test_database_limit(self) -> None:
        self.assertLessEqual(len(self.database.records), 2000)
        self.assertGreaterEqual(len(self.database.records), 150)

    def test_haben(self) -> None:
        result = self.conjugator.conjugate("haben")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[1], "du hast")
        self.assertEqual(self.card(result, "KONJUNKTIV II", "Präteritum")[0], "ich hätte")
        self.assertEqual(result.imperatives, ["hab (du)", "habt (ihr)", "haben Sie"])

    def test_regular_arbeiten(self) -> None:
        result = self.conjugator.conjugate("arbeiten")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[1], "du arbeitest")
        self.assertEqual(self.card(result, "INDIKATIV", "Präteritum")[0], "ich arbeitete")
        self.assertEqual(result.participle, "gearbeitet")
        self.assertEqual(result.imperatives[0], "arbeite (du)")

    def test_separable_irregular_inheritance(self) -> None:
        result = self.conjugator.conjugate("aufstehen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[0], "ich stehe auf")
        self.assertEqual(self.card(result, "INDIKATIV", "Präteritum")[0], "ich stand auf")
        self.assertEqual(result.participle, "aufgestanden")
        self.assertEqual(result.imperatives[0], "steh auf (du)")
        self.assertIn(("zu + Infinitiv", "aufzustehen"), result.infinitives)

    def test_inseparable_irregular_inheritance(self) -> None:
        result = self.conjugator.conjugate("verstehen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präteritum")[0], "ich verstand")
        self.assertEqual(result.participle, "verstanden")

    def test_regular_separable(self) -> None:
        result = self.conjugator.conjugate("aufmachen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[0], "ich mache auf")
        self.assertEqual(result.participle, "aufgemacht")
        self.assertEqual(result.imperatives[0], "mach auf (du)")

    def test_three_imperatives_for_irregular(self) -> None:
        result = self.conjugator.conjugate("geben")
        self.assertEqual(result.imperatives, ["gib (du)", "gebt (ihr)", "geben Sie"])

    def test_sein_formal_imperative(self) -> None:
        result = self.conjugator.conjugate("sein")
        self.assertEqual(result.imperatives, ["sei (du)", "seid (ihr)", "seien Sie"])

    def test_strong_preterite_sibilant_endings(self) -> None:
        result = self.conjugator.conjugate("lesen")
        forms = self.card(result, "INDIKATIV", "Präteritum")
        self.assertEqual(forms[1], "du lasest")
        self.assertEqual(forms[4], "ihr last")

    def test_mussen_is_interpreted_as_muessen(self) -> None:
        result = self.conjugator.conjugate("mussen")
        self.assertEqual(result.infinitive, "müssen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[0], "ich muss")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[3], "wir müssen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präteritum")[0], "ich musste")
        self.assertEqual(self.card(result, "KONJUNKTIV I", "Präsens")[0], "ich müsse")
        self.assertEqual(self.card(result, "KONJUNKTIV II", "Präteritum")[0], "ich müsste")
        self.assertEqual(result.imperatives[0], "müsse (du)")
        self.assertIn("interpreted as “müssen”", result.note)

    def test_digraph_keyboard_alias(self) -> None:
        result = self.conjugator.conjugate("muessen")
        self.assertEqual(result.infinitive, "müssen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[1], "du musst")

    def test_alias_for_prefixed_compound(self) -> None:
        result = self.conjugator.conjugate("zuruckkommen")
        self.assertEqual(result.infinitive, "zurückkommen")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[0], "ich komme zurück")
        self.assertEqual(result.participle, "zurückgekommen")

    def test_variable_prefixes(self) -> None:
        separable = self.conjugator.conjugate("umsteigen")
        self.assertEqual(self.card(separable, "INDIKATIV", "Präsens")[0], "ich steige um")
        self.assertEqual(separable.participle, "umgestiegen")

        inseparable = self.conjugator.conjugate("übernehmen")
        self.assertEqual(self.card(inseparable, "INDIKATIV", "Präsens")[0], "ich übernehme")
        self.assertEqual(self.card(inseparable, "INDIKATIV", "Präteritum")[0], "ich übernahm")
        self.assertEqual(inseparable.participle, "übernommen")

    def test_regular_nonseparable_participle(self) -> None:
        result = self.conjugator.conjugate("übernachten")
        self.assertEqual(result.participle, "übernachtet")
        self.assertEqual(self.card(result, "INDIKATIV", "Präsens")[0], "ich übernachte")

        keyboard_spelling = self.conjugator.conjugate("ubernachten")
        self.assertEqual(keyboard_spelling.infinitive, "übernachten")
        self.assertEqual(keyboard_spelling.participle, "übernachtet")

    def test_participle_i_special_forms(self) -> None:
        self.assertIn(("Präsens", "seiend"), self.conjugator.conjugate("sein").participles)
        self.assertIn(("Präsens", "tuend"), self.conjugator.conjugate("tun").participles)
        self.assertIn(("Präsens", "antuend"), self.conjugator.conjugate("antun").participles)

    def test_every_database_verb_generates_complete_tables(self) -> None:
        for verb in self.database.records:
            with self.subTest(verb=verb):
                result = self.conjugator.conjugate(verb)
                self.assertEqual(len(result.imperatives), 3)
                for cards in result.sections.values():
                    for _title, forms in cards:
                        self.assertEqual(len(forms), 6)


if __name__ == "__main__":
    unittest.main()
