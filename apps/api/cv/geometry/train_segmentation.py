"""Phase 2: UNet Hair Segmentation Training & Evaluation Pipeline.

Trains a lightweight UNet model (or optional ResNet/MobileNet-style encoder via
pure PyTorch HairUNet) on the curated Figaro-1k dataset split from Phase 1
(`curated_manifest.json`) paired with extracted ground-truth binary masks
(`data/figaro1k_gt/*.png`), evaluates on validation and locked test splits,
checks the Phase 2 gate (IoU >= 0.75, Dice >= 0.85, CPU inference < 200ms),
exports `hair_segmentation.onnx`, and records `segmentation_eval.json`.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
from PIL import Image, ImageOps
from torch.utils.data import DataLoader, Dataset

# Allow direct import when executed as script or via unittest
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from unet_model import BCEDiceLoss, HairUNet, build_hair_segmentation_model

DEFAULT_MANIFEST = HERE / "reports" / "phase1" / "curated_manifest.json"
DEFAULT_DATASET = HERE.parent / "dataset"
DEFAULT_MASK_DIR = HERE / "data" / "figaro1k_gt"
DEFAULT_WEIGHTS_DIR = HERE / "weights"
DEFAULT_REPORTS_DIR = HERE / "reports"
DEFAULT_FIGURES_DIR = DEFAULT_REPORTS_DIR / "figures"

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_figaro_split_records(
    manifest_path: Path,
    dataset_dir: Path,
    mask_dir: Path,
) -> Dict[str, List[dict]]:
    """Load Figaro-1k image/mask pairs grouped by Phase 1 split (train/val/test)."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Curated manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    splits: Dict[str, List[dict]] = {"train": [], "val": [], "test": []}
    for rec in manifest.get("records", []):
        if rec.get("cohort") != "figaro1k":
            continue
        split = rec.get("split")
        if split not in splits:
            continue
        img_path = dataset_dir / rec["image_id"]
        frame_no = int(Path(rec["image_id"]).stem)
        mask_path = mask_dir / f"{frame_no:05d}.png"
        if not img_path.exists():
            raise FileNotFoundError(f"Image missing: {img_path}")
        if not mask_path.exists():
            raise FileNotFoundError(f"Mask missing: {mask_path}")
        splits[split].append(
            {
                "image_id": rec["image_id"],
                "hair_class": rec["approved_label"],
                "img_path": img_path,
                "mask_path": mask_path,
            }
        )
    return splits


class HairSegmentationDataset(Dataset):
    """Dataset yielding normalized RGB tensor (3, H, W) and binary mask (1, H, W)."""

    def __init__(
        self,
        records: List[dict],
        img_size: int = 256,
        augment: bool = False,
        seed: int = 42,
    ):
        self.records = records
        self.img_size = img_size
        self.augment = augment
        self.rng = random.Random(seed)

    def __len__(self) -> int:
        return len(self.records)

    def _augment_pair(self, img: Image.Image, mask: Image.Image) -> Tuple[Image.Image, Image.Image]:
        # Horizontal flip (safe for hair segmentation)
        if self.rng.random() < 0.5:
            img = ImageOps.mirror(img)
            mask = ImageOps.mirror(mask)

        # Small rotation (-12 to +12 deg)
        if self.rng.random() < 0.5:
            angle = self.rng.uniform(-12.0, 12.0)
            img = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(0, 0, 0))
            mask = mask.rotate(angle, resample=Image.Resampling.NEAREST, fillcolor=0)

        # Mild brightness / contrast jitter on RGB only
        if self.rng.random() < 0.6:
            arr = np.asarray(img, dtype=np.float32)
            alpha = self.rng.uniform(0.85, 1.15)  # contrast
            beta = self.rng.uniform(-18.0, 18.0)  # brightness
            arr = np.clip(arr * alpha + beta, 0, 255).astype(np.uint8)
            img = Image.fromarray(arr)

        return img, mask

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        rec = self.records[idx]
        with Image.open(rec["img_path"]) as im_raw, Image.open(rec["mask_path"]) as mk_raw:
            im = ImageOps.exif_transpose(im_raw).convert("RGB")
            mk = mk_raw.convert("L")

            if self.augment:
                im, mk = self._augment_pair(im, mk)

            im = im.resize((self.img_size, self.img_size), Image.Resampling.BILINEAR)
            mk = mk.resize((self.img_size, self.img_size), Image.Resampling.NEAREST)

            img_np = np.asarray(im, dtype=np.float32) / 255.0
            img_np = (img_np - IMAGENET_MEAN) / IMAGENET_STD
            img_chw = np.transpose(img_np, (2, 0, 1)).astype(np.float32)

            mk_np = (np.asarray(mk, dtype=np.float32) > 127.0).astype(np.float32)[None, ...]

        return torch.from_numpy(img_chw), torch.from_numpy(mk_np)


def compute_batch_metrics(
    preds_bin: torch.Tensor, targets_bin: torch.Tensor, eps: float = 1e-6
) -> Dict[str, float]:
    """Compute pixel-wise TP, FP, FN, TN sums over a batch."""
    p = preds_bin.bool()
    t = targets_bin.bool()

    tp = float((p & t).sum().item())
    fp = float((p & ~t).sum().item())
    fn = float((~p & t).sum().item())
    tn = float((~p & ~t).sum().item())
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def summarize_confusion(counts: Dict[str, float], eps: float = 1e-6) -> Dict[str, float]:
    """Derive IoU, Dice (F1), Precision, Recall, Pixel Accuracy from TP/FP/FN/TN."""
    tp, fp, fn, tn = counts["tp"], counts["fp"], counts["fn"], counts["tn"]
    iou = (tp + eps) / (tp + fp + fn + eps)
    dice = (2.0 * tp + eps) / (2.0 * tp + fp + fn + eps)
    precision = (tp + eps) / (tp + fp + eps)
    recall = (tp + eps) / (tp + fn + eps)
    accuracy = (tp + tn + eps) / (tp + fp + fn + tn + eps)
    return {
        "iou": iou,
        "dice": dice,
        "precision": precision,
        "recall": recall,
        "pixel_accuracy": accuracy,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
    }


@torch.no_grad()
def evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
    threshold: float = 0.5,
) -> Dict[str, object]:
    """Evaluate model on a DataLoader returning loss, global & per-image mean IoU/Dice."""
    model.eval()
    total_loss = 0.0
    total_samples = 0
    global_counts = {"tp": 0.0, "fp": 0.0, "fn": 0.0, "tn": 0.0}
    per_image_ious: List[float] = []
    per_image_dices: List[float] = []

    for imgs, masks in loader:
        imgs = imgs.to(device)
        masks = masks.to(device)
        logits = model(imgs)
        loss = criterion(logits, masks)

        bs = imgs.size(0)
        total_loss += float(loss.item()) * bs
        total_samples += bs

        probs = torch.sigmoid(logits)
        preds = (probs >= threshold).float()
        targets = (masks >= 0.5).float()

        batch_counts = compute_batch_metrics(preds, targets)
        for k in global_counts:
            global_counts[k] += batch_counts[k]

        for i in range(bs):
            c_i = compute_batch_metrics(preds[i : i + 1], targets[i : i + 1])
            m_i = summarize_confusion(c_i)
            per_image_ious.append(m_i["iou"])
            per_image_dices.append(m_i["dice"])

    global_metrics = summarize_confusion(global_counts)
    return {
        "loss": total_loss / max(1, total_samples),
        "mean_iou": float(np.mean(per_image_ious)) if per_image_ious else 0.0,
        "std_iou": float(np.std(per_image_ious)) if per_image_ious else 0.0,
        "mean_dice": float(np.mean(per_image_dices)) if per_image_dices else 0.0,
        "std_dice": float(np.std(per_image_dices)) if per_image_dices else 0.0,
        "global_iou": global_metrics["iou"],
        "global_dice": global_metrics["dice"],
        "precision": global_metrics["precision"],
        "recall": global_metrics["recall"],
        "pixel_accuracy": global_metrics["pixel_accuracy"],
        "confusion": {
            "tp": global_metrics["tp"],
            "fp": global_metrics["fp"],
            "fn": global_metrics["fn"],
            "tn": global_metrics["tn"],
        },
        "per_image_ious": per_image_ious,
        "per_image_dices": per_image_dices,
    }


def export_to_onnx(model: nn.Module, onnx_path: Path, img_size: int = 256) -> None:
    """Export trained PyTorch UNet model to ONNX with dynamic batch size."""
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    model_cpu = model.to("cpu").eval()
    dummy = torch.randn(1, 3, img_size, img_size, dtype=torch.float32)

    export_kwargs = {
        "export_params": True,
        "opset_version": 17,
        "do_constant_folding": True,
        "input_names": ["input"],
        "output_names": ["logits"],
        "dynamic_axes": {"input": {0: "batch_size"}, "logits": {0: "batch_size"}},
    }
    # Pass dynamo=False if supported to ensure stable TorchScript ONNX exporter
    try:
        torch.onnx.export(model_cpu, dummy, str(onnx_path), dynamo=False, **export_kwargs)
    except TypeError:
        torch.onnx.export(model_cpu, dummy, str(onnx_path), **export_kwargs)


def benchmark_onnx_cpu(onnx_path: Path, img_size: int = 256, runs: int = 20) -> dict:
    """Verify ONNX model output and measure CPU inference latency (ms)."""
    import onnx
    import onnxruntime as ort

    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    dummy = np.random.randn(1, 3, img_size, img_size).astype(np.float32)

    # Warmup
    for _ in range(3):
        sess.run(None, {input_name: dummy})

    times_ms = []
    for _ in range(runs):
        t0 = time.perf_counter()
        out = sess.run(None, {input_name: dummy})[0]
        times_ms.append((time.perf_counter() - t0) * 1000.0)

    return {
        "output_shape": list(out.shape),
        "mean_ms": float(np.mean(times_ms)),
        "p95_ms": float(np.percentile(times_ms, 95)),
        "min_ms": float(np.min(times_ms)),
        "max_ms": float(np.max(times_ms)),
        "file_size_mb": round(onnx_path.stat().st_size / (1024 * 1024), 3),
    }


def save_qualitative_grid(
    model: nn.Module,
    records: List[dict],
    out_path: Path,
    device: torch.device,
    img_size: int = 256,
    max_samples: int = 6,
) -> None:
    """Save qualitative comparison (Input | GT Mask | Pred Mask | Overlay)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()

    # Select diverse hair classes if available
    selected = []
    seen_classes = set()
    for r in records:
        if r["hair_class"] not in seen_classes:
            selected.append(r)
            seen_classes.add(r["hair_class"])
        if len(selected) >= max_samples:
            break
    for r in records:
        if len(selected) >= max_samples:
            break
        if r not in selected:
            selected.append(r)

    rows = []
    with torch.no_grad():
        for rec in selected:
            with Image.open(rec["img_path"]) as im_raw, Image.open(rec["mask_path"]) as mk_raw:
                im = ImageOps.exif_transpose(im_raw).convert("RGB").resize((img_size, img_size), Image.Resampling.BILINEAR)
                mk = mk_raw.convert("L").resize((img_size, img_size), Image.Resampling.NEAREST)

                im_np = np.asarray(im, dtype=np.float32)
                norm = (im_np / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
                tensor = torch.from_numpy(np.transpose(norm, (2, 0, 1))[None, ...].astype(np.float32)).to(device)
                logits = model(tensor)
                prob = torch.sigmoid(logits)[0, 0].cpu().numpy()
                pred_bin = (prob >= 0.5).astype(np.float32)

                gt_bin = (np.asarray(mk, dtype=np.float32) > 127.0).astype(np.float32)
                gt_rgb = np.stack([gt_bin * 255.0] * 3, axis=-1)
                pred_rgb = np.stack([pred_bin * 255.0] * 3, axis=-1)

                green = np.array([34.0, 197.0, 94.0], dtype=np.float32)
                overlay = im_np * (1.0 - 0.45 * pred_bin[:, :, None]) + green * (0.45 * pred_bin[:, :, None])

                row = np.concatenate([im_np, gt_rgb, pred_rgb, overlay], axis=1).clip(0, 255).astype(np.uint8)
                rows.append(row)

    if rows:
        grid = np.concatenate(rows, axis=0)
        Image.fromarray(grid).save(out_path, quality=90)


def train_and_evaluate(
    manifest_path: Path = DEFAULT_MANIFEST,
    dataset_dir: Path = DEFAULT_DATASET,
    mask_dir: Path = DEFAULT_MASK_DIR,
    weights_dir: Path = DEFAULT_WEIGHTS_DIR,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    arch: str = "mobilenet_v2",
    pretrained: bool = True,
    img_size: int = 256,
    base_features: int = 32,
    epochs: int = 45,
    batch_size: int = 16,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    patience: int = 12,
    seed: int = 42,
    device_str: Optional[str] = None,
) -> dict:
    """Run complete Phase 2 UNet training, evaluation, ONNX export, and reporting."""
    set_seed(seed)

    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    splits = load_figaro_split_records(manifest_path, dataset_dir, mask_dir)
    print(
        f"Phase 2 Hair Segmentation | arch={arch} (pretrained={pretrained}) | device={device}"
        + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else "")
        + f" | split={len(splits['train'])}/{len(splits['val'])}/{len(splits['test'])}"
    )

    train_ds = HairSegmentationDataset(splits["train"], img_size=img_size, augment=True, seed=seed)
    val_ds = HairSegmentationDataset(splits["val"], img_size=img_size, augment=False, seed=seed)
    test_ds = HairSegmentationDataset(splits["test"], img_size=img_size, augment=False, seed=seed)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=(device.type == "cuda"))
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    model = build_hair_segmentation_model(
        arch=arch,
        pretrained=pretrained,
        base_features=base_features,
        out_channels=1,
    ).to(device)
    criterion = BCEDiceLoss(alpha=0.5)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs), eta_min=1e-5)

    best_val_iou = -1.0
    best_epoch = 0
    epochs_no_improve = 0
    weights_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt = weights_dir / "hair_segmentation_best.pt"
    history = []

    t_start = time.time()
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_sum = 0.0
        train_n = 0
        for imgs, masks in train_loader:
            imgs = imgs.to(device)
            masks = masks.to(device)
            optimizer.zero_grad()
            logits = model(imgs)
            loss = criterion(logits, masks)
            loss.backward()
            optimizer.step()

            bs = imgs.size(0)
            train_loss_sum += float(loss.item()) * bs
            train_n += bs

        scheduler.step()
        train_loss = train_loss_sum / max(1, train_n)

        val_res = evaluate_model(model, val_loader, criterion, device)
        history.append(
            {
                "epoch": epoch,
                "train_loss": round(train_loss, 5),
                "val_loss": round(val_res["loss"], 5),
                "val_mean_iou": round(val_res["mean_iou"], 5),
                "val_mean_dice": round(val_res["mean_dice"], 5),
                "val_global_iou": round(val_res["global_iou"], 5),
                "lr": round(optimizer.param_groups[0]["lr"], 7),
            }
        )
        print(
            f"Epoch {epoch:02d}/{epochs:02d} | train_loss={train_loss:.4f} "
            f"| val_loss={val_res['loss']:.4f} | val_mIoU={val_res['mean_iou']:.4f} "
            f"| val_mDice={val_res['mean_dice']:.4f}"
        )

        if val_res["mean_iou"] > best_val_iou:
            best_val_iou = val_res["mean_iou"]
            best_epoch = epoch
            epochs_no_improve = 0
            torch.save(model.state_dict(), best_ckpt)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"Early stopping triggered at epoch {epoch} (best val_mIoU={best_val_iou:.4f} at epoch {best_epoch})")
                break

    train_duration_s = time.time() - t_start

    # Load best checkpoint for final evaluation and ONNX export
    model.load_state_dict(torch.load(best_ckpt, map_location=device, weights_only=True))
    val_final = evaluate_model(model, val_loader, criterion, device)
    test_final = evaluate_model(model, test_loader, criterion, device)

    # Breakdown by hair class on test split
    by_class_test = {}
    for cls_name in sorted({r["hair_class"] for r in splits["test"]}):
        cls_recs = [r for r in splits["test"] if r["hair_class"] == cls_name]
        cls_ds = HairSegmentationDataset(cls_recs, img_size=img_size, augment=False, seed=seed)
        cls_loader = DataLoader(cls_ds, batch_size=batch_size, shuffle=False, num_workers=0)
        cls_res = evaluate_model(model, cls_loader, criterion, device)
        by_class_test[cls_name] = {
            "count": len(cls_recs),
            "mean_iou": round(cls_res["mean_iou"], 4),
            "mean_dice": round(cls_res["mean_dice"], 4),
            "global_iou": round(cls_res["global_iou"], 4),
        }

    # Save qualitative preview grid
    save_qualitative_grid(
        model,
        splits["test"],
        figures_dir / "segmentation_test_grid.jpg",
        device=device,
        img_size=img_size,
    )

    # Export ONNX and benchmark CPU inference
    onnx_path = weights_dir / "hair_segmentation.onnx"
    export_to_onnx(model, onnx_path, img_size=img_size)
    onnx_bench = benchmark_onnx_cpu(onnx_path, img_size=img_size, runs=20)

    # Phase 2 Gate check
    gate_passed = (
        val_final["mean_iou"] >= 0.75
        and val_final["mean_dice"] >= 0.85
        and onnx_bench["mean_ms"] < 200.0
    )

    # Strip large per-image arrays from JSON summary
    for d in (val_final, test_final):
        d.pop("per_image_ious", None)
        d.pop("per_image_dices", None)

    report = {
        "phase": "2_hair_segmentation",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "device_used": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "architecture": {
            "name": arch,
            "pretrained": pretrained,
            "base_features": base_features,
            "img_size": img_size,
            "bilinear": True,
            "loss": "0.5 * BCEWithLogits + 0.5 * SoftDice",
            "param_count": sum(p.numel() for p in model.parameters()),
        },
        "dataset": {
            "source": "figaro1k (curated_manifest.json)",
            "train_count": len(splits["train"]),
            "val_count": len(splits["val"]),
            "test_count": len(splits["test"]),
        },
        "training": {
            "epochs_configured": epochs,
            "epochs_run": len(history),
            "best_epoch": best_epoch,
            "duration_seconds": round(train_duration_s, 2),
            "batch_size": batch_size,
            "lr": lr,
        },
        "gate": {
            "status": "LULUS" if gate_passed else "BELUM_LULUS",
            "criteria": {
                "val_mean_iou_ge": 0.75,
                "val_mean_dice_ge": 0.85,
                "cpu_latency_lt_ms": 200.0,
            },
            "actual": {
                "val_mean_iou": round(val_final["mean_iou"], 4),
                "val_mean_dice": round(val_final["mean_dice"], 4),
                "cpu_latency_mean_ms": round(onnx_bench["mean_ms"], 2),
            },
        },
        "val_metrics": val_final,
        "test_metrics": test_final,
        "test_by_hair_class": by_class_test,
        "onnx": {
            "path": str(onnx_path.relative_to(HERE.parents[3]).as_posix()),
            **onnx_bench,
        },
        "history": history,
    }

    eval_path = reports_dir / "segmentation_eval.json"
    eval_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved evaluation report: {eval_path}")
    print(f"Saved ONNX model: {onnx_path} ({onnx_bench['file_size_mb']} MB, {onnx_bench['mean_ms']:.2f} ms CPU)")
    print(f"Phase 2 Gate Status: {report['gate']['status']}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Train and evaluate Phase 2 UNet hair segmentation model."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--mask-dir", type=Path, default=DEFAULT_MASK_DIR)
    parser.add_argument("--weights-dir", type=Path, default=DEFAULT_WEIGHTS_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument(
        "--arch",
        type=str,
        default="mobilenet_v2",
        choices=["mobilenet_v2", "resnet34", "scratch"],
        help="UNet architecture/encoder (default: mobilenet_v2)",
    )
    parser.add_argument(
        "--no-pretrained",
        action="store_true",
        help="Disable ImageNet pretrained encoder weights",
    )
    parser.add_argument("--img-size", type=int, default=256)
    parser.add_argument("--base-features", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=45)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", type=str, default=None, help="Force 'cuda' or 'cpu'")
    args = parser.parse_args()

    train_and_evaluate(
        manifest_path=args.manifest,
        dataset_dir=args.dataset_dir,
        mask_dir=args.mask_dir,
        weights_dir=args.weights_dir,
        reports_dir=args.reports_dir,
        figures_dir=args.figures_dir,
        arch=args.arch,
        pretrained=not args.no_pretrained,
        img_size=args.img_size,
        base_features=args.base_features,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        seed=args.seed,
        device_str=args.device,
    )


if __name__ == "__main__":
    main()
