"""Entity vocabulary for the sanitisation service.

The label set is NOT invented here. It is the project's locked 27-label
taxonomy (`data/schema.md` v2.0.0, encoded in `piigen.config.DETECTION_TIERS`),
reused verbatim so a span this service masks means exactly what the same span
means to the NER model trained in this repo. Inventing a parallel vocabulary
was the single most likely way to make the two halves of the project disagree.

What this module adds on top of the taxonomy is the *placeholder family*: the
human-readable word that appears inside a placeholder. Several taxonomy labels
collapse into one family on purpose -- `GIVENNAME` and `SURNAME` are both
PERSON to a reader, and keeping them apart in the placeholder would leak the
fact that a document names someone by surname only.

`DATE`/`TIME`/`AGE`/`BUILDINGNUM`/`CARD_SECURITY_CODE` are in the taxonomy's
`anchor_required` tier: a bare number is only one of those if the surrounding
text licenses it. They are listed here, but `detect.anchored` is what decides
whether a given occurrence is really PII -- see STEP 2's "Invoice date:
2026-09-01 should not become [DATE]".
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen.config import DETECTION_TIERS  # noqa: E402

#: The locked taxonomy, re-exported so callers never hand-roll a label list.
LABELS: frozenset[str] = frozenset(DETECTION_TIERS)

#: taxonomy label -> placeholder family. Families are deliberately coarser
#: than labels: the placeholder is shown to an external model, so it must
#: carry the *kind* of fact without narrowing it further than necessary.
FAMILY: dict[str, str] = {
    # people and places (ml_context tier)
    "GIVENNAME": "PERSON",
    "SURNAME": "PERSON",
    "CITY": "LOCATION",
    "STREET": "ADDRESS",
    "BUILDINGNUM": "ADDRESS",
    "ZIPCODE": "POSTCODE",
    # contact
    "EMAIL": "EMAIL",
    "TELEPHONENUM": "PHONE",
    "URL": "URL",
    # financial
    "PAYMENT_CARD_NUMBER": "CARD",
    "CARD_SECURITY_CODE": "CARD_CVV",
    "IBAN": "IBAN",
    # government / national identifiers
    "AZ_FIN": "NATIONAL_ID",
    "AZ_ID_CARD_NUMBER": "NATIONAL_ID",
    "AZ_PASSPORT_NUMBER": "PASSPORT",
    "AZ_VOEN": "TAX_ID",
    "AZ_DRIVER_LICENSE_NUMBER": "DRIVER_LICENSE",
    # credentials and machine identifiers
    "API_KEY": "CREDENTIAL",
    "ACCESS_TOKEN": "CREDENTIAL",
    "PRIVATE_KEY": "CREDENTIAL",
    "IPV4_ADDRESS": "IP",
    "IPV6_ADDRESS": "IP",
    "MAC_ADDRESS": "MAC",
    "ICCID": "SIM_ID",
    # temporal (only PII when anchored -- see detect.anchored)
    "DATE": "DATE",
    "TIME": "TIME",
    "AGE": "AGE",
}

assert set(FAMILY) == set(LABELS), (
    "FAMILY must cover exactly the locked taxonomy; drift means this service "
    "and the NER model disagree about what a label is. "
    f"missing={sorted(set(LABELS) - set(FAMILY))} "
    f"extra={sorted(set(FAMILY) - set(LABELS))}"
)

#: Families whose placeholders should normally be kept even when the caller
#: asks for a minimal mask: these are direct identifiers.
DIRECT_IDENTIFIERS: frozenset[str] = frozenset({
    "PERSON", "EMAIL", "PHONE", "NATIONAL_ID", "PASSPORT", "TAX_ID",
    "DRIVER_LICENSE", "CARD", "CARD_CVV", "IBAN", "CREDENTIAL", "SIM_ID",
})


@dataclass(frozen=True, slots=True)
class Detection:
    """One PII span found in extracted text.

    `start`/`end` are character offsets into the text the detector was given,
    end-exclusive -- the same convention as `data/schema.md` and the rest of
    the repo, so a Detection can be compared against a gold entity directly.
    """

    start: int
    end: int
    label: str
    text: str
    #: 0..1. Pattern+checksum detections are 1.0; model detections carry the
    #: model's own score. Used by the confidence floor in `GuardConfig`.
    score: float = 1.0
    #: which detector produced this, for auditing ("pattern", "anchored", ...)
    source: str = ""

    def __post_init__(self) -> None:
        if self.label not in LABELS:
            raise ValueError(
                f"{self.label!r} is not in the locked taxonomy. "
                f"Add it to data/schema.md and piigen.config first.")
        if not (0 <= self.start < self.end):
            raise ValueError(f"bad span [{self.start}:{self.end}) for {self.label}")

    @property
    def family(self) -> str:
        return FAMILY[self.label]

    def overlaps(self, other: "Detection") -> bool:
        return self.start < other.end and other.start < self.end


def resolve_overlaps(dets: list[Detection]) -> list[Detection]:
    """Drop overlapping detections, keeping the strongest.

    Two detectors legitimately fire on the same characters -- an IBAN contains
    digit runs a phone pattern likes, a URL contains a hostname the IP rule
    matches. Masking both would corrupt offsets, and masking the weaker one
    would under-protect, so the winner is chosen by (longer span, then higher
    score, then earlier start). Longest-first matters: masking the IBAN is
    strictly safer than masking a fragment of it and leaving the rest.
    """
    ordered = sorted(dets, key=lambda d: (-(d.end - d.start), -d.score, d.start))
    kept: list[Detection] = []
    for d in ordered:
        if not any(d.overlaps(k) for k in kept):
            kept.append(d)
    return sorted(kept, key=lambda d: (d.start, d.end))


#: Sentence terminator followed by whitespace/end/closing punctuation.
_SENTENCE_END = re.compile(r"[.!?][\"'\)\]]*(?:\s|$)")


def cue_window(text: str, pos: int, window: int, *, before: bool) -> str:
    """Up to `window` characters before/after `pos`, clipped at the nearest
    segment boundary (`extract.base.SEGMENT_JOIN`, "\\n\\n") or sentence end,
    whichever is closer.

    Every anchor/cue lookup in this package (`detect.anchored`'s
    PERSONAL_CONTEXT, `detect.patterns`'s ANCHOR_WORDS, `detect.names`'s
    TITLE_CUE/ADDRESS_CUE) used a bare fixed-size slice before this existed,
    and a fixed window has no notion of "this is a different sentence" or
    "this is a different part of the document" -- it only knows character
    count. Two real, confirmed bugs came from that, both found by testing
    against realistic multi-sentence, multi-segment documents rather than
    one-line smoke tests:

    * A "CVV 482" mention at the end of one body paragraph sat within 80
      characters of an unrelated ticket number in the document's own
      HEADER (`extract/docx.py` appends header/footer segments after body
      paragraphs and table cells, so they land physically adjacent in the
      joined text) -- the ticket number got masked as CARD_SECURITY_CODE.
    * An address cue ("küçəsi", street) in one sentence sat within 40
      characters of an unrelated word STARTING THE NEXT SENTENCE -- that
      word got masked as a street name.

    Neither is a plausible real anchor: a licensing word in one sentence,
    or one document region, does not license a value in a different
    sentence or region just because they happen to be within N raw
    characters of each other.
    """
    if before:
        raw = text[max(0, pos - window):pos]
        seg = raw.rfind("\n\n")
        if seg != -1:
            raw = raw[seg + 2:]
        last_end = None
        for m in _SENTENCE_END.finditer(raw):
            last_end = m
        return raw[last_end.end():] if last_end else raw
    raw = text[pos:pos + window]
    seg = raw.find("\n\n")
    if seg != -1:
        raw = raw[:seg]
    m = _SENTENCE_END.search(raw)
    return raw[:m.start() + 1] if m else raw
