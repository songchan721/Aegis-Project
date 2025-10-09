import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..logging import get_logger

logger = get_logger(__name__)


class SecretManager:
    """시크릿 관리자"""

    def __init__(self, encryption_key: Optional[str] = None):
        self.encryption_key = encryption_key or os.getenv("SECRET_ENCRYPTION_KEY")
        self.fernet = None

        if self.encryption_key:
            # 키를 바이트로 변환
            if len(self.encryption_key) < 32:
                # 키 파생
                self.encryption_key = self._derive_key(self.encryption_key)

            self.fernet = Fernet(
                base64.urlsafe_b64encode(
                    self.encryption_key.encode()[:32].ljust(32, b"0")
                )
            )

    def _derive_key(self, key: str) -> str:
        """키 파생"""
        salt = b"aegis_secret_salt_2025"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return derived_key.decode()

    def encrypt_secret(self, secret_value: str) -> str:
        """시크릿 암호화"""
        if not self.fernet:
            raise ValueError("Encryption key not configured")

        encrypted = self.fernet.encrypt(secret_value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_secret(self, encrypted_secret: str) -> str:
        """시크릿 복호화"""
        if not self.fernet:
            raise ValueError("Encryption key not configured")

        try:
            encrypted = base64.urlsafe_b64decode(encrypted_secret.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error("secret_decryption_failed", error=str(e))
            raise ValueError("Failed to decrypt secret")

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """환경 변수에서 시크릿 조회"""
        value = os.getenv(key, default)

        # 암호화된 시크릿인지 확인
        if value and self._is_encrypted(value):
            try:
                return self.decrypt_secret(value)
            except Exception as e:
                logger.error("failed_to_decrypt_secret", key=key, error=str(e))
                return default

        return value

    def _is_encrypted(self, value: str) -> bool:
        """암호화된 값인지 확인"""
        try:
            # Base64 디코딩 시도
            decoded = base64.urlsafe_b64decode(value.encode())
            # Fernet 토큰 구조 확인 (간단한 체크)
            return len(decoded) > 57  # Fernet 토큰 최소 길이
        except Exception:
            return False

    def get_database_url(self) -> str:
        """데이터베이스 URL 조회 (비밀번호 복호화)"""
        url = self.get_secret("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL not configured")
        return url

    def get_jwt_secret(self) -> str:
        """JWT 시크릿 조회"""
        secret = self.get_secret("JWT_SECRET")
        if not secret:
            raise ValueError("JWT_SECRET not configured")
        return secret

    def get_redis_url(self) -> str:
        """Redis URL 조회 (비밀번호 복호화)"""
        url = self.get_secret("REDIS_URL", "redis://localhost:6379/0")
        return url

    def get_kafka_servers(self) -> str:
        """Kafka 서버 목록 조회"""
        servers = self.get_secret("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        return servers


# 전역 시크릿 관리자
_secret_manager = SecretManager()


def get_secret_manager() -> SecretManager:
    """전역 시크릿 관리자 조회"""
    return _secret_manager


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """시크릿 조회"""
    return _secret_manager.get_secret(key, default)


def get_database_url() -> str:
    """데이터베이스 URL 조회"""
    return _secret_manager.get_database_url()


def get_jwt_secret() -> str:
    """JWT 시크릿 조회"""
    return _secret_manager.get_jwt_secret()


def get_redis_url() -> str:
    """Redis URL 조회"""
    return _secret_manager.get_redis_url()


def get_kafka_servers() -> str:
    """Kafka 서버 목록 조회"""
    return _secret_manager.get_kafka_servers()
