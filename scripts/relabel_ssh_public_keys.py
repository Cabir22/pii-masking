"""D-36a: OpenSSH public-key lines labelled PRIVATE_KEY become declared look-alikes.

WHY
---
`checksums.private_key_valid` used to accept `ssh-rsa AAAA...`,
`ssh-ed25519 ...`, `ssh-dss ...` and `ecdsa-sha2-...` lines, and
`values.private_key` minted them, so 1,572 public keys in v3's sources (974
in the old corpus's train share, 598 in LLM b1-b5) were labelled PRIVATE_KEY.
A public key is not secret, and D-34f teaches PEM `PUBLIC KEY` blocks as
look-alikes; neither the benchmark nor the probes label an `ssh-...` line.
D-36a: the validator rejects them, the generator stops minting them, and this
script turns the old labels into declared look-alikes, deterministically, as
D-17 and D-33a did. OpenSSH PRIVATE keys (`BEGIN OPENSSH PRIVATE KEY`) stay.

WHAT CHANGES
------------
* A PRIVATE_KEY entity whose text starts with an OpenSSH public-key type
  (`checksums.SSH_PUBLIC_KEY_PREFIXES`) leaves `entities` and is declared in
  `_decoys` at the same span, kind `public_key_ssh`, resembling PRIVATE_KEY.
* Except where the LLM wrapped the line in PEM armour that says PRIVATE KEY
  (`-----BEGIN RSA PRIVATE KEY----- ssh-rsa AAAA... -----END RSA PRIVATE
  KEY-----`; ~200 labels, only the inner line labelled). The text presents a
  private key, so the label grows to the whole block, which is a valid PEM
  PRIVATE_KEY, as the benchmark labels such blocks. With only half of that
  armour (a BEGIN or an END saying PRIVATE KEY), neither label is valid and
  the record is dropped. Armour that says PUBLIC KEY, SSH KEY or KEY is not a
  private key: the inner line becomes a look-alike like a bare one. Armour
  lines may sit in a quoted reply (`> `); armour the PEM rule rejects
  (`-----END PRIVATE  KEY-----`) drops the record like half armour.
* The gates also include the leak scan: an unlabelled PRIVATE KEY header
  next to a look-alike would be a leak.
* The change is kept only if the record then fails no gate it passed before
  (`relabel_standalone_dates.gate_state`: repeat mentions, resolver drift,
  span boundaries, anchors, `validate_example`). A record where a gate objects
  is dropped and counted: under the new validator its label is invalid.
* A record left with no entity is declared `_pii_free: true` (validate_corpus
  fails an undeclared empty record; the old corpus has no such field before);
  `_hard_negatives` / `_adversarials` count the new look-alikes (where they exist).

Text is never changed; an untouched record is written back byte for byte.

Run:
  python scripts/relabel_ssh_public_keys.py --file data/raw/sprint1_llm_b1.clean.jsonl --out new.jsonl
Without --in-place/--out it only reports.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.checksums import SSH_PUBLIC_KEY_PREFIXES, private_key_valid     # noqa: E402
from piigen.llm.quality import find_leaked_pii                            # noqa: E402
from piigen.validate import declared_decoy_spans                          # noqa: E402
from relabel_standalone_dates import gate_state, no_new_failure           # noqa: E402

KIND = "public_key_ssh"
# armour lines may sit inside a quoted reply (`> -----BEGIN ...`)
_BEGIN = re.compile(r"-----BEGIN ([A-Z ]*)-----[\s>]*$")
_END = re.compile(r"^[\s>]*-----END ([A-Z ]*)-----")


def ssh_entities(rec: dict) -> list[dict]:
    text = rec["text"]
    return [e for e in rec.get("entities") or []
            if e["label"] == "PRIVATE_KEY" and text[e["start"]:e["end"]].startswith(SSH_PUBLIC_KEY_PREFIXES)]


def armour(text: str, e: dict) -> tuple[str, tuple[int, int] | None]:
    """How the line is wrapped: ("private", block span) inside PEM armour
    saying PRIVATE KEY on both sides, ("half", None) with only one side of
    it, ("none", None) otherwise (bare, or armour that is not PRIVATE KEY)."""
    lo = max(0, e["start"] - 80)
    b = _BEGIN.search(text[lo:e["start"]])
    en = _END.match(text[e["end"]:e["end"] + 80])
    private = lambda m: m is not None and "PRIVATE KEY" in " ".join(m.group(1).split())   # noqa: E731
    if private(b) and private(en):
        return "private", (lo + b.start(), e["end"] + en.end())
    if private(b) or private(en):
        return "half", None
    return "none", None


def relabel(rec: dict) -> tuple[dict | None, Counter]:
    """(the record with its OpenSSH public-key labels relabelled, or None to
    drop it; what was done, by kind)."""
    text = rec["text"]
    hits = ssh_entities(rec)
    done = Counter()
    ents = rec.get("entities") or []
    looks, grown = [], []
    for e in hits:
        how, block = armour(text, e)
        if how == "half":
            done["half"] += 1
            return None, done
        if how == "private":
            if not private_key_valid(text[block[0]:block[1]]):
                # armour the PEM rule rejects (`-----END PRIVATE  KEY-----`)
                done["half"] += 1
                return None, done
            g = {**e, "start": block[0], "end": block[1]}
            if "text" in e:
                g["text"] = text[block[0]:block[1]]
            grown.append((e, g))
        else:
            looks.append(e)
    before = gate_state(rec, ents, declared_decoy_spans(rec)[0], True)
    gone = {(e["start"], e["end"]) for e in looks} | {(e["start"], e["end"]) for e, _ in grown}
    new = dict(rec)
    new["entities"] = sorted([e for e in ents if (e["start"], e["end"]) not in gone]
                             + [g for _, g in grown], key=lambda e: e["start"])
    if looks:
        new["_decoys"] = sorted((rec.get("_decoys") or [])
                                + [{"start": e["start"], "end": e["end"], "kind": KIND,
                                    "resembles": "PRIVATE_KEY"} for e in looks],
                                key=lambda d: d["start"])
    after = gate_state(new, new["entities"], declared_decoy_spans(new)[0], True)
    # and the leak gate: a PRIVATE KEY armour header left unlabelled is a leak
    before["leaks"] = len(find_leaked_pii(text, ents, decoy_spans=rec.get("_decoys") or []))
    after["leaks"] = len(find_leaked_pii(text, new["entities"], decoy_spans=new.get("_decoys") or []))
    if not no_new_failure(before, after):
        done["gate"] += 1
        return None, done
    if not new["entities"]:
        # declared, as validate_corpus requires of an empty record; the old
        # corpus's records carry no such field until now
        new["_pii_free"] = True
    for key in ("_hard_negatives", "_adversarials"):
        if isinstance(new.get(key), int):
            new[key] += len(looks)
    done["look-alike"] += len(looks)
    done["grown to the PEM block"] += len(grown)
    return new, done


def process(lines, stats: Counter, examples: list, n_examples: int):
    for line in lines:
        rec = json.loads(line)
        stats["documents in"] += 1
        hits = ssh_entities(rec)
        if hits:
            lang = rec.get("lang", "?")
            new, done = relabel(rec)
            if new is None:
                why = "half or malformed PRIVATE KEY armour" if done["half"] else "a gate objected"
                stats[f"documents dropped ({why})"] += 1
                stats[f"labels in dropped documents ({lang})"] += len(hits)
                continue
            stats["documents changed"] += 1
            stats[f"labels turned into look-alikes ({lang})"] += done["look-alike"]
            stats[f"labels grown to their PEM PRIVATE KEY block ({lang})"] += done["grown to the PEM block"]
            stats["documents now PII-free"] += bool(new.get("_pii_free")) and not rec.get("_pii_free")
            if len(examples) < n_examples:
                e = hits[0]
                examples.append(rec["text"][max(0, e["start"] - 40):e["end"] + 10].replace("\n", " "))
            line = json.dumps(new, ensure_ascii=False) + "\n"
        stats["documents out"] += 1
        yield line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path, required=True, help="one corpus file (.jsonl)")
    ap.add_argument("--out", type=Path, help="write the result here")
    ap.add_argument("--in-place", action="store_true", help="rewrite the file")
    ap.add_argument("--report", type=Path, help="write the counts as JSON")
    ap.add_argument("--examples", type=int, default=3)
    args = ap.parse_args(argv)

    stats, examples = Counter(), []
    dst = args.file if args.in_place else args.out
    tmp = dst.with_name(dst.name + ".tmp") if dst else None
    with args.file.open(encoding="utf-8") as fh, \
            (tmp.open("w", encoding="utf-8", newline="") if tmp else open(os.devnull, "w", encoding="utf-8")) as out:
        for line in process(fh, stats, examples, args.examples):
            out.write(line)
    if tmp:
        os.replace(tmp, dst)

    for k in sorted(stats, key=lambda k: (not k.startswith("documents"), k)):
        print(f"{k}: {stats[k]:,}")
    for ex in examples:
        print("  e.g.", ex)
    if args.report:
        args.report.write_text(json.dumps({"stats": stats, "examples": examples},
                                          ensure_ascii=False, indent=1), encoding="utf-8")
    if not (args.out or args.in_place):
        print("(report only -- pass --in-place or --out to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
