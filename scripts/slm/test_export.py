"""Task 2.1 checks: the round trip, every export format, and one id list.

No network, no model weights. The two tokenizer checks use the locally cached
xlm-roberta-large and Qwen3-1.7B tokenizers and are skipped if absent.

    python scripts/slm/test_export.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import export as EX            # noqa: E402
import roundtrip as RT         # noqa: E402
from piigen.config import ENTITY_TYPES   # noqa: E402

PASS = FAIL = 0


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL  {msg}" + (f"\n      {detail!r}" if detail is not None else ""))


def ent(text: str, value: str, label: str, nth: int = 0) -> dict:
    i = -1
    for _ in range(nth + 1):
        i = text.index(value, i + 1)
    return {"start": i, "end": i + len(value), "label": label}


# --- round trip -------------------------------------------------------------

t = "Əli dedi ki, Əli sabah gələcək."
es = [ent(t, "Əli", "GIVENNAME", 0), ent(t, "Əli", "GIVENNAME", 1)]
check(RT.round_trip(t, es) == (True, "ok"), "repeats: both occurrences claimed in order")
check(RT.completion(t, es) == "GIVENNAME\tƏli\nGIVENNAME\tƏli", "repeats: every occurrence emitted")

t = "[2024-08-10 14:22:05] Yaşı 10 olan uşaq."
check(RT.round_trip(t, [ent(t, "10", "AGE", 1)])[0] is False,
      "ambiguity: an earlier unlabeled '10' in a timestamp makes the doc fail")
check(RT.round_trip(t, [ent(t, "10", "AGE", 1)])[1] == "grounded to another occurrence", "ambiguity: reason")

t = "Alim gəldi. Ali isə yox."
check(RT.round_trip(t, [ent(t, "Ali", "GIVENNAME", 1)]) == (True, "ok"),
      "word boundary: 'Ali' inside 'Alim' is skipped by tier 1")

pem = "-----BEGIN PRIVATE KEY-----\nMIIBVAIBADANBgkqhkiG9w0BAQEFAASCAT4w\n-----END PRIVATE KEY-----"
t = f"Açar:\n{pem}\nSaxlayın."
es = [ent(t, pem, "PRIVATE_KEY")]
line = RT.completion(t, es)
check("\n" not in line.split("\t", 1)[1], "multi-line value rendered on one line", line)
found, missing = RT.ground(t, RT.parse(line)[0])
check(not missing and (found[0]["start"], found[0]["end"]) == (es[0]["start"], es[0]["end"]),
      "multi-line value grounds back to the exact span", found)
check(found and found[0]["tier"] == 3, "multi-line value is found by tier 3")

t = "Ad: İSMAYILOVA Gülnar, ünvan: Bakı."
found, missing = RT.ground(t, [("SURNAME", "ismayilova"), ("CITY", "Bakı")])
check(not missing and t[found[0]["start"]:found[0]["end"]] == "İSMAYILOVA",
      "tier 3 fold handles İ without shifting offsets", found)
check(len("İ".lower()) == 2 and t[found[1]["start"]:found[1]["end"]] == "Bakı",
      "spans after an İ are not shifted (lower() would shift them)")

check(RT.parse("NONE") == ([], 0), "NONE parses to no lines")
check(RT.parse("GIVENNAME\tƏli\nFOO\tx\nno tab here\nCITY\t") == ([("GIVENNAME", "Əli")], 3),
      "strict parse rejects unknown labels, missing tabs and empty values")
check(RT.completion("Heç nə yoxdur.", []) == "NONE", "no PII -> NONE")
check(RT.parse("TELEPHONENUM\t+994\t50 123")[0] == [("TELEPHONENUM", "+994\t50 123")],
      "a tab inside a value survives (split on the first tab only)")

# --- offsets for byte-level BPE ---------------------------------------------

t = "Adım Əli.\n  Son"
offs = [(0, 4), (4, 8), (8, 10), (10, 12), (12, 15)]   # 'Adım', ' Əli', '.\n', '  ', 'Son'
check(EX.trim_offsets(t, offs) == [(0, 4), (5, 8), (8, 9), (10, 12), (12, 15)],
      "trim_offsets: leading space and trailing newline trimmed, whitespace-only token kept",
      EX.trim_offsets(t, offs))

# --- arm C ------------------------------------------------------------------

t = "Əli Məmmədov, Əli."
r = {"id": "x1", "lang": "az", "text": t,
     "entities": [ent(t, "Əli", "GIVENNAME", 0), ent(t, "Məmmədov", "SURNAME"), ent(t, "Əli", "GIVENNAME", 1)]}
row = EX.opf_row(r)
check(row["spans"]["GIVENNAME: Əli"] == [[0, 3], [14, 17]], "opf: a repeated value shares one key", row)
got = {(s, e, k.split(": ", 1)[0]) for k, v in row["spans"].items() for s, e in v}
check(got == {(e["start"], e["end"], e["label"]) for e in r["entities"]}, "opf: spans reconstruct the gold set")
with tempfile.TemporaryDirectory() as tmp:
    EX.write_label_files(["opf"], Path(tmp))
    space = json.loads((Path(tmp) / "opf" / "labels27.json").read_text(encoding="utf-8"))
check(space["span_class_names"] == ["O", *ENTITY_TYPES], "opf: label space is O + the 27 labels")

chat = EX.chat_row(r)
check([m["role"] for m in chat["messages"]] == ["system", "user", "assistant"]
      and chat["messages"][0]["content"] == RT.SYSTEM_PROMPT, "chat: system/user/assistant with the plan's prompt")

# --- sampling ---------------------------------------------------------------

q = EX.allocate({"a": 50, "b": 30, "c": 20}, 10)
check(q == {"a": 5, "b": 3, "c": 2}, "allocate: proportional", q)
q = EX.allocate({"a": 1, "b": 1, "c": 1}, 2)
check(sum(q.values()) == 2 and q == {"a": 1, "b": 1, "c": 0}, "allocate: largest remainder, ties by name", q)

pool = {}
for lang in EX.LANGS:
    for k in range(400):
        text = f"Doc {k} Əli" if k % 4 else f"Doc {k}"
        ents = [{"start": len(text) - 3, "end": len(text), "label": "GIVENNAME"}] if k % 4 else []
        pool[f"{lang}{k}"] = {"id": f"{lang}{k}", "lang": lang, "text": text, "entities": ents}
ids = EX.sample(pool, 100, 7, "train")
check(len(ids) == 400 and all(sum(i.startswith(g) for i in ids) == 100 for g in EX.LANGS),
      "sample: exactly per_lang documents in every language")
check(sum(1 for i in ids if not pool[i]["entities"]) == 100, "sample: no-PII share kept (25% of the pool)")
check(EX.sample(pool, 100, 7, "train") == ids and EX.sample(pool, 100, 8, "train") != ids,
      "sample: deterministic for a seed, different for another")

# --- end to end on a tiny corpus --------------------------------------------

with tempfile.TemporaryDirectory() as tmp:
    src, out = Path(tmp) / "src", Path(tmp) / "out"
    src.mkdir()
    for split, n in (("train", 40), ("val", 12)):
        with (src / f"{split}.docs.jsonl").open("w", encoding="utf-8") as fh:
            for lang in EX.LANGS:
                for k in range(n):
                    text = f"Müştəri {k}: Əli Məmmədov, tel +994 50 {k:03d} 11 22."
                    es = [ent(text, "Əli", "GIVENNAME"), ent(text, "Məmmədov", "SURNAME"),
                          ent(text, f"+994 50 {k:03d} 11 22", "TELEPHONENUM")] if k % 3 else []
                    fh.write(json.dumps({"id": f"{split}-{lang}-{k}", "lang": lang, "text": text,
                                         "entities": es}, ensure_ascii=False) + "\n")
            # one document that must fail the round trip
            text = "[2024-08-10] Yaşı 10."
            fh.write(json.dumps({"id": f"{split}-bad", "lang": "az", "text": text,
                                 "entities": [ent(text, "10", "AGE", 1)]}) + "\n")
    saved = dict(EX.PER_LANG)
    EX.PER_LANG.update({"train": 8, "val": 2})
    try:
        args = ["--src", str(src), "--out", str(out), "--formats", "docs,chat,opf", "--no-edge-stats"]
        rc = EX.main(args)
        card = json.loads((out / "data_card.json").read_text(encoding="utf-8"))
        first = {s: card["splits"][s]["files"] for s in ("train", "val")}
        rc2 = EX.main(args)                       # reuses ids/
        card2 = json.loads((out / "data_card.json").read_text(encoding="utf-8"))
    finally:
        EX.PER_LANG.clear()
        EX.PER_LANG.update(saved)
    check(rc == 0 and rc2 == 0, "end to end: exits 0")
    tr = card["splits"]["train"]
    check(tr["dropped"] == 1 and tr["dropped_reasons"] == {"grounded to another occurrence": 1},
          "end to end: the ambiguous document is dropped before sampling", tr["dropped_reasons"])
    ids = (out / "ids" / "train_ids.txt").read_text(encoding="utf-8").split()
    check(len(ids) == 32 and "train-bad" not in ids, "end to end: 8 per language, dropped doc absent")
    check(all(v["same_ids"] and v["round_trip_or_content_failures"] == 0
              for s in card["splits"].values() for v in s["verify"].values()),
          "end to end: every format has the same ids and 0 round-trip failures")
    check({s: card2["splits"][s]["files"] for s in ("train", "val")} == first,
          "end to end: rerun from the saved ids gives byte-identical files")
    check(card["splits"]["train"]["ids_hash"] == EX.ids_hash(ids), "end to end: ids hash recorded")
    check((out / "DATA_CARD.md").exists(), "end to end: DATA_CARD.md written")
    # verify must notice a format that lost a document
    p = out / "export" / "chat" / "train.jsonl"
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    p.write_text("".join(lines[1:]), encoding="utf-8")
    pool_all = {json.loads(l)["id"]: json.loads(l) for l in (src / "train.docs.jsonl").open(encoding="utf-8")}
    v = EX.verify("train", ids, pool_all, {"chat": (p, 0)})
    check(v["chat"]["same_ids"] is False, "verify: a missing document is detected")

# --- real tokenizers (cached locally) ---------------------------------------

try:
    toks = EX.load_tokenizers(["xlmr", "qwen3"])
except Exception as exc:  # noqa: BLE001
    toks = {}
    print(f"skip  tokenizer checks: {type(exc).__name__}")
if toks:
    label_list = EX.build_label_list()
    label2id = {lab: i for i, lab in enumerate(label_list)}
    t = "Mənim adım Əli Məmmədovdur. Telefon: +994 50 123 45 67"
    r = {"id": "d", "text": t, "entities": [ent(t, "Əli", "GIVENNAME"), ent(t, "Məmmədov", "SURNAME"),
                                           ent(t, "+994 50 123 45 67", "TELEPHONENUM")]}
    for name, rows in (("xlmr", EX.tokenize_split([r], toks["xlmr"], label2id, *EX.XLMR_WINDOW)),
                       ("qwen3", EX.qwen_windows([r], toks["qwen3"], label2id))):
        tags = [label_list[i] for i in rows[0]["labels"] if i != -100]
        check(all(tags.count(f"B-{lab}") == 1 for lab in ("GIVENNAME", "SURNAME", "TELEPHONENUM")),
              f"{name}: every entity opens with exactly one B-", tags)
    enc = toks["qwen3"](t, return_offsets_mapping=True)
    raw = [label_list[i] for i in EX.align_labels_for_window(enc["offset_mapping"], r["entities"], label2id)]
    # ' Məmmədovdur' starts with the space, so the surname never gets its B-
    check("B-SURNAME" not in raw, "qwen3 without trimming loses the surname's B- (why trim)", raw)
    long = "Söz " * 3000 + "Əli"
    rows = EX.qwen_windows([{"id": "L", "text": long, "entities": [ent(long, "Əli", "GIVENNAME")]}],
                           toks["qwen3"], label2id)
    check(len(rows) > 1 and max(len(w["input_ids"]) for w in rows) <= EX.QWEN_WINDOW[0]
          and any(label2id["B-GIVENNAME"] in w["labels"] for w in rows),
          "qwen3: long document windowed at 2,048 and the entity still labelled")

print(f"PASSED {PASS}   FAILED {FAIL}")
sys.exit(1 if FAIL else 0)
