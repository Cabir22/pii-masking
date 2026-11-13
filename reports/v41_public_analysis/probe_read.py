"""v4.1 analysis: C3 and C4 probe items, v3 against v4 (track R).

  C3: every licence_vs_id and contrast_licence_id item with the label each model gives each
      value (ID card / licence / missed).
  C4: every look-alike in the decoy families that either model masks with the
      label it resembles: its shape, the word before it, policy or not.

    python reports/v41_public_analysis/probe_read.py [--families decoy_cvv,decoy_time,...] \
        [--out reports/v41_public_analysis/out/probes.md]

The probes are public (task sheet, rule 3): values are printed.
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

M = R.M
SHORT = {"AZ_ID_CARD_NUMBER": "ID card", "AZ_DRIVER_LICENSE_NUMBER": "licence"}
FAMILIES = ["decoy_cvv", "decoy_time", "decoy_age", "decoy_date", "decoy_zip", "decoy_fin",
            "decoy_voen_passport_id", "decoy_ipv4", "decoy_ipv6_mac", "decoy_card_iccid_iban",
            "decoy_names_as_org"]


def label_at(preds: list[dict], s: int, e: int) -> str:
    hit = [p for p in preds if p["start"] < e and p["end"] > s]
    if not hit:
        return "missed"
    exact = [p for p in hit if p["start"] == s and p["end"] == e]
    p = (exact or hit)[0]
    return SHORT.get(p["label"], p["label"]) + ("" if exact else " (partial)")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--families", default=",".join(FAMILIES))
    ap.add_argument("--track", default="R")
    ap.add_argument("--out", default=str(R.OUT / "probes.md"))
    a = ap.parse_args()
    O, N = R.OLD, R.NEW
    docs = R.load_docs("probes")
    preds = {m: R.load_preds(mid, sha, "probes", a.track, R.SB.DEFAULT_CACHE) for m, (mid, sha) in R.MODELS.items()}
    L = [f"# Probe items, {O} against {N} (track {a.track})", "", "## C3: licence_vs_id and contrast_licence_id", "",
         f"| id | role | text | gold | {O} | {N} |", "|---|---|---|---|---|---|"]
    c3 = collections.Counter()
    for d in docs:
        if not d["id"].startswith(("licence_vs_id", "contrast_licence_id")):
            continue
        for g in d["gold"]:
            v3, v4 = (label_at(preds[m].get(d["id"], []), g["start"], g["end"]) for m in (O, N))
            gl = SHORT[g["label"]]
            c3[(d["id"].rsplit("_", 1)[0], gl, v3, v4)] += 1
            mark = " **←**" if v4 != gl else ""
            L.append(f"| {d['id']} | {d['meta'].get('role', '')} | {d['text']} | "
                     f"`{d['text'][g['start']:g['end']]}` {gl} | {v3} | {v4}{mark} |")
        for x in d["decoys"]:
            v3, v4 = (label_at(preds[m].get(d["id"], []), x["start"], x["end"]) for m in (O, N))
            if "missed" not in (v3, v4) or v3 != v4:
                L.append(f"| {d['id']} | decoy | {d['text']} | `{d['text'][x['start']:x['end']]}` none | {v3} | {v4} |")
    L += ["", f"| family | gold | {O} | {N} | n |", "|---|---|---|---|---|"]
    L += [f"| {f} | {g} | {v3} | {v4} | {n} |" for (f, g, v3, v4), n in sorted(c3.items())]

    fams = a.families.split(",")
    L += ["", "## C4: look-alikes masked with the label they resemble", "",
          f"| family | look-alikes (non-policy) | {O} triggered | {N} triggered |", "|---|---|---|---|"]
    rows = []
    for f in fams:
        n = t3 = t4 = 0
        for d in docs:
            if d["meta"].get("family") != f and not d["id"].startswith(f):
                continue
            for x in d["decoys"]:
                hit = {m: any(p["label"] == x["resembles"] and M._overlaps(p, x) for p in preds[m].get(d["id"], []))
                       for m in preds}
                if not x.get("policy"):
                    n += 1
                    t3 += hit[O]
                    t4 += hit[N]
                if hit[O] or hit[N]:
                    t = d["text"]
                    prev = re.findall(r"\S+", t[max(0, x["start"] - 40):x["start"]])
                    rows.append((f, d["id"], t, t[x["start"]:x["end"]], x.get("kind"), x.get("policy"),
                                 " ".join(prev[-2:]), hit[O], hit[N]))
        L.append(f"| {f} | {n} | {t3} | {t4} |")
    L += ["", f"| family | id | text | look-alike | kind | policy | words before | {O} | {N} |",
          "|---|---|---|---|---|---|---|---|---|"]
    for f, i, t, v, k, pol, pw, h3, h4 in rows:
        L.append(f"| {f} | {i} | {t} | `{v}` | {k} | {'yes' if pol else ''} | {pw} | "
                 f"{'masked' if h3 else ''} | {'masked' if h4 else ''} |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
