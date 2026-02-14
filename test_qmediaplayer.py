"""
Тест QMediaPlayer с Edge TTS
"""

import sys
import asyncio
import tempfile
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices
from PyQt6.QtCore import QUrl
import edge_tts


class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test QMediaPlayer + Edge TTS")
        layout = QVBoxLayout()

        btn = QPushButton("Test Edge TTS")
        btn.clicked.connect(self.test_edge_tts)
        layout.addWidget(btn)

        self.setLayout(layout)

        # Инициализируем плеер
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        # Подключаем сигналы
        self.player.errorOccurred.connect(self.on_error)
        self.player.playbackStateChanged.connect(self.on_state_changed)
        self.player.mediaStatusChanged.connect(self.on_media_status_changed)

        print("🔊 Доступные аудио устройства:")
        for device in QMediaDevices.audioOutputs():
            print(f"  - {device.description()}")

    def on_error(self, error):
        print(f"❌ Player error: {error}, {self.player.errorString()}")

    def on_state_changed(self, state):
        print(f"🎵 State changed: {state}")

    def on_media_status_changed(self, status):
        print(f"📊 Media status: {status}")

    def test_edge_tts(self):
        print("\n🔄 Генерируем Edge TTS...")

        async def generate():
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            text = "Тестовое сообщение от Edge TTS"
            voice_id = "ru-RU-DmitryNeural"

            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(tmp_path)
            return tmp_path

        tmp_path = asyncio.run(generate())

        import os

        print(f"✅ Файл создан: {tmp_path} ({os.path.getsize(tmp_path)} bytes)")

        # Останавливаем плеер
        self.player.stop()

        # Устанавливаем громкость
        self.audio_output.setVolume(1.0)
        print(f"🔊 Громкость: {self.audio_output.volume()}")

        # Загружаем файл
        url = QUrl.fromLocalFile(tmp_path)
        print(f"📁 Загружаем: {url.toString()}")
        self.player.setSource(url)

        # Проигрываем
        print("▶️ Вызов play()...")
        self.player.play()

        print(f"🎵 Состояние после play(): {self.player.playbackState()}")
        print(f"📊 Media status: {self.player.mediaStatus()}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
