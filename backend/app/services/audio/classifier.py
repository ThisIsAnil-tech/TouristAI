"""
app/services/audio/classifier.py — MobileNetV2-based distress classifier.

Implements the MobileNetV2 architecture as specified in the project documents.
Uses depthwise separable convolutions for edge-efficient inference.
"""
from __future__ import annotations

import torch
import torch.nn as nn
class InvertedResidual(nn.Module):
    def __init__(self, inp: int, oup: int, stride: int, expand_ratio: int) -> None:
        super().__init__()
        self.stride = stride
        hidden_dim = int(round(inp * expand_ratio))
        self.use_res_connect = self.stride == 1 and inp == oup

        layers = []
        if expand_ratio != 1:
            layers.append(nn.Conv2d(inp, hidden_dim, 1, 1, 0, bias=False))
            layers.append(nn.BatchNorm2d(hidden_dim))
            layers.append(nn.ReLU6(inplace=True))
        layers.extend([
            nn.Conv2d(hidden_dim, hidden_dim, 3, stride, 1, groups=hidden_dim, bias=False),
            nn.BatchNorm2d(hidden_dim),
            nn.ReLU6(inplace=True),
            nn.Conv2d(hidden_dim, oup, 1, 1, 0, bias=False),
            nn.BatchNorm2d(oup),
        ])
        self.conv = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.use_res_connect:
            return x + self.conv(x)
        return self.conv(x)


class MobileNetV2Classifier(nn.Module):
    """
    MobileNetV2-based audio distress classifier.

    Input:  [batch, 1, n_mels, time_frames]  (greyscale mel-spectrogram)
    Output: [batch, num_classes]              (logits)
    """

    def __init__(self, num_classes: int = 3, pretrained: bool = False) -> None:
        super().__init__()
        input_channel = 32
        last_channel = 1280

        # Architecture config: (expansion_factor, output_channels, num_blocks, stride)
        inverted_residual_setting = [
            (1, 16, 1, 1),
            (6, 24, 2, 2),
            (6, 32, 3, 2),
            (6, 64, 4, 2),
            (6, 96, 3, 1),
            (6, 160, 3, 2),
            (6, 320, 1, 1),
        ]

        # First layer: 1-channel mel-spectrogram input
        features = [
            nn.Sequential(
                nn.Conv2d(1, input_channel, 3, 2, 1, bias=False),
                nn.BatchNorm2d(input_channel),
                nn.ReLU6(inplace=True),
            )
        ]

        # Inverted residual blocks
        for t, c, n, s in inverted_residual_setting:
            for i in range(n):
                stride = s if i == 0 else 1
                features.append(InvertedResidual(input_channel, c, stride, expand_ratio=t))
                input_channel = c

        # Last conv
        features.append(
            nn.Sequential(
                nn.Conv2d(input_channel, last_channel, 1, 1, 0, bias=False),
                nn.BatchNorm2d(last_channel),
                nn.ReLU6(inplace=True),
            )
        )

        self.features = nn.Sequential(*features)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Dropout(0.2),
            nn.Linear(last_channel, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        return self.classifier(x)


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
