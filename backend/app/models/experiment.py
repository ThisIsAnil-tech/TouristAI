"""app/models/experiment.py — Research experiment run records."""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class ExperimentStatus(str, PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NOT_RUN = "NOT_RUN"
    SIMULATED = "SIMULATED"


class ExperimentRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Records one execution of a research experiment.
    Supports full reproducibility requirements.
    """
    __tablename__ = "experiment_runs"
    __table_args__ = (
        Index("ix_experiment_runs_name", "experiment_name"),
        Index("ix_experiment_runs_status", "status"),
    )

    experiment_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(
        SAEnum(ExperimentStatus, name="experimentstatus"),
        default=ExperimentStatus.PENDING,
        nullable=False,
    )

    # Dataset
    dataset_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dataset_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    dataset_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Reproducibility
    random_seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    python_version: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    git_commit: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    environment_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    package_versions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON

    # Config
    config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # YAML/JSON

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Outputs
    result_directory: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    metrics_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    metrics: Mapped[list["ExperimentMetric"]] = relationship(
        "ExperimentMetric", back_populates="experiment_run", cascade="all, delete-orphan"
    )


class ExperimentMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "experiment_metrics"
    __table_args__ = (
        Index("ix_exp_metrics_run_id", "experiment_run_id"),
        Index("ix_exp_metrics_name", "metric_name"),
    )

    experiment_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("experiment_runs.id", ondelete="CASCADE"), nullable=False
    )

    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    metric_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    baseline_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    experiment_run: Mapped["ExperimentRun"] = relationship("ExperimentRun", back_populates="metrics")
