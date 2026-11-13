"""EntityResolver -- labels EVERY occurrence, resolves overlaps deterministically.

The audit traced 272 unlabeled mentions across 233 examples to one line in the
old resolver:

    if s < e and not any(...):
        ...
        placed = True
        break          # <-- stopped after the FIRST occurrence

So an email address in a header was labeled and the same address inside the
quoted reply below it was not. The model was being taught that a value is PII
in one position and not in another -- on quoted email threads, which are among
the highest-value real masking targets.

This module fixes that and takes on further jobs the old one did not:

  * `complete_occurrences` runs over documents the offline generator produced,
    catching any case where a value was written twice but only recorded once
  * overlap resolution is longest-match-first, so `john.doe@acme.com` wins over
    the `john.doe` USERNAME inside it regardless of the order they were claimed
  * `_extend_span_for_suffix` grows a span to include a fused Azerbaijani case
    suffix ("Bakı" -> "Bakıda") on the 4 `ml_context` labels, per the
    2026-08-26 tokenizer audit's span-policy decision: a
    stem-only span has no token boundary at its own end (the whole inflected
    word is one SentencePiece token), so it is structurally unemittable by a
    token classifier even when correctly detected
"""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass

from .anchors import (ANCHOR_REQUIRED, has_anchor, is_structural_position,
                      resolvable_unanchored)
from .config import DETECTION_TIERS, ENTITY_SET
from .text import DIACRITIC_MAP, fold_diacritics

_WORDISH = re.compile(r"[\w@]")
_JOIN_PUNCT = ".+-"


@functools.lru_cache(maxsize=None)
def _key_char(ch: str) -> str:
    folded = DIACRITIC_MAP.get(ch, ch)
    low = folded.lower()
    return low if len(low) == 1 else folded


def match_key(s: str) -> str:
    """`s` lower-cased and diacritic-folded, ONE character for one character.

    The LLM writes a planned value in forms a verbatim search cannot see: in
    capitals (`ŞƏMKIRDƏDIR` for `Şəmkir`), without Azerbaijani letters
    (`Gence`, `Xirdalanda`) or both (P2-5, batch 1). Comparing keys finds all
    of them, and because no character expands (`"İ".lower()` is two
    characters, so plain lower() would shift every later offset), a match at
    (s, e) in the key is the span (s, e) in `s` itself.
    """
    return "".join(map(_key_char, s))

# The 4 ml_context labels (data/schema.md) are the only ones that are ever
# real Azerbaijani proper nouns in running prose -- the only ones a genuine
# grammatical case suffix can attach to. Derived from DETECTION_TIERS (the
# single source of truth for label kind) rather than duplicated, so this
# cannot silently drift from the taxonomy if a label's tier ever changes.
_INFLECTABLE_LABELS = {label for label, tier in DETECTION_TIERS.items()
                       if tier == "ml_context"}

# Azerbaijani grammatical suffixes that commonly attach directly (via a bare
# hyphen, no space) to a value at the end of a sentence or clause: "10:17-də"
# (locative, "at 10:17"), "67-dir" (copula, "is 67"), "5-ci" (ordinal,
# "5th"), "10-dan" (ablative, "from 10"). This is closed-class Azerbaijani
# morphology, not a general word list -- ordered longest-first so e.g. "dan"
# is tried before a shorter prefix of it could ever matter, though the
# trailing lookahead below makes that non-issue moot anyway.
#
# Found by manual review of real generated output (2026-08-24,
# quality_filter.check_unlabeled_planned_pii): 35 confirmed instances across
# 1,100 documents of a real, present, verbatim value match being discarded as
# "inside a longer token" for exactly this reason, 18 of them TIME
# ("10:17-də", "11:32 PM-dir"). This was the documented-but-unfixed gap
# referenced below until this rule.
# 2026-08-27 audit: two additions, and a change of construction.
#
#   * Copula/personal endings ("Kazımli-yəm" = "I am Kazimli") were missing.
#     The audit found real, present, verbatim values discarded for this.
#   * Every form is now paired automatically with its diacritic-FOLDED
#     variant, derived from text.DIACRITIC_MAP -- the same table noise.py's
#     `strip_diacritics` kind uses to produce them. Hand-listed forms had
#     drifted: "-də" was listed, the folded "-de" that the noise injector
#     actually emits was not, so noised documents lost annotations
#     ("Saat 14:35-de"). Deriving instead of listing makes that class of
#     divergence impossible.
_AZ_HYPHEN_SUFFIX_FORMS = (
    "dirlər", "dır", "dir", "dur", "dür",
    "dan", "dən", "da", "də",
    "ıncı", "inci", "uncu", "üncü", "cı", "ci", "cu", "cü",
    "nın", "nin", "nun", "nün",
    "la", "lə",
    # copula / personal endings -- safe here because the hyphen itself
    # already marks the boundary, unlike the fused set below.
    "yəm", "yam", "əm", "am", "sən", "san",
    # P2-6 (batch 1, 2026-10-03): the consonant-stem genitive, the dative and
    # the accusative after a hyphen were missing, so `Sarracov-un`,
    # `Hacıxanova-ya`, `Gülyanaq-a` and `küç.-dəki` left real names
    # unlabelled (43 occurrences in 6,000 documents). The hyphen marks the
    # boundary, as for the copula above.
    "ın", "in", "un", "ün",
    "ya", "yə", "a", "ə",
    "nı", "ni", "nu", "nü", "ı", "i", "u", "ü",
    "dakı", "dəki",
    # v4.2 native review: the end of a range, `saat 09:00-dan
    # 18:00-dək`; without it every `-dək` end was refused (targeted build:
    # all such documents rejected; R10 left the range's end unlabelled)
    "dək",
)


def _suffix_pattern(forms: tuple[str, ...]) -> re.Pattern:
    """Whole-suffix alternation over `forms` plus their folded variants.

    Longest-first so a longer real suffix wins; `(?!\\w)` keeps the match
    anchored to the end of the token, which is what stops a suffix from
    matching a mere prefix of some longer unrelated word.
    """
    every = {f for form in forms for f in (form, fold_diacritics(form))}
    ordered = sorted(every, key=len, reverse=True)
    return re.compile("^(" + "|".join(ordered) + r")(?!\w)")


_AZ_HYPHEN_SUFFIX = _suffix_pattern(_AZ_HYPHEN_SUFFIX_FORMS)

# The far more common case: a real Azerbaijani noun-case suffix fused
# DIRECTLY onto a proper noun with no delimiter at all -- "Bakıda" (Bakı +
# locative, "in Baku"), "Bakıdan" (+ ablative, "from Baku"), "Bakıya" (+
# dative, "to Baku"), "Bakının" (+ genitive, "Baku's"), "Bakını" (+
# accusative), "Bakılar" (+ plural). This is how a native speaker actually
# writes these words; a hyphen is the exception (mostly seen on bare
# numerals), not the rule.
#
# 2026-08-26: measured directly against the repaired corpus -- of 55,935
# GIVENNAME/SURNAME/CITY/STREET mentions, exactly 2 (0.004%) were followed
# by a letter, and both of those 2 turned out to be noise-injection typo
# artifacts on the real inspection, not genuine grammar (`_noise:
# ['typos', ...]` on both records) -- the true rate of the model actually
# writing (and the resolver accepting) a naturally inflected name/place is
# 0%. Cross-checked against the reject log: leaked-unlabeled-PII rejects
# (the failure mode an inflected-but-unrecognized value would produce) are
# 95% EMAIL; essentially none implicate these four labels -- so this was
# not primarily documents being thrown away for trying to inflect and
# failing, it is the model barely attempting natural inflection in the
# first place, most likely reinforced by the "verbatim value" framing in
# dspy_generate.py's prompt (see the sibling fix there). This resolver
# change is necessary but not sufficient on its own -- pairs with that
# prompt change so there is something for it to actually accept.
#
# Same closed-class, whole-suffix-match, `(?!\w)`-guarded design as
# `_AZ_HYPHEN_SUFFIX` above, extended to the full noun case paradigm
# (genitive, dative, accusative, locative, ablative) plus plural and the
# common plural+case combinations, in both the post-vowel (glide-consonant)
# and post-consonant (bare) surface forms -- deliberately not conditioned
# on the claimed value's own final character, so both forms are accepted
# regardless of which one is grammatically correct for that particular
# stem. That is safe, not sloppy: a form that is grammatically impossible
# for a given stem (e.g. "Bakıa" instead of the correct "Bakıya") simply
# never occurs in real text, so admitting it costs nothing, while requiring
# stem-conditioned matching would add real complexity for no reduction in
# false accepts. Ordered longest-first (plural+case before plural before
# bare case) so a longer real suffix is preferred, though `(?!\w)`-driven
# backtracking would still find it either way, as `_AZ_HYPHEN_SUFFIX`'s own
# comment already notes.
#
# False-accept risk is the same as the hyphen case and is guarded the same
# way: the WHOLE remainder after the claimed value must be exactly one of
# these closed strings with nothing else following, not merely a prefix of
# some longer unrelated word. "Əliyev" (a different person's surname) does
# not falsely admit a claimed "Əli" -- "yev" is not a member of this set.
# "Əliağa" (a compound name) does not falsely admit "Əli" either -- "a" IS
# a member (bare dative), but the lookahead fails because "ğa" continues
# past it. Possessive suffixes (-ım/-in/-ı, 1st/2nd/3rd person "my/your/
# his") are deliberately NOT included: they are shorter, more
# collision-prone, and grammatically odd on a bare proper noun outside
# specific constructions -- narrower scope, not an oversight.
#
# `na/nə`, `nda/ndə`, `ndan/ndən` (the "n"-buffered dative/locative/ablative)
# are a separate surface form from the bare/glide ones above, needed
# specifically for a noun that already ends in the 3rd-person possessive
# marker "-(s)i" -- which is every non-abbreviated STREET value in this
# project (`locales/az.py`'s street() always appends "küçəsi"/"prospekti"/
# "döngəsi", never a bare stem): "Nizami küçəsi" + "ndə" = "Nizami
# küçəsində" ("on Nizami street"), verified against real generated STREET
# values, not assumed. Genitive/accusative do not need a separate entry
# here -- "küçəsi" + "nin"/"ni" happens to produce the identical surface
# string ("küçəsinin", "küçəsini") that a bare vowel-final stem's genitive/
# accusative already covers above, confirmed by direct testing.
# 2026-08-27 audit: added the copula (-dır/-dir/-dur/-dür, "X is ..."), which
# the hyphenated set above already had but this one did not -- "Ümid
# Fərəcovdur" lost its SURNAME. Personal endings (-yəm/-am/-əm) are
# deliberately NOT added here: without a hyphen to mark the boundary they are
# short enough to bite into ordinary names ("Adəm" is not "Ad" + "əm"), the
# same reasoning that keeps possessives out. Folded variants are derived, not
# listed -- see `_suffix_pattern`.
_AZ_FUSED_NOUN_SUFFIX_FORMS = (
    "lardan", "lərdən", "larda", "lərdə", "ların", "lərin", "lara", "lərə",
    "lar", "lər",
    "ndan", "ndən", "nda", "ndə", "na", "nə",
    "nın", "nin", "nun", "nün", "ın", "in", "un", "ün",
    "ya", "yə", "a", "ə",
    "nı", "ni", "nu", "nü",
    "dan", "dən", "da", "də",
    "dır", "dir", "dur", "dür",
)
_AZ_FUSED_NOUN_SUFFIX = _suffix_pattern(_AZ_FUSED_NOUN_SUFFIX_FORMS)

# A third delimiter form, alongside bare-fused and hyphen: an apostrophe
# before the suffix ("Qax'da", "Salyan'ın"). 39 spans in the live corpus.
# This is Turkish orthography rather than standard Azerbaijani -- see
# validate.turkish_contamination, which reports it as a language signal --
# but the annotation still has to be correct wherever it occurs.
_APOSTROPHES = "'’ʼ`"


def _fused_suffix_match(text: str, end: int, label: str | None) -> re.Match | None:
    """The `_AZ_FUSED_NOUN_SUFFIX` match immediately after `end`, for a label
    real Azerbaijani grammar can inflect, or None otherwise.

    Single source of truth for two callers that must never disagree about
    what counts as a recognized suffix: `_is_word_boundary` (should stopping
    the span here be treated as "embedded in a longer token", or as genuine
    grammar continuing the word?) and `_extend_span_for_suffix` below (how
    much of that grammar belongs inside the emitted span).
    """
    if label not in _INFLECTABLE_LABELS:
        return None
    after = text[end] if end < len(text) else ""
    if not after:
        return None
    # The suffix is matched on `match_key` (lower-cased, folded, one char for
    # one char): the noise injector's `all_caps`/`case_glitch` kinds run
    # AFTER labelling, and the LLM itself writes whole documents in capitals,
    # so `ŞƏMKIRDƏ` is the same grammar as `Şəmkirdə` (P2-6 fix 2).
    # An apostrophe delimiter is a third surface form of the same grammar
    # ("Qax'da"); skip over it and match the suffix behind it.
    if after in _APOSTROPHES:
        return _AZ_FUSED_NOUN_SUFFIX.match(match_key(text[end + 1:end + 11]))
    if not _WORDISH.match(after):
        return None
    return _AZ_FUSED_NOUN_SUFFIX.match(match_key(text[end:end + 10]))


def _extend_span_for_suffix(text: str, end: int, label: str | None) -> int:
    """Grows a resolved span's end to include a fused AZ case suffix.

    2026-08-26 tokenizer audit: a stem-only span --
    'Bakı' inside 'Bakıda' -- has no token boundary at its own end, because
    'Bakıda' is a SINGLE token in xlm-roberta-large's real SentencePiece
    vocabulary (confirmed by direct encoding, not assumed). A token
    classifier can never emit a span that ends mid-token, so a stem-only
    span is structurally unemittable even when the resolver correctly
    detects the mention. Recommendation adopted verbatim from that audit:
    include the suffix in the span. It is tokenizer-recoverable (the whole
    inflected word is either one token, matching the grown span exactly, or
    splits at a real morpheme boundary) and is what a masking system should
    redact anyway -- a de-identified name should not leave its case ending
    exposed.

    Deliberately NOT applied to `_AZ_HYPHEN_SUFFIX` matches (e.g.
    "10:17-də"): measured directly against the real tokenizer that the
    fused case needed the fix for -- the hyphen already tokenizes as its
    own piece with no space on either side ("10:17-də" -> ...,':17', '-',
    'də', ...), so a stem-only span ending right before the hyphen already
    lands on a real token boundary. Extending it would only lengthen the
    span for no tokenizer benefit.

    Only ever grows `end`; `start` is never touched by this function.
    """
    m = _fused_suffix_match(text, end, label)
    if not m:
        return end
    # +1 for the apostrophe delimiter when one is what triggered the match, so
    # the span covers "Qax'da" whole rather than stopping inside it.
    delim = 1 if (end < len(text) and text[end] in _APOSTROPHES) else 0
    return end + delim + len(m.group(0))


def _is_word_boundary(text: str, start: int, end: int,
                      label: str | None = None) -> bool:
    """Reject a match that sits inside a longer token.

    Without this, labeling every occurrence of the NAME "Ali" would also tag
    the "Ali" inside "Aliyev" or inside an email local part.

    '.', '+', '-' only count as continuing the token when a further wordish
    character sits beyond them too (the '.' in "acme.com", continuing past
    "acme"; the '-' inside a hyphen-grouped phone number). A bare '.'/'-'/'+'
    with nothing wordish past it -- most commonly a sentence-final period
    right after an injected value, e.g. "...AZ1762." -- is ordinary
    punctuation, not evidence the match sits inside a longer token.

    An Azerbaijani numeral (or any value) followed by a hyphenated
    grammatical suffix ("67-dir", "10:17-də", "5-ci") is a second such case:
    the character after the hyphen is a letter, so naive single-character
    lookahead reads it as "continuing" into a longer token the same way a
    genuine hyphen-joined phone/IBAN segment would. `_AZ_HYPHEN_SUFFIX`
    tells the two apart: a real suffix is a member of this closed set AND
    ends where the set says it ends (checked with a full lookahead, not one
    character) -- a value's next hyphen-joined segment does not.

    A proper noun (GIVENNAME/SURNAME/CITY/STREET) followed by a case suffix
    fused directly on with no hyphen at all -- "Bakıda", "Məmmədovun" -- is a
    third case, and the much more common one grammatically. `label` opts
    into checking `_AZ_FUSED_NOUN_SUFFIX` for exactly the labels real
    Azerbaijani noun inflection can apply to; every other label (numbers,
    emails, keys, ...) is never grammatically inflected in running text, so
    checking it there would only add false-accept risk for no benefit.
    """
    def continues(ch: str, beyond: str) -> bool:
        if not ch:
            return False
        if _WORDISH.match(ch):
            return True
        if ch in _JOIN_PUNCT:
            return bool(beyond) and _WORDISH.match(beyond) is not None
        return False

    before = text[start - 1] if start > 0 else ""
    before2 = text[start - 2] if start > 1 else ""
    after = text[end] if end < len(text) else ""
    after2 = text[end + 1] if end + 1 < len(text) else ""

    trailing_continues = continues(after, after2)
    # P2-6 fix 2: on match_key, so the capitals that the noise injector's
    # all_caps kind writes AFTER labelling (`MIKAYIL ƏLIYEV PR.-DƏ`, `SAAT
    # 06:50-DAN`) stay the boundary they were in lowercase. The case-sensitive
    # match made validate_corpus's resolver_drift re-check drop 7 correct
    # spans in batch 1.
    if (trailing_continues and after == "-"
            and _AZ_HYPHEN_SUFFIX.match(match_key(text[end + 1:end + 9]))):
        trailing_continues = False
    if (trailing_continues and after != "-"
            and _fused_suffix_match(text, end, label)):
        trailing_continues = False
    # A clock-time range joined by a bare hyphen (`14:00:00-15:30:00`): the
    # hyphen separates two TIME values, it does not continue one. v3 missed
    # 72 of 80 times with seconds on shadow-dev, 36 of them followed directly
    # by a dash (v3_shadow_shapes.md); v4_clean R10 labels both ends.
    if label == "TIME" and _CLOCK_ONLY.fullmatch(text[start:end]):
        if trailing_continues and after == "-" and _CLOCK_START.match(text, end + 1):
            trailing_continues = False
        if before == "-" and _CLOCK_END.search(text, max(0, start - 10), start - 1):
            before = ""

    leading_continues = continues(before, before2) if before else False
    # 2026-08-27 audit: `@` is in _WORDISH so an email local part is not split
    # mid-token, but that also made every social @mention unresolvable
    # ("@Şirinlı, qeyd etdiyiniz..." lost its SURNAME). A leading `@` is a
    # real boundary for the four ml_context labels. This does NOT reopen the
    # email case: in "john@Şirinli.az" the TRAILING check still rejects the
    # match, because "." followed by a wordish character continues the token.
    if leading_continues and before == "@" and label in _INFLECTABLE_LABELS:
        leading_continues = False

    return not (leading_continues or trailing_continues)


_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(:(\d{2}))?(\s*[APap][Mm])?$")
_CLOCK_ONLY = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
_CLOCK_START = re.compile(r"\d{1,2}:\d{2}(?!\d)")
_CLOCK_END = re.compile(r"(?<![\d:])\d{1,2}:\d{2}(?::\d{2})?$")


def _surface_variants(label: str, value: str) -> list[str]:
    """Alternate spellings of the SAME value that a writer may legitimately use.

    2026-08-27 audit: the planner mints "7:34 AM" while the model writes
    "07:34 AM" (or the reverse), and the verbatim search then fails, silently
    losing the annotation. Only zero-padding of the hour is varied -- this is
    a spelling of one value, not a different value, so the resolved span still
    matches `text` exactly and offsets stay exact.

    Returns alternates only; the caller tries the original first.

    P2-4c: a native Azerbaijani word ending in k/q softens before a vowel
    suffix (`Çiçək` -> `Çiçəyin`, `Bulaq` -> `Bulağın`; orthography norms).
    The softened stem is offered for the 4 inflectable labels; it is only
    ever placed where a recognised or declared suffix follows it, because
    `_is_word_boundary` refuses the bare stem anywhere else.
    """
    if label in _INFLECTABLE_LABELS and len(value) > 2 and value[-1] in "kq":
        return [value[:-1] + ("y" if value[-1] == "k" else "ğ")]
    if label != "TIME":
        return []
    m = _TIME_RE.match(value)
    if not m:
        return []
    hour, rest = m.group(1), value[len(m.group(1)):]
    out = []
    if len(hour) == 1:
        out.append("0" + hour + rest)
    elif hour.startswith("0"):
        out.append(hour[1:] + rest)
    return out


def _occurrence_allowed(label: str, value: str, text: str,
                        start: int, end: int) -> bool:
    """Shared span-resolution policy for both public entry points.

    A value long enough to be self-identifying may be labeled anywhere it
    appears verbatim. A short one (< 3 chars) may not: the audit found 539
    single-character spans in the corpus and 32 documents where a planned
    `AGE=3` had also tagged the `3` in `### 3. Kritik Ssenari`, because
    `resolve_claims` labeled every occurrence with no length rule at all
    while `complete_occurrences` already refused values under 3 characters.
    That asymmetry is what this function removes -- one policy, applied in
    both places.

    A short value survives only where the context actually identifies it:
    not in a structural position, and with a licensing anchor nearby.

    The same requirement applies at ANY length to the five `anchor_required`
    labels, independent of how long their value happens to be. "103/1" is
    five characters, so the length rule alone would wave it through, but a
    BUILDINGNUM with no street, building or address word anywhere near it is
    exactly as unidentifiable as a bare "3". Keeping the anchor rule here
    rather than only in the validator is what stops `complete_occurrences`
    from re-adding a span the validator is about to reject.

    D-17: a date followed (or preceded) by a clock time is a timestamp, not a
    DATE (`[12.05.2018 09:10:05]`). Without this, a document's own date
    labelled once made every gate demand the same string inside a log line
    be labelled too: 125 standalone dates in batch 2 could not be labelled.
    """
    if label == "DATE":
        from .standalone_dates import is_timestamp      # lazy: it imports this module
        if is_timestamp(text, start, end):
            return False
    if label in ANCHOR_REQUIRED:
        if is_structural_position(text, start, end):
            return False
        return has_anchor(label, text, start, end)
    if resolvable_unanchored(label, value):
        return True
    if is_structural_position(text, start, end):
        return False
    return has_anchor(label, text, start, end)


def resolve_claims(text: str, claims: list[dict],
                   blocked=(), declared=()) -> tuple[list[dict], int]:
    """Turn {label, text} claims into verified, non-overlapping spans.

    Used for LLM-produced examples, where only the value is known. Every
    occurrence of each claimed value is labeled, not just the first.

    `blocked` are declared decoy spans (C2 `_decoys`): no entity is placed
    over one, so the planned CITY `Bakı` is not labeled inside the policy
    decoy `Bakı layihəsi`.

    `declared` are (start, end) spans of inflected words the generator wrote
    on purpose (C2 `_suffixes`, P2-4c): a claimed value found at such a
    start is the stem of that word, and the span is the whole word
    (`Əsgər` -> `Əsgərgilə`, `Bakı` -> `Bakıdayam`). These forms are trusted
    ONLY where declared, never as an open pattern: the open suffix set above
    deliberately leaves out short endings that bite into ordinary names
    (`Adəm` is not `Ad` + `əm`).
    """
    declared_end = {s: e for s, e in declared}
    candidates = []
    dropped = 0
    for c in claims:
        label, value = c.get("label"), c.get("text")
        if not isinstance(label, str) or not isinstance(value, str):
            dropped += 1
            continue
        value = value.strip()
        if not value or label not in ENTITY_SET:
            dropped += 1
            continue
        candidates.append((label, value))

    # Longest first so a containing entity claims its span before a contained
    # one can -- makes the result independent of claim order.
    candidates.sort(key=lambda lv: len(lv[1]), reverse=True)

    claimed: list[tuple[int, int]] = [(s, e) for s, e in blocked]
    resolved: list[dict] = []

    for label, value in candidates:
        placed = 0
        # Try the value exactly as planned first, then each alternate SPELLING
        # of the same value (see `_surface_variants`). A containment test would
        # be wrong here -- "7:34 AM" IS a substring of "07:34 AM", so the exact
        # form is found, rejected by the word-boundary rule, and the variant
        # must still get its turn.
        #
        # P2-6 (batch 1): for the four name labels every spelling gets its
        # turn, not only when the exact form placed nothing: `Gülyanaq`
        # labelled twice left `Gülyanağın` (the softened genitive, grammar of
        # the same mention) unlabelled in the same document; the overlap check
        # below stops two spellings claiming one span. For TIME the exact
        # planned form still wins: a zero-padded `03:28 PM` elsewhere may be
        # an unrelated log timestamp.
        for surface in [value] + _surface_variants(label, value):
            if placed and label not in _INFLECTABLE_LABELS:
                break
            from_ = 0
            while True:
                idx = text.find(surface, from_)
                if idx == -1:
                    break
                s, e = idx, idx + len(surface)
                from_ = idx + 1
                word_end = declared_end.get(s)
                # the stem of a declared inflected word: the boundary that
                # matters, and the span, are the whole word's
                inside = word_end is not None and e < word_end
                if not _is_word_boundary(text, s, word_end if inside else e, label):
                    continue
                if any(s < ce and cs < (word_end if inside else e) for cs, ce in claimed):
                    continue
                if not _occurrence_allowed(label, surface, text, s, e):
                    continue
                e = word_end if inside else _extend_span_for_suffix(text, e, label)
                claimed.append((s, e))
                resolved.append({"start": s, "end": e, "label": label,
                                 "text": text[s:e]})
                placed += 1
                # NOTE: no break -- this is the audit fix. Every occurrence counts.
        if not placed:
            dropped += 1

    resolved.sort(key=lambda x: x["start"])
    return resolved, dropped


def complete_occurrences(text: str, entities: list[dict],
                         blocked=()) -> tuple[list[dict], int]:
    """Label any further occurrence of an already-labeled value.

    Safety net for the offline generator: sections record spans as they write,
    but a value can also appear in text a section did not author (a quoted
    block, a mixed-language insert, a value that happens to recur). This makes
    the 100%-repeat-mention guarantee hold by construction *and* by check.
    Occurrences inside `blocked` (declared decoy spans) are left alone.
    """
    if not entities:
        return entities, 0

    occupied = [(e["start"], e["end"]) for e in entities] + [(s, e) for s, e in blocked]
    by_value: dict[str, str] = {}
    for e in entities:
        # if the same string was labeled with two different types, do not guess
        prev = by_value.get(e["text"])
        if prev is None:
            by_value[e["text"]] = e["label"]
        elif prev != e["label"]:
            by_value[e["text"]] = ""        # ambiguous -- skip completion

    added = []
    for value, label in by_value.items():
        if not label:
            continue
        from_ = 0
        while True:
            idx = text.find(value, from_)
            if idx == -1:
                break
            from_ = idx + 1
            s, e = idx, idx + len(value)
            if any(s < ce and cs < e for cs, ce in occupied):
                continue
            if not _is_word_boundary(text, s, e, label):
                continue
            # Same policy as resolve_claims: a short value is completed only
            # where context identifies it. Previously this was a blanket
            # `len(value) < 3: continue`, which was the right instinct but
            # the wrong half of the codebase -- resolve_claims, which had no
            # such rule, is where the mislabels actually came from.
            if not _occurrence_allowed(label, value, text, s, e):
                continue
            e = _extend_span_for_suffix(text, e, label)
            occupied.append((s, e))
            added.append({"start": s, "end": e, "label": label,
                          "text": text[s:e]})

    if added:
        entities = sorted(entities + added, key=lambda x: x["start"])
    return entities, len(added)


def find_unlabeled_repeats(text: str, entities: list[dict], exempt=()) -> int:
    """Count occurrences of labeled values that carry no span. Should be 0.

    Uses the same `_occurrence_allowed` policy as the two functions above, so
    the checker and the completer cannot disagree about what counts as a
    missing mention -- a disagreement would make the repeat-mention gate
    unsatisfiable for short values. An occurrence inside an `exempt` span (a
    declared decoy) is deliberately unlabeled and is not counted.
    """
    occupied = [(e["start"], e["end"]) for e in entities] + [(s, e) for s, e in exempt]
    by_value: dict[str, str] = {}
    for e in entities:
        prev = by_value.get(e["text"])
        if prev is None:
            by_value[e["text"]] = e["label"]
        elif prev != e["label"]:
            by_value[e["text"]] = ""        # ambiguous -- skip, as elsewhere
    missing = 0
    for value, label in by_value.items():
        if not label:
            continue
        from_ = 0
        while True:
            idx = text.find(value, from_)
            if idx == -1:
                break
            from_ = idx + 1
            s, e = idx, idx + len(value)
            if any(s < ce and cs < e for cs, ce in occupied):
                continue
            if not _is_word_boundary(text, s, e, label):
                continue
            if not _occurrence_allowed(label, value, text, s, e):
                continue
            missing += 1
    return missing


# ---------------------------------------------------------------------------
# Planned values in the form the LLM actually wrote (P2-5 / P2-6)
# ---------------------------------------------------------------------------
#
# The LLM path plans (label, value) pairs and `pipeline.assemble_document` used
# to label only VERBATIM occurrences. Batch 1 (2026-10-02/03, 6,000 accepted
# documents, 11,015 attempts) measured what that costs, in both directions:
#
#   * Accepted with the value unlabelled (a false negative in training data):
#     the model wrote `Vaqif Məmmədov küçəsində` for `Vaqif Məmmədov küç.`
#     (49 streets), `İsağın` for `İsaq` (k/q softening), the value in capitals
#     or without Azerbaijani letters (`ŞƏMKIRDƏDIR`, `Gence`, `Xirdalanda`),
#     a Cyrillic name with a Latin suffix (`Мабудзаdanın`), or a misspelling
#     (`Hacıqabılda`). The verbatim search saw none of them, so the value was
#     "dropped" and stayed in the text unlabelled.
#   * Rejected although correctly labelled: 1,707 documents (15.5% of every
#     API call) whose planned name was labelled in an inflected form
#     (`Şamaxıda`), because the old check compared the planned value with the
#     entity TEXTS and then found the bare value inside the labelled word.
#
# `planned_forms` finds every occurrence of a planned value in any form, and
# says whether that form can be labelled exactly. Two rules make it safe:
#
#   1. A form is LABELLABLE only if `resolve_claims`, given the form's own
#      text, places exactly the same span again (`_reproducible`). That is the
#      invariant validate_corpus's `resolver_drift` re-check enforces, so
#      nothing labelled here can ever drift.
#   2. A form that is present but cannot be labelled exactly (a misspelling,
#      mixed script, a lowercase homograph, a token with a changed character)
#      is still reported. The caller rejects the document: a planned value in
#      the text is never left unlabelled (A2 rule 2).

_NAME_LABELS = {"GIVENNAME", "SURNAME", "CITY"}

# `locales/az.py` street(): stem + one of these five type words.
_STREET_VALUE = re.compile(
    r"^(?P<name>.+?)\s+(?P<type>küç\.|küçəsi|pr\.|prospekti|döngəsi)$")
# The type word as the LLM writes it, in match_key space: küç., küç.dədir,
# küçəsində, kuc.esinde, küçədə, pr., prospektindəki, döngəsinə ... A hyphen
# suffix (`pr.-da`) stays outside the span, as everywhere else in this module.
_STREET_TYPE_KEY = re.compile(r"kuc\.\w*|kuce\w*|pr\.\w*|prospekt\w*|donge\w*")
# Something that starts like a street word but is not one the pattern above
# can label (`prospek- tindəki`, a line-break hyphen): a trace, not a form.
_STREET_HINT_KEY = re.compile(r"(?:kuc|pros|pr\.|dong)[\w.\-]*")

# A different character makes a different secret: a case change is not a
# spelling of the same token.
_CASE_SENSITIVE = {"ACCESS_TOKEN", "API_KEY", "PRIVATE_KEY", "URL"}
# The same digits regrouped (`099 274 86 12` -> `099  274 86 12`, `0992748612`).
_DIGIT_LABELS = {"TELEPHONENUM", "PAYMENT_CARD_NUMBER", "ICCID", "AZ_VOEN"}
_MIN_DIGITS = 7
# A long value of which a piece survives: a token with one character changed.
_FRAGMENT_LABELS = {"ACCESS_TOKEN", "API_KEY", "PRIVATE_KEY", "URL", "EMAIL",
                    "IBAN", "PAYMENT_CARD_NUMBER", "ICCID"}
_FRAGMENT = 12
# A misspelt name is recognised by a stem of at least this many letters.
_MIN_STEM = 5
# Derivational suffixes (match_key space) that turn a name-like word into
# another word: -lI/-lIk (`Səadətli`, `Bakılı`), -çI, -sIz, -dar, -cA.
_DERIVED = re.compile(r"(?:l[iu]k?|c[iu]|s[iu]z|dar|c[ae])")


def _undouble(s: str) -> str:
    """`s` with every run of one repeated letter collapsed to one letter."""
    return re.sub(r"(.)\1+", r"\1", s)


# A name misspelt inside the word is looked for from this many letters on.
_MIN_EDIT_NAME = 6


def _edits_within(a: str, b: str, cap: int) -> bool:
    """Is `a` at most `cap` single-letter edits (drop, add, change) from `b`?"""
    if abs(len(a) - len(b)) > cap:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return False
        prev = cur
    return prev[-1] <= cap

_CYRILLIC_LETTER = re.compile(r"[Ѐ-ӿ]")
_LATIN_LETTER = re.compile(r"[A-Za-zÀ-ɏɐ-ʯ]")


@dataclass(frozen=True)
class PlannedForm:
    """One occurrence of a planned value.

    `kind` says how it was written: `exact`, `inflected`, `softened`,
    `street`, `reformatted`, `transliterated`, `english_spelling`, joined with
    `case`, `folded` or `spacing` where the letters differ from the plan that
    way. A form that cannot be labelled is `misspelled`, `mixed_script`,
    `fragment`, `lowercase_homograph`, `altered` (a secret with a changed
    character) or `...+unresolvable` (the resolver could not place it exactly).
    """
    start: int
    end: int
    kind: str
    labelable: bool


def _ws_pattern(key_value: str) -> re.Pattern:
    return re.compile(r"\s+".join(re.escape(p) for p in key_value.split()))


# After an `@`, a dotted name is an email domain (`info@bakı.az`), not a mention.
_AT_DOMAIN = re.compile(r"[\w-]+\.\w")


def _left_ok(text: str, s: int, label: str | None = None) -> bool:
    """Nothing word-like before `s`. A leading `@` is a boundary for the four
    name labels, as in `_is_word_boundary` (`@Nurbacı` in a chat, batch 2),
    unless what follows is an email domain."""
    if s == 0 or not _WORDISH.match(text[s - 1]):
        return True
    return (text[s - 1] == "@" and label in _INFLECTABLE_LABELS
            and not _AT_DOMAIN.match(text, s))


def _differences(surface: str, value: str) -> str:
    """How `surface` differs from `value` letter for letter: "" (it is the
    value), or "spacing", "case", "folded", joined with "+"."""
    if surface == value:
        return ""
    def norm(s: str) -> str:
        return " ".join(s.split())
    out = []
    if norm(surface) != surface or norm(value) != value or len(surface) != len(value):
        out.append("spacing")
    a, b = norm(surface), norm(value)
    if a != b:
        out.append("case" if a.casefold() == b.casefold() else "folded")
    return "+".join(out)


@functools.lru_cache(maxsize=1)
def _known_words() -> frozenset:
    """match_key of every given name (the foreign ones too, P2-15), city and
    common word: a misspelt suffix that spells one of them is that word, not a
    misspelling."""
    from .locales import az as AZ
    names = AZ.FIRST_M + AZ.FIRST_F + AZ.FOREIGN_NAMES.given_names()
    return frozenset({match_key(n) for n in names + AZ.CITIES + AZ.SETTLEMENTS}) \
        | _common_words()


def noisy_forms(value: str, case: str, label: str | None = None) -> dict:
    """`suffix.noisy` (wrong harmony, a dropped buffer, a doubled consonant,
    the colloquial -(y)nAn), minus a form that spells another real name or
    word: `Rabi` + dative with the buffer dropped is `Rabiə`, a name of its
    own (0.18% of the pool's noisy forms)."""
    from .targeted import suffix as SFX            # lazy; it imports only ..text
    try:
        correct = match_key(SFX.inflect(value, case, label))
    except (SFX.NotInflectable, KeyError):
        return {}
    known = _known_words()
    return {k: w for k, w in SFX.noisy(value, case, label).items()
            if match_key(w) == correct or match_key(w) not in known}


@functools.lru_cache(maxsize=4096)
def _renderer_suffixes(value: str, label: str) -> tuple[frozenset, tuple]:
    """Every suffix the P2-4c renderer puts on THIS value, in match_key space:
    (suffixes after the value itself, ((softened stem, suffixes), ...)).

    Stem-conditioned, so it may contain what the open set above deliberately
    leaves out (personal endings, -gil, -kı, -dək): `Adəm` is never read as
    `Ad` + `əm`, because `Ad` would have to be the planned value.
    """
    from .targeted import suffix as SFX            # lazy; it imports only ..text
    if label not in SFX.APPLIES:
        return frozenset(), ()
    vk = match_key(value)
    direct, soft = set(), {}
    for case in SFX.FORMS:
        try:
            words = [SFX.inflect(value, case, label)]
        except (SFX.NotInflectable, KeyError):
            continue
        # and the suffix as people misspell it (Bakıdə, Gəncəin, Bakıdda,
        # Leylaynan): still the name, so still labelled (noisy grammar)
        words += noisy_forms(value, case, label).values()
        for word in words:
            wk = match_key(word)
            if wk.startswith(vk):
                direct.add(wk[len(vk):])
            else:
                cut = SFX.split(word, value)
                soft.setdefault(wk[:cut], set()).add(wk[cut:])
    return frozenset(direct), tuple((k, frozenset(v)) for k, v in sorted(soft.items()))


@functools.lru_cache(maxsize=1)
def _common_words() -> frozenset:
    """Lowercase words a name can also be: the homograph list (P2-4d) and the
    Azerbaijani stopwords. A capitalised planned name written in lowercase is
    ambiguous when it is one of these (D-10), so it is not labelled."""
    try:
        from .targeted import homographs_az as H   # the list (P4-2)
    except ImportError:
        from .targeted import homographs_az_stub as H
    from .locales import LOCALES
    words = set(H.LONE_WORDS) | {e.get("az", "") for e in H.HOMOGRAPHS.values()}
    words |= set(LOCALES["az"].stopwords)
    return frozenset(match_key(w) for w in words if w)


def _reproducible(text: str, s: int, e: int, label: str) -> bool:
    """Would `resolve_claims`, given text[s:e] as the claim, place exactly
    (s, e)? Only such a span may be labelled: it cannot drift."""
    return (_left_ok(text, s, label) and _is_word_boundary(text, s, e, label)
            and _extend_span_for_suffix(text, e, label) == e
            and _occurrence_allowed(label, text[s:e], text, s, e))


def _word_end(text: str, key: str, e: int, label: str,
              suffixes: frozenset) -> int | None:
    """Where the word that starts with a value ending at `e` ends, when the
    rest of it is grammar the value takes; None when the value is only the
    start of a different word (`Əli` in `Əliyev`)."""
    if e >= len(text) or not _WORDISH.match(text[e]):
        if e < len(text) and text[e] in _APOSTROPHES:
            m = _fused_suffix_match(text, e, label)
            return e + 1 + len(m.group(0)) if m else e
        return e
    best = None
    if label in _INFLECTABLE_LABELS:
        m = _AZ_FUSED_NOUN_SUFFIX.match(key[e:e + 10])
        if m:
            best = e + len(m.group(0))
    for suf in suffixes:
        end = e + len(suf)
        if (suf and key.startswith(suf, e)
                and (end >= len(text) or not _WORDISH.match(text[end]))):
            if best is None or end > best:
                best = end
    return best


def _name_forms(text: str, key: str, label: str, value: str,
                spelling: str | None = None, kind0: str = "") -> list[PlannedForm]:
    """Occurrences of a name-like value: GIVENNAME, SURNAME, CITY (or the same
    value in another `spelling`, then tagged `kind0`)."""
    base = spelling or value
    if spelling is None:
        direct, soft = _renderer_suffixes(value, label)
    else:
        direct, soft = frozenset(), ()
    targets = [(match_key(base), direct, "")]
    targets += [(k, sufs, "softened") for k, sufs in soft]
    # the resolver's own softened spelling (`_surface_variants`) with the open
    # suffix set: covers values the renderer will not inflect
    targets += [(match_key(v), frozenset(), "softened") for v in _surface_variants(label, base)]
    out, seen = [], set()
    for stem_key, suffixes, kind1 in targets:
        if not stem_key:
            continue
        for m in _ws_pattern(stem_key).finditer(key):
            s, e = m.span()
            if s in seen or not _left_ok(text, s, label):
                continue
            end = _word_end(text, key, e, label, suffixes)
            if end is None:
                continue
            seen.add(s)
            parts = [kind0, kind1, "inflected" if end > e and not kind1 else "",
                     "" if kind1 else _differences(text[s:e], base)]
            kind = "+".join(p for p in parts if p) or "exact"
            labelable = True
            if (label in _NAME_LABELS and value[:1].isupper() and text[s].islower()
                    and match_key(value) in _common_words()):
                kind, labelable = "lowercase_homograph", False
            elif not _reproducible(text, s, end, label):
                kind, labelable = kind + "+unresolvable", False
            out.append(PlannedForm(s, end, kind, labelable))
    return out


def _street_forms(text: str, key: str, value: str) -> list[PlannedForm] | None:
    """The street name followed by its type word in any form (`küç.` ->
    `küçəsində`, `KÜÇ.DƏDIR`, `kuc.esinde`; `pr.` -> `prospektindəki`).
    None when `value` is not a `name + type word` street."""
    m = _STREET_VALUE.match(value)
    if not m:
        return None
    name = m.group("name")
    out = []
    for mm in _ws_pattern(match_key(name)).finditer(key):
        s, e = mm.span()
        if not _left_ok(text, s, "STREET"):
            continue
        ws = re.match(r"\s+", key[e:e + 8])
        tm = _STREET_TYPE_KEY.match(key, e + ws.end()) if ws else None
        if not tm:
            # the name alone may be the person the street is named after
            continue
        end = tm.end()
        diff = _differences(text[s:e], name)
        kind = "exact" if text[s:end] == value else "+".join(p for p in ("street", diff) if p)
        if _reproducible(text, s, end, "STREET"):
            out.append(PlannedForm(s, end, kind, True))
        else:
            out.append(PlannedForm(s, end, kind + "+unresolvable", False))
    return out


def _structured_forms(text: str, key: str, label: str, value: str) -> list[PlannedForm]:
    """Values that are not names: the same characters, perhaps re-spaced or
    re-cased, or (phones, cards, ICCID, VÖEN) the same digits regrouped."""
    from .validate import value_valid            # lazy: validate imports this module
    out = []
    for mm in _ws_pattern(match_key(value)).finditer(key):
        s, e = mm.span()
        if not _left_ok(text, s, label) or not _is_word_boundary(text, s, e, label):
            continue
        surface = text[s:e]
        diff = _differences(surface, value)
        if not diff:
            if _occurrence_allowed(label, surface, text, s, e):
                out.append(PlannedForm(s, e, "exact", True))
            continue
        if label in _CASE_SENSITIVE and diff != "spacing":
            out.append(PlannedForm(s, e, "altered", False))
            continue
        ok = value_valid(label, surface)[0] and _reproducible(text, s, e, label)
        out.append(PlannedForm(s, e, diff if ok else diff + "+unresolvable", ok))
    if not any(f.kind == "exact" for f in out):
        # the resolver's alternate spelling (`7:34 AM` / `07:34 AM`) stands for
        # the value only where the value itself is absent, as in resolve_claims
        for variant in _surface_variants(label, value):
            for mm in re.finditer(re.escape(variant), text):
                s, e = mm.span()
                if (_left_ok(text, s, label) and _is_word_boundary(text, s, e, label)
                        and _occurrence_allowed(label, variant, text, s, e)):
                    out.append(PlannedForm(s, e, "variant", True))
    if label in _DIGIT_LABELS:
        digits = re.sub(r"\D", "", value)
        if len(digits) >= _MIN_DIGITS:
            for mm in re.finditer(r"\+?\d[\d \-.()/]*\d", text):
                s, e = mm.span()
                surface = mm.group(0)
                if re.sub(r"\D", "", surface) != digits or surface == value:
                    continue
                if any(f.start == s and f.end == e for f in out):
                    continue
                ok = value_valid(label, surface)[0] and _reproducible(text, s, e, label)
                out.append(PlannedForm(s, e, "reformatted" if ok
                                       else "reformatted+unresolvable", ok))
    return out


# P2-6 (batch 2, 2026-10-03): 36 times in 31 accepted batch-2 documents a
# planned date was written in another format, 33 of them an ISO date in the
# Azerbaijani order (`1991-09-14` -> `14.09.1991`) -- the brief's own DATE
# hint said "or write it as dd.mm.yyyy". The verbatim search saw neither: in
# 29 documents that was the date's only form, so the run counted it as
# "dropped by the model" (the README's DATE 30) and left it unlabelled. A
# date in the text is the planned value when it is the same calendar day.
_AZ_MONTHS = ("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
              "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr")
_MONTH_RE = "|".join(_AZ_MONTHS)
_DATE_WORDED = re.compile(r"(\d{1,2})\s+(" + _MONTH_RE + r")\w*\s+(\d{4})", re.IGNORECASE)
_DATE_ISO = re.compile(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})")
_DATE_DMY = re.compile(r"(\d{1,2})([./-])(\d{1,2})\2(\d{4})")
_DATE_IN_TEXT = re.compile(
    r"(?<![\w.])(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}([./-])\d{1,2}\1\d{4}"
    r"|\d{1,2}\s+(?:" + _MONTH_RE + r")\w*\s+\d{4})(?!\w)", re.IGNORECASE)


def _calendar_date(value: str) -> tuple[int, int, int] | None:
    """(year, month, day) of a date written as yyyy-mm-dd, dd.mm.yyyy (day
    first, the Azerbaijani order; month first only when the day-first reading
    is impossible) or `d <month> yyyy`; None for anything else."""
    import datetime

    def real(y: int, m: int, d: int) -> tuple[int, int, int] | None:
        try:
            datetime.date(y, m, d)
        except ValueError:
            return None
        return y, m, d

    m = _DATE_WORDED.search(value)
    if m:
        month = next(i for i, name in enumerate(_AZ_MONTHS, 1)
                     if match_key(m.group(2)).startswith(match_key(name)))
        return real(int(m.group(3)), month, int(m.group(1)))
    m = _DATE_ISO.search(value)
    if m:
        return real(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = _DATE_DMY.search(value)
    if m:
        a, b, y = int(m.group(1)), int(m.group(3)), int(m.group(4))
        return real(y, b, a) or real(y, a, b)
    return None


def _date_forms(text: str, value: str, found: list[PlannedForm]) -> list[PlannedForm]:
    """The planned date written in another format: the same calendar day."""
    from .validate import value_valid            # lazy: validate imports this module
    day = _calendar_date(value)
    if day is None:
        return []
    out = []
    for mm in _DATE_IN_TEXT.finditer(text):
        s, e = mm.span()
        surface = mm.group(0)
        if surface == value or any(f.start <= s and e <= f.end for f in found):
            continue
        if _calendar_date(surface) != day:
            continue
        ok = value_valid("DATE", surface)[0] and _reproducible(text, s, e, "DATE")
        out.append(PlannedForm(s, e, "reformatted" if ok else "reformatted+unresolvable", ok))
    return out


def _word_after(text: str, s: int) -> int:
    w = re.match(r"\w+", text[s:])
    return s + (w.end() if w else 1)


def _lost_forms(text: str, key: str, label: str, value: str) -> list[PlannedForm]:
    """Traces of a planned value that no form above can label: a misspelt
    name (`Hacıqabılda` for `Hacıqabul`), a Cyrillic name with Latin letters
    in it (`Мабудзаdanın`), a street word the patterns do not know, a piece
    of a long value (a token with one character changed).

    A misspelt NAME is only looked for in a capitalised word when the plan is
    capitalised: lowercase words sharing a stem are ordinary vocabulary."""
    out = []
    street = _STREET_VALUE.match(value) if label == "STREET" else None
    if label in _NAME_LABELS or street:
        name = street.group("name") if street else value
        base = match_key(name)
        capital = name[:1].isupper()
        for k in (1, 2, 3):
            stem = base[:-k]
            if len(stem) < _MIN_STEM:
                break
            for m in re.finditer(re.escape(stem), key):
                s = m.start()
                if not _left_ok(text, s, label) or (capital and not text[s].isupper()):
                    continue
                end = _word_after(text, s)
                if key.startswith(base, s) and _DERIVED.match(key, s + len(base)):
                    # the whole value plus a derivational suffix is another
                    # word (`Səadətli` "happy", `Bakılı`), as `Əliyev` is
                    # not `Əli`; a changed ending (`Ağarzayev` + `a`) is not
                    continue
                if street:
                    ws = re.match(r"\s+", key[end:end + 8])
                    tm = _STREET_HINT_KEY.match(key, end + ws.end()) if ws else None
                    if not tm:
                        continue
                    end = tm.end()
                out.append(PlannedForm(s, end, "misspelled", False))
        if not street:
            # A letter doubled or undoubled (`Tərttərdə` for `Tərtər`,
            # batch 2, D-16c). The stem search above cannot see it when the
            # change sits inside the stem: compare with doubled letters
            # collapsed instead.
            flat = _undouble(base)
            seen = {f.start for f in out}
            for w in re.finditer(r"\w+", text):
                s = w.start()
                if (len(flat) < 4 or s in seen or (capital and not text[s].isupper())
                        or not _left_ok(text, s, label)):
                    continue
                wk = key[s:w.end()]
                if wk.startswith(base) or not _undouble(wk).startswith(flat):
                    continue
                if _DERIVED.match(_undouble(wk), len(flat)):
                    continue
                out.append(PlannedForm(s, w.end(), "misspelled", False))
            # A letter dropped, added or changed inside the name: `Seyidnovun`
            # for `Seyidxanov`, `Müxtərov` for `Müxtarov`, `Zaqalatada` for
            # `Zaqatala`, and self-corrections (`Bəyimacı (yox, Bəyimbacı)`):
            # 31 documents in clean batches 1-4 (P2-5, batch 4). The stem
            # search sees only a changed ending, the rule above only a doubled
            # letter. A capitalised word whose start is within one edit of a
            # 6-7 letter name, or two of a longer one, is a misspelling of it.
            # Short words are dense, so a short name's first three letters must
            # match (`NÖMRƏSİ` is not `Növrəs`), a long name's first two.
            if capital and len(base) >= _MIN_EDIT_NAME:
                cap, head = (1, 3) if len(base) < 8 else (2, 2)
                seen = {f.start for f in out}
                for w in re.finditer(r"\w+", text):
                    s, e = w.span()
                    wk = key[s:e]
                    if (s in seen or wk[:head] != base[:head] or not text[s].isupper()
                            or wk.startswith(base) or len(wk) < len(base) - cap
                            or not _left_ok(text, s, label)):
                        continue
                    cuts = range(len(base) - cap, min(len(wk), len(base) + cap) + 1)
                    if any(_edits_within(wk[:n], base, cap) for n in cuts):
                        out.append(PlannedForm(s, e, "misspelled", False))
        if street:
            for mm in _ws_pattern(base).finditer(key):
                s, e = mm.span()
                ws = re.match(r"\s+", key[e:e + 8])
                tm = _STREET_HINT_KEY.match(key, e + ws.end()) if ws else None
                if _left_ok(text, s, label) and tm:
                    out.append(PlannedForm(s, tm.end(), "street+unresolvable", False))
        if _CYRILLIC_LETTER.search(name):
            for w in re.finditer(r"\w+", text):
                word = w.group(0)
                if not (_CYRILLIC_LETTER.search(word) and _LATIN_LETTER.search(word)):
                    continue
                wk = match_key(word)
                n = 0
                while n < min(len(wk), len(base)) and wk[n] == base[n]:
                    n += 1
                if n >= 3:
                    out.append(PlannedForm(w.start(), w.end(), "mixed_script", False))
    if label in _FRAGMENT_LABELS and len(value) >= 16:
        for i in range(0, len(value) - _FRAGMENT + 1, 4):
            piece = value[i:i + _FRAGMENT]
            if any(c.isspace() for c in piece):
                continue
            p = text.find(piece)
            while p != -1:
                out.append(PlannedForm(p, p + _FRAGMENT, "fragment", False))
                p = text.find(piece, p + 1)
    return out


@functools.lru_cache(maxsize=1)
def _english_spelling():
    from .values import az_english_spelling      # lazy: values is heavy
    return az_english_spelling


@functools.lru_cache(maxsize=1)
def _latin_spelling():
    from .values import _load_transliterators    # lazy, as values.py does
    nt = _load_transliterators()
    return lambda v: nt.transliterate(v, "ru", "latin")


def planned_forms(text: str, label: str, value: str) -> list[PlannedForm]:
    """Every occurrence of the planned (label, value) in `text`, in any form.

    Overlapping findings are merged: a labellable form wins over a trace of
    the same word, and a longer form over a shorter one inside it.
    """
    value = (value or "").strip()
    if not value or not label:
        return []
    key = match_key(text)
    found: list[PlannedForm] = []
    if label == "STREET":
        street = _street_forms(text, key, value)
        found += street if street is not None else _name_forms(text, key, label, value)
    elif label in _INFLECTABLE_LABELS:
        found += _name_forms(text, key, label, value)
        if _CYRILLIC_LETTER.search(value):
            try:
                other = _latin_spelling()(value)
            except Exception:                    # noqa: BLE001 -- best effort
                other = ""
            if other and other != value:
                found += _name_forms(text, key, label, value, other, "transliterated")
        else:
            other = _english_spelling()(value)
            if other and other != value:
                found += _name_forms(text, key, label, value, other, "english_spelling")
    else:
        found += _structured_forms(text, key, label, value)
        if label == "DATE":
            found += _date_forms(text, value, found)
    found += _lost_forms(text, key, label, value)
    if label == "DATE":
        # D-17: inside a timestamp the planned date is not a DATE at all, so it
        # is not a form of the planned value either (batch 3 wrote planned
        # dates into log lines: `[14.04.2018 04:02] INFO`, llm_az_001518).
        from .standalone_dates import is_timestamp      # lazy: it imports this module
        found = [f for f in found if not is_timestamp(text, f.start, f.end)]

    found.sort(key=lambda f: (not f.labelable, -(f.end - f.start), f.start))
    kept: list[PlannedForm] = []
    for f in found:
        if not any(k.start < f.end and f.start < k.end for k in kept):
            kept.append(f)
    kept.sort(key=lambda f: f.start)
    return kept


def _in_timestamp(text: str, start: int, end: int) -> bool:
    from .standalone_dates import is_timestamp          # lazy: it imports this module
    return is_timestamp(text, start, end)


def _covered(start: int, end: int, label: str, entities) -> bool:
    """Labelled: overlapped by an entity of the planned label, or lying inside
    any entity (a planned GIVENNAME `Nizami` inside the STREET `Nizami küçəsi`)."""
    for e in entities:
        es, ee = e["start"], e["end"]
        if es <= start and end <= ee:
            return True
        if e["label"] == label and es < end and start < ee:
            return True
    return False


def find_unlabelled_planned(text: str, entities: list[dict], planned,
                            decoys=()) -> list[dict]:
    """Planned values present in `text` but not labelled there. Should be [].

    Two rules, both per occurrence:
      * every form `planned_forms` finds outside the declared decoys must be
        covered by a label (`_covered`);
      * the older verbatim rule, kept so nothing it caught is lost: a value
        with NO labelled occurrence must not appear verbatim anywhere outside
        the decoys and the labels (a planned AGE `34` inside an undeclared
        `REF340012`). The old check ran this whenever the entity TEXT differed
        from the plan, so a value labelled as `Şamaxıda` counted as "never
        labelled" -- the 1,707 false rejections of batch 1.

    `planned` is [(label, value), ...]; `decoys` are (start, end) spans.
    Each finding: label, value, start, end, text, kind, labelable.
    """
    out: list[dict] = []
    decoys = list(decoys)
    for label, value in planned:
        value = (value or "").strip()
        if not label or not value:
            continue
        labelled_any = False
        for f in planned_forms(text, label, value):
            if any(ds < f.end and f.start < de for ds, de in decoys):
                continue
            if _covered(f.start, f.end, label, entities):
                labelled_any = True
                continue
            out.append({"label": label, "value": value, "start": f.start,
                        "end": f.end, "text": text[f.start:f.end],
                        "kind": f.kind, "labelable": f.labelable})
        if labelled_any:
            continue
        i = text.find(value)
        while i != -1:
            j = i + len(value)
            if (not any(ds <= i and j <= de for ds, de in decoys)
                    and not any(e["start"] <= i and j <= e["end"] for e in entities)
                    and not any(o["start"] <= i and j <= o["end"] for o in out)
                    and not (label == "DATE" and _in_timestamp(text, i, j))):
                out.append({"label": label, "value": value, "start": i, "end": j,
                            "text": value, "kind": "embedded", "labelable": False})
            i = text.find(value, i + 1)
    return out


def planned_value_present(text: str, label: str, value: str) -> bool:
    """Is the planned value in `text` in a form that can be labelled?"""
    return any(f.labelable for f in planned_forms(text, label, value))


def resolve_planned(text: str, planned, blocked=()) -> tuple[list[dict], int]:
    """`resolve_claims` for the LLM path's planned values, in every form the
    model wrote them (P2-6 fix 1).

    First the claims themselves, exactly as `resolve_claims` places them;
    then every other form `planned_forms` can label exactly (`küçəsində` for
    `küç.`, `ŞƏMKIRDƏDIR` for `Şəmkir`, `Əsgərgilə`, a re-spaced phone). Forms
    it cannot label are left for `find_unlabelled_planned`, which the caller
    turns into a rejection. `planned` is [(label, value), ...]. Returns
    (entities, number of planned values placed nowhere).
    """
    planned = [(lab, (val or "").strip()) for lab, val in planned if lab and val]
    resolved, _ = resolve_claims(text, [{"label": lab, "text": val} for lab, val in planned],
                                 blocked=blocked)
    occupied = [(s, e) for s, e in blocked] + [(r["start"], r["end"]) for r in resolved]
    for label, value in sorted(planned, key=lambda lv: len(lv[1]), reverse=True):
        for f in planned_forms(text, label, value):
            if not f.labelable or any(f.start < oe and os < f.end for os, oe in occupied):
                continue
            occupied.append((f.start, f.end))
            resolved.append({"start": f.start, "end": f.end, "label": label,
                             "text": text[f.start:f.end]})
    resolved.sort(key=lambda x: x["start"])
    nowhere = 0
    for label, value in planned:
        forms = planned_forms(text, label, value)
        if not any(r["label"] == label and any(f.start < r["end"] and r["start"] < f.end
                                                for f in forms) for r in resolved):
            nowhere += 1
    return resolved, nowhere
