"""v4.1 analysis: the left-context words of the benchmark frames v4
fails in, counted in the training data. For each word, the next token that
holds a digit is classed as labelled (with its label), a declared look-alike
(with its kind) or unlabelled.

    python reports/v41_public_analysis/left_words.py v3=<train.docs.jsonl> v4=<train.docs.jsonl> \
        [--out reports/v41_public_analysis/out/left_words.md]
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

WORDS = {  # benchmark frame -> the left context, as a regex (digit token up to 2 words later)
    "Logda … (IPv4/IPv6 X qeyd olunub)": r"\b[Ll]ogda\b",
    "Server … (IPv6-si / ünvanı X yazılıb)": r"\bServer\b",
    "Təqvimdə X görünür": r"\bTəqvimdə\b",
    "… üzrə ZIP X görünür": r"\bZIP\b",
    "Çatdırılma indeksi X qeyd olunub": r"\b[Çç]atdırılma indeksi\b",
    "IPv6 ünvanı X": r"\bIPv6 ünvanı\b",
    "Mənbə IP X (v4 finds 92%)": r"\bMənbə IP\b",
    "Şəbəkə tarixçəsində X (v4 finds 93-98%)": r"\bŞəbəkə tarixçəsində\b",
}
WRE = {k: re.compile(v + r"((?:\s+\S+){0,2}?)\s+(\S*\d\S*)") for k, v in WORDS.items()}


def analyse(path: str) -> collections.Counter:
    c = collections.Counter()
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        t = d["text"]
        src = "targeted" if source(d) == "targeted" else "LLM" if source(d).startswith("LLM") else "old"
        for k, r in WRE.items():
            for m in r.finditer(t):
                s, e = m.span(2)
                lab = next((x["label"] for x in d["entities"] if x["start"] < e and x["end"] > s), None)
                dec = next((x.get("kind") for x in d.get("_decoys") or [] if x["start"] < e and x["end"] > s), None)
                st = f"labelled {lab}" if lab else f"look-alike {dec}" if dec else "unlabelled"
                c[(k, st, src)] += 1
    return c


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+")
    ap.add_argument("--out", default=str(Path(__file__).parent / "out" / "left_words.md"))
    a = ap.parse_args()
    res = {b.split("=", 1)[0]: analyse(b.split("=", 1)[1]) for b in a.builds}
    names = list(res)
    srcs = ("targeted", "LLM", "old")
    L = ["# Left-context words of v4's failing benchmark frames, in training", "",
         "| frame word | next digit token | " + " | ".join(f"{b} {s}" for b in names for s in srcs) + " |",
         "|---|---|" + "---|" * (len(names) * len(srcs))]
    keys = sorted({k[:2] for r in res.values() for k in r}, key=lambda k: (list(WORDS).index(k[0]), k[1]))
    for k in keys:
        L.append(f"| {k[0]} | {k[1]} | " + " | ".join(str(res[b].get((*k, s), 0)) for b in names for s in srcs) + " |")
    Path(a.out).write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
