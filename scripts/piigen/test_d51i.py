"""D-51i: the generator causes behind the label noise, fixed for later LLM batches.

    python scripts/piigen/test_d51i.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.llm import specs as S  # noqa: E402
from piigen.llm.quality import PLACE_COMMON_WORDS, find_invented_pii  # noqa: E402
from piigen.resolver import match_key  # noqa: E402
from piigen.values import ValueFactory, ValuePool  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def found(text: str, doc_type: str | None = None, entities=()) -> list[tuple[str, str]]:
    return [(f["label"], f["text"]) for f in find_invented_pii(text, list(entities), (), doc_type)]


def test_places() -> None:
    """The 4,422-place pool, any case ending, any spelling (match_key, not
    casefold); never an ordinary word, an organisation or an institution."""
    check(("CITY", "BAKI") in found("Ofis BAKI şəhərində yerləşir."), "ALL-CAPS city (the casefold bug)")
    check(("CITY", "Baki") in found("Unvan: Baki seheri, Nizami."), "ASCII city")
    check(("CITY", "Şüvəlanda") in found("Anbar Şüvəlanda yerləşir."), "a settlement with a case ending")
    check(("CITY", "Bakının") in found("Bakının mərkəzi ərazisində yeni park açılıb."), "a genitive city")
    for t in ("İkinci problem: SIM kart.", "Müştəri: Səbir? Səbirim tükənib!", "İcarə müddəti bitir.",
              "Hormetle, Xezer Loqistika numayendesi", 'Salam, "Araz Mebel" dəstək xidməti.',
              "GÖNDƏRİLƏN: Sənaye Təchizatçısı ASC", "Salyan Rayon Məhkəməsi qərar verib.",
              "400 Bad Request: sorğu yanlışdır."):
        check(not [f for f in found(t) if f[0] == "CITY"], "no place: an ordinary word, an organisation "
              "or an institution", t)
    check(len(PLACE_COMMON_WORDS) > 50 and "icare" in PLACE_COMMON_WORDS and "seki" not in PLACE_COMMON_WORDS,
          "the place word list is loaded and never holds a main town", len(PLACE_COMMON_WORDS))
    labelled = [{"start": 5, "end": 9, "label": "CITY"}]
    check(not found("Ofis BAKI şəhərində.", entities=labelled), "a labelled city is no finding")


def test_persona_and_age() -> None:
    """The R4/R5/R9 detectors: what cleaning would label, generation rejects."""
    chat = found("[10:15] Babek: Salam, sifariş haqqında.\n[10:16] Operator: Buyurun.", "live_chat")
    check(("GIVENNAME", "Babek") in chat and ("CITY", "Babek") not in chat,
          "a chat speaker is a name, not also a place (Babək is a district)", chat)
    check(("GIVENNAME", "Leyla") in found("Salam! Mən Leyla, sizə necə kömək edə bilərəm?", "live_chat"),
          "a self-introduction")
    sign = found("Məlumat üçün təşəkkür edirik.\n\nHörmətlə,\nAynur Quliyeva", "customer_email")
    check(sign and len(sign) == 1, "a signature, reported once", sign)
    check(("AGE", "32") in found("Müştərinin məlumatları:\nYaş: 32\nStatus: aktiv"), "an unlabelled age")
    check(not found("Sənəd hazırlanıb və göndərilib."), "a clean document has no finding")


def test_full_names() -> None:
    """A given name that is a village too (`Ümid`) is still a full name before a
    surname; one that is an ordinary word needs a real surname ending."""
    for name in ("Ümid Əliyev", "Murad Məmmədov", "Boyukaga Sadili"):
        check(("GIVENNAME", name) in found(f"Hörmətlə, {name}."), f"{name!r} is a full name")
    for t in ("Sənaye Tipli avadanlıq gəlib.", "Şəhər Filialı bağlıdır.", "Server Modulu yenilənib."):
        check(not [f for f in found(t) if f[0] == "GIVENNAME"], "an ordinary word + adjective is no name", t)


def test_plans() -> None:
    """LLM plans keep common-word names out (`Şəkil`, `Döyüş`, `Ümid`)."""
    common = S.common_word_keys()
    check({"sekil", "doyus", "umid"} <= common, "the common-word names are known")
    f = ValueFactory(random.Random(3), ValuePool(state_path=None))
    draws = [S.plan_value(f, "GIVENNAME", "az") for _ in range(2000)]
    check(not [d for d in draws if match_key(d) in common], "no planned given name is a common word")
    check(len(set(draws)) > 300, "plans stay varied", len(set(draws)))
    raw = [f.make("GIVENNAME", "az") for _ in range(2000)]
    check(any(match_key(d) in common for d in raw), "(the factory alone does draw them)")


def test_surname_sweep() -> None:
    """The sweep's stoplist and institution check (`relabel_unlabeled_surnames.py`)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("sweep", ROOT / "scripts" / "relabel_unlabeled_surnames.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    known = {"Şəkərli", "Əliyev", "Məmmədov", "Nərimanov"}
    check(not m.find_additions("Xəstədə Şəkərli diabet aşkarlanıb.", [], known)[0], "a stoplist word stays unlabelled")
    check(not m.find_additions("Heydər Əliyev Beynəlxalq Hava Limanı bağlıdır.", [], known)[0],
          "a surname inside an institution's name stays unlabelled")
    check(not m.find_additions("Nərimanov Liseyi yeni il üçün qəbul elan edib.", [], known)[0],
          "`Nərimanov Liseyi` is an institution")
    add = m.find_additions("Sənədi Məmmədov imzalayıb.", [], known)[0]
    check([a["text"] for a in add] == ["Məmmədov"], "a real surname is still labelled", add)


TESTS = [("places", test_places), ("persona names and ages", test_persona_and_age), ("full names", test_full_names),
         ("LLM plans", test_plans), ("surname sweep", test_surname_sweep)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}")
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
