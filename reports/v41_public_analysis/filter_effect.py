"""v4.2 analysis: what track M's validity-2 filter (D-64b) takes away.
Every span of track M without the filter (M0, from unfiltered_m.py) that the
filter drops, with why (impossible TIME / DATE, CVV length, D-2 dummy) and
what it was: a real value (recall lost), a look-alike, or another false alarm,
and whether track R masks it too. Checks first that the filter applied to M0
gives exactly the shipped track M, document by document.

    python reports/v41_public_analysis/filter_effect.py [--model v4.2] [--out .../filter_effect.md]

Reads both prediction caches (scoreboard.py for R and M, unfiltered_m.py for
M0). The benchmark and the probes are public (task sheet, rule 3): values are printed.
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402
import unfiltered_m as U  # noqa: E402

P = U.predict
REAL_FILTER = P._drop_impossible_values  # kept before anything patches it


def reason(label: str, value: str) -> str:
    """Why validity-2 drops this span (the order of _drop_impossible_values)."""
    if not P._value_possible(label, value):
        return {"TIME": "impossible TIME", "DATE": "impossible DATE",
                "CARD_SECURITY_CODE": "CVV not 3-4 digits"}.get(label, "impossible " + label)
    if re.sub(r"[\s-]", "", value) in P.D2_DUMMIES or value.strip() in P.D2_DUMMIES:
        return "D-2 dummy"
    return "kept"


def kind(doc: dict, s: dict) -> str:
    """real value / look-alike: <kind> / other false alarm, for a predicted span s."""
    if any(g["label"] == s["label"] and R.M._overlaps(g, s) for g in doc["gold"]):
        return "real value"
    for x in doc.get("decoys", []):
        if x.get("resembles") == s["label"] and R.M._overlaps(x, s):
            return f"look-alike: {x.get('kind')}" + (" (policy)" if x.get("policy") else "")
    return "other false alarm"


def key(p: dict) -> tuple:
    return p["start"], p["end"], p["label"]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=R.NEW)
    ap.add_argument("--sets", default="probes,benchmark")
    ap.add_argument("--out", default=str(R.OUT / "filter_effect.md"))
    a = ap.parse_args()
    mid, sha = R.ALL_MODELS[a.model]
    L = [f"# {a.model}: what track M's validity-2 filter drops (M0 = track M without it)", ""]
    for set_name in a.sets.split(","):
        docs = R.load_docs(set_name)
        m = R.load_preds(mid, sha, set_name, "M", R.SB.DEFAULT_CACHE)
        m0 = R.load_preds(mid, sha, set_name, "M", U.CACHE)
        r = R.load_preds(mid, sha, set_name, "R", R.SB.DEFAULT_CACHE)
        bad = [d["id"] for d in docs
               if sorted(map(key, REAL_FILTER(m0.get(d["id"], []), d["text"]))) != sorted(map(key, m.get(d["id"], [])))]
        if bad:
            sys.exit(f"{set_name}: filter(M0) != M in {len(bad)} documents, e.g. {bad[:3]}")
        counts = collections.Counter()
        rows = []
        for d in docs:
            kept = set(map(key, m.get(d["id"], [])))
            for s in m0.get(d["id"], []):
                if key(s) in kept:
                    continue
                v = d["text"][s["start"]:s["end"]]
                k = kind(d, s)
                in_r = any(p["label"] == s["label"] and R.M._overlaps(p, s) for p in r.get(d["id"], []))
                counts[(s["label"], reason(s["label"], v), k.split(" (")[0].split(":")[0])] += 1
                prev = re.findall(r"\S+", d["text"][max(0, s["start"] - 40):s["start"]])
                rows.append((d["meta"].get("family", ""), d["id"], s["label"], v, " ".join(prev[-2:]),
                             reason(s["label"], v), k, "yes" if in_r else ""))
        L += [f"## {set_name}: {len(rows)} spans dropped, in {len(docs)} documents (filter(M0) = M in every one)", "",
              "| label | why | what it was | n |", "|---|---|---|---|"]
        L += [f"| {lab} | {why} | {what} | {n} |" for (lab, why, what), n in sorted(counts.items())]
        L += ["", "| family | id | label | value | words before | why | what it was | track R masks it too |",
              "|---|---|---|---|---|---|---|---|"]
        L += [f"| {f} | {i} | {lab} | `{v}` | {pw} | {why} | {k} | {ir} |" for f, i, lab, v, pw, why, k, ir in rows]
        L.append("")
        print(set_name, dict(counts))
    Path(a.out).write_text("\n".join(L), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
