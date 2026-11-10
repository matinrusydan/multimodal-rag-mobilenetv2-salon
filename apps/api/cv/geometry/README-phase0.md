# Fase 0: Pose feasibility evaluator

Reproducible evaluator for landmark availability using the repository's existing MediaPipe Pose Tasks assets. It processes canonical `figaro1k` and `new_dataset` cohorts and reports low-resolution new-dataset backups separately. It does not download models or modify source data.

## Run

From repository root (PowerShell):

```powershell
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/pose_feasibility.py --help
apps/api/cv/.venv/Scripts/python.exe apps/api/cv/geometry/pose_feasibility.py --out apps/api/cv/geometry/reports/phase0
```

Use `--limit 3` for a deterministic sampling smoke evaluation, `--model lite|heavy` to choose the existing local asset, and `--seed 42` to reproduce sampling. `--out` must remain within this geometry directory. Outputs are JSON, CSV, Markdown summary, per-image landmark overlays, and success/failure contact sheets.

The evaluator uses IMAGE mode, min detection/presence confidence 0.3, visibility 0.5, and normalized-coordinate tolerance 0.15. A shoulder success requires both shoulders; a head success requires at least one of nose/ears. Dataset class labels `sangat keriting` and `sangat-keriting` are normalized to the canonical `sangat-keriting`. Only the four canonical class directories and their explicitly named low-resolution backups are discovered; the canonical dataset roots must exist.

Gate statistics are computed directly over the canonical cohorts (`figaro1k` and `new_dataset`) without camera-position filtering or historical annotation loading. Low-resolution backups are reported separately as an exploratory cohort. Rates include Wilson 95% intervals, both unconditional and conditional on pose detection.

Paired filename candidates are generated for Figaro/new_dataset and, separately, new_dataset/its low-resolution backup using identical class and filename. Filenames do not prove that images depict the same scene. Restoring an image may change crop or scene, not only resolution, so the backup comparison is not necessarily a resolution-only experiment. Backups are a separate cohort, excluded from the canonical gate; absent backups are not synthetically replaced. MediaPipe visibility is not anatomical accuracy. This evaluator has no independent human validation, so its automated result alone is not a fully human-validated gate.

Run pure helper tests (no MediaPipe import/inference):

```powershell
apps/api/cv/.venv/Scripts/python.exe -m unittest discover -s apps/api/cv/geometry -p test_pose_feasibility.py
```
