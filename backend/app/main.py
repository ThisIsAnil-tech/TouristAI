"""
app/main.py — FastAPI application factory.

Configures:
  - CORS
  - Rate limiting
  - Request ID middleware
  - Structured logging
  - Exception handlers
  - API routers
  - Health endpoint
  - Background scheduler
  - Startup/shutdown lifecycle
"""
from __future__ import annotations

import time
import uuid
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.core.logging import configure_logging, request_id_var
from app.database import check_database_connection

# ---- Configure logging immediately ----
configure_logging(level=settings.LOG_LEVEL, fmt=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# ---- Rate limiter ----
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Tourist Safety Backend v%s [%s]", settings.VERSION, settings.APP_ENV)

    # Verify DB connectivity
    db_ok = await check_database_connection()
    if not db_ok:
        logger.error("Database connection failed at startup — check DATABASE_URL")
    else:
        logger.info("Database connection: OK")
        try:
            import app.models  # noqa: F401
            from app.database import create_all_tables
            await create_all_tables()
            logger.info("Database tables verified / created.")
        except Exception as exc:
            logger.warning("Could not auto-create tables: %s", exc)

    # Start background scheduler
    try:
        from app.workers.scheduler import start_scheduler, stop_scheduler
        await start_scheduler()
        logger.info("Background scheduler started")
    except Exception as exc:
        logger.warning("Background scheduler failed to start: %s", exc)

    yield

    # Shutdown
    try:
        from app.workers.scheduler import stop_scheduler
        await stop_scheduler()
    except Exception:
        pass

    logger.info("Tourist Safety Backend shutdown complete")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=(
            "Edge-Based Tourist Safety System — Backend & Research Platform.\n\n"
            "This backend serves as both the production API for the mobile application "
            "and the experimental research infrastructure for the associated academic paper."
        ),
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.is_production else ["*"],
        allow_origin_regex=None if settings.is_production else r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Rate limiting ----
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ---- Request ID middleware ----
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(req_id)
        start = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
        logger.info(
            "HTTP %s %s → %d (%.1f ms)",
            request.method, request.url.path, response.status_code, elapsed_ms,
            extra={"request_id": req_id, "method": request.method,
                   "path": request.url.path, "status": response.status_code},
        )
        return response

    # ---- Global exception handlers ----
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ---- Root / Welcome endpoint ----
    @app.get(
        "/",
        tags=["Health"],
        summary="Root welcome endpoint",
    )
    async def root():
        return {
            "name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "frontend": "http://localhost:5173",
        }

    # ---- Health endpoint ----
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health check",
        response_description="Returns service health status",
    )
    async def health_check():
        db_healthy = await check_database_connection()
        return {
            "status": "healthy" if db_healthy else "degraded",
            "version": settings.VERSION,
            "environment": settings.APP_ENV,
            "database": "connected" if db_healthy else "unavailable",
        }

    # ---- Register API routers ----
    _register_routers(app)

    return app


def _register_routers(app: FastAPI) -> None:
    """Register all versioned API routers."""
    from app.api.v1 import router as v1_router
    app.include_router(v1_router, prefix=settings.API_V1_STR)


# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------
app = create_app()
