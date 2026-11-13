"""Compare two scoreboard runs (checkpoint 1 vs a new model) set by set.

    python eval/compare_runs.py --base-probes A.json --new-probes B.json \
        --base-runb C.json --new-runb D.json --out compare.md \
        [--base-real E.json --new-real F.json --real-out private/compare_real_text.md]

Reads only the aggregate reports written by eval/scoreboard.py (never
document text). Writes markdown tables with checkpoint 1, the new model and
the difference:
  probes      overall exact F1 and decoy trigger, then every target
              condition per family (both tracks);
  runb_test   micro P/R/F1, macro F1 and PII-free FP for all documents and
              each split (old/new vs v1, old corpus/new data), then F1 per
              label on all documents;
  real_text   raw counts per label (gold, exact hits, predictions), written
              to a separate, private file (--real-out), never into git.
Differences are percentage points (counts for real text). A warning line is
printed when the two runs did not score the same documents.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SPLITS = [("all", None), ("old (same id and text in v1)", ("by_part", "old")), ("new (v2 only)", ("by_part", "new")),
          ("old corpus", ("by_origin", "old_corpus")), ("new data", ("by_origin", "new_data"))]


def load(p: str | None) -> dict | None:
    return json.loads(Path(p).read_text(encoding="utf-8")) if p else None


def pct(v):
    return "–" if v is None else f"{100 * v:.1f}"


def diff(a, b):
    if a is None or b is None:
        return "–"
    d = 100 * (b - a)
    return "0.0" if abs(d) < 0.05 else f"{d:+.1f}"


def tracks(rep: dict, s: str) -> dict:
    return rep["sets"][s]["tracks"]


def meta_lines(name: str, base: dict, new: dict, s: str) -> list[str]:
    bm, nm = base["meta"], new["meta"]
    bi, ni = base["sets"][s]["info"], new["sets"][s]["info"]
    L = [f"| {name} | checkpoint 1 | new model |", "|---|---|---|",
         f"| model | `{bm['model']}` @ `{str(bm['revision_sha'])[:12]}` | `{nm['model']}` @ `{str(nm['revision_sha'])[:12]}` |",
         f"| documents | {bi.get('documents')} | {ni.get('documents')} |",
         f"| data | `{bi.get('data_sha256_16')}` {bi.get('sample', '')} | `{ni.get('data_sha256_16')}` {ni.get('sample', '')} |",
         f"| code | `{bm['git']['sha'][:7]}` | `{nm['git']['sha'][:7]}` |"]
    same = (bi.get("documents") == ni.get("documents") and bi.get("data_sha256_16") == ni.get("data_sha256_16")
            and bi.get("sample") == ni.get("sample"))
    if not same:
        L += ["", f"**WARNING: the two runs did not score the same {s} documents; differences are not comparable.**"]
    return L


def block(tr: dict, key) -> dict | None:
    if key is None:
        return tr.get("all")
    return tr.get(key[0], {}).get(key[1])


def runb_tables(base: dict, new: dict) -> list[str]:
    bt, nt = tracks(base, "runb_test"), tracks(new, "runb_test")
    ts = [t for t in ("R", "M") if t in bt and t in nt]
    L = ["", "## runb_test (Run B v2 test split)", ""] + meta_lines("runb_test", base, new, "runb_test") + [""]
    head = "| Split | Metric | " + " | ".join(f"{t}: ckpt1 | {t}: new | {t}: Δ" for t in ts) + " |"
    L += [head, "|---|---|" + "---|---|---|" * len(ts)]
    metrics = [("micro P", lambda r: r["exact"]["micro"]["precision"]), ("micro R", lambda r: r["exact"]["micro"]["recall"]),
               ("micro F1", lambda r: r["exact"]["micro"]["f1"]), ("macro F1", lambda r: r["exact"]["macro_f1"]),
               ("PII-free FP", lambda r: r["documents"]["pii_free_fp_rate"])]
    for sname, key in SPLITS:
        if block(bt[ts[0]], key) is None:
            continue
        docs = block(bt[ts[0]], key)["documents"]["documents"]
        for mname, f in metrics:
            cells = []
            for t in ts:
                a, b = block(bt[t], key), block(nt[t], key)
                va, vb = (f(a) if a else None), (f(b) if b else None)
                cells.append(f"{pct(va)} | {pct(vb)} | {diff(va, vb)}")
            L.append(f"| {sname} ({docs:,}) | {mname} | " + " | ".join(cells) + " |")
    L += ["", "F1 per label, all documents (gold spans in brackets):", "",
          "| Label | " + " | ".join(f"{t}: ckpt1 | {t}: new | {t}: Δ" for t in ts) + " |",
          "|---|" + "---|---|---|" * len(ts)]
    labels = sorted({l for t in ts for l in bt[t]["all"]["exact"]["per_label"]} |
                    {l for t in ts for l in nt[t]["all"]["exact"]["per_label"]})
    for lab in labels:
        cells, gold = [], None
        for t in ts:
            a = bt[t]["all"]["exact"]["per_label"].get(lab)
            b = nt[t]["all"]["exact"]["per_label"].get(lab)
            gold = gold or (a or b) and ((a or b)["tp"] + (a or b)["fn"])
            va, vb = (a["f1"] if a else None), (b["f1"] if b else None)
            cells.append(f"{pct(va)} | {pct(vb)} | {diff(va, vb)}")
        L.append(f"| {lab} ({gold or 0:,}) | " + " | ".join(cells) + " |")
    return L


def cond_name(c: dict) -> str:
    s = c["metric"]
    if c.get("labels"):
        s += " [" + ",".join(c["labels"]) + "]"
    if "from" in c:
        s += f" {c['from']}→{','.join(c['to'])}"
    return s


def probe_tables(base: dict, new: dict) -> list[str]:
    bt, nt = tracks(base, "probes"), tracks(new, "probes")
    ts = [t for t in ("R", "M") if t in bt and t in nt]
    L = ["", "## Probes", ""] + meta_lines("probes", base, new, "probes") + [""]
    L += ["| Metric | " + " | ".join(f"{t}: ckpt1 | {t}: new | {t}: Δ" for t in ts) + " |", "|---|" + "---|---|---|" * len(ts)]
    rows = [("exact F1, all probes", lambda tr: tr["all"]["exact"]["micro"]["f1"], True),
            ("decoy trigger (same label)", lambda tr: tr["all"]["decoys"]["overall"]["rate_same_label"], True),
            ("families passing their target", lambda tr: sum(1 for v in tr["targets"].values() if v["pass"]), False)]
    for name, f, is_rate in rows:
        cells = []
        for t in ts:
            a, b = f(bt[t]), f(nt[t])
            cells.append(f"{pct(a)} | {pct(b)} | {diff(a, b)}" if is_rate else f"{a} | {b} | {b - a:+d}")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L += ["", "Every target condition (measured value; pass = meets the target):", "",
          "| Family | Condition | Target | " + " | ".join(f"{t}: ckpt1 | {t}: new | {t}: Δ" for t in ts) + " |",
          "|---|---|---|" + "---|---|---|" * len(ts)]
    for fam in sorted(bt[ts[0]]["targets"]):
        conds = bt[ts[0]]["targets"][fam]["conditions"]
        for i, c in enumerate(conds):
            cells = []
            for t in ts:
                a = bt[t]["targets"].get(fam, {}).get("conditions", [None] * (i + 1))[i]
                b = nt[t]["targets"].get(fam, {}).get("conditions", [None] * (i + 1))[i]
                va, vb = (a or {}).get("measured"), (b or {}).get("measured")
                mark = lambda x: "" if not x or x.get("pass") is None else (" ✓" if x["pass"] else " ✗")  # noqa: E731
                cells.append(f"{pct(va)}{mark(a)} | {pct(vb)}{mark(b)} | {diff(va, vb)}")
            thr = c.get("threshold", c.get("value"))
            L.append(f"| {fam} | {cond_name(c)} | {c['op']} {pct(thr) if thr is not None else 'rel.'} | " + " | ".join(cells) + " |")
    return L


def real_tables(base: dict, new: dict) -> list[str]:
    bt, nt = tracks(base, "real_text"), tracks(new, "real_text")
    ts = [t for t in ("R", "M") if t in bt and t in nt]
    L = ["# Real-text comparison (private: never commit)", ""] + meta_lines("real_text", base, new, "real_text")
    for t in ts:
        a, b = bt[t]["all"]["exact"], nt[t]["all"]["exact"]
        L += ["", f"## Track {t} (exact spans, raw counts)", "",
              "| Label | Gold | ckpt1 found | new found | Δ found | ckpt1 predicted | new predicted | Δ predicted |",
              "|---|---|---|---|---|---|---|---|"]
        labels = sorted(set(a["per_label"]) | set(b["per_label"]),
                        key=lambda l: -((a["per_label"].get(l) or b["per_label"].get(l))["tp"]
                                        + (a["per_label"].get(l) or b["per_label"].get(l))["fn"]))
        rows = [(l, a["per_label"].get(l), b["per_label"].get(l)) for l in labels] + [("**all**", a["micro"], b["micro"])]
        for lab, x, y in rows:
            z = {"tp": 0, "fn": 0, "fp": 0}
            x, y = x or z, y or z
            g = max(x["tp"] + x["fn"], y["tp"] + y["fn"])
            px, py = x["tp"] + x["fp"], y["tp"] + y["fp"]
            L.append(f"| {lab} | {g} | {x['tp']} | {y['tp']} | {y['tp'] - x['tp']:+d} | {px} | {py} | {py - px:+d} |")
    return L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("base-probes", "new-probes", "base-runb", "new-runb", "base-real", "new-real"):
        ap.add_argument(f"--{k}", default=None)
    ap.add_argument("--out", required=True, help="public comparison (probes, runb_test)")
    ap.add_argument("--real-out", default=None, help="private comparison for real_text")
    a = ap.parse_args(argv)
    L = ["# Run comparison: checkpoint 1 vs new model", "",
         "Exact-span percentages; Δ = new − checkpoint 1 in percentage points. Generated by `scripts/score_runb.sh`."]
    bp, np_, br, nr = load(a.base_probes), load(a.new_probes), load(a.base_runb), load(a.new_runb)
    if bp and np_:
        L += probe_tables(bp, np_)
    if br and nr:
        L += runb_tables(br, nr)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote", a.out)
    be, ne = load(a.base_real), load(a.new_real)
    if be and ne and a.real_out:
        Path(a.real_out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.real_out).write_text("\n".join(real_tables(be, ne)) + "\n", encoding="utf-8")
        print("wrote", a.real_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
