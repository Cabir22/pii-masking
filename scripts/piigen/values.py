"""ValueFactory -- every entity value in the pipeline is minted here.

Three guarantees, each of which fixes a specific finding from the audit:

  1. **Checksum-valid where a checksum exists.** Cards pass Luhn and carry a
     real issuer prefix, IBANs pass mod-97 with correct per-country length,
     ICCIDs pass Luhn. Where the source taxonomy says a check digit is
     unverified (AZ_VOEN), no checksum is invented -- see `az_voen()`.
  2. **Never a placeholder, never a benchmark or shadow value.** Every value
     is screened against `blocklist` before it is returned, so no test card,
     documentation key, 555 number or fictional address can enter the
     dataset; and against the leakage guard (`leak_screen`), so no value the
     guard would fail on is ever minted.
  3. **Deduplicated with a persistent pool.** The pool persists to disk and
     enforces a hard ceiling on how often any value may repeat.

Entropy is the design target throughout: sampling the address space directly
(rather than from a hand-written list) bounds distinctness by the number of
draws, not by list size.
"""

from __future__ import annotations

import math
import base64
import calendar
import collections
import importlib.util
import ipaddress
import json
import logging
import os
import random
import re
import string
import sys
import tempfile
import uuid
from pathlib import Path

from . import checksums as CK
from .blocklist import is_blocked, has_password_keyword
from .leak_screen import is_forbidden

log = logging.getLogger("piigen.values")
from .locales import LOCALES


# ---------------------------------------------------------------------------
# Persistent, capped value pool
# ---------------------------------------------------------------------------

# Share of a label's draws that may exceed its repeat cap before the pool is
# considered unhealthy. Exceeding the cap is not itself an error -- it is the
# pool honestly reporting that the underlying list cannot cover the requested
# volume -- but past these shares the label's values are being memorised
# rather than learned, and continuing produces degraded output.
#
# The audit simulated the real ValueFactory at 100k documents and measured
# 31,322 over-cap CITY draws (CITY reuse 324x, "Baki" taking 45.19% of all
# mentions) and 12,793 for AGE. Both would have tripped `stop` here long
# before the run finished; instead the pool warned once and continued.
POOL_WARN_SHARE = 0.02
# 2026-08-26: labels whose real-world value space is genuinely finite --
# ~97 Azerbaijani cities, ~95 plausible human ages, 253 real postal codes --
# not merely small in our data. No amount of pool engineering creates more.
#
# `over_cap_share` (draws exceeding the flat max_share cap) is the wrong
# signal for these: for AGE, a perfectly UNIFORM draw already puts each of
# the 95 values at 1/95 = 1.053% share, which is already 2.6x over the
# global 0.4% max_share -- so over_cap_share approaches 100% almost
# immediately by construction, regardless of volume, and regardless of how
# healthy the actual distribution is. Confirmed live: a resumed run halted
# after batch 1 on "pool_over_cap_share=1" for AGE with only 4,376
# cumulative AGE draws on record, nowhere near real generation volume.
#
# `scripts/simulate_pools.py` already worked this out independently and
# judges these three labels by concentration (does one value dominate?)
# and tail coverage instead of reuse/over-cap-share -- this constant and
# `health()`'s branch below bring that same judgment into the LIVE stop
# gate, which simulate_pools.py's analysis never fed back into. Kept here
# (not duplicated in simulate_pools.py) as the one place a label's
# liveness-check kind is decided.
FINITE_BY_NATURE = {"CITY", "ZIPCODE", "AGE"}
# Below this many total draws, top_share is sample noise, not a signal: one
# value drawn once out of one total draw IS 100% of the total, trivially.
# Caught by the fake-generator pipeline tests (tiny batches, 8-30 examples)
# instantly self-tripping "stop" on batch 1 purely from having only 1-2
# AGE/CITY/ZIPCODE draws on record -- nowhere near real concentration.
MIN_CONCENTRATION_SAMPLE = 50
POOL_STOP_SHARE = 0.10


class ValuePool:
    """Tracks emitted values so the dataset cannot memorise any single string."""

    def __init__(self, max_share: float = 0.004, state_path: str | None = None,
                 attempts: int = 24, warn_share: float = POOL_WARN_SHARE,
                 stop_share: float = POOL_STOP_SHARE) -> None:
        self.counts: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        self.max_share = max_share
        self.attempts = attempts
        self.state_path = Path(state_path) if state_path else None
        self.collisions = 0
        self.exhausted = collections.Counter()
        # Per-label draw accounting. `exhausted` counts how many times fresh()
        # gave up entirely; `over_cap` counts every draw that was actually
        # emitted above its cap, which is the quantity the stop condition
        # needs -- a label can be quietly repeating past cap on most draws
        # while only occasionally exhausting every attempt.
        self.draws = collections.Counter()
        self.over_cap = collections.Counter()
        # Values re-drawn because the leakage guard would fail on them.
        self.leak_redraws = collections.Counter()
        self.warn_share = warn_share
        self.stop_share = stop_share
        # `exhausted` was tracked but never read anywhere in the codebase --
        # confirmed by audit before adding this warning, not assumed. A label
        # only lands here once every attempt in fresh() failed to find a
        # value under its cap, meaning the pool is too small for the current
        # volume and every draw from here on repeats past max_share silently.
        # One warning per label per pool lifetime -- loud enough to notice,
        # not spammy across tens of thousands of subsequent calls.
        self._warned_exhausted: set[str] = set()
        if self.state_path and self.state_path.exists():
            self.load()

    # -- persistence ------------------------------------------------------
    def load(self) -> None:
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        for label, values in data.items():
            self.counts[label] = collections.Counter(values)

    def save(self) -> None:
        """Persist atomically: temp file, fsync, rename.

        `write_text` is not atomic. This file is the only record that a value
        has already been used, it is rewritten in full on every save, and it is
        gitignored -- so a crash mid-write silently resets every cross-run
        dedup guarantee with no error anywhere.
        """
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: dict(v) for k, v in self.counts.items()}
        fd, tmp = tempfile.mkstemp(dir=str(self.state_path.parent),
                                   prefix=".valuepool-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.state_path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    # -- allocation -------------------------------------------------------
    def _cap(self, label: str, weight: float = 1.0) -> int:
        total = sum(self.counts[label].values())
        # allow a value to repeat only once the label has enough mentions that
        # the repeat stays under max_share. `weight` scales this per-value --
        # see fresh()'s weight_fn -- so a value the caller deliberately
        # oversamples (a capital city, weighted for realism) is allowed a
        # proportionally higher cap instead of the flat cap immediately
        # fighting the oversampling and silently flattening it back to
        # near-uniform.
        return max(1, int(total * self.max_share * weight))

    def fresh(self, label: str, factory, weight_fn=None) -> str:
        """Draw a value that is unused (or under its repeat cap) and not blocked.

        `weight_fn`, if given, maps a candidate value to its relative
        sampling weight (1.0 = average). Without it every value gets the
        same flat cap, as before.
        """
        fallback = None
        self.draws[label] += 1
        for _ in range(self.attempts):
            value = factory()
            if not value:
                continue
            if is_blocked(value):
                continue
            # A value the leakage guard would fail (a benchmark or shadow
            # value, A2 rules 3 and 5) is re-drawn like a placeholder.
            if is_forbidden(value):
                self.leak_redraws[label] += 1
                continue
            # Only an UNBLOCKED value may become the fallback. Assigning before
            # the screen let the exhaustion path below return a known
            # placeholder, which then surfaced downstream as an unexplained
            # validator rejection rather than as a pool problem.
            if fallback is None:
                fallback = value
            cap = self._cap(label, weight_fn(value) if weight_fn else 1.0)
            if self.counts[label][value] < cap:
                self.counts[label][value] += 1
                return value
            self.collisions += 1
        # Exhausted: record it honestly rather than silently emitting a dup.
        self.exhausted[label] += 1
        if label not in self._warned_exhausted:
            self._warned_exhausted.add(label)
            log.warning(
                "value pool exhausted for %s: only %d distinct value(s) on "
                "record cannot cover the current volume under max_share=%.4f "
                "-- every draw for this label will now repeat past its cap "
                "until the pool is expanded.",
                label, self.distinct(label), self.max_share)
        value = fallback
        if value is None:
            for _ in range(self.attempts):
                candidate = factory()
                if candidate and not is_blocked(candidate) and not is_forbidden(candidate):
                    value = candidate
                    break
        if value is None:
            return ""
        self.counts[label][value] += 1
        self.over_cap[label] += 1
        return value

    def record(self, label: str, value: str) -> None:
        self.counts[label][value] += 1

    def distinct(self, label: str) -> int:
        return len(self.counts[label])

    # -- health -----------------------------------------------------------
    def health(self, label: str) -> dict:
        """Draw statistics and warn/stop status for one label."""
        draws = self.draws[label]
        over = self.over_cap[label]
        share = (over / draws) if draws else 0.0
        counter = self.counts[label]
        total = sum(counter.values())
        top_value, top_count = (counter.most_common(1) or [("", 0)])[0]
        top_share = (top_count / total) if total else 0.0
        # FINITE_BY_NATURE labels: over_cap_share is expected to run high by
        # construction (see the constant's comment above) and is not a
        # health signal for them. Judge by concentration instead -- the
        # same axis scripts/simulate_pools.py already uses for these labels
        # -- but only once there is enough volume for concentration to mean
        # anything (see MIN_CONCENTRATION_SAMPLE).
        if label in FINITE_BY_NATURE and total >= MIN_CONCENTRATION_SAMPLE:
            judged_share = top_share
        elif label in FINITE_BY_NATURE:
            judged_share = 0.0
        else:
            judged_share = share
        if judged_share > self.stop_share:
            status = "stop"
        elif judged_share > self.warn_share:
            status = "warn"
        else:
            status = "ok"
        return {
            "label": label,
            "draws": draws,
            "distinct": len(counter),
            "over_cap": over,
            "over_cap_share": share,
            "exhausted": self.exhausted[label],
            "reuse": (total / len(counter)) if counter else 0.0,
            "top_value": top_value,
            "top_share": top_share,
            # The metric `status` above was actually judged on -- callers
            # that reduce across labels (e.g. "what's the worst share right
            # now") should use this, not raw `over_cap_share`, or they
            # silently reintroduce the FINITE_BY_NATURE false-positive this
            # method exists to avoid.
            "judged_share": judged_share,
            "status": status,
        }

    def health_report(self) -> dict:
        """Run-level rollup. `status` is the worst status of any label."""
        labels = sorted(set(self.draws) | set(self.counts))
        per_label = {lab: self.health(lab) for lab in labels}
        stop_labels = sorted(l for l, h in per_label.items()
                             if h["status"] == "stop")
        warn_labels = sorted(l for l, h in per_label.items()
                             if h["status"] == "warn")
        status = "stop" if stop_labels else ("warn" if warn_labels else "ok")
        return {
            "status": status,
            "stop_labels": stop_labels,
            "warn_labels": warn_labels,
            "labels": per_label,
            "warn_share": self.warn_share,
            "stop_share": self.stop_share,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALNUM = string.ascii_letters + string.digits
_LOWER_NUM = string.ascii_lowercase + string.digits
_B64URL = _ALNUM + "-_"
_HEX = "0123456789abcdef"

# ACCESS_TOKEN and API_KEY can share a body shape; the prefix and the anchor
# word around the value are what separate them. The benchmark's 385 missed
# ACCESS_TOKENs were all `at_`/`bearer_`/`tok_` tokens, 229 of them read as
# API_KEY, while every training token was one JWT-like shape (P2-1). No prefix
# in one list may start, or be started by, a prefix in the other --
# piigen/test_value_formats.py asserts it.
ACCESS_TOKEN_PREFIXES = ("at_", "bearer_", "tok_", "oauth_", "sess_", "atk-", "pat_")
API_KEY_PREFIXES = (
    # vendor
    "sk_live_", "sk_test_", "pk_live_", "rk_", "ghp_", "gho_", "github_pat_",
    "AKIA", "ASIA", "xoxb-", "xapp-1-", "AIza", "glpat-", "npm_", "dop_v1_",
    "SG.", "shpat_", "sq0atp-",
    # generic, vendor-neutral
    "key_", "api_", "apikey_", "svc_", "sk-live-", "sk-test-",
)
_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    "ə": "e", "ı": "i", "ö": "o", "ü": "u", "ç": "c", "ş": "s", "ğ": "g",
    "İ": "i", "i̇": "i", "ð": "d", "þ": "t",
}


def translit(s: str) -> str:
    out = []
    for ch in s.lower():
        out.append(_TRANSLIT.get(ch, ch))
    return "".join(c for c in "".join(out) if c.isascii())


def _rand(rng: random.Random, alphabet: str, k: int) -> str:
    return "".join(rng.choice(alphabet) for _ in range(k))


# --- name spelling and script variants (P2-4b) -----------------------------
#
# The same person is written `Məmmədov`, `Mammadov` (the English / passport
# spelling) or `Маммадов` (Cyrillic, from Russian-language paperwork). The
# corpus only ever had the first. scripts/name_transliterators.py already
# implements the script conversions for cross-language name substitution; it
# is loaded by path so this module does not depend on how sys.path was set.

def _load_transliterators():
    mod = sys.modules.get("name_transliterators")
    if mod is None:
        path = Path(__file__).resolve().parent.parent / "name_transliterators.py"
        spec = importlib.util.spec_from_file_location("name_transliterators", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["name_transliterators"] = mod
    return mod


# Azerbaijani letters in the usual English-language spelling of a name
# (Məmmədov -> Mammadov, Cəfərov -> Jafarov, Xəlilov -> Khalilov,
# Qasımov -> Gasimov, Ağayev -> Aghayev). transliterate() has no such
# direction: its az -> latin is the identity.
_AZ_ENGLISH = {
    "ə": "a", "Ə": "A", "ç": "ch", "Ç": "Ch", "ş": "sh", "Ş": "Sh",
    "ğ": "gh", "Ğ": "Gh", "x": "kh", "X": "Kh", "ı": "i", "İ": "I",
    "ö": "o", "Ö": "O", "ü": "u", "Ü": "U", "c": "j", "C": "J",
    "q": "g", "Q": "G",
}


def az_english_spelling(name: str) -> str:
    return "".join(_AZ_ENGLISH.get(ch, ch) for ch in name)


_CYRILLIC_LETTER = re.compile(r"[Ѐ-ӿ]")
_LATIN_LETTER = re.compile(r"[A-Za-zƏəÇçĞğIıİÖöŞşÜü]")


# --- PEM private keys of real lengths (P2-4b) --------------------------------
#
# The old generator wrote 1-2 body lines of 64 characters: at most 192
# characters, while a real RSA-2048 key is about 1,700. (header, DER size in
# bytes, how the base64 body starts, weight). Body bytes are random; only the
# leading ASN.1 shape is the real one, so the key looks like its kind.
PEM_KINDS = (
    ("RSA PRIVATE KEY", (1190, 1193), "MIIEow", 0.14),        # RSA-2048, PKCS#1
    ("PRIVATE KEY", (1216, 1219), "MIIEvQIBADANBgkqhkiG9w0B", 0.10),  # RSA-2048, PKCS#8
    ("RSA PRIVATE KEY", (2347, 2350), "MIIJKAIBAAKCAgEA", 0.06),      # RSA-4096
    ("EC PRIVATE KEY", (121, 121), "MHcCAQEEI", 0.18),       # P-256, SEC1
    ("PRIVATE KEY", (138, 138), "MIGHAgEAMBMGByqGSM49AgEG", 0.12),   # P-256, PKCS#8
    ("PRIVATE KEY", (48, 48), "MC4CAQAwBQYDK2VwBCIEI", 0.22),         # Ed25519, PKCS#8
    ("OPENSSH PRIVATE KEY", (399, 411), "b3BlbnNzaC1rZXktdjEAAAAA", 0.18),
)
PEM_WIDTHS = (64, 76)


def pem_max_length(kind: tuple) -> int:
    """The longest key `private_key_varied` can write for a PEM_KINDS entry:
    BEGIN and END lines, the base64 body, one newline per body line at the
    narrowest width, plus the newline after BEGIN."""
    header, (_lo, hi), _lead, _w = kind
    body = -(-hi // 3) * 4
    lines = -(-body // min(PEM_WIDTHS))
    return len(f"-----BEGIN {header}-----") + len(f"-----END {header}-----") + body + lines + 1


# A Turkish, German or French name typed without its letters (P2-15)
_ASCII_FOLD = str.maketrans("ÇçĞğIıİÖöŞşÜüəƏ", "CcGgIiIOoSsUuaA")
_FOREIGN_NAMES: dict | None = None


def _foreign_names() -> dict:
    """Every foreign given name and surname form of the az locale (P2-15)
    -> its Cyrillic form, or '' when it has none."""
    global _FOREIGN_NAMES
    if _FOREIGN_NAMES is None:
        fn = LOCALES["az"].foreign_names
        names = (fn.given_names() + fn.surname_forms()) if fn else []
        _FOREIGN_NAMES = {n: fn.cyrillic.get(n, "") for n in names}
    return _FOREIGN_NAMES


_DRAWN_NAMES: frozenset | None = None


def _drawn_names() -> frozenset:
    """The foreign names and the Azerbaijani given names: what a foreign
    name's variant must not equal, or it would be read as that name."""
    global _DRAWN_NAMES
    if _DRAWN_NAMES is None:
        az = LOCALES["az"]
        _DRAWN_NAMES = frozenset(_foreign_names()) | frozenset(az.first_names_m) \
            | frozenset(az.first_names_f)
    return _DRAWN_NAMES


# ---------------------------------------------------------------------------
# ValueFactory
# ---------------------------------------------------------------------------

class ValueFactory:
    # P2-4b: share of GIVENNAME/SURNAME mints rendered in another spelling or
    # script. The pool keeps the canonical form, so its dedup, caps and
    # coreference are unchanged; only the surface form varies.
    NAME_VARIANT_RATE = 0.10
    # P2-15 (D-23d): share of persons with a foreign name (Russian, Turkish,
    # Georgian, Persian/Arabic, English/European), for ~10-15% of name
    # mentions; the locale's own names stay the majority. 0.13 gives LLM
    # briefs 13.4% (0.14 gave 14.5%, 16.2% at batch 5's seed). The targeted
    # builder sets its own rate in quotas.json (`names`): a sixth of its name
    # mentions are homograph-list names, always Azerbaijani.
    FOREIGN_NAME_RATE = 0.13

    def __init__(self, rng: random.Random, pool: ValuePool,
                 password_keyword_share: float = 0.12,
                 name_variant_rate: float = NAME_VARIANT_RATE,
                 foreign_name_rate: float = FOREIGN_NAME_RATE) -> None:
        self.rng = rng
        self.pool = pool
        self.password_keyword_share = password_keyword_share
        self.name_variant_rate = name_variant_rate
        self.foreign_name_rate = foreign_name_rate
        # Its own stream, seeded without drawing from `rng`: every other
        # value keeps exactly the draws it had before this feature existed.
        # Only the integer state is hashed (hash(None) varies per process
        # before Python 3.12).
        self.variant_rng = random.Random(hash(rng.getstate()[1]) & 0xFFFFFFFF)
        # rendered surface form -> (canonical pool value, variant kind)
        self.name_variants: dict[str, tuple[str, str]] = {}
        # variants a foreign name without another spelling passed on (P2-15)
        self.variant_owed = 0
        self._male_only: dict[int, list[str]] = {}     # father_name(), per locale (D-40a)

    def loc(self, lang: str):
        return LOCALES[lang]

    # -- identity -----------------------------------------------------------
    def name_origin(self, lang: str) -> str:
        """'' for a name of the locale itself, else the origin of a foreign
        name (`ru`, `tr`, ...; P2-15). Settle it once per person and pass it
        to both givenname() and surname(), as with `female`: the two then
        belong together (`Sergey Petrov`, never `Sergey Məmmədova`). Without
        one, each name draws its own."""
        fn = self.loc(lang).foreign_names
        if not fn or not fn.origins or self.rng.random() >= self.foreign_name_rate:
            return ""
        return self.rng.choices(fn.origins, weights=fn.origin_weights())[0]

    def givenname(self, lang: str, female: bool | None = None,
                  origin: str | None = None, variant: bool = True) -> str:
        """`variant=False`: always the pool's own spelling (D-40a: an official
        list writes one person's names in one spelling)."""
        loc = self.loc(lang)
        rng = self.rng
        if origin is None:
            origin = self.name_origin(lang)

        def make() -> str:
            f = female if female is not None else rng.random() < 0.5
            if origin:
                names, weights = (loc.foreign_names.given_f if f
                                  else loc.foreign_names.given_m)[origin]
                return rng.choices(names, weights=weights)[0]
            return rng.choice(loc.first_names_f if f else loc.first_names_m)

        value = self.pool.fresh("GIVENNAME", make)
        return self._name_variant(value, lang) if variant else value

    def father_name(self, lang: str) -> str:
        """D-40a: the father's name in a patronymic. A man's Azerbaijani name
        that is not also in the women's pool: the two pools share 233 names,
        some of them women's names (`Ulduz`, `Röya`), and `Ulduz oğlu` is no
        patronymic. In the pool's own spelling, like the rest of the line."""
        loc = self.loc(lang)
        key = id(loc)
        if key not in self._male_only:
            from .validate import _TURKISH_RE        # lazy: validate imports this module
            female = set(loc.first_names_f)
            # nor a name the validator reads as a Turkish word (`Nasil`, "nasıl")
            self._male_only[key] = sorted(n for n in set(loc.first_names_m)
                                          if n not in female and not _TURKISH_RE.fullmatch(n))
        names = self._male_only[key]
        return self.pool.fresh("GIVENNAME", lambda: self.rng.choice(names))

    def surname(self, lang: str, female: bool | None = None,
                origin: str | None = None, variant: bool = True) -> str:
        loc = self.loc(lang)
        rng = self.rng
        if origin is None:
            origin = self.name_origin(lang)

        def make() -> str:
            f = female if female is not None else rng.random() < 0.5
            if origin:
                pairs, weights = loc.foreign_names.surnames[origin]
                masc, fem = rng.choices(pairs, weights=weights)[0]
                return fem if f else masc
            return loc.surname_builder(rng.choice(loc.surname_stems), f, rng)

        value = self.pool.fresh("SURNAME", make)
        return self._name_variant(value, lang) if variant else value

    def name_spellings(self, name: str, lang: str | None = None) -> dict[str, str]:
        """Every other spelling/script of `name` this generator can write,
        as {kind: form}; forms equal to the name itself are left out.

        Decided by the name's own script, not the document's language: the
        en/tr/ru locales carry Azerbaijani names too (`Uğurluyev`), and
        en_to_cyrillic would leave their ğ/ə behind (`Уğурлуиев`). A form
        that mixes Latin and Cyrillic letters is never returned.
        """
        foreign = _foreign_names()
        if name in foreign:
            # a foreign name (P2-15): its Russian form if it has one, and its
            # spelling on an English keyboard (`Öztürk` -> `Ozturk`, `Müller`
            # -> `Muller`); no Azerbaijani transliteration (`John` is never
            # `Жохн`). Without the second, Turkish, German and French names
            # had no variant and the variant share fell below the ~10% gate.
            forms = {"cyrillic": foreign[name], "english": name.translate(_ASCII_FOLD)}
            return {k: v for k, v in forms.items() if v and v != name}
        nt = _load_transliterators()
        if _CYRILLIC_LETTER.search(name):
            forms = {"latin": nt.transliterate(name, "ru", "latin")}
        else:
            forms = {"english": az_english_spelling(name),
                     "cyrillic": nt.transliterate(name, "az", "cyrillic")}
        return {k: v for k, v in forms.items()
                if v and v != name and not (_CYRILLIC_LETTER.search(v) and _LATIN_LETTER.search(v))}

    def _name_variant(self, canonical: str, lang: str) -> str:
        if not canonical:
            return canonical
        drawn = self.variant_rng.random() < self.name_variant_rate
        if not drawn and not self.variant_owed:
            return canonical
        # a form that is itself a foreign name we draw is not a variant
        # (`Samad` is Saməd's English spelling and a Persian name), nor is a
        # foreign name's form that is an Azerbaijani one (P2-15)
        # D-40b: an Azerbaijani name's form must not be another drawn name
        # either (`Susana`, Süsanə's English spelling, is also a pool name);
        # this was checked for foreign names only, and the pool change made
        # the collision surface
        taken = _drawn_names()
        forms = {k: v for k, v in self.name_spellings(canonical, lang).items()
                 if not is_blocked(v) and v not in taken}
        if not forms:
            # A foreign name with no other spelling (`John`, P2-15) passes its
            # turn to the next name that has one; otherwise the variant share
            # fell from 9.5% to 8.6% of names and below the gate in small builds.
            if drawn and canonical in _foreign_names():
                self.variant_owed += 1
            return canonical
        if not drawn:
            self.variant_owed -= 1
        # Azerbaijani: the English spelling is the common one in practice
        weights = [0.6 if k == "english" else 0.4 for k in sorted(forms)]
        kind = self.variant_rng.choices(sorted(forms), weights=weights)[0]
        self.name_variants[forms[kind]] = (canonical, kind)
        return forms[kind]

    def latin_spelling(self, value: str) -> str:
        """A name minted in Cyrillic, written in its English spelling instead
        and still recorded as a variant; any other value unchanged.

        For a name that takes an Azerbaijani suffix (P2-4c): a Latin suffix
        cannot follow a Cyrillic stem, and drawing another name instead would
        leave inflected names with half the ~10% variant rate."""
        canonical, kind = self.name_variants.get(value, ("", ""))
        if kind != "cyrillic":
            return value
        english = self.name_spellings(canonical).get("english")
        if english is None:
            # the English spelling is the Azerbaijani one (Yunusov, Mutlu):
            # the name itself, which is no variant. Returning the Cyrillic
            # value left `Юнусовdur`, a Latin suffix on a Cyrillic stem (P4-2
            # round 2: 5 in 5,000 documents).
            return canonical
        if is_blocked(english):
            return value
        self.name_variants[english] = (canonical, "english")
        return english

    def email(self, lang: str, first: str = "", last: str = "",
              corporate: bool | None = None) -> str:
        loc = self.loc(lang)
        rng = self.rng

        def make() -> str:
            f = translit(first) if first else translit(rng.choice(
                loc.first_names_m + loc.first_names_f))
            l = translit(last) if last else translit(
                loc.surname_builder(rng.choice(loc.surname_stems), False, rng))
            f = "".join(c for c in f if c.isalnum()) or "user"
            l = "".join(c for c in l if c.isalnum()) or "mail"
            corp = rng.random() < 0.42 if corporate is None else corporate
            domain = rng.choice(loc.corporate_domains if corp else loc.email_domains)
            style = rng.random()
            if style < 0.20:
                local = f"{f}.{l}"
            elif style < 0.34:
                local = f"{f[0]}.{l}"
            elif style < 0.46:
                local = f"{f}{l}"
            elif style < 0.56:
                local = f"{f}.{l}{rng.randint(1, 99)}"
            elif style < 0.65:
                local = f"{f}_{l}"
            elif style < 0.73:
                local = f"{l}.{f[0]}"
            elif style < 0.80:
                local = f"{f}{rng.randint(1, 9999)}"
            elif style < 0.86:
                local = f"{f[0]}{l}{rng.randint(10, 99)}"
            elif style < 0.91:
                local = f"{l}{f[0]}"
            elif style < 0.95:
                local = f"{f}-{l}"
            else:
                local = rng.choice(["info", "support", "sales", "hr", "billing",
                                    "accounts", "helpdesk", "noreply", "careers",
                                    "finance", "legal", "orders"]) + f".{l}"
            local = "".join(c for c in local if c in _LOWER_NUM + "._+-")
            return f"{local or 'user'}@{domain}"

        return self.pool.fresh("EMAIL", make)

    # -- contact --------------------------------------------------------
    def telephonenum(self, lang: str) -> str:
        loc = self.loc(lang)
        return self.pool.fresh("TELEPHONENUM", lambda: loc.phone_builder(self.rng))

    # -- address components -----------------------------------------------
    def city(self, lang: str) -> str:
        loc = self.loc(lang)
        rng = self.rng

        # P2-14 (D-23c): the settlement pool when the locale has one
        cities, weights = ((loc.settlements, loc.settlement_weights) if loc.settlements
                           else (loc.cities, loc.city_weights))

        def make() -> str:
            if weights:
                return rng.choices(cities, weights=weights)[0]
            return rng.choice(cities)

        weight_fn = None
        if weights:
            weight_map = dict(zip(cities, weights))
            avg_weight = math.fsum(weights) / len(weights)     # D-49: same on every Python

            # Normalized so the average city keeps the pool's existing
            # max_share cap unchanged (ratio 1.0); a city weighted well above
            # average (the capital) earns a proportionally larger cap instead
            # of hitting the flat cap almost immediately and effectively
            # cancelling the whole point of oversampling it.
            def weight_fn(v: str) -> float:
                return weight_map.get(v, avg_weight) / avg_weight

        return self.pool.fresh("CITY", make, weight_fn=weight_fn)

    def street(self, lang: str) -> str:
        loc = self.loc(lang)

        def make() -> str:
            stem = self.rng.choice(loc.street_stems)
            return loc.street_builder(stem, self.rng)

        return self.pool.fresh("STREET", make)

    def street_town(self, lang: str = "az") -> str:
        """v4.2 fix list (v4.1 read 11 streets as CITY on shadow-dev): a street
        named after a town (`Gəncə prospekti`, `Şamaxı küçəsi`), as many in
        Azerbaijan are. The whole name is the STREET; 12 of the 1,637 streets
        in v4.1's targeted build had a town in them."""
        loc = self.loc(lang)

        # v4.2 native review F: town-named streets are mostly `küçəsi` and
        # `prospekti`, a town-named `döngə` is rare; a two-word place takes
        # only `küçəsi`, and `Qobustan Mərəzə` none
        words = ["küçəsi", "küç.", "prospekti", "pr.", "şossesi", "döngəsi"]
        weights = [0.35, 0.2, 0.12, 0.08, 0.15, 0.1]

        def make() -> str:
            while True:
                town = self.rng.choice(loc.cities)
                if town != "Qobustan Mərəzə":
                    break
            if " " in town:
                return town + " küçəsi"
            return town + " " + self.rng.choices(words, weights=weights)[0]

        return self.pool.fresh("STREET", make)

    def buildingnum(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            n = rng.randint(1, 220)
            if rng.random() < 0.12:
                return f"{n}{rng.choice(string.ascii_uppercase[:6])}"
            if rng.random() < 0.08:
                return f"{n}/{rng.randint(1, 12)}"
            return str(n)

        return self.pool.fresh("BUILDINGNUM", make)

    # D-42c: share of Azerbaijani ZIPs written bare, without `AZ` (`1043`).
    # Run B never found one on shadow-dev (0 of 62); no source had one.
    ZIP_BARE_RATE = 0.25

    def zipcode(self, lang: str) -> str:
        loc = self.loc(lang)
        if lang == "az" and self.rng.random() < self.ZIP_BARE_RATE:
            return self.zipcode_bare()
        return self.pool.fresh("ZIPCODE", lambda: loc.postal_builder(self.rng))

    def zipcode_bare(self, lang: str | None = None) -> str:
        """D-42c: a real postal code's four digits, without `AZ`. Years
        (1900-2099) and round hundreds are left out: a bare ZIP that equals
        an amount or a year elsewhere in a document would be labelled there
        too."""
        from .locales import az as AZ

        codes = [z[2:] for z in AZ._ZIPCODES
                 if not (1900 <= int(z[2:]) <= 2099 or int(z[2:]) % 100 == 0)]
        return self.pool.fresh("ZIPCODE", lambda: self.rng.choice(codes))

    # -- calendar / context-only -------------------------------------------
    def date(self, lang: str, min_year: int = 1945, max_year: int = 2027) -> str:
        loc = self.loc(lang)
        rng = self.rng

        def make() -> str:
            year = rng.randint(min_year, max_year)
            month = rng.randint(1, 12)
            day = rng.randint(1, 28 if month == 2 else 30)
            return loc.date_builder(day, month, year, rng)

        return self.pool.fresh("DATE", make)

    def time_of_day(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            h, m = rng.randint(0, 23), rng.randint(0, 59)
            if rng.random() < 0.15:
                hh = h % 12 or 12
                return f"{hh}:{m:02d} {'AM' if h < 12 else 'PM'}"
            return f"{h:02d}:{m:02d}"

        return self.pool.fresh("TIME", make)

    def time_with_seconds(self, lo: int = 0, hi: int = 86399, step: int = 1,
                          seconds: bool = True) -> str:
        """A 24-hour clock time with seconds (`14:05:22`), between `lo` and
        `hi` seconds after midnight, on a multiple of `step` (900: a quarter
        hour, `15:30:00`); `seconds=False` writes `15:30`. v3 missed 72 of 80
        `99:99:99` times on shadow-dev (v3_shadow_shapes.md, lead 1): the data
        had seconds only inside unlabelled stamps (D-17, D-51f)."""
        rng = self.rng

        def make() -> str:
            t = rng.randint(-(-lo // step), hi // step) * step
            h, m, s = t // 3600, t % 3600 // 60, t % 60
            return f"{h:02d}:{m:02d}:{s:02d}" if seconds else f"{h:02d}:{m:02d}"

        return self.pool.fresh("TIME", make)

    def age(self, lang: str | None = None) -> str:
        return self.pool.fresh("AGE", lambda: str(self.rng.randint(1, 95)))

    def card_security_code(self, lang: str | None = None) -> str:
        rng = self.rng
        return self.pool.fresh(
            "CARD_SECURITY_CODE",
            lambda: _rand(rng, string.digits, 4 if rng.random() < 0.15 else 3))

    # -- financial ----------------------------------------------------------
    def payment_card_number(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            prefixes, length, _brand, _w = rng.choices(
                CK.CARD_SPECS, weights=[s[3] for s in CK.CARD_SPECS])[0]
            prefix = rng.choice(prefixes)
            body = prefix + _rand(rng, string.digits, length - len(prefix) - 1)
            number = body + CK.luhn_check_digit(body)
            style = rng.random()
            if style < 0.40:
                if length == 15:
                    return f"{number[:4]} {number[4:10]} {number[10:]}"
                return " ".join(number[i:i + 4] for i in range(0, len(number), 4))
            if style < 0.62:
                return "-".join(number[i:i + 4] for i in range(0, len(number), 4))
            return number

        return self.pool.fresh("PAYMENT_CARD_NUMBER", make)

    def iban(self, lang: str) -> str:
        loc = self.loc(lang)
        rng = self.rng

        def make() -> str:
            country = rng.choice(loc.iban_countries)
            total = CK.IBAN_LENGTHS[country]
            alpha = CK.IBAN_BBAN_ALPHA.get(country, 0)
            bban_len = total - 4
            bban = (_rand(rng, string.ascii_uppercase, alpha)
                    + _rand(rng, string.digits, bban_len - alpha))
            code = country + CK.iban_check_digits(country, bban) + bban
            style = rng.random()
            if style < 0.32:
                return " ".join(code[i:i + 4] for i in range(0, len(code), 4))
            if style < 0.40:
                return code.lower()
            return code

        return self.pool.fresh("IBAN", make)

    # -- fixed-style variants for the targeted builder (P2-4) -------------
    # New methods, not new parameters: the defaults above keep drawing the
    # exact same random numbers, so LLM-path runs stay reproducible.
    def payment_card_grouped(self, lang: str | None = None) -> str:
        """A 16-digit card, space-grouped `#### #### #### ####`: the form the
        benchmark's missed cards take in prose."""
        rng = self.rng

        def make() -> str:
            specs = [s for s in CK.CARD_SPECS if s[1] == 16]
            prefixes, length, _brand, _w = rng.choices(specs, weights=[s[3] for s in specs])[0]
            prefix = rng.choice(prefixes)
            body = prefix + _rand(rng, string.digits, length - len(prefix) - 1)
            number = body + CK.luhn_check_digit(body)
            return " ".join(number[i:i + 4] for i in range(0, 16, 4))

        return self.pool.fresh("PAYMENT_CARD_NUMBER", make)

    def iban_az_compact(self, lang: str | None = None) -> str:
        """A 28-character Azerbaijani IBAN, written without spaces."""
        rng = self.rng

        def make() -> str:
            alpha = CK.IBAN_BBAN_ALPHA.get("AZ", 0)
            bban = (_rand(rng, string.ascii_uppercase, alpha)
                    + _rand(rng, string.digits, CK.IBAN_LENGTHS["AZ"] - 4 - alpha))
            return "AZ" + CK.iban_check_digits("AZ", bban) + bban

        return self.pool.fresh("IBAN", make)

    def iban_az_alnum(self, grouped: bool = False) -> str:
        """D-34e: an AZ IBAN whose 20-character account part holds letters,
        as the registered format `AZ2!n4!a20!c` allows: 2-8 capital letters
        spread through it, compact or in groups of four."""
        rng = self.rng

        def make() -> str:
            account = [rng.choice(string.digits) for _ in range(20)]
            for i in rng.sample(range(20), rng.randint(2, 8)):
                account[i] = rng.choice(string.ascii_uppercase)
            bban = _rand(rng, string.ascii_uppercase, 4) + "".join(account)
            code = "AZ" + CK.iban_check_digits("AZ", bban) + bban
            return " ".join(code[i:i + 4] for i in range(0, len(code), 4)) if grouped else code

        return self.pool.fresh("IBAN", make)

    # -- boundary shapes for the targeted builder (P2-4b, RC5) -------------
    # The benchmark's boundary errors cut values short at their inner spaces,
    # line breaks and query strings; these write those shapes on purpose.
    def iban_az_grouped(self, lang: str | None = None) -> str:
        """A 28-character AZ IBAN in space-separated groups of four."""
        rng = self.rng

        def make() -> str:
            alpha = CK.IBAN_BBAN_ALPHA.get("AZ", 0)
            bban = (_rand(rng, string.ascii_uppercase, alpha)
                    + _rand(rng, string.digits, CK.IBAN_LENGTHS["AZ"] - 4 - alpha))
            code = "AZ" + CK.iban_check_digits("AZ", bban) + bban
            return " ".join(code[i:i + 4] for i in range(0, len(code), 4))

        return self.pool.fresh("IBAN", make)

    def iban_az_irregular(self, lang: str | None = None) -> str:
        """v4.2 fix list (v4.1 missed 23 IBANs on shadow-dev, 7 too narrow and
        7 split): an AZ IBAN grouped the way people type it rather than in
        clean fours -- `AZ 21 NABZ ...`, only the first group spaced, only the
        account part grouped, or groups joined by dashes. Every form is the
        same valid IBAN (`checksums.iban_valid` ignores spaces and dashes)."""
        rng = self.rng

        def make() -> str:
            alpha = CK.IBAN_BBAN_ALPHA.get("AZ", 0)
            bban = (_rand(rng, string.ascii_uppercase, alpha)
                    + _rand(rng, string.digits, CK.IBAN_LENGTHS["AZ"] - 4 - alpha))
            code = "AZ" + CK.iban_check_digits("AZ", bban) + bban
            fours = [code[i:i + 4] for i in range(0, len(code), 4)]
            style = rng.random()
            if style < 0.3:
                return "AZ " + code[2:4] + " " + " ".join(fours[1:])       # AZ 21 NABZ 0000 ...
            if style < 0.55:
                return fours[0] + " " + "".join(fours[1:])                  # AZ21 NABZ0000...
            if style < 0.8:
                return "".join(fours[:2]) + " " + " ".join(fours[2:])       # AZ21NABZ 0000 0000 ...
            return "-".join(fours)                                          # AZ21-NABZ-0000-...

        return self.pool.fresh("IBAN", make)

    # D-42c: `+994 ({op}) {a}-{b}-{c}` added (Run B missed 33 of 49 on shadow-dev)
    PHONE_GROUPED_STYLES = ("+994 {op} {a} {b} {c}", "0{op} {a} {b} {c}",
                            "+994 ({op}) {a} {b} {c}", "(0{op}) {a} {b} {c}",
                            "+994 {op} {a} {b}{c}", "0{op} {a} {b}-{c}",
                            "+994 ({op}) {a}-{b}-{c}")

    def telephone_grouped(self, lang: str | None = None) -> str:
        """An Azerbaijani number written in space-separated groups
        (`055 123 45 67`, `+994 55 123 45 67`)."""
        from .locales import az as AZ
        rng = self.rng

        def make() -> str:
            if rng.random() < 0.78:
                op = rng.choices(AZ._MOBILE_CODES, weights=AZ._MOBILE_WEIGHTS)[0]
            else:
                op = rng.choices(AZ._LANDLINE_CODES, weights=AZ._LANDLINE_WEIGHTS)[0]
            return rng.choice(self.PHONE_GROUPED_STYLES).format(
                op=op, a=rng.randint(100, 999), b=f"{rng.randint(0, 99):02d}",
                c=f"{rng.randint(0, 99):02d}")

        return self.pool.fresh("TELEPHONENUM", make)

    def url_query(self, lang: str | None = None) -> str:
        """A URL whose credential sits in a multi-parameter query string,
        not always the first or the last parameter."""
        loc = self.loc(lang or "az")
        rng = self.rng

        def make() -> str:
            host = rng.choice(loc.corporate_domains)
            sub = rng.choice(["app", "portal", "auth", "id", "secure", "my", "api", "login"])
            path = rng.choice(["/verify", "/reset", "/oauth/callback", "/v2/auth", "/confirm",
                               "/activate", "/download", "/session", "/sso/return"])
            token = _rand(rng, _ALNUM + "-_", rng.randint(24, 48))
            param = rng.choice(sorted(CK.TOKEN_PARAMS - {"t"}))
            extra = [rng.choice(["lang=az", "lang=en", "ref=mail", "utm_source=sms",
                                 f"uid={rng.randint(10000, 999999)}", "redirect=%2Fhome",
                                 f"expires={rng.choice([900, 3600, 86400])}", "v=2",
                                 # under 8 characters: url_with_token_valid
                                 # reads the first parameter with a value of
                                 # 8+ characters as the credential
                                 f"state={_rand(rng, _LOWER_NUM, 6)}"])
                     for _ in range(rng.randint(1, 3))]
            params = extra + [f"{param}={token}"]
            rng.shuffle(params)
            return f"https://{sub}.{host}{path}?{'&'.join(params)}"

        return self.pool.fresh("URL", make)

    def private_key_varied(self, lang: str | None = None, max_chars: int | None = None,
                           min_chars: int | None = None) -> str:
        """A PEM private key of a real kind and length (PEM_KINDS), body
        wrapped at 64 or 76 columns. Line breaks are newlines; the layout
        on the page (one line, trailing punctuation) is the builder's job.

        `max_chars` keeps only the kinds whose longest key fits: a real
        RSA key (1,700+ characters) needs a document of about 6,800
        characters to pass the quality gate's PII-density cap. `min_chars`
        keeps only kinds at least that long (D-27: the long-key documents)."""
        rng = self.rng
        kinds = [k for k in PEM_KINDS if (max_chars is None or pem_max_length(k) <= max_chars)
                 and (min_chars is None or pem_max_length(k) >= min_chars)]
        if not kinds:
            raise ValueError(f"no PEM kind between {min_chars} and {max_chars} characters")

        def make() -> str:
            header, (lo, hi), lead, _w = rng.choices(kinds, weights=[k[3] for k in kinds])[0]
            der = bytes(rng.getrandbits(8) for _ in range(rng.randint(lo, hi)))
            body = base64.b64encode(der).decode("ascii")
            body = lead + body[len(lead):]
            width = rng.choice(PEM_WIDTHS)
            lines = [body[i:i + width] for i in range(0, len(body), width)]
            return "\n".join([f"-----BEGIN {header}-----", *lines, f"-----END {header}-----"])

        return self.pool.fresh("PRIVATE_KEY", make)

    def private_key_ed25519(self, lang: str | None = None) -> str:
        """D-51h: a short Ed25519 private key, PKCS#8 (`-----BEGIN PRIVATE
        KEY-----`, a 64-character body starting `MC4CAQAw...`), fresh random
        bytes behind the real ASN.1 lead. The builder sets at least three of
        these per Ed25519 public-key look-alike (v3: 166 short public
        look-alikes vs 77 short private keys split at the header)."""
        rng = self.rng
        kind = next(k for k in PEM_KINDS if k[2].startswith("MC4CAQAw"))

        def make() -> str:
            header, (lo, hi), lead, _w = kind
            der = bytes(rng.getrandbits(8) for _ in range(rng.randint(lo, hi)))
            body = lead + base64.b64encode(der).decode("ascii")[len(lead):]
            return "\n".join([f"-----BEGIN {header}-----", body, f"-----END {header}-----"])

        return self.pool.fresh("PRIVATE_KEY", make)

    DATE_STYLES = ("dmy", "iso", "spelled")

    def date_styled(self, lang: str, style: str,
                    min_year: int = 1945, max_year: int = 2027, day31_rate: float = 0.0) -> str:
        """A DATE in one named style: `dmy` 05.03.1990, `iso` 1990-03-05,
        `spelled` 5 mart 1990. D-57 S6: any day of the month (the 31st, and
        29 February in a leap year), so real dates stand beside the day-31
        and 29-February look-alikes (v4.2: 1,483 day-31 look-alikes, no real
        31st in the targeted data). `day31_rate`: the chance of the 31st of a
        31-day month, so real 31sts stand beside the many day-31 look-alikes."""
        loc = self.loc(lang)
        rng = self.rng

        def make() -> str:
            year = rng.randint(min_year, max_year)
            if day31_rate and rng.random() < day31_rate:
                month, day = rng.choice((1, 3, 5, 7, 8, 10, 12)), 31
            else:
                month = rng.randint(1, 12)
                day = rng.randint(1, calendar.monthrange(year, month)[1])
            if style == "dmy":
                return f"{day:02d}.{month:02d}.{year}"
            if style == "iso":
                return f"{year}-{month:02d}-{day:02d}"
            return f"{day} {loc.months[month - 1]} {year}"

        return self.pool.fresh("DATE", make)

    RESERVED_TLDS = ("invalid", "test", "example", "local")

    def email_synthetic(self, lang: str | None = None) -> str:
        """v4.1 (#91 item 9): a synthetic-looking test address
        (`test.user12@example.invalid`, `demo.user3@demo-mail4.invalid`), as
        test and demo accounts appear in tables, JSON and logs. v4 split all 26
        of the benchmark's synthetic addresses; our own shapes, not its
        values."""
        rng = self.rng

        def make() -> str:
            local = rng.choice(["test.user", "demo.user", "qa.tester", "sample.account", "trial.user",
                                "user.test", "dev.tester"]) + str(rng.randint(1, 99))
            n = rng.randint(1, 9)
            domain = rng.choice(["example.invalid", f"demo-mail{n}.invalid", f"test-mail{n}.example",
                                 f"sample{n}.test", "qa-portal.invalid", f"sandbox{n}.invalid"])
            return f"{local}@{domain}"

        return self.pool.fresh("EMAIL", make)

    def email_reserved(self, lang: str) -> str:
        """An address on a reserved TLD (`.invalid`, `.test`, `.example`,
        `.local`), with a digit-suffixed host part half of the time
        (`mail7.example`). The benchmark's missed emails all look like this;
        a real local part keeps it from being a placeholder."""
        loc = self.loc(lang)
        rng = self.rng

        def make() -> str:
            f = "".join(c for c in translit(rng.choice(
                loc.first_names_m + loc.first_names_f)) if c.isalnum()) or "ad"
            l = "".join(c for c in translit(loc.surname_builder(
                rng.choice(loc.surname_stems), False, rng)) if c.isalnum()) or "soyad"
            # D-34 (D-33f, EMAIL in structured formats): `name.surname` + 2
            # digits, and a hyphenated host + digit, the shapes Run B split
            local = rng.choice([f"{f}.{l}", f"{f[0]}.{l}", f"{f}{rng.randint(1, 99)}",
                                f"{f}_{l}", f"{l}.{f[0]}", f"{f}.{l}{rng.randint(10, 99)}"])
            if rng.random() < 0.3:
                words = ["ofis", "xidmet", "portal", "kassa", "satis", "destek", "hesab",
                         "mail", "info", "sened", "qeydiyyat", "muraciet"]
                a, b = rng.sample(words, 2)
                host = f"{a}-{b}{rng.randint(1, 9)}"
            else:
                host = rng.choice(["mail", "posta", "inbox", "office", "portal", "hr",
                                   "crm", "server", "corp", "bank"])
                if rng.random() < 0.5:
                    host += str(rng.randint(1, 30))
            return f"{local}@{host}.{rng.choice(self.RESERVED_TLDS)}"

        return self.pool.fresh("EMAIL", make)

    def token_key_same_body(self, lang: str | None = None) -> tuple[str, str]:
        """An ACCESS_TOKEN and an API_KEY with the SAME body, different
        prefixes (P2-4 contrast pairs): only the prefix and the anchor word
        can tell them apart."""
        rng = self.rng
        body = _rand(rng, _ALNUM, rng.randint(24, 40))
        token = self.pool.fresh("ACCESS_TOKEN", lambda: rng.choice(
            [p for p in ACCESS_TOKEN_PREFIXES if p != "bearer_"]) + body)
        key = self.pool.fresh("API_KEY", lambda: rng.choice(
            ("key_", "api_", "apikey_", "svc_")) + body)
        return token, key

    def licence_and_id_same_prefix(self, lang: str | None = None,
                                   prefix: str | None = None) -> tuple[str, str]:
        """A driver licence (2 letters + 6 digits) and an ID card (+ 7 digits)
        with the same prefix: only the digit count and the anchor word can
        tell them apart (P2-4 contrast pairs). D-51h: any ID-card prefix
        (`az_id_card_prefix`), not only `AA`/`AB`; `prefix` fixes it (D-56a 3)."""
        rng = self.rng
        prefix = prefix or self.az_id_card_prefix()
        licence = self.pool.fresh("AZ_DRIVER_LICENSE_NUMBER",
                                  lambda: prefix + _rand(rng, string.digits, 6))
        card = self.pool.fresh("AZ_ID_CARD_NUMBER",
                               lambda: prefix + _rand(rng, string.digits, 7))
        return licence, card

    def ipv6_and_mac(self, lang: str | None = None) -> tuple[str, str]:
        """A `::`-compressed IPv6 address and a MAC address for one device
        (P2-6 contrast lesson): the benchmark read 131 compressed IPv6
        addresses as MAC, and none of the old training IPv6 had `::`."""
        ip = ""
        for _ in range(30):
            ip = self.ipv6_address(lang)
            if "::" in ip:
                break
        return ip, self.mac_address(lang)

    # -- network / infrastructure --------------------------------------
    def ipv4_address(self, lang: str | None = None, prefer_public: bool = False) -> str:
        rng = self.rng

        def make() -> str:
            r = rng.random()
            if prefer_public or r < 0.42:
                while True:
                    addr = ipaddress.IPv4Address(rng.randint(0x01000000, 0xDFFFFFFF))
                    if not (addr.is_private or addr.is_reserved or addr.is_loopback
                            or addr.is_multicast or addr.is_link_local):
                        return str(addr)
            if r < 0.56:
                net = rng.choice(["192.0.2", "198.51.100", "203.0.113"])
                return f"{net}.{rng.randint(1, 254)}"
            if r < 0.82:
                c = rng.random()
                if c < 0.4:
                    return f"192.168.{rng.randint(0, 255)}.{rng.randint(2, 254)}"
                if c < 0.75:
                    return f"10.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(2, 254)}"
                return f"172.{rng.randint(16, 31)}.{rng.randint(0, 255)}.{rng.randint(2, 254)}"
            if r < 0.90:
                return f"100.{rng.randint(64, 127)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
            return str(ipaddress.IPv4Address(rng.randint(0x01000000, 0xDFFFFFFF)))

        return self.pool.fresh("IPV4_ADDRESS", make)

    def ipv4_one_digit(self, lang: str | None = None) -> str:
        """v4.1 (#91 item 2, D-52b priority): a valid IPv4 with two
        to four one-digit octets -- public-DNS-like `4.2.2.1`, gateways
        `10.0.0.x`, `192.168.0.x`. v4 found 0 of 30 `8.8.8.8`-type and 5 of 30
        `10.0.0.1`-type addresses (v3: 29 and 30): D-51h's look-alikes are
        built from one-digit octets, and the labelled side had 14 such values.
        The textbook addresses themselves (`8.8.8.8`, `10.0.0.1`, ...) stay
        blocked (blocklist.BLOCKED_EXACT); the shape is what is taught."""
        rng = self.rng

        def make() -> str:
            r = rng.random()
            if r < 0.25:                                    # four one-digit octets
                return f"{rng.randint(1, 9)}.{rng.randint(0, 9)}.{rng.randint(0, 9)}.{rng.randint(1, 9)}"
            if r < 0.5:
                return f"10.{rng.randint(0, 9)}.{rng.randint(0, 9)}.{rng.randint(1, 9)}"
            if r < 0.7:
                return f"192.168.{rng.randint(0, 9)}.{rng.randint(1, 9)}"
            if r < 0.8:
                return f"172.{rng.randint(16, 31)}.{rng.randint(0, 9)}.{rng.randint(1, 9)}"
            first = rng.choice([a for a in range(11, 224) if a not in (100, 127, 169, 172, 192)])
            if r < 0.9:                                     # three one-digit octets, public
                return f"{first}.{rng.randint(0, 9)}.{rng.randint(0, 9)}.{rng.randint(1, 9)}"
            return f"{first}.{rng.randint(10, 255)}.{rng.randint(0, 9)}.{rng.randint(1, 9)}"

        return self.pool.fresh("IPV4_ADDRESS", make)

    def ipv6_address(self, lang: str | None = None) -> str:
        return self.pool.fresh("IPV6_ADDRESS", self._ipv6)

    def _ipv6(self) -> str:
        """~64% `::`-compressed, ~36% full 8-group form (P2-1).

        The old version compressed random groups, which are almost never
        zero, so 0 of 8,033 training values contained `::` -- while all 399
        benchmark misses did. Zero runs are now placed explicitly: `::` in
        the middle (the benchmark's form), at the start and at the end, a
        `<prefix>::1` host address, and IPv4-embedded `::ffff:a.b.c.d`.
        Bare `::1` is never emitted: blocklist.py rejects it as a placeholder.
        """
        rng = self.rng

        def grp() -> str:
            return format(rng.randint(1, 0xFFFF), "x")

        def prefix() -> list[str]:
            r = rng.random()
            if r < 0.45:
                return ["2001", "db8"]
            if r < 0.75:
                return ["fd00" if rng.random() < 0.5 else "fd" + _rand(rng, _HEX, 2)]
            if r < 0.85:
                return ["fe80"]
            return ["2" + _rand(rng, _HEX, 3)]

        if rng.random() < 0.36:
            p = prefix()
            if p == ["fe80"]:
                groups = ["fe80", "0", "0", "0"] + [grp() for _ in range(4)]
            else:
                groups = p + [grp() for _ in range(8 - len(p))]
                if rng.random() < 0.3:                      # written-out zero run
                    i = rng.randint(len(p), 6)
                    groups[i] = groups[i + 1] = "0"
            if rng.random() < 0.5:                          # keep leading zeros
                groups = [g.zfill(4) for g in groups]
            value = ":".join(groups)
        else:
            r = rng.random()
            if r < 0.60:                                    # middle
                p = prefix()
                if p == ["fe80"]:
                    value = "fe80::" + ":".join(grp() for _ in range(rng.randint(2, 4)))
                else:
                    head = p + [grp() for _ in range(rng.randint(0, 2))]
                    tail = [grp() for _ in range(rng.randint(1, 6 - len(head)))]
                    value = ":".join(head) + "::" + ":".join(tail)
            elif r < 0.72:                                  # end
                p = [g for g in prefix() if g != "fe80"] or ["fd00"]
                value = ":".join(p + [grp() for _ in range(rng.randint(1, 3))]) + "::"
            elif r < 0.82:                                  # start
                value = "::" + ":".join(grp() for _ in range(rng.randint(2, 4)))
            elif r < 0.91:                                  # <prefix>::1
                p = [g for g in prefix() if g != "fe80"] or ["2001", "db8"]
                value = ":".join(p + [grp() for _ in range(rng.randint(0, 2))]) + "::1"
            else:                                           # IPv4-embedded
                value = "::ffff:" + ".".join(str(rng.randint(1, 254)) for _ in range(4))
        c = rng.random()
        if c < 0.15:
            return value.upper()
        if c < 0.22:
            return "".join(ch.upper() if rng.random() < 0.5 else ch for ch in value)
        return value

    def mac_address(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            oui = rng.choice(["00:1B:44", "3C:5A:B4", "B8:27:EB", "DC:A6:32",
                              "F0:18:98", "AC:DE:48", "00:16:3E", "8C:85:90",
                              "E4:5F:01", "00:0C:29", "5C:F9:38", "A4:83:E7",
                              "D8:3A:DD", "48:2A:E3", "70:85:C2"])
            octets = oui.split(":") + [f"{rng.randint(0, 255):02X}" for _ in range(3)]
            style = rng.random()
            if style < 0.55:
                mac = ":".join(octets)
            elif style < 0.80:
                mac = "-".join(octets)
            else:                                   # Cisco dotted aabb.ccdd.eeff
                flat = "".join(octets)
                mac = ".".join(flat[i:i + 4] for i in (0, 4, 8))
            case = rng.random()
            if case < 0.40:
                return mac.lower()
            if case < 0.85:
                return mac
            return "".join(ch.lower() if rng.random() < 0.5 else ch for ch in mac)

        return self.pool.fresh("MAC_ADDRESS", make)

    def iccid(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            # 89 (telecom) + country code + issuer + account, 18 digits before
            # the check digit -- 89, 994 (AZ), then 15 more digits, Luhn check.
            body = "89994" + _rand(rng, string.digits, 14)
            return body + CK.luhn_check_digit(body)

        return self.pool.fresh("ICCID", make)

    def api_key(self, lang: str | None = None) -> str:
        rng = self.rng
        styles = [
            lambda: "sk_live_" + _rand(rng, _ALNUM, rng.randint(24, 32)),
            lambda: "sk_test_" + _rand(rng, _ALNUM, rng.randint(24, 32)),
            lambda: "pk_live_" + _rand(rng, _ALNUM, rng.randint(24, 32)),
            lambda: "rk_" + _rand(rng, _ALNUM, 28),
            lambda: "ghp_" + _rand(rng, _ALNUM, 36),
            lambda: "gho_" + _rand(rng, _ALNUM, 36),
            lambda: "github_pat_" + _rand(rng, _ALNUM, 22) + "_" + _rand(rng, _ALNUM, 59),
            lambda: "AKIA" + _rand(rng, string.ascii_uppercase + string.digits, 16),
            lambda: "ASIA" + _rand(rng, string.ascii_uppercase + string.digits, 16),
            lambda: "xoxb-" + "-".join(str(rng.randint(10 ** 10, 10 ** 12))
                                       for _ in range(2)) + "-" + _rand(rng, _ALNUM, 24),
            lambda: "xapp-1-" + _rand(rng, string.ascii_uppercase, 9) + "-" + _rand(rng, _ALNUM, 24),
            lambda: "AIza" + _rand(rng, _ALNUM + "_-", 35),
            lambda: "glpat-" + _rand(rng, _ALNUM + "_-", 20),
            lambda: "npm_" + _rand(rng, _ALNUM, 36),
            lambda: "dop_v1_" + _rand(rng, "0123456789abcdef", 64),
            lambda: "SG." + _rand(rng, _ALNUM + "_-", 22) + "." + _rand(rng, _ALNUM + "_-", 43),
            lambda: "shpat_" + _rand(rng, "0123456789abcdef", 32),
            lambda: "sq0atp-" + _rand(rng, _ALNUM + "_-", 22),
        ]

        def generic() -> str:
            # Vendor-neutral keys (`key_…`, `api_…`): 137 of the benchmark's
            # 138 missed API_KEYs looked like this, and none of ours did.
            prefix = rng.choices(("key_", "api_", "apikey_", "svc_", "sk-live-", "sk-test-"),
                                 weights=(35, 35, 10, 10, 5, 5))[0]
            return prefix + _rand(rng, _ALNUM, rng.randint(24, 40))

        def make() -> str:
            return generic() if rng.random() < 0.45 else rng.choice(styles)()

        return self.pool.fresh("API_KEY", make)

    def access_token(self, lang: str | None = None) -> str:
        """A mixture, JWT at most ~25% (P2-1):

        - a JWT whose header and payload really are base64url JSON, so it
          starts with `eyJ` like a real one;
        - a token prefix (ACCESS_TOKEN_PREFIXES) + 20-64 base64url or hex
          characters;
        - a bare 32-64 character base64url (mixed case, with a digit) or
          lower-case hex token.
        """
        rng = self.rng

        def bare() -> str:
            while True:
                if rng.random() < 0.6:
                    v = _rand(rng, _B64URL, rng.randint(32, 64))
                    if not (any(c.isupper() for c in v) and any(c.islower() for c in v)
                            and any(c.isdigit() for c in v)):
                        continue
                else:
                    v = _rand(rng, _HEX, rng.randint(32, 64))
                # a bare body that happens to begin like a key would be a key
                if not v.startswith(API_KEY_PREFIXES):
                    return v

        def make() -> str:
            r = rng.random()
            if r < 0.25:
                return self._jwt()
            if r < 0.75:
                body = _B64URL if rng.random() < 0.7 else _HEX
                return rng.choice(ACCESS_TOKEN_PREFIXES) + _rand(rng, body, rng.randint(20, 64))
            return bare()

        return self.pool.fresh("ACCESS_TOKEN", make)

    def _jwt(self) -> str:
        rng = self.rng

        def b64(obj: dict) -> str:
            raw = json.dumps(obj, separators=(",", ":")).encode()
            return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

        alg = rng.choice(["HS256", "HS384", "HS512", "RS256", "ES256", "PS256"])
        header = {"alg": alg, "typ": "JWT"}
        if rng.random() < 0.4:
            header["kid"] = _rand(rng, _LOWER_NUM, rng.randint(8, 16))
        iat = rng.randint(1_700_000_000, 1_830_000_000)
        payload = {"sub": (str(rng.randint(10_000, 99_999_999)) if rng.random() < 0.5
                           else str(uuid.UUID(int=rng.getrandbits(128)))),
                   "iat": iat, "exp": iat + rng.choice([900, 3600, 86_400, 604_800])}
        if rng.random() < 0.5:
            payload["sid"] = _rand(rng, _B64URL, rng.randint(16, 24))
        if rng.random() < 0.3:
            payload["scope"] = rng.choice(["read", "read write", "openid profile", "admin"])
        sig_len = {"HS256": 43, "HS384": 64, "HS512": 86, "ES256": 86,
                   "RS256": 342, "PS256": 342}[alg]
        return f"{b64(header)}.{b64(payload)}.{_rand(rng, _B64URL, sig_len)}"

    def private_key(self, lang: str | None = None) -> str:
        rng = self.rng
        styles = [
            lambda: ("-----BEGIN RSA PRIVATE KEY-----\n"
                     + _rand(rng, _ALNUM + "+/", 64) + "\n"
                     + _rand(rng, _ALNUM + "+/", 64)
                     + "\n-----END RSA PRIVATE KEY-----"),
            lambda: ("-----BEGIN OPENSSH PRIVATE KEY-----\n"
                     + _rand(rng, _ALNUM + "+/", 64)
                     + "\n-----END OPENSSH PRIVATE KEY-----"),
            lambda: ("-----BEGIN PRIVATE KEY-----\n"
                     + _rand(rng, _ALNUM + "+/", 64) + "\n"
                     + _rand(rng, _ALNUM + "+/", 64)
                     + "\n-----END PRIVATE KEY-----"),
            # D-36a: no `ssh-rsa`/`ssh-ed25519` lines -- those are public keys
            # (negatives `public_key_ssh` writes them as look-alikes)
        ]
        return self.pool.fresh("PRIVATE_KEY", lambda: rng.choice(styles)())

    def url(self, lang: str | None = None) -> str:
        loc = self.loc(lang or "az")
        rng = self.rng

        def make() -> str:
            host = rng.choice(loc.corporate_domains)
            sub = rng.choice(["app", "portal", "auth", "id", "secure", "my",
                              "account", "dashboard", "login", "api", "link",
                              "share", "files", "docs", "www"])
            path = rng.choice(["/verify", "/reset", "/invite", "/callback",
                               "/session/resume", "/v2/auth", "/confirm",
                               "/activate", "/download", "/share", "/join",
                               "/unsubscribe", "/oauth/callback", "/magic"])
            token = _rand(rng, _ALNUM + "-_", rng.randint(22, 48))
            style = rng.random()
            if style < 0.55:
                param = rng.choice(sorted(CK.TOKEN_PARAMS))
                return f"https://{sub}.{host}{path}?{param}={token}"
            if style < 0.75:
                return f"https://{sub}.{host}{path}/{token}"
            if style < 0.86:
                return (f"https://{sub}.{host}{path}?uid={rng.randint(10000, 999999)}"
                        f"&token={token}")
            if style < 0.94:
                return f"https://{sub}.{host}{path}#{token}"
            return f"http://{sub}.{host}{path}?t={token}"

        return self.pool.fresh("URL", make)

    # -- Azerbaijan-local identifiers ---------------------------------------
    # AZ_FIN excludes I/O (34-char alphabet); AZ_PASSPORT_NUMBER's leading
    # letter includes them. These must never share a constant -- see
    # data/schema.md notes.
    AZ_FIN_ALPHABET = "".join(c for c in string.ascii_uppercase if c not in "IO") \
        + string.digits

    def az_fin(self, lang: str | None = None) -> str:
        return self.pool.fresh("AZ_FIN", lambda: _rand(self.rng, self.AZ_FIN_ALPHABET, 7))

    # -- fix round (D-30b): shapes for the targeted builder ----------------
    # New methods, as in P2-4: the defaults above keep drawing the same
    # random numbers, so LLM-path runs stay reproducible.
    CVV_DASHED_STYLES = ((2, 1), (1, 2), (2, 2))
    CVV_DASHED_WEIGHTS = (0.6, 0.2, 0.2)

    def card_security_code_dashed(self, lang: str | None = None) -> str:
        """A CVV with one dash between its digits (`12-3`, `1-23`, `12-34`)."""
        rng = self.rng

        def make() -> str:
            a, b = rng.choices(self.CVV_DASHED_STYLES, weights=self.CVV_DASHED_WEIGHTS)[0]
            return f"{_rand(rng, string.digits, a)}-{_rand(rng, string.digits, b)}"

        return self.pool.fresh("CARD_SECURITY_CODE", make)

    def zipcode_any_az(self, lang: str | None = None) -> str:
        """`AZ` + any four digits. `zipcode` draws from the 253 real postal
        codes (AZ0060-AZ7303); the model must learn the shape, not the list."""
        rng = self.rng
        return self.pool.fresh("ZIPCODE", lambda: f"AZ{rng.randint(0, 9999):04d}")

    # D-51h (D-34d: the shape decides, licence 2 letters + 6 digits, ID card
    # 2 letters + 7): v3's ID cards used only AA/AB (9 characters) or DYI/MYI
    # (10, 41% of them), while 59% of licences had other prefixes, so an
    # unfamiliar prefix meant "licence" (53 benchmark errors). ID cards now
    # take the licences' prefix mix -- AA/AB about 40% of the two-letter ones,
    # any other pair the rest -- and DYI/MYI rarely, so the length is the cue.
    ID_CARD_DYI_MYI_RATE = 0.08
    ID_CARD_AA_AB_RATE = 0.38

    def az_id_card_prefix(self) -> str:
        """A two-letter ID-card prefix: AA/AB at ID_CARD_AA_AB_RATE, else any
        pair except `AZ` (the ZIP and IBAN country code)."""
        rng = self.rng
        if rng.random() < self.ID_CARD_AA_AB_RATE:
            return rng.choice(("AA", "AB"))
        while True:
            pair = _rand(rng, string.ascii_uppercase, 2)
            if pair != "AZ":
                return pair

    def az_id_card_number(self, lang: str | None = None) -> str:
        rng = self.rng

        def make() -> str:
            if rng.random() < self.ID_CARD_DYI_MYI_RATE:
                prefix = rng.choice(["DYI", "MYI"])
            else:
                prefix = self.az_id_card_prefix()
            return prefix + _rand(rng, string.digits, 7)

        return self.pool.fresh("AZ_ID_CARD_NUMBER", make)

    def az_passport_number(self, lang: str | None = None) -> str:
        rng = self.rng
        return self.pool.fresh(
            "AZ_PASSPORT_NUMBER",
            lambda: rng.choice(string.ascii_uppercase) + _rand(rng, string.digits, 8))

    def az_voen(self, lang: str | None = None) -> str:
        """Tax ID. Check digit (position 9) is unverified -- see
        data/schema.md -- so it is a random digit, never a computed one."""
        rng = self.rng

        def make() -> str:
            territorial = _rand(rng, string.digits, 2)
            sequence = _rand(rng, string.digits, 6)
            check = _rand(rng, string.digits, 1)   # unverified, not computed
            type_digit = _rand(rng, string.digits, 1)
            base = territorial + sequence + check + type_digit
            if rng.random() < 0.1:
                return base + _rand(rng, string.digits, 5)   # branch form
            return base

        return self.pool.fresh("AZ_VOEN", make)

    def az_driver_license_number(self, lang: str | None = None) -> str:
        """Any of the 676 letter pairs + 6 digits, with AA/AB oversampled.

        AA/AB appeared ~21,909 times on ID cards and ~40 times on licences in
        the old corpus, so the model read them as "ID card" (224 benchmark
        licences labelled AZ_ID_CARD_NUMBER). The 6-digit body (ID cards have
        7) and the anchor word are what the model must learn to use instead.
        """
        rng = self.rng

        def make() -> str:
            if rng.random() < 0.40:
                prefix = rng.choice(("AA", "AB"))
            else:
                prefix = _rand(rng, string.ascii_uppercase, 2)
            return prefix + _rand(rng, string.digits, 6)

        return self.pool.fresh("AZ_DRIVER_LICENSE_NUMBER", make)

    # -- dispatch -----------------------------------------------------------
    def make(self, label: str, lang: str, **kw) -> str:
        fn = {
            "API_KEY": self.api_key, "ACCESS_TOKEN": self.access_token,
            "PRIVATE_KEY": self.private_key,
            "PAYMENT_CARD_NUMBER": self.payment_card_number, "IBAN": self.iban,
            "CARD_SECURITY_CODE": self.card_security_code,
            "IPV4_ADDRESS": self.ipv4_address, "IPV6_ADDRESS": self.ipv6_address,
            "MAC_ADDRESS": self.mac_address, "URL": self.url,
            "ICCID": self.iccid, "GIVENNAME": self.givenname,
            "SURNAME": self.surname, "EMAIL": self.email,
            "TELEPHONENUM": self.telephonenum, "DATE": self.date,
            "TIME": self.time_of_day, "AGE": self.age, "CITY": self.city,
            "STREET": self.street, "BUILDINGNUM": self.buildingnum,
            "ZIPCODE": self.zipcode,
            "AZ_FIN": self.az_fin, "AZ_ID_CARD_NUMBER": self.az_id_card_number,
            "AZ_PASSPORT_NUMBER": self.az_passport_number,
            "AZ_VOEN": self.az_voen,
            "AZ_DRIVER_LICENSE_NUMBER": self.az_driver_license_number,
        }[label]
        return fn(lang, **kw)
