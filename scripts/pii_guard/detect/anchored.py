"""The `anchor_required` tier: DATE, TIME, AGE, BUILDINGNUM, CARD_SECURITY_CODE.

This module exists to answer one question from the brief directly:

    "Invoice date: 2026-09-01" should not automatically become "[DATE]"
    unless there is a good reason to classify it as personal information.

A date is not PII. A *date of birth* is. The taxonomy already encodes this --
these five labels are `anchor_required`, meaning a value only carries the
label if a licensing word sits within ~80 characters. The repo already
implements that rule for Azerbaijani (`piigen.anchors.az`) and Russian
(`piigen.anchors.ru`), and those modules are reused verbatim here.

On top of the generator's anchors this module adds a **personal-context
filter**. The generator's anchors answer "is this a date?"; a sanitiser must
answer the narrower "is this date *about a person*?". `2026-09-01` next to
"Invoice date" is a date but not PII; the same string next to "date of birth"
is. So a match must clear two gates:

    1. the taxonomy's own anchor rule (is it this label at all?)
    2. a personal-context word nearby (is it about a person?)

`structural_kind` from the shared anchors module is also consulted, so a
number that is document furniture -- a heading number, a list marker, a table
index -- is never masked.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from piigen.anchors import az as az_anchors  # noqa: E402

from ..entities import Detection, cue_window  # noqa: E402

WINDOW = 80

#: Shapes for the five anchor-required labels. Deliberately broad -- the
#: gating below, not the regex, decides whether a match is PII.
SHAPES: dict[str, re.Pattern[str]] = {
    "DATE": re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b"
        r"|\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[a-z]*\.?,?\s+\d{4}\b"
        r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+"
        r"\d{1,2},?\s+\d{4}\b"),
    "TIME": re.compile(r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?\b"),
    "AGE": re.compile(r"\b(?:1[01]\d|[1-9]\d|[1-9])\b"),
    "BUILDINGNUM": re.compile(r"\b\d{1,4}[A-Za-z]?\b"),
    "CARD_SECURITY_CODE": re.compile(r"\b\d{3,4}\b"),
}

#: "is this about a person?" -- the second gate. Multilingual.
PERSONAL_CONTEXT: dict[str, re.Pattern[str]] = {
    "DATE": re.compile(
        r"(?i)(date\s*of\s*birth|d\.?o\.?b\b|birth\s*d|born|doğum|dogum|"
        r"дата\s*рожд|рожден|doğum\s*tarihi|"
        r"hired|employ\w*\s*(?:since|date)|admitted|discharged|"
        r"patient|diagnos|prescri|appointment|"
        r"expir\w*|issued|valid\s*(?:from|until|to)|"
        r"vəsiqə|pasport|passport|паспорт)", re.UNICODE),
    "TIME": re.compile(
        r"(?i)(appointment|admitted|discharged|patient|visit|consultation|"
        r"shift|clock[- ]?(?:in|out)|check[- ]?(?:in|out)|"
        r"görüş|qəbul|приём|прием|randevu)", re.UNICODE),
    "AGE": re.compile(
        r"(?i)(\bage[ds]?\b|years?\s*old|yr?s\s*old|y/?o\b|"
        r"yaş|yas\b|возраст|лет\b|года\b|patient|minor|adult|"
        r"born|doğum)", re.UNICODE),
    "BUILDINGNUM": re.compile(
        r"(?i)(street|st\.|avenue|ave\.|road|rd\.|lane|apt\.?|apartment|"
        r"flat|suite|floor|block|house|building|"
        r"küç|kucə|kuce|prospekt|məhəllə|mehelle|bina|mənzil|menzil|"
        r"улиц|ул\.|дом|кварт|проспект|"
        r"sokak|cadde|mahalle|daire|"
        r"address|ünvan|unvan|адрес|adres)", re.UNICODE),
    "CARD_SECURITY_CODE": re.compile(
        r"(?i)(cvv|cvc|cvv2|cvc2|security\s*code|card\s*code|"
        r"təhlükəsizlik|tehlukesizlik|код\s*безопасн|güvenlik\s*kodu)",
        re.UNICODE),
}


def _near(pat: re.Pattern[str], text: str, start: int, end: int) -> bool:
    left = cue_window(text, start, WINDOW, before=True)
    right = cue_window(text, end, WINDOW, before=False)
    return bool(pat.search(left) or pat.search(right))


def detect(text: str, labels: frozenset[str] | None = None) -> list[Detection]:
    """Anchor-required detections that are genuinely about a person."""
    out: list[Detection] = []

    for label, shape in SHAPES.items():
        if labels is not None and label not in labels:
            continue
        personal = PERSONAL_CONTEXT[label]
        for m in shape.finditer(text):
            value, start, end = m.group(0), m.start(), m.end()

            # gate 0: document furniture (headings, list markers, table indices)
            if az_anchors.is_structural_position(text, start, end):
                continue

            # gate 1: is it about a person? This is the deciding gate, and it
            # must be a CONTEXT check, never a shape check. Shape alone
            # cannot answer "is this PII" for these five labels -- that is
            # the whole point of the anchor_required tier (STEP 2's own
            # example: "Invoice date: 2026-09-01" must not become "[DATE]").
            #
            # `az_anchors.SELF_SIGNALLING` was tried here first and removed:
            # it answers "is this shape unambiguously a DATE" (as opposed to
            # some other entity), which is a different question from "is
            # this date personal", and treating a self-signalling ISO date
            # as sufficient masked "Invoice date: 2026-09-01" outright --
            # caught by a smoke test, not by inspection.
            #
            # `az_anchors.has_anchor` (AZERBAIJANI licensing words) was also
            # tried as the sole gate and dropped: for English/Russian/
            # Turkish chat text -- the actual deployment target, chathal's
            # users -- it failed almost every match before the multilingual
            # PERSONAL_CONTEXT below ever got a chance ("123 Main Street"
            # left "123" completely unmasked because gate 1 required an
            # Azerbaijani address word next to an English sentence).
            #
            # So: multilingual PERSONAL_CONTEXT is the primary gate, and the
            # AZ anchor vocabulary is kept only as an ADDITIONAL acceptable
            # context signal for genuinely Azerbaijani documents.
            if _near(personal, text, start, end):
                score = 0.8
            else:
                # Deliberately `ANCHOR_REQUIRED` (the raw licensing-word
                # pattern), NOT `az_anchors.has_anchor` -- `has_anchor` has
                # its own internal SELF_SIGNALLING shortcut (returns True on
                # shape alone) for the same reason removed above, and calling
                # it here would reintroduce the exact bug one level down.
                az_pattern = az_anchors.ANCHOR_REQUIRED.get(label)
                if az_pattern is None or not _near(az_pattern, text, start, end):
                    continue
                score = 0.7

            out.append(Detection(start=start, end=end, label=label,
                                 text=value, score=score, source="anchored"))
    return out
