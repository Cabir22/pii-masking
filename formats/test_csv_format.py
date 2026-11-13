"""Tests for formats/csv_format.py."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "model"))

from csv_format import (_dedupe_fieldnames, classify_column, extract,  # noqa: E402
                        mask_csv, unmask_csv, write_csv)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


KEY = b"\x04" * 16
tmp = Path(tempfile.mkdtemp())

# ---------------------------------------------------------------------------
print("1. classify_column")
# ---------------------------------------------------------------------------
check(classify_column("Telefon", ["0501234567"]) == "TELEPHONENUM",
      "header match: 'Telefon' -> TELEPHONENUM")
check(classify_column("Phone Number", ["0501234567"]) == "TELEPHONENUM",
      "header match is case/wording tolerant: 'Phone Number'")
check(classify_column("E-poçt", ["a@b.com"]) == "EMAIL",
      "header match: 'E-poçt' -> EMAIL")

# Real bug, found by running an actual generated Excel file and reading the
# output rather than only checking what earlier tests happened to assert:
# "ad" (GIVENNAME's own keyword) is a substring of "soyad" (SURNAME), so
# plain substring containment classified every Soyad column as GIVENNAME.
check(classify_column("Ad", ["Əli", "Aysel", "Rəşad"]) == "GIVENNAME",
      "'Ad' alone still correctly matches GIVENNAME")
check(classify_column("Soyad", ["Məmmədov", "Hüseynova", "Qasımov"]) == "SURNAME",
      "'Soyad' matches SURNAME, NOT GIVENNAME -- word-boundary matching "
      "fixes the substring collision with GIVENNAME's own 'ad' keyword")
check(classify_column("Final Score", ["85", "92", "78"]) is None,
      "a header merely CONTAINING a keyword substring ('Final' contains "
      "'fin') is not falsely matched to AZ_FIN")

# No header match, but the VALUES themselves are checksum-valid AZ_FIN codes.
check(classify_column("Kod", ["30LJV5Z", "7XKMN2P", "AB123CD"]) == "AZ_FIN",
      "value-pattern fallback classifies an unlabeled AZ_FIN-shaped column")

# Neither header nor values suggest a structured label -> free text.
check(classify_column("Qeydlər", ["Salam, hər şey yaxşıdır.",
                                  "Zəng edin zəhmət olmasa."]) is None,
      "ordinary prose is classified as free text (None)")

# Too few samples to trust a value-pattern guess.
check(classify_column("X", ["30LJV5Z"]) is None,
      "a single sample is not enough to trust a value-pattern guess")


# ---------------------------------------------------------------------------
print("2. extract() -- delimiter and encoding handling")
# ---------------------------------------------------------------------------
comma_path = tmp / "comma.csv"
comma_path.write_text("Ad,Telefon\nƏli,0501234567\n", encoding="utf-8")
fields, rows = extract(comma_path)
check(fields == ["Ad", "Telefon"] and rows == [{"Ad": "Əli", "Telefon": "0501234567"}],
      "comma-delimited CSV parses correctly", (fields, rows))

semi_path = tmp / "semi.csv"
semi_path.write_text("Ad;Telefon\nAysel;0559876543\n", encoding="utf-8")
fields2, rows2 = extract(semi_path)
check(fields2 == ["Ad", "Telefon"] and rows2[0]["Telefon"] == "0559876543",
      "semicolon-delimited CSV is auto-detected, not assumed comma",
      (fields2, rows2))

cp1251_path = tmp / "cp1251.csv"
cp1251_path.write_bytes("Имя,Город\nИван,Баку\n".encode("cp1251"))
fields3, rows3 = extract(cp1251_path)
check(rows3[0]["Имя"] == "Иван",
      "non-UTF-8 CSV falls back through chardet correctly", rows3)


# ---------------------------------------------------------------------------
print("2b. Phase 6: duplicate headers, empty file, ragged rows")
# ---------------------------------------------------------------------------
check(_dedupe_fieldnames(["Telefon", "Ad", "Telefon"]) ==
      ["Telefon", "Ad", "Telefon (2)"],
      "duplicate headers get a disambiguating suffix, not silently collapsed")
check(_dedupe_fieldnames(["Telefon", "Telefon", "Telefon"]) ==
      ["Telefon", "Telefon (2)", "Telefon (3)"],
      "three-way duplicates all get distinct names")

# TELEPHONENUM vs. AZ_VOEN: a bare 10-digit string is a valid shape for
# BOTH (data/schema.md's own documented, "unresolved-by-ordering" taxonomy
# collision). classify_column can't resolve genuine ambiguity, but it must
# be DETERMINISTIC -- the same input classified the same way every call,
# not dependent on Python's unordered-set iteration.
ambiguous_phones = ["0501234567", "0559876543", "0709998877", "0501112233"]
results = {classify_column("Data", ambiguous_phones) for _ in range(20)}
check(len(results) == 1,
      "classifying the same ambiguous (TELEPHONENUM/AZ_VOEN-shaped) column "
      "20 times in a row gives the SAME answer every time, not an "
      "iteration-order-dependent coin flip", results)
check(next(iter(results)) in ("TELEPHONENUM", "AZ_VOEN"),
      "the deterministic answer is at least one of the two genuinely "
      "plausible labels", results)
# Whichever one wins, the actual PROTECTION is identical either way -- both
# labels share model.masking's DIGIT_ALPHABET, so this ambiguity is a
# manifest-labeling question, not a masking-correctness one.
from masking import LABEL_ALPHABET  # noqa: E402
check(LABEL_ALPHABET["TELEPHONENUM"] == LABEL_ALPHABET["AZ_VOEN"],
      "confirms why the ambiguity above is cosmetic: both labels mask "
      "identically regardless of which one classify_column picks")

dup_path = tmp / "dup_headers.csv"
dup_path.write_text("Telefon,Ad,Telefon\n0501234567,Əli,0559999999\n",
                    encoding="utf-8")
fields_d, rows_d = extract(dup_path)
check(fields_d == ["Telefon", "Ad", "Telefon (2)"],
      "extract() disambiguates duplicate headers", fields_d)
check(rows_d[0]["Telefon"] == "0501234567"
      and rows_d[0]["Telefon (2)"] == "0559999999",
      "BOTH Telefon columns' data survive -- this was a real, verified "
      "data-loss bug in stdlib DictReader before this fix", rows_d[0])

empty_path = tmp / "empty.csv"
empty_path.write_text("", encoding="utf-8")
fields_e, rows_e = extract(empty_path)
check(fields_e == [] and rows_e == [],
      "a genuinely empty file returns empty fieldnames/rows, not a crash")

header_only_path = tmp / "header_only.csv"
header_only_path.write_text("Ad,Telefon\n", encoding="utf-8")
fields_h, rows_h = extract(header_only_path)
check(fields_h == ["Ad", "Telefon"] and rows_h == [],
      "a header-only file (no data rows) is handled cleanly")

ragged_path = tmp / "ragged.csv"
ragged_path.write_text("Ad,Telefon,VÖEN\nƏli,0501234567\n", encoding="utf-8")
fields_r, rows_r = extract(ragged_path)
check(rows_r[0]["VÖEN"] == "",
      "a row shorter than the header is padded, not dropped or crashed on",
      rows_r[0])
mc, mf = mask_csv(fields_r, rows_r, lambda t: [], KEY)
check(mc[0]["VÖEN"] == "",
      "a padded-empty cell stays empty through masking, no crash")


# ---------------------------------------------------------------------------
print("3. mask_csv / unmask_csv round-trip")
# ---------------------------------------------------------------------------
notes_ground_truth = {
    "Zəng edin, telefon nömrəm 0501234567-dir.":
        [{"start": 26, "end": 36, "label": "TELEPHONENUM"}],
    "Bakıda yaşayan Əli ilə əlaqə saxlayın.":
        [{"start": 0, "end": 6, "label": "CITY"},
         {"start": 15, "end": 18, "label": "GIVENNAME"}],
    "Heç bir problem yoxdur, sağ olun.": [],
}


def stub_detect(text):
    return notes_ground_truth.get(text, [])


header = ["Ad", "Soyad", "Telefon", "E-poçt", "VÖEN", "Qeydlər"]
data_rows = [
    {"Ad": "Əli", "Soyad": "Məmmədov", "Telefon": "0501234567",
     "E-poçt": "eli@example.com", "VÖEN": "1503613621",
     "Qeydlər": "Zəng edin, telefon nömrəm 0501234567-dir."},
    {"Ad": "Aysel", "Soyad": "Hüseynova", "Telefon": "0559876543",
     "E-poçt": "aysel@example.com", "VÖEN": "2716452839",
     "Qeydlər": "Bakıda yaşayan Əli ilə əlaqə saxlayın."},
    {"Ad": "Rəşad", "Soyad": "Qasımov", "Telefon": "0709998877",
     "E-poçt": "resad@example.com", "VÖEN": "9164606445",
     "Qeydlər": "Heç bir problem yoxdur, sağ olun."},
]

masked_rows, manifest = mask_csv(header, data_rows, stub_detect, KEY)

check(manifest["column_labels"]["Ad"] == "GIVENNAME",
      "Ad column classified correctly", manifest["column_labels"])
check(manifest["column_labels"]["Soyad"] == "SURNAME",
      "Soyad column classified correctly, NOT GIVENNAME -- this exact "
      "fixture is what let the substring-collision bug hide before: the "
      "columns were here, nothing checked what they classified as",
      manifest["column_labels"])
check(manifest["column_labels"]["Telefon"] == "TELEPHONENUM",
      "Telefon column classified correctly", manifest["column_labels"])
check(manifest["column_labels"]["VÖEN"] == "AZ_VOEN",
      "VÖEN column classified correctly", manifest["column_labels"])
check(manifest["column_labels"]["Qeydlər"] is None,
      "Qeydlər (notes) column classified as free text",
      manifest["column_labels"])

for i in range(3):
    check(masked_rows[i]["Telefon"] != data_rows[i]["Telefon"],
          f"row {i}: Telefon is actually masked, not left as-is",
          masked_rows[i]["Telefon"])
    check(len(masked_rows[i]["Telefon"]) == len(data_rows[i]["Telefon"]),
          f"row {i}: masked Telefon keeps the original length")

# EMAIL was header-matched (it's a STRUCTURED_LABEL) and now DOES have a
# reversible mask in model.masking (EMAIL_ALPHABET -- '@'/'.'/'-' stay in
# place as punctuation furniture, same as a phone number's spaces/dashes).
check(manifest["unsupported"] == [],
      "EMAIL is now masked, not reported as unsupported",
      manifest["unsupported"])
for i in range(3):
    check(masked_rows[i]["E-poçt"] != data_rows[i]["E-poçt"],
          f"row {i}: E-poçt is actually masked, not left as-is",
          masked_rows[i]["E-poçt"])
    check(len(masked_rows[i]["E-poçt"]) == len(data_rows[i]["E-poçt"]),
          f"row {i}: masked E-poçt keeps the original length")
    orig, masked = data_rows[i]["E-poçt"], masked_rows[i]["E-poçt"]
    check(masked.index("@") == orig.index("@")
          and [j for j, c in enumerate(masked) if c == "."]
          == [j for j, c in enumerate(orig) if c == "."],
          f"row {i}: '@' and every '.' stay at the exact same positions "
          f"(only the letters/digits either side are encrypted, the domain "
          f"letters included -- e.g. '.com' does NOT survive as literal "
          f"text, only its position does)",
          masked)

# Free-text column: PII inside actually changed, surrounding prose did not.
check(masked_rows[0]["Qeydlər"] != data_rows[0]["Qeydlər"],
      "free-text cell with embedded PII is actually modified")
check(masked_rows[2]["Qeydlər"] == data_rows[2]["Qeydlər"],
      "a free-text cell with NO detected PII is left untouched",
      masked_rows[2]["Qeydlər"])
check("Zəng edin, telefon nömrəm " in masked_rows[0]["Qeydlər"]
      and "-dir." in masked_rows[0]["Qeydlər"],
      "surrounding prose in a free-text cell survives untouched",
      masked_rows[0]["Qeydlər"])

# Full round trip.
recovered = unmask_csv(header, masked_rows, manifest, KEY)
check(recovered == data_rows,
      "unmask_csv recovers every row EXACTLY as originally written",
      recovered)


# ---------------------------------------------------------------------------
print("3b. Phase 6: a whole file with zero PII anywhere is a clean no-op")
# ---------------------------------------------------------------------------
nopii_header = ["Status", "Notes"]
nopii_rows = [{"Status": "Aktiv", "Notes": "Hər şey qaydasındadır."}
             for _ in range(5)]
nopii_masked, nopii_manifest = mask_csv(nopii_header, nopii_rows,
                                        lambda t: [], KEY)
check(nopii_masked == nopii_rows,
      "a file with no PII anywhere is byte-for-byte unchanged after "
      "masking, not accidentally altered")
check(unmask_csv(nopii_header, nopii_masked, nopii_manifest, KEY) == nopii_rows,
      "...and round-trips trivially since there was nothing to undo")


# ---------------------------------------------------------------------------
print("4. Full file round-trip (extract -> mask -> write -> extract -> unmask)")
# ---------------------------------------------------------------------------
src_path = tmp / "customers.csv"
write_csv(src_path, header, data_rows)
h2, r2 = extract(src_path)
masked2, manifest2 = mask_csv(h2, r2, stub_detect, KEY)
out_path = tmp / "customers.masked.csv"
write_csv(out_path, h2, masked2)

h3, r3 = extract(out_path)
recovered2 = unmask_csv(h3, r3, manifest2, KEY)
check(recovered2 == data_rows,
      "a real extract -> mask -> write-to-disk -> re-extract -> unmask "
      "round trip recovers the original data exactly", recovered2)


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
