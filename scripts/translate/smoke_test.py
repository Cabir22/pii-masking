"""Phase-0.5 smoke test: does Wahoo preserve ⟦N⟧ sentinels across a translation?

The whole harness assumes that when we hand Wahoo carrier text with the PII
cut out and replaced by ⟦0⟧, ⟦1⟧, ..., it hands back the translation with
those tokens intact. Nothing has actually verified that yet. This script does,
on a handful of real documents, before 500 lines of harness get built on top.

It is a DEV TOOL, not part of the pipeline -- re-run it while tuning the
translation prompt.

Usage:
    export COMPANY_API_KEY=...
    python scripts/translate/smoke_test.py                 # ~12 docs, en
    python scripts/translate/smoke_test.py --n 2 --lang tr
    python scripts/translate/smoke_test.py --think         # leave reasoning on
    python scripts/translate/smoke_test.py --no-stream-check

What to read in the output:
  1. slots  -- did every ⟦N⟧ come back, right count, unmangled?
  2. faithful -- is it a translation, or did Wahoo paraphrase / summarise /
     prepend "Here is the translation:"?
  3. register -- did the terse one-line log stay terse?
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate.sentinel import check_round_trip, found_slots, sentinelize  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
AZ_DOCS = ROOT / "data" / "processed" / "az" / "train.docs.jsonl"

DEFAULT_BASE_URL = "https://api.hal-x.ai/v1"
DEFAULT_MODEL = "wahoo-1.5-preview"
LANG_NAME = {"en": "English", "tr": "Turkish", "ru": "Russian"}

BUCKETS = ["very_short", "short", "medium", "long", "very_long", "extreme"]

# --- draft translation prompt (this is the artifact being tuned) ----------

def build_messages(templated: str, lang: str) -> list[dict]:
    target = LANG_NAME[lang]
    system = (
        f"You are a professional translator. Translate the user's text from "
        f"Azerbaijani into {target}.\n"
        f"Rules:\n"
        f"- Translate faithfully, sentence for sentence. Do not paraphrase, "
        f"summarise, add, or omit anything.\n"
        f"- The text contains placeholder tokens of the form ⟦N⟧ "
        f"(e.g. ⟦0⟧, ⟦1⟧). Reproduce every one EXACTLY: "
        f"same count, same numbers, same ⟦ ⟧ characters. Do not "
        f"translate, renumber, space out, or drop them.\n"
        f"- Keep the register and tone of the source (a terse log line stays "
        f"terse; a formal notice stays formal).\n"
        f"- Output ONLY the translation. No preamble, no notes, no quotes."
    )
    return [{"role": "system", "content": system},
            {"role": "user", "content": templated}]


# --- client --------------------------------------------------------------

def make_client(base_url: str | None):
    from openai import OpenAI
    key = (os.environ.get("COMPANY_API_KEY") or os.environ.get("HALX_API_KEY"))
    if not key:
        sys.exit("error: export COMPANY_API_KEY (or HALX_API_KEY) first")
    url = (base_url or os.environ.get("COMPANY_API_BASE_URL")
           or DEFAULT_BASE_URL).rstrip("/")
    return OpenAI(api_key=key, base_url=url), url


def _extra_body(think: bool) -> dict:
    # wahoo-1.5-preview is a thinking model; left on, it spends the token
    # budget in a reasoning channel and can return content=None. Translation
    # needs no reasoning.
    if think:
        return {}
    return {"chat_template_kwargs": {"enable_thinking": False}}


def translate(client, model: str, templated: str, lang: str, *,
              think: bool, max_tokens: int) -> tuple[str, float]:
    t0 = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=build_messages(templated, lang),
        temperature=0.2,
        max_tokens=max_tokens,
        extra_body=_extra_body(think),
    )
    return (resp.choices[0].message.content or ""), time.time() - t0


def stream_probe(client, model: str, lang: str, think: bool) -> tuple[bool, int, str]:
    """Confirm the endpoint streams text deltas (SIMURG-live depends on it)."""
    templated = "Salam. Sifariş nömrəniz ⟦0⟧. Təşəkkür edirik."
    try:
        stream = client.chat.completions.create(
            model=model, messages=build_messages(templated, lang),
            temperature=0.2, max_tokens=200, stream=True,
            extra_body=_extra_body(think),
        )
        chunks, text = 0, []
        for ev in stream:
            delta = ev.choices[0].delta.content if ev.choices else None
            if delta:
                chunks += 1
                text.append(delta)
        return chunks > 1, chunks, "".join(text)
    except Exception as exc:  # noqa: BLE001
        return False, 0, f"{type(exc).__name__}: {exc}"


# --- sampling -----------------------------------------------------------

def sample_docs(n_per_bucket: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_bucket: dict[str, list[dict]] = defaultdict(list)
    with AZ_DOCS.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("entities"):                       # positives only here
                by_bucket[r.get("_bucket", "?")].append(r)
    picked: list[dict] = []
    for b in BUCKETS:
        pool = by_bucket.get(b, [])
        rng.shuffle(pool)
        picked.extend(pool[:n_per_bucket])
    return picked


# --- reporting --------------------------------------------------------

def looks_like_preamble(s: str) -> bool:
    head = s.lstrip()[:60].lower()
    return head.startswith(("here is", "here's", "translation:", "sure,",
                            "the translation", "certainly"))


def clip(s: str, n: int = 320) -> str:
    s = s.replace("\n", " ↵ ")
    return s if len(s) <= n else s[:n] + " …"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lang", default="en", choices=["en", "tr", "ru"])
    ap.add_argument("--n", type=int, default=2, help="docs per length bucket")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=os.environ.get("COMPANY_MODEL", DEFAULT_MODEL))
    ap.add_argument("--base-url", default=None)
    ap.add_argument("--think", action="store_true",
                    help="leave the model's reasoning channel on")
    ap.add_argument("--no-stream-check", action="store_true")
    ap.add_argument("--full", action="store_true",
                    help="print full source/translation, not clipped")
    args = ap.parse_args()

    if not AZ_DOCS.exists():
        sys.exit(f"error: {AZ_DOCS} not found")

    client, url = make_client(args.base_url)
    print(f"endpoint {url}  model {args.model}  lang az->{args.lang}  "
          f"thinking={'on' if args.think else 'off'}\n")

    if not args.no_stream_check:
        ok, nchunks, sample = stream_probe(client, args.model, args.lang, args.think)
        verdict = "OK" if ok else "NOT STREAMING"
        print(f"[stream probe] {verdict} -- {nchunks} delta chunk(s)")
        if not ok:
            print(f"               {sample}")
        print()

    docs = sample_docs(args.n, args.seed)
    rows = []
    for k, r in enumerate(docs, 1):
        templated, labels = sentinelize(r["text"], r["entities"])
        n = len(labels)
        budget = min(8000, 400 + len(templated))
        try:
            out, secs = translate(client, args.model, templated, args.lang,
                                   think=args.think, max_tokens=budget)
        except Exception as exc:  # noqa: BLE001
            print(f"--- {k}. {r['_bucket']:<10} {r['id']}   CALL FAILED: "
                  f"{type(exc).__name__}: {exc}\n")
            rows.append((r["_bucket"], n, "CALL FAILED", False, False))
            continue

        slots_ok, reason = check_round_trip(out, n)
        ratio = (len(out) / max(1, len(templated)))
        pre = looks_like_preamble(out)
        faithful = (0.5 <= ratio <= 2.2) and not pre

        print(f"--- {k}. {r['_bucket']:<10} {r['id']}   "
              f"{n} slot(s)   {secs:.1f}s   len {len(r['text'])}->{len(out)}")
        src = r["text"] if args.full else clip(r["text"])
        tsl = out if args.full else clip(out)
        print(f"    SÉ  {clip(templated) if not args.full else templated}")
        print(f"    EN  {tsl}")
        flags = []
        flags.append(f"slots={'ok' if slots_ok else 'FAIL: ' + reason}")
        flags.append(f"len-ratio={ratio:.2f}")
        if pre:
            flags.append("PREAMBLE")
        print(f"    ->  {'  '.join(flags)}\n")
        rows.append((r["_bucket"], n, "ok" if slots_ok else reason,
                     slots_ok, faithful))

    # summary
    total = len(rows)
    slot_pass = sum(1 for *_, s, _ in rows if s)
    faith_pass = sum(1 for *_, f in rows if f)
    print("=" * 60)
    print(f"docs: {total}   slots survived: {slot_pass}/{total}   "
          f"faithful-ish: {faith_pass}/{total}")
    bad = [f"{b} ({r})" for b, _, r, s, _ in rows if not s]
    if bad:
        print("slot failures: " + "; ".join(bad))
    print("=" * 60)
    print("\nNow read the EN lines yourself: real translation, or paraphrase?"
          " Did terse stay terse?")
    return 0 if slot_pass == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
