"""Build scripts/piigen/v4_clean_lexicon.json, the frozen word lists of the v4
cleaning pass (D-51g, `piigen.v4_clean`).

`v4_clean.clean_doc` is a pure function of one record: every corpus-level
fact it needs is read from this file, so a cleaned record does not depend on
which other records happen to be in the run. The file is built once from the
sources of a v4 build and committed with the code; rebuild it only when the
sources change, and say so in the data card.

    python scripts/build_v4_clean_lexicon.py \
        [--targeted data/raw/runb_v3verify_targeted.jsonl] [--out scripts/piigen/v4_clean_lexicon.json]

What it holds (keys are `resolver.match_key` forms: lower-case, diacritics
folded, one character for one):

  given_excluded    pool given names (locales az_first_names_m/f) that are
                    NOT relabelled as names, with the reason:
                      role    a role, title or field word (`Agent`, `Tarix`)
                      city    labelled CITY more often than GIVENNAME
                      common  written lower-case in running text 20+ times
                              and not commonly labelled as a name (labelled
                              GIVENNAME < 20 times or < 1/10 of its lower-case
                              uses); the targeted homograph names (`Dəniz`,
                              `Ümid`, ...) are names by D-10 and stay allowed
                      native  NATIVE_NOT_NAMES (native check);
                              NATIVE_NAMES are allowed whatever the counts
  given_borderline  pool names a native speaker should check: common words
                    that are also real names (lower-case 20+ times and
                    labelled GIVENNAME 5+ times), with the decision taken
  given_lowercase_uses
                    allowed pool names that are also written lower-case 3+
                    times (`ümid`, `aydın`), with the count: another
                    sentence-initial use of such a name in the same document
                    may be the ordinary word, so the pass does not guess
  surname_vocab     strings labelled SURNAME 2+ times, never or rarely (< 5)
                    written lower-case: a second token of a speaker tag,
                    signature or header line is a surname only if it is here
                    or has a surname ending
  surname_shaped_common
                    surname-shaped words (`-ov`, `-li`, `-zadə` ...) written
                    lower-case 3+ times (`maraqlı`, `təhlükəli`): never a
                    surname by shape alone
  surname_stoplist  R7: strings labelled SURNAME in the old corpus that are
                    common words (lower-case 5+ times and 2x more often than
                    labelled SURNAME, not a pool given name), plus the label-
                    noise report's list; unlabelled only without name context

Read-only on every source; writes the one JSON file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.resolver import match_key                      # noqa: E402
from piigen.targeted.homographs_az import HOMOGRAPHS        # noqa: E402

OLD = ROOT / "data/processed/merged_relabeled_swept_dated"
LLM = [ROOT / f"data/raw/sprint1_llm_b{i}.clean.jsonl" for i in range(1, 7)]
TARGETED = ROOT / "data/raw/runb_v3verify_targeted.jsonl"
POOLS = ROOT / "scripts/piigen/locales/data"
OUT = ROOT / "scripts/piigen/v4_clean_lexicon.json"

WORD = re.compile(r"[^\W\d_]+")
SURNAME_SHAPE = re.compile(r"(?:ov|ova|yev|yeva|ev|eva|zade|li|lu|beyli)$")

# Role, title and field words that are also in the given-name pools or look
# like a speaker tag. Never a name in a speaker, signature or header slot.
ROLE_WORDS = """
Agent Müştəri Musteri Operator Sistem Admin Dəstək Destek Tarix Mövzu Qeyd Rəsmi Resmi Menecer Manager
Bot Support User İstifadəçi Klient Abunəçi Həkim Pasient Xəstə Vəkil Hakim Katib Direktor Müdir Rəhbər
Sədr Mütəxəssis Məsləhətçi Kassir Satıcı Sürücü Kuryer Usta Tələbə Müəllim Cənab Xanım Bəy Ağa Hörmətli
Status Səbəb Cavab Sual Nəticə Diqqət Xəbərdarlıq Məlumat Ünvan Mənbə Qəbul Göndərən Alıcı Kimdən Kimə
Salam Info Error Debug Warn Log Note Subject From To Date Ad Soyad Ata Ana Qardaş Bacı Dost Yoldaş Şahid
Namizəd Sakin Rəis Zabit Həkimə Gəlin Qonaq Adam İnsan Ali Nümunə Müşavir Nümayəndə Təmsilçi Əməkdaş
Komanda Şirkət Bank Xidmət Mərkəz Şöbə Bölmə İdarə Müdiriyyət Rəhbərlik Heyət Qrup Server Monitorinq
Müəllimə Katibə Mühasib Mühəndis Nəzarətçi Müfəttiş Hüquqşünas Ekspert Koordinator Mütəxəssis Kuratör
Xala Dayı Əmi Bibi Nənə Baba Qonşu Bacı Qız Oğul Gəlin Kürəkən Uşaq Körpə Müəllif Redaktor Şair Yazıçı
""".split()

# The label-noise report's false SURNAME labels (v3_label_noise_report.md 4.8),
# always in the stoplist (context still protects a real surname).
# `Sabirli` is added by hand: in the old corpus it is `səbirli olun` ("be
# patient") misspelt, 7 of 7 sweep labels (a real `Sabirli` in a name list
# keeps its label through the context check).
REPORT_STOPLIST = ["Şəkərli", "Xeyirli", "Etibarlı", "Etibarli", "Suretli", "Suratli", "Sürətli",
                   "Şiddətli", "Lazımlı", "Amili", "Merkezli", "Miqyaslı", "Zamanlı", "Ehtiyatli",
                   "Sabirli"]


# The native check (15 Oct 2026, D-51g (4)), over every pool name the
# counts above exclude or put on the borderline that fills a name slot in the
# sources (speaker tag, signature, header, self-introduction, before a
# surname): NATIVE_NAMES are a person's name there and are relabelled;
# NATIVE_NOT_NAMES never are. Both override the counts and ROLE_WORDS.
NATIVE_NAMES = """
Adım Ağa Ali Babək Cəbrayıl Demir Duran Dünyam Əməl Əsli Gül Həkim İntizam Kifayət Laçın Macəra Malı Malik
Mənzərə Mərkəz Nizami Sadiq Sakin Sam Səmimi Səyyar Şad Uğur Zabit
""".split()
NATIVE_NOT_NAMES = "Nəzakət Səfər Zamin".split()


def pool(*names: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for n in names:
        for line in (POOLS / n).open(encoding="utf-8"):
            w = line.strip()
            if w and not w.startswith("#"):
                out.setdefault(match_key(w), w)
    return out


def standalone(t: str, s: int, e: int) -> bool:
    """A word of running text, not a piece of a handle, an address, a file
    name or an identifier (`elvin.m@…`, `murad_92`, `/leyla/`): the lower-case
    counts measure how often a word is an ordinary word."""
    before = t[s - 1] if s else " "
    after = t[e] if e < len(t) else " "
    after2 = t[e + 1] if e + 1 < len(t) else " "
    if before.isalnum() or before in "@._/-\\#=:+&%$" or after in "@_/\\#=-+&%$" or after.isdigit():
        return False
    return not (after in ".:" and after2.isalnum())


def iter_sources(targeted: Path):
    drop = {}
    for line in (OLD / "az_drop_list.jsonl").open(encoding="utf-8"):
        r = json.loads(line)
        drop[r["id"]] = r["split"]
    for split in ("train", "val", "test"):
        for line in (OLD / f"{split}.docs.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            if r["lang"] == "az" and drop.get(r["id"]) != split:
                yield "old", r
    for q in LLM:
        for line in q.open(encoding="utf-8"):
            if line.strip():
                yield "llm", json.loads(line)
    for line in targeted.open(encoding="utf-8"):
        if line.strip():
            yield "targeted", json.loads(line)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--targeted", type=Path, default=TARGETED)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    lower: Counter = Counter()
    labelled = {lab: Counter() for lab in ("GIVENNAME", "SURNAME", "CITY")}
    old_surname: Counter = Counter()
    ndocs: Counter = Counter()
    for src, d in iter_sources(args.targeted):
        ndocs[src] += 1
        t = d["text"]
        covered = bytearray(len(t))
        for e in d["entities"]:
            covered[e["start"]:e["end"]] = b"\x01" * (e["end"] - e["start"])
            if e["label"] in labelled:
                k = match_key(t[e["start"]:e["end"]])
                labelled[e["label"]][k] += 1
                if src == "old" and e["label"] == "SURNAME":
                    old_surname[k] += 1
        for m in WORD.finditer(t):
            if not covered[m.start()] and m.group(0)[0].islower() and standalone(t, m.start(), m.end()):
                lower[match_key(m.group(0))] += 1

    given_pool = pool("az_first_names_m.txt", "az_first_names_f.txt")
    homographs = {match_key(h) for h in HOMOGRAPHS}
    roles = {match_key(w) for w in ROLE_WORDS}
    native_yes, native_no = {match_key(w) for w in NATIVE_NAMES}, {match_key(w) for w in NATIVE_NOT_NAMES}
    missing = (native_yes | native_no) - set(given_pool)
    if missing:
        raise SystemExit(f"native decisions for names not in the pools: {sorted(missing)}")
    excluded, borderline, lowercase_uses = {}, [], {}
    for k, name in sorted(given_pool.items()):
        lo, g, c = lower[k], labelled["GIVENNAME"][k], labelled["CITY"][k]
        common = lo >= 20 and not (g >= 20 and g * 10 >= lo)
        why = ("" if k in native_yes else "native" if k in native_no else
               "role" if k in roles else "city" if c > g else
               "" if k in homographs else "common" if common else "")
        if why:
            excluded[k] = {"name": name, "reason": why, "lower": lo, "labelled_givenname": g,
                           "labelled_city": c}
        if not why and lo >= 3:
            lowercase_uses[k] = lo
        if lo >= 20 and g >= 5 and why != "role":
            borderline.append({"name": name, "lower": lo, "labelled_givenname": g,
                               "decision": "excluded (native check)" if k in native_no
                               else "allowed (native check)" if k in native_yes
                               else "excluded" if why else "allowed (homograph name, D-10)"
                               if k in homographs else "allowed"})

    surname_vocab = sorted(k for k, n in labelled["SURNAME"].items()
                           if n >= 2 and lower[k] < 5 and len(k) >= 3 and " " not in k)
    shaped_common = sorted(k for k, n in lower.items() if n >= 3 and SURNAME_SHAPE.search(k) and len(k) >= 5)
    stop = {k for k, n in old_surname.items()
            if " " not in k and lower[k] >= 5 and lower[k] >= 2 * labelled["SURNAME"][k]
            and k not in given_pool}
    stop |= {match_key(w) for w in REPORT_STOPLIST}
    stoplist = sorted({k: None for k in stop})

    lex = {
        "version": "v4-clean-lexicon-1",
        "built_by": "scripts/build_v4_clean_lexicon.py",
        "sources": {"old": OLD.relative_to(ROOT).as_posix() + " (az, minus az_drop_list.jsonl)",
                    "llm": [q.relative_to(ROOT).as_posix() for q in LLM],
                    "targeted": (args.targeted.resolve().relative_to(ROOT).as_posix()
                                 if args.targeted.resolve().is_relative_to(ROOT) else str(args.targeted))},
        "documents": dict(ndocs),
        "given_excluded": excluded,
        "given_borderline": sorted(borderline, key=lambda r: -r["lower"]),
        "given_lowercase_uses": dict(sorted(lowercase_uses.items())),
        "surname_vocab": surname_vocab,
        "surname_shaped_common": shaped_common,
        "surname_stoplist": stoplist,
        "surname_stoplist_counts": {k: {"lower": lower[k], "labelled_surname": labelled["SURNAME"][k],
                                        "labelled_surname_old": old_surname[k]} for k in stoplist},
    }
    data = json.dumps(lex, ensure_ascii=False, indent=1, sort_keys=False) + "\n"
    args.out.write_text(data, encoding="utf-8", newline="\n")
    print(f"documents {dict(ndocs)}")
    print(f"given pool {len(given_pool):,}: excluded {len(excluded):,} "
          f"({dict(Counter(v['reason'] for v in excluded.values()))}), borderline {len(borderline)}")
    print(f"surname vocab {len(surname_vocab):,}, surname-shaped common {len(shaped_common):,}, "
          f"stoplist {len(stoplist)}")
    print(f"-> {args.out}  sha256 {hashlib.sha256(data.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
