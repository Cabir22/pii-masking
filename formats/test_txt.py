"""Tests for formats/txt.py. Uses a STUB detect_fn built from real
ground-truth entities (same "no model needed" policy as model/test_predict.py
and model/test_masking.py) rather than the actual trained checkpoint.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "model"))

from txt import extract, mask_text, unmask_text  # noqa: E402
from masking import LABEL_ALPHABET  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


KEY = b"\x03" * 16
tmp = Path(tempfile.mkdtemp())

# ---------------------------------------------------------------------------
print("1. extract() -- encoding handling")
# ---------------------------------------------------------------------------
utf8_path = tmp / "utf8.txt"
utf8_path.write_text("Salam, mənim adım Əli, Bakıda yaşayıram.", encoding="utf-8")
check(extract(utf8_path) == "Salam, mənim adım Əli, Bakıda yaşayıram.",
      "extract() reads a UTF-8 file correctly")

cyrillic_text = "Привет, меня зовут Алекс."
cp1251_path = tmp / "cp1251.txt"
cp1251_path.write_bytes(cyrillic_text.encode("cp1251"))
check(extract(cp1251_path) == cyrillic_text,
      "extract() auto-detects and correctly decodes a non-UTF-8 (cp1251) file",
      repr(extract(cp1251_path)))

# ---------------------------------------------------------------------------
print("1b. mask_text rejects malformed spans instead of silently corrupting")
# ---------------------------------------------------------------------------
_bad_text = "Zəng edin: +994501234567 haqqında."

for bad_spans, why in [
    ([{"start": 11, "end": 24, "label": "TELEPHONENUM"},
     {"start": 15, "end": 20, "label": "AGE"}],
     "overlapping spans"),
    ([{"start": 5, "end": 3, "label": "AGE"}], "start >= end"),
    ([{"start": 0, "end": 999, "label": "AGE"}], "end past the text length"),
    ([{"start": -1, "end": 5, "label": "AGE"}], "negative start"),
]:
    try:
        mask_text(_bad_text, lambda t, s=bad_spans: s, KEY)
        check(False, f"mask_text raises on {why}")
    except ValueError:
        check(True, f"mask_text raises on {why}")

# Non-overlapping, merely adjacent spans (one ends exactly where the next
# starts) must NOT be rejected -- that's normal, valid input, not an error.
_adjacent_ok = [{"start": 0, "end": 5, "label": "AGE"},
               {"start": 5, "end": 10, "label": "AGE"}]
try:
    mask_text("11111 22222 rest", lambda t, s=_adjacent_ok: s, KEY)
    check(True, "adjacent (non-overlapping) spans are accepted, not rejected")
except ValueError as e:
    check(False, "adjacent (non-overlapping) spans are accepted, not rejected",
          str(e))


# ---------------------------------------------------------------------------
print("2. mask_text / unmask_text round-trip on real ground-truth documents")
# ---------------------------------------------------------------------------
try:
    docs = []
    with (ROOT / "data/processed/merged/test.docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("entities"):
                docs.append(r)
            if len(docs) >= 150:
                break

    exact_round_trips = 0
    total_unsupported = 0
    all_supported_labels_present = False
    for doc in docs:
        text = doc["text"]
        entities = doc["entities"]

        def stub_detect(t, _ents=entities):
            return _ents

        masked, spans, unsupported = mask_text(text, stub_detect, KEY)
        total_unsupported += len(unsupported)
        if any(e["label"] in LABEL_ALPHABET for e in entities):
            all_supported_labels_present = True

        # Every masked span must actually differ from the original (a mask
        # that happens to equal the input would silently look "protected"
        # while doing nothing).
        for span in spans:
            s, e = span["start"], span["end"]
            core_had_content = any(
                ch in text[s:e] for ch in [c for c in text[s:e]])
            if text[s:e].strip():
                check(masked[s:e] != text[s:e] or masked[s:e] == "",
                      f"masked span actually changed the text: "
                      f"{span['label']} {text[s:e]!r}",
                      masked[s:e])

        # Unsupported-label spans must be left EXACTLY as they were --
        # not masked, not corrupted, clearly reported.
        for span in unsupported:
            s, e = span["start"], span["end"]
            check(masked[s:e] == text[s:e],
                  f"unsupported-label span ({span['label']}) is left "
                  f"untouched, not silently mangled",
                  f"{masked[s:e]!r} vs {text[s:e]!r}")

        recovered = unmask_text(masked, spans, KEY)
        if recovered == text:
            exact_round_trips += 1
        else:
            if len(FAILURES) < 10:
                FAILURES.append(f"round-trip mismatch on {doc.get('id')}")

    check(len(docs) > 0, "found real documents to test against", len(docs))
    check(all_supported_labels_present,
          "at least some tested documents contain a maskable label")
    check(exact_round_trips == len(docs),
          f"mask_text -> unmask_text recovers the ORIGINAL text exactly on "
          f"all {len(docs)} sampled real documents",
          f"{exact_round_trips}/{len(docs)}")
    print(f"  (unsupported spans encountered and correctly flagged, not "
          f"silently masked: {total_unsupported})")

except FileNotFoundError as exc:
    print(f"  SKIPPED (missing data file: {exc})")

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for f in FAILURES[:25]:
    print("  FAIL:", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
