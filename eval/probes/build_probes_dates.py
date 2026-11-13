"""Build the date_forms_az probe family (D-82, 27 Oct): eval/probes/date_forms_az.jsonl.

    python eval/probes/build_probes_dates.py [--seed 82]

D-82 changes two things about Azerbaijani dates in m2, and no Azerbaijani set in the release check sees
either: the benchmark has no weekday next to a date and no year-first date, and A7 is EN/TR/RU only.
  (1) a weekday next to a date stays outside DATE (D-54d), on either side:
      `cümə axşamı, ⟦16 may 1963⟧`, `⟦10 iyun 1991⟧, bazar ertəsi`;
  (2) a year-first date is one DATE from the year to the day, a hyphen suffix after the day outside:
      `⟦2023-cü il oktyabrın 15⟧-də`, `⟦2025-ci ilin 12 may⟧`, `⟦2018-ci il, 15 iyun⟧`.
m1 and v4.2 put the weekday inside for 93-100% of such dates and find year-first dates 7.7% / 0% of the
time (X-DFRAG counts).

Five cells (`cell` on the DATE span), 15 documents each, 75 in all:
  plain            a date with no weekday (reference: the model's ordinary date skill);
  weekday_before   weekday, then the date;
  weekday_after    the date, then the weekday;
  year_first_gen   `2023-cü il oktyabrın 15` + a suffix after the day;
  year_first_ilin  `2025-ci ilin 12 may` / `2018-ci il, 15 iyun`.
Exact recall per cell is the D-82 measure (a weekday inside the predicted span is an exact miss); the
scoreboard's partial recall shows whether the date is masked at all. The weekday is the date's real one.
Every third document also holds a weekday on its own (`controls`, kind `weekday_alone`): DATE is the
calendar date only (D-54d), so a model that learned to mask weekdays shows up there.
Reported for m2 (year-first dates go into m2 only with the year_before relabel, else in m3; D-82).

Every sentence here was written for this probe (rule A2.5); none copies a training frame (X-DFRAG and
X-NOYR in scripts/piigen/targeted/: 0 shared 6-grams when built).
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

FAMILY = "date_forms_az"
CELLS = ("plain", "weekday_before", "weekday_after", "year_first_gen", "year_first_ilin")
PER_CELL = 15

MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avqust", "sentyabr", "oktyabr", "noyabr", "dekabr"]
MONTHS_GEN = ["yanvarın", "fevralın", "martın", "aprelin", "mayın", "iyunun", "iyulun", "avqustun", "sentyabrın",
              "oktyabrın", "noyabrın", "dekabrın"]
WEEKDAYS = ["bazar ertəsi", "çərşənbə axşamı", "çərşənbə", "cümə axşamı", "cümə", "şənbə", "bazar"]  # Monday first

# suffixes by the last number word: units 1-9, then tens 10..90 (index = tens digit)
_ORD_UNIT = {1: "ci", 2: "ci", 3: "cü", 4: "cü", 5: "ci", 6: "cı", 7: "ci", 8: "ci", 9: "cu"}
_ORD_TEN = {1: "cu", 2: "ci", 3: "cu", 4: "cı", 5: "ci", 6: "cı", 7: "ci", 8: "ci", 9: "cı"}
_POSS = {1: "i", 2: "si", 3: "ü", 4: "ü", 5: "i", 6: "sı", 7: "si", 8: "i", 9: "u", 10: "u", 20: "si", 30: "u"}
_LOC = {1: "də", 2: "də", 3: "də", 4: "də", 5: "də", 6: "da", 7: "də", 8: "də", 9: "da", 10: "da", 20: "də", 30: "da"}


def year_suffix(y: int) -> str:  # 2023 -> cü, 2020 -> ci, 2010 -> cu, 1990 -> cı, 2000 -> ci (min), 1900 -> cü (yüz)
    if y % 10:
        return _ORD_UNIT[y % 10]
    if y % 100:
        return _ORD_TEN[(y % 100) // 10]
    return "ci" if y % 1000 == 0 else "cü"


def day_key(d: int) -> int:
    return d % 10 or d


def a_date(r) -> datetime.date:
    return datetime.date(r.randint(1950, 2030), r.randint(1, 12), r.randint(1, 28))


def plain_form(r, dt):
    return r.choice([f"{dt.day} {MONTHS[dt.month - 1]} {dt.year}", f"{dt.day:02d}.{dt.month:02d}.{dt.year}"])


PLAIN = [
    "Sənəd {d} tarixində arxivə təhvil verilib.",
    "Hesabat {d} tarixinə olan vəziyyəti göstərir.",
    "Abunəlik {d} tarixindən etibarən dayandırılıb.",
    "Mənzil {d} tarixində yeni sahibinin adına keçirilib.",
    "Cihaz {d} tarixində təmirə qəbul olunub.",
]
W_BEFORE = [  # {w} weekday, {d} date
    "Komissiyanın iclası {w}, {d} tarixində keçirildi.",
    "Bağlama {w}, {d} günü ünvana çatdırılıb.",
    "Ərizəçi {w}, {d} tarixində yenidən müraciət edib.",
    "{W}, {d}: anbarda illik sayım aparıldı.",
    "Növbəti dərs {w}, {d} tarixinə keçirilib.",
]
W_AFTER = [
    "Komissiyanın iclası {d}, {w} keçirildi.",
    "Bağlama {d} ({w}) ünvana çatdırılıb.",
    "Son müraciət günü: {d}, {w}.",
    "Müqavilə {d}, {w} imzalanıb və qüvvəyə minib.",
    "Yoxlama {d}, {w} gününə təyin olunub.",
]
Y_GEN = [  # {y} = year-first date with the genitive month, then a suffix after the day ({s})
    "Fond {y}-{s} yaradılıb.",
    "Yeni qaydalar {y}-{s} tətbiq olunmağa başladı.",
    "Bina {y}-{s} istismara verilib.",
    "Məktub {y}-{s} poçta təhvil verilib.",
    "Sərgi {y}-{s} açıldı və bir ay davam etdi.",
]
Y_ILIN = [  # {y} = `2025-ci ilin 12 may` or `2018-ci il, 15 iyun`
    "Kurs {y} tarixində başa çatıb.",
    "Şikayət {y} tarixində qeydə alınıb.",
    "Avadanlıq {y} tarixində quraşdırılıb.",
    "Müqavilənin müddəti {y} tarixində bitir.",
    "Tədbir {y} tarixində paytaxtda keçirilib.",
]
CONTROL = ["Qəbul hər {w} günü aparılır.", "Ofis {w} günləri bağlı olur.",
           "Görüşü növbəti {w} gününə saxladıq."]


def doc_for(r, cell, i):
    """-> (text, (start, end) of the DATE)."""
    dt = a_date(r)
    w = WEEKDAYS[dt.weekday()]
    if cell == "plain":
        d, tpl = plain_form(r, dt), PLAIN[i % 5]
    elif cell in ("weekday_before", "weekday_after"):
        d, tpl = plain_form(r, dt), (W_BEFORE if cell == "weekday_before" else W_AFTER)[i % 5]
        tpl = tpl.replace("{W}", w[0].upper() + w[1:]).replace("{w}", w)
    elif cell == "year_first_gen":
        d = f"{dt.year}-{year_suffix(dt.year)} il {MONTHS_GEN[dt.month - 1]} {dt.day}"
        tpl = Y_GEN[i % 5].replace("{s}", (_LOC if i % 2 else _POSS)[day_key(dt.day)])
    else:
        ys = f"{dt.year}-{year_suffix(dt.year)}"
        d = f"{ys} ilin {dt.day} {MONTHS[dt.month - 1]}" if i % 3 else f"{ys} il, {dt.day} {MONTHS[dt.month - 1]}"
        tpl = Y_ILIN[i % 5]
    tpl = tpl.replace("{y}", "{d}")
    pre, post = tpl.split("{d}")
    return pre + d + post, (len(pre), len(pre) + len(d))


def build(seed: int) -> list[dict]:
    r = random.Random(seed)
    rows = []
    for cell in CELLS:
        for i in range(PER_CELL):
            text, (s, e) = doc_for(r, cell, i)
            rec = {"id": f"{FAMILY}_{len(rows) + 1:03d}", "text": text, "lang": "az", "family": FAMILY, "role": cell,
                   "entities": [{"start": s, "end": e, "label": "DATE", "cell": cell}]}
            if i % 3 == 0:
                w = r.choice(WEEKDAYS)
                pre, post = r.choice(CONTROL).split("{w}")
                text += " " + pre
                rec["controls"] = [{"start": len(text), "end": len(text) + len(w), "resembles": "DATE",
                                    "kind": "weekday_alone"}]
                rec["text"] = text + w + post
            rows.append(rec)
    return rows


WD_RE = re.compile("|".join(sorted(WEEKDAYS, key=len, reverse=True)), re.I)
SHAPE = {
    "plain": re.compile(r"\d{1,2} [a-z]+ \d{4}|\d{2}\.\d{2}\.\d{4}"),
    "weekday_before": re.compile(r"\d{1,2} [a-z]+ \d{4}|\d{2}\.\d{2}\.\d{4}"),
    "weekday_after": re.compile(r"\d{1,2} [a-z]+ \d{4}|\d{2}\.\d{2}\.\d{4}"),
    "year_first_gen": re.compile(r"\d{4}-c[iıuü] il [a-z]+ın \d{1,2}|\d{4}-c[iıuü] il [a-z]+(ın|in|un) \d{1,2}"),
    "year_first_ilin": re.compile(r"\d{4}-c[iıuü] il(in|,) \d{1,2} [a-z]+"),
}


def check(rows: list[dict]) -> list[str]:
    bad = []
    for x in rows:
        t, ents = x["text"], x["entities"]
        if len(ents) != 1:
            bad.append(f"{x['id']}: needs one DATE")
            continue
        s = ents[0]
        span = t[s["start"]:s["end"]]
        if span != span.strip() or not SHAPE[s["cell"]].fullmatch(span):
            bad.append(f"{x['id']}: DATE shape {s['cell']}")
        if WD_RE.search(span):
            bad.append(f"{x['id']}: weekday inside DATE")
        if s["cell"].startswith("weekday") and not WD_RE.search(t[max(0, s["start"] - 20):s["end"] + 20]):
            bad.append(f"{x['id']}: no weekday next to the date")
        if s["cell"] == "year_first_gen" and not re.match(r"-(s?[iıuü]|d[əa])\b", t[s["end"]:]):
            bad.append(f"{x['id']}: suffix after the day")
        for c in x.get("controls", []):
            if not WD_RE.fullmatch(t[c["start"]:c["end"]]) or c["start"] < s["end"]:
                bad.append(f"{x['id']}: control")
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=82)
    ap.add_argument("--out", type=Path, default=HERE)
    a = ap.parse_args(argv)
    rows = build(a.seed)
    problems = check(rows)
    (a.out / f"{FAMILY}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    print(f"{FAMILY}: {len(rows)} documents ({len(CELLS)} cells x {PER_CELL}), "
          f"{sum(len(x.get('controls', [])) for x in rows)} weekday-alone controls; problems: {len(problems)}")
    for p in problems[:20]:
        print("  ", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
