"""tests/experiments/edge_ai_experiment.py — Experiment 7: Edge AI Performance."""
from __future__ import annotations

import logging
import time
from pathlib import Path
import numpy as np
from tests.experiments.base_runner import BaseExperimentRunner, ExperimentReport, ResultCategory

logger = logging.getLogger(__name__)


class EdgeAiExperiment(BaseExperimentRunner):
    """Experiment 7: Edge AI inference performance on mobile-spec hardware."""
    experiment_name = "edge_ai_experiment"

    async def run(self) -> ExperimentReport:
        model_path = Path("models/audio/mobilenetv2_distress.pt")

        if not model_path.exists():
            note = f"Model not found at {model_path}. Run training first."
            self.report.status = "NOT_RUN"
            self.report.error_message = note
            self.report.add_metric("inference_time_ms", None, "ms", ResultCategory.NOT_RUN, notes=note)
            return self.report

        try:
            import torch
            from app.services.audio.classifier import MobileNetV2Classifier, CNNBaselineClassifier

            # Benchmark on CPU (simulates mobile device without GPU)
            models_to_test = {
                "MobileNetV2": MobileNetV2Classifier(num_classes=3),
                "CNN_Baseline": CNNBaselineClassifier(num_classes=3),
            }

            for model_name, model in models_to_test.items():
                model.eval()
                # Warm up
                dummy = torch.randn(1, 1, 128, 128)
                for _ in range(5):
                    with torch.no_grad():
                        model(dummy)

                # Benchmark 100 inferences
                times = []
                for _ in range(100):
                    t0 = time.perf_counter()
                    with torch.no_grad():
                        model(dummy)
                    times.append((time.perf_counter() - t0) * 1000)

                self.report.add_metric(
                    "inference_time_mean_ms", float(np.mean(times)), "ms",
                    ResultCategory.ACTUAL, model_name=model_name,
                    notes="CPU benchmark, n=100"
                )
                self.report.add_metric(
                    "inference_time_p95_ms", float(np.percentile(times, 95)), "ms",
                    ResultCategory.ACTUAL, model_name=model_name
                )

                # Model parameter count
                param_count = sum(p.numel() for p in model.parameters())
                self.report.add_metric(
                    "param_count", float(param_count), "params",
                    ResultCategory.ACTUAL, model_name=model_name
                )

                # Model file size
                if model_name == "MobileNetV2":
                    size_mb = model_path.stat().st_size / (1024**2)
                    self.report.add_metric("model_size_mb", size_mb, "MB",
                                           ResultCategory.ACTUAL, model_name=model_name)

            self.report.status = "COMPLETED"
            self.report.notes = "Benchmarked on CPU; mobile inference would use optimized ARM runtime"

        except Exception as exc:
            self.report.status = "FAILED"
            self.report.error_message = str(exc)

        return self.report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    EdgeAiExperiment().execute()
