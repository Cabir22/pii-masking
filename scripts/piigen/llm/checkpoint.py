"""Crash-safe checkpointing.

The requirement is that a run interrupted by Ctrl-C, a crash, a timeout or a
server restart resumes without regenerating completed work. Two files:

    <output>.jsonl        accepted examples, appended and fsync'd per batch
    <output>.state.json   counters, spec cursor, and the dedupe index

The output file is the source of truth. On resume the state file is used for
counters and the cursor, but accepted examples are re-read from the JSONL so
that a state file which is stale, corrupt or missing degrades gracefully into
"rebuild everything from the data" rather than losing work or duplicating it.

State is written via write-to-temp-then-rename, which is atomic on POSIX and
on Windows via os.replace, so a crash mid-write cannot leave a half-written
state file behind.
"""

from __future__ import annotations

import json
import logging
import os
import random
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger("piigen.llm")

STATE_SUFFIX = ".state.json"


def encode_rng_state(rng: random.Random) -> list:
    """`random.getstate()` -> JSON-safe list. See RunState.rng_state."""
    version, internal, gauss_next = rng.getstate()
    return [version, list(internal), gauss_next]


def decode_rng_state(encoded: list) -> tuple:
    """Inverse of encode_rng_state, in the shape random.setstate() expects."""
    version, internal, gauss_next = encoded
    return (version, tuple(internal), gauss_next)


@dataclass
class RunState:
    """Everything needed to continue a run exactly where it stopped."""

    version: int = 1
    model: str = ""
    seed: int = 0
    requested: int = 0
    accepted: int = 0
    attempted: int = 0
    next_spec_index: int = 0
    # 2026-08-26: `next_spec_index` was ALREADY understood to only number
    # documents for id/resume-collision purposes (see next_spec_index()'s
    # docstring in pipeline.py) -- but nothing else ever restored the
    # sampler's actual random state either. Every `--resume` re-seeds
    # `random.Random(seed)` fresh and starts drawing from the beginning of
    # that seed's sequence again, completely independent of how far a prior
    # invocation (on this machine or another) had already walked it. This
    # is invisible in the output -- the near-duplicate detector silently
    # absorbs the resulting collisions -- until two resumes' fresh restarts
    # overlap heavily enough to spike a batch's near-duplicate rate and trip
    # acceptance_rate's stop condition, which is what surfaced this.
    # `random.getstate()` returns (version, 625-int-tuple, gauss_next);
    # encoded as [int, list[int], float|None] for JSON, decoded back to the
    # tuple shape setstate() expects. None on a fresh run or an old
    # checkpoint written before this field existed -- falls back to the
    # previous (seed-only) behaviour, not an error.
    rng_state: list | None = None
    # RunMonitor.export_smoothing_state() -- see monitor.py's RunMonitor
    # for why this needs to survive a resume (bounded, not unlimited: see
    # RunMonitor._SMOOTHING_CEILING).
    rate_smoothing: dict | None = None
    # D-38: the run's --doc-types (None: every type). A resume must ask for
    # the same ones, or the rest of the run would draw other genres.
    doc_types: list | None = None
    rejections: dict = field(default_factory=dict)
    # Labels planned for an ACCEPTED document that never appeared in the text.
    # Not random: the model omits what is hardest to weave into prose, which is
    # systematically the rare labels augmentation exists to reinforce.
    dropped_labels: dict = field(default_factory=dict)
    label_counts: dict = field(default_factory=dict)
    lang_counts: dict = field(default_factory=dict)
    doc_type_counts: dict = field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    api_retries: int = 0
    elapsed_seconds: float = 0.0

    def merge_rejections(self, more: dict) -> None:
        for key, count in more.items():
            self.rejections[key] = self.rejections.get(key, 0) + count


def state_path_for(output: Path) -> Path:
    return output.with_name(output.name + STATE_SUFFIX)


def save_state(output: Path, state: RunState) -> None:
    """Atomically persist run state next to the output file."""
    path = state_path_for(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".state-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(asdict(state), handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_state(output: Path) -> RunState | None:
    path = state_path_for(output)
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("checkpoint unreadable (%s); rebuilding from output file", exc)
        return None
    known = {f for f in RunState.__dataclass_fields__}       # noqa: SLF001
    return RunState(**{k: v for k, v in data.items() if k in known})


def load_existing(output: Path) -> list[dict]:
    """Read already-accepted examples, tolerating a truncated final line.

    A crash during append can leave a partial JSON line. Dropping it is correct
    and safe -- the example was never counted as accepted in a saved state.
    """
    if not output.exists():
        return []
    rows: list[dict] = []
    with output.open(encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                log.warning("dropping malformed line %d in %s (likely a "
                            "partial write from an interrupted run)",
                            lineno, output)
                continue
            if isinstance(obj, dict) and obj.get("text"):
                rows.append(obj)
    return rows


class OutputWriter:
    """Append-only JSONL writer that flushes and fsyncs on demand.

    Durability is per batch rather than per record: fsync costs milliseconds
    and a batch is the unit we are willing to lose.
    """

    def __init__(self, path: Path, append: bool = True) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = path.open("a" if append else "w", encoding="utf-8")

    def write_many(self, rows: list[dict]) -> None:
        for row in rows:
            self._handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.commit()

    def commit(self) -> None:
        self._handle.flush()
        os.fsync(self._handle.fileno())

    def close(self) -> None:
        try:
            self.commit()
        finally:
            self._handle.close()

    def __enter__(self) -> "OutputWriter":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
