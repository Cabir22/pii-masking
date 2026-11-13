"""m2's own relabel rows, beside D-70's list: writes scripts/relabel/m2_extra_list.tsv (relabel.py's format).

  * D-76a: group ages are not AGE. The 364 rows the team decided `remove` in scripts/relabel/inputs/group_ages_review.csv,
    in AZ and in every translation. A translated span is the same-position AGE entity (the k-th AGE of the
    document, as D-70): every listed document must have as many AGE entities in the translation as in AZ, and
    the counts must match or the run stops. Translation mints new values, so in a document where only some AGEs are
    removed, a translated row is written only if the span's relative position in the text agrees with its order;
    otherwise the translated label stays (the privacy-safe side) and the row is reported. A document with no
    translation in a language gets a "not translated" row (relabel.py checks it is really absent).
  * D-66a / X-NOYR: year-less dates are DATE. Group `relabel` of scripts/relabel/inputs/noyr_relabel_ids.tsv (358 spans,
    native-read by) is added as DATE, **in AZ only** for m2: the translated date has other offsets
    and wording, so the translations follow in m3. With --year-before also group `year_before` (D-82 (2), D-82a:
    `⟦2025-ci ilin 12 may⟧`, one span from the year; 1,728 spans), only after its 100-row native check.
  * D-72 (b), D-84: a disguised e-mail is EMAIL. v4.2's old `OBFUSCATED_EMAIL` look-alike left ~1,900 per language
    unlabelled in train (`name [at] host [dot] com`, `name(at)host(dot)net`, `name AT host DOT org`, any case, 1-3
    spaces). Each one gets an EMAIL span from the first character of the name to the last of the domain, in AZ and
    in every translation (each translation is scanned on its own: the address is copied, not translated). Noise-
    broken ones (a line break or a typo inside) stay as they are.
  * D-82 (1): a weekday is outside DATE. reports/x_dfrag/weekday_relabel_ids.tsv (the team: 628 v4.2 DATEs with
    the weekday at the start or the end) gives the old span and the span without the weekday: the old DATE is
    removed and the trimmed one added, AZ only (the translations wrote no weekday next to these dates: 0 of
    ~500 documents per language).

No row may repeat a span of D-70's list (relabel.py would stop on a span listed twice).

  python scripts/relabel/build_m2_extra_list.py --az-dir data/processed/m2/_in/az --tr-dir data/processed/m2/_in [--year-before]
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from relabel import sha16  # noqa: E402

SPLITS = ("train", "val", "test")
LANGS = ("en", "tr", "ru")
COLS = ["lang", "split", "doc_id", "start", "end", "label", "value", "text_sha16", "reason", "relabel_to"]
GROUP_AGES = ROOT / "scripts" / "relabel" / "inputs" / "group_ages_review.csv"
NOYR = ROOT / "scripts" / "relabel" / "inputs" / "noyr_relabel_ids.tsv"
WEEKDAYS = ROOT / "reports" / "x_dfrag" / "weekday_relabel_ids.tsv"
_AT = r"(?:[ \t]{0,3}(?i:\[at\]|\(at\))[ \t]{0,3}|[ \t]{1,3}AT[ \t]{1,3})"
_DOT = r"(?:[ \t]{0,3}(?i:\[dot\]|\(dot\))[ \t]{0,3}|[ \t]{1,3}DOT[ \t]{1,3})"
DISGUISED_EMAIL = re.compile(rf"(?<![\w.+-])[\w.+-]+{_AT}[\w-]+(?:{_DOT}[\w-]+)+(?![\w-])")
STAMP_AFTER = re.compile(r"^[ T,]*\d{1,2}:\d{2}")   # D-17: a date followed by a time is a timestamp, not DATE
D70 = HERE / "d70_list.tsv"
OUT = HERE / "m2_extra_list.tsv"


def read_docs(folder: Path, key: str) -> dict[str, dict]:
    docs = {}
    for split in SPLITS:
        with (folder / f"{split}.docs.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    d["_split"] = split
                    docs[d[key]] = d
    return docs


def nearest(aa: list[dict], atext: str, ta: list[dict], ttext: str, k: int) -> int:
    """The translated AGE whose relative position in the text is nearest the k-th Azerbaijani one's."""
    pos = aa[k]["start"] / max(1, len(atext))
    return min(range(len(ta)), key=lambda j: abs(ta[j]["start"] / max(1, len(ttext)) - pos))


def disguised(lang: str, docs: dict[str, dict], rows: list, problems: list, counts: Counter) -> None:
    """D-84: every disguised e-mail of `docs` (keyed by the AZ id) as an EMAIL add row."""
    for key, d in sorted(docs.items()):
        t = d["text"]
        for m in DISGUISED_EMAIL.finditer(t):
            s, e = m.span()
            if any(x["start"] < e and s < x["end"] for x in d["entities"]):
                problems.append(f"{lang} {key} {s}:{e}: disguised e-mail overlaps a label")
                continue
            rows.append([lang, d["_split"], key, s, e, "", t[s:e], sha16(t), "D-84: disguised e-mail (D-72 (b))", "EMAIL"])
            counts[f"{lang} disguised e-mails"] += 1


def ages(doc: dict) -> list[dict]:
    return sorted((e for e in doc["entities"] if e["label"] == "AGE"), key=lambda e: e["start"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--az-dir", type=Path, required=True, help="runb-az-v4.2's {split}.docs.jsonl")
    ap.add_argument("--tr-dir", type=Path, required=True, help="runb-translated-v4.2: {en,tr,ru}/{split}.docs.jsonl")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--noyr-list", type=Path, default=NOYR)
    ap.add_argument("--weekday-list", type=Path, default=WEEKDAYS)
    ap.add_argument("--year-before", action="store_true",
                    help="also X-NOYR's year_before group (D-82a: only after its 100-row native check)")
    a = ap.parse_args(argv)
    az = read_docs(a.az_dir, "id")
    with D70.open(encoding="utf-8", newline="") as f:
        d70 = {(r["lang"], r["doc_id"], r["start"], r["end"]) for r in csv.DictReader(f, delimiter="\t")}
    rows, problems, unsure = [], [], []

    # D-76a: group ages, every language
    with GROUP_AGES.open(encoding="utf-8-sig", newline="") as f:
        ga = list(csv.DictReader(f))
    dec = next(k for k in ga[0] if k.startswith("decision"))
    remove = [r for r in ga if r[dec].strip().lower() == "remove"]
    by_doc: dict[str, list[dict]] = {}
    for r in remove:
        d = az[r["doc_id"]]
        s, e = int(r["start"]), int(r["end"])
        hit = [i for i, x in enumerate(ages(d)) if x["start"] == s and x["end"] == e]
        if len(hit) != 1 or d["text"][s:e] != r["value"]:
            problems.append(f"az {r['gid']}: no AGE {r['value']!r} at {s}:{e} in {r['doc_id']}")
            continue
        by_doc.setdefault(r["doc_id"], []).append({"k": hit[0], "gid": r["gid"]})
    reason = "D-76a: group age, not a person's age"
    for doc_id, items in sorted(by_doc.items()):
        d = az[doc_id]
        for it in sorted(items, key=lambda x: x["k"]):
            x = ages(d)[it["k"]]
            rows.append(["az", d["_split"], doc_id, x["start"], x["end"], "AGE", d["text"][x["start"]:x["end"]],
                         sha16(d["text"]), f"{reason} ({it['gid']})", ""])
    counts = Counter({"az": sum(len(v) for v in by_doc.values())})
    disguised("az", az, rows, problems, counts)
    for lang in LANGS:
        tr = read_docs(a.tr_dir / lang, "source_id")
        disguised(lang, tr, rows, problems, counts)
        for doc_id, items in sorted(by_doc.items()):
            d = az[doc_id]
            t = tr.get(doc_id)
            if t is None:
                rows.append([lang, d["_split"], doc_id, "", "", "AGE", "", "", "not translated (rejected)", ""])
                counts[f"{lang} absent"] += 1
                continue
            ta, aa = ages(t), ages(d)
            if len(ta) != len(aa):
                problems.append(f"{lang} {doc_id}: {len(ta)} AGE entities, AZ has {len(aa)}")
                continue
            mixed = len(items) < len(aa)
            for it in sorted(items, key=lambda x: x["k"]):
                x = ta[it["k"]]
                v = t["text"][x["start"]:x["end"]]
                if mixed and nearest(aa, d["text"], ta, t["text"], it["k"]) != it["k"]:
                    counts[f"{lang} kept (position unsure)"] += 1      # the label stays: the privacy-safe side
                    unsure.append(f"{lang}\t{doc_id}\t{it['gid']}\t{v}")
                    continue
                rows.append([lang, t["_split"], doc_id, x["start"], x["end"], "AGE", v, sha16(t["text"]),
                             f"{reason} ({it['gid']})", ""])
                counts[lang] += 1

    # X-NOYR: year-less dates (and with --year-before the year-first ones), AZ only
    groups = ("relabel", "year_before") if a.year_before else ("relabel",)
    with a.noyr_list.open(encoding="utf-8", newline="") as f:
        noyr = [r for r in csv.DictReader(f, delimiter="\t") if r["group"] in groups]
    for r in sorted(noyr, key=lambda r: (r["id"], int(r["start"]))):
        d = az[r["id"]]
        s, e = int(r["start"]), int(r["end"])
        if r["split"] != d["_split"]:
            problems.append(f"X-NOYR {r['id']}: split {r['split']} != {d['_split']}")
        if any(x["start"] < e and s < x["end"] for x in d["entities"]):
            problems.append(f"X-NOYR {r['id']} {s}:{e}: overlaps a labelled span")
        if STAMP_AFTER.match(d["text"][e:e + 12]):
            counts[f"az X-NOYR {r['group']} skipped (timestamp, D-17)"] += 1
            continue
        what = "D-66a X-NOYR: year-less date" if r["group"] == "relabel" else "D-82a: year-first date, from the year"
        rows.append(["az", d["_split"], r["id"], s, e, "", d["text"][s:e], sha16(d["text"]),
                     f"{what} ({r['form']}, {r['kind']})", "DATE"])
        counts[f"az X-NOYR {r['group']}"] += 1

    # D-82 (1): the weekday out of DATE, AZ only: the old span removed, the trimmed span added
    with a.weekday_list.open(encoding="utf-8", newline="") as f:
        wd = list(csv.DictReader(f, delimiter="\t"))
    for r in sorted(wd, key=lambda r: (r["id"], int(r["start"]))):
        d = az[r["id"]]
        t = d["text"]
        s, e, ns, ne = int(r["start"]), int(r["end"]), int(r["new_start"]), int(r["new_end"])
        if r["split"] != d["_split"]:
            problems.append(f"weekday {r['id']}: split {r['split']} != {d['_split']}")
        if not (s <= ns < ne <= e and (ns, ne) != (s, e)) or not any(ch.isdigit() for ch in t[ns:ne]):
            problems.append(f"weekday {r['id']} {s}:{e} -> {ns}:{ne}: not a trim that keeps a digit")
        rest = (t[s:ns] + " " + t[ne:e]).strip(" ,()")
        if not rest or any(ch.isdigit() for ch in rest):
            problems.append(f"weekday {r['id']}: the part cut off ({rest!r}) is not a weekday")
        h = sha16(t)
        rows.append(["az", d["_split"], r["id"], s, e, "DATE", t[s:e], h, f"D-82 (1): weekday out of DATE ({r['side']})", ""])
        rows.append(["az", d["_split"], r["id"], ns, ne, "", t[ns:ne], h, f"D-82 (1): the date without the weekday ({r['side']})", "DATE"])
        counts["az weekday trims"] += 1

    twice = [r for r in rows if r[3] != "" and (r[0], r[2], str(r[3]), str(r[4])) in d70]
    problems += [f"{r[0]} {r[2]} {r[3]}:{r[4]}: already in D-70's list" for r in twice]
    if problems:
        print(f"STOPPED, {len(problems)} problem(s):", *problems[:20], sep="\n  ", file=sys.stderr)
        return 1
    with a.out.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(COLS)
        w.writerows(rows)
    print(f"{a.out}: {len(rows)} rows; {dict(counts)}")
    for u in unsure:
        print("  position unsure, label kept:", u)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
