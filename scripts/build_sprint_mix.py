"""Assemble and gate the sprint corpus (P4-3): one command, one tokenised folder.

    python scripts/build_sprint_mix.py [--data-version sprint1-v1] [--replay-n 60000] [--seed 20261001]

Steps, in order; any gate that exits non-zero stops the run (A2 rule 4: the
gate is never loosened, the report goes to its owner):

  1. targeted corpus   build_targeted_corpus.py -n 37000 (D-57; v4.2 30,000; D-52d 28,000; D-20 25,000) -> data/raw/<name>_targeted.jsonl
  2. gates             validate_corpus.py on the targeted file and on each LLM batch
                       (--llm, default the clean b1..b5), leakage_guard.py on all of
                       them with benchmark_v3 (D-6)
  3. split             prepare_splits.py --no-tokenize --group-split template (v4.1, data
                       audit A2: one template, one split) -> data/processed/<name>_az/,
                       then D-19c: a document whose normalised text is in more than
                       one split moves to train (the ümid / Ümid pairs)
  4. mix               train = new train + replay stratified per language,
                       val = new val + 5,000 replay val, test = new test only
                       --az-only (Run B, D-23b): no replay; each split = new + the old
                       corpus's az documents of that split minus P2-16's drop list,
                       then stop if a normalised text is in more than one split
  5. tokenise          prepare_splits.py --tokenize-only, labels.json copied in
  6. data card         <out>/DATA_CARD.md

--v4-clean (D-51f, D-51g): after step 1, the targeted file and each LLM batch
are cleaned by `piigen.v4_clean` into <out>/v4_clean_inputs/ (the inputs are
never modified) and steps 2-3 use the cleaned copies; in step 4 (--az-only)
every old document passes through the same `clean_doc` (replay documents are
not cleaned: the rules are Azerbaijani). The data card counts each rule per
source. Without the flag nothing changes.

<name> is the part of --data-version before the first "-" (sprint1-v1 ->
sprint1). --targeted-n and --out-dir exist for a small smoke run.

    python scripts/build_sprint_mix.py --az-only --data-version runb-az-v1
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from piigen.config import ENTITY_TYPES      # noqa: E402
from prepare_splits import leakage_report   # noqa: E402

LLM = [ROOT / f"data/raw/sprint1_llm_b{i}.clean.jsonl" for i in (1, 2, 3, 4, 5)]  # D-19d, D-23e
REPLAY = ROOT / "data/processed/merged_relabeled_swept_dated"
DROP_LIST = REPLAY / "az_drop_list.jsonl"   # P2-16
BENCH_V3 = ROOT / "data/benchmark_v3/pii_az_benchmark_v3_structured_9780.jsonl"
LANGS = ("az", "en", "tr", "ru")
TARGETED_SEED = 20261001
REPLAY_VAL_N = 5000
SPLITS = ("train", "val", "test")
NAME_LABELS = ("GIVENNAME", "SURNAME", "CITY", "STREET")


def run(*args: str) -> None:
    cmd = [sys.executable, *args]
    print("\n$ python " + " ".join(args), flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    if rc:
        raise SystemExit(f"STOPPED: exit {rc} from {args[0]}. Send the report to its owner; "
                         "do not loosen the gate (A2 rule 4).")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:   # LF on Windows too (D-26)
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def norm(text: str) -> str:
    """prepare_splits.leakage_report's normalized_text key."""
    return re.sub(r"\s+", " ", text).strip().lower()


def splits_by_text(splits: dict[str, list[dict]]) -> dict[str, set]:
    seen: dict[str, set] = defaultdict(set)
    for name, rows in splits.items():
        for r in rows:
            seen[norm(r["text"])].add(name)
    return seen


def cross_split_dups(splits: dict[str, list[dict]]) -> Counter:
    """Normalised texts found in more than one split, counted per split pair.
    For --az-only this covers new val/test vs old train and the reverse (D-23b)."""
    return Counter(tuple(sorted(s)) for s in splits_by_text(splits).values() if len(s) > 1)


def regroup(splits: dict[str, list[dict]]) -> int:
    """D-19c: every document whose normalised text occurs in more than one
    split moves to train, so a D-10 pair stays together. Returns how many moved."""
    seen = splits_by_text(splits)
    moved = 0
    for name in ("val", "test"):
        keep = []
        for r in splits[name]:
            if len(seen[norm(r["text"])]) > 1:
                splits["train"].append(r)
                moved += 1
            else:
                keep.append(r)
        splits[name] = keep
    return moved


def sample_replay(path: Path, n: int, rng: random.Random) -> list[dict]:
    """n documents, n // 4 per language, without loading the 700 MB file into dicts."""
    with path.open(encoding="utf-8") as fh:
        lines = fh.readlines()
    by_lang: dict[str, list[int]] = defaultdict(list)
    for i, line in enumerate(lines):
        by_lang[json.loads(line)["lang"]].append(i)
    picked = sorted(i for lang in LANGS for i in rng.sample(by_lang[lang], n // len(LANGS)))
    return [{**json.loads(lines[i]), "_replay": True} for i in picked]


def read_drop_list(path: Path) -> dict[str, tuple[str, str]]:
    """P2-16's az_drop_list.jsonl as {id: (split, reason)}; stops if it is missing."""
    if not path.exists():
        raise SystemExit(f"STOPPED: no drop list at {path} (P2-16). Run B is not built "
                         "without it (D-23b).")
    return {r["id"]: (r["split"], r["reason"]) for r in read_jsonl(path)}


def read_old_az(folder: Path, drop: dict[str, tuple[str, str]], v4=None
                ) -> tuple[dict[str, list[dict]], Counter]:
    """D-23b: the old corpus's az documents in their own splits, minus the drop list,
    tagged `_old`. Returns them and the dropped count per (reason, split). Stops if a
    listed id is not an az document of the split the list names.

    With `v4` (a `piigen.v4_clean.Tally`, --v4-clean) each kept document then
    passes through `v4_clean.clean_doc`; its drops are counted in `v4` per rule
    and split (`old_train`, ...), not in the returned counter."""
    if v4 is not None:
        from piigen.v4_clean import clean_record
    old: dict[str, list[dict]] = {}
    dropped: Counter = Counter()
    for n in SPLITS:
        old[n] = []
        with (folder / f"{n}.docs.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r["lang"] != "az":
                    continue
                hit = drop.get(r["id"])
                if hit and hit[0] == n:
                    dropped[hit[1], n] += 1
                elif v4 is None:
                    old[n].append({**r, "_old": True})
                else:
                    cleaned = clean_record({**r, "_old": True}, v4, f"old_{n}").doc
                    if cleaned is not None:
                        old[n].append(cleaned)
    if sum(dropped.values()) != len(drop):
        raise SystemExit(f"STOPPED: {len(drop) - sum(dropped.values())} drop-list ids are not "
                         "az documents of the split the list names. Send this to the team.")
    return old, dropped


def v4_lexicon_sha() -> str:
    from piigen.v4_clean import lexicon_sha256
    return lexicon_sha256()


def git_sha() -> str:
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                         text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return sha + (" (+ uncommitted changes)" if dirty else "")


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}%" if b else "n/a"


def table(head: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(f"{c:,}" if isinstance(c, int) else str(c) for c in r) + " |"
            for r in rows]
    return out + [""]


NEW = ("targeted", "llm")


def source(r: dict) -> str:
    # replay and old az documents keep the old corpus's `_source: "llm"`, hence the tags
    return "replay" if r.get("_replay") else "old" if r.get("_old") else r["_source"]


def data_card(out: Path, splits: dict[str, list[dict]], meta: dict) -> tuple[str, bool]:
    az_only = meta["az_only"]
    new = [r for name in SPLITS for r in splits[name] if source(r) in NEW]
    train_new = sum(source(r) in NEW for r in splits["train"])
    srcs = (*NEW, "old" if az_only else "replay")
    corpus = REPLAY.relative_to(ROOT).as_posix()
    L = [f"# {meta['data_version']} data card", "",
         f"- `data_version`: **{meta['data_version']}**",
         f"- git SHA: `{meta['sha']}`",
         f"- built: {date.today().isoformat()}, `{meta['cmd']}`",
         f"- targeted build: `-n {meta['targeted_n']} --seed {TARGETED_SEED}`; "
         f"split and replay seed: {meta['seed']}",
         (f"- Azerbaijani only (D-23b), no replay: the `lang == \"az\"` documents of `{corpus}` "
          f"in their own splits, minus the P2-16 drop list `{meta['drop_list']}` "
          f"({sum(meta['dropped'].values()):,} documents)") if az_only else
         (f"- replay: `{corpus}`, {meta['replay_n']:,} train "
          f"({meta['replay_n'] // 4:,} per language) + {REPLAY_VAL_N:,} val"),
         f"- LLM input: {', '.join(p.name for p in meta['llm'])}", "",
         "## Gates", "",
         "All exited 0: `validate_corpus.py` on the targeted file and on each LLM batch, "
         f"`leakage_guard.py` on all {1 + len(meta['llm'])} files with `--bench-docs` "
         f"`{BENCH_V3.relative_to(ROOT).as_posix()}`.", "",
         f"- new documents in: {meta['new_in']:,}; after `prepare_splits` "
         f"(re-validation and exact-text dedup): {meta['new_split']:,} "
         f"({meta['new_in'] - meta['new_split']:,} dropped)",
         "- v4.1 (data audit A2): the new documents are split by template (`prepare_splits "
         "--group-split template`): documents that differ only in their values and look-alikes "
         "(`_skeleton`) are always in the same split.",
         f"- D-19c: {meta['moved']:,} documents moved from val/test to train because their "
         "normalised text was in another split. After the move, exact and normalised "
         "text overlap between splits is 0.", ""]
    if az_only:
        L += ["- D-23b: after the old documents are added, no normalised text is in more "
              "than one split (new val/test vs old train and the reverse; the build stops "
              "otherwise).", ""]
    L += ["## Documents", ""]
    L += table(["source"] + list(SPLITS) + ["total"],
               [[s] + [sum(source(r) == s for r in splits[n]) for n in SPLITS]
                + [sum(source(r) == s for n in SPLITS for r in splits[n])] for s in srcs])
    L += table(["language"] + list(SPLITS),
               [[g] + [sum(r["lang"] == g for r in splits[n]) for n in SPLITS] for g in LANGS])
    if az_only:
        L += ["### Old and new per split", ""]
        rows = []
        for n in SPLITS:
            k = sum(source(r) in NEW for r in splits[n])
            rows.append([n, len(splits[n]) - k, k, len(splits[n]), pct(k, len(splits[n]))])
        L += table(["split", "old", "new", "total", "new share"], rows)
        dropped = meta["dropped"]
        L += ["### Old documents left out (P2-16 drop list, first reason)", ""]
        L += table(["reason"] + list(SPLITS) + ["total"],
                   [[why] + [dropped[why, n] for n in SPLITS]
                    + [sum(dropped[why, n] for n in SPLITS)]
                    for why in sorted({w for w, _ in dropped})])
    v4 = meta.get("v4")
    if v4 is not None:
        L += ["## v4 cleaning (D-51f, D-51g)", "",
              f"`piigen.v4_clean.clean_doc` on every source; lexicon `scripts/piigen/v4_clean_lexicon.json` "
              f"(sha256 `{meta['v4_lexicon']}`). Cleaned copies of the targeted and LLM inputs: "
              f"`{meta['v4_dir']}`; the originals are untouched. Each cell: values labelled / values "
              "unlabelled / spans trimmed / documents dropped.", ""]
        L += v4.table()
        L += ["", "Rules: R1 D-47/D-45b drop (old only), R2 TIME/DATE in stamps, R3 `-ci il` out of DATE, "
              "R4 persona names, R5 half-labelled names, R6 city heading an institution/project, "
              "R7 false SURNAME, R8 checksum-only look-alikes, R9 unlabelled ages, "
              "R10 clock times after `saat`/`vaxtı`, GATE a record that would fail a check it passed before.", ""]
        extra = v4.as_json()["checksum_only_extra_docs (IMEI_BAD_LUHN with a card's shape, not dropped)"]
        if any(extra.values()):
            L += [f"Kept, for the team: documents with an `IMEI_BAD_LUHN` look-alike that has a card's "
                  f"shape (checksum-only, not in D-51d's list): {extra}.", ""]
    L += [f"New data in train: {train_new:,} of {len(splits['train']):,} = "
          f"**{pct(train_new, len(splits['train']))}** "
          f"({'D-23b: about 31% before the drop list' if az_only else 'target about 40%, D-20'}).",
          ""]

    ent = {n: Counter(e["label"] for r in splits[n] for e in r["entities"]) for n in SPLITS}
    L += ["## Entities per label", ""]
    L += table(["label"] + list(SPLITS), [[lab] + [ent[n][lab] for n in SPLITS]
                                          for lab in ENTITY_TYPES])
    missing = [lab for lab in ENTITY_TYPES if not ent["train"][lab]]

    by_src = {s: [r for r in new if source(r) == s] for s in ("targeted", "llm")}
    L += ["## New data (targeted + LLM, all splits)", ""]
    rows = []
    for s, rs in [*by_src.items(), ("all new", new)]:
        rows.append([s, len(rs),
                     pct(sum(bool(r.get("_decoys")) for r in rs), len(rs)),
                     pct(sum(not r["entities"] for r in rs), len(rs)),
                     pct(sum(len(r["entities"]) == 1 for r in rs), len(rs))])
    L += table(["source", "documents", "with decoys", "PII-free", "single-entity"], rows)

    decoys = Counter(x["kind"] for r in new for x in r.get("_decoys", []))
    L += ["### Decoys per `_decoys.kind`", ""]
    L += table(["kind", "count"], [[k, v] for k, v in sorted(decoys.items())])

    L += ["### Format mix (`_doc_type`)", ""]
    fm = {s: Counter(r.get("_doc_type") for r in rs) for s, rs in by_src.items()}
    L += table(["`_doc_type`", "targeted", "llm"],
               [[k, fm["targeted"][k], fm["llm"][k]]
                for k in sorted(set(fm["targeted"]) | set(fm["llm"]), key=str)])

    L += ["### Suffixed name/city/street mentions per case (targeted)", "",
          "From `_suffixes`; LLM records carry no case tags, so they are left out.", ""]
    tgt = by_src["targeted"]
    mentions = Counter(e["label"] for r in tgt for e in r["entities"] if e["label"] in NAME_LABELS)
    case = defaultdict(Counter)
    for r in tgt:
        label_at = {(e["start"], e["end"]): e["label"] for e in r["entities"]}
        for x in r.get("_suffixes", []):
            lab = label_at.get((x["start"], x["end"]))
            if lab in NAME_LABELS:
                case[x["case"]][lab] += 1
    case["any case"] = sum(case.values(), Counter())
    L += table(["case"] + [f"{lab} ({mentions[lab]:,} mentions)" for lab in NAME_LABELS],
               [[c] + [f"{case[c][lab]:,} ({pct(case[c][lab], mentions[lab])})"
                       for lab in NAME_LABELS] for c in sorted(case)])

    with_decoys = sum(bool(r.get("_decoys")) for r in new)
    pii_free = sum(not r["entities"] for r in new)
    checks = [
        (not missing, f"all {len(ENTITY_TYPES)} labels in train"
                      + (f" (missing: {', '.join(missing)})" if missing else "")),
        (with_decoys >= 0.25 * len(new), f"decoys in ≥ 25% of new documents: {pct(with_decoys, len(new))}"),
        (0.07 <= pii_free / len(new) <= 0.13, f"PII-free ≈ 10% of new documents: {pct(pii_free, len(new))}"),
    ]
    L += ["## Checks", ""] + [f"- {'PASS' if ok else 'FAIL'}: {msg}" for ok, msg in checks]
    return "\n".join(L) + "\n", all(ok for ok, _ in checks)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-version", default="sprint1-v1")
    p.add_argument("--replay-n", type=int, default=60000, help="replay train documents (÷ 4 languages)")
    p.add_argument("--seed", type=int, default=20261001, help="split and replay sampling seed")
    p.add_argument("--targeted-n", type=int, default=37000,
                   help="D-57: 37,000 (v4.2 30,000, D-52d 28,000, D-20 25,000): the share-floor families keep their shares, the rest their counts, and the fix list's new content fits; smaller only for a smoke run")
    p.add_argument("--out-dir", type=Path, help="default: data/processed/<name>")
    p.add_argument("--az-only", action="store_true",
                   help="Run B (D-23b): old az documents in their own splits minus the drop list, no replay")
    p.add_argument("--drop-list", type=Path, default=DROP_LIST, help="P2-16's list, for --az-only")
    p.add_argument("--llm", type=Path, nargs="+", default=LLM,
                   help="clean LLM batches (default: data/raw/sprint1_llm_b1..b5.clean.jsonl)")
    p.add_argument("--v4-clean", action="store_true",
                   help="D-51f/D-51g: clean the old corpus, the LLM batches and the targeted file with "
                        "piigen.v4_clean (inputs untouched; cleaned copies in <out>/v4_clean_inputs/)")
    args = p.parse_args(argv)
    llm = [q.resolve() for q in args.llm]

    name = args.data_version.split("-")[0]
    out = (args.out_dir or ROOT / "data/processed" / name).resolve()
    az_dir = out.parent / f"{out.name}_az"
    targeted = ROOT / "data/raw" / f"{out.name}_targeted.jsonl"
    rel = lambda q: q.relative_to(ROOT).as_posix() if q.is_relative_to(ROOT) else str(q)  # noqa: E731

    inputs = [*llm, REPLAY / "train.docs.jsonl", REPLAY / "val.docs.jsonl", BENCH_V3]
    if args.az_only:
        inputs += [REPLAY / "test.docs.jsonl", args.drop_list.resolve()]
    pointers = [q for q in inputs
                if q.exists() and q.read_bytes()[:24] == b"version https://git-lfs"]
    if pointers:
        raise SystemExit("git-lfs pointers, run `git lfs checkout` on: "
                         + " ".join(rel(q) for q in pointers))
    if args.az_only:
        drop = read_drop_list(args.drop_list.resolve())    # stops now if it is missing

    # 1. targeted corpus
    run("scripts/build_targeted_corpus.py", "-n", str(args.targeted_n),
        "--seed", str(TARGETED_SEED), "-o", rel(targeted))

    # 1b. v4 cleaning (D-51f, D-51g): cleaned copies, the inputs untouched
    v4 = None
    v4_dir = out / "v4_clean_inputs"
    tag = ""
    if args.v4_clean:
        from piigen.v4_clean import Tally, clean_jsonl
        v4 = Tally()
        print(f"\nv4 cleaning -> {rel(v4_dir)}/", flush=True)
        targeted = clean_jsonl(targeted, v4_dir / targeted.name, v4, "targeted")
        llm = [clean_jsonl(q, v4_dir / q.name, v4, q.name.removesuffix(".clean.jsonl").replace("sprint1_", ""))
               for q in llm]
        tag = ".v4clean"

    # 2. gates
    (ROOT / "reports").mkdir(exist_ok=True)
    run("scripts/validate_corpus.py", rel(targeted), "--json", f"reports/validation_targeted{tag}.json")
    for q in llm:
        run("scripts/validate_corpus.py", rel(q), "--json",
            f"reports/validation_{q.name.removesuffix('.clean.jsonl')}{tag}.json")
    run("eval/leakage_guard.py", rel(targeted), *map(rel, llm), "--bench-docs", rel(BENCH_V3))

    # 3. split + D-19c
    run("scripts/prepare_splits.py", rel(targeted), *map(rel, llm), "--output-dir", rel(az_dir),
        "--no-tokenize", "--seed", str(args.seed), "--group-split", "template")
    az = {n: read_jsonl(az_dir / f"{n}.docs.jsonl") for n in SPLITS}
    new_split = sum(map(len, az.values()))
    moved = regroup(az)
    leak = leakage_report(az)
    bad = {f"{s}/{k}": v["shared"] for s, kinds in leak.items() for k, v in kinds.items()
           if k in ("exact_text", "normalized_text") and v["shared"]}
    if bad:
        raise SystemExit(f"STOPPED: document overlap after the D-19c move: {bad}")
    for n in SPLITS:
        write_jsonl(az_dir / f"{n}.docs.jsonl", az[n])
    (az_dir / "leakage_report.json").write_text(json.dumps(leak, indent=2), encoding="utf-8",
                                                 newline="\n")
    print(f"\nD-19c: moved {moved} documents to train; exact and normalised overlap now 0")

    # 4. mix
    rng = random.Random(args.seed)
    dropped: Counter = Counter()
    if args.az_only:
        old, dropped = read_old_az(REPLAY, drop, v4)
        mix = {n: az[n] + old[n] for n in SPLITS}
        dups = cross_split_dups(mix)
        if dups:
            raise SystemExit("STOPPED: normalised text in more than one split after adding the "
                             f"old documents (D-23b), per split pair: {dict(dups)}")
        print(f"\nD-23b: {sum(dropped.values()):,} old documents dropped; "
              "no normalised text in more than one split")
    else:
        mix = {"train": az["train"] + sample_replay(REPLAY / "train.docs.jsonl", args.replay_n, rng),
               "val": az["val"] + sample_replay(REPLAY / "val.docs.jsonl", REPLAY_VAL_N, rng),
               "test": az["test"]}
    out.mkdir(parents=True, exist_ok=True)
    for n in SPLITS:
        rng.shuffle(mix[n])
        write_jsonl(out / f"{n}.docs.jsonl", mix[n])

    # 5. tokenise
    run("scripts/prepare_splits.py", "--tokenize-only",
        *(rel(out / f"{n}.docs.jsonl") for n in SPLITS), "--base-model", "FacebookAI/xlm-roberta-large")
    shutil.copy(az_dir / "labels.json", out / "labels.json")

    # 6. data card
    new_in = sum(sum(1 for line in q.open(encoding="utf-8") if line.strip()) for q in [targeted, *llm])
    card, ok = data_card(out, mix, {
        "data_version": args.data_version, "sha": git_sha(), "seed": args.seed,
        "cmd": "python scripts/build_sprint_mix.py " + " ".join(argv if argv is not None else sys.argv[1:]),
        "targeted_n": args.targeted_n, "replay_n": args.replay_n,
        "new_in": new_in, "new_split": new_split, "moved": moved,
        "az_only": args.az_only, "dropped": dropped, "llm": llm, "drop_list": rel(args.drop_list.resolve()),
        "v4": v4, "v4_dir": rel(v4_dir), "v4_lexicon": v4_lexicon_sha() if v4 is not None else ""})
    (out / "DATA_CARD.md").write_text(card, encoding="utf-8", newline="\n")
    print("\n" + card + f"\nwrote {rel(out)}/ (docs, tokenised windows, labels.json, DATA_CARD.md)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
