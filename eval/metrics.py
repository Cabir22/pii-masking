"""Pure scoring functions for eval/scoreboard.py -- no model, no I/O.

Every function takes plain span dicts ({"label", "start", "end"}, plus an
optional "score" on predictions) so it can be unit-tested on hand-made
examples (eval/test_metrics.py) without downloading anything.

A "doc" here is {"id", "text", "gold": [span], "pred": [span],
"decoys": [{"start", "end", "resembles", "kind", "policy"}], "meta": {...}}.
The scoreboard builds these; the metrics never look at the text except to
count characters.

Definitions (P3-1):
  exact      label + start + end all equal (the benchmark's method)
  overlap    any character overlap with the same label
  leakage    gold PII characters covered by no predicted span (any label)
             / all gold PII characters
  boundary   a prediction of the same label that overlaps a gold span but
             is not equal to it; "narrower" = the prediction lies inside
             gold, so part of the value stays visible
  trigger    a prediction overlapping a planted decoy; counted once with
             the decoy's `resembles` label and once with any label
"""
from __future__ import annotations

from collections import Counter, defaultdict


def _key(s: dict) -> tuple:
    return (s["label"], s["start"], s["end"])


def _overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": p, "recall": r, "f1": f}


def _summarise(per_label_counts: dict[str, Counter]) -> dict:
    """{label: Counter(tp, fp, fn)} -> micro, macro and per-label P/R/F1.

    Macro averages F1 over labels that occur in gold or predictions, the
    same way the report's 67.6% is the mean of its 27 per-label F1s.
    """
    per_label = {lab: prf(c["tp"], c["fp"], c["fn"])
                 for lab, c in sorted(per_label_counts.items())}
    tot = Counter()
    for c in per_label_counts.values():
        tot.update(c)
    micro = prf(tot["tp"], tot["fp"], tot["fn"])
    labels = [l for l, v in per_label.items() if v["tp"] + v["fp"] + v["fn"]]
    macro_f1 = sum(per_label[l]["f1"] for l in labels) / len(labels) if labels else 0.0
    return {"micro": micro, "macro_f1": macro_f1, "per_label": per_label}


def exact_scores(docs: list[dict]) -> dict:
    """Exact-match P/R/F1: label + start + end. Multisets, so a duplicated
    prediction of one gold span is one TP and one FP."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        gold = Counter(_key(s) for s in d["gold"])
        pred = Counter(_key(s) for s in d["pred"])
        for k in gold | pred:
            tp = min(gold[k], pred[k])
            counts[k[0]]["tp"] += tp
            counts[k[0]]["fn"] += gold[k] - tp
            counts[k[0]]["fp"] += pred[k] - tp
    return _summarise(counts)


def overlap_scores(docs: list[dict]) -> dict:
    """Overlap-based P/R/F1. A prediction is correct if it overlaps any gold
    span of the same label; a gold span is found if any prediction of the
    same label overlaps it. Precision and recall are counted on their own
    sides (one long prediction covering two gold values is 1 correct
    prediction and 2 found gold), so tp differs between P and R; the
    reported tp is the gold-side one."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        for g in d["gold"]:
            hit = any(p["label"] == g["label"] and _overlaps(p, g) for p in d["pred"])
            counts[g["label"]]["gold_found" if hit else "fn"] += 1
        for p in d["pred"]:
            hit = any(p["label"] == g["label"] and _overlaps(p, g) for g in d["gold"])
            counts[p["label"]]["pred_ok" if hit else "fp"] += 1
    per_label = {}
    tot = Counter()
    for lab, c in sorted(counts.items()):
        tot.update(c)
        per_label[lab] = _overlap_prf(c)
    labels = [l for l, v in per_label.items() if v["n_gold"] + v["n_pred"]]
    macro = sum(per_label[l]["f1"] for l in labels) / len(labels) if labels else 0.0
    return {"micro": _overlap_prf(tot), "macro_f1": macro, "per_label": per_label}


def _overlap_prf(c: Counter) -> dict:
    n_pred = c["pred_ok"] + c["fp"]
    n_gold = c["gold_found"] + c["fn"]
    p = c["pred_ok"] / n_pred if n_pred else 0.0
    r = c["gold_found"] / n_gold if n_gold else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"tp": c["gold_found"], "fp": c["fp"], "fn": c["fn"],
            "n_pred": n_pred, "n_gold": n_gold, "precision": p, "recall": r, "f1": f}


def char_leakage(docs: list[dict]) -> dict:
    """Gold PII characters that no predicted span covers, whatever its label:
    a character masked under the wrong label is still not leaked."""
    total = leaked = 0
    per_label: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        covered = set()
        for p in d["pred"]:
            covered.update(range(p["start"], p["end"]))
        for g in d["gold"]:
            n = g["end"] - g["start"]
            miss = sum(1 for i in range(g["start"], g["end"]) if i not in covered)
            total += n
            leaked += miss
            per_label[g["label"]]["chars"] += n
            per_label[g["label"]]["leaked"] += miss
    return {"gold_chars": total, "leaked_chars": leaked,
            "rate": leaked / total if total else 0.0,
            "per_label": {l: {"gold_chars": c["chars"], "leaked_chars": c["leaked"],
                              "rate": c["leaked"] / c["chars"] if c["chars"] else 0.0}
                          for l, c in sorted(per_label.items())}}


def boundary_errors(docs: list[dict]) -> dict:
    """Same-label predictions that overlap a gold span without matching it
    exactly, classified against that gold span:
      narrower  inside gold (part of the value leaks)
      wider     contains gold (over-masks the surroundings)
      shifted   crosses one gold edge
    A prediction that exactly matches some gold span is never a boundary
    error, even if it also overlaps another one."""
    kinds = Counter()
    per_label: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        gold_keys = {_key(g) for g in d["gold"]}
        for p in d["pred"]:
            if _key(p) in gold_keys:
                continue
            for g in d["gold"]:
                if g["label"] != p["label"] or not _overlaps(p, g):
                    continue
                if p["start"] >= g["start"] and p["end"] <= g["end"]:
                    kind = "narrower"
                elif p["start"] <= g["start"] and p["end"] >= g["end"]:
                    kind = "wider"
                else:
                    kind = "shifted"
                kinds[kind] += 1
                per_label[p["label"]][kind] += 1
                break
    n = sum(kinds.values())
    return {"n": n, **{k: kinds[k] for k in ("narrower", "wider", "shifted")},
            "narrower_share": kinds["narrower"] / n if n else 0.0,
            "per_label": {l: dict(c) for l, c in sorted(per_label.items())}}


def decoy_triggers(docs: list[dict], include_policy: bool = True) -> dict:
    """Hard-negative trigger rate: planted decoys hit by a prediction.
    Reported twice: `same_label` (the prediction carries the label the decoy
    resembles, the benchmark's "hard_negative_trigger") and `any_label`."""
    per: dict[str, Counter] = defaultdict(Counter)
    per_kind: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        for dec in d.get("decoys", []):
            if dec.get("policy") and not include_policy:
                continue
            lab = dec.get("resembles") or "UNKNOWN"
            hits = [p for p in d["pred"] if _overlaps(p, dec)]
            for c in (per[lab], per_kind[dec.get("kind") or "UNKNOWN"]):
                c["decoys"] += 1
                c["any_label"] += bool(hits)
                c["same_label"] += any(p["label"] == lab for p in hits)
    tot = Counter()
    for c in per.values():
        tot.update(c)

    def rates(c: Counter) -> dict:
        n = c["decoys"]
        return {"decoys": n, "triggered_same_label": c["same_label"],
                "triggered_any_label": c["any_label"],
                "rate_same_label": c["same_label"] / n if n else 0.0,
                "rate_any_label": c["any_label"] / n if n else 0.0}

    return {"overall": rates(tot), "per_label": {l: rates(c) for l, c in sorted(per.items())},
            "per_kind": {k: rates(c) for k, c in sorted(per_kind.items())}}


def _control_hits(d: dict) -> tuple[bool | None, list[tuple[dict, bool]]]:
    """(record masked?, [(control span, masked?)]) for one doc.

    A record marked `control` is an ordinary-word use as a whole
    (`Dəniz sakit idi.`): it is masked if any prediction falls outside its
    gold spans (normally it has none). A `controls` span marks one
    ordinary-word use inside a text (`dənizə baxdım`): masked if any
    prediction of any label overlaps it."""
    rec = None
    if d.get("control"):
        rec = any(not any(_overlaps(p, g) for g in d["gold"]) for p in d["pred"])
    spans = [(c, any(_overlaps(p, c) for p in d["pred"])) for c in d.get("controls", [])]
    return rec, spans


def control_fp(docs: list[dict]) -> dict:
    """False-positive rate on marked non-PII controls (RC9 homographs:
    names that are also ordinary words, used as the word). Records and
    spans are reported apart, overall and per `resembles` label."""
    tot = Counter()
    per: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        rec, spans = _control_hits(d)
        if rec is not None:
            tot["records"] += 1
            tot["records_masked"] += rec
            lab = d.get("meta", {}).get("resembles") or "UNKNOWN"
            per[lab]["records"] += 1
            per[lab]["records_masked"] += rec
        for c, hit in spans:
            tot["spans"] += 1
            tot["spans_masked"] += hit
            lab = c.get("resembles") or "UNKNOWN"
            per[lab]["spans"] += 1
            per[lab]["spans_masked"] += hit

    def block(c: Counter) -> dict:
        return {"records": c["records"], "records_masked": c["records_masked"],
                "record_fp_rate": c["records_masked"] / c["records"] if c["records"] else None,
                "spans": c["spans"], "spans_masked": c["spans_masked"],
                "span_fp_rate": c["spans_masked"] / c["spans"] if c["spans"] else None}

    return {**block(tot), "per_label": {l: block(c) for l, c in sorted(per.items())}}


def document_rates(docs: list[dict]) -> dict:
    """PII-free document FP rate (documents with no gold that got at least
    one prediction) and perfect-document rate (prediction set == gold set,
    exactly)."""
    pii_free = [d for d in docs if not d["gold"]]
    fp_docs = sum(1 for d in pii_free if d["pred"])
    perfect = sum(1 for d in docs
                  if Counter(map(_key, d["gold"])) == Counter(map(_key, d["pred"])))
    # PII-free documents holding policy items, keyed by their policy kinds ("a|b"), so a target
    # can leave them out of the PII-free count (D-41c: a dashed CVV is a real value by D-39c)
    by_kinds: dict = {}
    for d in pii_free:
        kinds = sorted({x.get("kind", "") for x in d.get("decoys", []) if x.get("policy")})
        if kinds:
            b = by_kinds.setdefault("|".join(kinds), {"documents": 0, "with_fp": 0})
            b["documents"] += 1
            b["with_fp"] += bool(d["pred"])
    return {"documents": len(docs),
            "pii_free_documents": len(pii_free), "pii_free_with_fp": fp_docs,
            "pii_free_fp_rate": fp_docs / len(pii_free) if pii_free else None,
            "pii_free_policy_kinds": by_kinds,
            "perfect_documents": perfect,
            "perfect_rate": perfect / len(docs) if docs else 0.0}


def calibration(docs: list[dict], n_bins: int = 10) -> dict:
    """Score bins vs exact precision. Report only: never used to pick a
    threshold (rule A2.2 -- precision is bought with decoys, not cut-offs).
    Predictions without a score are counted separately."""
    bins = [Counter() for _ in range(n_bins)]
    unscored = 0
    for d in docs:
        gold = Counter(map(_key, d["gold"]))
        for p in d["pred"]:
            if p.get("score") is None:
                unscored += 1
                continue
            b = min(int(p["score"] * n_bins), n_bins - 1)
            ok = gold[_key(p)] > 0
            if ok:
                gold[_key(p)] -= 1
            bins[b]["n"] += 1
            bins[b]["correct"] += ok
    return {"unscored_predictions": unscored,
            "bins": [{"lo": i / n_bins, "hi": (i + 1) / n_bins, "n": c["n"],
                      "precision": c["correct"] / c["n"] if c["n"] else None}
                     for i, c in enumerate(bins)]}


def drop_policy_predictions(docs: list[dict]) -> list[dict]:
    """The D-2 policy bucket: the same documents with every prediction that
    overlaps a policy decoy removed, so a disputed value (`1234` as CVV,
    `4242...`) neither counts as an FP nor as a trigger."""
    out = []
    for d in docs:
        pol = [x for x in d.get("decoys", []) if x.get("policy")]
        if not pol:
            out.append(d)
            continue
        out.append({**d, "pred": [p for p in d["pred"]
                                  if not any(_overlaps(p, x) for x in pol)]})
    return out


def drop_listed(docs: list[dict]) -> list[dict]:
    """D-42: the same documents without the look-alikes from the private policy list (`listed`)
    and without the predictions that overlap them: A4 and A5 "without them"."""
    out = []
    for d in docs:
        lst = [x for x in d.get("decoys", []) if x.get("listed")]
        if not lst:
            out.append(d)
            continue
        out.append({**d, "decoys": [x for x in d["decoys"] if not x.get("listed")],
                    "pred": [p for p in d["pred"] if not any(_overlaps(p, x) for x in lst)]})
    return out


def density_bucket(n_gold: int) -> str:
    if n_gold == 0:
        return "0"
    if n_gold == 1:
        return "1"
    if n_gold <= 3:
        return "2-3"
    if n_gold <= 6:
        return "4-6"
    return "7+"


MAX_SLICE_VALUES = 50  # a field with more distinct values is an id, not a slice


GOLD_OUTCOMES = ("exact", "split", "covered_inexact", "wrong_label", "missed")


def gold_outcome(g: dict, preds: list[dict]) -> str:
    """What happened to one gold span, first match wins:
      exact            a prediction with the same label and span
      split            same-label predictions cover it only partly or in
                       fragments (`dan` for `Fidan`, a stem-only `Bakı` for
                       `Bakıda`, a PEM key in two halves): part of the value
                       leaks or the value is cut up
      covered_inexact  one same-label prediction covers all of it but runs
                       past its edges (wider): nothing leaks
      wrong_label      only predictions of other labels touch it
      missed           nothing touches it: a full miss"""
    if any(_key(p) == _key(g) for p in preds):
        return "exact"
    same = [p for p in preds if p["label"] == g["label"] and _overlaps(p, g)]
    if same:
        covered = set()
        for p in same:
            covered.update(range(max(p["start"], g["start"]), min(p["end"], g["end"])))
        if len(same) > 1 or len(covered) < g["end"] - g["start"]:
            return "split"
        return "covered_inexact"
    if any(_overlaps(p, g) for p in preds):
        return "wrong_label"
    return "missed"


def gold_recall(pairs: list[tuple[dict, list[dict]]]) -> dict:
    """Exact and overlap recall over (gold span, that doc's predictions)
    pairs, overall and per label, plus the count of every gold_outcome.
    `partial` = found by overlap but not exactly (split + covered_inexact).
    High overlap with low exact recall is a boundary problem, not a
    detection one; `split` is counted apart from `missed` because it leaks
    part of the value rather than all of it."""
    per: dict[str, Counter] = defaultdict(Counter)
    for g, preds in pairs:
        out = gold_outcome(g, preds)
        c = per[g["label"]]
        c["n"] += 1
        c[out] += 1
        c["overlap"] += out in ("exact", "split", "covered_inexact")

    def block(c: Counter) -> dict:
        n = c["n"]
        return {"gold": n, "exact_hits": c["exact"], "overlap_hits": c["overlap"],
                "partial": c["split"] + c["covered_inexact"],
                **{o: c[o] for o in GOLD_OUTCOMES if o != "exact"},
                "exact_recall": c["exact"] / n if n else None,
                "overlap_recall": c["overlap"] / n if n else None,
                "split_rate": c["split"] / n if n else None}

    tot = Counter()
    for c in per.values():
        tot.update(c)
    return {**block(tot), "per_label": {l: block(c) for l, c in sorted(per.items())}}


NEW_NAME_LABELS = ("GIVENNAME", "SURNAME", "STREET")


def seen_values(docs, labels=NEW_NAME_LABELS) -> dict[str, set[str]]:
    """label -> every exact gold value (the span's text, suffix included per
    D-9) that occurs in `docs`, an iterable of corpus-schema records
    ({"text", "entities"}) such as the training split."""
    seen: dict[str, set[str]] = {lab: set() for lab in labels}
    for rec in docs:
        text = rec["text"]
        for e in rec.get("entities", []):
            if e["label"] in seen:
                seen[e["label"]].add(text[e["start"]:e["end"]])
    return seen


def new_name_recall(docs: list[dict], seen: dict[str, set[str]]) -> dict:
    """The "new names" slice: recall on mentions whose exact value appears
    in training (`seen`) vs mentions whose value never does (`new`), per
    label in `seen`. A model that memorised its training names scores well
    on `seen` and badly on `new`; only `new` says it generalises."""
    pairs: dict[str, dict[str, list]] = {lab: {"seen": [], "new": []} for lab in seen}
    for d in docs:
        for g in d["gold"]:
            if g["label"] not in seen:
                continue
            bucket = "seen" if d["text"][g["start"]:g["end"]] in seen[g["label"]] else "new"
            pairs[g["label"]][bucket].append((g, d["pred"]))
    def rec(p):  # one label per block, so its per_label copy is redundant
        r = gold_recall(p)
        r.pop("per_label")
        return r

    out = {lab: {b: rec(p) for b, p in buckets.items()} for lab, buckets in pairs.items()}
    out["ALL"] = {b: rec([x for buckets in pairs.values() for x in buckets[b]])
                  for b in ("seen", "new")}
    return out


def _slice_doc_group(docs: list[dict]) -> dict:
    return {"documents": len(docs),
            "exact": exact_scores(docs)["micro"],
            "overlap": overlap_scores(docs)["micro"],
            "recall": gold_recall([(g, d["pred"]) for d in docs for g in d["gold"]]),
            "controls": control_fp(docs),
            "decoys": decoy_triggers(docs)["overall"]}


def _control_span_fp(pairs: list[tuple[dict, bool]]) -> dict:
    n, hit = len(pairs), sum(h for _, h in pairs)
    return {"spans": n, "spans_masked": hit, "span_fp_rate": hit / n if n else None}


def _scalar(v) -> bool:
    return isinstance(v, (str, int, float, bool))


def slices(docs: list[dict], keys: list[str] | None = None) -> dict:
    """Slices by any record field, at two levels.

    doc     every scalar field in a doc's `meta` (format, category, family,
            noise, ...); `density` falls back to a bucket of the gold count.
            Per value: exact and overlap P/R/F1, and exact/overlap recall
            overall and per label.
    entity  every extra scalar field on gold spans (e.g. `case` on a
            suffixed name); predictions carry no such field, so only
            recall is defined: exact/overlap recall and split spans,
            overall and per label.
    control every extra scalar field on `controls` spans (ordinary-word
            uses): how often anything is masked on them.

    Fields with more than MAX_SLICE_VALUES distinct values are skipped as
    identifiers unless named in `keys`."""
    forced = set(keys or [])

    def usable(k: str, values: set) -> bool:
        return k in forced or len(values) <= MAX_SLICE_VALUES

    doc_vals: dict[str, set] = defaultdict(set)
    for d in docs:
        for k, v in d.get("meta", {}).items():
            if _scalar(v):
                doc_vals[k].add(str(v))
    doc_keys = sorted(k for k, vals in doc_vals.items() if usable(k, vals))
    if "density" not in doc_keys:
        doc_keys.append("density")

    out_doc = {}
    for key in doc_keys:
        groups: dict[str, list] = defaultdict(list)
        for d in docs:
            val = d.get("meta", {}).get(key)
            if val is None and key == "density":
                val = density_bucket(len(d["gold"]))
            if val is not None and _scalar(val):
                groups[str(val)].append(d)
        if groups:
            out_doc[key] = {v: _slice_doc_group(g) for v, g in sorted(groups.items())}

    ent_vals: dict[str, set] = defaultdict(set)
    for d in docs:
        for g in d["gold"]:
            for k, v in g.items():
                if k not in ("label", "start", "end") and _scalar(v):
                    ent_vals[k].add(str(v))
    out_ent = {}
    for key in sorted(k for k, vals in ent_vals.items() if usable(k, vals)):
        groups: dict[str, list] = defaultdict(list)
        for d in docs:
            for g in d["gold"]:
                if g.get(key) is not None and _scalar(g[key]):
                    groups[str(g[key])].append((g, d["pred"]))
        out_ent[key] = {v: gold_recall(p) for v, p in sorted(groups.items())}

    ctl_vals: dict[str, set] = defaultdict(set)
    for d in docs:
        for c in d.get("controls", []):
            for k, v in c.items():
                if k not in ("start", "end") and _scalar(v):
                    ctl_vals[k].add(str(v))
    out_ctl = {}
    for key in sorted(k for k, vals in ctl_vals.items() if usable(k, vals)):
        groups = defaultdict(list)
        for d in docs:
            for c, hit in _control_hits(d)[1]:
                if c.get(key) is not None and _scalar(c[key]):
                    groups[str(c[key])].append((c, hit))
        out_ctl[key] = {v: _control_span_fp(p) for v, p in sorted(groups.items())}
    return {"doc": out_doc, "entity": out_ent, "control": out_ctl}


def score_docs(docs: list[dict], slice_keys: list[str] | None = None) -> dict:
    """Every per-set metric of P3-1, for one track."""
    return {
        "exact": exact_scores(docs),
        "overlap": overlap_scores(docs),
        "recall": gold_recall([(g, d["pred"]) for d in docs for g in d["gold"]]),
        "leakage": char_leakage(docs),
        "boundary": boundary_errors(docs),
        "decoys": decoy_triggers(docs),
        "controls": control_fp(docs),
        "documents": document_rates(docs),
        "slices": slices(docs, slice_keys),
        "calibration": calibration(docs),
    }


# ---------------------------------------------------------------------------
# Appendix replay: the benchmark lists only its errors, so no P/R/F1 here.
# ---------------------------------------------------------------------------

def appendix_replay(records: list[dict], preds: dict[str, list[dict]]) -> dict:
    """records: benchmark appendix documents with text, each with `entries`
    ({kind: gold|pred|hard_negative, label, start, end, error_class}).
    preds: data_id -> current predictions.

    Counts, overall and by error_class:
      gold   fixed (now predicted exactly) / still missed
      pred   reproduced (still produced exactly) / removed
      hard_negative  still triggered (any label, and same label)
    plus current predictions that overlap nothing listed ("unjudgeable":
    the appendix omits correctly found gold, so these are never FP)."""
    by_class: dict[str, Counter] = defaultdict(Counter)
    tot = Counter()
    for rec in records:
        cur = preds.get(rec["data_id"], [])
        cur_keys = Counter(map(_key, cur))
        entries = rec["entries"]
        for e in entries:
            cls = e.get("error_class") or "unknown"
            if e["kind"] == "gold":
                k = "gold_fixed" if cur_keys[_key(e)] else "gold_still_missed"
            elif e["kind"] == "pred":
                k = "pred_reproduced" if cur_keys[_key(e)] else "pred_removed"
            else:
                hits = [p for p in cur if _overlaps(p, e)]
                if not hits:
                    k = "decoy_cleared"
                else:
                    k = "decoy_still_triggered"
                    if any(p["label"] == e["label"] for p in hits):
                        by_class[cls]["decoy_still_triggered_same_label"] += 1
                        tot["decoy_still_triggered_same_label"] += 1
            by_class[cls][k] += 1
            tot[k] += 1
        listed_pred = {_key(e) for e in entries if e["kind"] == "pred"}
        for p in cur:
            if _key(p) in listed_pred:
                continue
            if any(_overlaps(p, e) for e in entries):
                tot["new_pred_overlapping_listed"] += 1
            else:
                tot["new_pred_unjudgeable"] += 1

    n_gold = tot["gold_fixed"] + tot["gold_still_missed"]
    n_pred = tot["pred_reproduced"] + tot["pred_removed"]
    n_hn = tot["decoy_still_triggered"] + tot["decoy_cleared"]
    return {
        "documents": len(records),
        "listed_gold": n_gold, "listed_pred": n_pred, "listed_hard_negative": n_hn,
        **dict(sorted(tot.items())),
        "pred_reproduced_rate": tot["pred_reproduced"] / n_pred if n_pred else None,
        "gold_still_missed_rate": tot["gold_still_missed"] / n_gold if n_gold else None,
        "by_error_class": {c: dict(sorted(v.items())) for c, v in sorted(by_class.items())},
    }


# ---------------------------------------------------------------------------
# Probes (P3-3): label confusion and per-family targets (eval/probes/targets.json)
# ---------------------------------------------------------------------------

def confusion_matrix(docs: list[dict]) -> dict:
    """gold label -> {"gold": n, "<pred label>": gold spans that a prediction
    of that OTHER label overlaps}. One gold span counts once per other label."""
    out: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        for g in d["gold"]:
            out[g["label"]]["gold"] += 1
            for lab in {p["label"] for p in d["pred"] if p["label"] != g["label"] and _overlaps(p, g)}:
                out[g["label"]][lab] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


def _target_metric(cond: dict, scores: dict, confusion: dict) -> float | None:
    m = cond["metric"]
    labels = cond.get("labels")
    rec = scores["recall"]
    if m in ("exact_recall", "overlap_recall", "split_spans", "wrong_label"):
        blocks = [rec["per_label"][l] for l in labels if l in rec["per_label"]] if labels else [rec]
        gold = sum(b["gold"] for b in blocks)
        if m == "split_spans":
            return float(sum(b["split"] for b in blocks))
        if m == "wrong_label":
            return float(sum(b["wrong_label"] for b in blocks))
        if not gold:
            return None
        key = "exact_hits" if m == "exact_recall" else "overlap_hits"
        return sum(b[key] for b in blocks) / gold
    if m == "exact_f1":
        return scores["exact"]["micro"]["f1"] if scores["recall"]["gold"] else None
    if m == "case_exact_recall_min":
        cases = scores["slices"]["entity"].get("case", {})
        vals = [c["exact_recall"] for c in cases.values() if c["exact_recall"] is not None]
        return min(vals) if vals else None
    if m in ("slice_exact_recall_min", "slice_exact_recall_spread"):
        # an entity slice field (code_density: `codes` 0/2/6): the worst value, or best minus worst
        vals = [c["exact_recall"] for c in scores["slices"]["entity"].get(cond["field"], {}).values()
                if c["exact_recall"] is not None]
        if not vals:
            return None
        return min(vals) if m == "slice_exact_recall_min" else max(vals) - min(vals)
    if m in ("decoy_trigger_rate", "decoy_trigger_rate_any") and cond.get("exclude_kinds"):
        # D-34c: policy items of these kinds are scored and reported apart, not counted here
        o = dict(scores["decoys"]["overall"])
        for k in cond["exclude_kinds"]:
            pk = scores["decoys"]["per_kind"].get(k)
            if pk:
                for f in ("decoys", "triggered_same_label", "triggered_any_label"):
                    o[f] -= pk[f]
        if not o["decoys"]:
            return None
        return (o["triggered_same_label"] if m == "decoy_trigger_rate" else o["triggered_any_label"]) / o["decoys"]
    if m == "decoy_trigger_rate":
        o = scores["decoys"]["overall"]
        return o["rate_same_label"] if o["decoys"] else None
    if m == "decoy_trigger_rate_any":
        o = scores["decoys"]["overall"]
        return o["rate_any_label"] if o["decoys"] else None
    if m == "control_fp_rate":
        c = scores["controls"]
        n = c["records"] + c["spans"]
        return (c["records_masked"] + c["spans_masked"]) / n if n else None
    if m == "pii_free_fp_rate" and cond.get("exclude_kinds"):
        # D-41c: PII-free documents holding a policy item of these kinds leave the count
        d = scores["documents"]
        n, fp = d["pii_free_documents"], d["pii_free_with_fp"]
        for key, b in d.get("pii_free_policy_kinds", {}).items():
            if set(key.split("|")) & set(cond["exclude_kinds"]):
                n, fp = n - b["documents"], fp - b["with_fp"]
        return fp / n if n else None
    if m == "pii_free_fp_rate":
        return scores["documents"]["pii_free_fp_rate"]
    if m == "char_leakage_rate":
        return scores["leakage"]["rate"] if scores["leakage"]["gold_chars"] else None
    if m == "confusion_rate":
        c = confusion.get(cond["from"], {})
        return sum(c.get(t, 0) for t in cond["to"]) / c["gold"] if c.get("gold") else None
    raise ValueError(f"unknown probe metric {m!r}")


_OPS = {">=": lambda a, b: a >= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}


def evaluate_target(target: dict, scores: dict, confusion: dict,
                    baseline: dict | None = None) -> dict:
    """One family's target. Each condition is absolute ({"metric", "op",
    "value"}) or relative to checkpoint 1 ({"metric", "op", "relative": f}:
    measured op f x baseline value, needs the baseline's measured values).
    `sanity` conditions say whether the probe shows the failure at all; for
    an absolute target that is simply "fails at checkpoint 1"."""
    rows = []
    for cond in target["conditions"]:
        v = _target_metric(cond, scores, confusion)
        thr, note = cond.get("value"), None
        if "relative" in cond:
            base = (baseline or {}).get(cond["metric"] + ":" + ",".join(cond.get("labels") or []))
            thr = None if base is None else cond["relative"] * base
            note = None if base is not None else "relative target: needs a checkpoint-1 baseline"
        passed = None if v is None or thr is None else _OPS[cond["op"]](v, thr)
        rows.append({**cond, "measured": v, "threshold": thr, "pass": passed, "note": note})
    sanity = []
    for cond in target.get("sanity", []):
        v = _target_metric(cond, scores, confusion)
        sanity.append({**cond, "measured": v,
                       "pass": None if v is None else _OPS[cond["op"]](v, cond["value"])})
    passed_all = all(r["pass"] is True for r in rows)
    if sanity:
        shows_failure = all(s["pass"] is True for s in sanity)
    else:
        shows_failure = not passed_all
    return {"conditions": rows, "pass": passed_all if all(r["pass"] is not None for r in rows) else None,
            "sanity": sanity, "shows_failure_at_ckpt1": shows_failure}


def baseline_values(target: dict, scores: dict, confusion: dict) -> dict:
    """The measured values a later run's relative conditions compare to."""
    out = {}
    for cond in target["conditions"]:
        if "relative" in cond:
            out[cond["metric"] + ":" + ",".join(cond.get("labels") or [])] = \
                _target_metric(cond, scores, confusion)
    return out
