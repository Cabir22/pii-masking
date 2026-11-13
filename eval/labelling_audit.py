"""P3-3a labelling check: does every entity get a `B-` tag?

Tokenises a sample of a corpus exactly as scripts/prepare_splits.py does
(tokenize_split: the patched fast tokenizer from add_punctuation_boundary,
max_length 512, stride 256, overflowing windows) and labels every window
with the real align_labels_for_window. Then, per label:

  (a) no_token_at_start   no token starts at entity.start: the entity
                          starts mid-token, so align gives it no B-
  (a') no_B               in some window that holds the entity's first
                          token, that token is not B-<label> (the effect
                          of (a) on the training labels, measured directly)
  (b) end_mid_token       a token straddles entity.end: the entity's last
                          token runs past it, so the model can't stop there
  (c) whitespace_multi    entities with whitespace/newlines inside and more
                          than one token (spaced phones, cards, IBANs, PEM),
                          and how many of them have ALL their tokens tagged
                          B/I of their own label, B first, in every window

Slices for the RC8/RC9 cases (D-9: a case suffix is inside the span):
  suffixed      GIVENNAME/SURNAME/CITY/STREET values that are another gold
                value of the same label plus an Azerbaijani case suffix
                (e.g. `Bakıda` when `Bakı` is also labelled), or with an
                apostrophe suffix (`Əsgər'in`)
  punct_after   the character right after the entity is punctuation
                (`Fidan.`, `(Fidan)`)
  short_doc     the document has at most 5 words (bare names)
  declared_suffix
                an entity the generator declared as inflected in the
                record's `_suffixes` (C2, P2-4c), by its surface: plain,
                apostrophe, folded or noisy (a misspelt suffix, `Bakıdə`).
                Exact where `suffixed` guesses; absent from corpora that do
                not declare suffixes (P2-12)
Plus a fixed set of hand-written minimal cases (own sentences, not the
generator's), each checked token by token.

Run:  python eval/labelling_audit.py [--n 20000] [--seed 13]
          [--corpus data/processed/merged_relabeled_swept/train.docs.jsonl]
          [--json out.json] [--md out.md]
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

DEFAULT_CORPUS = ROOT / "data" / "processed" / "merged_relabeled_swept" / "train.docs.jsonl"
TOKENIZER = "FacebookAI/xlm-roberta-large"  # model/train.py's base; same SentencePiece as ckpt 1
THRESHOLD = 0.005
NAME_LABELS = ("GIVENNAME", "SURNAME", "CITY", "STREET")
# Azerbaijani case suffixes (with vowel-harmony and buffer-consonant forms),
# longest first so `-dakı` wins over `-ı`. Written for this audit, not taken
# from the generator.
SUFFIXES = sorted({
    "da", "də", "ta", "tə", "dan", "dən", "tan", "tən",
    "ın", "in", "un", "ün", "nın", "nin", "nun", "nün",
    "a", "ə", "ya", "yə", "ı", "i", "u", "ü", "nı", "ni", "nu", "nü",
    "la", "lə", "yla", "ylə", "dakı", "dəki", "takı", "təki",
    "lar", "lər", "ların", "lərin", "lara", "lərə", "larda", "lərdə",
    "lardan", "lərdən", "dır", "dir", "dur", "dür", "dı", "di",
}, key=len, reverse=True)
PUNCT = re.compile(r"[^\w\s]", re.UNICODE)

# Hand-written minimal cases: (text, [(value, label)]). Offsets are found
# by value, so every span is exactly value + suffix (D-9).
MINIMAL_CASES = [
    ("Fidan.", [("Fidan", "GIVENNAME")]),
    ("Fidan!", [("Fidan", "GIVENNAME")]),
    ("(Fidan)", [("Fidan", "GIVENNAME")]),
    ('"Fidan"', [("Fidan", "GIVENNAME")]),
    ("Fidan Məmmədova", [("Fidan", "GIVENNAME"), ("Məmmədova", "SURNAME")]),
    ("Salam, Fidan!", [("Fidan", "GIVENNAME")]),
    ("Hörmətlə, Fidan Məmmədova", [("Fidan", "GIVENNAME"), ("Məmmədova", "SURNAME")]),
    ("— Fidan", [("Fidan", "GIVENNAME")]),
    ("Bakıda yaşayıram.", [("Bakıda", "CITY")]),
    ("Bakını gördüm.", [("Bakını", "CITY")]),
    ("Bakıdakı ofis bağlıdır.", [("Bakıdakı", "CITY")]),
    ("Gəncədən gəldim.", [("Gəncədən", "CITY")]),
    ("Əsgərin kitabı buradadır.", [("Əsgərin", "GIVENNAME")]),
    ("Əsgəri çağırdım.", [("Əsgəri", "GIVENNAME")]),
    ("Əsgərlə danışdım.", [("Əsgərlə", "GIVENNAME")]),
    ("Əsgərdən məktub gəldi.", [("Əsgərdən", "GIVENNAME")]),
    ("Əsgər'in sənədi hazırdır.", [("Əsgər'in", "GIVENNAME")]),
    ("Məmmədovlar gəldi.", [("Məmmədovlar", "SURNAME")]),
    ("Məmmədovların evi", [("Məmmədovların", "SURNAME")]),
    ("Nizami küçəsində görüşək.", [("Nizami küçəsində", "STREET")]),
    ("Nizami küçəsindən keçdik.", [("Nizami küçəsindən", "STREET")]),
    ("Bakida yasayiram.", [("Bakida", "CITY")]),
    ("Esgerden mektub geldi.", [("Esgerden", "GIVENNAME")]),
    ("Tel: +994 50 123 45 67.", [("+994 50 123 45 67", "TELEPHONENUM")]),
    ("Kart 4169 7388 1234 5678, müddət 12/27", [("4169 7388 1234 5678", "PAYMENT_CARD_NUMBER")]),
    ("IBAN: AZ21 NABZ 0000 0000 1370 1000 1944", [("AZ21 NABZ 0000 0000 1370 1000 1944", "IBAN")]),
]


def load_sample(path: Path, n: int, seed: int) -> list[dict]:
    """A seeded random sample of n records, in two streaming passes (count,
    then read the chosen lines), so a 600 MB corpus never sits in memory."""
    with open(path, "rb") as fh:
        total = sum(1 for line in fh if line.strip())
    pick = set(random.Random(seed).sample(range(total), min(n, total)))
    out = []
    with open(path, encoding="utf-8") as fh:
        i = 0
        for line in fh:
            if not line.strip():
                continue
            if i in pick:
                out.append(json.loads(line))
            i += 1
    return out


def suffix_kind(value: str, label: str, bare: dict[str, set[str]]) -> str | None:
    """'apostrophe' / 'case' / None. A value is suffixed when stripping one
    known suffix leaves another gold value of the same label, so plain names
    that merely end in `-a` (`Leyla`) are not counted."""
    if "'" in value or "’" in value:
        return "apostrophe"
    last = value.split()[-1] if value.split() else value
    head = value[: len(value) - len(last)]
    for suf in SUFFIXES:
        if len(last) > len(suf) + 1 and last.endswith(suf):
            if head + last[: -len(suf)] in bare[label]:
                return "case"
    return None


def audit_entity(text: str, e: dict, windows: list[tuple[list, list[int]]],
                 id2label: dict[int, str]) -> dict:
    """Per-entity flags across every window of its document."""
    starts, straddle_end = False, False
    first_tok_seen = False
    no_b = False
    consistent = True
    n_tokens = 0
    for offsets, labels in windows:
        toks = [(i, s, t) for i, (s, t) in enumerate(offsets)
                if s != t and s < e["end"] and t > e["start"]]
        for _, s, t in toks:
            if s == e["start"]:
                starts = True
            if s < e["end"] < t:
                straddle_end = True
        if not toks:
            continue
        n_tokens = max(n_tokens, len(toks))
        first_i, first_s, _ = toks[0]
        holds_first = first_s <= e["start"]  # this window holds the entity's first token
        if holds_first:
            first_tok_seen = True
            if id2label[labels[first_i]] != f"B-{e['label']}":
                no_b = True
        for j, (i, _, _) in enumerate(toks):
            want = ("B" if (j == 0 and holds_first) else "I") + "-" + e["label"]
            if id2label[labels[i]] != want:
                consistent = False
    return {"no_token_at_start": not starts, "no_B": no_b or not first_tok_seen,
            "end_mid_token": straddle_end, "n_tokens": n_tokens,
            "whitespace_inside": bool(re.search(r"\s", text[e["start"]:e["end"]])),
            "all_tokens_consistent": consistent}


def run(records: list[dict], tokenizer, label2id, max_length=512, stride=256) -> dict:
    from prepare_splits import align_labels_for_window
    id2label = {i: l for l, i in label2id.items()}

    bare: dict[str, set[str]] = defaultdict(set)
    for r in records:
        for e in r["entities"]:
            if e["label"] in NAME_LABELS:
                bare[e["label"]].add(r["text"][e["start"]:e["end"]])

    per: dict[str, Counter] = defaultdict(Counter)
    sl: dict[tuple, Counter] = defaultdict(Counter)
    examples: dict[str, list] = defaultdict(list)
    for r in records:
        text = r["text"]
        enc = tokenizer(text, return_offsets_mapping=True, return_overflowing_tokens=True,
                        truncation=True, max_length=max_length, stride=stride)
        windows = [(enc["offset_mapping"][w],
                    align_labels_for_window(enc["offset_mapping"][w], r["entities"], label2id))
                   for w in range(len(enc["input_ids"]))]
        short = len(text.split()) <= 5
        declared = {(x["start"], x["end"]): x.get("surface", "plain")
                    for x in r.get("_suffixes") or [] if isinstance(x, dict)}
        for e in r["entities"]:
            f = audit_entity(text, e, windows, id2label)
            c = per[e["label"]]
            c["entities"] += 1
            for k in ("no_token_at_start", "no_B", "end_mid_token"):
                c[k] += f[k]
            if f["whitespace_inside"] and f["n_tokens"] > 1:
                c["ws_multi"] += 1
                c["ws_multi_consistent"] += f["all_tokens_consistent"]
            c["all_consistent"] += f["all_tokens_consistent"]
            for k in ("no_token_at_start", "end_mid_token", "no_B"):
                if f[k] and len(examples[f"{e['label']}:{k}"]) < 3:
                    examples[f"{e['label']}:{k}"].append(
                        {"doc": r["id"], "left": text[max(0, e["start"] - 6):e["start"]],
                         "span": text[e["start"]:e["end"]], "right": text[e["end"]:e["end"] + 6]})
            keys = []
            if e["label"] in NAME_LABELS:
                sk = suffix_kind(text[e["start"]:e["end"]], e["label"], bare)
                keys.append(("suffixed", sk or "no"))
            nxt = text[e["end"]:e["end"] + 1]
            keys.append(("punct_after", "yes" if nxt and PUNCT.match(nxt) else "no"))
            if short:
                keys.append(("short_doc", "yes"))
            if (e["start"], e["end"]) in declared:
                keys.append(("declared_suffix", declared[(e["start"], e["end"])]))
            for key in keys:
                s = sl[(e["label"], *key)]
                s["entities"] += 1
                for k in ("no_token_at_start", "no_B", "end_mid_token"):
                    s[k] += f[k]
    return {"per_label": {l: dict(c) for l, c in sorted(per.items())},
            "slices": {"|".join(k): dict(v) for k, v in sorted(sl.items())},
            "examples": dict(examples)}


def minimal_cases(tokenizer, label2id) -> list[dict]:
    from prepare_splits import align_labels_for_window
    id2label = {i: l for l, i in label2id.items()}
    out = []
    for text, spans in MINIMAL_CASES:
        ents = []
        for value, label in spans:
            s = text.index(value)
            ents.append({"start": s, "end": s + len(value), "label": label})
        enc = tokenizer(text, return_offsets_mapping=True, truncation=True, max_length=512)
        labels = align_labels_for_window(enc["offset_mapping"], ents, label2id)
        toks = [(text[s:t], id2label[l]) for (s, t), l in zip(enc["offset_mapping"], labels) if s != t]
        flags = [audit_entity(text, e, [(enc["offset_mapping"], labels)], id2label) for e in ents]
        out.append({"text": text, "tokens": toks,
                    "ok": all(not f["no_token_at_start"] and not f["no_B"]
                              and not f["end_mid_token"] and f["all_tokens_consistent"]
                              for f in flags)})
    return out


def _pct(n, d):
    return f"{100 * n / d:.3f}" if d else "–"


def render_md(res: dict, meta: dict) -> str:
    L = ["# P3-3a labelling check", "",
         f"Corpus `{meta['corpus']}` (SHA-256 `{meta['corpus_sha256'][:16]}…`), "
         f"{meta['documents']} documents sampled (seed {meta['seed']}), tokenizer "
         f"`{meta['tokenizer']}` + `add_punctuation_boundary`, max_length {meta['max_length']} / "
         f"stride {meta['stride']}, labels from `prepare_splits.align_labels_for_window` "
         f"(git `{meta['git_sha'][:10]}`). Threshold {THRESHOLD * 100:.1f}% for (a) and (b).", "",
         "| Label | Entities | (a) no token at start % | (a') no B- % | (b) end mid-token % | "
         "(c) whitespace multi-token | (c) all B/I same label | Over 0.5%? |",
         "|---|---|---|---|---|---|---|---|"]
    for lab, c in res["per_label"].items():
        n = c["entities"]
        over = c["no_token_at_start"] / n > THRESHOLD or c["end_mid_token"] / n > THRESHOLD
        L.append(f"| {lab} | {n} | {_pct(c['no_token_at_start'], n)} ({c['no_token_at_start']}) | "
                 f"{_pct(c['no_B'], n)} ({c['no_B']}) | {_pct(c['end_mid_token'], n)} "
                 f"({c['end_mid_token']}) | {c.get('ws_multi', 0)} | "
                 f"{c.get('ws_multi_consistent', 0)}/{c.get('ws_multi', 0)} | "
                 f"{'**YES**' if over else 'no'} |")
    L += ["", "## Slices (RC8 suffixed, RC9 punctuation-touching and bare names)", "",
          "| Label | Slice | Value | Entities | (a) % | (a') % | (b) % |", "|---|---|---|---|---|---|---|"]
    for key, c in res["slices"].items():
        lab, sk, val = key.split("|")
        if sk == "punct_after" and val == "no":
            continue
        n = c["entities"]
        L.append(f"| {lab} | {sk} | {val} | {n} | {_pct(c['no_token_at_start'], n)} | "
                 f"{_pct(c['no_B'], n)} | {_pct(c['end_mid_token'], n)} |")
    L += ["", "## Hand-written minimal cases", "",
          "| Text | Tokens (label) | OK |", "|---|---|---|"]
    for m in res["minimal"]:
        toks = " ".join(f"`{t}`:{l}" for t, l in m["tokens"])
        L.append(f"| `{m['text']}` | {toks} | {'yes' if m['ok'] else '**NO**'} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    import hashlib
    import subprocess
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--n", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--tokenizer", default=TOKENIZER)
    ap.add_argument("--max-length", type=int, default=512)
    ap.add_argument("--stride", type=int, default=256)
    ap.add_argument("--json", default=None)
    ap.add_argument("--md", default=None)
    args = ap.parse_args(argv)

    from transformers import AutoTokenizer
    from prepare_splits import add_punctuation_boundary, build_label_list
    tok = AutoTokenizer.from_pretrained(args.tokenizer)
    if not add_punctuation_boundary(tok):
        raise SystemExit("no fast tokenizer: cannot apply the punctuation-boundary patch")
    label2id = {l: i for i, l in enumerate(build_label_list())}

    corpus = Path(args.corpus)
    h = hashlib.sha256()
    with open(corpus, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    records = load_sample(corpus, args.n, args.seed)
    print(f"{len(records)} documents from {corpus.name}")
    res = run(records, tok, label2id, args.max_length, args.stride)
    res["minimal"] = minimal_cases(tok, label2id)
    meta = {"corpus": str(corpus.relative_to(ROOT)) if corpus.is_relative_to(ROOT) else str(corpus),
            "corpus_sha256": h.hexdigest(), "documents": len(records), "seed": args.seed,
            "tokenizer": args.tokenizer, "max_length": args.max_length, "stride": args.stride,
            "git_sha": subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                                      capture_output=True, text=True).stdout.strip()}
    res["meta"] = meta
    over = [l for l, c in res["per_label"].items()
            if c["no_token_at_start"] / c["entities"] > THRESHOLD
            or c["end_mid_token"] / c["entities"] > THRESHOLD]
    res["labels_over_threshold"] = over
    md = render_md(res, meta)
    print(md)
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    if args.md:
        Path(args.md).write_text(md, encoding="utf-8")
    print("labelling clean" if not over else f"over {THRESHOLD * 100:.1f}%: {', '.join(over)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
