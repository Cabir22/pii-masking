"""Drop-only passes on the clean LLM batches before the v3 build (D-45b, D-47).

  D-45b  --max-value-repeats N: one value (same label, same text) labelled N
         times or more; the rule batch 6 was cleaned with.
  D-47a  --drop-explained-typos: the model explains its own typo or OCR
         artifact (`vəziyyit (typo)`, `l0st (0/O qarışığı)`), any doc type.
  D-47b  --drop-formal-self-corrections: a bracketed self-correction
         (`aparılmalıddır (yox, aparılmalıdır)`) in a formal doc type; kept in
         chat, email and complaints (piigen.meta_noise.CONVERSATIONAL).
  D-47e  --drop-placeholders: an unfilled template slot (`[Məhkəmənin adı]`,
         `[Şirkət Adı]`), any doc type; form blanks (`[İmza]`) stay.
  C4     --drop-id ID: a document the leakage guard lists (a shadow or
         real-text barrier hit is reported by hash and id only).

The clean files are filtered, not re-cleaned from raw, because D-33a, D-35b
and D-36a were applied to them afterwards. A kept line is written byte for
byte; nothing is edited.

    python scripts/drop_before_v3.py data/raw/sprint1_llm_b1.clean.jsonl \
        --max-value-repeats 20 --drop-explained-typos --drop-formal-self-corrections \
        --in-place --report reports/d47/drop_b1.json
    ... --sample reports/d47/sample.jsonl     # what each rule catches, nothing written
Without --in-place/--out it only reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clean_llm_batch import most_repeated  # noqa: E402
from piigen.meta_noise import explained_typos, is_formal, placeholders, self_corrections  # noqa: E402


def reasons(rec: dict, args) -> dict[str, list]:
    """{rule: evidence} for every rule that drops this record."""
    out = {}
    if args.max_value_repeats and most_repeated(rec) >= args.max_value_repeats:
        c = Counter((e["label"], rec["text"][e["start"]:e["end"]]) for e in rec["entities"])
        (label, _), times = c.most_common(1)[0]
        out["D-45b"] = [f"{label} x{times}"]
    if args.drop_explained_typos and (hits := explained_typos(rec["text"])):
        out["D-47a"] = hits
    if args.drop_formal_self_corrections and is_formal(rec.get("_doc_type")) \
            and (hits := self_corrections(rec["text"])):
        out["D-47b"] = hits
    if args.drop_placeholders and (hits := placeholders(rec["text"])):
        out["D-47e"] = hits
    if rec["id"] in (args.drop_id or ()):
        out["C4"] = ["listed by the leakage guard"]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--max-value-repeats", type=int, default=None, metavar="N")
    ap.add_argument("--drop-explained-typos", action="store_true")
    ap.add_argument("--drop-formal-self-corrections", action="store_true")
    ap.add_argument("--drop-placeholders", action="store_true")
    ap.add_argument("--drop-id", action="append", metavar="ID",
                    help="drop this id (a leakage-guard hit); repeatable")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--in-place", action="store_true")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--sample", type=Path, help="append every dropped record's id, rules and evidence (JSONL)")
    args = ap.parse_args(argv)

    lines = args.batch.read_bytes().splitlines(keepends=True)
    kept, dropped = [], []
    for line in lines:
        if not line.strip():
            continue
        rec = json.loads(line)
        why = reasons(rec, args)
        if why:
            dropped.append({"id": rec["id"], "doc_type": rec.get("_doc_type"), "rules": why})
        else:
            kept.append(line if line.endswith(b"\n") else line + b"\n")
    data = b"".join(kept)
    by_rule = Counter(r for d in dropped for r in d["rules"])
    report = {"batch": str(args.batch), "max_value_repeats": args.max_value_repeats,
              "drop_explained_typos": args.drop_explained_typos,
              "drop_formal_self_corrections": args.drop_formal_self_corrections,
              "drop_placeholders": args.drop_placeholders, "drop_ids": args.drop_id or [],
              "documents in": len(kept) + len(dropped), "documents out": len(kept),
              "dropped by rule (a document can match several)": dict(by_rule),
              "dropped": dropped, "sha256_out": hashlib.sha256(data).hexdigest()}
    print(f"{args.batch.name}: {report['documents in']:,} -> {len(kept):,} "
          f"({len(dropped)} dropped; by rule {dict(by_rule)})")
    print("sha256 out:", report["sha256_out"])
    if args.sample:
        with args.sample.open("a", encoding="utf-8") as fh:
            for d in dropped:
                fh.write(json.dumps({"batch": args.batch.name, **d}, ensure_ascii=False) + "\n")
    target = args.batch if args.in_place else args.out
    if target:
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        print("written ->", target)
    else:
        print("(report only -- pass --in-place or --out to write)")
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
