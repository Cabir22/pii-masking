# sprint1_llm_b2 — LLM generation batch 2 (task P1-5)

**Status (2026-10-05): audited and cleaned (P2-5, batch 2; D-15c), re-cleaned with the batch-4 checks (P2-5 batch 4). Train only on `sprint1_llm_b2.clean.jsonl` (5,779 documents).** It was built with `python scripts/clean_llm_batch.py data/raw/sprint1_llm_b2.jsonl --drop-unplanned-pii`; validate_corpus PASS, leakage guard CLEAN. Drop reasons are in `sprint1_llm_b2.clean.report.json`. The raw file below is kept unchanged.

**D-33a (2026-10-10): 5,775 → 5,726 documents.** 37 dashed CVVs that were declared look-alikes (`cvv_separator`, `12-3`) are now labelled CARD_SECURITY_CODE; 49 documents with a `fin_with_i_or_o` look-alike are dropped (D-33c). Text is unchanged. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b2.clean.jsonl --in-place`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d30b/d33a_relabel_b2.json`.

**D-35b (2026-10-12): 5,726 → 5,684 documents.** 42 documents with a `fin_6_chars` look-alike are dropped (D-34b: a foreign resident's PIN has 5-6 characters). Every kept line is byte-identical. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b2.clean.jsonl --in-place --drop-kind fin_6_chars`; SHA-256 of the new clean file `6cc0b93c6008ffe8a3754747b2ded5487ef6ed575be330e39c86c1a1881a3299`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d31b/d35b_drop_b2.json`.

**D-36a (2026-10-12): 5,684 → 5,684 documents.** OpenSSH public-key lines (`ssh-rsa`, `ssh-ed25519`, ...) are no longer PRIVATE_KEY: 73 labels became declared look-alikes (`public_key_ssh`) and 8 lines the LLM wrapped in PEM PRIVATE KEY armour are labelled as the whole block; 0 document(s) with broken armour or a gate objection dropped; 12 documents now PII-free. Text is unchanged. `python scripts/relabel_ssh_public_keys.py --file data/raw/sprint1_llm_b2.clean.jsonl --in-place`; SHA-256 `511975271dae0415d3b21cd7fd6a8f389ee5049caed5a5e1323dc68fcd08c621`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d36a/d36a_sprint1_llm_b2.clean.json`.

**D-45b (2026-10-14): 5,684 → 5,679 documents.** 5 document(s) that label one value 20 times or more are dropped (the rule batch 6 was cleaned with; most: GIVENNAME 31×, TIME 31×, MAC_ADDRESS 28×; 2 of them a name). Every kept line is byte-identical. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b2.clean.jsonl --max-value-repeats 20 --in-place`; SHA-256 `d668af24f84551b198ef78de80d01d962e0439447494c1b3a9aa72363bdf6dba`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d45b/d45b_drop_b2.json`.

**D-47 (2026-10-14): 5,679 → 5,480 documents.** 199 dropped: 56 with an explained typo (D-47a), 133 with a bracketed self-correction in a formal doc type (D-47b), 18 with an unfilled template placeholder (D-47e); a document can match more than one rule. Every kept line is byte-identical and in order. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b2.clean.jsonl --drop-explained-typos --drop-formal-self-corrections --drop-placeholders --in-place`; SHA-256 `683fdbb932afc38699098db756d007140e4f877c580cdf91886d8b22733930fe`; validate_corpus PASS, leakage guard CLEAN; ids in `reports/d47/d47_drop_b2.json`.

**D-17 (2026-10-04):** standalone dates are labelled DATE in this clean file (`scripts/relabel_standalone_dates.py --in-place`; timestamps excluded): DATE labels 788 -> 4,427, 0 standalone dates left; validate_corpus PASS, leakage guard CLEAN. Re-cleaned first: 5,803 -> 5,802, dropping `llm_az_005577` (a misspelled planned city, D-16c). Relabelled again with the batch-3 audit's rule (P2-5 batch 3, D-18d): DATE 4,427 -> 4,428 (6 en-dash or dd.mm.yy dates added, 5 removed from log timestamps with a malformed time such as `09:122`); 2 dates left without an anchor; validate_corpus PASS, leakage guard CLEAN.

**Re-cleaned on 2026-10-05 with the batch-4 audit's checks**, from the raw file: 5,802 → 5,779. Removed: 10 with an invented email the old leak sweep missed (Azerbaijani letters or an underscore, `dəstək@hal-x.ai`), 6 with corrupt text (a foreign-script letter such as `な`, or the brief's `(noise)` copied into the text), 8 with a planned name misspelt inside the word and left unlabelled (`Heydrov` for `Heydərov`). One document comes back (`llm_az_003980`): its only unlabelled copy of a planned date sits in a log timestamp, which D-17 does not label. Every other line is byte-identical to the previous file. Dates relabelled with the same rule: DATE 783 → 4,390, 2 left without an anchor; validate_corpus PASS, leakage guard CLEAN.

The 198 dropped at the first clean: 162 with PII the model invented, 32 with a planned value left unlabelled (31 dates in another format, 1 misspelled city), 2 with a decoy copied wrong, 2 that noise broke after labelling. The "DATE dropped by the model (30)" below was not dropped but reformatted (`1991-09-14` as `14.09.1991`).

| | |
|---|---|
| Files | `sprint1_llm_b2.jsonl` (accepted, 6,000 docs, SHA-256 `db102eae040b205544e459216796773df408a5944be77601f62f4a027a5459c9`), `sprint1_llm_b2.rejects.jsonl` (708 rejected candidates with reasons, SHA-256 `6e7c76565e4de8fc4c6e8234cdc53753cfac855794f0a6e7773a05578fd29288`), both Git LFS |
| Generated | 2026-10-03, 4.8 h, model `wahoo-1.5-preview`, concurrency 32, from `main` @ `14e1626` (PR #11's fixes) |
| Command | `python scripts/llm_augment_data.py --model wahoo-1.5-preview -n 6000 --concurrency 32 --seed 20261003 --hard-negative-rate 0.3 --adversarial-rate 0.2 --negative-only-rate 0.1 --edge-case-rate 0.3 --output data/raw/sprint1_llm_b2.jsonl --dump-rejects` |

## Generation report (from the run)
- 6,000 accepted of 6,708 attempts: **10.6% rejected** (batch 1: 45.5%). Validation 5.1% (mostly "only N az words"), leaked unlabelled PII 2.3%, judgment leak 1.3%, quality 1.0%, taxonomy label 0.5%.
- Docs with hard negatives 33.7%, adversarial 18.7%, PII-free (zero-entity) 9.8%, password-keyword share 0.1%.
- Planned labels dropped by the model: DATE 3.5% of planned (30), others ≤ 0.1%.
- Run-monitor warnings (not stops): validator_failure_rate 5.4%, english_contamination 3.7%, label_share_drift_high 1.79 (IPv6/ICCID/MAC above target, as in batch 1).
