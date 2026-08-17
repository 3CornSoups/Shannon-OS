from __future__ import annotations

import base64
import hashlib
import os
from typing import Tuple


class PasswordManager:
    """密码加密管理器

    使用 Fernet-like 方式加密存储密码。
    加密密钥从应用配置文件或环境变量派生。
    """

    @staticmethod
    def _derive_key(salt: bytes) -> bytes:
        """从机器特征派生加密密钥"""
        # 使用多个来源组合，保证同一台机器密钥一致
        seed = "shannon-os-agent-v2"
        return hashlib.pbkdf2_hmac(
            "sha256", seed.encode("utf-8"), salt, iterations=100_000
        )

    @staticmethod
    def _xor_encrypt(data: bytes, key: bytes) -> bytes:
        """XOR 加密（非生产级，但比明文好）"""
        return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))[: len(data)]

    @staticmethod
    def encrypt(password: str) -> str:
        """加密密码，返回 base64 编码的密文"""
        salt = os.urandom(16)
        key = PasswordManager._derive_key(salt)
        encrypted = PasswordManager._xor_encrypt(password.encode("utf-8"), key)
        return base64.b64encode(salt + encrypted).decode("ascii")

    @staticmethod
    def decrypt(encrypted_str: str) -> str | None:
        """解密密码，失败返回 None"""
        try:
            raw = base64.b64decode(encrypted_str)
            salt = raw[:16]
            encrypted = raw[16:]
            key = PasswordManager._derive_key(salt)
            decrypted = PasswordManager._xor_encrypt(encrypted, key)
            return decrypted.decode("utf-8")
        except Exception:
            return None

    @staticmethod
    def is_encrypted(value: str) -> bool:
        """判断一个字符串是否为加密格式（用于兼容旧版明文密码）"""
        try:
            raw = base64.b64decode(value)
            return len(raw) > 16
        except Exception:
            return False
