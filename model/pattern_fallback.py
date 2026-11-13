"""Deterministic regex+checksum safety net for the pattern-tier labels.

Why this exists: real-model testing found the trained
xlm-roberta checkpoint has genuine, measured detection gaps on several
pattern-tier labels in ordinary sentence phrasing -- most concretely DATE
(dd.mm.yyyy misses ~all sentence-embedded phrasings despite that exact
format being 33% of all DATE training examples -- a robustness gap, not a
corpus-coverage one) and EMAIL (the model fragments one address into
disjoint sub-spans like '.', '@', '.com' instead of one span covering the
whole thing). Retraining to close either gap is out of scope here -- that's
the model-training track's job, already mid-benchmarking. What IS in scope:
these specific labels don't actually need ML at all. A VOEN, an IBAN, a
phone number, a date, an email address are all regular, checksum- or
format-verifiable shapes -- exactly the same reasoning formats/csv_format.py
already applies when it classifies a structured COLUMN by pattern rather
than asking the model to look at every cell. This module applies that same
reasoning to free text: run a deterministic finder alongside the model, and
let a verified pattern match override a model span in the same region
rather than trusting the model's guess (or its silence) for these specific
labels.

Deliberately narrow: only labels with a real regex shape AND (where one
exists) a real validator from piigen.checksums are covered here -- this is
a safety net for label types that don't need semantic/contextual judgment,
not a second NER system. GIVENNAME/SURNAME/CITY/STREET etc. have no shape
to match and stay entirely the model's job; hybrid_detect (predict.py)
never touches those.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from piigen import checksums as CK  # noqa: E402
from piigen.values import translit  # noqa: E402


def _date_plausible(value: str) -> bool:
    """No checksum exists for a date (unlike VOEN/IBAN/etc.) -- this is a
    structural sanity check only: reject a token that merely LOOKS like
    dd.mm.yyyy but has an impossible day/month (e.g. a version string like
    "12.45.2024" or a decimal-looking id fragment), so the fallback doesn't
    turn every stray dotted-number in a document into a false DATE.
    """
    parts = re.split(r"[.\-/]", value)
    if len(parts) != 3:
        return False
    try:
        d, m, y = (int(p) for p in parts)
    except ValueError:
        return False
    if len(parts[2]) == 2:
        pass  # 2-digit year: any value is plausible (no century to check)
    return 1 <= d <= 31 and 1 <= m <= 12


# Month names actually observed in DATE-labeled corpus entities across all
# four training languages (data/processed/merged/test.docs.jsonl) -- pulled
# from the real data, not guessed. RU uses the genitive form ("января"),
# which is how a day-month-year Russian date is actually written ("14
# февраля 1995"), not the dictionary/nominative form ("январь"). A handful
# of abbreviations (aug/apr/sep/nov, ağu/eki) are included only because they
# were directly observed with real counts in the corpus -- not a guessed
# complete abbreviation set for every language.
_MONTH_NUMBER = {
    # AZ
    "yanvar": 1, "fevral": 2, "mart": 3, "aprel": 4, "may": 5, "iyun": 6,
    "iyul": 7, "avqust": 8, "sentyabr": 9, "oktyabr": 10, "noyabr": 11,
    "dekabr": 12,
    # RU (genitive)
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
    # TR (full names, then the standard 3-letter abbreviations -- found via
    # a real leaked case that "ağu"/"eki" were the only TR abbreviations
    # present, an arbitrary partial set rather than a deliberate choice)
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11,
    "aralık": 12,
    "oca": 1, "şub": 2, "mar": 3, "nis": 4, "haz": 6, "tem": 7, "ağu": 8,
    "eyl": 9, "eki": 10, "kas": 11, "ara": 12,
    # EN (same story: aug/apr/sep/nov existed, the rest of the 3-letter set
    # didn't -- "20 Mar 2020" went undetected by both the model and this
    # module until "mar" was added here)
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
# Longest names first, so e.g. "may" doesn't shadow a longer alternative
# starting the same way when regex alternation tries options left-to-right.
_MONTH_ALTERNATION = "|".join(
    re.escape(m) for m in sorted(_MONTH_NUMBER, key=len, reverse=True))
_DAY_MONTH_YEAR_RE = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_ALTERNATION})\s+(\d{{4}})\b", re.IGNORECASE)
_MONTH_DAY_YEAR_RE = re.compile(
    rf"\b({_MONTH_ALTERNATION})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b",
    re.IGNORECASE)


def _named_month_date_plausible(value: str) -> bool:
    m = _DAY_MONTH_YEAR_RE.fullmatch(value) or _MONTH_DAY_YEAR_RE.fullmatch(value)
    if m is None:
        return False
    groups = m.groups()
    day_str = groups[0] if groups[0].isdigit() else groups[1]
    month_name = groups[1] if groups[0].isdigit() else groups[0]
    day = int(day_str)
    return 1 <= day <= 31 and month_name.lower() in _MONTH_NUMBER


# (label, finder regex, validator taking the matched string -> bool, or
# None if the shape alone is specific enough). Order doesn't matter --
# find_pattern_spans resolves overlaps itself.
# Domain hyphens tolerate common Unicode dash lookalikes ('\u2010'-'\u2015'
# hyphen/figure/en/em dash, '\u2212' minus sign) alongside plain ASCII '-'
# -- must stay in sync with CK.email_valid's own tolerance (checksums.py),
# or a value this finder catches would fail its own validator. Real
# example that surfaced this: an LLM wrote "hal-x\u2013billing.az" with an
# en dash where a hyphen belongs, which this regex used to miss outright.
_EMAIL_DOMAIN_DASHES = "\\-\u2010-\u2015\u2212"

_CANDIDATES: list[tuple[str, re.Pattern, object]] = [
    ("EMAIL",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9."
                rf"{_EMAIL_DOMAIN_DASHES}]+\.[A-Za-z]{{2,}}\b"),
     CK.email_valid),
    ("DATE",
     re.compile(r"\b\d{1,2}[.\-/]\d{1,2}[.\-/]\d{2,4}\b"),
     _date_plausible),
    ("DATE", _DAY_MONTH_YEAR_RE, _named_month_date_plausible),
    ("DATE", _MONTH_DAY_YEAR_RE, _named_month_date_plausible),
    ("TELEPHONENUM",
     re.compile(r"(?:\+994|\b0)(?:[ \-]?\d){9}\b"),
     CK.STRUCTURED_VALIDATORS["TELEPHONENUM"]),
    ("AZ_VOEN", re.compile(r"\b\d{10}\b"), CK.az_voen_valid),
    ("AZ_FIN", re.compile(r"\b[0-9A-HJ-NP-Z]{7}\b"), CK.az_fin_valid),
    # D-51h: any two letters + 7 digits (or DYI/MYI + 7), trusted like the
    # licence's two letters + 6 below; the length tells them apart
    ("AZ_ID_CARD_NUMBER", re.compile(r"\b(?:[A-Z]{2}|DYI|MYI)\d{7}\b"),
     CK.az_id_card_valid),
    ("AZ_PASSPORT_NUMBER", re.compile(r"\b[A-Z]\d{8}\b"), CK.az_passport_valid),
    ("AZ_DRIVER_LICENSE_NUMBER", re.compile(r"\b[A-Z]{2}\d{6}\b"),
     CK.az_driver_license_valid),
    ("IBAN", re.compile(r"\bAZ\d{2}[A-Z]{4}\d{20}\b"), CK.bank_account_valid),
]


# Role/generic local-part words that should never be treated as a name
# fragment even though they pass the length/shape checks below. The first
# line is copied verbatim from model/values.py's own email() generator (the
# exact prefixes IT deliberately mixes in for a non-personal address);
# the second is a defensive superset covering common real-world role
# addresses the generator doesn't happen to produce but a real customer
# database still would.
_EMAIL_LOCAL_EXCLUDE = {
    "info", "support", "sales", "hr", "billing", "accounts", "helpdesk",
    "noreply", "careers", "finance", "legal", "orders",
    "contact", "office", "team", "admin", "user", "mail", "webmaster",
    "service", "help", "customer", "general", "no-reply", "reply",
}
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def find_email_echoed_name_spans(text: str, existing_spans: list[dict]
                                 ) -> list[dict]:
    """A name the model missed, recovered by cross-referencing an EMAIL
    address already found elsewhere in the SAME document.

    Real-model testing found a specific, reproducible failure: a person's
    name mentioned in running text goes undetected specifically when a
    name-derived email address ("nermin.kerimova@mail.az" for "Nərmin
    Kərimova") also appears in the same short document -- confirmed NOT to
    be a general rule (a real corpus document handles the identical
    pattern correctly elsewhere), so this isn't safely fixable by
    retraining guidance alone; it needs a targeted catch here.

    Why this is safe where a bare "match any word against a name list"
    approach would not be: it never invents candidates from nothing. It
    only acts on a fragment of an ALREADY-VERIFIED EMAIL address that
    belongs to THIS document, transliterated with the exact same table
    model/values.py's own generator used to BUILD such emails from real
    names in the first place (imported directly, not reproduced) -- so a
    match here means "this word, written with real diacritics, IS the
    same value already present in a verified PII field two lines away",
    not "this word merely resembles some name somewhere".

    Guardrails against false positives:
      - only acts on fragments of an address already confirmed EMAIL by
        `existing_spans` (model or pattern-tier, doesn't matter which)
      - role/generic local parts ("info", "support", ...) are excluded,
        including the exact prefix list the corpus generator itself mixes
        into non-personal addresses
      - a minimum 4-character fragment, to keep a short coincidental word
        from colliding with a short name fragment
      - whole-WORD comparison only (`translit(word) == fragment`), never
        substring matching -- the same "Ali" inside "Aliyev" problem
        resolver.py's own _is_word_boundary was built to avoid
      - never overrides a position any other detector already covered,
        only fills a genuine gap
    """
    email_spans = [s for s in existing_spans if s["label"] == "EMAIL"]
    if not email_spans:
        return []

    claimed = [(s["start"], s["end"]) for s in existing_spans]

    fragments: set[str] = set()
    for s in email_spans:
        local = s["text"].split("@", 1)[0]
        for frag in re.split(r"[.\-_+0-9]+", local):
            frag = frag.lower()
            if len(frag) >= 4 and frag not in _EMAIL_LOCAL_EXCLUDE:
                fragments.add(frag)
    if not fragments:
        return []

    found = []
    for m in _WORD_RE.finditer(text):
        s, e = m.start(), m.end()
        if any(s < ce and cs < e for cs, ce in claimed):
            continue  # already covered by some other detection
        word = m.group(0)
        if len(word) < 4:
            continue
        if translit(word) in fragments:
            found.append({"start": s, "end": e, "label": "GIVENNAME",
                          "text": word})
            claimed.append((s, e))  # don't let two fragments double-claim
    return found


def find_pattern_spans(text: str) -> list[dict]:
    """Every checksum/format-verified pattern-tier match in `text`, as
    non-overlapping spans. Longest-match-first claim on overlap -- the same
    policy predict.py's _merge_window_spans and resolver.py's
    resolve_claims both already use, for the same reason: a complete match
    should win over a partial one caught inside it (a 10-digit AZ_VOEN
    fully containing a coincidentally-valid 7-character AZ_FIN substring,
    for example), independent of which pattern happened to fire first.
    """
    candidates = []
    for label, pattern, validator in _CANDIDATES:
        for m in pattern.finditer(text):
            value = m.group(0)
            if validator is not None and not validator(value):
                continue
            candidates.append({"start": m.start(), "end": m.end(),
                               "label": label, "text": value})

    candidates.sort(key=lambda c: c["end"] - c["start"], reverse=True)
    claimed: list[tuple[int, int]] = []
    spans = []
    for c in candidates:
        s, e = c["start"], c["end"]
        if any(s < ce and cs < e for cs, ce in claimed):
            continue
        claimed.append((s, e))
        spans.append(c)

    spans.sort(key=lambda sp: sp["start"])
    return spans
