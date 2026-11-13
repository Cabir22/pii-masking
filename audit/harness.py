"""Shared setup for the audit experiments.

Everything the audit exercises lives in this tree: `formats/` (TXT / CSV /
XLSX), `scripts/pii_guard/` (DOCX + PPTX, one package), `model/` (inference)
and `scripts/piigen/` (validators). An earlier version of this file `git
archive`d two divergent copies of pii_guard out of the `mask/docx` and
`mask/pptx` branches, because no single branch held all six formats. Those
branches were consolidated into `main` on 2026-09-28 and deleted (the
`archive/mask-*` tags keep them), so the audit now imports straight from the
working tree and needs no particular branch, git access, or scratch path.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Generated fixtures and per-run results. Git-ignored (see .gitignore) and
#: safe to delete; override with AUDIT_WORK to put it somewhere else.
WORK = Path(os.environ.get("AUDIT_WORK", REPO / "audit" / "_work"))
SCRATCH = WORK      # exp7 keeps its patched copy of excel_format.py here
FIXTURES = WORK / "fixtures"
RESULTS = WORK / "results"

MODEL_ID = "your-hf-org/masking-multilingual"


def setup_paths() -> None:
    """Make formats/, model/, scripts/ (piigen, pii_guard) and audit/ importable."""
    for p in [REPO / "audit", REPO / "formats", REPO / "model", REPO / "scripts"]:
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


_MODEL = None


def get_model():
    """Loads the one checkpoint that actually exists. Model A (the
    Azerbaijani-only 105k-row checkpoint) is NOT present: it is referenced
    nowhere in any branch, is not in the local HuggingFace cache, and the
    your-hf-org account exposes only masking-multilingual and an unrelated
    whisper model. Every Model-A-vs-Model-B comparison in the brief is
    therefore reported as blocked rather than estimated."""
    global _MODEL
    if _MODEL is None:
        from predict import load_model
        _MODEL = load_model(MODEL_ID)
    return _MODEL


def detect_fn_factory():
    """The detect_fn shape formats/*.py expect: text -> [{start,end,label}].

    Spans are de-overlapped because formats.txt.mask_text treats overlapping
    spans as a hard error (by design -- silent corruption otherwise), and raw
    model output can legitimately overlap across windows.
    """
    from predict import detect_entities
    model, tokenizer, id2label = get_model()

    def detect(text: str) -> list[dict]:
        raw = detect_entities(text, model, tokenizer, id2label)
        spans = sorted(
            ({"start": int(d["start"]), "end": int(d["end"]),
              "label": d["label"],
              "score": float(d.get("score", d.get("confidence", 1.0)))}
             for d in raw),
            key=lambda s: (s["start"], -(s["end"] - s["start"])))
        out: list[dict] = []
        for s in spans:
            if out and s["start"] < out[-1]["end"]:
                continue  # keep the first/longest, drop the overlapper
            out.append(s)
        return out

    return detect


# --------------------------------------------------------------------------
# Value-level scoring
# --------------------------------------------------------------------------

def score_values(found: list[tuple[str, str]],
                 expected: list[tuple[str, str]]) -> dict:
    """Multiplicity-aware (label, value) matching.

    Value-level rather than offset-level on purpose: identical content lands
    at different offsets in different formats, so an offset-exact comparison
    across formats would measure the renderer, not the pipeline. Offset and
    mapping correctness are measured separately, per format, against that
    format's own extracted text.

    Multiplicity matters because a value repeated N times in the extracted
    text should be found N times; counting it once would turn correct repeat
    detections into false positives (a real scoring bug hit earlier in this
    project's PDF pass, worth 19 F1 points).
    """
    from collections import Counter
    exp = Counter(expected)
    got = Counter(found)
    tp = sum(min(got[k], exp[k]) for k in exp)
    fp = sum(got[k] - min(got[k], exp.get(k, 0)) for k in got)
    fn = sum(exp[k] - min(got[k], exp[k]) for k in exp)
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r,
            "f1": f1,
            "missed": sorted(k for k in exp if got[k] < exp[k]),
            "spurious": sorted(k for k in got if got[k] > exp.get(k, 0))}


def spans_to_values(text: str, spans: list[dict]) -> list[tuple[str, str]]:
    return [(s["label"], text[s["start"]:s["end"]]) for s in spans]
