# Manual review samples

Real corpus documents run through the actual production code
(`model/predict.py`, `formats/txt.py`, `formats/excel_format.py`), for
hand-inspection rather than automated testing. Each pair is one
unmasked/masked run; open both side by side to compare.

- **`big_txt_original.txt` / `big_txt_masked.txt`** — 200 real documents
  (50 each AZ/EN/RU/TR), concatenated into one file, masked via the full
  production pipeline (`hybrid_detect_entities`: model + regex/checksum
  fallback + email-echo pass).

- **`big_table_original.xlsx` / `big_table_masked.xlsx`** — 1000-row,
  28-column workbook covering all 27 entity labels with real corpus
  values, masked via the full production pipeline
  (`hybrid_detect_entities`).

- **`big_table_rawmodel_original.xlsx` / `big_table_rawmodel_masked.xlsx`**
  — the *same* 1000 rows as `big_table_original.xlsx`, but masked using
  the raw model only (`predict.detect_entities`), no regex/checksum
  fallback layer. Built to see where the model itself struggles,
  separate from what the fallback layer compensates for — compare
  against `big_table_masked.xlsx` to see exactly what the fallback layer
  is catching.

Regenerated with `KEY = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")`
(hardcoded in the generating scripts) — not a real deployment key, safe to
keep example values as-is.
