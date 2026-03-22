import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet
from django.conf import settings


class EncryptionService:
    _instance: Optional['EncryptionService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._fernet = cls._build_fernet()
        return cls._instance

    @staticmethod
    def _build_fernet() -> Fernet:
        key_bytes = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
        return Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt(self, value: str) -> str:
        if not value:
            return ''
        return self._fernet.encrypt(value.encode('utf-8')).decode('utf-8')

    def decrypt(self, value: str) -> str:
        if not value:
            return ''
        try:
            return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except Exception:
            return value

    def is_encrypted(self, value: str) -> bool:
        if not value:
            return False
        try:
            self._fernet.decrypt(value.encode('utf-8'))
            return True
        except Exception:
            return False


encryption_service = EncryptionService()


def encrypt_value(value: str) -> str:
    return encryption_service.encrypt(value)



def decrypt_value(value: str) -> str:
    return encryption_service.decrypt(value)
