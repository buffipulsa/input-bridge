"""Visual theme for the Input Bridge editor."""

from __future__ import annotations


def application_stylesheet() -> str:
    """Return the first-pass dark visual theme for the editor."""

    return """
    QWidget {
        background: #17191d;
        color: #e7eaf0;
        font-family: "Segoe UI";
        font-size: 10pt;
    }

    QMainWindow {
        background: #17191d;
    }

    QMenuBar {
        background: #1d2025;
        border-bottom: 1px solid #2f343d;
        padding: 4px 8px;
    }

    QMenuBar::item {
        padding: 6px 12px;
        background: transparent;
    }

    QMenuBar::item:selected,
    QMenu::item:selected {
        background: #2e6fbd;
        border-radius: 4px;
    }

    QMenu {
        background: #24282e;
        border: 1px solid #3a414c;
        padding: 6px;
    }

    QFrame {
        background: #202329;
        border: 1px solid #303640;
        border-radius: 8px;
    }

    QSplitter::handle {
        background: #15171a;
    }

    QLabel {
        background: transparent;
        border: none;
    }

    QLabel#breadcrumbRoot {
        color: #9ca8b8;
        font-weight: 600;
        padding: 5px 8px;
    }

    QPushButton#breadcrumbButton {
        color: #6fa8e8;
        background: transparent;
        border: none;
        padding: 5px 8px;
    }

    QPushButton#breadcrumbButton:hover {
        color: #b7d8ff;
        background: #26384e;
    }

    QPushButton {
        background: #292e36;
        border: 1px solid #3b4450;
        border-radius: 6px;
        padding: 7px 12px;
    }

    QPushButton:hover {
        background: #323a46;
        border-color: #568bd1;
    }

    QPushButton:pressed {
        background: #22558f;
    }

    QFrame#knobCard {
        background: #242930;
        border: 1px solid #3a424e;
        border-radius: 10px;
        padding: 2px;
    }

    QLabel#knobTitle {
        color: #aeb9c8;
        font-size: 9pt;
        font-weight: 600;
        padding: 2px 4px;
    }

    QPushButton#knobButton {
        background: #2c333d;
        border-color: #46515f;
        border-radius: 6px;
        padding: 5px 8px;
    }

    QPushButton#knobButton:hover {
        background: #354354;
        border-color: #6a9de0;
    }

    QPushButton#controlButton {
        background: #242930;
        border: 1px solid #3a424e;
        border-radius: 8px;
        padding: 10px 6px;
        font-size: 10pt;
    }

    QPushButton#controlButton:hover {
        background: #2c3541;
        border-color: #6a9de0;
    }

    QPushButton#controlButton:pressed {
        background: #22558f;
    }

    QComboBox,
    QLineEdit,
    QPlainTextEdit,
    QListWidget,
    QTreeWidget {
        background: #1c1f24;
        border: 1px solid #353c47;
        border-radius: 6px;
        selection-background-color: #2e6fbd;
        selection-color: #ffffff;
    }

    QComboBox,
    QLineEdit {
        padding: 6px 8px;
    }

    QComboBox::drop-down {
        border: none;
        width: 24px;
    }

    QTabWidget::pane {
        background: #202329;
        border: 1px solid #303640;
        border-radius: 6px;
        top: -1px;
    }

    QTabBar::tab {
        background: #24282e;
        border: 1px solid #303640;
        padding: 7px 14px;
        margin-right: 3px;
    }

    QTabBar::tab:selected {
        background: #2e6fbd;
        border-color: #568bd1;
    }

    QScrollBar:vertical {
        background: #1c1f24;
        width: 10px;
        margin: 2px;
    }

    QScrollBar::handle:vertical {
        background: #424b58;
        border-radius: 5px;
        min-height: 24px;
    }

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
