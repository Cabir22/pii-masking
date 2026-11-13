"""Exhaustive corpus validation. Every record, every check, no sampling.

This is the gate that decides whether a corpus is fit to train on. It runs the
full per-record rule table from the 100k audit, plus the corpus-level checks
(duplicates, distribution drift) that only make sense over the whole set.

Exit code is 0 only when every MUST-BE-ZERO check is zero.

Run:  python scripts/validate_corpus.py data/repaired/repaired.jsonl
      python scripts/validate_corpus.py data/repaired/repaired.jsonl --json reports/validation.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.anchors import ANCHOR_REQUIRED, has_anchor, structural_kind  # noqa: E402
from piigen.config import (ENTITY_SET, ENTITY_TYPES,        # noqa: E402
                           GeneratorConfig, REMOVED_LABELS)
from piigen.llm.quality import (GlobalSimilarityIndex,       # noqa: E402
                                normalize_for_similarity)
from piigen.llm.specs import LENGTH_BANDS                    # noqa: E402
from piigen.llm.quality import find_leaked_pii               # noqa: E402
from piigen.resolver import (find_unlabeled_repeats,                  # noqa: E402
                             find_unlabelled_planned, resolve_claims)
from piigen.validate import declared_decoy_spans, validate_example  # noqa: E402
from piigen.standalone_dates import find_unlabelled_dates  # noqa: E402

BAND_BOUNDS = {n: (lo, hi) for n, _w, lo, hi, _h in LENGTH_BANDS}
ZERO_WIDTH = re.compile(r"[​‌‍﻿]")
CYRILLIC = re.compile(r"[Ѐ-ӿ]")

# Checks whose only acceptable value is zero. Anything here that is non-zero
# fails the run, because each one means the corpus contains a record that
# would teach the model something false.
MUST_BE_ZERO = [
    "malformed_json", "duplicate_id", "span_text_mismatch", "span_out_of_range",
    "empty_span", "overlapping_spans", "duplicate_span", "unknown_label",
    "removed_label", "zero_width_in_span", "not_nfc", "no_entities",
    "exact_duplicate_text", "structural_number_span", "missing_anchor",
    "repeat_mention_incomplete", "validator_failure",
    # 2026-08-27 audit, both added because their absence let real defects sit
    # in a corpus that every existing check called clean:
    #
    #   unlabeled_pii_leak -- an INDEPENDENT full-text sweep, not anchored to
    #     the planned-value list. find_unlabeled_repeats can only re-find
    #     values that are already labeled somewhere, so a value the model
    #     invented and used once was invisible to every gate. The audit found
    #     348 such records, including a valid AZ_ID_CARD_NUMBER in the golden
    #     reference corpus.
    #
    #   resolver_drift -- re-resolving each record with TODAY's resolver must
    #     reproduce the spans it already carries. Without this, resolver fixes
    #     are forward-only: records generated before a fix keep their old
    #     annotations forever. 26 of 30 lost annotations in the live corpus
    #     were exactly this, all from before the 2026-08-25/26 fixes.
    "unlabeled_pii_leak", "resolver_drift",
    # P2-6 (LLM batch 1, 2026-10-03): a value the brief planned (`_spec.
    # entities`) that is in the text in any form -- verbatim, inflected
    # (`küçəsində` for `küç.`), softened (`İsağın`), in capitals or without
    # Azerbaijani letters, misspelt -- but not labelled there. 349 such
    # occurrences in 245 of batch 1's 6,000 documents passed every check
    # above: none of them knows what was planned.
    "planned_value_unlabelled",
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--similarity-threshold", type=float, default=0.82)
    ap.add_argument("--skip-dedup", action="store_true",
                    help="skip the global near-duplicate sweep (the slow part)")
    ap.add_argument("--ids-out", type=Path, default=None,
                    help="write every failing record id, per check, as JSON "
                         "(scripts/clean_llm_batch.py drops exactly these)")
    args = ap.parse_args()

    if not args.corpus.exists():
        print(f"not found: {args.corpus}")
        return 2

    counts: Counter = Counter()
    samples: dict[str, list] = defaultdict(list)
    failing: dict[str, set] = defaultdict(set)
    ids: set = set()
    texts: set = set()
    label_counts: Counter = Counter()
    label_values: dict[str, set] = defaultdict(set)
    doc_types: Counter = Counter()
    bands: Counter = Counter()
    langs: Counter = Counter()
    lengths: list[int] = []
    mentions_total = 0
    n = 0

    def note(key: str, rid: str, detail: str = "") -> None:
        counts[key] += 1
        failing[key].add(rid)
        if len(samples[key]) < 5:
            samples[key].append(f"{rid} {detail}".strip())

    index = None if args.skip_dedup else GlobalSimilarityIndex(
        threshold=args.similarity_threshold)
    near_dupe_pairs: list = []

    for lineno, line in enumerate(args.corpus.open(encoding="utf-8"), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            note("malformed_json", f"line {lineno}", str(exc)[:60])
            continue
        n += 1
        rid = rec.get("id", f"line {lineno}")
        text = rec.get("text", "")
        entities = rec.get("entities") or []

        if rid in ids:
            note("duplicate_id", rid)
        ids.add(rid)

        if text in texts:
            note("exact_duplicate_text", rid)
        texts.add(text)

        if unicodedata.normalize("NFC", text) != text:
            note("not_nfc", rid)
        # An empty entity list is a harness failure unless the record DECLARES
        # itself PII-free: D-1 brings deliberate PII-free documents back
        # (`--negative-only-rate`, the targeted builder's ~10%). An undeclared
        # empty record still fails.
        if not entities and not (rec.get("_pii_free") is True or
                                 (rec.get("_spec") or {}).get("negative_only") is True):
            note("no_entities", rid)

        lengths.append(len(text))
        langs[rec.get("lang")] += 1
        doc_types[rec.get("_doc_type")] += 1
        bands[rec.get("_bucket")] += 1

        band = rec.get("_bucket")
        if band in BAND_BOUNDS:
            lo, hi = BAND_BOUNDS[band]
            if not (lo <= len(text) <= hi):
                note("band_metadata_mismatch", rid, f"{band} len={len(text)}")

        spans = []
        for e in entities:
            label = e.get("label")
            s, en, t = e.get("start"), e.get("end"), e.get("text")
            mentions_total += 1
            label_counts[label] += 1
            label_values[label].add(t)

            if label in REMOVED_LABELS:
                note("removed_label", rid, str(label))
            elif label not in ENTITY_SET:
                note("unknown_label", rid, str(label))
            if not isinstance(s, int) or not isinstance(en, int):
                note("span_out_of_range", rid, "non-integer offsets")
                continue
            if s < 0 or en > len(text) or s >= en:
                note("span_out_of_range", rid, f"({s},{en})")
                continue
            if en == s:
                note("empty_span", rid)
            if text[s:en] != t:
                note("span_text_mismatch", rid, f"{t!r} != {text[s:en]!r}")
            if ZERO_WIDTH.search(t or ""):
                note("zero_width_in_span", rid, repr(t))
            if structural_kind(text, s, en):
                note("structural_number_span", rid, repr(t))
            if label in ANCHOR_REQUIRED and not has_anchor(label, text, s, en):
                note("missing_anchor", rid, f"{label} {t!r}")
            spans.append((s, en, label))

        spans.sort()
        for (s1, e1, _l1), (s2, e2, _l2) in zip(spans, spans[1:]):
            if s2 < e1:
                note("overlapping_spans", rid, f"({s1},{e1})/({s2},{e2})")
            if (s1, e1) == (s2, e2):
                note("duplicate_span", rid, f"({s1},{e1})")

        # Declared decoys (C2 `_decoys`, P2-3) are deliberately unlabeled; each
        # check below exempts exactly those spans. A malformed `_decoys` field
        # is reported by validate_example further down.
        decoys, _ = declared_decoy_spans(rec)

        if find_unlabeled_repeats(text, entities, exempt=decoys):
            note("repeat_mention_incomplete", rid)

        # Independent full-text PII sweep. Deliberately NOT anchored to the
        # planned-value list -- that is the whole point (see MUST_BE_ZERO).
        for leak in find_leaked_pii(text, entities, decoy_spans=decoys)[:3]:
            note("unlabeled_pii_leak", rid, leak[:70])

        # The complement: every value the record's brief planned must be
        # labelled wherever it occurs, in whatever form (see MUST_BE_ZERO).
        # Records without a plan (`_spec.entities`) are not affected.
        planned = [(e.get("label"), e.get("value"))
                   for e in (rec.get("_spec") or {}).get("entities") or []
                   if isinstance(e, dict) and e.get("label") and e.get("value")]
        if planned:
            for miss in find_unlabelled_planned(text, entities, planned, decoys)[:3]:
                note("planned_value_unlabelled", rid,
                     f"{miss['label']} {miss['value']!r} as {miss['text']!r} ({miss['kind']})"[:90])

        # Does this record still reproduce under TODAY's resolver? Re-resolve
        # its own (label, value) pairs against its own text and compare the
        # resulting span set. A mismatch means the record was annotated by an
        # older resolver and has been carrying stale spans ever since.
        if entities:
            reclaimed, _ = resolve_claims(
                text, [{"label": e["label"], "text": e["text"]}
                       for e in entities], blocked=decoys)
            now = {(e["start"], e["end"], e["label"]) for e in reclaimed}
            was = {(e["start"], e["end"], e["label"]) for e in entities}
            if now != was:
                note("resolver_drift", rid,
                     f"+{len(now - was)} -{len(was - now)} span(s)")
        # One call, not two. `validate_example` re-scans the whole document
        # (language, checksums, blocklist, repeat mentions), so calling it
        # once for the boolean and again for the message doubled the runtime
        # of the slowest check in this script.
        problems = validate_example(rec)
        if problems:
            note("validator_failure", rid, problems[0][:80])
        if CYRILLIC.search(text):
            note("cyrillic_present", rid)
        # D-17: a standalone date (not a timestamp) must be labelled DATE.
        # Informational for now: the old corpus and older batches need
        # scripts/relabel_standalone_dates.py first (P2, 2026-10-04).
        for d in find_unlabelled_dates(text, entities, decoys)[:1]:
            note("unlabelled_standalone_date", rid, repr(d["text"]))

        if index is not None:
            normalized = normalize_for_similarity(text, entities)
            is_dupe, score, match = index.check(normalized)
            if is_dupe:
                counts["near_duplicate"] += 1
                if len(near_dupe_pairs) < 20:
                    near_dupe_pairs.append((rid, match, round(score, 3)))
            index.add(normalized, doc_id=rid)

    lengths.sort()

    def pct(p: float) -> int:
        return lengths[min(len(lengths) - 1, int(len(lengths) * p))] if lengths else 0

    cfg = GeneratorConfig()
    drift = {}
    for label in ENTITY_TYPES:
        target = cfg.entity_weights.get(label, 0.0)
        if not target:
            continue
        actual = label_counts[label] / mentions_total if mentions_total else 0.0
        drift[label] = round(actual / target, 3)

    failures = {k: counts[k] for k in MUST_BE_ZERO if counts[k]}
    ok = not failures

    print("=" * 74)
    print(f"CORPUS VALIDATION -- {args.corpus.name}")
    print("=" * 74)
    print(f"records            : {n:,}")
    print(f"entity mentions    : {mentions_total:,}")
    print(f"distinct ids       : {len(ids):,}")
    print(f"labels present     : {len([l for l in ENTITY_TYPES if label_counts[l]])}/27")
    print(f"length             : min {lengths[0]:,}  p50 {pct(.5):,}  "
          f"p95 {pct(.95):,}  max {lengths[-1]:,}" if lengths else "")
    print(f"doc types          : {len([d for d in doc_types if d])}")
    print(f"sha256             : {hashlib.sha256(args.corpus.read_bytes()).hexdigest()[:32]}...")
    print()
    print("MUST-BE-ZERO CHECKS")
    for key in MUST_BE_ZERO:
        value = counts[key]
        mark = "FAIL" if value else "ok"
        print(f"  {key:<30}{value:>9,}   {mark}")
        for sample in samples[key][:3]:
            print(f"      e.g. {sample[:100]}")
    print()
    print("INFORMATIONAL")
    for key in ("band_metadata_mismatch", "cyrillic_present", "near_duplicate",
                "unlabelled_standalone_date"):
        print(f"  {key:<30}{counts[key]:>9,}")
    for pair in near_dupe_pairs[:5]:
        print(f"      {pair[0]} ~ {pair[1]} (jaccard {pair[2]})")
    print()
    print("LABEL DISTRIBUTION (actual / target)")
    worst = sorted(drift.items(), key=lambda kv: abs(kv[1] - 1.0), reverse=True)
    for label, ratio in worst[:8]:
        uniq = len(label_values[label])
        print(f"  {label:<26}{label_counts[label]:>8,} mentions  "
              f"{uniq:>7,} distinct  ratio {ratio:.2f}")
    print()
    print("=" * 74)
    print("RESULT:", "PASS -- corpus is fit to train on" if ok
          else f"FAIL -- {len(failures)} blocking check(s): {', '.join(failures)}")
    print("=" * 74)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({
            "corpus": str(args.corpus),
            "sha256": hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
            "records": n,
            "mentions": mentions_total,
            "pass": ok,
            "failures": failures,
            "counts": dict(counts),
            "samples": {k: v for k, v in samples.items()},
            "label_counts": dict(label_counts),
            "label_distinct": {k: len(v) for k, v in label_values.items()},
            "label_drift": drift,
            "doc_types": dict(doc_types),
            "bands": dict(bands),
            "langs": dict(langs),
            "length_percentiles": {
                "min": lengths[0] if lengths else 0, "p50": pct(.5),
                "p95": pct(.95), "max": lengths[-1] if lengths else 0},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"json -> {args.json}")

    if args.ids_out:
        args.ids_out.parent.mkdir(parents=True, exist_ok=True)
        args.ids_out.write_text(json.dumps(
            {"must_be_zero": MUST_BE_ZERO,
             "ids": {k: sorted(map(str, v)) for k, v in failing.items()}},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"ids  -> {args.ids_out}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
