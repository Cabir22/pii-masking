"""PII sanitisation service for text/documents crossing to a foreign LLM.

See `pipeline.py` for the three calls an integration needs
(`sanitize`, `sanitize_document`, `rehydrate`) and the deployment context
this was built for (chathal's overload-failover path to a foreign provider).
"""

from __future__ import annotations

from .pipeline import (
    DocxMaskResult, GuardConfig, MaskResult, SanitizationFailed, Vault,
    assert_no_raw_pii, build_external_request, rehydrate,
    rehydrate_document, sanitize, sanitize_document,
    sanitize_document_to_docx,
)

__all__ = [
    "sanitize", "sanitize_document", "rehydrate", "build_external_request",
    "assert_no_raw_pii", "SanitizationFailed",
    "sanitize_document_to_docx", "rehydrate_document", "DocxMaskResult",
    "GuardConfig", "MaskResult", "Vault",
]
