import unittest
import verb_rektion_patch as v

class VerbRektionTests(unittest.TestCase):
    def test_no_invented_grammar(self):
        first = "marschieren (intransitiv): march"
        raw = first + "\nBedeutung: zu Fuß gehen."
        patterns = v._patterns_for_entry(raw, first, "marschieren")
        self.assertEqual(patterns, [])
        self.assertEqual(v._canonical_rektion_raw(raw, patterns), raw)

    def test_two_distinct_patterns(self):
        first = "wünschen: wish"
        raw = first + "\nRektion: jemandem [Dat.] + etwas [Akk.]\nRektion 2: sich [Dat.] + etwas [Akk.]"
        patterns = v._patterns_for_entry(raw, first, "wünschen")
        self.assertEqual(len(patterns), 2)
        self.assertEqual(patterns[0].display, "jemandem [Dat.] + etwas [Akk.]")

    def test_sense_label_and_infinitive(self):
        self.assertIsNotNone(v.REKTION_LINE_RE.fullmatch("Rektion [nach]: sich [Akk.] + nach etwas [Dat.]"))
        p = v._parse_pattern_text("Infinitiv ohne zu", first_line="wollen: want", headword="wollen")
        self.assertEqual(p.display, "Infinitiv ohne zu")

if __name__ == "__main__":
    unittest.main()
