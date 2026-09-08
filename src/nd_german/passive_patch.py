from __future__ import annotations

try:
    import conjugation_core as _core
except ImportError:  # package execution
    from . import conjugation_core as _core


_WERDEN_PRESENT = ("werde", "wirst", "wird", "werden", "werdet", "werden")
_WERDEN_PRETERITE = ("wurde", "wurdest", "wurde", "wurden", "wurdet", "wurden")
_SEIN_PRESENT = ("bin", "bist", "ist", "sind", "seid", "sind")
_SEIN_PRETERITE = ("war", "warst", "war", "waren", "wart", "waren")

_VON_AGENTS = ("mir", "dir", "ihm/ihr/ihm", "uns", "euch", "Ihnen")

_SECTION_TITLE = "PASSIV (VORGANGSPASSIV · falls möglich)"
_ORIGINAL_CONJUGATE = _core.GermanConjugator.conjugate


def _lines(finite_forms, tail: str) -> list[str]:
    return [
        f"{finite} {tail} von {agent}"
        for finite, agent in zip(finite_forms, _VON_AGENTS)
    ]


def _passive_cards(participle: str) -> list[tuple[str, list[str]]]:
    return [
        ("Präsens", _lines(_WERDEN_PRESENT, participle)),
        ("Präteritum", _lines(_WERDEN_PRETERITE, participle)),
        ("Perfekt", _lines(_SEIN_PRESENT, f"{participle} worden")),
        ("Plusquamperfekt", _lines(_SEIN_PRETERITE, f"{participle} worden")),
        ("Futur I", _lines(_WERDEN_PRESENT, f"{participle} werden")),
        ("Futur II", _lines(_WERDEN_PRESENT, f"{participle} worden sein")),
    ]


def _conjugate_with_passive(self, raw_infinitive: str):
    result = _ORIGINAL_CONJUGATE(self, raw_infinitive)

    if not result.reflexive:
        result.sections[_SECTION_TITLE] = _passive_cards(result.participle)

    return result


def install_passive_conjugation() -> None:
    current = _core.GermanConjugator.conjugate
    if getattr(current, "_nd_passive_patch", False):
        return

    _conjugate_with_passive._nd_passive_patch = True
    _core.GermanConjugator.conjugate = _conjugate_with_passive
