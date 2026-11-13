# `pii_guard` + `your-hf-org/masking-multilingual`: model behavior notes

Referenced from `scripts/pii_guard/detect/_chunk.py` and `scripts/pii_guard/ocr.py`.
Two things carried forward from an earlier, since-abandoned prototype of
docx masking (built on branch `main`, before this work moved onto the
actual `mask/docx` branch and its `pii_guard` package) and **re-verified
against this codebase specifically**, not assumed to transfer as-is -- the
internals differ (native `transformers.pipeline` aggregation there vs.
`model/predict.py`'s own stride/window + raw BIO decode here; a flat-text
detector there vs. `pii_guard`'s hybrid pattern/anchor/ml_context tiers
here).

## Model limitation, restated precisely

**`your-hf-org/masking-multilingual` is trained on Azerbaijani names only.**
Only 4 of the taxonomy's 27 labels ever reach this model in `pii_guard`
(`GIVENNAME`, `SURNAME`, `CITY`, `STREET` -- see `detect/names.py`'s
`TransformerBackend` docstring for why every other label is handled by
`detect/patterns.py`/`detect/anchored.py` instead, with real checksum
validation). Non-Azerbaijani name recall is out of scope for this model's
current training; do not read it as this package's own name detection
being broken -- see `GuardConfig.ner_model`'s docstring and
`AZ_NAME_ONLY_CAVEAT`-equivalent framing throughout this package's docs.

## Root cause #1 (FIXED): context-length collapse

**Evidence, re-measured directly through `model/predict.py`'s own
`load_model`/`detect_entities`** (not through `transformers.pipeline`, and
not assumed identical to the earlier prototype's measurement):

```
FULL paragraph (208 chars, gen_test_docs.py's sample 02): 7 total spans, names found: []
SHORT prefix  (49 chars, same text)                     : 3 total spans, names found:
    [{'label': 'GIVENNAME', 'text': 'Vüqar'}, {'label': 'SURNAME', 'text': 'Səmədov'}]
```

Both runs used the identical model weights and the identical characters at
the start of the string -- the only variable was how much text followed.
`predict.py`'s own `max_length=512, stride=256` window never engaged for
either case (both far under 512 tokens), so this is not a windowing
artifact: it is the model's own per-token confidence in a real,
correctly-placed name decaying as more tokens follow it in the *same
inference call*, collapsing to ~0 well inside a single window.

**Fix, confirmed working through the actual `TransformerBackend` class**
(not just raw `predict.py`):

```
TransformerBackend.detect() on the FULL 208-char paragraph, chunked:
  GIVENNAME    'Vüqar'   score=0.85
  SURNAME      'Səmədov' score=0.85
  STREET       'Neftçilər prospekti' score=0.85
names found: 2/2 expected -- FIX CONFIRMED WORKING
```

`detect/_chunk.py`'s `chunk_spans` (clause-level, ≤100 characters, never
splitting inside a word) runs before every `detect_entities` call in
`TransformerBackend.detect()`. 100 characters was not picked arbitrarily --
tested directly against re-triggering the collapse:

| `max_chars` | sample-02 names found | sample-03 JWT/access-token fragmentation |
|---|---|---|
| 100 (chosen) | `Vüqar`=0.88, `Səmədov`=0.93 | present (unrelated, see #3 below) |
| 130 | `Vüqar`=0.79, `Səmədov`=0.83 (degrading) | unchanged |
| 150 | **none found** (collapsed again) | unchanged |

Raising the chunk size does nothing for the fragmentation issue (unrelated
mechanism, confirmed unaffected at every size tested) while directly
re-triggering the collapse. 100 is the evidence-based choice.

## Root cause #2 (NOT FIXABLE HERE): a genuine model blind spot

`sample_07`'s "Elvin Tofiq oğlu Məmmədov" scores ~0 for GIVENNAME/SURNAME
at *every* context length tested, including the shortest possible:

```
'Elvin Məmmədov'                 -> []
'Elvin Tofiq oğlu Məmmədov'      -> []
'Elvin'                          -> []
'Məmmədov'                       -> []
'Vüqar Səmədov' (control)        -> [GIVENNAME=0.61, SURNAME=0.73]
```

Re-verified through `TransformerBackend.detect()` directly (chunking
applied, as it would be in real use): still `[]` on the full paragraph.
There is no context length at which this recovers, because there is no
signal to recover -- confirmed, not assumed. This is a training-data
coverage gap for these specific tokens, not a pipeline defect, and no
change in this package can fix it. The standalone prototype found it first
(2026-09-14); this section is the re-verification specific to
`pii_guard`/`model/predict.py`.

**Practical implication for `pii_guard` specifically:** because only 4
labels ever reach this model, and 3 of the 5 test-document languages (EN/
TR/RU) get zero name coverage from it by design (out of training scope),
`detect/names.py`'s `GazetteerBackend` fallback and its own weaknesses
(documented in that module) matter more here than they would in a
model-only pipeline. `GuardConfig.require_ml_context=True` (the default)
at least guarantees *some* name/address detector is active rather than
silently skipping the tier -- it does not guarantee that detector is
reliable for a given language or a given specific name.

## Root cause #3 (confirmed, unrelated to #1/#2): subword fragmentation

Long alphanumeric values occasionally come back from the model as 2-3
adjacent spans with small character gaps, or with only part of the value
correctly labeled -- e.g. a JWT access token split into three dot-delimited
pieces, or an Azerbaijani FIN number split with only its first character
correctly tagged. Confirmed present in the **unchunked baseline** too
(so not caused by chunking) and confirmed unaffected by chunk size from
100 to 150 characters (so not fixable by tuning chunk size either) -- this
is the model's own per-token argmax disagreeing across the SentencePiece
subword pieces of one long value, a separate and much more localized
behavior than #1's context-length collapse.

Impact in `pii_guard` specifically is smaller than it would be in a
model-only pipeline: `PAYMENT_CARD_NUMBER`, `IBAN`, `ACCESS_TOKEN`,
`PRIVATE_KEY`, `AZ_FIN`, and every other structured label are detected by
`detect/patterns.py`'s checksum-validated regex, not by this model at all
-- fragmentation only matters for the 4 ml_context labels, and a
fragmented multi-word name still usually gets at least one piece
(GIVENNAME or SURNAME) caught, which is enough to seed
`detect/__init__.py`'s `_propagate_strong_mentions` coreference pass for
the rest of that name's mentions in the document.

## OCR: Cyrillic and diacritics (confirmed, `ocr.py`'s RapidOCR choice)

Re-verified by cropping the exact source-image regions RapidOCR misread,
using this package's own `gen_test_docs.py` fixtures (`sample_09`'s
embedded Russian bank-card image, `sample_07`/`sample_11`'s Azerbaijani
embedded ID-card images):

| Sample | Image shows | RapidOCR read |
|---|---|---|
| `sample_09` | "Действительна до:" (RU: "Valid until:") | Latin homoglyphs, not Cyrillic at all -- not an approximation, a wholesale substitution |
| `sample_07` | "Tələbə bileti:" (AZ: "Student ID:") | `ə` diacritic silently stripped -> reads as an unrelated Latin word |
| `sample_11` | "Vəzifə:" (AZ: "Position:") | same diacritic-stripping pattern |

**Confirmed, not a suspicion: `rapidocr-onnxruntime`'s bundled recognition
model has no Cyrillic support.** A Russian-language document's embedded
images will not have Cyrillic PII detected via the OCR path at all -- the
text the detector sees is garbage, not degraded-but-readable Cyrillic.
This is a real, unaddressed gap in the current OCR engine choice (picked
for having no system-binary dependency -- see `ocr.py`'s module
docstring), not something worked around here. If Cyrillic image content
matters for a real deployment, the fix is a different/additional OCR
engine, not a tuning change to this one.

## Addendum (2026-09-15): root cause #2's IMPACT on recall is now mitigated, the CAUSE is not

`detect/gazetteer_names.py` -- a new, unconditional, comprehensive
given-name/surname pool tier (AZ/EN/RU/TR, reusing
`scripts/name_pools.py`) -- now runs on every document regardless of
whether a model is configured, specifically to catch names root cause #2
predicts the model itself will miss. Re-tested directly against
`sample_07`'s "Elvin"/"Məmmədov": **the model's own score is still ~0,
unchanged** -- root cause #2 is a training-data gap and remains exactly
that. What changed is that the pipeline no longer depends on the model
alone for GIVENNAME/SURNAME: `sample_07`'s masked output now shows both
names redacted via `source=gazetteer_names`, not `source=ner`. Full
before/after recall numbers, the false positives this pool-membership
approach introduces, and how most of them were found-and-fixed rather
than merely reported: `reports/pii_guard_docx/VALIDATION_REPORT.md`'s
"Addendum (2026-09-15)" section. Point #1 below is superseded by that
addendum for GIVENNAME/SURNAME specifically; CITY/STREET recall is
unchanged by this pass (`gazetteer_names.py` deliberately does not touch
those two labels -- see its own module docstring for why).

## What this means for reading any accuracy number out of `pii_guard`

1. Azerbaijani name recall is real but not reliable, even after the
   chunking fix -- expect roughly half of Azerbaijani names in a given
   document to be caught, not all of them, and expect it to vary
   document-to-document depending on whether that specific name happens
   to fall in root cause #2's blind spot. **Superseded for GIVENNAME/
   SURNAME by the 2026-09-15 addendum above** -- CITY/STREET recall is
   still governed by this point as written.
2. Non-Azerbaijani name/address recall depends entirely on
   `GazetteerBackend`'s heuristics when no other model is configured --
   weaker still, and explicitly documented as such in `detect/names.py`.
   **CITY/STREET only, as of the 2026-09-15 addendum** -- GIVENNAME/
   SURNAME now also gets the unconditional `gazetteer_names.py` tier
   regardless of whether a model is configured.
3. Every other label (financial, government ID, credential, network,
   anchored date/time/age) is checksum- or pattern-validated by
   `detect/patterns.py`/`detect/anchored.py` and does not depend on this
   model at all -- its accuracy is governed by those modules' own regex/
   anchor design, not by anything in this document.
