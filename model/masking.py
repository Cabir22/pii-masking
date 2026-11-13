"""Phase 2: the reversible masking operator.

Format-agnostic on purpose, same as predict.py's detect_entities -- this
takes one entity VALUE and a key, and returns a same-shape masked value that
a later unmask_value(..., same key) recovers exactly. Nothing here knows or
cares whether the value came from a TXT line, a CSV cell, or an Excel sheet.

Technique: format-preserving encryption (FF3, NIST SP 800-38G), chosen over
a tokenization vault specifically because masked values need to survive
being processed by an EXTERNAL LLM and come back in its response still
recoverable (the project's actual purpose: masking text before a fallback
call to a provider like OpenAI when the in-house AI is down). A real-looking
fake value reads as ordinary text to an external model and is far more
likely to survive untouched in its response than an opaque token like
"[PERSON_1]", which an LLM that doesn't know it's a protected placeholder
can paraphrase, drop, or reformat.

Two real constraints FF3 has, both verified empirically against the
installed `ff3` package rather than assumed:

  1. FF3 only operates on a single, fixed alphabet at a time -- it has no
     idea that "+994 50 123-45-67" is "digits with punctuation furniture".
     `_extract_core`/`_reinsert` below split any value into its
     alphabet-member characters (encrypted) and everything else (left
     exactly where it was), so a phone number keeps its spaces and dashes
     in place and a name keeps any apostrophe in place.
  2. FF3 refuses inputs below a minimum domain size (NIST's own
     vulnerability-driven floor: an attacker who can enumerate a too-small
     domain can brute-force it). Measured directly: 6 characters minimum
     for a 10-symbol digit alphabet, only 4 for a 34-symbol Azerbaijani
     letter alphabet -- the minimum shrinks as the alphabet grows, because
     what actually matters is domain SIZE (alphabet_size ** length), not
     character count. A 2-digit AGE or a 3-letter name ("Əli") still falls
     under even the smaller floor, so those use `_small_domain_permute`
     instead -- a fully keyed, deterministic permutation of the exact
     (small) space of possible values, recomputed identically on encrypt and
     decrypt rather than stored anywhere. This is not a weaker protection
     invented to work around FF3's limit; it's the same reason FF3 itself
     refuses these lengths -- a 2-digit value has ~100 possible real values
     no matter what disguises it, so the honest design is a correct
     reversible permutation of that small space, not a false sense of
     cryptographic strength FF3 wouldn't actually provide there either.
"""

from __future__ import annotations

import hashlib
import random
import re

from ff3 import FF3Cipher

DIGIT_ALPHABET = "0123456789"
# Letter alphabet covering every script this project's corpus actually
# contains -- Latin (+ Azerbaijani-specific letters) AND Cyrillic, since the
# checkpoint and corpus are AZ/EN/TR/RU (see model/train.py, README). A
# Latin-only alphabet was the FIRST version of this and it shipped a real,
# silent bug: a Cyrillic name/city/street has zero characters in a
# Latin-only alphabet, so _extract_core finds no "core" to encrypt and
# mask_value quietly returns the input unchanged -- the round-trip test
# still passes (nothing was masked, so nothing needed to un-mask), which is
# exactly how a masking no-op hides. Caught only by testing against the
# FULL 4-language corpus, not just Azerbaijani samples.
_AZ_LOWER = "abcdefghijklmnopqrstuvwxyzəıöüçşğ"
_AZ_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZƏİÖÜÇŞĞ"
_CYRILLIC_LOWER = "".join(chr(c) for c in range(0x0430, 0x0450)) + "ё"
_CYRILLIC_UPPER = "".join(chr(c) for c in range(0x0410, 0x0430)) + "Ё"
# Armenian, for the same reason Cyrillic is here. Sweeping every
# GIVENNAME/SURNAME/CITY/STREET value in the corpus for alphabetic
# characters this alphabet cannot represent turned up exactly one script
# beyond the expected four languages' own: Armenian, 313 occurrences over
# 29 distinct characters, in street names like "Կարո Ալվարյան փողոց".
# Without it those characters are structurally unmaskable and pass through
# the "masked" output verbatim -- the same silent no-op the Latin-only
# version of this alphabet shipped for Cyrillic. The full blocks are
# included rather than just the 29 characters observed, so a name using a
# letter that happens not to appear in this corpus is not a fresh leak.
_ARMENIAN_UPPER = "".join(chr(c) for c in range(0x0531, 0x0557))
_ARMENIAN_LOWER = "".join(chr(c) for c in range(0x0561, 0x0588))
LETTER_ALPHABET = (_AZ_LOWER + _AZ_UPPER + _CYRILLIC_LOWER + _CYRILLIC_UPPER
                   + _ARMENIAN_UPPER + _ARMENIAN_LOWER)
# Latin letters only -- for structured codes whose letters are a format
# prefix rather than free text ("AZ4740", "215A"). Masking those through
# the full LETTER_ALPHABET is not wrong, but it turned "AZ4740" into
# "Оo6820": a Cyrillic country prefix on an Azerbaijani postcode reads as
# corrupted data rather than as masked data, and the point of preserving
# format is that the result still looks like the thing it replaced.
_LATIN_CODE_ALPHABET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                        "abcdefghijklmnopqrstuvwxyz")
# Both cases, deliberately. This was uppercase-only until a corpus-wide
# sweep found the exact same class of silent no-op the Cyrillic bug above
# was: a lowercase IBAN ("az98gtzy3180...") has its letters OUTSIDE the
# alphabet, so _extract_core never picks them up and they pass through the
# "masked" output verbatim -- the country code and bank code fully
# readable. 93/1200 real IBANs in the corpus are lowercase. Round-trip
# tests could never catch it (nothing was masked, so nothing needed
# un-masking); only checking which characters are structurally incapable
# of being encrypted did.
ALNUM_ALPHABET = ("0123456789"
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "abcdefghijklmnopqrstuvwxyz")
# Hex, both cases -- for values whose format only permits hex digits, where
# a general alnum alphabet would produce something that no longer parses as
# that format at all (a MAC masked with ALNUM_ALPHABET came out as
# "9X:Bb:DU:Kf:8f:9E": 'X', 'U', 'K' are not hex, so the result was not a
# MAC address). Case is not preserved within the mapping and does not need
# to be: hex is case-insensitive, so a mixed-case result is still valid.
HEX_ALPHABET = "0123456789abcdefABCDEF"
# Case-preserving, digits+Latin-letters only (no AZ/Cyrillic extras): real
# email local-parts/domains are near-universally ASCII, and mixing case
# matters here (VOEN/FIN/passport values are conventionally upper-cased
# already, but "Eli.Mammadov@..." would round-trip through an upper-only
# alphabet as "ELI.MAMMADOV@..." -- a silent, needless case-corruption bug
# for the one label whose real-world values are actually mixed-case).
EMAIL_ALPHABET = ("abcdefghijklmnopqrstuvwxyz"
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                  "0123456789")

# Which alphabet applies per label. Only labels whose VALUE is itself the
# secret need an entry -- anchor_required labels are masked the same way as
# their shape (AGE/BUILDINGNUM/CARD_SECURITY_CODE are digit-shaped; DATE and
# TIME are handled as digit-shaped too, since _extract_core leaves every
# separator -- '.', ':', '-' -- untouched in place).
LABEL_ALPHABET = {
    "TELEPHONENUM": DIGIT_ALPHABET, "AZ_VOEN": DIGIT_ALPHABET,
    "AGE": DIGIT_ALPHABET, "BUILDINGNUM": DIGIT_ALPHABET,
    "CARD_SECURITY_CODE": DIGIT_ALPHABET, "PAYMENT_CARD_NUMBER": DIGIT_ALPHABET,
    "ICCID": DIGIT_ALPHABET, "ZIPCODE": DIGIT_ALPHABET,
    "DATE": DIGIT_ALPHABET, "TIME": DIGIT_ALPHABET,
    "AZ_FIN": ALNUM_ALPHABET, "AZ_ID_CARD_NUMBER": ALNUM_ALPHABET,
    "AZ_PASSPORT_NUMBER": ALNUM_ALPHABET,
    "AZ_DRIVER_LICENSE_NUMBER": ALNUM_ALPHABET,
    "IBAN": ALNUM_ALPHABET,
    "MAC_ADDRESS": HEX_ALPHABET,
    "GIVENNAME": LETTER_ALPHABET, "SURNAME": LETTER_ALPHABET,
    "CITY": LETTER_ALPHABET, "STREET": LETTER_ALPHABET,
    "IPV6_ADDRESS": HEX_ALPHABET,
    # An API key / access token is an opaque alphanumeric string; its
    # separators ('-', '_', '.' -- a JWT's three base64url segments) stay
    # in place as punctuation furniture, so the masked value keeps the
    # same shape and length and still reads as a credential. Nothing about
    # these needs to stay VALID (there is no checksum and no issuer to
    # satisfy), which is what makes them ordinary FPE cases rather than
    # the structure-aware ones below.
    "API_KEY": ALNUM_ALPHABET, "ACCESS_TOKEN": ALNUM_ALPHABET,
    # Handled by STRUCTURED_MASKERS below, not by plain FPE over this
    # alphabet -- present here only so formats/*.py's "is this maskable"
    # membership check resolves, and naming the alphabet the structured
    # masker actually uses on the encrypted portion.
    "IPV4_ADDRESS": DIGIT_ALPHABET,
    "URL": ALNUM_ALPHABET,
    "PRIVATE_KEY": ALNUM_ALPHABET,
    # EMAIL: '@' and every '.'/'-'/'_' are punctuation furniture to
    # _extract_core exactly like a phone number's spaces and dashes -- they
    # stay in place untouched, only the letters/digits either side of them
    # get encrypted. "eli.mammadov@example.com" keeps its shape (one '@',
    # dots where they were, same length either side) but the actual name and
    # domain are gone, which is all format-preserving encryption promises:
    # it was never a guarantee the output re-resolves as a real mailbox
    # (mask_value doesn't promise that for GIVENNAME/CITY either).
    "EMAIL": EMAIL_ALPHABET,
}

# DATE and TIME can carry BOTH digits and letters in the same value
# ("14 noyabr 2018", "2:54 PM") -- LABEL_ALPHABET above still lists them as
# plain DIGIT_ALPHABET (that's what formats/*.py's "is this label
# maskable at all" check reads, and it's correct: every DATE/TIME value
# has digits), but mask_value/unmask_value check THIS registry first.
# Without it, the letters (a month name, AM/PM) would fall entirely
# outside DIGIT_ALPHABET and be left as untouched template text --
# harmless for a purely-numeric date, but it silently left the true month
# name or AM/PM fully readable in an otherwise "masked" value (found via
# real-model testing). Digits and letters are extracted
# and FPE'd independently -- a digit position stays a digit, a letter
# position stays a letter of the SAME alphabet GIVENNAME/CITY/STREET
# already use, exactly the treatment every other letter-bearing label in
# this module already gets, not a new one invented just for this.
MULTI_ALPHABET_LABELS: dict[str, list[str]] = {
    "DATE": [DIGIT_ALPHABET, LETTER_ALPHABET],
    "TIME": [DIGIT_ALPHABET, LETTER_ALPHABET],
    # The same mixed-content problem, found by sweeping every label's real
    # corpus values for characters structurally incapable of being masked:
    #   BUILDINGNUM  381/861  ("215A", "48E" -- the building letter walked
    #                          straight through a digits-only alphabet)
    #   STREET       158/1200 ("переулок 2-джи Зира" -- the number in a
    #                          street name walked through a letters-only one)
    #   ZIPCODE      561/561  ("AZ4740" -- the AZ prefix; a constant rather
    #                          than per-person information, so not a leak in
    #                          the way the two above are, but there is no
    #                          reason to leave it as the one label that
    #                          half-masks its own values)
    #   CITY           1/497  (a single corpus value, "6oranboy", where a
    #                          digit stands in for a mistyped 'G')
    "BUILDINGNUM": [DIGIT_ALPHABET, _LATIN_CODE_ALPHABET],
    "STREET": [LETTER_ALPHABET, DIGIT_ALPHABET],
    "ZIPCODE": [DIGIT_ALPHABET, _LATIN_CODE_ALPHABET],
    "CITY": [LETTER_ALPHABET, DIGIT_ALPHABET],
}

# IPV4_ADDRESS, URL and PRIVATE_KEY are the three labels whose structure
# genuinely ISN'T "one alphabet plus punctuation furniture", so each gets a
# real structure-aware masker below rather than being excluded (they, plus
# IPV6/API_KEY/ACCESS_TOKEN above, used to be the six labels this module
# masked not at all -- they were left in plaintext and merely reported,
# which for an IP address or a private key is the worst thing on the list
# to leave readable). They still go in LABEL_ALPHABET so that
# formats/*.py's "is this label maskable at all" membership check sees
# them; the alphabet named is the one the structured masker uses for the
# part of the value it does encrypt.
STRUCTURED_MASKERS: dict[str, str] = {
    "IPV4_ADDRESS": "ipv4",
    "URL": "url",
    "PRIVATE_KEY": "private_key",
}

_DOMAIN_SAFETY_CAP = 5_000_000  # see _small_domain_permute


def _extract_core(value: str, alphabet: str) -> tuple[str, list]:
    """Splits `value` into (core, template): `core` is every character that
    belongs to `alphabet`, in order; `template` has one entry per original
    character -- None where a core character goes, or the literal character
    itself where it must be reinserted unchanged.
    """
    core_chars = []
    template = []
    for ch in value:
        if ch in alphabet:
            core_chars.append(ch)
            template.append(None)
        else:
            template.append(ch)
    return "".join(core_chars), template


def _reinsert(core: str, template: list) -> str:
    it = iter(core)
    return "".join(next(it) if slot is None else slot for slot in template)


def _extract_multi_core(value: str, alphabets: list[str]) -> tuple[list[str], list]:
    """Like _extract_core, generalized to several non-overlapping
    alphabets at once: each character goes into the core of the FIRST
    alphabet it belongs to, `template` records which alphabet's core
    (by index into `alphabets`) each position came from, or the literal
    character where it belongs to none of them. A digit stays tagged as
    "the digit core" and a letter as "the letter core" even though both
    get reinserted into the same final string -- that's what keeps "14
    noyabr 2018" masking to something still digit-where-digits-were,
    letter-where-letters-were, rather than the two classes bleeding into
    each other's positions.
    """
    cores: list[list[str]] = [[] for _ in alphabets]
    template = []
    for ch in value:
        for i, alphabet in enumerate(alphabets):
            if ch in alphabet:
                cores[i].append(ch)
                template.append(i)
                break
        else:
            template.append(ch)
    return ["".join(c) for c in cores], template


def _reinsert_multi(cores: list[str], template: list) -> str:
    iters = [iter(c) for c in cores]
    return "".join(next(iters[slot]) if isinstance(slot, int) else slot
                   for slot in template)


def _permutation_for(alphabet: str, length: int, key: bytes, tag: str) -> list[int]:
    """A deterministic keyed permutation of range(len(alphabet) ** length),
    recomputed identically (never stored) whenever encrypt/decrypt needs it.
    Caching per (alphabet, length, key, tag) avoids rebuilding it on every
    call within one process -- masking a column of thousands of AGE values
    would otherwise reshuffle the same 100-element list thousands of times.

    `tag` (the entity label, e.g. "AGE" vs "BUILDINGNUM") keeps two
    same-alphabet, same-length fields from sharing one permutation table.
    Without it, AGE=3 and BUILDINGNUM=3 masked under the same key would
    hit the exact same table lookup and therefore the exact same output --
    found via a real leak scan: single-digit AGE and BUILDINGNUM values
    were landing on IDENTICAL fixed points (both mapped "3" to itself)
    because they were, unintentionally, permuting one shared table rather
    than two independent ones. Matches _permute_index's existing tag
    convention (used for IPv4 octets) -- this function was the one place
    that convention hadn't been applied.

    Domain-separating by tag does NOT remove fixed points themselves: a
    permutation over a small domain (10 values for a 1-digit field) has an
    expected ~1 fixed point no matter how it's keyed -- that's inherent to
    any keyed permutation over a small domain, not fixable without
    breaking either determinism or reversibility. What this fixes is the
    CROSS-FIELD leak: an attacker who spots AGE's fixed point learns
    nothing about BUILDINGNUM's anymore, because they're now different,
    independently-keyed permutations.
    """
    n = len(alphabet)
    domain_size = n ** length
    if domain_size > _DOMAIN_SAFETY_CAP:
        raise ValueError(
            f"small-domain fallback asked to permute {domain_size:,} values "
            f"(alphabet size {n}, length {length}) -- likely means this "
            f"value should have gone through FF3 instead; refusing rather "
            f"than materializing a multi-million-entry list")
    cache_key = (alphabet, length, key, tag)
    cached = _permutation_for._cache.get(cache_key)
    if cached is not None:
        return cached
    seed_material = (key + alphabet.encode("utf-8") + length.to_bytes(4, "big")
                     + tag.encode("utf-8"))
    seed = int.from_bytes(hashlib.sha256(seed_material).digest(), "big")
    perm = list(range(domain_size))
    random.Random(seed).shuffle(perm)
    _permutation_for._cache[cache_key] = perm
    return perm


_permutation_for._cache = {}
_inverse_cache: dict = {}


def _small_domain_permute(core: str, alphabet: str, key: bytes,
                          forward: bool, tag: str) -> str:
    n = len(alphabet)
    length = len(core)
    char_to_idx = {c: i for i, c in enumerate(alphabet)}
    perm = _permutation_for(alphabet, length, key, tag)

    rank = 0
    for ch in core:
        rank = rank * n + char_to_idx[ch]

    if forward:
        new_rank = perm[rank]
    else:
        cache_key = (alphabet, length, key, tag)
        inverse = _inverse_cache.get(cache_key)
        if inverse is None:
            inverse = [0] * len(perm)
            for i, p in enumerate(perm):
                inverse[p] = i
            _inverse_cache[cache_key] = inverse
        new_rank = inverse[rank]

    out = []
    for _ in range(length):
        out.append(alphabet[new_rank % n])
        new_rank //= n
    return "".join(reversed(out))


_ff3_cache: dict = {}


def _ff3_for(alphabet: str, key: bytes) -> FF3Cipher:
    cache_key = (alphabet, key)
    cipher = _ff3_cache.get(cache_key)
    if cipher is None:
        hex_key = key.hex().upper()
        tweak = hashlib.sha256(key).hexdigest()[:16].upper()
        if alphabet == DIGIT_ALPHABET:
            cipher = FF3Cipher(hex_key, tweak, 10)
        else:
            cipher = FF3Cipher.withCustomAlphabet(hex_key, tweak, alphabet)
        _ff3_cache[cache_key] = cipher
    return cipher


def _min_ff3_length(alphabet: str) -> int:
    """FF3's own floor for this alphabet -- domain size (alphabet_size **
    length) must clear NIST's minimum; found by probing directly against the
    installed library (6 for digits, 4 for a 34-symbol letter alphabet)
    rather than hardcoding a number that might not hold for every alphabet
    size used here.
    """
    cached = _min_ff3_length._cache.get(alphabet)
    if cached is not None:
        return cached
    cipher = _ff3_for(alphabet, b"\x00" * 16)
    for length in range(2, 20):
        try:
            cipher.encrypt(alphabet[0] * length)
            _min_ff3_length._cache[alphabet] = length
            return length
        except ValueError:
            continue
    raise RuntimeError(f"could not determine FF3 minimum length for {alphabet!r}")


_min_ff3_length._cache = {}


def _max_ff3_length(alphabet: str) -> int:
    """FF3's own ceiling for this alphabet, probed the same way as the
    floor. Found empirically, not assumed: a 30-symbol-or-so cap that a real
    corpus value can and does exceed -- a compound STREET name like
    "Çingiz Mehdi oğlu Cuvarlı prospekti" has a 31-letter core once spaces
    are set aside, one character over the letter alphabet's ceiling. Caught
    by the large-scale real-value round-trip test, not assumed away.
    """
    cached = _max_ff3_length._cache.get(alphabet)
    if cached is not None:
        return cached
    cipher = _ff3_for(alphabet, b"\x00" * 16)
    lo = _min_ff3_length(alphabet)
    hi = lo
    while hi < 200:
        try:
            cipher.encrypt(alphabet[0] * (hi + 1))
        except ValueError:
            break
        hi += 1
    _max_ff3_length._cache[alphabet] = hi
    return hi


_max_ff3_length._cache = {}


def _chunk_lengths(total_length: int, min_len: int, max_len: int) -> list[int]:
    """Splits `total_length` into pieces each within [min_len, max_len],
    as evenly sized as possible. Deterministic from `total_length` alone, so
    decrypt recomputes the identical chunk boundaries from the masked core's
    length (masking never changes length) without needing to store anything.
    """
    if total_length <= max_len:
        return [total_length]
    n_chunks = -(-total_length // max_len)  # ceil division
    base, rem = divmod(total_length, n_chunks)
    lengths = [base + 1] * rem + [base] * (n_chunks - rem)
    if any(l < min_len for l in lengths):
        raise ValueError(
            f"cannot split a {total_length}-character value into pieces "
            f"that all fit within FF3's [{min_len}, {max_len}] bounds for "
            f"this alphabet")
    return lengths


def _transform_core(core: str, alphabet: str, key: bytes, forward: bool,
                    tag: str = "") -> str:
    if not core:
        return core
    min_len, max_len = _min_ff3_length(alphabet), _max_ff3_length(alphabet)
    if len(core) < min_len:
        # Domain separation only matters here: FF3 below operates on
        # domains in the millions+, where a same-alphabet cross-label
        # collision is negligible; the small-domain path is where it's
        # concretely observed (see _permutation_for's docstring).
        return _small_domain_permute(core, alphabet, key, forward, tag)
    if len(core) > max_len:
        cipher = _ff3_for(alphabet, key)
        out = []
        pos = 0
        for length in _chunk_lengths(len(core), min_len, max_len):
            chunk = core[pos:pos + length]
            out.append(cipher.encrypt(chunk) if forward else cipher.decrypt(chunk))
            pos += length
        return "".join(out)
    cipher = _ff3_for(alphabet, key)
    return cipher.encrypt(core) if forward else cipher.decrypt(core)


def _permute_index(index: int, domain: int, key: bytes, tag: str,
                   forward: bool) -> int:
    """Keyed permutation of range(domain), for the structure-aware maskers
    below where the thing being permuted is a NUMBER in a bounded range
    rather than a string over an alphabet (an IPv4 octet). Same
    construction and same honesty as _small_domain_permute: recomputed
    from the key, never stored, and no pretence that a small domain gives
    more protection than its own size allows.
    """
    cache_key = (domain, tag, key, forward)
    cached = _permute_index._cache.get(cache_key)
    if cached is None:
        seed_material = key + tag.encode("utf-8") + domain.to_bytes(4, "big")
        seed = int.from_bytes(hashlib.sha256(seed_material).digest(), "big")
        perm = list(range(domain))
        random.Random(seed).shuffle(perm)
        if not forward:
            inverse = [0] * domain
            for i, p in enumerate(perm):
                inverse[p] = i
            perm = inverse
        _permute_index._cache[cache_key] = perm
        cached = perm
    return cached[index]


_permute_index._cache = {}


def _mask_ipv4(value: str, key: bytes, forward: bool) -> str:
    """Masks each octet WITHIN its own digit width, so the result is both
    the same length and still a valid IPv4 address.

    Plain digit FPE would satisfy the length invariant but not validity:
    "192" encrypts just as happily to "847", and 847 is not an octet, so
    the "masked" value no longer parses as an IP at all. Permuting inside
    the set of values that render to the SAME number of digits keeps both
    properties at once.

    Each width's domain deliberately EXCLUDES leading-zero forms -- width 3
    is 100-255, not 0-255 zero-padded. Zero padding looked like the tidier
    way to preserve width until it was actually tested: "15.199.229.147"
    masked to "58.114.011.039", and Python's own ipaddress module rejects
    that, because a leading-zero octet is ambiguous between decimal and
    octal and has been treated as a parsing hazard since CVE-2021-29662.
    Anything that refuses to parse as an IP defeats the point of preserving
    the format in the first place.

    A 1-digit octet has only ten possible values and a permutation of ten
    values is all the protection that exists for it; that is a property of
    the data, not a weakness introduced here, and it is the same reasoning
    _small_domain_permute is built on.
    """
    parts = value.split(".")
    if len(parts) != 4 or not all(p.isdigit() and len(p) <= 3 for p in parts):
        # Not a dotted quad after all -- fall back to plain digit FPE, which
        # still masks and still round-trips, rather than raising on a value
        # a detector labelled IPV4_ADDRESS in good faith.
        core, template = _extract_core(value, DIGIT_ALPHABET)
        return _reinsert(_transform_core(core, DIGIT_ALPHABET, key, forward,
                                         tag="ipv4_fallback"),
                         template)
    out = []
    for p in parts:
        width = len(p)
        lo = 10 ** (width - 1) if width > 1 else 0
        hi = min(255, 10 ** width - 1)
        n = int(p)
        if not lo <= n <= hi:
            # A leading-zero octet ("010") or an out-of-range one ("300"):
            # no same-width, no-leading-zero value to map it onto, so leave
            # it rather than emit something that won't parse.
            out.append(p)
            continue
        out.append(str(lo + _permute_index(n - lo, hi - lo + 1, key,
                                           f"ipv4w{width}", forward)))
    return ".".join(out)


_URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")


def _mask_url(value: str, key: bytes, forward: bool) -> str:
    """Masks a URL's host, path and query values, leaving the scheme and
    every structural delimiter in place.

    The scheme ("https://") is deliberately NOT masked: it identifies a
    protocol, not a person, and scrambling it into "kxjqz://" would cost
    the one property this project actually needs from a masked value --
    that an external LLM reads it as ordinary text of the right kind and
    hands it back unmangled -- in exchange for hiding nothing. Everything
    after it IS masked, with '/', '?', '=', '&', '.', '-', '_' left as
    punctuation furniture so the result still parses as a URL.
    """
    m = _URL_SCHEME_RE.match(value)
    scheme = m.group(0) if m else ""
    rest = value[len(scheme):]
    core, template = _extract_core(rest, ALNUM_ALPHABET)
    masked_rest = _reinsert(
        _transform_core(core, ALNUM_ALPHABET, key, forward, tag="url"),
        template)
    return scheme + masked_rest


_PEM_ARMOUR_RE = re.compile(r"-----(?:BEGIN|END)[A-Z ]*-----")
_SSH_PREFIX_RE = re.compile(r"^(ssh-[a-z0-9\-]+|ecdsa-[a-z0-9\-]+)\s")


def _mask_private_key(value: str, key: bytes, forward: bool) -> str:
    """Masks the key MATERIAL, leaving the armour that says what kind of
    key it is.

    Both real shapes in this corpus carry a fixed, public preamble -- a PEM
    block ("-----BEGIN OPENSSH PRIVATE KEY-----" ... "-----END ...-----")
    or an SSH type prefix ("ssh-rsa AAAAB3Nza..."). Those announce the
    format; they are identical across every key of that type and reveal
    nothing about this one. The base64 body after them is the entire
    secret. Masking the whole string indiscriminately would shred the
    armour into "-----XKQPV ZBNMTQK-----" and destroy the one part that
    tells a reader (or an LLM) what it is looking at, while protecting
    nothing extra.
    """
    protected: list[tuple[int, int]] = []
    for m in _PEM_ARMOUR_RE.finditer(value):
        protected.append((m.start(), m.end()))
    m = _SSH_PREFIX_RE.match(value)
    if m:
        protected.append((m.start(), m.end()))

    pieces = []
    cursor = 0
    for start, end in sorted(protected):
        if start > cursor:
            pieces.append((value[cursor:start], True))   # maskable body
        pieces.append((value[start:end], False))          # armour, verbatim
        cursor = end
    if cursor < len(value):
        pieces.append((value[cursor:], True))

    out = []
    for text, maskable in pieces:
        if not maskable:
            out.append(text)
            continue
        core, template = _extract_core(text, ALNUM_ALPHABET)
        out.append(_reinsert(
            _transform_core(core, ALNUM_ALPHABET, key, forward,
                            tag="private_key"), template))
    return "".join(out)


_STRUCTURED_MASK_FNS = {
    "ipv4": _mask_ipv4,
    "url": _mask_url,
    "private_key": _mask_private_key,
}


def mask_value(label: str, value: str, key: bytes) -> str:
    """value -> a same-shape, reversible masked value.

    Deterministic: the same (label, value, key) always produces the same
    output, so the same real phone number appearing twice in one document
    masks to the same fake number both times -- consistent with how this
    project's own generation pipeline already treats repeat mentions of one
    real value as the same entity.
    """
    structured = STRUCTURED_MASKERS.get(label)
    if structured is not None:
        return _STRUCTURED_MASK_FNS[structured](value, key, True)

    alphabets = MULTI_ALPHABET_LABELS.get(label)
    if alphabets is not None:
        cores, template = _extract_multi_core(value, alphabets)
        masked_cores = [_transform_core(c, a, key, forward=True, tag=label)
                        for c, a in zip(cores, alphabets)]
        return _reinsert_multi(masked_cores, template)

    alphabet = LABEL_ALPHABET.get(label)
    if alphabet is None:
        raise ValueError(
            f"{label!r} is not in LABEL_ALPHABET -- URL/API_KEY/"
            f"ACCESS_TOKEN/PRIVATE_KEY/IPV4_ADDRESS/IPV6_ADDRESS need a "
            f"structure-aware mask, not plain FPE (see module docstring)")
    core, template = _extract_core(value, alphabet)
    masked_core = _transform_core(core, alphabet, key, forward=True, tag=label)
    return _reinsert(masked_core, template)


def unmask_value(label: str, masked_value: str, key: bytes) -> str:
    structured = STRUCTURED_MASKERS.get(label)
    if structured is not None:
        return _STRUCTURED_MASK_FNS[structured](masked_value, key, False)

    alphabets = MULTI_ALPHABET_LABELS.get(label)
    if alphabets is not None:
        cores, template = _extract_multi_core(masked_value, alphabets)
        real_cores = [_transform_core(c, a, key, forward=False, tag=label)
                     for c, a in zip(cores, alphabets)]
        return _reinsert_multi(real_cores, template)

    alphabet = LABEL_ALPHABET.get(label)
    if alphabet is None:
        raise ValueError(f"{label!r} is not in LABEL_ALPHABET")
    core, template = _extract_core(masked_value, alphabet)
    real_core = _transform_core(core, alphabet, key, forward=False, tag=label)
    return _reinsert(real_core, template)
