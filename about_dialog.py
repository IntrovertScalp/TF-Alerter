from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)
from PyQt6.QtCore import Qt, QUrl, QSettings
from PyQt6.QtGui import QDesktopServices, QFont
import config


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Переводы
        self.translations = {
            "RU": {
                "title": "О программе",
                "version": "Версия 1.0",
                "description": "Бесплатный таймер с оповещениями для трейдеров.\nУведомляет о закрытии свечей на выбранных таймфреймах\nс голосовыми оповещениями и визуальными часами.",
                "developer": "Разработчик:",
                "youtube_btn": "🎥 YouTube",
            },
            "EN": {
                "title": "About",
                "version": "Version 1.0",
                "description": "Free timer with alerts for traders.\nNotifies about candle closures on selected timeframes\nwith voice notifications and visual clocks.",
                "developer": "Developer:",
                "youtube_btn": "🎥 YouTube",
            },
        }

        settings = QSettings("MyTradeTools", "TF-Alerter")
        self.current_lang = settings.value("language", "RU")
        self.t = self.translations[self.current_lang]
        self.setWindowTitle(self.t["title"])
        scale_text = settings.value("interface_scale_text", "100%")
        try:
            value = int(str(scale_text).replace("%", ""))
            factor = value / 100.0
        except Exception:
            factor = 1.0

        def s(px):
            return max(1, int(px * factor))

        self.setFixedSize(s(420), s(360))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Главный контейнер
        main_container = QFrame(self)
        main_container.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLORS['background']};
                border: 2px solid {config.COLORS['border']};
                border-radius: 10px;
            }}
        """
        )
        main_container.setGeometry(0, 0, s(420), s(360))

        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(s(25), s(15), s(25), s(20))
        layout.setSpacing(s(15))

        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(s(28), s(28))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {config.COLORS['text']};
                border: none;
                font-size: {s(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: transparent;
                color: {config.COLORS['accent']};
            }}
        """
        )
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Заголовок с логотипом
        title_layout = QHBoxLayout()
        title_layout.setSpacing(s(10))
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        from PyQt6.QtGui import QPixmap

        logo_pix = QPixmap(config.LOGO_PATH).scaled(
            s(40),
            s(40),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        logo_label.setPixmap(logo_pix)
        logo_label.setStyleSheet("background: transparent; border: none;")
        title_layout.addWidget(logo_label)

        title = QLabel("TF-Alerter")
        title.setStyleSheet(
            f"""
            color: #1e90ff;
            font-size: {s(22)}px;
            font-weight: bold;
            border: none;
        """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_layout.addWidget(title)

        layout.addLayout(title_layout)

        # Версия
        version = QLabel(self.t["version"])
        version.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(11)}px; border: none;"
        )
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        layout.addSpacing(10)

        # Описание программы
        description = QLabel(self.t["description"])
        description.setStyleSheet(
            f"""
            color: {config.COLORS['text']};
            font-size: {s(12)}px;
            border: none;
            background: transparent;
        """
        )
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        layout.addSpacing(10)

        # Разработчик
        dev_label = QLabel(self.t["developer"])
        dev_label.setStyleSheet(
            f"color: #888; font-size: {s(11)}px; border: none; background: transparent;"
        )
        dev_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dev_label)

        dev_name = QLabel(config.AUTHOR_NAME)
        dev_name.setStyleSheet(
            f"""
            color: {config.COLORS['text']};
            font-size: {s(14)}px;
            font-weight: bold;
            border: none;
            background: transparent;
        """
        )
        dev_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dev_name)

        layout.addSpacing(5)

        # Кнопка YouTube
        youtube_btn = QPushButton(self.t["youtube_btn"])
        youtube_btn.setFixedHeight(s(38))
        youtube_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        youtube_btn.clicked.connect(self.open_youtube)
        youtube_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #FF0000;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px;
                font-size: {s(13)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #CC0000;
            }}
        """
        )
        layout.addWidget(youtube_btn)

        # Для перетаскивания
        self.old_pos = None

    def open_youtube(self):
        """Открывает YouTube канал в браузере"""
        QDesktopServices.openUrl(QUrl(config.YOUTUBE_URL))

    def mousePressEvent(self, event):
        """Начало перетаскивания окна"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Окончание перетаскивания"""
        self.old_pos = None
