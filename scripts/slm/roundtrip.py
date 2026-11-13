"""Task 2.1's round-trip check: gold spans -> generated lines -> grounding -> spans.

A document is usable by every arm only if its gold spans survive this round
trip exactly; the export drops the ones that don't, from all arms
(task 2.1).

`ground` implements the grounding algorithm of the plan's section 4:

  1. parse each line strictly (LABEL<TAB>value, LABEL one of the 27);
  2. search from the cursor, then from the start of the text, in three tiers:
       (1) exact match, with a word boundary wherever the value's own edge
           is a letter or digit;
       (2) exact match without the boundary;
       (3) a length-preserving fold with an index map back to the original
           text: İ/I/ı/i -> i, ə -> e, ş ç ğ ö ü -> ASCII, lower-case one
           character at a time, zero-width characters dropped, whitespace
           runs collapsed. Never `lower()` on a whole text;
  3. claim one span per line, skipping occurrences already claimed.

The team owns the production grounder (model/grounding.py, task 4.1). This is
the export's own copy of the same algorithm, used only to choose training
documents; once 4.1 lands, re-run the check with it and the two must agree.

Values that contain a line break cannot sit on one LABEL<TAB>value line. They
are written with each line-break-containing whitespace run replaced by one
space (`render_value`), which tier 3 maps back to the exact original span.
61% of PRIVATE_KEY values are multi-line PEM blocks, so dropping them instead
would take most private keys out of every arm.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from piigen.config import ENTITY_TYPES  # noqa: E402

LABELS = frozenset(ENTITY_TYPES)
SYSTEM_PROMPT = ("PII extraction. For each personal-data value in the text, in order of "
                 "appearance, output one line: LABEL<TAB>exact text copied from the input. "
                 "Output NONE if there is none.")
NONE = "NONE"

_LINE_BREAK_RUN = re.compile(r"\s*[\r\n  ]\s*")
_ZERO_WIDTH = frozenset("​‌‍⁠﻿")
_FOLD = {"İ": "i", "I": "i", "ı": "i", "ə": "e", "Ə": "e", "ş": "s", "Ş": "s",
         "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ö": "o", "Ö": "o", "ü": "u", "Ü": "u"}


def render_value(value: str) -> str:
    """A gold value as it appears on its generated line."""
    return _LINE_BREAK_RUN.sub(" ", value)


def to_lines(text: str, entities: list[dict]) -> list[tuple[str, str]]:
    """Gold spans as (label, value) lines, in order of appearance, every occurrence."""
    return [(e["label"], render_value(text[e["start"]:e["end"]]))
            for e in sorted(entities, key=lambda e: (e["start"], e["end"]))]


def completion(text: str, entities: list[dict]) -> str:
    lines = to_lines(text, entities)
    return "\n".join(f"{lab}\t{val}" for lab, val in lines) if lines else NONE


def parse(output: str) -> tuple[list[tuple[str, str]], int]:
    """Strict parse: (lines, rejected). `NONE` alone means no PII."""
    if output.strip() == NONE:
        return [], 0
    lines, rejected = [], 0
    for raw in output.split("\n"):
        lab, sep, val = raw.partition("\t")
        if not sep or lab not in LABELS or not val:
            rejected += 1
            continue
        lines.append((lab, val))
    return lines, rejected


def fold(s: str) -> tuple[str, list[int]]:
    """Folded string plus, for each folded character, its index in `s`."""
    out, index, prev_space = [], [], False
    for i, c in enumerate(s):
        if c in _ZERO_WIDTH:
            continue
        if c.isspace():
            if not prev_space:
                out.append(" ")
                index.append(i)
            prev_space = True
            continue
        prev_space = False
        f = _FOLD.get(c)
        if f is None:
            low = c.lower()
            f = low if len(low) == 1 else c
        out.append(f)
        index.append(i)
    return "".join(out), index


def _boundary_ok(text: str, start: int, end: int, value: str) -> bool:
    if value[0].isalnum() and start > 0 and text[start - 1].isalnum():
        return False
    if value[-1].isalnum() and end < len(text) and text[end].isalnum():
        return False
    return True


def _free(span: tuple[int, int], claimed: list[tuple[int, int]]) -> bool:
    return not any(span[0] < c[1] and c[0] < span[1] for c in claimed)


def _find_exact(text, value, origin, claimed, boundary):
    i = text.find(value, origin)
    while i >= 0:
        span = (i, i + len(value))
        if _free(span, claimed) and (not boundary or _boundary_ok(text, *span, value)):
            return span
        i = text.find(value, i + 1)
    return None


def _find_folded(folded, index, fvalue, origin, claimed):
    # origin is a position in the original text; start at the first folded
    # character at or after it
    lo = next((k for k, j in enumerate(index) if j >= origin), len(index))
    k = folded.find(fvalue, lo)
    while k >= 0:
        span = (index[k], index[k + len(fvalue) - 1] + 1)
        if _free(span, claimed):
            return span
        k = folded.find(fvalue, k + 1)
    return None


def ground(text: str, lines: list[tuple[str, str]]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Grounded spans (with the tier that found each) and the lines not found."""
    cursor, claimed, found, missing = 0, [], [], []
    folded = None
    for lab, val in lines:
        span, tier = None, 0
        for tier, origin in ((1, cursor), (1, 0), (2, cursor), (2, 0)):
            span = _find_exact(text, val, origin, claimed, boundary=(tier == 1))
            if span:
                break
        if span is None:
            if folded is None:
                folded = fold(text)
            fval = fold(val)[0]
            if fval:
                for origin in (cursor, 0):
                    span = _find_folded(*folded, fval, origin, claimed)
                    if span:
                        tier = 3
                        break
        if span is None:
            missing.append((lab, val))
            continue
        claimed.append(span)
        found.append({"start": span[0], "end": span[1], "label": lab, "tier": tier})
        cursor = span[1]
    return found, missing


def round_trip(text: str, entities: list[dict]) -> tuple[bool, str]:
    """(ok, reason). ok means grounding the doc's own lines returns its gold spans exactly."""
    lines, rejected = parse(completion(text, entities))
    if rejected:
        return False, "unparseable line"
    found, missing = ground(text, lines)
    if missing:
        return False, "ungroundable"
    gold = {(e["start"], e["end"], e["label"]) for e in entities}
    got = {(f["start"], f["end"], f["label"]) for f in found}
    if got != gold or len(found) != len(entities):
        return False, "grounded to another occurrence"
    return True, "ok"
