"""Phase-0 smoke test for the Russian carrier translation (translate/ru).

Per the translation design (2026-09-03, section 10) this runs BEFORE any of the
shared harness is built: a handful of varied Azerbaijani documents, one or two
per length bucket, sentinelized by hand and pushed through Wahoo, then checked
by eye for slot survival, faithfulness and register preservation. If Wahoo
mangles the ``⟦N⟧`` sentinels on ten documents it will mangle them on eighty
thousand, and the whole harness would have been built on a false assumption.

This is deliberately NOT the harness. No SIMURG, no repair queue, no
re-splicing with freshly minted PII, no round-trip validator. It only answers
one question: does ``wahoo-1.5-preview`` carry the sentinels across a
Russian translation intact?

Two modes:

* ``--prepare`` (default when COMPANY_API_KEY is unset) -- select and
  sentinelize the sample, run the offline re-splice self-check that proves the
  sentineliser is offset-exact, and write the batch to
  ``scratch/ru_phase0_batch.jsonl`` for a later ``--run``.
* ``--run`` (needs COMPANY_API_KEY) -- also translate each slotted text via
  Wahoo, check the returned slot set equals the slot set sent, and write
  ``scratch/ru_phase0_results.jsonl`` plus a human-readable summary.

Usage::

    python scripts/translate/smoke_test_ru.py                       # prepare only
    export COMPANY_API_KEY='...'                            # bash/zsh
    $env:COMPANY_API_KEY='...'                              # PowerShell
    python scripts/translate/smoke_test_ru.py --run
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from piigen.sentinel import (       # noqa: E402
    SENT_CLOSE, SENT_OPEN, SlotError, resplice, sentinelize, slot_set,
)

REPO = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO / "data" / "processed" / "az" / "val.docs.jsonl"
SCRATCH = REPO / "scratch"

# Bands as defined in scripts/piigen/llm/specs.py LENGTH_BANDS. Ordered short
# to long so the sample reads top-to-bottom by size.
BUCKETS = ["very_short", "short", "medium", "long", "very_long", "extreme"]

MODEL = "wahoo-1.5-preview"
ENV_KEY = "COMPANY_API_KEY"
LEGACY_ENV_KEY = "HALX_API_KEY"
ENV_BASE_URL = "COMPANY_API_BASE_URL"
DEFAULT_BASE_URL = "https://api.hal-x.ai/v1"

# Draft translation prompt. The spec calls for a short four-bullet instruction,
# not a DSPy signature: one string in, one string out. Register preservation
# and sentinel survival are the two things being smoke-tested here, so both are
# stated explicitly.
SYSTEM_PROMPT = (
    "You translate Azerbaijani business text into natural, fluent Russian.\n"
    "\n"
    "Rules:\n"
    f"- Keep every {SENT_OPEN}N{SENT_CLOSE} marker exactly as written "
    "(same digits), keep the same number of them, never translate, duplicate "
    "or drop one. Move a marker only where Russian word order requires it.\n"
    "- Preserve the register and tone of the source (formal, frustrated, "
    "terse, etc.) and keep the layout: line breaks, headings, log lines, "
    "tables, list markers.\n"
    "- Do not translate or reformat anything that is not prose: numbers, "
    "codes, IDs, emails, URLs, timestamps. Leave OCR-style noise and typos "
    "as they are; do not tidy them.\n"
    "- Output only the translated text. No preamble, no notes, no quoting.\n"
)


def eprint(*a: object) -> None:
    print(*a, file=sys.stderr)


# --------------------------------------------------------------------------- #
# sample selection
# --------------------------------------------------------------------------- #
def select_docs(path: Path, per_bucket: int, min_entities: int, seed: int) -> list[dict]:
    """One-pass reservoir-ish pick: ``per_bucket`` positive docs per length
    bucket, preferring a spread of ``_doc_type``. Deterministic under ``seed``.
    """
    rng = random.Random(seed)
    by_bucket: dict[str, list[dict]] = {b: [] for b in BUCKETS}
    with path.open(encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            ents = d.get("entities") or []
            if len(ents) < min_entities:
                continue
            b = d.get("_bucket")
            if b in by_bucket:
                by_bucket[b].append(d)

    picked: list[dict] = []
    for b in BUCKETS:
        pool = by_bucket[b]
        rng.shuffle(pool)
        # spread doc types: take the first doc of each unseen type, then top up
        seen_types: set[str] = set()
        chosen: list[dict] = []
        for d in pool:
            dt = d.get("_doc_type")
            if dt not in seen_types:
                chosen.append(d)
                seen_types.add(dt)
            if len(chosen) == per_bucket:
                break
        for d in pool:
            if len(chosen) == per_bucket:
                break
            if d not in chosen:
                chosen.append(d)
        if not chosen:
            eprint(f"WARNING: no positive doc with >= {min_entities} entities in bucket {b!r}")
        picked.extend(chosen)
    return picked


# --------------------------------------------------------------------------- #
# translation (only used by --run)
# --------------------------------------------------------------------------- #
def translate(slotted: str, *, api_key: str, base_url: str,
              temperature: float, max_tokens: int) -> str:
    """Stream one Russian translation from Wahoo. Streaming (rather than a
    single response) is what the real harness needs for the SIMURG guard, so
    the smoke test exercises the same path.
    """
    import litellm

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": slotted},
    ]
    stream = litellm.completion(
        model=f"openai/{MODEL}",
        messages=messages,
        api_key=api_key,
        api_base=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
        # wahoo-1.5-preview is a "thinking" model: without this it spends the
        # whole token budget in a reasoning channel and returns empty content
        # (docs/audit_llm_augmentation.md F10/F11).
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    chunks: list[str] = []
    for part in stream:
        try:
            delta = part.choices[0].delta.content
        except (AttributeError, IndexError):
            delta = None
        if delta:
            chunks.append(delta)
    return "".join(chunks).strip()


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                    help=f"source .docs.jsonl (default: {DEFAULT_INPUT.relative_to(REPO)})")
    ap.add_argument("--per-bucket", type=int, default=2,
                    help="documents per length bucket (default 2 -> ~12 docs)")
    ap.add_argument("--min-entities", type=int, default=2,
                    help="skip docs with fewer entities (default 2)")
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--run", action="store_true",
                    help="also translate via Wahoo (needs COMPANY_API_KEY)")
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--max-tokens", type=int, default=8192)
    args = ap.parse_args(argv)

    if not args.input.exists():
        eprint(f"input not found: {args.input}")
        return 2

    SCRATCH.mkdir(exist_ok=True)
    docs = select_docs(args.input, args.per_bucket, args.min_entities, args.seed)
    if not docs:
        eprint("no documents selected")
        return 2

    batch: list[dict] = []
    resplice_failures = 0
    for d in docs:
        try:
            slotted, labels, values = sentinelize(d["text"], d["entities"])
        except SlotError as exc:
            eprint(f"SKIP {d['id']} ({d.get('_bucket')}): {exc}")
            continue
        ok = resplice(slotted, values) == d["text"]
        if not ok:
            resplice_failures += 1
            eprint(f"RESPLICE FAIL {d['id']}: sentineliser is not offset-exact")
        batch.append({
            "id": d["id"],
            "bucket": d.get("_bucket"),
            "doc_type": d.get("_doc_type"),
            "register": d.get("_register"),
            "n_slots": len(labels),
            "slot_labels": labels,
            "slot_values": values,
            "source_text": d["text"],
            "slotted_text": slotted,
        })

    batch_path = SCRATCH / "ru_phase0_batch.jsonl"
    with batch_path.open("w", encoding="utf-8") as f:
        for row in batch:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"selected {len(batch)} documents across {len({r['bucket'] for r in batch})} buckets")
    for r in batch:
        print(f"  {r['bucket']:<10} {r['id']:<34} slots={r['n_slots']:<3} "
              f"{r['doc_type']}")
    print(f"\noffline re-splice self-check: "
          f"{len(batch) - resplice_failures}/{len(batch)} offset-exact")
    print(f"batch written to {batch_path.relative_to(REPO)}")

    if not args.run:
        key = os.environ.get(ENV_KEY) or os.environ.get(LEGACY_ENV_KEY)
        if not key:
            print(f"\n{ENV_KEY} is not set -- prepare-only. To translate:")
            print(f"    $env:{ENV_KEY}='...'      # PowerShell")
            print(f"    python scripts/translate/smoke_test_ru.py --run")
        else:
            print("\n(key is set; re-run with --run to translate)")
        return 1 if resplice_failures else 0

    key = os.environ.get(ENV_KEY) or os.environ.get(LEGACY_ENV_KEY)
    if not key:
        eprint(f"--run needs {ENV_KEY} (or {LEGACY_ENV_KEY}) in the environment")
        return 2
    base_url = (os.environ.get(ENV_BASE_URL) or DEFAULT_BASE_URL).rstrip("/")

    print(f"\ntranslating {len(batch)} documents via {MODEL} at {base_url} ...\n")
    results: list[dict] = []
    slot_ok = 0
    for r in batch:
        sent = slot_set(r["slotted_text"])
        try:
            ru = translate(r["slotted_text"], api_key=key, base_url=base_url,
                           temperature=args.temperature, max_tokens=args.max_tokens)
        except Exception as exc:  # noqa: BLE001 - smoke test, surface everything
            eprint(f"  {r['id']}: translation error: {exc!r}")
            results.append({**r, "ru_text": None, "error": repr(exc),
                            "slots_ok": False})
            continue
        got = slot_set(ru)
        ok = got == sent
        slot_ok += ok
        status = "OK  " if ok else "FAIL"
        detail = "" if ok else f"  sent={sorted(sent)} got={sorted(got)}"
        print(f"  [{status}] {r['bucket']:<10} {r['id']:<34} "
              f"slots {len(sent)}->{len(got)}{detail}")
        results.append({**r, "ru_text": ru, "slots_ok": ok,
                        "slots_sent": sorted(sent), "slots_got": sorted(got)})

    res_path = SCRATCH / "ru_phase0_results.jsonl"
    with res_path.open("w", encoding="utf-8") as f:
        for row in results:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"\nslot survival: {slot_ok}/{len(batch)} documents")
    print(f"results written to {res_path.relative_to(REPO)}")
    print("NEXT: read ru_phase0_results.jsonl by eye -- Russian fluency, "
          "register match, structured data untouched, noise left alone.")
    return 0 if slot_ok == len(batch) and not resplice_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
