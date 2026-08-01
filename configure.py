from __future__ import annotations

from pathlib import Path
import yaml

root = Path(__file__).resolve().parent
settings_path = root / "settings.yaml"
bundled_database_path = (root / "data" / "woerterbuch.txt").resolve()
bundled_irregular_verbs_path = (root / "data" / "irregular_verbs.yaml").resolve()
bundled_irregular_adjectives_path = (root / "data" / "irregular_adjectives.yaml").resolve()

existing = {}
if settings_path.exists():
    existing = yaml.safe_load(settings_path.read_text(encoding="utf-8")) or {}


def resolve_existing_path(value, fallback: Path) -> Path:
    if value:
        candidate = Path(str(value)).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if candidate.exists():
            return candidate
    return fallback


selected_database_path = resolve_existing_path(
    existing.get("database_path"), bundled_database_path
)
selected_irregular_verbs_path = resolve_existing_path(
    existing.get("irregular_verbs_path"), bundled_irregular_verbs_path
)
selected_irregular_adjectives_path = resolve_existing_path(
    existing.get("irregular_adjectives_path"), bundled_irregular_adjectives_path
)

settings = {
    "database_path": str(selected_database_path),
    "irregular_verbs_path": str(selected_irregular_verbs_path),
    "irregular_adjectives_path": str(selected_irregular_adjectives_path),
    "max_results": int(existing.get("max_results", 20)),
    "fuzzy_threshold": int(existing.get("fuzzy_threshold", 58)),
    "search_debounce_ms": int(existing.get("search_debounce_ms", 80)),
    "conjugation_search_debounce_ms": int(existing.get("conjugation_search_debounce_ms", 60)),
    "conjugation_suggestion_count": int(existing.get("conjugation_suggestion_count", 14)),
    "pronunciation_enabled": bool(existing.get("pronunciation_enabled", True)),
    "pronunciation_api_url": str(
        existing.get("pronunciation_api_url", "https://translate.google.com/translate_tts")
    ),
    "pronunciation_language": str(existing.get("pronunciation_language", "de")),
    "pronunciation_timeout_ms": int(existing.get("pronunciation_timeout_ms", 12000)),
    "pronunciation_max_download_bytes": int(
        existing.get("pronunciation_max_download_bytes", 5000000)
    ),
    "window_title": str(existing.get("window_title", "Deutsch–English–Persian Dictionary")),
}
settings_path.write_text(
    yaml.safe_dump(settings, allow_unicode=True, sort_keys=False),
    encoding="utf-8",
)
print(f"Configured database_path: {selected_database_path}")
print(f"Configured irregular_verbs_path: {selected_irregular_verbs_path}")
print(f"Configured irregular_adjectives_path: {selected_irregular_adjectives_path}")
