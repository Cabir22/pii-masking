"""Hybrid detection: patterns + anchors + NER + name gazetteer, combined once.

Tier -> detector, following `data/schema.md`'s own split:

    pattern (16 labels)        detect.patterns         regex + checksum
    hybrid  (2 labels)         detect.patterns         regex + licensing word
    anchor_required (5)        detect.anchored         anchor + personal context
    ml_context (4)             detect.names            NER, or gazetteer fallback
    (GIVENNAME/SURNAME only)   detect.gazetteer_names   comprehensive name-pool
                                                        membership, UNCONDITIONAL

`gazetteer_names` is not part of the `ml_context` tier's backend choice --
it runs every time, on top of whichever `ml_context` backend is active
(model or fallback), specifically to recover names the model scores ~0 for
even in complete isolation (a confirmed training-data gap, not a pipeline
bug -- see `docs/pii_guard_model_notes.md`). Its scores are kept below the
model's own, so when both fire on the same span `entities.resolve_overlaps`
naturally keeps the model's answer; when the model finds nothing, the
gazetteer hit survives on its own. See `detect/gazetteer_names.py`'s module
docstring for the full reasoning. The one exception: `GuardConfig.ner_only`
("the model alone -- no gazetteer, not even as a supplement") switches this
tier off too, otherwise that flag would silently keep a name gazetteer on.

Running every tier and resolving overlaps once at the end is what makes the
combination safe: an IBAN that a phone pattern also matched is masked as an
IBAN (longer span wins), and a name the NER found inside an already-matched
email local part does not produce a second, offset-corrupting edit.

`GuardConfig.ner_full_taxonomy=True` is the one exception to all of the
above: patterns/anchored/gazetteer are skipped entirely and the model alone
covers all 27 labels (see `HybridDetector.__init__` and
`detect.names.TransformerBackend`'s `restrict_to_ml_context` flag). Explicit,
gated, off-by-default user choice (2026-09-15) -- ship the model alone once
it's fixed; `detect/patterns.py` and `detect/anchored.py` stay in the
codebase unused in that mode, not deleted, for when they're needed again.
"""

from __future__ import annotations

import re
import unicodedata

from ..config import GuardConfig
from ..entities import Detection
from . import anchored, gazetteer_names, patterns
from .names import MlContextUnavailable, TransformerBackend, resolve_backend  # noqa: F401

__all__ = ["HybridDetector", "MlContextUnavailable", "DetectorError"]

#: A detection below this score has too little evidence on its own to be
#: propagated to OTHER occurrences of the same string -- see
#: `_propagate_strong_mentions`. Excludes exactly the gazetteer's weakest
#: tier (the generic "looks like Title Case" fallback, scored 0.35) so a
#: coincidentally-capitalized ordinary word doesn't get treated as a
#: confirmed entity and start matching itself all over the document.
_PROPAGATION_MIN_SCORE = 0.45
#: Values shorter than this are not propagated even from a strong mention --
#: short strings collide with ordinary vocabulary too easily ("Ali" the
#: name vs. a stray 3-letter fragment elsewhere).
_PROPAGATION_MIN_LEN = 4


class DetectorError(RuntimeError):
    """A detector failed. In strict mode this aborts the whole request."""


class HybridDetector:
    """The service's detector. Construct once, reuse across documents."""

    def __init__(self, config: GuardConfig | None = None):
        self.config = config or GuardConfig()
        self._full_taxonomy = self.config.ner_full_taxonomy
        if self._full_taxonomy:
            backend = TransformerBackend(
                model_path=self.config.ner_model,
                name="transformer_full_taxonomy",
                restrict_to_ml_context=False,
            )
            try:
                backend._load()          # load now so failure surfaces here
            except Exception as exc:
                raise MlContextUnavailable(
                    f"ner_full_taxonomy=True but the configured model "
                    f"{self.config.ner_model!r} could not be loaded "
                    f"({type(exc).__name__}: {exc}). Refusing to continue: "
                    f"patterns/anchored/gazetteer are all skipped in this "
                    f"mode, so there is no fallback detector at all.") from exc
            self._names = backend
        else:
            self._names = resolve_backend(
                self.config.ner_model,
                required=self.config.require_ml_context,
                allow_gazetteer=not self.config.ner_only,
            )

    @property
    def ml_context_backend(self) -> str:
        return getattr(self._names, "name", "none")

    @property
    def ml_context_is_strong(self) -> bool:
        return bool(getattr(self._names, "high_confidence", False))

    def detect(self, text: str) -> list[Detection]:
        """Every detection in `text`. Raises `DetectorError` in strict mode."""
        if not text:
            return []
        labels = self.config.labels
        found: list[Detection] = []

        if self._full_taxonomy:
            # patterns/anchored/gazetteer deliberately skipped -- see the
            # module docstring and GuardConfig.ner_full_taxonomy.
            try:
                found.extend(self._names.detect(text, labels))
            except Exception as exc:
                if self.config.strict:
                    raise DetectorError(
                        f"the full-taxonomy model detector failed "
                        f"({type(exc).__name__}: {exc}). ner_full_taxonomy="
                        f"True has no fallback detector; refusing to emit "
                        f"partially-sanitised text."
                    ) from exc
            found.extend(_propagate_strong_mentions(text, found))
            return found

        tiers = [("patterns", lambda: patterns.detect(text, labels)),
                 ("anchored", lambda: anchored.detect(text, labels))]
        if not self.config.ner_only:
            tiers.append(("gazetteer_names", lambda: gazetteer_names.detect(text, labels)))
        for tier, fn in tiers:
            try:
                found.extend(fn())
            except Exception as exc:
                if self.config.strict:
                    raise DetectorError(
                        f"the {tier} detector failed ({type(exc).__name__}: "
                        f"{exc}). Refusing to emit partially-sanitised text."
                    ) from exc

        if self._names is not None:
            try:
                found.extend(self._names.detect(text, labels))
            except Exception as exc:
                if self.config.strict:
                    raise DetectorError(
                        f"the ml_context detector failed ({type(exc).__name__}: "
                        f"{exc}). Names and addresses may be unmasked; refusing "
                        f"to continue."
                    ) from exc

        found.extend(_propagate_strong_mentions(text, found))
        return found


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold()


def _propagate_strong_mentions(text: str, found: list[Detection]) -> list[Detection]:
    """One document-wide pass: a value detected once with real evidence is
    the same entity everywhere else it appears verbatim, even where the
    LOCAL context around that other occurrence gives no cue at all.

    Real bug this exists for, found by testing against a realistic
    multi-mention document (not a one-sentence smoke test): "Jonathan joins
    the Baku office" (no address cue -- gazetteer sees nothing) and "he
    resides at 47 Nizami Street, Apartment 12, Baku" (address cue present --
    gazetteer catches it) name the SAME city. Only masking the second
    mention defeats the point of masking the city at all: the fact is still
    stated in the clear two sentences earlier. A word-level detector that
    decides per-occurrence from local context alone cannot see this: it has
    no notion that two spans describe the same real-world thing. This is
    document-level coreference, propagated by exact string match rather than
    left to local cues alone.

    Deliberately conservative: only a detection that already cleared
    `_PROPAGATION_MIN_SCORE` seeds a propagation (so a weak, low-confidence
    guess never gets to declare every occurrence of a common word an
    entity), and only labels whose value IS the identifying fact -- person/
    place names -- propagate; a propagated span always inherits the
    ORIGINAL detection's label and a slightly reduced score, and is dropped
    entirely if it would overlap something already found.
    """
    propagatable = {"GIVENNAME", "SURNAME", "CITY", "STREET"}
    seeds: dict[str, Detection] = {}
    for d in found:
        if (d.label in propagatable and d.score >= _PROPAGATION_MIN_SCORE
                and len(d.text) >= _PROPAGATION_MIN_LEN):
            key = _norm(d.text)
            if key not in seeds or d.score > seeds[key].score:
                seeds[key] = d

    if not seeds:
        return []

    covered = [(d.start, d.end) for d in found]
    extra: list[Detection] = []
    for key, seed in seeds.items():
        pattern = re.compile(r"(?<!\w)" + re.escape(seed.text) + r"(?!\w)",
                             re.IGNORECASE | re.UNICODE)
        for m in pattern.finditer(text):
            s, e = m.start(), m.end()
            if any(s < ce and cs < e for cs, ce in covered):
                continue
            new_det = Detection(start=s, end=e, label=seed.label, text=m.group(0),
                                score=seed.score * 0.9, source="propagated")
            extra.append(new_det)
            covered.append((s, e))
    return extra
