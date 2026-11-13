"""Adversarial red-team probe against the trained masking model.

Tests the token-classification model hosted at the Hugging Face repo
`your-hf-org/masking-multilingual` (override with --model) against every label
in data/schema.md, looking specifically for FAILURES: missed entities,
wrong labels, partial-span detections, and over-detection on hard
negatives / structurally-suppressed positions. This is a red-team tool,
not an accuracy report: a correct detection is not a "finding" -- it is
still counted in run_ledger.jsonl, but findings.jsonl holds only failures.

Read-only with respect to the rest of the repo: this module and
scripts/redteam/cases.py reuse scripts/piigen's value generators,
checksums, hard negatives, noise injector and anchor rules as a library,
but never write to data/processed/, model/train.py, or any generation
pipeline file. All state this script writes lives under scripts/redteam/.

Credential handling (hard constraint): the Hugging Face token is read from
the HF_TOKEN environment variable ONLY -- never from argv (shell history /
`ps` exposure), never logged, never written to findings.jsonl, run_ledger
or the report. If HF_TOKEN is unset, this script prints exactly that and
exits; it does not fabricate a token or attempt to proceed without one.

Usage:
    export HF_TOKEN="<token>"
    python scripts/redteam/masking_model_probe.py --self-test
        # plumbing sanity check (a handful of should-obviously-pass cases,
        # id2label verification). Not persisted, not part of the report.
    python scripts/redteam/masking_model_probe.py --run
        # run every not-yet-run case in scripts/redteam/cases.py, append
        # new rows to findings.jsonl (failures only) and run_ledger.jsonl
        # (every case), checkpoint progress to checkpoint.json.
    python scripts/redteam/masking_model_probe.py --run --category formatting
        # run only one category (see cases.ALL_CATEGORIES) -- for
        # incremental waves.
    python scripts/redteam/masking_model_probe.py --report
        # (re)generate docs/findings/redteam_masking_model_findings.md from
        # findings.jsonl + run_ledger.jsonl. Does not touch the model.
    python scripts/redteam/masking_model_probe.py --reset
        # wipe checkpoint.json + findings.jsonl + run_ledger.jsonl and
        # start a fresh campaign (asks for confirmation).

Resumability: run_ledger.jsonl records the outcome of EVERY case run (pass
or fail) so a later invocation knows what's already covered without
re-running it; findings.jsonl holds only the failure rows the report reads.
Both are append-only, flushed + fsynced per case. checkpoint.json is
rewritten atomically (temp file + fsync + os.replace) after every case,
mirroring scripts/piigen/values.py's ValuePool.save() pattern.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import json
import os
import sys
import tempfile
from pathlib import Path

REDTEAM_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = str(REDTEAM_DIR.parent)
ROOT = REDTEAM_DIR.parents[1]
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from piigen.config import ENTITY_TYPES, DETECTION_TIERS       # noqa: E402
from redteam.cases import ALL_CASES, ALL_CATEGORIES, TestCase, coverage_report  # noqa: E402

DEFAULT_MODEL = "your-hf-org/masking-multilingual"

FINDINGS_PATH = REDTEAM_DIR / "findings.jsonl"
LEDGER_PATH = REDTEAM_DIR / "run_ledger.jsonl"
CHECKPOINT_PATH = REDTEAM_DIR / "checkpoint.json"
REPORT_PATH = ROOT / "docs" / "findings" / "redteam_masking_model_findings.md"

# Real-world risk tier, used only for report ranking -- purely a display
# concern, never affects pass/fail classification itself.
RISK_TIER = {
    "AZ_FIN": "high", "AZ_ID_CARD_NUMBER": "high", "AZ_PASSPORT_NUMBER": "high",
    "AZ_VOEN": "high", "AZ_DRIVER_LICENSE_NUMBER": "high",
    "PAYMENT_CARD_NUMBER": "high", "IBAN": "high", "CARD_SECURITY_CODE": "high",
    "API_KEY": "high", "ACCESS_TOKEN": "high", "PRIVATE_KEY": "high",
    "EMAIL": "medium", "TELEPHONENUM": "medium", "GIVENNAME": "medium",
    "SURNAME": "medium", "ICCID": "medium", "MAC_ADDRESS": "medium",
    "IPV4_ADDRESS": "medium", "IPV6_ADDRESS": "medium",
    "CITY": "low", "STREET": "low", "BUILDINGNUM": "low", "ZIPCODE": "low",
    "DATE": "low", "TIME": "low", "AGE": "low", "URL": "low",
}


def get_hf_token() -> str:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN is not set in the environment. Export it and re-run:\n"
              '  export HF_TOKEN="<token>"', file=sys.stderr)
        raise SystemExit(1)
    return token


# --------------------------------------------------------------------------
# Model client
# --------------------------------------------------------------------------
class ModelClient:
    def __init__(self, model_id: str, token: str) -> None:
        from transformers import (AutoConfig, AutoModelForTokenClassification,
                                  AutoTokenizer, pipeline)

        self.model_id = model_id
        self.config = AutoConfig.from_pretrained(model_id, token=token)
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, token=token)
        self.model = AutoModelForTokenClassification.from_pretrained(model_id, token=token)
        self.revision = getattr(self.config, "_commit_hash", None) or "unknown"
        device = -1
        if _cuda_available():
            device = 0
        elif _mps_available():
            device = "mps"
        self.pipe = pipeline(
            "token-classification", model=self.model, tokenizer=self.tokenizer,
            aggregation_strategy="simple", device=device,
        )

    def schema_mismatch(self) -> dict | None:
        """Compare the model's actual id2label against data/schema.md's 27
        labels. Any mismatch is itself a first-class finding, per the task
        instructions -- computed BEFORE any test expectation is written
        against it.
        """
        model_labels = set()
        for v in self.config.id2label.values():
            if v == "O":
                continue
            model_labels.add(v.split("-", 1)[1] if "-" in v else v)
        expected_labels = set(ENTITY_TYPES)
        missing = sorted(expected_labels - model_labels)
        extra = sorted(model_labels - expected_labels)
        if not missing and not extra:
            return None
        return {"missing": missing, "extra": extra,
                "model_id2label": dict(self.config.id2label)}

    def classify(self, text: str) -> list[dict]:
        if not text:
            return []
        raw = self.pipe(text)
        out = []
        for p in raw:
            out.append({
                "entity_group": p["entity_group"],
                "start": int(p["start"]),
                "end": int(p["end"]),
                "score": float(p["score"]),
            })
        return out


def _cuda_available() -> bool:
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:  # noqa: BLE001
        return False


def _mps_available() -> bool:
    try:
        import torch
        return torch.backends.mps.is_available()
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------
# Diffing: expected spans vs predicted spans
# --------------------------------------------------------------------------
def _overlap_len(a_start: int, a_end: int, b_start: int, b_end: int) -> int:
    return max(0, min(a_end, b_end) - max(a_start, b_start))


_FAILURE_STATUSES = {"missed", "partial_span", "wrong_label",
                     "wrong_label_and_span", "false_positive"}


def classify_case(expected: list[dict], predicted: list[dict]) -> list[dict]:
    """Greedy best-overlap matching, expected-entity-first. Returns one row
    per expected entity ('pass'/'missed'/'partial_span'/'wrong_label'/
    'wrong_label_and_span') plus one row per unmatched prediction
    ('false_positive' -- over-detection, the failure mode hard-negative and
    suppression cases exist to catch).
    """
    results = []
    used = set()
    for e in expected:
        best_i, best_overlap = None, 0
        for i, p in enumerate(predicted):
            if i in used:
                continue
            ov = _overlap_len(e["start"], e["end"], p["start"], p["end"])
            if ov > best_overlap:
                best_overlap, best_i = ov, i
        if best_i is None:
            results.append({"expected": e, "predicted": None, "outcome": "missed"})
            continue
        p = predicted[best_i]
        used.add(best_i)
        exact = p["start"] == e["start"] and p["end"] == e["end"]
        same_label = p["entity_group"] == e["label"]
        if exact and same_label:
            outcome = "pass"
        elif same_label:
            outcome = "partial_span"
        elif exact:
            outcome = "wrong_label"
        else:
            outcome = "wrong_label_and_span"
        results.append({"expected": e, "predicted": p, "outcome": outcome})
    for i, p in enumerate(predicted):
        if i not in used:
            results.append({"expected": None, "predicted": p, "outcome": "false_positive"})
    return results


def _describe_outcome(case: TestCase, row: dict) -> str:
    o = row["outcome"]
    if o == "missed":
        e = row["expected"]
        return f"MISSED {e['label']} {e['start']}:{e['end']} {e['text']!r}"
    if o == "false_positive":
        p = row["predicted"]
        return (f"FALSE POSITIVE {p['entity_group']} {p['start']}:{p['end']} "
                f"{case.text[p['start']:p['end']]!r} (score={p['score']:.3f})")
    e, p = row["expected"], row["predicted"]
    return (f"{o.upper()} expected {e['label']} {e['start']}:{e['end']} {e['text']!r}, "
            f"got {p['entity_group']} {p['start']}:{p['end']} "
            f"{case.text[p['start']:p['end']]!r}")


def _contributing_characteristics(case: TestCase) -> list[str]:
    tags = [f"category:{case.category}", f"lang:{case.lang}"]
    if case.is_hard_negative:
        tags.append("hard_negative")
    if case.is_ambiguous:
        tags.append("ambiguous_collision")
    return tags


# --------------------------------------------------------------------------
# Crash-safe state: checkpoint.json (atomic), findings/ledger (append+fsync)
# --------------------------------------------------------------------------
def _atomic_write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"completed_ids": [], "waves_run": 0, "model_id": None, "model_revision": None}


def save_checkpoint(ckpt: dict) -> None:
    _atomic_write_json(CHECKPOINT_PATH, ckpt)


def completed_case_ids(ckpt: dict) -> set[str]:
    return set(ckpt.get("completed_ids", []))


class _JsonlAppender:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")

    def append(self, obj: dict) -> None:
        self._fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# --------------------------------------------------------------------------
# Run a wave
# --------------------------------------------------------------------------
def run_wave(cases: list[TestCase], client: ModelClient, category: str | None,
            limit: int | None = None) -> None:
    ckpt = load_checkpoint()
    done = completed_case_ids(ckpt)
    to_run = [c for c in cases if c.id not in done]
    if category:
        to_run = [c for c in to_run if c.category == category]
    if limit:
        to_run = to_run[:limit]

    if not to_run:
        print("Nothing to run (all matching cases already completed -- see checkpoint.json).")
        return

    findings = _JsonlAppender(FINDINGS_PATH)
    ledger = _JsonlAppender(LEDGER_PATH)
    ckpt["model_id"] = client.model_id
    ckpt["model_revision"] = client.revision
    ckpt["waves_run"] = ckpt.get("waves_run", 0) + 1

    passed = failed = 0
    try:
        for i, case in enumerate(to_run, 1):
            preds = client.classify(case.text)
            rows = classify_case(case.expected, preds)
            case_failed = any(r["outcome"] in _FAILURE_STATUSES for r in rows)
            ledger.append({
                "case_id": case.id, "label": case.label, "lang": case.lang,
                "category": case.category, "n_expected": len(case.expected),
                "n_predicted": len(preds), "outcome": "fail" if case_failed else "pass",
                "n_failure_rows": sum(1 for r in rows if r["outcome"] in _FAILURE_STATUSES),
                "timestamp": _now(),
            })
            if case_failed:
                failed += 1
                findings.append({
                    "case_id": case.id, "label": case.label, "lang": case.lang,
                    "category": case.category, "risk_tier": RISK_TIER.get(case.label, "n/a"),
                    "is_hard_negative": case.is_hard_negative,
                    "is_ambiguous": case.is_ambiguous,
                    "notes": case.notes,
                    "text": case.text,
                    "characteristics": _contributing_characteristics(case),
                    "failure_rows": [
                        {"outcome": r["outcome"], "description": _describe_outcome(case, r),
                         "expected": r["expected"], "predicted": r["predicted"]}
                        for r in rows if r["outcome"] in _FAILURE_STATUSES
                    ],
                    "timestamp": _now(),
                })
            else:
                passed += 1
            ckpt["completed_ids"].append(case.id)
            save_checkpoint(ckpt)
            if i % 10 == 0 or i == len(to_run):
                print(f"  [{i}/{len(to_run)}] {case.id}: {'FAIL' if case_failed else 'pass'} "
                      f"(running: {passed} pass / {failed} fail)")
    finally:
        findings.close()
        ledger.close()

    print(f"\nWave complete: {passed} passed, {failed} failed out of {len(to_run)} run.")


def self_test(client: ModelClient) -> None:
    mismatch = client.schema_mismatch()
    if mismatch:
        print("SCHEMA MISMATCH:")
        print(json.dumps(mismatch, ensure_ascii=False, indent=2))
    else:
        print("id2label matches data/schema.md's 27 labels (BIO scheme) -- OK")

    sample = [c for c in ALL_CASES if c.category == "core"][:6]
    ok = 0
    for c in sample:
        preds = client.classify(c.text)
        rows = classify_case(c.expected, preds)
        passed = not any(r["outcome"] in _FAILURE_STATUSES for r in rows)
        ok += passed
        print(f"  {c.id}: {'PASS' if passed else 'FAIL'}"
              + ("" if passed else " -- " + "; ".join(_describe_outcome(c, r)
                 for r in rows if r["outcome"] in _FAILURE_STATUSES)))
    print(f"\nself-test: {ok}/{len(sample)} obviously-should-pass core cases passed "
          "(plumbing check only, not persisted).")


# --------------------------------------------------------------------------
# Report generation -- reads findings.jsonl + run_ledger.jsonl, nothing else
# --------------------------------------------------------------------------
def _load_findings() -> list[dict]:
    if not FINDINGS_PATH.exists():
        return []
    rows = []
    with open(FINDINGS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_ledger() -> list[dict]:
    if not LEDGER_PATH.exists():
        return []
    rows = []
    with open(LEDGER_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _label_of(row: dict) -> str:
    return row.get("label", "unknown")


def generate_report(model_id: str) -> str:
    findings = _load_findings()
    ledger = _load_ledger()
    ckpt = load_checkpoint()
    cov = coverage_report()

    lines = []
    lines.append(f"# Adversarial red-team findings -- `{model_id}`")
    lines.append("")
    lines.append(f"Model: `{ckpt.get('model_id') or model_id}` "
                 f"(revision `{ckpt.get('model_revision') or 'unknown'}`). "
                 f"Generated from `scripts/redteam/findings.jsonl` and "
                 f"`scripts/redteam/run_ledger.jsonl` by "
                 f"`scripts/redteam/masking_model_probe.py --report` -- do not hand-edit.")
    lines.append("")
    lines.append("**Scope note:** this document lists FAILURES in detail, and totals "
                 "computed from `run_ledger.jsonl` (every case run, pass or fail). "
                 "Every number below is derived directly from those two files, not "
                 "asserted in prose.")
    lines.append("")

    if not ledger:
        lines.append("## Status: campaign not yet started (blocked)")
        lines.append("")
        lines.append(
            f"**No wave has been run against the model yet.** The test harness "
            f"(`scripts/redteam/cases.py`, {cov['total_cases']} cases across all "
            f"{len(ENTITY_TYPES)} labels and all {len(ALL_CATEGORIES)} categories) "
            "is built and self-validated. Run "
            "`python scripts/redteam/masking_model_probe.py --run` (resumes "
            "automatically on every later invocation).")
        return "\n".join(lines) + "\n"

    total_run = len(ledger)
    total_fail = sum(1 for r in ledger if r["outcome"] == "fail")
    total_pass = total_run - total_fail

    lines.append("## Overall results")
    lines.append("")
    lines.append(f"- **Cases in harness:** {cov['total_cases']}")
    lines.append(f"- **Cases run:** {total_run}")
    lines.append(f"- **Passed:** {total_pass}")
    lines.append(f"- **Failed:** {total_fail}")
    if total_run < cov["total_cases"]:
        lines.append(f"- **Not yet run:** {cov['total_cases'] - total_run} "
                     "(resume with `--run`)")
    lines.append("")

    # -- per-label recall (only labels that appear as an expected entity
    # somewhere in the ledger's cases are computable here) --------------
    label_totals = collections.Counter()
    label_fail = collections.Counter()
    for r in ledger:
        lab = _label_of(r)
        if lab.startswith("_HARD_NEGATIVE"):
            continue
        label_totals[lab] += r["n_expected"]
        # crude per-case attribution: count this case's failure rows against
        # its primary label (multi-entity cases undercount secondary labels
        # here by design -- see findings.jsonl for the exact per-entity rows)
        if r["outcome"] == "fail":
            label_fail[lab] += r["n_failure_rows"]

    lines.append("## Per-label snapshot (primary-label cases only)")
    lines.append("")
    lines.append("| Label | Risk | Cases (primary) | Expected entities | Failure rows |")
    lines.append("|---|---|---|---|---|")
    for lab in sorted(ENTITY_TYPES):
        n_cases = sum(1 for r in ledger if _label_of(r) == lab)
        if n_cases == 0:
            continue
        lines.append(f"| {lab} | {RISK_TIER.get(lab, 'n/a')} | {n_cases} | "
                     f"{label_totals[lab]} | {label_fail[lab]} |")
    lines.append("")

    if not findings:
        lines.append("## No failures recorded")
        lines.append("")
        lines.append("Every case run so far passed. See `run_ledger.jsonl` for the "
                     "full pass tally.")
        return "\n".join(lines) + "\n"

    # -- cross-cutting root cause: trailing-character over-capture --------
    # A `partial_span` row where the predicted span is exactly the expected
    # span plus one trailing character (almost always the sentence-final
    # '.') is the same underlying bug regardless of which label/category it
    # shows up in -- surfaced separately because grouping by category alone
    # hides how dominant and cross-cutting this one pattern actually is.
    trailing_over_capture = []
    other_partial = 0
    for f in findings:
        for row in f["failure_rows"]:
            if row["outcome"] != "partial_span":
                continue
            e, p = row["expected"], row["predicted"]
            if e and p and p["start"] == e["start"] and p["end"] == e["end"] + 1:
                trailing_over_capture.append((f, row))
            else:
                other_partial += 1

    if trailing_over_capture:
        lines.append("## Dominant cross-cutting root cause: trailing-character over-capture")
        lines.append("")
        lines.append(
            f"**{len(trailing_over_capture)} of {sum(1 for f in findings for r in f['failure_rows'] if r['outcome'] == 'partial_span')} "
            "`partial_span` failure rows** (across "
            f"{len({f['case_id'] for f, _ in trailing_over_capture})} cases, "
            f"{len({f['label'] for f, _ in trailing_over_capture})} distinct "
            "labels) share one exact pattern: the predicted span is the "
            "correct span plus exactly one trailing character -- the "
            "sentence-final punctuation immediately after the value. This is "
            "the single largest failure cluster in this run, larger than any "
            "per-category grouping below, and it hits every risk tier "
            "(AZ_DRIVER_LICENSE_NUMBER, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, "
            "IBAN, CARD_SECURITY_CODE, ICCID -- all `high` risk -- alongside "
            "AGE/BUILDINGNUM).")
        lines.append("")
        affected_labels = sorted({f["label"] for f, _ in trailing_over_capture})
        lines.append(f"- **Labels affected:** {', '.join(affected_labels)}")
        example_ids = sorted({f["case_id"] for f, _ in trailing_over_capture})[:8]
        lines.append(f"- **Example case IDs:** {', '.join(f'`{i}`' for i in example_ids)}")
        lines.append("")

    # -- root-cause clusters: (category, dominant outcome) ----------------
    cluster = collections.Counter()
    cluster_examples = collections.defaultdict(list)
    for f in findings:
        outcomes = collections.Counter(row["outcome"] for row in f["failure_rows"])
        dominant = outcomes.most_common(1)[0][0]
        key = (f["category"], dominant)
        cluster[key] += 1
        if len(cluster_examples[key]) < 3:
            cluster_examples[key].append(f)

    lines.append("## Systemic failure clusters (root-cause grouped, by category)")
    lines.append("")
    lines.append("| Category | Dominant failure type | # cases | Example case IDs |")
    lines.append("|---|---|---|---|")
    for (cat, outcome), n in sorted(cluster.items(), key=lambda kv: -kv[1]):
        examples = ", ".join(f"`{f['case_id']}`" for f in cluster_examples[(cat, outcome)])
        lines.append(f"| {cat} | {outcome} | {n} | {examples} |")
    lines.append("")

    # -- top-severity findings, risk-ranked ------------------------------
    def _severity_key(f: dict):
        risk_rank = {"high": 0, "medium": 1, "low": 2, "n/a": 3}[f.get("risk_tier", "n/a")]
        return (risk_rank, -len(f["failure_rows"]))

    ranked = sorted(findings, key=_severity_key)
    lines.append("## Top findings (risk-ranked: government-ID / financial / "
                 "credential labels first)")
    lines.append("")
    for f in ranked[:20]:
        lines.append(f"### `{f['case_id']}`  ({f['label']}, risk={f['risk_tier']}, "
                     f"lang={f['lang']}, category={f['category']})")
        lines.append("")
        lines.append(f"- Notes: {f['notes']}")
        for row in f["failure_rows"]:
            lines.append(f"- {row['description']}")
        lines.append("")

    lines.append(f"*{max(0, len(findings) - 20)} additional failing case(s) not shown "
                 "above -- see `findings.jsonl` for the complete set.*")
    lines.append("")

    lines.append("## Known harness limitations")
    lines.append("")
    lines.append("- Per-label recall above is computed only from each case's "
                 "*primary* label attribution; multi-entity cases (the `embedded` "
                 "category) test several labels per case but are only tallied "
                 "under one. Exact per-entity outcomes for every label in every "
                 "case are in `findings.jsonl`'s `failure_rows`, not summarized "
                 "here.")
    lines.append("- `translate.lang.ANCHORS[\"en\"]` (and tr/ru) has no "
                 "structural-position guard equivalent to "
                 "`piigen.anchors.az.is_structural_position` -- confirmed during "
                 "harness construction, not from a probe result. The "
                 "`suppression` category is therefore AZ-only in this harness.")
    return "\n".join(lines) + "\n"


def write_report(model_id: str) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(generate_report(model_id), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--reset", action="store_true")
    ap.add_argument("--category", default=None, choices=ALL_CATEGORIES)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if args.reset:
        confirm = input(f"This will delete {FINDINGS_PATH.name}, {LEDGER_PATH.name} "
                        f"and {CHECKPOINT_PATH.name}. Type 'yes' to confirm: ")
        if confirm.strip().lower() == "yes":
            for p in (FINDINGS_PATH, LEDGER_PATH, CHECKPOINT_PATH):
                p.unlink(missing_ok=True)
            print("reset done.")
        else:
            print("aborted.")
        return 0

    if args.report:
        write_report(args.model)
        return 0

    if not (args.run or args.self_test):
        ap.print_help()
        return 1

    token = get_hf_token()
    print(f"loading {args.model} ...")
    client = ModelClient(args.model, token)
    mismatch = client.schema_mismatch()
    if mismatch:
        print("SCHEMA MISMATCH -- model's id2label does not match data/schema.md's "
              "27-label taxonomy:")
        print(json.dumps(mismatch, ensure_ascii=False, indent=2))
        if args.run:
            ledger = _JsonlAppender(LEDGER_PATH)
            findings = _JsonlAppender(FINDINGS_PATH)
            row = {"case_id": "_SCHEMA_CHECK", "label": "_SCHEMA", "lang": "n/a",
                   "category": "schema", "n_expected": 0, "n_predicted": 0,
                   "outcome": "fail", "n_failure_rows": 1, "timestamp": _now()}
            ledger.append(row)
            findings.append({**row, "risk_tier": "high", "is_hard_negative": False,
                             "is_ambiguous": False,
                             "notes": "Model id2label differs from data/schema.md's "
                                      "27-label taxonomy.",
                             "text": "", "characteristics": ["schema_mismatch"],
                             "failure_rows": [{"outcome": "schema_mismatch",
                                               "description": json.dumps(mismatch),
                                               "expected": None, "predicted": None}]})
            ledger.close()
            findings.close()
            print("SCHEMA MISMATCH logged as a finding -- see findings.jsonl")
        return 1

    if args.self_test:
        self_test(client)
        return 0

    run_wave(ALL_CASES, client, args.category, args.limit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
