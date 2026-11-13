"""v4.1 analysis: read every benchmark gold span of one label that
v4 does not find exactly, next to v3's outcome on the same span, and the
false alarms of that label.

    python reports/v41_public_analysis/read_errors.py --label IPV6_ADDRESS [--label EMAIL ...] \
        [--set benchmark|probes] [--track R] [--out reports/v41_public_analysis/out]

Predictions come from the scoreboard's prediction cache (run eval/scoreboard.py
for both models first). The benchmark and the probes are public (task sheet,
rule 3), so values are printed. Outcomes are metrics.gold_outcome's.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval"))
import metrics as M  # noqa: E402
import scoreboard as SB  # noqa: E402

ALL_MODELS = {
    "v3": ("your-hf-org/masking-az-runb-v3-seed42", "717b0105c5203f6b3e9919e170be7000c17b6d79"),
    "v4": ("your-hf-org/masking-az-runb-v4-seed42", "e4ca17842f005e5b103f1d32d21859360c92b258"),
    "v4.1": ("your-hf-org/masking-az-runb-v4.1-seed42", "502598c1d5850958e98b1922ce65d504f700b528"),
    "v4.2": ("your-hf-org/masking-az-runb-v4.2-seed42", "223e54e8799dc60f6f6b19362191cf7c10c774c7"),
}
# The pair every script compares, older first: P4_PAIR=v4,v4.1 for the v4 -> v4.1 check,
# P4_PAIR=v4.1,v4.2 for v4.1 -> v4.2 (outputs in out_v42/).
# The default is the v4 analysis (v3 against v4, outputs in out/).
OLD, NEW = os.environ.get("P4_PAIR", "v3,v4").split(",")
MODELS = {NEW: ALL_MODELS[NEW], OLD: ALL_MODELS[OLD]}
OUT = Path(__file__).parent / ("out" if NEW == "v4" else "out_" + NEW.replace(".", ""))
STAMP = re.compile(r"(?<![\d:])\d{1,2}:\d{2}(?::\d{2})?(?![\d:])")


def load_docs(name: str) -> list[dict]:
    if name == "benchmark":
        docs = SB._read_jsonl([SB.BENCH_V3])[:SB.BENCH_V3_SCORED]
        SB.apply_d51e(docs)
        return docs
    return SB._read_jsonl(sorted((ROOT / "eval" / "probes").glob("*.jsonl")))


def load_preds(model: str, sha: str, set_name: str, track: str, cache_dir: Path) -> dict[str, list[dict]]:
    f = cache_dir / SB._slug(model) / SB._slug(sha) / f"{set_name}.{track}.json"
    return json.loads(f.read_text(encoding="utf-8"))["preds"]


# -- shape of a value ---------------------------------------------------------
def ipv6_shape(v: str) -> list[str]:
    groups = [g for g in v.split(":") if g]
    letters = [c for c in v if c.isalpha()]
    if v.lower().startswith("::ffff:"):
        form = "::ffff:"
    elif "::" not in v:
        form = f"full {len(v.split(':'))} groups"
    elif v.startswith("::"):
        form = ":: start"
    elif v.endswith("::"):
        form = ":: end"
    else:
        form = ":: middle"
    case = ("no letters" if not letters else "upper" if all(c.isupper() for c in letters)
            else "lower" if all(c.islower() for c in letters) else "mixed")
    out = [form, case]
    if groups and all(g.isdigit() for g in groups if "." not in g):
        out.append("digit-only groups")
    if any(len(g) == 4 and g.startswith("0") for g in groups):
        out.append("leading zeros")
    low = v.lower()
    out.append("prefix 2001:db8" if low.startswith("2001:db8") else "prefix fd/fc" if low[:2] in ("fd", "fc")
               else "prefix fe80" if low.startswith("fe80") else "prefix ::" if low.startswith("::") else "other prefix")
    return out


def mac_shape(v: str) -> list[str]:
    sep = "dotted" if v.count(".") == 2 else "dash" if "-" in v else "colon" if ":" in v else "other"
    letters = [c for c in v if c.isalpha()]
    case = ("no letters" if not letters else "upper" if all(c.isupper() for c in letters)
            else "lower" if all(c.islower() for c in letters) else "mixed")
    return [sep, case]


def ipv4_shape(v: str) -> list[str]:
    o = v.split(".")
    out = [f"{len(o)} parts"]
    short = sum(len(x) == 1 for x in o)
    out.append(f"{short} one-digit octets" if short else "no one-digit octet")
    if v.startswith(("10.", "192.168.", "172.")):
        out.append("private")
    if v.startswith(("192.0.2.", "198.51.100.", "203.0.113.")):
        out.append("documentation")
    return out


def email_shape(v: str) -> list[str]:
    local, _, dom = v.partition("@")
    bits = [n for n, ok in (("dot", "." in local), ("hyphen", "-" in local), ("underscore", "_" in local),
                            ("digit", any(c.isdigit() for c in local)), ("plus", "+" in local)) if ok]
    out = ["local: " + ("+".join(bits) if bits else "letters only"),
           f"domain dots {dom.count('.')}"]
    if "-" in dom:
        out.append("domain hyphen")
    if any(c.isupper() for c in v):
        out.append("upper case")
    return out


def generic_shape(v: str) -> list[str]:
    s = re.sub(r"[A-Za-zƏəÖöÜüĞğİıŞşÇç]", "a", v)
    return [re.sub(r"\d", "9", s)]


SHAPE = {"IPV6_ADDRESS": ipv6_shape, "IPV4_ADDRESS": ipv4_shape, "EMAIL": email_shape, "MAC_ADDRESS": mac_shape}


# -- context --------------------------------------------------------------------
def line_of(text: str, s: int, e: int) -> tuple[str, str, str]:
    ls = text.rfind("\n", 0, s) + 1
    le = text.find("\n", e)
    le = len(text) if le < 0 else le
    return text[ls:s], text[s:e], text[e:le]


def context(text: str, s: int, e: int) -> str:
    before, _, after = line_of(text, s, e)
    line = before + text[s:e] + after
    if re.search(r'"[\w .-]+"\s*:\s*"?$', before) or line.lstrip().startswith(("{", '"')):
        return "JSON"
    if re.match(r"\s*(\[?\d{4}-\d{2}-\d{2}[ T]\d|\[\d{1,2}:\d{2}|\[?(INFO|WARN|ERROR|DEBUG)\b)", line):
        return "log line"
    # a table cell: pipes, tabs, or separators with no space after them (`a,b;c`);
    # long benchmark sentences joined by "; " are prose
    if line.count("|") >= 2 or "\t" in line or len(re.findall(r"[,;](?! )", line)) >= 2:
        return "CSV / table"
    clause = re.split(r"[.;!?]\s", before)[-1]
    if re.fullmatch(r"\s*[-*•]?\s*[\w ./()ƏəÖöÜüĞğİıŞşÇç-]{1,40}[:=]\s*", clause):
        return "Label: value"
    return "prose"


def words(text: str, s: int, e: int) -> tuple[str, str]:
    prev = re.findall(r"\S+", text[max(0, s - 60):s])
    nxt = re.findall(r"\S+", text[e:e + 60])
    return (prev[-1] if prev else "^"), (nxt[0] if nxt else "$")


def frame(text: str, s: int, e: int) -> str:
    """Two words before and after, the value as X, cut at a sentence or line end."""
    before = re.split(r"(?<=[.;!?])\s|\n", text[max(0, s - 80):s])[-1]
    after = re.split(r"[.;!?]\s|[.;!?]$|\n", text[e:e + 80])[0]
    b = re.findall(r"\S+", before)[-2:]
    a = re.findall(r"\S+", after)[:2]
    if a and not text[e:e + 1].isspace():
        a[0] = "X" + a[0]  # a suffix glued to the value (`X-dir`)
        return " ".join(b + a)
    return " ".join(b + ["X"] + a)


def norm_frame(f: str) -> str:
    """Frames that differ only by the benchmark's typos or casing count as one:
    case-folded, Azerbaijani letters to ASCII, and each word cut to 5 letters."""
    f = f.lower().translate(str.maketrans("əöüğışçı", "eougisci"))
    return " ".join(w if w.startswith("x") else w[:5] for w in f.split())


def marked(text: str, g: dict, preds: list[dict]) -> str:
    """The gold value with each same-label predicted piece in [brackets]."""
    s, e = g["start"], g["end"]
    cov = [False] * (e - s)
    starts, ends = set(), set()
    for p in preds:
        if p["label"] == g["label"] and p["start"] < e and p["end"] > s:
            a, b = max(p["start"], s), min(p["end"], e)
            for i in range(a, b):
                cov[i - s] = True
            starts.add(a)
            ends.add(b)
    out = []
    for i in range(s, e):
        if i in starts:
            out.append("[")
        out.append(text[i])
        if i + 1 in ends:
            out.append("]")
    return "".join(out)


def cut_chars(text: str, g: dict, preds: list[dict]) -> str:
    """Characters at which the value is cut: the first character not covered,
    or the character on either side of a boundary between two pieces."""
    s, e = g["start"], g["end"]
    same = sorted((p for p in preds if p["label"] == g["label"] and p["start"] < e and p["end"] > s),
                  key=lambda p: p["start"])
    cuts = []
    pos = s
    for p in same:
        a, b = max(p["start"], s), min(p["end"], e)
        if a > pos:
            cuts.append(text[pos])  # gap starts here
        elif a == pos and pos != s:
            cuts.append(text[pos - 1] + "|" + text[pos])  # two pieces touch
        pos = max(pos, b)
    if pos < e:
        cuts.append(text[pos])
    return " ".join(cuts) or "-"


def other_labels(g: dict, preds: list[dict]) -> str:
    labs = sorted({p["label"] for p in preds if p["label"] != g["label"] and p["start"] < g["end"]
                   and p["end"] > g["start"]})
    return ",".join(labs) or "-"


def analyse(label: str, docs: list[dict], preds: dict[str, dict[str, list[dict]]]) -> dict:
    shape = SHAPE.get(label, generic_shape)
    items, fps = [], []
    totals = {m: collections.Counter() for m in preds}
    by_frame = collections.defaultdict(collections.Counter)  # normalised frame -> n, exact per model
    for d in docs:
        text = d["text"]
        has_mac = any(x["label"] == "MAC_ADDRESS" for x in d["gold"])
        has_stamp = bool(STAMP.search(text))
        golds = [g for g in d["gold"] if g["label"] == label]
        for g in golds:
            outs = {m: M.gold_outcome(g, preds[m].get(d["id"], [])) for m in preds}
            for m, o in outs.items():
                totals[m][o] += 1
            fk = norm_frame(frame(text, g["start"], g["end"]))
            by_frame[fk]["n"] += 1
            for m, o in outs.items():
                by_frame[fk][m] += o == "exact"
            if outs[NEW] == "exact" and outs.get(OLD, "exact") == "exact":
                continue
            pv, nx = words(text, g["start"], g["end"])
            items.append({
                "id": d["id"], "value": text[g["start"]:g["end"]],
                "outcomes": outs,
                "new_marked": marked(text, g, preds[NEW].get(d["id"], [])),
                "old_marked": marked(text, g, preds[OLD].get(d["id"], [])) if OLD in preds else "",
                "new_cut": cut_chars(text, g, preds[NEW].get(d["id"], [])),
                "new_other": other_labels(g, preds[NEW].get(d["id"], [])),
                "shape": shape(text[g["start"]:g["end"]]),
                "context": context(text, g["start"], g["end"]),
                "prev": pv, "next": nx, "frame": frame(text, g["start"], g["end"]),
                "mac_in_doc": has_mac, "stamp_in_doc": has_stamp,
                "doc_type": d["meta"].get("_doc_type", d["meta"].get("family", "")),
                "category": d["meta"].get("_benchmark_category", d["meta"].get("role", "")),
                "n_same_label_in_doc": len(golds),
            })
        # false alarms of this label (no same-label gold overlapping), per model
        for m in preds:
            for p in preds[m].get(d["id"], []):
                if p["label"] != label or any(g["label"] == label and M._overlaps(p, g) for g in d["gold"]):
                    continue
                pol = any(x.get("policy") and M._overlaps(p, x) for x in d["decoys"])
                dec = next((x for x in d["decoys"] if M._overlaps(p, x)), None)
                pv, nx = words(text, p["start"], p["end"])
                fps.append({"model": m, "id": d["id"], "value": text[p["start"]:p["end"]],
                            "shape": generic_shape(text[p["start"]:p["end"]])[0],
                            "gold_here": ",".join(sorted({g["label"] for g in d["gold"] if M._overlaps(p, g)})) or "-",
                            "decoy_kind": (dec or {}).get("kind") or "-", "policy": pol,
                            "context": context(text, p["start"], p["end"]), "prev": pv, "next": nx})
    return {"label": label, "totals": {m: dict(c) for m, c in totals.items()},
            "by_frame": {k: dict(c) for k, c in by_frame.items()}, "items": items, "false_alarms": fps}


def md(res: dict) -> str:
    lab, items = res["label"], res["items"]
    L = [f"# {lab}: spans {NEW} or {OLD} does not find exactly", ""]
    L += ["| outcome | " + " | ".join(res["totals"]) + " |", "|---|" + "---|" * len(res["totals"])]
    for o in M.GOLD_OUTCOMES:
        L.append(f"| {o} | " + " | ".join(str(res["totals"][m].get(o, 0)) for m in res["totals"]) + " |")
    bad = [i for i in items if i["outcomes"][NEW] != "exact"]
    models = list(res["totals"])
    L += ["", "## Exact rate per frame, all spans (frames folded: case, letters, 5-letter stems)", "",
          "| frame | n | " + " | ".join(f"{m} exact" for m in models) + " |", "|---|---|" + "---|" * len(models)]
    for k, c in sorted(res["by_frame"].items(), key=lambda kv: -kv[1]["n"])[:25]:
        L.append(f"| `{k}` | {c['n']} | " + " | ".join(f"{c.get(m, 0)} ({c.get(m, 0) / c['n']:.0%})" for m in models) + " |")

    def table(title, key):
        c = collections.Counter()
        for i in bad:
            for k in (i[key] if isinstance(i[key], list) else [i[key]]):
                c[str(k)] += 1
        L.extend(["", f"## {NEW} misses and splits by {title} (n = {len(bad)})", "", "| | n |", "|---|---|"])
        L.extend(f"| `{k}` | {n} |" for k, n in c.most_common(25))

    for title, key in (("outcome", None), ("cut character", "new_cut"), ("shape", "shape"),
                       ("context", "context"), ("frame", "frame"), ("previous word", "prev"), ("next word", "next"),
                       ("MAC in the same document", "mac_in_doc"),
                       ("hh:mm(:ss) stamp in the same document", "stamp_in_doc"),
                       (f"{OLD} outcome on the same span", None), ("doc type", "doc_type"),
                       ("benchmark category", "category")):
        if key is None and title == "outcome":
            for i in bad:
                i["_o4"] = i["outcomes"][NEW]
            table(title, "_o4")
        elif key is None:
            for i in bad:
                i["_o3"] = i["outcomes"].get(OLD, "")
            table(title, "_o3")
        else:
            table(title, key)
    L += ["", f"## Every span ({NEW} not exact, or {OLD} not exact)", "",
          f"| id | {NEW} | {OLD} | {NEW} pieces | {OLD} pieces | other label ({NEW}) | context | prev | next | MAC | stamp |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for i in items:
        L.append(f"| {i['id']} | {i['outcomes'][NEW]} | {i['outcomes'].get(OLD, '')} | `{i['new_marked']}` | "
                 f"`{i['old_marked']}` | {i['new_other']} | {i['context']} | {i['prev']} | {i['next']} | "
                 f"{'y' if i['mac_in_doc'] else ''} | {'y' if i['stamp_in_doc'] else ''} |")
    fps = res["false_alarms"]
    L += ["", f"## False alarms of {lab} (no gold {lab} under them)", ""]
    for m in sorted({f['model'] for f in fps}):
        mine = [f for f in fps if f["model"] == m]
        L += [f"### {m}: {len(mine)} (policy items {sum(f['policy'] for f in mine)})", "",
              "| shape | n |", "|---|---|"]
        c = collections.Counter(f"{f['shape']} · gold here {f['gold_here']} · decoy {f['decoy_kind']}" for f in mine)
        L.extend(f"| `{k}` | {n} |" for k, n in c.most_common(30))
        L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", action="append", required=True)
    ap.add_argument("--set", default="benchmark", choices=("benchmark", "probes"))
    ap.add_argument("--track", default="R")
    ap.add_argument("--cache-dir", default=str(SB.DEFAULT_CACHE))
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    docs = load_docs(a.set)
    preds = {}
    for m, (mod, sha) in MODELS.items():
        try:
            preds[m] = load_preds(mod, sha, a.set, a.track, Path(a.cache_dir).expanduser())
        except FileNotFoundError:
            print(f"no {m} predictions cached for {a.set}/{a.track}: {m} left out")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for lab in a.label:
        res = analyse(lab, docs, preds)
        stem = f"{a.set}_{a.track}_{lab}"
        (out / f"{stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        (out / f"{stem}.md").write_text(md(res), encoding="utf-8", newline="\n")
        print(lab, res["totals"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
