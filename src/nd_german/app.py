from pathlib import Path
import sys

from PySide6.QtGui import QIcon

from conjugation_passive import PassiveGermanConjugator
import language_application as application
from language_application import *  # noqa: F401,F403


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS_PATH = PROJECT_ROOT / "settings.yaml"


def _project_language_icon() -> QIcon:
    icon_path = PROJECT_ROOT / "assets" / "app_icon.svg"
    if icon_path.is_file():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon
    return QIcon()


def _ensure_project_settings_argument() -> None:
    if "--settings" not in sys.argv:
        sys.argv[1:1] = ["--settings", str(SETTINGS_PATH)]


application.base.legacy.GermanConjugator = PassiveGermanConjugator
application.base.language_icon = _project_language_icon


def main() -> int:
    _ensure_project_settings_argument()
    application.base.legacy.GermanConjugator = PassiveGermanConjugator
    application.base.language_icon = _project_language_icon
    return application.main()


if __name__ == "__main__":
    raise SystemExit(main())
