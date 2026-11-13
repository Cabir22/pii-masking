# -*- coding: utf-8 -*-
"""Extract GIVENNAME/SURNAME values from data/processed/merged_rebalanced/
(train + val + test), split by whether each individual name is literally
Azerbaijani-origin or not -- NOT by the document's own language, and NOT by
the per-document 60/40 "native" roll (native there means "native to that
DOCUMENT's language", e.g. an English name in an en-tagged document, which
is a different, looser cut than "is this name Azerbaijani").

How the AZ/foreign call is made: substitute_names.substitute_names_in_doc
draws each name from a specific language pool (`sample_lang`) -- doc_lang
itself when the doc rolled "native", otherwise a randomly chosen OTHER
language. That per-name draw is never written back into the corpus, so it
has to be replayed from the same seeded RNG stream substitute_names.py
used (same technique audit_substitution.py already uses for the native/
foreign roll -- this reuses that approach but also captures the language
each key actually drew, not just the roll). Verified against
merged_original for exact entity-count / order alignment before trusting
any of this.

One row = one document's distinct name value (deduplicated per document,
same as before) plus the language it was actually drawn from. A single
document CAN contain one AZ-origin name and one non-AZ name at once (a
GIVENNAME and a SURNAME draw independently), so AZ/foreign is decided per
name, not per document.

Output (data/name_extracts/rebalanced/, replaces the previous run which
used the wrong split):
  train_az.csv        train_foreign.csv
  val_az.csv          val_foreign.csv
  test_az.csv         test_foreign.csv
      columns: split, doc_id, doc_lang, label, value, origin_lang
  all_pairs.csv
      one row per document's given_name/surname pairing (positional, see
      pair_rows()'s docstring), WITH each side's own origin_lang so you can
      see when a document's given name and surname came from different
      languages.

Usage:
    python scripts/extract_names.py
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from substitute_names import get_doc_language, LANGUAGES  # noqa: E402

ORIG_DIR = ROOT / "data" / "processed" / "merged_original"
REBAL_DIR = ROOT / "data" / "processed" / "merged_rebalanced"
OUT_DIR = ROOT / "data" / "name_extracts" / "rebalanced"
RUN_ORDER = ["train", "val", "test"]
NAME_LABELS = ("GIVENNAME", "SURNAME")


def load_docs(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def replay_origin_langs(splits_in_order: list[tuple[str, list[dict]]],
                        seed: int = 42, native_pct: float = 0.60,
                        ) -> dict[str, list[dict[tuple[str, str], str]]]:
    """Replay the exact RNG stream substitute_names.py consumed (same seed,
    same split order, same per-doc draw pattern as
    substitute_names_in_doc), but instead of discarding the language each
    name key drew, record it.

    Returns {split: [ {(label, old_value): sample_lang}, ... ]} -- one dict
    per document, in the same order as that split's docs list.
    """
    random.seed(seed)
    out: dict[str, list[dict[tuple[str, str], str]]] = {}
    for split_name, docs in splits_in_order:
        per_doc = []
        for d in docs:
            use_native = random.random() < native_pct
            doc_lang = get_doc_language(d)
            text = d["text"]
            key_lang: dict[tuple[str, str], str] = {}
            for e in reversed(d.get("entities", [])):
                lab = e.get("label", "")
                if lab not in NAME_LABELS:
                    continue
                s, en_ = e.get("start", 0), e.get("end", 0)
                key = (lab, text[s:en_])
                if key in key_lang:
                    continue
                if use_native:
                    key_lang[key] = doc_lang
                else:
                    key_lang[key] = random.choice(
                        [l for l in LANGUAGES if l != doc_lang])
            per_doc.append(key_lang)
        out[split_name] = per_doc
    return out


def doc_name_occurrences(orig_doc: dict, rebal_doc: dict,
                          key_lang: dict[tuple[str, str], str],
                          ) -> list[tuple[str, str, str]]:
    """(label, new_value, origin_lang) for each distinct name in this
    document, deduplicated by new_value, in order of first appearance.
    Matches original and rebalanced entities positionally -- both lists
    have the same length and order, only start/end and the text differ
    after substitution (verified by the entity-count-preserved check in
    audit_substitution.py's own audit)."""
    orig_entities = orig_doc.get("entities", [])
    rebal_entities = rebal_doc.get("entities", [])
    assert len(orig_entities) == len(rebal_entities), (
        f"entity count mismatch on {orig_doc.get('id')}")
    orig_text = orig_doc["text"]
    rebal_text = rebal_doc["text"]

    seen_new_values: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for oe, re in zip(orig_entities, rebal_entities):
        label = oe.get("label", "")
        if label not in NAME_LABELS:
            continue
        old_val = orig_text[oe.get("start", 0):oe.get("end", 0)]
        new_val = rebal_text[re.get("start", 0):re.get("end", 0)]
        if new_val in seen_new_values:
            continue
        seen_new_values.add(new_val)
        origin_lang = key_lang.get((label, old_val), "?")
        out.append((label, new_val, origin_lang))
    return out


def pair_rows(occurrences: list[tuple[str, str, str]], split: str,
              doc_id: str, doc_lang: str) -> list[dict]:
    """Positional given_name/surname pairing for a friendlier combined
    view -- 1st GIVENNAME with 1st SURNAME, 2nd with 2nd, etc. Documents
    with an uneven count leave the other side blank. This is a pairing
    heuristic (the corpus doesn't track which name belongs to which
    person when several people are mentioned), not identity resolution."""
    givens = [(v, o) for l, v, o in occurrences if l == "GIVENNAME"]
    surnames = [(v, o) for l, v, o in occurrences if l == "SURNAME"]
    n = max(len(givens), len(surnames))
    rows = []
    for i in range(n):
        gv, go = givens[i] if i < len(givens) else ("", "")
        sv, so = surnames[i] if i < len(surnames) else ("", "")
        rows.append({
            "split": split, "doc_id": doc_id, "doc_lang": doc_lang,
            "given_name": gv, "given_origin": go,
            "surname": sv, "surname_origin": so,
        })
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    print("Loading merged_original (train/val/test, for RNG replay order)...",
          file=sys.stderr)
    orig_by_split = {s: load_docs(ORIG_DIR / f"{s}.docs.jsonl") for s in RUN_ORDER}
    lang_by_split = replay_origin_langs([(s, orig_by_split[s]) for s in RUN_ORDER])

    flat_fields = ["split", "doc_id", "doc_lang", "label", "value", "origin_lang"]
    pair_fields = ["split", "doc_id", "doc_lang", "given_name", "given_origin",
                   "surname", "surname_origin"]

    all_pairs: list[dict] = []
    summary = []

    for split in RUN_ORDER:
        print(f"Processing {split}...", file=sys.stderr)
        orig_docs = orig_by_split[split]
        rebal_docs = load_docs(REBAL_DIR / f"{split}.docs.jsonl")
        key_langs = lang_by_split[split]
        assert len(orig_docs) == len(rebal_docs) == len(key_langs)

        az_rows, foreign_rows = [], []
        for orig_doc, rebal_doc, key_lang in zip(orig_docs, rebal_docs, key_langs):
            doc_id = rebal_doc.get("id", "")
            doc_lang = rebal_doc.get("lang", "")
            occ = doc_name_occurrences(orig_doc, rebal_doc, key_lang)
            for label, value, origin_lang in occ:
                row = {"split": split, "doc_id": doc_id, "doc_lang": doc_lang,
                       "label": label, "value": value, "origin_lang": origin_lang}
                (az_rows if origin_lang == "az" else foreign_rows).append(row)
            all_pairs.extend(pair_rows(occ, split, doc_id, doc_lang))

        write_csv(OUT_DIR / f"{split}_az.csv", az_rows, flat_fields)
        write_csv(OUT_DIR / f"{split}_foreign.csv", foreign_rows, flat_fields)
        summary.append((split, len(rebal_docs), len(az_rows), len(foreign_rows)))

    write_csv(OUT_DIR / "all_pairs.csv", all_pairs, pair_fields)

    print()
    print(f"{'split':<8}{'docs':>10}{'az names':>12}{'foreign names':>16}")
    for split, ndocs, naz, nf in summary:
        print(f"{split:<8}{ndocs:>10}{naz:>12}{nf:>16}")
    print()
    print(f"Written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
