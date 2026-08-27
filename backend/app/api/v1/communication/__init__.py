"""app/api/v1/communication/__init__.py — Communication attempts API."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.communication import CommunicationAttempt, CommunicationChannel, DeliveryStatus
from app.models.sos import SosEvent
from app.models.user import EmergencyContact

logger = logging.getLogger(__name__)
router = APIRouter()


class CommAttemptResponse(BaseModel):
    id: uuid.UUID
    sos_event_id: uuid.UUID
    channel: str
    status: str
    destination: str
    attempt_at: datetime
    delivered_at: Optional[datetime]
    latency_ms: Optional[float]
    retry_count: int
    error_message: Optional[str]


@router.get("/sos/{sos_event_id}", response_model=List[CommAttemptResponse],
            summary="Get communication attempts for an SOS event")
async def get_comm_attempts(
    sos_event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
) -> List[CommAttemptResponse]:
    result = await db.scalars(
        select(CommunicationAttempt)
        .where(CommunicationAttempt.sos_event_id == sos_event_id)
        .order_by(CommunicationAttempt.attempt_at.asc())
    )
    attempts = result.all()
    return [_to_response(a) for a in attempts]


@router.post("/sos/{sos_event_id}/send", summary="Send emergency alert for an SOS event")
async def send_alert(
    sos_event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """
    Triggers the full communication fallback pipeline:
    Internet → SMS → Mesh for all emergency contacts.
    """
    sos = await db.get(SosEvent, sos_event_id)
    if not sos:
        raise HTTPException(status_code=404, detail="SOS event not found")

    # Get emergency contacts
    contacts = await db.scalars(
        select(EmergencyContact).where(
            EmergencyContact.user_id == sos.user_id,
            EmergencyContact.notify_on_sos == True,
        )
    )
    contact_list = contacts.all()

    if not contact_list:
        return {"message": "No emergency contacts to notify", "notified": 0}

    from app.services.communication.fallback import CommunicationFallbackManager
    from app.services.communication.sms_provider import get_sms_provider
    from app.services.communication.internet_provider import InternetAlertProvider
    from app.services.mesh.routing import MeshRoutingService

    sms = get_sms_provider()
    internet = InternetAlertProvider()
    mesh = MeshRoutingService()

    manager = CommunicationFallbackManager(
        internet_provider=internet,
        sms_provider=sms,
        mesh_provider=mesh,
    )

    message = (
        f"EMERGENCY ALERT: {sos.trigger} detected. "
        f"User may need immediate assistance. "
        f"Location: {sos.latitude}, {sos.longitude}. "
        f"SOS ID: {sos.id}"
    )

    results = []
    for contact in contact_list:
        destination = contact.phone_number
        final_state = await manager.send_emergency_alert(
            sos_event=sos, db=db, destination=destination, message=message
        )
        results.append({"contact": contact.name, "state": final_state.value})

    await db.commit()
    return {"notified": len(contact_list), "results": results}


@router.post("/sos/{sos_event_id}/retry", summary="Retry failed communication attempts")
async def retry_failed(
    sos_event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.scalars(
        select(CommunicationAttempt).where(
            CommunicationAttempt.sos_event_id == sos_event_id,
            CommunicationAttempt.status == DeliveryStatus.FAILED,
            CommunicationAttempt.retry_count < CommunicationAttempt.max_retries,
        )
    )
    failed = result.all()

    for attempt in failed:
        attempt.retry_count += 1
        attempt.status = DeliveryStatus.RETRYING
        attempt.attempt_at = datetime.now(timezone.utc)

    await db.commit()
    return {"retrying": len(failed)}


def _to_response(a: CommunicationAttempt) -> CommAttemptResponse:
    return CommAttemptResponse(
        id=a.id,
        sos_event_id=a.sos_event_id,
        channel=a.channel,
        status=a.status,
        destination=a.destination,
        attempt_at=a.attempt_at,
        delivered_at=a.delivered_at,
        latency_ms=a.latency_ms,
        retry_count=a.retry_count,
        error_message=a.error_message,
    )
