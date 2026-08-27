"""
tests/integration/test_auth_api.py — Integration tests for auth endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestAuthRegister:
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "new@test.com",
            "password": "SecurePass123!",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "new@test.com"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        payload = {"email": "dup@test.com", "password": "pass123!", "full_name": "Dup"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@test.com", "password": "123", "full_name": "Weak"
        })
        assert response.status_code == 422


class TestAuthLogin:
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", data={
            "username": "tourist@test.com",
            "password": "testpass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        response = await client.post("/api/v1/auth/login", data={
            "username": "tourist@test.com",
            "password": "wrongpass",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", data={
            "username": "nobody@test.com", "password": "anypass"
        })
        assert response.status_code == 401


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
