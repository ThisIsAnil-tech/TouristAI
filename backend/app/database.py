"""
app/database.py — SQLAlchemy async engine, session factory, Base.

Uses asyncpg driver for fully asynchronous database operations.
Engine is created lazily on first use to allow unit tests with SQLite
to run without requiring asyncpg or a PostgreSQL connection.

Provides:
  - get_engine() / get_session_factory() — lazy factory functions
  - get_db() — FastAPI dependency that yields an async session
  - get_db_context() — async context manager for workers/scripts
  - Base — declarative base for all ORM models
  - check_database_connection() — health check
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Common declarative base for all SQLAlchemy ORM models."""
    pass


# ---------------------------------------------------------------------------
# Lazy engine / session factory
# ---------------------------------------------------------------------------
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Return (and create if needed) the async engine singleton."""
    global _engine
    if _engine is None:
        kwargs: dict = {
            "echo": settings.DEBUG,
            "pool_pre_ping": True,
        }
        if "sqlite" in settings.DATABASE_URL:
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_size"] = settings.DB_POOL_SIZE
            kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
            kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
        _engine = create_async_engine(settings.DATABASE_URL, **kwargs)
        logger.debug("Async engine created: %s", settings.DATABASE_URL)
    return _engine


def get_session_factory() -> async_sessionmaker:
    """Return (and create if needed) the session factory singleton."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an async database session.

    The session is committed on success, rolled back on exception,
    and always closed.
    """
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Context-manager version for use outside FastAPI (workers, scripts)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions outside request scope."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Startup / Shutdown helpers
# ---------------------------------------------------------------------------
async def create_all_tables() -> None:
    """Create all tables (used in tests). Production uses Alembic."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("All database tables created.")


async def drop_all_tables() -> None:
    """Drop all tables (used in tests)."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("All database tables dropped.")


async def check_database_connection() -> bool:
    """Health-check: return True if DB is reachable."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        return False


async def dispose_engine() -> None:
    """Dispose engine connection pool (call on shutdown)."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
