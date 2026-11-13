"""v4.1 analysis: which other sentence of a benchmark document
makes v4 miss a value it finds when that sentence is shown alone
(perturb.py: `sentence` found, `doc` missed)?

For every v4 miss of the given labels, each other sentence of the document is
deleted in turn and v4 (track R) is re-run; a deletion that brings the exact
span back is a "blocker". Blockers are reported by shape: digits -> 9,
letters kept (benchmark documents are public), and by what the benchmark
planted in them (its hard negatives and distractors).

    python reports/v41_public_analysis/ablate.py --label IPV6_ADDRESS --label IPV4_ADDRESS \
        [--model v4] [--out reports/v41_public_analysis/out/ablate.md]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

SB = R.SB


def sentences(text: str) -> list[tuple[int, int]]:
    """Sentence spans: split after . ; ! ? followed by a space, and at line breaks."""
    out, a = [], 0
    for m in re.finditer(r"[.;!?](?=\s)|\n", text):
        b = m.end()
        if text[a:b].strip():
            out.append((a, b))
        a = b
    if text[a:].strip():
        out.append((a, len(text)))
    return out


def shape(s: str) -> str:
    return re.sub(r"\d", "9", s.strip())


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--model", default=R.NEW, choices=list(R.MODELS))
    ap.add_argument("--errors-dir", default=str(R.OUT))
    ap.add_argument("--out", default=str(R.OUT / "ablate.md"))
    a = ap.parse_args()
    docs = {d["id"]: d for d in R.load_docs("benchmark")}
    raw = {}
    with open(SB.BENCH_V3, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if i >= SB.BENCH_V3_SCORED:
                break
            r = json.loads(line)
            raw[r["id"]] = r
    eng = SB.Engine(*R.MODELS[a.model], "cpu", ["R"])
    L = [f"# Ablation: which other sentence blocks {a.model} (track R)", "",
         "Each other sentence of the document deleted in turn; a blocker is a deletion that brings "
         "the exact span back.", ""]
    for lab in a.label:
        res = json.loads((Path(a.errors_dir) / f"benchmark_R_{lab}.json").read_text(encoding="utf-8"))
        bad = [(i["id"], i["value"]) for i in res["items"] if i["outcomes"][a.model] != "exact"]
        n_docs = n_blocked = 0
        blockers = collections.Counter()
        planted = collections.Counter()
        n_blockers = collections.Counter()
        examples = []
        for did, val in bad:
            d = docs[did]
            g = next(x for x in d["gold"] if x["label"] == lab and d["text"][x["start"]:x["end"]] == val)
            text = d["text"]
            spec = raw[did]["_spec"]
            plants = [(p, "hard negative") for p in spec.get("hard_negatives", [])] + \
                     [(p, "distractor") for p in spec.get("distractors", [])]
            n_docs += 1
            found_by = []
            for s, e in sentences(text):
                if s <= g["start"] < e:
                    continue
                t2 = text[:s] + text[e:]
                shift = e - s if s < g["start"] else 0
                gs, ge = g["start"] - shift, g["end"] - shift
                if any(p["start"] == gs and p["end"] == ge and p["label"] == lab for p in eng.run("R", t2)):
                    found_by.append(text[s:e])
            n_blockers[min(len(found_by), 3)] += 1
            if found_by:
                n_blocked += 1
            for sent in found_by:
                blockers[shape(sent)[:90]] += 1
                hit = [f"{kind}: {shape(p)}" for p, kind in plants if p in sent]
                for h in hit or ["nothing planted"]:
                    planted[h] += 1
            if found_by and len(examples) < 12:
                examples.append((did, val, found_by[:2]))
        L += [f"## {lab}: {n_docs} {a.model} misses, {n_blocked} brought back by deleting one other sentence", "",
              "| blockers per miss | misses |", "|---|---|"]
        L += [f"| {k if k < 3 else '3+'} | {v} |" for k, v in sorted(n_blockers.items())]
        L += ["", "### What the blocking sentences hold (benchmark plants, digits as 9)", "", "| plant | n |", "|---|---|"]
        L += [f"| `{k}` | {v} |" for k, v in planted.most_common(30)]
        L += ["", "### Blocking sentences by shape", "", "| sentence | n |", "|---|---|"]
        L += [f"| `{k}` | {v} |" for k, v in blockers.most_common(30)]
        L += ["", "### Examples", ""]
        L += [f"- {did} `{val}`: " + " / ".join(f"`{s.strip()}`" for s in fb) for did, val, fb in examples]
        L.append("")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
