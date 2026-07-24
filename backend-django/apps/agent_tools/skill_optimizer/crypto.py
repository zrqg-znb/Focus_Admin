"""Skill Optimizer 自有凭证加密能力，不依赖其他业务应用。"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CredentialCipher:
    """用 Django 密钥派生 Fernet 密钥，确保凭证不会明文入库。"""

    def __init__(self) -> None:
        raw_key = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(raw_key))

    def encrypt(self, value: str) -> str:
        """加密 API Key；空值保持为空，便于编辑时保留旧凭证。"""
        return self._fernet.encrypt(value.encode('utf-8')).decode('utf-8') if value else ''

    def decrypt(self, value: str) -> str:
        """解密 API Key；遇到历史无效值时返回空字符串。"""
        if not value:
            return ''
        try:
            return self._fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            return ''


credential_cipher = CredentialCipher()
