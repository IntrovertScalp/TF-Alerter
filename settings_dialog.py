from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QLineEdit,
    QGridLayout,
    QFileDialog,
    QSizePolicy,
    QWidget,
    QScrollArea,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QSettings, QEvent, QUrl, QRect
from PyQt6.QtGui import QKeySequence, QKeyEvent, QColor, QPainter, QPen
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import os
import shutil
import datetime
import config
import ctypes
from ctypes import wintypes


class SoundColumnCheckBox(QCheckBox):
    """Кастомный чекбокс для управления колонками звуков - стиль как на главном окне"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)

    def paintEvent(self, event):
        """Рисуем галочку как на главном окне для таймфреймов"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        indicator_rect_x = 2
        indicator_rect_y = 2
        indicator_rect = QRect(indicator_rect_x, indicator_rect_y, 16, 16)

        if self.isChecked():
            # Синий квадрат с белой галочкой
            painter.fillRect(indicator_rect, QColor("#1e90ff"))
            painter.setPen(QPen(QColor("#1e90ff"), 2))
            painter.drawRect(indicator_rect)

            # Рисуем галочку
            pen = QPen(QColor("black"), 2, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            x = indicator_rect_x
            y = indicator_rect_y
            painter.drawLine(int(x + 3), int(y + 9), int(x + 7), int(y + 13))
            painter.drawLine(int(x + 7), int(y + 13), int(x + 13), int(y + 5))
        else:
            # Пустой квадрат
            painter.setPen(QPen(QColor("#555"), 2))
            painter.drawRect(indicator_rect)

        painter.end()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Настройки")

        # Нужно для надёжного получения keyPress/keyRelease во время захвата
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Устанавливаем ширину шире родительского окна для блока звуков
        parent_width = parent.width() if parent else 380
        scale_text = QSettings("MyTradeTools", "TF-Alerter").value(
            "interface_scale_text", "100%"
        )
        try:
            value = int(str(scale_text).replace("%", ""))
            factor = value / 100.0
        except Exception:
            factor = 1.0

        # Сохраняем масштаб как переменная класса для использования в других методах
        self.scale_factor = factor

        def s(px):
            return max(1, int(px * factor))

        dialog_width = max(parent_width + s(140), s(700))
        self.setFixedSize(dialog_width, s(560))

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.capturing_hotkey = False
        self.captured_hotkey_codes = None
        self._pressed_vks = set()
        self._pressed_names = {}
        self._saw_non_modifier = False
        self._last_modifiers_vks = set()
        self.funding_sound_file = ""

        self._user32 = ctypes.windll.user32
        self._MAPVK_VK_TO_VSC_EX = 4
        self._VK_MODIFIERS = {
            0x10,  # VK_SHIFT
            0x11,  # VK_CONTROL
            0x12,  # VK_MENU (Alt)
            0x5B,  # VK_LWIN
            0x5C,  # VK_RWIN
            0xA0,  # VK_LSHIFT
            0xA1,  # VK_RSHIFT
            0xA2,  # VK_LCONTROL
            0xA3,  # VK_RCONTROL
            0xA4,  # VK_LMENU
            0xA5,  # VK_RMENU
        }

        self._VK_DISPLAY = {
            0xA2: "Left Ctrl",
            0xA3: "Right Ctrl",
            0x11: "Ctrl",
            0xA4: "Left Alt",
            0xA5: "Right Alt",
            0x12: "Alt",
            0xA0: "Left Shift",
            0xA1: "Right Shift",
            0x10: "Shift",
            0x5B: "Left Windows",
            0x5C: "Right Windows",
        }

        # Словари переводов
        self.translations = {
            "RU": {
                "title": "Настройки",
                "language": "Язык:",
                "scale": "Масштаб:",
                "hotkey": "Горячая клавиша (свернуть/развернуть):",
                "clear": "Очистить",
                "cancel": "Отмена",
                "save": "Сохранить",
                "not_set": "Не задана",
                "capturing": "Нажмите клавишу...",
                "sounds_title": "Звуки таймфреймов",
                "tf_col": "ТФ",
                "voice_col": "Основной",
                "tick_col": "Тики 5с",
                "transition_col": "Переход",
                "enable_voice": "Включить",
                "enable_tick": "Включить",
                "enable_transition": "Включить",
                "about_btn": "ℹ️ О программе",
                "donate_btn": "♥️ Поддержать",
                "funding_title": "Фандинг: звук и голос",
                "funding_sound_enabled": "Включить звук фандинга",
                "funding_tts_enabled": "Включить голос (TTS)",
                "funding_sound_file": "Звук фандинга:",
                "funding_sound_pick": "Выбрать звук",
                "funding_tts_voice": "Голос TTS:",
            },
            "EN": {
                "title": "Settings",
                "language": "Language:",
                "scale": "Scale:",
                "hotkey": "Hotkey (minimize/restore):",
                "clear": "Clear",
                "cancel": "Cancel",
                "save": "Save",
                "not_set": "Not set",
                "capturing": "Press a key...",
                "sounds_title": "Timeframe Sounds",
                "tf_col": "TF",
                "voice_col": "Voice",
                "tick_col": "Ticks 5s",
                "transition_col": "Transition",
                "enable_voice": "Enable",
                "enable_tick": "Enable",
                "enable_transition": "Enable",
                "about_btn": "ℹ️ About the Program",
                "donate_btn": "♥️ Support",
                "funding_title": "Funding: sound and voice",
                "funding_sound_enabled": "Enable funding sound",
                "funding_tts_enabled": "Enable voice (TTS)",
                "funding_sound_file": "Funding sound:",
                "funding_sound_pick": "Pick sound",
                "funding_tts_voice": "TTS Voice:",
            },
        }

        # Главный контейнер
        main_container = QFrame(self)
        main_container.setStyleSheet(
            f"""
            QFrame {{
                background-color: {config.COLORS['background']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 10px;
            }}
        """
        )
        main_container.setGeometry(0, 0, dialog_width, s(560))

        layout = QVBoxLayout(main_container)
        layout.setContentsMargins(s(20), s(12), s(20), s(15))
        layout.setSpacing(s(12))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Заголовок с кнопкой закрытия
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self.title = QLabel("Настройки")
        self.title.setStyleSheet(
            f"""
            color: {config.COLORS['text']};
            font-size: {s(14)}px;
            font-weight: bold;
            border: none;
            background: transparent;
        """
        )
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.title)
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
                color: #1e90ff;
            }}
        """
        )
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # Кнопки для информации и донатов
        info_layout = QHBoxLayout()
        self.about_btn = QPushButton(self.translations["RU"]["about_btn"])
        self.about_btn.setMaximumWidth(s(150))
        self.about_btn.clicked.connect(self._open_about)
        self.about_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                padding: {s(8)}px {s(20)}px;
                font-size: {s(11)}px;
            }}
            QPushButton:hover {{
                background-color: {config.COLORS['hover']};
                border: 1px solid #1e90ff;
            }}
        """
        )

        self.donate_btn = QPushButton(self.translations["RU"]["donate_btn"])
        self.donate_btn.setMaximumWidth(s(150))
        self.donate_btn.clicked.connect(self._open_donate)
        self.donate_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                padding: {s(8)}px {s(20)}px;
                font-size: {s(11)}px;
            }}
            QPushButton:hover {{
                background-color: {config.COLORS['hover']};
                border: 1px solid #1e90ff;
            }}
        """
        )

        info_layout.addStretch()
        info_layout.addWidget(self.about_btn)
        info_layout.addSpacing(5)
        info_layout.addWidget(self.donate_btn)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Язык
        lang_layout = QHBoxLayout()
        lang_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lang_label = QLabel("Язык:")
        self.lang_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(12)}px; border: none; background: transparent;"
        )
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["RU", "EN"])
        self.lang_combo.setStyleSheet(self._combo_style())
        if self.lang_combo.lineEdit():
            self.lang_combo.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lang_combo.currentTextChanged.connect(self.change_dialog_language)
        lang_layout.addWidget(self.lang_label)
        lang_layout.addSpacing(10)
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        # Масштаб интерфейса
        scale_layout = QHBoxLayout()
        scale_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scale_label = QLabel("Масштаб:")
        self.scale_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(12)}px; border: none; background: transparent;"
        )
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(
            ["80%", "90%", "100%", "110%", "120%", "130%", "140%", "150%"]
        )
        self.scale_combo.setStyleSheet(self._combo_style())
        if self.scale_combo.lineEdit():
            self.scale_combo.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)
        scale_layout.addWidget(self.scale_label)
        scale_layout.addSpacing(10)
        scale_layout.addWidget(self.scale_combo)
        layout.addLayout(scale_layout)

        # Горячая клавиша
        self.hotkey_label = QLabel("Горячая клавиша (свернуть/развернуть):")
        self.hotkey_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(12)}px; border: none; background: transparent;"
        )
        self.hotkey_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hotkey_label)

        hotkey_input_layout = QHBoxLayout()
        hotkey_input_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hotkey_input = QPushButton("Не задана")
        # Чтобы фокус не оставался на кнопке и не "съедал" события клавиатуры
        self.hotkey_input.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hotkey_input.setFixedHeight(s(32))
        self.hotkey_input.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hotkey_input.clicked.connect(self.start_capture)
        self.hotkey_input.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                padding: {s(8)}px;
                font-size: {s(11)}px;
                text-align: left;
            }}
            QPushButton:hover {{
                border: 1px solid #1e90ff;
            }}
        """
        )

        self.clear_hotkey_btn = QPushButton("Очистить")
        self.clear_hotkey_btn.setFixedHeight(s(32))
        self.clear_hotkey_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_hotkey_btn.clicked.connect(self.clear_hotkey)
        self.clear_hotkey_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                padding: {s(5)}px {s(12)}px;
                font-size: {s(11)}px;
            }}
            QPushButton:hover {{
                border: 1px solid #1e90ff;
            }}
        """
        )

        hotkey_input_layout.addWidget(self.hotkey_input)
        hotkey_input_layout.addWidget(self.clear_hotkey_btn)
        layout.addLayout(hotkey_input_layout)

        # Настройки фандинга (звук и голос)
        layout.addSpacing(s(8))

        self.funding_title = QLabel(self.translations["RU"]["funding_title"])
        self.funding_title.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(12)}px; font-weight: bold; border: none; background: transparent;"
        )
        self.funding_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.funding_title)

        funding_frame = QFrame()
        funding_frame.setStyleSheet(
            f"QFrame {{ background-color: {config.COLORS['panel']}; border: 1px solid {config.COLORS['border']}; border-radius: {s(6)}px; }}"
        )
        funding_layout = QVBoxLayout(funding_frame)
        funding_layout.setContentsMargins(s(10), s(8), s(10), s(8))
        funding_layout.setSpacing(s(6))

        funding_check_row = QHBoxLayout()
        self.funding_sound_check = QCheckBox(
            self.translations["RU"]["funding_sound_enabled"]
        )
        self.funding_tts_check = QCheckBox(
            self.translations["RU"]["funding_tts_enabled"]
        )
        for cb in (self.funding_sound_check, self.funding_tts_check):
            cb.setStyleSheet(
                f"color: {config.COLORS['text']}; font-size: {s(11)}px; border: none; background: transparent;"
            )
        funding_check_row.addWidget(self.funding_sound_check)
        funding_check_row.addWidget(self.funding_tts_check)
        funding_check_row.addStretch()
        funding_layout.addLayout(funding_check_row)

        sound_row = QHBoxLayout()
        self.funding_sound_label = QLabel(self.translations["RU"]["funding_sound_file"])
        self.funding_sound_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(11)}px; border: none; background: transparent;"
        )
        self.funding_sound_value = QLabel("-")
        self.funding_sound_value.setStyleSheet(
            f"color: {config.COLORS['border']}; font-size: {s(10)}px; border: none; background: transparent;"
        )
        self.funding_sound_btn = QPushButton(
            self.translations["RU"]["funding_sound_pick"]
        )
        self.funding_sound_btn.setFixedHeight(s(30))
        self.funding_sound_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.funding_sound_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['background']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                padding: {s(4)}px {s(10)}px;
                font-size: {s(10)}px;
            }}
            QPushButton:hover {{
                border: 1px solid #1e90ff;
            }}
            """
        )
        self.funding_sound_play_btn = QPushButton("▶")
        self.funding_sound_play_btn.setFixedSize(s(28), s(30))
        self.funding_sound_play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.funding_sound_play_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {config.COLORS['background']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: {s(5)}px;
                font-size: {s(11)}px;
            }}
            QPushButton:hover {{
                border: 1px solid #1e90ff;
            }}
            """
        )
        self.funding_sound_btn.clicked.connect(self._select_funding_sound)
        self.funding_sound_play_btn.clicked.connect(self._play_funding_sound)
        sound_row.addWidget(self.funding_sound_label)
        sound_row.addWidget(self.funding_sound_value, 1)
        sound_row.addWidget(self.funding_sound_btn)
        sound_row.addWidget(self.funding_sound_play_btn)
        funding_layout.addLayout(sound_row)

        voice_row = QHBoxLayout()
        self.funding_tts_voice_label = QLabel(
            self.translations["RU"]["funding_tts_voice"]
        )
        self.funding_tts_voice_label.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(11)}px; border: none; background: transparent;"
        )
        self.funding_tts_voice_combo = QComboBox()
        self.funding_tts_voice_combo.setStyleSheet(self._combo_style())
        if self.funding_tts_voice_combo.lineEdit():
            self.funding_tts_voice_combo.lineEdit().setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )
        voice_row.addWidget(self.funding_tts_voice_label)
        voice_row.addWidget(self.funding_tts_voice_combo)
        funding_layout.addLayout(voice_row)

        layout.addWidget(funding_frame)

        layout.addSpacing(s(15))

        # Preview player for sounds
        self.preview_player = QMediaPlayer()
        self.preview_output = QAudioOutput()
        self.preview_player.setAudioOutput(self.preview_output)
        # Set default device for preview output
        from PyQt6.QtMultimedia import QMediaDevices

        try:
            default_device = QMediaDevices.defaultAudioOutput()
            self.preview_output.setDevice(default_device)
        except Exception:
            pass

        # Настройки звуков
        self.sounds_title = QLabel(self.translations["RU"]["sounds_title"])
        self.sounds_title.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(12)}px; font-weight: bold; border: none; background: transparent;"
        )
        self.sounds_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.sounds_title)

        sounds_container = QWidget()
        sounds_layout = QVBoxLayout(sounds_container)
        sounds_layout.setContentsMargins(s(8), 0, s(8), 0)
        sounds_layout.setSpacing(s(4))

        sounds_scroll = QScrollArea()
        sounds_scroll.setWidgetResizable(True)
        sounds_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sounds_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        sounds_scroll.setViewportMargins(s(8), 0, s(8), 0)
        sounds_scroll.setStyleSheet("QScrollArea { background: transparent; }")
        sounds_scroll.setWidget(sounds_container)

        self.sound_buttons = {}
        # Списки всех кнопок (выбора и проигрывания) для каждого типа звука
        self.buttons_main = []  # Основной звук (выбор + проигрывание)
        self.buttons_tick = []  # Звуки тиков (выбор + проигрывание)
        self.buttons_transition = []  # Звуки переходов (выбор + проигрывание)
        self.tf_labels = {}

        # Инициализируем settings для использования на всей этой странице
        settings = QSettings("MyTradeTools", "TF-Alerter")

        def make_btn(text):
            btn = QPushButton(text)
            btn.setFixedSize(s(130), s(32))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {config.COLORS['background']};
                    color: {config.COLORS['text']};
                    border: 1px solid {config.COLORS['border']};
                    border-radius: {s(5)}px;
                    padding: {s(4)}px {s(12)}px;
                    font-size: {s(10)}px;
                }}
                QPushButton:hover {{
                    border: 1px solid #1e90ff;
                }}
                """
            )
            return btn

        def make_play_btn():
            btn = QPushButton("▶")
            btn.setFixedSize(s(24), s(32))  # Уменьшенная ширина для экономии места
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {config.COLORS['background']};
                    color: {config.COLORS['text']};
                    border: 1px solid {config.COLORS['border']};
                    border-radius: {s(5)}px;
                    font-size: {s(11)}px;
                }}
                QPushButton:hover {{
                    border: 1px solid #1e90ff;
                }}
                """
            )
            return btn

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(s(10), 0, s(10), 0)
        header_layout.setSpacing(s(4))

        self.header_tf = QLabel(self.translations["RU"]["tf_col"])
        self.header_tf.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: {s(10)}px; font-weight: bold; border: none; background: transparent;"
        )
        self.header_tf.setFixedWidth(s(56))
        self.header_tf.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.header_tf)
        header_layout.addSpacing(s(8))

        def make_header(text):
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {config.COLORS['text']}; font-size: {s(10)}px; font-weight: bold; border: none; background: transparent;"
            )
            lbl.setFixedWidth(s(130))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return lbl

        # Создим контейнеры для каждой колонки с заголовком и чекбоксом
        self.check_voice_enabled = SoundColumnCheckBox()
        self.check_voice_enabled.setChecked(
            settings.value("sounds_voice_enabled", True, type=bool)
        )
        voice_container = QWidget()
        voice_layout = QVBoxLayout(voice_container)
        voice_layout.setContentsMargins(0, 0, 0, 0)
        voice_layout.setSpacing(s(2))
        self.header_voice = make_header(self.translations["RU"]["voice_col"])
        voice_layout.addWidget(
            self.header_voice, alignment=Qt.AlignmentFlag.AlignCenter
        )
        voice_layout.addWidget(
            self.check_voice_enabled, alignment=Qt.AlignmentFlag.AlignCenter
        )
        voice_container.setFixedWidth(s(150))

        self.check_tick_enabled = SoundColumnCheckBox()
        self.check_tick_enabled.setChecked(
            settings.value("sounds_tick_enabled", True, type=bool)
        )
        tick_container = QWidget()
        tick_layout = QVBoxLayout(tick_container)
        tick_layout.setContentsMargins(0, 0, 0, 0)
        tick_layout.setSpacing(s(2))
        self.header_tick = make_header(self.translations["RU"]["tick_col"])
        tick_layout.addWidget(self.header_tick, alignment=Qt.AlignmentFlag.AlignCenter)
        tick_layout.addWidget(
            self.check_tick_enabled, alignment=Qt.AlignmentFlag.AlignCenter
        )
        tick_container.setFixedWidth(s(150))

        self.check_transition_enabled = SoundColumnCheckBox()
        self.check_transition_enabled.setChecked(
            settings.value("sounds_transition_enabled", True, type=bool)
        )
        transition_container = QWidget()
        transition_layout = QVBoxLayout(transition_container)
        transition_layout.setContentsMargins(0, 0, 0, 0)
        transition_layout.setSpacing(s(2))
        self.header_transition = make_header(self.translations["RU"]["transition_col"])
        transition_layout.addWidget(
            self.header_transition, alignment=Qt.AlignmentFlag.AlignCenter
        )
        transition_layout.addWidget(
            self.check_transition_enabled, alignment=Qt.AlignmentFlag.AlignCenter
        )
        transition_container.setFixedWidth(s(150))

        header_layout.addWidget(voice_container)
        header_layout.addSpacing(s(4))
        header_layout.addSpacing(s(28))
        header_layout.addWidget(tick_container)
        header_layout.addSpacing(s(4))
        header_layout.addSpacing(s(28))
        header_layout.addWidget(transition_container)
        header_layout.addSpacing(s(4))
        header_layout.addSpacing(s(28))

        # Подключаем события для изменения стиля при отключении
        self.check_voice_enabled.stateChanged.connect(
            lambda: self._update_sound_column_style(
                "main", self.check_voice_enabled, self.header_voice
            )
        )
        self.check_tick_enabled.stateChanged.connect(
            lambda: self._update_sound_column_style(
                "tick", self.check_tick_enabled, self.header_tick
            )
        )
        self.check_transition_enabled.stateChanged.connect(
            lambda: self._update_sound_column_style(
                "transition", self.check_transition_enabled, self.header_transition
            )
        )

        # Инициальное обновление стилей
        self._update_sound_column_style(
            "main", self.check_voice_enabled, self.header_voice
        )
        self._update_sound_column_style(
            "tick", self.check_tick_enabled, self.header_tick
        )
        self._update_sound_column_style(
            "transition", self.check_transition_enabled, self.header_transition
        )

        sounds_layout.addWidget(header_row)

        for tf_key, data in config.TIMEFRAMES.items():
            # Создаем карточку для каждого таймфрейма
            tf_card = QFrame()
            tf_card.setStyleSheet(
                f"QFrame {{ background-color: {config.COLORS['panel']}; border: 1px solid {config.COLORS['border']}; border-radius: {s(6)}px; }}"
            )
            tf_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            tf_card.setFixedHeight(s(44))
            card_layout = QHBoxLayout(tf_card)
            card_layout.setContentsMargins(
                s(10), s(6), s(20), s(6)
            )  # Увеличенный правый margin для свободы
            card_layout.setSpacing(s(2))  # Уменьшенный spacing между элементами

            # Метка таймфрейма
            saved_lang = settings.value("language", "RU")
            tf_label = QLabel(config.get_timeframe_label(tf_key, saved_lang))
            tf_label.setStyleSheet(
                f"color: {config.COLORS['text']}; font-size: {s(11)}px; font-weight: bold; border: none; background: transparent;"
            )
            tf_label.setFixedWidth(s(56))
            tf_label.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            )
            card_layout.addWidget(tf_label)
            self.tf_labels[tf_key] = tf_label

            # Разделитель
            card_layout.addSpacing(s(4))  # Spacing перед первой group

            # Основной звук
            main_name = os.path.basename(data["file"])
            main_btn = make_btn(main_name)
            main_btn.setMinimumWidth(s(130))
            card_layout.addWidget(main_btn, 1)

            play_main_btn = make_play_btn()
            card_layout.addWidget(play_main_btn)

            # Разделитель
            card_layout.addSpacing(s(2))  # Уменьшенный spacing между группами

            # Звук тиков
            tick_name = os.path.basename(config.SOUND_TICK_BY_TF.get(tf_key, ""))
            tick_btn = make_btn(tick_name)
            tick_btn.setMinimumWidth(s(130))
            card_layout.addWidget(tick_btn, 1)

            play_tick_btn = make_play_btn()
            card_layout.addWidget(play_tick_btn)

            # Разделитель
            card_layout.addSpacing(s(2))  # Уменьшенный spacing между группами

            # Звук перехода
            transition_name = os.path.basename(
                config.SOUND_TRANSITION_BY_TF.get(tf_key, "")
            )
            transition_btn = make_btn(transition_name)
            transition_btn.setMinimumWidth(s(130))
            card_layout.addWidget(transition_btn, 1)

            play_transition_btn = make_play_btn()
            card_layout.addWidget(play_transition_btn)

            # Подключаем события
            main_btn.clicked.connect(
                lambda _=False, k=tf_key: self._select_sound(k, "main")
            )
            tick_btn.clicked.connect(
                lambda _=False, k=tf_key: self._select_sound(k, "tick")
            )
            transition_btn.clicked.connect(
                lambda _=False, k=tf_key: self._select_sound(k, "transition")
            )
            play_main_btn.clicked.connect(
                lambda _=False, k=tf_key: self._play_sound(k, "main")
            )
            play_tick_btn.clicked.connect(
                lambda _=False, k=tf_key: self._play_sound(k, "tick")
            )
            play_transition_btn.clicked.connect(
                lambda _=False, k=tf_key: self._play_sound(k, "transition")
            )

            # Сохраняем кнопки
            self.sound_buttons[(tf_key, "main")] = main_btn
            self.sound_buttons[(tf_key, "tick")] = tick_btn
            self.sound_buttons[(tf_key, "transition")] = transition_btn

            # Сохраняем все кнопки по типам звука для управления стилями
            self.buttons_main.append((main_btn, play_main_btn))
            self.buttons_tick.append((tick_btn, play_tick_btn))
            self.buttons_transition.append((transition_btn, play_transition_btn))

            sounds_layout.addWidget(tf_card)

        layout.addWidget(sounds_scroll)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setFixedHeight(s(32))
        self.cancel_btn.setFixedWidth(s(100))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet(
            """
            QPushButton {
                color: #ff3b30;
                border: 2px solid #ff3b30;
                border-radius: 10px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background: #ff3b30;
                color: black;
            }
        """
        )

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFixedHeight(s(32))
        self.save_btn.setFixedWidth(s(100))
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self.save_and_close)
        self.save_btn.setStyleSheet(
            """
            QPushButton {
                color: #1e90ff;
                border: 2px solid #1e90ff;
                border-radius: 10px;
                font-weight: bold;
                padding: 5px;
            }
            QPushButton:hover {
                background: #1e90ff;
                color: black;
            }
        """
        )

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addSpacing(5)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Загрузка текущих настроек
        self.load_current_settings()

        # Для перетаскивания
        self.old_pos = None

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 80px;
            }}
            QComboBox:hover {{
                border: 1px solid #1e90ff;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {config.COLORS['panel']};
                color: {config.COLORS['text']};
                selection-background-color: #1e90ff;
                border: 1px solid {config.COLORS['border']};
            }}
        """

    def _update_sound_column_style(self, kind, checkbox, header_label):
        """Обновляет стиль всей колонки звуков (заголовок и все кнопки)"""
        scaled_px = max(1, int(10 * self.scale_factor))

        is_enabled = checkbox.isChecked()

        # Определяем цвет для заголовка
        if is_enabled:
            header_color = config.COLORS["text"]
            button_opacity = 1.0
            button_border_color = config.COLORS["border"]
        else:
            header_color = config.COLORS["border"]
            button_opacity = 0.5
            button_border_color = "#555555"  # Еще более темный бордер

        # Обновляем стиль заголовка
        header_label.setStyleSheet(
            f"color: {header_color}; font-size: {scaled_px}px; font-weight: bold; border: none; background: transparent;"
        )

        # Получаем список кнопок для этого типа звука
        if kind == "main":
            buttons = self.buttons_main
        elif kind == "tick":
            buttons = self.buttons_tick
        elif kind == "transition":
            buttons = self.buttons_transition
        else:
            buttons = []

        # Обновляем стиль и состояние всех кнопок в колонке
        for select_btn, play_btn in buttons:
            # Обновляем стиль кнопки выбора
            select_btn.setEnabled(is_enabled)
            if is_enabled:
                select_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {config.COLORS['background']};
                        color: {config.COLORS['text']};
                        border: 1px solid {config.COLORS['border']};
                        border-radius: {max(1, int(5 * self.scale_factor))}px;
                        padding: {max(1, int(4 * self.scale_factor))}px {max(1, int(12 * self.scale_factor))}px;
                        font-size: {max(1, int(10 * self.scale_factor))}px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #1e90ff;
                    }}
                    """
                )
            else:
                select_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: #0a0a0a;
                        color: #555555;
                        border: 1px solid #555555;
                        border-radius: {max(1, int(5 * self.scale_factor))}px;
                        padding: {max(1, int(4 * self.scale_factor))}px {max(1, int(12 * self.scale_factor))}px;
                        font-size: {max(1, int(10 * self.scale_factor))}px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #555555;
                    }}
                    """
                )

            # Обновляем стиль кнопки проигрывания
            play_btn.setEnabled(is_enabled)
            if is_enabled:
                play_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {config.COLORS['background']};
                        color: {config.COLORS['text']};
                        border: 1px solid {config.COLORS['border']};
                        border-radius: {max(1, int(5 * self.scale_factor))}px;
                        font-size: {max(1, int(11 * self.scale_factor))}px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #1e90ff;
                    }}
                    """
                )
            else:
                play_btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: #0a0a0a;
                        color: #555555;
                        border: 1px solid #555555;
                        border-radius: {max(1, int(5 * self.scale_factor))}px;
                        font-size: {max(1, int(11 * self.scale_factor))}px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid #555555;
                    }}
                    """
                )

    def _update_header_style(self, header_label, checkbox):
        """Обновляет стиль заголовка колонки (затемняет если отключена)"""
        scaled_px = max(1, int(10 * self.scale_factor))
        if checkbox.isChecked():
            # Включена - нормальный цвет
            color = config.COLORS["text"]
        else:
            # Отключена - затемненный цвет
            color = config.COLORS["border"]

        header_label.setStyleSheet(
            f"color: {color}; font-size: {scaled_px}px; font-weight: bold; border: none; background: transparent;"
        )

    def _select_sound(self, tf_key, kind):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать звук",
            "",
            "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)",
        )
        if not file_path:
            return

        ext = os.path.splitext(file_path)[1].lower() or ".wav"

        # Формируем имя файла в зависимости от типа
        # Для 1M (месяца) используем префикс 1Mo
        file_prefix = "1Mo" if tf_key == "1M" else tf_key

        if kind == "main":
            target_name = f"{file_prefix}_voice{ext}"
        elif kind == "tick":
            target_name = f"{file_prefix}_tick{ext}"
        else:  # transition
            target_name = f"{file_prefix}_transition{ext}"

        target_dir = config.get_sound_dir(kind)
        target_path = os.path.join(target_dir, target_name)
        os.makedirs(target_dir, exist_ok=True)

        # Копируем новый звук, заменяя старый
        try:
            shutil.copy2(file_path, target_path)
        except Exception:
            return

        settings = QSettings("MyTradeTools", "TF-Alerter")

        # КРИТИЧНО: Используем разные имена для 1m и 1M в QSettings
        # Потому что Windows реестр case-insensitive и 1m/1M конфликтуют
        # Для 1M используем 1Month чтобы избежать конфликта
        qsettings_key = tf_key.replace("1M", "1Month") if tf_key == "1M" else tf_key

        if kind == "main":
            config.TIMEFRAMES[tf_key]["file"] = target_name
            key_name = f"sound_main_{qsettings_key}"
            settings.setValue(key_name, target_name)
        elif kind == "tick":
            config.SOUND_TICK_BY_TF[tf_key] = target_name
            key_name = f"sound_tick_{qsettings_key}"
            settings.setValue(key_name, target_name)
        elif kind == "transition":
            config.SOUND_TRANSITION_BY_TF[tf_key] = target_name
            key_name = f"sound_transition_{qsettings_key}"
            settings.setValue(key_name, target_name)

        settings.sync()

        # ВАЖНО: Обновляем кнопки ТОЛЬКО для текущего таймфрейма и вида
        btn = self.sound_buttons.get((tf_key, kind))
        if btn:
            btn.setText(os.path.basename(target_name))

    def _load_tts_voices(self):
        try:
            import pyttsx3

            engine = pyttsx3.init()
            voices = engine.getProperty("voices") or []
            self.funding_tts_voice_combo.clear()
            self.funding_tts_voice_combo.addItem("Default", "")
            for voice in voices:
                name = getattr(voice, "name", None) or "Voice"
                vid = getattr(voice, "id", "")
                langs = "".join(
                    [str(lang).lower() for lang in getattr(voice, "languages", [])]
                )
                is_ru = "ru" in langs or "russian" in name.lower()
                is_en = "en" in langs or "english" in name.lower()
                if is_ru:
                    label = f"[RU] {name}"
                elif is_en:
                    label = f"[EN] {name}"
                else:
                    label = f"[Other] {name}"
                self.funding_tts_voice_combo.addItem(label, vid)
            if self.funding_tts_voice_combo.count() == 1:
                for voice in voices:
                    name = getattr(voice, "name", "Voice")
                    vid = getattr(voice, "id", "")
                    self.funding_tts_voice_combo.addItem(name, vid)
        except Exception:
            self.funding_tts_voice_combo.clear()
            self.funding_tts_voice_combo.addItem("Default", "")

    def _select_funding_sound(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translations[self.lang_combo.currentText()]["funding_sound_pick"],
            "",
            "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)",
        )
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower() or ".wav"
        target_name = f"funding_alert{ext}"
        target_dir = config.get_sound_dir("transition")
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, target_name)
        try:
            shutil.copy2(file_path, target_path)
        except Exception:
            return
        settings = QSettings("MyTradeTools", "TF-Alerter")
        settings.setValue("funding_sound_file", target_name)
        settings.sync()
        self.funding_sound_file = target_name
        self.funding_sound_value.setText(os.path.basename(target_name))

    def _play_funding_sound(self):
        settings = QSettings("MyTradeTools", "TF-Alerter")
        filename = settings.value("funding_sound_file", "")
        if not filename:
            return
        path = config.get_sound_path("transition", filename)
        if not path or not os.path.exists(path):
            return
        self.preview_player.stop()
        self.preview_player.setSource(QUrl())
        self.preview_player.setSource(QUrl.fromLocalFile(path))
        self.preview_output.setVolume(1.0)
        self.preview_player.play()

    def _play_sound(self, tf_key, kind):
        if kind == "main":
            filename = config.TIMEFRAMES.get(tf_key, {}).get("file", "")
        elif kind == "tick":
            filename = config.SOUND_TICK_BY_TF.get(tf_key, "")
        else:
            filename = config.SOUND_TRANSITION_BY_TF.get(tf_key, "")

        if not filename:
            print(f"⚠️ Нет названия файла для {kind}")
            return

        path = config.get_sound_path(kind, filename)
        if not path or not os.path.exists(path):
            print(f"⚠️ Файл не существует: {path}")
            return

        # Чистая громкость: 100% максимум (1.0) - без треска и искажений
        # Значения выше 1.0 вызывают цифровое клиппирование
        target_volume = 1.0
        self.preview_output.setVolume(target_volume)
        print(f"🔊 Воспроизведение {kind}: {filename}")
        print(f"   Громкость установлена: {target_volume * 100:.0f}%")
        print(f"   Путь: {path}")

        # Полностью останавливаем и очищаем предыдущий звук
        self.preview_player.stop()
        self.preview_player.setSource(QUrl())  # Очищаем источник

        # Устанавливаем новый звук и проигрываем
        self.preview_player.setSource(QUrl.fromLocalFile(path))
        self.preview_player.play()

    def load_current_settings(self):
        """Загружает текущие настройки"""
        settings = QSettings("MyTradeTools", "TF-Alerter")

        # Язык
        saved_lang = settings.value("language", "RU")
        self.lang_combo.setCurrentText(saved_lang)

        # Масштаб
        saved_scale = settings.value("interface_scale_text", "100%")
        self.scale_combo.setCurrentText(saved_scale)

        # Горячая клавиша
        saved_hotkey = settings.value("hotkey", "")
        saved_codes = settings.value("hotkey_codes", "")
        if saved_codes:
            try:
                self.captured_hotkey_codes = [
                    int(x) for x in str(saved_codes).split(",") if x.strip().isdigit()
                ]
            except Exception:
                self.captured_hotkey_codes = None
        else:
            self.captured_hotkey_codes = None
        # Игнорируем placeholder текст
        invalid_texts = [
            "Не задана",
            "Нажмите клавишу...",
            "Not set",
            "Press a key...",
            "",
        ]
        # Показываем сохранённый текст только если есть коды (иначе он неработоспособен)
        if (
            saved_hotkey
            and saved_hotkey not in invalid_texts
            and self.captured_hotkey_codes is not None
            and len(self.captured_hotkey_codes) > 0
        ):
            self.hotkey_input.setText(saved_hotkey)
        else:
            self.hotkey_input.setText(self.translations[saved_lang]["not_set"])

        # Обновляем текст на кнопках звуков (читаем из QSettings, а не из config)
        for tf_key in config.TIMEFRAMES.keys():
            # Используем разные имена для 1M в QSettings (1Month вместо 1M)
            # чтобы избежать case-insensitive конфликтов в Windows реестре
            qsettings_key = tf_key.replace("1M", "1Month") if tf_key == "1M" else tf_key

            main_name = settings.value(
                f"sound_main_{qsettings_key}", config.TIMEFRAMES[tf_key]["file"]
            )
            tick_name = settings.value(
                f"sound_tick_{qsettings_key}", config.SOUND_TICK_BY_TF.get(tf_key, "")
            )
            trans_name = settings.value(
                f"sound_transition_{qsettings_key}",
                config.SOUND_TRANSITION_BY_TF.get(tf_key, ""),
            )

            if (tf_key, "main") in self.sound_buttons:
                self.sound_buttons[(tf_key, "main")].setText(
                    os.path.basename(main_name) if main_name else ""
                )
            if (tf_key, "tick") in self.sound_buttons:
                self.sound_buttons[(tf_key, "tick")].setText(
                    os.path.basename(tick_name) if tick_name else ""
                )
            if (tf_key, "transition") in self.sound_buttons:
                self.sound_buttons[(tf_key, "transition")].setText(
                    os.path.basename(trans_name) if trans_name else ""
                )

        # Настройки фандинга (звук и TTS)
        self.funding_sound_check.setChecked(
            settings.value("funding_sound_enabled", True, type=bool)
        )
        self.funding_tts_check.setChecked(
            settings.value("funding_tts_enabled", True, type=bool)
        )
        self.funding_sound_file = settings.value("funding_sound_file", "")
        self.funding_sound_value.setText(
            os.path.basename(self.funding_sound_file)
            if self.funding_sound_file
            else "-"
        )
        self._load_tts_voices()
        saved_voice_id = settings.value("funding_tts_voice_id", "")
        if saved_voice_id:
            idx = self.funding_tts_voice_combo.findData(saved_voice_id)
            if idx >= 0:
                self.funding_tts_voice_combo.setCurrentIndex(idx)

        # Сбрасываем режим захвата
        self.capturing_hotkey = False

    def change_dialog_language(self, lang):
        """Изменяет язык всех элементов диалога"""
        t = self.translations[lang]

        self.title.setText(t["title"])
        self.lang_label.setText(t["language"])
        self.scale_label.setText(t["scale"])
        self.hotkey_label.setText(t["hotkey"])
        self.clear_hotkey_btn.setText(t["clear"])
        self.cancel_btn.setText(t["cancel"])
        self.save_btn.setText(t["save"])
        self.sounds_title.setText(t["sounds_title"])
        self.header_tf.setText(t["tf_col"])
        self.header_voice.setText(t["voice_col"])
        self.header_tick.setText(t["tick_col"])
        self.header_transition.setText(t["transition_col"])
        self.about_btn.setText(t["about_btn"])
        self.donate_btn.setText(t["donate_btn"])
        self.funding_title.setText(t["funding_title"])
        self.funding_sound_check.setText(t["funding_sound_enabled"])
        self.funding_tts_check.setText(t["funding_tts_enabled"])
        self.funding_sound_label.setText(t["funding_sound_file"])
        self.funding_sound_btn.setText(t["funding_sound_pick"])
        self.funding_tts_voice_label.setText(t["funding_tts_voice"])

        # Обновляем названия таймфреймов
        for tf_key, label in self.tf_labels.items():
            label.setText(config.get_timeframe_label(tf_key, lang))

        # Обновляем placeholder тексты не привращаю текст по-быстрому
        current_hotkey = self.hotkey_input.text()
        invalid_texts = ["Не задана", "Нажмите клавишу...", "Not set", "Press a key..."]
        if current_hotkey in invalid_texts:
            self.hotkey_input.setText(t["not_set"])

    def start_capture(self):
        """Начинает захват клавиши"""
        self._pressed_vks.clear()
        self._pressed_names.clear()
        self._saw_non_modifier = False
        self._last_modifiers_vks.clear()

        self.capturing_hotkey = True
        current_lang = self.lang_combo.currentText()
        self.hotkey_input.setText(self.translations[current_lang]["capturing"])
        # Устанавливаем фокус на диалог, а не на кнопку
        self.setFocus()
        # Гарантируем что все события клавиатуры придут сюда
        try:
            self.grabKeyboard()
        except Exception:
            pass

    def _vk_to_name(self, vk):
        try:
            scan = int(self._user32.MapVirtualKeyW(int(vk), self._MAPVK_VK_TO_VSC_EX))
            if scan == 0:
                return str(vk)
            lparam = (scan & 0xFF) << 16
            buf = ctypes.create_unicode_buffer(64)
            if self._user32.GetKeyNameTextW(lparam, buf, 64) > 0:
                return buf.value
        except Exception:
            pass
        return str(vk)

    def keyPressEvent(self, event: QKeyEvent):
        """Обработка нажатия клавиш"""
        if not self.capturing_hotkey:
            super().keyPressEvent(event)
            return

        if event.isAutoRepeat():
            return

        key = event.key()
        current_lang = self.lang_combo.currentText()

        # ESC отменяет ввод
        if key == Qt.Key.Key_Escape:
            self.hotkey_input.setText(self.translations[current_lang]["not_set"])
            self.capturing_hotkey = False
            return

        vk = int(event.nativeVirtualKey())
        if vk <= 0:
            return

        self._pressed_vks.add(vk)
        if vk not in self._pressed_names:
            self._pressed_names[vk] = self._vk_to_name(vk)

        if vk in self._VK_MODIFIERS:
            self._last_modifiers_vks = set(self._pressed_vks)
            return

        self._saw_non_modifier = True
        self._finalize_hotkey(list(self._pressed_vks))

    def keyReleaseEvent(self, event: QKeyEvent):
        if not self.capturing_hotkey:
            super().keyReleaseEvent(event)
            return

        if event.isAutoRepeat():
            return

        vk = int(event.nativeVirtualKey())
        if vk > 0:
            self._pressed_vks.discard(vk)

        if (
            not self._saw_non_modifier
            and not self._pressed_vks
            and self._last_modifiers_vks
        ):
            self._finalize_hotkey(list(self._last_modifiers_vks))

    def _is_modifier_name(self, name):
        if not name:
            return False
        return name in {
            "Left Ctrl",
            "Right Ctrl",
            "Ctrl",
            "Left Alt",
            "Right Alt",
            "Alt",
            "Alt Gr",
            "Left Shift",
            "Right Shift",
            "Shift",
            "Left Windows",
            "Right Windows",
            "Windows",
        }

    def _format_key_name(self, name):
        if not name:
            return ""
        return " ".join(part.capitalize() for part in name.split())

    def _vk_display_name(self, vk):
        if vk in self._VK_DISPLAY:
            return self._VK_DISPLAY[vk]
        name = self._pressed_names.get(vk)
        if name:
            return name
        return self._vk_to_name(vk)

    def _build_hotkey_display(self, scan_codes):
        vks = [int(x) for x in scan_codes if isinstance(x, int) or str(x).isdigit()]
        modifier_order_vks = [
            0xA2,  # LCtrl
            0xA3,  # RCtrl
            0x11,  # Ctrl
            0xA4,  # LAlt
            0xA5,  # RAlt
            0x12,  # Alt
            0xA0,  # LShift
            0xA1,  # RShift
            0x10,  # Shift
            0x5B,  # LWin
            0x5C,  # RWin
        ]
        mods = [vk for vk in vks if vk in self._VK_MODIFIERS]
        others = [vk for vk in vks if vk not in self._VK_MODIFIERS]

        ordered = [vk for vk in modifier_order_vks if vk in mods]
        ordered += others

        parts = [self._vk_display_name(vk) for vk in ordered]
        parts = [self._format_key_name(p) for p in parts if p]
        return "+".join(parts)

    def _finalize_hotkey(self, scan_codes):
        if not scan_codes:
            return
        display = self._build_hotkey_display(scan_codes)
        if display:
            self.hotkey_input.setText(display)
            self.captured_hotkey_codes = list(scan_codes)
            self.capturing_hotkey = False

        if not self.capturing_hotkey:
            try:
                self.releaseKeyboard()
            except Exception:
                pass

    def clear_hotkey(self):
        """Очищает горячую клавишу"""
        current_lang = self.lang_combo.currentText()
        self.hotkey_input.setText(self.translations[current_lang]["not_set"])
        self.capturing_hotkey = False
        self.captured_hotkey_codes = None
        try:
            self.releaseKeyboard()
        except Exception:
            pass

    def save_and_close(self):
        """Сохраняет настройки и закрывает окно"""
        settings = QSettings("MyTradeTools", "TF-Alerter")

        # Сохраняем язык
        settings.setValue("language", self.lang_combo.currentText())

        # Сохраняем масштаб
        settings.setValue("interface_scale_text", self.scale_combo.currentText())

        # Сохраняем горячую клавишу
        hotkey_text = self.hotkey_input.text()
        # Игнорируем placeholder текст
        invalid_texts = [
            "Не задана",
            "Нажмите клавишу...",
            "Not set",
            "Press a key...",
            "",
        ]
        hotkey = "" if hotkey_text in invalid_texts else hotkey_text
        settings.setValue("hotkey", hotkey)
        if hotkey and self.captured_hotkey_codes is not None:
            settings.setValue(
                "hotkey_codes",
                ",".join(str(sc) for sc in self.captured_hotkey_codes),
            )
        else:
            settings.remove("hotkey_codes")

        # Применяем язык в родительском окне (только если изменился)
        if self.parent:
            current_lang = self.parent.ui.lang_sel.currentText()
            new_lang = self.lang_combo.currentText()

            if current_lang != new_lang:
                self.parent.ui.lang_sel.setCurrentText(new_lang)
                self.parent.ui.change_language(new_lang)

            # Применяем масштаб интерфейса
            new_scale = self.scale_combo.currentText()
            self.parent.apply_interface_scale(new_scale)

        # Сохраняем состояние переключателей звуков по колонкам
        settings.setValue("sounds_voice_enabled", self.check_voice_enabled.isChecked())
        settings.setValue("sounds_tick_enabled", self.check_tick_enabled.isChecked())
        settings.setValue(
            "sounds_transition_enabled",
            self.check_transition_enabled.isChecked(),
        )

        # Сохраняем настройки фандинга
        settings.setValue("funding_sound_enabled", self.funding_sound_check.isChecked())
        settings.setValue("funding_tts_enabled", self.funding_tts_check.isChecked())
        settings.setValue(
            "funding_tts_voice_id",
            (
                self.funding_tts_voice_combo.currentData()
                if self.funding_tts_voice_combo.count() > 0
                else ""
            ),
        )

        self.accept()

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

    def _open_about(self):
        """Открыть диалог О программе из главного окна"""
        if self.parent and hasattr(self.parent, "open_about"):
            self.parent.open_about()

    def _open_donate(self):
        """Открыть диалог Пожертвований из главного окна"""
        if self.parent and hasattr(self.parent, "open_donate"):
            self.parent.open_donate()

    def closeEvent(self, event):
        try:
            self.releaseKeyboard()
        except Exception:
            pass
        super().closeEvent(event)
