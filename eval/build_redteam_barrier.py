"""Build eval/leakage_guard_barrier_redteam.json.gz from the red-team findings.

    python eval/build_redteam_barrier.py [--findings redteam/findings]
                                         [--out eval/leakage_guard_barrier_redteam.json.gz]

Every finding is marked `test` or `training` (column `split`). The `test` rows must stay
out of every training build, so they can measure m2 and later models fairly. An unmarked
row counts as `test`; only a row marked `training` is left out.

Same format as the other barriers (eval/build_shadow_hashes.py), so eval/leakage_guard.py
and every build that runs it (build_m1-style) pick it up without a flag:
  - SHA-1 of every word 8-gram of every `test` text;
  - SHA-1 of each distinctive code-like value in `expected` (VALUE_LABELS, not low-entropy,
    found in the text), keyed on its longest word run, as the shadow values.
Half of the findings are shorter than 8 words, which no 8-gram can catch. For a text of
3-7 words the whole text is hashed as one n-gram (`short_sha1`, with its length), and the
guard looks for that exact word run inside training texts. Texts of 1-2 words are too
common to block (`salam necesen`); they count in `source.too_short`.
The findings are public, so hashing hides nothing here; it only keeps the format the same.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from build_shadow_hashes import VALUE_LABELS  # noqa: E402
from leakage_guard import (N, SHADOW_FORMAT, anchor_of, is_distinctive, is_low_entropy,  # noqa: E402
                           ngrams, sha1, words)

FINDINGS = HERE.parent / "redteam" / "findings"
OUT = HERE / "leakage_guard_barrier_redteam.json.gz"
MIN_SHORT = 3


def expected_values(expected: str) -> list[tuple[str, str]]:
    """`value=LABEL; value=LABEL` -> [(value, LABEL)]; `(nothing)` and free text give []."""
    out = []
    for part in expected.split("; "):
        v, sep, lab = part.rpartition("=")
        if sep and v.strip() and lab.strip().isupper():
            out.append((v.strip(), lab.strip()))
    return out


def build(paths: list[Path]) -> dict:
    grams: set[str] = set()
    short: dict[str, dict] = {}
    values: dict[str, dict] = {}
    rows = test = too_short = 0
    by_file: dict[str, int] = {}
    skipped = {"name, place or date label": 0, "vocabulary or too short": 0,
               "low-entropy label or value": 0, "not found in the text": 0}
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes())
        with open(p, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                rows += 1
                if (r.get("split") or "").strip().lower() == "training":
                    continue
                test += 1
                by_file[p.stem] = by_file.get(p.stem, 0) + 1
                text = r["text"]
                ws = words(text)
                if len(ws) >= N:
                    grams.update(sha1(g) for g in ngrams(ws))
                elif len(ws) >= MIN_SHORT:
                    g = " ".join(ws)
                    short[sha1(g)] = {"sha1": sha1(g), "n": len(ws)}
                else:
                    too_short += 1
                for v, lab in expected_values(r.get("expected") or ""):
                    a = anchor_of(v)
                    if lab not in VALUE_LABELS:
                        skipped["name, place or date label"] += 1
                    elif v not in text:
                        skipped["not found in the text"] += 1
                    elif is_low_entropy(v, [lab]):
                        skipped["low-entropy label or value"] += 1
                    elif not (a and is_distinctive(v)):
                        skipped["vocabulary or too short"] += 1
                    else:
                        values[sha1(v)] = {"sha1": sha1(v), "anchor_sha1": sha1(a[0]),
                                           "offset": a[1], "length": len(v)}
    return {"format": SHADOW_FORMAT, "n": N,
            "normalisation": "lower() minus U+0307, \\w+ word runs, 8-grams joined by one space; "
                             f"texts of {MIN_SHORT}-{N - 1} words hashed whole (short_sha1)",
            "value_rule": "label in VALUE_LABELS (codes only, never names, places or dates), distinctive and not low-entropy",
            "built_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": {"files": len(paths), "findings": rows, "test_rows": test,
                       "training_rows": rows - test, "test_rows_by_file": by_file,
                       "too_short": too_short, "sha256": h.hexdigest() if paths else None,
                       "rule": "a row counts as test unless split is 'training'"},
            "values_skipped": skipped,
            "ngram_sha1": sorted(grams),
            "short_sha1": sorted(short.values(), key=lambda x: x["sha1"]),
            "values": sorted(values.values(), key=lambda x: x["sha1"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--findings", type=Path, default=FINDINGS)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    paths = sorted(args.findings.glob("*.csv"))
    if not paths:
        raise SystemExit(f"no findings in {args.findings}")
    data = build(paths)
    with gzip.open(args.out, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True)
    s = data["source"]
    print(f"wrote {args.out}: {s['test_rows']} test rows of {s['findings']} "
          f"({s['training_rows']} marked training), {len(data['ngram_sha1'])} 8-gram hashes, "
          f"{len(data['short_sha1'])} short-text hashes, {len(data['values'])} value hashes; "
          f"{s['too_short']} texts under {MIN_SHORT} words; values not hashed: {data['values_skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
