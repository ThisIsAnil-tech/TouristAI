"""
app/services/audio/inference.py — Backend audio inference service.

Implements actual audio preprocessing and MobileNetV2-based inference.
Mode B: backend receives audio file and performs classification.

Pipeline:
  audio bytes → resample → normalize → mel-spectrogram → CNN → probabilities → decision
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from app.config import settings
from app.models.audio import AudioClass

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    predicted_class: AudioClass
    confidence: float
    class_probabilities: Dict[str, float]
    model_version: str


class AudioModelNotLoadedError(Exception):
    """Raised when no trained model weights are available."""


class AudioInferenceService:
    """
    Actual audio distress inference service.

    Loads trained MobileNetV2 weights from AUDIO_MODEL_PATH.
    Falls back to AUDIO_MOCK_MODE only when explicitly enabled.
    """

    _model = None
    _model_version: str = "unloaded"
    _CLASS_LABELS = [AudioClass.SCREAM, AudioClass.GLASS_BREAK, AudioClass.NORMAL]

    @classmethod
    def _load_model(cls) -> None:
        """Load MobileNetV2 model from disk (lazy, singleton)."""
        if cls._model is not None:
            return

        model_path = Path(settings.AUDIO_MODEL_PATH)

        if settings.AUDIO_MOCK_MODE:
            logger.warning("Audio inference running in MOCK MODE")
            cls._model = "mock"
            cls._model_version = "mock-0.0"
            return

        if not model_path.exists():
            raise AudioModelNotLoadedError(
                f"Audio model not found at {model_path}. "
                f"Train the model and place weights at {model_path}. "
                f"Set AUDIO_MOCK_MODE=true for development without a trained model."
            )

        import torch
        from app.services.audio.classifier import MobileNetV2Classifier

        model = MobileNetV2Classifier(num_classes=len(cls._CLASS_LABELS))
        state = torch.load(model_path, map_location="cpu", weights_only=True)
        model.load_state_dict(state["model_state_dict"])
        model.eval()
        cls._model = model
        cls._model_version = state.get("version", "1.0")
        logger.info("Audio model loaded: v%s from %s", cls._model_version, model_path)

    async def infer(self, audio_bytes: bytes) -> InferenceResult:
        """
        Run actual inference on raw audio bytes.

        Args:
            audio_bytes: Raw audio file content (WAV/MP3/FLAC).

        Returns:
            InferenceResult with predicted class and confidence.
        """
        self._load_model()

        if self._model == "mock":
            return self._mock_result()

        mel = self._preprocess(audio_bytes)

        import torch
        with torch.no_grad():
            tensor = torch.FloatTensor(mel).unsqueeze(0).unsqueeze(0)  # [1, 1, n_mels, frames]
            logits = self._model(tensor)
            probs = torch.softmax(logits, dim=-1).squeeze().numpy()

        predicted_idx = int(np.argmax(probs))
        predicted_class = self._CLASS_LABELS[predicted_idx]
        confidence = float(probs[predicted_idx])

        class_probs = {
            label.value: float(probs[i])
            for i, label in enumerate(self._CLASS_LABELS)
        }

        return InferenceResult(
            predicted_class=predicted_class,
            confidence=confidence,
            class_probabilities=class_probs,
            model_version=self._model_version,
        )

    def _preprocess(self, audio_bytes: bytes) -> np.ndarray:
        """
        Full audio preprocessing pipeline:
          raw bytes → load → resample → normalize → Mel-spectrogram
        """
        import librosa

        audio_io = io.BytesIO(audio_bytes)
        y, sr = librosa.load(audio_io, sr=settings.AUDIO_SAMPLE_RATE, mono=True)

        # Trim/pad to fixed duration
        target_len = settings.AUDIO_SAMPLE_RATE * settings.AUDIO_DURATION_SECONDS
        if len(y) > target_len:
            y = y[:target_len]
        else:
            y = np.pad(y, (0, target_len - len(y)))

        # Normalize amplitude
        max_val = np.abs(y).max()
        if max_val > 0:
            y = y / max_val

        # Mel-spectrogram
        mel = librosa.feature.melspectrogram(
            y=y,
            sr=sr,
            n_mels=settings.AUDIO_N_MELS,
            hop_length=settings.AUDIO_HOP_LENGTH,
            n_fft=settings.AUDIO_N_FFT,
        )
        # Convert to dB and normalize to [0, 1]
        mel_db = librosa.power_to_db(mel, ref=np.max)
        mel_norm = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
        return mel_norm.astype(np.float32)

    @classmethod
    def _mock_result(cls) -> InferenceResult:
        """Mock result for development only — clearly labelled."""
        return InferenceResult(
            predicted_class=AudioClass.NORMAL,
            confidence=0.85,
            class_probabilities={
                AudioClass.SCREAM.value: 0.10,
                AudioClass.GLASS_BREAK.value: 0.05,
                AudioClass.NORMAL.value: 0.85,
            },
            model_version="mock-0.0",
        )
