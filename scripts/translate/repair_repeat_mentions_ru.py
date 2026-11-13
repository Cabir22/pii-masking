"""Make repeated mentions of one entity use one value, in a finished file.

`roundtrip_positive` used to mint a fresh value per slot rather than per
distinct source entity, so a document naming the same city twice named two
different cities: "Sahil ... Sahil" came back "Нефтечала ... Ордубад", and one
person collected three given names. It affected 27% of the Russian test output.

The generator is fixed, but the documents already written do not need
retranslating -- the carrier text is correct and only the spliced values
disagree. This rewrites them in place: group each document's entities by
(label, stem of the ORIGINAL Azerbaijani value), elect one minted value per
group, and re-splice, shifting every later offset by the length difference.

    python scripts/translate/repair_repeat_mentions_ru.py --out scratch/ru_test.jsonl \
        --input data/processed/az/test.docs.jsonl [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from piigen.locales.ru import (  # noqa: E402
    decline_street, governing_case, restyle_street,
)
from translate.run_ru import az_stem, label_shape_errors  # noqa: E402


# A street that has been declined is the same street, not a second one:
# "переулок Х" and "переулке Х" differ only in the case the sentence demanded.
# Comparing the raw strings makes the two look inconsistent, and unifying them
# would undo the declension -- which decline_streets would then redo, the two
# repairs quietly fighting over the same value.
# Canonical stems for the Russian street types. Declension changes the ending
# and "переулок" also drops its fill vowel in the oblique cases ("переулка",
# "переулке"), so a shared prefix is the only reliable comparison.
_TYPE_STEMS = ("переул", "улиц", "проспект", "площад", "шоссе",
               "ул.", "пр.", "пер.", "пл.")


def case_insensitive_form(value: str) -> str:
    """A street value with its type word reduced to a stem, the rest unchanged.

    A street that has been declined is the same street, not a second one:
    "переулок Х" and "переулке Х" differ only in the case the sentence
    demanded. Comparing raw strings makes those look inconsistent, and
    unifying them would undo the declension -- which decline_streets would
    then redo, the two repairs quietly fighting over one value.
    """
    head, _, rest = value.partition(" ")
    low = head.lower()
    for stem in _TYPE_STEMS:
        if low.startswith(stem):
            return f"{stem} {rest}" if rest else stem
    return value


def _elect(values: list[str]) -> str:
    """The value a group keeps: the commonest, ties broken by first-seen.

    Picking the most frequent one means the fewest edits, which keeps the
    rewrite as small as possible.
    """
    counts = Counter(values)
    best = max(counts.values())
    for v in values:                      # first-seen among the most frequent
        if counts[v] == best:
            return v
    return values[0]


def slot_order_is_recoverable(rec: dict, source: dict) -> bool:
    """Can an output entity still be matched to the source entity it replaced?

    The two lists correspond by SLOT. Source entities are always sorted by
    start, and the record is written sorted by start too -- but the prompt
    lets the model move a ⟦N⟧ marker where Russian word order demands, so in
    about 1.2% of documents the spliced values land in a different order from
    their slots and the two lists no longer line up position by position.

    That shows up as the label sequences disagreeing, which is cheap to test
    and is the only signal available after the fact. Where they disagree, no
    repair here can know which source value an entity came from, and guessing
    would assign the wrong label or unify the wrong pair -- so every repair
    that needs the source declines to touch the document.
    """
    src_ents = source.get("entities") or []
    ents = rec.get("entities") or []
    if len(src_ents) != len(ents):
        return False
    return [e["label"] for e in src_ents] == [e["label"] for e in ents]


def restyle_streets(rec: dict) -> tuple[dict, int]:
    """Rewrite street values written type-last in transliteration.

    "Низами кючаси" is an Azerbaijani noun sitting inside a Russian address;
    Russian puts the type first and translates it, "улица Низами". The name
    part was already transliterated correctly, so this is a rewrite rather
    than a regeneration -- but it changes the value's length, so the text and
    every later offset move with it.
    """
    ents = sorted(rec.get("entities") or [], key=lambda e: e["start"])
    if not any(e["label"] == "STREET" and restyle_street(e["text"]) for e in ents):
        return rec, 0

    text = rec["text"]
    out: list[str] = []
    new_ents: list[dict] = []
    cursor = 0
    changed = 0
    for e in ents:
        want = e["text"]
        if e["label"] == "STREET":
            fixed = restyle_street(e["text"])
            if fixed:
                want = fixed
                changed += 1
        out.append(text[cursor:e["start"]])
        start = sum(len(p) for p in out)
        out.append(want)
        new_ents.append({"start": start, "end": start + len(want),
                         "label": e["label"], "text": want})
        cursor = e["end"]
    out.append(text[cursor:])

    rec = dict(rec)
    rec["text"] = "".join(out)
    rec["entities"] = new_ents
    for e in new_ents:
        assert rec["text"][e["start"]:e["end"]] == e["text"], rec["id"]
    return rec, changed


def decline_streets(rec: dict) -> tuple[dict, int]:
    """Put a street into the case the preposition before it demands.

    "недалеко от переулок Мюбариз" is broken Russian; "от переулка Мюбариз" is
    not. Only the type word moves -- see `decline_street` for why the name is
    deliberately left in the nominative.
    """
    ents = sorted(rec.get("entities") or [], key=lambda e: e["start"])
    if not any(e["label"] == "STREET" for e in ents):
        return rec, 0

    text = rec["text"]
    out: list[str] = []
    new_ents: list[dict] = []
    cursor = 0
    changed = 0
    for e in ents:
        want = e["text"]
        if e["label"] == "STREET":
            case = governing_case(text[max(0, e["start"] - 24):e["start"]],
                                  "STREET")
            if case:
                declined = decline_street(e["text"], case)
                if declined != e["text"]:
                    want = declined
                    changed += 1
        out.append(text[cursor:e["start"]])
        start = sum(len(p) for p in out)
        out.append(want)
        new_ents.append({"start": start, "end": start + len(want),
                         "label": e["label"], "text": want})
        cursor = e["end"]
    out.append(text[cursor:])
    if not changed:
        return rec, 0

    rec = dict(rec)
    rec["text"] = "".join(out)
    rec["entities"] = new_ents
    for e in new_ents:
        assert rec["text"][e["start"]:e["end"]] == e["text"], rec["id"]
    return rec, changed


def realign_labels(rec: dict, source: dict) -> tuple[dict, int]:
    """Take each entity's label from the source entity at the same position.

    An older revision let labels and values come apart, so a ZIPCODE held a
    street name and a SURNAME held an IP address. The values were right for
    their slot and only the labels had rotated, so the source -- which is
    ordered the same way -- restores them. Only applied when it actually
    resolves every shape error in the document; anything else is left for
    regeneration rather than guessed at.
    """
    # No slot_order_is_recoverable() guard here, deliberately. That guard
    # compares the two label sequences, and this function exists precisely for
    # documents whose labels are wrong -- it would refuse every case it was
    # written for. Its own check is stronger anyway: the source labels are
    # accepted only if they resolve EVERY shape error in the document, so a
    # reordered document, where they would not, is declined on that basis.
    ents = rec.get("entities") or []
    src_ents = source.get("entities") or []
    if not ents or len(ents) != len(src_ents):
        return rec, 0
    if not label_shape_errors(ents):
        return rec, 0
    fixed = [dict(e, label=s["label"]) for e, s in zip(ents, src_ents)]
    if label_shape_errors(fixed):
        return rec, 0                     # source labels do not explain it
    changed = sum(1 for a, b in zip(ents, fixed) if a["label"] != b["label"])
    rec = dict(rec)
    rec["entities"] = fixed
    return rec, changed


def repair_record(rec: dict, source: dict) -> tuple[dict, int]:
    """Return (record, mentions_changed). The record is rewritten only if
    something actually changed, so a clean document is left byte-identical.
    """
    if not slot_order_is_recoverable(rec, source):
        return rec, 0
    ents = rec.get("entities") or []
    src_ents = source.get("entities") or []
    if len(ents) < 2:
        return rec, 0

    stext = source["text"]
    # Pair each output entity with the source entity it replaced, then keep
    # them together through the sort. The two lists correspond by SLOT, and
    # slot order is not always text order: the prompt lets the model move a
    # marker where Russian word order demands, so 157 train documents come
    # back with their entities in a different order from the source. Building
    # the keys in slot order and then walking a separately sorted list, as
    # this did, silently paired each key with the wrong entity in exactly
    # those documents.
    paired = [(e, (e["label"], az_stem(stext[s["start"]:s["end"]])))
              for e, s in zip(ents, src_ents)]
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for e, key in paired:
        groups[key].append(e["text"])
    chosen = {k: _elect(v) for k, v in groups.items()
              if len({case_insensitive_form(x) for x in v}) > 1}
    if not chosen:
        return rec, 0

    # Rebuild left to right, tracking the offset drift as values change length.
    text = rec["text"]
    out: list[str] = []
    new_ents: list[dict] = []
    cursor = 0
    changed = 0
    for e, key in sorted(paired, key=lambda t: t[0]["start"]):
        want = chosen.get(key, e["text"])
        if (want != e["text"]
                and case_insensitive_form(want) == case_insensitive_form(e["text"])):
            want = e["text"]          # same street, just in a different case
        out.append(text[cursor:e["start"]])
        start = sum(len(p) for p in out)
        out.append(want)
        if want != e["text"]:
            changed += 1
        new_ents.append({"start": start, "end": start + len(want),
                         "label": e["label"], "text": want})
        cursor = e["end"]
    out.append(text[cursor:])

    rec = dict(rec)
    rec["text"] = "".join(out)
    rec["entities"] = new_ents
    for e in new_ents:                    # the whole point: spans stay exact
        assert rec["text"][e["start"]:e["end"]] == e["text"], rec["id"]
    return rec, changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True,
                    help="the finished .jsonl to repair, rewritten in place")
    ap.add_argument("--input", type=Path, required=True,
                    help="the Azerbaijani split it was translated from")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change and write nothing")
    args = ap.parse_args(argv)

    src = {}
    for line in args.input.open(encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            src[d["id"]] = d
    rows = [json.loads(l) for l in args.out.open(encoding="utf-8") if l.strip()]

    repaired: list[dict] = []
    n_docs = n_mentions = n_relabel = n_relabel_docs = 0
    n_street = n_street_docs = n_decl = n_decl_docs = 0
    for r in rows:
        s = src.get(r["source_id"])
        if not s:
            repaired.append(r)
            continue
        new, changed = repair_record(r, s)
        if changed:
            n_docs += 1
            n_mentions += changed
        new, relabelled = realign_labels(new, s)
        if relabelled:
            n_relabel_docs += 1
            n_relabel += relabelled
        new, restyled = restyle_streets(new)
        if restyled:
            n_street_docs += 1
            n_street += restyled
        new, declined = decline_streets(new)
        if declined:
            n_decl_docs += 1
            n_decl += declined
        repaired.append(new)

    print(f"{len(rows)} documents read from {args.out.name}")
    print(f"  inconsistent documents : {n_docs} ({100 * n_docs / max(1, len(rows)):.2f}%)")
    print(f"  mentions rewritten     : {n_mentions}")
    print(f"  label/value mismatches : {n_relabel_docs} documents, "
          f"{n_relabel} labels realigned from the source")
    print(f"  street values restyled : {n_street_docs} documents, "
          f"{n_street} addresses put type-first in Russian")
    print(f"  streets declined       : {n_decl_docs} documents, "
          f"{n_decl} put in the case the preposition demands")
    if args.dry_run:
        print("  --dry-run: nothing written")
        return 0
    if not (n_docs or n_relabel_docs or n_street_docs or n_decl_docs):
        print("  nothing to do")
        return 0
    with args.out.open("w", encoding="utf-8") as f:
        for r in repaired:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  rewritten: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
