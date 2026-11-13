"""Placeholder / famous-value denylist.

The audit of the previous dataset found that a third of generated credit cards
were publicly-known payment-processor test numbers, 55 API keys were the
verbatim AWS documentation key, 152 phone numbers used the US 555 fiction
range, and addresses included the Simpsons' house. Values like these teach a
model to memorise *specific strings* rather than to recognise *structure*, and
they corrupt the Day 8 regex-layer evaluation because most of them appear on
public denylists already.

This module is enforced in both directions: ValueFactory will not emit a
blocked value, and the Validator rejects any example containing one -- so LLM
augmentation cannot reintroduce them either.
"""

from __future__ import annotations

import re

# --- exact strings ---------------------------------------------------------

BLOCKED_EXACT = {
    # payment-processor test cards
    "4242424242424242", "4111111111111111", "5555555555554444",
    "4000000000000002", "378282246310005", "371449635398431",
    "6011111111111117", "5105105105105100", "4012888888881881",
    "30569309025904", "3530111333300000", "5200828282828210",
    "4000056655665556", "2223003122003222", "6200000000000005",
    # cloud / vendor documentation keys
    "AKIAIOSFODNN7EXAMPLE", "AKIAI44QH8DHBEXAMPLE",
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "sk_test_4eC39HqLyjWDarjtT1zdp7dc", "sk_live_4eC39HqLyjWDarjtT1zdp7dc",
    "pk_test_TYooMQauvdEDq54NiTphI7jx",
    "AIzaSyDaGmWKa4JsXZ-HjGw7ISLn_3namBGewQe",
    "ghp_16C7e42F292c6912E7710c838347Ae178B4a",
    "xoxb-123456789012-1234567890123-abcdefghijklmnopqrstuvwx",
    # textbook IBANs (these two accounted for 48 of 53 IBAN mentions before)
    "DE89370400440532013000", "GB29NWBK60161331926819",
    "DE89 3704 0044 0532 0130 00", "GB29 NWBK 6016 1331 9268 19",
    "FR1420041010050500013M02606", "GB82WEST12345698765432",
    # well-known public IPs / hosts
    "8.8.8.8", "8.8.4.4", "1.1.1.1", "1.0.0.1", "9.9.9.9", "208.67.222.222",
    "127.0.0.1", "0.0.0.0", "255.255.255.255", "192.168.1.1", "192.168.0.1",
    "10.0.0.1", "172.16.0.1", "::1", "2001:4860:4860::8888",
    # D-52c: sequential dummy times (negatives.SEQUENTIAL_TIMES), never a real TIME
    "12:34:56", "01:23:45", "10:20:30", "11:11:11", "22:22:22", "12:12:12",
    # D-56a (2): sequential IPv4 placeholders (negatives.SEQUENTIAL_IPV4), never a real IPv4
    "1.2.3.4", "4.3.2.1", "2.3.4.5", "10.20.30.40", "11.22.33.44", "12.34.56.78",
    # placeholder MACs / VINs / IMEIs seen in documentation
    "00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF", "00:1A:2B:3C:4D:5E",
    "AA:BB:CC:DD:EE:FF", "DE:AD:BE:EF:00:00",
    "1HGCM82633A004352", "1HGBH41JXMN109186", "WBAAA1305H2320124",
    "123456789012345", "356938035643809", "490154203237518",
    # placeholder credentials
    "password", "password1", "password123", "Password1", "Password123",
    "P@ssw0rd", "P@ssw0rd123", "passw0rd", "letmein", "changeme", "secret",
    "s3cret", "hunter2", "qwerty", "qwerty123", "admin", "admin123", "root",
    "toor", "test", "test123", "guest", "123456", "12345678", "abc123",
    "SuperSecret123", "supersecret", "topsecret", "welcome1", "iloveyou",
    "monkey", "dragon", "sunshine", "princess", "trustno1",
    # placeholder identities
    "John Doe", "Jane Doe", "John Smith", "Jane Smith", "Joe Bloggs",
    "Max Mustermann", "Erika Mustermann", "Иван Иванов", "Иванов Иван Иванович",
    "Mehmet Yılmaz", "Ali Veli", "Foo Bar", "Test User", "Lorem Ipsum",
    # placeholder emails / domains
    "john.doe@example.com", "jane.doe@example.com", "test@test.com",
    "user@example.com", "admin@example.com", "noreply@example.com",
    "foo@bar.com", "email@example.com",
}
BLOCKED_EXACT_LOWER = {s.lower() for s in BLOCKED_EXACT}

# --- substrings that mark a value as fake ----------------------------------

BLOCKED_SUBSTRINGS = [
    "example.com", "example.org", "example.net", "example.edu",
    "test.com", "localhost", "invalid", "yourdomain", "mydomain",
    "yourcompany", "acme.com", "lorem", "ipsum", "asdf", "qwerty",
    "xxxxxx", "aaaaaa", "111111", "000000", "123456789",
    "changeme", "placeholder", "dummy", "sample", "notreal", "fakemail",
    "EXAMPLE", "YOUR_", "MY_SECRET", "INSERT_", "REPLACE_", "TODO",
]
BLOCKED_SUBSTRINGS_LOWER = [s.lower() for s in BLOCKED_SUBSTRINGS]

# --- pattern-level rules ---------------------------------------------------

# US 555-01xx is the reserved fiction range; +44 7700 900xxx is Ofcom's drama
# range; both are guaranteed never to be real numbers.
_FICTION_PHONE = [
    re.compile(r"\b555[-.\s]?01\d{2}\b"),
    re.compile(r"\(?\d{3}\)?[-.\s]?555[-.\s]?\d{4}"),
    re.compile(r"7700[-.\s]?900\d{3}"),
    re.compile(r"\b(\d)\1{6,}\b"),                 # 1111111, 0000000
    re.compile(r"\b(?:0123456789|1234567890|9876543210)\b"),
]

# Sequential or repeated filler inside a key/secret.
_FILLER = re.compile(
    r"(a1b2c3|abc123|xyz789|1234567890|aBcDeF|deadbeef|cafebabe|0123456789)",
    re.IGNORECASE)

# Pop-culture places and people that leaked into the previous dataset.
_FICTION_WORDS = [
    "evergreen terrace", "springfield", "blackwater", "west elizabeth",
    "arthur morgan", "bruce wayne", "peter parker", "clark kent",
    "tony stark", "luke skywalker", "harry potter", "sherlock holmes",
    "baker street", "hogwarts", "gotham", "metropolis", "wakanda",
    "walter white", "jesse pinkman", "homer simpson", "rick sanchez",
    "john wick", "james bond", "jason bourne", "ellen ripley",
]


# RFC 2606 / 6761 reserved top-level names. The benchmark labels addresses on
# them as EMAIL -- all 52 of its missed EMAILs were `…@synthetic-mailN.invalid`
# -- and P2-4 asks the targeted corpus for them explicitly (`.invalid`,
# `.test`, `.example`, `.local`). The substring rules below would block every
# one ("invalid", "example"), so a reserved-name address is judged on its
# LOCAL part: a placeholder local part is still blocked.
_RESERVED_TLD_EMAIL = re.compile(
    r"^([^@\s]+)@([a-z0-9-]+(?:\.[a-z0-9-]+)*)\.(?:invalid|test|example|local)$", re.I)
_PLACEHOLDER_LOCAL_PARTS = {
    "user", "test", "tester", "admin", "noreply", "no-reply", "email", "mail",
    "foo", "bar", "john.doe", "jane.doe", "example", "sample", "demo",
    "someone", "somebody", "name", "username", "your.name", "yourname",
}


def is_blocked(value: str) -> str | None:
    """Return a reason string if `value` is a known placeholder, else None."""
    if not value:
        return None
    v = value.strip()
    low = v.lower()

    if low in BLOCKED_EXACT_LOWER:
        return "known placeholder value"

    reserved = _RESERVED_TLD_EMAIL.match(v)
    if reserved:
        local, host = reserved.group(1).lower(), reserved.group(2).lower()
        if local in _PLACEHOLDER_LOCAL_PARTS or any(
                frag in part for frag in BLOCKED_SUBSTRINGS_LOWER for part in (local, host)):
            return "placeholder email address"
        return None

    compact = re.sub(r"[\s-]", "", v)
    if compact.lower() in BLOCKED_EXACT_LOWER:
        return "known placeholder value (unformatted)"

    for frag in BLOCKED_SUBSTRINGS_LOWER:
        if frag in low:
            return f"placeholder substring {frag!r}"

    for word in _FICTION_WORDS:
        if word in low:
            return f"fictional entity {word!r}"

    for pat in _FICTION_PHONE:
        if pat.search(v):
            return "reserved/fiction number range"

    if _FILLER.search(v):
        return "keyboard-sequence filler"

    # a value that is a single repeated character is never real
    core = re.sub(r"[\s.:_-]", "", v)
    if len(core) >= 6 and len(set(core)) == 1:
        return "single repeated character"

    return None


_TEXT_PLACEHOLDERS = ("example.com", "lorem ipsum", "akiaiosfodnn7example",
                      "4242424242424242", "4111111111111111")


def text_blocklist_hits(text: str, exempt=()) -> list[str]:
    """Scan a whole document for placeholder markers (used by the Validator).

    `exempt` are declared decoy spans (C2 `_decoys`). The D-2 policy decoys
    include the test cards `4242…` and `4111…` on purpose, planted next to
    their anchor; a marker counts only where it sits outside every declared
    span, so an undeclared copy of the same string is still a hit.
    """
    if not exempt:
        hits = []
        low = text.lower()
        for word in _FICTION_WORDS:
            if word in low:
                hits.append(f"fictional entity {word!r}")
        for frag in _TEXT_PLACEHOLDERS:
            if frag in low:
                hits.append(f"placeholder {frag!r}")
        return hits

    # Positions are taken on `text` itself: `text.lower()` can change the
    # length ("İ" lowers to two characters), which would shift every offset.
    def outside(marker: str) -> bool:
        return any(not any(s <= m.start() and m.end() <= e for s, e in exempt)
                   for m in re.finditer(re.escape(marker), text, re.IGNORECASE))

    return ([f"fictional entity {w!r}" for w in _FICTION_WORDS if outside(w)]
            + [f"placeholder {f!r}" for f in _TEXT_PLACEHOLDERS if outside(f)])


# ---------------------------------------------------------------------------
# Password realism
# ---------------------------------------------------------------------------

PASSWORD_KEYWORDS = ("pass", "secret", "admin", "root", "login", "key",
                     "şifr", "пароль", "parol", "gizli", "секрет")


_PEM_ARMOUR = re.compile(r"-----(?:BEGIN|END) [A-Z0-9 ]+-----")


def secret_material(value: str) -> str:
    """The chosen part of a secret: without PEM armour lines and without the
    documented vendor/format prefix (`values.API_KEY_PREFIXES`,
    `ACCESS_TOKEN_PREFIXES`).

    P2-6 fix 5 (LLM batch 1, 2026-10-03): the keyword share read 21.4%
    against its 12% cap, and every one of the 186 hits was `key` -- 105 in
    `-----BEGIN PRIVATE KEY-----` armour, which every real PEM key carries,
    and 81 in the `key_`/`apikey_` prefixes P2-1 added because the
    benchmark's API keys use them. Neither is a password someone chose; the
    material after them had no keyword at all.
    """
    from .values import ACCESS_TOKEN_PREFIXES, API_KEY_PREFIXES   # lazy: values imports this module
    body = _PEM_ARMOUR.sub(" ", value).strip()
    for prefix in sorted(API_KEY_PREFIXES + ACCESS_TOKEN_PREFIXES, key=len, reverse=True):
        if body.startswith(prefix):
            return body[len(prefix):]
    return body


def has_password_keyword(value: str) -> bool:
    """True if a secret contains a giveaway keyword in its material.

    59% of the previous dataset's passwords did, which trains a keyword
    detector rather than a secret detector. The config caps this share. The
    format around the material (PEM armour, a documented prefix) is not
    checked: see `secret_material`.
    """
    low = secret_material(value).lower()
    return any(k in low for k in PASSWORD_KEYWORDS)
