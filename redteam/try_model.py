"""Try the Azerbaijani model on a sentence, and save it as a finding if it fails.

The red-team tool. It runs the product decoding
(track M: model/predict.py's _detect_entities_word_consistent, the validity check
included), which is what users get.

  # see what the model masks
  python redteam/try_model.py "Mən Elvin Məmmədov, Gəncədə yaşayıram."

  # save a failure to redteam/findings/findings.csv (the model's output is filled in automatically)
  python redteam/try_model.py "..." --save --area names \
      --expect "Elvin=GIVENNAME; Məmmədov=SURNAME; Gəncədə=CITY" \
      --problem missed --note "surname before a comma"

  # type sentences one by one (empty line ends)
  python redteam/try_model.py

The first run downloads the model from Hugging Face (needs `hf auth login` and access
to the model repo). Use transformers 4.57.x / tokenizers 0.22.x, as the scoreboard does.
Never put a real person's data in a sentence: make every value up.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))

MODEL = "your-hf-org/masking-az-runb-v4.2-seed42"
REVISION = "223e54e8799dc60f6f6b19362191cf7c10c774c7"
FINDINGS = ROOT / "redteam" / "findings" / "findings.csv"
COLUMNS = ["id", "date", "area", "language", "text", "expected", "model_output",
           "problem", "note", "model", "split"]
PROBLEMS = ("missed", "partly_masked", "wrong_type", "false_alarm", "other")


def _show(text: str, spans: list[dict]) -> str:
    out, last = [], 0
    for s in sorted(spans, key=lambda s: s["start"]):
        out += [text[last:s["start"]], f"⟦{text[s['start']:s['end']]}|{s['label']}⟧"]
        last = s["end"]
    return "".join(out + [text[last:]])


def _next_id(rows: list[dict]) -> str:
    prefix = "RT-"
    nums = [int(r["id"][len(prefix):]) for r in rows if r.get("id", "").startswith(prefix)]
    return f"{prefix}{max(nums, default=0) + 1:04d}"


def save(text: str, spans: list[dict], args) -> str:
    path = FINDINGS
    rows = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    row = {
        "id": _next_id(rows), "date": dt.date.today().isoformat(),
        "area": args.area, "language": args.language, "text": text,
        "expected": args.expect,
        "model_output": "; ".join(f"{s['text']}={s['label']}" for s in spans) or "(nothing)",
        "problem": args.problem, "note": args.note,
        "model": f"{MODEL}@{REVISION[:8]} validity", "split": "",
    }
    path.parent.mkdir(exist_ok=True)
    new = not path.exists() or path.stat().st_size == 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)
    return f"{row['id']} in {path.relative_to(ROOT)}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="the sentence or document; omit to type lines")
    ap.add_argument("--save", action="store_true", help="append it to redteam/findings/findings.csv")
    ap.add_argument("--area", default="", help="your area in the plan (formats, names, ...)")
    ap.add_argument("--language", default="az", help="az (default), or az+ru, az+en ...")
    ap.add_argument("--expect", default="", help='what should be masked: "value=LABEL; ..."')
    ap.add_argument("--problem", default="", choices=("",) + PROBLEMS)
    ap.add_argument("--note", default="")
    args = ap.parse_args(argv)
    if args.save and not args.problem:
        ap.error("--save needs --problem")

    import predict
    print("loading the model...", file=sys.stderr)
    model, tokenizer, id2label = predict.load_model(MODEL, revision=REVISION)

    def run(text: str) -> None:
        spans = predict._detect_entities_word_consistent(text, model, tokenizer, id2label)
        print(_show(text, spans))
        for s in spans:
            print(f"  {s['label']:<28} {s['text']!r}")
        if not spans:
            print("  (nothing masked)")
        if args.save:
            print(f"saved as {save(text, spans, args)}")

    if args.text is not None:
        run(args.text)
        return 0
    print("type a sentence and press Enter (empty line ends)", file=sys.stderr)
    for line in sys.stdin:
        if not line.strip():
            break
        run(line.rstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
