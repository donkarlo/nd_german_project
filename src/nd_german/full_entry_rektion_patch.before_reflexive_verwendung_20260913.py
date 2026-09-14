from __future__ import annotations

import re


_CASE = r"Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?"
_PLACEHOLDER = (
    r"jemanden/etwas|jemandem/etwas|jemandes/einer\s+Sache|jemand/etwas|"
    r"jemanden|jemandem|jemandes|jemand|etwas|jdn\.?|jdm\.?|etw\.?"
)
_BARE_INFINITIVE_RE = re.compile(r"\bInfinitiv\s+ohne\s+zu\b", re.IGNORECASE)


def _clean_pattern_text(text: str) -> str:
    """Normalize common ChatGPT/dictionary notation before valency parsing."""
    value = text.replace("\u00a0", " ").replace("\u202f", " ").strip()
    value = value.replace("**", "").replace("__", "").replace("`", "")

    # jemanden/etwas (Akk.) -> jemanden/etwas [Akk.]
    value = re.sub(
        rf"\(\s*(?P<case>{_CASE})(?:\.)?\s*\)",
        lambda m: f"[{m.group('case')}.]",
        value,
        flags=re.IGNORECASE,
    )
    # jemanden/etwas Akk. -> jemanden/etwas [Akk.]
    value = re.sub(
        rf"(?P<slot>\b(?:{_PLACEHOLDER})\b)\s+(?P<case>{_CASE})(?:\.)?"
        rf"(?=\s*(?:$|\+|\||;|,|\)))",
        lambda m: f"{m.group('slot')} [{m.group('case')}.]",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[ \t]+", " ", value).strip()


def _has_grounded_argument(pattern) -> bool:
    """Do not turn mere 'intransitiv/reflexiv' metadata into a visible '?' Rektion."""
    for arg in getattr(pattern, "arguments", ()):
        role = getattr(arg, "role", "")
        case_code = (getattr(arg, "case_code", None) or "").upper()
        if role in {"clause", "infinitive"}:
            return True
        if getattr(arg, "preposition", None):
            return True
        if case_code and case_code != "UNK":
            return True
    return False


def install(verb_rektion_module) -> None:
    """Keep one complete-entry editor and parse Rektion from the pasted entry."""

    # Accept both the canonical plain label and pasted Markdown variants.
    verb_rektion_module.REKTION_LINE_RE = re.compile(
        r"^\s*(?:[-•]\s*)?(?:\*\*|__)?"
        r"Rektion(?:\s+\d+)?(?:\s*\[(?P<sense>[^\]]+)\])?"
        r"(?:\*\*|__)?\s*:\s*(?:\*\*|__)?(?P<value>.*?)\s*$",
        re.IGNORECASE,
    )

    # Extend explicit parsing while preserving the normalized v2 SQLite model.
    original_parse = verb_rektion_module._parse_pattern_text
    if not getattr(original_parse, "_nd_full_entry_mode_v2", False):
        def parse_pattern_text(text: str, *, first_line: str, headword: str, sense_label: str | None = None):
            cleaned = _clean_pattern_text(text)
            bare_infinitive = bool(_BARE_INFINITIVE_RE.search(cleaned))
            if not bare_infinitive:
                return original_parse(
                    cleaned,
                    first_line=first_line,
                    headword=headword,
                    sense_label=sense_label,
                )

            remaining = _BARE_INFINITIVE_RE.sub("", cleaned)
            remaining = re.sub(r"^\s*\+\s*|\s*\+\s*$", "", remaining).strip()
            args = []
            if remaining:
                base_pattern = original_parse(
                    remaining,
                    first_line=first_line,
                    headword=headword,
                    sense_label=sense_label,
                )
                args.extend(
                    arg for arg in base_pattern.arguments
                    if getattr(arg, "role", "") != "complement"
                    or (getattr(arg, "case_code", None) or "").upper() != "UNK"
                )
            args.append(
                verb_rektion_module.ArgumentSpec(
                    role="infinitive",
                    placeholder="Infinitiv ohne zu",
                    infinitive_marker="ohne zu",
                    required=True,
                )
            )
            return verb_rektion_module.PatternSpec(
                arguments=tuple(args),
                source="explicit",
                confidence=1.0,
                sense_label=sense_label,
            )

        parse_pattern_text._nd_full_entry_mode_v2 = True
        verb_rektion_module._parse_pattern_text = parse_pattern_text

    # Unknown inferred patterns such as "Rektion: ?" are not useful to the learner.
    original_patterns_for_entry = verb_rektion_module._patterns_for_entry
    if not getattr(original_patterns_for_entry, "_nd_grounded_rektion_only", False):
        def patterns_for_entry(raw: str, first_line: str, headword: str):
            patterns = original_patterns_for_entry(raw, first_line, headword)
            return [pattern for pattern in patterns if _has_grounded_argument(pattern)]

        patterns_for_entry._nd_grounded_rektion_only = True
        verb_rektion_module._patterns_for_entry = patterns_for_entry

    # Keep Rektion in the user's/source format: after Bedeutung/Synonyme/Verwendung
    # and immediately before examples/conjugation, rather than after Penglish.
    def canonical_rektion_raw(raw: str, patterns) -> str:
        lines = [line.rstrip() for line in raw.strip().splitlines()]
        lines = [line for line in lines if not verb_rektion_module.REKTION_LINE_RE.match(line)]

        grounded = [
            pattern for pattern in patterns
            if str(getattr(pattern, "display", "")).strip()
            and _has_grounded_argument(pattern)
        ]
        if not grounded:
            return "\n".join(lines).strip()

        rendered = []
        for index, pattern in enumerate(grounded):
            label = "Rektion" if index == 0 else f"Rektion {index + 1}"
            sense_label = getattr(pattern, "sense_label", None)
            if sense_label:
                label += f" [{sense_label}]"
            rendered.append(f"{label}: {pattern.display}")

        insertion = len(lines)
        tense_labels = {
            "präsens", "präteritum", "perfekt", "futur i",
            "konjunktiv ii", "konjunktiv i",
        }
        for index, line in enumerate(lines[1:], start=1):
            stripped = line.strip()
            label = stripped.split(":", 1)[0].strip().casefold() if ":" in stripped else ""
            if stripped.casefold().startswith("ex:") or label in tense_labels:
                insertion = index
                break

        lines[insertion:insertion] = rendered
        return "\n".join(lines).strip()

    canonical_rektion_raw._nd_source_order = True
    verb_rektion_module._canonical_rektion_raw = canonical_rektion_raw

    # Desktop Add/Edit stays one paste-ready complete-entry box.
    def no_separate_rektion_editor(base) -> None:
        return None

    no_separate_rektion_editor._nd_full_entry_mode = True
    verb_rektion_module._patch_add_dialog = no_separate_rektion_editor

    # Same purple used by Bedeutung, Synonyme, Verwendung and other field labels.
    original_render = verb_rektion_module._render_rektion_line
    if not getattr(original_render, "_nd_purple_rektion_label", False):
        def render_rektion_line(line: str):
            rendered = original_render(line)
            if rendered is None:
                return None
            return rendered.replace("color:#315f88", "color:#6f42c1")

        render_rektion_line._nd_purple_rektion_label = True
        verb_rektion_module._render_rektion_line = render_rektion_line
