"""app/api/v1/risk/__init__.py — Risk engine endpoints."""
from __future__ import annotations

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.database import get_db
from app.models.risk import RiskScore
from app.models.zone import GeographicZone
from app.services.risk.risk_calculator import RiskCalculator

logger = logging.getLogger(__name__)
router = APIRouter()
_calculator = RiskCalculator()


class RiskScoreResponse(BaseModel):
    id: uuid.UUID
    zone_id: uuid.UUID
    final_score: float
    risk_level: str
    adaptive_threshold: float
    weather_score: float
    news_score: float
    historical_score: float
    details: Optional[str] = None


@router.get("/zone/{zone_id}", response_model=RiskScoreResponse,
            summary="Get latest risk score for a zone")
async def get_zone_risk(
    zone_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    score = await db.scalar(
        select(RiskScore)
        .where(RiskScore.zone_id == zone_id)
        .order_by(RiskScore.created_at.desc())
        .limit(1)
    )
    if not score:
        raise HTTPException(status_code=404, detail="No risk score for this zone")
    return _to_response(score)


@router.post("/calculate/{zone_id}", response_model=RiskScoreResponse,
             summary="Trigger risk calculation for a zone")
async def calculate_zone_risk(
    zone_id: uuid.UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    zone = await db.get(GeographicZone, zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    result = await _calculator.calculate_for_zone(db, zone)
    score = await _calculator.persist(db, result)
    await db.commit()
    await db.refresh(score)
    return _to_response(score)


def _to_response(score: RiskScore) -> RiskScoreResponse:
    return RiskScoreResponse(
        id=score.id,
        zone_id=score.zone_id,
        final_score=score.final_score,
        risk_level=score.risk_level,
        adaptive_threshold=score.adaptive_threshold,
        weather_score=score.weather_score,
        news_score=score.news_score,
        historical_score=score.historical_score,
    )
