"""Audit one LLM generation batch (P2-5): run it on every batch, b1 to b4.

    python scripts/piigen/audit_llm_batch.py data/raw/sprint1_llm_b1.jsonl \\
        --rejects data/raw/sprint1_llm_b1.rejects.jsonl --json reports/b1_audit.json
    # the same documents re-labelled by TODAY's code, offline (no API call):
    python scripts/piigen/audit_llm_batch.py data/raw/sprint1_llm_b1.jsonl --replay

Per document it checks:
  1. planned values present but unlabelled -- a `_spec.entities` value whose
     surface form, an inflected form, a softened stem, a capitals/folded form
     or a misspelling still occurs outside every entity span
     (`resolver.find_unlabelled_planned`). Doc id, label, value, context.
  2. labels that disagree with the plan -- a label not planned at all, a
     labelled string that is no form of any planned value, or a label that
     covers only part of a planned value.
  3. decoy integrity -- every `_decoys` span is in range, holds one of the
     planted decoy strings, never overlaps an entity, and is really invalid
     (`validate.value_valid`; the name pools for name-like decoys), unless
     its kind is a `policy_` decoy (D-2) or a contextual one (P2-2: those are
     well-formed by design, the anchor is what makes them not PII).
  4. rate shares -- hard-negative, adversarial, PII-free and edge-case
     documents against the requested rates, and label shares against
     `GeneratorConfig.entity_weights`.
  5. D-9 / D-10 -- a name, city or street span never stops before its suffix;
     a capitalised planned name alone is labelled, a lowercase homograph is not.
  6. the rejects file -- grouped by reason and sub-reason, 3 examples per
     top-10 group, and how many name rejections had the planned value
     labelled in an inflected form (the batch-1 false-rejection bug).

`--replay` first re-runs `pipeline.assemble_document` on every stored
(`_spec`, text) pair with today's code and audits the result instead. Noise is
not applied again (`noise_rate=0`): the stored text already carries it, so a
noised document is re-labelled on its noised text -- a stricter test than
generation, which labels before noise. Everything runs offline.
"""

from __future__ import annotations

import argparse
import collections
import difflib
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.config import ENTITY_TYPES, GeneratorConfig                # noqa: E402
from piigen.locales import LOCALES                                      # noqa: E402
from piigen.negatives import ALL_DECOY_KINDS                            # noqa: E402
from piigen.standalone_dates import standalone_dates                    # noqa: E402
from piigen.resolver import (_INFLECTABLE_LABELS, find_unlabelled_planned,  # noqa: E402
                             match_key, planned_forms)
from piigen.validate import (declared_decoy_spans, span_boundary_problems,  # noqa: E402
                             validate_example, value_valid)

# What batch 1 asked for (data/raw/sprint1_llm_b1.README.md).
DEFAULT_RATES = {"hard_negative": 0.30, "adversarial": 0.20,
                 "pii_free": 0.10, "edge_case": 0.30}
NAME_POOLS = {
    "GIVENNAME": {n.casefold() for loc in LOCALES.values()
                  for n in list(loc.first_names_m) + list(loc.first_names_f)
                  + (loc.foreign_names.given_names() if loc.foreign_names else [])},
    "CITY": {c.casefold() for loc in LOCALES.values() for c in loc.cities},
}


def planned_of(rec: dict) -> list[tuple[str, str]]:
    spec = rec.get("_spec") or {}
    return [(e.get("label"), e.get("value")) for e in spec.get("entities") or []
            if isinstance(e, dict) and e.get("label") and e.get("value")]


def _ctx(text: str, s: int, e: int, width: int = 40) -> str:
    return (text[max(0, s - width):s] + "[[" + text[s:e] + "]]"
            + text[e:e + width]).replace("\n", " ")


def decoy_invalid(kind: str, resembles: str | None, value: str) -> bool | None:
    """True if the decoy is really not a valid value of what it resembles;
    None when the rule does not apply (policy or contextual kinds)."""
    k = ALL_DECOY_KINDS.get(kind)
    if kind.startswith("policy_") or (k is not None and k.contextual):
        return None
    if not resembles:
        return None
    if resembles in NAME_POOLS:
        return value.casefold() not in NAME_POOLS[resembles]
    return not value_valid(resembles, value)[0]


def decoy_problems(rec: dict) -> list[dict]:
    """Every declared decoy of `rec`, with what is wrong with it (or None).

    A decoy is sound when its span is in range, holds one of the strings the
    brief planted, overlaps no entity, and is really invalid as what it
    resembles -- unless it is a policy (D-2) or contextual (P2-2) decoy,
    which are `exempt` from the invalidity rule. scripts/clean_llm_batch.py
    drops a record with any problem here.
    """
    text = rec.get("text") or ""
    ents = rec.get("entities") or []
    planted = planted_strings(rec.get("_spec") or {})
    out = []
    for d in rec.get("_decoys") or []:
        s, e = d.get("start"), d.get("end")
        row = {"kind": d.get("kind"), "start": s, "end": e, "value": None,
               "problem": None, "exempt": False}
        if not (isinstance(s, int) and isinstance(e, int) and 0 <= s < e <= len(text)):
            row["problem"] = "out_of_range"
            out.append(row)
            continue
        value = row["value"] = text[s:e]
        if any(x["start"] < e and s < x["end"] for x in ents):
            row["problem"] = "inside an entity"
        elif planted and not any(value == p or value in p for p in planted):
            row["problem"] = "not a planted decoy string"
        else:
            inv = decoy_invalid(d.get("kind", ""), d.get("resembles"), value)
            row["exempt"] = inv is None
            if inv is False:
                row["problem"] = "a VALID value of what it resembles"
        out.append(row)
    return out


def planted_strings(spec: dict) -> set[str]:
    out = set(spec.get("hard_negatives") or [])
    for d in (spec.get("anchored_decoys") or []) + (spec.get("plain_decoys") or []):
        for key in ("value", "phrase"):
            if d.get(key):
                out.add(d[key])
    return out


# --------------------------------------------------------------------------- #
def audit_records(records: list[dict], rates: dict | None = None,
                  examples: int = 5) -> dict:
    rates = rates or DEFAULT_RATES
    cfg = GeneratorConfig()
    homographs = _homograph_words()
    out: dict = {"documents": len(records)}

    unl, unl_docs, unl_ex = collections.Counter(), set(), []
    # The definition (batch-1 README): a planned value with NO labelled
    # occurrence, although some form of it is in the text
    nowhere, nowhere_docs = collections.Counter(), set()
    unl_kinds = collections.Counter()
    disagree, disagree_ex = collections.Counter(), []
    decoy, decoy_ex = collections.Counter(), []
    d9, d9_ex = collections.Counter(), []
    d10 = collections.Counter()
    planned_n, planned_dropped = collections.Counter(), collections.Counter()
    labels = collections.Counter()
    shares = collections.Counter()

    for rec in records:
        text, ents = rec.get("text") or "", rec.get("entities") or []
        spec = rec.get("_spec") or {}
        planned = planned_of(rec)
        decoys, _ = declared_decoy_spans(rec)
        labels.update(e["label"] for e in ents)

        # 4. rates, as shares of all documents
        # each rate on its own field (P2-6 fix 4): hard negatives are the
        # anchored/plain look-alikes, adversarials the near-misses; a
        # negative-only document carries both
        adv = set(spec.get("adversarials") or [])
        hard = [h for h in spec.get("hard_negatives") or [] if h not in adv]
        shares["hard_negative_spec"] += bool(hard)
        shares["hard_negative_text"] += any(h in text for h in hard)
        shares["adversarial_spec"] += bool(adv)
        shares["adversarial_text"] += rec.get("_adversarials", 0) > 0
        shares["any_decoy_text (README metric)"] += rec.get("_hard_negatives", 0) > 0
        shares["pii_free"] += bool(rec.get("_pii_free") or spec.get("negative_only"))
        shares["edge_case"] += spec.get("edge_case") is not None
        shares["with_decoy_spans"] += bool(rec.get("_decoys"))

        # 1. planned values present but unlabelled
        found = find_unlabelled_planned(text, ents, planned, decoys)
        for f in found:
            unl[f["label"]] += 1
            unl_kinds[f["kind"].split("+")[0] + ("" if f["labelable"] else " (not labellable)")] += 1
            unl_docs.add(rec.get("id"))
            if len(unl_ex) < 200:
                unl_ex.append({"id": rec.get("id"), "label": f["label"], "value": f["value"],
                               "written": f["text"], "kind": f["kind"],
                               "context": _ctx(text, f["start"], f["end"])})
        unl_values = {(f["label"], f["value"]) for f in found}
        for lab, val in planned:
            planned_n[lab] += 1
            forms = planned_forms(text, lab, val)
            labelled = any(any(e["start"] < f.end and f.start < e["end"] and e["label"] == lab
                               for e in ents) for f in forms)
            if not labelled:
                planned_dropped[lab] += 1
                if (lab, val) in unl_values:
                    nowhere[lab] += 1
                    nowhere_docs.add(rec.get("id"))

        # 2. labels that disagree with the plan
        planned_labels = {lab for lab, _v in planned}
        plan_forms = [(lab, f) for lab, val in planned for f in planned_forms(text, lab, val)]
        standalone = set(standalone_dates(text))
        for e in ents:
            why = None
            if e["label"] not in planned_labels:
                why = "label not planned"
            else:
                same = [f for lab, f in plan_forms if lab == e["label"]
                        and f.start < e["end"] and e["start"] < f.end]
                if not same:
                    why = "not a form of any planned value"
                elif not any(f.start >= e["start"] and f.end <= e["end"] for f in same):
                    why = "covers only part of a planned value"
            if why and rec.get("_noise") and any(
                    lab == e["label"] and _close(e["text"], val) for lab, val in planned):
                # noise (typos, OCR, a line-break hyphen) applied AFTER
                # labelling changed the letters inside a correct span
                why = "changed by noise after labelling (ok)"
            if why and e["label"] == "DATE" and (e["start"], e["end"]) in standalone:
                # D-17: every standalone date is DATE, planned or not
                # (relabel_standalone_dates.py adds them to older batches)
                why = "standalone date, D-17 (ok)"
            if why:
                disagree[why] += 1
                if len(disagree_ex) < examples * 4:
                    disagree_ex.append({"id": rec.get("id"), "why": why, "label": e["label"],
                                        "text": e["text"],
                                        "context": _ctx(text, e["start"], e["end"])})

        # 3. decoy integrity
        for f in decoy_problems(rec):
            if f["problem"] == "out_of_range":
                decoy["out_of_range"] += 1
                continue
            decoy["checked"] += 1
            if f["exempt"]:
                decoy["exempt (policy/contextual)"] += 1
            if f["problem"]:
                decoy[f["problem"]] += 1
                if len(decoy_ex) < examples * 3:
                    decoy_ex.append({"id": rec.get("id"), "problem": f["problem"],
                                     "kind": f["kind"], "value": f["value"],
                                     "context": _ctx(text, f["start"], f["end"])})

        # 5. D-9: a name/city/street span never stops before its suffix
        name_ents = [x for x in ents if x["label"] in _INFLECTABLE_LABELS]
        d9["mentions"] += len(name_ents)
        for p in span_boundary_problems(text, name_ents):
            d9["span stops mid-word"] += 1
            if len(d9_ex) < examples:
                d9_ex.append({"id": rec.get("id"), "problem": p})
        for x in name_ents:
            if any(x["text"] != v and match_key(x["text"]).startswith(match_key(v)[:max(3, len(v) - 1)])
                   for lab, v in planned if lab == x["label"]):
                d9["suffixed (label includes the suffix)"] += 1
        # 5. D-10 in LLM prose: a homograph written lowercase is never labelled
        # as a name; a document of 1-5 words that holds a capitalised planned
        # name has it labelled
        for x in ents:
            if (x["label"] == "GIVENNAME" and x["text"][:1].islower()
                    and match_key(x["text"]) in homographs):
                d10["lowercase homograph labelled"] += 1
        if len(re.findall(r"\w+", text)) <= 5:
            d10["documents of 1-5 words"] += 1
            for lab, v in planned:
                if lab == "GIVENNAME" and v[:1].isupper() and v in text and not any(
                        x["label"] == lab and v in x["text"] for x in ents):
                    d10["lone capitalised name unlabelled"] += 1

    n = max(1, len(records))
    mentions = max(1, sum(labels.values()))
    out["unlabelled_planned"] = {
        "values": sum(unl.values()), "documents": len(unl_docs),
        "values_with_no_label_anywhere": sum(nowhere.values()),
        "documents_with_no_label_anywhere": len(nowhere_docs),
        "no_label_anywhere_by_label": dict(nowhere.most_common()),
        "by_label": dict(unl.most_common()), "by_kind": dict(unl_kinds.most_common()),
        "examples": unl_ex}
    out["planned"] = {lab: {"planned": planned_n[lab], "not_labelled_anywhere": planned_dropped[lab],
                            "share": round(planned_dropped[lab] / planned_n[lab], 4)}
                      for lab in sorted(planned_n)}
    out["label_disagreement"] = {"count": sum(disagree.values()), "by_reason": dict(disagree),
                                 "examples": disagree_ex}
    out["decoys"] = {"counts": dict(decoy), "examples": decoy_ex}
    out["rates"] = {
        "requested": rates,
        "measured": {k: round(v / n, 4) for k, v in shares.items()}}
    out["label_shares"] = {lab: {"mentions": labels[lab],
                                 "share": round(labels[lab] / mentions, 4),
                                 "target": cfg.entity_weights.get(lab, 0.0),
                                 "ratio": round((labels[lab] / mentions) / cfg.entity_weights[lab], 2)
                                 if cfg.entity_weights.get(lab) else None}
                           for lab in ENTITY_TYPES}
    out["d9"] = {"counts": dict(d9), "examples": d9_ex}
    out["d10"] = dict(d10)
    out["validate_example_failures"] = dict(collections.Counter(
        p[0].split("(")[0].strip()[:60] for p in (validate_example(r) for r in records) if p))
    return out


# OCR look-alikes the noise injector swaps in (`114` -> `l14`, batch 3)
_OCR_DIGITS = str.maketrans("lioszgb", "1105298")


def _close(written: str, planned: str) -> bool:
    a = re.sub(r"[\W_]", "", match_key(written))
    b = re.sub(r"[\W_]", "", match_key(planned))
    if b.isdigit():
        a = a.translate(_OCR_DIGITS)
    return bool(a and b) and (a.startswith(b[:-2]) or
                              difflib.SequenceMatcher(None, a[:len(b) + 2], b).ratio() >= 0.75)


def _homograph_words() -> set[str]:
    try:
        from piigen.targeted import homographs_az as H
    except ImportError:
        from piigen.targeted import homographs_az_stub as H
    return {match_key(w) for w in H.LONE_WORDS} | {match_key(e["az"]) for e in H.HOMOGRAPHS.values()}


# --------------------------------------------------------------------------- #
def unplanned_pii(rec: dict) -> list[dict]:
    """PII the model INVENTED in this record (informational in the audit; a
    drop in clean_llm_batch.py --drop-unplanned-pii, D-15c): the shared
    definition, `piigen.llm.quality.find_invented_pii`."""
    from piigen.llm.quality import find_invented_pii
    decoys = [(d["start"], d["end"]) for d in rec.get("_decoys") or []
              if isinstance(d.get("start"), int) and isinstance(d.get("end"), int)]
    return find_invented_pii(rec.get("text") or "", rec.get("entities") or [], decoys,
                             rec.get("_doc_type"))


def sweep_unplanned(records: list[dict], examples: int = 5) -> dict:
    by_label, docs, ex = collections.Counter(), set(), []
    pii_free_docs = set()
    for rec in records:
        found = unplanned_pii(rec)
        for f in found:
            by_label[f["label"]] += 1
            if len(ex) < examples * 4:
                ex.append({"id": rec.get("id"), **{k: f[k] for k in ("label", "text")},
                           "context": _ctx(rec["text"], f["start"], f["end"])})
        if found:
            docs.add(rec.get("id"))
            if rec.get("_pii_free"):
                pii_free_docs.add(rec.get("id"))
    return {"documents": len(docs), "share": round(len(docs) / max(1, len(records)), 4),
            "pii_free_documents": len(pii_free_docs), "by_label": dict(by_label.most_common()),
            "examples": ex}


def sweep_dates(records: list[dict], examples: int = 5) -> dict:
    """D-17: standalone dates no label covers (timestamps excluded)."""
    from piigen.standalone_dates import find_unlabelled_dates
    docs, spans, ex, why = 0, 0, [], collections.Counter()
    for rec in records:
        decoys, _ = declared_decoy_spans(rec)
        found = find_unlabelled_dates(rec.get("text") or "", rec.get("entities") or [], decoys)
        docs += bool(found)
        spans += len(found)
        why.update(f["why_not"] or "labellable" for f in found)
        for f in found:
            if len(ex) < examples:
                ex.append({"id": rec.get("id"), "text": f["text"],
                           "context": _ctx(rec["text"], f["start"], f["end"])})
    return {"documents": docs, "share": round(docs / max(1, len(records)), 4), "dates": spans,
            "by_reason": dict(why.most_common()), "examples": ex}


def _reason_group(reason: str) -> tuple[str, str]:
    head = reason.split(":")[0].strip()
    rest = reason[len(head) + 1:].strip()
    sub = re.sub(r"\d+", "N", re.sub(r"'[^']*'|\"[^\"]*\"", "'…'", rest))[:70]
    return head, sub


def audit_rejects(rejects: list[dict], examples: int = 3) -> dict:
    groups = collections.Counter()
    subs = collections.Counter()
    ex = collections.defaultdict(list)
    inflected_ok = collections.Counter()
    for r in rejects:
        reason = r.get("reason", "")
        head, sub = _reason_group(reason)
        groups[head] += 1
        subs[(head, sub)] += 1
        if len(ex[(head, sub)]) < examples:
            ex[(head, sub)].append((r.get("text") or "")[:240].replace("\n", " "))
        m = re.match(r"quality: (CITY|STREET|SURNAME|GIVENNAME)$", reason)
        if m:
            lab = m.group(1)
            inflected_ok["name rejects"] += 1
            if any(e.get("label") == lab and re.search(
                    r"(da|də|dan|dən|nın|nin|nun|nün|ın|in|un|ün|ya|yə|a|ə|nı|ni|ı|i|u|ü|"
                    r"lar|lər|ları|ləri|dır|dir|dakı|dəki|sində|sinə|sindən|sinin|sini)$",
                    e.get("text", "")) for e in r.get("entities") or []):
                inflected_ok["planned value labelled in an inflected form"] += 1
    total = max(1, len(rejects))
    top = [k for k, _v in subs.most_common(10)]
    return {"rejects": len(rejects),
            "by_reason": {k: {"count": v, "share": round(v / total, 4)} for k, v in groups.most_common()},
            "top_subreasons": [{"reason": h, "sub": s, "count": subs[(h, s)],
                                "examples": ex[(h, s)]} for h, s in top],
            "name_rejects": dict(inflected_ok)}


# --------------------------------------------------------------------------- #
def spec_from_record(rec: dict):
    from piigen.llm import edge_cases as EC
    from piigen.llm.specs import DocumentSpec, PlannedEntity
    d = dict(rec["_spec"])
    d["entities"] = [PlannedEntity(**e) for e in d.get("entities") or []]
    ec = d.get("edge_case")
    if ec:
        fields = EC.EdgeCase.__dataclass_fields__
        d["edge_case"] = EC.EdgeCase(**{k: v for k, v in ec.items() if k in fields})
    fields = DocumentSpec.__dataclass_fields__
    return DocumentSpec(**{k: v for k, v in d.items() if k in fields})


def replay(records: list[dict]) -> tuple[list[dict], list[dict]]:
    """Re-label every stored (spec, text) pair with today's assemble_document.
    Returns (accepted records, [{"id", "reason", "noised"}] for rejections)."""
    from piigen.llm.pipeline import assemble_document
    cfg = GeneratorConfig()
    accepted, rejected = [], []
    for rec in records:
        outcome = assemble_document(spec_from_record(rec), rec["text"], cfg, 0.0)
        if outcome.ok:
            new = outcome.record
            new["id"] = rec["id"]
            new["_noise"] = rec.get("_noise", [])
            new["_gen_version_replayed_from"] = rec.get("_gen_version")
            accepted.append(new)
        else:
            rejected.append({"id": rec.get("id"), "reason": outcome.reason,
                             "noised": bool(rec.get("_noise"))})
    return accepted, rejected


# --------------------------------------------------------------------------- #
def format_report(res: dict, rej: dict | None, examples: int) -> str:
    w = []
    p = w.append
    u = res["unlabelled_planned"]
    p(f"documents: {res['documents']:,}")
    p("")
    p(f"1. PLANNED VALUES PRESENT BUT UNLABELLED: {u['values']} occurrence(s) in {u['documents']} document(s)")
    p(f"   of which a value with no labelled occurrence at all (count): "
      f"{u['values_with_no_label_anywhere']} in {u['documents_with_no_label_anywhere']} document(s) "
      f"{u['no_label_anywhere_by_label']}")
    p(f"   by label: {u['by_label']}")
    p(f"   by form : {u['by_kind']}")
    for e in u["examples"][:examples]:
        p(f"   {e['id']}  {e['label']}  {e['value']!r} written {e['written']!r} ({e['kind']})")
        p(f"      ...{e['context']}...")
    p("   planned values with no labelled occurrence, by label (share of that label's plans):")
    p("   " + ", ".join(f"{lab} {v['not_labelled_anywhere']}/{v['planned']} ({v['share']:.1%})"
                         for lab, v in sorted(res["planned"].items(), key=lambda kv: -kv[1]["share"])[:8]))
    p("")
    d = res["label_disagreement"]
    p(f"2. LABELS THAT DISAGREE WITH THE PLAN: {d['count']}  {d['by_reason']}")
    for e in d["examples"][:examples]:
        p(f"   {e['id']}  {e['why']}: {e['label']} {e['text']!r}  ...{e['context']}...")
    p("")
    dc = res["decoys"]["counts"]
    bad = {k: v for k, v in dc.items() if k not in ("checked", "exempt (policy/contextual)")}
    p(f"3. DECOY INTEGRITY: {dc.get('checked', 0)} decoy span(s) checked, "
      f"{dc.get('exempt (policy/contextual)', 0)} policy/contextual; problems: {bad or 'none'}")
    for e in res["decoys"]["examples"][:examples]:
        p(f"   {e['id']}  {e['problem']}: {e['kind']} {e['value']!r}  ...{e['context']}...")
    p("")
    r = res["rates"]
    p("4. RATES (share of all documents)")
    for k, v in r["requested"].items():
        got = r["measured"].get(k if k in ("pii_free", "edge_case") else f"{k}_text", 0)
        spec = r["measured"].get(f"{k}_spec")
        p(f"   {k:<14} requested {v:.1%}   in the text {got:.1%}"
          + (f"   in the briefs {spec:.1%}" if spec is not None else ""))
    p(f"   any decoy in the text (_hard_negatives > 0, the batch-1 README's measure): "
      f"{r['measured'].get('any_decoy_text (README metric)', 0):.1%}")
    worst = sorted(((lab, v) for lab, v in res["label_shares"].items() if v["ratio"]),
                   key=lambda kv: -abs(kv[1]["ratio"] - 1))[:6]
    p("   label share / target, furthest off: "
      + ", ".join(f"{lab} {v['ratio']:.2f}" for lab, v in worst))
    p("")
    p(f"5. D-9: {res['d9']['counts']}")
    for e in res["d9"]["examples"][:examples]:
        p(f"   {e['id']}  {e['problem']}")
    p(f"   D-10: {res['d10'] or 'no lone-name documents'}")
    p(f"   validate_example failures: {res['validate_example_failures'] or 'none'}")
    up = res.get("unplanned_pii")
    if up:
        p("")
        p(f"7. INDEPENDENT SWEEP, PII THE MODEL INVENTED (informational): {up['documents']} document(s) "
          f"({up['share']:.1%}), {up['pii_free_documents']} of them declared PII-free; {up['by_label']}")
        for e in up["examples"][:examples]:
            p(f"   {e['id']}  {e['label']} {e['text']!r}  ...{e['context']}...")
    sd = res.get("standalone_dates")
    if sd:
        p("")
        p(f"8. STANDALONE DATES LEFT UNLABELLED (D-17; timestamps excluded): {sd['dates']} in "
          f"{sd['documents']} document(s) ({sd['share']:.1%}); {sd['by_reason']}. "
          f"scripts/relabel_standalone_dates.py labels them")
        for e in sd["examples"][:examples]:
            p(f"   {e['id']}  {e['text']!r}  ...{e['context']}...")
    if rej:
        p("")
        p(f"6. REJECTS: {rej['rejects']:,}")
        for k, v in rej["by_reason"].items():
            p(f"   {v['count']:>6}  {v['share']:6.1%}  {k}")
        p(f"   name rejects: {rej['name_rejects']}")
        p("   top-10 sub-reasons:")
        for g in rej["top_subreasons"]:
            p(f"   {g['count']:>6}  {g['reason']} | {g['sub']}")
            for x in g["examples"]:
                p(f"            e.g. {x[:160]}")
    return "\n".join(w)


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch", type=Path)
    ap.add_argument("--rejects", type=Path, default=None)
    ap.add_argument("--replay", action="store_true",
                    help="re-label the stored documents with today's code first")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--write-replay", type=Path, default=None,
                    help="with --replay: write the re-labelled accepted records here")
    ap.add_argument("--examples", type=int, default=5)
    ap.add_argument("--rates", default=None,
                    help="requested rates, e.g. hard_negative=0.3,adversarial=0.2,pii_free=0.1,edge_case=0.3")
    ap.add_argument("--read", type=int, default=0,
                    help="also print N random accepted documents for the read-by-hand pass")
    args = ap.parse_args()

    records = load(args.batch)
    rates = dict(DEFAULT_RATES)
    if args.rates:
        rates.update({k: float(v) for k, v in (x.split("=") for x in args.rates.split(","))})
    result: dict = {"batch": str(args.batch)}
    if args.replay:
        accepted, rejected = replay(records)
        result["replay"] = {
            "replayed": len(records), "accepted": len(accepted), "rejected": len(rejected),
            "rejected_by_reason": dict(collections.Counter(
                _reason_group(r["reason"])[0] + ": " + _reason_group(r["reason"])[1][:50]
                for r in rejected).most_common()),
            "rejected_noised": sum(r["noised"] for r in rejected),
            "rejected_ids": [r["id"] for r in rejected]}
        print(f"REPLAY with today's code: {len(records):,} stored -> {len(accepted):,} accepted, "
              f"{len(rejected):,} rejected ({result['replay']['rejected_noised']} of them noised)")
        for k, v in list(result["replay"]["rejected_by_reason"].items())[:15]:
            print(f"   {v:>5}  {k}")
        print()
        records = accepted
        if args.write_replay:
            args.write_replay.parent.mkdir(parents=True, exist_ok=True)
            with args.write_replay.open("w", encoding="utf-8") as fh:
                for rec in accepted:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"replayed records -> {args.write_replay}")
    result.update(audit_records(records, rates, args.examples))
    result["unplanned_pii"] = sweep_unplanned(records, args.examples)
    result["standalone_dates"] = sweep_dates(records, args.examples)
    rej = audit_rejects(load(args.rejects)) if args.rejects else None
    if rej:
        result["rejects"] = rej
    print(format_report(result, rej, args.examples))
    if args.read:
        print()
        print(f"READ BY HAND: {args.read} random documents (seed 5)")
        for rec in random.Random(5).sample(records, min(args.read, len(records))):
            print("-" * 70)
            print(rec["id"], rec.get("_doc_type"), rec.get("_bucket"), "noise:", rec.get("_noise"))
            print(rec["text"][:1200])
            print("  entities:", [(e["label"], e["text"]) for e in rec["entities"]])
            print("  decoys  :", [rec["text"][d["start"]:d["end"]] for d in rec.get("_decoys") or []])
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\njson -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
