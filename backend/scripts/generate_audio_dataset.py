"""
scripts/generate_audio_dataset.py — Generate synthetic distress audio dataset.

Synthesizes reproducible .wav audio files for distress classes:
  - scream: high pitch resonant FM sweep (1kHz - 3.5kHz)
  - glass_break: sharp transient impulsive bursts with high-frequency noise (3kHz - 7kHz)
  - normal: ambient low-frequency pink/brown noise and speech-like harmonics

Creates:
  datasets/audio_distress/
    train/ (scream, glass_break, normal) - 30 files each
    val/   (scream, glass_break, normal) - 10 files each
    test/  (scream, glass_break, normal) - 10 files each
"""
from __future__ import annotations

import argparse
import logging
import struct
import wave
from pathlib import Path
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def write_wav(fp: Path, audio: np.ndarray, sr: int):
    # Scale to 16-bit PCM
    audio_int16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    with wave.open(str(fp), "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sr)
        wav_file.writeframes(audio_int16.tobytes())


def generate_scream(duration: float = 2.0, sr: int = 16000, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Pitch sweep 1200 Hz to 2800 Hz with vibrato modulation
    f0 = 1200 + 1400 * np.sin(np.pi * t / duration)
    vibrato = 30 * np.sin(2 * np.pi * 7 * t)
    phase = 2 * np.pi * np.cumsum((f0 + vibrato) / sr)
    signal = 0.6 * np.sin(phase) + 0.3 * np.sin(2 * phase) + 0.1 * np.sin(3 * phase)
    # Add turbulent breath noise
    noise = rng.normal(0, 0.15, len(t))
    envelope = np.sin(np.pi * t / duration) ** 0.5
    return (signal + noise) * envelope


def generate_glass_break(duration: float = 2.0, sr: int = 16000, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = np.zeros_like(t)
    # Multiple sharp impact bursts
    for _ in range(rng.integers(3, 7)):
        offset = rng.uniform(0.1, 0.6)
        idx = int(offset * sr)
        if idx < len(t):
            burst_len = int(rng.uniform(0.05, 0.25) * sr)
            end_idx = min(idx + burst_len, len(t))
            burst_t = t[:end_idx - idx]
            decay = np.exp(-burst_t * rng.uniform(25, 60))
            burst_freq = rng.uniform(3000, 6000)
            burst = np.sin(2 * np.pi * burst_freq * burst_t) * decay
            noise = rng.normal(0, 0.4, len(burst)) * decay
            signal[idx:end_idx] += burst + noise
    return signal / (np.max(np.abs(signal)) + 1e-8)


def generate_normal(duration: float = 2.0, sr: int = 16000, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Low frequency gentle ambient wind / speech hum
    f_hum = 150 + 50 * np.sin(2 * np.pi * 0.5 * t)
    signal = 0.3 * np.sin(2 * np.pi * f_hum * t)
    # Gentle low-pass filtered background noise
    noise = rng.normal(0, 0.1, len(t))
    envelope = 0.5 + 0.5 * np.sin(np.pi * t / duration)
    return (signal + noise) * envelope


def build_dataset(base_dir: Path, sr: int = 16000, duration: float = 2.0):
    splits = {
        "train": {"scream": 30, "glass_break": 30, "normal": 30},
        "val": {"scream": 10, "glass_break": 10, "normal": 10},
        "test": {"scream": 10, "glass_break": 10, "normal": 10},
    }

    base_dir.mkdir(parents=True, exist_ok=True)
    seed = 100

    for split_name, class_counts in splits.items():
        split_dir = base_dir / split_name
        for cls_name, count in class_counts.items():
            cls_dir = split_dir / cls_name
            cls_dir.mkdir(parents=True, exist_ok=True)
            for i in range(count):
                seed += 1
                if cls_name == "scream":
                    audio = generate_scream(duration, sr, seed)
                elif cls_name == "glass_break":
                    audio = generate_glass_break(duration, sr, seed)
                else:
                    audio = generate_normal(duration, sr, seed)
                
                # Normalize
                max_v = np.max(np.abs(audio))
                if max_v > 0:
                    audio = audio / max_v

                out_fp = cls_dir / f"{cls_name}_{i:03d}.wav"
                write_wav(out_fp, audio, sr)

    logger.info("Synthetic audio dataset created at %s", base_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=str, default="datasets/audio_distress")
    parser.add_argument("--sample-rate", type=int, default=16000)
    parser.add_argument("--duration", type=float, default=2.0)
    args = parser.parse_args()

    build_dataset(Path(args.output_dir), args.sample_rate, args.duration)
