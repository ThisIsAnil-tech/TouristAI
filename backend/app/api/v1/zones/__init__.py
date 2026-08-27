from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id, require_admin
from app.database import get_db
from app.models.zone import GeographicZone
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()

class ZoneRequest(BaseModel):
    name: str
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    is_high_risk: bool = False

@router.get("/", summary="List geographic zones")
async def list_zones(db: AsyncSession = Depends(get_db), _=Depends(get_current_user_id)):
    result = await db.scalars(select(GeographicZone).where(GeographicZone.is_active == True))
    return [{"id": str(z.id), "name": z.name, "risk_level": z.risk_level, "is_high_risk": z.is_high_risk} for z in result.all()]

@router.post("/", summary="Create zone (admin)")
async def create_zone(body: ZoneRequest, db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    zone = GeographicZone(**body.model_dump())
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return {"id": str(zone.id), "name": zone.name}
