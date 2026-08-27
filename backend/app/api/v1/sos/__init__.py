"""app/api/v1/sos/__init__.py — SOS & emergency endpoints."""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_responder
from app.database import get_db
from app.models.sos import SosEvent, SosStatus
from app.services.emergency.decision_engine import (
    DecisionInput, EmergencyDecisionEngine
)

logger = logging.getLogger(__name__)
router = APIRouter()

_engine = EmergencyDecisionEngine()


class ManualSosRequest(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[uuid.UUID] = None
    message: Optional[str] = None


class SosEvaluateRequest(BaseModel):
    audio_confidence: Optional[float] = None
    audio_is_distress: Optional[bool] = None
    audio_detection_id: Optional[uuid.UUID] = None
    gps_is_anomalous: Optional[bool] = None
    gps_consecutive_anomalies: Optional[int] = None
    gps_reading_id: Optional[uuid.UUID] = None
    risk_score: Optional[float] = None
    risk_score_id: Optional[uuid.UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    zone_id: Optional[uuid.UUID] = None


class SosResponse(BaseModel):
    sos_triggered: bool
    sos_event_id: Optional[uuid.UUID]
    trigger: Optional[str]
    reason: str
    confidence: Optional[float]
    adaptive_threshold: Optional[float]
    details: str


@router.post("/manual", response_model=SosResponse, summary="Trigger manual SOS")
async def manual_sos(
    body: ManualSosRequest,
    x_idempotency_key: Optional[str] = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SosResponse:
    inp = DecisionInput(
        user_id=uuid.UUID(user_id),
        latitude=body.latitude,
        longitude=body.longitude,
        zone_id=body.zone_id,
        is_manual=True,
        idempotency_key=x_idempotency_key,
    )
    result = await _engine.evaluate(inp, db)
    return SosResponse(
        sos_triggered=result.should_trigger_sos,
        sos_event_id=result.sos_event_id,
        trigger=result.trigger,
        reason=result.reason.value if result.reason else "",
        confidence=result.confidence,
        adaptive_threshold=result.adaptive_threshold_used,
        details=result.details,
    )


@router.post("/evaluate", response_model=SosResponse, summary="Evaluate evidence for SOS")
async def evaluate_sos(
    body: SosEvaluateRequest,
    x_idempotency_key: Optional[str] = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> SosResponse:
    inp = DecisionInput(
        user_id=uuid.UUID(user_id),
        latitude=body.latitude,
        longitude=body.longitude,
        zone_id=body.zone_id,
        audio_detection_id=body.audio_detection_id,
        audio_confidence=body.audio_confidence,
        audio_is_distress=body.audio_is_distress,
        gps_reading_id=body.gps_reading_id,
        gps_is_anomalous=body.gps_is_anomalous,
        gps_consecutive_anomalies=body.gps_consecutive_anomalies,
        risk_score_id=body.risk_score_id,
        risk_score=body.risk_score,
        idempotency_key=x_idempotency_key,
    )
    result = await _engine.evaluate(inp, db)
    return SosResponse(
        sos_triggered=result.should_trigger_sos,
        sos_event_id=result.sos_event_id,
        trigger=result.trigger,
        reason=result.reason.value if result.reason else "",
        confidence=result.confidence,
        adaptive_threshold=result.adaptive_threshold_used,
        details=result.details,
    )


@router.post("/{sos_id}/resolve", summary="Resolve an SOS event")
async def resolve_sos(
    sos_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    sos = await db.get(SosEvent, sos_id)
    if not sos:
        raise HTTPException(status_code=404, detail="SOS event not found")
    sos.status = SosStatus.RESOLVED
    sos.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "resolved", "sos_id": str(sos_id)}
