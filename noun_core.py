from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

import yaml

CASES = ("Nominativ", "Akkusativ", "Dativ", "Genitiv")
GENDERS = ("Maskulin", "Feminin", "Neutrum")

DEFINITE_ARTICLES = {
    "Maskulin": {
        "Nominativ": "der",
        "Akkusativ": "den",
        "Dativ": "dem",
        "Genitiv": "des",
    },
    "Feminin": {
        "Nominativ": "die",
        "Akkusativ": "die",
        "Dativ": "der",
        "Genitiv": "der",
    },
    "Neutrum": {
        "Nominativ": "das",
        "Akkusativ": "das",
        "Dativ": "dem",
        "Genitiv": "des",
    },
}

PLURAL_ARTICLES = {
    "Nominativ": "die",
    "Akkusativ": "die",
    "Dativ": "den",
    "Genitiv": "der",
}

ARTICLE_GENDER = {
    "der": "Maskulin",
    "ein": "Maskulin",
    "die": "Feminin",
    "eine": "Feminin",
    "das": "Neutrum",
}

FIELD_RE = re.compile(r"^\s*([^:]{1,32})\s*:\s*(.*?)\s*$", re.I)


def load_irregular_nouns(path: Path) -> dict[str, dict[str, str]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("The irregular noun database must be a YAML mapping.")

    result: dict[str, dict[str, str]] = {}
    for noun, spec in raw.items():
        if not isinstance(noun, str) or not noun.strip():
            raise ValueError("Every irregular noun key must be a non-empty string.")
        if not isinstance(spec, dict):
            raise ValueError(f"Irregular noun {noun!r} must map to a dictionary.")
        cleaned: dict[str, str] = {}
        for key, value in spec.items():
            if value is None:
                continue
            if not isinstance(value, str):
                raise ValueError(f"Irregular noun {noun!r}: {key!r} must be text.")
            cleaned[str(key)] = value.strip()
        result[noun.casefold().strip()] = cleaned
    return result


def _first_line_left(text: str) -> str:
    first_line = text.splitlines()[0].strip() if text else ""
    left = first_line.split(":", 1)[0].strip()
    left = re.sub(r"\s*\[[^\]]*\].*$", "", left).strip()
    left = re.sub(r"\s*\([^)]*\).*$", "", left).strip()
    return re.sub(r"\s+", " ", left).strip()


def noun_and_gender(text: str) -> tuple[str, str | None]:
    left = _first_line_left(text)
    match = re.match(r"^(der|die|das|ein|eine)\s+(.+)$", left, re.I)
    if not match:
        return left.strip(), None
    article = match.group(1).casefold()
    return match.group(2).strip(), ARTICLE_GENDER.get(article)


def _field(raw: str, label: str) -> str:
    wanted = label.casefold()
    for line in raw.splitlines()[1:]:
        match = FIELD_RE.match(line)
        if match and match.group(1).strip().casefold() == wanted:
            return match.group(2).strip()
    return ""


def _strip_article(value: str) -> str:
    text = re.sub(r"\s+", " ", value.strip())
    text = re.sub(
        r"^(?:des|der|dem|den|die|das|ein(?:es|em|en|er|e)?|kein(?:es|em|en|er|e)?)\s+",
        "",
        text,
        flags=re.I,
    )
    return text.strip()


def _is_no_plural(value: str) -> bool:
    normalized = value.casefold().replace("—", "-")
    return normalized in {
        "kein plural",
        "keine pluralform",
        "kein pl.",
        "singular",
        "nur singular",
        "-",
    }


def _regular_genitive(base: str, gender: str | None) -> str:
    if not base:
        return ""
    if gender == "Feminin":
        return base
    lower = base.casefold()
    if lower.endswith(("s", "ß", "x", "z", "tz", "tsch")):
        return base + "es"
    syllable_hint = len(re.findall(r"[aeiouyäöü]+", lower))
    if syllable_hint <= 1:
        return base + "es"
    return base + "s"


def _dative_plural(plural: str) -> str:
    if not plural:
        return ""
    lower = plural.casefold()
    if lower.endswith(("n", "s")):
        return plural
    return plural + "n"


def _weak_oblique(base: str) -> str:
    lower = base.casefold()
    if lower.endswith("e"):
        return base + "n"
    return base + "en"


def _looks_weak_masculine(base: str, gender: str | None) -> bool:
    if gender != "Maskulin":
        return False
    lower = base.casefold()
    return lower.endswith(
        (
            "ant",
            "ent",
            "ist",
            "oge",
            "at",
            "nom",
            "graf",
            "graph",
            "arch",
            "soph",
            "ot",
        )
    )


def _ending(base: str, form: str) -> str:
    if not base or not form or form == "—":
        return "—"
    if form == base:
        return "—"
    if form.casefold().startswith(base.casefold()):
        suffix = form[len(base):]
        return f"-{suffix}" if suffix else "—"
    return f"→ {form}"


def decline_noun(
    word: str,
    *,
    raw: str = "",
    irregular_nouns: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, object]:
    query_base, query_gender = noun_and_gender(word)
    raw_base, raw_gender = noun_and_gender(raw) if raw else ("", None)
    base = raw_base or query_base
    gender = raw_gender or query_gender

    genitive_field = _field(raw, "Genitiv") if raw else ""
    plural_field = _field(raw, "Plural") if raw else ""
    genitive = _strip_article(genitive_field) if genitive_field else ""
    plural = "" if _is_no_plural(plural_field) else _strip_article(plural_field)
    no_plural = bool(plural_field and _is_no_plural(plural_field))

    singular = {
        "Nominativ": base,
        "Akkusativ": base,
        "Dativ": base,
        "Genitiv": genitive or _regular_genitive(base, gender),
    }
    source_bits: list[str] = []
    if genitive_field:
        source_bits.append("Genitiv aus Dictionary")
    if plural_field:
        source_bits.append("Plural aus Dictionary")

    if _looks_weak_masculine(base, gender):
        oblique = _weak_oblique(base)
        singular["Akkusativ"] = oblique
        singular["Dativ"] = oblique
        if not genitive_field:
            singular["Genitiv"] = oblique
        source_bits.append("n-Deklination per Regel")

    plural_forms = {
        "Nominativ": plural,
        "Akkusativ": plural,
        "Dativ": _dative_plural(plural),
        "Genitiv": plural,
    }

    irregular = None
    if irregular_nouns and base:
        irregular = irregular_nouns.get(base.casefold())
    if irregular:
        gender = irregular.get("gender", gender) or gender
        singular["Nominativ"] = irregular.get("nominative_singular", singular["Nominativ"])
        singular["Akkusativ"] = irregular.get("accusative_singular", singular["Akkusativ"])
        singular["Dativ"] = irregular.get("dative_singular", singular["Dativ"])
        singular["Genitiv"] = irregular.get("genitive_singular", singular["Genitiv"])
        irregular_plural = irregular.get("plural", "")
        if irregular_plural:
            no_plural = _is_no_plural(irregular_plural)
            plural = "" if no_plural else irregular_plural
            plural_forms = {
                "Nominativ": plural,
                "Akkusativ": plural,
                "Dativ": irregular.get("dative_plural", _dative_plural(plural)),
                "Genitiv": plural,
            }
        source_bits.append("irregular_nouns.yaml")

    if not plural and not no_plural:
        plural_forms = {case: "" for case in CASES}

    rows: list[dict[str, str]] = []
    for case in CASES:
        singular_form = singular.get(case, "") or "—"
        plural_form = plural_forms.get(case, "") or ("kein Plural" if no_plural else "—")
        singular_article = DEFINITE_ARTICLES.get(gender or "", {}).get(case, "")
        plural_article = PLURAL_ARTICLES[case] if plural_form not in {"—", "kein Plural"} else ""
        rows.append(
            {
                "case": case,
                "singular": f"{singular_article} {singular_form}".strip(),
                "singular_ending": _ending(base, singular_form),
                "plural": f"{plural_article} {plural_form}".strip(),
                "plural_ending": _ending(base, plural_form) if plural_form not in {"—", "kein Plural"} else "—",
            }
        )

    note = irregular.get("note", "") if irregular else ""
    return {
        "base": base,
        "gender": gender or "Unbekannt",
        "rows": rows,
        "note": note,
        "source": "; ".join(dict.fromkeys(source_bits)) or "Regelbasierte Form",
        "has_dictionary_entry": bool(raw),
    }
