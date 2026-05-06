from PySide6.QtWidgets import QApplication


class ThemeManager:
    DEFAULT = "default"
    PIXEL = "pixel"

    _current = DEFAULT

    @classmethod
    def current(cls) -> str:
        return cls._current

    @classmethod
    def apply_theme(cls, app: QApplication, theme_name: str) -> str:
        theme = THEMES.get(theme_name)
        if theme is None:
            return cls._current
        app.setStyleSheet(theme["stylesheet"])
        cls._current = theme_name
        return theme_name

    @classmethod
    def toggle(cls, app: QApplication) -> str:
        next_theme = cls.PIXEL if cls._current == cls.DEFAULT else cls.DEFAULT
        return cls.apply_theme(app, next_theme)


THEMES = {
    "default": {
        "name": "默认主题",
        "stylesheet": "",
    },
    "pixel": {
        "name": "像素风",
        "stylesheet": """
            QMainWindow {
                background-color: #0d0d0d;
            }
            QToolBar {
                background: #111118;
                border-bottom: 3px solid #00ff41;
                padding: 4px;
                spacing: 6px;
            }
            QToolBar QLabel {
                color: #00ff41;
                font-size: 13px;
                font-weight: bold;
            }
            QToolButton {
                background: #1a1a2e;
                color: #00ff41;
                border: 2px solid #00ff41;
                padding: 5px 10px;
                font-size: 12px;
                min-width: 60px;
            }
            QToolButton:hover {
                background: #00ff41;
                color: #0d0d0d;
                border-color: #00cc33;
            }
            QToolButton:pressed {
                background: #009933;
                border-color: #009933;
                color: #0d0d0d;
            }
            QToolButton:checked {
                background: #004400;
                color: #00ff41;
                border-color: #00ff41;
            }
            QToolButton:disabled {
                background: #1a1a2e;
                color: #555;
                border-color: #555;
            }
            QStatusBar {
                background: #111118;
                border-top: 3px solid #00ff41;
                color: #00ff41;
                font-size: 12px;
            }
            QStatusBar::item {
                border: none;
            }
            QProgressBar {
                background: #0d0d0d;
                border: 2px solid #00ff41;
                height: 18px;
                text-align: center;
                color: #0d0d0d;
                font-size: 11px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: #00ff41;
                margin: 0px;
            }
            QSplitter::handle {
                background: #333;
                width: 4px;
                border-left: 1px solid #555;
                border-right: 1px solid #555;
            }
            QScrollBar:vertical {
                background: #0d0d0d;
                width: 16px;
                border-left: 2px solid #333;
            }
            QScrollBar::handle:vertical {
                background: #00ff41;
                min-height: 24px;
                border: 1px solid #00aa33;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #0d0d0d;
                height: 16px;
                border-top: 2px solid #333;
            }
            QScrollBar::handle:horizontal {
                background: #00ff41;
                min-width: 24px;
                border: 1px solid #00aa33;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QLabel {
                color: #e0e0e0;
            }
            QFrame[frameShape="4"], QFrame[frameShape="5"] {
                background: #333;
            }
            QMenu {
                background: #1a1a2e;
                border: 2px solid #00ff41;
                color: #00ff41;
                padding: 2px;
            }
            QMenu::item {
                padding: 4px 20px;
            }
            QMenu::item:selected {
                background: #00ff41;
                color: #0d0d0d;
            }
            QMenu::separator {
                height: 2px;
                background: #333;
                margin: 4px 0;
            }
            QToolTip {
                background: #1a1a2e;
                color: #00ff41;
                border: 2px solid #00ff41;
                padding: 4px;
            }
            QPushButton {
                background: #1a1a2e;
                color: #00ff41;
                border: 2px solid #00ff41;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #00ff41;
                color: #0d0d0d;
            }
            QPushButton:pressed {
                background: #009933;
                border-color: #009933;
            }
        """,
    },
}
