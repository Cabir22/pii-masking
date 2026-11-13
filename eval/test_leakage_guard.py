"""Tests for eval/leakage_guard.py and build_shadow_hashes.py on synthetic
strings written for this test (no benchmark, training or shadow text).

Run:  python eval/test_leakage_guard.py
"""
from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_shadow_hashes as B  # noqa: E402
from leakage_guard import (Guard, _bounded, anchor_of, is_distinctive,  # noqa: E402
                           is_low_entropy, load_allowlist, load_shadow, main, ngrams,
                           words)

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond, name, detail=None):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}" if detail is not None else name)


EMPTY_SHADOW = {"ngram_sha1": [], "values": []}

# --- normalisation and value rules ------------------------------------------
check(words("İlkin, SALAM! yaxşı-dır") == ["ilkin", "salam", "yaxşı", "dır"],
      "words: lower-case, İ without combining dot, punctuation dropped", words("İlkin, SALAM! yaxşı-dır"))
check(list(ngrams(list("abcdefghi"))) == ["a b c d e f g h", "b c d e f g h i"], "ngrams of 9 words")
check(is_distinctive("AZ12TEST00000000000000000001") and is_distinctive("+994 55 000 00 00")
      and is_distinctive("99.99.2099"), "distinctive: IBAN-like, phone-like, date-like")
check(not is_distinctive("Qaranquş") and not is_distinctive("QaRaNquŞ") and not is_distinctive("Qara Dəniz")
      and not is_distinctive("A1B2") and not is_distinctive("12345"),
      "not distinctive: words/names (also case-noised), or under 6 characters")
check(is_distinctive("QWXZKPT"), "distinctive: an all-capitals code is not a word")
check(is_low_entropy("ZZ1000", ["ZIPCODE"]) and is_low_entropy("99.99.2099", ["DATE"])
      and is_low_entropy("12:50 AM", ["TIME|API_KEY"]) and not is_low_entropy("QWXZKPT", ["AZ_FIN"])
      and not is_low_entropy("QQ00TEST1111222233334444", ["IBAN"]), "low entropy: small universe or < 28 bits")
check(anchor_of("+994 55 000 00 00") == ("994", 1), "anchor: longest word run + offset")
check(_bounded("x ZZ9999 y", 2, 8) and not _bounded("xZZ9999 y", 1, 7) and not _bounded("ZZ99999", 0, 6),
      "bounded: no word char glued on either side")
allow, src = load_allowlist()
check("12345" in allow and "4242424242424242" in allow and "policy_allowlist.txt" in src,
      "allowlist read from data/policy_allowlist.txt", (sorted(allow), src))

# --- check 1: values ----------------------------------------------------------
values = {"QQ00TEST1111222233334444": ["IBAN"], "12345": ["CARD_SECURITY_CODE"],
          "Qaranquş": ["GIVENNAME"], "7Z": ["AGE"]}
g = Guard(values, {}, {"12345"}, [], EMPTY_SHADOW)
check(set(g.checked) == {"QQ00TEST1111222233334444", "12345"} and set(g.skipped) == {"Qaranquş", "7Z"},
      "checked = distinctive + allowlisted", (g.checked, g.skipped))
g.scan("d1", "Hesab QQ00TEST1111222233334444 idi.")
g.scan("d2", "Hesab QQ00TEST11112222333344449 idi.")      # longer run: not the value
g.scan("d3", "Kod 12345 yazılıb, Qaranquş gəldi.")        # allowlisted + skipped vocabulary
check(g.counts["values"] == 1 and g.hits["values"][0]["doc"] == "d1", "check 1: exact bounded hit only",
      g.hits["values"])
check(g.counts["allowlisted"] == 1 and g.hits["allowlisted"][0]["value"] == "12345",
      "check 1b: allowlisted value reported apart")
check(not g.clean(), "check 1 hit -> not clean")

# --- check 2: 8-grams and the stoplist ----------------------------------------
bench = "alfa beta qamma delta epsilon zeta eta teta yota kappa"
grams = {x: "bench_1" for x in ngrams(words(bench))}
g = Guard({}, grams, set(), [], EMPTY_SHADOW)
g.scan("t1", "Giriş: Alfa, beta, qamma delta epsilon zeta eta teta. Son.")
check(g.counts["sentences"] == 1 and g.hits["sentences"][0]["benchmark"] == "bench_1",
      "check 2: 8-gram hit through punctuation and case", g.hits["sentences"])
g.scan("t2", "alfa beta qamma delta epsilon zeta eta")    # only 7 shared words
check(g.counts["sentences"] == 1, "check 2: 7 words is not a hit")
stop = ["alfa beta qamma delta epsilon zeta eta teta"]
g = Guard({}, grams, set(), stop, EMPTY_SHADOW)
g.scan("t1", "alfa beta qamma delta epsilon zeta eta teta")
check(g.counts["sentences"] == 0 and g.stopped_grams == 1, "check 2: stoplisted 8-gram ignored")

# --- check 3: shadow hashes built by build_shadow_hashes -----------------------
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    ftext = "Omeqa psi xi pi ro siqma tau ipsilon fi xi psi. Kod QX-4419-77 ilə."
    vs = ftext.index("QX-4419-77")
    fake_shadow = [{"id": "s1", "text": ftext,
                    "entities": [{"start": vs, "end": vs + 10, "label": "API_KEY"}]}]
    (td / "shadow_dev.jsonl").write_text(json.dumps(fake_shadow[0]) + "\n", encoding="utf-8")
    out = td / "h.json.gz"
    B.main(["--shadow-dir", str(td), "--files", "shadow_dev.jsonl", "--out", str(out)])
    data = load_shadow(out)
    raw = gzip.open(out, "rt", encoding="utf-8").read()
    check(len(data["ngram_sha1"]) == len(list(ngrams(words(ftext)))) == 9 and len(data["values"]) == 1, "builder: hashes counted",
          (len(data["ngram_sha1"]), len(data["values"])))
    check("siqma" not in raw and "QX-4419-77" not in raw, "builder: no clear text in the hash file")
    g = Guard({}, {}, set(), [], data)
    g.scan("c1", "Burada: omeqa psi xi pi ro siqma tau ipsilon.")
    g.scan("c2", "Sifariş QX-4419-77 hazırdır.")
    g.scan("c3", "Sifariş QX-4419-778 hazırdır.")          # not bounded: not the value
    check(g.counts["shadow_ngrams"] == 1 and set(g.hits["shadow_ngrams"][0]) == {"doc", "ngram_sha1"},
          "check 3: shadow 8-gram hit reported as hash + doc id only", g.hits["shadow_ngrams"])
    check(g.counts["shadow_values"] == 1 and g.hits["shadow_values"][0]["doc"] == "c2"
          and set(g.hits["shadow_values"][0]) == {"doc", "value_sha1"},
          "check 3: shadow value hit by hash only, bounded", g.hits["shadow_values"])
    # Low-entropy shadow values (a date, a postcode) are not hashed: they
    # would match any corpus by chance (check-1 rule).
    t2 = "Tarix 99.99.2099, indeks ZZ1999, kod QX-4419-77 qeyd edildi."
    ents = [{"start": t2.index(v), "end": t2.index(v) + len(v), "label": lab}
            for v, lab in (("99.99.2099", "DATE"), ("ZZ1999", "ZIPCODE"), ("QX-4419-77", "API_KEY"))]
    (td / "low.jsonl").write_text(json.dumps({"id": "s2", "text": t2, "entities": ents}) + "\n", encoding="utf-8")
    B.main(["--shadow-dir", str(td), "--files", "low.jsonl", "--out", str(td / "low.json.gz")])
    low = load_shadow(td / "low.json.gz")
    check(len(low["values"]) == 1, "builder: low-entropy shadow values are not hashed", low["values"])
    # The empty placeholder loads and blocks nothing.
    B.main(["--empty", "--out", str(td / "e.json.gz")])
    e = load_shadow(td / "e.json.gz")
    check(e["ngram_sha1"] == [] and e["values"] == [] and e["source"]["documents"] == 0, "placeholder is empty")

    # --- end to end: exit codes ---------------------------------------------------
    (td / "clean.docs.jsonl").write_text(json.dumps({"id": "k", "text": "Sadə mətn."}) + "\n", encoding="utf-8")
    (td / "dirty.docs.jsonl").write_text(
        json.dumps({"id": "k", "text": "omeqa psi xi pi ro siqma tau ipsilon"}) + "\n", encoding="utf-8")
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        rc_clean = main([str(td / "clean.docs.jsonl"), "--shadow-hashes", str(out)])
        rc_dirty = main([str(td / "dirty.docs.jsonl"), "--shadow-hashes", str(out)])
    check(rc_clean == 0 and rc_dirty == 1, "exit code 0 only when clean", (rc_clean, rc_dirty))

    # --- --frames: slots break 8-grams --------------------------------------------
    fr = td / "frames_fake.py"
    fr.write_text('FRAMES = {"DATE": ["omeqa psi xi pi {v} ro siqma tau ipsilon"]}\n'
                  'GENERIC_FRAMES = ["omeqa psi xi pi ro siqma tau ipsilon {v}"]\n'
                  'NEUTRAL = []\nANCHORS = {}\nFRAME_VERSION = "t"\n', encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()):
        rc = main(["--frames", str(fr), "--shadow-hashes", str(out)])
    check(rc == 1, "frames: a generic frame copying a shadow sentence fails")


if __name__ == "__main__":
    print(f"{PASS} passed, {FAIL} failed")
    for f in FAILURES:
        print("  FAIL", f)
    sys.exit(1 if FAIL else 0)
