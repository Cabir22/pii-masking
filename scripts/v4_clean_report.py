"""Dry run of the v4 cleaning pass (D-51f, D-51g): what `piigen.v4_clean`
would change in every current source, without modifying any of them.

    python scripts/v4_clean_report.py --out <dir> [--targeted data/raw/runb_v3verify_targeted.jsonl]
                                      [--examples 15] [--seed 20261015] [--gates]

Sources: the old corpus (`merged_relabeled_swept_dated/{train,val,test}`, az,
minus `az_drop_list.jsonl`, tagged `_old` as build_sprint_mix.read_old_az
does), the six LLM batches, the targeted file. Writes into <dir> only:

  cleaned/<source>.jsonl     the cleaned copies (old splits as old_<split>.jsonl)
  before/old_<split>.jsonl   the old splits as the build reads them, uncleaned
                             (for a before/after validate_corpus comparison)
  counts.json, counts.md     per rule x source: values labelled / unlabelled /
                             trimmed, documents dropped, name candidates left
                             unlabelled (unplaceable), IMEI-type extras
  examples.md                N random before/after examples per rule (seeded)
  names_excluded.tsv         the pool given names never relabelled, with why
  names_borderline.tsv       common words that are also names: native check
  surname_stoplist.tsv       R7's stoplist with its counts
  gates/                     with --gates: validate_corpus.py on every cleaned
                             file (and on the uncleaned old splits), and
                             eval/leakage_guard.py on all cleaned files with
                             benchmark_v3, as build_sprint_mix.py runs them
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.v4_clean import (LEXICON_PATH, RULE_IDS, Tally, clean_record,  # noqa: E402
                             lexicon_sha256)

OLD = ROOT / "data/processed/merged_relabeled_swept_dated"
LLM = [ROOT / f"data/raw/sprint1_llm_b{i}.clean.jsonl" for i in range(1, 7)]
TARGETED = ROOT / "data/raw/runb_v3verify_targeted.jsonl"
BENCH_V3 = ROOT / "data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl"


def mark(text: str, ents: list[dict], lo: int, hi: int) -> str:
    """text[lo:hi] with every entity inside written ⟦value⟧LABEL."""
    out, pos = [], lo
    for e in sorted(ents, key=lambda x: x["start"]):
        if e["end"] <= lo or e["start"] >= hi:
            continue
        s, en = max(e["start"], lo), min(e["end"], hi)
        out.append(text[pos:s])
        out.append(f"⟦{text[s:en]}⟧{e['label']}")
        pos = en
    out.append(text[pos:hi])
    return "".join(out).replace("\n", "⏎")


class Reservoir:
    """k random items per key, seeded, independent of the order of keys."""

    def __init__(self, k: int, seed: int):
        self.k, self.rng = k, random.Random(seed)
        self.items: dict[str, list] = defaultdict(list)
        self.seen: dict[str, int] = defaultdict(int)

    def offer(self, key: str, make) -> None:
        self.seen[key] += 1
        n = self.seen[key]
        if len(self.items[key]) < self.k:
            self.items[key].append(make())
        else:
            j = self.rng.randrange(n)
            if j < self.k:
                self.items[key][j] = make()


def example(doc: dict, res, ch) -> dict:
    text = doc["text"]
    if ch.action == "drop":
        return {"id": doc["id"], "rule": ch.rule, "action": "drop", "why": ch.note,
                "text": text[:220].replace("\n", "⏎")}
    lo, hi = max(0, ch.start - 70), min(len(text), ch.end + 60)
    after = res.doc["entities"] if res.doc is not None else []
    return {"id": doc["id"], "rule": ch.rule, "action": f"{ch.action} {ch.label}", "value": ch.text,
            "note": ch.note, "before": mark(text, doc.get("entities") or [], lo, hi),
            "after": mark(text, after, lo, hi) if res.doc is not None else "(record dropped: "
            + (res.changes[0].note if res.changes else "") + ")"}


def iter_old(split: str, drop: dict):
    with (OLD / f"{split}.docs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["lang"] == "az" and drop.get(r["id"]) != split:
                yield {**r, "_old": True}


def iter_file(path: Path):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line), line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--targeted", type=Path, default=TARGETED)
    ap.add_argument("--examples", type=int, default=15)
    ap.add_argument("--seed", type=int, default=20261015)
    ap.add_argument("--gates", action="store_true", help="run validate_corpus.py and leakage_guard.py")
    args = ap.parse_args(argv)
    out = args.out.resolve()
    if out.is_relative_to(ROOT / "data"):
        raise SystemExit("--out must not be inside data/ (a dry run modifies no data file)")
    (out / "cleaned").mkdir(parents=True, exist_ok=True)
    (out / "before").mkdir(parents=True, exist_ok=True)

    tally = Tally()
    res_ex = Reservoir(args.examples, args.seed)
    drop = {}
    for line in (OLD / "az_drop_list.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        drop[r["id"]] = r["split"]

    def handle(name: str, doc: dict, line: str | None, fout, fbefore=None):
        res = clean_record(doc, tally, name)
        if fbefore is not None:
            fbefore.write(json.dumps(doc, ensure_ascii=False) + "\n")
        if res.doc is not None:
            fout.write(line if (line is not None and res.doc is doc) else json.dumps(res.doc, ensure_ascii=False) + "\n")
        for ch in res.changes:
            if ch.action == "drop" or ch.note != "another occurrence":
                res_ex.offer(ch.rule if ch.action != "drop" else f"{ch.rule} (drop)",
                             lambda ch=ch: {"source": name, **example(doc, res, ch)})
        for ch in res.skipped:
            res_ex.offer(f"{ch.rule} (left unlabelled: unplaceable)",
                         lambda ch=ch: {"source": name, "id": doc["id"], "value": ch.text, "note": ch.note,
                                        "before": mark(doc["text"], doc["entities"], max(0, ch.start - 60),
                                                       min(len(doc["text"]), ch.end + 50))})

    files = {}
    for split in ("train", "val", "test"):
        name = f"old_{split}"
        with (out / "cleaned" / f"{name}.jsonl").open("w", encoding="utf-8") as fo, \
                (out / "before" / f"{name}.jsonl").open("w", encoding="utf-8") as fb:
            for doc in iter_old(split, drop):
                handle(name, doc, None, fo, fb)
        files[name] = out / "cleaned" / f"{name}.jsonl"
        print(f"{name}: {tally.docs_in[name]:,} in", flush=True)
    for path in [*LLM, args.targeted]:
        name = "targeted" if path == args.targeted else path.name.removesuffix(".clean.jsonl").replace("sprint1_", "")
        with (out / "cleaned" / f"{name}.jsonl").open("w", encoding="utf-8") as fo:
            for doc, line in iter_file(path):
                handle(name, doc, line, fo)
        files[name] = out / "cleaned" / f"{name}.jsonl"
        print(f"{name}: {tally.docs_in[name]:,} in", flush=True)

    sources = list(tally.docs_in)
    counts = tally.as_json()
    counts["lexicon"] = {"path": LEXICON_PATH.relative_to(ROOT).as_posix(), "sha256": lexicon_sha256()}
    (out / "counts.json").write_text(json.dumps(counts, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# v4 cleaning dry run (D-51f, D-51g)", "",
          f"Lexicon `{counts['lexicon']['path']}` sha256 `{counts['lexicon']['sha256'][:16]}…`; "
          "targeted copy `" + (args.targeted.resolve().relative_to(ROOT).as_posix()
                               if args.targeted.resolve().is_relative_to(ROOT) else str(args.targeted)) + "`.", "",
          "Cells: values labelled / values unlabelled / spans trimmed / documents dropped.", ""]
    md += tally.table(sources)
    md += ["", "## Documents changed (kept, at least one value changed) per rule", ""]
    md += ["| rule | " + " | ".join(sources) + " |", "|" + "---|" * (len(sources) + 1)]
    for rule in RULE_IDS:
        row = [tally.c[s, rule, "docs"] for s in sources]
        if any(row):
            md.append(f"| {rule} | " + " | ".join(f"{v:,}" for v in row) + " |")
    md += ["", "## Name candidates left unlabelled (the resolver would not place them)", ""]
    md += ["| rule | " + " | ".join(sources) + " |", "|" + "---|" * (len(sources) + 1)]
    for rule in ("R4", "R5"):
        md.append(f"| {rule} | " + " | ".join(f"{tally.c[s, rule, 'unplaceable']:,}" for s in sources) + " |")
    md += ["", "IMEI_BAD_LUHN look-alikes with a card's shape (checksum-only, not in D-51d, kept): "
           + json.dumps(dict(tally.extra)), ""]
    totals = defaultdict(int)
    for (s, r, w), n in tally.c.items():
        group = "old" if s.startswith("old") else "targeted" if s == "targeted" else "llm"
        totals[group, r, w] += n
    md += ["## Totals per source group", "", "| rule | old | llm | targeted |", "|---|---|---|---|"]
    for rule in RULE_IDS:
        cells = []
        for g in ("old", "llm", "targeted"):
            vals = [totals[g, rule, w] for w in ("labelled", "unlabelled", "trimmed", "dropped")]
            cells.append(" / ".join(f"{v:,}" for v in vals) if any(vals) else "")
        if any(cells):
            md.append(f"| {rule} | " + " | ".join(cells) + " |")
    (out / "counts.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    ex = ["# v4 cleaning: random before/after examples per rule", "",
          f"Up to {args.examples} per rule (seed {args.seed}); `⟦value⟧LABEL` marks a labelled span; "
          "only the first occurrence of each new value is sampled (its other occurrences follow it).", ""]
    for key in sorted(res_ex.items, key=lambda k: (RULE_IDS.index(k.split(" ")[0]) if k.split(" ")[0] in RULE_IDS
                                                  else 99, k)):
        ex += [f"## {key} ({res_ex.seen[key]:,} in all)", ""]
        for i, item in enumerate(res_ex.items[key], 1):
            ex.append(f"{i}. `{item['source']}` `{item['id']}`" + (f" — {item.get('action', '')}" if item.get("action") else "")
                      + (f" `{item['value']}`" if item.get("value") else "") + (f" ({item['note']})" if item.get("note") else "")
                      + (f" — {item['why']}" if item.get("why") else ""))
            if "before" in item:
                ex.append(f"   - before: {item['before']}")
            if "after" in item:
                ex.append(f"   - after:  {item['after']}")
            if "text" in item:
                ex.append(f"   - text: {item['text']}")
        ex.append("")
    (out / "examples.md").write_text("\n".join(ex) + "\n", encoding="utf-8")

    lex = json.loads(LEXICON_PATH.read_text(encoding="utf-8"))
    with (out / "names_excluded.tsv").open("w", encoding="utf-8") as fh:
        fh.write("name\treason\tlower_case_uses\tlabelled_givenname\tlabelled_city\n")
        for v in sorted(lex["given_excluded"].values(), key=lambda v: (v["reason"], -v["lower"], v["name"])):
            fh.write(f"{v['name']}\t{v['reason']}\t{v['lower']}\t{v['labelled_givenname']}\t{v['labelled_city']}\n")
    with (out / "names_borderline.tsv").open("w", encoding="utf-8") as fh:
        fh.write("name\tdecision\tlower_case_uses\tlabelled_givenname\n")
        for v in lex["given_borderline"]:
            fh.write(f"{v['name']}\t{v['decision']}\t{v['lower']}\t{v['labelled_givenname']}\n")
    with (out / "surname_stoplist.tsv").open("w", encoding="utf-8") as fh:
        fh.write("key\tlower_case_uses\tlabelled_surname\tlabelled_surname_old\n")
        for k, v in lex["surname_stoplist_counts"].items():
            fh.write(f"{k}\t{v['lower']}\t{v['labelled_surname']}\t{v['labelled_surname_old']}\n")
    print((out / "counts.md").read_text(encoding="utf-8"))

    if args.gates:
        g = out / "gates"
        g.mkdir(exist_ok=True)
        py = sys.executable
        for name, path in files.items():
            for tag, p in (("cleaned", path), *((("before", out / "before" / f"{name}.jsonl"),)
                                                 if name.startswith("old") else ())):
                cmd = [py, "scripts/validate_corpus.py", str(p), "--json", str(g / f"validate_{name}.{tag}.json")]
                if name.startswith("old"):
                    cmd.append("--skip-dedup")
                with (g / f"validate_{name}.{tag}.log").open("w", encoding="utf-8") as log:
                    rc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
                print(f"validate {name} ({tag}): exit {rc}", flush=True)
        cmd = [py, "eval/leakage_guard.py", *map(str, files.values()), "--bench-docs", str(BENCH_V3),
               "--json", str(g / "leakage_guard.json")]
        with (g / "leakage_guard.log").open("w", encoding="utf-8") as log:
            rc = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT).returncode
        print(f"leakage_guard (all cleaned files): exit {rc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
