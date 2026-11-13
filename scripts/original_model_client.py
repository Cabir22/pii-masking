# -*- coding: utf-8 -*-
"""Adapter for the ORIGINAL (non-rebalanced) production model's API.

Wraps the user's own mask_pii(text) -> {"masked_text": ..., "entities": [...]}
request code (pasted below unchanged) so benchmark_rebalance.py can call it
exactly like it calls the local rebalanced model.

ONE THING YOU STILL NEED TO DO: replace BASE_URL below with the real
endpoint URL (it was "something" as a placeholder in the code you gave me).
"""
from __future__ import annotations

import os
import time

import requests

# ============================================================================
# STEP 1 of 2 -- your API key (already wired, nothing to change here)
# ============================================================================
# Before running anything, set it in your terminal (not in this file):
#
#   PowerShell:   $env:PII_API_KEY = "your-key-here"
#   bash:         export PII_API_KEY=your-key-here
API_KEY = os.environ["PII_API_KEY"]

# ============================================================================
# STEP 2 of 2 -- fill in the real endpoint
# ============================================================================
BASE_URL = "http://10.10.70.70:18101"


def mask_pii(text: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/mask",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        json={"text": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


# ============================================================================
# Everything below this line is already done -- no need to touch it.
# ============================================================================

def _entity_span(e: dict, text: str) -> dict:
    """Normalizes one entity from your API's response into
    {"label", "start", "end", "text"}. Tries the common field-name variants
    so it should work out of the box; if your response uses different key
    names than these, tell me the actual keys (in words, not real data) and
    I'll adjust this one function."""
    label = e.get("label") or e.get("type") or e.get("entity") or e.get("entity_group")
    start = e.get("start")
    if start is None:
        start = e.get("start_offset")
    end = e.get("end")
    if end is None:
        end = e.get("end_offset")
    span_text = e.get("text")
    if span_text is None and start is not None and end is not None:
        span_text = text[start:end]
    return {"label": label, "start": start, "end": end, "text": span_text}


def predict(text: str) -> list[dict]:
    result = mask_pii(text)
    return [_entity_span(e, text) for e in result["entities"]]


# ============================================================================
# How to check your own work, with a FAKE test sentence (no real data)
# ============================================================================
# Run this from the project folder:
#
#   python scripts/original_model_client.py
#
if __name__ == "__main__":
    _test_sentence = "Contact John Smith at john.smith@example.com or 555-0100."
    print(predict(_test_sentence))


# ============================================================================
# Retry wrapper -- do not touch, benchmark_rebalance.py uses this name
# ============================================================================
_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 2.0
_raw_predict = predict


def predict(text: str) -> list[dict]:  # noqa: F811 -- intentional wrapper
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return _raw_predict(text)
        except Exception as exc:  # noqa: BLE001 -- deliberately broad, retried
            last_exc = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_BACKOFF_SECONDS * (attempt + 1))
    assert last_exc is not None
    raise last_exc
