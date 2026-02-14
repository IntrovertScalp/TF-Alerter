"""
Скрипт для создания голосовых файлов фандинга
Использует Google TTS (gTTS) для генерации голосовых сообщений
"""


def create_voice_files():
    try:
        from gtts import gTTS
        import os

        voice_dir = os.path.join(os.path.dirname(__file__), "Sounds", "Voice")
        os.makedirs(voice_dir, exist_ok=True)

        # Словарь с фразами для разных языков
        voices = {
            "funding_alert_ru.mp3": ("Фандинг превышен", "ru"),
            "funding_alert_en.mp3": ("Funding exceeded", "en"),
            "funding_attention_ru.mp3": ("Внимание, фандинг", "ru"),
            "funding_attention_en.mp3": ("Attention, funding", "en"),
        }

        print("=" * 60)
        print("ГЕНЕРАЦИЯ ГОЛОСОВЫХ ФАЙЛОВ ДЛЯ ФАНДИНГА")
        print("=" * 60)

        for filename, (text, lang) in voices.items():
            path = os.path.join(voice_dir, filename)
            print(f"\nСоздание: {filename}")
            print(f"  Текст: {text}")
            print(f"  Язык: {lang}")

            try:
                tts = gTTS(text=text, lang=lang, slow=False)
                tts.save(path)
                print(f"  ✅ Сохранено в: {path}")
            except Exception as e:
                print(f"  ❌ Ошибка: {e}")

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print(
            f"Создано файлов: {len([f for f in voices.keys() if os.path.exists(os.path.join(voice_dir, f))])}/{len(voices)}"
        )
        print(f"Папка: {voice_dir}")
        print("=" * 60)

    except ImportError:
        print("=" * 60)
        print("ОШИБКА: библиотека gTTS не установлена")
        print("=" * 60)
        print("\nУстановите библиотеку:")
        print("  pip install gTTS")
        print("\nИли создайте голосовые файлы вручную:")
        print("  1. Запишите фразы голосом")
        print("  2. Сохраните в формате .wav, .mp3 или .ogg")
        print(f"  3. Положите файлы в папку: Sounds/Voice/")
        print("\nРекомендуемые фразы:")
        print("  Русский: 'Фандинг превышен', 'Внимание, фандинг'")
        print("  English: 'Funding exceeded', 'Attention, funding'")
        print("=" * 60)


if __name__ == "__main__":
    create_voice_files()
