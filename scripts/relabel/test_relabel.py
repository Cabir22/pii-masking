"""relabel.py on fixtures (no download): labels removed, text unchanged, strict on every mismatch, windows."""
import csv
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import relabel as R  # noqa: E402

PASS = FAIL = 0


def check(cond, msg, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", msg, detail if detail is not None else "")


def ent(text, value, label, nth=0):
    i = -1
    for _ in range(nth + 1):
        i = text.index(value, i + 1)
    return {"start": i, "end": i + len(value), "label": label}


T1 = "Maşının yaşı 3 olduğu üçün baxış lazımdır. Müştəri 34 yaşındadır."
T2 = "Yaş həddi: 17. İstifadəçinin yaşı 17 göstərilib."
DOCS = [{"id": "d1", "text": T1, "entities": [ent(T1, "3", "AGE"), ent(T1, "34", "AGE")]},
        {"id": "d2", "text": T2, "entities": [ent(T2, "17", "AGE"), ent(T2, "17", "AGE", 1)]},
        {"id": "d3", "text": "Ünvan: Nizami küçəsi 5.", "entities": []}]
COLS = ["lang", "split", "doc_id", "start", "end", "label", "value", "text_sha16", "reason"]


def write_list(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def row(lang, doc, text, e, reason="test"):
    return {"lang": lang, "split": "train", "doc_id": doc, "start": e["start"], "end": e["end"], "label": e["label"],
            "value": text[e["start"]:e["end"]], "text_sha16": R.sha16(text), "reason": reason}


class FakeTok:
    """Whitespace 'tokenizer' with the call shape tokenize_split uses: one window per text."""
    def __call__(self, text, **kw):
        offs, ids, pos = [(0, 0)], [0], 0
        for w in text.split():
            s = text.index(w, pos)
            offs.append((s, s + len(w)))
            ids.append(sum(map(ord, w)) % 1000 + 5)
            pos = s + len(w)
        offs.append((0, 0))
        ids.append(2)
        return {"input_ids": [ids], "attention_mask": [[1] * len(ids)], "offset_mapping": [offs]}


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    lst = td / "list.tsv"
    write_list(lst, [row("az", "d1", T1, DOCS[0]["entities"][0]), row("az", "d2", T2, DOCS[1]["entities"][0]),
                     {"lang": "ru", "split": "train", "doc_id": "d2", "start": "", "end": "", "label": "AGE", "value": "",
                      "text_sha16": "", "reason": "not translated (rejected)"}])
    spans, absent = R.load_list(lst, "az")
    out, rep = R.relabel_docs([dict(d) for d in DOCS], spans, absent)
    check(rep["documents"] == 2 and rep["spans"] == 2, "two documents, two labels removed", rep)
    check([d["text"] for d in out] == [d["text"] for d in DOCS], "the text is unchanged")
    check([e["start"] for e in out[0]["entities"]] == [DOCS[0]["entities"][1]["start"]], "d1 keeps the person's age only")
    check(out[1]["entities"] == [DOCS[1]["entities"][1]], "d2 removes the limit, keeps the user's age (same value 17)")
    check(out[2] == DOCS[2], "an unlisted document is untouched")

    def fails(records, spans_, absent_=frozenset()):
        try:
            R.relabel_docs(records, spans_, set(absent_))
        except R.RelabelError:
            return True
        return False
    changed = [dict(DOCS[0], text=T1.replace("baxış", "yoxlama"))]
    check(fails(changed, {"d1": spans["d1"]}), "a changed text stops the run (hash)")
    bad = [dict(spans["d1"][0], start=spans["d1"][0]["start"] + 1, end=spans["d1"][0]["end"] + 1)]
    check(fails([dict(DOCS[0])], {"d1": bad}), "a span that is not there stops the run")
    wrong_label = [dict(spans["d1"][0], label="DATE")]
    check(fails([dict(DOCS[0])], {"d1": wrong_label}), "a span with another label stops the run")
    # translations: found by source_id; a 'not translated' row must really be absent
    ru = [{"id": "x", "source_id": "d2", "lang": "ru", "text": "Возраст 17.", "entities": []}]
    sp_ru, ab_ru = R.load_list(lst, "ru")
    check(ab_ru == {"d2"} and not sp_ru, "a 'not translated' row is read as absent")
    check(fails(ru, sp_ru, ab_ru), "a document listed as not translated but present stops the run")

    # the CLI: docs + windows, a missing listed document stops it
    d = td / "in"
    d.mkdir()
    (d / "train.docs.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in DOCS), encoding="utf-8")
    from prepare_splits import build_label_list, tokenize_split
    label2id = {l: i for i, l in enumerate(build_label_list())}
    wins = tokenize_split(DOCS, FakeTok(), label2id, 512, 256)
    (d / "train.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wins), encoding="utf-8")
    R.load_tokenizer = lambda base: FakeTok()                    # no download in tests
    rc = R.main(["--list", str(lst), "--lang", "az", "--docs-dir", str(d), "--out-dir", str(td / "out"), "--windows"])
    check(rc == 0, "the CLI runs")
    new = [json.loads(x) for x in (td / "out" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
    old = {w["id"]: w for w in wins}
    check([w["input_ids"] for w in new] == [w["input_ids"] for w in wins], "windows keep their input_ids")
    check(next(w for w in new if w["id"] == "d3__w0") == old["d3__w0"], "an unlisted document's window is unchanged")
    b_age = label2id["B-AGE"]
    check(new[0]["labels"].count(b_age) == 1 and old["d1__w0"]["labels"].count(b_age) == 2,
          "d1's window loses the car's age label, keeps the person's")
    rep = json.loads((td / "out" / "relabel_report.json").read_text(encoding="utf-8"))
    check(rep["documents"] == 2 and rep["splits"]["train"]["windows"]["labels_changed"] >= 2, "the report counts", rep)
    # the stored windows differ from what re-windowing gives -> stop
    wins[0]["input_ids"][1] += 1
    (d / "train.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wins), encoding="utf-8")
    rc = R.main(["--list", str(lst), "--lang", "az", "--docs-dir", str(d), "--out-dir", str(td / "out2"), "--windows"])
    check(rc == 1, "windows that re-windowing does not reproduce stop the run")
    # a listed document missing from the files -> stop
    write_list(lst, [row("az", "zz", T1, DOCS[0]["entities"][0])])
    rc = R.main(["--list", str(lst), "--lang", "az", "--docs-dir", str(d), "--out-dir", str(td / "out3")])
    check(rc == 1, "a listed document that is not in the files stops the run")

# D-76: relabel_to keeps the span and changes its label (A30-A32: a building number labelled AGE)
T3 = "Ofis bina 94-də yerləşir. Direktor 52 yaşındadır."
DOC3 = {"id": "d4", "text": T3, "entities": [ent(T3, "94", "AGE"), ent(T3, "52", "AGE")]}
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    lst = td / "list.tsv"
    COLS.append("relabel_to")
    r_bn = dict(row("az", "d4", T3, DOC3["entities"][0]), relabel_to="BUILDINGNUM")
    r_rm = dict(row("az", "d1", T1, DOCS[0]["entities"][0]), relabel_to="")
    write_list(lst, [r_bn, r_rm])
    spans, absent = R.load_list(lst, "az")
    out, rep = R.relabel_docs([dict(DOCS[0]), dict(DOC3)], spans, absent)
    check(rep["removed"] == 1 and rep["relabelled"] == 1, "one label removed, one relabelled", rep)
    check(out[1]["entities"] == [dict(DOC3["entities"][0], label="BUILDINGNUM"), DOC3["entities"][1]],
          "the building number keeps its span as BUILDINGNUM, the person's age stays AGE", out[1]["entities"])
    check(out[1]["text"] == T3 and DOC3["entities"][0]["label"] == "AGE", "text unchanged, the input not mutated")
    check(len(out[0]["entities"]) == 1, "an empty relabel_to still removes")

    def list_fails(rows):
        write_list(lst, rows)
        try:
            R.load_list(lst, "az")
        except R.RelabelError:
            return True
        return False
    check(list_fails([dict(r_bn, relabel_to="BUILDING")]), "an unknown relabel_to stops the run")
    check(list_fails([dict(r_bn, relabel_to="AGE")]), "relabel_to equal to the label stops the run")
    write_list(lst, [r_bn, dict(r_bn, relabel_to="")])
    spans, absent = R.load_list(lst, "az")
    try:
        R.relabel_docs([dict(DOC3)], spans, absent)
        twice = False
    except R.RelabelError:
        twice = True
    check(twice, "a span listed twice (relabel and remove) stops the run")
    # the CLI with windows: the token labels become B-BUILDINGNUM, input_ids unchanged
    d = td / "in"
    d.mkdir()
    (d / "train.docs.jsonl").write_text(json.dumps(DOC3, ensure_ascii=False) + "\n", encoding="utf-8")
    from prepare_splits import build_label_list, tokenize_split
    label2id = {l: i for i, l in enumerate(build_label_list())}
    wins = tokenize_split([DOC3], FakeTok(), label2id, 512, 256)
    (d / "train.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wins), encoding="utf-8")
    write_list(lst, [r_bn])
    rc = R.main(["--list", str(lst), "--lang", "az", "--docs-dir", str(d), "--out-dir", str(td / "out"), "--windows"])
    new = [json.loads(x) for x in (td / "out" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
    check(rc == 0 and new[0]["input_ids"] == wins[0]["input_ids"], "the CLI runs, windows keep their input_ids")
    check(new[0]["labels"].count(label2id["B-BUILDINGNUM"]) == 1 and new[0]["labels"].count(label2id["B-AGE"]) == 1,
          "the window has one B-BUILDINGNUM and keeps one B-AGE")
    rep = json.loads((td / "out" / "relabel_report.json").read_text(encoding="utf-8"))
    check(rep["removed"] == 0 and rep["relabelled"] == {"AGE->BUILDINGNUM": 1}, "the report counts the relabel", rep)

# D-78: an add row (no label, relabel_to) labels a span that has none (a card expiry left unlabelled)
T4 = "Kart nömrəsi: 4220 9957 2923 6783\nSon istifadə tarixi: 12/28\nCVV: 412"
DOC4 = {"id": "d5", "text": T4, "entities": [dict(ent(T4, "4220 9957 2923 6783", "PAYMENT_CARD_NUMBER"),
                                                    text="4220 9957 2923 6783"),
                                               dict(ent(T4, "412", "CARD_SECURITY_CODE"), text="412")]}
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    lst = td / "list.tsv"
    e = ent(T4, "12/28", "DATE")
    r_add = dict(row("az", "d5", T4, e), label="", relabel_to="DATE")
    write_list(lst, [r_add])
    spans, absent = R.load_list(lst, "az")
    out, rep = R.relabel_docs([dict(DOC4)], spans, absent)
    added = [x for x in out[0]["entities"] if x["label"] == "DATE"]
    check(rep["added"] == 1 and rep["removed"] == 0 and rep["relabelled"] == 0, "one span added", rep)
    check(added == [{"start": e["start"], "end": e["end"], "label": "DATE", "text": "12/28"}],
          "the expiry is added as DATE with its text (the records' entity shape)", added)
    check([x["start"] for x in out[0]["entities"]] == sorted(x["start"] for x in out[0]["entities"]),
          "the entities stay in text order")
    check(out[0]["text"] == T4 and len(DOC4["entities"]) == 2, "text unchanged, the input not mutated")

    def add_fails(rows, doc=DOC4):
        write_list(lst, rows)
        try:
            sp, ab = R.load_list(lst, "az")
            R.relabel_docs([dict(doc)], sp, ab)
        except R.RelabelError:
            return True
        return False
    check(add_fails([dict(r_add, value="12/29")]), "an add whose value is not in the text stops the run")
    card = DOC4["entities"][0]
    check(add_fails([dict(r_add, start=card["start"], end=card["end"], value=T4[card["start"]:card["end"]])]),
          "an add over an existing entity stops the run")
    check(add_fails([r_add, r_add]), "the same span added twice stops the run")
    check(add_fails([dict(r_add, relabel_to="")]), "an add row without relabel_to stops the run")
    # the CLI with windows: the token labels gain B-DATE, input_ids unchanged
    d = td / "in"
    d.mkdir()
    (d / "train.docs.jsonl").write_text(json.dumps(DOC4, ensure_ascii=False) + "\n", encoding="utf-8")
    from prepare_splits import build_label_list, tokenize_split
    label2id = {l: i for i, l in enumerate(build_label_list())}
    wins = tokenize_split([DOC4], FakeTok(), label2id, 512, 256)
    (d / "train.jsonl").write_text("".join(json.dumps(w) + "\n" for w in wins), encoding="utf-8")
    write_list(lst, [r_add])
    rc = R.main(["--list", str(lst), "--lang", "az", "--docs-dir", str(d), "--out-dir", str(td / "out"), "--windows"])
    new = [json.loads(x) for x in (td / "out" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
    check(rc == 0 and new[0]["input_ids"] == wins[0]["input_ids"], "add: the CLI runs, windows keep their input_ids")
    check(new[0]["labels"].count(label2id["B-DATE"]) == 1 and wins[0]["labels"].count(label2id["B-DATE"]) == 0,
          "add: the window gains one B-DATE")
    rep = json.loads((td / "out" / "relabel_report.json").read_text(encoding="utf-8"))
    check(rep["added"] == {"DATE": 1} and rep["relabelled"] == {}, "add: the report counts it", rep)

# D-82: a DATE with its weekday inside is trimmed to the calendar date: the old span removed, the trimmed one added
T6 = "Görüş cümə axşamı, 16 may 1963 tarixində olub. Növbəti: 10 iyun 1991, bazar ertəsi."
wd = {"start": T6.index("cümə"), "end": T6.index(" tarixində"), "label": "DATE"}
wa = {"start": T6.index("10 iyun"), "end": T6.index("."  , T6.index("bazar")), "label": "DATE"}
DOC6 = {"id": "d6", "text": T6, "entities": [wd, wa]}


def trim_rows(e, value):
    old = dict(row("az", "d6", T6, e), relabel_to="")
    s = T6.index(value, e["start"])
    new = dict(row("az", "d6", T6, {"start": s, "end": s + len(value), "label": ""}), relabel_to="DATE")
    return [old, new]


rows6 = trim_rows(wd, "16 may 1963") + trim_rows(wa, "10 iyun 1991")
out, rep = R.relabel_docs([dict(DOC6)], {"d6": rows6}, set())
check([T6[x["start"]:x["end"]] for x in out[0]["entities"]] == ["16 may 1963", "10 iyun 1991"]
      and all(x["label"] == "DATE" for x in out[0]["entities"]), "D-82: both weekdays trimmed out of the DATE", out)
check(rep["removed"] == 2 and rep["added"] == 2 and out[0]["text"] == T6, "D-82: 2 removed, 2 added, text unchanged", rep)
try:
    R.relabel_docs([dict(DOC6)], {"d6": rows6[1:]}, set())      # the add without its removal
    check(False, "D-82: an add over a span the list does not remove still stops the run")
except R.RelabelError:
    check(True, "")

print(f"PASSED {PASS}   FAILED {FAIL}")
sys.exit(1 if FAIL else 0)
