"""Sentinel slotting primitives for the translation pipeline.

The one hard requirement of the multilingual expansion (
2026-09-03) is that character offsets stay exact. The mechanism: cut every
entity span out of the source, leave a numbered sentinel ``⟦i⟧``, translate
the sentinel-only text, then splice fresh values back in and read
``start``/``end`` off the positions you inserted at. Offsets are correct by
construction, and a broken translation is caught by a slot-count mismatch
rather than a fuzzy alignment failure.

This module is the single source of truth for that cut / restore / splice
arithmetic. It is language-agnostic and has no dependency on the rest of
``piigen``; the Russian calibration harness and the (future) shared
``scripts/translate/`` harness both import it so there is never a second copy
of the offset logic to drift.

Sentinel is ``⟦ ⟧`` (U+27E6 / U+27E7 MATHEMATICAL WHITE SQUARE BRACKETS):
absent from natural text in az/en/tr/ru so the extraction regex cannot
false-match, rare enough that an LLM treats it as opaque, and the digit inside
stays ASCII.
"""

from __future__ import annotations

import re

SENT_OPEN = "⟦"    # ⟦
SENT_CLOSE = "⟧"    # ⟧
SENT_RE = re.compile(re.escape(SENT_OPEN) + r"(\d+)" + re.escape(SENT_CLOSE))


class SlotError(ValueError):
    """A source record whose spans cannot be sentinelised, or a translation
    whose sentinels did not survive intact."""


def sentinelize(text: str, entities: list[dict]) -> tuple[str, list[str], list[str]]:
    """Replace each entity span with ``⟦i⟧`` left to right.

    Returns ``(slotted_text, slot_labels, slot_values)`` where index ``i`` in
    both lists corresponds to ``⟦i⟧``. Raises :class:`SlotError` on overlapping
    spans or an offset that does not match the stored entity ``text`` -- both
    mean the source record is broken and must not go through translation.
    """
    ents = sorted(entities, key=lambda e: (e["start"], e["end"]))
    out: list[str] = []
    labels: list[str] = []
    values: list[str] = []
    cursor = 0
    for i, e in enumerate(ents):
        s, t = e["start"], e["end"]
        if s < cursor:
            raise SlotError(f"overlapping span at slot {i}: start={s} < cursor={cursor}")
        if e.get("text") is not None and text[s:t] != e["text"]:
            raise SlotError(
                f"offset mismatch at slot {i}: text[{s}:{t}]={text[s:t]!r} "
                f"!= entity text {e['text']!r}")
        out.append(text[cursor:s])
        out.append(f"{SENT_OPEN}{i}{SENT_CLOSE}")
        labels.append(e["label"])
        values.append(text[s:t])
        cursor = t
    out.append(text[cursor:])
    return "".join(out), labels, values


def slot_set(s: str) -> set[int]:
    """The set of sentinel indices present in ``s``."""
    return {int(n) for n in SENT_RE.findall(s)}


def check_slots_survived(slotted_sent: str, translated: str) -> None:
    """Raise :class:`SlotError` unless ``translated`` carries exactly the same
    sentinel set as ``slotted_sent`` -- none missing, duplicated or renumbered.
    Nothing proceeds on a broken slot set.
    """
    sent = slot_set(slotted_sent)
    got_list = SENT_RE.findall(translated)
    got = {int(n) for n in got_list}
    if len(got_list) != len(got):
        raise SlotError(f"duplicated sentinel(s): {sorted(got_list)}")
    if got != sent:
        raise SlotError(f"slot set changed: sent {sorted(sent)}, got {sorted(got)}")


def resplice(slotted: str, values: list[str]) -> str:
    """Put ``values[i]`` back where ``⟦i⟧`` sits. Inverse of
    :func:`sentinelize` when ``values`` are the originals; also the splice step
    when ``values`` are freshly minted. Use :func:`splice_with_offsets` when
    you need the resulting spans.
    """
    def _sub(m: "re.Match[str]") -> str:
        idx = int(m.group(1))
        if idx >= len(values):
            raise SlotError(f"slot {idx} has no value (only {len(values)} given)")
        return values[idx]

    return SENT_RE.sub(_sub, slotted)


def splice_with_offsets(
    slotted: str, values: list[str]
) -> tuple[str, list[tuple[int, int]]]:
    """Splice ``values`` into their sentinels and report where each landed.

    Returns ``(final_text, spans)`` where ``spans[i] == (start, end)`` and
    ``final_text[start:end] == values[i]`` exactly. ``spans`` is in sentinel-
    index order (``⟦0⟧`` first), which is also left-to-right document order.

    Raises :class:`SlotError` if a sentinel index has no corresponding value
    or the sentinel set is not exactly ``range(len(values))``.
    """
    seen = slot_set(slotted)
    expected = set(range(len(values)))
    if seen != expected:
        raise SlotError(f"sentinel set {sorted(seen)} != range({len(values)})")

    out: list[str] = []
    spans: list[tuple[int, int] | None] = [None] * len(values)
    pos = 0
    last = 0
    for m in SENT_RE.finditer(slotted):
        idx = int(m.group(1))
        gap = slotted[last:m.start()]
        out.append(gap)
        pos += len(gap)
        val = values[idx]
        out.append(val)
        spans[idx] = (pos, pos + len(val))
        pos += len(val)
        last = m.end()
    out.append(slotted[last:])
    final = "".join(out)

    for i, sp in enumerate(spans):
        if sp is None:
            raise SlotError(f"no sentinel ⟦{i}⟧ in slotted text")
        assert final[sp[0]:sp[1]] == values[i], (i, sp, final[sp[0]:sp[1]], values[i])
    return final, spans  # type: ignore[return-value]
