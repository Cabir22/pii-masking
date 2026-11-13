"""One-command scoreboard for any checkpoint (contract C3, task P3-1).

    python eval/scoreboard.py --model your-hf-org/masking-multilingual --name baseline_ckpt1
    python eval/scoreboard.py --model <hub id or path> --revision <sha> --name <run> \
        [--sets appendix,golden_az,...] [--public-only] [--baseline reports/scoreboard/x.json]

Writes reports/scoreboard/<name>.json and <name>.md: aggregates only, never
document texts or per-document predictions. Those stay in the resumable
prediction cache (--cache-dir, outside the repo by default).

Two inference tracks, always both:
  R  raw: transformers.pipeline("token-classification",
     aggregation_strategy="simple"), tokenizer as shipped. The benchmark's
     path (benchmarks/check_inference_path.py reproduced 94/94) and the
     primary number for every A6 gate. Documents longer than 512 tokens use
     the pipeline's sliding window (stride 256), with overlapping same-label
     window pieces joined into one span (D-51c, as model/predict.py, D-51b).
  M  model-only product path: model/predict.load_model (punctuation-boundary
     tokenizer patch) + _detect_entities_word_consistent. No regex (A2.1).
  H  optional (--with-hybrid): hybrid_detect_entities, which adds the
     pattern_fallback regex layer. Informational, never a gate.

Sets (default: every one available; `sealed` only when named explicitly):
  public   appendix (benchmark Appendix A replay), benchmark (first 5,000
           documents of data/benchmark_v3, D-6), golden_az, golden_en,
           lang_tr, lang_ru, internal_test, probes
  on request  runb_test: Run B's test split (--runb-test, default
           data/processed/runb/test.docs.jsonl, not in git; D-28). With
           --runb-v1-test each document is tagged `runb_part`: "old" when
           v1's test split has the same id with the same text, else "new";
           every metric is then also reported per part (`by_part`). Without
           it, the parts come from --runb-parts (default
           eval/runb_v2_test_parts.tsv.gz: v2's ids, parts and text hashes;
           a document not listed with the same text is "unlisted"). Always
           split by origin too (`by_origin`): "old_corpus" for the ids of
           merged_relabeled_swept_dated (RUNB_OLD_PREFIXES), else "new_data"
  private  shadow_dev, real_text, real_text_en/_tr/_ru (D-46b), sealed -- read from --private-dir
           (default ~/pii-eval-private), never from the repo

The appendix lists only the benchmark's errors, so it gets no P/R/F1: only
errors fixed / removed / still triggered by error_class, plus "unjudgeable"
new predictions (see metrics.appendix_replay).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "model"))
sys.path.insert(0, str(ROOT / "scripts"))

import metrics as M  # noqa: E402

BENCH = ROOT / "benchmarks" / "extracted"
OUT_DIR = ROOT / "reports" / "scoreboard"
PROBE_TARGETS = HERE / "probes" / "targets.json"
DEFAULT_PRIVATE = Path.home() / "pii-eval-private"
# Private list of look-alikes moved to the policy bucket by a decision (D-42), by document id and
# offsets: {set: {"data_sha256_16", "items": [{"id", "start", "end", "resembles", "kind"}]}}.
# The private set files stay unchanged (their SHA-256 must still match); the list is applied at load.
POLICY_ITEMS_FILE = "policy_items.json"
DEFAULT_CACHE = Path.home() / ".cache" / "pii-scoreboard"

PROBE_LANGS = ("tr", "en", "ru")  # D-58: our own probes per language, eval/probes_<lang>/, scored apart from the Azerbaijani ones
PUBLIC_SETS = ["appendix", "benchmark", "golden_az", "golden_en", "lang_tr", "lang_ru", "internal_test", "probes"] + \
    [f"probes_{l}" for l in PROBE_LANGS]
REAL_TEXT_LANGS = ["en", "tr", "ru"]  # independent real-text sets per language (D-46b)
PRIVATE_SETS = ["shadow_dev", "real_text"] + [f"real_text_{l}" for l in REAL_TEXT_LANGS] + [f"shadow_dev_{l}" for l in PROBE_LANGS]
EXPLICIT_ONLY = ["sealed"]
ON_REQUEST_SETS = ["runb_test"]  # public, but 15,835 documents: scored only when named
RUNB_TEST = ROOT / "data" / "processed" / "runb" / "test.docs.jsonl"
# build_sprint_mix.py prefixes every id with its source file: the old corpus's
# documents (D-23b, `_old: true`) come from these two; targeted and LLM b1-b5 are new.
RUNB_OLD_PREFIXES = ("repaired.clean__", "negatives.clean__")
RUNB_PARTS = HERE / "runb_v2_test_parts.tsv.gz"
GATE_SET = "shadow_dev"
# Until the team sends shadow aggregates (D-21), the same gate metrics on the
# benchmark are shown beside them: a reference only, never a gate.
INTERIM_GATE_SET = "benchmark"
PRIMARY_TRACK = "R"
TRACK_NAMES = {"R": "raw HF pipeline (simple)", "M": "model-only product path",
               "H": "hybrid with regex (informational, not a gate)"}
LFS_POINTER = "version https://git-lfs.github.com/spec/v1"
# Record/entity fields never used as slices: identifiers and anything that
# holds document text or a PII value (slice values land in the report).
NOT_SLICES = {"id", "text", "source_id", "value", "surface", "stem", "sentence",
              "template", "start", "end", "label", "entities", "hard_negatives", "_decoys",
              "controls"}
CHECKPOINT_EVERY_S = 30
# D-51c: track R's long-document path joins overlapping same-label window pieces (the same
# rule as predict._merge_window_spans, D-51b). Stored in each track-R cache: a cache written
# before it re-runs only its long documents.
R_LONG_DECODER = "D-51c"


# ---------------------------------------------------------------------------
# Environment and metadata
# ---------------------------------------------------------------------------

def pick_device() -> str:
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# D-37: tokenizers 0.23.x returns only the first overflow window, so every span after a long
# document's first 512-token window is lost. Scores must come from tokenizers below 0.23.
TOKENIZERS_REFUSE_FROM = (0, 23)


def _version_tuple(v: str) -> tuple[int, ...]:
    import re
    return tuple(int(x) for x in re.findall(r"\d+", v.split("+")[0])[:3])


def tokenizers_ok(version: str) -> bool:
    return _version_tuple(version)[:2] < TOKENIZERS_REFUSE_FROM


def library_versions() -> dict:
    import tokenizers
    import torch
    import transformers
    return {"tokenizers": tokenizers.__version__, "transformers": transformers.__version__,
            "torch": torch.__version__, "python": sys.version.split()[0]}


def check_versions() -> dict:
    """The library versions recorded in every report; refuse tokenizers >= 0.23 (D-37)."""
    v = library_versions()
    if not tokenizers_ok(v["tokenizers"]):
        raise SystemExit(f"tokenizers {v['tokenizers']} refused (D-37): 0.23.x keeps only the first 512-token "
                         "window of a long document, so every span after it is lost. Use tokenizers < 0.23 "
                         "(requirements.txt), with a transformers version that accepts it (e.g. 4.57.x).")
    return v


# D-51a ships the training tokenizer, whose tokenizer.json isolates punctuation. transformers 5.x
# rebuilds XLMRobertaTokenizer from the vocabulary and drops that pre-tokenizer, so track R would
# silently score with the plain tokenizer (v4's probes: R 94.6 -> 90.8). Track M sets it itself.
TOKENIZER_CHECK_TEXT = "Vəsiqə (AB9818978) və 13 oktyabr 2013, saat 14:05."


def shipped_tokenizer_json(model_id: str, revision: str | None) -> Path | None:
    p = Path(model_id) / "tokenizer.json"
    if Path(model_id).exists():
        return p if p.exists() else None
    try:
        from huggingface_hub import hf_hub_download
        return Path(hf_hub_download(model_id, "tokenizer.json", revision=revision))
    except Exception:
        return None


def tokenizer_matches_shipped(tok, tokenizer_json: Path | None, text: str = TOKENIZER_CHECK_TEXT) -> tuple[bool, str]:
    """(ok, detail): the loaded tokenizer splits `text` exactly as the model's tokenizer.json does."""
    if tokenizer_json is None:
        return True, "no tokenizer.json shipped"
    from tokenizers import Tokenizer
    want = Tokenizer.from_file(str(tokenizer_json)).encode(text, add_special_tokens=False).tokens
    got = tok.convert_ids_to_tokens(tok(text, add_special_tokens=False)["input_ids"])
    return want == got, f"shipped {want} vs loaded {got}"


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True,
                              text=True).stdout.strip()
    return {"sha": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": bool(run("status", "--porcelain", "--", "eval", "model"))}


def resolve_revision(model: str, revision: str | None) -> str:
    """The exact commit SHA scored. For a Hub id this asks the Hub (with the
    login already configured); for a local directory it hashes the weights."""
    path = Path(model)
    if path.exists():
        h = hashlib.sha256()
        for f in sorted(path.glob("*.safetensors")) or sorted(path.glob("*.bin")):
            with open(f, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
        return "local-sha256:" + h.hexdigest()[:16]
    from huggingface_hub import HfApi
    try:
        return HfApi().model_info(model, revision=revision).sha
    except Exception as e:  # offline (HF_HUB_OFFLINE, no network): use the local cache
        sha = _cached_revision(model, revision)
        if not sha:
            raise SystemExit(f"cannot resolve {model}@{revision or 'main'}: {type(e).__name__}, "
                             "and it is not in the local Hugging Face cache")
        print(f"Hub unreachable ({type(e).__name__}); revision from the local cache")
        return sha


def _cached_revision(model: str, revision: str | None) -> str | None:
    from huggingface_hub.constants import HF_HUB_CACHE
    repo = Path(HF_HUB_CACHE) / ("models--" + model.replace("/", "--"))
    if revision and len(revision) == 40 and (repo / "snapshots" / revision).is_dir():
        return revision
    ref = repo / "refs" / (revision or "main")
    return ref.read_text().strip() if ref.is_file() else None


def file_sha(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def _slug(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)


# ---------------------------------------------------------------------------
# Sets
# ---------------------------------------------------------------------------

def _is_lfs_pointer(path: Path) -> bool:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read(len(LFS_POINTER)) == LFS_POINTER


def _normalise(rec: dict) -> dict:
    """Corpus-schema record -> scoreboard doc. Decoys come from the shadow
    format (`hard_negatives`) or the generator's C2 field (`_decoys`).

    Every other scalar record field (format, category, family, noise, ...)
    becomes a doc-level slice, and every extra scalar field on an entity
    (e.g. `case`) an entity-level slice. Slice values are written into the
    committed report, so fields that hold text are never carried over."""
    decoys = rec.get("hard_negatives") or rec.get("_decoys") or _bench_decoys(rec)
    meta = {k: v for k, v in rec.items()
            if k not in NOT_SLICES and isinstance(v, (str, int, float, bool))}
    return {"id": str(rec["id"]), "text": rec["text"],
            "gold": [{**{k: v for k, v in e.items()
                         if k not in NOT_SLICES and isinstance(v, (str, int, float, bool))},
                      "label": e["label"], "start": e["start"], "end": e["end"]}
                     for e in rec.get("entities", [])],
            "control": bool(rec.get("control")),
            "controls": [{**{k: v for k, v in c.items()
                             if k not in NOT_SLICES and isinstance(v, (str, int, float, bool))},
                          "start": c["start"], "end": c["end"]}
                         for c in rec.get("controls", [])],
            "decoys": [{"start": d["start"], "end": d["end"],
                        "resembles": d.get("resembles") or d.get("label"),
                        "kind": d.get("kind"), "policy": bool(d.get("policy")), "listed": False}
                       for d in decoys],
            "meta": meta}


def _bench_decoys(rec: dict) -> list[dict]:
    """benchmark_v3 declares its look-alikes as strings (`_spec.hard_negatives`,
    labels in `hard_negative_labels`), without offsets. Each one becomes one
    decoy at its first occurrence that overlaps no gold span, preferring one
    that is not inside a longer word. `kind` says whether that place was
    unique, so the rate on ambiguous ones can be read apart."""
    spec = rec.get("_spec") or {}
    text, gold = rec["text"], rec.get("entities", [])
    out = []
    for value, label in zip(spec.get("hard_negatives") or [], spec.get("hard_negative_labels") or []):
        free, i = [], text.find(value) if value else -1
        while i >= 0:
            j = i + len(value)
            if not any(i < g["end"] and j > g["start"] for g in gold):
                free.append((i, j))
            i = text.find(value, i + 1)
        if not free:
            continue
        whole = [(i, j) for i, j in free
                 if not (i and text[i - 1].isalnum()) and not (j < len(text) and text[j].isalnum())]
        i, j = (whole or free)[0]
        out.append({"start": i, "end": j, "resembles": label,
                    "kind": "benchmark_unique" if len(free) == 1 else "benchmark_ambiguous"})
    return out


def _read_jsonl(paths: list[Path]) -> list[dict]:
    docs = []
    for p in paths:
        with open(p, encoding="utf-8") as fh:
            docs.extend(_normalise(json.loads(line)) for line in fh if line.strip())
    return docs


SWEPT = ROOT / "data" / "processed" / "merged_relabeled_swept_dated"
# The dated split (D-18b): every checkpoint is scored on this version.
# Never data/processed/merged_disjoint/test: superseded by the relabelled,
# swept split (team decision, 2026-09-30).
BENCH_V3 = ROOT / "data" / "benchmark_v3" / "pii_az_benchmark_v3_structured_9780.jsonl"
BENCH_V3_SCORED = 5000  # D-6: only bench_az_000001 ... bench_az_005000 were scored


def _lang_file(lang: str) -> tuple[list[Path], str]:
    swept = SWEPT / "test.docs.jsonl"
    if swept.exists() and not _is_lfs_pointer(swept):
        return [swept], "merged_relabeled_swept_dated/test.docs.jsonl"
    return ([ROOT / "data" / "processed" / "merged" / "test.docs.jsonl"],
            "processed/merged/test.docs.jsonl (merged_relabeled_swept_dated not pulled)")


_SEEN: dict = {}


def train_seen_values() -> tuple[dict[str, set[str]], dict]:
    """Every exact GIVENNAME/SURNAME/STREET value in merged_relabeled_swept_dated/
    train (suffix included, D-9; the D-17 relabel changed DATE spans only), for the "new names" slice. Built once per
    process by streaming the file; the values never leave memory."""
    if not _SEEN:
        path = SWEPT / "train.docs.jsonl"
        if not path.exists() or _is_lfs_pointer(path):
            raise SystemExit(f"{path.relative_to(ROOT)} missing: run `git lfs pull` "
                             "(needed for the internal_test \"new names\" slice)")
        h = hashlib.sha256()
        seen = {lab: set() for lab in M.NEW_NAME_LABELS}

        def records():
            with open(path, "rb") as fh:
                for line in fh:
                    h.update(line)
                    if line.strip():
                        yield json.loads(line)

        for lab, vals in M.seen_values(records()).items():
            seen[lab] |= vals
        _SEEN["seen"] = seen
        _SEEN["info"] = {"source": str(path.relative_to(ROOT)),
                         "sha256": h.hexdigest(),
                         "distinct_values": {l: len(v) for l, v in seen.items()}}
    return _SEEN["seen"], _SEEN["info"]


def load_set(name: str, args) -> tuple[list[dict] | None, dict]:
    """-> (docs, info). docs is None when the set is unavailable; info says why."""
    priv = Path(args.private_dir).expanduser()
    if name == "appendix":
        return load_appendix()
    if name in ("golden_az", "golden_en"):
        paths = [ROOT / "data" / "golden" / f"{name}.jsonl"]
        source = str(paths[0].relative_to(ROOT))
    elif name in ("lang_tr", "lang_ru"):
        lang = name.split("_")[1]
        paths, source = _lang_file(lang)
    elif name == "internal_test":
        paths = [SWEPT / "test.docs.jsonl"]
        source = "merged_relabeled_swept_dated/test.docs.jsonl"
    elif name == "benchmark":
        paths = [BENCH_V3]
        source = f"data/benchmark_v3 (first {BENCH_V3_SCORED:,} documents, D-6)"
    elif name == "probes" or (name.startswith("probes_") and name[7:] in PROBE_LANGS):
        paths = sorted((HERE / name).glob("*.jsonl"))
        source = f"eval/{name}/"
    elif name == "runb_test":
        paths = [Path(args.runb_test).expanduser()]
        source = f"Run B test split ({paths[0].name})"
    elif name == "shadow_dev":
        paths = [priv / "shadow_dev.jsonl"]
        source = "private: shadow_dev.jsonl"
    elif name.startswith("shadow_dev_") and name[11:] in PROBE_LANGS:   # D-58: our own EN/TR/RU shadow sets
        paths = [priv / f"{name}.jsonl"]
        source = f"private: {name}.jsonl"
    elif name == "real_text":
        paths = sorted((priv / "real_text").glob("*.jsonl"))
        source = "private: real_text/"
    elif name.startswith("real_text_") and name[10:] in REAL_TEXT_LANGS:
        paths = sorted((priv / name).glob("*.jsonl"))
        source = f"private: {name}/"
    elif name == "sealed":
        paths = [priv / "sealed.jsonl"]
        source = "private: sealed.jsonl"
    else:
        raise SystemExit(f"unknown set {name!r}")

    paths = [p for p in paths if p.exists()]
    if not paths:
        return None, {"skipped": "not found", "source": source}
    if any(_is_lfs_pointer(p) for p in paths):
        return None, {"skipped": "LFS pointer stub: run `git lfs pull`", "source": source}
    docs = []
    for p in paths:
        for d in _read_jsonl([p]):
            if name == "probes" or name.startswith("probes_"):
                d["meta"].setdefault("family", p.stem)  # one family per file
            docs.append(d)
    info = {"source": source, "data_sha256_16": file_sha(paths)}
    if name == "benchmark":
        info["file_sha256"] = hashlib.sha256(BENCH_V3.read_bytes()).hexdigest()
        docs = docs[:BENCH_V3_SCORED]
        if len(docs) != BENCH_V3_SCORED or docs[-1]["id"] != f"bench_az_{BENCH_V3_SCORED:06d}":
            raise SystemExit(f"{source}: expected ids bench_az_000001..{BENCH_V3_SCORED:06d} "
                             f"as the first {BENCH_V3_SCORED} lines")
        info["decoys_located"] = sum(len(d["decoys"]) for d in docs)
        info["policy_items"] = apply_d51e(docs)
    if name in ("lang_tr", "lang_ru"):
        lang = name.split("_")[1]
        docs = [d for d in docs if d["meta"].get("lang", lang) == lang]
        random.Random(13).shuffle(docs)
        docs = sorted(docs[:args.lang_sample], key=lambda d: d["id"])
        info["sample"] = f"{len(docs)} (seed 13)"
    if name == "runb_test":
        info["file_sha256"] = hashlib.sha256(paths[0].read_bytes()).hexdigest()
        if args.runb_v1_test:
            v1 = Path(args.runb_v1_test).expanduser()
            info["v1_file_sha256"] = hashlib.sha256(v1.read_bytes()).hexdigest()
            info["parts"] = tag_runb_parts(docs, v1)
        elif getattr(args, "runb_parts", None) and Path(args.runb_parts).exists():
            parts = read_runb_parts(Path(args.runb_parts))
            counts = {"old": 0, "new": 0, "unlisted": 0}
            for d in docs:
                hit = parts.get(d["id"])
                counts[hit[0] if hit and hit[1] == _text_hash(d["text"]) else "unlisted"] += 1
            if counts["unlisted"] < len(docs):  # the list is about this split
                for d in docs:
                    hit = parts.get(d["id"])
                    d["meta"]["runb_part"] = hit[0] if hit and hit[1] == _text_hash(d["text"]) else "unlisted"
                info["parts"] = {k: v for k, v in counts.items() if v or k != "unlisted"}
                pf = Path(args.runb_parts).resolve()
                info["parts_file"] = str(pf.relative_to(ROOT)) if pf.is_relative_to(ROOT) else pf.name
        info["origins"] = tag_runb_origins(docs)
    if name in ("shadow_dev", "sealed"):
        apply_policy_items(name, docs, info, priv)
    return docs, info


def apply_policy_items(name: str, docs: list[dict], info: dict, priv: Path) -> None:
    """D-42: mark the look-alikes named in the private policy list as policy items (kind from
    the list, `listed` True). The list must have been built from this exact file."""
    # the list lives next to the set or one level up (outside a shadow/ folder that D-5 deletes)
    f = next((d / POLICY_ITEMS_FILE for d in (priv, priv.parent) if (d / POLICY_ITEMS_FILE).exists()), None)
    spec = json.loads(f.read_text(encoding="utf-8")).get(name) if f else None
    if not spec:
        return
    if spec["data_sha256_16"] != info["data_sha256_16"]:
        raise SystemExit(f"{f.name}: the {name} list was built for data {spec['data_sha256_16']}, "
                         f"this file is {info['data_sha256_16']}")
    want = defaultdict(list)
    for it in spec["items"]:
        want[str(it["id"])].append(it)
    found = Counter()
    for d in docs:
        for it in want.get(d["id"], []):
            hit = [x for x in d["decoys"] if (x["start"], x["end"], x["resembles"]) ==
                   (it["start"], it["end"], it["resembles"])]
            if len(hit) != 1:
                raise SystemExit(f"{f.name}: {name} item {it['id']} {it['start']}-{it['end']} not found once")
            hit[0].update(kind=it["kind"], policy=True, listed=True)
            found[it["kind"]] += 1
    if sum(found.values()) != len(spec["items"]):
        raise SystemExit(f"{f.name}: {sum(found.values())} of {len(spec['items'])} {name} items found")
    info["policy_items"] = dict(sorted(found.items()))


# D-51e (2026-10-15): look-alikes that our own privacy rules treat as real values. They go to
# the policy bucket (scored and reported apart, D-29 F3): kind by rule, from the look-alike's
# label and shape only. The benchmark's are marked at load (below); shadow-dev's go into the
# private policy list (D-42) with the same rule, so the set's files stay unchanged.
D51E_KINDS = {
    "policy_d51e_fin_7_letters": "7 capital letters in a FIN field (D-33b: all-letter FINs may be real)",
    "policy_d51e_fin_6_chars": "6 letters and digits in a FIN field (D-34b: a foreign resident's PIN)",
    "policy_d51e_phone_in_fin": "a +994 phone number in a FIN field (a real phone in the wrong field)",
    "policy_d51e_10_digits_in_fin": "10 digits in a FIN field (a real VÖEN-shaped number in the wrong field)",
    "policy_d51e_date_in_building": "a real calendar date in a building-number field (D-42a, D-17: DATE)",
    # The team, 15 Oct (after the v3 release check, #84): our own conventions decide these too
    "policy_fin_7_chars": "7 letters and digits in a FIN field, not all letters (D-34a: the FIN format)",
    "policy_fin_5_6_chars": "5-6 letters or digits in a FIN field, other than the D-51e mixed 6 (D-34b)",
    "policy_card_checksum": "a card number whose only defect is the Luhn digit (D-51d)",
    "policy_iban_checksum": "an IBAN whose only defect is the mod-97 check digits (D-51d)",
    "policy_cvv_dashed": "a dashed CVV such as 99-9 (D-30b, D-39c: a real CVV)",
}
CARD_PREFIXES = ("4", "51", "52", "53", "54", "55", "2", "34", "37", "6", "35", "9")


def _luhn_digit(body: str) -> str:
    s = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        s += d - 9 if d > 9 else d
    return str((10 - s % 10) % 10)


def checksum_only(label: str, value: str) -> bool:
    """D-51d: a card or IBAN look-alike whose only defect is its check digit(s)."""
    v = "".join(value.split()).replace("-", "") if label == "PAYMENT_CARD_NUMBER" else "".join(value.split())
    if label == "PAYMENT_CARD_NUMBER":
        return v.isdigit() and 13 <= len(v) <= 19 and v.startswith(CARD_PREFIXES) and v[-1] != _luhn_digit(v[:-1])
    if label == "IBAN":
        if not (len(v) == 28 and v[:2] == "AZ" and v[2:4].isdigit() and v[4:].isalnum() and v[4:].upper() == v[4:]):
            return False
        n = int("".join(str(int(c, 36)) for c in v[4:] + v[:2] + "00"))
        return v[2:4] != f"{98 - n % 97:02d}"
    return False


def _real_date(v: str) -> bool:
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", v)
    if not m:
        return False
    try:
        dt.date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return False
    return True


def d51e_kind(resembles: str, value: str) -> str | None:
    """D-51e and the 15 Oct follow-up: the policy kind of one look-alike, or None when it
    stays a look-alike. Label and shape only."""
    v = value.strip()
    if resembles == "AZ_FIN":
        if re.fullmatch(r"[A-Z]{7}", v):
            return "policy_d51e_fin_7_letters"
        if re.fullmatch(r"(?=.*[A-Z])(?=.*\d)[A-Z0-9]{6}", v):
            return "policy_d51e_fin_6_chars"
        if re.fullmatch(r"\+994\d{9}", v):
            return "policy_d51e_phone_in_fin"
        if re.fullmatch(r"\d{10}", v):
            return "policy_d51e_10_digits_in_fin"
        if re.fullmatch(r"[A-Z0-9]{7}", v):
            return "policy_fin_7_chars"
        if re.fullmatch(r"[A-Z0-9]{5,6}", v):
            return "policy_fin_5_6_chars"
    if resembles == "BUILDINGNUM" and _real_date(v):
        return "policy_d51e_date_in_building"
    if resembles in ("PAYMENT_CARD_NUMBER", "IBAN") and checksum_only(resembles, v):
        return "policy_card_checksum" if resembles == "PAYMENT_CARD_NUMBER" else "policy_iban_checksum"
    if resembles == "CARD_SECURITY_CODE" and re.fullmatch(r"\d{1,3}-\d{1,3}", v):
        return "policy_cvv_dashed"
    return None


def apply_d51e(docs: list[dict]) -> dict[str, int]:
    """Mark the benchmark's policy look-alikes (D51E_KINDS) as policy items; -> counts per kind."""
    found = Counter()
    for d in docs:
        for x in d["decoys"]:
            k = d51e_kind(x["resembles"], d["text"][x["start"]:x["end"]])
            if k and not x["policy"]:
                x.update(kind=k, policy=True)
                found[k] += 1
    return dict(sorted(found.items()))


def read_runb_parts(path: Path) -> dict[str, tuple[str, str]]:
    """eval/runb_v2_test_parts.tsv.gz -> {id: (part, text hash)}."""
    out = {}
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or line.startswith("id\t") or not line.strip():
                continue
            i, part, _origin, h = line.rstrip("\n").split("\t")
            out[i] = (part, h)
    return out


def tag_runb_origins(docs: list[dict]) -> dict:
    """meta["runb_origin"] = "old_corpus" by id prefix, else "new_data".
    -> counts, plus how many disagree with the record's `_old` flag."""
    counts = {"old_corpus": 0, "new_data": 0}
    disagree = 0
    for d in docs:
        origin = "old_corpus" if d["id"].startswith(RUNB_OLD_PREFIXES) else "new_data"
        d["meta"]["runb_origin"] = origin
        counts[origin] += 1
        if "_old" in d["meta"] and bool(d["meta"]["_old"]) != (origin == "old_corpus"):
            disagree += 1
    return {**counts, "disagree_with__old": disagree}


def tag_runb_parts(docs: list[dict], v1_path: Path) -> dict[str, int]:
    """meta["runb_part"] = "old" if v1's test split has the same id with the
    same text, else "new" (P4-14: v2 re-split the new data). -> counts."""
    v1 = {}
    with open(v1_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                v1[str(r["id"])] = _text_hash(r["text"])
    counts = {"old": 0, "new": 0}
    for d in docs:
        part = "old" if v1.get(d["id"]) == _text_hash(d["text"]) else "new"
        d["meta"]["runb_part"] = part
        counts[part] += 1
    return counts


def load_appendix() -> tuple[list[dict], dict]:
    """Benchmark Appendix A documents that have text, each listed entry
    tagged with its errors.csv error_class (joined on data_id + kind + label
    + span; errors.csv has exactly one row per records.json entry)."""
    recs = json.loads((BENCH / "records.json").read_text(encoding="utf-8"))
    kind_of = {"prediction_not_matched": "pred", "gold_not_matched": "gold",
               "hard_negative_touched": "hard_negative"}
    classes: dict[tuple, list[str]] = defaultdict(list)
    with open(BENCH / "errors.csv", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            kind = kind_of[row["row_kind"]]
            # A prediction row carries the prediction in predicted_*; its
            # label/gold_span columns hold the gold it was compared to
            # (empty for `spurious`).
            if kind == "pred":
                label, span = row["predicted_label"], row["predicted_span"]
            else:
                label, span = row["label"], row["gold_span"]
            s, e = (int(x) for x in span.split(":"))
            classes[(row["data_id"], kind, label, s, e)].append(row["error_class"])
    docs, unjoined = [], 0
    for r in recs:
        entries = []
        for e in r["entries"]:
            lst = classes.get((r["data_id"], e["kind"], e["label"], e["start"], e["end"]))
            cls = lst.pop(0) if lst else None
            unjoined += cls is None
            entries.append({**e, "error_class": cls})
        if r["text"] is None:
            continue
        docs.append({"id": r["data_id"], "text": r["text"], "entries": entries,
                     "gold": [], "decoys": [], "meta": {}})
    listed_all = {k: sum(1 for r in recs for e in r["entries"] if e["kind"] == k)
                  for k in ("pred", "gold", "hard_negative")}
    info = {"source": "benchmarks/extracted/records.json + errors.csv",
            "data_sha256_16": file_sha([BENCH / "records.json", BENCH / "errors.csv"]),
            "appendix_documents": len(recs), "documents_with_text": len(docs),
            "listed_in_all_documents": listed_all,
            "entries_without_error_class": unjoined}
    return docs, info


# ---------------------------------------------------------------------------
# Inference with a resumable, atomically written prediction cache
# ---------------------------------------------------------------------------

def join_window_pieces(entities: list[dict]) -> list[dict]:
    """D-51c: same-label entities that overlap are pieces of one entity seen by different
    windows (an entity longer than one window, e.g. a full-length PEM key, D-27), so they are
    joined into one span; its score is the highest piece score. Touching-but-not-overlapping
    spans stay separate entities, and spans of different labels are left to the pipeline's own
    keep-longest rule afterwards. Same rule as predict._merge_window_spans (D-51b)."""
    joined: list[dict] = []
    for e in sorted(entities, key=lambda x: (x["entity_group"], x["start"], -x["end"])):
        last = joined[-1] if joined else None
        if last is not None and last["entity_group"] == e["entity_group"] and e["start"] < last["end"]:
            if e["end"] > last["end"] or e["score"] > last["score"]:
                joined[-1] = {**{k: v for k, v in last.items() if k != "word"},
                              "end": max(last["end"], e["end"]), "score": max(last["score"], e["score"])}
            continue
        joined.append(dict(e))
    return joined


def _join_pieces_pipeline():
    """The token-classification pipeline with D-51c in its long-document path. The pipeline
    calls aggregate_overlapping_entities only when a document needed more than one window,
    so documents that fit in 512 tokens (all of the benchmark's) are scored exactly as before."""
    from transformers import TokenClassificationPipeline

    class JoinPiecesPipeline(TokenClassificationPipeline):
        def aggregate_overlapping_entities(self, entities):
            return super().aggregate_overlapping_entities(join_window_pieces(entities))

    return JoinPiecesPipeline


class Engine:
    def __init__(self, model_id: str, revision: str | None, device: str, tracks: list[str]):
        from transformers import AutoTokenizer, pipeline
        import predict
        self.predict = predict
        self.device = device
        self.model, self.tok_m, self.id2label = predict.load_model(
            model_id, device=device, revision=revision)
        # Track R gets its own tokenizer exactly as shipped: load_model patched
        # tok_m in place with the punctuation-boundary pre-tokenizer.
        self.tok_r = AutoTokenizer.from_pretrained(model_id, revision=revision)
        ok, detail = tokenizer_matches_shipped(self.tok_r, shipped_tokenizer_json(model_id, revision))
        if not ok:
            import transformers
            raise SystemExit(f"track R tokenizer differs from the shipped tokenizer.json (D-51a) under "
                             f"transformers {transformers.__version__}: {detail}. Score with transformers "
                             "4.57.x (as the reports so far), not 5.x.")
        self.hf = pipeline("token-classification", model=self.model, tokenizer=self.tok_r,
                           aggregation_strategy="simple", device=device,
                           pipeline_class=_join_pieces_pipeline())
        self.max_len = min(self.tok_r.model_max_length, 512)
        self.tracks = tracks
        self.long_docs = defaultdict(int)

    def r_is_long(self, text: str) -> bool:
        return len(self.tok_r(text, add_special_tokens=True, verbose=False)["input_ids"]) > self.max_len

    def run(self, track: str, text: str) -> list[dict]:
        if track == "R":
            # The benchmark's call: no stride. Its documents all fit in 512
            # tokens; a longer one would be truncated by the pipeline, so
            # only those fall back to the pipeline's own sliding window,
            # whose overlapping same-label pieces are joined (D-51c).
            kw = {}
            if self.r_is_long(text):
                kw = {"stride": 256}
                self.long_docs["R"] += 1
            return [{"label": o["entity_group"], "start": int(o["start"]), "end": int(o["end"]),
                     "score": round(float(o["score"]), 6)} for o in self.hf(text, **kw)]
        if track == "M":
            out = self.predict._detect_entities_word_consistent(
                text, self.model, self.tok_m, self.id2label, device=self.device)
        elif track == "H":
            out = self.predict.hybrid_detect_entities(
                text, self.model, self.tok_m, self.id2label, device=self.device)
        else:
            raise ValueError(track)
        return [{"label": o["label"], "start": o["start"], "end": o["end"]} for o in out]


def _atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def predict_set(engine: Engine, track: str, docs: list[dict], cache_file: Path,
                cache_key: dict, label: str) -> dict[str, list[dict]]:
    """Predictions for every doc, resumed from `cache_file` when its key
    (model, revision, set, track) matches. Each cached prediction carries a
    hash of its document's text, so editing some documents of a set (probes)
    re-runs only those. A cache written before per-document hashes is
    trusted only if its whole-set hash still matches. Partial results are
    written atomically every CHECKPOINT_EVERY_S seconds and at the end, so a
    killed CPU run loses at most that much work. The cache holds offsets,
    labels, scores and text hashes only, never text. A track-R cache written before the
    D-51c join re-runs only its documents longer than one window."""
    data_sha = cache_key.get("data")
    key = {k: v for k, v in cache_key.items() if k != "data"}
    preds: dict[str, list[dict]] = {}
    hashes: dict[str, str] = {}
    marks = {"r_long": R_LONG_DECODER} if track == "R" else {}
    blob = {}
    if cache_file.exists():
        blob = json.loads(cache_file.read_text(encoding="utf-8"))
        old_key = {k: v for k, v in blob.get("key", {}).items() if k != "data"}
        if old_key == key and "hashes" in blob:
            preds, hashes = blob["preds"], blob["hashes"]
        elif old_key == key and blob["key"].get("data") == data_sha:
            preds = blob["preds"]
            hashes = {d["id"]: _text_hash(d["text"]) for d in docs if d["id"] in preds}
        else:
            print(f"  [{label}] cache key or data changed, starting fresh: {cache_file}")
    remark = bool(preds) and any(blob.get(k) != v for k, v in marks.items())
    if remark and track == "R":
        stale = [d["id"] for d in docs if d["id"] in hashes and engine.r_is_long(d["text"])]
        for i in stale:
            hashes.pop(i)
        print(f"  [{label}] cache written before the {R_LONG_DECODER} join: "
              f"re-running its {len(stale)} long documents")
    todo = [d for d in docs if hashes.get(d["id"]) != _text_hash(d["text"])]
    if preds:
        print(f"  [{label}] resuming: {len(docs) - len(todo)} cached, {len(todo)} to go")

    def save():
        _atomic_write(cache_file, json.dumps({"key": key, **marks, "preds": preds, "hashes": hashes}))

    t0 = last = time.time()
    for i, d in enumerate(todo, 1):
        preds[d["id"]] = engine.run(track, d["text"])
        hashes[d["id"]] = _text_hash(d["text"])
        now = time.time()
        if now - last >= CHECKPOINT_EVERY_S or i == len(todo):
            save()
            last = now
            rate = (now - t0) / i
            print(f"  [{label}] {i}/{len(todo)}  {rate:.2f} s/doc  "
                  f"ETA {rate * (len(todo) - i) / 60:.1f} min", flush=True)
    if not todo and (remark or not cache_file.exists()):
        save()
    return preds


# ---------------------------------------------------------------------------
# Scoring and reports
# ---------------------------------------------------------------------------

def score_set(name: str, docs: list[dict], preds: dict[str, list[dict]],
              slice_keys: list[str] | None = None, baseline: dict | None = None) -> dict:
    scored = [{**d, "pred": preds[d["id"]]} for d in docs]
    if name == "appendix":
        return {"appendix_replay": M.appendix_replay(
            [{"data_id": d["id"], "entries": d["entries"]} for d in scored],
            {d["id"]: d["pred"] for d in scored})}
    out = {"all": M.score_docs(scored, slice_keys)}
    n_policy = sum(1 for d in docs for x in d["decoys"] if x["policy"])
    out["policy_decoys"] = n_policy
    if n_policy:
        excl = M.drop_policy_predictions(scored)
        res = M.score_docs(excl, slice_keys)
        res["decoys"] = M.decoy_triggers(excl, include_policy=False)
        out["excl_policy"] = res
    if any(x.get("listed") for d in docs for x in d["decoys"]):
        # D-42: the same scores without the listed items (their look-alikes and the predictions
        # on them), for A4 and A5 with and without them; plus A5 with their documents left out
        res = M.score_docs(M.drop_listed(scored), slice_keys)
        res["documents_listed_docs_out"] = M.document_rates(
            [d for d in scored if d["gold"] or not any(x.get("listed") for x in d["decoys"])])
        out["excl_listed"] = res
    if name == "internal_test":
        seen, _ = train_seen_values()
        langs = defaultdict(list)
        for d in scored:
            langs[d["meta"].get("lang", "unknown")].append(d)
        out["new_names"] = {"all": M.new_name_recall(scored, seen),
                            "per_lang": {l: M.new_name_recall(g, seen)
                                         for l, g in sorted(langs.items())}}
    if name == "runb_test" and any("runb_part" in d["meta"] for d in docs):
        parts = defaultdict(list)
        for d in scored:
            parts[d["meta"]["runb_part"]].append(d)
        out["by_part"] = {p: M.score_docs(g, slice_keys) for p, g in sorted(parts.items())}
    if name == "runb_test" and any("runb_origin" in d["meta"] for d in docs):
        origins = defaultdict(list)
        for d in scored:
            origins[d["meta"]["runb_origin"]].append(d)
        out["by_origin"] = {o: M.score_docs(g, slice_keys) for o, g in sorted(origins.items())}
    if name == "probes" or name.startswith("probes_"):
        fams = defaultdict(list)
        for d in scored:
            fams[d["meta"].get("family", "unknown")].append(d)
        out["per_family"] = {f: M.score_docs(g, slice_keys) for f, g in sorted(fams.items())}
        out["confusion"] = {f: M.confusion_matrix(g) for f, g in sorted(fams.items())}
        tpath = PROBE_TARGETS if name == "probes" else HERE / name / "targets.json"
        targets = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else {}
        base = ((baseline or {}).get("sets", {}).get(name, {}).get("tracks", {})
                .get(PRIMARY_TRACK, {}).get("target_baseline", {}))
        out["targets"], out["target_baseline"] = {}, {}
        for f in sorted(fams):
            if f in targets:
                out["targets"][f] = M.evaluate_target(targets[f], out["per_family"][f],
                                                      out["confusion"][f], base.get(f))
                out["target_baseline"][f] = M.baseline_values(targets[f], out["per_family"][f],
                                                              out["confusion"][f])
        out["families_without_target"] = sorted(set(fams) - set(targets))
    return out


TARGETS = [  # (gate, sprint-1 target, sprint-2 target)
    ("micro_f1", (">=", 0.76), (">=", 0.82)),
    ("weakest_label_f1", (">=", 0.50), (">=", 0.65)),
    ("ACCESS_TOKEN_f1", (">=", 0.50), (">=", 0.75)),
    ("IPV6_ADDRESS_f1", (">=", 0.50), (">=", 0.75)),
    ("AZ_DRIVER_LICENSE_NUMBER_f1", (">=", 0.50), (">=", 0.75)),
    ("hard_negative_trigger_rate", ("<", 0.12), ("<", 0.08)),
    ("pii_free_fp_rate", ("<", 0.30), ("<", 0.15)),
]


def _passes(v, op_t):
    if v is None:
        return None
    op, t = op_t
    return v >= t if op == ">=" else v < t


def _gate_values(g: dict | None) -> dict:
    if not g:
        return {}
    pl = g["exact"]["per_label"]
    supported = {l: v for l, v in pl.items() if v["tp"] + v["fn"] > 0}
    values = {
        "micro_f1": g["exact"]["micro"]["f1"],
        "weakest_label_f1": min((v["f1"] for v in supported.values()), default=None),
        "hard_negative_trigger_rate": g["decoys"]["overall"]["rate_same_label"]
        if g["decoys"]["overall"]["decoys"] else None,
        "pii_free_fp_rate": g["documents"]["pii_free_fp_rate"],
    }
    for lab in ("ACCESS_TOKEN", "IPV6_ADDRESS", "AZ_DRIVER_LICENSE_NUMBER"):
        values[f"{lab}_f1"] = supported[lab]["f1"] if lab in supported else None
    return values


def gates(results: dict, baseline: dict | None) -> list[dict]:
    """The A6 gate table, measured on shadow-dev, track R. Rows that need a
    set that was not scored say so instead of inventing a number. `interim`
    is the same metric on INTERIM_GATE_SET: a reference, never a pass/fail."""
    rows = []
    g = results.get(GATE_SET, {}).get("tracks", {}).get(PRIMARY_TRACK, {}).get("all")
    values = _gate_values(g)
    interim = _gate_values(results.get(INTERIM_GATE_SET, {}).get("tracks", {})
                           .get(PRIMARY_TRACK, {}).get("all"))
    for gate, s1, s2 in TARGETS:
        v = values.get(gate)
        rows.append({"gate": gate, "value": v, "sprint1": s1, "sprint1_pass": _passes(v, s1),
                     "sprint2": s2, "sprint2_pass": _passes(v, s2),
                     "interim": interim.get(gate),
                     "note": None if g else f"{GATE_SET} not scored: shadow pending"})

    # Recall guard: no label's exact recall more than 1 point below the baseline's.
    note, ok, viol = None, None, []
    base_g = (baseline or {}).get("sets", {}).get(GATE_SET, {}).get("tracks", {}) \
        .get(PRIMARY_TRACK, {}).get("all")
    if not baseline:
        note = "no --baseline given"
    elif not (g and base_g):
        note = f"{GATE_SET} missing in this run or the baseline"
    else:
        for lab, b in base_g["exact"]["per_label"].items():
            cur = g["exact"]["per_label"].get(lab, {"recall": 0.0})
            if b["tp"] + b["fn"] and cur["recall"] < b["recall"] - 0.01:
                viol.append(f"{lab} {b['recall']:.3f}->{cur['recall']:.3f}")
        ok = not viol
    rows.append({"gate": "recall_guard", "value": "; ".join(viol) or None,
                 "sprint1": ("", "no label -1 pt"), "sprint1_pass": ok,
                 "sprint2": ("", "no label -1 pt"), "sprint2_pass": ok, "note": note})

    # Golden / per-language regression: <= 1 pt micro-F1 drop vs the baseline.
    drops, note, ok = [], None, None
    if not baseline:
        note = "no --baseline given"
    else:
        for s in ("golden_en", "lang_tr", "lang_ru"):
            cur = results.get(s, {}).get("tracks", {}).get(PRIMARY_TRACK, {}).get("all")
            base = baseline.get("sets", {}).get(s, {}).get("tracks", {}) \
                .get(PRIMARY_TRACK, {}).get("all")
            if cur and base:
                drops.append((s, base["exact"]["micro"]["f1"] - cur["exact"]["micro"]["f1"]))
        ok = all(dd <= 0.01 for _, dd in drops) if drops else None
        note = None if drops else "no language set in both runs"
    rows.append({"gate": "en_tr_ru_regression",
                 "value": "; ".join(f"{s} {-dd * 100:+.1f} pt" for s, dd in drops) or None,
                 "sprint1": ("", "<= 1 pt drop"), "sprint1_pass": ok,
                 "sprint2": ("", "<= 1 pt drop"), "sprint2_pass": ok, "note": note})

    ap = results.get("appendix", {}).get("tracks", {}).get(PRIMARY_TRACK, {}).get("appendix_replay")
    rows.append({"gate": "appendix_known_errors_fixed",
                 "value": (f"FN fixed {ap.get('gold_fixed', 0)}/{ap['listed_gold']}, "
                           f"FP removed {ap.get('pred_removed', 0)}/{ap['listed_pred']}") if ap else None,
                 "sprint1": ("", "reported by class"), "sprint1_pass": None,
                 "sprint2": ("", "reported by class"), "sprint2_pass": None,
                 "note": None if ap else "appendix not scored"})
    rows.append({"gate": "sealed_set", "value": "scored" if "sealed" in results else "untouched",
                 "sprint1": ("", "untouched"), "sprint1_pass": "sealed" not in results,
                 "sprint2": ("", "run once"), "sprint2_pass": None, "note": None})
    return rows


def _pct(v):
    return "–" if v is None else f"{v * 100:.1f}"


def _fmt_val(v):
    if v is None:
        return "n/a"
    return _pct(v) if isinstance(v, float) else str(v)


def _ctl(c):
    parts = []
    if c["records"]:
        parts.append(f"{_pct(c['record_fp_rate'])} rec")
    if c["spans"]:
        parts.append(f"{_pct(c['span_fp_rate'])} span")
    return ", ".join(parts) or "–"


def _pf(p):
    return "–" if p is None else ("PASS" if p else "FAIL")


MD_SLICE_ROWS = 60


def _render_slices(report: dict) -> list[str]:
    """Exact vs overlap recall per slice value, every track side by side.
    Per-label numbers per slice are in the JSON."""
    L = []
    for sname, s in report["sets"].items():
        tracks = s.get("tracks") or {}
        firsts = [tr["all"]["slices"] for tr in tracks.values() if "all" in tr]
        if not firsts:
            continue
        rows = []
        for level in ("entity", "doc"):
            for key, vals in firsts[0][level].items():
                for val in vals:
                    cells = []
                    for tr in tracks.values():
                        blk = tr["all"]["slices"][level].get(key, {}).get(val)
                        rec = (blk or {}).get("recall", blk) if level == "doc" else blk
                        cells.append(f"{_pct(rec and rec['exact_recall'])} / "
                                     f"{_pct(rec and rec['overlap_recall'])} / "
                                     f"{rec['split'] if rec else '–'}")
                    n = (vals[val]["recall"] if level == "doc" else vals[val])["gold"]
                    rows.append(f"| {level}:{key} | {val} | {n} | " + " | ".join(cells) + " |")
        for key, vals in firsts[0]["control"].items():
            for val in vals:
                cells = [f"FP {_pct(tr['all']['slices']['control'].get(key, {}).get(val, {}).get('span_fp_rate'))}"
                         for tr in tracks.values()]
                rows.append(f"| control:{key} | {val} | {vals[val]['spans']} spans | "
                            + " | ".join(cells) + " |")
        if not rows:
            continue
        L += ["", f"### Slices: {sname} (exact recall / overlap recall / split spans)", "",
              "| Slice | Value | Gold | " + " | ".join(tracks) + " |",
              "|---|---|---|" + "---|" * len(tracks)]
        L += rows[:MD_SLICE_ROWS]
        if len(rows) > MD_SLICE_ROWS:
            L.append(f"| … | {len(rows) - MD_SLICE_ROWS} more rows in the JSON | | |")
    return L


def _fmt_metric(v, metric):
    if v is None:
        return "–"
    if metric in ("split_spans", "wrong_label"):
        return str(int(v))
    return _pct(v)


def _render_probe_targets(report: dict) -> list[str]:
    s = report["sets"].get("probes")
    if not s or "tracks" not in s:
        return []
    L = []
    for t, tr in s["tracks"].items():
        tg = tr.get("targets")
        if not tg:
            continue
        n_pass = sum(1 for x in tg.values() if x["pass"] is True)
        n_show = sum(1 for x in tg.values() if x["shows_failure_at_ckpt1"])
        L += ["", f"## Probe targets (track {t}): {n_pass}/{len(tg)} families pass; "
              f"{n_show}/{len(tg)} show their failure", "",
              "| Family | Docs | Condition | Measured | Target | Pass | Shows the failure |",
              "|---|---|---|---|---|---|---|"]
        for fam, res in tg.items():
            docs = tr["per_family"][fam]["documents"]["documents"]
            for i, c in enumerate(res["conditions"]):
                what = c["metric"] + (f" [{','.join(c['labels'])}]" if c.get("labels") else "") + \
                    (f" {c['from']}→{'/'.join(c['to'])}" if c.get("from") else "")
                thr = ("×" + str(c["relative"]) + " ckpt1") if "relative" in c and c["threshold"] is None \
                    else _fmt_metric(c["threshold"], c["metric"])
                L.append(f"| {fam if i == 0 else ''} | {docs if i == 0 else ''} | {what} | "
                         f"{_fmt_metric(c['measured'], c['metric'])} | {c['op']} {thr} | "
                         f"{_pf(c['pass'])} | {('yes' if res['shows_failure_at_ckpt1'] else '**NO**') if i == 0 else ''} |")
            for sc in res["sanity"]:
                L.append(f"|  |  | sanity: {sc['metric']} | {_fmt_metric(sc['measured'], sc['metric'])} | "
                         f"{sc['op']} {_fmt_metric(sc['value'], sc['metric'])} | {_pf(sc['pass'])} |  |")
        cvv = tr["per_family"].get("decoy_cvv", {}).get("decoys", {}).get("per_kind")
        if cvv:  # 12345 is in the training data now (D-44): its items apart from the random 5-digit codes
            L.append("\n`decoy_cvv` look-alikes masked as CVV, by kind: " + "; ".join(
                f"{CVV_KINDS.get(k, k)} {v['triggered_same_label']}/{v['decoys']}" for k, v in sorted(cvv.items())))
        if tr.get("families_without_target"):
            L.append(f"\nFamilies without a target: {', '.join(tr['families_without_target'])}")
    return L


CVV_KINDS = {"d2_dummy": "`12345` dummies (D-2)", "invalid_shape": "random 5-digit codes",
             "policy_d34c": "dashed, policy (D-34c)", "policy_d39c": "dashed, policy (D-39c)"}


def _render_new_names(report: dict) -> list[str]:
    s = report["sets"].get("internal_test")
    if not s or "tracks" not in s:
        return []
    si = s["info"].get("seen_index", {})
    L = ["", "## New names (internal_test)", "",
         "Recall on GIVENNAME/SURNAME/STREET mentions whose exact value (suffix included, D-9) "
         f"occurs in `{si.get('source', 'train')}` (seen) vs never (new). A large seen−new gap "
         "means the model memorised the name pool.", "",
         "| Track | Scope | Label | Seen gold | Seen exact / overlap R | New gold | "
         "New exact / overlap R | Exact gap (pt) |",
         "|---|---|---|---|---|---|---|---|"]
    for t, tr in s["tracks"].items():
        nn = tr.get("new_names")
        if not nn:
            continue
        scopes = [("all", nn["all"])] + [(l, v) for l, v in nn["per_lang"].items()]
        for scope, blk in scopes:
            for lab in (["ALL"] + list(M.NEW_NAME_LABELS) if scope == "all" else ["ALL"]):
                se, ne = blk[lab]["seen"], blk[lab]["new"]
                gap = (se["exact_recall"] - ne["exact_recall"]) * 100 \
                    if se["exact_recall"] is not None and ne["exact_recall"] is not None else None
                L.append(f"| {t} | {scope} | {lab} | {se['gold']} | {_pct(se['exact_recall'])} / "
                         f"{_pct(se['overlap_recall'])} | {ne['gold']} | {_pct(ne['exact_recall'])} / "
                         f"{_pct(ne['overlap_recall'])} | "
                         f"{'–' if gap is None else f'{gap:+.1f}'} |")
    return L


def _render_runb_parts(report: dict) -> list[str]:
    """runb_test: overall; old (also in v1) / new (v2 only); old corpus / new data."""
    s = report["sets"].get("runb_test")
    if not s or "tracks" not in s:
        return []
    L = []
    for t, tr in s["tracks"].items():
        blocks = ([("all", tr["all"])] + list(tr.get("by_part", {}).items())
                  + list(tr.get("by_origin", {}).items()))
        L += ["", f"## Run B test split by part (track {t})", "",
              "old / new = same id and text as in v1's test split / v2 only; old_corpus / new_data = "
              "by id prefix (merged_relabeled_swept_dated vs targeted + LLM b1-b5). Exact-span percentages.", "",
              "| Part | Docs | Micro P / R / F1 | Macro F1 | PII-free docs | PII-free FP |",
              "|---|---|---|---|---|---|"]
        for name, r in blocks:
            e, dd = r["exact"], r["documents"]
            L.append(f"| {name} | {dd['documents']} | {_pct(e['micro']['precision'])} / "
                     f"{_pct(e['micro']['recall'])} / {_pct(e['micro']['f1'])} | {_pct(e['macro_f1'])} | "
                     f"{dd['pii_free_documents']} | {_pct(dd['pii_free_fp_rate'])} |")
        labels = sorted({l for _, r in blocks for l in r["exact"]["per_label"]})
        L += ["", "| Label | " + " | ".join(f"{n} F1 (gold)" for n, _ in blocks) + " |",
              "|---|" + "---|" * len(blocks)]
        for lab in labels:
            cells = []
            for _, r in blocks:
                v = r["exact"]["per_label"].get(lab)
                cells.append("–" if not v else f"{_pct(v['f1'])} ({v['tp'] + v['fn']})")
            L.append(f"| {lab} | " + " | ".join(cells) + " |")
    return L


def render_md(report: dict) -> str:
    m = report["meta"]
    L = [f"# Scoreboard: {m['name']}", "",
         "| | |", "|---|---|",
         f"| Model | `{m['model']}` |", f"| Revision SHA | `{m['revision_sha']}` |",
         f"| Requested revision | `{m['revision_requested']}` |",
         f"| Code git SHA | `{m['git']['sha']}`{' (eval/ or model/ dirty)' if m['git']['dirty'] else ''} |",
         f"| Date (UTC) | {m['date_utc']} |", f"| Device | {m['device']} |",
         f"| Libraries | {', '.join(f'{k} {v}' for k, v in m.get('versions', {}).items()) or 'not recorded (report older than D-37)'} |",
         f"| Tracks | {', '.join(f'{t} = {TRACK_NAMES[t]}' for t in m['tracks'])} |",
         f"| Data version | {'; '.join(f'{k} `{v}`' for k, v in m['data_version'].items()) or '–'} |",
         "", f"## A6 gates ({GATE_SET}, track {PRIMARY_TRACK})", "",
         f"`{INTERIM_GATE_SET}` is the same metric on that set, track {PRIMARY_TRACK}: "
         "a reference while the shadow numbers are pending, never a gate.", "",
         f"| Gate | Measured | {INTERIM_GATE_SET} | Sprint 1 target | S1 | Sprint 2 target | S2 | Note |",
         "|---|---|---|---|---|---|---|---|"]
    for r in report["gates"]:
        t1 = f"{r['sprint1'][0]} {_fmt_val(r['sprint1'][1])}".strip()
        t2 = f"{r['sprint2'][0]} {_fmt_val(r['sprint2'][1])}".strip()
        L.append(f"| {r['gate']} | {_fmt_val(r['value'])} | {_fmt_val(r.get('interim'))} | {t1} | "
                 f"{_pf(r['sprint1_pass'])} | {t2} | {_pf(r['sprint2_pass'])} | {r['note'] or ''} |")
    gs = report["sets"].get(GATE_SET, {})
    xl = gs.get("tracks", {}).get(PRIMARY_TRACK, {}).get("excl_listed")
    if xl:
        dc = xl["decoys"]["overall"]
        L += ["", f"Without the private policy list ({', '.join(f'{k} {v}' for k, v in gs['info']['policy_items'].items())}; D-42): "
              f"hard-negative trigger rate {_pct(dc['rate_same_label']) if dc['decoys'] else '–'}, "
              f"PII-free FP {_pct(xl['documents']['pii_free_fp_rate'])} "
              f"({_pct(xl['documents_listed_docs_out']['pii_free_fp_rate'])} with their documents left out of the PII-free count)."]

    L += ["", "## Sets", "",
          "Percentages. Exact = label+start+end. Trigger = decoy hit with the label it "
          "resembles (any label in brackets).", "",
          "| Set | Track | Docs | Exact P / R / F1 | Macro F1 | Overlap F1 | Char leak | "
          "Narrower | Split | Trigger | Control FP | PII-free FP | Perfect |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for sname, s in report["sets"].items():
        if "skipped" in s:
            continue
        for t, tr in s["tracks"].items():
            for variant in ("all", "excl_policy"):
                r = tr.get(variant)
                if not r:
                    continue
                e, dd, dc = r["exact"], r["documents"], r["decoys"]["overall"]
                trig = (f"{_pct(dc['rate_same_label'])} ({_pct(dc['rate_any_label'])})"
                        if dc["decoys"] else "–")
                tag = " excl. policy" if variant == "excl_policy" else ""
                L.append(f"| {sname}{tag} | {t} | {dd['documents']} | "
                         f"{_pct(e['micro']['precision'])} / {_pct(e['micro']['recall'])} / "
                         f"{_pct(e['micro']['f1'])} | {_pct(e['macro_f1'])} | "
                         f"{_pct(r['overlap']['micro']['f1'])} | {_pct(r['leakage']['rate'])} | "
                         f"{_pct(r['boundary']['narrower_share'])} | {r['recall']['split']} | {trig} | "
                         f"{_ctl(r['controls'])} | "
                         f"{_pct(dd['pii_free_fp_rate'])} | {_pct(dd['perfect_rate'])} |")
    L += _render_probe_targets(report)
    L += _render_runb_parts(report)
    L += _render_slices(report)
    L += _render_new_names(report)
    skipped = {k: v for k, v in report["sets"].items() if "skipped" in v}
    if skipped:
        L += ["", "Not scored: " + "; ".join(f"`{k}` ({v['skipped']})" for k, v in skipped.items())]

    ap = report["sets"].get("appendix")
    if ap and "tracks" in ap:
        la = ap["info"]["listed_in_all_documents"]
        a0 = next(iter(ap["tracks"].values()))["appendix_replay"]
        L += ["", "## Appendix replay (errors only: no P/R/F1 on this set)", "",
              f"Only the {ap['info']['documents_with_text']} of {ap['info']['appendix_documents']} "
              "appendix documents whose text was rebuilt exactly can be re-run, so every "
              f"count below is restricted to them: {a0['listed_pred']} of the report's "
              f"{la['pred']} listed wrong predictions, {a0['listed_gold']} of its {la['gold']} "
              f"listed missed gold and {a0['listed_hard_negative']} of its {la['hard_negative']} "
              "touched decoys. The other "
              f"{ap['info']['appendix_documents'] - ap['info']['documents_with_text']} documents "
              "have no usable text in the PDF extraction (benchmarks/extract_report.py accepts a "
              "rebuild only if every listed span lands on its value).", "",
              "| Track | Listed FP reproduced | FP removed | Listed FN still missed | FN fixed | "
              "Decoys still triggered (same label) | Unjudgeable new preds | New preds on listed |",
              "|---|---|---|---|---|---|---|---|"]
        for t, tr in ap["tracks"].items():
            a = tr["appendix_replay"]
            L.append(f"| {t} | {a.get('pred_reproduced', 0)}/{a['listed_pred']} "
                     f"({_pct(a['pred_reproduced_rate'])}) | {a.get('pred_removed', 0)} | "
                     f"{a.get('gold_still_missed', 0)}/{a['listed_gold']} "
                     f"({_pct(a['gold_still_missed_rate'])}) | {a.get('gold_fixed', 0)} | "
                     f"{a.get('decoy_still_triggered', 0)}/{a['listed_hard_negative']} "
                     f"({a.get('decoy_still_triggered_same_label', 0)}) | "
                     f"{a.get('new_pred_unjudgeable', 0)} | {a.get('new_pred_overlapping_listed', 0)} |")
        for t, tr in ap["tracks"].items():
            L += ["", f"By error class, track {t}:", "",
                  "| error_class | FP reproduced | FP removed | FN still missed | FN fixed | "
                  "Decoy still triggered | Decoy cleared |", "|---|---|---|---|---|---|---|"]
            for cls, c in tr["appendix_replay"]["by_error_class"].items():
                L.append(f"| {cls} | {c.get('pred_reproduced', 0)} | {c.get('pred_removed', 0)} | "
                         f"{c.get('gold_still_missed', 0)} | {c.get('gold_fixed', 0)} | "
                         f"{c.get('decoy_still_triggered', 0)} | {c.get('decoy_cleared', 0)} |")
    if m.get("reproduction_check"):
        rc = m["reproduction_check"]
        L += ["", f"## Reproduction check (track {PRIMARY_TRACK}): **{'PASS' if rc['pass'] else 'FAIL'}**", "",
              f"- listed wrong predictions reproduced exactly: {rc['pred_reproduced']}/{rc['listed_pred']} "
              f"= {_pct(rc['pred_reproduced_rate'])}% (need ≥ 99%)",
              f"- listed gold still missed: {rc['gold_still_missed']}/{rc['listed_gold']} "
              f"= {_pct(rc['gold_still_missed_rate'])}% (need ≥ 99%)",
              "- denominators: documents with text only (see the appendix section above)"]
    L += ["", "Calibration (score bins vs precision) is in the JSON. It is reported only and "
          "is never used to set a threshold (A2.2).", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="Hub id or local checkpoint directory")
    ap.add_argument("--revision", default=None, help="Hub branch, tag or commit SHA")
    ap.add_argument("--name", required=True, help="run name: reports/scoreboard/<name>.json/.md")
    ap.add_argument("--sets", default=None,
                    help=f"comma list (default: all available of {PUBLIC_SETS + PRIVATE_SETS})")
    ap.add_argument("--public-only", action="store_true", help="skip private sets")
    ap.add_argument("--tracks", default="R,M",
                    help="R and M are always both for a real run; narrowing is for debugging only")
    ap.add_argument("--with-hybrid", action="store_true",
                    help="add track H (regex hybrid), informational only")
    ap.add_argument("--baseline", default=None, help="an earlier scoreboard JSON (recall guard, regression)")
    ap.add_argument("--private-dir", default=str(DEFAULT_PRIVATE))
    ap.add_argument("--cache-dir", default=str(DEFAULT_CACHE),
                    help="resumable prediction cache (keep it outside git)")
    ap.add_argument("--slice-by", default=None,
                    help="comma list of record/entity fields to slice by even if they have "
                         "many values (every scalar field is sliced automatically)")
    ap.add_argument("--lang-sample", type=int, default=1000)
    ap.add_argument("--runb-test", default=str(RUNB_TEST), help="runb_test: Run B's test.docs.jsonl")
    ap.add_argument("--runb-v1-test", default=None,
                    help="runb_test: v1's test.docs.jsonl, to split the report into old/new documents")
    ap.add_argument("--runb-parts", default=str(RUNB_PARTS),
                    help="runb_test without --runb-v1-test: the saved old/new id list (ids + text hashes)")
    ap.add_argument("--limit", type=int, default=None, help="first N docs per set (smoke tests)")
    ap.add_argument("--sample", type=int, default=None,
                    help="a seeded random N docs per set (smoke tests on CPU); predictions "
                         "are cached per doc id, so a later full run reuses them")
    ap.add_argument("--check-reproduction", action="store_true",
                    help="exit 1 unless track R reproduces >= 99%% of the appendix's listed "
                         "wrong predictions and still misses >= 99%% of its listed gold "
                         "(checkpoint 1 only)")
    ap.add_argument("--out-dir", default=str(OUT_DIR))
    args = ap.parse_args(argv)

    tracks = [t.strip() for t in args.tracks.split(",") if t.strip()]
    if args.with_hybrid and "H" not in tracks:
        tracks.append("H")
    if set(tracks) - set(TRACK_NAMES):
        raise SystemExit(f"unknown track in {tracks}")
    if not {"R", "M"} <= set(tracks):
        print(f"WARNING: tracks {tracks} -- a real scoreboard run scores both R and M")

    if args.sets:
        wanted = [s.strip() for s in args.sets.split(",") if s.strip()]
    else:
        wanted = PUBLIC_SETS + PRIVATE_SETS
    if args.public_only:
        wanted = [s for s in wanted if s in PUBLIC_SETS + ON_REQUEST_SETS]

    git_at_start = git_info()  # the code that produces the predictions, not the code at exit
    slice_keys = [k.strip() for k in (args.slice_by or "").split(",") if k.strip()]
    versions = check_versions()
    print("libraries: " + ", ".join(f"{k} {v}" for k, v in versions.items()))
    device = pick_device()
    print(f"device: {device}")
    revision_sha = resolve_revision(args.model, args.revision)
    print(f"model: {args.model}  revision: {revision_sha}")

    loaded = {}
    results: dict = {}
    for s in wanted:
        docs, info = load_set(s, args)
        if docs is None:
            print(f"set {s}: skipped ({info['skipped']})")
            results[s] = info
            continue
        if args.sample and len(docs) > args.sample:
            docs = sorted(random.Random(7).sample(docs, args.sample), key=lambda d: d["id"])
            info["sample"] = f"{args.sample} (seed 7)"
        if args.limit:
            docs = docs[:args.limit]
            info["limit"] = args.limit
        info["documents"] = len(docs)
        loaded[s] = (docs, info)
        print(f"set {s}: {len(docs)} docs  [{info['source']}]")

    # Load exactly the commit recorded in the report (a Hub id is pinned to
    # its resolved SHA; a local directory has no revision).
    load_rev = None if Path(args.model).exists() else revision_sha
    engine = Engine(args.model, load_rev, device, tracks) if loaded else None
    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8")) if args.baseline else None
    cache_root = Path(args.cache_dir).expanduser() / _slug(args.model) / _slug(revision_sha)
    timings = {}
    for s, (docs, info) in loaded.items():
        results[s] = {"info": info, "tracks": {}}
        for t in tracks:
            key = {"model": args.model, "revision": revision_sha, "set": s, "track": t,
                   "data": info["data_sha256_16"]}
            if t in ("M", "H"):   # the product decoder changes (e.g. the validity check) re-run M/H
                key["decoder"] = getattr(engine.predict, "DECODER_VERSION", "none") if engine.predict else "none"  # per-doc-id preds: --limit runs resume into full ones
            t0 = time.time()
            preds = predict_set(engine, t, docs, cache_root / f"{s}.{t}.json", key, f"{s}/{t}")
            timings[f"{s}/{t}"] = round(time.time() - t0, 1)
            results[s]["tracks"][t] = score_set(s, docs, preds, slice_keys, baseline)
            if t == "H":
                results[s]["tracks"][t]["informational"] = True

    if "internal_test" in loaded:
        results["internal_test"]["info"]["seen_index"] = train_seen_values()[1]
    meta = {
        "name": args.name, "model": args.model, "revision_requested": args.revision,
        "revision_sha": revision_sha, "git": git_at_start,
        "date_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "device": device, "versions": versions, "tracks": tracks, "primary_track": PRIMARY_TRACK,
        "data_version": {s: v["info"]["data_sha256_16"] for s, v in results.items() if "info" in v},
        "long_documents_strided_track_R": dict(engine.long_docs) if engine else {},
        "track_R_long_documents": f"overlapping same-label window pieces joined ({R_LONG_DECODER})",
        "seconds": timings, "baseline": args.baseline,
    }
    rc_ok = True
    ap_r = results.get("appendix", {}).get("tracks", {}).get("R", {}).get("appendix_replay")
    if ap_r:
        rc = {k: ap_r.get(k, 0) for k in ("pred_reproduced", "listed_pred", "pred_reproduced_rate",
                                           "gold_still_missed", "listed_gold",
                                           "gold_still_missed_rate")}
        # A rate is None when a --limit/--sample run lists nothing of that kind.
        rc["pass"] = (rc["pred_reproduced_rate"] or 0) >= 0.99 and (rc["gold_still_missed_rate"] or 0) >= 0.99
        if args.check_reproduction:
            meta["reproduction_check"] = rc
            rc_ok = rc["pass"]
    report = {"meta": meta, "gates": gates(results, baseline), "sets": results}

    out = Path(args.out_dir)
    _atomic_write(out / f"{args.name}.json", json.dumps(report, ensure_ascii=False, indent=1))
    _atomic_write(out / f"{args.name}.md", render_md(report))
    print(f"wrote {out / args.name}.json and .md")
    if ap_r:
        print(f"appendix/R: listed FP reproduced {ap_r.get('pred_reproduced', 0)}/{ap_r['listed_pred']} "
              f"({_pct(ap_r['pred_reproduced_rate'])}%), listed gold still missed "
              f"{ap_r.get('gold_still_missed', 0)}/{ap_r['listed_gold']} "
              f"({_pct(ap_r['gold_still_missed_rate'])}%)")
    if args.check_reproduction:
        print(f"reproduction check: {'PASS' if rc_ok and ap_r else 'FAIL'}")
        return 0 if rc_ok and ap_r else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
