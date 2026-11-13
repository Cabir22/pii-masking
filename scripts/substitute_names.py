# -*- coding: utf-8 -*-
"""Substitute PII names in merged corpus with 60/40 native/foreign split.

For each document:
  - Determine language from its labels
  - 60% (or 60-70%): use native-language names
  - 40% (or 30-40%): use names from another language, transliterated
  - Maintain repeat-mention consistency (same person gets same new name)
  - Preserve gender for gendered given names
  - Recompute entity byte offsets after substitution

Usage:
    python scripts/substitute_names.py [--splits train val test] [--native-pct 60]
    python scripts/substitute_names.py --split train --dry-run  # preview only
"""

from __future__ import annotations
import argparse
import json
import random
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

# Ensure scripts/ is in path for imports
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from name_pools import load_all_pools, NameEntry
from name_transliterators import transliterate


# ============================================================================
# Globals and Configuration
# ============================================================================

LANGUAGES = ["az", "en", "ru", "tr"]
DOCUMENT_LANGS = {
    "az": "az",
    "en": "en",
    "ru": "ru",
    "tr": "tr",
}

# Entity labels that are names
NAME_LABELS = {"GIVENNAME", "SURNAME"}


# ============================================================================
# Name Sampling
# ============================================================================

class NameSampler:
    """Sample names from pools with dampened frequency-weighted selection.

    Sampling weight is ``count ** weight_exponent``. The registries differ
    wildly in how steep their counts are -- AZ/EN given names carry no counts
    (weight 1.0, so the exponent is a no-op), while the RU sorokinpf list is
    census-steep (Александр alone is ~5% of raw mass). ``weight_exponent=0.5``
    (the default) square-root-dampens that: common names stay modestly more
    common, but the tail keeps enough mass that ~90% of RU given-name draws
    span ~3,000 names instead of ~107. Pass 1.0 for raw frequency, 0.0 for
    uniform.
    """

    def __init__(self, pools: dict[str, dict[str, list[NameEntry]]],
                 weight_exponent: float = 0.5):
        self.pools = pools
        # Dampening applies to GIVEN names only: the RU/TR given registries are
        # census-steep (Александр ~5% of raw mass) while surname registries are
        # already well-spread (top-15 <= 7%), and keeping raw surname frequency
        # preserves the realism of common surnames (Smith, Yılmaz).
        self.given_exponent = weight_exponent
        self.rng = random.Random(42)  # fixed seed for reproducibility
        # (names, cumulative_weights) per lookup key -- built once, reused for
        # every draw, so the 150k-element weight list is never rebuilt per call.
        self._cache: dict[str, tuple[list[str], list[float]]] = {}

    def _table(self, key: str, entries: list[NameEntry], exponent: float):
        cached = self._cache.get(key)
        if cached is None:
            names = [x.name for x in entries]
            if exponent == 1.0:
                weights = [float(x.count) for x in entries]
            elif exponent == 0.0:
                weights = [1.0] * len(entries)
            else:
                weights = [max(x.count, 0.0) ** exponent for x in entries]
            cum: list[float] = []
            running = 0.0
            for w in weights:
                running += w
                cum.append(running)
            cached = (names, cum)
            self._cache[key] = cached
        return cached

    def sample_given_name(self, lang: str, gender: str | None = None) -> str:
        """Sample a given name from the pool for a language/gender."""
        pool = self.pools.get(lang, {})
        if gender == "M":
            key, candidates = f"g:{lang}:M", pool.get("given_names_m", [])
        elif gender == "F":
            key, candidates = f"g:{lang}:F", pool.get("given_names_f", [])
        else:
            key = f"g:{lang}:*"
            candidates = pool.get("given_names_m", []) + pool.get("given_names_f", [])

        if not candidates:
            raise ValueError(f"empty given-name pool for lang={lang!r} gender={gender!r}")

        names, cum = self._table(key, candidates, self.given_exponent)
        return names[self.rng.choices(range(len(names)), cum_weights=cum, k=1)[0]]

    def sample_surname(self, lang: str) -> str:
        """Sample a surname from the pool for a language (raw frequency)."""
        candidates = self.pools.get(lang, {}).get("surnames", [])
        if not candidates:
            raise ValueError(f"empty surname pool for lang={lang!r}")

        names, cum = self._table(f"s:{lang}", candidates, 1.0)
        return names[self.rng.choices(range(len(names)), cum_weights=cum, k=1)[0]]


# ============================================================================
# Entity Substitution
# ============================================================================

def substitute_entity(
    doc: dict[str, Any],
    entity_idx: int,
    new_value: str,
    source_lang: str,
    target_lang: str,
) -> None:
    """Substitute an entity's value and recompute offsets.

    Args:
        doc: document dict with "entities" and "text"
        entity_idx: index in entities list
        new_value: the replacement value
        source_lang: language of the new value's native orthography
        target_lang: language of the document
    """
    entity = doc["entities"][entity_idx]
    text = doc["text"]
    start = entity["start"]
    end = entity["end"]
    old_value = text[start:end]

    # Transliterate if needed
    if source_lang != target_lang:
        # Determine target script from target language
        target_script = "cyrillic" if target_lang == "ru" else "latin"
        new_value = transliterate(new_value, source_lang, target_script)

    # Build new text with replacement
    new_text = text[:start] + new_value + text[end:]

    # Compute character-level offset change (offsets are character positions, not bytes)
    char_delta = len(new_value) - len(old_value)

    # Update this entity's end offset
    entity["end"] = start + len(new_value)

    # Update offsets of all subsequent entities
    for i in range(entity_idx + 1, len(doc["entities"])):
        if doc["entities"][i]["start"] >= end:
            doc["entities"][i]["start"] += char_delta
            doc["entities"][i]["end"] += char_delta

    doc["text"] = new_text


def get_doc_language(doc: dict[str, Any]) -> str:
    """Return the document's carrier language.

    The merged corpus stamps every record with a top-level ``lang`` field
    ("az" | "en" | "ru" | "tr"); that is authoritative. Fall back to parsing
    a ``LANG_`` prefix off the first entity label, then to "az".
    """
    lang = (doc.get("lang") or "").strip().lower()
    if lang in LANGUAGES:
        return lang

    entities = doc.get("entities", [])
    if entities:
        label = entities[0].get("label", "")
        for code in LANGUAGES:
            if label.startswith(code.upper() + "_"):
                return code

    return "az"


def substitute_names_in_doc(
    doc: dict[str, Any],
    sampler: NameSampler,
    native_pct: int = 60,
) -> dict[str, Any]:
    """Substitute names in a document with native/foreign 60/40 split.

    Args:
        doc: document dict
        sampler: NameSampler instance
        native_pct: percentage of docs using native language (default 60)

    Returns:
        Modified document dict
    """
    doc_lang = get_doc_language(doc)

    # Roll 60/40 (or native_pct / (100-native_pct))
    use_native = random.random() < (native_pct / 100.0)

    # Track replacements per (label, old_value) for repeat-mention consistency
    replacements: dict[tuple[str, str], tuple[str, str]] = {}  # (label, old_value) -> (new_value, sample_lang)

    # Process entities in reverse order so offsets stay valid
    for i in range(len(doc.get("entities", [])) - 1, -1, -1):
        entity = doc["entities"][i]
        label = entity.get("label", "")
        text = doc["text"]
        start = entity.get("start", 0)
        end = entity.get("end", 0)
        old_value = text[start:end] if start < len(text) else ""

        # Only substitute names
        if not any(name_label in label for name_label in NAME_LABELS):
            continue

        # Build key for repeat-mention tracking
        key = (label, old_value)

        # Check if we've already replaced this entity before
        if key in replacements:
            new_value, sample_lang = replacements[key]
        else:
            # Determine which language to sample from
            if use_native:
                sample_lang = doc_lang
            else:
                # Pick a random other language
                other_langs = [l for l in LANGUAGES if l != doc_lang]
                sample_lang = random.choice(other_langs)

            # Determine gender if it's a GIVENNAME
            gender = None
            if "GIVENNAME" in label:
                # Try to infer gender from label suffix (e.g., GIVENNAME_M)
                if "_M" in label:
                    gender = "M"
                elif "_F" in label:
                    gender = "F"

            # Sample the new name
            if "GIVENNAME" in label:
                new_value = sampler.sample_given_name(sample_lang, gender)
            elif "SURNAME" in label:
                new_value = sampler.sample_surname(sample_lang)
            else:
                new_value = old_value

            # Cache the replacement
            replacements[key] = (new_value, sample_lang)

        # Substitute in document
        substitute_entity(doc, i, new_value, sample_lang, doc_lang)

    # Normalize text to NFC
    doc["text"] = unicodedata.normalize("NFC", doc["text"])

    return doc


# ============================================================================
# Main Pipeline
# ============================================================================

def substitute_split(
    split_name: str,
    sampler: NameSampler,
    native_pct: int = 60,
    dry_run: bool = False,
) -> None:
    """Process one split (train/val/test).

    Args:
        split_name: "train", "val", or "test"
        sampler: NameSampler instance
        native_pct: percentage using native language
        dry_run: if True, only process first 10 docs and print, don't write
    """
    docs_path = Path(f"data/processed/merged_rebalanced/{split_name}.docs.jsonl")
    if not docs_path.exists():
        print(f"ERROR: {docs_path} not found", file=sys.stderr)
        return

    print(f"\nProcessing {split_name}...", file=sys.stderr)

    processed = []
    with open(docs_path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                doc = json.loads(line)
                doc = substitute_names_in_doc(doc, sampler, native_pct)
                processed.append(doc)

                if dry_run and line_no >= 10:
                    break

                if line_no % 50000 == 0:
                    print(f"  {line_no:,} docs processed...", file=sys.stderr)

    print(f"  Total: {len(processed):,} docs", file=sys.stderr)

    if dry_run:
        import io
        # Use utf-8 for output to handle all characters
        utf8_out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        utf8_out.write("\n--- DRY RUN: First 3 docs ---\n")
        for i, doc in enumerate(processed[:3]):
            text = doc['text']
            utf8_out.write(f"\nDoc {i+1}:\n")
            utf8_out.write(f"  Text: {text[:100]}...\n")
            utf8_out.write(f"  Entities: {len(doc['entities'])}\n")
            for ent in doc["entities"][:3]:
                start, end = ent.get("start"), ent.get("end")
                value = text[start:end] if start and end else "[N/A]"
                utf8_out.write(f"    {ent['label']}: {value}\n")
        utf8_out.flush()
    else:
        # Write back to same file
        with open(docs_path, "w", encoding="utf-8") as f:
            for doc in processed:
                f.write(json.dumps(doc, ensure_ascii=False) + "\n")
        print(f"  Written to {docs_path}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Substitute PII names with 60/40 native/foreign split"
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=["train", "val", "test"],
        choices=["train", "val", "test"],
        help="Which splits to process (default: all three)"
    )
    parser.add_argument(
        "--native-pct",
        type=int,
        default=60,
        help="Percentage of documents using native language (default: 60)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--weight-exponent",
        type=float,
        default=0.5,
        help="Frequency-weight dampening: sampling weight = count ** this. "
             "0.5 (default) sqrt-dampens census-steep pools; 1.0 = raw "
             "frequency; 0.0 = uniform. No-op for count-less AZ/EN given names."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process first 10 docs only, print results, don't write"
    )

    args = parser.parse_args()

    random.seed(args.seed)

    print("Loading name pools...", file=sys.stderr)
    pools = load_all_pools()
    sampler = NameSampler(pools, weight_exponent=args.weight_exponent)
    print(f"weight_exponent = {args.weight_exponent}", file=sys.stderr)

    print(f"Pools loaded: {list(pools.keys())}", file=sys.stderr)
    MIN_POOL = 50
    problems = []
    for lang in LANGUAGES:
        pool = pools.get(lang, {})
        m = len(pool.get("given_names_m", []))
        f = len(pool.get("given_names_f", []))
        s = len(pool.get("surnames", []))
        print(f"  {lang}: {m}M + {f}F given, {s} surnames", file=sys.stderr)
        for slot, n in (("given_names_m", m), ("given_names_f", f), ("surnames", s)):
            if n < MIN_POOL:
                problems.append(f"{lang}.{slot} has only {n} entries (min {MIN_POOL})")
    if problems:
        for p in problems:
            print(f"  ABORT: {p}", file=sys.stderr)
        sys.exit(1)

    for split in args.splits:
        substitute_split(split, sampler, args.native_pct, args.dry_run)

    print(f"\nDone!" if not args.dry_run else "\nDry run complete!", file=sys.stderr)


if __name__ == "__main__":
    main()
