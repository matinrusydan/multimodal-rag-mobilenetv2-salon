"""Standalone UNet architecture for binary hair segmentation.

This module provides a pure-PyTorch, lightweight UNet implementation with
residual double-conv blocks, bilinear/transposed upsampling, and single-channel
sigmoid output. It is self-contained with no external segmentation dependencies,
enabling direct training, ONNX export, and CPU/GPU inference.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DoubleConv(nn.Module):
    """[Conv2d -> BatchNorm -> ReLU] * 2 with optional residual connection."""

    def __init__(self, in_channels: int, out_channels: int, residual: bool = True):
        super().__init__()
        self.residual = residual and (in_channels == out_channels)
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = self.conv(x)
        if self.residual:
            out = out + x
        return out


class Down(nn.Module):
    """Downscaling with MaxPool2d then DoubleConv."""

    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.mpconv = nn.Sequential(
            nn.MaxPool2d(2),
            DoubleConv(in_channels, out_channels),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.mpconv(x)


class Up(nn.Module):
    """Upscaling with Bilinear interpolation or ConvTranspose2d, then DoubleConv."""

    def __init__(self, in_channels: int, out_channels: int, bilinear: bool = True):
        super().__init__()
        if bilinear:
            self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
            self.conv = DoubleConv(in_channels, out_channels)
        else:
            self.up = nn.ConvTranspose2d(in_channels // 2, in_channels // 2, kernel_size=2, stride=2)
            self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1: torch.Tensor, x2: torch.Tensor) -> torch.Tensor:
        x1 = self.up(x1)
        # Pad x1 to match x2 size if odd dimensions
        diff_y = x2.size()[2] - x1.size()[2]
        diff_x = x2.size()[3] - x1.size()[3]
        if diff_x > 0 or diff_y > 0:
            x1 = F.pad(x1, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)


class HairUNet(nn.Module):
    """Lightweight 4-level UNet for binary hair segmentation.

    Args:
        in_channels: Input image channels (default: 3 for RGB).
        out_channels: Output mask channels (default: 1 for binary hair mask).
        base_features: Number of features in the first layer (default: 32).
        bilinear: Use bilinear upsampling (True) or transposed conv (False).
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: int = 1,
        base_features: int = 32,
        bilinear: bool = True,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.bilinear = bilinear

        f = base_features  # default 32 -> 64 -> 128 -> 256 -> bottleneck 512
        self.inc = DoubleConv(in_channels, f, residual=False)
        self.down1 = Down(f, f * 2)
        self.down2 = Down(f * 2, f * 4)
        self.down3 = Down(f * 4, f * 8)
        factor = 2 if bilinear else 1
        self.down4 = Down(f * 8, (f * 16) // factor)

        self.up1 = Up(f * 16, (f * 8) // factor, bilinear)
        self.up2 = Up(f * 8, (f * 4) // factor, bilinear)
        self.up3 = Up(f * 4, (f * 2) // factor, bilinear)
        self.up4 = Up(f * 2, f, bilinear)
        self.outc = nn.Conv2d(f, out_channels, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)

        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        logits = self.outc(x)
        return logits


class DecoderBlock(nn.Module):
    """Upsample -> Concat skip -> DoubleConv."""

    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super().__init__()
        self.up = nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True)
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels + skip_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor | None = None) -> torch.Tensor:
        x = self.up(x)
        if skip is not None:
            diff_y = skip.size(2) - x.size(2)
            diff_x = skip.size(3) - x.size(3)
            if diff_x > 0 or diff_y > 0:
                x = F.pad(x, [diff_x // 2, diff_x - diff_x // 2, diff_y // 2, diff_y - diff_y // 2])
            x = torch.cat([skip, x], dim=1)
        return self.conv(x)


class MobileNetV2UNet(nn.Module):
    """UNet with ImageNet-pretrained MobileNetV2 encoder (docs/08-roadmap Section 8.2)."""

    def __init__(self, pretrained: bool = True, out_channels: int = 1):
        super().__init__()
        from torchvision import models

        weights = models.MobileNet_V2_Weights.DEFAULT if pretrained else None
        m = models.mobilenet_v2(weights=weights)
        feats = m.features

        # Slices corresponding to strides 2, 4, 8, 16, 32
        self.enc0 = feats[0:2]    # -> (16, H/2, W/2)
        self.enc1 = feats[2:4]    # -> (24, H/4, W/4)
        self.enc2 = feats[4:7]    # -> (32, H/8, W/8)
        self.enc3 = feats[7:14]   # -> (96, H/16, W/16)
        self.enc4 = feats[14:19]  # -> (1280, H/32, W/32)

        # Decoder stages
        self.dec4 = DecoderBlock(in_channels=1280, skip_channels=96, out_channels=256) # -> H/16
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=32, out_channels=128)  # -> H/8
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=24, out_channels=64)   # -> H/4
        self.dec1 = DecoderBlock(in_channels=64, skip_channels=16, out_channels=32)    # -> H/2
        self.dec0 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True),            # -> H
            nn.Conv2d(32, 16, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, out_channels, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e0 = self.enc0(x)   # (16, 128, 128)
        e1 = self.enc1(e0)  # (24, 64, 64)
        e2 = self.enc2(e1)  # (32, 32, 32)
        e3 = self.enc3(e2)  # (96, 16, 16)
        e4 = self.enc4(e3)  # (1280, 8, 8)

        d4 = self.dec4(e4, e3)
        d3 = self.dec3(d4, e2)
        d2 = self.dec2(d3, e1)
        d1 = self.dec1(d2, e0)
        out = self.dec0(d1)
        return out


class ResNet34UNet(nn.Module):
    """UNet with ImageNet-pretrained ResNet34 encoder (docs/08-roadmap Section 8.2)."""

    def __init__(self, pretrained: bool = True, out_channels: int = 1):
        super().__init__()
        from torchvision import models

        weights = models.ResNet34_Weights.DEFAULT if pretrained else None
        m = models.resnet34(weights=weights)

        self.enc0 = nn.Sequential(m.conv1, m.bn1, m.relu)  # (64, H/2, W/2)
        self.enc1 = nn.Sequential(m.maxpool, m.layer1)     # (64, H/4, W/4)
        self.enc2 = m.layer2                               # (128, H/8, W/8)
        self.enc3 = m.layer3                               # (256, H/16, W/16)
        self.enc4 = m.layer4                               # (512, H/32, W/32)

        self.dec4 = DecoderBlock(in_channels=512, skip_channels=256, out_channels=256)
        self.dec3 = DecoderBlock(in_channels=256, skip_channels=128, out_channels=128)
        self.dec2 = DecoderBlock(in_channels=128, skip_channels=64, out_channels=64)
        self.dec1 = DecoderBlock(in_channels=64, skip_channels=64, out_channels=32)
        self.dec0 = nn.Sequential(
            nn.Upsample(scale_factor=2, mode="bilinear", align_corners=True),
            nn.Conv2d(32, 16, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, out_channels, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e0 = self.enc0(x)
        e1 = self.enc1(e0)
        e2 = self.enc2(e1)
        e3 = self.enc3(e2)
        e4 = self.enc4(e3)

        d4 = self.dec4(e4, e3)
        d3 = self.dec3(d4, e2)
        d2 = self.dec2(d3, e1)
        d1 = self.dec1(d2, e0)
        out = self.dec0(d1)
        return out


def build_hair_segmentation_model(
    arch: str = "mobilenet_v2",
    pretrained: bool = True,
    base_features: int = 32,
    out_channels: int = 1,
) -> nn.Module:
    """Build hair segmentation model according to architecture choice."""
    arch_norm = arch.lower().replace("-", "_")
    if arch_norm in ("mobilenet_v2", "mobilenet", "mobilenet_v2_unet"):
        return MobileNetV2UNet(pretrained=pretrained, out_channels=out_channels)
    elif arch_norm in ("resnet34", "resnet34_unet"):
        return ResNet34UNet(pretrained=pretrained, out_channels=out_channels)
    elif arch_norm in ("scratch", "hair_unet", "unet"):
        return HairUNet(
            in_channels=3,
            out_channels=out_channels,
            base_features=base_features,
            bilinear=True,
        )
    else:
        raise ValueError(
            f"Unknown architecture: {arch} (supported: 'mobilenet_v2', 'resnet34', 'scratch')"
        )


class BCEDiceLoss(nn.Module):
    """Combination of Binary Cross-Entropy and Soft Dice Loss.

    Loss = alpha * BCE + (1 - alpha) * Dice
    """

    def __init__(self, alpha: float = 0.5, smooth: float = 1.0):
        super().__init__()
        self.alpha = alpha
        self.smooth = smooth

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce = F.binary_cross_entropy_with_logits(logits, targets)

        probs = torch.sigmoid(logits)
        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        dice = (2.0 * intersection + self.smooth) / (probs_flat.sum() + targets_flat.sum() + self.smooth)
        dice_loss = 1.0 - dice

        return self.alpha * bce + (1.0 - self.alpha) * dice_loss
