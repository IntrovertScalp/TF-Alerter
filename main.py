import sys
import datetime
import threading
import ctypes
import os
from collections import deque
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QHBoxLayout,
    QCheckBox,
    QListWidgetItem,
    QToolTip,
)
from PyQt6.QtGui import QColor, QIcon, QFont, QGuiApplication, QCursor
from PyQt6.QtCore import Qt, QSettings, QTimer, QEvent
import config
import gui
import logic
from hotkey_manager import HotkeyManager
from color_picker_dialog import ColorPickerDialog
from funding_alerts import FundingMonitor

# Установка App User Model ID для иконки на панели задач (Windows)
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "MyTradeTools.TF-Alerter"
    )
except Exception:
    pass

# Логирование
# Логирование - отключено для экономии памяти и ресурсов
LOG_ENABLED = False
LOG_FILE = "debug.log"


def log_write(msg):
    if not LOG_ENABLED:
        return
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except:
        pass


class MainWindow(QMainWindow):
    def __init__(self):
        # Чтобы иконка отображалась в панели задач Windows
        myappid = "mytrader.tfalerter.v1"
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        super().__init__()

        # Установка иконки для окна
        self.setWindowIcon(QIcon(config.LOGO_PATH))

        # Настройки окна (безрамочное)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(*config.WINDOW_SIZE)
        self.setWindowTitle("TF-Alerter")

        # Центральный виджет
        self.central_widget = QWidget()
        self.central_widget.setObjectName("mainContainer")  # Имя для точечного стиля
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # 1. Создаем заголовок
        self.title_bar = gui.CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)

        # 2. Создаем основной интерфейс
        self.ui = gui.UI_Widget(parent=self)
        self.main_layout.addWidget(self.ui)

        # 3. Инициализация логики
        self.logic = logic.AlerterLogic(self.ui)
        self.logic.time_signal.connect(self.ui.time_label.setText)

        # Funding alerts
        self.funding_monitor = FundingMonitor(self.ui)
        self.funding_monitor.alert_signal.connect(self.on_funding_alert)
        self.funding_monitor.log_signal.connect(self.append_funding_log_text)

        # Передаем ссылку на main_window в overlay для автосохранения
        self.logic.overlay.main_window = self

        # Переменная для перетаскивания окна
        self.old_pos = None

        # Флаг для отслеживания авторизованного сворачивания (через горячую клавишу)
        self._is_closing = False

        # Флаг для блокировки автосохранения во время загрузки
        self.loading_settings = True
        self.current_overlay_font = "Arial"
        self.overlay_bg_enabled = False
        self.overlay_bg_color = "#000000"
        self.overlay_move_locked = False
        self.funding_alert_counter = 0
        self.funding_alert_entries = []
        self.triggered_alerts = []  # Список завершённых алертов
        self.max_triggered_alerts = 10  # Максимум зачеркнутых алертов
        self._funding_log_view_mode = "upcoming"
        self._edge_tts_queue = []
        self._edge_tts_busy = False
        self._edge_tts_started = False
        self._last_funding_sound_duration_ms = 1700
        self._edge_ready_paths = deque()
        self._edge_ready_lock = threading.Lock()
        self._edge_ready_timer = QTimer()
        self._edge_ready_timer.setInterval(50)
        self._edge_ready_timer.timeout.connect(self._drain_edge_ready_paths)
        self._edge_ready_timer.start()
        self._pending_tts_entries = {}
        self._funding_tts_timer = QTimer()
        self._funding_tts_timer.setSingleShot(True)
        self._funding_tts_timer.timeout.connect(self._flush_funding_tts_queue)

        # --- ПОДКЛЮЧЕНИЕ СИГНАЛОВ ---
        self.ui.color_btn.clicked.connect(self.change_color)
        self.ui.clock_font_combo.currentTextChanged.connect(
            self.on_overlay_font_changed
        )
        self.ui.lang_sel.currentTextChanged.connect(self.ui.change_language)

        # Подключаем переключатель отображения часов
        self.ui.cb_overlay.toggled.connect(self.toggle_overlay)
        self.ui.cb_lock_overlay_move.toggled.connect(self.toggle_overlay_move_lock)

        # --- ПОДКЛЮЧЕНИЕ СИГНАЛОВ ДЛЯ УПРАВЛЕНИЯ OVERLAY ОКНАМИ ---
        self.ui.overlay_mode_combo.currentIndexChanged.connect(self.update_overlay_mode)
        self.ui.select_app_btn.clicked.connect(self.select_overlay_app)

        # Инициализация менеджера горячих клавиш
        self.hotkey_manager = HotkeyManager(self)
        self.hotkey_manager.hotkey_pressed.connect(self.toggle_minimize)
        self.hotkey_manager.start()

        # Загружаем настройки (это вызовет apply_interface_scale автоматически)
        self.load_settings()

        # Миграция звуков (только если еще не выполнена)
        settings = QSettings("MyTradeTools", "TF-Alerter")
        if not settings.value("sounds_migrated", False, type=bool):
            try:
                config.migrate_sounds_to_subdirs()
                settings.setValue("sounds_migrated", True)
            except Exception:
                pass

        # Re-apply accent-based styles to already-created widgets
        try:
            fixed_blue = "#1e90ff"
            # Title label
            if hasattr(self, "title_bar") and hasattr(self.title_bar, "title_label"):
                self.title_bar.title_label.setStyleSheet(
                    f"color: {fixed_blue}; font-family: 'Segoe UI Semibold'; font-size: 12px; letter-spacing: 2px; background: transparent; border: none;"
                )
            # Main UI buttons
            if hasattr(self, "ui"):
                try:
                    if hasattr(self.ui, "select_app_btn"):
                        self.ui.select_app_btn.setStyleSheet(
                            self.ui._select_app_style()
                        )
                except Exception:
                    pass
        except Exception:
            pass

        # Теперь подключаем автосохранение ПОСЛЕ загрузки
        self.ui.volume_slider.valueChanged.connect(self.save_settings)
        self.ui.ov_size_slider.valueChanged.connect(self.save_settings)
        self.ui.lang_sel.currentTextChanged.connect(self.save_settings)
        self.ui.cb_overlay.toggled.connect(self.save_settings)
        self.ui.cb_lock_overlay_move.toggled.connect(self.save_settings)
        self.ui.funding_binance_check.toggled.connect(self.on_funding_exchanges_changed)
        self.ui.funding_bybit_check.toggled.connect(self.on_funding_exchanges_changed)
        self.ui.funding_okx_check.toggled.connect(self.on_funding_exchanges_changed)
        self.ui.funding_gate_check.toggled.connect(self.on_funding_exchanges_changed)
        self.ui.funding_bitget_check.toggled.connect(self.on_funding_exchanges_changed)
        self.ui.funding_enable_check.toggled.connect(self.on_funding_enable_toggled)
        self.ui.funding_minutes_edit.textChanged.connect(self.save_settings)
        self.ui.funding_threshold_pos_edit.textChanged.connect(self.save_settings)
        self.ui.funding_threshold_neg_edit.textChanged.connect(self.save_settings)
        self.ui.funding_volume_slider.valueChanged.connect(self.save_settings)
        self.ui.funding_clear_btn.clicked.connect(self.clear_funding_log)
        self.ui.funding_refresh_btn.clicked.connect(self.refresh_funding_data)
        self.ui.funding_log_upcoming_btn.clicked.connect(
            lambda: self.set_funding_log_view_mode("upcoming")
        )
        self.ui.funding_log_triggered_btn.clicked.connect(
            lambda: self.set_funding_log_view_mode("triggered")
        )
        self.ui.funding_log_list.itemClicked.connect(self.copy_funding_symbol)

        # Подключаем автосохранение для галочек таймфреймов
        self.reconnect_checkbox_signals()

        # Разрешаем сохранение
        self.loading_settings = False

        # Запускаем таймеры часов и логики алертов
        self.logic.timer.start(1000)  # Основная логика каждую секунду
        self.logic.overlay_update_timer.start()  # Обновление часов каждые 100мс

        # Запускаем funding monitor только если фандинг включен
        if self.ui.funding_enable_check.isChecked():
            self.funding_monitor.start()

        # Таймер для обновления логов фандинга каждую секунду
        self.funding_log_timer = QTimer()
        self.funding_log_timer.timeout.connect(self._update_funding_log_realtime)
        self.funding_log_timer.start(1000)  # Каждую секунду

        # Устанавливаем eventFilter для снятия выделения
        self.ui.funding_log_list.installEventFilter(self)
        self.ui.funding_minutes_edit.installEventFilter(self)
        self.ui.funding_threshold_pos_edit.installEventFilter(self)
        self.ui.funding_threshold_neg_edit.installEventFilter(self)

    def _tf_registry_key(self, tf):
        # Windows registry value names are case-insensitive, so 1m and 1M collide.
        return "tf_1mo" if tf == "1M" else f"tf_{tf}"

    def eventFilter(self, obj, event):
        """Перехватываем события для снятия выделения"""
        # ESC и Enter снимают выделение
        if event.type() == QEvent.Type.KeyPress:
            if (
                event.key() == Qt.Key.Key_Escape
                or event.key() == Qt.Key.Key_Return
                or event.key() == Qt.Key.Key_Enter
            ):
                if obj == self.ui.funding_log_list:
                    self.ui.funding_log_list.clearSelection()
                    return True
                elif obj in [
                    self.ui.funding_minutes_edit,
                    self.ui.funding_threshold_pos_edit,
                    self.ui.funding_threshold_neg_edit,
                ]:
                    obj.clearFocus()
                    obj.deselect()
                    return True

        # Клик вне элемента снимает выделение
        if event.type() == QEvent.Type.FocusOut:
            if obj in [
                self.ui.funding_minutes_edit,
                self.ui.funding_threshold_pos_edit,
                self.ui.funding_threshold_neg_edit,
            ]:
                obj.deselect()

        return super().eventFilter(obj, event)

    def reconnect_checkbox_signals(self):
        """Переподключает все чекбоксы таймфреймов к save_settings"""
        log_write("[RECONNECT] Переподключение сигналов чекбоксов...")
        for tf, cb in self.ui.checkboxes.items():
            # Подключаем только один раз на экземпляр чекбокса
            if not getattr(cb, "_save_signal_connected", False):
                cb.stateChanged.connect(self.save_settings)
                cb._save_signal_connected = True
            log_write(f"[RECONNECT]   tf_{tf}: сигнал переподключен")

    def toggle_overlay(self, state):
        """Метод управления видимостью оверлея"""
        if state:
            self.logic.overlay.show()
        else:
            self.logic.overlay.hide()

    def update_overlay_mode(self, mode_index):
        """Обновляет режим отображения overlay"""
        if self.loading_settings:
            return
        # 0 = "Всегда показывать" / "Always Show" → "always"
        # 1 = "Только на определённых окнах" / "Only on Specific Windows" → "custom"
        overlay_mode = "always" if mode_index == 0 else "custom"
        settings = QSettings("MyTradeTools", "TF-Alerter")
        settings.setValue("overlay_show_mode", overlay_mode)
        config.OVERLAY_SHOW_MODE = overlay_mode
        self.save_settings()

    def select_overlay_app(self):
        """Простой диалог для выбора приложений для Overlay"""
        from PyQt6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QListWidget,
            QPushButton,
            QLabel,
            QLineEdit,
            QListWidgetItem,
            QCompleter,
            QWidget,
            QCheckBox,
        )
        from PyQt6.QtCore import Qt, QSize, QSettings
        from PyQt6.QtGui import QColor

        # Переводы
        translations = {
            "RU": {
                "title": "Добавить приложение для Overlay",
                "info": "Выберите приложения, на которых должен отображаться overlay:",
                "placeholder": "Название приложения точно как в панели задач",
                "add_btn": "+ Добавить",
                "select_all": "✓ Всё",
                "clear_all": "✗ Ничего",
                "cancel": "✗ Отмена",
                "save": "✓ Сохранить",
            },
            "EN": {
                "title": "Add Application for Overlay",
                "info": "Select applications where the overlay should be displayed:",
                "placeholder": "Application name exactly as in taskbar",
                "add_btn": "+ Add",
                "select_all": "✓ All",
                "clear_all": "✗ None",
                "cancel": "✗ Cancel",
                "save": "✓ Save",
            },
        }

        # Получаем текущий язык
        settings = QSettings("MyTradeTools", "TF-Alerter")
        current_lang = settings.value("language", "RU")
        t = translations[current_lang]

        # Получаем список открытых окон
        all_open_apps = list(self.get_open_windows())

        # Загружаем историю всех добавленных приложений
        settings = QSettings("MyTradeTools", "TF-Alerter")
        overlay_all = settings.value("overlay_windows_all", [])
        if not isinstance(overlay_all, list):
            overlay_all = []

        # Добавляем уже добавленные приложения если их нет в списке
        for app in config.OVERLAY_WINDOWS:
            if app not in all_open_apps:
                all_open_apps.insert(0, app)

        # Добавляем исторические приложения
        for app in overlay_all:
            if app not in all_open_apps:
                all_open_apps.append(app)

        dialog = QDialog(self)
        dialog.setWindowTitle(t["title"])
        dialog.setGeometry(self.x() + 100, self.y() + 100, 550, 400)

        # Use a fixed dialog accent (blue) for this dialog's controls regardless of global clock color
        dialog_accent = "#1e90ff"
        # Стилизация диалога и явное переопределение highlight/selection цветов на dialog_accent
        dialog.setStyleSheet(
            f"QDialog {{ background-color: {config.COLORS['background']}; }} "
            f"QLabel {{ color: #aaa; }} "
            f"QLineEdit {{ background: #1a1a1a; color: #bbb; border: 1px solid #333; border-radius: 6px; padding: 5px; }}"
            f" QPushButton.add {{ color: {dialog_accent}; border: 1px solid {dialog_accent}; }}"
        )

        # Устанавливаем палитру highlight (выделение) в цвет accent, чтобы системные стилей не показывали зелёный
        from PyQt6.QtGui import QPalette

        pal = dialog.palette()
        pal.setColor(QPalette.ColorRole.Highlight, QColor(dialog_accent))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
        dialog.setPalette(pal)

        layout = QVBoxLayout()

        # Инструкция
        info_label = QLabel(t["info"])
        info_label.setStyleSheet("color: #aaa; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Поле для ввода приложения вручную
        search_layout = QHBoxLayout()
        search_input = QLineEdit()
        search_input.setPlaceholderText(t["placeholder"])

        # Добавляем автодополнение
        completer = QCompleter(sorted(set(all_open_apps)))
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        search_input.setCompleter(completer)

        search_layout.addWidget(search_input)

        # Кнопка добавить вручную
        add_custom_btn = QPushButton(t["add_btn"])
        add_custom_btn.setStyleSheet(
            f"QPushButton {{ color: {dialog_accent}; border: 1px solid {dialog_accent}; border-radius: 5px; background: transparent; padding: 5px; }} "
            f"QPushButton:hover {{ background: #333; }}"
        )
        add_custom_btn.setMaximumWidth(100)
        search_layout.addWidget(add_custom_btn)
        layout.addLayout(search_layout)

        # Список приложений с чекбоксами
        app_list = QListWidget()
        # Removed explicit border to avoid broken/discontinuous outline; rely on dialog/frame border
        app_list.setStyleSheet(
            f"QListWidget {{ background: #1a1a1a; color: #bbb; border: none; border-radius: 6px; }} "
            f"QListWidget::item {{ padding: 6px 5px; margin: 1px 0px; border-radius: 4px; }} "
            f"QListWidget::item:selected {{ background: transparent; color: #bbb; }} "
            f"QListWidget::item:focus {{ outline: none; border: none; }}"
        )
        app_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Устанавливаем максимальную высоту с возможностью прокрутки
        app_list.setMaximumHeight(240)
        app_list.setMinimumHeight(90)

        # Заполняем список с кастомными виджетами
        def create_app_item_widget(app_name, is_checked):
            """Создает кастомный виджет для элемента списка"""
            from PyQt6.QtGui import QPainter, QFont, QPen, QColor
            from PyQt6.QtCore import QRect

            container = QWidget()
            container_layout = QHBoxLayout()
            container_layout.setContentsMargins(5, 4, 4, 8)
            container_layout.setSpacing(8)

            # Создаём кастомный чекбокс с рисованием
            class CustomCheckBox(QCheckBox):
                # Кэш шрифтов для оптимизации памяти
                _font_cache = {}

                @classmethod
                def get_font(cls, family, size, weight=None):
                    """Возвращает закэшированный шрифт"""
                    key = (family, size, weight)
                    if key not in cls._font_cache:
                        font = QFont(family, size)
                        if weight:
                            font.setWeight(weight)
                        cls._font_cache[key] = font
                    return cls._font_cache[key]

                def paintEvent(self, event):
                    painter = QPainter(self)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

                    # Очищаем фон
                    painter.fillRect(self.rect(), QColor("#1e1e1e"))

                    # Рисуем квадрат для чекбокса (опущен чуть ниже, чтобы не обрезаться снизу)
                    checkbox_rect = QRect(2, 10, 16, 16)

                    if self.isChecked():
                        # Синий фон с полной заливкой
                        painter.fillRect(checkbox_rect, QColor("#1e90ff"))
                        painter.setPen(QPen(QColor("#1e90ff"), 1))
                        painter.drawRect(checkbox_rect)

                        # Чёрная галочка (используем закэшированный шрифт)
                        painter.setPen(QPen(QColor("#000000"), 2))
                        painter.setFont(self.get_font("Arial", 9, QFont.Weight.Bold))
                        painter.drawText(
                            checkbox_rect, Qt.AlignmentFlag.AlignCenter, "✓"
                        )
                    else:
                        # Синяя граница с прозрачным фоном
                        painter.fillRect(checkbox_rect, QColor("#1a1a1a"))
                        painter.setPen(QPen(QColor("#1e90ff"), 2))
                        painter.drawRect(checkbox_rect)

                    # Текст (используем закэшированный шрифт)
                    painter.setPen(QColor("#ffffff"))
                    painter.setFont(self.get_font("Arial", 10))
                    text_rect = QRect(25, 8, self.width() - 30, 24)
                    painter.drawText(
                        text_rect,
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter,
                        self.text(),
                    )
                    painter.end()

            checkbox = CustomCheckBox(app_name)
            checkbox.setMaximumHeight(42)
            checkbox.setMinimumHeight(40)
            checkbox.setChecked(is_checked)
            container_layout.addWidget(checkbox)

            # Кнопка удаления
            delete_btn = QPushButton("✕")
            delete_btn.setMaximumWidth(30)
            delete_btn.setStyleSheet(
                f"QPushButton {{ color: {config.COLORS['danger']}; border: 1px solid {config.COLORS['danger']}; border-radius: 4px; background: transparent; padding: 2px; }} "
                f"QPushButton:hover {{ background: #333; }}"
            )

            def delete_item():
                # 找到这个widget在列表中的位置并删除
                for i in range(app_list.count()):
                    item = app_list.item(i)
                    if app_list.itemWidget(item) == container:
                        app_list.takeItem(i)
                        break

            delete_btn.clicked.connect(delete_item)
            container_layout.addWidget(delete_btn)

            container.setLayout(container_layout)
            return container, checkbox

        def add_app_item(app_name, is_checked):
            item = QListWidgetItem()
            item.setSizeHint(QSize(450, 46))
            app_list.addItem(item)
            widget, checkbox = create_app_item_widget(app_name, is_checked)
            widget.checkbox = checkbox
            item.data_checkbox = checkbox  # Store reference
            app_list.setItemWidget(item, widget)

        # Заполняем список
        for app in sorted(set(all_open_apps)):
            is_checked = app in config.OVERLAY_WINDOWS
            add_app_item(app, is_checked)

        layout.addWidget(app_list)

        def add_custom_app():
            text = search_input.text().strip()
            if text and len(text) > 0:
                # Проверяем что такого приложения еще нет
                found = False
                for i in range(app_list.count()):
                    item = app_list.item(i)
                    widget = app_list.itemWidget(item) if item else None
                    if widget and hasattr(widget, "checkbox"):
                        if widget.checkbox.text() == text:
                            # Уже есть, просто отмечаем галочкой
                            widget.checkbox.setChecked(True)
                            search_input.clear()
                            found = True
                            break

                if not found:
                    # Добавляем новый элемент с сохранением сортировки
                    insert_pos = app_list.count()
                    for i in range(app_list.count()):
                        item = app_list.item(i)
                        widget = app_list.itemWidget(item) if item else None
                        if widget and hasattr(widget, "checkbox"):
                            if widget.checkbox.text().lower() > text.lower():
                                insert_pos = i
                                break

                    item = QListWidgetItem()
                    item.setSizeHint(QSize(450, 46))
                    if insert_pos >= app_list.count():
                        app_list.addItem(item)
                    else:
                        app_list.insertItem(insert_pos, item)

                    item_widget, checkbox = create_app_item_widget(text, True)
                    item_widget.checkbox = checkbox
                    app_list.setItemWidget(item, item_widget)
                    search_input.clear()

        add_custom_btn.clicked.connect(add_custom_app)
        # Нажатие Enter в поле поиска тоже добавляет
        search_input.returnPressed.connect(add_custom_app)

        # Кнопки выбора
        btn_layout = QHBoxLayout()

        select_all_btn = QPushButton(t["select_all"])
        select_all_btn.setStyleSheet(
            f"QPushButton {{ color: {dialog_accent}; border: 1px solid {dialog_accent}; border-radius: 5px; background: transparent; padding: 5px; }} "
            f"QPushButton:hover {{ background: #333; }}"
        )
        select_all_btn.setMaximumWidth(60)

        def select_all():
            for i in range(app_list.count()):
                item = app_list.item(i)
                widget = app_list.itemWidget(item) if item else None
                if widget and hasattr(widget, "checkbox"):
                    widget.checkbox.setChecked(True)

        select_all_btn.clicked.connect(select_all)
        btn_layout.addWidget(select_all_btn)

        clear_all_btn = QPushButton(t["clear_all"])
        clear_all_btn.setStyleSheet(
            f"QPushButton {{ color: {config.COLORS['danger']}; border: 1px solid {config.COLORS['danger']}; border-radius: 5px; background: transparent; padding: 5px; }} "
            f"QPushButton:hover {{ background: #333; }}"
        )
        clear_all_btn.setMinimumWidth(100)

        def clear_all():
            for i in range(app_list.count()):
                item = app_list.item(i)
                widget = app_list.itemWidget(item) if item else None
                if widget and hasattr(widget, "checkbox"):
                    widget.checkbox.setChecked(False)

        clear_all_btn.clicked.connect(clear_all)
        btn_layout.addWidget(clear_all_btn)

        btn_layout.addStretch()

        # ОТМЕНА - идет ПЕРВОЙ (переставлена местами)
        cancel_btn = QPushButton(t["cancel"])
        cancel_btn.setStyleSheet(
            "QPushButton { color: #666; border: 1px solid #444; border-radius: 6px; padding: 6px 15px; } "
            "QPushButton:hover { background: #333; }"
        )
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        # СОХРАНИТЬ - идет ВТОРОЙ (переставлена местами)
        ok_btn = QPushButton(t["save"])
        ok_btn.setStyleSheet(
            f"QPushButton {{ color: {dialog_accent}; border: 2px solid {dialog_accent}; border-radius: 6px; font-weight: bold; padding: 6px 15px; }} "
            f"QPushButton:hover {{ background: {dialog_accent}; color: black; }}"
        )
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        def on_save():
            config.OVERLAY_WINDOWS.clear()
            overlay_all = []

            for i in range(app_list.count()):
                item = app_list.item(i)
                widget = app_list.itemWidget(item) if item else None
                if widget and hasattr(widget, "checkbox"):
                    app_name = widget.checkbox.text()
                    overlay_all.append(app_name)  # Сохраняем все
                    if widget.checkbox.isChecked():
                        config.OVERLAY_WINDOWS.append(
                            app_name
                        )  # Добавляем только отмеченные

            # Сохраняем историю всех приложений
            settings = QSettings("MyTradeTools", "TF-Alerter")
            settings.setValue("overlay_windows_all", overlay_all)

            self.update_config_overlay_windows()
            self.save_settings()
            dialog.accept()

        ok_btn.clicked.connect(on_save)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def get_open_windows(self):
        """Получает список открытых окон Windows"""
        try:
            import ctypes
            from ctypes import wintypes

            open_apps = []

            # Используем более безопасный способ перечисления окон
            EnumWindows = ctypes.windll.user32.EnumWindows
            GetWindowTextLength = ctypes.windll.user32.GetWindowTextLength
            GetWindowTextW = ctypes.windll.user32.GetWindowTextW
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            # Определяем callback функцию
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, wintypes.HWND, wintypes.LPARAM
            )

            def enum_callback(hwnd, lparam):
                try:
                    if IsWindowVisible(hwnd):
                        length = GetWindowTextLength(hwnd)
                        if length > 0:
                            buf = ctypes.create_unicode_buffer(length + 1)
                            GetWindowTextW(hwnd, buf, length + 1)
                            text = buf.value.strip()
                            if text and len(text) > 0:
                                # Не добавляем системные окна
                                if not text.startswith("Default IME"):
                                    open_apps.append(text)
                except Exception as e:
                    pass
                return True

            # Вызываем EnumWindows с callback
            callback = WNDENUMPROC(enum_callback)
            result = EnumWindows(callback, 0)

            # Удаляем дубликаты и сортируем
            unique_apps = sorted(list(set(open_apps)))
            return unique_apps

        except Exception as e:
            # Если что-то пошло не так, возвращаем пустой список
            return []

    def update_config_overlay_windows(self):
        """Обновляет конфиг с текущим списком приложений"""
        settings = QSettings("MyTradeTools", "TF-Alerter")
        settings.setValue("overlay_windows", config.OVERLAY_WINDOWS)

    def open_about(self):
        """Открывает окно 'О программе'"""
        from about_dialog import AboutDialog

        dialog = AboutDialog(self)
        dialog.exec()

    def open_donate(self):
        """Открывает окно 'Поддержать проект'"""
        from donate_dialog import DonateDialog

        dialog = DonateDialog(self)
        dialog.exec()

    def open_settings(self):
        """Открывает окно настроек"""
        from settings_dialog import SettingsDialog

        dialog = SettingsDialog(self)
        dialog.exec()

        # Восстанавливаем hotkey после закрытия диалога
        settings = QSettings("MyTradeTools", "TF-Alerter")
        hotkey = settings.value("hotkey", "")
        hotkey_codes = settings.value("hotkey_codes", "")
        invalid_hotkeys = ["", "Нажмите клавишу...", "Не задана"]
        if hotkey and hotkey not in invalid_hotkeys:
            codes = None
            if hotkey_codes:
                try:
                    codes = [
                        int(x)
                        for x in str(hotkey_codes).split(",")
                        if x.strip().isdigit()
                    ]
                except Exception:
                    codes = None
            if codes:
                self.hotkey_manager.register_hotkey_codes(codes, hotkey)

    def toggle_minimize(self):
        """Сворачивает/разворачивает окно по горячей клавише"""
        if self.windowState() & Qt.WindowState.WindowMinimized:
            # Используем Windows API для надежного восстановления
            hwnd = int(self.winId())

            # Константы Windows API
            SW_RESTORE = 9
            SW_SHOW = 5
            SW_SHOWNORMAL = 1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            HWND_TOP = 0

            # Получаем foreground поток
            foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
            foreground_thread = ctypes.windll.user32.GetWindowThreadProcessId(
                foreground_hwnd, None
            )
            current_thread = ctypes.windll.kernel32.GetCurrentThreadId()

            # Присоединяем потоки для обхода ограничений SetForegroundWindow
            if foreground_thread != current_thread:
                ctypes.windll.user32.AttachThreadInput(
                    foreground_thread, current_thread, True
                )

            try:
                # Восстанавливаем окно (несколько вызовов для надежности)
                ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
                ctypes.windll.user32.ShowWindow(hwnd, SW_SHOWNORMAL)
                ctypes.windll.user32.SetWindowPos(
                    hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE
                )
                ctypes.windll.user32.SetForegroundWindow(hwnd)
                ctypes.windll.user32.BringWindowToTop(hwnd)
                ctypes.windll.user32.SetActiveWindow(hwnd)
                ctypes.windll.user32.SetFocus(hwnd)
            finally:
                # Отсоединяем потоки
                if foreground_thread != current_thread:
                    ctypes.windll.user32.AttachThreadInput(
                        foreground_thread, current_thread, False
                    )

            # Дополнительно активируем через Qt
            self.setWindowState(Qt.WindowState.WindowNoState)
            self.activateWindow()
            self.raise_()
            self.show()
        else:
            self.request_minimize()

    def refresh_funding_data(self):
        """Принудительно обновляет данные фандинга"""
        if hasattr(self, "funding_monitor"):
            if hasattr(self.funding_monitor, "clear_cache"):
                self.funding_monitor.clear_cache()
            # Останавливаем таймер и запускаем poll немедленно
            self.funding_monitor.timer.stop()
            self.funding_monitor.poll()

    def on_funding_enable_toggled(self, checked):
        """Обработка вкл/выкл фандинга: затемняет/осветляет интерфейс"""
        self.ui.funding_content_widget.setEnabled(checked)

        # Изменяем прозрачность контента для визуального эффекта
        if checked:
            self.ui.funding_opacity_effect.setOpacity(1.0)  # Полная яркость
            if hasattr(self, "funding_monitor") and hasattr(
                self.funding_monitor, "clear_cache"
            ):
                self.funding_monitor.clear_cache()
            self.funding_monitor.start()
        else:
            self.ui.funding_opacity_effect.setOpacity(0.3)  # Затемнение
            self.funding_monitor.stop()
            self._stop_funding_audio(tts_only=False)

        self.save_settings()

    def on_funding_exchanges_changed(self, *args):
        if self.loading_settings:
            return

        if hasattr(self, "funding_monitor") and hasattr(
            self.funding_monitor, "clear_cache"
        ):
            self.funding_monitor.clear_cache()

        self.funding_alert_entries = []
        self.triggered_alerts = []
        self._pending_tts_entries = {}
        self.ui.funding_log_list.clear()

        if self.ui.funding_enable_check.isChecked() and hasattr(
            self, "funding_monitor"
        ):
            self.funding_monitor.timer.stop()
            self.funding_monitor.poll()

        self.save_settings()

    def request_minimize(self):
        """Сворачивает окно."""
        self.showMinimized()

    def apply_interface_scale(self, scale_text):
        """Метод масштабирования без дрожания"""
        self.setUpdatesEnabled(False)
        try:
            value = int(scale_text.replace("%", ""))
            factor = value / 100.0

            # 1. Глобальный шрифт
            font = QApplication.font()
            font.setPointSize(int(10 * factor))
            QApplication.setFont(font)

            # 2. Размер окна
            self.setFixedSize(
                int(config.WINDOW_SIZE[0] * factor),
                int(config.WINDOW_SIZE[1] * factor),
            )

            # 3. Принудительно увеличиваем кнопки (чтобы текст не заходил под них)
            self.ui.color_btn.setFixedSize(int(125 * factor), int(38 * factor))
            self.ui.clock_font_combo.setMinimumWidth(int(170 * factor))
            self.ui.lang_sel.setFixedSize(int(65 * factor), int(28 * factor))

            # 4. Стили контейнера
            self.central_widget.setStyleSheet(
                f"#mainContainer {{ background-color: {config.COLORS['background']}; "
                f"border: 2px solid {config.COLORS['border']}; border-radius: {int(15 * factor)}px; }}"
            )

            # 5. Шапка
            if hasattr(self, "title_bar"):
                self.title_bar.setFixedHeight(int(40 * factor))
                for btn in self.title_bar.findChildren(QPushButton):
                    btn.setFixedSize(int(45 * factor), int(40 * factor))

            # 6. Масштабируем комбобокс режима оверлея
            if hasattr(self.ui, "overlay_mode_combo"):
                self.ui.overlay_mode_combo.setMinimumWidth(int(260 * factor))

        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def save_settings(self, *args):
        """Сохраняет всё в память Windows (реестр)"""
        # Не сохраняем во время загрузки
        if hasattr(self, "loading_settings") and self.loading_settings:
            return

        settings = QSettings("MyTradeTools", "TF-Alerter")
        settings.setValue("volume", self.ui.volume_slider.value())
        settings.setValue("overlay_active", self.ui.cb_overlay.isChecked())
        settings.setValue("overlay_size", self.ui.ov_size_slider.value())
        settings.setValue("language", self.ui.lang_sel.currentText())
        settings.setValue("overlay_pos", self.logic.overlay.pos())
        settings.setValue("window_pos", self.pos())
        settings.setValue("accent_color", config.COLORS["accent"])
        settings.setValue("accent_alpha", config.COLORS.get("accent_alpha", 255))
        settings.setValue(
            "overlay_font_family",
            (self.current_overlay_font or "").strip() or "Arial",
        )
        settings.setValue("overlay_bg_enabled", bool(self.overlay_bg_enabled))
        settings.setValue("overlay_bg_color", self.overlay_bg_color or "#000000")
        settings.setValue(
            "overlay_move_locked", self.ui.cb_lock_overlay_move.isChecked()
        )
        settings.setValue(
            "funding_binance_enabled", self.ui.funding_binance_check.isChecked()
        )
        settings.setValue(
            "funding_bybit_enabled", self.ui.funding_bybit_check.isChecked()
        )
        settings.setValue("funding_okx_enabled", self.ui.funding_okx_check.isChecked())
        settings.setValue(
            "funding_gate_enabled", self.ui.funding_gate_check.isChecked()
        )
        settings.setValue(
            "funding_bitget_enabled", self.ui.funding_bitget_check.isChecked()
        )
        settings.setValue("funding_enabled", self.ui.funding_enable_check.isChecked())
        settings.setValue(
            "funding_minutes", self.ui.funding_minutes_edit.text().strip()
        )
        settings.setValue(
            "funding_threshold_pos",
            self.ui.funding_threshold_pos_edit.text().strip(),
        )
        settings.setValue(
            "funding_threshold_neg",
            self.ui.funding_threshold_neg_edit.text().strip(),
        )
        settings.setValue("funding_volume", self.ui.funding_volume_slider.value())

        # Сохраняем режим и список приложений для overlay
        settings.setValue("overlay_show_mode", config.OVERLAY_SHOW_MODE)
        settings.setValue("overlay_windows", config.OVERLAY_WINDOWS)

        # Сохраняем состояния таймфреймов напрямую через winreg (без открытия консоли)
        import winreg

        try:
            hkey = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\MyTradeTools\TF-Alerter",
                0,
                winreg.KEY_SET_VALUE,
            )
            for tf, cb in self.ui.checkboxes.items():
                val = "Y" if cb.isChecked() else "N"
                key_name = self._tf_registry_key(tf)
                winreg.SetValueEx(hkey, key_name, 0, winreg.REG_SZ, val)
                log_write(f"[SAVE] {key_name} = {val} (checked={cb.isChecked()})")
            winreg.CloseKey(hkey)
            log_write("[SAVE] Значения записаны через winreg")
        except Exception as e:
            log_write(f"[SAVE] Ошибка при записи через winreg: {e}")
            # Fallback на QSettings
            for tf, cb in self.ui.checkboxes.items():
                val = "Y" if cb.isChecked() else "N"
                settings.setValue(self._tf_registry_key(tf), val)

        settings.sync()
        log_write("[SAVE] settings.sync() called")

    def load_settings(self):
        """Загружает всё из памяти при запуске"""
        settings = QSettings("MyTradeTools", "TF-Alerter")

        # 1. Загружаем Язык первым!
        saved_lang = settings.value("language", "RU")
        self.ui.lang_sel.setCurrentText(saved_lang)
        self.ui.change_language(saved_lang)

        # 2. Загружаем Масштаб
        scale_txt = settings.value("interface_scale_text", "100%")
        self.apply_interface_scale(scale_txt)

        # 3. Остальные настройки
        vol = int(settings.value("volume", 80))
        self.ui.volume_slider.setValue(vol)

        is_ov_active = settings.value("overlay_active", False, type=bool)
        self.ui.cb_overlay.setChecked(is_ov_active)
        # Если чекбокс выключен — скрываем оверлей сразу
        if is_ov_active:
            self.logic.overlay.show()
        else:
            self.logic.overlay.hide()

        size = int(settings.value("overlay_size", 40))
        self.ui.ov_size_slider.setValue(size)

        saved_color = settings.value("accent_color", config.COLORS["accent"])
        saved_alpha = int(settings.value("accent_alpha", 255))
        saved_font = settings.value("overlay_font_family", "Arial")
        if not isinstance(saved_font, str) or not saved_font.strip():
            saved_font = "Arial"
        self.current_overlay_font = saved_font
        self.ui.clock_font_combo.setCurrentFont(QFont(saved_font))

        self.overlay_bg_enabled = settings.value("overlay_bg_enabled", False, type=bool)
        saved_bg_color = settings.value("overlay_bg_color", "#000000")
        if not isinstance(saved_bg_color, str) or not saved_bg_color.strip():
            saved_bg_color = "#000000"
        self.overlay_bg_color = saved_bg_color

        self.overlay_move_locked = settings.value(
            "overlay_move_locked", False, type=bool
        )
        self.ui.cb_lock_overlay_move.setChecked(self.overlay_move_locked)
        self.logic.overlay.move_locked = self.overlay_move_locked

        self.ui.funding_binance_check.setChecked(
            settings.value("funding_binance_enabled", True, type=bool)
        )
        self.ui.funding_bybit_check.setChecked(
            settings.value("funding_bybit_enabled", True, type=bool)
        )
        self.ui.funding_okx_check.setChecked(
            settings.value("funding_okx_enabled", True, type=bool)
        )
        self.ui.funding_gate_check.setChecked(
            settings.value("funding_gate_enabled", True, type=bool)
        )
        self.ui.funding_bitget_check.setChecked(
            settings.value("funding_bitget_enabled", True, type=bool)
        )
        funding_enabled = settings.value("funding_enabled", True, type=bool)
        self.ui.funding_enable_check.setChecked(funding_enabled)
        self.ui.funding_content_widget.setEnabled(funding_enabled)

        # Устанавливаем прозрачность в зависимости от состояния
        if funding_enabled:
            self.ui.funding_opacity_effect.setOpacity(1.0)
        else:
            self.ui.funding_opacity_effect.setOpacity(0.3)

        self.ui.funding_minutes_edit.setText(settings.value("funding_minutes", "15,5"))

        threshold_legacy = settings.value("funding_threshold", "")
        self.ui.funding_threshold_pos_edit.setText(
            settings.value("funding_threshold_pos", threshold_legacy or "0")
        )
        self.ui.funding_threshold_neg_edit.setText(
            settings.value("funding_threshold_neg", threshold_legacy or "0")
        )
        funding_vol = int(settings.value("funding_volume", 80))
        self.ui.funding_volume_slider.setValue(funding_vol)

        config.COLORS["accent"] = saved_color
        config.COLORS["accent_alpha"] = saved_alpha
        self.logic.overlay.update_style(
            saved_color,
            size,
            saved_alpha,
            saved_font,
            self.overlay_bg_enabled,
            self.overlay_bg_color,
        )

        pos = settings.value("overlay_pos")
        if pos:
            self.logic.overlay.move(pos)

        # Загружаем режим отображения overlay и список приложений
        overlay_mode = settings.value("overlay_show_mode", "custom")
        config.OVERLAY_SHOW_MODE = overlay_mode
        # Используем индекс вместо текста: 0 = "always", 1 = "custom"
        mode_index = 0 if overlay_mode == "always" else 1
        self.ui.overlay_mode_combo.setCurrentIndex(mode_index)

        overlay_windows = settings.value("overlay_windows", config.OVERLAY_WINDOWS)
        if isinstance(overlay_windows, str):
            # Конвертируем строку в список если нужно
            overlay_windows = overlay_windows.split(", ") if overlay_windows else []
        elif not isinstance(overlay_windows, list):
            overlay_windows = []

        config.OVERLAY_WINDOWS = overlay_windows

        # Загружаем звуки для каждого таймфрейма
        # ВАЖНО: каждый таймфрейм загружается ОТДЕЛЬНО, без связи с другими
        for tf_key in config.TIMEFRAMES.keys():
            # Используем разные имена для 1M в QSettings (1Month вместо 1M)
            # чтобы избежать case-insensitive конфликтов в Windows реестре
            qsettings_key = tf_key.replace("1M", "1Month") if tf_key == "1M" else tf_key

            # Читаем ОТДЕЛЬНО для каждого tf_key
            main_sound = settings.value(f"sound_main_{qsettings_key}")
            tick_sound = settings.value(f"sound_tick_{qsettings_key}")
            transition_sound = settings.value(f"sound_transition_{qsettings_key}")

            # Если не найдено в QSettings, используем значение по умолчанию из config
            if not main_sound:
                main_sound = config.TIMEFRAMES[tf_key]["file"]
            if not tick_sound:
                tick_sound = config.SOUND_TICK_BY_TF.get(tf_key)
            if not transition_sound:
                transition_sound = config.SOUND_TRANSITION_BY_TF.get(tf_key)

            # Обновляем config БЕЗ проверки существования
            # (проверка будет при попытке воспроизведения в logic.play_voice)
            if isinstance(main_sound, str) and main_sound:
                config.TIMEFRAMES[tf_key]["file"] = main_sound

            if isinstance(tick_sound, str) and tick_sound:
                config.SOUND_TICK_BY_TF[tf_key] = tick_sound

            if isinstance(transition_sound, str) and transition_sound:
                config.SOUND_TRANSITION_BY_TF[tf_key] = transition_sound

        # Загружаем позицию главного окна
        window_pos = settings.value("window_pos")
        if window_pos:
            self.move(window_pos)

        # Загружаем и регистрируем горячую клавишу
        hotkey = settings.value("hotkey", "")
        hotkey_codes = settings.value("hotkey_codes", "")
        # Игнорируем placeholder текст и невалидные значения
        invalid_hotkeys = ["", "Нажмите клавишу...", "Не задана", "\\"]
        if hotkey and hotkey not in invalid_hotkeys:
            codes = None
            if hotkey_codes:
                try:
                    codes = [
                        int(x)
                        for x in str(hotkey_codes).split(",")
                        if x.strip().isdigit()
                    ]
                except Exception:
                    codes = None
            if codes:
                self.hotkey_manager.register_hotkey_codes(codes, hotkey)

        # Загружаем состояния таймфреймов из реестра
        # Значения хранятся как "Y"/"N" строки
        log_write("\n[LOAD] Загружаем состояния таймфреймов из реестра:")
        for tf in config.TIMEFRAMES.keys():
            val = settings.value(self._tf_registry_key(tf))
            # Конвертируем строку в boolean: "Y" -> True, всё остальное -> False
            is_checked = (str(val).upper() == "Y") if val is not None else False
            if tf in self.ui.checkboxes:
                self.ui.checkboxes[tf].setChecked(is_checked)
                log_write(
                    f"[LOAD]   {self._tf_registry_key(tf)}: val={val} -> is_checked={is_checked}"
                )

    def apply_overlay_visual(self):
        """Применяет текущий стиль overlay (цвет, размер, шрифт, фон)"""
        overlay_size = self.ui.ov_size_slider.value()
        accent_color = config.COLORS.get("accent", "#ffffff")
        accent_alpha = int(config.COLORS.get("accent_alpha", 255))
        self.logic.overlay.update_style(
            accent_color,
            overlay_size,
            accent_alpha,
            self.current_overlay_font,
            self.overlay_bg_enabled,
            self.overlay_bg_color,
        )

    def append_funding_log(self, entry, trigger_alert=False):
        if not entry:
            return
        if not self.ui.funding_enable_check.isChecked():
            return
        self.funding_alert_entries.append(entry)
        # Сортируем: сначала по минимальному времени, потом по максимальному % (по модулю)
        self.funding_alert_entries = sorted(
            self.funding_alert_entries,
            key=lambda item: (
                item.get("minutes_to", 999999),
                -abs(item.get("signed_rate_pct", 0)),
            ),
        )[:200]
        self._render_funding_log()

        # Если это новая запись из лога (не алерт), проигрываем алерт
        if trigger_alert:
            key = self._entry_tts_key(entry)
            self._pending_tts_entries[key] = entry
            self._funding_tts_timer.start(250)

    def append_funding_log_text(self, payload):
        if not isinstance(payload, dict):
            return
        if not self.ui.funding_enable_check.isChecked():
            return
        self.funding_alert_counter += 1
        entry = {
            "index": self.funding_alert_counter,
            "exchange": payload.get("exchange", ""),
            "symbol": payload.get("symbol", ""),
            "minutes_to": payload.get("minutes_to", 999999),
            "signed_rate_pct": payload.get("signed_rate_pct", 0.0),
            "next_funding_time": payload.get("next_funding_time", 0),
            "triggered": False,
            "trigger_time": None,
        }
        entry["message"] = (
            f"{entry['exchange']} {entry['symbol']} — "
            f"funding {entry['signed_rate_pct']:.2f}% — "
            f"до фандинга {entry['minutes_to']} мин"
        )
        self.append_funding_log(entry, trigger_alert=True)

    def clear_funding_log(self):
        self.ui.funding_log_list.clear()
        self.funding_alert_counter = 0
        self.funding_alert_entries = []
        self.triggered_alerts = []
        self._pending_tts_entries = {}
        self._stop_funding_audio(tts_only=False)
        if hasattr(self, "funding_monitor") and hasattr(
            self.funding_monitor, "clear_cache"
        ):
            self.funding_monitor.clear_cache()

    def _update_funding_log_realtime(self):
        """Обновляет логи в реальном времени: время, секунды, зачеркивание"""
        import time

        self._enforce_funding_audio_policy()

        now_ms = int(time.time() * 1000)

        # Проверяем каждый алерт
        to_move = []
        for entry in self.funding_alert_entries:
            next_funding_time = entry.get("next_funding_time", 0)
            if not next_funding_time:
                continue

            time_diff_ms = next_funding_time - now_ms

            # Если время прошло и алерт еще не triggered
            if time_diff_ms <= 0 and not entry.get("triggered", False):
                entry["triggered"] = True
                entry["trigger_time"] = now_ms

            # Если алерт triggered и прошло 5 секунд после срабатывания
            trigger_time = entry.get("trigger_time")
            if entry.get("triggered", False) and trigger_time:
                elapsed_since_trigger = now_ms - trigger_time
                if elapsed_since_trigger >= 5000:  # 5 секунд
                    to_move.append(entry)

        # Перемещаем завершенные алерты в список triggered_alerts
        for entry in to_move:
            self.funding_alert_entries.remove(entry)
            self.triggered_alerts.append(entry)

        # Ограничиваем количество triggered_alerts до 10
        if len(self.triggered_alerts) > self.max_triggered_alerts:
            # Удаляем самые старые (первые в списке)
            self.triggered_alerts = self.triggered_alerts[-self.max_triggered_alerts :]

        # Перерисовываем лог
        if to_move or self.funding_alert_entries:
            self._render_funding_log()

    def on_funding_alert(self, payload):
        if not isinstance(payload, dict):
            return
        if not self.ui.funding_enable_check.isChecked():
            return
        self.funding_alert_counter += 1
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {
            "index": self.funding_alert_counter,
            "ts": ts,
            "exchange": payload.get("exchange", ""),
            "symbol": payload.get("symbol", ""),
            "minutes_to": payload.get("minutes_to", 0),
            "signed_rate_pct": payload.get("signed_rate_pct", 0.0),
        }
        entry["message"] = (
            f"{entry['exchange']} {entry['symbol']} — "
            f"funding {entry['signed_rate_pct']:.2f}% — "
            f"до фандинга {entry['minutes_to']} мин"
        )

        # Определяем сколько бирж выбрано
        exchanges_count = 0
        if self.ui.funding_binance_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_bybit_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_okx_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_gate_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_bitget_check.isChecked():
            exchanges_count += 1
        is_multiple_exchanges = exchanges_count > 1

        # Генерируем голосовые сообщения
        entry["voice_message_ru"] = self._format_funding_message_ru(
            entry, is_multiple_exchanges
        )
        entry["voice_message_en"] = self._format_funding_message_en(
            entry, is_multiple_exchanges
        )

        self.append_funding_log(
            entry, trigger_alert=False
        )  # Не триггерим алерт для истинных алертов
        settings = QSettings("MyTradeTools", "TF-Alerter")
        sound_enabled = settings.value("funding_sound_enabled", True, type=bool)
        tts_enabled = settings.value("funding_tts_enabled", True, type=bool)
        funding_volume = int(settings.value("funding_volume", 80))

        if sound_enabled:
            try:
                sound_file = settings.value("funding_sound_file", "")
                if sound_file:
                    self._play_funding_sound(sound_file, funding_volume)
                else:
                    self._play_funding_sound(config.SOUND_TICK_LONG, funding_volume)
            except Exception:
                pass

        if tts_enabled:
            settings = QSettings("MyTradeTools", "TF-Alerter")
            tts_engine = settings.value("funding_tts_engine", "system")
            tts_voice_id = settings.value("funding_tts_voice_id", "")
            tts_language = settings.value("funding_tts_language", "ru")

            # Выбираем сообщение на нужном языке
            message = (
                entry["voice_message_ru"]
                if tts_language == "ru"
                else entry["voice_message_en"]
            )

            self._speak_tts_async(message, tts_engine, tts_voice_id, sound_enabled)

    def _trigger_funding_alert(self, entry):
        """Триггерит алерт для записи в логе"""
        if not self.ui.funding_enable_check.isChecked():
            return
        time_text_ru, time_text_en = self._format_tts_time_text(entry)

        # Определяем сколько бирж выбрано
        exchanges_count = 0
        if self.ui.funding_binance_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_bybit_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_okx_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_gate_check.isChecked():
            exchanges_count += 1
        if self.ui.funding_bitget_check.isChecked():
            exchanges_count += 1
        is_multiple_exchanges = exchanges_count > 1

        # Генерируем голосовые сообщения
        entry["voice_message_ru"] = self._format_funding_message_ru(
            entry, is_multiple_exchanges, time_text_ru
        )
        entry["voice_message_en"] = self._format_funding_message_en(
            entry, is_multiple_exchanges, time_text_en
        )

        settings = QSettings("MyTradeTools", "TF-Alerter")
        sound_enabled = settings.value("funding_sound_enabled", True, type=bool)
        tts_enabled = settings.value("funding_tts_enabled", True, type=bool)
        funding_volume = int(settings.value("funding_volume", 80))

        if sound_enabled:
            try:
                sound_file = settings.value("funding_sound_file", "")
                if sound_file:
                    self._play_funding_sound(sound_file, funding_volume)
                else:
                    self._play_funding_sound(config.SOUND_TICK_LONG, funding_volume)
            except Exception:
                pass

        if tts_enabled:
            tts_engine = settings.value("funding_tts_engine", "system")
            tts_voice_id = settings.value("funding_tts_voice_id", "")
            tts_language = settings.value("funding_tts_language", "ru")

            # Выбираем сообщение на нужном языке
            message = (
                entry["voice_message_ru"]
                if tts_language == "ru"
                else entry["voice_message_en"]
            )

            # TTS должен ждать окончания звука, если звук был включен
            self._speak_tts_async(
                message, tts_engine, tts_voice_id, wait_for_sound=sound_enabled
            )

    def _is_funding_tts_enabled(self):
        settings = QSettings("MyTradeTools", "TF-Alerter")
        return settings.value("funding_tts_enabled", True, type=bool)

    def _stop_funding_audio(self, tts_only=False):
        self._edge_tts_queue = []
        self._edge_tts_busy = False
        self._edge_tts_started = False
        with self._edge_ready_lock:
            self._edge_ready_paths.clear()

        if hasattr(self, "_edge_player"):
            try:
                self._edge_player.stop()
            except Exception:
                pass

        engine = getattr(self, "_active_system_tts_engine", None)
        if engine is not None:
            try:
                engine.stop()
            except Exception:
                pass

        if not tts_only and hasattr(self, "_funding_player"):
            try:
                self._funding_player.stop()
            except Exception:
                pass

    def _enforce_funding_audio_policy(self):
        if not self.ui.funding_enable_check.isChecked():
            self._stop_funding_audio(tts_only=False)
            self._pending_tts_entries = {}
            return

        if not self._is_funding_tts_enabled():
            self._stop_funding_audio(tts_only=True)

    def _entry_tts_key(self, entry):
        return (
            str(entry.get("exchange", "")),
            str(entry.get("symbol", "")),
            int(entry.get("next_funding_time", 0) or 0),
            round(float(entry.get("signed_rate_pct", 0.0) or 0.0), 6),
        )

    def _flush_funding_tts_queue(self):
        if not self.ui.funding_enable_check.isChecked():
            self._pending_tts_entries = {}
            self._stop_funding_audio(tts_only=False)
            return

        if not self._pending_tts_entries:
            return

        import time

        now_ms = int(time.time() * 1000)

        def sort_key(item):
            next_time = int(item.get("next_funding_time", 0) or 0)
            if next_time > 0:
                seconds_to = max(0, int((next_time - now_ms) / 1000))
            else:
                seconds_to = 99999999
            return (seconds_to, -abs(float(item.get("signed_rate_pct", 0.0) or 0.0)))

        entries = sorted(self._pending_tts_entries.values(), key=sort_key)
        self._pending_tts_entries = {}

        for entry in entries:
            self._trigger_funding_alert(entry)

    def _ru_minutes_word(self, value):
        n = abs(int(value))
        if n % 10 == 1 and n % 100 != 11:
            return "минута"
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return "минуты"
        return "минут"

    def _ru_seconds_word(self, value):
        n = abs(int(value))
        if n % 10 == 1 and n % 100 != 11:
            return "секунда"
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return "секунды"
        return "секунд"

    def _format_tts_time_text(self, entry):
        import time

        next_time = int(entry.get("next_funding_time", 0) or 0)
        if not next_time:
            return "0 минут", "0 minutes"

        now_ms = int(time.time() * 1000)
        diff_ms = max(0, next_time - now_ms)

        if diff_ms < 60000:
            seconds = max(1, int(diff_ms / 1000))
            return f"{seconds} {self._ru_seconds_word(seconds)}", f"{seconds} seconds"

        minutes = max(1, int(diff_ms / 60000))
        return f"{minutes} {self._ru_minutes_word(minutes)}", f"{minutes} minutes"

    def _play_funding_sound(self, filename, volume_percent):
        """Plays funding sound from transition directory with specified volume"""
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
        from PyQt6.QtCore import QUrl
        import config

        path = config.get_sound_path("transition", filename)
        if not path or not os.path.exists(path):
            return

        try:
            duration_ms = None
            if path.lower().endswith(".wav"):
                import wave

                with wave.open(path, "rb") as wav_file:
                    frame_rate = wav_file.getframerate()
                    frame_count = wav_file.getnframes()
                    if frame_rate > 0:
                        duration_ms = int((frame_count / frame_rate) * 1000)
            if duration_ms and duration_ms > 0:
                self._last_funding_sound_duration_ms = duration_ms
        except Exception:
            pass

        if not hasattr(self, "_funding_player"):
            self._funding_player = QMediaPlayer()
            self._funding_output = QAudioOutput()
            self._funding_player.setAudioOutput(self._funding_output)
            try:
                default_device = QMediaDevices.defaultAudioOutput()
                self._funding_output.setDevice(default_device)
            except Exception:
                pass

        volume = max(0.0, min(1.0, volume_percent / 100.0))
        self._funding_output.setVolume(volume)
        self._funding_player.stop()
        self._funding_player.setSource(QUrl())
        self._funding_player.setSource(QUrl.fromLocalFile(path))
        self._funding_player.play()

    def _format_funding_message_ru(
        self, entry, is_multiple_exchanges=True, time_text_ru="0 минут"
    ):
        """Формирует голосовое сообщение на русском"""
        # Названия бирж и монет с правильным произношением
        exchange_names = {"binance": "Бинанс", "bybit": "Байбит"}
        coin_names = {
            "BTC": "биткоин",
            "ETH": "эфир",
            "BNB": "бинб",
            "SOL": "сол",
            "XRP": "рипл",
            "ADA": "кардано",
            "DOGE": "доге",
            "AVAX": "аваланш",
            "MATIC": "матик",
            "ARB": "арбитрум",
            "OP": "оптимизм",
        }

        exchange = entry["exchange"].lower()
        symbol = self._symbol_for_tts(entry["symbol"])
        rate = entry["signed_rate_pct"]

        # Переводим название биржи
        exchange_ru = exchange_names.get(exchange, exchange)

        # Переводим название монеты (берем только первое совпадение)
        coin_ru = symbol
        for coin_code, coin_name in coin_names.items():
            if coin_code in symbol:
                coin_ru = coin_name
                break

        # Определяем направление
        if rate > 0:
            direction = "плюс"
        elif rate < 0:
            direction = "минус"
        else:
            direction = "ноль"

        # Формируем сообщение
        rate_str = f"{abs(rate):.2f}".replace(".", " точка ")

        # Включаем название биржи только если выбрано больше 1 биржи
        if is_multiple_exchanges:
            message = f"{exchange_ru}, {coin_ru}, {direction} {rate_str} процента, через {time_text_ru}"
        else:
            message = (
                f"{coin_ru}, {direction} {rate_str} процента, через {time_text_ru}"
            )

        return message

    def _format_funding_message_en(
        self, entry, is_multiple_exchanges=True, time_text_en="0 minutes"
    ):
        """Формирует голосовое сообщение на английском"""
        exchange_names = {"binance": "Binance", "bybit": "Bybit"}

        exchange = entry["exchange"].lower()
        symbol = self._symbol_for_tts(entry["symbol"])
        rate = entry["signed_rate_pct"]

        # Переводим название биржи
        exchange_en = exchange_names.get(exchange, exchange)

        # Определяем направление
        if rate > 0:
            direction = "positive"
        elif rate < 0:
            direction = "negative"
        else:
            direction = "zero"

        # Формируем сообщение
        rate_str = f"{abs(rate):.2f}".replace(".", " point ")

        # Включаем название биржи только если выбрано больше 1 биржи
        if is_multiple_exchanges:
            message = f"{exchange_en}, {symbol}, {direction} {rate_str} percent, in {time_text_en}"
        else:
            message = f"{symbol}, {direction} {rate_str} percent, in {time_text_en}"

        return message

    def _symbol_for_tts(self, symbol):
        if not isinstance(symbol, str):
            return ""
        cleaned = symbol.strip().upper()
        for suffix in ("USDT", "USDC", "BUSD", "USD"):
            if cleaned.endswith(suffix) and len(cleaned) > len(suffix):
                return cleaned[: -len(suffix)]
        return cleaned

    def _start_next_edge_tts(self):
        if (
            not self.ui.funding_enable_check.isChecked()
            or not self._is_funding_tts_enabled()
        ):
            self._stop_funding_audio(tts_only=True)
            return

        if self._edge_tts_busy:
            return
        if not self._edge_tts_queue:
            return
        message, voice_id, delay_ms = self._edge_tts_queue.pop(0)
        self._edge_tts_busy = True
        self._edge_tts_started = False
        QTimer.singleShot(
            max(0, int(delay_ms)),
            lambda msg=message, vid=voice_id: self._speak_edge_tts(msg, vid),
        )

    def _on_edge_tts_playback_state(self, state):
        from PyQt6.QtMultimedia import QMediaPlayer

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._edge_tts_started = True
            return

        if (
            state == QMediaPlayer.PlaybackState.StoppedState
            and self._edge_tts_busy
            and self._edge_tts_started
        ):
            self._edge_tts_busy = False
            self._edge_tts_started = False
            QTimer.singleShot(50, self._start_next_edge_tts)

    def _on_edge_tts_media_status(self, status):
        from PyQt6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.InvalidMedia and self._edge_tts_busy:
            self._edge_tts_busy = False
            self._edge_tts_started = False
            QTimer.singleShot(50, self._start_next_edge_tts)

    def _speak_tts_async(self, message, engine_type, voice_id, wait_for_sound=False):
        """Асинхронное проигрывание TTS с поддержкой разных движков"""
        import threading
        import time

        if (
            not self.ui.funding_enable_check.isChecked()
            or not self._is_funding_tts_enabled()
        ):
            return

        def _run_system_tts(text, tts_voice_id, delay_ms):
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)
            try:
                self._speak_system_tts(text, tts_voice_id)
            except Exception as e:
                print(f"⚠️ Ошибка TTS: {e}")

        delay_ms = 0
        if wait_for_sound:
            sound_duration = int(
                getattr(self, "_last_funding_sound_duration_ms", 1700) or 1700
            )
            delay_ms = max(300, sound_duration + 80)

        if engine_type == "edge":
            if self._edge_tts_busy or self._edge_tts_queue:
                delay_ms = 0
            self._edge_tts_queue.append((message, voice_id, delay_ms))
            self._start_next_edge_tts()
            return

        thread = threading.Thread(
            target=_run_system_tts,
            args=(message, voice_id, delay_ms),
            daemon=True,
        )
        thread.start()

    def _speak_system_tts(self, text, voice_id):
        """Проигрывание через системный TTS (pyttsx3)"""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            self._active_system_tts_engine = engine
            if voice_id:
                engine.setProperty("voice", voice_id)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"⚠️ Ошибка System TTS: {e}")
        finally:
            self._active_system_tts_engine = None

    def _speak_edge_tts(self, text, voice_name):
        """Проигрывание через Edge TTS (онлайн)"""
        try:
            if (
                not self.ui.funding_enable_check.isChecked()
                or not self._is_funding_tts_enabled()
            ):
                self._edge_tts_busy = False
                self._edge_tts_started = False
                return

            import edge_tts
            import asyncio
            import tempfile

            # Проверяем и устанавливаем voice_name с fallback
            if not voice_name:
                voice_name = "ru-RU-DmitryNeural"

            def _generate_worker(message_text, current_voice):
                try:

                    async def generate_audio():
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=".mp3"
                        ) as tmp_file:
                            tmp_path = tmp_file.name

                        communicate = edge_tts.Communicate(message_text, current_voice)
                        await communicate.save(tmp_path)
                        return tmp_path

                    tmp_path = asyncio.run(generate_audio())
                    with self._edge_ready_lock:
                        self._edge_ready_paths.append(tmp_path)
                except Exception:
                    with self._edge_ready_lock:
                        self._edge_ready_paths.append(False)

            thread = threading.Thread(
                target=_generate_worker,
                args=(text, voice_name),
                daemon=True,
            )
            thread.start()

        except ImportError:
            print("⚠️ Edge TTS не установлен. Установите: pip install edge-tts")
            self._edge_tts_busy = False
            self._edge_tts_started = False
            QTimer.singleShot(50, self._start_next_edge_tts)
        except Exception as e:
            print(f"⚠️ Ошибка Edge TTS: {e}")
            self._edge_tts_busy = False
            self._edge_tts_started = False
            QTimer.singleShot(50, self._start_next_edge_tts)

    def _drain_edge_ready_paths(self):
        if not self._edge_tts_busy:
            return

        if (
            not self.ui.funding_enable_check.isChecked()
            or not self._is_funding_tts_enabled()
        ):
            self._stop_funding_audio(tts_only=True)
            return

        _no_item = object()
        ready_item = _no_item
        with self._edge_ready_lock:
            if self._edge_ready_paths:
                ready_item = self._edge_ready_paths.popleft()

        if ready_item is _no_item:
            return

        if ready_item is False:
            self._edge_tts_busy = False
            self._edge_tts_started = False
            QTimer.singleShot(50, self._start_next_edge_tts)
            return

        if isinstance(ready_item, str):
            self._play_edge_tts_file(ready_item)

    def _play_edge_tts_file(self, tmp_path):
        from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
        from PyQt6.QtCore import QUrl

        if (
            not self.ui.funding_enable_check.isChecked()
            or not self._is_funding_tts_enabled()
        ):
            self._edge_tts_busy = False
            self._edge_tts_started = False
            return

        if not hasattr(self, "_edge_player"):
            self._edge_player = QMediaPlayer()
            self._edge_output = QAudioOutput()
            self._edge_player.setAudioOutput(self._edge_output)
            self._edge_player.playbackStateChanged.connect(
                self._on_edge_tts_playback_state
            )
            self._edge_player.mediaStatusChanged.connect(self._on_edge_tts_media_status)
            try:
                default_device = QMediaDevices.defaultAudioOutput()
                self._edge_output.setDevice(default_device)
            except Exception:
                pass

        settings = QSettings("MyTradeTools", "TF-Alerter")
        volume = settings.value("funding_volume", 80, type=int) / 100.0
        self._edge_output.setVolume(volume)

        self._edge_player.stop()
        self._edge_player.setSource(QUrl())
        self._edge_player.setSource(QUrl.fromLocalFile(tmp_path))
        self._edge_player.play()

    def _render_funding_log(self):
        import time

        self.ui.funding_log_list.clear()
        now_ms = int(time.time() * 1000)

        if self._funding_log_view_mode == "triggered":
            triggered_now = [
                entry
                for entry in self.funding_alert_entries
                if entry.get("triggered", False)
            ]
            for entry in self.triggered_alerts:
                self._add_funding_log_item(entry, now_ms, triggered=True)
            for entry in triggered_now:
                self._add_funding_log_item(entry, now_ms, triggered=True)
            return

        # По умолчанию показываем предстоящие
        for entry in self.funding_alert_entries:
            if entry.get("triggered", False):
                continue
            self._add_funding_log_item(entry, now_ms, triggered=False)

    def set_funding_log_view_mode(self, mode):
        if mode not in ("upcoming", "triggered"):
            mode = "upcoming"
        self._funding_log_view_mode = mode

        self.ui.funding_log_upcoming_btn.blockSignals(True)
        self.ui.funding_log_triggered_btn.blockSignals(True)
        self.ui.funding_log_upcoming_btn.setChecked(mode == "upcoming")
        self.ui.funding_log_triggered_btn.setChecked(mode == "triggered")
        self.ui.funding_log_upcoming_btn.blockSignals(False)
        self.ui.funding_log_triggered_btn.blockSignals(False)

        self._render_funding_log()

    def _add_funding_log_item(self, entry, now_ms, triggered=False):
        """Добавляет элемент в лог фандинга"""
        exchange = entry.get("exchange", "")
        symbol = entry.get("symbol", "")
        rate = entry.get("signed_rate_pct", 0.0)
        next_funding_time = entry.get("next_funding_time", 0)

        # Вычисляем время до фандинга
        if next_funding_time:
            time_diff_ms = next_funding_time - now_ms
            if time_diff_ms > 60000:  # > 1 минуты
                minutes = max(0, int(time_diff_ms / 60000))
                time_str = f"{minutes} мин"
            elif time_diff_ms > 0:  # < 1 минуты, показываем секунды
                seconds = max(0, int(time_diff_ms / 1000))
                time_str = f"{seconds} сек"
            else:
                time_str = "завершён"

            # Конвертируем next_funding_time в локальное время
            funding_dt = datetime.datetime.fromtimestamp(next_funding_time / 1000)
            funding_time_str = funding_dt.strftime("%H:%M:%S")
        else:
            time_str = "?"
            funding_time_str = "?"

        # Текст: СИМВОЛ биржа — funding X% — до фандинга Y мин/сек — фандинг в HH:MM:SS
        text = f"{symbol}  {exchange} — funding {rate:.2f}% — до фандинга {time_str} — фандинг в {funding_time_str}"

        item = QListWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignLeft)
        item.setData(Qt.ItemDataRole.UserRole, entry)

        font = item.font()
        font.setPointSize(9)

        # Если алерт сработал - зачеркиваем и делаем темнее
        if triggered:
            font.setStrikeOut(True)
            item.setFont(font)
            item.setForeground(QColor(100, 100, 100))  # Темно-серый
        else:
            item.setFont(font)
            # Цвет по времени
            if next_funding_time:
                time_diff_ms = next_funding_time - now_ms
                minutes_to = max(0, int(time_diff_ms / 60000))
                if minutes_to <= 5 or (time_diff_ms > 0 and time_diff_ms <= 60000):
                    item.setForeground(QColor(config.COLORS["danger"]))
                elif minutes_to <= 15:
                    item.setForeground(QColor(config.COLORS["accent"]))
                else:
                    item.setForeground(QColor(config.COLORS["text"]))
            else:
                item.setForeground(QColor(config.COLORS["text"]))

        self.ui.funding_log_list.addItem(item)

    def copy_funding_symbol(self, item):
        if not item:
            return

        # Получаем позицию клика относительно элемента
        cursor_pos = self.ui.funding_log_list.mapFromGlobal(QCursor.pos())
        item_rect = self.ui.funding_log_list.visualItemRect(item)

        entry = item.data(Qt.ItemDataRole.UserRole) or {}
        symbol = entry.get("symbol", "")
        if not symbol:
            return

        # Копируем только если клик в первых ~100 пикселях (примерная ширина символа)
        relative_x = cursor_pos.x() - item_rect.x()
        if relative_x <= 100:  # Только если клик на начале строки (на символе)
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(symbol)
            QToolTip.showText(QCursor.pos(), f"Скопировано: {symbol}")
            QTimer.singleShot(2000, QToolTip.hideText)

    def toggle_overlay_move_lock(self, state):
        self.overlay_move_locked = bool(state)
        self.logic.overlay.move_locked = self.overlay_move_locked

    def on_overlay_font_changed(self, font_name):
        selected_family = (font_name or "").strip() or "Arial"
        self.current_overlay_font = selected_family
        self.apply_overlay_visual()
        self.save_settings()

    def changeEvent(self, event):
        """Перехватываем изменения состояния окна"""
        super().changeEvent(event)

    def hideEvent(self, event):
        """Окно скрывается"""
        super().hideEvent(event)

    def closeEvent(self, event):
        log_write("\n[CLOSE] closeEvent вызван!")
        try:
            self._is_closing = True
            self.save_settings()

            # Дополнительно флешим все значения при закрытии
            settings = QSettings("MyTradeTools", "TF-Alerter")
            settings.sync()
            log_write("[CLOSE] Финальный sync() при закрытии приложения")

            # Останавливаем менеджер горячих клавиш
            if hasattr(self, "hotkey_manager"):
                self.hotkey_manager.stop()

            if hasattr(self, "logic"):
                self.logic.timer.stop()
                self.logic.overlay_update_timer.stop()  # Останавливаем таймер обновления часов
                self.logic.overlay.close()
            event.accept()
        except Exception as e:
            log_write(f"Ошибка при закрытии: {e}")
            event.accept()

    def change_color(self):
        self.logic.is_selecting_color = True
        current_hex = config.COLORS.get("accent", "#007acc")
        settings = QSettings("MyTradeTools", "TF-Alerter")
        current_alpha = int(settings.value("accent_alpha", 255))

        dialog = ColorPickerDialog(
            self,
            current_hex,
            current_alpha,
            self.overlay_bg_enabled,
            self.overlay_bg_color,
        )
        # При открытии диалога сразу применяются все изменения благодаря live preview
        if dialog.exec():
            # Пользователь нажал OK - сохраняем значения в конфиг и настройки
            new_hex = dialog.get_color()
            new_alpha = dialog.get_alpha()
            self.overlay_bg_enabled = dialog.get_bg_enabled()
            self.overlay_bg_color = dialog.get_bg_color()
            config.COLORS["accent"] = new_hex
            config.COLORS["accent_alpha"] = new_alpha
            self.save_settings()
        else:
            # Пользователь нажал Cancel или закрыл диалог
            # Значения уже восстановлены в dialog.reject()
            pass
        self.logic.is_selecting_color = False


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Установка иконки приложения для панели задач и Alt+Tab
    app.setWindowIcon(QIcon(config.LOGO_PATH))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
