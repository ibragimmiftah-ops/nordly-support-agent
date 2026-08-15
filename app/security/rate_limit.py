"""Distributed production and in-process demo request rate limiting."""

import hashlib
import threading
import time
from collections import defaultdict, deque

import jwt
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.auth.repository import AuthRepository, api_key_digest
from app.auth.tokens import decode_token
from app.config import settings

_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return current
"""


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limit requests by network source and stable validated principal identity."""

    def __init__(self, app) -> None:
        """Use Redis in production and isolated memory buckets in demo mode."""
        super().__init__(app)
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()
        self._redis = None
        if not settings.is_demo_mode:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)

    @staticmethod
    def _principal_key(request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            principal = AuthRepository.authenticate_api_key(api_key)
            return f"api:{api_key_digest(api_key)}" if principal else "anonymous"
        authorization = request.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            try:
                claimed = decode_token(authorization.split(" ", 1)[1], "access")
                current = AuthRepository.current_user(claimed.subject, claimed.tenant_id)
                if current:
                    identity = f"{current.tenant_id}:{current.subject}"
                    return "jwt:" + hashlib.sha256(identity.encode()).hexdigest()
            except (jwt.PyJWTError, KeyError, ValueError):
                pass
        return "anonymous"

    async def dispatch(self, request: Request, call_next):
        """Apply source and principal limits per endpoint."""
        if request.url.path in {"/health", "/ready"} or request.url.path.startswith("/metrics"):
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        suffix = f":{request.method}:{request.url.path}"
        keys = (
            f"nordly:rate:ip:{ip}{suffix}",
            f"nordly:rate:principal:{self._principal_key(request)}{suffix}",
        )
        limit = settings.rate_limit_requests
        window = settings.rate_limit_window_seconds
        if self._redis is not None:
            counts = [int(await self._redis.eval(_SCRIPT, 1, key, window)) for key in keys]
            fullest = max(counts)
            if fullest > limit:
                return self._blocked(window, limit)
            remaining = limit - fullest
        else:
            remaining = self._consume_memory(keys, limit, window)
            if remaining is None:
                return self._blocked(window, limit)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _consume_memory(self, keys: tuple[str, str], limit: int, window: int) -> int | None:
        now = time.monotonic()
        with self._lock:
            buckets = [self._events[key] for key in keys]
            for events in buckets:
                while events and events[0] <= now - window:
                    events.popleft()
            if any(len(events) >= limit for events in buckets):
                return None
            for events in buckets:
                events.append(now)
            return max(0, limit - max(map(len, buckets)))

    @staticmethod
    def _blocked(window: int, limit: int) -> JSONResponse:
        return JSONResponse(
            {"detail": "Rate limit exceeded"},
            status_code=429,
            headers={
                "Retry-After": str(window),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
