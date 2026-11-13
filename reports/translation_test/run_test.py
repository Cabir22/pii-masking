"""Run the translation harness unchanged on a sample, and record what it costs.

    python reports/translation_test/run_test.py --lang en|tr|ru --input sample.jsonl --out out.jsonl [--concurrency 8] [--dry-run]

EN/TR go through scripts/translate/run.py, RU through scripts/translate/run_ru.py.
Around every API call this asks the endpoint for its usage (`stream_options:
include_usage`; both harnesses skip the text-less usage chunk) and counts calls,
prompt/completion/reasoning tokens and wall time. Written to <out>.usage.json.
Aborted streams (the guard stops them early) report no usage; they are counted
as calls, and their tokens are missing from the totals.
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "translate"))

LOCK = threading.Lock()
USAGE = {"calls": 0, "calls_with_usage": 0, "prompt_tokens": 0, "completion_tokens": 0, "reasoning_tokens": 0}


def _add(usage) -> None:
    if usage is None:
        return
    u = usage if isinstance(usage, dict) else usage.model_dump()
    with LOCK:
        USAGE["calls_with_usage"] += 1
        USAGE["prompt_tokens"] += u.get("prompt_tokens") or 0
        USAGE["completion_tokens"] += u.get("completion_tokens") or 0
        det = u.get("completion_tokens_details") or {}
        USAGE["reasoning_tokens"] += (det.get("reasoning_tokens") or 0) if isinstance(det, dict) else 0


def _wrap(stream):
    for part in stream:
        u = getattr(part, "usage", None)
        if u:
            _add(u)
        yield part


def patch(lang: str) -> None:
    """Both runners call the OpenAI SDK (run_ru.py since 19 Oct; it used litellm,
    which dropped the no-thinking flag)."""
    from openai.resources.chat.completions import Completions

    orig_create = Completions.create

    def create(self, *a, **kw):
        if kw.get("stream"):
            kw.setdefault("stream_options", {"include_usage": True})
        with LOCK:
            USAGE["calls"] += 1
        r = orig_create(self, *a, **kw)
        return _wrap(r) if kw.get("stream") else r

    Completions.create = create


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["en", "tr", "ru"])
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run:
        patch(a.lang)
    t0 = time.time()
    if a.lang == "ru":
        import translate.run_ru as R
        argv = ["--input", a.input, "--out", a.out, "--all", "--concurrency", str(a.concurrency), "--diagnostics"]
        rc = R.main(argv + (["--dry-run"] if a.dry_run else []))
    else:
        import translate.run as R
        argv = ["--lang", a.lang, "--input", a.input, "--out", a.out, "--concurrency", str(a.concurrency)]
        rc = R.main(argv + (["--dry-run"] if a.dry_run else []))
    USAGE["seconds"] = round(time.time() - t0, 1)
    USAGE["concurrency"] = a.concurrency
    if not a.dry_run:
        Path(a.out + ".usage.json").write_text(json.dumps(USAGE, indent=1), encoding="utf-8")
    print("usage:", json.dumps(USAGE))
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
