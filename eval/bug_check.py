"""Bug check for a mid-training checkpoint (D-44b): probes and the benchmark only, against Run B.

    python eval/bug_check.py --name TAG --probes-new P --bench-new P --probes-ref P --bench-ref P \
        [--model M --revision R --ref-model M --ref-revision R] [--cache-dir DIR] --out-dir DIR

Usually run by `scripts/release_check.sh <model> <revision> --bug-check`. Flags only clear bugs:
  - a label near 0 (exact recall or F1 below 5% with 20+ gold values, on the benchmark or the probes)
  - the benchmark far below Run B (micro F1 more than 10 points lower; a label more than 30 points lower)
  - a label map different from Run B's, or not a clean BIO scheme
  - a tokenizer different from Run B's (vocabulary, or the token ids of fixed test strings)
  - predictions with impossible offsets or labels outside the label map
  - values after the first 512-token window missed far more often than values before it (the
    tokenizers 0.23 bug, D-37)
No go/no-go verdict, never shadow-dev or real text: epoch 1 is not a release candidate, and its
numbers change nothing except for a clear bug (D-44b, F1, A9).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

MIN_GOLD = 20
NEAR_ZERO = 0.05
BENCH_GAP = 0.10
LABEL_GAP = 0.30
WINDOW_TOKENS = 510  # content tokens in one 512-token window
TOKENIZER_PROBES = ["Ərizəçi Həsənova Gülnarə Əli qızı, FİN 5ZK3T9P, tel. +994 (50) 123-45-67.",
                    "IBAN AZ21NABZ00000000137010001944; e-poçt: test.user@example.az; IPv6 2001:db8::1"]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8")) if p and Path(p).exists() else None


def pct(v):
    return "–" if v is None else f"{100 * v:.1f}"


def per_label(rep, set_name, track="R"):
    t = (rep or {}).get("sets", {}).get(set_name, {}).get("tracks", {}).get(track)
    return (t["all"]["exact"]["per_label"], t["all"]["exact"]["micro"]) if t else (None, None)


def label_checks(new, ref):
    """Near-zero labels (benchmark, probes) and labels / the benchmark far below Run B."""
    flags, info = [], {}
    for set_name in ("benchmark", "probes"):
        pl, micro = per_label(new, set_name)
        if pl is None:
            flags.append(f"{set_name}: not scored")
            continue
        for lab, v in sorted(pl.items()):
            gold = v["tp"] + v["fn"]
            if gold >= MIN_GOLD and (v["recall"] < NEAR_ZERO or v["f1"] < NEAR_ZERO):
                flags.append(f"{set_name}: {lab} near 0 (recall {pct(v['recall'])}, F1 {pct(v['f1'])}, {gold} gold values)")
    pl, micro = per_label(new, "benchmark")
    rpl, rmicro = per_label(ref, "benchmark")
    if pl and rpl:
        info["benchmark_f1_R"], info["ref_benchmark_f1_R"] = micro["f1"], rmicro["f1"]
        if micro["f1"] < rmicro["f1"] - BENCH_GAP:
            flags.append(f"benchmark micro F1 {pct(micro['f1'])}, more than {100 * BENCH_GAP:.0f} points below Run B's {pct(rmicro['f1'])}")
        for lab, v in sorted(pl.items()):
            r = rpl.get(lab)
            if r and v["tp"] + v["fn"] >= MIN_GOLD and v["f1"] < r["f1"] - LABEL_GAP:
                flags.append(f"benchmark: {lab} F1 {pct(v['f1'])}, more than {100 * LABEL_GAP:.0f} points below Run B's {pct(r['f1'])}")
    m, _ = per_label(new, "benchmark", "M")
    if m:
        info["benchmark_f1_M"] = per_label(new, "benchmark", "M")[1]["f1"]
    return flags, info


def label_map_checks(id2label, ref_id2label):
    flags = []
    tags = set(id2label.values())
    if "O" not in tags:
        flags.append("label map: no O tag")
    ents = {t[2:] for t in tags if t[:2] in ("B-", "I-")}
    for e in sorted(ents):
        if f"B-{e}" not in tags or f"I-{e}" not in tags:
            flags.append(f"label map: {e} lacks its B- or I- tag")
    odd = sorted(t for t in tags if t != "O" and t[:2] not in ("B-", "I-"))
    if odd:
        flags.append(f"label map: tags outside the BIO scheme: {', '.join(odd)}")
    if ref_id2label is not None:
        ref = set(ref_id2label.values())
        if tags != ref:
            flags.append(f"label map differs from Run B's: missing {sorted(ref - tags) or 'none'}, extra {sorted(tags - ref) or 'none'}")
        elif {int(k): v for k, v in id2label.items()} != {int(k): v for k, v in ref_id2label.items()}:
            flags.append("label map: same tags as Run B but different ids (check the checkpoint's config)")
    return flags, sorted(ents)


def tokenizer_checks(tok, ref_tok):
    if ref_tok is None:
        return []
    flags = []
    if len(tok) != len(ref_tok):
        flags.append(f"tokenizer vocabulary {len(tok)} vs Run B's {len(ref_tok)}")
    if getattr(tok, "model_max_length", None) != getattr(ref_tok, "model_max_length", None):
        flags.append(f"tokenizer model_max_length {getattr(tok, 'model_max_length', None)} vs Run B's "
                     f"{getattr(ref_tok, 'model_max_length', None)} (truncation)")
    for s in TOKENIZER_PROBES:
        if tok(s)["input_ids"] != ref_tok(s)["input_ids"]:
            flags.append("tokenizer: a fixed test string gets different token ids than with Run B's tokenizer")
            break
    return flags


def prediction_checks(docs_by_set, preds_by_set, labels):
    """Impossible offsets or labels outside the map, in the cached predictions."""
    bad_off, bad_lab, n = 0, {}, 0
    for key, preds in preds_by_set.items():
        texts = docs_by_set[key.split(".")[0]]
        for did, ps in preds.items():
            t = texts.get(did)
            if t is None:
                continue
            for p in ps:
                n += 1
                if not (0 <= p["start"] < p["end"] <= len(t)):
                    bad_off += 1
                if labels and p["label"] not in labels:
                    bad_lab[p["label"]] = bad_lab.get(p["label"], 0) + 1
    flags = []
    if bad_off:
        flags.append(f"predictions: {bad_off} of {n} with impossible offsets")
    if bad_lab:
        flags.append(f"predictions: labels outside the label map: {bad_lab}")
    return flags, n


def window_check(docs, preds, tok):
    """Exact recall of gold values that end after the first 512-token window vs before it."""
    hit = {"before": [0, 0], "after": [0, 0]}
    for d in docs:
        offs = tok(d["text"], return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]
        cut = offs[WINDOW_TOKENS - 1][1] if len(offs) > WINDOW_TOKENS else None
        got = {(p["label"], p["start"], p["end"]) for p in preds.get(d["id"], [])}
        for g in d["gold"]:
            k = "after" if cut is not None and g["end"] > cut else "before"
            hit[k][1] += 1
            hit[k][0] += (g["label"], g["start"], g["end"]) in got
    rb = hit["before"][0] / hit["before"][1] if hit["before"][1] else None
    ra = hit["after"][0] / hit["after"][1] if hit["after"][1] else None
    flags = []
    if ra is not None and rb and hit["after"][1] >= 30 and ra < 0.5 * rb:
        flags.append(f"long documents: values after the first 512-token window found {pct(ra)}% vs {pct(rb)}% before "
                     f"({hit['after'][1]} values after): the tokenizers 0.23 pattern (D-37)")
    return flags, {"recall_before_window": rb, "recall_after_window": ra, "values_after_window": hit["after"][1]}


def render_md(res):
    m = res["meta"]
    L = [f"# Bug check: `{m['model']}` @ `{m['revision'][:12]}`", "",
         f"`scripts/release_check.sh --bug-check`, {m['date_utc']}, code `{m['code']}`. Probes and the benchmark only, "
         "against Run B. **Not a release verdict** (D-44b): shadow-dev and real text are not looked at.", ""]
    if res["flags"]:
        L += [f"**{len(res['flags'])} possible bug(s):**", ""] + [f"- {f}" for f in res["flags"]]
    else:
        L += ["**No clear bug found.**"]
    i = res["info"]
    L += ["", "| Check | Result |", "|---|---|",
          f"| Benchmark micro F1 (R / M) | {pct(i.get('benchmark_f1_R'))} / {pct(i.get('benchmark_f1_M'))} (Run B {pct(i.get('ref_benchmark_f1_R'))}) |",
          f"| Label map | {i.get('n_tags', '–')} tags, {i.get('n_labels', '–')} labels{', same as Run B' if i.get('label_map_same') else ''} |",
          f"| Tokenizer | {i.get('tokenizer', '–')} |",
          f"| Predictions checked | {i.get('predictions_checked', '–')} |",
          f"| Values after the first 512-token window ({i.get('window_documents', '–')} runb_test documents, R) | found {pct(i.get('recall_after_window'))}% of "
          f"{i.get('values_after_window', '–')} vs {pct(i.get('recall_before_window'))}% before |"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("probes-new", "bench-new", "probes-ref", "bench-ref", "model", "revision", "ref-model", "ref-revision",
              "runb-test"):
        ap.add_argument(f"--{k}")
    ap.add_argument("--cache-dir", default=str(Path.home() / ".cache" / "pii-scoreboard"))
    ap.add_argument("--name", required=True)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    pn, bn = load(a.probes_new), load(a.bench_new)
    if not (pn and bn):
        raise SystemExit("probes and benchmark reports of the candidate are required")
    import scoreboard as S
    model, rev = bn["meta"]["model"], bn["meta"]["revision_sha"]
    flags, info = label_checks(bn | {"sets": {**bn["sets"], **pn["sets"]}}, load(a.bench_ref))
    # label map, tokenizer, predictions, long documents (offline from the Hugging Face cache)
    try:
        from transformers import AutoConfig, AutoTokenizer
        load_rev = None if Path(model).exists() else rev
        cfg = AutoConfig.from_pretrained(model, revision=load_rev)
        tok = AutoTokenizer.from_pretrained(model, revision=load_rev)
        ref_cfg = ref_tok = None
        if a.ref_model:
            ref_cfg = AutoConfig.from_pretrained(a.ref_model, revision=a.ref_revision)
            ref_tok = AutoTokenizer.from_pretrained(a.ref_model, revision=a.ref_revision)
        f, ents = label_map_checks(cfg.id2label, ref_cfg.id2label if ref_cfg else None)
        flags += f
        info.update(n_tags=len(cfg.id2label), n_labels=len(ents),
                    label_map_same=bool(ref_cfg) and set(cfg.id2label.values()) == set(ref_cfg.id2label.values()))
        f = tokenizer_checks(tok, ref_tok)
        flags += f
        info["tokenizer"] = (f"vocabulary {len(tok)}" + (", same ids as Run B on the test strings" if ref_tok and not f else ""))
        cache = Path(a.cache_dir).expanduser() / S._slug(model) / S._slug(rev)
        none = argparse.Namespace(private_dir=str(ROOT / ".no-private-sets"))
        docs = {s: S.load_set(s, none)[0] for s in ("benchmark", "probes")}
        texts = {s: {d["id"]: d["text"] for d in docs[s]} for s in docs}
        preds = {f"{s}.{t}": json.loads((cache / f"{s}.{t}.json").read_text(encoding="utf-8"))["preds"]
                 for s in docs for t in "RM" if (cache / f"{s}.{t}.json").exists()}
        f, n = prediction_checks(texts, preds, set(ents))
        flags += f
        info["predictions_checked"] = n
        # long documents: the cached predictions on the runb_test sample (the benchmark has none past one window)
        rt = cache / "runb_test.R.json"
        if a.runb_test and rt.exists():
            rp = json.loads(rt.read_text(encoding="utf-8"))["preds"]
            alld = S._read_jsonl([Path(a.runb_test)])  # the scoreboard's --sample 400 (seed 7)
            rdocs = [d for d in random.Random(7).sample(alld, min(400, len(alld))) if d["id"] in rp]
            f, w = window_check(rdocs, rp, tok)
            flags += f
            info.update(w, window_documents=len(rdocs))
        else:
            flags.append("long-document check not run (no runb_test sample)")
    except OSError as e:  # model files not in the local cache
        flags.append(f"could not load the checkpoint's config or tokenizer: {type(e).__name__}")
    res = {"meta": {"name": a.name, "model": model, "revision": rev, "code": S.git_info()["sha"][:7],
                    "date_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")},
           "flags": flags, "info": info}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "bug_check.json").write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    (out / "bug_check.md").write_text(render_md(res), encoding="utf-8")
    print(f"bug check: {len(flags)} possible bug(s)" + "".join(f"\n  - {f}" for f in flags) if flags else "bug check: no clear bug found")
    print(f"wrote {out}/bug_check.{{json,md}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
