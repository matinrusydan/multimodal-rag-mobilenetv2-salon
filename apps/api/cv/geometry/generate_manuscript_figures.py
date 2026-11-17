"""Generate high-resolution publication figures for JMASIF manuscript.

Outputs:
1. fig1_system_architecture.png: End-to-end multi-tier system architecture
2. fig2_training_dynamics.png: Phase 2 UNet & Phase 4 EfficientNetV2-S training dynamics
3. fig3_evaluation_and_calibration.png: Locked test confusion matrix, cohort analysis, and calibration
4. fig4_geometric_grounding_schema.png: Anthropometric head-unit geometry and dual-mode anchoring schema
"""
from __future__ import annotations

import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.path import Path as MplPath
import numpy as np
from scipy.interpolate import splprep, splev
import fitz  # PyMuPDF

# Style configuration for IEEE/JMASIF single-column / full-width clarity
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif"],
    "font.size": 10,
    "axes.labelsize": 10,
    "axes.titlesize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 8.5,
    "figure.titlesize": 12,
    "mathtext.fontset": "stix",
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
})

HERE = Path(__file__).resolve().parent
REPORTS_DIR = HERE / "reports"
OUTPUT_DIR = REPORTS_DIR / "figures" / "manuscript"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_system_architecture():
    """Figure 1: End-to-End System Architecture.
    
    Academic, minimalist styling with sharp borders, neutral slate palette,
    and clear non-overlapping connectors.
    """
    fig, ax = plt.subplots(figsize=(11.0, 7.2))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Clean academic palette (slate / neutral)
    c_tier_bg = "#F8FAFC"
    c_tier_border = "#94A3B8"
    c_comp_border = "#334155"
    c_comp_bg = "#FFFFFF"
    c_arrow = "#1E293B"

    # Tier containers (Sharp rectangular boxes)
    tiers = [
        ("Client Tier (Next.js 16 App Router)", 0.03, 0.81, 0.94, 0.16, c_tier_bg, "--"),
        ("API Gateway & Security Tier (Node.js / Express)", 0.03, 0.58, 0.94, 0.18, c_tier_bg, "--"),
        ("Computer Vision Subsystem (FastAPI + ONNX)", 0.03, 0.25, 0.44, 0.28, "#FFFFFF", "-"),
        ("RAG Consultation Subsystem (FastAPI + Gemini)", 0.53, 0.25, 0.44, 0.28, "#FFFFFF", "-"),
        ("Persistence & Multi-Source Knowledge Corpus Tier", 0.03, 0.03, 0.94, 0.18, c_tier_bg, "--"),
    ]

    for title, x, y, w, h, bg, ls in tiers:
        rect = patches.Rectangle((x, y), w, h, facecolor=bg, edgecolor=c_tier_border,
                                 linewidth=1.0, linestyle=ls, zorder=1)
        ax.add_patch(rect)

    # Subsystem dedicated header bands (clean background so arrows never hit text)
    # CV Header band (title right-aligned so left side at x=0.145 is clear for arrow)
    cv_header = patches.Rectangle((0.03, 0.495), 0.44, 0.035, facecolor="#F1F5F9",
                                  edgecolor=c_tier_border, linewidth=0.8, zorder=2)
    ax.add_patch(cv_header)
    ax.text(0.455, 0.512, "Computer Vision Subsystem (FastAPI + ONNX)", fontsize=8.5,
            fontweight="bold", color="#0F172A", ha="right", va="center", zorder=3)

    # RAG Header band (title left-aligned so right side at x=0.855 is clear for arrow)
    rag_header = patches.Rectangle((0.53, 0.495), 0.44, 0.035, facecolor="#F1F5F9",
                                   edgecolor=c_tier_border, linewidth=0.8, zorder=2)
    ax.add_patch(rag_header)
    ax.text(0.545, 0.512, "RAG Consultation Subsystem (FastAPI + Gemini)", fontsize=8.5,
            fontweight="bold", color="#0F172A", ha="left", va="center", zorder=3)

    # Outer Tier titles
    ax.text(0.045, 0.950, "Client Tier (Next.js 16 App Router)", fontsize=8.8,
            fontweight="bold", color="#0F172A", ha="left", va="center", zorder=3)
    ax.text(0.045, 0.742, "API Gateway Tier (Node.js / Express)", fontsize=8.8,
            fontweight="bold", color="#0F172A", ha="left", va="center", zorder=3)
    ax.text(0.045, 0.192, "Persistence & Multi-Source Knowledge Corpus Tier", fontsize=8.8,
            fontweight="bold", color="#0F172A", ha="left", va="center", zorder=3)

    # Component box helper (crisp sharp rectangle)
    def draw_box(x, y, w, h, title, subtitle=""):
        b = patches.Rectangle((x, y), w, h, facecolor=c_comp_bg, edgecolor=c_comp_border,
                              linewidth=1.0, zorder=4)
        ax.add_patch(b)
        cy = y + h / 2.0
        if subtitle:
            ax.text(x + w / 2.0, cy + 0.013, title, ha="center", va="center",
                    fontsize=8.2, fontweight="bold", color="#0F172A", zorder=5)
            ax.text(x + w / 2.0, cy - 0.015, subtitle, ha="center", va="center",
                    fontsize=6.8, color="#475569", zorder=5)
        else:
            ax.text(x + w / 2.0, cy, title, ha="center", va="center",
                    fontsize=8.0, fontweight="bold", color="#0F172A", zorder=5)

    # Client components (x centers: 0.19, 0.50, 0.81)
    draw_box(0.06, 0.83, 0.26, 0.08, "Photo Capture / Upload", "Back-View Hair Image")
    draw_box(0.37, 0.83, 0.26, 0.08, "Consultation Chat Interface", "Streaming Dialog & Context")
    draw_box(0.68, 0.83, 0.26, 0.08, "Service Booking & Catalog", "Transparent Pricing & Cart")

    # Gateway components (x centers: 0.19, 0.50, 0.81)
    draw_box(0.06, 0.60, 0.26, 0.09, "Multer Multipart Handler", "Memory Stream Forwarding")
    draw_box(0.37, 0.60, 0.26, 0.09, "RBAC Security Enforcer", "Route & Permission Shield")
    draw_box(0.68, 0.60, 0.26, 0.09, "Reverse Proxy / Router", "FastAPI Brain Dispatcher")

    # Vision Subsystem components (x: 0.05 to 0.45)
    draw_box(0.05, 0.38, 0.19, 0.08, "Stage 1: Hair Type", "EfficientNetV2-S (3-Cls)")
    draw_box(0.26, 0.38, 0.19, 0.08, "Stage 2: UNet Mask", "MobileNetV2 (256x256)")
    draw_box(0.05, 0.27, 0.19, 0.08, "Garment LRASPP", "Clothing Silhouette Mask")
    draw_box(0.26, 0.27, 0.19, 0.08, "Head-Unit Engine", "Relative Length & Volume")

    # RAG Subsystem components (x: 0.55 to 0.95)
    draw_box(0.55, 0.38, 0.19, 0.08, "BM25 Balanced Retriever", "Cross-Source Recall")
    draw_box(0.76, 0.38, 0.19, 0.08, "source_scoped_v2 Filter", "Condition-Safe Comp.")
    draw_box(0.55, 0.27, 0.19, 0.08, "Ambiguity Guardrail", "Clarification Protocol")
    draw_box(0.76, 0.27, 0.19, 0.08, "Gemini 2.5 LLM", "Grounded Consultation")

    # Data Tier components (x centers: 0.19, 0.50, 0.81)
    draw_box(0.06, 0.05, 0.26, 0.09, "PostgreSQL Relational DB", "Salon Services, Stylists, Bookings")
    draw_box(0.37, 0.05, 0.26, 0.09, "Curated Knowledge Base", "Clinical Scalp Protocols & Care Rules")
    draw_box(0.68, 0.05, 0.26, 0.09, "ONNX Runtime Cache", "Hair Type, UNet, Pose Models")

    # Clean directional connectors (Zero crossing of text)
    arrow_kw = dict(arrowstyle="->", color=c_arrow, lw=1.2, shrinkA=3, shrinkB=3)

    # 1. Client -> Gateway (Direct vertical links, aligned with box centers and clear of tier title)
    ax.annotate("", xy=(0.29, 0.69), xytext=(0.29, 0.83), arrowprops=arrow_kw)
    ax.annotate("", xy=(0.50, 0.69), xytext=(0.50, 0.83), arrowprops=arrow_kw)
    ax.annotate("", xy=(0.81, 0.83), xytext=(0.81, 0.69), arrowprops=arrow_kw)

    # 2. Gateway -> Vision (Vertical link from Multer to Stage 1 at x=0.145, passing through clear header gap)
    ax.annotate("", xy=(0.145, 0.46), xytext=(0.145, 0.60), arrowprops=arrow_kw)

    # 3. Gateway -> RAG (Vertical link from Reverse Proxy to Filter at x=0.855, passing through clear header gap)
    ax.annotate("", xy=(0.855, 0.46), xytext=(0.855, 0.60), arrowprops=arrow_kw)

    # 4. RAG -> Gateway (Vertical return link from Gemini to Reverse Proxy at x=0.78)
    ax.annotate("", xy=(0.78, 0.60), xytext=(0.78, 0.46), arrowprops=arrow_kw)

    # 5. Vision -> RAG horizontal bridge (clean gap 0.45..0.55)
    ax.annotate("", xy=(0.55, 0.42), xytext=(0.45, 0.42),
                arrowprops=dict(arrowstyle="->", color="#1E3A8A", lw=1.5, shrinkA=2, shrinkB=2))
    ax.text(0.50, 0.435, "CV Profile", ha="center", va="bottom", fontsize=7.5,
            fontweight="bold", color="#1E3A8A")

    plt.tight_layout()
    out_path = OUTPUT_DIR / "fig1_system_architecture.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


def plot_training_dynamics():
    """Figure 2: Unsmoothed histories, laid out at the 6.6-inch insertion width."""
    seg = json.loads((REPORTS_DIR / "segmentation_eval.json").read_text(encoding="utf-8"))
    ht_path = HERE / "experiments" / "partner-20261114-threeclass-corrected-seed42" / "reports" / "hair_type_eval.json"
    if not ht_path.exists():
        ht_path = REPORTS_DIR / "hair_type_eval.json"
    ht = json.loads(ht_path.read_text(encoding="utf-8"))

    # Local style keeps the other manuscript figures unchanged.
    style = {"font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9.5,
             "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
             "text.color": "#252525", "axes.labelcolor": "#252525",
             "savefig.bbox": None}
    with plt.rc_context(style):
        fig, axes = plt.subplots(2, 2, figsize=(6.6, 5.4))
        fig.subplots_adjust(left=0.10, right=0.98, bottom=0.12, top=0.86,
                            wspace=0.34, hspace=0.88)
        blue, rust = "#356581", "#A65E3B"
        runs = [(seg, "MobileNetV2-UNet", "BCE + Dice loss",
                 ("val_mean_iou", "val_mean_dice"), ("Mean IoU", "Mean Dice")),
                (ht, "EfficientNetV2-S", "Weighted CE loss",
                 ("val_accuracy", "val_macro_f1"), ("Accuracy", "Macro-F1"))]
        for row, (run, model, loss_label, metric_keys, metric_labels) in enumerate(runs):
            history = run["history"]
            epochs = [h["epoch"] for h in history]
            best = run["training"]["best_epoch"]
            loss_ax, metric_ax = axes[row]
            for key, label, color, ls in [("train_loss", "Training", blue, "-"),
                                           ("val_loss", "Validation", rust, "--")]:
                loss_ax.plot(epochs, [h[key] for h in history], label=label,
                             color=color, lw=1.3, linestyle=ls)
            loss_ax.set_ylabel(loss_label)
            loss_ax.set_ylim(0, max(h[k] for h in history
                                    for k in ("train_loss", "val_loss")) * 1.12)
            for key, label, color, ls in zip(metric_keys, metric_labels,
                                              (blue, rust), ("-", "--")):
                metric_ax.plot(epochs, [h[key] for h in history], label=label,
                               color=color, lw=1.3, linestyle=ls)
            metric_ax.set_ylabel("Validation score")
            metric_ax.set_ylim(0.65, 1.01)
            metric_ax.set_yticks([0.7, 0.8, 0.9, 1.0])
            for col, ax in enumerate((loss_ax, metric_ax)):
                letter = "abcd"[row * 2 + col]
                ax.set_title(f"({letter}) {model}", loc="left", pad=32,
                             fontweight="normal")
                ax.legend(loc="lower left", bbox_to_anchor=(0, 1.015), ncol=2,
                          frameon=False, fontsize=8.5, borderaxespad=0,
                          handlelength=2.0, columnspacing=1.2)
                ax.axvline(best, color="#777777", linestyle=":", lw=0.9, zorder=0)
                ax.set_xlim(1, max(epochs))
                ax.set_xticks([1, 5, 10, 15, 20, max(epochs)])
                ax.set_xlabel("Epoch", labelpad=3)
                ax.grid(axis="y", color="#E2E2E2", linewidth=0.5)
                ax.set_axisbelow(True)
                ax.spines[["top", "right"]].set_visible(False)
                for spine in ("left", "bottom"):
                    ax.spines[spine].set_color("#909090")
                    ax.spines[spine].set_linewidth(0.6)
                ax.tick_params(width=0.6, length=3)
        fig.text(0.10, 0.025,
                 f"Dotted lines: selected epochs {seg['training']['best_epoch']} (UNet) and "
                 f"{ht['training']['best_epoch']} (classifier). Histories shown without smoothing.",
                 fontsize=8.5)
        out_path = OUTPUT_DIR / "fig2_training_dynamics.png"
        # Fixed canvas preserves the intended point sizes at 6.6 inches in Word.
        fig.savefig(out_path, dpi=300, bbox_inches=None)
        plt.close(fig)
    print(f"Saved: {out_path}")


def plot_evaluation_and_calibration():
    """Figure 3: Test counts, non-controlled validation snapshots, and cohort scores."""
    ht_path = HERE / "experiments" / "partner-20261114-threeclass-corrected-seed42" / "reports" / "hair_type_eval.json"
    if not ht_path.exists():
        ht_path = REPORTS_DIR / "hair_type_eval.json"
    ht = json.loads(ht_path.read_text(encoding="utf-8"))
    mob = json.loads((REPORTS_DIR / "val_mobilenet_v2.json").read_text(encoding="utf-8"))

    style = {"font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9.5,
             "xtick.labelsize": 9, "ytick.labelsize": 9,
             "text.color": "#252525", "axes.labelcolor": "#252525",
             "savefig.bbox": None}
    with plt.rc_context(style):
        fig = plt.figure(figsize=(6.6, 6.4))
        grid = fig.add_gridspec(2, 2, left=0.12, right=0.98, bottom=0.15,
                               top=0.92, wspace=0.28, hspace=0.65,
                               height_ratios=[1.05, 1], width_ratios=[1, 1.18])
        ax1, ax2 = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1])
        blue, rust = "#356581", "#A65E3B"

        # Every cell has its count and row percentage; a colorbar is redundant.
        cm = np.array(ht["test_metrics"]["confusion_matrix"])
        classes_display = ["Straight", "Wavy", "Curly"]
        ax1.imshow(cm, interpolation="nearest", cmap="Blues", vmin=0, vmax=cm.max())
        ax1.set_xticks(np.arange(3), classes_display)
        ax1.set_yticks(np.arange(3), classes_display)
        ax1.set_xlabel("Predicted class", labelpad=5)
        ax1.set_ylabel("True class", labelpad=5)
        ax1.set_title(f"(a) Locked test (n = {cm.sum()})", loc="left", pad=12,
                      fontweight="normal")
        ax1.tick_params(length=0, pad=5)
        for spine in ax1.spines.values():
            spine.set_visible(False)
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                val = cm[i, j]
                pct = val / cm[i].sum() * 100 if cm[i].sum() else 0
                ax1.text(j, i, f"{val}\n({pct:.1f}%)", ha="center", va="center",
                         color="white" if val > cm.max() / 2 else "#252525",
                         fontsize=9, linespacing=1.5)

        # A numeric snapshot avoids implying an architecture-only experiment.
        ax2.set_axis_off()
        ax2.set_title("(b) Validation snapshots (n = 57)", loc="left", pad=12,
                      fontweight="normal")
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        for x, label, align in [(0, "Model", "left"), (0.72, "Macro-F1", "right"),
                                 (0.98, "ECE", "right")]:
            ax2.text(x, 0.87, label, ha=align, va="center", fontsize=9)
        ax2.axhline(0.80, color="#777777", lw=0.6)
        for y, model, report in [(0.66, "MobileNetV2\n4 classes", mob),
                                   (0.43, "EfficientNetV2-S\n3 classes", ht)]:
            ax2.text(0, y, model, va="center", fontsize=9, linespacing=1.4)
            ax2.text(0.72, y, f"{report['val_metrics']['macro_f1']:.4f}",
                     ha="right", va="center", fontsize=9)
            ax2.text(0.98, y, f"{report['val_metrics']['ece'] * 100:.2f}%",
                     ha="right", va="center", fontsize=9)
        ax2.axhline(0.29, color="#B0B0B0", lw=0.6)
        ax2.text(0, 0.20, "Different class definitions and training data;\n"
                 "not a controlled architecture comparison.", va="top", fontsize=8.5,
                 linespacing=1.5)

        # Zoomed positional encoding, never a truncated bar. External n=6 is
        # retained from the original manuscript, not inferred from locked-test JSON.
        ax3 = fig.add_subplot(grid[1, :])
        pos = ax3.get_position()
        ax3.set_position([0.32, pos.y0, 0.60, pos.height])
        cohorts = [("Overall test (n = 59)", ht["test_metrics"], 3),
                   ("Figaro-1k (n = 37)", ht["test_by_cohort"]["figaro1k"], 2),
                   ("New dataset (n = 22)", ht["test_by_cohort"]["new_dataset"], 1),
                   ("External (n = 6)\nExploratory sample", {"accuracy": 1.0, "macro_f1": 1.0}, -0.4)]
        for key, label, offset, color, marker in [
                ("accuracy", "Accuracy", 0.13, blue, "o"),
                ("macro_f1", "Macro-F1", -0.13, rust, "D")]:
            values = [report[key] * 100 for _, report, _ in cohorts]
            ys = [y + offset for _, _, y in cohorts]
            ax3.scatter(values, ys, label=label, color=color, marker=marker, s=23, zorder=3)
            for value, y in zip(values, ys):
                ax3.annotate(f"{value:.2f}", (value, y), xytext=(-7, 0),
                             textcoords="offset points", ha="right", va="center",
                             fontsize=8.5, color=color)
        ax3.set_yticks([y for _, _, y in cohorts], [name for name, _, _ in cohorts])
        ax3.set_ylim(-1.05, 3.65)
        ax3.set_xlim(88, 101.5)
        ax3.set_xticks([90, 95, 100])
        ax3.set_xlabel("Score (%) — zoomed axis", labelpad=5)
        ax3.set_title("(c) Test cohorts and separate external sample", loc="left", pad=32,
                      fontweight="normal")
        ax3.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=2,
                   frameon=False, fontsize=9, borderaxespad=0, handletextpad=0.5)
        ax3.axhline(0.3, color="#909090", linestyle="--", lw=0.7)
        ax3.grid(axis="x", color="#E2E2E2", lw=0.5)
        ax3.set_axisbelow(True)
        ax3.spines[["top", "right", "left"]].set_visible(False)
        ax3.spines["bottom"].set_color("#909090")
        ax3.spines["bottom"].set_linewidth(0.6)
        ax3.tick_params(axis="y", length=0, pad=9)
        ax3.tick_params(axis="x", width=0.6, length=3)
        fig.text(0.12, 0.025,
                 "Cells: count (row %). External n = 6 is exploratory, outside the locked test.\n"
                 f"Classifier ONNX CPU mean latency: {ht['onnx']['mean_ms']:.2f} ms.",
                 fontsize=8.5, linespacing=1.5)
        out_path = OUTPUT_DIR / "fig3_evaluation_and_calibration.png"
        fig.savefig(out_path, dpi=300, bbox_inches=None)
        plt.close(fig)
    print(f"Saved: {out_path}")


def plot_geometric_grounding_schema():
    """Figure 4: Technical schema of head-unit canon and dual-mode anthropometric grounding.
    
    Academic anatomical vector line art, clean dimension callouts with dedicated clearance,
    and structured mathematical formulation cards.
    """
    svg_source = Path(r"C:\Users\lilol\AppData\Local\Temp\opencode-smartfetch\Human_silhouette_gender_neutral_back.svg")
    doc = fitz.open(svg_source)
    page = doc[0]
    drawings = page.get_drawings()

    def extract_path(drw):
        verts, codes = [], []
        for item in drw["items"]:
            cmd = item[0]
            if cmd == "l":
                p1, p2 = item[1], item[2]
                if len(verts) == 0:
                    verts.append((p1.x, p1.y))
                    codes.append(MplPath.MOVETO)
                verts.append((p2.x, p2.y))
                codes.append(MplPath.LINETO)
            elif cmd == "c":
                p1, p2, p3, p4 = item[1], item[2], item[3], item[4]
                if len(verts) == 0:
                    verts.append((p1.x, p1.y))
                    codes.append(MplPath.MOVETO)
                verts.extend([(p2.x, p2.y), (p3.x, p3.y), (p4.x, p4.y)])
                codes.extend([MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4])
        verts.append(verts[0])
        codes.append(MplPath.CLOSEPOLY)
        return MplPath(verts, codes)

    raw_body_path = extract_path(drawings[0])
    raw_arm_path = extract_path(drawings[1])

    fig_w, fig_h = 12.0, 6.6
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Scale and position
    Xc = 0.270
    Ytop = 0.90
    # Head height in Y plot coordinates:
    H_head = 0.228
    scale_y = H_head / 140.1
    scale_x = scale_y * (fig_h / fig_w)

    def transform_coords(x_svg, y_svg):
        nx = Xc + (x_svg - 279.68) * scale_x
        ny = Ytop - (y_svg - 1.89) * scale_y
        return nx, ny

    def transform_path(p):
        new_verts = []
        for (x, y) in p.vertices:
            nx, ny = transform_coords(x, y)
            new_verts.append((nx, ny))
        return MplPath(new_verts, p.codes)

    body_path = transform_path(raw_body_path)
    arm_path = transform_path(raw_arm_path)

    # Add body and arm contour
    ax.add_patch(patches.PathPatch(body_path, facecolor="#F8FAFC", edgecolor="#334155", lw=1.3, zorder=2))
    ax.add_patch(patches.PathPatch(arm_path, facecolor="none", edgecolor="#64748B", lw=1.0, zorder=3))

    # Hair silhouette (Medium length wavy hair draping naturally over head & shoulders)
    hair_pts_svg = [
        (279.68, -4.0),   # Crown
        (312.0, 0.0),
        (335.0, 30.0),
        (345.0, 80.0),
        (348.0, 140.0),
        (352.0, 185.0),
        (330.0, 235.0),
        (300.0, 255.0),
        (279.68, 252.0), # Bottom center terminal (y_bottom = 252 in SVG, H_head * 1.8)
        (259.0, 255.0),
        (229.0, 235.0),
        (207.0, 185.0),
        (211.0, 140.0),
        (214.0, 80.0),
        (224.0, 30.0),
        (247.0, 0.0),
        (279.68, -4.0)
    ]

    hair_pts_plot = [transform_coords(x, y) for (x, y) in hair_pts_svg]
    tck_h, u_h = splprep([[p[0] for p in hair_pts_plot], [p[1] for p in hair_pts_plot]], s=0, k=3, per=True)
    hx, hy = splev(np.linspace(0, 1, 300), tck_h)

    ax.fill(hx, hy, color="#E2E8F0", alpha=0.55, hatch="///", edgecolor="#64748B", lw=0.6, zorder=4)
    ax.plot(hx, hy, color="#1E293B", lw=1.4, zorder=5)

    # Guidelines Y levels
    y_c7 = Ytop - 140.1 * scale_y
    y_sh = Ytop - 186.1 * scale_y
    y_hb = Ytop - 252.0 * scale_y
    y_sc = Ytop - 280.0 * scale_y
    y_w  = Ytop - 420.0 * scale_y

    # Shoulder markers
    x_lsh, _ = transform_coords(165.0, 186.1)
    x_rsh, _ = transform_coords(394.0, 186.1)

    # Left Guidelines & Labels with Staggering and Stacked Nomenclature (Guaranteed Zero Collision!)
    # 1. Cranial Vertex
    ax.plot([0.015, 0.44], [Ytop, Ytop], color="#0F172A", linestyle="-", lw=1.1, zorder=1)
    ax.text(0.018, Ytop + 0.007, r"Cranial Vertex ($y_{top}$)", ha="left", va="bottom",
            fontsize=8.5, color="#0F172A", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # 2. Cervical Base
    ax.plot([0.015, 0.44], [y_c7, y_c7], color="#475569", linestyle=":", lw=1.1, zorder=1)
    ax.text(0.018, y_c7 + 0.007, r"Cervical Base ($y_{C7}$)", ha="left", va="bottom",
            fontsize=8.5, color="#475569", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # 3. Shoulder Baseline (Stacked name & symbol to provide wide clearance before L_sh)
    ax.plot([0.015, 0.44], [y_sh, y_sh], color="#DC2626", linestyle="--", lw=1.1, zorder=1)
    ax.text(0.018, y_sh + 0.007, "Shoulder Baseline", ha="left", va="bottom",
            fontsize=8.5, color="#DC2626", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)
    ax.text(0.018, y_sh - 0.005, r"($y_{shoulder}$)", ha="left", va="top",
            fontsize=8.0, color="#DC2626",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # 4. Hair Terminal (Positioned ABOVE line y_hb)
    ax.plot([0.015, 0.44], [y_hb, y_hb], color="#2563EB", linestyle="-", lw=1.1, zorder=1)
    ax.text(0.018, y_hb + 0.007, r"Hair Terminal ($y_{bottom}$)", ha="left", va="bottom",
            fontsize=8.5, color="#2563EB", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # 5. Mid-Back / Scapula (Stacked 2 lines BELOW line y_sc -> zero contact with arm and hair terminal)
    ax.plot([0.015, 0.44], [y_sc, y_sc], color="#7C3AED", linestyle=":", lw=1.1, zorder=1)
    ax.text(0.018, y_sc - 0.006, "Mid-Back / Scapula", ha="left", va="top",
            fontsize=8.5, color="#7C3AED", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)
    ax.text(0.018, y_sc - 0.024, r"($y_{scapula}$)", ha="left", va="top",
            fontsize=8.0, color="#7C3AED",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # 6. Waist Anchor
    ax.plot([0.015, 0.44], [y_w, y_w], color="#0D9488", linestyle=":", lw=1.1, zorder=1)
    ax.text(0.018, y_w + 0.007, r"Waist Anchor ($y_{waist}$)", ha="left", va="bottom",
            fontsize=8.5, color="#0D9488", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.10", facecolor="#FFFFFF", edgecolor="none", alpha=0.95), zorder=10)

    # Anatomical markers
    ax.scatter([x_lsh, x_rsh], [y_sh, y_sh], color="#DC2626", s=28, zorder=6)
    ax.scatter([Xc], [y_c7], color="#2563EB", s=24, zorder=6)
    ax.text(Xc, y_c7 + 0.012, r"$C_7$", ha="center", va="bottom", fontsize=8.5, color="#2563EB", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.1", facecolor="#FFFFFF", edgecolor="none", alpha=0.85), zorder=10)

    # Symmetrical L_sh and R_sh markers
    ax.text(x_lsh, y_sh + 0.016, r"$L_{sh}$", ha="center", va="bottom", fontsize=8.8, color="#DC2626", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.1", facecolor="#FFFFFF", edgecolor="none", alpha=0.9), zorder=10)
    ax.text(x_rsh, y_sh + 0.016, r"$R_{sh}$", ha="center", va="bottom", fontsize=8.8, color="#DC2626", fontweight="bold",
            bbox=dict(boxstyle="square,pad=0.1", facecolor="#FFFFFF", edgecolor="none", alpha=0.9), zorder=10)

    # Cranial Width
    x_parietal_l, _ = transform_coords(225.5, 50.0)
    x_parietal_r, _ = transform_coords(333.9, 50.0)
    ax.plot([x_parietal_l, x_parietal_l], [Ytop, Ytop + 0.05], color="#475569", lw=0.9)
    ax.plot([x_parietal_r, x_parietal_r], [Ytop, Ytop + 0.05], color="#475569", lw=0.9)
    ax.annotate("", xy=(x_parietal_l, Ytop + 0.04), xytext=(x_parietal_r, Ytop + 0.04),
                arrowprops=dict(arrowstyle="<->", color="#0F172A", lw=1.2))
    ax.text(Xc, Ytop + 0.048, r"$W_{cranial}$", ha="center", va="bottom",
            fontsize=9.5, fontweight="bold", color="#0F172A")

    # Head Height (x=0.355)
    ax.plot([x_parietal_r, 0.355], [Ytop, Ytop], color="#475569", lw=0.9, linestyle=":")
    ax.plot([Xc + 25.0 * scale_x, 0.355], [y_c7, y_c7], color="#475569", lw=0.9, linestyle=":")
    ax.annotate("", xy=(0.35, y_c7), xytext=(0.35, Ytop),
                arrowprops=dict(arrowstyle="<->", color="#0F172A", lw=1.2))
    ax.text(0.356, (Ytop + y_c7) / 2, r"$H_{head} \approx 1.30\,W_{cranial}$",
            ha="left", va="center", fontsize=8.5, color="#0F172A", fontweight="bold")

    # Hair Span on Right (x=0.445)
    ax.plot([Xc, 0.445], [Ytop, Ytop], color="#2563EB", lw=0.8, linestyle=":")
    ax.annotate("", xy=(0.44, y_hb), xytext=(0.44, Ytop),
                arrowprops=dict(arrowstyle="<->", color="#2563EB", lw=1.3))
    ax.text(0.446, (Ytop + y_hb) / 2, "Hair Span\n" + r"$\Delta y_{hair}$",
            ha="left", va="center", fontsize=8.8, color="#2563EB", fontweight="bold")

    # Right Card: Formulations & Grounding Rules (Generous left margin at x=0.50)
    card = patches.Rectangle((0.50, 0.03), 0.48, 0.94, facecolor="#FFFFFF",
                             edgecolor="#CBD5E1", lw=1.2, zorder=1)
    ax.add_patch(card)
    header_bar = patches.Rectangle((0.50, 0.895), 0.48, 0.075, facecolor="#F1F5F9",
                                   edgecolor="#CBD5E1", lw=1.0, zorder=2)
    ax.add_patch(header_bar)
    ax.text(0.74, 0.932, "Anthropometric Head-Unit Geometry Engine",
            ha="center", va="center", fontsize=11.5, fontweight="bold", color="#0F172A")

    sections = [
        (0.850,
         r"1. Head-Unit Canon & Cranial Normalization",
         r"$H_{head} = 1.30 \cdot W_{cranial}$  (Burton 2013, Domljan 2024 7.5-head canon)" + "\n" +
         r"$d_{shoulder} = 1.33 \cdot H_{head}$  (Cranial vertex to acromion baseline)" + "\n" +
         r"• Invariant scale: all vertical coordinates normalized by head unit $H_{head}$."),

        (0.640,
         r"2. Dual-Mode Anatomical Grounding Engine",
         r"• Mode 1 (Pose-Guided): MediaPipe Lite posterior landmarks (visibility $\geq 0.50$)." + "\n" +
         r"• Mode 2 (Silhouette Inflection): $\frac{d^2 W_{silh}}{dy^2}$ curvature on garment mask $M_{person} \backslash M_{hair}$." + "\n" +
         r"• Recovers 44.22% failure rate of monocular back-view pose tracking."),

        (0.425,
         r"3. Relative Length Classification ($R_{length} = \frac{y_{bottom} - y_{top}}{y_{shoulder} - y_{top}}$)",
         r"• Short ($R_{length} \leq 0.75$ or $L < 1.0\,H_{head}$): Cranial / nape terminal" + "\n" +
         r"• Short-Medium ($0.75 < R_{length} \leq 1.15$): Nape to shoulder baseline" + "\n" +
         r"• Medium ($1.15 < R_{length} \leq 1.65$): Shoulder to scapular zone" + "\n" +
         r"• Long ($R_{length} > 1.65$): Mid-back to lumbar zone"),

        (0.205,
         r"4. Volumetric Density & Tied-Hair Detection",
         r"• Volumetric Ratio: $R_{vol} = \frac{Area_{hair}}{H_{head}^2}$  (Thin $\leq 0.70$, Medium, Thick $\geq 1.35$)" + "\n" +
         r"• Lateral Spread: $R_{width} = \frac{W_{hair\_max}}{W_{cranial}}$  (Thin $\leq 1.15$, Medium, Thick $\geq 1.35$)" + "\n" +
         r"• Neck Constriction: $\eta = \frac{W_{neck}}{W_{cranial}}$  (Loose hair $\geq 0.55$, Ponytail / tied $< 0.55$)")
    ]

    for y_top_sec, title, body in sections:
        ax.text(0.518, y_top_sec, title, fontsize=10.0, fontweight="bold", color="#1E293B", va="top")
        ax.text(0.528, y_top_sec - 0.038, body, fontsize=8.8, color="#334155", va="top", linespacing=1.4)

    out_path = OUTPUT_DIR / "fig4_geometric_grounding_schema.png"
    plt.savefig(out_path)
    plt.close()
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    plot_system_architecture()
    plot_training_dynamics()
    plot_evaluation_and_calibration()
    plot_geometric_grounding_schema()
    print("All manuscript publication figures successfully generated!")
