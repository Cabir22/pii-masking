"""P4-3 / P4-14 checks: the D-19c move, the replay sample, and the Azerbaijani-only
parts (old documents minus the drop list, the old/new duplicate gate) of `build_sprint_mix.py`.

No data files, no model.

    python scripts/test_build_sprint_mix.py
"""

from __future__ import annotations

import json
import random
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_sprint_mix import (LANGS, cross_split_dups, read_drop_list,  # noqa: E402
                              read_old_az, regroup, sample_replay, source, write_jsonl)
from prepare_splits import leakage_report                   # noqa: E402


def doc(text: str) -> dict:
    return {"text": text, "lang": "az", "entities": []}


def test_regroup() -> None:
    splits = {"train": [doc("Ümid gəldi."), doc("a")],
              "val": [doc("ümid  gəldi."), doc("b"), doc("c")],
              "test": [doc("c"), doc("d")]}
    assert regroup(splits) == 3                     # the ümid pair, and c from val and test
    assert sorted(r["text"] for r in splits["val"]) == ["b"]
    assert sorted(r["text"] for r in splits["test"]) == ["d"]
    for kinds in leakage_report(splits).values():
        assert kinds["exact_text"]["shared"] == kinds["normalized_text"]["shared"] == 0


def test_sample_replay() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "replay.docs.jsonl"
        path.write_text("".join(json.dumps({"id": f"{g}{i}", "lang": g}) + "\n"
                                for g in LANGS for i in range(50)), encoding="utf-8")
        a = sample_replay(path, 40, random.Random(1))
        assert Counter(r["lang"] for r in a) == {g: 10 for g in LANGS}
        assert len({r["id"] for r in a}) == 40 and all(r["_replay"] for r in a)
        assert a == sample_replay(path, 40, random.Random(1))   # fixed seed, same sample


def stops(fn, *args) -> bool:
    try:
        fn(*args)
    except SystemExit:
        return True
    return False


def test_old_az_and_drop_list() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for n in ("train", "val", "test"):
            (tmp / f"{n}.docs.jsonl").write_text(
                "".join(json.dumps({"id": f"{g}_{n}{i}", "lang": g, "text": f"{g} {n} {i}",
                                    "entities": [], "_source": "llm"}) + "\n"
                        for g in ("az", "en") for i in range(3)), encoding="utf-8")
        drop = tmp / "drop.jsonl"
        assert stops(read_drop_list, drop)                  # no file: stop (P2-16 not there)
        drop.write_text(json.dumps({"id": "az_train0", "split": "train", "reason": "turkish"}) + "\n"
                        + json.dumps({"id": "az_val2", "split": "val", "reason": "resolver_drift"})
                        + "\n", encoding="utf-8")
        old, dropped = read_old_az(tmp, read_drop_list(drop))
        assert {n: [r["id"] for r in rs] for n, rs in old.items()} == {
            "train": ["az_train1", "az_train2"], "val": ["az_val0", "az_val1"],
            "test": ["az_test0", "az_test1", "az_test2"]}
        assert dropped == {("turkish", "train"): 1, ("resolver_drift", "val"): 1}
        assert all(source(r) == "old" for rs in old.values() for r in rs)   # not counted as llm
        # a listed id that is not an az document of that split stops the build
        for bad in ({"id": "az_val2", "split": "test", "reason": "x"},
                    {"id": "en_train0", "split": "train", "reason": "x"},
                    {"id": "nope", "split": "train", "reason": "x"}):
            drop.write_text(json.dumps(bad) + "\n", encoding="utf-8")
            assert stops(read_old_az, tmp, read_drop_list(drop)), bad


def test_cross_split_dups() -> None:
    old = {"train": [doc("Köhnə  sənəd.")], "val": [doc("old val")], "test": [doc("old test")]}
    new = {"train": [doc("new train")], "val": [doc("köhnə sənəd.")], "test": [doc("x")]}
    mix = {n: old[n] + new[n] for n in old}
    assert cross_split_dups(mix) == {("train", "val"): 1}           # new val = old train
    new["val"] = [doc("y")]
    new["train"].append(doc("OLD TEST"))                            # the reverse: old test = new train
    mix = {n: old[n] + new[n] for n in old}
    assert cross_split_dups(mix) == {("test", "train"): 1}
    new["train"].pop()
    assert not cross_split_dups({n: old[n] + new[n] for n in old})


def test_lf_line_endings() -> None:
    """D-26: the files are written with LF on every OS, so Windows gives the canonical bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "x.docs.jsonl"
        write_jsonl(path, [doc("a"), doc("b")])
        assert b"\r" not in path.read_bytes() and path.read_bytes().count(b"\n") == 2


if __name__ == "__main__":
    test_regroup()
    test_sample_replay()
    test_old_az_and_drop_list()
    test_cross_split_dups()
    test_lf_line_endings()
    print("OK: test_build_sprint_mix")
