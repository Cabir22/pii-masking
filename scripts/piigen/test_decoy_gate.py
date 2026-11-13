"""P2-3 acceptance check: the quality gates skip DECLARED decoys, and only those.

No network, no model. The task's four checks, plus the machinery they rest on:

  (a) a Luhn-valid `4242…` declared as a decoy passes every gate;
  (b) the same string undeclared still fails;
  (c) a real unlabeled planned value still fails when a decoy is declared
      elsewhere in the same document;
  (d) 200 LLM-shaped decoy records, assembled by the real
      `pipeline.assemble_document` from real briefs with decoys switched on,
      pass `prepare_splits.py --no-tokenize` with 0 rejections, and their
      `_decoys` / `_gen_version` / `_source` fields survive it.

Mirrors the translation harness's tests (scripts/translate/test_harness.py):
declared decoys are exempt, an undeclared copy of the same string is a leak,
and a value inside a declared decoy is exempt.

    python scripts/piigen/test_decoy_gate.py
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from piigen import checksums as CK                                    # noqa: E402
from piigen.config import GeneratorConfig                             # noqa: E402
from piigen.llm.pipeline import assemble_document                     # noqa: E402
from piigen.llm.quality import find_leaked_pii                        # noqa: E402
from piigen.llm.quality_filter import (check_unlabeled_planned_pii,   # noqa: E402
                                       screen_record)
from piigen.llm.specs import SpecSampler                              # noqa: E402
from piigen.negatives import (ADVERSARIAL, FAMILY_RESEMBLES,          # noqa: E402
                              HARD_NEGATIVES, decoy_occurrences,
                              locate_decoys, planted_decoys)
from piigen.noise import NoiseInjector                                # noqa: E402
from piigen.provenance import GEN_VERSION                             # noqa: E402
from piigen.resolver import (complete_occurrences,                    # noqa: E402
                             find_unlabeled_repeats, resolve_claims)
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
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def span(text: str, sub: str, nth: int = 0) -> tuple[int, int]:
    i = -1
    for _ in range(nth + 1):
        i = text.index(sub, i + 1)
    return i, i + len(sub)


def ent(text: str, sub: str, label: str, nth: int = 0) -> dict:
    s, e = span(text, sub, nth)
    return {"start": s, "end": e, "label": label, "text": sub}


def decoy(text: str, sub: str, kind: str = "policy_test_card",
          resembles: str = "PAYMENT_CARD_NUMBER", nth: int = 0) -> dict:
    s, e = span(text, sub, nth)
    return {"start": s, "end": e, "kind": kind, "resembles": resembles}


CARD = "4242424242424242"
# A plain Azerbaijani document that passes validate_example on its own.
BODY = ("Hörmətli Aysel xanım, müraciətiniz qəbul edildi və bank şöbəsi tərəfindən "
        "diqqətlə nəzərdən keçirildi. Ödəniş sistemində kart nömrəsi {card} "
        "yalnız yoxlama məqsədilə göstərilib, heç bir əməliyyat aparılmayıb. "
        "Əlavə sualınız olarsa, bizimlə əlaqə saxlamağınızı xahiş edirik.")


def base_record(text: str, decoys: list[dict] | None = None) -> dict:
    rec = {"id": "t1", "text": text, "lang": "az",
           "entities": [ent(text, "Aysel", "GIVENNAME")]}
    if decoys is not None:
        rec["_decoys"] = decoys
    return rec


# --------------------------------------------------------------------------- #
def test_a_declared_decoy_passes() -> None:
    text = BODY.format(card=CARD)
    rec = base_record(text, [decoy(text, CARD)])
    check(find_leaked_pii(text, rec["entities"], decoy_spans=rec["_decoys"]) == [],
          "(a) declared Luhn-valid 4242… is not a leak",
          find_leaked_pii(text, rec["entities"], decoy_spans=rec["_decoys"]))
    check(validate_example(rec) == [], "(a) validate_example accepts it (blocklist exempt)",
          validate_example(rec))
    check(screen_record(rec) == [], "(a) screen_record with base gates accepts it",
          screen_record(rec))


def test_b_undeclared_same_string_fails() -> None:
    text = BODY.format(card=CARD)
    rec = base_record(text)                                   # no _decoys at all
    check(any(l.startswith("CARD:") for l in find_leaked_pii(text, rec["entities"])),
          "(b) the same string undeclared is a CARD leak")
    check(any("placeholder" in p for p in validate_example(rec)),
          "(b) undeclared 4242… still hits the blocklist", validate_example(rec))
    check(screen_record(rec) != [], "(b) screen_record rejects the undeclared copy")
    # two copies, only the first declared: the second is still a leak
    text2 = text + f" Təkrar: {CARD}."
    rec2 = base_record(text2, [decoy(text2, CARD, nth=0)])
    check(any(l.startswith("CARD:") for l in
              find_leaked_pii(text2, rec2["entities"], decoy_spans=rec2["_decoys"])),
          "(b) an undeclared SECOND copy is a leak even with the first declared")
    check(any("placeholder" in p for p in validate_example(rec2)),
          "(b) an undeclared second copy still hits the blocklist")


def test_c_planned_value_still_fails() -> None:
    email = "leyla.aliyeva@example-bank.az"
    text = BODY.format(card=CARD) + f" Cavab {email} ünvanına göndəriləcək."
    rec = base_record(text, [decoy(text, CARD)])
    planned = [("GIVENNAME", "Aysel"), ("EMAIL", email)]
    check(any("EMAIL" in p for p in check_unlabeled_planned_pii(
              text, rec["entities"], planned, [(d["start"], d["end"]) for d in rec["_decoys"]])),
          "(c) an unlabeled planned EMAIL fails although a decoy is declared elsewhere")
    check(any(l.startswith("EMAIL:") for l in
              find_leaked_pii(text, rec["entities"], decoy_spans=rec["_decoys"])),
          "(c) the unlabeled EMAIL is a leak although a decoy is declared elsewhere")
    check(any("never labeled" in p for p in screen_record(rec, planned=planned)),
          "(c) screen_record reports it")
    # mirror of the harness's "a value inside a declared decoy is exempt":
    # a planned AGE `34` whose only occurrence is inside the decoy REF340012
    text3 = "Müştərinin daxili istinad nömrəsi REF340012 arxivdə saxlanılır."
    check(check_unlabeled_planned_pii(text3, [], [("AGE", "34")],
                                      [span(text3, "REF340012")]) == [],
          "(c) a planned value found only inside a declared decoy is not a leak")
    check(check_unlabeled_planned_pii(text3, [], [("AGE", "34")]) != [],
          "(c) ...and without the declaration it is still reported")


def test_old_string_hole_closed() -> None:
    # The old rule exempted any match CONTAINING a decoy's characters: a
    # planted port `443` exempted this real, Luhn-valid, unlabeled card.
    body = "453244317775123"
    digits = body + CK.luhn_check_digit(body)
    real = " ".join(digits[i:i + 4] for i in range(0, 16, 4))
    check(CK.luhn_valid(digits) and "443" in digits, "fixture card is Luhn-valid and holds 443")
    text = f"Port 443 açıqdır. Müştəri {real} kartı ilə ödəniş edib."
    check(any(l.startswith("CARD:") for l in find_leaked_pii(text, [], decoys=["443"])),
          "a planted `443` no longer exempts a real card containing 443",
          find_leaked_pii(text, [], decoys=["443"]))
    # the older string API still works for the translation harness
    legacy = "Ref 4539578763621486 kimi göstərilib."
    check(find_leaked_pii(legacy, [], decoys=["4539578763621486"]) == [],
          "string-form decoy is still exempt (translation harness contract)")
    check(find_leaked_pii("Ref 4539 5787 6362 1486 kimi.", [],
                          decoys=["4539578763621486"]) == [],
          "a regrouped string-form decoy is still exempt")
    check(find_leaked_pii(legacy, [], decoys=[]) != [],
          "...and without it the same string is a leak")


def test_locate_decoys() -> None:
    def plant(phrase, value, kind="k", resembles="R", anchored=True):
        return {"string": phrase, "value": value, "kind": kind,
                "resembles": resembles, "anchored": anchored}

    t = "Qeyddə kart nömrəsi 4242424242424242 göstərilib."
    d = locate_decoys(t, [plant("kart nömrəsi 4242424242424242", CARD)])
    check([t[x["start"]:x["end"]] for x in d] == [CARD],
          "anchored decoy: the declared span is the value inside its phrase", d)
    t = "İstinad nömrəsi REF123456 arxivdədir."
    d = locate_decoys(t, [plant("istinad nömrəsi REF123456", "REF123456")])
    check([t[x["start"]:x["end"]] for x in d] == ["REF123456"],
          "a sentence-initial İ-capitalised phrase is found", d)
    t = "Sənəddə şəxsiyyət vəsiqəsinin FİN kodu A12-B34 yazılıb."
    d = locate_decoys(t, [plant("şəxsiyyət vəsiqəsinin FİN kodu A12-B34", "A12-B34")])
    check([t[x["start"]:x["end"]] for x in d] == ["A12-B34"],
          "offsets stay exact after an İ in the phrase (no .lower())", d)
    t = "Qeyd: istinad REF654321 sonradan əlavə olunub."
    d = locate_decoys(t, [plant("daxili istinad REF654321", "REF654321")])
    check([t[x["start"]:x["end"]] for x in d] == ["REF654321"],
          "phrase paraphrased, value survived: the value is declared", d)
    t = "Kodu 12 kimi yazıb."
    check(locate_decoys(t, [plant("CVV kodu 12", "12")]) == [],
          "phrase gone and the value is too short: nothing declared")
    t = "Poçt indeksi AZ1234 kimi yazılıb."
    check(locate_decoys(t, [plant("IBAN: AZ1234", "AZ1234")], planned_values=["AZ1234"]) == [],
          "phrase gone and the value is a planned entity value: nothing declared")
    check(locate_decoys("Tamam başqa mətn.", [plant("CVV kodu 12345", "12345")]) == [],
          "a decoy the model dropped is not declared")
    t = "Əlaqə: +994 50 443 12 34, port 443."
    d = locate_decoys(t, [plant("443", "443", anchored=False)],
                      planned_values=["+994 50 443 12 34"])
    check([t[x["start"]:x["end"]] for x in d] == ["443"] and d[0]["start"] > t.index(","),
          "a decoy is never declared inside a planned value", d)
    t = "Bu il şəhər Bakı layihəsi başa çatdı, Bakı isə böyüyür."
    d = locate_decoys(t, [plant("şəhər Bakı layihəsi", "Bakı layihəsi", "policy_city_as_project", "CITY")],
                      planned_values=["Bakı"])
    check([t[x["start"]:x["end"]] for x in d] == ["Bakı layihəsi"],
          "a policy phrase that fully contains a planned value wins (D-2)", d)
    ents, _ = resolve_claims(t, [{"label": "CITY", "text": "Bakı"}],
                             blocked=[(x["start"], x["end"]) for x in d])
    check([e["start"] for e in ents] == [t.rindex("Bakı")],
          "...and the planned CITY is labeled only outside it", ents)
    t = "Link https://x.az/AB123 var, AB123 də."
    d = locate_decoys(t, [plant("https://x.az/AB123", "https://x.az/AB123", anchored=False),
                          plant("AB123", "AB123", anchored=False)])
    check([t[x["start"]:x["end"]] for x in d] == ["https://x.az/AB123", "AB123"],
          "longest first, and every other occurrence is declared", d)
    t = "Kod 4539 5787 6362 1486 imiş."
    d = locate_decoys(t, [plant("4539578763621486", "4539578763621486", anchored=False)])
    check([t[x["start"]:x["end"]] for x in d] == ["4539 5787 6362 1486"],
          "a regrouped plain decoy is found (tolerant for 8+ characters)", d)
    check(decoy_occurrences("x12345y 12345", "12345") == [(8, 13)],
          "occurrences glued to a letter are not the decoy")
    sources = planted_decoys([{"phrase": "CVV kodu 12345", "value": "12345", "kind": "cvv_5_digits",
                               "resembles": "CARD_SECURITY_CODE"}],
                             [{"kind": "PORT", "value": "443", "resembles": None}],
                             ["CVV kodu 12345", "443", "legacy"])
    check([s["kind"] for s in sources] == ["cvv_5_digits", "PORT", "unknown"],
          "planted_decoys: anchored, plain, then strings-only briefs", sources)


def test_labeled_or_malformed_decoys_are_problems() -> None:
    text = BODY.format(card=CARD)
    rec = base_record(text, [decoy(text, "Aysel", kind="sentence_initial_genitive",
                                   resembles="GIVENNAME")])
    check(any("overlaps the GIVENNAME span" in p for p in validate_example(rec)),
          "a decoy overlapping a labeled entity is a validation problem")
    for bad, why in (([{"start": 5}], "malformed"), ("x", "not a list"),
                     ([{"start": 5, "end": 999999, "kind": "k"}], "out of range")):
        rec = base_record(text, bad)
        check(any(why in p for p in validate_example(rec)),
              f"malformed `_decoys` is reported: {why}", validate_example(rec))
    check(validate_example(base_record(BODY.format(card="0000 kod"))) == [],
          "a record without `_decoys` behaves exactly as before")


def test_resolver_and_repeats() -> None:
    t = "Ad Dəniz yazılıb. Dəniz sakit idi."
    sea = span(t, "Dəniz", 1)
    ents, _ = resolve_claims(t, [{"label": "GIVENNAME", "text": "Dəniz"}], blocked=[sea])
    check([(e["start"], e["end"]) for e in ents] == [span(t, "Dəniz", 0)],
          "resolve_claims never labels inside a declared decoy", ents)
    done, added = complete_occurrences(t, ents, blocked=[sea])
    check(added == 0, "complete_occurrences leaves a declared decoy alone", done)
    check(find_unlabeled_repeats(t, ents, exempt=[sea]) == 0,
          "an identical string inside a declared decoy is not a missing repeat")
    check(find_unlabeled_repeats(t, ents) == 1, "...and undeclared it is")


def test_noise_protects_decoys() -> None:
    gen = GeneratorConfig()
    text = ("Saat 22:94 kimi yazılıb, istinad REF654321 və kart 4242424242424242 "
            "qeyd olunub. Aysel xanım bu barədə məlumatlandırılıb, hər şey qaydasındadır. "
            * 3)
    decs = [{**decoy(text, v, nth=k), "value": v} for v in ("22:94", "REF654321", CARD)
            for k in range(3)]
    ents = [ent(text, "Aysel", "GIVENNAME", nth=k) for k in range(3)]
    changed = kept_all = exact = 0
    for seed in range(300):
        new, new_ents, kept, applied = NoiseInjector(gen, random.Random(seed)).apply_protected(
            text, ents, [{k: v for k, v in d.items() if k != "value"} for d in decs], "az", rate=1.0)
        changed += new != text
        kept_all += len(kept) == len(decs)
        exact += all(new[k["start"]:k["end"]] == d["value"] for k, d in zip(kept, decs))
        if not all(new[e["start"]:e["end"]] == e["text"] for e in new_ents):
            check(False, "entity spans stay exact under noise", seed)
            return
    REPORT.append(f"noise: 300 noised docs, {changed} changed, decoys kept {kept_all}/300, "
                  f"decoy text unchanged {exact}/300")
    check(changed > 250, "noise was actually applied", changed)
    check(kept_all == 300 and exact == 300,
          "every declared decoy survives noise, byte for byte, at its remapped offset",
          (kept_all, exact))


def test_old_families_r4() -> None:
    check(set(FAMILY_RESEMBLES) == set(HARD_NEGATIVES) | set(ADVERSARIAL),
          "every older family says what it imitates",
          set(HARD_NEGATIVES) | set(ADVERSARIAL) ^ set(FAMILY_RESEMBLES))
    r = random.Random(5)
    for fam, fn in list(HARD_NEGATIVES.items()) + list(ADVERSARIAL.items()):
        label = FAMILY_RESEMBLES.get(fam)
        if not label:
            continue
        bad = [v for v in (fn("az", r) for _ in range(2000)) if value_valid(label, v)[0]]
        check(not bad, f"R4: family {fam} emits valid {label} values", bad[:3])


def test_gen_version() -> None:
    check(bool(re.fullmatch(r"[0-9a-f]{12}(\+dirty)?|unknown", GEN_VERSION)),
          "_gen_version is a 12-character SHA (+dirty) or 'unknown'", GEN_VERSION)


# --------------------------------------------------------------------------- #
# (d) LLM-shaped decoy records through the real assemble_document
# --------------------------------------------------------------------------- #
_FRAME = {
    "GIVENNAME": "Müraciət edən şəxsin adı {v} kimi qeyd olunub.",
    "SURNAME": "Soyadı {v} olaraq göstərilib.",
    "CITY": "Müştəri hazırda {v} şəhərində yaşayır.",
    "STREET": "Faktiki ünvan: {v}.",
    "BUILDINGNUM": "Ünvanda bina {v} göstərilib.",
    "ZIPCODE": "Poçt indeksi {v} kimi yazılıb.",
    "TELEPHONENUM": "Əlaqə telefonu: {v}.",
    "EMAIL": "Elektron poçt ünvanı {v} qeydə alınıb.",
    "DATE": "Doğum tarixi {v} kimi qeyd olunub.",
    "TIME": "Görüş saat {v} üçün planlaşdırılıb.",
    "AGE": "Müştərinin yaşı {v} kimi göstərilib.",
    "CARD_SECURITY_CODE": "Kartın CVV kodu {v} olaraq daxil edilib.",
    "PAYMENT_CARD_NUMBER": "Ödəniş bank kartı {v} ilə aparılıb.",
    "IBAN": "Hesabın IBAN kodu {v} kimi verilib.",
}
_FILLER = ("Sənəd şöbə tərəfindən yoxlanılıb və arxivə təhvil verilib. "
           "Bütün qeydlər qaydaya uyğun olaraq sistemdə saxlanılır.")


def _llm_text(spec) -> str:
    """What a well-behaved model would write for this brief: every value and
    every decoy verbatim, in ordinary Azerbaijani sentences."""
    parts = [_FILLER]
    for e in spec.entities:
        parts.append(_FRAME.get(e.label, "Sənəddə göstərilən məlumat: {v}.").format(v=e.value))
    for d in spec.hard_negatives:
        parts.append(f"Əlavə olaraq, {d} barədə qeyd sistemdə saxlanılır.")
    parts.append(_FILLER)
    return " ".join(parts)


def test_d_prepare_splits() -> None:
    gen = GeneratorConfig()
    gen.hard_negative_rate = 1.0          # decoys switched on, as P1-5 does (D-1)
    gen.adversarial_rate = 0.5
    gen.negative_only_rate = 0.1
    gen.edge_case_rate = 0.0
    sampler = SpecSampler(gen, ValueFactory(random.Random(21), ValuePool(state_path=None)),
                          random.Random(22))
    accepted, reasons = [], collections.Counter()
    kinds, index = collections.Counter(), 0
    logging.disable(logging.WARNING)
    try:
        while len(accepted) < 200 and index < 2000:
            spec = sampler.sample(index)
            index += 1
            out = assemble_document(spec, _llm_text(spec), gen, 0.18)
            if out.ok:
                accepted.append(out.record)
                kinds.update(d["kind"] for d in out.record["_decoys"])
            else:
                reasons[re.sub(r"\d+", "N", out.reason)[:70]] += 1
    finally:
        logging.disable(logging.NOTSET)
    declared = sum(len(r["_decoys"]) for r in accepted)
    planted = sum(len(r["_spec"]["hard_negatives"]) for r in accepted)
    REPORT.append(f"(d) {len(accepted)} accepted of {index} assembled; rejections: "
                  f"{dict(reasons.most_common(6))}")
    REPORT.append(f"(d) {declared} decoys declared for {planted} planted, "
                  f"{len(kinds)} kinds, policy_test_card {kinds['policy_test_card']}")
    check(len(accepted) == 200, "(d) 200 decoy records assembled", len(accepted))
    check(sum(1 for r in accepted if r["_decoys"]) >= 190,
          "(d) (almost) every record declares its decoys",
          sum(1 for r in accepted if r["_decoys"]))
    # This fixture writes fixed-length text, so briefs for the longest bands
    # fail the carrier-word minimum; nothing may fail because of a decoy.
    # D-57 added anchored kinds, which moved the sampler's draws onto two
    # value-pool cases that involve no decoy: a rare given name the quality
    # gate reads as a misspelling (`Ünvanzər`), and a pool name inside an
    # email's local part that the Turkish-lexis check reads (`nasil.…@`).
    value_side = re.compile(r"never labeled \(\w+, misspelled\)|turkish_lexis")
    decoy_reasons = [k for k in reasons if not value_side.search(k)
                     and re.search(r"leak|blocklist|decoy|never labeled|overlap", k)]
    check(not decoy_reasons, "(d) no document rejected because of its decoys", dict(reasons))
    check(all("carrier word" in k or "density" in k or value_side.search(k) for k in reasons),
          "(d) every rejection is the fixture's length (or a value-side case), not a gate misfire",
          dict(reasons))
    check(all(r["_source"] == "llm" and r["_gen_version"] == GEN_VERSION for r in accepted),
          "(d) every record carries _source and _gen_version")

    with tempfile.TemporaryDirectory() as tmp:
        sample = Path(tmp) / "sample.jsonl"
        sample.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in accepted),
                          encoding="utf-8")
        out_dir = Path(tmp) / "p2check"
        run = subprocess.run([sys.executable, str(HERE.parent / "prepare_splits.py"),
                              str(sample), "--output-dir", str(out_dir), "--no-tokenize"],
                             capture_output=True, text=True, encoding="utf-8")
        REPORT.append("(d) prepare_splits: " + " | ".join(
            ln.strip() for ln in run.stdout.splitlines()
            if "record" in ln or "clean" in ln or "failed" in ln)[:300])
        check(run.returncode == 0, "(d) prepare_splits exits 0", run.stderr[-400:])
        check("failed re-validation" not in run.stdout,
              "(d) 0 records rejected by prepare_splits' re-validation", run.stdout[-800:])
        rows = [json.loads(line) for name in ("train", "val", "test")
                for line in (out_dir / f"{name}.docs.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
        # P1-6 gates the same files with validate_corpus.py on Day 3
        gate = subprocess.run([sys.executable, str(HERE.parent / "validate_corpus.py"), str(sample)],
                              capture_output=True, text=True, encoding="utf-8")
        verdict = next((ln for ln in gate.stdout.splitlines() if ln.startswith("RESULT")), "")
        REPORT.append(f"(d) validate_corpus.py: {verdict}")
        check(gate.returncode == 0, "(d) P1-6's validate_corpus.py passes the decoy records",
              [ln for ln in gate.stdout.splitlines() if "FAIL" in ln][:5])
        undeclared = [{k: v for k, v in r.items() if k not in ("_spec", "_pii_free")}
                      for r in accepted if not r["entities"]][:2]
        check(len(undeclared) == 2, "(d) the sample has PII-free records", len(undeclared))
        bad = Path(tmp) / "undeclared.jsonl"
        bad.write_text("".join(json.dumps({**r, "id": r["id"] + "_x"}, ensure_ascii=False) + "\n"
                               for r in undeclared), encoding="utf-8")
        gate = subprocess.run([sys.executable, str(HERE.parent / "validate_corpus.py"), str(bad)],
                              capture_output=True, text=True, encoding="utf-8")
        check(gate.returncode != 0 and "no_entities" in gate.stdout,
              "(d) an empty record NOT declared PII-free still fails no_entities")
    check(all(r["_pii_free"] == (not r["entities"]) for r in accepted),
          "(d) `_pii_free` is set exactly on the PII-free records")
    check(len(rows) == 200, "(d) all 200 records written by prepare_splits", len(rows))
    check(all("_decoys" in r and "_gen_version" in r and r.get("_source") == "llm" for r in rows),
          "(d) `_decoys`, `_gen_version` and `_source` are carried through, not dropped")
    by_id = {r["id"]: r for r in accepted}
    check(all(r["_decoys"] == by_id[r["id"]]["_decoys"] for r in rows),
          "(d) declared spans are unchanged by prepare_splits")


TESTS = [
    ("(a) a declared 4242… passes every gate", test_a_declared_decoy_passes),
    ("(b) the same string undeclared still fails", test_b_undeclared_same_string_fails),
    ("(c) a real unlabeled planned value still fails", test_c_planned_value_still_fails),
    ("the old string-containment hole is closed", test_old_string_hole_closed),
    ("locate_decoys", test_locate_decoys),
    ("labeled or malformed decoys are problems", test_labeled_or_malformed_decoys_are_problems),
    ("resolver and repeat check respect declared decoys", test_resolver_and_repeats),
    ("noise never edits a declared decoy", test_noise_protects_decoys),
    ("R4 for the older decoy families", test_old_families_r4),
    ("_gen_version", test_gen_version),
    ("(d) 200 decoy records through prepare_splits", test_d_prepare_splits),
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
