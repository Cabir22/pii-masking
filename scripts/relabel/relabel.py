"""Relabel documents by a fixed list (D-70, D-76): remove listed labels or change them, text unchanged, in every
language.

    # AZ: the docs and v4.2's verified windows (m1/m2 keep AZ's windows, they are not re-tokenized)
    python scripts/relabel/relabel.py --list scripts/relabel/d70_list.tsv --lang az \
        --docs-dir <runb-az-v4.2 dir> --windows --out-dir <out>/az
    # EN / TR / RU: the docs (tokenized later, as in build_m1)
    python scripts/relabel/relabel.py --list scripts/relabel/d70_list.tsv --lang en \
        --docs-dir <runb-translated-v4.2>/en --out-dir <out>/en

The list (TSV) has one row per span: lang, split, doc_id (the AZ id; translations are found by their
`source_id`), start, end, label, value, text_sha16 (the first 16 hex of the document text's SHA-256), reason,
and relabel_to (optional, D-76): empty removes the label; a label name keeps the span and gives it that label
(A30-A32: building numbers labelled AGE become BUILDINGNUM). A list without the column only removes.
A row with no label and a relabel_to ADDS a missing span (D-78: v4.2's unlabelled card expiries become DATE): the
text there must be `value` and nothing may overlap it.
A row with no start is a document that has no translation in that language (rejected), and must be absent.

Strict, so a stale list never applies to the wrong text:
  * every listed span must exist exactly (start, end, label, and the text there equal to `value`) in a
    document whose text hash matches, and be listed once; anything else stops the run;
  * relabel_to must be a known label (piigen.config.ENTITY_TYPES) other than the row's label;
  * every listed document must be found, and a row marked "not translated" must really be absent;
  * windows (--windows): the listed documents are re-windowed with prepare_splits' own code (tokenizer,
    punctuation patch, max_length 512, stride 256); their input_ids must equal the stored windows exactly,
    then the new labels replace the old ones. Every other window is copied unchanged.
Writes {split}.docs.jsonl (and {split}.jsonl with --windows) to --out-dir, and relabel_report.json.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPLITS = ("train", "val", "test")
WINDOW_ID = re.compile(r'\{"id":\s*"([^"]+)"')


class RelabelError(Exception):
    pass


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_list(path: Path, lang: str) -> tuple[dict[str, list[dict]], set[str]]:
    """{doc_id: [span rows]} for `lang`, and the doc ids marked as not translated."""
    from piigen.config import ENTITY_TYPES
    spans: dict[str, list[dict]] = defaultdict(list)
    absent: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["lang"] != lang:
                continue
            if not row["start"]:
                absent.add(row["doc_id"])
                continue
            row["start"], row["end"] = int(row["start"]), int(row["end"])
            row["relabel_to"] = (row.get("relabel_to") or "").strip()
            if row["relabel_to"] and (row["relabel_to"] not in ENTITY_TYPES or row["relabel_to"] == row["label"]):
                raise RelabelError(f"{row['doc_id']} {row['start']}:{row['end']}: relabel_to {row['relabel_to']!r} "
                                   f"is not another known label")
            if not row["label"] and not row["relabel_to"]:
                raise RelabelError(f"{row['doc_id']} {row['start']}:{row['end']}: an add row (no label) needs relabel_to")
            spans[row["doc_id"]].append(row)
    return dict(spans), absent


def relabel_record(rec: dict, rows: list[dict]) -> dict:
    """The record with the listed spans' labels removed, changed or added; raises RelabelError on any mismatch."""
    text = rec["text"]
    key = rec.get("source_id") or rec["id"]
    if sha16(text) != rows[0]["text_sha16"]:
        raise RelabelError(f"{key}: the text changed (sha16 {sha16(text)} != {rows[0]['text_sha16']})")
    drop, change, add = set(), {}, []
    for row in rows:
        if not row["label"]:
            continue                                       # adds come after the removals, below
        hit = [i for i, e in enumerate(rec["entities"])
               if e["start"] == row["start"] and e["end"] == row["end"] and e["label"] == row["label"]]
        if len(hit) != 1 or text[row["start"]:row["end"]] != row["value"]:
            raise RelabelError(f"{key}: no {row['label']} {row['value']!r} at {row['start']}:{row['end']}")
        if hit[0] in drop or hit[0] in change:
            raise RelabelError(f"{key}: {row['start']}:{row['end']} is listed twice")
        if row.get("relabel_to"):
            change[hit[0]] = row["relabel_to"]
        else:
            drop.add(hit[0])
    kept = [e for i, e in enumerate(rec["entities"]) if i not in drop]
    for row in rows:
        if row["label"]:
            continue
        # D-78: add a missing span. The text there must be the value, and nothing may overlap it -- not a kept
        # entity, not another added span. A span this list removes does not count (D-82: a DATE trimmed to the
        # calendar date is listed as the old span removed and the trimmed one added)
        s, e = row["start"], row["end"]
        if text[s:e] != row["value"]:
            raise RelabelError(f"{key}: no {row['value']!r} at {s}:{e} to add")
        if any(x["start"] < e and s < x["end"] for x in kept + add):
            raise RelabelError(f"{key}: {s}:{e} ({row['value']!r}) overlaps a span already there")
        new = {"start": s, "end": e, "label": row["relabel_to"]}
        if rec["entities"] and "text" in rec["entities"][0]:
            new["text"] = row["value"]
        add.append(new)
    out = dict(rec)
    out["entities"] = [dict(e, label=change[i]) if i in change else e
                       for i, e in enumerate(rec["entities"]) if i not in drop]
    if add:
        out["entities"] = sorted(out["entities"] + add, key=lambda x: (x["start"], x["end"]))
    return out


def relabel_docs(records: list[dict], spans: dict[str, list[dict]], absent: set[str]) -> tuple[list[dict], dict]:
    out, done = [], set()
    for rec in records:
        key = rec.get("source_id") or rec["id"]
        if key in absent:
            raise RelabelError(f"{key}: listed as not translated, but the document is there")
        if key in spans:
            rec = relabel_record(rec, spans[key])
            done.add(key)
        out.append(rec)
    rows = [r for k in done for r in spans[k]]
    return out, {"documents": len(done), "spans": len(rows), "removed": sum(not r.get("relabel_to") for r in rows),
                 "relabelled": sum(bool(r.get("relabel_to") and r["label"]) for r in rows),
                 "added": sum(not r["label"] for r in rows), "done": sorted(done)}


def load_tokenizer(base_model: str):
    from prepare_splits import add_punctuation_boundary
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(base_model)
    if not add_punctuation_boundary(tok):
        raise RelabelError(f"{base_model}: no fast tokenizer, the punctuation patch cannot be applied")
    return tok


def relabel_windows(src: Path, dst: Path, docs: dict[str, dict], tokenizer, max_length: int, stride: int) -> dict:
    """Copy `src` windows to `dst`; the windows of `docs` (relabelled records by id) get new labels."""
    from prepare_splits import build_label_list, tokenize_split
    label2id = {l: i for i, l in enumerate(build_label_list())}
    fresh = {}
    for doc_id, rec in docs.items():
        for w in tokenize_split([rec], tokenizer, label2id, max_length, stride):
            fresh[w["id"]] = w
    seen, changed_tokens = set(), 0
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8", newline="\n") as fout:
        for line in fin:
            if not line.strip():
                continue
            m = WINDOW_ID.match(line)
            wid = m.group(1) if m else None
            doc_id = wid.rsplit("__w", 1)[0] if wid else None
            if doc_id not in docs:
                fout.write(line if line.endswith("\n") else line + "\n")
                continue
            w = json.loads(line)
            new = fresh.get(w["id"])
            if new is None or new["input_ids"] != w["input_ids"]:
                raise RelabelError(f"{w['id']}: re-windowing does not reproduce the stored input_ids")
            changed_tokens += sum(a != b for a, b in zip(w["labels"], new["labels"]))
            w["labels"] = new["labels"]
            seen.add(w["id"])
            fout.write(json.dumps(w, ensure_ascii=False) + "\n")
    missing = sorted(set(fresh) - seen)
    if missing:
        raise RelabelError(f"windows not found in {src.name}: {missing[:3]}")
    return {"windows": len(seen), "labels_changed": changed_tokens}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", type=Path, required=True)
    ap.add_argument("--lang", required=True, choices=("az", "en", "tr", "ru"))
    ap.add_argument("--docs-dir", type=Path, required=True, help="holds {train,val,test}.docs.jsonl")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--windows", action="store_true", help="also relabel {split}.jsonl windows (AZ)")
    ap.add_argument("--base-model", default="xlm-roberta-large")
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--stride", type=int, default=256)
    a = ap.parse_args(argv)
    try:
        spans, absent = load_list(a.list, a.lang)
    except RelabelError as exc:
        print(f"RELABEL FAILED: {exc}", file=sys.stderr)
        return 1
    a.out_dir.mkdir(parents=True, exist_ok=True)
    report = {"list": str(a.list), "list_sha256": file_sha256(a.list), "lang": a.lang, "splits": {}}
    tokenizer = load_tokenizer(a.base_model) if a.windows else None
    found = set()
    try:
        for split in SPLITS:
            src = a.docs_dir / f"{split}.docs.jsonl"
            if not src.exists():
                continue
            records, rep = relabel_docs(read_jsonl(src), spans, absent)
            found |= set(rep.pop("done"))
            dst = a.out_dir / src.name
            with dst.open("w", encoding="utf-8", newline="\n") as f:
                for r in records:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            rep.update(input_sha256=file_sha256(src), output_sha256=file_sha256(dst))
            if a.windows and rep["documents"]:
                docs = {r["id"]: r for r in records if r["id"] in spans}
                wsrc, wdst = a.docs_dir / f"{split}.jsonl", a.out_dir / f"{split}.jsonl"
                rep["windows"] = relabel_windows(wsrc, wdst, docs, tokenizer, a.max_length, a.stride)
                rep["windows"].update(input_sha256=file_sha256(wsrc), output_sha256=file_sha256(wdst))
            elif a.windows:
                (a.out_dir / f"{split}.jsonl").write_bytes((a.docs_dir / f"{split}.jsonl").read_bytes())
            report["splits"][split] = rep
            print(f"{a.lang}/{split}: {rep['documents']} documents, {rep['removed']} labels removed, "
                  f"{rep['relabelled']} relabelled, {rep['added']} added"
                  + (f"; windows {rep['windows']['windows']}, token labels changed {rep['windows']['labels_changed']}"
                     if "windows" in rep else ""), flush=True)
        missing = sorted(set(spans) - found)
        if missing:
            raise RelabelError(f"listed documents not found in {a.docs_dir}: {missing[:5]}")
    except RelabelError as exc:
        print(f"RELABEL FAILED: {exc}", file=sys.stderr)
        return 1
    report["documents"] = len(found)
    rows = [r for k in found for r in spans[k]]
    report["spans"] = len(rows)
    report["removed"] = sum(not r["relabel_to"] for r in rows)
    report["relabelled"] = dict(collections.Counter(f"{r['label']}->{r['relabel_to']}" for r in rows
                                                    if r["relabel_to"] and r["label"]))
    report["added"] = dict(collections.Counter(r["relabel_to"] for r in rows if not r["label"]))
    (a.out_dir / "relabel_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"{a.lang}: {report['documents']} documents, {report['removed']} labels removed, "
          f"{sum(report['relabelled'].values())} relabelled {report['relabelled']}, "
          f"{sum(report['added'].values())} added {report['added']} (list sha256 {report['list_sha256'][:12]})")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
