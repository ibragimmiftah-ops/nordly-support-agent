"""Authenticated encryption for sensitive application fields."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

PREFIX = "enc:v1:"


def _fernet() -> Fernet:
    """Build a Fernet instance from configured key material."""
    material = settings.encryption_key or settings.jwt_secret
    try:
        return Fernet(material.encode())
    except (ValueError, TypeError):
        key = base64.urlsafe_b64encode(hashlib.sha256(material.encode()).digest())
        return Fernet(key)


def encrypt(value: str | None) -> str | None:
    """Encrypt text, preserving null values and avoiding double encryption."""
    if value is None or value.startswith(PREFIX):
        return value
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value: str | None) -> str | None:
    """Decrypt managed ciphertext while allowing legacy plaintext reads."""
    if value is None or not value.startswith(PREFIX):
        return value
    try:
        return _fernet().decrypt(value.removeprefix(PREFIX).encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Sensitive value authentication failed") from exc
