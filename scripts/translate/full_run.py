"""The full translation of the Azerbaijani splits into EN / TR / RU (D-54a, D-64c).

    python scripts/translate/full_run.py --input-dir <runb-az-v4.2 dir> --out-dir <dir>
        [--splits train,val,test] [--concurrency 40] [--langs en,tr,ru] [--upload your-hf-org/<dataset>]

D-64c: each source split is translated on its own, in turn (`--splits`). For
each split, scripts/translate/run.py (EN, TR) and run_ru.py (RU) run side by
side, the total concurrency split between them, each with `--resume` and
`--split-name <split>`, so every row keeps its `source_id` and carries its
source split. A crash, a reboot or Ctrl-C loses nothing: run the same command
again and every runner skips what its output already holds.

Reads <input-dir>/<split>.docs.jsonl. Writes <out-dir>/<lang>/<split>.docs.jsonl,
the repair queues, the runners' logs (<lang>/<split>.run.log), and
<out-dir>/MANIFEST.json (each input's sha256, the git commit the code came
from, start/end times, rows per language and split). After the last split it
runs scripts/translate/check_splits.py; nothing is uploaded unless that
passes. On Windows the machine is kept awake while this process runs
(SetThreadExecutionState; nothing is changed in the system's power settings,
and it ends with the process).

With `--upload`, the out-dir goes to that Hugging Face dataset (private) when
every split has finished and the check has passed; uploading again later
replaces the files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLITS = ("train", "val", "test")


def _keep_awake() -> None:
    if os.name == "nt":
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def _rows(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def split_concurrency(total: int, langs: list[str]) -> dict[str, int]:
    """Russian's prompt is about three times longer, so it gets the remainder."""
    base = total // len(langs)
    out = {lang: base for lang in langs}
    out[langs[-1]] += total - base * len(langs)
    return out


def command(lang: str, inp: Path, out: Path, conc: int, split: str) -> list[str]:
    if lang == "ru":
        return [sys.executable, str(ROOT / "scripts/translate/run_ru.py"), "--input", str(inp),
                "--out", str(out), "--all", "--concurrency", str(conc), "--resume", "--diagnostics",
                "--split-name", split]
    return [sys.executable, str(ROOT / "scripts/translate/run.py"), "--lang", lang, "--input", str(inp),
            "--out", str(out), "--concurrency", str(conc), "--resume", "--split-name", split]


def run_split(split: str, inp: Path, out_dir: Path, langs: list[str], conc: dict[str, int],
              commit: str) -> dict[str, int]:
    """Translate one split into every language, side by side; exit codes per language."""
    procs = {}
    for lang in langs:
        d = out_dir / lang
        d.mkdir(exist_ok=True)
        log = open(d / f"{split}.run.log", "a", encoding="utf-8")
        log.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} start {split} (commit {commit[:9]})\n")
        log.flush()
        procs[lang] = (subprocess.Popen(command(lang, inp, d / f"{split}.docs.jsonl", conc[lang], split),
                                        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                        env=dict(os.environ, PYTHONIOENCODING="utf-8")), log)
        print(f"{split}/{lang}: started, concurrency {conc[lang]}, log {d / f'{split}.run.log'}", flush=True)
    t0 = time.time()
    while any(p.poll() is None for p, _ in procs.values()):
        time.sleep(int(os.environ.get("FULL_RUN_POLL", "300")))
        done = {lang: _rows(out_dir / lang / f"{split}.docs.jsonl") for lang in langs}
        print(f"{split} {(time.time() - t0) / 3600:.1f} h: " + ", ".join(f"{k} {v:,}" for k, v in done.items()),
              flush=True)
    for _, log in procs.values():
        log.close()
    return {lang: p.returncode for lang, (p, _) in procs.items()}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", required=True, type=Path,
                    help="the Azerbaijani source: <dir>/{train,val,test}.docs.jsonl (runb-az-v4.2)")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--splits", default=",".join(SPLITS), help="in this order, one after another")
    ap.add_argument("--concurrency", type=int, default=40, help="total, split across the languages")
    ap.add_argument("--langs", default="en,tr,ru")
    ap.add_argument("--upload", help="Hugging Face dataset, e.g. your-hf-org/runb-translated-v4.2")
    a = ap.parse_args()
    if not os.environ.get("COMPANY_API_KEY"):
        sys.exit("COMPANY_API_KEY is not set")
    langs, splits = a.langs.split(","), a.splits.split(",")
    if not set(splits) <= set(SPLITS):
        sys.exit(f"--splits must be within {SPLITS}")
    inputs = {s: a.input_dir / f"{s}.docs.jsonl" for s in splits}
    missing = [str(p) for p in inputs.values() if not p.exists()]
    if missing:
        sys.exit(f"missing input: {missing}")
    if _git("status", "--porcelain", "--untracked-files=no"):
        print("warning: the working tree has uncommitted changes; MANIFEST records HEAD only")
    a.out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = a.out_dir / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    commit = _git("rev-parse", "HEAD")
    manifest.setdefault("runs", []).append({
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "commit": commit,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"), "splits": splits,
    })
    manifest["input_dir"] = str(a.input_dir)
    manifest.setdefault("inputs", {})
    for s, p in inputs.items():
        if s not in manifest["inputs"]:
            manifest["inputs"][s] = {"file": p.name, "sha256": _sha256(p), "docs": _rows(p)}
    manifest.update({"langs": langs, "concurrency": split_concurrency(a.concurrency, langs)})
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    _keep_awake()

    codes: dict[str, dict[str, int]] = {}
    for s in splits:
        codes[s] = run_split(s, inputs[s], a.out_dir, langs, manifest["concurrency"], commit)
        manifest["runs"][-1].setdefault("exit_codes", {})[s] = codes[s]
        manifest["written"] = {lang: {sp: _rows(a.out_dir / lang / f"{sp}.docs.jsonl") for sp in SPLITS
                                      if (a.out_dir / lang / f"{sp}.docs.jsonl").exists()} for lang in langs}
        manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
        print(f"{s} done: {manifest['written']}; exit codes {codes[s]}", flush=True)
        if any(codes[s].values()):
            print("a runner failed; run the same command again to resume")
            return 1

    manifest["runs"][-1]["ended"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    # D-64c: every row's split is its source's, no source_id in two splits
    check = subprocess.run([sys.executable, str(ROOT / "scripts/translate/check_splits.py"),
                            "--source-dir", str(a.input_dir), "--out-dir", str(a.out_dir), "--langs", a.langs,
                            "--json", str(a.out_dir / "split_check.json")],
                           cwd=ROOT, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    manifest["split_check"] = "pass" if check.returncode == 0 else "FAIL"
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    if check.returncode:
        print("the split check failed (split_check.json): nothing uploaded")
        return 1
    if a.upload:
        from huggingface_hub import HfApi
        api = HfApi()
        api.create_repo(a.upload, repo_type="dataset", private=True, exist_ok=True)
        api.upload_folder(repo_id=a.upload, repo_type="dataset", folder_path=str(a.out_dir),
                          commit_message=f"Translation of {a.input_dir.name} ({', '.join(splits)}; "
                                         f"{', '.join(langs)}), commit {commit[:9]}",
                          ignore_patterns=["*.lock", "*.tmp"])
        print(f"uploaded to https://huggingface.co/datasets/{a.upload}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
