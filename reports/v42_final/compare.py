"""D-57 (v4.2 final fix list): every Must and Should item counted in two
targeted builds, and every real value per label and context.

    python reports/v42_final/compare.py <v4.2 build.jsonl> <new build.jsonl> [--md out.md]

Shapes are counted by value (not by kind name), so look-alikes the old kinds
already drew count too. Look-alikes are `_decoys` spans; real values are
`entities`. "PII-free" is a document with no entity. Item rows are per 25,000
documents (the fix list's unit); the label x context table is in absolute
counts, since D-57 asks that no real-value count goes down against v4.2.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import statistics
from pathlib import Path

ROWS = []          # (group, row, function(record) -> count)


def row(group, name):
    def deco(fn):
        ROWS.append((group, name, fn))
        return fn
    return deco


def _decoys(r, resembles=None):
    for d in r.get("_decoys") or []:
        if resembles is None or d.get("resembles") == resembles:
            yield d, r["text"][d["start"]:d["end"]]


def _ents(r, label=None):
    for e in r["entities"]:
        if label is None or e["label"] == label:
            yield e, r["text"][e["start"]:e["end"]]


def _pii_free(r) -> bool:
    return not r["entities"]


def _leap(y: int) -> bool:
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def _date_parts(v):
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        return int(m[1]), int(m[2]), int(m[3])
    m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", v)
    if m:
        return int(m[3]), int(m[2]), int(m[1])
    return None


def _near_date(v) -> bool:
    """D-57 M1: an impossible day (30/31 Feb, 31 in a 30-day month, day 32),
    month 13-19, or 29 Feb in a non-leap year."""
    p = _date_parts(v)
    if not p:
        return False
    y, m, d = p
    if 13 <= m <= 19:
        return True
    if m == 2 and (d in (30, 31) or (d == 29 and not _leap(y))):
        return True
    return 1 <= m <= 12 and (d == 32 or (d == 31 and m in (4, 6, 9, 11)))


def _line_prefix(text: str, s: int) -> str:
    return text[text.rfind("\n", 0, s) + 1:s]


def _after_label(text: str, s: int) -> bool:
    """`Field: value` (a short field name and a colon, alone before the value on its line)."""
    return bool(re.fullmatch(r"\s*[^\n:|,;]{1,40}:\s*", _line_prefix(text, s)))


def _line_end(text: str, e: int) -> bool:
    return e == len(text) or text[e] == "\n"


def _in_table(r, s: int) -> bool:
    if r["_spec"].get("format") or r["_spec"].get("cvv_rows"):
        return True
    ls = r["text"].rfind("\n", 0, s) + 1
    le = r["text"].find("\n", s)
    line = r["text"][ls:le if le != -1 else len(r["text"])]
    return line.count("|") >= 2 or line.count(";") >= 2 or (line.count(",") >= 2 and " " not in line.strip())


def context(r, s: int, e: int) -> str:
    """The context of a span: a table cell, after a field name (`Field: value`),
    the start of a line, or prose."""
    if _in_table(r, s):
        return "table"
    if _after_label(r["text"], s):
        return "after a label"
    if not _line_prefix(r["text"], s).strip():
        return "line start"
    return "prose"


# --------------------------------------------------------------------------- #
# Must
# --------------------------------------------------------------------------- #

@row("M1 PII-free near misses", "PII-free: near-miss date look-alikes")
def _(r):
    return sum(_near_date(v) for _, v in _decoys(r, "DATE")) if _pii_free(r) else 0


@row("M1 PII-free near misses", "PII-free: short IBAN-like codes (AZ99AAAA + digits, < 28)")
def _(r):
    return sum(bool(re.fullmatch(r"AZ\d{2}[A-Z]{4}\d{10,19}", v)) for _, v in _decoys(r, "IBAN")) \
        if _pii_free(r) else 0


@row("M1 PII-free near misses", "PII-free: ... of them exactly 18 characters")
def _(r):
    return sum(bool(re.fullmatch(r"AZ\d{2}[A-Z]{4}\d{10}", v)) for _, v in _decoys(r, "IBAN")) \
        if _pii_free(r) else 0


@row("M1 PII-free near misses", "PII-free: bare AZ")
def _(r):
    return sum(v == "AZ" for _, v in _decoys(r, "IBAN")) if _pii_free(r) else 0


@row("M1 PII-free near misses", "PII-free: three-letter licence shapes AAA999999")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Z]{3}\d{6}", v)) for _, v in _decoys(r, "AZ_DRIVER_LICENSE_NUMBER")) \
        if _pii_free(r) else 0


@row("M1 PII-free near misses", "PII-free: near-miss times (hour 24-29, minute 60-69)")
def _(r):
    return sum(bool(re.fullmatch(r"2[4-9]:[0-5]\d|([01]\d|2[0-3]):6\d", v)) for _, v in _decoys(r, "TIME")) \
        if _pii_free(r) else 0


_M1 = ("DATE", "IBAN", "AZ_DRIVER_LICENSE_NUMBER", "TIME")


def _m1(r, d, v) -> bool:
    lab = d.get("resembles")
    return ((lab == "DATE" and _near_date(v)) or (lab == "IBAN" and (v == "AZ" or re.fullmatch(
        r"AZ\d{2}[A-Z]{4}\d{10,19}", v))) or (lab == "AZ_DRIVER_LICENSE_NUMBER" and re.fullmatch(
        r"[A-Z]{3}\d{6}", v)) or (lab == "TIME" and re.fullmatch(r"2[4-9]:[0-5]\d|([01]\d|2[0-3]):6\d", v)))


@row("M1 PII-free near misses", "PII-free: ... of all the above, in `Label: value` lines or tables")
def _(r):
    if not _pii_free(r):
        return 0
    return sum(bool(_m1(r, d, v)) and (_after_label(r["text"], d["start"]) or _in_table(r, d["start"]))
               for d, v in _decoys(r))


@row("M2 PII-free documents", "PII-free documents (targeted)")
def _(r):
    return int(_pii_free(r))


@row("M2 PII-free documents", "PII-free documents with a table")
def _(r):
    return int(_pii_free(r) and any(line.count("|") >= 2 or line.count(";") >= 2
                                    for line in r["text"].split("\n")))


@row("M3 FIN", "FIN look-alikes dashed after the 2nd or 4th character")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Z0-9]{2}-[A-Z0-9]{4}|[A-Z0-9]{4}-[A-Z0-9]{2}", v))
               for _, v in _decoys(r, "AZ_FIN"))


@row("M3 FIN", "FIN look-alikes dashed 3-3")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Z0-9]{3}-[A-Z0-9]{3}", v)) for _, v in _decoys(r, "AZ_FIN"))


@row("M3 FIN", "FIN look-alikes right before the word FİN")
def _(r):
    return sum(bool(re.match(r"\s+F[İI]N", r["text"][d["end"]:d["end"] + 6])) for d, _ in _decoys(r, "AZ_FIN"))


@row("M3 FIN", "real FINs right before the word FİN")
def _(r):
    return sum(bool(re.match(r"\s+F[İI]N", r["text"][e["end"]:e["end"] + 6])) for e, _ in _ents(r, "AZ_FIN"))


@row("M4 dates before their noun", "Feb 30/31 and month 13-19 look-alikes before `tarix…`")
def _(r):
    n = 0
    for d, v in _decoys(r, "DATE"):
        p = _date_parts(v)
        if p and ((p[1] == 2 and p[2] in (30, 31)) or 13 <= p[1] <= 19) \
                and re.match(r"\s+tarix", r["text"][d["end"]:d["end"] + 8]):
            n += 1
    return n


@row("M4 dates before their noun", "real dates before `tarix…`")
def _(r):
    return sum(bool(re.match(r"\s+tarix", r["text"][e["end"]:e["end"] + 8])) for e, _ in _ents(r, "DATE"))


@row("M5 CVV", "5-digit CVV look-alikes at a line end after `CVV kodu:`")
def _(r):
    return sum(bool(re.fullmatch(r"\d{5}", v)) and _line_end(r["text"], d["end"])
               and bool(re.search(r"CVV kodu:\s*$", _line_prefix(r["text"], d["start"])))
               for d, v in _decoys(r, "CARD_SECURITY_CODE"))


@row("M5 CVV", "2-digit CVV look-alikes")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}", v)) for _, v in _decoys(r, "CARD_SECURITY_CODE"))


@row("M5 CVV", "... in PII-free documents")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}", v)) for _, v in _decoys(r, "CARD_SECURITY_CODE")) \
        if _pii_free(r) else 0


@row("M6 IPv6", "IPv6 look-alikes with `::`")
def _(r):
    return sum("::" in v for _, v in _decoys(r, "IPV6_ADDRESS"))


@row("M6 IPv6", "... in PII-free documents")
def _(r):
    return sum("::" in v for _, v in _decoys(r, "IPV6_ADDRESS")) if _pii_free(r) else 0


@row("M6 IPv6", "real compressed IPv6 (`::`)")
def _(r):
    return sum("::" in v for _, v in _ents(r, "IPV6_ADDRESS"))


@row("M6 IPv6", "... mid-sentence")
def _(r):
    return sum("::" in v and context(r, e["start"], e["end"]) == "prose" for e, v in _ents(r, "IPV6_ADDRESS"))


@row("M6 IPv6", "... after a label")
def _(r):
    return sum("::" in v and context(r, e["start"], e["end"]) == "after a label"
               for e, v in _ents(r, "IPV6_ADDRESS"))


@row("M7 small A5 groups", "9-digit VÖEN look-alikes")
def _(r):
    return sum(bool(re.fullmatch(r"\d{9}", v)) for _, v in _decoys(r, "AZ_VOEN"))


@row("M7 small A5 groups", "... in PII-free documents")
def _(r):
    return sum(bool(re.fullmatch(r"\d{9}", v)) for _, v in _decoys(r, "AZ_VOEN")) if _pii_free(r) else 0


@row("M7 small A5 groups", "letters-only MAC look-alikes (AA:BB:...)")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Za-z]{2}([:-][A-Za-z]{2}){2,7}", v)) for _, v in _decoys(r, "MAC_ADDRESS"))


@row("M7 small A5 groups", "3-part IPv4 look-alikes")
def _(r):
    return sum(bool(re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}", v)) for _, v in _decoys(r, "IPV4_ADDRESS"))


@row("M7 small A5 groups", "... ending in one digit (`99.99.9`)")
def _(r):
    return sum(bool(re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d", v)) for _, v in _decoys(r, "IPV4_ADDRESS"))


# --------------------------------------------------------------------------- #
# Should
# --------------------------------------------------------------------------- #

_LOWER_WORD_BEFORE = re.compile(r"(?<![^\W\d_])[a-zəğıöüçş]+[ \t]+$")


@row("S1 ages", "real 2-digit ages after a lowercase word")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}", v)) and bool(_LOWER_WORD_BEFORE.search(r["text"][:e["start"]][-30:]))
               for e, v in _ents(r, "AGE"))


@row("S1 ages", "... without `yaş` right after")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}", v)) and bool(_LOWER_WORD_BEFORE.search(r["text"][:e["start"]][-30:]))
               and not re.match(r"\s*-?(yaş|yas)", r["text"][e["end"]:e["end"] + 6], re.I)
               for e, v in _ents(r, "AGE"))


@row("S1 ages", "age-shaped look-alikes (2-digit numbers declared as non-ages)")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}", v)) for _, v in _decoys(r, "AGE"))


def _caps(v: str) -> bool:
    letters = [c for c in v if c.isalpha()]
    return len(letters) >= 2 and all(c.isupper() for c in letters)


@row("S2 ALL-CAPS", "ALL-CAPS cities")
def _(r):
    return sum(_caps(v) for _, v in _ents(r, "CITY"))


@row("S2 ALL-CAPS", "ALL-CAPS given names and surnames")
def _(r):
    return sum(_caps(v) for e, v in _ents(r) if e["label"] in ("GIVENNAME", "SURNAME"))


@row("S2 ALL-CAPS", "ALL-CAPS heading words declared as controls")
def _(r):
    return sum(_caps(v) and d.get("resembles") in ("CITY", "GIVENNAME", "SURNAME") for d, v in _decoys(r))


_OPEN = "(\"«“'["


@row("S3 brackets and quotes", "cities, names and streets right after an opening bracket or quote")
def _(r):
    return sum(e["start"] > 0 and r["text"][e["start"] - 1] in _OPEN
               for e, _ in _ents(r) if e["label"] in ("CITY", "GIVENNAME", "SURNAME", "STREET"))


@row("S3 brackets and quotes", "... of them cities")
def _(r):
    return sum(e["start"] > 0 and r["text"][e["start"] - 1] in _OPEN for e, _ in _ents(r, "CITY"))


@row("S3 brackets and quotes", "quoted organisation/brand names built from a town word (unlabelled)")
def _(r):
    return sum(d.get("kind") == "policy_city_in_brand" for d, _ in _decoys(r))


_STREET_TYPE = re.compile(r"(küçəsi|prospekti|döngəsi|şossesi|bulvarı|dalanı|küç\.|pr\.)[ \t]+$", re.I)


@row("S4 building numbers", "real building numbers after a lowercase word")
def _(r):
    return sum(bool(_LOWER_WORD_BEFORE.search(r["text"][:e["start"]][-30:])) for e, _ in _ents(r, "BUILDINGNUM"))


@row("S4 building numbers", "... after a street-type word")
def _(r):
    return sum(bool(_STREET_TYPE.search(r["text"][:e["start"]][-20:])) for e, _ in _ents(r, "BUILDINGNUM"))


@row("S4 building numbers", "... after a label (`Bina: 12`)")
def _(r):
    return sum(_after_label(r["text"], e["start"]) for e, _ in _ents(r, "BUILDINGNUM"))


@row("S5 thinned labels", "ACCESS_TOKEN in prose")
def _(r):
    return sum(context(r, e["start"], e["end"]) == "prose" for e, _ in _ents(r, "ACCESS_TOKEN"))


@row("S5 thinned labels", "ACCESS_TOKEN in table cells")
def _(r):
    return sum(context(r, e["start"], e["end"]) == "table" for e, _ in _ents(r, "ACCESS_TOKEN"))


for _lab, _name in (("CARD_SECURITY_CODE", "CVV"), ("PAYMENT_CARD_NUMBER", "cards"),
                    ("AZ_VOEN", "VÖEN"), ("AZ_PASSPORT_NUMBER", "passports")):
    @row("S5 thinned labels", f"{_name} after a label")
    def _(r, _lab=_lab):
        return sum(context(r, e["start"], e["end"]) == "after a label" for e, _ in _ents(r, _lab))

    @row("S5 thinned labels", f"{_name} mid-sentence")
    def _(r, _lab=_lab):
        return sum(context(r, e["start"], e["end"]) == "prose" for e, _ in _ents(r, _lab))


@row("S5 thinned labels", "seconds-times closing a range")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", v))
               and bool(re.search(r"(\d[ \t]*[-–—][ \t]*|-d[aə]n[ \t]+)$", r["text"][max(0, e["start"] - 8):e["start"]]))
               for e, v in _ents(r, "TIME"))


@row("S6 recall guards", "real 29 February in a leap year")
def _(r):
    return sum(bool((p := _date_parts(v)) and p[1] == 2 and p[2] == 29 and _leap(p[0]))
               or bool(re.fullmatch(r"29 fevral (\d{4})", v) and _leap(int(v[-4:])))
               for _, v in _ents(r, "DATE"))


@row("S6 recall guards", "29 February look-alikes in a non-leap year")
def _(r):
    return sum(bool((p := _date_parts(v)) and p[1] == 2 and p[2] == 29 and not _leap(p[0]))
               for _, v in _decoys(r, "DATE"))


@row("S6 recall guards", "real dates on the 31st")
def _(r):
    return sum(bool((p := _date_parts(v)) and p[2] == 31) or v.startswith("31 ") for _, v in _ents(r, "DATE"))


@row("S6 recall guards", "day-31 look-alikes")
def _(r):
    return sum(bool((p := _date_parts(v)) and p[2] == 31) for _, v in _decoys(r, "DATE"))


@row("S6 recall guards", "real times in `saat X radələrində`")
def _(r):
    return sum(bool(re.match(r"\s*radələrində", r["text"][e["end"]:e["end"] + 14])) for e, _ in _ents(r, "TIME"))


@row("S6 recall guards", "time look-alikes in `saat X radələrində`")
def _(r):
    return sum(bool(re.match(r"\s*radələrində", r["text"][d["end"]:d["end"] + 14])) for d, _ in _decoys(r, "TIME"))


@row("S6 recall guards", "real times 23:5x")
def _(r):
    return sum(v.startswith("23:5") for _, v in _ents(r, "TIME"))


@row("S6 recall guards", "real times 00:0x")
def _(r):
    return sum(v.startswith("00:0") for _, v in _ents(r, "TIME"))


@row("S6 recall guards", "real `24:00` (labelled)")
def _(r):
    return sum(v in ("24:00", "24:00:00") for _, v in _ents(r, "TIME"))


@row("S6 recall guards", "`24:00` as a look-alike (must be 0)")
def _(r):
    return sum(v in ("24:00", "24:00:00") for _, v in _decoys(r, "TIME"))


@row("S7 floors", "contrast ipv6_mac documents")
def _(r):
    return int(r["_spec"].get("sub") == "ipv6_mac")


@row("S7 floors", "contrast licence_id documents")
def _(r):
    return int(r["_spec"].get("sub") == "licence_id")


@row("S7 floors", "postal documents")
def _(r):
    return int(r["_spec"]["family"] == "postal")


# --------------------------------------------------------------------------- #

def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def item_counts(records: list[dict]) -> dict:
    scale = 25000 / len(records)
    return {(g, n): sum(fn(r) for r in records) * scale for g, n, fn in ROWS}


def label_context(records: list[dict]) -> collections.Counter:
    c = collections.Counter()
    for r in records:
        for e in r["entities"]:
            c[(e["label"], context(r, e["start"], e["end"]))] += 1
    return c


def pii_free_shape(records: list[dict]) -> dict:
    pf = [r for r in records if _pii_free(r)]
    return {"documents": len(pf), "median characters": statistics.median(len(r["text"]) for r in pf) if pf else 0,
            "numbers per document": (sum(len(re.findall(r"\d+(?:[.,]\d+)?", r["text"])) for r in pf) / len(pf))
            if pf else 0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("new")
    ap.add_argument("--md")
    a = ap.parse_args()
    base, new = load(a.base), load(a.new)
    bi, ni = item_counts(base), item_counts(new)
    out = [f"# D-57: the v4.2 build against the fixed build", "",
           f"v4.2: `{Path(a.base).name}`, {len(base):,} documents; new: `{Path(a.new).name}`, {len(new):,} documents.",
           "", "## The fix-list items (per 25,000 documents)", "", "| Item | Row | v4.2 | new |", "|---|---|---|---|"]
    for g, n, _ in ROWS:
        out.append(f"| {g} | {n} | {bi[(g, n)]:.0f} | {ni[(g, n)]:.0f} |")
    bs, ns = pii_free_shape(base), pii_free_shape(new)
    out += ["", "## PII-free documents", "", "| | v4.2 | new |", "|---|---|---|"]
    out += [f"| {k} | {bs[k]:.1f} | {ns[k]:.1f} |" for k in bs]
    bl, nl = label_context(base), label_context(new)
    out += ["", "## Real values per label and context (absolute counts)", "",
            "| Label | Context | v4.2 | new | change |", "|---|---|---|---|---|"]
    down = []
    for key in sorted(set(bl) | set(nl)):
        b, n = bl[key], nl[key]
        ch = f"{(n - b) / b:+.1%}" if b else "new"
        out.append(f"| {key[0]} | {key[1]} | {b} | {n} | {ch} |")
        if n < b:
            down.append((key, b, n))
    bt, nt = collections.Counter(), collections.Counter()
    for (lab, _c), v in bl.items():
        bt[lab] += v
    for (lab, _c), v in nl.items():
        nt[lab] += v
    out += ["", "## Real values per label (absolute counts)", "", "| Label | v4.2 | new | change |", "|---|---|---|---|"]
    out += [f"| {lab} | {bt[lab]} | {nt[lab]} | {(nt[lab] - bt[lab]) / bt[lab]:+.1%} |" for lab in sorted(bt | nt)]
    out += ["", f"**Label x context cells that went down: {len(down)}**"]
    out += [f"- {k[0]} / {k[1]}: {b} -> {n}" for k, b, n in down]
    text = "\n".join(out)
    print(text)
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
