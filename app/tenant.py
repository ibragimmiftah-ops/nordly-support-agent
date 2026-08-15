"""Request-local tenant context used by PostgreSQL row-level security."""

from contextvars import ContextVar, Token

tenant_id_context: ContextVar[str | None] = ContextVar("tenant_id", default=None)


def bind_tenant(tenant_id: str) -> Token[str | None]:
    """Bind a validated tenant for the current request or operation."""
    return tenant_id_context.set(tenant_id)


def reset_tenant(token: Token[str | None]) -> None:
    """Restore the previous tenant context."""
    tenant_id_context.reset(token)
