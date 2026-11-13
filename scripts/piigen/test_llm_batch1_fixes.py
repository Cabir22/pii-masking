"""P2-6 generator fixes from the LLM batch-1 audit (P2-5), fixes 2 to 6.
Fix 1 has its own file, test_planned_values.py.

No network, no model, no API key. Checks that read batch 1 itself are
skipped when data/raw/sprint1_llm_b1.jsonl is not pulled.

    python scripts/piigen/test_llm_batch1_fixes.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.config import GeneratorConfig                              # noqa: E402
from piigen.resolver import resolve_claims                              # noqa: E402
from piigen.validate import declared_decoy_spans                        # noqa: E402

BATCH1 = ROOT / "data" / "raw" / "sprint1_llm_b1.jsonl"
PASS = FAIL = SKIP = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def batch1() -> list[dict] | None:
    global SKIP
    if not BATCH1.exists() or BATCH1.stat().st_size < 10_000:   # absent, or an LFS pointer
        SKIP += 1
        return None
    return [json.loads(line) for line in BATCH1.open(encoding="utf-8")]


def drifts(rec: dict) -> bool:
    decoys, _ = declared_decoy_spans(rec)
    ents = rec["entities"]
    now, _ = resolve_claims(rec["text"], [{"label": e["label"], "text": e["text"]} for e in ents],
                            blocked=decoys)
    return ({(e["start"], e["end"], e["label"]) for e in now}
            != {(e["start"], e["end"], e["label"]) for e in ents})


def spans(ents: list[dict]) -> set:
    return {(e["start"], e["end"], e["label"]) for e in ents}


# --------------------------------------------------------------------------- #
def test_fix2_caps() -> None:
    """Noise in capitals after labelling must not make validate_corpus's
    resolver_drift re-check lose a span (batch 1: 7 records)."""
    from piigen.noise import NoiseInjector
    text = ("Ünvan: Mikayıl Əliyev pr.-də mövcud olan mülk barədə yazırıq. "
            "Saat 06:50-dan bəri gözləyirəm, Şəmkirdə ofisimiz var.")
    claims = [{"label": "STREET", "text": "Mikayıl Əliyev pr."},
              {"label": "TIME", "text": "06:50"}, {"label": "CITY", "text": "Şəmkir"}]
    ents, _ = resolve_claims(text, claims)
    check([e["text"] for e in ents] == ["Mikayıl Əliyev pr.", "06:50", "Şəmkirdə"],
          "lowercase: street and time stop before the hyphen suffix, the city takes its suffix",
          [e["text"] for e in ents])
    inj = NoiseInjector(GeneratorConfig(), random.Random(3))
    noised, moved = inj._all_caps(text, ents, [], "az")
    check(noised.startswith("ÜNVAN: MIKAYIL ƏLIYEV PR.-DƏ"), "the all_caps kind shouts the document", noised[:40])
    again, _ = resolve_claims(noised, [{"label": e["label"], "text": e["text"]} for e in moved])
    check(spans(again) == spans(moved), "all_caps: re-resolution reproduces every span",
          [e["text"] for e in again])
    glitched = text.replace("pr.-də", "pr.-Də").replace("06:50-dan", "06:50-dAN").replace(
        "Şəmkirdə", "ŞəmkirDƏ")
    ents2, _ = resolve_claims(glitched, claims)
    check([e["text"] for e in ents2] == ["Mikayıl Əliyev pr.", "06:50", "ŞəmkirDƏ"],
          "case_glitch inside a suffix: still the same grammar", [e["text"] for e in ents2])
    recs = batch1()
    if recs:
        caps = {"llm_az_000899", "llm_az_004039", "llm_az_004478", "llm_az_005995", "llm_az_008903"}
        stored = [r for r in recs if r["id"] in caps]
        check(len(stored) == 5 and not any(drifts(r) for r in stored),
              "batch 1: the 5 capitals records no longer drift")


def _spec(negative_only: bool = False, band: str = "very_short", entities=()):
    from piigen.llm.specs import LENGTH_BANDS, DocumentSpec, PlannedEntity
    lo, hi = next((b[2], b[3]) for b in LENGTH_BANDS if b[0] == band)
    return DocumentSpec(index=1, lang="az", doc_type="technical_log", doc_type_hint="a log",
                        register="terse", band=band, min_chars=lo, max_chars=hi,
                        length_hint="", seed=5, negative_only=negative_only,
                        entities=[PlannedEntity(lab, val) for lab, val in entities])


def test_fix3_language() -> None:
    """Generation applies the gate's language rule to PII-free documents:
    the 33 short ones validate_corpus failed are rejected when generated."""
    from piigen.audit_llm_batch import spec_from_record
    from piigen.llm.pipeline import assemble_document
    from piigen.validate import validate_example
    cfg = GeneratorConfig()
    text = "[ERR] npm@latest failed: code 5531-6969, retry 3/5."
    out = assemble_document(_spec(negative_only=True), text, cfg, 0.0)
    check(not out.ok and out.reason.startswith("validation: language"),
          "a PII-free log line without Azerbaijani words is rejected at generation", out.reason)
    text = ("[ERR] Sistem xətası baş verdi, kod 5531-6969. Zəhmət olmasa bir az sonra "
            "yenidən cəhd edin, problem həll olunacaq.")
    out = assemble_document(_spec(negative_only=True), text, cfg, 0.0)
    check(out.ok, "...and one with two real Azerbaijani sentences is accepted", out.reason)
    recs = batch1()
    if recs:
        gate = {r["id"] for r in recs
                if any(p.startswith("language") for p in validate_example(r))}
        rejected = set()
        for r in recs:
            if not r["_spec"]["negative_only"]:
                continue
            o = assemble_document(spec_from_record(r), r["text"], cfg, 0.0)
            if not o.ok and o.reason.startswith("validation: language"):
                rejected.add(r["id"])
        check(len(gate) == 33 and rejected == gate,
              "batch 1: replaying the PII-free documents rejects exactly the gate's 33",
              (len(gate), len(rejected), sorted(rejected ^ gate)[:5]))


BATCH1_RATES = {"edge_case_rate": 0.3, "negative_only_rate": 0.1,
                "hard_negative_rate": 0.3, "adversarial_rate": 0.2}
_SPECS: list = []


def offline_specs(n: int = 12_000) -> list:
    """12,000 briefs sampled offline at batch 1's rates (no API)."""
    if not _SPECS:
        from piigen.llm.specs import SpecSampler
        from piigen.values import ValueFactory, ValuePool
        import logging
        logging.getLogger("piigen.values").setLevel(logging.ERROR)
        cfg = GeneratorConfig()
        for k, v in BATCH1_RATES.items():
            setattr(cfg, k, v)
        sampler = SpecSampler(cfg, ValueFactory(random.Random(7), ValuePool(state_path=None)),
                              random.Random(11))
        _SPECS.extend(sampler.sample(i) for i in range(n))
    return _SPECS


def test_fix4_rates() -> None:
    """Requested rates hold as shares of ALL documents; edge cases still work."""
    specs = offline_specs()
    n = len(specs)
    measured = {
        "edge_case_rate": sum(s.edge_case is not None for s in specs) / n,
        "negative_only_rate": sum(s.negative_only for s in specs) / n,
        "hard_negative_rate": sum(any(h not in s.adversarials for h in s.hard_negatives)
                                  for s in specs) / n,
        "adversarial_rate": sum(bool(s.adversarials) for s in specs) / n,
    }
    for k, want in BATCH1_RATES.items():
        check(abs(measured[k] - want) <= 0.015, f"{k}: {measured[k]:.1%} of {n:,} briefs "
              f"(asked {want:.0%}, +/-1.5 points)", measured[k])
    edge = [s for s in specs if s.edge_case is not None]
    from piigen.llm import edge_cases as EC
    pair = {c.case.id for c in EC.CONTRAST_CASES}          # P2-6: two values
    check(all(len(s.entities) <= (2 if s.edge_case.id in pair else 1)
              and not s.hard_negatives and not s.negative_only for s in edge)
          and sum(bool(s.entities) for s in edge) / len(edge) > 0.95,
          "edge-case briefs still target one value (a contrast lesson two), with no decoys")
    neg = [s for s in specs if s.negative_only]
    check(all(not s.entities and s.hard_negatives and s.adversarials for s in neg),
          "PII-free briefs plan no value and carry both kinds of decoy")
    # a rate that cannot hold is reported, and the nearest share is used
    from piigen.llm.specs import SpecSampler
    cfg = GeneratorConfig()
    for k, v in {**BATCH1_RATES, "hard_negative_rate": 0.05}.items():
        setattr(cfg, k, v)
    p_neg, p_hard, p_adv = SpecSampler(cfg, None, random.Random(1)).branch_rates()
    check(p_hard == 0.0 and abs(p_neg - 0.1 / 0.7) < 1e-9,
          "hard_negative_rate below negative_only_rate: no positive gets hard negatives",
          (p_neg, p_hard, p_adv))


def test_fix5_keyword() -> None:
    """The password-keyword share is measured on the secret's material and
    stays under GeneratorConfig.password_keyword_share (12%)."""
    from piigen.blocklist import has_password_keyword
    cap = GeneratorConfig().password_keyword_share
    secrets = [e.value for s in offline_specs() for e in s.entities
               if e.label in ("PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN")]
    share = sum(map(has_password_keyword, secrets)) / max(1, len(secrets))
    check(len(secrets) > 1000 and share <= cap,
          f"offline briefs: keyword share {share:.1%} of {len(secrets):,} planned secrets <= {cap:.0%}")
    for value, want in [("-----BEGIN OPENSSH PRIVATE KEY-----\nAbCdEf0123\n-----END OPENSSH PRIVATE KEY-----", False),
                        ("key_tyJyTmyMj0eP7MI4jYEt", False), ("apikey_wlZUenmQIs3fFyWey", False),
                        ("-----BEGIN PRIVATE KEY-----\nadminSecretXyz\n-----END PRIVATE KEY-----", True),
                        ("key_root1234abcd", True), ("tok_mypassw0rd", True), ("secretkey_live_x", True),
                        ("Password123", True)]:
        check(has_password_keyword(value) is want, f"keyword in {value[:30]!r}: {want}")
    recs = batch1()
    if recs:
        sec = [e["text"] for r in recs for e in r["entities"]
               if e["label"] in ("PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN")]
        b1 = sum(map(has_password_keyword, sec)) / len(sec)
        check(b1 <= cap, f"batch 1: keyword share {b1:.1%} of {len(sec)} secrets (was 21.4%)")


def rejects1() -> list[dict] | None:
    global SKIP
    path = BATCH1.with_name("sprint1_llm_b1.rejects.jsonl")
    if not path.exists() or path.stat().st_size < 10_000:
        SKIP += 1
        return None
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def test_fix6_prompt_and_parser() -> None:
    """What wasted batch 1's API calls, fixed on our side without touching a
    quality filter: the parser, and the brief's wording."""
    from piigen.llm.dspy_generate import _language_clause, strip_completion_marker
    from piigen.llm.quality import LEAK_WORDS
    from piigen.llm.quality_filter import _ADAPTER_ARTIFACT
    from piigen.validate import TURKISH_ONLY_FORMS
    for raw in ["Hörmətlə,\nNurlan\n\n[[ ## completed ]]", "x\n[[ ##   completed ]]",
                "x [[\xa0## completed ]]", "x [[ ## completed ## ]]  "]:
        check(strip_completion_marker(raw) in ("Hörmətlə,\nNurlan", "x"),
              f"a trailing completion marker is protocol, not text: {raw[-22:]!r}")
    mid = "a [[ ## completed ]] b"
    check(strip_completion_marker(mid) == mid and _ADAPTER_ARTIFACT.search(mid),
          "a marker inside the text stays, and the quality filter still rejects it")
    rej = rejects1()
    if rej:
        art = [r for r in rej if r["reason"] == "quality: adapter artifact in text"]
        saved = [r for r in art if not _ADAPTER_ARTIFACT.search(strip_completion_marker(r["text"]))]
        check(len(art) == 482 and len(saved) >= 470,
              f"batch 1: {len(saved)} of {len(art)} adapter-artifact rejections were only the trailing marker")
    src = (ROOT / "scripts" / "piigen" / "llm" / "dspy_generate.py").read_text(encoding="utf-8")
    brief = src[src.index("class GenerateTrainingDocument"):src.index("language: str = dspy.InputField")]
    brief = " ".join(brief.split())
    check(all(w in brief for w in LEAK_WORDS),
          "rule 5 names every word the judgment-leak check rejects", [w for w in LEAK_WORDS if w not in brief])
    for phrase in ("support, info, admin or destek mailbox", "domain of the service",
                   "city, district or village names", "building or flat numbers", "From:/Göndərən:"):
        check(phrase in brief, f"rule 3 names {phrase!r}")
    az = _language_clause("az")
    check(all(f"{a} (not {t})" in az for t, a in TURKISH_ONLY_FORMS.items()),
          "the Azerbaijani clause lists every Turkish form the validator rejects")


def test_fix6b_label_tokens() -> None:
    """The taxonomy-label check matches label TOKENS, as its docstring says."""
    from piigen.llm.quality import find_label_name_leak
    for text, want in [("Ad: GIVENNAME: Fatimə", ["GIVENNAME"]),
                       ("AZ_PASSPORT_NUMBER: O69367632", ["AZ_PASSPORT_NUMBER"]),
                       ("REG_DATE=2020", ["DATE"]), ("ATTR_GIVENNAME", ["GIVENNAME"]),
                       ("DATE: 12.05.2020", ["DATE"]), ("TIMESTAMP 10:00", []),
                       ("MESSAGE AGENT", []), ("STORAGE UPDATE", []), ("CAPACITY 5", []),
                       ("ERR_TIMEOUT", [])]:
        check(find_label_name_leak(text, []) == want, f"label leak in {text!r}: {want}",
              find_label_name_leak(text, []))
    rej = rejects1()
    if rej:
        hits = [r for r in rej if r["reason"].startswith("taxonomy label leaked")]
        still = sum(1 for r in hits if find_label_name_leak(r["text"], r.get("entities") or []))
        check(len(hits) == 205 and still == 63,
              f"batch 1: {still} of {len(hits)} label-leak rejections are real tokens", still)


def test_clean_drops_never_edits() -> None:
    """scripts/clean_llm_batch.py on three batch-1 records: an unlabelled
    planned street, a PII-free document too short on Azerbaijani words, and
    a sound one. The first two go, the third is kept byte for byte."""
    import subprocess
    import tempfile
    recs = batch1()
    if not recs:
        return
    raw = {json.loads(line)["id"]: line for line in BATCH1.open(encoding="utf-8")}
    pick = ["llm_az_000010", "llm_az_000192", "llm_az_009343"]
    with tempfile.TemporaryDirectory() as tmp:
        batch = Path(tmp) / "mini.jsonl"
        batch.write_text("".join(raw[i] for i in pick), encoding="utf-8")
        run = subprocess.run([sys.executable, str(ROOT / "scripts" / "clean_llm_batch.py"), str(batch)],
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        clean = batch.with_suffix(".clean.jsonl").read_text(encoding="utf-8")
        report = json.loads(batch.with_suffix(".clean.report.json").read_text(encoding="utf-8"))
        unchanged = batch.read_text(encoding="utf-8") == "".join(raw[i] for i in pick)
    dropped = {d["id"]: d["reasons"] for d in report["dropped_documents"]}
    check(run.returncode == 0 and clean == raw["llm_az_009343"],
          "the sound record is kept, byte for byte, and both gates pass", run.stdout[-300:])
    check(set(dropped) == {"llm_az_000010", "llm_az_000192"}
          and "validate_corpus:planned_value_unlabelled" in dropped["llm_az_000010"]
          and "validate_corpus:validator_failure" in dropped["llm_az_000192"],
          "the unlabelled street and the wordless PII-free document are dropped, with reasons", dropped)
    check(unchanged, "the input batch is only read")


def test_line_wrap_mid_word() -> None:
    """noise `line_wrap` hyphenates mid-word only: a wrap after an entity's
    last letter left `-\\n` inside the span (`...2021-CI IL-\\n`), which
    validation rejects. Found when fix 4's new draws reached it."""
    from piigen.noise import NoiseInjector

    class AlwaysWrap(random.Random):
        def random(self):
            return 0.0

        def choice(self, seq):
            return 64

    text = "x" * 59 + " Bakı yolu bağlıdır, Gəncə tərəfə getmək olmur heç cür indi."
    ents = [{"start": 60, "end": 64, "label": "CITY", "text": "Bakı"}]
    out, moved = NoiseInjector(GeneratorConfig(), AlwaysWrap())._line_wrap(text, ents, [], "az")
    check(moved[0]["text"] == "Bakı" and "Bakı-\n" not in out,
          "no wrap after a word's last letter", (moved[0]["text"], out[55:70]))
    check("-\n" in out, "a wrap still happens mid-word further on", out[60:])


TESTS = [("fix 2: capitals after labelling do not drift", test_fix2_caps),
         ("noise line_wrap: mid-word only", test_line_wrap_mid_word),
         ("clean_llm_batch: drops, never edits", test_clean_drops_never_edits),
         ("fix 6b: label tokens, not substrings", test_fix6b_label_tokens),
         ("fix 6: parser and brief", test_fix6_prompt_and_parser),
         ("fix 5: keyword share on the secret material", test_fix5_keyword),
         ("fix 3: the gate's language rule at generation", test_fix3_language),
         ("fix 4: rates as shares of all documents (12,000 offline briefs)", test_fix4_rates)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}" + (f"   SKIPPED {SKIP}" if SKIP else ""))
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
