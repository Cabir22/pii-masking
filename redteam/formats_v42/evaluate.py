"""Score predictions.jsonl against the frozen cases (spans.jsonl) and write results.

Per expected occurrence, on one decoding (M by default; R for comparison):
  correct          a prediction with exactly its span and label
  boundary         fully masked with the right label, but not the exact span (overreach or split)
  wrong_type       fully masked, but no covering prediction has the right label
  partly_masked    some of its characters stay visible
  missed           none of its characters is masked
"Fully masked" counts every character except whitespace and invisible format characters (Cf):
a digit or letter left outside a mask is a visible fragment. A prediction that overlaps no
expected occurrence is a false alarm. Diagnostics: overreach, split, merged.

  python redteam/formats_v42/evaluate.py            # writes results.jsonl and results.md
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return {json.loads(l)["id"]: json.loads(l) for l in (HERE / name).open(encoding="utf-8")}


def required(text: str, s: int, e: int) -> list[int]:
    return [i for i in range(s, e) if not text[i].isspace() and unicodedata.category(text[i]) != "Cf"]


def score_case(text: str, exp: list[dict], pred: list[dict]) -> dict:
    out_exp, used = [], set()
    for x in exp:
        s, e = x["start"], x["end"]
        need = required(text, s, e)
        over = [i for i, p in enumerate(pred) if p["start"] < e and s < p["end"]]
        cov = {c for i in over for c in range(pred[i]["start"], pred[i]["end"])}
        hit = sum(1 for c in need if c in cov)
        exact = any(pred[i]["start"] == s and pred[i]["end"] == e and pred[i]["label"] == x["label"] for i in over)
        if exact:
            cat = "correct"
        elif hit == 0:
            cat = "missed"
        elif hit < len(need):
            cat = "partly_masked"
        elif any(pred[i]["label"] == x["label"] for i in over):
            cat = "boundary"
        else:
            cat = "wrong_type"
        diag = []
        if any(required(text, pred[i]["start"], s) or required(text, e, pred[i]["end"]) for i in over):
            diag.append("overreach")
        if len(over) > 1:
            diag.append("split")
        used.update(over)
        visible = "".join(text[c] for c in need if c not in cov)
        out_exp.append({**x, "category": cat, "diag": diag, "pred_labels": [pred[i]["label"] for i in over],
                        "visible": visible})
    # merged: one prediction covering two or more expected occurrences
    for i, p in enumerate(pred):
        hits = [o for o in out_exp if p["start"] < o["end"] and o["start"] < p["end"]]
        if len(hits) > 1:
            for o in hits:
                if "merged" not in o["diag"]:
                    o["diag"].append("merged")
    fa = [p | {"text": text[p["start"]:p["end"]]} for i, p in enumerate(pred) if i not in used]
    return {"expected": out_exp, "false_alarms": fa}


def case_pass(r: dict, strict: bool) -> bool:
    ok = {"correct"} if strict else {"correct", "boundary", "wrong_type"}
    return not r["false_alarms"] and all(o["category"] in ok for o in r["expected"])


def main() -> int:
    cases = load("formats_az_v42_200.jsonl")
    spans = load("spans.jsonl")
    meta = load("manifest.jsonl")
    preds = load("predictions.jsonl")
    missing = [i for i in cases if i not in preds]
    if missing:
        print(f"{len(missing)} cases have no predictions yet: {missing[:5]}…")
        return 1
    results = {}
    for cid, c in cases.items():
        results[cid] = {t: score_case(c["text"], spans[cid]["spans"], preds[cid][t]) for t in ("M", "R")}
    with (HERE / "results.jsonl").open("w", encoding="utf-8") as f:
        for cid in cases:
            f.write(json.dumps({"id": cid, **results[cid], "masked_M": preds[cid]["masked_M"],
                                "windows": preds[cid]["windows"]}, ensure_ascii=False) + "\n")

    L = ["# Formats benchmark on v4.2: results", "",
         f"Model `{next(iter(preds.values()))['model']}`, decoder `{next(iter(preds.values()))['settings']['decoder']}`, "
         "max_length 512, stride 256, no truncation (overlapping windows, merged). "
         "**M** = product decoding (decides, D-64a); **R** = raw model.", ""]

    def totals(track: str, ids) -> dict:
        cat, fa, tp, npred = Counter(), 0, 0, 0
        for cid in ids:
            r = results[cid][track]
            cat.update(o["category"] for o in r["expected"])
            fa += len(r["false_alarms"])
            tp += sum(o["category"] == "correct" for o in r["expected"])
            npred += len(preds[cid][track])
        n = sum(cat.values())
        p = tp / npred if npred else 0
        rc = tp / n if n else 0
        f1 = 2 * p * rc / (p + rc) if p + rc else 0
        masked_full = cat["correct"] + cat["boundary"] + cat["wrong_type"]
        return {"n": n, "cat": cat, "fa": fa, "p": p, "r": rc, "f1": f1, "cover": masked_full / n if n else 0,
                "npred": npred, "tp": tp}

    allids = list(cases)
    L += ["## Overall", "", "| | M (product) | R (raw) |", "|---|---|---|"]
    tm, tr = totals("M", allids), totals("R", allids)
    for name, fn in (("Exact span+label precision", lambda t: f"{100*t['p']:.1f}% ({t['tp']}/{t['npred']})"),
                     ("Exact span+label recall", lambda t: f"{100*t['r']:.1f}% ({t['tp']}/{t['n']})"),
                     ("Exact F1", lambda t: f"{100*t['f1']:.1f}"),
                     ("**Fully masked (any label)**", lambda t: f"{100*t['cover']:.1f}% ({t['n']-t['cat']['missed']-t['cat']['partly_masked']}/{t['n']})"),
                     ("Missed", lambda t: str(t["cat"]["missed"])),
                     ("Partly masked (fragment visible)", lambda t: str(t["cat"]["partly_masked"])),
                     ("Wrong type (masked)", lambda t: str(t["cat"]["wrong_type"])),
                     ("Boundary only (masked, right label)", lambda t: str(t["cat"]["boundary"])),
                     ("False alarms", lambda t: str(t["fa"]))):
        L.append(f"| {name} | {fn(tm)} | {fn(tr)} |")
    neg = [cid for cid in cases if not cases[cid]["expected"]]
    negfa = sum(len(results[c]["M"]["false_alarms"]) for c in neg)
    L += ["", f"Negative-only cases: {len(neg)}; with a false alarm on M: "
              f"{sum(1 for c in neg if results[c]['M']['false_alarms'])} ({negfa} false alarms).",
          f"Cases passing strictly (all exact, no false alarm) on M: {sum(case_pass(results[c]['M'], True) for c in cases)}/200; "
          f"safely (every value fully masked, no false alarm): {sum(case_pass(results[c]['M'], False) for c in cases)}/200.", ""]

    L += ["## By group (M)", "", "| Group | Values | Fully masked | Missed | Partly | Wrong type | False alarms | Exact F1 |",
          "|---|---|---|---|---|---|---|---|"]
    by_group = defaultdict(list)
    for cid in cases:
        by_group[meta[cid]["group"]].append(cid)
    for g, ids in by_group.items():
        t = totals("M", ids)
        L.append(f"| {g} | {t['n']} | {100*t['cover']:.0f}% | {t['cat']['missed']} | {t['cat']['partly_masked']} | "
                 f"{t['cat']['wrong_type']} | {t['fa']} | {100*t['f1']:.0f} |")

    L += ["", "## By label (M)", "", "| Label | Values | Correct | Boundary | Wrong type | Partly | Missed |",
          "|---|---|---|---|---|---|---|"]
    lab = defaultdict(Counter)
    for cid in cases:
        for o in results[cid]["M"]["expected"]:
            lab[o["label"]][o["category"]] += 1
    for k, c in sorted(lab.items(), key=lambda kv: -sum(kv[1].values())):
        L.append(f"| {k} | {sum(c.values())} | {c['correct']} | {c['boundary']} | {c['wrong_type']} | "
                 f"{c['partly_masked']} | {c['missed']} |")
    conf = Counter((o["label"], tuple(sorted(set(o["pred_labels"])))) for cid in cases
                   for o in results[cid]["M"]["expected"] if o["category"] == "wrong_type")
    if conf:
        L += ["", "Label confusions (expected → predicted): " +
              "; ".join(f"{a} → {'/'.join(b)} ×{n}" for (a, b), n in conf.most_common())]

    # paired: reference vs transformations (safe pass = every value fully masked, no false alarm)
    L += ["", "## Reference vs transformation (M, safe pass)", "",
          "| Family | Reference | Transformations failing while the reference passes | Both fail | Reference fails, transformation passes |",
          "|---|---|---|---|---|"]
    fams = defaultdict(list)
    for cid in cases:
        fams[meta[cid]["family"]].append(cid)
    for fam, ids in fams.items():
        refs = {meta[c]["reference"] for c in ids}
        cells = [[], [], []]
        for c in ids:
            ref = meta[c]["reference"]
            if ref == c:
                continue
            a, b = case_pass(results[ref]["M"], False), case_pass(results[c]["M"], False)
            if a and not b:
                cells[0].append(c)
            elif not a and not b:
                cells[1].append(c)
            elif not a and b:
                cells[2].append(c)
        refstat = ", ".join(f"{r} {'pass' if case_pass(results[r]['M'], False) else 'FAIL'}" for r in sorted(refs))
        L.append(f"| {fam} | {refstat} | {', '.join(cells[0]) or '–'} | {', '.join(cells[1]) or '–'} | {', '.join(cells[2]) or '–'} |")

    L += ["", "## Every failing case (M)", ""]
    for cid, c in cases.items():
        r = results[cid]["M"]
        bad = [o for o in r["expected"] if o["category"] != "correct"]
        if not bad and not r["false_alarms"]:
            continue
        L.append(f"**{cid}** `{meta[cid]['family']}` — {meta[cid]['factor']}")
        if len(c["text"]) < 400:
            L.append(f"- input: `{json.dumps(c['text'], ensure_ascii=False)[1:-1]}`")
        else:
            L.append(f"- input: long document ({len(c['text'])} characters, {preds[cid]['windows']} windows)")
        for o in bad:
            L.append(f"- {o['category']}: `{json.dumps(o['value'], ensure_ascii=False)[1:-1]}` ({o['label']})"
                     + (f" → predicted {'/'.join(o['pred_labels'])}" if o["pred_labels"] else "")
                     + (f"; visible: `{json.dumps(o['visible'], ensure_ascii=False)[1:-1]}`" if o["visible"] else "")
                     + (f"; {', '.join(o['diag'])}" if o["diag"] else ""))
        for p in r["false_alarms"]:
            L.append(f"- false_alarm: `{json.dumps(p['text'], ensure_ascii=False)[1:-1]}` as {p['label']}")
        if len(c["text"]) < 400:
            L.append(f"- masked (M): `{json.dumps(preds[cid]['masked_M'], ensure_ascii=False)[1:-1]}`")
        L.append("")
    (HERE / "results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:60]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
