from __future__ import annotations

import re


_MARKER = r"(?:\*\*|__)?"
_CASE = r"Nom(?:inativ)?|Akk(?:usativ)?|Dat(?:iv)?|Gen(?:itiv)?"
_PLACEHOLDER = (
    r"jemanden/etwas|jemandem/etwas|jemandes/einer\s+Sache|jemand/etwas|"
    r"jemanden|jemandem|jemandes|jemand|etwas|jdn\.?|jdm\.?|etw\.?"
)


def _clean_pattern_text(text: str) -> str:
    """Accept paste-ready ChatGPT/Markdown notation and normalize it for the v2 parser."""
    value = text.replace("\u00a0", " ").replace("\u202f", " ").strip()
    value = value.replace("**", "").replace("__", "").replace("`", "")

    # Common learning notation: jemanden/etwas (Akk.) -> jemanden/etwas [Akk.]
    value = re.sub(
        rf"\(\s*(?P<case>{_CASE})(?:\.)?\s*\)",
        lambda m: f"[{m.group('case')}.]",
        value,
        flags=re.IGNORECASE,
    )
    # Also accept the user's compact form: jemanden/etwas Akk.
    value = re.sub(
        rf"(?P<slot>\b(?:{_PLACEHOLDER})\b)\s+(?P<case>{_CASE})(?:\.)?(?=\s*(?:$|\+|\||;|,|\)))",
        lambda m: f"{m.group('slot')} [{m.group('case')}.]",
        value,
        flags=re.IGNORECASE,
    )

    # Normalize whitespace without touching the semantics of +, / or parentheses.
    value = re.sub(r"[ \t]+", " ", value).strip()
    return value


def install(verb_rektion_module) -> None:
    """Switch verb rection editing back to the single complete-entry editor.

    The normalized SQLite valency model stays active. Only the redundant second
    editor is removed; Rektion lines are parsed from the complete pasted entry.
    """

    # Accept plain and Markdown labels, e.g.:
    # Rektion: ...
    # **Rektion:** ...
    # **Rektion 2:** ...
    verb_rektion_module.REKTION_LINE_RE = re.compile(
        r"^\s*(?:[-•]\s*)?(?:\*\*|__)?"
        r"Rektion(?:\s+\d+)?(?:\s*\[(?P<sense>[^\]]+)\])?"
        r"(?:\*\*|__)?\s*:\s*(?:\*\*|__)?(?P<value>.*?)\s*$",
        re.IGNORECASE,
    )

    original_parse = verb_rektion_module._parse_pattern_text
    if not getattr(original_parse, "_nd_full_entry_mode", False):
        def parse_pattern_text(text: str, *, first_line: str, headword: str, sense_label: str | None = None):
            return original_parse(
                _clean_pattern_text(text),
                first_line=first_line,
                headword=headword,
                sense_label=sense_label,
            )

        parse_pattern_text._nd_full_entry_mode = True
        verb_rektion_module._parse_pattern_text = parse_pattern_text

    # The desktop Add/Edit dialog must contain only the original complete-entry box.
    def no_separate_rektion_editor(base) -> None:
        return None

    no_separate_rektion_editor._nd_full_entry_mode = True
    verb_rektion_module._patch_add_dialog = no_separate_rektion_editor
