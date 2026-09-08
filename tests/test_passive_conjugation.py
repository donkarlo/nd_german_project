from __future__ import annotations

import unittest
from pathlib import Path

from conjugation_core import IrregularVerbDatabase
from conjugation_passive import PASSIVE_SECTION_TITLE, PassiveGermanConjugator


ROOT = Path(__file__).resolve().parents[1]


class PassiveConjugationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        database = IrregularVerbDatabase.from_file(ROOT / "data" / "irregular_verbs.yaml")
        cls.conjugator = PassiveGermanConjugator(database)

    def passive_card(self, result, tense: str) -> list[str]:
        return dict(result.sections[PASSIVE_SECTION_TITLE])[tense]

    def test_vorgangspassiv_has_all_six_indicative_tenses(self) -> None:
        result = self.conjugator.conjugate("machen")

        self.assertEqual(
            [title for title, _forms in result.sections[PASSIVE_SECTION_TITLE]],
            [
                "Präsens",
                "Präteritum",
                "Perfekt",
                "Plusquamperfekt",
                "Futur I",
                "Futur II",
            ],
        )
        self.assertEqual(self.passive_card(result, "Präsens")[0], "ich werde gemacht")
        self.assertEqual(self.passive_card(result, "Präteritum")[1], "du wurdest gemacht")
        self.assertEqual(self.passive_card(result, "Perfekt")[2], "er/sie/es ist gemacht worden")
        self.assertEqual(self.passive_card(result, "Plusquamperfekt")[3], "wir waren gemacht worden")
        self.assertEqual(self.passive_card(result, "Futur I")[4], "ihr werdet gemacht werden")
        self.assertEqual(self.passive_card(result, "Futur II")[5], "Sie werden gemacht worden sein")

    def test_passive_uses_the_verbs_real_participle(self) -> None:
        result = self.conjugator.conjugate("schreiben")
        self.assertEqual(self.passive_card(result, "Präsens")[0], "ich werde geschrieben")
        self.assertEqual(self.passive_card(result, "Perfekt")[0], "ich bin geschrieben worden")

    def test_every_passive_tense_contains_six_persons(self) -> None:
        result = self.conjugator.conjugate("öffnen")
        for _title, forms in result.sections[PASSIVE_SECTION_TITLE]:
            self.assertEqual(len(forms), 6)


if __name__ == "__main__":
    unittest.main()
