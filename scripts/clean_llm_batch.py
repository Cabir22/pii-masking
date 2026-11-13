"""Clean one LLM generation batch: drop, never edit, every failing document.

    python scripts/clean_llm_batch.py data/raw/sprint1_llm_b1.jsonl
    # -> data/raw/sprint1_llm_b1.clean.jsonl
    #    data/raw/sprint1_llm_b1.clean.report.json

A document is dropped when it fails any of:
  1. a MUST-BE-ZERO check of scripts/validate_corpus.py (planned_value_
     unlabelled included), run on the batch with --ids-out;
  2. the leakage guard (eval/leakage_guard.py, contract C4) with
     --bench-docs data/benchmark_v3/... -- its JSON lists at most 20 hits
     per check, so the guard is re-run on what is left until it is clean;
  3. decoy integrity (piigen/audit_llm_batch.decoy_problems).

With --drop-unplanned-pii it also drops documents in which the model
INVENTED PII nobody planned, so nobody labelled (a gazetteer city,
`<Name> küçəsi`, `bina N`, a full name: piigen.llm.quality.find_invented_pii,
which generation now rejects too). The team decided to drop them (D-15c):
every LLM batch is cleaned with this flag. The report counts these
documents either way.

With --max-value-repeats N it also drops a document in which one value
(same label, same text) is labelled N times or more: a log or a schedule
that repeats one IPv6 address or one time 20-75 times teaches that value,
not the label (batch 6, `llm_az_000599`; the benchmark has no value
repeated even 5 times).

Labels are never touched: a kept line is written byte for byte as it came
in, and the raw batch file is only read. The fixes for what is dropped
belong in the generator, for the next batch (P2-6). At the end both gates
are run on the clean file and must pass; the script exits 1 if not.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.audit_llm_batch import decoy_problems, sweep_unplanned, unplanned_pii  # noqa: E402

BENCH_DOCS = ROOT / "data" / "benchmark_v3" / "pii_az_benchmark_v3_structured_9780.jsonl"
LEAK_FAILURES = ("values", "sentences", "shadow_ngrams", "shadow_values")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *map(str, cmd)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", cwd=ROOT)


def gate_failures(path: Path, tmp: Path) -> dict[str, set]:
    """{record id: {failed MUST-BE-ZERO checks}} from validate_corpus."""
    ids_out = tmp / "validate_ids.json"
    run([ROOT / "scripts" / "validate_corpus.py", path, "--skip-dedup", "--ids-out", ids_out])
    data = json.loads(ids_out.read_text(encoding="utf-8"))
    out: dict[str, set] = {}
    for check in data["must_be_zero"]:
        for rid in data["ids"].get(check, []):
            out.setdefault(rid, set()).add(f"validate_corpus:{check}")
    return out


def leak_failures(path: Path, tmp: Path, bench: list[Path]) -> tuple[bool, dict[str, set]]:
    report = tmp / "leak.json"
    cmd = [ROOT / "eval" / "leakage_guard.py", path, "--json", report]
    for b in bench:
        cmd += ["--bench-docs", b]
    proc = run(cmd)
    if not report.exists():   # the guard crashed (seen once when memory was short)
        raise RuntimeError(f"leakage guard wrote no report (exit {proc.returncode}):\n{proc.stderr[-2000:]}")
    data = json.loads(report.read_text(encoding="utf-8"))
    out: dict[str, set] = {}
    for check in LEAK_FAILURES:
        for hit in data["hits"].get(check, []):
            out.setdefault(str(hit.get("doc")), set()).add(f"leakage_guard:{check}")
    return bool(data.get("clean")), out


def most_repeated(rec: dict) -> int:
    """How many times the document's most repeated value is labelled."""
    text = rec["text"]
    c = Counter((e["label"], text[e["start"]:e["end"]]) for e in rec.get("entities") or [])
    return max(c.values(), default=0)


def write(lines: list[str], ids: list[str], keep: set, path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        for line, rid in zip(lines, ids):
            if rid in keep:
                fh.write(line if line.endswith("\n") else line + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="default: <batch>.clean.jsonl")
    ap.add_argument("--report", type=Path, default=None,
                    help="default: <batch>.clean.report.json")
    ap.add_argument("--bench-docs", type=Path, action="append", default=None,
                    help=f"default: {BENCH_DOCS.relative_to(ROOT)}")
    ap.add_argument("--drop-unplanned-pii", action="store_true",
                    help="also drop documents with PII the model invented (a decision "
                         "for the team; see the module docstring)")
    ap.add_argument("--max-value-repeats", type=int, default=None, metavar="N",
                    help="also drop documents that label one value N times or more")
    args = ap.parse_args()

    batch = args.batch.resolve()
    out = (args.out or batch.with_suffix(".clean.jsonl")).resolve()
    report_path = (args.report or batch.with_suffix(".clean.report.json")).resolve()
    if out == batch:
        print("refusing to overwrite the raw batch")
        return 2
    bench = args.bench_docs or [BENCH_DOCS]

    lines = [l for l in batch.open(encoding="utf-8", newline="") if l.strip()]
    records = [json.loads(l) for l in lines]
    ids = [str(r.get("id")) for r in records]
    reasons: dict[str, set] = {}

    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for rid, why in gate_failures(batch, tmp).items():
            reasons.setdefault(rid, set()).update(why)
        for rec, rid in zip(records, ids):
            for f in decoy_problems(rec):
                if f["problem"]:
                    reasons.setdefault(rid, set()).add(f"decoy_integrity:{f['problem']}")

        if args.drop_unplanned_pii:
            for rec, rid in zip(records, ids):
                if rid not in reasons and unplanned_pii(rec):
                    reasons.setdefault(rid, set()).add("unplanned_pii")
        if args.max_value_repeats:
            for rec, rid in zip(records, ids):
                if most_repeated(rec) >= args.max_value_repeats:
                    reasons.setdefault(rid, set()).add(f"value_repeated_{args.max_value_repeats}x_or_more")
        keep ={rid for rid in ids if rid not in reasons}
        candidate = tmp / "candidate.jsonl"
        for _round in range(20):
            write(lines, ids, keep, candidate)
            clean, hits = leak_failures(candidate, tmp, bench)
            if clean:
                break
            if not hits:
                print("leakage guard failed but listed no document; stopping")
                return 1
            for rid, why in hits.items():
                reasons.setdefault(rid, set()).update(why)
                keep.discard(rid)
        write(lines, ids, keep, out)

    # both gates on the result
    gate = run([ROOT / "scripts" / "validate_corpus.py", out, "--skip-dedup"])
    leak_cmd = [ROOT / "eval" / "leakage_guard.py", out]
    for b in bench:
        leak_cmd += ["--bench-docs", b]
    leak = run(leak_cmd)

    by_reason = Counter(r for why in reasons.values() for r in why)
    report = {
        "batch": str(batch.relative_to(ROOT) if batch.is_relative_to(ROOT) else batch),
        "batch_sha256": sha256(batch),
        "clean": str(out.relative_to(ROOT) if out.is_relative_to(ROOT) else out),
        "clean_sha256": sha256(out),
        "records": len(records), "kept": len(keep), "dropped": len(records) - len(keep),
        "dropped_by_reason": dict(by_reason.most_common()),
        "dropped_documents": [{"id": rid, "reasons": sorted(reasons[rid])}
                              for rid in ids if rid in reasons],
        "unplanned_pii_in_kept": sweep_unplanned(
            [r for r, rid in zip(records, ids) if rid in keep], examples=3),
        "dropped_unplanned_pii": bool(args.drop_unplanned_pii),
        "max_value_repeats": args.max_value_repeats,
        "validate_corpus_exit": gate.returncode,
        "leakage_guard_exit": leak.returncode,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"{len(records):,} records -> {len(keep):,} kept, {len(records) - len(keep):,} dropped")
    for reason, n in by_reason.most_common():
        print(f"   {n:>5}  {reason}")
    print(f"validate_corpus on the clean file: exit {gate.returncode}"
          f" ({gate.stdout.strip().splitlines()[-2].strip() if gate.stdout.strip() else ''})")
    print(f"leakage guard on the clean file  : exit {leak.returncode}")
    up = report["unplanned_pii_in_kept"]
    print(f"kept documents with PII the model invented (not dropped unless "
          f"--drop-unplanned-pii): {up['documents']} ({up['share']:.1%}) {up['by_label']}")
    print(f"clean  -> {out}\nreport -> {report_path}")
    return 0 if gate.returncode == 0 and leak.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
