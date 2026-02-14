"""
Создает простые голосовые файлы через Windows TTS (pyttsx3)
"""


def create_voice_files_pyttsx3():
    import pyttsx3
    import os

    voice_dir = os.path.join(os.path.dirname(__file__), "Sounds", "Voice")
    os.makedirs(voice_dir, exist_ok=True)

    phrases = {
        "funding_alert_en.wav": ("Funding exceeded", "en"),
        "funding_attention_en.wav": ("Attention, funding", "en"),
    }

    print("=" * 60)
    print("ГЕНЕРАЦИЯ ГОЛОСОВЫХ ФАЙЛОВ через pyttsx3")
    print("=" * 60)

    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    # Ищем английский голос
    en_voice = None
    for voice in voices:
        name = getattr(voice, "name", "").lower()
        if "en" in name or "english" in name or "zira" in name:
            en_voice = getattr(voice, "id", "")
            print(f"\nИспользуем голос: {getattr(voice, 'name', 'Unknown')}")
            break

    if en_voice:
        engine.setProperty("voice", en_voice)

    for filename, (text, lang) in phrases.items():
        path = os.path.join(voice_dir, filename)
        print(f"\nСоздание: {filename}")
        print(f"  Текст: {text}")

        try:
            engine.save_to_file(text, path)
            engine.runAndWait()
            if os.path.exists(path):
                print(f"  ✅ Сохранено: {path}")
            else:
                print(f"  ⚠️ Файл не создан")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")

    print("\n" + "=" * 60)
    print("ГОТОВО!")
    print("=" * 60)
    print("\nДЛЯ РУССКИХ ГОЛОСОВ:")
    print("- Установите русские TTS голоса в Windows")
    print("- Запустите этот скрипт снова")
    print("- Или запишите свои голосовые файлы")
    print("=" * 60)


if __name__ == "__main__":
    create_voice_files_pyttsx3()
