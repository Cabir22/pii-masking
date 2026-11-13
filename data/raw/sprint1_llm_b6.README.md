# sprint1_llm_b6 — LLM generation batch 6 (D-38, D-39b, D-42c)

**P2-5 audit and clean (2026-10-14): 24,000 → 23,977 documents.** Use `sprint1_llm_b6.clean.jsonl` (SHA-256 `7b3a8cb252b12c47302148cc973fc77aab4cb9a7fe916c1ca2780893c29c49f5`, Git LFS). Dropped 23: 13 decoy integrity (noise changed a look-alike), **7 with one value labelled 20 times or more** (new `--max-value-repeats 20`; `llm_az_000599`'s 51 IPv6 addresses, logs and schedules repeating one time 21–75 times), 1 `not_nfc`, 1 `resolver_drift`, 1 benchmark 8-gram (`llm_az_016136`). Every kept line is byte-identical to the raw file. The date relabel, D-33a (dashed CVVs), D-35b (`fin_6_chars`) and D-36a (OpenSSH keys) change nothing here. `python scripts/clean_llm_batch.py data/raw/sprint1_llm_b6.jsonl --drop-unplanned-pii --max-value-repeats 20` (`reports/llm_batch6/run_pipeline.sh`); validate_corpus PASS, leakage guard CLEAN, audit: 0 unlabelled planned values, 0 invented PII, no look-alike problems.

**D-47 (2026-10-14): 23,977 → 22,832 documents.** 1145 dropped: 208 with an explained typo (D-47a), 886 with a bracketed self-correction in a formal doc type (D-47b), 62 with an unfilled template placeholder (D-47e), and `llm_az_001904`, listed by the leakage guard's new real-text barrier (D-46c; hash only); a document can match more than one rule. Every kept line is byte-identical and in order. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b6.clean.jsonl --drop-explained-typos --drop-formal-self-corrections --drop-placeholders --drop-id llm_az_001904 --in-place`; SHA-256 `43ec88f71ba4aa7caa86c0a4309b3d94f618c89a438327feb12bbb257946f14c`; validate_corpus PASS, leakage guard CLEAN; ids in `reports/d47/d47_drop_b6.json`.

**Status (2026-10-14): raw, not yet audited.** 24,000 documents in the eight published-text and legal genres (D-38 option 2, raised from 12,000 by the team on 2026-10-13). Needs the audit and clean (`clean_llm_batch.py --drop-unplanned-pii`) and the native read of about 50 documents before the `runb-az-v3` build. Do not train on the raw file.

| | |
|---|---|
| Files | `sprint1_llm_b6.jsonl` (24,000 docs, SHA-256 `28a438044fdc59f1ef5648e925ff905579cfd1e14ef6def0c43c4b22c98ce31a`), `sprint1_llm_b6.rejects.jsonl` (3,230 rejects, all three runs, SHA-256 `faca4d2cd4b723d9692b134217a3a3a93ca948b6291e7258f890ffa6841093d8`), both Git LFS |
| Command | `llm_augment_data.py --model wahoo-1.5-preview --concurrency 40 --seed 20261013 --hard-negative-rate 0.3 --adversarial-rate 0.2 --negative-only-rate 0.1 --edge-case-rate 0.3 --doc-types news_article,press_release,official_notice,procurement_announcement,court_announcement,legal_notice,government_form,court_filing --dump-rejects` |
| Generated | 2026-10-13/14, about 18.8 h in three runs; 27,230 attempts, 0 API retries |

## Three runs, two code versions

| Run | When | Documents | Code |
|---|---|---|---|
| 1 | 10-13 ~12:00–13:12 | 1–1,777 | `main` before D-40b and D-42c: D-39b name constructions and D-40a fathers, but the old name pools, no bracketed phones, no bare ZIPs, no D-41a/D-42c look-alike kinds. **Stopped on label drift:** one court filing (`llm_az_000599`) repeats one IPv6 address 51 times (IPv6 at 3.3x its target) |
| 2 | 10-13 14:40–21:47 | 1,778–about 9,400 | `1e97694`: D-43e (a value repeated in one document counts once in the label mix), D-40b pools, D-41a CVV look-alikes, D-42c (bracketed phones 12% of az phones, bare ZIPs 25% of az ZIPs, new look-alike kinds), D-43c. Stopped by the team to raise `-n` to 24,000 |
| 3 | 10-13 21:50–10-14 08:19 | about 9,400–24,000 | `2ee9cb4` (same generator code as run 2) |

So about 22,200 of the 24,000 documents carry the D-42c shapes.

## Generation report

- 24,000 accepted of 27,230 attempts (11.9% rejected). Rejects: quality 2,214, validation 375, leaked unlabelled PII 279, judgment leak 249, taxonomy label 56, no entities resolved 38, api 17, missing values 2. The rejects file is complete (`--dump-rejects` rewrites it on a resume, so the three runs' files were joined).
- Every line is valid JSON; 24,000 unique ids.
- Genres: press_release 3,179, procurement_announcement 3,150, news_article 3,096, legal_notice 2,997, government_form 2,967, court_filing 2,929, official_notice 2,876, court_announcement 2,806.
- 125,484 labels; 2,358 documents with none. **Names dominate:** GIVENNAME 36,410 and SURNAME 25,367 (49% of all labels), then DATE 12,005, EMAIL 7,358, TELEPHONENUM 6,028, CITY 5,647. Mostly by design (D-39b name lists and patronymics, left out of the steered mix), but worth a look in the audit and in v3's label balance.

## For the audit

- `llm_az_000599`: a log that repeats one IPv6 address 51 times. Valid and labelled, but low value; decide whether to drop or cap documents that repeat one value that many times.
- The first 1,777 documents predate D-40b, D-41a and D-42c (see above).
