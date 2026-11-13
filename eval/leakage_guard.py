"""Leakage guard (contract C4, task P3-5): exit 0 only if a corpus is clean.

    python eval/leakage_guard.py <file.docs.jsonl> [...] [--frames <py file>]
                                 [--shadow-hashes eval/leakage_guard_shadow.json.gz]
                                 [--barrier-hashes eval/leakage_guard_barrier_<set>.json.gz ...]
                                 [--bench-docs <jsonl> ...] [--json report.json]

Three checks (A2 rules 3 and 5):

1. Benchmark values. Every value in benchmarks/extracted/records.json
   (gold, pred, hard_negative) and errors.csv, found as an exact,
   boundary-delimited match inside a training text, is a failure.
   - The D-2 policy allowlist (data/policy_allowlist.txt) is reported
     separately, never failed.
   - Only DISTINCTIVE values are checked: at least 6 non-space characters
     and not vocabulary. Short fragments (`Ə`, `42`) and words or names,
     even case-noised (`Məmmədov`, `Ərizənin`, `BUZoVNA`), are natural
     vocabulary, not generated values: counted and listed for review, like
     the 8-gram stoplist. A name copied inside a benchmark SENTENCE is
     still caught by check 2. All-capitals codes (`AUJAKHM`) are checked.
   - A listed wrong PREDICTION that is a piece of a listed gold/decoy value
     of the same document (`KEY-----`, `+994 51`) is covered by that value.
   - LOW-ENTROPY values are scanned but reported, not failed: every label
     they were listed under is small-universe (DATE, TIME, AGE, ZIPCODE,
     BUILDINGNUM, CARD_SECURITY_CODE: every calendar date occurs somewhere),
     or they carry under 28 bits (`AZ1000`, `12:50 AM`).
2. Benchmark sentences. Shared word 8-grams between the appendix texts
   (plus errors.csv snippets and any --bench-docs file, D-6) and the
   training text. A shared 8-gram that is in the reviewed stoplist
   (eval/leakage_guard_stoplist.txt, printed on every run) is ignored.
3. Shadow barrier. SHA-1 hashes of the shadow set's word 8-grams and
   distinctive values (eval/leakage_guard_shadow.json.gz, built by
   eval/build_shadow_hashes.py from the private shadow folder). Hits are
   reported as hash + training doc id only; the shadow texts never
   appear anywhere. Every committed eval/leakage_guard_barrier_*.json.gz
   (the same format, built from another private set such as the EN/TR/RU
   real-text sets, D-46) is checked the same way, merged with the shadow
   hashes; --barrier-hashes adds more. The red-team barrier
   (eval/build_redteam_barrier.py, the findings marked `test`) adds
   whole-text hashes of its 3-7 word findings (`short_sha1`): the exact word
   run of that length inside a training text is a hit, like an 8-gram.

Normalisation for 8-grams: lower-case (with the combining dot of `İ`
removed), then Unicode word runs (`\\w+`), so punctuation and spacing
differences don't hide a copied sentence.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT / "benchmarks" / "extracted"
ALLOWLIST = ROOT / "data" / "policy_allowlist.txt"
STOPLIST = HERE / "leakage_guard_stoplist.txt"
SHADOW_HASHES = HERE / "leakage_guard_shadow.json.gz"
SHADOW_FORMAT = "pii-leakage-shadow/1"
N = 8
MAX_HITS_SHOWN = 20
MIN_VALUE_CHARS = 6
MIN_ENTROPY_BITS = 28.0  # ~4.7 bits per letter, ~3.3 per digit
# Labels whose values come from a small universe (every calendar date, real
# postcodes, times, ages, house numbers, 3-4 digit codes): a match in a
# training text is expected by chance, so it is reported, not failed.
LOW_ENTROPY_LABELS = {"DATE", "TIME", "AGE", "ZIPCODE", "BUILDINGNUM", "CARD_SECURITY_CODE"}
WORD = re.compile(r"\w+")

# Used only if data/policy_allowlist.txt is missing; a fallback, not the source.
POLICY_ALLOWLIST_FALLBACK = ("1234", "12345", "123456", "0000", "4242424242424242",
                             "4111111111111111", "5555555555554444", "P12345678", "A12B34")


# ---------------------------------------------------------------------------
# Shared normalisation (also used by build_shadow_hashes.py)
# ---------------------------------------------------------------------------

def words(text: str) -> list[str]:
    return WORD.findall(text.lower().replace("̇", ""))


def ngrams(ws: list[str], n: int = N):
    for i in range(len(ws) - n + 1):
        yield " ".join(ws[i:i + n])


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


APOSTROPHES = "'\u2019\u02bc"


def is_vocabulary(value: str) -> bool:
    """Words and names, including case-noised ones (`BUZoVNA`): letters and
    spaces only, with at least one lower-case letter or a space. An
    all-capitals letter string (`AUJAKHM`) is a code, not a word.

    An apostrophe between letters belongs to the word: `Ordubad'ı` is the
    city Ordubad with an apostrophe-form suffix (D-9, the P2-4c renderer),
    as natural as `Ordubadı`, not a generated code."""
    if not value or not (value[0].isalpha() and value[-1].isalpha()):
        return False
    core = value
    for a in APOSTROPHES:
        core = core.replace(a, "")
    return \
        all(ch.isalpha() or ch.isspace() for ch in core) and \
        (any(ch.islower() for ch in core) or " " in core.strip())


def is_distinctive(value: str) -> bool:
    """A generated value worth guarding: >= 6 non-space characters and not
    vocabulary."""
    return len("".join(value.split())) >= MIN_VALUE_CHARS and not is_vocabulary(value)


def entropy_bits(value: str) -> float:
    return sum(4.7 if ch.isalpha() else 3.32 if ch.isdigit() else 0.0 for ch in value)


def is_low_entropy(value: str, labels: list[str]) -> bool:
    """Distinctive in shape but likely to occur by chance: every label it was
    listed under is a small-universe label, or it carries under 28 bits
    (`AZ1000`, `12:50 AM`, `192.168.1.1`)."""
    labs = {x for l in labels for x in l.split("|")}
    return (bool(labs) and labs <= LOW_ENTROPY_LABELS) or entropy_bits(value) < MIN_ENTROPY_BITS


def anchor_of(value: str) -> tuple[str, int] | None:
    """The value's longest word run and its offset inside the value: the
    key a training text is scanned for before the full value is compared."""
    runs = list(WORD.finditer(value))
    if not runs:
        return None
    m = max(runs, key=lambda r: len(r.group()))
    return m.group(), m.start()


def _bounded(text: str, s: int, e: int) -> bool:
    """No word character glued on either side of text[s:e]."""
    before = text[s - 1] if s > 0 else ""
    after = text[e] if e < len(text) else ""
    return not (before and WORD.match(before) and WORD.match(text[s])) and \
        not (after and WORD.match(after) and WORD.match(text[e - 1]))


# ---------------------------------------------------------------------------
# Reference material
# ---------------------------------------------------------------------------

def load_allowlist() -> tuple[set[str], str]:
    if ALLOWLIST.exists():
        vals = {l.strip() for l in ALLOWLIST.read_text(encoding="utf-8").splitlines() if l.strip()}
        return vals, ALLOWLIST.relative_to(ROOT).as_posix()
    return set(POLICY_ALLOWLIST_FALLBACK), "POLICY_ALLOWLIST_FALLBACK constant"


def load_stoplist(path: Path = STOPLIST) -> list[str]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(" ".join(words(line)))
    return out


def load_benchmark(extra_docs: list[Path]) -> tuple[dict, dict]:
    """-> (values: value -> {"labels", "fragment"}, grams: 8-gram -> source id).

    `fragment` is True when every listing of the value is a wrong
    PREDICTION that lies inside a listed gold or decoy value of the same
    document (a boundary error: `KEY-----` of a PEM key, `+994 51` of a
    phone). Such a value is covered by the full value it was cut from."""
    recs = json.loads((BENCH / "records.json").read_text(encoding="utf-8"))
    values: dict[str, set] = defaultdict(set)
    not_fragment: set[str] = set()
    grams: dict[str, str] = {}
    for r in recs:
        planted = [e["value"] for e in r["entries"] if e["kind"] != "pred"]
        for e in r["entries"]:
            values[e["value"]].add(e["label"])
            if e["kind"] != "pred" or not any(e["value"] != p and e["value"] in p for p in planted):
                not_fragment.add(e["value"])
        if r["text"]:
            for g in ngrams(words(r["text"])):
                grams.setdefault(g, r["data_id"])
    with open(BENCH / "errors.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["value"]:
                values[row["value"]].add(row["label"] or row["predicted_label"])
                if row["value"] not in values or row["row_kind"] != "prediction_not_matched":
                    not_fragment.add(row["value"])
            # Snippets are cut mid-word at both ends: drop the edge words.
            for g in ngrams(words(row["text_snippet"])[1:-1]):
                grams.setdefault(g, row["data_id"] + ":snippet")
    for p in extra_docs:  # D-6: the full benchmark file, when it arrives
        with open(p, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                r = json.loads(line)
                for e in r.get("entities", []):
                    values[r["text"][e["start"]:e["end"]]].add(e["label"])
                    not_fragment.add(r["text"][e["start"]:e["end"]])
                for g in ngrams(words(r["text"])):
                    grams.setdefault(g, str(r.get("id", p.name)))
    return ({v: {"labels": sorted(l for l in labs if l), "fragment": v not in not_fragment}
             for v, labs in values.items()}, grams)


def barrier_files() -> list[Path]:
    """The committed barrier files besides the shadow one (D-46: EN/TR/RU private sets)."""
    return sorted(HERE.glob("leakage_guard_barrier_*.json.gz"))


def merge_barriers(parts: list[tuple[Path, dict]]) -> dict:
    """One barrier from several hash files: the union of 8-gram and value hashes."""
    grams, short, values, sources = set(), {}, {}, []
    for path, d in parts:
        if d.get("missing"):
            continue
        grams.update(d["ngram_sha1"])
        short.update({x["sha1"]: x for x in d.get("short_sha1", [])})
        values.update({v["sha1"]: v for v in d["values"]})
        sources.append(f"{path.name}: {d.get('source')}")
    return {"ngram_sha1": sorted(grams), "short_sha1": sorted(short.values(), key=lambda x: x["sha1"]),
            "values": sorted(values.values(), key=lambda v: v["sha1"]),
            "source": sources or None, "missing": not sources}


def load_shadow(path: Path) -> dict:
    if not path.exists():
        return {"ngram_sha1": [], "values": [], "source": None, "missing": True}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("format") != SHADOW_FORMAT or data.get("n") != N:
        raise SystemExit(f"{path}: not a {SHADOW_FORMAT} file with n={N}")
    return data


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def iter_docs(paths: list[Path]):
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if line.strip():
                    r = json.loads(line)
                    yield str(r.get("id", f"{p.name}:{i}")), r.get("text") or ""


def iter_frames(path: Path):
    """The C1 module: every frame, generic frame, neutral sentence and
    anchor form, with value/anchor slots replaced by a word that breaks
    8-grams (so an 8-gram never spans a slot)."""
    spec = importlib.util.spec_from_file_location("frames_under_check", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    items = []
    for name in ("FRAMES", "ANCHORS"):
        for lab, strs in (getattr(mod, name, None) or {}).items():
            items += [(f"{name}[{lab}][{i}]", s) for i, s in enumerate(strs)]
    for name in ("GENERIC_FRAMES", "NEUTRAL"):
        items += [(f"{name}[{i}]", s) for i, s in enumerate(getattr(mod, name, None) or [])]
    for ident, s in items:
        yield f"frames:{ident}", re.sub(r"\{[^{}]*\}", " zzslotzz ", s)


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------

class Guard:
    def __init__(self, values: dict, grams: dict, allowlist: set[str], stoplist: list[str],
                 shadow: dict):
        self.allowlist = allowlist
        values = {v: (x if isinstance(x, dict) else {"labels": list(x), "fragment": False})
                  for v, x in values.items()}
        self.fragments = {v for v, x in values.items() if x["fragment"] and v not in allowlist}
        self.checked = {v: x["labels"] for v, x in values.items() if v not in self.fragments
                        and (v in allowlist or is_distinctive(v))}
        self.skipped = {v: x["labels"] for v, x in values.items()
                        if v not in self.checked and v not in self.fragments}
        self.low_entropy = {v for v, l in self.checked.items()
                            if v not in allowlist and is_low_entropy(v, l)}
        self.index: dict[str, list] = defaultdict(list)
        for v in self.checked:
            a = anchor_of(v)
            if a:
                self.index[a[0]].append((v, a[1]))
        self.stop = set(stoplist)
        self.grams = {g: src for g, src in grams.items() if g not in self.stop}
        self.stopped_grams = len(grams) - len(self.grams)
        self.first = {g.split(" ", 1)[0] for g in self.grams}
        stop_h = {sha1(g) for g in self.stop}
        self.sh_grams = {bytes.fromhex(h) for h in shadow["ngram_sha1"]} - {bytes.fromhex(h) for h in stop_h}
        # Whole short texts (3-7 words, the red-team barrier): exact word run of that length.
        self.sh_short: dict[int, set] = defaultdict(set)
        for x in shadow.get("short_sha1", []):
            self.sh_short[x["n"]].add(bytes.fromhex(x["sha1"]))
        self.sh_values: dict[bytes, list] = defaultdict(list)
        for v in shadow["values"]:
            self.sh_values[bytes.fromhex(v["anchor_sha1"])].append((v["offset"], v["length"], v["sha1"]))
        self.hits = {"values": [], "allowlisted": [], "low_entropy": [], "sentences": [],
                     "shadow_ngrams": [], "shadow_values": []}
        self.value_counts = Counter()
        self.counts = Counter()

    def _hit(self, kind: str, rec: dict):
        self.counts[kind] += 1
        if "value" in rec:
            self.value_counts[(kind, rec["value"])] += 1
        if len(self.hits[kind]) < MAX_HITS_SHOWN:
            self.hits[kind].append(rec)

    def scan(self, doc_id: str, text: str):
        self.counts["documents"] += 1
        # Check 1: benchmark values, keyed on their longest word run.
        seen_here = set()
        for m in WORD.finditer(text):
            for v, off in self.index.get(m.group(), ()):
                s = m.start() - off
                if s < 0 or text[s:s + len(v)] != v or not _bounded(text, s, s + len(v)):
                    continue
                if (v, s) in seen_here:
                    continue
                seen_here.add((v, s))
                kind = ("allowlisted" if v in self.allowlist else
                        "low_entropy" if v in self.low_entropy else "values")
                self._hit(kind, {"doc": doc_id, "value": v, "labels": self.checked[v][:3],
                                 "context": text[max(0, s - 30):s + len(v) + 30]})
        ws = words(text)
        # Check 2: benchmark 8-grams (first-word prefilter keeps this cheap).
        for i in range(len(ws) - N + 1):
            if ws[i] in self.first:
                g = " ".join(ws[i:i + N])
                if g in self.grams:
                    self._hit("sentences", {"doc": doc_id, "ngram": g, "benchmark": self.grams[g]})
        # Check 3: shadow barrier, by hash only.
        if self.sh_grams:
            for g in ngrams(ws):
                h = hashlib.sha1(g.encode("utf-8")).digest()
                if h in self.sh_grams:
                    self._hit("shadow_ngrams", {"doc": doc_id, "ngram_sha1": h.hex()})
        for n, hs in self.sh_short.items():
            for g in ngrams(ws, n):
                h = hashlib.sha1(g.encode("utf-8")).digest()
                if h in hs:
                    self._hit("shadow_ngrams", {"doc": doc_id, "ngram_sha1": h.hex(), "n": n})
        if self.sh_values:
            for m in WORD.finditer(text):
                cands = self.sh_values.get(hashlib.sha1(m.group().encode("utf-8")).digest())
                for off, length, vh in cands or ():
                    s = m.start() - off
                    if s >= 0 and _bounded(text, s, s + length) and \
                            not is_vocabulary(text[s:s + length]) and \
                            sha1(text[s:s + length]) == vh:
                        self._hit("shadow_values", {"doc": doc_id, "value_sha1": vh})

    def clean(self) -> bool:
        return not (self.counts["values"] or self.counts["sentences"]
                    or self.counts["shadow_ngrams"] or self.counts["shadow_values"])


def report(g: Guard, meta: dict) -> str:
    L = ["=" * 70, "LEAKAGE GUARD (C4)", "=" * 70]
    for k, v in meta.items():
        L.append(f"{k}: {v}")
    L += ["", f"8-gram stoplist ({len(g.stop)} entries, {STOPLIST.relative_to(ROOT)}):"]
    L += [f"  - {s}" for s in sorted(g.stop)] or ["  (empty)"]
    n_allow = len([v for v in g.checked if v in g.allowlist])
    alpha = sorted((v for v in g.skipped if len("".join(v.split())) >= MIN_VALUE_CHARS),
                   key=lambda x: (len(x), x))
    L += ["", f"Benchmark values: {len(g.checked) + len(g.skipped) + len(g.fragments)} distinct.",
          f"  failed on a match: {len(g.checked) - n_allow - len(g.low_entropy)} high-entropy values "
          f"(>= {MIN_VALUE_CHARS} non-space chars, not vocabulary, >= {MIN_ENTROPY_BITS:.0f} bits, "
          f"not only small-universe labels {sorted(LOW_ENTROPY_LABELS)})",
          f"  reported, not failed: {n_allow} D-2 allowlisted; {len(g.low_entropy)} low-entropy",
          f"  not scanned: {len(g.fragments)} prediction fragments of a listed gold/decoy value; "
          f"{len(g.skipped)} vocabulary or too short (words/names, or under {MIN_VALUE_CHARS} chars)",
          "  vocabulary values of 6+ characters, first 30 for review: "
          + ", ".join(repr(v) for v in alpha[:30]),
          "  prediction fragments, first 20 for review: "
          + ", ".join(repr(v) for v in sorted(g.fragments, key=lambda x: (len(x), x))[:20])]
    L += [f"Benchmark 8-grams: {len(g.grams)} ({g.stopped_grams} stoplisted). "
          f"Shadow: {len(g.sh_grams)} 8-gram hashes, {sum(map(len, g.sh_short.values()))} short-text hashes, "
          f"{sum(len(v) for v in g.sh_values.values())} value hashes.", ""]
    sections = [("values", "CHECK 1  benchmark values (FAIL)"),
                ("allowlisted", "CHECK 1b D-2 allowlisted values (reported, not a failure)"),
                ("low_entropy", "CHECK 1c low-entropy values (reported, not a failure)"),
                ("sentences", "CHECK 2  benchmark 8-grams (FAIL)"),
                ("shadow_ngrams", "CHECK 3  shadow 8-grams, hash + doc id only (FAIL)"),
                ("shadow_values", "CHECK 3  shadow values, hash + doc id only (FAIL)")]
    for key, title in sections:
        L.append(f"{title}: {g.counts[key]} hit(s)")
        top = [(v, n) for (k, v), n in g.value_counts.most_common() if k == key]
        if top:
            L.append(f"    {len(top)} distinct value(s); most frequent: "
                     + ", ".join(f"{v!r} x{n}" for v, n in top[:15]))
        for h in g.hits[key]:
            L.append("    " + json.dumps(h, ensure_ascii=False))
    L += ["", f"documents scanned: {g.counts['documents']}",
          f"RESULT: {'CLEAN (exit 0)' if g.clean() else 'LEAK FOUND (exit 1)'}"]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", type=Path, help=".docs.jsonl files to check")
    ap.add_argument("--frames", type=Path, action="append", default=[],
                    help="a frames module (C1) to check")
    ap.add_argument("--shadow-hashes", type=Path, default=SHADOW_HASHES)
    ap.add_argument("--barrier-hashes", type=Path, action="append", default=[],
                    help="more barrier files (default: every eval/leakage_guard_barrier_*.json.gz)")
    ap.add_argument("--bench-docs", type=Path, action="append", default=[],
                    help="extra benchmark documents (D-6: the full 5,000-document file)")
    ap.add_argument("--json", type=Path, default=None, help="write the full report as JSON")
    args = ap.parse_args(argv)
    if not args.inputs and not args.frames:
        ap.error("give at least one .docs.jsonl file or --frames")

    allowlist, allow_src = load_allowlist()
    values, grams = load_benchmark(args.bench_docs)
    extra = sorted(set(barrier_files()) | set(args.barrier_hashes))
    shadow = merge_barriers([(args.shadow_hashes, load_shadow(args.shadow_hashes))] +
                            [(p, load_shadow(p)) for p in extra])
    g = Guard(values, grams, allowlist, load_stoplist(), shadow)
    for p in args.inputs:
        for doc_id, text in iter_docs([p]):
            g.scan(doc_id, text)
    for p in args.frames:
        for doc_id, text in iter_frames(p):
            g.scan(doc_id, text)
    meta = {"inputs": ", ".join(str(p) for p in args.inputs + args.frames),
            "D-2 allowlist": f"{len(allowlist)} values from {allow_src}",
            "shadow hashes": (f"{args.shadow_hashes} (source: {shadow.get('source')})"
                              if not shadow.get("missing") else f"{args.shadow_hashes} MISSING"),
            "barrier files": ", ".join(p.name for p in extra) or "none"}
    print(report(g, meta))
    if args.json:
        per_value: dict[str, dict] = defaultdict(dict)
        for (kind, v), n in g.value_counts.most_common():
            per_value[kind][v] = n
        args.json.write_text(json.dumps({"meta": meta, "counts": dict(g.counts), "hits": g.hits,
                                         "value_hit_counts": per_value, "clean": g.clean()},
                                        ensure_ascii=False, indent=1),
                             encoding="utf-8")
    return 0 if g.clean() else 1


if __name__ == "__main__":
    raise SystemExit(main())
