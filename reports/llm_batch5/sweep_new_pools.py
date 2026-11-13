"""Batch 5: are the new pools' values (P2-14 settlements, P2-15 foreign names)
labelled wherever they occur, and do their spans keep the suffix?

    python reports/llm_batch5/sweep_new_pools.py data/raw/sprint1_llm_b5.jsonl --json out.json

Diagnostic, not a gate. Per document:
  1. a settlement name of the 4,414-place pool (not one of the old 97 cities,
     which the invented-PII sweep already covers), capitalised, possibly with a
     case suffix, that no entity and no declared decoy covers;
  2. a foreign given name followed by a capitalised word that is a foreign
     surname (`Mehmet Yılmaz`, `John Smith`), uncovered: the invented-PII sweep
     only knows Azerbaijani-shaped surnames (`-ov`, `-li`, ...);
  3. a lone foreign surname from the pool, uncovered;
  4. a labelled CITY / GIVENNAME / SURNAME span on a new-pool value that stops
     before the end of its word (the suffix left outside the label, D-9).
Each finding says whether the value was planned (`_spec.entities`).
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
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.locales import LOCALES                     # noqa: E402
from piigen.resolver import match_key                  # noqa: E402

AZ = LOCALES["az"]
try:
    from piigen.targeted import homographs_az as H
except ImportError:
    from piigen.targeted import homographs_az_stub as H
COMMON = frozenset(match_key(w) for w in list(AZ.stopwords) + list(H.LONE_WORDS))
WORD = re.compile(r"[^\W\d_]+")
MAX_SUFFIX = 7


def low(s: str) -> str:
    """Azerbaijani lower case: `İ` -> `i`, `I` -> `ı` (str.casefold gives `i̇`)."""
    return s.replace("İ", "i").replace("I", "ı").lower()


OLD_CITIES = {low(c) for c in AZ.cities}
SETTLEMENTS = {low(s): s for s in AZ.settlements if low(s) not in OLD_CITIES}
FOREIGN_GIVEN = {low(n) for n in AZ.foreign_names.given_names()}
FOREIGN_SUR = {low(n) for n in AZ.foreign_names.surname_forms()}


def stem_in(word: str, pool) -> str | None:
    """The pool entry `word` is, or starts with followed by at most MAX_SUFFIX letters."""
    w = low(word)
    for cut in range(len(w), max(2, len(w) - MAX_SUFFIX) - 1, -1):
        if w[:cut] in pool:
            return w[:cut]
    return None


def sweep(rec: dict) -> dict:
    text = rec.get("text") or ""
    ents = rec.get("entities") or []
    covered = [(e["start"], e["end"]) for e in ents] + \
              [(d["start"], d["end"]) for d in rec.get("_decoys") or []
               if isinstance(d.get("start"), int)]
    planned = {match_key(e["value"]) for e in (rec.get("_spec") or {}).get("entities") or []
               if isinstance(e, dict) and e.get("value")}

    def free(s, e):
        return not any(a < e and s < b for a, b in covered)

    out = collections.defaultdict(list)
    words = list(WORD.finditer(text))
    for i, m in enumerate(words):
        w = m.group(0)
        if not w[:1].isupper() or w.isupper() or match_key(w) in COMMON:
            continue
        # 1. settlements: one to three words, the last one may carry a suffix
        for n in (3, 2, 1):
            if i + n > len(words):
                continue
            span = words[i:i + n]
            if any(span[k + 1].start() - span[k].end() != 1 for k in range(n - 1)):
                continue
            head = " ".join(x.group(0) for x in span[:-1])
            last = stem_in(span[-1].group(0), {k.split(" ")[-1] for k in SETTLEMENTS
                                               if k.count(" ") == n - 1}) if n > 1 else None
            key = (low(head) + " " + last) if n > 1 and last else None
            if n == 1:
                key = stem_in(w, SETTLEMENTS)
            if key and key in SETTLEMENTS and free(span[0].start(), span[-1].end()):
                out["settlement"].append({"text": text[span[0].start():span[-1].end()],
                                          "place": SETTLEMENTS[key],
                                          "planned": match_key(SETTLEMENTS[key]) in planned,
                                          "start": span[0].start()})
                break
        # 2-3. foreign names
        g = stem_in(w, FOREIGN_GIVEN)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if g and nxt and nxt.start() - m.end() == 1 and nxt.group(0)[:1].isupper() \
                and stem_in(nxt.group(0), FOREIGN_SUR) and free(m.start(), nxt.end()):
            out["foreign_full_name"].append({"text": text[m.start():nxt.end()],
                                             "planned": match_key(w) in planned
                                             or match_key(nxt.group(0)) in planned,
                                             "start": m.start()})
        elif low(w) in FOREIGN_SUR and len(w) > 3 and free(m.start(), m.end()) \
                and not (i and stem_in(words[i - 1].group(0), FOREIGN_GIVEN)):
            out["foreign_surname"].append({"text": w, "planned": match_key(w) in planned,
                                           "start": m.start()})
    # 4. suffix left outside a label
    for e in ents:
        if e["label"] not in ("CITY", "GIVENNAME", "SURNAME"):
            continue
        val = text[e["start"]:e["end"]]
        pool = SETTLEMENTS if e["label"] == "CITY" else (FOREIGN_GIVEN | FOREIGN_SUR)
        if not stem_in(val.split(" ")[-1] if e["label"] != "CITY" else val, pool) \
                and low(val) not in pool:
            continue
        if e["end"] < len(text) and (text[e["end"]].isalpha()):
            out["suffix_outside"].append({"text": val, "label": e["label"],
                                          "word": text[e["start"]:e["end"] + 8].split()[0],
                                          "start": e["start"]})
    return out


def drop_ordinary_words(path: Path) -> dict:
    """Pool names the batch itself writes as lowercase words (`icarə`, `dəstək`,
    `uğurlu`): a capitalised one is a heading or a sentence start, not a place
    or a person. Also drops all-caps-only noise. Returns the counts removed."""
    lower = collections.Counter()
    for line in path.open(encoding="utf-8"):
        for m in WORD.finditer(json.loads(line).get("text") or ""):
            w = m.group(0)
            if w.islower():
                lower[low(w)] += 1
    by_head = collections.defaultdict(list)
    for w in lower:
        by_head[w[:3]].append(w)

    def ordinary(name: str) -> bool:
        last = name.split(" ")[-1]
        return any(w.startswith(last) and len(w) - len(last) <= MAX_SUFFIX
                   for w in by_head.get(last[:3], ()))

    removed = {}
    for pool_name, pool in (("settlements", SETTLEMENTS), ("given", FOREIGN_GIVEN),
                            ("surnames", FOREIGN_SUR)):
        keys = list(pool)
        gone = [k for k in keys if ordinary(k)]
        for k in gone:
            if isinstance(pool, dict):
                del pool[k]
            else:
                pool.discard(k)
        removed[pool_name] = {"removed": len(gone), "kept": len(pool), "e.g.": gone[:15]}
    return removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("batch", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args()
    removed = drop_ordinary_words(args.batch)
    print("pool names left out as ordinary words:", {k: v["removed"] for k, v in removed.items()})
    docs = collections.Counter()
    finds = collections.Counter()
    planned = collections.Counter()
    ex = collections.defaultdict(list)
    labelled = collections.Counter()
    every = collections.defaultdict(collections.Counter)
    n = 0
    for line in args.batch.open(encoding="utf-8"):
        if not line.strip():
            continue
        rec = json.loads(line)
        n += 1
        text = rec["text"]
        for e in rec.get("entities") or []:
            v = text[e["start"]:e["end"]]
            if e["label"] == "CITY" and stem_in(v, SETTLEMENTS):
                labelled["CITY_new_pool"] += 1
            if e["label"] in ("GIVENNAME", "SURNAME") and stem_in(v.split(" ")[0], FOREIGN_GIVEN | FOREIGN_SUR):
                labelled[e["label"] + "_foreign_pool"] += 1
        for kind, items in sweep(rec).items():
            docs[kind] += 1
            finds[kind] += len(items)
            planned[kind] += sum(1 for it in items if it.get("planned"))
            for it in items:
                every[kind][it.get("place") or it.get("text")] += 1
                if len(ex[kind]) < args.examples:
                    s = it["start"]
                    ex[kind].append({"id": rec["id"], **{k: v for k, v in it.items() if k != "start"},
                                     "context": text[max(0, s - 50):s + 60].replace("\n", " / ")})
    report = {"documents": n, "ordinary_words_left_out": removed,
              "labelled_new_pool_spans": dict(labelled),
              "findings": {k: {"documents": docs[k], "occurrences": finds[k],
                               "planned": planned[k], "values": dict(every[k].most_common()),
                               "examples": ex[k]} for k in docs}}
    print(f"{n:,} documents; labelled new-pool spans: {dict(labelled)}")
    for k in ("settlement", "foreign_full_name", "foreign_surname", "suffix_outside"):
        print(f"{k:<18} docs {docs[k]:>5}  occurrences {finds[k]:>5}  planned {planned[k]:>5}")
        for e in ex[k][:6]:
            print("    ", e["id"], "|", e.get("text"), "|", e["context"])
    if args.json:
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
