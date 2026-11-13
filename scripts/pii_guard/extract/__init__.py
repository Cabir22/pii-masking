"""Format dispatch. `extract(path)` routes to the right adapter by suffix.

PDF was removed from this service's scope 2026-09-14 -- a different
contributor owns PDF ingestion. `docx`/`pptx` and everything upstream of
extraction (detect/mask/vault/pipeline) are unaffected: `extract.base`'s
`ExtractedDocument`/`Segment` contract was already format-agnostic, so
dropping one adapter is a one-file removal, not a redesign. Re-adding PDF
later (or picking up whatever the other contributor builds) means adding
one adapter module and one line in `_ADAPTERS`; nothing else changes.
"""

from __future__ import annotations

from pathlib import Path

from . import docx, pptx
from .base import (ExtractedDocument, ExtractionDependencyMissing,  # noqa: F401
                   ExtractionError, Segment, suffix_format)

__all__ = ["extract", "ExtractedDocument", "Segment",
          "ExtractionError", "ExtractionDependencyMissing"]

_ADAPTERS = {"docx": docx.extract, "pptx": pptx.extract}


def extract(path: str | Path) -> ExtractedDocument:
    """Extract `path` using the adapter its extension selects."""
    fmt = suffix_format(path)
    return _ADAPTERS[fmt](path)
