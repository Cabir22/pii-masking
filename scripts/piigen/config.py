"""ConfigurationManager -- every tunable distribution in one auditable place.

Rationale: in the previous generator, distributions were implicit in the
template list (how many templates mentioned NAME determined how often NAME
appeared). That made the class balance an emergent property of prose rather
than a decision. Here every distribution is declared, overridable from a YAML
or JSON file, and reported by the analyzer, so a distribution change is a
config diff rather than an archaeology exercise.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Locked taxonomy v2.0.0 (data/schema.md), sourced from `Claude.pdf` ("PII
# Taxonomy -- Final Reference", 30 candidate labels, 27 included). Current
# phase is Azerbaijani-only -- en/ru/tr return once the az model is good.
# Adding/removing a label requires explicit confirmation, not a silent edit.
# ---------------------------------------------------------------------------

LANGUAGES = ["az"]
LANG_NAMES = {"az": "Azerbaijani"}

# Removed from the 30 candidates -- kept here for traceability, never
# reintroduce into a generator, validator, or entity_weights.
REMOVED_LABELS = {"PASSWORD", "AZ_BIRTH_CERTIFICATE_NUMBER", "AZ_PROPERTY_REGISTER_NUMBER"}

ENTITY_TYPES = [
    # GLOBAL (22)
    "API_KEY", "ACCESS_TOKEN", "PRIVATE_KEY", "PAYMENT_CARD_NUMBER", "IBAN",
    "CARD_SECURITY_CODE", "IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS", "URL",
    "ICCID", "GIVENNAME", "SURNAME", "EMAIL", "TELEPHONENUM", "DATE", "TIME",
    "AGE", "CITY", "STREET", "BUILDINGNUM", "ZIPCODE",
    # LOCAL -- Azerbaijan-specific (5)
    "AZ_FIN", "AZ_ID_CARD_NUMBER", "AZ_PASSPORT_NUMBER", "AZ_VOEN",
    "AZ_DRIVER_LICENSE_NUMBER",
]
ENTITY_SET = set(ENTITY_TYPES)

# Detection tier per label (data/schema.md). Never pattern-generate an
# anchor_required or ml_context label as if it had a fixed shape.
DETECTION_TIERS = {
    # pattern (16) -- deterministic generator + independent regex/checksum validator
    "API_KEY": "pattern", "ACCESS_TOKEN": "pattern", "PRIVATE_KEY": "pattern",
    "PAYMENT_CARD_NUMBER": "pattern", "IBAN": "pattern", "IPV4_ADDRESS": "pattern",
    "IPV6_ADDRESS": "pattern", "MAC_ADDRESS": "pattern", "URL": "pattern",
    "ICCID": "pattern", "EMAIL": "pattern", "AZ_FIN": "pattern",
    "AZ_ID_CARD_NUMBER": "pattern", "AZ_PASSPORT_NUMBER": "pattern",
    "AZ_VOEN": "pattern", "AZ_DRIVER_LICENSE_NUMBER": "pattern",
    # hybrid (2) -- some variants pattern, some anchor_required (schema.md notes)
    "TELEPHONENUM": "hybrid", "ZIPCODE": "hybrid",
    # anchor_required (5) -- no standalone signal, needs a nearby AZ context anchor
    "CARD_SECURITY_CODE": "anchor_required", "DATE": "anchor_required",
    "TIME": "anchor_required", "AGE": "anchor_required", "BUILDINGNUM": "anchor_required",
    # ml_context (4) -- no value-level pattern, curated-pool/NER only
    "GIVENNAME": "ml_context", "SURNAME": "ml_context", "CITY": "ml_context",
    "STREET": "ml_context",
}
assert set(DETECTION_TIERS) == ENTITY_SET, "DETECTION_TIERS must cover exactly ENTITY_TYPES"

# Labels whose values carry a verifiable internal structure (pattern + hybrid
# tiers). The validator enforces every one of these.
STRUCTURED_LABELS = {label for label, tier in DETECTION_TIERS.items()
                      if tier in ("pattern", "hybrid")}

# Labels whose interior must never be corrupted by the noise injector, because
# doing so would invalidate a checksum/format the validator relies on.
NOISE_PROTECTED_LABELS = set(STRUCTURED_LABELS)


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------

@dataclass
class LengthBucket:
    name: str
    weight: float
    min_chars: int
    max_chars: int


# Production PII documents are not snippets. This distribution is the single
# most important change from the previous generator, which topped out at 361
# characters and had a median of 103.
DEFAULT_LENGTH_BUCKETS = [
    LengthBucket("fragment",  0.14,    20,   80),
    LengthBucket("short",     0.24,    80,  300),
    LengthBucket("medium",    0.26,   300,  900),
    LengthBucket("long",      0.20,   900, 2500),
    LengthBucket("very_long", 0.12,  2500, 6000),
    LengthBucket("extreme",   0.04,  6000, 12000),
]


@dataclass
class GeneratorConfig:
    """All knobs. Override any subset via --config <file.json>."""

    # --- languages -------------------------------------------------------
    # Azerbaijani-only phase -- en/ru/tr return once the az model is good
    # (see docs/schema.md). Single-entry dict kept (not a bare constant) so
    # validate()'s sum-to-1.0 check and the sampler's weighted-choice code
    # don't need an az-only special case.
    lang_weights: dict = field(default_factory=lambda: {"az": 1.0})

    # --- document shape --------------------------------------------------
    length_buckets: list = field(default_factory=lambda: list(DEFAULT_LENGTH_BUCKETS))

    # Share of documents that mix languages. No-op while lang_weights has a
    # single entry -- revisit when en/ru/tr are reintroduced.
    mixed_language_rate: float = 0.0

    # --- entity policy ---------------------------------------------------
    # Target share of total entity MENTIONS per label.
    #
    # Deliberately NOT uniform. Production PII is genuinely Zipfian -- people
    # are named far more often than their VIN is quoted -- and flattening that
    # would introduce its own distribution shift. Forcing NAME down to 15% also
    # fights the architecture pointlessly: a document is *about* someone, so
    # every correspondence section refers to a person at least once.
    #
    # What actually mattered in the audit was tail COLLAPSE (IBAN had 53
    # mentions built from 6 distinct values), not NAME's share. So these
    # weights track realistic frequency while the floors below guarantee every
    # label gets enough absolute volume and value diversity to be learnable.
    # First-pass estimate, not a finalized decision -- revisit once real
    # generation runs surface actual label-difficulty/frequency tradeoffs.
    entity_weights: dict = field(default_factory=lambda: {
        "GIVENNAME":                0.150,
        "SURNAME":                  0.120,
        "EMAIL":                    0.120,
        "TELEPHONENUM":             0.100,
        "CITY":                     0.065,
        "STREET":                   0.050,
        "DATE":                     0.045,
        "ZIPCODE":                  0.035,
        "BUILDINGNUM":              0.035,
        "AGE":                      0.030,
        "TIME":                     0.025,
        "URL":                      0.025,
        "API_KEY":                  0.025,
        "AZ_FIN":                   0.020,
        "PAYMENT_CARD_NUMBER":      0.018,
        "IPV4_ADDRESS":             0.018,
        "ACCESS_TOKEN":             0.015,
        "AZ_ID_CARD_NUMBER":        0.015,
        "IBAN":                     0.014,
        "AZ_PASSPORT_NUMBER":       0.012,
        "CARD_SECURITY_CODE":       0.012,
        "AZ_VOEN":                  0.010,
        "AZ_DRIVER_LICENSE_NUMBER": 0.010,
        "PRIVATE_KEY":              0.010,
        "MAC_ADDRESS":              0.008,
        "IPV6_ADDRESS":             0.006,
        "ICCID":                    0.006,
    })

    # Absolute floor on mentions per label, as a share of the dataset size.
    # A label below this is reported as a quality failure by the analyzer
    # regardless of how well the relative distribution matches.
    min_mentions_per_label_ratio: float = 0.02

    # How hard to steer toward under-represented labels/languages. 0 = pure
    # sampling, 1 = always pick the most-starved. 0.65 keeps the distribution
    # honest while preventing tail collapse.
    balance_strength: float = 0.65

    # Documents carrying no PII at all. Zeroed by explicit instruction
    # (2026-08-21): training data should be true-positive only -- every
    # document contains and labels real PII, no "this document has nothing to
    # mask" examples. Precision-calibration tradeoff (see hard_negative_rate/
    # adversarial_rate below) accepted as a known, deliberate choice, not an
    # oversight -- re-enable by raising these three rates if that's revisited.
    negative_only_rate: float = 0.0

    # Share of documents carrying >=1 hard negative (a string that resembles
    # PII but must not be labeled). Zeroed alongside negative_only_rate --
    # same true-positive-only instruction.
    hard_negative_rate: float = 0.0

    # Share of documents carrying an adversarial near-miss (invalid checksum,
    # truncated key, partial email). Zeroed alongside the above. NOTE: this is
    # a real precision tradeoff, not a free simplification -- these were the
    # examples that taught the model "Luhn-valid 16 digits = card" instead of
    # "any 16 digits = card". Without them, false-positive rate on
    # lookalikes (order ids, tracking codes, invalid checksums) is untested.
    adversarial_rate: float = 0.0

    # Share of documents that deliberately target one specific case from the
    # edge-case catalog (piigen/llm/edge_cases.py) instead of the broad random
    # sampling below -- restricted to positive-family cases only now (see
    # specs.py._sample_edge_case), consistent with the true-positive-only
    # instruction above.
    edge_case_rate: float = 0.15

    # --- entity placement ------------------------------------------------
    # Fraction of sections that carry exactly one entity type, so the model
    # sees each label in isolation instead of always co-occurring with NAME.
    solo_entity_rate: float = 0.30

    # Fraction of documents where an entity starts at offset 0.
    leading_entity_rate: float = 0.15

    # Fraction of documents containing two entities separated by <=2 chars,
    # half of them same-type. This is what makes the BIO-vs-BIOES decision
    # evidence-based instead of a guess.
    adjacency_rate: float = 0.10
    same_type_adjacency_share: float = 0.5

    # Probability that an entity already used in a document is mentioned again
    # later (quoted reply, repeated log field, signature block). Every such
    # occurrence is labeled -- the old resolver labeled only the first.
    repeat_mention_rate: float = 0.35

    # Share of composition steps that append entity-free body text. This is
    # the main control on PII density: production documents run well under 5%
    # of characters inside a PII span, the previous dataset was at 29.6%, and
    # without filler this generator lands around 25%.
    filler_rate: float = 0.92

    # --- noise -----------------------------------------------------------
    noise_rate: float = 0.22          # share of documents receiving any noise
    noise_intensity: float = 0.012    # per-character edit probability when noised

    # --- value policy ----------------------------------------------------
    # Hard ceiling on how often any single value may be reused, as a share of
    # that label's total mentions. Enforced by ValueFactory.
    max_value_share: float = 0.004

    # Share of PASSWORD values allowed to contain a password-ish keyword. The
    # old data was at 59%, which trains a keyword detector, not a secret
    # detector.
    password_keyword_share: float = 0.12

    # --- document types (D-38) -------------------------------------------
    # The LLM briefs' document types, drawn evenly; None draws from every
    # type in llm.specs.DOC_TYPES. llm_augment_data.py --doc-types sets it.
    doc_types: list | None = None

    seed: int = 42

    # ------------------------------------------------------------------
    def merged(self, overrides: dict) -> "GeneratorConfig":
        base = copy.deepcopy(self)
        for key, value in (overrides or {}).items():
            if not hasattr(base, key):
                raise KeyError(f"unknown config key {key!r}")
            current = getattr(base, key)
            if isinstance(current, dict) and isinstance(value, dict):
                current.update(value)
            elif key == "length_buckets":
                setattr(base, key, [LengthBucket(**b) for b in value])
            else:
                setattr(base, key, value)
        base.validate()
        return base

    def validate(self) -> None:
        for name, dist in (("lang_weights", self.lang_weights),
                           ("entity_weights", self.entity_weights)):
            total = sum(dist.values())
            if abs(total - 1.0) > 0.02:
                raise ValueError(f"{name} must sum to ~1.0, got {total:.3f}")
        missing = ENTITY_SET - set(self.entity_weights)
        if missing:
            raise ValueError(f"entity_weights missing labels: {sorted(missing)}")
        unknown = set(self.entity_weights) - ENTITY_SET
        if unknown:
            raise ValueError(f"entity_weights has unknown labels: {sorted(unknown)}")
        if abs(sum(b.weight for b in self.length_buckets) - 1.0) > 0.02:
            raise ValueError("length_buckets weights must sum to ~1.0")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["length_buckets"] = [asdict(b) for b in self.length_buckets]
        return d

    @classmethod
    def load(cls, path: str | Path | None) -> "GeneratorConfig":
        cfg = cls()
        if path:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            cfg = cfg.merged(data)
        cfg.validate()
        return cfg
