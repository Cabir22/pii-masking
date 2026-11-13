"""v4.2 fix list: the target shapes in two targeted builds, per 25,000 documents.

    python reports/v42_generator/compare.py <v4.1 build.jsonl> <v4.2 build.jsonl> [--md out.md]

Shapes are counted by value (not by kind name), so the near misses the old
kinds already drew count too. Look-alikes are `_decoys` spans; real values
are `entities`.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROWS = [
    # (group, row, function(record) -> count)
]


def _decoy_vals(r, resembles=None):
    for d in r.get("_decoys") or []:
        if resembles is None or d.get("resembles") == resembles:
            yield d, r["text"][d["start"]:d["end"]]


def _ents(r, label):
    for e in r["entities"]:
        if e["label"] == label:
            yield e, r["text"][e["start"]:e["end"]]


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


def row(group, name):
    def deco(fn):
        ROWS.append((group, name, fn))
        return fn
    return deco


@row("Must: C4 time", "time look-alikes, hour 24-29")
def _(r):
    return sum(bool(re.fullmatch(r"2[4-9]:[0-5]\d", v)) for _, v in _decoy_vals(r, "TIME"))


@row("Must: C4 time", "time look-alikes, minute 60-69")
def _(r):
    return sum(bool(re.fullmatch(r"([01]\d|2[0-3]):6\d", v)) for _, v in _decoy_vals(r, "TIME"))


@row("Must: C4 date / A5 invalid dates", "date look-alikes, 29-31 February (29 only in a non-leap year)")
def _(r):
    n = 0
    for _, v in _decoy_vals(r, "DATE"):
        p = _date_parts(v)
        n += bool(p and p[1] == 2 and (p[2] in (30, 31) or (p[2] == 29 and not _leap(p[0]))))
    return n


@row("Must: C4 date / A5 invalid dates", "date look-alikes, month 13-19")
def _(r):
    return sum(bool((p := _date_parts(v)) and 13 <= p[1] <= 19) for _, v in _decoy_vals(r, "DATE"))


@row("Must: C4 date / A5 invalid dates", "date look-alikes, ISO with month 13-19 or 29-31 Feb")
def _(r):
    n = 0
    for _, v in _decoy_vals(r, "DATE"):
        m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", v)
        if m:
            y, mo, d = int(m[1]), int(m[2]), int(m[3])
            n += 13 <= mo <= 19 or (mo == 2 and (d in (30, 31) or (d == 29 and not _leap(y))))
    return n


@row("Must: A5 IBAN", "IBAN-shaped codes of 18-27 characters (`AA99AAAA9999999999`)")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Z]{2}\d{2}[A-Z]{4}\d{10,19}", v)) for _, v in _decoy_vals(r, "IBAN"))


@row("Must: A5 IBAN", "a bare country code (`AZ`) after country-code words (D-55b)")
def _(r):
    return sum(d["kind"] == "iban_country_code" for d, _ in _decoy_vals(r))


@row("Must: A5 licence", "three letters + 6 digits (`AAA999999`), any look-alike")
def _(r):
    return sum(bool(re.fullmatch(r"[A-Z]{3}\d{6}", v)) for _, v in _decoy_vals(r))


@row("Must: A5 licence", "... in the licence slot, beside a real licence")
def _(r):
    return sum(d["kind"] == "licence_three_letters" for d, _ in _decoy_vals(r))


@row("Must: C4 FIN", "patterned FIN dummies (`A12B34`)")
def _(r):
    return sum(d["kind"] == "fin_dummy_pattern" for d, _ in _decoy_vals(r))


@row("Must: C4 IPv4", "3-part IPv4 look-alikes (`99.99.9`)")
def _(r):
    return sum(bool(re.fullmatch(r"\d{1,3}\.\d{1,3}\.\d{1,3}", v)) for _, v in _decoy_vals(r, "IPV4_ADDRESS"))


@row("Must: C4 IPv4", "real IPv4")
def _(r):
    return sum(1 for _ in _ents(r, "IPV4_ADDRESS"))


@row("Should: seconds-times in ranges", "TIME with seconds")
def _(r):
    return sum(bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", v)) for _, v in _ents(r, "TIME"))


@row("Should: seconds-times in ranges", "... followed by a dash or a case ending (`-`, `–`, `—`, `-dan`)")
def _(r):
    t = r["text"]
    return sum(bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", v) and re.match(r"\s?[-–—]", t[e["end"]:e["end"] + 2]))
               for e, v in _ents(r, "TIME"))


@row("Should: seconds-times in ranges", "... with a case ending (`14:00:00-dan`, `-ə qədər`)")
def _(r):
    t = r["text"]
    return sum(bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", v) and re.match(r"-(d[aə]n|y?[aə] |dək)", t[e["end"]:e["end"] + 5]))
               for e, v in _ents(r, "TIME"))


@row("Should: IBAN boundaries", "IBAN in a typed grouping (`AZ 21 ...`, part-grouped, dashes)")
def _(r):
    n = 0
    for _, v in _ents(r, "IBAN"):
        clean_fours = re.fullmatch(r"[A-Za-z0-9]{4}( [A-Za-z0-9]{4})*( [A-Za-z0-9]{1,4})?", v)
        n += (" " in v or "-" in v) and not clean_fours
    return n


@row("Should: IBAN boundaries", "IBAN with an ending or a mark glued on (`...1944-dür`, `(...)`, `iban=`)")
def _(r):
    t = r["text"]
    return sum(bool(re.match(r"[-)]", t[e["end"]:e["end"] + 1]) or t[max(0, e["start"] - 1):e["start"]] in "(=")
               for e, _ in _ents(r, "IBAN"))


@row("Should: line-start names", "line-start look-alikes (roles, headings) in PII-free documents")
def _(r):
    if r["entities"]:
        return 0
    t = r["text"]
    return sum(d.get("resembles") == "GIVENNAME" and (d["start"] == 0 or t[d["start"] - 1] == "\n")
               for d, _ in _decoy_vals(r))


@row("Should: line-start names", "line-start GIVENNAME, labelled")
def _(r):
    t = r["text"]
    return sum(e["start"] == 0 or t[e["start"] - 1] == "\n" for e, _ in _ents(r, "GIVENNAME"))


@row("Should: 19-digit codes", "19-digit look-alikes without `89` (not ICCID, not a card)")
def _(r):
    return sum(bool(re.fullmatch(r"\d{19}", v) and not v.startswith("89")) for _, v in _decoy_vals(r))


@row("Should: 19-digit codes", "real ICCID")
def _(r):
    return sum(1 for _ in _ents(r, "ICCID"))


@row("Should: street vs city", "STREET named after a town (`Gəncə prospekti`)")
def _(r, _towns=None):
    from piigen.locales import az
    return sum(any(v.startswith(c + " ") for c in az.CITIES) for _, v in _ents(r, "STREET"))


@row("Should: street vs city", "STREET, all")
def _(r):
    return sum(1 for _ in _ents(r, "STREET"))


def _spec_count(key, value):
    def fn(r):
        return sum(x == value for x in r.get("_spec", {}).get(key, []))
    return fn


for _name, _key, _value in (("IP prose sentences ending with `;`", "ip_ends", "semicolon"),
                            ("IP prose sentences ending with nothing (then a line break)", "ip_ends", "bare"),
                            ("IPs ending a chat line", "net_layouts", "chat"),
                            ("IPs ending a log line", "net_layouts", "log")):
    ROWS.append(("D-56a (1) IPs without a final period", _name, _spec_count(_key, _value)))


@row("D-56a (2) IPv4 swing", "4-part look-alikes, an octet over 255 beside a one-digit octet (`256.1.1.1`)")
def _(r):
    n = 0
    for _, v in _decoy_vals(r, "IPV4_ADDRESS"):
        o = v.split(".")
        n += (len(o) == 4 and all(x.isdigit() for x in o) and any(int(x) > 255 for x in o)
              and any(len(x) == 1 for x in o))
    return n


@row("D-56a (2) IPv4 swing", "sequential IPv4 dummies (`1.2.3.4`)")
def _(r):
    return sum(d["kind"] == "policy_sequential_ipv4" for d, _ in _decoy_vals(r))


@row("D-56a (3) short ID words", "ID cards / licences right after `ID` or `ID nömrə…`")
def _(r):
    t = r["text"]
    return sum(e["label"] in ("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER")
               and bool(re.search(r"\bID( nömrə\w*)?:? $", t[max(0, e["start"] - 25):e["start"]]))
               for e in r["entities"])


@row("A5 overall", "PII-free documents with a look-alike of IBAN / licence / IPv4 / VÖEN / ICCID")
def _(r):
    return int(not r["entities"] and any(d.get("resembles") in
               ("IBAN", "AZ_DRIVER_LICENSE_NUMBER", "IPV4_ADDRESS", "AZ_VOEN", "ICCID") for d in r.get("_decoys") or []))


@row("A5 overall", "PII-free documents")
def _(r):
    return int(not r["entities"])


def count(path: Path) -> tuple[int, list[int]]:
    tot = [0] * len(ROWS)
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            n += 1
            for i, (_, _, fn) in enumerate(ROWS):
                tot[i] += fn(r)
    return n, tot


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
    ap = argparse.ArgumentParser()
    ap.add_argument("v41")
    ap.add_argument("v42")
    ap.add_argument("--md")
    a = ap.parse_args()
    (n1, c1), (n2, c2) = count(Path(a.v41)), count(Path(a.v42))
    lines = ["| Item | Shape | v4.1 (28k) | v4.2 (30k) |", "|---|---|---|---|"]
    for (group, name, _), x, y in zip(ROWS, c1, c2):
        lines.append(f"| {group} | {name} | {round(x * 25000 / n1):,} | {round(y * 25000 / n2):,} |")
    text = (f"Per 25,000 documents. v4.1: {n1:,} documents (`main`, seed 20261001); "
            f"v4.2: {n2:,} documents (seed 20261001).\n\n" + "\n".join(lines) + "\n")
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
