"""Hard negatives and adversarial near-misses.

Two distinct jobs, both aimed at precision.

**Hard negatives** are strings that resemble PII but are not: order IDs, UUIDs,
git SHAs, ports, version strings, coordinates. The old generator had 16 such
families and reached ~21% document coverage.

**Adversarial near-misses** are the harder and more valuable class: values that
a *regex* would match but that are structurally invalid, or that sit one
character away from being real PII. A model that has only seen valid cards
learns "16 digits => CREDIT_CARD"; a model that has also seen Luhn-invalid
16-digit loyalty numbers has to learn something closer to the real rule. These
are what separate a model that learned structure from one that learned shape,
and the previous dataset had none at all.

Everything here is deliberately NOT labeled. The document that contains it must
leave it as plain text.
"""

from __future__ import annotations

import base64
import functools
import json
import logging
import random
import re
import string
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import checksums as CK
from .leak_screen import is_forbidden

log = logging.getLogger(__name__)

_HEX = "0123456789abcdef"
_UP = string.ascii_uppercase
_D = string.digits


def _r(rng, alphabet, k):
    return "".join(rng.choice(alphabet) for _ in range(k))


def _not_id_prefix3(rng) -> str:
    """Three capitals that are not an ID-card prefix (DYI/MYI). D-51h: any
    two letters + 7 digits is an ID card now (the length decides, D-34d), so
    an order number takes three letters + 7 digits."""
    while True:
        prefix = _r(rng, _UP, 3)
        if prefix not in ("DYI", "MYI"):
            return prefix


def _luhn_bad_digits(rng, n: int) -> str:
    body = _r(rng, _D, n - 1)
    good = CK.luhn_check_digit(body)
    return body + str((int(good) + rng.randint(1, 9)) % 10)


# ---------------------------------------------------------------------------
# Hard negatives -- resemble PII, are not PII
# ---------------------------------------------------------------------------

HARD_NEGATIVES = {
    "ORDER_ID": lambda lang, r: r.choice([
        f"ORD-{r.randint(2021, 2026)}-{r.randint(10000, 99999)}",
        f"#{r.randint(100000, 9999999)}", f"ORD{_r(r, _D, 8)}",
        f"SO-{r.randint(100000, 999999)}", f"{_not_id_prefix3(r)}{_r(r, _D, 7)}"]),
    "INVOICE_ID": lambda lang, r: r.choice([
        f"INV-{r.randint(100000, 999999)}",
        f"FA-{r.randint(2021, 2026)}/{r.randint(100, 9999)}",
        f"INV/{r.randint(2021, 2026)}/{r.randint(1000, 99999)}",
        f"BILL-{_r(r, _UP, 3)}-{r.randint(1000, 9999)}"]),
    "TRACKING": lambda lang, r: r.choice([
        _r(r, _UP, 2) + _r(r, _D, 9) + r.choice(["US", "AZ", "RU", "TR", "DE", "GB"]),
        f"TRK-{_r(r, _D, 10)}", _r(r, _D, 12),
        f"1Z{_r(r, _UP + _D, 16)}"]),
    "VERSION": lambda lang, r: r.choice([
        f"v{r.randint(1, 9)}.{r.randint(0, 20)}.{r.randint(0, 30)}",
        f"{r.randint(1, 9)}.{r.randint(0, 20)}.{r.randint(0, 30)}-rc{r.randint(1, 5)}",
        f"build {r.randint(1000, 99999)}", f"iOS {r.randint(15, 19)}.{r.randint(0, 6)}",
        f"{r.randint(1, 9)}.{r.randint(0, 9)}.{r.randint(0, 9)}+{_r(r, _HEX, 7)}",
        f"Android {r.randint(10, 16)}"]),
    "UUID": lambda lang, r: str(uuid.UUID(int=r.getrandbits(128))),
    "SHA256": lambda lang, r: _r(r, _HEX.upper(), 64),
    "MD5": lambda lang, r: _r(r, _HEX.upper(), 32),
    "GIT_SHA": lambda lang, r: _r(r, _HEX, r.choice([7, 8, 10, 12])),
    "HEX_BLOB": lambda lang, r: "0x" + _r(r, "0123456789ABCDEF", r.choice([8, 12, 16])),
    "TIMESTAMP": lambda lang, r: r.choice([
        f"20{r.randint(21, 26)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}T"
        f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}Z",
        f"{r.randint(1700000000, 1799999999)}",
        f"{r.randint(1, 28):02d}.{r.randint(1, 12):02d}.20{r.randint(21, 26)} "
        f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}",
        f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}:{r.randint(0, 59):02d}.{r.randint(100, 999)}"]),
    "REF_CODE": lambda lang, r: r.choice([
        f"REF{_r(r, _D, 6)}", f"CASE-{_r(r, _D, 7)}", f"TKT-{_r(r, _D, 6)}",
        f"{_r(r, _UP, 3)}-{r.randint(100, 999)}", f"PRJ-{r.randint(1000, 9999)}"]),
    "EMPLOYEE_ID": lambda lang, r: r.choice([
        f"EMP{_r(r, _D, 5)}", f"E-{_r(r, _D, 6)}", f"STAFF/{_r(r, _D, 5)}"]),
    "PORT": lambda lang, r: str(r.choice([80, 443, 8080, 8443, 5432, 3306,
                                          6379, 27017, 9200, 5672, 15672, 2181])),
    "AMOUNT": lambda lang, r: r.choice([
        f"{r.randint(10, 9999)}.{r.randint(0, 99):02d}",
        f"{r.randint(100, 99999)} {r.choice(['USD', 'EUR', 'AZN', 'RUB', 'TRY', 'GBP'])}",
        f"{r.choice(['$', '€', '£', '₼', '₺', '₽'])}{r.randint(10, 9999)}.{r.randint(0, 99):02d}"]),
    "SKU": lambda lang, r: r.choice([
        "SKU-" + _r(r, _UP, 3) + "-" + _r(r, _D, 5),
        _r(r, _UP, 4) + "/" + _r(r, _D, 4),
        f"EAN{_r(r, _D, 13)}"]),
    "COORDINATES": lambda lang, r: r.choice([
        f"{r.randint(-89, 89)}.{r.randint(100000, 999999)}, "
        f"{r.randint(-179, 179)}.{r.randint(100000, 999999)}",
        f"{r.randint(30, 60)}°{r.randint(10, 59)}'{r.randint(10, 59)}\"N"]),
    "ERROR_CODE": lambda lang, r: r.choice([
        f"E{_r(r, _D, 4)}", f"ERR_{_r(r, _UP, 6)}", f"0x{_r(r, '0123456789ABCDEF', 8)}",
        f"HTTP {r.choice([400, 401, 403, 404, 409, 422, 429, 500, 502, 503])}",
        f"SQLSTATE[{_r(r, _UP + _D, 5)}]"]),
    "BUILD_HASH": lambda lang, r: f"build-{_r(r, _HEX, 12)}",
    "SESSION_COUNT": lambda lang, r: f"{r.randint(100, 999999)}",
    "PERCENT": lambda lang, r: f"{r.randint(1, 99)}.{r.randint(0, 9)}%",
    "DURATION": lambda lang, r: r.choice([
        f"{r.randint(1, 999)}ms", f"{r.randint(1, 60)}s", f"{r.randint(1, 24)}h",
        f"{r.randint(1, 999)}.{r.randint(0, 99)}s"]),
    "CONTAINER_ID": lambda lang, r: _r(r, _HEX, 12),
    "MEM_ADDR": lambda lang, r: "0x" + _r(r, _HEX, 12),
    "LICENSE_KEY_PRODUCT": lambda lang, r: "-".join(
        _r(r, _UP + _D, 5) for _ in range(5)),
}


# ---------------------------------------------------------------------------
# Adversarial near-misses -- a regex WOULD match these; they are still not PII
# (or are structurally invalid), so the model must use more than surface shape.
# ---------------------------------------------------------------------------

def _imei_bad_luhn(rng) -> str:
    """15 digits failing Luhn, never with the Amex prefixes 34/37 (D-51d)."""
    while True:
        value = _luhn_bad_digits(rng, 15)
        if not value.startswith(("34", "37")):
            return value


def _vin_bad_checkdigit(rng) -> str:
    wmi = rng.choice(["1HG", "WBA", "JHM", "WVW", "5YJ"])
    partial = wmi + _r(rng, CK.VIN_ALPHABET, 5) + "0" + \
        rng.choice("ABCDEFGHJKLMNPRSTVWXY") + rng.choice(CK.VIN_ALPHABET) + _r(rng, _D, 6)
    good = CK.vin_check_digit(partial)
    bad = rng.choice([c for c in "0123456789X" if c != good])
    return partial[:8] + bad + partial[9:]


# D-51d: cards and IBANs are masked whatever their checksum (privacy first,
# as D-33c for FINs). A token classifier cannot compute Luhn or mod-97, so a
# look-alike that differs from a real value only by its checksum
# (`LOYALTY_CARD_LUHN_BAD`, `IBAN_BAD_CHECKSUM`; anchored `card_luhn_invalid`,
# `tracking_code_15_16`) only taught it to doubt real values. They leave the
# generator; the look-alikes whose length or format shows (wrong-length
# cards, truncated IBANs, masked cards) stay.
ADVERSARIAL = {
    # --- invalid check digits on values that are no taxonomy label ----------
    "VIN_BAD_CHECKDIGIT": lambda lang, r: _vin_bad_checkdigit(r),
    # 15 digits: a card only with an Amex prefix (34/37), which is left out
    # here, so the length and prefix show it is no card (D-51d)
    "IMEI_BAD_LUHN": lambda lang, r: _imei_bad_luhn(r),

    # --- truncated / partial credentials -----------------------------------
    "TRUNCATED_API_KEY": lambda lang, r: r.choice([
        "sk_live_" + _r(r, string.ascii_letters + _D, 6) + "...",
        "ghp_" + _r(r, string.ascii_letters + _D, 8) + "…",
        "AKIA" + _r(r, _UP + _D, 6) + "****",
        "Bearer " + _r(r, string.ascii_letters, 5) + "...[redacted]"]),
    "MASKED_CARD": lambda lang, r: r.choice([
        f"**** **** **** {_r(r, _D, 4)}",
        f"{_r(r, _D, 4)} **** **** {_r(r, _D, 4)}",
        f"XXXX-XXXX-XXXX-{_r(r, _D, 4)}",
        f"•••• {_r(r, _D, 4)}"]),
    "MASKED_EMAIL": lambda lang, r: r.choice([
        f"{_r(r, string.ascii_lowercase, 2)}***@{r.choice(string.ascii_lowercase)}****.com",
        f"a***.b***@c******.com", f"{_r(r, string.ascii_lowercase, 3)}***@***.az"]),
    "PARTIAL_PHONE": lambda lang, r: r.choice([
        f"***-***-{_r(r, _D, 4)}", f"+994 ** *** ** {_r(r, _D, 2)}",
        f"ending in {_r(r, _D, 4)}", f"...{_r(r, _D, 3)}"]),
    "REDACTED": lambda lang, r: r.choice([
        "[REDACTED]", "[MASKED]", "<hidden>", "***", "[PII REMOVED]",
        "‹redacted›", "[[email protected]]"]),

    # --- shape collisions ---------------------------------------------------
    "IP_LIKE_VERSION": lambda lang, r: (
        f"{r.randint(1, 20)}.{r.randint(0, 40)}.{r.randint(0, 99)}.{r.randint(256, 9999)}"),
    "IP_INVALID_OCTET": lambda lang, r: (
        f"{r.randint(256, 999)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(256, 999)}"),
    "MAC_LIKE_HASH": lambda lang, r: ":".join(_r(r, _HEX, 2) for _ in range(16)),
    "EMAIL_LIKE_HANDLE": lambda lang, r: r.choice([
        f"@{_r(r, string.ascii_lowercase, 7)}", f"user@{_r(r, string.ascii_lowercase, 6)}",
        f"root@{_r(r, string.ascii_lowercase, 5)}:~$", "npm@latest",
        f"@{_r(r, string.ascii_lowercase, 5)}/{_r(r, string.ascii_lowercase, 6)}"]),
    "URL_NO_TOKEN": lambda lang, r: r.choice([
        "https://docs.internal.dev/getting-started",
        f"https://status.{_r(r, string.ascii_lowercase, 6)}.io/incidents",
        f"https://cdn.{_r(r, string.ascii_lowercase, 5)}.net/assets/logo.svg"]),
    "SSN_LIKE_CODE": lambda lang, r: r.choice([
        f"{r.randint(100, 999)}-{r.randint(10, 99)}-{r.randint(1000, 9999)}",
        f"{r.randint(100, 999)}-{r.randint(100, 999)}-{r.randint(100, 999)}"]),
    "ISBN": lambda lang, r: (
        f"978-{r.randint(0, 9)}-{r.randint(100, 999)}-{r.randint(10000, 99999)}-"
        f"{r.randint(0, 9)}"),
    "DATE_LIKE_ID": lambda lang, r: (
        f"{r.randint(32, 39)}.{r.randint(1, 12):02d}.{r.randint(1990, 2010)}"),
    "PLATE_LIKE_CODE": lambda lang, r: r.choice([
        f"{_r(r, _UP, 2)}-{r.randint(100, 999)}", f"RACK-{_r(r, _UP, 2)}{r.randint(10, 99)}",
        f"{_r(r, _UP, 3)}{r.randint(100, 999)}"]),

    # --- obfuscated PII (still not to be labeled -- it is not a valid value) -
    "OBFUSCATED_EMAIL": lambda lang, r: r.choice([
        f"{_r(r, string.ascii_lowercase, 5)} [at] {_r(r, string.ascii_lowercase, 6)} [dot] com",
        f"{_r(r, string.ascii_lowercase, 4)}(at){_r(r, string.ascii_lowercase, 5)}(dot)net",
        f"{_r(r, string.ascii_lowercase, 5)} AT {_r(r, string.ascii_lowercase, 6)} DOT org"]),
}


def make_negative(kind: str, lang: str, rng: random.Random) -> str:
    if kind in HARD_NEGATIVES:
        return HARD_NEGATIVES[kind](lang, rng)
    return ADVERSARIAL[kind](lang, rng)


HARD_KEYS = sorted(HARD_NEGATIVES)
ADV_KEYS = sorted(ADVERSARIAL)


def random_hard(lang: str, rng: random.Random) -> tuple[str, str]:
    k = rng.choice(HARD_KEYS)
    return k, HARD_NEGATIVES[k](lang, rng)


def random_adversarial(lang: str, rng: random.Random) -> tuple[str, str]:
    k = rng.choice(ADV_KEYS)
    return k, ADVERSARIAL[k](lang, rng)


# ===========================================================================
# Anchored decoys (P2-2) -- a look-alike NEXT TO THE CORRECT ANCHOR WORD
# ===========================================================================
#
# Everything above is unanchored: a bare Luhn-bad number. The benchmark's
# decoys sit beside the anchor of the label they imitate -- `CVV kodu 12345`,
# `saat 25:81`, `yaş 999` -- and checkpoint 1 masked them (1,784 decoy
# triggers + 1,362 spurious masks, median confidence 0.979, so no threshold
# fixes it). Shapes follow the benchmark; values are fresh random, and a
# value the benchmark planted is re-drawn unless it is on the D-2 allowlist.
#
# Three kinds of decoy, and how each is proven not to be PII
# (piigen/test_anchored_decoys.py):
#   * ordinary   -- the value itself is invalid: value_valid(resembles, v)
#                   is False (for the NER-only name labels, which have no
#                   validator: the value is in no name pool);
#   * contextual -- the value is well-formed, and only the anchor makes it
#                   not PII (`otaq 247` is not a building number). Its anchors
#                   must not be ones that license the resembled label;
#   * policy     -- valid under our schema, but decision D-2 says not to mask
#                   it (obvious dummy sequences, names used as company,
#                   project or topic names). Kind names start with `policy_`.

@dataclass(frozen=True)
class DecoyKind:
    kind: str
    resembles: str
    make: Callable[[random.Random], str]
    anchors: tuple[str, ...]        # carrier phrases, each with one "{v}"
    policy: bool = False
    contextual: bool = False


@dataclass(frozen=True)
class PlantedDecoy:
    kind: str
    resembles: str
    value: str
    phrase: str                     # the anchor phrase with the value in it
    policy: bool

    def as_dict(self) -> dict:
        return {"kind": self.kind, "resembles": self.resembles,
                "value": self.value, "phrase": self.phrase,
                "policy": self.policy}


# D-2 policy allowlist: the only benchmark values that may appear in training,
# and only as policy decoys. data/policy_allowlist.txt (one value per line)
# wins; this tuple is the fallback if that file is missing.
_D2_RECOMMENDED_ALLOWLIST = (
    "1234", "12345", "123456", "0000", "4242424242424242", "4111111111111111",
    "5555555555554444", "P12345678", "A12B34",
)
_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = _ROOT / "data" / "policy_allowlist.txt"
BENCHMARK_RECORDS = _ROOT / "benchmarks" / "extracted" / "records.json"


@functools.lru_cache(maxsize=None)
def policy_allowlist() -> frozenset[str]:
    if ALLOWLIST_PATH.exists():
        lines = ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines()
        return frozenset(ln.strip() for ln in lines if ln.strip())
    log.warning("%s missing; using the built-in D-2 allowlist", ALLOWLIST_PATH)
    return frozenset(_D2_RECOMMENDED_ALLOWLIST)


@functools.lru_cache(maxsize=None)
def benchmark_planted_values() -> frozenset[str]:
    """Every value the benchmark planted (gold entities and its must-not-mask
    look-alikes). Model predictions are not benchmark content and are left
    out: they include ordinary words such as `Ərizənin`."""
    if not BENCHMARK_RECORDS.exists():
        log.warning("%s missing: decoys are not screened against benchmark "
                    "values", BENCHMARK_RECORDS)
        return frozenset()
    records = json.loads(BENCHMARK_RECORDS.read_text(encoding="utf-8"))
    return frozenset(e["value"] for r in records for e in r["entries"]
                     if e["kind"] in ("gold", "hard_negative"))


def _allowlisted(pred: Callable[[str], bool]) -> list[str]:
    return sorted(v for v in policy_allowlist() if pred(v))


# -- value makers ------------------------------------------------------------

def _digits(r, lo, hi):
    return _r(r, _D, r.randint(lo, hi))


# D-52c: sequential dummy times, like D-2's test cards and D-41a's `12345`
# CVVs. The benchmark's only seconds look-alike is `12:34:56` (126 of its
# first 5,000 documents; D-2 allowlist); real times with seconds stay TIME
# (#87). blocklist.BLOCKED_EXACT keeps them out of real values.
SEQUENTIAL_TIMES = ("12:34:56", "01:23:45", "10:20:30", "11:11:11", "22:22:22", "12:12:12")
# D-56a (2): sequential IPv4 placeholders, a dummy kind as D-52c's times.
# `1.2.3.4` is the benchmark's (D-2 allowlist); v4.1 masked 53 of its 122.
SEQUENTIAL_IPV4 = ("1.2.3.4", "4.3.2.1", "2.3.4.5", "10.20.30.40", "11.22.33.44", "12.34.56.78")


def _sequential_time(r):
    return r.choice(SEQUENTIAL_TIMES)


def _time_bad_hour(r):
    while True:
        value = f"{r.randint(24, 99)}:{r.randint(0, 59):02d}"
        if value != "24:00":            # D-57: `24:00` is a real time (the end of a day)
            return value


def _time_bad_minute(r):
    return f"{r.randint(0, 23):02d}:{r.randint(60, 99)}"


# v4.2 fix list (19 Oct; v41_shadow_shapes.md, C4): near misses.
# v4.1 still masked half of the C4 time look-alikes (`24:51`, `27:49`,
# `20:61`, the v4 analysis) and a quarter of the date ones
# (`30.02.2027`, `19.15.2022`). The kinds above draw hours 24-99, minutes
# 60-99 and ISO months 13-99, so the model learnt "absurd, not a time"; these
# are one step past the valid range.
def _time_hour_near(r):
    """An hour just past 23 (`24:51`, `27:49`). Never `24:00`, the end of a day."""
    while True:
        value = f"{r.randint(24, 29)}:{r.randint(0, 59):02d}"
        if value != "24:00":
            return value


def _time_minute_near(r):
    """A minute just past 59 (`20:61`)."""
    return f"{r.randint(0, 23):02d}:{r.randint(60, 69)}"


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _date_form(r, day: int, month: int, year: int) -> str:
    """dd.mm.yyyy (55%), dd/mm/yyyy (15%), dd-mm-yyyy (5%) or ISO (25%)."""
    x = r.random()
    if x < 0.25:
        return f"{year}-{month:02d}-{day:02d}"
    sep = "." if x < 0.80 else ("/" if x < 0.95 else "-")
    return f"{day:02d}{sep}{month:02d}{sep}{year}"


def _date_feb_invalid(r):
    """30 or 31 February, or 29 February in a year that is not a leap year
    (`30.02.2027`, `2023-02-29`)."""
    year = r.randint(1950, 2030)
    days = [30, 31] + ([] if _is_leap(year) else [29])
    return _date_form(r, r.choice(days), 2, year)


def _date_month_near(r):
    """Month 13-19 (`19.15.2022`, `2024-13-05`). The day is 13-28 in the
    day-first forms, so reading them month-first is no date either."""
    year, month = r.randint(1950, 2030), r.randint(13, 19)
    day = r.randint(1, 28) if r.random() < 0.25 else r.randint(13, 28)
    value = _date_form(r, day, month, year)
    if not value.startswith(str(year)) and day < 13:
        value = _date_form(r, r.randint(13, 28), month, year)
    return value


def _date_impossible_day(r):
    month, day = r.choice([(2, r.randint(30, 31)), (4, 31), (6, 31), (9, 31),
                           (11, 31), (r.randint(1, 12), 32)])
    sep = r.choice(".../")
    return f"{day:02d}{sep}{month:02d}{sep}{r.randint(1950, 2030)}"


def _date_bad_month(r):
    # day 13-28 as well, so reading it month-first is no valid date either
    sep = r.choice("..-/")
    return f"{r.randint(13, 28)}{sep}{r.randint(13, 99)}{sep}{r.randint(1950, 2030)}"


def _date_iso_bad(r):
    return f"{r.randint(1950, 2030)}-{r.randint(13, 99)}-{r.randint(32, 99)}"


def _card_wrong_length(r):
    """D-51d/D-51h (C4 `decoy_card_iccid_iban`): a card number of a length no
    card of our schema has, so the length shows it (never a Luhn-only
    difference). 13 digits mostly, the length the probes plant; never a
    first digit that starts a 13-digit Visa (4) or a Maestro (5/6, 12-19
    digits), never 0 (a phone's trunk prefix). Some are 14 or 17 digits (no
    14-digit Diners prefix 30/36/38). Grouped in fours a third of the time."""
    n = r.choices((13, 14, 17), weights=(0.7, 0.15, 0.15))[0]
    while True:
        number = r.choice("123789") + _r(r, _D, n - 1)
        if not (n == 14 and number.startswith(("30", "36", "38"))):
            break
    if r.random() < 0.33:
        return " ".join(number[i:i + 4] for i in range(0, n, 4))
    return number


def _fin_8_9_chars(r):
    """8-9 FIN characters; never two letters + 6 or 7 digits, which is a
    driver licence or (D-51h, any prefix) an ID card, both real values."""
    while True:
        value = _r(r, CK.AZ_FIN_ALPHABET, r.choice([8, 9]))
        if not re.fullmatch(r"[A-Z]{2}\d{6,7}", value):
            return value


def _fin_hyphen(r):
    """A FIN-like code with a dash. D-57 M3: half are dashed after the 2nd or
    4th character (`AA99-AA`, `AA-9999`; C4's decoy_fin trigger had that
    shape, v4.2 had none), half 3-3 (`A12-B34`)."""
    letters = CK.AZ_FIN_ALPHABET[:-10]
    if r.random() < 0.5:
        if r.random() < 0.5:                        # AA99-AA
            return f"{_r(r, letters, 2)}{_r(r, _D, 2)}-{_r(r, letters, 2)}"
        return f"{_r(r, letters, 2)}-{_r(r, _D, 4)}"    # AA-9999
    if r.random() < 0.7:                            # A12-B34
        return f"{r.choice(letters)}{_r(r, _D, 2)}-{r.choice(letters)}{_r(r, _D, 2)}"
    return f"{_r(r, CK.AZ_FIN_ALPHABET, 3)}-{_r(r, CK.AZ_FIN_ALPHABET, 3)}"


def _voen_letters(r):
    return _r(r, _D, 2) + _r(r, _UP, 2) + _r(r, _D, 6)


def _passport_letter_inside(r):
    body = list(_r(r, _D, 8))
    body[r.randrange(1, 8)] = r.choice(_UP)
    return r.choice(_UP) + "".join(body)


def _mac_short(r):
    sep = r.choice(":-")
    return sep.join(_r(r, "0123456789ABCDEF" if r.random() < 0.6 else _HEX, 2)
                    for _ in range(r.choice([3, 4, 5])))


def _ipv6_triple_colon(r):
    head = r.choice(["2001:db8", "fd00", "fe80", "2a02:" + _r(r, _HEX, 4)])
    return f"{head}:::{format(r.randint(1, 0xFFFF), 'x')}"


def _ipv4_bad_octet(r):
    octets = [str(r.randint(0, 255)) for _ in range(4)]
    for i in r.sample(range(4), r.randint(1, 2)):
        octets[i] = str(r.randint(256, 999))
    return ".".join(octets)


# --- D-51h (v3 coverage report, section 5): look-alikes in OTHER labels'
# slots and shapes v3 never saw unlabelled. Each value is invalid as the
# label whose anchor it follows; the targeted builder pairs it with a real
# value of that label in the same frame.

def _short_number(r):
    """2-3 digits (mostly 3): after VÖEN/FİN/vəsiqə/token words v3 tagged
    them CVV (132 benchmark errors); training had 2-4 of them there."""
    return str(r.randint(10, 99) if r.random() < 0.25 else r.randint(100, 999))


def _not_a_date(value: str) -> bool:
    return not CK.date_valid(value)


def _mac_fragment_dashed(r):
    """3-4 dash-separated groups, mostly digits only (`12-34-56`): a MAC
    prefix or suffix quoted on its own. v3 tagged these DATE (39 errors; 14
    such strings in all of v3's training). Never a real calendar date."""
    while True:
        alphabet = _D if r.random() < 0.7 else "0123456789ABCDEF"
        value = "-".join(_r(r, alphabet, 2) for _ in range(r.choice([3, 3, 4])))
        if _not_a_date(value):
            return value


def _digits_19_not_iccid(r):
    """19 digits that neither an ICCID (it starts `89`) nor a card (an issuer
    prefix at a legal length) can be: the shape tells them apart, not a
    checksum (D-51d). v4.2 fix list: v4.1 masked 19-digit ICCID-shaped
    numbers as VÖEN 23 times and as cards 21 times on shadow-dev."""
    while True:
        value = _r(r, _D, 19)
        if value[:2] != "89" and value[0] != "0" and not CK.card_brand_ok(value):
            return value


def _iban_short_account(r):
    """`AZ` + check digits + a bank code + 10-19 digits: 18-27 characters, an
    account code shaped like an IBAN but shorter than the 28 an Azerbaijani
    IBAN has (v4.2 fix list: v4.1 masked `AA99AAAA9999999999` in 7 PII-free
    shadow documents, 31 times in all; `iban_truncated` stops at 16). D-57
    M1: 30% are exactly that shape, 18 characters."""
    digits = 10 if r.random() < 0.3 else r.randint(11, 19)
    return "AZ" + _r(r, _D, 2) + _r(r, _UP, 4) + _r(r, _D, digits)


# v4.2 fix list (C4 decoy_fin, the `A12B34` dummy after FİN). D-34b dropped
# `fin_6_chars`: a foreign resident's PIN has 5-6 letters and digits, so a
# random 6-character code after FİN must not be taught safe. These are a
# fixed list of patterned dummies (like D-52c's `12:34:56`), never random
# codes; not a policy kind, since none is a valid FIN.
FIN_DUMMIES = ("A12B34", "A1B2C3", "AB12CD", "1A2B3C", "ABC123", "123ABC",
               "X1Y2Z3", "AA11BB")


def _iban_fragment_short(r):
    """`AZ` + check digits + three letters of the bank code (`AZ37NAB`), an
    IBAN quoted only by its beginning. v3 tagged it AZ_FIN (13 errors)."""
    return "AZ" + _r(r, _D, 2) + _r(r, _UP, 3)


def _ipv4_short_over_255(r):
    """One octet of 256-999, the other three single digits (`412.3.7.1`)."""
    octets = [str(r.randint(0, 9)) for _ in range(4)]
    octets[r.randrange(4)] = str(r.randint(256, 999))
    return ".".join(octets)


def _ipv4_over_255_mixed(r):
    """D-56a (2): one octet of 256-999, mostly the first, beside one- and
    two-digit octets, at least one of one digit (`318.15.0.5`). v4.1 learnt
    "one-digit octets mean an IP" and masked these past the octet over 255."""
    while True:
        octets = [str(r.randint(0, 9) if r.random() < 0.6 else r.randint(10, 99)) for _ in range(4)]
        octets[0 if r.random() < 0.6 else r.randrange(4)] = str(r.randint(256, 999))
        if any(len(o) == 1 for o in octets):
            return ".".join(octets)


def _ipv4_three_octets(r):
    """Three octets (`10.4.7`, `99.9.9`): never a calendar date. D-57 M7: 40%
    end in a single digit (`99.99.9`, A5's IPv4 group)."""
    one_digit_end = r.random() < 0.4
    while True:
        parts = [str(r.randint(0, 255) if r.random() < 0.3 else r.randint(0, 99)) for _ in range(3)]
        if one_digit_end:
            parts[2] = str(r.randint(0, 9))
        value = ".".join(parts)
        if _not_a_date(value):
            return value


def _ipv4_placeholder(r):
    """A placeholder or template address: single-digit octets with a
    wildcard (`1.2.3.x`, `9.9.9.*`, `x.x.x.x`), or five single-digit parts.
    A valid single-digit address (`1.2.3.4`) is NOT written: it is a real
    IPv4 shape, and masking it is the privacy-safe side (v3_root_causes 3).

    v4.1 A5 (v3_shadow_shapes.md lead 5: 24 false alarms on 5-part
    `9.9.9.9.9`): the five-part form 40% -> 60% of this kind, not a new kind,
    so IPv4 look-alikes don't grow while the team checks whether they caused
    v4's IPv4 drop (v4.1 task 1, H3)."""
    style = r.random()
    if style < 0.3:
        octets = [str(r.randint(0, 9)) for _ in range(4)]
        wildcard = r.choice("xX*")
        for i in r.sample(range(4), r.choice([1, 1, 2])):
            octets[i] = wildcard
        return ".".join(octets)
    if style < 0.4:
        return r.choice(("x.x.x.x", "X.X.X.X", "*.*.*.*"))
    return ".".join(str(r.randint(0, 9)) for _ in range(5))


def _code_aaa999(r):
    """A project or product code (`KRM482`) where a surname would stand."""
    return _r(r, _UP, 3) + _r(r, _D, 3)


def _id_prefix(r) -> str:
    """D-34d/D-51h: ID-card look-alikes take the same two-letter prefixes as
    real ID cards (`values.az_id_card_number`), so only the length or the
    format tells them apart, never the prefix."""
    if r.random() < 0.4:
        return r.choice(("AA", "AB"))
    while True:
        pair = _r(r, _UP, 2)
        if pair != "AZ":                    # as values.az_id_card_number
            return pair


# Sentence-initial capitalised common nouns: checkpoint 1 masked `Ərizənin`
# ("of the application") and its fragments as GIVENNAME 246 times. None of
# these is a name; test_anchored_decoys.py checks each against every pool.
_NOUNS_GENITIVE = (
    "Ərizənin", "Müraciətin", "Sənədin", "Hesabatın", "Qərarın", "Bildirişin",
    "Məktubun", "Sorğunun", "Şikayətin", "Arayışın", "Müqavilənin", "Protokolun",
    "Aktın", "Əmrin", "Sərəncamın", "Tələbin", "İddianın", "Cavabın", "Qeydin",
    "Faylın", "Formanın", "Anketin", "Blankın", "Çıxarışın", "Ödənişin",
    "Qəbzin", "Fakturanın", "Sifarişin", "Layihənin", "Cədvəlin", "Siyahının",
    "Sertifikatın", "Lisenziyanın", "İcazənin", "Vəsatətin", "Təklifin", "Rəyin",
    "Nəticənin", "Yoxlamanın", "Təqdimatın", "Xülasənin", "Əlavənin",
    "Bölmənin", "Səhifənin", "Kitabçanın", "Jurnalın", "Reyestrin",
    "Əsasnamənin", "Məlumatın", "Qaimənin", "Etibarnamənin", "Hesabın",
)
_NOUNS_LOCATIVE = (
    "Ərizədə", "Müraciətdə", "Sənəddə", "Hesabatda", "Qərarda", "Bildirişdə",
    "Məktubda", "Sorğuda", "Şikayətdə", "Arayışda", "Müqavilədə", "Protokolda",
    "Əmrdə", "Sərəncamda", "Cavabda", "Qeyddə", "Faylda", "Formada", "Anketdə",
    "Çıxarışda", "Qəbzdə", "Fakturada", "Layihədə", "Cədvəldə", "Siyahıda",
    "Təklifdə", "Rəydə", "Nəticədə", "Əlavədə", "Bölmədə", "Səhifədə",
    "Jurnalda", "Reyestrdə", "Məlumatda", "Qaimədə", "Etibarnamədə",
)


def _az():
    from .locales import LOCALES
    return LOCALES["az"]


def _city_as_project(r):
    return f"{r.choice(_az().cities)} " + r.choice([
        "layihəsi", "festivalı", "marafonu", "forumu", "sərgisi", "konfransı",
        "turniri", "proqramı", "fondu", "klubu", "yarmarkası", "müsabiqəsi"])


def _surname_in_company(r):
    loc = _az()
    surname = loc.surname_builder(r.choice(loc.surname_stems), r.random() < 0.3, r)
    return f"{surname} {r.choice(['MMC', 'ASC', 'Holdinq', 'və Partnyorlar'])}"


# D-34 (D-33f, `decoy_names_as_org`): a common given name + a shop or trade
# word is a business name ("<name> Market"), not a person. Run B masked it as
# GIVENNAME + SURNAME in a signatory slot.
_SHOP_WORDS = ("Market", "Ərzaq", "Mebel", "Tekstil", "Servis", "Tikinti", "Aptek",
               "Plaza", "Group", "Store", "Kafe", "Gözəllik Salonu", "Avto")


def _givenname_in_company(r):
    loc = _az()
    name = r.choice(loc.first_names_m if r.random() < 0.6 else loc.first_names_f)
    return f"{name} {r.choice(_SHOP_WORDS)}"


# D-34 (D-33f, `foreign_names` brands): a foreign company's one-word brand in a
# slot where a person could stand (`<brand> nümayəndəsi ...`). Run B masked it
# as SURNAME. Brands that are also a surname or a given name (Ford, Siemens,
# Suzuki) are left out, and _foreign_brands() drops any that is in a name or
# place pool, so the lesson is the slot, not an ambiguous word.
# D-36c: brands that also occur in eval/probes/ are left out, so the probes stay an
# independent test (removed by the team; the list is checked against the probes only here).
_FOREIGN_BRANDS = (
    "Toyota", "Samsung", "Huawei", "Lenovo", "Xiaomi", "Nissan", "Hyundai", "Panasonic",
    "Nokia", "Unilever", "Danone", "Ikea", "Volvo", "Scania",
    "Adidas", "Zara", "Canon", "Nikon", "Sony", "Toshiba", "Hitachi", "Fujitsu", "Mazda",
    "Subaru", "Rosneft", "Yandex", "Beko", "Vestel", "Microsoft", "Google", "Oracle", "Cisco", "Intel", "Nvidia", "Amazon",
    "Netflix", "Spotify", "Pepsi", "Nescafe", "Kodak", "Xerox", "Logitech", "Asus", "Acer",
    "Lego", "Nivea", "Novartis", "Sanofi", "Airbus", "Alibaba", "Tencent", "Baidu",
)


@functools.lru_cache(maxsize=None)
def _foreign_brands() -> tuple[str, ...]:
    from .locales import LOCALES
    from .locales import az as AZ
    taken = {s.casefold() for s in AZ.SETTLEMENTS}
    for loc in LOCALES.values():
        taken |= {n.casefold() for n in [*loc.first_names_m, *loc.first_names_f, *loc.cities,
                                         *getattr(loc, "surname_stems", ())]}
    path = Path(AZ._DATA_DIR) / "foreign_names.txt"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            cols = line.split("\t")
            if not line.startswith("#") and len(cols) > 2:
                taken.add(cols[2].casefold())
    return tuple(b for b in _FOREIGN_BRANDS if b.casefold() not in taken)


# D-34 (D-33f, `single_entity`, `fmt_csv_noheader`): emails that are not
# addresses -- a doubled `@`, `@localhost`, no `@` at all. Run B masked them in
# every format; the targeted corpus had none.
_FOLD = str.maketrans("əƏçÇğĞıİöÖşŞüÜ", "aAcCgGiIoOsSuU")
_MAIL_HOSTS = ("mail", "poct", "inbox", "ofis", "corp", "bank", "portal", "info")
_MAIL_TLDS = ("az", "com", "net", "org")


def _email_local(r) -> str:
    loc = _az()
    f = "".join(c for c in r.choice(loc.first_names_m + loc.first_names_f).translate(_FOLD).lower()
                if c.isalnum()) or "ad"
    s = "".join(c for c in loc.surname_builder(r.choice(loc.surname_stems), False, r)
                .translate(_FOLD).lower() if c.isalnum()) or "soyad"
    return r.choice([f"{f}.{s}", f"{f}.{s}{r.randint(10, 99)}", f"{f[0]}.{s}", f"{f}{r.randint(1, 99)}"])


def _email_double_at(r) -> str:
    host = f"{r.choice(_MAIL_HOSTS)}.{r.choice(_MAIL_TLDS)}"
    return r.choice([f"{_email_local(r)}@@{host}", f"{_email_local(r)}@{r.choice(_MAIL_HOSTS)}@{host}"])


def _email_no_at(r) -> str:
    # D-42c: also the hyphenated host form `a.a-a.a`, masked 21 of 21 on shadow-dev
    host = r.choice(_MAIL_HOSTS)
    if r.random() < 0.4:
        host = f"{host}-{r.choice([h for h in _MAIL_HOSTS if h != host])}"
    return f"{_email_local(r)}.{host}.{r.choice(_MAIL_TLDS)}"


def _email_dotless(r) -> str:
    # D-42c: a domain with no dot (`ad.soyad@poctserver`), masked 25 of 30
    return f"{_email_local(r)}@{r.choice(_MAIL_HOSTS)}{r.choice(['server', ''])}"


# D-42c (shadow-dev, D-41d): broken IPv6, JWTs and API keys that Run B
# masked 50-100% of the time in PII-free documents
def _ipv6_non_hex(r) -> str:
    groups = [_r(r, _HEX, 4) for _ in range(8)]
    for i in r.sample(range(8), r.randint(1, 2)):
        g = list(groups[i])
        g[r.randrange(4)] = r.choice("ghijklmnopqrstuvwxyz")
        groups[i] = "".join(g)
    return ":".join(groups)


def _ipv6_two_compressions(r) -> str:
    a = [_r(r, _HEX, r.randint(1, 4)) for _ in range(4)]
    return f"{a[0]}:{a[1]}::{a[2]}::{a[3]}"


def _ipv6_compressed_bad(r) -> str:
    """D-57 M6: a `::`-compressed IPv6 shape that is no address -- a 5-hex
    group, a non-hex letter, 9 groups, or a stray colon at an end. v4.1 masked
    compressed `::` look-alikes in 12 PII-free shadow documents (A5)."""
    head = r.choice([["2001", "db8"], ["fd00"], ["fe80"], ["2" + _r(r, _HEX, 3)], ["fd" + _r(r, _HEX, 2)]])
    tail = [format(r.randint(1, 0xFFFF), "x") for _ in range(r.randint(1, 3))]
    style = r.randrange(4)
    if style == 0:                                  # a group of 5 hex digits
        tail[r.randrange(len(tail))] = format(r.randint(0x10000, 0xFFFFF), "x")
    elif style == 1:                                # a letter outside a-f
        i = r.randrange(len(tail))
        g = list(tail[i].rjust(3, "0"))
        g[r.randrange(len(g))] = r.choice("ghijkmnpqrstuvwxyz")
        tail[i] = "".join(g)
    elif style == 2:                                # 9 groups beside `::`
        tail = [format(r.randint(1, 0xFFFF), "x") for _ in range(9 - len(head))]
    value = ":".join(head) + "::" + ":".join(tail)
    if style == 3:                                  # a stray colon at one end
        value = value + ":" if r.random() < 0.6 else ":" + value
    return value


def _mac_letters_only(r) -> str:
    """D-57 M7: six letter pairs, at least one letter outside A-F, so no MAC
    (`XX:XX:XX:XX:XX:XX`, `AB:CD:EF:GH:IJ:KL`). v4.1 masked letters-only MAC
    shapes in 3 PII-free shadow documents."""
    sep = r.choice(":-")
    if r.random() < 0.3:
        return sep.join([r.choice(["XX", "YY", "ZZ", "XY"])] * 6)
    while True:
        pairs = [_r(r, _UP, 2) for _ in range(6)]
        if any(c not in "ABCDEF" for p in pairs for c in p):
            return sep.join(pairs)


def _voen_nine_digits(r) -> str:
    """D-57 M7: 9 digits, one short of a VÖEN (A5's VÖEN group: 9-digit values
    masked in 7 PII-free shadow documents). Never a leading 0."""
    return str(r.randint(1, 9)) + _r(r, _D, 8)


def _city_in_brand(r) -> str:
    """D-57 S3 (D-2): an organisation or brand name built from a town word
    (`Gəncə Tekstil`), written in quotes; the town inside it stays
    unlabelled. Towns from az_cities.txt (the CITY pool's towns)."""
    return f"{r.choice(_az().cities)} {r.choice(_SHOP_WORDS)}"


def _jwt_two_segments(r) -> str:
    head = base64.urlsafe_b64encode(r.choice([b'{"alg":"HS256","typ":"JWT"}',
                                              b'{"alg":"RS256","typ":"JWT"}'])).decode().rstrip("=")
    body = "eyJ" + _r(r, string.ascii_letters + _D + "_-", r.randint(30, 60))
    return f"{head}.{body}"


def _api_key_short(r) -> str:
    prefix = r.choice(["sk_live_", "sk_test_", "ghp_", "key_", "api_", "AKIA"])
    alphabet = (_UP + _D) if prefix == "AKIA" else (string.ascii_letters + _D)
    return prefix + _r(r, alphabet, r.randint(4, 12))


# D-34f: a public key is not secret and is not a PRIVATE_KEY. (header, DER
# bytes, how the real base64 body starts): Ed25519 and EC P-256 SPKI, RSA-2048
# SPKI and PKCS#1 -- the short blocks Run B masked in 10 of 10 probe documents.
_PUBLIC_KEY_KINDS = (
    ("PUBLIC KEY", 44, "MCowBQYDK2VwAyEA", 0.3),
    ("PUBLIC KEY", 91, "MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE", 0.3),
    ("PUBLIC KEY", 294, "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA", 0.3),
    ("RSA PUBLIC KEY", 270, "MIIBCgKCAQEA", 0.1),
)


# D-36a: an OpenSSH public-key line, as in `authorized_keys`: the key type, the
# base64 blob (which starts with the encoded type name) and sometimes a comment
_SSH_PUBLIC_KINDS = (("ssh-ed25519", "AAAAC3NzaC1lZDI1NTE5", 51),          # 68 base64 characters
                     ("ssh-rsa", "AAAAB3NzaC1yc2E", 279),                # RSA-2048, 372
                     ("ecdsa-sha2-nistp256", "AAAAE2VjZHNhLXNoYTItbmlzdHAyNTY", 104))  # 140
_SSH_COMMENTS = ("deploy@ci", "admin@server", "backup@host", "user@laptop", "git@repo")


def _public_key_ssh(r) -> str:
    kind, lead, n = r.choice(_SSH_PUBLIC_KINDS)
    blob = lead + base64.b64encode(bytes(r.getrandbits(8) for _ in range(n))).decode("ascii")[len(lead):]
    return f"{kind} {blob}" + (f" {r.choice(_SSH_COMMENTS)}" if r.random() < 0.4 else "")


# D-41a: a sequential or repeated 5-digit dummy after a CVV word (`CVV 12345`).
# Five digits are never a CVV, so it is an ordinary look-alike, not a D-2
# policy kind; the probes' `decoy_cvv` still had Run B mask these. Benchmark
# values are left out unless D-2 allows them (`12345` is allowed).
_SEQ5 = ("12345", "54321", "11111", "00000", "99999", "98765", "55555", "12121", "67890")


@functools.lru_cache(maxsize=None)
def _seq5_pool() -> tuple[str, ...]:
    planted, allow = benchmark_planted_values(), policy_allowlist()
    return tuple(v for v in _SEQ5 if v not in planted or v in allow)


def _public_key(r, kind: tuple | None = None) -> str:
    header, n, lead, _w = kind or r.choices(_PUBLIC_KEY_KINDS,
                                            weights=[k[3] for k in _PUBLIC_KEY_KINDS])[0]
    body = base64.b64encode(bytes(r.getrandbits(8) for _ in range(n))).decode("ascii")
    body = lead + body[len(lead):]
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return "\n".join([f"-----BEGIN {header}-----", *lines, f"-----END {header}-----"])


ED25519_PUBLIC_LEAD = _PUBLIC_KEY_KINDS[0][2]


def public_key_ed25519(r) -> str:
    """D-51h: an Ed25519 public-key block (`MCowBQYDK2VwAyEA...`, 60 base64
    characters), the short look-alike the targeted builder sets beside short
    Ed25519 PRIVATE keys (`MC4CAQAw...`), at least three private per public."""
    return _public_key(r, _PUBLIC_KEY_KINDS[0])


@functools.lru_cache(maxsize=None)
def _person_street_stems() -> tuple[str, ...]:
    # street stems that are a person's name (`Nizami`, `Zakir Nəcəfov`), the
    # ones that can double as a book or lecture topic
    return tuple(s for s in _az().street_stems
                 if not re.search(r"\d|\.", s) and s[:1].isupper())


def _street_as_topic(r):
    return f"{r.choice(_person_street_stems())} haqqında " \
           f"{r.choice(['kitab', 'mühazirə', 'sənədli film', 'məqalə'])}"


# -- the catalogue -------------------------------------------------------------

_CVV = ("CVV kodu {v}", "CVV: {v}", "kartın CVV kodu {v}", "CVC {v}",
        "CVV2 kodu {v}", "təhlükəsizlik kodu {v}")
_TIME = ("saat {v}", "görüş vaxtı {v}", "başlama vaxtı: {v}", "saat {v} radələrində")
# "yaşı {v} kimi qeyd olunub" is gone: it carries its own verb, and the generic
# frame it is written into adds another (`yaşı 47 kimi qeyd olunub tapılıb`,
# P4-2 round 2: 9 of 5,000 documents)
_AGE = ("yaşı {v}", "yaş: {v}", "{v} yaşında")
_DATE = ("tarix: {v}", "{v} tarixində", "doğum tarixi {v}",
         "müqavilənin imzalanma tarixi {v}")
_ZIP = ("poçt indeksi {v}", "indeks: {v}", "ZIP {v}")
_FIN = ("FİN kodu {v}", "FİN: {v}", "şəxsiyyət vəsiqəsinin FİN kodu {v}")
_VOEN = ("VÖEN {v}", "VÖEN: {v}", "VÖEN nömrəsi {v}")
_PASSPORT = ("pasport nömrəsi {v}", "pasport: {v}", "xarici pasportun nömrəsi {v}")
# D-34d: the generic `sənədin nömrəsi` / `vəsiqə nömrəsi` before both labels
_ID = ("şəxsiyyət vəsiqəsinin nömrəsi {v}", "vəsiqə nömrəsi {v}", "şəxsiyyət vəsiqəsi: {v}",
       "sənədin nömrəsi {v}")
_LICENCE = ("sürücülük vəsiqəsinin nömrəsi {v}", "sürücülük vəsiqəsi: {v}",
            "vəsiqə nömrəsi {v}", "sənədin nömrəsi {v}")
_IPV4 = ("IP ünvanı {v}", "server IP: {v}", "mənbə IP {v}")
_IPV6 = ("IPv6 ünvanı {v}", "IPv6: {v}")
_MAC = ("MAC ünvanı {v}", "cihazın MAC ünvanı {v}", "MAC: {v}")
_CARD = ("kart nömrəsi {v}", "bank kartının nömrəsi {v}", "kart: {v}")
_ICCID = ("ICCID {v}", "SIM kartın ICCID nömrəsi {v}")
_IBAN = ("IBAN {v}", "hesab nömrəsi (IBAN) {v}")
_EMAIL = ("e-poçt ünvanı {v}", "e-poçt: {v}", "email: {v}", "elektron poçt {v}")

ANCHORED_DECOYS: dict[str, list[DecoyKind]] = {
    "CARD_SECURITY_CODE": [
        DecoyKind("cvv_5_digits", "CARD_SECURITY_CODE", lambda r: _r(r, _D, 5), _CVV),
        DecoyKind("cvv_sequential_5", "CARD_SECURITY_CODE", lambda r: r.choice(_seq5_pool()), _CVV),
        # D-57 M5: mostly two digits (A5's CVV group: `99`)
        DecoyKind("cvv_1_2_digits", "CARD_SECURITY_CODE",
                  lambda r: _r(r, _D, 2) if r.random() < 0.8 else _r(r, _D, 1), _CVV),
        DecoyKind("cvv_letters", "CARD_SECURITY_CODE", lambda r: r.choice([
            _r(r, _D, 2) + r.choice(string.ascii_lowercase), _r(r, _UP, 3),
            r.choice(_D) + r.choice(_UP) + r.choice(_D)]), _CVV),
        # D-30b: a dash is a real CVV now (`12-3`, checksums._CVV_RE); only
        # a slash or a dot makes the separator look-alike
        DecoyKind("cvv_separator", "CARD_SECURITY_CODE", lambda r: r.choice([
            f"{_r(r, _D, 2)}/{r.choice(_D)}", f"{r.choice(_D)}/{_r(r, _D, 2)}",
            f"{_r(r, _D, 2)}.{r.choice(_D)}"]), _CVV),
        DecoyKind("policy_sequential", "CARD_SECURITY_CODE",
                  lambda r: r.choice(_allowlisted(CK.card_security_code_valid)),
                  _CVV, policy=True),
        # D-51h: a room, office or door number named a `kod` by the words
        # around it (`otağın kodu 412`, `412 qapı kodu`; D-51h native review C:
        # not `otaq 412 kodu`). v3 tagged 47 such
        # benchmark distractors CVV; training had no room number before kodu
        DecoyKind("room_code", "CARD_SECURITY_CODE", lambda r: str(r.randint(100, 999)),
                  ("otağın kodu {v}", "{v} kodlu otaq", "kabinetin kodu {v}"), contextual=True),
        DecoyKind("door_code", "CARD_SECURITY_CODE",
                  lambda r: str(r.randint(100, 999) if r.random() < 0.6 else r.randint(1000, 9999)),
                  ("{v} qapı kodu", "qapının kodu {v}", "giriş qapısının kodu {v}"), contextual=True),
    ],
    "TIME": [
        DecoyKind("time_bad_hour", "TIME", _time_bad_hour, _TIME),
        DecoyKind("time_bad_minute", "TIME", _time_bad_minute, _TIME),
        DecoyKind("time_3_digit_minutes", "TIME",
                  lambda r: f"{r.randint(0, 23):02d}:{r.randint(100, 999)}", _TIME),
        DecoyKind("policy_version_time", "TIME",
                  lambda r: f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}",
                  ("{v} versiyası", "proqramın {v} versiyası"), policy=True),
        DecoyKind("policy_sequential_time", "TIME", _sequential_time, _TIME, policy=True),
        DecoyKind("time_hour_near", "TIME", _time_hour_near, _TIME),
        DecoyKind("time_minute_near", "TIME", _time_minute_near, _TIME),
    ],
    "AGE": [
        DecoyKind("age_negative", "AGE", lambda r: f"-{r.randint(1, 99)}", _AGE),
        DecoyKind("age_implausible", "AGE", lambda r: str(r.randint(131, 1500)), _AGE),
        DecoyKind("age_currency_amount", "AGE",
                  lambda r: f"{r.randint(5, 500)} {r.choice(['AZN', 'manat', '₼'])}",
                  ("yaş həddi üzrə ödəniş {v}", "yaşı ilə bağlı güzəşt məbləği {v}",
                   "yaş qrupu üçün haqq: {v}")),
    ],
    "DATE": [
        DecoyKind("date_impossible_day", "DATE", _date_impossible_day, _DATE),
        DecoyKind("date_bad_month", "DATE", _date_bad_month, _DATE),
        DecoyKind("date_iso_out_of_range", "DATE", _date_iso_bad, _DATE),
        DecoyKind("date_feb_invalid", "DATE", _date_feb_invalid, _DATE),
        DecoyKind("date_month_near", "DATE", _date_month_near, _DATE),
        DecoyKind("date_clause_number", "DATE",
                  lambda r: f"{r.randint(1, 30)}.{r.randint(1, 20)}.{r.randint(1, 9)}",
                  ("müqavilə bəndi {v}", "müqavilənin {v} bəndi", "{v} maddəsi", "maddə {v}")),
        DecoyKind("date_version_string", "DATE",
                  lambda r: f"v{r.randint(1, 12)}.{r.randint(0, 20)}.{r.randint(0, 99)}",
                  ("versiya {v}", "proqram versiyası {v}")),
    ],
    "ZIPCODE": [
        # not 6 or 7 digits: AZ + 6 digits is a driver licence and AZ + 7 an
        # ID card (any two letters, D-51h), real values in our schema
        DecoyKind("zip_wrong_length", "ZIPCODE",
                  lambda r: "AZ" + _r(r, _D, r.choice([1, 2, 3, 5])), _ZIP),
        # coverage report section 5, item 7: a bare 2-digit number after a ZIP
        # word, which v3 tagged BUILDINGNUM (17 benchmark errors); an
        # Azerbaijani ZIP has 4 digits
        DecoyKind("zip_two_digits", "ZIPCODE", lambda r: str(r.randint(10, 99)), _ZIP),
        DecoyKind("zip_shape_in_iban_field", "ZIPCODE",
                  lambda r: "AZ" + _r(r, _D, 4),
                  ("IBAN: {v}", "IBAN sahəsində {v}"), contextual=True),
        # D-30b: a ZIP-shaped code that the words around it make a product,
        # batch or warehouse code (Run B masked such codes 64 times)
        DecoyKind("zip_shape_as_code", "ZIPCODE",
                  lambda r: "AZ" + _r(r, _D, 4),
                  ("{v} model kodu", "anbar kodu {v}", "partiya kodu {v}",
                   "məhsulun seriya kodu {v}", "{v} kateqoriyalı mal"), contextual=True),
    ],
    # `fin_6_chars` was dropped (D-34b): a foreign resident's PIN has 5-6
    # letters and digits (State Migration Service), so a 6-character code
    # after FİN must not be taught as safe to leave unmasked.
    "AZ_FIN": [
        DecoyKind("fin_8_9_chars", "AZ_FIN", _fin_8_9_chars, _FIN),
        # `fin_with_i_or_o` was dropped (D-33c): that FINs exclude I and O is
        # not established, so a 7-character FIN with one may be real.
        DecoyKind("fin_with_hyphen", "AZ_FIN", _fin_hyphen, _FIN),
        # D-51h: 2-3 digits after the FIN word (v3: CVV, 31 benchmark errors)
        DecoyKind("fin_short_number", "AZ_FIN", _short_number, _FIN),
        DecoyKind("fin_dummy_pattern", "AZ_FIN", lambda r: r.choice(FIN_DUMMIES), _FIN),
    ],
    "AZ_VOEN": [
        DecoyKind("voen_wrong_length", "AZ_VOEN",
                  lambda r: _r(r, _D, r.choice([8, 9, 11, 12])), _VOEN),
        DecoyKind("voen_letters_in_digits", "AZ_VOEN", _voen_letters, _VOEN),
        DecoyKind("order_number", "AZ_VOEN", lambda r: _digits(r, 7, 8),
                  ("sifariş nömrəsi {v}", "sifariş №{v}")),
        # D-51h: 2-3 digits after VÖEN / Vergi nömrəsi (v3: CVV, 60 errors)
        DecoyKind("voen_short_number", "AZ_VOEN", _short_number,
                  _VOEN + ("vergi nömrəsi {v}",)),
        DecoyKind("voen_nine_digits", "AZ_VOEN", _voen_nine_digits, _VOEN),       # D-57 M7
    ],
    "AZ_PASSPORT_NUMBER": [
        DecoyKind("passport_wrong_length", "AZ_PASSPORT_NUMBER",
                  lambda r: r.choice(_UP) + _r(r, _D, r.choice([5, 6, 7, 9, 10])), _PASSPORT),
        DecoyKind("passport_letter_in_digits", "AZ_PASSPORT_NUMBER",
                  _passport_letter_inside, _PASSPORT),
        DecoyKind("policy_passport_dummy", "AZ_PASSPORT_NUMBER",
                  lambda r: r.choice(_allowlisted(CK.az_passport_valid)),
                  _PASSPORT, policy=True),
    ],
    "AZ_ID_CARD_NUMBER": [
        # D-51h: the prefixes real ID cards take (`_id_prefix`), so the
        # length or the hyphen is the only difference
        DecoyKind("id_card_too_short", "AZ_ID_CARD_NUMBER",
                  lambda r: _id_prefix(r) + _digits(r, 2, 5), _ID),
        DecoyKind("id_card_hyphen", "AZ_ID_CARD_NUMBER",
                  lambda r: _id_prefix(r) + "-" + _digits(r, 2, 5), _ID),
        DecoyKind("id_card_too_long", "AZ_ID_CARD_NUMBER",
                  lambda r: _id_prefix(r) + _digits(r, 8, 9), _ID),
        # D-51h: 2-3 digits after vəsiqə words (v3: CVV, 21 errors)
        DecoyKind("id_card_short_number", "AZ_ID_CARD_NUMBER", _short_number, _ID),
    ],
    "AZ_DRIVER_LICENSE_NUMBER": [
        DecoyKind("licence_too_short", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: _r(r, _UP, 2) + _digits(r, 3, 5), _LICENCE),
        DecoyKind("licence_hyphen", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: _r(r, _UP, 2) + "-" + _digits(r, 2, 5), _LICENCE),
        # non-PII internal ids: checkpoint 1 read REF905784 / CMP-2431 /
        # ARX-3353 as driver licences. D-34 (D-33f, `single_entity`): Run B
        # read filler codes of any 3 letters + 6 digits as licences, not
        # only REF ones
        DecoyKind("internal_reference", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: ("REF" if r.random() < 0.3 else _r(r, _UP, 3)) + _r(r, _D, 6),
                  ("daxili istinad {v}", "istinad nömrəsi {v}")),
        DecoyKind("campaign_code", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: r.choice([f"CMP-{_r(r, _D, 4)}",
                                      f"CMP-{r.randint(2021, 2027)}-{_r(r, _D, 3)}"]),
                  ("kampaniya kodu {v}", "kampaniya {v}")),
        # v4.2 fix list (A5): three letters + 6 digits in the licence slot
        # itself, beside a real licence (two letters + 6). v4.1 masked
        # `AAA999999` in 9 PII-free shadow documents and 39 times in all;
        # `internal_reference` writes the shape only after reference words.
        DecoyKind("licence_three_letters", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: _r(r, _UP, 3) + _r(r, _D, 6), _LICENCE),
        DecoyKind("archive_folder", "AZ_DRIVER_LICENSE_NUMBER",
                  lambda r: "ARX-" + _digits(r, 4, 6),
                  ("arxiv qovluğu {v}", "arxiv qovluğunun nömrəsi {v}")),
    ],
    "IPV4_ADDRESS": [
        DecoyKind("ipv4_octet_over_255", "IPV4_ADDRESS", _ipv4_bad_octet, _IPV4),
        # D-51h: the shapes v3 masked after IP words (47 errors), 0 in training
        DecoyKind("ipv4_short_over_255", "IPV4_ADDRESS", _ipv4_short_over_255, _IPV4),
        DecoyKind("ipv4_three_octets", "IPV4_ADDRESS", _ipv4_three_octets, _IPV4),
        DecoyKind("ipv4_over_255_mixed", "IPV4_ADDRESS", _ipv4_over_255_mixed, _IPV4),
        DecoyKind("policy_sequential_ipv4", "IPV4_ADDRESS", lambda r: r.choice(SEQUENTIAL_IPV4),
                  _IPV4, policy=True),
        DecoyKind("ipv4_placeholder", "IPV4_ADDRESS", _ipv4_placeholder,
                  _IPV4 + ("IP ünvanı şablonu {v}",)),
    ],
    "IPV6_ADDRESS": [
        DecoyKind("ipv6_triple_colon", "IPV6_ADDRESS", _ipv6_triple_colon, _IPV6),
        DecoyKind("ipv6_non_hex", "IPV6_ADDRESS", _ipv6_non_hex, _IPV6),
        DecoyKind("ipv6_two_compressions", "IPV6_ADDRESS", _ipv6_two_compressions, _IPV6),
        DecoyKind("ipv6_compressed_bad", "IPV6_ADDRESS", _ipv6_compressed_bad, _IPV6),   # D-57 M6
    ],
    "MAC_ADDRESS": [
        DecoyKind("mac_3_to_5_groups", "MAC_ADDRESS", _mac_short, _MAC),
        # D-51h: `12-34-56`, which v3 tagged DATE
        DecoyKind("mac_fragment_dashed", "MAC_ADDRESS", _mac_fragment_dashed, _MAC),
        DecoyKind("mac_letters_only", "MAC_ADDRESS", _mac_letters_only, _MAC),           # D-57 M7
    ],
    "PAYMENT_CARD_NUMBER": [
        # D-51d: `card_luhn_invalid` and `tracking_code_15_16` (checksum-only)
        # are gone; a card of the wrong length shows it by its length
        DecoyKind("card_wrong_length", "PAYMENT_CARD_NUMBER", _card_wrong_length, _CARD),
        DecoyKind("policy_test_card", "PAYMENT_CARD_NUMBER",
                  lambda r: r.choice(_allowlisted(
                      lambda v: CK.luhn_valid(v) and CK.card_brand_ok(v))),
                  _CARD, policy=True),
    ],
    "ICCID": [
        DecoyKind("iccid_short_prefix", "ICCID", lambda r: "89" + _digits(r, 0, 6), _ICCID),
        # v4.2 fix list: 19 digits without the `89` an ICCID starts with,
        # after ICCID words and beside a real one (the shape decides)
        DecoyKind("iccid_wrong_prefix", "ICCID", _digits_19_not_iccid, _ICCID),
        DecoyKind("reference_19_digits", "ICCID", _digits_19_not_iccid,
                  ("əməliyyat nömrəsi {v}", "izləmə nömrəsi {v}", "tranzaksiyanın ID-si {v}",
                   "qəbzin nömrəsi {v}")),
    ],
    "IBAN": [
        DecoyKind("iban_truncated", "IBAN",
                  lambda r: "AZ" + _r(r, _D, 2) + _r(r, _UP, 4) + _digits(r, 0, 8), _IBAN),
        # D-51h: `AZ37NAB`, an IBAN quoted by its beginning (v3: AZ_FIN)
        DecoyKind("iban_fragment_short", "IBAN", _iban_fragment_short, _IBAN),
        DecoyKind("iban_short_account", "IBAN", _iban_short_account, _IBAN),
        # D-55b (1): a bare two-letter country code (v4.1 masked a bare `AA`
        # as IBAN in 5 PII-free shadow documents)
        DecoyKind("iban_country_code", "IBAN", lambda r: "AZ" if r.random() < 0.8 else r.choice(["TR", "GE"]),
                  ("IBAN-ın ölkə kodu {v}", "hesabın ölkə kodu {v}", "ölkə kodu {v}")),
    ],
    "EMAIL": [
        DecoyKind("email_double_at", "EMAIL", _email_double_at, _EMAIL),
        DecoyKind("email_localhost", "EMAIL", lambda r: f"{_email_local(r)}@localhost", _EMAIL),
        DecoyKind("email_no_at", "EMAIL", _email_no_at, _EMAIL),
        DecoyKind("email_dotless_domain", "EMAIL", _email_dotless, _EMAIL),
    ],
    "API_KEY": [
        DecoyKind("api_key_short", "API_KEY", _api_key_short,
                  ("API açarı {v}", "api key: {v}", "inteqrasiya açarı {v}")),
        # D-51h: 2-3 digits after API-key words (v3: CVV)
        DecoyKind("api_key_short_number", "API_KEY", _short_number,
                  ("API açarı {v}", "api key: {v}", "inteqrasiya açarı {v}")),
    ],
    "PRIVATE_KEY": [
        DecoyKind("public_key_block", "PRIVATE_KEY", _public_key,
                  ("açıq açar {v}", "public key: {v}", "açıq açarın məzmunu: {v}")),
        DecoyKind("public_key_ssh", "PRIVATE_KEY", _public_key_ssh,
                  ("SSH açıq açarı {v}", "authorized_keys faylına əlavə edilən açar: {v}",
                   "public key: {v}")),
    ],
    # D-34 (D-33f, `contrast_token_key`): a container image digest (Run B split
    # it into IPV6 and ACCESS_TOKEN pieces) and the first characters of a
    # token, which the sentence says are only its beginning
    "ACCESS_TOKEN": [
        DecoyKind("image_digest", "ACCESS_TOKEN", lambda r: "sha256:" + _r(r, _HEX, 64),
                  ("obrazın digest dəyəri {v}", "image digest: {v}", "konteyner obrazının heşi {v}")),
        DecoyKind("token_prefix_only", "ACCESS_TOKEN",
                  lambda r: r.choice(["at_", "tok_", "sess_", "pat_", "oauth_"])
                  + _r(r, string.ascii_letters + _D, r.randint(6, 12)),
                  ("tokenin yalnız əvvəli {v}", "tokenin ilk simvolları: {v}",
                   "qısaldılmış token {v}")),
        DecoyKind("jwt_two_segments", "ACCESS_TOKEN", _jwt_two_segments,
                  ("access token {v}", "JWT {v}", "sessiya tokeni {v}")),
        # D-51h: 2-3 digits after token words (v3: CVV)
        DecoyKind("token_short_number", "ACCESS_TOKEN", _short_number,
                  ("token {v}", "token: {v}", "sessiya tokeni {v}")),
    ],
    "CITY": [
        DecoyKind("policy_city_as_project", "CITY", _city_as_project,
                  ("şəhər {v}", "{v} üzrə hesabat", "{v} çərçivəsində"), policy=True),
        # D-57 S3 (D-2): a quoted organisation or brand built from a town word
        DecoyKind("policy_city_in_brand", "CITY", _city_in_brand,
                  ("«{v}» MMC", "«{v}» şirkəti", "\"{v}\" mağazası"), policy=True),
    ],
    "SURNAME": [
        DecoyKind("policy_surname_in_company", "SURNAME", _surname_in_company,
                  ("{v} ilə müqavilə", "{v} şirkəti", "{v} tərəfindən"), policy=True),
        DecoyKind("policy_foreign_brand", "SURNAME", lambda r: r.choice(_foreign_brands()),
                  ("{v} nümayəndəsi", "{v} şirkəti", "{v} tərəfindən"), policy=True),
        # D-51h: a code (`KRM482`) where a surname would stand (`soyad kimi`)
        DecoyKind("code_in_name_slot", "SURNAME", _code_aaa999,
                  ("{v} kodu", "layihə kodu {v}", "məhsul kodu {v}")),
    ],
    "STREET": [
        DecoyKind("policy_street_as_topic", "STREET", _street_as_topic,
                  ("küçə {v}", "{v} nəşr olunub"), policy=True),
    ],
    "GIVENNAME": [
        DecoyKind("policy_givenname_in_company", "GIVENNAME", _givenname_in_company,
                  ("{v} ilə müqavilə", "{v} şirkəti", "{v} tərəfindən"), policy=True),
        DecoyKind("sentence_initial_genitive", "GIVENNAME",
                  lambda r: r.choice(_NOUNS_GENITIVE),
                  ("{v} surəti", "{v} nömrəsi", "{v} mətni", "{v} statusu")),
        DecoyKind("sentence_initial_locative", "GIVENNAME",
                  lambda r: r.choice(_NOUNS_LOCATIVE),
                  ("{v} qeyd olunub", "{v} göstərilib", "{v} əlavə edilib")),
    ],
    # Room, floor and office numbers: checkpoint 1 masked `otaq NNN` as
    # BUILDINGNUM 226 times. `blok` is deliberately absent: anchors/az.py
    # counts it as a building anchor.
    "BUILDINGNUM": [
        DecoyKind("room_number", "BUILDINGNUM", lambda r: str(r.randint(1, 999)),
                  ("otaq {v}", "{v} nömrəli otaq", "otaq №{v}"), contextual=True),
        DecoyKind("floor_number", "BUILDINGNUM", lambda r: str(r.randint(1, 30)),
                  ("mərtəbə {v}", "mərtəbə: {v}"), contextual=True),
        DecoyKind("office_number", "BUILDINGNUM", lambda r: str(r.randint(1, 999)),
                  ("kabinet {v}", "{v} saylı kabinet"), contextual=True),
    ],
}

# The genuine anchor phrases of each label: what a VALID value is written
# beside. The ordinary decoy kinds use these same phrases on purpose, so a
# decoy pair (P2-4) can show one anchor with a valid value and with a decoy.
LABEL_ANCHOR_PHRASES: dict[str, tuple[str, ...]] = {
    "CARD_SECURITY_CODE": _CVV, "TIME": _TIME, "AGE": _AGE, "DATE": _DATE,
    "ZIPCODE": _ZIP, "AZ_FIN": _FIN, "AZ_VOEN": _VOEN,
    "AZ_PASSPORT_NUMBER": _PASSPORT, "AZ_ID_CARD_NUMBER": _ID,
    "AZ_DRIVER_LICENSE_NUMBER": _LICENCE, "IPV4_ADDRESS": _IPV4,
    "IPV6_ADDRESS": _IPV6, "MAC_ADDRESS": _MAC, "PAYMENT_CARD_NUMBER": _CARD,
    "ICCID": _ICCID, "IBAN": _IBAN, "EMAIL": _EMAIL,
    "BUILDINGNUM": ("bina {v}", "bina nömrəsi {v}", "ev {v}"),
}

ALL_DECOY_KINDS: dict[str, DecoyKind] = {
    k.kind: k for kinds in ANCHORED_DECOYS.values() for k in kinds}

# P2-4d (RC9): a given name used as the ordinary word it also is -- `dəniz`
# (sea), `bahar` (spring), `fidan` (sapling). Written only from the homograph
# list in the targeted builder, never planted by `make_decoy`, so it is not an
# anchored kind and not among `active_decoy_kinds()`. Contextual: the word is
# not invalid as a name, the sentence makes it a noun (R4 by meaning).
HOMOGRAPH_NOUN = DecoyKind("homograph_noun", "GIVENNAME", lambda r: "", (), contextual=True)
ALL_DECOY_KINDS[HOMOGRAPH_NOUN.kind] = HOMOGRAPH_NOUN
# D-34 (D-33f, `villages`): the control words Run B masked, written only by the
# targeted builder's `village` documents, like `homograph_noun`. A
# sentence-initial noun or adjective describing villages (`Ucqar kəndlərdə`,
# `Bağ evi`, `Talışdilli`) resembles CITY; a kinship noun with a possessive
# (`Xalam`, `Əmim`) resembles GIVENNAME.
VILLAGE_WORD = DecoyKind("village_descriptor", "CITY", lambda r: "", (), contextual=True)
KINSHIP_NOUN = DecoyKind("kinship_possessive", "GIVENNAME", lambda r: "", (), contextual=True)
ALL_DECOY_KINDS[VILLAGE_WORD.kind] = VILLAGE_WORD
ALL_DECOY_KINDS[KINSHIP_NOUN.kind] = KINSHIP_NOUN
# D-51h (probe families `names_list_lines`, `names_after_role`, the
# signature lines): non-names in the D-39b name frames, written only by the
# targeted builder's `namelist` documents -- a list line that is a
# department, organisation, position or document title; a capitalised
# department or organisation right after a lowercase role word; a signature
# with only a title. v3 masked 25-50% of such controls: every list line and
# every word after a role word it had seen was a name.
NAMELIST_CONTROL = DecoyKind("namelist_control", "GIVENNAME", lambda r: "", (), contextual=True)
ROLE_WORD_CONTROL = DecoyKind("role_word_control", "GIVENNAME", lambda r: "", (), contextual=True)
SIGNATURE_TITLE = DecoyKind("signature_title_only", "GIVENNAME", lambda r: "", (), contextual=True)
for _k in (NAMELIST_CONTROL, ROLE_WORD_CONTROL, SIGNATURE_TITLE):
    ALL_DECOY_KINDS[_k.kind] = _k
# v3_shadow_shapes.md lead 1 (15 Oct): a chat or log line stamp
# (`[14:05:22] Operator:`, `14:05:22 - Agent:`, `[14:05:22] INFO`) is no TIME
# (D-51f; v4_clean R2), written only by the targeted builder's `time_seconds`
# documents beside a labelled time with seconds. Contextual: the clock time is
# valid, the line position makes it a stamp.
TIME_LINE_STAMP = DecoyKind("time_line_stamp", "TIME", lambda r: "", (), contextual=True)
ALL_DECOY_KINDS[TIME_LINE_STAMP.kind] = TIME_LINE_STAMP
# v4.1 (v3_shadow_shapes.md lead 5, A5): a private-key block whose body is a
# placeholder or was redacted (`-----BEGIN PRIVATE KEY-----` / `[REDACTED]` /
# `-----END PRIVATE KEY-----`) holds no key. v3 masked the header words of
# such blocks as PRIVATE_KEY about 80 times on shadow-dev; training had none.
# Written only by the targeted builder's `key_placeholder` documents.
KEY_PLACEHOLDER = DecoyKind("private_key_placeholder", "PRIVATE_KEY", lambda r: "", (), contextual=True)
ALL_DECOY_KINDS[KEY_PLACEHOLDER.kind] = KEY_PLACEHOLDER
# v4.1 A5 (v3_shadow_shapes.md lead 5 and part 3): a role or heading word that
# opens a line (`Operator: ...`, `Qeyd: ...`), beside lines opened by a real
# given name. v3 masked capitalised words at a line start as GIVENNAME (41 of
# its 110 GIVENNAME false alarms) and missed 8 of 15 real given names there.
# Written only by the targeted builder's `namelist` documents (`line_start`).
LINE_START_CONTROL = DecoyKind("line_start_control", "GIVENNAME", lambda r: "", (), contextual=True)
ALL_DECOY_KINDS[LINE_START_CONTROL.kind] = LINE_START_CONTROL
# D-57 (final v4.2 fix list), written only by the targeted builder:
#   S1  a 2-digit number in a real age's sentence frame that the words around
#       it make a score, a queue number, months of work, a pulse or a weight;
#   S2  an ALL-CAPS heading word on its own line beside ALL-CAPS cities and
#       names (`ƏRİZƏ`, `ARAYIŞ`), in no name or place pool;
#   item 5 a place-like word in a PII-free text about geography, routes or
#       regions (a river, a mountain, a country, a corridor), in no city,
#       settlement or given-name pool (one such shadow document had 15 CITY
#       false alarms).
AGE_SHAPED = DecoyKind("age_shaped_number", "AGE", lambda r: "", (), contextual=True)
CAPS_HEADING = DecoyKind("caps_heading_control", "CITY", lambda r: "", (), contextual=True)
PLACE_WORD = DecoyKind("place_word_topic", "CITY", lambda r: "", (), contextual=True)
for _k in (AGE_SHAPED, CAPS_HEADING, PLACE_WORD):
    ALL_DECOY_KINDS[_k.kind] = _k


def _available(kind: DecoyKind) -> bool:
    """A policy kind drawn from the allowlist is off if D-2 leaves it empty."""
    try:
        kind.make(random.Random(0))
        return True
    except IndexError:
        return False


@functools.lru_cache(maxsize=None)
def active_decoy_kinds() -> tuple[DecoyKind, ...]:
    """The kinds decoy planting draws from: the anchored ones."""
    return tuple(k for kinds in ANCHORED_DECOYS.values() for k in kinds if _available(k))


def make_decoy(kind: DecoyKind, rng: random.Random) -> str:
    """A fresh value for `kind`, re-drawn while it equals a value the
    benchmark planted (A2 rule 3) unless D-2 allowlists it."""
    planted, allowed = benchmark_planted_values(), policy_allowlist()
    for _ in range(200):
        value = kind.make(rng)
        if value in allowed:
            return value
        # The guard also fails on shadow values (A2 rule 5), and on the
        # benchmark_v3 values that records.json does not list.
        if value not in planted and not is_forbidden(value):
            return value
    raise RuntimeError(f"{kind.kind}: 200 draws all equal benchmark values")


def plant_decoy(kind: DecoyKind, rng: random.Random) -> PlantedDecoy:
    value = make_decoy(kind, rng)
    phrase = rng.choice(kind.anchors).replace("{v}", value)
    return PlantedDecoy(kind.kind, kind.resembles, value, phrase, kind.policy)


def random_anchored(rng: random.Random) -> PlantedDecoy:
    """One anchored decoy, every active kind equally likely."""
    return plant_decoy(rng.choice(active_decoy_kinds()), rng)


# ===========================================================================
# Declaring planted decoys in the final text (P2-3, C2 field `_decoys`)
# ===========================================================================
#
# A decoy is exempt from the quality gates only where it is DECLARED: a
# `_decoys` span on the record. An undeclared copy of the same string is
# still a leak, which is the rule the translation harness already applies
# (translate.sentinel.decoy_spans). Every gate reads the same spans.

# The label each older, unanchored family imitates: its values must not be
# valid as that label (rule R4, test_decoy_gate.py). None: it imitates no
# label in the taxonomy (a VIN, an ISBN, a redaction marker).
FAMILY_RESEMBLES: dict[str, str | None] = {
    "ORDER_ID": "AZ_ID_CARD_NUMBER", "INVOICE_ID": None, "TRACKING": None,
    "VERSION": None, "UUID": None, "SHA256": "ACCESS_TOKEN",
    "MD5": "ACCESS_TOKEN", "GIT_SHA": "ACCESS_TOKEN", "HEX_BLOB": None,
    "TIMESTAMP": "DATE", "REF_CODE": None, "EMPLOYEE_ID": None, "PORT": None,
    "AMOUNT": None, "SKU": None, "COORDINATES": None, "ERROR_CODE": None,
    "BUILD_HASH": None, "SESSION_COUNT": None, "PERCENT": None,
    "DURATION": None, "CONTAINER_ID": None, "MEM_ADDR": None,
    "LICENSE_KEY_PRODUCT": None,
    "VIN_BAD_CHECKDIGIT": None, "IMEI_BAD_LUHN": "PAYMENT_CARD_NUMBER",
    "TRUNCATED_API_KEY": "API_KEY", "MASKED_CARD": "PAYMENT_CARD_NUMBER",
    "MASKED_EMAIL": "EMAIL", "PARTIAL_PHONE": "TELEPHONENUM", "REDACTED": None,
    "IP_LIKE_VERSION": "IPV4_ADDRESS", "IP_INVALID_OCTET": "IPV4_ADDRESS",
    "MAC_LIKE_HASH": "MAC_ADDRESS", "EMAIL_LIKE_HANDLE": "EMAIL",
    "URL_NO_TOKEN": "URL", "SSN_LIKE_CODE": None, "ISBN": None,
    "DATE_LIKE_ID": "DATE", "PLATE_LIKE_CODE": None, "OBFUSCATED_EMAIL": "EMAIL",
}


def planted_decoys(anchored: list[dict], plain: list[dict],
                   strings: list[str]) -> list[dict]:
    """Everything a brief planted, as {string, value, kind, resembles,
    anchored}. `string` is what the model was given (for an anchored decoy,
    the anchor phrase around the value). Briefs older than P2-3 carried only
    the strings; those get kind "unknown"."""
    out: list[dict] = []
    seen: set[str] = set()
    for d in anchored or []:
        out.append({"string": d["phrase"], "value": d["value"], "kind": d["kind"],
                    "resembles": d["resembles"], "anchored": True})
        seen.add(d["phrase"])
    for d in plain or []:
        out.append({"string": d["value"], "value": d["value"], "kind": d["kind"],
                    "resembles": d.get("resembles"), "anchored": False})
        seen.add(d["value"])
    for s in strings or []:
        if s and s not in seen:
            out.append({"string": s, "value": s, "kind": "unknown",
                        "resembles": None, "anchored": False})
            seen.add(s)
    return out


_TOLERANT_MIN = 8          # letters/digits a needle needs before separators may vary
_SEPARATOR = r"[\s\-.:/]?"


def decoy_occurrences(text: str, needle: str,
                      tolerant: bool = False) -> list[tuple[int, int]]:
    """(start, end) of every standalone occurrence of `needle`, one not glued
    to a letter or digit on either side.

    `tolerant` also finds it with separators added or dropped between its
    characters -- a card regrouped as `4539 5787 6362 1486`, which is how a
    model rewrites a digit run -- but only for needles of 8+ letters/digits,
    where that cannot hit an unrelated string by chance.
    """
    if not needle:
        return []
    patterns = [re.escape(needle)]
    alnum = re.sub(r"[^0-9A-Za-z]", "", needle)
    if tolerant and len(alnum) >= _TOLERANT_MIN:
        patterns.append(_SEPARATOR.join(re.escape(c) for c in alnum))
    found: set[tuple[int, int]] = set()
    for pattern in patterns:
        for m in re.finditer(rf"(?<!\w)(?:{pattern})(?!\w)", text):
            found.add((m.start(), m.end()))
    return sorted(found)


def _az_capitalize(s: str) -> str:
    """Sentence-initial capital, Azerbaijani style: i -> İ, ı -> I."""
    if not s:
        return s
    return {"i": "İ", "ı": "I"}.get(s[0], s[0].upper()) + s[1:]


def _overlaps(a: tuple[int, int], spans) -> bool:
    return any(a[0] < e and s < a[1] for s, e in spans)


def _inside(inner: tuple[int, int], outer: tuple[int, int]) -> bool:
    return outer[0] <= inner[0] and inner[1] <= outer[1]


def locate_decoys(text: str, planted: list[dict],
                  entity_spans=(), planned_values=()) -> list[dict]:
    """The C2 `_decoys` spans for what was planted, as it stands in `text`.

    Mirrors translate.sentinel.decoy_spans: every occurrence, longest planted
    string first, never overlapping a span already claimed. A decoy that
    cannot be found (the model paraphrased it) is simply not declared.

    For an anchored decoy the declared span is the VALUE inside its anchor
    phrase, found through the phrase (also with a sentence-initial capital).
    If the phrase is gone but the value survived on its own, the value is
    declared when it is at least 4 characters long and is not also a planned
    entity value, so a lone `12` or a real planned value is never claimed.

    `planned_values` are the entity values the brief asked for. A decoy never
    covers part of one, with one exception: an anchor phrase that fully
    contains it wins, because the phrase is the context D-2 is about -- the
    planned CITY `Bakı` inside `şəhər Bakı layihəsi` is a project name there.
    """
    planned_occ = [span for v in {p for p in planned_values if p}
                   for span in decoy_occurrences(text, v)]
    claimed = [tuple(s) for s in entity_spans]
    declared: list[dict] = []

    for d in sorted(planted, key=lambda d: len(d["string"]), reverse=True):
        value = d["value"]
        candidates: list[tuple[tuple[int, int], bool]] = []   # (span, via phrase)
        if d["anchored"]:
            # never .lower() here: "İ".lower() is two characters, which would
            # shift every offset after it (`FİN kodu {v}`)
            at = d["string"].find(value)
            for phrase in {d["string"], _az_capitalize(d["string"])}:
                for s, _e in decoy_occurrences(text, phrase):
                    candidates.append(((s + at, s + at + len(value)), True))
            if not candidates and len(value) >= 4 and value not in planned_values:
                candidates = [(span, False) for span in decoy_occurrences(text, value)]
        else:
            candidates = [(span, False) for span in
                          decoy_occurrences(text, value, tolerant=True)]

        for span, via_phrase in sorted(set(candidates)):
            if _overlaps(span, claimed):
                continue
            # A planned value under 4 characters wholly inside a longer decoy
            # is a fragment of it, not the value: the planned AGE `78` inside
            # the hash `2e:78:e1:...` left the hash undeclared, and the leak
            # gate then rejected the document for a MAC inside it. As with a
            # lone `12` above, a short value never claims or blocks a span.
            clashes = [p for p in planned_occ if _overlaps(span, [p])
                       and not (p[1] - p[0] < 4 and _inside(p, span) and span[1] - span[0] > p[1] - p[0])]
            if clashes and not (via_phrase and all(_inside(p, span) for p in clashes)):
                continue
            claimed.append(span)
            declared.append({"start": span[0], "end": span[1], "kind": d["kind"],
                             "resembles": d["resembles"]})

    return sorted(declared, key=lambda d: d["start"])
