"""D-36a acceptance check: OpenSSH public-key lines are look-alikes.

  * checksums.private_key_valid rejects `ssh-rsa`/`ssh-ed25519`/`ssh-dss`/
    `ecdsa-sha2-` lines and still accepts PEM private keys, OpenSSH ones too;
  * values.private_key never mints a public-key line;
  * the `public_key_ssh` look-alike is never a valid PRIVATE_KEY;
  * relabel_ssh_public_keys: a bare line becomes a declared look-alike at the
    same span; inside PRIVATE KEY armour the label grows to the PEM block;
    with half of that armour the record is dropped; other armour is a
    look-alike; a record without such a label is written back byte for byte.

    python scripts/test_relabel_ssh_public_keys.py
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.checksums import private_key_valid                           # noqa: E402
from piigen.negatives import ALL_DECOY_KINDS, make_decoy                  # noqa: E402
from piigen.validate import value_valid                                   # noqa: E402
from piigen.values import ValueFactory, ValuePool                         # noqa: E402
from relabel_ssh_public_keys import process, relabel                      # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg)


SSH = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5b6MMHitw2gsFFMaX3imN1QAchkvEwr4H7P4hMKg1F2H"
PEM = "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAAA\n-----END OPENSSH PRIVATE KEY-----"


def rec(text: str, value: str, **extra) -> dict:
    s = text.index(value)
    return {"id": "x", "lang": "az", "text": text,
            "entities": [{"start": s, "end": s + len(value), "label": "PRIVATE_KEY", "text": value}],
            **extra}


def test_validator_and_values() -> None:
    for line in (SSH, "ssh-rsa AAAAB3NzaC1yc2E" + "x" * 60, "ecdsa-sha2-nistp256 AAAAE2VjZHNh"):
        check(not private_key_valid(line), f"a public-key line is not a PRIVATE_KEY: {line[:20]}")
    check(private_key_valid(PEM), "an OpenSSH PRIVATE key block is still a PRIVATE_KEY")
    vf = ValueFactory(random.Random(3), ValuePool(state_path=None))
    keys = [vf.private_key() for _ in range(500)]
    check(all(k.startswith("-----BEGIN") and private_key_valid(k) for k in keys),
          "values.private_key mints PEM private keys only")
    k = ALL_DECOY_KINDS.get("public_key_ssh")
    rng = random.Random(5)
    vals = [make_decoy(k, rng) for _ in range(300)] if k else []
    check(k is not None and k.resembles == "PRIVATE_KEY"
          and all(v.startswith(("ssh-", "ecdsa-")) and not value_valid("PRIVATE_KEY", v)[0] for v in vals),
          "public_key_ssh: OpenSSH public-key lines, never a valid PRIVATE_KEY")


def test_relabel() -> None:
    bare = rec(f"Serverə giriş üçün açar: {SSH}. Sabah yenilənəcək.", SSH, _pii_free=False)
    new, done = relabel(bare)
    check(new is not None and not new["entities"] and new["_pii_free"] is True
          and new["_decoys"] == [{"start": bare["entities"][0]["start"], "end": bare["entities"][0]["end"],
                                  "kind": "public_key_ssh", "resembles": "PRIVATE_KEY"}]
          and new["text"] == bare["text"],
          "a bare line becomes a declared look-alike at the same span; text unchanged")
    text = f"Faylda bu açar var:\n-----BEGIN RSA PRIVATE KEY-----\n{SSH}\n-----END RSA PRIVATE KEY-----\nSilinməlidir."
    new, done = relabel(rec(text, SSH))
    block = text[text.index("-----BEGIN"):text.index("KEY-----\nSil") + 8]
    check(new is not None and len(new["entities"]) == 1 and new["entities"][0]["text"] == block
          and private_key_valid(block) and not new.get("_decoys"),
          "inside PRIVATE KEY armour the label grows to the whole PEM block")
    quoted = f"Cavab:\n> key: \"-----BEGIN RSA PRIVATE KEY-----\n> {SSH}\n> -----END RSA PRIVATE KEY-----\"\n> }}"
    new, _ = relabel(rec(quoted, SSH))
    check(new is not None and len(new["entities"]) == 1 and new["entities"][0]["text"].startswith("-----BEGIN")
          and new["entities"][0]["text"].endswith("-----END RSA PRIVATE KEY-----") and not new.get("_decoys"),
          "armour inside a quoted reply (`> `) is still armour: the label grows to the block")
    bad = f"Faylda:\n-----BEGIN PRIVATE KEY-----\n{SSH}\n-----END PRIVATE  KEY-----\nSilinməlidir."
    new, done = relabel(rec(bad, SSH))
    check(new is None and done["half"] == 1, "armour the PEM rule rejects: the record is dropped")
    half = f"Faylda:\n-----BEGIN PRIVATE KEY-----\n{SSH}\nSilinməlidir."
    new, done = relabel(rec(half, SSH))
    check(new is None and done["half"] == 1, "half PRIVATE KEY armour: the record is dropped")
    pub = f"Açar:\n-----BEGIN SSH PUBLIC KEY-----\n{SSH}\n-----END SSH PUBLIC KEY-----"
    new, _ = relabel(rec(pub, SSH))
    check(new is not None and not new["entities"] and new["_decoys"][0]["kind"] == "public_key_ssh",
          "PUBLIC KEY armour: the line is a look-alike")
    old = rec(f"Açar: {SSH}", SSH)                    # an old-corpus record: no _pii_free field
    new, _ = relabel(old)
    check(new is not None and new.get("_pii_free") is True,
          "a record left empty is declared PII-free even without the field before")
    plain = json.dumps(rec(f"Açar: {PEM}", PEM), ensure_ascii=False) + "\n"
    out = list(process([plain], Counter(), [], 0))
    check(out == [plain], "a record without a public-key label is written back byte for byte")


if __name__ == "__main__":
    for name, fn in (("validator and values", test_validator_and_values), ("relabel", test_relabel)):
        print(name)
        fn()
    print("\n" + "=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
