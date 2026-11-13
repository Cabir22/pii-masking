"""Tests for eval/probes/build_probes_runb.py (the Run B probe families).

Run:  python eval/test_probes_runb.py

Fixed seed, counts per family, offsets matching the text, the committed
files equal to a fresh build, and validity (scripts/piigen validators,
checking only).
"""
from __future__ import annotations

import ipaddress
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "probes"))

import build_probes_runb as R  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


def span(rec, s):
    return rec["text"][s["start"]:s["end"]]


# --- marked() and fill() on synthetic strings -------------------------------------
t, g, h, c = R.marked("A [[Bx|CITY|noise=double]] b {{qq|SURNAME|brand_not_person}} c <<dd|CITY|common_word>>.")
check(t == "A Bx b qq c dd.", "marked: marks removed", t)
check(g == [{"start": 2, "end": 4, "label": "CITY", "noise": "double"}], "marked: gold span and extra field", g)
check(h == [{"start": 7, "end": 9, "resembles": "SURNAME", "kind": "brand_not_person", "policy": False}],
      "marked: look-alike span", h)
check(c == [{"start": 12, "end": 14, "resembles": "CITY", "kind": "common_word"}], "marked: control span", c)
t, g, h, c = R.fill("x {a} y {b}", a=("g", "VAL", "DATE", {"form": "iso"}), b=("h", "TS", "DATE", "timestamp"))
check(t == "x VAL y TS" and t[g[0]["start"]:g[0]["end"]] == "VAL" and t[h[0]["start"]:h[0]["end"]] == "TS",
      "fill: offsets point at the values", (t, g, h))
check(g[0]["form"] == "iso" and h[0]["kind"] == "timestamp" and c == [], "fill: extra fields kept")

# --- fixed seed ----------------------------------------------------------------------
out, problems = R.run(34)
again, _ = R.run(34)
other, _ = R.run(35)
dump = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True)  # noqa: E731
check(dump(out) == dump(again), "seed 34 twice: identical output")
check(dump(out["contrast_ipv6_mac"]) != dump(other["contrast_ipv6_mac"]), "seed 35: other generated values")
check(dump(out["homograph_pairs"]) == dump(other["homograph_pairs"]), "hand-written family does not depend on the seed")
check(sorted(out) == sorted(R.FAMILIES), "exactly the eight Run B families", sorted(out))

# --- the committed files are this build -------------------------------------------------
for fam in R.FAMILIES:
    p = HERE / "probes" / f"{fam}.jsonl"
    disk = p.read_text(encoding="utf-8") if p.exists() else ""
    fresh = "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out[fam])
    check(disk == fresh, f"{fam}.jsonl equals a fresh seed-34 build")

# --- counts ----------------------------------------------------------------------------
DOCS = {"noisy_suffixes": 36, "contrast_token_key": 24, "contrast_ipv6_mac": 60, "contrast_licence_id": 26,
        "homograph_pairs": 16, "date_vs_timestamp": 22, "villages": 34, "foreign_names": 30}
for fam, rows in out.items():
    n_gold = sum(len(r["entities"]) for r in rows)
    n_neg = sum(len(r.get("hard_negatives", [])) + len(r.get("controls", [])) for r in rows)
    check(len(rows) == DOCS[fam], f"{fam}: document count", len(rows))
    check(n_gold >= 12 and n_neg >= 8, f"{fam}: >= 12 true values and >= 8 decoys/controls", (n_gold, n_neg))
    check(len({r["id"] for r in rows}) == len(rows), f"{fam}: unique ids")
    check(all(r["lang"] == "az" and r["family"] == fam and r["role"] for r in rows), f"{fam}: az, family, role")

net = out["contrast_ipv6_mac"]
v6 = [span(r, e) for r in net for e in r["entities"] if e["label"] == "IPV6_ADDRESS"]
macs = [(span(r, e), e["sep"]) for r in net for e in r["entities"] if e["label"] == "MAC_ADDRESS"]
decoys = [h for r in net for h in r.get("hard_negatives", [])]
check(len(v6) + len(macs) + len(decoys) >= 40, "IPv6/MAC: 40+ items", len(v6) + len(macs) + len(decoys))
check(sum("::" in v for v in v6) / len(v6) >= 0.8, "IPv6: >= 80% '::'-compressed", sum("::" in v for v in v6))
check({e["form"] for r in net for e in r["entities"] if e["label"] == "IPV6_ADDRESS"} == set(R.IPV6_FORMS),
      "IPv6: every form present")
check(all(sum(s == sep for _, s in macs) >= 4 for sep in R.MAC_SEPS), "MAC: >= 4 per separator (: - .)")
check(all({"colon": ":", "hyphen": "-", "dot": "."}[s] in v for v, s in macs), "MAC: separator matches its tag")
check({"md5_hash", "sha1_hash", "commit_hash", "timestamp", "timecode"} <= {h["kind"] for h in decoys},
      "IPv6/MAC decoys: hex hashes and timestamps present")
check(sum(r["role"] == "side_by_side" and len(r["entities"]) == 2 for r in net) == 10, "IPv6/MAC: 10 side by side")
for v in v6:
    ipaddress.IPv6Address(v)  # raises on a bad value

# --- contrast pairs keep their contrast --------------------------------------------------
for r in out["contrast_token_key"]:
    if r.get("same_body"):
        tok, key = (span(r, e) for e in sorted(r["entities"], key=lambda e: e["label"]))
        check(re.sub(r"^[a-z]+[_-]", "", tok) == re.sub(r"^[a-z]+_", "", key) and tok != key,
              f"{r['id']}: token and key share the body", (tok, key))
for r in out["contrast_licence_id"]:
    if r["role"] == "same_prefix":
        lab = {e["label"]: span(r, e) for e in r["entities"]}
        lic, idc = lab["AZ_DRIVER_LICENSE_NUMBER"], lab["AZ_ID_CARD_NUMBER"]
        check(lic[:2] == idc[:2] and lic[:2] in ("AA", "AB") and len(lic) == 8 and len(idc) == 9,
              f"{r['id']}: same AA/AB prefix, 6 vs 7 digits", (lic, idc))
for r in out["date_vs_timestamp"]:
    for h in r.get("hard_negatives", []):
        check(re.search(r"\d{1,2}:\d{2}", span(r, h)) and re.search(r"\d{4}", span(r, h)),
              f"{r['id']}: a timestamp has a date and a clock time", span(r, h))
for r in out["noisy_suffixes"]:
    check(all(x.get("noise") in ("harmony", "buffer", "double", "colloquial")
              for x in r["entities"] + r.get("controls", [])), f"{r['id']}: noise type tagged")
check(all(len(r["entities"]) == 1 and len(r["controls"]) == 1 for r in out["homograph_pairs"]),
      "homograph_pairs: one name use and one word use per document")
check(all(span(r, e)[:3].casefold() == span(r, c)[:3].casefold()
          for r in out["homograph_pairs"] for e, c in zip(r["entities"], r["controls"])),
      "homograph_pairs: both uses are the same word")

# --- offsets match the text ----------------------------------------------------------------
for fam, rows in out.items():
    for r in rows:
        spans = [(x["start"], x["end"]) for k in ("entities", "hard_negatives", "controls") for x in r.get(k, [])]
        ok = all(0 <= s < e <= len(r["text"]) and r["text"][s:e] == r["text"][s:e].strip() for s, e in spans)
        check(ok, f"{r['id']}: spans inside the text, no edge spaces")
        spans.sort()
        check(all(b[0] >= a[1] for a, b in zip(spans, spans[1:])), f"{r['id']}: no overlapping spans")
        check(not re.search(r"\[\[|\]\]|\{\{|\}\}|<<|>>|\{[A-Za-z]\}", r["text"]), f"{r['id']}: no marks left")

# --- validity and targets -------------------------------------------------------------------
_, problems = R.run(34, validators=str(HERE.parent / "scripts"))
check(problems == [], "every gold valid, every look-alike invalid, no benchmark value", problems[:5])
targets = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))
for fam, rows in out.items():
    check(fam in targets, f"{fam}: has a target")
    gold_labels = {e["label"] for r in rows for e in r["entities"]}
    for cond in targets.get(fam, {}).get("conditions", []):
        for lab in cond.get("labels", []) + ([cond["from"]] if "from" in cond else []):
            check(lab in gold_labels, f"{fam}: target label {lab} has gold in the family")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
