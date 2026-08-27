"""
app/services/communication/internet_provider.py — HTTP/webhook alert delivery.

Sends emergency alerts via HTTP POST to a configured endpoint (e.g.,
emergency services API, push notification gateway, monitoring webhook).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AlertResult:
    success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    error: Optional[str]


class InternetAlertProviderNotConfiguredError(Exception):
    pass


class InternetAlertProvider:
    """
    Sends emergency alerts via HTTP POST.

    Target URL is configured via ALERT_PROVIDER_URL.
    Retries up to 3 times with exponential backoff.
    """

    def __init__(self) -> None:
        self._url = settings.ALERT_PROVIDER_URL
        self._api_key = settings.ALERT_PROVIDER_API_KEY
        self._mock = settings.ALERT_MOCK_MODE
        self._timeout = settings.ALERT_REQUEST_TIMEOUT

    async def send_alert(self, message: str, destination: str) -> AlertResult:
        if self._mock:
            logger.warning("Internet alert MOCK MODE — not sending real HTTP alert")
            return AlertResult(True, 200, '{"status":"mock"}', None)

        if not self._url:
            raise InternetAlertProviderNotConfiguredError(
                "ALERT_PROVIDER_URL not configured. "
                "Set ALERT_MOCK_MODE=true for development."
            )

        return await self._post(message=message, destination=destination)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    async def _post(self, message: str, destination: str) -> AlertResult:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "message": message,
            "destination": destination,
            "priority": "EMERGENCY",
            "source": "tourist_safety_backend",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(self._url, json=payload, headers=headers)
                success = response.is_success
                if success:
                    logger.info("Internet alert delivered: status=%d", response.status_code)
                else:
                    logger.warning("Internet alert failed: status=%d body=%s",
                                   response.status_code, response.text[:200])
                return AlertResult(
                    success=success,
                    status_code=response.status_code,
                    response_body=response.text[:500],
                    error=None if success else f"HTTP {response.status_code}",
                )
        except Exception as exc:
            logger.error("Internet alert exception: %s", exc)
            return AlertResult(False, None, None, str(exc))
