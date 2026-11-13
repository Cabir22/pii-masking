"""Build multilingual m2: m1's data (AZ v4.2 + EN/TR/RU) relabelled, plus the extra AZ batch and its
translation, with Azerbaijani train twice (D-64d, D-70, D-75, D-76a, D-78, D-81, D-82).

Two stages, both deterministic, so the Windows build and the Mac build must give the same
content hashes (D-49):

  python scripts/build_m2.py batch      # Wed/Thu: the AZ batch, split; its docs go to the team to translate
  python scripts/build_m2.py assemble   # Thu: everything, once the batch translation is pinned below

batch
  1. download  runb-az-v4.2 at its pinned commit (docs + windows) and check the windows
  2. generate  every item of BATCH with its preset and fixed seed -> batch_raw/v43_<item>.jsonl
               (the file name becomes the id prefix, D-64d (2): `v43_x_mac__targeted_az_000123`)
  3. validate  validate_corpus on every item: it must pass
  4. split     prepare_splits --no-tokenize --group-split template on the batch alone (D-64d (3)); then
               D-64d (4): a document whose template (_skeleton) already exists in v4.2 takes v4.2's split;
               a document whose text (normalised) is already in v4.2 is dropped; D-19c within the batch
  5. guard     the leakage guard on the batch (every barrier); a failing document is dropped, then it must
               be clean
  6. report    batch/BATCH_REPORT.md with the content hashes of batch/{split}.docs.jsonl

assemble
  1. download  v4.2's translation (pinned) and the batch translation (pinned: BATCH_TR_*), or
               --batch-tr-dir <folder> with {en,tr,ru}/{split}.docs.jsonl; check every input's hash
  2. relabel   D-70's list + m2's own list (scripts/relabel/m2_extra_list.tsv) with relabel.py: AZ docs and
               windows (re-windowed to identical input_ids), EN/TR/RU docs
  3. guard     the leakage guard on all EN/TR/RU documents; failing documents are dropped, then clean
  4. tokenize  EN/TR/RU (v4.2 + batch) and the AZ batch with prepare_splits --tokenize-only
               (xlm-roberta-large, the punctuation pre-tokenizer); v4.2's AZ windows are kept
  5. AZ x2     D-75: v4.2's AZ train windows a second time (ids `…__x2__wN`); the batch, val and test once
  6. merge     merge_languages --root data/processed/m2 (seeded shuffle)
  7. report    BUILD_REPORT.md: counts, relabel counts, dropped ids, content hashes

Needs transformers 4.57.x and tokenizers 0.22.x, `hf auth login` with your-hf-org access, Python 3.11.
Gentle on a laptop: OMP_NUM_THREADS / RAYON_NUM_THREADS default to 4 here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

for _v in ("OMP_NUM_THREADS", "RAYON_NUM_THREADS", "TOKENIZERS_PARALLELISM"):
    os.environ.setdefault(_v, "4" if _v != "TOKENIZERS_PARALLELISM" else "true")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
OUT = ROOT / "data" / "processed" / "m2"
IN = OUT / "_in"
LANGS = ("en", "tr", "ru")
SPLITS = ("train", "val", "test")
BASE_MODEL = "FacebookAI/xlm-roberta-large"
AZ_REPO, AZ_REV = "your-hf-org/runb-az-v4.2", "13959aa981bff58c187d0d1b384fc89daabb36b2"
TR_REPO, TR_REV = "your-hf-org/runb-translated-v4.2", "27785fa245406ad39628403fb92dc0deff708496"
# runb-az-v4.2 at 425f301, as in scripts/gpu/run_v42.sh and build_m1.py
AZ_WINDOWS = {"train.jsonl": "da0bb68b1a726d351085624fc033798ec551be2c53103c3197baf3f1ceb9c88d",
              "val.jsonl": "b61b7b11c1d78b6d585c4e0864814179a32f191bf9169916d993b0afdfe92bc2",
              "test.jsonl": "a9da61fcb2f6838870d90c34f0a4bc49b0a22a21bf15f75e7dd87721b3d81569"}
# The batch translation, pinned once uploaded; until then assemble needs --batch-tr-dir
BATCH_TR_REPO, BATCH_TR_REV = "your-hf-org/runb-translated-m2-batch", None
# The extra batch: item, preset, documents, seed. Whatever is merged
# by Fri 30 evening is in (D-83): tier 1 + tier 2 complete.
BATCH = [("x_age", "quotas_x_age.json", 400, 4301),
         ("x_buildingnum", "quotas_x_buildingnum.json", 600, 4302),
         ("x_card", "quotas_x_card.json", 300, 4303),
         ("x_glue", "quotas_x_glue.json", 420, 4304),
         ("x_ip6", "quotas_x_ip6.json", 400, 4305),
         ("x_mac", "quotas_x_mac.json", 350, 4306),
         ("x_tok", "quotas_x_tok.json", 200, 4307),
         ("x_c4", "quotas_x_c4.json", 300, 4308),
         ("x_a6a10", "quotas_x_a6a10.json", 320, 4309),
         ("x_noyr", "quotas_x_noyr.json", 150, 4310),
         ("x_words", "quotas_x_words.json", 200, 4311),
         ("x_dfrag", "quotas_x_dfrag.json", 160, 4312),
         ("x_d59", "quotas_x_d59.json", 500, 4313),
         ("x_aze", "quotas_x_aze.json", 135, 4314)]
PRESETS = ROOT / "scripts" / "piigen" / "targeted"
BATCH_SPLIT_SEED = 43
RELABEL_LISTS = [ROOT / "scripts" / "relabel" / "d70_list.tsv", ROOT / "scripts" / "relabel" / "m2_extra_list.tsv"]
FAILING = ("values", "sentences", "shadow_ngrams", "shadow_values")   # leakage_guard.Guard.clean()
WINDOW_ID = re.compile(r'^\{"id": "([^"]+)__w(\d+)"')


def say(msg: str) -> None:
    print(msg, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list) -> None:
    say("  $ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, cwd=ROOT)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def concat(dst: Path, *srcs: Path) -> None:
    """Byte concatenation with LF endings, one record per line."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("wb") as fout:
        for src in srcs:
            with src.open("rb") as fin:
                for line in fin:
                    if line.strip():
                        fout.write(line.rstrip(b"\r\n") + b"\n")


def check_versions() -> None:
    import tokenizers
    import transformers
    if not (transformers.__version__.startswith("4.57.") and tokenizers.__version__.startswith("0.22.")):
        sys.exit(f"need transformers 4.57.x and tokenizers 0.22.x, have {transformers.__version__} / "
                 f"{tokenizers.__version__}: pip install 'transformers==4.57.6' 'tokenizers==0.22.2'")


def download_az() -> None:
    from huggingface_hub import snapshot_download
    say(f"download {AZ_REPO}@{AZ_REV[:8]}")
    snapshot_download(AZ_REPO, repo_type="dataset", revision=AZ_REV, local_dir=IN / "az",
                      allow_patterns=["*.docs.jsonl", "train.jsonl", "val.jsonl", "test.jsonl",
                                      "labels.json", "DATA_CARD.md"])
    for name, want in AZ_WINDOWS.items():
        got = sha256(IN / "az" / name)
        say(f"  az/{name}: {got[:12]} {'OK' if got == want else 'MISMATCH'}")
        if got != want:
            sys.exit("the AZ windows are not the verified v4.2 build: stopping")


def guard(files: list[Path], name: str) -> list[str]:
    """The leakage guard on `files` (every barrier); returns the ids of the documents that fail it."""
    report = OUT / f"leakage_guard_{name}.json"
    rc = subprocess.run([sys.executable, "eval/leakage_guard.py", *map(str, files), "--json", str(report)],
                        cwd=ROOT, stdout=subprocess.DEVNULL).returncode
    hits = json.loads(report.read_text(encoding="utf-8"))["hits"]
    drop = sorted({h["doc"] for key in FAILING for h in hits.get(key, [])})
    if rc not in (0, 1) or (rc == 1) != bool(drop):
        sys.exit(f"leakage guard ({name}): unexpected result (exit {rc}, {len(drop)} failing documents)")
    return drop


def drop_docs(path: Path, drop: set[str]) -> int:
    rows = [r for r in read_jsonl(path) if r["id"] not in drop]
    write_jsonl(path, rows)
    return len(rows)


# ---------------------------------------------------------------- batch

def stage_batch(args) -> int:
    from build_sprint_mix import norm
    from prepare_splits import _skeleton
    if not args.skip_download:
        download_az()
    raw, bdir = OUT / "batch_raw", OUT / "batch"
    if raw.exists():
        shutil.rmtree(raw)
    raw.mkdir(parents=True)
    batch_items = [b for b in BATCH if not args.items or b[0] in args.items]
    if args.items and len(batch_items) != len(args.items):
        sys.exit(f"unknown items: {sorted(set(args.items) - {b[0] for b in BATCH})}")
    missing = [p for _, p, _, _ in batch_items if not (PRESETS / p).exists()]
    if missing:
        sys.exit(f"presets not merged yet: {missing}")
    say("2. generate")
    files = []
    for item, preset, n, seed in batch_items:
        f = raw / f"v43_{item}.jsonl"
        run([sys.executable, "scripts/build_targeted_corpus.py", "-n", n, "--seed", seed, "-o", f,
             "--quotas", PRESETS / preset])
        files.append(f)
    say("3. validate_corpus")
    for f in files:
        run([sys.executable, "scripts/validate_corpus.py", f, "--json", raw / f"{f.stem}.validation.json"])
    say("4. split the batch on its own (template groups), then D-64d (4) and D-19c")
    if bdir.exists():
        shutil.rmtree(bdir)
    run([sys.executable, "scripts/prepare_splits.py", *files, "--output-dir", bdir, "--no-tokenize",
         "--seed", BATCH_SPLIT_SEED, "--group-split", "template"])
    batch = {s: read_jsonl(bdir / f"{s}.docs.jsonl") for s in SPLITS}
    old_skel, old_text = {}, {}
    for s in SPLITS:
        with (IN / "az" / f"{s}.docs.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    d = json.loads(line)
                    old_skel.setdefault(_skeleton(d), s)
                    old_text[norm(d["text"])] = s
    moved, dup = Counter(), []
    new = {s: [] for s in SPLITS}
    for s in SPLITS:
        for d in batch[s]:
            if norm(d["text"]) in old_text:
                dup.append(d["id"])
                continue
            to = old_skel.get(_skeleton(d), s)
            moved[f"{s}->{to}"] += to != s
            new[to].append(d)
    seen: dict[str, set] = {}
    for s in SPLITS:
        for d in new[s]:
            seen.setdefault(norm(d["text"]), set()).add(s)
    for s in ("val", "test"):
        keep = []
        for d in new[s]:
            if len(seen[norm(d["text"])]) > 1:
                new["train"].append(d)
                moved[f"{s}->train (D-19c)"] += 1
            else:
                keep.append(d)
        new[s] = keep
    for s in SPLITS:
        write_jsonl(bdir / f"{s}.docs.jsonl", new[s])
    say(f"  inherited v4.2's split or moved: {dict(+moved) or 'none'}; already in v4.2 (dropped): {len(dup)}")
    say("5. leakage guard on the batch")
    drop = guard([bdir / f"{s}.docs.jsonl" for s in SPLITS], "batch_before_drop")
    for s in SPLITS:
        drop_docs(bdir / f"{s}.docs.jsonl", set(drop))
    if guard([bdir / f"{s}.docs.jsonl" for s in SPLITS], "batch"):
        sys.exit("the batch still fails the leakage guard after the drop: stopping")
    say(f"  dropped by the guard: {len(drop)}")
    # D-84: no unlabelled disguised e-mail may come in with the batch (m2 relabels the old ones to EMAIL)
    sys.path.insert(0, str(ROOT / "scripts" / "relabel"))
    from build_m2_extra_list import DISGUISED_EMAIL
    bad = [d["id"] for s in SPLITS for d in read_jsonl(bdir / f"{s}.docs.jsonl")
           for m in DISGUISED_EMAIL.finditer(d["text"])
           if not any(e["start"] <= m.start() and m.end() <= e["end"] and e["label"] == "EMAIL" for e in d["entities"])]
    if bad:
        sys.exit(f"D-84: {len(bad)} unlabelled disguised e-mail(s) in the batch, e.g. {bad[:3]}: stopping")
    from hash_build import hashes
    per_item = Counter()
    rows = []
    for s in SPLITS:
        for d in read_jsonl(bdir / f"{s}.docs.jsonl"):
            per_item[(d["id"].split("__")[0], s)] += 1
    for s in SPLITS:
        n, raw_sha, content = hashes(str(bdir / f"{s}.docs.jsonl"))
        rows.append(f"| `batch/{s}.docs.jsonl` | {n:,} | `{content[:16]}` | `{raw_sha[:16]}` |")
    lines = ["# m2 extra batch (AZ): build report", "",
             f"v4.2 `{AZ_REPO}@{AZ_REV[:8]}`; split seed {BATCH_SPLIT_SEED}, template groups (D-64d).", "",
             "| item | preset | -n | seed | train | val | test |", "|---|---|---|---|---|---|---|"]
    for item, preset, n, seed in batch_items:
        k = f"v43_{item}"
        lines.append(f"| {item} | `{preset}` | {n} | {seed} | " + " | ".join(str(per_item[(k, s)]) for s in SPLITS) + " |")
    lines += ["", f"Split moves (D-64d (4) template inherited from v4.2; D-19c): {dict(+moved) or 'none'}. "
              f"Already in v4.2 by normalised text, dropped: {len(dup)}"
              + (f" ({', '.join(f'`{x}`' for x in dup[:20])})" if dup else "") + ". "
              f"Dropped by the leakage guard: {len(drop)}" + (f" ({', '.join(f'`{x}`' for x in drop)})" if drop else "") + ".",
              "", "| file | documents | content hash | raw SHA-256 (LF) |", "|---|---|---|---|", *rows]
    (bdir / "BATCH_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    say("\n".join(lines))
    say(f"\nDONE: {bdir} (send {{train,val,test}}.docs.jsonl for translation)")
    return 0


# ---------------------------------------------------------------- assemble

def download_rest(args) -> Path:
    from huggingface_hub import snapshot_download
    say(f"download {TR_REPO}@{TR_REV[:8]}")
    snapshot_download(TR_REPO, repo_type="dataset", revision=TR_REV, local_dir=IN,
                      allow_patterns=[f"{lang}/{s}.docs.jsonl" for lang in LANGS for s in SPLITS])
    if args.batch_tr_dir:
        return args.batch_tr_dir.resolve()
    if not BATCH_TR_REV:
        sys.exit("the batch translation is not pinned yet (BATCH_TR_REV): pass --batch-tr-dir, or "
                 "--no-batch-translation for a dry run")
    snapshot_download(BATCH_TR_REPO, repo_type="dataset", revision=BATCH_TR_REV, local_dir=IN / "batch_tr",
                      allow_patterns=[f"{lang}/{s}.docs.jsonl" for lang in LANGS for s in SPLITS])
    return IN / "batch_tr"


def check_translation(folder: Path, source: dict[str, str], what: str) -> Counter:
    """Every row in its source's split, no source twice, lang right, spans inside the text."""
    counts = Counter()
    for lang in LANGS:
        seen, problems = set(), Counter()
        for s in SPLITS:
            for d in read_jsonl(folder / lang / f"{s}.docs.jsonl"):
                counts[(lang, s)] += 1
                sid, text = d.get("source_id"), d["text"]
                problems["source not in the same split"] += source.get(sid) != s
                problems["source id twice"] += sid in seen
                problems["lang field"] += d.get("lang") != lang
                seen.add(sid)
                for e in d.get("entities", []):
                    v = text[e["start"]:e["end"]] if 0 <= e["start"] < e["end"] <= len(text) else None
                    problems["span outside the text or with edge spaces"] += v is None or v != v.strip()
        problems = +problems
        say(f"  {what} {lang}: {sum(counts[(lang, s)] for s in SPLITS):,} documents; problems: {dict(problems) or 'none'}")
        if problems:
            sys.exit(f"{what} {lang}: problems: stopping")
    return counts


def relabel(lang: str, docs_dir: Path, out: Path, windows: bool) -> dict:
    lst = OUT / "relabel_list.tsv"                         # D-70's list + m2's own, one header
    with lst.open("w", encoding="utf-8", newline="\n") as f:
        for i, p in enumerate(RELABEL_LISTS):
            lines = p.read_text(encoding="utf-8").splitlines()
            f.write("\n".join(lines if i == 0 else lines[1:]) + "\n")
    cmd = [sys.executable, "scripts/relabel/relabel.py", "--list", lst, "--lang", lang, "--docs-dir", docs_dir,
           "--out-dir", out, "--base-model", BASE_MODEL] + (["--windows"] if windows else [])
    run(cmd)
    return json.loads((out / "relabel_report.json").read_text(encoding="utf-8"))


def double_az_train(src: Path, dst: Path) -> int:
    """D-75: the windows once as they are, then again with `__x2` before the window number."""
    n = 0
    with dst.open("ab") as fout, src.open("rb") as fin:
        for line in fin:
            if not line.strip():
                continue
            text = line.decode("utf-8")
            m = WINDOW_ID.match(text)
            if not m:
                sys.exit(f"unexpected window line in {src}: {text[:80]}")
            fout.write((f'{{"id": "{m.group(1)}__x2__w{m.group(2)}"' + text[m.end():]).rstrip("\r\n").encode("utf-8") + b"\n")
            n += 1
    return n


def stage_assemble(args) -> int:
    rel = OUT / "_rel"
    if not args.skip_download:
        download_az()
        btr = download_rest(args)
    else:
        btr = args.batch_tr_dir.resolve() if args.batch_tr_dir else (IN / "batch_tr" if BATCH_TR_REV else None)
    if btr is None and not args.no_batch_translation:
        sys.exit("no batch translation: pass --batch-tr-dir, or --no-batch-translation for a dry run")
    bdir = OUT / "batch"
    if not all((bdir / f"{s}.docs.jsonl").exists() for s in SPLITS):
        sys.exit("run the batch stage first")
    say("2. check the inputs")
    source = {}
    for s in SPLITS:
        for p in (IN / "az" / f"{s}.docs.jsonl", bdir / f"{s}.docs.jsonl"):
            with p.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        source[json.loads(line)["id"]] = s
    v42_counts = check_translation(IN, source, "v4.2 translation")
    batch_counts = check_translation(btr, source, "batch translation") if btr else Counter()
    say("3. relabel (D-70, D-76, D-76a, D-78, D-81, X-NOYR)")
    if rel.exists():
        shutil.rmtree(rel)
    reports = {"az": relabel("az", IN / "az", rel / "az", windows=True)}
    for lang in LANGS:
        reports[lang] = relabel(lang, IN / lang, rel / lang, windows=False)
    say("4. leakage guard on EN/TR/RU (v4.2 + batch translations)")
    for lang in ("az", *LANGS):
        for s in SPLITS:
            parts = [rel / lang / f"{s}.docs.jsonl"]
            if lang == "az":
                parts.append(bdir / f"{s}.docs.jsonl")
            elif btr:
                parts.append(btr / lang / f"{s}.docs.jsonl")
            concat(OUT / lang / f"{s}.docs.jsonl", *parts)
    tr_files = [OUT / lang / f"{s}.docs.jsonl" for lang in LANGS for s in SPLITS]
    drop = guard(tr_files, "translations_before_drop")
    for p in tr_files:
        drop_docs(p, set(drop))
    if guard(tr_files, "translations"):
        sys.exit("the translations still fail the leakage guard after the drop: stopping")
    say(f"  dropped: {len(drop)} {', '.join(drop)}")
    say("5. tokenize EN/TR/RU and the AZ batch")
    tok = OUT / "_tok_az_batch"
    if tok.exists():
        shutil.rmtree(tok)
    tok.mkdir(parents=True)
    for s in SPLITS:
        shutil.copyfile(bdir / f"{s}.docs.jsonl", tok / f"{s}.docs.jsonl")
    run([sys.executable, "scripts/prepare_splits.py", "--tokenize-only", *tr_files,
         *[tok / f"{s}.docs.jsonl" for s in SPLITS], "--base-model", BASE_MODEL])
    labels = (IN / "az" / "labels.json").read_bytes()
    for lang in ("az", *LANGS):
        (OUT / lang / "labels.json").write_bytes(labels)
    say("6. AZ windows: v4.2 relabelled + batch; train twice (D-75)")
    doubled = 0
    for s in SPLITS:
        dst = OUT / "az" / f"{s}.jsonl"
        concat(dst, rel / "az" / f"{s}.jsonl", tok / f"{s}.jsonl")
        if s == "train":
            doubled = double_az_train(rel / "az" / "train.jsonl", dst)
    say(f"  AZ train: v4.2's {doubled:,} windows appear twice")
    say("7. merge")
    run([sys.executable, "scripts/merge_languages.py", "--root", OUT, "--langs", "az", *LANGS,
         "--out", OUT / "merged"])
    report(reports, v42_counts, batch_counts, drop, doubled, btr)
    say(f"\nDONE: {OUT / 'merged'}")
    return 0


def report(reports, v42_counts, batch_counts, drop, doubled, btr) -> None:
    from hash_build import hashes
    rows = []
    for relp in [f"merged/{s}.{k}" for s in SPLITS for k in ("jsonl", "docs.jsonl")] + \
                [f"{lang}/{s}.jsonl" for lang in ("az", *LANGS) for s in SPLITS] + \
                [f"batch/{s}.docs.jsonl" for s in SPLITS]:
        n, raw, content = hashes(str(OUT / relp))
        rows.append(f"| `{relp}` | {n:,} | `{content[:16]}` | `{raw[:16]}` |")
    lists = ", ".join(f"`{p.name}` ({sha256(p)[:12]})" for p in RELABEL_LISTS)
    lines = ["# m2 build report", "",
             f"AZ `{AZ_REPO}@{AZ_REV[:8]}`; EN/TR/RU `{TR_REPO}@{TR_REV[:8]}`; batch translation "
             + (f"`{BATCH_TR_REPO}@{BATCH_TR_REV[:8]}`" if BATCH_TR_REV and btr == IN / "batch_tr"
                else f"`{btr}` (local)" if btr else "**none (dry run)**") + f"; tokenizer `{BASE_MODEL}`.", "",
             f"**Relabel** ({lists}):", "", "| lang | documents | removed | relabelled | added |", "|---|---|---|---|---|"]
    for lang, r in reports.items():
        lines.append(f"| {lang} | {r['documents']} | {r['removed']} | {r['relabelled']} | {r['added']} |")
    lines += ["", "| translated documents (before the guard) | train | val | test |", "|---|---|---|---|"]
    for lang in LANGS:
        lines.append(f"| {lang}: v4.2 / batch | " + " | ".join(
            f"{v42_counts[(lang, s)]:,} / {batch_counts[(lang, s)]:,}" for s in SPLITS) + " |")
    lines += ["", f"**Dropped by the leakage guard ({len(drop)}):** " + (", ".join(f"`{d}`" for d in drop) or "none") + ".",
              f"**AZ x2 (D-75):** v4.2's {doubled:,} AZ train windows appear twice (`…__x2__wN`); the batch, val and test once.",
              "", "Compare the **content hash** across machines (`scripts/hash_build.py`).", "",
              "| file | rows | content hash | raw SHA-256 (LF) |", "|---|---|---|---|", *rows]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    say("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("batch", "assemble"))
    ap.add_argument("--skip-download", action="store_true", help="reuse data/processed/m2/_in")
    ap.add_argument("--batch-tr-dir", type=Path, help="the batch translation: {en,tr,ru}/{split}.docs.jsonl")
    ap.add_argument("--no-batch-translation", action="store_true", help="dry run without the batch translation")
    ap.add_argument("--items", type=lambda v: v.split(","), help="batch: only these items (a trial, not the build)")
    args = ap.parse_args(argv)
    check_versions()
    return stage_batch(args) if args.stage == "batch" else stage_assemble(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
