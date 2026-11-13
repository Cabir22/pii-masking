# merged_relabeled_swept_dated — the sprint corpus with D-17's dates

`merged_relabeled_swept/` (the sprint corpus, P1-3) with **one change**: every
**standalone date** is labelled DATE, as D-17 decided ("follow the benchmark":
dates in prose, after `Tarix:`/`Date:`/`Дата:`, in tables, in every format).
A **date followed by a time** (a log or record timestamp) is not labelled, and
the 180 DATE labels the corpus had on such timestamps are removed.

Built the way P1-3 relabelled surnames, deterministically, by
`scripts/relabel_standalone_dates.py` (the definition is `scripts/piigen/standalone_dates.py`,
the same one generation now enforces):

```bash
python scripts/relabel_standalone_dates.py --data-dir data/processed/merged_relabeled_swept \
    --out data/processed/merged_relabeled_swept_dated --report reports/d17_dates/corpus_relabel.json
```

Texts, ids, splits and every other label are unchanged. A document that gains no label is written back byte for byte.

## Before and after

| | `merged_relabeled_swept` | this folder |
|---|---|---|
| documents | 416,255 | 416,255 (the same) |
| DATE labels | 58,922 | **286,625** |
| unlabelled standalone dates | 227,999 in 159,026 documents (38.2%) | **116 in 112** (0.03%) |
| DATE labels on a timestamp | 180 | 0 |

227,883 DATE spans added, 180 removed, in 159,038 documents. By language: en 40,991, az 39,841, tr 39,666 and ru 38,540 documents changed.

| DATE labels | az | en | tr | ru |
|---|---|---|---|---|
| train | 12,003 → 57,605 | 11,859 → 58,902 | 11,615 → 56,707 | 11,405 → 55,228 |
| val | 1,544 → 7,077 | 1,527 → 7,275 | 1,498 → 7,025 | 1,494 → 7,069 |
| test | 1,523 → 7,441 | 1,515 → 7,642 | 1,488 → 7,394 | 1,451 → 7,260 |

The 116 dates left unlabelled could not be labelled without breaking a gate:
- 110 are not self-signalling (an ISO date with `/`, or an English or Russian worded date with a suffix), and no Azerbaijani anchor word is near them, so `validate_corpus` would report `missing_anchor`;
- 6 are the same date string as a timestamp in the same document, where the record would drift.

## How it was checked

- **Every added span** passes, on its own, each check the gates apply to a DATE span: a valid value, an anchor or a self-signalling shape, not a structural number, and re-placed exactly by the resolver.
- **Every changed document** fails no per-record gate it did not fail before: repeat-mention, resolver drift, span boundary, anchor, and `validate_example`.
- **`validate_corpus.py`** cannot read the original folder as it is: 49% of its entities have no `text` (A9). So it was run on the **test split**, before and after, with `text` filled in from the offsets and nothing else changed. No check got worse, and `unlabelled_standalone_date` fell to ~0. See `reports/d17_dates/corpus_test_validate_before_after.txt`.
- **The leakage guard** (`--bench-docs benchmark_v3`) on all three files: see `reports/d17_dates/corpus_leakage_guard_after.txt`. The relabel never changes text, which is all the guard reads.

**Results (test split, 41,640 documents):** no check got worse; `unlabelled_standalone_date` went from 15,873 documents to 16.

| check | before | after |
|---|---|---|
| unlabelled_standalone_date (informational) | 15,873 | 16 |
| no_entities | 7,377 | 4,868 |
| planned_value_unlabelled | 425 | 381 |
| resolver_drift | 4,169 | 4,159 |
| missing_anchor | 5,764 | 5,763 |
| repeat_mention_incomplete | 96 | 95 |
| validator_failure, unlabeled_pii_leak, exact_duplicate_text | 31,421 / 1,441 / 5 | the same |

The other failures were already there (A9). The relabel neither adds to them nor fixes them, apart from the drops above:
- planned dates written in another format are now labelled;
- 2,509 documents that had no label carry a standalone date and are now labelled.

**Leakage guard** on all three files (416,255 documents): **CLEAN** (0 benchmark values, 0 8-grams, 0 shadow hits).

**PII-free documents.** 2,509 of the test split's zero-entity documents contain a standalone date, so they are no longer PII-free. That is what D-17 says, but the "PII-free document FP rate" (A6) is measured on documents without labels. The team should know that this set shrinks.

## Note for the internal test set

The test split's DATE gold goes from 5,977 to 29,737 labels. A checkpoint scored on the old split was penalised for every standalone date it found. Compare checkpoints on the same version of the split.

## D-36a (2026-10-12): OpenSSH public-key lines are look-alikes

`checksums.private_key_valid` no longer accepts `ssh-rsa` / `ssh-ed25519` / `ssh-dss` / `ecdsa-sha2-` lines, so their PRIVATE_KEY labels became declared look-alikes (`_decoys`, kind `public_key_ssh`), in every language and split, by `scripts/relabel_ssh_public_keys.py`. A line the text wraps in PEM PRIVATE KEY armour is labelled as the whole block; documents with broken armour or a gate objection are dropped; a document left without labels is declared `_pii_free: true`. Text is unchanged; untouched documents are byte for byte the same.

| Split | Documents | Look-alikes | Grown to the block | Now PII-free |
|---|---|---|---|---|
| train | 332,888 → 332,882 | 4,013 | 87 | 384 |
| val | 41,727 → 41,727 | 544 | 12 | 50 |
| test | 41,640 → 41,640 | 572 | 13 | 50 |

The Azerbaijani share v3 uses (not on the drop list) passes `validate_corpus` in each split (train 72,151, val 8,979, test 8,935; entity `text` filled in from offsets, A9); the leakage guard on all three files is CLEAN. **Internal test set:** 572 PRIVATE_KEY labels in the test split are look-alikes now and 13 grew; compare checkpoints on the same version of the split.

## Files

| File | Documents | SHA-256 |
|---|---|---|
| `train.docs.jsonl` | 332,882 | `8fd3423c7f1cb08be3b53103b805ea14adbedfaba492d09a45e4ec1f6152922e` (D-36a) |
| `val.docs.jsonl` | 41,727 | `78af058e3be2e50302d0d22b892b855e960b9dd2f6748de3e8e1d598798966d2` (D-36a) |
| `test.docs.jsonl` | 41,640 | `fdbce3ed012b12057824e8b558ad0e204e3881f9881c9b119a03ab5c6be31d52` (D-36a) |
| `labels.json` | byte copy of the source folder's (its hash depends on the checkout's line endings) | |

The input matched the SHA-256s in `merged_relabeled_swept/README.md`. Rebuilt a second time from scratch: the same three SHA-256s.
