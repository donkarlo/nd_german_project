from __future__ import annotations

from dataclasses import replace

from conjugation_core import AUX_PRETERITE, AUX_PRESENT, WERDEN_PRESENT, GermanConjugator


WERDEN_PRETERITE = ("wurde", "wurdest", "wurde", "wurden", "wurdet", "wurden")
PASSIVE_SECTION_TITLE = "PASSIV (VORGANGSPASSIV · falls möglich)"


class PassiveGermanConjugator(GermanConjugator):
    """German conjugator with Vorgangspassiv in all six indicative tenses."""

    def conjugate(self, raw_infinitive: str):
        result = super().conjugate(raw_infinitive)

        participle = result.participle
        passive = [
            (
                "Präsens",
                self._compound_lines(WERDEN_PRESENT, participle, False),
            ),
            (
                "Präteritum",
                self._compound_lines(WERDEN_PRETERITE, participle, False),
            ),
            (
                "Perfekt",
                self._compound_lines(
                    AUX_PRESENT["sein"], f"{participle} worden", False
                ),
            ),
            (
                "Plusquamperfekt",
                self._compound_lines(
                    AUX_PRETERITE["sein"], f"{participle} worden", False
                ),
            ),
            (
                "Futur I",
                self._compound_lines(
                    WERDEN_PRESENT, f"{participle} werden", False, future=True
                ),
            ),
            (
                "Futur II",
                self._compound_lines(
                    WERDEN_PRESENT, f"{participle} worden sein", False, future=True
                ),
            ),
        ]

        sections = dict(result.sections)
        sections[PASSIVE_SECTION_TITLE] = passive
        return replace(result, sections=sections)
