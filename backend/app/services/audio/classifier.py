"""
app/services/audio/classifier.py — MobileNetV2-based distress classifier.

Implements the MobileNetV2 architecture as specified in the project documents.
Uses depthwise separable convolutions for edge-efficient inference.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torchvision.models as tv_models


class MobileNetV2Classifier(nn.Module):
    """
    MobileNetV2-based audio distress classifier.

    Input:  [batch, 1, n_mels, time_frames]  (greyscale mel-spectrogram)
    Output: [batch, num_classes]              (logits)

    Architecture based on MobileNetV2 pretrained on ImageNet,
    adapted for single-channel audio spectrograms.
    """

    def __init__(self, num_classes: int = 3, pretrained: bool = False) -> None:
        super().__init__()

        # Load MobileNetV2 backbone
        weights = tv_models.MobileNet_V2_Weights.DEFAULT if pretrained else None
        backbone = tv_models.mobilenet_v2(weights=weights)

        # Adapt first conv layer for 1-channel input (mel-spectrogram)
        # Original: Conv2d(3, 32, ...) → New: Conv2d(1, 32, ...)
        original_conv = backbone.features[0][0]
        backbone.features[0][0] = nn.Conv2d(
            1,
            original_conv.out_channels,
            kernel_size=original_conv.kernel_size,
            stride=original_conv.stride,
            padding=original_conv.padding,
            bias=False,
        )

        if pretrained:
            # Average the 3-channel weights into 1-channel
            with torch.no_grad():
                backbone.features[0][0].weight.data = (
                    original_conv.weight.data.mean(dim=1, keepdim=True)
                )

        self.features = backbone.features
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(backbone.last_channel, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        x = self.classifier(x)
        return x


class CNNBaselineClassifier(nn.Module):
    """
    Simple CNN baseline for comparison in research experiments.

    4 convolutional layers + global average pooling + FC.
    """

    def __init__(self, num_classes: int = 3, n_mels: int = 128) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(128, 256, kernel_size=3, padding=1), nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.pool(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)
