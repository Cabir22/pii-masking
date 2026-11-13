"""Planned values in the form the LLM wrote (P2-5 audit, P2-6 fix 1).

No network, no model, no API key.

    python scripts/piigen/test_planned_values.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.resolver import (find_unlabelled_planned, match_key,  # noqa: E402
                             planned_forms, resolve_claims)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def forms(text: str, label: str, value: str) -> list[tuple[str, bool]]:
    return [(text[f.start:f.end], f.labelable) for f in planned_forms(text, label, value)]


def span(text: str, sub: str) -> tuple[int, int]:
    i = text.index(sub)
    return i, i + len(sub)


def ent(text: str, label: str, sub: str) -> dict:
    s, e = span(text, sub)
    return {"start": s, "end": e, "label": label, "text": sub}


# Every form batch 1 wrote for a planned value (2026-10-02/03), as found in
# the accepted documents: labellable ones, and traces that must reject.
CASES = [
    # (text, label, planned value, expected surface, labellable)
    ("Yaşayış ünvanı: Vaqif Məmmədov küçəsində, bina 197.", "STREET",
     "Vaqif Məmmədov küç.", "Vaqif Məmmədov küçəsində", True),
    ("Ünvan: Göyəmtala küçəsindəki mənzil.", "STREET",
     "Göyəmtala küç.", "Göyəmtala küçəsindəki", True),
    ("OPERATOR: VÜQAR TOFIQOĞLU KÜÇ.DƏDIR, DÜZDÜR?", "STREET",
     "Vüqar Tofiqoğlu küç.", "VÜQAR TOFIQOĞLU KÜÇ.DƏDIR", True),
    ("Unvan: Xeqani Aslanov kuc.inde yaşayır.", "STREET",
     "Xəqani Aslanov küç.", "Xeqani Aslanov kuc.inde", True),
    ("Unvan tesdiqlendi: Şehriyar prospektindeki merkez.", "STREET",
     "Şəhriyar prospekti", "Şehriyar prospektindeki", True),
    ("ünvan Vidadi Babanlı pr.-da yaşayıram", "STREET",
     "Vidadi Babanlı pr.", "Vidadi Babanlı pr.", True),
    ("2020-cu ildən bəri İsağın nömrəsi belədir.", "GIVENNAME", "İsaq", "İsağın", True),
    ("Gülyanağın göstərdiyi loq.", "GIVENNAME", "Gülyanaq", "Gülyanağın", True),
    ("ONLAR ŞƏMKIRDƏDIR. OFIS", "CITY", "Şəmkir", "ŞƏMKIRDƏDIR", True),
    ("Gence tərəfe gedeceyik.", "CITY", "Gəncə", "Gence", True),
    ("Şəhər: Xirdalanda nəticələr.", "CITY", "Xırdalan", "Xirdalanda", True),
    ("Abasət Şadkamovla söhbət etdik.", "SURNAME", "Şadkamov", "Şadkamovla", True),
    ("Siyəzəndəki çatdırılma pozuldu.", "CITY", "Siyəzən", "Siyəzəndəki", True),
    ("Əsgərgilə getdik.", "GIVENNAME", "Əsgər", "Əsgərgilə", True),
    ("Nömrəm 099  274 86 12-dir.", "TELEPHONENUM", "099 274 86 12", "099  274 86 12", True),
    ("Doğum tarixi? Şənbə, 27 avqust 1949.", "DATE", "şənbə, 27 avqust 1949",
     "Şənbə, 27 avqust 1949", True),
    # traces: present, but not labellable exactly -> the document is rejected
    ("Hacıqabılda baş vermiş xəta.", "CITY", "Hacıqabul", "Hacıqabılda", False),
    ("Sistemdə Dadaşağayevənin icazələri.", "SURNAME", "Dadaşağayeva", "Dadaşağayevənin", False),
    ("Xüsusilə, Мабудзаdanın yazdığı hissə.", "SURNAME", "Мабудзада", "Мабудзаdanın", False),
    ("Giriş tokeni: tok_EzguTQ5cSpN0TOVBazxbwpN2TY6abJr_aTufCT.", "ACCESS_TOKEN",
     "tok_EzguTQ5cSpN0TOBlVBazxbwpN2TY6abJr_aTufCT", "tok_EzguTQ5c", False),
    ("Mən Aşur Həsənbalayev prospek- tindəki mərkəzə getdim.", "STREET",
     "Aşur Həsənbalayev prospekti", "Aşur Həsənbalayev prospek-", False),
    ("Bu il bahar tez gəldi.", "GIVENNAME", "Bahar", "bahar", False),
]


def test_forms() -> None:
    for text, label, value, surface, labelable in CASES:
        got = forms(text, label, value)
        check((surface, labelable) in got, f"{value!r} written {surface!r}: labellable={labelable}", got)


def test_collisions() -> None:
    """resolver.py's own collision rules hold for planned values too."""
    check(forms("Əliyev zəng etdi.", "GIVENNAME", "Əli") == [], "Əliyev does not admit Əli")
    check(forms("Əliağa zəng etdi.", "GIVENNAME", "Əli") == [], "Əliağa does not admit Əli")
    check(forms("Adəm gəldi.", "GIVENNAME", "Ad") == [], "Adəm is not Ad + əm")
    check(forms("Bakılı dostum gəldi.", "CITY", "Bakı") == [],
          "bakılı (native of Baku) stays unlabelled (user decision, P2-4c)")
    check(forms("Salam elvin, necəsən?", "GIVENNAME", "Elvin") == [("elvin", True)],
          "a lowercase name that is no common word is still the name")
    check(forms("Səadətli günlər!", "GIVENNAME", "Səadət") == [],
          "the value plus a derivational suffix is another word (Səadətli 'happy')")
    check(forms("Bu səadətli günlər idi.", "GIVENNAME", "Səadət") == [],
          "a lowercase common word sharing a stem is not a misspelt name")
    check(forms("Ağarzayevin koodu əladır.", "SURNAME", "Ağarzayeva") == [("Ağarzayevin", False)],
          "a changed ending (the other gender, batch 1) is a trace: present, not labellable")
    check(forms("Ağarzayeva zəng etdi.", "SURNAME", "Ağarzayev") == [("Ağarzayeva", True)],
          "...while Ağarzayev + a is also its dative: labelled, a surname either way")


def test_reproducible() -> None:
    """Every labellable form is re-placed exactly by resolve_claims from its
    own text: what fix 1 labels can never show up as resolver_drift."""
    for text, label, value, _surface, _ok in CASES:
        for f in planned_forms(text, label, value):
            if not f.labelable:
                continue
            got, _ = resolve_claims(text, [{"label": label, "text": text[f.start:f.end]}])
            check([(g["start"], g["end"]) for g in got] == [(f.start, f.end)],
                  f"{text[f.start:f.end]!r} re-resolves to itself", got)


def test_unlabelled() -> None:
    text = "Bakıda yaşayıram, Bakının mərkəzində."
    ents = [ent(text, "CITY", "Bakıda"), ent(text, "CITY", "Bakının")]
    check(find_unlabelled_planned(text, ents, [("CITY", "Bakı")]) == [],
          "a value labelled only in inflected forms is labelled (the 1,707 false rejections)")
    check(len(find_unlabelled_planned(text, ents[:1], [("CITY", "Bakı")])) == 1,
          "...and each occurrence counts: the second one unlabelled is reported")
    text = "Müştəri Vaqif Məmmədov küçəsində yaşayır."
    found = find_unlabelled_planned(text, [], [("STREET", "Vaqif Məmmədov küç.")])
    check([f["text"] for f in found] == ["Vaqif Məmmədov küçəsində"], "an unlabelled street form is reported", found)
    # the older verbatim rule is kept
    text = "Müştərinin daxili istinad nömrəsi REF340012 arxivdə saxlanılır."
    check(find_unlabelled_planned(text, [], [("AGE", "34")]) != [],
          "a planned value only embedded in another token is still reported")
    check(find_unlabelled_planned(text, [], [("AGE", "34")], [span(text, "REF340012")]) == [],
          "...unless it is inside a declared decoy")
    text = "Bakı layihəsi üzrə hesabat hazırdır."
    check(find_unlabelled_planned(text, [], [("CITY", "Bakı")], [span(text, "Bakı layihəsi")]) == [],
          "a planned value inside a declared decoy is the decoy, not the value")
    text = "Ünvan: Nizami küçəsi 5."
    check(find_unlabelled_planned(text, [ent(text, "STREET", "Nizami küçəsi")],
                                  [("GIVENNAME", "Nizami")]) == [],
          "a planned name inside another label's span is not a separate mention")
    check(match_key("İSMAYILLI") == match_key("İsmayıllı") == "ismayilli"
          and len(match_key("İ")) == 1, "match_key folds case and diacritics one-for-one")


# --------------------------------------------------------------------------- #
# P2-6 fix 1: label every labellable form, reject the rest, gate it
# --------------------------------------------------------------------------- #
PROSE = ("Hörmətli müştəri, sizin müraciətiniz qəbul edildi və yaxın günlərdə "
         "nəzərdən keçiriləcək. Sənədlərin surətini də əlavə etməyinizi xahiş edirik. ")


def test_resolution() -> None:
    from piigen.resolver import resolve_planned
    text = ("Müştəri Vaqif Məmmədov küçəsində yaşayır. Gülyanaq gəldi, Gülyanağın sənədi "
            "hazırdır, Gülyanaq-a dedim. Sarracov-un ərizəsi də var. ONLAR ŞƏMKIRDƏDIR. "
            "Hacıqabılda xəta olub.")
    planned = [("STREET", "Vaqif Məmmədov küç."), ("GIVENNAME", "Gülyanaq"),
               ("SURNAME", "Sarracov"), ("CITY", "Şəmkir"), ("CITY", "Hacıqabul")]
    ents, nowhere = resolve_planned(text, planned)
    got = [(e["label"], e["text"]) for e in ents]
    for want in [("STREET", "Vaqif Məmmədov küçəsində"), ("GIVENNAME", "Gülyanağın"),
                 ("SURNAME", "Sarracov"), ("CITY", "ŞƏMKIRDƏDIR")]:
        check(want in got, f"resolve_planned labels {want[1]!r}", got)
    check(got.count(("GIVENNAME", "Gülyanaq")) == 2,
          "exact, softened (Gülyanağın) and hyphen-dative (Gülyanaq-a) occurrences all labelled", got)
    check(not any(t == "Hacıqabılda" for _l, t in got), "a misspelling is never labelled")
    check(nowhere == 1, "the misspelt city is the one value placed nowhere", nowhere)
    left = find_unlabelled_planned(text, ents, planned)
    check([f["text"] for f in left] == ["Hacıqabılda"], "...and is what find_unlabelled_planned reports", left)
    # resolve_claims tries every spelling (P2-6): exact AND softened in one document
    text = "Gülyanaq gəldi. Gülyanağın sənədi hazırdır."
    got, _ = resolve_claims(text, [{"label": "GIVENNAME", "text": "Gülyanaq"}])
    check([g["text"] for g in got] == ["Gülyanaq", "Gülyanağın"],
          "resolve_claims labels the softened genitive although the exact form placed first", got)
    text = "Saat 3:28 PM idi. [2025-05-14 03:28 PM] - saat 3:28 PM."
    got, _ = resolve_claims(text, [{"label": "TIME", "text": "3:28 PM"}])
    check([g["text"] for g in got] == ["3:28 PM", "3:28 PM"]
          and find_unlabelled_planned(text, got, [("TIME", "3:28 PM")]) == [],
          "TIME: the exact planned form wins; a zero-padded log timestamp is not the value", got)
    text = "Görüş saat 07:34 AM-də olacaq."
    got, _ = resolve_claims(text, [{"label": "TIME", "text": "7:34 AM"}])
    check([g["text"] for g in got] == ["07:34 AM"]
          and find_unlabelled_planned(text, got, [("TIME", "7:34 AM")]) == [],
          "...and where it is absent the zero-padded spelling is the value", got)


def _spec(entities, band="medium", negative_only=False):
    from piigen.llm.specs import DocumentSpec, PlannedEntity
    lo, hi = {"short": (150, 400), "medium": (400, 1100)}[band]
    return DocumentSpec(index=7, lang="az", doc_type="customer_email",
                        doc_type_hint="an email", register="formal", band=band,
                        min_chars=lo, max_chars=hi, length_hint="", seed=11,
                        entities=[PlannedEntity(lab, val) for lab, val in entities],
                        negative_only=negative_only)


def test_assemble() -> None:
    from piigen.config import GeneratorConfig
    from piigen.llm.pipeline import assemble_document
    cfg = GeneratorConfig()
    text = (PROSE + "Ünvan: Vaqif Məmmədov küçəsində yerləşən ofis. Bakıda yaşayan "
            "müştərimiz Bakının mərkəzində işləyir və Lalə xanım sizinlə əlaqə saxlayacaq. " + PROSE)
    out = assemble_document(_spec([("STREET", "Vaqif Məmmədov küç."), ("CITY", "Bakı"),
                                   ("GIVENNAME", "Lalə")]), text, cfg, 0.0)
    check(out.ok, "a document with küç. written küçəsində and Bakı only inflected is accepted",
          out.reason)
    if out.ok:
        got = [(e["label"], e["text"]) for e in out.record["entities"]]
        check(("STREET", "Vaqif Məmmədov küçəsində") in got and ("CITY", "Bakıda") in got
              and ("CITY", "Bakının") in got, "...with the street and both inflected cities labelled", got)
        check(out.dropped_labels == [], "...and no planned label counted as dropped", out.dropped_labels)
    text = (PROSE + "Hacıqabılda baş vermiş texniki xəta haqqında Lalə xanım bizə məlumat verdi. " + PROSE)
    out = assemble_document(_spec([("CITY", "Hacıqabul"), ("GIVENNAME", "Lalə")]), text, cfg, 0.0)
    check(not out.ok and "planned value never labeled (CITY, misspelled)" in out.reason,
          "a misspelt planned city rejects the document", out.reason)


def test_gate() -> None:
    import json
    import subprocess
    import tempfile
    script = Path(__file__).resolve().parents[1] / "validate_corpus.py"
    good = PROSE + "Ünvan: Vaqif Məmmədov küçəsində yerləşən ofis. " + PROSE
    s = good.index("Vaqif")
    e = s + len("Vaqif Məmmədov küçəsində")
    spec = {"entities": [{"label": "STREET", "value": "Vaqif Məmmədov küç."}]}
    recs = [{"id": "ok", "text": good, "lang": "az", "_spec": spec,
             "entities": [{"start": s, "end": e, "label": "STREET", "text": good[s:e]}]},
            {"id": "bad", "text": good.replace("Ünvan", "Yer"), "lang": "az", "_spec": spec,
             "entities": [{"start": s - 4, "end": s - 1, "label": "STREET", "text": "Yer"}]}]
    recs[1]["entities"] = []
    recs[1]["_pii_free"] = True
    with tempfile.TemporaryDirectory() as tmp:
        corpus = Path(tmp) / "c.jsonl"
        corpus.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs), encoding="utf-8")
        report = Path(tmp) / "r.json"
        run = subprocess.run([sys.executable, str(script), str(corpus), "--skip-dedup",
                              "--json", str(report)], capture_output=True, text=True,
                             encoding="utf-8")
        counts = json.loads(report.read_text(encoding="utf-8"))["counts"]
    check(run.returncode == 1 and counts.get("planned_value_unlabelled") == 1,
          "validate_corpus: planned_value_unlabelled is MUST-BE-ZERO and fires once, on the bad record",
          (run.returncode, counts))
    check(not counts.get("resolver_drift"), "...and the labelled street form does not drift", counts)


TESTS = [("forms the LLM wrote (batch 1)", test_forms), ("collision rules", test_collisions),
         ("labellable forms re-resolve to themselves", test_reproducible),
         ("unlabelled planned values", test_unlabelled),
         ("fix 1: resolve_planned", test_resolution),
         ("fix 1: assemble_document labels or rejects", test_assemble),
         ("fix 1: validate_corpus planned_value_unlabelled", test_gate)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
