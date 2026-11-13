"""Tests for masking.py. No network, no model weights -- pure crypto/logic."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from masking import (ALNUM_ALPHABET, DIGIT_ALPHABET, LABEL_ALPHABET,  # noqa: E402
                     LETTER_ALPHABET, MULTI_ALPHABET_LABELS, _extract_core,
                     _reinsert, mask_value, unmask_value)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


KEY1 = b"\x01" * 16
KEY2 = b"\x02" * 16

# ---------------------------------------------------------------------------
print("1. _extract_core / _reinsert (template preservation)")
# ---------------------------------------------------------------------------
core, tmpl = _extract_core("+994 50 123-45-67", DIGIT_ALPHABET)
check(core == "994501234567", "digits extracted, punctuation excluded", core)
check(_reinsert(core, tmpl) == "+994 50 123-45-67",
      "reinserting the SAME core reproduces the original exactly")
check(_reinsert("000000000000", tmpl) == "+000 00 000-00-00",
      "reinserting a DIFFERENT core keeps punctuation positions fixed",
      _reinsert("000000000000", tmpl))

core2, tmpl2 = _extract_core("Nizami küçəsi 84A", LETTER_ALPHABET)
check("84A" not in core2 and " " not in core2,
      "digits and spaces are not part of the letter core", core2)


# ---------------------------------------------------------------------------
print("2. mask_value / unmask_value round-trip -- realistic values per label")
# ---------------------------------------------------------------------------
REALISTIC = [
    ("TELEPHONENUM", "+994 50 123-45-67"),
    ("TELEPHONENUM", "0501234567"),
    ("AZ_VOEN", "1503613621"),
    ("AGE", "34"),                       # below FF3's digit floor (6)
    ("AGE", "7"),                        # 1-digit, tiny domain
    ("BUILDINGNUM", "84A".replace("A", "")),  # keep pure-digit for this alphabet
    ("CARD_SECURITY_CODE", "047"),       # below floor
    ("PAYMENT_CARD_NUMBER", "4111 1111 1111 1111"),
    ("ICCID", "8994411234567890123"),
    ("ZIPCODE", "AZ1132"),
    ("DATE", "21.02.1956"),
    ("TIME", "14:30"),
    ("AZ_FIN", "30LJV5Z"),
    ("AZ_ID_CARD_NUMBER", "AA1014572"),
    ("AZ_PASSPORT_NUMBER", "X05000971"),
    ("AZ_DRIVER_LICENSE_NUMBER", "BA154675"),
    ("IBAN", "AZ21NABZ00000000137010001944"),
    ("MAC_ADDRESS", "00:1A:2B:3C:4D:5E"),
    ("GIVENNAME", "Əli"),                # 3 letters, below even the letter floor
    ("GIVENNAME", "Aysel"),
    ("SURNAME", "Məmmədov"),
    ("CITY", "Bakı"),                    # 4 letters, exactly at the letter floor
    ("CITY", "Gəncə"),
    ("STREET", "Nizami küçəsi"),
    ("SURNAME", "Мюршюдалиева"),          # Cyrillic -- the real bug this
    ("GIVENNAME", "Зийад"),               # found: a Latin-only alphabet
    ("CITY", "Нахичевань"),               # silently no-ops on these
    ("STREET", "улица Натиг Садиев"),
    ("EMAIL", "eli.mammadov@example.com"),
    ("EMAIL", "John.Doe123@my-domain.co.uk"),  # mixed case must round-trip
                                                # as mixed case, not be
                                                # silently upper-cased
    ("EMAIL", "a@b.co"),                       # short local-part/domain
]
for label, value in REALISTIC:
    masked = mask_value(label, value, KEY1)
    recovered = unmask_value(label, masked, KEY1)
    check(recovered == value,
          f"{label} round-trips exactly: {value!r}",
          f"masked={masked!r} recovered={recovered!r}")
    check(len(masked) == len(value),
          f"{label} masked value keeps the original length: {value!r}",
          f"masked={masked!r} ({len(masked)} vs {len(value)})")
    if value.strip():
        check(masked != value or len(_extract_core(value, LABEL_ALPHABET[label])[0]) == 0,
              f"{label} masked value actually differs from the original: {value!r}",
              masked)


# ---------------------------------------------------------------------------
print("2a. DATE/TIME with letters (named month, AM/PM) -- multi-alphabet path")
# ---------------------------------------------------------------------------
# Real-model testing found DATE/TIME can carry letters as well as digits
# ("14 noyabr 2018", "2:54 PM"). LABEL_ALPHABET alone (DIGIT_ALPHABET only)
# would leave those letters as untouched template text -- the true month
# name or AM/PM fully readable in an otherwise "masked" value. These cases
# check the letters actually change too, not just the digits.
MIXED_DATE_TIME = [
    ("DATE", "14 noyabr 2018"),
    ("DATE", "14 февраля 1995"),
    ("DATE", "1 Ocak 1992"),
    ("DATE", "March 3rd, 1988"),
    ("TIME", "2:54 PM"),
    ("TIME", "11:01 PM"),
]
for label, value in MIXED_DATE_TIME:
    masked = mask_value(label, value, KEY1)
    recovered = unmask_value(label, masked, KEY1)
    check(recovered == value,
          f"{label} with letters round-trips exactly: {value!r}",
          f"masked={masked!r} recovered={recovered!r}")
    check(len(masked) == len(value),
          f"{label} with letters keeps the original length: {value!r}",
          f"masked={masked!r} ({len(masked)} vs {len(value)})")
    orig_letters = "".join(c for c in value if c in LETTER_ALPHABET)
    masked_letters = "".join(c for c in masked if c in LETTER_ALPHABET)
    check(orig_letters and masked_letters != orig_letters,
          f"{label}'s letter portion (month name / AM-PM) actually changes, "
          f"not just its digits: {value!r}",
          f"orig letters={orig_letters!r} masked letters={masked_letters!r}")
    # Character CLASS is preserved positionally: every digit position in
    # the original is still a digit in the masked output, and vice versa
    # for letters -- confirms the two classes don't bleed into each
    # other's positions.
    check(all((c1 in DIGIT_ALPHABET) == (c2 in DIGIT_ALPHABET)
             for c1, c2 in zip(value, masked)
             if c1 in DIGIT_ALPHABET or c1 in LETTER_ALPHABET),
          f"{label}: digit positions stay digits, letter positions stay "
          f"letters: {value!r} -> {masked!r}")

# Pure-numeric DATE/TIME values must behave EXACTLY as before this change
# (no letters to touch -> the multi-alphabet path degrades to the same
# digit-only result as the plain LABEL_ALPHABET path would have given).
check(mask_value("DATE", "15.03.2024", KEY1) == mask_value("DATE", "15.03.2024", KEY1),
      "a pure-numeric DATE is still deterministic under the new path")
numeric_masked = mask_value("DATE", "15.03.2024", KEY1)
check(all(c in DIGIT_ALPHABET or c in ".-/" for c in numeric_masked),
      "a pure-numeric DATE's masked output has no stray letters introduced",
      numeric_masked)

check(set(MULTI_ALPHABET_LABELS) == {"DATE", "TIME", "BUILDINGNUM", "STREET",
                                     "ZIPCODE", "CITY"},
      "exactly the labels whose real corpus values mix digits and letters "
      "use the multi-alphabet path", sorted(MULTI_ALPHABET_LABELS))


# ---------------------------------------------------------------------------
print("2b. Values over FF3's length ceiling (chunking fallback)")
# ---------------------------------------------------------------------------
OVERLONG = [
    ("STREET", "Çingiz Mehdi oğlu Cuvarlı prospekti"),  # the real value that
    ("STREET", "İran İslam Respublikası ilə bağlantı pr."),  # broke this first
    ("STREET", "a" * 80),  # well past the ceiling either way
]
for label, value in OVERLONG:
    masked = mask_value(label, value, KEY1)
    recovered = unmask_value(label, masked, KEY1)
    check(recovered == value,
          f"over-ceiling {label} value round-trips via chunking: {value!r}",
          f"masked={masked!r} recovered={recovered!r}")
    check(len(masked) == len(value),
          f"over-ceiling {label} masked value keeps original length",
          f"{len(masked)} vs {len(value)}")


# ---------------------------------------------------------------------------
print("3. Determinism and key-sensitivity")
# ---------------------------------------------------------------------------
m1 = mask_value("TELEPHONENUM", "0501234567", KEY1)
m2 = mask_value("TELEPHONENUM", "0501234567", KEY1)
check(m1 == m2, "same (label, value, key) always masks the same way")

m3 = mask_value("TELEPHONENUM", "0501234567", KEY2)
check(m1 != m3, "a different key produces a different masked value")
check(unmask_value("TELEPHONENUM", m3, KEY2) == "0501234567",
      "the differently-keyed value still round-trips under ITS OWN key")

m_age1 = mask_value("AGE", "34", KEY1)
m_age2 = mask_value("AGE", "34", KEY1)
check(m_age1 == m_age2, "small-domain path is also deterministic")
check(unmask_value("AGE", m_age1, KEY2) != "34" or KEY1 == KEY2,
      "small-domain path is also key-sensitive (wrong key ~never recovers "
      "the right small value)")


# ---------------------------------------------------------------------------
print("4. All 27 taxonomy labels are maskable; an unknown label still "
      "fails loudly")
# ---------------------------------------------------------------------------
# There is no longer any label in the taxonomy this module refuses. The six
# that used to be excluded (URL, API_KEY, ACCESS_TOKEN, PRIVATE_KEY,
# IPV4_ADDRESS, IPV6_ADDRESS) were left in PLAINTEXT and merely reported --
# which for an IP address or a private key is the worst possible thing on
# the list to leave readable.
TAXONOMY = json.loads(
    (ROOT / "data/processed/merged/labels.json").read_text(encoding="utf-8"))
entity_types = sorted({l.split("-", 1)[1] for l in TAXONOMY["labels"]
                       if l != "O"})
check(len(entity_types) == 27, "taxonomy really is 27 entity types",
      len(entity_types))
unmaskable = [t for t in entity_types if t not in LABEL_ALPHABET]
check(unmaskable == [],
      "every one of the 27 taxonomy labels has a reversible mask",
      unmaskable)

# An unknown label -- a typo, or a taxonomy change nobody wired up -- must
# still raise rather than silently pass the value through untouched.
try:
    mask_value("NOT_A_REAL_LABEL", "irrelevant", KEY1)
    check(False, "an unknown label raises rather than silently mis-masking")
except ValueError:
    check(True, "an unknown label raises rather than silently mis-masking")


# ---------------------------------------------------------------------------
print("4b. The six formerly-unmasked labels: real values, real formats")
# ---------------------------------------------------------------------------
NEWLY_SUPPORTED = [
    ("IPV4_ADDRESS", "192.168.216.30"),
    ("IPV4_ADDRESS", "15.199.229.147"),
    ("IPV4_ADDRESS", "8.8.8.8"),                 # 1-digit octets
    ("IPV6_ADDRESS", "3956:5813:315e:39a0:f162:ac8f:4041:5db7"),
    ("URL", "https://login.araz-mebel.az/reset/pZdJ0lSAbDJTQaB_6xn"),
    ("API_KEY", "xapp-1-VOUYMQADH-0ur5ne4bitHPSj8IXKOrplZk"),
    ("ACCESS_TOKEN", "i_NLOD77h2yvl_CX5_AB1lCskUmSXWY5VBKY.4I4bGDo-rW8d"),
    ("PRIVATE_KEY", "ssh-rsa AAAAB3NzaC1yc2E9xB1Yfy0802h4ii8SZsW5AOxbUHrU"),
    ("PRIVATE_KEY",
     "-----BEGIN PRIVATE KEY-----\nzB1badLganCQNvJxQmv45N9fX639R0W2\n"
     "-----END PRIVATE KEY-----"),
]
for label, value in NEWLY_SUPPORTED:
    masked = mask_value(label, value, KEY1)
    check(unmask_value(label, masked, KEY1) == value,
          f"{label} round-trips exactly: {value[:40]!r}", masked[:60])
    check(len(masked) == len(value),
          f"{label} preserves length: {value[:40]!r}")
    check(masked != value, f"{label} actually changed: {value[:40]!r}")

# Format validity: a masked value that no longer parses as the format it is
# impersonating defeats the point of format-preserving encryption.
for _, value in [c for c in NEWLY_SUPPORTED if c[0] == "IPV4_ADDRESS"]:
    masked = mask_value("IPV4_ADDRESS", value, KEY1)
    octets = masked.split(".")
    check(len(octets) == 4
          and all(o.isdigit() and 0 <= int(o) <= 255 for o in octets)
          and all(o == str(int(o)) for o in octets),
          f"masked IPv4 is still a valid, leading-zero-free dotted quad: "
          f"{value} -> {masked}")

ipv6_masked = mask_value("IPV6_ADDRESS",
                         "3956:5813:315e:39a0:f162:ac8f:4041:5db7", KEY1)
check(all(c in "0123456789abcdefABCDEF:" for c in ipv6_masked),
      "masked IPv6 contains only hex digits and colons", ipv6_masked)

url_masked = mask_value("URL", "https://login.araz-mebel.az/reset/abc", KEY1)
check(url_masked.startswith("https://"),
      "a URL's scheme survives masking -- it identifies a protocol, not a "
      "person, and mangling it would cost plausibility for no protection",
      url_masked)
check("login" not in url_masked and "araz-mebel" not in url_masked,
      "...but the host IS masked", url_masked)

pem = ("-----BEGIN PRIVATE KEY-----\nzB1badLganCQNvJxQmv45N9fX639R0W2\n"
       "-----END PRIVATE KEY-----")
pem_masked = mask_value("PRIVATE_KEY", pem, KEY1)
check("-----BEGIN PRIVATE KEY-----" in pem_masked
      and "-----END PRIVATE KEY-----" in pem_masked,
      "a PEM key keeps its armour (which says only what KIND of key it is)",
      pem_masked[:40])
check("zB1badLganCQNvJxQmv45N9fX639R0W2" not in pem_masked,
      "...but the key material itself is gone", pem_masked)

ssh = "ssh-rsa AAAAB3NzaC1yc2E9xB1Yfy0802h4ii8SZsW5"
ssh_masked = mask_value("PRIVATE_KEY", ssh, KEY1)
check(ssh_masked.startswith("ssh-rsa "),
      "an SSH key keeps its type prefix", ssh_masked)
check("AAAAB3NzaC1yc2E9xB1Yfy0802h4ii8SZsW5" not in ssh_masked,
      "...but the key body is gone", ssh_masked)


# ---------------------------------------------------------------------------
print("4c. Structural leaks: no alphanumeric character may be incapable "
      "of being masked")
# ---------------------------------------------------------------------------
# The bug class this guards against is NOT "the cipher mapped a character to
# itself" (that is ordinary chance, ~1/alphabet_size per position, and
# unavoidable). It is "this character is not in the label's alphabet at
# all", so it passes through verbatim EVERY time, for every key. A
# corpus-wide sweep found five labels doing exactly that: BUILDINGNUM
# (381/861 -- "215A"), MAC_ADDRESS (362/1000 -- lowercase hex), IBAN
# (93/1200 -- lowercase, leaking country and bank code), STREET (158/1200 --
# digits in street names) and ZIPCODE (561/561 -- the "AZ" prefix).
LEAK_CASES = [
    ("BUILDINGNUM", "215A"),
    ("BUILDINGNUM", "48E"),
    ("MAC_ADDRESS", "00:1b:44:3f:2f:29"),      # lowercase hex
    ("MAC_ADDRESS", "e4-5f-01-a5-9b-4d"),      # lowercase, dash-separated
    ("IBAN", "az98gtzy31809389086024296585"),  # lowercase
    ("STREET", "переулок 2-джи Зира"),         # digit inside a street name
    ("STREET", "Կարո Ալվարյան փողոց"),         # Armenian
    ("ZIPCODE", "AZ4740"),
]
for label, value in LEAK_CASES:
    alphabets = MULTI_ALPHABET_LABELS.get(label) or [LABEL_ALPHABET[label]]
    covered = set("".join(alphabets))
    uncovered = [c for c in value if c.isalnum() and c not in covered]
    check(not uncovered,
          f"{label}: every alphanumeric character of {value[:30]!r} is "
          f"inside the alphabet, so none can pass through verbatim",
          uncovered)
    masked = mask_value(label, value, KEY1)
    check(unmask_value(label, masked, KEY1) == value,
          f"{label} still round-trips: {value[:30]!r}", masked)

mac_masked = mask_value("MAC_ADDRESS", "00:1b:44:3f:2f:29", KEY1)
check(all(c in "0123456789abcdefABCDEF:" for c in mac_masked),
      "a masked MAC is still valid hex -- masking it through a general "
      "alnum alphabet used to produce 'X'/'U'/'K', which is not a MAC",
      mac_masked)
zip_masked = mask_value("ZIPCODE", "AZ4740", KEY1)
check(all(c.isascii() for c in zip_masked),
      "a masked postcode's letters stay Latin, not Cyrillic -- 'Оo6820' "
      "reads as corrupted data rather than as masked data", zip_masked)


# ---------------------------------------------------------------------------
print("5. Large-scale round-trip against real corpus values")
# ---------------------------------------------------------------------------
try:
    counts = Counter()
    total = 0
    seen_values = set()
    with (ROOT / "data/processed/merged/test.docs.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            for e in r.get("entities", []):
                # A known pre-existing gap (see
                # test_100k_readiness.py's own KeyError: 'text' note): some
                # entities lack the 'text' field. Derive it from offsets --
                # the same value either way, just not always cached.
                label = e["label"]
                value = e.get("text")
                if value is None:
                    value = r["text"][e["start"]:e["end"]]
                if label not in LABEL_ALPHABET:
                    continue
                key = (label, value)
                if key in seen_values:
                    continue
                seen_values.add(key)
                total += 1
                try:
                    masked = mask_value(label, value, KEY1)
                    recovered = unmask_value(label, masked, KEY1)
                except Exception as exc:
                    FAILURES.append(f"real-value EXCEPTION {label} {value!r}: {exc}")
                    counts["exception"] += 1
                    continue
                if recovered == value:
                    counts["ok"] += 1
                else:
                    counts["mismatch"] += 1
                    if counts["mismatch"] <= 8:
                        FAILURES.append(
                            f"real-value mismatch {label} {value!r} -> "
                            f"{masked!r} -> {recovered!r}")
            if total >= 4000:
                break

    check(total > 0, "found real corpus values to test against", total)
    check(counts["ok"] == total,
          f"all {total} unique real (label, value) pairs round-trip exactly",
          dict(counts))
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
