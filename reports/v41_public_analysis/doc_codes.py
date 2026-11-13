"""v4.1 analysis: IPv6 misses against the unlabelled codes in the
same benchmark document (§1.3 of v4_public_analysis.md), per document and
inside each frame, for the pair in read_errors.MODELS.

    python reports/v41_public_analysis/doc_codes.py [--label IPV6_ADDRESS] [--out .../doc_codes.md]

Reads the prediction cache, as read_errors.py.
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

CODES = {
    "a dotted 3-part number (`9.9.9`, `v9.99.99`)": re.compile(r"(?<![\d.])v?\d{1,3}\.\d{1,3}\.\d{1,3}(?![\w.]|\.\d)"),
    "a 16-digit code": re.compile(r"(?<!\d)\d{16}(?!\d)"),
    "a code with a dash (`ARX-9999`)": re.compile(r"\b[A-Z]+-\d+\b"),
    "an `hh:mm` time": re.compile(r"(?<![\w:])\d{1,2}:\d{2}(?![\w:])"),
}
EITHER = list(CODES)[:2]  # the within-frame table: a dotted 3-part number or a 16-digit code


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", default="IPV6_ADDRESS")
    ap.add_argument("--out", default=str(R.OUT / "doc_codes.md"))
    a = ap.parse_args()
    docs = R.load_docs("benchmark")
    preds = {m: R.load_preds(mid, sha, "benchmark", "R", R.SB.DEFAULT_CACHE) for m, (mid, sha) in R.MODELS.items()}
    models = [R.OLD, R.NEW]
    doc_rows = collections.Counter()  # (code, present, model) -> missed; (code, present) -> n
    frame_rows = collections.Counter()  # (frame, either, model) -> missed; (frame, either) -> n
    frames = collections.Counter()
    for d in docs:
        has = {k: bool(r.search(d["text"])) for k, r in CODES.items()}
        either = any(has[k] for k in EITHER)
        for g in d["gold"]:
            if g["label"] != a.label:
                continue
            fk = R.norm_frame(R.frame(d["text"], g["start"], g["end"]))
            frames[fk] += 1
            frame_rows[(fk, either)] += 1
            for k in CODES:
                doc_rows[(k, has[k])] += 1
            for m in models:
                miss = R.M.gold_outcome(g, preds[m].get(d["id"], [])) != "exact"
                frame_rows[(fk, either, m)] += miss
                for k in CODES:
                    doc_rows[(k, has[k], m)] += miss

    def cell(c, key, m):
        n = c[key]
        return f"{c[(*key, m)]}/{n} ({c[(*key, m)] / n:.0%})" if n else "-"

    L = [f"# {a.label} not found exactly, by the codes in the same document (benchmark, track R)", "",
         "| in the same document | " + " | ".join(f"{m} missed, with | {m} missed, without" for m in models) + " |",
         "|---|" + "---|---|" * len(models)]
    for k in CODES:
        L.append(f"| {k} | " + " | ".join(f"{cell(doc_rows, (k, True), m)} | {cell(doc_rows, (k, False), m)}"
                                         for m in models) + " |")
    L += ["", "Inside each frame (a dotted 3-part number or a 16-digit code in the document, against neither):", "",
          "| frame | " + " | ".join(f"{m} missed, with a code | {m} missed, without" for m in models) + " |",
          "|---|" + "---|---|" * len(models)]
    for fk, _ in frames.most_common(5):
        L.append(f"| `{fk}` | " + " | ".join(f"{cell(frame_rows, (fk, True), m)} | {cell(frame_rows, (fk, False), m)}"
                                            for m in models) + " |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
