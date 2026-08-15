"""JWT creation and validation."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

import jwt

from app.auth.models import Principal, Role
from app.config import settings


def create_token(
    principal: Principal,
    token_type: Literal["access", "refresh"],
    *,
    jti: str | None = None,
    session_id: str | None = None,
) -> str:
    """Create a short-lived access token or longer-lived refresh token."""
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"  # nosec B105
        else timedelta(days=settings.refresh_token_days)
    )
    payload = {
        "sub": principal.subject,
        "tenant_id": principal.tenant_id,
        "role": principal.role.value,
        "type": token_type,
        "iat": now,
        "exp": now + lifetime,
        "jti": jti or uuid.uuid4().hex,
    }
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> Principal:
    """Validate a JWT and convert its claims to a principal."""
    payload = decode_token_claims(token, expected_type)
    return Principal(
        subject=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=Role(payload["role"]),
        auth_method="jwt",
    )


def decode_token_claims(
    token: str, expected_type: Literal["access", "refresh"]
) -> dict[str, object]:
    """Validate a JWT and return its claims for bounded session checks."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload
