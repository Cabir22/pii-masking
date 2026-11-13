"""EXPERIMENT 6 -- context effects and the mechanism (brief sections 16, 23).

exp2 established WHAT helps ('Label: value' beats a bare value by ~25-30
recall points). This asks WHY, by separating two candidate mechanisms that
the earlier work in this project treated as one:

  (a) LABEL ADJACENCY -- a value is easier when a field label sits next to it.
  (b) POSITION DECAY  -- a value is harder the more tokens precede it in the
      same inference call (the 'context-length collapse' documented in
      docs/pii_guard_model_notes.md, which chunking fixes).

These make different predictions. If (b) alone were true, a bare value early
in the text would do as well as a labelled one. If (a) alone were true,
position would not matter. Both are tested on the same values.

Part 3 runs the brief's section 16 context ladder verbatim, per entity type,
so the effect can be reported per label rather than only in aggregate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness  # noqa: E402

harness.setup_paths()

import spec  # noqa: E402


def main() -> None:
    detect = harness.detect_fn_factory()
    harness.RESULTS.mkdir(parents=True, exist_ok=True)
    out = {}

    # ---------- Part 1: position decay, bare values ----------
    # One target value placed at position k in a run of bare filler values.
    # Filler is other real values of other labels, so the text stays the same
    # KIND of content and only the target's position changes.
    print("=== Part 1: does position in a bare-value run matter? ===")
    print(f"{'lang':5s} " + " ".join(f"pos{k:<2d}" for k in [0, 5, 10, 20, 40]))
    part1 = []
    for lang in spec.LANGS:
        recs = spec.records(lang)
        targets = [(r["GIVENNAME"], "GIVENNAME") for r in recs] + \
                  [(r["CITY"], "CITY") for r in recs]
        filler = [r[k] for r in recs
                  for k in ("AZ_VOEN", "ZIPCODE", "BUILDINGNUM", "TELEPHONENUM")]
        row = []
        for k in [0, 5, 10, 20, 40]:
            hits = 0
            for val, lab in targets:
                pre = [filler[i % len(filler)] for i in range(k)]
                text = " ".join(pre + [val])
                got = {(s["label"], text[s["start"]:s["end"]])
                       for s in detect(text)}
                hits += (lab, val) in got
            rate = hits / len(targets)
            row.append(rate)
            part1.append({"lang": lang, "position": k, "recall": rate})
        print(f"{lang:5s} " + " ".join(f"{v:>5.0%}" for v in row))
    out["position_decay_bare"] = part1

    # ---------- Part 2: same, but WITH the field label attached ----------
    print("\n=== Part 2: same positions, value carries its own label ===")
    print(f"{'lang':5s} " + " ".join(f"pos{k:<2d}" for k in [0, 5, 10, 20, 40]))
    part2 = []
    for lang in spec.LANGS:
        recs = spec.records(lang)
        labels = spec.FIELD_LABELS[lang]
        targets = [(r["GIVENNAME"], "GIVENNAME") for r in recs] + \
                  [(r["CITY"], "CITY") for r in recs]
        filler = [f'{labels["AZ_VOEN"]}: {r["AZ_VOEN"]}' for r in recs] + \
                 [f'{labels["ZIPCODE"]}: {r["ZIPCODE"]}' for r in recs]
        row = []
        for k in [0, 5, 10, 20, 40]:
            hits = 0
            for val, lab in targets:
                pre = [filler[i % len(filler)] for i in range(k)]
                text = " ".join(pre + [f"{labels[lab]}: {val}"])
                got = {(s["label"], text[s["start"]:s["end"]])
                       for s in detect(text)}
                hits += (lab, val) in got
            rate = hits / len(targets)
            row.append(rate)
            part2.append({"lang": lang, "position": k, "recall": rate})
        print(f"{lang:5s} " + " ".join(f"{v:>5.0%}" for v in row))
    out["position_decay_labeled"] = part2

    # ---------- Part 3: the brief's context ladder, per entity type ----------
    print("\n=== Part 3: context ladder, per entity type (all langs pooled) ===")
    LADDER = {
        "bare":        lambda lbl, v: v,
        "label_colon": lambda lbl, v: f"{lbl}: {v}",
        "short_sent":  None,   # per-language, built below
        "paragraph":   None,
    }
    SENT = {
        "az": {"pre": "Onun məlumatı belədir: ", "post": " olaraq qeyd olunub."},
        "en": {"pre": "Their detail is as follows: ", "post": " has been recorded."},
        "ru": {"pre": "Его данные следующие: ", "post": " было записано."},
        "tr": {"pre": "Bilgileri şöyledir: ", "post": " olarak kaydedilmiştir."},
    }
    PARA = {
        "az": ("Müştəri xidmətləri şöbəsi bu gün yeni müraciəti qeydə aldı. "
               "Sənədlər yoxlanıldı və təsdiqləndi. "),
        "en": ("The customer service department registered a new request today. "
               "The documents were checked and approved. "),
        "ru": ("Отдел обслуживания клиентов сегодня зарегистрировал новую заявку. "
               "Документы были проверены и одобрены. "),
        "tr": ("Müşteri hizmetleri bugün yeni bir talep kaydetti. "
               "Belgeler kontrol edildi ve onaylandı. "),
    }

    per_label = {}
    for k in spec.FIELD_ORDER:
        per_label[k] = {}
        for cond in ["bare", "label_colon", "short_sent", "paragraph"]:
            hits = tot = 0
            for lang in spec.LANGS:
                lbl = spec.FIELD_LABELS[lang][k]
                for r in spec.records(lang):
                    v = r[k]
                    if cond == "bare":
                        text = v
                    elif cond == "label_colon":
                        text = f"{lbl}: {v}"
                    elif cond == "short_sent":
                        text = SENT[lang]["pre"] + v + SENT[lang]["post"]
                    else:
                        text = (PARA[lang] + SENT[lang]["pre"] + v
                                + SENT[lang]["post"])
                    got = {(s["label"], text[s["start"]:s["end"]])
                           for s in detect(text)}
                    hits += (k, v) in got
                    tot += 1
            per_label[k][cond] = hits / tot
    out["context_ladder"] = per_label

    print(f"{'entity':26s} {'bare':>7s} {'Label:':>8s} {'sentence':>9s} {'paragraph':>10s}")
    print("-" * 64)
    for k in spec.FIELD_ORDER:
        d = per_label[k]
        print(f"{k:26s} {d['bare']:>6.0%} {d['label_colon']:>7.0%} "
              f"{d['short_sent']:>8.0%} {d['paragraph']:>9.0%}")
    for cond in ["bare", "label_colon", "short_sent", "paragraph"]:
        m = sum(per_label[k][cond] for k in spec.FIELD_ORDER) / len(spec.FIELD_ORDER)
        print(f"{'MEAN' if cond=='bare' else '':26s}" if False else "", end="")
    print("-" * 64)
    means = {c: sum(per_label[k][c] for k in spec.FIELD_ORDER) / len(spec.FIELD_ORDER)
             for c in ["bare", "label_colon", "short_sent", "paragraph"]}
    print(f"{'MEAN':26s} {means['bare']:>6.0%} {means['label_colon']:>7.0%} "
          f"{means['short_sent']:>8.0%} {means['paragraph']:>9.0%}")

    p = harness.RESULTS / "exp6_context.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
