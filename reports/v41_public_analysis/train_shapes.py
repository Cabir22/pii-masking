"""v4.1 analysis: count value shapes in the training data, v3
against v4, by source (targeted / LLM b1-b6 / old corpus).

    python reports/v41_public_analysis/train_shapes.py v3=<runb-az-v3 train.docs.jsonl> \
        v4=<runb-az-v4 train.docs.jsonl> [--out reports/v41_public_analysis/out/train_shapes]

Three kinds of counts, all shapes and numbers only (no values leave this script):
  1. labelled values per label and shape (read_errors.SHAPE, or digits -> 9);
  2. declared look-alikes (`_decoys`) per label they resemble and kind;
  3. regex shapes (SHAPES below) anywhere in the text, split into: labelled
     with which label, inside a declared look-alike, or neither (unlabelled,
     undeclared).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from read_errors import SHAPE, generic_shape  # noqa: E402

LABELS = ("IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS", "EMAIL", "TIME", "DATE", "ZIPCODE",
          "CARD_SECURITY_CODE", "AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER")
H = r"[0-9A-Fa-f]"
SHAPES = {
    # colon groups
    "hh:mm": r"(?<![\w:])\d{1,2}:\d{2}(?![\w:])",
    "hh:mm:ss": r"(?<![\w:])\d{1,2}:\d{2}:\d{2}(?![\w:])",
    "[hh:mm(:ss)] line stamp": r"(?m)^\[\d{1,2}:\d{2}(?::\d{2})?\]",
    # hex groups with `::` or at least 3 colons (an hh:mm:ss stamp has 2)
    "IPv6-like (:: or 3+ colons)": rf"(?<![\w:])(?=[0-9A-Fa-f:]*(?:::|:[0-9A-Fa-f]*:[0-9A-Fa-f]*:)){H}{{0,4}}(?::{H}{{0,4}}){{2,7}}(?![\w:])",
    "IPv6-like, digit-only groups": r"(?<![\w:])(?=[\d:]*(?:::|:\d*:\d*:))\d{0,4}(?::\d{0,4}){2,7}(?![\w:])",
    "::ffff: + IPv4": r"(?i)(?<![\w:])::ffff:\d{1,3}(?:\.\d{1,3}){3}(?![\w.])",
    "MAC colon 6 pairs": rf"(?<![\w:]){H}{{2}}(?::{H}{{2}}){{5}}(?![\w:])",
    "MAC dash 6 pairs": rf"(?<![\w-]){H}{{2}}(?:-{H}{{2}}){{5}}(?![\w-])",
    "dash pairs 3-4 (99-99-99)": rf"(?<![\w-]){H}{{2}}(?:-{H}{{2}}){{2,3}}(?![\w-])",
    # dotted numbers
    "dotted 4 parts, all <=255": r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\w.]|\.\d)",
    "dotted 4 parts, one-digit octets >=2": r"(?<![\w.])(?=(?:\d\.){2})\d{1,3}(?:\.\d{1,3}){3}(?![\w.]|\.\d)",
    "dotted 3 parts (99.99.99)": r"(?<![\w.])\d{1,3}\.\d{1,3}\.\d{1,3}(?![\w.]|\.\d)",
    "dotted 5 parts": r"(?<![\w.])\d{1,3}(?:\.\d{1,3}){4}(?![\w.]|\.\d)",
    # email-like
    "email-like a@b.c": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",
    "email-like, local part with dot": r"[\w+-]+\.[\w.+-]*@[\w-]+(?:\.[\w-]+)+",
    "email-like, local part with hyphen": r"[\w.+]*-[\w.+-]*@[\w-]+(?:\.[\w-]+)+",
    # ID card / licence
    "2 letters + 6 digits": r"(?<![\w])[A-Z]{2}\d{6}(?![\w])",
    "2 letters + 7 digits": r"(?<![\w])[A-Z]{2}\d{7}(?![\w])",
    "AZE + 8 digits": r"(?<![\w])AZE\d{8}(?![\w])",
    # C4 families
    "3 digits": r"(?<![\w.,:/-])\d{3}(?![\w.,:/-])",
    "4 digits": r"(?<![\w.,:/-])\d{4}(?![\w.,:/-])",
    "AZ + 4 digits": r"(?<![\w])AZ ?\d{4}(?![\w])",
    "dd.mm.yyyy": r"(?<![\w.])\d{2}\.\d{2}\.\d{4}(?![\w.])",
    "5 digits": r"(?<![\w.,:/-])\d{5}(?![\w.,:/-])",
    "AZ + 1-3 digits": r"(?<![\w])AZ ?\d{1,3}(?![\w])",
    "AZ + 5 digits": r"(?<![\w])AZ ?\d{5}(?![\w])",
    "hh:mm, hour > 23 or minute > 59": r"(?<![\w:])(?:(?:2[4-9]|[3-9]\d):\d{2}|\d{1,2}:[6-9]\d)(?![\w:])",
    "dd.mm.yyyy, month > 12": r"(?<![\w.])\d{2}\.(?:1[3-9]|[2-9]\d)\.\d{4}(?![\w.])",
    "30/31.02.yyyy": r"(?<![\w.])3[01]\.02\.\d{4}(?![\w.])",
}
# a shape counted again when one of these words is in the 30 characters before it
NEAR = {
    "3 digits": r"(?i)cvv|cvc|təhlükəsizlik kodu",
    "4 digits": r"(?i)cvv|cvc|indeks|poçt",
    "5 digits": r"(?i)cvv|cvc|indeks|poçt",
    "AZ + 4 digits": r"(?i)indeks|poçt",
    "AZ + 1-3 digits": r"(?i)indeks|poçt",
    "AZ + 5 digits": r"(?i)indeks|poçt",
    "hh:mm": r"(?i)saat|vaxt",
    "hh:mm, hour > 23 or minute > 59": r"(?i)saat|vaxt",
    "dd.mm.yyyy": r"(?i)tarix",
    "dd.mm.yyyy, month > 12": r"(?i)tarix",
    "30/31.02.yyyy": r"(?i)tarix",
    "2 letters + 6 digits": r"(?i)sürücü|şəxsiyyət|vəsiqə",
    "2 letters + 7 digits": r"(?i)sürücü|şəxsiyyət|vəsiqə",
}
NEAR_RE = {k: re.compile(v) for k, v in NEAR.items()}
SHAPES_RE = {k: re.compile(v) for k, v in SHAPES.items()}


def source(d: dict) -> str:
    if d.get("_source") == "targeted":
        return "targeted"
    if d.get("_old"):
        return "old corpus"
    m = re.match(r"sprint1_llm_(b\d)", d["id"])
    return f"LLM {m.group(1)}" if m else "other"


def bump(c, *keys):
    c[keys] += 1


def analyse(path: str) -> dict:
    lab_shape = collections.Counter()   # (label, shape, source)
    lab_n = collections.Counter()       # (label, source)
    dec = collections.Counter()         # (resembles, kind, source)
    rx = collections.Counter()          # (shape, status, source)
    docs = collections.Counter()
    for line in open(path, encoding="utf-8"):
        d = json.loads(line)
        src = source(d)
        docs[src] += 1
        text = d["text"]
        ents = d["entities"]
        for e in ents:
            if e["label"] in LABELS:
                v = text[e["start"]:e["end"]]
                bump(lab_n, e["label"], src)
                for s in SHAPE.get(e["label"], generic_shape)(v):
                    bump(lab_shape, e["label"], s, src)
        decs = d.get("_decoys") or []
        for x in decs:
            if x.get("resembles") in LABELS:
                bump(dec, x["resembles"], x.get("kind") or "?", src)
        for name, r in SHAPES_RE.items():
            for m in r.finditer(text):
                s, t = m.span()
                lab = next((e["label"] for e in ents if e["start"] < t and e["end"] > s), None)
                if lab:
                    status = "labelled " + lab
                elif any(x["start"] < t and x["end"] > s for x in decs):
                    status = "declared look-alike"
                else:
                    status = "unlabelled"
                bump(rx, name, status, src)
                if name in NEAR_RE:
                    kw = NEAR_RE[name].search(text, max(0, s - 30), s)
                    if kw:
                        bump(rx, f"{name} after `{kw.group().lower()}`", status, src)
    def js(c):
        return [[*k, n] for k, n in sorted(c.items())]
    return {"documents": dict(docs), "labelled": js(lab_n), "labelled_shapes": js(lab_shape),
            "decoys": js(dec), "regex": js(rx)}


def pivot(rows, keylen, names, srcs):
    """rows per build -> {key tuple: {build: {source: n}}}"""
    out = collections.defaultdict(lambda: {b: collections.Counter() for b in names})
    for b in names:
        for r in rows[b]:
            out[tuple(r[:keylen])][b][r[keylen]] += r[keylen + 1]
    return out


def md(res: dict) -> str:
    names = list(res)
    srcs = ["targeted", "LLM b1", "LLM b2", "LLM b3", "LLM b4", "LLM b5", "LLM b6", "old corpus"]
    grp = {"targeted": "targeted", "old corpus": "old"}

    def g(s):
        return grp.get(s, "LLM")
    cols = ["targeted", "LLM", "old"]
    hdr = "| | " + " | ".join(f"{b} {c}" for c in cols + ["all"] for b in names) + " |"
    sep = "|---|" + "---|" * (len(names) * (len(cols) + 1))

    def row(key, per):
        cells = []
        for c in cols + ["all"]:
            for b in names:
                cells.append(sum(n for s, n in per[b].items() if c == "all" or g(s) == c))
        return f"| {key} | " + " | ".join(f"{x:,}" for x in cells) + " |"

    L = ["# Shapes in the training data: " + " against ".join(names), "",
         "Sources: targeted builder; LLM batches b1-b6; old corpus (`_old`).", "",
         "| documents | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    for s in srcs:
        L.append(f"| {s} | " + " | ".join(f"{res[b]['documents'].get(s, 0):,}" for b in names) + " |")
    L += ["", "## 1. Labelled values", "", hdr, sep]
    p = pivot({b: res[b]["labelled"] for b in names}, 1, names, srcs)
    for k in sorted(p):
        L.append(row(k[0], p[k]))
    L += ["", "### By shape", "", hdr, sep]
    p = pivot({b: res[b]["labelled_shapes"] for b in names}, 2, names, srcs)
    for k in sorted(p, key=lambda k: (k[0], -sum(sum(v.values()) for v in p[k].values()))):
        if sum(sum(v.values()) for v in p[k].values()) >= 5:
            L.append(row(f"{k[0]} · `{k[1]}`", p[k]))
    L += ["", "## 2. Declared look-alikes (`_decoys`)", "", hdr, sep]
    p = pivot({b: res[b]["decoys"] for b in names}, 2, names, srcs)
    for k in sorted(p):
        L.append(row(f"{k[0]} · {k[1]}", p[k]))
    L += ["", "## 3. Regex shapes anywhere in the text", "", hdr, sep]
    p = pivot({b: res[b]["regex"] for b in names}, 2, names, srcs)
    for k in sorted(p, key=lambda k: (list(SHAPES).index(k[0].split(' after `')[0]), k[0], -sum(sum(v.values()) for v in p[k].values()))):
        if sum(sum(v.values()) for v in p[k].values()) >= 3:
            L.append(row(f"{k[0]} · {k[1]}", p[k]))
    return "\n".join(L) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+", help="name=train.docs.jsonl, oldest first")
    ap.add_argument("--out", default=str(Path(__file__).parent / "out" / "train_shapes"))
    a = ap.parse_args()
    res = {}
    for b in a.builds:
        name, path = b.split("=", 1)
        res[name] = analyse(path)
        print(name, res[name]["documents"], flush=True)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".md").write_text(md(res), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
