from __future__ import annotations

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QStyle, QToolButton


_MAX_HISTORY = 100
_HISTORY_DELAY_MS = 650
_INSTALLED = False


def _make_history_button(window, *, back: bool) -> QToolButton:
    button = QToolButton(window)
    pixmap = (
        QStyle.StandardPixmap.SP_ArrowLeft
        if back
        else QStyle.StandardPixmap.SP_ArrowRight
    )
    button.setIcon(window.style().standardIcon(pixmap))
    button.setIconSize(QSize(15, 15))
    button.setFixedSize(30, 30)
    button.setAutoRaise(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    button.setAccessibleName("Previous dictionary search" if back else "Next dictionary search")
    button.setShortcut(QKeySequence("Alt+Left" if back else "Alt+Right"))
    button.setStyleSheet(
        """
        QToolButton {
            border: 1px solid transparent;
            border-radius: 7px;
            padding: 3px;
            background: transparent;
        }
        QToolButton:hover:enabled {
            background: #edf3fb;
            border-color: #c8d7e9;
        }
        QToolButton:pressed:enabled {
            background: #dce8f6;
            border-color: #afc4dc;
        }
        QToolButton:disabled {
            opacity: 0.42;
        }
        """
    )
    return button


def _update_history_buttons(window) -> None:
    history = getattr(window, "_dictionary_search_history", [])
    index = int(getattr(window, "_dictionary_search_history_index", -1))

    can_back = index > 0
    can_forward = 0 <= index < len(history) - 1
    window.search_back_button.setEnabled(can_back)
    window.search_forward_button.setEnabled(can_forward)

    if can_back:
        previous = history[index - 1]
        window.search_back_button.setToolTip(f'Back to “{previous}”  (Alt+Left)')
    else:
        window.search_back_button.setToolTip("No previous search  (Alt+Left)")

    if can_forward:
        following = history[index + 1]
        window.search_forward_button.setToolTip(f'Forward to “{following}”  (Alt+Right)')
    else:
        window.search_forward_button.setToolTip("No next search  (Alt+Right)")


def _commit_current_search(window) -> None:
    if getattr(window, "_dictionary_history_navigating", False):
        return

    query = window.search_box.text().strip()
    if not query:
        return

    history = list(getattr(window, "_dictionary_search_history", []))
    index = int(getattr(window, "_dictionary_search_history_index", -1))

    if 0 <= index < len(history) and history[index] == query:
        _update_history_buttons(window)
        return

    # A new search after going Back creates a new branch, exactly like a browser.
    if 0 <= index < len(history) - 1:
        history = history[: index + 1]

    # Avoid adjacent duplicates while still allowing the same query again later.
    if not history or history[-1] != query:
        history.append(query)

    if len(history) > _MAX_HISTORY:
        history = history[-_MAX_HISTORY:]

    window._dictionary_search_history = history
    window._dictionary_search_history_index = len(history) - 1
    _update_history_buttons(window)


def _schedule_history_commit(window, _text: str = "") -> None:
    if getattr(window, "_dictionary_history_navigating", False):
        window._dictionary_history_timer.stop()
        return
    if window.search_box.text().strip():
        window._dictionary_history_timer.start()
    else:
        window._dictionary_history_timer.stop()


def _navigate_history(window, step: int) -> None:
    # Preserve a just-typed query before moving away from it.
    if window._dictionary_history_timer.isActive():
        window._dictionary_history_timer.stop()
        _commit_current_search(window)

    history = getattr(window, "_dictionary_search_history", [])
    index = int(getattr(window, "_dictionary_search_history_index", -1))
    target = index + step
    if not (0 <= target < len(history)):
        _update_history_buttons(window)
        return

    window._dictionary_history_navigating = True
    try:
        window.search_timer.stop()
        window.search_box.setText(history[target])
        window._dictionary_search_history_index = target
        window.search_timer.stop()
        window.perform_search()
        window.search_box.setFocus()
        window.search_box.setCursorPosition(len(window.search_box.text()))
    finally:
        window._dictionary_history_navigating = False

    _update_history_buttons(window)


def _dictionary_tab_with_history(original):
    def build(self):
        tab = original(self)
        outer = tab.layout()
        top_item = outer.itemAt(0) if outer is not None else None
        top = top_item.layout() if top_item is not None else None
        if top is None:
            return tab

        self._dictionary_search_history: list[str] = []
        self._dictionary_search_history_index = -1
        self._dictionary_history_navigating = False

        self.search_back_button = _make_history_button(self, back=True)
        self.search_forward_button = _make_history_button(self, back=False)
        top.insertWidget(0, self.search_back_button)
        top.insertWidget(1, self.search_forward_button)

        self._dictionary_history_timer = QTimer(self)
        self._dictionary_history_timer.setSingleShot(True)
        self._dictionary_history_timer.setInterval(_HISTORY_DELAY_MS)
        self._dictionary_history_timer.timeout.connect(lambda: _commit_current_search(self))

        self.search_box.textChanged.connect(lambda text: _schedule_history_commit(self, text))
        self.search_box.returnPressed.connect(lambda: _commit_current_search(self))
        self.search_box.editingFinished.connect(lambda: _commit_current_search(self))
        self.search_back_button.clicked.connect(lambda: _navigate_history(self, -1))
        self.search_forward_button.clicked.connect(lambda: _navigate_history(self, +1))

        _update_history_buttons(self)
        return tab

    return build


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Import here so the patch works both as a script and as a package module.
    try:
        import app_legacy as legacy
    except ImportError:
        from . import app_legacy as legacy

    legacy.DictionaryWindow._build_dictionary_tab = _dictionary_tab_with_history(
        legacy.DictionaryWindow._build_dictionary_tab
    )
    _INSTALLED = True
