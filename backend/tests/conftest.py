"""
tests/conftest.py — Pytest fixtures for all tests.

Provides:
  - async_db: in-memory SQLite async session (no PostgreSQL needed for unit tests)
  - app_client: FastAPI TestClient with overridden DB dependency
  - test_user / test_admin: pre-created user fixtures
  - auth_headers: JWT headers for test requests
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db, get_engine, get_session_factory, dispose_engine
from app.main import app
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token


# ---------------------------------------------------------------------------
# Event loop (single shared event loop for all async tests)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# In-memory SQLite async engine (no PostgreSQL needed)
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import StaticPool
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def async_db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client with DB override
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(test_engine) -> AsyncGenerator[AsyncClient, None]:
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User fixtures
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def test_user(async_db: AsyncSession) -> User:
    from sqlalchemy import select
    res = await async_db.execute(select(User).where(User.email == "tourist@test.com"))
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    user = User(
        id=uuid.uuid4(),
        email="tourist@test.com",
        full_name="Test Tourist",
        hashed_password=hash_password("testpass123"),
        role=UserRole.TOURIST,
        is_active=True,
        is_verified=True,
    )
    async_db.add(user)
    await async_db.commit()
    await async_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_admin(async_db: AsyncSession) -> User:
    from sqlalchemy import select
    res = await async_db.execute(select(User).where(User.email == "admin@test.com"))
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    admin = User(
        id=uuid.uuid4(),
        email="admin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("adminpass123"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    async_db.add(admin)
    await async_db.commit()
    await async_db.refresh(admin)
    return admin


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    token = create_access_token(subject=str(test_user.id), role=test_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(test_admin: User) -> dict:
    token = create_access_token(subject=str(test_admin.id), role=test_admin.role)
    return {"Authorization": f"Bearer {token}"}
