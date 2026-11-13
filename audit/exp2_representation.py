"""EXPERIMENT 2 -- representation ablation (brief section 24).

exp1 showed that TXT/CSV/XLSX/DOCX score identically on the same content and
that PPTX and PDF differ ONLY in the table register -- where no data is lost
(survived=50/50) and the sole difference is the string used to join table
cells. This experiment isolates that variable directly: one row of content,
eight textual representations, nothing else changed.

Representation -> which real component produces it:
  space      -- pdfplumber's table reflow (PDF)
  pipe       -- formats/* flattening and the repo's own row fixtures
  blankline  -- pii_guard extract/base.py SEGMENT_JOIN (PPTX cells, DOCX)
  newline    -- a plain multi-line cell dump
  labeled_nl -- 'Header: value' per line
  labeled_pipe
  percell    -- EACH CELL ALONE. This is not hypothetical: it is exactly
                what formats/excel_format.py and formats/csv_format.py feed
                the model, one cell per detect_fn call.
  prose      -- flowing sentence, the training distribution

Scored value-level against the same expected set, so the numbers are
directly comparable across representations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec  # noqa: E402


def build(lang: str, kind: str):
    """Returns (list_of_texts, expected_pairs). Most representations are one
    text; `percell` is many, which is the point of it."""
    recs = spec.records(lang)
    labels = spec.FIELD_LABELS[lang]
    header = [labels[k] for k in spec.FIELD_ORDER]
    rows = [[r[k] for k in spec.FIELD_ORDER] for r in recs]
    expected = [(k, r[k]) for r in recs for k in spec.FIELD_ORDER]

    if kind == "space":
        texts = [" ".join(header) + "\n" + "\n".join(" ".join(r) for r in rows)]
    elif kind == "pipe":
        texts = [" | ".join(header) + "\n" + "\n".join(" | ".join(r) for r in rows)]
    elif kind == "blankline":
        cells = header + [c for r in rows for c in r]
        texts = ["\n\n".join(cells)]
    elif kind == "newline":
        cells = header + [c for r in rows for c in r]
        texts = ["\n".join(cells)]
    elif kind == "labeled_nl":
        texts = ["\n".join(f"{labels[k]}: {r[k]}" for k in spec.FIELD_ORDER)
                 for r in recs]
    elif kind == "labeled_pipe":
        texts = [" | ".join(f"{labels[k]}: {r[k]}" for k in spec.FIELD_ORDER)
                 for r in recs]
    elif kind == "percell":
        # Only DATA cells: the shipped pipelines classify header cells, they
        # never run detection over them. This matches the product exactly.
        texts = [c for r in rows for c in r]
    elif kind == "percell_labeled":
        # The proposed fix. Identical per-cell inference to `percell`, except
        # each cell is prefixed with ITS OWN COLUMN HEADER -- which both
        # formats/excel_format.py and formats/csv_format.py have already
        # parsed and are already holding at that point in the code. No new
        # information is needed from anywhere; it is purely a change to how
        # the existing information is presented to the model.
        texts = [f"{header[j]}: {c}" for r in rows for j, c in enumerate(r)]
    elif kind == "prose":
        texts = [spec._PROSE[lang].format(**r) for r in recs]
    else:
        raise ValueError(kind)
    return texts, expected


KINDS = ["prose", "labeled_nl", "labeled_pipe", "pipe", "newline",
         "blankline", "space", "percell", "percell_labeled"]


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.RESULTS.mkdir(parents=True, exist_ok=True)
    results = []

    for kind in KINDS:
        for lang in spec.LANGS:
            texts, expected = build(lang, kind)
            found = []
            for t in texts:
                for s in detect(t):
                    found.append((s["label"], t[s["start"]:s["end"]]))
            sc = harness.score_values(found, expected)
            results.append({"kind": kind, "lang": lang,
                            "n_inference_calls": len(texts),
                            **{k: v for k, v in sc.items()
                               if k in ("tp", "fp", "fn", "precision",
                                        "recall", "f1")},
                            "missed": [list(x) for x in sc["missed"]]})

    out = harness.RESULTS / "exp2_representation.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    # --- readable matrix ---
    print(f"{'representation':14s} " + " ".join(f"{l:>12s}" for l in spec.LANGS)
          + f"{'  MEAN':>10s}")
    print("-" * 78)
    by = {(r["kind"], r["lang"]): r for r in results}
    for kind in KINDS:
        cells, tot_tp, tot_fn = [], 0, 0
        for lang in spec.LANGS:
            r = by[(kind, lang)]
            cells.append(f"{r['recall']:>11.0%} ")
            tot_tp += r["tp"]
            tot_fn += r["fn"]
        mean = tot_tp / (tot_tp + tot_fn) if (tot_tp + tot_fn) else 0
        print(f"{kind:14s} " + " ".join(cells) + f"{mean:>9.0%}")
    print("\n(recall; precision in the JSON)")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
