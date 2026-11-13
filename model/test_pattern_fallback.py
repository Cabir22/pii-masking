"""Tests for pattern_fallback.py. No network, no model weights -- pure
regex/checksum logic, same "no downloaded model in tests" policy as
test_predict.py and scripts/test_prepare_splits.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "scripts"))

from pattern_fallback import (_date_plausible, _named_month_date_plausible,  # noqa: E402
                              find_email_echoed_name_spans, find_pattern_spans)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


# ---------------------------------------------------------------------------
print("1. Each pattern-tier label found at the right offset")
# ---------------------------------------------------------------------------
CASES = [
    ("Telefon: 0501234567", "TELEPHONENUM", "0501234567"),
    ("E-poçt: eli.mammadov@example.com filan", "EMAIL", "eli.mammadov@example.com"),
    ("Sizə 15.03.2024 tarixində göndərdiyim", "DATE", "15.03.2024"),
    ("VÖEN: 1503613621", "AZ_VOEN", "1503613621"),
    ("Hesab: AZ21NABZ00000000137010001944", "IBAN", "AZ21NABZ00000000137010001944"),
]
for text, expected_label, expected_value in CASES:
    spans = find_pattern_spans(text)
    match = [s for s in spans if s["label"] == expected_label]
    check(len(match) == 1,
          f"{expected_label} found exactly once in {text!r}", spans)
    if match:
        s = match[0]
        check(text[s["start"]:s["end"]] == expected_value,
              f"{expected_label} span offsets are exactly right",
              text[s["start"]:s["end"]])
        check(s["text"] == expected_value,
              f"{expected_label} span carries the matched text")


# ---------------------------------------------------------------------------
print("2. DATE structural plausibility rejects impossible day/month")
# ---------------------------------------------------------------------------
check(_date_plausible("15.03.2024"), "15.03.2024 is a plausible date")
check(not _date_plausible("45.13.2024"),
      "day 45 / month 13 is rejected -- not every dotted-number triple is a date")
check(not _date_plausible("12.45"),
      "a two-part dotted value (e.g. a version-looking fragment) is rejected")

no_date_candidate = find_pattern_spans("Versiya: 45.13.2024 buraxılışı")
check(not any(s["label"] == "DATE" for s in no_date_candidate),
      "an implausible dd.mm.yyyy-shaped number is not flagged as DATE",
      no_date_candidate)


# ---------------------------------------------------------------------------
print("2b. Named-month dates (AZ/RU/TR day-first, EN month-first)")
# ---------------------------------------------------------------------------
NAMED_MONTH_CASES = [
    ("Tarix: 14 noyabr 2018", "14 noyabr 2018"),          # AZ
    ("Я родилась 14 февраля 1995 года.", "14 февраля 1995"),  # RU (genitive)
    ("1 Ocak 1992 tarihinde doğdum.", "1 Ocak 1992"),      # TR
    ("I was born on March 3rd, 1988 in Leeds.", "March 3rd, 1988"),  # EN
    ("Toplantı 27 dekabr 2010-cu ildə keçiriləcək.", "27 dekabr 2010"),
]
for text, expected in NAMED_MONTH_CASES:
    spans = [s for s in find_pattern_spans(text) if s["label"] == "DATE"]
    check(len(spans) == 1 and spans[0]["text"] == expected,
          f"named-month date found exactly: {expected!r} in {text!r}", spans)

check(not any(s["label"] == "DATE" for s in
             find_pattern_spans("Versiya: 45 fake 2024 buraxılışı")),
      "a number-word-number triple with no real month name is not flagged "
      "as DATE (the word 'fake' isn't in the observed month list)")

check(_named_month_date_plausible("14 noyabr 2018"),
      "a real day-month-year triple is plausible")
check(not _named_month_date_plausible("45 noyabr 2018"),
      "day 45 is rejected even with a real month name")
check(not _named_month_date_plausible("14 fakemonth 2018"),
      "an unrecognized month word is rejected")


# ---------------------------------------------------------------------------
print("3. Overlap resolution -- longest verified match wins")
# ---------------------------------------------------------------------------
# A 10-digit AZ_VOEN fully contains plenty of 7-char substrings that could
# coincidentally look like other shapes; the whole verified match should be
# the only thing returned for that region, not a shorter distractor.
text = "VÖEN nömrəsi 1503613621 rəsmi sənəddə qeyd olunub."
spans = find_pattern_spans(text)
check(len(spans) == 1 and spans[0]["label"] == "AZ_VOEN"
      and text[spans[0]["start"]:spans[0]["end"]] == "1503613621",
      "the full AZ_VOEN match wins outright, no overlapping fragment leaks through",
      spans)


# ---------------------------------------------------------------------------
print("4. Multiple distinct entities in one document, no cross-contamination")
# ---------------------------------------------------------------------------
doc = ("Telefon: 0501234567\nE-poçt: eli.mammadov@example.com\n"
       "VÖEN: 1503613621\nTarix: 15.03.2024")
spans = find_pattern_spans(doc)
found_labels = sorted(s["label"] for s in spans)
check(found_labels == ["AZ_VOEN", "DATE", "EMAIL", "TELEPHONENUM"],
      "all four distinct pattern-tier entities found in one pass, "
      "each exactly once", found_labels)
check(all(doc[s["start"]:s["end"]] == s["text"] for s in spans),
      "every span's recorded text matches its own offsets in the source")


# ---------------------------------------------------------------------------
print("5. Plain prose with nothing pattern-tier produces no false positives")
# ---------------------------------------------------------------------------
prose = "Mənim adım Əli Məmmədovdur və Bakı şəhərində yaşayıram."
check(find_pattern_spans(prose) == [],
      "a name/city-only sentence -- no phone/email/date/id shapes -- yields "
      "zero pattern-tier candidates (this module never touches GIVENNAME/"
      "SURNAME/CITY/STREET, that stays entirely the model's job)",
      find_pattern_spans(prose))


# ---------------------------------------------------------------------------
print("6. find_email_echoed_name_spans: recovers a name the model missed "
      "by cross-referencing a verified EMAIL, without inventing false hits")
# ---------------------------------------------------------------------------
positive_text = ("Mən Nərmin Kərimova, işə qəbul üçün müraciət edirəm.\n"
                 "E-poçt: nermin.kerimova@mail.az\n\n"
                 "Hörmətlə,\nNərmin Kərimova")
positive_pattern_spans = find_pattern_spans(positive_text)
echoed = find_email_echoed_name_spans(positive_text, positive_pattern_spans)
echoed_texts = sorted(s["text"] for s in echoed)
check(echoed_texts == ["Kərimova", "Kərimova", "Nərmin", "Nərmin"],
      "every standalone occurrence of the name echoed in the email is "
      "recovered, both the mid-letter mention and the signature",
      echoed_texts)
check(all(positive_text[s["start"]:s["end"]] == s["text"] for s in echoed),
      "every recovered span's offsets are exactly right")
check(all(positive_text[s["start"] - 1:s["start"]] != "@"
         and "@" not in positive_text[max(0, s["start"]-15):s["start"]]
         for s in echoed),
      "no recovered span sits inside the email address itself")

check(find_email_echoed_name_spans("No email here at all.", []) == [],
      "no EMAIL span present -> nothing to cross-reference, no crash")

role_text = "Please contact support for help.\nE-poçt: support@company.az"
role_spans = find_pattern_spans(role_text)
check(find_email_echoed_name_spans(role_text, role_spans) == [],
      "a generic role address ('support@...') never causes the ordinary "
      "word 'support' elsewhere in the text to be flagged as a name")

unrelated_text = ("The meeting is about sales figures.\n"
                  "E-poçt: eli.mammadov@example.com")
unrelated_spans = find_pattern_spans(unrelated_text)
check(find_email_echoed_name_spans(unrelated_text, unrelated_spans) == [],
      "an email unrelated to any word elsewhere in the text recovers "
      "nothing -- this is cross-referencing, not a blind name-list scan")

already_found_text = "Nərmin Kərimova, e-poçt: nermin.kerimova@mail.az"
already_spans = find_pattern_spans(already_found_text) + [
    {"start": 0, "end": 6, "label": "GIVENNAME", "text": "Nərmin"},
    {"start": 7, "end": 15, "label": "SURNAME", "text": "Kərimova"},
]
check(find_email_echoed_name_spans(already_found_text, already_spans) == [],
      "a name the model ALREADY found is never re-added by this pass -- "
      "it only fills genuine gaps, never duplicates an existing detection")


# ---------------------------------------------------------------------------
print()
print("=" * 62)
print(f"PASSED {PASS}   FAILED {FAIL}")
for f in FAILURES[:25]:
    print("  FAIL:", f)
print("=" * 62)
sys.exit(1 if FAIL else 0)
