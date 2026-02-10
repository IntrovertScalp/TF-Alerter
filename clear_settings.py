#!/usr/bin/env python3
"""Очищает все звуковые настройки из QSettings"""

from PyQt6.QtCore import QSettings

settings = QSettings("MyTradeTools", "TF-Alerter")

# Удаляем все звуковые настройки
for tf_key in ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M", "1Month"]:
    settings.remove(f"sound_main_{tf_key}")
    settings.remove(f"sound_tick_{tf_key}")
    settings.remove(f"sound_transition_{tf_key}")
    print(f"Очищены настройки для {tf_key}")

settings.sync()
print("QSettings очищены!")

# Проверяем
print("\nПроверка - оставшиеся звуковые ключи:")
settings = QSettings("MyTradeTools", "TF-Alerter")
all_keys = settings.allKeys()
sound_keys = [k for k in all_keys if "sound" in k]
print(f"Звуковых ключей осталось: {len(sound_keys)}")
if sound_keys:
    for k in sound_keys:
        print(f"  {k}: {settings.value(k)}")
else:
    print("  (нет)")
