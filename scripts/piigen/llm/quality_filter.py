"""Final screening gate: one verdict per document, hard-reject semantics.

**A document that fails ANY check here is deleted in full.** Nothing is
repaired, trimmed or patched -- the same policy `pipeline.py` already applies
to its own rejections, for the same reason: a partially-fixed document is an
unverifiable document, and at 5,000-8,000 examples nobody will re-read them.

Why this exists on top of `validate.py` + `quality.py`
------------------------------------------------------
Those two already gate every document at generation time (offsets, checksums,
blocklist, language, repeat-mentions, leaked PII, taxonomy-label leak,
near-duplicates). Running them again would flag nothing -- verified against
the 1,000-document `llm_augmented_batch_colleague.jsonl` batch: 0 problems
from all four existing gates.

This module targets the class of defect those gates structurally cannot see:
**generation-harness artifacts and degenerate output shapes**. Both real bugs
this project has hit (the GIVENNAME/SURNAME gender mismatch and the taxonomy
label leak) were found by a human reading output, not by a validator -- and
each one silently entered the corpus first. This is the standing automated
version of that reading pass.

Every threshold below is derived from the real 1,000-document batch, not
invented, and is set deliberately OUTSIDE the observed range so a known-good
corpus passes untouched while genuine degeneracy is still caught. Measured
per-band figures (carrier words = words outside every entity span):

    band         n    carrier p1   median   density p95   density max
    very_short   91       3          10        39.2%        71.5%
    short       241      13          26        37.2%        65.6%
    medium      318      33          75        31.3%        50.2%
    long        234      96         200        16.9%        29.4%
    very_long    96     165         375        15.1%        20.4%
    extreme      20     301         447        10.1%        10.1%

False positives this module deliberately does NOT raise (each was a real
candidate rule, tested against the batch and rejected):

  * **Missing Azerbaijani diacritics.** 19/1000 documents contain no `ə/ğ/ş/...`
    at all -- every one of them carries `strip_diacritics` in `_noise`, applied
    on purpose by `NoiseInjector`. A "must contain Azerbaijani letters" rule
    would have deleted 19 good documents.
  * **Sentence ending without terminal punctuation.** 86/1000 -- almost all are
    letter signature blocks ("Hörmətlə,\nİnsan Resursları Komandası"), which is
    exactly how a real letter ends. Only 8 carried the "leave one sentence
    unfinished" directive; neither group is a defect.
  * **A phrase repeated 3+ times.** Both hits were markdown table rules
    (`| :--- | :--- |`) and `-----` dividers -- legitimate formatting, so the
    repetition check below ignores separator-only lines.
  * **The same string labeled differently across documents** (`"86"` as AGE in
    one document and BUILDINGNUM in another, `"Laçın"` as CITY and GIVENNAME).
    That is the taxonomy working as designed: those labels are
    `anchor_required`/`ml_context` tier precisely because context decides.
    Within a single document it would be a contradiction -- 0 occurrences,
    and `contradictory_label` below still guards it.
  * **Markdown fences.** 6/1000, all inside `api_documentation`/`onboarding_doc`
    where a fenced JSON payload is what a real document looks like. Only a
    fence wrapping the WHOLE document is treated as an artifact.

Usage
-----
As a library (this is what `pipeline.py` calls per document):

    from .quality_filter import screen_record
    problems = screen_record(record)      # [] means keep

As a CLI, to screen a file that already exists:

    python -m piigen.llm.quality_filter data/raw/batch.jsonl \\
        --out data/raw/batch.clean.jsonl \\
        --rejects data/raw/batch.rejects.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Importable both as a package module (`from .quality import ...`, the way
# pipeline.py uses it) and as a directly-executed script, which the relative
# form alone cannot support.
try:                                                       # package context
    from ..config import ENTITY_SET
    from ..resolver import find_unlabelled_planned
    from ..validate import declared_decoy_spans, minimal_context, validate_example
    from .quality import find_invented_pii, find_label_name_leak, find_leaked_pii
except ImportError:                                        # direct execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from piigen.config import ENTITY_SET
    from piigen.resolver import find_unlabelled_planned
    from piigen.validate import declared_decoy_spans, minimal_context, validate_example
    from piigen.llm.quality import find_invented_pii, find_label_name_leak, find_leaked_pii


# ---------------------------------------------------------------------------
# Thresholds -- all derived from the 1,000-document batch (see module docstring)
# ---------------------------------------------------------------------------

# Minimum words that must sit OUTSIDE every entity span. Below the measured p1
# for each band, so the known-good corpus passes and a value-dump does not.
# A document that is mostly PII with no prose around it teaches the model that
# entities appear without context, which production text never does.
MIN_CARRIER_WORDS = {
    "very_short": 3,     # measured p1 3
    "short": 8,          # measured p1 13
    "medium": 20,        # measured p1 33
    "long": 50,          # measured p1 96
    "very_long": 90,     # measured p1 165
    "extreme": 150,      # measured p1 301
}
DEFAULT_MIN_CARRIER = 3          # unknown/missing band -- stay permissive

# Maximum share of characters that may be inside entity spans. Above the
# measured maximum for each band. Long secrets (a 250-char ACCESS_TOKEN in a
# short log line) legitimately push this high, which is why the cap is loose
# for short bands and tight only where a high ratio cannot be innocent.
MAX_PII_DENSITY = {
    "very_short": 0.80,  # measured max 71.5%
    "short": 0.75,       # measured max 65.6%
    "medium": 0.60,      # measured max 50.2%
    "long": 0.45,        # measured max 29.4%
    "very_long": 0.35,   # measured max 20.4%
    "extreme": 0.25,     # measured max 10.1%
}
DEFAULT_MAX_DENSITY = 0.85

# Repetition thresholds.
#
# These are set against what a KNOWN-GOOD corpus actually does, because the
# first version of this rule rejected 4 good documents out of 1,000: a
# voicemail archive repeating "Müştəri: Ramazanov" across six separate
# messages, a fleet log repeating "Status: Tamamlandı." across eight vehicles,
# and two documents repeating markdown table rules. All four are realistic
# structured documents, not decoding loops.
#
# The distinction that actually separates the two: a decoding loop repeats
# PROSE. Structured documents repeat short field labels and table furniture.
# So both checks below only consider prose-bearing content, and the thresholds
# sit above the maximum any clean document reached (3 for lines, 2 for
# phrases).
MIN_REPEATED_LINE_CHARS = 40     # shorter than this is a field label, not prose
MIN_REPEATED_LINE_WORDS = 5      # real words (>=3 letters) required in the line
MAX_LINE_REPEATS = 5             # clean-corpus max was 3

PHRASE_WINDOW = 10
MIN_PHRASE_PROSE_WORDS = 6       # of the 10, this many must be real words
MAX_PHRASE_REPEATS = 4           # clean-corpus max was 2

# Words of >=3 letters -- the unit both repetition checks count to decide
# "is this prose or is this furniture".
_PROSE_WORD = re.compile(r"[^\W\d_]{3,}", re.UNICODE)

# DSPy / harness artifacts. These can never be part of a real document: they are
# the adapter's own field framing, or the prompt's internal field names, echoed
# into the output. One real occurrence in 1,000 (`[[ ## completed ]]`).
_ADAPTER_ARTIFACT = re.compile(r"\[\[\s*##.*?##?\s*\]\]|\[\[\s*##\s*completed\s*\]\]")

# Signature field names from dspy_generate.py's GenerateTrainingDocument. If one
# appears in the text, the model narrated its own brief instead of writing a
# document. Matched with word boundaries so ordinary prose cannot trip them.
_PROMPT_FIELD_LEAK = re.compile(
    r"\b(entities_to_embed|scenario_note|noise_directives|document_year"
    r"|tone_register|length_hint|doc_type)\b")

# Assistant-voice meta-commentary. Anchored to the document's opening so that
# ordinary in-document English (a log line, a quoted translation) cannot match:
# one document legitimately contains "I can't find anything" inside a parenthetical
# translation of its own Azerbaijani dev-note, and must not be rejected for it.
_META_OPENING = re.compile(
    r"^\s*(here is|here's|below is|sure[,!]|certainly[,!]|of course[,!]"
    r"|i (?:cannot|can't|won't|will not|am unable)"
    r"|as an ai|as a language model|i'm sorry|i apologize)\b",
    re.IGNORECASE)

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# ZWSP, ZWNJ, ZWJ, BOM/ZWNBSP. Legitimate OUTSIDE entity spans -- NoiseInjector
# deliberately adds these to simulate realistic copy/paste artifacts (335/347
# occurrences in the reference batch were exactly this, working as intended).
# INSIDE a labeled value they are never legitimate: no label in this taxonomy
# is meant to contain an invisible character, and one there makes the span's
# exact string silently inconsistent with the same value anywhere else it's
# matched against (a tokenizer, a downstream exact-match check). Found by
# audit: 3 real occurrences, all in STREET spans, growing over time -- not
# rare enough to ignore.
_ZERO_WIDTH = re.compile(r"[​‌‍﻿]")
_WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _entity_mask(text: str, entities: list[dict]) -> bytearray:
    mask = bytearray(len(text))
    for e in entities:
        start = max(0, int(e.get("start", 0)))
        end = min(len(text), int(e.get("end", 0)))
        for i in range(start, end):
            mask[i] = 1
    return mask


def carrier_word_count(text: str, entities: list[dict]) -> int:
    """Words that sit entirely outside every entity span.

    This is the honest measure of "is there a real document around the PII",
    and it is what raw length cannot tell you: a 400-character document that
    is one long API token plus four words is short on carrier text even though
    it looks long.
    """
    mask = _entity_mask(text, entities)
    n = 0
    for m in _WORD.finditer(text):
        if not any(mask[i] for i in range(m.start(), m.end())):
            n += 1
    return n


def pii_density(text: str, entities: list[dict]) -> float:
    if not text:
        return 0.0
    return sum(max(0, int(e.get("end", 0)) - int(e.get("start", 0)))
               for e in entities) / len(text)


# ---------------------------------------------------------------------------
# Individual checks -- each returns a list of problem strings (empty == pass)
# ---------------------------------------------------------------------------

def check_harness_artifacts(text: str) -> list[str]:
    """DSPy adapter framing or prompt field names echoed into the document."""
    problems = []
    for m in set(_ADAPTER_ARTIFACT.findall(text)):
        problems.append(f"adapter artifact in text: {m[:40]!r}")
    leaked = sorted(set(_PROMPT_FIELD_LEAK.findall(text)))
    if leaked:
        problems.append(f"prompt field name(s) in text: {leaked}")
    if _META_OPENING.search(text):
        problems.append("document opens with assistant-voice meta-commentary")
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        problems.append("entire document wrapped in a markdown fence")
    return problems


def check_structure(text: str) -> list[str]:
    """Malformed output shapes: control characters, unbalanced blocks."""
    problems = []
    if not text or not text.strip():
        problems.append("empty document")
        return problems
    if _CONTROL_CHARS.search(text):
        problems.append("control characters in text")
    if text.count("```") % 2:
        problems.append("unbalanced markdown fence")
    begins, ends = text.count("-----BEGIN"), text.count("-----END")
    if begins != ends:
        problems.append(f"unbalanced PEM block ({begins} BEGIN / {ends} END)")
    return problems


def check_zero_width_in_spans(text: str, entities: list[dict]) -> list[str]:
    """A zero-width character sitting inside an entity's own span.

    See _ZERO_WIDTH's comment for why this only checks span text, not the
    document as a whole -- the same characters are expected and fine in
    ordinary carrier text.
    """
    problems = []
    for e in entities:
        val = e.get("text", "")
        if _ZERO_WIDTH.search(val):
            problems.append(
                f"{e.get('label')}: zero-width character inside entity span "
                f"({val!r})")
    return problems


def check_repetition(text: str) -> list[str]:
    """Decoding loops -- prose repeated verbatim.

    Only prose counts. A structured document legitimately repeats a field
    label on every record ("Status: Tamamlandı." once per vehicle) and a table
    rule once per table; treating either as a loop deletes good data, which is
    exactly what the first version of this check did. See the threshold block
    above for the measured basis.
    """
    problems = []

    lines = [l.strip() for l in text.split("\n")
             if len(l.strip()) >= MIN_REPEATED_LINE_CHARS
             and len(_PROSE_WORD.findall(l)) >= MIN_REPEATED_LINE_WORDS]
    if lines:
        line, n = Counter(lines).most_common(1)[0]
        if n >= MAX_LINE_REPEATS:
            problems.append(f"prose line repeated {n}x: {line[:50]!r}")

    words = text.split()
    if len(words) >= 4 * PHRASE_WINDOW:
        grams = Counter()
        for i in range(len(words) - PHRASE_WINDOW + 1):
            gram = " ".join(words[i:i + PHRASE_WINDOW])
            if len(_PROSE_WORD.findall(gram)) >= MIN_PHRASE_PROSE_WORDS:
                grams[gram] += 1
        if grams:
            gram, n = grams.most_common(1)[0]
            if n >= MAX_PHRASE_REPEATS:
                problems.append(
                    f"{PHRASE_WINDOW}-word prose phrase repeated {n}x: {gram[:50]!r}")
    return problems


def check_shape(text: str, entities: list[dict], band: str | None) -> list[str]:
    """Is there a real document around the PII, or is this a value dump?"""
    problems = []
    min_carrier = MIN_CARRIER_WORDS.get(band or "", DEFAULT_MIN_CARRIER)
    carrier = carrier_word_count(text, entities)
    if carrier < min_carrier:
        problems.append(
            f"only {carrier} carrier word(s) outside entity spans "
            f"(band {band!r} requires >= {min_carrier})")

    max_density = MAX_PII_DENSITY.get(band or "", DEFAULT_MAX_DENSITY)
    density = pii_density(text, entities)
    if density > max_density:
        problems.append(
            f"PII character density {density:.1%} exceeds the "
            f"{max_density:.0%} cap for band {band!r}")
    return problems


def check_unlabeled_planned_pii(text: str, entities: list[dict],
                                planned: list[tuple[str, str]],
                                decoy_spans=()) -> list[str]:
    """A planned PII value that made it into the text verbatim but was never
    resolved into any entity span -- real, unmasked PII sitting in accepted
    training data, exactly the failure mode the true-positive-only policy
    exists to prevent.

    Found by direct inspection, not theory: 35 confirmed instances across the
    1,000-doc reference batch plus the two comparison batches (1,100 documents
    total), 18 of them TIME. Root cause traced to `resolver.py`'s own
    documented gap: `_is_word_boundary` treats a hyphen followed by a letter as
    "continuing the token" (correct for phone/IBAN digit grouping), so an
    Azerbaijani grammatical suffix attached right after a value with a hyphen
    -- "10:17-də", "11:32 PM-dir" -- makes the resolver discard a real,
    present, verbatim match as "inside a longer token." The resolver docstring
    already names this exact gap ("Known gap, not fixed here... needs a
    deliberate AZ-morphology rule") and it is not fixed there by this module --
    that is core logic shared by every label, and deserves its own change with
    its own regression tests, not a quick patch here. This check exists so the
    gap cannot silently reach the dataset in the meantime.

    An occurrence lying entirely inside a declared decoy span (`decoy_spans`,
    C2 `_decoys`) is not the planned value: it is part of a look-alike we
    planted on purpose (a planned AGE `34` inside the decoy `REF340012`, the
    planned CITY `Bakı` inside the policy decoy `Bakı layihəsi`).

    P2-6 (batch 1, 2026-10-03): the check is now per occurrence and covers
    every form the LLM writes (`resolver.find_unlabelled_planned`). Both of
    the old rule's failures were measured on batch 1:
      * it compared the planned value with the entity TEXTS, so a value
        labelled only in an inflected form (`Şamaxıda`) counted as "never
        labeled" -- 1,707 of 11,015 API calls rejected a correct document;
      * it looked only for the verbatim value, so `Vaqif Məmmədov küçəsində`
        for `küç.`, `İsağın`, capitals or folded letters, and a second
        unlabelled occurrence of a value labelled once all passed.
    The verbatim rule itself is kept (see find_unlabelled_planned).
    """
    if not planned:
        return []
    problems = []
    for f in find_unlabelled_planned(text, entities, planned, decoy_spans):
        # "planned value never labeled (LABEL, kind): ..." -- the part before
        # the first colon is what pipeline.py keeps as the rejection reason,
        # so it names the label and the form; TIME values carry their own
        # colon, which is why the value comes after it
        problems.append(
            f"planned value never labeled ({f['label']}, {f['kind']}): "
            f"{f['value']!r} written {f['text']!r}")
    return problems


def check_entity_consistency(text: str, entities: list[dict]) -> list[str]:
    """Contradictions inside ONE document.

    Deliberately not applied across documents: a bare "86" really is an AGE in
    one document and a BUILDINGNUM in another, and "Laçın" really is both a
    city and a given name -- that ambiguity is what the anchor_required and
    ml_context detection tiers exist for. Inside a single document, though, the
    same string carrying two labels is an unresolvable contradiction.
    """
    problems = []
    by_value: dict[str, set] = defaultdict(set)
    for e in entities:
        by_value[e.get("text", "")].add(e.get("label"))
    for value, labels in by_value.items():
        if len(labels) > 1:
            problems.append(
                f"{value[:30]!r} labeled as both {sorted(labels)} in one document")

    for e in entities:
        label = e.get("label")
        if label not in ENTITY_SET:
            problems.append(f"unknown label {label!r}")
    return problems


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def screen_record(record: dict, *, run_base_gates: bool = True,
                  band: str | None = None,
                  planned: list[tuple[str, str]] | None = None,
                  invented: bool = False, doc_type: str | None = None) -> list[str]:
    """Every reason this document should be deleted. Empty list == keep it.

    `run_base_gates` re-runs `validate_example` / `find_leaked_pii` /
    `find_label_name_leak`. Leave it on when screening a file after the fact
    (the file may predate a gate, exactly as the pre-fix batches did); turn it
    off inside `pipeline.py`, where those three have already run on this very
    document and re-running them is pure duplicated work.

    `band` overrides the length band read from the record. `pipeline.py` needs
    this because it screens before `_bucket` has been written onto the record,
    and the shape thresholds are meaningless without the band.

    `planned` is the [(label, value), ...] this document was ASKED to embed.
    `pipeline.py` passes `spec.entities` directly, because at the point it
    calls this the record does not have `_spec` written onto it yet (that
    happens later in `assemble_document`). Screening a file after the fact
    falls back to the record's own `_spec.entities`, which is present there.

    `invented` (D-15c, P2-6 batch 2): also reject PII the model added on its
    own -- a city, street, building number or full name nobody planned, so
    nobody labelled (`quality.find_invented_pii`), and a standalone date
    nobody planned (D-17, `standalone_dates`). pipeline.py turns it on for
    LLM documents; the targeted builder writes only labelled values.
    """
    text = record.get("text") or ""
    entities = record.get("entities") or []
    band = band or record.get("_bucket") or record.get("_spec", {}).get("band")
    if planned is None:
        planned = [(e.get("label"), e.get("value"))
                  for e in record.get("_spec", {}).get("entities", [])]

    problems: list[str] = []
    problems += check_structure(text)
    if "empty document" in problems:
        return problems

    problems += check_harness_artifacts(text)
    problems += check_repetition(text)
    # a declared minimal-context document (P2-4d) is a name with almost no
    # text around it on purpose: the shape check cannot apply to it
    if not minimal_context(record):
        problems += check_shape(text, entities, band)
    problems += check_entity_consistency(text, entities)
    # The record's own declared decoys (C2 `_decoys`, P2-3): every gate here
    # exempts exactly those spans, and nothing else.
    decoy_spans, _ = declared_decoy_spans(record)
    problems += check_unlabeled_planned_pii(text, entities, planned, decoy_spans)
    if invented:
        problems += [f"invented PII ({f['label']}): {f['text']!r}"
                     for f in find_invented_pii(text, entities, decoy_spans,
                                                doc_type or record.get("_doc_type"))]
        # D-17: every standalone date is DATE. One the brief did not plan is
        # unlabelled by construction, so it is rejected the same way.
        from ..standalone_dates import find_unlabelled_dates
        problems += [f"unlabelled date (D-17): {f['text']!r}"
                     for f in find_unlabelled_dates(text, entities, decoy_spans)]
    problems += check_zero_width_in_spans(text, entities)

    if run_base_gates:
        problems += [f"validation: {p}" for p in validate_example(record)]
        problems += [f"leaked PII: {p}" for p in
                     find_leaked_pii(text, entities, decoy_spans=decoy_spans)]
        problems += [f"label leak: {p}" for p in find_label_name_leak(text, entities)]

    return problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _reason_key(problem: str) -> str:
    return problem.split(":")[0].split("(")[0].strip()


def run_cli(args: argparse.Namespace) -> int:
    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: {src} does not exist", file=sys.stderr)
        return 1

    rows = []
    for lineno, line in enumerate(src.open(encoding="utf-8"), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(f"ERROR: {src}:{lineno} is not valid JSON: {exc}", file=sys.stderr)
            return 1

    kept, dropped = [], []
    for r in rows:
        problems = screen_record(r, run_base_gates=not args.no_base_gates)
        if problems:
            dropped.append((r, problems))
        else:
            kept.append(r)

    print(f"screened {len(rows)} document(s) from {src}")
    print(f"  kept    : {len(kept)} ({len(kept)/max(1,len(rows)):.1%})")
    print(f"  deleted : {len(dropped)} ({len(dropped)/max(1,len(rows)):.1%})")
    if dropped:
        counts = Counter(_reason_key(p) for _, ps in dropped for p in ps)
        print("\nreasons (a document may fail more than one):")
        for reason, n in counts.most_common():
            print(f"  {n:5d}  {reason}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for r in kept:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nclean -> {out}")

    if args.rejects and dropped:
        rej = Path(args.rejects)
        rej.parent.mkdir(parents=True, exist_ok=True)
        with rej.open("w", encoding="utf-8") as fh:
            for r, problems in dropped:
                fh.write(json.dumps(
                    {"id": r.get("id"), "problems": problems,
                     "doc_type": r.get("_doc_type"), "band": r.get("_bucket"),
                     "text": r.get("text", "")[:4000]},
                    ensure_ascii=False) + "\n")
        print(f"rejects -> {rej}")

    if args.fail_over and len(dropped) / max(1, len(rows)) > args.fail_over:
        print(f"\nFAIL: rejection rate exceeds --fail-over {args.fail_over:.0%}",
              file=sys.stderr)
        return 2
    return 0


def main() -> None:
    # A rejection reason routinely contains the actual Azerbaijani value that
    # triggered it (a SURNAME, a CITY name) -- printing it crashes outright on
    # Windows consoles whose codepage isn't UTF-8 (cp1251/cp1252), which is
    # this project's default terminal. `errors="replace"` degrades to `?` for
    # the rare truly unprintable glyph instead of losing the whole run's
    # summary output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="JSONL file to screen")
    p.add_argument("--out", help="write surviving documents here")
    p.add_argument("--rejects", help="write deleted documents + reasons here")
    p.add_argument("--no-base-gates", action="store_true",
                   help="skip validate_example/leaked-PII/label-leak (they already "
                        "ran at generation time; on by default for standalone files)")
    p.add_argument("--fail-over", type=float, default=None, metavar="RATE",
                   help="exit non-zero if the rejection rate exceeds this "
                        "(e.g. 0.10) -- for unattended large-scale runs")
    raise SystemExit(run_cli(p.parse_args()))


if __name__ == "__main__":
    main()
