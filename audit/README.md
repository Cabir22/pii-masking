# Multi-format model & pipeline audit

Reproducible experiment suite behind **PII Masking Pipeline — Multi-Format
Model & Pipeline Audit** (2026-09-16).

Nothing here modifies the production pipeline. `audit/` only reads the repo,
builds fixtures in `audit/_work/`, and writes JSON results.

## What it runs against

Everything the audit exercises is in this tree:

| formats | where |
|---|---|
| TXT, CSV, XLSX | `formats/` |
| DOCX, PPTX | `scripts/pii_guard/` (one package) |
| PDF | *(no extractor anywhere; `pdfplumber` stands in and is flagged as ad hoc)* |

Until the 2026-09-28 consolidation (see `docs/branches.md`) no single branch
held all six formats, and `harness.py` worked around that by `git archive`-ing
two divergent copies of `pii_guard` out of `mask/docx` and `mask/pptx`. Those
branches are gone (tags `archive/mask-docx` / `archive/mask-pptx` keep them),
so the harness now imports straight from the working tree.

## Prerequisites

The repo's `requirements.txt` does **not** declare everything the audit needs.
On top of it:

```bash
pip install openpyxl chardet pdfplumber reportlab
```

(`openpyxl` + `chardet` are used by `formats/`; `pdfplumber` extracts PDFs and
`reportlab` renders the PDF fixtures.) The model `your-hf-org/masking-multilingual`
must be loadable from the local Hugging Face cache or via your own login. Never
put a token in a script.

## Running

```bash
.venv/bin/python audit/exp1_cross_format.py       # same content, 6 formats
.venv/bin/python audit/exp2_representation.py     # representation ablation
.venv/bin/python audit/exp3_pipeline_vs_model.py  # shipped pipeline, end to end
.venv/bin/python audit/exp4_docx_pptx_pipeline.py # pii_guard + chunking
.venv/bin/python audit/exp5_pdf_structure.py      # PDF layout variants
.venv/bin/python audit/exp6_context.py            # context mechanism
.venv/bin/python audit/exp7_fix_prototype.py      # candidate fix, measured
.venv/bin/python audit/exp8_header_edge_cases.py  # KNOWN_ISSUES 1 + 2 repros
.venv/bin/python audit/compile_tables.py          # summary matrices
```

Generated fixtures and per-run results go to `audit/_work/` (git-ignored, safe
to delete; override with `AUDIT_WORK=/some/dir`). `compile_tables.py` reads
`results/*.json` from there and writes `results/tables.txt`. The full suite
makes thousands of model calls and takes on the order of an hour on a laptop.

`exp8` is the regression check for `formats/KNOWN_ISSUES.md` items 1 and 2:
while those bugs exist it prints the leaks; after a fix it should print none.
`exp7` builds its patched copy of `formats/excel_format.py` itself at run time
and refuses to run if the call site it patches has changed.

## Files

| file | purpose |
|---|---|
| `spec.py` | the canonical content: 5 records x 4 languages x 3 registers |
| `render.py` | renders that content into TXT/CSV/XLSX/DOCX/PPTX/PDF |
| `extract_all.py` | one `extract()` per format, using the **real shipped** extractor wherever one exists |
| `harness.py` | path setup, model loading, value-level scoring |
| `exp*.py` | the experiments |
| `compile_tables.py` | builds the summary matrices |

## Methodology notes that matter

**Value-level scoring, not offset-level.** Identical content necessarily
lands at different character offsets in different formats, so an
offset-exact cross-format comparison would measure the renderer rather than
the pipeline. Matching is multiplicity-aware `(label, value)`. Offset and
mapping correctness are measured separately, per format, in `exp3`
(mask → unmask round-trip against the original file).

**Extraction loss is separated from detection loss.** Every experiment first
checks which expected values survive extraction verbatim, and scores
detection only against those. A value destroyed by extraction is charged to
extraction, never to the model.

**Fixture values are sampled from the project's own corpus**, first-N-distinct
in corpus order — in-distribution and *not* chosen for model behaviour. All
structured values are asserted against `piigen.validate` before scoring, so a
miss is never just an invalid fixture value.

**Two fixture bugs were found and fixed during the audit, not reported as
findings.** Both would have produced confident false conclusions:

1. A single hand-picked name (`Rəşad Quliyev`) produced a flat 70% recall in
   every format — which was that one name being a model blind spot, not a
   property of any format. Fixed by sampling five records.
2. STREET gold was written bare (`Nizami`) while the corpus's own convention
   includes the street-type word (`Nizami küçəsi`, `Olimpiya Ave.`). That
   scored a 100% STREET miss rate across all six formats, entirely
   spuriously. Fixed by matching the corpus convention.

A third (`render.py` clipping PDF table cells to 14 characters, which looked
exactly like a PDF extraction failure) is now guarded by `_assert_fits`,
which refuses to render a clipped table rather than silently producing one.

## Not covered, and why

**Model A vs Model B.** The brief asks for a comparison of the
Azerbaijani-only checkpoint against the multilingual one. Only
`your-hf-org/masking-multilingual` exists: it is the only checkpoint referenced
on any branch, the only one in the local HuggingFace cache, and the
`your-hf-org` account exposes exactly two models (this one and an unrelated
Whisper model). Every Model-A comparison is reported as blocked rather than
estimated. Re-run everything here with `MODEL_ID` in `harness.py` pointed at Model A
if it is recovered.

**Images/OCR.** Explicitly out of scope per the brief.
