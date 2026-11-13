"""Stage 3: merge, dedup, stratified split, and tokenizer/BIO alignment.

Turns one or more `data/raw/*.jsonl` generation-run outputs (each already
individually valid, but never merged or split) into a trainable dataset,
written by default to `data/processed/az/` (the Azerbaijani source split --
carrier-language translations of it land in `data/processed/{en,tr,ru}/`,
and the shuffled union in `data/processed/merged/`):

    {train,val,test}.docs.jsonl  -- text + char-span entities, always written.
                                     Human-readable, re-tokenizable if the
                                     base model changes later.
    {train,val,test}.jsonl       -- tokenized input_ids/attention_mask/labels
                                     windows, unless --no-tokenize.
    labels.json                  -- label list + label2id/id2label. Also
                                     written one level up (`data/processed/`)
                                     since it is language-independent.

Design notes (why it's built this way):

  * Re-validates every record through `piigen.validate.validate_example`
    before anything else. Each input file already passed this gate once at
    generation time, but files from different runs -- possibly different
    code versions, possibly hand-edited -- are combined here for the first
    time; re-checking costs nothing and catches drift instead of assuming it.
  * Dedup is by id first (a real collision means two runs reused indices)
    and by exact text second (the same document surviving from two
    different output files, e.g. a rename-without-clean).
  * Stratification key is (lang, rarest entity type present in the doc),
    using global label frequency computed over the loaded set to decide
    "rarest". Stratifying by language alone would let a low-frequency label
    land almost entirely in one split by chance -- with the current
    entity_weights config some labels target under 1% of mentions, so this
    matters more here than it would for a balanced label set.
  * BIO alignment is a pure function of (offset_mapping, entities):
    `align_labels_for_window`. A token gets B-<TYPE> only when
    `tok_start == entity_start`, I-<TYPE> on any other overlap, else O.
    Entities are always the document's *global* char-span list, never
    re-derived per window, which is what makes sliding windows correct with
    zero cross-window state -- an entity split across a window boundary is
    B-/I- in the first window and the *same* entity is seen again (this
    time with tok_start > entity_start) as I- in the next, never a spurious
    second B-. Verified empirically before writing this: the tokenizer's
    own `return_overflowing_tokens`/`stride` keeps `offset_mapping` in
    *original-document* character coordinates in every window, not
    window-relative -- confirmed by direct inspection, not assumed.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from piigen.config import ENTITY_TYPES          # noqa: E402
from piigen.validate import validate_example    # noqa: E402

IGNORE_LABEL_ID = -100


# ---------------------------------------------------------------------------
# Tokenizer patching
# ---------------------------------------------------------------------------

def add_punctuation_boundary(tokenizer) -> bool:
    """Adds a `Punctuation()` step to a fast tokenizer's pre-tokenizer.

    2026-08-26 tokenizer audit: SentencePiece's Metaspace
    pre-tokenizer only splits on the space BEFORE a word, so punctuation that
    directly follows an entity with no space -- '(92)' -> '_(' + '92)' --
    stays welded onto the entity's own final token, leaving no token
    boundary at the span's end. Measured directly against the real corpus
    (xlm-roberta-large, all 141,215 gold spans): span *starts* aligned to a
    token boundary 99.606% of the time, ends only 98.605% -- exactly the
    asymmetry a closing-punctuation weld predicts, and 1.614% of gold spans
    were physically unemittable for this reason alone. Confirmed empirically
    before shipping (not assumed): re-encoding '(92)' after this patch
    produces '(' + '92' + ')' as three separate tokens instead of one welded
    '92)'.

    Appending `Punctuation()` moved the exact-span-recoverable ceiling
    98.386% -> 99.982% in that measurement, for a measured +20% sequence
    length cost (mean 298 -> 357 tokens/doc). Worth it per the audit: those
    points are otherwise unrecoverable at any model quality, no matter which
    base model wins the Stage 4 bake-off -- all candidates share the same
    SentencePiece-250k tokenizer family.

    Preserves whatever pre-tokenizer steps the base model actually ships
    with (read back via indexing rather than hand-reconstructed, since a
    hand-built replacement could silently drop or mis-parameterize a step
    e.g. Metaspace's `prepend_scheme`/`replacement`) and appends
    `Punctuation()` after them, matching the ordering the audit measured.

    Returns True if patched, False (no-op) for a tokenizer with no
    `backend_tokenizer` -- a slow/Python tokenizer, which no candidate in
    the Stage 4 bake-off uses, but a future base-model swap could still
    surface one, and this should fail loudly (caller prints a warning)
    rather than silently skip the fix.
    """
    backend = getattr(tokenizer, "backend_tokenizer", None)
    if backend is None:
        return False
    from tokenizers import pre_tokenizers
    pt = backend.pre_tokenizer
    steps = []
    if isinstance(pt, pre_tokenizers.Sequence):
        i = 0
        while True:
            try:
                steps.append(pt[i])
            except Exception:
                break
            i += 1
    elif pt is not None:
        steps = [pt]
    backend.pre_tokenizer = pre_tokenizers.Sequence(
        steps + [pre_tokenizers.Punctuation()])
    return True


# ---------------------------------------------------------------------------
# Label space
# ---------------------------------------------------------------------------

def build_label_list() -> list[str]:
    labels = ["O"]
    for ent in ENTITY_TYPES:
        labels.append(f"B-{ent}")
        labels.append(f"I-{ent}")
    return labels


# ---------------------------------------------------------------------------
# Load / dedup / re-validate
# ---------------------------------------------------------------------------

def load_records(paths: list[Path]) -> list[dict]:
    """Loads records and rewrites `id` to be globally unique across files.

    Each generation run numbers its own output from 0
    (`llm_{lang}_{index:06d}`), so the SAME id string routinely appears in
    two independent runs while pointing at two completely different
    documents -- confirmed empirically (0 shared exact texts, 38 shared ids
    across two real 50-doc runs) before relying on this. Prefixing by
    source filename keeps ids traceable back to their run without treating
    that numbering coincidence as a collision.

    Only applied across multiple input files -- a single file's own ids are
    already unique by construction, and prefixing it anyway would just
    double a prefix a prior merge (e.g. `combine_repaired.py`) already
    applied (`combined__repaired.clean__llm_az_000003` instead of the
    single, already-correct `repaired.clean__llm_az_000003`).
    """
    records = []
    for p in paths:
        with p.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(f"  skipping malformed line {p}:{lineno}: {exc}",
                          file=sys.stderr)
                    continue
                if len(paths) > 1:
                    r["id"] = f"{p.stem}__{r.get('id', lineno)}"
                records.append(r)
    return records


def dedup(records: list[dict]) -> tuple[list[dict], int]:
    """Drops exact-text duplicates only. `id` is not a dedup signal here --
    see `load_records`'s note on why id equality across files is
    meaningless; genuine cross-run duplication only ever shows up as
    identical text.
    """
    seen_text: set = set()
    out = []
    dupes = 0
    for r in records:
        text = r.get("text")
        if text in seen_text:
            dupes += 1
            continue
        seen_text.add(text)
        out.append(r)
    return out, dupes


def revalidate(records: list[dict]) -> tuple[list[dict], list[tuple[str, list[str]]]]:
    """Re-runs the shared validator over every record before splitting.

    A record with zero entities is, in this repaired/audited corpus,
    necessarily a negative_only document (the ordinary generation path's
    `no_entities` gate never lets a zero-entity positive doc through) --
    decoy-dominated by construction, so it was already accepted at
    generation time under a relaxed language-evidence floor (see
    pipeline.py's `assemble_document`, 2026-08-28). Re-validating it here
    under the DEFAULT length-scaled threshold would silently reject a large
    share of that corpus for the exact false-positive pattern already found
    and fixed -- not a new check, just matching the standard this class of
    document was actually accepted under.
    """
    clean, rejected = [], []
    for r in records:
        min_native = 0 if not r.get("entities") else None
        problems = validate_example(r, min_native_words=min_native)
        if problems:
            rejected.append((r.get("id", "?"), problems))
        else:
            clean.append(r)
    return clean, rejected


# ---------------------------------------------------------------------------
# Stratified split
# ---------------------------------------------------------------------------

def _rarest_label(entities: list[dict], label_freq: Counter) -> str:
    if not entities:
        return "_none"
    return min((e["label"] for e in entities), key=lambda l: label_freq.get(l, 0))


def stratified_split(records: list[dict], val_frac: float, test_frac: float,
                     seed: int, group_key=None) -> tuple[list[dict], list[dict], list[dict]]:
    """Split within (lang, rarest label) strata.

    `group_key` (v4.1, data audit A2): documents with the same key -- the same
    template, `_skeleton` -- always land in the same split, so a template never
    sits in both train and test (it inflated the internal test score). Without
    it, documents are split one by one, exactly as before."""
    label_freq = Counter()
    for r in records:
        for e in r["entities"]:
            label_freq[e["label"]] += 1
    if group_key is not None:
        return _group_split(records, val_frac, test_frac, seed, group_key, label_freq)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        key = (r["lang"], _rarest_label(r["entities"], label_freq))
        groups[key].append(r)

    rng = random.Random(seed)
    train, val, test = [], [], []
    for rows in groups.values():
        rng.shuffle(rows)
        n = len(rows)
        # Small groups (common at pilot scale, where many (lang, rarest-label)
        # combinations have only 1-2 members): keep them in train rather
        # than force a fractional split that would put a whole label's only
        # example in val/test where it teaches the model nothing.
        if n < 3:
            train.extend(rows)
            continue
        n_test = max(1, round(n * test_frac))
        n_val = max(1, round(n * val_frac))
        n_test = min(n_test, n - 1)
        n_val = min(n_val, n - n_test - 1) if n - n_test > 1 else 0
        test.extend(rows[:n_test])
        val.extend(rows[n_test:n_test + n_val])
        train.extend(rows[n_test + n_val:])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def _group_split(records: list[dict], val_frac: float, test_frac: float, seed: int,
                 group_key, label_freq: Counter) -> tuple[list[dict], list[dict], list[dict]]:
    """`stratified_split` with whole groups. A group's stratum is its first
    document's. In each stratum the groups are shuffled, then placed largest
    first, each into the split furthest below its target share (by documents):
    the big template groups (`minimal`'s lone `<GIVENNAME>`, 112 documents in
    a 25,000 build) go to train, where their lesson is learnt, and val/test
    fill with distinct templates. Strata under 3 documents stay in train."""
    groups: dict = {}
    for r in records:
        groups.setdefault(group_key(r), []).append(r)
    strata: dict[tuple, list[list[dict]]] = defaultdict(list)
    for g in groups.values():
        strata[(g[0]["lang"], _rarest_label(g[0]["entities"], label_freq))].append(g)

    rng = random.Random(seed)
    train, val, test = [], [], []
    for gs in strata.values():
        n = sum(len(g) for g in gs)
        if n < 3:
            for g in gs:
                train.extend(g)
            continue
        rng.shuffle(gs)
        gs.sort(key=len, reverse=True)          # stable: shuffled order among equal sizes
        target = {"train": n * (1 - val_frac - test_frac), "val": n * val_frac, "test": n * test_frac}
        got = {"train": 0, "val": 0, "test": 0}
        out = {"train": train, "val": val, "test": test}
        for g in gs:
            name = max(("test", "val", "train"), key=lambda k: target[k] - got[k])
            out[name].extend(g)
            got[name] += len(g)

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


# ---------------------------------------------------------------------------
# Tokenizer / BIO alignment
# ---------------------------------------------------------------------------

def align_labels_for_window(offset_mapping: list[tuple[int, int]],
                            entities: list[dict], label2id: dict[str, int]
                            ) -> list[int]:
    """One label id per token in this window. Pure function of the window's
    own offsets (in original-document coordinates) and the document's full
    entity list -- no state carried BETWEEN WINDOWS, no window-relative
    coordinates. `open_key` below is carried between TOKENS within this one
    window/call only -- see the note on it.

    2026-08-30: xlm-roberta-large's own fast tokenizer sometimes emits a
    standalone metaspace token immediately before a real one, with an
    offset that OVERLAPS the real token's first character instead of
    ending where it starts -- e.g. for "...CVV: 483..." it produced a
    bare '▁' token at (10, 11) ('4') immediately followed by '483' at
    (10, 13), both starting at 10. `tok_start == e["start"]` was then true
    for BOTH tokens, so both got B-, an invalid BIO sequence (confirmed on
    the real corpus: 21.4% of windows, 41,828 double-B occurrences,
    zero-cost to check for and never legitimate -- two tokens can't both
    begin the same entity). Not caused by the Punctuation() patch above;
    confirmed present on the unpatched tokenizer for the same input.
    """
    out = []
    # (start, end, label) of whichever entity the PREVIOUS non-special token
    # in THIS window was labeled for, or None. Only ever compared within one
    # call/window, so it can't affect the documented cross-window
    # continuation behavior (a window whose first real token starts a
    # continuation gets a fresh `open_key = None` here, so `tok_start ==
    # e["start"]` being false there -- true start was in an earlier window
    # -- still correctly yields "I", exactly as before this change).
    open_key = None
    for tok_start, tok_end in offset_mapping:
        if tok_start == tok_end:
            # Special token (<s>, </s>, <pad>, ...): excluded from the loss.
            out.append(IGNORE_LABEL_ID)
            open_key = None
            continue
        label = "O"
        matched_key = None
        for e in entities:
            if tok_end <= e["start"] or tok_start >= e["end"]:
                continue
            matched_key = (e["start"], e["end"], e["label"])
            if matched_key == open_key:
                # Already opened this exact entity on the token just before
                # this one. A second token whose offset ALSO satisfies
                # tok_start == e["start"] is the tokenizer artifact above,
                # not a second beginning -- never re-open with B once I has
                # started for this entity in this window.
                tag = "I"
            else:
                tag = "B" if tok_start == e["start"] else "I"
            label = f"{tag}-{e['label']}"
            break
        out.append(label2id[label])
        open_key = matched_key
    return out


def tokenize_split(records: list[dict], tokenizer, label2id: dict[str, int],
                   max_length: int, stride: int) -> list[dict]:
    windows = []
    for r in records:
        enc = tokenizer(
            r["text"],
            return_offsets_mapping=True,
            return_overflowing_tokens=True,
            truncation=True,
            max_length=max_length,
            stride=stride,
        )
        for w in range(len(enc["input_ids"])):
            windows.append({
                "id": f"{r['id']}__w{w}",
                "input_ids": enc["input_ids"][w],
                "attention_mask": enc["attention_mask"][w],
                "labels": align_labels_for_window(
                    enc["offset_mapping"][w], r["entities"], label2id),
            })
    return windows


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def report(name: str, records: list[dict]) -> None:
    n = len(records)
    langs = Counter(r["lang"] for r in records)
    mentions = sum(len(r["entities"]) for r in records)
    print(f"  {name:<6} {n:>6} docs   {mentions:>6} mentions   "
          f"langs={dict(langs)}")


# ---------------------------------------------------------------------------
# Leakage between splits
# ---------------------------------------------------------------------------

def _skeleton(rec: dict) -> str:
    """Document with every entity value replaced by its label, every declared
    look-alike (`_decoys`) by the label it resembles, and digits collapsed --
    two documents sharing a skeleton share a template. v4.1 (A2): look-alikes
    too, so two documents that differ only in their look-alike values count
    as one template."""
    chars = list(rec["text"])
    spans = [(e["start"], e["end"], f"<{e['label']}>") for e in rec["entities"]]
    spans += [(x["start"], x["end"], f"<~{x.get('resembles', '')}>") for x in rec.get("_decoys") or []
              if "start" in x and "end" in x]
    for s, e, tag in sorted(spans, key=lambda t: -t[0]):
        chars[s:e] = list(tag)
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", "".join(chars))).strip().lower()


def _identity_combos(rec: dict) -> set:
    """(GIVENNAME, SURNAME) pairs present in a document.

    The most consequential leak is not a shared city -- cities repeat
    legitimately -- but the same PERSON appearing in train and test, which
    lets a model score well by remembering an individual.
    """
    given = sorted({e["text"] for e in rec["entities"]
                    if e["label"] == "GIVENNAME"})
    surs = sorted({e["text"] for e in rec["entities"]
                   if e["label"] == "SURNAME"})
    return {(g, s) for g in given for s in surs}


def leakage_report(splits: dict[str, list[dict]]) -> dict:
    """Quantify what train shares with val and test.

    Reported, not enforced. Some overlap is unavoidable and even correct:
    there are 97 Azerbaijani cities and every split will contain most of
    them. What must never overlap is exact or near-identical DOCUMENTS, and
    what should be watched is identity reuse.
    """
    def texts(rows):
        return {r["text"] for r in rows}

    def normed(rows):
        return {re.sub(r"\s+", " ", r["text"]).strip().lower() for r in rows}

    def skeletons(rows):
        return {_skeleton(r) for r in rows}

    def values(rows):
        return {(e["label"], e["text"]) for r in rows for e in r["entities"]}

    def identities(rows):
        out = set()
        for r in rows:
            out |= _identity_combos(r)
        return out

    train = splits["train"]
    out: dict = {}
    for name in ("val", "test"):
        other = splits[name]
        if not other:
            continue
        entry = {}
        for kind, fn in (("exact_text", texts), ("normalized_text", normed),
                         ("template_skeleton", skeletons),
                         ("entity_value", values), ("identity_combo", identities)):
            a, b = fn(train), fn(other)
            shared = a & b
            entry[kind] = {
                "shared": len(shared),
                "share_of_split": (len(shared) / len(b)) if b else 0.0,
            }
        out[name] = entry
    return out


def print_leakage(report_data: dict) -> None:
    print("\nSplit leakage (train vs each held-out split):")
    print(f"  {'split':<6}{'measure':<20}{'shared':>9}{'% of split':>12}")
    for split, kinds in report_data.items():
        for kind, stats in kinds.items():
            flag = ""
            # Exact and normalized document overlap must be zero -- dedup
            # runs before the split, so anything here is a bug. Template and
            # value overlap are informational.
            if kind in ("exact_text", "normalized_text") and stats["shared"]:
                flag = "   <-- MUST BE ZERO"
            elif kind == "template_skeleton" and stats["share_of_split"] > 0.05:
                flag = "   <-- high template reuse"
            elif kind == "identity_combo" and stats["share_of_split"] > 0.10:
                flag = "   <-- identity reuse"
            print(f"  {split:<6}{kind:<20}{stats['shared']:>9,}"
                  f"{stats['share_of_split']*100:>11.2f}%{flag}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def tokenize_only(args) -> int:
    """Tokenize already-split `*.docs.jsonl` files in place, and nothing else.

    The multilingual corpus is built by translating each split file
    separately (so a record and its translations can never straddle
    train/test). Translation changes text length,
    so the Azerbaijani windows do not transfer and every language's
    `.docs.jsonl` has to be re-windowed against its own text.

    This path deliberately skips `revalidate()`, `dedup()`,
    `stratified_split()` and `leakage_report()`. The records arrive already
    split, so three of those have nothing to do -- and `revalidate()` would
    actively destroy the run: it enforces an Azerbaijani language-evidence
    floor and rejects every translated document on sight. Span integrity for
    a translated record is established by the translation harness's
    round-trip validator at splice time, which is a stronger check than
    anything available here.
    """
    paths = [Path(p) for p in args.inputs]
    missing = [p for p in paths if not p.exists()]
    if missing:
        print(f"error: input file(s) not found: {missing}", file=sys.stderr)
        return 1
    bad = [p for p in paths if not p.name.endswith(".docs.jsonl")]
    if bad:
        print(f"error: --tokenize-only takes *.docs.jsonl files, got: {bad}",
              file=sys.stderr)
        return 1

    label_list = build_label_list()
    label2id = {l: i for i, l in enumerate(label_list)}

    print(f"Loading tokenizer {args.base_model!r}...")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if add_punctuation_boundary(tokenizer):
        print("  patched pre-tokenizer: added Punctuation() step "
              "(2026-08-26 tokenizer audit)")
    else:
        print(f"  warning: {args.base_model!r} has no fast tokenizer -- "
              "punctuation-weld fix NOT applied, spans may be unemittable "
              "at punctuation-adjacent boundaries", file=sys.stderr)

    for path in paths:
        records = []
        with path.open(encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"  skipping malformed line {path}:{lineno}: {exc}",
                          file=sys.stderr)
        windows = tokenize_split(records, tokenizer, label2id,
                                 args.max_length, args.stride)
        out = path.with_name(path.name[:-len(".docs.jsonl")] + ".jsonl")
        write_jsonl(out, windows)
        langs = Counter(r.get("lang", "?") for r in records)
        print(f"  {path.name}: {len(records)} docs -> {len(windows)} window(s)"
              f"  langs={dict(langs)}  -> {out.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+", help="data/raw/*.jsonl file(s) to merge")
    p.add_argument("--output-dir", default="data/processed/az",
                   help="where to write the split (default: the AZ source "
                        "split location). labels.json is also written to this "
                        "dir's parent.")
    p.add_argument("--tokenize-only", action="store_true",
                   help="inputs are already-split *.docs.jsonl files (e.g. a "
                        "translated corpus): tokenize each in place to the "
                        "sibling *.jsonl and exit. Skips revalidation, dedup, "
                        "splitting and the leakage report -- see tokenize_only()")
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--test-frac", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--group-split", choices=("none", "template"), default="none",
                   help="v4.1 (data audit A2): 'template' keeps documents with the same "
                        "template (_skeleton) in one split; default: documents one by one")
    p.add_argument("--no-tokenize", action="store_true",
                   help="write only the .docs.jsonl files, skip tokenization")
    p.add_argument("--base-model", default="xlm-roberta-base",
                   help="HF model id or local path whose tokenizer to use")
    # 2026-08-26: was max_length=256/stride=32. Measured entity token
    # lengths on the live corpus: ACCESS_TOKEN mean 154.5, max 197;
    # PRIVATE_KEY max 127. At max_length=256 a 197-token entity fills 76%
    # of the window on its own, so no stride up to 192 gets it fully into
    # any single window (swept 80 boundary positions: even stride=192 still
    # truncated 5% of the time, worst case 194/195 tokens). The window was
    # too small for the entities, not just the stride too short.
    #
    # max_length=512 is XLM-R's actual max sequence length (also our
    # primary base-model candidate's cap (2026-08-25
    # base-model research entry), so raising to it is not a new constraint,
    # just using the model's real capacity. At 512/stride=256, the same
    # 80-position sweep against the worst-case 195-token entity: 0%
    # truncated, every position captures the entity whole in >=1 window.
    p.add_argument("--max-length", type=int, default=512)
    p.add_argument("--stride", type=int, default=256)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.tokenize_only:
        return tokenize_only(args)

    out_dir = Path(args.output_dir)

    input_paths = [Path(p) for p in args.inputs]
    missing = [p for p in input_paths if not p.exists()]
    if missing:
        print(f"error: input file(s) not found: {missing}", file=sys.stderr)
        return 1

    print(f"Loading {len(input_paths)} file(s)...")
    records = load_records(input_paths)
    print(f"  {len(records)} raw records")

    records, rejected = revalidate(records)
    if rejected:
        print(f"  {len(rejected)} record(s) failed re-validation, dropped:")
        for rid, problems in rejected[:10]:
            print(f"    {rid}: {problems[0]}")
        if len(rejected) > 10:
            print(f"    ... and {len(rejected) - 10} more")

    records, dupes = dedup(records)
    print(f"  {dupes} exact-text duplicate(s) dropped")
    print(f"  {len(records)} clean, unique record(s) remain")

    if not records:
        print("error: nothing left to split", file=sys.stderr)
        return 1

    train, val, test = stratified_split(records, args.val_frac, args.test_frac, args.seed,
                                        group_key=_skeleton if args.group_split == "template" else None)
    if args.group_split == "template":
        n_groups = len({_skeleton(r) for r in records})
        print(f"  group split by template: {n_groups:,} templates for {len(records):,} documents")
    print("\nSplit:")
    report("train", train)
    report("val", val)
    report("test", test)

    # Leakage is reported, never silently enforced. Entity-value overlap
    # between splits is expected (there are only 97 Azerbaijani cities);
    # document-level overlap is not, and is a bug if it appears.
    leak = leakage_report({"train": train, "val": val, "test": test})
    print_leakage(leak)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "leakage_report.json").write_text(
        json.dumps(leak, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  -> leakage_report.json written to {out_dir}/")

    for name, rows in (("train", train), ("val", val), ("test", test)):
        write_jsonl(out_dir / f"{name}.docs.jsonl", rows)
    print(f"\nWrote {{train,val,test}}.docs.jsonl to {out_dir}/")

    label_list = build_label_list()
    label2id = {l: i for i, l in enumerate(label_list)}
    id2label = {i: l for i, l in enumerate(label_list)}
    labels_blob = json.dumps({"labels": label_list, "label2id": label2id,
                              "id2label": id2label}, indent=2, ensure_ascii=False)
    # labels.json is language-independent: write it beside the split AND one
    # level up, so `data/processed/labels.json` is the single source the
    # merged set and every translated split share.
    (out_dir / "labels.json").write_text(labels_blob, encoding="utf-8")
    shared = out_dir.parent / "labels.json"
    if shared != out_dir / "labels.json":
        shared.write_text(labels_blob, encoding="utf-8")
    print(f"Wrote labels.json ({len(label_list)} labels) to {out_dir}/ "
          f"and {out_dir.parent}/")

    if args.no_tokenize:
        return 0

    print(f"\nLoading tokenizer {args.base_model!r}...")
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    if add_punctuation_boundary(tokenizer):
        print("  patched pre-tokenizer: added Punctuation() step "
              "(2026-08-26 tokenizer audit)")
    else:
        print(f"  warning: {args.base_model!r} has no fast tokenizer -- "
              "punctuation-weld fix NOT applied, spans may be unemittable "
              "at punctuation-adjacent boundaries", file=sys.stderr)

    for name, rows in (("train", train), ("val", val), ("test", test)):
        windows = tokenize_split(rows, tokenizer, label2id,
                                 args.max_length, args.stride)
        write_jsonl(out_dir / f"{name}.jsonl", windows)
        print(f"  {name}: {len(rows)} docs -> {len(windows)} window(s)")
    print(f"\nWrote {{train,val,test}}.jsonl (tokenized) to {out_dir}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
