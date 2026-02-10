#!/usr/bin/env python3
"""
Скрипт для генерации и шифрования адресов кошельков
Запусти этот скрипт один раз, чтобы зашифровать свои адреса
"""

from crypto_utils import encrypt_address, generate_new_key


def encrypt_your_addresses():
    """Зашифруй свои адреса"""

    print("=" * 60)
    print("ШИФРОВАНИЕ АДРЕСОВ КОШЕЛЬКОВ")
    print("=" * 60)
    print()

    # Твои реальные адреса (замени на свои)
    your_addresses = {
        "BTC": "bc1qrzyz9j44hj0ex9q33fhghwxhg2clysxyq0ps9f",
        "ETH": "0x416E6544D8DCD9C4dDa2C10D394480F89642FaD7",
        "BNB": "0x416E6544D8DCD9C4dDa2C10D394480F89642FaD7",
        "USDT_BEP20": "0x416E6544D8DCD9C4dDa2C10D394480F89642FaD7",
        "USDT_TRC20": "TPuCWaaHgdCJEjhRp1wG1wQbWHgkd9Rpdq",
        "USDT_ERC20": "0x416E6544D8DCD9C4dDa2C10D394480F89642FaD7",
    }

    print("Зашифровываем адреса...\n")

    encrypted_config = {}
    for coin, address in your_addresses.items():
        encrypted = encrypt_address(address)
        encrypted_config[coin] = encrypted
        print(f"{coin}:")
        print(f"  Оригинал: {address}")
        print(f"  Зашифрован: {encrypted[:50]}...")
        print()

    print("=" * 60)
    print("ИНСТРУКЦИЯ:")
    print("=" * 60)
    print()
    print("1. Скопируй зашифрованные адреса выше")
    print("2. Открой config.py")
    print("3. Найди _CRYPTO_ADDRESSES_ENCRYPTED")
    print(
        "4. Замени все 'address' на 'address_encrypted' и вставь зашифрованные значения"
    )
    print()
    print("Пример для config.py:")
    print(
        """
    "BTC": {
        "label": "Bitcoin (BTC)",
        "network": "Bitcoin",
        "address_encrypted": "{encrypted_address}",
    },
    """
    )
    print()
    print("КОГДА ГОТОВО - ПЕРЕСОБЕРИ ПРОГРАММУ:")
    print(
        'pyinstaller --onedir --windowed --add-data "Logo;Logo" --add-data "Sounds;Sounds" --add-data "DopSounds;DopSounds" --icon="Logo\\Logo.png" --name "TF-Alerter" main.py'
    )
    print()


if __name__ == "__main__":
    encrypt_your_addresses()
