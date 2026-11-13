"""Which generator code produced a record: the C2 field `_gen_version`.

Stamped ONCE, when this module is first imported, not per record. A
long-running generation process keeps the code it imported in memory; after
a merge, the checkout on disk moves on while the process still runs the old
code, and nothing in the old records said so. Reading the SHA at import time
records the code actually running, so a record written by a stale process
carries the stale SHA and can be found and regenerated.

`+dirty` is appended when the generator sources had uncommitted changes at
import time, because then the SHA alone does not identify the code.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR_PATHS = ("scripts/piigen", "scripts/llm_augment_data.py",
                    "scripts/build_targeted_corpus.py")


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(_ROOT), *args], capture_output=True,
                          text=True, timeout=10, check=True).stdout.strip()


def _read_version() -> str:
    try:
        sha = _git("rev-parse", "--short=12", "HEAD")
        dirty = _git("status", "--porcelain", "--untracked-files=no", "--",
                     *_GENERATOR_PATHS)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return f"{sha}+dirty" if dirty else sha


GEN_VERSION: str = _read_version()
