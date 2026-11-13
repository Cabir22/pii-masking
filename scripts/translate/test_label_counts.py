"""label_counts.py on a tiny fixture: lost, kept, translated and the flag."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import label_counts  # noqa: E402

FAIL = 0


def check(name, ok):
    global FAIL
    print(("ok   " if ok else "FAIL ") + name)
    FAIL += not ok


def ents(*labels):
    return [{"start": 0, "end": 1, "label": l} for l in labels]


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    (td / "src").mkdir()
    (td / "out" / "ru").mkdir(parents=True)
    src = [{"id": "a", "entities": ents("GIVENNAME", "DATE")},
           {"id": "b", "entities": ents("GIVENNAME", "GIVENNAME", "DATE")},     # not translated
           {"id": "c", "entities": ents("IBAN")},
           {"id": "d", "entities": ents("GIVENNAME")}]
    out = [{"source_id": "a", "entities": ents("GIVENNAME", "DATE")},
           {"source_id": "c", "entities": []},                                  # an IBAN dropped inside a written doc
           {"source_id": "d", "entities": ents("GIVENNAME")}]
    (td / "src" / "train.docs.jsonl").write_text("\n".join(json.dumps(r) for r in src), encoding="utf-8")
    (td / "out" / "ru" / "train.docs.jsonl").write_text("\n".join(json.dumps(r) for r in out), encoding="utf-8")
    r = label_counts.count(td / "src", td / "out", "ru", "train")
    g, d, i = r["labels"]["GIVENNAME"], r["labels"]["DATE"], r["labels"]["IBAN"]
    check("documents: 3 of 4 written, 25% lost", (r["docs"], r["written"], r["doc_loss_pct"]) == (4, 3, 25.0))
    check("GIVENNAME: source 4, kept 2, lost 2, translated 2", (g["source"], g["kept"], g["lost"], g["translated"]) == (4, 2, 2, 2))
    check("GIVENNAME lost 50%", g["lost_pct"] == 50.0)
    check("DATE kept 1 of 2, translated 1", (d["source"], d["kept"], d["translated"]) == (2, 1, 1))
    check("IBAN dropped inside a written document: kept→translated 0%", i["kept_to_translated_pct"] == 0.0)
    check("nothing outside the source", r["not_in_source"] == 0)
    check("labels with under 30 source entities are never flagged", not any(x["flag"] for x in r["labels"].values()))
    check("missing split gives None", label_counts.count(td / "src", td / "out", "ru", "val") is None)
    md = label_counts.markdown({"ru": {"train": r}}, ["ru"], ["train"])
    check("markdown has the label table", "| GIVENNAME |" in md and "## train" in md)

print("FAIL" if FAIL else "all passed", FAIL)
sys.exit(1 if FAIL else 0)
