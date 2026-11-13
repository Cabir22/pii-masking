# Testing samples

20 review samples (10 TXT + 10 Excel, each half freshly authored / half
pulled straight from the real corpus), masked via the actual production
pipeline (`hybrid_detect_entities`: model + regex/checksum fallback),
for hand-inspection. Each pair is one unmasked/masked run; open both side
by side to compare. Regenerated with
`KEY = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")` (hardcoded in
the generating script) — not a real deployment key.

## `txt/` (10 documents)

- **`txt_scratch_*_original.txt` / `_masked.txt`** (5) — freshly written
  documents (an HR memo, a support email, a courier chat log, a rental
  contract excerpt, an IT incident report — AZ/EN/RU/TR), populated with
  real PII values drawn from the corpus's own value pool. New sentences,
  authentic values.
- **`txt_corpus_*_original.txt` / `_masked.txt`** (5) — actual documents
  lifted verbatim out of `data/processed/merged/{train,val,test}.docs.jsonl`
  (one per language where available), gold labels and all. Nothing rewritten.

## `excel/` (200 workbooks, ORIGINAL only — replaces the earlier 10-file/
masked-pair version)

Rebuilt to the same principles as `pdf/` below: 200 total, ORIGINAL only (no
masking), split 50/50/50/50 across az/en/tr/ru, 25/language from
already-generated JSON content and 25/language freshly authored.

- **`json_<lang>_NNN.xlsx`** (100, 25/language) — the *same* 100 source
  documents used in `pdf/json_<lang>_NNN.pdf` (same content, different file
  format), one document's full text per workbook in a single `Text`/`Mətn`/
  `Metin`/`Текст` column, one row.
- **`new_<lang>_NNN.xlsx`** (100, 25/language) — 5 genuinely tabular
  templates (customer registry, payroll/HR extract, device/IT inventory,
  travel/booking log, security credential-rotation log) × 5 row-value
  variations each, per language, 8 rows per workbook, real corpus-pool
  values per cell. The 5 templates collectively cover all 27 entity labels
  (verified at generation time, see `generate_excel_200.py`'s own coverage
  check).

## `csv/` (200 files, one record per file)

Original and newly authored CSV fixtures for exercising the CSV pipeline.
Each numbered file (`001_<id>.csv` through `200_<id>.csv`) contains the shared
header and exactly one example record. Nested fields such as `entities`,
`_noise`, and `_spec` are preserved as JSON strings inside their CSV cells.

The set contains 100 source records and 100 newly authored records. The new
records are split evenly across Azerbaijani, English, Russian, and Turkish
(25 records per language). The `origin` column distinguishes `source` from
`generated` records.

## Known issue found while building this batch, NOT fixed (raw model gap)

The TXT leak scan (checks every known injected/gold value against the
actual masked output, not just round-trip/span-match) found the raw model
**completely misses a GIVENNAME/SURNAME pair sitting in a low-context
position** — right after a label colon ("Kimdən: ...", "Kiracı: ...") or in
a closing signature line ("Hörmətlə,\n...") — in 4 of the 5 `txt_scratch_*`
documents (8 name tokens across `az_hr_onboarding`, `en_support_escalation`,
`tr_rental_excerpt`, `az_it_incident`). The *same* model, on the *same*
document, correctly caught names embedded in a full sentence a few lines
away. This is a genuine raw-model generalization gap (short, low-context
mentions score under the classification threshold — the model's own
measured 53-97% isolated-word confidence range, documented in
`model_weaknesses_report.md`), not a decode-time bug — `pattern_fallback.py`
deliberately has no name coverage (no fixed shape to verify), so there's no
existing safety net for this category the way there is for
EMAIL/DATE/phone/IDs.

Two *are* fixed, in `formats/excel_format.py` / `formats/csv_format.py`,
found via the same leak scan on this batch's Excel side:
1. Column-consensus promotion required unanimous agreement among detected
   cells; one minority mislabel (GIVENNAME/CITY confusion) blocked
   promotion for the whole column, leaving real names unmasked. Now
   requires a majority instead of unanimity.
2. `HEADER_KEYWORDS["TIME"]` was missing common possessive forms
   ("saatı"/"saati"/"vaxtı"), so a bare `HH:MM` column with such a header
   fell back to weak per-cell model detection instead of direct
   classification.

The signature/label-colon name miss above is still open — a fix would mean
either better training coverage for that structural position or a new
context-position heuristic (higher false-positive risk, needs design
sign-off), not a safe drop-in patch like the two above.

## `pdf/` (200 documents, ORIGINAL only — no masked counterparts)

Format-testing fixtures for a future PDF pipeline; unlike `txt/`/`excel/`
above, these are unmasked on purpose (real generated PII values, not run
through detection/masking at all). Split 50/50/50/50 across az/en/tr/ru;
within each language, 25 are pulled from already-generated JSON content and
25 are freshly authored here.

- **`json_<lang>_NNN.pdf`** (100, 25/language) — plain text of an existing
  generated document rendered straight to PDF: `az` from
  `test_samples.jsonl` (the 200-doc Wahoo batch), `en`/`tr`/`ru` from
  `translate_input/<lang>_output.jsonl` (the real translations of that same
  batch).
- **`new_<lang>_NNN.pdf`** (100, 25/language) — 5 document templates (HR
  onboarding, travel/ID verification, banking, IT/security incident,
  delivery note) × 5 value-variations each, per language, each populated
  with real corpus-pool values. The 5 templates collectively cover all 27
  entity labels (verified at generation time, see
  `generate_pdfs.py`'s own coverage check).

Rendered with `reportlab`, embedding Windows' `arial.ttf`/`arialbd.ttf` so
Cyrillic and Azerbaijani/Turkish diacritics (ə, ş, ç, ğ, ı, ö, ü) render
correctly — the default PDF base fonts don't cover either script.

## `web_style/` (200 text samples, JSON, `{"text": ...}` only)

`web_style_samples.json`: 200 records, 50 each az/en/tr/ru. NOT scraped
from real articles — real news sites (bbc.com, apa.az, trthaber.com,
ru.trend.az) were browsed only for grounding (real organization names,
real place-name texture, real journalistic sentence structure per
language), never copying article bodies verbatim, to avoid both
reproducing copyrighted news prose and compiling real people's personal
information. Every sentence is written from scratch as one of 6 genre
templates (career profile, local incident report, business appointment,
sports club signing, insurance/financial customer story, cybersecurity
breach report), each populated with a synthetic individual using real
corpus-pool PII values — no real named person appears anywhere. The 6
genres collectively cover all 27 entity labels. Purpose: test detection
against natural narrative prose the model wasn't trained on, rather than
this project's own templated document styles.
