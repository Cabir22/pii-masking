"""v4.1 step 1 (17 Oct): did values in the middle of a sentence
lose practice when `prose` went from 3% to 1.85% (v4.1 A5, PR #90)?

    python reports/v41_prose_check/count_midsentence.py v3=<file> v4=<file> v4.1=<file> [--md out.md] [--json out.json]

Each file is a 25,000-document targeted build (`-n 25000 --seed 20261001`)
at that version's commit. A value is "mid-sentence" when it sits in running
text -- not in a container format (CSV, JSON, log, ...), not in a
`Label: value` line, not alone on a line -- with a word right before it
(after a space) and more text after it on the same line. Counts only.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

WORD_BEFORE = re.compile(r"[^\W\d_][\w-]*[ \t]+$")


def where(text: str, s: int, e: int, fmt: str | None) -> str:
    if fmt:
        return "container"
    ls = text.rfind("\n", 0, s) + 1
    le = text.find("\n", e)
    le = len(text) if le < 0 else le
    before, after = text[ls:s], text[e:le]
    if re.fullmatch(r"\s*[\w ./()-]{1,40}:\s*", before):
        return "label: value line"
    if not before.strip() and not after.strip(" .,;"):
        return "alone on a line"
    if WORD_BEFORE.search(before) and re.search(r"[^\W_]", after):
        return "mid-sentence"
    return "other prose"


def analyse(path: str) -> dict:
    mid = collections.Counter()
    mid_family = collections.defaultdict(collections.Counter)
    alls = collections.Counter()
    docs_family = collections.Counter()
    n = 0
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        n += 1
        spec = r.get("_spec") or {}
        fam, fmt = spec.get("family", "?"), spec.get("format")
        docs_family[fam] += 1
        for ent in r["entities"]:
            lab = ent["label"]
            alls[lab] += 1
            if where(r["text"], ent["start"], ent["end"], fmt) == "mid-sentence":
                mid[lab] += 1
                mid_family[lab][fam] += 1
    return {"documents": n, "families": dict(docs_family), "all": dict(alls), "mid": dict(mid),
            "mid_family": {k: dict(v) for k, v in mid_family.items()}}


def md(res: dict) -> str:
    names = list(res)
    labels = sorted({lab for n in names for lab in res[n]["all"]},
                    key=lambda lab: -res[names[0]]["mid"].get(lab, 0))
    L = ["# Values in the middle of a sentence, per 25,000 targeted documents", ""]
    L += ["| Family share | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    L.append("| prose | " + " | ".join(f"{res[n]['families'].get('prose', 0) / res[n]['documents']:.2%}" for n in names) + " |")
    L += ["", "| Label | " + " | ".join(f"{n} mid-sentence" for n in names) + f" | {names[-1]} vs {names[-2]} | "
          + " | ".join(f"{n} all" for n in names) + " |",
          "|---|" + "---|" * (2 * len(names) + 1)]
    for lab in labels:
        m = [res[n]["mid"].get(lab, 0) for n in names]
        a = [res[n]["all"].get(lab, 0) for n in names]
        ch = f"{(m[-1] - m[-2]) / m[-2]:+.0%}" if m[-2] else "–"
        L.append(f"| {lab} | " + " | ".join(f"{x:,}" for x in m) + f" | {ch} | " + " | ".join(f"{x:,}" for x in a) + " |")
    L += ["", "## Which families write mid-sentence values (last build)", "",
          "| Label | top families |", "|---|---|"]
    last = res[names[-1]]["mid_family"]
    for lab in labels:
        top = sorted(last.get(lab, {}).items(), key=lambda kv: -kv[1])[:4]
        L.append(f"| {lab} | " + ", ".join(f"{f} {c}" for f, c in top) + " |")
    return "\n".join(L) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+", help="name=path.jsonl, oldest first")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    res = {b.split("=", 1)[0]: analyse(b.split("=", 1)[1]) for b in a.builds}
    text = md(res)
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8", newline="\n")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
