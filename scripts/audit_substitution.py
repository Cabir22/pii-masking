# -*- coding: utf-8 -*-
"""Audit the 60/40 name-substitution pass on merged_rebalanced/.

Checks, over a sample of N documents (default 1000), aligned 1:1 with
merged_original/:

  1. doc-language detection    - did substitute_names see the right language?
  2. script correctness        - names in RU docs Cyrillic, else Latin
  3. garbage / fallback names  - "SurnameNNNN", "NameNNNN" leaking through
  4. names actually changed    - GIVENNAME/SURNAME spans differ from original
  5. repeat-mention consistency- same original value -> one replacement per doc
  6. offset / count integrity  - spans valid, entity count preserved
  7. 60/40 ratio               - reconstructed by replaying the RNG stream

Usage:
    python scripts/audit_substitution.py [--split train] [--n 1000]
"""

from __future__ import annotations
import argparse
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from substitute_names import get_doc_language, LANGUAGES

ORIG_DIR = Path("data/processed/merged_original")
NEW_DIR = Path("data/processed/merged_rebalanced")

CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-zÇçĞğİıÖöŞşÜüƏə]")
GARBAGE_RE = re.compile(r"^(Surname|Name|Givenname)\d{3,4}$")

NAME_LABELS = ("GIVENNAME", "SURNAME")


def script_of(s: str) -> str:
    """Dominant script of a string: 'cyrillic', 'latin', 'other', or 'empty'."""
    cyr = len(CYR_RE.findall(s))
    lat = len(LAT_RE.findall(s))
    if cyr == 0 and lat == 0:
        return "empty"
    if cyr > lat:
        return "cyrillic"
    if lat > cyr:
        return "latin"
    return "other"


def name_spans(doc: dict) -> list[tuple[str, str]]:
    """(label, value) for every GIVENNAME/SURNAME entity, in list order."""
    text = doc["text"]
    out = []
    for e in doc.get("entities", []):
        if e.get("label") in NAME_LABELS:
            s, en = e.get("start", 0), e.get("end", 0)
            out.append((e["label"], text[s:en] if 0 <= s <= en <= len(text) else None))
    return out


def _consume_doc(d: dict, native_pct: float = 0.60) -> bool:
    """Consume exactly the global-RNG draws that substitute_names_in_doc makes
    for one document, and return its `use_native` flag.

    Stream usage per doc:
      * one random.random()  -- the 60/40 roll
      * one random.choice()  -- per UNIQUE (label, old_value) name key, only
                                when the doc rolled foreign
    The NameSampler draws from its own Random(42), so it is not replayed here.
    """
    use_native = random.random() < native_pct
    if not use_native:
        doc_lang = get_doc_language(d)
        seen = set()
        text = d["text"]
        for e in reversed(d.get("entities", [])):
            lab = e.get("label", "")
            if lab not in NAME_LABELS:
                continue
            s, en = e.get("start", 0), e.get("end", 0)
            key = (lab, text[s:en])
            if key in seen:
                continue
            seen.add(key)
            random.choice([l for l in LANGUAGES if l != doc_lang])
    return use_native


def replay_native_flags(splits_in_order: list[tuple[str, list[dict]]],
                        seed: int = 42) -> dict[str, list[bool]]:
    """Replay the whole run's RNG stream, in the split order the real run used
    (substitute_names.py seeds once, then does train, then val, then test).

    Returns {split_name: [use_native per doc]}.
    """
    random.seed(seed)
    out: dict[str, list[bool]] = {}
    for name, docs in splits_in_order:
        out[name] = [_consume_doc(d) for d in docs]
    return out


def load(split: str, d: Path) -> list[dict]:
    with open(d / f"{split}.docs.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="train", choices=["train", "val", "test"])
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args()

    # The real run (substitute_names.py) seeds once and processes splits in
    # this fixed order; the RNG stream must be replayed the same way or the
    # native/foreign flags for val and test come out desynced.
    RUN_ORDER = ["train", "val", "test"]

    print("Loading all splits for an in-order RNG replay...", file=sys.stderr)
    orig_by_split = {s: load(s, ORIG_DIR) for s in RUN_ORDER}
    flags_by_split = replay_native_flags(
        [(s, orig_by_split[s]) for s in RUN_ORDER], args.seed)

    orig = orig_by_split[args.split]
    new = load(args.split, NEW_DIR)
    assert len(orig) == len(new), f"length mismatch {len(orig)} vs {len(new)}"
    native_flags = flags_by_split[args.split]

    # deterministic sample
    rng = random.Random(args.seed)
    idxs = rng.sample(range(len(orig)), min(args.n, len(orig)))

    # ---- counters -------------------------------------------------------
    doclang_actual = Counter()          # doc["lang"]
    doclang_seen = Counter()            # what get_doc_language returned
    doclang_mismatch = Counter()        # (actual -> seen) when different
    roll_by_lang = defaultdict(Counter) # lang -> {native, foreign}

    name_entities = 0
    changed = 0
    unchanged_examples = []
    script_ok = 0
    script_bad = 0
    script_bad_examples = []
    garbage = 0
    garbage_examples = []
    repeat_checks = 0
    repeat_ok = 0
    repeat_bad_examples = []
    offset_bad = 0
    count_bad = 0

    ex_by_cell = defaultdict(list)  # (doc_lang, native?) -> [(before,after)]

    for i in idxs:
        od, nd = orig[i], new[i]
        actual = od.get("lang", "?")
        seen = get_doc_language(od)
        doclang_actual[actual] += 1
        doclang_seen[seen] += 1
        if actual != seen:
            doclang_mismatch[(actual, seen)] += 1

        is_native = native_flags[i]
        roll_by_lang[actual]["native" if is_native else "foreign"] += 1

        # entity count integrity
        if len(od.get("entities", [])) != len(nd.get("entities", [])):
            count_bad += 1

        # offset integrity on new doc
        ntext = nd["text"]
        for e in nd.get("entities", []):
            s, en = e.get("start"), e.get("end")
            if s is None or en is None or not (0 <= s <= en <= len(ntext)):
                offset_bad += 1
                break

        o_names = name_spans(od)
        n_names = name_spans(nd)
        expected_script = "cyrillic" if actual == "ru" else "latin"

        # repeat-mention: same original value -> single replacement
        by_val = defaultdict(set)
        for (ol, ov), (nl, nv) in zip(o_names, n_names):
            if ov is None or nv is None:
                continue
            by_val[(ol, ov)].add(nv)
        for k, vs in by_val.items():
            repeat_checks += 1
            if len(vs) == 1:
                repeat_ok += 1
            elif len(repeat_bad_examples) < 8:
                repeat_bad_examples.append((actual, k, sorted(vs)))

        for (ol, ov), (nl, nv) in zip(o_names, n_names):
            if nv is None:
                continue
            name_entities += 1
            if ov != nv:
                changed += 1
            elif len(unchanged_examples) < 10:
                unchanged_examples.append((actual, ol, ov))

            sc = script_of(nv)
            if sc in ("empty",):
                pass
            elif sc == expected_script:
                script_ok += 1
            else:
                script_bad += 1
                if len(script_bad_examples) < 15:
                    script_bad_examples.append((actual, expected_script, ol, ov, nv))

            if GARBAGE_RE.match(nv):
                garbage += 1
                if len(garbage_examples) < 15:
                    garbage_examples.append((actual, ol, ov, nv))

            cell = (actual, "native" if is_native else "foreign")
            if len(ex_by_cell[cell]) < args.examples:
                ex_by_cell[cell].append((ov, nv))

    # ---- report -------------------------------------------------------
    W = 78
    def rule(c="-"): print(c * W)
    def pct(a, b): return f"{(100*a/b):.1f}%" if b else "n/a"

    print()
    rule("=")
    print(f"  SUBSTITUTION AUDIT  --  split={args.split}  sample={len(idxs):,} docs")
    rule("=")

    print("\n1. DOC-LANGUAGE DETECTION  (what substitute_names actually saw)")
    print(f"   actual doc['lang'] : {dict(doclang_actual)}")
    print(f"   get_doc_language() : {dict(doclang_seen)}")
    mism = sum(doclang_mismatch.values())
    print(f"   mismatched         : {mism}/{len(idxs)}  ({pct(mism,len(idxs))})")
    for (a, s), c in doclang_mismatch.most_common():
        print(f"      {a:3} treated as {s:3} : {c}")

    print("\n2. 60/40 ROLL  (RNG replay, per ACTUAL language)")
    print(f"   {'lang':<6}{'native':>10}{'foreign':>10}{'native %':>12}")
    tot_n = tot_f = 0
    for lg in ("az", "en", "ru", "tr"):
        n = roll_by_lang[lg]["native"]; f = roll_by_lang[lg]["foreign"]
        tot_n += n; tot_f += f
        print(f"   {lg:<6}{n:>10}{f:>10}{pct(n, n+f):>12}")
    print(f"   {'ALL':<6}{tot_n:>10}{tot_f:>10}{pct(tot_n, tot_n+tot_f):>12}")
    print("   (target: 60.0% native)")

    print("\n3. SCRIPT CORRECTNESS  (name matches doc script: RU=Cyrillic, else Latin)")
    tot = script_ok + script_bad
    print(f"   correct : {script_ok}/{tot}  ({pct(script_ok, tot)})")
    print(f"   WRONG   : {script_bad}/{tot}  ({pct(script_bad, tot)})")
    for a, exp, ol, ov, nv in script_bad_examples:
        print(f"      [{a}] want {exp:8} {ol:9} {ov!r} -> {nv!r}")

    print("\n4. GARBAGE / FALLBACK NAMES  (empty-pool sentinels)")
    print(f"   count : {garbage}/{name_entities}  ({pct(garbage, name_entities)})")
    for a, ol, ov, nv in garbage_examples:
        print(f"      [{a}] {ol:9} {ov!r} -> {nv!r}")

    print("\n5. NAMES ACTUALLY CHANGED")
    print(f"   changed : {changed}/{name_entities}  ({pct(changed, name_entities)})")
    for a, ol, ov in unchanged_examples:
        print(f"      unchanged [{a}] {ol:9} {ov!r}")

    print("\n6. REPEAT-MENTION CONSISTENCY  (same original value -> one replacement)")
    print(f"   consistent : {repeat_ok}/{repeat_checks}  ({pct(repeat_ok, repeat_checks)})")
    for a, k, vs in repeat_bad_examples:
        print(f"      [{a}] {k} -> {vs}")

    print("\n7. STRUCTURAL INTEGRITY")
    print(f"   entity-count preserved : {len(idxs)-count_bad}/{len(idxs)}")
    print(f"   offsets valid          : {len(idxs)-offset_bad}/{len(idxs)}")

    print("\n8. BEFORE -> AFTER EXAMPLES  (by actual lang x roll)")
    for lg in ("az", "en", "ru", "tr"):
        for roll in ("native", "foreign"):
            cell = ex_by_cell.get((lg, roll), [])
            if not cell:
                continue
            print(f"\n   {lg.upper()}  /  {roll}")
            for ov, nv in cell[:args.examples]:
                print(f"      {ov!r:32} -> {nv!r}")

    rule("=")


if __name__ == "__main__":
    main()
