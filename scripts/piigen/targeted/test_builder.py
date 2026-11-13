"""P2-4 acceptance check: the targeted corpus builder.

No network, no model. Builds real documents and checks them against the gates
they will meet downstream, then runs the task's own commands on a build:

    python scripts/piigen/targeted/test_builder.py
"""

from __future__ import annotations

import collections
import json
import logging
import random
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1]
sys.path.insert(0, str(SCRIPTS))
logging.disable(logging.WARNING)            # value-pool exhaustion notes at volume

from piigen.anchors import ANCHOR_REQUIRED, structural_kind           # noqa: E402
from piigen.blocklist import is_blocked                               # noqa: E402
from piigen.config import ENTITY_TYPES                                # noqa: E402
from piigen.llm.quality import find_leaked_pii                        # noqa: E402
from piigen.llm.quality_filter import screen_record                   # noqa: E402
from piigen.negatives import ALL_DECOY_KINDS                          # noqa: E402
from piigen.resolver import complete_occurrences, resolve_claims      # noqa: E402
from piigen.targeted import builder as B                              # noqa: E402
from piigen.targeted import formats as FMT                            # noqa: E402
from piigen.targeted import frames_az_stub as STUB                    # noqa: E402
from piigen.targeted import quotas as Q                               # noqa: E402
from piigen.targeted.stats import compute_stats                       # noqa: E402
from piigen.validate import validate_example, value_valid             # noqa: E402
from piigen.values import ValueFactory, ValuePool                     # noqa: E402

PASS = 0
FAIL = 0
FAILURES: list[str] = []
REPORT: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:400] if detail is not None else ""))


N = 1500
BUILDER = B.TargetedBuilder(seed=11, n_docs=N)
RECORDS = BUILDER.build()


# --------------------------------------------------------------------------- #
def test_stub_shape() -> None:
    for name in ("ANCHORS", "FRAMES", "GENERIC_FRAMES", "NEUTRAL", "FRAME_VERSION"):
        check(hasattr(STUB, name), f"stub exports the C1 name {name}")
    frames = [(f"F.{l}.{i}", t, l) for l, ts in STUB.FRAMES.items() for i, t in enumerate(ts)]
    frames += [(f"G.{i}", t, None) for i, t in enumerate(STUB.GENERIC_FRAMES)]
    for fid, text, label in frames:
        try:
            B.parse_frame(fid, text)
        except ValueError as exc:
            check(False, str(exc))
        # no digits outside names such as "IPv6" and "CVV2": a digit in a
        # frame would be an unlabeled number in every document it writes
        check(not re.search(r"\d", re.sub(r"IPv6|CVV2", "", text)),
              f"{fid}: frames carry no digits", text)
        if "{a}" in text and label:
            check(bool(STUB.ANCHORS.get(label)), f"{fid}: {{a}} needs ANCHORS[{label}]")
    for label, pattern in ANCHOR_REQUIRED.items():
        bad = [a for a in STUB.ANCHORS[label] if not pattern.search(a)]
        check(not bad, f"every {label} anchor form licenses the label", bad)
    check(len(STUB.NEUTRAL) >= 100, "NEUTRAL has 100+ sentences", len(STUB.NEUTRAL))
    check(not any(re.search(r"\d", s) for s in STUB.NEUTRAL), "NEUTRAL is digit-free")
    check(len(set(STUB.NEUTRAL)) == len(STUB.NEUTRAL), "NEUTRAL has no duplicates")


def test_frames_pickup() -> None:
    """The builder takes the frames_az.py automatically once it exists,
    and fails loudly (never falls back) if that file is broken."""
    fake = types.SimpleNamespace(__name__="piigen.targeted.frames_az",
                                 ANCHORS=STUB.ANCHORS, FRAMES=STUB.FRAMES,
                                 GENERIC_FRAMES=STUB.GENERIC_FRAMES, NEUTRAL=STUB.NEUTRAL,
                                 FRAME_VERSION="real-1")
    saved = (B.importlib.util.find_spec, B.importlib.import_module)
    try:
        B.importlib.util.find_spec = lambda name: object()
        B.importlib.import_module = lambda name: fake if name.endswith("frames_az") else None
        module = B.load_frames_module()
        check(module is fake, "frames_az.py is used when it exists")
        check(B.FrameLibrary(module).source == "frames_az", "library reports the real file")
        broken = types.SimpleNamespace(__name__="piigen.targeted.frames_az", ANCHORS={})
        B.importlib.import_module = lambda name: broken
        try:
            B.load_frames_module()
            check(False, "a frames_az.py missing C1 names must raise")
        except ImportError:
            check(True, "")
    finally:
        B.importlib.util.find_spec, B.importlib.import_module = saved
    # frames_az.py now exists (P4-1): hide it to check the fallback
    B.importlib.util.find_spec = lambda name: None
    try:
        check(B.load_frames_module() is STUB, "without frames_az.py the stub is used")
    finally:
        B.importlib.util.find_spec = saved[0]
    check(B.load_frames_module().__name__.endswith(".frames_az"), "frames_az.py is the default now")


def test_records_pass_every_gate() -> None:
    ids, texts = set(), set()
    problems = collections.Counter()
    for r in RECORDS:
        t = r["text"]
        for key in ("id", "text", "lang", "entities", "_decoys", "_source", "_gen_version",
                    "_frame_ids", "_doc_type", "_pii_free", "_bucket", "_spec"):
            if key not in r:
                problems[f"missing field {key}"] += 1
        if r["lang"] != "az" or r["_source"] != "targeted" or not r["_frame_ids"]:
            problems["lang/_source/_frame_ids"] += 1
        if r["id"] in ids or t in texts:
            problems["duplicate id or text"] += 1
        ids.add(r["id"])
        texts.add(t)
        if r["_pii_free"] != (not r["entities"]):
            problems["_pii_free disagrees with entities"] += 1
        if any(t[e["start"]:e["end"]] != e["text"] for e in r["entities"]):
            problems["offset mismatch"] += 1
        spans = sorted([(e["start"], e["end"]) for e in r["entities"]]
                       + [(d["start"], d["end"]) for d in r["_decoys"]])
        if any(b[0] < a[1] for a, b in zip(spans, spans[1:])):
            problems["overlapping entity/decoy spans"] += 1
        if validate_example(r):
            problems["validate_example: " + validate_example(r)[0][:50]] += 1
        if screen_record(r):
            problems["screen_record: " + screen_record(r)[0][:50]] += 1
        if find_leaked_pii(t, r["entities"], decoy_spans=r["_decoys"]):
            problems["leak gate"] += 1
        if any(structural_kind(t, e["start"], e["end"]) for e in r["entities"]):
            problems["structural span"] += 1
        blocked = [(d["start"], d["end"]) for d in r["_decoys"]]
        again, _ = resolve_claims(t, [{"label": l, "text": v} for l, v in
                                      {(e["label"], e["text"]) for e in r["entities"]}],
                                  blocked=blocked)
        again, _ = complete_occurrences(t, again, blocked=blocked)
        if {(e["start"], e["end"], e["label"]) for e in again} != \
                {(e["start"], e["end"], e["label"]) for e in r["entities"]}:
            problems["resolver disagrees"] += 1
        for d in r["_decoys"]:
            kind = ALL_DECOY_KINDS[d["kind"]]
            valid = value_valid(kind.resembles, t[d["start"]:d["end"]])[0]
            if kind.policy and not valid:
                problems[f"policy decoy not valid: {d['kind']}"] += 1
            if (not kind.policy and not kind.contextual
                    and kind.resembles not in B.NAME_LABELS and valid):
                problems[f"decoy valid (R4): {d['kind']}"] += 1
        for e in r["entities"]:
            if e["label"] in ("GIVENNAME", "SURNAME", "CITY", "STREET"):
                continue
            if not value_valid(e["label"], e["text"])[0]:
                problems[f"entity invalid: {e['label']}"] += 1
    check(not problems, f"all {len(RECORDS)} records pass every gate", dict(problems))


# The --stats targets are shares with a tolerance, meant for a full build.
# In this 1,500-document build some rest on a few hundred draws (names in
# another spelling: ~500 names; noisy suffixes: ~10 of ~330 suffixed), so a
# change that only moves the random stream can push one out of tolerance
# (D-30b fix round: name variants 6.6% at seed 11, 7.7-10.6% at seeds 12-18;
# noisy suffixes 2.7%; the full 25,000-document build passes both, 9.7% and
# 3.9%). As with the PEM delimiters below, judge them on more draws rather
# than on one stream: three builds pooled.
def test_stats() -> None:
    st = compute_stats(RECORDS, BUILDER)
    pooled = RECORDS + [r for s in (12, 13) for r in B.TargetedBuilder(seed=s, n_docs=N).build()]
    for name, c in compute_stats(pooled, BUILDER)["checks"].items():
        if name.startswith("noisy suffixes"):
            # ~1,100 suffixed mentions in these builds: the noisy share reads
            # 1.3-5.0% per 1,500-document build (3.5% over six seeds) against
            # 4.5% in the 37k build, whose --stats judges the 5% +- 2 band.
            # Here: written, labelled whole, and not above the band.
            share = float(c["value"].split("%")[0]) / 100
            t = Q.load()["targets"]
            check(0 < share <= t["suffix_noisy"] + t["suffix_noisy_tolerance"],
                  f"--stats (3 builds pooled): {name} (present, not above the band)", c["value"])
            continue
        check(c["ok"], f"--stats (3 builds pooled): {name}", c["value"])
    REPORT.append(f"{N} docs: " + ", ".join(f"{k} {v:.1%}" for k, v in st["families"].items()))
    REPORT.append("rejected while building: " + str(sum(st["rejections"].values())))
    fams = collections.Counter(r["_doc_type"].split("_")[0] for r in RECORDS)
    check(set(fams) >= {"decoy", "contrast", "prose", "structured", "pii"},
          "every family is present", dict(fams))


def test_contrasts() -> None:
    tk = [r for r in RECORDS if r["_spec"].get("sub") == "token_key"]
    same = [r for r in tk if r["_spec"].get("same_body")]
    ok = True
    for r in same:
        tok = next(e["text"] for e in r["entities"] if e["label"] == "ACCESS_TOKEN")
        key = next(e["text"] for e in r["entities"] if e["label"] == "API_KEY")
        ok &= tok.split("_", 1)[-1].split("-", 1)[-1] == key.split("_", 1)[-1]
    check(bool(same) and ok, "same-body token/key pairs share the body exactly", len(same))
    # D-51h: the shared prefix is any ID-card prefix, not only AA/AB
    lic = [r for r in RECORDS if r["_spec"].get("sub") == "licence_id"]
    # the pair sentence: the document's first licence and ID card (v4.1's extra
    # lines after it carry their own same-prefix pairs)
    pair = lambda r: sorted((e for e in r["entities"] if e["label"] in  # noqa: E731
                             ("AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER")), key=lambda e: e["start"])[:2]
    ok = all(len({e["text"].upper()[:2] for e in pair(r)}) == 1 and
             sorted(len(e["text"]) for e in pair(r)) == [8, 9] for r in lic)
    check(bool(lic) and ok, "licence and ID card share one prefix, 8 vs 9 characters", len(lic))
    ipm = [r for r in RECORDS if r["_spec"].get("sub") == "ipv6_mac"]
    check(bool(ipm) and all({e["label"] for e in r["entities"]} ==
                            {"IPV6_ADDRESS", "MAC_ADDRESS"} for r in ipm),
          "IPv6 and MAC side by side", len(ipm))


def test_pairs() -> None:
    pairs = [r for r in RECORDS if r["_spec"]["family"] == "decoy_pair"]
    ok = collections.Counter()
    for r in pairs:
        labels = {e["label"] for e in r["entities"]}
        kinds = {d["kind"] for d in r["_decoys"]}
        group = r["_spec"]["group"]
        if group == "age":
            # D-57 S1: a real age and an age-shaped look-alike, often a second real age
            ok["one labeled value + one decoy"] += (labels == {"AGE"} and len(r["entities"]) in (1, 2)
                                                    and kinds == {"age_shaped_number"} and len(r["_decoys"]) == 1)
            continue
        # D-56g: an IPv4 pair adds a second real IPv4 in a sentence of its own;
        # D-57 S4: a building number after a street name comes with the street
        street = r["_spec"].get("building_style") == "street"
        reals = 2 if labels == {"IPV4_ADDRESS"} or street else 1
        ok["one labeled value + one decoy"] += len(r["entities"]) == reals and len(kinds) == 1
        if group == "building":
            ok["bina beside otaq/mərtəbə/kabinet"] += labels == ({"BUILDINGNUM", "STREET"} if street
                                                                 else {"BUILDINGNUM"})
    check(ok["one labeled value + one decoy"] == len(pairs),
          "every decoy pair has one labeled value and one decoy", dict(ok))
    other = [r for r in pairs if r["_spec"]["group"] == "other"]
    same_frame = sum(1 for r in other if collections.Counter(
        f for f in r["_frame_ids"] if f.startswith("G."))
        and len([f for f in r["_frame_ids"] if f.startswith("G.")]) == 1)
    check(same_frame == len(other), "an 'other' pair uses one generic frame for both halves",
          (same_frame, len(other)))


def test_determinism() -> None:
    a = B.TargetedBuilder(seed=5, n_docs=200).build()
    b = B.TargetedBuilder(seed=5, n_docs=200).build()
    c = B.TargetedBuilder(seed=6, n_docs=200).build()
    check(a == b, "same seed, same corpus")
    check(a != c, "different seed, different corpus")


def test_frame_cap() -> None:
    tiny = types.SimpleNamespace(
        __name__="piigen.targeted.frames_az_stub", ANCHORS=STUB.ANCHORS, FRAMES={},
        GENERIC_FRAMES=["Qeyddə {a} {v} göstərilib."], NEUTRAL=STUB.NEUTRAL[:3],
        FRAME_VERSION="tiny")
    try:
        B.TargetedBuilder(seed=1, n_docs=400, frames_module=tiny).build()
        check(False, "a frame pool that cannot meet the 3% rule must fail the build")
    except B.BuildError:
        check(True, "")


def test_quotas() -> None:
    q = Q.load()
    check(abs(sum(Q.families(q).values()) - 1) < 1e-9, "default family shares sum to 1")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump({"structured": {"decoy_cell_rate": 0.5}}, fh)
    merged = Q.load(fh.name)
    check(merged["structured"]["decoy_cell_rate"] == 0.5
          and merged["structured"]["formats"] == q["structured"]["formats"],
          "an override file is merged over the defaults")
    bad = json.loads(Q.DEFAULT_PATH.read_text(encoding="utf-8"))
    bad["families"]["prose"] = 0.9
    try:
        Q.check(bad)
        check(False, "family shares that do not sum to 1 are rejected")
    except ValueError:
        check(True, "")
    Path(fh.name).unlink()


def test_values_and_emails() -> None:
    f = ValueFactory(random.Random(3), ValuePool(state_path=None))
    emails = [f.email_reserved("az") for _ in range(500)]
    check(all(value_valid("EMAIL", e)[0] and not is_blocked(e) for e in emails),
          "reserved-TLD emails are valid and not blocked")
    check({e.rsplit(".", 1)[1] for e in emails} == set(f.RESERVED_TLDS),
          "every reserved TLD appears")
    for placeholder in ("user@mail.invalid", "test@x.test", "john.doe@example.com",
                        "x@sample.test", "a@example.test"):
        check(bool(is_blocked(placeholder)), f"placeholder stays blocked: {placeholder}")
    cards = [f.payment_card_grouped() for _ in range(200)]
    check(all(re.fullmatch(r"\d{4} \d{4} \d{4} \d{4}", c) and value_valid(
        "PAYMENT_CARD_NUMBER", c)[0] for c in cards), "grouped cards: #### #### #### ####")
    ibans = [f.iban_az_compact() for _ in range(200)]
    check(all(len(i) == 28 and i.startswith("AZ") and value_valid("IBAN", i)[0] for i in ibans),
          "AZ IBANs: 28 characters")
    styles = {s: f.date_styled("az", s) for s in f.DATE_STYLES}
    check(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", styles["dmy"]) and
          re.fullmatch(r"\d{4}-\d{2}-\d{2}", styles["iso"]) and
          re.fullmatch(r"\d{1,2} [a-zəıöüşçğ]+ \d{4}", styles["spelled"]),
          "DATE styles dd.mm.yyyy, ISO, spelled-out", styles)


def test_formats() -> None:
    fmts = collections.Counter(r["_spec"]["format"] for r in RECORDS
                               if r["_spec"]["family"] == "structured")
    # D-57 S2: `caps_form`, an ALL-CAPS form the builder writes itself
    check(set(fmts) == set(FMT.FORMATS) | {"caps_form"}, "every structured format is built", dict(fmts))
    # D-51h item 8: the `cvv` CSV tables are the one exception, a CVV only
    # where its `cvv` header still licenses it (within 80 characters)
    keyed_in_tables = [r["id"] for r in RECORDS
                       if r["_spec"].get("format") in FMT.TABLE_FORMATS + ("dialogue",)
                       and not r["_spec"].get("cvv_rows")
                       and {e["label"] for e in r["entities"]} & FMT.KEYED_ONLY]
    check(not keyed_in_tables, "AGE/CVV/BUILDINGNUM only in keyed formats (and the cvv CSV tables)",
          keyed_in_tables[:3])
    cells = sum(1 for r in RECORDS if r["_spec"]["family"] == "structured" and r["_decoys"])
    check(cells > 0, "decoys also appear in cells", cells)


def test_task_commands() -> None:
    """The task's check, on a real build: validate_corpus.py exits 0 and
    prepare_splits.py --no-tokenize rejects nothing."""
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "t.jsonl"
        corpus.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in RECORDS),
                          encoding="utf-8")
        gate = subprocess.run([sys.executable, str(SCRIPTS / "validate_corpus.py"), str(corpus)],
                              capture_output=True, text=True, encoding="utf-8")
        check(gate.returncode == 0, "validate_corpus.py exits 0",
              [ln for ln in gate.stdout.splitlines() if "FAIL" in ln][:5])
        split = subprocess.run([sys.executable, str(SCRIPTS / "prepare_splits.py"), str(corpus),
                                "--output-dir", str(Path(tmp) / "split" / "s"), "--no-tokenize"],
                               capture_output=True, text=True, encoding="utf-8")
        check(split.returncode == 0 and "failed re-validation" not in split.stdout,
              "prepare_splits.py rejects nothing", split.stdout[-500:])
        cli = subprocess.run([sys.executable, str(SCRIPTS / "build_targeted_corpus.py"), "-n", "300",
                              "--seed", "3", "-o", str(Path(tmp) / "cli.jsonl"), "--stats"],
                             capture_output=True, text=True, encoding="utf-8")
        check(cli.returncode == 0 and "P2-4 checks:" in cli.stdout,
              "the CLI builds and prints --stats", cli.stderr[-300:])
        REPORT.append("validate_corpus: " + next((ln for ln in gate.stdout.splitlines()
                                                  if ln.startswith("RESULT")), "?"))


# --------------------------------------------------------------------------- #
# P2-4b extras
# --------------------------------------------------------------------------- #
_AZ_LETTERS = set("əƏıİşŞçÇğĞöÖüÜ")


def test_case_noise_unit() -> None:
    from piigen.noise import CASE_NOISE_KINDS, apply_entity_casing, case_noised
    rng = random.Random(2)
    for value in ("İsmayıllı", "Xınalıq", "Qəbələ", "Nizami küçəsi", "Маммадов", "IŞIQ"):
        for kind in CASE_NOISE_KINDS:
            out = case_noised(value, kind, rng)
            check(len(out) == len(value), f"{kind}({value}) keeps the length", out)
            if kind.endswith("fold"):
                check(not _AZ_LETTERS & set(out), f"{kind}({value}) has no Azerbaijani letters", out)
            if kind.startswith("lower"):
                check(out == out.lower() or not any(c.isupper() for c in out),
                      f"{kind}({value}) is lower-case", out)
    check(case_noised("İsmayıllı", "lower", rng) == "ismayıllı", "İ -> i and ı stays ı (Azerbaijani lower)")
    check(case_noised("IŞIQ", "lower", rng) == "ışıq", "I -> ı (Azerbaijani lower)")
    m = case_noised("Novxanı", "mixed", rng)
    check(any(c.isupper() for c in m[1:]) and any(c.islower() for c in m[1:]),
          "mixed case has both cases after the first letter", m)
    text = "Ünvan: İsmayıllı, Nizami küçəsi. Əlaqə: Leyla."
    ents = [{"start": 7, "end": 16, "label": "CITY", "text": "İsmayıllı"},
            {"start": 18, "end": 31, "label": "STREET", "text": "Nizami küçəsi"},
            {"start": 40, "end": 45, "label": "GIVENNAME", "text": "Leyla"}]
    new, out, applied = apply_entity_casing(text, ents, {0: "lower_fold", 2: "fold"}, rng)
    check(new[:7] == text[:7] and new[16:] == text[16:], "only the chosen entity's characters change", new)
    check(out[0]["text"] == "ismayilli" and all(new[e["start"]:e["end"]] == e["text"] for e in out),
          "offsets and entity text are exact after noise", out)
    check(applied == {0: "lower_fold"}, "a kind that changes nothing (folding Leyla) is not counted", applied)


def test_extras_in_build() -> None:
    st = compute_stats(RECORDS, BUILDER)
    n_ents = sum(len(r["entities"]) for r in RECORDS)
    noised = [(r, x) for r in RECORDS for x in r["_spec"].get("case_noise", ())]
    check(0 < len(noised) <= 0.08 * n_ents, f"casing noise on {len(noised)}/{n_ents} entities (<= 8%)")
    # "CITY especially" (P2-4b) is a rate: of each label's mentions, cities are
    # the most likely to be noised (counts depend on the label mix, which
    # P2-4c's family plurals shifted towards surnames)
    mentions = collections.Counter(e["label"] for r in RECORDS for e in r["entities"])
    rate = {lab: n / mentions[lab] for lab, n in st["case_noise"]["by_label"].items()}
    check(rate.get("CITY", 0) == max(rate.values()), "CITY is the most likely to be noised",
          {k: f"{v:.1%}" for k, v in rate.items()})
    for r, (label, text, kind) in noised:
        e = [e for e in r["entities"] if e["label"] == label and e["text"] == text]
        check(bool(e), "the noised value is the labelled span", (label, text))
        if kind.endswith("fold"):
            check(not _AZ_LETTERS & set(text), f"{kind}: no Azerbaijani letters left", text)
    variants = [x for r in RECORDS for x in r["_spec"].get("name_variants", ())]

    def bases(r: dict) -> list[tuple[str, str]]:
        stem = {(x["start"], x["end"]): x["stem_end"] for x in r.get("_suffixes", ())}
        return [(e["label"], r["text"][e["start"]:stem.get((e["start"], e["end"]), e["end"])])
                for e in r["entities"]]
    check(all((lab, v) in bases(r) for r in RECORDS for lab, v, _k in r["_spec"].get("name_variants", ())),
          "every recorded variant is an entity, or the stem of an inflected one")
    inflected = sum(1 for r in RECORDS for lab, v, _k in r["_spec"].get("name_variants", ())
                    if (lab, v) not in {(e["label"], e["text"]) for e in r["entities"]})
    check(inflected > 0, "inflected names take spelling variants too (`Mammadovun`)")
    names = sum(1 for r in RECORDS for e in r["entities"] if e["label"] in ("GIVENNAME", "SURNAME"))         - sum(r["_spec"].get("listed_names", 0) for r in RECORDS)   # checked in test_short_homograph
    reported = compute_stats(RECORDS, BUILDER)["checks"]["names in another spelling/script ~10%, all valid"]
    check(reported["value"].startswith(f"{len(variants) / names:.1%} of {names}"),
          "--stats reports the name-variant share itself", (reported["value"], len(variants), names))
    check({k for *_x, k in variants} == {"english", "cyrillic"}, "both English and Cyrillic spellings occur",
          collections.Counter(k for *_x, k in variants))
    pem = [r for r in RECORDS if r["_spec"].get("pem")]
    keys = [e["text"] for r in pem for e in r["entities"] if e["label"] == "PRIVATE_KEY"]
    check(any("\n" in k for k in keys) and any("BEGIN" in k and "\n" not in k for k in keys),
          "PEM keys on several lines and pasted onto one line")
    after = collections.Counter()
    for r in pem:
        for e in r["entities"]:
            if e["label"] == "PRIVATE_KEY" and "BEGIN" in e["text"]:
                after[r["text"][e["end"]:e["end"] + 1]] += 1
    # What follows a key is drawn per key, and the build above has only about
    # a dozen, so whether all four show up depends on the random stream (a
    # copy of the tree without the benchmark file drew no quote). 200 more
    # keys, drawn directly, make the four a certainty.
    sampler = B.TargetedBuilder(seed=5, n_docs=1)
    for _ in range(200):
        d = B.Draft()
        sampler._pem_sentence(d, set(), {})
        e = next(x for x in d.entities if x["label"] == "PRIVATE_KEY")
        after[d.text[e["end"]:e["end"] + 1]] += 1
    check({"\n", ";", " ", '"'} <= set(after), "a key is followed by a newline, ;, a space and a quote",
          dict(after))
    wrapped = [r for r in RECORDS if r["_spec"].get("touch")]
    check(all(any(r["text"][e["start"] - 1:e["start"]] in "([«\"" for e in r["entities"]) for r in wrapped),
          "every wrapped value sits right after its opening bracket or quote")
    REPORT.append(f"P2-4b: casing noise {len(noised) / n_ents:.2%}, name variants {len(variants)}, "
                  f"PEM documents {len(pem)}, wrapped values {sum(len(r['_spec']['touch']) for r in wrapped)}")


def test_quota_cap() -> None:
    q = Q.load()
    q["noise"]["case_target_share"] = 0.08
    try:
        Q.check(q)
        check(False, "a casing-noise target at the 8% cap is refused")
    except ValueError:
        check(True, "a casing-noise target at the 8% cap is refused")


def test_fix_round() -> None:
    """D-30b, D-33: dashed CVVs are real (10% of the builder's CVVs), slashed
    ones are not; FINs keep their natural share of all-letter values; no
    look-alike FIN with I or O; ZIPs reach past the 253 real postal codes."""
    from piigen import checksums as CK
    from piigen.locales import az as AZ
    good, bad = ["123", "1234", "12-3", "1-23", "12-34"], ["12/3", "1/23", "12.3", "123-4", "1-2", "12345"]
    check(all(CK.card_security_code_valid(v) for v in good), "dashed CVVs are valid", good)
    check(not any(CK.card_security_code_valid(v) for v in bad), "slashed, dotted, too long or short are not", bad)
    check("fin_with_i_or_o" not in ALL_DECOY_KINDS, "the fin_with_i_or_o look-alike is gone (D-33c)")
    # The shares are drawn per value, and the build above holds only a few
    # dozen CVVs and FINs: draw 2,000 of each from the builder directly.
    sampler = B.TargetedBuilder(seed=5, n_docs=1)
    cvv_draws = [sampler._mint("CARD_SECURITY_CODE", "prose") for _ in range(2000)]
    share = sum("-" in v for v in cvv_draws) / len(cvv_draws)
    check(0.07 <= share <= 0.13, "~10% of the builder's CVVs are dashed (D-33d)", f"{share:.1%}")
    fin_draws = [sampler._mint("AZ_FIN", "prose") for _ in range(2000)]
    share = sum(not re.search(r"\d", v) for v in fin_draws) / len(fin_draws)
    check(0.05 <= share <= 0.13, "all-letter FINs keep their natural ~8.7% share (D-33b)", f"{share:.1%}")
    f = ValueFactory(random.Random(7), ValuePool(state_path=None))
    cvvs = [f.card_security_code_dashed() for _ in range(300)]
    check(all(CK.card_security_code_valid(v) and "-" in v for v in cvvs), "dashed CVVs are valid", cvvs[:3])
    zips = [f.zipcode_any_az() for _ in range(300)]
    check(all(value_valid("ZIPCODE", z)[0] for z in zips), "AZ + four digits is a valid ZIP", zips[:3])
    check(sum(z not in set(AZ._ZIPCODES) for z in zips) > 250, "most drawn ZIPs are outside the real list")
    ents = [(e["label"], e["text"]) for r in RECORDS for e in r["entities"]]
    zipc = [v for lab, v in ents if lab == "ZIPCODE"]
    check(zipc and sum(z not in set(AZ._ZIPCODES) for z in zipc) / len(zipc) >= 0.30,
          "a third or more of the build's ZIPs are outside the real list")
    dashed_decoys = [r["text"][d["start"]:d["end"]] for r in RECORDS for d in r["_decoys"]
                     if d["kind"] == "cvv_separator" and "-" in r["text"][d["start"]:d["end"]]]
    check(not dashed_decoys, "no dashed CVV is planted as a look-alike", dashed_decoys[:3])


def test_part2_group1() -> None:
    """D-34 part 2, group 1: fin_6_chars gone; a given name + shop word is a
    policy look-alike; generic document nouns before both licence and ID;
    look-alikes before their noun and in `Label: value` forms."""
    from piigen.targeted import frames_az as F
    check("fin_6_chars" not in ALL_DECOY_KINDS, "the fin_6_chars look-alike is gone (D-34b)")
    k = ALL_DECOY_KINDS.get("policy_givenname_in_company")
    check(k is not None and k.policy and k.resembles == "GIVENNAME",
          "a given name + shop word is a GIVENNAME policy look-alike (D-33f names_as_org)")
    for lab in ("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"):
        check({"sənəd", "sənədin nömrəsi", "vəsiqə nömrəsi"} <= set(F.ANCHORS[lab]),
              f"{lab}: generic document nouns among its anchors (D-34d)")
    noun = [r for r in RECORDS if r["_spec"].get("group") == "noun"]
    labs = collections.Counter(ALL_DECOY_KINDS[r["_spec"]["kind"]].resembles for r in noun)
    check(noun and set(labs) == set(B.NOUN_FRAMES), "before-noun pairs cover DATE, AGE, ZIP and card",
          dict(labs))
    ok = all(any(r["text"][d["end"]:d["end"] + 12].lstrip().lower().startswith(("tarix", "yaş", "indeks", "kart", "nömrəli",
                                                                                 "fi̇n", "fin"))
                 for d in r["_decoys"]) for r in noun)
    check(ok, "every before-noun look-alike sits right before its noun")
    forms = [r for r in RECORDS if r["_spec"]["family"] == "form"]
    check(forms and all(r["entities"] and r["_decoys"] for r in forms),
          "every form mixes real values and look-alikes", len(forms))
    lines_ok = all(re.search(r"(?m)^[^\n:]{2,40}: $", r["text"][:d["start"]].rsplit("\n", 1)[-1] + "\n")
                   or r["text"][:d["start"]].rsplit("\n", 1)[-1].endswith(": ")
                   for r in forms for d in r["_decoys"])
    check(lines_ok, "every form look-alike sits right after `Label: `")


def test_part2_group2() -> None:
    """D-34 part 2, group 2: IBANs with letters in the account part, long
    clerical chains, village names with controls, headerless contact rows,
    keys in log lines and public-key look-alikes, foreign brands, token
    look-alikes."""
    from piigen.checksums import iban_valid
    from piigen.locales.az import SETTLEMENT_KINDS, SETTLEMENTS
    from piigen.negatives import make_decoy
    vf = ValueFactory(random.Random(5), ValuePool(state_path=None))
    ibans = [vf.iban_az_alnum(grouped=i % 2 == 1) for i in range(300)]
    check(all(iban_valid(x) and len(x.replace(" ", "")) == 28 and x[:2] == "AZ"
              and any(c.isalpha() for c in x.replace(" ", "")[8:]) for x in ibans),
          "AZ IBANs with letters in the 20-character account part are valid (D-34e)")
    rng = random.Random(9)
    for kind, label in (("email_double_at", "EMAIL"), ("email_localhost", "EMAIL"),
                        ("email_no_at", "EMAIL"), ("public_key_block", "PRIVATE_KEY"),
                        ("image_digest", "ACCESS_TOKEN"), ("token_prefix_only", "ACCESS_TOKEN")):
        k = ALL_DECOY_KINDS.get(kind)
        check(k is not None and k.resembles == label
              and not any(value_valid(label, make_decoy(k, rng))[0] for _ in range(200)),
              f"{kind}: a look-alike of {label}, never valid as one")
    cl = [r for r in RECORDS if r["_spec"]["family"] == "clerical"]
    one = all((len(r["entities"]) == 1) != r["_spec"]["clerical"]["look_alike"] for r in cl)
    fake_ok = all(any(d["resembles"] == r["_spec"]["clerical"]["label"] for d in r["_decoys"])
                  for r in cl if r["_spec"]["clerical"]["look_alike"])
    check(cl and one and fake_ok, "a clerical chain holds one value or one look-alike", len(cl))
    in_band = sum(330 <= len(r["text"]) <= 660 and r["text"].count("; ") >= 5 for r in cl)
    check(in_band >= 0.95 * len(cl), "clerical chains: 330-660 characters, 6+ clauses", f"{in_band}/{len(cl)}")
    vil = [r for r in RECORDS if r["_spec"]["family"] == "village"]
    kind_of = dict(zip(SETTLEMENTS, SETTLEMENT_KINDS))
    ctrl = all(any(d["kind"] in ("village_descriptor", "kinship_possessive") for d in r["_decoys"])
               and any(e["label"] == "CITY" for e in r["entities"]) for r in vil)
    kend = sum(any(e["label"] == "CITY" and r["text"][e["end"]:].startswith(" kənd") for e in r["entities"])
               for r in vil)
    check(vil and ctrl and kend, "village documents: a village CITY and a control word in each, some before kənd",
          f"{len(vil)} documents, {kend} with `<name> kənd...`")
    plain = [e["text"] for r in vil for e in r["entities"] if e["label"] == "CITY"
             and not any(x["start"] == e["start"] for x in r["_suffixes"]) and e["text"] in kind_of]
    check(all(kind_of[v] == "settlement" for v in plain), "village documents name villages, not cities")
    # two builds pooled: one build of 1,500 has ~16 public keys at a 0.4
    # log-line rate, and seed 11 drew 0 log lines in v4.2 (about 1 in 3,000)
    pub = [(r, d) for r in RECORDS + B.TargetedBuilder(seed=12, n_docs=N).build()
           for d in r["_decoys"] if d["kind"] == "public_key_block"]
    check(pub and any(r["text"][d["start"] - 1] == "=" for r, d in pub)
          and any("\n" in r["text"][d["start"]:d["end"]] for r, d in pub),
          "public-key look-alikes as blocks and in log lines (D-34f)", len(pub))
    # a log-line key is rare in a small build (~1 in 1,500 documents): drawn directly
    sampler = B.TargetedBuilder(seed=5, n_docs=1)
    logged = []
    for _ in range(300):
        dd, spec = B.Draft(), {}
        sampler._pem_sentence(dd, set(), spec)
        if spec["pem"][0]["layout"] == "logline":
            e = dd.entities[0]
            logged.append(dd.text[e["start"] - 1] == "=" and "\n" not in e["text"]
                          and re.match(r" \w+=", dd.text[e["end"]:]) is not None)
    check(logged and all(logged), "a flattened private key as one `key=value` field between others "
          "(D-33f pem b)", len(logged))
    contact = [r for r in RECORDS if "STATUS" in (r["_spec"].get("columns") or [])]
    rows_ok = all(sum(any(line.endswith(("," + w, ";" + w)) for w in FMT.STATUS_WORDS)
                      for line in r["text"].split("\n")) == FMT.rows_for("csv_noheader") for r in contact)
    check(contact and rows_ok and all({"EMAIL", "AZ_ID_CARD_NUMBER", "TELEPHONENUM"}
                                      <= {e["label"] for e in r["entities"]} | {d["resembles"] for d in r["_decoys"]}
                                      for r in contact),
          "headerless contact rows: email, ID card, phone and a status word", len(contact))
    from piigen.negatives import _foreign_brands
    brands = [d for r in RECORDS for d in r["_decoys"] if d["kind"] == "policy_foreign_brand"]
    check(brands and not any(e["text"] in _foreign_brands() for r in RECORDS for e in r["entities"]),
          "foreign brands are look-alikes, never labelled", len(brands))
    tla = [r for r in RECORDS if "token_look_alike" in r["_spec"]]
    check(tla, "image digests or truncated tokens beside token/key pairs", len(tla))


def test_part2_group3() -> None:
    """D-34 part 2, group 3: 13-digit invalid cards, chain IBANs with
    letters, values glued to punctuation, probe-shaped reserved emails,
    grouped phones after a key and phones in log lines."""
    from piigen.negatives import make_decoy
    rng = random.Random(4)
    # D-51d: `card_wrong_length` replaced the checksum-only `card_luhn_invalid`
    cards = [make_decoy(ALL_DECOY_KINDS["card_wrong_length"], rng) for _ in range(500)]
    thirteen = [c for c in cards if len(re.sub(r"\D", "", c)) == 13]
    check(thirteen and not any(value_valid("PAYMENT_CARD_NUMBER", c)[0] for c in cards),
          "card look-alikes include 13-digit ones, none valid", len(thirteen))
    # a family build of its own: the small RECORDS build holds ~5 chain IBANs,
    # too few for a 0.8 rate (2 of 5 happened after an unrelated RNG shift)
    chain = [e["text"].replace(" ", "") for r in _family_records("clerical", 300)
             for e in r["entities"] if e["label"] == "IBAN"]
    lettered = sum(any(ch.isalpha() for ch in x[8:]) for x in chain)
    check(chain and lettered >= 0.6 * len(chain), "most chain IBANs have letters in the account part",
          f"{lettered}/{len(chain)}")
    glued = [r for r in RECORDS if r["_spec"]["family"] == "punct"]
    spans = [(r["text"], s["start"], s["end"]) for r in glued for s in r["entities"] + r["_decoys"]]
    tight = all(t[s - 1] in ":([—" and t[e] in ";)]!" for t, s, e in spans)
    check(glued and tight, "punct documents: every value glued to a mark on both sides", len(spans))
    f = ValueFactory(random.Random(8), ValuePool(state_path=None))
    emails = [f.email_reserved("az") for _ in range(600)]
    check(any(re.fullmatch(r"[a-z]+\.[a-z]+\d\d", e.split("@")[0]) for e in emails)
          and any(re.match(r"[a-z]+-[a-z]+\d\.", e.split("@")[1]) for e in emails)
          and all(value_valid("EMAIL", e)[0] and not is_blocked(e) for e in emails),
          "reserved emails include name.surname42@word-word7.<tld>, all valid and unblocked")
    keyed = [e for r in RECORDS if r["_spec"].get("format") in B.KEYED_PHONE_FORMATS
             for e in r["entities"] if e["label"] == "TELEPHONENUM"]
    check(keyed and any(" " in e["text"] for e in keyed), "grouped phones after a key", len(keyed))
    # its own sample: the fixture holds ~26 log documents, too few for a 50%
    # rate to stay above 35% whenever the draws shift (v4.1 A5: 9/26)
    logs = [r for r in RECORDS + _family_records("structured", 1200, seed=31) if r["_spec"].get("format") == "log"]
    with_phone = sum("TELEPHONENUM" in r["_spec"]["columns"] for r in logs)
    check(logs and with_phone >= 0.35 * len(logs), "phones in log lines", f"{with_phone}/{len(logs)}")


def test_d42c() -> None:
    """D-42c (shadow shapes): the `+994 (55) 123-45-67` phone,
    bare 4-digit ZIPs with their context, values glued to punctuation and
    after a document noun, more broken look-alikes in PII-free documents."""
    from piigen.locales import az as AZ
    from piigen.llm.dspy_generate import build_fields
    from piigen.llm.specs import DocumentSpec, PlannedEntity
    rng = random.Random(6)
    phones = [AZ.phone(rng) for _ in range(4000)]
    bracket = [p for p in phones if re.fullmatch(r"\+994 \(\d\d\) \d{3}-\d\d-\d\d", p)]
    check(0.08 <= len(bracket) / len(phones) <= 0.16 and all(value_valid("TELEPHONENUM", p)[0] for p in bracket),
          "about 12% of az phones are `+994 (55) 123-45-67`, all valid", len(bracket))
    vf = ValueFactory(random.Random(7), ValuePool(state_path=None))
    zips = [vf.zipcode("az") for _ in range(4000)]
    bare = [z for z in zips if z.isdigit()]
    check(0.2 <= len(bare) / len(zips) <= 0.3 and all(len(z) == 4 and value_valid("ZIPCODE", z)[0] for z in bare),
          "about 25% of az ZIPs are bare 4 digits, all valid", len(bare))
    check(not any(1900 <= int(z) <= 2099 or int(z) % 100 == 0 for z in bare),
          "no bare ZIP is a year or a round hundred")
    spec = DocumentSpec(index=0, lang="az", doc_type="official_notice", doc_type_hint="x", register="x",
                        band="medium", min_chars=1, max_chars=2, length_hint="x",
                        entities=[PlannedEntity("ZIPCODE", bare[0])])
    check("poçt indeksi" in build_fields(spec)["entities_to_embed"], "the brief places a bare ZIP after its context")
    postal = [r for r in RECORDS if r["_spec"]["family"] == "postal"]
    check(postal and any(e["label"] == "ZIPCODE" and e["text"].isdigit() for r in postal for e in r["entities"]),
          "postal documents carry bare ZIPs", len(postal))
    # D-43c (finding 1): only a town is called `şəhər`
    # (noise may write a town in ASCII and any case: Şuşa -> susa)
    # ("İ".casefold() is "i̇", two characters: fold it to i first)
    fold = lambda s: s.replace("İ", "i").casefold().translate(str.maketrans("əışçğöü", "eiscgou"))
    towns = {fold(c) for c in AZ.CITIES}
    before_seher = [r["text"][e["start"]:e["end"]] for r in postal for e in r["entities"]
                    if e["label"] == "CITY" and r["text"][e["end"]:].startswith(" şəhər")]
    check(before_seher and all(fold(v) in towns for v in before_seher),
          "a city before `şəhər` in postal documents is a town from az_cities.txt",
          [v for v in before_seher if fold(v) not in towns][:3])
    check(not any("Kuryer ev" in t or "qeydiyyatdan keçərkən {v}" in t
                  for t in B.EDGE_SENTENCES["BUILDINGNUM"] + B.CONTEXT_SENTENCES["AZ_VOEN"]),
          "D-43c optional edits applied (findings 2, 4)")
    edges = [r for r in RECORDS if r["_spec"]["family"] == "edges"]
    labs = ("AZ_VOEN", "AZ_PASSPORT_NUMBER", "BUILDINGNUM")
    spans = [(r["text"], e) for r in edges for e in r["entities"] if e["label"] in labs]
    check(edges and spans and all(e["text"] == t[e["start"]:e["end"]] and not re.search(r"[.\-)(=,:]$|^[(=]", e["text"])
                                  for t, e in spans), "edge spans are the value only, no mark inside", len(spans))
    glued = sum(t[e["end"]:e["end"] + 1] in ".-)," or t[e["start"] - 1:e["start"]] in "(=" for t, e in spans)
    check(glued >= 0.3 * len(spans), "many edge values touch a mark", f"{glued}/{len(spans)}")
    B_ = B.suffix_after_number
    check([B_(v, "cop") for v in ("13", "19", "1234567891", "34567")] == ["-dür", "-dur", "-dir", "-dir"]
          and [B_(v, "loc") for v in ("12", "16", "45/9")] == ["-də", "-da", "-da"]
          and not B.takes_suffix("10") and not B.takes_suffix("12A") and B.takes_suffix("45/9"),
          "a suffix after a number follows the last digit's vowel; none after 0 or a letter")
    suffixed = [t[e["end"]:e["end"] + 5] for t, e in spans if t[e["end"]:e["end"] + 1] == "-"]
    check(all(not t[e["end"] - 1] in "0ABCDEFGHIJKLMNOPQRSTUVWXYZ" for t, e in spans
              if t[e["end"]:e["end"] + 2] in ("-d",)), "no suffix sentence after a value ending in 0 or a letter",
          suffixed[:3])
    from piigen.negatives import ALL_DECOY_KINDS, make_decoy
    for kind in ("email_dotless_domain", "api_key_short", "ipv6_non_hex", "ipv6_two_compressions", "jwt_two_segments"):
        k = ALL_DECOY_KINDS[kind]
        check(not any(value_valid(k.resembles, make_decoy(k, rng))[0] for _ in range(300)),
              f"{kind}: never a valid {k.resembles}")
    pf = [d["resembles"] for r in RECORDS if not r["entities"] and r["_spec"]["family"] == "pii_free"
          for d in r["_decoys"]]
    focus = collections.Counter(x for x in pf if x in B.PII_FREE_FOCUS)
    check(set(focus) == set(B.PII_FREE_FOCUS), "PII-free documents hold look-alikes of every focus label", dict(focus))


def test_cvv_pairs() -> None:
    """D-41a: `cvv` pairs -- a real CVV and a 5-digit or sequential look-alike
    in the same sentence; the dummies are never valid CVVs; R1 in the frames."""
    from piigen.targeted.test_frames import RECORDING_VERBS
    pairs = [r for r in RECORDS if r["_spec"].get("group") == "cvv"]
    ok = all(len([e for e in r["entities"] if e["label"] == "CARD_SECURITY_CODE"]) == 1
             and len([d for d in r["_decoys"] if d["kind"] in B.CVV_KINDS]) == 1 for r in pairs)
    check(pairs and ok, "each cvv pair: one real CVV, one 5-digit or sequential look-alike", len(pairs))
    kinds = collections.Counter(d["kind"] for r in pairs for d in r["_decoys"] if d["kind"] in B.CVV_KINDS)
    check(set(kinds) == set(B.CVV_KINDS), "both look-alike kinds in the pairs", dict(kinds))
    check(not any(value_valid("CARD_SECURITY_CODE", v)[0] for v in __import__("piigen.negatives",
                  fromlist=["_seq5_pool"])._seq5_pool()), "the sequential dummies are never valid CVVs")
    bare = [t for t in B.CVV_FRAMES if re.search(r"\{v\} (" + "|".join(RECORDING_VERBS) + r")\b", t)]
    check(not bare, "CVV frames: a recording verb after the value takes kimi/olaraq (R1)", bare)


def test_d39b_names() -> None:
    """D-39b: the name constructions the team listed. Patronymics: the father's
    name is a GIVENNAME and `oğlu`/`qızı` stay outside every span; every
    construction present; Latin spelling and proper case; the official register."""
    # D-57: namelist keeps its 30k count in a 37k build, so the 1,500-document
    # build holds ~35; dedicated documents keep every construction in reach
    nl = [r for r in RECORDS if r["_spec"]["family"] == "namelist"] + _family_records("namelist", 200)
    subs = collections.Counter(r["_spec"]["namelist"] for r in nl)
    check(set(subs) == set(Q.load()["namelist"]["subs"]), "every name construction is written", dict(subs))
    ents = lambda r, label: [e for e in r["entities"] if e["label"] == label]    # noqa: E731
    bad = []
    for r in nl:
        t = r["text"]
        for m in re.finditer(r"(?<!\w)(oğlu|qızı)(?!\w)", t):
            before = [e for e in r["entities"] if e["end"] + 1 == m.start() and t[e["end"]] == " "]
            inside = any(e["start"] < m.end() and m.start() < e["end"] for e in r["entities"])
            if inside or len(before) != 1 or before[0]["label"] != "GIVENNAME":
                bad.append((r["id"], t[max(0, m.start() - 30):m.end()]))
    patro = [r for r in nl if r["_spec"]["namelist"].startswith("patronymic")]
    check(patro and not bad, "a patronymic: the father's name is a GIVENNAME right before oğlu/qızı, "
          "the word outside every span", bad[:2])
    pairs = [(g, f) for r in patro for g in ents(r, "GIVENNAME") for f in ents(r, "GIVENNAME")
             if f["start"] > g["end"] and r["text"][g["end"]:f["start"]] == " "]
    check(len(pairs) >= len(patro), "the person's given name stands right before the father's name", len(pairs))
    check(all("case_noise" not in r["_spec"] and not re.search(r"[Ѐ-ӿ]", r["text"]) for r in nl),
          "name lists: proper case and Latin spelling only")
    check(all(r["_spec"]["register"] == "bureaucratic" for r in nl), "the official filler register")
    lists = [r for r in nl if r["_spec"]["namelist"] == "patronymic_list"]
    check(lists and all(2 <= r["_spec"]["people"] <= 5 and r["text"].count("\n") >= r["_spec"]["people"]
                        for r in lists), "a list holds 2-5 people, one per line", len(lists))
    roles = [r for r in nl if r["_spec"]["namelist"] == "role_word"]
    lower = re.compile(r"(?<!\w)(" + "|".join(B.ROLE_WORDS) + r") $")
    check(roles and all(any(lower.search(r["text"][:e["start"]]) for e in ents(r, "GIVENNAME")
                            + ents(r, "SURNAME")) for r in roles),
          "role-word documents: a name right after a lowercase role word", len(roles))
    sigs = [r for r in nl if r["_spec"]["namelist"] == "signature"
            and r["_spec"]["signature"] != "title_only"]      # D-51h: no name under the title
    check(sigs and all(any(ln.strip() == r["text"][e["start"]:e["end"]] or
                           ln.strip() == " ".join(r["text"][x["start"]:x["end"]] for x in r["entities"][:2])
                           for ln in r["text"].split("\n")[-3:] for e in r["entities"]) for r in sigs),
          "signature documents: a name alone on one of the last lines", len(sigs))
    # D-40a (review): fathers from men's names that are not also
    # women's names; one spelling per person (the pool's own); a title is
    # never above a bare given name; a list ends its line
    loc = BUILDER.values.loc("az")
    fathers = [r["text"][f["start"]:f["end"]] for r in patro for f in ents(r, "GIVENNAME")
               if r["text"][f["end"]:].startswith((" oğlu", " qızı"))]
    check(fathers and all(v in loc.first_names_m and v not in loc.first_names_f for v in fathers),
          "fathers are men's names not in the women's pool",
          [v for v in fathers if v in loc.first_names_f][:5])
    spelled = [e["text"] for r in nl for e in r["entities"] if e["text"] in BUILDER.values.name_variants]
    check(not spelled, "name lists use the pool's own spelling, no English-style or Cyrillic variant", spelled[:5])
    check(not any(r["_spec"].get("signature") == "title_given" for r in sigs)
          and all(not re.search(r"^(" + "|".join(B.SIGNATURE_TITLES) + r")\n\S+$", r["text"], re.M)
                  for r in sigs if r["_spec"]["signature"] != "greeting_given"),
          "no title above a bare given name")
    def ends_line(r) -> bool:
        # after the last oğlu/qızı: at most a surname (given-first style) or a
        # role tail and a punctuation mark, then a line break
        last = [m for m in re.finditer(r"(?<!\w)(oğlu|qızı)(?!\w)", r["text"])][-1]
        return re.match(r"( \S+)?( — [^\n]+)?[.;,]?\n", r["text"][last.end():]) is not None
    check(all(ends_line(r) for r in lists), "the list's last line ends with a line break",
          [r["id"] for r in lists if not ends_line(r)][:3])
    orgs = [r for r in nl if r["_spec"]["namelist"] == "after_org"]
    check(orgs and all(re.search(r"(MMC|ASC)(-ni)? $", r["text"][:r["entities"][0]["start"]]) for r in orgs),
          "after-organisation documents: the name right after the organisation", len(orgs))


def test_d36b_review() -> None:
    """D-36b (native review): FIN clauses take "olaraq" before a
    recording verb (R1); the "private key stays on the server" sentence never
    sits beside a private key written out; no fixed sentence twice in one
    document."""
    from piigen.targeted.test_frames import RECORDING_VERBS
    verb = re.compile(r"\{v\}((?: \w+){0,2}) (" + "|".join(RECORDING_VERBS) + r")\b")
    bare = [t for t in B.CLERICAL_VALUE["AZ_FIN"]
            if verb.search(t) and not re.search(r"\{v\} (olaraq|kimi)\b", t)]
    check(not bare, "clerical FIN clauses: a recording verb after the value takes olaraq/kimi (R1)", bare)
    sampler = B.TargetedBuilder(seed=9, n_docs=1)
    sampler.q["contrast"]["key_pair_private_rate"] = 0.5     # enough documents of both kinds
    for k in ("token_key", "ipv6_mac", "licence_id"):        # only key_pair documents
        sampler.q["contrast"][k] = 0.0
    docs = [sampler._compose("contrast") for _ in range(400)]
    beside = [d for d, spec in docs if spec.get("sub") == "key_pair" and spec.get("with_private")]
    check(beside and not any(B.PUBLIC_SERVER_AFTER in d.text for d in beside),
          "no `private key stays on the server` sentence beside a private key", len(beside))
    check(not any(B.PUBLIC_VERIFY_INTRO in d.text and B.PUBLIC_VERIFY_AFTER in d.text for d, _ in docs),
          "the signature-verification intro is not followed by the same point again")
    pools = [B.parse_marked(s)[0] + B.parse_marked(s)[1] + B.parse_marked(s)[2]
             for s in B.VILLAGE_CONTROLS + B.KINSHIP_CONTROLS] + B.PUBLIC_AFTER + B.PEM_AFTER
    twice = [(r["id"], s) for r in RECORDS for s in pools if r["text"].count(s) >= 2]
    vil = [sampler._compose("village")[0].text for _ in range(400)]
    twice += [s for t in vil for s in pools if t.count(s) >= 2]
    check(not twice, "no control or after-sentence twice in one document", twice[:3])


def test_d35a_dates() -> None:
    """D-35a: DATE look-alikes in `label: value` lines -- most forms carry a
    date line, keyed containers a date column -- and only invalid dates."""
    # the rate on composed forms: early in a small build, dated forms fail the
    # language gate a little more often (1,500 documents: 79%; 25,000: 90.2%)
    composer = B.TargetedBuilder(seed=11, n_docs=1)
    specs = [composer._compose("form")[1] for _ in range(1000)]
    with_date = sum("DATE" in s["labels"] for s in specs)
    check(with_date >= 0.85 * len(specs), "most forms carry a date line", f"{with_date}/{len(specs)}")
    forms = [r for r in RECORDS if r["_spec"]["family"] == "form"]
    keyed = [r for r in RECORDS if r["_spec"].get("format") in B.DATE_KEYED_FORMATS]
    with_col = sum("DATE" in r["_spec"]["columns"] for r in keyed)
    check(keyed and with_col >= 0.75 * len(keyed), "most keyed containers carry a DATE column",
          f"{with_col}/{len(keyed)}")
    kinds = collections.Counter(d["kind"] for r in forms + keyed for d in r["_decoys"] if d["resembles"] == "DATE")
    check(kinds and set(kinds) <= set(B.DATE_SLOT_KINDS),
          "date look-alikes there are invalid dates only (month 13-18, impossible day, ISO out of range)",
          dict(kinds))


def _family_records(family: str, n: int, seed: int = 21) -> list[dict]:
    """`n` documents of one family that passed every gate (`_check`)."""
    composer = B.TargetedBuilder(seed=seed, n_docs=100_000)    # the 3% cap as in a full build
    out: list[dict] = []
    for _ in range(n * 3):
        d, spec = composer._compose(family)
        record, _reason = composer._check(d, spec)
        if record:
            out.append(record)
            composer._accept(record)            # the steering a real build does
            if len(out) == n:
                break
    return out


def _marked(r: dict, x: dict, before: int = 0, after: int = 0) -> tuple[str, str, str]:
    t = r["text"]
    return t[max(0, x["start"] - before):x["start"]], t[x["start"]:x["end"]], t[x["end"]:x["end"] + after]


def _gates_ok(records: list[dict]) -> list:
    bad = []
    for r in records:
        if validate_example(r) or screen_record(r) or \
                find_leaked_pii(r["text"], r["entities"], decoy_spans=r["_decoys"]):
            bad.append(r["id"])
        spans = sorted([(e["start"], e["end"]) for e in r["entities"]] + [(x["start"], x["end"]) for x in r["_decoys"]])
        if any(b[0] < a[1] for a, b in zip(spans, spans[1:])):
            bad.append(r["id"])
    return bad


def test_d51h() -> None:
    """D-51h (v4 targeted data), D-51d and D-51i: every new construction --
    labels and spans right, look-alikes unlabelled, the pairs present, the
    suffix rules, and ID cards and licences that never share a shape."""
    from piigen.locales import az as AZ
    from piigen.targeted import frames_v4 as V4
    from piigen.targeted.test_frames import RECORDING_VERBS

    # -- item 1-2: cross-anchor look-alikes ---------------------------------
    cross = _family_records("cross_anchor", 700)
    check(len(cross) >= 650 and not _gates_ok(cross), "cross_anchor documents pass every gate", len(cross))
    subs = collections.Counter(r["_spec"]["cross_slot"] for r in cross)
    check(set(subs) == set(Q.load()["cross_anchor"]["subs"]), "every cross-anchor slot is written", dict(subs))
    check(all(r["entities"] and r["_decoys"] for r in cross),
          "each cross-anchor document pairs a real value with a look-alike")
    short = [r for r in cross if r["_spec"]["cross_slot"] == "short_number"]
    ok = all(any(e["label"] == r["_spec"]["short_label"] for e in r["entities"])
             and any(x["kind"] == B.SHORT_KIND[r["_spec"]["short_label"]] and
                     re.fullmatch(r"\d{2,3}", r["text"][x["start"]:x["end"]]) for x in r["_decoys"])
             for r in short)
    check(short and ok, "short numbers: a real value of the slot's label beside an unlabelled 2-3-digit number",
          len(short))
    fmts = collections.Counter((r["_spec"]["short_label"], r["_spec"]["short_format"]) for r in short)
    check({f for _l, f in fmts} == {"prose", "kv", "csv"} and
          {l for l, _f in fmts} == set(B.SHORT_KIND), "short numbers in prose, `label: value` and CSV cells, "
          "after every ID/token word", dict(fmts))
    same = 0
    for r in short:
        if r["_spec"]["short_format"] != "prose":
            continue
        x = r["_decoys"][0]
        e = next(e for e in r["entities"] if e["label"] == r["_spec"]["short_label"])
        line = lambda s, t=r["text"]: t[t.rfind("\n", 0, s) + 1 if "\n" in t[:s] else 0:s][-40:]   # noqa: E731
        same += r["text"][:x["start"]].endswith(line(e["start"])[-20:])
    check(same > 0, "some short-number pairs share the left context exactly", same)
    for sub, kinds, follow in (("room_code", {"room_code", "door_code"}, re.compile(r" (qapı )?kodu\b")),):
        docs = [r for r in cross if r["_spec"]["cross_slot"] == sub]
        ok = all(any(x["kind"] in kinds and follow.match(r["text"][x["end"]:]) for x in r["_decoys"])
                 and any(e["label"] == "CARD_SECURITY_CODE" for e in r["entities"]) for r in docs)
        check(docs and ok, "room/door numbers followed by `kodu`, unlabelled, beside a real CVV", len(docs))
    names = [r for r in cross if r["_spec"]["cross_slot"] == "name_org"]
    ok = all(any(e["label"] == r["_spec"]["name_label"] for e in r["entities"])
             and all(x["kind"] == r["_spec"]["name_kind"] for x in r["_decoys"]) for r in names)
    check(names and ok, "name slots: a real surname/town/street and a company/project/code look-alike", len(names))
    slot_word = re.compile(r"(soyad|şəhər|küçə)\w* (kimi|olaraq|sahəsində) $|(Soyad|Soyadı|Şəhər|Küçə): $")
    ok = all(slot_word.search(_marked(r, x, before=40)[0]) for r in names for x in r["_decoys"] + r["entities"])
    check(ok, "name-slot values sit right after soyad/şəhər/küçə + kimi/olaraq/sahəsində (or `Soyad:`)")
    org = [r["text"][x["start"]:x["end"]] for r in names for x in r["_decoys"]]
    check(any(re.search(r" (MMC|ASC|Holdinq)$", v) for v in org) and any(re.fullmatch(r"[A-Z]{3}\d{3}", v) for v in org)
          and any(" " in v and v.split()[-1][0].islower() for v in org),
          "company names, AAA999 codes and town + project nouns in the name slots", org[:4])
    mac = [r for r in cross if r["_spec"]["cross_slot"] == "mac_fragment"]
    check(mac and all(any(e["label"] == "MAC_ADDRESS" for e in r["entities"]) and
                      all(x["kind"] == "mac_fragment_dashed" for x in r["_decoys"]) and
                      not any(e["label"] == "DATE" for e in r["entities"]) for r in mac),
          "MAC fragments unlabelled (never DATE) beside a real MAC", len(mac))
    iban = [r for r in cross if r["_spec"]["cross_slot"] == "iban_fragment"]
    csv_iban = [r for r in iban if r["_spec"].get("iban_format") == "csv"]
    check(iban and csv_iban and all(sum(e["label"] == "IBAN" for e in r["entities"]) >= 1 for r in iban)
          and {r["_spec"]["iban_kind"] for r in iban} == {"iban_fragment_short", "zip_shape_in_iban_field"},
          "IBAN fragments (AZ1234, AZ37NAB), in prose and CSV iban cells, beside real IBANs",
          (len(iban), len(csv_iban)))
    cells = [_marked(r, x, before=1, after=1) for r in csv_iban for x in r["_decoys"]]
    check(all(b in ",;\n" and a in ",;" for b, _v, a in cells), "CSV IBAN fragments are bare cells", cells[:2])
    ipv4 = [r for r in cross if r["_spec"]["cross_slot"] == "ipv4"]
    check(ipv4 and {r["_spec"]["ipv4_kind"] for r in ipv4} == set(B.IPV4_KINDS)
          and all(any(e["label"] == "IPV4_ADDRESS" for e in r["entities"]) for r in ipv4),
          "every IPv4 look-alike shape beside a real IPv4", len(ipv4))
    zips = [r for r in cross if r["_spec"]["cross_slot"] == "zip_code"]
    tails = tuple(V4.ZIP_TAILS)
    ok = all(any(e["label"] == "ZIPCODE" and not r["text"][e["end"]:].startswith(tails) for e in r["entities"])
             and all(r["text"][x["end"]:].startswith(tails) for x in r["_decoys"]) for r in zips)
    check(zips and ok, "right context: the same indeks sentence, the code followed by `məhsul kodu`", len(zips))

    # -- item 3: the locative + verb frame -----------------------------------
    loc = _family_records("locative", 400)
    check(len(loc) >= 380 and not _gates_ok(loc), "locative documents pass every gate", len(loc))
    labs = collections.Counter(e["label"] for r in loc for e in r["entities"])
    check(set(labs) == set(V4.LOCATIVE), "cards, VÖENs, ID cards, passports and IBANs in the frame", dict(labs))
    verbs = re.compile(r" (" + "|".join(RECORDING_VERBS + ("seçilib", "daxil edilib", "saxlanılır",
                                                           "olaraq qeyd olunub")) + r")\b")
    before_ok = re.compile(r"\w+(da|də|na|nə|ya|yə|a|ə) $")
    vals = [(r, e) for r in loc for e in r["entities"]]
    ok = all(verbs.match(r["text"][e["end"]:]) and before_ok.search(r["text"][max(0, e["start"] - 30):e["start"]])
             for r, e in vals)
    check(ok, "the value follows a locative/dative noun and comes right before the verb",
          [r["text"][max(0, e["start"] - 30):e["end"] + 15] for r, e in vals
           if not (verbs.match(r["text"][e["end"]:]) and before_ok.search(r["text"][max(0, e["start"] - 30):e["start"]]))][:2])
    la = [r for r in loc if r["_decoys"]]
    check(la and all(not value_valid(ALL_DECOY_KINDS[x["kind"]].resembles, r["text"][x["start"]:x["end"]])[0]
                     for r in la for x in r["_decoys"]) and
          not any(x["kind"] in B.CHECKSUM_ONLY_KINDS for r in la for x in r["_decoys"]),
          "locative look-alikes are wrong-length/format values, never checksum-only", len(la))
    cards = [e["text"] for e in (e for r in loc for e in r["entities"]) if e["label"] == "PAYMENT_CARD_NUMBER"]
    check(any(" " in c for c in cards) and any(" " not in c for c in cards),
          "locative cards both grouped and plain", len(cards))

    # -- item 9: invalid values in the label slot ----------------------------
    slot = _family_records("slot_invalid", 400)
    check(len(slot) >= 380 and not _gates_ok(slot), "slot_invalid documents pass every gate", len(slot))
    combos = collections.Counter((r["_spec"]["slot_label"], r["_spec"]["slot_format"]) for r in slot)
    check(len(combos) == 2 * len(V4.SLOT_KINDS),
          "TIME/AGE/DATE/FIN/card/ZIP (v4.2: IBAN/licence/IPv4), each in prose and in `label: value` lines",
          dict(combos))
    # coverage report section 5, items 7 and 10
    zips = [r for r in slot if r["_spec"]["slot_label"] == "ZIPCODE"]
    # v4.1 (D-52d): the slot takes turns with the protected zip_wrong_length
    two = [r for r in zips if any(x["kind"] == "zip_two_digits" and
                                  re.fullmatch(r"\d{2}", r["text"][x["start"]:x["end"]]) for x in r["_decoys"])]
    check(zips and len(two) >= 0.35 * len(zips)
          and all(any(x["kind"] in ("zip_two_digits", "zip_wrong_length") for x in r["_decoys"])
                  and any(e["label"] == "ZIPCODE" for e in r["entities"]) for r in zips),
          "a 2-digit number (or a wrong-length ZIP) after a ZIP word, unlabelled, beside a real ZIP",
          (len(two), len(zips)))
    cal = [(r, e) for r in slot if r["_spec"]["slot_label"] == "TIME" for e in r["entities"]
           if e["label"] == "TIME" and re.search(r"[Tt]əqvim\w* $", r["text"][max(0, e["start"] - 25):e["start"]])]
    check(cal, "real times right after a calendar word (təqvimdə)", len(cal))
    ok = True
    for r in slot:
        lab = r["_spec"]["slot_label"]
        real = [e for e in r["entities"] if e["label"] == lab]
        fake = [x for x in r["_decoys"] if x["kind"] == r["_spec"]["slot_kind"]]
        ok &= len(real) == 1 and len(fake) == 1 and \
            not value_valid(lab, r["text"][fake[0]["start"]:fake[0]["end"]])[0]
        # the same sentence or `Field:` line up to the value
        before = lambda s: re.split(r"[.!?] |\n", r["text"][:s])[-1]                    # noqa: E731
        ok &= before(real[0]["start"]) == before(fake[0]["start"]) != ""
    check(ok, "one valid and one invalid value, the same label word right before both")
    kinds = collections.Counter(r["_spec"]["slot_kind"] for r in slot)
    check(set(kinds) == {k for ks in V4.SLOT_KINDS.values() for k in ks},
          "hours > 23, minutes > 59, negative/implausible ages, impossible dates, hyphenated FINs, "
          "wrong-length cards", dict(kinds))

    # -- item 7: suffixed towns in verbs that also take people ---------------
    pv = _family_records("place_verbs", 300)
    check(len(pv) >= 280 and not _gates_ok(pv), "place_verbs documents pass every gate", len(pv))
    sfx = [(r, x, next(e for e in r["entities"] if (e["start"], e["end"]) == (x["start"], x["end"])))
           for r in pv for x in r["_suffixes"]]
    cases = collections.Counter((e["label"], x["case"]) for _r, x, e in sfx)
    check({("CITY", c) for c in ("cop", "ins", "acc", "abl")} | {("SURNAME", "abl")} <= set(cases),
          "towns with the copula, instrumental, accusative, ablative; surnames with the ablative", dict(cases))
    check(all(e["label"] == "SURNAME" for _r, x, e in sfx if x["case"] == "abl" and
              r_text_is_person(_r, x)) , "an ablative after which a person acts (`o, ...`) is a SURNAME")
    whole = all(not r["text"][x["end"]:x["end"] + 1].isalpha() and not r["text"][x["start"] - 1:x["start"]].isalpha()
                for r, x, _e in sfx)
    check(whole, "the suffix is inside the span (D-9): the span is the whole word")
    acc = [(r, x) for r, x, e in sfx if x["case"] == "acc" and e["label"] == "CITY" and x["surface"] == "plain"]
    check(acc and all(r["text"][x["stem_end"] - 1].lower() not in "aıoueəiöü" for r, x in acc),
          "accusative towns end in a consonant before the suffix", len(acc))
    sep = sum(r["_spec"].get("ins_separate", 0) for r in pv)
    check(sep and all(r["text"][e["end"]:e["end"] + 4] == " ilə" for r in pv if r["_spec"].get("ins_separate")
                      for e in r["entities"] if e["label"] == "CITY" and not any(
                          x["start"] == e["start"] for x in r["_suffixes"])),
          "`<town> ilə`: the town alone is the span", sep)
    loc_az = BUILDER.values.loc("az")
    # (noise may write a town in ASCII and any case; a native k/q softens:
    # Qıvraq -> Qıvrağı)
    fold = lambda s: s.replace("İ", "i").casefold().translate(str.maketrans("əışçğöü", "eiscgou"))  # noqa: E731
    towns = {fold(c) for c in loc_az.cities}
    stems = [fold(r["text"][e["start"]:(next((x["stem_end"] for x in r["_suffixes"] if x["start"] == e["start"]),
                                             e["end"]))]).rstrip("'") for r in pv for e in r["entities"]
             if e["label"] == "CITY"]
    known = lambda s: s in towns or s[:-1] + "q" in towns or s[:-1] + "k" in towns   # noqa: E731
    check(stems and all(known(s) for s in stems), "only towns are called `şəhər` (D-43c)",
          [s for s in stems if not known(s)][:3])

    # -- item 5: short Ed25519 private keys -----------------------------------
    keys = _family_records("short_keys", 200)
    check(len(keys) >= 190 and not _gates_ok(keys), "short_keys documents pass every gate", len(keys))
    priv = [e["text"] for r in keys for e in r["entities"] if e["label"] == "PRIVATE_KEY"]
    pubs = [r["text"][x["start"]:x["end"]] for r in keys for x in r["_decoys"]]
    check(priv and all("MC4CAQAw" in k and k.startswith("-----BEGIN PRIVATE KEY-----") for k in priv),
          "Ed25519 PKCS#8 private keys (`MC4CAQAw...`)", len(priv))
    check(pubs and all("MCowBQYDK2VwAyEA" in p for p in pubs) and len(priv) >= 3 * len(pubs),
          "beside them Ed25519 public look-alikes, at least 3 private per public", (len(priv), len(pubs)))
    check(len(set(priv)) == len(priv), "every private key is fresh")
    check(any(sum(e["label"] == "PRIVATE_KEY" for e in r["entities"]) >= 2 for r in keys),
          "several keys in one document")

    # -- item 6: non-names in the name frames ---------------------------------
    nl = _family_records("namelist", 600)
    check(len(nl) >= 570 and not _gates_ok(nl), "namelist documents pass every gate", len(nl))
    ctrl = collections.Counter(x["kind"] for r in nl for x in r["_decoys"])
    check({"namelist_control", "role_word_control", "signature_title_only"} <= set(ctrl),
          "list-line, role-word and title-only signature controls", dict(ctrl))
    from piigen.locales.az import SETTLEMENTS
    pools = {fold(n) for loc in LOCALES_ALL() for n in list(loc.first_names_m) + list(loc.first_names_f)
             + list(getattr(loc, "cities", ())) + list(getattr(loc, "surname_stems", ()))}
    pools |= {fold(n) for n in SETTLEMENTS}
    words = {fold(w) for r in nl for x in r["_decoys"] for w in re.findall(r"[^\W\d_]+", r["text"][x["start"]:x["end"]])}
    check(not words & pools, "no control word is a name or a place in any pool", sorted(words & pools)[:5])
    mixed = [r for r in nl if r["_spec"].get("control_line") or r["_spec"].get("control_list")]
    check(mixed and all(any(e["label"] == "GIVENNAME" for e in r["entities"]) for r in mixed),
          "lists with controls still hold labelled names", len(mixed))
    role = [r for r in nl if r["_spec"].get("role_control")]
    lower = re.compile(r"(?<!\w)(" + "|".join(B.ROLE_WORDS) + r") $")
    check(role and all(any(lower.search(r["text"][:x["start"]]) for x in r["_decoys"]) for r in role)
          and all(r["entities"] for r in role), "a lowercase role word, then a capitalised non-name, "
                                                "beside role + name", len(role))
    title = [r for r in nl if r["_spec"].get("signature") == "title_only"]
    check(title and all(r["text"].startswith("Hörmətli ") and r["entities"]
                        and r["_decoys"][-1]["end"] >= len(r["text"].rstrip()) - 200
                        and r["text"][r["_decoys"][-1]["start"] - 10:r["_decoys"][-1]["start"]] == "Hörmətlə,\n"
                        for r in title), "a title-only signature, the letter addressed to a named person",
          len(title))

    # -- item 8: CSV rows with cvv and şəxsiyyət_vəsiqəsi columns -------------
    composer = B.TargetedBuilder(seed=31, n_docs=1)
    composer.q["structured"]["cvv_csv_rate"] = 1.0
    csv = []
    for _ in range(300):
        d, spec = composer._compose("structured")
        rec, _why = composer._check(d, spec)
        if rec:
            csv.append(rec)
    check(len(csv) >= 270, "cvv CSV tables pass every gate", len(csv))
    ok = all(has_anchor_(r, e) for r in csv for e in r["entities"] if e["label"] == "CARD_SECURITY_CODE")
    check(ok, "every CVV in a CSV row is licensed by its `cvv` header")
    with_id = [r for r in csv if "AZ_ID_CARD_NUMBER" in r["_spec"]["columns"]]
    check(len(with_id) >= 0.6 * len(csv) and any(r["_spec"]["format"] == "csv_snake" and "şəxsiyyət_vəsiqəsi"
                                                 in r["text"] for r in with_id),
          "most cvv tables have an ID-card column, some headed `şəxsiyyət_vəsiqəsi`", len(with_id))
    check(sum(r["_spec"]["cvv_rows_n"] >= 2 for r in csv) >= 0.5 * len(csv), "most cvv tables have 2-3 rows")

    # -- item 4: ID cards and licences side by side --------------------------
    # (a single-row container may give one of the two cells to a look-alike)
    both = [r for r in RECORDS if r["_spec"].get("id_and_licence")]
    full = sum({"AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"} <= {e["label"] for e in r["entities"]} for r in both)
    check(both and all({"AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"} <= set(r["_spec"]["columns"]) for r in both)
          and full >= 0.8 * len(both), "ID card and licence in the same rows", f"{full}/{len(both)}")
    ids = [e["text"].upper() for r in RECORDS for e in r["entities"] if e["label"] == "AZ_ID_CARD_NUMBER"]
    lic = [e["text"].upper() for r in RECORDS for e in r["entities"] if e["label"] == "AZ_DRIVER_LICENSE_NUMBER"]
    check(all(len(i) in (9, 10) for i in ids) and all(len(x) == 8 for x in lic) and not set(ids) & set(lic),
          "ID cards 9-10 characters, licences 8: the shapes never collide")
    other = sum(i[:2] not in ("AA", "AB") and i[:3] not in ("DYI", "MYI") for i in ids)
    check(other >= 0.4 * len(ids), "most ID cards in the build take another two-letter prefix",
          f"{other}/{len(ids)}")
    keyed = [r for r in RECORDS if r["_spec"].get("format") in ("csv_snake", "json", "config", "log")]
    check(any("şəxsiyyət_vəsiqəsi" in r["text"] for r in keyed) and
          any("sürücülük_vəsiqəsi" in r["text"] for r in keyed), "Azerbaijani snake_case ID/licence keys")

    # -- D-51i: the year suffix outside the span, harmonised ------------------
    check([AZ.year_suffix(y) for y in (2016, 2021, 2023, 2010, 2000, 1900, 1990, 1944, 1999, 2040)]
          == ["-cı", "-ci", "-cü", "-cu", "-ci", "-cü", "-cı", "-cü", "-cu", "-cı"],
          "the year suffix follows the year's last spoken word")
    rng = random.Random(2)
    dates = [AZ.date(rng.randint(1, 28), rng.randint(1, 12), rng.randint(1945, 2030), rng) for _ in range(3000)]
    check(not any(re.search(r"-c[ıiuü]\b| il$", v) for v in dates), "az.date() writes no `-ci il` inside the value")
    composer = B.TargetedBuilder(seed=41, n_docs=1)
    composer.q["fix_round"]["date_year_suffix_rate"] = 1.0
    tails = []
    composer.q["decoy_groups"].update(sentence_initial=0, policy_names=0, building=0, other=0, cvv=0)
    for _ in range(3000):
        d, spec = composer._compose("decoy_pair")
        composer.sub_counts["noun_label"][ALL_DECOY_KINDS[spec["kind"]].resembles] += 1
        if spec.get("year_suffix"):
            e = next(e for e in d.entities if e["label"] == "DATE")
            tails.append((e["text"], d.text[e["end"]:e["end"] + len(spec["year_suffix"])], spec["year_suffix"]))
    check(tails and all(t == s and s == AZ.year_suffix(int(v[-4:])) + " il" for v, t, s in tails),
          "`-cı il` after a spelled date, outside the span, harmonised", tails[:2])

    # -- D-51d: no checksum-only look-alike anywhere --------------------------
    every = RECORDS + cross + loc + slot + pv + keys + nl + csv
    check(not any(x["kind"] in B.CHECKSUM_ONLY_KINDS for r in every for x in r["_decoys"]),
          "no checksum-only look-alike is written (D-51d)")
    # (review) D-51d masks every card shape whatever its Luhn, so a
    # card look-alike must differ by length or prefix; IMEI_BAD_LUHN (15
    # digits) never takes the Amex prefix 34/37 -- the 22 card-shaped ones the
    # dry run found in the LLM files came from the old generator
    from piigen import checksums as CK, negatives as NEG
    kinds = {k.kind: k for ks in NEG.ANCHORED_DECOYS.values() for k in ks}
    rng = random.Random(5)
    shaped = [v for v in (kinds["card_wrong_length"].make(rng) for _ in range(5000))
              if CK.card_brand_ok(re.sub(r"\D", "", v))]
    shaped += [v for v in (NEG.ADVERSARIAL["IMEI_BAD_LUHN"]("az", rng) for _ in range(5000))
               if CK.card_brand_ok(v)]
    check(not shaped, "card_wrong_length and IMEI_BAD_LUHN are never card-shaped (D-51d)", shaped[:3])
    # any two letters + 7 digits is an ID card now (D-51h): no look-alike of
    # another label may take that shape, or the data would say both
    id_shape = re.compile(r"^[A-Z]{2}\d{7}$")
    clash = collections.Counter()
    for k in kinds.values():
        if k.resembles == "AZ_ID_CARD_NUMBER":
            continue
        for _ in range(500):
            v = k.make(rng)
            clash[k.kind] += bool(isinstance(v, str) and id_shape.match(v.strip()))
    for name, make in list(NEG.HARD_NEGATIVES.items()) + list(NEG.ADVERSARIAL.items()):
        for _ in range(500):
            v = make("az", rng)
            clash[name] += bool(isinstance(v, str) and id_shape.match(v.strip()))
    check(not +clash, "no look-alike of another label takes the ID-card shape (2 letters + 7 digits)", +clash)
    # both IBAN fragment kinds in prose and in CSV iban cells (balanced
    # within the family: the global least-used choice left AZ37NAB 1 of 90)
    ib = collections.Counter((r["_spec"]["iban_kind"], r["_spec"].get("iban_format", "prose")) for r in iban)
    check(len(ib) == 4 and min(ib.values()) >= 3, "AZ37NAB and AZ1234 fragments both in prose and in CSV cells",
          dict(ib))
    # (the Ed25519 ratio, ssh-ed25519 lines included, is a --stats check on
    # the full build: it is global across families)

    # -- the sentences: no digits; R1 ----------------------------------------
    sentences = [s for _pool, s in V4.native_check_list()]
    check(not any(re.search(r"\d", s) for s in sentences), "frames_v4 sentences carry no digits")
    r1 = re.compile(r"(VÖEN|VÖEN-i|FİN|kodu|nömrəsi|açarı|tokeni|token|ünvanı|tarixi|yaşı|vaxtı|saatı|IBAN-ı|"
                    r"vəsiqəsi) \{v\} (" + "|".join(RECORDING_VERBS) + r")\b")
    bare = [s for s in sentences if r1.search(s)]
    check(not bare, "R1: after anchor + value a recording verb takes kimi/olaraq", bare)
    # D-51h native review (finding B): a LOCATIVE sentence has no
    # anchor word right before the value -- the frame is a locative noun, the
    # value, the verb (`Müqavilədə VÖEN {v} olaraq ...` was replaced)
    anchor_before = re.compile(r"(VÖEN|VOEN|kart nömrəsi|kartın nömrəsi|IBAN|vəsiqə\w*|pasport\w*|"
                               r"nömrəsi|nömrə)\s*(kimi|olaraq|:)?\s*\{v\}", re.IGNORECASE)
    bad = [s for sents in V4.LOCATIVE.values() for s in sents if anchor_before.search(s)]
    check(not bad, "no anchor word right before {v} in a LOCATIVE sentence", bad)
    # ... and the review's other fixes are in place (A, C-I)
    old_text = ("rayonun", "otaq {v} kodu", "kabinetin {v} kodu", "tərəfin şəxsiyyət vəsiqəsi {v}",
                "Formanın vəsiqə sahəsində", "{v} nömrəli qovluqda", "Ən çox darıxdığım {v}",
                "dəqiqə etibarlı olur", "qısaldılmış formada, {v}")
    from piigen.negatives import ANCHORED_DECOYS as _AD
    texts = sentences + [a for ks in _AD.values() for k in ks for a in k.anchors]
    check(not [t for t in old_text for x in texts if t in x], "D-51h native review fixes A-I applied",
          [t for t in old_text for x in texts if t in x][:3])
    pools = collections.defaultdict(list)
    for pool, sent in V4.native_check_list():
        pools[pool].append(sent)
    check(all(len(set(v)) == len(v) for v in pools.values()), "no sentence twice in one frames_v4 pool")


def r_text_is_person(r: dict, x: dict) -> bool:
    """The SURNAME_ABLATIVE sentences say `o, ...` / `o isə`: a person."""
    rest = r["text"][x["end"]:x["end"] + 80]
    return bool(re.search(r"\bo(,| isə)", rest.split(".")[0])) and r["text"][x["start"]].isupper()


def has_anchor_(r: dict, e: dict) -> bool:
    from piigen.anchors import has_anchor
    return has_anchor(e["label"], r["text"], e["start"], e["end"])


def LOCALES_ALL():
    from piigen.locales import LOCALES
    return LOCALES.values()


def test_d49_fsum() -> None:
    """D-49: the build is the same on every Python version. Python 3.12 made
    sum() of floats compensated, so a float total feeding a choice gave
    different builds on 3.11 (Mac) and 3.13 (Windows) from document 917 on.
    Every such total is math.fsum (correctly rounded everywhere)."""
    import functools
    import inspect
    import math
    import operator
    from piigen.locales.base import ForeignNames
    from piigen.values import ValueFactory
    deficit = inspect.getsource(B.TargetedBuilder._deficit)
    check("math.fsum(weights.values())" in deficit and "= sum(weights" not in deficit,
          "_deficit normalises the weights with math.fsum")
    check("math.fsum(" in inspect.getsource(ForeignNames.origin_weights),
          "foreign-name origin weights are summed with math.fsum")
    check("avg_weight = math.fsum(" in inspect.getsource(ValueFactory.city),
          "the city-weight average uses math.fsum")
    # why: the old left-to-right total of the case weights is not the
    # correctly rounded one, so 3.11's sum() and 3.12's sum() disagreed
    w = [float(v) for v in Q._weights(Q.load()["suffix"]["case_weights"]).values()]
    check(functools.reduce(operator.add, w) != math.fsum(w),
          "(documentation) the case weights' left-to-right total differs from fsum",
          (functools.reduce(operator.add, w), math.fsum(w)))


def test_time_seconds() -> None:
    """v3_shadow_shapes.md lead 1 (15 Oct): v3 missed 72 of 80
    `99:99:99` times. Labelled times with seconds in prose (`saat`), `Saat:`
    fields, ranges (both ends) and chat lines; chat and log line stamps in the
    same documents stay unlabelled (D-51f); v4_clean changes nothing."""
    from piigen.v4_clean import clean_doc_detail
    recs = _family_records("time_seconds", 400)
    check(len(recs) >= 380 and not _gates_ok(recs), "time_seconds documents pass every gate", len(recs))
    subs = collections.Counter(r["_spec"]["time_sub"] for r in recs)
    check(set(subs) == {"prose", "field", "range", "chat"}, "every construction present", subs)
    sec = re.compile(r"\d{2}:\d{2}:\d{2}")
    bad, stamps, joined, both_ends, saat, field = [], 0, 0, 0, 0, 0
    for r in recs:
        t = r["text"]
        times = [e for e in r["entities"] if e["label"] == "TIME"]
        if not any(sec.fullmatch(e["text"]) for e in times):
            bad.append(("no time with seconds", r["id"]))
        for x in r["_decoys"]:
            if x["kind"] == "time_line_stamp":
                stamps += 1
                ls = t.rfind("\n", 0, x["start"]) + 1
                if t[ls:x["start"]] not in ("", "["):
                    bad.append(("stamp not at a line start", r["id"]))
                if any(e["start"] < x["end"] and x["start"] < e["end"] for e in r["entities"]):
                    bad.append(("stamp labelled", r["id"]))
        for a, b in zip(times, times[1:]):
            gap = t[a["end"]:b["start"]]
            if gap in ("-", " – ", " - "):
                both_ends += 1
                joined += gap == "-"
        saat += sum(t[max(0, e["start"] - 5):e["start"]] == "saat " for e in times)
        field += sum(t[max(0, e["start"] - 6):e["start"]] == "Saat: " for e in times)
        res = clean_doc_detail({"id": r["id"], "text": t, "_doc_type": r.get("_doc_type"),
                                "entities": r["entities"], "_decoys": r["_decoys"]})
        if res.changes:
            bad.append(("v4_clean changes it", r["id"], [(c.rule, c.action, c.text) for c in res.changes]))
    check(not bad, "every document: a labelled time with seconds, stamps at line starts and unlabelled, "
          "nothing for v4_clean to change", bad[:5])
    check(stamps >= 400 and both_ends >= 60 and joined >= 25 and saat >= 100 and field >= 40,
          "stamps, ranges (both ends, some joined by a bare hyphen), `saat` and `Saat:` all frequent",
          dict(stamps=stamps, both_ends=both_ends, joined=joined, saat=saat, field=field))
    # the resolver takes both ends of a hyphen-joined range, and nothing else changes
    text = "Növbə saat 14:00:00-15:30:00 arasında davam edib, sonra 16:00-17:45."
    got, _ = resolve_claims(text, [{"label": "TIME", "text": v}
                                   for v in ("14:00:00", "15:30:00", "16:00", "17:45")])
    check(sorted(text[e["start"]:e["end"]] for e in got) == ["14:00:00", "15:30:00", "16:00", "17:45"],
          "the resolver places both ends of a range joined by a bare hyphen", got)
    for text, v in (("Kod 14:00-AB12 göndərilib.", "14:00"), ("Versiya 2-14:00 yükləndi.", "14:00"),
                    ("Nömrə 12:30-45 yazılıb.", "12:30")):
        got, _ = resolve_claims(text, [{"label": "TIME", "text": v}])
        check(not got, f"no range without a clock time on the other side: {text!r}", got)


def test_v41_a5() -> None:
    """v4.1 A5 (v3_shadow_shapes.md leads 3-5): key blocks with a placeholder
    body (unlabelled), bare ZIPs after a town with no index word (labelled),
    lines opened by a role/heading word (unlabelled) or a given name
    (labelled), PII-free documents weighted to v3's false-alarm labels, and
    the five-part IPv4 placeholder at ~60% of its kind."""
    from piigen.negatives import ALL_DECOY_KINDS, make_decoy
    from piigen.targeted import frames_v4 as V4
    from piigen.v4_clean import clean_doc_detail

    def clean_changes(recs):
        return [(r["id"], c.rule, c.action, c.text) for r in recs
                for c in clean_doc_detail({**r}).changes]

    # key blocks with a placeholder body
    kp = _family_records("key_placeholder", 200)
    check(len(kp) >= 190 and not _gates_ok(kp), "key_placeholder documents pass every gate", len(kp))
    bad = []
    for r in kp:
        blocks = [x for x in r["_decoys"] if x["kind"] == "private_key_placeholder"]
        for x in blocks:
            v = r["text"][x["start"]:x["end"]]
            body = re.sub(r"-----(?:BEGIN|END) [A-Z ]+-----", "", v).strip()
            if not (v.startswith("-----BEGIN ") and v.endswith("-----") and body in V4.KEY_PLACEHOLDER_BODIES):
                bad.append(("block shape", v[:60]))
            if any(e["start"] < x["end"] and x["start"] < e["end"] for e in r["entities"]):
                bad.append(("labelled", r["id"]))
        if len(blocks) != 1:
            bad.append(("blocks", r["id"], len(blocks)))
    real = sum(any(e["label"] == "PRIVATE_KEY" for e in r["entities"]) for r in kp)
    check(not bad, "one placeholder block per document, whole, never labelled", bad[:3])
    check(0.35 * len(kp) <= real <= 0.65 * len(kp), "about half beside a real, labelled key", real)
    check(not clean_changes(kp), "v4_clean changes nothing in key_placeholder documents", clean_changes(kp)[:3])

    # bare ZIPs after a town, no index word
    po = _family_records("postal", 300)
    check(len(po) >= 290 and not _gates_ok(po), "postal documents pass every gate", len(po))
    hits, bad = 0, []
    for r in po:
        t = r["text"]
        ents = sorted(r["entities"], key=lambda e: e["start"])
        for a, b in zip(ents, ents[1:]):
            if b["label"] == "ZIPCODE" and b["text"].isdigit() and a["label"] == "CITY":
                gap = t[a["end"]:b["start"]]
                if re.fullmatch(r"(?: şəhəri)?(?:, |; | — | - )", gap):
                    hits += 1
                    sent = max(t.rfind(". ", 0, a["start"]), t.rfind("\n", 0, a["start"])) + 1
                    if re.search(r"indeks|poçt", t[sent:b["start"]]):        # in the same sentence
                        bad.append(t[sent:b["end"]])
    check(hits >= 100, "bare ZIPs right after a town and a comma, semicolon or dash", hits)
    check(not bad, "no index word before those ZIPs", bad[:2])
    check(not clean_changes(po), "v4_clean changes nothing in postal documents", clean_changes(po)[:3])

    # lines opened by a role or heading word, or a given name
    nl = [r for r in _family_records("namelist", 600) if r["_spec"]["namelist"] == "line_start"]
    check(len(nl) >= 60 and not _gates_ok(nl), "line_start documents pass every gate", len(nl))
    bad, kinds = [], collections.Counter()
    for r in nl:
        t = r["text"]
        starts = {m.end() for m in re.finditer(r"\n", t)}
        opened = [x for x in r["_decoys"] if x["kind"] == "line_start_control"]
        names = [e for e in r["entities"] if e["label"] == "GIVENNAME" and e["start"] in starts]
        kinds["role/heading"] += len(opened)
        kinds["name"] += len(names)
        if not opened or not names:
            bad.append(r["id"])
        if any(x["start"] not in starts or t[x["end"]] != ":" for x in opened):
            bad.append(("control not at a line start before a colon", r["id"]))
    check(not bad, "every line_start document opens lines with both a control word and a name", bad[:3])
    check(kinds["role/heading"] >= 2 * len(nl) and kinds["name"] >= len(nl), "several of each", dict(kinds))
    check(not clean_changes(nl), "v4_clean changes nothing in line_start documents", clean_changes(nl)[:3])

    # PII-free documents weighted to v3's false-alarm labels
    pf = _family_records("pii_free", 600)
    check(len(pf) >= 590 and not _gates_ok(pf) and not any(r["entities"] for r in pf),
          "pii_free documents pass every gate and hold no label", len(pf))
    labs = collections.Counter(ALL_DECOY_KINDS[x["kind"]].resembles for r in pf for x in r["_decoys"])
    check(labs["CARD_SECURITY_CODE"] > labs["EMAIL"] and labs["AZ_FIN"] > labs["IPV6_ADDRESS"]
          and labs["SURNAME"] >= 20, "v3's false-alarm labels lead the PII-free look-alikes", dict(labs.most_common(8)))
    kp_free = sum(x["kind"] == "private_key_placeholder" for r in pf for x in r["_decoys"])
    check(kp_free >= 20, "PII-free documents carry placeholder key blocks", kp_free)

    # five-part IPv4 placeholders: 60% of the kind, never a valid IPv4
    k = ALL_DECOY_KINDS["ipv4_placeholder"]
    rng = random.Random(5)
    vals = [make_decoy(k, rng) for _ in range(2000)]
    five = sum(len(v.split(".")) == 5 for v in vals) / len(vals)
    check(0.55 <= five <= 0.65, "five-part IPv4 placeholders ~60% of the kind", round(five, 3))
    check(not any(value_valid("IPV4_ADDRESS", v)[0] for v in vals), "an IPv4 placeholder is never a valid IPv4")


def test_v41_generator() -> None:
    """v4.1 generator (D-52b-d; the #91 fix list and native review of
    #90, A-G): every new construction passes the gates and v4_clean changes
    nothing; the look-alikes and the labels follow the rules below."""
    import copy
    from piigen import blocklist
    from piigen.negatives import ALL_DECOY_KINDS, SEQUENTIAL_TIMES, make_decoy, policy_allowlist
    from piigen.targeted import frames_v4 as V4
    from piigen.v4_clean import clean_doc_detail

    def clean_changes(recs):
        return [(r["id"], c.rule, c.text) for r in recs for c in clean_doc_detail({**r}).changes]

    # -- A, B: one story per key block (removed or template) ----------------------
    kp = _family_records("key_placeholder", 200)
    bad = []
    for r in kp:
        t = r["text"]
        intro = next(i for i in V4.KEY_PLACEHOLDER_INTROS if i in t)
        story = V4.KEY_PLACEHOLDER_INTRO_STORY[intro]
        x = next(x for x in r["_decoys"] if x["kind"] == "private_key_placeholder")
        body = re.sub(r"-----(?:BEGIN|END) [A-Z ]+-----", "", t[x["start"]:x["end"]]).strip()
        b_story = next(k for k, v in V4.KEY_PLACEHOLDER_BODY_STORY.items() if body in v)
        if story != "any" and b_story not in (story, "both"):
            bad.append((intro, body))
        for a in (a for a in V4.KEY_PLACEHOLDER_AFTER if a in t):
            a_story = V4.KEY_PLACEHOLDER_AFTER_STORY[a]
            if a_story != "any" and (b_story not in (a_story, "both") or story not in (a_story, "any")):
                bad.append((intro, body, a))
    check(len(kp) >= 190 and not bad, "A/B: intro, body and closing sentence tell one story", bad[:3])

    # -- C, D, E, F: line-start blocks ------------------------------------------
    nl = [r for r in _family_records("namelist", 900, seed=23) if r["_spec"]["namelist"] == "line_start"]
    agent, customer = set(V4.STAMP_AGENT_LINES), set(V4.STAMP_CUSTOMER_LINES)
    own = {r: set(v) for r, v in V4.LINE_START_OWN_LINES.items()}
    mus_agent, own_bad, block_bad = 0, [], []
    for r in nl:
        t = r["text"]
        for m in re.finditer(r"(?m)^(Müştəri|Kuryer|Mühasib|Direktor|Kassir): (.*)$", t):
            if m.group(1) == "Müştəri" and m.group(2) in agent:
                mus_agent += 1
            if m.group(1) in own and m.group(2) not in own[m.group(1)]:
                own_bad.append(m.group(0))
        intro = next(i for i in V4.LINE_START_INTROS if i in t)
        block = t[t.index(intro) + len(intro):].strip("\n").split("\n")[:sum(r["_spec"]["line_start"].values())]
        if not all(re.match(r"[^\W\d_]+(?: [^\W\d_]+)?: \S", line) and
                   line.split(": ", 1)[1] in agent | customer | set(V4.LINE_START_HEADINGS.values())
                   | {v for vs in own.values() for v in vs} for line in block):
            block_bad.append(block)
    named_agent = sum(r["_spec"].get("line_start_named_agent", 0) for r in nl)
    check(nl and not mus_agent and not own_bad, "C: a speaker's line fits the speaker (Müştəri never an agent's)",
          (mus_agent, own_bad[:2]))
    check(named_agent >= 0.2 * len(nl), "D: named people also speak agent lines, so the line doesn't give the label away",
          (named_agent, len(nl)))
    check(not any("Görüşün protokolundan" in r["text"] for r in nl), "E: no meeting minutes around a support chat")
    check(not block_bad, "F: each line of the block is one speaker and one utterance; the next sentence starts below",
          block_bad[:1])
    check("Çatdırılma ünvanı: {t}; {z}; Azərbaycan." in V4.POSTAL_BARE_SENTENCES
          and not any("Sifariş {t}; {z}" in s for s in V4.POSTAL_BARE_SENTENCES), "G: the postal sentence reworded")
    check(not clean_changes(kp + nl), "v4_clean changes nothing in the A-G documents", clean_changes(kp + nl)[:3])

    # -- items 2, 3: IPv4 ---------------------------------------------------------
    ca = [r for r in _family_records("cross_anchor", 1200, seed=29) if r["_spec"].get("cross_slot") == "ipv4"]
    twins, same, ratio = 0, [], [0, 0]
    for r in ca:
        reals = [e for e in r["entities"] if e["label"] == "IPV4_ADDRESS"]
        fakes = [x for x in r["_decoys"] if ALL_DECOY_KINDS[x["kind"]].resembles == "IPV4_ADDRESS"]
        ratio[0] += len(reals)
        ratio[1] += len(fakes)
        for x in fakes:
            fv = r["text"][x["start"]:x["end"]]
            # a twin differs in one octet at most (the invalid one, or the added
            # fourth); D-56a's over-255 octet is mostly the first
            fo = fv.split(".")
            twins += any(sum(a == b for a, b in zip(fo, e["text"].split("."))) >= min(len(fo), 4) - 1
                         for e in reals)
            left = r["text"][max(0, x["start"] - 30):x["start"]]
            same += [fv for e in reals if r["text"][max(0, e["start"] - 30):e["start"]] == left]
    check(ca and twins >= 0.6 * ratio[1], "item 2: most IPv4 look-alikes sit beside a valid twin of their pattern",
          (twins, ratio[1]))
    check(not same, "item 3: no look-alike in the real value's sentence", same[:3])
    check(ratio[0] >= 1.8 * ratio[1], "item 3: cross_anchor writes about two real IPv4 per look-alike", ratio)
    from piigen.values import ValueFactory, ValuePool
    vf = ValueFactory(random.Random(4), ValuePool(state_path=None))
    one = [vf.ipv4_one_digit() for _ in range(400)]
    check(all(value_valid("IPV4_ADDRESS", v)[0] and not is_blocked(v) for v in one)
          and all(sum(len(p) == 1 for p in v.split(".")) >= 2 for v in one) and len(set(one)) > 300,
          "item 2: one-digit-octet IPv4 are valid, varied, never a blocked textbook address")

    # -- item 5: licence/ID lines -------------------------------------------------
    lid = [r for r in _family_records("contrast", 700, seed=31) if r["_spec"].get("sub") == "licence_id"]
    bad, ways = [], collections.Counter()
    for r in lid:
        for e in r["entities"]:
            if e["label"] not in ("AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER"):
                continue
            digits = len(re.sub(r"\D", "", e["text"]))
            if (e["label"] == "AZ_ID_CARD_NUMBER") != (digits == 7):
                bad.append(e["text"])
            line = r["text"][r["text"].rfind("\n", 0, e["start"]) + 1:e["start"]]
            for lab, fields in V4.LICENCE_ID_DISAGREE_FIELDS.items():
                if any(line == f + ": " for f in fields):
                    ways[lab] += 1
                    if e["label"] != lab:
                        bad.append(("disagree", line, e["text"]))
    check(lid and not bad, "item 5: the shape decides the label, whatever the field says (D-34d)", bad[:3])
    check(min(ways.values(), default=0) >= 0.3 * len(lid), "item 5: context-disagrees lines both ways", dict(ways))

    # -- items 1(b, c), 6, 9 --------------------------------------------------------
    nc = _family_records("net_context", 200)
    check(len(nc) >= 190 and not _gates_ok(nc) and all(
        any(e["label"] in ("IPV6_ADDRESS", "IPV4_ADDRESS", "MAC_ADDRESS") for e in r["entities"])
        and any(x["kind"] in V4.NET_CODE_KINDS for x in r["_decoys"]) for r in nc),
          "item 1: net_context documents hold a real network value and an unlabelled code", len(nc))
    check(not clean_changes(nc), "v4_clean changes nothing in net_context documents", clean_changes(nc)[:3])
    po = _family_records("postal", 300, seed=33)
    after = sum(1 for r in po for e in r["entities"] if e["label"] == "ZIPCODE"
                and re.search(r"(ZIP|ZIP kodu|poçt kodu) $", r["text"][max(0, e["start"] - 12):e["start"]]))
    check(after >= 40, "item 6: real ZIPs right after ZIP / poçt kodu", after)
    st = _family_records("structured", 900, seed=35)
    synth = [e["text"] for r in st for e in r["entities"] if e["label"] == "EMAIL"
             and re.match(r"(test\.user|demo\.user|qa\.tester|sample\.account|trial\.user|user\.test|dev\.tester)\d", e["text"])]
    check(len(synth) >= 10 and all(value_valid("EMAIL", v)[0] for v in synth),
          "item 9: synthetic test addresses labelled in table/JSON/log rows", len(synth))

    # -- D-52c: sequential dummy times ---------------------------------------------
    k = ALL_DECOY_KINDS["policy_sequential_time"]
    rng = random.Random(6)
    vals = {make_decoy(k, rng) for _ in range(300)}
    check(k.policy and "12:34:56" in policy_allowlist() and vals <= set(SEQUENTIAL_TIMES),
          "D-52c: the dummy times are a policy look-alike; 12:34:56 is on the D-2 allowlist", vals)
    check(all(blocklist.is_blocked(v) for v in SEQUENTIAL_TIMES), "D-52c: a real TIME is never a dummy time")

    # -- D-52d: protected quotas and kind weights ----------------------------------
    q = copy.deepcopy(Q.load())
    q["families"]["contrast"] -= 0.01
    q["families"]["prose"] += 0.01
    try:
        Q.check(q)
        refused = False
    except ValueError as e:
        refused = "protected quota contrast" in str(e)
    check(refused, "D-52d: quotas.json can't shrink a protected contrast sub-family")
    b = B.TargetedBuilder(seed=3, n_docs=1000)
    picks = collections.Counter(b._least_used_kind([b.kinds["zip_wrong_length"], b.kinds["zip_two_digits"]]).kind
                                for _ in range(1))
    for _ in range(900):
        kk = b._least_used_kind([b.kinds["zip_wrong_length"], b.kinds["zip_two_digits"]])
        b.kind_counts[kk.kind] += 1
        picks[kk.kind] += 1
    w = Q.load()["kind_weights"]["zip_wrong_length"]
    check(abs(picks["zip_wrong_length"] / max(1, picks["zip_two_digits"]) - w) < 0.5,
          "D-52d: the least-used choice follows the kind weights", dict(picks))
    bsm = (Path(__file__).resolve().parents[2] / "build_sprint_mix.py").read_text(encoding="utf-8")
    check('"--targeted-n", type=int, default=37000' in bsm,
          "D-57: build_sprint_mix builds 37,000 targeted documents (v4.2 30,000, D-52d 28,000)")


def test_v42_fix_list() -> None:
    """v4.2 fix list (19 Oct; v41_shadow_shapes.md). Must: near-miss
    C4 look-alikes and A5's three groups, in their label slots. Should:
    seconds-times in ranges, IBAN boundaries, line-start names, 19-digit
    codes, street vs city."""
    import json as _json
    import random as _random
    from piigen import checksums as CK
    from piigen import negatives as N
    from piigen.locales import az as AZL
    from piigen.targeted import frames_v4 as V4
    from piigen.values import ValueFactory, ValuePool

    rng = _random.Random(5)
    kinds = {k.kind: k for k in N.ALL_DECOY_KINDS.values()}

    def vals(name, n=2000):
        return [kinds[name].make(rng) for _ in range(n)]

    def date_parts(v):
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v) or re.fullmatch(r"(\d{2})[./-](\d{2})[./-](\d{4})", v)
        a, b, c = (int(x) for x in m.groups())
        return (a, b, c) if a > 31 else (c, b, a)            # (year, month, day)

    # -- Must: the near misses and the A5 shapes, never valid ---------------------
    v = vals("time_hour_near")
    check(all(re.fullmatch(r"2[4-9]:[0-5]\d", x) and x != "24:00" for x in v), "hours 24-29, never 24:00")
    check(all(re.fullmatch(r"([01]\d|2[0-3]):6\d", x) for x in vals("time_minute_near")), "minutes 60-69")
    feb = [date_parts(x) for x in vals("date_feb_invalid")]
    check(all(m == 2 and (d in (30, 31) or (d == 29 and not N._is_leap(y))) for y, m, d in feb),
          "29-31 February, 29 only in a non-leap year")
    mon = vals("date_month_near")
    check(all(13 <= date_parts(x)[1] <= 19 for x in mon), "months 13-19")
    check(all(x[:4].isdigit() or date_parts(x)[2] >= 13 for x in mon),
          "day-first near-month dates have a day of 13+, so month-first is no date either")
    check({len(x) for x in mon} >= {10} and any("-" in x and x[:4].isdigit() for x in mon), "ISO and day-first forms")
    ib = vals("iban_short_account")
    check(all(re.fullmatch(r"AZ\d{2}[A-Z]{4}\d{10,19}", x) and not CK.iban_valid(x) for x in ib),
          "IBAN-shaped codes of 18-27 characters, never a valid IBAN")
    cc = vals("iban_country_code", 500)
    check(set(cc) <= {"AZ", "TR", "GE"} and cc.count("AZ") > 300 and not any(CK.iban_valid(x) for x in cc),
          "D-55b: a bare country code (`AZ`) after country-code words, never an IBAN")
    lic = vals("licence_three_letters")
    check(all(re.fullmatch(r"[A-Z]{3}\d{6}", x) and not value_valid("AZ_DRIVER_LICENSE_NUMBER", x)[0]
              and not value_valid("AZ_PASSPORT_NUMBER", x)[0] and not value_valid("AZ_ID_CARD_NUMBER", x)[0]
              for x in lic), "three letters + 6 digits: no licence, passport or ID card")
    fin = vals("fin_dummy_pattern", 500)
    check(set(fin) <= set(N.FIN_DUMMIES) and not any(value_valid("AZ_FIN", x)[0] for x in fin)
          and not kinds["fin_dummy_pattern"].policy, "FIN dummies: a fixed list (D-34b), none a valid FIN")
    d19 = vals("iccid_wrong_prefix") + vals("reference_19_digits")
    check(all(len(x) == 19 and x.isdigit() and not x.startswith("89") and not CK.iccid_valid(x)
              and not CK.credit_card_valid(x) and not CK.card_brand_ok(x) for x in d19),
          "19 digits without `89`: no ICCID, no card prefix (the shape decides, D-51d)")

    # -- the new slots ---------------------------------------------------------------
    slot = _family_records("slot_invalid", 700)
    labels = collections.Counter(r["_spec"]["slot_label"] for r in slot)
    check(all(labels[x] for x in ("IBAN", "AZ_DRIVER_LICENSE_NUMBER", "ICCID")) and not labels["IPV4_ADDRESS"],
          "IBAN, licence and ICCID slots written; no IPv4 slot (native review B, D-52b)", dict(labels))
    cross = _family_records("cross_anchor", 600)
    ip3 = [(r, x) for r in cross for x in r["_decoys"] if x["kind"] == "ipv4_three_octets"]

    def sent(r, s):
        return re.split(r"[.!?] |\n", r["text"][:s])[-1]
    check(ip3 and all(not any(e["label"] == "IPV4_ADDRESS" and sent(r, e["start"]) == sent(r, x["start"])
                              for e in r["entities"]) for r, x in ip3),
          "a 3-part IPv4 look-alike never shares a sentence with a real IPv4 (D-52b)", len(ip3))
    near = collections.Counter(r["_spec"]["slot_kind"] for r in slot)
    check(all(near[k] for k in ("time_hour_near", "time_minute_near", "date_feb_invalid", "date_month_near",
                                "iban_short_account", "licence_three_letters", "iccid_wrong_prefix")),
          "the near misses and A5 shapes sit in their label slots", dict(near))

    # -- Should 1: seconds-times in ranges ---------------------------------------------
    expect = {"14:05:22": ("-dən", "-yə"), "10:00:00": ("-dan", "-a"), "15:30:00": ("-dan", "-a"),
              "16:00:00": ("-dan", "-ya"), "09:15:00": ("-dən", "-ə"), "20:00:00": ("-dən", "-yə"),
              "13:00:00": ("-dən", "-ə"), "12:00:06": ("-dan", "-ya")}
    check(all((B.time_case_suffix(t, "abl"), B.time_case_suffix(t, "dat")) == e for t, e in expect.items()),
          "case endings follow the last spoken number",
          {t: (B.time_case_suffix(t, "abl"), B.time_case_suffix(t, "dat")) for t in expect})
    ts = _family_records("time_seconds", 500)
    sfx = [(r, e) for r in ts for e in r["entities"] if e["label"] == "TIME"
           and re.match(r"-d[aə]n ", r["text"][e["end"]:e["end"] + 5])]
    check(len(sfx) >= 20 and all(re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", r["text"][e["start"]:e["end"]])
                                 for r, e in sfx), "ranges with case endings, the ending outside the span",
          len(sfx))
    dek = [(r, e) for r in ts for e in r["entities"] if e["label"] == "TIME"
           and r["text"][e["end"]:e["end"] + 4] == "-dək"]
    check(len(dek) >= 5, "native review A: `-dək` range ends reach the data (resolver)", len(dek))
    agenda = [r for r in ts if any(i in r["text"] for i in V4.TIME_AGENDA_INTROS)]
    check(agenda and all(any(e["label"] == "TIME" and r["text"][e["start"] - 1] == "\n" for e in r["entities"])
                         for r in agenda), "agenda lines open with a labelled range", len(agenda))
    bad_agenda = []
    for r in agenda:
        t = r["text"]
        start = t.index(next(i for i in V4.TIME_AGENDA_INTROS if i in t))
        lines = []
        for ln in t[start:].split("\n")[1:]:
            if not re.match(r"\d{2}:\d{2}\s?[-–]", ln):
                break
            lines.append(ln)
        rng_ = [re.match(r"(\d{2}:\d{2})\s?[-–]\s?(\d{2}:\d{2})\W*\s*(.+)$", ln) for ln in lines]
        ok_ = (all(rng_) and all(rng_[i].group(2) == rng_[i + 1].group(1) for i in range(len(rng_) - 1))
               and rng_[0].group(3) in V4.TIME_AGENDA_FIRST and rng_[-1].group(3) == V4.TIME_AGENDA_LAST
               and all("12:00" <= m.group(1) < "14:00" for m in rng_ if m.group(3) == "Nahar fasiləsi"))
        if not ok_:
            bad_agenda.append(lines)
    check(agenda and not bad_agenda,
          "native review C: agendas run forward (each range starts where the last ended), hh:mm, "
          "from registration or the opening to `Yekun söz`, lunch starting 12:00-13:59", bad_agenda[:2])

    # -- Should 2: IBAN boundaries ------------------------------------------------------
    vf = ValueFactory(_random.Random(9), ValuePool(max_share=1.0, state_path=None))
    irr = [vf.iban_az_irregular() for _ in range(300)]
    clean = r"[A-Z0-9]{4}( [A-Z0-9]{4})*( [A-Z0-9]{1,4})?"
    check(all(CK.iban_valid(x) and (" " in x or "-" in x) and not re.fullmatch(clean, x) for x in irr),
          "typed IBAN groupings: valid, never clean fours")
    edges = _family_records("edges", 400)
    ib_edge = [(r, e) for r in edges for e in r["entities"] if e["label"] == "IBAN"]
    check(ib_edge and all(CK.iban_valid(r["text"][e["start"]:e["end"]]) and
                          not r["text"][e["start"]:e["end"]].endswith(("-dür", "-dir", "-dur", "-dır", ")"))
                          for r, e in ib_edge), "IBAN edges: the copula and marks stay outside the span",
          len(ib_edge))
    check(not any("-" in r["text"][e["start"]:e["end"]] and r["text"][e["end"]:e["end"] + 2] == "-d"
                  for r, e in ib_edge), "native review G: no ending after a dashed IBAN")
    check(not any(": {v}" in a for k in ("iban_country_code", "reference_19_digits") for a in kinds[k].anchors),
          "native review E: no colon before the value inside a running sentence")

    # -- Should 3: line-start words in PII-free documents ------------------------------
    pf = _family_records("pii_free", 400)
    ls = [r for r in pf if any(x["kind"] == "line_start_control" for x in r["_decoys"])]
    check(ls and all(not r["entities"] for r in ls), "PII-free documents with role/heading lines, no names",
          len(ls))

    # -- Should 5: streets named after a town ------------------------------------------
    st = [vf.street_town() for _ in range(300)]
    check(all(any(x.startswith(c + " ") for c in AZL.CITIES) and value_valid("STREET", x)[0] for x in st),
          "streets named after a town")
    st = [vf.street_town() for _ in range(3000)]
    words = collections.Counter(x.rsplit(" ", 1)[1] for x in st)
    check(not any(x.startswith("Qobustan Mərəzə") for x in st)
          and all(x.endswith(" küçəsi") for x in st if x.count(" ") > 1)
          and words["küçəsi"] > 2 * words["döngəsi"],
          "native review F: mostly küçəsi, a two-word town only with küçəsi, no Qobustan Mərəzə", dict(words))

    # -- protected floors and the build size -------------------------------------------
    q = _json.loads((Path(B.__file__).parent / "quotas.json").read_text(encoding="utf-8"))
    prot = q["protected"]["kinds"]
    check(all(k in prot for k in ("time_hour_near", "time_minute_near", "date_feb_invalid", "date_month_near",
                                  "iban_short_account", "licence_three_letters", "ipv4_three_octets")),
          "the new kinds have protected floors")
    check(prot["date_impossible_day"] == 1390 and prot["zip_wrong_length"] == 559 and prot["cvv_5_digits"] == 304,
          "the D-52d floors are unchanged")


def test_v42_d56a() -> None:
    """D-56a (v4 -> v4.1 note): (1) IPs at the end of a line or
    sentence without a final period; (2) the IPv4 look-alike swing (an octet
    over 255 beside one-digit octets, `1.2.3.4`-type dummies); (3) ID cards
    AA + 7 digits after short ID words, beside licences, 1 : 1."""
    import random as _random
    from piigen import negatives as N
    from piigen.blocklist import is_blocked
    from piigen.negatives import policy_allowlist
    from piigen.targeted import frames_v4 as V4

    # -- (1) IPs that end a line -----------------------------------------------------
    net = _family_records("net_context", 500)
    layouts = collections.Counter(x for r in net for x in r["_spec"].get("net_layouts", []))
    ends = collections.Counter(x for r in net for x in r["_spec"].get("ip_ends", []))
    check(layouts["chat"] and layouts["log"] and layouts["sentence"] and ends["semicolon"] and ends["bare"],
          "net_context: chat and log lines, and sentences ending with `;` or nothing", (dict(layouts), dict(ends)))
    ip_labels = ("IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS")
    line_end = [(r, e) for r in net for e in r["entities"] if e["label"] in ip_labels
                and (e["end"] == len(r["text"]) or r["text"][e["end"]] in "\n;")]
    check(len(line_end) >= 100, "IPs at a line end or before `;`", len(line_end))
    lead = [r["id"] for r in net + _family_records("cross_anchor", 300) if "\n " in r["text"]]
    check(not lead, "no line starts with a space after a line that ended open", lead[:3])
    # the IP sits mid-sentence (`Server ünvanı X yazılıb;`); the sentence's end changes
    cross = _family_records("cross_anchor", 600)
    open_ip = collections.Counter(x for r in cross for x in r["_spec"].get("ip_ends", []))
    open_txt = sum(1 for r in cross for e in r["entities"] if e["label"] == "IPV4_ADDRESS"
                   and re.match(r"[^.\n]*[^.\n;]?(;|)\n", r["text"][e["end"]:]))
    check(open_ip["semicolon"] and open_ip["bare"] and open_txt >= 5,
          "cross_anchor: real IPv4 sentences that end with `;` or nothing, then a line break",
          (dict(open_ip), open_txt))

    # -- (2) the IPv4 swing --------------------------------------------------------------
    kinds = {k.kind: k for k in N.ALL_DECOY_KINDS.values()}
    rng = _random.Random(4)
    mixed = [N.make_decoy(kinds["ipv4_over_255_mixed"], rng) for _ in range(1000)]
    check(all(not value_valid("IPV4_ADDRESS", x)[0] and any(int(o) > 255 for o in x.split("."))
              and any(len(o) == 1 for o in x.split(".")) for x in mixed),
          "an octet over 255 beside one-digit octets, never a valid IPv4")
    check(sum(int(x.split(".")[0]) > 255 for x in mixed) > 500, "the octet over 255 is mostly the first")
    seq = {N.make_decoy(kinds["policy_sequential_ipv4"], rng) for _ in range(500)}
    check(seq == set(N.SEQUENTIAL_IPV4) and all(value_valid("IPV4_ADDRESS", x)[0] and is_blocked(x) for x in seq)
          and kinds["policy_sequential_ipv4"].policy and "1.2.3.4" in policy_allowlist(),
          "sequential IPv4 dummies: a policy kind, valid, never minted as real, `1.2.3.4` on the D-2 list")
    # D-56g: in decoy_pair too, an IPv4 look-alike never shares a sentence frame with a real IPv4
    dp = [r for r in _family_records("decoy_pair", 1500, seed=31)
          if any(x["resembles"] == "IPV4_ADDRESS" for x in r["_decoys"])]

    def frame_of(r, s):
        return re.split(r"[.!?] |\n", r["text"][:s])[-1]
    shared = [r["id"] for r in dp for x in r["_decoys"] if x["resembles"] == "IPV4_ADDRESS"
              for e in r["entities"] if e["label"] == "IPV4_ADDRESS"
              and frame_of(r, e["start"]) == frame_of(r, x["start"])]
    check(dp and not shared, "D-56g: decoy_pair IPv4 look-alikes in a sentence of their own", (len(dp), shared[:3]))
    twins = [(x, B.TargetedBuilder(seed=3, n_docs=10)._ipv4_twin(x, "ipv4_over_255_mixed")) for x in mixed[:200]]
    check(all(t is None or value_valid("IPV4_ADDRESS", t)[0] for _, t in twins),
          "the valid twin of an over-255 look-alike is a valid IPv4")

    # -- (3) short ID words ----------------------------------------------------------------
    con = [r for r in _family_records("contrast", 900) if "short:both" in r["_spec"].get("licence_id_lines", [])]
    ok, aa, n = True, 0, 0
    for r in con:
        t = r["text"]
        short = [e for e in r["entities"] if e["label"] in ("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER")
                 and re.search(r"\bID( nömrə\w*)?:? $", t[max(0, e["start"] - 25):e["start"]])]
        labs = collections.Counter(e["label"] for e in short)
        ok &= labs["AZ_ID_CARD_NUMBER"] >= 1 and labs["AZ_DRIVER_LICENSE_NUMBER"] >= 1
        for e in short:
            v = t[e["start"]:e["end"]]
            ok &= len(v) == (9 if e["label"] == "AZ_ID_CARD_NUMBER" else 8)
            aa += v.startswith("AA")
            n += 1
    check(con and ok, "short ID words: an ID card (+7 digits) and a licence (+6) after the same words",
          len(con))
    check(n and aa / n >= 0.5, "short ID words: mostly the AA prefix (the benchmark's misses)", (aa, n))


def test_v42_final() -> None:
    """D-57 (v4.2 final fix list, 20 Oct): Must M1-M7 and Should
    S1-S7, on the generators and on documents of every family they touch."""
    import random as _random
    from piigen import checksums as CK
    from piigen import negatives as N
    from piigen.anchors import has_anchor
    from piigen.targeted import frames_v42 as V42

    rng = _random.Random(57)
    kinds = {k.kind: k for k in N.ALL_DECOY_KINDS.values()}

    def vals(name, n=3000):
        return [kinds[name].make(rng) for _ in range(n)]

    # -- generators --------------------------------------------------------------------------
    check("24:00" not in vals("time_bad_hour", 20000), "S6: `24:00` is never a look-alike")
    check(CK.time_valid("24:00") and CK.time_valid("24:00:00") and not CK.time_valid("24:01")
          and not CK.time_valid("24:00:01") and not CK.time_valid("25:00"), "S6: `24:00` is a valid time, 24:01 not")
    fins = vals("fin_with_hyphen")
    two_four = sum(bool(re.fullmatch(r"[A-Z0-9]{2}-[A-Z0-9]{4}|[A-Z0-9]{4}-[A-Z0-9]{2}", v)) for v in fins)
    check(0.42 <= two_four / len(fins) <= 0.58, "M3: about half the dashed FINs dashed after the 2nd or 4th character",
          two_four / len(fins))
    check(not any(value_valid("AZ_FIN", v)[0] for v in fins), "M3: dashed FIN look-alikes are no FIN")
    three = vals("ipv4_three_octets")
    one = sum(bool(re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d", v)) for v in three)
    check(0.35 <= one / len(three) <= 0.5, "M7: ~40% of 3-part IPv4 look-alikes end in one digit", one / len(three))
    short = vals("iban_short_account")
    eighteen = sum(len(v) == 18 for v in short)
    check(0.25 <= eighteen / len(short) <= 0.36 and all(len(v) < 28 for v in short),
          "M1: ~30% of short IBAN-like codes have 18 characters", eighteen / len(short))
    cvv = vals("cvv_1_2_digits")
    check(sum(len(v) == 2 for v in cvv) / len(cvv) >= 0.75, "M5: CVV look-alikes of 1-2 digits are mostly 2 digits")
    ip6 = vals("ipv6_compressed_bad")
    check(all("::" in v and not value_valid("IPV6_ADDRESS", v)[0] for v in ip6),
          "M6: every IPv6 look-alike has `::` and is no IPv6", [v for v in ip6 if value_valid("IPV6_ADDRESS", v)[0]][:3])
    styles = {"5hex": any(re.search(r"(^|:)[0-9a-f]{5}(:|$)", v) for v in ip6),
              "non_hex": any(re.search(r"[g-z]", v) for v in ip6),
              "9 groups": any(len([g for g in v.split(":") if g]) == 9 for v in ip6),
              "stray colon": any(v.startswith(":") and not v.startswith("::") or v.endswith(":") and not v.endswith("::")
                                 for v in ip6)}
    check(all(styles.values()), "M6: the four IPv6 look-alike shapes", styles)
    macs = vals("mac_letters_only")
    check(all(re.fullmatch(r"[A-Z]{2}([:-][A-Z]{2}){5}", v) and not value_valid("MAC_ADDRESS", v)[0] for v in macs),
          "M7: letters-only MAC look-alikes, none a MAC")
    voen9 = vals("voen_nine_digits")
    check(all(re.fullmatch(r"[1-9]\d{8}", v) and not value_valid("AZ_VOEN", v)[0] for v in voen9),
          "M7: 9-digit VÖEN look-alikes")
    towns = {t.casefold() for t in ValueFactory(_random.Random(1), ValuePool(state_path=None)).loc("az").cities}
    brands = vals("policy_city_in_brand", 500)
    check(all(any(v.casefold().startswith(t + " ") for t in towns) for v in brands),
          "S3: brand names start with a town word", [v for v in brands if not any(v.casefold().startswith(t + " ")
                                                                                   for t in towns)][:3])
    vf = ValueFactory(_random.Random(3), ValuePool(state_path=None))
    dates = [vf.date_styled("az", s, day31_rate=0.14) for s in ("dmy", "iso") * 1500]
    check(all(CK.date_valid(d) for d in dates), "S6: every minted date is a calendar date")
    d31 = sum(bool(re.match(r"31\.", d) or d.endswith("-31")) for d in dates) / len(dates)
    check(0.1 <= d31 <= 0.2, "S6: real dates on the 31st at the quota's rate", d31)

    # -- the sentences ------------------------------------------------------------------------
    native = V42.native_check_list()
    check(len(native) > 200, "every new sentence is in the native check list", len(native))
    digits = [s for _p, s in native
              if re.search(r"\d", re.sub(r"IPv6|CVV2|A4|mAh|GB|\s+\[\d+-\d+\]$", "", s))]   # [18-80]: an age range
    check(not digits, "the new sentences carry no digits", digits[:3])
    judged = [s for _p, s in native if re.search(r"\b(səhv|yanlış|etibarsız|düzgün deyil)", s, re.I)]
    check(not judged, "no sentence calls a look-alike wrong", judged[:3])

    # -- decoy_pair: ages (S1), noun FIN and dates (M3, M4), buildings (S4), brands (S3) -------
    pairs = _family_records("decoy_pair", 2500)
    check(not _gates_ok(pairs), "decoy_pair documents pass every gate", _gates_ok(pairs)[:3])
    ages = [r for r in pairs if r["_spec"].get("group") == "age"]
    check(len(ages) >= 60, "S1: age pairs written", len(ages))
    real = [(r, e) for r in ages for e in r["entities"] if e["label"] == "AGE"]
    fake = [(r, x) for r in ages for x in r["_decoys"] if x["kind"] == "age_shaped_number"]
    check(all(re.fullmatch(r"\d{2}", e["text"]) and has_anchor("AGE", r["text"], e["start"], e["end"]) for r, e in real),
          "S1: real ages are 2 digits with an age word within reach")
    no_yas = sum(not re.match(r"\s*-?ya[şs]", r["text"][e["end"]:e["end"] + 6]) for r, e in real)
    check(no_yas >= 0.85 * len(real), "S1: mostly no `yaş` right after the age", (no_yas, len(real)))
    check(len(fake) == len(ages) and all(re.fullmatch(r"\d{2}", r["text"][x["start"]:x["end"]]) for r, x in fake)
          and all(any(e["label"] == "AGE" for e in r["entities"]) for r in ages),
          "S1: each age pair has an age-shaped look-alike beside a real age")
    nouns = [r for r in pairs if r["_spec"].get("group") == "noun"]
    fin = [(r, x) for r in nouns for x in r["_decoys"] if x["resembles"] == "AZ_FIN"]
    check(fin and all(re.match(r"\s+FİN", r["text"][x["end"]:x["end"] + 6]) for r, x in fin)
          and all(any(e["label"] == "AZ_FIN" for e in r["entities"]) for r, _x in fin),
          "M3: FIN look-alikes right before `FİN`, beside a real FIN there", len(fin))
    nd = [r["text"][x["start"]:x["end"]] for r in nouns for x in r["_decoys"] if x["resembles"] == "DATE"]

    def near(v):
        m = re.fullmatch(r"(\d{2})[./-](\d{2})[./-](\d{4})", v) or re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
        if not m:
            return False
        d, mo = (int(m[3]), int(m[2])) if len(m[1]) == 4 else (int(m[1]), int(m[2]))
        return (mo == 2 and d in (30, 31)) or 13 <= mo <= 19
    check(nd and all(near(v) for v in nd), "M4: noun date look-alikes are 30-31 February or month 13-19",
          [v for v in nd if not near(v)][:3])
    blds = [r for r in pairs if r["_spec"].get("group") == "building"]
    styles = collections.Counter(r["_spec"].get("building_style") for r in blds)
    check(all(styles[s] for s in ("street", "ev", "bina")) and any(r["_spec"].get("building_lines") for r in blds),
          "S4: building numbers after a street name, `ev`, `bina`, and `Bina:` lines", dict(styles))
    for r in blds:
        if r["_spec"].get("building_style") == "street":
            st = next(e for e in r["entities"] if e["label"] == "STREET")
            b = next(e for e in r["entities"] if e["label"] == "BUILDINGNUM")
            # casing noise may re-case or fold the street (`KUcESI`): compare folded
            check(b["start"] == st["end"] + 1
                  and B.fold_diacritics(st["text"]).lower().endswith(("kucesi", "prospekti", "dongesi")),
                  "S4: the number right after the street's type word", r["text"])
    brand = [r for r in pairs if r["_spec"].get("kind") == "policy_city_in_brand"]
    check(len(brand) >= 10, "S3: brand pairs written", len(brand))
    for r in brand:
        x = next(x for x in r["_decoys"] if x["kind"] == "policy_city_in_brand")
        c = [e for e in r["entities"] if e["label"] == "CITY"]
        check(r["text"][x["start"] - 1] in "«\"" and c and all(r["text"][e["start"] - 1] in "(\"«" for e in c),
              "S3: the brand in quotes, the real town right after an opening bracket or quote", r["text"])

    # -- PII-free near misses (M1) and business-like PII-free documents (M2, item 5) ----------
    pf = _family_records("pii_free", 600) + _family_records("pii_free_business", 600)
    check(not _gates_ok(pf), "PII-free documents pass every gate", _gates_ok(pf)[:3])
    check(all(not r["entities"] for r in pf), "PII-free documents hold no real value")
    items = collections.Counter(i for r in pf for i in r["_spec"].get("pf_near", ()))
    check(set(items) == set(B.TargetedBuilder.PF_NEAR_KINDS), "M1: every near-miss item in PII-free documents", dict(items))
    biz = [r for r in pf if r["_spec"]["family"] == "pii_free_business"]
    check(set(collections.Counter(r["_spec"]["biz"] for r in biz)) == set(V42.BIZ_TITLES),
          "M2: every business document kind")
    places = [r["text"][x["start"]:x["end"]] for r in biz for x in r["_decoys"] if x["kind"] == "place_word_topic"]
    check(len(places) >= 50 and not any(w.casefold() in towns for p in places for w in re.split(r"[\s\-–]+", p)),
          "item 5: place words declared, none a town", len(places))
    check(sum(len(r["text"]) for r in biz) / len(biz) > 300, "M2: business documents are long",
          sum(len(r["text"]) for r in biz) / len(biz))

    # -- ALL-CAPS forms (S2) ---------------------------------------------------------------
    caps = [r for r in _family_records("structured", 1500) if r["_spec"].get("format") == "caps_form"]
    check(len(caps) >= 20 and not _gates_ok(caps), "S2: ALL-CAPS forms written, every gate passed", len(caps))
    names = [e["text"] for r in caps for e in r["entities"] if e["label"] in ("CITY", "GIVENNAME", "SURNAME")]
    check(names and all(n == n.upper() and "i" not in n for n in names), "S2: every name and city in capitals",
          [n for n in names if n != n.upper()][:3])
    heads = [r["text"][x["start"]:x["end"]] for r in caps for x in r["_decoys"]]
    check(heads and all(h in V42.CAPS_HEADINGS for h in heads), "S2: the heading controls are unlabelled capitals")

    # -- form extras (M5, M7, S5), ipv6_mac extras (M6, M7), recall (S5, S6) ------------------
    forms = _family_records("form", 800)
    check(not _gates_ok(forms), "form documents pass every gate", _gates_ok(forms)[:3])
    # (per-25k quotas: a forms-only build writes them at the whole build's rate)
    extra5 = [r for r in forms if "cvv5" in r["_spec"].get("form_extra", ())]
    cvv5 = [r for r in extra5 if any(x["kind"] == "cvv_5_digits" and r["text"][:x["start"]].endswith("CVV kodu: ")
                                     and (x["end"] == len(r["text"]) or r["text"][x["end"]] == "\n")
                                     for x in r["_decoys"])]
    check(extra5 and len(cvv5) == len(extra5), "M5: 5-digit CVVs at a line end after `CVV kodu:`",
          (len(cvv5), len(extra5)))
    for r in forms:
        for item in r["_spec"].get("form_extra", ()):
            lab = B.TargetedBuilder.FORM_EXTRA[item][0]
            check(any(e["label"] == lab for e in r["entities"]), f"form extra {item}: a real {lab} in the form", r["text"])
    con = [r for r in _family_records("contrast", 900) if r["_spec"].get("ipv6_extra")]
    check(con and not _gates_ok(con), "M6: ipv6_mac extras written, every gate passed", len(con))
    extra = collections.Counter(i for r in con for i in r["_spec"]["ipv6_extra"])
    check(all(extra[k] for k in ("ipv6_bad", "ipv6_real", "mac_letters")), "M6/M7: every ipv6_mac extra", dict(extra))
    rec = _family_records("recall", 400)
    check(not _gates_ok(rec), "recall documents pass every gate", _gates_ok(rec)[:3])
    times = [e["text"] for r in rec for e in r["entities"] if e["label"] == "TIME"]
    check("24:00" in times and any(t.startswith("23:5") for t in times) and any(t.startswith("00:0") for t in times),
          "S6: `24:00`, 23:5x and 00:0x written as real times")
    feb = [e["text"] for r in rec for e in r["entities"] if e["label"] == "DATE"]
    check(feb and all("29" in d and int(re.search(r"\d{4}", d)[0]) % 4 == 0 for d in feb),
          "S6: leap years' 29 February", feb[:3])
    q = Q.load()
    check(q["protected"]["contrast_subs"] == {"ipv6_mac": 600, "licence_id": 600}, "S7: the contrast floors are 600")

    # -- The native review of the D-57 sentences, findings A-H ------------------------
    texts = [s for _p, s in native]
    check(not any("ətəklərindən" in s or "anbarından («" in s or "(«" in s or "yəni o, indi" in s
                  or "ünvanına çatdırıb" in s or "ölkələrini birləşdirir" in s for s in texts),
          "A, B, C, F, G: the reviewed sentences are rewritten")
    ev = [(r, e) for r in blds for e in r["entities"] if e["label"] == "BUILDINGNUM"
          and r["text"][max(0, e["start"] - 3):e["start"]] == "ev "]
    def ev_ok(r, e):
        return bool(re.search(r"(Kuryer sifarişi|Müştəri) ev " + re.escape(e["text"]) + r", mərtəbə ", r["text"]))
    check(ev and all(ev_ok(r, e) for r, e in ev), "D: `ev` only in the courier and customer frames, beside a floor",
          [r["text"] for r, e in ev if not ev_ok(r, e)][:3])
    check(not any(re.search(r"daxilində keçiriləcək|hissəsinə köçürülüb", r["text"]) for r in blds),
          "D: no `… daxilində keçiriləcək` / `… hissəsinə köçürülüb` with a building")
    fam = [e["text"] for r in rec for e in r["entities"] if e["label"] == "SURNAME"
           and r["text"][e["end"]:e["end"] + 7] == " ailəsi"]
    check(not any(B.fold_diacritics(n).lower().endswith(("ova", "eva", "yeva", "ina", "skaya")) for n in fam),
          "E: a family named by the man's form", [n for n in fam if n.lower().endswith(("ova", "eva", "ina"))][:3])
    for r in caps:
        t = r["text"]
        check(not (("SOYADI:" in t and "\nAD:" in t) or ("SOYAD:" in t and "ADI:" in t.replace("ATASININ ADI:", ""))),
              "H: one field style per ALL-CAPS form", t)
        towns_f = re.findall(r"^(ŞƏHƏR|DOĞULDUĞU ŞƏHƏR|YAŞADIĞI ŞƏHƏR|QEYDİYYAT YERİ):", t, re.M)
        check(not ("ŞƏHƏR" in towns_f and len(towns_f) > 1), "H: a bare ŞƏHƏR only as the one town field", t)
        m = re.search(r"^(.+) ŞƏHƏRİ$", t, re.M)
        check(not m or m[1] in {B.az_upper(c) for c in V42.CAPS_HEADER_CITIES}, "H: the ŞƏHƏRİ header names a city", t)
    geo = [r for r in biz if r["_spec"]["biz"] == "geography"]
    for r in geo:
        for reg, members in V42.GEO_REGION_MEMBERS.items():
            for sent in re.split(r"(?<=\.) ", r["text"]):
                check(not (reg in sent and any(c in sent for c in members)), "G: no country inside its own region", sent)


def test_extra_batch_buildingnum() -> None:
    """X-BN (the extra batch's BUILDINGNUM top-up, frames_v43): the preset builds the shapes v4.2 lost, each
    beside its unlabelled look-alike, and without the preset nothing changes."""
    from piigen.targeted import frames_v43 as V43
    preset = Path(B.__file__).with_name("quotas_x_buildingnum.json")
    q = Q.load(preset)
    check(q["building_v43"]["rate"] > 0 and Q._weights(q["families"])["decoy_pair"] == 1.0,
          "X-BN: the preset loads, every document a building pair")
    check(not Q.load().get("building_v43"), "X-BN: quotas.json alone has no building_v43 (v4.2 untouched)")
    recs = B.TargetedBuilder(seed=31, n_docs=600, quotas=q).build()
    check(len(recs) == 600, "X-BN: 600 documents built", len(recs))
    check(not _gates_ok(recs), "X-BN: every document passes every gate", _gates_ok(recs)[:3])
    styles = collections.Counter(r["_spec"].get("building_style") for r in recs)
    check(all(styles["v43_" + s] >= 60 for s in ("form_lines", "number_first", "numero", "count", "building_count")),
          "X-BN: each new shape written", dict(styles))
    for r in recs:
        st, t = r["_spec"].get("building_style", ""), r["text"]
        if not st.startswith("v43_"):
            continue
        b = [e for e in r["entities"] if e["label"] == "BUILDINGNUM"]
        s = [e for e in r["entities"] if e["label"] == "STREET"]
        check(len(b) == 1 and len(s) == 1 and all(has_anchor_(r, e) for e in b),
              "X-BN: one building number, anchored, and its street", t)
        bb, ss = b[0], s[0]
        if r["_spec"].get("building_doc_number"):
            # the contrast is a document `№` in the same sentence, unlabelled
            check(re.search(r"№\d{3,5} ", t) and not any(e["text"].isdigit() and len(e["text"]) >= 3 and
                                                         t[e["start"] - 1] == "№" and e["label"] != "BUILDINGNUM"
                                                         for e in r["entities"]),
                  "X-BN: a document `№` beside the address `№`, unlabelled", t)
            continue
        check(any(x["kind"] in ("room_number", "floor_number", "office_number", "building_count")
                  and x["resembles"] == "BUILDINGNUM" for x in r["_decoys"]),
              "X-BN: a building look-alike in the same document", t)
        if st == "v43_number_first":
            check(bb["end"] < ss["start"], "X-BN: number_first puts the number before the street", t)
        elif st == "v43_numero":
            check("№" in t[max(0, bb["start"] - 2):bb["start"]], "X-BN: numero writes `№` right before the number", t)
        elif st == "v43_form_lines":
            key = t[t.rfind("\n", 0, bb["start"]) + 1:bb["start"]]
            check(key.rstrip(": ") in V43.FORM_KEYS_EV + V43.FORM_KEYS_BINA and ss["end"] < bb["start"],
                  "X-BN: form_lines puts the building on its own `Ev:` / `Bina:` line under the street", t)
        elif st == "v43_building_count":
            x = next(x for x in r["_decoys"] if x["kind"] == "building_count")
            lo, hi = V43.BUILDING_COUNT_RANGE
            check(lo <= int(t[x["start"]:x["end"]]) <= hi and re.match(r" (\w+ )?(ev|bina)", t[x["end"]:]),
                  "X-BN: a house / building count right before `ev` / `bina`, unlabelled (#136)", t)
        elif st == "v43_count":
            x = next(x for x in r["_decoys"] if x["kind"] in V43.COUNT_RANGE)
            lo, hi = V43.COUNT_RANGE[x["kind"]]
            check(lo <= int(t[x["start"]:x["end"]]) <= hi, "X-BN: the count look-alike is in its range", t)
        # The D-57 review, D: `ev` (a dwelling) never in a sentence beside a room or an office
        if st in ("v43_number_first", "v43_numero") and re.search(r"\bev №?$", t[:bb["start"]]):
            check(any(x["kind"] == "floor_number" for x in r["_decoys"]), "X-BN: `ev` only beside a floor", t)
    ends = [r for r in recs if r["_spec"].get("building_style") == "v43_form_lines"
            and r["text"].endswith(next(e["text"] for e in r["entities"] if e["label"] == "BUILDINGNUM"))]
    check(len(ends) >= 20, "X-BN: some forms end the document on the building number", len(ends))
    a = B.TargetedBuilder(seed=31, n_docs=300, quotas=q).build()
    b = B.TargetedBuilder(seed=31, n_docs=300, quotas=q).build()
    check([r["text"] for r in a] == [r["text"] for r in b], "X-BN: the preset build is deterministic")


def test_extra_batch_age() -> None:
    """X-AGE (red-team rule #136, frames_v43): a number next to `yaş` that is not a person's age, unlabelled, beside
    a real age of a person with `yaş`; without the preset nothing changes."""
    from piigen.targeted import frames_v43 as V43
    q = Q.load(Path(B.__file__).with_name("quotas_x_age.json"))
    check(q["age_v43"]["rate"] > 0 and Q._weights(q["decoy_groups"])["age"] == 1.0, "X-AGE: the preset loads")
    check(not Q.load().get("age_v43"), "X-AGE: quotas.json alone has no age_v43 (v4.2 untouched)")
    recs = B.TargetedBuilder(seed=33, n_docs=400, quotas=q).build()
    check(len(recs) == 400 and not _gates_ok(recs), "X-AGE: 400 documents, every gate passes", _gates_ok(recs)[:3])
    styles = collections.Counter(r["_spec"].get("age_style") for r in recs)
    check(all(styles["v43_" + s] >= 60 for s in V43.AGE_LOOKALIKES), "X-AGE: each look-alike kind written", dict(styles))
    for r in recs:
        st, t = r["_spec"].get("age_style", ""), r["text"]
        if not st.startswith("v43_"):
            continue
        kind = st[4:]
        ages = [e for e in r["entities"] if e["label"] == "AGE"]
        fakes = [x for x in r["_decoys"] if x["kind"] == kind]
        check(len(ages) == 1 and has_anchor_(r, ages[0]) and re.match(r" yaş", t[ages[0]["end"]:])
              or len(ages) == 1 and re.search(r"yaşı $", t[:ages[0]["start"]]),
              "X-AGE: one real age of a person, with `yaş` beside it", t)
        check(len(fakes) == (2 if kind == "age_range" else 1) and all(x["resembles"] == "AGE" for x in fakes)
              and all(t[x["start"]:x["end"]].isdigit() for x in fakes), "X-AGE: the look-alike(s), unlabelled", t)
        near = t[max(0, fakes[0]["start"] - 40):fakes[-1]["end"] + 20]
        check("yaş" in near, "X-AGE: the look-alike sits next to `yaş`", near)
        if kind == "age_range":
            check(int(t[fakes[0]["start"]:fakes[0]["end"]]) < int(t[fakes[1]["start"]:fakes[1]["end"]]),
                  "X-AGE: a range runs low to high", t)
        check(not re.search(r"\d-(dır|dir|dur|dür|dı|di|du|dü)\b", t), "X-AGE: no suffix glued to a digit", t)
    a = B.TargetedBuilder(seed=33, n_docs=200, quotas=q).build()
    b = B.TargetedBuilder(seed=33, n_docs=200, quotas=q).build()
    check([r["text"] for r in a] == [r["text"] for r in b], "X-AGE: the preset build is deterministic")


TESTS = [
    ("X-AGE: AGE look-alikes next to `yaş` (frames_v43)", test_extra_batch_age),
    ("X-BN: the extra batch's BUILDINGNUM top-up (frames_v43)", test_extra_batch_buildingnum),
    ("D-57: the v4.2 final fix list (M1-M7, S1-S7)", test_v42_final),
    ("D-56a: IPs at a line end, the IPv4 swing, short ID words", test_v42_d56a),
    ("v4.2 fix list (19 Oct; v4.1 shadow shapes)", test_v42_fix_list),
    ("v4.1 generator (D-52b-d, #91 fix list, #90 review A-G)", test_v41_generator),
    ("v4.1 A5 items (v3 shadow shapes, leads 3-5)", test_v41_a5),
    ("TIME with seconds (v3 shadow shapes, lead 1)", test_time_seconds),
    ("D-51h/D-51d/D-51i v4 targeted data", test_d51h),
    ("D-49: float totals with math.fsum", test_d49_fsum),
    ("D-42c shadow-shape fixes", test_d42c),
    ("D-41a cvv pairs", test_cvv_pairs),
    ("D-39b name constructions", test_d39b_names),
    ("D-36b native review fixes", test_d36b_review),
    ("D-34 part 2, group 3", test_part2_group3),
    ("D-35a DATE look-alikes in label: value lines", test_d35a_dates),
    ("D-34 part 2, group 2", test_part2_group2),
    ("D-34 part 2, group 1", test_part2_group1),
    ("D-30b/D-33 fix round: CVV, FIN, ZIP shapes", test_fix_round),
    ("entity casing noise (P2-4b)", test_case_noise_unit),
    ("P2-4b extras in a real build", test_extras_in_build),
    ("casing-noise quota cannot reach the cap", test_quota_cap),
    ("C1 stub shape", test_stub_shape),
    ("frames_az.py is picked up automatically", test_frames_pickup),
    ("every record passes every gate", test_records_pass_every_gate),
    ("--stats targets", test_stats),
    ("contrast pairs", test_contrasts),
    ("decoy pairs", test_pairs),
    ("determinism", test_determinism),
    ("frame diversity rule fails the build", test_frame_cap),
    ("quotas.json", test_quotas),
    ("value styles and reserved-TLD emails", test_values_and_emails),
    ("structured containers", test_formats),
    ("validate_corpus.py, prepare_splits.py and the CLI", test_task_commands),
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
