# Known issues

Bugs that came into `main` with the 2026-09-28 branch consolidation. They are
**recorded here, not fixed**: the consolidation deliberately changed no
behaviour. Each needs its own follow-up PR. Every entry was re-checked against
the merged code before being written down. Background: the work of
2026-09-16 (multi-format audit), 2026-09-21 (red-team probes)
and 2026-09-28 (benchmark extraction).

## 1. Excel: a real header row is taken for data, and the first data row ships in plaintext

**Where:** `formats/excel_format.py::_looks_like_data_row`.

The function treats a row as data if **any** cell passes any structured-label
validator. `AZ_FIN` is 7 alphanumeric characters with no checksum, so ordinary
7-letter header words pass it. The real header row is then disqualified, the
first data row is used as the header, and that row is written to the "masked"
workbook in plaintext.

**Reproduce:** `_looks_like_data_row` on `["First name", "Surname", "City",
"Building"]` returns `True`. Checked: all 12 of `Surname`, `Address`,
`Payment`, `Manager`, `Balance`, `Message`, `Partner`, `Subject`, `Channel`,
`Created`, `Updated`, `Deleted` pass on their own. (`["Ad", "Soyad", "Şəhər",
"Bina"]` does not.)

## 2. CSV: no headerless-file handling; a headerless CSV ships its first record in plaintext

**Where:** `formats/csv_format.py::extract`.

Line 1 is always consumed as the header (`raw_header = next(raw_reader)`).
None of the Excel pipeline's `_detect_header_row`, `_looks_like_data_row` or
`_promote_unclassified_columns` exist in `csv_format.py`, so there is also no
column-consensus promotion. A CSV without a header row has its first record
treated as column names and never masked.

## 3. pii_guard: invisible Unicode inside a value defeats every regex detector

**Where:** `scripts/pii_guard/detect/patterns.py`, `detect/anchored.py`.

A zero-width space (U+200B), zero-width joiner (U+200D) or soft hyphen
(U+00AD) inside an email, card number, IBAN, phone number or FIN stops the
regex from matching, and nothing strips or normalises format characters
first. Reproduced by `redteam/rt2_invisible_chars.py`.

## 4. pii_guard: `strict=False` silently drops a whole detector tier

**Where:** `scripts/pii_guard/detect/__init__.py::HybridDetector.detect`.

Every tier is wrapped in `except Exception: if self.config.strict: raise`.
With `strict=False` the exception is swallowed with no log line, so one
failure in `detect/anchored.py` removes all five anchor_required labels (DATE,
TIME, AGE, BUILDINGNUM, CARD_SECURITY_CODE) for the whole document without any
trace.
`redteam/rt5_strict_false_failopen.py`.

## 5. pii_guard: the fail-closed self-check is Unicode-normalisation-blind

**Where:** `scripts/pii_guard/logging_.py::value_present`.

`value_present()` compares raw strings. `mask.py::_norm_key` already
NFKC-normalises for coreference, but `_assert_clean` / `assert_no_raw_pii`
go through `value_present`, so an NFD copy of an NFC vault value is not
recognised as the same value. Today the model's tokenizer happens to fold NFD
to NFC first, which masks the problem; that is a side effect, not a guarantee.
`redteam/rt1_unicode_normalization.py`.

## 6. ACCESS_TOKEN: the regex tier only knows JWTs

**Where:** `scripts/pii_guard/detect/patterns.py`.

The ACCESS_TOKEN pattern is `\beyJ…\.…\.…` (a JWT). Verified against the
5000-document benchmark (`benchmarks/extracted/errors.csv`): all 385 gold
ACCESS_TOKEN values use `at_` (152), `bearer_` (132) or `tok_` (101) prefixes
and none is a JWT, so nothing in the regex tier covers them. The API_KEY
pattern (`AKIA`/`ASIA`, `sk_`/`pk_`/`rk_`, `sk-`, `ghp_`, `glpat-`, `xox…-`)
does not match them either. The training corpus has the same gap: all 15,455
training ACCESS_TOKEN values are JWT-shaped.

## Other pre-existing issues found during the consolidation

Not introduced by the merge; recorded so they are not rediscovered.

- **`scripts/test_100k_readiness.py` fails on every branch** with
  `KeyError: 'text'` in section 10: golden-corpus entities carry no
  precomputed `text` field.
- **`model/test_masking.py` depends on an untracked file**,
  `data/processed/merged/labels.json`. Only `data/processed/labels.json` is in
  git, so the test fails on any fresh checkout.
- **`scripts/pii_guard/ocr.py` imports `rapidocr_onnxruntime`**, which no
  `requirements.txt` declares. The DOCX round-trip tests crash without it.
- **`scripts/pii_guard/test_pii_guard.py` has one failing assertion**,
  "the actual name right after 'My' is still caught" (already failing on
  `mask/docx` before the merge).
- **`data/testing_samples/translate_input/en_output.repair_queue.jsonl`** is an
  empty plain file inside the LFS-tracked `data/**/*.jsonl` pattern (git-lfs
  does not convert empty files). Harmless, but it is the one `.jsonl` there
  that is not an LFS pointer.
