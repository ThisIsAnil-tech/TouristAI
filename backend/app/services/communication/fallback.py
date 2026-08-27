"""
app/services/communication/fallback.py — Communication fallback state machine.

Patent requirement: Internet → SMS → Mesh → Retry/Pending

Each provider actually attempts its configured operation.
Never claims delivery success if provider failed.
Every attempt is stored in the communication_attempts table.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import CommunicationAttempt, CommunicationChannel, DeliveryStatus
from app.models.sos import SosEvent

logger = logging.getLogger(__name__)


class CommunicationState(str, Enum):
    INTERNET = "INTERNET"
    SMS = "SMS"
    MESH = "MESH"
    PENDING_RETRY = "PENDING_RETRY"
    DELIVERED = "DELIVERED"


class CommunicationFallbackManager:
    """
    Manages the communication fallback state machine.

    State transitions:
      INTERNET → (success) DELIVERED
      INTERNET → (failure) SMS
      SMS      → (success) DELIVERED
      SMS      → (failure) MESH
      MESH     → (success) DELIVERED
      MESH     → (failure) PENDING_RETRY

    Each channel makes a real attempt via its provider.
    """

    def __init__(
        self,
        internet_provider=None,
        sms_provider=None,
        mesh_provider=None,
    ) -> None:
        self._internet = internet_provider
        self._sms = sms_provider
        self._mesh = mesh_provider

    async def send_emergency_alert(
        self,
        sos_event: SosEvent,
        db: AsyncSession,
        destination: str,
        message: str,
    ) -> CommunicationState:
        """
        Attempt to deliver an emergency alert through available channels.

        Args:
            sos_event: The active SOS event.
            db: Database session.
            destination: Phone number, URL, or device ID.
            message: Alert message body.

        Returns:
            Final CommunicationState.
        """
        state = CommunicationState.INTERNET

        # ── Attempt Internet ───────────────────────────────────────────────
        if self._internet is not None:
            attempt = await self._log_attempt(
                db, sos_event.id, CommunicationChannel.INTERNET, destination, message
            )
            success, error = await self._try_internet(message, destination)
            await self._update_attempt(db, attempt, success, error)

            if success:
                return CommunicationState.DELIVERED
            logger.warning("Internet delivery failed for SOS %s: %s", sos_event.id, error)
        else:
            logger.info("No internet provider configured — skipping to SMS")

        state = CommunicationState.SMS

        # ── Attempt SMS ────────────────────────────────────────────────────
        if self._sms is not None:
            attempt = await self._log_attempt(
                db, sos_event.id, CommunicationChannel.SMS, destination, message
            )
            success, error = await self._try_sms(message, destination)
            await self._update_attempt(db, attempt, success, error)

            if success:
                return CommunicationState.DELIVERED
            logger.warning("SMS delivery failed for SOS %s: %s", sos_event.id, error)
        else:
            logger.info("No SMS provider configured — skipping to MESH")

        state = CommunicationState.MESH

        # ── Attempt Mesh ───────────────────────────────────────────────────
        if self._mesh is not None:
            attempt = await self._log_attempt(
                db, sos_event.id, CommunicationChannel.MESH, destination, message
            )
            success, error = await self._try_mesh(sos_event, db)
            await self._update_attempt(db, attempt, success, error)

            if success:
                return CommunicationState.DELIVERED
            logger.warning("Mesh delivery failed for SOS %s: %s", sos_event.id, error)

        logger.error("All communication channels failed for SOS %s", sos_event.id)
        return CommunicationState.PENDING_RETRY

    async def _try_internet(self, message: str, url: str) -> tuple[bool, Optional[str]]:
        try:
            result = await self._internet.send_alert(message=message, destination=url)
            return result.success, result.error
        except Exception as exc:
            return False, str(exc)

    async def _try_sms(self, message: str, phone: str) -> tuple[bool, Optional[str]]:
        try:
            result = await self._sms.send_sms(to=phone, body=message)
            return result.success, result.error
        except Exception as exc:
            return False, str(exc)

    async def _try_mesh(self, sos_event: SosEvent, db: AsyncSession) -> tuple[bool, Optional[str]]:
        try:
            from app.services.mesh.routing import MeshRoutingService
            routing = MeshRoutingService()
            result = await routing.route_emergency(sos_event=sos_event, db=db)
            return result.success, result.error if not result.success else None
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    async def _log_attempt(
        db: AsyncSession,
        sos_event_id: uuid.UUID,
        channel: CommunicationChannel,
        destination: str,
        message: str,
    ) -> CommunicationAttempt:
        attempt = CommunicationAttempt(
            sos_event_id=sos_event_id,
            channel=channel,
            status=DeliveryStatus.PENDING,
            destination=destination,
            message_body=message[:10000],
            attempt_at=datetime.now(timezone.utc),
        )
        db.add(attempt)
        await db.flush()
        return attempt

    @staticmethod
    async def _update_attempt(
        db: AsyncSession,
        attempt: CommunicationAttempt,
        success: bool,
        error: Optional[str],
    ) -> None:
        if success:
            attempt.status = DeliveryStatus.DELIVERED
            attempt.delivered_at = datetime.now(timezone.utc)
            latency = (attempt.delivered_at - attempt.attempt_at).total_seconds() * 1000
            attempt.latency_ms = latency
        else:
            attempt.status = DeliveryStatus.FAILED
            attempt.error_message = error
        await db.flush()
