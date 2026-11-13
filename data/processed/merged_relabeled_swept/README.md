# merged_relabeled_swept — the remediation-sprint corpus

**This is the corpus every sprint task uses** (task P1-3):
- Run A's replay (P1-6);
- Run B's training data (P1-12);
- the internal test set and the "new names" slice for every checkpoint (P3-1, P3-4).

It is tracked on `main` through Git LFS, so all three people and the GPU pod use the byte-identical file. `git lfs pull` fetches it.

## What it is

The original four-language corpus, `merged/` (az + en + tr + ru), with two changes and **nothing else**:

1. **Missing surname labels added**, by `scripts/relabel_unlabeled_surnames.py --apply`. The generator wrote real surnames into the text without labelling them. The script added 18,373 SURNAME labels in 12,699 documents, which matches commit `e73108d`.
2. **24 documents with a broken span dropped**, by `scripts/sweep_span_defects.py --drop`. A broken span is one that starts or ends mid-word, 0.006% of the corpus. That removed 21 documents from train, 1 from val and 2 from test.

The **split is the original one**:
- every document stays in the split it had in `merged/`;
- every document stays with its own EN/TR/RU translations.

The value-disjoint re-split (`scripts/regroup_splits.py`, branch `data/merged-disjoint`) was deliberately **not** used. It left the test set almost without names and split 47% of documents from their translations (2026-09-30).

## Files

| File | Documents | az / en / tr / ru | SURNAME labels | SHA-256 |
|---|---|---|---|---|
| `train.docs.jsonl` | 332,888 | 84,333 / 83,807 / 83,016 / 81,732 | 149,328 | `b4c737c162f8374a3eaf098fb614c68839ff7f3210bd2846e33d67e348dfc014` |
| `val.docs.jsonl` | 41,727 | 10,540 / 10,477 / 10,381 / 10,329 | 19,816 | `a4e65ecbcb6e38b0335e115a5459876cdb8a92dbdb3ec357094666b24a8a4379` |
| `test.docs.jsonl` | 41,640 | 10,540 / 10,484 / 10,379 / 10,237 | 19,690 | `ed076c2610797f28b3e00f836d65b278f4884ce27600a0141fc586bfe724df4a` |
| `labels.json` | the 27-label map (identical to `data/processed/labels.json`) | | | `bf9ad4259e2f7476b4bb235a829891bac97aa7f037b7f0012bd159aa3f6fe784` |

Total: 416,255 documents and 188,834 SURNAME labels (`merged/` has 170,492). The files hold document-level records (`*.docs.jsonl`) only. They are not tokenised: tokenise the training mix, not this folder (P1-6).

To check that your copy is this dataset:

```bash
shasum -a 256 data/processed/merged_relabeled_swept/*
```

## How it was verified (2026-09-30)

- `merged/`, the input, is **identical** to the union of the per-language splits committed on `main`: the same 416,279 ids, splits, texts and labels. So this corpus is derived from exactly the committed data.
- Compared with `merged/`:
  - 0 documents changed split;
  - 0 texts changed;
  - the only label change is **+18,357 SURNAME** on the kept documents (the other 16 added labels were on dropped documents);
  - no label was removed.
- All 27 labels are present in every split. 0 of 105,418 translation families span two splits.
- **Checkpoint 1 never saw `test` or `val`.** It was trained on `merged/`: `scripts/benchmark_rebalance.py` calls it the "original production model (trained with AZ-only names)". The unshared checkpoint 2 was trained on `merged_rebalanced/`, which uses the **same split for all 416,279 ids**. So checkpoint 1, Run A, Run B and checkpoint 2 can all be scored on this test set.

## How to rebuild it (only to verify; the result must match the SHA-256s above)

```bash
python scripts/merge_languages.py
python scripts/relabel_unlabeled_surnames.py --data-dir data/processed/merged --apply
python scripts/sweep_span_defects.py --data-dir data/processed/merged_relabeled \
    --out data/processed/merged_relabeled_swept --drop
```

Ignore the relabel script's closing hint to run `regroup_splits.py`: that step was dropped.
