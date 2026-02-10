import os
import sys
import shutil
from crypto_utils import decrypt_address


# --- 1. СИСТЕМНЫЕ НАСТРОЙКИ ---
def get_base_path():
    """
    Определяет базовую папку программы:
    - Если запущено из exe (PyInstaller): использует _MEIPASS
    - Если запущено из launcher.py: использует переменную окружения TFALER_HOME
    - Иначе: использует директорию текущего скрипта
    """
    # Проверяем переменную окружения (для launcher.py)
    if "TFALER_HOME" in os.environ:
        return os.environ["TFALER_HOME"]

    if hasattr(sys, "_MEIPASS"):
        # PyInstaller: используем _MEIPASS как базовую директорию
        return sys._MEIPASS

    # Разработка: используем директорию скрипта
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = get_base_path()
SOUNDS_DIR = os.path.join(BASE_DIR, "Sounds")
SOUND_DIR_VOICE = os.path.join(SOUNDS_DIR, "Voice")
SOUND_DIR_TICK = os.path.join(SOUNDS_DIR, "Tick")
SOUND_DIR_TRANSITION = os.path.join(SOUNDS_DIR, "Transition")
LOGO_DIR = os.path.join(BASE_DIR, "Logo")
LOGO_PATH = os.path.join(LOGO_DIR, "Logo.png")


# Проверяем наличие файлов и выводим путь для отладки
def _validate_paths():
    if not os.path.exists(LOGO_PATH):
        print(f"⚠️ Логотип не найден: {LOGO_PATH}")
        print(f"BASE_DIR: {BASE_DIR}")
        print(f"LOGO_DIR: {LOGO_DIR}")
        # Пробуем альтернативный путь
        alt_logo = os.path.join(BASE_DIR, "..", "..", "Logo", "Logo.png")
        if os.path.exists(alt_logo):
            return os.path.abspath(alt_logo)
    return LOGO_PATH


LOGO_PATH = _validate_paths()

# --- 2. НАСТРОЙКИ ПРИЛОЖЕНИЯ ---
APP_NAME = "TF-Alerter"
APP_VERSION = "1.0"
WINDOW_SIZE = (360, 500)

# --- ИНФОРМАЦИЯ ОБ АВТОРЕ ---
AUTHOR_NAME = "IntrovertScalp"
YOUTUBE_URL = "https://www.youtube.com/@Introvert_Scalp"

# --- КРИПТОАДРЕСА ДЛЯ ДОНАТОВ (ЗАШИФРОВАНЫ) ---
# Адреса зашифрованы для защиты от простого редактирования
# При добавлении новых адресов используй crypto_utils.encrypt_address()

_CRYPTO_ADDRESSES_ENCRYPTED = {
    "BTC": {
        "label": "Bitcoin (BTC)",
        "network": "Bitcoin",
        "address_encrypted": "gAAAAABph7GCESgAbLvXZtOPd3zTsu5Z8PD4IX2R51DMGs-27min4nWBWBh1owbKkCqo7LDQEN5P4T80X1k3a4ZglTQTTEFPM9I3ZLqjpf0ZMw8NmQigCZSBRqahlpuLGlsTb_DtEqdQ",
    },
    "ETH": {
        "label": "Ethereum (ETH)",
        "network": "ERC20",
        "address_encrypted": "gAAAAABph7GCgttLmOxp_gN4EqpcTDowQ3DRllnYF6rZAYwAo5xW4J_KjH-aeGWe2dYDHDlJ2smLH9Tz8MjLIVh3DSaZ_qNg7miNylxnIWerBwB9p66P9Yni3wfMe2unmvEoD2ynQZHb",
    },
    "BNB": {
        "label": "BNB (Binance Coin)",
        "network": "BEP20 (BSC)",
        "address_encrypted": "gAAAAABph7GCu-nNBsdg-IAkBNRQmZgb-x4LHLV5DQzomhUlIFgMazURcvmSEc7my5K8GshGu9be8RMFoutdRDthl7hYniAqNbrbVb8awh5sUUsLWXUbzbQbHDeb87VyZsB6PZWs99QD",
    },
    "USDT_BEP20": {
        "label": "USDT",
        "network": "BEP20 (BNB Smart Chain)",
        "address_encrypted": "gAAAAABph7GCxnniEWQGR1sPqLb2qmLX9knwGAhShwtQfK1RdnVVx9QP3qhkvc_zrfq7pzkOaFNx9VbHkjzaP30WXj6Mz4Bq4c2jxdSbgytE4nylagmlz00uPrTXhIhcBj7EQRfiSb97",
    },
    "USDT_TRC20": {
        "label": "USDT",
        "network": "TRC20 (Tron)",
        "address_encrypted": "gAAAAABph7GC3r7cDg1e5rJ00mrPq7dd01m9aY2A9jpcXiDhFCTcNw676LY3kfM52ZgKp_XpK7gfbjyKK3pG1wUL0TWUyzZPQJiHGF56ppqX85irjq-Qv16xgfhgxkjE_WRcBPEfRig2",
    },
    "USDT_ERC20": {
        "label": "USDT",
        "network": "ERC20 (Ethereum)",
        "address_encrypted": "gAAAAABph7GCvzfJuzid6w1eVm9R356IsaWDEXX16jbdBs2ENwvmMTA0Wfn4at7JY-3bd8QxXVVI-zYXqafVhnAJnOxWSdsIuSSOAFPJXR4_q7xPPu_vZ0iXQU_kTaRVaTNEFBaZF6n_",
    },
}


def _decrypt_crypto_addresses():
    """Расшифровывает адреса при инициализации"""
    global CRYPTO_ADDRESSES
    CRYPTO_ADDRESSES = {}
    for key, data in _CRYPTO_ADDRESSES_ENCRYPTED.items():
        CRYPTO_ADDRESSES[key] = {
            "label": data["label"],
            "network": data["network"],
            "address": decrypt_address(data["address_encrypted"]),
        }


# Расшифровываем адреса при импорте
_decrypt_crypto_addresses()

# --- 3. ЦВЕТОВАЯ СХЕМА ---
COLORS = {
    "background": "#121212",
    "panel": "#1e1e1e",
    "text": "#e0e0e0",
    "accent": "#1e90ff",
    "danger": "#e81123",
    "danger_hover": "#f1707a",
    "border": "#333333",
    "hover": "#3e3e42",
}

# --- 4. НАСТРОЙКИ ТАЙМЕРА И ЗВУКА ---
# За сколько секунд до закрытия включать ГОЛОС
VOICE_LEAD_TIME = 10

# 💡 СОВЕТ О ЗВУКАХ:
# Громкость в программе идёт от 0% до 100% для чистого звучания.
# Если нужно громче - увеличьте громкость в настройках Windows.
# Добавляйте звуки в формате WAV или MP3.

# Файлы тиканья (должны лежать в папке sounds)
SOUND_TICK = "tick.wav"  # Обычный тик (5, 4, 3, 2 сек)
SOUND_TICK_LONG = "transition.wav"  # Длинный тик (1 сек)


def get_sound_dir(kind: str) -> str:
    if kind in ("main", "voice"):
        return SOUND_DIR_VOICE
    if kind == "tick":
        return SOUND_DIR_TICK
    if kind == "transition":
        return SOUND_DIR_TRANSITION
    return SOUNDS_DIR


def get_sound_path(kind: str, filename: str) -> str:
    if not filename:
        return ""
    preferred = os.path.join(get_sound_dir(kind), filename)
    if os.path.exists(preferred):
        return preferred
    # Backward compatibility: allow files in the base Sounds folder
    fallback = os.path.join(SOUNDS_DIR, filename)
    return fallback


def _ensure_sound_dirs():
    for path in (SOUNDS_DIR, SOUND_DIR_VOICE, SOUND_DIR_TICK, SOUND_DIR_TRANSITION):
        os.makedirs(path, exist_ok=True)


def _migrate_sound_file(kind: str, filename: str):
    if not filename:
        return
    src = os.path.join(SOUNDS_DIR, filename)
    dst = os.path.join(get_sound_dir(kind), filename)
    if not os.path.exists(src):
        return
    if os.path.exists(dst):
        return
    try:
        shutil.move(src, dst)
    except Exception:
        pass


def migrate_sounds_to_subdirs():
    _ensure_sound_dirs()
    items = set()

    for data in TIMEFRAMES.values():
        items.add(("main", data.get("file")))

    for filename in SOUND_TICK_BY_TF.values():
        items.add(("tick", filename))

    for filename in SOUND_TRANSITION_BY_TF.values():
        items.add(("transition", filename))

    items.add(("tick", SOUND_TICK))
    items.add(("transition", SOUND_TICK_LONG))

    for kind, filename in items:
        _migrate_sound_file(kind, filename)


# Список таймфреймов
TIMEFRAMES = {
    "1m": {"file": "1m_voice.wav", "seconds": 60, "label": "1 Минута"},
    "5m": {"file": "5m_voice.wav", "seconds": 300, "label": "5 Минут"},
    "15m": {"file": "15m_voice.wav", "seconds": 900, "label": "15 Минут"},
    "1h": {"file": "1h_voice.wav", "seconds": 3600, "label": "1 Час"},
    "4h": {"file": "4h_voice.wav", "seconds": 14400, "label": "4 Часа"},
    "1d": {"file": "1d_voice.wav", "seconds": 86400, "label": "1 День"},
    "1w": {"file": "1w_voice.wav", "seconds": 604800, "label": "1 Неделя"},
    "1M": {"file": "1Mo_voice.wav", "seconds": 2592000, "label": "1 Месяц"},
}

# Переводы для таймфреймов
TIMEFRAME_LABELS = {
    "RU": {
        "1m": "1 Минута",
        "5m": "5 Минут",
        "15m": "15 Минут",
        "1h": "1 Час",
        "4h": "4 Часа",
        "1d": "1 День",
        "1w": "1 Неделя",
        "1M": "1 Месяц",
    },
    "EN": {
        "1m": "1 Minute",
        "5m": "5 Minutes",
        "15m": "15 Minutes",
        "1h": "1 Hour",
        "4h": "4 Hours",
        "1d": "1 Day",
        "1w": "1 Week",
        "1M": "1 Month",
    },
}


def get_timeframe_label(tf_key, lang="RU"):
    """Получить переведённое название таймфрейма"""
    return TIMEFRAME_LABELS.get(lang, {}).get(tf_key, TIMEFRAMES[tf_key]["label"])


# Персональные звуки для каждого ТФ (уникальные для каждого таймфрейма)
# Для 1M (месяца) используем префикс 1Mo вместо 1M

# VOICE звуки (колонка 1 - основной голосовой алерт)
for tf_key in TIMEFRAMES.keys():
    if tf_key == "1M":
        TIMEFRAMES[tf_key]["file"] = "1Mo_voice.wav"
    else:
        TIMEFRAMES[tf_key]["file"] = f"{tf_key}_voice.wav"

# TICK звуки (колонка 2 - отсчет последних 5 секунд)
SOUND_TICK_BY_TF = {}
for tf_key in TIMEFRAMES.keys():
    if tf_key == "1M":
        SOUND_TICK_BY_TF[tf_key] = "1Mo_tick.wav"
    else:
        SOUND_TICK_BY_TF[tf_key] = f"{tf_key}_tick.wav"

# TRANSITION звуки (колонка 3 - переход на 59-ю секунду)
SOUND_TRANSITION_BY_TF = {}
for tf_key in TIMEFRAMES.keys():
    if tf_key == "1M":
        SOUND_TRANSITION_BY_TF[tf_key] = "1Mo_transition.wav"
    else:
        SOUND_TRANSITION_BY_TF[tf_key] = f"{tf_key}_transition.wav"
# Конфигурация overlay часов
OVERLAY_SHOW_MODE = "custom"  # "always" или "custom" (только для указанных приложений)
OVERLAY_WINDOWS = [
    "Profit Forge",
    "TF-Alerter",
]  # Список приложений для отображения overlay
