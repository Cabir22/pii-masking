"""Unconditional, comprehensive given-name/surname gazetteer tier.

Why this exists on top of `TransformerBackend`/`GazetteerBackend`: the
real model (`your-hf-org/masking-multilingual`) has a confirmed, measured
blind spot for SOME specific names -- score ~0 at every context length
tested, including total isolation (see `docs/pii_guard_model_notes.md`
"Root cause #2", `sample_07`'s "Elvin"/"Məmmədov"). That is a training-
data coverage gap, not fixable by chunking, prompting, or any other
pipeline-level trick -- retraining is the only real fix, and that's out
of scope here. What IS in scope: a name the model missed can often still
be caught by simple pool membership, because "is this exact string a
known human name" doesn't need a neural network. `Elvin` and `Məmmədov`
are both in `piigen.locales.az`'s name data (verified directly before
writing this module, not assumed) -- the model just never learned to say
so.

Deliberately UNCONDITIONAL: this tier runs every time, in
`detect/__init__.py`'s `HybridDetector.detect()`, alongside
`detect.patterns`/`detect.anchored` -- NOT gated behind
`self._names is None` the way `GazetteerBackend` is (that class is a
*fallback* used only when no NER backend is configured at all; this
module runs *in addition to* whatever backend is active, model or not).
A high-confidence model detection and a lower-confidence gazetteer hit on
the same span both feed `entities.resolve_overlaps`, which already picks
the higher-scoring one -- so nothing new has to be built to "prefer the
model when both agree": this tier's scores (0.55/0.65, see below) are
kept below `TransformerBackend`'s 0.85 specifically so the existing
overlap-resolution machinery does that automatically. When the model
finds nothing at all for a span, there is nothing to overlap with, and
the gazetteer detection survives on its own -- which is exactly the
`sample_07` recovery case this module exists for.

Broader than `GazetteerBackend`'s AZ-only pools on purpose: reuses
`scripts/name_pools.py`, which already loads real, sizeable name data for
all four languages this repo handles (AZ ~8.5k+6.9k given / ~19k
surnames from `piigen.locales.az`; EN ~22k given names -- the public-
domain Moby Word List -- + ~152k US Census surnames; RU ~3.1k+1.4k given
/ ~99k surnames; TR ~6.5k+7.4k given / ~18k surnames from
`scripts/tr_names_out/`) built for the corpus generator's own 60/40
name-substitution pipeline. Reused here rather than duplicated -- the
data-cleaning work (rejecting dirty CSV rows, normalising case, gendering
Russian entries) already happened once in `name_pools.py`, and a second,
independently-loaded copy would be a second thing to keep correct.
Pools are unioned ACROSS all four languages rather than kept per-document-
language, because this corpus's own documents code-switch names across
languages on purpose (`sample_09`, a Russian-language document, names an
Azerbaijani guarantor; `sample_11` mixes Azerbaijani and English in one
letter) -- restricting matching to "the document's own language" would
miss exactly the cases that matter most.

What this tier does NOT do: it never touches CITY or STREET (that
remains `GazetteerBackend`'s job when no model is configured, and the
model's job otherwise) -- `name_pools.py` only has given-name and
surname data, and conflating "name pool" with "address pool" would be a
scope change beyond what was asked. It also does not replace
`GazetteerBackend`: that class is still the no-model fallback and still
covers CITY/STREET; this module only adds GIVENNAME/SURNAME recall on
top, everywhere, always.

Precision cost, measured and mitigated, not hidden: pool membership
alone cannot tell "Elvin" (a person) from "Bakı"/"Nizami"/"Atatürk" (a
city, a street, a street) -- unioning ~270k+ entries across 4 languages
guarantees some collide with ordinary vocabulary or with place names.
Found by testing this tier against the full 11-sample corpus, not
assumed away: a city-name exclusion (`_combined_pools` above), a
street-suffix/address-cue disqualifier (both checked before pool
membership, right below), and shared `detect.names._STOP_CAPS` additions
for document-boilerplate collisions ("Confidential", "PRIVATE KEY", ...)
together closed most of what testing found. What is NOT closed (see
`docs/pii_guard_model_notes.md`'s addendum for the full, current list):
patronymic words in AZ/RU three-part names ("Tofiq" in "Elvin Tofiq oğlu
Məmmədov"), place names outside the AZ-only city pool ("İstanbul"), a
`cue_window` sentence-boundary edge case with period-abbreviated cues
("ул." parsed as a sentence end), and fictional proper nouns with no
gazetteer of their own (a company name, "Zirvə").
"""

from __future__ import annotations

import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ..entities import Detection, cue_window  # noqa: E402
from .names import _ADDRESS_CUE, _STREET_SUFFIX, find_capitalized_runs  # noqa: E402

#: A word that is part of a multi-word capitalized run (e.g. the "Elvin" in
#: "Elvin Tofiq") is somewhat stronger evidence than a single bare word
#: standing alone -- the surrounding capitalization pattern itself is a
#: weak signal this is a proper-noun context, not just a coincidence.
#: Both are kept well below TransformerBackend's 0.85 (see module
#: docstring: that's what makes "prefer the model when both agree"
#: automatic via entities.resolve_overlaps) and above
#: detect.__init__._PROPAGATION_MIN_SCORE (0.45), so either can still seed
#: coreference propagation to the name's other mentions in the document.
_SCORE_IN_MULTIWORD_RUN = 0.65
_SCORE_LONE_WORD = 0.55

#: Below this length, pool membership stops being good evidence: at
#: hundreds of thousands of pooled entries across 4 languages, short
#: strings collide with ordinary words too easily -- found in testing via
#: a real false positive ("My", as in "My name is Jane Doe", is a genuine
#: but rare EN pool entry: given_names_m/f count 1.0, surnames count
#: 267.0). Every real name in this project's own test corpus is >=4 chars
#: (checked directly: Rauf, Amir, Elif, Aygün, ...), and this mirrors the
#: same threshold `detect.__init__._PROPAGATION_MIN_LEN` already uses for
#: an identical reason ("short strings collide with ordinary vocabulary
#: too easily").
_MIN_WORD_LEN = 4


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


@lru_cache(maxsize=1)
def _combined_pools() -> tuple[frozenset[str], frozenset[str]]:
    """(given-name set, surname set), casefolded, unioned across every
    language `scripts/name_pools.py` has a pool for. Loaded once per
    process -- these pools are large (hundreds of thousands of entries
    combined) and never change at runtime.

    Known place names are subtracted from both sets before returning.
    Real bug this fixes, found by testing against `sample_07` (a document
    literally titled "Bakı Dövlət Universiteti", Azerbaijani for "Baku
    State University"): "Bakı" is a genuine (if rare) entry in the TR
    surname pool, so without this exclusion the document's own header --
    and the city name inside the applicant's address -- were masked as
    [PERSON], not [CITY]/left alone. `detect.names._pools()`'s AZ city
    list (97 real Azerbaijani cities/towns, from this repo's own
    `piigen.locales` data) is reused here rather than duplicated, same as
    everywhere else in this module: a name that is ALSO a documented
    place should never silently become a person label. This does not
    catch every place-name collision (there is no comprehensive street-
    name pool to check against the same way, so "Nizami" the poet's name
    is still wrongly caught when it's actually part of a street name,
    "Nizami küçəsi" -- a real, known, unfixed-by-this-pass limitation,
    not silently hidden).
    """
    from name_pools import load_all_pools  # noqa: E402 (scripts/ on sys.path)
    from .names import _pools as _az_pools  # noqa: E402

    given: set[str] = set()
    surnames: set[str] = set()
    for pool in load_all_pools().values():
        for entry in pool.get("given_names_m", ()):
            given.add(_norm(entry.name))
        for entry in pool.get("given_names_f", ()):
            given.add(_norm(entry.name))
        for entry in pool.get("surnames", ()):
            surnames.add(_norm(entry.name))

    _, _, cities = _az_pools()
    given -= cities
    surnames -= cities
    return frozenset(given), frozenset(surnames)


def detect(text: str, labels: frozenset[str] | None = None) -> list[Detection]:
    """GIVENNAME/SURNAME detections from comprehensive name-pool
    membership. Independent of any model and of `GazetteerBackend`'s
    smaller AZ-only pools -- see module docstring for why both exist.
    """
    if labels is not None and not ({"GIVENNAME", "SURNAME"} & labels):
        return []
    given_set, surname_set = _combined_pools()

    out: list[Detection] = []
    for cap_run in find_capitalized_runs(text):
        words = cap_run.words
        n = len(words)
        # A street TYPE word as the run's own LAST word ("Nizami Street",
        # "Atatürk Caddesi") is a structural fact about the run itself --
        # stronger evidence than any single word's pool membership, and
        # for the same reason `GazetteerBackend` already checks this
        # first (see `names.py`'s own comment: streets are routinely
        # named after people, so pool membership alone mislabels every
        # such street as a PERSON). Found here the same way: testing
        # against sample_07's real "Nizami küç. 28" wrongly produced
        # GIVENNAME 'Nizami'. Skip the WHOLE run rather than only the
        # last word -- "Nizami" is the one pool hit, but it is the run's
        # own street-suffix structure that disqualifies it, not the word.
        if n >= 2 and _STREET_SUFFIX.search(words[-1]):
            continue
        # A lone word immediately followed by an address-suffix word that
        # is NOT itself capitalized ("Nizami küç. 28" -- Azerbaijani
        # abbreviates "küçəsi"/street lower-case, so it never joins the
        # capitalized run above) reaches here with n==1 and would
        # otherwise be pool-matched as a person. Checked via the SAME
        # `_ADDRESS_CUE` regex/`cue_window` `GazetteerBackend` already
        # uses for its own (lower-priority, AFTER pool membership)
        # address-cue fallback -- reused here as a disqualifier, checked
        # BEFORE pool membership, because (matching the same reasoning as
        # the street-suffix check above) a name pool and a street-naming
        # convention draw from the same vocabulary, so structural address
        # context should win. Found via `sample_07`'s real "Nizami küç.
        # 28" wrongly producing GIVENNAME 'Nizami'. Checked on BOTH sides:
        # Russian puts the cue word first ("улица Низами 88" -- "street
        # Nizami 88"), found via `sample_05`/`sample_09`'s real "улица
        # Низами" wrongly producing GIVENNAME 'Низами' even after the
        # after-only version of this check was added.
        if n == 1:
            after = cue_window(text, cap_run.end, 20, before=False)
            before = cue_window(text, cap_run.start, 20, before=True)
            if _ADDRESS_CUE.search(after) or _ADDRESS_CUE.search(before):
                continue
        score = _SCORE_IN_MULTIWORD_RUN if n >= 2 else _SCORE_LONE_WORD
        for i, word in enumerate(words):
            if len(word) < _MIN_WORD_LEN:
                continue
            key = _norm(word)
            is_given = key in given_set
            is_surname = key in surname_set
            if not is_given and not is_surname:
                continue
            if is_given and is_surname:
                # Ambiguous across languages/pools (a name that is a given
                # name in one language's pool and a surname in another's,
                # or genuinely both, e.g. many English surnames are also
                # given names). Positional tie-break: the LAST word of a
                # multi-word run reads as a surname by the "Given Surname"
                # convention this corpus's documents actually use; every
                # other position defaults to GIVENNAME.
                label = "SURNAME" if (n >= 2 and i == n - 1) else "GIVENNAME"
            else:
                label = "GIVENNAME" if is_given else "SURNAME"
            if labels is not None and label not in labels:
                continue
            start, end = cap_run.word_spans[i]
            out.append(Detection(start=start, end=end, label=label,
                                 text=text[start:end], score=score,
                                 source="gazetteer_names"))
    return out
