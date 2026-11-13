"""P2-6 generator fixes from the LLM batch-2 audit (P2-5), before batch 3.

No network, no model, no API key. Checks that read batch 2 itself are
skipped when data/raw/sprint1_llm_b2.jsonl is not pulled.

    python scripts/piigen/test_llm_batch2_fixes.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.resolver import (find_unlabelled_planned, planned_forms,  # noqa: E402
                             resolve_planned)

BATCH2 = ROOT / "data" / "raw" / "sprint1_llm_b2.jsonl"
PASS = FAIL = SKIP = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


_B2: list[dict] = []


def batch2() -> list[dict] | None:
    global SKIP
    if not BATCH2.exists() or BATCH2.stat().st_size < 10_000:   # absent, or an LFS pointer
        SKIP += 1
        return None
    if not _B2:
        _B2.extend(json.loads(line) for line in BATCH2.open(encoding="utf-8"))
    return _B2


def forms(text: str, label: str, value: str) -> list[tuple[str, bool]]:
    return [(text[f.start:f.end], f.labelable) for f in planned_forms(text, label, value)]


def ent(text: str, label: str, sub: str) -> dict:
    i = text.index(sub)
    return {"start": i, "end": i + len(sub), "label": label, "text": sub}


# --------------------------------------------------------------------------- #
def test_reformatted_dates() -> None:
    """A planned date written in another format is the same calendar day:
    found, and labellable when the gate's DATE rule accepts that surface."""
    cases = [
        ("Doğum tarixi: 14.09.1991, qeydiyyat bitdi.", "1991-09-14", "14.09.1991"),
        ("Müqavilə 27 avqust 2021-ci il tarixində bağlandı.", "27.08.2021", "27 avqust 2021"),
        ("Sənəd 14 noyabr 1991 tarixində verilib.", "1991-11-14", "14 noyabr 1991"),
        ("Tarix: 2015-05-14, imzalandı.", "14.05.2015", "2015-05-14"),
        ("Tarix: 14/05/2015, imzalandı.", "14.05.2015", "14/05/2015"),
    ]
    for text, value, written in cases:
        got = forms(text, "DATE", value)
        check((written, True) in got, f"DATE {value!r} written {written!r} is found and labellable", got)
        miss = find_unlabelled_planned(text, [], [("DATE", value)])
        check(any(f["text"] == written for f in miss),
              f"...and reported while unlabelled ({written!r})", miss)
        done = find_unlabelled_planned(text, [ent(text, "DATE", written)], [("DATE", value)])
        check(not done, f"...and not reported once labelled ({written!r})", done)


def test_dates_not_confused() -> None:
    """Another day, an ambiguous order and a version number stay unmatched."""
    check(not forms("Tarix: 15.09.1991.", "DATE", "1991-09-14"),
          "a different day is not the planned date")
    # day-first is the Azerbaijani order: 03.08.1981 is 3 August, not 8 March
    check(not forms("Tarix: 03.08.1981.", "DATE", "1981-03-08"),
          "03.08.1981 is read day first, so it is not 1981-03-08")
    check(("08.03.1981", True) in forms("Tarix: 08.03.1981.", "DATE", "1981-03-08"),
          "...and 08.03.1981 is")
    check(not forms("Versiya v2.14.09.1991 yükləndi.", "DATE", "1991-09-14"),
          "a date-shaped piece of a version string is not a date")
    check(not forms("Tarix: 31.02.2020.", "DATE", "2020-02-31"),
          "an impossible planned date has no other spelling")


def test_reformatted_date_labelled() -> None:
    """resolve_planned labels the reformatted copy, so generation keeps it."""
    text = "Tarix: 2015-05-14. Təkrar: doğum tarixi 14.05.2015 kimi yazılıb."
    ents, dropped = resolve_planned(text, [("DATE", "2015-05-14")])
    got = sorted(text[e["start"]:e["end"]] for e in ents if e["label"] == "DATE")
    check(got == ["14.05.2015", "2015-05-14"], "both spellings of the planned date are labelled",
          (got, dropped))


def test_at_mention() -> None:
    """`@Nurbacı` in a chat is the planned name (an `@` is a boundary for the
    four name labels, as resolve_claims already treats it)."""
    text = "Salam @Nurbacı, sabah görüşək. Nurbacı da gələcək."
    got = forms(text, "GIVENNAME", "Nurbacı")
    check(sum(1 for t, lab in got if t == "Nurbacı" and lab) == 2,
          "the @-mention and the plain mention are both labellable", got)
    plain = text.index("Nurbacı da")
    labelled = [{"start": plain, "end": plain + 7, "label": "GIVENNAME", "text": "Nurbacı"}]
    miss = find_unlabelled_planned(text, labelled, [("GIVENNAME", "Nurbacı")])
    check(len(miss) == 1 and miss[0]["start"] == text.index("@") + 1,
          "only the @-mention is reported when it is left unlabelled", miss)
    check(not forms("Hesab: user@Nurbacı yoxdur.".replace("user@", "x"), "GIVENNAME", "Nurbacı"),
          "a name glued to a word is still not the planned name")
    for mail in ("Ünvan: info@bakı.az, Bakı ofisi.", "Ünvan: info@baki-ofis.az, Bakı ofisi."):
        found = planned_forms(mail, "CITY", "Bakı")
        check([mail[f.start:f.end] for f in found] == ["Bakı"]
              and not any(mail[f.start - 1] == "@" for f in found),
              "an email domain after @ is not a mention of the planned CITY",
              [(mail[f.start:f.end], f.kind) for f in found])


def test_batch2_dates() -> None:
    """Batch 2: the reformatted dates the old check missed are all found."""
    recs = batch2()
    if not recs:
        return
    hits = []
    for r in recs:
        planned = [(e["label"], e["value"]) for e in r["_spec"]["entities"]]
        for f in find_unlabelled_planned(r["text"], r["entities"], planned):
            hits.append((r["id"], f["label"], f["kind"]))
    dates = [h for h in hits if h[1] == "DATE"]
    check(len(dates) >= 30 and all(k.startswith("reformatted") for _, _, k in dates),
          "batch 2: 30+ unlabelled reformatted dates are found", (len(dates), hits[:5]))


def test_noise_keeps_records_resolvable() -> None:
    """Noise that loses an entity, or leaves one that resolve_claims cannot
    place again, is undone: batch 2 shipped one record with its only entity
    typo'd away (llm_az_004213) and one that drifts (llm_az_005216)."""
    import random

    from piigen.config import GeneratorConfig
    from piigen.noise import NoiseInjector, _still_resolvable

    text = "Ünvan: Nizami küçəsi, bina 61. Zəng: +994 55 374 27 11."
    ents = [ent(text, "BUILDINGNUM", "61"), ent(text, "TELEPHONENUM", "+994 55 374 27 11")]
    check(_still_resolvable(text, ents, 2, 0), "an intact record is resolvable")
    check(not _still_resolvable(text, ents[1:], 2, 0), "a lost entity is caught")
    bad = text.replace("bina 61.", "bina 61-dirr.")
    moved = [ent(bad, "BUILDINGNUM", "61"), ent(bad, "TELEPHONENUM", "+994 55 374 27 11")]
    check(not _still_resolvable(bad, moved, 2, 0),
          "a span resolve_claims no longer places (`61-dirr`) is caught")

    class Breaks(NoiseInjector):
        def maybe_apply(self, text, entities, lang, rate=None):
            return bad, [moved[0], moved[1]] + entities[2:], ["typos"]

    out, got, kept, applied = Breaks(GeneratorConfig(), random.Random(1)).apply_protected(
        text, ents, [], "az", rate=1.0)
    check(out == text and got == ents and applied == [],
          "apply_protected ships the record un-noised instead", (out, applied))

    applied_n = 0
    for seed in range(200):
        out, got, _, applied = NoiseInjector(GeneratorConfig(), random.Random(seed)).apply_protected(
            text, ents, [], "az", rate=1.0)
        applied_n += bool(applied)
        if not _still_resolvable(out, got, 2, 0):
            check(False, "every noised record is resolvable", (seed, out))
            break
    check(applied_n >= 150, "noise is still applied to most records", applied_n)

    recs = batch2()
    if recs:
        from piigen.noise import _PROTECT_TAG
        from piigen.validate import declared_decoy_spans
        r = next(r for r in recs if r["id"] == "llm_az_005216")
        decoys, _ = declared_decoy_spans(r)
        merged = r["entities"] + [{"start": s, "end": e, "label": f"{_PROTECT_TAG}{i}"}
                                  for i, (s, e) in enumerate(decoys)]
        check(not _still_resolvable(r["text"], merged, len(r["entities"]), len(decoys)),
              "batch 2: llm_az_005216 as shipped would have been refused")


PROSE = ("Hörmətli müştəri, sizin müraciətiniz qəbul edildi və yaxın günlərdə "
         "nəzərdən keçiriləcək. Sənədlərin surətini də əlavə etməyinizi xahiş edirik. ")


def _spec(entities, band="medium"):
    from piigen.llm.specs import DocumentSpec, PlannedEntity
    lo, hi = {"short": (150, 400), "medium": (400, 1100)}[band]
    return DocumentSpec(index=7, lang="az", doc_type="customer_email",
                        doc_type_hint="an email", register="formal", band=band,
                        min_chars=lo, max_chars=hi, length_hint="", seed=11,
                        entities=[PlannedEntity(lab, val) for lab, val in entities])


def test_invented_pii() -> None:
    """D-15c follow-up: PII the model invented (unplanned, so unlabelled) is
    rejected at generation, with the definition cleaning drops it by."""
    from piigen.audit_llm_batch import unplanned_pii
    from piigen.llm.quality_filter import screen_record

    def screen(text, entities=(), decoys=(), invented=True):
        rec = {"text": text, "lang": "az", "entities": list(entities), "_decoys": list(decoys)}
        return [p for p in screen_record(rec, run_base_gates=False, band="medium", planned=[],
                                         invented=invented) if p.startswith("invented PII")]

    text = PROSE + "Marşrut: Bakı-Sumqayıt. Yük təhvil verildi."
    check(screen(text) == ["invented PII (CITY): 'Bakı'", "invented PII (CITY): 'Sumqayıt'"],
          "two unlabelled cities are rejected", screen(text))
    check(not screen(text, invented=False), "...only when asked (the targeted builder is unchanged)")
    labelled = [ent(text, "CITY", "Bakı"), ent(text, "CITY", "Sumqayıt")]
    check(not screen(text, labelled), "...and not once they are labelled")
    decoy = [{**ent(text, "CITY", "Bakı-Sumqayıt"), "kind": "plain"}]
    check(screen(text, decoys=decoy) == [], "...nor inside a declared decoy", screen(text, decoys=decoy))
    for extra, label in (("Ünvan: Səməd Vurğun küçəsi, bina 12.", "STREET"),
                         ("Ünvan: Səməd Vurğun küçəsi, bina 12.", "BUILDINGNUM"),
                         ("Hörmətlə, Alxan Zeynullayev", "GIVENNAME"),
                         ("Tədbir Bakıda keçiriləcək.", "CITY")):
        got = screen(PROSE + extra)
        check(any(p.startswith(f"invented PII ({label})") for p in got),
              f"an invented {label} is rejected: {extra!r}", got)
    # D-51i: a city heading an institution is not a place (D-2, the R6)
    for plain in ("Dünya bankının hesabatı hazırdır.", "İnsan hüquqları haqqında məlumat.",
                  "Bakı Dövlət Universitetinin tələbəsi."):
        check(not screen(PROSE + plain), f"an ordinary capitalised word is not a name: {plain!r}",
              screen(PROSE + plain))

    from piigen.config import GeneratorConfig
    from piigen.llm.pipeline import assemble_document
    text = PROSE + "Lalə xanım Gəncədən zəng etdi, Şəki filialına isə sabah gedəcək. " + PROSE
    out = assemble_document(_spec([("GIVENNAME", "Lalə")]), text, GeneratorConfig(), 0.0)
    check(not out.ok and out.reason == "quality: invented PII (CITY)",
          "assemble_document rejects a document with a city nobody planned", out.reason)
    # D-51i: `Gəncədən` is a city too (inflected forms count), so both are planned
    out = assemble_document(_spec([("GIVENNAME", "Lalə"), ("CITY", "Gəncə"), ("CITY", "Şəki")]), text,
                            GeneratorConfig(), 0.0)
    check(out.ok, "...and accepts it once that city is planned (and labelled)", out.reason)

    recs = batch2()
    if recs:
        disagree = []
        for r in recs:
            got = screen_record(r, run_base_gates=False, band=r["_spec"]["band"], planned=[],
                                invented=True)
            if bool(unplanned_pii(r)) != any(p.startswith("invented PII") for p in got):
                disagree.append(r["id"])
        check(not disagree, "batch 2: generation rejects exactly the documents cleaning drops",
              disagree[:5])


def test_date_hint() -> None:
    """The brief no longer invites a re-spelt date or time: a value whose own
    shape licenses it is asked to keep that format; one that needs a context
    word gets the word and the same request."""
    from piigen.llm.dspy_generate import build_fields
    lines = build_fields(_spec([("DATE", "2015-05-14"), ("DATE", "14.05.2015"),
                                ("DATE", "5 fevral 1992-ci il"), ("TIME", "3:05 PM"),
                                ("TIME", "10:17"), ("AGE", "34")]))["entities_to_embed"]
    by_value = {line.split("   ")[0]: line for line in lines.splitlines()}
    check("dd.mm.yyyy" not in lines and "HH:MM" not in lines,
          "no hint offers another date or time format", lines)
    for key in ("DATE: 2015-05-14", "DATE: 14.05.2015", "TIME: 3:05 PM", "TIME: 10:17"):
        line = by_value.get(key, "")
        check("exactly this format" in line and "must appear next to" not in line,
              f"{key}: self-signalling, asked only to keep its format", line)
    line = by_value.get("DATE: 5 fevral 1992-ci il", "")
    check("\"tarix\"" in line and "exactly this format" in line,
          "a worded date keeps its anchor words and is asked to keep its format", line)
    line = by_value.get("AGE: 34", "")
    check("\"yaşı\"" in line and "format" not in line, "AGE's hint is unchanged", line)


def test_turkish_lookalikes() -> None:
    """Azerbaijani written without diacritics is not Turkish (for the team's
    review): `tesekkur` is folded `təşəkkür`, `lutfen` folded `lütfən`. The
    Turkish spellings, and folded forms only Turkish has, are still caught."""
    from piigen.validate import turkish_contamination

    def turkish(text):
        return any(p.startswith("turkish_lexis") for p in turkish_contamination(text))

    for az in ("Sizin dəstəyiniz üçün əvvəlcədən tesekkur edirik.",
               "Sualınız varsa, lutfen texniki dəstək komandasına müraciət edin.",
               "Cox tesekkur edirem, lutfen bir az gozleyin."):
        check(not turkish(az), f"Azerbaijani without diacritics is not Turkish: {az!r}")
    for tr in ("Yardımınız için teşekkür ederiz.", "Lütfen bekleyin.",
               "Menim ucun bu cox buyuk problemdir.", "Bu guzel bir gun idi.",
               "Bu degisiklik lazimdir.", "Bunun icin zəng edin.", "Önemli bildiriş."):
        check(turkish(tr), f"Turkish is still caught: {tr!r}")

    rejects = BATCH2.with_name("sprint1_llm_b2.rejects.jsonl")
    if not rejects.exists() or rejects.stat().st_size < 10_000:
        global SKIP
        SKIP += 1
        return
    rows = [json.loads(line) for line in rejects.open(encoding="utf-8")]
    was = [r for r in rows if "turkish_lexis" in (r.get("reason") or "")]
    still = [r for r in was if turkish(r["text"])]
    check(len(was) == 107 and len(was) - len(still) == 84,
          "batch 2: 84 of the 107 Turkish rejections were Azerbaijani without diacritics",
          (len(was), len(still)))


def test_short_brief() -> None:
    """Short documents with PII are asked for a real sentence around the
    values (201 of batch 2's 229 language rejections); longer ones and
    PII-free ones (which have their own request) are unchanged."""
    from piigen.llm.dspy_generate import build_fields
    from piigen.llm.specs import LENGTH_BANDS, DocumentSpec, PlannedEntity

    def hint(band, entities=(("AZ_FIN", "7Z78A12"),), negative_only=False):
        lo, hi = next((b[2], b[3]) for b in LENGTH_BANDS if b[0] == band)
        spec = DocumentSpec(index=1, lang="az", doc_type="support_ticket", doc_type_hint="x",
                            register="terse", band=band, min_chars=lo, max_chars=hi,
                            length_hint="one or two lines", seed=1, negative_only=negative_only,
                            entities=[PlannedEntity(lab, val) for lab, val in entities])
        return build_fields(spec)["length_hint"]

    for band in ("very_short", "short"):
        check("full sentence of ordinary Azerbaijani words" in hint(band),
              f"{band} with PII: the values go inside a real sentence", hint(band))
    check("sentence" not in hint("medium"), "medium: unchanged", hint("medium"))
    check("sentence" not in hint("very_short", (), True),
          "PII-free: unchanged here (fix 3 asks for two sentences)", hint("very_short", (), True))
    rejects = BATCH2.with_name("sprint1_llm_b2.rejects.jsonl")
    if rejects.exists() and rejects.stat().st_size > 10_000:
        rows = [json.loads(line) for line in rejects.open(encoding="utf-8")]
        short = [r for r in rows if "language" in (r.get("reason") or "")
                 and r.get("entities") and r.get("band") in ("very_short", "short")]
        check(len(short) == 201, "batch 2: 201 short documents with PII failed the language gate",
              len(short))


FIN_CONTEXT = (r"(?i)\bfin\b|fin[\s-]*kod|fərdi\s+identifikasiya|ferdi\s+identifikasiya"
               r"|şəxsiyyət|vəsiqə")


def test_fin_meaning() -> None:
    """The brief says what AZ_FIN is: batch 2 wrote most FINs as a
    financial, account or transaction code ("Maliyyə kodu: 4DW9Z35")."""
    import re

    from piigen.llm.dspy_generate import build_fields
    lines = build_fields(_spec([("AZ_FIN", "4DW9Z35"), ("AZ_VOEN", "6129601637"),
                                ("EMAIL", "a.b@mail.az")]))["entities_to_embed"].splitlines()
    fin = next(line for line in lines if line.startswith("AZ_FIN"))
    check("FİN kodu" in fin and "not a financial" in fin, "AZ_FIN's line says what a FIN is", fin)
    check(any(line == "AZ_VOEN: 6129601637" for line in lines)
          and any(line == "EMAIL: a.b@mail.az" for line in lines),
          "other labels' lines are unchanged", lines)

    # Measured on the raw batch, which never changes; the clean file shrinks
    # whenever a later audit drops more documents (99 of 416 at batch 2's
    # audit, 99 of 415 after batch 4's).
    if BATCH2.exists() and BATCH2.stat().st_size > 10_000:
        near = total = 0
        for line in BATCH2.open(encoding="utf-8"):
            r = json.loads(line)
            for e in r["entities"]:
                if e["label"] == "AZ_FIN":
                    total += 1
                    near += bool(re.search(FIN_CONTEXT, r["text"][max(0, e["start"] - 60):e["end"] + 30]))
        check(total == 434 and near == 102,
              "batch 2 (raw): 102 of 434 FINs stood near a FIN or ID-card word", (near, total))


TESTS = [("reformatted planned dates", test_reformatted_dates),
         ("dates that are not the planned one", test_dates_not_confused),
         ("resolve_planned labels a reformatted date", test_reformatted_date_labelled),
         ("@-mentions of a planned name", test_at_mention),
         ("batch 2: reformatted dates", test_batch2_dates),
         ("noise never ships an unresolvable record", test_noise_keeps_records_resolvable),
         ("D-15c: invented PII rejected at generation", test_invented_pii),
         ("brief: dates and times keep their format", test_date_hint),
         ("Turkish check: Azerbaijani look-alikes (review)", test_turkish_lookalikes),
         ("brief: short documents with PII need a real sentence", test_short_brief),
         ("brief: what AZ_FIN is", test_fin_meaning)]

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
