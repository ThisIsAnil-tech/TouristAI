"""Detection router — audio distress detection."""
from __future__ import annotations

import io
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.audio import AudioClass, AudioDetection, AudioDetectionMode

logger = logging.getLogger(__name__)
router = APIRouter()


class AudioDetectionRequest(BaseModel):
    """Mode A: mobile client sends classification result."""
    predicted_class: AudioClass
    confidence: float = Field(..., ge=0.0, le=1.0)
    class_probabilities: Optional[dict] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    model_version: Optional[str] = None
    inference_time_ms: Optional[float] = None
    risk_score: Optional[float] = None

    model_config = {"json_schema_extra": {"example": {
        "predicted_class": "SCREAM",
        "confidence": 0.87,
        "class_probabilities": {"SCREAM": 0.87, "GLASS_BREAK": 0.08, "NORMAL": 0.05},
        "inference_time_ms": 45.2
    }}}


class AudioDetectionResponse(BaseModel):
    detection_id: uuid.UUID
    is_distress: bool
    confidence: float
    predicted_class: str
    adaptive_threshold_used: Optional[float]
    risk_score_at_detection: Optional[float]
    mode: str


@router.post(
    "/audio",
    response_model=AudioDetectionResponse,
    summary="Submit audio detection result from mobile client (Mode A)",
)
async def submit_audio_detection(
    body: AudioDetectionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AudioDetectionResponse:
    from app.services.risk.adaptive_threshold import threshold_controller

    uid = uuid.UUID(user_id)
    risk_score = body.risk_score or 5.0

    is_distress, threshold = threshold_controller.is_distress(body.confidence, risk_score)

    detection = AudioDetection(
        user_id=uid,
        predicted_class=body.predicted_class,
        confidence=body.confidence,
        class_probabilities=json.dumps(body.class_probabilities) if body.class_probabilities else None,
        adaptive_threshold_used=threshold,
        risk_score_at_detection=body.risk_score,
        is_distress=is_distress,
        detection_mode=AudioDetectionMode.EDGE,
        latitude=body.latitude,
        longitude=body.longitude,
        inference_time_ms=body.inference_time_ms,
        model_version=body.model_version,
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    return AudioDetectionResponse(
        detection_id=detection.id,
        is_distress=is_distress,
        confidence=body.confidence,
        predicted_class=body.predicted_class.value,
        adaptive_threshold_used=threshold,
        risk_score_at_detection=body.risk_score,
        mode="EDGE",
    )


@router.post(
    "/audio/infer",
    response_model=AudioDetectionResponse,
    summary="Upload audio file for backend inference (Mode B / research)",
)
async def infer_audio(
    file: UploadFile = File(..., description="Audio file (WAV/MP3/FLAC)"),
    risk_score: float = 5.0,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> AudioDetectionResponse:
    """
    Backend performs actual audio inference using the trained model.
    Requires models/audio/mobilenetv2_distress.pt to be present.
    """
    from app.services.audio.inference import AudioInferenceService
    from app.services.risk.adaptive_threshold import threshold_controller

    uid = uuid.UUID(user_id)
    audio_bytes = await file.read()

    service = AudioInferenceService()
    start = time.perf_counter()
    result = await service.infer(audio_bytes)
    elapsed_ms = (time.perf_counter() - start) * 1000

    is_distress, threshold = threshold_controller.is_distress(result.confidence, risk_score)

    detection = AudioDetection(
        user_id=uid,
        predicted_class=result.predicted_class,
        confidence=result.confidence,
        class_probabilities=json.dumps(result.class_probabilities),
        adaptive_threshold_used=threshold,
        risk_score_at_detection=risk_score,
        is_distress=is_distress,
        detection_mode=AudioDetectionMode.BACKEND,
        inference_time_ms=elapsed_ms,
        model_version=result.model_version,
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    return AudioDetectionResponse(
        detection_id=detection.id,
        is_distress=is_distress,
        confidence=result.confidence,
        predicted_class=result.predicted_class.value,
        adaptive_threshold_used=threshold,
        risk_score_at_detection=risk_score,
        mode="BACKEND",
    )
