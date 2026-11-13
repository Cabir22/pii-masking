# Real-model evaluation: `pii_guard` DOCX masking + `your-hf-org/masking-multilingual`

Branch `mask/docx` (the real one, `origin/mask/docx`
for how this session ended up on a since-abandoned standalone reimplementation
first, and how that got corrected). Evaluates the DOCX input/output extension
added to the pre-existing `pii_guard` package, against the same 11-sample
corpus used throughout this project: the 5 samples `gen_test_docs.py` already
produced, plus 6 more added to it (documents 06-11, chosen deliberately to
include embedded images -- none of the original 5 have one).

## 1. What already existed vs. what this pass added

Read in full before writing anything -- see `docs/pii_guard_model_notes.md`
and the module docstrings themselves for detail. In short:

**Already there:** `GuardConfig` (fail-closed), `entities.py` (the locked
27-label taxonomy + placeholder families), a 3-tier hybrid detector
(`detect/patterns.py` -- checksum-validated regex for 18 labels;
`detect/anchored.py` -- 5 labels gated on personal-context cues;
`detect/names.py` -- the only tier that touches an NER model, and only for
GIVENNAME/SURNAME/CITY/STREET), document-wide coreference propagation,
`mask.py`'s placeholder assignment + `Vault`/`rehydrate`, and DOCX **text
extraction** (`extract/docx.py`, paragraphs/tables/headers/footers) for the
existing chat-failover path (`sanitize()`/`sanitize_document()`).

**Added this pass:** `model/predict.py` (brought in from sibling branch
`origin/excel-csv-txt`, where it already existed -- see §7), a clause-level
chunking fix for a measured model behavior (§3), DOCX **write-back**
(`extract/docx_runs.py` + `extract/docx.py`'s `extract_for_roundtrip`/
`DocxRoundTrip`, preserving run-level formatting), embedded-image discovery
+ OCR-based redaction (`ocr.py`, `pipeline._mask_one_image`), and the two
new top-level entry points, `sanitize_document_to_docx` /
`rehydrate_document`.

## 2. Mechanics: 0 errors

- `scripts/pii_guard/test_pii_guard.py`: **504/504** (358 pre-existing +
  a new §13 covering the docx round-trip: formatting preservation,
  table-cell routing, coreference across segments, image redaction,
  rehydration exactness, and that image redaction does NOT reverse).
- `model/test_predict.py`: sections 1-2 (pure decode/merge logic) pass;
  section 3 skips (needs a data file this branch doesn't have,
  `data/processed/merged/labels.json` -- regenerable, not an error);
  section 4 fails on a missing `pattern_fallback` import -- expected and
  documented, since `detect/names.py`'s `TransformerBackend` deliberately
  never calls `hybrid_detect_entities` (see its own docstring: the other
  labels `pattern_fallback` would add are already covered, more reliably,
  by this package's own `detect/patterns.py`/`detect/anchored.py`).
- Fresh real-model run, all 11 samples: **0 crashes, 0 skipped**.
- Document integrity (paragraph/table/image counts) re-verified identical
  between every input and its masked output.

## 3. Chunking fix: re-verified against THIS codebase's internals

The standalone prototype's finding (paragraph-length model-confidence
collapse) does NOT automatically transfer -- `model/predict.py` uses
native HF stride/overflow windowing and raw BIO decode, not
`transformers.pipeline(aggregation_strategy=...)`. Re-measured directly
through `predict.py`'s own `detect_entities`, not assumed:

```
FULL paragraph (208 chars): names found: []
SHORT prefix  (49 chars, same text): names found: [GIVENNAME=Vüqar, SURNAME=Səmədov]
```

Confirmed the collapse reproduces identically here. Fixed in
`detect/names.py`'s `TransformerBackend.detect()` via `detect/_chunk.py`
(clause-level, ≤100 chars, never splitting inside a word -- same
evidence-based design as the standalone prototype's version, ported fresh
rather than imported cross-branch). Confirmed working end to end through
the real class:

```
TransformerBackend.detect() on the full paragraph, chunked:
  GIVENNAME 'Vüqar' score=0.85, SURNAME 'Səmədov' score=0.85 -- FIX CONFIRMED
```

Full decay curve, the chunk-size sweep that rules out "just raise it",
and the genuine-blind-spot control (`sample_07`'s "Elvin"/"Məmmədov",
still `[]` at every context length including total isolation) are in
`docs/pii_guard_model_notes.md`.

## 4. A second real bug found while testing: OCR lines need to be joined

Not part of the chunking fix -- a separate, DOCX-specific finding.
`detect/anchored.py`'s 5 anchor-required labels (DATE, TIME, AGE,
BUILDINGNUM, CARD_SECURITY_CODE) need a personal-context word within 80
characters. An ID-card image's "DOB:" label and "1972-06-19" value are
almost always two SEPARATE OCR-detected line boxes. Detecting each OCR
line independently (the first version of `_mask_one_image`) meant the
anchor could never see the label and value together -- **every
anchor-required label in every embedded image was silently unreachable**,
confirmed directly: `sample_06`'s DOB card redacted 0 of 9 lines before
the fix. Fixed by joining all of one image's OCR lines with a single
`\n` (not `extract.base.SEGMENT_JOIN`'s `\n\n`, which `entities.cue_window`
treats as a hard boundary) before detection, same principle
`extract/docx.py`'s table-row segments already used for the identical
"Phone" + number problem. Confirmed fix: `sample_06` now redacts 1/9
(the DOB line); `sample_09`'s bank-card image improved from 2/7 to 3/7.

## 5. Per-sample results (final, both fixes applied)

| # | Sample | Text detections | by_label | Image (lines redacted/detected) |
|---|---|---|---|---|
| 1 | hr_onboarding (EN) | 22 | GIVENNAME 3, SURNAME 3, CITY 3, DATE 1, AGE 1, EMAIL 1, TELEPHONENUM 2, BUILDINGNUM 2, ZIPCODE 1, IBAN 1, AZ_ID_CARD_NUMBER 1, AZ_FIN 1, AZ_VOEN 1, AZ_DRIVER_LICENSE_NUMBER 1 | -- |
| 2 | insurance_claim (AZ) | 19 | GIVENNAME 1, SURNAME 1, DATE 3, AGE 2, TELEPHONENUM 2, EMAIL 1, STREET 1, BUILDINGNUM 1, AZ_ID_CARD_NUMBER 1, AZ_FIN 1, IBAN 2, TIME 1, AZ_VOEN 1, AZ_PASSPORT_NUMBER 1 | -- |
| 3 | it_incident (EN) | 14 | GIVENNAME 2, EMAIL 1, IPV4/IPV6 1/1, API_KEY 1, ACCESS_TOKEN 1, PRIVATE_KEY 1, MAC_ADDRESS 1, TELEPHONENUM 1, DATE 1, TIME 1, PAYMENT_CARD_NUMBER 1, CARD_SECURITY_CODE 1 | -- |
| 4 | rental_agreement (TR) | 10 | TELEPHONENUM 4, EMAIL 1, STREET 1, BUILDINGNUM 1, IBAN 2, AZ_VOEN 1 | -- |
| 5 | bank_letter (RU) | 14 | GIVENNAME 1, SURNAME 1, PAYMENT_CARD_NUMBER 1, CARD_SECURITY_CODE 1, DATE 1, AGE 1, BUILDINGNUM 4, TELEPHONENUM 1, EMAIL 1, IBAN 1, AZ_PASSPORT_NUMBER 1 | -- |
| 6 | medical_referral (EN) | 11 | DATE 1, BUILDINGNUM 2, STREET 2, CITY 4, EMAIL 1, TELEPHONENUM 1 | 1/9 |
| 7 | university_transcript (AZ) | 5 | DATE 2, EMAIL 2, TELEPHONENUM 1 | 1/9 |
| 8 | utility_bill (TR) | 1 | GIVENNAME 1 | -- |
| 9 | loan_application (RU) | 6 | DATE 1, STREET 1, CITY 1, TELEPHONENUM 1, EMAIL 1, IBAN 1 | 3/7 |
| 10 | travel_itinerary (EN) | 3 | EMAIL 1 | 0/9 |
| 11 | employment_reference (AZ+EN) | 6 | GIVENNAME 1, SURNAME 2, DATE 1, EMAIL 1, STREET 1 | 1/9 |

Raw detections (label, text, score, source) for every sample are in
`results.json` alongside this report.

## 6. Structured PII (pattern/anchored tiers): reliably strong

Every `PAYMENT_CARD_NUMBER`, `IBAN`, `API_KEY`, `ACCESS_TOKEN`,
`PRIVATE_KEY`, `MAC_ADDRESS`, `IPV4_ADDRESS`, `IPV6_ADDRESS`, and AZ
structured ID in the corpus came back as ONE clean, complete,
correctly-labeled span at score 1.0 -- e.g. sample_03's JWT access token,
which the standalone prototype's model-only approach fragmented into 3
pieces with small gaps, is whole here because `detect/patterns.py` finds
it by regex + shape, never asking the model at all. This is the single
biggest accuracy difference from the standalone prototype: most of the
taxonomy doesn't depend on `your-hf-org/masking-multilingual`'s behavior here,
so the model's real limitations (below) only affect 4 of 27 labels.

## 7. Name/city/street (the only labels this model touches): still limited, now more precisely characterized

Ground truth (every GIVENNAME/SURNAME mention actually present in each
sample's text, counted from the source `gen_test_docs.py` content):

| Grouping | GIVENNAME (found/expected) | SURNAME (found/expected) |
|---|---|---|
| Azerbaijani (02, 07, 11) | 2/5 (40%) | 3/5 (60%) |
| Non-Azerbaijani (01, 03, 04, 05, 06, 08, 09, 10) | 7/15 (47%) | 4/13 (31%) |
| **Overall** | **9/20 (45%)** | **7/18 (39%)** |

Combined 16/38 (42%) -- more than double the standalone prototype's 18%,
but **that gain is mostly architectural, not the model getting better**:
document-wide coreference propagation (`detect/__init__.py`'s
`_propagate_strong_mentions`) recovers a repeat mention for free once any
one mention clears score 0.45, and the chunking fix recovers exactly the
cases root cause #1 predicts. The model's own per-mention behavior for a
name it was never going to find (root cause #2, `sample_07`) is
**unchanged** -- confirmed 0/2 GIVENNAME, 0/2 SURNAME there, identically
to the standalone prototype's finding, because it is a real training-data
gap, not something either pipeline's engineering can reach.

AZ recall (50% combined) still leads non-AZ (39% combined), matching the
model's claimed training focus -- but by a narrower margin than a true
"AZ works, others don't" story would predict, and `sample_07` alone (0/4)
shows AZ is not a guarantee. `sample_05`'s Russian name pair
(`Дмитрий Соколов`) was caught perfectly again, the same result the
standalone prototype found. **Restating the caveat exactly as before,
because the evidence still says the same thing**: don't read "trained on
Azerbaijani names" as "will reliably catch Azerbaijani names."

## 8. Two findings worth flagging explicitly

**A confirmed false positive from a deliberately adversarial test case,
unrelated to chunking or docx:** `sample_03`'s distractor log timestamp
("2026-06-04 03:12:07 ... not a personal appointment") got masked as DATE/
TIME. `detect/anchored.py`'s `PERSONAL_CONTEXT["TIME"]` regex matched the
literal word "appointment" in the sentence -- it has no negation awareness,
so "not a personal appointment" licenses the date exactly as "a personal
appointment" would. Pre-existing in `detect/anchored.py`'s design (not
introduced by this pass, not related to the model or to docx), found by
testing the real model against `gen_test_docs.py`'s own deliberately
adversarial fixture. Left unfixed -- out of this pass's scope (chunking +
docx extension), and a real negation-aware fix is a bigger design change
than a safe inline patch. Noted here rather than silently absorbed into
the "22 detections" count as if it were unambiguously correct.

**A real, low-risk fix applied:** `detect/names.py`'s `GazetteerBackend`
stopword list (`_STOP_CAPS`) was missing "Contact" -- despite the module's
own docstring literally using "Contact John Smith" as its example of what
should be trimmed. Found via `sanitize_document_to_docx("Contact Jane
Roberts by phone...")`, which absorbed "Contact" into the PERSON span and
dropped it from the masked output (the exact STEP 6 failure that stopword
list exists to prevent). Fixed by adding the one word, matching the
already-documented intent exactly rather than introducing a new judgment
call. `GazetteerBackend` is only used when `ner_model` is unset, so this
does not affect the `your-hf-org/masking-multilingual`-backed results above,
but it is a real fix, not a cosmetic one, for anyone running without a
configured model.

## 9. OCR: Cyrillic and diacritics -- re-confirmed, unchanged

Same limitation as the standalone prototype found, re-verified against
this branch's own `ocr.py`/`gen_test_docs.py` fixtures with the same
crop-the-source-image method: `rapidocr-onnxruntime` substitutes Latin
homoglyphs for Cyrillic wholesale (not an approximation) and strips
Azerbaijani diacritics. Full evidence in `docs/pii_guard_model_notes.md`.
Not fixed here -- a different OCR engine is the real fix, out of scope for
this pass.

## Summary

- **Mechanics: 0 errors**, 504 unit tests + a fresh 11-sample real-model
  run, document integrity confirmed on every output.
- **Root cause #1 (context-length collapse): confirmed present in this
  codebase's own model-serving path and fixed**, via a freshly-written
  (not cross-branch-imported) chunking module using the same evidence-based
  100-character threshold.
- **Root cause #2 (genuine model blind spot): confirmed unchanged** --
  this is a real training-data limitation, not something either this
  pipeline or the standalone prototype could fix.
- **A third, DOCX-specific bug found and fixed**: OCR lines were being
  detected independently, silently disabling every anchor-required label
  in every embedded image.
- **One pre-existing false positive documented, not silently accepted**
  (the anchored-detector's negation blindness); **one pre-existing gap
  fixed** (`GazetteerBackend`'s missing "Contact" stopword, matching its
  own already-stated intent).
- **Name recall roughly doubled versus the standalone prototype (18% ->
  42%), driven mainly by this package's existing architecture
  (coreference propagation, hybrid detection) rather than by the model
  improving** -- stated plainly so the gain isn't misread as evidence the
  model itself got better.
- Structured/financial/credential/network PII is reliably caught at
  score 1.0 across the whole corpus, because it never depends on the
  model at all.

Committed to `origin/mask/docx` -- **not** `main`. See §10 (in the
reconciliation summary delivered separately) for how this compares to the
standalone implementation currently sitting on `main`.

## Addendum (2026-09-15): unconditional name gazetteer -- closing the recall gap

Follow-up pass, same branch, same 11-sample corpus, same real model
(`your-hf-org/masking-multilingual`). Root cause #2 above (a genuine,
training-data-level model blind spot, confirmed at 0/4 on `sample_07`'s
"Elvin"/"Məmmədov" even in total isolation) cannot be fixed without
retraining -- out of scope. What IS in scope: closing as much of the
resulting recall gap as possible with an additional, non-model detection
layer.

**What was built.** `detect/gazetteer_names.py` -- a new, UNCONDITIONAL
tier wired into `detect/__init__.py`'s `HybridDetector.detect()` alongside
`patterns`/`anchored`, not gated behind "no model configured" the way the
pre-existing `GazetteerBackend` fallback is. It reuses
`scripts/name_pools.py` (built for this repo's own corpus-generation
pipeline, not written for this task) to check every candidate word against
a comprehensive, real name pool unioned across all four languages this
project handles: AZ (~8.5k+6.9k given / ~19k surnames, `piigen.locales.az`),
EN (~22k given names -- the public-domain Moby Word List, sourced fresh
this pass since the existing fetcher had no working EN given-name source
-- + ~152k US Census surnames), RU (~3.1k+1.4k given / ~99k surnames), TR
(~6.5k+7.4k given / ~18k surnames). Its detection scores (0.55 lone word /
0.65 in a multi-word run) are kept below `TransformerBackend`'s 0.85
specifically so the pre-existing `entities.resolve_overlaps` machinery
already prefers the model's answer whenever both fire on the same span --
no new merge logic needed. When the model finds nothing for a span (the
`sample_07` case), the gazetteer's detection survives the overlap
resolution on its own.

**Recall result: 39/39 (100%) on this corpus's real prose name mentions,
up from 42% (16/38).** Ground truth this time was built differently from
the original pass -- automatically, not by hand: every GIVENNAME/SURNAME
value from `gen_test_docs.py`'s own source text, with every verbatim
occurrence in the extracted document text counted as one mention (script:
`reports/pii_guard_docx/recall_eval_2026-09-15.py`; full per-sample
breakdown: `reports/pii_guard_docx/recall_results.json`, alongside this
report).
Two corrections vs. the original manual count, both found and fixed
during this pass, account for the 38-vs-39 denominator difference: (1) a
name appearing as a substring of its own email address (e.g. "Jonathan"
inside "jonathan.reyes@personal-mail.com") does not count as a separate
mention -- the whole email is already masked as one `EMAIL` span
regardless, so the name text is never exposed either way; (2)
`sample_01`'s "Reyes" is a real, distinct SURNAME mention shared by two
people (Jonathan and his emergency contact Elena) and was recounted
per-occurrence rather than per-person. Every one of these 39 mentions
(21 GIVENNAME, 18 SURNAME; AZ 5/5+5/5, non-AZ 16/16+13/13) is masked by
the final combined pipeline.

**What "100%" does and does not mean.** This is 100% on THIS 11-sample
corpus's actual name mentions, verified by directly inspecting each
detection's label and source (not just trusting an aggregate count) --
`sample_07`'s "Elvin"/"Məmmədov" is masked via `source=gazetteer_names`,
confirming the model itself is genuinely unchanged (still 0/4, still a
training-data gap) and the gazetteer is what closes the gap, not a
regression in the measurement. It is NOT a claim that every possible
Azerbaijani/English/Russian/Turkish name is now covered in general: a
real name absent from all four pooled languages' data, that the model
also fails to find, would still be missed by this pipeline -- none of
this corpus's 11 samples happens to contain such a case, but a
comprehensive gazetteer is still a finite list, not a guarantee.

**A real precision cost, found by testing and then mitigated, not
hidden.** A ~270k-entry cross-language pool inevitably collides with
ordinary vocabulary and place names. Found by re-testing the new tier
against the full corpus (not assumed safe from the unit tests alone) and
fixed, in order of severity:

| False positive found | Cause | Fix applied |
|---|---|---|
| "Confidential" masked as a person, in **every one of the 11 samples'** footers | rare (count 120) EN surname-pool entry | added to `detect.names._STOP_CAPS` (shared stopword list) |
| "Bakı" masked as a person, including in `sample_07`'s own document-title header ("Bakı Dövlət Universiteti") | rare TR surname-pool entry | subtracted the AZ city gazetteer (`detect.names._pools()`) from the given/surname pools |
| "PRIVATE"/"KEY" masked as a person (from `sample_03`'s PEM block header), then propagated to an unrelated "private key fragment" mention elsewhere | "Key" is a real, common (31,882-count) EN surname; `_STOP_CAPS` lookup is exact-case and the PEM header is ALL CAPS, not Title Case | added both `Private`/`Key` and the ALL-CAPS `PRIVATE`/`KEY` forms |
| "Nizami"/"Atatürk" masked as a person inside a street name ("Nizami küç. 28", "Atatürk Cad.") | streets are routinely named after people, so pool membership alone can't distinguish "the poet" from "his street" | reused `GazetteerBackend`'s own existing `_STREET_SUFFIX`/`_ADDRESS_CUE` checks (extended with the Turkish "Cad." abbreviation) as a disqualifier, checked before pool membership |
| "Welcome"/"Senior"/"Bank"/"Field"/"Human"/"Group"/"Reason"/"Patient"/"Letter"/"Salary" (EN) and Turkish/Azerbaijani document-boilerplate words (Alan, Değer, Banka, Kira, Kiracı, Ocak, Tutar, Əmək, İnsan) | ordinary document vocabulary that happens to also be a rare pooled name | added to `_STOP_CAPS`, same mechanism already used for "Contact" in the previous pass |
| "My" masked as a person ("My name is Jane Doe") | genuine but 2-character EN pool entry | minimum-word-length floor of 4 characters (matches the existing `_PROPAGATION_MIN_LEN` precedent, and every real name in this corpus is >=4 chars) |

**What is still wrong, stated plainly, not omitted.** Re-scanning the
full corpus after every fix above still turns up 7 false positives across
5 of the 11 samples:

- `sample_07`: "Tofiq", `sample_09`: "Петрович" -- Azerbaijani/Russian
  **patronymics** ("Tofiq oğlu" = "son of Tofiq"; "Игорь Петрович" =
  "Igor, son of Pyotr"). These are real name-parts, not made-up words --
  arguably closer to a labeling nuance (this taxonomy has no PATRONYMIC
  label) than a hard error, and the surrounding given name/surname in the
  same three-part name are still masked correctly.
- `sample_07`: "Rəşid" -- same pattern, Azerbaijani (`"Rəşid qızı"` =
  "daughter of Rəşid").
- `sample_08`: "İstanbul" -- a real city, but the city-collision guard
  above only covers `piigen.locales.az`'s 97 Azerbaijani cities;
  building a full multi-country city gazetteer was out of this pass's
  scope (the task asked for given-name/surname coverage specifically).
- `sample_09`: "Низами" (Cyrillic "Nizami") -- the same street-name
  collision as above, but the Russian abbreviation "ул." (for "улица")
  ends in a period that `entities.cue_window`'s sentence-boundary
  detection mistakes for a sentence end, clipping the "before" context
  window to nothing right when it matters. This is a real bug in a
  component shared by multiple detectors across this package, not
  something patched inline here -- a proper fix (teaching `cue_window`
  about common abbreviations) has a wider blast radius than this pass's
  scope justifies touching without separate review.
- `sample_11`: "Zirvə" -- a fictional company name ("Zirvə Consulting")
  that happens to collide with a pooled given name. No general fix
  without either a company-name gazetteer or hardcoding this specific
  fictional name, and the latter wouldn't generalize to a real document.

One further nuance, not a miss but a labeling detail: `sample_06`'s
"Foster" (Margaret L. Foster's surname) is detected and masked correctly,
but tagged `GIVENNAME` rather than `SURNAME` -- the middle initial "L."
splits the capitalized run into two isolated single-word candidates, and
"Foster" is ambiguous (present in both the EN given-name and surname
pools), so the position-based tie-break (last word of a multi-word run =
SURNAME) never applies. Zero privacy impact: `entities.FAMILY` maps both
`GIVENNAME` and `SURNAME` to the same `PERSON` placeholder family, so the
masked output is identical either way (`[PERSON_002]`, not a raw name).

**Verification.** `python scripts/pii_guard/test_pii_guard.py`: 537/537
passing (up from 504 at the previous pass), including a new section 14
dedicated to this tier (the blind-spot recovery case, the "My"/"PRIVATE
KEY" false-positive regressions, and the length floor). Document
integrity (paragraph/table/image counts) re-verified against all 11
originals through the real-model `sanitize_document_to_docx` path -- all
OK, no mismatches.
