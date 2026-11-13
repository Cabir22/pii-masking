"""Adversarial audit of a translated corpus. Assume it is NOT ready.

`validate_corpus.py` is the gate for the Azerbaijani corpus; much of it is
AZ-specific (language gates, AZ anchors, the AZ resolver). This is the
equivalent gate for a translated one, reusing every language-independent
check from piigen and adding the ones only translation can fail.

Deliberately NOT circular: the checks here do not ask "does this match what
the harness produced", which is what the harness's own verification does and
is why two real defects (repeat-mention inconsistency, decoy mangling) shipped
past it. These checks interrogate the text itself.

Run:
    python scripts/translate/audit_corpus.py --lang tr --split train
    python scripts/translate/audit_corpus.py --lang tr --all
    python scripts/translate/audit_corpus.py --lang en --all --tokenizer
    python scripts/translate/audit_corpus.py --lang tr \
        --docs data/processed/tr/calibration_sample.tr.docs.jsonl \
        --az   data/processed/tr/calibration_sample.docs.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen.anchors import structural_kind                       # noqa: E402
from piigen.config import DETECTION_TIERS, REMOVED_LABELS        # noqa: E402
from piigen.llm.quality import find_leaked_pii                   # noqa: E402
from piigen.validate import span_boundary_problems, value_valid  # noqa: E402
from translate.lang import ANCHORS as ANCHOR_MODULES            # noqa: E402
from translate.sentinel import SENTINEL_RE, entity_source_values, sentinelize  # noqa: E402
from translate.validate import (_domain_skeleton, _leftover_azerbaijani,  # noqa: E402
                                _mixed_script_words, _LEAK_VALUE_RE,
                                inherited_leak_exemptions)

ZERO_WIDTH = set("​‌‍⁠﻿")
KNOWN_LABELS = set(DETECTION_TIERS)

# Checks whose only acceptable value is zero -- each means a record would
# teach the model something false.
MUST_BE_ZERO = [
    "duplicate_id", "exact_duplicate_text", "span_out_of_range", "empty_span",
    "whitespace_edge_span", "overlapping_spans", "duplicate_span",
    "unknown_label", "removed_label", "sentinel_survived", "not_nfc",
    "zero_width", "entities_unsorted", "entity_count_drift",
    "unlabeled_pii_leak", "structural_number_span", "missing_anchor",
    "leftover_azerbaijani", "stale_az_value", "value_invalid",
    "repeat_group_inconsistent", "no_az_source", "lang_wrong",
    "decoy_lost_in_translation", "corrupt_char", "mixed_script_word",
]
# Real, but judgement calls rather than automatic corpus failures.
ADVISORY = ["decoy_absent_in_source", "span_boundary_problem",
            "length_ratio_extreme"]


def audit_record(en: dict, az: dict, lang: str, counts: Counter,
                 samples: dict) -> None:
    def hit(check: str, detail: str = "") -> None:
        counts[check] += 1
        if len(samples[check]) < 8:
            samples[check].append(f"{en.get('id','?')}: {detail}"[:300])

    text = en.get("text", "")
    ents = en.get("entities", [])

    if en.get("lang") != lang:
        hit("lang_wrong", str(en.get("lang")))

    # --- spans -------------------------------------------------------
    prev_end = -1
    seen_spans = set()
    for i, e in enumerate(ents):
        s, t, lab = e.get("start"), e.get("end"), e.get("label")
        if not isinstance(s, int) or not isinstance(t, int) or not (0 <= s < t <= len(text)):
            hit("span_out_of_range", f"e{i} [{s},{t}) len={len(text)}")
            continue
        val = text[s:t]
        if not val.strip():
            hit("empty_span", f"e{i}")
        if val != val.strip():
            hit("whitespace_edge_span", f"e{i} {val!r}")
        if s < prev_end:
            hit("overlapping_spans", f"e{i} starts {s}, prev ended {prev_end}")
        if (s, t) in seen_spans:
            hit("duplicate_span", f"e{i} [{s},{t})")
        seen_spans.add((s, t))
        prev_end = t
        if lab in REMOVED_LABELS:
            hit("removed_label", f"{lab}")
        elif lab not in KNOWN_LABELS:
            hit("unknown_label", f"{lab}")
        # value must actually be a valid instance of its label
        ok, why = value_valid(lab, val)
        if not ok:
            hit("value_invalid", f"{lab}={val!r}: {why}")
        # a digit sitting in document furniture is never PII
        kind = structural_kind(text, s, t)
        if kind:
            hit("structural_number_span", f"{lab}={val!r} ({kind})")

    if ents != sorted(ents, key=lambda e: (e.get("start", 0), e.get("end", 0))):
        hit("entities_unsorted")

    # --- text hygiene -------------------------------------------------
    # ANY ⟦ or ⟧, not just a well-formed ⟦digits⟧: those characters were
    # chosen because natural az/en/tr/ru text never contains them, so a bare
    # one is always a leak. The strict form misses a mangled token and, more
    # importantly, the model echoing the literal "⟦N⟧" out of the prompt's
    # own description of the token format -- which shipped one record into
    # the Turkish train split (2026-09-06).
    if any(c in ("⟦", "⟧") for c in text):
        m = SENTINEL_RE.search(text)
        hit("sentinel_survived", m.group(0) if m else
            next(repr(text[max(0, i - 2):i + 3])
                 for i, c in enumerate(text) if c in ("⟦", "⟧")))
    if unicodedata.normalize("NFC", text) != text:
        hit("not_nfc")
    if any(c in ZERO_WIDTH for c in text):
        hit("zero_width")
    # Never-legitimate characters. The Azerbaijani source provably contains
    # none of them (0 across all 84,339 train records, measured 2026-09-06),
    # so any occurrence is corruption introduced downstream -- two Turkish
    # records carried a U+FFFD replacement character.
    corrupt = sorted({c for c in text
                      if c == "\ufffd"
                      or unicodedata.category(c) in ("Co", "Cs", "Cn")})
    if corrupt:
        hit("corrupt_char", ", ".join(f"U+{ord(c):04X}" for c in corrupt[:4]))
    leftover = _leftover_azerbaijani(text, ents, lang)
    if leftover:
        hit("leftover_azerbaijani", ", ".join(map(repr, leftover[:4])))
    mixed = _mixed_script_words(text, ents, lang)
    if mixed:
        hit("mixed_script_word", ", ".join(map(repr, mixed[:4])))

    # --- anchors ------------------------------------------------------
    mod = ANCHOR_MODULES.get(lang)
    if mod:
        for e in mod.anchor_failures(text, ents):
            hit("missing_anchor", f"{e['label']}@{e['start']}")

    # --- against the Azerbaijani source -------------------------------
    if az is None:
        hit("no_az_source", en.get("source_id", "?"))
        return

    _, labels = sentinelize(az["text"], az["entities"])
    src_values = entity_source_values(az["text"], az["entities"])
    decoys = (az.get("_spec") or {}).get("hard_negatives") or []
    if len(ents) != len(labels):
        hit("entity_count_drift", f"{len(ents)} vs {len(labels)} in source")

    # An original Azerbaijani entity value still sitting in the English text
    # means an occurrence that was never tagged (so never sentinelized) rode
    # through translation untouched -- the document now states the same fact
    # two different ways. Word-boundary match, not substring: plain "in text"
    # false-positives whenever the old value is a numeric prefix of an
    # unrelated freshly-minted one (a stale "192.0.2.5" flagged purely
    # because a different, correct, entity minted "192.0.2.56" nearby) --
    # found during the 2026-09-05 audit. Two more exemptions, same audit:
    #  - a match sitting inside a tagged EN span is a MINTING COLLISION, not a
    #    leak -- ZIPCODE/CITY have a small value space, so mint_values legit-
    #    imately re-draws a value equal to the source one now and then; it is
    #    still correctly tagged and internally consistent.
    #  - a match inside a decoy string is the decoy, spliced back verbatim by
    #    design (self-correction traps like "Astara (no, Tovuz)"). Pruning it
    #    would just reproduce it on the retry -- an infinite repair loop.
    spans = [(e["start"], e["end"]) for e in ents
             if isinstance(e.get("start"), int) and isinstance(e.get("end"), int)]
    decoy_hits = [(m.start(), m.end()) for d in decoys if d
                  for m in re.finditer(re.escape(d), text)]
    for sv in set(src_values):
        if len(sv) < 6:
            continue
        for m in re.finditer(rf"(?<!\w){re.escape(sv)}(?!\w)", text):
            if any(a <= m.start() and m.end() <= b for a, b in spans):
                continue
            if any(a <= m.start() < b or a < m.end() <= b
                   for a, b in decoy_hits):
                continue
            hit("stale_az_value", f"{sv!r}")
            break
        else:
            continue
        break

    # repeat mentions must have come out identical
    groups = defaultdict(list)
    for i, key in enumerate(zip(labels, src_values)):
        groups[key].append(i)
    if any(len(v) >= 2 for v in groups.values()):
        by_label = defaultdict(set)
        for e in ents:
            v = text[e["start"]:e["end"]]
            # Russian declines the street-TYPE word for grammatical case
            # (переулок / переулком, проспект / проспекта) -- deliberate, done
            # with pymorphy3 on translate/ru. The base name is unchanged, so
            # two case forms of one street are consistent, not "split". Drop
            # the leading Cyrillic type word before comparing.
            if lang == "ru" and e["label"] == "STREET":
                v = re.sub(r"^[А-Яа-яЁё-]+\s+", "", v, count=1)
            by_label[e["label"]].add(v)
        for (lab, sv), idxs in groups.items():
            if len(idxs) < 2:
                continue
            # every slot in this group should hold one value; if the English
            # doc has more distinct values for this label than the source has
            # distinct source-values for it, something split.
            src_distinct = len({s for (l, s) in groups if l == lab})
            if len(by_label[lab]) > src_distinct:
                hit("repeat_group_inconsistent",
                    f"{lab}: {src_distinct} source value(s) -> "
                    f"{len(by_label[lab])} English value(s)")
                break

    # --- unlabeled PII (the check that is not circular) ---------------
    leaks = find_leaked_pii(text, ents, decoys)
    # An EMAIL "leak" whose domain matches an untagged email already sitting
    # in the AZ source is not a translation defect -- it is an AZ-corpus
    # tagging gap (header/signature emails its own ASCII-only find_leaked_pii
    # never saw) faithfully carried through. Held to the same standard as the
    # source; tracked since 2026-09-05. Same filter as
    # validate_record.
    exempt = inherited_leak_exemptions(az["text"], az["entities"], lang)
    real = []
    for lk in leaks:
        m = _LEAK_VALUE_RE.match(lk)
        val = m.group(1) if m else lk
        if lk.startswith("EMAIL:") and _domain_skeleton(val, lang) in exempt:
            continue
        real.append(lk)
    if real:
        hit("unlabeled_pii_leak", "; ".join(map(repr, real[:3])))

    # --- advisory -----------------------------------------------------
    # A decoy that is missing from the translation is only a TRANSLATION
    # defect if it was in the Azerbaijani source to begin with. 3.1% of
    # declared `_spec.hard_negatives` strings never appear in the rendered
    # text at all (a typo, a case difference, a fused Azerbaijani suffix) --
    # a pre-existing AZ-corpus artifact that predates translation and that
    # re-translating cannot fix. Reporting the two together made the English
    # track's 1.75% look like a translation problem and cost ~1,800
    # already-good records to a mistaken prune. They are counted separately
    # now: `decoy_lost_in_translation` is the one that means something.
    for d in decoys:
        if not d or d in text:
            continue
        if d in az.get("text", ""):
            counts["decoy_lost_in_translation"] += 1
            if len(samples["decoy_lost_in_translation"]) < 8:
                samples["decoy_lost_in_translation"].append(
                    f"{en.get('id')}: {d!r} was in the source, gone from output")
        else:
            counts["decoy_absent_in_source"] += 1
            if len(samples["decoy_absent_in_source"]) < 8:
                samples["decoy_absent_in_source"].append(
                    f"{en.get('id')}: {d!r} (never in the AZ text -- AZ artifact)")
        break
    probs = span_boundary_problems(text, ents)
    if probs:
        counts["span_boundary_problem"] += 1
        if len(samples["span_boundary_problem"]) < 8:
            samples["span_boundary_problem"].append(f"{en.get('id')}: {probs[0]}")
    if az.get("text"):
        ratio = len(text) / max(1, len(az["text"]))
        if not (0.4 <= ratio <= 2.5):
            counts["length_ratio_extreme"] += 1
            if len(samples["length_ratio_extreme"]) < 8:
                samples["length_ratio_extreme"].append(f"{en.get('id')}: {ratio:.2f}")


def audit_file(lang: str, en_path: Path, az_path: Path,
               tokenizer_check: bool) -> tuple[Counter, dict, dict]:
    az = {json.loads(l)["id"]: json.loads(l)
          for l in az_path.open(encoding="utf-8") if l.strip()}
    counts: Counter = Counter()
    samples: dict = defaultdict(list)
    ids, texts = set(), set()
    label_counts: Counter = Counter()
    n = 0
    docs = []
    bad: set[str] = set()
    for line in en_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        n += 1
        if r.get("id") in ids:
            counts["duplicate_id"] += 1
            samples["duplicate_id"].append(str(r.get("id")))
        ids.add(r.get("id"))
        th = hash(r.get("text", ""))
        if th in texts:
            counts["exact_duplicate_text"] += 1
            if len(samples["exact_duplicate_text"]) < 8:
                samples["exact_duplicate_text"].append(str(r.get("id")))
        texts.add(th)
        for e in r.get("entities", []):
            label_counts[e.get("label")] += 1
        before = Counter(counts)
        audit_record(r, az.get(r.get("source_id")), lang, counts, samples)
        # ONLY genuine MUST_BE_ZERO failures are pruned-and-retranslated.
        # decoy_altered and span_boundary_problem were pruned on 2026-09-05
        # under the wrong assumption that retranslation would fix them --
        # decoy_altered turned out to be almost entirely a pre-existing
        # _spec.hard_negatives-vs-rendered-text mismatch that PREDATES
        # translation (the AZ generator's planned decoy string sometimes
        # differs from what actually ended up in the text -- a typo, a case
        # difference, a fused suffix), so re-translating the same AZ source
        # reproduces the same gap. That prune cost ~1,800 already-good
        # records for nothing. Advisory stays advisory: reported, never
        # auto-pruned.
        newly = {c for c in counts if counts[c] != before.get(c, 0)}
        if newly & set(MUST_BE_ZERO):
            bad.add(r.get("source_id"))
        if tokenizer_check:
            docs.append(r)
    stats = {"records": n, "labels": label_counts, "az_total": len(az),
             "docs": docs, "bad": bad}
    return counts, samples, stats


def prune_file(en_path: Path, bad: set[str]) -> int:
    """Drop failing records so `run.py --resume` re-translates exactly those."""
    kept = []
    dropped = 0
    for line in en_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("source_id") in bad:
            dropped += 1
        else:
            kept.append(line)
    if not dropped:
        return 0
    bak = en_path.with_name(en_path.stem + ".preprune_bak.jsonl")
    if not bak.exists():
        en_path.replace(bak)
    tmp = en_path.with_name(en_path.stem + ".pruned.jsonl")
    with tmp.open("w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")
    tmp.replace(en_path)
    return dropped


def tokenizer_recoverability(docs: list[dict], base_model: str) -> dict:
    """Can every span still be recovered as a token boundary after
    tokenization? This is what actually decides whether BIO labels are
    assignable -- the 2026-08-26 audit moved it 98.386% -> 99.982% on AZ with
    add_punctuation_boundary, and translated text has never been measured."""
    from transformers import AutoTokenizer
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from prepare_splits import add_punctuation_boundary

    tok = AutoTokenizer.from_pretrained(base_model)
    patched = add_punctuation_boundary(tok)
    total = starts_ok = ends_ok = both_ok = 0
    for r in docs:
        text = r["text"]
        if not r["entities"]:
            continue
        enc = tok(text, return_offsets_mapping=True, add_special_tokens=False)
        starts = {a for a, b in enc["offset_mapping"] if a != b}
        ends = {b for a, b in enc["offset_mapping"] if a != b}
        for e in r["entities"]:
            total += 1
            s_ok = e["start"] in starts
            e_ok = e["end"] in ends
            starts_ok += s_ok
            ends_ok += e_ok
            both_ok += (s_ok and e_ok)
    return {"patched": patched, "spans": total,
            "start_aligned": starts_ok, "end_aligned": ends_ok,
            "fully_recoverable": both_ok}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", required=True)
    ap.add_argument("--split", choices=["train", "val", "test"])
    ap.add_argument("--all", action="store_true",
                    help="train + val + test + golden")
    ap.add_argument("--docs", type=Path,
                    help="audit an arbitrary translated docs file (e.g. a "
                         "calibration sample) instead of a split. Needs --az.")
    ap.add_argument("--az", type=Path,
                    help="the Azerbaijani source file for --docs")
    ap.add_argument("--tokenizer", action="store_true",
                    help="also measure span recoverability under the tokenizer "
                         "(slow; sampled to --tokenizer-sample docs)")
    ap.add_argument("--tokenizer-sample", type=int, default=4000)
    ap.add_argument("--base-model", default="xlm-roberta-base")
    ap.add_argument("--prune", action="store_true",
                    help="REWRITE each docs file without the records that fail "
                         "a MUST-BE-ZERO check or lost a decoy, so a "
                         "`run.py --resume` re-translates exactly those under "
                         "the fixed harness. Keeps a .preprune_bak.jsonl.")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    targets = []
    if args.all:
        for s in ("train", "val", "test"):
            targets.append((s,
                            root / "data" / "processed" / args.lang / f"{s}.docs.jsonl",
                            root / "data" / "processed" / "az" / f"{s}.docs.jsonl"))
        targets.append(("golden",
                        root / "data" / "golden" / f"golden_{args.lang}.jsonl",
                        root / "data" / "golden" / "golden_az.jsonl"))
    elif args.split:
        targets.append((args.split,
                        root / "data" / "processed" / args.lang / f"{args.split}.docs.jsonl",
                        root / "data" / "processed" / "az" / f"{args.split}.docs.jsonl"))
    elif args.docs:
        if not args.az:
            print("error: --docs needs --az", file=sys.stderr)
            return 1
        targets.append((args.docs.name, args.docs, args.az))
    else:
        print("error: pass --split, --all, or --docs + --az", file=sys.stderr)
        return 1

    grand: Counter = Counter()
    all_docs = []
    total_records = 0
    for name, en_path, az_path in targets:
        if not en_path.exists():
            print(f"SKIP {name}: {en_path} not found")
            continue
        counts, samples, stats = audit_file(args.lang, en_path, az_path,
                                            args.tokenizer)
        total_records += stats["records"]
        grand.update(counts)
        all_docs.extend(stats["docs"][:args.tokenizer_sample])
        print(f"\n{'='*66}\n{name}: {stats['records']} records "
              f"({len(stats['labels'])} labels, "
              f"{sum(stats['labels'].values())} entities)\n{'='*66}")
        failures = [(c, counts[c]) for c in MUST_BE_ZERO if counts.get(c)]
        advisories = [(c, counts[c]) for c in ADVISORY if counts.get(c)]
        if not failures:
            print("  MUST-BE-ZERO: all clean")
        for c, v in failures:
            pct = v / max(1, stats["records"]) * 100
            print(f"  FAIL  {c:<28} {v:>7}  ({pct:.2f}% of records)")
            for s in samples[c][:4]:
                print(f"          {s}")
        for c, v in advisories:
            pct = v / max(1, stats["records"]) * 100
            print(f"  note  {c:<28} {v:>7}  ({pct:.2f}%)")
            for s in samples[c][:3]:
                print(f"          {s}")
        if args.prune:
            dropped = prune_file(en_path, stats["bad"])
            print(f"  pruned {dropped} record(s) from {en_path.name} "
                  f"(backup: {en_path.stem}.preprune_bak.jsonl)")
        elif stats["bad"]:
            print(f"  -> {len(stats['bad'])} record(s) would be pruned "
                  f"for re-translation (--prune)")

    print(f"\n{'='*66}\nGRAND TOTAL over {total_records} records\n{'='*66}")
    hard = {c: grand[c] for c in MUST_BE_ZERO if grand.get(c)}
    if hard:
        for c, v in sorted(hard.items(), key=lambda kv: -kv[1]):
            print(f"  FAIL  {c:<28} {v:>7}  ({v/max(1,total_records)*100:.2f}%)")
    else:
        print("  every MUST-BE-ZERO check is zero")
    for c in ADVISORY:
        if grand.get(c):
            print(f"  note  {c:<28} {grand[c]:>7}  "
                  f"({grand[c]/max(1,total_records)*100:.2f}%)")

    if args.tokenizer and all_docs:
        print(f"\ntokenizer span recoverability ({len(all_docs)} docs sampled, "
              f"{args.base_model}):")
        tk = tokenizer_recoverability(all_docs, args.base_model)
        sp = max(1, tk["spans"])
        print(f"  punctuation patch applied: {tk['patched']}")
        print(f"  spans measured:      {tk['spans']}")
        print(f"  start aligned:       {tk['start_aligned']} ({tk['start_aligned']/sp*100:.3f}%)")
        print(f"  end aligned:         {tk['end_aligned']} ({tk['end_aligned']/sp*100:.3f}%)")
        print(f"  fully recoverable:   {tk['fully_recoverable']} ({tk['fully_recoverable']/sp*100:.3f}%)")

    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
