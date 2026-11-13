"""Value-disjoint re-split of the merged corpus for the ml_context labels.

NOT USED -- measured 2026-09-30 (P1-3). On this corpus the name pool is so
small that shared values chain almost every named document into one group:
- the 2026-09-22 build's test set had ~12x fewer GIVENNAME mentions than a
  representative 10% split (1,911 vs ~23,000);
- it also split 47% of documents from their own translations (translations
  carry freshly minted values, so they share no value with their source --
  the claim below that they "group together" is false);
- gluing translation families as well leaves test with 1 GIVENNAME mention.

The project keeps the original per-family `merged/` split and measures
memorisation with a "new names" slice (test mentions whose value never
occurs in train, ~15,000 of them) instead. Kept for the record; don't use it
to build training or evaluation data.

WHY
---
The current merged split was made per-document at random. GIVENNAME,
SURNAME and STREET are drawn from finite pools, so the *same value*
appears in train and in val/test. A token classifier that has memorised
"Mammadov is a SURNAME" then scores as if it had generalised, and the
headline F1 measures recall of the pool, not of the task.

This script re-assigns whole documents so that no GIVENNAME/SURNAME/STREET
*value* is ever present on both sides of the split.

CITY is deliberately NOT included. Its value space is finite by nature
(~97 real places, see values.py FINITE_BY_NATURE) -- holding cities out of
training would delete signal the model genuinely needs at inference time,
and "can it recognise a city that does not exist" is not a question worth
asking. CITY generalisation is measured by context/morphology variation
instead (see the adversarial eval set), not by value disjointness.

METHOD
------
Two documents are glued into the same group when they share any
GIVENNAME/SURNAME/STREET value; grouping is transitive (union-find), so a
chain A-B-C ends up in one group even when A and C share nothing directly.
Whole groups are then assigned to a split, largest first, each group going
to whichever split is furthest below its target share.

Measured on the current corpus (416,279 docs): 64.6% of documents share no
such value with any other document and are freely assignable; the mass is
two large groups of 89,209 and 20,506 documents, which land in train.

A translated document and its source share entity values, so translations
of the same document also group together -- which additionally closes a
train/test leak that per-document splitting left open.

Run:
  python scripts/regroup_splits.py --dry-run
  python scripts/regroup_splits.py --out data/processed/merged_disjoint
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ("train", "val", "test")
GROUP_LABELS = frozenset({"GIVENNAME", "SURNAME", "STREET"})
DEFAULT_TARGETS = {"train": 0.80, "val": 0.10, "test": 0.10}


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def add(self, x: str) -> None:
        self.parent.setdefault(x, x)

    def find(self, x: str) -> str:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:          # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def entity_value(doc_text: str, ent: dict) -> str:
    """Entities do not all carry a precomputed `text` field."""
    return ent.get("text") or doc_text[ent["start"]:ent["end"]]


def scan(data_dir: Path) -> tuple[UnionFind, list[str], dict, dict]:
    """Pass 1 -- build groups. Document text is never retained."""
    uf = UnionFind()
    order: list[str] = []
    doc_lang: dict[str, str] = {}
    doc_labels: dict[str, frozenset] = {}
    first_doc_for_value: dict[tuple[str, str], str] = {}

    for split in SPLITS:
        path = data_dir / f"{split}.docs.jsonl"
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh):
                doc = json.loads(line)
                key = f"{split}#{line_no}"
                uf.add(key)
                order.append(key)
                doc_lang[key] = doc.get("lang", "?")
                text = doc["text"]
                labels = set()
                for ent in doc["entities"]:
                    label = ent["label"]
                    labels.add(label)
                    if label in GROUP_LABELS:
                        vkey = (label, entity_value(text, ent))
                        prior = first_doc_for_value.get(vkey)
                        if prior is None:
                            first_doc_for_value[vkey] = key
                        else:
                            uf.union(key, prior)
                doc_labels[key] = frozenset(labels)
    return uf, order, doc_lang, doc_labels


def assign(uf: UnionFind, order: list[str],
           targets: dict[str, float]) -> dict[str, str]:
    """Largest group first, into whichever split is furthest below target."""
    members: dict[str, list[str]] = defaultdict(list)
    for key in order:
        members[uf.find(key)].append(key)

    total = len(order)
    quota = {s: targets[s] * total for s in SPLITS}
    filled = {s: 0 for s in SPLITS}
    doc_split: dict[str, str] = {}

    for group in sorted(members.values(), key=len, reverse=True):
        split = max(SPLITS, key=lambda s: quota[s] - filled[s])
        filled[split] += len(group)
        for key in group:
            doc_split[key] = split
    return doc_split


def verify(data_dir: Path, doc_split: dict[str, str]) -> dict[str, set]:
    """Pass 2a -- recollect values per split and prove the split is disjoint."""
    per_split_values: dict[str, set] = {s: set() for s in SPLITS}
    for split in SPLITS:
        path = data_dir / f"{split}.docs.jsonl"
        with path.open(encoding="utf-8") as fh:
            for line_no, line in enumerate(fh):
                doc = json.loads(line)
                key = f"{split}#{line_no}"
                dest = doc_split[key]
                text = doc["text"]
                for ent in doc["entities"]:
                    if ent["label"] in GROUP_LABELS:
                        per_split_values[dest].add(
                            (ent["label"], entity_value(text, ent)))
    return per_split_values


def write_out(data_dir: Path, out_dir: Path, doc_split: dict[str, str]) -> None:
    """Pass 2b -- stream every document to its newly assigned split."""
    out_dir.mkdir(parents=True, exist_ok=True)
    handles = {s: (out_dir / f"{s}.docs.jsonl").open("w", encoding="utf-8")
               for s in SPLITS}
    try:
        for split in SPLITS:
            path = data_dir / f"{split}.docs.jsonl"
            with path.open(encoding="utf-8") as fh:
                for line_no, line in enumerate(fh):
                    handles[doc_split[f"{split}#{line_no}"]].write(line)
    finally:
        for fh in handles.values():
            fh.close()

    labels_src = data_dir / "labels.json"
    if labels_src.exists():
        (out_dir / "labels.json").write_text(
            labels_src.read_text(encoding="utf-8"), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "processed" / "merged"))
    ap.add_argument("--out", default=str(ROOT / "data" / "processed" / "merged_disjoint"))
    ap.add_argument("--dry-run", action="store_true",
                    help="report the split it would produce, write nothing")
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir)
    for split in SPLITS:
        path = data_dir / f"{split}.docs.jsonl"
        if not path.exists():
            print(f"error: {path} not found")
            return 1

    print("pass 1: grouping documents by shared name/surname/street values...")
    uf, order, doc_lang, doc_labels = scan(data_dir)
    print(f"  {len(order):,} documents")

    doc_split = assign(uf, order, DEFAULT_TARGETS)

    sizes = Counter(doc_split.values())
    total = len(order)
    print("\nnew split sizes:")
    for split in SPLITS:
        print(f"  {split:<5} {sizes[split]:>8,}  ({sizes[split]/total:.2%})")

    print("\nper-language distribution:")
    lang_split = defaultdict(Counter)
    for key, split in doc_split.items():
        lang_split[doc_lang[key]][split] += 1
    for lang in sorted(lang_split):
        counts = lang_split[lang]
        lang_total = sum(counts.values())
        shares = "  ".join(f"{s}={counts[s]/lang_total:.1%}" for s in SPLITS)
        print(f"  {lang}: {lang_total:>7,}   {shares}")

    print("\nlabel coverage (labels missing from a split are a problem):")
    label_split = defaultdict(set)
    for key, split in doc_split.items():
        for label in doc_labels[key]:
            label_split[label].add(split)
    missing = {lab: sorted(set(SPLITS) - splits)
               for lab, splits in label_split.items()
               if set(SPLITS) - splits}
    if missing:
        for lab, absent in sorted(missing.items()):
            print(f"  WARNING {lab}: absent from {', '.join(absent)}")
    else:
        print(f"  all {len(label_split)} labels present in all three splits")

    print("\npass 2: verifying value disjointness...")
    values = verify(data_dir, doc_split)
    ok = True
    for a, b in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = values[a] & values[b]
        status = "OK" if not overlap else f"LEAK ({len(overlap):,} shared values)"
        if overlap:
            ok = False
            sample = list(overlap)[:5]
            print(f"  {a} vs {b}: {status}  e.g. {sample}")
        else:
            print(f"  {a} vs {b}: {status}")
    for split in SPLITS:
        print(f"  distinct name/surname/street values in {split}: {len(values[split]):,}")

    if not ok:
        print("\nERROR: split is not disjoint; not writing output.")
        return 1

    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    out_dir = Path(args.out)
    print(f"\npass 3: writing documents to {out_dir} ...")
    write_out(data_dir, out_dir, doc_split)
    print("done. Re-tokenise before training:")
    print(f"  python scripts/retokenize_merged.py --data-dir {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
