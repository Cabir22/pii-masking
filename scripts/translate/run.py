"""Translate one already-split docs file into a carrier language.

    python scripts/translate/run.py --lang en --split train
    python scripts/translate/run.py --lang en --split train --limit 50
    python scripts/translate/run.py --lang en --split train --resume

Reads  data/processed/az/<split>.docs.jsonl
Writes data/processed/<lang>/<split>.docs.jsonl
       data/processed/<lang>/<split>.repair_queue.jsonl   (git-ignored)

Per document: sentinelize -> translate under SIMURG -> check the slot set ->
mint fresh Azerbaijani values and splice them back, recording exact offsets
-> round-trip validate -> write. Any failure at any stage sends the record to
the repair queue with a reason, and the run continues.

Crash-safe by construction: the output JSONL is the source of truth and
`--resume` re-reads it to skip what is already done. The generation pipeline
learned this the hard way -- a multi-hour run that cannot be resumed will
eventually be a multi-hour run that is lost.

Value minting is seeded per `(source_id, lang)`, so re-running a document
produces the same values even though the translation itself will not be
bit-identical.
"""
from __future__ import annotations

import argparse
import atexit
import json
import random
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen.values import ValueFactory, ValuePool  # noqa: E402
from translate.client import CallFailed, ClientConfig, WahooClient  # noqa: E402
from translate import morph as MORPH  # noqa: E402
from translate.decoys import protected_ranges  # noqa: E402
from translate.stem import az_stem  # noqa: E402
from translate.guard import GuardAborted, guarded_stream  # noqa: E402
from translate.prompt import build_messages, token_budget  # noqa: E402
from translate.render import get_renderer  # noqa: E402
from translate.outputlock import OutputBusy, _OutputLock
from translate.sentinel import (CLOSE, OPEN, SlotError, check_round_trip,  # noqa: E402
                                entity_source_values, sentinelize,
                                sentinelize_protected, splice)
from translate.validate import (inherited_leak_exemptions,  # noqa: E402
                                validate_record)

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "data" / "processed"
CARRIER_MINTED = {"DATE", "TIME"}   # minted through the carrier locale
ZERO_WIDTH_RE = re.compile(r"[​‌‍⁠﻿]")
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")


def out_paths(lang: str, split: str) -> tuple[Path, Path]:
    d = PROCESSED / lang
    return d / f"{split}.docs.jsonl", d / f"{split}.repair_queue.jsonl"


def load_done(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["source_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def independent_mint_values(labels: list[str], lang: str, seed: str) -> dict[int, str]:
    """The ORIGINAL (2026-09-04) mint_values -- one independent draw per
    slot, no awareness that two slots can be the same underlying fact.

    Kept ONLY so scripts/translate/repair_repeat_mentions.py can
    reconstruct, byte-for-byte, what an already-translated document's values
    were minted from -- that reconstruction is how the repair pass recovers
    which written entity came from which slot, since the JSONL on disk does
    not record slot numbers. Do not call this from the live pipeline; use
    `mint_values` below.
    """
    rng = random.Random(seed)
    factory = ValueFactory(rng, ValuePool(max_share=1.0, state_path=None))
    renderer = get_renderer(lang)
    out: dict[int, str] = {}
    for i, label in enumerate(labels):
        mint_lang = lang if label in CARRIER_MINTED else "az"
        out[i] = renderer(label, factory.make(label, mint_lang), rng)
    return out


def mint_values(labels: list[str], source_values: list[str], lang: str,
                seed: str, genders: list[str | None] | None = None,
                years: list[int | None] | None = None) -> dict[int, str]:
    """slot index -> its fresh value, minted ONCE PER DISTINCT SOURCE VALUE,
    in fixed first-occurrence order.

    Repeat mentions -- the same underlying fact stated more than once in the
    source, which piigen's own `complete_occurrences` creates by finding
    every textual occurrence of a resolved claim and tagging each one -- must
    still be the same fact after translation. Slots are grouped by
    `(label, az_stem(source_values[i]))` -- the same entity however the
    Azerbaijani inflected or cased it (`Sumqayıt` / `Sumqayıtda`, `Eldarlı` /
    `ELDARLI`), as run_ru.py does; every slot in a group reuses the first
    mint. (This is also why source_values must be exact substrings of the
    ORIGINAL text, not the sentinelized one -- two mentions of the same
    "18:53" are identical strings before they are replaced by different
    sentinel numbers.)

    Minting must still not depend on the order the sentinels come back in
    the translation -- see mint_values' groups being built by slot order
    0..n-1, not by the order splice() encounters them -- so a document the
    model reorders, or a --resume, reproduces the same values.

    DATE and TIME are minted through the *carrier* locale (an English
    document wants "21 February 1956", not "21 fevral 1956"); everything
    else comes from the Azerbaijani pools with its orthography adjusted --
    structured values pass through the renderer untouched.

    D-56c: `genders[i]` ('f'/'m') mints a given name or surname of the source
    person's gender (item 1); `years[i]` mints a DATE in the source year
    (item 3). Without them, the draw is as before.
    """
    rng = random.Random(seed)
    factory = ValueFactory(rng, ValuePool(max_share=1.0, state_path=None))
    renderer = get_renderer(lang)
    group_values: dict[tuple[str, str], str] = {}
    out: dict[int, str] = {}
    for i, (label, src) in enumerate(zip(labels, source_values)):
        key = (label, az_stem(src))
        if key not in group_values:
            mint_lang = lang if label in CARRIER_MINTED else "az"
            g = genders[i] if genders else None
            y = years[i] if years else None
            if label == "GIVENNAME" and g:
                raw = factory.givenname("az", female=g == "f")
            elif label == "SURNAME" and g:
                raw = factory.surname("az", female=g == "f")
            elif label == "DATE" and isinstance(y, tuple):
                # M4: the text repeats the whole date; the same day, month and
                # year, in the carrier's own date format
                raw = factory.loc(mint_lang).date_builder(*y, rng)
            elif label == "DATE" and y:
                raw = factory.date(mint_lang, min_year=y, max_year=y)
            else:
                raw = factory.make(label, mint_lang)
            # M2 (re-check): no Cyrillic name in Turkish text
            # (`Алтунбай`, `Етигад'in`): a Cyrillic spelling variant goes back
            # to the pool's own Latin spelling
            if lang == "tr" and label in ("GIVENNAME", "SURNAME") and _CYRILLIC.search(raw):
                raw = factory.name_variants.get(raw, (raw, ""))[0]
            group_values[key] = renderer(label, raw, rng)
        out[i] = group_values[key]
    return out


def source_facts(rec: dict) -> tuple[list[str | None], list[int | None], list[str | None]]:
    """Per entity, in text order (the order of the entity slots): the source
    person's gender, the source DATE's year, and the Azerbaijani case of an
    inflected name or place span (D-56c items 1-3)."""
    text = rec["text"]
    ents = sorted(rec["entities"], key=lambda e: (e["start"], e["end"]))
    vals = [text[e["start"]:e["end"]] for e in ents]
    stems, cases = [], []
    for e, v in zip(ents, vals):
        stem, case = MORPH.source_case(e["label"], v)
        stems.append(stem)
        cases.append(case)
    genders = MORPH.person_genders(text, ents, stems)
    # the source DATE's year, or its whole date when the text repeats it (M4)
    years = [MORPH.source_date(text, e["start"], e["end"]) if e["label"] == "DATE" else None for e in ents]
    return genders, years, cases


_TR_HYPHEN_SUFFIX = re.compile(r"-(?:dir|dır|dur|dür|da|də|de|dan|dən|den|ci|cı|cu|cü)\b")


def translate_one(rec: dict, lang: str, client: WahooClient,
                  attempts: int) -> tuple[dict | None, dict | None]:
    """(record, None) on success, (None, repair_entry) on failure.

    A fresh ValueFactory per document, its rng seeded on (source_id, lang):
    the minted values are then a pure function of the document, so a
    re-run -- or a --resume that processes a different subset, or a
    different thread order -- reproduces them exactly. A single shared
    factory cannot promise that: its ValuePool is stateful and the pool
    draw for document N would depend on which of documents 1..N-1 happened
    to finish first. `max_share=1.0` disables the pool's cross-document
    reuse cap, which was a synthetic-diversity aid for the AZ *generation*
    run and has nothing to do here -- the source set is already ~50k
    diverse documents and the per-draw pool distributions carry it.
    """
    src_id = rec["id"]
    # Decoys are protected alongside entities: they are PII-shaped on purpose
    # and their exact broken shape is the training signal, so they must come
    # back byte-for-byte. Negative records have entities: [], so before this
    # they were handed to the model as raw text and 2.1% came back mangled on
    # the English track. Shadows -- untagged repeat occurrences of a tagged
    # value -- are protected too, so a document cannot end up naming the
    # original person in one place and the freshly minted one in another.
    # D-54b: the look-alike's value only, by position, not the Azerbaijani
    # phrase around it (translate/decoys.py). `decoys` stays the excuse list
    # for the leak checks: the protected values plus the declared phrases.
    ranges = protected_ranges(rec)
    decoys = ([rec["text"][a:b] for a, b in ranges]
              + list((rec.get("_spec") or {}).get("hard_negatives") or []))
    templated, slots = sentinelize_protected(rec["text"], rec["entities"],
                                             decoy_ranges=ranges)
    entity_slots = [i for i, s in enumerate(slots) if s["kind"] == "entity"]
    labels = [slots[i]["label"] for i in entity_slots]
    source_values = [slots[i]["value"] for i in entity_slots]
    exempt_domains = inherited_leak_exemptions(rec["text"], rec["entities"], lang)
    n = len(slots)
    genders, years, cases = source_facts(rec)
    if lang == "tr":
        # D-56c (2): the Azerbaijani case of a name or place, as a tag after
        # its placeholder; the model writes the tag Turkish needs
        for k, slot_i in enumerate(entity_slots):
            if cases[k]:
                tok = f"{OPEN}{slot_i}{CLOSE}"
                templated = templated.replace(tok, tok + "{" + cases[k] + "}", 1)
    messages = build_messages(templated, lang)
    budget = token_budget(templated)
    last_reason = "unknown"
    last_output = ""          # kept for the repair queue -- failures must be
                              # debuggable without a re-run

    for attempt in range(attempts):
        try:
            stream = client.stream_chat(messages, max_tokens=budget)
            guarded = guarded_stream(stream, lang)
        except GuardAborted as exc:
            last_reason = f"simurg_corrupt: {'; '.join(exc.reasons)}"
            if exc.partial:
                last_output = exc.partial
            continue
        except CallFailed as exc:
            last_reason = f"call_failed: {exc}"
            continue

        # Zero-width characters (ZWJ/ZWNJ/ZWSP/BOM) turn up occasionally in
        # LLM output, usually next to an emoji. They are never meaningful,
        # never part of a span, and stripping them here -- before splicing --
        # keeps every offset correct.
        translated = ZERO_WIDTH_RE.sub("", guarded.text).strip()
        last_output = translated
        translated, tags = MORPH.take_tags(translated)
        if lang == "tr":
            inflectable = {slot_i for k, slot_i in enumerate(entity_slots)
                           if labels[k] in MORPH.INFLECTED_LABELS}
            translated = MORPH.take_tr_suffixes(translated, inflectable, tags)
            MORPH.spread_person_tags(translated, tags, {slot_i for k, slot_i in enumerate(entity_slots)
                                                        if labels[k] in ("GIVENNAME", "SURNAME")}, "tr")
            MORPH.drop_gen_before_tarafindan(translated, tags)     # M6
        if MORPH.STRAY_TAG.search(translated):
            last_reason = "stray case tag"
            continue
        slots_ok, reason = check_round_trip(translated, n)
        if not slots_ok:
            last_reason = f"slots: {reason}"
            continue

        # Minted in fixed slot order, so values are a pure function of
        # (source_id, lang) whatever order the model returned the sentinels
        # in -- and re-computed each attempt from the same seed, so a retry
        # that re-mints does not drift.
        entity_values = mint_values(labels, source_values, lang,
                                    f"{src_id}|{lang}", genders=genders, years=years)
        # slot -> what goes back in: a fresh value for an entity, the SAME
        # fresh value for a shadow occurrence of that entity's value (so the
        # document does not end up naming two different people), and the
        # original string verbatim for a decoy.
        by_slot: dict[int, str] = {}
        group_value: dict[tuple[str, str], str] = {}
        for k, slot_i in enumerate(entity_slots):
            by_slot[slot_i] = entity_values[k]
            group_value[(labels[k], source_values[k])] = entity_values[k]
            # D-56c (2) / D-56d: the case the Turkish sentence needs, on the
            # value itself; the span is the whole inflected form
            tag = tags.get(slot_i)
            if lang == "tr" and tag and labels[k] in MORPH.INFLECTED_LABELS:
                by_slot[slot_i] = MORPH.tr_inflect(entity_values[k], tag)
        for i, s in enumerate(slots):
            if s["kind"] == "decoy":
                by_slot[i] = s["value"]
            elif s["kind"] == "shadow":
                by_slot[i] = group_value.get((s["label"], s["value"]), s["value"])
        try:
            final_text, spans = splice(translated, lambda i: by_slot[i])
        except SlotError as exc:
            last_reason = f"splice: {exc}"
            continue

        # Only entity slots become entities; decoy and shadow slots are
        # carrier text. Spans come back in output order, so pair each with its
        # own slot and then sort by position (the schema and the tokenizer
        # alignment both assume left-to-right).
        placed = sorted(
            ({"start": sp["start"], "end": sp["end"],
              "label": slots[sp["slot"]]["label"], "_val": by_slot[sp["slot"]]}
             for sp in spans if slots[sp["slot"]]["kind"] == "entity"),
            key=lambda e: (e["start"], e["end"]))
        entities = [{k: v for k, v in e.items() if k != "_val"} for e in placed]
        minted_by_pos = {i: e["_val"] for i, e in enumerate(placed)}
        # D-56c (10): a mask of a value's last digits follows the new value;
        # (6) no year word after a full Turkish date
        masks = MORPH.mask_edits(rec["text"], source_values,
                                 [entity_values[k] for k in range(len(labels))])
        final_text, entities = MORPH.apply_masks(final_text, entities, masks)
        if lang == "tr":
            final_text, entities = MORPH.apply_text_edits(
                final_text, entities, MORPH.year_word_edits(final_text, entities, "tr"))
            # M6: `üzrə` -> never `uyarınca`
            final_text, entities = MORPH.apply_text_edits(
                final_text, entities, MORPH.tr_uyarinca_edits(rec["text"], final_text, entities))
            # (7) an Azerbaijani hyphen ending after a value
            if any(_TR_HYPHEN_SUFFIX.match(final_text, e["end"]) for e in entities):
                last_reason = "validator: tr_hyphen_suffix"
                last_output = final_text
                continue
        out = {
            "id": f"{src_id}__{lang}",
            "source_id": src_id,
            "lang": lang,
            "split": rec.get("_split", ""),
            "text": final_text,
            "entities": entities,
            "_bucket": rec.get("_bucket"),
            "_register": rec.get("_register"),
        }
        report = validate_record(out, source_text=rec["text"],
                                 templated=templated,
                                 minted=minted_by_pos,
                                 decoys=decoys,
                                 source_values=source_values,
                                 expected_entities=len(entity_slots),
                                 inherited_leak_domains=exempt_domains,
                                 guard_state=guarded.state)
        if report.ok:
            return out, None
        last_reason = "validator: " + "; ".join(report.failures)

    return None, {"source_id": src_id, "lang": lang, "reason": last_reason,
                  "slots": n, "bucket": rec.get("_bucket"),
                  "templated": templated, "output": last_output}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", required=True, choices=["en", "tr"],
                    help="carrier language. Russian has its own runner, "
                         "scripts/translate/run_ru.py -- it carries the "
                         "Cyrillic-specific validators (az_residue tuned "
                         "for Cyrillic, romanised_russian, mixed_script) "
                         "and the retry-with-correction loop this one "
                         "does not have.")
    ap.add_argument("--split", choices=["train", "val", "test"],
                    help="one of the three az splits; reads "
                         "data/processed/az/<split>.docs.jsonl and writes "
                         "data/processed/<lang>/<split>.*")
    ap.add_argument("--input", type=Path,
                    help="translate an arbitrary docs file instead of a "
                         "split (e.g. data/golden/golden_az.jsonl). Needs "
                         "--out.")
    ap.add_argument("--out", type=Path,
                    help="output path for --input mode; the repair queue is "
                         "written alongside it as <stem>.repair_queue.jsonl")
    ap.add_argument("--split-name", choices=["train", "val", "test"],
                    help="D-64c: --input mode's source split, stamped on every "
                         "row (else a split already on the record, else \"\")")
    ap.add_argument("--limit", type=int, default=None,
                    help="stop after N documents (smoke runs)")
    ap.add_argument("--resume", action="store_true",
                    help="skip source_ids already in the output file")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="split the agreed endpoint budget three ways -- "
                         "sustained 64 took api.hal-x.ai down on 2026-08-28")
    ap.add_argument("--attempts", type=int, default=3,
                    help="tries per document before the repair queue")
    ap.add_argument("--model", default=None)
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--think", action="store_true",
                    help="leave the model's reasoning channel on (slower, and "
                         "it invites restructuring rather than translating)")
    ap.add_argument("--dry-run", action="store_true",
                    help="sentinelize and mint only; no API calls")
    args = ap.parse_args(argv)

    if bool(args.split) == bool(args.input):
        print("error: pass exactly one of --split or (--input + --out)",
              file=sys.stderr)
        return 1
    if args.input:
        if not args.out:
            print("error: --input needs --out", file=sys.stderr)
            return 1
        src = args.input
        out_path = args.out
        repair_path = out_path.with_name(
            out_path.name.rsplit(".jsonl", 1)[0] + ".repair_queue.jsonl")
        split_tag = args.split_name or ""
    else:
        src = PROCESSED / "az" / f"{args.split}.docs.jsonl"
        out_path, repair_path = out_paths(args.lang, args.split)
        split_tag = args.split

    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Claim the output before reading it. --resume snapshots "what is already
    # done" and then appends, so two runs against one output both translate
    # the whole remainder -- see translate/outputlock.py for the incident this
    # prevents. Russian had this guard; en/tr did not until 2026-09-07.
    out_lock = _OutputLock(out_path)
    if not args.dry_run:
        try:
            out_lock.acquire()
        except OutputBusy as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        atexit.register(out_lock.release)

    done = load_done(out_path) if args.resume else set()
    records = []
    with src.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r["id"] in done:
                continue
            # Prefer a real split already on the record (--input mode feeds
            # arbitrary files, including ones the caller pre-filtered per
            # split and stamped themselves, under either field name) over
            # split_tag, which is "" for --input mode precisely because it
            # cannot otherwise know. Checked BEFORE assigning, not after --
            # unconditionally overwriting first (the previous behavior)
            # clobbers a correctly-set field before it can ever be read.
            # D-64c: an explicit --split-name wins (the full run passes the
            # source split it is translating)
            r["_split"] = (args.split_name if args.input and args.split_name
                           else r.get("split") or r.get("_split") or split_tag)
            records.append(r)
            if args.limit and len(records) >= args.limit:
                break

    print(f"{src.name}: {len(records)} to do"
          + (f" ({len(done)} already done)" if done else ""))
    if not records:
        return 0

    if args.dry_run:
        return _dry_run(records, args.lang)

    cfg = ClientConfig(temperature=args.temperature, think=args.think)
    if args.model:
        cfg.model = args.model
    if args.base_url:
        cfg.base_url = args.base_url
    client = WahooClient(cfg)
    print(f"endpoint {client.base_url}  model {client.model}  "
          f"concurrency {args.concurrency}  thinking="
          f"{'on' if args.think else 'off'}\n")

    ok = failed = 0
    newly_done: set[str] = set()
    t0 = time.time()
    mode = "a" if args.resume else "w"
    with out_path.open(mode, encoding="utf-8") as fout, \
            repair_path.open(mode, encoding="utf-8") as frep, \
            ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(translate_one, r, args.lang, client,
                               args.attempts): r for r in records}
        for i, fut in enumerate(as_completed(futures), 1):
            rec, repair = fut.result()
            if rec is not None:
                # Written as they complete; JSONL order is not meaningful and
                # the split is already fixed, so no ordering guarantee is lost.
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                ok += 1
                newly_done.add(rec["source_id"])
            else:
                frep.write(json.dumps(repair, ensure_ascii=False) + "\n")
                frep.flush()
                failed += 1
            if i % 25 == 0 or i == len(records):
                rate = i / max(1e-9, time.time() - t0)
                print(f"  {i}/{len(records)}  ok={ok} repair={failed}  "
                      f"{rate:.1f} docs/s  calls={client.calls} "
                      f"retries={client.retries}")

    total = ok + failed
    print(f"\nwrote {ok} to {out_path}")
    if failed:
        print(f"     {failed} to {repair_path}  "
              f"({failed / max(1, total):.1%} repair rate)")
    print(f"elapsed {time.time() - t0:.0f}s")

    if args.resume:
        _dedupe_repair_queue(repair_path, done | newly_done)
    return 0


def _dedupe_repair_queue(repair_path: Path, succeeded: set[str]) -> None:
    """Rewrite the repair queue keeping only its LATEST entry per source_id,
    and dropping any source_id that has since succeeded.

    `--resume` opens this file in append mode across every invocation, so
    without this it accumulates forever: a source_id that failed once, then
    succeeded on a later --resume, keeps its stale failure entry alongside
    the (correct) record already in docs.jsonl -- 1,032 stale/duplicate
    entries were found in the wild on the English track after several
    resumed runs. Latest-wins on duplicates because a later attempt reflects
    the current prompt/harness, not an earlier one.
    """
    if not repair_path.exists():
        return
    latest: dict[str, dict] = {}
    for line in repair_path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        latest[r["source_id"]] = r              # later line overwrites earlier
    kept = [r for sid, r in latest.items() if sid not in succeeded]
    with repair_path.open("w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _dry_run(records, lang) -> int:
    """Exercise sentinelize -> mint -> splice with no API, using the templated
    text itself as the 'translation'. Catches wiring and renderer errors, and
    checks mint determinism -- including under a shuffled sentinel order,
    which is what a real translation does."""
    from translate.sentinel import splice as _splice
    ok = bad = 0
    for r in records:
        ranges = protected_ranges(r)
        decoys = [r["text"][a:b] for a, b in ranges]
        templated, slots = sentinelize_protected(r["text"], r["entities"],
                                                 decoy_ranges=ranges)
        entity_slots = [i for i, s in enumerate(slots) if s["kind"] == "entity"]
        labels = [slots[i]["label"] for i in entity_slots]
        source_values = [slots[i]["value"] for i in entity_slots]
        seed = f"{r['id']}|{lang}"
        values = mint_values(labels, source_values, lang, seed)
        if mint_values(labels, source_values, lang, seed) != values:
            print(f"  NONDETERMINISTIC {r['id']}")
            bad += 1
        # repeat mentions must mint identically
        by_group: dict[tuple[str, str], set[str]] = {}
        for i, (lab, src) in enumerate(zip(labels, source_values)):
            by_group.setdefault((lab, src), set()).add(values[i])
        for (lab, src), vs in by_group.items():
            if len(vs) > 1:
                print(f"  REPEAT-GROUP INCONSISTENT {r['id']} {lab} {src!r}: {vs}")
                bad += 1
        by_slot: dict[int, str] = {}
        group_value: dict[tuple[str, str], str] = {}
        for k, slot_i in enumerate(entity_slots):
            by_slot[slot_i] = values[k]
            group_value[(labels[k], source_values[k])] = values[k]
        for i, s in enumerate(slots):
            if s["kind"] == "decoy":
                by_slot[i] = s["value"]
            elif s["kind"] == "shadow":
                by_slot[i] = group_value.get((s["label"], s["value"]), s["value"])
        try:
            text, spans = _splice(templated, lambda i: by_slot[i])
        except SlotError as exc:
            print(f"  SPLICE FAIL {r['id']}: {exc}")
            bad += 1
            continue
        if any(text[s["start"]:s["end"]] != by_slot[s["slot"]] for s in spans):
            print(f"  SPAN FAIL {r['id']}")
            bad += 1
        # A decoy must come back byte-identical -- but only judge the ones
        # that were actually IN the source. 3.3% of declared
        # `_spec.hard_negatives` strings do not appear in the rendered text
        # at all (a typo, a case difference, a fused Azerbaijani suffix): a
        # pre-existing AZ-corpus artifact that predates translation and that
        # re-translating cannot fix. Flagging those here would report a
        # harness bug that is not one.
        elif any(d and d in r["text"] and d not in text for d in decoys):
            print(f"  DECOY LOST {r['id']}")
            bad += 1
        else:
            ok += 1
    print(f"dry run: {ok} spliced with exact spans, {bad} failed")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
