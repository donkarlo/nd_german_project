from pathlib import Path
import re
import shutil
import sys

from PySide6.QtGui import QIcon

import dictionary_core
import language_application as application
from language_application import *  # noqa: F401,F403

try:
    import dictionary_storage as sqlite_search
    import verb_valency
    from entry_valency_editor import install as install_full_entry_rektion
    from search_history import install as install_search_history
    from window_ui import install_ui_polish
    from verb_valency import install as install_verb_rektion
except ImportError:
    from . import dictionary_storage as sqlite_search
    from . import verb_valency
    from .entry_valency_editor import install as install_full_entry_rektion
    from .search_history import install as install_search_history
    from .window_ui import install_ui_polish
    from .verb_valency import install as install_verb_rektion


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




application.base.language_icon = _project_language_icon


class GermanDictionaryApplication:
    """Composition root for dictionary storage, grammar and Qt features.

    Dependencies are configured once, with SQLite as the authoritative store.
    Legacy feature adapters are isolated behind this application boundary.
    """

    def configure(self) -> None:
        _ensure_project_settings_argument()
        sqlite_search.install(
            application,
            application.base,
            source_path=TEXT_DATABASE_PATH,
            sqlite_path=SQLITE_DATABASE_PATH,
        )
        install_ui_polish()
        install_search_history()
        install_full_entry_rektion(verb_valency)
        install_verb_rektion(
            application,
            application.base,
            sqlite_search,
            sqlite_path=SQLITE_DATABASE_PATH,
            text_path=None,
        )
        application.base.language_icon = _project_language_icon

    def run(self) -> int:
        self.configure()
        return application.main()


def main() -> int:
    return GermanDictionaryApplication().run()


if __name__ == "__main__":
    raise SystemExit(main())
