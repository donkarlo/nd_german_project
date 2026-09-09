from pathlib import Path
import re
import shutil
import sys

from PySide6.QtGui import QIcon

import dictionary_core
import language_application as application
from language_application import *  # noqa: F401,F403

try:
    from passive_patch import install_passive_conjugation
    from sqlite_search_patch import install as install_sqlite_search
    from ui_polish_patch import install_ui_polish
except ImportError:
    from .passive_patch import install_passive_conjugation
    from .sqlite_search_patch import install as install_sqlite_search
    from .ui_polish_patch import install_ui_polish


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PERSISTENCE_DIR = Path("/home/donkarlo/Dropbox/repo/data/nd_german_project")
LEGACY_SETTINGS_PATH = PROJECT_ROOT / "settings.yaml"
SETTINGS_PATH = PERSISTENCE_DIR / "settings.yaml"
TEXT_DATABASE_PATH = PROJECT_ROOT / "data" / "woerterbuch.txt"
SQLITE_DATABASE_PATH = PERSISTENCE_DIR / "dictionary.sqlite3"


def _project_language_icon() -> QIcon:
    icon_path = PROJECT_ROOT / "assets" / "app_icon.svg"
    if icon_path.is_file():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon
    return QIcon()


def _ensure_persistence_files() -> None:
    PERSISTENCE_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_PATH.exists() and LEGACY_SETTINGS_PATH.is_file():
        shutil.copy2(LEGACY_SETTINGS_PATH, SETTINGS_PATH)


def _ensure_project_settings_argument() -> None:
    _ensure_persistence_files()
    if "--settings" not in sys.argv:
        sys.argv[1:1] = ["--settings", str(SETTINGS_PATH)]


def _install_headword_colon_fix() -> None:
    """Ignore colons inside IPA/grammar metadata when extracting a dictionary headword."""

    def extract_headword(first_line: str) -> str:
        cleaned = dictionary_core.IPA_RE.sub("", first_line)
        cleaned = dictionary_core.PAREN_RE.sub("", cleaned)
        left = cleaned.split(":", 1)[0].strip()
        left = re.split(
            r"\s+(?=(?:nicht trennbar|trennbar|untrennbar|transitiv|intransitiv|"
            r"reflexiv|regelmäßig|unregelmäßig|stark|schwach|adjektiv|adverb|"
            r"pronom|konjunktion|präposition|substantiv|verb)\b)",
            left,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        return dictionary_core.WHITESPACE_RE.sub(" ", left).strip(" -")

    dictionary_core.extract_headword = extract_headword


application.base.language_icon = _project_language_icon


def main() -> int:
    _ensure_project_settings_argument()
    _install_headword_colon_fix()

    install_sqlite_search(
        application,
        application.base,
        source_path=TEXT_DATABASE_PATH,
        sqlite_path=SQLITE_DATABASE_PATH,
    )
    install_passive_conjugation()
    install_ui_polish()

    application.base.language_icon = _project_language_icon
    return application.main()


if __name__ == "__main__":
    raise SystemExit(main())
