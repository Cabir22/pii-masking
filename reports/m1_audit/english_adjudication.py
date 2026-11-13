"""m1 audit: a documented current-policy reassessment of golden_en (the original gold is not changed).

Every m1 prediction that is not an exact gold match, and every gold value m1 misses, gets a verdict
by an explicit rule (reviewed by the team, 24 Oct, from english_review.jsonl):
  gold_missing    real PII under current policy that the gold leaves unlabelled (D-17 dates, names, …)
  model_error     the prediction is wrong under current policy (split dates, weekday inside DATE, …)
  ambiguous       policy not settled; reported as a range
  gold_error      the gold span itself is wrong (a value placed on the wrong occurrence)
Writes english_adjudication.jsonl and english_adjudication.md: the original score, and the current-policy
score as a range (ambiguous counted against m1, then for m1).

  python reports/m1_audit/english_adjudication.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent

AMBIGUOUS = {("CITY", "Hamburg"): "a city in a company's address (organisation, D-2) — not settled",
             ("EMAIL", "info@baküenerji.az"): "organisation mailbox, no person — not settled",
             ("EMAIL", "destek@servis.az"): "organisation mailbox, no person — not settled",
             ("IPV4_ADDRESS", "100.22.14.01"): "leading-zero octet in an obfuscated log — not settled",
             ("GIVENNAME", "Gulli"): "gold SURNAME vs predicted GIVENNAME: either reading is possible",
             ("CITY", "Sahil"): "a settlement name inside a police department's name (D-2/D-66f-like) — not settled"}
MODEL_ERRORS = {("ACCESS_TOKEN", "*"): "an asterisk from a masked card number",
                ("STREET", "Link to"): "street split; 'Link to' is not part of it",
                ("STREET", "beajh St."): "street split from its prefix",
                ("DATE", "Thursday, 16 May 1963"): "weekday inside DATE (D-54d: outside)",
                ("DATE", "Wednesday, 14 October 1981"): "weekday inside DATE (D-54d: outside)"}


def verdict(r: dict) -> tuple[str, str]:
    lab, v, cat = r["label"], r["value"], r["category"]
    if (lab, v) in AMBIGUOUS:
        return "ambiguous", AMBIGUOUS[(lab, v)]
    if (lab, v) in MODEL_ERRORS:
        return "model_error", MODEL_ERRORS[(lab, v)]
    if cat.startswith("standalone date"):
        return "gold_missing", "standalone date (D-17: every standalone date is DATE)"
    if cat == "DATE on other text":
        return "model_error", "a piece of a date or a bare year (partial or wrong DATE)"
    if cat == "MISSED gold":
        if lab == "AGE" and v == "54":
            return "gold_error", "gold AGE placed on '54' inside a time stamp (10:54), not on 'Age: 54'"
        return "model_error", "gold value not masked at all"
    if cat.endswith("with no gold overlap") and lab in ("GIVENNAME", "SURNAME", "CITY", "STREET", "AGE", "TIME",
                                                         "BUILDINGNUM", "ACCESS_TOKEN"):
        return "gold_missing", "a real value of a person (names incl. chat speakers D-72h, address parts, ages, times, tokens)"
    return "ambiguous", f"unreviewed category: {cat}"


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    return p, r, (2 * p * r / (p + r) if p + r else 0)


def main() -> int:
    rows = [json.loads(l) for l in (HERE / "english_review.jsonl").open(encoding="utf-8") if json.loads(l)["model"] == "m1"]
    for r in rows:
        r["verdict"], r["reason"] = verdict(r)
    (HERE / "english_adjudication.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                                     encoding="utf-8")
    tp, fp, fn = 1016, 329, 11              # the original exact scores (report, reproduced)
    preds_extra = [r for r in rows if r["category"] != "MISSED gold"]
    missed = [r for r in rows if r["category"] == "MISSED gold"]
    c = Counter((r["verdict"]) for r in preds_extra)
    gm = c["gold_missing"]; amb = c["ambiguous"]; me = c["model_error"]
    gold_err = sum(r["verdict"] == "gold_error" for r in missed)
    # boundary predictions (same label, other span): one exact FP + one FN of the same gold value
    lo = prf(tp + gm, fp - gm, fn - gold_err)                 # ambiguous counted against m1
    hi = prf(tp + gm + amb, fp - gm - amb, fn - gold_err)      # ambiguous counted for m1
    L = ["# English (golden_en): original score and a current-policy reassessment", "",
         "The original gold is unchanged; this is a separate, documented view. Track M, exact spans.", "",
         "| View | TP | FP | FN | P | R | F1 |", "|---|---|---|---|---|---|---|",
         f"| original gold (A7's number) | {tp} | {fp} | {fn} | {100*tp/(tp+fp):.1f} | {100*tp/(tp+fn):.1f} | **{100*prf(tp,fp,fn)[2]:.1f}** |",
         f"| current policy, ambiguous against m1 | {tp+gm} | {fp-gm} | {fn-gold_err} | {100*lo[0]:.1f} | {100*lo[1]:.1f} | **{100*lo[2]:.1f}** |",
         f"| current policy, ambiguous for m1 | {tp+gm+amb} | {fp-gm-amb} | {fn-gold_err} | {100*hi[0]:.1f} | {100*hi[1]:.1f} | **{100*hi[2]:.1f}** |", "",
         f"Of m1's {len(preds_extra)} non-exact predictions: **{gm} gold missing**, {me} model errors, {amb} ambiguous. "
         f"Of its {len(missed)} misses: {gold_err} gold error(s), the rest model misses.", "",
         "Checkpoint 1 (98.6 on the original gold) was trained on the same old corpus as this gold, with the same "
         "sparse labelling; under the current policy it would also lose the values it leaves unlabelled. "
         "**Not re-scored here:** checkpoint 1's own current-policy score would need the same review of its predictions.", "",
         "| Verdict | Label | Spans | Reason |", "|---|---|---|---|"]
    for (v, lab, why), n in Counter((r["verdict"], r["label"], r["reason"]) for r in rows).most_common():
        L.append(f"| {v} | {lab} | {n} | {why} |")
    (HERE / "english_adjudication.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
