"""FastAPI application entry point for Nordly Support Agent."""

import re
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.api.routes import router
from app.config import settings
from app.observability import (
    configure_logging,
    configure_tracing,
    correlation_context,
    get_logger,
    metrics,
    shutdown_tracing,
)
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import RateLimitMiddleware

logger = get_logger(__name__)
_CORRELATION_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize persistent application resources before serving requests."""
    from app.auth.repository import AuthRepository
    from app.database import init_database
    from app.repositories.retention_repository import RetentionRepository

    configure_logging(settings.log_level)
    configure_tracing(application)
    init_database()
    if settings.is_demo_mode:
        AuthRepository.ensure_demo_credentials()
    elif settings.production_bootstrap_configured:
        AuthRepository.ensure_production_admin()
    RetentionRepository.cleanup()
    logger.info("application_started", version=application.version)
    try:
        yield
    finally:
        shutdown_tracing()


app = FastAPI(
    title="Nordly Support Agent",
    description="AI-powered Level 1 support operations agent",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    """Correlate requests and record bounded, non-sensitive HTTP metrics."""
    supplied_id = request.headers.get("X-Correlation-ID", "")
    accepted_id = supplied_id if _CORRELATION_ID.fullmatch(supplied_id) else None
    started = monotonic()
    with correlation_context(accepted_id) as correlation_id:
        try:
            response = await call_next(request)
        except Exception:
            route = getattr(request.scope.get("route"), "path", "unmatched")
            metrics.http_errors.labels(method=request.method, route=route, status="500").inc()
            logger.exception("http_request_failed", method=request.method, route=route)
            raise
        route = getattr(request.scope.get("route"), "path", "unmatched")
        status = str(response.status_code)
        duration = monotonic() - started
        metrics.http_requests.labels(method=request.method, route=route, status=status).inc()
        metrics.http_duration.labels(method=request.method, route=route).observe(duration)
        if response.status_code >= 400:
            metrics.http_errors.labels(method=request.method, route=route, status=status).inc()
        response.headers["X-Correlation-ID"] = correlation_id
        logger.info(
            "http_request_completed",
            method=request.method,
            route=route,
            status=response.status_code,
            duration_ms=round(duration * 1000, 2),
        )
        return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
if settings.https_redirect:
    app.add_middleware(HTTPSRedirectMiddleware)

# Include API routes
app.include_router(router)
app.mount("/metrics", make_asgi_app())
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.middleware("http")
async def protect_metrics(request: Request, call_next):
    """Require the dedicated scrape token whenever configured or in production."""
    if request.url.path.startswith("/metrics") and settings.metrics_token:
        supplied = request.headers.get("X-Metrics-Token")
        authorization = request.headers.get("Authorization", "")
        if not supplied and authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        import hmac

        if not supplied or not hmac.compare_digest(supplied, settings.metrics_token):
            return JSONResponse({"detail": "Metrics authentication required"}, status_code=401)
    return await call_next(request)


@app.get("/dashboard", include_in_schema=False)
async def dashboard() -> FileResponse:
    """Serve the responsive operations dashboard."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")
