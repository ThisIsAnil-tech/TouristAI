from fastapi import APIRouter, Depends, HTTPException
from app.core.security import require_admin
from app.database import get_db
from app.models.experiment import ExperimentRun, ExperimentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

router = APIRouter()

REGISTERED_EXPERIMENTS = {
    "audio_experiment", "gps_experiment", "risk_experiment",
    "emergency_decision_experiment", "internet_alert_experiment",
    "sms_alert_experiment", "mesh_experiment", "blockchain_experiment",
    "mobile_performance_experiment", "edge_ai_experiment", "battery_experiment",
    "emergency_response_experiment", "field_test_experiment",
    "scalability_experiment", "overall_system_experiment",
}

@router.post("/{experiment_name}/run", summary="Run a research experiment (admin only)")
async def run_experiment(
    experiment_name: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
):
    if experiment_name not in REGISTERED_EXPERIMENTS:
        raise HTTPException(status_code=400, detail=f"Unknown experiment: {experiment_name}")

    run = ExperimentRun(experiment_name=experiment_name, status=ExperimentStatus.PENDING)
    db.add(run)
    await db.commit()
    await db.refresh(run)

    return {
        "experiment_id": str(run.id),
        "experiment_name": experiment_name,
        "status": run.status,
        "message": f"Experiment queued. Run: python -m tests.experiments.{experiment_name}"
    }

@router.get("/", summary="List experiment runs")
async def list_experiments(db: AsyncSession = Depends(get_db), _=Depends(require_admin)):
    result = await db.scalars(select(ExperimentRun).order_by(ExperimentRun.created_at.desc()).limit(50))
    return [{"id": str(r.id), "name": r.experiment_name, "status": r.status} for r in result.all()]
