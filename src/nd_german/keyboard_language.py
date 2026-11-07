"""Set a language-specific search field's actual desktop input source.

GNOME manages keyboard sources itself, including its IBus integration; XKB
alone is insufficient when the Qt application uses the IBus input method.
"""

from __future__ import annotations

import ctypes
import os
import re
import subprocess

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage
from PySide6.QtWidgets import QLineEdit


class GnomeInputSources:
    """Switch the GNOME input source (and IBus state), not just its XKB group."""

    def __init__(self) -> None:
        self._shell = QDBusInterface(
            "org.gnome.Shell", "/org/gnome/Shell", "org.gnome.Shell",
            QDBusConnection.sessionBus(),
        )

    def select(self, language: str) -> bool:
        if not self._shell.isValid():
            return False
        # Only literal identifiers: no application or user input reaches Eval.
        ids = '["ir"]' if language.lower() == "persian" else '["at","de","ch","us","gb"]'
        script = (
            "(function() {"
            "let m = imports.ui.status.keyboard.getInputSourceManager();"
            f"let ids = {ids};"
            "let s = Object.values(m.inputSources).find(x => ids.includes(x.id));"
            "if (!s) return false;"
            "if (m.currentSource !== s) s.activate(true);"
            "return true;"
            "})()"
        )
        reply = self._shell.call("Eval", script)
        return (
            reply.type() == QDBusMessage.MessageType.ReplyMessage
            and len(reply.arguments()) == 2
            and reply.arguments()[0] is True
            and reply.arguments()[1] == "true"
        )


class X11KeyboardLayouts:
    """Switch existing XKB groups only when a language-specific field gains focus."""

    def __init__(self) -> None:
        self._display = None
        self._x11 = None
        self._groups = self._configured_groups()
        if not self._groups or os.environ.get("XDG_SESSION_TYPE", "x11") == "wayland":
            return
        try:
            x11 = ctypes.CDLL("libX11.so.6")
            x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XkbLockGroup.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint]
            x11.XkbLockGroup.restype = ctypes.c_int
            x11.XFlush.argtypes = [ctypes.c_void_p]
            x11.XFlush.restype = ctypes.c_int
            x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
            x11.XCloseDisplay.restype = ctypes.c_int
            display = x11.XOpenDisplay(None)
            if display:
                self._display = display
                self._x11 = x11
        except (OSError, AttributeError):
            pass

    @staticmethod
    def _configured_groups() -> dict[str, int]:
        """Discover XKB group indices rather than assuming their order."""
        try:
            result = subprocess.run(
                ["setxkbmap", "-query"], capture_output=True, text=True,
                check=True, timeout=1,
            )
        except (OSError, subprocess.SubprocessError):
            return {}
        match = re.search(r"^layout:\s*(.+)$", result.stdout, re.MULTILINE)
        if not match:
            return {}
        layouts = [name.strip().lower() for name in match.group(1).split(",")]
        latin = next(
            (index for index, name in enumerate(layouts)
             if name in ("at", "de", "ch", "us", "gb")),
            None,
        )
        persian = next(
            (index for index, name in enumerate(layouts) if name == "ir"),
            None,
        )
        if latin is None or persian is None:
            return {}
        return {"german": latin, "english": latin, "penglish": latin, "persian": persian}

    def select(self, language: str) -> None:
        group = self._groups.get(language.lower())
        if self._x11 is not None and self._display is not None and group is not None:
            self._x11.XkbLockGroup(self._display, 0x0100, group)  # XkbUseCoreKbd
            self._x11.XFlush(self._display)

    def close(self) -> None:
        if self._x11 is not None and self._display is not None:
            self._x11.XCloseDisplay(self._display)
            self._display = None


class DictionaryKeyboardController(QObject):
    """Apply a language's existing layout on focus; let manual switching still work."""

    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self._gnome = GnomeInputSources()
        self._keyboard = X11KeyboardLayouts()
        self._fields: dict[QLineEdit, str] = {}
        self.destroyed.connect(lambda: self._keyboard.close())

    def watch(self, field: QLineEdit, language: str) -> None:
        self._fields[field] = language
        if language != "Persian":
            field.setInputMethodHints(Qt.InputMethodHint.ImhPreferLatin)
        field.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.FocusIn:
            language = self._fields.get(watched)
            if language is not None:
                if not self._gnome.select(language):
                    self._keyboard.select(language)
        return False
