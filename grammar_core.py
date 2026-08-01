from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

import yaml

CASES = ("Nominativ", "Akkusativ", "Dativ", "Genitiv")
GENDERS = ("Maskulin", "Feminin", "Neutrum", "Plural")

ARTICLES = {
    "Bestimmter Artikel": {
        "Nominativ": ("der", "die", "das", "die"),
        "Akkusativ": ("den", "die", "das", "die"),
        "Dativ": ("dem", "der", "dem", "den"),
        "Genitiv": ("des", "der", "des", "der"),
    },
    "Unbestimmter Artikel": {
        "Nominativ": ("ein", "eine", "ein", "—"),
        "Akkusativ": ("einen", "eine", "ein", "—"),
        "Dativ": ("einem", "einer", "einem", "—"),
        "Genitiv": ("eines", "einer", "eines", "—"),
    },
    "Negativartikel (kein)": {
        "Nominativ": ("kein", "keine", "kein", "keine"),
        "Akkusativ": ("keinen", "keine", "kein", "keine"),
        "Dativ": ("keinem", "keiner", "keinem", "keinen"),
        "Genitiv": ("keines", "keiner", "keines", "keiner"),
    },
    "dieser": {
        "Nominativ": ("dieser", "diese", "dieses", "diese"),
        "Akkusativ": ("diesen", "diese", "dieses", "diese"),
        "Dativ": ("diesem", "dieser", "diesem", "diesen"),
        "Genitiv": ("dieses", "dieser", "dieses", "dieser"),
    },
    "jener": {
        "Nominativ": ("jener", "jene", "jenes", "jene"),
        "Akkusativ": ("jenen", "jene", "jenes", "jene"),
        "Dativ": ("jenem", "jener", "jenem", "jenen"),
        "Genitiv": ("jenes", "jener", "jenes", "jener"),
    },
    "jeder": {
        "Nominativ": ("jeder", "jede", "jedes", "—"),
        "Akkusativ": ("jeden", "jede", "jedes", "—"),
        "Dativ": ("jedem", "jeder", "jedem", "—"),
        "Genitiv": ("jedes", "jeder", "jedes", "—"),
    },
    "welcher": {
        "Nominativ": ("welcher", "welche", "welches", "welche"),
        "Akkusativ": ("welchen", "welche", "welches", "welche"),
        "Dativ": ("welchem", "welcher", "welchem", "welchen"),
        "Genitiv": ("welches", "welcher", "welches", "welcher"),
    },
}

# The labels are deliberately unique.  In the old implementation both the
# feminine singular and third-person plural were literally called "sie".
# QComboBox.currentText() therefore always resolved to the first tuple entry.
PERSONS = (
    "ich",
    "du",
    "er",
    "sie (Singular, feminin)",
    "es",
    "wir",
    "ihr",
    "sie (Plural)",
    "Sie (Höflichkeitsform)",
)

PERSONAL = {
    "Nominativ": ("ich", "du", "er", "sie", "es", "wir", "ihr", "sie", "Sie"),
    "Akkusativ": ("mich", "dich", "ihn", "sie", "es", "uns", "euch", "sie", "Sie"),
    "Dativ": ("mir", "dir", "ihm", "ihr", "ihm", "uns", "euch", "ihnen", "Ihnen"),
    "Genitiv": ("meiner", "deiner", "seiner", "ihrer", "seiner", "unser", "euer", "ihrer", "Ihrer"),
}

REFLEXIVE = {
    "Akkusativ": ("mich", "dich", "sich", "sich", "sich", "uns", "euch", "sich", "sich"),
    "Dativ": ("mir", "dir", "sich", "sich", "sich", "uns", "euch", "sich", "sich"),
}

POSSESSIVE_STEMS = {
    "ich": "mein",
    "du": "dein",
    "er": "sein",
    "sie (Singular, feminin)": "ihr",
    "es": "sein",
    "wir": "unser",
    "ihr": "euer",
    "sie (Plural)": "ihr",
    "Sie (Höflichkeitsform)": "Ihr",
}

POSSESSIVE_ARTICLE_ENDINGS = {
    "Nominativ": ("", "e", "", "e"),
    "Akkusativ": ("en", "e", "", "e"),
    "Dativ": ("em", "er", "em", "en"),
    "Genitiv": ("es", "er", "es", "er"),
}

POSSESSIVE_PRONOUN_ENDINGS = {
    "Nominativ": ("er", "e", "es", "e"),
    "Akkusativ": ("en", "e", "es", "e"),
    "Dativ": ("em", "er", "em", "en"),
    "Genitiv": ("es", "er", "es", "er"),
}


def _stem_with_ending(stem: str, ending: str) -> str:
    """Attach an ending and handle the e-loss in forms of *euer*."""
    if stem.lower() == "euer" and ending:
        stem = "eur" if stem[0].islower() else "Eur"
    return stem + ending


def possessive_article_form(owner: str, case: str, gender: str) -> str:
    stem = POSSESSIVE_STEMS[owner]
    ending = POSSESSIVE_ARTICLE_ENDINGS[case][GENDERS.index(gender)]
    return _stem_with_ending(stem, ending)


def possessive_pronoun_form(owner: str, case: str, gender: str) -> str:
    stem = POSSESSIVE_STEMS[owner]
    ending = POSSESSIVE_PRONOUN_ENDINGS[case][GENDERS.index(gender)]

    # In present-day standard German, the short neuter nominative/accusative
    # forms meins, deins and seins are the usual standalone forms.  The longer
    # variants are also shown because they occur, especially in formal usage.
    if case in ("Nominativ", "Akkusativ") and gender == "Neutrum":
        if stem.lower() in {"mein", "dein", "sein"}:
            short = stem + "s"
            long = stem + "es"
            return f"{short} / {long}"

    return _stem_with_ending(stem, ending)


# Backwards-compatible name used by older callers: it means possessive article.
def possessive_form(owner: str, case: str, gender: str) -> str:
    return possessive_article_form(owner, case, gender)


PRONOUN_DECLENSIONS = {
    "Demonstrativpronomen: der/die/das": {
        "Nominativ": ("der", "die", "das", "die"),
        "Akkusativ": ("den", "die", "das", "die"),
        "Dativ": ("dem", "der", "dem", "denen"),
        "Genitiv": ("dessen", "deren", "dessen", "deren"),
    },
    "Demonstrativpronomen: dieser": ARTICLES["dieser"],
    "Demonstrativpronomen: jener": ARTICLES["jener"],
    "Relativpronomen": {
        "Nominativ": ("der", "die", "das", "die"),
        "Akkusativ": ("den", "die", "das", "die"),
        "Dativ": ("dem", "der", "dem", "denen"),
        "Genitiv": ("dessen", "deren", "dessen", "deren"),
    },
    "Fragepronomen: welcher": ARTICLES["welcher"],
}

ADJECTIVE_ENDINGS = {
    "Stark (ohne Artikel)": {
        "Nominativ": ("er", "e", "es", "e"),
        "Akkusativ": ("en", "e", "es", "e"),
        "Dativ": ("em", "er", "em", "en"),
        "Genitiv": ("en", "er", "en", "er"),
    },
    "Schwach (der/die/das …)": {
        "Nominativ": ("e", "e", "e", "en"),
        "Akkusativ": ("en", "e", "e", "en"),
        "Dativ": ("en", "en", "en", "en"),
        "Genitiv": ("en", "en", "en", "en"),
    },
    "Gemischt (ein/kein/mein …)": {
        "Nominativ": ("er", "e", "es", "en"),
        "Akkusativ": ("en", "e", "es", "en"),
        "Dativ": ("en", "en", "en", "en"),
        "Genitiv": ("en", "en", "en", "en"),
    },
}

ADJECTIVE_AUTO = "Automatisch (nach Begleiter)"
STRONG_ADJECTIVE = "Stark (ohne Artikel)"
WEAK_ADJECTIVE = "Schwach (der/die/das …)"
MIXED_ADJECTIVE = "Gemischt (ein/kein/mein …)"


def _forms(stem: str, endings: tuple[str, ...]) -> set[str]:
    return {stem + ending for ending in endings}


_WEAK_DETERMINERS = {
    "der", "die", "das", "den", "dem", "des",
    "alle", "aller", "allen", "allem",
    "beide", "beider", "beiden", "beidem",
    "sämtliche", "sämtlicher", "sämtlichen", "sämtlichem", "sämtliches",
    "derselbe", "dieselbe", "dasselbe", "denselben", "demselben", "derselben", "desselben",
    "derjenige", "diejenige", "dasjenige", "denjenigen", "demjenigen", "derjenigen", "desjenigen",
}
for _stem in ("dies", "jen", "jed", "welch", "solch", "manch", "jeglich"):
    _WEAK_DETERMINERS.update(_forms(_stem, ("er", "e", "es", "en", "em")))

_MIXED_DETERMINERS: set[str] = set()
for _stem in ("ein", "kein", "mein", "dein", "sein", "ihr", "unser", "irgendein"):
    _MIXED_DETERMINERS.update(_forms(_stem, ("", "e", "en", "em", "er", "es")))
# euer loses the first e before most endings: euer, eure, euren, eurem, eurer, eures.
_MIXED_DETERMINERS.update({"euer", "eure", "euren", "eurem", "eurer", "eures"})

_STRONG_DETERMINERS = {
    "viel", "viele", "vieler", "vielen", "vielem", "vieles",
    "wenig", "wenige", "weniger", "wenigen", "wenigem", "weniges",
    "einige", "einiger", "einigen", "einigem", "einiges",
    "mehrere", "mehrerer", "mehreren",
    "etliche", "etlicher", "etlichen", "etlichem", "etliches",
    "zahlreiche", "zahlreicher", "zahlreichen", "zahlreichem", "zahlreiches",
    "etwas", "nichts", "genug",
}


def detect_adjective_declension(determiner_text: str) -> tuple[str | None, str]:
    """Infer adjective declension from the determiner/article.

    An adjective is not inherently strong, weak, or mixed.  The surrounding
    determiner supplies (or fails to supply) case/gender information.  If the
    determiner is unknown, returning ``None`` is safer than guessing.
    """
    raw = determiner_text.strip()
    normalized = raw.casefold().replace("—", "-")
    if not normalized or normalized in {"-", "ohne", "ohne artikel", "kein artikel"}:
        return STRONG_ADJECTIVE, "Kein Begleiter eingegeben: starke Deklination angenommen."

    tokens = re.findall(r"[a-zäöüß]+", normalized)
    for token in tokens:
        if token in _WEAK_DETERMINERS:
            return WEAK_ADJECTIVE, f"„{token}“ trägt eine vollständige Endung; deshalb ist das Adjektiv schwach."
        if token in _MIXED_DETERMINERS:
            return MIXED_ADJECTIVE, f"„{token}“ ist ein ein-Wort; deshalb ist die Deklination gemischt."
        if token in _STRONG_DETERMINERS:
            return STRONG_ADJECTIVE, f"Nach „{token}“ steht das Adjektiv normalerweise stark."

    return None, "Begleiter nicht sicher erkannt; deshalb werden alle drei Deklinationsarten gezeigt."


def load_irregular_adjective_stems(path: Path) -> dict[str, str]:
    """Load adjective base-form -> declined stem mappings from YAML.

    Example: ``hoch: hoh`` produces *hohe*, *hoher*, *hohen*, etc.
    Keys are normalized case-insensitively. Empty or non-string entries are
    rejected so a malformed settings file cannot silently create bad forms.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("The irregular adjective database must be a YAML mapping.")

    stems: dict[str, str] = {}
    for adjective, stem in raw.items():
        if not isinstance(adjective, str) or not adjective.strip():
            raise ValueError("Every irregular adjective key must be a non-empty string.")
        if not isinstance(stem, str) or not stem.strip():
            raise ValueError(
                f"The irregular adjective stem for {adjective!r} must be a non-empty string."
            )
        stems[adjective.strip().casefold()] = stem.strip()
    return stems


def _match_input_capitalization(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def adjective_stem(
    word: str, irregular_stems: Mapping[str, str] | None = None
) -> str:
    w = word.strip()
    low = w.casefold()

    if irregular_stems is not None and low in irregular_stems:
        return _match_input_capitalization(w, irregular_stems[low])

    # Safe built-in fallbacks keep the core useful even without a YAML file.
    if low == "hoch":
        return w[:-2] + "h"
    if low == "nah":
        return w
    if low.endswith("el") and len(w) > 3:
        return w[:-2] + "l"
    if low.endswith("er") and len(w) > 3:
        return w[:-2] + "r"
    return w


def decline_adjective(
    word: str,
    declension: str,
    case: str,
    gender: str,
    irregular_stems: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    ending = ADJECTIVE_ENDINGS[declension][case][GENDERS.index(gender)]
    if not word.strip():
        return "-" + ending, ending
    return adjective_stem(word, irregular_stems) + ending, ending
