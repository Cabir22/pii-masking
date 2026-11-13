#!/usr/bin/env python3
"""Select the canonical 60,000-record AZ sample shared across the EN/TR/RU
translation tracks -- one fixed set of record IDs, not independent per-language
samples. Read-only against the source corpus: never writes, resizes, or
reorders data/processed/az/{train,val,test}.docs.jsonl.

Method: multi-label iterative stratification (Sechidis, Tsoumakas & Vlahavas,
2011, "On the Stratification of Multi-Label Data"), via the `iterstrat`
package's MultilabelStratifiedShuffleSplit -- the standard, peer-reviewed
approach for drawing a class-balanced subsample when records carry multiple,
overlapping labels (a record with both GIVENNAME and EMAIL must be accounted
for in both label counts at once, which plain per-label random sampling
cannot do consistently). Applied independently within each of train/val/test,
so the original ~80/10/10 split proportions are preserved by construction,
not approximated afterward.

A record's "labels" for stratification purposes are the set of distinct
entity labels present, PLUS a synthetic NEGATIVE label for records with an
empty entities list (~23.5% of the corpus) -- so negatives are proportionally
represented too, not left to chance.

MultilabelStratifiedShuffleSplit does not guarantee an exact requested size
(it prioritizes label-proportion fidelity over hitting a precise count --
confirmed empirically before writing this: 48,050 vs a 48,002 target on the
real train split, a 0.1% overshoot). Each split's near-target selection is
therefore trimmed or padded to its exact target count with a seeded uniform
random adjustment -- small enough (tens of records out of tens of thousands)
that it does not meaningfully perturb the label proportions the stratified
draw already achieved; the verification report shows the distribution
actually delivered, not the pre-adjustment one.

Run: python scripts/select_translation_sample.py
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

ROOT = Path(__file__).resolve().parent.parent
AZ_DIR = ROOT / "data" / "processed" / "az"
SPLITS = ["train", "val", "test"]

TOTAL_TARGET = 60_000
SEED = 42  # matches this repo's existing convention (GeneratorConfig.seed,
           # prepare_splits.py's default split seed) -- documented, fixed,
           # printed below, and reused identically by anyone re-running this.

# Fixed, explicit per-split seed offsets -- NOT Python's built-in hash(str),
# which is randomized per-process (PYTHONHASHSEED) unless disabled, and would
# silently break reproducibility across machines/runs for EN and RU re-running
# this exact script.
SEED_OFFSETS = {"train": 0, "val": 1, "test": 2}

OUT_PATH = ROOT / "data" / "processed" / "shared_translation_sample_60000.jsonl"

NEGATIVE = "NEGATIVE"


def load_split(name: str) -> list[dict]:
    recs = []
    with (AZ_DIR / f"{name}.docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            recs.append(json.loads(line))
    return recs


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def label_set(rec: dict) -> set[str]:
    ents = rec.get("entities") or []
    return {e["label"] for e in ents} if ents else {NEGATIVE}


def build_label_matrix(records: list[dict], all_labels: list[str]) -> np.ndarray:
    idx = {l: i for i, l in enumerate(all_labels)}
    Y = np.zeros((len(records), len(all_labels)), dtype=int)
    for i, rec in enumerate(records):
        for lab in label_set(rec):
            Y[i, idx[lab]] = 1
    return Y


def stratified_select(records: list[dict], target: int, seed: int,
                      all_labels: list[str]) -> list[int]:
    """Indices into `records` for a stratified sample of exactly `target` size."""
    n = len(records)
    Y = build_label_matrix(records, all_labels)
    X = np.zeros((n, 1))  # iterstrat's API wants an X; unused beyond shape

    splitter = MultilabelStratifiedShuffleSplit(
        n_splits=1, train_size=target, test_size=n - target, random_state=seed)
    selected, _ = next(splitter.split(X, Y))
    selected = list(selected)

    rng = random.Random(seed)
    if len(selected) > target:
        drop_n = len(selected) - target
        drop = set(rng.sample(selected, drop_n))
        adjustment = -drop_n
        selected = [i for i in selected if i not in drop]
    elif len(selected) < target:
        need = target - len(selected)
        remaining = [i for i in range(n) if i not in set(selected)]
        add = rng.sample(remaining, need)
        adjustment = need
        selected = selected + add
    else:
        adjustment = 0
    assert len(selected) == target
    return selected, adjustment


def main() -> None:
    print(f"seed = {SEED}")
    print(f"per-split seed offsets = {SEED_OFFSETS} "
          f"(effective seeds: {{s: SEED + offset}})")
    print(f"total target = {TOTAL_TARGET:,}\n")

    # -- 1. load, tracking split membership; hash source files first --------
    before_hashes = {s: file_hash(AZ_DIR / f"{s}.docs.jsonl") for s in SPLITS}
    all_records: dict[str, list[dict]] = {s: load_split(s) for s in SPLITS}
    split_sizes = {s: len(all_records[s]) for s in SPLITS}
    corpus_total = sum(split_sizes.values())
    print("real split sizes (independently loaded):", split_sizes,
          "total:", corpus_total)

    # -- 2. label distribution over the full corpus --------------------------
    canonical_labels = sorted({lab for s in SPLITS for rec in all_records[s]
                               for lab in label_set(rec) if lab != NEGATIVE})
    all_labels = canonical_labels + [NEGATIVE]
    print(f"{len(canonical_labels)} canonical labels + NEGATIVE = "
          f"{len(all_labels)} stratification columns\n")

    entity_mentions = {lab: 0 for lab in all_labels}
    records_with_label = {lab: 0 for lab in all_labels}
    for s in SPLITS:
        for rec in all_records[s]:
            labs = label_set(rec)
            for lab in labs:
                records_with_label[lab] += 1
            if labs != {NEGATIVE}:
                for e in rec["entities"]:
                    entity_mentions[e["label"]] += 1

    # -- 3. exact per-split target sizes, from REAL counts, summing to exactly
    #       TOTAL_TARGET (residual assigned to the largest split to avoid a
    #       rounding shortfall/surplus) --------------------------------------
    raw = {s: TOTAL_TARGET * split_sizes[s] / corpus_total for s in SPLITS}
    targets = {s: round(raw[s]) for s in SPLITS}
    diff = TOTAL_TARGET - sum(targets.values())
    if diff != 0:
        biggest = max(targets, key=lambda s: split_sizes[s])
        targets[biggest] += diff
    assert sum(targets.values()) == TOTAL_TARGET
    print("per-split targets (from real counts, sum forced to exact total):")
    for s in SPLITS:
        print(f"  {s}: {split_sizes[s]:,} real -> target {targets[s]:,} "
              f"({targets[s]/split_sizes[s]:.4%} of that split)")
    print()

    # -- 4. stratified selection per split ------------------------------------
    selected_records: list[dict] = []
    adjustments = {}
    for s in SPLITS:
        idxs, adj = stratified_select(all_records[s], targets[s],
                                      SEED + SEED_OFFSETS[s], all_labels)
        adjustments[s] = adj
        for i in idxs:
            rec = all_records[s][i]
            selected_records.append({"id": rec["id"], "split": s})
    print("trim/pad adjustment applied per split (post-stratification, "
          "to hit the exact target):", adjustments, "\n")

    assert len(selected_records) == TOTAL_TARGET, len(selected_records)

    # -- 5. write output -------------------------------------------------------
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for r in selected_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(selected_records):,} record IDs to {OUT_PATH}\n")

    # -- 6. verification report: counts -----------------------------------------
    by_split_count = {s: sum(1 for r in selected_records if r["split"] == s)
                      for s in SPLITS}
    print("=== VERIFICATION: counts ===")
    print("total selected:", len(selected_records), "(must be 60,000)")
    for s in SPLITS:
        print(f"  {s}: {by_split_count[s]:,}  (target was {targets[s]:,})")
    print()

    # -- 7. verification report: label proportions, before vs after -----------
    sel_by_id = {r["id"]: r["split"] for r in selected_records}
    sel_records_by_split = {s: [] for s in SPLITS}
    for s in SPLITS:
        for rec in all_records[s]:
            if rec["id"] in sel_by_id and sel_by_id[rec["id"]] == s:
                sel_records_by_split[s].append(rec)

    sel_records_with_label = {lab: 0 for lab in all_labels}
    sel_entity_mentions = {lab: 0 for lab in all_labels}
    for s in SPLITS:
        for rec in sel_records_by_split[s]:
            labs = label_set(rec)
            for lab in labs:
                sel_records_with_label[lab] += 1
            if labs != {NEGATIVE}:
                for e in rec["entities"]:
                    sel_entity_mentions[e["label"]] += 1

    print("=== VERIFICATION: per-label proportion, full corpus vs sample "
          "(share of records containing the label at least once) ===")
    print(f"{'label':<28}{'orig %':>10}{'sample %':>10}{'delta (pp)':>12}"
          f"{'orig n':>10}{'sample n':>10}")
    max_abs_delta = 0.0
    flagged = []
    for lab in all_labels:
        orig_pct = 100 * records_with_label[lab] / corpus_total
        samp_pct = 100 * sel_records_with_label[lab] / TOTAL_TARGET
        delta = samp_pct - orig_pct
        max_abs_delta = max(max_abs_delta, abs(delta))
        flag = " <-- FLAG" if abs(delta) > 1.0 else ""
        if flag:
            flagged.append((lab, delta))
        print(f"{lab:<28}{orig_pct:>9.3f}%{samp_pct:>9.3f}%{delta:>+11.3f}pp"
              f"{records_with_label[lab]:>10,}{sel_records_with_label[lab]:>10,}{flag}")
    print()
    print(f"max |delta| across all {len(all_labels)} labels: {max_abs_delta:.4f} pp")
    print("labels flagged (|delta| > 1.0 pp):", flagged if flagged else "none")

    # -- 8. re-hash source files -- must be byte-identical to step 1 -----------
    after_hashes = {s: file_hash(AZ_DIR / f"{s}.docs.jsonl") for s in SPLITS}
    print()
    print("=== source-file integrity check (sha256, before vs after) ===")
    all_unchanged = True
    for s in SPLITS:
        unchanged = before_hashes[s] == after_hashes[s]
        all_unchanged &= unchanged
        print(f"  {s}.docs.jsonl: {'UNCHANGED' if unchanged else 'CHANGED!!'}"
              f"  {after_hashes[s][:16]}...")
    print("ALL SOURCE FILES UNCHANGED:" , all_unchanged)


if __name__ == "__main__":
    main()
