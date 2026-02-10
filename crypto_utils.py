"""
Шифрование адресов кошельков для защиты от простого редактирования
"""

from cryptography.fernet import Fernet

# Встроенный ключ (генерируется при сборке, хранится в коде)
# Это не 100% защита, но затруднит простой поиск/замену адресов
ENCRYPTION_KEY = b"UEVQhZ2o5adZU_AidULpC4hKGC_eLKBdhewNq5NP-R4="


def get_cipher():
    """Получить шифр для энкрипции/декрипции"""
    return Fernet(ENCRYPTION_KEY)


def encrypt_address(address: str) -> str:
    """Зашифровать адрес кошелька"""
    cipher = get_cipher()
    encrypted = cipher.encrypt(address.encode())
    return encrypted.decode()


def decrypt_address(encrypted_address: str) -> str:
    """Расшифровать адрес кошелька"""
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_address.encode())
        return decrypted.decode()
    except Exception:
        # Если ошибка расшифровки - вернуть как есть
        return encrypted_address


def generate_new_key():
    """Генерирует новый ключ (используй для создания своего ключа)"""
    new_key = Fernet.generate_key()
    print(f"Новый ключ: {new_key.decode()}")
    print("Скопируй его в ENCRYPTION_KEY в crypto_utils.py")
    return new_key
