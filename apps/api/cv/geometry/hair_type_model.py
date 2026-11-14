"""Phase 4: Hair Type CNN Architecture & Model Builder.

Defines the Stage 1 Hair Type classifier using ImageNet pretrained backbones
(EfficientNetV2-S or MobileNetV2) adapted for 4 canonical hair type classes:
["lurus", "bergelombang", "keriting", "sangat-keriting"].
Includes model building, forward pass, and ONNX export helpers.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Tuple

HAIR_TYPE_CLASSES = ["lurus", "bergelombang", "keriting", "sangat-keriting"]


def build_hair_type_model(
    arch: str = "efficientnet_v2_s",
    pretrained: bool = True,
    num_classes: int = len(HAIR_TYPE_CLASSES),
    dropout: float = 0.3,
):
    """Build a PyTorch classifier for hair type.

    Supported architectures:
    - 'efficientnet_v2_s': Benchmark winner (21.5M params), high accuracy and stability.
    - 'mobilenet_v2': Lightweight alternative (3.5M params), fast CPU inference.
    """
    import torch
    import torch.nn as nn
    from torchvision import models
    if arch == "efficientnet_v2_s":
        weights = models.EfficientNet_V2_S_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_v2_s(weights=weights)
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=dropout, inplace=True),
            nn.Linear(in_features, num_classes),
        )
    elif arch == "mobilenet_v2":
        weights = models.MobileNet_V2_Weights.DEFAULT if pretrained else None
        model = models.mobilenet_v2(weights=weights)
        in_features = model.last_channel
        model.classifier = nn.Sequential(
            nn.Dropout(p=dropout, inplace=True),
            nn.Linear(in_features, num_classes),
        )
    else:
        raise ValueError(f"Unsupported architecture: {arch}. Choose 'efficientnet_v2_s' or 'mobilenet_v2'.")

    return model


def export_hair_type_onnx(
    model: nn.Module,
    onnx_path: Path,
    img_size: int = 224,
    opset: int = 17,
) -> Path:
    """Export trained PyTorch model to ONNX with dynamic batch size."""
    import torch

    onnx_path = Path(onnx_path)
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    model_cpu = model.to("cpu").eval()
    dummy = torch.randn(1, 3, img_size, img_size, dtype=torch.float32)

    export_kwargs = {
        "export_params": True,
        "opset_version": opset,
        "do_constant_folding": True,
        "input_names": ["input"],
        "output_names": ["logits"],
        "dynamic_axes": {"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
    }
    try:
        torch.onnx.export(model_cpu, dummy, str(onnx_path), dynamo=False, **export_kwargs)
    except TypeError:
        torch.onnx.export(model_cpu, dummy, str(onnx_path), **export_kwargs)

    return onnx_path
