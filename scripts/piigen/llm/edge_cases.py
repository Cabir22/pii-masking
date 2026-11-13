"""Edge-case catalog transcribed from the (repo-external) PII Edge Case
Specification, taxonomy v2.0.0.

That specification was built, then deliberately removed from this repo on
request (2026-08-19/20 session) -- it still exists as a
PDF the user holds outside the repo. This module is NOT the specification
itself; it is a working transcription of the parts needed to *drive*
generation: which specific case to target per label, and (for cases whose
ground truth is "no entity") the deliberately-wrong value to embed as an
unlabeled decoy.

Every label has exactly two cases picked here for the initial smoke test: one
`positive_valid`-family case (a real, checksum-valid value from `ValueFactory`)
and one contrastive case, preferring `hard_negative`/`invalid_near_miss` where
the spec defines one, falling back to a second positive case for the four
ml_context labels (GIVENNAME/SURNAME/CITY/STREET), which the spec gives no
negative case for.

Cases whose spec status is `blocked_pending_evidence` or `out_of_scope` are
never selected -- the spec's own status vocabulary says not to generate them
(unverified check-digit algorithms, unconfirmed prefix sets).
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from random import Random

from .. import checksums as CK
from ..values import ValueFactory

_HEX = "0123456789abcdef"


@dataclass(frozen=True)
class EdgeCase:
    id: str
    status: str  # positive_valid | positive_format_variant | hard_negative |
                 # invalid_near_miss | ambiguous_requires_anchor
    description: str  # internal/catalog reference -- NOT sent to the model
    scenario: str = ""  # neutral, judgment-free phrasing that IS sent to the
                         # model. Deliberately contains no words like
                         # "invalid"/"wrong"/"do not label": a model handed
                         # that language reliably writes it straight into the
                         # prose ("...lakin format yanlışdır"), which is
                         # exactly the leak the first smoke-test run showed on
                         # 9 of 22 negative-family cases. Falls back to
                         # `description` for positive cases, which don't
                         # carry judgment language to begin with.

    @property
    def prompt_text(self) -> str:
        return self.scenario or self.description


# One or two representative cases per label -- id, status, description --
# transcribed from the Label-Specific Edge Cases tables. Not the full case
# list from the spec (each label has 2-4 there); this is the pair actually
# used to drive the smoke-test generation.
LABEL_CASES: dict[str, list[EdgeCase]] = {
    "API_KEY": [
        EdgeCase("APK-01", "positive_valid",
                 "Stripe-style live key in a quoted config-snippet assignment."),
        EdgeCase("APK-03", "hard_negative",
                 "Random 32-char alphanumeric order id with no recognized "
                 "provider prefix -- format alone cannot distinguish a bare "
                 "high-entropy string from a key without a recognized prefix; "
                 "do not label.",
                 scenario="A random 32-character alphanumeric order-tracking "
                          "id, mentioned in an order-status note."),
    ],
    "ACCESS_TOKEN": [
        EdgeCase("ATK-01", "positive_valid",
                 "An access token, exactly as given (prefixed `at_`/`bearer_`/"
                 "`tok_`, opaque, or JWT: P2-1), in an Authorization header or a "
                 "session note inside a log line."),
        EdgeCase("ATK-02", "invalid_near_miss",
                 "Only 2 of the 3 required dot-separated segments present -- "
                 "not a valid token, do not label.",
                 scenario="A two-segment dot-separated token fragment, "
                          "mentioned in a routine system log line."),
    ],
    "PRIVATE_KEY": [
        EdgeCase("PVK-01", "positive_valid",
                 "PEM envelope, multi-line, inside a config block."),
        EdgeCase("PVK-04", "hard_negative",
                 "An ordinary Azerbaijani code comment inside a config/log "
                 "excerpt that is not a key block -- do not label.",
                 scenario="An ordinary Azerbaijani code comment inside a "
                          "config file excerpt."),
    ],
    "PAYMENT_CARD_NUMBER": [
        EdgeCase("PCN-01", "positive_valid",
                 "Grouped 16-digit Visa-shaped number, Luhn-valid, synthetic only."),
        EdgeCase("PCN-03", "invalid_near_miss",
                 "Luhn check digit wrong by one -- structurally invalid, "
                 "do not label.",
                 scenario="A grouped 16-digit card-shaped number, mentioned "
                          "while describing a payment attempt."),
    ],
    "IBAN": [
        EdgeCase("IBN-01", "positive_valid",
                 "Grouped Azerbaijan IBAN, MOD 97-10 valid, synthetic bank code."),
        EdgeCase("IBN-03", "invalid_near_miss",
                 "MOD 97-10 checksum digit wrong -- structurally invalid, "
                 "do not label.",
                 scenario="A grouped Azerbaijan-IBAN-shaped value, mentioned "
                          "while describing a bank transfer."),
    ],
    "IPV4_ADDRESS": [
        EdgeCase("IP4-01", "positive_valid",
                 "Public-range address in a technical log line."),
        EdgeCase("IP4-04", "hard_negative",
                 "A dotted version number that happens to be format-valid as "
                 "an IPv4 address -- context/register is the only signal; "
                 "do not label.",
                 scenario="A dotted four-part software version number, "
                          "mentioned while describing a release."),
    ],
    "IPV6_ADDRESS": [
        EdgeCase("IP6-01", "positive_valid", "Compressed form."),
        EdgeCase("IP6-03", "invalid_near_miss",
                 "Contains an illegal hex group -- not a valid IPv6 address, "
                 "do not label.",
                 scenario="A colon-hex address-shaped string, mentioned in a "
                          "system configuration note."),
    ],
    "MAC_ADDRESS": [
        EdgeCase("MAC-01", "positive_valid", "Colon-separated form."),
        EdgeCase("MAC-04", "hard_negative",
                 "A hex checksum/hash fragment of the same length and shape "
                 "as a MAC address, framed as a file hash -- do not label.",
                 scenario="A colon-separated hex string given as a file "
                          "checksum in a build log."),
    ],
    "URL": [
        EdgeCase("URL-01", "positive_valid",
                 "Password-reset URL with a token query parameter."),
        EdgeCase("URL-04", "hard_negative",
                 "An ordinary public marketing URL with no credential-bearing "
                 "parameter -- not sensitive, do not label.",
                 scenario="An ordinary public marketing-page URL, mentioned "
                          "while pointing someone to a news page."),
    ],
    "ICCID": [
        EdgeCase("ICC-01", "positive_valid", "89-prefixed 20-digit form, Luhn-valid."),
        EdgeCase("ICC-02", "invalid_near_miss",
                 "Luhn check digit wrong -- structurally invalid, do not label.",
                 scenario="A 20-digit SIM-card-shaped number, mentioned "
                          "while describing a SIM card."),
    ],
    "EMAIL": [
        EdgeCase("EML-01", "positive_valid", "Corporate-style domain, dotted local part."),
        EdgeCase("EML-04", "hard_negative",
                 "A social-media @-mention, not an email address -- do not label.",
                 scenario="A social-media @-mention of a username, in a "
                          "post about tagging someone."),
    ],
    "AZ_FIN": [
        EdgeCase("FIN-01", "positive_valid", "7-char value from the no-I/O alphabet."),
        EdgeCase("FIN-03", "hard_negative",
                 "A 7-char Git short SHA that happens to be format-valid as "
                 "AZ_FIN (uppercased, no I/O) -- context/register is the only "
                 "signal, framed as a commit reference; do not label.",
                 scenario="A 7-character commit hash, mentioned while "
                          "describing a code change."),
    ],
    "AZ_ID_CARD_NUMBER": [
        EdgeCase("IDC-01", "positive_valid", "AA-prefixed citizen form."),
        EdgeCase("IDC-03", "invalid_near_miss",
                 "Prefix 'AC' is not one of AA/AB/DYI/MYI -- invalid, do not label.",
                 scenario="A citizen-ID-shaped alphanumeric string, "
                          "mentioned during a routine document check."),
    ],
    "AZ_PASSPORT_NUMBER": [
        EdgeCase("PAS-01", "positive_valid",
                 "Full-alphabet leading letter form, includes I."),
        EdgeCase("PAS-02", "invalid_near_miss",
                 "Two leading letters instead of one -- invalid, do not label.",
                 scenario="A passport-shaped alphanumeric string, mentioned "
                          "during a routine document check."),
    ],
    "AZ_VOEN": [
        EdgeCase("VOE-01", "positive_valid",
                 "10-digit form with an explicit VOEN anchor word nearby."),
        EdgeCase("VOE-02", "invalid_near_miss",
                 "9 digits, wrong length -- invalid, do not label.",
                 scenario="A 9-digit reference number, mentioned in an "
                          "administrative note."),
    ],
    "AZ_DRIVER_LICENSE_NUMBER": [
        EdgeCase("DRV-01", "positive_valid", "2-letter + 6-digit form."),
        EdgeCase("DRV-02", "invalid_near_miss",
                 "Three leading letters instead of two -- invalid, do not label.",
                 scenario="A driver's-license-shaped alphanumeric string, "
                          "mentioned during a routine document check."),
    ],
    "TELEPHONENUM": [
        EdgeCase("TEL-01", "positive_valid", "International form with spaces."),
        EdgeCase("TEL-04", "invalid_near_miss",
                 "Only 5 significant digits, below the minimum -- invalid, "
                 "do not label.",
                 scenario="A short partial phone-number fragment, mentioned "
                          "while jotting down a contact note."),
    ],
    "ZIPCODE": [
        EdgeCase("ZIP-01", "positive_valid",
                 "AZ-prefixed international form, format-resolvable on its own."),
        EdgeCase("ZIP-02", "ambiguous_requires_anchor",
                 "Bare 4-digit domestic form, identical in shape to "
                 "BUILDINGNUM -- requires a postal anchor ('poçt indeksi' / "
                 "'poçt kodu' / 'indeks') immediately nearby to resolve toward "
                 "ZIPCODE rather than BUILDINGNUM."),
    ],
    "CARD_SECURITY_CODE": [
        EdgeCase("CVV-01", "positive_valid",
                 "3-digit code with an explicit CVV anchor immediately before it."),
        EdgeCase("CVV-03", "hard_negative",
                 "A bare 3-digit item count with no CVV/CVC/'təhlükəsizlik "
                 "kodu'/'kartın kodu' anchor nearby -- do not label.",
                 scenario="A 3-digit item count, mentioned while describing "
                          "an order's contents."),
    ],
    "DATE": [
        EdgeCase("DAT-01", "positive_valid",
                 "Numeric dd.mm.yyyy form, birth-date context, anchor required."),
        EdgeCase("DAT-04", "hard_negative",
                 "A bare number sequence with no date anchor -- ambiguous with "
                 "AGE/BUILDINGNUM, do not label.",
                 scenario="A bare small number, mentioned as a headcount in "
                          "an unrelated note."),
    ],
    "TIME": [
        EdgeCase("TIM-01", "positive_valid",
                 "24-hour form with a schedule anchor."),
        EdgeCase("TIM-03", "hard_negative",
                 "A sports score, colon-shaped but not a time -- do not label.",
                 scenario="A sports match score, mentioned while recapping "
                          "a game."),
    ],
    "AGE": [
        EdgeCase("AGE-01", "positive_valid", "Direct age anchor."),
        EdgeCase("AGE-03", "hard_negative",
                 "A room/building number with the same bare-number shape as "
                 "an age -- collides with BUILDINGNUM, do not label.",
                 scenario="A room number, mentioned while giving directions "
                          "inside an office building."),
    ],
    "BUILDINGNUM": [
        EdgeCase("BLD-01", "positive_valid",
                 "Building number with a street anchor nearby."),
        EdgeCase("BLD-02", "hard_negative",
                 "An order number with no address anchor nearby -- collides "
                 "with ZIPCODE's bare form, do not label.",
                 scenario="An order number, mentioned while discussing a "
                          "delivery that hasn't shipped yet."),
    ],
    "GIVENNAME": [
        EdgeCase("GVN-01", "positive_valid", "First name, sentence-initial."),
        EdgeCase("GVN-02", "positive_valid",
                 "Initial form (e.g. 'A.') standing in for the given name."),
        EdgeCase("GVN-03", "positive_valid",
                 "Given name in a signature block: a closing salutation on "
                 "one line and the name alone on the next, with no "
                 "surrounding sentence.",
                 scenario="End the document with a closing salutation on its "
                          "own line, then the person's full name alone on the "
                          "line below it, the way a letter or an email is "
                          "signed off."),
        EdgeCase("GVN-04", "positive_valid",
                 "Given name in an oblique grammatical case -- the inflected "
                 "surface form, not the dictionary form.",
                 scenario="Mention the person as the object or recipient of "
                          "the action rather than as the subject, so the name "
                          "carries the grammatical ending that role requires "
                          "in this language."),
    ],
    "SURNAME": [
        EdgeCase("SUR-01", "positive_valid",
                 "Surname with a genitive suffix that must be excluded from the span."),
        EdgeCase("SUR-02", "positive_valid",
                 "Feminine form is the complete value, not a suffix to strip."),
        EdgeCase("SUR-03", "positive_valid",
                 "Surname carrying a copula ending written joined to it "
                 "('-dir/-dır/-dur/-dür' and its person-inflected forms).",
                 scenario="Have someone state whose name it is in a single "
                          "clause, so the surname is written with its "
                          "sentence ending joined directly onto it with no "
                          "space, as ordinary speech does."),
        EdgeCase("SUR-04", "positive_valid",
                 "Surname in surname-first ordering, as on official forms.",
                 scenario="Write the person's name the way an official form "
                          "lists it, family name first and given name second, "
                          "separated only by a space or a comma."),
        EdgeCase("SUR-05", "positive_valid",
                 "Plural/collective family form of the surname.",
                 scenario="Refer to the whole family or household by their "
                          "family name rather than to one individual, using "
                          "the plural form the language requires."),
        EdgeCase("SUR-06", "positive_valid",
                 "Surname in an oblique grammatical case -- the inflected "
                 "surface form, not the dictionary form.",
                 scenario="Mention the person as the object or recipient of "
                          "the action rather than as the subject, so the "
                          "family name carries the grammatical ending that "
                          "role requires in this language."),
    ],
    "CITY": [
        EdgeCase("CTY-01", "positive_valid", "City name in an address line."),
        EdgeCase("CTY-02", "positive_valid",
                 "City name mentioned in running prose (e.g. 'X şəhərində "
                 "yaşayır'), with no address-line formatting -- the city "
                 "name itself, without a trailing 'şəhəri' suffix word "
                 "attached to it. Still a full sentence, not a bare word."),
        EdgeCase("CTY-03", "positive_valid",
                 "City name carrying a locative/possessive ending written "
                 "joined directly to it.",
                 scenario="Say where something happened or where someone "
                          "lives, so the city name is written with its "
                          "place ending joined directly onto it with no "
                          "space, as ordinary prose does."),
    ],
    "STREET": [
        EdgeCase("STR-01", "positive_valid",
                 "Street value (name plus its bundled 'küçəsi'/'küç.' suffix "
                 "word, already part of the given value) in an address line -- "
                 "embed the value exactly as given, do not add another "
                 "street-type word of your own."),
        EdgeCase("STR-02", "positive_valid",
                 "Same as STR-01 but the given value's bundled suffix "
                 "happens to be 'prospekti'/'pr.' -- embed exactly as given, "
                 "do not add another street-type word of your own."),
        EdgeCase("STR-03", "positive_valid",
                 "Street named after a person, referred to in running prose "
                 "with a place ending rather than in an address block.",
                 scenario="Have someone say where they are or where they are "
                          "heading, naming the street in the middle of a "
                          "sentence instead of in a formatted address line. "
                          "Embed the street value exactly as given."),
    ],
}

# P2-6: contrast lessons. Two values the model confused on the benchmark,
# in one document, each beside its own anchor word: the anchor is what tells
# them apart (A7 rows 1-3). Values come from ValueFactory's contrast helpers,
# so a token and a key can share one body, and a licence and an ID card one
# prefix. `labels` are the two planned labels, in the helper's order.
@dataclass(frozen=True)
class ContrastCase:
    case: EdgeCase
    labels: tuple[str, str]
    maker: str          # ValueFactory method returning the two values


CONTRAST_CASES: list[ContrastCase] = [
    ContrastCase(EdgeCase("CON-01", "positive_valid",
                          "An access token and an API key with the same body, "
                          "told apart only by their anchor words.",
                          scenario="Mention both credentials in the same document, each "
                                   "introduced by its own words: one as an access or session "
                                   "token, the other as an API key. Embed each value exactly "
                                   "as given."),
                 ("ACCESS_TOKEN", "API_KEY"), "token_key_same_body"),
    ContrastCase(EdgeCase("CON-02", "positive_valid",
                          "A ::-compressed IPv6 address and a MAC address in one "
                          "network note.",
                          scenario="Describe one device on a network: give its IPv6 address "
                                   "and its MAC (hardware) address, each named as such. Embed "
                                   "each value exactly as given."),
                 ("IPV6_ADDRESS", "MAC_ADDRESS"), "ipv6_and_mac"),
    ContrastCase(EdgeCase("CON-03", "positive_valid",
                          "A driver's licence and an ID card with the same letter "
                          "prefix, told apart by their anchor words.",
                          scenario="Mention both of one person's documents: the driving "
                                   "licence number and the identity card number, each named "
                                   "as such. Embed each value exactly as given."),
                 ("AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER"), "licence_and_id_same_prefix"),
]


_NEGATIVE_STATUSES = {"hard_negative", "invalid_near_miss"}


def is_negative(case: EdgeCase) -> bool:
    """True if this case's ground truth is 'no entity' (a decoy, not a value)."""
    return case.status in _NEGATIVE_STATUSES


def is_negative_status(status: str) -> bool:
    """Same check by bare status string -- for code that only has a status
    field (e.g. reconstructing from a dspy.Example), not an EdgeCase object."""
    return status in _NEGATIVE_STATUSES


def smoke_pair(label: str) -> list[EdgeCase]:
    """The two cases used for the initial 'N per label' generation run."""
    return LABEL_CASES[label]


def _rand(rng: Random, alphabet: str, k: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(k))


def near_miss_value(case: EdgeCase, label: str, rng: Random) -> str:
    """Build the deliberately-wrong value for a hard_negative/invalid_near_miss
    case. Ground truth for these is 'no entity' -- the string is embedded as
    an unlabeled decoy, never claimed as this (or any) label."""
    cid = case.id

    if cid == "APK-03":
        return _rand(rng, string.ascii_letters + string.digits, 32)
    if cid == "ATK-02":
        seg = lambda n: _rand(rng, string.ascii_letters + string.digits + "-_", n)
        return f"{seg(24)}.{seg(30)}"
    if cid == "PVK-04":
        return rng.choice([
            "// TODO: bu hissəni sonra refaktor et",
            "# köhnə açar idarəetməsi buraya köçürüləcək",
            "// bu funksiya artıq istifadə olunmur, silinəcək",
        ])
    if cid == "PCN-03":
        prefix = rng.choice(["4", "5"])
        body = prefix + _rand(rng, string.digits, 14)
        good = CK.luhn_check_digit(body)
        bad = str((int(good) + rng.randint(1, 9)) % 10)
        number = body + bad
        return " ".join(number[i:i + 4] for i in range(0, 16, 4))
    if cid == "IBN-03":
        country = "AZ"
        bban_len = 24
        bban = _rand(rng, string.ascii_uppercase, 4) + _rand(rng, string.digits, bban_len - 4)
        good = CK.iban_check_digits(country, bban)
        bad = f"{(int(good) + rng.randint(1, 20)) % 100:02d}"
        return country + bad + bban
    if cid == "IP4-04":
        return (f"{rng.randint(1, 20)}.{rng.randint(0, 40)}."
                f"{rng.randint(0, 99)}.{rng.randint(0, 999) % 256}")
    if cid == "IP6-03":
        return "2001:0db8:zzzz::1"
    if cid == "MAC-04":
        return ":".join(_rand(rng, _HEX, 2) for _ in range(6))
    if cid == "URL-04":
        return rng.choice([
            "https://example.az/haqqinda",
            "https://sirket.az/xeberler/2026-yeniliklər",
        ])
    if cid == "ICC-02":
        body = "89994" + _rand(rng, string.digits, 14)
        good = CK.luhn_check_digit(body)
        bad = str((int(good) + rng.randint(1, 9)) % 10)
        return body + bad
    if cid == "EML-04":
        return "@" + _rand(rng, string.ascii_lowercase, rng.randint(6, 10))
    if cid == "FIN-03":
        return _rand(rng, "0123456789ABCDEF", 7)
    if cid == "IDC-03":
        return "AC" + _rand(rng, string.digits, 7)
    if cid == "PAS-02":
        return _rand(rng, string.ascii_uppercase, 2) + _rand(rng, string.digits, 8)
    if cid == "VOE-02":
        return _rand(rng, string.digits, 9)
    if cid == "DRV-02":
        return _rand(rng, string.ascii_uppercase, 3) + _rand(rng, string.digits, 5)
    if cid == "TEL-04":
        return "+994 " + _rand(rng, string.digits, 2)
    if cid == "CVV-03":
        return str(rng.randint(100, 999))
    if cid == "DAT-04":
        return str(rng.randint(1, 40))
    if cid == "TIM-03":
        return f"{rng.randint(0, 5)}:{rng.randint(0, 5)}"
    if cid == "AGE-03":
        return str(rng.randint(1, 60))
    if cid == "BLD-02":
        return str(rng.randint(1, 200))

    raise KeyError(f"no near-miss builder registered for case {cid!r}")


def positive_value(case: EdgeCase, label: str, factory: ValueFactory,
                    lang: str = "az") -> str:
    """Mint the real, valid value for a positive_valid/positive_format_variant/
    ambiguous_requires_anchor case, reusing the checksum-valid, deduplicated
    ValueFactory rather than inventing a value ad hoc."""
    value = factory.make(label, lang)
    if case.id == "GVN-02":
        # "Initial form" -- same first name, truncated to its initial.
        value = value[0] + "."
    return value
