# -*- coding: utf-8 -*-
"""Distribution analysis of the 60/40 name-substituted corpus.

Runs over the FULL merged_rebalanced/ corpus (all three splits), aligned 1:1
with merged_original/, and reports:

  A. per-language document counts
  B. native vs foreign roll, per language (target 60/40)  -- via RNG replay
  C. foreign-language mix, per source language (target uniform 1/3)
  D. GIVENNAME / SURNAME counts, before vs after
  E. name-pool utilisation: unique names used, top-N concentration
  F. gender balance of substituted given names
  G. script purity, per document language
  H. per-document person count and repeat-mention spread

Usage:
    python scripts/analyze_distribution.py [--splits train val test]
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
from name_pools import load_all_pools

ORIG_DIR = Path("data/processed/merged_original")
NEW_DIR = Path("data/processed/merged_rebalanced")
NAME_LABELS = ("GIVENNAME", "SURNAME")

CYR_RE = re.compile(r"[Ѐ-ӿ]")
LAT_RE = re.compile(r"[A-Za-zÇçĞğİıÖöŞşÜüƏə]")


def script_of(s: str) -> str:
    c, l = len(CYR_RE.findall(s)), len(LAT_RE.findall(s))
    if c == 0 and l == 0:
        return "empty"
    return "cyrillic" if c > l else "latin" if l > c else "mixed"


def _consume_doc(d: dict, native_pct: float = 0.60):
    """Replay exactly the global-RNG draws substitute_names_in_doc makes for
    one doc. Returns (use_native, {(label, old_value): sampled_lang}).
    The sampler uses its own Random, so only the roll + the per-key
    random.choice() are on this stream."""
    use_native = random.random() < native_pct
    doc_lang = get_doc_language(d)
    key_lang: dict[tuple, str] = {}
    text = d["text"]
    seen = set()
    for e in reversed(d.get("entities", [])):
        if e.get("label") not in NAME_LABELS:
            continue
        s, en = e.get("start", 0), e.get("end", 0)
        key = (e["label"], text[s:en])
        if key in seen:
            continue
        seen.add(key)
        if use_native:
            key_lang[key] = doc_lang
        else:
            key_lang[key] = random.choice([l for l in LANGUAGES if l != doc_lang])
    return use_native, key_lang


def replay(splits_in_order, seed=42):
    random.seed(seed)
    out = {}
    for name, docs in splits_in_order:
        out[name] = [_consume_doc(d) for d in docs]
    return out


def load(split, d):
    with open(d / f"{split}.docs.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def classify_name_lang(value: str, doc_lang: str, pools, latin_lookup) -> str:
    """Best-effort: which language pool did this (already-rendered) name come
    from? For RU docs the name is Cyrillic so only 'ru' vs 'transliterated'
    is knowable; for Latin docs check membership in az/en/tr Title-case sets."""
    if doc_lang == "ru":
        return "ru-or-translit"
    v = value.strip()
    hits = [lg for lg in ("az", "en", "tr") if v in latin_lookup[lg]]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        return "unknown"
    return "ambiguous"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"],
                    choices=["train", "val", "test"])
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--topn", type=int, default=15)
    args = ap.parse_args()

    RUN_ORDER = ["train", "val", "test"]
    print("Loading all splits (original for RNG replay + rebalanced)...", file=sys.stderr)
    orig_all = {s: load(s, ORIG_DIR) for s in RUN_ORDER}
    flags_all = replay([(s, orig_all[s]) for s in RUN_ORDER], args.seed)

    print("Loading name pools for utilisation stats...", file=sys.stderr)
    pools = load_all_pools()
    latin_lookup = {
        lg: {e.name for slot in ("given_names_m", "given_names_f", "surnames")
             for e in pools[lg][slot]}
        for lg in ("az", "en", "tr")
    }
    pool_sizes = {
        lg: {
            "given": len(pools[lg]["given_names_m"]) + len(pools[lg]["given_names_f"]),
            "surnames": len(pools[lg]["surnames"]),
        }
        for lg in LANGUAGES
    }

    # accumulators
    doc_lang_ct = Counter()
    roll_ct = defaultdict(Counter)                    # lang -> native/foreign
    foreign_src_ct = defaultdict(Counter)             # doc_lang -> sampled src lang (from RNG replay)
    label_ct_before = Counter()
    label_ct_after = Counter()
    used_names = defaultdict(Counter)                  # (doc_lang, label) -> Counter(name)
    given_script_ct = defaultdict(Counter)            # doc_lang -> script
    surname_script_ct = defaultdict(Counter)
    persons_per_doc = Counter()
    gender_ct = defaultdict(Counter)                   # (src_lang) -> M/F/both/unknown  (native rolls only)

    # gender-exclusive sets: a name in BOTH slots is "both" (unisex), not M or F
    g_excl = {}
    for lg in LANGUAGES:
        m = {e.name for e in pools[lg]["given_names_m"]}
        f = {e.name for e in pools[lg]["given_names_f"]}
        g_excl[lg] = (m - f, f - m, m & f)   # (male-only, female-only, unisex)

    for split in args.splits:
        new = load(split, NEW_DIR)
        orig = orig_all[split]
        rep = flags_all[split]
        for idx, (od, nd) in enumerate(zip(orig, new)):
            dl = od.get("lang", "?")
            doc_lang_ct[dl] += 1
            is_native, key_lang = rep[idx]
            roll_ct[dl]["native" if is_native else "foreign"] += 1

            ntext = nd["text"]
            otext = od["text"]
            distinct_people = set()
            for oe, ne in zip(od.get("entities", []), nd.get("entities", [])):
                lab = oe.get("label")
                if lab in NAME_LABELS:
                    label_ct_before[lab] += 1
                if ne.get("label") in NAME_LABELS:
                    lab2 = ne["label"]
                    label_ct_after[lab2] += 1
                    val = ntext[ne["start"]:ne["end"]]
                    oval = otext[oe["start"]:oe["end"]]
                    distinct_people.add((lab2, oval))
                    src_lang = key_lang.get((lab2, oval), dl)
                    used_names[(dl, lab2)][val] += 1
                    sc = script_of(val)
                    if lab2 == "GIVENNAME":
                        given_script_ct[dl][sc] += 1
                        mo, fo, uni = g_excl.get(src_lang, (set(), set(), set()))
                        g = ("M" if val in mo else "F" if val in fo
                             else "unisex" if val in uni else "unknown")
                        gender_ct[src_lang][g] += 1
                    else:
                        surname_script_ct[dl][sc] += 1
                    if not is_native:
                        foreign_src_ct[dl][src_lang] += 1
            persons_per_doc[len({p[1] for p in distinct_people})] += 1

    # ---------------- report ----------------
    W = 80
    def rule(c="="): print(c * W)
    def pct(a, b): return f"{100*a/b:5.1f}%" if b else "  n/a"

    rule()
    print(f"  NAME-SUBSTITUTION DISTRIBUTION  --  splits: {', '.join(args.splits)}")
    rule()

    total_docs = sum(doc_lang_ct.values())
    print(f"\nA. DOCUMENTS BY LANGUAGE   (total {total_docs:,})")
    for lg in ("az", "en", "ru", "tr"):
        n = doc_lang_ct[lg]
        print(f"   {lg}  {n:>8,}   {pct(n, total_docs)}")

    print("\nB. NATIVE vs FOREIGN ROLL   (target 60.0 / 40.0)")
    print(f"   {'lang':<6}{'native':>10}{'foreign':>10}{'native%':>10}{'foreign%':>10}")
    tn = tf = 0
    for lg in ("az", "en", "ru", "tr"):
        n, f = roll_ct[lg]["native"], roll_ct[lg]["foreign"]
        tn += n; tf += f
        print(f"   {lg:<6}{n:>10,}{f:>10,}{pct(n, n+f):>10}{pct(f, n+f):>10}")
    print(f"   {'ALL':<6}{tn:>10,}{tf:>10,}{pct(tn, tn+tf):>10}{pct(tf, tn+tf):>10}")

    print("\nC. FOREIGN-ROLL SOURCE LANGUAGE   (from RNG replay; target ~33.3% each)")
    for dl in ("az", "en", "ru", "tr"):
        c = foreign_src_ct[dl]
        tot = sum(c.values())
        if not tot:
            continue
        others = [l for l in LANGUAGES if l != dl]
        parts = "   ".join(f"{o}: {pct(c[o], tot).strip()}" for o in others)
        print(f"   {dl} docs (n={tot:,})   {parts}")

    print("\nD. NAME ENTITIES  (before -> after; must be unchanged)")
    for lab in NAME_LABELS:
        b, a = label_ct_before[lab], label_ct_after[lab]
        flag = "OK" if a == b else "*** MISMATCH ***"
        print(f"   {lab:<10} {b:>8,} -> {a:>8,}   {flag}")

    print("\nE. NAME-POOL UTILISATION   (unique substituted values / pool size)")
    print(f"   {'lang/label':<18}{'unique used':>12}{'pool size':>12}{'top-'+str(args.topn)+' share':>14}")
    for dl in ("az", "en", "ru", "tr"):
        for lab in NAME_LABELS:
            c = used_names[(dl, lab)]
            if not c:
                continue
            tot = sum(c.values())
            topshare = sum(v for _, v in c.most_common(args.topn)) / tot
            psize = pool_sizes[dl]["given" if lab == "GIVENNAME" else "surnames"]
            print(f"   {dl+'/'+lab:<18}{len(c):>12,}{psize:>12,}{topshare*100:>13.1f}%")

    print(f"\n   Top {args.topn} substituted SURNAMEs per language:")
    for dl in ("az", "en", "ru", "tr"):
        c = used_names[(dl, "SURNAME")]
        if not c:
            continue
        tot = sum(c.values())
        items = "  ".join(f"{n}({100*v/tot:.1f}%)" for n, v in c.most_common(args.topn))
        print(f"     {dl}: {items}")

    print(f"\n   Top {args.topn} substituted GIVENNAMEs per language:")
    for dl in ("az", "en", "ru", "tr"):
        c = used_names[(dl, "GIVENNAME")]
        if not c:
            continue
        tot = sum(c.values())
        items = "  ".join(f"{n}({100*v/tot:.1f}%)" for n, v in c.most_common(args.topn))
        print(f"     {dl}: {items}")

    print("\nF. GENDER of substituted GIVENNAMEs, by SOURCE language")
    print("   (gender-exclusive pool sets; 'unisex' = name in both M and F slots)")
    for sl in ("az", "en", "ru", "tr"):
        c = gender_ct[sl]
        tot = sum(c.values())
        if not tot:
            continue
        print(f"   from {sl}   M {pct(c['M'], tot)}   F {pct(c['F'], tot)}   "
              f"unisex {pct(c['unisex'], tot)}   unknown {pct(c['unknown'], tot)}   (n={tot:,})")
    print("   (EN given-name list has no gender -> every EN name is 'unisex' here)")

    print("\nG. SCRIPT PURITY by document language   (RU must be Cyrillic; others Latin)")
    for dl in ("az", "en", "ru", "tr"):
        g, s = given_script_ct[dl], surname_script_ct[dl]
        want = "cyrillic" if dl == "ru" else "latin"
        gt, st = sum(g.values()), sum(s.values())
        gbad = gt - g[want] - g["empty"]
        sbad = st - s[want] - s["empty"]
        print(f"   {dl}   GIVENNAME {g[want]:,}/{gt:,} {want} (bad {gbad})   "
              f"SURNAME {s[want]:,}/{st:,} {want} (bad {sbad})")

    print("\nH. DISTINCT PEOPLE PER DOCUMENT")
    tot = sum(persons_per_doc.values())
    for k in sorted(persons_per_doc):
        if k > 8:
            continue
        print(f"   {k} people  {persons_per_doc[k]:>8,}   {pct(persons_per_doc[k], tot)}")
    big = sum(v for k, v in persons_per_doc.items() if k > 8)
    if big:
        print(f"   9+ people  {big:>8,}   {pct(big, tot)}")

    rule()


if __name__ == "__main__":
    main()
