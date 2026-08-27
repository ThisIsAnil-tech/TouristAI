"""
tests/integration/test_gps_api.py — Integration tests for GPS endpoints.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient


class TestGpsSubmit:
    @pytest.mark.asyncio
    async def test_submit_location_authenticated(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/gps/location",
            json={
                "latitude": 10.5276,
                "longitude": 76.2144,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "reading_id" in data
        assert "is_anomalous" in data
        assert "should_trigger_sos" in data

    @pytest.mark.asyncio
    async def test_submit_location_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/gps/location",
            json={"latitude": 10.0, "longitude": 76.0,
                  "recorded_at": datetime.now(timezone.utc).isoformat()},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_invalid_latitude(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/gps/location",
            json={"latitude": 999.0, "longitude": 76.0,
                  "recorded_at": datetime.now(timezone.utc).isoformat()},
            headers=auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_first_reading_not_anomalous(self, client: AsyncClient, auth_headers):
        """First GPS reading for a user should not trigger SOS."""
        response = await client.post(
            "/api/v1/gps/location",
            json={"latitude": 10.0, "longitude": 76.0,
                  "recorded_at": datetime.now(timezone.utc).isoformat()},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["should_trigger_sos"] is False
