"""D-17 (standalone dates are DATE, timestamps are not) and D-16c's
doubled-letter follow-up.

No network, no model, no API key. Checks that read the batches are skipped
when the files are not pulled.

    python scripts/piigen/test_standalone_dates.py
"""

from __future__ import annotations

import collections
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.resolver import (find_unlabeled_repeats, find_unlabelled_planned,  # noqa: E402
                             planned_forms, resolve_claims)
from piigen.standalone_dates import (find_unlabelled_dates, labelable,  # noqa: E402
                                     standalone_dates)

BATCH2 = ROOT / "data" / "raw" / "sprint1_llm_b2.clean.jsonl"
PASS = FAIL = SKIP = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


def found(text: str) -> list[str]:
    return [text[s:e] for s, e in standalone_dates(text)]


def batch2() -> list[dict] | None:
    global SKIP
    if not BATCH2.exists() or BATCH2.stat().st_size < 10_000:
        SKIP += 1
        return None
    return [json.loads(line) for line in BATCH2.open(encoding="utf-8")]


# --------------------------------------------------------------------------- #
def test_what_is_a_standalone_date() -> None:
    yes = [("Tarix: 12.05.2016", "12.05.2016"), ("Sənəd tarixi: 2022-09-15.", "2022-09-15"),
           ("Tarix: 22/08/2015", "22/08/2015"), ("12 noyabr 2022-ci il tarixində", "12 noyabr 2022"),
           ("Tarix: 14 İyun 2023", "14 İyun 2023"), ("Date: March 12, 1990.", "March 12, 1990"),
           ("on 12th of March 1990", "12th of March 1990"), ("12 марта 1990 г.", "12 марта 1990"),
           ("12 Mayıs 2020 tarihinde", "12 Mayıs 2020"), ("Doğum tarixi 03.08.1981-dir.", "03.08.1981"),
           ("14.05.2022\n10:05:12 - Görüş başladı", "14.05.2022"),
           ("| 12.05.2016 | Aktiv |", "12.05.2016"), ("12 avqust 2026", "12 avqust 2026"),
           ("Babarza,14:02,24.07.1973,AZ4509", "24.07.1973"),
           ("| e4:5f:01:50:75:85 | 20 iyun 1946 |", "20 iyun 1946"),
           ("Tarix: 12.05.2016 saat 10:15-də", "12.05.2016"),
           # D-18d: a number with a dot or comma after a date is not a time
           ("Ödəniş tarixi: 2025-04-15\t8500.50\tGecikmiş", "2025-04-15"),
           ("Qeydiyyat 08.08.1996 4.24.43.624 ünvanından", "08.08.1996"),
           ("Tarix: 2025-08-14\t1250,00\tGecikmə", "2025-08-14"),
           # batch 3: en/em dashes and the strict 2-digit-year shape
           ("Tarix: 12–11–2022", "12–11–2022"), ("Tarix: 2023—09-14 | Məbləğ", "2023—09-14"),
           ("| Tamamlandı 30.08.25    | 001 |", "30.08.25"), ("Tarix: 12/05/21 təsdiqləndi", "12/05/21")]
    for text, date in yes:
        check(found(text) == [date], f"standalone: {text!r}", found(text))
    no = ["[2016-11-05 14:22:01] INFO", "Date: 12.05.2021 10:15", "2025-03-12T10:15:00Z",
          "10:15 12.05.2021", "Tarix: 14 may 2021, 09:30", "[2018-09-14 22:1O:05] [DIAG]",
          "Дата: 15.09.2017 l4:10", "[2081-04-12 10:60:12] DEBUG",
          # D-18d: a malformed time after a date still makes a timestamp
          "[2017-11-15 09:122:50] DEBUG: Validating", "[2017-03-15 008:15:00] [PROCESS]",
          "[2025-01-15 0:905:44] [LOG]", "[2017-05-12 16:0:35] Müştəri", "[2017-06-15 14:3022] Post",
          "[2016-05-20 l4:2Z1:0] [LOG]", "[2026-04-15 11:OZ:42] [ERROR]", "[2016-04-22 1415:00] [CRIT]",
          "31.02.2020", "33.08.2009",
          "v2.14.09.1991", "2018-ci il", "may 2016", "05/2016", "1.2.16", "12-05-16",
          "versiya 10.12.21.5", "31.02.21", "INV-2016-05-12-7",
          "№ 2026/08/12-X", "Sistem loq kodu: 2018-09-12-X99", "versiya 1.2.2016.4"]
    for text in no:
        check(found(text) == [], f"not a standalone date: {text!r}", found(text))
    check(labelable("Tarix: 12.05.2016", 7, 17) == "", "a header date can be labelled as it stands")


def test_resolver_timestamps() -> None:
    """D-17 in the resolver: a date inside a timestamp is never placed as
    DATE, so labelling the standalone copy does not make the gates demand
    the timestamp copy too (125 batch-2 dates hung on this)."""
    text = "Tarix: 12.05.2018\n[12.05.2018 09:10:05] Sistem başladı.\nYenə 12.05.2018 tarixində."
    placed, _ = resolve_claims(text, [{"label": "DATE", "text": "12.05.2018"}])
    starts = sorted(e["start"] for e in placed)
    check(starts == [7, text.rindex("12.05.2018")], "only the two standalone copies are placed",
          starts)
    ents = [{"start": s, "end": s + 10, "label": "DATE", "text": "12.05.2018"} for s in starts]
    check(find_unlabeled_repeats(text, ents) == 0, "the timestamp copy is not a missing repeat")
    check(find_unlabelled_dates(text, ents) == [], "nothing left to label")
    log = "Sistem jurnalı:\n[14.04.2018 04:02] INFO: Session started.\n[14.04.2018 04:02] WARN: Latency."
    check(find_unlabelled_planned(log, [], [("DATE", "14.04.2018")]) == [],
          "batch 3: a planned date written only inside timestamps is not a missing DATE")
    check(find_unlabelled_planned("Tarix: 14.04.2018. " + log, [], [("DATE", "14.04.2018")])
          and all(f["start"] == 7 for f in find_unlabelled_planned("Tarix: 14.04.2018. " + log, [],
                                                                    [("DATE", "14.04.2018")])),
          "...but its standalone copy still is, alone")
    text = "Sənəd tarixi: 2017-11-15\n[2017-11-15 09:122:50] DEBUG: Validating"
    placed, _ = resolve_claims(text, [{"label": "DATE", "text": "2017-11-15"}])
    check([e["start"] for e in placed] == [14],
          "D-18d: the date before a malformed time (09:122) is not placed", placed)
    raw = BATCH2.with_name("sprint1_llm_b2.jsonl")
    if raw.exists() and raw.stat().st_size > 10_000:
        from piigen.standalone_dates import is_timestamp
        r = next(json.loads(line) for line in raw.open(encoding="utf-8") if '"llm_az_006627"' in line)
        i = r["text"].index("2017-11-15 09:122")
        check(is_timestamp(r["text"], i, i + 10), "batch 2: llm_az_006627's 09:122 makes a timestamp")


def test_doubled_letters() -> None:
    """D-16c: `Tərttərdə` for the planned `Tərtər` (llm_az_005577)."""
    def forms(t, label, v):
        return [(t[f.start:f.end], f.kind) for f in planned_forms(t, label, v)]
    check(("Tərttərdə", "misspelled") in forms("Biz Tərttərdə yaşayırıq.", "CITY", "Tərtər"),
          "a doubled letter is a misspelling of the planned value")
    check(("Sətarın", "misspelled") in forms("Sətarın sənədi.", "GIVENNAME", "Səttar"),
          "...and so is an undoubled one")
    check(forms("Tərtərdə yaşayırıq.", "CITY", "Tərtər") == [("Tərtərdə", "inflected")],
          "the correct inflected form is still labellable, not a misspelling")
    check(forms("Əlli manat ödədi.", "GIVENNAME", "Əli") == [], "a short name is left alone (Əli/Əlli)")
    check(forms("Bu tərttər deyil.", "CITY", "Tərtər") == [], "a lowercase word is not the capitalised name")
    raw = BATCH2.with_name("sprint1_llm_b2.jsonl")        # the clean file no longer has it
    recs = ([json.loads(line) for line in raw.open(encoding="utf-8")]
            if raw.exists() and raw.stat().st_size > 10_000 else None)
    if recs:
        r = next(r for r in recs if r["id"] == "llm_az_005577")
        planned = [(e["label"], e["value"]) for e in r["_spec"]["entities"]]
        miss = find_unlabelled_planned(r["text"], r["entities"], planned)
        check([m["text"] for m in miss] == ["Tərttərdə"], "batch 2: llm_az_005577 is caught", miss)


def test_document_date_in_briefs() -> None:
    from piigen.config import GeneratorConfig
    from piigen.llm import specs as S
    from piigen.llm.dspy_generate import build_fields
    from piigen.values import ValueFactory, ValuePool
    from piigen.validate import value_valid
    cfg = GeneratorConfig()
    cfg.edge_case_rate, cfg.negative_only_rate = 0.3, 0.1
    sampler = S.SpecSampler(cfg, ValueFactory(random.Random(3), ValuePool(state_path=None)),
                            random.Random(4))
    briefs = [sampler.sample(i) for i in range(3000)]
    dated = [b for b in briefs if any(e.role == "document_date" for e in b.entities)]
    eligible = [b for b in briefs if b.edge_case is None and not b.negative_only
                and b.doc_type not in S._UNDATED_DOC_TYPES]
    share = len(dated) / max(len(eligible), 1)
    check(abs(share - S.DOCUMENT_DATE_SHARE) < 0.05, "a document date in ~60% of dated briefs",
          round(share, 3))
    check(all(b.doc_type not in S._UNDATED_DOC_TYPES and not b.negative_only and b.edge_case is None
              for b in dated), "never in chats, logs, code, PII-free or edge-case briefs")
    values = [e.value for b in dated for e in b.entities if e.role == "document_date"]
    check(all(value_valid("DATE", v)[0] and found(f"Tarix: {v}") == [v] for v in values),
          "every document date is a valid standalone date")
    days = collections.Counter(int(next(p for p in v.replace("/", " ").replace(".", " ").replace("-", " ").split()
                                        if len(p) <= 2)) for v in values)
    check(max(days.values()) / len(values) < 0.08, "days are spread (batch 2: 56% on the 12th or 14th)",
          days.most_common(3))
    fields = build_fields(dated[0])
    line = next(x for x in fields["entities_to_embed"].splitlines() if "document's own date" in x)
    check(line.startswith("DATE: "), "the brief names it as the document's own date", line)
    # batch 3: a self-signalling time line names the Azerbaijani context word
    # again (61 attempts were rejected for writing `TIME: 14:10`)
    spec = dated[0]
    spec.entities = [S.PlannedEntity("TIME", "14:10"), S.PlannedEntity("DATE", "05.03.1968")]
    lines = build_fields(spec)["entities_to_embed"].splitlines()
    check('"saat"' in lines[0] and "exactly this format" in lines[0],
          "a self-signalling TIME line suggests saat/vaxt", lines[0])
    check('"tarix"' in lines[1], "...and a self-signalling DATE line tarix", lines[1])
    rules = (ROOT / "scripts" / "piigen" / "llm" / "dspy_generate.py").read_text(encoding="utf-8")
    check("Do not add any" in rules and "timestamp" in rules, "rule 10 allows no other full date")


def test_drift_and_steering() -> None:
    """Batch 3 audit (P2-6): counted in the label mix, planned document
    dates put DATE at ~3x its target in a 6,000-brief batch, past the run
    monitor's 2.5x stop. They are left out of the steering counts."""
    from piigen.config import GeneratorConfig
    from piigen.llm import specs as S
    from piigen.llm.monitor import DEFAULT_THRESHOLDS
    from piigen.values import ValueFactory, ValuePool
    ents = [{"label": "DATE", "text": "14.03.2016"}, {"label": "DATE", "text": "05.03.1968"},
            {"label": "GIVENNAME", "text": "Lalə"}]
    spec = {"entities": [{"label": "DATE", "value": "14.03.2016", "role": "document_date"},
                         {"label": "DATE", "value": "05.03.1968", "role": ""},
                         {"label": "GIVENNAME", "value": "Lalə"}]}
    check(S.steering_labels(ents, spec) == ["DATE", "GIVENNAME"],
          "only the document date's mention is left out", S.steering_labels(ents, spec))
    check(S.steering_labels(ents, {"entities": []}) == ["DATE", "DATE", "GIVENNAME"],
          "a record without a planned document date counts every label")
    # Batch 6: one log quoting the same IPv6 address 51 times stopped the run
    rep = [{"label": "IPV6_ADDRESS", "text": "2657:5632::7745"}] * 51 + [
        {"label": "IPV6_ADDRESS", "text": "fe80::1"}, {"label": "GIVENNAME", "text": "Lalə"},
        {"label": "GIVENNAME", "text": "Lalə"}]
    check(S.steering_labels(rep, {"entities": []}) == ["IPV6_ADDRESS", "IPV6_ADDRESS", "GIVENNAME"],
          "a value repeated in one document counts once", S.steering_labels(rep, {"entities": []}))
    cfg = GeneratorConfig()
    cfg.edge_case_rate, cfg.negative_only_rate, cfg.hard_negative_rate, cfg.adversarial_rate = 0.3, 0.1, 0.3, 0.2
    sampler = S.SpecSampler(cfg, ValueFactory(random.Random(3), ValuePool(state_path=None)),
                            random.Random(20261005))
    for i in range(6000):
        sp = sampler.sample(i)
        written = [{"label": e.label, "text": e.value} for e in sp.entities]
        sampler.record(S.steering_labels(written, sp), sp.lang, sp.doc_type)
    drift = (sampler.label_counts["DATE"] / sampler.total_mentions) / cfg.entity_weights["DATE"]
    warn = DEFAULT_THRESHOLDS["label_share_drift_high"].warn
    check(drift < warn, f"simulated batch 4: DATE drift stays below the monitor's warn level ({warn}x)",
          round(drift, 2))
    # Batch 5 (D-23e): contrast lessons plant IPv6+MAC, token+key and licence+ID
    # outside the mix. Left out of steering, no label may reach the stop level.
    stop = DEFAULT_THRESHOLDS["label_share_drift_high"].stop
    worst = max((sampler.label_counts[k] / sampler.total_mentions) / w
                for k, w in cfg.entity_weights.items() if w)
    check(worst < stop, f"simulated batch 5 settings: every label's drift stays below stop ({stop}x)",
          round(worst, 2))
    from piigen.llm import edge_cases as EC
    con = next(c for c in EC.CONTRAST_CASES if c.labels == ("IPV6_ADDRESS", "MAC_ADDRESS"))
    lesson = {"edge_case": {"id": con.case.id},
              "entities": [{"label": "IPV6_ADDRESS", "value": "2bab:b575::"},
                           {"label": "MAC_ADDRESS", "value": "F0:18:98:B9:50:51"}]}
    ents = [{"label": "IPV6_ADDRESS", "text": "2bab:b575::"}, {"label": "MAC_ADDRESS", "text": "F0:18:98:B9:50:51"},
            {"label": "GIVENNAME", "text": "Lalə"}]
    check(S.steering_labels(ents, lesson) == ["GIVENNAME"],
          "a contrast lesson's two values are left out of steering", S.steering_labels(ents, lesson))
    check(S.steering_labels(ents, {"edge_case": {"id": "ATK-01"}, "entities": lesson["entities"]})
          == ["IPV6_ADDRESS", "MAC_ADDRESS", "GIVENNAME"], "other edge cases still count every label")


def test_rejected_at_generation() -> None:
    from piigen.config import GeneratorConfig
    from piigen.llm.pipeline import assemble_document
    from piigen.llm.quality_filter import screen_record
    from piigen.llm.specs import DocumentSpec, PlannedEntity
    prose = ("Hörmətli müştəri, sizin müraciətiniz qəbul edildi və yaxın günlərdə nəzərdən "
             "keçiriləcək. Sənədlərin surətini də əlavə etməyinizi xahiş edirik. ")

    def spec(entities):
        return DocumentSpec(index=1, lang="az", doc_type="customer_email", doc_type_hint="x",
                            register="formal", band="medium", min_chars=400, max_chars=1100,
                            length_hint="", seed=1,
                            entities=[PlannedEntity(*e) for e in entities])

    def screen(text, ents=()):
        rec = {"text": text, "lang": "az", "entities": list(ents), "_decoys": []}
        return [p for p in screen_record(rec, run_base_gates=False, band="medium", planned=[],
                                         invented=True) if "D-17" in p]
    check(screen(prose + "Tarix: 12.05.2016.") == ["unlabelled date (D-17): '12.05.2016'"],
          "an unlabelled standalone date is rejected")
    check(screen(prose + "[12.05.2016 10:15] sistem işə düşdü.") == [], "a timestamp is not")
    text = prose + "Tarix: 12.05.2016. Lalə xanım zəng etdi. " + prose
    out = assemble_document(spec([("GIVENNAME", "Lalə")]), text, GeneratorConfig(), 0.0)
    check(not out.ok and out.reason == "quality: unlabelled date (D-17)",
          "assemble_document rejects a date nobody planned", out.reason)
    out = assemble_document(spec([("GIVENNAME", "Lalə"), ("DATE", "12.05.2016", "document_date")]),
                            text, GeneratorConfig(), 0.0)
    check(out.ok and ("DATE", "12.05.2016") in [(e["label"], e["text"]) for e in out.record["entities"]],
          "...and labels it when it is the planned document date", out.reason)
    check(out.ok and out.labels == ["GIVENNAME"],
          "...and leaves it out of the labels the sampler and monitor count", out.labels)


def test_relabel_script() -> None:
    """The relabel adds DATE spans that pass every gate, leaves timestamps,
    and writes untouched records byte for byte."""
    recs = batch2()
    if not recs:
        return
    # The committed clean file is already relabelled: take its DATE labels
    # that no brief planned off again, and the script must put them back.
    def unrelabelled(r):
        planned = {e["value"] for e in r["_spec"]["entities"] if e["label"] == "DATE"}
        return {**r, "entities": [e for e in r["entities"]
                                  if e["label"] != "DATE" or e["text"] in planned]}
    sample = [json.dumps(unrelabelled(r), ensure_ascii=False) + "\n" for r in recs[:400]]
    with tempfile.TemporaryDirectory() as tmp:
        src, dst = Path(tmp) / "in.jsonl", Path(tmp) / "out.jsonl"
        src.write_text("".join(sample), encoding="utf-8")
        run = subprocess.run([sys.executable, str(ROOT / "scripts" / "relabel_standalone_dates.py"),
                              "--batch", str(src), "--out", str(dst), "--report", str(Path(tmp) / "r.json")],
                             capture_output=True, text=True, encoding="utf-8")
        check(run.returncode == 0, "the relabel runs", run.stderr[-300:])
        stats = collections.Counter(
            json.loads((Path(tmp) / "r.json").read_text(encoding="utf-8"))["stats"])
        check(stats["spans_added"] > 100 and stats["unlabelled_dates_after"] == 0,
              "dates added, none left", stats)
        out = dst.read_text(encoding="utf-8").splitlines(keepends=True)
        same = [a == b for a, b in zip(sample, out)]
        changed = [json.loads(b) for a, b in zip(sample, out) if a != b]
        check(len(out) == len(sample) and sum(same) == len(sample) - stats["docs_changed"],
              "untouched records are written byte for byte")
        check(all(json.loads(a)["text"] == json.loads(b)["text"] for a, b in zip(sample, out)),
              "text is never changed")
        check(all(e["label"] == "DATE" for r, a in zip(changed, [json.loads(a) for a, b in zip(sample, out) if a != b])
                  for e in r["entities"] if e not in a["entities"]), "only DATE spans are added")
        gate = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_corpus.py"), str(dst),
                               "--skip-dedup"], capture_output=True, text=True, encoding="utf-8")
        check(gate.returncode == 0, "validate_corpus passes on the relabelled sample", gate.stdout[-400:])


def test_reports() -> None:
    """The batch audit and validate_corpus both count what is left (D-17)."""
    from piigen.audit_llm_batch import sweep_dates
    recs = [{"id": "a", "text": "Tarix: 12.05.2016. Salam.", "entities": []},
            {"id": "b", "text": "[12.05.2016 10:15] Salam.", "entities": []},
            {"id": "c", "text": "Tarix: 12.05.2016. Salam.",
             "entities": [{"start": 7, "end": 17, "label": "DATE", "text": "12.05.2016"}]}]
    got = sweep_dates(recs)
    check(got["documents"] == 1 and got["dates"] == 1, "the audit counts one unlabelled date", got)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "c.jsonl"
        text = ("Hörmətli müştəri, Tarix: 12.05.2016 olan müraciətiniz qəbul edildi. "
                "Əlaqə nömrəsi: +994 50 123 45 67, zəng edin.")
        i = text.index("+994")
        rec = {"id": "x1", "lang": "az", "text": text,
               "entities": [{"start": i, "end": i + 17, "label": "TELEPHONENUM", "text": text[i:i + 17]}]}
        path.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_corpus.py"), str(path),
                              "--skip-dedup", "--json", str(Path(tmp) / "r.json")],
                             capture_output=True, text=True, encoding="utf-8")
        counts = json.loads((Path(tmp) / "r.json").read_text(encoding="utf-8"))["counts"]
        check(counts.get("unlabelled_standalone_date") == 1,
              "validate_corpus reports it (informational)", counts)


def test_targeted_builder() -> None:
    from piigen.targeted import builder as B
    from piigen.validate import declared_decoy_spans
    docs = B.TargetedBuilder(seed=7, n_docs=500).build()
    bad = [r["id"] for r in docs
           if find_unlabelled_dates(r["text"], r["entities"], declared_decoy_spans(r)[0])]
    check(not bad, "the targeted builder leaves no standalone date unlabelled", bad[:3])


TESTS = [("what a standalone date is", test_what_is_a_standalone_date),
         ("the resolver skips timestamps", test_resolver_timestamps),
         ("doubled-letter misspellings (D-16c)", test_doubled_letters),
         ("briefs plan the document date", test_document_date_in_briefs),
         ("generation rejects an unlabelled date", test_rejected_at_generation),
         ("document dates stay out of steering and drift", test_drift_and_steering),
         ("relabel_standalone_dates.py", test_relabel_script),
         ("audit and validate_corpus report it", test_reports),
         ("targeted builder", test_targeted_builder)]

if __name__ == "__main__":
    for name, fn in TESTS:
        print(name)
        fn()
    print("=" * 60)
    print(f"PASSED {PASS}   FAILED {FAIL}" + (f"   SKIPPED {SKIP}" if SKIP else ""))
    print("=" * 60)
    for f in FAILURES:
        print("  FAIL:", f)
    sys.exit(1 if FAIL else 0)
