"""Shared setup for the redteam/ probes.

The probes import `scripts/pii_guard/` (one package, DOCX + PPTX) and
`model/predict.py` straight from this working tree. An earlier version of
this file `git archive`d the package out of the `mask/docx` branch into a
scratch dir and imported it as `pg_docx`, because on that date the package
only existed on two divergent branches. Those branches were consolidated
into `main` on 2026-09-28 and deleted (tags `archive/mask-*` keep them), so
nothing here depends on which branch is checked out any more.

Note: `scripts/redteam/` (a different, colleague-written adversarial suite)
is unrelated to this directory; the two are deliberately kept apart.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MODEL_ID = "your-hf-org/masking-multilingual"


def allow_unsafe_for_probes() -> None:
    """Several probes construct `GuardConfig(require_ml_context=False)`
    deliberately -- to exercise the regex/anchor tier alone, without paying
    to load the transformer, for attacks that don't target ml_context at
    all (RT-2, RT-3, RT-4, RT-5, RT-6). That is a weakened config by
    `_enforce_safety`'s own rule, gated behind `PII_GUARD_ALLOW_UNSAFE=1`
    exactly like production code would be -- this is not a bypass of that
    gate, it is this test harness legitimately opting in to it, the same
    way `test_pii_guard.py` does for its own fail-closed-config tests.
    """
    os.environ.setdefault("PII_GUARD_ALLOW_UNSAFE", "1")


def setup_paths() -> None:
    """Make scripts/ (pii_guard, piigen) and model/ (predict) importable."""
    for p in [REPO / "scripts", REPO / "model"]:
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
