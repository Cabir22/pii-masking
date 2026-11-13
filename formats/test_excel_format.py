"""Tests for formats/excel_format.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

import openpyxl  # noqa: E402
from excel_format import (_detect_header_row, _promote_unclassified_columns,  # noqa: E402
                          mask_workbook, unmask_workbook)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


KEY = b"\x05" * 16
tmp = Path(tempfile.mkdtemp())

notes_ground_truth = {
    "Bakıda yaşayan Əli ilə əlaqə saxlayın.":
        [{"start": 0, "end": 6, "label": "CITY"},
         {"start": 15, "end": 18, "label": "GIVENNAME"}],
}


def stub_detect(text):
    return notes_ground_truth.get(text, [])


# ---------------------------------------------------------------------------
print("0a. Phase 6: blank / header-only workbooks, malformed file")
# ---------------------------------------------------------------------------
blank_path = tmp / "blank.xlsx"
openpyxl.Workbook().save(blank_path)
try:
    _, blank_manifest = mask_workbook(blank_path, stub_detect, KEY)
    check(blank_manifest["sheets"]["Sheet"]["column_labels"] == {},
          "a genuinely blank workbook is handled without crashing")
except Exception as e:
    check(False, "a genuinely blank workbook is handled without crashing",
          f"{type(e).__name__}: {e}")

header_only_path = tmp / "header_only.xlsx"
how = openpyxl.Workbook()
how.active["A1"] = "Ad"
how.active["B1"] = "Telefon"
how.save(header_only_path)
try:
    _, ho_manifest = mask_workbook(header_only_path, stub_detect, KEY)
    check(ho_manifest["sheets"]["Sheet"]["column_labels"].get("Telefon")
          == "TELEPHONENUM",
          "a header-only workbook (zero data rows) still classifies "
          "columns correctly and doesn't crash on an empty data range")
except Exception as e:
    check(False, "a header-only workbook doesn't crash", f"{type(e).__name__}: {e}")

fake_xlsx_path = tmp / "fake.xlsx"
fake_xlsx_path.write_text("this is not a real xlsx file", encoding="utf-8")
try:
    mask_workbook(fake_xlsx_path, stub_detect, KEY)
    check(False, "a non-XLSX file raises a clear error rather than "
         "succeeding on garbage")
except ValueError as e:
    check(".xlsx" in str(e) and "not be read" in str(e),
          "a non-XLSX file raises a CLEAR, actionable error rather than "
          "openpyxl's raw 'BadZipFile' message", str(e))
except Exception as e:
    check(False, "a non-XLSX file raises ValueError with a clear message, "
         "not some other unwrapped exception type",
         f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
print("0c. Phase 6+: a genuinely headerless workbook (row 1 IS data)")
# ---------------------------------------------------------------------------
# Real gap, confirmed by actually building this file and running it through
# mask_workbook BEFORE the fix: row 1 got silently read as column HEADER
# TEXT (never masked) instead of the first customer's real PII, which
# leaked completely unmasked into the "masked" output.
headerless_path = tmp / "headerless.xlsx"
hw = openpyxl.Workbook()
hws = hw.active
headerless_rows = [
    ("Əli", "Məmmədov", "0501234567", "eli.mammadov@example.com"),
    ("Aysel", "Hüseynova", "0559876543", "aysel.huseynova@example.com"),
    ("Rəşad", "Qasımov", "0709998877", "resad.qasimov@example.com"),
]
for r_idx, row in enumerate(headerless_rows, 1):  # starts at row 1, no header
    for c_idx, val in enumerate(row, 1):
        hws.cell(row=r_idx, column=c_idx, value=val)
hw.save(headerless_path)

check(_detect_header_row(hws) == 0,
      "a row whose own cells are verified real data (a real phone number, "
      "a real email) is never mistaken for a header row",
      _detect_header_row(hws))

headerless_masked_wb, headerless_manifest = mask_workbook(
    headerless_path, stub_detect, KEY)
hm = headerless_manifest["sheets"]["Sheet"]
check(hm["header_row"] == 0, "manifest records the headerless sentinel")
check(hm["column_labels"].get("Column C") == "AZ_VOEN"
      and hm["column_labels"].get("Column D") == "EMAIL",
      "phone/email columns are still classified correctly from their "
      "VALUES alone, with no header text to help",
      hm["column_labels"])

hmc = headerless_masked_wb["Sheet"]
check(str(hmc.cell(row=1, column=3).value) != "0501234567",
      "row 1's phone number IS masked -- this is the actual leak this fix "
      "closes: before it, row 1 was treated as the header and never "
      "masked at all", hmc.cell(row=1, column=3).value)
check(str(hmc.cell(row=1, column=4).value) != "eli.mammadov@example.com",
      "row 1's email is masked too", hmc.cell(row=1, column=4).value)

headerless_masked_path = tmp / "headerless.masked.xlsx"
headerless_masked_wb.save(headerless_masked_path)
headerless_restored = unmask_workbook(
    headerless_masked_path, headerless_manifest, KEY)
hrc = headerless_restored["Sheet"]
check(hrc.cell(row=1, column=1).value == "Əli"
      and hrc.cell(row=1, column=3).value == "0501234567"
      and hrc.cell(row=3, column=4).value == "resad.qasimov@example.com",
      "full mask -> save -> unmask round trip recovers every row exactly, "
      "including row 1",
      (hrc.cell(row=1, column=1).value, hrc.cell(row=1, column=3).value,
       hrc.cell(row=3, column=4).value))


# ---------------------------------------------------------------------------
print("0d. Column-consensus promotion: a name the detector misses ALONE is "
      "still masked if the rest of its column agrees")
# ---------------------------------------------------------------------------
# Reproduces a real, confirmed case: probing the actual model directly found
# "Ruslan" alone scores well under its confidence threshold (33%) while
# "Poladxan" alone scores 93% -- both real, well-represented training
# values, same entity type, different per-word luck in total isolation.
# This stub reproduces exactly that asymmetry without needing the real
# checkpoint: two GIVENNAME-shaped words the stub confidently tags whole-
# cell, one ("Ruslan") it does not, mirroring the real measured gap.
def consensus_detect(text: str) -> list[dict]:
    given = {"Poladxan": "GIVENNAME", "Elmira": "GIVENNAME"}
    surname = {"Əzəmov": "SURNAME", "Xəlilli": "SURNAME", "Mustafali": "SURNAME"}
    if text in given:
        return [{"start": 0, "end": len(text), "label": given[text], "text": text}]
    if text in surname:
        return [{"start": 0, "end": len(text), "label": surname[text], "text": text}]
    return []  # "Ruslan" (deliberately) and everything else: no detection


consensus_path = tmp / "consensus_headerless.xlsx"
cw = openpyxl.Workbook()
cws = cw.active
# A real phone number in column C gives _detect_header_row the positive
# evidence it needs to recognize row 1 as data, not a header -- an
# all-name table (no pattern-tier column at all) has no such evidence and
# would be a different, already-covered case (test 0c above).
consensus_rows = [
    ("Ruslan", "Əzəmov", "0501234561"),
    ("Poladxan", "Mustafali", "0501234568"),
    ("Elmira", "Xəlilli", "0501234560"),
]
for r_idx, row in enumerate(consensus_rows, 1):  # headerless
    for c_idx, val in enumerate(row, 1):
        cws.cell(row=r_idx, column=c_idx, value=val)
cw.save(consensus_path)

consensus_masked_wb, consensus_manifest = mask_workbook(
    consensus_path, consensus_detect, KEY)
cm = consensus_manifest["sheets"]["Sheet"]
check(cm["column_labels"].get("Column A") == "GIVENNAME",
      "a column where 2/3 cells confidently agree on GIVENNAME gets "
      "promoted to it, even though the detector alone missed the third",
      cm["column_labels"])
check(cm["column_labels"].get("Column B") == "SURNAME",
      "same promotion for the surname column (3/3 agree)",
      cm["column_labels"])

cmc = consensus_masked_wb["Sheet"]
check(cmc.cell(row=1, column=1).value != "Ruslan",
      "the cell the detector missed alone IS masked anyway, via column "
      "consensus -- this is the actual fix, not just the promotion label",
      cmc.cell(row=1, column=1).value)

consensus_masked_path = tmp / "consensus_headerless.masked.xlsx"
consensus_masked_wb.save(consensus_masked_path)
consensus_restored = unmask_workbook(
    consensus_masked_path, consensus_manifest, KEY)
crc = consensus_restored["Sheet"]
check(crc.cell(row=1, column=1).value == "Ruslan"
      and crc.cell(row=2, column=1).value == "Poladxan"
      and crc.cell(row=3, column=2).value == "Xəlilli",
      "full round trip recovers every cell exactly, including the "
      "consensus-promoted one",
      (crc.cell(row=1, column=1).value, crc.cell(row=2, column=1).value,
       crc.cell(row=3, column=2).value))

# Guardrails: no promotion without real agreement.
no_consensus_path = tmp / "no_consensus.xlsx"
ncw = openpyxl.Workbook()
ncws = ncw.active
for r_idx, val in enumerate(["Astara", "Poladxan", "random text here",
                             "another unrelated cell"], 1):
    ncws.cell(row=r_idx, column=1, value=val)
ncw.save(no_consensus_path)


def disagreeing_detect(text: str) -> list[dict]:
    if text == "Astara":
        return [{"start": 0, "end": len(text), "label": "CITY", "text": text}]
    if text == "Poladxan":
        return [{"start": 0, "end": len(text), "label": "GIVENNAME", "text": text}]
    return []


_, no_consensus_manifest = mask_workbook(
    no_consensus_path, disagreeing_detect, KEY)
check(no_consensus_manifest["sheets"]["Sheet"]["column_labels"].get("Column A")
      is None,
      "a column whose matched cells TIE (1 CITY vs 1 GIVENNAME, no real "
      "majority) is never promoted -- too ambiguous to trust",
      no_consensus_manifest["sheets"]["Sheet"]["column_labels"])

# Regression test for a real, confirmed leak: a 10-row GIVENNAME column
# where per-cell detection alone found 5 GIVENNAME, 1 CITY (the model's own
# known GIVENNAME/CITY confusion on an isolated word) and 4 nothing at all.
# Under the old unanimity rule that single CITY cell blocked promotion
# entirely, leaving all 4 no-detection cells -- real names -- unmasked in
# the actual output file. A real majority (5 of 6 matched cells) must still
# promote the column and mask every cell, including the disagreeing one.
majority_path = tmp / "majority_override.xlsx"
mow = openpyxl.Workbook()
mows = mow.active
majority_values = ["Sambey", "Ozgune", "Mingul", "Logman", "Cannatali",
                   "Gazi", "Mutubey", "Muzayyam", "Saday", "Nutvali"]
# A real phone number in column B gives _detect_header_row the positive
# evidence it needs to treat row 1 as data, not a header -- same technique
# test 0d's own consensus_rows fixture uses above, needed here because a
# single all-names column has no pattern-tier signal of its own.
for r_idx, val in enumerate(majority_values, 1):
    mows.cell(row=r_idx, column=1, value=val)
    mows.cell(row=r_idx, column=2, value=f"050123456{r_idx % 10}")
mow.save(majority_path)


def majority_detect(text: str) -> list[dict]:
    given = {"Ozgune", "Mingul", "Logman", "Cannatali", "Muzayyam"}
    if text in given:
        return [{"start": 0, "end": len(text), "label": "GIVENNAME", "text": text}]
    if text == "Nutvali":  # the model's own real GIVENNAME/CITY confusion
        return [{"start": 0, "end": len(text), "label": "CITY", "text": text}]
    return []  # Sambey/Gazi/Mutubey/Saday: no detection alone, same as real probe


_, majority_manifest = mask_workbook(majority_path, majority_detect, KEY)
mm = majority_manifest["sheets"]["Sheet"]
check(mm["column_labels"].get("Column A") == "GIVENNAME",
      "a 5-GIVENNAME/1-CITY real majority still promotes the column, "
      "despite the single disagreeing cell",
      mm["column_labels"])

majority_masked_wb, _ = mask_workbook(majority_path, majority_detect, KEY)
mmc = majority_masked_wb["Sheet"]
check(all(mmc.cell(row=r, column=1).value != v
          for r, v in enumerate(majority_values, 1)),
      "every cell in the promoted column is masked, including the 4 the "
      "detector missed alone and the 1 it mislabeled CITY -- this is the "
      "actual leak the majority-override fix closes",
      [mmc.cell(row=r, column=1).value for r in range(1, len(majority_values) + 1)])

single_match_path = tmp / "single_match.xlsx"
smw = openpyxl.Workbook()
smws = smw.active
for r_idx, val in enumerate(["Poladxan"] + [f"note {i}" for i in range(6)], 1):
    smws.cell(row=r_idx, column=1, value=val)
smw.save(single_match_path)


def one_hit_detect(text: str) -> list[dict]:
    if text == "Poladxan":
        return [{"start": 0, "end": len(text), "label": "GIVENNAME", "text": text}]
    return []


_, single_match_manifest = mask_workbook(single_match_path, one_hit_detect, KEY)
check(single_match_manifest["sheets"]["Sheet"]["column_labels"].get("Column A")
      is None,
      "a single matching cell out of 7 is NOT enough support to promote "
      "the whole column (below both the min-count and min-fraction floor)",
      single_match_manifest["sheets"]["Sheet"]["column_labels"])


# ---------------------------------------------------------------------------
print("0. Phase 6: header-row detection (a title banner ABOVE the header)")
# ---------------------------------------------------------------------------
# This is exactly the fixture Phase 4 built, hit, and deliberately abandoned
# ("informational, not tested as if handled") because _MAX_HEADER_ROW was a
# fixed constant back then -- now that _detect_header_row exists, this is
# the real test that gap is actually closed, not just documented.
banner_path = tmp / "banner_header.xlsx"
bwb = openpyxl.Workbook()
bws = bwb.active
bws.title = "Customers"
bws.merge_cells("A1:D1")
bws["A1"] = "Müştəri Siyahısı"
bws["A2"] = "Ad"
bws["B2"] = "Telefon"
bws["C2"] = "VÖEN"
bws["D2"] = "Qeydlər"
bws["A3"] = "Əli"
bws["B3"] = "0501234567"
bws["C3"] = "1503613621"
bws["D3"] = "Heç bir problem yoxdur."
bwb.save(banner_path)

check(_detect_header_row(bws) == 2,
      "a title banner merged across row 1 is correctly skipped; row 2 "
      "(the real header) is detected instead", _detect_header_row(bws))

banner_masked_wb, banner_manifest = mask_workbook(banner_path, stub_detect, KEY)
check(banner_manifest["sheets"]["Customers"]["header_row"] == 2,
      "the detected header row is recorded in the manifest")
check(banner_manifest["sheets"]["Customers"]["column_labels"].get("Telefon")
      == "TELEPHONENUM",
      "columns are classified from the REAL header (row 2), not the "
      "banner text", banner_manifest["sheets"]["Customers"]["column_labels"])
bmc = banner_masked_wb["Customers"]
check(bmc["A1"].value == "Müştəri Siyahısı",
      "the banner cell itself is completely untouched")
check(str(bmc["B3"].value) != "0501234567",
      "the actual data row (row 3, below the detected header) was masked")

banner_masked_path = tmp / "banner_header.masked.xlsx"
banner_masked_wb.save(banner_masked_path)
banner_restored = unmask_workbook(banner_masked_path, banner_manifest, KEY)
brc = banner_restored["Customers"]
check(brc["A1"].value == "Müştəri Siyahısı" and brc["A2"].value == "Ad"
      and brc["B3"].value == "0501234567",
      "full mask -> save -> unmask round trip recovers everything exactly, "
      "banner and header both left alone throughout",
      (brc["A1"].value, brc["A2"].value, brc["B3"].value))


# ---------------------------------------------------------------------------
print("1. Build a realistic multi-sheet workbook, header row + a merge "
      "elsewhere on the sheet")
# ---------------------------------------------------------------------------
src_path2 = tmp / "customers_clean.xlsx"
wb2 = openpyxl.Workbook()
c1 = wb2.active
c1.title = "Customers"
c1["A1"] = "Ad"
c1["B1"] = "Telefon"
c1["C1"] = "VÖEN"
c1["D1"] = "Qeydlər"
c1["A2"] = "Əli"
c1["B2"] = 501234567
c1["C2"] = "1503613621"
c1["D2"] = "Bakıda yaşayan Əli ilə əlaqə saxlayın."
c1["A3"] = "Aysel"
c1["B3"] = "0559876543"
c1["C3"] = "2716452839"
c1["D3"] = "Heç bir problem yoxdur."
# a merged range elsewhere on the sheet (e.g. a footer note), well clear of
# the header/data -- must not crash mask_workbook.
c1.merge_cells("A5:D5")
c1["A5"] = "Qeyd: bütün məlumatlar test üçündür."

c2 = wb2.create_sheet("Orders")
c2["A1"] = "Sifariş"
c2["B1"] = "Telefon"
c2["A2"] = "ORD-001"
c2["B2"] = "0709998877"

wb2.save(src_path2)

print("2. mask_workbook: correctness per sheet, per gotcha")
masked_wb2, manifest2 = mask_workbook(src_path2, stub_detect, KEY)
cust2 = manifest2["sheets"]["Customers"]
orders2 = manifest2["sheets"]["Orders"]

check(cust2["column_labels"]["Ad"] == "GIVENNAME",
      "Customers.Ad classified correctly", cust2["column_labels"])
check(cust2["column_labels"]["Telefon"] == "TELEPHONENUM",
      "Customers.Telefon classified correctly", cust2["column_labels"])
check(cust2["column_labels"]["VÖEN"] == "AZ_VOEN",
      "Customers.VÖEN classified correctly")
check(cust2["column_labels"]["Qeydlər"] is None,
      "Customers.Qeydlər classified as free text")
check(orders2["column_labels"]["Telefon"] == "TELEPHONENUM",
      "Orders.Telefon (SAME header name, different sheet) classified "
      "independently and correctly")

masked_c1 = masked_wb2["Customers"]
masked_c2 = masked_wb2["Orders"]

check(str(masked_c1["B2"].value) != "501234567",
      "the numeric-typed phone cell was actually masked",
      masked_c1["B2"].value)
check(isinstance(masked_c1["B2"].value, str),
      "a masked cell is written back as TEXT even though the original was "
      "numeric -- deliberate, documented trade-off (avoids losing a "
      "leading zero a second time)", type(masked_c1["B2"].value))
check(len(str(masked_c1["B2"].value)) == len("501234567"),
      "masked numeric-origin cell keeps the original digit count")

check(masked_c1["A5"].value == "Qeyd: bütün məlumatlar test üçündür.",
      "a multi-column-merged banner/footer row is correctly recognized as "
      "NOT table data and left completely untouched, not corrupted by "
      "being treated as an ordinary column-A value",
      masked_c1["A5"].value)

check(masked_c1["D2"].value != "Bakıda yaşayan Əli ilə əlaqə saxlayın.",
      "free-text cell's PII is actually masked, not left as the original "
      "sentence", masked_c1["D2"].value)

masked_out = tmp / "customers_clean.masked.xlsx"
masked_wb2.save(masked_out)


# ---------------------------------------------------------------------------
print("3. unmask_workbook: full round trip via real files on disk")
# ---------------------------------------------------------------------------
restored_wb = unmask_workbook(masked_out, manifest2, KEY)
r1 = restored_wb["Customers"]
r2 = restored_wb["Orders"]

check(r1["A1"].value == "Ad" and r1["B1"].value == "Telefon",
      "header row survives untouched")
check(str(r1["B2"].value) == "501234567",
      "the originally-numeric phone cell recovers its correct digit "
      "sequence (as text -- the type itself is not recoverable, only the "
      "value, which is the documented trade-off)", r1["B2"].value)
check(r1["B3"].value == "0559876543",
      "the originally-text phone cell round-trips exactly")
check(r1["C2"].value == "1503613621" and r1["C3"].value == "2716452839",
      "VÖEN column round-trips exactly for both rows")
check(r1["D2"].value == "Bakıda yaşayan Əli ilə əlaqə saxlayın.",
      "free-text cell recovers the EXACT original sentence", r1["D2"].value)
check(r1["D3"].value == "Heç bir problem yoxdur.",
      "a free-text cell with no detected PII round-trips unchanged (it was "
      "never touched in the first place)")
check(r1["A5"].value == "Qeyd: bütün məlumatlar test üçündür.",
      "the untouched merged-range cell is still correct after the full "
      "mask -> save -> unmask cycle")
check(r2["B2"].value == "0709998877",
      "the Orders sheet (independent classification) round-trips correctly")


import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for f in FAILURES[:25]:
    print("  FAIL:", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
