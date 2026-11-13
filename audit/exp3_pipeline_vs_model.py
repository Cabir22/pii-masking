"""EXPERIMENT 3 -- shipped pipeline vs. raw model (brief sections 14, 20, 30).

exp1/exp2 measured the MODEL. This measures the PRODUCT, which is a
different thing and, for CSV/XLSX, mostly does not use the model at all:
formats/csv_format.py classifies each COLUMN (by header keyword, else by
running the corpus's own checksum validators over its values) and masks
classified columns with mask_value() directly, never invoking NER. Only
columns that stay unclassified fall through to per-cell model detection.

So the product's real failure mode is not "the model missed an entity in a
table". It is "column classification missed a column, the fallback per-cell
model path then missed the value, and the cell shipped in plaintext".

Three conditions per format, all on identical data:
  known_headers   -- headers in the vocabulary HEADER_KEYWORDS ships
  unknown_headers -- headers renamed Col1..Col10 (classification by header
                     impossible; value-validators and column consensus are
                     all that remain)
  no_header       -- first row is already data

Measured, separately, per brief section 20:
  DETECTION -- did something find the entity at all?
  MASKING   -- is the value actually GONE from the written-out file? This is
               the only number that means "protected", and it is computed by
               searching the real output file for the plaintext value.
  MAPPING   -- does unmask() restore the original file exactly?
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec     # noqa: E402
import render   # noqa: E402

KEY = b"0" * 32


def _leaked_cells(orig_cells: list[tuple[str, str]],
                  masked_cells: list[tuple[str, str]],
                  expected) -> list:
    """Cell-precise leak detection.

    A value counts as leaked only if it is still present in the SAME CELL it
    came from after masking. An earlier version of this searched the whole
    output file for the plaintext value, which reported false leaks for short
    values -- BUILDINGNUM '14' "leaked" in every run simply because the two
    digits 1 and 4 occur adjacently somewhere in a file full of masked digit
    strings. That would have turned a clean result into a fake finding, so
    leak detection is anchored to the originating cell instead.

    `orig_cells` / `masked_cells` are parallel (key, value) lists in the same
    order, where key identifies the cell position.
    """
    by_key = dict(masked_cells)
    wanted = {}
    for lab, v in expected:
        wanted.setdefault(v, []).append(lab)

    leaked = []
    for key, orig in orig_cells:
        masked = by_key.get(key, "")
        for v, labs in wanted.items():
            if v in orig and v in masked:
                leaked.append([labs[0], v])
    return leaked


def run_csv(lang: str, condition: str, detect) -> dict:
    import csv_format

    labels = (spec.FIELD_LABELS[lang] if condition == "known_headers"
              else spec.FIELD_LABELS_UNKNOWN[lang])
    path = harness.FIXTURES / f"p3_{lang}_{condition}.csv"
    render.render_csv(path, lang, "table", labels)

    if condition == "no_header":
        # Strip the header row entirely: row 1 becomes real data.
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[1:]) + "\n", encoding="utf-8")

    expected = spec.expected_entities(lang)
    fieldnames, rows = csv_format.extract(path)
    masked_rows, manifest = csv_format.mask_csv(fieldnames, rows, detect, KEY)

    out = harness.FIXTURES / f"p3_{lang}_{condition}.masked.csv"
    csv_format.write_csv(out, fieldnames, masked_rows)

    # Header cells are included on BOTH sides: in a headerless file the first
    # data row IS the fieldname list, and whether that row got masked is
    # precisely what this condition is testing.
    orig_cells = ([(f"h{j}", c) for j, c in enumerate(fieldnames)]
                  + [(f"{i}:{c}", r.get(c, ""))
                     for i, r in enumerate(rows) for c in fieldnames])
    masked_cells = ([(f"h{j}", c) for j, c in enumerate(fieldnames)]
                    + [(f"{i}:{c}", r.get(c, ""))
                       for i, r in enumerate(masked_rows) for c in fieldnames])
    leaked = _leaked_cells(orig_cells, masked_cells, expected)
    restored = csv_format.unmask_csv(fieldnames, masked_rows, manifest, KEY)
    roundtrip_ok = restored == rows

    classified = {c: l for c, l in manifest["column_labels"].items() if l}
    return {
        "format": "csv", "lang": lang, "condition": condition,
        "columns_total": len(fieldnames),
        "columns_classified": len(classified),
        "classified_map": classified,
        "expected": len(expected), "leaked": len(leaked),
        "leaked_detail": leaked,
        "mask_rate": 1 - len(leaked) / len(expected),
        "roundtrip_exact": roundtrip_ok,
    }


def run_xlsx(lang: str, condition: str, detect) -> dict:
    import excel_format

    labels = (spec.FIELD_LABELS[lang] if condition == "known_headers"
              else spec.FIELD_LABELS_UNKNOWN[lang])
    path = harness.FIXTURES / f"p3_{lang}_{condition}.xlsx"
    render.render_xlsx(path, lang, "table", labels)

    if condition == "no_header":
        import openpyxl
        wb = openpyxl.load_workbook(path)
        wb.active.delete_rows(1)
        wb.save(path)

    expected = spec.expected_entities(lang)
    wb, manifest = excel_format.mask_workbook(path, detect, KEY)
    out = harness.FIXTURES / f"p3_{lang}_{condition}.masked.xlsx"
    wb.save(out)

    import openpyxl
    def cells(p_):
        wbx = openpyxl.load_workbook(p_)
        return [(f"{ws.title}!{c.row}:{c.column}",
                 "" if c.value is None else str(c.value))
                for ws in wbx.worksheets for row in ws.iter_rows() for c in row]

    leaked = _leaked_cells(cells(path), cells(out), expected)

    wb3 = excel_format.unmask_workbook(out, manifest, KEY)
    restored_text = "\n".join(
        " | ".join("" if c is None else str(c) for c in row)
        for ws in wb3.worksheets for row in ws.iter_rows(values_only=True))
    orig_wb = openpyxl.load_workbook(path)
    orig_text = "\n".join(
        " | ".join("" if c is None else str(c) for c in row)
        for ws in orig_wb.worksheets for row in ws.iter_rows(values_only=True))

    sheet_man = next(iter(manifest["sheets"].values())) \
        if "sheets" in manifest else manifest
    classified = {c: l for c, l in sheet_man.get("column_labels", {}).items() if l}
    return {
        "format": "xlsx", "lang": lang, "condition": condition,
        "columns_total": len(sheet_man.get("column_labels", {})),
        "columns_classified": len(classified),
        "classified_map": classified,
        "expected": len(expected), "leaked": len(leaked),
        "leaked_detail": leaked,
        "mask_rate": 1 - len(leaked) / len(expected),
        "roundtrip_exact": restored_text == orig_text,
    }


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.FIXTURES.mkdir(parents=True, exist_ok=True)
    harness.RESULTS.mkdir(parents=True, exist_ok=True)

    results = []
    for condition in ["known_headers", "unknown_headers", "no_header"]:
        for lang in spec.LANGS:
            for fn in (run_csv, run_xlsx):
                try:
                    r = fn(lang, condition, detect)
                except Exception as exc:
                    r = {"format": fn.__name__, "lang": lang,
                         "condition": condition,
                         "error": f"{type(exc).__name__}: {exc}"}
                results.append(r)
                if "error" in r:
                    print(f"{r['format']:5s} {lang} {condition:16s} ERROR {r['error']}")
                else:
                    print(f"{r['format']:5s} {lang} {condition:16s} "
                          f"cols_classified={r['columns_classified']}/{r['columns_total']} "
                          f"masked={r['mask_rate']:.0%} "
                          f"leaked={r['leaked']}/{r['expected']} "
                          f"roundtrip={'OK' if r['roundtrip_exact'] else 'BROKEN'}")

    out = harness.RESULTS / "exp3_pipeline_vs_model.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
