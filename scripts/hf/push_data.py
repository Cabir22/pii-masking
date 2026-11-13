"""Copy the repo's data/ folder to one private Hugging Face dataset, path for path.

    python scripts/hf/push_data.py            # dry run: what would be uploaded, sizes, nothing sent
    python scripts/hf/push_data.py --upload   # upload (resumable), then verify every file
    python scripts/hf/push_data.py --verify   # verify only (after an upload)

Why: the data leaves GitHub's Git LFS (it is what GitHub charges for); this keeps every file
under the same path, so `hf download your-hf-org/pii-masking-data --repo-type dataset --local-dir .`
in a fresh clone puts it back exactly where the scripts expect it.

Left out: builds already on Hugging Face (runb-az-v3, runb-az-v4) and temporary verification
builds (runb_v*mac*, runb_v*verify*, runb_v4_upload, data/raw/*_targeted.jsonl).
data/processed/runb holds runb-az-v2's documents; its data card there is v2's (from git),
not the v4 card the folder now carries in git.

Upload: hard links in data/processed/_hf_stage (no extra disk space), then
`upload_large_folder` (resumable: run it again if it stops). Verify: every file's SHA-256
(large files) or git blob id (small files) on the Hub against the local file.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
STAGE = DATA / "processed" / "_hf_stage"
REPO = "your-hf-org/pii-masking-data"
V2_CARD_COMMIT = "31dafca"          # P4-14: runb-az-v2's data card

SKIP_DIRS = {"_hf_stage", "runb_v4", "runb_v4_upload", "runb_v4mac", "runb_v4mac_az",
             "runb_v4verify", "runb_v4verify_az", "runb_v3verify", "runb_v3verify_az"}

README = """---
license: other
---
# pii-masking-data (private)

The `data/` folder of the PII masking project, path for path, moved here from GitHub's Git LFS.
In a clone of the code repository:

    hf download your-hf-org/pii-masking-data --repo-type dataset --local-dir .

puts every file back under `data/`. Training mixes that have their own dataset are not here:
`your-hf-org/runb-az-v3`, `your-hf-org/runb-az-v4`.

- `data/processed/merged_relabeled_swept_dated`: the old Azerbaijani corpus (D-17, D-18a) and its drop list
- `data/processed/{az,en,ru,tr,merged,merged_rebalanced}`: checkpoint 1's multilingual data
- `data/processed/runb`: runb-az-v2 documents (Run B), with v2's data card
- `data/processed/sprint1`: the first sprint mix
- `data/raw`: LLM batches b1-b6 (raw, clean, rejects, reports) and the earlier LLM augmentation
- `data/benchmark_v3`, `data/golden`, `data/calibration`, `data/testing_samples`, `data/repaired`, `data/name_extracts`, `data/slm`

The full list with sizes and SHA-256s: `MANIFEST.tsv`.
"""


def files() -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(DATA):
        rel = Path(dirpath).relative_to(DATA)
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            if f == ".gitkeep" or f == ".DS_Store" or f.startswith("._"):
                continue
            if rel == Path("raw") and f.endswith("_targeted.jsonl"):
                continue
            out.append(Path(dirpath) / f)
    return out


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def git_blob_id(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def is_pointer(p: Path) -> bool:
    with open(p, "rb") as fh:
        return fh.read(24) == b"version https://git-lfs"


def stage(fs: list[Path]) -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    for p in fs:
        dst = STAGE / "data" / p.relative_to(DATA)
        dst.parent.mkdir(parents=True, exist_ok=True)
        os.link(p, dst)
    card = STAGE / "data/processed/runb/DATA_CARD.md"
    if card.exists():
        card.unlink()
    v2 = subprocess.run(["git", "show", f"{V2_CARD_COMMIT}:data/processed/runb/DATA_CARD.md"],
                        cwd=ROOT, capture_output=True, check=True).stdout
    card.write_bytes(v2)
    (STAGE / "README.md").write_text(README, encoding="utf-8")
    with open(STAGE / "MANIFEST.tsv", "w", encoding="utf-8") as m:
        m.write("path\tbytes\tsha256\n")
        for p in fs:
            q = STAGE / "data" / p.relative_to(DATA)
            m.write(f"data/{p.relative_to(DATA)}\t{q.stat().st_size}\t{sha256(q)}\n")


def verify() -> int:
    from huggingface_hub import HfApi
    api = HfApi()
    local = sorted(q for q in STAGE.rglob("*") if q.is_file() and ".cache" not in q.parts)
    paths = [str(q.relative_to(STAGE)) for q in local]
    remote = {}
    for i in range(0, len(paths), 50):
        for info in api.get_paths_info(REPO, paths[i:i + 50], repo_type="dataset"):
            remote[info.path] = info
    bad = 0
    for q, path in zip(local, paths):
        info = remote.get(path)
        if info is None:
            print(f"MISSING  {path}"); bad += 1; continue
        if info.lfs is not None:
            ok = info.lfs.sha256 == sha256(q)
        else:
            ok = info.blob_id == git_blob_id(q)
        if not ok:
            print(f"DIFFERS  {path}"); bad += 1
    print(f"verified {len(paths) - bad} of {len(paths)} files" + ("" if not bad else f"; {bad} problems"))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    fs = files()
    pointers = [p for p in fs if is_pointer(p)]
    if pointers:
        sys.exit("git-lfs pointers, run `git lfs pull` first:\n  " + "\n  ".join(map(str, pointers)))
    if a.verify:
        return verify()
    total = sum(p.stat().st_size for p in fs)
    by_top: dict[str, int] = {}
    for p in fs:
        r = p.relative_to(DATA).parts
        k = "/".join(r[:2]) if r[0] == "processed" and len(r) > 2 else r[0]
        by_top[k] = by_top.get(k, 0) + p.stat().st_size
    for k, v in sorted(by_top.items(), key=lambda x: -x[1]):
        print(f"{v / 1e9:7.2f} GB  data/{k}")
    print(f"{total / 1e9:7.2f} GB  in {len(fs)} files -> {REPO} (private dataset)")
    if not a.upload:
        print("dry run: nothing uploaded. Upload with --upload")
        return 0
    from huggingface_hub import HfApi
    print("staging (hard links)…")
    stage(fs)
    api = HfApi()
    api.create_repo(REPO, repo_type="dataset", private=True, exist_ok=True)
    api.upload_large_folder(repo_id=REPO, folder_path=str(STAGE), repo_type="dataset", private=True)
    return verify()


if __name__ == "__main__":
    sys.exit(main())
