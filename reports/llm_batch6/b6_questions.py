"""Batch 6: the three questions in the hand-over (2026-10-14).

1. Name share: label shares per v3 source and for v3 as a whole, against v2
   and the benchmark; names per document in b6 by genre.
2. Repeats: documents in which one value is labelled many times.
3. Runs 2-3 (D-42c code): bracketed phones, bare ZIPs and the new look-alike
   kinds, counted and checked against their shapes, by `_gen_version`.

    python reports/llm_batch6/b6_questions.py B6.jsonl TARGETED.jsonl [--json OUT]

Counts and shapes only; prints at most a few short value examples.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OLD = ROOT / "data" / "processed" / "merged_relabeled_swept_dated"
BENCH = ROOT / "data" / "benchmark_v3" / "pii_az_benchmark_v3_structured_9780.jsonl"
NAMES = ("GIVENNAME", "SURNAME")
RUN1 = "run 1 (before D-40b/D-42c)"
RUN1_VERSION = "57fcdd4581e2"  # _gen_version of run 1 (README: main before D-40b)

NEW_KINDS = {  # kind -> shape it must have
    "email_dotless_domain": lambda v: "@" in v and "." not in v.split("@", 1)[1],
    "api_key_short": lambda v: len(v) < 32,
    "ipv6_non_hex": lambda v: ":" in v and re.search(r"[g-zG-Z]", v) is not None,
    "ipv6_two_compressions": lambda v: v.count("::") >= 2,
    "jwt_two_segments": lambda v: v.count(".") == 1 and v.startswith("eyJ"),
    "cvv_sequential_5": lambda v: v.isdigit() and len(v) == 5,
}
OLD_KINDS = ("cvv_separator", "fin_with_i_or_o", "fin_6_chars")
BRACKET_PHONE = re.compile(r"^\+994 \(\d\d\) \d{3}-\d\d-\d\d$")
BARE_ZIP = re.compile(r"^\d{4}$")


def records(path: Path, drop: set | None = None):
    with path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if drop is not None and (r.get("lang") != "az" or r["id"] in drop):
                continue
            yield r


def label_counts(recs) -> tuple[Counter, int]:
    c, n = Counter(), 0
    for r in recs:
        n += 1
        c.update(e["label"] for e in r["entities"])
    return c, n


def name_share(c: Counter) -> float:
    total = sum(c.values())
    return sum(c[l] for l in NAMES) / total if total else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("b6", type=Path)
    ap.add_argument("targeted", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    out: dict = {}

    # ---- 1. name share per source
    drop = {json.loads(l)["id"] for l in (OLD / "az_drop_list.jsonl").open(encoding="utf-8")}
    src: dict[str, tuple[Counter, int]] = {}
    old = Counter(); n_old = 0
    for split in ("train", "val", "test"):
        c, n = label_counts(records(OLD / f"{split}.docs.jsonl", drop))
        old += c; n_old += n
    src["old (kept az)"] = (old, n_old)
    b15 = Counter(); n15 = 0
    for b in range(1, 6):
        c, n = label_counts(records(ROOT / "data" / "raw" / f"sprint1_llm_b{b}.clean.jsonl"))
        src[f"llm b{b}"] = (c, n); b15 += c; n15 += n
    b6 = list(records(args.b6))
    src["llm b6"] = label_counts(b6)
    src["targeted 25k"] = label_counts(records(args.targeted))
    src["benchmark"] = label_counts(records(BENCH))
    v2 = old + b15 + src["targeted 25k"][0]
    v3 = v2 + src["llm b6"][0]
    src["v2 mix (old + b1-b5 + targeted)"] = (v2, n_old + n15 + src["targeted 25k"][1])
    src["v3 mix (+ b6)"] = (v3, src["v2 mix (old + b1-b5 + targeted)"][1] + src["llm b6"][1])

    print("1. NAME SHARE (GIVENNAME + SURNAME of all labels)")
    print(f"  {'source':34} {'docs':>8} {'labels':>9} {'names':>8} {'share':>6}  names/doc")
    rows = {}
    for k, (c, n) in src.items():
        names = sum(c[l] for l in NAMES)
        rows[k] = {"docs": n, "labels": sum(c.values()), "names": names,
                   "share": round(name_share(c), 4), "names_per_doc": round(names / n, 2) if n else 0}
        print(f"  {k:34} {n:8,} {sum(c.values()):9,} {names:8,} {name_share(c):6.1%}  {names / max(n, 1):.2f}")
    out["name_share"] = rows
    print("\n  label shares, v2 mix -> v3 mix -> benchmark (top 14 of v3):")
    tv2, tv3, tb = sum(v2.values()), sum(v3.values()), sum(src["benchmark"][0].values())
    shares = {}
    for l, _ in v3.most_common(14):
        shares[l] = [round(v2[l] / tv2, 4), round(v3[l] / tv3, 4), round(src["benchmark"][0][l] / tb, 4)]
        print(f"    {l:26} {v2[l] / tv2:6.1%} -> {v3[l] / tv3:6.1%}   bench {src['benchmark'][0][l] / tb:6.1%}")
    out["label_shares_v2_v3_bench"] = shares

    per_doc = [sum(e["label"] in NAMES for e in r["entities"]) for r in b6]
    print("\n  b6 names per document: mean %.2f, median %d, p90 %d, max %d; documents with >=20: %d, >=40: %d"
          % (statistics.mean(per_doc), statistics.median(per_doc),
             sorted(per_doc)[int(.9 * len(per_doc))], max(per_doc),
             sum(x >= 20 for x in per_doc), sum(x >= 40 for x in per_doc)))
    distinct = [len({(e["label"], e["text"] if "text" in e else r["text"][e["start"]:e["end"]])
                     for e in r["entities"] if e["label"] in NAMES}) for r in b6]
    print("  b6 distinct names per document: mean %.2f, p90 %d" % (
        statistics.mean(distinct), sorted(distinct)[int(.9 * len(distinct))]))
    by_genre = defaultdict(lambda: [0, 0, 0])
    for r, k in zip(b6, per_doc):
        g = by_genre[r.get("_doc_type")]
        g[0] += 1; g[1] += k; g[2] += len(r["entities"])
    print("  by genre: docs, names/doc, name share")
    for g, (n, k, t) in sorted(by_genre.items(), key=lambda x: -x[1][1] / x[1][0]):
        print(f"    {g:26} {n:6,} {k / n:6.2f} {k / max(t, 1):6.1%}")
    out["b6_names_per_doc"] = {"mean": round(statistics.mean(per_doc), 2), "max": max(per_doc),
                               "ge20": sum(x >= 20 for x in per_doc), "ge40": sum(x >= 40 for x in per_doc),
                               "by_genre": {g: [n, round(k / n, 2)] for g, (n, k, t) in by_genre.items()}}

    # ---- 2. repeats of one value in one document
    def repeats(recs, exclude_names: bool):
        dist = Counter(); worst = []
        for r in recs:
            c = Counter((e["label"], r["text"][e["start"]:e["end"]]) for e in r["entities"]
                        if not (exclude_names and e["label"] in NAMES))
            if not c:
                continue
            (lab, val), m = c.most_common(1)[0]
            dist[m] += 1
            if m >= 10:
                worst.append((m, r["id"], lab))
        return dist, sorted(worst, reverse=True)

    print("\n2. REPEATS: documents by the most times one value is labelled in them")
    rep = {}
    for name, recs, excl in (("b6, all labels", b6, False), ("b6, names left out", b6, True),
                             ("b1-b5 clean, names left out",
                              (r for b in range(1, 6) for r in records(ROOT / "data" / "raw" / f"sprint1_llm_b{b}.clean.jsonl")), True),
                             ("benchmark, names left out", records(BENCH), True)):
        dist, worst = repeats(recs, excl)
        n = sum(dist.values())
        ge = {t: sum(v for k, v in dist.items() if k >= t) for t in (5, 10, 20)}
        print(f"  {name:30} docs {n:6,}; one value >=5x: {ge[5]:5,}  >=10x: {ge[10]:4,}  >=20x: {ge[20]:3,}; worst {worst[:4]}")
        rep[name] = {"docs": n, "ge5": ge[5], "ge10": ge[10], "ge20": ge[20], "worst": worst[:15]}
    out["repeats"] = rep

    # ---- 3. D-42c shapes by run
    def run_of(r):
        return RUN1 if r.get("_gen_version") == RUN1_VERSION else "runs 2-3 (D-42c code)"
    phones = defaultdict(Counter); zips = defaultdict(Counter); kinds = defaultdict(Counter)
    bad = defaultdict(list); oldk = Counter(); versions = Counter()
    for r in b6:
        run = run_of(r); versions[(run, r.get("_gen_version"))] += 1
        for e in r["entities"]:
            v = r["text"][e["start"]:e["end"]]
            if e["label"] == "TELEPHONENUM":
                phones[run]["all"] += 1; phones[run]["+994 (55) 123-45-67"] += bool(BRACKET_PHONE.match(v))
            elif e["label"] == "ZIPCODE":
                zips[run]["all"] += 1; zips[run]["bare 4 digits"] += bool(BARE_ZIP.match(v))
        for d in r.get("_decoys", []):
            v = r["text"][d["start"]:d["end"]]
            kinds[run][d["kind"]] += 1
            if d["kind"] in NEW_KINDS and not NEW_KINDS[d["kind"]](v):
                bad[d["kind"]].append((r["id"], v[:60]))
            if d["kind"] in OLD_KINDS:
                oldk[d["kind"]] += 1
    print("\n3. D-42c SHAPES BY RUN (run 1 = `_gen_version` %s)" % RUN1_VERSION)
    print("  _gen_version per run:", dict(versions))
    for run in (RUN1, "runs 2-3 (D-42c code)"):
        p, z = phones[run], zips[run]
        print(f"  {run}: phones {p['all']:,}, bracketed {p['+994 (55) 123-45-67']:,} ({p['+994 (55) 123-45-67'] / max(p['all'], 1):.1%}); "
              f"ZIPs {z['all']:,}, bare {z['bare 4 digits']:,} ({z['bare 4 digits'] / max(z['all'], 1):.1%})")
        print("    new look-alike kinds:", {k: kinds[run][k] for k in NEW_KINDS})
    print("  new kinds not matching their shape:", {k: len(v) for k, v in bad.items()} or 0,
          {k: v[:3] for k, v in bad.items()})
    print("  retired kinds present (cvv_separator, fin_with_i_or_o, fin_6_chars):", dict(oldk) or 0)
    out["d42c"] = {"phones": {k: dict(v) for k, v in phones.items()}, "zips": {k: dict(v) for k, v in zips.items()},
                   "new_kinds": {run: {k: kinds[run][k] for k in NEW_KINDS} for run in kinds},
                   "bad_shape": {k: len(v) for k, v in bad.items()}, "retired_kinds": dict(oldk)}
    if args.json:
        args.json.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
