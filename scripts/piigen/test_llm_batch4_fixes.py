"""Fixes from the LLM batch-4 audit (P2-5, batch 4).

No network, no model, no API key. Checks that read a batch are skipped when
its file is not pulled.

    python scripts/piigen/test_llm_batch4_fixes.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW4 = ROOT / "data" / "raw" / "sprint1_llm_b4.jsonl"
PASS = FAIL = SKIP = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def batch4() -> list[dict] | None:
    global SKIP
    if not RAW4.exists() or RAW4.stat().st_size < 10_000:
        SKIP += 1
        return None
    return [json.loads(line) for line in RAW4.open(encoding="utf-8")]


# --------------------------------------------------------------------------- #
def test_invented_emails() -> None:
    """Company mailboxes invented with Azerbaijani letters or an underscored
    host are leaked PII like any other email (44 in clean batch 1)."""
    from piigen.llm.quality import find_leaked_pii
    for text, email in [("Yazın: dəstək@hal-x.ai ünvanına.", "dəstək@hal-x.ai"),
                        ("Əlaqə: hüquq@şirkət.az, sağ olun.", "hüquq@şirkət.az"),
                        ("support@bank_system.az yazın", "support@bank_system.az"),
                        ("DƏSTƏK@RKK.AZ ünvanı", "DƏSTƏK@RKK.AZ"),
                        ("E-poçt: test.user@example.com.", "test.user@example.com")]:
        check(find_leaked_pii(text, []) == [f"EMAIL:{email}"], f"leaked email: {email}",
              find_leaked_pii(text, []))
    for text in ("user@kjunjx", "krbqv [at] urdixt [dot] com", "@Nurbacı salam", "v1.2@build",
                 "npm@latest yükləndi"):
        check(not find_leaked_pii(text, []), f"not an email: {text!r}", find_leaked_pii(text, []))
    text = "Əlaqə: dəstək@hal-x.ai"
    i = text.index("dəstək")
    labelled = [{"start": i, "end": len(text), "label": "EMAIL", "text": text[i:]}]
    check(not find_leaked_pii(text, labelled), "a labelled one is not a leak")
    recs = batch4()
    if recs:
        from piigen.validate import declared_decoy_spans
        hit = [r["id"] for r in recs if any(
            "@" in x and any(ord(c) > 127 or c == "_" for c in x.split("@")[1])
            or any(ord(c) > 127 for c in x.split("@")[0])
            for x in find_leaked_pii(r["text"], r["entities"],
                                     decoy_spans=declared_decoy_spans(r)[0]))]
        check(len(hit) == 8, "raw batch 4: 8 documents with such an email", (len(hit), hit[:3]))


def test_corrupt_text() -> None:
    from piigen.validate import corrupt_text, validate_example
    for text in ("muqavilenin legvine esasな ola biler", "Kod 居 yazılıb", "xəta ت oldu",
                 "Bu sened (noise) sizin üçündür"):
        check(corrupt_text(text), f"corrupt: {text!r}")
    for text in ("Məbləğ 45 ₼, № 5, 37 °C, 5 µg", "﻿Salam", "Мамедов Əli", "Türkçe şöyle 😀"):
        check(not corrupt_text(text), f"not corrupt: {text!r}", corrupt_text(text))
    rec = {"text": "Hörmətli müştəri, müraciətiniz qəbul edildi və tezliklə baxılacaq. "
                   "Sənəd 居 nömrəsi ilə qeydə alınıb, gözləyin.", "lang": "az", "entities": []}
    check(any(p.startswith("corrupt_text") for p in validate_example(rec)),
          "validate_example reports it (so generation rejects and cleaning drops it)",
          validate_example(rec))


def test_noise_language_net() -> None:
    """Noise that alone makes a document fail the language gate is undone."""
    from piigen.config import GeneratorConfig
    from piigen.noise import NoiseInjector
    from piigen.text import fold_diacritics
    from piigen.validate import language_ok
    # the shape of a batch-4 very short document: field lines, whose only
    # Azerbaijani evidence is its letters
    text = "Abonent: Qəhrəman\nİndeks: AZ59 227902\n> Ödəniş tələb olunur\nHesabın qalıq məbləği..."
    check(language_ok(text, "az")[0] and not language_ok(fold_diacritics(text), "az")[0],
          "the fixture: passes as written, fails once folded")

    class Folds(NoiseInjector):
        def maybe_apply(self, text, entities, lang, rate=None):
            return fold_diacritics(text), entities, ["strip_diacritics"]

    out, ents, kept, applied = Folds(GeneratorConfig(), random.Random(1)).apply_protected(
        text, [], [], "az", rate=1.0)
    check(out == text and applied == [], "the document ships un-noised", (out, applied))
    long_text = ("Hörmətli müştəri, sizin müraciətiniz qəbul edildi və yaxın günlərdə nəzərdən "
                 "keçiriləcək. Sənədlərin surətini də əlavə etməyinizi xahiş edirik. ") * 2
    out, _e, _k, applied = Folds(GeneratorConfig(), random.Random(1)).apply_protected(
        long_text, [], [], "az", rate=1.0)
    check(applied == ["strip_diacritics"], "a document that still passes keeps its noise",
          applied)
    recs = batch4()
    if recs:
        from piigen.validate import declared_decoy_spans
        short = [r for r in recs if r["_spec"]["band"] in ("very_short", "short")
                 and not r.get("_noise")][:600]
        failing = 0
        for k, r in enumerate(short):
            out, _e, _k, _a = NoiseInjector(GeneratorConfig(), random.Random(k)).apply_protected(
                r["text"], [dict(e) for e in r["entities"]],
                [{"start": s, "end": e} for s, e in declared_decoy_spans(r)[0]], "az", rate=1.0)
            failing += not language_ok(out, "az")[0]
        check(failing == 0, "batch 4: 600 short documents, noised, none fails the language gate",
              failing)


def test_briefs() -> None:
    from piigen.config import GeneratorConfig
    from piigen.llm import specs as S
    from piigen.llm.dspy_generate import build_fields
    from piigen.values import ValueFactory, ValuePool
    check(S._DROP_DIACRITICS in S.NOISE_DIRECTIVES, "the diacritics directive exists")
    check(S._DROP_DIACRITICS not in S.noise_directives("very_short")
          and S._DROP_DIACRITICS not in S.noise_directives("short")
          and S._DROP_DIACRITICS in S.noise_directives("medium"),
          "short briefs never get the diacritics directive; longer ones may")
    typo = next(d for d in S.NOISE_DIRECTIVES if "typos" in d)
    check("never inside a value" in typo, "typos stay out of the planned values", typo)
    cfg = GeneratorConfig()
    cfg.edge_case_rate, cfg.negative_only_rate = 0.3, 0.1
    sampler = S.SpecSampler(cfg, ValueFactory(random.Random(3), ValuePool(state_path=None)),
                            random.Random(5))
    briefs = [sampler.sample(i) for i in range(3000)]
    short_with = [b for b in briefs if b.band in ("very_short", "short") and S._DROP_DIACRITICS in b.noise]
    check(not short_with, "3,000 briefs: no short brief asks to drop diacritics", len(short_with))
    lines = []
    for b in briefs:
        if any(e.role == "document_date" for e in b.entities):
            text = build_fields(b)["entities_to_embed"]
            lines.append(next(x for x in text.splitlines() if "document's own date" in x))
    from piigen.llm.dspy_generate import _DOCUMENT_DATE_PLACEMENTS
    used = {p for p in _DOCUMENT_DATE_PLACEMENTS if any(p in x for x in lines)}
    tarix = sum('"Tarix: <date>"' in x for x in lines) / max(len(lines), 1)
    check(used == set(_DOCUMENT_DATE_PLACEMENTS) and tarix < 0.35,
          "document dates go to four placements, 'Tarix:' about a quarter", (len(used), round(tarix, 2)))


def test_misspelt_names() -> None:
    """A planned name misspelt inside the word is a form of it that cannot be
    labelled, so the document is rejected (generation) or dropped (cleaning),
    instead of keeping the real name unlabelled."""
    from piigen.resolver import find_unlabelled_planned, planned_forms
    for text, label, value, form in [
            ("System log: Seyidnovun (Seyidxanovun) məlumatı", "SURNAME", "Seyidxanov", "Seyidnovun"),
            ("Müxtərov bəy bildirib ki, hər şey qaydasındadır.", "SURNAME", "Müxtarov", "Müxtərov"),
            ("Zaqalatada problem var.", "CITY", "Zaqatala", "Zaqalatada"),
            ("Riyahi Minaxovun adına olan sənədlər", "SURNAME", "Minaxanov", "Minaxovun"),
            ("Hörmətlə, Esilxanov", "SURNAME", "Əslxanov", "Esilxanov"),
            ("Bildiyiniz kimi, Altayovanın avtomobili", "SURNAME", "Alatayova", "Altayovanın"),
            ("Bəyimacı (yox, Bəyimbacı) gəldi", "GIVENNAME", "Bəyimbacı", "Bəyimacı"),
            ("Müraciət edən: Rahşana aid sənədlər", "GIVENNAME", "Rahshan", "Rahşana")]:
        forms = [(text[f.start:f.end], f.kind, f.labelable) for f in planned_forms(text, label, value)]
        check((form, "misspelled", False) in forms, f"misspelt: {form} for {value}", forms)
    for text, label, value in [
            ("ÖDƏNİŞ KARTININ NÖMRƏSİ 4106", "GIVENNAME", "Növrəs"),     # a short name's first 3 letters
            ("Avadanlıqlar: evdəki bütün avadanlıqlar", "SURNAME", "Alaşanlı"),
            ("Hörmətli Sevinc xanım", "GIVENNAME", "Hörmət"),            # a derived word
            ("nəzarət şöbəsi", "GIVENNAME", "Nəzakət")]:                 # not capitalised
        bad = [text[f.start:f.end] for f in planned_forms(text, label, value) if f.kind == "misspelled"]
        check(not bad, f"not a misspelling of {value}: {text!r}", bad)
    text = "Müxtarovun müraciəti"
    check([(text[f.start:f.end], f.labelable) for f in planned_forms(text, "SURNAME", "Müxtarov")]
          == [("Müxtarovun", True)], "an inflected form is still labelled, not misspelt")
    recs = batch4()
    if recs:
        from piigen.validate import declared_decoy_spans
        hit = [r["id"] for r in recs if any(
            m["kind"] == "misspelled" for m in find_unlabelled_planned(
                r["text"], r["entities"], [(e["label"], e["value"]) for e in r["_spec"]["entities"]],
                declared_decoy_spans(r)[0]))]
        check(len(hit) == 9, "raw batch 4: 9 documents keep a misspelt planned name unlabelled",
              (len(hit), hit[:3]))


TESTS = [("invented emails with Azerbaijani letters", test_invented_emails),
         ("corrupt text: foreign script, '(noise)'", test_corrupt_text),
         ("noise never fails the language gate alone", test_noise_language_net),
         ("briefs: diacritics, typos, document-date placement", test_briefs),
         ("planned names misspelt inside the word", test_misspelt_names)]

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
