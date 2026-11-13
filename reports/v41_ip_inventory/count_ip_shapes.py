"""v4.1 task 1 (the team for): IPv4, IPv6, MAC and email in the
targeted data, v3 against v4 -- real values by format, look-alikes by kind,
both by family and by context.

    python reports/v41_ip_inventory/count_ip_shapes.py v3=<v3 targeted.jsonl> v4=<v4 targeted.jsonl> \
        [--json out.json] [--md out.md]

The two files are 25,000-document targeted builds (`-n 25000 --seed
20261001`) at the commits `runb-az-v3` (39dc5be, Python 3.11 as the Mac build)
and `runb-az-v4` (095f69f) were built from. Counts only; generated values
appear as format classes, never as values.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

LABELS = ("IPV4_ADDRESS", "IPV6_ADDRESS", "MAC_ADDRESS", "EMAIL")
SHORT = {"IPV4_ADDRESS": "IPv4", "IPV6_ADDRESS": "IPv6", "MAC_ADDRESS": "MAC", "EMAIL": "email"}


# -- format classes ---------------------------------------------------------
def ipv6_form(v: str) -> str:
    if v.lower().startswith("::ffff:"):
        form = "IPv4-embedded ::ffff:"
    elif "::" not in v:
        form = "full 8 groups" + (" (leading zeros)" if all(len(g) == 4 for g in v.split(":")) else "")
    elif v.startswith("::"):
        form = ":: at start"
    elif v.endswith("::1"):
        form = "<prefix>::1"
    elif v.endswith("::"):
        form = ":: at end"
    else:
        form = ":: in the middle"
    letters = [c for c in v if c.isalpha()]
    case = ("no letters" if not letters else "upper" if all(c.isupper() for c in letters)
            else "lower" if all(c.islower() for c in letters) else "mixed")
    return f"{form} / {case}"


def ipv4_form(v: str) -> str:
    o = v.split(".")
    if len(o) != 4:
        return f"{len(o)} parts"
    a, b = int(o[0]), int(o[1])
    if v.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
        return "documentation range"
    if a == 10 or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31):
        return "private"
    if a == 100 and 64 <= b <= 127:
        return "carrier-grade NAT"
    return "public"


def mac_form(v: str) -> str:
    sep = "dotted aabb.ccdd.eeff" if v.count(".") == 2 else "dash" if "-" in v else "colon" if ":" in v else "other"
    letters = [c for c in v if c.isalpha()]
    case = ("upper" if all(c.isupper() for c in letters) else "lower" if all(c.islower() for c in letters)
            else "mixed") if letters else "no letters"
    return f"{sep} / {case}"


def email_form(v: str) -> str:
    local = v.split("@", 1)[0]
    bits = [n for n, ok in (("dot", "." in local), ("hyphen", "-" in local), ("underscore", "_" in local),
                            ("digit", any(c.isdigit() for c in local))) if ok]
    return "local part: " + ("+".join(bits) if bits else "letters only")


FORM = {"IPV4_ADDRESS": ipv4_form, "IPV6_ADDRESS": ipv6_form, "MAC_ADDRESS": mac_form, "EMAIL": email_form}


# -- context ----------------------------------------------------------------
def context(text: str, s: int, e: int, family: str, fmt: str | None) -> str:
    """Where the span sits: a structured container format, a `Label: value`
    line, a CSV-like cell, or prose."""
    if fmt:
        return f"container:{fmt}"
    ls = text.rfind("\n", 0, s) + 1
    le = text.find("\n", e)
    line = text[ls:le if le >= 0 else len(text)]
    before = text[ls:s]
    if re.fullmatch(r"\s*[\w ./()-]{1,40}:\s*", before):
        return "label: value line"
    if line.count(";") >= 2 or line.count(",") >= 3 or line.count("|") >= 2:
        return "table / csv-like line"
    return "prose"


def boundary(text: str, s: int, e: int) -> str:
    """The character right after the value (a split often starts at one)."""
    ch = text[e:e + 1]
    return {"": "end of text", "\n": "line break", " ": "space"}.get(ch, ch)


def analyse(path: str) -> dict:
    out = {lab: {"real": 0, "real_docs": 0, "real_forms": collections.Counter(),
                 "real_family": collections.Counter(), "real_context": collections.Counter(),
                 "real_after": collections.Counter(),
                 "lookalike": 0, "lookalike_docs": 0, "lookalike_kinds": collections.Counter(),
                 "lookalike_family": collections.Counter(), "lookalike_context": collections.Counter(),
                 "both_in_doc": 0} for lab in LABELS}
    resembles = {}
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
        from piigen.negatives import ALL_DECOY_KINDS
        resembles = {k: v.resembles for k, v in ALL_DECOY_KINDS.items()}
    except Exception:
        pass
    n = 0
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        n += 1
        text, spec = r["text"], r.get("_spec") or {}
        fam, fmt = spec.get("family", "?"), spec.get("format")
        real_here, fake_here = collections.Counter(), collections.Counter()
        for ent in r["entities"]:
            lab = ent["label"]
            if lab not in out:
                continue
            o = out[lab]
            v = text[ent["start"]:ent["end"]]
            o["real"] += 1
            real_here[lab] += 1
            o["real_forms"][FORM[lab](v)] += 1
            o["real_family"][fam] += 1
            o["real_context"][context(text, ent["start"], ent["end"], fam, fmt)] += 1
            o["real_after"][boundary(text, ent["start"], ent["end"])] += 1
        for x in r.get("_decoys") or []:
            lab = x.get("resembles") or resembles.get(x["kind"])
            if lab not in out:
                continue
            o = out[lab]
            o["lookalike"] += 1
            fake_here[lab] += 1
            o["lookalike_kinds"][x["kind"]] += 1
            o["lookalike_family"][fam] += 1
            o["lookalike_context"][context(text, x["start"], x["end"], fam, fmt)] += 1
        for lab in LABELS:
            out[lab]["real_docs"] += bool(real_here[lab])
            out[lab]["lookalike_docs"] += bool(fake_here[lab])
            out[lab]["both_in_doc"] += bool(real_here[lab] and fake_here[lab])
    return {"documents": n, "labels": {lab: {k: (dict(v.most_common()) if isinstance(v, collections.Counter) else v)
                                              for k, v in o.items()} for lab, o in out.items()}}


def md_report(res: dict) -> str:
    names = list(res)
    L = ["# IPv4, IPv6, MAC and email in the targeted data: v3 against v4", ""]
    L += ["| | " + " | ".join(names) + " |", "|---|" + "---|" * len(names)]
    L += ["| documents | " + " | ".join(f"{res[n]['documents']:,}" for n in names) + " |"]
    for lab in LABELS:
        for key, title in (("real", "real values"), ("real_docs", "documents with a real value"),
                           ("lookalike", "look-alikes"), ("lookalike_docs", "documents with a look-alike"),
                           ("both_in_doc", "documents with both")):
            L.append(f"| {SHORT[lab]}: {title} | " + " | ".join(f"{res[n]['labels'][lab][key]:,}" for n in names) + " |")
    for lab in LABELS:
        L += ["", f"## {SHORT[lab]}", ""]
        for key, title in (("real_forms", "Real values by format"), ("real_family", "Real values by family"),
                           ("real_context", "Real values by context"),
                           ("real_after", "Character right after a real value"),
                           ("lookalike_kinds", "Look-alikes by kind"), ("lookalike_family", "Look-alikes by family"),
                           ("lookalike_context", "Look-alikes by context")):
            keys = []
            for n in names:
                keys += [k for k in res[n]["labels"][lab][key] if k not in keys]
            if not keys:
                continue
            L += [f"### {title}", "", "| | " + " | ".join(names) + " | change |", "|---|" + "---|" * (len(names) + 1)]
            for k in sorted(keys, key=lambda k: -max(res[n]["labels"][lab][key].get(k, 0) for n in names)):
                vals = [res[n]["labels"][lab][key].get(k, 0) for n in names]
                ch = f"{vals[-1] - vals[0]:+,}" if len(vals) > 1 else ""
                L.append(f"| {k} | " + " | ".join(f"{v:,}" for v in vals) + f" | {ch} |")
            L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("builds", nargs="+", help="name=path.jsonl, oldest first")
    ap.add_argument("--json")
    ap.add_argument("--md")
    a = ap.parse_args()
    res = {}
    for b in a.builds:
        name, path = b.split("=", 1)
        res[name] = analyse(path)
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    md = md_report(res)
    if a.md:
        Path(a.md).write_text(md, encoding="utf-8", newline="\n")
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
