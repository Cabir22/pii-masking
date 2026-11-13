"""Quality gates specific to LLM output.

`validate.validate_example` already covers everything shared with the
procedural generator (offsets, overlaps, checksums, blocklist, language,
repeat-mention completeness). This module adds the failure modes that only
arise when a language model wrote the text.

**Leaked PII.** The prompt forbids inventing entities, but models still slip in
an extra email address or IP. An unlabeled real entity is worse than a rejected
document: it teaches the model that this exact pattern is *not* PII, directly
manufacturing false negatives. So we scan for high-precision PII shapes outside
known spans and reject on sight.

**Taxonomy label leak.** The model is handed 'LABEL: value' input lines and
sometimes echoes the label token itself into the document as a fake field
name ("GIVENNAME: Fatimə") instead of a natural one. See
`find_label_name_leak` below.

**Near-duplicates.** Sampling the same endpoint thousands of times with similar
briefs produces documents that differ only in their injected values. Character
n-gram Jaccard over a normalized form (with entity values masked out) catches
that, because masking is what makes two structurally identical documents look
identical to the detector rather than merely similar.
"""

from __future__ import annotations

import hashlib
import random
import re
from collections import deque

from .. import checksums as CK
from ..negatives import decoy_occurrences

try:                                  # optional, for a ~100x faster MinHash
    import numpy as _np
except ImportError:                   # pure-Python fallback below
    _np = None

# --- leak detection ---------------------------------------------------------
#
# Only shapes with near-zero false-positive rates in ordinary prose. A loose
# NAME or ADDRESS pattern would reject good documents constantly, so those are
# not checked here -- the injected-value contract covers them.

# 2026-08-27 audit: this list covered 6 of 27 taxonomy labels, and in practice
# fired almost only on EMAIL -- 310 of 331 live leak rejections (94%) were
# EMAIL, 1 was MAC, and ZERO were Azerbaijan-specific because no pattern for
# them existed. An independent sweep of the 65,690-record corpus found 348
# records carrying real unlabeled PII that this gate had waved through,
# including a valid AZ_ID_CARD_NUMBER sitting in the GOLDEN reference corpus
# ("Şəxsiyyət vəsiqəsi də AB6947773-dür"). Every such record teaches a masking
# model a false negative, which is the most expensive error it can learn.
#
# Coverage is now every `pattern`-tier label, split by how much the SHAPE
# alone can be trusted:
#
#   _LEAK_PATTERNS   high-precision shapes, rejected on sight (subject to the
#                    confirmer below). A false positive here costs one
#                    regenerated document.
#   _LEAK_ANCHORED   shapes that collide with ordinary non-PII content --
#                    AZ_FIN is explicitly a hard-negative target against order
#                    IDs and git SHAs (schema.md), and a bare 10-digit AZ_VOEN
#                    is indistinguishable from a national phone number. These
#                    are only treated as leaks when a licensing word sits
#                    nearby, so the gate cannot collapse generation yield.
_LEAK_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Letters of any script, and `_` in the domain (P2-5, batch 4): the model
    # invents company mailboxes in Azerbaijani (`dəstək@hal-x.ai`,
    # `hüquq@şirkət.az`) and with underscored hosts (`support@bank_system.az`).
    # The ASCII-only shape saw none of them: 44 documents in clean batch 1,
    # 10, 13 and 8 in batches 2-4, all unlabelled invented PII.
    ("EMAIL", re.compile(
        r"(?<![\w.%+-])[\w.%+-]+@[\w-]+(?:\.[\w-]+)*\.[^\W\d_]{2,}(?![\w-])")),
    ("IPV4", re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\b")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
    ("AWS_KEY", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("BEARER", re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("MAC", re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")),
    # --- added 2026-08-27 -------------------------------------------------
    # The project's own generator mints these two forms; the AWS/BEARER
    # patterns above matched neither.
    ("API_KEY", re.compile(
        r"\b(?:sk-[A-Za-z0-9._-]{16,}|ghp_[A-Za-z0-9]{20,}|"
        r"xox[bapr]-[A-Za-z0-9-]{12,})")),
    ("ACCESS_TOKEN", re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("ICCID", re.compile(r"\b89\d{17,18}\b")),
    # Deliberately permissive: match any hex-and-colon run of plausible shape
    # and let ipv6_valid (plus the substance guard in _LEAK_CONFIRM) decide.
    # A stricter regex missed COMPRESSED addresses such as "2001:0db8::1",
    # which is precisely the form the project's own generator mints.
    ("IPV6", re.compile(r"\b[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,7}\b")),
    # url_with_token_valid only passes a URL that actually carries a
    # secret/PII-bearing token, which is what schema.md defines URL as.
    ("URL", re.compile(r"https?://[^\s<>\"'\)\]]+")),
    # AA/AB/DYI/MYI + 7 digits is specific enough to trust without an anchor.
    ("AZ_ID_CARD_NUMBER", re.compile(r"\b(?:AA|AB|DYI|MYI)\d{7}\b")),
]

# Shape alone is not enough -- a licensing word must sit within
# _LEAK_ANCHOR_WINDOW characters before treating the match as leaked PII.
_LEAK_ANCHORED: list[tuple[str, re.Pattern]] = [
    ("AZ_VOEN", re.compile(r"\b\d{10}\b")),
    ("AZ_FIN", re.compile(r"\b[0-9A-HJ-NP-Z]{7}\b")),
    ("AZ_PASSPORT_NUMBER", re.compile(r"\b[A-Z]\d{8}\b")),
    ("AZ_DRIVER_LICENSE_NUMBER", re.compile(r"\b[A-Z]{2}\d{6}\b")),
    ("TELEPHONENUM", re.compile(r"(?:\+994|\b0)(?:[ \-()]?\d){9}\b")),
    # D-51h: an ID card with any other two-letter prefix (the known ones are
    # trusted unanchored above); like the licence, only near an ID-card word
    ("AZ_ID_CARD_NUMBER", re.compile(r"\b[A-Z]{2}\d{7}\b")),
]

_LEAK_ANCHOR_WINDOW = 80
_LEAK_ANCHOR_WORDS: dict[str, re.Pattern] = {
    "AZ_VOEN": re.compile(r"(?i)(vöen|voen|vergi|mükellef|mukellef)"),
    "AZ_FIN": re.compile(r"(?i)(\bfin\b|f\.i\.n|şəxsiyyət|sexsiyyet|"
                         r"vəsiqə|vesiqe|\bpin\b)"),
    "AZ_PASSPORT_NUMBER": re.compile(r"(?i)(pasport|passport)"),
    "AZ_ID_CARD_NUMBER": re.compile(r"(?i)(şəxsiyyət|sexsiyyet|vəsiqə|vesiqe|id card)"),
    "AZ_DRIVER_LICENSE_NUMBER": re.compile(
        r"(?i)(sürücü|surucu|vəsiqə|vesiqe|licence|license)"),
    "TELEPHONENUM": re.compile(
        r"(?i)(telefon|nömr|nomr|mobil|zəng|zeng|əlaqə|elaqe|whatsapp|phone)"),
}

# Structural confirmation, so a shape match that cannot possibly be a real
# value is never reported. Keyed by the kind used above.
_LEAK_CONFIRM = {
    "IBAN": lambda v: _iban_ok(v),
    "ICCID": lambda v: CK.iccid_valid(v),
    # "16::40" is a structurally valid compressed IPv6 address AND a
    # noise-mangled timestamp ("16:40" with a doubled colon from the typos
    # kind) -- which is the only way it ever occurs here. ipv6_valid alone
    # cannot tell them apart, so require real address substance: at least 3
    # non-empty groups, one of them wider than 2 hex digits. That keeps
    # 2001:0db8::1 and 2001:1234:5678::1 (all-decimal but genuine) while
    # dropping 16::40 and 14::02:10. Deliberately also drops bare link-local
    # forms like fe80::1, which carry no identifying information anyway.
    "IPV6": lambda v: (CK.ipv6_valid(v)
                       and len([g for g in v.split(":") if g]) >= 3
                       and max((len(g) for g in v.split(":") if g), default=0) >= 3),
    "URL": lambda v: CK.url_with_token_valid(v),
    "ACCESS_TOKEN": lambda v: CK.access_token_valid(v),
    "PRIVATE_KEY": lambda v: True,
    "AZ_ID_CARD_NUMBER": lambda v: CK.az_id_card_valid(v),
    "AZ_PASSPORT_NUMBER": lambda v: CK.az_passport_valid(v),
    "AZ_DRIVER_LICENSE_NUMBER": lambda v: CK.az_driver_license_valid(v),
    "AZ_VOEN": lambda v: CK.az_voen_valid(v),
    # A real FIN is mixed alphanumeric; an all-letter run of 7 from the same
    # alphabet is an ordinary uppercase word ("HEADERS").
    "AZ_FIN": lambda v: (CK.az_fin_valid(v)
                         and any(c.isdigit() for c in v)
                         and any(c.isalpha() for c in v)),
}


def _leak_anchor_ok(kind: str, text: str, start: int, end: int) -> bool:
    """Is there a word nearby that licenses reading this shape as `kind`?

    NOTE: deliberately not `anchors.has_anchor` -- that returns True
    unconditionally for any label outside the anchor_required tier, so using
    it here would be a silent no-op (the 2026-08-27 audit made exactly that
    mistake in its own first draft and had to correct it).
    """
    pattern = _LEAK_ANCHOR_WORDS.get(kind)
    if pattern is None:
        return True
    lo = max(0, start - _LEAK_ANCHOR_WINDOW)
    hi = min(len(text), end + _LEAK_ANCHOR_WINDOW)
    return bool(pattern.search(text[lo:hi]))

# Shapes that legitimately appear unlabeled because we deliberately injected
# them as decoys, or that the hard-negative families produce.
_LEAK_EXEMPT = re.compile(
    r"^(?:0\.0\.0\.0|255\.255\.255\.\d{1,3}|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})$")


def _covered(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= start and end <= e for s, e in spans)


def _overlaps(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < e and s < end for s, e in spans)


def _trimmed(text: str, start: int, end: int) -> tuple[int, int]:
    """The match without the separators a pattern can swallow at its edges:
    the CARD pattern `(?:\\d[ -]?){13,19}` takes the space AFTER a number, so
    an untrimmed match ends one character past a declared decoy."""
    while end > start and text[end - 1] in " \t-":
        end -= 1
    while start < end and text[start] in " \t-":
        start += 1
    return start, end


def _span_pairs(spans) -> list[tuple[int, int]]:
    """(start, end) pairs from `_decoys` dicts or plain pairs."""
    return [(d["start"], d["end"]) if isinstance(d, dict) else (d[0], d[1])
            for d in spans or []]


def find_leaked_pii(text: str, entities: list[dict],
                    decoys: list[str] | None = None, *,
                    decoy_spans=None) -> list[str]:
    """Unlabeled substrings that look unmistakably like real PII.

    A match is exempt when it lies ENTIRELY inside a declared decoy span
    (C2 `_decoys`, P2-3). That covers the two cases string equality got
    wrong: a pattern matching only a prefix of the decoy (the MAC regex takes
    the first 17 characters of a colon-hex fingerprint), and a decoy the
    model regrouped (`4539 5787 6362 1486` for `4539578763621486`), because
    the span is located in the final text (negatives.locate_decoys).

    Exemption is by POSITION, never by string. The old rule exempted any
    match that merely CONTAINED a decoy's characters, so a planted port
    `443` exempted a real, unlabeled card `4532 4431 ...`, and any copy of a
    decoy string anywhere in the document was exempt. Now an undeclared copy
    of the same string is a leak, as in the translation harness.

    `decoy_spans` are the declared spans (dicts or (start, end) pairs).
    `decoys` is the older string form, still used by the translation harness:
    every standalone occurrence of each string counts as declared.
    """
    spans = [(e["start"], e["end"]) for e in entities]
    declared = _span_pairs(decoy_spans)
    for d in decoys or []:
        declared += decoy_occurrences(text, d, tolerant=True)
    leaks: list[str] = []

    # the tier decides whether a licensing word is needed: a kind may be in
    # both (AZ_ID_CARD_NUMBER: AA/AB/DYI/MYI on sight, other prefixes anchored)
    tiers = [(False, kp) for kp in _LEAK_PATTERNS] + [(True, kp) for kp in _LEAK_ANCHORED]
    for anchored, (kind, pattern) in tiers:
        for match in pattern.finditer(text):
            value = match.group(0)
            if _covered(match.start(), match.end(), spans):
                continue
            if _overlaps(match.start(), match.end(), spans):
                # Partially covered: usually a span boundary difference, not a
                # leak (e.g. we labeled "a@b.com" inside "<a@b.com>").
                continue
            if _covered(*_trimmed(text, match.start(), match.end()), declared):
                continue
            if _LEAK_EXEMPT.match(value):
                continue
            if kind == "CARD":
                digits = re.sub(r"\D", "", value)
                # Only flag a digit run if it is Luhn-valid; otherwise it is an
                # order number, a tracking code, or one of our own decoys.
                if len(digits) < 13 or not _luhn_ok(digits):
                    continue
            # Structural confirmation, where one exists. Mirrors the Luhn gate
            # on CARD: a shape match that fails its own checksum/format is an
            # adversarial near-miss or a reference code, not real PII.
            confirm = _LEAK_CONFIRM.get(kind)
            if confirm is not None:
                try:
                    if not confirm(value):
                        continue
                except Exception:
                    continue
            # Collision-prone shapes need a licensing word nearby.
            if anchored and not _leak_anchor_ok(kind, text, match.start(), match.end()):
                continue
            # A bare PEM armour header carries no secret. The generator mints
            # the OpenSSH body ("ssh-rsa AAAA...") and the model sometimes
            # wraps it in a PEM header the span does not cover -- a span
            # BOUNDARY question, not leaked PII. Only report the header when
            # the document has no labeled PRIVATE_KEY near it at all.
            if kind == "PRIVATE_KEY" and any(
                    e.get("label") == "PRIVATE_KEY"
                    and abs(e["start"] - match.end()) <= 300
                    for e in entities):
                continue
            leaks.append(f"{kind}:{value[:48]}")

    return leaks


# --- judgment-word leak ------------------------------------------------------
#
# A different failure mode than find_leaked_pii: not extra unlabeled PII, but
# the model editorializing about a decoy/hard-negative's validity instead of
# just using it as ordinary content -- "...lakin format yanlışdır" (but the
# format is wrong). Found in 9/22 negative-family cases in an early
# edge-case-catalog smoke test, traced to feeding the model prose that
# contained words like "invalid"/"wrong" describing why a value shouldn't be
# labeled; the model echoed that judgment straight into the generated text.

LEAK_WORDS = ["yanlış", "düzgün deyil", "səhv", "etibarsız", "keçərsiz",
              "invalid", "wrong", "incorrect"]


def find_judgment_leak(text: str) -> list[str]:
    """Words indicating the model commented on a value's correctness."""
    low = text.lower()
    return [w for w in LEAK_WORDS if w in low]


# --- taxonomy-label leak -----------------------------------------------------
#
# entities_to_embed hands the model 'LABEL: value' lines (dspy_generate.py's
# build_fields()) so it can locate each value. Found by manual review of real
# output (2026-08-24): the model sometimes takes the literal shortcut of
# echoing the whole line -- label name included -- into the document as if it
# were the field's own display name ("Ad: GIVENNAME: Fatimə", "Pasport
# məlumatı: AZ_PASSPORT_NUMBER: O69367632") instead of translating it into a
# natural field label. A real production document never contains the
# taxonomy's internal label string.
#
# Restricted to labels with no legitimate real-world/technical reading of
# their own name -- IBAN, ICCID, URL, EMAIL, MAC_ADDRESS, API_KEY,
# ACCESS_TOKEN and PRIVATE_KEY are all real terms a genuine document
# (including a config/log snippet) can say verbatim, so they are
# deliberately not checked here; flagging them would reject good documents,
# not leaks.
TAXONOMY_LABEL_LEAK_CHECK = frozenset({
    "GIVENNAME", "SURNAME", "BUILDINGNUM", "TELEPHONENUM", "ZIPCODE", "AGE",
    "CITY", "STREET", "DATE", "TIME", "CARD_SECURITY_CODE",
    "PAYMENT_CARD_NUMBER", "IPV4_ADDRESS", "IPV6_ADDRESS",
    "AZ_FIN", "AZ_ID_CARD_NUMBER", "AZ_PASSPORT_NUMBER", "AZ_VOEN",
    "AZ_DRIVER_LICENSE_NUMBER",
})


def find_label_name_leak(text: str, entities: list[dict]) -> list[str]:
    """Literal taxonomy label tokens written into the text as a fake field
    name, instead of a natural field label in the target language."""
    spans = [(e["start"], e["end"]) for e in entities]
    hits: list[str] = []
    for label in TAXONOMY_LABEL_LEAK_CHECK:
        # The label as a token: no letter or digit on either side. Matched as
        # a bare substring, `AGE` fired inside AGENT/MESSAGE/STORAGE, `TIME`
        # inside TIMESTAMP/TIMEOUT and `DATE` inside UPDATE -- 158 of batch
        # 1's 205 rejections here (P2-6). `_` stays a boundary, so a key such
        # as REG_DATE or ATTR_GIVENNAME is still caught.
        for m in re.finditer(r"(?<![A-Za-z0-9])" + re.escape(label) + r"(?![A-Za-z0-9])", text):
            if _overlaps(m.start(), m.end(), spans):
                continue
            hits.append(label)
    return hits


def _iban_ok(value: str) -> bool:
    """ISO 13616 mod-97 check."""
    v = re.sub(r"[\s-]", "", value).upper()
    if len(v) < 15 or not v[:2].isalpha() or not v[2:4].isdigit():
        return False
    rearranged = v[4:] + v[:4]
    total = 0
    for ch in rearranged:
        if ch.isdigit():
            total = (total * 10 + ord(ch) - 48) % 97
        elif ch.isalpha():
            total = (total * 100 + ord(ch) - 55) % 97
        else:
            return False
    return total == 1


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = ord(ch) - 48
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# --- near-duplicate detection ----------------------------------------------

_WS = re.compile(r"\s+")
_DIGITS = re.compile(r"\d+")


def normalize_for_similarity(text: str, entities: list[dict]) -> str:
    """Mask entity values and digits, collapse whitespace, lowercase.

    Masking matters: two documents built from the same prose skeleton with
    different injected values are the *same* document for diversity purposes,
    and comparing raw text would score them as distinct.
    """
    spans = sorted(((e["start"], e["end"]) for e in entities), reverse=True)
    chars = list(text)
    for start, end in spans:
        chars[start:end] = [" "]
    masked = "".join(chars)
    masked = _DIGITS.sub("#", masked)
    return _WS.sub(" ", masked).strip().lower()


def _stable_hash(s: str) -> int:
    """Deterministic 64-bit hash.

    Python's builtin `hash()` is salted per interpreter process (PYTHONHASH-
    SEED), so shingle sets -- and therefore every similarity score derived
    from them -- were reproducible within a run and different across runs.
    That made a duplicate-rate regression impossible to bisect and made the
    `--seed` flag's determinism promise incomplete. blake2b at 8 bytes is
    fast enough here: the cost is dominated by the per-character slicing.
    """
    return int.from_bytes(
        hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")


def shingles(text: str, size: int = 5) -> set:
    """Character n-grams, hashed to keep the set small.

    Stable across processes -- see `_stable_hash`.
    """
    if len(text) <= size:
        return {_stable_hash(text)}
    return {_stable_hash(text[i:i + size]) for i in range(len(text) - size + 1)}


class SimilarityIndex:
    """Rejects documents too similar to ones already accepted.

    Exact duplicates are caught by hash. Near-duplicates use Jaccard over
    character shingles against a bounded window of recent documents, which
    keeps the check O(window) per candidate instead of O(n) over the whole
    dataset -- the difference between usable and unusable at 100k documents.
    """

    def __init__(self, threshold: float = 0.82, window: int = 600) -> None:
        self.threshold = threshold
        self.window = window
        self._hashes: set[str] = set()
        self._recent: deque = deque(maxlen=window)

    def __len__(self) -> int:
        return len(self._hashes)

    @staticmethod
    def _digest(normalized: str) -> str:
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def check(self, normalized: str) -> tuple[bool, float]:
        """Return (is_duplicate, best_similarity)."""
        digest = self._digest(normalized)
        if digest in self._hashes:
            return True, 1.0

        candidate = shingles(normalized)
        if not candidate:
            return False, 0.0

        best = 0.0
        for other in self._recent:
            if not other:
                continue
            inter = len(candidate & other)
            if not inter:
                continue
            union = len(candidate) + len(other) - inter
            score = inter / union if union else 0.0
            if score > best:
                best = score
                if best >= self.threshold:
                    return True, best
        return False, best

    def add(self, normalized: str) -> None:
        self._hashes.add(self._digest(normalized))
        self._recent.append(shingles(normalized))


# ---------------------------------------------------------------------------
# Global near-duplicate detection
# ---------------------------------------------------------------------------

_MINHASH_PERMS = 96
_LSH_ROWS = 4                       # bands = 96/4 = 24
_MERSENNE = (1 << 61) - 1
# Shingles processed per numpy block. 512 x 96 uint64 = 384 KB peak,
# independent of document length.
_CHUNK = 512


def _perm_params(count: int = _MINHASH_PERMS
                 ) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Fixed (a, b) coefficients for the MinHash permutation family.

    Derived from a constant seed rather than `random` so two processes --
    and two runs weeks apart -- build identical signatures. A signature that
    changed between runs would silently make a resumed run's index
    incompatible with the rows already in the output file.
    """
    rng = random.Random(0x9E3779B97F4A7C15)
    a = tuple(rng.randrange(1, _MERSENNE) for _ in range(count))
    b = tuple(rng.randrange(0, _MERSENNE) for _ in range(count))
    return a, b


_PERM_A, _PERM_B = _perm_params()


class GlobalSimilarityIndex:
    """Near-duplicate detection across the WHOLE corpus, not a recent window.

    `SimilarityIndex` compares each candidate against the last `window` (600)
    accepted documents, which makes it structurally incapable of catching a
    duplicate pair separated by more than that. The audit's global MinHash
    sweep found 0 such pairs in 28,560 documents, so the window has never
    actually cost anything -- but "we have never needed it" is not a property
    that survives a 3x increase in corpus size, and the failure mode is
    silent.

    Design: MinHash signatures + LSH banding. Only documents sharing a full
    band of the signature are ever compared, so cost per candidate does not
    grow with the corpus.

    Memory is the part worth being careful about, and the first version of
    this class got it wrong. It kept every document's full shingle SET so it
    could compute exact Jaccard -- roughly 1,000 Python ints per document,
    which is ~1.3 GB at 32k documents and ~4 GB at 100k, and it duly failed
    to allocate partway through a 32,524-document sweep.

    Signatures alone are kept instead, in one contiguous uint64 array:
    `perms` x 8 bytes per document, so 768 B/doc -- 25 MB at 32k, 77 MB at
    100k. Bounded and predictable.

    The cost of dropping the shingle sets is that Jaccard becomes an
    ESTIMATE: the fraction of signature positions where two documents agree
    is an unbiased estimator of their Jaccard similarity, with standard error
    ~sqrt(J(1-J)/perms) -- about 0.039 at J=0.82 with 96 permutations. That
    is the standard MinHash trade and it is appropriate here, because this is
    a screening threshold, not a measurement. Exact duplicates are still
    caught exactly, by hash, before any estimation happens.
    """

    def __init__(self, threshold: float = 0.82,
                 perms: int = _MINHASH_PERMS, rows: int = _LSH_ROWS) -> None:
        self.threshold = threshold
        self.perms = perms
        self.rows = rows
        self.bands = perms // rows
        self._hashes: dict[str, str] = {}          # exact digest -> doc id
        self._ids: list[str] = []                  # row index -> doc id
        self._buckets: dict[tuple, list] = {}      # (band, key) -> [row index]
        self._counter = 0
        self._rows_used = 0
        if _np is not None:
            self._a = _np.array(_PERM_A[:perms], dtype=_np.uint64)
            self._b = _np.array(_PERM_B[:perms], dtype=_np.uint64)
            self._sigs = _np.zeros((1024, perms), dtype=_np.uint64)
        else:
            self._sigs = []

    def __len__(self) -> int:
        return self._rows_used

    @staticmethod
    def _digest(normalized: str) -> str:
        return hashlib.sha1(normalized.encode("utf-8")).hexdigest()

    def _signature(self, shs: frozenset):
        """MinHash signature: min over shingles, for each of `perms` hashes.

        Vectorized through numpy when available. The pure-Python fallback is
        correct but does perms x |shingles| modular multiplications per
        document, which does not finish in reasonable time at 100k.
        """
        if _np is None:
            if not shs:
                return tuple([0] * self.perms)
            return tuple(min(((_PERM_A[i] * x + _PERM_B[i]) % _MERSENNE)
                             for x in shs) for i in range(self.perms))
        if not shs:
            return _np.zeros(self.perms, dtype=_np.uint64)
        values = _np.fromiter(shs, dtype=_np.uint64, count=len(shs))
        # Chunked so peak memory is O(perms x _CHUNK) rather than
        # O(perms x |shingles|), independent of document length.
        best = _np.full(self.perms, _MERSENNE, dtype=_np.uint64)
        for start in range(0, values.size, _CHUNK):
            block = values[start:start + _CHUNK]
            prod = (self._a[:, None] * block[None, :]) % _MERSENNE
            prod += self._b[:, None]
            prod %= _MERSENNE
            _np.minimum(best, prod.min(axis=1), out=best)
        return best

    def _band_keys(self, sig):
        for band in range(self.bands):
            chunk = sig[band * self.rows:(band + 1) * self.rows]
            yield (band, tuple(int(x) for x in chunk))

    def _grow(self) -> None:
        if _np is None:
            return
        if self._rows_used < self._sigs.shape[0]:
            return
        bigger = _np.zeros((self._sigs.shape[0] * 2, self.perms),
                           dtype=_np.uint64)
        bigger[:self._rows_used] = self._sigs[:self._rows_used]
        self._sigs = bigger

    def check(self, normalized: str) -> tuple[bool, float, str]:
        """Return (is_duplicate, estimated_similarity, matching_doc_id)."""
        digest = self._digest(normalized)
        if digest in self._hashes:
            return True, 1.0, self._hashes[digest]

        shs = frozenset(shingles(normalized))
        if not shs:
            return False, 0.0, ""

        sig = self._signature(shs)
        seen: set = set()
        for key in self._band_keys(sig):
            seen.update(self._buckets.get(key, ()))
        if not seen:
            return False, 0.0, ""

        best, best_row = 0.0, -1
        if _np is not None:
            rows = _np.fromiter(seen, dtype=_np.int64, count=len(seen))
            agree = (self._sigs[rows] == sig[None, :]).mean(axis=1)
            idx = int(agree.argmax())
            best, best_row = float(agree[idx]), int(rows[idx])
        else:
            for row in seen:
                other = self._sigs[row]
                score = sum(1 for x, y in zip(sig, other) if x == y) / self.perms
                if score > best:
                    best, best_row = score, row
        match = self._ids[best_row] if best_row >= 0 else ""
        return best >= self.threshold, best, match

    def add(self, normalized: str, doc_id: str = "") -> str:
        if not doc_id:
            self._counter += 1
            doc_id = f"_auto_{self._counter:08d}"
        digest = self._digest(normalized)
        self._hashes.setdefault(digest, doc_id)
        sig = self._signature(frozenset(shingles(normalized)))
        self._grow()
        row = self._rows_used
        if _np is not None:
            self._sigs[row] = sig
        else:
            self._sigs.append(sig)
        self._ids.append(doc_id)
        self._rows_used += 1
        for key in self._band_keys(sig):
            self._buckets.setdefault(key, []).append(row)
        return doc_id


# --- PII the model invented ---------------------------------------------------
#
# The brief plans every value, and only planned values are labelled; a city,
# street, name or building number the model adds on its own is therefore
# unlabelled by construction -- and an unlabelled real name teaches the model
# to skip names. Measured: 9.0% of batch 1's clean documents and 2.8% of batch
# 2's carried one (P2-5). D-15c (2026-10-03): such documents are dropped in
# cleaning (clean_llm_batch.py --drop-unplanned-pii) and rejected at
# generation (quality_filter.screen_record(invented=True)). A city inside an
# organisation's name (`Bakı Dövlət Universiteti`) counts too: D-15c weighed
# those (about 1 hit in 4 of its sample) and chose to drop, since a wrongly
# dropped document costs one document and an unlabelled real city teaches
# the model to skip cities.
#
# High-precision shapes only, outside every label and declared decoy:
#   * a gazetteer city;
#   * `<Capitalised name> küçəsi/prospekti/döngəsi/küç./pr.`, also folded or
#     misspelt (`küçesi`, `kucesi`, `kuçəsi`, `dongesi`): 38 invented streets
#     in the clean batches 1-5 were written so (P2-5 batch 5);
#   * `bina N`;
#   * a pool given name directly before a surname-shaped word (`Alxan
#     Zeynullayev`). Pool names alone are too often ordinary words (Dünya,
#     İnsan, Hüquq) -- an undercount, on purpose.
_STREET_SHAPE = re.compile(
    r"(?<!\w)((?:[A-ZƏÖÜÇŞĞİ][\wəöüçşğı.-]*\s+){1,3})"
    r"((?:k[uü][cç][eə]s[iı]|prospekt[iı]|d[oö]ng[eə]s[iı])\w*|k[uü][cç]\.|pr\.)")
_BUILDING_SHAPE = re.compile(r"(?i)(?<!\w)bina\s*(?:№\s*)?(\d{1,4})(?!\d)")
_WORD_RE = re.compile(r"[^\W\d_]+")
_SURNAME_AFTER = re.compile(
    r"[ \t]+[A-ZƏÖÜÇŞĞİ][a-zəöüçşğıi]+(?:ov|ova|yev|yeva|ev|eva|li|lı|lu|lü|zadə|oğlu|qızı)(?!\w)")
# D-51i: after a given name that is an ordinary word too (`Sənaye`, `Şəhər`,
# `Server`), `-li/-lu` is an adjective or a possessive (`Sənaye Tipli`,
# `Şəhər Filialı`, `Server Modulu`), not a surname: only these endings count
_STRONG_SURNAME_AFTER = re.compile(
    r"[ \t]+[A-ZƏÖÜÇŞĞİ][a-zəöüçşğıi]+(?:ov|ova|yev|yeva|ev|eva|zadə|oğlu|qızı)(?!\w)")


def _invented_resources():
    """(place keys, given-name keys, common words), built once.

    D-51i: every key is `resolver.match_key` (lower-cased AND diacritic-
    folded), not `casefold`: `"BAKI".casefold()` is `baki`, which never met
    `bakı`, so ALL-CAPS cities and ASCII spellings (`Gence`) passed. The
    places are the 4,422-place pool (cities, districts, settlements; Person
    4's `v4_clean` lexicon), not the 97 cities."""
    global _INVENTED
    if _INVENTED is None:
        from ..locales import LOCALES
        from ..resolver import match_key
        from ..v4_clean import lexicon
        try:
            from ..targeted import homographs_az as H
        except ImportError:
            from ..targeted import homographs_az_stub as H
        lex = lexicon()
        places = set(lex.city_bases) | {match_key(c) for loc in LOCALES.values() for c in loc.cities}
        # the foreign given names too (P2-15): `Anna Petrova` added by the
        # model is as unlabelled as `Aynur Əliyeva`
        names = {match_key(n) for loc in LOCALES.values()
                 for n in list(loc.first_names_m) + list(loc.first_names_f)
                 + (loc.foreign_names.given_names() if loc.foreign_names else [])}
        common = frozenset(match_key(w) for w in
                           list(LOCALES["az"].stopwords) + list(H.LONE_WORDS)
                           + list(PLACE_COMMON_WORDS))
        _INVENTED = (frozenset(places), frozenset(names), common)
    return _INVENTED


# D-51i: place names of the pool that the LLM batches write as ordinary words
# (`Sənaye`, `İcarə`, `Səbir`: villages too), capitalised at a sentence start
# or in a heading. Built from the clean batches 1-6 by
# reports/d51i/build_place_common_words.py.
def _place_common_words() -> list[str]:
    from pathlib import Path
    path = Path(__file__).with_name("place_common_words.txt")
    if not path.exists():
        return []
    return [line.split("\t")[0] for line in path.read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")]


PLACE_COMMON_WORDS: tuple[str, ...] = tuple(_place_common_words()) + (
    # names in the pool that LLM text uses for a sea, a river, a mountain, a
    # direction or a brand far more than for the settlement (`Xəzər dənizi`,
    # `Xəzər Bank`, `Araz çayı`, `Şərq`, `Turan`, `Şahdağ`), and `İnstitut`
    "xezer", "araz", "serq", "turan", "sahdag", "institut", "institute")
# a place name of under 4 letters is far more often an acronym or another
# word (`SIM`, `HAL`, `Bad Request`) than a village
PLACE_MIN_LEN = 4
# a place followed by one of these names an organisation, not a place the
# model invented (`Xəzər Loqistika`, `"Araz Mebel"`, `Sənaye Təchizatçısı ASC`)
_ORG_AFTER = re.compile(
    r"[\"'»”]?[ \t]+(?:[\w-]+[ \t]+){0,2}(?:MMC|ASC|QSC|SC|LLC|Ltd|Inc|Bank|Holding|Holdinq|Group|Qrup|"
    r"Loqistika|Logistika|Mebel|Tekstil|Market|Servis|Tikinti|Aptek|Supermarket|Mall|Plaza|Hotel|"
    r"Otel|Restoran|Kafe|Studio|Media|Telecom|Telekom|Sığorta|Siğorta|Insurance|Energy|Enerji|"
    r"Təchizatçısı|Şirkəti|Sirketi|Company)(?![\w])")


_INVENTED = None


def find_invented_pii(text: str, entities: list[dict], decoy_spans=(),
                      doc_type: str | None = None) -> list[dict]:
    """PII-shaped strings no label and no declared decoy covers: a place, a
    street, a building number, a full name, a persona name or an age the
    model added on its own. Each finding: label, text, start, end. Should be
    [] in a training record. `doc_type` tells the persona detectors whether
    the document is a chat (speaker tags without timestamps)."""
    from ..resolver import match_key
    from ..v4_clean import _CASE_END, _inflected, _institution_after
    from .specs import common_word_keys
    places, names, common = _invented_resources()
    name_words = common_word_keys()
    covered = [(e["start"], e["end"]) for e in entities] + [tuple(d) for d in decoy_spans]

    def free(s: int, e: int) -> bool:
        return not any(a < e and s < b for a, b in covered)

    out = []
    for m in _WORD_RE.finditer(text):
        w, s, e = m.group(0), m.start(), m.end()
        if not w[:1].isupper() or not free(s, e):
            continue
        k = match_key(w)
        # A given name before a surname is a full name first, even when the
        # word is a common word or a place too: `Murad Məmmədov`, `Ümid
        # Əliyev` (P4-2; `Ümid` is a village of the 4,422-place pool as well).
        if k in names and len(w) > 3:
            after = (_STRONG_SURNAME_AFTER if k in name_words or k in common else _SURNAME_AFTER).match(text, e)
            if after and free(e, after.end()):
                out.append({"label": "GIVENNAME", "text": text[s:after.end()],
                            "start": s, "end": after.end()})
                continue
        # D-51i: a place in any case (`Bakının`, `Şüvəlanda`) and spelling
        # (`GƏNCƏ`, `Gence`); not an ordinary word, and not one heading an
        # institution or project (`Salyan Rayon Məhkəməsi`: D-2, the R6)
        # or an organisation (`Xəzər Loqistika`).
        if (k in places or _inflected(k, places)) and len(k) >= PLACE_MIN_LEN:
            stem_common = k in common or any(k.endswith(x) and k[:-len(x)] in common for x in _CASE_END)
            if (not stem_common and _institution_after(text, e) is None
                    and not _ORG_AFTER.match(text, e)):
                out.append({"label": "CITY", "text": w, "start": s, "end": e})
    for m in _STREET_SHAPE.finditer(text):
        if free(m.start(), m.end()):
            out.append({"label": "STREET", "text": m.group(0), "start": m.start(), "end": m.end()})
    for m in _BUILDING_SHAPE.finditer(text):
        if free(m.start(1), m.end(1)):
            out.append({"label": "BUILDINGNUM", "text": m.group(0), "start": m.start(),
                        "end": m.end()})
    persona = _persona_and_age(text, entities, covered, doc_type)
    # one finding per value: a name the persona rules place is not also a
    # place (`[10:15] Babek:`, Babək is a district too), and a name the
    # full-name rule already reported is not reported again
    names_at = [(f["start"], f["end"]) for f in persona if f["start"] >= 0]
    out = [f for f in out if not (f["label"] == "CITY" and any(
        a < f["end"] and f["start"] < b for a, b in names_at))]
    have = [(f["start"], f["end"]) for f in out]
    out += [f for f in persona if f["start"] < 0 or not any(
        a <= f["start"] and f["end"] <= b for a, b in have)]
    return out


def _persona_and_age(text: str, entities: list[dict], covered: list, doc_type: str | None) -> list[dict]:
    """D-51i: chat speakers (`[10:15] Babek:`), self-introductions (`Mən
    Leyla, ...`), signatures (`Hörmətlə,\nAynur Quliyeva`), `From:` headers,
    `S. Surname`, a given name half-labelled before its surname, and an age
    (`Yaş: 32`, `52 yaşında`) nobody labelled. The detectors are the team's
    cleaning rules R4, R5 and R9 (`v4_clean`), run on the record as it
    stands: whatever they would label, or drop as an unplaceable name, the
    model invented. One definition for generation and cleaning."""
    from ..v4_clean import clean_doc_detail
    doc = {"id": "invented-check", "text": text, "_doc_type": doc_type,
           "entities": [{"start": e["start"], "end": e["end"], "label": e["label"]} for e in entities],
           "_decoys": [{"start": a, "end": b, "kind": "declared"} for a, b in covered
                       if not any(a == e["start"] and b == e["end"] for e in entities)]}
    result = clean_doc_detail(doc)
    out = []
    for c in result.changes:
        if c.rule in ("R4", "R5", "R9") and c.action == "label":
            out.append({"label": c.label, "text": c.text, "start": c.start, "end": c.end,
                        "rule": f"{c.rule} {c.note}".strip()})
        elif c.rule == "R4" and c.action == "drop":
            out.append({"label": "GIVENNAME", "text": c.note, "start": -1, "end": -1,
                        "rule": "R4 unplaceable"})
    return out
