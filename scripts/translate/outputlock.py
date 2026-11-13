"""Exclusive lock on one translation output file, held for a whole run.

Language-neutral, and used by every runner: `run.py` (en/tr) and `run_ru.py`.

`--resume` reads the output ONCE to decide what is already done, then appends.
Two runs started against the same output therefore compute the same
"remaining" set and both translate all of it. On 2026-09-06 three concurrent
`--all-splits --resume` runs (concurrency 20 + 20 + 32) put 16,697 duplicate
copies into the Russian train split and pushed 72 concurrent requests at an
endpoint that falls over at 64. Nothing in the code could notice: each
process was individually correct.

This lived in the Russian runner only, which meant English and Turkish runs
had no such protection -- the same bug was available to them, just not yet
triggered. Extracted here in the 2026-09-07 restructure.
"""
from __future__ import annotations

import os
from pathlib import Path


def _rel(p: Path) -> str:
    try:
        return str(p.relative_to(Path.cwd()))
    except ValueError:
        return str(p)


class OutputBusy(RuntimeError):
    """Another run already owns this output file."""


class _OutputLock:
    """Exclusive lock on one output file, held for the life of the run.

    `--resume` reads the output ONCE to decide what is already done, then
    appends. Two runs started against the same output therefore compute the
    same "remaining" set and both translate all of it -- on 2026-09-06 three
    concurrent `--all-splits --resume` runs (concurrency 20 + 20 + 32) put
    16,697 duplicate copies into train and pushed 72 concurrent requests at
    an endpoint that fell over at 64. Nothing in the code could notice: each
    process was individually correct.

    O_EXCL creation is atomic, so exactly one process wins. A stale lock from
    a killed run is detected by checking whether its recorded pid is alive.
    """

    def __init__(self, target: Path) -> None:
        self.path = target.with_suffix(target.suffix + ".lock")
        self.fd: int | None = None

    def acquire(self) -> None:
        for _ in range(2):
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, f"{os.getpid()}\n".encode())
                return
            except FileExistsError:
                try:
                    pid = int(self.path.read_text().strip() or 0)
                except (OSError, ValueError):
                    pid = 0
                alive = False
                if pid:
                    try:
                        os.kill(pid, 0)
                        alive = True
                    except (ProcessLookupError, PermissionError):
                        alive = pid and False
                if alive:
                    raise OutputBusy(
                        f"{_rel(self.path)} is held by pid {pid}, which is still "
                        f"running. Two runs appending to one output duplicate "
                        f"every remaining document. Wait for it, or kill it and "
                        f"re-run with --resume (nothing is lost).")
                eprint(f"[lock] clearing stale lock from dead pid {pid}")
                self.path.unlink(missing_ok=True)
        raise OutputBusy(f"could not acquire {_rel(self.path)}")

    def release(self) -> None:
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        self.path.unlink(missing_ok=True)
