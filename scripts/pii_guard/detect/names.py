"""The `ml_context` tier: GIVENNAME, SURNAME, CITY, STREET.

These four cannot be found by regex -- that is exactly why the taxonomy puts
them in their own tier and why this repo is training an NER model for them.
This module is the seam where that model plugs in.

Three backends:

* **`TransformerBackend`** -- a token-classification model, which is what
  `model/train.py` produces. Point `GuardConfig.ner_model` at a checkpoint
  directory and it is used. Labels come from the model's own `id2label`, so a
  model trained on this repo's 55-label BIO scheme works with no mapping.

* **`GazetteerBackend`** -- the offline fallback. It reuses the generator's
  own AZ name and place pools (`piigen.locales`), plus a capitalised-token
  heuristic gated on a title/address cue. It is *deliberately weaker* and it
  says so: `available` is True but `high_confidence` is False.

* **`CombinedBackend`** -- what `resolve_backend` actually returns when a
  model IS configured and the gazetteer is allowed: the union of both
  backends' detections, not a choice between them. This exists because of a
  measured result, not a guess: run against the 10 realistic multilingual
  sample documents `gen_test_docs.py` generates, the real trained checkpoint
  (`your-hf-org/masking-multilingual`) found 0 PERSON entities in 9 of the 10
  documents and 1 in the 10th, against the gazetteer's 1-9 per document over
  the same set -- the model missed 32 of 33 real name mentions the gazetteer
  caught. A checkpoint this far from its training distribution (the corpus
  this repo trains on is synthetic single-sentence/short-span examples; these
  test documents are realistic multi-paragraph prose) is not something a
  production service can treat as sufficient on its own, but it is not
  worthless either -- it can still catch something the gazetteer's AZ-only
  pools and generic capitalised-run heuristic miss entirely (a name in a
  script the gazetteer has no pool for, e.g.), and `entities.resolve_overlaps`
  (already called once, downstream, over every tier's output -- see
  `detect/__init__.py`'s module docstring) already knows how to reconcile two
  detectors firing on the same span, so combining is just "let both run and
  hand the union to the machinery that already exists for exactly this".
  Nothing in `HybridDetector` or `mask.py` needed to change for this.

The fail-closed rule lives in `resolve_backend`. With
`require_ml_context=True` (the default) and no usable backend, it raises --
because silently falling back means every name and street in the document
goes to the external model in the clear, which is the exact failure the whole
service exists to prevent. The gazetteer counts as "usable" only when the
caller has explicitly accepted it via `allow_gazetteer`; a caller that
explicitly refuses the gazetteer (e.g. because its false-positive rate is
unacceptable for their use case) gets the transformer alone, not silently
upgraded back to combined.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "model"))

from ..entities import LABELS, Detection, cue_window  # noqa: E402
from ._chunk import chunk_spans  # noqa: E402


class MlContextUnavailable(RuntimeError):
    """No usable name/address detector. Fail closed rather than under-mask."""


# --------------------------------------------------------------------------
# gazetteer fallback
# --------------------------------------------------------------------------
_TITLE_CUE = re.compile(
    r"(?i)\b(mr|mrs|ms|miss|dr|prof|sir|madam|"
    r"cənab|cenab|xanım|xanim|müəllim|muellim|"
    r"г-н|г-жа|госп|"
    r"bay|bayan|say[ıi]n)\b\.?\s*$", re.UNICODE)

_ADDRESS_CUE = re.compile(
    r"(?i)\b(street|st\.|avenue|ave\.|road|rd\.|lane|boulevard|blvd|"
    r"küç|kuce|prospekt|məhəllə|mehelle|"
    r"улиц|ул\.|проспект|переулок|"
    r"sokak|cadde|cad\.|bulvar|"
    r"address|ünvan|unvan|адрес|adres|lives?\s+at|resides?\s+at)",
    re.UNICODE)

#: A street TYPE word as the run's own LAST word -- "Nizami Street",
#: "Füzuli küçəsi". Streets in Baku (and elsewhere) are routinely named
#: after people ("Nizami" is both a common given name AND the country's
#: most-named street, after the poet), so a bare pool-membership check on
#: the run's first word alone misclassified "Nizami Street" as a PERSON --
#: found by testing against a realistic multi-sentence address, not a
#: single-entity smoke test. Checked before pool membership for exactly
#: this reason: the run's OWN structure is stronger evidence than a name
#: pool hit that a common name and a common street both draw from.
_STREET_SUFFIX = re.compile(
    r"(?i)(street|st\.?|avenue|ave\.?|road|rd\.?|lane|ln\.?|boulevard|blvd\.?|"
    r"küçəsi|kucesi|prospekti|prospekt|döngəsi|"
    r"улица|переулок|проспект|бульвар|"
    r"caddesi|cad\.?|sokağı|sokak|bulvarı)$", re.UNICODE)

#: A role/heading/label word as the run's own LAST word -- "HR Business
#: Partner", "Backend Engineer", "Payroll Setup Confirmation", "National
#: ID". The generic fallback below (no pool match, no cue -- just "this is
#: capitalized") cannot otherwise tell a real name from a job title or a
#: slide heading: in English both are indistinguishable multi-word
#: Title-Case runs. Found by reading the actual sanitized output of a real
#: generated PPTX end to end, not a targeted unit test -- a slide's own
#: title ("New Hire Spotlight") and body job titles ("HR Business
#: Partner", "Backend Engineer") were all coming out as PERSON. Same
#: priority reasoning as `_STREET_SUFFIX`: the run's OWN last word is
#: stronger evidence about what KIND of phrase this is than the mere fact
#: that it happens to be capitalized. English-heavy because English prose
#: is what actually hit this; not exhaustive -- see the module docstring's
#: note on the gazetteer being deliberately weak.
_NON_NAME_SUFFIX = re.compile(
    r"(?i)\b(partner|engineer|manager|director|officer|specialist|"
    r"coordinator|analyst|consultant|representative|administrator|"
    r"associate|assistant|supervisor|technician|developer|designer|"
    r"architect|advisor|adviser|executive|lead|head|chief|president|team|"
    r"members|"
    r"spotlight|confirmation|summary|overview|review|update|report|"
    r"agenda|meeting|session|training|onboarding|handbook|policy|setup|"
    r"section|plan|process|proposal|roadmap|checklist|guideline|"
    r"guidelines|procedure|workshop|webinar|briefing|presentation|"
    r"id|number|no|code|reference|ref)$", re.UNICODE)

#: A RUN of 1-4 consecutive Title-Case tokens, not a single token. Matching
#: single capitalized words first and merging adjacent ones afterward (the
#: original design) split "Main Street" into two placeholders and, worse,
#: never gave the merge step a reason to fire for two ordinary proper nouns
#: with no shared label -- matching the whole run up front and classifying
#: it once is what makes "John Smith" and "Main Street" each come out as one
#: span. Found by a smoke test, not by inspection.
#: `[ \t]+` between words, NOT `\s+`. A bare `\s+` matches newlines too,
#: which let this regex walk straight across `extract.base.SEGMENT_JOIN`
#: ("\n\n", the separator `pipeline.sanitize_document` uses between
#: extracted segments) and merge a name from one PPTX slide's body text
#: with an unrelated capitalized word from that slide's speaker notes into
#: ONE placeholder -- found by the format-adapter test suite, not by
#: inspection: `[PERSON_001]` ended up mapped to the literal string
#: `"Ali Karimov\n\nCall Ali"`.
_CAPRUN = re.compile(
    r"\b[A-ZƏÇĞİÖŞÜА-ЯЁ][\w'’-]{1,}(?:[ \t]+[A-ZƏÇĞİÖŞÜА-ЯЁ][\w'’-]{1,}){0,3}\b",
    re.UNICODE)

#: Capitalised words that are never a person/place in document prose.
_STOP_CAPS = frozenset({
    "The", "This", "That", "These", "Those", "There", "Their", "They",
    "Invoice", "Date", "Total", "Subtotal", "Tax", "Amount", "Due", "Page",
    "Dear", "Sincerely", "Regards", "Attachment", "Subject", "From", "To",
    "Cc", "Bcc", "Sent", "Received", "Re", "Fwd", "Note", "Notes", "Terms",
    "Conditions", "Agreement", "Contract", "Section", "Article", "Clause",
    "Company", "Ltd", "Llc", "Inc", "Gmbh", "Mmc", "Asc",
    "January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday",
    # Common name-introducing lead-ins that sit directly adjacent to a name
    # with no lowercase word breaking the capitalized run (so the run-based
    # matcher would otherwise absorb them into the name span). Not
    # exhaustive -- this heuristic gazetteer cannot be exhaustive across
    # languages, which is exactly why `GuardConfig.ner_model` exists; this
    # list only covers the cases actually hit while building this module.
    "Please", "Kindly", "Regards", "Hello", "Hi", "Hey", "Thanks", "Best",
    "Attn", "Attention", "Contact",
    # "Contact" was missing despite being this very docstring's own example
    # two paragraphs up ("Trimming keeps 'Contact' as ordinary prose...")
    # -- found by testing sanitize_document_to_docx against a realistic
    # "Contact Jane Roberts by phone..." sentence, where it silently
    # absorbed "Contact" into the PERSON span and dropped the word from the
    # masked output entirely (STEP 6: the exact context-preservation
    # failure this stopword list exists to prevent).
    "Adım", "Adı", "Benim", "Mənim", "Meni", "Menim",       # az/tr "my name"
    "Later", "Then", "Also", "Call", "Meanwhile", "Additionally",
    # Ordinary document-boilerplate words that happen to also be real (if
    # rare) entries in `scripts/name_pools.py`'s pooled name data --
    # found by testing `gazetteer_names.py`'s comprehensive, always-on
    # tier against the full 11-sample corpus, where each of these fired
    # as a false-positive GIVENNAME/SURNAME with nothing else in the
    # sentence to lose an overlap to. "Confidential" is the most severe:
    # `gen_test_docs.py`'s own footer boilerplate ("Confidential --
    # internal use only...") put it in EVERY sample, so left unfixed it
    # would have masked part of the footer as a person in all 11
    # documents. Shared via `find_capitalized_runs`, so this also
    # benefits `GazetteerBackend`, which has the identical exposure
    # whenever it is the active backend (previously untested against
    # this corpus, since evaluations always configured a real model).
    "Confidential", "Welcome", "Senior", "Bank", "Field", "Human", "Group",
    "Reason", "Patient", "Letter", "Salary", "Private", "Key",
    # "Key" (a real, common EN surname -- count 31,882, not a rare
    # collision like "My") is excluded anyway: "PRIVATE KEY" in a PEM
    # block header (sample_03's "-----BEGIN PRIVATE KEY-----") got pool-
    # matched as GIVENNAME+SURNAME, then propagated (via
    # `detect.__init__._propagate_strong_mentions`) to the unrelated
    # lowercase "private key fragment" mention elsewhere in the same
    # document. IT/security documents saying "private key" are common
    # enough in this corpus's own document types that the false-positive
    # cost outweighs the (already-covered-by-NER-when-configured) recall
    # loss for the rare real surname.
    #
    # This lookup is exact-case (see `find_capitalized_runs`: a plain
    # `in _STOP_CAPS` set membership check, not casefolded -- true of
    # every existing entry here too, not something this pass changed).
    # A PEM header is conventionally ALL CAPS ("-----BEGIN PRIVATE
    # KEY-----"), not Title Case, so "Private"/"Key" alone did not
    # actually stop it -- found by re-testing after adding them, not
    # assumed to work.
    "PRIVATE", "KEY",
    "Alan", "Değer", "Banka", "Kira", "Kiracı", "Ocak", "Tutar",   # tr
    "Əmək", "İnsan",                                              # az
})


@dataclass(frozen=True, slots=True)
class CapRun:
    """One stopword-trimmed run of 1-4 consecutive Title-Case tokens."""

    words: tuple[str, ...]
    #: absolute (start, end) per word in `words`, same order
    word_spans: tuple[tuple[int, int], ...]
    start: int
    end: int
    text: str


def find_capitalized_runs(text: str) -> list[CapRun]:
    """Every candidate proper-noun run in `text` -- the "what looks like a
    name/place" search shared by `GazetteerBackend` (AZ-only pools, also
    classifies CITY/STREET) and `gazetteer_names.py` (the comprehensive,
    always-on GIVENNAME/SURNAME tier across all four languages this repo
    has a name pool for). Both need the exact same candidate set, so this
    is the one place `_CAPRUN` and the `_STOP_CAPS` trim live -- see their
    own docstrings for the real bugs (multi-word merging, segment-boundary
    crossing, "Contact John Smith" losing its verb) this logic already
    carries fixes for. A second, independent implementation would risk
    re-introducing any of them.
    """
    out: list[CapRun] = []
    for m in _CAPRUN.finditer(text):
        run, run_start = m.group(0), m.start()
        word_spans = [(wm.group(0), wm.start(), wm.end())
                     for wm in re.finditer(r"\S+", run)]
        words = [w for w, _, _ in word_spans]

        lead = 0
        while lead < len(words) and words[lead] in _STOP_CAPS:
            lead += 1
        tail = len(words)
        while tail > lead and words[tail - 1] in _STOP_CAPS:
            tail -= 1
        if lead >= tail:
            continue

        trimmed = words[lead:tail]
        start = run_start + word_spans[lead][1]
        end = run_start + word_spans[tail - 1][2]
        abs_spans = tuple((run_start + s, run_start + e)
                          for _, s, e in word_spans[lead:tail])
        out.append(CapRun(words=tuple(trimmed), word_spans=abs_spans,
                          start=start, end=end, text=text[start:end]))
    return out


@lru_cache(maxsize=1)
def _pools() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """(given, surname, city) name pools from the generator's own locale data."""
    given: set[str] = set()
    surnames: set[str] = set()
    cities: set[str] = set()
    try:
        from piigen.locales import LOCALES
        az = LOCALES.get("az")
        for attr in ("FIRST_M", "FIRST_F", "first_names_m", "first_names_f"):
            given |= {str(x) for x in getattr(az, attr, ()) or ()}
        for attr in ("SURNAME_STEMS", "surname_stems", "SURNAMES"):
            surnames |= {str(x) for x in getattr(az, attr, ()) or ()}
        for attr in ("CITIES", "cities"):
            cities |= {str(x) for x in getattr(az, attr, ()) or ()}
    except Exception:
        pass
    return (frozenset(g.casefold() for g in given if g),
            frozenset(s.casefold() for s in surnames if s),
            frozenset(c.casefold() for c in cities if c))


import logging  # noqa: E402

_LOG = logging.getLogger("pii_guard")
_warned_once = False


def _warn_weak_backend_once() -> None:
    global _warned_once
    if not _warned_once:
        _warned_once = True
        _LOG.warning(
            "pii_guard: using the offline GAZETTEER name/address detector -- "
            "it reliably covers Azerbaijani names/cities (from this repo's "
            "own locale pools) and generic 'Capitalized Word' runs, but has "
            "no real understanding of names in other scripts or unusual "
            "capitalization. Configure GuardConfig.ner_model with a trained "
            "checkpoint before relying on this in production.")


@dataclass(slots=True)
class GazetteerBackend:
    """Offline name/place detector. Weak on purpose -- see module docstring."""

    name = "gazetteer"
    available: bool = True
    high_confidence: bool = False

    def detect(self, text: str, labels: frozenset[str] | None = None) -> list[Detection]:
        _warn_weak_backend_once()
        given, surnames, cities = _pools()
        out: list[Detection] = []
        for cap_run in find_capitalized_runs(text):
            words = list(cap_run.words)
            start, end = cap_run.start, cap_run.end
            run = cap_run.text

            # cue_window, not a bare slice: an address cue ("küçəsi",
            # street) in one sentence used to license an unrelated word
            # STARTING THE NEXT SENTENCE, purely because it fell within 40
            # raw characters -- "...AZ1078. Kira bedeli..." made the
            # ordinary Turkish word "Kira" ("rent") register as a street
            # name. Found by testing a realistic multi-sentence paragraph,
            # not a single-clause smoke test.
            before = cue_window(text, start, 40, before=True)

            # Priority: the run's OWN trailing street-type word first (a
            # structural fact about this specific run), THEN a pool match on
            # the first word, then an explicit cue, then -- only for a
            # multi-word run -- a generic fallback. Street suffix goes
            # first because a name pool and a street-naming convention both
            # draw from the same vocabulary ("Nizami Street" is named after
            # a person called Nizami): checking pool membership first
            # mislabels every such street as a PERSON. This order is what
            # lets "123 Main Street" resolve to STREET (address cue beats
            # the generic fallback) while "John Smith" (no cue, no AZ pool
            # match) still gets caught as PERSON via the fallback rather
            # than being invisible.
            head = words[0].casefold()
            label = score = None
            if len(words) >= 2 and _STREET_SUFFIX.search(words[-1]):
                label, score = "STREET", 0.6
            elif head in cities:
                label, score = "CITY", 0.65
            elif head in given:
                label, score = "GIVENNAME", 0.65
            elif head in surnames:
                label, score = "SURNAME", 0.6
            elif _TITLE_CUE.search(before):
                label, score = "GIVENNAME", 0.5        # "Mr. <run>"
            elif _ADDRESS_CUE.search(before):
                label, score = "STREET", 0.45
            elif (len(words) >= 2 and not (start == 0 and end == len(text))
                  and not _NON_NAME_SUFFIX.search(words[-1])
                  and not any(re.search(r"\d", w) for w in words)):
                # generic multi-word "Title Case Run" -- the fallback for
                # names this service has no gazetteer entry for at all
                # (most of them: chathal's users are not Azerbaijani-only).
                # Gated on two negative signals, not just "is capitalized":
                # a role/heading word as the run's own last word
                # (_NON_NAME_SUFFIX -- "HR Business Partner", "New Hire
                # Spotlight") or any digit anywhere in the run (a real
                # person's name is never mixed with digits; an employee/
                # ticket/ID code run together with a capitalized label word,
                # e.g. "ID AZ5567123", is not a name even though it shares
                # the run's capitalization shape). Both found the same way:
                # reading a real generated PPTX's actual sanitized output
                # end to end, not a targeted unit test.
                label, score = "GIVENNAME", 0.35
            if label is None:
                continue
            if labels is not None and label not in labels:
                continue
            out.append(Detection(start=start, end=end, label=label,
                                 text=run, score=score, source="gazetteer"))
        return _merge_adjacent(out, text)


# --------------------------------------------------------------------------
# transformer backend
# --------------------------------------------------------------------------
@dataclass(slots=True)
class TransformerBackend:
    """Real trained-checkpoint NER, delegating to `model/predict.py`.

    `model/predict.py` did not exist when this class was first written, so
    the original version called a generic `transformers.pipeline(
    "token-classification")` directly -- no sliding-window/stride handling,
    no verified BIO decode, no punctuation-boundary pre-tokenizer patch.
    `model/predict.py` (built independently, for the Excel/CSV/TXT track)
    is the correct implementation of the same contract `prepare_splits.py`
    actually trained against: same tokenizer patch, same stride=256,
    windows merged by the same longest-span-wins policy `resolver.py` and
    `entities.resolve_overlaps` both already use. Delegating to it instead
    of re-implementing it is the same "reuse, don't duplicate" principle
    this whole package tries to follow elsewhere (`piigen.checksums`,
    `piigen.config.DETECTION_TIERS`).

    By default only `_ML_CONTEXT_LABELS` is kept from the model's own
    output -- `model/predict.py`'s `hybrid_detect_entities` also layers on
    `pattern_fallback.find_pattern_spans`, which is NOT used here, and this
    matters: `pattern_fallback`'s DATE finder has no personal-context gate
    at all -- it would mask "Invoice date: 2026-09-01" outright, exactly
    the case STEP 2 says must never happen and `detect.anchored` exists to
    prevent. The other pattern-tier labels (EMAIL, phone, IBAN, national
    IDs) are also already covered, with real checksum validation, by this
    package's own `detect.patterns` -- running them twice from two sources
    is wasted work `resolve_overlaps` would just have to reconcile anyway.
    So: take the model's opinion ONLY on the four labels nothing else in
    this package can find at all.

    Set `restrict_to_ml_context=False` to take ALL 27 taxonomy labels from
    the model instead -- used only when `GuardConfig.ner_full_taxonomy=True`
    (see `HybridDetector.__init__`), which is also the only case where
    `detect.patterns`/`detect.anchored`/the gazetteer are skipped entirely,
    so there is no double-detection to reconcile and none of the reasoning
    above about redundant/ungated pattern-tier output applies. Explicit,
    gated, off-by-default user choice (2026-09-15): ship the model alone
    once it is fixed, but until then `patterns.py`/`anchored.py` stay in
    the codebase exactly as they are, unused in this mode but intact for
    when they are needed again.
    """

    model_path: str
    name: str = "transformer"
    available: bool = True
    high_confidence: bool = True
    restrict_to_ml_context: bool = True
    _loaded: tuple | None = None

    #: See the class docstring -- deliberately narrower than "every label
    #: the model predicts", unless `restrict_to_ml_context=False`.
    _ML_CONTEXT_LABELS = frozenset({"GIVENNAME", "SURNAME", "CITY", "STREET"})

    def _load(self):
        if self._loaded is None:
            from predict import load_model  # noqa: E402 (model/ on sys.path)
            self._loaded = load_model(self.model_path)
        return self._loaded

    def detect(self, text: str, labels: frozenset[str] | None = None) -> list[Detection]:
        """Chunked on purpose -- see `_chunk.py`'s module docstring.

        `your-hf-org/masking-multilingual`'s confidence in a real name/address
        decays as more tokens follow it in the same call and can collapse
        to ~0 well inside `predict.py`'s own 512-token window (measured
        collapse around ~47 tokens on this package's own `gen_test_docs.py`
        fixtures -- see docs/pii_guard_model_notes.md). `predict.py`'s
        stride/window machinery does not help here: the paragraphs affected
        are far short of 512 tokens, so it never engages at all. Splitting
        the TEXT into short clauses before it ever reaches `detect_entities`
        keeps the model's own context window short enough that a real name
        stays visible; chunk_spans never cuts inside a value (a name spread
        across a chunk boundary would be silently missed at either half),
        so this is safe even though the model's own windowing operates
        independently on top of each chunk.
        """
        from predict import detect_entities  # noqa: E402
        model, tokenizer, id2label = self._load()
        out: list[Detection] = []
        for offset, end_ in chunk_spans(text):
            chunk = text[offset:end_]
            if not chunk.strip():
                continue
            for span in detect_entities(chunk, model, tokenizer, id2label):
                label = span["label"]
                if self.restrict_to_ml_context and label not in self._ML_CONTEXT_LABELS:
                    continue
                if label not in LABELS:
                    # defensive only -- id2label should already only ever
                    # produce a taxonomy label; guards against a corrupted or
                    # mismatched checkpoint producing something Detection's
                    # own __post_init__ would otherwise raise on.
                    continue
                if labels is not None and label not in labels:
                    continue
                start = int(span["start"]) + offset
                stop = int(span["end"]) + offset
                if start >= stop:
                    continue
                # model/predict.py does not expose a per-span confidence
                # (its own decode walks argmax label ids, not logit
                # probabilities) -- 0.85 reflects "a real trained model
                # said so", comfortably above _PROPAGATION_MIN_SCORE (0.45)
                # so a model-found name seeds propagation to its other
                # mentions in the document.
                out.append(Detection(start=start, end=stop, label=label,
                                     text=text[start:stop], score=0.85, source="ner"))
        return out


# --------------------------------------------------------------------------
# combined backend
# --------------------------------------------------------------------------
@dataclass(slots=True)
class CombinedBackend:
    """Gazetteer + transformer, union of both -- see module docstring for
    the measured recall gap that motivates running both instead of picking
    one. `available`/`high_confidence` report True: a real trained model
    genuinely is in the mix, even though (currently) most of the actual
    recall still comes from the gazetteer half.
    """

    transformer: TransformerBackend
    name: str = "combined"
    available: bool = True
    high_confidence: bool = True

    def detect(self, text: str, labels: frozenset[str] | None = None) -> list[Detection]:
        # Independent detectors over the same text -- neither needs to know
        # about the other's output. Overlaps between the two (or with the
        # pattern/anchored tiers) are reconciled once, downstream, by
        # `entities.resolve_overlaps` (called from `mask.apply_mask`), the
        # same place every other cross-tier overlap in this package is
        # already resolved -- see `detect/__init__.py`'s module docstring.
        out = self.transformer.detect(text, labels)
        out.extend(GazetteerBackend().detect(text, labels))
        return out


def _merge_adjacent(dets: list[Detection], text: str) -> list[Detection]:
    """Join `GIVENNAME SURNAME` runs so a full name gets one placeholder."""
    if not dets:
        return dets
    dets = sorted(dets, key=lambda d: d.start)
    merged: list[Detection] = []
    for d in dets:
        if merged:
            prev = merged[-1]
            gap = text[prev.end:d.start]
            if (gap in (" ", "  ") and {prev.label, d.label} <= {"GIVENNAME", "SURNAME"}
                    and prev.label != d.label):
                merged[-1] = Detection(
                    start=prev.start, end=d.end, label="GIVENNAME",
                    text=text[prev.start:d.end],
                    score=min(prev.score, d.score), source=prev.source)
                continue
        merged.append(d)
    return merged


# --------------------------------------------------------------------------
# backend selection -- this is where fail-closed lives
# --------------------------------------------------------------------------
def resolve_backend(model_path: str | None, *, required: bool,
                    allow_gazetteer: bool = True):
    """Pick a name/address backend, or refuse.

    `required=True` (the default posture) means: if nothing trustworthy is
    available, raise. Returning a no-op detector here would leave every name
    and street in the document unmasked while the pipeline reported success.

    A configured, loadable model does NOT mean "use the model alone" --
    see `CombinedBackend`'s docstring for the measured reason. Only a
    caller who has explicitly set `allow_gazetteer=False` gets the
    transformer by itself.
    """
    if model_path:
        try:
            transformer = TransformerBackend(model_path=model_path)
            transformer._load()           # load now so failure surfaces here
            return CombinedBackend(transformer=transformer) if allow_gazetteer else transformer
        except Exception as exc:
            if required:
                raise MlContextUnavailable(
                    f"the configured NER model {model_path!r} could not be "
                    f"loaded ({type(exc).__name__}: {exc}). Refusing to "
                    f"continue: names and addresses would go to the external "
                    f"model unmasked.") from exc

    if allow_gazetteer:
        return GazetteerBackend()

    if required:
        raise MlContextUnavailable(
            "no ml_context backend available (no NER model configured and the "
            "gazetteer fallback is disabled). Names, cities and streets cannot "
            "be detected, so the text cannot be safely sanitised.")
    return None
