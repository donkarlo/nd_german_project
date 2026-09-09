from __future__ import annotations

import html

import app_base as base
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabBar, QLabel


GRAMMAR_CSS = ""


GRAMMAR_QT_STYLESHEET = """
body {
    font-family: sans-serif;
    font-size: 11pt;
    color: #263545;
}
h2 {
    color: #315f88;
    font-size: 14pt;
    font-weight: bold;
    margin-top: 14px;
    margin-bottom: 8px;
}
.hint {
    color: #526171;
    margin-top: 4px;
    margin-bottom: 12px;
}
table {
    border-collapse: collapse;
}
th {
    font-weight: bold;
}
td {
    font-weight: normal;
}
"""
def _grammar_table(headers: list[str], rows: list[list[str]]) -> str:
    """Qt-safe grammar table: visual styling is inline, forms stay normal-weight."""
    legacy = base.legacy
    cases = set(getattr(legacy, "CASES", ()))
    genders = set(getattr(legacy, "GENDERS", ()))

    case_palette = {
        "Nominativ": ("#eaf2fb", "#245d87"),
        "Akkusativ": ("#fff3ea", "#8a4f2f"),
        "Dativ": ("#eef9f2", "#356b49"),
        "Genitiv": ("#f3efff", "#58458e"),
    }
    gender_palette = {
        "Maskulin": ("#3f6fa1", "#ffffff"),
        "Feminin": ("#9a5271", "#ffffff"),
        "Neutrum": ("#4f7c65", "#ffffff"),
        "Plural": ("#8a6932", "#ffffff"),
    }
    gender_light = {
        "Maskulin": ("#edf4fb", "#315f88"),
        "Feminin": ("#fbf0f5", "#8b4966"),
        "Neutrum": ("#eef7f2", "#3d6a55"),
        "Plural": ("#fbf5e9", "#775a2c"),
    }

    base_header = (
        "padding:8px 10px; border:1px solid #365786; "
        "background-color:#466eaa; color:#ffffff; font-weight:bold;"
    )
    base_cell = (
        "padding:7px 9px; border:1px solid #aebfd6; "
        "background-color:#f8fbff; color:#263545; font-weight:normal;"
    )

    head_cells: list[str] = []
    for value in headers:
        label = str(value)
        style = base_header
        if label in gender_palette:
            bg, fg = gender_palette[label]
            style = (
                "padding:8px 10px; border:1px solid #365786; "
                f"background-color:{bg}; color:{fg}; font-weight:bold;"
            )
        head_cells.append(
            f"<th style='{style}'>{html.escape(label)}</th>"
        )

    body: list[str] = []
    for row_index, row in enumerate(rows):
        cells: list[str] = []
        for index, value in enumerate(row):
            label = str(value)
            header = str(headers[index]) if index < len(headers) else ""
            style = base_cell
            inner = html.escape(label)

            if label in cases:
                bg, fg = case_palette[label]
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:{fg}; font-weight:bold;"
                )
            elif label in genders:
                bg, fg = gender_light[label]
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:{fg}; font-weight:bold;"
                )
            elif header == "Kasus" and label in case_palette:
                bg, fg = case_palette[label]
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:{fg}; font-weight:bold;"
                )
            elif header in {"Genus/Numerus", "Genus/Numerus des Bezugsworts"} and label in gender_light:
                bg, fg = gender_light[label]
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:{fg}; font-weight:bold;"
                )
            elif header == "Form" or header in genders or header in {"Singular", "Plural", "Nomenform"}:
                # Answers/forms intentionally remain normal-weight.
                bg = "#ffffff" if row_index % 2 == 0 else "#f4f8fc"
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:#263545; font-weight:normal;"
                )
            else:
                bg = "#fbfdff" if row_index % 2 == 0 else "#f1f6fb"
                style = (
                    "padding:7px 9px; border:1px solid #aebfd6; "
                    f"background-color:{bg}; color:#33485e; font-weight:normal;"
                )

            cells.append(f"<td style='{style}'>{inner}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")

    return (
        "<table width='100%' cellspacing='0' cellpadding='0' "
        "style='border-collapse:collapse; margin-top:8px; margin-bottom:18px;'>"
        f"<thead><tr>{''.join(head_cells)}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table>"
    )


def _format_conjugation_line(line: str) -> str:
    text = line.strip()
    if not text:
        return ""

    agent_html = ""
    core = text
    if " von " in core:
        core, agent = core.rsplit(" von ", 1)
        agent_html = (
            " <span style='color:#7b3f72; font-weight:700'>"
            f"von {html.escape(agent)}</span>"
        )

    pronoun = ""
    rest = core
    for candidate in ("er/sie/es", "ich", "du", "wir", "ihr", "Sie"):
        prefix = candidate + " "
        if core.startswith(prefix):
            pronoun = candidate
            rest = core[len(prefix):]
            break

    if " " in rest:
        finite, remainder = rest.split(" ", 1)
    else:
        finite, remainder = rest, ""

    pieces: list[str] = []
    if pronoun:
        pieces.append(
            "<span style='color:#5d6b7e; font-weight:700'>"
            f"{html.escape(pronoun)}</span> "
        )

    pieces.append(
        "<span style='color:#1f5f9b; font-weight:800'>"
        f"{html.escape(finite)}</span>"
    )
    if remainder:
        pieces.append(
            " <span style='color:#253447'>"
            f"{html.escape(remainder)}</span>"
        )
    pieces.append(agent_html)
    return "".join(pieces)


def _card_palette(title: str) -> tuple[str, str, str]:
    lowered = title.casefold()
    if "präsens" in lowered:
        return "#edf7ff", "#9ac9ec", "#245d87"
    if "präteritum" in lowered:
        return "#fff3ea", "#e8b89b", "#8a4f2f"
    if "plusquamperfekt" in lowered:
        return "#fff1f8", "#e7adca", "#894766"
    if "perfekt" in lowered:
        return "#f3efff", "#c4b5ee", "#58458e"
    if "futur" in lowered:
        return "#eef9f2", "#add9bd", "#356b49"
    return "#f6f8fb", "#cad3df", "#33485e"


def _conjugation_card(cls, title: str, lines: list[str]) -> str:
    background, border, heading = _card_palette(title)
    body = "".join(
        "<div style='margin:0 0 8px 0; white-space:normal; line-height:1.5'>"
        f"{cls._format_conjugation_line(line)}</div>"
        for line in lines
    )
    return (
        "<td valign='top' style='padding:7px; min-width:0'>"
        f"<div style='background:{background}; border:1px solid {border}; "
        "padding:12px 13px; border-radius:8px'>"
        f"<div align='center' style='margin-bottom:11px; color:{heading}; "
        "font-size:11pt; font-weight:800'>"
        f"{html.escape(title)}</div>{body}</div></td>"
    )


def _conjugation_section(cls, title: str, cards: list[tuple[str, list[str]]]) -> str:
    rows: list[str] = []
    for start in range(0, len(cards), 3):
        chunk = cards[start : start + 3]
        cells = "".join(
            cls._conjugation_card(card_title, lines)
            for card_title, lines in chunk
        )
        cells += "<td></td>" * (3 - len(chunk))
        rows.append(f"<tr>{cells}</tr>")

    passive = "PASSIV" in title.upper()
    section_bg = "#725078" if passive else "#315f88"
    return (
        f"<div style='background:{section_bg}; color:white; margin:18px 7px 7px 7px; "
        "padding:7px 11px; font-weight:800; letter-spacing:.3px'>"
        f"{html.escape(title)}</div>"
        "<table width='100%' cellspacing='0' cellpadding='0'>"
        + "".join(rows)
        + "</table>"
    )


def _render_conjugation(self, result) -> None:
    sections = "".join(
        self._conjugation_section(section_name, cards)
        for section_name, cards in result.sections.items()
    )
    imperative = self._conjugation_section(
        "IMPERATIV PRÄSENS", [("du · ihr · Sie", result.imperatives)]
    )
    participles = self._conjugation_section(
        "PARTIZIP", [(name, [form]) for name, form in result.participles]
    )
    infinitives = self._conjugation_section(
        "INFINITIV", [(name, [form]) for name, form in result.infinitives]
    )
    note = (
        "<div style='margin:12px 8px; padding:10px 12px; background:#fff7df; "
        "border:1px solid #e8d28f'><b>Note:</b> "
        f"{html.escape(result.note)}</div>"
        if result.note
        else ""
    )

    self.conjugation_results.setHtml(
        "<div style='padding:10px; background:#fbfcfe'>"
        "<div style='background:#eaf2fb; border:1px solid #bfd2e8; "
        "padding:12px 14px; margin:0 6px 10px 6px'>"
        f"<h2 align='center' style='color:#214f79; margin:2px 0 7px 0'>"
        f"{html.escape(result.infinitive)}</h2>"
        "<div align='center' style='color:#4f6275'>"
        "Partizip II: "
        f"<b style='color:#6b3f7d'>{html.escape(result.participle)}</b>"
        " &nbsp;·&nbsp; Hilfsverb: "
        f"<b style='color:#1f5f9b'>{html.escape(result.auxiliary)}</b>"
        f" &nbsp;·&nbsp; {html.escape(result.source)}</div></div>"
        f"{note}{sections}{imperative}{participles}{infinitives}</div>"
    )
    self.conjugation_results.verticalScrollBar().setValue(0)


def _show_existing_word(window, headword: str) -> None:
    window.tabs.setCurrentIndex(0)
    window.search_box.setText(headword)
    window.search_box.setFocus()
    window.perform_search()


def _open_add_dialog(self) -> None:
    legacy = base.legacy
    if self.index is None:
        legacy.QMessageBox.warning(
            self, "Database unavailable", "Load a app database first."
        )
        return

    dialog = legacy.AddEntryDialog(self)
    if dialog.exec() != legacy.QDialog.Accepted:
        return

    try:
        added = self.index.add_entry(self.database_path, dialog.entry_text())
    except legacy.DuplicateEntryError as exc:
        legacy.QMessageBox.warning(
            self,
            "Duplicate entry",
            f'“{exc.headword}” already exists with grammatical role “{exc.role}”.',
        )
        _show_existing_word(self, exc.headword)
        return
    except (OSError, UnicodeError, ValueError) as exc:
        legacy.QMessageBox.critical(self, "Could not add entry", str(exc))
        return

    self.tabs.setCurrentIndex(0)
    self.search_box.setText(added.headword)
    self.perform_search()
    legacy.QMessageBox.information(
        self,
        "Entry added",
        f'Added “{added.headword}” ({added.role}) to the app.',
    )


def _polish_controls(window) -> None:
    legacy = base.legacy

    for edit in window.findChildren(legacy.QLineEdit):
        edit.setMinimumHeight(38)
        font = edit.font()
        if font.pointSize() < 11:
            font.setPointSize(11)
            edit.setFont(font)
        edit.setStyleSheet(
            "QLineEdit { padding: 5px 9px; border: 1px solid #b9c5d3; "
            "border-radius: 6px; background: #ffffff; }"
            "QLineEdit:focus { border: 1px solid #4f83b7; }"
        )

    for combo in window.findChildren(legacy.QComboBox):
        combo.setMinimumHeight(36)
        font = combo.font()
        if font.pointSize() < 10:
            font.setPointSize(10)
            combo.setFont(font)

    if hasattr(window, "add_button"):
        window.add_button.setMinimumHeight(38)

    if hasattr(window, "tabs"):
        window.tabs.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #b8c6d6;
                border-top: 2px solid #315f88;
                background: #ffffff;
            }

            QTabBar::tab {
                min-height: 34px;
                padding: 0px;
                margin-right: 3px;
                border: none;
                background: transparent;
            }
            """
        )

        tab_bar = window.tabs.tabBar()
        tab_palette = (
            ("#dceaf8", "#315f88"),  # Dictionary
            ("#eee6f7", "#6b3f7d"),  # Conjugation
            ("#fbe9dc", "#8a4f2f"),  # Artikel
            ("#e1f1e7", "#356b49"),  # Pronomen
            ("#f5ead3", "#8a6932"),  # Adjektivendungen
        )

        tab_labels = []
        for index in range(window.tabs.count()):
            title = window.tabs.tabText(index)
            bg, fg = tab_palette[index % len(tab_palette)]

            label = QLabel(title, tab_bar)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAttribute(
                Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
            )
            label.setMinimumWidth(112)
            label.setMinimumHeight(34)
            label.setContentsMargins(14, 7, 14, 7)

            tab_bar.setTabButton(index, QTabBar.ButtonPosition.LeftSide, label)
            tab_bar.setTabText(index, "")
            tab_bar.setTabToolTip(index, title)
            tab_labels.append((label, bg, fg))

        def update_tab_colors(current_index: int) -> None:
            for index, (label, bg, fg) in enumerate(tab_labels):
                if index == current_index:
                    label.setStyleSheet(
                        "QLabel {"
                        " background-color:#315f88;"
                        " color:#ffffff;"
                        " font-weight:800;"
                        " border:1px solid #315f88;"
                        " border-top-left-radius:7px;"
                        " border-top-right-radius:7px;"
                        "}"
                    )
                else:
                    label.setStyleSheet(
                        "QLabel {"
                        f" background-color:{bg};"
                        f" color:{fg};"
                        " font-weight:700;"
                        " border:1px solid #b9c7d6;"
                        " border-bottom:none;"
                        " border-top-left-radius:7px;"
                        " border-top-right-radius:7px;"
                        "}"
                    )

        window.tabs.currentChanged.connect(update_tab_colors)
        update_tab_colors(window.tabs.currentIndex())

    if hasattr(window, "conjugation_results"):
        font = window.conjugation_results.font()
        if font.pointSize() < 11:
            font.setPointSize(11)
            window.conjugation_results.setFont(font)

    # QTextBrowser/QTextDocument supports a limited CSS subset. Apply grammar
    # styling through the document API, while table cells also carry inline
    # fallback styles. Dictionary results are deliberately excluded.
    for browser_name in ("article_results", "pronoun_results", "adj_results"):
        browser = getattr(window, browser_name, None)
        if browser is not None:
            browser.document().setDefaultStyleSheet(GRAMMAR_QT_STYLESHEET)

    # The original __init__ rendered these tabs before this polish hook ran.
    # Render them once again so the new default stylesheet takes effect now.
    if hasattr(window, "_render_article"):
        window._render_article()
    if hasattr(window, "_render_pronoun"):
        window._render_pronoun()
    if hasattr(window, "_render_adjective"):
        window._render_adjective()

    important_labels = {
        "Artikeltyp:",
        "Kasus:",
        "Genus/Numerus:",
        "Typ:",
        "Person:",
        "Besitzer/Subjekt:",
        "Bezugswort:",
        "Adjektiv:",
        "Begleiter/Artikel:",
        "Deklination:",
        "Nomen:",
    }
    for label in window.findChildren(legacy.QLabel):
        if label.text().strip() in important_labels:
            font = label.font()
            font.setBold(True)
            label.setFont(font)


def _install_runtime_patches() -> None:
    legacy = base.legacy
    cls = legacy.DictionaryWindow
    if getattr(cls, "_nd_ui_polish_installed", False):
        return

    original_init = cls.__init__

    def polished_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _polish_controls(self)

    cls.__init__ = polished_init
    cls.GRAMMAR_CSS = ""
    cls._table = staticmethod(_grammar_table)
    cls._format_conjugation_line = staticmethod(_format_conjugation_line)
    cls._conjugation_card = classmethod(_conjugation_card)
    cls._conjugation_section = classmethod(_conjugation_section)
    cls._render_conjugation = _render_conjugation
    cls.open_add_dialog = _open_add_dialog
    cls._nd_ui_polish_installed = True


def install_ui_polish() -> None:
    """Install after app_base's own monkey patches, but before the window is created."""
    current_install = base.install
    if getattr(current_install, "_nd_ui_polish_wrapper", False):
        return

    original_install = current_install

    def install_then_polish() -> None:
        original_install()
        _install_runtime_patches()

    install_then_polish._nd_ui_polish_wrapper = True
    base.install = install_then_polish
