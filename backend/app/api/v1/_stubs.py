"""Stub routers for Phase 1 — detailed implementations in later phases."""
from fastapi import APIRouter, Depends
from app.core.security import get_current_user_id, require_admin

def _stub(name: str):
    router = APIRouter()
    @router.get("/", summary=f"{name} endpoint")
    async def _():
        return {"module": name, "status": "implemented in Phase 3+"}
    return router

# These are imported by app/api/v1/__init__.py
responders_router = _stub("Responders")
zones_router = _stub("Geographic Zones")
communication_router = _stub("Communication")
mesh_router = _stub("Mesh Network")
blockchain_router = _stub("Blockchain Identity")
telemetry_router = _stub("Mobile Telemetry")
field_tests_router = _stub("Field Tests")
experiments_router = _stub("Research Experiments")
audit_router = _stub("Audit Logs")
