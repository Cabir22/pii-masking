"""D-64c: the translated splits keep the source's ids and splits.

    python scripts/translate/check_splits.py --source-dir <runb-az-v4.2 dir> --out-dir <translation dir>
        [--langs en,tr,ru] [--json report.json]

For each language, over <out-dir>/<lang>/{train,val,test}.docs.jsonl:
  * every row's `split` is one of train / val / test;
  * every row's `split` is the split of its file;
  * every row's `split` equals its source document's split
    (<source-dir>/{train,val,test}.docs.jsonl);
  * every `source_id` is a v4.2 document;
  * no `source_id` is in two splits, and none twice in one.
Exit 0 only if every check passes.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

SPLITS = ("train", "val", "test")


def source_splits(source_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in SPLITS:
        p = source_dir / f"{s}.docs.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    out[json.loads(line)["id"]] = s
    return out


def check_lang(out_dir: Path, lang: str, src: dict[str, str]) -> dict:
    c = collections.Counter()
    seen: dict[str, set[str]] = collections.defaultdict(set)
    examples: dict[str, list] = collections.defaultdict(list)
    for s in SPLITS:
        p = out_dir / lang / f"{s}.docs.jsonl"
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                c[f"rows {s}"] += 1
                sid, sp = r.get("source_id"), r.get("split")
                if sp not in SPLITS:
                    c["split not in train/val/test"] += 1
                    examples["split not in train/val/test"].append((sid, sp))
                if sp != s:
                    c["split differs from its file"] += 1
                    examples["split differs from its file"].append((sid, sp, s))
                if sid not in src:
                    c["source_id not in v4.2"] += 1
                    examples["source_id not in v4.2"].append(sid)
                elif src[sid] != sp:
                    c["split differs from the source's"] += 1
                    examples["split differs from the source's"].append((sid, sp, src[sid]))
                if s in seen[sid]:
                    c["source_id twice in one split"] += 1
                seen[sid].add(s)
    multi = [sid for sid, ss in seen.items() if len(ss) > 1]
    c["source_id in two splits"] = len(multi)
    examples["source_id in two splits"] = multi[:5]
    bad = [k for k in ("split not in train/val/test", "split differs from its file", "source_id not in v4.2",
                       "split differs from the source's", "source_id twice in one split", "source_id in two splits")
           if c[k]]
    return {"counts": dict(c), "failed": bad, "examples": {k: v[:5] for k, v in examples.items() if v}}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-dir", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--langs", default="en,tr,ru")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    src = source_splits(a.source_dir)
    report = {"source_docs": len(src), "langs": {}}
    ok = True
    for lang in a.langs.split(","):
        r = check_lang(a.out_dir, lang, src)
        report["langs"][lang] = r
        ok &= not r["failed"]
        print(f"{lang}: " + ", ".join(f"{k} {v}" for k, v in sorted(r["counts"].items()))
              + ("  PASS" if not r["failed"] else f"  FAIL: {r['failed']}"))
    if a.json:
        a.json.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
