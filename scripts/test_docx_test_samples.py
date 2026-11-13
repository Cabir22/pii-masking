"""Verifies data/testing_samples/docx/ -- the 200-document DOCX
format-testing fixture batch.

Checks, per manifest entry:
  * the .docx opens and its extracted text (single paragraph for
    corpus_*, "\n".join(paragraph texts) for new_*) matches the manifest's
    `text` field EXACTLY;
  * every gold entity's start/end slices out of that extracted text the
    exact same substring recorded in the manifest.

Also checks file/bucket/language counts against the acceptance criteria.

Run: python scripts/test_docx_test_samples.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCX_DIR = ROOT / "data" / "testing_samples" / "docx"
MANIFEST_PATH = DOCX_DIR / "manifest.json"

PASS = FAIL = 0


def check(cond: bool, msg: str, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL {msg}" + (f"  [{detail}]" if detail else ""))


def extract_text(path: Path, bucket: str) -> str:
    d = docx.Document(str(path))
    if bucket == "corpus_derived":
        return d.paragraphs[0].text
    return "\n".join(p.text for p in d.paragraphs)


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    check(len(manifest) == 200, "manifest has 200 entries", str(len(manifest)))

    buckets = {}
    langs = {}
    for m in manifest:
        buckets[m["bucket"]] = buckets.get(m["bucket"], 0) + 1
        langs[m["lang"]] = langs.get(m["lang"], 0) + 1
    check(buckets.get("corpus_derived") == 100, "100 corpus_derived entries", str(buckets))
    check(buckets.get("generated") == 100, "100 generated entries", str(buckets))
    check(set(langs) == {"az", "en", "tr", "ru"}, "all 4 languages present", str(langs))
    print(f"  language totals across 200 files: {langs}")

    docx_files = sorted(DOCX_DIR.glob("*.docx"))
    check(len(docx_files) == 200, "200 .docx files on disk", str(len(docx_files)))
    manifest_names = {m["filename"] for m in manifest}
    disk_names = {p.name for p in docx_files}
    check(manifest_names == disk_names, "manifest filenames match files on disk",
          f"only-in-manifest={manifest_names - disk_names} only-on-disk={disk_names - manifest_names}")

    for m in manifest:
        path = DOCX_DIR / m["filename"]
        try:
            extracted = extract_text(path, m["bucket"])
        except Exception as e:  # noqa: BLE001
            check(False, f"{m['filename']} opens and extracts text", repr(e))
            continue
        check(extracted == m["text"], f"{m['filename']} extracted text matches manifest",
              f"len(extracted)={len(extracted)} len(expected)={len(m['text'])}")
        for e in m["entities"]:
            got = extracted[e["start"]:e["end"]]
            expected = e.get("text")
            if expected is None:
                # corpus_derived entities carry no cached 'text' in the manifest
                # dump for translate_input/*_output.jsonl records that lacked
                # it in the source; re-slice from the manifest's own text field.
                expected = m["text"][e["start"]:e["end"]]
            check(got == expected,
                  f"{m['filename']} entity {e['label']}@{e['start']}:{e['end']} slices correctly",
                  f"got={got!r} expected={expected!r}")

    print(f"\n{'='*56}\nPASSED {PASS}   FAILED {FAIL}\n{'='*56}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
