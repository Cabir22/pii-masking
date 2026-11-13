"""Relabel A7's gold sets to the current conventions (D-54c).

WHY
---
A7 compares a multilingual candidate with checkpoint 1 on `golden_en`, `lang_tr`
and `lang_ru`. Their gold predates three conventions the training data now
follows, so a model that learned them would be scored against old labels:

  T  no TIME (or DATE) inside a date+time stamp or on a chat/log line stamp
     (D-17, D-51f): exactly `piigen.v4_clean`'s rule R2, reused as it is;
  Y  the year word outside DATE (D-51i; D-54c names Russian `года`/`г.`):
     `21 февраля 1956 года` -> `21 февраля 1956`; also `году`/`год`, and the
     Turkish `yılı`/`yılında`/`yıl` after a 4-digit year;
  W  a weekday outside DATE, in every language (D-54d): `Pazartesi, 21 Şubat
     1956` -> `21 Şubat 1956`, `21 февраля, понедельник` -> `21 февраля`.
  I  an inflected name labelled whole, apostrophe ending included (D-56d, like
     D-9): Turkish `⟦Gence⟧'nin` -> `⟦Gence'nin⟧`, for GIVENNAME, SURNAME, CITY
     and STREET (Russian endings are fused into the word, already inside).

WHAT CHANGES
------------
Only entity offsets (Y, W: the DATE span is trimmed; I: a name span is extended) and, for T, a removed
label that is declared in `_decoys` as a TIMESTAMP (as v4_clean does). Text is
never edited; a record with no change is written back byte for byte. A trim
that would leave no digit in the DATE is not made, and is counted. Every
changed record gets `_a7_relabel`: the rule letters that changed it.

`golden_en` is relabelled whole. `lang_tr` / `lang_ru` are drawn by the
scoreboard from `merged_relabeled_swept_dated/test.docs.jsonl` (its Turkish and
Russian documents, seed 13), so every Turkish and Russian document of that file
is relabelled; its Azerbaijani and English documents are left untouched.

Deterministic: same input, same output.

Run (report only, then write):
  python scripts/relabel_a7_gold.py --golden-en data/golden/golden_en.jsonl \\
      --test data/processed/merged_relabeled_swept_dated/test.docs.jsonl
  python scripts/relabel_a7_gold.py ... --out-dir /tmp/a7 --report reports/a7_relabel/report.json
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.v4_clean import Change, _Work, lexicon, rule_r2  # noqa: E402

LANGS = ("tr", "ru")

# --- Y: the year word after a 4-digit year, at the end of a DATE ----------------------------
YEAR_WORD = {
    "ru": re.compile(r"(?<=\d{4})\s*(?:г\.|гг\.|года|году|год)$", re.I),
    "tr": re.compile(r"(?<=\d{4})\s*(?:yılı|yılında|yıl)$", re.I),
}

# --- W: a weekday at the start or the end of a DATE -----------------------------------------
_WD = {
    "en": r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)\.?",
    "tr": r"(?:pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar)(?:\s+günü)?",
    "ru": r"(?:понедельник|вторник|сред[аеуы]|четверг|пятниц[аеуы]|суббот[аеуы]|воскресень[еяю])",
}
WD_LEAD = {k: re.compile(rf"^(?:{v})(?:\s*,\s*|\s+)(?=\S)", re.I) for k, v in _WD.items()}
WD_TAIL = {k: re.compile(rf"(?<=\S)(?:\s*,\s*|\s+)(?:\(\s*)?(?:{v})(?:\s*\))?$", re.I) for k, v in _WD.items()}


def _trim(w: _Work, ent: dict, s: int, e: int, rule: str, why: str, skipped: collections.Counter) -> None:
    head = w.text[s:e]
    if not any(ch.isdigit() for ch in head):
        skipped[f"{rule}: would leave no digit"] += 1
        return
    w.changes.append(Change(rule, "trim", "DATE", ent["start"], ent["end"], ent["text"], f"{why} -> {head!r}"))
    ent["start"], ent["end"], ent["text"] = s, e, head


def rule_year_word(w: _Work, lang: str, skipped: collections.Counter) -> None:
    rx = YEAR_WORD.get(lang)
    if rx is None:
        return
    for ent in [x for x in w.ents if x["label"] == "DATE"]:
        m = rx.search(ent["text"])
        if m:
            _trim(w, ent, ent["start"], ent["start"] + m.start(), "Y", "year word out", skipped)


def rule_weekday(w: _Work, lang: str, skipped: collections.Counter) -> None:
    for ent in [x for x in w.ents if x["label"] == "DATE"]:
        m = WD_LEAD[lang].match(ent["text"])
        if m:
            _trim(w, ent, ent["start"] + m.end(), ent["end"], "W", "leading weekday out", skipped)
        m = WD_TAIL[lang].search(ent["text"])
        if m:
            _trim(w, ent, ent["start"], ent["start"] + m.start(), "W", "trailing weekday out", skipped)


# --- I: an inflected name labelled whole, apostrophe ending included (D-56d, like D-9) -------
NAME_LABELS = ("GIVENNAME", "SURNAME", "CITY", "STREET")
APOSTROPHE_ENDING = re.compile(r"['’][^\W\d_]+")


def rule_inflected(w: _Work, lang: str) -> None:
    if lang != "tr":        # Russian endings are fused into the word, which the gold already labels whole
        return
    for ent in [x for x in w.ents if x["label"] in NAME_LABELS]:
        m = APOSTROPHE_ENDING.match(w.text, ent["end"])
        if not m:
            continue
        if any(x is not ent and x["start"] < m.end() and ent["end"] < x["end"] for x in w.ents):
            continue
        w.changes.append(Change("I", "extend", ent["label"], ent["start"], ent["end"], ent["text"],
                                f"ending in -> {w.text[ent['start']:m.end()]!r}"))
        ent["end"], ent["text"] = m.end(), w.text[ent["start"]:m.end()]


def relabel(doc: dict, lang: str, lex, skipped: collections.Counter) -> tuple[dict, list[Change]]:
    w = _Work(doc)
    rule_r2(w, lex)
    for c in w.changes:
        c.rule = "T"
    rule_weekday(w, lang, skipped)      # first: `11 декабря 1960 г., воскресенье` -> `… 1960 г.` -> `… 1960`
    rule_year_word(w, lang, skipped)
    rule_inflected(w, lang)
    if not w.changes:
        return doc, []
    out = dict(doc)
    keep = set(doc["entities"][0]) if doc.get("entities") else {"start", "end", "label"}
    out["entities"] = sorted(({k: v for k, v in e.items() if k in keep or k in ("start", "end", "label")}
                              for e in w.ents), key=lambda e: (e["start"], e["end"]))
    for e in out["entities"]:
        if "text" in keep:
            e["text"] = doc["text"][e["start"]:e["end"]]
    if w.decoys or doc.get("_decoys"):
        out["_decoys"] = w.decoys
    out["_a7_relabel"] = sorted(set(doc.get("_a7_relabel", [])) | {c.rule for c in w.changes})
    return out, w.changes


def run_file(path: Path, langs: tuple[str, ...] | None, fixed_lang: str | None, lex, out: Path | None) -> dict:
    stats = {"documents": 0, "relabelled_documents": 0, "changed": 0, "by_lang": {}}
    changes, skipped = collections.Counter(), collections.Counter()
    lines_out = []
    for line in path.read_text(encoding="utf-8").splitlines(keepends=True):
        doc = json.loads(line)
        lang = fixed_lang or doc.get("lang")
        if langs is not None and lang not in langs:
            lines_out.append(line)
            continue
        stats["documents"] += 1
        stats["by_lang"][lang] = stats["by_lang"].get(lang, 0) + 1
        new, ch = relabel(doc, lang, lex, skipped)
        if ch:
            stats["changed"] += 1
            for c in ch:
                changes[f"{lang} {c.rule} {c.action} {c.label}" + (f" ({c.note.split(' ->')[0]})" if c.rule in "WY" else "")] += 1
            lines_out.append(json.dumps(new, ensure_ascii=False) + "\n")
        else:
            lines_out.append(line)
    stats["relabelled_documents"] = stats.pop("changed")
    stats["changes"] = dict(sorted(changes.items()))
    stats["not_made"] = dict(sorted(skipped.items()))
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("".join(lines_out), encoding="utf-8")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--golden-en", type=Path, required=True)
    ap.add_argument("--test", type=Path, required=True, help="merged_relabeled_swept_dated/test.docs.jsonl")
    ap.add_argument("--out-dir", type=Path, help="write golden_en.jsonl and test.docs.jsonl here")
    ap.add_argument("--report", type=Path, help="write the counts as JSON")
    a = ap.parse_args()
    lex = lexicon()
    rep = {
        "golden_en": run_file(a.golden_en, None, "en", lex, a.out_dir / "golden_en.jsonl" if a.out_dir else None),
        "test_tr_ru": run_file(a.test, LANGS, None, lex, a.out_dir / "test.docs.jsonl" if a.out_dir else None),
    }
    for k, v in rep.items():
        print(f"== {k}: {v['documents']} documents {v['by_lang']}, {v['relabelled_documents']} relabelled")
        for c, n in v["changes"].items():
            print(f"     {n:5d}  {c}")
        for c, n in v["not_made"].items():
            print(f"     {n:5d}  not made: {c}")
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
