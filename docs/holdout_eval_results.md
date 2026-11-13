# Held-out dataset evaluation -- `your-hf-org/masking-multilingual`

Model: `your-hf-org/masking-multilingual` (revision `3a0a6e5df228bdc89dd01312a728e10a78b3e3fb`). Generated from `scripts/eval_holdout_out/eval_results.jsonl` by `scripts/eval_holdout.py --report` -- do not hand-edit. Every number below is recomputed directly from that file (re-running the model's own tokenizer to rebuild BIO tag sequences from the stored gold/predicted character-offset entities -- not re-run through the model itself), not asserted in prose.

**Companion to, not a replacement for, the adversarial results on `redteam/adversarial-eval` (commit `78e8f78`)**: this evaluates typical-case performance on real held-out documents sampled from `data/processed/<lang>/test.docs.jsonl`; that branch hand-builds edge-case stress tests and does not represent typical-case performance.

## Sample sizes

- **Sampling seed:** 20260916
- **Requested per language:** 200

| Language | Documents evaluated | Total gold entities | Total predicted entities |
|---|---|---|---|
| az | 200 | 599 | 615 |
| en | 200 | 687 | 697 |
| tr | 200 | 705 | 721 |
| ru | 200 | 764 | 771 |
| **all** | **800** | **2755** | **2804** |

## Overall (all languages combined)

| Average | Precision | Recall | F1 |
|---|---|---|---|
| micro | 0.9597 | 0.9768 | 0.9682 |
| macro | 0.9589 | 0.9813 | 0.9695 |

## Per-language (micro-averaged across that language's labels)

| Language | Precision | Recall | F1 |
|---|---|---|---|
| az | 0.9577 | 0.9833 | 0.9703 |
| en | 0.9684 | 0.9825 | 0.9754 |
| tr | 0.9556 | 0.9773 | 0.9663 |
| ru | 0.9572 | 0.9660 | 0.9616 |

## Per-label (all languages combined)

| Label | Risk | Precision | Recall | F1 | Support |
|---|---|---|---|---|---|
| ACCESS_TOKEN | high | 0.8511 | 0.9302 | 0.8889 | 43 |
| AGE | low | 0.9853 | 0.9710 | 0.9781 | 69 |
| API_KEY | high | 1.0000 | 1.0000 | 1.0000 | 65 |
| AZ_DRIVER_LICENSE_NUMBER | high | 0.9737 | 1.0000 | 0.9867 | 37 |
| AZ_FIN | high | 1.0000 | 1.0000 | 1.0000 | 50 |
| AZ_ID_CARD_NUMBER | high | 1.0000 | 1.0000 | 1.0000 | 36 |
| AZ_PASSPORT_NUMBER | high | 1.0000 | 1.0000 | 1.0000 | 28 |
| AZ_VOEN | high | 0.9615 | 1.0000 | 0.9804 | 25 |
| BUILDINGNUM | low | 1.0000 | 1.0000 | 1.0000 | 81 |
| CARD_SECURITY_CODE | high | 0.8485 | 1.0000 | 0.9180 | 28 |
| CITY | low | 0.9028 | 0.9701 | 0.9353 | 201 |
| DATE | low | 0.9730 | 0.9153 | 0.9432 | 118 |
| EMAIL | medium | 0.9938 | 0.9969 | 0.9954 | 323 |
| GIVENNAME | medium | 0.9593 | 0.9676 | 0.9634 | 463 |
| IBAN | high | 0.9394 | 0.9688 | 0.9538 | 32 |
| ICCID | medium | 1.0000 | 1.0000 | 1.0000 | 14 |
| IPV4_ADDRESS | medium | 1.0000 | 1.0000 | 1.0000 | 55 |
| IPV6_ADDRESS | medium | 1.0000 | 1.0000 | 1.0000 | 16 |
| MAC_ADDRESS | medium | 1.0000 | 1.0000 | 1.0000 | 33 |
| PAYMENT_CARD_NUMBER | high | 0.9828 | 1.0000 | 0.9913 | 57 |
| PRIVATE_KEY | high | 0.7778 | 0.8750 | 0.8235 | 24 |
| STREET | low | 0.9360 | 1.0000 | 0.9669 | 117 |
| SURNAME | medium | 0.9792 | 0.9676 | 0.9734 | 340 |
| TELEPHONENUM | medium | 0.9170 | 0.9621 | 0.9390 | 264 |
| TIME | low | 0.9886 | 1.0000 | 0.9943 | 87 |
| URL | low | 0.9322 | 0.9821 | 0.9565 | 56 |
| ZIPCODE | low | 0.9892 | 0.9892 | 0.9892 | 93 |

## Comparison to the adversarial (Task 8) findings

Task 8's headline finding (`redteam/adversarial-eval`, commit `78e8f78`): 24/29 `partial_span` failures were the model over-capturing by exactly one trailing character (usually sentence-final punctuation), across 13 labels. seqeval's entity-level scoring here is EXACT-MATCH on both boundaries, so that exact bug -- if it occurs at the same rate on typical held-out text as it did in Task 8's short, punctuation-adjacent stress sentences -- would show up here as reduced precision (over-wide predicted spans) rather than reduced recall (the entity is still found, just not exactly bounded), concentrated on the same labels Task 8 flagged (AZ_DRIVER_LICENSE_NUMBER, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, IBAN, CARD_SECURITY_CODE, ICCID, AGE, BUILDINGNUM, DATE, TELEPHONENUM, IPV6_ADDRESS, URL, ZIPCODE).

| Label (flagged by Task 8) | Precision here | Recall here | Support |
|---|---|---|---|
| AZ_DRIVER_LICENSE_NUMBER | 0.9737 | 1.0000 | 37 |
| AZ_ID_CARD_NUMBER | 1.0000 | 1.0000 | 36 |
| AZ_PASSPORT_NUMBER | 1.0000 | 1.0000 | 28 |
| IBAN | 0.9394 | 0.9688 | 32 |
| CARD_SECURITY_CODE | 0.8485 | 1.0000 | 28 |
| ICCID | 1.0000 | 1.0000 | 14 |
| AGE | 0.9853 | 0.9710 | 69 |
| BUILDINGNUM | 1.0000 | 1.0000 | 81 |
| DATE | 0.9730 | 0.9153 | 118 |
| TELEPHONENUM | 0.9170 | 0.9621 | 264 |
| IPV6_ADDRESS | 1.0000 | 1.0000 | 16 |
| URL | 0.9322 | 0.9821 | 56 |
| ZIPCODE | 0.9892 | 0.9892 | 93 |

*(A precision score here noticeably below that label's recall would be consistent with Task 8's boundary bug generalizing to typical held-out text; support=0 means this sample happened to contain no gold instance of that label and this comparison is inconclusive for it, not evidence either way.)*

## Known methodology limitations

- **Sampled, not exhaustive.** `test.docs.jsonl` holds {az: 10540, en: 10485, tr: 10380, ru: 10237} held-out documents; running the full corpus through the model on CPU was impractical, so a fixed-seed random sample (`--per-lang 200`, seed `20260916`) was used instead. Re-running with the same seed and `--per-lang` reproduces the identical sample.
- **Non-overlapping windows, not sliding.** Documents longer than 512 tokens are split into consecutive non-overlapping chunks (see module docstring), unlike training's overlapping stride-256 windows. An entity that straddles a window boundary loses its `I-` continuation across that boundary and is scored as two shorter spans instead of one -- a real, disclosed source of undercounted recall on long documents, not hidden by sampling only short ones.
- **`data/golden/` was investigated and deliberately excluded** -- it is a frozen regression corpus for the data-generation/translation pipeline with known, intentionally-uncorrected defects, has no `tr` file, and is not a held-out set for model evaluation.
