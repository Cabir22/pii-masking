# DOCX testing samples

200 `.docx` documents (100 corpus-derived + 100 freshly generated) for
`mask/docx` (and any other DOCX-adapter work) format testing, split evenly
25/25/25/25 across az/en/tr/ru in both halves (100/100 overall). Built by
`scripts/gen_docx_test_samples.py`; verified by
`scripts/test_docx_test_samples.py`. Every file, its language, its source,
and its gold entity list (label + character offsets) is in `manifest.json`.

Mirrors the existing `txt/`/`excel/`/`pdf/` batches in this directory: one
half pulled verbatim from the real corpus, one half freshly authored with
real minted PII, both halves offset-labelled.

## `corpus_<lang>_NNN.docx` (100, 25/language)

One real record per file, inserted **verbatim** into a single Word
paragraph (multi-line source text is preserved via Word soft line breaks --
`run.add_break()` -- not separate paragraphs, so `python-docx`'s
`paragraph.text` reconstructs the exact original string and the source
`start`/`end` offsets apply unchanged):

- `corpus_az_NNN.docx` -- from `test_samples.jsonl` on `excel-txt` (the
  200-doc Wahoo-generated Azerbaijani batch, also used as the source for
  `pdf/json_az_*.pdf`).
- `corpus_en_NNN.docx` / `corpus_tr_NNN.docx` / `corpus_ru_NNN.docx` -- from
  `translate_input/{en,tr,ru}_output.jsonl` (the real EN/TR/RU translations
  of a 50-document subset of that same 200-doc AZ batch).

25 records were sampled per language (fixed seed, `--seed 1337`) out of the
available pools: 200 AZ / 50 EN / 48 TR / 48 RU (TR and RU are each missing
2 of 50 -- excluded for failing translation validation at generation time,
per that batch's own commit history). None of the sampled records had zero
gold entities (checked: 0 zero-entity records in any of the 4 source
files), so no exclusion was needed on that account.

**`az_group_ids.json`**, sitting alongside `test_samples.jsonl` in
`data/testing_samples/`, is *not* a near-duplicate or quality grouping --
verified directly: it is exactly the 50 of the 200 AZ ids that were **not**
selected for translation (the other 150 partition cleanly into the EN/TR/RU
`translate_input` sets, 50 each, all four groups pairwise disjoint and
covering all 200). It only records which AZ documents were held back from
translation, so it did not constrain which AZ ids this batch draws from --
the 25 AZ picks here are sampled from the full 200, regardless of whether a
given id was also translated elsewhere.

## `new_<lang>_NNN.docx` (100, 25/language)

5 document templates (HR onboarding memo, travel/ID verification form,
bank loan application, IT/security incident report, delivery note) x 5
value-variations each x 4 languages, collectively covering all 27 taxonomy
labels (verified programmatically -- see Verification below). No corpus
text is reused; every sentence is freshly authored per language.

Every PII value is minted through `piigen.values.ValueFactory` (never
invented inline): checksum-valid where a checksum exists (Luhn cards,
mod-97 IBANs, Luhn ICCIDs), real-format for `AZ_*` labels, and screened
against `scripts/piigen/blocklist.py`. Gold spans are recorded through
`piigen.text.TextBuilder` at the moment each value is written into the
document -- never recovered afterwards by searching the assembled text, per
this repo's standing invariant (see `piigen/text.py`'s module docstring).

**GIVENNAME/SURNAME/CITY/STREET/BUILDINGNUM/ZIPCODE/EMAIL/TELEPHONENUM/IBAN
are minted with `lang="az"` even inside EN/TR/RU documents.** This is not
an oversight: `scripts/piigen/locales/{en,tr,ru}.py` are explicitly
work-in-progress locale packs (see their module docstrings) -- only the
calendar layer (`date_builder`/`MONTHS`/`WEEKDAYS`) is populated for
en/tr/ru; identity and geography fields are deliberately borrowed from
`az`, because under this project's translation approach "the PII stays
Azerbaijani and is spliced from the shared az pools." Calling
`ValueFactory` with the document's own lang for those specific labels
raises (`Cannot choose from an empty sequence`) because the en/tr/ru
`Locale` objects have no `cities`/`street_stems`/`phone_builder`/
`iban_countries`/`email_domains`/`corporate_domains` populated. This
matches the real translated corpus's own behaviour: e.g. `translate_input/
en_output.jsonl` keeps the Azerbaijani city name `Astara` verbatim inside
translated English carrier text. `DATE`/`TIME` and every globally-generic
pattern-tier label (`EMAIL` excepted, see above) are minted with the
document's actual language, since those builders are fully populated for
all four locales.

## Sampling / generation details

- Seed `1337` (corpus-derived sampling) / `1338` (generated-batch value
  minting), both fixed in `gen_docx_test_samples.py`'s CLI defaults --
  regenerating with the same seed and the same `excel-txt` commit
  reproduces this batch exactly.
- Source corpus was read from a throwaway `git worktree` checked out to
  `origin/excel-txt` (LFS-pulled there), never merged or checked out into
  this branch's working tree. `test_samples.jsonl` and the
  `translate_input/*.jsonl` files are **not** copied into this branch --
  the manifest captures each corpus-derived file's full text and gold
  entities directly, so this batch is self-contained without needing the
  source jsonl again.
- `python-docx` was not previously a dependency on this branch (removed
  when an earlier `mask/docx` merge was reverted -- see commit `08ecfd1`);
  added back to `requirements.txt`.
- New `.docx` files are committed as ordinary blobs, matching how
  `excel/*.xlsx` and `pdf/*.pdf` are already committed in this directory
  (`.gitattributes` only LFS-tracks `data/**/*.jsonl`, not spreadsheet/PDF/
  Word binaries) -- `manifest.json` stays a plain (non-LFS) JSON file for
  the same reason.

## Known issues / limitations found while building this batch

- **`mask/docx` branch-name discrepancy.** The real, current DOCX-masking
  code (`scripts/pii_guard/`, including `gen_test_docs.py`, the
  hand-authored-fixture generator this batch's template/value-minting
  patterns were adapted from) lives on `origin/mask/docx`. The *local*
  branch named `mask/docx` in this checkout is stale -- it's the version
  from before the `mask/docx` merge was reverted on `main` (see `08ecfd1`)
  and does not contain `scripts/pii_guard/` at all. The local branch
  `mask/docx-correct` is what actually tracks `origin/mask/docx`. Read
  `origin/mask/docx:scripts/pii_guard/gen_test_docs.py` directly (or use
  `mask/docx-correct` locally) if you need that file again -- not the
  local `mask/docx` branch.
- **EN/TR/RU locale packs are incomplete** (see above) -- this is a
  pre-existing, documented state of `scripts/piigen/locales/`, not
  something this batch worked around by accident. Any future work that
  fully populates `en.py`/`tr.py`/`ru.py` geography/phone/email pools could
  regenerate a version of `new_<lang>_*.docx` with genuinely
  language-native addresses/phone numbers instead of spliced-in
  Azerbaijani ones; today's batch intentionally matches the same
  splicing behaviour the real translated corpus already exhibits.
- Tables and embedded images (both present in `scripts/pii_guard/
  gen_test_docs.py`'s own fixtures) were deliberately **not** used here:
  `python-docx` does not expose table-cell or image-OCR'd text through
  `paragraph.text`, and this batch's correctness requirement is
  "extracted text reconstructs gold offsets exactly" -- adding either would
  have meant a second, independent offset-remapping path with no upstream
  precedent. Every document here is header/footer (decorative, no PII) +
  body paragraphs only.

## Verification

`scripts/test_docx_test_samples.py`: opens all 200 files, reconstructs
each one's text (`corpus_*`: the one paragraph's `.text`; `new_*`:
`"\n".join(p.text for p in doc.paragraphs)`), and checks it against
`manifest.json` exactly, then checks every gold entity's `start:end` slice
against the recorded value. Also independently re-validated (outside the
generator) that every structured-tier minted value in the generated half
passes its real `piigen.checksums` validator and is not on
`piigen.blocklist`'s denylist, and that all 27 `data/schema.md` labels
appear at least once in the generated half (`AGE`/`DATE`/`GIVENNAME`/
`SURNAME`/`TELEPHONENUM` most frequent by template design; `ACCESS_TOKEN`/
`API_KEY`/`CARD_SECURITY_CODE`/`ICCID`/`IPV4_ADDRESS`/`IPV6_ADDRESS`/
`MAC_ADDRESS`/`PAYMENT_CARD_NUMBER`/`PRIVATE_KEY` each appear exactly 20
times, once per `it_incident`/`loan_application` variation x language, the
templates that carry them).

Run: `python scripts/test_docx_test_samples.py`
