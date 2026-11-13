"""v4.1 task 1: what the v4 cleaning pass (`v4_clean`, --v4-clean) changed in
or next to IPv4, IPv6, MAC and email values, per source file.

    python reports/v41_ip_inventory/clean_effects.py <file.jsonl> [...]

A change counts when its label is one of the four, or when its span touches an
email-, IP- or MAC-shaped token (a name labelled inside an email address
would split it). Counts and shapes only.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.v4_clean import clean_doc_detail  # noqa: E402

LABELS = {"IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS", "EMAIL"}
# an IPv6 needs `::`, a hex letter or 4+ groups, so a clock time (`12:30:45`,
# 3 digit groups) is not taken for one; a MAC needs 6 pairs
TOKENS = re.compile(r"[\w.+-]+@[\w.-]+\.\w+|(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])|"
                    r"(?=[0-9A-Fa-f:]*(?:::|[A-Fa-f]))[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){2,}|"
                    r"[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4}){3,}|(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}")


def main() -> int:
    for path in sys.argv[1:]:
        docs = changes = 0
        by = collections.Counter()
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            docs += 1
            res = clean_doc_detail(r)
            toks = [(m.start(), m.end()) for m in TOKENS.finditer(r["text"])]
            for c in res.changes:
                touch = c.start >= 0 and any(a < c.end and c.start < b for a, b in toks)
                if c.label in LABELS or touch:
                    changes += 1
                    by[(c.rule, c.action, c.label, "inside an IP/MAC/email token" if touch else "")] += 1
        print(f"== {Path(path).name}: {docs:,} documents, {changes:,} changes on or inside IP/MAC/email")
        for (rule, action, label, where), n in by.most_common(20):
            print(f"   {n:6,}  {rule} {action} {label} {where}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
