"""models.json -> data.json: the numbers the progress report shows, from the score reports.

    python reports/progress_report/extract.py

For each model in models.json:
  bench  a scoreboard benchmark report; the policy items are left out when the report has
         them apart (`excl_policy`, as rule B1 counts), so every model is judged the same way.
         Score every model with the same code (cached predictions make a re-score quick).
  rules  a release_check.json, or "historical" for rules_history.json (checkpoint 1 and
         Run B, judged on 14 Oct).
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RULE_IDS = ("A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "C1", "C2", "C3", "C4", "C12", "C13", "E3")


def bench(path):
    d = json.load(open(ROOT / path, encoding="utf-8"))
    s = d["sets"][next(iter(d["sets"]))]["tracks"]
    out = {}
    for t in ("R", "M"):
        view = "excl_policy" if "excl_policy" in s[t] else "all"
        ex = s[t][view]["exact"]
        out[t] = {k: ex["micro"][k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")}
        out[t]["view"] = view
        if t == "R":
            out["labels"] = {l: {"f1": v["f1"], "recall": v["recall"], "n": v["tp"] + v["fn"]}
                             for l, v in ex["per_label"].items()}
    return out


def rules(spec, history):
    if spec == "historical":
        return history
    d = json.load(open(ROOT / spec, encoding="utf-8"))
    return {r["id"]: {"status": r["status"], "result": r["result"]} for r in d["rules"] if r["id"] in RULE_IDS}


def main():
    m = json.load(open(HERE / "models.json", encoding="utf-8"))
    hist = json.load(open(HERE / "rules_history.json", encoding="utf-8"))
    data = {"order": m["order"], "models": {}, "bench": {}, "rules": {}}
    for k in m["order"]:
        e = m["models"][k]
        data["models"][k] = {x: e[x] for x in ("name", "id", "train_docs", "new_share", "llm_docs")}
        data["bench"][k] = bench(e["bench"])
        data["rules"][k] = rules(e["rules"], hist.get(k, {}))
        print(f"{k:6} benchmark R F1 {data['bench'][k]['R']['f1'] * 100:.1f} ({data['bench'][k]['R']['view']}), "
              f"{len(data['rules'][k])} rules")
    json.dump(data, open(HERE / "data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", HERE / "data.json")


if __name__ == "__main__":
    main()
