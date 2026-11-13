"""P2-2 acceptance check: anchored decoys and non-PII look-alikes.

No network, no model. For every kind in negatives.ANCHORED_DECOYS, 1,000
samples, checked against code that did not make them (rule R4):

  * ordinary decoys fail value_valid(resembles, value). The NER-only name
    labels have no validator (value_valid accepts any string), so for them
    the independent check is that the value is in no locale's name pool;
  * contextual decoys (`otaq 247`) are well-formed values whose anchors must
    not be words that license the resembled label;
  * policy decoys (D-2) pass value_valid, which is why they are tagged;
  * decoys of anchor_required labels sit next to an anchor that really
    licenses that label (anchors/az.py), except the two kinds that imitate a
    date under a clause/version word;
  * no value equals a value the benchmark planted, except the D-2 allowlist;
  * every kind is sampled by llm/specs.py, and the brief carries its anchor.

    python scripts/piigen/test_anchored_decoys.py
"""

from __future__ import annotations

import collections
import logging
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from piigen.anchors import ANCHOR_REQUIRED, has_anchor                 # noqa: E402
from piigen.config import GeneratorConfig                             # noqa: E402
from piigen.locales import LOCALES                                    # noqa: E402
from piigen.llm.specs import SpecSampler                              # noqa: E402
from piigen.negatives import (ALL_DECOY_KINDS, ANCHORED_DECOYS,       # noqa: E402
                              active_decoy_kinds, benchmark_planted_values,
                              plant_decoy, policy_allowlist)
from piigen.validate import value_valid                               # noqa: E402
from piigen.values import ValueFactory, ValuePool                     # noqa: E402

N = 1_000
NAME_LABELS = ("GIVENNAME", "SURNAME", "CITY", "STREET")
# These imitate a date under a clause or version word, as the benchmark's
# `müqavilə bəndi 18.9.1` and `versiya v8.3.34` do: no date anchor by design.
UNLICENSED_BY_DESIGN = {"date_clause_number", "date_version_string"}
# ZIPCODE has no anchor_required pattern; these are the words that would
# license a postal code, written here independently of negatives.py.
_ZIP_LICENSING = re.compile(r"(?i)poçt|poct|indeks|zip|postal")
# Kinds in ALL_DECOY_KINDS with no anchor: written only by the targeted
# builder, never planted (P2-4d: a name used as the ordinary word it is;
# D-34: the village documents' control words).
UNANCHORED = {"homograph_noun", "village_descriptor", "kinship_possessive",
              # D-51h: the non-name controls of the `namelist` documents
              "namelist_control", "role_word_control", "signature_title_only",
              # v3_shadow_shapes.md lead 1: the `time_seconds` line stamps
              "time_line_stamp",
              # v4.1 A5: private-key blocks with a placeholder body
              "private_key_placeholder",
              # v4.1 A5: role and heading words opening a line
              "line_start_control",
              # D-57: age-shaped numbers (S1), ALL-CAPS headings (S2), place words (item 5)
              "age_shaped_number", "caps_heading_control", "place_word_topic"}
ANCHORED = {k.kind: k for ks in ANCHORED_DECOYS.values() for k in ks}

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


RNG = random.Random(20261001)
SAMPLES = {k.kind: [plant_decoy(k, RNG) for _ in range(N)] for k in active_decoy_kinds()}

_NAME_POOLS = {
    "GIVENNAME": {n.casefold() for loc in LOCALES.values()
                  for n in list(loc.first_names_m) + list(loc.first_names_f)},
    "CITY": {c.casefold() for loc in LOCALES.values() for c in loc.cities},
}


def _invalid(resembles: str, value: str) -> bool:
    if resembles in _NAME_POOLS:
        return value.casefold() not in _NAME_POOLS[resembles]
    if resembles == "SURNAME":
        # D-51h `code_in_name_slot` (`KRM482`): no surname carries a digit
        return bool(re.search(r"\d", value))
    return not value_valid(resembles, value)[0]


# --------------------------------------------------------------------------- #
def test_catalogue() -> None:
    kinds = list(ANCHORED.values())
    check(len(kinds) == sum(len(v) for v in ANCHORED_DECOYS.values()),
          "duplicate kind names in ANCHORED_DECOYS")
    check(set(ALL_DECOY_KINDS) - set(ANCHORED) == UNANCHORED,
          f"unanchored kinds: {sorted(set(ALL_DECOY_KINDS) - set(ANCHORED))}")
    for name in UNANCHORED:
        k = ALL_DECOY_KINDS[name]
        check(k.contextual and not k.anchors and not k.policy,
              f"{name}: an unanchored kind is contextual, with no anchors")
    check(all(k.resembles == label for label, ks in ANCHORED_DECOYS.items() for k in ks),
          "a kind is filed under a label it does not resemble")
    check(all(k.kind.startswith("policy_") == k.policy for k in kinds),
          "policy kinds must be exactly the ones named policy_*")
    check(not any(k.policy and k.contextual for k in kinds), "a kind is both policy and contextual")
    for k in kinds:
        check(k.anchors and all(a.count("{v}") == 1 for a in k.anchors),
              f"{k.kind}: every anchor needs exactly one {{v}}")
    check(len(active_decoy_kinds()) == len(kinds),
          f"inactive kinds: {sorted(set(ANCHORED) - {k.kind for k in active_decoy_kinds()})}")
    check(not UNANCHORED & {k.kind for k in active_decoy_kinds()}, "an unanchored kind is planted")
    # the rows of the P2-2 table
    for label in ("CARD_SECURITY_CODE", "TIME", "AGE", "DATE", "ZIPCODE", "AZ_FIN",
                  "AZ_VOEN", "AZ_PASSPORT_NUMBER", "AZ_ID_CARD_NUMBER",
                  "AZ_DRIVER_LICENSE_NUMBER", "IPV4_ADDRESS", "IPV6_ADDRESS",
                  "MAC_ADDRESS", "PAYMENT_CARD_NUMBER", "ICCID", "IBAN", "CITY",
                  "SURNAME", "STREET", "GIVENNAME", "BUILDINGNUM"):
        check(bool(ANCHORED_DECOYS.get(label)), f"no decoy kind resembles {label}")


def test_ordinary_invalid() -> None:
    for kind, ds in SAMPLES.items():
        k = ALL_DECOY_KINDS[kind]
        if k.policy or k.contextual:
            continue
        bad = [d.value for d in ds if not _invalid(k.resembles, d.value)]
        check(not bad, f"{kind}: {len(bad)}/{N} decoys are VALID {k.resembles}, e.g. {bad[:3]}")


def test_policy_valid() -> None:
    allow = policy_allowlist()
    for kind, ds in SAMPLES.items():
        k = ALL_DECOY_KINDS[kind]
        if not k.policy:
            continue
        bad = [d.value for d in ds if not value_valid(k.resembles, d.value)[0]]
        check(not bad, f"{kind}: {len(bad)}/{N} policy decoys fail value_valid, e.g. {bad[:3]}")
        check(all(d.policy for d in ds), f"{kind}: planted decoy not flagged policy")
    for kind in ("policy_sequential", "policy_passport_dummy", "policy_test_card"):
        check(all(d.value in allow for d in SAMPLES[kind]),
              f"{kind}: a value outside the D-2 allowlist")


def test_contextual() -> None:
    for kind, ds in SAMPLES.items():
        k = ALL_DECOY_KINDS[kind]
        if not k.contextual:
            continue
        licensing = ANCHOR_REQUIRED.get(k.resembles) or \
            (_ZIP_LICENSING if k.resembles == "ZIPCODE" else None)
        check(licensing is not None, f"{kind}: no independent licensing rule for {k.resembles}")
        for anchor in k.anchors:
            words = anchor.replace("{v}", " ")
            check(not (licensing and licensing.search(words)),
                  f"{kind}: anchor {anchor!r} would license {k.resembles}")
        bad = [d.value for d in ds if not value_valid(k.resembles, d.value)[0]]
        check(not bad, f"{kind}: contextual values should be well-formed, e.g. {bad[:3]}")


def test_anchor_licenses() -> None:
    for kind, ds in SAMPLES.items():
        k = ALL_DECOY_KINDS[kind]
        if k.contextual or k.resembles not in ANCHOR_REQUIRED or kind in UNLICENSED_BY_DESIGN:
            continue
        for d in ds[:200]:
            text = f"Qeyddə {d.phrase} göstərilib."
            start = text.index(d.phrase) + d.phrase.index(d.value)
            if not has_anchor(k.resembles, text, start, start + len(d.value)):
                check(False, f"{kind}: {d.phrase!r} is not next to a {k.resembles} anchor")
                break
        else:
            check(True, "")


def test_phrases() -> None:
    for kind, ds in SAMPLES.items():
        k = ALL_DECOY_KINDS[kind]
        check(all(d.phrase in {a.replace("{v}", d.value) for a in k.anchors} for d in ds),
              f"{kind}: phrase is not one of its anchors filled with the value")
        check(all(d.resembles == k.resembles and d.kind == kind for d in ds),
              f"{kind}: planted decoy carries the wrong kind/resembles")


def test_no_benchmark_values() -> None:
    planted, allow = benchmark_planted_values(), policy_allowlist()
    check(len(planted) > 2000, f"benchmark planted values not loaded ({len(planted)})")
    for kind, ds in SAMPLES.items():
        hits = sorted({d.value for d in ds if d.value in planted and d.value not in allow})
        check(not hits, f"{kind}: benchmark values used as decoys: {hits[:5]}")


def test_distinct() -> None:
    small = {"policy_sequential", "policy_passport_dummy", "policy_test_card",
             "sentence_initial_genitive", "sentence_initial_locative",
             "cvv_1_2_digits", "floor_number", "iccid_short_prefix",
             "age_negative", "zip_wrong_length", "policy_foreign_brand", "cvv_sequential_5",
             "zip_two_digits",          # 2 digits: at most 90 values
             "policy_sequential_time",  # D-52c: a fixed list of sequential dummies
             "fin_dummy_pattern",       # v4.2: a fixed list of patterned FIN dummies
             "time_hour_near",          # v4.2: hours 24-29, 359 values
             "time_minute_near",        # v4.2: minutes 60-69, 240 values
             "iban_country_code",       # D-55b: a bare `AZ` (or `TR`, `GE`)
             "policy_sequential_ipv4"}  # D-56a: a fixed list of sequential dummies
    for kind, ds in SAMPLES.items():
        distinct = len({d.value for d in ds})
        REPORT.append(f"{kind:28} distinct {distinct:4}/{N}  e.g. {ds[0].phrase}")
        if kind not in small:
            check(distinct >= 0.5 * N, f"{kind}: only {distinct} distinct values in {N}")


def test_specs_sampling() -> None:
    cfg = GeneratorConfig()
    cfg.hard_negative_rate = 1.0
    cfg.edge_case_rate = 0.0
    sampler = SpecSampler(cfg, ValueFactory(random.Random(7), ValuePool(state_path=None)),
                          random.Random(11))
    seen = collections.Counter()
    ok_phrase = True
    specs = [sampler.sample(i) for i in range(4000)]
    for s in specs:
        for d in s.anchored_decoys:
            seen[d["kind"]] += 1
            ok_phrase &= d["phrase"] in s.hard_negatives and d["value"] in d["phrase"]
    missing = sorted(set(ANCHORED) - set(seen))
    check(not UNANCHORED & set(seen), "llm/specs.py samples an unanchored kind")
    check(not missing, f"kinds never sampled by llm/specs.py: {missing}")
    check(ok_phrase, "an anchored decoy's phrase is missing from the brief's decoys")
    share = sum(len(s.anchored_decoys) for s in specs) / max(1, sum(len(s.hard_negatives) for s in specs))
    REPORT.append(f"specs.py: {len(specs)} az briefs, anchored share of decoys {share:.2f}, "
                  f"{len(seen)} kinds seen")
    check(0.5 <= share <= 0.7, f"anchored share of decoys {share:.2f} outside 0.5-0.7")
    # non-az briefs never get Azerbaijani anchor phrases
    cfg_en = GeneratorConfig(lang_weights={"en": 1.0})
    cfg_en.hard_negative_rate = 1.0
    cfg_en.edge_case_rate = 0.0
    en = SpecSampler(cfg_en, ValueFactory(random.Random(7), ValuePool(state_path=None)),
                     random.Random(12))
    logging.disable(logging.WARNING)    # the en locale lacks city/phone pools here
    try:
        check(not any(en.sample(i).anchored_decoys for i in range(300)),
              "an English brief got Azerbaijani anchored decoys")
    finally:
        logging.disable(logging.NOTSET)


# --------------------------------------------------------------------------- #
# D-51h / D-51d
# --------------------------------------------------------------------------- #
D51H_KINDS = ("voen_short_number", "fin_short_number", "id_card_short_number", "token_short_number",
              "api_key_short_number", "code_in_name_slot", "room_code", "door_code",
              "mac_fragment_dashed", "iban_fragment_short", "ipv4_short_over_255",
              "ipv4_three_octets", "ipv4_placeholder", "card_wrong_length")
# labels whose validity depends on an anchor word (a bare `412` is a valid CVV,
# AGE or building number shape), and the loose phone check (7-15 digits)
CONTEXT_LABELS = set(ANCHOR_REQUIRED) | {"TELEPHONENUM", "GIVENNAME", "SURNAME", "CITY", "STREET"}
# D-51h names `AA99AAA` IBAN fragments as look-alikes after IBAN/hesab words,
# though the shape is also a 7-character FIN (the policy is the decision's)
FIN_SHAPED_BY_DESIGN = {"iban_fragment_short"}


def test_d51h_kinds() -> None:
    from piigen.config import ENTITY_TYPES
    from piigen.negatives import (ADVERSARIAL, FAMILY_RESEMBLES, HARD_NEGATIVES,
                                  public_key_ed25519)
    for kind in D51H_KINDS:
        check(kind in ANCHORED, f"D-51h kind {kind} is not an anchored kind")
    for kind in D51H_KINDS:
        k = ALL_DECOY_KINDS[kind]
        values = [d.value for d in SAMPLES[kind]]
        if not k.contextual:
            # never a valid value of ANY pattern label (privacy: a look-alike
            # that is a real value of another label would teach a leak)
            for label in ENTITY_TYPES:
                if label in CONTEXT_LABELS or (label == "AZ_FIN" and kind in FIN_SHAPED_BY_DESIGN):
                    continue
                bad = [v for v in values if value_valid(label, v)[0]]
                check(not bad, f"{kind}: {len(bad)} values are valid {label}, e.g. {bad[:3]}")
        # (date_valid accepts any value with a word in it as a worded date)
        check(not any(value_valid("DATE", v)[0] for v in values if not re.search(r"[A-Za-z]{2}", v)),
              f"{kind}: a value is a real date")
    shorts = [d.value for k in ("voen_short_number", "fin_short_number", "id_card_short_number",
                                "token_short_number", "api_key_short_number") for d in SAMPLES[k]]
    check(all(re.fullmatch(r"\d{2,3}", v) for v in shorts), "short numbers are 2-3 digits")
    macs = [d.value for d in SAMPLES["mac_fragment_dashed"]]
    check(all(re.fullmatch(r"[0-9A-F]{2}(?:-[0-9A-F]{2}){2,3}", v) for v in macs)
          and sum(v.replace("-", "").isdigit() for v in macs) >= 0.6 * len(macs),
          "MAC fragments: 3-4 dashed groups, mostly digits only")
    check(all(re.fullmatch(r"AZ\d{2}[A-Z]{3}", d.value) for d in SAMPLES["iban_fragment_short"]),
          "IBAN fragments are AZ + 2 digits + 3 letters")
    check(all(len(d.value.split(".")) == 3 for d in SAMPLES["ipv4_three_octets"]), "3-octet IPv4 shapes")
    check(all(sum(int(o) > 255 for o in d.value.split(".")) == 1 and
              sum(len(o) == 1 for o in d.value.split(".")) == 3 for d in SAMPLES["ipv4_short_over_255"]),
          "short IPv4 shapes: one octet over 255, three single digits")
    cards = [re.sub(r"\D", "", d.value) for d in SAMPLES["card_wrong_length"]]
    check(all(len(c) in (13, 14, 17) for c in cards) and sum(len(c) == 13 for c in cards) >= 0.6 * len(cards),
          "wrong-length cards: 13 (mostly), 14 or 17 digits, never 15/16")
    check(not any(len(c) == 13 and c[0] in "456" for c in cards),
          "a 13-digit look-alike starts like a Visa or Maestro")
    for kind in ("room_code", "door_code"):
        check(all(value_valid("CARD_SECURITY_CODE", d.value)[0] for d in SAMPLES[kind]),
              f"{kind}: a CVV-shaped number (contextual)")
    # D-51d: the checksum-only kinds are gone everywhere
    gone = {"card_luhn_invalid", "tracking_code_15_16", "LOYALTY_CARD_LUHN_BAD", "IBAN_BAD_CHECKSUM"}
    check(not gone & (set(ALL_DECOY_KINDS) | set(ADVERSARIAL) | set(FAMILY_RESEMBLES) | set(HARD_NEGATIVES)),
          "D-51d: a checksum-only look-alike kind is still generated")
    rng = random.Random(3)
    imei = [ADVERSARIAL["IMEI_BAD_LUHN"]("az", rng) for _ in range(2000)]
    check(not any(v.startswith(("34", "37")) for v in imei), "an IMEI look-alike has an Amex prefix")
    # D-51h: any two letters + 7 digits is an ID card, so no look-alike or
    # hard negative may have that shape (or a licence's 2 + 6)
    for kind, ds in SAMPLES.items():
        for label in ("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"):
            bad = [d.value for d in ds if value_valid(label, d.value)[0]]
            check(not bad, f"{kind}: {len(bad)} values are valid {label}, e.g. {bad[:3]}")
    for fam, fn in list(HARD_NEGATIVES.items()) + list(ADVERSARIAL.items()):
        vals = [fn("az", rng) for _ in range(500)]
        for label in ("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"):
            bad = [v for v in vals if value_valid(label, v)[0]]
            check(not bad, f"{fam}: {len(bad)} hard negatives are valid {label}, e.g. {bad[:3]}")
    ids = [d.value for k in ("id_card_too_short", "id_card_hyphen", "id_card_too_long") for d in SAMPLES[k]]
    other = sum(v[:2] not in ("AA", "AB") for v in ids)
    check(other >= 0.45 * len(ids), "ID-card look-alikes take varied prefixes like real ID cards")
    key = public_key_ed25519(random.Random(1)).split("\n")
    check(key[0] == "-----BEGIN PUBLIC KEY-----" and key[1].startswith("MCowBQYDK2VwAyEA")
          and len(key[1]) == 60, "the Ed25519 public-key look-alike")


TESTS = [
    ("D-51h new kinds, D-51d checksum-only kinds gone", test_d51h_kinds),
    ("catalogue shape", test_catalogue),
    ("ordinary decoys are invalid (R4)", test_ordinary_invalid),
    ("policy decoys are valid and allowlisted", test_policy_valid),
    ("contextual decoys: anchors never license the label", test_contextual),
    ("anchor_required decoys sit next to a licensing anchor", test_anchor_licenses),
    ("phrases are anchor + value", test_phrases),
    ("no benchmark values except the D-2 allowlist", test_no_benchmark_values),
    ("value variety", test_distinct),
    ("llm/specs.py samples every kind", test_specs_sampling),
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
