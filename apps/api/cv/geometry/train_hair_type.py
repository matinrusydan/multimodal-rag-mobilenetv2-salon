"""Phase 4: Stage 1 Hair Type CNN Training & Evaluation Pipeline.

Trains and evaluates a Stage 1 Hair Type classifier on the curated Phase 1 dataset
split (`curated_manifest.json`) across the 4 canonical classes:
["lurus", "bergelombang", "keriting", "sangat-keriting"].

Supports pretrained ImageNet backbones (EfficientNetV2-S or MobileNetV2),
inverse-frequency class weighting, cosine annealing LR scheduling, early stopping
on validation Macro-F1, evaluation on locked test split (without tuning on test),
subgroup performance analysis (by cohort), ONNX export, and CPU inference benchmarking.
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

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from hair_type_model import HAIR_TYPE_CLASSES, build_hair_type_model, export_hair_type_onnx

DEFAULT_MANIFEST = HERE / "reports" / "phase1" / "curated_manifest.json"
DEFAULT_DATASET = HERE.parent / "dataset"
DEFAULT_WEIGHTS_DIR = HERE / "weights"
DEFAULT_REPORTS_DIR = HERE / "reports"
DEFAULT_FIGURES_DIR = DEFAULT_REPORTS_DIR / "figures"

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
CLASS_TO_IDX = {c: i for i, c in enumerate(HAIR_TYPE_CLASSES)}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def load_hair_type_split_records(
    manifest_path: Path,
    dataset_dir: Path,
) -> Dict[str, List[dict]]:
    """Load curated image records grouped by Phase 1 split (train/val/test)."""
    if not manifest_path.exists():
        raise FileNotFoundError(f"Curated manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    splits: Dict[str, List[dict]] = {"train": [], "val": [], "test": []}
    for rec in manifest.get("records", []):
        split = rec.get("split")
        if split not in splits:
            continue
        label = rec.get("approved_label")
        if label not in CLASS_TO_IDX:
            raise ValueError(f"Unknown approved label: {label} in {rec['image_id']}")
        img_path = dataset_dir / rec["image_id"]
        if not img_path.is_file():
            raise FileNotFoundError(f"Image missing: {img_path}")

        splits[split].append(
            {
                "image_id": rec["image_id"],
                "cohort": rec.get("cohort", "unknown"),
                "hair_class": label,
                "class_idx": CLASS_TO_IDX[label],
                "img_path": img_path,
                "width": rec.get("width"),
                "height": rec.get("height"),
            }
        )
    return splits


class HairTypeDataset(Dataset):
    """Dataset yielding normalized RGB tensor (3, H, W) and class index (int)."""

    def __init__(
        self,
        records: List[dict],
        img_size: int = 224,
        resize_side: int = 256,
        augment: bool = False,
        seed: int = 42,
    ):
        self.records = records
        self.img_size = img_size
        self.resize_side = resize_side
        self.augment = augment
        self.seed = seed
        self.epoch = 0

    def set_epoch(self, epoch: int) -> None:
        self.epoch = epoch

    def __len__(self) -> int:
        return len(self.records)

    def _transform(self, im: Image.Image, idx: int) -> torch.Tensor:
        w, h = im.size
        scale = self.resize_side / min(h, w)
        rw = max(self.img_size, round(w * scale))
        rh = max(self.img_size, round(h * scale))

        if self.augment:
            rng = random.Random(self.seed + self.epoch * 100003 + idx * 7919)
            if rng.random() < 0.5:
                im = ImageOps.mirror(im)
            if rng.random() < 0.5:
                angle = rng.uniform(-10.0, 10.0)
                im = im.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(0, 0, 0))

            resized = im.resize((rw, rh), Image.Resampling.BILINEAR)
            max_x = max(0, rw - self.img_size)
            max_y = max(0, rh - self.img_size)
            left = rng.randint(0, max_x) if max_x > 0 else 0
            top = rng.randint(0, max_y) if max_y > 0 else 0
            cropped = resized.crop((left, top, left + self.img_size, top + self.img_size))

            if rng.random() < 0.5:
                arr = np.asarray(cropped, dtype=np.float32)
                alpha = rng.uniform(0.85, 1.15)
                beta = rng.uniform(-15.0, 15.0)
                arr = np.clip(arr * alpha + beta, 0.0, 255.0).astype(np.uint8)
                cropped = Image.fromarray(arr)
        else:
            resized = im.resize((rw, rh), Image.Resampling.BILINEAR)
            left = (rw - self.img_size) // 2
            top = (rh - self.img_size) // 2
            cropped = resized.crop((left, top, left + self.img_size, top + self.img_size))

        arr = np.asarray(cropped, dtype=np.float32) / 255.0
        arr = (arr - IMAGENET_MEAN) / IMAGENET_STD
        tensor = torch.from_numpy(np.transpose(arr, (2, 0, 1)).astype(np.float32))
        return tensor

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        rec = self.records[idx]
        with Image.open(rec["img_path"]) as raw_img:
            im = ImageOps.exif_transpose(raw_img).convert("RGB")
            tensor = self._transform(im, idx)
        return tensor, rec["class_idx"]


def compute_classification_metrics(
    probs: np.ndarray,
    targets: np.ndarray,
    class_names: List[str] = HAIR_TYPE_CLASSES,
    n_bins: int = 10,
) -> dict:
    """Derive Accuracy, Macro-F1, per-class F1, Confusion Matrix, and ECE."""
    num_classes = len(class_names)
    total = len(targets)
    if total == 0:
        return {
            "accuracy": 0.0,
            "macro_f1": 0.0,
            "weighted_f1": 0.0,
            "ece": 0.0,
            "per_class": {},
            "confusion_matrix": [],
        }

    preds = np.argmax(probs, axis=1)
    acc = float(np.mean(preds == targets))

    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(targets, preds):
        cm[t, p] += 1

    per_class = {}
    f1s = []
    supports = []
    for c in range(num_classes):
        tp = int(cm[c, c])
        fp = int(cm[:, c].sum() - tp)
        fn = int(cm[c, :].sum() - tp)
        support = int(cm[c, :].sum())
        supports.append(support)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)

        per_class[class_names[c]] = {
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "support": support,
        }

    macro_f1 = float(np.mean(f1s))
    total_supp = sum(supports)
    weighted_f1 = (
        float(sum(f * s for f, s in zip(f1s, supports)) / total_supp)
        if total_supp > 0
        else 0.0
    )

    # Multi-class Expected Calibration Error (ECE)
    confidences = np.max(probs, axis=1)
    accuracies = (preds == targets)
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        low, high = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (confidences >= low) & (
            confidences <= high if i == n_bins - 1 else confidences < high
        )
        prop = np.mean(in_bin)
        if prop > 0:
            avg_acc = np.mean(accuracies[in_bin])
            avg_conf = np.mean(confidences[in_bin])
            ece += np.abs(avg_conf - avg_acc) * prop

    return {
        "accuracy": round(acc, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(weighted_f1, 4),
        "ece": round(float(ece), 4),
        "per_class": per_class,
        "confusion_matrix": cm.tolist(),
    }


@torch.no_grad()
def evaluate_model(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict:
    """Evaluate model on a DataLoader returning loss and full classification metrics."""
    model.eval()
    total_loss = 0.0
    total_samples = 0
    all_probs = []
    all_targets = []

    for imgs, targets in loader:
        imgs = imgs.to(device)
        targets = targets.to(device)
        logits = model(imgs)
        loss = criterion(logits, targets)

        bs = imgs.size(0)
        total_loss += float(loss.item()) * bs
        total_samples += bs

        probs = torch.softmax(logits, dim=1).cpu().numpy()
        all_probs.append(probs)
        all_targets.append(targets.cpu().numpy())

    probs_arr = np.concatenate(all_probs, axis=0) if all_probs else np.zeros((0, len(HAIR_TYPE_CLASSES)))
    targets_arr = np.concatenate(all_targets, axis=0) if all_targets else np.zeros(0, dtype=int)

    metrics = compute_classification_metrics(probs_arr, targets_arr, HAIR_TYPE_CLASSES)
    metrics["loss"] = round(total_loss / max(1, total_samples), 5)
    return metrics


def benchmark_onnx_cpu(onnx_path: Path, img_size: int = 224, runs: int = 20) -> dict:
    """Measure ONNX CPU inference latency (ms)."""
    import onnx
    import onnxruntime as ort

    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name
    dummy = np.random.randn(1, 3, img_size, img_size).astype(np.float32)

    for _ in range(3):
        sess.run(None, {input_name: dummy})

    times_ms = []
    for _ in range(runs):
        t0 = time.perf_counter()
        out = sess.run(None, {input_name: dummy})[0]
        times_ms.append((time.perf_counter() - t0) * 1000.0)

    return {
        "output_shape": list(out.shape),
        "mean_ms": round(float(np.mean(times_ms)), 2),
        "p95_ms": round(float(np.percentile(times_ms, 95)), 2),
        "min_ms": round(float(np.min(times_ms)), 2),
        "max_ms": round(float(np.max(times_ms)), 2),
        "file_size_mb": round(onnx_path.stat().st_size / (1024 * 1024), 3),
    }


def save_confusion_matrix_plot(cm: list[list[int]], out_path: Path, title: str = "Hair Type Confusion Matrix") -> None:
    """Render and save confusion matrix heatmap."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        cm_arr = np.array(cm)
        fig, ax = plt.subplots(figsize=(6, 5))
        cax = ax.matshow(cm_arr, cmap=plt.cm.Blues, alpha=0.8)

        for i in range(cm_arr.shape[0]):
            for j in range(cm_arr.shape[1]):
                ax.text(x=j, y=i, s=str(cm_arr[i, j]), va="center", ha="center", fontsize=11)

        fig.colorbar(cax)
        ax.set_xticks(range(len(HAIR_TYPE_CLASSES)))
        ax.set_yticks(range(len(HAIR_TYPE_CLASSES)))
        ax.set_xticklabels(HAIR_TYPE_CLASSES, rotation=30, ha="left")
        ax.set_yticklabels(HAIR_TYPE_CLASSES)
        ax.set_xlabel("Predicted Label")
        ax.set_ylabel("True Label")
        ax.set_title(title, pad=15)
        plt.tight_layout()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_path, dpi=150)
        plt.close(fig)
    except Exception as exc:
        print(f"Warning: could not save confusion matrix plot: {exc}")


def train_and_evaluate(
    manifest_path: Path = DEFAULT_MANIFEST,
    dataset_dir: Path = DEFAULT_DATASET,
    weights_dir: Path = DEFAULT_WEIGHTS_DIR,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    figures_dir: Path = DEFAULT_FIGURES_DIR,
    arch: str = "efficientnet_v2_s",
    pretrained: bool = True,
    img_size: int = 224,
    epochs: int = 35,
    batch_size: int = 16,
    lr: float = 3e-4,
    weight_decay: float = 1e-4,
    patience: int = 10,
    seed: int = 42,
    use_class_weights: bool = True,
    device_str: Optional[str] = None,
    skip_test: bool = False,
    eval_ckpt: Optional[Path] = None,
    report_name: str = "hair_type_eval.json",
    onnx_name: str = "hair_type.onnx",
) -> dict:
    """Run Stage 1 Hair Type training, validation, locked test evaluation, and ONNX export."""
    set_seed(seed)

    if device_str:
        device = torch.device(device_str)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    splits = load_hair_type_split_records(manifest_path, dataset_dir)
    print(
        f"Phase 4 Hair Type Classifier | arch={arch} (pretrained={pretrained}) | device={device}"
        + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else "")
        + f" | split={len(splits['train'])}/{len(splits['val'])}/{len(splits['test'])}"
    )

    train_ds = HairTypeDataset(splits["train"], img_size=img_size, augment=True, seed=seed)
    val_ds = HairTypeDataset(splits["val"], img_size=img_size, augment=False, seed=seed)
    test_ds = HairTypeDataset(splits["test"], img_size=img_size, augment=False, seed=seed)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=(device.type == "cuda"))
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # Compute inverse class frequency weights
    if use_class_weights:
        class_counts = np.bincount([r["class_idx"] for r in splits["train"]], minlength=len(HAIR_TYPE_CLASSES))
        total_train = len(splits["train"])
        weights_arr = total_train / (len(HAIR_TYPE_CLASSES) * np.maximum(class_counts, 1).astype(np.float32))
        class_weights = torch.from_numpy(weights_arr).float().to(device)
        print(f"Class counts: {class_counts.tolist()} | Class weights: {[round(w, 3) for w in weights_arr.tolist()]}")
        criterion = nn.CrossEntropyLoss(weight=class_weights)
    else:
        criterion = nn.CrossEntropyLoss()

    model = build_hair_type_model(arch=arch, pretrained=pretrained, num_classes=len(HAIR_TYPE_CLASSES)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs), eta_min=1e-5)

    best_val_macro_f1 = -1.0
    best_epoch = 0
    epochs_no_improve = 0
    weights_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    best_ckpt = weights_dir / f"hair_type_{arch}_best.pt"
    history = []

    if eval_ckpt is not None:
        best_ckpt = Path(eval_ckpt)
        if not best_ckpt.exists():
            raise FileNotFoundError(f"Checkpoint for evaluation not found: {best_ckpt}")
        print(f"Loading pre-trained checkpoint for evaluation: {best_ckpt}")
        train_duration_s = 0.0
        history_file = reports_dir / f"val_{arch}.json"
        if history_file.exists():
            try:
                prior_data = json.loads(history_file.read_text(encoding="utf-8"))
                history = prior_data.get("history", [])
                train_duration_s = prior_data.get("training", {}).get("duration_seconds", 0.0)
                best_epoch = prior_data.get("training", {}).get("best_epoch", 0)
            except Exception:
                pass
    else:
        t_start = time.time()
        for epoch in range(1, epochs + 1):
            train_ds.set_epoch(epoch)
            model.train()
            train_loss_sum = 0.0
            train_n = 0
            for imgs, targets in train_loader:
                imgs, targets = imgs.to(device), targets.to(device)
                optimizer.zero_grad()
                logits = model(imgs)
                loss = criterion(logits, targets)
                loss.backward()
                optimizer.step()

                bs = imgs.size(0)
                train_loss_sum += float(loss.item()) * bs
                train_n += bs

            scheduler.step()
            train_loss = train_loss_sum / max(1, train_n)

            val_metrics = evaluate_model(model, val_loader, criterion, device)
            history.append(
                {
                    "epoch": epoch,
                    "train_loss": round(train_loss, 5),
                    "val_loss": val_metrics["loss"],
                    "val_accuracy": val_metrics["accuracy"],
                    "val_macro_f1": val_metrics["macro_f1"],
                    "val_ece": val_metrics["ece"],
                    "lr": round(optimizer.param_groups[0]["lr"], 7),
                }
            )
            print(
                f"Epoch {epoch:02d}/{epochs:02d} | train_loss={train_loss:.4f} "
                f"| val_loss={val_metrics['loss']:.4f} | val_acc={val_metrics['accuracy']:.4f} "
                f"| val_mF1={val_metrics['macro_f1']:.4f} | ECE={val_metrics['ece']:.4f}"
            )

            if val_metrics["macro_f1"] > best_val_macro_f1:
                best_val_macro_f1 = val_metrics["macro_f1"]
                best_epoch = epoch
                epochs_no_improve = 0
                torch.save(model.state_dict(), best_ckpt)
            else:
                epochs_no_improve += 1
                if epochs_no_improve >= patience:
                    print(f"Early stopping triggered at epoch {epoch} (best val_mF1={best_val_macro_f1:.4f} at epoch {best_epoch})")
                    break

        train_duration_s = time.time() - t_start

    # Load best checkpoint for final evaluation and ONNX export
    model.load_state_dict(torch.load(best_ckpt, map_location=device, weights_only=True))
    val_final = evaluate_model(model, val_loader, criterion, device)

    # Subgroup breakdown on validation
    val_by_cohort = {}
    for cohort in sorted({r["cohort"] for r in splits["val"]}):
        c_recs = [r for r in splits["val"] if r["cohort"] == cohort]
        c_ds = HairTypeDataset(c_recs, img_size=img_size, augment=False, seed=seed)
        c_loader = DataLoader(c_ds, batch_size=batch_size, shuffle=False, num_workers=0)
        c_res = evaluate_model(model, c_loader, criterion, device)
        val_by_cohort[cohort] = {
            "count": len(c_recs),
            "accuracy": c_res["accuracy"],
            "macro_f1": c_res["macro_f1"],
        }

    # Evaluate on locked test split if requested
    if not skip_test:
        test_final = evaluate_model(model, test_loader, criterion, device)
        test_by_cohort = {}
        for cohort in sorted({r["cohort"] for r in splits["test"]}):
            c_recs = [r for r in splits["test"] if r["cohort"] == cohort]
            c_ds = HairTypeDataset(c_recs, img_size=img_size, augment=False, seed=seed)
            c_loader = DataLoader(c_ds, batch_size=batch_size, shuffle=False, num_workers=0)
            c_res = evaluate_model(model, c_loader, criterion, device)
            test_by_cohort[cohort] = {
                "count": len(c_recs),
                "accuracy": c_res["accuracy"],
                "macro_f1": c_res["macro_f1"],
            }
        save_confusion_matrix_plot(
            test_final["confusion_matrix"],
            figures_dir / f"hair_type_{arch}_test_confusion.png",
            title=f"Hair Type ({arch}) Locked Test Confusion Matrix",
        )
    else:
        test_final = None
        test_by_cohort = None

    # Export ONNX and benchmark CPU
    onnx_path = weights_dir / onnx_name
    export_hair_type_onnx(model, onnx_path, img_size=img_size)
    onnx_bench = benchmark_onnx_cpu(onnx_path, img_size=img_size, runs=20)

    # Gate check (Roadmap 10.5: Hair type accuracy >= 0.85)
    target_accuracy = 0.85
    gate_passed = val_final["accuracy"] >= target_accuracy

    report = {
        "phase": "4_hair_type_classification",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "device_used": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "architecture": {
            "name": arch,
            "pretrained": pretrained,
            "img_size": img_size,
            "param_count": sum(p.numel() for p in model.parameters()),
            "classes": HAIR_TYPE_CLASSES,
        },
        "dataset": {
            "manifest": str(manifest_path.relative_to(HERE.parents[3]).as_posix()),
            "train_count": len(splits["train"]),
            "val_count": len(splits["val"]),
            "test_count": len(splits["test"]),
            "class_distribution_train": {c: int(np.bincount([r['class_idx'] for r in splits['train']], minlength=len(HAIR_TYPE_CLASSES))[i]) for i, c in enumerate(HAIR_TYPE_CLASSES)},
        },
        "training": {
            "epochs_configured": epochs,
            "epochs_run": len(history),
            "best_epoch": best_epoch,
            "duration_seconds": round(train_duration_s, 2),
            "batch_size": batch_size,
            "lr": lr,
            "class_weighted_loss": use_class_weights,
        },
        "gate": {
            "status": "LULUS" if gate_passed else "BELUM_LULUS",
            "criterion": "val_accuracy >= 0.85",
            "actual_val_accuracy": val_final["accuracy"],
            "actual_val_macro_f1": val_final["macro_f1"],
        },
        "val_metrics": val_final,
        "val_by_cohort": val_by_cohort,
        "test_metrics": test_final,
        "test_by_cohort": test_by_cohort,
        "onnx": {
            "path": str(onnx_path.relative_to(HERE.parents[3]).as_posix()),
            **onnx_bench,
        },
        "history": history,
    }

    eval_path = reports_dir / report_name
    eval_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved evaluation report: {eval_path}")
    print(f"Saved ONNX model: {onnx_path} ({onnx_bench['file_size_mb']} MB, {onnx_bench['mean_ms']:.2f} ms CPU)")
    print(f"Phase 4 Hair Type Gate Status: {report['gate']['status']} (val_acc={val_final['accuracy']:.4f}, val_mF1={val_final['macro_f1']:.4f})")

    return report


def main():
    parser = argparse.ArgumentParser(description="Train and evaluate Phase 4 Hair Type CNN classifier.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--weights-dir", type=Path, default=DEFAULT_WEIGHTS_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument(
        "--arch",
        type=str,
        default="efficientnet_v2_s",
        choices=["efficientnet_v2_s", "mobilenet_v2"],
        help="Classifier backbone (default: efficientnet_v2_s)",
    )
    parser.add_argument("--no-pretrained", action="store_true", help="Disable ImageNet pretrained weights")
    parser.add_argument("--img-size", type=int, default=224)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-class-weights", action="store_true", help="Disable inverse frequency loss weighting")
    parser.add_argument("--skip-test", action="store_true", help="Evaluate only on train and val (do not touch test)")
    parser.add_argument("--eval-ckpt", type=Path, default=None, help="Skip training and evaluate an existing checkpoint")
    parser.add_argument("--report-name", type=str, default="hair_type_eval.json", help="Report filename in reports-dir")
    parser.add_argument("--onnx-name", type=str, default="hair_type.onnx", help="ONNX filename in weights-dir")
    parser.add_argument("--device", type=str, default=None, help="Force 'cuda' or 'cpu'")
    args = parser.parse_args()

    train_and_evaluate(
        manifest_path=args.manifest,
        dataset_dir=args.dataset_dir,
        weights_dir=args.weights_dir,
        reports_dir=args.reports_dir,
        figures_dir=args.figures_dir,
        arch=args.arch,
        pretrained=not args.no_pretrained,
        img_size=args.img_size,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        patience=args.patience,
        seed=args.seed,
        use_class_weights=not args.no_class_weights,
        device_str=args.device,
        skip_test=args.skip_test,
        eval_ckpt=args.eval_ckpt,
        report_name=args.report_name,
        onnx_name=args.onnx_name,
    )


if __name__ == "__main__":
    main()
