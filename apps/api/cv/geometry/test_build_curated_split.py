"""Unit tests for curated dataset split and Gate Fase 1 decision."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from build_curated_split import assign_splits, load_curated_records, run, summarize_splits


class BuildCuratedSplitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.tmp = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_load_curated_records_excludes_and_relabels(self):
        audit = {
            "records": [
                {"image_id": "figaro1k/keriting/00320.jpg", "cohort": "figaro1k", "hair_class": "keriting",
                 "sha256": "hash1", "width": 600, "height": 800, "min_side_ge_224": True},
                {"image_id": "new_dataset/bergelombang/download (6).jpg", "cohort": "new_dataset", "hair_class": "bergelombang",
                 "sha256": "hash2", "width": 600, "height": 800, "min_side_ge_224": True},
                {"image_id": "new_dataset/sangat keriting/download (13).jpg", "cohort": "new_dataset", "hair_class": "sangat-keriting",
                 "sha256": "hash3", "width": 736, "height": 920, "min_side_ge_224": True},
                {"image_id": "figaro1k/lurus/00001.jpg", "cohort": "figaro1k", "hair_class": "lurus",
                 "sha256": "hash4", "width": 400, "height": 500, "min_side_ge_224": True},
            ]
        }
        resolution = {
            "resolved_group": {
                "action": "exclude_all_from_curated_dataset",
                "image_ids": ["new_dataset/sangat keriting/download (13).jpg"]
            },
            "other_decisions": [
                {
                    "pair_index": 1,
                    "relation": "sama",
                    "selected_image_id": "new_dataset/bergelombang/download (6).jpg",
                    "approved_label": "keriting",
                    "excluded_image_id": "figaro1k/keriting/00320.jpg"
                }
            ]
        }

        audit_path = self.tmp / "audit.json"
        res_path = self.tmp / "res.json"
        audit_path.write_text(json.dumps(audit), encoding="utf-8")
        res_path.write_text(json.dumps(resolution), encoding="utf-8")

        curated, meta = load_curated_records(audit_path, res_path)
        curated_ids = [r["image_id"] for r in curated]

        self.assertNotIn("figaro1k/keriting/00320.jpg", curated_ids)
        self.assertNotIn("new_dataset/sangat keriting/download (13).jpg", curated_ids)
        self.assertIn("new_dataset/bergelombang/download (6).jpg", curated_ids)
        self.assertIn("figaro1k/lurus/00001.jpg", curated_ids)

        relabel_rec = next(r for r in curated if r["image_id"] == "new_dataset/bergelombang/download (6).jpg")
        self.assertEqual(relabel_rec["approved_label"], "keriting")
        self.assertEqual(relabel_rec["original_label"], "bergelombang")

    def test_assign_splits_deterministic_and_disjoint(self):
        records = [
            {"image_id": f"img_{i:03d}", "approved_label": "lurus", "cohort": "figaro1k"}
            for i in range(20)
        ]
        s1 = assign_splits(records, seed=42)
        s2 = assign_splits(records, seed=42)
        self.assertEqual(s1, s2)

        # Check disjoint
        train_ids = {r["image_id"] for r in s1 if r["split"] == "train"}
        val_ids = {r["image_id"] for r in s1 if r["split"] == "val"}
        test_ids = {r["image_id"] for r in s1 if r["split"] == "test"}
        self.assertEqual(len(train_ids & val_ids), 0)
        self.assertEqual(len(train_ids & test_ids), 0)
        self.assertEqual(len(val_ids & test_ids), 0)
        self.assertEqual(train_ids | val_ids | test_ids, {r["image_id"] for r in records})

    def test_summarize_splits_counts(self):
        records = [
            {"image_id": f"l_{i}", "approved_label": "lurus", "cohort": "figaro1k", "split": "train"} for i in range(7)
        ] + [
            {"image_id": f"l_val_{i}", "approved_label": "lurus", "cohort": "figaro1k", "split": "val"} for i in range(2)
        ] + [
            {"image_id": f"l_tst_{i}", "approved_label": "lurus", "cohort": "figaro1k", "split": "test"} for i in range(1)
        ]
        summary = summarize_splits(records)
        self.assertEqual(summary["total"], 10)
        self.assertEqual(summary["split_counts"]["train"], 7)
        self.assertEqual(summary["split_counts"]["val"], 2)
        self.assertEqual(summary["split_counts"]["test"], 1)
        self.assertEqual(summary["class_totals"]["lurus"], 10)


if __name__ == "__main__":
    unittest.main()
