"""Configuration, and the fail-closed policy that governs it.

The brief's rule: *"If PII protection is a mandatory security requirement,
production should fail safely rather than silently sending unmasked PII."*
That shapes every default here.

Two ideas keep it honest:

* **Nothing security-relevant defaults to off.** `enabled` is True, the
  ml_context (name/address) detector is *required* by default, and the
  outbound assertion that re-scans the sanitised text is always on.
* **Turning protection off is loud and refused in production.** `enabled=False`
  or `require_ml_context=False` raise unless `PII_GUARD_ALLOW_UNSAFE=1` is set
  AND the environment is not production. There is no config file value that
  silently disables masking -- an operator has to set an env var whose name
  says what it does.

`strict` is the master switch and it is on by default. Turning it off is a
development convenience that the production check refuses.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .entities import FAMILY, LABELS

#: Env var an operator must set to run with protection weakened. Named so it
#: cannot be mistaken for a performance or verbosity flag.
UNSAFE_ENV = "PII_GUARD_ALLOW_UNSAFE"

#: Env vars that mark a production deployment. If any is set to a production
#: value, weakening the guard is refused outright.
_PROD_ENV_VARS = ("ENV", "ENVIRONMENT", "APP_ENV", "DEPLOY_ENV", "STAGE")
_PROD_VALUES = {"prod", "production", "live"}


class UnsafeConfiguration(RuntimeError):
    """Raised when a configuration would let raw PII reach an external model."""


def is_production() -> bool:
    return any(os.environ.get(v, "").strip().lower() in _PROD_VALUES
               for v in _PROD_ENV_VARS)


def _unsafe_allowed() -> bool:
    return os.environ.get(UNSAFE_ENV, "").strip() == "1" and not is_production()


@dataclass
class GuardConfig:
    """How the sanitisation service behaves. Safe by default."""

    # --- master switches -------------------------------------------------
    #: Whole guard. False is refused unless explicitly allowed (see above).
    enabled: bool = True
    #: Fail closed. When True (default) any detector error, missing
    #: dependency, or failed outbound assertion aborts instead of degrading.
    strict: bool = True

    # --- detection -------------------------------------------------------
    #: Taxonomy labels to detect. Defaults to all 27.
    labels: frozenset[str] = field(default_factory=lambda: frozenset(LABELS))
    #: Require the ml_context detector (GIVENNAME/SURNAME/CITY/STREET) to be
    #: available. Those four cannot be found by regex, so running without it
    #: means names and addresses go to the model in the clear.
    require_ml_context: bool = True
    #: Detections below this score are dropped. 0.0 keeps everything; pattern
    #: detections are always 1.0 so this only ever gates model output.
    min_score: float = 0.35
    #: Optional path/name of a token-classification model for the ml_context
    #: tier. None -> gazetteer only. Set (with ner_only=False, the default)
    #: -> gazetteer AND the model, combined (see detect.names.CombinedBackend)
    #: -- measured against 10 realistic multilingual documents, the
    #: checkpoint alone missed almost every PERSON mention the gazetteer
    #: caught (1 of 33), so the model is additive to the gazetteer by
    #: default, not a replacement for it.
    ner_model: str | None = None
    #: Use the model ALONE for ml_context -- no gazetteer, not even as a
    #: supplement. Requires `ner_model`. This is a deliberate, measured
    #: trade: with the checkpoint this repo currently trains
    #: (`your-hf-org/masking-multilingual`), real PERSON recall on realistic
    #: PPTX prose was 0-1 caught per document versus 6-11 with the gazetteer
    #: combined in -- turning this on means most real names will reach the
    #: foreign LLM unmasked until a stronger checkpoint replaces the current
    #: one. Listed in `_enforce_safety`'s weakened set for exactly that
    #: reason: this is a real reduction in protection, not a style choice,
    #: and the whole point of that mechanism is that reductions like this
    #: are loud and explicit rather than a quiet default.
    ner_only: bool = False
    #: Strictly stronger (and riskier) than `ner_only`: skips
    #: `detect.patterns`/`detect.anchored` AND the gazetteer entirely, not
    #: just the gazetteer. The model becomes the ONLY detector, for the
    #: FULL 27-label taxonomy -- not just GIVENNAME/SURNAME/CITY/STREET --
    #: including EMAIL/IBAN/PHONE/card numbers/credentials, which otherwise
    #: get deterministic, checksum-verified pattern detection regardless of
    #: which ml_context backend is in play. Requires `ner_model`. Explicit
    #: user direction (2026-09-15): the target is to ship the model alone
    #: once it is fixed; until then this stays off. `detect/patterns.py`
    #: and `detect/anchored.py` are NOT deleted when this is on -- kept in
    #: the codebase, unused in this mode, for when they're needed again.
    #: Untested on realistic fragmented documents (see
    #: `detect.names.TransformerBackend`'s docstring for the golden-set
    #: benchmark this was measured against, which is continuous prose, not
    #: PPTX-shaped text) -- listed in `_enforce_safety`'s weakened set for
    #: the same reason `ner_only` is: refused without
    #: `PII_GUARD_ALLOW_UNSAFE=1` outside production, refused outright in
    #: production.
    ner_full_taxonomy: bool = False

    # --- masking ---------------------------------------------------------
    #: Placeholder shape. `{family}` and `{n}` are substituted.
    placeholder_format: str = "[{family}_{n:03d}]"
    #: Treat two identical strings with the same label as the same entity
    #: within one document. See mask.py for why this is not always true.
    coreference_by_value: bool = True

    # --- response handling ----------------------------------------------
    #: Substitute real values back into the model's response, locally.
    rehydrate: bool = True

    # --- logging ---------------------------------------------------------
    #: Never log detected values. Turning this off is refused like `enabled`.
    redact_logs: bool = True

    def __post_init__(self) -> None:
        unknown = set(self.labels) - set(LABELS)
        if unknown:
            raise ValueError(f"unknown labels: {sorted(unknown)}")
        if self.ner_only and not self.ner_model:
            raise ValueError(
                "ner_only=True requires ner_model to be set -- there is no "
                "model to use alone.")
        if self.ner_full_taxonomy and not self.ner_model:
            raise ValueError(
                "ner_full_taxonomy=True requires ner_model to be set -- "
                "there is no model to use alone.")
        self._enforce_safety()
        self._check_placeholder_format()

    # -- safety ----------------------------------------------------------
    def _enforce_safety(self) -> None:
        weakened = []
        if not self.enabled:
            weakened.append("enabled=False (no masking at all)")
        if not self.strict:
            weakened.append("strict=False (failures degrade instead of aborting)")
        if not self.require_ml_context:
            weakened.append("require_ml_context=False (names/addresses unmasked "
                            "if no model is available)")
        if self.ner_only:
            weakened.append("ner_only=True (ml_context relies on the model alone, "
                            "no gazetteer -- measured recall on real PPTX prose "
                            "was 0-1 real names caught per document with the "
                            "current checkpoint; most real names will reach the "
                            "foreign LLM unmasked)")
        if self.ner_full_taxonomy:
            weakened.append("ner_full_taxonomy=True (patterns/anchored/gazetteer "
                            "all skipped -- the model alone handles every label, "
                            "including EMAIL/IBAN/PHONE/credentials that would "
                            "otherwise get deterministic checksum-verified "
                            "detection regardless of ml_context recall; untested "
                            "on realistic fragmented documents)")
        if not self.redact_logs:
            weakened.append("redact_logs=False (raw PII may reach logs)")
        if not weakened:
            return
        if _unsafe_allowed():
            return
        why = "; ".join(weakened)
        if is_production():
            raise UnsafeConfiguration(
                f"refusing to weaken PII protection in production: {why}. "
                f"{UNSAFE_ENV} is ignored when the environment is production.")
        raise UnsafeConfiguration(
            f"this configuration would let raw PII reach an external model: "
            f"{why}. If that is genuinely intended (tests, local debugging), "
            f"set {UNSAFE_ENV}=1.")

    def _check_placeholder_format(self) -> None:
        """A placeholder must not be able to carry the value it replaces."""
        import string
        fields = {name for _, name, _, _ in string.Formatter().parse(self.placeholder_format)
                  if name}
        # `.format(family=..., n=...)` alone does not catch a format string
        # missing `{n}` -- str.format silently ignores unused kwargs, so
        # `"{family}".format(family="PERSON", n=1)` succeeds and produces
        # "PERSON" with no braces left over, passing the checks below even
        # though every entity of one family would collide on one
        # placeholder. Caught by the test suite, not by inspection.
        missing = {"family", "n"} - fields
        if missing:
            raise ValueError(
                f"placeholder_format must reference both {{family}} and "
                f"{{n}} -- missing {sorted(missing)}. Omitting {{n}} means "
                f"every entity in a family collides on one placeholder.")
        try:
            sample = self.placeholder_format.format(family="PERSON", n=1)
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(
                f"placeholder_format must use only {{family}} and {{n}}: {exc}"
            ) from None
        if "{" in sample or "}" in sample:
            raise ValueError("placeholder_format left unsubstituted fields")
        if not sample.strip():
            raise ValueError("placeholder_format produced an empty placeholder")

    # -- helpers ----------------------------------------------------------
    @property
    def families(self) -> frozenset[str]:
        return frozenset(FAMILY[l] for l in self.labels)

    @classmethod
    def from_env(cls) -> "GuardConfig":
        """Build from `PII_GUARD_*` env vars. Only ever *tightens* silently;
        loosening still goes through `_enforce_safety`."""
        def flag(name: str, default: bool) -> bool:
            raw = os.environ.get(f"PII_GUARD_{name}")
            return default if raw is None else raw.strip().lower() in ("1", "true", "yes")

        return cls(
            enabled=flag("ENABLED", True),
            strict=flag("STRICT", True),
            require_ml_context=flag("REQUIRE_ML_CONTEXT", True),
            rehydrate=flag("REHYDRATE", True),
            redact_logs=flag("REDACT_LOGS", True),
            ner_model=os.environ.get("PII_GUARD_NER_MODEL") or None,
            ner_only=flag("NER_ONLY", False),
            ner_full_taxonomy=flag("NER_FULL_TAXONOMY", False),
            min_score=float(os.environ.get("PII_GUARD_MIN_SCORE", "0.35")),
        )
