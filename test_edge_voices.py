"""
Тест Edge TTS голосов
"""

import asyncio
import edge_tts


async def list_voices():
    """Получает список доступных голосов Edge TTS"""
    voices = await edge_tts.list_voices()

    print("\n=== Русские голоса ===")
    for voice in voices:
        if voice["Locale"].startswith("ru"):
            print(f"{voice['ShortName']}: {voice['FriendlyName']} ({voice['Gender']})")

    print("\n=== Английские голоса (US) ===")
    for voice in voices:
        if voice["Locale"].startswith("en-US"):
            print(f"{voice['ShortName']}: {voice['FriendlyName']} ({voice['Gender']})")
            if len([v for v in voices if v["Locale"].startswith("en-US")]) > 50:
                break  # Ограничиваем вывод


async def test_voice(voice_id, text):
    """Тестирует конкретный голос"""
    print(f"\nТест голоса: {voice_id}")
    communicate = edge_tts.Communicate(text, voice_id)

    # Проверяем что можно генерировать
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        await communicate.save(tmp_path)
        import os

        file_size = os.path.getsize(tmp_path)
        print(f"✅ Файл создан: {file_size} bytes")
        os.unlink(tmp_path)
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    # Список голосов
    asyncio.run(list_voices())

    # Тест конкретных голосов
    print("\n=== Тестирование голосов ===")
    asyncio.run(test_voice("ru-RU-DmitryNeural", "Тестовое сообщение"))
    asyncio.run(test_voice("ru-RU-SvetlanaNeural", "Тестовое сообщение"))
    asyncio.run(test_voice("en-US-GuyNeural", "Test message"))
    asyncio.run(test_voice("en-US-AriaNeural", "Test message"))
