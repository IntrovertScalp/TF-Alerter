import os
import datetime
import ctypes
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QUrl, QSettings
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
import config
from overlay import OverlayClock


class AlerterLogic(QObject):
    time_signal = pyqtSignal(str)

    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.is_selecting_color = False
        self.overlay = OverlayClock()

        # Звук (раздельные плееры для чистого воспроизведения)
        self.voice_player = QMediaPlayer()
        self.voice_output = QAudioOutput()
        self.voice_player.setAudioOutput(self.voice_output)

        self.tick_player = QMediaPlayer()
        self.tick_output = QAudioOutput()
        self.tick_player.setAudioOutput(self.tick_output)

        self.transition_player = QMediaPlayer()
        self.transition_output = QAudioOutput()
        self.transition_player.setAudioOutput(self.transition_output)
        self._apply_default_audio_output()
        self.media_devices = QMediaDevices()
        self.media_devices.audioOutputsChanged.connect(self._on_audio_outputs_changed)

        # Кеш звуков для мгновенного воспроизведения (без задержки загрузки)
        self.sound_cache = {}
        self.preload_sounds()

        # Основной таймер для логики алертов (каждую секунду)
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_time)
        self.last_played_second = -1
        self.last_tick_second = (
            -1
        )  # Отдельный трекер для синхронизации тиков в последних 5 сек

        # Отдельный быстрый таймер для обновления часов (каждые 100мс)
        # Это позволяет часам обновляться более плавно без нагрузки на основную логику
        self.overlay_update_timer = QTimer()
        self.overlay_update_timer.setInterval(100)  # Обновление каждые 100мс
        self.overlay_update_timer.timeout.connect(self.update_overlay_time)

        self.terminal_title = "Profit Forge"
        self.ui.ov_size_slider.valueChanged.connect(self.update_overlay_style)

    def _apply_default_audio_output(self):
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            self.voice_output.setDevice(default_device)
            self.tick_output.setDevice(default_device)
            self.transition_output.setDevice(default_device)
        except Exception:
            pass

    def preload_sounds(self):
        """Предварительная загрузка всех звуков в кеш для мгновенного воспроизведения"""
        print("📢 Предварительная загрузка звуков...")

        # Загружаем основные голосовые звуки (закрытие таймфреймов)
        for tf_key, tf_data in config.TIMEFRAMES.items():
            filename = tf_data["file"]
            path = config.get_sound_path("main", filename)
            if path and os.path.exists(path):
                self.sound_cache[f"main_{filename}"] = path
                print(f"  ✓ {filename}")
            else:
                print(f"  ⚠ {filename} - файл не найден")

        # Загружаем звуки тиков
        for tf_key, tick_sound in config.SOUND_TICK_BY_TF.items():
            if tick_sound:
                path = config.get_sound_path("tick", tick_sound)
                if path and os.path.exists(path):
                    self.sound_cache[f"tick_{tick_sound}"] = path

        # Загружаем звуки переходов
        for tf_key, trans_sound in config.SOUND_TRANSITION_BY_TF.items():
            if trans_sound:
                path = config.get_sound_path("transition", trans_sound)
                if path and os.path.exists(path):
                    self.sound_cache[f"transition_{trans_sound}"] = path

        # Загружаем звук "длинный переход" (для последней секунды)
        if hasattr(config, "SOUND_TICK_LONG"):
            path = config.get_sound_path("transition", config.SOUND_TICK_LONG)
            if path and os.path.exists(path):
                self.sound_cache[f"transition_{config.SOUND_TICK_LONG}"] = path

        print(f"📢 Загружено звуков в кеш: {len(self.sound_cache)}")

    def _get_player_output(self, kind: str):
        if kind == "tick":
            return self.tick_player, self.tick_output
        if kind == "transition":
            return self.transition_player, self.transition_output
        return self.voice_player, self.voice_output

    def _on_audio_outputs_changed(self):
        self._apply_default_audio_output()

    def update_overlay_style(self):
        accent_color = config.COLORS.get("accent", "#ffffff")
        accent_alpha = config.COLORS.get("accent_alpha", 255)
        new_size = self.ui.ov_size_slider.value()
        settings = QSettings("MyTradeTools", "TF-Alerter")
        font_family = settings.value("overlay_font_family", "Arial")
        if not isinstance(font_family, str) or not font_family.strip():
            font_family = "Arial"
        bg_enabled = settings.value("overlay_bg_enabled", False, type=bool)
        bg_color = settings.value("overlay_bg_color", "#000000")
        if not isinstance(bg_color, str) or not bg_color.strip():
            bg_color = "#000000"
        self.overlay.update_style(
            accent_color,
            new_size,
            accent_alpha,
            font_family,
            bg_enabled,
            bg_color,
        )

    def update_overlay_time(self):
        """Обновляет время в overlay каждые 100мс (оптимизировано)"""
        now_local = datetime.datetime.now()
        self.overlay.set_time(now_local.strftime("%H:%M:%S"))

    def get_active_window_title_fast(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception:
            return ""

    def check_time(self):
        # 1. Время UTC для логики свечей
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        # 2. Локальное время для отображения
        now_local = datetime.datetime.now()

        # Текущая секунда (абсолютная) для защиты от повторов в одном цикле
        current_second_total = (
            now_utc.hour * 3600 + now_utc.minute * 60 + now_utc.second
        )

        if current_second_total != self.last_played_second:
            self.last_played_second = current_second_total
            sec = now_utc.second

            # --- ЛОГИКА АЛЕРТОВ И ТИКАНЬЯ ---

            # Определяем, какой "следующий" момент времени мы ждем (конец минуты)
            # Если сейчас 50 сек, то закрытие будет через 10 сек (в след. минуту :00)
            next_minute_dt = now_utc + datetime.timedelta(seconds=(60 - sec))

            # Проверяем, есть ли активные таймфреймы, которые закроются в конце этой минуты
            closing_tf, closing_msg = self.get_closing_tf(next_minute_dt)

            if closing_tf:
                # 1. ГОЛОСОВОЙ АЛЕРТ (за 10 секунд)
                if sec == (60 - config.VOICE_LEAD_TIME):  # 50-я секунда
                    # Проверяем, включены ли голосовые звуки
                    settings = QSettings("MyTradeTools", "TF-Alerter")
                    if settings.value("sounds_voice_enabled", True, type=bool):
                        self.play_voice(config.TIMEFRAMES[closing_tf]["file"], "main")
                    self.time_signal.emit(f"{closing_msg} (через 10с)")

                # 2. ТИКАНЬЕ (55, 56, 57, 58 сек) - синхронизировано по абсолютной секунде
                elif 55 <= sec <= 58:
                    # Используем last_tick_second для точной синхронизации тиков
                    # Это гарантирует, что каждый тик играет ровно в момент прихода на эту секунду
                    tick_sound = config.SOUND_TICK_BY_TF.get(closing_tf, "")
                    if tick_sound and current_second_total != self.last_tick_second:
                        self.last_tick_second = current_second_total
                        # Проверяем, включены ли звуки тиков
                        settings = QSettings("MyTradeTools", "TF-Alerter")
                        if settings.value("sounds_tick_enabled", True, type=bool):
                            self.play_voice(tick_sound, "tick")

                # 3. ПОСЛЕДНИЙ ТИК (59 сек)
                elif sec == 59:
                    transition_sound = config.SOUND_TRANSITION_BY_TF.get(closing_tf, "")
                    if transition_sound:
                        # Проверяем, включены ли звуки переходов
                        settings = QSettings("MyTradeTools", "TF-Alerter")
                        if settings.value("sounds_transition_enabled", True, type=bool):
                            self.play_voice(transition_sound, "transition")

            # 4. МОМЕНТ ЗАКРЫТИЯ (00 сек) - Только текст, без звука (звук был в 50 сек)
            if sec == 0:
                # Проверяем "текущий" момент (он уже наступил)
                active_tf, msg = self.get_closing_tf(now_utc)
                if active_tf:
                    self.time_signal.emit(msg)

        # --- ЛОГИКА ВИДИМОСТИ (Оптимизированная) ---
        if self.ui.cb_overlay.isChecked():
            # Определяем должно ли окно быть видимым
            if config.OVERLAY_SHOW_MODE == "always":
                # "Всегда показывать" - показываем во всех окнах
                is_visible_context = True
            else:
                # "Только на определённых окнах" - проверяем список
                active_window = self.get_active_window_title_fast()
                is_visible_context = any(
                    app.lower() in active_window.lower()
                    for app in config.OVERLAY_WINDOWS
                )

            # Дополнительные контексты (выбор цвета, перетаскивание)
            if self.is_selecting_color or self.overlay._dragging:
                is_visible_context = True

            if is_visible_context and not self.overlay.isVisible():
                self.overlay.show()
            elif not is_visible_context and self.overlay.isVisible():
                self.overlay.hide()
        else:
            if self.overlay.isVisible():
                self.overlay.hide()

    def get_closing_tf(self, dt):
        """
        Возвращает самый старший активный таймфрейм, который закрывается в момент dt (обычно :00 секунд).
        dt - это объект datetime (UTC).
        Возвращает кортеж (ключ_тф, сообщение) или (None, None).
        """
        # Сначала проверяем, что секунды == 0 (или близко к 0, т.к. dt мы считаем математически)
        # Но так как мы передаем dt выравненный на минуту, проверим условия кратности.

        # Проверяем включен ли чекбокс перед возвратом
        def is_active(key):
            return self.ui.checkboxes.get(key) and self.ui.checkboxes[key].isChecked()

        # 1. Месяц
        if dt.day == 1 and dt.hour == 0 and dt.minute == 0 and is_active("1M"):
            return "1M", "Месячная свеча закрыта!"

        # 2. Неделя
        if dt.weekday() == 0 and dt.hour == 0 and dt.minute == 0 and is_active("1w"):
            return "1w", "НЕДЕЛЬНАЯ свеча закрыта!"

        # 3. День
        if dt.hour == 0 and dt.minute == 0 and is_active("1d"):
            return "1d", "Дневная свеча закрыта!"

        # 4. 4 Часа
        if dt.hour % 4 == 0 and dt.minute == 0 and is_active("4h"):
            return "4h", "Свеча H4 закрыта!"

        # 5. 1 Час
        if dt.minute == 0 and is_active("1h"):
            return "1h", "Часовая свеча закрыта!"

        # 6. 30 Минут
        if dt.minute % 30 == 0 and is_active("30m"):
            return "30m", "Свеча 30м закрыта!"

        # 7. 15 Минут
        if dt.minute % 15 == 0 and is_active("15m"):
            return "15m", "Свеча 15м закрыта!"

        # 8. 5 Минут
        if dt.minute % 5 == 0 and is_active("5m"):
            return "5m", "Свеча 5м закрыта!"

        # 9. 1 Минута
        if is_active("1m"):
            # 1 минута закрывается каждую минуту
            return "1m", "Минутная свеча закрыта!"

        return None, None

    def play_voice(self, filename, kind="main"):
        vol_value = self.ui.volume_slider.value()
        if vol_value <= 0:
            return

        # Пытаемся получить путь из кеша для мгновенного доступа
        cache_key = f"{kind}_{filename}"
        if cache_key in self.sound_cache:
            path = self.sound_cache[cache_key]
        else:
            # Fallback: получаем путь обычным способом
            path = config.get_sound_path(kind, filename)
            if not path or not os.path.exists(path):
                fallback_path = os.path.join(config.SOUNDS_DIR, filename)
                if os.path.exists(fallback_path):
                    path = fallback_path
                else:
                    print(f"⚠️ [{kind.upper()}] Звуковой файл не найден: {filename}")
                    return

        # Громкость 0-100% (макс 1.0) для ЧИСТОГО звучания без треска
        volume = max(0.0, min(1.0, vol_value / 100.0))
        player, output = self._get_player_output(kind)

        output.setVolume(volume)

        # Полностью останавливаем и очищаем предыдущий звук этого типа
        player.stop()
        player.setSource(QUrl())  # Очищаем источник

        # Устанавливаем новый звук и проигрываем (из кеша)
        player.setSource(QUrl.fromLocalFile(path))
        player.play()

    def test_timeframe_alert(self, tf_key):
        """Debug-метод для тестирования звука любого таймфрейма"""
        if tf_key in config.TIMEFRAMES:
            filename = config.TIMEFRAMES[tf_key]["file"]
            label = config.TIMEFRAMES[tf_key]["label"]
            print(f"🔊 [TEST] Проигрываем звук для {label}: {filename}")
            self.play_voice(filename, "main")
            self.time_signal.emit(f"[ТЕСТ] {label} закрыт!")
        else:
            print(f"❌ Таймфрейм '{tf_key}' не найден в config.TIMEFRAMES")

    def start(self):
        self.timer.start(16)  # 60 FPS для максимально быстрого отклика на смену окна
