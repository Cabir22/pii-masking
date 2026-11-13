"""The translation test run: survival, rejection reasons, cost, per language.

    python reports/translation_test/analyse.py <sample.jsonl> <dir with real_{en,tr,ru}.jsonl> [--md out.md] [--json out.json]

Per language: documents written / sent (overall and per source), the repair
queue's reasons, whether each targeted document's declared look-alikes (`_decoys`,
which the harness does not protect) came back verbatim, and the run's calls,
tokens and seconds (from run_test.py's <out>.usage.json), scaled to 1,000
documents and to runb-az-v4.1's train split (135,270 documents).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

TRAIN_DOCS = 135_270


def source(r: dict) -> str:
    if r.get("_source") == "targeted" or str(r["id"]).startswith("runb_targeted"):
        return "targeted"
    return "old" if r.get("_old") else "llm"


def reason_of(q: dict) -> str:
    for k in ("reason", "problem", "error", "why", "status"):
        if q.get(k):
            r = str(q[k])
            r = re.sub(r"\d+", "N", r)
            return r[:90]
    return "?"


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")] if path.exists() else []


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("sample")
    ap.add_argument("dir")
    ap.add_argument("--md")
    ap.add_argument("--json")
    a = ap.parse_args()
    src = {r["id"]: r for r in load(Path(a.sample))}
    n_src = collections.Counter(source(r) for r in src.values())
    d = Path(a.dir)
    res = {}
    for lang in ("en", "tr", "ru"):
        out = load(d / f"real_{lang}.jsonl")
        rq = load(d / f"real_{lang}.repair_queue.jsonl")
        use = json.loads((d / f"real_{lang}.jsonl.usage.json").read_text()) if (d / f"real_{lang}.jsonl.usage.json").exists() else {}
        written = {}
        for r in out:
            sid = r.get("source_id") or r["id"].rsplit("__", 1)[0]
            written[sid] = r
        by_src = collections.Counter(source(src[s]) for s in written if s in src)
        reasons = collections.Counter(reason_of(q) for q in rq)
        # targeted look-alikes: did each declared `_decoys` value come back verbatim?
        dec_total = dec_kept = 0
        for sid, r in written.items():
            s = src.get(sid)
            if not s or source(s) != "targeted":
                continue
            for x in s.get("_decoys") or []:
                v = s["text"][x["start"]:x["end"]]
                dec_total += 1
                dec_kept += v in r["text"]
        labelled_decoy = 0
        for sid, r in written.items():
            s = src.get(sid)
            if not s:
                continue
            vals = {s["text"][x["start"]:x["end"]] for x in s.get("_decoys") or []}
            labelled_decoy += sum(r["text"][e["start"]:e["end"]] in vals for e in r.get("entities", []))
        k = 1000 / max(1, len(src))
        res[lang] = {
            "sent": len(src), "written": len(written), "survival": len(written) / max(1, len(src)),
            "by_source": {s: f"{by_src[s]}/{n_src[s]}" for s in sorted(n_src)},
            "repair_queue": len(rq), "reasons": dict(reasons.most_common(8)),
            "targeted_lookalikes_kept_verbatim": f"{dec_kept}/{dec_total}",
            "lookalike_values_now_labelled": labelled_decoy,
            "usage": use,
            "per_1000_docs": {"calls": round(use.get("calls", 0) * k), "prompt_tokens": round(use.get("prompt_tokens", 0) * k),
                              "completion_tokens": round(use.get("completion_tokens", 0) * k),
                              "reasoning_tokens": round(use.get("reasoning_tokens", 0) * k),
                              "minutes_at_concurrency": round(use.get("seconds", 0) * k / 60, 1)},
        }
    L = ["# Translation test run: 300 documents of runb-az-v4.1 train", ""]
    L += ["| | " + " | ".join(res) + " |", "|---|" + "---|" * len(res)]
    rows = [("survival (written / sent)", lambda r: f"{r['written']}/{r['sent']} = {r['survival']:.1%}")]
    rows += [(f"  {s}", (lambda s: lambda r: r["by_source"][s])(s)) for s in sorted(n_src)]
    rows += [("repair queue", lambda r: str(r["repair_queue"])),
             ("targeted look-alikes kept verbatim", lambda r: r["targeted_lookalikes_kept_verbatim"]),
             ("look-alike values now labelled", lambda r: str(r["lookalike_values_now_labelled"])),
             ("API calls (incl. retries)", lambda r: str(r["usage"].get("calls", "?"))),
             ("prompt / completion tokens", lambda r: f"{r['usage'].get('prompt_tokens', 0):,} / {r['usage'].get('completion_tokens', 0):,}"),
             ("wall time (concurrency 8)", lambda r: f"{r['usage'].get('seconds', 0) / 60:.1f} min"),
             ("per 1,000 docs: tokens in / out", lambda r: f"{r['per_1000_docs']['prompt_tokens']:,} / {r['per_1000_docs']['completion_tokens']:,}"),
             ("per 1,000 docs: minutes", lambda r: str(r["per_1000_docs"]["minutes_at_concurrency"]))]
    for name, f in rows:
        L.append(f"| {name} | " + " | ".join(f(res[x]) for x in res) + " |")
    for lang, r in res.items():
        L += ["", f"## {lang}: repair-queue reasons", ""] + [f"- {v} × {k}" for k, v in r["reasons"].items()]
    text = "\n".join(L) + "\n"
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8", newline="\n")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
