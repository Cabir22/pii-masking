"""D-51f / D-51g: the deterministic cleaning pass over the v4 training sources.

    from piigen.v4_clean import clean_doc
    cleaned, rules = clean_doc(record)      # cleaned is None: drop the record

One pure function of one record. `text` is never edited; entities stay sorted,
non-overlapping and exact (`text[start:end] == entity["text"]`). A label that
is removed is declared in `_decoys` at the same place (what it is, and what it
resembles), as the targeted builder and `relabel_ssh_public_keys.py` do, so
every gate that re-resolves the record (validate_corpus's resolver_drift,
repeat mentions, planned values) agrees with the cleaned labels. A label that
is added is added on EVERY occurrence the resolver would place (D-9 suffixes
included), the corpus's every-occurrence rule. The record gets `_v4_clean`:
the ids of the rules that changed it.

The rules (ids as in the D-51g list, the v3 root-cause analysis, sections 6-7):

  R1  drop, old corpus only (`_old`): D-47a explained typos, D-47b a bracketed
      self-correction in a formal doc type, D-47e an unfilled placeholder,
      D-45b one value labelled 20+ times -- exactly drop_before_v3.py's
      detectors, which were applied to the LLM files only.
  R2  timestamps (D-17, D-51f): no TIME or DATE label inside a date+time stamp
      (any horizontal space between them: standalone_dates.STAMP_SPACE), and no
      TIME label on a chat or log line stamp (`[10:16] Elvin:`, `10:16 -
      Agent:`, `Elvin [10:16]:`, `[10:16] ERROR`). TIME stays for clock times
      in the text (`saat 14:30`), in timelines (`- 14:37: xəbərdarlıq`) and in
      CSV cells (`05:47;FD00::1`).
  R3  `-ci il` out of DATE (real-text guide): `12 mart 2016-cı il` -> `12 mart
      2016`, also `-cu/-cü`, en/em dash, capitals, the bare suffix.
  R4  persona names (D-10, D-15c): an unlabelled name in a chat speaker tag, a
      self-introduction (`Mən Leyla,`, `Mənim adım …`, `Mən Ayseldir`), the
      line after a closing (`Hörmətlə,⏎Leyla Məmmədova`), a `From:/Kimdən:/
      Göndərən:` header, and `S. Qəmbərov` (SURNAME; the initial stays out).
      A given name must be in the az pools and not in the lexicon's exclusion
      list (roles, field words, common words, cities); a surname must be in the
      corpus's SURNAME vocabulary or have a surname ending without being a
      common word. When another use of the same name in the document may be
      the ordinary word (or a shop name), the pass does not guess: the record is
      dropped (D-15c: an unlabelled real name costs more than a document).
  R5  half-labelled names: an unlabelled pool given name directly before a
      labelled SURNAME, or right after it at the head of a surname-first list
      line, becomes GIVENNAME; in `Given Father oğlu/qızı` the father's name is
      GIVENNAME too and `oğlu/qızı` stays outside (D-39b).
  R6  a CITY heading an institution or project name (`Salyan Rayon
      Məhkəməsi`, `Bakı Dövlət Universiteti`, `Lerik layihəsi`) is not PII
      (D-2): unlabelled, declared `policy_city_in_institution` /
      `policy_city_as_project`.
  R7  false SURNAME labels: in the old corpus, a stoplist word (`Şəkərli`,
      `Xeyirli`, ...; lexicon) labelled SURNAME with no name context around it;
      in every source, a name heading an institution (`Heydər Əliyev
      Beynəlxalq Hava Limanı`, `Nərimanov Liseyi`, `… adına Bakı …`).
  R8  drop a record holding a checksum-only look-alike (D-51d):
      `LOYALTY_CARD_LUHN_BAD`, `card_luhn_invalid`, `tracking_code_15_16`,
      `IBAN_BAD_CHECKSUM`; old-corpus records declare look-alikes only as
      strings in `_spec`, so there the kind is read from the string's shape (16
      digits failing Luhn, an IBAN failing mod 97); a 16-digit one drops the
      record only with a card word within 4 words (D-51j).
  R9  unlabelled ages (`Yaş: 59`, `52 yaşında`, `59 yaş`): AGE when 0-120 and
      not a range (`18–30 yaş`, `2-4 yaş arası`); a figurative age (`sanki 80
      yaşında`) cannot be decided and drops the record.
  R10 clock times after a time word (v4 data audit A1): a valid `HH:MM`,
      `HH:MM:SS` or `7:30 AM` right after `saat`/`Saat:`/`vaxtı:`/`zamanı:`/
      `İş saatları:` (forms: TIME_WORDS) is TIME, and both ends of a range
      (`10:00 – 14:30`, `09:00-dan 18:00-a qədər`); not inside a date+time
      or line stamp (R2, D-51f), not on a declared look-alike, not before
      `versiya…` (`saat 14:30 versiyası`, v4.1 item 7: a look-alike). Every
      occurrence of the value is labelled; one that is a stamp is declared
      TIMESTAMP instead.

Finally the gate: the record must fail no check it passed before (repeat
mentions, resolver drift, span boundaries, anchors, planned values,
`validate_example`, and D-45b's 20 repeats); otherwise it is dropped as `GATE`.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from . import checksums as CK
from .anchors import ANCHOR_REQUIRED, has_anchor
from .meta_noise import explained_typos, is_formal, placeholders, self_corrections
from .resolver import find_unlabeled_repeats, find_unlabelled_planned, match_key, resolve_claims
from .standalone_dates import STAMP_SPACE, is_timestamp
from .validate import declared_decoy_spans, span_boundary_problems, validate_example

HERE = Path(__file__).resolve().parent
LEXICON_PATH = HERE / "v4_clean_lexicon.json"
POOLS = HERE / "locales" / "data"

RULE_IDS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10", "GATE")

# D-51d: the look-alikes that differ from a real value only by a checksum.
CHECKSUM_ONLY_KINDS = frozenset({"LOYALTY_CARD_LUHN_BAD", "card_luhn_invalid",
                                 "tracking_code_15_16", "IBAN_BAD_CHECKSUM"})
# Read from negatives.py (2026-10-15): `IMEI_BAD_LUHN` (15 random digits with a
# wrong Luhn digit) is checksum-only too WHEN its value has a card's shape (an
# Amex prefix 34/37, ~2% of them); D-51d does not list it, so it is only
# counted (`checksum_only_extra`), never dropped, until the team decides.
CHECKSUM_ONLY_IF_CARD_SHAPED = frozenset({"IMEI_BAD_LUHN"})
MAX_VALUE_REPEATS = 20                                    # D-45b


# --------------------------------------------------------------------------
# lexicon and pools
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Lexicon:
    given: frozenset            # pool given names (match_key), exclusions removed
    given_lowercase: dict       # allowed names also written lower-case: count
    surname_vocab: frozenset
    surname_shaped_common: frozenset
    surname_stoplist: frozenset
    city_bases: frozenset


def _pool(*names: str) -> set[str]:
    out = set()
    for n in names:
        for line in (POOLS / n).open(encoding="utf-8"):
            w = line.split("\t")[0].strip()
            if w and not w.startswith("#"):
                out.add(match_key(w))
    return out


@lru_cache(maxsize=None)
def lexicon(path: Path = LEXICON_PATH) -> Lexicon:
    lex = json.loads(Path(path).read_text(encoding="utf-8"))
    given = _pool("az_first_names_m.txt", "az_first_names_f.txt") - set(lex["given_excluded"])
    return Lexicon(given=frozenset(given), given_lowercase=dict(lex["given_lowercase_uses"]),
                   surname_vocab=frozenset(lex["surname_vocab"]),
                   surname_shaped_common=frozenset(lex["surname_shaped_common"]),
                   surname_stoplist=frozenset(lex["surname_stoplist"]),
                   city_bases=frozenset(_pool("az_cities.txt", "az_districts.txt", "az_settlements.txt")))


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

CAP = "A-ZƏÇĞİÖŞÜ"
LOW = "a-zəçğıöşüi"
NAME_TOKEN = rf"[{CAP}][{LOW}]+"
_SURNAME_END = re.compile(r"(?:ov|ova|yev|yeva|ev|eva|zade|li|lu|beyli)$")   # on match_key
_WORD = re.compile(r"[^\W\d_]+")
_HS = STAMP_SPACE                                                   # one horizontal space

TITLES = {match_key(w) for w in (
    "cənab", "xanım", "bəy", "hörmətli", "həkim", "dr", "prof", "müəllim", "müəllimə", "vəkil",
    "hakim", "direktor", "müdir", "leytenant", "mayor", "kapitan", "polkovnik", "serjant", "mr",
    "mrs", "ms", "sayın", "ağa", "xala", "dayı", "əmi", "baba", "nənə", "ana", "ata", "usta")}
CHAT_ROLES = {match_key(w) for w in (
    "Agent", "Müştəri", "Musteri", "Operator", "Admin", "Sistem", "System", "Dəstək", "Destek",
    "Menecer", "Manager", "Bot", "İstifadəçi", "Istifadeci", "User", "Customer", "Support", "Kuryer",
    "Həkim", "Pasient", "Satıcı", "Alıcı", "Moderator", "Mühəndis", "Texnik", "Dispetçer")}
LOG_LEVEL = r"(?:\[?(?:INFO|ERROR|ERR|WARN|WARNING|DEBUG|TRACE|FATAL|CRITICAL|CRIT|LOG|ALERT|NOTICE|SUCCESS|AUDIT|AUTH|SECURITY|SEC|SYSTEM|SYS)\]?)\b"
# A shop or trade word after a given name makes a business name (negatives._SHOP_WORDS).
SHOP_WORDS = {match_key(w) for w in ("Market", "Ərzaq", "Mebel", "Tekstil", "Servis", "Tikinti", "Aptek",
                                     "Plaza", "Group", "Store", "Kafe", "Avto", "MMC", "ASC", "QSC",
                                     "Holdinq", "Holding", "Ltd", "LLC", "Bank", "Klinika", "Salonu")}


def source_of(doc: dict) -> str:
    """old / targeted / llm, as the build tags them (`_old` from read_old_az)."""
    if doc.get("_old"):
        return "old"
    return "targeted" if doc.get("_source") == "targeted" else "llm"


def _overlaps(spans, s: int, e: int) -> bool:
    return any(a < e and s < b for a, b in spans)


def _line_bounds(text: str, i: int) -> tuple[int, int]:
    ls = text.rfind("\n", 0, i) + 1
    le = text.find("\n", i)
    return ls, (len(text) if le < 0 else le)


def _ent(text: str, s: int, e: int, label: str) -> dict:
    return {"start": s, "end": e, "label": label, "text": text[s:e]}


@dataclass
class Change:
    rule: str
    action: str                 # label / unlabel / trim / drop
    label: str = ""
    start: int = -1
    end: int = -1
    text: str = ""
    note: str = ""

    def as_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in ("", -1)}


@dataclass
class Result:
    doc: dict | None
    rules: list[str]
    changes: list[Change] = field(default_factory=list)
    skipped: list[Change] = field(default_factory=list)     # name candidates left unlabelled


class _Work:
    """The record being cleaned: entities and decoys as mutable lists."""

    def __init__(self, doc: dict):
        self.doc = doc
        self.text = doc["text"]
        self.ents = [dict(e, text=self.text[e["start"]:e["end"]]) for e in doc.get("entities") or []]
        self.decoys = [dict(d) for d in doc.get("_decoys") or []]
        self.changes: list[Change] = []
        self.skipped: list[Change] = []
        self.drop: Change | None = None

    def spans(self, with_decoys: bool = True) -> list[tuple[int, int]]:
        out = [(e["start"], e["end"]) for e in self.ents]
        if with_decoys:
            out += [(d["start"], d["end"]) for d in self.decoys]
        return out

    def covered(self, s: int, e: int) -> bool:
        return _overlaps(self.spans(), s, e)

    def entity_at(self, s: int, e: int) -> dict | None:
        for x in self.ents:
            if x["start"] < e and s < x["end"]:
                return x
        return None

    def unlabel(self, rule: str, ent: dict, kind: str, resembles: str | None = None,
                decoy_span: tuple[int, int] | None = None, note: str = "") -> None:
        self.ents.remove(ent)
        self.changes.append(Change(rule, "unlabel", ent["label"], ent["start"], ent["end"], ent["text"], note))
        ds, de = decoy_span or (ent["start"], ent["end"])
        others = [(x["start"], x["end"]) for x in self.ents]
        if _overlaps(others, ds, de):
            ds, de = ent["start"], ent["end"]
        already = [(d["start"], d["end"]) for d in self.decoys]
        if any(a <= ds and de <= b for a, b in already):
            return
        self.decoys = [d for d in self.decoys if not (ds <= d["start"] and d["end"] <= de)]
        self.decoys.append({"start": ds, "end": de, "kind": kind, "resembles": resembles or ent["label"]})

    def add(self, rule: str, s: int, e: int, label: str, note: str = "") -> None:
        self.ents.append(_ent(self.text, s, e, label))
        self.changes.append(Change(rule, "label", label, s, e, self.text[s:e], note))

    def set_drop(self, rule: str, note: str) -> None:
        if self.drop is None:
            self.drop = Change(rule, "drop", note=note)


# --------------------------------------------------------------------------
# R1, R8: drops
# --------------------------------------------------------------------------

def _most_repeated(ents: list[dict], text: str) -> int:
    from clean_llm_batch import most_repeated          # scripts/ is on sys.path wherever piigen is
    return most_repeated({"text": text, "entities": ents})


def r1_reasons(doc: dict) -> list[str]:
    """drop_before_v3.py's four rules (D-45b, D-47a/b/e), for an old-corpus record."""
    text = doc["text"]
    out = []
    if _most_repeated(doc.get("entities") or [], text) >= MAX_VALUE_REPEATS:
        out.append("D-45b")
    if explained_typos(text):
        out.append("D-47a")
    if is_formal(doc.get("_doc_type")) and self_corrections(text):
        out.append("D-47b")
    if placeholders(text):
        out.append("D-47e")
    return out


# negatives._luhn_invalid_16: first digit 6-9, 16 digits, grouped by 4 or not
_CARD16 = re.compile(r"[6-9]\d{15}|[6-9]\d{3}(?:[ -]\d{4}){3}")
_IBAN = re.compile(r"[A-Z]{2}\d{2}(?: ?[A-Z0-9]){10,30}")


def _old_checksum_kind(value: str) -> str | None:
    """The D-51d kind an old-corpus `_spec` look-alike string has, by shape."""
    v = value.strip()
    if _CARD16.fullmatch(v) and not CK.luhn_valid(v):
        return "LOYALTY_CARD_LUHN_BAD"
    flat = v.replace(" ", "")
    if _IBAN.fullmatch(v) and CK.IBAN_LENGTHS.get(flat[:2]) == len(flat) and not CK.iban_valid(flat):
        return "IBAN_BAD_CHECKSUM"
    return None


# D-51j: an old-corpus 16-digit look-alike drops its record only with a card
# word within 4 words; transaction, product and log IDs keep their own words
# (`əməliyyat nömrəsi`, `transaction id`) and stay. `kart…` but not `kartof`,
# `karton`, `kartric`, `kartel`, `kartoqrafiya`, `kartoteka`; not `viza`.
_CARD_WORD = re.compile(r"(?i)(?<![^\W\d_])(?:kart(?!of|on|ric|el|oq|otek)|card|visa|master|maestro|amex|"
                        r"american express|unionpay)")
CARD_WORD_WINDOW = 4


def _card_word_near(text: str, s: int, e: int, n: int = CARD_WORD_WINDOW) -> bool:
    before = re.findall(r"\S+", text[max(0, s - 100):s])[-n:]
    after = re.findall(r"\S+", text[e:e + 100])[:n]
    return any(_CARD_WORD.search(t) for t in before + after)


def r8_kinds(doc: dict) -> tuple[list[str], list[str]]:
    """(checksum-only kinds in the record, IMEI-type kinds that are card-shaped)."""
    text = doc["text"]
    hits, extra = [], []
    for d in doc.get("_decoys") or []:
        kind = d.get("kind")
        if kind in CHECKSUM_ONLY_KINDS:
            hits.append(kind)
        elif kind in CHECKSUM_ONLY_IF_CARD_SHAPED and CK.card_brand_ok(text[d["start"]:d["end"]]):
            extra.append(kind)
    if doc.get("_old"):
        spec = doc.get("_spec") or {}
        labelled = [(e["start"], e["end"]) for e in doc.get("entities") or []]
        for s in [*(spec.get("adversarials") or []), *(spec.get("hard_negatives") or [])]:
            if not isinstance(s, str) or not s.strip():
                continue
            kind = _old_checksum_kind(s)
            if not kind:
                continue
            i = text.find(s.strip())
            while i >= 0:
                j = i + len(s.strip())
                if not _overlaps(labelled, i, j) and (kind == "IBAN_BAD_CHECKSUM" or _card_word_near(text, i, j)):
                    hits.append(kind)
                    break
                i = text.find(s.strip(), i + 1)
    return hits, extra


# --------------------------------------------------------------------------
# R2: timestamps and line stamps
# --------------------------------------------------------------------------

_DIG = "[0-9OoIlZSB]"
_NOISY_DATE = (rf"(?:{_DIG}{{4}}[-/.–—]{_DIG}{{1,2}}[-/.–—]{_DIG}{{1,2}}"
               rf"|{_DIG}{{1,2}}[./\-–—]{_DIG}{{1,2}}[./\-–—]{_DIG}{{2,4}})")
_DATE_THEN_GAP = re.compile(rf"(?<![\w./-]){_NOISY_DATE}(?:{_HS}+|T|,{_HS}{{1,2}})$")
_TAIL = r"(?::[0-5O]\d)?(?:[.,]\d{1,6})?(?:\s?[AaPp][Mm])?"
_GAP_THEN_DATE = re.compile(rf"{_TAIL}{_HS}+{_NOISY_DATE}(?![\w/])")
_SECONDS = re.compile(r":[0-5O]\d(?:[.,]\d{1,6})?")
_CLOCK_AFTER_DATE = re.compile(rf"(?:{_HS}+|T|,{_HS}{{1,2}})(?P<clock>[0-9OoIlZSGB]{{1,4}}:[0-9OoIlZSGB]{{1,4}}"
                               rf"(?::[0-9OoIlZSGB]{{1,3}})?(?:[.,]\d{{1,6}})?(?:\s?[AaPp][Mm])?)")
_SPEAKER_AFTER = re.compile(rf"[ \t]*(?:[-–—|][ \t]*)?(?P<who>[^\W\d_]+(?:[ \t]+[^\W\d_]+){{0,2}})[ \t]*:(?![/\d])")
_COLUMN_ROLE = re.compile(r"[ \t]*\|?[ \t]*(?P<who>[^\W\d_]+(?:[ \t][^\W\d_]+)?)[ \t]*(?:\||[ \t]{2,})")


def _is_speaker(who: str, lex: Lexicon) -> bool:
    words = who.split()
    k = match_key(words[0])
    if k in CHAT_ROLES:
        return True
    return words[0][:1].isupper() and k in lex.given


def _stamp_of_time(text: str, s: int, e: int, lex: Lexicon) -> tuple[int, int, str] | None:
    """If the TIME span (s, e) is part of a stamp: (stamp start, stamp end, kind)."""
    m = _DATE_THEN_GAP.search(text, max(0, s - 40), s)
    if m and sum(ch.isdigit() for ch in m.group(0)) >= 4:
        sec = _SECONDS.match(text, e)
        return m.start(), sec.end() if sec else e, "date_time"
    after = _GAP_THEN_DATE.match(text, e)
    if after:
        return s, e + len(after.group(0)), "time_date"
    ls, le = _line_bounds(text, s)
    pre, post = text[ls:s], text[e:le]
    sec = _SECONDS.match(post)
    tail = re.match(_TAIL, post).end()
    rest = post[tail:]
    stamp_end = e + tail
    if re.fullmatch(r"[ \t>*\-]*[\[(]", pre) and re.match(r"[\])]", rest):
        return s, stamp_end, "line_bracket"
    if re.fullmatch(rf"[ \t>*\-]*{NAME_TOKEN}(?:[ \t]+{NAME_TOKEN})?[ \t]*[\[(]", pre) \
            and re.match(r"[\])][ \t]*:", rest):
        return s, stamp_end, "speaker_then_stamp"
    if re.fullmatch(rf"[ \t>*\-]*{NAME_TOKEN}(?:[ \t]+{NAME_TOKEN})?[ \t]*:[ \t]*[\[(]", pre) \
            and re.match(r"[\])]", rest):
        return s, stamp_end, "speaker_colon_stamp"
    if re.fullmatch(r"[ \t>*\-]*", pre):
        sp = _SPEAKER_AFTER.match(rest)
        if sp and _is_speaker(sp.group("who"), lex):
            return s, stamp_end, "line_speaker"
        if re.match(rf"[ \t]*(?:[-–—|][ \t]*)?{LOG_LEVEL}", rest):
            return s, stamp_end, "line_log"
        col = _COLUMN_ROLE.match(rest)
        if col and re.match(r"[ \t]*(?:\||[ \t]{2,})", rest) and _is_speaker(col.group("who"), lex):
            return s, stamp_end, "line_transcript_column"
        # `- 23:06:15 - Bağlantı kəsildi`: a log line's own HH:MM:SS
        if sec and re.match(r"(?:[ \t]+[-–—|]|[ \t]*\]|[ \t]*$)", rest):
            return s, stamp_end, "line_hhmmss"
    return None


def _date_stamp_end(text: str, s: int, e: int) -> int:
    m = _CLOCK_AFTER_DATE.match(text, e)
    return m.end() if m else e


def rule_r2(w: _Work, lex: Lexicon) -> None:
    text = w.text
    for ent in sorted([x for x in w.ents if x["label"] in ("TIME", "DATE")], key=lambda x: x["start"]):
        if ent not in w.ents:
            continue
        s, e = ent["start"], ent["end"]
        if ent["label"] == "DATE":
            if is_timestamp(text, s, e):
                end = _date_stamp_end(text, s, e)
                start = s
                if end == e:          # the time came first: `10:15 12.05.2021`
                    m = re.search(rf"(?<![\w:.])\d{{1,2}}:\d{{2}}{_TAIL}{_HS}+$", text[max(0, s - 64):s])
                    start = s - len(m.group(0)) if m else s
                w.unlabel("R2", ent, "TIMESTAMP", "DATE", (start, end), "date in a date+time stamp")
            continue
        stamp = _stamp_of_time(text, s, e, lex)
        if stamp:
            st, en, kind = stamp
            w.unlabel("R2", ent, "TIMESTAMP", "TIME" if kind.startswith(("line", "speaker")) else "DATE",
                      (st, en), kind)


# --------------------------------------------------------------------------
# R3: `-ci il` out of DATE
# --------------------------------------------------------------------------

_CI_IL = re.compile(r"[-–—]\s?c[iu](?:\s+(?:il|li))?$")      # on match_key


def rule_r3(w: _Work) -> None:
    for ent in list(w.ents):
        if ent["label"] != "DATE":
            continue
        m = _CI_IL.search(match_key(ent["text"]))
        if not m:
            continue
        head = ent["text"][:m.start()]
        if not head or not head[-1].isdigit():
            continue
        new_end = ent["start"] + len(head)
        w.changes.append(Change("R3", "trim", "DATE", ent["start"], ent["end"], ent["text"],
                                f"-> {head!r}" + ("; year only" if re.fullmatch(r"\d{4}", head) else "")))
        ent["end"] = new_end
        ent["text"] = w.text[ent["start"]:new_end]


# --------------------------------------------------------------------------
# R6: a city heading an institution or project name (D-2)
# --------------------------------------------------------------------------

_PROJECT_HEADS = ("layihesi", "proqrami", "festivali", "marafonu", "forumu", "sergisi", "konfransi",
                  "turniri", "fondu", "klubu", "yarmarkasi", "musabiqesi", "komandasi", "olimpiadasi",
                  "cempionati", "kubogu")
_INSTITUTION_HEADS = ("mehkemesi", "hakimiyyeti", "universiteti", "institutu", "kolleci", "liseyi",
                      "gimnaziyasi", "mektebi", "xestexanasi", "klinikasi", "poliklinikasi", "prokurorlugu",
                      "belediyyesi", "nazirliyi", "komitesi", "agentliyi", "departamenti", "zavodu", "fabriki",
                      "akademiyasi", "teatri", "filarmoniyasi", "muzeyi", "kitabxanasi", "stadionu", "limani",
                      "metropoliteni", "laboratoriyasi", "laboratoriya", "konservatoriyasi", "seminariyasi",
                      "texnikumu", "baglcasi", "bagcasi", "inspeksiyasi", "xidmeti", "xidmetleri")
# heads that name a branch of something bigger: only with a filler before them
# (`Rayon Polis Bölməsi`, `şəhər Təhsil İdarəsi`), never bare (`Sumqayıt şöbəsi`)
# `mərkəzi` is never a head: `Naxçıvan şəhər mərkəzi` is the city centre, a place.
_WEAK_HEADS = ("idaresi", "bolmesi", "sobesi", "mudirliyi")
_FILLERS = {match_key(w) for w in (
    "rayon", "şəhər", "dövlət", "kommunal", "regional", "region", "bölgə", "mərkəzi", "orta", "ibtidai",
    "təhsil", "polis", "icra", "baş", "texniki", "tibb", "tibbi", "nəqliyyat", "su", "elektrik", "qaz",
    "inzibati", "beynəlxalq", "milli", "respublika", "maliyyə", "yerli", "ali", "hava", "ümumi",
    "ixtisaslaşdırılmış", "apellyasiya", "iqtisad", "iqtisadi", "pedaqoji", "musiqi", "incəsənət",
    "sosial", "dram", "opera", "balet", "tarix", "diyarşünaslıq", "mərkəzləşdirilmiş", "kitabxana",
    "uşaq", "gənclər", "idman", "olimpiya", "kənd", "təsərrüfatı", "sığorta", "vergi", "gömrük",
    "statistika", "əmək", "müdafiə", "fövqəladə", "hallar", "daxili", "işlər", "ədliyyə", "ekologiya",
    "səhiyyə", "mədəniyyət", "turizm", "nömrəli", "saylı", "tam", "klinik", "doğum", "psixi",
    "sağlamlıq", "texnologiya", "texnologiyalar", "mühəndislik", "neft", "kimya", "tibbi")}
_TOKEN = re.compile(r"[^\W_][\w'’]*")


def _head_kind(key: str) -> str | None:
    for heads, kind in ((_PROJECT_HEADS, "project"), (_INSTITUTION_HEADS, "institution"),
                        (_WEAK_HEADS, "weak")):
        for h in heads:
            if key.startswith(h) and len(key) - len(h) <= 5:
                return kind
    return None


def _institution_after(text: str, e: int, max_fillers: int = 5) -> tuple[str, int] | None:
    """If an institution or project name continues after `e` on the same line:
    (kind, end of the head word)."""
    _, le = _line_bounds(text, e)
    pos, fillers = e, 0
    while fillers <= max_fillers:
        m = re.match(r"[ \t]+", text[pos:le])
        if not m:
            return None
        t = _TOKEN.match(text, pos + m.end(), le)
        if not t:
            return None
        k = match_key(t.group(0))
        kind = _head_kind(k)
        if kind == "weak" and fillers == 0:
            return None
        if kind:
            return ("project" if kind == "project" else "institution"), t.end()
        if k not in _FILLERS and not t.group(0).isdigit():
            return None
        fillers += 1
        pos = t.end()
    return None


_CASE_END = ("da", "de", "dan", "den", "nin", "nun", "in", "un", "ya", "ye", "ni", "nu", "a", "e",
             "ndan", "nden", "nda", "nde", "na", "ne")


def _inflected(key: str, bases: frozenset) -> bool:
    if key in bases:
        return False
    return any(key.endswith(suf) and key[:-len(suf)] in bases for suf in _CASE_END)


def rule_r6(w: _Work, lex: Lexicon) -> None:
    for ent in sorted([x for x in w.ents if x["label"] == "CITY"], key=lambda x: x["start"]):
        if _inflected(match_key(ent["text"]), lex.city_bases):
            continue
        hit = _institution_after(w.text, ent["end"])
        if not hit:
            continue
        kind, head_end = hit
        others = [(x["start"], x["end"]) for x in w.ents if x is not ent]
        if _overlaps(others, ent["end"], head_end):
            continue                # a labelled value inside the name: not this construction
        w.unlabel("R6", ent, "policy_city_as_project" if kind == "project" else "policy_city_in_institution",
                  "CITY", note=w.text[ent["start"]:head_end])


# --------------------------------------------------------------------------
# R7: false SURNAME labels
# --------------------------------------------------------------------------

_FIELD_BEFORE = re.compile(r"(?i)(?:soyad\w*|ad\w*[ \t,/]+soyad\w*|surname|last[ _]?name|familiya|"
                           r"müştəri|musteri|istifadəçi|istifadeci|pasient|xəstə|xeste|şəxs|sexs|iddiaçı|"
                           r"cavabdeh|vətəndaş|əməkdaş|işçi|namizəd|abunəçi|tələbə|müraciət edən)"
                           r"[\"']?[ \t]*[:=|]?[ \t]*[\"']?$")
_NAME_AFTER = re.compile(r"[ \t]+(?:adlı|adli|soyadlı|soyadli|bəy|bey|xanım|xanim|müəllim)\b", re.I)
_PATRONYMIC = re.compile(r"\b(?:oğlu|qızı|oglu|qizi)\b", re.I)
_INITIAL_BEFORE = re.compile(rf"(?<![\w.])[{CAP}]\.[ \t]?$")
# The head of an institution named after a person, in its possessive form
# (`Heydər Əliyev Fondu`, `Nərimanov Liseyi`), with a case ending of at most 5
# letters.
_INSTITUTION_AFTER_NAME = re.compile(
    r" (?:Beynəlxalq Hava Limanı|Hava Limanı|Fondu|Mərkəzi|Universiteti|Liseyi|Muzeyi|Parkı|"
    r"Kitabxanası|Akademiyası|Stadionu|Sarayı|Mükafatı|Ordeni|Metrosu|Stansiyası|Məktəbi|İnstitutu|"
    r"Teatrı|Xəstəxanası|Klinikası)(?:[^\W\d_]{0,5})(?![^\W\d_])")
_ADINA = re.compile(r" ad[ıi]na(?= )")


def _named_after(text: str, e: int) -> int | None:
    """`… adına Bakı Dövlət Universiteti`, `… adına 6 nömrəli tam orta məktəb`:
    the end of the institution's head word, else None. `X adına` alone means
    "in X's name" (`Nəmət Azayev adına yazılıb`, `Həmidova adına 2023-cü ildə
    açılmış borc`: a real person), so a head word must follow within 6 tokens
    of capitalised words, numbers and filler words."""
    m = _ADINA.match(text, e)
    if not m:
        return None
    _, le = _line_bounds(text, e)
    pos = m.end()
    for _ in range(7):
        sp = re.match(r"[ \t]+", text[pos:le])
        if not sp:
            return None
        t = _TOKEN.match(text, pos + sp.end(), le)
        if not t:
            return None
        k = match_key(t.group(0))
        if _head_kind(k) or k.startswith(("mekteb", "kitabxana", "park", "liseyi", "muzey", "teatr", "xestexana",
                                          "universitet", "institut", "akademiya", "stadion", "saray", "limani")):
            return t.end()
        if not (t.group(0)[0].isupper() or t.group(0).isdigit() or k in _FILLERS):
            return None
        pos = t.end()
    return None


def _name_context(w: _Work, ent: dict) -> bool:
    text, s, e = w.text, ent["start"], ent["end"]
    ls, le = _line_bounds(text, s)
    for x in w.ents:
        if x is ent or x["label"] not in ("GIVENNAME", "SURNAME"):
            continue
        if 0 <= s - x["end"] <= 2 and re.fullmatch(r"[ \t,]*", text[x["end"]:s]):
            return True
        if 0 <= x["start"] - e <= 2 and re.fullmatch(r"[ \t,]*", text[e:x["start"]]):
            return True
        # `Odabaşı və Uğurlu`: another person on either side of `və`
        if re.fullmatch(r"[ \t]+(?:və|ve)[ \t]+", text[x["end"]:s] if x["end"] <= s else text[e:x["start"]]):
            return True
    pre = text[ls:s]
    if _FIELD_BEFORE.search(pre) or _INITIAL_BEFORE.search(pre):
        return True
    words = _WORD.findall(pre)
    if words and match_key(words[-1]) in TITLES and re.search(r"[^\W\d_][ \t]+$", pre):
        return True
    if _NAME_AFTER.match(text, e) or _PATRONYMIC.search(text[ls:le]):
        return True
    return False


def rule_r7(w: _Work, lex: Lexicon, src: str) -> None:
    text = w.text
    for ent in sorted([x for x in w.ents if x["label"] == "SURNAME"], key=lambda x: x["start"]):
        if ent not in w.ents:
            continue
        # R7b: a surname heading an institution (every source; D-2)
        m = _INSTITUTION_AFTER_NAME.match(text, ent["end"])
        head_end = ent["end"] + len(m.group(0)) if m else _named_after(text, ent["end"])
        if head_end and not re.search(r"(?:n[ıiuü]n|[ıiuü]n)$", match_key(ent["text"])):
            prev = [x for x in w.ents if x["label"] == "GIVENNAME" and 0 <= ent["start"] - x["end"] <= 1
                    and re.fullmatch(r"[ \t]?", text[x["end"]:ent["start"]])]
            start = prev[0]["start"] if prev else ent["start"]
            note = text[start:head_end]
            for g in prev:
                w.unlabel("R7", g, "policy_name_in_institution", "GIVENNAME", note=note)
            w.unlabel("R7", ent, "policy_name_in_institution", "SURNAME", note=note)
            continue
        # R7a: a common word the old corpus's surname sweep labelled (old only)
        if src == "old" and match_key(ent["text"]) in lex.surname_stoplist and not _name_context(w, ent):
            w.unlabel("R7", ent, "common_word_surname", "SURNAME", note="stoplist, no name context")


# --------------------------------------------------------------------------
# names: candidates, placement on every occurrence, ambiguity
# --------------------------------------------------------------------------

def is_given(word: str, lex: Lexicon) -> bool:
    return bool(word) and word[0].isupper() and not word.isupper() and match_key(word) in lex.given


def is_surname(word: str, lex: Lexicon, *, shape_ok: bool = True) -> bool:
    if not word or not word[0].isupper() or (word.isupper() and len(word) > 1):
        return False
    k = match_key(word)
    if k in lex.surname_stoplist or k in lex.given:
        return False
    if k in lex.surname_vocab:
        return True
    return shape_ok and len(k) >= 5 and bool(_SURNAME_END.search(k)) and k not in lex.surname_shaped_common


_SENT_START = re.compile(r"(?:^|[.!?…:;]|\n)[ \t\"'“«(*\-–—>]*$")


# A name written lower-case this often is also an ordinary word (`Ümid`,
# `Aydın`, `Mehriban`): a sentence-initial use of it may be the word.
HOMOGRAPH_MIN_LOWER = 20
# What follows a name: punctuation, a CSV or table cell end (`;Sevinc;`), the
# line end, a capitalised word, or a title with its case ending (`Bayram
# bəylə`, `Leyla xanıma`; not `bəyanat`).
_NAME_FOLLOWS = re.compile(rf"(?:[ \t]*[,:;|!?)]|[ \t]*$|[ \t]*\n|[ \t]+(?:xanım|xanim|bəy(?!an)|bey(?!an)|"
                           rf"müəllim|həkim)\w{{0,4}}(?!\w)|[ \t]+[{CAP}])")
_STREET_AFTER = re.compile(r"(?:[ \t]+[^\W\d_]+)?[ \t]+(?:küç|kuc|prospekt|pr\.|döngə|donge|bulvar|meydan|"
                           r"park[ıi]|qəsəbə|massiv)", re.I)


def _ambiguous_use(w: _Work, s: int, e: int, lex: Lexicon) -> str:
    """Why another occurrence (s, e) of a name being labelled may not be the
    name, or ''."""
    text = w.text
    nxt = re.match(r"[ \t]+([^\W\d_]+)", text[e:e + 40])
    if nxt and match_key(nxt.group(1)) in SHOP_WORDS:
        return "shop or company name"
    if _institution_after(text, e):
        return "institution name"
    if _STREET_AFTER.match(text, e):
        return "street or place name"
    k = match_key(text[s:e])
    homograph = any(lex.given_lowercase.get(b, 0) >= HOMOGRAPH_MIN_LOWER
                    for b in {k, k[:-1], k[:-2], k[:-3], k[:-4]} if b)
    if homograph and _SENT_START.search(text, max(0, s - 8), s) and not _NAME_FOLLOWS.match(text, e):
        return "sentence-initial homograph"
    return ""


def place_name(w: _Work, rule: str, label: str, value: str, target: tuple[int, int] | None,
               lex: Lexicon, note: str = "") -> str:
    """Label `value` as `label` on every occurrence the resolver would place
    (the resolver's every-occurrence rule, D-9 suffixes included), the target
    span among them. '' on success, else why nothing was labelled:
    `unplaceable` when the resolver itself would not label the target, or why
    another occurrence may not be this name (the caller drops the record)."""
    placed, _ = resolve_claims(w.text, [{"label": label, "text": value}], blocked=w.spans())
    if target is not None and not any(p["start"] == target[0] for p in placed):
        w.skipped.append(Change(rule, "skip", label, target[0], target[1], value, "unplaceable: " + note))
        return "unplaceable"
    if label in ("GIVENNAME", "SURNAME"):
        for p in placed:
            if target is None or p["start"] != target[0]:
                why = _ambiguous_use(w, p["start"], p["end"], lex)
                if why:
                    return why
    for p in placed:
        first = target is not None and p["start"] == target[0]
        w.add(rule, p["start"], p["end"], label, note if first else "another occurrence")
    return ""


# --------------------------------------------------------------------------
# R5: half-labelled names, patronymics
# --------------------------------------------------------------------------

_LIST_HEAD = re.compile(r"[ \t]*(?:[-*•>]|\d{1,3}[.)]|\|)?[ \t]*$")


def rule_r5(w: _Work, lex: Lexicon) -> None:
    text = w.text
    for ent in sorted([x for x in w.ents if x["label"] == "SURNAME"], key=lambda x: x["start"]):
        s, e = ent["start"], ent["end"]
        ls, le = _line_bounds(text, s)
        m = re.search(r"([^\W\d_]+)[ \t]+$", text[max(ls, s - 40):s])
        if m:
            word = m.group(1)
            ws = s - len(m.group(0))
            if (is_given(word, lex) and not w.covered(ws, ws + len(word))
                    and match_key(word) not in TITLES
                    and not (ws > 0 and text[ws - 1] in "@.-_/")):
                why = place_name(w, "R5", "GIVENNAME", word, (ws, ws + len(word)), lex,
                                 f"before SURNAME {ent['text']}")
                if why and why != "unplaceable":
                    w.set_drop("R5", f"{word}: {why}")
        # surname-first list line: `2. Məmmədov Rəşad Əli oğlu`
        if _LIST_HEAD.fullmatch(text[ls:s]):
            m2 = re.match(rf"[ \t]+({NAME_TOKEN})(?=[ \t,]|$)", text[e:le])
            if m2:
                word = m2.group(1)
                ws = e + m2.start(1)
                if is_given(word, lex) and not w.covered(ws, ws + len(word)):
                    why = place_name(w, "R5", "GIVENNAME", word, (ws, ws + len(word)), lex,
                                     f"after SURNAME {ent['text']} (list line)")
                    if why and why != "unplaceable":
                        w.set_drop("R5", f"{word}: {why}")


def rule_patronymic(w: _Work, lex: Lexicon, rule: str) -> None:
    """D-39b: in `Given Father oğlu/qızı` the father's name is GIVENNAME."""
    text = w.text
    for ent in sorted([x for x in w.ents if x["label"] == "GIVENNAME"], key=lambda x: x["start"]):
        m = re.match(rf"[ \t]+({NAME_TOKEN})[ \t]+(?:oğlu|qızı|oglu|qizi|OĞLU|QIZI)\b", text[ent["end"]:ent["end"] + 60])
        if not m:
            continue
        word = m.group(1)
        ws = ent["end"] + m.start(1)
        k = match_key(word)
        if w.covered(ws, ws + len(word)) or k in TITLES or (k not in lex.given and _SURNAME_END.search(k)):
            continue
        why = place_name(w, rule, "GIVENNAME", word, (ws, ws + len(word)), lex, "father's name (D-39b)")
        if why and why != "unplaceable":
            w.set_drop(rule, f"{word}: {why}")


# --------------------------------------------------------------------------
# R4: persona names
# --------------------------------------------------------------------------

_STAMP = r"[\[(]?\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?[\])]?"
_SPEAKER_LINE = re.compile(
    rf"(?m)^[ \t>*\-]*(?:\*\*)?(?:(?P<stamp>{_STAMP})[ \t]*(?:[-–—|][ \t]*)?)?"
    rf"(?P<n1>{NAME_TOKEN})(?:[ \t]+(?P<n2>{NAME_TOKEN}))?[ \t]*"
    rf"(?P<stamp2>[\[(]\d{{1,2}}:\d{{2}}(?::\d{{2}})?(?:\s?[AaPp][Mm])?[\])][ \t]*)?:(?:\*\*)?(?![/\d])"
    rf"(?P<msg>[^\n]*)")
_COPULA = ("dir", "dur", "yam", "yem", "am", "em")
_INTRO = re.compile(
    rf"(?:\b(?:[Mm][əe]n(?:im)?(?:[ \t]+ad[ıi]m)?(?:[ \t]+d[əe])?|(?<![\w])[Aa]d[ıi]m)[ \t]+)"
    rf"(?P<n1>{NAME_TOKEN})(?:[ \t]+(?P<n2>{NAME_TOKEN}))?"
    rf"(?=[ \t]*(?:[,.!;]|$|\n)|[ \t]+(?:və|ve|burada|buradayam)\b)")
_CLOSINGS = (r"Hörmətlə|Hormetle|Ehtiramla|Sayğılarla|Sayğı ilə|Saygilarla|Best regards|Kind regards|Regards|"
             r"Təşəkkürlə|Minnətdarlıqla|Səmimiyyətlə|Dərin hörmətlə|Hörmətlə və təşəkkürlə")
_SIGNATURE = re.compile(rf"(?:{_CLOSINGS})[ \t]*[,.!]?[ \t]*\n(?:[ \t]*\n)?(?:[ \t]*[-–—_]+[ \t]*\n)?"
                        rf"[ \t>*]*(?P<line>[^\n]{{2,70}})")
_HEADER = re.compile(r"(?mi)^[ \t>*]*(?:\*\*)?(?:From|Kimdən|Kimden|Göndərən|Gonderen|Göndərici)(?:\*\*)?[ \t]*:"
                     r"(?:\*\*)?[ \t]*(?P<line>[^\n]{2,70})")
_INITIAL_SURNAME = re.compile(rf"(?<![\w.@])[{CAP}]\.[ \t]?(?P<sur>[{CAP}][{LOW}]{{2,}})\b")
_NOT_AFTER_INITIAL = re.compile(r"[ \t]*(?:küç|küçə|kuc|prospekt|pr\.|döngə|adına|adina|metro|parkı|liseyi|"
                                r"məktəbi|universitet|institut|bağı|bulvar|meydan|qəsəbə|rayon|şəhər)", re.I)
CONVERSATIONAL_TYPES = frozenset({"live_chat", "whatsapp_thread", "social_media", "forum_post",
                                  "call_center_transcript", "voicemail_transcript", "chat", "email_thread"})


def _name_tokens(line: str, base: int, lex: Lexicon) -> list[tuple[int, int, str]] | None:
    """A signature or header line that is nothing but a person's name (1-3
    tokens: given names, surnames, initials), optionally followed by a role
    after a comma, a dash or a bracket, or an e-mail. [(start, end, label)]."""
    m = re.match(r"[ \t]*((?:[^\W\d_]+\.?(?:[ \t]+|$))+?)[ \t]*(?:[,(<|]|[-–—][ \t]|\[|$)", line)
    if not m:
        return None
    toks = [(base + t.start(), base + t.end(), t.group(0)) for t in re.finditer(r"[^\W\d_]+\.?", m.group(1))]
    if not 1 <= len(toks) <= 3:
        return None
    rest = line[m.end(1):].strip()
    if rest and not re.match(r"[,(<|\-–—\[]", rest):
        return None
    out = []
    for s, e, tok in toks:
        if re.fullmatch(rf"[{CAP}]\.", tok):
            continue                                     # an initial: stays unlabelled
        if tok.endswith("."):
            return None
        if is_given(tok, lex):
            out.append((s, e, "GIVENNAME"))
        elif is_surname(tok, lex):
            out.append((s, e, "SURNAME"))
        else:
            return None
    return out or None


def _speaker_doc(text: str, doc_type: str | None, lex: Lexicon) -> bool:
    if doc_type in CONVERSATIONAL_TYPES:
        return True
    n = 0
    for m in _SPEAKER_LINE.finditer(text):
        k = match_key(m.group("n1"))
        if m.group("stamp") or m.group("stamp2") or k in CHAT_ROLES or k in lex.given:
            n += 1
            if n >= 3:
                return True
    return False


def rule_r4(w: _Work, lex: Lexicon) -> None:
    text = w.text
    cands: list[tuple[int, int, str, str]] = []          # start, end, label, note
    chat = None
    for m in _SPEAKER_LINE.finditer(text):
        n1, n2 = m.group("n1"), m.group("n2")
        stamped = bool(m.group("stamp") or m.group("stamp2"))
        if not stamped:
            if chat is None:
                chat = _speaker_doc(text, w.doc.get("_doc_type"), lex)
            msg = m.group("msg").strip(" \t*")
            # a message, not a field value: it starts with a letter, a quote or a bracket
            if not chat or not msg or not re.match(r"[^\W\d_]|[\"'“«\[(]", msg):
                continue
        toks = [(m.start("n1"), m.end("n1"), n1)] + ([(m.start("n2"), m.end("n2"), n2)] if n2 else [])
        k1 = match_key(n1)
        if k1 in CHAT_ROLES:
            continue
        if n2:
            if not (is_given(n1, lex) and is_surname(n2, lex)):
                continue
            cands += [(toks[0][0], toks[0][1], "GIVENNAME", "speaker tag"),
                      (toks[1][0], toks[1][1], "SURNAME", "speaker tag")]
        elif is_given(n1, lex):
            cands.append((toks[0][0], toks[0][1], "GIVENNAME", "speaker tag"))
        elif is_surname(n1, lex, shape_ok=False):
            cands.append((toks[0][0], toks[0][1], "SURNAME", "speaker tag"))
    for m in _INTRO.finditer(text):
        n1, n2 = m.group("n1"), m.group("n2")
        k1 = match_key(n1)
        given = is_given(n1, lex) or any(k1.endswith(c) and k1[:-len(c)] in lex.given and n1[0].isupper()
                                         for c in _COPULA)
        if not given:
            continue
        if n2 and not is_surname(n2, lex):
            n2 = None
        cands.append((m.start("n1"), m.end("n1"), "GIVENNAME", "self-introduction"))
        if n2:
            cands.append((m.start("n2"), m.end("n2"), "SURNAME", "self-introduction"))
    for rx, note in ((_SIGNATURE, "signature"), (_HEADER, "header")):
        for m in rx.finditer(text):
            toks = _name_tokens(m.group("line"), m.start("line"), lex)
            for s, e, lab in toks or []:
                cands.append((s, e, lab, note))
    for m in _INITIAL_SURNAME.finditer(text):
        sur = m.group("sur")
        k = match_key(sur)
        if _NOT_AFTER_INITIAL.match(text, m.end("sur")):
            continue
        if k in lex.surname_vocab or (is_surname(sur, lex) and _SURNAME_END.search(k)):
            cands.append((m.start("sur"), m.end("sur"), "SURNAME", "initial + surname"))
    seen = set()
    for s, e, label, note in sorted(cands):
        if (s, e) in seen or w.covered(s, e):
            continue
        seen.add((s, e))
        value = text[s:e]
        k = match_key(value)
        stem = None
        if label == "GIVENNAME" and k not in lex.given:
            # `Mən Ayseldir` / `Mən Cemiləm`: one word, labelled whole (D-9);
            # the stem is labelled wherever else it occurs
            stem = next((value[:-len(c)] for c in _COPULA if k.endswith(c) and k[:-len(c)] in lex.given), None)
        why = place_name(w, "R4", label, value, (s, e), lex, note)
        if not why and stem:
            why = place_name(w, "R4", label, stem, None, lex, note)
        # unplaceable too (`S.Mətinov`: the resolver does not place a surname
        # glued to an initial): a person's name left unlabelled drops (D-15c)
        if why:
            w.set_drop("R4", f"{value} ({note}): {why}")


# --------------------------------------------------------------------------
# R9: unlabelled ages
# --------------------------------------------------------------------------

_AGE_FIELD = re.compile(r"(?i)(?<![\w])(?:yaş|yaşı|yas|yasi|age)[ \t]*[:：=][ \t]*[\"']?(\d{1,3})(?![\d.,:/])")
_AGE_SUFFIX = re.compile(r"(?i)(?<![\w.,:/])(\d{1,3})[ \t]*-?(?:yaşında\w*|yaşlı\w*|yaşı\b|yaşım\w*|yaşa\b|yaş\b|"
                         r"yasinda\w*|yasli\w*|yasi\b|yas\b)")
_RANGE_BEFORE = re.compile(r"(?:\d[ \t]*[-–—][ \t]*|[<>≤≥~][ \t]*|[-–—+])$")
_RANGE_AFTER = re.compile(r"[ \t]*(?:[-–—][ \t]*\d|-?(?:yaş|yas)\w*[ \t]+(?:arası|arasi|aralığı|qədər|üstü|yuxarı|aşağı|altı))", re.I)
_FIGURATIVE = re.compile(r"(?i)\b(?:sanki|elə bil|ele bil|kimi|kimidir|hiss|təxminən deyil|bənzəyir)\b")


def rule_r9(w: _Work, lex: Lexicon) -> None:
    text = w.text
    found: list[tuple[int, int, str]] = []
    for m in _AGE_FIELD.finditer(text):
        found.append((m.start(1), m.end(1), "field"))
    for m in _AGE_SUFFIX.finditer(text):
        found.append((m.start(1), m.end(1), "suffix"))
    for s, e, how in sorted(set(found)):
        if w.covered(s, e):
            continue
        n = int(text[s:e])
        if not 0 <= n <= 120:
            continue
        if how == "suffix":
            if _RANGE_BEFORE.search(text[max(0, s - 6):s]) or _RANGE_AFTER.match(text, e):
                continue                                    # an age group, not a person's age
            ls, le = _line_bounds(text, s)
            sent = re.split(r"(?<=[.!?])\s", text[ls:le])
            pos, ctx = ls, ""
            for part in sent:
                if pos <= s < pos + len(part) + 1:
                    ctx = part
                    break
                pos += len(part) + 1
            if _FIGURATIVE.search(ctx):
                w.set_drop("R9", f"figurative or uncertain age {text[s:e]!r}")
                continue
        why = place_name(w, "R9", "AGE", text[s:e], (s, e), lex, f"unlabelled age ({how})")
        if why:
            w.set_drop("R9", f"age {text[s:e]!r} cannot be labelled ({why})")


# --------------------------------------------------------------------------
# R10: clock times after `saat` / `vaxtı`
# --------------------------------------------------------------------------

_CLOCK = r"(?:[01]?\d|2[0-3]):[0-5]\d"
_R10_TIME = rf"(?<![\d:.]){_CLOCK}(?::[0-5]\d)?(?:[ \t]?[AaPp][Mm](?![^\W\d_]))?"
_CLOCK_END = r"(?![\d:]|[.,]\d|[^\W\d_])"              # no decimals or glued letters after the clock
# Decided 2026-10-15: `zaman` and the plural (`İş saatları:`) too, like `İş vaxtı:`
TIME_WORDS = ("saat", "saatı", "saati", "saatında", "saatinda", "vaxt", "vaxtı", "vaxti", "vaxtında", "vaxtinda",
              "zaman", "zamanı", "zamani", "saatlar", "saatları", "saatlari", "saatlarımız", "saatlarimiz")
# the other end of a range: `10:00 – 14:30`, `09:00-dan 18:00-a qədər`
_RANGE_SEP = r"(?:[ \t]*[-–—][ \t]*|(?:-|'|’)?(?:dan|dən|den)[ \t]+)"
_TIME_AFTER_WORD = re.compile(
    rf"(?<![^\W\d_])(?:{'|'.join(sorted(TIME_WORDS, key=len, reverse=True))})(?![^\W\d_])"
    rf"[ \t]*[:：]?[ \t]*(?P<t>{_R10_TIME}){_CLOCK_END}"
    rf"(?:{_RANGE_SEP}(?P<t2>{_R10_TIME}){_CLOCK_END})?", re.I)
# v4.1 item 7 (D-52b): `saat 14:30 versiyası` names a version, not a time;
# the benchmark plants it as a look-alike (negatives.py `policy_version_time`)
_VERSION_AFTER = re.compile(r"[ \t]*-?[ \t]*versiya", re.I)


def _r10_stamp(text: str, s: int, e: int, lex: Lexicon) -> tuple[int, int, str] | None:
    """`_stamp_of_time` on the HH:MM part (it reads any seconds itself)."""
    return _stamp_of_time(text, s, re.match(_CLOCK, text[s:e]).end() + s, lex)


def rule_r10(w: _Work, lex: Lexicon) -> None:
    """A valid HH:MM or HH:MM:SS right after `saat`/`vaxtı` (and both ends of a
    range) is TIME, on every occurrence the resolver places; a time inside a
    stamp (R2, D-51f line stamps) or a declared look-alike stays out, and an
    occurrence that is a stamp is declared a TIMESTAMP look-alike so the
    resolver does not claim it. A time followed by a form of `versiya`
    (`saat 14:30 versiyası`) is a version's name: declared a
    `policy_version_time` look-alike, not labelled."""
    text = w.text
    found = []
    for m in _TIME_AFTER_WORD.finditer(text):
        version = _VERSION_AFTER.match(text, m.end())
        for g in ("t", "t2"):
            if not m.group(g):
                continue
            s, e = m.span(g)
            if not version:
                found.append((s, e))
            elif not w.covered(s, e):
                w.decoys.append({"start": s, "end": e, "kind": "policy_version_time", "resembles": "TIME"})
    for s, e in sorted(set(found)):
        if w.covered(s, e):
            continue
        if _r10_stamp(text, s, e, lex):
            continue
        placed, _ = resolve_claims(text, [{"label": "TIME", "text": text[s:e]}], blocked=w.spans())
        for p in placed:
            ps, pe = p["start"], p["end"]
            st = _r10_stamp(text, ps, pe, lex)
            if st:
                w.decoys.append({"start": st[0], "end": st[1], "kind": "TIMESTAMP",
                                 "resembles": "TIME" if st[2].startswith(("line", "speaker")) else "DATE"})
            else:
                w.add("R10", ps, pe, "TIME", "after a time word" if ps == s else "another occurrence")


# --------------------------------------------------------------------------
# the gate, and clean_doc
# --------------------------------------------------------------------------

def _gate_state(text: str, ents: list[dict], decoys: list[dict], rec: dict) -> dict:
    spans = [(d["start"], d["end"]) for d in decoys]
    reclaimed, _ = resolve_claims(text, [{"label": e["label"], "text": e["text"]} for e in ents], blocked=spans)
    drift = ({(e["start"], e["end"], e["label"]) for e in reclaimed}
             ^ {(e["start"], e["end"], e["label"]) for e in ents})
    planned = [(p.get("label"), p.get("value")) for p in (rec.get("_spec") or {}).get("entities") or []
               if isinstance(p, dict) and p.get("label") and p.get("value")]
    full = {**rec, "entities": ents, "_decoys": decoys} if decoys or "_decoys" in rec else {**rec, "entities": ents}
    return {
        "repeats": find_unlabeled_repeats(text, ents, exempt=spans),
        "drift": frozenset(drift),
        "boundary": len(span_boundary_problems(text, ents)),
        "anchor": sum(1 for e in ents if e["label"] in ANCHOR_REQUIRED
                      and not has_anchor(e["label"], text, e["start"], e["end"])),
        "planned": len(find_unlabelled_planned(text, ents, planned, spans)) if planned else 0,
        "validator": len(validate_example(full)),
        "repeat20": int(_most_repeated(ents, text) >= MAX_VALUE_REPEATS),
    }


def _new_failure(before: dict, after: dict) -> list[str]:
    return [k for k in before if not (after[k] <= before[k])]


def clean_doc_detail(doc: dict, lex: Lexicon | None = None) -> Result:
    """`clean_doc` with every change listed (for reports)."""
    lex = lex or lexicon()
    src = source_of(doc)
    text = doc["text"]
    kinds, _extra = r8_kinds(doc)
    if kinds:
        return Result(None, ["R8"], [Change("R8", "drop", note=", ".join(sorted(set(kinds))))])
    if src == "old":
        why = r1_reasons(doc)
        if why:
            return Result(None, ["R1"], [Change("R1", "drop", note=", ".join(why))])

    w = _Work(doc)
    rule_r2(w, lex)
    rule_r3(w)
    rule_r6(w, lex)
    rule_r7(w, lex, src)
    rule_r5(w, lex)
    rule_r4(w, lex)
    if any(c.rule in ("R4", "R5") and c.action == "label" for c in w.changes):
        rule_patronymic(w, lex, "R5")
    rule_r9(w, lex)
    rule_r10(w, lex)
    if w.drop:
        return Result(None, [w.drop.rule], [w.drop] + w.changes, w.skipped)
    if not w.changes:
        return Result(doc, [], [], w.skipped)

    ents = sorted(w.ents, key=lambda e: (e["start"], e["end"]))
    for a, b in zip(ents, ents[1:]):
        if b["start"] < a["end"]:
            raise AssertionError(f"{doc.get('id')}: overlapping spans after cleaning {a} {b}")
    for e in ents:
        assert text[e["start"]:e["end"]] == e["text"], (doc.get("id"), e)
    decoys = sorted(w.decoys, key=lambda d: (d["start"], d["end"]))
    orig_ents = [dict(e, text=text[e["start"]:e["end"]]) for e in doc.get("entities") or []]
    before = _gate_state(text, orig_ents, list(doc.get("_decoys") or []), doc)
    after = _gate_state(text, ents, decoys, doc)
    bad = _new_failure(before, after)
    if bad:
        return Result(None, ["GATE"], [Change("GATE", "drop", note="new failure: " + ", ".join(bad))] + w.changes,
                      w.skipped)

    rules = sorted({c.rule for c in w.changes}, key=RULE_IDS.index)
    out = dict(doc)
    out["entities"] = [{k: e[k] for k in ("start", "end", "label", "text")} for e in ents]
    if decoys or "_decoys" in doc:
        out["_decoys"] = decoys
    if not out["entities"] and not ((doc.get("_spec") or {}).get("negative_only") is True):
        out["_pii_free"] = True
    out["_v4_clean"] = rules
    return Result(out, rules, w.changes, w.skipped)


def clean_doc(doc: dict) -> tuple[dict | None, list[str]]:
    """The cleaned record (None: drop it) and the ids of the rules applied."""
    r = clean_doc_detail(doc)
    return r.doc, r.rules


# --------------------------------------------------------------------------
# files and counts (build_sprint_mix.py --v4-clean, scripts/v4_clean_report.py)
# --------------------------------------------------------------------------

class Tally:
    """Counts per (source, rule, what): `docs` changed, values `labelled`,
    `unlabelled`, `trimmed`, documents `dropped` (by the rule that dropped
    them), name candidates `unplaceable` (left unlabelled: the resolver would
    not place them), and `checksum_only_extra` (IMEI-type look-alikes with a
    card's shape, counted only)."""

    WHAT = ("docs", "labelled", "unlabelled", "trimmed", "dropped", "unplaceable")

    def __init__(self):
        from collections import Counter
        self.c = Counter()
        self.docs_in = Counter()
        self.extra = Counter()

    def add(self, source: str, doc: dict, result: Result) -> None:
        self.docs_in[source] += 1
        _, extra = r8_kinds(doc)
        if extra:
            self.extra[source] += 1
        for ch in result.skipped:
            self.c[source, ch.rule, "unplaceable"] += 1
        if result.doc is None:
            self.c[source, result.rules[0], "dropped"] += 1
            return
        for r in result.rules:
            self.c[source, r, "docs"] += 1
        for ch in result.changes:
            what = {"label": "labelled", "unlabel": "unlabelled", "trim": "trimmed"}.get(ch.action)
            if what:
                self.c[source, ch.rule, what] += 1

    def sources(self) -> list[str]:
        return list(self.docs_in)

    def table(self, sources: list[str] | None = None) -> list[str]:
        """Markdown: one row per rule, one column per source, cells
        `labelled / unlabelled / trimmed / dropped`."""
        sources = sources or self.sources()
        head = "| rule | " + " | ".join(sources) + " |"
        out = [head, "|" + "---|" * (len(sources) + 1)]
        for rule in RULE_IDS:
            cells = []
            for s in sources:
                vals = [self.c[s, rule, w] for w in ("labelled", "unlabelled", "trimmed", "dropped")]
                cells.append(" / ".join(f"{v:,}" for v in vals) if any(vals) else "")
            if any(cells):
                out.append(f"| {rule} | " + " | ".join(cells) + " |")
        out.append("| documents in | " + " | ".join(f"{self.docs_in[s]:,}" for s in sources) + " |")
        out.append("| documents out | " + " | ".join(
            f"{self.docs_in[s] - sum(self.c[s, r, 'dropped'] for r in RULE_IDS):,}" for s in sources) + " |")
        return out

    def as_json(self) -> dict:
        out: dict = {}
        for (s, r, w), n in sorted(self.c.items()):
            out.setdefault(s, {}).setdefault(r, {})[w] = n
        return {"docs_in": dict(self.docs_in), "counts": out,
                "checksum_only_extra_docs (IMEI_BAD_LUHN with a card's shape, not dropped)": dict(self.extra)}


def clean_record(doc: dict, tally: Tally | None = None, source: str | None = None) -> Result:
    """clean_doc_detail + counting."""
    r = clean_doc_detail(doc)
    if tally is not None:
        src = source or source_of(doc)
        tally.add(src, doc, r)
    return r


def clean_jsonl(src: Path, dst: Path, tally: Tally | None = None, source: str | None = None) -> Path:
    """Clean a JSONL file into `dst` (never in place). A record no rule
    touched is written byte for byte; a changed one is re-serialised; a
    dropped one is left out. Returns `dst`."""
    src, dst = Path(src), Path(dst)
    if src.resolve() == dst.resolve():
        raise ValueError("clean_jsonl never writes over its input")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    with src.open("rb") as fin, tmp.open("wb") as fout:
        for line in fin:
            if not line.strip():
                continue
            doc = json.loads(line)
            r = clean_record(doc, tally, source)
            if r.doc is None:
                continue
            if r.doc is doc:
                fout.write(line if line.endswith(b"\n") else line + b"\n")
            else:
                fout.write((json.dumps(r.doc, ensure_ascii=False) + "\n").encode("utf-8"))
    tmp.replace(dst)
    return dst


def lexicon_sha256(path: Path = LEXICON_PATH) -> str:
    """Of the LF form, as git stores it: a Windows checkout (core.autocrlf)
    writes CRLF, and the data card's hash must match the Mac build's."""
    import hashlib
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
