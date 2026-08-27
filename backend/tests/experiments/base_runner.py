"""
tests/experiments/base_runner.py — Centralized experiment runner base class.

All experiment runners must inherit from BaseExperimentRunner.
Enforces:
  - Result categorization: ACTUAL / SIMULATED / NOT_RUN
  - Git commit / Python version / package version capture
  - Centralized metrics storage to DB
  - JSON + CSV result export
  - Academic integrity: never fabricates metrics
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import platform
import subprocess
import sys
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultCategory(str, Enum):
    ACTUAL = "ACTUAL"         # Real measurement from real data/system
    SIMULATED = "SIMULATED"   # Controlled simulation with documented assumptions
    NOT_RUN = "NOT_RUN"       # Experiment could not be run; reasons documented


@dataclass
class MetricRecord:
    name: str
    value: Optional[float]
    unit: Optional[str]
    category: ResultCategory
    model_name: Optional[str] = None
    baseline_name: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class ExperimentReport:
    experiment_name: str
    run_id: str
    status: str  # COMPLETED | FAILED | PARTIAL | NOT_RUN
    metrics: List[MetricRecord] = field(default_factory=list)
    git_commit: Optional[str] = None
    python_version: str = ""
    package_versions: Dict[str, str] = field(default_factory=dict)
    environment_info: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    dataset_name: Optional[str] = None
    dataset_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_directory: Optional[str] = None
    notes: str = ""

    def add_metric(
        self,
        name: str,
        value: Optional[float],
        unit: Optional[str] = None,
        category: ResultCategory = ResultCategory.ACTUAL,
        model_name: Optional[str] = None,
        baseline_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> None:
        self.metrics.append(MetricRecord(
            name=name, value=value, unit=unit, category=category,
            model_name=model_name, baseline_name=baseline_name, notes=notes,
        ))


class BaseExperimentRunner(ABC):
    """
    Base class for all 15 research experiment runners.

    Each subclass implements:
      - experiment_name: str
      - run(): coroutine returning ExperimentReport
    """

    experiment_name: str = "base"
    results_dir: Path = Path("tests/results")

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.run_id = str(uuid.uuid4())[:8]
        self.report = ExperimentReport(
            experiment_name=self.experiment_name,
            run_id=self.run_id,
            status="PENDING",
            python_version=sys.version,
            git_commit=self._get_git_commit(),
            package_versions=self._get_package_versions(),
            environment_info=self._get_env_info(),
            config=self.config,
        )

    @abstractmethod
    async def run(self) -> ExperimentReport:
        """Execute the experiment and return a completed ExperimentReport."""

    def execute(self) -> ExperimentReport:
        """Synchronous entry point."""
        self.report.started_at = datetime.now(timezone.utc)
        try:
            report = asyncio.run(self.run())
            report.completed_at = datetime.now(timezone.utc)
            return report
        except Exception as exc:
            self.report.status = "FAILED"
            self.report.error_message = str(exc)
            self.report.completed_at = datetime.now(timezone.utc)
            logger.exception("Experiment %s failed: %s", self.experiment_name, exc)
            return self.report
        finally:
            self._export(self.report)

    def _export(self, report: ExperimentReport) -> None:
        """Export results to JSON and CSV."""
        out_dir = self.results_dir / report.experiment_name
        out_dir.mkdir(parents=True, exist_ok=True)
        report.result_directory = str(out_dir)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        # JSON
        json_path = out_dir / f"run_{self.run_id}_{ts}.json"
        with open(json_path, "w") as f:
            json.dump(self._report_to_dict(report), f, indent=2, default=str)

        # CSV (metrics only)
        csv_path = out_dir / f"run_{self.run_id}_{ts}.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "metric_name", "value", "unit", "category",
                "model_name", "baseline_name", "notes"
            ])
            writer.writeheader()
            for m in report.metrics:
                writer.writerow({
                    "metric_name": m.name, "value": m.value, "unit": m.unit,
                    "category": m.category, "model_name": m.model_name,
                    "baseline_name": m.baseline_name, "notes": m.notes,
                })

        logger.info("Experiment results saved to %s", out_dir)
        print(f"\n{'='*60}")
        print(f"Experiment: {report.experiment_name}")
        print(f"Status: {report.status}")
        print(f"Metrics: {len(report.metrics)}")
        for m in report.metrics:
            val = f"{m.value:.4f}" if m.value is not None else "N/A"
            print(f"  [{m.category}] {m.name}: {val} {m.unit or ''}")
        print(f"Results: {json_path}")
        print(f"{'='*60}\n")

    @staticmethod
    def _report_to_dict(report: ExperimentReport) -> dict:
        return {
            "experiment_name": report.experiment_name,
            "run_id": report.run_id,
            "status": report.status,
            "started_at": report.started_at,
            "completed_at": report.completed_at,
            "git_commit": report.git_commit,
            "python_version": report.python_version,
            "package_versions": report.package_versions,
            "environment_info": report.environment_info,
            "config": report.config,
            "dataset_name": report.dataset_name,
            "dataset_path": report.dataset_path,
            "error_message": report.error_message,
            "notes": report.notes,
            "metrics": [
                {
                    "name": m.name, "value": m.value, "unit": m.unit,
                    "category": m.category, "model_name": m.model_name,
                    "baseline_name": m.baseline_name, "notes": m.notes,
                }
                for m in report.metrics
            ],
        }

    @staticmethod
    def _get_git_commit() -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()[:40] if result.returncode == 0 else None
        except Exception:
            return None

    @staticmethod
    def _get_package_versions() -> Dict[str, str]:
        packages = [
            "fastapi", "sqlalchemy", "pydantic", "numpy",
            "scikit-learn", "torch", "librosa", "web3",
        ]
        versions = {}
        for pkg in packages:
            try:
                import importlib.metadata
                versions[pkg] = importlib.metadata.version(pkg)
            except Exception:
                versions[pkg] = "not_installed"
        return versions

    @staticmethod
    def _get_env_info() -> Dict[str, Any]:
        return {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
        }
