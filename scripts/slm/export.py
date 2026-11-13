"""SLM test plan, task 2.1: one id list, and every arm's training data from it.

The SLM test plan, section 2 and task 2.1:
  - 64,000 training documents from merged_relabeled_swept/train.docs.jsonl,
    16,000 per language, and 4,000 validation documents (1,000 per language)
    from val.docs.jsonl; stratified, seed 20261001, natural label mix kept
    (the ~24% of documents with no PII included), no oversampling;
  - documents whose gold spans do not survive a round trip through grounding
    (roundtrip.py) are removed from the pool first, so they are out of every
    arm and the counts stay exactly 64,000 / 4,000;
  - exports, all from the same id list:
      docs/   the documents themselves (text + gold spans)
      xlmr/   BIO windows for arm 0: the production recipe, unchanged
              (xlm-roberta-large + punctuation patch, 512 / stride 256,
              prepare_splits.tokenize_split) -- what model/train.py reads
      qwen3/  BIO windows for arm A: Qwen3-1.7B tokenizer, 2,048 / 256
              overlap, the same labelling rule (align_labels_for_window)
      chat/   arm B: {"id", "messages": [system, user, assistant]}, the
              assistant turn being LABEL<TAB>value lines or NONE
      opf/    arm C: {"text", "spans": {"LABEL: value": [[start, end]]}} and
              labels27.json for `opf train --label-space-json`
  - a data card (DATA_CARD.md, data_card.json): ids hash, counts per language
    and label, the seed, file hashes, window counts and edge statistics.

The id lists (data/slm/ids/) are committed; the exports are regenerated from
them on any machine (data/slm/export/ is git-ignored). Run again without
--resample and the same ids give byte-identical files.

    python scripts/slm/export.py              # reuse data/slm/ids/ if present
    python scripts/slm/export.py --resample   # draw the id lists (before any arm trains)
    python scripts/slm/export.py --formats docs,chat,opf
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import roundtrip as RT                                               # noqa: E402
from piigen.config import ENTITY_TYPES                               # noqa: E402
from prepare_splits import (_rarest_label, add_punctuation_boundary,  # noqa: E402
                            align_labels_for_window, build_label_list, tokenize_split)

SRC = ROOT / "data" / "processed" / "merged_relabeled_swept"
OUT = ROOT / "data" / "slm"
SEED = 20261001
LANGS = ("az", "en", "ru", "tr")
PER_LANG = {"train": 16_000, "val": 1_000}
FORMATS = ("docs", "xlmr", "qwen3", "chat", "opf")
XLMR_TOKENIZER = "xlm-roberta-large"
QWEN_TOKENIZER = "Qwen/Qwen3-1.7B"
XLMR_WINDOW = (512, 256)
QWEN_WINDOW = (2048, 256)
CHUNK = 500


# ---------------------------------------------------------------------------
# Pool, round trip and sampling
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ids_hash(ids) -> str:
    return hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode("utf-8")).hexdigest()


def load_pool(path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    """All records by id, and {id: reason} for those failing the round trip."""
    pool, dropped = {}, {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            ok, why = RT.round_trip(r["text"], r["entities"])
            if ok:
                pool[r["id"]] = r
            else:
                dropped[r["id"]] = why
    return pool, dropped


def allocate(sizes: dict[str, int], n: int) -> dict[str, int]:
    """Proportional quotas summing to n (largest remainder, ties by stratum name)."""
    total = sum(sizes.values())
    if n > total:
        raise SystemExit(f"asked for {n} documents, only {total} available")
    exact = {k: n * v / total for k, v in sizes.items()}
    quota = {k: int(x) for k, x in exact.items()}
    rest = n - sum(quota.values())
    for k in sorted(exact, key=lambda k: (-(exact[k] - quota[k]), k))[:rest]:
        quota[k] += 1
    return quota


def sample(pool: dict[str, dict], per_lang: int, seed: int, split: str) -> list[str]:
    """Stratified within each language by the rarest label present (prepare_splits'
    key), so the natural label mix and the no-PII share are kept."""
    label_freq = collections.Counter(e["label"] for r in pool.values() for e in r["entities"])
    chosen = []
    for lang in LANGS:
        strata: dict[str, list[str]] = collections.defaultdict(list)
        for rid, r in pool.items():
            if r["lang"] == lang:
                strata[_rarest_label(r["entities"], label_freq)].append(rid)
        quota = allocate({k: len(v) for k, v in strata.items()}, per_lang)
        rng = random.Random(f"{seed}:{split}:{lang}")
        for key in sorted(strata):
            chosen += rng.sample(sorted(strata[key]), quota[key])
    return sorted(chosen)


# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

def trim_offsets(text: str, offsets) -> list[tuple[int, int]]:
    """Byte-level BPE offsets carry the token's leading space (' Əli') or a
    trailing newline ('.\\n'). Trim whitespace off tokens that have other
    content, so `tok_start == entity_start` means what it means for XLM-R;
    whitespace-only tokens keep their offsets (O, or I inside an entity)."""
    out = []
    for s, e in offsets:
        if s < e and not text[s:e].isspace():
            while text[s].isspace():
                s += 1
            while text[e - 1].isspace():
                e -= 1
        out.append((s, e))
    return out


def qwen_windows(records: list[dict], tokenizer, label2id: dict[str, int]) -> list[dict]:
    max_length, stride = QWEN_WINDOW
    rows = []
    for r in records:
        enc = tokenizer(r["text"], return_offsets_mapping=True, return_overflowing_tokens=True,
                        truncation=True, max_length=max_length, stride=stride)
        for w in range(len(enc["input_ids"])):
            rows.append({"id": f"{r['id']}__w{w}", "input_ids": enc["input_ids"][w],
                         "attention_mask": enc["attention_mask"][w],
                         "labels": align_labels_for_window(
                             trim_offsets(r["text"], enc["offset_mapping"][w]),
                             r["entities"], label2id)})
    return rows


def chat_row(r: dict) -> dict:
    return {"id": r["id"], "lang": r["lang"], "messages": [
        {"role": "system", "content": RT.SYSTEM_PROMPT},
        {"role": "user", "content": r["text"]},
        {"role": "assistant", "content": RT.completion(r["text"], r["entities"])}]}


def opf_row(r: dict) -> dict:
    spans: dict[str, list[list[int]]] = {}
    for e in sorted(r["entities"], key=lambda e: (e["start"], e["end"])):
        spans.setdefault(f"{e['label']}: {r['text'][e['start']:e['end']]}", []).append(
            [e["start"], e["end"]])
    return {"text": r["text"], "spans": spans, "info": {"id": r["id"], "lang": r["lang"]}}


def write_rows(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def chunked(records: list[dict], fn):
    for i in range(0, len(records), CHUNK):
        yield from fn(records[i:i + CHUNK])


def load_tokenizers(formats) -> dict:
    from transformers import AutoTokenizer
    toks = {}
    if "xlmr" in formats:
        toks["xlmr"] = AutoTokenizer.from_pretrained(XLMR_TOKENIZER)
        if not add_punctuation_boundary(toks["xlmr"]):
            raise SystemExit("xlm-roberta-large has no fast tokenizer: cannot apply the production patch")
    if "qwen3" in formats:
        toks["qwen3"] = AutoTokenizer.from_pretrained(QWEN_TOKENIZER)
        if not toks["qwen3"].is_fast:
            raise SystemExit("Qwen3 tokenizer is not a fast tokenizer: no offsets")
    return toks


def export(split: str, records: list[dict], formats, toks: dict, out: Path) -> dict:
    label_list = build_label_list()
    label2id = {lab: i for i, lab in enumerate(label_list)}
    files = {}
    if "docs" in formats:
        files["docs"] = (out / "docs" / f"{split}.docs.jsonl", write_rows(out / "docs" / f"{split}.docs.jsonl", records))
    if "xlmr" in formats:
        ml, st = XLMR_WINDOW
        p = out / "xlmr" / f"{split}.jsonl"
        files["xlmr"] = (p, write_rows(p, chunked(records, lambda c: tokenize_split(c, toks["xlmr"], label2id, ml, st))))
    if "qwen3" in formats:
        p = out / "qwen3" / f"{split}.jsonl"
        files["qwen3"] = (p, write_rows(p, chunked(records, lambda c: qwen_windows(c, toks["qwen3"], label2id))))
    if "chat" in formats:
        p = out / "chat" / f"{split}.jsonl"
        files["chat"] = (p, write_rows(p, map(chat_row, records)))
    if "opf" in formats:
        p = out / "opf" / f"{split}.jsonl"
        files["opf"] = (p, write_rows(p, map(opf_row, records)))
    return files


def write_label_files(formats, out: Path) -> None:
    label_list = build_label_list()
    blob = json.dumps({"labels": label_list,
                       "label2id": {lab: i for i, lab in enumerate(label_list)},
                       "id2label": {i: lab for i, lab in enumerate(label_list)}},
                      indent=2, ensure_ascii=False)
    for fmt in ("xlmr", "qwen3"):
        if fmt in formats:
            (out / fmt).mkdir(parents=True, exist_ok=True)
            (out / fmt / "labels.json").write_text(blob, encoding="utf-8", newline="\n")
    if "opf" in formats:
        (out / "opf").mkdir(parents=True, exist_ok=True)
        (out / "opf" / "labels27.json").write_text(json.dumps(
            {"category_version": "pii-masking-27", "span_class_names": ["O", *ENTITY_TYPES]},
            indent=2), encoding="utf-8", newline="\n")


# ---------------------------------------------------------------------------
# Verification: "all formats come from one id list, and the round-trip check
# reports 0 failures"
# ---------------------------------------------------------------------------

def verify(split: str, ids: list[str], records: dict[str, dict], files: dict) -> dict:
    want = set(ids)
    result = {}
    for fmt, (path, _n) in files.items():
        seen, bad = set(), 0
        for line in path.open(encoding="utf-8"):
            row = json.loads(line)
            if fmt in ("xlmr", "qwen3"):
                seen.add(row["id"].rsplit("__w", 1)[0])
                continue
            rid = row["info"]["id"] if fmt == "opf" else row["id"]
            seen.add(rid)
            gold = {(e["start"], e["end"], e["label"]) for e in records[rid]["entities"]}
            if fmt == "chat":
                lines, rejected = RT.parse(row["messages"][2]["content"])
                found, missing = RT.ground(row["messages"][1]["content"], lines)
                got = {(f["start"], f["end"], f["label"]) for f in found}
                bad += bool(rejected or missing or got != gold or len(found) != len(gold))
            elif fmt == "opf":
                got = set()
                for key, offs in row["spans"].items():
                    label, _, value = key.partition(": ")
                    for s, e in offs:
                        got.add((s, e, label))
                        bad += row["text"][s:e] != value
                bad += got != gold
            elif fmt == "docs":
                bad += row != records[rid]
        result[fmt] = {"same_ids": seen == want, "round_trip_or_content_failures": bad}
    return result


# ---------------------------------------------------------------------------
# Data card
# ---------------------------------------------------------------------------

def edge_stats(records: list[dict], toks: dict) -> dict:
    """Entities whose start or end falls inside a token (a token classifier
    cannot hit that edge exactly), and documents needing more than one window."""
    out = {}
    for name, tok in toks.items():
        # XLM-R spends 2 of its 512 positions on <s> and </s>; Qwen adds no special tokens
        capacity = XLMR_WINDOW[0] - 2 if name == "xlmr" else QWEN_WINDOW[0]
        n_ent = inside = multi = 0
        for r in records:
            offs = tok(r["text"], return_offsets_mapping=True, add_special_tokens=False,
                       verbose=False)["offset_mapping"]
            if name == "qwen3":
                offs = trim_offsets(r["text"], offs)
            starts = {s for s, e in offs if s < e}
            ends = {e for s, e in offs if s < e}
            multi += len(offs) > capacity
            for e in r["entities"]:
                n_ent += 1
                inside += e["start"] not in starts or e["end"] not in ends
        out[name] = {"entities": n_ent, "edge_inside_token": inside,
                     "edge_inside_token_share": inside / n_ent if n_ent else 0.0,
                     "docs_over_one_window": multi, "docs": len(records)}
    return out


def counts(records: list[dict]) -> dict:
    per_lang = collections.Counter(r["lang"] for r in records)
    no_pii = collections.Counter(r["lang"] for r in records if not r["entities"])
    mentions = {lang: collections.Counter() for lang in LANGS}
    for r in records:
        mentions[r["lang"]].update(e["label"] for e in r["entities"])
    tier3 = sum(1 for r in records for e in r["entities"]
                if RT.render_value(r["text"][e["start"]:e["end"]]) != r["text"][e["start"]:e["end"]])
    return {"docs": dict(per_lang), "no_pii_docs": dict(no_pii),
            "mentions": {lang: dict(sorted(c.items())) for lang, c in mentions.items()},
            "values_rendered_on_one_line": tier3}


def tool_versions() -> dict:
    import tokenizers
    import transformers
    from huggingface_hub import scan_cache_dir
    revs = {}
    try:
        for repo in scan_cache_dir().repos:
            if repo.repo_id in (XLMR_TOKENIZER, QWEN_TOKENIZER):
                revs[repo.repo_id] = sorted(r.commit_hash for r in repo.revisions)[-1]
    except Exception:
        pass
    return {"python": sys.version.split()[0], "transformers": transformers.__version__,
            "tokenizers": tokenizers.__version__, "tokenizer_revisions": revs}


def render_card(card: dict) -> str:
    L = ["# SLM test data card (task 2.1)", "",
         f"Generated {card['generated']} by `scripts/slm/export.py`. "
         "Plan: the SLM test plan (sections 2, 4 and task 2.1).", "",
         "| | |", "|---|---|",
         f"| Seed | `{card['seed']}` |",
         f"| Source | `{card['source']['dir']}` |"]
    for split in ("train", "val"):
        s = card["splits"][split]
        L.append(f"| {split} ids hash (sha256 of sorted ids, one per line) | `{s['ids_hash']}` |")
    L.append(f"| Combined ids hash | `{card['ids_hash_all']}` |")
    for name, h in card["source"]["sha256"].items():
        L.append(f"| Source `{name}` sha256 | `{h}` |")
    L += ["", "## Round trip through grounding", "",
          "Pool documents whose gold spans do not come back exactly were removed before "
          "sampling, so they are out of every arm. Ids in `ids/roundtrip_dropped_<split>.txt`.", "",
          "| split | pool | dropped | share | reasons |", "|---|---:|---:|---:|---|"]
    for split in ("train", "val"):
        s = card["splits"][split]
        L.append(f"| {split} | {s['pool']} | {s['dropped']} | {s['dropped'] / s['pool']:.3%} | "
                 f"{', '.join(f'{k} {v}' for k, v in s['dropped_reasons'].items())} |")
    L += ["", "Values containing a line break (multi-line PEM keys and a few names, streets, "
          "dates) are written on one line with each line-break run replaced by a space; the "
          "plan's grounding tier 3 (whitespace collapse) maps them back to the exact span. "
          f"Train values written this way: {card['splits']['train']['counts']['values_rendered_on_one_line']}.",
          "", "## Counts", ""]
    for split in ("train", "val"):
        c = card["splits"][split]["counts"]
        L += [f"### {split}", "", "| | " + " | ".join(LANGS) + " | all |", "|---|" + "---:|" * (len(LANGS) + 1)]
        L.append("| documents | " + " | ".join(str(c["docs"].get(g, 0)) for g in LANGS)
                 + f" | {sum(c['docs'].values())} |")
        L.append("| no-PII documents | " + " | ".join(
            f"{c['no_pii_docs'].get(g, 0)} ({c['no_pii_docs'].get(g, 0) / max(c['docs'].get(g, 1), 1):.1%})"
            for g in LANGS) + f" | {sum(c['no_pii_docs'].values())} |")
        for lab in ENTITY_TYPES:
            vals = [c["mentions"][g].get(lab, 0) for g in LANGS]
            L.append(f"| {lab} | " + " | ".join(map(str, vals)) + f" | {sum(vals)} |")
        L.append("")
    L += ["## Files", "", "| split | format | rows | sha256 |", "|---|---|---:|---|"]
    for split in ("train", "val"):
        for fmt, f in card["splits"][split]["files"].items():
            L.append(f"| {split} | {fmt} | {f['rows']} | `{f['sha256'][:16]}…` |")
    L += ["", "## Same ids in every format, round trip on the written files", "",
          "| split | format | same id list | failures |", "|---|---|---|---:|"]
    for split in ("train", "val"):
        for fmt, v in card["splits"][split]["verify"].items():
            L.append(f"| {split} | {fmt} | {'yes' if v['same_ids'] else '**NO**'} | "
                     f"{v['round_trip_or_content_failures']} |")
    if card.get("edges"):
        L += ["", "## Token edges (train)", "",
              "Entities with a start or end inside a token, and documents longer than one window.", "",
              "| tokenizer | window | entities | edge inside a token | docs over one window |",
              "|---|---:|---:|---:|---:|"]
        for name, e in card["edges"].items():
            win = XLMR_WINDOW[0] if name == "xlmr" else QWEN_WINDOW[0]
            L.append(f"| {name} | {win} | {e['entities']} | {e['edge_inside_token']} "
                     f"({e['edge_inside_token_share']:.2%}) | {e['docs_over_one_window']} "
                     f"({e['docs_over_one_window'] / e['docs']:.1%}) |")
    L += ["", "## Tools", "", "```", json.dumps(card["tools"], indent=2), "```", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(SRC))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--resample", action="store_true", help="draw new id lists")
    ap.add_argument("--formats", default=",".join(FORMATS))
    ap.add_argument("--no-edge-stats", action="store_true")
    args = ap.parse_args(argv)

    src, out = Path(args.src), Path(args.out)
    formats = [f for f in args.formats.split(",") if f]
    unknown = set(formats) - set(FORMATS)
    if unknown:
        raise SystemExit(f"unknown formats: {sorted(unknown)}")
    ids_dir, exp_dir = out / "ids", out / "export"
    card = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "seed": args.seed, "plan": "SLM test plan",
            "source": {"dir": (src.relative_to(ROOT) if src.is_relative_to(ROOT) else src).as_posix(),
                       "sha256": {}},
            "per_language": PER_LANG, "splits": {}}
    toks = load_tokenizers(formats)
    write_label_files(formats, exp_dir)
    all_ids = []
    for split in ("train", "val"):
        path = src / f"{split}.docs.jsonl"
        print(f"[{split}] hashing and round-tripping {path.name} ...", flush=True)
        card["source"]["sha256"][path.name] = sha256_file(path)
        pool, dropped = load_pool(path)
        ids_file = ids_dir / f"{split}_ids.txt"
        if ids_file.exists() and not args.resample:
            ids = ids_file.read_text(encoding="utf-8").split()
            missing = [i for i in ids if i not in pool]
            if missing:
                raise SystemExit(f"{len(missing)} ids in {ids_file} are not in the round-tripped pool, "
                                 f"e.g. {missing[:3]}: the corpus changed; rerun with --resample")
            print(f"  reusing {len(ids)} ids from {ids_file}")
        else:
            ids = sample(pool, PER_LANG[split], args.seed, split)
            ids_dir.mkdir(parents=True, exist_ok=True)
            ids_file.write_text("\n".join(ids) + "\n", encoding="utf-8", newline="\n")
            (ids_dir / f"roundtrip_dropped_{split}.txt").write_text(
                "".join(f"{i}\t{w}\n" for i, w in sorted(dropped.items())), encoding="utf-8", newline="\n")
            print(f"  sampled {len(ids)} ids -> {ids_file}")
        all_ids += ids
        order = list(ids)
        random.Random(f"{args.seed}:{split}:order").shuffle(order)
        records = [pool[i] for i in order]
        print(f"  writing {', '.join(formats)} ...", flush=True)
        files = export(split, records, formats, toks, exp_dir)
        ver = verify(split, ids, pool, files)
        card["splits"][split] = {
            "pool": len(pool) + len(dropped), "dropped": len(dropped),
            "dropped_reasons": dict(collections.Counter(dropped.values())),
            "ids_hash": ids_hash(ids), "counts": counts(records),
            "files": {fmt: {"path": p.relative_to(out).as_posix(), "rows": n, "sha256": sha256_file(p)}
                      for fmt, (p, n) in files.items()},
            "verify": ver}
        for fmt, v in ver.items():
            print(f"  {fmt:6} same ids: {v['same_ids']}  failures: {v['round_trip_or_content_failures']}")
        if split == "train" and toks and not args.no_edge_stats:
            print("  edge statistics ...", flush=True)
            card["edges"] = edge_stats(records, toks)
    card["ids_hash_all"] = ids_hash(all_ids)
    card["tools"] = tool_versions()
    (out / "data_card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False) + "\n",
                                        encoding="utf-8", newline="\n")
    (out / "DATA_CARD.md").write_text(render_card(card), encoding="utf-8", newline="\n")
    ok = all(v["same_ids"] and not v["round_trip_or_content_failures"]
             for s in card["splits"].values() for v in s["verify"].values())
    print(f"\n{'DONE' if ok else 'FAILED'}: data card -> {out / 'DATA_CARD.md'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
