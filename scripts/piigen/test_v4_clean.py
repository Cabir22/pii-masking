"""D-51f/D-51g cleaning pass (piigen.v4_clean): every rule on positive and
negative fixtures, plus the invariants (text untouched, exact sorted spans,
deterministic, the input record not mutated, the gates still pass).

    python scripts/piigen/test_v4_clean.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.resolver import find_unlabeled_repeats, resolve_claims        # noqa: E402
from piigen.standalone_dates import is_timestamp                            # noqa: E402
from piigen.v4_clean import clean_doc, clean_doc_detail                     # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:400] if detail is not None else ""))


_N = 0


def rec(text: str, labels=(), *, old: bool = False, source: str = "llm", doc_type: str = "official_notice",
        decoys=(), spec=None) -> dict:
    """A record; `labels` are (value, label) or (value, label, occurrence)."""
    global _N
    _N += 1
    ents = []
    for item in labels:
        value, label = item[0], item[1]
        nth = item[2] if len(item) > 2 else 0
        i = -1
        for _ in range(nth + 1):
            i = text.index(value, i + 1)
        ents.append({"start": i, "end": i + len(value), "label": label, "text": value})
    r = {"id": f"t{_N}", "text": text, "lang": "az", "entities": sorted(ents, key=lambda e: e["start"]),
         "_doc_type": doc_type, "_source": source}
    if old:
        r["_old"] = True
    if decoys:
        r["_decoys"] = [dict(d) for d in decoys]
    if spec is not None:
        r["_spec"] = spec
    return r


def spans(doc: dict | None) -> list[tuple[str, str]]:
    return [] if doc is None else [(e["text"], e["label"]) for e in doc["entities"]]


def decoy_kinds(doc: dict | None) -> list[tuple[str, str]]:
    if doc is None:
        return []
    return [(doc["text"][d["start"]:d["end"]], d["kind"]) for d in doc.get("_decoys") or []]


def invariants(before: dict, after: dict | None, name: str) -> None:
    if after is None:
        return
    check(after["text"] == before["text"], f"{name}: text unchanged")
    es = after["entities"]
    check(all(after["text"][e["start"]:e["end"]] == e["text"] for e in es), f"{name}: exact spans", es)
    check(all(a["end"] <= b["start"] for a, b in zip(es, es[1:])), f"{name}: sorted, no overlap", es)
    decs = [(d["start"], d["end"]) for d in after.get("_decoys") or []]
    check(not any(a < e["end"] and e["start"] < b for a, b in decs for e in es),
          f"{name}: no decoy overlaps an entity", (decs, es))
    claimed, _ = resolve_claims(after["text"], [{"label": e["label"], "text": e["text"]} for e in es],
                                blocked=decs)
    check({(e["start"], e["end"], e["label"]) for e in claimed} == {(e["start"], e["end"], e["label"]) for e in es},
          f"{name}: no resolver drift", (claimed, es))
    check(find_unlabeled_repeats(after["text"], es, exempt=decs) == 0, f"{name}: no unlabelled repeat")


def run(r: dict, name: str) -> tuple[dict | None, list[str]]:
    frozen = copy.deepcopy(r)
    out, rules = clean_doc(r)
    check(r == frozen, f"{name}: input record not mutated")
    again, rules2 = clean_doc(copy.deepcopy(frozen))
    check(again == out and rules2 == rules, f"{name}: deterministic")
    invariants(frozen, out, name)
    return out, rules


# --------------------------------------------------------------------------

def test_r1_old_corpus_drops():
    formal = "Məhkəmə qərarı aparılmalıddır (yox, aparılmalıdır). Tarix: 12.05.2020"
    out, rules = run(rec(formal, [("12.05.2020", "DATE")], old=True, doc_type="court_filing"), "R1 formal")
    check(out is None and rules == ["R1"], "R1: a formal self-correction in the old corpus is dropped", rules)
    out, rules = run(rec(formal, [("12.05.2020", "DATE")], old=True, doc_type="live_chat"), "R1 chat")
    check(out is not None and "R1" not in rules, "R1: kept in a chat (D-47b keeps conversational types)", rules)
    out, rules = run(rec(formal, [("12.05.2020", "DATE")], doc_type="court_filing"), "R1 llm")
    check(out is not None, "R1: old corpus only (the LLM files were cleaned by drop_before_v3.py)", rules)
    out, rules = run(rec("Hörmətli [Şirkət Adı] rəhbərliyi, Leyla yazır.", [("Leyla", "GIVENNAME")], old=True),
                     "R1 placeholder")
    check(out is None and rules == ["R1"], "R1: an unfilled placeholder (D-47e)", rules)
    out, rules = run(rec("Sistem l0st (0/O qarışığı) qeyd edildi, Leyla.", [("Leyla", "GIVENNAME")], old=True),
                     "R1 typo")
    check(out is None, "R1: an explained typo (D-47a)", rules)
    many = " ".join(["Leyla gəldi."] * 20)
    out, rules = run(rec(many, [("Leyla", "GIVENNAME", i) for i in range(20)], old=True, doc_type="live_chat"),
                     "R1 repeats")
    check(out is None and rules == ["R1"], "R1: one value labelled 20 times (D-45b)", rules)


def test_r2_timestamps():
    check(is_timestamp("[08.09.2026\u00a015:25] DEBUG", 1, 11), "is_timestamp: a non-breaking space joins a stamp")
    check(is_timestamp("2020-01-02\u2009 10:15", 0, 10), "is_timestamp: a thin space joins a stamp")
    check(is_timestamp("2018-11-14     17:20   Xəta", 0, 10), "is_timestamp: 4+ spaces join a stamp")
    check(is_timestamp("2018-11-14\t\t17:20", 0, 10), "is_timestamp: tabs join a stamp")
    check(is_timestamp("10:15\u00a012.05.2021", 6, 16), "is_timestamp: time, NBSP, date")
    check(not is_timestamp("Tarix: 2018-11-14\n17:20 görüş", 7, 17), "is_timestamp: a newline is not a gap")
    check(not is_timestamp("Tarix: 2018-11-14 | 17:20", 7, 17), "is_timestamp: a table border is not a gap")

    t = "[2023-11-14 13:36:00] INFO: Faktura 13:36 vaxtı ilə ödənildi."
    out, rules = run(rec(t, [("13:36", "TIME", 0), ("13:36", "TIME", 1)]), "R2 log")
    check(spans(out) == [("13:36", "TIME")] and out["entities"][0]["start"] == t.index("13:36", 20),
          "R2: TIME in a date+time stamp unlabelled, the clock time in the text kept", spans(out))
    check(("2023-11-14 13:36:00", "TIMESTAMP") in decoy_kinds(out), "R2: the stamp is declared TIMESTAMP",
          decoy_kinds(out))
    t = "[08.09.2026\u00a015:25] DEBUG: Retrying. Müqavilə tarixi: 08.09.2026"
    out, _ = run(rec(t, [("08.09.2026", "DATE", 0), ("15:25", "TIME"), ("08.09.2026", "DATE", 1)]), "R2 nbsp")
    check(spans(out) == [("08.09.2026", "DATE")] and out["entities"][0]["start"] > 20,
          "R2: DATE and TIME in an NBSP stamp unlabelled, the standalone date kept", spans(out))
    t = "2018-11-4     17:20            Xəta: Şəbəkə əlaqəsi kəsildi"
    out, _ = run(rec(t, [("17:20", "TIME")], spec={"entities": [{"label": "TIME", "value": "17:20"}]}),
                 "R2 4 spaces")
    check(spans(out) == [] and out.get("_pii_free") is True,
          "R2: TIME after 4+ spaces unlabelled; an emptied record is declared PII-free", out)
    t = "[10:16] Agent: Salam!\n[10:17] Müştəri: Kartım bloklanıb."
    out, _ = run(rec(t, [("10:16", "TIME"), ("10:17", "TIME")], doc_type="live_chat"), "R2 chat")
    check(spans(out) == [], "R2: TIME on line-initial chat stamps unlabelled (D-51f)", spans(out))
    t = "10:16 - Agent: Salam!\n10:18 - Agent: Buyurun."
    out, _ = run(rec(t, [("10:16", "TIME"), ("10:18", "TIME")], doc_type="live_chat"), "R2 bare stamp")
    check(spans(out) == [], "R2: `10:16 - Agent:` is a chat stamp", spans(out))
    t = "Elvin [10:16]: Salam, sabah görüşək."
    out, _ = run(rec(t, [("Elvin", "GIVENNAME"), ("10:16", "TIME")], doc_type="live_chat"), "R2 speaker stamp")
    check(spans(out) == [("Elvin", "GIVENNAME")], "R2: `Elvin [10:16]:` stamp unlabelled", spans(out))
    t = "Görüş saat 14:30-da başlayacaq."
    out, rules = run(rec(t, [("14:30", "TIME")]), "R2 saat")
    check(spans(out) == [("14:30", "TIME")] and not rules, "R2: `saat 14:30` stays TIME", rules)
    t = "05:47;FD00:4760:7B5::1;Leyla"
    out, rules = run(rec(t, [("05:47", "TIME"), ("Leyla", "GIVENNAME")], source="targeted"), "R2 csv")
    check(("05:47", "TIME") in spans(out), "R2: a time in a CSV cell stays TIME", spans(out))
    t = "Xronologiya:\n- 14:37: Sistem xəbərdarlığı alındı."
    out, _ = run(rec(t, [("14:37", "TIME")]), "R2 timeline")
    check(spans(out) == [("14:37", "TIME")], "R2: a timeline entry stays TIME", spans(out))
    t = "- 23:06:15 - Verilənlər bazası ilə əlaqə kəsildi."
    out, _ = run(rec(t, [("23:06", "TIME")]), "R2 hhmmss")
    check(spans(out) == [], "R2: HH:MM of a log line's HH:MM:SS unlabelled", spans(out))


def test_r3_ci_il():
    for t, value, want in (("Tarix: 12 mart 2016-cı il", "12 mart 2016-cı il", "12 mart 2016"),
                           ("Doğum tarixi: 3 iyun 1959-ci il", "3 iyun 1959-ci il", "3 iyun 1959"),
                           ("Tarix: 1 may 2020-ci il.", "1 may 2020-ci il", "1 may 2020"),
                           ("TARIX: 14 MART 1994-CI IL", "14 MART 1994-CI IL", "14 MART 1994"),
                           ("Tarix: 6 yanvar 1960—ci il", "6 yanvar 1960—ci il", "6 yanvar 1960"),
                           ("Tarix: 9 sentyabr 2023-cü", "9 sentyabr 2023-cü", "9 sentyabr 2023")):
        out, rules = run(rec(t, [(value, "DATE")]), f"R3 {value}")
        check(spans(out) == [(want, "DATE")] and rules == ["R3"], f"R3: {value!r} -> {want!r}", spans(out))
    out, rules = run(rec("Tarix: 12.03.2016", [("12.03.2016", "DATE")]), "R3 plain")
    check(spans(out) == [("12.03.2016", "DATE")] and not rules, "R3: a date without the suffix is untouched")


def test_r4_persona_names():
    t = "[10:41] Samir: Salam\n[10:42] Agent: Buyurun\n[10:43] Samir: Kartım bloklanıb"
    out, rules = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 speaker")
    check(spans(out) == [("Samir", "GIVENNAME"), ("Samir", "GIVENNAME")] and rules == ["R4"],
          "R4: a chat speaker becomes GIVENNAME on every line, `Agent` does not", spans(out))
    t = "Müştəri: Salam, kartım işləmir.\nOperator: Buyurun, yoxlayıram.\nMüştəri: Təşəkkürlər."
    out, rules = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 roles")
    check(spans(out) == [] and not rules, "R4: role words are never names", spans(out))
    t = "Tarix: 12.05.2020\nMövzu: Kart\nQeyd: Rəsmi müraciət"
    out, rules = run(rec(t, [("12.05.2020", "DATE")]), "R4 fields")
    check(spans(out) == [("12.05.2020", "DATE")] and not rules, "R4: field labels are not speaker tags")
    t = "Qiymətlər:\n- Kimya: 75\n- Tarix: 82\n- Fizika: 90"
    out, rules = run(rec(t, spec={"negative_only": True}, doc_type="report"), "R4 grades")
    check(not rules, "R4: `Kimya: 75` in a list is not a speaker", rules)
    t = "Agent: Salam, mən Leyla, sizə necə kömək edə bilərəm?\nMüştəri: Salam."
    out, _ = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 intro")
    check(spans(out) == [("Leyla", "GIVENNAME")], "R4: a self-introduction", spans(out))
    t = "Agent: Salam! Mən Agent Məmmədov, buyurun."
    out, _ = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 intro role")
    check(spans(out) == [], "R4: `Mən Agent …` is not a name", spans(out))
    t = "Sənədləri göndərdim.\n\nHörmətlə,\nLeyla Məmmədova"
    out, _ = run(rec(t, spec={"negative_only": True}, doc_type="customer_email"), "R4 signature")
    check(spans(out) == [("Leyla", "GIVENNAME"), ("Məmmədova", "SURNAME")], "R4: a signature line", spans(out))
    t = "Sənədləri göndərdik.\n\nHörmətlə,\nMüştəri Xidmətləri Komandası"
    out, rules = run(rec(t, spec={"negative_only": True}), "R4 team signature")
    check(not rules, "R4: a team signature is not a name", rules)
    t = "From: Elvin Həsənov\nSubject: Hesab\n\nSalam, hesabı yoxlayın."
    out, _ = run(rec(t, spec={"negative_only": True}, doc_type="email_thread"), "R4 header")
    check(spans(out) == [("Elvin", "GIVENNAME"), ("Həsənov", "SURNAME")], "R4: a From: header", spans(out))
    t = "Göndərən: Dəstək Xidməti\nMövzu: Bildiriş"
    out, rules = run(rec(t, spec={"negative_only": True}), "R4 header team")
    check(not rules, "R4: `Göndərən: Dəstək Xidməti` is not a name", rules)
    t = "Məsul şəxs: S. Qəmbərov\nTelefon yoxdur."
    out, _ = run(rec(t, spec={"negative_only": True}), "R4 initial")
    check(spans(out) == [("Qəmbərov", "SURNAME")], "R4: `S. Qəmbərov` -> SURNAME, the initial stays out",
          spans(out))
    t = "Ünvan: N. Nərimanov prospekti 12"
    out, rules = run(rec(t, spec={"negative_only": True}), "R4 initial street")
    check(not any(lab == "SURNAME" for _, lab in spans(out)), "R4: an initial + surname in a street name", rules)
    t = "[10:41] Ümid: Salam\n[10:42] Agent: Buyurun\nÜmid edirəm ki, hər şey yaxşı olacaq."
    out, rules = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 homograph")
    check(out is None and rules == ["R4"], "R4: a homograph used as a word elsewhere: not guessed, dropped", rules)
    t = "Agent: Salam, mən Aydın. Sizə necə kömək edim?\nMüştəri: Salam, Aydın bəy."
    out, _ = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 homograph name")
    check(spans(out) == [("Aydın", "GIVENNAME"), ("Aydın", "GIVENNAME")],
          "R4: a homograph name used only as a name is labelled everywhere", spans(out))
    t = "Müştəri: Salam, mən Ayseldir. Kartım bloklanıb."
    out, _ = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 copula")
    check(spans(out) == [("Ayseldir", "GIVENNAME")], "R4: a fused copula is labelled whole (D-9)", spans(out))
    # The review (15 Oct): a name the resolver cannot place drops the record (D-15c)
    t = "Məsul: S.Mətinov, iclas bitdi."
    out, rules = run(rec(t, spec={"negative_only": True}), "R4 unplaceable")
    check(out is None and rules == ["R4"], "R4: `S.Mətinov` cannot be placed: dropped, not left unlabelled", rules)
    # ... and a title with a case ending, or a CSV cell end, follows a name (not a homograph use)
    t = "Tapşırıqlar:\n- Bayram bəylə təcili əlaqə saxlanılmalıdır.\n\nHörmətlə,\nBayram Elibeyov"
    out, rules = run(rec(t, spec={"negative_only": True}), "R4 title suffix")
    check(spans(out) == [("Bayram", "GIVENNAME"), ("Bayram", "GIVENNAME"), ("Elibeyov", "SURNAME")],
          "R4: `Bayram bəylə` is the name, not the word", (rules, spans(out)))
    t = "[10:15] Sevinc: Salam!\n[10:16] Elvin: Salam Sevinc!\nSıra;İcraçı;Status\n10;Sevinc;Tamamlandı"
    out, rules = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 csv cell")
    check(spans(out) == [("Sevinc", "GIVENNAME"), ("Elvin", "GIVENNAME"), ("Sevinc", "GIVENNAME"),
                         ("Sevinc", "GIVENNAME")], "R4: `;Sevinc;` in a CSV row is the name", (rules, spans(out)))
    t = "[10:41] Bayram: Salam\n[10:42] Agent: Buyurun\nBayram bəyanatı oxundu."
    out, rules = run(rec(t, doc_type="live_chat", spec={"negative_only": True}), "R4 bəyanat")
    check(out is None and rules == ["R4"], "R4: `Bayram bəyanatı` is not a title after a name: dropped", rules)


def test_native_name_decisions():
    from build_v4_clean_lexicon import NATIVE_NAMES, NATIVE_NOT_NAMES
    from piigen.resolver import match_key
    from piigen.v4_clean import lexicon
    lex = lexicon()
    check(all(match_key(n) in lex.given for n in NATIVE_NAMES), "lexicon: the names are allowed (rebuilt)",
          [n for n in NATIVE_NAMES if match_key(n) not in lex.given])
    check(not any(match_key(n) in lex.given for n in NATIVE_NOT_NAMES), "lexicon: the non-names excluded")
    t = "Sənədləri göndərdim.\n\nHörmətlə,\nAli Vəliyev"
    out, _ = run(rec(t, spec={"negative_only": True}, doc_type="customer_email"), "R4 Ali")
    check(spans(out) == [("Ali", "GIVENNAME"), ("Vəliyev", "SURNAME")], "R4: `Ali` in a signature (native check)",
          spans(out))


def test_r5_half_names():
    t = "Tofiq Osmanov dünən zəng etdi."
    out, rules = run(rec(t, [("Osmanov", "SURNAME")], old=True), "R5 given")
    check(spans(out) == [("Tofiq", "GIVENNAME"), ("Osmanov", "SURNAME")] and rules == ["R5"],
          "R5: the given name before a labelled surname", spans(out))
    t = "Həkim Məmmədov bu gün qəbul etmir."
    out, rules = run(rec(t, [("Məmmədov", "SURNAME")], old=True), "R5 title")
    check(spans(out) == [("Məmmədov", "SURNAME")] and not rules, "R5: a title is not a given name", rules)
    t = "Siyahı:\n1. Məmmədov Rəşad Əli oğlu\n2. Quliyeva Nigar"
    out, _ = run(rec(t, [("Məmmədov", "SURNAME"), ("Quliyeva", "SURNAME")], old=True), "R5 list")
    check(spans(out) == [("Məmmədov", "SURNAME"), ("Rəşad", "GIVENNAME"), ("Əli", "GIVENNAME"),
                         ("Quliyeva", "SURNAME"), ("Nigar", "GIVENNAME")],
          "R5: surname-first list lines; the father's name is GIVENNAME, `oğlu` outside (D-39b)", spans(out))
    t = "Müştəri Leyla Hüseynova müraciət edib. Leyla xanım gözləyir."
    out, _ = run(rec(t, [("Hüseynova", "SURNAME")], old=True), "R5 repeat")
    check(spans(out) == [("Leyla", "GIVENNAME"), ("Hüseynova", "SURNAME"), ("Leyla", "GIVENNAME")],
          "R5: the new given name is labelled on every occurrence", spans(out))


def test_r6_city_in_institution():
    t = "Salyan Rayon Məhkəməsi qərar verdi."
    out, rules = run(rec(t, [("Salyan", "CITY")]), "R6 court")
    check(spans(out) == [] and decoy_kinds(out) == [("Salyan", "policy_city_in_institution")] and rules == ["R6"],
          "R6: a city heading a court's name is unlabelled and declared", (spans(out), decoy_kinds(out)))
    t = "Lerik layihəsi üzrə hesabat hazırdır."
    out, _ = run(rec(t, [("Lerik", "CITY")]), "R6 project")
    check(decoy_kinds(out) == [("Lerik", "policy_city_as_project")], "R6: a project name", decoy_kinds(out))
    t = "Bakı Dövlət Universiteti, Bakı şəhəri."
    out, _ = run(rec(t, [("Bakı", "CITY", 0), ("Bakı", "CITY", 1)]), "R6 mixed")
    check(spans(out) == [("Bakı", "CITY")] and out["entities"][0]["start"] > 5,
          "R6: the university's city unlabelled, the city in prose kept (decoy blocks the re-claim)", spans(out))
    for t, city in (("Mən Salyan rayonunda yaşayıram.", "Salyan"), ("Naxçıvan şəhər mərkəzi bağlıdır.", "Naxçıvan"),
                    ("Sumqayıt şöbəsi ilə əlaqə saxlayın.", "Sumqayıt"), ("Bakının mərkəzi küçələri.", "Bakının")):
        out, rules = run(rec(t, [(city, "CITY")]), f"R6 keep {city}")
        check(spans(out) == [(city, "CITY")] and not rules, f"R6: a city in prose stays CITY ({t!r})", rules)


def test_r7_false_surnames():
    t = "Pasientə tövsiyə: Şəkərli qidaları azaldın."
    out, rules = run(rec(t, [("Şəkərli", "SURNAME")], old=True), "R7 stoplist")
    check(spans(out) == [] and rules == ["R7"], "R7: a common word labelled SURNAME in the old corpus", rules)
    out, rules = run(rec(t, [("Şəkərli", "SURNAME")]), "R7 llm")
    check(spans(out) == [("Şəkərli", "SURNAME")], "R7: the stoplist applies to the old corpus only", rules)
    t = "Soyadı: Şiddətli\nTelefon yoxdur."
    out, rules = run(rec(t, [("Şiddətli", "SURNAME")], old=True), "R7 field")
    check(spans(out) == [("Şiddətli", "SURNAME")] and not rules, "R7: a stoplist word in a surname field stays")
    t = "Elnur Şəkərli zəng etdi."
    out, rules = run(rec(t, [("Elnur", "GIVENNAME"), ("Şəkərli", "SURNAME")], old=True), "R7 name")
    check(("Şəkərli", "SURNAME") in spans(out) and not rules, "R7: next to a given name it stays", rules)
    t = "Nəzarət məntəqəsi: Heydər Əliyev Beynəlxalq Hava Limanı"
    out, rules = run(rec(t, [("Heydər", "GIVENNAME"), ("Əliyev", "SURNAME")]), "R7 airport")
    check(spans(out) == [] and rules == ["R7"], "R7: a name heading an institution is unlabelled (D-2)", spans(out))
    t = "Hesab Nəmət Azayev adına açılıb."
    out, rules = run(rec(t, [("Nəmət", "GIVENNAME"), ("Azayev", "SURNAME")]), "R7 adına")
    check(len(spans(out)) == 2 and not rules, "R7: `X adına` (in X's name) stays a person", rules)
    t = "Nizami Gəncəvi adına Ədəbiyyat İnstitutu"
    out, rules = run(rec(t, [("Nizami", "GIVENNAME"), ("Gəncəvi", "SURNAME")]), "R7 named after")
    check(spans(out) == [] and rules == ["R7"], "R7: `… adına … İnstitutu` is an institution", spans(out))


def test_r8_checksum_lookalikes():
    t = "Kart nömrəsi 6328 0717 0275 9726 kimi qeyd edilib. Leyla yoxlayır."
    for kind in ("LOYALTY_CARD_LUHN_BAD", "card_luhn_invalid", "tracking_code_15_16", "IBAN_BAD_CHECKSUM"):
        r = rec(t, [("Leyla", "GIVENNAME")], decoys=[{"start": 13, "end": 32, "kind": kind,
                                                      "resembles": "PAYMENT_CARD_NUMBER"}])
        out, rules = run(r, f"R8 {kind}")
        check(out is None and rules == ["R8"], f"R8: a `{kind}` look-alike drops the record", rules)
    r = rec(t, [("Leyla", "GIVENNAME")], decoys=[{"start": 13, "end": 32, "kind": "policy_test_card",
                                                  "resembles": "PAYMENT_CARD_NUMBER"}])
    out, rules = run(r, "R8 policy")
    check(out is not None and "R8" not in rules, "R8: a D-2 dummy card stays", rules)
    # D-51j: an old 16-digit look-alike drops its record only with a card word within 4 words
    for t in ("Kartın nömrəsi belədir: 7669 7249 4877 2558. Leyla bilmir.",
              "Ödəniş kartı 7669724948772558 bloklanıb, Leyla bilmir.",
              "Visa 7669 7249 4877 2558 qəbul edilmədi, Leyla bilmir.",
              "7669 7249 4877 2558 nömrəli card aktiv deyil, Leyla bilmir."):
        r = rec(t, [("Leyla", "GIVENNAME")], old=True, doc_type="live_chat",
                spec={"adversarials": [], "hard_negatives": ["7669 7249 4877 2558" if " 4877" in t
                                                             else "7669724948772558"]})
        out, rules = run(r, "R8 old card word")
        check(out is None and rules == ["R8"], "R8 (D-51j): an old 16-digit look-alike by a card word drops", t)
    for t in ("Baxın, bu rəqəmlər nədir: 7669 7249 4877 2558. Leyla bilmir.",
              "Əməliyyat nömrəsi 7669 7249 4877 2558 qeydə alınıb, Leyla bilmir.",
              "Kartof partiyası: məhsul nömrəsi 7669 7249 4877 2558, Leyla bilmir.",
              "Kart sifariş edildi. Bu gün səhər əməliyyat nömrəsi 7669 7249 4877 2558 qeydə alınıb, Leyla bilmir."):
        r = rec(t, [("Leyla", "GIVENNAME")], old=True, doc_type="live_chat",
                spec={"adversarials": ["7669 7249 4877 2558"], "hard_negatives": []})
        out, rules = run(r, "R8 old no card word")
        check(out is not None and "R8" not in rules, "R8 (D-51j): an old 16-digit look-alike with no card word "
              "within 4 words stays", t)
    t = "Hesab: AZ21NABZ00000000137010001945 (köhnə), Leyla bilmir."
    r = rec(t, [("Leyla", "GIVENNAME")], old=True, doc_type="live_chat",
            spec={"adversarials": ["AZ21NABZ00000000137010001945"], "hard_negatives": []})
    out, rules = run(r, "R8 old iban")
    check(out is None and rules == ["R8"], "R8: an old-corpus IBAN failing mod 97 drops (D-51j narrows cards only)",
          rules)
    r = rec("Kod: v3.14.2 yeniləndi, Leyla.", [("Leyla", "GIVENNAME")], old=True, doc_type="live_chat",
            spec={"adversarials": ["v3.14.2"], "hard_negatives": ["INV-869822"]})
    out, rules = run(r, "R8 old other")
    check(out is not None and "R8" not in rules, "R8: other old look-alikes stay", rules)


def test_r9_ages():
    t = "Ad: Leyla\nYaş: 59\nCins: Qadın"
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R9 field")
    check(("59", "AGE") in spans(out) and rules == ["R9"], "R9: `Yaş: 59` -> AGE", spans(out))
    t = "Xəstə 52 yaşında kişidir, Leyla həkimdir."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R9 suffix")
    check(("52", "AGE") in spans(out), "R9: `52 yaşında` -> AGE", spans(out))
    t = "Qruplar: 18–30 yaş və 31–45 yaş. Leyla qeyd etdi."
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R9 range")
    check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, "R9: an age range is not an age", rules)
    t = "Bu yükdən sonra özümü sanki 80 yaşında hiss edirəm, Leyla."
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R9 figurative")
    check(out is None and rules == ["R9"], "R9: a figurative age cannot be decided: dropped", rules)
    t = "Yaş: 150\nAd: Leyla"
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R9 implausible")
    check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, "R9: 150 is not a plausible age", rules)


def test_r10_times():
    t = "Görüş sabah saat 14:30-da olacaq, Leyla."
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 saat")
    check(("14:30", "TIME") in spans(out) and rules == ["R10"], "R10: `saat 14:30-da` -> TIME", spans(out))
    t = "Tarix: 14.11.2017\nSaat: 16:42\nKassir: Leyla"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 field")
    check(("16:42", "TIME") in spans(out), "R10: `Saat: 16:42` -> TIME", spans(out))
    t = "Başlama vaxtı: 11:42\nOperator: Leyla"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 vaxtı")
    check(("11:42", "TIME") in spans(out), "R10: `vaxtı: 11:42` -> TIME", spans(out))
    t = "Giriş saat 10:15:30-da qeydə alındı, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 hms")
    check(("10:15:30", "TIME") in spans(out), "R10: `saat 10:15:30` -> TIME, seconds included", spans(out))
    t = "Saat: 14:00:00 – 15:30:00\nOperator: Leyla"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 hms range")
    check(("14:00:00", "TIME") in spans(out) and ("15:30:00", "TIME") in spans(out),
          "R10: each end of an HH:MM:SS range", spans(out))
    t = "Xəta saat 23:06:15 oldu, Leyla.\n- 23:06:15 - Bağlantı kəsildi"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 hms log line")
    check(spans(out).count(("23:06:15", "TIME")) == 1 and ("23:06:15", "TIMESTAMP") in decoy_kinds(out),
          "R10: the same HH:MM:SS as a log line stamp (D-51f) is declared, not labelled",
          (spans(out), decoy_kinds(out)))
    t = "Leyla yazdı:\n[10:16] saat 10:16 uyğundur"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 chat stamp")
    check(spans(out).count(("10:16", "TIME")) == 1 and ("10:16", "TIMESTAMP") in decoy_kinds(out),
          "R10: a chat line stamp of the same value stays out", (spans(out), decoy_kinds(out)))
    t = "Görüşün yeni vaxtı saat 7:15 PM olaraq yeniləndi, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 pm")
    check(("7:15 PM", "TIME") in spans(out), "R10: `saat 7:15 PM` -> TIME with PM", spans(out))
    t = "Sistem zamanı: 14:30:15\nİş saatları: 09:00–18:00\nOperator: Leyla"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 zaman saatları")
    check(all((v, "TIME") in spans(out) for v in ("14:30:15", "09:00", "18:00")),
          "R10: `zamanı:` and `İş saatları:` (range)", spans(out))
    t = "Ofisimiz hər gün saat 09:00-dan 18:00-a qədər açıqdır, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 dan-a")
    check(("09:00", "TIME") in spans(out) and ("18:00", "TIME") in spans(out),
          "R10: both ends of `09:00-dan 18:00-a qədər`", spans(out))
    t = "Filial hər iş günü saat 09:00-dan 18:00-dək qəbul aparır, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 dan-dək")
    check(("09:00", "TIME") in spans(out) and ("18:00", "TIME") in spans(out),
          "R10: both ends of `09:00-dan 18:00-dək` (v4.2 native review)", spans(out))
    t = "Leyla qeyd etdi.\nsaat 09:43       Müştəri        Oldu."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 column")
    check(("09:43", "TIME") in spans(out), "R10: `saat 09:43` in a transcript column -> TIME", spans(out))
    t = "Saat 10:00 amma gecikdi, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 amma")
    check(("10:00", "TIME") in spans(out), "R10: `amma` after the clock is not AM", spans(out))
    for bad in ("saat 25:10", "vaxtı: 17:73", "saat 10:15:75", "saat 14:30.5", "saatlarla 10:00"):
        out, rules = run(rec(f"Qeyd: {bad} idi, Leyla.", [("Leyla", "GIVENNAME")]), "R10 " + bad)
        check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, f"R10: `{bad}` is not labelled", rules)
    t = "Saat: 10:00 – 14:30\nMövzu: büdcə, Leyla"
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 range")
    check(("10:00", "TIME") in spans(out) and ("14:30", "TIME") in spans(out), "R10: each end of a range", spans(out))
    t = "Leyla qeyd etdi: saat 14:30 12.05.2021 tarixində."
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 stamp")
    check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, "R10: a time inside a time+date stamp stays out",
          rules)
    t = "12.05.2021 14:30 Ölçmə\nSaat 14:30 vaxtında təzyiq düşdü, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 stamp occurrence")
    check(spans(out).count(("14:30", "TIME")) == 1 and ("12.05.2021 14:30", "TIMESTAMP") in decoy_kinds(out),
          "R10: the same value in a stamp is declared TIMESTAMP, not labelled", (spans(out), decoy_kinds(out)))
    t = "Nümunə: saat 09:00 formatında yazın, Leyla."
    i = t.index("09:00")
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")], decoys=[{"start": i, "end": i + 5, "kind": "format_example",
                                                                  "resembles": "TIME"}]), "R10 look-alike")
    check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, "R10: a declared look-alike stays out", rules)
    t = "Görüş saat 09:00-da, fasilə 09:00-dan sonra deyil, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 every occurrence")
    check(spans(out).count(("09:00", "TIME")) == 2, "R10: every occurrence of the value", spans(out))
    # v4.1 item 7: a time followed by `versiya…` names a version
    for v in ("versiya", "versiyası", "versiyasında", "versiyaya", "versiyasını", "Versiyası", "- versiyası"):
        t = f"Leyla proqramın saat 14:30 {v} ilə işləyir."
        out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 " + v)
        check(spans(out) == [("Leyla", "GIVENNAME")] and not rules, f"R10: `saat 14:30 {v}` is not TIME", rules)
    t = "Saat 10:00-14:30 versiyası yükləndi, Leyla."
    out, rules = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 range versiya")
    check(not rules, "R10: a range before `versiyası` is not TIME", spans(out))
    t = "Görüş saat 14:30-da olacaq. Saat 14:30 versiyası isə köhnədir, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 versiya occurrence")
    i = t.rindex("14:30")
    check(spans(out).count(("14:30", "TIME")) == 1
          and {"start": i, "end": i + 5, "kind": "policy_version_time", "resembles": "TIME"} in out["_decoys"],
          "R10: the same value before `versiyası` is declared a look-alike, not labelled",
          (spans(out), out.get("_decoys")))
    t = "Görüş saat 14:30 versiyanın təqdimatı ilə yox, saat 15:00 ilə başlayır, Leyla."
    out, _ = run(rec(t, [("Leyla", "GIVENNAME")]), "R10 versiya next")
    check(("15:00", "TIME") in spans(out) and ("14:30", "TIME") not in spans(out),
          "R10: only the time right before `versiya…` is skipped", spans(out))
    t = "Görüş saat 14:30-da, Leyla."
    out, rules = run(rec(t, [("14:30", "TIME"), ("Leyla", "GIVENNAME")]), "R10 labelled")
    check(not rules, "R10: an already labelled time is left alone", rules)


def test_untouched_and_targeted():
    t = "Gözəl yardımlımız qonaqları salamlayır. Fidan sənədləri gətirdi."
    out, rules = run(rec(t, [("Fidan", "GIVENNAME")], source="targeted"), "targeted")
    check(out is not None and not rules and out == clean_doc(copy.deepcopy(out))[0],
          "a clean record comes back unchanged", rules)
    r = rec("Sənədləri Leyla imzaladı.", [("Leyla", "GIVENNAME")])
    out, rules = clean_doc(r)
    check(out is r and not rules, "an untouched record is returned as is (written byte for byte)")
    det = clean_doc_detail(rec("Tarix: 1 may 2020-ci il", [("1 may 2020-ci il", "DATE")]))
    check(det.doc["_v4_clean"] == ["R3"] and det.changes[0].action == "trim", "the record lists its rules")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("=" * 62)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 62)
    for f in FAILURES:
        print("FAIL:", f)
    raise SystemExit(1 if FAIL else 0)
