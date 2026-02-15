from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFontDatabase
import config


class FontPickerDialog(QDialog):
    def __init__(self, parent=None, current_font_family="Arial", preview_callback=None):
        super().__init__(parent)
        self._selected_font_family = (current_font_family or "").strip() or "Arial"
        self._all_families = sorted(QFontDatabase.families())
        self._preview_callback = preview_callback
        self.old_pos = None

        self.translations = {
            "RU": {
                "title": "Выбор шрифта часов",
                "search": "Поиск шрифта...",
                "cancel": "Отмена",
                "ok": "OK",
            },
            "EN": {
                "title": "Clock Font Picker",
                "search": "Search font...",
                "cancel": "Cancel",
                "ok": "OK",
            },
        }
        settings = QSettings("MyTradeTools", "TF-Alerter")
        self.current_lang = settings.value("language", "RU")
        self.t = self.translations.get(self.current_lang, self.translations["RU"])

        self.setWindowTitle(self.t["title"])
        self.setFixedSize(360, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        container = QFrame(self)
        container.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLORS['background']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 10px;
            }}
            """
        )
        container.setGeometry(0, 0, 360, 420)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel(self.t["title"])
        title.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: 13px; font-weight: bold; border: none; background: transparent;"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.t["search"])
        self.search_edit.setStyleSheet(
            "QLineEdit { background: #1a1a1a; color: #bbb; border: 1px solid #333; border-radius: 6px; padding: 6px; }"
        )
        self.search_edit.textChanged.connect(self._filter_fonts)
        layout.addWidget(self.search_edit)

        self.font_list = QListWidget()
        self.font_list.setStyleSheet(
            "QListWidget { background: #1a1a1a; color: #bbb; border: 1px solid #333; border-radius: 6px; outline: 0; } "
            "QListWidget::item { padding: 5px; border-radius: 4px; } "
            "QListWidget::item:hover { background: #262b33; color: #d0d6de; } "
            "QListWidget::item:selected { background: #2d3440; color: #e7ebf0; border: 1px solid #3d4654; } "
            "QListWidget::item:selected:active { background: #2d3440; color: #e7ebf0; border: 1px solid #3d4654; } "
            "QListWidget::item:selected:!active { background: #2d3440; color: #e7ebf0; border: 1px solid #3d4654; }"
        )
        self.font_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.font_list.itemClicked.connect(self._on_item_clicked)
        self.font_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.font_list.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.font_list)

        button_row = QHBoxLayout()
        button_row.addStretch()

        cancel_btn = QPushButton(self.t["cancel"])
        cancel_btn.setFixedHeight(30)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(self._button_style())
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton(self.t["ok"])
        ok_btn.setFixedHeight(30)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(self._button_style())
        ok_btn.clicked.connect(self.accept)

        button_row.addWidget(cancel_btn)
        button_row.addSpacing(6)
        button_row.addWidget(ok_btn)
        layout.addLayout(button_row)

        self._populate_fonts(self._all_families)
        self._select_current_font(current_font_family)

    def _button_style(self):
        return f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid #1e90ff;
            }}
        """

    def _populate_fonts(self, families):
        self.font_list.clear()
        for family in families:
            item = QListWidgetItem(family)
            self.font_list.addItem(item)

    def _filter_fonts(self, text):
        query = (text or "").strip().lower()
        if not query:
            filtered = self._all_families
        else:
            filtered = [name for name in self._all_families if query in name.lower()]

        self._populate_fonts(filtered)
        self._select_current_font(self._selected_font_family)

    def _select_current_font(self, family):
        target = (family or "").strip()
        if not target:
            return
        for row in range(self.font_list.count()):
            item = self.font_list.item(row)
            if item and item.text() == target:
                self.font_list.setCurrentRow(row)
                self.font_list.scrollToItem(item)
                break

    def _on_selection_changed(self):
        item = self.font_list.currentItem()
        if item:
            self._selected_font_family = item.text().strip()
            if callable(self._preview_callback):
                self._preview_callback(self._selected_font_family)

    def _on_item_clicked(self, item):
        if item:
            self._selected_font_family = item.text().strip()
            if callable(self._preview_callback):
                self._preview_callback(self._selected_font_family)

    def _on_item_double_clicked(self, item):
        if item:
            self._selected_font_family = item.text().strip()
        self.accept()

    def get_selected_font_family(self):
        return self._selected_font_family

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None
