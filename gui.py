from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QCheckBox,
    QFrame,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QListWidget,
    QStyledItemDelegate,
    QFontComboBox,
    QTabWidget,
    QTabBar,
    QGraphicsOpacityEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSettings, QRect, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
import config


class TFCheckBox(QCheckBox):
    """Чекбокс с поддержкой двойного клика и собственным рисованием галочки"""

    double_clicked = pyqtSignal(str)  # Передаём ключ таймфрейма

    def __init__(self, text, tf_key, parent=None):
        super().__init__(text, parent)
        self.tf_key = tf_key

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.tf_key)
        super().mouseDoubleClickEvent(event)

    def paintEvent(self, event):
        """Переопределяем рисование для кастомной галочки"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        indicator_rect_x = 2
        indicator_rect_y = (self.height() - 16) // 2
        indicator_rect = QRect(indicator_rect_x, indicator_rect_y, 16, 16)

        if self.isChecked():
            painter.fillRect(indicator_rect, QColor("#1e90ff"))
            painter.setPen(QPen(QColor("#1e90ff"), 2))
            painter.drawRect(indicator_rect)

            pen = QPen(QColor("black"), 2, Qt.PenStyle.SolidLine)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            x = indicator_rect_x
            y = indicator_rect_y
            painter.drawLine(int(x + 3), int(y + 9), int(x + 7), int(y + 13))
            painter.drawLine(int(x + 7), int(y + 13), int(x + 13), int(y + 5))
        else:
            painter.setPen(QPen(QColor("#555"), 2))
            painter.drawRect(indicator_rect)

        text_color = QColor("#bbb") if self.isEnabled() else QColor("#666")
        painter.setPen(text_color)
        text_rect = QRect(25, 0, self.width() - 30, self.height())
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.text(),
        )
        painter.end()


class CenteredItemDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter


class CenteredComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ignore_next_hide = False

    def mousePressEvent(self, event):
        # For non-editable combo, open popup on any click except drop-down arrow area
        if event.pos().x() < self.width() - 25:
            if not self.view().isVisible():
                self._ignore_next_hide = True
                self.showPopup()
        event.accept()

    def hidePopup(self):
        if self._ignore_next_hide:
            self._ignore_next_hide = False
            return  # Ignore this immediate hide call
        super().hidePopup()


class ExpandingTabBar(QTabBar):
    """QTabBar, который растягивает вкладки на всю ширину поровну"""

    def sizeHint(self):
        """Растягиваем tab bar на полную ширину"""
        hint = super().sizeHint()
        return hint

    def mouseReleaseEvent(self, event):
        # Make sure selection works properly
        super().mouseReleaseEvent(event)


class NoSelectLineEdit(QLineEdit):
    """QLineEdit that prevents text selection and responds to clicks by showing popup"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._combo = None

    def setCombo(self, combo):
        self._combo = combo

    def mousePressEvent(self, event):
        if self._combo and not self._combo.view().isVisible():
            self._combo.showPopup()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        # Block double-click selection
        event.ignore()

    def contextMenuEvent(self, event):
        # Block context menu
        event.ignore()

    def keyPressEvent(self, event):
        # Block Ctrl+A
        if (
            event.key() == Qt.Key.Key_A
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            event.ignore()
            return
        super().keyPressEvent(event)


class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.setStyleSheet(
            f"background-color: {config.COLORS['panel']}; border-top-left-radius: 15px; border-top-right-radius: 15px; border-bottom: 1px solid #222;"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 0, 0)
        layout.setSpacing(0)
        self.logo_label = QLabel()
        # Ленивая загрузка логотипа - загружаем только при первом обращении
        self._logo_loaded = False
        self.logo_label.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.logo_label)
        layout.addSpacing(8)
        self.title_label = QLabel(config.APP_NAME.upper())
        fixed_blue = "#1e90ff"
        self.title_label.setStyleSheet(
            f"color: {fixed_blue}; font-family: 'Segoe UI Semibold'; font-size: 12px; letter-spacing: 2px; background: transparent; border: none;"
        )
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Кнопки справа (шестеренка, свернуть, закрыть) — плотно, как "мордочка"
        button_group = QWidget()
        button_group.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        button_group.setStyleSheet("background: transparent;")
        group_layout = QHBoxLayout(button_group)
        group_layout.setContentsMargins(0, 0, 0, 0)
        group_layout.setSpacing(0)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(34, 40)
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #888; border: none; font-size: 18px; padding-left: 4px; }"
            "QPushButton:hover { background: transparent; color: #1e90ff; border: 2px solid #1e90ff; }"
        )
        settings_btn.clicked.connect(self.parent.open_settings)
        group_layout.addWidget(settings_btn)

        minimize_btn = QPushButton("")
        minimize_btn.setFixedSize(34, 40)
        minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        minimize_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #888; border: none; font-family: 'Segoe MDL2 Assets'; font-size: 12px; padding-left: 4px; }"
            "QPushButton:hover { background: #333; color: white; }"
        )
        minimize_btn.clicked.connect(self.parent.request_minimize)

        minimize_wrap = QWidget()
        minimize_wrap.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        minimize_wrap.setStyleSheet("background: transparent;")
        minimize_layout = QVBoxLayout(minimize_wrap)
        minimize_layout.setContentsMargins(0, 12, 0, 0)
        minimize_layout.setSpacing(0)
        minimize_layout.addWidget(minimize_btn)
        group_layout.addWidget(minimize_wrap)

        close_btn = QPushButton("")
        close_btn.setFixedSize(34, 40)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {config.COLORS['danger']}; border: none; font-family: 'Segoe MDL2 Assets'; font-size: 12px; }} QPushButton:hover {{ background: {config.COLORS['danger']}; color: white; }}"
        )
        close_btn.setStyleSheet(
            close_btn.styleSheet() + "border-top-right-radius: 15px;"
        )
        close_btn.clicked.connect(self.parent.close)
        group_layout.addWidget(close_btn)

        layout.addWidget(button_group)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.parent.old_pos:
            delta = event.globalPosition().toPoint() - self.parent.old_pos
            self.parent.move(self.parent.x() + delta.x(), self.parent.y() + delta.y())
            self.parent.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.parent.old_pos = None
        # Сохраняем позицию окна после перетаскивания
        if hasattr(self.parent, "save_settings"):
            self.parent.save_settings()

    def showEvent(self, event):
        """Загружаем логотип при первом отображении (ленивая загрузка)"""
        if not self._logo_loaded:
            self._load_logo()
        super().showEvent(event)

    def _load_logo(self):
        """Ленивая загрузка логотипа - вызывается только при первом показе"""
        try:
            pix = QPixmap(config.LOGO_PATH).scaled(
                22,
                22,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            self.logo_label.setPixmap(pix)
            self._logo_loaded = True
        except Exception:
            pass


class UI_Widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.old_pos = None
        self.trans = {
            "ru": {
                "main_tab": "Главное",
                "funding_tab": "Фандинг",
                "funding_title": "Алерты фандинга",
                "funding_exchanges": "Биржи:",
                "funding_binance": "Binance",
                "funding_bybit": "Bybit",
                "funding_okx": "OKX",
                "funding_gate": "Gate",
                "funding_bitget": "Bitget",
                "funding_alerts": "Типы алертов:",
                "funding_before": "До фандинга",
                "funding_percent": "Funding %",
                "funding_minutes": "Минуты до фандинга:",
                "funding_threshold": "Порог %:",
                "funding_threshold_pos": "Порог +%:",
                "funding_threshold_neg": "Порог -%:",
                "funding_tts": "Голос (TTS)",
                "funding_sound": "Звук",
                "funding_voice": "Голос TTS:",
                "funding_sound_file": "Звук фандинга:",
                "funding_sound_pick": "Выбрать звук",
                "funding_log": "Лог алертов:",
                "funding_upcoming": "Предстоящие",
                "funding_triggered": "Сработавшие",
                "funding_clear": "Очистить лог",
                "funding_refresh": "Обновить",
                "vol": "ГРОМКОСТЬ",
                "font": "РАЗМЕР ЧАСОВ",
                "scale": "МАСШТАБ ИНТЕРФЕЙСА",
                "show": "ОТОБРАЖАТЬ ЧАСЫ (OVERLAY)",
                "lock_move": "Блокировать перемещение часов",
                "btn": "ЦВЕТ ЧАСОВ",
                "font_btn": "Шрифт",
                "mode": "Режим:",
                "select_app": "Выбрать приложения",
                "always_show": "Всегда показывать",
                "custom_windows": "Только на определённых окнах",
                "tfs": {
                    "1m": "1м",
                    "5m": "5м",
                    "15m": "15м",
                    "30m": "30м",
                    "1h": "1ч",
                    "4h": "4ч",
                    "1d": "1д",
                    "1w": "1н",
                    "1M": "1мес",
                },
            },
            "en": {
                "main_tab": "Main",
                "funding_tab": "Funding",
                "funding_title": "Funding Alerts",
                "funding_exchanges": "Exchanges:",
                "funding_binance": "Binance",
                "funding_bybit": "Bybit",
                "funding_okx": "OKX",
                "funding_gate": "Gate",
                "funding_bitget": "Bitget",
                "funding_alerts": "Alert Types:",
                "funding_before": "Before Funding",
                "funding_percent": "Funding %",
                "funding_minutes": "Minutes before funding:",
                "funding_threshold": "Threshold %:",
                "funding_threshold_pos": "Threshold +%:",
                "funding_threshold_neg": "Threshold -%:",
                "funding_tts": "Voice (TTS)",
                "funding_sound": "Sound",
                "funding_voice": "TTS Voice:",
                "funding_sound_file": "Funding sound:",
                "funding_sound_pick": "Pick sound",
                "funding_log": "Alert log:",
                "funding_upcoming": "Upcoming",
                "funding_triggered": "Triggered",
                "funding_clear": "Clear log",
                "vol": "VOLUME",
                "font": "CLOCK SIZE",
                "scale": "INTERFACE SCALE",
                "show": "DISPLAY CLOCK (OVERLAY)",
                "lock_move": "Lock Clock Movement",
                "btn": "CLOCK COLOR",
                "font_btn": "Font",
                "mode": "Mode:",
                "select_app": "Select Applications",
                "always_show": "Always Show",
                "custom_windows": "Only on Specific Windows",
                "tfs": {
                    "1m": "1m",
                    "5m": "5m",
                    "15m": "15m",
                    "30m": "30m",
                    "1h": "1h",
                    "4h": "4h",
                    "1d": "1d",
                    "1w": "1w",
                    "1M": "1mo",
                },
            },
        }
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: none; margin: 0px; }} "
            f"QTabWidget::tab-bar {{ left: 8px; }} "
            f"QTabBar {{ background: {config.COLORS['background']}; margin: 0px; }} "
            f"QTabBar::tab {{ background: {config.COLORS['panel']}; color: {config.COLORS['text']}; padding: 6px 10px; margin: 0px; border: 1px solid {config.COLORS['border']}; border-bottom: none; min-width: 0px; }} "
            f"QTabBar::tab:first {{ margin-left: 8px; }} "
            f"QTabBar::tab:last {{ margin-right: 0px; }} "
            f"QTabBar::tab:selected {{ background: #1e90ff; color: black; border: 2px solid #1e90ff; border-bottom: none; font-weight: bold; }} "
        )
        self.root_layout.addWidget(self.tabs)

        self.main_tab = QWidget()
        self.main_layout = QVBoxLayout(self.main_tab)
        self.main_layout.setContentsMargins(15, 10, 15, 20)
        self.main_layout.setSpacing(10)
        self.selected_clock_font = "Arial"

        # Язык (скрытый, управляется через настройки)
        self.lang_sel = QComboBox()
        self.lang_sel.addItems(["RU", "EN"])
        self.lang_sel.setVisible(False)  # Теперь управляется через окно настроек

        # ТФ
        self.card_tf = QFrame()
        self.card_tf.setStyleSheet(
            "QFrame { background: #161616; border-radius: 12px; border: 1px solid #252525; }"
        )
        self.card_tf_layout = QVBoxLayout(self.card_tf)
        self.card_tf_layout.setContentsMargins(10, 10, 10, 10)
        self.card_tf_layout.setSpacing(8)
        self.grid = QGridLayout()
        self.checkboxes = {}
        self.create_tf_widgets("ru")
        self.card_tf_layout.addLayout(self.grid)

        # Слайдер громкости внутри блока ТФ, под галочками
        vol_lay = QHBoxLayout()
        vol_lay.setContentsMargins(4, 0, 4, 0)
        self.l_vol = QLabel("ГРОМКОСТЬ")
        self.l_vol.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px; border: none; background: transparent;"
        )
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setStyleSheet(self._slider_style())
        vol_lay.addWidget(self.l_vol)
        vol_lay.addWidget(self.volume_slider)
        self.card_tf_layout.addLayout(vol_lay)

        self.main_layout.addWidget(self.card_tf)

        # Блок настроек Overlay: размер, отображение, режим, выбор приложений, цвет
        self.card_overlay = QFrame()
        self.card_overlay.setStyleSheet(self._card_style(padding="12px"))
        overlay_lay = QVBoxLayout(self.card_overlay)
        overlay_lay.setSpacing(8)

        # 1) Чекбокс отображения часов (используем TFCheckBox чтобы получить чёрную галочку)
        self.cb_overlay = TFCheckBox(self.trans["ru"]["show"], "overlay")
        self.cb_overlay.setStyleSheet(self._tf_check_style())
        overlay_lay.addWidget(self.cb_overlay)

        self.cb_lock_overlay_move = TFCheckBox(
            self.trans["ru"]["lock_move"], "lock_move"
        )
        self.cb_lock_overlay_move.setStyleSheet(self._tf_check_style())
        overlay_lay.addWidget(self.cb_lock_overlay_move)

        # 2) Режим (ниже чекбокса)
        mode_layout = QHBoxLayout()
        mode_layout.setSpacing(0)
        self.overlay_mode_label = QLabel(self.trans["ru"]["mode"])
        self.overlay_mode_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        self.overlay_mode_combo = CenteredComboBox()
        # Non-editable combo: add items first, use paintEvent to center display text
        self.overlay_mode_combo.addItems(
            [self.trans["ru"]["always_show"], self.trans["ru"]["custom_windows"]]
        )
        self.overlay_mode_combo.setStyleSheet(self._combo_style())
        self.overlay_mode_combo.setItemDelegate(
            CenteredItemDelegate(self.overlay_mode_combo)
        )
        for i in range(self.overlay_mode_combo.count()):
            self.overlay_mode_combo.setItemData(
                i, Qt.AlignmentFlag.AlignCenter, Qt.ItemDataRole.TextAlignmentRole
            )
        self.overlay_mode_combo.setMinimumContentsLength(20)
        self.overlay_mode_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.overlay_mode_combo.setMinimumWidth(220)
        mode_layout.addWidget(self.overlay_mode_label)
        mode_layout.addWidget(self.overlay_mode_combo)
        mode_layout.addStretch()
        overlay_lay.addLayout(mode_layout)

        # 3) Кнопка выбора приложений (под режимом) — может скрываться если режим "Всегда показывать"
        select_app_layout = QHBoxLayout()
        select_app_layout.setSpacing(8)
        self.select_app_btn = QPushButton(self.trans["ru"]["select_app"])
        self.select_app_btn.setStyleSheet(self._select_app_style())
        self.select_app_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.select_app_btn.setMinimumWidth(200)
        select_app_layout.addStretch()
        select_app_layout.addWidget(self.select_app_btn)
        select_app_layout.addStretch()
        overlay_lay.addLayout(select_app_layout)

        # 4) Слайдер размера часов (уменьшенный)
        h2 = QHBoxLayout()
        self.l_size = QLabel(self.trans["ru"]["font"])
        self.l_size.setStyleSheet("color:#888; font-weight:bold; font-size: 9px;")
        self.ov_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.ov_size_slider.setRange(20, 150)
        self.ov_size_slider.setStyleSheet(self._small_slider_style())
        self.ov_size_slider.setFixedHeight(14)
        h2.addWidget(self.l_size)
        h2.addWidget(self.ov_size_slider)
        overlay_lay.addLayout(h2)

        # 5) Кнопка цвета часов — под размером, слева
        color_layout = QHBoxLayout()
        color_layout.setContentsMargins(0, 0, 0, 0)
        self.color_btn = QPushButton(self.trans["ru"]["btn"])
        self.color_btn.setStyleSheet(self._color_btn_style())
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setFont(self.l_size.font())
        self.color_btn.setSizePolicy(
            self.color_btn.sizePolicy().Policy.Fixed,
            self.color_btn.sizePolicy().Policy.Fixed,
        )
        self._sync_color_btn_size()
        QTimer.singleShot(0, self._sync_color_btn_size)
        color_layout.addWidget(self.color_btn)
        color_layout.addSpacing(10)

        self.clock_font_label = QLabel(self.trans["ru"]["font_btn"])
        self.clock_font_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px; border: none; background: transparent;"
        )
        color_layout.addWidget(self.clock_font_label)

        self.clock_font_combo = QFontComboBox()
        self.clock_font_combo.setStyleSheet(self._combo_style())
        self.clock_font_combo.setMinimumWidth(170)
        self.clock_font_combo.setToolTip("Выбор шрифта часов")
        color_layout.addWidget(self.clock_font_combo)

        color_layout.setAlignment(self.color_btn, Qt.AlignmentFlag.AlignLeft)
        color_layout.addStretch()
        overlay_lay.addLayout(color_layout)

        self.main_layout.addWidget(self.card_overlay)

        self.tabs.addTab(self.main_tab, self.trans["ru"]["main_tab"])

        self.funding_tab = QWidget()
        funding_layout = QVBoxLayout(self.funding_tab)
        funding_layout.setContentsMargins(15, 10, 15, 20)
        funding_layout.setSpacing(10)

        funding_title = QLabel(self.trans["ru"]["funding_title"])
        funding_title.setStyleSheet(
            f"color: {config.COLORS['text']}; font-size: 12px; font-weight: bold;"
        )
        funding_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        funding_layout.addWidget(funding_title)

        # Кнопка включения/выключения фандинга
        enable_row = QHBoxLayout()
        self.funding_enable_check = TFCheckBox(
            "Включить алерты фандинга", "funding_enable"
        )
        self.funding_enable_check.setStyleSheet(self._tf_check_style())
        self.funding_enable_check.setChecked(True)
        enable_row.addWidget(self.funding_enable_check)
        enable_row.addStretch()
        funding_layout.addLayout(enable_row)

        # Контейнер для остального контента фандинга
        self.funding_content_widget = QWidget()

        # Создаем эффект затемнения для отключенного состояния
        self.funding_opacity_effect = QGraphicsOpacityEffect()
        self.funding_opacity_effect.setOpacity(1.0)
        self.funding_content_widget.setGraphicsEffect(self.funding_opacity_effect)

        funding_content_layout = QVBoxLayout(self.funding_content_widget)
        funding_content_layout.setContentsMargins(0, 5, 0, 0)
        funding_content_layout.setSpacing(10)

        self.funding_exchanges_label = QLabel(self.trans["ru"]["funding_exchanges"])
        self.funding_exchanges_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        funding_content_layout.addWidget(self.funding_exchanges_label)

        exchanges_grid = QGridLayout()
        exchanges_grid.setHorizontalSpacing(12)
        exchanges_grid.setVerticalSpacing(6)
        self.funding_binance_check = TFCheckBox(
            self.trans["ru"]["funding_binance"], "funding_binance"
        )
        self.funding_bybit_check = TFCheckBox(
            self.trans["ru"]["funding_bybit"], "funding_bybit"
        )
        self.funding_okx_check = TFCheckBox(
            self.trans["ru"]["funding_okx"], "funding_okx"
        )
        self.funding_gate_check = TFCheckBox(
            self.trans["ru"]["funding_gate"], "funding_gate"
        )
        self.funding_bitget_check = TFCheckBox(
            self.trans["ru"]["funding_bitget"], "funding_bitget"
        )
        self.funding_binance_check.setStyleSheet(self._tf_check_style())
        self.funding_bybit_check.setStyleSheet(self._tf_check_style())
        self.funding_okx_check.setStyleSheet(self._tf_check_style())
        self.funding_gate_check.setStyleSheet(self._tf_check_style())
        self.funding_bitget_check.setStyleSheet(self._tf_check_style())
        exchanges_grid.addWidget(self.funding_binance_check, 0, 0)
        exchanges_grid.addWidget(self.funding_bybit_check, 0, 1)
        exchanges_grid.addWidget(self.funding_okx_check, 0, 2)
        exchanges_grid.addWidget(self.funding_gate_check, 1, 0)
        exchanges_grid.addWidget(self.funding_bitget_check, 1, 1)
        exchanges_grid.setColumnStretch(2, 1)
        funding_content_layout.addLayout(exchanges_grid)

        minutes_row = QHBoxLayout()
        self.funding_minutes_label = QLabel(self.trans["ru"]["funding_minutes"])
        self.funding_minutes_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        self.funding_minutes_edit = QLineEdit()
        self.funding_minutes_edit.setPlaceholderText("15,5")
        self.funding_minutes_edit.setStyleSheet(self._input_style())
        minutes_row.addWidget(self.funding_minutes_label)
        minutes_row.addWidget(self.funding_minutes_edit)
        funding_content_layout.addLayout(minutes_row)

        threshold_row = QHBoxLayout()
        self.funding_threshold_pos_label = QLabel(
            self.trans["ru"]["funding_threshold_pos"]
        )
        self.funding_threshold_pos_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        self.funding_threshold_pos_edit = QLineEdit()
        self.funding_threshold_pos_edit.setPlaceholderText("0")
        self.funding_threshold_pos_edit.setStyleSheet(self._input_style())
        threshold_row.addWidget(self.funding_threshold_pos_label)
        threshold_row.addWidget(self.funding_threshold_pos_edit)

        self.funding_threshold_neg_label = QLabel(
            self.trans["ru"]["funding_threshold_neg"]
        )
        self.funding_threshold_neg_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        self.funding_threshold_neg_edit = QLineEdit()
        self.funding_threshold_neg_edit.setPlaceholderText("0")
        self.funding_threshold_neg_edit.setStyleSheet(self._input_style())
        threshold_row.addWidget(self.funding_threshold_neg_label)
        threshold_row.addWidget(self.funding_threshold_neg_edit)
        funding_content_layout.addLayout(threshold_row)

        # Слайдер громкости для фандинга
        funding_vol_lay = QHBoxLayout()
        funding_vol_lay.setContentsMargins(4, 0, 4, 0)
        self.funding_volume_label = QLabel(self.trans["ru"]["vol"])
        self.funding_volume_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px; border: none; background: transparent;"
        )
        self.funding_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.funding_volume_slider.setStyleSheet(self._slider_style())
        self.funding_volume_slider.setRange(0, 100)
        self.funding_volume_slider.setValue(80)
        funding_vol_lay.addWidget(self.funding_volume_label)
        funding_vol_lay.addWidget(self.funding_volume_slider)
        funding_content_layout.addLayout(funding_vol_lay)

        self.funding_log_label = QLabel(self.trans["ru"]["funding_log"])
        self.funding_log_label.setStyleSheet(
            "color:#888; font-weight:bold; font-size: 10px;"
        )
        funding_content_layout.addWidget(self.funding_log_label)

        log_filters_row = QHBoxLayout()
        log_filters_row.setSpacing(6)
        self.funding_log_upcoming_btn = QPushButton(
            self.trans["ru"]["funding_upcoming"]
        )
        self.funding_log_triggered_btn = QPushButton(
            self.trans["ru"]["funding_triggered"]
        )
        for btn in (self.funding_log_upcoming_btn, self.funding_log_triggered_btn):
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ color: #9a9a9a; border: 1px solid #3a3a3a; border-radius: 6px; background: #191919; padding: 2px 8px; font-size: 9px; font-weight: bold; }} "
                f"QPushButton:checked {{ color: #111; border: 1px solid {config.COLORS['accent']}; background: {config.COLORS['accent']}; }} "
                "QPushButton:hover:!checked { border: 1px solid #5a5a5a; color: #c7c7c7; }"
            )
        self.funding_log_upcoming_btn.setChecked(True)
        log_filters_row.addWidget(self.funding_log_upcoming_btn)
        log_filters_row.addWidget(self.funding_log_triggered_btn)
        log_filters_row.addStretch()
        funding_content_layout.addLayout(log_filters_row)

        self.funding_log_list = QListWidget()
        self.funding_log_list.setStyleSheet(self._list_style())
        self.funding_log_list.setWordWrap(True)
        self.funding_log_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        funding_content_layout.addWidget(self.funding_log_list)

        buttons_row = QHBoxLayout()
        self.funding_refresh_btn = QPushButton(self.trans["ru"]["funding_refresh"])
        self.funding_refresh_btn.setStyleSheet(self._select_app_style())
        self.funding_clear_btn = QPushButton(self.trans["ru"]["funding_clear"])
        self.funding_clear_btn.setStyleSheet(self._select_app_style())
        buttons_row.addWidget(self.funding_refresh_btn)
        buttons_row.addStretch()
        buttons_row.addWidget(self.funding_clear_btn)
        funding_content_layout.addLayout(buttons_row)

        # Добавляем контейнер контента в основной layout
        funding_layout.addWidget(self.funding_content_widget)

        self.tabs.addTab(self.funding_tab, self.trans["ru"]["funding_tab"])

        # Растягиваем обе вкладки равномерно на всю ширину
        tab_bar = self.tabs.tabBar()
        tab_bar.setExpanding(True)
        tab_bar.setUsesScrollButtons(False)

        # --- УПРАВЛЕНИЕ ОКНАМИ OVERLAY ---
        # Подключаем отображение кнопки выбора приложений к изменениям режима
        self.overlay_mode_combo.currentIndexChanged.connect(
            self._on_overlay_mode_changed
        )
        # Инициалное состояние: скрыть кнопку если выбран "Всегда показывать"
        if self.overlay_mode_combo.currentIndex() == 0:
            self.select_app_btn.setVisible(False)
        else:
            self.select_app_btn.setVisible(True)

        # Невидимый лейбл для логики
        self.time_label = QLabel("")
        self.time_label.hide()

    def create_tf_widgets(self, lang_key):
        from PyQt6.QtCore import QSettings

        # Сохраняем текущее состояние галочек из UI (перед пересозданием)
        saved_states_from_ui = {}
        for key, cb in self.checkboxes.items():
            saved_states_from_ui[key] = cb.isChecked()

        # Удаляем старые виджеты
        for i in reversed(range(self.grid.count())):
            w = self.grid.itemAt(i).widget()
            if w:
                w.setParent(None)

        # Создаем новые с сохраненными состояниями (для смены языка)
        tfs = self.trans[lang_key]["tfs"]
        for i, (key, data) in enumerate(config.TIMEFRAMES.items()):
            cb = TFCheckBox(tfs.get(key, data["label"]), key)
            # Получаем переведённый label для тултипа
            settings = QSettings("MyTradeTools", "TF-Alerter")
            current_lang = settings.value("language", "RU")
            tooltip_label = config.get_timeframe_label(key, current_lang)
            cb.setToolTip(tooltip_label + " (Двойной клик для теста звука)")
            # Восстанавливаем состояние из UI (перед пересозданием)
            # Состояние из реестра будет установлено в load_settings()
            cb.setChecked(saved_states_from_ui.get(key, False))
            cb.setStyleSheet(self._tf_check_style())
            self.checkboxes[key] = cb
            self.grid.addWidget(cb, i // 4, i % 4)

    def _small_slider_style(self):
        return f"QSlider::groove:horizontal {{ background: #222; height: 4px; border-radius: 2px; }} QSlider::handle:horizontal {{ background: white; border: 1px solid {config.COLORS['accent']}; width: 10px; height: 10px; margin: -4px 0; border-radius: 5px; }}"

    def _sync_color_btn_size(self):
        try:
            label_hint = self.l_size.sizeHint()
            self.color_btn.setMinimumSize(label_hint.width(), label_hint.height())
            self.color_btn.setMaximumSize(label_hint.width(), label_hint.height())
        except Exception:
            pass

    def _on_overlay_mode_changed(self, index_or_text):
        # If index 0 (first item) => "Всегда показывать" -> hide select_app_btn
        try:
            idx = self.overlay_mode_combo.currentIndex()
            if idx == 0:
                self.select_app_btn.setVisible(False)
            else:
                self.select_app_btn.setVisible(True)
        except Exception:
            pass

    def change_language(self, lang):
        l_key = lang.lower()
        t = self.trans[l_key]

        # Обновляем текстовые метки настроек
        self.l_vol.setText(t["vol"])
        self.l_size.setText(t["font"])

        # Обновляем чекбокс и кнопку
        self.cb_overlay.setText(t["show"])
        self.cb_lock_overlay_move.setText(t["lock_move"])
        self.color_btn.setText(t["btn"])
        self.clock_font_label.setText(t["font_btn"])
        self._sync_color_btn_size()

        self.tabs.setTabText(0, t["main_tab"])
        self.tabs.setTabText(1, t["funding_tab"])
        self.funding_exchanges_label.setText(t["funding_exchanges"])
        self.funding_binance_check.setText(t["funding_binance"])
        self.funding_bybit_check.setText(t["funding_bybit"])
        self.funding_okx_check.setText(t["funding_okx"])
        self.funding_gate_check.setText(t["funding_gate"])
        self.funding_bitget_check.setText(t["funding_bitget"])
        self.funding_minutes_label.setText(t["funding_minutes"])
        self.funding_threshold_pos_label.setText(t["funding_threshold_pos"])
        self.funding_threshold_neg_label.setText(t["funding_threshold_neg"])
        self.funding_volume_label.setText(t["vol"])
        self.funding_log_label.setText(t["funding_log"])
        self.funding_log_upcoming_btn.setText(t["funding_upcoming"])
        self.funding_log_triggered_btn.setText(t["funding_triggered"])
        self.funding_refresh_btn.setText(t["funding_refresh"])
        self.funding_clear_btn.setText(t["funding_clear"])

        # Обновляем элементы режима
        self.overlay_mode_label.setText(t["mode"])
        self.overlay_mode_combo.blockSignals(True)
        current_idx = self.overlay_mode_combo.currentIndex()
        self.overlay_mode_combo.clear()
        self.overlay_mode_combo.addItems([t["always_show"], t["custom_windows"]])
        self.overlay_mode_combo.setCurrentIndex(current_idx)
        self.overlay_mode_combo.blockSignals(False)

        # Обновляем кнопку выбора приложений
        self.select_app_btn.setText(t["select_app"])

        # Пересоздаем виджеты таймфреймов с новым языком
        self.create_tf_widgets(l_key)

        # Переподключаем сигналы чекбоксов после пересоздания
        if self.main_window and hasattr(self.main_window, "reconnect_checkbox_signals"):
            self.main_window.reconnect_checkbox_signals()

    def mousePressEvent(self, event):
        """Начало перетаскивания окна"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        if self.old_pos and self.main_window:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.main_window.move(
                self.main_window.x() + delta.x(), self.main_window.y() + delta.y()
            )
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Окончание перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = None
            # Сохраняем позицию окна после перетаскивания
            if self.main_window and hasattr(self.main_window, "save_settings"):
                self.main_window.save_settings()

    def _card_style(self, padding="10px"):
        return f"QFrame {{ background: #161616; border-radius: 12px; border: 1px solid #252525; padding: {padding}; }}"

    def _tf_check_style(self):
        return """
            QCheckBox {{ 
                color: #bbb; 
                border: none; 
                spacing: 5px; 
            }} 
            QCheckBox::indicator {{ 
                width: 16px; 
                height: 16px; 
                border-radius: 4px;
                border: none;
                background: transparent;
                image: none;
            }} 
            QCheckBox::indicator:checked {{ 
                image: none;
            }}
            QCheckBox::indicator:unchecked {{
                background: transparent;
            }}
        """

    def _check_style(self):
        return f"QCheckBox {{ color: #bbb; border: none; spacing: 8px; }} QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid #333; border-radius: 4px; }} QCheckBox::indicator:checked {{ background: {config.COLORS['accent']}; }}"

    def _slider_style(self):
        return f"QSlider::groove:horizontal {{ background: #222; height: 6px; border-radius: 3px; }} QSlider::handle:horizontal {{ background: white; border: 2px solid {config.COLORS['accent']}; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}"

    def _btn_style(self):
        return f"QPushButton {{ color: {config.COLORS['accent']}; border: 2px solid {config.COLORS['accent']}; border-radius: 10px; font-weight: bold; padding: 5px; }} QPushButton:hover {{ background: {config.COLORS['accent']}; color: black; }}"

    def _color_btn_style(self):
        return f"QPushButton {{ color: {config.COLORS['accent']}; border: 2px solid {config.COLORS['accent']}; border-radius: 10px; font-weight: bold; padding: 0px; }} QPushButton:hover {{ background: {config.COLORS['accent']}; color: black; }}"

    def _select_app_style(self):
        fixed_blue = "#1e90ff"
        return f"QPushButton {{ color: {fixed_blue}; border: 2px solid {fixed_blue}; border-radius: 10px; font-weight: bold; padding: 5px; }} QPushButton:hover {{ background: {fixed_blue}; color: black; }}"

    def _combo_style(self):
        fixed_blue = "#1e90ff"
        return f"QComboBox {{ background: #1a1a1a; color: #888; border: 1px solid #333; border-radius: 6px; padding: 3px; font-size: 10px; margin-left: auto; margin-right: auto; }} QComboBox:hover {{ border: 1px solid {fixed_blue}; background: #202020; }} QComboBox::drop-down {{ border: none; }} QAbstractItemView {{ font-size: 10px; padding: 2px; }} QAbstractItemView::item {{ text-align: center; }} QComboBox QAbstractItemView::item {{ padding-left: 0px; padding-right: 0px; }}"

    def _input_style(self):
        return "QLineEdit { background: #1a1a1a; color: #888; border: 1px solid #333; border-radius: 6px; padding: 5px; }"

    def _list_style(self):
        return f"QListWidget {{ background: #1a1a1a; color: #bbb; border: 1px solid #333; border-radius: 6px; }} QListWidget::item:selected {{ background: {config.COLORS['accent']}; color: black; }} QListWidget::item {{ padding: 5px; }}"
