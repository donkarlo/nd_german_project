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
    # Also accept compact notation: jemanden/etwas Akk.
    value = re.sub(
        rf"(?P<slot>\b(?:{_PLACEHOLDER})\b)\s+(?P<case>{_CASE})(?:\.)?(?=\s*(?:$|\+|\||;|,|\)))",
        lambda m: f"{m.group('slot')} [{m.group('case')}.]",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(r"[ \t]+", " ", value).strip()
    return value


def install(verb_rektion_module) -> None:
    """Use one complete-entry editor and parse Rektion from that pasted entry."""

    # Accept plain and Markdown labels:
    # Rektion: ...
    # **Rektion:** ...
    # Rektion 2: ...
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

    # Desktop Add/Edit must contain only the original complete-entry box.
    def no_separate_rektion_editor(base) -> None:
        return None

    no_separate_rektion_editor._nd_full_entry_mode = True
    verb_rektion_module._patch_add_dialog = no_separate_rektion_editor

    # Match the ordinary dictionary field-label purple exactly.
    # language_application.py uses #6f42c1 for Bedeutung, Synonyme, Verwendung, etc.
    original_render = verb_rektion_module._render_rektion_line
    if not getattr(original_render, "_nd_purple_rektion_label", False):
        def render_rektion_line(line: str):
            rendered = original_render(line)
            if rendered is None:
                return None
            return rendered.replace("color:#315f88", "color:#6f42c1")

        render_rektion_line._nd_purple_rektion_label = True
        verb_rektion_module._render_rektion_line = render_rektion_line
