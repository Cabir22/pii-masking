"""Validator -- structural correctness for every label, not just two.

The old validator checked CREDIT_CARD and IBAN and nothing else, and its IBAN
rule had an `or [\\d\\s-]{14,34}` escape hatch that admitted essentially any
digit string. VIN, IMEI, MAC, IPv4/IPv6, email and URL all had generators and
checksum functions but were never verified.

Everything is verified here, plus three checks the old gate had no concept of:

  * **repeat-mention completeness** -- the defect behind 272 unlabeled mentions
  * **placeholder blocklist** -- so test cards and AWS example keys cannot enter
    from any source, including LLM augmentation
  * **language authenticity** -- kept from the previous pipeline (it fixed a
    real bug) but tightened: field labels no longer count toward the word
    threshold, so a form of six labels can no longer pass as prose
"""

from __future__ import annotations

import re

from . import checksums as CK
from .anchors import DEFAULT_WINDOW, has_anchor
from .blocklist import is_blocked, text_blocklist_hits
from .config import ENTITY_SET, LANGUAGES, REMOVED_LABELS, STRUCTURED_LABELS
from .locales import LOCALES
from .resolver import (_AZ_FUSED_NOUN_SUFFIX_FORMS, _AZ_HYPHEN_SUFFIX_FORMS,
                       _suffix_pattern, find_unlabeled_repeats)
from .text import fold_diacritics

# Every suffix either matcher recognises, in one alternation. Derived from
# resolver.py's own lists rather than restated, so this check and the
# resolver can never disagree about what counts as grammar.
_AZ_ANY_SUFFIX = _suffix_pattern(
    _AZ_FUSED_NOUN_SUFFIX_FORMS + _AZ_HYPHEN_SUFFIX_FORMS)

# language_evidence's az branch only credited a stopword on an EXACT match,
# so casual/diacritic-free spelling ("gore" for "görə", "uzr" for "üzr")
# scored zero -- invisible to the SAME blind spot the 2026-08-27 audit
# documented for distinctive characters (validation_gap_report.json, rule
# `language_ok`), just on the stopword side instead of the character side.
# Measured live on the 2026-08-28 negative-only run: every one of the first
# five english_contamination rejects was genuine (if sparse/diacritic-light)
# Azerbaijani, not English -- e.g. "Gecikmeye gore uzr isteyirik" scored 0
# native words despite being an ordinary apology sentence. Folding both
# sides once, at import time, costs nothing per-call and closes this
# specific gap without touching the distinctive-character path at all.
_AZ_STOPWORDS_FOLDED = {fold_diacritics(w) for w in LOCALES["az"].stopwords}


def labels_allowed(entities: list[dict]) -> list[str]:
    """Taxonomy allowlist gate. Empty list means every label is permitted.

    Separate from `validate_example` so the migration, the analyzer and the
    split preparer can all assert the same rule without running a full
    validation pass. A removed label is reported distinctly from an unknown
    one: a removed label reappearing is a policy breach worth alerting on,
    an unknown one is usually a typo.
    """
    problems = []
    for e in entities:
        label = e.get("label") if isinstance(e, dict) else None
        if label in ENTITY_SET:
            continue
        if label in REMOVED_LABELS:
            problems.append(f"REMOVED label {label!r} reappeared in output")
        else:
            problems.append(f"unknown label {label!r} not in taxonomy")
    return problems

_TRAILING_JUNK = ".,;:!?\"'»)]}…"
_LEADING_JUNK = "\"'«([{"
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_CYRILLIC = re.compile(r"[Ѐ-ӿ]")
_LATIN_WORD = re.compile(r"^[a-z]{2,}$")
_AZ_ONLY = "əƏ"

MIN_NATIVE_WORDS = {"en": 3, "az": 4, "ru": 4, "tr": 4}

# Labels whose real-world formats include an edge character the generic
# punctuation trim would otherwise flag.
#
# 2026-08-26: added STREET. `locales/az.py`'s street() builder deliberately
# generates abbreviated suffixes ending in a period ("küç.", "pr." -- real
# Azerbaijani abbreviations for "küçəsi"/"prospekti", 2 of its 5 suffix
# choices, so ~40% of all STREET spans), and the initial-abbreviation
# carve-out just below only covers a SINGLE alpha character before the
# period (an initial like "H."), not a multi-letter word like "küç." --
# t[-3] ('ç' in "küç.") is alpha, so the carve-out's own condition excludes
# it. Confirmed via a live batch that this had been silently rejecting a
# real share of valid STREET spans since validate.py's original commit
# (915a457) -- it just never blocked a run until the batch-level
# validator_failure_rate stop check (from the 2026-08-26 merge) had one
# unlucky batch concentrate enough of them to trip it.
_PUNCT_EDGE_EXEMPT_LEADING = {"TELEPHONENUM", "PRIVATE_KEY"}
_PUNCT_EDGE_EXEMPT_TRAILING = {"PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN", "URL",
                               "STREET"}


# ---------------------------------------------------------------------------
# Language authenticity
# ---------------------------------------------------------------------------

def language_evidence(text: str, lang: str) -> dict:
    """How much genuine target-language content the text carries.

    Technical identifiers are ASCII English, so they contribute nothing toward
    an az/ru/tr tag -- which is precisely what makes an English-only JSON blob
    fail while the same blob carrying a native comment passes.
    """
    loc = LOCALES[lang]
    toks = _WORD_RE.findall(text.lower())
    cyr = len(_CYRILLIC.findall(text))
    has_az = any(c in _AZ_ONLY for c in text)

    # Field labels are vocabulary but not prose. Counting them let a bare form
    # ("Ad Soyad: ... Telefon: ...") pass the old gate with no sentence in it.
    label_words = {w.lower() for v in loc.labels.values() for w in v.split()}

    if lang == "ru":
        native = sum(1 for t in toks
                     if _CYRILLIC.search(t) and t not in label_words)
        return {"native_words": native, "conflict": False}
    if lang == "az":
        native = sum(1 for t in toks
                     if (t in loc.stopwords
                         or any(c in _AZ_ONLY + loc.distinctive_chars for c in t)
                         or fold_diacritics(t) in _AZ_STOPWORDS_FOLDED)
                     and t not in label_words)
        return {"native_words": native, "conflict": cyr > 3}
    if lang == "tr":
        native = sum(1 for t in toks
                     if (t in loc.stopwords
                         or any(c in loc.distinctive_chars for c in t))
                     and t not in label_words)
        # 'ə' does not exist in Turkish: its presence means the text is az
        return {"native_words": native, "conflict": has_az or cyr > 3}
    native = sum(1 for t in toks if _LATIN_WORD.match(t) and t not in label_words)
    return {"native_words": native, "conflict": cyr > 3 or has_az}


def language_ok(text: str, lang: str, min_words: int | None = None,
                allow_mixed: bool = True) -> tuple[bool, str]:
    if lang not in LANGUAGES:
        return False, f"unknown lang {lang!r}"
    threshold = MIN_NATIVE_WORDS[lang] if min_words is None else min_words

    # Scale the threshold to document length. A 40-character chat fragment
    # ("Salam, nömrəniz?") cannot contain four native words, and rejecting it
    # would silently delete the whole short end of the length distribution --
    # which is exactly the range the previous dataset was stuck in and the new
    # one is trying to cover deliberately.
    if min_words is None:
        n_words = len(_WORD_RE.findall(text))
        if n_words < 6:
            threshold = 1
        elif n_words < 12:
            threshold = 2
        elif n_words < 20:
            threshold = max(2, threshold - 1)

    ev = language_evidence(text, lang)
    if ev.get("conflict") and not allow_mixed:
        return False, f"script conflict with lang={lang}"
    if ev["native_words"] < threshold:
        return False, (f"only {ev['native_words']} {lang} words "
                       f"(need >={threshold})")
    return True, ""


# ---------------------------------------------------------------------------
# Turkish contamination (2026-08-27 audit)
# ---------------------------------------------------------------------------
#
# `language_ok` above structurally cannot catch this. It counts a word as
# native if it is an AZ stopword or carries an AZ-distinctive character --
# but Turkish shares every one of those characters except "ə", so fluent
# Turkish scores as fluent Azerbaijani. The audit measured 167 records
# (0.25%) carrying Turkish-only lexis, e.g. "AZERTECH HIZMET COZUMLERI" and
# "Önemli Bildiriş".
#
# Only forms whose Azerbaijani spelling genuinely DIFFERS are listed. Words
# that merely look Turkish after diacritic folding are excluded on purpose:
# the `strip_diacritics` noise kind rewrites "və"->"ve" and "ilə"->"ile",
# so treating bare "ve"/"ile" as Turkish would flag ~2,000 deliberately
# noised Azerbaijani records. That mistake was made and corrected during the
# audit itself.
TURKISH_ONLY_FORMS = {
    "lütfen": "zəhmət olmasa", "için": "üçün", "büyük": "böyük",
    "güzel": "gözəl", "değil": "deyil", "nasıl": "necə", "şimdi": "indi",
    "önemli": "əhəmiyyətli", "yapmak": "etmək", "hepsi": "hamısı",
    "teşekkür": "təşəkkür", "hizmet": "xidmət", "çözüm": "həll",
    "değişiklik": "dəyişiklik", "bilgi": "məlumat",
}


# Azerbaijani words that fold to the same letters as a Turkish form above:
# "təşəkkür" and "teşekkür" both become "tesekkur", "lütfən" and "lütfen"
# both "lutfen".
_AZ_LOOKALIKES = ("təşəkkür", "lütfən")


def _tr_pattern() -> re.Pattern:
    """Turkish forms plus their diacritic-folded variants, whole-word.

    A folded variant that is also the folded spelling of an Azerbaijani word
    is left out (P2-6 batch 2, for the review). That is the rule the
    comment above sets for "ve"/"ile"; adding every folded variant broke it
    for two words, and 84 of batch 2's 107 Turkish rejections were
    Azerbaijani written without diacritics ("əvvəlcədən tesekkur edirik").
    The Turkish spellings themselves ("teşekkür", "lütfen") are still caught,
    and so is "buyuk", which is Turkish "büyük", not Azerbaijani "böyük".
    """
    az_folded = {fold_diacritics(w) for w in _AZ_LOOKALIKES}
    az_folded |= {fold_diacritics(w) for w in TURKISH_ONLY_FORMS.values()}
    every = set()
    for form in TURKISH_ONLY_FORMS:
        every.add(form)
        if fold_diacritics(form) not in az_folded:
            every.add(fold_diacritics(form))
    ordered = sorted(every, key=len, reverse=True)
    return re.compile(r"(?<!\w)(" + "|".join(ordered) + r")(?!\w)", re.IGNORECASE)


_TURKISH_RE = _tr_pattern()

# Turkish orthography: an apostrophe between a proper noun and its suffix
# ("Qax'da"). Standard Azerbaijani does not do this. 39 spans in the corpus.
_TURKISH_APOSTROPHE = re.compile(
    r"\b[A-ZİƏÖÜÇŞĞ][\wə]*['’ʼ]"
    r"(?:d[aə]|d[aı]n|d[əe]n|n[ıi]n|[aə]|y[aə]|l[aı]r|n[ıi])(?!\w)")


# ---------------------------------------------------------------------------
# Corrupt text (P2-5, batch 4)
# ---------------------------------------------------------------------------
# Letters of scripts that never belong in these documents -- Hebrew, Arabic,
# Devanagari, Thai, kana, CJK, Hangul. The model now and then emits one in
# the middle of a word (`esasな ola biler`, `居`, `ت`): 3-8 documents in each
# of batches 1-4. U+FEFF is left out: the noise injector adds it on purpose.
_FOREIGN_SCRIPT = re.compile(
    r"[\u0590-\u05ff\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\u0900-\u097f"   # Hebrew, Arabic, Devanagari
    r"\u0e00-\u0e7f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"    # Thai, kana, CJK, Hangul
    r"\uf900-\ufaff\ufb1d-\ufdff\ufe70-\ufefe]")                             # compatibility and presentation forms
# The brief's own "(noise)" marker written into the document
# (`Bu sened (noise) sizin ...`): 1-8 occurrences a batch.
_BRIEF_ECHO = re.compile(r"\(noise\)", re.IGNORECASE)


def corrupt_text(text: str) -> list[str]:
    """Characters or brief markers that cannot be part of a real document."""
    problems = []
    m = _FOREIGN_SCRIPT.search(text or "")
    if m:
        problems.append(f"corrupt_text: foreign-script character {m.group(0)!r}")
    if _BRIEF_ECHO.search(text or ""):
        problems.append("corrupt_text: the brief's '(noise)' marker in the text")
    return problems


def turkish_contamination(text: str, exempt=()) -> list[str]:
    """Turkish lexis or orthography inside text tagged as Azerbaijani.

    `exempt` are (start, end) spans where the apostrophe form was written on
    purpose (C2 `_suffixes` with surface "apostrophe", P2-4c): those are
    training data for the model to label, not contamination. An apostrophe
    form anywhere else is still reported.
    """
    problems = []
    forms = sorted({m.group(1).lower() for m in _TURKISH_RE.finditer(text)})
    if forms:
        problems.append("turkish_lexis: " + ", ".join(forms[:6]))
    apos = [m.group(0) for m in _TURKISH_APOSTROPHE.finditer(text)
            if not any(s <= m.start() and m.end() <= e for s, e in exempt)]
    if apos:
        problems.append(f"turkish_apostrophe_orthography: {apos[:4]}")
    return problems


# ---------------------------------------------------------------------------
# Span boundary policy (2026-08-27 audit)
# ---------------------------------------------------------------------------

def span_boundary_problems(text: str, entities: list[dict]) -> list[str]:
    """Spans that stop in the middle of a word.

    A span may legitimately be followed by a letter only when what follows is
    a recognised Azerbaijani suffix -- that is ordinary grammar and
    `resolver._extend_span_for_suffix` now absorbs it into the span. Anything
    else means the span ends mid-token, which a token classifier can never
    reproduce: it would be trained to end an entity where no token boundary
    exists.

    The audit found 52 such spans, all produced by the noise injector's
    `typos`/`whitespace` kinds splitting a word across the span edge
    ("Qubar egionunda" for CITY "Quba"). Offsets are repaired after noise, so
    the span stays structurally valid and every existing check passes -- this
    is the check that notices the surrounding WORD did not survive.

    BOTH edges are checked. The first version of this function looked only at
    the trailing edge; the `resolver_drift` corpus gate then surfaced 996
    records with the mirror-image defect, where the `whitespace` noise kind
    moved a space and glued the previous word's last letter onto the FRONT of
    the span -- "vAxtı 13:41" corrupted into "vAxt ı13:41", "ünvanı
    172.30.233.243" into "ünvan ı172.30.233.243". A leading letter is never
    legitimate: `resolver._is_word_boundary` refuses to produce such a span,
    which is precisely why re-resolving those records could not reproduce
    them.
    """
    problems = []
    for e in entities:
        start, end = e.get("start"), e.get("end")
        label = e.get("label")

        if isinstance(end, int) and end < len(text) and text[end].isalpha():
            if not _AZ_ANY_SUFFIX.match(text[end:end + 12]):
                problems.append(
                    f"span_truncated_midword: {label} "
                    f"{text[max(0, start or 0):end + 6]!r}")

        if isinstance(start, int) and start > 0 and text[start - 1].isalpha():
            problems.append(
                f"span_glued_to_previous_word: {label} "
                f"{text[max(0, start - 6):(end if isinstance(end, int) else start)]!r}")
    return problems


# ---------------------------------------------------------------------------
# Per-label structural validation
# ---------------------------------------------------------------------------

# D-51h (D-34d: the shape decides the label): an ID card is any two capital
# letters + 7 digits, or DYI/MYI + 7 digits; a driver licence is two letters
# + 6 digits, so the two never share a shape. The prefix was AA/AB only
# (`checksums._AZ_ID_CARD_RE`, still used by the regex fallbacks), which made
# an unfamiliar prefix read as "licence" (53 benchmark errors).
AZ_ID_CARD_RE = CK._AZ_ID_CARD_RE          # one rule: checksums follows D-51h now


def az_id_card_valid(value: str) -> bool:
    return bool(AZ_ID_CARD_RE.match(value.strip().upper()))


def value_valid(label: str, value: str) -> tuple[bool, str]:
    v = value.strip()
    if label == "AZ_ID_CARD_NUMBER":
        return (True, "") if az_id_card_valid(v) else (False, f"bad {label} format")
    if label == "PAYMENT_CARD_NUMBER":
        if not CK.luhn_valid(v):
            return False, "fails Luhn"
        if not CK.card_brand_ok(v):
            return False, "no valid issuer prefix/length"
        return True, ""
    if label == "IBAN":
        return (True, "") if CK.bank_account_valid(v) else (False, "bad IBAN")
    if label == "IPV4_ADDRESS":
        return (True, "") if CK.ipv4_valid(v) else (False, "unparseable IPv4")
    if label == "IPV6_ADDRESS":
        return (True, "") if CK.ipv6_valid(v) else (False, "unparseable IPv6")
    if label == "MAC_ADDRESS":
        return (True, "") if CK.mac_valid(v) else (False, "malformed MAC")
    if label == "ICCID":
        return (True, "") if CK.iccid_valid(v) else (False, "bad ICCID (Luhn/shape)")
    if label == "EMAIL":
        return (True, "") if CK.email_valid(v) else (False, "malformed email")
    if label == "URL":
        return (True, "") if CK.url_with_token_valid(v) else (False, "URL carries no token")
    if label == "API_KEY":
        return (True, "") if CK.api_key_valid(v) else (False, "unrecognized API key shape")
    if label == "ACCESS_TOKEN":
        return (True, "") if CK.access_token_valid(v) else (False, "not a JWT, prefixed or bare token")
    if label == "PRIVATE_KEY":
        return (True, "") if CK.private_key_valid(v) else (False, "not a PEM private key")
    if label in ("AZ_FIN", "AZ_ID_CARD_NUMBER", "AZ_PASSPORT_NUMBER", "AZ_VOEN",
                 "AZ_DRIVER_LICENSE_NUMBER"):
        checker = CK.STRUCTURED_VALIDATORS[label]
        return (True, "") if checker(v) else (False, f"bad {label} format")
    if label == "TELEPHONENUM":
        return (True, "") if CK.STRUCTURED_VALIDATORS["TELEPHONENUM"](v) \
            else (False, "not enough digits for a phone number")
    if label == "ZIPCODE":
        return (True, "") if CK.STRUCTURED_VALIDATORS["ZIPCODE"](v) \
            else (False, "bad postal code shape")
    # anchor_required labels: not called by validate_example (not in
    # STRUCTURED_LABELS); used to prove decoys invalid (P2-2)
    if label == "CARD_SECURITY_CODE":
        return (True, "") if CK.card_security_code_valid(v) else (False, "not 3-4 digits")
    if label == "TIME":
        return (True, "") if CK.time_valid(v) else (False, "not a clock time")
    if label == "AGE":
        return (True, "") if CK.age_valid(v) else (False, "not an age 0-130")
    if label == "DATE":
        return (True, "") if CK.date_valid(v) else (False, "not a real calendar date")
    return True, ""


# ---------------------------------------------------------------------------
# Whole-example validation
# ---------------------------------------------------------------------------

def declared_decoy_spans(ex: dict) -> tuple[list[tuple[int, int]], list[str]]:
    """The record's C2 `_decoys` spans, and any problem with the field itself.

    Records older than P2-3 have no `_decoys`: that is an empty list, not a
    problem. A malformed entry is a problem, never silently skipped: every
    gate trusts these spans to exempt what is inside them.
    """
    raw = ex.get("_decoys")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ["decoy: `_decoys` is not a list"]
    text = ex.get("text") or ""
    spans, problems = [], []
    for d in raw:
        s = d.get("start") if isinstance(d, dict) else None
        e = d.get("end") if isinstance(d, dict) else None
        if not isinstance(s, int) or not isinstance(e, int)                 or not isinstance(d.get("kind"), str):
            problems.append(f"decoy: malformed entry {d!r}"[:80])
        elif s < 0 or e > len(text) or s >= e:
            problems.append(f"decoy: offsets out of range ({s},{e})")
        else:
            spans.append((s, e))
    return spans, problems


MINIMAL_CONTEXT_MAX_WORDS = 5


def minimal_context(ex: dict) -> bool:
    """A declared minimal-context document (P2-4d, RC9): a name, a full name, a
    greeting or a lone city/street of at most 5 words, written on purpose by
    the targeted builder (`Fidan.`, `Salam, Fidan!`, `Bakı`).

    Checkpoint 1 misses or splits exactly these (`Fidan.` -> only `dan`), and
    the length/context gates -- the language-word minimum here, the
    carrier-word minimum and PII-density cap in the quality filter -- reject
    every one of them by construction: they were measured on full LLM
    documents to catch value dumps. Those three checks, and only those, skip a
    record that declares itself this way; every other check still applies,
    and no other record is affected.
    """
    return (ex.get("_doc_type") == "minimal_context" and ex.get("_source") == "targeted"
            and len(_WORD_RE.findall(ex.get("text") or "")) <= MINIMAL_CONTEXT_MAX_WORDS)


SUFFIX_SURFACES = ("plain", "apostrophe", "folded", "noisy")


def declared_suffix_spans(ex: dict) -> tuple[list[dict], list[str]]:
    """The record's C2 `_suffixes` (P2-4c): inflected words the generator
    wrote on purpose, `{"start", "end", "stem_end", "case", "surface"}`, and
    any problem with the field. Absent means none. Each must cover exactly
    one entity, with the stem ending inside it."""
    raw = ex.get("_suffixes")
    if raw is None:
        return [], []
    if not isinstance(raw, list):
        return [], ["suffix: `_suffixes` is not a list"]
    spans = {(e.get("start"), e.get("end")) for e in ex.get("entities") or []
             if isinstance(e, dict)}
    good, problems = [], []
    for d in raw:
        if not isinstance(d, dict) or not all(isinstance(d.get(k), int)
                                              for k in ("start", "end", "stem_end")) \
                or not isinstance(d.get("case"), str) or d.get("surface") not in SUFFIX_SURFACES:
            problems.append(f"suffix: malformed entry {d!r}"[:80])
        elif (d["start"], d["end"]) not in spans or not d["start"] < d["stem_end"] < d["end"]:
            problems.append(f"suffix: ({d['start']},{d['end']}) is not an entity with its stem inside")
        else:
            good.append(d)
    return good, problems


def validate_example(ex: dict, *, strict_language: bool = True,
                     check_structured: bool = True,
                     check_blocklist: bool = True,
                     check_repeats: bool = True,
                     check_anchors: bool = True,
                     check_turkish: bool = True,
                     check_span_boundary: bool = True,
                     anchor_window: int = DEFAULT_WINDOW,
                     min_native_words: int | None = None) -> list[str]:
    problems: list[str] = []
    if not isinstance(ex, dict):
        return ["example is not an object"]

    text, lang, entities = ex.get("text"), ex.get("lang"), ex.get("entities")
    if not isinstance(text, str) or not text.strip():
        return ["empty or missing text"]
    if lang not in LANGUAGES:
        return [f"invalid lang {lang!r}"]
    if not isinstance(entities, list):
        return ["entities is not a list"]

    if strict_language and not minimal_context(ex):
        ok, why = language_ok(text, lang, min_native_words)
        if not ok:
            problems.append(f"language: {why}")

    # Declared decoys (C2 `_decoys`, P2-3): deliberately unlabeled look-alikes.
    # Their spans are exempt from the text-level blocklist and repeat checks;
    # an undeclared copy of the same string is still checked.
    decoy_spans, decoy_problems = declared_decoy_spans(ex)
    problems.extend(decoy_problems)

    if check_blocklist:
        for hit in text_blocklist_hits(text, exempt=decoy_spans):
            problems.append(f"blocklist: {hit}")

    suffixes, suffix_problems = declared_suffix_spans(ex)
    problems.extend(suffix_problems)
    problems.extend(corrupt_text(text))
    if check_turkish and lang == "az":
        problems.extend(turkish_contamination(
            text, exempt=[(d["start"], d["end"]) for d in suffixes if d["surface"] == "apostrophe"]))

    spans = []
    for e in entities:
        if not isinstance(e, dict):
            problems.append("entity is not an object")
            continue
        label, s, en, t = e.get("label"), e.get("start"), e.get("end"), e.get("text")
        if label not in ENTITY_SET:
            problems.append(f"invalid label {label!r}")
            continue
        if not isinstance(s, int) or not isinstance(en, int):
            problems.append(f"{label}: non-integer offsets")
            continue
        if s < 0 or en > len(text) or s >= en:
            problems.append(f"{label}: offsets out of range ({s},{en})")
            continue
        if text[s:en] != t:
            problems.append(f"{label}: text/offset mismatch {t!r} != {text[s:en]!r}")
            continue
        if t != t.strip():
            problems.append(f"{label}: span has leading/trailing whitespace")
        # Punctuation-edge checks do not apply uniformly:
        #   PHONE legitimately starts with "(" -- "(012) 345 67 89" is one of
        #   the standard national formats, not a span that swallowed a bracket.
        #   Secrets and keys legitimately end in "!", "*", "=" (base64 padding).
        if label not in _PUNCT_EDGE_EXEMPT_LEADING and t and t[0] in _LEADING_JUNK:
            problems.append(f"{label}: span starts with punctuation {t!r}")
        # An IPv6 address compressed at the end ("2001:db8:1::") ends in a
        # colon that is part of the address, not stray punctuation; only a
        # span that parses as a complete address is let through.
        if (label not in _PUNCT_EDGE_EXEMPT_TRAILING and t
                and t[-1] in _TRAILING_JUNK and not (
                    len(t) >= 2 and t[-1] == "." and t[-2].isalpha()
                    and (len(t) < 3 or not t[-3].isalpha()))
                and not (label == "IPV6_ADDRESS" and t.endswith("::")
                         and CK.ipv6_valid(t))):
            problems.append(f"{label}: span ends with punctuation {t!r}")
        if check_blocklist:
            reason = is_blocked(t)
            if reason:
                problems.append(f"{label}: {reason} ({t[:40]!r})")
        if check_structured and label in STRUCTURED_LABELS:
            ok, why = value_valid(label, t)
            if not ok:
                problems.append(f"{label}: {why} ({t[:40]!r})")
        # anchor_required tier (data/schema.md). Declared in DETECTION_TIERS
        # since the taxonomy was locked but never enforced anywhere until the
        # 100k audit -- 401 of 1,487 CARD_SECURITY_CODE mentions in the
        # corpus sat next to no CVV anchor at all.
        if check_anchors and not has_anchor(label, text, s, en, anchor_window):
            problems.append(
                f"missing_required_anchor: {label} at ({s},{en}) has no "
                f"licensing context within +/-{anchor_window} chars ({t[:24]!r})")
        spans.append((s, en, label))

    # A labeled decoy is the one contradiction the decoy machinery must never
    # produce: the same characters both "not PII" and PII.
    for ds, de in decoy_spans:
        for s, en, label in spans:
            if ds < en and s < de:
                problems.append(f"decoy: ({ds},{de}) overlaps the {label} span ({s},{en})")

    spans.sort()
    for (s1, e1, l1), (s2, e2, l2) in zip(spans, spans[1:]):
        if s2 < e1:
            problems.append(f"overlapping spans ({s1},{e1}) and ({s2},{e2})")
        if (s1, e1) == (s2, e2):
            problems.append(f"duplicate span ({s1},{e1})")

    if check_span_boundary:
        problems.extend(span_boundary_problems(text, [
            {"start": s, "end": e, "label": l} for s, e, l in spans]))

    if check_repeats:
        missing = find_unlabeled_repeats(text, [
            {"start": s, "end": e, "label": l, "text": text[s:e]}
            for s, e, l in spans], exempt=decoy_spans)
        if missing:
            problems.append(f"repeat-mention: {missing} occurrence(s) of a "
                            f"labeled value left unlabeled")

    return problems
