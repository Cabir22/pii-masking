# sprint1_llm_b1 — LLM generation batch 1 (task P1-5)

**Status (2026-10-05): audited and cleaned (PR #11, D-15), re-cleaned with the batch-4 checks (P2-5 batch 4). Train only on `sprint1_llm_b1.clean.jsonl` (5,133 documents).** It was built with `python scripts/clean_llm_batch.py data/raw/sprint1_llm_b1.jsonl --drop-unplanned-pii`; validate_corpus PASS, leakage guard CLEAN. Drop reasons are in `sprint1_llm_b1.clean.report.json`. The raw file below is kept unchanged.

**D-33a (2026-10-10): 5,115 → 5,080 documents.** 18 dashed CVVs that were declared look-alikes (`cvv_separator`, `12-3`) are now labelled CARD_SECURITY_CODE; 35 documents with a `fin_with_i_or_o` look-alike are dropped (D-33c). Text is unchanged. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b1.clean.jsonl --in-place`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d30b/d33a_relabel_b1.json`.

**D-35b (2026-10-12): 5,080 → 5,058 documents.** 22 documents with a `fin_6_chars` look-alike are dropped (D-34b: a foreign resident's PIN has 5-6 characters). Every kept line is byte-identical. `python scripts/relabel_dashed_cvv.py --batch data/raw/sprint1_llm_b1.clean.jsonl --in-place --drop-kind fin_6_chars`; SHA-256 of the new clean file `5bdbe601c46f868d9e246894215b31d862777f0fb4b6f50536ef73762bd6ceb2`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d31b/d35b_drop_b1.json`.

**D-36a (2026-10-12): 5,058 → 5,057 documents.** OpenSSH public-key lines (`ssh-rsa`, `ssh-ed25519`, ...) are no longer PRIVATE_KEY: 43 labels became declared look-alikes (`public_key_ssh`) and 21 lines the LLM wrapped in PEM PRIVATE KEY armour are labelled as the whole block; 1 document(s) with broken armour or a gate objection dropped; 7 documents now PII-free. Text is unchanged. `python scripts/relabel_ssh_public_keys.py --file data/raw/sprint1_llm_b1.clean.jsonl --in-place`; SHA-256 `24313bef7d60337c01c6762d1475db76a4bed6db6bb83acee48d4fe504efe08b`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d36a/d36a_sprint1_llm_b1.clean.json`.

**D-45b (2026-10-14): 5,057 → 5,055 documents.** 2 document(s) that label one value 20 times or more are dropped (the rule batch 6 was cleaned with; most: DATE 34×, GIVENNAME 20×; 1 of them a name). Every kept line is byte-identical. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b1.clean.jsonl --max-value-repeats 20 --in-place`; SHA-256 `ffadd4ec0f6d198d91585c12451b7e62c208c9614676751852ef647213aa61df`; validate_corpus PASS, leakage guard CLEAN; counts in `reports/d45b/d45b_drop_b1.json`.

**D-47 (2026-10-14): 5,055 → 4,874 documents.** 181 dropped: 43 with an explained typo (D-47a), 123 with a bracketed self-correction in a formal doc type (D-47b), 19 with an unfilled template placeholder (D-47e); a document can match more than one rule. Every kept line is byte-identical and in order. `python scripts/drop_before_v3.py data/raw/sprint1_llm_b1.clean.jsonl --drop-explained-typos --drop-formal-self-corrections --drop-placeholders --in-place`; SHA-256 `9bdf7094c0ae5c8c0d0f48a13eee862500e5d211b5b67bd5f0e1fc171c970399`; validate_corpus PASS, leakage guard CLEAN; ids in `reports/d47/d47_drop_b1.json`.

**D-17 (2026-10-04):** standalone dates are labelled DATE in this clean file (`scripts/relabel_standalone_dates.py --in-place`; timestamps excluded): DATE labels 613 -> 4,210, 0 standalone dates left; validate_corpus PASS, leakage guard CLEAN. Relabelled again with the batch-3 audit's rule (P2-5 batch 3, D-18d): DATE 4,210 -> 4,212 (3 en-dash or dd.mm.yy dates added, 1 removed from log timestamps with a malformed time such as `09:122`); validate_corpus PASS, leakage guard CLEAN.

**Re-cleaned on 2026-10-05 with the batch-4 audit's checks**, from the raw file: 5,191 → 5,133. Removed: 44 with an invented email the old leak sweep missed (Azerbaijani letters or an underscore, `dəstək@hal-x.ai`), 9 with corrupt text (a foreign-script letter such as `な`, or the brief's `(noise)` copied into the text), 6 with a planned name misspelt inside the word and left unlabelled (`Abubkrov` for `Abubəkrov`). One document comes back (`llm_az_000330`): its only unlabelled copy of a planned date sits in a log timestamp, which D-17 does not label. Every other line is byte-identical to the previous file. Dates relabelled with the same rule: DATE 605 → 4,159, 0 left; validate_corpus PASS, leakage guard CLEAN.

Re-cleaned on 2026-10-03 with the batch-2 audit's checks: 5,201 → 5,191. The 10 documents removed have a planned date written in another format and left unlabelled (`14.05.2015` as `2015-05-14`). The 5,191 kept lines are byte-identical to the earlier file.

| | |
|---|---|
| Files | `sprint1_llm_b1.jsonl` (accepted, 6,000 docs, SHA-256 `1203e6a5dbd78eb935ef3af0d7743c23dfc151f00f9fff134b031e263caf313e`), `sprint1_llm_b1.rejects.jsonl` (5,015 rejected candidates with reasons, SHA-256 `c2dcd3e80abcf38a25bb1b9af83cdb03433b96b0235a31172042533abe2f97da`) — both Git LFS |
| Generated | 2026-10-02 → 03, 5.9 h, model `wahoo-1.5-preview`, concurrency 32 |
| Code | `_gen_version` = `c3e7de3b39f5` (main with the leak screen) |
| Command | `python scripts/llm_augment_data.py --model wahoo-1.5-preview -n 6000 --concurrency 32 --seed 20261002 --hard-negative-rate 0.3 --adversarial-rate 0.2 --negative-only-rate 0.1 --edge-case-rate 0.3 --output data/raw/sprint1_llm_b1.jsonl --dump-rejects` (resumed once after the drift-monitor fix `d0e7f1d`) |
| Batch plan | 4 batches of 6,000 (seeds 20261002, 20261003, 20261004, 20261005; files `sprint1_llm_b1…b4.jsonl`), each audited before the next |

## Measured on 2026-10-03
- `eval/leakage_guard.py … --bench-docs data/benchmark_v3/…`: **CLEAN** (0 benchmark values, 0 benchmark 8-grams, 0 shadow hits).
- `scripts/validate_corpus.py`: **FAIL**, 2 blocking checks:
  - `validator_failure` 33 — language check ("only N az words") on very short / log-like documents;
  - `resolver_drift` 7 — all-caps abbreviated streets (`MIKAYIL ƏLIYEV PR.`) the resolver cannot re-find.
- **Unlabelled planned values: 89 documents.** The LLM inflected a planned value (`Vaqif Məmmədov küç.` → `küçəsində`, `İsaq` → `İsağın`, `Hacıqabul` → `Hacıqabılda`); the resolver did not match it, the label was dropped, and the real value stays in the text **unlabelled** (STREET 53, SURNAME 17, GIVENNAME 12, CITY 6, ACCESS_TOKEN 1). Not caught by any gate today.
- Generation report: 45.5% of attempts rejected (quality 21.5%, leaked unlabelled PII 9.5%, judgment leak 7.0%, validation 4.6%); hard-negative docs 24.6% (target 30%), PII-free 7.5% (target 10%); IPv6/ICCID/MAC ~2× target share (edge-case targeting); password-keyword share 21.4% (cap 12%).
