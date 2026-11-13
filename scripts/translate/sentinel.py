"""Placeholder slotting -- the core of the translation harness.

An entity value is cut out of the source text and replaced with a numbered
sentinel BEFORE translation, then a fresh value is spliced back in AFTER.
The model never sees PII, and the harness never has to guess where a span
moved to -- offsets are recomputed at splice time from the position the
value was inserted at.

Sentinel is U+27E6 / U+27E7 (mathematical white square brackets): essentially
absent from natural az/en/tr/ru text so the extraction regex cannot
false-match, rare enough that an LLM treats it as opaque, and the digit
inside stays plain ASCII.
"""
from __future__ import annotations

import re

OPEN, CLOSE = "⟦", "⟧"          # ⟦ ⟧

# Strict: the exact form the sentinelizer emits.
SENTINEL_RE = re.compile(OPEN + r"(\d+)" + CLOSE)
# Lenient: catches an LLM that added inner spaces or dropped one bracket, so
# the round-trip validator can report "mangled" rather than "missing".
SENTINEL_LENIENT_RE = re.compile(
    r"[" + OPEN + r"\[]\s*(\d+)\s*[" + CLOSE + r"\]]|" + OPEN + r"\s*(\d+)\s*(?![" + CLOSE + r"])"
)


class SlotError(RuntimeError):
    """The sentinel set did not survive translation intact."""


def entity_source_values(text: str, entities: list[dict]) -> list[str]:
    """Source substring for each entity, in the same left-to-right order
    ``sentinelize`` assigns slots in -- so ``entity_source_values(...)[i]``
    is exactly the text slot ``i`` replaced. Used to detect repeat mentions:
    two slots with the same label and the same source value are the same
    underlying fact stated twice, and must mint to the same fresh value.
    """
    ents = sorted(entities, key=lambda e: (e["start"], e["end"]))
    return [text[e["start"]:e["end"]] for e in ents]


def sentinelize(text: str, entities: list[dict]) -> tuple[str, list[str]]:
    """Replace every entity span with ``⟦i⟧``.

    Returns the templated text and a positional list of labels: ``labels[i]``
    is the label that belonged in ``⟦i⟧``. Entities are taken left to right;
    they must not overlap (schema guarantee).
    """
    ents = sorted(entities, key=lambda e: (e["start"], e["end"]))
    out: list[str] = []
    labels: list[str] = []
    cursor = 0
    for i, e in enumerate(ents):
        s, t = e["start"], e["end"]
        if s < cursor:
            raise SlotError(f"overlapping entities at {s} (cursor {cursor})")
        out.append(text[cursor:s])
        out.append(f"{OPEN}{i}{CLOSE}")
        labels.append(e["label"])
        cursor = t
    out.append(text[cursor:])
    return "".join(out), labels


def decoy_spans(text: str, decoys: list[str],
                taken: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    """Every occurrence of each decoy string, minus anything overlapping an
    already-claimed span.

    Decoys (`_spec.hard_negatives`) are PII-SHAPED ON PURPOSE -- an order id
    that looks like an AZ_FIN, an IP with an out-of-range octet, a non-Luhn
    card number. Their exact broken shape IS the training signal, so they
    have to survive translation byte-for-byte, which means sentinelizing
    them exactly like real entities. Negative records carry `entities: []`,
    so without this they were handed to the model as raw text -- and 2.1% of
    them came back with a decoy reformatted or dropped on the English track.

    Longest-first so a decoy that contains another (an id inside a URL)
    claims the region before its substring can.
    """
    claimed = list(taken)
    out: list[tuple[int, int, str]] = []
    for decoy in sorted({d for d in decoys if d}, key=len, reverse=True):
        start = 0
        while True:
            i = text.find(decoy, start)
            if i < 0:
                break
            j = i + len(decoy)
            if not any(i < ce and cs < j for cs, ce in claimed):
                claimed.append((i, j))
                out.append((i, j, decoy))
            start = i + 1
    return out


SHADOW_MIN_LEN = 4


def sentinelize_protected(text: str, entities: list[dict],
                          decoys: list[str] | None = None,
                          decoy_ranges: list[tuple[int, int]] | None = None):
    """Sentinelize entities, their untagged repeat occurrences, and decoys.

    Returns (templated, slots) where each slot is
    ``{"kind": "entity"|"shadow"|"decoy", "label": str|None, "value": str}``
    in slot order:

      * ``entity`` -- re-minted after translation and emitted as an entity;
      * ``shadow`` -- another occurrence of a tagged value that carries no
        span of its own. The Azerbaijani corpus leaves these untagged by
        policy (`resolver._occurrence_allowed`: inside a filename, a CSV
        field, not at a word boundary). Left as raw text they translate to
        the ORIGINAL Azerbaijani value while the tagged mentions become a
        fresh one, so the document ends up naming two different people --
        250 records (0.24%) shipped like that. Protected here and given the
        same fresh value as its group, without becoming an entity;
      * ``decoy`` -- spliced back verbatim, never an entity.

    `decoy_ranges` (positions, from `translate.decoys.protected_ranges`) takes
    the place of `decoys` (strings, every occurrence) when given (D-54b).
    """
    ents = [(e["start"], e["end"], "entity", e["label"],
             text[e["start"]:e["end"]])
            for e in entities]
    taken = [(s, t) for s, t, *_ in ents]

    shadows: list[tuple[int, int, str, str | None, str]] = []
    for e in entities:
        value = text[e["start"]:e["end"]]
        if len(value) < SHADOW_MIN_LEN:
            continue          # too short to match safely
        start = 0
        while True:
            i = text.find(value, start)
            if i < 0:
                break
            j = i + len(value)
            if not any(i < ce and cs < j for cs, ce in taken):
                taken.append((i, j))
                shadows.append((i, j, "shadow", e["label"], value))
            start = i + 1

    if decoy_ranges is not None:
        dec = [(s, t, "decoy", None, text[s:t]) for s, t in decoy_ranges
               if not any(s < ce and cs < t for cs, ce in taken)]
    else:
        dec = [(s, t, "decoy", None, v)
               for s, t, v in decoy_spans(text, list(decoys or []), taken)]

    items = sorted(ents + shadows + dec, key=lambda x: (x[0], x[1]))
    out: list[str] = []
    slots: list[dict] = []
    cursor = 0
    for i, (s, t, kind, label, value) in enumerate(items):
        if s < cursor:
            raise SlotError(f"overlapping protected span at {s} (cursor {cursor})")
        out.append(text[cursor:s])
        out.append(f"{OPEN}{i}{CLOSE}")
        slots.append({"kind": kind, "label": label, "value": value})
        cursor = t
    out.append(text[cursor:])
    return "".join(out), slots


def found_slots(text: str) -> list[int]:
    """Slot indices present in `text`, in order of first appearance."""
    return [int(m.group(1)) for m in SENTINEL_RE.finditer(text)]


def check_round_trip(translated: str, n_slots: int) -> tuple[bool, str]:
    """Did all N slots survive, exactly once each, unmangled?

    Returns (ok, reason). `reason` is "" on success.
    """
    want = set(range(n_slots))
    found = found_slots(translated)
    fset = set(found)

    if fset == want and len(found) == n_slots:
        return True, ""

    # classify the failure for the repair queue / prompt tuning
    lenient = {int(a or b) for a, b in SENTINEL_LENIENT_RE.findall(translated)}
    missing = want - fset
    extra = fset - want
    dupes = [i for i in fset if found.count(i) > 1]

    if missing and (missing & lenient):
        return False, f"mangled sentinels (inner space / dropped bracket): {sorted(missing & lenient)}"
    if missing:
        return False, f"dropped slots: {sorted(missing)}"
    if dupes:
        return False, f"duplicated slots: {sorted(dupes)}"
    if extra:
        return False, f"invented slots: {sorted(extra)}"
    return False, f"slot count {len(found)} != {n_slots}"


def splice(translated: str, mint) -> tuple[str, list[dict]]:
    """Replace each ``⟦i⟧`` with ``mint(i)`` and record its char span.

    `mint(i) -> str` returns the fresh value for slot i. Walks left to right
    so each recorded (start, end) is exact in the string being built. Raises
    SlotError if the sentinel set is not intact -- call check_round_trip
    first for a classified reason.
    """
    n = len(found_slots(translated))
    parts: list[str] = []
    spans: list[dict] = []
    pos = 0
    last = 0
    seen: set[int] = set()
    for m in SENTINEL_RE.finditer(translated):
        i = int(m.group(1))
        if i in seen:
            raise SlotError(f"slot {i} appears more than once")
        seen.add(i)
        head = translated[last:m.start()]
        parts.append(head)
        pos += len(head)
        value = mint(i)
        parts.append(value)
        # `slot` is the sentinel's own number, NOT its position in the output.
        # The model is free to reorder ⟦0⟧ and ⟦1⟧ during translation, and the
        # caller must pair each span with labels[slot], not labels[nth-span].
        spans.append({"slot": i, "start": pos, "end": pos + len(value)})
        pos += len(value)
        last = m.end()
    parts.append(translated[last:])
    if len(seen) != n or seen != set(range(n)):
        raise SlotError(f"expected slots 0..{n-1}, got {sorted(seen)}")
    return "".join(parts), spans
