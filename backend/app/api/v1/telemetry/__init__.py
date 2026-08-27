from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user_id
from app.database import get_db
from app.models.telemetry import MobileTelemetry
from pydantic import BaseModel
from typing import Optional
import uuid
router = APIRouter()

class TelemetryRequest(BaseModel):
    fps: Optional[float] = None
    cpu_pct: Optional[float] = None
    ram_mb: Optional[float] = None
    battery_pct: Optional[float] = None
    battery_drain_per_hour: Optional[float] = None
    inference_time_ms: Optional[float] = None
    device_model: Optional[str] = None
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    session_id: Optional[str] = None

@router.post("/mobile", summary="Submit mobile telemetry")
async def submit_telemetry(body: TelemetryRequest, user_id: str = Depends(get_current_user_id), db: AsyncSession = Depends(get_db)):
    t = MobileTelemetry(user_id=uuid.UUID(user_id), **body.model_dump())
    db.add(t)
    await db.commit()
    return {"message": "Telemetry recorded"}
