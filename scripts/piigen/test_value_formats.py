"""P2-1 acceptance check: token/key, IPv6/MAC and licence/ID value formats.

No network, no model. 10,000 samples per label from a fresh ValuePool
(state_path=None). Checks the shares the task sets, that every variant is
present, that every value passes the independent validator, that the ID card
is unchanged, and that the token and key prefix lists are disjoint.

    python scripts/piigen/test_value_formats.py
"""

from __future__ import annotations

import collections
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from piigen import checksums as CK                                    # noqa: E402
from piigen.validate import validate_example, value_valid             # noqa: E402
from piigen.values import (ACCESS_TOKEN_PREFIXES, API_KEY_PREFIXES,   # noqa: E402
                           ValueFactory, ValuePool)

N = 10_000
LABELS = ("ACCESS_TOKEN", "API_KEY", "IPV6_ADDRESS", "MAC_ADDRESS",
          "AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER")

PASS = 0
FAIL = 0
FAILURES: list[str] = []
REPORT: list[str] = []


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg)


def share(values: list[str], pred) -> float:
    return sum(1 for v in values if pred(v)) / len(values)


POOL = ValuePool(state_path=None)
FACTORY = ValueFactory(random.Random(20260930), POOL)
SAMPLES = {label: [FACTORY.make(label, "az") for _ in range(N)] for label in LABELS}


# --------------------------------------------------------------------------- #
def test_tokens() -> None:
    toks = SAMPLES["ACCESS_TOKEN"]
    eyj = share(toks, lambda v: v.startswith("eyJ"))
    three_seg = share(toks, lambda v: v.count(".") == 2)
    prefixed = share(toks, lambda v: v.startswith(ACCESS_TOKEN_PREFIXES))
    REPORT.append(f"ACCESS_TOKEN  eyJ {eyj:.3f}  3-segment {three_seg:.3f}  prefixed {prefixed:.3f}")
    check(eyj <= 0.30, f"token eyJ share {eyj:.3f} > 0.30")
    check(three_seg <= 0.30, f"token 3-segment share {three_seg:.3f} > 0.30")
    check(eyj > 0.10, f"token eyJ share {eyj:.3f}: the JWT family has vanished")
    # every JWT's header really is base64url JSON
    check(all(v.startswith("eyJ") for v in toks if v.count(".") == 2),
          "a 3-segment token does not start with eyJ")
    for p in ACCESS_TOKEN_PREFIXES:
        check(any(v.startswith(p) for v in toks), f"token prefix {p!r} never generated")
    bare = [v for v in toks if v.count(".") != 2 and not v.startswith(ACCESS_TOKEN_PREFIXES)]
    check(any(re.fullmatch(r"[0-9a-f]{32,64}", v) for v in bare), "no bare hex token")
    check(any(re.fullmatch(r"[A-Za-z0-9_-]{32,64}", v) and not re.fullmatch(r"[0-9a-f]+", v)
              for v in bare), "no bare base64url token")
    def body(v: str) -> str:
        return v[len(next(p for p in ACCESS_TOKEN_PREFIXES if v.startswith(p))):]
    check(all(20 <= len(body(v)) <= 64 for v in toks if v.startswith(ACCESS_TOKEN_PREFIXES)),
          "a prefixed token body is outside 20-64 characters")


def test_keys() -> None:
    keys = SAMPLES["API_KEY"]
    generic = share(keys, lambda v: v.startswith(("key_", "api_", "apikey_", "svc_",
                                                  "sk-live-", "sk-test-")))
    REPORT.append(f"API_KEY       generic prefixes {generic:.3f}")
    for p in ("key_", "api_", "apikey_", "svc_", "sk-live-", "sk-test-"):
        check(any(v.startswith(p) for v in keys), f"key prefix {p!r} never generated")
    check(all(v.startswith(API_KEY_PREFIXES) for v in keys),
          "a generated key has a prefix missing from API_KEY_PREFIXES")
    check(0.30 <= generic <= 0.60, f"generic key share {generic:.3f} outside 0.30-0.60")


def test_prefixes_disjoint() -> None:
    for a in ACCESS_TOKEN_PREFIXES:
        for b in API_KEY_PREFIXES:
            check(not a.startswith(b) and not b.startswith(a),
                  f"token prefix {a!r} and key prefix {b!r} overlap")
    # and at the validator: no generated token is a valid key, and vice versa
    check(not any(CK.api_key_valid(v) for v in SAMPLES["ACCESS_TOKEN"]),
          "a generated ACCESS_TOKEN also passes the API_KEY validator")
    check(not any(CK.access_token_valid(v) for v in SAMPLES["API_KEY"]),
          "a generated API_KEY also passes the ACCESS_TOKEN validator")


def test_ipv6() -> None:
    ips = SAMPLES["IPV6_ADDRESS"]
    comp = share(ips, lambda v: "::" in v)
    REPORT.append(f"IPV6_ADDRESS  '::' {comp:.3f}")
    check(comp >= 0.60, f"IPv6 '::' share {comp:.3f} < 0.60")
    check(comp <= 0.70, f"IPv6 '::' share {comp:.3f} > 0.70 (full form should stay ~40%)")
    lo = [v.lower() for v in ips]
    variants = {
        "'::' at start": lambda v: v.startswith("::") and not v.startswith("::ffff:"),
        "'::' in middle": lambda v: "::" in v.strip(":"),
        "'::' at end": lambda v: v.endswith("::"),
        "<prefix>::1": lambda v: v.endswith("::1") and v != "::1",
        "IPv4-embedded ::ffff:": lambda v: v.startswith("::ffff:") and "." in v,
        "2001:db8 prefix": lambda v: v.startswith("2001:db8") or v.startswith("2001:0db8"),
        "fd00 prefix": lambda v: v.startswith("fd00"),
        "fe80 prefix": lambda v: v.startswith("fe80"),
        "full 8-group": lambda v: "::" not in v and v.count(":") == 7,
    }
    for name, pred in variants.items():
        check(any(pred(v) for v in lo), f"IPv6 variant missing: {name}")
    full = [v for v in lo if "::" not in v]
    check(any(any(len(g) < 4 for g in v.split(":")) for v in full),
          "IPv6 variant missing: dropped leading zeros")
    check(any(any(len(g) == 4 and g.startswith("0") for g in v.split(":")) for v in full),
          "IPv6 variant missing: kept leading zeros")
    check(any(v == v.upper() and re.search(r"[A-F]", v) for v in ips), "IPv6 variant missing: upper case")
    check(any(re.search(r"[a-f]", v) and re.search(r"[A-F]", v) for v in ips),
          "IPv6 variant missing: mixed case")
    check("::1" not in ips, "bare ::1 generated (blocklisted placeholder)")


def test_mac() -> None:
    macs = SAMPLES["MAC_ADDRESS"]
    forms = {
        "colon": lambda v: re.fullmatch(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", v),
        "hyphen": lambda v: re.fullmatch(r"(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}", v),
        "dotted": lambda v: re.fullmatch(r"(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}", v),
    }
    parts = []
    for name, pred in forms.items():
        s = share(macs, pred)
        parts.append(f"{name} {s:.3f}")
        check(s >= 0.10, f"MAC {name} share {s:.3f} < 0.10")
    REPORT.append("MAC_ADDRESS   " + "  ".join(parts))
    check(any(re.search(r"[a-f]", v) and not re.search(r"[A-F]", v) for v in macs), "MAC: no lower case")
    check(any(re.search(r"[A-F]", v) and not re.search(r"[a-f]", v) for v in macs), "MAC: no upper case")
    check(any(re.search(r"[a-f]", v) and re.search(r"[A-F]", v) for v in macs), "MAC: no mixed case")


def test_licence_and_id() -> None:
    lic = SAMPLES["AZ_DRIVER_LICENSE_NUMBER"]
    aa_ab = share(lic, lambda v: v[:2] in ("AA", "AB"))
    pairs = len({v[:2] for v in lic})
    REPORT.append(f"LICENCE       AA/AB {aa_ab:.3f}  distinct prefixes {pairs}")
    check(aa_ab >= 0.35, f"licence AA/AB share {aa_ab:.3f} < 0.35")
    check(all(re.fullmatch(r"[A-Z]{2}\d{6}", v) for v in lic), "a licence is not 2 letters + 6 digits")
    check(pairs >= 600, f"licence uses only {pairs} of 676 letter pairs")
    # D-51h (D-34d: the shape decides): an ID card is any two letters (or
    # DYI/MYI) + 7 digits, so the prefix carries no signal; DYI/MYI are rare
    ids = SAMPLES["AZ_ID_CARD_NUMBER"]
    check(all(re.fullmatch(r"(?:[A-Z]{2}|DYI|MYI)\d{7}", v) for v in ids),
          "ID card: not two letters (or DYI/MYI) + 7 digits")
    two = [v for v in ids if re.fullmatch(r"[A-Z]{2}\d{7}", v)]
    other = share(ids, lambda v: v[:2] not in ("AA", "AB") and v[:3] not in ("DYI", "MYI"))
    dyi = share(ids, lambda v: v[:3] in ("DYI", "MYI"))
    id_aa_ab = share(two, lambda v: v[:2] in ("AA", "AB"))
    REPORT.append(f"ID CARD       AA/AB {share(ids, lambda v: v[:2] in ('AA', 'AB')):.3f}  other two-letter "
                  f"{other:.3f}  DYI/MYI {dyi:.3f}  distinct prefixes {len({v[:2] for v in two})}")
    check(other >= 0.45, f"ID card: other two-letter prefixes {other:.3f} < 0.45 (most should be)")
    check(0.02 <= dyi <= 0.15, f"ID card: DYI/MYI share {dyi:.3f} outside 2-15%")
    check(abs(id_aa_ab - aa_ab) <= 0.08,
          f"ID card AA/AB share among two-letter prefixes {id_aa_ab:.3f} far from the licences' {aa_ab:.3f}")
    check(len({v[:2] for v in two}) >= 500, "ID cards use few letter pairs")
    check(not any(v.startswith("AZ") for v in ids), "an ID card starts with AZ (the ZIP/IBAN country code)")
    check(all(value_valid("AZ_ID_CARD_NUMBER", v)[0] for v in ids), "an ID card fails value_valid")
    check(not (set(lic) & set(ids)), "a licence value equals an ID card value")
    # the two shapes never collide: no licence is a valid ID card, no ID card a valid licence
    check(not any(value_valid("AZ_ID_CARD_NUMBER", v)[0] for v in lic), "a licence passes as an ID card")
    check(not any(value_valid("AZ_DRIVER_LICENSE_NUMBER", v)[0] for v in ids), "an ID card passes as a licence")
    f5 = ValueFactory(random.Random(5), ValuePool(state_path=None))
    pairs = [f5.licence_and_id_same_prefix() for _ in range(400)]
    check(all(l[:2] == i[:2] and len(l) == 8 and len(i) == 9 for l, i in pairs),
          "licence/ID contrast pairs: same prefix, 8 vs 9 characters")
    check(len({l[:2] for l, _ in pairs} - {"AA", "AB"}) >= 50, "licence/ID contrast pairs use AA/AB only")


def test_value_valid() -> None:
    for label in LABELS:
        bad = [v for v in SAMPLES[label] if not value_valid(label, v)[0]]
        check(not bad, f"{label}: {len(bad)} values fail value_valid, e.g. {bad[:3]}")


def test_spans_pass_validate_example() -> None:
    """value_valid is not the only gate: the whole-record validator also
    checks the span's edges. An IPv6 address compressed at the end
    (`2001:db8:1::`) once failed there as "ends with punctuation"."""
    for label in LABELS:
        bad = []
        for v in SAMPLES[label][:3000]:
            text = f"Sənəddə göstərilən məlumat {v} kimi qeyd olunub və sistemdə yoxlanılıb."
            s = text.index(v)
            problems = [p for p in validate_example(
                {"text": text, "lang": "az",
                 "entities": [{"start": s, "end": s + len(v), "label": label, "text": v}]})
                if not p.startswith("language")]
            if problems:
                bad.append((v, problems[0]))
        check(not bad, f"{label}: {len(bad)} values fail validate_example in a sentence, "
                       f"e.g. {bad[:2]}")


def test_pool() -> None:
    for label in LABELS:
        check(POOL.exhausted[label] == 0,
              f"{label}: ValuePool exhausted {POOL.exhausted[label]} times (new forms starved)")
        distinct = len(set(SAMPLES[label]))
        check(distinct >= 0.99 * N, f"{label}: only {distinct} distinct of {N}")


# --------------------------------------------------------------------------- #
# P2-4b: name spelling/script variants and the boundary shapes
# --------------------------------------------------------------------------- #
_CYR = re.compile(r"[Ѐ-ӿ]")
_LAT = re.compile(r"[A-Za-zƏəÇçĞğIıİÖöŞşÜü]")


def test_name_variants() -> None:
    from piigen.values import az_english_spelling
    check(az_english_spelling("Məmmədov") == "Mammadov", "Məmmədov -> Mammadov")
    check(az_english_spelling("Cəfərova") == "Jafarova", "Cəfərova -> Jafarova")
    check(az_english_spelling("Xəlilov") == "Khalilov", "Xəlilov -> Khalilov")
    f = ValueFactory(random.Random(1), ValuePool(state_path=None))
    check(f.name_spellings("Məmmədov", "az").get("cyrillic") == "Маммадов", "Məmmədov -> Маммадов")
    check(f.name_spellings("Иванов", "ru") == {"latin": "Ivanov"}, "a Cyrillic name gets a Latin form")
    # the en/tr/ru locales carry Azerbaijani names: decided by the name's script
    forms = f.name_spellings("Uğurluyev", "en")
    check(forms and all(not (_CYR.search(v) and _LAT.search(v)) for v in forms.values()),
          f"never a mixed-script form: {forms}")
    for lang in ("az", "en", "tr", "ru"):
        pool = ValuePool(state_path=None)
        fac = ValueFactory(random.Random(3), pool)
        names = [fac.givenname(lang) for _ in range(3000)] + [fac.surname(lang) for _ in range(3000)]
        var = [n for n in names if n in fac.name_variants]
        rate = len(var) / len(names)
        check(0.08 <= rate <= 0.12, f"{lang}: {rate:.1%} of name mints are variants (~10%)")
        check(all(value_valid("SURNAME", v)[0] for v in var), f"{lang}: every variant passes value_valid")
        check(all(not (_CYR.search(v) and _LAT.search(v)) for v in var), f"{lang}: no mixed-script variant")
        canon = {c for c, _k in fac.name_variants.values()}
        check(not (set(var) & set(pool.counts["GIVENNAME"]) - canon) and
              all(c in pool.counts["GIVENNAME"] or c in pool.counts["SURNAME"] for c in canon),
              f"{lang}: the pool holds the canonical form, not the variant")
        REPORT.append(f"name variants {lang}: {rate:.1%} "
                      + str(dict(collections.Counter(k for _c, k in fac.name_variants.values()))))
    # the other values keep exactly the draws they had before variants existed
    off = ValueFactory(random.Random(9), ValuePool(state_path=None), name_variant_rate=0.0)
    on = ValueFactory(random.Random(9), ValuePool(state_path=None))
    a = [off.surname("az") for _ in range(300)] + [off.iban("az") for _ in range(50)]
    b = [on.surname("az") for _ in range(300)] + [on.iban("az") for _ in range(50)]
    check([on.name_variants.get(x, (x,))[0] for x in b] == a, "variants do not shift the main random stream")
    check(not off.name_variants, "name_variant_rate=0 writes no variant")


def test_boundary_values() -> None:
    from piigen.values import PEM_KINDS, PEM_WIDTHS, pem_max_length
    f = ValueFactory(random.Random(4), ValuePool(state_path=None))
    phones = [f.telephone_grouped() for _ in range(2000)]
    check(all(value_valid("TELEPHONENUM", p)[0] and " " in p for p in phones),
          "grouped phones: valid and space-separated")
    ibans = [f.iban_az_grouped() for _ in range(2000)]
    check(all(value_valid("IBAN", v)[0] and len(v.replace(" ", "")) == 28 and v.startswith("AZ")
              and all(len(g) == 4 for g in v.split(" ")) for v in ibans),
          "grouped AZ IBANs: valid, 28 characters, groups of four")
    urls = [f.url_query() for _ in range(2000)]
    check(all(value_valid("URL", u)[0] for u in urls), "query-string URLs: all valid")
    check(all("&" in u.split("?", 1)[1] for u in urls), "query-string URLs: several parameters")
    last = sum(u.split("?", 1)[1].split("&")[-1].split("=")[0] in CK.TOKEN_PARAMS for u in urls)
    check(0.2 < last / len(urls) < 0.8, f"the token is not always the last parameter ({last / len(urls):.0%})")
    keys = [f.private_key_varied() for _ in range(1500)]
    check(all(value_valid("PRIVATE_KEY", k)[0] for k in keys), "PEM keys: all valid")
    widths = collections.Counter(max(len(x) for x in k.split("\n")[1:-1]) for k in keys)
    check(set(PEM_WIDTHS) <= set(widths), f"PEM widths 64 and 76 both present: {dict(widths)}")
    check(all(len(x) <= max(PEM_WIDTHS) for k in keys for x in k.split("\n")[1:-1]),
          "no PEM body line wider than 76")
    lengths = sorted(len(k) for k in keys)
    check(lengths[0] < 200 and lengths[-1] > 1600, f"PEM lengths vary: {lengths[0]}-{lengths[-1]}")
    check(all(len(k) <= max(pem_max_length(kind) for kind in PEM_KINDS) for k in keys),
          "pem_max_length bounds every key")
    small = [f.private_key_varied(max_chars=700) for _ in range(500)]
    check(all(len(k) <= 700 for k in small), "max_chars=700 keeps every key under 700 characters")
    try:
        f.private_key_varied(max_chars=50)
        check(False, "max_chars smaller than every kind raises")
    except ValueError:
        check(True, "max_chars smaller than every kind raises")


TESTS = [
    ("name spelling/script variants (P2-4b)", test_name_variants),
    ("boundary shapes: grouped phone/IBAN, query URLs, PEM (P2-4b)", test_boundary_values),
    ("ACCESS_TOKEN mixture", test_tokens),
    ("API_KEY generic prefixes", test_keys),
    ("token/key prefixes disjoint", test_prefixes_disjoint),
    ("IPv6 compression and variants", test_ipv6),
    ("MAC separators and case", test_mac),
    ("licence AA/AB; ID card any two letters (D-51h)", test_licence_and_id),
    ("100% value_valid", test_value_valid),
    ("spans pass validate_example in a sentence", test_spans_pass_validate_example),
    ("ValuePool does not starve the new forms", test_pool),
]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print()
    for line in REPORT:
        print("  " + line)
    print()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
