from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import yaml


PRONOUNS = ("ich", "du", "er/sie/es", "wir", "ihr", "Sie")
REFLEXIVE_PRONOUNS = ("mich", "dich", "sich", "uns", "euch", "sich")

PRESENT_ENDINGS = ("e", "st", "t", "en", "t", "en")
K1_ENDINGS = ("e", "est", "e", "en", "et", "en")

SEPARABLE_PREFIXES = tuple(
    sorted(
        {
            "auseinander", "durcheinander", "gegenüber", "hinterher", "nebeneinander",
            "vorwärts", "zusammen", "zurecht", "zurück", "dazwischen", "entgegen",
            "entlang", "herunter", "hinunter", "voraus", "vorbei", "weiter", "wieder",
            "heraus", "herein", "hinaus", "hinein", "herauf", "hinauf", "herab",
            "hinab", "heran", "voran", "empor", "fort", "frei", "heim", "nieder",
            "preis", "statt", "teil", "umher", "durch", "unter", "über", "um",
            "ab", "an", "auf", "aus", "bei",
            "ein", "fest", "her", "hin", "los", "mit", "nach", "vor", "weg", "zu",
        },
        key=len,
        reverse=True,
    )
)
INSEPARABLE_PREFIXES = (
    "hinter", "wider", "miss", "emp", "ent", "ver", "zer", "be", "er", "ge"
)

# These common verbs contain a prefix-looking string but are normally not separated.
NONSEPARABLE_EXCEPTIONS = {
    "antworten", "arbeiten", "beobachten", "beurteilen", "hinterfragen",
    "durchdringen", "durchqueren", "durchschauen", "durchsuchen",
    "überarbeiten", "überblicken", "überfordern", "überleben", "überlegen",
    "übergeben", "übermitteln", "übernachten", "übernehmen", "überprüfen",
    "überqueren", "überraschen", "übersehen", "übersetzen", "übertragen",
    "übertreffen", "überwachen", "überweisen", "überzeugen",
    "umarmen", "umgeben",
    "unterbrechen", "unterdrücken", "unterhalten", "unterrichten", "unterstützen",
    "unterlassen", "unternehmen", "unterscheiden", "unterstehen", "untersuchen",
    "unterzeichnen", "unterziehen",
    "wiederholen", "widerlegen", "widerrufen", "widersprechen", "widerstehen",
}

# ``antworten`` and ``arbeiten`` are in the set above only to prevent a false
# prefix split; unlike the other entries, their participles do take ge-.
NO_GE_EXCEPTIONS = NONSEPARABLE_EXCEPTIONS - {"antworten", "arbeiten"}


def _spelling_aliases(text: str) -> set[str]:
    """Return common keyboard spellings for a German word.

    Both the standard digraph spelling (``ue``) and the frequently typed
    umlaut-less spelling (``u``) are accepted.  Ambiguous aliases are removed
    when the database is built.
    """

    value = unicodedata.normalize("NFC", text).lower()
    return {
        value,
        value.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})),
        value.translate(str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss"})),
    }

VALID_INFINITIVE_RE = re.compile(r"^[a-zäöüß]+(?:eln|ern|en|n)$", re.IGNORECASE)


def normalize_verb(text: str) -> tuple[str, bool]:
    value = unicodedata.normalize("NFC", text).strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = value.rstrip(".!?,;:")
    reflexive = False
    if value.startswith("sich "):
        reflexive = True
        value = value[5:].strip()
    if value.startswith("zu "):
        value = value[3:].strip()
    return value, reflexive


def is_plausible_infinitive(text: str) -> bool:
    infinitive, _ = normalize_verb(text)
    return bool(VALID_INFINITIVE_RE.fullmatch(infinitive)) and len(infinitive) >= 3


def infinitive_stem(infinitive: str) -> str:
    if infinitive.endswith("en"):
        return infinitive[:-2]
    if infinitive.endswith("n"):
        return infinitive[:-1]
    raise ValueError(f'“{infinitive}” does not look like a German infinitive.')


def _needs_e_insertion(stem: str) -> bool:
    if stem.endswith(("d", "t")):
        return True
    # Atmen/öffnen-type clusters generally insert e; liquid/nasal combinations do not.
    return bool(re.search(r"[^aeiouäöüyrlmn][mn]$", stem))


def regular_present(infinitive: str) -> list[str]:
    stem = infinitive_stem(infinitive)
    ich_stem = stem
    if infinitive.endswith("eln") and stem.endswith("el"):
        ich_form = stem[:-2] + "le"
    else:
        ich_form = ich_stem + "e"

    insert_e = _needs_e_insertion(stem)
    if insert_e:
        du = stem + "est"
        er = stem + "et"
        ihr = stem + "et"
    elif stem.endswith(("s", "ß", "x", "z", "tz")):
        du = stem + "t"
        er = stem + "t"
        ihr = stem + "t"
    else:
        du = stem + "st"
        er = stem + "t"
        ihr = stem + "t"
    return [ich_form, du, er, infinitive, ihr, infinitive]


def regular_preterite(infinitive: str) -> list[str]:
    stem = infinitive_stem(infinitive)
    marker = "ete" if _needs_e_insertion(stem) else "te"
    first = stem + marker
    return [first, first + "st", first, first + "n", first + "t", first + "n"]


def regular_konjunktiv_i(infinitive: str) -> list[str]:
    stem = infinitive_stem(infinitive)
    return [stem + ending for ending in K1_ENDINGS]


def strong_preterite(first_person: str) -> list[str]:
    if first_person.endswith("e"):
        base = first_person[:-1]
        return [first_person, first_person + "st", first_person, base + "en", base + "et", base + "en"]
    if first_person.endswith(("d", "t")):
        second = first_person + "est"
        plural_ihr = first_person + "et"
    elif first_person.endswith(("s", "ß", "z", "x")):
        second = first_person + "est"
        plural_ihr = first_person + "t"
    else:
        second = first_person + "st"
        plural_ihr = first_person + "t"
    return [first_person, second, first_person, first_person + "en", plural_ihr, first_person + "en"]


def konjunktiv_ii_from_first(first_person: str) -> list[str]:
    if not first_person.endswith("e"):
        first_person += "e"
    base = first_person[:-1]
    return [first_person, base + "est", first_person, base + "en", base + "et", base + "en"]


def remove_initial_ge(participle: str) -> str:
    return participle[2:] if participle.startswith("ge") else participle


@dataclass(frozen=True, slots=True)
class VerbRecord:
    infinitive: str
    participle: str
    auxiliary: str = "haben"
    present: tuple[str, ...] | None = None
    present_du: str | None = None
    present_er: str | None = None
    preterite: tuple[str, ...] | None = None
    preterite_ich: str | None = None
    konjunktiv_i: tuple[str, ...] | None = None
    konjunktiv_ii: tuple[str, ...] | None = None
    konjunktiv_ii_ich: str | None = None
    imperative_du: str | None = None
    imperative_ihr: str | None = None
    note: str = ""

    @classmethod
    def from_mapping(cls, infinitive: str, data: dict[str, Any]) -> "VerbRecord":
        def tup(name: str) -> tuple[str, ...] | None:
            value = data.get(name)
            if value is None:
                return None
            if not isinstance(value, list) or len(value) != 6:
                raise ValueError(f"{infinitive}.{name} must contain exactly six forms")
            return tuple(str(item) for item in value)

        return cls(
            infinitive=infinitive,
            participle=str(data["participle"]),
            auxiliary=str(data.get("auxiliary", "haben")),
            present=tup("present"),
            present_du=data.get("present_du"),
            present_er=data.get("present_er"),
            preterite=tup("preterite"),
            preterite_ich=data.get("preterite_ich"),
            konjunktiv_i=tup("konjunktiv_i"),
            konjunktiv_ii=tup("konjunktiv_ii"),
            konjunktiv_ii_ich=data.get("konjunktiv_ii_ich"),
            imperative_du=data.get("imperative_du"),
            imperative_ihr=data.get("imperative_ihr"),
            note=str(data.get("note", "")),
        )


@dataclass(frozen=True, slots=True)
class PrefixAnalysis:
    prefix: str = ""
    base: str = ""
    separable: bool = False
    inherited: bool = False


@dataclass(frozen=True, slots=True)
class ConjugationResult:
    infinitive: str
    reflexive: bool
    source: str
    auxiliary: str
    participle: str
    note: str
    sections: dict[str, list[tuple[str, list[str]]]]
    imperatives: list[str]
    participles: list[tuple[str, str]]
    infinitives: list[tuple[str, str]]


class IrregularVerbDatabase:
    def __init__(
        self, records: Iterable[VerbRecord], auxiliary_overrides: dict[str, str] | None = None
    ) -> None:
        self.records = {record.infinitive: record for record in records}
        self.auxiliary_overrides = {
            str(key).lower(): str(value) for key, value in (auxiliary_overrides or {}).items()
        }
        if len(self.records) > 2000:
            raise ValueError("The irregular-verb database may not contain more than 2000 verbs.")

        alias_candidates: dict[str, set[str]] = {}
        alias_lexemes = set(self.records) | NONSEPARABLE_EXCEPTIONS
        for infinitive in alias_lexemes:
            for alias in _spelling_aliases(infinitive):
                alias_candidates.setdefault(alias, set()).add(infinitive)
        self._aliases = {
            alias: next(iter(matches))
            for alias, matches in alias_candidates.items()
            if len(matches) == 1
        }

        prefix_alias_candidates: dict[str, set[str]] = {}
        for prefix in set(SEPARABLE_PREFIXES) | set(INSEPARABLE_PREFIXES):
            for alias in _spelling_aliases(prefix):
                prefix_alias_candidates.setdefault(alias, set()).add(prefix)
        self._prefix_aliases = {
            alias: next(iter(matches))
            for alias, matches in prefix_alias_candidates.items()
            if len(matches) == 1
        }

        self._search_forms: dict[str, str] = {}
        for infinitive, record in self.records.items():
            self._search_forms[infinitive] = infinitive
            for alias in _spelling_aliases(infinitive):
                self._search_forms.setdefault(alias, infinitive)
            self._search_forms[record.participle] = infinitive
            if record.preterite_ich:
                self._search_forms[record.preterite_ich] = infinitive
        for infinitive in self.auxiliary_overrides:
            self._search_forms.setdefault(infinitive, infinitive)
        for infinitive in NONSEPARABLE_EXCEPTIONS:
            self._search_forms.setdefault(infinitive, infinitive)
            for alias in _spelling_aliases(infinitive):
                self._search_forms.setdefault(alias, infinitive)

    @classmethod
    def from_file(cls, path: str | Path) -> "IrregularVerbDatabase":
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        verb_data = data.get("verbs", data)
        auxiliary_overrides = data.get("auxiliary_overrides", {}) if isinstance(data, dict) else {}
        if not isinstance(verb_data, dict):
            raise ValueError("Irregular verb YAML must contain a 'verbs' mapping.")
        records = []
        for infinitive, mapping in verb_data.items():
            if not isinstance(mapping, dict):
                raise ValueError(f"Entry for {infinitive} must be a mapping.")
            records.append(VerbRecord.from_mapping(str(infinitive).lower(), mapping))
        if not isinstance(auxiliary_overrides, dict):
            raise ValueError("auxiliary_overrides must be a mapping.")
        return cls(records, auxiliary_overrides)

    def auxiliary_for(self, infinitive: str, default: str) -> str:
        return self.auxiliary_overrides.get(infinitive, default)

    def canonicalize(self, infinitive: str) -> str:
        """Map safe keyboard variants such as ``mussen`` to ``müssen``.

        Only aliases that point to exactly one database verb are accepted, so
        an ambiguous spelling is never silently changed.  The same logic also
        supports prefixed compounds, for example ``zuruckkommen``.
        """

        if infinitive in self.records:
            return infinitive
        direct = self._aliases.get(infinitive)
        if direct:
            return direct

        candidates: list[tuple[int, str]] = []
        for alias, canonical_base in self._aliases.items():
            if infinitive == alias or not infinitive.endswith(alias):
                continue
            raw_prefix = infinitive[: -len(alias)]
            canonical_prefix = self._prefix_aliases.get(raw_prefix, raw_prefix)
            if canonical_prefix in SEPARABLE_PREFIXES or canonical_prefix in INSEPARABLE_PREFIXES:
                candidates.append(
                    (len(alias), canonical_prefix + canonical_base)
                )
        if candidates:
            return max(candidates, key=lambda item: item[0])[1]

        # Also normalize a keyboard spelling of a prefix when the base verb is
        # regular and therefore absent from the irregular database.
        for alias in sorted(self._prefix_aliases, key=len, reverse=True):
            if not infinitive.startswith(alias):
                continue
            base = infinitive[len(alias):]
            if len(base) >= 3 and VALID_INFINITIVE_RE.fullmatch(base):
                return self._prefix_aliases[alias] + base
        return infinitive

    def suggestions(self, query: str, limit: int = 14) -> list[str]:
        normalized, _ = normalize_verb(query)
        if not normalized:
            return sorted(self.records)[:limit]
        scored: dict[str, float] = {}
        for form, infinitive in self._search_forms.items():
            if form == normalized:
                score = 1000
            elif form.startswith(normalized):
                score = 900 - (len(form) - len(normalized))
            elif normalized in form:
                score = 800 - form.index(normalized)
            else:
                ratio = SequenceMatcher(None, normalized, form).ratio() * 100
                if ratio < 45:
                    continue
                score = 500 + ratio
            scored[infinitive] = max(scored.get(infinitive, 0), score)
        return [key for key, _ in sorted(scored.items(), key=lambda item: (-item[1], item[0]))[:limit]]

    def resolve(self, infinitive: str) -> tuple[VerbRecord | None, PrefixAnalysis]:
        if infinitive in self.records:
            return self.records[infinitive], PrefixAnalysis(base=infinitive)

        # Prefer a known irregular base. Long prefixes win over short prefixes.
        candidates: list[tuple[int, VerbRecord, PrefixAnalysis]] = []
        for base, record in self.records.items():
            if infinitive == base or not infinitive.endswith(base):
                continue
            prefix = infinitive[: -len(base)]
            if not prefix:
                continue
            if infinitive in NONSEPARABLE_EXCEPTIONS:
                candidates.append((len(prefix), record, PrefixAnalysis(prefix, base, False, True)))
            elif prefix in INSEPARABLE_PREFIXES:
                candidates.append((len(prefix), record, PrefixAnalysis(prefix, base, False, True)))
            elif prefix in SEPARABLE_PREFIXES and infinitive not in NONSEPARABLE_EXCEPTIONS:
                candidates.append((len(prefix), record, PrefixAnalysis(prefix, base, True, True)))
        if candidates:
            _, record, analysis = max(candidates, key=lambda item: item[0])
            return record, analysis
        return None, self.analyse_regular_prefix(infinitive)

    @staticmethod
    def analyse_regular_prefix(infinitive: str) -> PrefixAnalysis:
        if infinitive in NONSEPARABLE_EXCEPTIONS:
            return PrefixAnalysis(base=infinitive)
        for prefix in SEPARABLE_PREFIXES:
            if infinitive.startswith(prefix):
                base = infinitive[len(prefix):]
                if len(base) >= 4 and VALID_INFINITIVE_RE.fullmatch(base):
                    return PrefixAnalysis(prefix, base, True, False)
        for prefix in INSEPARABLE_PREFIXES:
            if infinitive.startswith(prefix) and len(infinitive) - len(prefix) >= 3:
                return PrefixAnalysis(prefix, infinitive[len(prefix):], False, False)
        return PrefixAnalysis(base=infinitive)


AUX_PRESENT = {
    "haben": ("habe", "hast", "hat", "haben", "habt", "haben"),
    "sein": ("bin", "bist", "ist", "sind", "seid", "sind"),
}
AUX_PRETERITE = {
    "haben": ("hatte", "hattest", "hatte", "hatten", "hattet", "hatten"),
    "sein": ("war", "warst", "war", "waren", "wart", "waren"),
}
AUX_K1 = {
    "haben": ("habe", "habest", "habe", "haben", "habet", "haben"),
    "sein": ("sei", "seiest", "sei", "seien", "seiet", "seien"),
}
AUX_K2 = {
    "haben": ("hätte", "hättest", "hätte", "hätten", "hättet", "hätten"),
    "sein": ("wäre", "wärest", "wäre", "wären", "wäret", "wären"),
}
WERDEN_PRESENT = ("werde", "wirst", "wird", "werden", "werdet", "werden")
WERDEN_K1 = ("werde", "werdest", "werde", "werden", "werdet", "werden")
WERDEN_K2 = ("würde", "würdest", "würde", "würden", "würdet", "würden")


class GermanConjugator:
    def __init__(self, database: IrregularVerbDatabase) -> None:
        self.database = database

    @staticmethod
    def _apply_prefix(forms: Iterable[str], analysis: PrefixAnalysis) -> list[str]:
        if not analysis.prefix:
            return list(forms)
        if analysis.separable:
            return [f"{form} {analysis.prefix}" for form in forms]
        return [analysis.prefix + form for form in forms]

    @staticmethod
    def _apply_prefix_one(form: str, analysis: PrefixAnalysis) -> str:
        if not analysis.prefix:
            return form
        return f"{form} {analysis.prefix}" if analysis.separable else analysis.prefix + form

    @staticmethod
    def _regular_participle(infinitive: str, analysis: PrefixAnalysis) -> str:
        target = analysis.base if analysis.separable else infinitive
        stem = infinitive_stem(target)
        ending = "et" if _needs_e_insertion(stem) else "t"
        if analysis.separable:
            return analysis.prefix + "ge" + stem + ending
        if (
            infinitive.endswith("ieren")
            or infinitive.startswith(INSEPARABLE_PREFIXES)
            or infinitive in NO_GE_EXCEPTIONS
        ):
            return stem + ending
        return "ge" + stem + ending

    @staticmethod
    def _derived_participle(record: VerbRecord, analysis: PrefixAnalysis) -> str:
        if not analysis.prefix:
            return record.participle
        if analysis.separable:
            return analysis.prefix + record.participle
        return analysis.prefix + remove_initial_ge(record.participle)

    @staticmethod
    def _record_present(record: VerbRecord) -> list[str]:
        if record.present:
            return list(record.present)
        forms = regular_present(record.infinitive)
        if record.present_du:
            forms[1] = record.present_du
        if record.present_er:
            forms[2] = record.present_er
        return forms

    @staticmethod
    def _record_preterite(record: VerbRecord) -> list[str]:
        if record.preterite:
            return list(record.preterite)
        if record.preterite_ich:
            return strong_preterite(record.preterite_ich)
        return regular_preterite(record.infinitive)

    @staticmethod
    def _record_k1(record: VerbRecord) -> list[str]:
        if record.konjunktiv_i:
            return list(record.konjunktiv_i)
        return regular_konjunktiv_i(record.infinitive)

    @staticmethod
    def _record_k2(record: VerbRecord) -> list[str]:
        if record.konjunktiv_ii:
            return list(record.konjunktiv_ii)
        if record.konjunktiv_ii_ich:
            return konjunktiv_ii_from_first(record.konjunktiv_ii_ich)
        # For weak verbs, Konjunktiv II is identical to Präteritum.
        return GermanConjugator._record_preterite(record)

    @staticmethod
    def _regular_imperative_du(infinitive: str) -> str:
        stem = infinitive_stem(infinitive)
        if infinitive.endswith("eln") and stem.endswith("el"):
            return stem[:-2] + "le"
        if _needs_e_insertion(stem):
            return stem + "e"
        return stem

    @staticmethod
    def _insert_reflexive(finite: str, reflexive: str) -> str:
        first, sep, rest = finite.partition(" ")
        return f"{first} {reflexive}{sep}{rest}" if sep else f"{first} {reflexive}"

    @staticmethod
    def _simple_lines(forms: Iterable[str], reflexive: bool) -> list[str]:
        result = []
        for index, (pronoun, form) in enumerate(zip(PRONOUNS, forms)):
            if reflexive:
                form = GermanConjugator._insert_reflexive(form, REFLEXIVE_PRONOUNS[index])
            result.append(f"{pronoun} {form}")
        return result

    @staticmethod
    def _compound_lines(
        finite_aux: Iterable[str], tail: str, reflexive: bool, *, future: bool = False
    ) -> list[str]:
        result = []
        for index, (pronoun, finite) in enumerate(zip(PRONOUNS, finite_aux)):
            middle = f" {REFLEXIVE_PRONOUNS[index]}" if reflexive else ""
            result.append(f"{pronoun} {finite}{middle} {tail}")
        return result

    @staticmethod
    def _imperative_line(form: str, person: str, reflexive: str | None = None) -> str:
        first, sep, rest = form.partition(" ")
        if person == "du":
            pieces = [first]
            if reflexive:
                pieces.append(reflexive)
            if sep:
                pieces.append(rest)
            return " ".join(pieces) + " (du)"
        if person == "ihr":
            pieces = [first]
            if reflexive:
                pieces.append(reflexive)
            if sep:
                pieces.append(rest)
            return " ".join(pieces) + " (ihr)"
        pieces = [first, "Sie"]
        if reflexive:
            pieces.append(reflexive)
        if sep:
            pieces.append(rest)
        return " ".join(pieces)

    @staticmethod
    def _zu_infinitive(infinitive: str, analysis: PrefixAnalysis) -> str:
        if analysis.prefix and analysis.separable:
            return analysis.prefix + "zu" + analysis.base
        return "zu " + infinitive

    @staticmethod
    def _participle_i(infinitive: str) -> str:
        # The normal rule is infinitive + d.  sein and tun (including prefixed
        # compounds) insert an e: seiend, tuend, antuend, vertuend.
        if infinitive.endswith("sein"):
            return infinitive[:-4] + "seiend"
        if infinitive.endswith("tun"):
            return infinitive[:-3] + "tuend"
        return infinitive + "d"

    def conjugate(self, raw_infinitive: str) -> ConjugationResult:
        entered_infinitive, reflexive = normalize_verb(raw_infinitive)
        if not is_plausible_infinitive(entered_infinitive):
            raise ValueError("Enter a German infinitive ending in -en or -n, for example: haben, gehen, arbeiten.")

        infinitive = self.database.canonicalize(entered_infinitive)

        record, analysis = self.database.resolve(infinitive)
        if record:
            present = self._apply_prefix(self._record_present(record), analysis)
            preterite = self._apply_prefix(self._record_preterite(record), analysis)
            k1 = self._apply_prefix(self._record_k1(record), analysis)
            k2 = self._apply_prefix(self._record_k2(record), analysis)
            participle = self._derived_participle(record, analysis)
            auxiliary = self.database.auxiliary_for(infinitive, record.auxiliary)
            base_present = self._record_present(record)
            imperative_du = record.imperative_du or self._regular_imperative_du(record.infinitive)
            imperative_ihr = record.imperative_ihr or base_present[4]
            imperative_du = self._apply_prefix_one(imperative_du, analysis)
            imperative_ihr = self._apply_prefix_one(imperative_ihr, analysis)
            source = "irregular database"
            if analysis.inherited:
                source += f" · inherited from {record.infinitive}"
            note = record.note
        else:
            base = analysis.base if analysis.separable else infinitive
            form_analysis = analysis if analysis.separable else PrefixAnalysis(base=infinitive)
            base_present = regular_present(base)
            base_preterite = regular_preterite(base)
            base_k1 = regular_konjunktiv_i(base)
            present = self._apply_prefix(base_present, form_analysis)
            preterite = self._apply_prefix(base_preterite, form_analysis)
            k1 = self._apply_prefix(base_k1, form_analysis)
            k2 = list(preterite)
            participle = self._regular_participle(infinitive, analysis)
            auxiliary = self.database.auxiliary_for(infinitive, "haben")
            imperative_du = self._regular_imperative_du(base)
            imperative_ihr = base_present[4]
            imperative_du = self._apply_prefix_one(imperative_du, form_analysis)
            imperative_ihr = self._apply_prefix_one(imperative_ihr, form_analysis)
            source = "regular rule"
            note = "Regular verbs use haben by default. Add an override to irregular_verbs.yaml if this verb uses sein or has a special form."

        if infinitive != entered_infinitive:
            correction = f'Input “{entered_infinitive}” was interpreted as “{infinitive}”.'
            note = f"{correction} {note}".strip()

        if auxiliary not in AUX_PRESENT:
            raise ValueError(f"Unsupported auxiliary for {infinitive}: {auxiliary}")

        infinitive_phrase = infinitive
        perfect_tail = f"{participle} {auxiliary}"
        future_tail = infinitive_phrase
        future_ii_tail = f"{participle} {auxiliary}"

        indicative = [
            ("Präsens", self._simple_lines(present, reflexive)),
            ("Präteritum", self._simple_lines(preterite, reflexive)),
            ("Futur I", self._compound_lines(WERDEN_PRESENT, future_tail, reflexive, future=True)),
            ("Perfekt", self._compound_lines(AUX_PRESENT[auxiliary], participle, reflexive)),
            ("Plusquamperfekt", self._compound_lines(AUX_PRETERITE[auxiliary], participle, reflexive)),
            ("Futur II", self._compound_lines(WERDEN_PRESENT, future_ii_tail, reflexive, future=True)),
        ]
        konjunktiv_i = [
            ("Präsens", self._simple_lines(k1, reflexive)),
            ("Futur I", self._compound_lines(WERDEN_K1, future_tail, reflexive, future=True)),
            ("Perfekt", self._compound_lines(AUX_K1[auxiliary], participle, reflexive)),
        ]
        konjunktiv_ii = [
            ("Präteritum", self._simple_lines(k2, reflexive)),
            ("Futur I", self._compound_lines(WERDEN_K2, future_tail, reflexive, future=True)),
            ("Plusquamperfekt", self._compound_lines(AUX_K2[auxiliary], participle, reflexive)),
            ("Futur II", self._compound_lines(WERDEN_K2, future_ii_tail, reflexive, future=True)),
        ]

        reflexive_du = "dich" if reflexive else None
        reflexive_ihr = "euch" if reflexive else None
        reflexive_sie = "sich" if reflexive else None
        if infinitive == "sein":
            imperative_sie = "seien"
        elif analysis.separable:
            imperative_sie = present[5]
        else:
            imperative_sie = infinitive
        imperatives = [
            self._imperative_line(imperative_du, "du", reflexive_du),
            self._imperative_line(imperative_ihr, "ihr", reflexive_ihr),
            self._imperative_line(imperative_sie, "Sie", reflexive_sie),
        ]

        participle_i = self._participle_i(infinitive)
        if reflexive:
            participle_i = "sich " + participle_i
            participle_ii = "sich " + participle
        else:
            participle_ii = participle

        zu_inf = self._zu_infinitive(infinitive, analysis)
        if reflexive:
            plain_inf = "sich " + infinitive
            perfect_inf = f"sich {participle} {auxiliary}"
            zu_inf = "sich " + zu_inf
            perfect_zu = f"sich {participle} zu {auxiliary}"
        else:
            plain_inf = infinitive
            perfect_inf = perfect_tail
            perfect_zu = f"{participle} zu {auxiliary}"

        return ConjugationResult(
            infinitive=("sich " if reflexive else "") + infinitive,
            reflexive=reflexive,
            source=source,
            auxiliary=auxiliary,
            participle=participle,
            note=note,
            sections={
                "INDIKATIV": indicative,
                "KONJUNKTIV I": konjunktiv_i,
                "KONJUNKTIV II": konjunktiv_ii,
            },
            imperatives=imperatives,
            participles=[("Präsens", participle_i), ("Perfekt", participle_ii)],
            infinitives=[
                ("Präsens", plain_inf),
                ("Perfekt", perfect_inf),
                ("zu + Infinitiv", zu_inf),
                ("Perfekt mit zu", perfect_zu),
            ],
        )
