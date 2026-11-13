"""Tests for D-51e: benchmark (and, through the private list, shadow-dev) look-alikes that our own
privacy rules treat as real values go to the policy bucket: 7 capital letters, 6 letters and
digits, a +994 phone or 10 digits as a FIN look-alike, and a real date as a building-number
look-alike. B1 is judged without them (both models), shown with them.

Run:  python eval/test_policy_d51e.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import release_check as RC  # noqa: E402
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


# --- the rule ------------------------------------------------------------------------------
for lab, v, want in (("AZ_FIN", "QWERTYU", "policy_d51e_fin_7_letters"),
                     ("AZ_FIN", "A12B34", "policy_d51e_fin_6_chars"),
                     ("AZ_FIN", "12AB3C", "policy_d51e_fin_6_chars"),
                     ("AZ_FIN", "+994501234567", "policy_d51e_phone_in_fin"),
                     ("AZ_FIN", "1234567890", "policy_d51e_10_digits_in_fin"),
                     ("BUILDINGNUM", "15.03.2019", "policy_d51e_date_in_building"),
                     ("AZ_FIN", "123456", "policy_fin_5_6_chars"),   # 15 Oct follow-up (D-34b)
                     ("AZ_FIN", "ABCDEF", "policy_fin_5_6_chars"),
                     ("AZ_FIN", "12345", "policy_fin_5_6_chars"),
                     ("AZ_FIN", "1234", None),
                     ("AZ_FIN", "1234567", "policy_fin_7_chars"),    # 15 Oct follow-up (D-34a)
                     ("AZ_FIN", "A12B345", "policy_fin_7_chars"),
                     ("AZ_FIN", "A12-B34", None),       # dashed: wrong shape, stays
                     ("AZ_FIN", "AB12-AB", None),
                     ("AZ_FIN", "A12B3456C", None),     # 9 characters
                     ("CARD_SECURITY_CODE", "12-8", "policy_cvv_dashed"),   # D-30b, D-39c
                     ("CARD_SECURITY_CODE", "123-45", "policy_cvv_dashed"),
                     ("CARD_SECURITY_CODE", "12345", None),
                     ("CARD_SECURITY_CODE", "-12", None),
                     ("PAYMENT_CARD_NUMBER", "4169737373737371", None if S._luhn_digit("416973737373737") == "1" else "policy_card_checksum"),
                     ("PAYMENT_CARD_NUMBER", "1169737373737371", None),  # no card prefix
                     ("AZ_FIN", "QWERTYUI", None),      # 8 letters
                     ("AZ_FIN", "ƏÖÜĞIÇŞ", None),       # not Latin capitals A-Z
                     ("AZ_FIN", "+90501234567", None),  # not a +994 phone
                     ("AZ_VOEN", "1234567890", None),   # a FIN field only
                     ("BUILDINGNUM", "31.02.2019", None),  # not a real date
                     ("BUILDINGNUM", "15/03/2019", None),
                     ("BUILDINGNUM", "123456", None),
                     ("DATE", "15.03.2019", None)):
    check(S.d51e_kind(lab, v) == want, f"d51e_kind({lab}, shape of {v!r}) == {want}", S.d51e_kind(lab, v))
check(set(S.D51E_KINDS) == {"policy_d51e_fin_7_letters", "policy_d51e_fin_6_chars", "policy_d51e_phone_in_fin",
                            "policy_d51e_10_digits_in_fin", "policy_d51e_date_in_building", "policy_fin_7_chars",
                            "policy_fin_5_6_chars", "policy_card_checksum", "policy_iban_checksum", "policy_cvv_dashed"},
      "ten kinds, each explained")
body = "416973737373737"
good = body + S._luhn_digit(body)
bad = body + str((int(S._luhn_digit(body)) + 4) % 10)
check(S.checksum_only("PAYMENT_CARD_NUMBER", good) is False and S.checksum_only("PAYMENT_CARD_NUMBER", bad) is True,
      "checksum_only: valid card no, Luhn-only defect yes")
check(S.checksum_only("PAYMENT_CARD_NUMBER", " ".join(bad[i:i + 4] for i in range(0, 16, 4))) is True, "spaced card too")
check(S.d51e_kind("PAYMENT_CARD_NUMBER", bad) == "policy_card_checksum", "card kind")
check(S.checksum_only("IBAN", "AZ12NABZ") is False, "an IBAN fragment is not checksum-only")

text = "FIN QWERTYU; bina 15.03.2019; FIN 1234"
docs = [{"id": "x", "text": text, "decoys": [
    {"start": 4, "end": 11, "resembles": "AZ_FIN", "kind": "benchmark_unique", "policy": False, "listed": False},
    {"start": 18, "end": 28, "resembles": "BUILDINGNUM", "kind": "benchmark_unique", "policy": False, "listed": False},
    {"start": 34, "end": 38, "resembles": "AZ_FIN", "kind": "benchmark_unique", "policy": False, "listed": False}]}]
got = S.apply_d51e(docs)
check(got == {"policy_d51e_date_in_building": 1, "policy_d51e_fin_7_letters": 1}, "apply_d51e counts", got)
check([x["policy"] for x in docs[0]["decoys"]] == [True, True, False], "4 digits stay a scored look-alike")
check(not any(x["listed"] for x in docs[0]["decoys"]), "benchmark items are policy, not the private list")
check(S.apply_d51e(docs) == {}, "already-policy look-alikes are not counted twice")

# --- the benchmark (needs the LFS file; skipped when only the pointer is checked out) --------
if S.BENCH_V3.exists() and not S._is_lfs_pointer(S.BENCH_V3):
    bench = [S._normalise(json.loads(line)) for _, line in zip(range(S.BENCH_V3_SCORED), open(S.BENCH_V3, encoding="utf-8"))]
    got = S.apply_d51e(bench)
    check(got == {"policy_d51e_10_digits_in_fin": 48, "policy_d51e_date_in_building": 63, "policy_d51e_fin_6_chars": 35,
                  "policy_d51e_fin_7_letters": 42, "policy_d51e_phone_in_fin": 43, "policy_card_checksum": 67,
                  "policy_fin_5_6_chars": 76, "policy_fin_7_chars": 39}, "benchmark: 413 policy items", got)
else:
    print("skipped the benchmark counts: data/benchmark_v3 is an LFS pointer here")

# --- B1 judged without the policy items ------------------------------------------------------
def micro(f1):
    return {"exact": {"micro": {"f1": f1}, "per_label": {}}}


def rep(f_all, f_excl=None):
    t = {"all": micro(f_all)}
    if f_excl is not None:
        t["excl_policy"] = micro(f_excl)
    return {"sets": {"benchmark": {"tracks": {"R": t}}}}


rows, k = RC.bench_rules(rep(0.880, 0.900), rep(0.870, 0.875))
b1 = rows[0]
check(b1["status"] == "pass" and "90.0 vs 87.5" in b1["result"] and "with the policy items 88.0 vs 87.0" in b1["result"],
      "B1: judged without the policy items, both shown", b1)
check(k["bench_f1_R"] == 0.880, "D2's benchmark F1 stays the one with all items", k)
rows, _ = RC.bench_rules(rep(0.880, 0.900), rep(0.870))
check(rows[0]["status"] == "fail" and "88.0 vs 87.0" in rows[0]["result"] and "not marked in both" in rows[0]["result"],
      "B1: a baseline without the items -> both judged with them, said so", rows[0])
rows, _ = RC.bench_rules(rep(0.900), rep(0.870))
check(rows[0]["status"] == "pass" and "D-51e" not in rows[0]["result"], "B1: neither marked -> unchanged", rows[0])

# --- the committed checkpoint-1 benchmark baseline carries the D-51e items --------------------
bb = json.loads((HERE.parent / "reports" / "scoreboard" / "baseline_ckpt1_benchmark.json").read_text(encoding="utf-8"))
bset = bb["sets"]["benchmark"]
check(bset["info"].get("policy_items", {}).get("policy_card_checksum") == 67 and
      all("excl_policy" in bset["tracks"][t] for t in ("R", "M")), "baseline_ckpt1_benchmark.json has the policy split (incl. the 15 Oct kinds)")
check(round(bset["tracks"]["R"]["all"]["exact"]["micro"]["f1"], 4) == 0.6871 and
      round(bset["tracks"]["M"]["all"]["exact"]["micro"]["f1"], 4) == 0.7138, "its all-items F1 is unchanged (68.71 / 71.38)")

print(f"{PASS} passed, {FAIL} failed")
for f in FAILURES:
    print("  FAIL", f)
sys.exit(1 if FAIL else 0)
