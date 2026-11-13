"""EXPERIMENT 8 -- header handling in formats/excel_format.py and csv_format.py.

These are the checks behind formats/KNOWN_ISSUES.md items 1 and 2 (and the
Excel-vs-CSV consensus gap). They were first run ad hoc; this makes them
reproducible, and gives whoever fixes those issues a before/after check.

  A. Which ordinary spreadsheet header words pass a STRUCTURED validator?
     (AZ_FIN is 7 alphanumeric characters with no checksum, so any 7-letter
     word does.)  -> KNOWN_ISSUES 1
  B. Does that make Excel take a real header row for data, and write the
     first data row out in plaintext?  Minimal pair: one header word changed.
     -> KNOWN_ISSUES 1
  C. Headers a person would really write but HEADER_KEYWORDS does not know.
     Excel's column-consensus promotion recovers them; CSV has no such
     mechanism.  -> KNOWN_ISSUES 2
  D. Structural cases that work and should keep working: one person split
     across two cells, several sheets with different names, a merged title
     banner above the real header.

Every "leaked" figure is cell-precise: a value counts as leaked only if it is
still in the SAME cell after masking (see exp3._leaked_cells for why a
whole-file substring search reports false leaks).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec  # noqa: E402
from exp3_pipeline_vs_model import _leaked_cells  # noqa: E402

KEY = b"0" * 32

# The 73 header words checked for part A (English, Azerbaijani, Turkish; the
# set that produced the "12 of 73" figure).
HEADER_WORDS = """Surname Name Address Country Company Contact Details Region District Balance
Account Number Status Comment Notes Customer Client Partner Manager Product Service Invoice
Payment Amount Currency Category Branch Office Position Department Employee Salary Passport
License Vehicle Device Session Channel Message Subject Sender Receiver Revision Version Created
Updated Deleted Approved Rejected Pending Active Expired Musteri Adres Sirket Telefon Bolge
Hesap Durum Yorum Musteriler Sube Odeme Tutar Fatura Soyad Unvan Vezife Sobe Hesab Status Qeyd
Musteri Mebleg Tarix""".split()

# Real headers a human would write that HEADER_KEYWORDS does not know.
UNKNOWN_HEADERS = {
    "az": ["Müştərinin adı", "Sahibin soyadı", "Yaşayış məntəqəsi", "Ünvan sətri"],
    "en": ["Employee full name", "Family name", "Place of residence", "Address line"],
    "ru": ["Владелец", "Фамилия сотрудника", "Место проживания", "Строка адреса"],
    "tr": ["Yetkili kişi", "Aile adı", "Yerleşim yeri", "Adres satırı"],
}
NAME_FIELDS = ["GIVENNAME", "SURNAME", "CITY", "STREET"]


def _cells(path: Path) -> list[tuple[str, str]]:
    import openpyxl
    wb = openpyxl.load_workbook(path)
    return [(f"{ws.title}!{c.row}:{c.column}", "" if c.value is None else str(c.value))
            for ws in wb.worksheets for row in ws.iter_rows() for c in row]


def part_a() -> dict:
    from piigen.config import STRUCTURED_LABELS
    from piigen.validate import value_valid
    words = sorted(set(HEADER_WORDS))
    hits = {}
    for w in words:
        for lab in sorted(STRUCTURED_LABELS):
            if value_valid(lab, w)[0]:
                hits.setdefault(lab, []).append(w)
    print(f"A. {len(words)} ordinary header words checked against every structured validator")
    for lab, ws in hits.items():
        print(f"   {lab}: {len(ws)} pass -> {ws}")
    if not hits:
        print("   none pass (KNOWN_ISSUES 1 no longer reproduces at the validator level)")
    return {"words": len(words), "hits": {k: v for k, v in hits.items()}}


def part_b(detect) -> dict:
    import openpyxl
    import excel_format
    rows = [("Khani", "Abadov", "Astara", "12"),
            ("Gulanzar", "Shahsoltanova", "Aghsu", "7"),
            ("Nənə", "Sarvarli", "Khojavand", "43")]
    expected = [(l, v) for r in rows for l, v in zip(NAME_FIELDS, r)]
    out = {}
    print("\nB. one header word changed, everything else identical")
    for tag, hdr in [("Surname", ["First name", "Surname", "City", "Building"]),
                     ("Last name", ["First name", "Last name", "City", "Building"])]:
        p = harness.FIXTURES / f"e8_header_{tag.replace(' ', '_')}.xlsx"
        p.parent.mkdir(parents=True, exist_ok=True)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(hdr)
        for r in rows:
            ws.append(list(r))
        wb.save(p)
        header_row = excel_format._detect_header_row(openpyxl.load_workbook(p).active)
        mwb, _ = excel_format.mask_workbook(p, detect, KEY)
        o = p.with_suffix(".masked.xlsx")
        mwb.save(o)
        leaked = _leaked_cells(_cells(p), _cells(o), expected)
        print(f"   header word {tag!r:11s}: header_row detected = {header_row}   "
              f"plaintext values left in masked file = {sorted({v for _, v in leaked})}")
        out[tag] = {"header_row": header_row, "leaked": sorted({v for _, v in leaked})}
    return out


def part_c(detect) -> dict:
    import openpyxl
    import csv_format
    import excel_format
    print("\nC. realistic headers HEADER_KEYWORDS does not know -- XLSX vs CSV, same values")
    tot = {"xlsx": [0, 0], "csv": [0, 0]}
    per = {}
    for lang in spec.LANGS:
        hdr = UNKNOWN_HEADERS[lang]
        recs = spec.records(lang)
        expected = [(k, r[k]) for r in recs for k in NAME_FIELDS]

        px = harness.FIXTURES / f"e8_unknown_{lang}.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(hdr)
        for r in recs:
            ws.append([r[k] for k in NAME_FIELDS])
        wb.save(px)
        mwb, _ = excel_format.mask_workbook(px, detect, KEY)
        ox = px.with_suffix(".masked.xlsx")
        mwb.save(ox)
        lx = _leaked_cells(_cells(px), _cells(ox), expected)

        pc = harness.FIXTURES / f"e8_unknown_{lang}.csv"
        with open(pc, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(hdr)
            for r in recs:
                w.writerow([r[k] for k in NAME_FIELDS])
        fn, rws = csv_format.extract(pc)
        mrows, man = csv_format.mask_csv(fn, rws, detect, KEY)
        oc = [(f"{i}:{c}", r.get(c, "")) for i, r in enumerate(rws) for c in fn]
        mc = [(f"{i}:{c}", r.get(c, "")) for i, r in enumerate(mrows) for c in fn]
        lc = _leaked_cells(oc, mc, expected)
        n_cls = sum(1 for v in man["column_labels"].values() if v)

        tot["xlsx"][0] += len(lx); tot["xlsx"][1] += len(expected)
        tot["csv"][0] += len(lc); tot["csv"][1] += len(expected)
        per[lang] = {"xlsx_leaked": len(lx), "csv_leaked": len(lc),
                     "csv_columns_classified": n_cls, "expected": len(expected)}
        print(f"   {lang}: XLSX leaked {len(lx):>2}/{len(expected)}   "
              f"CSV leaked {len(lc):>2}/{len(expected)} (columns classified: {n_cls}/{len(fn)})")
    print(f"   TOTAL: XLSX {tot['xlsx'][0]}/{tot['xlsx'][1]} leaked, "
          f"CSV {tot['csv'][0]}/{tot['csv'][1]} leaked")
    return {"per_lang": per, "totals": tot}


def part_d(detect) -> dict:
    import openpyxl
    import excel_format
    out = {}
    print("\nD. structural cases")

    # D1: one person split across two cells
    p = harness.FIXTURES / "e8_split.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["A", "B"])
    people = [("Khani", "Abadov"), ("Gulanzar", "Shahsoltanova"), ("Nənə", "Sarvarli"),
              ("Vulkan", "Fuladlı"), ("Seyyab", "Garalov")]
    for gn, sn in people:
        ws.append([gn, sn])
    wb.save(p)
    mwb, man = excel_format.mask_workbook(p, detect, KEY)
    o = p.with_suffix(".masked.xlsx")
    mwb.save(o)
    exp = [("GIVENNAME", g) for g, _ in people] + [("SURNAME", s) for _, s in people]
    lk = _leaked_cells(_cells(p), _cells(o), exp)
    print(f"   D1 given name and surname in two cells: masked "
          f"{1 - len(lk) / len(exp):.0%}, leaked {sorted({v for _, v in lk})} "
          f"(no cross-cell joining exists)")
    out["split_cells_leaked"] = sorted({v for _, v in lk})

    # D2: several sheets with different names
    p = harness.FIXTURES / "e8_multisheet.xlsx"
    wb = openpyxl.Workbook()
    a = wb.active
    a.title = "Müştərilər"
    a.append(["Ad", "Soyad"])
    a.append(["Khani", "Abadov"])
    b = wb.create_sheet("Sheet2")
    b.append(["Telefon", "E-poçt"])
    b.append(["(051) 617-87-13", "s.humehrov@list.az"])
    c = wb.create_sheet("Пустой")
    c.append(["x"])
    c.append(["1"])
    wb.save(p)
    mwb, man = excel_format.mask_workbook(p, detect, KEY)
    sheets = list(man["sheets"].keys())
    o = p.with_suffix(".masked.xlsx")
    mwb.save(o)
    row = [c.value for c in openpyxl.load_workbook(o)["Müştərilər"][2]]
    print(f"   D2 multi-sheet: sheets processed {sheets}; row 2 of the first "
          f"sheet after masking: {row}")
    out["sheets"] = sheets
    out["multisheet_row_masked"] = row[0] != "Khani" and row[1] != "Abadov"

    # D3: merged title banner above the real header
    p = harness.FIXTURES / "e8_banner.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Müştəri Siyahısı", "", ""])
    ws.merge_cells("A1:C1")
    ws.append(["Ad", "Soyad", "Telefon"])
    ws.append(["Khani", "Abadov", "(051) 617-87-13"])
    wb.save(p)
    hr = excel_format._detect_header_row(openpyxl.load_workbook(p).active)
    mwb, _ = excel_format.mask_workbook(p, detect, KEY)
    o = p.with_suffix(".masked.xlsx")
    mwb.save(o)
    row = [c.value for c in openpyxl.load_workbook(o).active[3]]
    print(f"   D3 banner row: header row detected = {hr}; data row after masking: {row}")
    out["banner_header_row"] = hr
    out["banner_row_masked"] = row[0] != "Khani"
    return out


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.RESULTS.mkdir(parents=True, exist_ok=True)
    res = {"A": part_a(), "B": part_b(detect), "C": part_c(detect), "D": part_d(detect)}
    out = harness.RESULTS / "exp8_header_edge_cases.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
