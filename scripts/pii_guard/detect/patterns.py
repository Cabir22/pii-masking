"""Structured-PII detection: shape + structural validation.

Covers the taxonomy's `pattern` tier (16 labels) and `hybrid` tier
(TELEPHONENUM, ZIPCODE). These are the labels where a regex plus a checksum
is more reliable than any model, which is why they are handled here and not
left to the NER tier.

Every rule is `(regex) AND (validator)`. The validators are
`piigen.checksums` -- the same Luhn / IBAN mod-97 / ICCID / IPv4 / IPv6 code
the generator uses to *mint* these values, so detection and generation cannot
disagree about what a valid IBAN is. Shape alone is never enough: a 16-digit
run is only a card number if it passes Luhn, which is what stops order
numbers and git SHAs from being masked as payment cards.

Two confidence classes, mirroring `piigen.llm.quality`'s design:

* **self-signalling** -- the shape is specific enough on its own
  (`-----BEGIN PRIVATE KEY-----`, an `@`-bearing email, `AA1234567`).
* **anchored** -- the shape collides with ordinary document content, so a
  licensing word must appear within `ANCHOR_WINDOW` characters. A bare
  10-digit run is an AZ_VOEN only if "VÖEN"/"tax"/"vergi" is nearby;
  otherwise it is an invoice number and masking it would destroy the
  document's meaning for no privacy gain.

The anchor vocabulary here is multilingual (az/en/ru/tr) because documents
arriving at this service are not language-controlled, unlike the generator's
Azerbaijani-only corpus.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from piigen import checksums as CK  # noqa: E402

from ..entities import Detection, cue_window  # noqa: E402

ANCHOR_WINDOW = 80


def _always(_v: str) -> bool:
    return True


# --------------------------------------------------------------------------
# self-signalling shapes: regex + structural validator, no context needed
# --------------------------------------------------------------------------
SELF_SIGNALLING: list[tuple[str, re.Pattern[str], object]] = [
    ("PRIVATE_KEY", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        re.DOTALL), _always),
    ("EMAIL", re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), CK.email_valid),
    ("ACCESS_TOKEN", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), _always),
    ("API_KEY", re.compile(
        r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"
        r"|\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}"
        r"|\bsk-[A-Za-z0-9._-]{16,}"
        r"|\bghp_[A-Za-z0-9]{20,}"
        r"|\bglpat-[A-Za-z0-9_-]{16,}"
        r"|\bxox[bapr]-[A-Za-z0-9-]{12,}"), _always),
    # URL only counts as PII when it carries a token / personal identifier --
    # that is how data/schema.md defines the label. A bare marketing link is
    # not PII and masking it would wreck document reasoning.
    ("URL", re.compile(r"https?://[^\s<>\"'\)\]]+"), CK.url_with_token_valid),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[ ]?(?:[A-Z0-9]{4}[ ]?){2,7}[A-Z0-9]{1,4}\b"),
     CK.iban_valid),
    ("ICCID", re.compile(r"\b89\d{17,18}\b"), CK.iccid_valid),
    ("MAC_ADDRESS", re.compile(
        r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"), CK.mac_valid),
    ("IPV4_ADDRESS", re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b"), CK.ipv4_valid),
    ("IPV6_ADDRESS", re.compile(
        r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}\b"), CK.ipv6_valid),
    ("PAYMENT_CARD_NUMBER", re.compile(r"\b(?:\d[ -]?){13,19}\b"),
     CK.credit_card_valid),
    # Letter-prefixed AZ ID forms are specific enough to trust unanchored.
    ("AZ_ID_CARD_NUMBER", re.compile(r"\b(?:AA|AB|DYI|MYI)\d{7}\b"),
     CK.az_id_card_valid),
]


# --------------------------------------------------------------------------
# anchored shapes: ambiguous alone, PII only with a licensing word nearby
# --------------------------------------------------------------------------
ANCHORED: list[tuple[str, re.Pattern[str], object]] = [
    ("AZ_VOEN", re.compile(r"\b\d{10}\b"), CK.az_voen_valid),
    ("AZ_FIN", re.compile(r"\b[0-9A-HJ-NP-Z]{7}\b"), CK.az_fin_valid),
    ("AZ_PASSPORT_NUMBER", re.compile(r"\b[A-Z]\d{8}\b"), CK.az_passport_valid),
    ("AZ_DRIVER_LICENSE_NUMBER", re.compile(r"\b[A-Z]{2}\d{6}\b"),
     CK.az_driver_license_valid),
    # D-51h: an ID card with any other two-letter prefix (AA/AB/DYI/MYI are
    # trusted unanchored above); like the licence, only near an ID-card word
    ("AZ_ID_CARD_NUMBER", re.compile(r"\b[A-Z]{2}\d{7}\b"), CK.az_id_card_valid),
    ("TELEPHONENUM", re.compile(
        r"(?:\+\d{1,3}[ \-.]?)?(?:\(\d{1,4}\)[ \-.]?)?\d{2,4}(?:[ \-.]?\d{2,4}){2,4}\b"),
     _always),
    ("ZIPCODE", re.compile(r"\b(?:AZ ?\d{4}|\d{4,6})\b"), _always),
]

#: Licensing vocabulary, multilingual. A shape in ANCHORED is masked only if
#: one of these appears within ANCHOR_WINDOW characters on either side.
ANCHOR_WORDS: dict[str, re.Pattern[str]] = {
    "AZ_VOEN": re.compile(
        r"(?i)\b(v[öo]en|vergi|m[üu]k[əe]ll[əe]f|tax\s*(?:id|number)|"
        r"[ин]?нн|taxpayer)", re.UNICODE),
    "AZ_FIN": re.compile(
        r"(?i)(\bfin\b|f\.i\.n|ş[əe]xsiyy[əe]t|sexsiyyet|v[əe]siq[əe]|"
        r"\bpin\b|national\s*id|id\s*card|kimlik)", re.UNICODE),
    "AZ_PASSPORT_NUMBER": re.compile(
        r"(?i)(pasport|passport|паспорт|pasaport)", re.UNICODE),
    "AZ_ID_CARD_NUMBER": re.compile(
        r"(?i)(ş[əe]xsiyy[əe]t|sexsiyyet|v[əe]siq[əe]|id\s*card|identity\s*card|"
        r"national\s*id|kimlik|удостоверени)", re.UNICODE),
    "AZ_DRIVER_LICENSE_NUMBER": re.compile(
        r"(?i)(s[üu]r[üu]c[üu]|v[əe]siq[əe]|driv\w*\s*lic|licen[cs]e|"
        r"права|ehliyet)", re.UNICODE),
    # NOT bare "contact"/"əlaqə" -- both are extremely common in ordinary
    # document/chat prose ("contact us", "Əlaqə: dəstək"), and a date or
    # any other digit run within 80 chars of one was being misclassified
    # as a phone number as a result ("Contact John Smith...Invoice date:
    # 2026-09-01" masked the date -- caught by the extraction test suite,
    # where a two-line PDF put "Contact" within the window of an unrelated
    # date on the next line). Require a *specific* phone cue instead.
    "TELEPHONENUM": re.compile(
        r"(?i)(telefon|n[öo]mr[əe]?si|mobil|z[əe]ng|[əe]laq[əe]\s*n[öo]mr|"
        r"whats\s*app|phone\s*(?:number|no\.?|:)?|tel\.?\s*:|\bcell\b|"
        r"contact\s*(?:number|no\.?|:)|телефон|звон|"
        r"call\s*(?:me|us|now)|fax)", re.UNICODE),
    "ZIPCODE": re.compile(
        r"(?i)(zip|post\w*\s*(?:code|kod)|[öo]sta|indeks|индекс|"
        r"posta\s*kodu|po[çc]t)", re.UNICODE),
}


def _anchored_ok(label: str, text: str, start: int, end: int) -> bool:
    pat = ANCHOR_WORDS.get(label)
    if pat is None:
        return True
    # cue_window, not a bare slice: a bare 80-char window let a "CVV 482"
    # mention at the end of one body paragraph license an unrelated ticket
    # number sitting in the document's own HEADER (extract/docx.py places
    # header/footer segments after body paragraphs, so they land physically
    # adjacent in the joined text) -- found by testing against a realistic
    # multi-segment document, not a single-paragraph smoke test.
    left = cue_window(text, start, ANCHOR_WINDOW, before=True)
    right = cue_window(text, end, ANCHOR_WINDOW, before=False)
    return bool(pat.search(left) or pat.search(right))


def _emit(label: str, text: str, m: re.Match[str], validator, source: str,
          score: float) -> Detection | None:
    value = m.group(0)
    # trim trailing sentence punctuation the regex may have swallowed
    while value and value[-1] in ".,;:!?)]}»":
        value = value[:-1]
    if not value:
        return None
    try:
        if not validator(value):
            return None
    except Exception:                       # a validator must never crash detection
        return None
    return Detection(start=m.start(), end=m.start() + len(value),
                     label=label, text=value, score=score, source=source)


def detect(text: str, labels: frozenset[str] | None = None) -> list[Detection]:
    """All structured-PII detections in `text`.

    Overlaps are left in: `entities.resolve_overlaps` (called by the masker)
    decides the winner globally, once every tier has had its say.
    """
    out: list[Detection] = []

    for label, pattern, validator in SELF_SIGNALLING:
        if labels is not None and label not in labels:
            continue
        for m in pattern.finditer(text):
            d = _emit(label, text, m, validator, "pattern", 1.0)
            if d is not None:
                out.append(d)

    # a label can be in both tiers (AZ_ID_CARD_NUMBER: AA/AB/DYI/MYI on sight,
    # any other prefix anchored, D-51h); the same span found by both is
    # reported once, by the self-signalling tier
    seen = {(d.start, d.end, d.label) for d in out}
    for label, pattern, validator in ANCHORED:
        if labels is not None and label not in labels:
            continue
        for m in pattern.finditer(text):
            d = _emit(label, text, m, validator, "pattern-anchored", 0.9)
            if (d is not None and (d.start, d.end, d.label) not in seen
                    and _anchored_ok(label, text, d.start, d.end)):
                out.append(d)
                seen.add((d.start, d.end, d.label))

    return out
