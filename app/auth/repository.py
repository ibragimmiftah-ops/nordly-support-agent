"""Bounded persistence for authentication identities."""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta

from app.auth.models import Principal, Role
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_token, decode_token_claims
from app.config import settings
from app.database import get_connection


def api_key_digest(api_key: str) -> str:
    """Return a stable keyed digest suitable for lookup and rate-limit identity."""
    return hmac.new(settings.jwt_secret.encode(), api_key.encode(), hashlib.sha256).hexdigest()


def _refresh_jti_digest(jti: str) -> str:
    """Key and hash refresh identifiers so neither tokens nor raw JTIs are persisted."""
    return hmac.new(settings.jwt_secret.encode(), jti.encode(), hashlib.sha256).hexdigest()


class AuthRepository:
    """Authenticate users and API keys without exposing broad database access."""

    @staticmethod
    def ensure_demo_credentials() -> None:
        """Provision idempotent test/demo credentials as hashes."""
        if not settings.is_demo_mode:
            raise RuntimeError("Demo credentials cannot be provisioned outside demo mode")
        with get_connection() as conn:
            user = conn.execute(
                "SELECT user_id FROM auth_users WHERE tenant_id = ? AND username = ?",
                (settings.demo_tenant_id, settings.demo_admin_username),
            ).fetchone()
            if not user:
                conn.execute(
                    "INSERT INTO auth_users "
                    "(user_id, tenant_id, username, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"usr-{uuid.uuid4().hex}",
                        settings.demo_tenant_id,
                        settings.demo_admin_username,
                        hash_password(settings.demo_admin_password),
                        Role.ADMIN.value,
                    ),
                )
            digest = api_key_digest(settings.demo_api_key)
            if not conn.execute(
                "SELECT key_id FROM api_keys WHERE key_hash = ?", (digest,)
            ).fetchone():
                conn.execute(
                    "INSERT INTO api_keys "
                    "(key_id, tenant_id, principal, key_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"key-{uuid.uuid4().hex}",
                        settings.demo_tenant_id,
                        "demo-api-key",
                        digest,
                        Role.ADMIN.value,
                    ),
                )
            conn.commit()

    @staticmethod
    def ensure_production_admin() -> None:
        """Idempotently create only an explicitly configured production administrator."""
        if settings.is_demo_mode or not settings.production_bootstrap_configured:
            raise RuntimeError("Explicit production bootstrap configuration is required")
        tenant = settings.bootstrap_admin_tenant
        username = settings.bootstrap_admin_username
        password = settings.bootstrap_admin_password
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT user_id FROM auth_users WHERE tenant_id = ? AND username = ?",
                (tenant, username),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO auth_users "
                    "(user_id, tenant_id, username, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                    (
                        f"usr-{uuid.uuid4().hex}",
                        tenant,
                        username,
                        hash_password(password),
                        Role.ADMIN.value,
                    ),
                )
                conn.commit()

    @staticmethod
    def authenticate_password(tenant_id: str, username: str, password: str) -> Principal | None:
        """Authenticate an active user by username and password."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT user_id, tenant_id, password_hash, role FROM auth_users "
                "WHERE tenant_id = ? AND username = ? AND active IS TRUE",
                (tenant_id, username),
            ).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return Principal(
            subject=row["user_id"],
            tenant_id=row["tenant_id"],
            role=Role(row["role"]),
            auth_method="password",
        )

    @staticmethod
    def current_user(subject: str, tenant_id: str) -> Principal | None:
        """Load the current active role instead of trusting mutable JWT claims."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT user_id, tenant_id, role FROM auth_users "
                "WHERE user_id = ? AND tenant_id = ? AND active IS TRUE",
                (subject, tenant_id),
            ).fetchone()
        if not row:
            return None
        return Principal(
            subject=row["user_id"],
            tenant_id=row["tenant_id"],
            role=Role(row["role"]),
            auth_method="jwt",
        )

    @staticmethod
    def authenticate_api_key(api_key: str) -> Principal | None:
        """Authenticate an API key via keyed digest lookup."""
        with get_connection() as conn:
            row = conn.execute(
                "SELECT tenant_id, principal, role FROM api_keys "
                "WHERE key_hash = ? AND active IS TRUE",
                (api_key_digest(api_key),),
            ).fetchone()
        if not row:
            return None
        return Principal(
            subject=row["principal"],
            tenant_id=row["tenant_id"],
            role=Role(row["role"]),
            auth_method="api_key",
        )

    @staticmethod
    def create_refresh_session(principal: Principal) -> str:
        """Persist and issue a refresh token for an active user."""
        if not AuthRepository.current_user(principal.subject, principal.tenant_id):
            raise ValueError("Inactive user")
        session_id = uuid.uuid4().hex
        jti = uuid.uuid4().hex
        expires_at = (datetime.now(UTC) + timedelta(days=settings.refresh_token_days)).isoformat()
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO refresh_sessions "
                "(session_id, jti_hash, tenant_id, user_id, expires_at) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    _refresh_jti_digest(jti),
                    principal.tenant_id,
                    principal.subject,
                    expires_at,
                ),
            )
            conn.commit()
        return create_token(principal, "refresh", jti=jti, session_id=session_id)

    @staticmethod
    def rotate_refresh_session(token: str) -> tuple[Principal, str] | None:
        """Atomically consume one refresh session and persist its replacement."""
        claims = decode_token_claims(token, "refresh")
        session_id = str(claims["sid"])
        jti_hash = _refresh_jti_digest(str(claims["jti"]))
        subject = str(claims["sub"])
        tenant_id = str(claims["tenant_id"])
        now = datetime.now(UTC).isoformat()
        new_session_id = uuid.uuid4().hex
        new_jti = uuid.uuid4().hex
        expires_at = (datetime.now(UTC) + timedelta(days=settings.refresh_token_days)).isoformat()
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE refresh_sessions SET used_at = ? "
                "WHERE session_id = ? AND jti_hash = ? AND tenant_id = ? AND user_id = ? "
                "AND used_at IS NULL AND revoked_at IS NULL AND expires_at > ?",
                (now, session_id, jti_hash, tenant_id, subject, now),
            )
            if cursor.rowcount != 1:
                conn.rollback()
                return None
            row = conn.execute(
                "SELECT user_id, tenant_id, role FROM auth_users "
                "WHERE user_id = ? AND tenant_id = ? AND active IS TRUE",
                (subject, tenant_id),
            ).fetchone()
            if not row:
                conn.rollback()
                return None
            principal = Principal(
                subject=row["user_id"],
                tenant_id=row["tenant_id"],
                role=Role(row["role"]),
                auth_method="jwt",
            )
            conn.execute(
                "INSERT INTO refresh_sessions "
                "(session_id, jti_hash, tenant_id, user_id, expires_at) VALUES (?, ?, ?, ?, ?)",
                (new_session_id, _refresh_jti_digest(new_jti), tenant_id, subject, expires_at),
            )
            conn.commit()
        return principal, create_token(principal, "refresh", jti=new_jti, session_id=new_session_id)

    @staticmethod
    def revoke_refresh_session(token: str) -> bool:
        """Revoke an unused refresh session belonging to a current active user."""
        claims = decode_token_claims(token, "refresh")
        now = datetime.now(UTC).isoformat()
        with get_connection() as conn:
            cursor = conn.execute(
                "UPDATE refresh_sessions SET revoked_at = ? WHERE session_id = ? AND jti_hash = ? "
                "AND tenant_id = ? AND user_id = ? AND used_at IS NULL AND revoked_at IS NULL "
                "AND expires_at > ? AND EXISTS (SELECT 1 FROM auth_users WHERE user_id = ? "
                "AND tenant_id = ? AND active IS TRUE)",
                (
                    now,
                    str(claims["sid"]),
                    _refresh_jti_digest(str(claims["jti"])),
                    str(claims["tenant_id"]),
                    str(claims["sub"]),
                    now,
                    str(claims["sub"]),
                    str(claims["tenant_id"]),
                ),
            )
            conn.commit()
            return cursor.rowcount == 1
