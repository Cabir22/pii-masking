"""piigen -- LLM-driven synthetic data generation for Azerbaijani PII NER.

The LLM (via `piigen.llm`) never invents structured values -- it writes
carrier text with placeholders. Everything below mints and verifies the
actual entity values and validates the assembled result:

    config      ConfigurationManager  -- all tunable distributions in one place
    checksums   validity primitives   -- Luhn / IBAN mod-97 / VIN / IMEI / MAC / IP
    locales     per-language data     -- morphologically composed, not translated
    values      ValueFactory          -- entity values: high-entropy, deduped, valid
    negatives   NegativeFactory       -- hard negatives + adversarial lookalikes
    text        TextBuilder           -- offset-exact assembly (spans by construction)
    resolver    EntityResolver        -- labels EVERY occurrence, resolves overlaps
    noise       NoiseInjector         -- corruption with exact offset repair
    validate    Validator             -- full structured validation
    analyze     DatasetAnalyzer       -- quality metrics + generalization estimate
    llm         LLM generation        -- carrier-text backend + augmentation pipeline

The design invariant that everything else protects: a span is recorded at the
moment its text is appended to the buffer, so offsets cannot drift. Any
transformation applied afterwards (noise, wrapping, quoting) must remap spans
explicitly rather than re-finding them by string search.
"""

from __future__ import annotations

__all__ = [
    "config", "checksums", "locales", "values", "negatives", "text",
    "resolver", "noise", "validate", "analyze", "llm",
]
