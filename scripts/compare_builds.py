"""Where two builds of the same data first differ (D-49: Windows vs Mac).

    python scripts/compare_builds.py hashes BUILD.jsonl > BUILD.lines.tsv
    python scripts/compare_builds.py diff A.lines.tsv B.lines.tsv [--show A.jsonl B.jsonl]

`hashes` writes one line per record: index, id, family and the record's
content hash, made as in `scripts/hash_build.py` (without `_gen_version`, keys
sorted, no ASCII escaping). A file of 25,000 lines is about 2 MB, small enough
to send. `diff` reports the first record that differs, how many differ, and
which families they are in; with `--show` and both build files it prints the
two records' texts and the keys that differ at the first mismatch.
"""
from __future__ import annotations

import collections
import hashlib
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def record_hash(rec: dict) -> str:
    rec = {k: v for k, v in rec.items() if k != "_gen_version"}
    return hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def hashes(path: str) -> None:
    with open(path, "rb") as fh:
        for i, line in enumerate(fh):
            line = line.rstrip(b"\r\n")
            if not line.strip():
                continue
            rec = json.loads(line)
            spec = rec.get("_spec") or {}
            print(f"{i}\t{rec.get('id')}\t{spec.get('family', '')}\t{record_hash(rec)}")


def load(path: str) -> list[tuple[str, str, str, str]]:
    return [tuple(l.rstrip("\n").split("\t")) for l in open(path, encoding="utf-8")]


def diff(a_path: str, b_path: str, show: tuple[str, str] | None) -> int:
    a, b = load(a_path), load(b_path)
    print(f"records: {len(a):,} vs {len(b):,}")
    n = min(len(a), len(b))
    bad = [i for i in range(n) if a[i][3] != b[i][3]]
    ids = sum(a[i][1] != b[i][1] for i in range(n))
    print(f"records that differ: {len(bad):,} of {n:,}; ids that differ: {ids:,}")
    if not bad:
        print("IDENTICAL")
        return 0
    first = bad[0]
    print(f"first difference: record {first} (id {a[first][1]} vs {b[first][1]}), "
          f"family {a[first][2]} vs {b[first][2]}")
    fam = collections.Counter(a[i][2] for i in bad)
    tot = collections.Counter(r[2] for r in a)
    print("differing records by family (of that family):")
    for f, c in fam.most_common():
        print(f"   {f:14} {c:6,} of {tot[f]:,}")
    print(f"records identical before the first difference: {first:,}")
    if show:
        ra = [json.loads(l) for l in open(show[0], "rb")][first]
        rb = [json.loads(l) for l in open(show[1], "rb")][first]
        keys = sorted(k for k in set(ra) | set(rb) if k != "_gen_version" and ra.get(k) != rb.get(k))
        print(f"keys that differ: {keys}")
        for k in keys[:3]:
            print(f"--- {k}\n A: {json.dumps(ra.get(k), ensure_ascii=False)[:600]}\n B: {json.dumps(rb.get(k), ensure_ascii=False)[:600]}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "hashes":
        hashes(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "diff":
        show = tuple(sys.argv[sys.argv.index("--show") + 1:][:2]) if "--show" in sys.argv else None
        sys.exit(diff(sys.argv[2], sys.argv[3], show))
    else:
        sys.exit(__doc__)
