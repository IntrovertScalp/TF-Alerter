import pyttsx3

print("=" * 60)
print("ПРОВЕРКА TTS ГОЛОСОВ В СИСТЕМЕ")
print("=" * 60)

try:
    engine = pyttsx3.init()
    voices = engine.getProperty("voices") or []

    print(f"\n✅ Всего найдено голосов: {len(voices)}\n")

    if len(voices) == 0:
        print("⚠️ ГОЛОСА НЕ НАЙДЕНЫ!")
        print("   Установите дополнительные голоса через:")
        print("   Параметры Windows → Время и язык → Речь → Управление голосами")
    else:
        for i, voice in enumerate(voices, 1):
            print(f"Голос #{i}:")
            print(f"  Имя: {getattr(voice, 'name', 'N/A')}")
            print(f"  ID: {getattr(voice, 'id', 'N/A')}")
            print(f"  Языки: {getattr(voice, 'languages', [])}")
            print(f"  Пол: {getattr(voice, 'gender', 'N/A')}")
            print(f"  Возраст: {getattr(voice, 'age', 'N/A')}")
            print()

    engine.stop()

except Exception as e:
    print(f"❌ ОШИБКА: {e}")

print("=" * 60)
print("\nДля добавления русских голосов:")
print("1. Откройте Параметры Windows")
print("2. Перейдите: Время и язык → Речь")
print("3. Нажмите 'Добавить голоса'")
print("4. Найдите и установите русские голоса Microsoft")
print("=" * 60)
