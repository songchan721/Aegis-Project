import bcrypt
from cryptography.fernet import Fernet


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_key() -> bytes:
    return Fernet.generate_key()


def encrypt(data: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(data)


def decrypt(token: bytes, key: bytes) -> bytes:
    f = Fernet(key)
    return f.decrypt(token)
