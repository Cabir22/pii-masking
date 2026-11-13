"""m1 audit: verify the claimed public results from the saved scoreboard reports.

Reads the reports as written (nothing is re-scored here) and applies eval/release_check.py's own
rule functions, on track M (D-64a) and track R. Writes scorecard.md and label_table.md.

  python reports/m1_audit/scorecard.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval"))
import release_check as rc  # noqa: E402

OUT = Path.home() / "m1_public_out"
R = {"m1": rc.load(OUT / "m1_public.json"), "ckpt1_langs": rc.load(OUT / "ckpt1_langs.json"),
     "ckpt1_bench": rc.load(ROOT / "reports/scoreboard/baseline_ckpt1_benchmark.json"),
     "ckpt1_probes": rc.load(ROOT / "reports/scoreboard/score_runb/v42_seed42_public/ckpt1_probes.json"),
     "v42_bench": rc.load(ROOT / "reports/scoreboard/score_runb/v42_seed42_public/new_benchmark.json"),
     "v42_probes": rc.load(ROOT / "reports/scoreboard/score_runb/v42_seed42_public/new_probes.json")}


def sub(rep, s, t, part="all"):
    return rc.tr(rep, s, t)[part]


def micro(rep, s, t, part="all"):
    return sub(rep, s, t, part)["exact"]["micro"]


def main() -> int:
    L = ["# m1 audit: verified public scorecard", "",
         "Source: the saved reports (`~/m1_public_out/`, `reports/scoreboard/…`), rules from `eval/release_check.py`. "
         "Exact-span micro scores: an entity counts only with the exact start, end and label.", ""]
    L += ["## Benchmark (Azerbaijani, first 5,000 documents of benchmark_v3, D-6)", "",
          "| Model | Track | Population | TP | FP | FN | P | R | F1 |", "|---|---|---|---|---|---|---|---|---|"]
    for mk, rep in (("checkpoint 1", R["ckpt1_bench"]), ("v4.2", R["v42_bench"]), ("m1", R["m1"])):
        for t in ("M", "R"):
            for part, pop in (("excl_policy", "policy items out (B1's number)"), ("all", "policy items in")):
                m = micro(rep, "benchmark", t, part)
                L.append(f"| {mk} | {t} | {pop} | {m['tp']} | {m['fp']} | {m['fn']} | {100*m['precision']:.1f} | "
                         f"{100*m['recall']:.1f} | **{100*m['f1']:.1f}** |")
    L += ["", "**96.4 vs 95.4:** the same 5,000 Azerbaijani documents, track M; 96.4 leaves the policy items out "
          "(B1's definition), 95.4 keeps them in. Both are Azerbaijani. Compare m1 with v4.2 within one row type only.", ""]

    L += ["## Rules (public part)", "", "| Rule | Track | Status | Result |", "|---|---|---|---|"]
    for t in ("M", "R"):
        rc.DECIDES = t
        rules = rc.bench_rules(R["m1"], R["ckpt1_bench"])[0]
        rules.append(rc.b3_rule(R["m1"], R["v42_bench"], "v4.2"))
        pr = rc.probe_rules(R["m1"], R["ckpt1_probes"], str(Path.home() / ".cache/pii-scoreboard"))
        rules += pr[0] if isinstance(pr, tuple) else pr
        rules.append(rc.a7_rule(R["m1"], R["ckpt1_langs"], None, None))
        for r in rules:
            if r["id"] in ("B1", "B2", "B3", "C1", "C2", "C3", "C4", "C13", "A7"):
                L.append(f"| {r['id']} | {t} | {r['status']} | {r['result']} |")
    rc.DECIDES = "M"

    L += ["", "## Translated sets (A7: exact micro F1, ≤ 1 point below checkpoint 1)", "",
          "| Set | Docs | Track | checkpoint 1 P / R / F1 | m1 P / R / F1 | TP/FP/FN m1 |", "|---|---|---|---|---|---|"]
    for s in ("golden_en", "lang_tr", "lang_ru"):
        for t in ("M", "R"):
            a, b = micro(R["ckpt1_langs"], s, t), micro(R["m1"], s, t)
            docs = R["m1"]["sets"][s]["info"]["documents"]
            L.append(f"| {s} | {docs} | {t} | {100*a['precision']:.1f} / {100*a['recall']:.1f} / {100*a['f1']:.1f} | "
                     f"{100*b['precision']:.1f} / {100*b['recall']:.1f} / **{100*b['f1']:.1f}** | {b['tp']}/{b['fp']}/{b['fn']} |")
    (HERE / "scorecard.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # language x label table (track M), with baselines where they exist
    T = ["# m1 audit: language × label (track M, exact spans)", "",
         "Support = gold occurrences. Labels with fewer than 30 gold values are marked (few). "
         "Baseline: Azerbaijani benchmark against v4.2 (policy items in); EN/TR/RU against checkpoint 1 "
         "(v4.2 was not scored on the translated sets).", ""]
    for s, base, bname in (("benchmark", R["v42_bench"], "v4.2"), ("golden_en", R["ckpt1_langs"], "ckpt1"),
                           ("lang_tr", R["ckpt1_langs"], "ckpt1"), ("lang_ru", R["ckpt1_langs"], "ckpt1")):
        a = sub(base, s, "M")["exact"]["per_label"]
        b = sub(R["m1"], s, "M")["exact"]["per_label"]
        T += [f"## {s}", "", f"| Label | Support | m1 pred | m1 P | m1 R | m1 F1 | {bname} F1 | Δ F1 | m1 FP | m1 FN |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for lab in sorted(b, key=lambda k: -(b[k]["tp"] + b[k]["fn"])):
            x, y = b[lab], a.get(lab)
            sup = x["tp"] + x["fn"]
            few = " (few)" if sup < 30 else ""
            d = f"{100*(x['f1']-y['f1']):+.1f}" if y else "–"
            T.append(f"| {lab}{few} | {sup} | {x['tp']+x['fp']} | {100*x['precision']:.1f} | {100*x['recall']:.1f} | "
                     f"{100*x['f1']:.1f} | {100*y['f1']:.1f} | {d} | {x['fp']} | {x['fn']} |" if y else
                     f"| {lab}{few} | {sup} | {x['tp']+x['fp']} | {100*x['precision']:.1f} | {100*x['recall']:.1f} | "
                     f"{100*x['f1']:.1f} | – | – | {x['fp']} | {x['fn']} |")
        T.append("")
    (HERE / "label_table.md").write_text("\n".join(T) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
