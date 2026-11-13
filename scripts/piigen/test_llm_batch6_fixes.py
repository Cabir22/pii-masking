"""Fixes from the LLM batch-6 audit (P2-5, batch 6).

No network, no model, no API key.

    python scripts/piigen/test_llm_batch6_fixes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from clean_llm_batch import most_repeated  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def record(text: str, spans: list[tuple[str, str]]) -> dict:
    """Label each (label, value) at its next occurrence in text."""
    ents, pos = [], 0
    for label, value in spans:
        start = text.index(value, pos)
        ents.append({"start": start, "end": start + len(value), "label": label})
        pos = start + len(value)
    return {"text": text, "entities": ents}


def test_most_repeated() -> None:
    """--max-value-repeats counts one value: same label and same text
    (batch 6: `llm_az_000599` labels one IPv6 address 51 times)."""
    ip = "fe80::1c2:3d4"
    log = " ".join(f"[{i:02d}] {ip} bağlantı" for i in range(25))
    check(most_repeated(record(log, [("IPV6_ADDRESS", ip)] * 25)) == 25, "one IPv6 address 25 times")
    check(most_repeated({"text": "", "entities": []}) == 0, "no entities: 0")
    two = record("Saat 10:00 və 10:00, sonra 11:00.", [("TIME", "10:00"), ("TIME", "10:00"), ("TIME", "11:00")])
    check(most_repeated(two) == 2, "two different times: the more frequent counts", most_repeated(two))
    # the same text under two labels is two values
    mixed = record("1234 və 1234", [("CARD_SECURITY_CODE", "1234"), ("AGE", "1234")])
    check(most_repeated(mixed) == 1, "same text, different labels: counted apart", most_repeated(mixed))


def test_drop_value_repeats() -> None:
    """D-45b: the filter drops only documents at the threshold and writes
    every other line byte for byte, in order."""
    import json
    import tempfile
    from drop_before_v3 import main as drop_main
    ip = "fe80::1c2:3d4"
    many = record(" ".join([ip] * 20), [("IPV6_ADDRESS", ip)] * 20)
    few = record(" ".join([ip] * 19), [("IPV6_ADDRESS", ip)] * 19)
    lines = [json.dumps({"id": i, **r}, ensure_ascii=False).encode() + b"\n"
             for i, r in (("a", few), ("b", many), ("c", few))]
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.jsonl", Path(tmp) / "out.jsonl"
        src.write_bytes(b"".join(lines))
        drop_main([str(src), "--max-value-repeats", "20", "--out", str(out)])
        check(out.read_bytes() == lines[0] + lines[2], "20 repeats dropped, 19 kept byte for byte")


TESTS = [("most repeated value in a document", test_most_repeated),
         ("D-45b filter", test_drop_value_repeats)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
