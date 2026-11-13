"""Tests for D-37 (the scoreboard records library versions and refuses tokenizers >= 0.23)
D-36d (the 6-character dummy FIN in punct_touching is a policy item) and D-39c (all 5 dashed
CVV look-alikes in decoy_cvv are policy items; D-41c: also the 3 in pii_free) and D-51d (card and
IBAN look-alikes whose only defect is the checksum are policy items, left out of C4).

Run:  python eval/test_scoreboard_versions.py
"""
from __future__ import annotations

import json
from collections import Counter
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import scoreboard as S  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


# --- D-37: version rule ------------------------------------------------------------------
for v, ok in (("0.22.2", True), ("0.21.4", True), ("0.19.1", True), ("0.22.2rc1", True),
              ("0.23.0", False), ("0.23.2", False), ("0.24.1", False), ("1.0.0", False)):
    check(S.tokenizers_ok(v) is ok, f"tokenizers_ok({v}) is {ok}", S.tokenizers_ok(v))

real = S.library_versions
try:
    S.library_versions = lambda: {"tokenizers": "0.23.2", "transformers": "5.16.1", "torch": "2.11", "python": "3.12"}
    try:
        S.check_versions()
        check(False, "check_versions refuses tokenizers 0.23.2")
    except SystemExit as e:
        check("D-37" in str(e) and "0.23.2" in str(e), "refusal names D-37 and the version", str(e)[:80])
    S.library_versions = lambda: {"tokenizers": "0.22.2", "transformers": "4.57.6", "torch": "2.11", "python": "3.12"}
    v = S.check_versions()
    check(v["tokenizers"] == "0.22.2" and set(v) == {"tokenizers", "transformers", "torch", "python"},
          "check_versions returns all four versions", v)
finally:
    S.library_versions = real

report = {"meta": {"name": "t", "model": "m", "revision_sha": "x", "revision_requested": None,
                   "git": {"sha": "abc", "dirty": False}, "date_utc": "d", "device": "cpu",
                   "versions": {"tokenizers": "0.22.2", "transformers": "4.57.6"}, "tracks": ["R"],
                   "data_version": {}}, "gates": [], "sets": {}}
md = S.render_md(report)
check("| Libraries | tokenizers 0.22.2, transformers 4.57.6 |" in md, "report header lists the versions")
del report["meta"]["versions"]
check("not recorded (report older than D-37)" in S.render_md(report), "older reports render without versions")

# --- D-36d: the 6-character dummy FIN is a policy item --------------------------------------
rows = {json.loads(l)["id"]: json.loads(l) for l in open(HERE / "probes" / "punct_touching.jsonl", encoding="utf-8")}
hn = [h for h in rows["punct_touching_022"].get("hard_negatives", []) if h["resembles"] == "AZ_FIN"]
check(len(hn) == 1 and hn[0]["kind"] == "policy_d36d" and hn[0]["policy"] is True,
      "punct_touching_022: the FIN look-alike is policy_d36d", hn)
check(len(rows["punct_touching_022"]["text"][hn[0]["start"]:hn[0]["end"]]) == 6, "it is the 6-character one")
others = [h for r in rows.values() for h in r.get("hard_negatives", []) if h["kind"] == "policy_d36d"]
check(len(others) == 1, "exactly one policy_d36d item in punct_touching", len(others))
t = json.loads((HERE / "probes" / "targets.json").read_text(encoding="utf-8"))
check("D-36d" in t["punct_touching"].get("policy_d36d", ""), "targets.json records the reason")

# --- D-39c: all 5 dashed CVV look-alikes are policy items, left out of C4 ------------------
cvv = [json.loads(l) for l in open(HERE / "probes" / "decoy_cvv.jsonl", encoding="utf-8")]
dashed = [(r["id"], h) for r in cvv for h in r.get("hard_negatives", []) if "-" in r["text"][h["start"]:h["end"]]]
check(len(dashed) == 5, "decoy_cvv has 5 dashed look-alikes", len(dashed))
check(all(h["policy"] is True and h["kind"] in ("policy_d34c", "policy_d39c") for _, h in dashed),
      "every dashed look-alike is a policy item", [(i, h["kind"]) for i, h in dashed])
check(sorted(i for i, h in dashed if h["kind"] == "policy_d39c") == ["decoy_cvv_006", "decoy_cvv_018", "decoy_cvv_024"],
      "D-39c moves 006, 018, 024")
check(all("-" not in r["text"][h["start"]:h["end"]] for r in cvv for h in r.get("hard_negatives", [])
          if not h["kind"].startswith("policy_d3")), "no dashed look-alike left in the scored bucket")
cond = t["decoy_cvv"]["conditions"][0]
check(set(cond.get("exclude_kinds", [])) == {"policy_d34c", "policy_d39c"}, "C4 leaves out both policy kinds", cond)
check("D-39c" in t["decoy_cvv"].get("policy_d39c", ""), "targets.json records the D-39c reason")

# --- D-41c: the 3 dashed CVVs in pii_free follow D-39c ----------------------------------------
pf = [json.loads(l) for l in open(HERE / "probes" / "pii_free.jsonl", encoding="utf-8")]
pd = [(r["id"], h) for r in pf for h in r.get("hard_negatives", [])
      if h["resembles"] == "CARD_SECURITY_CODE" and "-" in r["text"][h["start"]:h["end"]]]
check(sorted(i for i, _ in pd) == ["pii_free_005", "pii_free_017", "pii_free_021"], "pii_free: the 3 dashed CVVs", pd)
check(all(h["kind"] == "policy_d39c" and h["policy"] is True for _, h in pd), "pii_free: dashed CVVs are policy_d39c")
check("policy_d39c" in t["pii_free"]["conditions"][0].get("exclude_kinds", []), "pii_free target leaves them out")
check("D-41c" in t["pii_free"].get("policy_d39c", ""), "targets.json records the D-41c reason")


# --- D-51d: card/IBAN look-alikes whose only defect is the checksum are policy items -------
sys.path.insert(0, str(HERE / "probes"))
import build_probes as BP  # noqa: E402

card_ok = "4169" + "73" * 5 + "1"
card_ok = card_ok[:15] + BP._luhn(card_ok[:15])
card_bad = card_ok[:15] + str((int(card_ok[-1]) + 3) % 10)
iban_ok = BP.iban(__import__("random").Random(1), spaced=False)
iban_bad = iban_ok[:2] + f"{(int(iban_ok[2:4]) + 1) % 100:02d}" + iban_ok[4:]
for lab, v, want, name in (("PAYMENT_CARD_NUMBER", card_ok, False, "a valid card"),
                           ("PAYMENT_CARD_NUMBER", card_bad, True, "a 16-digit card failing only Luhn"),
                           ("PAYMENT_CARD_NUMBER", " ".join(card_bad[i:i + 4] for i in range(0, 16, 4)), True,
                            "the same, spaced"),
                           ("PAYMENT_CARD_NUMBER", "4" + card_bad[4:16], None, "13 digits"),
                           ("PAYMENT_CARD_NUMBER", "1" + card_bad[1:], False, "16 digits with no card prefix"),
                           ("PAYMENT_CARD_NUMBER", card_bad[:12], False, "12 digits"),
                           ("IBAN", iban_ok, False, "a valid IBAN"),
                           ("IBAN", iban_bad, True, "an IBAN failing only mod-97"),
                           ("IBAN", iban_ok[:8], False, "an 8-character IBAN fragment")):
    got = BP.checksum_only(lab, v)
    if want is None:  # 13 digits: checksum-only exactly when the Luhn digit is wrong
        want = v[-1] != BP._luhn(v[:-1])
    check(got is want, f"checksum_only: {name}", got)

d51 = Counter()
left = []
for f in sorted((HERE / "probes").glob("*.jsonl")):
    for line in open(f, encoding="utf-8"):
        r = json.loads(line)
        for h in r.get("hard_negatives", []):
            v = r["text"][h["start"]:h["end"]]
            if h["kind"] == "policy_d51d":
                d51[(f.stem, len("".join(v.split())))] += 1
                check(h["policy"] is True and h["resembles"] == "PAYMENT_CARD_NUMBER", f"{r['id']}: policy card", h)
            elif h["resembles"] in BP.D51D_LABELS and not h["policy"] and BP.checksum_only(h["resembles"], v):
                left.append(r["id"])
check(sum(d51.values()) == 24, "D-51d: 24 card look-alikes moved", dict(d51))
check(sum(v for (f, n), v in d51.items() if n == 13) == 11 and sum(v for (f, n), v in d51.items() if n == 16) == 13,
      "11 of 13 digits, 13 of 16", dict(d51))
check(sorted({f for f, _ in d51}) == ["anchor_distance", "decoy_card_iccid_iban", "inflected_anchor", "prose_card",
                                       "spaced_card_iban"], "the 5 families", sorted({f for f, _ in d51}))
check(left == [], "no checksum-only card/IBAN look-alike left in the scored bucket", left)
dc = [h for line in open(HERE / "probes" / "decoy_card_iccid_iban.jsonl", encoding="utf-8")
      for h in json.loads(line).get("hard_negatives", [])]
check(Counter((h["resembles"], h["kind"]) for h in dc) == Counter({("IBAN", "invalid_shape"): 4, ("ICCID", "invalid_shape"): 4,
                                                                  ("PAYMENT_CARD_NUMBER", "policy_d51d"): 4}),
      "decoy_card_iccid_iban: IBAN fragments and short ICCIDs stay scored", Counter((h["resembles"], h["kind"]) for h in dc))
check(t["decoy_card_iccid_iban"]["conditions"][0].get("exclude_kinds") == ["policy_d51d"], "C4 leaves out policy_d51d")
check(all("D-51d" in t[f].get("policy_d51d", "") for f, _ in d51), "targets.json records the D-51d reason per family")


# --- The team, 15 Oct: FIN look-alikes of 5-7 letters/digits are policy items ----------------
fl = []
for f in sorted((HERE / "probes").glob("*.jsonl")):
    for line in open(f, encoding="utf-8"):
        r = json.loads(line)
        for h in r.get("hard_negatives", []):
            v = r["text"][h["start"]:h["end"]]
            if h["kind"] == "policy_fin_len":
                fl.append((f.stem, len(v)))
            elif h["resembles"] == "AZ_FIN" and not h["policy"]:
                check("-" in v or not (5 <= len(v) <= 7), f"{r['id']}: no 5-7 character FIN look-alike left scored", v)
check(sorted(Counter(n for _, n in fl).items()) == [(5, 6), (7, 4)], "10 items: 6 of 5 digits, 4 of 7 characters", fl)
check(t["decoy_fin"]["conditions"][0]["exclude_kinds"] == ["policy_d34c", "policy_fin_len"], "C4 leaves them out")
check("policy_fin_len" in t["pii_free"]["conditions"][0]["exclude_kinds"], "pii_free leaves their documents out")
check(all("policy_fin_len" in t[f] for f in {f for f, _ in fl}), "targets.json records the reason per family")


# --- track R must load the shipped tokenizer as shipped (D-51a; transformers 5.x drops it) -------
V4 = ("your-hf-org/masking-az-runb-v4-seed42", "e4ca17842f005e5b103f1d32d21859360c92b258")
CK1 = ("your-hf-org/masking-multilingual", "3a0a6e5df228bdc89dd01312a728e10a78b3e3fb")
try:
    from transformers import AutoTokenizer
    v4_json = S.shipped_tokenizer_json(*V4)
    tok_v4 = AutoTokenizer.from_pretrained(V4[0], revision=V4[1]) if v4_json else None
    tok_ck1 = AutoTokenizer.from_pretrained(CK1[0], revision=CK1[1])
except Exception as e:  # models not in the local cache
    v4_json = None
    print(f"skipped the shipped-tokenizer check: {type(e).__name__}")
if v4_json:
    import transformers
    ok, detail = S.tokenizer_matches_shipped(tok_v4, v4_json)
    if S._version_tuple(transformers.__version__)[0] < 5:
        check(ok, "v4's tokenizer, as loaded here, isolates punctuation like its tokenizer.json", detail)
    else:
        check(not ok, "transformers 5.x drops v4's shipped pre-tokenizer, and the check catches it", detail)
    check(not S.tokenizer_matches_shipped(tok_ck1, v4_json)[0], "a plain XLM-R tokenizer against v4's tokenizer.json is caught")
    check(S.tokenizer_matches_shipped(tok_ck1, None)[0], "no tokenizer.json shipped: nothing to compare")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
