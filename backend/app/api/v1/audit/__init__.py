from fastapi import APIRouter, Depends
from app.core.security import require_admin
from app.database import get_db
from app.models.audit import AuditLog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()

@router.get("/", summary="List audit logs (admin only)")
async def list_audit_logs(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    result = await db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return [{"id": str(a.id), "action": a.action, "outcome": a.outcome, "created_at": a.created_at.isoformat()} for a in result.all()]
