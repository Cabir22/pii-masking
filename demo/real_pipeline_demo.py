# -*- coding: utf-8 -*-
"""Manual, human-readable verification of the full TXT/Excel pipeline
against REAL data -- not part of the automated test suite (deliberately:
every test_*.py in this repo runs with no downloaded model weights, per
the policy stated in model/test_predict.py's own docstring; this script
downloads and runs the actual your-hf-org/masking-multilingual checkpoint from
Hugging Face Hub, which is slow and requires network + `hf auth login`).

Run this after any change to detect_fn/masking/format code to eyeball real
before/after output on real data, not just green test output. Two samples:

  1. TXT: an ACTUAL document from data/processed/merged/test.docs.jsonl,
     gold labels and all -- a genuine gold-vs-predicted comparison, not
     just "does this look masked".
  2. Excel: real corpus-generated entity VALUES (not invented) assembled
     into a demo customer table -- the table structure is illustrative,
     the cell values are authentic model-training data.

Usage:
    python demo/real_pipeline_demo.py [output_dir]

Writes sample_{original,masked}_corpus.{txt,xlsx} to `output_dir`
(default: this script's own directory) and prints a gold-vs-predicted
comparison plus round-trip verification to stdout.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "formats"))

from predict import load_model, hybrid_detect_entities  # noqa: E402
import txt as txt_fmt                                   # noqa: E402
import excel_format as xl_fmt                            # noqa: E402
import openpyxl                                          # noqa: E402

KEY = bytes.fromhex("a1b2c3d4e5f60718293a4b5c6d7e8f90")
CHECKPOINT = "your-hf-org/masking-multilingual"

# A real corpus document, chosen for covering several entity types at once
# (GIVENNAME, DATE, AZ_PASSPORT_NUMBER, TELEPHONENUM, EMAIL) in one short,
# realistic document.
TXT_SAMPLE_DOC_ID = "repaired.clean__llm_az_001707"

# Real generated entity VALUES pulled from the corpus (the pattern-tier
# detection gaps this pipeline's hybrid_detect_entities was built to close), assembled into a demo customer table.
EXCEL_SAMPLE_VALUES = {
    "GIVENNAME": ["Poladxan", "Ruslan", "Elmira", "Eyyubxan"],
    "SURNAME": ["Mustafali", "Əzəmov", "Xəlilli", "Əhsənzadə"],
    "TELEPHONENUM": ["(055) 332-93-91", "+994 12 943 29 52",
                     "010 166 78 72", "099-808-31-91"],
    "EMAIL": ["mexfire.henifeyev@araz-mebel.az", "m.sefiyev@company.az",
             "efken.serxeyilov@bakutech.az", "heyreddin.afiqov@icloud.com"],
    "AZ_VOEN": ["9104446531", "8772503301", "9962803868", "8768001742"],
    "CITY": ["Astara", "İmişli", "Ağstafa", "Naxçıvan"],
}
EXCEL_NOTE_TEMPLATES = [
    "{city} filialına göndərilib, əlaqə: {phone}.",
    "Sifariş təsdiqləndi, VÖEN yoxlanıldı.",
    "Zəng gözlənilir, hələ cavab yoxdur.",
    "{city} anbarından çatdırılacaq.",
]


def _load_txt_sample_doc() -> dict:
    with open(ROOT / "data/processed/merged/test.docs.jsonl", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            if d.get("id") == TXT_SAMPLE_DOC_ID:
                return d
    raise LookupError(f"{TXT_SAMPLE_DOC_ID} not found in test.docs.jsonl")


def run_txt_demo(out_dir: Path, detect) -> bool:
    doc = _load_txt_sample_doc()
    original = doc["text"]
    gold = {(e.get("label") or e.get("type"), original[e["start"]:e["end"]])
            for e in doc.get("entities", doc.get("labels", []))}

    txt_path = out_dir / "sample_original_corpus.txt"
    with open(txt_path, "w", encoding="utf-8", newline="") as f:
        f.write(original)

    extracted = txt_fmt.extract(txt_path)
    assert extracted == original

    detected = detect(extracted)
    masked_text, used_spans, unsupported = txt_fmt.mask_text(extracted, detect, KEY)
    (out_dir / "sample_masked_corpus.txt").write_text(masked_text, encoding="utf-8")
    recovered = txt_fmt.unmask_text(masked_text, used_spans, KEY)
    round_trip_ok = recovered == original

    pred = {(p["label"], p["text"]) for p in detected}
    print("=" * 70)
    print(f"TXT DEMO -- real corpus document {TXT_SAMPLE_DOC_ID}")
    print("=" * 70)
    print(f"gold entities found : {len(gold & pred)}/{len(gold)}")
    print(f"missing              : {gold - pred}")
    print(f"extra (beyond gold)  : {pred - gold}")
    print(f"unsupported          : {unsupported}")
    print(f"round-trip exact     : {round_trip_ok}")
    return round_trip_ok and gold <= pred


def run_excel_demo(out_dir: Path, detect) -> bool:
    n_rows = 4
    xlsx_path = out_dir / "sample_original_corpus.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Müştərilər"
    headers = ["Ad", "Soyad", "Telefon", "E-poçt", "VÖEN", "Şəhər", "Qeydlər"]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    for r in range(n_rows):
        city = EXCEL_SAMPLE_VALUES["CITY"][r]
        phone = EXCEL_SAMPLE_VALUES["TELEPHONENUM"][r]
        row = [EXCEL_SAMPLE_VALUES["GIVENNAME"][r], EXCEL_SAMPLE_VALUES["SURNAME"][r],
               phone, EXCEL_SAMPLE_VALUES["EMAIL"][r], EXCEL_SAMPLE_VALUES["AZ_VOEN"][r],
               city, EXCEL_NOTE_TEMPLATES[r].format(city=city, phone=phone)]
        for c, val in enumerate(row, 1):
            ws.cell(row=r + 2, column=c, value=val)
    wb.save(xlsx_path)

    masked_wb, manifest = xl_fmt.mask_workbook(xlsx_path, detect, KEY)
    masked_path = out_dir / "sample_masked_corpus.xlsx"
    masked_wb.save(masked_path)

    restored_wb = xl_fmt.unmask_workbook(masked_path, manifest, KEY)
    ws_orig = openpyxl.load_workbook(xlsx_path)["Müştərilər"]
    ws_restored = restored_wb["Müştərilər"]
    round_trip_ok = all(
        ws_restored.cell(row=r, column=c).value == ws_orig.cell(row=r, column=c).value
        for r in range(1, n_rows + 2) for c in range(1, len(headers) + 1))

    sheet_manifest = manifest["sheets"]["Müştərilər"]
    print()
    print("=" * 70)
    print("EXCEL DEMO -- real corpus VALUES in a demo customer table")
    print("=" * 70)
    print("column classification:", sheet_manifest["column_labels"])
    print(f"unsupported cells   : {len(sheet_manifest['unsupported'])}")
    print(f"round-trip exact    : {round_trip_ok}")
    return round_trip_ok


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    out_dir = Path(args[0]) if args else Path(__file__).resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading {CHECKPOINT} ...", file=sys.stderr)
    model, tokenizer, id2label = load_model(CHECKPOINT)
    print("Model loaded.", file=sys.stderr)

    def detect(text: str) -> list[dict]:
        return hybrid_detect_entities(text, model, tokenizer, id2label)

    txt_ok = run_txt_demo(out_dir, detect)
    excel_ok = run_excel_demo(out_dir, detect)

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"TXT   : {'PASS' if txt_ok else 'CHECK OUTPUT ABOVE'}")
    print(f"Excel : {'PASS' if excel_ok else 'CHECK OUTPUT ABOVE'}")
    print(f"\nfiles written to: {out_dir}")
    return 0 if (txt_ok and excel_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
