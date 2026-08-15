"""FastAPI authentication and RBAC dependencies."""

from collections.abc import AsyncIterator, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import Principal, Role
from app.auth.repository import AuthRepository
from app.auth.tokens import decode_token
from app.tenant import bind_tenant, reset_tenant

bearer = HTTPBearer(auto_error=False)


async def require_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AsyncIterator[Principal]:
    """Accept either a valid access JWT or an API key."""
    principal = None
    api_key = request.headers.get("X-API-Key")
    if api_key:
        principal = AuthRepository.authenticate_api_key(api_key)
    elif credentials and credentials.scheme.lower() == "bearer":
        try:
            claimed = decode_token(credentials.credentials, "access")
            principal = AuthRepository.current_user(claimed.subject, claimed.tenant_id)
        except (jwt.PyJWTError, KeyError, ValueError):
            principal = None
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.principal = principal
    token = bind_tenant(principal.tenant_id)
    try:
        yield principal
    finally:
        reset_tenant(token)


def require_roles(*roles: Role) -> Callable:
    """Build a dependency requiring one of the supplied roles."""

    async def dependency(
        principal: Annotated[Principal, Depends(require_principal)],
    ) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return principal

    return dependency
