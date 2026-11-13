"""Which look-alikes the translation keeps verbatim (D-54b, problem B).

A look-alike (an unlabelled value that resembles PII) is protected like an
entity: it is replaced by a slot, the model translates around it, and it is
spliced back byte for byte, because its exact broken shape is the training
signal. Until D-54b the protected strings were `_spec.hard_negatives`, and
in the LLM batches those are phrases, not values: `kampaniya CMP-3287`,
`vəsiqə nömrəsi AB-5115`, `SIM kartın ICCID nömrəsi 891`. Spliced back
verbatim, the phrase put Azerbaijani words into the English, Turkish or
Russian text, and the leftover-Azerbaijani check rejected the document: 10 of
16 English rejects, 10 of 17 Turkish and 6-8 of 20 Russian in the 300-
document test (reports/translation_test/README.md). Phrases without `ə`-type
letters (`kampaniya ...`) passed that check and shipped untranslated.

What is protected now, in `text` positions:

  * every `_decoys` span (the generator's own record of each look-alike's
    exact position) unless it is a word look-alike -- a homograph, a
    sentence-initial `Bölmədə`, a city or surname inside a company name (a
    `policy_*` kind without a digit). Those are words, and a word is
    translated: `SUMQAYIT` must become `Сумгаит` in Russian. The `policy_*`
    kinds with digits are dummy values (`policy_test_card` 5555555555554444,
    `policy_passport_dummy` P12345678, `policy_version_time` 20:16) and are
    kept;
  * a `_spec.hard_negatives` phrase that no `_decoys` span falls inside,
    every occurrence, as before;
  * either of these, if it contains Azerbaijani letters, only by its
    digit-bearing tokens: `kartın CVV kodu 96-0` keeps `96-0` and translates
    the rest.

Positions, not strings: a three-digit ICCID prefix searched for by value
would also match inside every longer number in the document.
"""
from __future__ import annotations

import re

AZ_LETTERS = re.compile(r"[əƏğĞıİşŞçÇöÖüÜ]")

# `_decoys` kinds whose look-alike is a word, not a value (v4.1 train,
# 19 Oct 2026). A `policy_*` kind is one too when its value has no digit:
# in v4.1 the name/place kinds never have one and the dummy-value kinds
# (test card, dummy passport, sequential and version times) always do.
WORD_KINDS = frozenset({
    "homograph_noun", "sentence_initial_locative", "sentence_initial_genitive",
    "line_start_control", "namelist_control", "village_descriptor",
    "kinship_possessive", "common_word_surname", "role_word_control",
    "signature_title_only",
})

_LEAD = "([{\"'«“"
_TRAIL = ".,;:!?)]}\"'»”"


def is_word_lookalike(kind: str | None, value: str) -> bool:
    if not kind:
        return False
    if kind in WORD_KINDS:
        return True
    return kind.startswith("policy_") and not any(c.isdigit() for c in value)


def value_parts(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """The parts of `text[start:end]` to keep verbatim: all of it, or -- if it
    holds Azerbaijani letters -- its runs of digit-bearing tokens."""
    v = text[start:end]
    if not AZ_LETTERS.search(v):
        return [(start, end)]
    out: list[tuple[int, int]] = []
    for m in re.finditer(r"\S+", v):
        tok = m.group(0)
        if not any(c.isdigit() for c in tok) or AZ_LETTERS.search(tok):
            continue
        a, b = start + m.start(), start + m.end()
        while a < b and text[a] in _LEAD:
            a += 1
        while b > a and text[b - 1] in _TRAIL:
            b -= 1
        if a >= b:
            continue
        if out and not text[out[-1][1]:a].strip():
            out[-1] = (out[-1][0], b)          # `5555 1234` stays one value
        else:
            out.append((a, b))
    return out


def protected_ranges(rec: dict) -> list[tuple[int, int]]:
    """Sorted, non-overlapping `(start, end)` ranges of `rec["text"]` to keep
    verbatim. Never overlaps an entity."""
    text = rec["text"]
    n = len(text)
    taken = [(e["start"], e["end"]) for e in rec.get("entities") or []]
    out: list[tuple[int, int]] = []

    def add(a: int, b: int) -> None:
        if a < b and not any(a < y and x < b for x, y in taken + out):
            out.append((a, b))

    declared: list[tuple[int, int]] = []
    for d in rec.get("_decoys") or []:
        s, e = d.get("start"), d.get("end")
        if not (isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= n):
            continue
        declared.append((s, e))
        if not is_word_lookalike(d.get("kind"), text[s:e]):
            for a, b in value_parts(text, s, e):
                add(a, b)

    phrases = {h for h in (rec.get("_spec") or {}).get("hard_negatives") or []
               if isinstance(h, str) and h}
    # Longest first, so a phrase that contains another claims its region.
    for h in sorted(phrases, key=len, reverse=True):
        i = text.find(h)
        while i >= 0:
            j = i + len(h)
            # A declared span inside the phrase already decided what to keep.
            if not any(i < y and x < j for x, y in declared):
                for a, b in value_parts(text, i, j):
                    add(a, b)
            i = text.find(h, i + 1)
    return sorted(out)


def protected_values(rec: dict) -> list[str]:
    """The protected strings, for checks that excuse them in the output."""
    return [rec["text"][a:b] for a, b in protected_ranges(rec)]
