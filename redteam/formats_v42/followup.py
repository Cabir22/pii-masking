"""Adaptive follow-up on the formats benchmark's confirmed failures (separate from the frozen 200).

Each probe varies one factor of a failing case: another value, another wrapper, a minimal text,
or the matched control. Expected annotations follow the same conventions (D-72). Runs gently
(4 threads, pauses) and writes followup_results.md and followup_predictions.jsonl.

  python redteam/formats_v42/followup.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(HERE))

from evaluate import score_case  # noqa: E402
from run_cases import MODEL, REVISION, masked, throttled  # noqa: E402

P: list[tuple[str, str, str, list[tuple[str, str]]]] = []   # (probe group, note, text, expected)


def add(group: str, note: str, text: str, exp: list[tuple[str, str]]) -> None:
    P.append((group, note, text, exp))


# A. disguised e-mails: which disguise leaks, does the value or the label matter
for em in ("nigar.huseynova@inbox.az", "kamal77@poct.az", "info.sabina@kamranservis.az"):
    add("A at-disguise", f"[at], {em}", f"E-poçt: {em.replace('@', '[at]')}", [(em.replace("@", "[at]"), "EMAIL")])
    add("A at-disguise", f"(at), {em}", f"E-poçt: {em.replace('@', '(at)')}", [(em.replace("@", "(at)"), "EMAIL")])
    add("A at-disguise", f"spaced at, {em}", f"E-poçt: {em.replace('@', ' at ')}", [(em.replace("@", " at "), "EMAIL")])
v = "nigar.huseynova[at]inbox.az"
add("A at-disguise", "[at] without a label word", f"Mənə {v} ünvanına yazın.", [(v, "EMAIL")])
add("A at-disguise", "[at] after 'Əlaqə üçün'", f"Əlaqə üçün: {v}", [(v, "EMAIL")])

# B. spoken digits: length and label word
add("B spoken", "short local, words", "Nömrəm: sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd",
    [("sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd", "TELEPHONENUM")])
add("B spoken", "'telefonum' as the label", "Telefonum: sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd",
    [("sıfır əlli yeddi yüz otuz doqquz iyirmi bir altmış dörd", "TELEPHONENUM")])
add("B spoken", "digit by digit", "Nömrəm: sıfır beş sıfır yeddi üç doqquz iki bir altı dörd",
    [("sıfır beş sıfır yeddi üç doqquz iki bir altı dörd", "TELEPHONENUM")])
add("B spoken", "control: same number in digits", "Nömrəm: 050 739 21 64", [("050 739 21 64", "TELEPHONENUM")])

# C. character-by-character IDs: other ID types, other spacing
for lab, v, word in (("AZ_VOEN", "1702938461", "VÖEN"), ("AZ_PASSPORT_NUMBER", "C47195362", "Pasport"),
                     ("AZ_ID_CARD_NUMBER", "AA7364519", "Vəsiqə"), ("AZ_FIN", "2HN6WK9", "FİN")):
    add("C spaced id", f"{lab} spaced by character", f"{word}: {' '.join(v)}", [(" ".join(v), lab)])
    add("C spaced id", f"{lab} control", f"{word}: {v}", [(v, lab)])
add("C spaced id", "FIN grouped 3-4", "FİN: 5RT 8VQ2", [("5RT 8VQ2", "AZ_FIN")])
add("C spaced id", "FIN grouped 2-2-3", "FİN: 5R T8 VQ2", [("5R T8 VQ2", "AZ_FIN")])

# D. HTML entities: wrapper and value
add("D entity", "&#64; without HTML tags", "E-poçt: s.qasimova&#64;inbox.az", [("s.qasimova&#64;inbox.az", "EMAIL")])
add("D entity", "&#64;, another address", "<p>E-poçt: kamal77&#64;poct.az</p>", [("kamal77&#64;poct.az", "EMAIL")])
add("D entity", "&#64; in a mailto link", '<a href="mailto:kamal77&#64;poct.az">yaz</a>', [("kamal77&#64;poct.az", "EMAIL")])
add("D entity", "control: literal @ in a link", '<a href="mailto:kamal77@poct.az">yaz</a>', [("kamal77@poct.az", "EMAIL")])

# E. 'Leyla' missed in row 4 of 8: the name, the position, the table size
add("E table name", "Leyla row alone", "Ad | Soyad | FİN\nLeyla | Rzayeva | 9PL4ZT3",
    [("Leyla", "GIVENNAME"), ("Rzayeva", "SURNAME"), ("9PL4ZT3", "AZ_FIN")])
add("E table name", "Leyla in a sentence", "Ərizəçi Leyla Rzayeva müraciət edib.", [("Leyla", "GIVENNAME"), ("Rzayeva", "SURNAME")])
add("E table name", "Leyla as given name with another surname", "Ad | Soyad\nLeyla | Quliyeva", [("Leyla", "GIVENNAME"), ("Quliyeva", "SURNAME")])
add("E table name", "Lalə in the same row instead", "Ad | Soyad | FİN\nLalə | Rzayeva | 9PL4ZT3",
    [("Lalə", "GIVENNAME"), ("Rzayeva", "SURNAME"), ("9PL4ZT3", "AZ_FIN")])
add("E table name", "Leyla at the start of a line, no table", "Leyla bu gün gəlməyəcək.", [("Leyla", "GIVENNAME")])

# F. the earlier 'phone cut to +' JSON finding (RT-0065): which field triggers it
base = {"name": "Elvin", "surname": "Məmmədov", "phone": "+994501234567", "fin": "5ZK3H7P"}
def j(d): return json.dumps(d, ensure_ascii=False)
add("F json plus", "original shape (name, surname, phone, fin)", j(base),
    [("Elvin", "GIVENNAME"), ("Məmmədov", "SURNAME"), ("+994501234567", "TELEPHONENUM"), ("5ZK3H7P", "AZ_FIN")])
add("F json plus", "without fin", j({k: base[k] for k in ("name", "surname", "phone")}),
    [("Elvin", "GIVENNAME"), ("Məmmədov", "SURNAME"), ("+994501234567", "TELEPHONENUM")])
add("F json plus", "without the names", j({k: base[k] for k in ("phone", "fin")}),
    [("+994501234567", "TELEPHONENUM"), ("5ZK3H7P", "AZ_FIN")])
add("F json plus", "another phone, same shape", j({**base, "phone": "+994553186427"}),
    [("Elvin", "GIVENNAME"), ("Məmmədov", "SURNAME"), ("+994553186427", "TELEPHONENUM"), ("5ZK3H7P", "AZ_FIN")])
add("F json plus", "Azerbaijani keys", j({"ad": "Elvin", "soyad": "Məmmədov", "telefon": "+994501234567", "fin": "5ZK3H7P"}),
    [("Elvin", "GIVENNAME"), ("Məmmədov", "SURNAME"), ("+994501234567", "TELEPHONENUM"), ("5ZK3H7P", "AZ_FIN")])

# G. surname-first display names
add("G display", "quoted 'Əliyev, Rauf' (another)", 'From: "Quliyev, Elnur" <elnur.q@poct.az>',
    [("Quliyev", "SURNAME"), ("Elnur", "GIVENNAME"), ("elnur.q@poct.az", "EMAIL")])
add("G display", "unquoted 'Əliyev Rauf'", "From: Əliyev Rauf <rauf.aliyev@kamranservis.az>",
    [("Əliyev", "SURNAME"), ("Rauf", "GIVENNAME"), ("rauf.aliyev@kamranservis.az", "EMAIL")])
add("G display", "'Əliyev, Rauf' in a sentence", "Sənədi Əliyev, Rauf imzalayıb.", [("Əliyev", "SURNAME"), ("Rauf", "GIVENNAME")])

# H. false alarms on codes: grouping and digit script
add("H codes", "spaced 5-group code", "Sifariş kodu: SIF 2026 0048 1752 3301", [])
add("H codes", "dashed code", "Sifariş kodu: SIF-2026-0048-1752-3301-7720", [])
add("H codes", "ASCII 10-digit after 'Sifariş №'", "Sifariş № 4829173651 qəbul olundu.", [])
add("H codes", "full-width 8-digit order", "Sifariş № ４８２９１７３６ qəbul olundu.", [])
add("H codes", "IP:port again, another IP", "client=91.198.36.14:443 closed", [("91.198.36.14", "IPV4_ADDRESS")])


def main() -> int:
    import torch
    torch.set_num_threads(4)
    import predict
    model, tok, id2label = predict.load_model(MODEL, revision=REVISION)
    rows, L = [], ["# Formats follow-up probes (v4.2, product decoding M)", "",
                   "Separate from the frozen 200. Each group varies one factor of a confirmed failure.", ""]
    cur = None
    for n, (g, note, text, exp) in enumerate(P, 1):
        while throttled():
            time.sleep(60)
        M = predict._detect_entities_word_consistent(text, model, tok, id2label)
        spans, pos = [], 0
        for v, lab in exp:
            s = text.index(v, pos)
            spans.append({"start": s, "end": s + len(v), "label": lab, "value": v})
            pos = s + 1
        r = score_case(text, spans, M)
        cats = [o["category"] for o in r["expected"]] + ["false_alarm"] * len(r["false_alarms"])
        ok = all(c == "correct" for c in cats)
        rows.append({"group": g, "note": note, "text": text, "expected": exp,
                     "M": [{k: s[k] for k in ("start", "end", "label")} for s in M], "categories": cats})
        if g != cur:
            L += ["", f"## {g}", "", "| Probe | Result | Masked (M) |", "|---|---|---|"]
            cur = g
        res = "ok" if ok else ", ".join(c for c in cats if c != "correct")
        L.append(f"| {note} | {res} | `{json.dumps(masked(text, M), ensure_ascii=False)[1:-1]}` |")
        time.sleep(0.3)
        if n % 20 == 0:
            time.sleep(30)
    (HERE / "followup_predictions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                                     encoding="utf-8")
    (HERE / "followup_results.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
