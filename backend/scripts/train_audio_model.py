"""
scripts/train_audio_model.py — Train MobileNetV2 distress audio classifier.

Usage:
    python scripts/train_audio_model.py \
        --dataset-path datasets/audio_distress \
        --epochs 30 \
        --batch-size 32 \
        --output-path models/audio/mobilenetv2_distress.pt

Dataset structure expected:
    datasets/audio_distress/
        train/
            scream/     *.wav files
            glass_break/
            normal/
        val/
            scream/
            glass_break/
            normal/
        test/
            scream/
            glass_break/
            normal/
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

LABEL_MAP = {"scream": 0, "glass_break": 1, "normal": 2}
CLASS_NAMES = list(LABEL_MAP.keys())


def load_split(split_dir: Path, sample_rate: int, duration_s: int, n_mels: int, hop: int, n_fft: int):
    """Load audio files from a split directory into mel-spectrograms."""
    import librosa

    X, y = [], []
    target_len = sample_rate * duration_s
    for label, idx in LABEL_MAP.items():
        label_dir = split_dir / label
        if not label_dir.exists():
            logger.warning("Label directory missing: %s", label_dir)
            continue
        files = list(label_dir.glob("*.wav")) + list(label_dir.glob("*.mp3"))
        logger.info("Loading %d files for class '%s'", len(files), label)
        for fp in files:
            try:
                audio, sr = librosa.load(str(fp), sr=sample_rate, mono=True)
                if len(audio) > target_len:
                    audio = audio[:target_len]
                else:
                    audio = np.pad(audio, (0, target_len - len(audio)))
                max_val = np.abs(audio).max()
                if max_val > 0:
                    audio = audio / max_val
                mel = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=n_mels,
                                                      hop_length=hop, n_fft=n_fft)
                mel_db = librosa.power_to_db(mel, ref=np.max)
                mel_norm = (mel_db - mel_db.min()) / (mel_db.max() - mel_db.min() + 1e-8)
                X.append(mel_norm.astype(np.float32))
                y.append(idx)
            except Exception as exc:
                logger.warning("Failed to load %s: %s", fp, exc)
    return np.array(X), np.array(y)


def train(args):
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        from sklearn.metrics import accuracy_score, classification_report
        from app.services.audio.classifier import MobileNetV2Classifier
    except ImportError as exc:
        logger.error("Required packages missing: %s", exc)
        sys.exit(1)

    dataset_path = Path(args.dataset_path)
    if not dataset_path.exists():
        logger.error("Dataset path does not exist: %s", dataset_path)
        sys.exit(1)

    logger.info("Loading training data...")
    X_train, y_train = load_split(dataset_path / "train", args.sample_rate,
                                   args.duration, args.n_mels, args.hop_length, args.n_fft)
    X_val, y_val = load_split(dataset_path / "val", args.sample_rate,
                               args.duration, args.n_mels, args.hop_length, args.n_fft)

    if len(X_train) == 0:
        logger.error("No training samples found. Check dataset structure.")
        sys.exit(1)

    logger.info("Train: %d samples, Val: %d samples", len(X_train), len(X_val))

    # DataLoaders
    X_t = torch.FloatTensor(X_train).unsqueeze(1)
    y_t = torch.LongTensor(y_train)
    X_v = torch.FloatTensor(X_val).unsqueeze(1)
    y_v = torch.LongTensor(y_val)

    train_loader = DataLoader(TensorDataset(X_t, y_t), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(X_v, y_v), batch_size=args.batch_size, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Using device: %s", device)

    model = MobileNetV2Classifier(num_classes=len(LABEL_MAP), pretrained=True).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    criterion = nn.CrossEntropyLoss()

    # Class weights for imbalance
    if len(y_train) > 0:
        from sklearn.utils.class_weight import compute_class_weight
        class_weights = compute_class_weight("balanced", classes=np.array([0, 1, 2]), y=y_train)
        weight_tensor = torch.FloatTensor(class_weights).to(device)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)

    best_val_acc = 0.0
    history = []

    for epoch in range(args.epochs):
        # ── Train ────────────────────────────────────────────────────────
        model.train()
        train_loss, correct = 0.0, 0
        for X_b, y_b in train_loader:
            X_b, y_b = X_b.to(device), y_b.to(device)
            optimizer.zero_grad()
            logits = model(X_b)
            loss = criterion(logits, y_b)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(X_b)
            correct += (logits.argmax(1) == y_b).sum().item()

        train_acc = correct / len(X_train) * 100
        avg_loss = train_loss / len(X_train)

        # ── Validate ─────────────────────────────────────────────────────
        model.eval()
        val_preds, val_true = [], []
        with torch.no_grad():
            for X_b, y_b in val_loader:
                X_b = X_b.to(device)
                preds = model(X_b).argmax(1).cpu().numpy()
                val_preds.extend(preds)
                val_true.extend(y_b.numpy())

        val_acc = accuracy_score(val_true, val_preds) * 100
        scheduler.step()
        history.append({"epoch": epoch + 1, "train_loss": avg_loss,
                         "train_acc": train_acc, "val_acc": val_acc})
        logger.info("Epoch %d/%d: loss=%.4f train_acc=%.2f%% val_acc=%.2f%%",
                    epoch + 1, args.epochs, avg_loss, train_acc, val_acc)

        # Save best model
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            output_path = Path(args.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save({
                "model_state_dict": model.state_dict(),
                "version": "1.0",
                "epoch": epoch + 1,
                "val_acc": val_acc,
                "class_names": CLASS_NAMES,
                "config": vars(args),
            }, output_path)
            logger.info("✅ Best model saved: val_acc=%.2f%% → %s", val_acc, output_path)

    # Final test evaluation
    logger.info("\nFinal evaluation on test set...")
    X_test, y_test = load_split(dataset_path / "test", args.sample_rate,
                                 args.duration, args.n_mels, args.hop_length, args.n_fft)
    if len(X_test) > 0:
        checkpoint = torch.load(args.output_path, weights_only=True)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        X_test_t = torch.FloatTensor(X_test).unsqueeze(1).to(device)
        with torch.no_grad():
            test_preds = model(X_test_t).argmax(1).cpu().numpy()
        print("\nTest Set Classification Report:")
        print(classification_report(y_test, test_preds, target_names=CLASS_NAMES, zero_division=0))

    # Save training history
    history_path = Path(args.output_path).parent / "training_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f, indent=2)
    logger.info("Training complete. Best val_acc=%.2f%%", best_val_acc)


def main():
    parser = argparse.ArgumentParser(description="Train audio distress classifier")
    parser.add_argument("--dataset-path", default="datasets/audio_distress")
    parser.add_argument("--output-path", default="models/audio/mobilenetv2_distress.pt")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--sample-rate", type=int, default=22050)
    parser.add_argument("--duration", type=int, default=3)
    parser.add_argument("--n-mels", type=int, default=128)
    parser.add_argument("--hop-length", type=int, default=512)
    parser.add_argument("--n-fft", type=int, default=2048)
    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
