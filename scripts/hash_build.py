"""One way to compare two builds of the same data on different machines.

    python scripts/hash_build.py <file.jsonl> [...]

A record's `_gen_version` holds the git commit it was built from (plus
`+dirty`), so a file's raw SHA-256 changes with every commit even when the data
is identical. This prints, per file: the document count, the raw SHA-256, and a
content hash that ignores `_gen_version` and line endings: each record is
re-serialised without that key (sorted keys, UTF-8, no ASCII escaping) and
hashed line by line. Two builds of the same data at different commits, on
Windows or macOS, must give the same content hash (D-49 for why it matters).
"""
from __future__ import annotations

import hashlib
import json
import sys


def hashes(path: str) -> tuple[int, str, str]:
    raw, content, n = hashlib.sha256(), hashlib.sha256(), 0
    with open(path, "rb") as fh:
        for line in fh:
            raw.update(line)
            line = line.rstrip(b"\r\n")
            if not line.strip():
                continue
            rec = json.loads(line)
            rec.pop("_gen_version", None)
            content.update(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n")
            n += 1
    return n, raw.hexdigest(), content.hexdigest()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        n, raw, content = hashes(p)
        print(f"{p}\n  documents {n:,}\n  raw SHA-256      {raw}\n  content (no _gen_version) {content}")
