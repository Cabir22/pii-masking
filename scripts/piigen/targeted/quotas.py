"""Quotas for the targeted builder (P2-4).

The defaults live in `quotas.json` beside this file, so a patch round (P2-7)
changes a number in a reviewable file, not in code. `--quotas other.json`
overrides any subset: its values are merged over the defaults.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("quotas.json")


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _weights(section: dict) -> dict[str, float]:
    """The numeric entries of a section (`_comment` keys dropped)."""
    return {k: float(v) for k, v in section.items()
            if not k.startswith("_") and isinstance(v, (int, float))}


def load(path: str | Path | None = None) -> dict:
    quotas = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    if path is not None:
        quotas = _merge(quotas, json.loads(Path(path).read_text(encoding="utf-8")))
    check(quotas)
    return quotas


def check(q: dict) -> None:
    fam = _weights(q["families"])
    if abs(sum(fam.values()) - 1.0) > 1e-6:
        raise ValueError(f"family shares must sum to 1, got {sum(fam.values()):.4f}")
    groups = _weights(q["decoy_groups"])
    if abs(sum(groups.values()) - 1.0) > 1e-6:
        raise ValueError(f"decoy_groups must sum to 1, got {sum(groups.values()):.4f}")
    if not 0 < q["max_frame_share"] <= 1:
        raise ValueError("max_frame_share must be in (0, 1]")
    # D-52d: a later family can't shrink a protected contrast sub-family
    prot = q.get("protected", {}).get("contrast_subs", {})
    if prot:
        cw = {k: float(q["contrast"][k]) for k in ("token_key", "ipv6_mac", "licence_id", "key_pair")}
        for sub, floor in _weights(prot).items():
            got = fam["contrast"] * cw[sub] / sum(cw.values()) * 25000
            if got + 1e-6 < floor:
                raise ValueError(f"protected quota contrast.{sub}: {got:.0f} per 25k documents, "
                                 f"below its floor {floor:.0f} (D-52d)")
    if not 0 <= q["noise"]["case_target_share"] < q["targets"]["case_noise_max"]:
        raise ValueError("noise.case_target_share must stay below targets.case_noise_max "
                         "(P2-4b caps casing noise at 8% of entities)")


def families(q: dict) -> dict[str, float]:
    return _weights(q["families"])


def decoy_groups(q: dict) -> dict[str, float]:
    return _weights(q["decoy_groups"])
