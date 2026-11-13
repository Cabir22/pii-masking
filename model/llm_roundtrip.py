"""Phase 5: the actual reason this project exists.

Everything through Phase 4 unmasks the SAME document it masked -- offsets
never move, because mask_value always returns a same-length replacement, so
`unmask_text`/`unmask_csv`/`unmask_workbook` just re-read the recorded
(start, end) positions. That does not work here: an external LLM's response
is a NEW piece of text. It may reorder information, summarize, paraphrase,
or drop values entirely -- there is no "offset" to trust. The masked value
has to be found by SEARCHING the response for it, not by position.

This is the one scenario that is the actual reason masking needs to be
reversible at all: the in-house AI has a server problem, the fallback is an
external provider (e.g. OpenAI), and the response that comes back needs the
real values restored before the client ever sees it.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "formats"))
from masking import LABEL_ALPHABET, _extract_core  # noqa: E402

LlmCallFn = Callable[[str], str]
DetectFn = Callable[[str], list]

# A masked value is only safely auto-replaced in a response if its DOMAIN is
# large enough that a coincidental, unrelated match in the response is
# implausible -- the exact same reasoning masking.py already uses to decide
# when FF3 itself is even appropriate (a value from a tiny domain, like a
# 2-digit AGE, has few enough possible values that an ordinary LLM response
# mentioning some OTHER unrelated 2-digit number is a real risk, not a
# hypothetical one). Reusing that reasoning here rather than inventing an
# unrelated threshold.
MIN_SAFE_DOMAIN_SIZE = 10_000


def build_mask_map(original_text: str, masked_text: str, spans: list[dict]
                   ) -> dict[str, tuple[str, str]]:
    """{masked_value: (real_value, label)} for every span that was masked.

    Both strings are read from their respective texts at the SAME (start,
    end) -- valid because mask_value never changes length, confirmed
    throughout test_masking.py including the chunking path.
    """
    mask_map = {}
    for span in spans:
        s, e, label = span["start"], span["end"], span["label"]
        mask_map[masked_text[s:e]] = (original_text[s:e], label)
    return mask_map


def _domain_size(masked_value: str, label: str) -> int:
    alphabet = LABEL_ALPHABET.get(label)
    if alphabet is None:
        return 0
    core, _ = _extract_core(masked_value, alphabet)
    if not core:
        return 0
    return len(alphabet) ** len(core)


def unmask_response(response_text: str, mask_map: dict[str, tuple[str, str]],
                    min_safe_domain_size: int = MIN_SAFE_DOMAIN_SIZE
                    ) -> dict:
    """Searches `response_text` for every masked value and restores the
    real value where found. Returns a report, not just a string -- silently
    returning "the unmasked text" with no way to tell what was and wasn't
    actually recovered would hide exactly the failure mode this function
    exists to catch.

    Longest values first (same "longest match wins" convention resolver.py
    already uses): protects against a short masked value coincidentally
    being a substring of a different, longer one. Word-boundary anchored
    (`\\b`, Unicode-aware by default for `str` patterns) so a match only
    counts when the masked value is a complete token in the response, not
    embedded inside an unrelated longer word or number.

    Values from a domain too small to safely auto-replace (see
    MIN_SAFE_DOMAIN_SIZE) are deliberately EXCLUDED from replacement and
    reported separately, not replaced anyway on a best-effort basis --
    guessing wrong here means silently inserting the WRONG real value into
    text the client will read.
    """
    ordered = sorted(mask_map.items(), key=lambda kv: -len(kv[0]))
    out = response_text
    recovered: list[str] = []
    not_found: list[str] = []
    low_confidence_skipped: list[str] = []

    for masked_val, (real_val, label) in ordered:
        if _domain_size(masked_val, label) < min_safe_domain_size:
            low_confidence_skipped.append(masked_val)
            continue
        pattern = re.compile(r"(?<!\w)" + re.escape(masked_val) + r"(?!\w)")
        if pattern.search(out):
            out = pattern.sub(lambda _m, rv=real_val: rv, out)
            recovered.append(masked_val)
        else:
            not_found.append(masked_val)

    return {
        "unmasked_text": out,
        "recovered": recovered,
        "not_found": not_found,
        "low_confidence_skipped": low_confidence_skipped,
    }


def round_trip_through_llm(text: str, detect_fn: DetectFn,
                           llm_call_fn: LlmCallFn, key: bytes) -> dict:
    """The full Phase-5 scenario: mask -> send through an external LLM ->
    unmask whatever comes back.

    `llm_call_fn` is pluggable so this is fully testable without a real
    API call (and without an API key, which this environment does not
    have). Wiring it to a REAL provider (e.g. OpenAI) is a thin adapter
    over this same function -- and a decision that needs an actual API key
    plus a deliberate choice to spend real quota/money, not something to
    assume.
    """
    from txt import mask_text  # noqa: E402 (formats/ added to sys.path above)
    masked_text, spans, unsupported = mask_text(text, detect_fn, key)
    mask_map = build_mask_map(text, masked_text, spans)

    response = llm_call_fn(masked_text)
    result = unmask_response(response, mask_map)
    result.update({
        "masked_text": masked_text,
        "llm_response": response,
        "unsupported_before_send": unsupported,
    })
    return result
