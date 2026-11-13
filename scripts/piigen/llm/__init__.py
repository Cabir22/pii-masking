"""LLM augmentation subsystem. DSPy is the sole generation backend.

    edge_cases     the edge-case catalog -- specific cases per label, and the
                   deliberately-wrong values for the negative-status ones
    specs          SpecSampler decides WHAT to generate: broad random
                   sampling (realistic distribution) plus, some share of the
                   time, a case deliberately drawn from edge_cases
    dspy_generate  DSPyGenerator decides HOW: one Signature (ported from the
                   former prompts.py), one dspy.LM, routed at the internal
                   endpoint via litellm
    quality        leaked-PII detection, judgment-word-leak detection,
                   near-duplicate rejection
    checkpoint     crash-safe resume
    pipeline       orchestrates all of the above
"""

from .dspy_generate import ConfigError, ContentError, DSPyGenerator, build_lm
from .pipeline import AugmentConfig, AugmentationPipeline

__all__ = [
    "DSPyGenerator", "build_lm", "ConfigError", "ContentError",
    "AugmentConfig", "AugmentationPipeline",
]
