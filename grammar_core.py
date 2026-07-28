from __future__ import annotations

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

PERSONS = ("ich", "du", "er", "sie", "es", "wir", "ihr", "sie", "Sie")
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
POSSESSIVE_STEMS = {"ich":"mein", "du":"dein", "er":"sein", "sie":"ihr", "es":"sein", "wir":"unser", "ihr":"euer", "sie (Plural)":"ihr", "Sie":"Ihr"}
POSSESSIVE_ENDINGS = {
    "Nominativ": ("", "e", "", "e"),
    "Akkusativ": ("en", "e", "", "e"),
    "Dativ": ("em", "er", "em", "en"),
    "Genitiv": ("es", "er", "es", "er"),
}

def possessive_form(owner: str, case: str, gender: str) -> str:
    stem = POSSESSIVE_STEMS[owner]
    if stem.lower() == "euer" and POSSESSIVE_ENDINGS[case][GENDERS.index(gender)]:
        stem = "eur" if stem[0].islower() else "Eur"
    return stem + POSSESSIVE_ENDINGS[case][GENDERS.index(gender)]

PRONOUN_DECLENSIONS = {
    "Demonstrativpronomen: der/die/das": ARTICLES["Bestimmter Artikel"],
    "Demonstrativpronomen: dieser": ARTICLES["dieser"],
    "Demonstrativpronomen: jener": ARTICLES["jener"],
    "Relativpronomen": {
        "Nominativ": ("der", "die", "das", "die"), "Akkusativ": ("den", "die", "das", "die"),
        "Dativ": ("dem", "der", "dem", "denen"), "Genitiv": ("dessen", "deren", "dessen", "deren")},
    "Fragepronomen: welcher": ARTICLES["welcher"],
}

ADJECTIVE_ENDINGS = {
    "Stark (ohne Artikel)": {
        "Nominativ": ("er", "e", "es", "e"), "Akkusativ": ("en", "e", "es", "e"),
        "Dativ": ("em", "er", "em", "en"), "Genitiv": ("en", "er", "en", "er")},
    "Schwach (der/die/das …)": {
        "Nominativ": ("e", "e", "e", "en"), "Akkusativ": ("en", "e", "e", "en"),
        "Dativ": ("en", "en", "en", "en"), "Genitiv": ("en", "en", "en", "en")},
    "Gemischt (ein/kein/mein …)": {
        "Nominativ": ("er", "e", "es", "en"), "Akkusativ": ("en", "e", "es", "en"),
        "Dativ": ("en", "en", "en", "en"), "Genitiv": ("en", "en", "en", "en")},
}

def adjective_stem(word: str) -> str:
    w = word.strip()
    low = w.lower()
    if low == "hoch": return w[:-2] + "h"
    if low == "nah": return w
    if low.endswith("el") and len(w) > 3: return w[:-2] + "l"
    if low.endswith("er") and len(w) > 3: return w[:-2] + "r"
    return w

def decline_adjective(word: str, declension: str, case: str, gender: str) -> tuple[str, str]:
    ending = ADJECTIVE_ENDINGS[declension][case][GENDERS.index(gender)]
    if not word.strip(): return "-" + ending, ending
    return adjective_stem(word) + ending, ending
