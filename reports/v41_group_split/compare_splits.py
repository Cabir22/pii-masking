"""v4.1 step 2 (data audit A2): the new documents split one by one (as in v4)
against split by template (`prepare_splits --group-split template`).

    python reports/v41_group_split/compare_splits.py <targeted.jsonl> <llm.clean.jsonl> [...] [--md out.md]

Counts per split: documents, sources, labels, and test/val documents whose
template (`prepare_splits._skeleton`) is also in train. Counts only.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_splits import _skeleton, stratified_split  # noqa: E402

SEED = 20261001


def source(r: dict) -> str:
    return "targeted" if str(r.get("id", "")).startswith("targeted") else "llm"


def describe(train: list, val: list, test: list) -> dict:
    tr = {_skeleton(r) for r in train}
    out = {}
    for name, rows in (("train", train), ("val", val), ("test", test)):
        d = {"documents": len(rows),
             "by_source": dict(collections.Counter(source(r) for r in rows)),
             "labels": dict(collections.Counter(e["label"] for r in rows for e in r["entities"])),
             "families": dict(collections.Counter((r.get("_spec") or {}).get("family", "llm") for r in rows))}
        if name != "train":
            shared = [r for r in rows if _skeleton(r) in tr]
            d["template_in_train"] = len(shared)
            d["template_in_train_by_source"] = dict(collections.Counter(source(r) for r in shared))
        out[name] = d
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    records = []
    for p in a.inputs:
        records += [json.loads(line) for line in open(p, encoding="utf-8")]
    res = {}
    for name, key in (("one by one (v4)", None), ("by template (v4.1)", _skeleton)):
        res[name] = describe(*stratified_split([dict(r) for r in records], 0.1, 0.1, SEED, group_key=key))
    names = list(res)
    L = [f"# Split by template: {len(records):,} new documents (seed {SEED})", "",
         "| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for split in ("train", "val", "test"):
        L.append(f"| {split} documents | " + " | ".join(f"{res[n][split]['documents']:,}" for n in names) + " |")
        L.append(f"| {split}: targeted / llm | " + " | ".join(
            f"{res[n][split]['by_source'].get('targeted', 0):,} / {res[n][split]['by_source'].get('llm', 0):,}"
            for n in names) + " |")
    for split in ("val", "test"):
        L.append(f"| **{split} documents whose template is also in train** | " + " | ".join(
            f"**{res[n][split]['template_in_train']:,}** (targeted {res[n][split]['template_in_train_by_source'].get('targeted', 0):,})"
            for n in names) + " |")
    labels = sorted(res[names[0]]["train"]["labels"])
    L += ["", "## Labels in test (share of the label's mentions)", "",
          "| Label | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for lab in labels:
        cells = []
        for n in names:
            tot = sum(res[n][s]["labels"].get(lab, 0) for s in ("train", "val", "test"))
            cells.append(f"{res[n]['test']['labels'].get(lab, 0):,} ({res[n]['test']['labels'].get(lab, 0) / tot:.1%})")
        L.append(f"| {lab} | " + " | ".join(cells) + " |")
    L += ["", "## Targeted families in test", "",
          "| Family | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    fams = sorted({f for n in names for f in res[n]["test"]["families"] if f != "llm"})
    for f in fams:
        L.append(f"| {f} | " + " | ".join(f"{res[n]['test']['families'].get(f, 0):,}" for n in names) + " |")
    text = "\n".join(L) + "\n"
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8", newline="\n")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
