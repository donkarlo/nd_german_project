from pathlib import Path

from PySide6.QtGui import QIcon

import language_application as application
from language_application import *  # noqa: F401,F403


def _project_language_icon() -> QIcon:
    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.svg"
    if icon_path.is_file():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon
    return QIcon()


application.base.language_icon = _project_language_icon


def main() -> int:
    application.base.language_icon = _project_language_icon
    return application.main()


if __name__ == "__main__":
    raise SystemExit(main())
