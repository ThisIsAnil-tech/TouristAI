"""
tests/integration/test_sos_api.py — Integration tests for SOS endpoints.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestSosManual:
    @pytest.mark.asyncio
    async def test_manual_sos_triggers(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sos/manual",
            json={"latitude": 10.5, "longitude": 76.2},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sos_triggered"] is True
        assert data["sos_event_id"] is not None

    @pytest.mark.asyncio
    async def test_manual_sos_requires_auth(self, client: AsyncClient):
        response = await client.post("/api/v1/sos/manual", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_evaluate_no_evidence_no_sos(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sos/evaluate",
            json={"risk_score": 2.0},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sos_triggered"] is False

    @pytest.mark.asyncio
    async def test_evaluate_high_confidence_audio_triggers(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sos/evaluate",
            json={
                "audio_confidence": 0.95,
                "audio_is_distress": True,
                "risk_score": 8.0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sos_triggered"] is True

    @pytest.mark.asyncio
    async def test_evaluate_gps_anomalies_trigger(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/sos/evaluate",
            json={
                "gps_is_anomalous": True,
                "gps_consecutive_anomalies": 3,
                "risk_score": 5.0,
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sos_triggered"] is True
