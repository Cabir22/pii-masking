"""The TR/RU translation check (D-56c), counted on two translations of
the same source sample: before and after the fixes.

    python reports/translation_test/d56c_check.py <source.jsonl> <before dir> <after dir> [--md out.md]

Each dir holds tr/train.docs.jsonl and ru/train.docs.jsonl (full_run.py's
layout); ru/train.docs.diag.jsonl, if present, gives Russian's declined count.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from translate import morph as M  # noqa: E402

PERSON = ("GIVENNAME", "SURNAME")


def load(p: Path) -> dict:
    if not p.exists():
        return {}
    return {r["source_id"]: r for r in (json.loads(x) for x in open(p, encoding="utf-8"))}


def ru_surname_gender(v: str) -> str | None:
    if re.search(r"(ова|ева|ёва|ина|ына)$", v):
        return "f"
    if re.search(r"(ов|ев|ёв|ин|ын)$", v):
        return "m"
    return None


def count(src: dict, out: dict, lang: str, diag: dict) -> collections.Counter:
    c = collections.Counter()
    for sid, r in out.items():
        s = src[sid]
        st, t = s["text"], r["text"]
        sents = sorted(s["entities"], key=lambda e: e["start"])
        svals = [st[e["start"]:e["end"]] for e in sents]
        facts = [M.source_case(e["label"], v) for e, v in zip(sents, svals)]
        genders = M.person_genders(st, sents, [f[0] for f in facts])
        # (1) a person's surname against the source person's gender: one-gender documents
        known = {g for g, e in zip(genders, sents) if g and e["label"] in PERSON}
        if len(known) == 1:
            g = known.pop()
            for e in r["entities"]:
                if e["label"] == "SURNAME":
                    v = t[e["start"]:e["end"]]
                    og = ru_surname_gender(v) if lang == "ru" else M.surname_gender(v.split("'")[0])
                    if og:
                        c["(1) surnames with a gender, in one-gender documents"] += 1
                        c["(1)   of the source person's gender"] += og == g
        # (2) inflected source spans, and endings in the translation
        c["(2) inflected name/place spans in the source"] += sum(1 for f in facts if f[1])
        if lang == "tr":
            c["(2) TR name/place spans with an ending"] += sum(
                1 for e in r["entities"] if e["label"] in M.INFLECTED_LABELS and "'" in t[e["start"]:e["end"]])
        elif sid in diag:
            c["(2) RU names/places declined"] += diag[sid].get("inflected", 0) or 0
        # (3) the source DATE's year, when the text repeats it
        for e, v in zip(sents, svals):
            y = M.source_year(v) if e["label"] == "DATE" else None
            if y and st.count(str(y)) > 1:
                c["(3) DATEs whose year the source text repeats"] += 1
                c["(3)   the translated DATE has that year"] += any(          # `27.07.18` counts
                    M.source_year(t[x["start"]:x["end"]]) == y for x in r["entities"] if x["label"] == "DATE")
        # (4) patronymics
        if re.search(r"\b(oğlu|qızı)\b", st, re.I):
            c["(4) documents with oğlu/qızı"] += 1
            if lang == "ru":
                c["(4)   with оглы/кызы"] += bool(re.search(r"(оглы|кызы)", t, re.I))
                c["(4)   with сын/дочь"] += bool(re.search(r"\b(сын|сына|дочь|дочери)\b", t, re.I))
        # (5) the combining dot
        c["(5) U+0307"] += t.count("̇")
        # (6) year words after a full date, (7) hyphen endings after a value
        for e in r["entities"]:
            v, rest = t[e["start"]:e["end"]], t[e["end"]:e["end"] + 12]
            if e["label"] == "DATE" and M._full_date(v):
                if (lang == "tr" and M._TR_YEAR_WORD.match(rest)) or \
                        (lang == "ru" and re.match(r"^(-й год| год\b)", rest)):
                    c["(6) year word after a full date"] += 1
            if lang == "tr" and re.match(r"-(?:dir|dır|dur|dür|da|də|de|dan|dən|den|ci|cı|cu|cü)\b", rest):
                c["(7) Azerbaijani hyphen ending after a value"] += 1
        # (8) VÖEN in Russian
        if lang == "ru" and "VÖEN" in st:
            c["(8) documents with VÖEN"] += 1
            c["(8)   ИНН"] += "ИНН" in t
            c["(8)   another form (VÖEN, ВОЕН, ВУИН)"] += bool(re.search(r"VÖEN|VOEN|ВОЕН|ВУИН", t, re.I))
        # (9) Turkish calques
        if lang == "tr":
            c["(9) bilgi taban… / prosedur… / tekniki"] += (len(re.findall(r"\bbilgi taban", t, re.I))
                                                           + len(re.findall(r"\bprosedur", t, re.I))
                                                           + len(re.findall(r"\btekniki\b", t.replace("İ", "i").lower())))
        # (10) masks of a labelled value
        for m in M._MASK.finditer(st):
            d = m.group(1)
            if any(len(re.sub(r"\D", "", v)) > len(d) and re.sub(r"\D", "", v).endswith(d) for v in svals):
                c["(10) masks of a labelled value"] += 1
                ovals = [re.sub(r"\D", "", t[e["start"]:e["end"]]) for e in r["entities"]]
                c["(10)   match the new value"] += any(any(v.endswith(x.group(1)) for v in ovals)
                                                       for x in M._MASK.finditer(t))
    c["documents"] = len(out)
    return c


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--md")
    a = ap.parse_args()
    src = {r["id"]: r for r in (json.loads(x) for x in open(a.source, encoding="utf-8"))}
    rows = []
    res = {}
    for lang in ("tr", "ru"):
        for name, d in (("before", Path(a.before)), ("after", Path(a.after))):
            diag = {}
            dp = d / lang / "train.docs.diag.jsonl"
            if dp.exists():
                for x in open(dp, encoding="utf-8"):
                    j = json.loads(x)
                    diag[j.get("source_id") or j["id"].rsplit("__", 1)[0]] = j.get("_diag", {})
            res[(lang, name)] = count(src, load(d / lang / "train.docs.jsonl"), lang, diag)
    keys = sorted({k for c in res.values() for k in c}, key=lambda k: (k != "documents", k))
    lines = ["| Check | TR before | TR after | RU before | RU after |", "|---|---|---|---|---|"]
    for k in keys:
        vals = [res[(lg, nm)].get(k, "–") if k in res[(lg, nm)] or k == "documents" else "–"
                for lg in ("tr", "ru") for nm in ("before", "after")]
        lines.append(f"| {k} | " + " | ".join(str(v) for v in vals) + " |")
    text = "\n".join(lines) + "\n"
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
