"""Per-label entity counts, source vs translated, per language and split.

    python scripts/translate/label_counts.py --source-dir <runb-az-v4.2 dir> --out-dir <translation dir>
        [--langs en,tr,ru] [--splits train,val,test] [--md report.md] [--json report.json]

The question: do the documents the translation did not write (rejects, or still pending) hit some labels
harder than others? For every language and split it counts, per label:

  source      entities in all source documents of the split
  kept        of those, entities in documents that were translated and written
  lost        of those, entities in documents not written (rejected or not yet retried)
  lost %      lost / source
  translated  entities in the translated documents
  kept→trans  translated / kept: below 100% means a written document lost entities (a dropped mask or decoy)

Rejected documents tend to be the long, entity-rich ones, so the entity loss is higher than the document loss. A
label is therefore flagged against the overall entity loss: lost % above 1.25 times it, with at least 30 source
entities, i.e. that label is hit harder than the rest, not just along with everything else.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

SPLITS = ("train", "val", "test")
FLAG_RATIO, FLAG_MIN = 1.25, 30


def read(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def count(source_dir: Path, out_dir: Path, lang: str, split: str) -> dict | None:
    sp, tp = source_dir / f"{split}.docs.jsonl", out_dir / lang / f"{split}.docs.jsonl"
    if not sp.exists() or not tp.exists():
        return None
    trans: dict[str, collections.Counter] = {}
    for r in read(tp):
        trans[r["source_id"]] = collections.Counter(e["label"] for e in r.get("entities", []))
    src_all, kept, lost, translated = (collections.Counter() for _ in range(4))
    docs = written = 0
    source_ids: set[str] = set()
    for r in read(sp):
        c = collections.Counter(e["label"] for e in r.get("entities", []))
        docs += 1
        source_ids.add(r["id"])
        src_all.update(c)
        if r["id"] in trans:
            written += 1
            kept.update(c)
            translated.update(trans[r["id"]])
        else:
            lost.update(c)
    extra = len(set(trans) - source_ids)
    doc_loss = 100 * (docs - written) / docs if docs else 0.0
    ent_loss = 100 * sum(lost.values()) / sum(src_all.values()) if src_all else 0.0
    rows = {}
    for label in sorted(set(src_all) | set(translated)):
        s, k, l, t = src_all[label], kept[label], lost[label], translated[label]
        loss = 100 * l / s if s else 0.0
        rows[label] = {"source": s, "kept": k, "lost": l, "lost_pct": round(loss, 2), "translated": t,
                       "kept_to_translated_pct": round(100 * t / k, 2) if k else None,
                       "flag": bool(s >= FLAG_MIN and loss > FLAG_RATIO * ent_loss)}
    return {"docs": docs, "written": written, "doc_loss_pct": round(doc_loss, 2),
            "entity_loss_pct": round(ent_loss, 2), "not_in_source": extra,
            "entities_source": sum(src_all.values()), "entities_translated": sum(translated.values()),
            "labels": rows}


def markdown(report: dict, langs: list[str], splits: list[str]) -> str:
    L = ["# Entities per label: source vs translated", "",
         "`lost %` = entities in source documents that have no translation yet (rejected, or not retried), over all "
         "source entities of that label. `kept→trans` = translated entities over the entities of the documents that "
         f"were written (100% = nothing dropped inside written documents). ⚠ = lost % above {FLAG_RATIO}× the overall "
         f"entity loss of that language and split, with at least {FLAG_MIN} source entities.", ""]
    for split in splits:
        L += [f"## {split}", "", "| language | source docs | written | documents lost | entities source | entities translated | entities lost |",
              "|---|---|---|---|---|---|---|"]
        for lang in langs:
            r = report[lang].get(split)
            if r:
                L.append(f"| {lang} | {r['docs']:,} | {r['written']:,} | {r['doc_loss_pct']}% | {r['entities_source']:,} | {r['entities_translated']:,} | {r['entity_loss_pct']}% |")
        labels = sorted({l for lang in langs if report[lang].get(split) for l in report[lang][split]["labels"]},
                        key=lambda l: -max((report[g][split]["labels"].get(l, {}).get("source", 0)
                                            for g in langs if report[g].get(split)), default=0))
        L += ["", "| label | source | " + " | ".join(f"{g} lost % | {g} kept→trans" for g in langs) + " |",
              "|---|---|" + "---|---|" * len(langs)]
        for label in labels:
            src = max(report[g][split]["labels"].get(label, {}).get("source", 0) for g in langs if report[g].get(split))
            cells = []
            for g in langs:
                x = report[g].get(split, {}).get("labels", {}).get(label)
                if not x:
                    cells.append("– | –")
                    continue
                kt = x["kept_to_translated_pct"]
                cells.append(f"{x['lost_pct']}%{' ⚠' if x['flag'] else ''} | " + (f"{kt}%" if kt is not None else "–"))
            L.append(f"| {label} | {src:,} | " + " | ".join(cells) + " |")
        L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--langs", default="en,tr,ru")
    ap.add_argument("--splits", default=",".join(SPLITS))
    ap.add_argument("--json", type=Path)
    ap.add_argument("--md", type=Path)
    a = ap.parse_args(argv)
    langs, splits = a.langs.split(","), a.splits.split(",")
    report = {lang: {} for lang in langs}
    for lang in langs:
        for split in splits:
            r = count(a.source_dir, a.out_dir, lang, split)
            if r:
                report[lang][split] = r
                flagged = [l for l, x in r["labels"].items() if x["flag"]]
                print(f"{lang}/{split}: {r['written']:,}/{r['docs']:,} written ({r['doc_loss_pct']}% of documents, "
                      f"{r['entity_loss_pct']}% of entities lost); "
                      f"flagged labels: {', '.join(flagged) or 'none'}", flush=True)
    if a.json:
        a.json.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.md:
        a.md.write_text(markdown(report, langs, splits), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
