"""Download the project's data from Hugging Face into this checkout (the repository has no Git LFS;
the data left GitHub in October 2026, D-73). Works the same on Windows, macOS and Linux: it uses the
huggingface_hub library directly (no `hf` command needed) and never overwrites a file git tracks.

  python scripts/hf/fetch_data.py                                # all of data/ (about 12 GB)
  python scripts/hf/fetch_data.py data/benchmark_v3 data/golden  # only these folders or files
  python scripts/hf/fetch_data.py --builds                       # also the training mixes runb-az-v3 / -v4

Needs `pip install -U "huggingface_hub>=0.30"` and a login with your-hf-org access (`hf auth login`, or
`python -c "from huggingface_hub import login; login()"`). Files land at the paths the scripts expect.
Re-running fetches only what changed. Every downloaded file is checked against MANIFEST.tsv (SHA-256).
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = "your-hf-org/pii-masking-data"


def tracked() -> set[str]:
    """Files git tracks under data/ (READMEs, schema): the repository's copy wins, never the download."""
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "data"], capture_output=True, text=True, check=True)
        return set(out.stdout.split())
    except Exception:
        return set()


def check(prefixes: list[str]) -> int:
    bad = ok = 0
    skip = tracked()
    for line in (ROOT / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        path, size, sha = line.split("\t")
        if prefixes and not any(path == p or path.startswith(p + "/") for p in prefixes):
            continue
        if path in skip:
            continue
        f = ROOT / path
        if not f.exists() or f.stat().st_size != int(size):
            print("MISSING or wrong size:", path)
            bad += 1
            continue
        h = hashlib.sha256()
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 24), b""):
                h.update(chunk)
        if h.hexdigest() != sha:
            print("CHECKSUM differs:", path)
            bad += 1
        else:
            ok += 1
    print(f"checked {ok + bad} files: {ok} OK" + (f", {bad} problems" if bad else ""))
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="folders or files under data/ (default: all of data/)")
    ap.add_argument("--builds", action="store_true", help="also download your-hf-org/runb-az-v3 and -v4")
    a = ap.parse_args(argv)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit('huggingface_hub not installed: pip install -U "huggingface_hub>=0.30"')
    prefixes = [p.rstrip("/\\").replace("\\", "/") for p in a.paths]
    allow = ["MANIFEST.tsv"] + [x for p in prefixes for x in (p, f"{p}/*")] if prefixes else None
    ignore = ["README.md", ".gitattributes", *sorted(tracked())]
    print(f"downloading {REPO} -> {ROOT} {' '.join(prefixes) or '(all of data/)'}")
    snapshot_download(REPO, repo_type="dataset", local_dir=ROOT, allow_patterns=allow, ignore_patterns=ignore)
    rc = check(prefixes)
    if a.builds:
        for v in ("v3", "v4"):
            snapshot_download(f"your-hf-org/runb-az-{v}", repo_type="dataset", local_dir=ROOT / "data/processed" / f"runb_{v}",
                              ignore_patterns=["README.md", ".gitattributes"])
    print("done")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
