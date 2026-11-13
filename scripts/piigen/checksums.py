"""Validity primitives for every structured entity type.

The previous pipeline validated exactly two labels (CREDIT_CARD, IBAN) and had
an escape hatch that admitted any 14-34 character digit string as an IBAN. That
matters more than it sounds: the Day 8 regex layer will Luhn-check cards and
mod-97-check IBANs, so training data containing invalid ones is data the regex
layer can never confirm, which silently inflates apparent model-only recall.

Every function here is used in BOTH directions -- to construct valid values and
to verify them -- so a generator and its validator cannot disagree.
"""

from __future__ import annotations

import ipaddress
import re
import string

# ---------------------------------------------------------------------------
# Luhn (credit cards, IMEI)
# ---------------------------------------------------------------------------

def luhn_check_digit(digits: str) -> str:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def luhn_valid(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    if len(digits) < 12:
        return False
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# Issuer prefixes that actually exist, with their legal lengths and a rough
# market weight. Generating from this table (rather than from a free-form digit
# string) is what makes a generated card indistinguishable in *shape* from a
# real one, which matters because the Day 8 regex layer will BIN-check.
CARD_SPECS = [
    # (prefix pool, total length, brand, sampling weight)
    (["4"], 16, "visa", 26),
    (["4"], 13, "visa13", 2),
    (["51", "52", "53", "54", "55"], 16, "mastercard", 18),
    (["2221", "2229", "2720", "2300"], 16, "mastercard2", 5),
    (["34", "37"], 15, "amex", 8),
    (["6011", "6221", "6445"], 16, "discover", 4),
    (["2200", "2201", "2202", "2204"], 16, "mir", 8),          # RU
    (["9792"], 16, "troy", 5),                                  # TR
    (["4169", "4127", "5239"], 16, "az_issuer", 6),             # AZ
    (["3528", "3538"], 16, "jcb", 2),
    (["62"], 16, "unionpay", 3),
]


def card_brand_ok(number: str) -> bool:
    digits = re.sub(r"\D", "", number)
    for prefixes, length, _brand, _w in CARD_SPECS:
        if len(digits) == length and any(digits.startswith(p) for p in prefixes):
            return True
    return False


def credit_card_valid(number: str) -> bool:
    """Luhn AND a real issuer prefix at a legal length."""
    return luhn_valid(number) and card_brand_ok(number)


# ---------------------------------------------------------------------------
# IBAN (ISO 13616) and domestic account numbers
# ---------------------------------------------------------------------------

# length of the full IBAN per country, used to reject wrong-length values
IBAN_LENGTHS = {
    "AZ": 28, "TR": 26, "GB": 22, "DE": 22, "FR": 27, "NL": 18, "ES": 24,
    "IT": 27, "PL": 28, "PT": 25, "CH": 21, "AT": 20, "BE": 16, "GE": 22,
    "KZ": 20, "UA": 29, "RO": 24, "BG": 22, "HU": 28, "CZ": 24, "SE": 24,
    "NO": 15, "DK": 18, "FI": 18, "IE": 22, "GR": 27, "AE": 23, "SA": 24,
}


# Count of leading ALPHA characters in the BBAN, per country. Needed so a
# generated IBAN has the right *shape*, not merely the right length.
IBAN_BBAN_ALPHA = {
    "AZ": 4, "GB": 4, "NL": 4, "IE": 4, "RO": 4, "GE": 2, "IT": 1,
    "TR": 0, "DE": 0, "FR": 0, "ES": 0, "PL": 0, "KZ": 0, "UA": 0, "AE": 0,
    "CH": 0, "AT": 0, "BE": 0, "PT": 0, "SE": 0, "NO": 0, "BG": 4, "HU": 0,
    "CZ": 0, "DK": 0, "FI": 0, "GR": 0, "SA": 0,
}


def iban_check_digits(country: str, bban: str) -> str:
    rearranged = f"{bban}{country}00"
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c
                      for c in rearranged.upper())
    return f"{98 - int(numeric) % 97:02d}"


def iban_valid(value: str) -> bool:
    """Strict ISO 13616: country code, length, alphabet, and mod-97 == 1."""
    s = re.sub(r"[\s-]", "", value).upper()
    if len(s) < 15 or len(s) > 34:
        return False
    if not (s[:2].isalpha() and s[2:4].isdigit()):
        return False
    if not s.isalnum():
        return False
    expected = IBAN_LENGTHS.get(s[:2])
    if expected is not None and len(s) != expected:
        return False
    rearranged = s[4:] + s[:4]
    try:
        numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def bank_account_valid(value: str) -> bool:
    """Alias kept for call-site readability (the label is IBAN)."""
    return iban_valid(value)


# ---------------------------------------------------------------------------
# VIN (ISO 3779)
# ---------------------------------------------------------------------------

_VIN_VALUES = {
    **{c: i for i, c in enumerate("ABCDEFGHI", start=1)},
    **{c: i for i, c in enumerate("JKLMNOP", start=1)},
    **{c: i for i, c in enumerate("QR", start=8)},
    **{c: i for i, c in enumerate("STUVWXYZ", start=2)},
    **{str(d): d for d in range(10)},
}
_VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]
VIN_ALPHABET = "".join(c for c in string.ascii_uppercase if c not in "IOQ") + string.digits


def vin_check_digit(vin17: str) -> str:
    """Used by negatives.py to build a VIN-shaped hard negative with a
    deliberately wrong check digit -- no label in the current taxonomy is a
    VIN itself, so only the construction side is needed here."""
    total = sum(_VIN_VALUES[c] * w for c, w in zip(vin17.upper(), _VIN_WEIGHTS))
    r = total % 11
    return "X" if r == 10 else str(r)


# ---------------------------------------------------------------------------
# MAC address
# ---------------------------------------------------------------------------

_MAC_RE = re.compile(r"^(?:[0-9A-Fa-f]{2}([:-]))(?:[0-9A-Fa-f]{2}\1){4}[0-9A-Fa-f]{2}$")
_MAC_DOT_RE = re.compile(r"^(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}$")


def mac_valid(value: str) -> bool:
    v = value.strip()
    return bool(_MAC_RE.match(v) or _MAC_DOT_RE.match(v))


# ---------------------------------------------------------------------------
# IP addresses
# ---------------------------------------------------------------------------

def ip_valid(value: str) -> bool:
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


def ipv4_valid(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value.strip())
        return True
    except ValueError:
        return False


def ipv6_valid(value: str) -> bool:
    try:
        ipaddress.IPv6Address(value.strip())
        return True
    except ValueError:
        return False


def ip_is_private(value: str) -> bool:
    try:
        addr = ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


def ip_is_private_or_reserved(value: str) -> bool:
    """Used by the analyzer: 88% of the old dataset's IPs were RFC1918, which
    teaches a `10.`/`192.168.` prefix prior instead of dotted-quad structure."""
    try:
        addr = ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return bool(addr.is_private or addr.is_reserved or addr.is_loopback
                or addr.is_link_local or addr.is_multicast)


# ---------------------------------------------------------------------------
# Email / URL -- structural rather than checksum, but still verifiable
# ---------------------------------------------------------------------------

# Domain hyphens tolerate the common Unicode dash lookalikes ('\u2010'-
# '\u2015' hyphen/figure/en/em dash, '\u2212' minus sign) alongside the
# plain ASCII '-'. LLM-generated text substitutes these for a real hyphen
# often enough (found via a real corpus document: an LLM wrote
# "hal-x\u2013billing.az" with an en dash where a hyphen belongs) that an
# otherwise-obviously-an-email value was going unrecognized by both this
# validator and pattern_fallback.py's regex -- not just unlabeled in gold,
# but structurally invisible to the regex safety net too.
_DASHES = "\\-\u2010-\u2015\u2212"
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    rf"@(?:[A-Za-z0-9](?:[A-Za-z0-9{_DASHES}]{{0,61}}[A-Za-z0-9])?\.)+[A-Za-z]{{2,}}$"
)


def email_valid(value: str) -> bool:
    return bool(_EMAIL_RE.match(value.strip()))


_URL_RE = re.compile(r"^https?://[^\s<>\"']+$")

# Query parameters that carry a credential. A URL_WITH_TOKEN must have one of
# these (or a long opaque path/fragment segment) -- a bare marketing URL is not
# PII and labelling it as such would poison precision.
TOKEN_PARAMS = {
    "access_token", "token", "session", "session_id", "reset_token", "auth",
    "key", "api_key", "apikey", "t", "code", "id_token", "sig", "signature",
    "invite", "confirm", "jwt", "otp", "ticket", "secret", "hash", "verify",
}


def url_valid(value: str) -> bool:
    v = value.strip()
    if not _URL_RE.match(v):
        return False
    return bool(re.search(r"[?&#/](?:[A-Za-z0-9_-]{16,})", v)
                or re.search(r"(token|key|secret|auth|session|reset|invite|t)=", v, re.I))


def url_with_token_valid(value: str) -> bool:
    """Stricter than url_valid: the credential component must be identifiable."""
    v = value.strip()
    if not _URL_RE.match(v):
        return False
    m = re.search(r"[?&#]([A-Za-z0-9_]+)=([A-Za-z0-9._~-]{8,})", v)
    if m and m.group(1).lower() in TOKEN_PARAMS:
        return True
    if re.search(r"#[A-Za-z0-9._~-]{16,}$", v):
        return True
    for seg in v.split("?")[0].split("/")[3:]:
        if len(seg) >= 16 and re.fullmatch(r"[A-Za-z0-9._~-]+", seg):
            return True
    return False


# ---------------------------------------------------------------------------
# ICCID (SIM card identifier) -- Luhn, per ITU-T E.118 / ISO 7812-1
# ---------------------------------------------------------------------------

def iccid_valid(value: str) -> bool:
    digits = re.sub(r"[\s-]", "", value)
    if not (digits.isdigit() and 18 <= len(digits) <= 20 and digits.startswith("89")):
        return False
    return luhn_valid(digits)


# ---------------------------------------------------------------------------
# API keys / access tokens / private keys -- shape-based, no checksum exists
# ---------------------------------------------------------------------------

_API_KEY_RE = re.compile(
    r"^(?:"
    r"sk_live_[A-Za-z0-9]{20,}"
    r"|sk_test_[A-Za-z0-9]{20,}"
    r"|pk_live_[A-Za-z0-9]{20,}"
    r"|rk_[A-Za-z0-9]{20,}"
    r"|gh[po]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{60,}"
    r"|AKIA[A-Z0-9]{16}"
    r"|ASIA[A-Z0-9]{16}"
    r"|xoxb-\d{8,}-\d{8,}-[A-Za-z0-9]{20,}"
    r"|xapp-1-[A-Z0-9]{6,}-[A-Za-z0-9]{20,}"
    r"|AIza[A-Za-z0-9_-]{30,}"
    r"|glpat-[A-Za-z0-9_-]{18,}"
    r"|npm_[A-Za-z0-9]{30,}"
    r"|dop_v1_[a-f0-9]{60,}"
    r"|SG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{40,}"
    r"|shpat_[a-f0-9]{30,}"
    r"|sq0atp-[A-Za-z0-9_-]{18,}"
    # generic, vendor-neutral (P2-1)
    r"|(?:key|api|apikey|svc)_[A-Za-z0-9]{20,64}"
    r"|sk-(?:live|test)-[A-Za-z0-9]{20,64}"
    r")$"
)


def api_key_valid(value: str) -> bool:
    return bool(_API_KEY_RE.match(value.strip()))


# ACCESS_TOKEN accepts three forms (data/schema.md). The benchmark's real
# tokens were all prefixed (`at_`/`bearer_`/`tok_`), so the old JWT-only
# definition was wrong, not too strict. Length and alphabet stay strict, and
# anything that is a valid API_KEY is never also an ACCESS_TOKEN.
_ACCESS_TOKEN_RE = re.compile(
    r"^[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}$")
_ACCESS_TOKEN_PREFIXED_RE = re.compile(
    r"^(?:at_|bearer_|tok_|oauth_|sess_|atk-|pat_)[A-Za-z0-9_-]{20,64}$")
_ACCESS_TOKEN_BARE_HEX_RE = re.compile(r"^[0-9a-f]{32,64}$")
_ACCESS_TOKEN_BARE_B64_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


def access_token_valid(value: str) -> bool:
    v = value.strip()
    if api_key_valid(v):
        return False
    if (_ACCESS_TOKEN_RE.match(v) or _ACCESS_TOKEN_PREFIXED_RE.match(v)
            or _ACCESS_TOKEN_BARE_HEX_RE.match(v)):
        return True
    # a bare base64url token must look random: mixed case and a digit, so a
    # long snake_case identifier is not a token
    return bool(_ACCESS_TOKEN_BARE_B64_RE.match(v)
                and re.search(r"[A-Z]", v) and re.search(r"[a-z]", v)
                and re.search(r"\d", v))


_PRIVATE_KEY_RE = re.compile(
    r"^-----BEGIN [A-Z ]*PRIVATE KEY-----.*-----END [A-Z ]*PRIVATE KEY-----$",
    re.DOTALL)


# D-36a: an OpenSSH public-key line (`ssh-rsa AAAA...`) is a public key, not a
# secret; it is a look-alike now (negatives `public_key_ssh`). An OpenSSH
# PRIVATE key (`-----BEGIN OPENSSH PRIVATE KEY-----`) is still a PEM block.
SSH_PUBLIC_KEY_PREFIXES = ("ssh-rsa ", "ssh-ed25519 ", "ssh-dss ", "ecdsa-sha2-")


def private_key_valid(value: str) -> bool:
    return bool(_PRIVATE_KEY_RE.match(value.strip()))


# ---------------------------------------------------------------------------
# Azerbaijan-local identifiers. AZ_FIN excludes I/O (34-char alphabet);
# AZ_PASSPORT_NUMBER's leading letter includes them -- see data/schema.md.
# AZ_VOEN's check digit is unverified (source taxonomy is explicit about
# this), so its validator checks length/digits only, never a computed digit.
# ---------------------------------------------------------------------------

AZ_FIN_ALPHABET = "".join(c for c in string.ascii_uppercase if c not in "IO") + string.digits
_AZ_FIN_RE = re.compile(rf"^[{AZ_FIN_ALPHABET}]{{7}}$")
# D-51h (D-34d, the shape decides): an ID card is any two capital letters + 7
# digits, or DYI/MYI + 7; a driver licence is two letters + 6. Was AA/AB/DYI/MYI
# only, which made an unfamiliar prefix read as a licence (53 benchmark errors)
_AZ_ID_CARD_RE = re.compile(r"^(?:[A-Z]{2}|DYI|MYI)\d{7}$")
_AZ_PASSPORT_RE = re.compile(r"^[A-Z]\d{8}$")
_AZ_DRIVER_LICENSE_RE = re.compile(r"^[A-Z]{2}\d{6}$")


def az_fin_valid(value: str) -> bool:
    return bool(_AZ_FIN_RE.match(value.strip().upper()))


def az_id_card_valid(value: str) -> bool:
    return bool(_AZ_ID_CARD_RE.match(value.strip().upper()))


def az_passport_valid(value: str) -> bool:
    return bool(_AZ_PASSPORT_RE.match(value.strip().upper()))


def az_voen_valid(value: str) -> bool:
    digits = re.sub(r"\s", "", value)
    return digits.isdigit() and len(digits) in (10, 15)


def az_driver_license_valid(value: str) -> bool:
    return bool(_AZ_DRIVER_LICENSE_RE.match(value.strip().upper()))


# ---------------------------------------------------------------------------
# anchor_required labels (CARD_SECURITY_CODE, TIME, AGE, DATE). These are not
# in STRUCTURED_LABELS, so validate_example() never calls them on corpus
# records; they exist so a decoy (`CVV kodu 12345`, `saat 25:81`, `yaş 999`,
# `31.02.2026`) can be proven invalid by a check independent of the code that
# made it (P2-2, rule R4). BUILDINGNUM has none: `otaq 247` is a well-formed
# number, and only its anchor makes it not a building number.
# ---------------------------------------------------------------------------

# D-30b (fix round): a CVV written with one dash between its digits (`12-3`,
# `1-23`, `12-34`) is a real code. Run B's data had none of these as values and
# ~300 as decoys, and it found 4 of the benchmark's 80 dashed CVVs. A slash or
# any other separator stays invalid.
_CVV_RE = re.compile(r"\d{3,4}|\d{2}-\d{1,2}|\d-\d{2}")


def card_security_code_valid(value: str) -> bool:
    return bool(_CVV_RE.fullmatch(value.strip()))


_TIME_RE = re.compile(
    r"(\d{1,2})[:.](\d{2})(?::(\d{2}))?(?:\s*([AaPp])\.?\s?[Mm]\.?)?")


def time_valid(value: str) -> bool:
    m = _TIME_RE.fullmatch(value.strip())
    if not m:
        return False
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3) is not None and int(m.group(3)) > 59:
        return False
    if m.group(4):                              # 12-hour clock
        return 1 <= h <= 12 and mi <= 59
    # D-57: `24:00` is a real time, the end of a day (`24:00-dək`)
    if h == 24 and mi == 0 and not int(m.group(3) or 0):
        return True
    return h <= 23 and mi <= 59


def age_valid(value: str) -> bool:
    v = value.strip()
    return v.isdigit() and len(v) <= 3 and int(v) <= 130


def _real_date(y: int, m: int, d: int) -> bool:
    import datetime
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False


def date_valid(value: str) -> bool:
    """A worded date (a month word of 2+ letters) is accepted as written; a
    numeric one must be a real calendar date. Day/month order is ambiguous
    across locales, so d/m or m/d either passes -- 31.02.2026 fails both.
    An en or em dash counts as a hyphen (`12–11–2022`, D-17)."""
    v = value.strip().replace("–", "-").replace("—", "-")
    if re.search(r"[^\W\d_]{2,}", v):
        return True
    m = re.fullmatch(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", v)
    if m:
        return _real_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})([./-])(\d{1,2})\2(\d{4}|\d{2})", v)
    if not m:
        return False
    a, b, y = int(m.group(1)), int(m.group(3)), m.group(4)
    year = int(y) if len(y) == 4 else 2000 + int(y)
    return _real_date(year, b, a) or _real_date(year, a, b)


# ---------------------------------------------------------------------------
# Dispatch used by the Validator -- one entry per `pattern`/`hybrid` tier
# label in data/schema.md (STRUCTURED_LABELS in config.py).
# ---------------------------------------------------------------------------

STRUCTURED_VALIDATORS = {
    "API_KEY": api_key_valid,
    "ACCESS_TOKEN": access_token_valid,
    "PRIVATE_KEY": private_key_valid,
    "PAYMENT_CARD_NUMBER": credit_card_valid,
    "IBAN": bank_account_valid,
    "IPV4_ADDRESS": ipv4_valid,
    "IPV6_ADDRESS": ipv6_valid,
    "MAC_ADDRESS": mac_valid,
    "URL": url_with_token_valid,
    "ICCID": iccid_valid,
    "EMAIL": email_valid,
    "AZ_FIN": az_fin_valid,
    "AZ_ID_CARD_NUMBER": az_id_card_valid,
    "AZ_PASSPORT_NUMBER": az_passport_valid,
    "AZ_VOEN": az_voen_valid,
    "AZ_DRIVER_LICENSE_NUMBER": az_driver_license_valid,
    # TELEPHONENUM and ZIPCODE are hybrid-tier: only their pattern-detectable
    # variant is checked here, format-only (no checksum exists for either).
    "TELEPHONENUM": lambda v: bool(re.sub(r"[\s()+-]", "", v).isdigit()
                                   and 7 <= len(re.sub(r"\D", "", v)) <= 15),
    "ZIPCODE": lambda v: bool(re.fullmatch(r"AZ\d{4}", v.strip().upper())
                              or re.fullmatch(r"\d{4}", v.strip())),
}
