"""Are golden_en, lang_tr and lang_ru ready for A7 (EN/TR/RU <= 1 point below
checkpoint 1)? Counts how far their gold is from today's labelling rules.

    python reports/translation_test/a7_readiness.py <merged_relabeled_swept_dated/test.docs.jsonl> <golden_en.jsonl>

lang_tr / lang_ru are sampled exactly as eval/scoreboard.py does (the split's
documents of that language, shuffled with seed 13, the first 1,000). Two
measures per set:
  * DATE span shapes: a year word inside (`года`/`г.`, `yılı`), a weekday, an
    English ordinal or `the ... of`;
  * what the v4 cleaning would change in the gold (`v4_clean`, read
    only): R2 (no DATE/TIME inside a date+time or line stamp, D-17/D-51f) and
    R3 (no year suffix inside a DATE). v4_clean's name rules use Azerbaijani
    word lists, so only R2 and R3 are counted for these languages.
Counts and shapes only.
"""
from __future__ import annotations

import collections
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.locales import LOCALES  # noqa: E402
from piigen.v4_clean import clean_doc_detail  # noqa: E402

YEAR_WORD = {"ru": r"\d{4}\s*(?:г\.|года|году|год)\b", "tr": r"\d{4}\s*(?:yılı|yılında|yıl)\b",
             "en": r"\d{4}\s*(?:AD|CE)\b"}


def sample(path: str, lang: str, n: int = 1000) -> list[dict]:
    docs = [json.loads(line) for line in open(path, encoding="utf-8")]
    docs = [d for d in docs if d.get("lang", lang) == lang]
    random.Random(13).shuffle(docs)
    return sorted(docs[:n], key=lambda d: d["id"])


def measure(name: str, lang: str, docs: list[dict]) -> dict:
    wd = [w.lower() for w in LOCALES[lang].weekdays]
    c = collections.Counter()
    dates = 0
    for d in docs:
        t = d["text"]
        for e in d["entities"]:
            if e["label"] != "DATE":
                continue
            dates += 1
            v = t[e["start"]:e["end"]]
            if re.search(YEAR_WORD.get(lang, r"$^"), v, re.I):
                c["DATE: year word inside"] += 1
            if any(w in v.lower() for w in wd):
                c["DATE: weekday inside"] += 1
            if lang == "en" and re.search(r"\d(?:st|nd|rd|th)\b", v):
                c["DATE: ordinal day"] += 1
            if lang == "en" and v.lower().startswith("the "):
                c["DATE: starts with `the`"] += 1
        res = clean_doc_detail({"id": d["id"], "text": t, "_doc_type": d.get("_doc_type"),
                                "entities": d["entities"], "_decoys": d.get("_decoys") or []})
        changed = False
        for ch in res.changes:
            if ch.rule in ("R2", "R3"):
                c[f"{ch.rule} {ch.action} {ch.label}"] += 1
                changed = True
        c["documents a cleaning rule would change"] += changed
    labels = collections.Counter(e["label"] for d in docs for e in d["entities"])
    return {"set": name, "documents": len(docs), "entities": sum(labels.values()), "DATE": dates,
            "TIME": labels["TIME"], "findings": dict(c)}


def main() -> int:
    test, golden_en = sys.argv[1], sys.argv[2]
    out = [measure("golden_en", "en", [json.loads(l) for l in open(golden_en, encoding="utf-8")])]
    for lang in ("tr", "ru"):
        out.append(measure(f"lang_{lang}", lang, sample(test, lang)))
    for m in out:
        print(f"== {m['set']}: {m['documents']} documents, {m['entities']} entities "
              f"({m['DATE']} DATE, {m['TIME']} TIME)")
        for k, v in sorted(m["findings"].items()):
            print(f"     {v:5d}  {k}")
    Path(__file__).with_name("a7_readiness.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                                             encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
