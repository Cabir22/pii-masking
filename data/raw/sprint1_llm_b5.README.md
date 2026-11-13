# sprint1_llm_b5 — LLM generation batch 5 (D-23e)

**Status (2026-10-08): raw, not yet audited.** Stopped by the team at 21,290 of the requested 27,300 documents (enough for the ~44K clean LLM target with batches 1–4). The first batch with the 4,414-place CITY pool (P2-14), foreign names (P2-15), P2-6's contrast lessons, target cases and layouts, and noisy suffixes. Needs the audit and clean (`clean_llm_batch.py --drop-unplanned-pii`). Do not train on the raw file.

**D-33a (2026-10-10): 21,265 → 21,110 documents.** 106 dashed CVVs that were declared look-alikes (`cvv_separator`, `12-3`) are now labelled CARD_SECURITY_CODE; 5 stay look-alikes because labelling them would fail a gate; 155 documents with a `fin_with_i_or_o` look-alike are dropped (D-33c). Text is unchanged. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b5.clean.jsonl --in-place`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d30b/d33a_relabel_b5.json`.

**D-35b (2026-10-12): 21,110 → 20,956 documents.** 154 documents with a `fin_6_chars` look-alike are dropped (D-34b: a foreign resident's PIN has 5-6 characters). Every kept line is byte-identical. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b5.clean.jsonl --in-place --drop-kind fin_6_chars`; SHA-256 of the new clean file `5de14d3efcf5bceaff6fc8bc25aead03c1ccb6fd41fa1a5b349c5b81b2815ea1`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d31b/d35b_drop_b5.json`.

**D-36a (2026-10-12): 20,956 → 20,954 documents.** OpenSSH public-key lines (`ssh-rsa`, `ssh-ed25519`, ...) are no longer PRIVATE_KEY: 237 labels became declared look-alikes (`public_key_ssh`) and 31 lines the LLM wrapped in PEM PRIVATE KEY armour are labelled as the whole block; 2 document(s) with broken armour or a gate objection dropped; 27 documents now PII-free. Text is unchanged. `python scripts/relabel_ssh_public_keys.py --file data/raw/sprint1_llm_b5.clean.jsonl --in-place`; SHA-256 `f8379019c89b418d34c222af53c21b4cdd0ff4138277f4c874c9765edadc6daa`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d36a/d36a_sprint1_llm_b5.clean.json`.

**D-45b (2026-10-14): 20,954 → 20,931 documents.** 23 document(s) that label one value 20 times or more are dropped (the rule batch 6 was cleaned with; most: TIME 76×, TIME 75×, TIME 58×; 6 of them a name). Every kept line is byte-identical. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b5.clean.jsonl --max-value-repeats 20 --in-place`; SHA-256 `0a5b0e65eba137b19facb5379e28abc1e7706d34ccf4d7f69cfbc2bd49148046`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d45b/d45b_drop_b5.json`.

**D-47 (2026-10-14): 20,931 → 20,351 documents.** 580 dropped: 167 with an explained typo (D-47a), 392 with a bracketed self-correction in a formal doc type (D-47b), 29 with an unfilled template placeholder (D-47e); a document can match more than one rule. Every kept line is byte-identical and in order. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b5.clean.jsonl --drop-explained-typos --drop-formal-self-corrections --drop-placeholders --in-place`; SHA-256 `64047eb557d527b81ff42ab0df84028db465f78ccb61d3062f61fdde8e9e32cc`; validate_corpus PASS, leakage guard CLEAN; ids in `reports/d47/d47_drop_b5.json`.

| | |
|---|---|
| Files | `sprint1_llm_b5.jsonl` (21,290 docs, SHA-256 `bbe2c33a427712bfcd4da06ab0207118ce411cb44d0fcb2f2f192f6b6790a3d2`), `sprint1_llm_b5.rejects.jsonl` (3,456 rejects, SHA-256 `c4fbc1e5b183c4a723443cde817b8be33b7af088fd5ad90018dd15b1db00b4a5`), both Git LFS |
| Generated | 2026-10-07/08, ~14.9 h of generation, `wahoo-1.5-preview`, concurrency 40, seed 20261007; 24,950 attempts, 23,450 API calls, 0 retries |
| Code | started at `f680dbb`; stopped at 1,146 on label drift (contrast lessons) and resumed at `c91c895` (fix); later resumed after an internet drop |

## Generation report
- 21,290 accepted of 24,950 attempts (14.7% rejected). In the rejects file: quality 1,755, leaked unlabelled PII 628, validation 474, judgment leak 279, api 192, taxonomy label 98.
- **The rejects file misses the first 204 rejects:** `--dump-rejects` rewrote it on the first resume (3,456 in the file vs 3,660 = 24,950 − 21,290). Diagnostic only; the accepted file is complete (21,290 unique ids, every line valid JSON).
- Turkish-check rejections stayed low with the new Turkish names (5 in the first 1,146).
