"""Audit the old corpus's Azerbaijani documents with today's checks (P2-16, D-23b).

    python scripts/audit_az_corpus.py                       # writes az_drop_list.jsonl + a report
    python scripts/audit_az_corpus.py --limit 3000          # a quick trial on the first 3,000 az documents

Reads the `lang == "az"` documents of data/processed/merged_relabeled_swept_dated
(train, val, test) and NEVER writes to the corpus: the output is a drop list that
`build_sprint_mix.py` (P4-14) leaves out.

A document is on the drop list when it fails ANY of these (A2.4: training data must
pass the blocking checks; the review of PR #27):
  every MUST-BE-ZERO check of scripts/validate_corpus.py, named as the reason
      (planned_value_unlabelled, unlabeled_pii_leak, validator_failure,
      resolver_drift, repeat_mention_incomplete, ...)
  unplanned_pii             a city, street, building number or full name nobody labelled
                            (D-15c, as in clean_llm_batch.py --drop-unplanned-pii)
  unlabelled_standalone_date  D-18c: a standalone date no DATE label covers (dropped,
                            never relabelled)
  turkish                   Turkish lexis or orthography in Azerbaijani text

`cyrillic_present` and the other non-blocking checks are only counted (`informational`).
At the end the kept set (az documents minus the drop list) is written to a temp file and
validate_corpus.py runs on it: it must exit 0, or this script exits 1.

The old records store entities without their `text`; validate_corpus needs it, so the
audit fills it in from the offsets in a temp copy.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.audit_llm_batch import unplanned_pii                   # noqa: E402
from piigen.standalone_dates import find_unlabelled_dates          # noqa: E402
from piigen.validate import declared_decoy_spans, turkish_contamination  # noqa: E402

CORPUS = ROOT / "data" / "processed" / "merged_relabeled_swept_dated"
SPLITS = ("train", "val", "test")
INFORMATIONAL = ("cyrillic_present",)
# the reason named first when a document fails several; the rest follow alphabetically
FIRST = ("planned_value_unlabelled", "unlabeled_pii_leak", "unplanned_pii",
         "unlabelled_standalone_date", "turkish")


def reason_key(r: str):
    return (FIRST.index(r), r) if r in FIRST else (len(FIRST), r)


def az_records(corpus: Path, limit: int | None):
    n = 0
    for split in SPLITS:
        with (corpus / f"{split}.docs.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                rec = json.loads(line)
                if rec.get("lang") != "az":
                    continue
                yield split, rec
                n += 1
                if limit and n >= limit:
                    return


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=CORPUS)
    ap.add_argument("--out", type=Path, default=None, help="default: <corpus>/az_drop_list.jsonl")
    ap.add_argument("--report", type=Path, default=ROOT / "reports" / "p2_16" / "az_audit.json")
    ap.add_argument("--limit", type=int, default=None, help="audit only the first N az documents")
    args = ap.parse_args()
    out = args.out or args.corpus / "az_drop_list.jsonl"

    reasons: dict[str, set] = {}
    split_of: dict[str, str] = {}
    totals = Counter()
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        filled = tmp / "az.jsonl"
        with filled.open("w", encoding="utf-8", newline="") as fh:
            for split, rec in az_records(args.corpus, args.limit):
                rid = str(rec["id"])
                if rid in split_of:
                    print(f"duplicate id inside the az documents: {rid}")
                    return 2
                split_of[rid] = split
                totals[split] += 1
                text = rec.get("text") or ""
                for e in rec.get("entities") or []:
                    e.setdefault("text", text[e["start"]:e["end"]])
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                decoys, _ = declared_decoy_spans(rec)
                if unplanned_pii(rec):
                    reasons.setdefault(rid, set()).add("unplanned_pii")
                if find_unlabelled_dates(text, rec.get("entities") or [], decoys):
                    reasons.setdefault(rid, set()).add("unlabelled_standalone_date")
                if turkish_contamination(text):
                    reasons.setdefault(rid, set()).add("turkish")

        ids_out = tmp / "ids.json"
        gate = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_corpus.py"), str(filled),
             "--skip-dedup", "--ids-out", str(ids_out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        data = json.loads(ids_out.read_text(encoding="utf-8"))
        blocking = data["must_be_zero"]
        for check in blocking:
            for rid in data["ids"].get(check, []):
                reasons.setdefault(rid, set()).add(check)
        informational = {c: len(data["ids"].get(c, [])) for c in INFORMATIONAL}

        kept = tmp / "kept.jsonl"
        with filled.open(encoding="utf-8") as src, kept.open("w", encoding="utf-8", newline="") as dst:
            for line in src:
                if str(json.loads(line)["id"]) not in reasons:
                    dst.write(line)
        recheck = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_corpus.py"), str(kept)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=ROOT)
        kept_exit = recheck.returncode
        kept_tail = [l.strip() for l in recheck.stdout.strip().splitlines()[-3:]]

    out.parent.mkdir(parents=True, exist_ok=True)
    by_reason, by_split = Counter(), Counter()
    with out.open("w", encoding="utf-8", newline="") as fh:
        for rid in sorted(reasons):
            why = sorted(reasons[rid], key=reason_key)
            by_split[split_of[rid]] += 1
            by_reason.update(why)
            fh.write(json.dumps({"id": rid, "split": split_of[rid], "reason": why[0],
                                 "reasons": why}, ensure_ascii=False) + "\n")

    n = sum(totals.values())
    report = {"documents": dict(totals), "audited": n, "dropped": len(reasons),
              "dropped_share": round(len(reasons) / max(1, n), 4),
              "dropped_by_split": dict(by_split), "documents_by_reason": dict(by_reason),
              "informational_validate_corpus_documents": informational,
              "kept": n - len(reasons), "validate_corpus_exit": gate.returncode,
              "kept_set_validate_corpus_exit": kept_exit}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{n:,} az documents ({dict(totals)}): {len(reasons):,} on the drop list "
          f"({report['dropped_share']:.2%}) {dict(by_split)}")
    for reason, count in sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {count:>7,}  {reason}")
    print("informational (not dropped):", informational)
    print(f"kept {n - len(reasons):,}; validate_corpus on the kept set: exit {kept_exit} {kept_tail}")
    print(f"drop list -> {out}\nreport    -> {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
