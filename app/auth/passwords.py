"""Password hashing helpers."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with an automatically generated salt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password without exposing parsing failures."""
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except (ValueError, TypeError):
        return False
