"""D-51h: the native-check list for the team (every new Azerbaijani sentence,
phrase and key of the v4 targeted data), with real examples from a build.

    python reports/v4_generator/make_native_check.py BUILD.jsonl > reports/v4_generator/native_check.md
"""
from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.negatives import ANCHORED_DECOYS  # noqa: E402
from piigen.targeted import frames_v4 as V4  # noqa: E402
from piigen.targeted.stats import D51_KINDS  # noqa: E402

# sentences the team would like a second look at (reason in brackets)
FLAGS = {
    "Qaimədə indeks kimi {v}{tail} göstərilib.":
        "with the tail: `indeks kimi 4821 məhsul kodu` -- does `indeks kimi` + a product code read as a contradiction?",
    "Bu gün {v} danışdım, oradakı filial sənədləri sabah göndərəcək.":
        "a town with the instrumental (`Gəncəylə danışdım`): natural, or only with `ilə` separate?",
    "İclasda müdir <<Maliyyə Şöbəsinin>> illik hesabatını təqdim edib.":
        "role word right before a department in the genitive: word order natural?",
    "Hər istifadəçi üçün token {v} dəqiqə etibarlı olur.":
        "`token 15 dəqiqə etibarlı olur`: natural?",
}
NEW_KINDS = {"voen_short_number", "fin_short_number", "id_card_short_number", "token_short_number",
             "api_key_short_number", "code_in_name_slot", "room_code", "door_code", "mac_fragment_dashed",
             "iban_fragment_short", "ipv4_short_over_255", "ipv4_three_octets", "ipv4_placeholder",
             "card_wrong_length"}


def show(s: str) -> str:
    return s.replace("{v}", "⟨value⟩").replace("{tail}", "⟨ məhsul kodu⟩").replace("<<", "**").replace(">>", "**")


def main() -> int:
    build = Path(sys.argv[1])
    recs = [json.loads(l) for l in build.open(encoding="utf-8")]
    rng = random.Random(15)
    print("# D-51h · New Azerbaijani text in the v4 targeted data: native check for the team\n")
    print("Every new sentence, phrase and key the v4 generator writes (`scripts/piigen/targeted/frames_v4.py`, "
          "new anchor phrases in `negatives.py`, new CSV keys in `formats.py`). `⟨value⟩` is where a value goes: "
          "a real one (masked) or a look-alike (left unmasked). Section 3 shows real documents from the 25,000-document build.\n")
    print("**Please mark** any sentence that reads unnatural or wrong, and give the fix. "
          "Sentences marked ⚑ are the ones I'd like a second look at.\n")
    print("## 1. Sentences (`frames_v4.py`)\n")
    pools = defaultdict(list)
    for pool, s in V4.native_check_list():
        pools[pool].append(s)
    n = 0
    for pool, items in pools.items():
        print(f"### {pool}\n")
        for s in items:
            n += 1
            flag = f" ⚑ *{FLAGS[s]}*" if s in FLAGS else ""
            print(f"{n}. {show(s)}{flag}")
        print()
    print("## 2. Short phrases and keys\n")
    print("Anchor phrases of the new look-alike kinds (`negatives.py`), used inside other sentences:\n")
    for lab, kinds in ANCHORED_DECOYS.items():
        for k in kinds:
            if k.kind in NEW_KINDS:
                n += 1
                print(f"{n}. `{k.kind}` ({lab}): " + " · ".join(show(a) for a in k.anchors))
    n += 1
    print(f"{n}. New snake_case keys in CSV/JSON/log/config: `şəxsiyyət_vəsiqəsi`, `sürücülük_vəsiqəsi`")
    n += 1
    print(f"{n}. D-51i: a spelled date before `tarixində` now ends `… 2016-cı il tarixində` "
          "(`-cı/-ci/-cu/-cü` by the year's last spoken word, as you confirmed for numbers); the date span stops at the year\n")
    print("## 3. Examples from the build (one per family; the masked values in **bold**, look-alikes in _italics_)\n")
    fams = defaultdict(list)
    for r in recs:
        f = r["_spec"]["family"]
        if f == "cross_anchor":
            f = f"cross_anchor/{r['_spec']['cross_slot']}"
        fams[f].append(r)
    for f in ("cross_anchor/short_number", "cross_anchor/name_org", "cross_anchor/room_code", "cross_anchor/zip_code",
              "cross_anchor/mac_fragment", "cross_anchor/iban_fragment", "cross_anchor/ipv4", "locative",
              "slot_invalid", "place_verbs", "short_keys"):
        if not fams.get(f):
            continue
        r = rng.choice([x for x in fams[f] if len(x["text"]) < 900] or fams[f])
        marks = sorted([(e["start"], e["end"], "**") for e in r["entities"]] +
                       [(x["start"], x["end"], "_") for x in r["_decoys"]], reverse=True)
        t = r["text"]
        for s, e, m in marks:
            t = t[:s] + m + t[s:e] + m + t[e:]
        print(f"**{f}** (`{r['id']}`)\n")
        print("> " + t.replace("\n", "\n> ") + "\n")
    nl = [r for r in fams["namelist"] if r["_spec"].get("control_list") or r["_spec"].get("signature") == "title_only"]
    for r in rng.sample(nl, min(2, len(nl))):
        t = r["text"]
        for s, e, m in sorted([(e["start"], e["end"], "**") for e in r["entities"]] +
                              [(x["start"], x["end"], "_") for x in r["_decoys"]], reverse=True):
            t = t[:s] + m + t[s:e] + m + t[e:]
        print(f"**namelist with controls** (`{r['id']}`)\n")
        print("> " + t.replace("\n", "\n> ") + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
