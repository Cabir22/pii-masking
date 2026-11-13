"""Tests for llm_roundtrip.py.

No real API call -- llm_call_fn is always a stub here, simulating the
realistic range of things an external LLM's response can actually do to a
masked value it was handed: echo it verbatim, paraphrase around it,
reorder it relative to other values, drop it entirely, or (the one real
documented limitation) reformat it slightly, which this search-based
approach genuinely cannot recover from and must not pretend to.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "formats"))

from llm_roundtrip import (MIN_SAFE_DOMAIN_SIZE, _domain_size,  # noqa: E402
                           build_mask_map, round_trip_through_llm,
                           unmask_response)
from masking import mask_value                          # noqa: E402
from txt import mask_text                                # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


KEY = b"\x06" * 16

# ---------------------------------------------------------------------------
print("1. build_mask_map")
# ---------------------------------------------------------------------------
text = "Zəng edin: 0501234567."
spans = [{"start": 11, "end": 21, "label": "TELEPHONENUM"}]
masked_text, real_spans, _ = mask_text(text, lambda t: spans, KEY)
mask_map = build_mask_map(text, masked_text, real_spans)
check(len(mask_map) == 1, "one masked span produces one mask_map entry")
(masked_val, (real_val, label)), = mask_map.items()
check(real_val == "0501234567" and label == "TELEPHONENUM",
      "mask_map maps the masked value back to the correct real value/label")


# ---------------------------------------------------------------------------
print("2. _domain_size -- the small-domain safety threshold")
# ---------------------------------------------------------------------------
age_masked = mask_value("AGE", "58", KEY)
phone_masked = mask_value("TELEPHONENUM", "0501234567", KEY)
check(_domain_size(age_masked, "AGE") < MIN_SAFE_DOMAIN_SIZE,
      "a 2-digit AGE value's domain is correctly judged too small to trust",
      _domain_size(age_masked, "AGE"))
check(_domain_size(phone_masked, "TELEPHONENUM") >= MIN_SAFE_DOMAIN_SIZE,
      "a 10-digit phone number's domain is correctly judged large enough",
      _domain_size(phone_masked, "TELEPHONENUM"))


# ---------------------------------------------------------------------------
print("3. unmask_response -- realistic LLM response behaviours")
# ---------------------------------------------------------------------------
phone_real = "0501234567"
phone_m = mask_value("TELEPHONENUM", phone_real, KEY)
name_real = "Aysel"
name_m = mask_value("GIVENNAME", name_real, KEY)
city_real = "Bakı"
city_m = mask_value("CITY", city_real, KEY)
age_real = "58"
age_m = mask_value("AGE", age_real, KEY)

mmap = {
    phone_m: (phone_real, "TELEPHONENUM"),
    name_m: (name_real, "GIVENNAME"),
    city_m: (city_real, "CITY"),
    age_m: (age_real, "AGE"),
}

# a) verbatim echo
r = unmask_response(f"Müştərinin nömrəsi {phone_m}-dir.", mmap)
check(phone_m in r["recovered"] and phone_real in r["unmasked_text"],
      "a) verbatim echo of a masked value is found and restored", r)

# b) paraphrase AROUND the value, value itself intact -- position-independent
r = unmask_response(
    f"Xülasə: müştəri {name_m} adlı şəxsdir və əlaqə nömrəsi {phone_m}-dir, "
    f"tamamilə fərqli cümlə quruluşu ilə.", mmap)
check(name_real in r["unmasked_text"] and phone_real in r["unmasked_text"],
      "b) values survive being embedded in totally reworded surrounding "
      "prose", r["unmasked_text"])

# c) value dropped entirely -- must be reported, not silently ignored
r = unmask_response("Ümumi xülasə, heç bir konkret məlumat yoxdur.", mmap)
check(set(r["recovered"]) == set(),
      "c) no values found when none appear in the response")
check(phone_m in r["not_found"] and name_m in r["not_found"],
      "c) every value that never came back is explicitly reported as "
      "not_found, not silently swallowed", r["not_found"])

# d) reordering: values present in a DIFFERENT order than the original
r = unmask_response(f"{city_m} şəhərindən olan {name_m}, tel: {phone_m}.", mmap)
check(all(v in r["unmasked_text"] for v in (city_real, name_real, phone_real)),
      "d) all values recovered correctly regardless of their order in the "
      "response", r["unmasked_text"])

# e) THE REAL LIMITATION: the LLM reformats a masked value (adds spacing)
#    before echoing it back. Search-based recovery cannot find this -- and
#    must say so, not claim success.
reformatted = phone_m[:3] + " " + phone_m[3:6] + " " + phone_m[6:]
r = unmask_response(f"Nömrə: {reformatted}", mmap)
check(phone_m in r["not_found"],
      "e) a reformatted (respaced) masked value is correctly reported as "
      "NOT recoverable -- a real, documented limitation, not silently "
      "papered over", r)

# f) low-confidence short value: present in the response, but must be
#    EXCLUDED from auto-replace rather than guessed at.
r = unmask_response(f"Yaş: {age_m}", mmap)
check(age_m in r["low_confidence_skipped"],
      "f) a small-domain (AGE) value is excluded from auto-replace even "
      "though it IS present in the response", r)
check(age_real not in r["unmasked_text"],
      "f) ...and is therefore correctly NOT substituted in", r["unmasked_text"])

# h) word-boundary safety: a masked value embedded INSIDE a longer unrelated
#    token in the response must not trigger a false replacement.
fake_collision_text = f"kod{phone_m}xyz"  # phone_m glued into a longer token
r = unmask_response(fake_collision_text, mmap)
check(phone_m in r["not_found"],
      "h) a masked value embedded inside a longer unrelated token is NOT "
      "falsely matched (word-boundary anchored)", r)


# ---------------------------------------------------------------------------
print("4. unmask_response -- substring collision between two masked values")
# ---------------------------------------------------------------------------
# Construct a deliberate case: one masked value is literally a substring of
# another. Longest-first processing must resolve this correctly rather than
# let the short one's replacement corrupt the long one's match.
short_val = "AB1234"
long_val = "XAB1234Y"
fake_map = {short_val: ("short-real", "AZ_FIN"), long_val: ("long-real", "AZ_FIN")}
# bypass the domain-size gate for this synthetic case by using a large
# min_safe_domain_size=0 -- this test is about ORDERING, not the gate.
r = unmask_response(f"see {long_val} here", fake_map, min_safe_domain_size=0)
check("long-real" in r["unmasked_text"] and "short-real" not in r["unmasked_text"],
      "the longer value's match wins; the shorter value's word-boundary "
      "check correctly refuses to match text embedded inside a longer "
      "token", r)


# ---------------------------------------------------------------------------
print("5. round_trip_through_llm -- full pipeline, real documents, stub LLM")
# ---------------------------------------------------------------------------
try:
    docs = []
    with (ROOT / "data/processed/merged/test.docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("lang") == "az" and len(r.get("entities", [])) >= 2:
                docs.append(r)
            if len(docs) >= 40:
                break

    fully_recovered = 0
    any_low_confidence = 0
    total = 0
    for doc in docs:
        text = doc["text"]
        entities = doc["entities"]

        def stub_detect(t, _ents=entities):
            return _ents

        def stub_llm(masked_text):
            # Simulate a realistic external LLM: produces its own summary
            # sentence that quotes every masked value verbatim (the best
            # case), in REVERSE order from how they appear in the input --
            # proving position independence, not just an identity
            # passthrough of the input.
            ordered_spans = sorted(entities, key=lambda e: e["start"])
            values = [masked_text[s["start"]:s["end"]] for s in ordered_spans]
            return "Xülasə (tərs qaydada): " + " | ".join(reversed(values))

        total += 1
        result = round_trip_through_llm(text, stub_detect, stub_llm, KEY)
        # Every value with a large-enough domain should come back; small
        # AGE-shaped values are expected to land in low_confidence_skipped
        # rather than recovered -- both count as "handled correctly".
        if result["not_found"]:
            if len(FAILURES) < 5:
                FAILURES.append(f"doc {doc.get('id')}: unexpectedly not_found "
                                f"{result['not_found']}")
        else:
            fully_recovered += 1
        if result["low_confidence_skipped"]:
            any_low_confidence += 1

    check(total > 0, "found real documents to test the full pipeline against",
          total)
    check(fully_recovered == total,
          f"every large-enough-domain value was recovered from the "
          f"(reordered) stub LLM response across all {total} documents",
          f"{fully_recovered}/{total}")
    print(f"  (documents with a small-domain value correctly routed to "
          f"low_confidence_skipped instead of guessed: {any_low_confidence})")

except FileNotFoundError as exc:
    print(f"  SKIPPED (missing data file: {exc})")

# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for f in FAILURES[:25]:
    print("  FAIL:", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
