"""Build eval/leakage_guard_shadow.json.gz from the private shadow set.

    python eval/build_shadow_hashes.py [--shadow-dir ~/pii-eval-private]
                                       [--files shadow_dev.jsonl sealed.jsonl]
                                       [--out eval/leakage_guard_shadow.json.gz]
    python eval/build_shadow_hashes.py --empty      # the committed placeholder

The shadow texts stay in ~/pii-eval-private/ (rule A2.5). This writes only:
  - SHA-1 of every word 8-gram of every shadow text, normalised exactly as
    eval/leakage_guard.py does (lower-case, `\\w+` word runs);
  - for every distinctive, high-entropy gold value (the same rules as
    check 1: not vocabulary, not a small-universe label such as DATE, TIME
    or ZIPCODE, >= 28 bits), SHA-1 of the value, SHA-1
    of its longest word run (the scan key) and that run's offset and the
    value's length, so the guard can re-hash the exact candidate substring.
No text, value or 8-gram is written in the clear. The source is identified
only by file count, document count and the SHA-256 of the input files.

Names, places and other vocabulary, and low-entropy values (dates, times,
ages, short names...), are never hashed as values: hashing them would stop
every training text that mentions a common name or date. A set that has
only such values (the Turkish real-text set: names, places, dates) gets 0
value hashes and is protected by its 8-grams; `values_skipped` says why.
The same builder makes the other barriers (D-46):
    --shadow-dir ~/pii-eval-private/real_text_tr --files real_text.jsonl \
    --out eval/leakage_guard_barrier_real_tr.json.gz
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from leakage_guard import (N, SHADOW_FORMAT, SHADOW_HASHES, anchor_of,  # noqa: E402
                           is_distinctive, is_low_entropy, ngrams, sha1, words)

# Value hashes are decided by LABEL, not by how the value looks: only these code-like labels are ever
# value-hashed (then still only when distinctive and not low-entropy). Names, places, dates, times, ages,
# building numbers and postcodes never are, whatever their casing: an all-capitals place name in a
# letterhead looks like a code to is_vocabulary() and once blocked a training build (D-48).
VALUE_LABELS = frozenset({"TELEPHONENUM", "EMAIL", "URL", "AZ_FIN", "AZ_ID_CARD_NUMBER", "AZ_PASSPORT_NUMBER",
                          "AZ_VOEN", "AZ_DRIVER_LICENSE_NUMBER", "PAYMENT_CARD_NUMBER", "IBAN", "CARD_SECURITY_CODE",
                          "ICCID", "IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS", "API_KEY", "ACCESS_TOKEN",
                          "PRIVATE_KEY"})

DEFAULT_DIR = Path.home() / "pii-eval-private"
DEFAULT_FILES = ["shadow_dev.jsonl", "sealed.jsonl"]


def build(paths: list[Path]) -> dict:
    grams: set[str] = set()
    values: dict[str, dict] = {}
    skipped = {"name, place or date label": 0, "vocabulary or too short": 0, "low-entropy label or value": 0}
    h = hashlib.sha256()
    docs = 0
    for p in paths:
        h.update(p.read_bytes())
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                docs += 1
                text = r["text"]
                grams.update(sha1(g) for g in ngrams(words(text)))
                for e in r.get("entities", []):
                    v = text[e["start"]:e["end"]]
                    a = anchor_of(v)
                    # Same rule as check 1: low-entropy values (every date,
                    # postcode, time...) occur in any corpus by chance, so
                    # hashing them would block every training run.
                    if e["label"] not in VALUE_LABELS:
                        skipped["name, place or date label"] += 1
                    elif is_low_entropy(v, [e["label"]]):
                        skipped["low-entropy label or value"] += 1
                    elif not (a and is_distinctive(v)):
                        skipped["vocabulary or too short"] += 1
                    else:
                        values[sha1(v)] = {"sha1": sha1(v), "anchor_sha1": sha1(a[0]),
                                           "offset": a[1], "length": len(v)}
    return {"format": SHADOW_FORMAT, "n": N,
            "normalisation": "lower() minus U+0307, \\w+ word runs, 8-grams joined by one space",
            "value_rule": "label in VALUE_LABELS (codes only, never names, places or dates), distinctive and not low-entropy",
            "built_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": {"files": len(paths), "documents": docs,
                       "sha256": h.hexdigest() if paths else None},
            "values_skipped": skipped,
            "ngram_sha1": sorted(grams), "values": sorted(values.values(), key=lambda x: x["sha1"])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shadow-dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--files", nargs="+", default=DEFAULT_FILES)
    ap.add_argument("--out", type=Path, default=SHADOW_HASHES)
    ap.add_argument("--empty", action="store_true",
                    help="write the placeholder (no shadow set yet, P3-2)")
    args = ap.parse_args(argv)

    if args.empty:
        paths = []
    else:
        paths = [args.shadow_dir.expanduser() / f for f in args.files]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            raise SystemExit(f"missing shadow file(s): {missing}")
    data = build(paths)
    if args.empty:
        data["source"] = {"files": 0, "documents": 0, "sha256": None,
                          "note": "placeholder: regenerate from the real shadow set after P3-2"}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True)
    print(f"wrote {args.out}: {len(data['ngram_sha1'])} 8-gram hashes, "
          f"{len(data['values'])} value hashes from {data['source']['documents']} documents"
          + (f"; values not hashed: {data['values_skipped']}" if data.get("values_skipped") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
