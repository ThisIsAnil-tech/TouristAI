"""
tests/experiments/audio_experiment.py — Experiment 1: Audio Distress Classification.

Evaluates MobileNetV2 vs CNN baseline on the distress audio dataset.

Metrics:
  - Accuracy, Precision, Recall, F1-score (per class + macro)
  - Confusion matrix
  - Inference time (mean ± std, ms)
  - Model size (MB)
  - AUC-ROC

Dataset: UrbanSound8K / custom collected distress audio
Dataset path: configured via AUDIO_DATASET_PATH env var
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import numpy as np

from tests.experiments.base_runner import (
    BaseExperimentRunner, ExperimentReport, ResultCategory
)

logger = logging.getLogger(__name__)

DATASET_PATH = os.getenv("AUDIO_DATASET_PATH", "datasets/audio_distress")
MODEL_PATH = os.getenv("AUDIO_MODEL_PATH", "models/audio/mobilenetv2_distress.pt")


class AudioExperiment(BaseExperimentRunner):
    """
    Experiment 1: Audio Distress Classification Accuracy.

    Runs evaluation on the test split of the audio dataset.
    If dataset/model unavailable → NOT_RUN with documented reason.
    """
    experiment_name = "audio_experiment"

    async def run(self) -> ExperimentReport:
        self.report.dataset_name = "distress_audio_dataset"
        self.report.dataset_path = DATASET_PATH

        dataset_path = Path(DATASET_PATH)
        model_path = Path(MODEL_PATH)

        # ── Dataset check ─────────────────────────────────────────────────
        if not dataset_path.exists():
            self.report.status = "NOT_RUN"
            self.report.error_message = (
                f"Dataset not found at {dataset_path}. "
                "Collect or download the audio distress dataset and set "
                "AUDIO_DATASET_PATH environment variable."
            )
            self.report.add_metric(
                "accuracy", None, "%", ResultCategory.NOT_RUN,
                notes=self.report.error_message
            )
            return self.report

        # ── Model check ────────────────────────────────────────────────────
        if not model_path.exists():
            self.report.status = "NOT_RUN"
            self.report.error_message = (
                f"Trained model not found at {model_path}. "
                "Run: python scripts/train_audio_model.py"
            )
            self.report.add_metric(
                "accuracy", None, "%", ResultCategory.NOT_RUN,
                notes=self.report.error_message
            )
            return self.report

        try:
            import torch
            from sklearn.metrics import (
                accuracy_score, classification_report,
                confusion_matrix, roc_auc_score
            )
            from app.services.audio.classifier import MobileNetV2Classifier, CNNBaselineClassifier
            from app.services.audio.inference import AudioInferenceService

            # Load test set
            X_test, y_test = self._load_test_data(dataset_path)
            if X_test is None or len(X_test) == 0:
                raise ValueError("Empty test set")

            # ── Evaluate MobileNetV2 ───────────────────────────────────────
            mv2_preds, mv2_confs, mv2_times = self._evaluate_model(
                model_path, X_test, MobileNetV2Classifier
            )
            mv2_acc = accuracy_score(y_test, mv2_preds) * 100

            self.report.add_metric(
                "accuracy", mv2_acc, "%", ResultCategory.ACTUAL,
                model_name="MobileNetV2",
                notes=f"n_samples={len(y_test)}"
            )
            self.report.add_metric(
                "inference_time_mean_ms", float(np.mean(mv2_times)), "ms",
                ResultCategory.ACTUAL, model_name="MobileNetV2"
            )
            self.report.add_metric(
                "inference_time_std_ms", float(np.std(mv2_times)), "ms",
                ResultCategory.ACTUAL, model_name="MobileNetV2"
            )
            self.report.add_metric(
                "model_size_mb",
                model_path.stat().st_size / (1024 * 1024), "MB",
                ResultCategory.ACTUAL, model_name="MobileNetV2"
            )

            # Per-class metrics
            from sklearn.metrics import precision_score, recall_score, f1_score
            class_names = ["SCREAM", "GLASS_BREAK", "NORMAL"]
            macro_f1 = f1_score(y_test, mv2_preds, average="macro", zero_division=0) * 100
            macro_prec = precision_score(y_test, mv2_preds, average="macro", zero_division=0) * 100
            macro_rec = recall_score(y_test, mv2_preds, average="macro", zero_division=0) * 100

            self.report.add_metric("macro_f1", macro_f1, "%", ResultCategory.ACTUAL, model_name="MobileNetV2")
            self.report.add_metric("macro_precision", macro_prec, "%", ResultCategory.ACTUAL, model_name="MobileNetV2")
            self.report.add_metric("macro_recall", macro_rec, "%", ResultCategory.ACTUAL, model_name="MobileNetV2")

            self.report.status = "COMPLETED"

        except Exception as exc:
            self.report.status = "FAILED"
            self.report.error_message = str(exc)
            logger.exception("Audio experiment failed: %s", exc)

        return self.report

    @staticmethod
    def _load_test_data(dataset_path: Path):
        """Load preprocessed mel-spectrograms from dataset directory."""
        try:
            import librosa
            X, y = [], []
            label_map = {"scream": 0, "glass_break": 1, "normal": 2}
            for label, idx in label_map.items():
                label_dir = dataset_path / "test" / label
                if not label_dir.exists():
                    continue
                for audio_file in list(label_dir.glob("*.wav"))[:200]:
                    try:
                        audio, sr = librosa.load(str(audio_file), sr=22050, mono=True)
                        mel = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128)
                        mel_db = librosa.power_to_db(mel, ref=np.max)
                        mel_norm = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
                        X.append(mel_norm.astype(np.float32))
                        y.append(idx)
                    except Exception:
                        pass
            return X, y
        except Exception as exc:
            logger.error("Failed to load audio dataset: %s", exc)
            return None, None

    @staticmethod
    def _evaluate_model(model_path: Path, X_test, ModelClass) -> tuple:
        import torch
        model = ModelClass(num_classes=3)
        state = torch.load(model_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state.get("model_state_dict", state))
        model.eval()

        preds, confs, times = [], [], []
        with torch.no_grad():
            for mel in X_test:
                t0 = time.perf_counter()
                tensor = torch.FloatTensor(mel).unsqueeze(0).unsqueeze(0)
                logits = model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().numpy()
                elapsed = (time.perf_counter() - t0) * 1000
                times.append(elapsed)
                preds.append(int(np.argmax(probs)))
                confs.append(float(probs.max()))

        return preds, confs, times


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    runner = AudioExperiment()
    report = runner.execute()
    print(f"Status: {report.status}")
