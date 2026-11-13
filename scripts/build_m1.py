"""Build multilingual m1: Azerbaijani v4.2 + its EN/TR/RU translation (D-67).

Everything comes from Hugging Face at pinned commits, so the Windows build
and the Mac build must give the same content hashes (D-49). Steps:

  1. download  runb-az-v4.2 (docs + windows)  and  runb-translated-v4.2 (docs)
  2. check     AZ windows = the verified v4.2 build; every translated row is in
               its source's split, no source id twice, spans inside the text
  3. guard     the leakage guard on EN/TR/RU (every barrier, the Turkish shadow
               set included); a translated document that fails it is dropped
               (the translation minted a value that collides with a held-out
               one), then the guard runs again and must be clean
  4. tokenize  EN/TR/RU with prepare_splits --tokenize-only (xlm-roberta-large,
               the punctuation pre-tokenizer); AZ keeps v4.2's verified windows
  5. merge     merge_languages --root data/processed/m1 (seeded shuffle)
  6. report    data/processed/m1/BUILD_REPORT.md: counts, dropped ids, content hashes

  python scripts/build_m1.py                 # about 30-60 min, ~6 GB on disk
  python scripts/build_m1.py --skip-download # reuse the downloaded files

Needs transformers 4.57.x and tokenizers 0.22.x (the windows depend on them),
`hf auth login` with your-hf-org access, and Python 3.11.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "m1"
LANGS = ("en", "tr", "ru")
SPLITS = ("train", "val", "test")
AZ_REPO, AZ_REV = "your-hf-org/runb-az-v4.2", "13959aa981bff58c187d0d1b384fc89daabb36b2"
TR_REPO, TR_REV = "your-hf-org/runb-translated-v4.2", "27785fa245406ad39628403fb92dc0deff708496"
# runb-az-v4.2 at 425f301, as in scripts/gpu/run_v42.sh (both machines identical)
AZ_WINDOWS = {"train.jsonl": "da0bb68b1a726d351085624fc033798ec551be2c53103c3197baf3f1ceb9c88d",
              "val.jsonl": "b61b7b11c1d78b6d585c4e0864814179a32f191bf9169916d993b0afdfe92bc2",
              "test.jsonl": "a9da61fcb2f6838870d90c34f0a4bc49b0a22a21bf15f75e7dd87721b3d81569"}
BASE_MODEL = "FacebookAI/xlm-roberta-large"
SRC = OUT / "_src"          # the translated documents as downloaded
FAILING = ("values", "sentences", "shadow_ngrams", "shadow_values")   # leakage_guard.Guard.clean()


def say(msg: str) -> None:
    print(msg, flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    say("  $ " + " ".join(str(c) for c in cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def check_versions() -> None:
    import tokenizers
    import transformers
    if not (transformers.__version__.startswith("4.57.") and tokenizers.__version__.startswith("0.22.")):
        sys.exit(f"need transformers 4.57.x and tokenizers 0.22.x, have {transformers.__version__} / "
                 f"{tokenizers.__version__}: pip install 'transformers==4.57.6' 'tokenizers==0.22.2'")


def download() -> None:
    from huggingface_hub import snapshot_download
    say("1. download")
    snapshot_download(AZ_REPO, repo_type="dataset", revision=AZ_REV, local_dir=OUT / "az",
                      allow_patterns=["*.docs.jsonl", "train.jsonl", "val.jsonl", "test.jsonl",
                                      "labels.json", "DATA_CARD.md"])
    snapshot_download(TR_REPO, repo_type="dataset", revision=TR_REV, local_dir=SRC,
                      allow_patterns=[f"{lang}/{split}.docs.jsonl" for lang in LANGS for split in SPLITS])


def check_inputs() -> dict:
    say("2. check the inputs")
    for name, want in AZ_WINDOWS.items():
        got = sha256(OUT / "az" / name)
        say(f"  az/{name}: {got[:12]} {'OK' if got == want else 'MISMATCH'}")
        if got != want:
            sys.exit("the AZ windows are not the verified v4.2 build: stopping")
    source = {}
    for split in SPLITS:
        with (OUT / "az" / f"{split}.docs.jsonl").open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    source[json.loads(line)["id"]] = split
    counts: dict = {"az": Counter(source.values())}
    for lang in LANGS:
        seen, problems, c = set(), Counter(), Counter()
        for split in SPLITS:
            with (SRC / lang / f"{split}.docs.jsonl").open(encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    d = json.loads(line)
                    c[split] += 1
                    sid, text = d.get("source_id"), d["text"]
                    if d.get("split") != split:
                        problems["split field differs from the file"] += 1
                    if source.get(sid) != split:
                        problems["source not in the same split"] += 1
                    if sid in seen:
                        problems["source id twice"] += 1
                    if d.get("lang") != lang:
                        problems["lang field"] += 1
                    seen.add(sid)
                    for e in d.get("entities", []):
                        v = text[e["start"]:e["end"]] if 0 <= e["start"] < e["end"] <= len(text) else None
                        if v is None or v != v.strip():
                            problems["span outside the text or with edge spaces"] += 1
        counts[lang] = c
        say(f"  {lang}: {dict(c)}  problems: {dict(problems) or 'none'}")
        if problems:
            sys.exit(f"{lang}: the translated data has problems: stopping")
    return counts


def guard_and_drop() -> list[str]:
    say("3. leakage guard on EN/TR/RU (all barriers)")
    files = [str(SRC / lang / f"{split}.docs.jsonl") for lang in LANGS for split in SPLITS]
    first = OUT / "leakage_guard_before_drop.json"
    rc = subprocess.run([sys.executable, "eval/leakage_guard.py", *files, "--json", str(first)],
                        cwd=ROOT, stdout=subprocess.DEVNULL).returncode
    report = json.loads(first.read_text(encoding="utf-8"))
    drop = sorted({h["doc"] for key in FAILING for h in report["hits"].get(key, [])})
    if rc not in (0, 1) or (rc == 1) != bool(drop):
        sys.exit(f"leakage guard: unexpected result (exit {rc}, {len(drop)} failing documents)")
    say(f"  {len(drop)} document(s) fail the guard and are dropped: {', '.join(drop) or 'none'}")
    for lang in LANGS:
        for split in SPLITS:
            src, dst = SRC / lang / f"{split}.docs.jsonl", OUT / lang / f"{split}.docs.jsonl"
            dst.parent.mkdir(parents=True, exist_ok=True)
            kept = 0
            with src.open("rb") as fin, dst.open("wb") as fout:
                for line in fin:
                    if line.strip() and json.loads(line)["id"] not in drop:
                        fout.write(line.rstrip(b"\r\n") + b"\n")
                        kept += 1
            say(f"  {lang}/{split}: {kept:,} documents")
    say("  the guard again, on what is kept: it must be clean")
    run([sys.executable, "eval/leakage_guard.py",
         *[str(OUT / lang / f"{split}.docs.jsonl") for lang in LANGS for split in SPLITS],
         "--json", str(OUT / "leakage_guard.json")])
    return drop


def tokenize() -> None:
    say("4. tokenize EN/TR/RU")
    files = [str(OUT / lang / f"{split}.docs.jsonl") for lang in LANGS for split in SPLITS]
    run([sys.executable, "scripts/prepare_splits.py", "--tokenize-only", *files,
         "--base-model", BASE_MODEL])
    for lang in LANGS:
        (OUT / lang / "labels.json").write_bytes((OUT / "az" / "labels.json").read_bytes())


def merge() -> None:
    say("5. merge")
    run([sys.executable, "scripts/merge_languages.py", "--root", str(OUT),
         "--langs", "az", *LANGS, "--out", str(OUT / "merged")])


def report(counts: dict, drop: list[str]) -> None:
    say("6. report")
    sys.path.insert(0, str(ROOT / "scripts"))
    from hash_build import hashes
    rows = []
    for rel in [f"merged/{s}.{k}" for s in SPLITS for k in ("jsonl", "docs.jsonl")] + \
               [f"{lang}/{s}.jsonl" for lang in LANGS for s in SPLITS]:
        n, raw, content = hashes(str(OUT / rel))
        rows.append(f"| `{rel}` | {n:,} | `{content[:16]}` | `{raw[:16]}` |")
    lines = ["# m1 build report", "",
             f"AZ: `{AZ_REPO}@{AZ_REV[:8]}`; EN/TR/RU: `{TR_REPO}@{TR_REV[:8]}`; tokenizer `{BASE_MODEL}`.", "",
             "| documents | train | val | test |", "|---|---|---|---|"]
    for lang in ("az", *LANGS):
        c = counts[lang]
        lines.append(f"| {lang} | {c['train']:,} | {c['val']:,} | {c['test']:,} |")
    lines += ["", "Documents per language are as translated (before the guard). **Dropped by the "
              f"leakage guard ({len(drop)}):** " + (", ".join(f"`{d}`" for d in drop) or "none") + "."]
    lines += ["", "Compare the **content hash** across machines (`scripts/hash_build.py`: it ignores "
              "`_gen_version` and line endings).", "",
              "| file | rows | content hash | raw SHA-256 (LF) |", "|---|---|---|---|", *rows]
    (OUT / "BUILD_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    say("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args(argv)
    check_versions()
    if not args.skip_download:
        download()
    counts = check_inputs()
    drop = guard_and_drop()
    tokenize()
    merge()
    report(counts, drop)
    say(f"\nDONE: {OUT / 'merged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
