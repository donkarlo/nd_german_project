from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from grammar_core import (
    MIXED_ADJECTIVE,
    PERSONAL,
    PERSONS,
    PRONOUN_DECLENSIONS,
    STRONG_ADJECTIVE,
    WEAK_ADJECTIVE,
    decline_adjective,
    detect_adjective_declension,
    load_irregular_adjective_stems,
    possessive_article_form,
    possessive_pronoun_form,
)


class GrammarCoreTests(unittest.TestCase):
    def test_person_labels_are_unique_and_sie_is_disambiguated(self) -> None:
        self.assertEqual(len(PERSONS), len(set(PERSONS)))
        feminine = PERSONS.index("sie (Singular, feminin)")
        plural = PERSONS.index("sie (Plural)")
        polite = PERSONS.index("Sie (Höflichkeitsform)")
        self.assertEqual(PERSONAL["Dativ"][feminine], "ihr")
        self.assertEqual(PERSONAL["Dativ"][plural], "ihnen")
        self.assertEqual(PERSONAL["Dativ"][polite], "Ihnen")

    def test_demonstrative_pronoun_is_not_declined_like_an_article(self) -> None:
        paradigm = PRONOUN_DECLENSIONS["Demonstrativpronomen: der/die/das"]
        self.assertEqual(paradigm["Dativ"][3], "denen")
        self.assertEqual(paradigm["Genitiv"][0], "dessen")
        self.assertEqual(paradigm["Genitiv"][1], "deren")

    def test_possessive_article_and_pronoun_are_separate(self) -> None:
        self.assertEqual(
            possessive_article_form("ich", "Nominativ", "Maskulin"),
            "mein",
        )
        self.assertEqual(
            possessive_pronoun_form("ich", "Nominativ", "Maskulin"),
            "meiner",
        )
        self.assertEqual(
            possessive_pronoun_form("ich", "Nominativ", "Neutrum"),
            "meins / meines",
        )
        self.assertEqual(
            possessive_article_form("ihr", "Dativ", "Plural"),
            "euren",
        )

    def test_adjective_declension_detection(self) -> None:
        self.assertEqual(detect_adjective_declension("der")[0], WEAK_ADJECTIVE)
        self.assertEqual(detect_adjective_declension("mit dem")[0], WEAK_ADJECTIVE)
        self.assertEqual(detect_adjective_declension("ein")[0], MIXED_ADJECTIVE)
        self.assertEqual(detect_adjective_declension("meiner")[0], MIXED_ADJECTIVE)
        self.assertEqual(detect_adjective_declension("")[0], STRONG_ADJECTIVE)
        self.assertEqual(detect_adjective_declension("viele")[0], STRONG_ADJECTIVE)
        self.assertIsNone(detect_adjective_declension("unbekannteswort")[0])

    def test_adjective_forms_after_detection(self) -> None:
        form, _ = decline_adjective("gut", WEAK_ADJECTIVE, "Nominativ", "Maskulin")
        self.assertEqual(form, "gute")
        form, _ = decline_adjective("gut", MIXED_ADJECTIVE, "Nominativ", "Maskulin")
        self.assertEqual(form, "guter")
        form, _ = decline_adjective("hoch", WEAK_ADJECTIVE, "Nominativ", "Neutrum")
        self.assertEqual(form, "hohe")

    def test_irregular_adjective_yaml_is_loaded_and_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "irregular_adjectives.yaml"
            path.write_text("rosa: ros\n", encoding="utf-8")
            stems = load_irregular_adjective_stems(path)

        form, _ = decline_adjective(
            "rosa", WEAK_ADJECTIVE, "Nominativ", "Neutrum", stems
        )
        self.assertEqual(form, "rose")

    def test_irregular_adjective_yaml_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "irregular_adjectives.yaml"
            path.write_text("hoch: hoh\n", encoding="utf-8")
            stems = load_irregular_adjective_stems(path)

        form, _ = decline_adjective(
            "Hoch", WEAK_ADJECTIVE, "Nominativ", "Neutrum", stems
        )
        self.assertEqual(form, "Hohe")

    def test_invalid_irregular_adjective_yaml_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "irregular_adjectives.yaml"
            path.write_text("- hoch\n- dunkel\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_irregular_adjective_stems(path)


if __name__ == "__main__":
    unittest.main()
