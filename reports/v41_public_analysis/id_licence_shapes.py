"""v4.1 analysis, C3: ID-card and licence values in the training
data, v3 against v4 -- prefix, digit count and the document word before them.

    python reports/v41_public_analysis/id_licence_shapes.py v3=<train.docs.jsonl> v4=<train.docs.jsonl> \
        [--out reports/v41_public_analysis/out/id_licence_shapes.md]

Prefixes are the value's letters (two-letter prefixes are a closed set of
codes, not personal data); digits are counted, never printed.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from train_shapes import source  # noqa: E402

LABS = {"AZ_ID_CARD_NUMBER": "ID card", "AZ_DRIVER_LICENSE_NUMBER": "licence"}
WORDS = [("sürücü", r"(?i)sürücü|\bSV\b|vəsiqə(?:si)? \(sürücü"), ("şəxsiyyət", r"(?i)şəxsiyyət|\bŞV\b"),
         ("vəsiqə only", r"(?i)vəsiqə"), ("none", r"")]


def word_before(text: str, s: int) -> str:
    win = text[max(0, s - 40):s]
    for name, rx in WORDS[:-1]:
        if re.search(rx, win):
            return name
    return "none"


def analyse(path: str) -> dict:
    c = collections.Counter()
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        src = "targeted" if source(d) == "targeted" else "other"
        for e in d["entities"]:
            if e["label"] not in LABS:
                continue
            v = d["text"][e["start"]:e["end"]].replace(" ", "")
            m = re.fullmatch(r"([A-ZƏÖÜĞİŞÇ]*)(\d+)", v)
            pref, nd = (m.group(1), len(m.group(2))) if m else ("other", 0)
            lab = LABS[e["label"]]
            c[(lab, "shape", f"{len(pref)} letters + {nd} digits", src)] += 1
            c[(lab, "prefix", pref if len(pref) == 2 else f"{pref[:3]}…" if pref else "-", src)] += 1
            c[(lab, "word before", word_before(d["text"], e["start"]), src)] += 1
    return {"|".join(k): n for k, n in c.items()}


def md(res: dict) -> str:
    names = list(res)
    keys = sorted({tuple(k.split("|")[:3]) for r in res.values() for k in r})
    L = ["# ID cards and licences in the training data: " + " against ".join(names), "",
         "| label | what | value | " + " | ".join(f"{b} targeted | {b} other" for b in names) + " |",
         "|---|---|---|" + "---|" * (2 * len(names))]
    tot = lambda k: sum(res[b].get("|".join((*k, s)), 0) for b in names for s in ("targeted", "other"))
    for k in sorted(keys, key=lambda k: (k[0], k[1], -tot(k))):
        if k[1] == "prefix" and tot(k) < 100:  # the long tail is summarised below
            continue
        L.append(f"| {k[0]} | {k[1]} | {k[2]} | " + " | ".join(
            f"{res[b].get('|'.join((*k, s)), 0):,}" for b in names for s in ("targeted", "other")) + " |")
    for b in names:
        for lab in LABS.values():
            pref = collections.Counter({k.split("|")[2]: n for k, n in res[b].items()
                                        if k.startswith(f"{lab}|prefix|")})
            L.append(f"\n{b} {lab}: {len(pref)} distinct prefixes; top 5 share "
                     f"{sum(n for _, n in pref.most_common(5)) / max(1, sum(pref.values())):.0%}")
    # prefixes used by both labels
    for b in names:
        idp = {k.split("|")[2] for k in res[b] if k.startswith("ID card|prefix|")}
        lic = {k.split("|")[2] for k in res[b] if k.startswith("licence|prefix|")}
        L.append(f"\n{b}: {len(idp & lic)} prefixes appear on both ID cards and licences")
    return "\n".join(L) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).parent / "out" / "id_licence_shapes.md"))
    a = ap.parse_args()
    res = {b.split("=", 1)[0]: analyse(b.split("=", 1)[1]) for b in a.builds}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(md(res), encoding="utf-8", newline="\n")
    print(md(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
