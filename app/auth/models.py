"""Authenticated principal models."""

from enum import StrEnum

from pydantic import BaseModel


class Role(StrEnum):
    """Supported application roles."""

    ADMIN = "admin"
    AGENT = "agent"
    VIEWER = "viewer"


class Principal(BaseModel):
    """Verified user or API-key identity."""

    subject: str
    tenant_id: str
    role: Role
    auth_method: str
