"""Fast, no-GPU tests for train.py's pure logic -- label loading and
metric computation. Does NOT load a real model/tokenizer or the `datasets`
Arrow pipeline (that's what --smoke-test is for, deliberately expensive
and run by hand, not part of this suite).

Run: python model/test_train.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np                                    # noqa: E402

from train import (build_compute_metrics, load_labels,  # noqa: E402
                   per_label_report)

FAIL = False


def check(cond: bool, name: str, detail: object = "") -> None:
    global FAIL
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  ({detail!r})" if not cond else ""))
    if not cond:
        FAIL = True


tmp = Path(tempfile.mkdtemp())

# ---------------------------------------------------------------------------
print("1. load_labels")
# ---------------------------------------------------------------------------
labels_json = {
    "labels": ["O", "B-EMAIL", "I-EMAIL"],
    "label2id": {"O": 0, "B-EMAIL": 1, "I-EMAIL": 2},
    "id2label": {"0": "O", "1": "B-EMAIL", "2": "I-EMAIL"},
}
(tmp / "labels.json").write_text(json.dumps(labels_json), encoding="utf-8")
labels, label2id, id2label = load_labels(tmp)
check(labels == ["O", "B-EMAIL", "I-EMAIL"], "labels list round-trips", labels)
check(label2id["B-EMAIL"] == 1, "label2id values are ints", label2id)
check(id2label[1] == "B-EMAIL", "id2label keys are ints", id2label)

# ---------------------------------------------------------------------------
print("2. build_compute_metrics / per_label_report")
# ---------------------------------------------------------------------------
# Two 4-token windows. Window 1: predicted == true (perfect). Window 2:
# predicted misses the entity entirely (all O) -- one false negative.
id2label3 = {0: "O", 1: "B-EMAIL", 2: "I-EMAIL"}


def logits_for(label_ids: list[int]) -> list[list[float]]:
    # One-hot-ish logits so argmax reproduces label_ids exactly.
    return [[10.0 if i == lid else 0.0 for i in range(3)] for lid in label_ids]


true_labels = np.array([
    [-100, 1, 2, -100],
    [-100, 1, 2, -100],
])
pred_logits = np.array([
    logits_for([0, 1, 2, 0]),
    logits_for([0, 0, 0, 0]),
])

compute_metrics = build_compute_metrics(id2label3)
metrics = compute_metrics((pred_logits, true_labels))
check(set(metrics.keys()) == {"precision", "recall", "f1", "accuracy"},
      "compute_metrics returns precision/recall/f1/accuracy", metrics.keys())
# 1 entity correctly found (window 1), 1 entity missed (window 2) -> recall 0.5,
# precision 1.0 (no false positives), f1 = 2*1*0.5/(1+0.5) = 0.667.
check(abs(metrics["recall"] - 0.5) < 1e-6, "recall reflects the missed entity",
      metrics["recall"])
check(abs(metrics["precision"] - 1.0) < 1e-6, "precision is 1.0 (no false positives)",
      metrics["precision"])
check("-100" not in str(metrics), "IGNORE_LABEL_ID never reaches seqeval", metrics)

report_text, report_dict = per_label_report(id2label3, pred_logits, true_labels)
check("EMAIL" in report_text, "per_label_report text names the real label",
      report_text[:200])
check(isinstance(report_text, str) and len(report_text) > 0,
      "per_label_report returns text", len(report_text))
check(report_dict is None or "EMAIL" in report_dict,
      "per_label_report dict (when supported) also names the real label",
      report_dict)

print("\n" + "=" * 62)
if FAIL:
    print("SOME TESTS FAILED")
else:
    print("ALL TESTS PASSED")
print("=" * 62)
sys.exit(1 if FAIL else 0)
