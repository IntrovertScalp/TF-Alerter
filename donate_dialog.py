from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QWidget,
    QSlider,
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QPixmap, QImage, QCursor
import config
import io
import os

try:
    import qrcode
    from PIL import Image, ImageDraw, ImageFont

    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# Словарь с данными криптовалют (символ и цвет)
CRYPTO_ICONS = {
    "BTC": {"symbol": "₿", "color": "#F7931A"},
    "ETH": {"symbol": "Ξ", "color": "#627EEA"},
    "BNB": {"symbol": "B", "color": "#F3BA2F"},
    "USDT_TRC20": {"symbol": "₮", "color": "#26A17B"},
    "USDT_BEP20": {"symbol": "₮", "color": "#26A17B"},
    "USDT_ERC20": {"symbol": "₮", "color": "#26A17B"},
}


class ClickableQRLabel(QLabel):
    """QLabel с QR-кодом, который можно кликнуть для увеличения"""

    def __init__(
        self, pixmap, address, crypto_name, scale_factor, parent_dialog, parent=None
    ):
        super().__init__(parent)
        self.address = address
        self.crypto_name = crypto_name
        self.scale_factor = scale_factor
        self.parent_dialog = parent_dialog
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"""
            QLabel {{
                border: 2px solid {config.COLORS['border']};
                border-radius: 4px;
                padding: 4px;
                background: white;
            }}
            QLabel:hover {{
                border: 2px solid #1e90ff;
            }}
        """
        )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._show_enlarged_qr()

    def _show_enlarged_qr(self):
        """Показать увеличенный QR-код в диалоге с возможностью перетаскивания и масштабирования"""
        # Обновляем текущий язык на случай, если он изменился
        settings = QSettings("MyTradeTools", "TF-Alerter")
        current_lang = settings.value("language", "RU")
        t = self.parent_dialog.translations[current_lang]

        dialog = QDialog(self)
        dialog.setWindowTitle(t["qr_title"])
        dialog.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Переменные для перетаскивания
        dialog.old_pos = None

        # Переменные для масштабирования
        dialog.qr_size = self.parent_dialog._s(300)
        dialog.qr_min_size = self.parent_dialog._s(200)
        dialog.qr_max_size = self.parent_dialog._s(450)
        dialog.qr_step = self.parent_dialog._s(20)
        dialog.base_window_width = self.parent_dialog._s(480)
        dialog.base_window_height = self.parent_dialog._s(540)
        dialog.min_qr_for_window = self.parent_dialog._s(300)

        def update_window_size():
            """Обновить размер окна в зависимости от размера QR-кода"""
            # Если QR-код больше базового размера, увеличиваем окно пропорционально
            if dialog.qr_size > dialog.min_qr_for_window:
                diff = dialog.qr_size - dialog.min_qr_for_window
                new_width = dialog.base_window_width + diff
                new_height = dialog.base_window_height + diff
            else:
                new_width = dialog.base_window_width
                new_height = dialog.base_window_height

            dialog.resize(new_width, new_height)
            main_frame.setGeometry(0, 0, new_width, new_height)

        dialog.update_window_size = update_window_size

        # Начальный размер окна
        dialog.resize(dialog.base_window_width, dialog.base_window_height)

        # Главный контейнер
        main_frame = QFrame(dialog)
        main_frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLORS['background']};
                border: 2px solid {config.COLORS['border']};
                border-radius: 10px;
            }}
        """
        )
        main_frame.setGeometry(
            0, 0, dialog.base_window_width, dialog.base_window_height
        )

        layout = QVBoxLayout(main_frame)
        layout.setContentsMargins(
            self.parent_dialog._s(20),
            self.parent_dialog._s(10),
            self.parent_dialog._s(20),
            self.parent_dialog._s(20),
        )
        layout.setSpacing(self.parent_dialog._s(10))

        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        title = QLabel("QR-код для сканирования")
        title.setStyleSheet(
            f"color: #1e90ff; font-size: {self.parent_dialog._s(14)}px; font-weight: bold; border: none; background: transparent;"
        )
        title.setCursor(Qt.CursorShape.OpenHandCursor)
        header_layout.addWidget(title)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(self.parent_dialog._s(28), self.parent_dialog._s(28))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(dialog.close)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {config.COLORS['text']};
                border: none;
                font-size: {self.parent_dialog._s(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                color: #1e90ff;
            }}
        """
        )
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Большой QR-код с прокруткой
        qr_label = QLabel()
        qr_label.setObjectName("qr_label")
        qr_pixmap = self.parent_dialog._generate_large_qr(
            self.address, self.crypto_name
        )
        if qr_pixmap:
            # Масштабируем QR-код до нужного размера
            scaled_pixmap = qr_pixmap.scaledToWidth(
                dialog.qr_size, Qt.TransformationMode.FastTransformation
            )
            qr_label.setPixmap(scaled_pixmap)
            qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            qr_label.setStyleSheet(
                f"""
                QLabel {{
                    border: 2px solid {config.COLORS['border']};
                    border-radius: 8px;
                    padding: {self.parent_dialog._s(10)}px;
                    background: white;
                }}
            """
            )

        dialog.qr_label = qr_label
        dialog.qr_original_pixmap = qr_pixmap
        layout.addWidget(qr_label)

        # Ползунок управления размером
        controls_layout = QHBoxLayout()
        controls_layout.addSpacing(self.parent_dialog._s(10))

        size_label = QLabel("Размер:")
        size_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {self.parent_dialog._s(10)}px; border: none; background: transparent;"
        )
        controls_layout.addWidget(size_label)

        qr_slider = QSlider(Qt.Orientation.Horizontal)
        qr_slider.setMinimum(dialog.qr_min_size)
        qr_slider.setMaximum(dialog.qr_max_size)
        qr_slider.setValue(dialog.qr_size)
        qr_slider.setSingleStep(dialog.qr_step)
        qr_slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                background: #333;
                height: {self.parent_dialog._s(6)}px;
                border-radius: {self.parent_dialog._s(3)}px;
            }}
            QSlider::handle:horizontal {{
                background: #1565c0;
                border: 2px solid #0d47a1;
                width: {self.parent_dialog._s(14)}px;
                height: {self.parent_dialog._s(14)}px;
                margin: -{self.parent_dialog._s(4)}px 0;
                border-radius: {self.parent_dialog._s(7)}px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #0d47a1;
            }}
        """
        )

        def on_slider_value_changed(value):
            dialog.qr_size = value
            if qr_pixmap:
                scaled = qr_pixmap.scaledToWidth(
                    dialog.qr_size, Qt.TransformationMode.FastTransformation
                )
                qr_label.setPixmap(scaled)
                dialog.update_window_size()

        qr_slider.valueChanged.connect(on_slider_value_changed)
        controls_layout.addWidget(qr_slider)

        size_value_label = QLabel(str(dialog.qr_size))
        size_value_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {self.parent_dialog._s(10)}px; border: none; background: transparent; min-width: {self.parent_dialog._s(30)}px;"
        )
        controls_layout.addWidget(size_value_label)

        def update_size_label(value):
            size_value_label.setText(str(value))

        qr_slider.valueChanged.connect(update_size_label)
        controls_layout.addSpacing(self.parent_dialog._s(10))
        layout.addLayout(controls_layout)

        # Адрес
        address_label = QLabel(self.address)
        address_label.setStyleSheet(
            f"""
            color: {config.COLORS['text']};
            font-size: {self.parent_dialog._s(10)}px;
            border: 1px solid {config.COLORS['border']};
            border-radius: 4px;
            padding: {self.parent_dialog._s(8)}px;
            background: {config.COLORS['panel']};
        """
        )
        address_label.setWordWrap(True)
        address_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(address_label)

        # Кнопка закрытия
        close_dialog_btn = QPushButton("Закрыть")
        close_dialog_btn.setFixedHeight(self.parent_dialog._s(32))
        close_dialog_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_dialog_btn.clicked.connect(dialog.close)
        close_dialog_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 5px;
                padding: 5px 12px;
                font-size: {self.parent_dialog._s(11)}px;
            }}
            QPushButton:hover {{
                background-color: {config.COLORS['hover']};
            }}
        """
        )
        layout.addWidget(close_dialog_btn)

        # Переопределяем методы для перетаскивания
        original_mouse_press = dialog.mousePressEvent
        original_mouse_move = dialog.mouseMoveEvent
        original_mouse_release = dialog.mouseReleaseEvent

        def new_mouse_press(event):
            # Проверяем, нажали ли на заголовок или свободное место
            if event.pos().y() < self.parent_dialog._s(50):  # Высота заголовка
                dialog.old_pos = event.globalPosition().toPoint()
            else:
                original_mouse_press(event)

        def new_mouse_move(event):
            if dialog.old_pos:
                delta = event.globalPosition().toPoint() - dialog.old_pos
                dialog.move(dialog.x() + delta.x(), dialog.y() + delta.y())
                dialog.old_pos = event.globalPosition().toPoint()
            else:
                original_mouse_move(event)

        def new_mouse_release(event):
            dialog.old_pos = None
            original_mouse_release(event)

        dialog.mousePressEvent = new_mouse_press
        dialog.mouseMoveEvent = new_mouse_move
        dialog.mouseReleaseEvent = new_mouse_release

        dialog.exec()

    def _s(self, px):
        return max(1, int(px * self.scale_factor))


class DonateDialog(QDialog):
    # Кэш для QR-кодов (класс-уровень, общий для всех экземпляров)
    _qr_cache = {}
    _qr_cache_max_size = 10  # Максимум 10 QR-кодов в кэше

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # Переводы
        self.translations = {
            "RU": {
                "title": "Поддержать проект",
                "header": "♥️ Поддержать",
                "description": "Программа полностью бесплатная и всегда такой останется.\nЕсли она вам помогает — буду рад любой поддержке! 🤗",
                "scroll_hint": "⬇ Прокрутите вниз чтобы увидеть все адреса ⬇",
                "close": "Закрыть",
                "qr_title": "QR-код",
                "copy_btn": "📋 Копировать адрес",
            },
            "EN": {
                "title": "Support the project",
                "header": "♥️ Support",
                "description": "The program is completely free and will always stay that way.\nIf it helps you, I'd be grateful for any support! 🤗",
                "scroll_hint": "⬇ Scroll down to see all addresses ⬇",
                "close": "Close",
                "qr_title": "QR Code",
                "copy_btn": "📋 Copy Address",
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
        self._scale_factor = factor

        self.setFixedSize(self._s(580), self._s(600))
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
        main_container.setGeometry(0, 0, self._s(580), self._s(600))

        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(self._s(20), self._s(6), self._s(20), self._s(12))
        layout.setSpacing(self._s(8))

        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(self._s(28), self._s(28))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                color: {config.COLORS['text']};
                border: none;
                font-size: {self._s(16)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: transparent;
                color: #1e90ff;
            }}
        """
        )
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Заголовок
        title = QLabel(self.t["header"])
        title.setStyleSheet(
            f"""
            color: #1e90ff;
            font-size: {self._s(18)}px;
            font-weight: bold;
            border: none;
        """
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Описание
        desc = QLabel(self.t["description"])
        desc.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {self._s(11)}px; border: none; background: transparent;"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Скроллируемая область для адресов
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: {config.COLORS['panel']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.COLORS['border']};
                border-radius: 4px;
            }}
        """
        )

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(self._s(15))
        scroll_layout.setContentsMargins(self._s(5), self._s(5), self._s(5), self._s(5))

        # Добавляем адреса
        for crypto_name, crypto_data in config.CRYPTO_ADDRESSES.items():
            if crypto_data["address"]:  # Только если адрес указан
                frame = self._create_address_widget(crypto_name, crypto_data)
                scroll_layout.addWidget(frame)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Индикатор прокрутки
        scroll_hint = QLabel(self.t["scroll_hint"])
        scroll_hint.setStyleSheet(
            f"color: #888; font-size: {self._s(10)}px; border: none; background: transparent; font-style: italic;"
        )
        scroll_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(scroll_hint)

        # Кнопка закрытия
        close_btn = QPushButton(self.t["close"])
        close_btn.setFixedHeight(self._s(32))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 5px;
                padding: 5px 12px;
                font-size: {self._s(11)}px;
            }}
            QPushButton:hover {{
                background-color: {config.COLORS['hover']};
            }}
        """
        )
        layout.addWidget(close_btn)

        # Для перетаскивания
        self.old_pos = None

    def _s(self, px):
        return max(1, int(px * self._scale_factor))

    def _create_address_widget(self, name, data):
        """Создаёт виджет для одного криптоадреса"""
        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLORS['panel']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 8px;
                padding: {self._s(10)}px;
            }}
        """
        )

        layout = QVBoxLayout(frame)
        layout.setSpacing(self._s(8))
        layout.setContentsMargins(self._s(10), self._s(10), self._s(10), self._s(10))

        # Название криптовалюты
        title_layout = QHBoxLayout()
        crypto_label = QLabel(data["label"])
        crypto_label.setStyleSheet(
            f"color: #1e90ff; font-size: {self._s(13)}px; font-weight: bold; border: none; background: transparent;"
        )
        title_layout.addWidget(crypto_label)

        # Сеть (если есть)
        if data.get("network"):
            network_label = QLabel(f"({data['network']})")
            network_label.setStyleSheet(
                f"color: #888; font-size: {self._s(11)}px; border: none; background: transparent;"
            )
            title_layout.addWidget(network_label)

        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Контейнер для QR и адреса
        content_layout = QHBoxLayout()
        content_layout.setSpacing(self._s(10))

        # QR код
        if HAS_QRCODE:
            qr_pixmap = self._generate_qr(data["address"], name)
            if qr_pixmap:
                # Добавляем небольшой отступ слева
                content_layout.addSpacing(self._s(8))

                qr_label = ClickableQRLabel(
                    qr_pixmap, data["address"], name, self._scale_factor, self
                )
                qr_label.setPixmap(qr_pixmap)
                qr_label.setFixedSize(self._s(100), self._s(100))
                content_layout.addWidget(qr_label)

        # Адрес и кнопка
        addr_layout = QVBoxLayout()

        address_label = QLabel(data["address"])
        address_label.setStyleSheet(
            f"""
            color: {config.COLORS['text']};
            font-size: {self._s(12)}px;
            border: 1px solid {config.COLORS['border']};
            border-radius: 4px;
            padding: {self._s(6)}px;
            background: {config.COLORS['background']};
        """
        )
        address_label.setWordWrap(True)
        addr_layout.addWidget(address_label)

        # Кнопка копирования
        copy_btn = QPushButton(self.t["copy_btn"])
        copy_btn.setFixedHeight(self._s(32))
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(
            lambda: self._copy_address(data["address"], name, copy_btn)
        )
        copy_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: #1565c0;
                color: white;
                border: none;
                border-radius: 4px;
                padding: {self._s(6)}px;
                font-size: {self._s(11)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #0d47a1;
            }}
        """
        )
        addr_layout.addWidget(copy_btn)
        addr_layout.addSpacing(self._s(5))

        content_layout.addLayout(addr_layout, 1)

        # Добавляем небольшой отступ справа
        content_layout.addSpacing(self._s(8))

        layout.addLayout(content_layout)

        return frame

    def _generate_qr(self, data, crypto_name):
        """Генерирует QR-код с кэшированием"""
        if not HAS_QRCODE or not data:
            return None

        # Проверяем кэш
        cache_key = ("qr", data, self._s(100))
        if cache_key in DonateDialog._qr_cache:
            return DonateDialog._qr_cache[cache_key]

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=4,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            # Конвертируем PIL Image в QPixmap
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            qimage = QImage()
            qimage.loadFromData(buffer.read())
            buffer.close()  # Явно закрываем буфер

            pixmap = QPixmap.fromImage(qimage).scaled(
                self._s(100),
                self._s(100),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )

            # Очищаем кэш если он получился слишком большим
            if len(DonateDialog._qr_cache) >= DonateDialog._qr_cache_max_size:
                # Удаляем первый элемент (самый старый)
                first_key = next(iter(DonateDialog._qr_cache))
                del DonateDialog._qr_cache[first_key]

            # Сохраняем в кэш
            DonateDialog._qr_cache[cache_key] = pixmap
            return pixmap
        except Exception as e:
            print(f"Ошибка генерации QR-кода: {e}")
            return None

    def _generate_large_qr(self, data, crypto_name):
        """Генерирует большой QR-код с кэшированием"""
        if not HAS_QRCODE or not data:
            return None

        # Проверяем кэш
        cache_key = ("qr_large", data, self._s(300))
        if cache_key in DonateDialog._qr_cache:
            return DonateDialog._qr_cache[cache_key]

        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            qimage = QImage()
            qimage.loadFromData(buffer.read())
            buffer.close()  # Явно закрываем буфер

            pixmap = QPixmap.fromImage(qimage).scaled(
                self._s(300),
                self._s(300),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )

            # Очищаем кэш если он получился слишком большим
            if len(DonateDialog._qr_cache) >= DonateDialog._qr_cache_max_size:
                first_key = next(iter(DonateDialog._qr_cache))
                del DonateDialog._qr_cache[first_key]

            # Сохраняем в кэш
            DonateDialog._qr_cache[cache_key] = pixmap
            return pixmap
        except Exception as e:
            print(f"Ошибка генерации большого QR-кода: {e}")
            return None

    def _create_crypto_icon(self, crypto_name, size):
        """Создает иконку криптовалюты с символом"""
        try:
            # Получаем данные криптовалюты
            crypto_data = CRYPTO_ICONS.get(
                crypto_name, {"symbol": "?", "color": "#888"}
            )
            symbol = crypto_data["symbol"]
            color = crypto_data["color"]

            # Создаем круглое изображение
            icon = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(icon)

            # Рисуем круг
            draw.ellipse((0, 0, size, size), fill=color)

            # Добавляем символ (используем простой способ без шрифта)
            # Создаем текстовый слой
            text_layer = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            text_draw = ImageDraw.Draw(text_layer)

            # Используем шрифт по умолчанию, но большого размера
            font_size = int(size * 0.6)
            try:
                # Пытаемся загрузить нормальный шрифт
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("segoeui.ttf", font_size)
                except:
                    # Если не получилось - используем дефолтный
                    font = ImageFont.load_default()

            # Вычисляем позицию текста (центрируем)
            bbox = text_draw.textbbox((0, 0), symbol, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            position = (
                (size - text_width) // 2 - bbox[0],
                (size - text_height) // 2 - bbox[1],
            )

            # Рисуем белый текст
            text_draw.text(position, symbol, fill="white", font=font)

            # Объединяем слои
            icon = Image.alpha_composite(icon, text_layer)

            return icon
        except Exception as e:
            print(f"Ошибка создания иконки: {e}")
            # Возвращаем простой белый круг
            icon = Image.new("RGB", (size, size), "white")
            return icon

    def _add_logo_to_qr(self, qr_img, crypto_name, logo_size_ratio=0.2):
        """Добавляет логотип криптовалюты в центр QR-кода"""
        try:
            # Размер QR-кода
            qr_width, qr_height = qr_img.size

            # Вычисляем размер логотипа (20-25% от размера QR)
            logo_size = int(qr_width * logo_size_ratio)

            # Создаем иконку криптовалюты
            logo = self._create_crypto_icon(crypto_name, logo_size)

            # Создаем белый фон под логотип (для лучшей читаемости QR)
            logo_bg_size = int(logo_size * 1.15)
            logo_bg = Image.new("RGB", (logo_bg_size, logo_bg_size), "white")

            # Создаем круглую маску для фона
            mask = Image.new("L", (logo_bg_size, logo_bg_size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, logo_bg_size, logo_bg_size), fill=255)

            # Вычисляем позицию для вставки (центр QR-кода)
            logo_bg_pos = (
                (qr_width - logo_bg_size) // 2,
                (qr_height - logo_bg_size) // 2,
            )

            # Вставляем белый круглый фон
            qr_img.paste(logo_bg, logo_bg_pos, mask)

            # Вычисляем позицию для логотипа
            logo_pos = ((qr_width - logo.size[0]) // 2, (qr_height - logo.size[1]) // 2)

            # Вставляем логотип с прозрачностью если есть
            if logo.mode == "RGBA":
                qr_img.paste(logo, logo_pos, logo)
            else:
                qr_img.paste(logo, logo_pos)

            return qr_img
        except Exception as e:
            print(f"Ошибка добавления логотипа: {e}")
            return qr_img

    def _copy_address(self, address, crypto_name, copy_btn=None):
        """Копирует адрес в буфер обмена и показывает подтверждение"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer

        clipboard = QApplication.clipboard()
        clipboard.setText(address)

        # Если передана кнопка, меняем её внешний вид
        if copy_btn:
            original_text = copy_btn.text()
            original_stylesheet = copy_btn.styleSheet()

            # Меняем текст и стиль кнопки
            copy_btn.setText("✓ Скопировано!")
            copy_btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: #4caf50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: {self._s(6)}px;
                    font-size: {self._s(11)}px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: #45a049;
                }}
            """
            )

            # Возвращаем исходное состояние через 1.2 секунды
            def restore_button():
                copy_btn.setText(original_text)
                copy_btn.setStyleSheet(original_stylesheet)

            QTimer.singleShot(1200, restore_button)

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
