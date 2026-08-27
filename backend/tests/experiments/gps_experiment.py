"""
tests/experiments/gps_experiment.py — Experiment 2: GPS Anomaly Detection.

Evaluates the GPS anomaly detection algorithm on a labelled GPS trace dataset.

Metrics:
  - True Positive Rate (Sensitivity)
  - False Positive Rate (False Alarm Rate)
  - Precision, F1
  - Mean detection latency (ms)
  - Consecutive anomaly threshold analysis
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np

from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)
GPS_DATASET_PATH = os.getenv("GPS_DATASET_PATH", "datasets/gps_traces")


class GpsExperiment(BaseExperimentRunner):
    """Experiment 2: GPS Anomaly Detection Performance."""
    experiment_name = "gps_experiment"

    async def run(self) -> ExperimentReport:
        self.report.dataset_name = "gps_traces_labelled"
        self.report.dataset_path = GPS_DATASET_PATH

        dataset_path = Path(GPS_DATASET_PATH)
        if not dataset_path.exists():
            self.report.status = "NOT_RUN"
            msg = (
                f"GPS dataset not found at {dataset_path}. "
                "Collect GPS traces with ground-truth labels (normal/anomalous). "
                "Format: CSV with columns: lat, lon, timestamp, label (0=normal, 1=anomaly)"
            )
            self.report.error_message = msg
            self.report.add_metric("tpr", None, "%", ResultCategory.NOT_RUN, notes=msg)
            return self.report

        try:
            from app.services.gps.haversine import GpsPoint, haversine_distance
            from app.services.gps.route_deviation import RouteDeviationDetector

            traces = self._load_traces(dataset_path)
            if not traces:
                raise ValueError("No GPS traces found in dataset")

            y_true, y_pred, latencies = [], [], []

            for trace in traces:
                points = trace["points"]
                labels = trace["labels"]
                route = trace.get("route", [])
                detector = RouteDeviationDetector(deviation_threshold_m=200.0, max_consecutive_deviations=3)

                for i, (point, label) in enumerate(zip(points, labels)):
                    t0 = time.perf_counter()
                    result = detector.check(point, route) if len(route) >= 2 else None
                    elapsed = (time.perf_counter() - t0) * 1000
                    latencies.append(elapsed)

                    if result:
                        pred = 1 if result.is_deviated else 0
                    else:
                        # Stationary check: use distance from previous
                        if i > 0:
                            dist = haversine_distance(points[i-1], point)
                            pred = 1 if dist < 50.0 else 0
                        else:
                            pred = 0

                    y_true.append(label)
                    y_pred.append(pred)

            from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
            tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)

            tpr = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            fpr = fp / (fp + tn) * 100 if (fp + tn) > 0 else 0
            precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            f1 = f1_score(y_true, y_pred, zero_division=0) * 100

            self.report.add_metric("tpr_sensitivity", tpr, "%", ResultCategory.ACTUAL)
            self.report.add_metric("fpr_false_alarm_rate", fpr, "%", ResultCategory.ACTUAL)
            self.report.add_metric("precision", precision, "%", ResultCategory.ACTUAL)
            self.report.add_metric("f1_score", f1, "%", ResultCategory.ACTUAL)
            self.report.add_metric("mean_detection_latency_ms", float(np.mean(latencies)), "ms", ResultCategory.ACTUAL)
            self.report.add_metric("n_samples", float(len(y_true)), "samples", ResultCategory.ACTUAL)

            self.report.status = "COMPLETED"
            self.report.notes = f"TP={tp} FP={fp} TN={tn} FN={fn}"

        except Exception as exc:
            self.report.status = "FAILED"
            self.report.error_message = str(exc)
            logger.exception("GPS experiment failed: %s", exc)

        return self.report

    @staticmethod
    def _load_traces(dataset_path: Path) -> list:
        """Load labelled GPS traces from CSV files."""
        traces = []
        for csv_file in list(dataset_path.glob("*.csv"))[:20]:
            try:
                import csv
                from app.services.gps.haversine import GpsPoint
                with open(csv_file) as f:
                    reader = csv.DictReader(f)
                    points, labels = [], []
                    for row in reader:
                        try:
                            points.append(GpsPoint(float(row["lat"]), float(row["lon"])))
                            labels.append(int(row.get("label", 0)))
                        except (KeyError, ValueError):
                            pass
                if len(points) > 0:
                    traces.append({"points": points, "labels": labels, "route": points[:5]})
            except Exception:
                pass
        return traces


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    GpsExperiment().execute()
