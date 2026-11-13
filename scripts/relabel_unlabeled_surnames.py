"""Label real surnames the generator wrote into text but never annotated.

WHY
---
The LLM writes realistic prose around the entity values it was briefed
with, and sometimes that prose contains a further, unplanned real name --
a signature block, a "Kimdən:" header, a second party to a contract. Those
never entered the planned-value list, so nothing ever swept them into the
gold labels. A full-corpus scan found 2,178 documents (0.52%) carrying at
least one unlabelled real SURNAME, concentrated in exactly the sentence
positions the live model was separately measured to miss.

An unlabelled real name is worse than a missing example: it is a counter-
example. The model is shown a surname in a signature block and taught that
nothing there needs masking, which is a false negative -- the expensive
error for a masking model.

WHAT COUNTS AS A SURNAME HERE
-----------------------------
The vocabulary is derived from the corpus itself: any string the corpus
labels as SURNAME somewhere is a known surname everywhere. No external
pool file, so the sweep is reproducible from the tracked data alone.

Matching is exact and token-bounded. Suffixed surface forms
("Məmmədovların") are deliberately NOT matched: inflected matching would
need morphological analysis to stay precise, and a wrong label is worse
here than a missed one.

WHAT IS DELIBERATELY NOT LABELLED
---------------------------------
* Occurrences already inside any labelled span.
* Occurrences in place context ("Vaqif Abdullayev caddesinde",
  "Narimanov rayonu"). Azerbaijan names streets and whole districts after
  historical figures; that span is a place, not a SURNAME, and guessing
  wrong teaches a wrong label. These are reported for review.
* GIVENNAME is out of scope entirely. Most unlabelled given-name hits are
  ordinary vocabulary -- `Ümid` ("hope") 4,073 times, `Tamam` ("okay")
  3,576 -- and auto-labelling those would inject false positives wholesale.

ORDER OF OPERATIONS
-------------------
Run this BEFORE scripts/regroup_splits.py. Adding SURNAME labels creates
new shared values between documents, which changes the grouping; splitting
first and relabelling second would silently reopen the leak the split
exists to close.

Run:
  python scripts/relabel_unlabeled_surnames.py
  python scripts/relabel_unlabeled_surnames.py --apply \
      --out data/processed/merged_relabeled
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SPLITS = ("train", "val", "test")

# Capitalised word, Latin-AZ/TR or Cyrillic. Same shape the original
# contamination scan used, so the counts stay comparable.
TOKEN_RE = re.compile(r"[A-ZА-ЯЁƏÇĞİIÖŞÜ][a-zа-яёəçğıöşü]{2,}")

# A surname sitting next to one of these is a PLACE named after a person,
# not the person. Azerbaijan names a great deal of its geography after
# historical figures -- "Nərimanov rayonu" is a district of Baku, not a
# man -- and the first draft of this sweep proposed ~894 SURNAME labels on
# Narimanov/Nərimanov almost entirely from that district. Labelling those
# would not merely miss an entity, it would teach the model that a district
# name is a person, producing false positives at inference.
PLACE_CUES = (
    # thoroughfares
    "küçə", "küç.", "kucə", "prospekt", "pr.", "döngə",
    "cadde", "cad.", "sokak", "sok.", "bulvar", "blv.",
    "улица", "ул.", "проспект", "пр.", "переулок", "шоссе",
    "street", "st.", "avenue", "ave.", "road", "rd.",
    # administrative areas
    "rayon", "район", "district", "ilçe", "mahalle", "qəsəbə",
    "kənd", "посёлок", "поселок", "region", "bölgə",
    # named public places and infrastructure
    "metro", "parkı", "park", "meydan", "square", "stansiya",
    "station", "muzey", "museum", "adına", "xiyaban",
)
PLACE_WINDOW = 40
MIN_LEN = 3


def entity_value(text: str, ent: dict) -> str:
    return ent.get("text") or text[ent["start"]:ent["end"]]


def collect_surnames(data_dir: Path) -> set[str]:
    """Every string the corpus labels SURNAME anywhere."""
    known: set[str] = set()
    for split in SPLITS:
        with (data_dir / f"{split}.docs.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                doc = json.loads(line)
                text = doc["text"]
                for ent in doc["entities"]:
                    if ent["label"] == "SURNAME":
                        value = entity_value(text, ent).strip()
                        if len(value) >= MIN_LEN and TOKEN_RE.fullmatch(value):
                            known.add(value)
    return known


# D-51i (v3 label-noise report, pattern 8): the vocabulary is "any string
# labelled SURNAME anywhere", so a common word labelled once (`Şəkərli` as in
# `şəkərli diabet`, `Xeyirli`, `Etibarlı`) was labelled everywhere, and a
# surname inside an institution's name (`Heydər Əliyev Beynəlxalq Hava
# Limanı`, `Nərimanov Liseyi`) became a person. The stoplist and his
# institution check (`piigen.v4_clean`, rule R7) now apply here too.
def surname_stoplist() -> frozenset:
    sys.path.insert(0, str(ROOT / "scripts"))
    from piigen.v4_clean import lexicon
    lex = lexicon()
    return lex.surname_stoplist | lex.surname_shaped_common


def in_institution(text: str, start: int, end: int) -> bool:
    """`Heydər Əliyev Beynəlxalq Hava Limanı`, `Əliyev adına ... Universiteti`."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from piigen.v4_clean import _INSTITUTION_AFTER_NAME, _named_after
    return bool(_INSTITUTION_AFTER_NAME.match(text, end)) or _named_after(text, end) is not None


def in_place_context(text: str, start: int, end: int) -> bool:
    window = text[max(0, start - PLACE_WINDOW):
                  min(len(text), end + PLACE_WINDOW)].lower()
    return any(cue in window for cue in PLACE_CUES)


def find_additions(text: str, entities: list[dict],
                   known: set[str]) -> tuple[list[dict], list[str]]:
    """New SURNAME spans to add, plus place-context occurrences skipped."""
    covered = [(e["start"], e["end"]) for e in entities]

    def is_covered(s: int, e: int) -> bool:
        return any(a < e and s < b for a, b in covered)

    additions: list[dict] = []
    skipped: list[str] = []
    stop = surname_stoplist()
    sys.path.insert(0, str(ROOT / "scripts"))
    from piigen.resolver import match_key
    for match in TOKEN_RE.finditer(text):
        word = match.group(0)
        if word not in known or match_key(word) in stop:
            continue
        start, end = match.span()
        if is_covered(start, end):
            continue
        if in_place_context(text, start, end) or in_institution(text, start, end):
            skipped.append(word)
            continue
        additions.append({"start": start, "end": end,
                          "label": "SURNAME", "text": word})
        covered.append((start, end))
    return additions, skipped


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "processed" / "merged"))
    ap.add_argument("--out", default=str(ROOT / "data" / "processed" / "merged_relabeled"))
    ap.add_argument("--apply", action="store_true",
                    help="write the relabelled corpus; otherwise report only")
    ap.add_argument("--examples", type=int, default=12)
    args = ap.parse_args(argv)

    data_dir = Path(args.data_dir)
    for split in SPLITS:
        if not (data_dir / f"{split}.docs.jsonl").exists():
            print(f"error: {data_dir / f'{split}.docs.jsonl'} not found")
            return 1

    print("pass 1: collecting known SURNAME values from the corpus...")
    known = collect_surnames(data_dir)
    print(f"  {len(known):,} distinct surnames known to the corpus")

    out_dir = Path(args.out)
    if args.apply:
        out_dir.mkdir(parents=True, exist_ok=True)

    docs_total = 0
    docs_changed = 0
    spans_added = 0
    skipped_place = 0
    per_lang: Counter = Counter()
    value_counts: Counter = Counter()
    examples: list[str] = []

    print("pass 2: finding unlabelled surnames...")
    for split in SPLITS:
        src = data_dir / f"{split}.docs.jsonl"
        dst = (out_dir / f"{split}.docs.jsonl").open("w", encoding="utf-8") if args.apply else None
        try:
            with src.open(encoding="utf-8") as fh:
                for line in fh:
                    doc = json.loads(line)
                    docs_total += 1
                    additions, skipped = find_additions(
                        doc["text"], doc["entities"], known)
                    skipped_place += len(skipped)

                    if additions:
                        docs_changed += 1
                        spans_added += len(additions)
                        per_lang[doc.get("lang", "?")] += 1
                        for add in additions:
                            value_counts[add["text"]] += 1
                        if len(examples) < args.examples:
                            first = additions[0]
                            ctx = doc["text"][max(0, first["start"] - 45):
                                              first["end"] + 20].replace("\n", "\\n")
                            examples.append(
                                f"[{doc.get('lang','?')}] {first['text']!r} in ...{ctx}...")
                        doc["entities"] = sorted(
                            doc["entities"] + additions, key=lambda e: e["start"])
                        line = json.dumps(doc, ensure_ascii=False) + "\n"

                    if dst is not None:
                        dst.write(line)
        finally:
            if dst is not None:
                dst.close()

    print(f"\nscanned {docs_total:,} documents")
    print(f"documents gaining at least one SURNAME label: {docs_changed:,} "
          f"({docs_changed/docs_total:.2%})")
    print(f"SURNAME spans added: {spans_added:,}")
    print(f"place-context occurrences left alone for review: {skipped_place:,}")

    print("\nby language:")
    for lang, n in per_lang.most_common():
        print(f"  {lang}: {n:,}")

    print("\nmost frequently added values:")
    for value, n in value_counts.most_common(12):
        print(f"  {value!r}: {n:,}")

    print(f"\nexamples (up to {args.examples}):")
    for ex in examples:
        print(f"  {ex}")

    if args.apply:
        labels_src = data_dir / "labels.json"
        if labels_src.exists():
            (out_dir / "labels.json").write_text(
                labels_src.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\nwrote relabelled corpus to {out_dir}")
        print("re-split it before training (new labels change the grouping):")
        print(f"  python scripts/regroup_splits.py --data-dir {out_dir} "
              f"--out data/processed/merged_disjoint")
    else:
        print("\n(report only -- pass --apply to write the relabelled corpus)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
