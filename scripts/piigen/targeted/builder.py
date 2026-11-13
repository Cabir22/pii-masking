"""The targeted corpus builder (P2-4).

Fast, exact and fully controlled training documents for the contrast lessons
the benchmark showed checkpoint 1 never learned:

  decoy_pair   the same frame twice, once with a valid value (labeled) and once
               with an anchored decoy (unlabeled, declared in `_decoys`);
               includes the name decoys (`Ərizənin …`, `<SURNAME> MMC`,
               project and topic names) and `otaq`/`mərtəbə` beside a labeled
               `bina`
  contrast     token vs key, IPv6 vs MAC, licence vs ID card with the same
               `AA`/`AB` prefix -- side by side, under their own anchors
  prose        C1 frames with an anchor form from every ANCHORS[label] form
  structured   CSV, pipe table, JSON, config, log, key-value, dialogue
  pii_free     NEUTRAL sentences and decoys only, `entities: []`

Every document is written into a `Draft` that records exact offsets as it
goes, then self-checked against every gate it will meet later -- the
shared validator, the quality screen, the leak gate, the resolver (spans
must be what the resolver itself would produce), structural positions, R4
for every decoy -- and rebuilt if it fails. The reasons are counted, so a
frame that keeps failing shows up in `--stats` instead of vanishing.
"""

from __future__ import annotations

import math
import collections
import importlib
import importlib.util
import random
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from ..anchors import ANCHOR_REQUIRED, has_anchor, structural_kind
from ..config import ENTITY_TYPES
from ..leak_screen import forbidden_ngrams, forbidden_values
from ..locales.az import SETTLEMENT_KINDS, SETTLEMENTS, year_suffix
from ..locales.az import last_spoken_word as AZ_last_spoken_word
from ..llm.quality import find_leaked_pii
from ..llm.quality_filter import (MAX_PII_DENSITY, MIN_CARRIER_WORDS, carrier_word_count,
                                  pii_density, screen_record)
from ..llm.specs import LENGTH_BANDS
from . import long_docs as LD
from ..negatives import (AGE_SHAPED, ALL_DECOY_KINDS, CAPS_HEADING, ED25519_PUBLIC_LEAD,
                         LABEL_ANCHOR_PHRASES, KEY_PLACEHOLDER, LINE_START_CONTROL, PLACE_WORD,
                         TIME_LINE_STAMP, active_decoy_kinds, make_decoy, public_key_ed25519)
from ..blocklist import is_blocked
from ..leak_screen import is_forbidden
from ..noise import apply_entity_casing
from ..provenance import GEN_VERSION
from ..resolver import complete_occurrences, noisy_forms, resolve_claims
from ..text import fold_diacritics
from ..validate import validate_example, value_valid
from ..values import ValueFactory, ValuePool
from . import formats as FMT
from . import frames_v4 as V4
from . import frames_v42 as V42
from . import frames_v43 as V43
from . import quotas as Q
from . import suffix as SFX
from .suffix_frames import KIND, SUFFIX_FRAMES

NAME_LABELS = ("GIVENNAME", "SURNAME", "CITY", "STREET")


# --------------------------------------------------------------------------- #
# Frames (contract C1)
# --------------------------------------------------------------------------- #

def load_frames_module():
    """The `frames_az.py` once it exists, otherwise the stub.

    Checked with find_spec, not a bare try/except ImportError: if the real
    file exists but is broken, that must fail loudly, never fall back.
    """
    name = f"{__package__}.frames_az"
    module = importlib.import_module(name if importlib.util.find_spec(name)
                                     else f"{__package__}.frames_az_stub")
    missing = [n for n in ("ANCHORS", "FRAMES", "GENERIC_FRAMES", "NEUTRAL",
                           "FRAME_VERSION") if not hasattr(module, n)]
    if missing:
        raise ImportError(f"{module.__name__} lacks the C1 names {missing}")
    return module


def load_homographs_module():
    """The `homographs_az.py` (P4-2) once it exists, otherwise the
    stub. Like the frames: a broken real file fails loudly, never falls back."""
    name = f"{__package__}.homographs_az"
    module = importlib.import_module(name if importlib.util.find_spec(name)
                                     else f"{__package__}.homographs_az_stub")
    missing = [n for n in ("HOMOGRAPHS", "LONE_NAMES", "LONE_WORDS", "HOMOGRAPHS_VERSION")
               if not hasattr(module, n)]
    if missing:
        raise ImportError(f"{module.__name__} lacks {missing}")
    return module


_MARKER = re.compile(r"\[\[(.+?)\]\]|<<(.+?)>>")


def parse_marked(sentence: str) -> tuple[str, str, str, str]:
    """`Bu gün [[Dənizə]] yazdım.` -> (before, marked word, after, side), side
    being "name" ([[...]]) or "word" (<<...>>). Exactly one marker."""
    marks = list(_MARKER.finditer(sentence))
    if len(marks) != 1:
        raise ValueError(f"a homograph sentence needs exactly one marker: {sentence!r}")
    m = marks[0]
    side = "name" if m.group(1) is not None else "word"
    return sentence[:m.start()], m.group(1) or m.group(2), sentence[m.end():], side


class HomographLibrary:
    def __init__(self, module) -> None:
        self.source = module.__name__.rsplit(".", 1)[-1]
        self.version = module.HOMOGRAPHS_VERSION
        self.entries: dict[str, dict[str, list]] = {}
        for name, e in module.HOMOGRAPHS.items():
            sides = {"name": [], "word": []}
            for side in ("name", "word"):
                for i, s in enumerate(e[side]):
                    before, word, after, got = parse_marked(s)
                    if got != side:
                        raise ValueError(f"{name}: a {side} sentence is marked as {got}: {s!r}")
                    sides[side].append((f"H.{name}.{side}.{i}", before, word, after))
            if not sides["name"] or not sides["word"]:
                raise ValueError(f"{name}: needs both name and word sentences")
            self.entries[name] = sides
        self.lone_names = list(module.LONE_NAMES)
        self.lone_words = list(module.LONE_WORDS)
        # optional, so a full name agrees: Səma Ağayeva, not Səma Ağayev
        self.gender = {name: e.get("gender") for name, e in module.HOMOGRAPHS.items()}


_SLOT = re.compile(r"\{a\}|\{v(?::([a-z_]+))?\}")


@dataclass(frozen=True)
class Frame:
    fid: str
    text: str
    case: str | None          # a {v:CASE} slot (rendered by P2-4c)
    gap: int | None           # words between {a} and {v}; None without {a}
    folded: bool              # written without Azerbaijani letters ("gorunur")


def parse_frame(fid: str, text: str) -> Frame:
    values = [m for m in _SLOT.finditer(text) if m.group(0) != "{a}"]
    if len(values) != 1:
        raise ValueError(f"{fid}: a frame needs exactly one value slot: {text!r}")
    slot, a = values[0], text.find("{a}")
    gap = None
    if a != -1:
        between = text[a + 3:slot.start()] if a < slot.start() else text[slot.end():a]
        gap = len(between.split())
    # An ASCII-folded frame gets a folded anchor and phrase too: nobody writes
    # half a sentence with Azerbaijani letters and half without.
    folded = fold_diacritics(text) == text and any(c.isalpha() for c in text)
    return Frame(fid, text, slot.group(1), gap, folded)


class FrameLibrary:
    def __init__(self, module) -> None:
        self.source = module.__name__.rsplit(".", 1)[-1]
        self.version = module.FRAME_VERSION
        self.anchors: dict[str, list[str]] = module.ANCHORS
        by_label = {label: [parse_frame(f"F.{label}.{i}", t) for i, t in enumerate(ts)]
                    for label, ts in module.FRAMES.items()}
        generic = [parse_frame(f"G.{i}", t) for i, t in enumerate(module.GENERIC_FRAMES)]
        # {v:CASE} frames are filled through the suffix renderer (P2-4c);
        # a case the renderer does not know fails here, loudly
        unknown = sorted({f.case for fs in [*by_label.values(), generic] for f in fs
                          if f.case is not None and f.case not in SFX.FORMS})
        if unknown:
            raise ValueError(f"frames use case codes the renderer does not know: {unknown}")
        self.case_frames = (sum(f.case is not None for fs in by_label.values() for f in fs)
                            + sum(f.case is not None for f in generic))
        self.skipped_case_frames = 0
        self.by_label = by_label
        self.generic = generic
        self.pairable = [f for f in self.generic if "{a} {v}" in f.text]
        registers = getattr(module, "NEUTRAL_BY_REGISTER", None) or {"mixed": list(module.NEUTRAL)}
        self.neutral = {reg: [(f"N.{reg}.{i}", s) for i, s in enumerate(ss)]
                        for reg, ss in registers.items()}
        if not self.pairable:
            raise ValueError("GENERIC_FRAMES has no frame with an adjacent '{a} {v}'")

    def anchor_forms(self, label: str) -> list[str]:
        forms = self.anchors.get(label)
        if forms:
            return list(forms)
        return [name.lower() for name in FMT.FIELDS[label][0]]


# --------------------------------------------------------------------------- #
# Fixed templates of the pair and contrast families (frames too: 3% rule)
# --------------------------------------------------------------------------- #

# Sentence-initial nouns (GIVENNAME decoys) and the name sentences they pair with.
SI_GENITIVE = ["{v} surəti arxivə göndərilib.", "{v} nömrəsi sistemdə qeydə alınıb.",
               "{v} mətni yenidən yoxlanılıb.", "{v} statusu dəyişdirilib.",
               "{v} əsli şöbədə saxlanılır.", "{v} baxılma müddəti uzadılıb."]
SI_LOCATIVE = ["{v} qeyd olunub ki, sənədlər tam təqdim edilib.",
               "{v} göstərilib ki, müraciətə artıq baxılıb.",
               "{v} heç bir düzəliş edilməyib.", "{v} bütün tələblər nəzərə alınıb.",
               "{v} əlavə qeyd yoxdur."]
NAME_START = {
    "f": ["{v} xanım sənədləri şəxsən təhvil verib.", "{v} xanım müraciətini geri götürüb.",
          "{v} xanım nəticə ilə maraqlanıb."],
    "m": ["{v} bəy sənədləri şəxsən təhvil verib.", "{v} bəy müraciətini geri götürüb.",
          "{v} bəy nəticə ilə maraqlanıb."],
    "any": ["{v} bu gün ofisə gəlib.", "{v} müraciətin nəticəsini soruşub.",
            "{v} sənədləri imzalayıb.", "{v} telefonla əlaqə saxlayıb."],
}
# D-2 policy decoys: a name used as a company, project or topic name.
POLICY_PAIRS = {
    "policy_surname_in_company": (
        "SURNAME",
        ["Müqavilə {v} ilə bağlanıb.", "Sifariş {v} tərəfindən təsdiqlənib.",
         "Hesab-faktura {v} adına tərtib edilib.", "Tender {v} tərəfindən udulub.",
         "Məhsullar {v} anbarından göndərilib."],
        ["Müqavilə {v} soyadlı sahibkarla bağlanıb.", "Sifariş müştəri {v} tərəfindən təsdiqlənib.",
         "Hesab-faktura {v} soyadlı şəxsin adına tərtib edilib.",
         "Tenderin qalibi {v} soyadlı sahibkar olub.", "Məhsulları {v} soyadlı kuryer çatdırıb."]),
    "policy_city_as_project": (
        "CITY",
        ["Tədbir {v} çərçivəsində keçiriləcək.", "{v} üzrə hesabat hazırlanıb.",
         "Könüllülər {v} üçün qeydiyyatdan keçir.", "Şirkət {v} sponsoru olub.",
         "Sərgi {v} proqramına daxil edilib.",
         # D-34: a city in a signatory slot is CITY, not a person's name
         "Müqaviləni {v} təşkilat komitəsi imzalayıb."],
        ["Tədbir {v} şəhərində keçiriləcək.", "{v} şəhəri üzrə hesabat hazırlanıb.",
         "Könüllülər {v} şəhərindən qeydiyyatdan keçir.", "Şirkət {v} şəhərində filial açıb.",
         "Sərgi {v} şəhərində təşkil olunub.",
         "Müqaviləni {v} filialının rəhbəri imzalayıb."]),
    # D-34 (D-33f `decoy_names_as_org`): a given name + a shop word is a
    # business in the signatory slot; a person's given name in the same slot
    "policy_givenname_in_company": (
        "GIVENNAME",
        ["Müqavilə {v} ilə imzalanıb.", "Sifarişi {v} təsdiqləyib.",
         "Hesab-faktura {v} adına tərtib edilib.", "Malları {v} göndərib.",
         "Təhvil-təslim aktını {v} tərəfi imzalayıb."],
        ["Müqavilə {v} adlı sahibkarla imzalanıb.", "Sifarişi müştəri {v} təsdiqləyib.",
         "Hesab-faktura {v} adlı şəxsin adına tərtib edilib.", "Malları kuryer {v} göndərib.",
         "Təhvil-təslim aktını nümayəndə {v} imzalayıb."]),
    # D-34 (D-33f, `foreign_names` brands): a foreign brand where a person
    # could stand; a (mostly foreign) surname in the same slot
    "policy_foreign_brand": (
        "SURNAME",
        ["{v} nümayəndəsi iclasda iştirak edib.", "Tərcüməni {v} sifariş edib.",
         "{v} təklifini rəsmi məktubla göndərib.", "Müqaviləni {v} imzalayıb.",
         "{v} görüşün vaxtını dəyişməyi xahiş edib."],
        ["{v} soyadlı nümayəndə iclasda iştirak edib.", "Tərcüməni cənab {v} sifariş edib.",
         "Təklifi {v} soyadlı mütəxəssis rəsmi məktubla göndərib.",
         "Müqaviləni direktor {v} imzalayıb.",
         "Görüşün vaxtını dəyişməyi {v} soyadlı əməkdaş xahiş edib."]),
    "policy_street_as_topic": (
        "STREET",
        ["Kitabxanada {v} təqdim olunub.", "Müəllim tələbələrə {v} tövsiyə edib.",
         "Jurnalda {v} dərc edilib.", "Festivalda {v} nümayiş etdirilib."],
        ["Kitabxana {v} ünvanında yerləşir.", "Müəllim tələbələri {v} ünvanındakı binaya dəvət edib.",
         "Jurnalın redaksiyası {v} ünvanına köçüb.", "Festival {v} yaxınlığında keçirilib."]),
    # D-57 S3 (D-2): a quoted organisation or brand built from a town word,
    # unlabelled; its twin, a real town right after an opening bracket or quote
    "policy_city_in_brand": ("CITY", V42.CITY_BRAND_DECOY, V42.CITY_BRAND_VALID),
}
# A labeled `bina` with a room, floor or office number beside it.
# The D-57 review, D: frames 1 and 3 no longer `… daxilində
# keçiriləcək` / `… hissəsinə köçürülüb` (odd with any building)
BUILDING_SENTENCES = ["Ofis {b}, {d} ünvanında yerləşir.", "Görüşün yeri: {b}, {d}.",
                      "Kuryer sifarişi {b}, {d} ünvanına çatdırmalıdır.",
                      "Şöbə yeni ünvana köçürülüb: {b}, {d}.",
                      "Müştəri {b}, {d} ünvanında qeydiyyatdadır.",
                      "Arxiv sənədləri {b}, {d} ünvanında saxlanılır."]
# ... and `ev` (a dwelling) only in the courier and the customer's registration
BUILDING_EV_FRAMES = frozenset({2, 4})
BUILDING_VALID = ["bina {v}", "bina nömrəsi {v}"]

# Between a valid value and its decoy in the same frame (no PII, no digits).
BRIDGES = ["Sonradan məlumat dəqiqləşdirilib.", "Yoxlama zamanı qeydlər müqayisə olunub.",
           "Köhnə və yeni qeydlər tutuşdurulub.", "Düzəliş edildikdən sonra qeyd yenilənib.",
           "Arxivdə başqa bir qeyd də tapılıb.", "Sistemdə ikinci qeyd də mövcuddur.",
           "Əməkdaş hər iki qeydi yoxlayıb.", "Qeydlər arasında fərq aşkarlanıb.",
           "Əvvəlki versiya ilə müqayisə aparılıb.", "Sənədin surətində isə başqa məlumat var."]

CONTRAST = {
    "token_key": [
        "Sorğunun başlığında Authorization: Bearer {t} göndərilir, xidmətin API açarı isə {k} kimi saxlanılır.",
        "Tətbiq sessiya tokeni olaraq {t} alır, inteqrasiya üçün isə api key {k} istifadə olunur.",
        "Mobil tətbiqin access token dəyəri {t}, ödəniş xidmətinin API açarı isə {k} olaraq konfiqurasiya edilib.",
        "Jurnalda access token {t} qeyd olunub, həmin sorğuda API açarı {k} də göstərilib.",
        "Yeni sessiya tokeni {t} yaradıldı, köhnə api key {k} isə deaktiv edildi.",
        "Konfiqurasiyada API açarı {k} yazılıb, Authorization başlığında isə {t} tokeni ötürülür.",
        "Xidmətin api key parametri {k}, istifadəçinin access token dəyəri isə {t} kimi verilib.",
        "Bearer {t} ilə göndərilən sorğu API açarı {k} olan xidmətə yönləndirilib.",
        # D-34 (D-33f): the value ends the sentence, before its full stop
        "Xidmətin API açarı {k} kimi saxlanılır, istifadəçinin tokeni isə {t}.",
        "Sorğuda access token {t} ötürülüb, inteqrasiyanın API açarı isə {k}.",
    ],
    "ipv6_mac": [
        "Cihazın MAC ünvanı {m}, IPv6 ünvanı isə {i} kimi göstərilib.",
        "Şəbəkə hesabatında IPv6 ünvanı {i} olan qovşağın MAC ünvanı {m} qeyd olunub.",
        "Router yeni cihazı MAC ünvanı {m} ilə tanıdı və ona IPv6 ünvanı {i} verdi.",
        "Printerin fiziki MAC ünvanı {m}, şəbəkədəki IPv6 ünvanı isə {i}.",
        "Jurnalda qoşulan cihazın IPv6 ünvanı {i}, MAC ünvanı isə {m} olaraq yazılıb.",
        "Texniki pasportda MAC ünvanı {m} kimi, konfiqurasiyada isə IPv6 ünvanı {i} kimi göstərilib.",
    ],
    "licence_id": [
        "Sürücünün sürücülük vəsiqəsi {l}, şəxsiyyət vəsiqəsi isə {d} kimi göstərilib.",
        "Müqavilədə şəxsiyyət vəsiqəsinin nömrəsi {d}, sürücülük vəsiqəsinin nömrəsi isə {l} olaraq yazılıb.",
        "İcarə formasına sürücülük vəsiqəsi {l} və şəxsiyyət vəsiqəsi {d} daxil edilib.",
        "Yoxlama zamanı şəxsiyyət vəsiqəsi {d} ilə yanaşı sürücülük vəsiqəsi {l} də təqdim olunub.",
        "Sürücülük vəsiqəsinin nömrəsi {l}, şəxsiyyət vəsiqəsinin nömrəsi isə {d}.",
        "Sənəddə şəxsiyyət vəsiqəsi {d}, sürücülük vəsiqəsi isə {l} olaraq əks olunub.",
    ],
}
CONTRAST_LABELS = {"t": "ACCESS_TOKEN", "k": "API_KEY", "i": "IPV6_ADDRESS",
                   "m": "MAC_ADDRESS", "l": "AZ_DRIVER_LICENSE_NUMBER", "d": "AZ_ID_CARD_NUMBER"}
# D-34 (D-33f, `contrast_token_key`): beside a token/key pair, a container
# image digest or a token's first characters, which are neither
TOKEN_LOOK_ALIKES = {
    "image_digest": ["Konteyner obrazı {v} digest-i ilə yüklənib.",
                     "Deploy jurnalında obrazın digest dəyəri {v} kimi göstərilib.",
                     "Yeni versiyanın image digest-i {v} olaraq qeyd edilib."],
    "token_prefix_only": ["Mesajda tokenin yalnız əvvəli göstərilib: {v}.",
                          "Hesabatda tokenin ilk simvolları {v} kimi yazılıb, qalanı gizlədilib.",
                          "Jurnalda qısaldılmış token {v} görünür, tam dəyər saxlanılmır."],
}

# P2-4b, RC5: a PEM key on its own lines after an introducing sentence, or
# pasted onto one line; followed by a line break, `;`, a space or a quote --
# the contexts the benchmark's split keys sat in. No PII, no digits.
PEM_INTROS = ["Serverə giriş üçün istifadə olunan şəxsi açar aşağıdakıdır:",
              "Konfiqurasiya faylında bu şəxsi açar saxlanılıb:",
              "Sertifikatın şəxsi açarı belədir:",
              "Köhnə serverdən köçürülən açarın məzmunu:",
              "SSH açarı jurnala səhvən yazılıb:",
              "Deploy skriptində aşağıdakı şəxsi açar tapılıb:",
              "Təhlükəsizlik yoxlaması zamanı bu açar aşkarlanıb:",
              "Tərtibatçı bu açarı yazışmada paylaşıb:",
              "Ehtiyat nüsxədə belə bir şəxsi açar var:",
              "Repozitoriyada saxlanılan açar:"]
PEM_INLINE = ["Jurnalda belə bir şəxsi açar qeydə alınıb: {v}{t}",
              "Konfiqurasiyada açarın dəyəri {v}{t}",
              "Mühit dəyişənində şəxsi açar {v}{t}",
              "Mesajda SSH açarı da göndərilib: {v}{t}",
              "Tikətə əlavə olunan açar {v}{t}",
              "Faylın məzmununda şəxsi açar görünür: {v}{t}"]
PEM_AFTER = ["Açar dərhal ləğv edilməlidir.", "Bu açar artıq dəyişdirilib.",
             "Açarın yenisi ilə əvəzlənməsi tapşırılıb.",
             "Bu məlumat açıq kanalda paylaşılmamalıdır.",
             "Hadisə təhlükəsizlik şöbəsinə bildirilib.", "Açar arxivdən silinib.",
             "Sorğu bu səbəbdən dayandırılıb.", "Giriş hüquqları yenidən yoxlanılıb."]
# A value wrapped in brackets or quotes inside a sentence (`(AZ3710)`).
TOUCH_WRAPPERS = (("(", ")"), ('"', '"'), ("«", "»"), ("[", "]"))

# P2-4d (RC9): documents of one to five words. {g} given name, {s} surname,
# {c} city, {t} street, {w} a lone lowercase homograph word (D-10: unlabelled).
MINIMAL_FORMS = {
    "name_alone": ["{g}"],
    "name_punct": ["{g}.", "{g}!", "{g},", "({g})", '"{g}"', "{g}?", "«{g}»"],
    "full_name": ["{g} {s}", "{s} {g}", "{g} {s}.", "{s} {g}."],
    "greeting": ["Salam, {g}!", "Sağ ol, {g}.", "{g}, salam!", "Hörmətlə, {g} {s}",
                 "Hörmətlə,\n{g} {s}", "— {g}", "Əziz {g},", "Təşəkkürlər, {g}!", "Salam {g}"],
    "chat_or_list": ["- {g} {s}", "• {g}", "{g}: gəlirəm", "{g}: bəli", "* {s} {g}"],
    "place_alone": ["{c}", "{c}.", "{t}", "{t}."],
    "lone_word": ["{w}", "{w}.", "{w}?"],
}

DECOY_GROUPS = {
    "sentence_initial": ("sentence_initial_genitive", "sentence_initial_locative"),
    "policy_names": tuple(POLICY_PAIRS),
    "building": ("room_number", "floor_number", "office_number"),
}

# D-34g (D-33f): the value right BEFORE its noun ("{v} tarixində imzalanıb",
# "{v} indeksinə göndərilib", "{v} yaşında", "{v} kartı"). Run B's data had
# almost no look-alikes there (DATE 8%, AGE 3%, ZIP 0%, card 5% of the slot),
# and the probes plant them there. One sentence carries the valid value, the
# same sentence the look-alike. The kinds stay in the `other` group as well.
NOUN_FRAMES = {
    "DATE": ["Müqavilə {v} tarixində imzalanıb.", "Ərizə {v} tarixində qəbul edilib.",
             "Qərar {v} tarixindən qüvvəyə minir.", "Arayış {v} tarixinə qədər etibarlıdır.",
             "Ödəniş {v} tarixində həyata keçirilib.", "Növbəti yoxlama {v} tarixinə təyin olunub.",
             *V42.NOUN_DATE_TARIXLI],                   # D-57 M4: `{v} tarixli`
    # D-57 M3: FIN look-alikes before the word (`{v} FİN-i`), beside real FINs there
    "AZ_FIN": V42.NOUN_FIN,
    "AGE": ["Pasiyent {v} yaşında qeydiyyata alınıb.", "Namizəd anketdə {v} yaşında olduğunu yazıb.",
            "Sığortalı müqavilədə {v} yaşında göstərilib.", "Şagird {v} yaşında məktəbə qəbul olunub."],
    "ZIPCODE": ["Bağlama {v} indeksinə göndərilib.", "Məktub {v} indeksli poçt şöbəsinə çatıb.",
                "Kuryer sifarişi {v} indeksinə uyğun ünvana aparır.",
                "Sifariş {v} indeksi üzrə qeydə alınıb."],
    "PAYMENT_CARD_NUMBER": ["{v} kartı ödəniş üçün qeyd olunub.", "Ödəniş {v} nömrəli kartla aparılıb.",
                            "Geri ödəniş {v} kartına köçürüləcək.", "Abunə haqqı {v} kartından tutulur."],
}
# D-34g: the labels whose look-alikes the probes plant in `label: value` lines
# (EMAIL: D-33f found look-alike emails masked in every structured format)
SLOT_LABELS = frozenset({"DATE", "TIME", "AGE", "CARD_SECURITY_CODE", "ZIPCODE",
                         "PAYMENT_CARD_NUMBER", "ICCID", "IBAN", "AZ_FIN", "EMAIL"})
# ... and the field names of the `form` family's `Label: value` lines
FORM_FIELDS = {
    "DATE": ["Doğum tarixi", "Tarix", "Müqavilənin tarixi", "Qeydiyyat tarixi", "Etibarlılıq tarixi"],
    "TIME": ["Saat", "Görüş vaxtı", "Başlama vaxtı", "Qəbul saatı"],
    "AGE": ["Yaş", "Müştərinin yaşı", "Xəstənin yaşı"],
    "CARD_SECURITY_CODE": ["CVV", "CVC", "CVV kodu", "Kartın təhlükəsizlik kodu"],
    "ZIPCODE": ["Poçt indeksi", "İndeks", "ZIP"],
    "PAYMENT_CARD_NUMBER": ["Kart nömrəsi", "Ödəniş kartı", "Bank kartı"],
    "ICCID": ["ICCID", "SIM kartın ICCID nömrəsi"],
    "IBAN": ["IBAN", "Hesab nömrəsi (IBAN)"],
    "AZ_FIN": ["FİN", "FİN kodu"],
    "EMAIL": ["E-poçt", "Elektron poçt", "E-poçt ünvanı"],
    # v4.2 fix list: the licence slot of `slot_invalid`
    "AZ_DRIVER_LICENSE_NUMBER": ["Sürücülük vəsiqəsi", "Sürücülük vəsiqəsinin nömrəsi"],
}
# D-41a (`decoy_cvv` still fully triggered: 5-digit codes and `12345`
# dummies): the same CVV sentence with a real CVV and with a 5-digit
# look-alike, so the length is the only difference. Run B's data held ~560
# five-digit look-alikes against ~5,500 real CVVs, never side by side.
# (a recording verb after the value takes kimi/olaraq: native-review rule R1)
CVV_FRAMES = ["Kartın CVV kodu {v} kimi qeyd olunub.", "Ödəniş zamanı CVV kodu {v} olaraq daxil edilib.",
              "Formada CVC kodu {v} olaraq yazılıb.", "Sifarişdə CVV2 kodu {v} kimi göstərilib.",
              "Müştəri təhlükəsizlik kodu {v} olaraq bildirib.", "Kartın arxasındakı CVV {v} kimi oxunur."]
CVV_KINDS = ("cvv_5_digits", "cvv_sequential_5")
# D-42c item 5: the labels whose look-alikes Run B masked most in shadow's
# PII-free documents; `pii_free` documents draw this share of their
# look-alikes from them (quotas pii_free.focus_rate)
# v4.1 A5 (v3_shadow_shapes.md, PII-free documents masked by predicted
# label: CVV 42, DATE 28, PRIVATE_KEY 23, AZ_FIN 22, SURNAME 20, cards 19,
# GIVENNAME 15) joins D-42c's labels; quotas.json `pii_free.focus_weights`
# weighs them. IPv4 (13) waits for the IPv4 analysis (v4.1 task 1, H3).
PII_FREE_FOCUS = frozenset({"EMAIL", "IPV6_ADDRESS", "TIME", "DATE", "ACCESS_TOKEN", "API_KEY",
                            "CARD_SECURITY_CODE", "PRIVATE_KEY", "AZ_FIN", "SURNAME",
                            "PAYMENT_CARD_NUMBER", "GIVENNAME"})

# D-42c item 3: VÖEN, passport and building numbers glued to punctuation --
# a trailing full stop, a dash (a suffix after a number: `-dur`, `-də`), a
# closing bracket; an opening bracket or `=` before. Run B's spans took the
# mark in (25) or dropped part of the value (25). {cop}/{loc} are the copula
# and locative suffixes, by the last digit's vowel (`suffix_after_number`).
EDGE_SENTENCES = {
    "AZ_VOEN": ["Şirkətin VÖEN-i {v}.", "Təşkilatın VÖEN kodu {v}{cop}.",
                "Vergi ödəyicisinin VÖEN-i ({v}) yoxlanılıb.", "Sorğu parametrləri: voen={v}, status=aktiv.",
                "Hesab-fakturada VÖEN: {v}."],
    "AZ_PASSPORT_NUMBER": ["Pasportun nömrəsi {v}.", "Xarici pasportun nömrəsi {v}{cop}.",
                           "Sərnişinin pasportu ({v}) yoxlanılıb.", "Sorğuda pasport={v} göndərilib.",
                           "Müraciətdə pasport: {v}."],
    "BUILDINGNUM": ["Ofis bina {v}{loc} yerləşir.", "Ünvan: Mərkəzi küçə, bina {v}.",
                    "Yeni filial (bina {v}) açılıb.", "Sorğuda bina={v} parametri göstərilib.",
                    # D-43c (finding 2): not `Kuryer ev 26-da` (read as a date)
                    "Mağaza bina {v}{loc}, birinci mərtəbədə yerləşir."],
    # v4.2 fix list (IBAN boundaries): an IBAN with the copula glued on, in
    # brackets, after `=` or a colon (native check)
    "IBAN": ["Şirkətin hesab nömrəsi {v}{cop}.", "Alıcının IBAN-ı {v}{cop}.",
             "Ödəniş üçün hesab ({v}) təsdiqlənib.", "Sorğuda iban={v} göndərilib.",
             "Hesab-fakturada IBAN: {v}."],
}
# D-42c item 4: VÖEN and building numbers mid-sentence after a document noun
# (in the X section / list / card) or a verb, with no anchor word right
# before; Run B masked no value of that label in such documents.
CONTEXT_SENTENCES = {
    "AZ_VOEN": ["Təşkilatın vergi qeydiyyatı yoxlanılıb, rekvizitlər bölməsində {v} kimi göstərilib.",
                "Vergi ödəyicilərinin siyahısında {v} də var.",
                "Şirkət bank hesabı açarkən {v} təqdim edib.",   # D-43c (finding 4)
                "Müqaviləyə əlavə olunan vergi kartında {v} kimi yazılıb."],
    "BUILDINGNUM": ["Ünvan kartında {v} kimi göstərilib.",
                    "Müştərinin ünvanı yenilənib, qeydiyyat bölməsində {v} kimi yazılıb.",
                    "Ev sahibi müraciət edərkən {v} göstərib.",
                    "Yaşayış ünvanları siyahısında {v} kimi əks olunub."],
}
# the vowel of the last digit's name: sıfır, bir, iki, üç, dörd, beş, altı,
# yeddi, səkkiz, doqquz -> the copula (-dır/-dir/-dur/-dür) and locative (-da/-də)
_DIGIT_VOWEL = dict(zip("0123456789", "ıiiüöeıiiu"))


def takes_suffix(value: str) -> bool:
    """A value ending in 1-9: its last spoken word is that digit's name. One
    ending in 0 is read by its tens or hundreds (10 `on` -> -dur, 40 `qırx`
    -> -dır, 100 `yüz` -> -dür), and one ending in a letter by the letter:
    neither takes a suffix sentence."""
    return value[-1] in "123456789"


def time_case_suffix(value: str, case: str) -> str:
    """The ablative (`-dan`/`-dən`) or dative (`-a`/`-ə`/`-ya`/`-yə`) after a
    clock time, by the vowel of its last spoken number: the seconds, else the
    minutes, else the hour when both are zero (`14:05:22-dən`, `10:00:00-dan`,
    `15:30:00-a`). v4.2 fix list: Azerbaijani ranges take these endings."""
    parts = [int(x) for x in value.split(":")]
    n = next((x for x in reversed(parts[1:]) if x), parts[0])
    word = AZ_last_spoken_word(n)
    back = next(c for c in reversed(word) if c in "aıoueəiöü") in "aıou"
    if case == "abl":       # built from the vowel: a quoted `dan` would read as a word
        return "-d" + ("a" if back else "ə") + "n"
    return ("-y" if word[-1] in "aıoueəiöü" else "-") + ("a" if back else "ə")


def suffix_after_number(value: str, kind: str) -> str:
    """`-dır`/`-dir`/`-dur`/`-dür` (cop) or `-da`/`-də` (loc) after a value
    that ends in 1-9, by that digit's spoken vowel (`takes_suffix`)."""
    v = _DIGIT_VOWEL[value[-1]]
    if kind == "cop":
        return "-d" + {"ı": "ır", "a": "ır", "i": "ir", "e": "ir", "ə": "ir", "u": "ur", "o": "ur",
                       "ü": "ür", "ö": "ür"}[v]
    return "-d" + ("a" if v in "aıou" else "ə")


# D-42c (shadow shapes): bare 4-digit ZIPs (`1043`), never found
# by Run B (0 of 62), mostly after a postal-code anchor word, a place name, a
# place name + postposition, an address word + anchor, a zone or value noun,
# a document-part noun, a pronoun. {c} a city, {z} the ZIP (bare 75%).
POSTAL_SENTENCES = [
    "Məktub {c} üzrə {z} indeksinə göndərilib.", "Bağlama {c} üçün {z} poçt indeksi ilə qeydə alınıb.",
    "Poçt indeksi {z} olan şöbə {t} şəhərində yerləşir.", "Ünvanın indeksi {z} kimi göstərilib.",
    "{c} üzrə poçt indeksi {z} olaraq yazılıb.", "Bu zona üzrə poçt indeksi {z} təyin edilib.",
    "Sorğuda göstərilən indeks dəyəri {z}{cop}.", "Anketin ünvan bölməsində indeks {z} kimi qeyd olunub.",
    "O, indeksi {z} olan ərazidə yaşayır.", "{t} şəhəri, {z} — çatdırılma bu ünvana olacaq.",
]
# v4.1 A5 (v3_shadow_shapes.md lead 3): a bare 4-digit ZIP right after a town
# and a comma, semicolon or dash, with NO index word: v3 missed 35% of bare
# ZIPs (after a comma or semicolon 7 of 21, after a dash 3 of 6), and v4's
# training had 63 such ZIPs in 25,000 documents. {t} is a town (labelled CITY).
POSTAL_BARE_SENTENCES = V4.POSTAL_BARE_SENTENCES       # frames_v4 section 13
# D-43c (finding 1): {t} is a town from az_cities.txt, for the
# sentences that call it `şəhər`; {c} may be a village (15 of 38 villages were
# called a town). Finding 3: `{c} üzrə poçt indeksi`.
# D-51d: `card_wrong_length` replaces the checksum-only `card_luhn_invalid`
NOUN_KINDS = ("date_bad_month", "date_impossible_day", "date_iso_out_of_range",
              "age_negative", "age_implausible", "zip_wrong_length", "card_wrong_length",
              # D-57 M4: the near misses before `tarixində`/`tarixli` (C4: all
              # 3 date triggers were 30 February there); M3: FIN look-alikes
              "date_feb_invalid", "date_month_near",
              "fin_with_hyphen", "fin_dummy_pattern", "fin_8_9_chars")
# D-57 M4: the date look-alikes a `noun` pair writes before `tarixində` /
# `tarixli`: 30-31 February (C4's three triggers), month 13-19
NOUN_DATE_KINDS = ("date_feb_invalid", "date_month_near")
# D-57 S4: a street name that ends in its type word, with no digit in it, so
# the building number after it reads as one (`Nizami küçəsi 45`). Only the
# type words that license a building number (anchors/az.py: not `küç.`, `pr.`)
_STREET_TYPE_END = re.compile(r"(küçəsi|prospekti|döngəsi)$")
# D-35a: DATE look-alikes in `label: value` lines up to ~10%: invalid dates only
# (month 13-18, day 30 in February, ISO out of range), which the value itself
# tells apart from a real date; in the keyed formats, where a date sits after
# its key (a CSV or pipe cell has no `key:` beside it)
DATE_SLOT_KINDS = ("date_bad_month", "date_impossible_day", "date_iso_out_of_range",
                   "date_feb_invalid", "date_month_near")             # v4.2 near misses
DATE_KEYED_FORMATS = frozenset({"json", "config", "key_value", "log"})
# where a grouped phone may sit after its key (`telefon: +994 55 123 45 67`); a
# space-separated value inside a log line would read as several fields
KEYED_PHONE_FORMATS = frozenset({"json", "config", "key_value", "dialogue"})
# Kinds with their own writer, never put into a generic frame: a multi-line key
PEM_DECOY_KINDS = frozenset({"public_key_block"})

# D-34 (D-33f, `single_entity`, `prose_card`, `prose_iban`): long clerical
# chains, 6-10 short office clauses joined by semicolons, with one value or
# one look-alike in the middle. Run B missed FINs, cards and IBANs there that
# it found in short sentences. No digits, names or places in the filler;
# {ref} is a filler reference code (an `internal_reference` look-alike).
CLERICAL_CLAUSES = [
    "müraciət ümumi şöbədə qeydiyyata alınıb", "sənədlər tam həcmdə təqdim olunub",
    "məsələ komissiyanın növbəti iclasına çıxarılıb", "ərizəçiyə ilkin cavab şifahi bildirilib",
    "əlavə arayış tələb olunmayıb", "işə baxılma müddəti bir ay uzadılıb",
    "qərarın surəti ərizəçiyə təqdim ediləcək", "şöbə rəhbəri məsələni nəzarətdə saxlayır",
    "sənədin əsli arxivdə saxlanılır", "yoxlama zamanı heç bir uyğunsuzluq aşkarlanmayıb",
    "cavab məktubu hazırlanaraq imzaya təqdim edilib", "məlumatlar müvafiq reyestrə daxil edilib",
    "icra müddəti cari ayın sonuna qədər müəyyən edilib", "bu barədə hüquq şöbəsinə məlumat verilib",
    "işin materialları elektron sistemə yüklənib", "nizamnamənin üçüncü bəndinə əsasən qərar qəbul edilib",
    "qaydaların beşinci maddəsinin ikinci hissəsi tətbiq olunub",
    "əvvəlki müraciətlə bağlı qeydlər yoxlanılıb", "işə məsul əməkdaş təyin olunub",
    "ödəniş haqqında qəbz sənədlərə əlavə edilib", "müqavilənin yeddinci bəndinə dəyişiklik edilib",
    "aktın ikinci nüsxəsi qarşı tərəfə göndərilib", "məsələ ilə bağlı daxili arayış hazırlanıb",
    "sənəd {ref} istinad nömrəsi ilə qeydə alınıb", "daxili qovluq {ref} kodu ilə açılıb",
    "qeyd {ref} saylı jurnalda əks olunub",
]
CLERICAL_VALUE = {
    # D-36b: a recording verb after the value takes "olaraq" (R1)
    "AZ_FIN": ["şəxsin FİN kodu {v} olaraq qeydə alınıb", "ərizəçinin FİN kodu sistemdə {v} olaraq qeydə alınıb",
               "FİN kodu {v} olaraq reyestrə daxil edilib"],
    "IBAN": ["köçürmə üçün hesab olaraq {v} qeyd edilib", "ödəniş {v} hesabına yönləndirilib",
             "hesab-fakturada {v} hesabı göstərilib", "vəsait {v} nömrəli hesaba köçürülüb"],
    "PAYMENT_CARD_NUMBER": ["ödəniş kartı olaraq {v} yazılıb", "kart məlumatlarında {v} göstərilib",
                            "ödəniş üçün {v} kartı qeyd olunub", "{v} kartı ödəniş üçün qeydə alınıb"],
    "EMAIL": ["əlaqə üçün {v} e-poçt ünvanı göstərilib", "cavab {v} ünvanına göndərilib",
              "ərizəçinin e-poçt ünvanı {v} kimi qeyd olunub"],
    "TELEPHONENUM": ["ərizəçinin əlaqə nömrəsi {v} olaraq göstərilib",
                     "{v} nömrəsi ilə əlaqə saxlanılıb"],
    "AZ_ID_CARD_NUMBER": ["şəxsiyyət vəsiqəsinin nömrəsi {v} olaraq yoxlanılıb",
                          "sənədin nömrəsi {v} kimi qeyd olunub"],
    "AZ_DRIVER_LICENSE_NUMBER": ["sürücülük vəsiqəsinin nömrəsi {v} olaraq göstərilib",
                                 "sənədin nömrəsi {v} kimi yoxlanılıb"],
    "AZ_PASSPORT_NUMBER": ["pasport nömrəsi {v} olaraq qeydə alınıb"],
    "AZ_VOEN": ["təşkilatın VÖEN nömrəsi {v} kimi göstərilib"],
}
# D-34 (D-33f `punct_touching`): a value glued to punctuation, no space on
# either side -- an IPv4 inside brackets, a FIN between `FİN:` and `;`, a
# phone inside `Əlaqə:(...)`, an email between an em dash and `!`. Run B's
# spans took the mark or stopped short there.
GLUED = {
    "IPV4_ADDRESS": ["Bağlantı [{v}] ünvanından gəlib.", "Jurnalda mənbə [{v}] kimi göstərilib.",
                     "Bloklanan ünvan: [{v}].", "Sorğular [{v}] serverinə yönləndirilib."],
    "AZ_FIN": ["Ərizəçinin məlumatları yoxlanılıb; FİN:{v}; status: təsdiqlənib.",
               "Qeyd: FİN:{v}; sənədlər tamdır.", "Şəxs müəyyən edilib (FİN:{v}; arayış verilib).",
               "Məlumat: FİN:{v}; müraciət qəbul olunub."],
    "TELEPHONENUM": ["Əlaqə:({v}) iş saatlarında.", "Müraciət üçün əlaqə:({v}).",
                     "Kuryerə zəng edin, əlaqə:({v}).", "Növbətçi operator, əlaqə:({v})."],
    "EMAIL": ["Sualınız varsa yazın —{v}!", "Cavab göndəriləcək ünvan —{v}!",
              "Sənədləri bu ünvana göndərin —{v}!", "Təklifləri gözləyirik —{v}!"],
}
GLUED_KINDS = {"IPV4_ADDRESS": ("ipv4_octet_over_255",), "AZ_FIN": ("fin_with_hyphen", "fin_8_9_chars"),
               "EMAIL": ("email_double_at", "email_localhost", "email_no_at")}

# D-39b (the shapes of the given names Run B missed in real text; the
# constructions only, never her text): 67 of 93 missed. 27 patronymics, mostly
# in one-name-per-line official lists; 22 given names in the list format
# `Surname Given Father oğlu/qızı`; 9 after a lowercase title or job word; 4
# alone on a signature line; 4 sentence-initial; 1 after an organisation name.
# Convention (D-39b): the father's name in a patronymic is GIVENNAME;
# `oğlu`/`qızı` stay outside the span. Names are from our pools.
NAMELIST_INTROS = [
    "Müsabiqədə iştirak üçün qeydiyyatdan keçmiş şəxslərin siyahısı:",
    "Komissiyanın tərkibi aşağıdakı kimi təsdiq edilib:",
    "Ərazi üzrə yeni təyin olunmuş əməkdaşların siyahısı:",
    "Məhkəmə iclasına çağırılan şəxslər:",
    "Təltif olunan şəxslərin siyahısı:",
    "Müraciət etmiş vətəndaşların siyahısı:",
    "Tenderdə iştirak edən təmsilçilər:",
    "İclasda iştirak edəcək şəxslər:",
    "Qəbul olunmuş abituriyentlərin siyahısı:",
    "Mükafata layiq görülən işçilər:",
]
NAMELIST_OUTROS = [
    "Siyahı rəsmi internet səhifəsində yerləşdirilib.",
    "Əlavə məlumat almaq istəyənlər müvafiq şöbəyə müraciət edə bilər.",
    "Siyahıya düzəliş olunarsa, bu barədə ayrıca məlumat veriləcək.",
    "Bütün şəxslərə əvvəlcədən yazılı bildiriş göndərilib.",
    "Sənədlərin əslini özləri ilə gətirmələri xahiş olunur.",
    "Qərar bütün iştirakçılara çatdırılıb.",
]
# a list line: {s} surname, {g} given name, {f} father's name, {p} oğlu/qızı
NAMELIST_LINES = {
    "plain": ("{s} {g} {f} {p}", 0.40),
    "numbered": ("{n}. {s} {g} {f} {p}", 0.25),
    "dash": ("— {s} {g} {f} {p}", 0.10),
    "given_first": ("{g} {f} {p} {s}", 0.15),
    "tail": ("{s} {g} {f} {p} — {t}", 0.10),
}
NAMELIST_TAILS = ["müraciət edən şəxs", "təmsilçi", "iştirakçı", "namizəd", "məsul əməkdaş", "ərizəçi"]
PATRO_SENTENCES = [
    "Ərizə {s} {g} {f} {p} adına qəbul edilib.", "Müqaviləni vətəndaş {s} {g} {f} {p} imzalayıb.",
    "Sənədləri {s} {g} {f} {p} şəxsən təqdim edib.", "{s} {g} {f} {p} haqqında qərar qəbul olunub.",
    "İddiaçı {s} {g} {f} {p} məhkəməyə müraciət edib.",          # D-40a (finding 4): no `kimi`
    "Torpaq sahəsi {s} {g} {f} {p} adına rəsmiləşdirilib.", "Çıxarışı {s} {g} {f} {p} əldə edib.",
]
ROLE_WORDS = ["direktor", "müdir", "hakim", "vəkil", "mühasib", "sədr", "katib", "prokuror",
              "müfəttiş", "rəis", "dosent", "professor", "həkim", "mühəndis", "nümayəndə"]
ROLE_SENTENCES = [
    "İclasa {role} {n} sədrlik edib.", "Müsabiqənin nəticələrini {role} {n} elan edib.",
    "Layihənin icrasına {role} {n} nəzarət edir.", "Sənədi {role} {n} təsdiq edib.",
    "Toplantıda {role} {n} çıxış edərək məsələni izah edib.",
    "Məlumatı {role} {n} mətbuata təqdim edib.",
]
SIGNATURE_TITLES = ["Direktor", "Baş mühasib", "Komissiyanın sədri", "Məsul katib", "Şöbə müdiri", "Rəis"]
INITIAL_SENTENCES = [
    "{n} müsabiqənin qalibi elan edilib.", "{n} iclasda iştirak edib və təklifini bildirib.",
    "{n} bu barədə yazılı izahat verib.", "{n} yeni vəzifəyə təyin olunub.",   # D-40a (finding 6)
    "{n} sənədləri təhvil verib.", "{n} ərizə ilə müraciət edib.",
]
# an organisation named in quotes, then the person right after it
ORG_SENTENCES = ["«{org}» MMC-ni {n} təmsil edir.", "«{org}» ASC-ni {n} idarə edir.",
                 "«{org}» MMC-ni {n} təmsil edərək iclasda iştirak edib."]
ORG_NAMES = ["Mərkəzi Anbar", "Yeni Üfüq", "Şimal Qapısı", "Birlik Servis", "Ümumi Tikinti",
             "Böyük Körpü", "Təmiz Su", "Parlaq Gələcək", "Etibarlı Yol", "Cənub Ticarət"]

# the look-alike kinds a clerical value clause may carry instead (not the
# tracking code: a `kart` clause would make it a card)
CLERICAL_KINDS = ("fin_8_9_chars", "fin_with_hyphen", "iban_truncated", "card_wrong_length",
                  "email_double_at", "email_localhost", "email_no_at", "id_card_too_short",
                  "id_card_hyphen", "id_card_too_long", "licence_too_short", "licence_hyphen",
                  "passport_wrong_length", "voen_wrong_length")

# D-34 (D-33f, `villages`): a village name before `kənd` with the suffix on
# `kənd` (the span is the name; Run B masked only the suffix), and the name
# itself suffixed. Controls in the same document: a sentence-initial word
# describing villages, `bağ evi`, a kinship noun with a possessive.
VILLAGE_KEND = ["{v} kəndinin sakinləri yeni yolun açılışında iştirak ediblər.",
                "{v} kəndindən olan fermerlər yarmarkaya qatılıb.",
                "Həkim briqadası {v} kəndinə göndərilib.", "{v} kəndində yeni məktəb binası tikilir.",
                "Avtobus {v} kəndindən səhər tezdən yola düşür.",
                "{v} kəndinin bələdiyyəsi müraciəti qəbul edib.",
                "Yarışda {v} kəndinin komandası qalib gəlib.", "Su xətti {v} kəndinə qədər çəkilib."]
VILLAGE_CASES = ("abl", "dat", "loc", "gen")
VILLAGE_CONTROLS = ["<<Dağ>> kəndlərində qışda yollar tez-tez bağlanır.",
                    "<<Ucqar>> kəndlərə səyyar tibb məntəqəsi göndərilib.",
                    "<<Qonşu>> kənddə bazar həftədə bir dəfə qurulur.",
                    "<<Sərhədyanı>> kəndlərin məktəbləri təmir olunub.",
                    "<<Dağətəyi>> kəndlərdə su təchizatı yaxşılaşdırılıb.",
                    "<<Bağ evi>> şəhərdən bir saatlıq məsafədə yerləşir.",
                    "<<Bağ evində>> təmir işləri başa çatıb.",
                    "<<Kiçik>> kəndlərdə internet bağlantısı zəifdir.",
                    "<<Talışdilli>> kəndlərdə folklor nümunələri toplanıb.",
                    "<<Ləzgidilli>> məktəblər üçün yeni dərsliklər çap olunub."]
KINSHIP_CONTROLS = ["<<Xalam>> bu həftə kənddən gəlib.", "<<Bibim>> bağ evində yaşayır.",
                    "<<Əmim>> kənddəki evi təmir etdirib.", "<<Dayım>> sabah rayona qayıdacaq.",
                    "<<Nənəm>> kənd həyatını çox sevir.", "<<Babam>> hər yay bağda işləyir.",
                    "<<Bacım>> kənd məktəbində müəllimdir.",
                    "<<Qardaşım>> fermer təsərrüfatında çalışır."]

# D-34f: a public key, after an introducing sentence or flattened into a log
# line. No PII, no digits.
PUBLIC_INTROS = ["Serverə əlavə edilən açıq açar:", "Tərəfdaşın göndərdiyi açıq açar belədir:",
                 "Sertifikatın açıq açarı:", "İmzanı yoxlamaq üçün istifadə olunan açıq açar:",
                 "Konfiqurasiyaya əlavə olunan açıq açar aşağıdadır:",
                 "Müştəri öz açıq açarını yazışmada paylaşıb:"]
PUBLIC_AFTER = ["Açıq açarı paylaşmaq təhlükəsizdir.", "Şəxsi açar isə yalnız serverdə saxlanılır.",
                "Bu açar imzanı yoxlamaq üçün istifadə olunur.", "Açar konfiqurasiyaya əlavə edildi.",
                "Açarın barmaq izi ayrıca yoxlanılıb."]
PUBLIC_SERVER_AFTER = PUBLIC_AFTER[1]
PUBLIC_VERIFY_INTRO, PUBLIC_VERIFY_AFTER = PUBLIC_INTROS[3], PUBLIC_AFTER[2]
# D-34 (D-33f, `pem` b): a key flattened into one log line, `key=value`
# between other `key=value` fields. Field values carry no digits.
LOG_KEY_FIELDS = {"private": ("private_key", "ssh_key", "tls_key", "key"),
                  "public": ("public_key", "pubkey", "ssh_pub")}
LOG_OTHER_FIELDS = (("svc", ("gateway", "deploy", "billing", "auth")),
                    ("env", ("prod", "staging", "test")),
                    ("user", ("deploy", "admin", "ci")),
                    ("host", ("app-srv", "db-main", "edge")))


# D-51h: the look-alike kinds of the v4 families (frames_v4.py holds the
# sentences). A 2-3-digit number after each ID/token word, by label:
SHORT_KIND = {"AZ_VOEN": "voen_short_number", "AZ_FIN": "fin_short_number",
              "AZ_ID_CARD_NUMBER": "id_card_short_number", "ACCESS_TOKEN": "token_short_number",
              "API_KEY": "api_key_short_number"}
# a name used as a company, project or topic name, or a code, in a name slot
NAME_SLOT_KINDS = {"SURNAME": (("policy_surname_in_company", 0.55), ("code_in_name_slot", 0.30),
                               ("policy_foreign_brand", 0.15)),
                   "CITY": (("policy_city_as_project", 1.0),),
                   "STREET": (("policy_street_as_topic", 1.0),)}
IPV4_KINDS = ("ipv4_short_over_255", "ipv4_three_octets", "ipv4_placeholder",
              "ipv4_over_255_mixed")                        # D-56a (2)
# D-51d: the checksum-only kinds; none may be written any more
CHECKSUM_ONLY_KINDS = frozenset({"card_luhn_invalid", "tracking_code_15_16",
                                 "LOYALTY_CARD_LUHN_BAD", "IBAN_BAD_CHECKSUM"})


def az_capitalize(s: str) -> str:
    if not s:
        return s
    return {"i": "İ", "ı": "I"}.get(s[0], s[0].upper()) + s[1:]


def az_upper(s: str) -> str:
    """All capitals the Azerbaijani way: `i` -> `İ`, `ı` -> `I` (D-57 S2)."""
    return s.replace("i", "İ").upper()


# --------------------------------------------------------------------------- #
# Draft: text written with exact offsets
# --------------------------------------------------------------------------- #

class Draft:
    def __init__(self) -> None:
        self.parts: list[str] = []
        self.length = 0
        self.entities: list[dict] = []
        self.decoys: list[dict] = []
        self.frame_ids: list[str] = []
        self.anchor_gaps: list[int] = []
        self.decoy_kinds: list[str] = []
        self.suffixes: list[dict] = []

    @property
    def text(self) -> str:
        return "".join(self.parts)

    def add(self, s: str) -> None:
        if s:
            self.parts.append(s)
            self.length += len(s)

    def entity(self, label: str, value: str) -> None:
        self.entities.append({"start": self.length, "end": self.length + len(value),
                              "label": label, "text": value})
        self.add(value)

    def suffixed(self, label: str, word: str, stem_len: int, case: str, surface: str) -> None:
        """An inflected value (P2-4c): the span is the whole word (D-9), and
        the record declares it in `_suffixes` so the resolver and the
        Turkish-apostrophe check can trust it."""
        self.suffixes.append({"start": self.length, "end": self.length + len(word),
                              "stem_end": self.length + stem_len, "case": case,
                              "surface": surface})
        self.entity(label, word)

    def decoy(self, value: str, kind: str, resembles: str) -> None:
        self.decoys.append({"start": self.length, "end": self.length + len(value),
                            "kind": kind, "resembles": resembles})
        self.decoy_kinds.append(kind)
        self.add(value)


def _append(draft: Draft, other: Draft) -> None:
    """Write `other` (composed on its own) at the end of `draft`, its spans
    shifted to their new offsets."""
    base = draft.length
    shift = lambda x: {**x, "start": x["start"] + base, "end": x["end"] + base}   # noqa: E731
    draft.entities += [shift(e) for e in other.entities]
    draft.decoys += [shift(x) for x in other.decoys]
    draft.suffixes += [{**shift(x), "stem_end": x["stem_end"] + base} for x in other.suffixes]
    draft.decoy_kinds += other.decoy_kinds
    draft.frame_ids += other.frame_ids
    draft.anchor_gaps += other.anchor_gaps
    draft.add(other.text)


def write(draft: Draft, template: str, writers: dict[str, Callable[[Draft], None]],
          capitalize: bool = True) -> None:
    """Write `template`, calling writers[name] at each `{name}` placeholder.

    A sentence-initial literal or anchor is capitalised (Azerbaijani i -> İ);
    a value at the start is written exactly as it is. A full stop right after
    a value that already ends in one (`küç.`) is not doubled. A phrase written
    inside a sentence passes capitalize=False.
    """
    pos = 0
    for m in re.finditer(r"\{(\w+)\}", template):
        literal = template[pos:m.start()]
        if pos == 0 and literal and capitalize:
            literal = az_capitalize(literal)
        draft.add(literal)
        writers[m.group(1)](draft)
        pos = m.end()
    tail = template[pos:]
    if pos == 0 and capitalize:
        tail = az_capitalize(tail)
    if tail.startswith(".") and draft.text.endswith("."):
        tail = tail[1:]
    draft.add(tail)


# --------------------------------------------------------------------------- #
# The builder
# --------------------------------------------------------------------------- #

class BuildError(RuntimeError):
    pass


class TargetedBuilder:
    def __init__(self, seed: int, n_docs: int, quotas: dict | None = None,
                 frames_module=None, homographs_module=None) -> None:
        self.q = quotas or Q.load()
        self.frames = FrameLibrary(frames_module or load_frames_module())
        self.homographs = HomographLibrary(homographs_module or load_homographs_module())
        self.homograph_counts: collections.Counter = collections.Counter()
        self.rng = random.Random(seed)
        self.values = ValueFactory(random.Random(seed ^ 0x7A6E), ValuePool(state_path=None),
                                   foreign_name_rate=self.q["names"]["foreign_name_rate"],
                                   name_variant_rate=self.q["names"].get("variant_rate", 0.10))
        self.value_rng = random.Random(seed ^ 0xDEC0)
        self.seed = seed
        self.n_docs = n_docs
        self.cap = max(1, int(n_docs * self.q["max_frame_share"]))
        self.frame_docs: collections.Counter = collections.Counter()
        self.family_counts: collections.Counter = collections.Counter()
        self.sub_counts: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
        self.kind_counts: collections.Counter = collections.Counter()
        self.rejections: collections.Counter = collections.Counter()
        self.texts: set[str] = set()
        self.written = 0
        # P2-4b entity casing noise: accepted entities so far, and how many
        # of them were noised; the share is held at the quota, below the cap
        self.entity_total = 0
        self.case_noised = 0
        self.noise_rng = random.Random(seed ^ 0xCA5E)
        # P2-4c: accepted inflected mentions per case, steering the next pick
        self.case_counts: collections.Counter = collections.Counter()
        # and accepted name/surname/city/street mentions, steering how many
        # inflected sentences the next `inflected` document writes
        self.inflectable_total = 0
        kinds = {k.kind: k for k in active_decoy_kinds()}
        self.kinds = kinds
        grouped = {kk for ks in DECOY_GROUPS.values() for kk in ks}
        self.groups = {g: [kinds[k] for k in ks if k in kinds] for g, ks in DECOY_GROUPS.items()}
        self.groups["other"] = [k for name, k in kinds.items()
                                if name not in grouped and name not in PEM_DECOY_KINDS]
        self.groups["noun"] = [kinds[k] for k in NOUN_KINDS if k in kinds]
        self.groups["cvv"] = [kinds[k] for k in CVV_KINDS if k in kinds]
        self.villages = frozenset(n for n, k in zip(SETTLEMENTS, SETTLEMENT_KINDS) if k == "settlement")

    # -- choosing ---------------------------------------------------------
    def _deficit(self, weights: dict[str, float], counts: collections.Counter) -> str:
        """The option furthest below its target share (weights normalised)."""
        # D-49: math.fsum, not sum(): Python 3.12 made sum() of floats
        # compensated, so 3.11 and 3.12+ gave totals a bit apart (99.2 vs
        # 99.19999999999996 for the case weights) and a near-tie here went the
        # other way -- the Mac (3.11) and Windows (3.13) builds parted at
        # document 917. fsum is correctly rounded on every version.
        norm = math.fsum(weights.values())
        total = sum(counts.values())
        return max(sorted(weights),
                   key=lambda k: weights[k] / norm - (counts[k] / total if total else 0))

    def _pick_frame(self, candidates: list, used: set[str], fid=lambda f: f.fid):
        ok = [c for c in candidates if self.frame_docs[fid(c)] < self.cap or fid(c) in used]
        if not ok:
            raise BuildError(f"every candidate frame is at the 3% cap "
                             f"({len(candidates)} candidates, cap {self.cap} documents)")
        return self.rng.choice(ok)

    def _slot_kind(self, label: str, kinds: list) -> object:
        """The look-alike kind for a `label: value` line or a cell. CVV kinds
        are drawn at random there (D-41a): the `cvv` pairs use the 5-digit
        kinds most, so least-used balancing kept them out of these slots."""
        if label == "CARD_SECURITY_CODE":
            return self.rng.choice(kinds)
        return self._least_used_kind(kinds)

    def _least_used_kind(self, kinds: list) -> object:
        """The kind furthest behind, counts divided by `kind_weights` (D-52d:
        the protected C4 kinds weigh more, so new kinds can't dilute them;
        weight 1 by default, which is the plain least-used choice)."""
        w = self.q.get("kind_weights", {})
        # D-57 S5: a label's factor on all of its kinds (the ID, FIN, VÖEN,
        # passport, CVV and licence look-alikes that the new kinds diluted)
        lw = self.q.get("label_kind_weights", {})
        score = {k.kind: self.kind_counts[k.kind] / (float(w.get(k.kind, 1.0)) * float(lw.get(k.resembles, 1.0)))
                 for k in kinds}
        low = min(score.values())
        return self.rng.choice([k for k in kinds if score[k.kind] == low])

    # -- values -----------------------------------------------------------
    def _mint(self, label: str, ctx: str, female: bool | None = None,
              origin: str | None = None) -> str:
        V = self.values
        b = self.q["boundary"]
        if label == "DATE":
            return V.date_styled("az", self.rng.choice(V.DATE_STYLES),
                                 day31_rate=self.q["fix_round"].get("date_day31_rate", 0.0))
        # fix round (D-30b): dashed CVVs and any-AZ#### ZIPs as real values.
        # FINs keep their natural share of all-letter values (D-33b).
        f = self.q["fix_round"]
        if label == "CARD_SECURITY_CODE" and self.rng.random() < f["cvv_dashed_rate"]:
            return V.card_security_code_dashed()
        if label == "ZIPCODE" and self.rng.random() < f["zip_any_rate"]:
            return V.zipcode_any_az()
        if label == "PAYMENT_CARD_NUMBER" and (
                ctx == "prose" or self.rng.random() < f["card_grouped_rate"]):
            return V.payment_card_grouped()
        # D-34e: the account part of an AZ IBAN may hold letters (AZ2!n4!a20!c)
        if label == "IBAN" and self.rng.random() < f["iban_letters_rate"]:
            return V.iban_az_alnum(grouped=self.rng.random() < b["iban_grouped_rate"])
        if ctx == "prose" and label == "IBAN":
            # v4.2 fix list: IBAN boundaries (too narrow / split on shadow-dev)
            if self.rng.random() < b.get("iban_irregular_rate", 0.0):
                return V.iban_az_irregular()
            return (V.iban_az_grouped() if self.rng.random() < b["iban_grouped_rate"]
                    else V.iban_az_compact())
        if ctx != "container" and label == "TELEPHONENUM" \
                and self.rng.random() < b["phone_grouped_rate"]:
            return V.telephone_grouped()
        # v4.2 fix list: streets named after a town (STREET read as CITY)
        if label == "STREET" and self.rng.random() < f.get("street_town_rate", 0.0):
            return V.street_town()
        if label == "URL" and self.rng.random() < b["url_query_rate"]:
            return V.url_query()
        # v4.1 (#91 item 2): real IPv4 with one-digit octets
        if label == "IPV4_ADDRESS" and self.rng.random() < self.q["ipv4"]["one_digit_rate"]:
            return V.ipv4_one_digit()
        if ctx == "pem_long" and label == "PRIVATE_KEY":
            return V.private_key_varied(min_chars=b["pem_long_min_chars"],
                                        max_chars=b["pem_long_max_chars"])
        if ctx != "container" and label == "PRIVATE_KEY":
            # D-51h: short keys are Ed25519 more often, so short private keys
            # outnumber the Ed25519 public-key look-alikes (>= 3 to 1)
            if self.rng.random() < b["ed25519_private_rate"]:
                return V.private_key_ed25519()
            return V.private_key_varied(max_chars=b["pem_max_chars"])
        if (ctx == "container" and label == "EMAIL"
                and self.rng.random() < self.q["structured"]["synthetic_email_rate"]):
            return V.email_synthetic()          # v4.1 (#91 item 9)
        if (ctx == "container" and label == "EMAIL"
                and self.rng.random() < self.q["structured"]["reserved_email_rate"]):
            return V.email_reserved("az")
        if label in ("GIVENNAME", "SURNAME") and (female is not None or origin is not None):
            return V.make(label, "az", female=female, origin=origin)
        return V.make(label, "az")

    def _container_row(self, columns: list, fmt: str | None = None) -> list:
        """One record's cells. A row with both a GIVENNAME and a SURNAME
        column is one person: one gender and one name origin (P2-15), so a
        record never reads `Sergey | Məmmədova`."""
        person = {}
        if "GIVENNAME" in columns and "SURNAME" in columns:
            person = {"female": self.rng.random() < 0.5,
                      "origin": self.values.name_origin("az")}

        def cell(lab: str) -> str:
            if lab in ("GIVENNAME", "SURNAME"):
                return self._mint(lab, "container", **person)
            # D-34 (D-33f): a grouped phone after `key: ` (Run B split it
            # after the operator code); cells had only ungrouped ones
            if (lab == "TELEPHONENUM" and fmt in KEYED_PHONE_FORMATS
                    and self.rng.random() < self.q["boundary"]["keyed_phone_grouped_rate"]):
                return self.values.telephone_grouped()
            return self._mint(lab, "container")

        return [("entity", lab, cell(lab)) for lab in columns]

    # -- inflected values (P2-4c) -----------------------------------------
    def _pick_case(self, local: collections.Counter) -> tuple[str, str]:
        """The case furthest below its target share, and a label that takes
        it and has sentences for it."""
        sq = self.q["suffix"]
        weights = {c: float(w) for c, w in Q._weights(sq["case_weights"]).items()}
        case = self._deficit(weights, self.case_counts + local)
        labels = [lab for lab in sorted(SFX.APPLIES) if case in SFX.APPLIES[lab]
                  and SUFFIX_FRAMES[KIND[lab]].get(case)]
        lw = sq["label_weights"]
        return case, self.rng.choices(labels, weights=[lw[lab] for lab in labels])[0]

    def _mint_inflectable(self, label: str, case: str, ctx: str = "prose",
                          female: bool | None = None, village: bool = False) -> tuple[str, str]:
        """A value that takes `case` (not an abbreviated street), with its
        inflected form. A name minted in Cyrillic is written in its English
        spelling (`Mammadovun`), so inflected names keep the variant rate.

        The family plural is built on the base surname, `Əkbərovlar`, never
        on the feminine `Əkbərovalar` (found reading 50 documents), and so is
        the family `-gil`: `Məmmədovgil` names the family, `Məmmədovagil` only
        one woman's household (P4-2 round 1: 16 of 25 surname `-gil` forms
        in a 5,000-document build were feminine)."""
        if label == "SURNAME" and case.startswith(("pl", "gil")):
            female = False
        for _ in range(20):
            value = self.values.latin_spelling(self._mint_village() if village
                                               else self._mint(label, ctx, female))
            try:
                return value, self._inflect(value, case, label)
            except SFX.NotInflectable:
                continue
        raise BuildError(f"no {label} value takes {case} in 20 mints")

    def _inflect(self, value: str, case: str, label: str) -> str:
        """The suffix follows the letters written: `Realada` takes `-dan`, and
        `Sarigul` `-u`, not the harmony of the Azerbaijani spelling it
        transliterates (P4-2 round 2: 12 of 54 forms had `Realadən`,
        `Sarigulü`). A name whose Azerbaijani form softens before `case`
        (`Cicek` for `Çiçək`) is refused: its written stem would have to
        change too."""
        canonical = self.values.name_variants.get(value, (value, ""))[0]
        if canonical != value and not SFX.inflect(canonical, case, label).startswith(canonical):
            raise SFX.NotInflectable(f"{canonical!r} softens before {case}")
        return SFX.inflect(value, case, label)

    def _surface(self, label: str, value: str, inflected: str, case: str) -> tuple[str, int, str]:
        """(written word, stem length, surface kind): about 10% of inflected
        mentions are written as Turkish-style `Bakı'da` or ASCII-folded
        `Bakida` (P2-4c item 2), and about 5% with the suffix misspelt as
        people write it, `Bakıdə`, `Gəncəin`, `Bakıdda`, `Leylaynan`: still
        the name, labelled whole (noisy grammar, 2026-10-05)."""
        sq = self.q["suffix"]
        r = self.rng.random()
        kind = "plain"
        if r < sq["apostrophe_rate"] and case in SFX.APOSTROPHE_CASES and label != "STREET":
            kind = "apostrophe"
        elif r < sq["apostrophe_rate"] + sq["folded_rate"]:
            kind = "folded"
        elif r < sq["apostrophe_rate"] + sq["folded_rate"] + sq["noisy_rate"]:
            forms = noisy_forms(value, case, label)
            if forms:
                word = forms[self.rng.choice(sorted(forms))]
                return word, SFX.split(inflected, value), "noisy"
        stem = len(value) if kind == "apostrophe" else SFX.split(inflected, value)
        return SFX.surface(value, inflected, kind), stem, kind

    def _suffix_sentence(self, d: Draft, label: str, case: str, used: set[str],
                         village: bool = False) -> None:
        kind = KIND[label]
        items = [(f"S.{kind}.{case}.{i}", t) for i, t in enumerate(SUFFIX_FRAMES[kind][case])]
        fid, template = self._pick_frame(items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        value, inflected = self._mint_inflectable(label, case, village=village)
        word, stem_len, surface = self._surface(label, value, inflected, case)
        write(d, template, {"v": lambda dd: dd.suffixed(label, word, stem_len, case, surface)})

    def _gender(self, template: str) -> bool | None:
        if " xanım" in template:
            return True
        if " bəy" in template:
            return False
        return None

    # -- sentences --------------------------------------------------------
    def _neutral(self, d: Draft, register: str, used: set[str]) -> None:
        """A filler sentence this document has not used yet: the same
        sentence twice in one short document reads like a template (found
        reading 50 documents: 3.8% of documents repeated one)."""
        every = [x for pool in self.frames.neutral.values() for x in pool]
        written = set(d.parts)
        fresh = lambda pool: [x for x in pool if x[0] not in used and x[1] not in written]  # noqa: E731
        try:
            fid, sentence = self._pick_frame(fresh(self.frames.neutral[register]), used,
                                             fid=lambda x: x[0])
        except (BuildError, IndexError):        # this register is used up or at the cap
            fid, sentence = self._pick_frame(fresh(every) or every, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        d.add(sentence)

    def _sep(self, d: Draft) -> None:
        newline = self.rng.random() < 0.25
        if d.text.endswith("\n"):          # D-56a (1): a line that ended open
            return
        d.add("\n" if newline else " ")

    def _pem_sentence(self, d: Draft, used: set[str], spec: dict, key: str | None = None) -> None:
        """A multi-line key after an introducing sentence, or one pasted onto
        a single line; then a line break, `;`, a space or a closing quote."""
        key = key or self._mint("PRIVATE_KEY", "prose")
        lines = key.split("\n")
        width = max((len(x) for x in lines[1:-1]), default=0)
        b = self.q["boundary"]
        flat = len(lines) > 1 and self.rng.random() < b["pem_flat_rate"]
        # D-34 (D-33f `pem` b): a flattened key as one `key=value` field of a log line
        logline = flat and self.rng.random() < b["pem_logline_rate"]
        value = " ".join(lines) if flat else key
        after = "field" if logline else self.rng.choice(["newline", "semicolon", "space", "quote"])
        pem = {"lines": len(lines), "width": width, "chars": len(key),
               "layout": "logline" if logline else "flat" if flat else "block", "after": after}
        spec.setdefault("pem", []).append(pem)
        pick = lambda prefix, pool: self._pick_text(d, used, f"B.pem.{prefix}", pool)  # noqa: E731
        if logline:
            d.add(self._pick_text(d, used, "FMT.intro.log", FMT.INTROS["log"]) + "\n")
            self._key_log_line(d, "private", lambda dd: dd.entity("PRIVATE_KEY", value))
            d.add("\n" + pick("after", PEM_AFTER))
            return

        # only the chosen ending draws an after-sentence: building all three
        # used up PEM_AFTER in a document with several keys (D-51h short_keys)
        tail = ('".' if after == "quote" else
                {"newline": "\n", "semicolon": "; ", "space": " "}[after] + pick("after", PEM_AFTER))
        if flat:
            template = pick("inline", PEM_INLINE)
            if after == "quote":
                template = template.replace("{v}", '"{v}')
            write(d, template, {"v": lambda dd: dd.entity("PRIVATE_KEY", value),
                                "t": lambda dd: dd.add(tail)})
        else:
            d.add(pick("intro", PEM_INTROS))
            d.add(' "' if after == "quote" else "\n")
            d.entity("PRIVATE_KEY", value)
            d.add(tail)

    def _pick_text(self, d: Draft, used: set[str], prefix: str, pool: list[str],
                   avoid: tuple[str, ...] = ()) -> str:
        """One fixed sentence from `pool` under the 3% cap, recorded as a frame:
        not one this document has already written (D-36b, the team: the same
        control sentence twice in 3 of 5,000 documents), nor one in `avoid`."""
        items = [(f"{prefix}.{i}", t) for i, t in enumerate(pool) if t not in avoid]
        fresh = [x for x in items if x[0] not in used]
        fid, t = self._pick_frame(fresh or items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        return t

    def _key_log_line(self, d: Draft, which: str, fill: Callable[[Draft], None]) -> None:
        """`LEVEL message: f=v [f=v] key=<flattened key> f=v [f=v]`: the key
        between other fields, the next field right after it (D-33f `pem` b:
        Run B masked the `env=` after the key)."""
        others = self.rng.sample(LOG_OTHER_FIELDS, 3)
        cut = self.rng.randint(1, 2)
        field = lambda kv: f"{kv[0]}={self.rng.choice(kv[1])}"   # noqa: E731
        d.add(f"{self.rng.choice(FMT.LOG_LEVELS)} {self.rng.choice(FMT.LOG_MESSAGES)}: "
              + " ".join(field(kv) for kv in others[:cut])
              + f" {self.rng.choice(LOG_KEY_FIELDS[which])}=")
        fill(d)
        d.add(" " + " ".join(field(kv) for kv in others[cut:]))

    def _public_key_sentence(self, d: Draft, used: set[str], spec: dict,
                             key: str | None = None) -> None:
        """D-34f: a public key, a look-alike of PRIVATE_KEY, as a block after
        an introducing sentence or flattened into a log line. `key`: a block
        drawn by the caller (D-51h: an Ed25519 one beside Ed25519 private
        keys)."""
        kind = self.kinds["public_key_block"]
        key = key or self._decoy_value(kind)
        spec.setdefault("public_keys", []).append("ed25519" if ED25519_PUBLIC_LEAD in key else "other")
        logline = self.rng.random() < self.q["boundary"]["public_logline_rate"]
        spec.setdefault("public_key", []).append("logline" if logline else "block")
        avoid = []
        if logline:
            flat = " ".join(key.split("\n"))
            d.add(self._pick_text(d, used, "FMT.intro.log", FMT.INTROS["log"]) + "\n")
            self._key_log_line(d, "public", lambda dd: dd.decoy(flat, kind.kind, kind.resembles))
        else:
            intro = self._pick_text(d, used, "B.public.intro", PUBLIC_INTROS)
            d.add(intro + "\n")
            d.decoy(key, kind.kind, kind.resembles)
            if intro == PUBLIC_VERIFY_INTRO:          # D-36b: not said twice
                avoid.append(PUBLIC_VERIFY_AFTER)
        # D-36b: "the private key is kept only on the server" does
        # not belong beside a private key written out in the same document
        if spec.get("with_private"):
            avoid.append(PUBLIC_SERVER_AFTER)
        d.add("\n" + self._pick_text(d, used, "B.public.after", PUBLIC_AFTER, avoid=tuple(avoid)))

    def _prose_sentence(self, d: Draft, label: str, used: set[str], spec: dict | None = None) -> None:
        b = self.q["boundary"]
        if label == "PRIVATE_KEY" and spec is not None and self.rng.random() < b["pem_block_rate"]:
            self._pem_sentence(d, used, spec)
            return
        takes = SFX.APPLIES.get(label, ())
        # a frame already at the 3% cap is not a candidate: when it was the
        # label's only far frame, `_pick_frame` raised BuildError instead of
        # falling back to the label's other frames or a generic one (P4-2
        # round 2: seed 3 of the C1 fixture, 1 in 12)
        own = [f for f in self.frames.by_label.get(label) or [] if f.case is None or f.case in takes]
        own = [f for f in own if self.frame_docs[f.fid] < self.cap or f.fid in used]
        # RC4: the anchor a few words away, not only right beside the value
        far = [f for f in own if f.gap is not None and 2 <= f.gap <= 6]
        # D-30b: a real FIN right after the bare word FİN. Run B's data had
        # more look-alikes than real FINs there, and the model found 30 of
        # the benchmark's 122 (AZ_FIN has no frames of its own, and most
        # generic frames put the anchor a few words away)
        fin_adjacent = (label == "AZ_FIN"
                        and self.rng.random() < self.q["fix_round"]["fin_right_after_rate"])
        if fin_adjacent:
            frame = self._pick_frame([f for f in self.frames.pairable if f.case is None
                                      and (self.frame_docs[f.fid] < self.cap or f.fid in used)],
                                     used)
        elif far and self.rng.random() < self.q["prose"]["distance_rate"]:
            frame = self._pick_frame(far, used)
        elif own and self.rng.random() < self.q["prose"]["label_frames_rate"]:
            frame = self._pick_frame(own, used)
        else:
            frame = self._pick_frame([f for f in self.frames.generic
                                      if f.case is None or f.case in takes], used)
        used.add(frame.fid)
        d.frame_ids.append(frame.fid)
        anchor = self.rng.choice(("FİN", "FIN") if fin_adjacent
                                 else self.frames.anchor_forms(label))
        if frame.folded:
            anchor = fold_diacritics(anchor)
        female = self._gender(frame.text) if label == "GIVENNAME" else None
        if frame.gap is not None:
            d.anchor_gaps.append(frame.gap)
        text = frame.text
        if frame.case is not None:
            # a C1 `{v:CASE}` slot: the value inflected for that case (P2-4c)
            value, inflected = self._mint_inflectable(label, frame.case, female=female)
            word, stem_len, surface = self._surface(label, value, inflected, frame.case)
            text = _SLOT.sub(lambda m: "{v}" if m.group(0) != "{a}" else "{a}", text)
            fill = lambda dd: dd.suffixed(label, word, stem_len, frame.case, surface)  # noqa: E731
        else:
            value = self._mint(label, "prose", female)
            fill = lambda dd: dd.entity(label, value)  # noqa: E731
            # RC5: the value touching a bracket or quote, not only spaces
            if (spec is not None and not text.startswith("{v}") and "{v}" in text
                    and "\n" not in value and self.rng.random() < b["touch_rate"]):
                o, c = self.rng.choice(TOUCH_WRAPPERS)
                text = text.replace("{v}", f"{o}{{v}}{c}", 1)
                spec.setdefault("touch", []).append(o + c)
        write(d, text, {"a": lambda dd: dd.add(az_capitalize(anchor)
                                               if text.startswith("{a}") else anchor),
                        "v": fill})

    def _phrase_in_generic(self, d: Draft, phrase: str, fill: Callable[[Draft], None],
                           used: set[str], frame=None) -> object:
        frame = frame or self._pick_frame(self.frames.pairable, used)
        used.add(frame.fid)
        d.frame_ids.append(frame.fid)
        if frame.folded:
            phrase = fold_diacritics(phrase)
        write(d, frame.text.replace("{a} {v}", phrase, 1), {"v": fill})
        return frame

    def _generic_phrase(self, anchors) -> str:
        """An anchor phrase that reads well inside a generic frame. A value-first
        age phrase does not ("... profilində 34 yaşında göstərilib")."""
        fits = [a for a in anchors if not a.startswith("{v} yaş")]
        return self.rng.choice(fits or list(anchors))

    def _policy_index(self, kind: str, used: set[str]) -> int:
        """A template index whose decoy AND valid sentences are both under the cap."""
        n = len(POLICY_PAIRS[kind][1])
        items = [(f"P.{kind}.{i}", i) for i in range(n)
                 if self.frame_docs[f"P.{kind}.valid.{i}"] < self.cap
                 or f"P.{kind}.valid.{i}" in used]
        return self._pick_frame(items, used, fid=lambda x: x[0])[1]

    def _decoy_value(self, kind) -> str:
        return make_decoy(kind, self.value_rng)

    def _decoy_sentence(self, d: Draft, kind, used: set[str], value: str | None = None,
                        idx: int | None = None, frame=None) -> object:
        """One sentence carrying a decoy of `kind`, in the form its group uses."""
        if kind.kind in PEM_DECOY_KINDS:
            self._public_key_sentence(d, used, {})
            return None
        value = value if value is not None else self._decoy_value(kind)
        fill = lambda dd: dd.decoy(value, kind.kind, kind.resembles)      # noqa: E731
        if kind.kind in DECOY_GROUPS["sentence_initial"]:
            pool = SI_GENITIVE if kind.kind.endswith("genitive") else SI_LOCATIVE
            items = [(f"P.si.{kind.kind}.{i}", t) for i, t in enumerate(pool)]
            fid, t = self._pick_frame(items, used, fid=lambda x: x[0])
            used.add(fid)
            d.frame_ids.append(fid)
            write(d, t, {"v": fill})
            return None
        if kind.kind in POLICY_PAIRS:
            _label, decoys, _valid = POLICY_PAIRS[kind.kind]
            i = idx if idx is not None else self._policy_index(kind.kind, used)
            fid = f"P.{kind.kind}.{i}"
            used.add(fid)
            d.frame_ids.append(fid)
            write(d, decoys[i], {"v": fill})
            return i
        return self._phrase_in_generic(d, self._generic_phrase(kind.anchors), fill, used, frame)

    # -- families ---------------------------------------------------------
    def _register(self) -> str:
        return self.rng.choice(sorted(self.frames.neutral))

    def _family_prose(self, d: Draft, used: set[str], spec: dict) -> None:
        reg = spec["register"]
        weights = {lab: float(self.q["prose"]["label_weights"].get(lab, 1.0))
                   for lab in ENTITY_TYPES}
        n = 1 if self.rng.random() < self.q["prose"]["single_entity_rate"] else 2
        labels: list[str] = []
        while len(labels) < n:
            lab = self.rng.choices(sorted(weights), weights=[weights[k] for k in sorted(weights)])[0]
            if lab not in labels:
                labels.append(lab)
        before = self.rng.randint(0, 1)
        for _ in range(before):
            self._neutral(d, reg, used)
            self._sep(d)
        for i, lab in enumerate(labels):
            if i:
                self._sep(d)
            self._prose_sentence(d, lab, used, spec)
        for _ in range(self.rng.randint(max(0, self.q["neutral"]["min"] - before),
                                        max(0, self.q["neutral"]["max"] - before - 1))):
            self._sep(d)
            self._neutral(d, reg, used)
        if spec.get("pem"):
            self._top_up(d, reg, used)
        spec["labels"] = labels

    def _top_up(self, d: Draft, reg: str, used: set[str], technical: bool = True) -> None:
        """More NEUTRAL sentences until the document meets its length band's
        carrier-word and PII-density thresholds (the quality gate, unchanged):
        a long key needs prose around it. Bounded; past the bound the gate
        rejects the document and it is rebuilt. Technical-register filler:
        pleasantries after a leaked key read wrong. D-39b: a name list takes
        the document's own register instead (`technical=False`)."""
        if technical and "technical" in self.frames.neutral:
            reg = "technical"
        for _ in range(self.q["boundary"]["pem_topup_max"]):
            text = d.text
            band = next((b[0] for b in LENGTH_BANDS if b[2] <= len(text) <= b[3]), None)
            if (carrier_word_count(text, d.entities) >= MIN_CARRIER_WORDS.get(band, 0)
                    and pii_density(text, d.entities) <= MAX_PII_DENSITY.get(band, 1.0)):
                return
            self._sep(d)
            self._neutral(d, reg, used)

    def _family_pem_long(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-27: a real-length RSA key (1,500+ characters) in a long technical
        document, a runbook, deployment note or ticket. The quality gate's
        PII-density cap for the longest band (`extreme`, 4,200-9,000
        characters) is 25% and is not changed, so the document is about 5
        times the key: the key is minted first and the carrier text fills a
        character budget around it (long_docs.TOPICS). Composed in a scratch
        draft and kept only if it lands inside the band with room to spare:
        a document over 9,000 characters would have no band, and the gate's
        default cap, a loophole this family must not use."""
        b = self.q["boundary"]
        top = max(x[3] for x in LENGTH_BANDS if x[0] == "extreme")
        key = self._mint("PRIVATE_KEY", "pem_long")
        lo = len(key) / b["pem_long_density_hi"]
        hi = min(b["pem_long_max_doc"], len(key) / b["pem_long_density_lo"])
        for _ in range(12):
            d2, used2, spec2 = Draft(), set(used), {k: v for k, v in spec.items() if k != "pem"}
            self._pem_long_text(d2, used2, spec2, key, self.rng.uniform(lo, hi))
            n = len(d2.text)
            if lo <= n <= min(hi, top - 50):
                d.__dict__.update(d2.__dict__)
                used |= used2
                spec.update(spec2)
                return
        raise BuildError("pem_long: no draft landed in the extreme band")

    def _pem_long_text(self, d: Draft, used: set[str], spec: dict, key: str, total: float) -> None:
        budget = total - len(key) - 600                      # 600: title, headings, intro, closing
        kind = self.rng.choice(sorted(LD.KINDS))
        k = LD.KINDS[kind]
        spec["long_kind"] = kind
        d.add(self.rng.choice(k["titles"]) + "\n\n")
        # topics until their sentences cover the character budget; the key's
        # topic is always one, at a random place after the first
        pool = [x for x in LD.TOPICS if x != LD.KEY_TOPIC]
        self.rng.shuffle(pool)
        order, have = [], len(" ".join(LD.TOPICS[LD.KEY_TOPIC]))
        while pool and have < budget * 1.05:
            order.append(pool.pop())
            have += len(" ".join(LD.TOPICS[order[-1]]))
        order.insert(self.rng.randint(min(1, len(order)), len(order)), LD.KEY_TOPIC)
        written = 0
        for idx, topic in enumerate(order):
            sentences = list(LD.TOPICS[topic])
            self.rng.shuffle(sentences)
            d.add(k["heading"].format(h=topic) + "\n")
            first = True
            if topic == LD.KEY_TOPIC:
                for s in [sentences.pop() for _ in range(2)]:
                    d.add(("" if first else " ") + s)
                    first = False
                    written += len(s) + 1
                d.add("\n")
                self._pem_sentence(d, used, spec, key=key)
                d.add("\n")
                first = True
            while sentences and written < budget * (idx + 1) / len(order) + 400:
                s = sentences.pop()
                d.add(("" if first else " ") + s)
                first = False
                written += len(s) + 1
            d.add("\n\n")
        d.add(self.rng.choice(k["closing"]))

    def _family_decoy_pair(self, d: Draft, used: set[str], spec: dict) -> None:
        reg = spec["register"]
        group = self._deficit(Q.decoy_groups(self.q), self.sub_counts["decoy_group"])
        if group == "age":
            self._age_pair(d, used, spec)
            return
        if group == "noun":
            # the label first, kept balanced: least-used kinds overall would
            # skip the ZIP and card kinds, which structured cells use most.
            # D-57: weighted (quotas decoy_noun_labels), DATE most (M4)
            weights = Q._weights(self.q.get("decoy_noun_labels") or {k: 1.0 for k in NOUN_FRAMES})
            lab = self._deficit(weights, self.sub_counts["noun_label"])
            if lab == "DATE":
                # D-57 M4: the two near-miss kinds by turns (the global
                # least-used choice sent most turns to kinds drawn elsewhere)
                kind = self.kinds[self._deficit({k: 1.0 for k in NOUN_DATE_KINDS},
                                                self.sub_counts["noun_date_kind"])]
            else:
                kind = self._least_used_kind([k for k in self.groups["noun"] if k.resembles == lab])
        else:
            kind = self._least_used_kind(self.groups[group])
        spec.update(group=group, kind=kind.kind)
        label = kind.resembles
        if self.rng.random() < 0.5:
            self._neutral(d, reg, used)
            self._sep(d)
        if group == "building":
            self._building_pair(d, used, spec, kind)
        elif group in ("noun", "cvv"):
            # D-34g: the same before-noun sentence twice, once with the valid
            # value and once with the look-alike, in either order. D-41a: the
            # same for a CVV sentence, a real CVV beside a 5-digit look-alike
            items = ([(f"P.noun.{label}.{i}", t) for i, t in enumerate(NOUN_FRAMES[label])]
                     if group == "noun" else [(f"P.cvv.{i}", t) for i, t in enumerate(CVV_FRAMES)])
            fid, sentence = self._pick_frame(items, used, fid=lambda x: x[0])
            used.add(fid)
            d.frame_ids.append(fid)
            dvalue = self._decoy_value(kind)
            # D-57 M4: 30 or 31 February before the noun (C4's trigger), not 29
            while kind.kind == "date_feb_invalid" and re.search(r"(^|\D)29(\D|$)", dvalue):
                dvalue = self._decoy_value(kind)
            value = self._mint(label, "pair")
            while value == dvalue:
                value = self._mint(label, "pair")
            real = lambda x: x.entity(label, value)          # noqa: E731
            # D-51i: a spelled date before `tarixində` may take the official
            # `-cı il`, outside the span and harmonised by the year
            if (label == "DATE" and re.search(r"[^\W\d_]", value) and re.search(r"\d{4}$", value)
                    and self.rng.random() < self.q["fix_round"]["date_year_suffix_rate"]):
                tail = year_suffix(int(value[-4:])) + " il"
                real = lambda x: (x.entity(label, value), x.add(tail))   # noqa: E731
                spec["year_suffix"] = tail
            halves = [real, lambda x: x.decoy(dvalue, kind.kind, label)]
            if self.rng.random() < 0.5:
                halves.reverse()
            write(d, sentence, {"v": halves[0]})
            self._between(d, reg, used, bridge=True)
            write(d, sentence, {"v": halves[1]})
        else:
            # Chosen up front, so whichever half comes first the valid value
            # differs from the decoy and can reuse the decoy's anchor phrase.
            dvalue = self._decoy_value(kind)
            dphrase = self._generic_phrase(kind.anchors)
            phrases = LABEL_ANCHOR_PHRASES.get(label) or tuple(
                f"{a} {{v}}" for a in self.frames.anchor_forms(label))
            vphrase = (dphrase if dphrase in phrases and self.rng.random() < 0.7
                       else self._generic_phrase(phrases))

            def valid(dd: Draft, frame=None, idx=None):
                if group == "sentence_initial":
                    items = [(f"P.name_start.{g}.{i}", t) for g in ("f", "m", "any")
                             for i, t in enumerate(NAME_START[g])]
                    fid, t = self._pick_frame(items, used, fid=lambda x: x[0])
                    used.add(fid)
                    dd.frame_ids.append(fid)
                    v = self._mint("GIVENNAME", "pair", self._gender(t))
                    write(dd, t, {"v": lambda x: x.entity("GIVENNAME", v)})
                    return None
                if group == "policy_names":
                    lab, _decoys, valids = POLICY_PAIRS[kind.kind]
                    i = idx if idx is not None else self._policy_index(kind.kind, used)
                    fid = f"P.{kind.kind}.valid.{i}"
                    used.add(fid)
                    dd.frame_ids.append(fid)
                    # a brand's valid twin is mostly a foreign surname, so the
                    # slot, not the spelling, tells them apart
                    origin = None
                    fn = self.values.loc("az").foreign_names
                    if kind.kind == "policy_foreign_brand" and fn and fn.origins \
                            and self.rng.random() < 0.7:
                        origin = self.rng.choice(fn.origins)
                    # D-57 S3: these sentences call it a town (D-43c: never a village)
                    v = (self._town() if kind.kind == "policy_city_in_brand"
                         else self._mint(lab, "pair", origin=origin))
                    write(dd, valids[i], {"v": lambda x: x.entity(lab, v)})
                    return i
                v = self._mint(label, "pair")
                while v == dvalue:
                    v = self._mint(label, "pair")
                return self._phrase_in_generic(
                    dd, vphrase, lambda x: x.entity(label, v), used, frame)

            # D-56g: an IPv4 look-alike never shares its sentence frame with a
            # real IPv4 (#91 item 3: the twin frame cost 44 IPv4 misses); it
            # gets a look-alike sentence of its own, as in cross_anchor. Other
            # labels keep the twin design
            ipv4_own = label == "IPV4_ADDRESS"

            def decoy(dd: Draft, frame=None, idx=None):
                if ipv4_own:
                    t = self._pick_text(dd, used, "X.ipv4_lookalike", V4.IPV4_LOOKALIKE)
                    write(dd, t, {"v": lambda x: x.decoy(dvalue, kind.kind, label)})
                    return None
                if group == "other":
                    return self._phrase_in_generic(
                        dd, dphrase, lambda x: x.decoy(dvalue, kind.kind, label), used, frame)
                return self._decoy_sentence(dd, kind, used, value=dvalue, idx=idx, frame=frame)

            # the same frame (or template index) for both halves
            first, second = (valid, decoy) if self.rng.random() < 0.5 else (decoy, valid)
            shared = first(d)
            self._between(d, reg, used, bridge=group == "other")
            second(d, frame=shared if group == "other" and not ipv4_own else None,
                   idx=shared if group == "policy_names" else None)
            if ipv4_own:
                # a second real IPv4 in a sentence of its own, as _cross_ipv4
                # does: real : look-alike stays >= 2 in prose (D-52b item 3)
                other = self._mint("IPV4_ADDRESS", "prose")
                while other == dvalue:
                    other = self._mint("IPV4_ADDRESS", "prose")
                self._between(d, reg, used, bridge=True)
                self._ip_write(d, self._pick_text(d, used, "X.ipv4", V4.IPV4_BOTH), "IPV4_ADDRESS", other, spec)
        if self.rng.random() < 0.6:
            self._sep(d)
            self._neutral(d, reg, used)

    def _building_pair(self, d: Draft, used: set[str], spec: dict, kind) -> None:
        """A labelled building number beside a room, floor or office number
        (unlabelled). D-57 S4 (shadow: 26 building numbers missed after an
        ordinary word; after a label 42 -> 21 in v4.2): besides `bina {v}`,
        `ev {v}` and a street name then the number (`Nizami küçəsi 45`, the
        street labelled), and `Bina: {v}` lines beside an `Otaq: 12` line."""
        # X-BN (extra batch, D-64d): the shapes v4.2 lost. Off unless quotas `building_v43.rate` > 0, so a
        # build without it draws nothing more (v4.2 stays byte-identical)
        x = self.q.get("building_v43") or {}
        if x.get("rate", 0.0) > 0 and self.rng.random() < x["rate"]:
            self._building_v43(d, used, spec, kind, x)
            return
        bq = self.q.get("decoy_building", {})
        label = kind.resembles
        value = self._mint("BUILDINGNUM", "pair")
        dvalue = self._decoy_value(kind)
        while dvalue == value:
            dvalue = self._decoy_value(kind)
        lines = self.rng.random() < bq.get("lines_rate", 0.0)
        r = self.rng.random()
        style = ("street" if r < bq.get("street_rate", 0.0) else
                 "ev" if r < bq.get("street_rate", 0.0) + bq.get("ev_rate", 0.0) else "bina")
        # The review, D: `ev` is a dwelling -- only where people live or
        # receive parcels (BUILDING_EV_FRAMES), only beside a floor (a house has
        # no room or office number), never in `Bina:` lines
        if style == "ev" and (lines or kind.kind != "floor_number"):
            style = "bina"
        street = self._street_plain() if style == "street" else None
        spec["building_style"] = style

        def valid(dd: Draft) -> None:
            if street:
                dd.entity("STREET", street)
                dd.add(" ")
                dd.entity("BUILDINGNUM", value)
            else:
                write(dd, "ev {v}" if style == "ev" else self.rng.choice(BUILDING_VALID),
                      {"v": lambda x: x.entity("BUILDINGNUM", value)}, capitalize=False)

        if lines:
            # `Bina: 45` / `Ünvan: Nizami küçəsi 45`, then `Otaq: 12`
            spec["building_lines"] = True
            d.add(self._pick_text(d, used, "P.building.lines", V42.BUILDING_LINES_INTROS) + "\n")
            d.add("Ünvan: " if street else "Bina: ")
            if street:
                valid(d)
            else:
                d.entity("BUILDINGNUM", value)
            d.add(f"\n{V42.BUILDING_LINE_FIELDS[kind.kind]}: ")
            d.decoy(dvalue, kind.kind, label)
            d.add("\n")
            self._neutral(d, spec["register"], used)     # the lines alone are too few words
            return
        items = [(f"P.building.{i}", t) for i, t in enumerate(BUILDING_SENTENCES)
                 if style != "ev" or i in BUILDING_EV_FRAMES]
        fid, sentence = self._pick_frame(items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        # inside a sentence: no "mərtəbə: 5"-style colon phrase
        decoy_phrase = self.rng.choice([a for a in kind.anchors if ":" not in a] or list(kind.anchors))
        write(d, sentence, {
            "b": valid,
            "d": lambda dd: write(dd, decoy_phrase, {"v": lambda x: x.decoy(dvalue, kind.kind, label)},
                                  capitalize=False),
        })

    def _building_v43(self, d: Draft, used: set[str], spec: dict, kind, x: dict) -> None:
        """X-BN (frames_v43; B3 flags BUILDINGNUM 90.8 -> 81.6 on v4.2). The shapes v4.2 lost against v4.1 on
        the same probes, each beside its unlabelled look-alike: `Küçə:` then `Ev:` / `Ev nömrəsi:` lines
        (form_lines), the number, `bina N` or `ev N` before the street (number_first), `№` beside the street
        (numero), and a real address beside a count, `9 mərtəbəli`, `3 otaqlı` (count). `ev` only beside a
        floor (D-57 review, D)."""
        style = self._deficit(Q._weights(x["styles"]), self.sub_counts["building_v43"])
        self.sub_counts["building_v43"][style] += 1
        spec["building_style"] = "v43_" + style
        label = kind.resembles
        floor = kind.kind == "floor_number"
        value = self._mint("BUILDINGNUM", "pair")
        street = self._street_plain()

        def addr(dd: Draft, templates: list[str]) -> None:
            write(dd, self.rng.choice(templates), {"v": lambda z: z.entity("BUILDINGNUM", value),
                                                   "s": lambda z: z.entity("STREET", street)}, capitalize=False)

        def pick(items: list) -> str:
            fid, sentence = self._pick_frame(items, used, fid=lambda z: z[0])
            used.add(fid)
            d.frame_ids.append(fid)
            return sentence

        if style == "building_count":
            # a count of houses / buildings (`120 ev var`), unlabelled, beside the real address (#136)
            lo, hi = V43.BUILDING_COUNT_RANGE
            c = str(self.value_rng.randint(lo, hi))
            while c == value:
                c = str(self.value_rng.randint(lo, hi))
            sentence = pick([(f"P.building43.bcount.{i}", t) for i, t in enumerate(V43.BUILDING_COUNT_SENTENCES)])
            write(d, sentence, {"b": lambda dd: addr(dd, ["{s} {v}", "{s}, bina {v}", "{s}, ev {v}"]),
                                "c": lambda dd: dd.decoy(c, "building_count", "BUILDINGNUM")})
            return
        if style == "count":
            lo, hi = V43.COUNT_RANGE[kind.kind]
            c = str(self.value_rng.randint(lo, hi))
            while c == value:
                c = str(self.value_rng.randint(lo, hi))
            sentence = pick([(f"P.building43.count.{kind.kind}.{i}", t)
                             for i, t in enumerate(V43.COUNT_SENTENCES[kind.kind])])
            write(d, sentence, {"b": lambda dd: addr(dd, ["{s} {v}", "{s}, bina {v}"]),
                                "c": lambda dd: dd.decoy(c, kind.kind, label)})
            return
        dvalue = self._decoy_value(kind)
        while dvalue == value:
            dvalue = self._decoy_value(kind)
        if style == "form_lines":
            # v4.2 misses an `Ev:` / `Ev nömrəsi:` line unless a `Mərtəbə:` line follows it (probes, task log):
            # mostly no look-alike line, the look-alike then in a sentence of its own, and `Ev` keys freely
            # (a home address form has no room or office line, so the `ev` rule is kept)
            line = self.rng.random() < x.get("form_decoy_line_rate", 0.0)
            # ... and above all when the `Ev:` line ENDS the text (a sentence or a line after it, `Bina:` or
            # `14A` all fix it): form_end_rate of the forms close the document on the building number, with
            # the filler and the look-alike sentence before them
            end = not line and self.rng.random() < x.get("form_end_rate", 0.0)
            if end:
                self._neutral(d, spec["register"], used)
                self._sep(d)
                self._decoy_sentence(d, kind, used, value=dvalue)
                d.add("\n")
            if self.rng.random() < x.get("form_intro_rate", 1.0):
                d.add(self._pick_text(d, used, "P.building43.lines", V43.FORM_INTROS) + "\n")
            if self.rng.random() < x.get("form_city_rate", 0.0):
                d.add(self.rng.choice(V43.FORM_CITY_KEYS) + ": ")
                d.entity("CITY", self._mint("CITY", "prose"))
                d.add("\n")
            d.add(self.rng.choice(V43.FORM_STREET_KEYS) + ": ")
            d.entity("STREET", street)
            keys = ((V43.FORM_KEYS_EV if floor else V43.FORM_KEYS_BINA) if line
                    else V43.FORM_KEYS_EV * 2 + V43.FORM_KEYS_BINA)
            d.add("\n" + self.rng.choice(keys) + ": ")
            d.entity("BUILDINGNUM", value)
            if end:
                return
            d.add("\n")
            if line:
                d.add(f"{V42.BUILDING_LINE_FIELDS[kind.kind]}: ")
                d.decoy(dvalue, kind.kind, label)
                d.add("\n")
            self._neutral(d, spec["register"], used)     # the lines alone are too few words
            if not line:
                self._sep(d)
                self._decoy_sentence(d, kind, used, value=dvalue)
            return
        use_ev = floor and self.rng.random() < x.get("ev_rate", 0.0)
        if style == "number_first":
            templates = V43.NUMBER_FIRST_EV if use_ev else V43.NUMBER_FIRST
        else:
            templates = V43.NUMERO_EV if use_ev else V43.NUMERO
            if self.rng.random() < x.get("numero_doc_rate", 0.0):
                # the address `№` beside a document `№` (plain text, not personal data): the contrast here is
                # the document number, so no room / floor / office look-alike
                spec["building_doc_number"] = True
                sentence = pick([(f"P.building43.doc.{i}", t) for i, t in enumerate(V43.NUMERO_DOC)])
                write(d, sentence, {"b": lambda dd: addr(dd, templates),
                                    "n": lambda dd: dd.add(str(self.value_rng.randint(100, 99999)))})
                return
        sentence = pick([(f"P.building43.{i}", t) for i, t in enumerate(V43.SENTENCES)
                         if not use_ev or i in V43.EV_FRAMES])
        decoy_phrase = self.rng.choice([a for a in kind.anchors if ":" not in a] or list(kind.anchors))
        write(d, sentence, {
            "b": lambda dd: addr(dd, templates),
            "d": lambda dd: write(dd, decoy_phrase, {"v": lambda z: z.decoy(dvalue, kind.kind, label)},
                                  capitalize=False),
        })

    def _street_plain(self) -> str:
        """A street that ends in its type word and holds no digit (D-57 S4)."""
        for _ in range(60):
            s = self._mint("STREET", "prose")
            if not re.search(r"\d", s) and _STREET_TYPE_END.search(s):
                return s
        raise BuildError("no plain street in 60 draws")

    def _two_digit_age(self, lo: int, hi: int, avoid: tuple[str, ...] = ()) -> str:
        """A 2-digit age in the sentence's range (lo-hi)."""
        for _ in range(60):
            v = self.values.pool.fresh("AGE", lambda: str(self.rng.randint(lo, hi)))
            if v not in avoid:
                return v
        raise BuildError("no fresh 2-digit age in 60 draws")

    def _age_pair(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-57 S1 (shadow: AGE misses flat at 36 since v3, all 2-digit, 28
        after a lowercase word; the targeted data had very few): a bare
        2-digit age after an ordinary word, mostly with no `yaş` right after
        it (the age word sits elsewhere in the sentence), and the same frame
        with an age-shaped number that the words around it make a score, a
        queue number, months of work, a pulse or a weight (unlabelled). Often
        a second real age in a sentence of its own."""
        reg = spec["register"]
        spec.update(group="age", kind=AGE_SHAPED.kind)
        # X-AGE (extra batch, D-64d): look-alikes next to `yaş`. Off unless quotas `age_v43.rate` > 0, so a
        # build without it draws nothing more (v4.2 stays byte-identical)
        xa = self.q.get("age_v43") or {}
        if xa.get("rate", 0.0) > 0 and self.rng.random() < xa["rate"]:
            self._age_v43(d, used, spec, xa)
            return
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)
        items = [(f"P.age.{i}", i) for i in range(len(V42.AGE_PAIRS))]
        fid, i = self._pick_frame(items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        real_t, fake_t, (lo, hi), (flo, fhi) = V42.AGE_PAIRS[i]
        age = self._two_digit_age(lo, hi)
        fake = age
        while fake == age:
            fake = str(self.rng.randint(flo, fhi))
        self._pair(d, reg, used, [
            lambda dd: write(dd, real_t, {"v": lambda x: x.entity("AGE", age)}),
            lambda dd: write(dd, fake_t, {"v": lambda x: x.decoy(fake, AGE_SHAPED.kind, "AGE")})])
        if self.rng.random() < self.q.get("decoy_age", {}).get("more_rate", 0.0):
            self._sep(d)
            t = self._pick_text(d, used, "P.age_more", [s for s, _r in V42.AGE_REAL_MORE])
            lo, hi = dict(V42.AGE_REAL_MORE)[t]
            other = self._two_digit_age(lo, hi, avoid=(age, fake))
            write(d, t, {"v": lambda x: x.entity("AGE", other)})
            spec["ages"] = 2
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)

    def _age_v43(self, d: Draft, used: set[str], spec: dict, xa: dict) -> None:
        """X-AGE (frames_v43, red-team rule #136): a real age of a person with `yaş` (`Müştəri 34 yaşındadır`) and,
        in either order, a number next to `yaş` that is not a person's age: a limit (`Pensiya yaşı 63`), a
        range (`12–15 yaş arası`), an average (`orta yaşı 34`) or the age of a thing (`Binanın yaşı 80`),
        unlabelled."""
        reg = spec["register"]
        style = self._deficit(Q._weights(xa["styles"]), self.sub_counts["age_v43"])
        self.sub_counts["age_v43"][style] += 1
        spec.update(age_style="v43_" + style, kind=style)
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)
        fid, (real_t, (lo, hi)) = self._pick_frame(
            [(f"P.age43.real.{i}", f) for i, f in enumerate(V43.AGE_REAL)], used, fid=lambda z: z[0])
        used.add(fid)
        d.frame_ids.append(fid)
        lid, (fake_t, (flo, fhi)) = self._pick_frame(
            [(f"P.age43.{style}.{i}", f) for i, f in enumerate(V43.AGE_LOOKALIKES[style])], used, fid=lambda z: z[0])
        used.add(lid)
        d.frame_ids.append(lid)
        if style == "age_range":
            a = self.value_rng.randint(flo, fhi - 2)
            fakes = [str(a), str(self.value_rng.randint(a + 2, fhi))]
        else:
            fakes = [str(self.value_rng.randint(flo, fhi))]
        age = self._two_digit_age(lo, hi, avoid=tuple(fakes))
        fill = {"v": lambda x: x.decoy(fakes[0], style, "AGE")}
        if len(fakes) == 2:
            fill["w"] = lambda x: x.decoy(fakes[1], style, "AGE")
        halves = [lambda dd: write(dd, real_t, {"v": lambda x: x.entity("AGE", age)}),
                  lambda dd: write(dd, fake_t, fill)]
        if self.rng.random() < 0.5:
            halves = halves[::-1]
        halves[0](d)
        # not _pair's bridge 75% of the time: in an age-only batch its 10 bridge sentences hit the frame cap
        self._between(d, reg, used, bridge=self.rng.random() < xa.get("bridge_rate", 0.3))
        halves[1](d)
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)

    def _between(self, d: Draft, reg: str, used: set[str], bridge: bool = False) -> None:
        """Between the two halves of a pair. The same frame twice in a row reads
        like a template; a bridging sentence makes it a record being checked
        against another one."""
        self._sep(d)
        if bridge and self.rng.random() < 0.75:
            items = [(f"P.bridge.{i}", t) for i, t in enumerate(BRIDGES)]
            fid, sentence = self._pick_frame(items, used, fid=lambda x: x[0])
            used.add(fid)
            d.frame_ids.append(fid)
            d.add(sentence)
            self._sep(d)
        elif self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)

    def _family_contrast(self, d: Draft, used: set[str], spec: dict) -> None:
        reg = spec["register"]
        weights = {k: v for k, v in Q._weights(self.q["contrast"]).items()
                   if k in CONTRAST or k == "key_pair"}
        sub = self._deficit(weights, self.sub_counts["contrast"])
        spec["sub"] = sub
        if sub == "key_pair":
            # D-34f: a public key (a look-alike), as a block or in a log line;
            # in some documents beside a private key (labelled). Only some:
            # every short key lowers the share of real-length ones (D-27)
            if self.rng.random() < 0.5:
                self._neutral(d, reg, used)
                self._sep(d)
            pub = self._decoy_value(self.kinds["public_key_block"])
            halves = [lambda: self._public_key_sentence(d, used, spec, key=pub)]
            spec["with_private"] = self.rng.random() < self.q["contrast"]["key_pair_private_rate"]
            if spec["with_private"]:
                # D-51h: beside an Ed25519 public key, an Ed25519 private one
                priv = (self.values.private_key_ed25519() if ED25519_PUBLIC_LEAD in pub else None)
                halves.append(lambda: self._pem_sentence(d, used, spec, key=priv))
                if self.rng.random() < 0.5:
                    halves.reverse()
            for i, half in enumerate(halves):
                if i:
                    d.add("\n")
                half()
            if spec["with_private"]:
                self._top_up(d, reg, used)
            else:
                for _ in range(self.rng.randint(1, 2)):
                    self._sep(d)
                    self._neutral(d, reg, used)
            return
        items = [(f"C.{sub}.{i}", t) for i, t in enumerate(CONTRAST[sub])]
        fid, template = self._pick_frame(items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        V = self.values
        vals: dict[str, str] = {}
        if sub == "token_key":
            same = self.rng.random() < self.q["contrast"]["same_body_rate"]
            spec["same_body"] = same
            if same:
                vals["t"], vals["k"] = V.token_key_same_body()
            else:
                vals["t"] = V.access_token()
                while "Bearer {t}" in template and vals["t"].startswith("bearer_"):
                    vals["t"] = V.access_token()
                vals["k"] = V.api_key()
        elif sub == "ipv6_mac":
            vals["i"], vals["m"] = V.ipv6_address(), V.mac_address()
        else:
            vals["l"], vals["d"] = V.licence_and_id_same_prefix()
        if self.rng.random() < 0.5:
            self._neutral(d, reg, used)
            self._sep(d)
        write(d, template, {k: (lambda dd, k=k: dd.entity(CONTRAST_LABELS[k], vals[k]))
                            for k in vals})
        if sub == "licence_id":
            self._licence_id_lines(d, used, spec)
        if sub == "ipv6_mac":
            self._ipv6_extras(d, used, spec, vals)
        if sub == "token_key" and self.rng.random() < self.q["contrast"]["token_look_alike_rate"]:
            kind = self._least_used_kind([self.kinds[k] for k in TOKEN_LOOK_ALIKES])
            self._sep(d)
            t = self._pick_text(d, used, f"C.token_look_alike.{kind.kind}", TOKEN_LOOK_ALIKES[kind.kind])
            dvalue = self._decoy_value(kind)
            write(d, t, {"v": lambda dd: dd.decoy(dvalue, kind.kind, kind.resembles)})
            spec["token_look_alike"] = kind.kind
        for _ in range(self.rng.randint(0, 2)):
            if spec.get("licence_id_lines"):        # after a `Field: value` line, a new line
                d.add("\n")
            else:
                self._sep(d)
            self._neutral(d, reg, used)

    def _ipv6_extras(self, d: Draft, used: set[str], spec: dict, vals: dict) -> None:
        """D-57 M6/M7 (quotas contrast.ipv6_extras, per 25k), beside the real
        IPv6 and MAC of an ipv6_mac document: an IPv6 look-alike with `::` (a
        5-hex group, a non-hex letter, 9 groups, a stray colon), another real
        compressed IPv6 mid-sentence or after a label (IPv6 F1 77.8 against
        A3's 75), a letters-only MAC look-alike. Each in a sentence or line of
        its own."""
        done: list[str] = []
        for _ in range(3):
            item = self._quota_item("ipv6_extra", self.q["contrast"].get("ipv6_extras", {}),
                                    exclude=tuple(done))
            if item is None:
                break
            done.append(item)
            if item == "ipv6_real":
                v = vals["i"]
                while v in (vals["i"], vals["m"]) or "::" not in v:
                    v = self.values.ipv6_and_mac()[0]
                if self.rng.random() < 0.5:
                    if not d.text.endswith("\n"):
                        d.add("\n")
                    d.add(f"{self.rng.choice(V42.IPV6_REAL_FIELDS)}: ")
                    d.entity("IPV6_ADDRESS", v)
                    d.add("\n")
                    spec.setdefault("ipv6_real_layout", []).append("label")
                else:
                    self._sep(d)
                    t = self._pick_text(d, used, "C.ipv6_real", V42.IPV6_REAL_PROSE)
                    write(d, t, {"v": lambda dd, v=v: dd.entity("IPV6_ADDRESS", v)})
                    spec.setdefault("ipv6_real_layout", []).append("prose")
                continue
            kind = self.kinds["ipv6_compressed_bad" if item == "ipv6_bad" else "mac_letters_only"]
            fake = self._decoy_value(kind)
            self._sep(d)
            t = self._pick_text(d, used, f"C.{item}", V42.IPV6_LOOKALIKE if item == "ipv6_bad" else V42.MAC_LETTERS)
            write(d, t, {"v": lambda dd: dd.decoy(fake, kind.kind, kind.resembles)})
        if done:
            spec["ipv6_extra"] = done

    def _licence_id_lines(self, d: Draft, used: set[str], spec: dict) -> None:
        """v4.1 (#91 item 5, C3): beside a same-prefix licence/ID
        pair, sometimes a line whose context word says nothing (each label
        1 : 1), and a `Field: value` line whose field names the other document
        -- the shape decides (D-34d), both ways about equally. The prefix
        keeps its variety (D-51h)."""
        cq = self.q["contrast"]
        both = ("AZ_DRIVER_LICENSE_NUMBER", "AZ_ID_CARD_NUMBER")
        lines = []
        if self.rng.random() < cq["licence_id_generic_rate"]:
            lines.append("generic")
        if self.rng.random() < cq["licence_id_disagree_rate"]:
            lines.append("disagree")
        if self.rng.random() < cq.get("licence_id_short_rate", 0.0):
            lines.append("short")
        for kind in lines:
            lab = self._deficit({x: 1.0 for x in both}, self.sub_counts[f"licence_id_{kind}"])
            self.sub_counts[f"licence_id_{kind}"][lab] += 1
            if kind == "short":
                # D-56a (3): both after a short ID word, 1 : 1, the length decides;
                # the benchmark's misses were all `AA` + 7 digits
                lic, card = self.values.licence_and_id_same_prefix(
                    prefix="AA" if self.rng.random() < cq["licence_id_short_aa_rate"] else None)
                pair = [("AZ_ID_CARD_NUMBER", card), ("AZ_DRIVER_LICENSE_NUMBER", lic)]
                self.rng.shuffle(pair)
                for plab, pv in pair:
                    d.add("\n")
                    t = self._pick_text(d, used, "C.licence_id.short", V4.SHORT_ID_LINES)
                    write(d, t, {"v": lambda dd, plab=plab, pv=pv: dd.entity(plab, pv)}, capitalize=False)
                spec.setdefault("licence_id_lines", []).append("short:both")
                continue
            lic, card = self.values.licence_and_id_same_prefix()
            v = lic if lab == "AZ_DRIVER_LICENSE_NUMBER" else card
            d.add("\n")
            if kind == "generic":
                t = self._pick_text(d, used, "C.licence_id.generic", V4.LICENCE_ID_GENERIC)
                write(d, t, {"v": lambda dd, lab=lab, v=v: dd.entity(lab, v)}, capitalize=False)
            else:
                d.add(self.rng.choice(V4.LICENCE_ID_DISAGREE_FIELDS[lab]) + ": ")
                d.entity(lab, v)
            spec.setdefault("licence_id_lines", []).append(f"{kind}:{lab}")

    def _family_net_context(self, d: Draft, used: set[str], spec: dict) -> None:
        """v4.1 (#91 item 1, b-c): v4 missed IPv6 twice as often
        when the document also held unlabelled dotted codes, though every
        missed sentence was found alone. One or two real IPv6/IPv4/MAC values
        in log/record prose, in the same document as one to three unlabelled
        codes (versions `v2.14.3`, clause numbers `4.2.1`, campaign and archive
        codes), each in its own sentence."""
        nq = self.q["net_context"]
        reg = spec["register"]
        items = ["real"] * self.rng.randint(1, 2) + ["code"] * self.rng.randint(1, 3)
        self.rng.shuffle(items)
        if self.rng.random() < 0.35:
            self._neutral(d, reg, used)
            self._sep(d)
        labels = []
        lw = Q._weights(nq["label_weights"])
        for i, item in enumerate(items):
            if i:
                self._sep(d)
            if item == "real":
                lab = self._deficit(lw, self.sub_counts["net_context"])
                self.sub_counts["net_context"][lab] += 1
                if lab == "IPV6_ADDRESS":
                    v = self.values.ipv6_and_mac()[0] if self.rng.random() < nq["ipv6_compressed_rate"] \
                        else self.values.ipv6_address()
                else:
                    v = self._mint(lab, "prose")
                layout = self.rng.choices(sorted(nq["layout_weights"]),
                                          weights=[nq["layout_weights"][k] for k in sorted(nq["layout_weights"])])[0]
                spec.setdefault("net_layouts", []).append(layout)
                if layout in ("chat", "log"):
                    # D-56a (1): the value ends a chat or log line
                    pool = V4.NET_CHAT_LINES if layout == "chat" else V4.NET_LOG_LINES
                    intros = V4.NET_CHAT_INTROS if layout == "chat" else V4.NET_LOG_INTROS
                    if d.text and not d.text.endswith("\n"):
                        d.add("\n")
                    d.add(self._pick_text(d, used, f"NC.{layout}.intro", intros) + "\n")
                    t = self._pick_text(d, used, f"NC.{layout}.{lab}", pool[lab])
                    write(d, t, {"v": lambda dd, lab=lab, v=v: dd.entity(lab, v)}, capitalize=False)
                    d.add("\n")
                else:
                    t = self._pick_text(d, used, f"NC.{lab}", V4.NET_PROSE[lab])
                    self._ip_write(d, t, lab, v, spec)
                labels.append(lab)
            else:
                kind = self._least_used_kind([self.kinds[k] for k in V4.NET_CODE_KINDS])
                self._decoy_sentence(d, kind, used)
                labels.append(kind.kind)
        spec["net_context"] = labels

    def _family_structured(self, d: Draft, used: set[str], spec: dict) -> None:
        sq = self.q["structured"]
        if self.rng.random() < sq["cvv_csv_rate"]:
            self._cvv_csv(d, used, spec)
            return
        fmt = self._deficit({k: float(v) for k, v in sq["formats"].items()},
                            self.sub_counts["format"])
        spec["format"] = fmt
        if fmt == "caps_form":
            self._caps_form(d, used, spec)
            return
        allowed = [lab for lab in ENTITY_TYPES if FMT.allowed(fmt, lab)]
        k = self.rng.randint(sq["columns_min"], sq["columns_max"])
        columns: list[str] = []
        # D-34 (D-33f `fmt_csv_noheader`): contact rows -- email, ID card,
        # phone -- and a status word; Run B missed the IDs and split the
        # emails and phones there
        contact = fmt == "csv_noheader" and self.rng.random() < sq["csv_noheader_contact_rate"]
        if contact:
            columns = ["EMAIL", "AZ_ID_CARD_NUMBER", "TELEPHONENUM"]
            self.sub_counts[f"id_licence.{fmt}"]["AZ_ID_CARD_NUMBER"] += 1
        elif self.rng.random() < sq["id_or_licence_rate"]:
            # ID card and licence in every format: whichever this format has
            # carried less of so far
            seen = self.sub_counts[f"id_licence.{fmt}"]
            if self.rng.random() < sq["id_and_licence_rate"]:
                # D-51h: both in one row, side by side; only the length
                # (licence 2+6, ID card 2+7) tells them apart (D-34d)
                columns += ["AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"]
                seen.update(columns)
                spec["id_and_licence"] = True
            else:
                pick = min(("AZ_ID_CARD_NUMBER", "AZ_DRIVER_LICENSE_NUMBER"),
                           key=lambda lab: (seen[lab], self.rng.random()))
                seen[pick] += 1
                columns.append(pick)
        if fmt in DATE_KEYED_FORMATS and self.rng.random() < sq["date_column_rate"]:
            columns.append("DATE")          # D-35a
        # D-34 (D-33f): phones after `=` in log lines (87 in a 25,000 build)
        if fmt == "log" and self.rng.random() < sq["log_phone_rate"]:
            columns.append("TELEPHONENUM")
        while not contact and len(columns) < k:
            lab = self.rng.choice(allowed)
            if lab not in columns:
                columns.append(lab)
        # D-57 S5: access tokens back in cells (v4.1 307 -> v4.2 248 per 25k);
        # and a margin for the thinnest table cells (no count below v4.2). On
        # top of the drawn columns, so no other label loses its share
        for lab, rate in Q._weights(sq.get("extra_columns", {})).items():
            if not contact and lab in allowed and lab not in columns and self.rng.random() < rate:
                columns.append(lab)
        self.rng.shuffle(columns)
        n_rows = FMT.rows_for(fmt)
        rows = [self._container_row(columns, fmt) for _ in range(n_rows)]
        # a policy decoy (D-2) is a decoy only beside its own words (`11:09
        # versiyası`, `test kartı`); alone in a cell it is a valid time, card or
        # passport left unlabelled (P4-2 round 2: 14 in 5,000 documents)
        if self.rng.random() < sq["decoy_cell_rate"]:
            options = [(r, c) for r in range(n_rows) for c, lab in enumerate(columns)
                       if any(kk.resembles == lab and not kk.contextual and not kk.policy
                              and kk.kind not in POLICY_PAIRS
                              and kk.kind not in DECOY_GROUPS["sentence_initial"]
                              for kk in self.kinds.values())]
            if options:
                r, c = self.rng.choice(options)
                lab = columns[c]
                kind = self._least_used_kind(
                    [self.kinds[k] for k in DATE_SLOT_KINDS]        # D-35a
                    if lab == "DATE" and fmt in DATE_KEYED_FORMATS else
                    [kk for kk in self.kinds.values() if kk.resembles == lab
                     and not kk.contextual and not kk.policy and kk.kind not in POLICY_PAIRS
                     and kk.kind not in DECOY_GROUPS["sentence_initial"]])
                rows[r][c] = ("decoy", lab, self._decoy_value(kind), kind.kind)
        # D-34g: `label: value` lines and cells. Run B's data held 1-19%
        # look-alikes in that slot (DATE 0.8%), and the probes plant them
        # there; every cell of these labels may now hold one, not one cell
        # per document
        fr = self.q["fix_round"]
        for r in range(n_rows):
            for c, lab in enumerate(columns):
                keyed_date = lab == "DATE" and fmt in DATE_KEYED_FORMATS
                rate = fr["date_cell_decoy_rate"] if keyed_date else fr["slot_cell_decoy_rate"]
                if lab not in SLOT_LABELS or rows[r][c][0] == "decoy" or self.rng.random() >= rate:
                    continue
                pool = ([self.kinds[k] for k in DATE_SLOT_KINDS] if keyed_date else
                        [kk for kk in self.kinds.values() if kk.resembles == lab
                         and not kk.contextual and not kk.policy and kk.kind not in POLICY_PAIRS])
                if pool:
                    kind = self._slot_kind(lab, pool)
                    rows[r][c] = ("decoy", lab, self._decoy_value(kind), kind.kind)
        if contact:
            columns.append("STATUS")
            for row in rows:
                row.append(("text", None, self.rng.choice(FMT.STATUS_WORDS)))
        # an Azerbaijani sentence around the container: header words are
        # field labels, and the language gate does not count them as prose
        before = self.rng.random() < 0.6
        if before:
            self._neutral(d, spec["register"], used)
            d.add("\n")
        pick = lambda items: self._pick_frame(items, used, fid=lambda x: x[0])   # noqa: E731
        for fid in FMT.render(fmt, d, columns, rows, self.rng, pick):
            used.add(fid)
            d.frame_ids.append(fid)
        if not before or self.rng.random() < 0.3:
            d.add("\n")
            self._neutral(d, spec["register"], used)
        spec["columns"] = columns

    def _caps_form(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-57 S2 (real text: all three all-capital cities missed; the
        targeted data had none): a form, header or stamp written in capitals
        -- `SOYADI: MƏMMƏDOV`, `ADI: ELVİN`, `DOĞULDUĞU ŞƏHƏR: GƏNCƏ`, a
        name line `MƏMMƏDOV ELVİN RAMİZ OĞLU` (the father's name GIVENNAME,
        D-39b) -- every value labelled, and an ALL-CAPS heading word on its own
        line as a control (unlabelled). Names in the pool's own spelling, so
        they are left out of the name-variant share (`listed_names`)."""
        cq = self.q["structured"].get("caps", {})
        p = self._person(set(), patronymic=self.rng.random() < cq.get("father_rate", 0.5))
        up = {k: az_upper(v) for k, v in p.items() if k in ("g", "s", "f")}
        layout = self.rng.choice(["fields", "name_line", "town_header"])
        spec["caps_layout"] = layout
        towns = [az_upper(self._town()) for _ in range(self.rng.randint(1, 2))]
        if layout == "town_header":
            # The review, H: the `… ŞƏHƏRİ` header only names a city
            towns[0] = az_upper(self.values.pool.fresh("CITY", lambda: self.rng.choice(V42.CAPS_HEADER_CITIES)))
        while len(towns) == 2 and towns[0] == towns[1]:
            towns[1] = az_upper(self._town())
        headings = self._screened(V42.CAPS_HEADINGS)
        lines: list[Callable[[Draft], None]] = []

        def field(name: str, label: str, value: str) -> Callable[[Draft], None]:
            return lambda dd: (dd.add(az_upper(name) + ": "), dd.entity(label, value))

        # The review, H: one style per form (`SOYADI`/`ADI` or `SOYAD`/`AD`)
        style = self.rng.randrange(len(V42.CAPS_FIELDS["SURNAME"]))
        lines.append(field(V42.CAPS_FIELDS["SURNAME"][style], "SURNAME", up["s"]))
        lines.append(field(V42.CAPS_FIELDS["GIVENNAME"][style], "GIVENNAME", up["g"]))
        if "f" in up:
            lines.append(field(V42.CAPS_FIELDS["FATHER"][0], "GIVENNAME", up["f"]))
        # ... and a bare `ŞƏHƏR` only as the form's one town field
        city_fields = self.rng.sample(V42.CAPS_FIELDS["CITY"] if len(towns) == 1
                                      else [f for f in V42.CAPS_FIELDS["CITY"] if f != "Şəhər"], len(towns))
        lines += [field(f, "CITY", t) for f, t in zip(city_fields, towns)]
        if self.rng.random() < cq.get("id_rate", 0.0):
            lines.append(field(V42.CAPS_FIELDS["AZ_ID_CARD_NUMBER"][0], "AZ_ID_CARD_NUMBER",
                               self._mint("AZ_ID_CARD_NUMBER", "container").upper()))
        if self.rng.random() < cq.get("licence_rate", 0.0):
            lines.append(field(V42.CAPS_FIELDS["AZ_DRIVER_LICENSE_NUMBER"][0], "AZ_DRIVER_LICENSE_NUMBER",
                               self._mint("AZ_DRIVER_LICENSE_NUMBER", "container").upper()))
        d.add(self._pick_text(d, used, "CF.intro", V42.CAPS_INTROS) + "\n")
        if layout == "town_header":           # `GƏNCƏ ŞƏHƏRİ` above the form
            d.entity("CITY", towns[0])
            d.add(" ŞƏHƏRİ\n")
        if self.rng.random() < cq.get("heading_rate", 0.0):
            d.decoy(self.rng.choice(headings), CAPS_HEADING.kind, CAPS_HEADING.resembles)
            d.add("\n")
        if layout == "name_line":             # `MƏMMƏDOV ELVİN RAMİZ OĞLU`
            d.entity("SURNAME", up["s"])
            d.add(" ")
            d.entity("GIVENNAME", up["g"])
            if "f" in up:
                d.add(" ")
                d.entity("GIVENNAME", up["f"])
                d.add(" " + az_upper(p["p"]))
            d.add("\n")
            lines = lines[3 if "f" in up else 2:]
        for i, line in enumerate(lines):
            line(d)
            d.add("\n")
        d.add(self._pick_text(d, used, "CF.after", V42.CAPS_AFTER))
        spec["listed_names"] = sum(e["label"] in ("GIVENNAME", "SURNAME") for e in d.entities)

    def _family_form(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-34g: a short form, 3-5 `Label: value` lines, mixing real values
        and look-alikes of the same labels (at least one of each). Run B's
        data held 1-15% look-alikes in that slot, and the probes plant
        invalid dates, ZIPs, ages and times there."""
        fq = self.q["form"]
        n = self.rng.randint(fq["lines_min"], fq["lines_max"])
        # D-35a: most forms carry one or two date lines, mostly look-alikes
        dates = (self.rng.randint(1, fq["date_lines_max"]) if self.rng.random() < fq["date_rate"] else 0)
        labels = ["DATE"] * dates + self.rng.sample(sorted(SLOT_LABELS - {"DATE"}), n - dates)
        self.rng.shuffle(labels)
        fake = [self.rng.random() < (fq["date_look_alike_rate"] if lab == "DATE" else fq["look_alike_rate"])
                for lab in labels]
        if all(fake) or not any(fake):
            fake[self.rng.randrange(len(fake))] = not fake[0]
        date_fields = self.rng.sample(FORM_FIELDS["DATE"], dates)
        self._neutral(d, spec["register"], used)
        d.add("\n")
        for i, (lab, is_fake) in enumerate(zip(labels, fake)):
            if i:
                d.add("\n")
            d.add(f"{date_fields.pop() if lab == 'DATE' else self.rng.choice(FORM_FIELDS[lab])}: ")
            if is_fake:
                kind = self._slot_kind(lab,
                    [self.kinds[k] for k in DATE_SLOT_KINDS] if lab == "DATE" else
                    [k for k in self.kinds.values() if k.resembles == lab and not k.contextual
                     and not k.policy and k.kind not in POLICY_PAIRS])
                d.decoy(self._decoy_value(kind), kind.kind, lab)
            else:
                d.entity(lab, self._mint(lab, "container"))
        self._form_extra(d, spec)
        if self.rng.random() < 0.6:
            d.add("\n")
            self._neutral(d, spec["register"], used)
        spec["labels"] = labels

    # D-57 form extras: item -> (label, look-alike kind or None)
    FORM_EXTRA = {"voen9": ("AZ_VOEN", "voen_nine_digits"), "passport": ("AZ_PASSPORT_NUMBER", None),
                  "cvv5": ("CARD_SECURITY_CODE", "cvv_5_digits"), "cvv2": ("CARD_SECURITY_CODE", "cvv_1_2_digits"),
                  "card": ("PAYMENT_CARD_NUMBER", None)}

    def _form_extra(self, d: Draft, spec: dict) -> None:
        """D-57 (quotas form.extras, per 25k): a real value after its field,
        and beside it, in the same form, a look-alike of the same label --
        M5 a 5-digit CVV at a line end after `CVV kodu:` and a 2-digit CVV,
        M7 a 9-digit VÖEN -- or the real value alone (S5: VÖEN and passports
        after a label, +150 each; CVVs and cards back to v4.1's level)."""
        item = self._quota_item("form_extra", self.q["form"].get("extras", {}))
        if item is None:
            return
        lab, fake_kind = self.FORM_EXTRA[item]
        fields = V42.FORM_EXTRA_FIELDS.get(lab) or FORM_FIELDS[lab]
        real = self._mint(lab, "container")
        lines = [(self.rng.choice(fields), lambda dd: dd.entity(lab, real))]
        if fake_kind:
            kind = self.kinds[fake_kind]
            fake = self._decoy_value(kind)
            while fake == real or (item == "cvv2" and len(fake) != 2):
                fake = self._decoy_value(kind)
            name = "CVV kodu" if item == "cvv5" else self.rng.choice(fields)
            lines.append((name, lambda dd: dd.decoy(fake, kind.kind, lab)))
            self.rng.shuffle(lines)
        for name, fill in lines:       # each on its own line: a line end after the value
            d.add(f"\n{name}: ")
            fill(d)
        spec["form_extra"] = [item]

    def _family_clerical(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-34 (D-33f `single_entity`, `prose_card`, `prose_iban`): a long
        clerical chain, 6-10 short office clauses joined by semicolons, one
        value or one look-alike in a clause in the middle, filler reference
        codes around it. Clauses are added until the chain is 330-660
        characters, the probes' length."""
        cq = self.q["clerical"]
        label = self._deficit(Q._weights(cq["label_weights"]), self.sub_counts["clerical_label"])
        kinds = [self.kinds[k] for k in CLERICAL_KINDS
                 if k in self.kinds and self.kinds[k].resembles == label]
        fake = bool(kinds) and self.rng.random() < cq["look_alike_rate"]
        if fake:
            kind = self._least_used_kind(kinds)
            vtext = self._decoy_value(kind)
            fill = lambda dd: dd.decoy(vtext, kind.kind, label)     # noqa: E731
        elif label == "IBAN" and self.rng.random() < cq["iban_letters_rate"]:
            # D-33f `prose_iban`: every IBAN Run B missed in a chain had
            # letters in its account part
            vtext = self.values.iban_az_alnum(grouped=self.rng.random() < 0.5)
            fill = lambda dd: dd.entity(label, vtext)              # noqa: E731
        else:
            # cards plain or grouped (the probes miss both); IBANs Azerbaijani
            vtext = self._mint(label, "clerical" if label == "PAYMENT_CARD_NUMBER" else "prose")
            fill = lambda dd: dd.entity(label, vtext)              # noqa: E731
        vt = self._pick_text(d, used, f"CL.v.{label}", CLERICAL_VALUE[label])
        ref_kind = self.kinds["internal_reference"]
        refs = [self._decoy_value(ref_kind)]
        target = self.rng.randint(cq["clauses_min"], cq["clauses_max"])
        length = len(vt.replace("{v}", vtext)) + 1
        pool = [(f"CL.{i}", t) for i, t in enumerate(CLERICAL_CLAUSES)
                if self.frame_docs[f"CL.{i}"] < self.cap]
        self.rng.shuffle(pool)
        chosen: list[tuple[str, str]] = []
        for fid, t in pool:
            if len(chosen) + 1 >= target and length >= cq["chars_min"]:
                break
            grow = len(t.replace("{ref}", refs[0])) + 2
            if length + grow > cq["chars_max"] or ("{ref}" in t and any("{ref}" in c for _, c in chosen)):
                continue
            chosen.append((fid, t))
            length += grow
        for fid, _t in chosen:
            used.add(fid)
            d.frame_ids.append(fid)
        at = self.rng.randint(min(2, len(chosen)), max(min(2, len(chosen)), len(chosen) - 2))
        clauses = [t for _, t in chosen]
        clauses.insert(at, vt)
        for i, t in enumerate(clauses):
            if i:
                d.add("; ")
            write(d, t, {"v": fill, "ref": lambda dd: dd.decoy(refs[0], ref_kind.kind, ref_kind.resembles)},
                  capitalize=i == 0)
        d.add(".")
        spec["clerical"] = {"label": label, "look_alike": fake, "clauses": len(clauses), "at": at}

    def _person(self, taken: set[str], patronymic: bool = False) -> dict:
        """D-39b: one person from our pools, a man or a woman; with a
        patronymic, the father's name (a man's, Azerbaijani) and `oğlu`/`qızı`.
        No name repeats inside the document (`taken`)."""
        female = self.rng.random() < 0.4
        person = {"female": female}
        V = self.values
        # D-40a (review, finding 1): the pool's own Azerbaijani
        # spelling for every part -- latin_spelling kept the English-style
        # variants (kh, gh, sh, j), so 35 of 327 people mixed two spellings;
        # the father from men's names that are not also women's names
        mint = {"g": lambda: V.givenname("az", female=female, origin="", variant=False),
                "s": lambda: V.surname("az", female=female, origin="", variant=False),
                "f": lambda: V.father_name("az")}
        for key in ("g", "s", "f"):
            if key == "f" and not patronymic:
                continue
            for _ in range(40):
                value = mint[key]()
                if value not in taken:
                    break
            else:
                raise BuildError("namelist: no unused name in 40 mints")
            taken.add(value)
            person[key] = value
        if patronymic:
            person["p"] = "qızı" if female else "oğlu"
        return person

    def _family_namelist(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-39b (shapes of the real-text misses): official name
        lists with patronymics, names after a lowercase role word, a name
        alone on a signature line, sentence-initial names, a name right after
        an organisation. Run B's data held no patronymic at all."""
        nq = self.q["namelist"]
        # official lists and notices: the bureaucratic filler register, not
        # the customer-service or chat one (`Zəhmət olmasa, cavabımızı gözləyin.`)
        reg = "bureaucratic" if "bureaucratic" in self.frames.neutral else spec["register"]
        spec["register"] = reg
        sub = self._deficit(Q._weights(nq["subs"]), self.sub_counts["namelist"])
        spec["namelist"] = sub
        taken: set[str] = set()

        def writers(p: dict, **text: str) -> dict:
            w = {"s": lambda dd: dd.entity("SURNAME", p["s"]),
                 "g": lambda dd: dd.entity("GIVENNAME", p["g"])}
            if "f" in p:
                w["f"] = lambda dd: dd.entity("GIVENNAME", p["f"])
                w["p"] = lambda dd: dd.add(p["p"])
            w.update({k: (lambda dd, v=v: dd.add(v)) for k, v in text.items()})
            return w

        def name(p: dict, forms: tuple = ("gs", "g", "s"), weights: tuple = (0.65, 0.2, 0.15)):
            form = self.rng.choices(forms, weights=weights)[0]

            def w(dd: Draft) -> None:
                if form in ("gs", "g"):
                    dd.entity("GIVENNAME", p["g"])
                if form == "gs":
                    dd.add(" ")
                if form in ("gs", "s"):
                    dd.entity("SURNAME", p["s"])
            return w

        given_forms = (("gs", "g"), (0.6, 0.4))         # a given name, with or without a surname

        def sentence(pool: str, items: list[str], p: dict, name_args: tuple = (), **text: str) -> None:
            t = self._pick_text(d, used, f"NL.{pool}", items)
            if "sədrlik" in t and text.get("role") == "sədr":
                # D-40a (finding 5): not "the chairman X chaired"
                text["role"] = self.rng.choice([r for r in ROLE_WORDS if r != "sədr"])
            w = writers(p, **text)
            w["n"] = name(p, *name_args)
            write(d, t, w, capitalize=False)

        style = None
        if sub == "signature":
            styles = Q._weights(nq["signature_styles"])
            style = self.rng.choices(sorted(styles), weights=[styles[k] for k in sorted(styles)])[0]
        # a letter signed with a title only opens with its addressee (D-51h)
        if self.rng.random() < nq["lead_rate"] and style != "title_only":
            self._neutral(d, reg, used)
            self._sep(d)
        if sub == "patronymic_list":
            d.add(self._pick_text(d, used, "NL.intro", NAMELIST_INTROS) + "\n")
            names = list(NAMELIST_LINES)
            style = self.rng.choices(names, weights=[NAMELIST_LINES[k][1] for k in names])[0]
            punct = self.rng.choice(["", "", ";", ","])
            people = self.rng.randint(nq["people_min"], nq["people_max"])
            # D-51h: some lists hold a vacant seat, a position title in a
            # name line (`Baş mühasib (vakant)`, unlabelled)
            lines = ["person"] * people
            if self.rng.random() < nq["control_line_rate"]:
                lines.insert(self.rng.randint(1, people), "vacant")
                spec["control_line"] = True
            marker = {"numbered": "{n}. ", "dash": "— "}.get(style, "")
            for i, kind in enumerate(lines):
                if kind == "person":
                    p = self._person(taken, patronymic=True)
                    write(d, NAMELIST_LINES[style][0],
                          writers(p, n=str(i + 1), t=self.rng.choice(NAMELIST_TAILS)), capitalize=False)
                else:
                    d.add(marker.format(n=i + 1))
                    d.decoy(self.rng.choice(V4.CONTROL_POSITIONS), "namelist_control", "GIVENNAME")
                    d.add(" " + V4.CONTROL_VACANT)
                last = i == len(lines) - 1
                d.add((punct if not last else ("." if punct else "")) + ("\n" if not last else ""))
            spec["people"] = people
            spec["line_style"] = style
            # D-40a (finding 3): the list ends its line; what follows starts
            # a new one (4 of 96 lists ran into the next sentence)
            d.add("\n")
            if self.rng.random() < nq["control_list_rate"]:
                self._control_list(d, used, marker, spec)
            if self.rng.random() < 0.8:
                d.add(self._pick_text(d, used, "NL.outro", NAMELIST_OUTROS))
            else:
                self._neutral(d, reg, used)
            self._top_up(d, reg, used, technical=False)
        elif sub == "patronymic_sentence":
            for i in range(self.rng.randint(1, 2)):
                if i:
                    self._sep(d)
                sentence("patro", PATRO_SENTENCES, self._person(taken, patronymic=True))
        elif sub == "role_word":
            items = ["name"] * self.rng.randint(1, 2)
            # D-51h: a lowercase role word, then a capitalised department or
            # organisation, in the same document as role + name
            if self.rng.random() < nq["role_control_rate"]:
                items.insert(self.rng.randint(0, len(items)), "control")
                spec["role_control"] = True
            for i, item in enumerate(items):
                if i:
                    self._sep(d)
                if item == "name":
                    sentence("role", ROLE_SENTENCES, self._person(taken), role=self.rng.choice(ROLE_WORDS))
                else:
                    before, word, after, _side = parse_marked(
                        self._pick_text(d, used, "NL.role_control", V4.ROLE_CONTROL_SENTENCES))
                    d.add(before)
                    d.decoy(word, "role_word_control", "GIVENNAME")
                    d.add(after)
        elif sub == "signature":
            # D-40a (finding 2): under a title, the full name; a bare given
            # name only after `Hörmətlə,`. D-51h: a signature with only a
            # title (unlabelled), the letter addressed to a named person
            spec["signature"] = style
            p = self._person(taken)
            if style == "title_only":
                addressee = self.rng.choice(V4.ADDRESSEE)
                write(d, addressee, writers(p, h="xanım" if p["female"] else "bəy"), capitalize=False)
                d.add("\n")
            for _ in range(self.rng.randint(1, 2)):
                self._neutral(d, reg, used)
                self._sep(d)
            title = self.rng.choice(SIGNATURE_TITLES)
            d.add("\n")
            if style == "title_only":
                d.add("Hörmətlə,\n")
                d.decoy(self.rng.choice(V4.SIGNATURE_ONLY_TITLES), "signature_title_only", "GIVENNAME")
            elif style == "title_name":
                d.add(title + "\n")
                write(d, "{g} {s}", writers(p), capitalize=False)
            elif style == "greeting_given":
                d.add("Hörmətlə,\n")
                d.entity("GIVENNAME", p["g"])
            else:
                write(d, "{g} {s}", writers(p), capitalize=False)
                d.add("\n" + title)
            self._top_up(d, reg, used, technical=False)
            self._listed_names(d, spec)
            return
        elif sub == "sentence_initial":
            sentence("initial", INITIAL_SENTENCES, self._person(taken), given_forms)
        elif sub == "line_start":
            self._line_start_lines(d, used, taken, spec)
        else:                                       # after_org
            sentence("org", ORG_SENTENCES, self._person(taken), given_forms,
                     org=self.rng.choice(ORG_NAMES))
        if self.rng.random() < nq["tail_rate"]:
            # The native review of #90 (F): after a block of lines the
            # next sentence starts on its own line, not after the last speaker
            if sub == "line_start":
                d.add("\n")
            else:
                self._sep(d)
            self._neutral(d, reg, used)
        self._listed_names(d, spec)

    def _line_start_lines(self, d: Draft, used: set[str], taken: set[str], spec: dict,
                          names: bool = True) -> None:
        """v4.1 A5 (v3_shadow_shapes.md lead 5, part 3): 4-6 lines, each opened
        by a capitalised word and a colon -- a role (`Operator:`) or heading
        word (`Qeyd:`), unlabelled, or a real given name (`Leyla:`, sometimes
        with the surname), labelled. At least one of each; no timestamps.
        v4.2 fix list (line-start GIVENNAME false alarms 20 -> 46, mostly in
        PII-free documents): with `names=False`, roles and headings only."""
        n = self.rng.randint(4, 6)
        if names:
            kinds = ["role", "heading", "name"] + self.rng.choices(["role", "heading", "name"],
                                                                  weights=[0.4, 0.25, 0.35], k=n - 3)
        else:
            kinds = ["role", "heading"] + self.rng.choices(["role", "heading"], weights=[0.55, 0.45], k=n - 2)
        self.rng.shuffle(kinds)
        roles = self.rng.sample(V4.LINE_START_ROLES, 3)
        headings = self.rng.sample(sorted(V4.LINE_START_HEADINGS), 3)
        agent = iter(self.rng.sample(V4.STAMP_AGENT_LINES, len(V4.STAMP_AGENT_LINES)) * 2)
        customer = iter(self.rng.sample(V4.STAMP_CUSTOMER_LINES, len(V4.STAMP_CUSTOMER_LINES)) * 2)
        people = [self._person(taken) for _ in range(2)]
        # The native review of #90 (D): the line must not give the label
        # away. In about 40% of the documents one named person is the agent
        # (`Leyla: Salam, sizə necə kömək edə bilərəm?`), and `Müştəri` speaks
        # the customer's lines (C)
        agent_person = self.rng.randrange(2) if self.rng.random() < self.q["namelist"]["named_agent_rate"] else -1
        own = {r: iter(self.rng.sample(v, len(v)) * 3) for r, v in V4.LINE_START_OWN_LINES.items()}

        def role_line(role: str) -> str:
            if role in V4.LINE_START_CUSTOMER_ROLES:
                return next(customer)
            if role in own:
                return next(own[role])
            return next(agent)

        if d.text and not d.text.endswith("\n"):          # the block starts on its own line
            d.add("\n")
        d.add(self._pick_text(d, used, "LS.intro", V4.LINE_START_INTROS) + "\n")
        counts = collections.Counter()
        named_agent_lines = 0
        for i, k in enumerate(kinds):
            if i:
                d.add("\n")
            j = counts[k]
            counts[k] += 1
            if k == "role":
                role = roles[j % 3]
                d.decoy(role, LINE_START_CONTROL.kind, "GIVENNAME")
                d.add(": " + role_line(role))
            elif k == "heading":
                h = headings[j % 3]
                d.decoy(h, LINE_START_CONTROL.kind, "GIVENNAME")
                d.add(": " + V4.LINE_START_HEADINGS[h])
            else:
                p = people[j % 2]
                d.entity("GIVENNAME", p["g"])
                if self.rng.random() < 0.3:
                    d.add(" ")
                    d.entity("SURNAME", p["s"])
                if j % 2 == agent_person:
                    d.add(": " + next(agent))
                    named_agent_lines += 1
                else:
                    d.add(": " + next(customer))
        spec["line_start"] = dict(counts)
        spec["line_start_named_agent"] = named_agent_lines

    def _control_list(self, d: Draft, used: set[str], marker: str, spec: dict) -> None:
        """D-51h: after a name list, a second list in the same layout whose
        items are departments, organisations, positions or document titles
        (unlabelled `namelist_control`)."""
        intro = self._pick_text(d, used, "NL.control_intro", list(V4.CONTROL_LISTS))
        pool = {"orgs_departments": V4.CONTROL_ORGS + V4.CONTROL_DEPARTMENTS,
                "departments": V4.CONTROL_DEPARTMENTS, "documents": V4.CONTROL_DOCUMENTS,
                "positions": V4.CONTROL_POSITIONS}[V4.CONTROL_LISTS[intro]]
        items = self.rng.sample(pool, self.rng.randint(2, 4))
        d.add(intro + "\n")
        for i, item in enumerate(items):
            d.add(marker.format(n=i + 1))
            d.decoy(item, "namelist_control", "GIVENNAME")
            d.add("\n")
        spec["control_list"] = len(items)

    def _listed_names(self, d: Draft, spec: dict) -> None:
        """D-40a: a name list's names are in the pool's own spelling on
        purpose, so `--stats` leaves them out of the ~10% name-variant share,
        like the homograph-list names (`listed_names`)."""
        spec["listed_names"] = sum(e["label"] in ("GIVENNAME", "SURNAME") for e in d.entities)

    def _family_postal(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-42c item 2: bare 4-digit ZIPs (and some `AZ####`) in the
        contexts of the shadow shapes, with a labelled city where the
        sentence names the place."""
        pq = self.q["postal"]
        reg = spec["register"]
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)
        zips = []
        for i in range(self.rng.randint(1, 2)):
            if i:
                self._sep(d)
            z = (self.values.zipcode_bare() if self.rng.random() < pq["bare_rate"]
                 else self._mint("ZIPCODE", "prose"))
            avoid = () if takes_suffix(z) else tuple(t for t in POSTAL_SENTENCES if "{cop}" in t)
            no_word = z.isdigit() and self.rng.random() < pq["bare_no_word_rate"]
            zip_word = not no_word and self.rng.random() < pq["zip_word_rate"]
            t = (self._pick_text(d, used, "PO.bare", POSTAL_BARE_SENTENCES) if no_word
                 else self._pick_text(d, used, "PO.zip", V4.POSTAL_ZIP_WORD_SENTENCES) if zip_word
                 else self._pick_text(d, used, "PO", POSTAL_SENTENCES, avoid=avoid))
            towns = self.values.loc("az").cities
            c = (self.values.pool.fresh("CITY", lambda: self.rng.choice(towns)) if "{t}" in t
                 else self._mint("CITY", "prose"))
            write(d, t, {"z": lambda dd, z=z: dd.entity("ZIPCODE", z),
                         "c": lambda dd, c=c: dd.entity("CITY", c),
                         "t": lambda dd, c=c: dd.entity("CITY", c),
                         "cop": lambda dd, z=z: dd.add(suffix_after_number(z, "cop"))}, capitalize=False)
            zips.append(("bare, no index word" if no_word else "bare") if z.isdigit() else "AZ")
            if zip_word:
                zips.append("after ZIP")
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)
        spec["zips"] = zips

    def _family_edges(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-42c items 3-4: VÖEN, passport and building numbers glued to
        punctuation (EDGE_SENTENCES), and VÖEN and building numbers after a
        document noun or a verb with no anchor right before
        (CONTEXT_SENTENCES). The span is always the value alone, the
        passport's letter and the building number's letter or `/9` inside."""
        reg = spec["register"]
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)
        done = []
        for i in range(self.rng.randint(1, 2)):
            if i:
                self._sep(d)
            kind = "edge" if self.rng.random() < self.q["edges"]["edge_rate"] else "context"
            pool = EDGE_SENTENCES if kind == "edge" else CONTEXT_SENTENCES
            label = self.rng.choice(sorted(pool))
            value = self._mint(label, "prose")
            # a suffix after a number only (frame ids stay stable: `avoid`)
            # v4.2 native review G: no ending after a dashed IBAN, whose
            # ending hyphen would read as one more group
            avoid = () if takes_suffix(value) and "-" not in value else tuple(
                t for t in pool[label] if "{cop}" in t or "{loc}" in t)
            t = self._pick_text(d, used, f"ED.{kind}.{label}", pool[label], avoid=avoid)
            write(d, t, {"v": lambda dd, value=value, label=label: dd.entity(label, value),
                         "cop": lambda dd, value=value: dd.add(suffix_after_number(value, "cop")),
                         "loc": lambda dd, value=value: dd.add(suffix_after_number(value, "loc"))},
                  capitalize=False)
            done.append([kind, label])
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)
        spec["edges"] = done

    def _family_punct(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-34 (D-33f `punct_touching`): one or two sentences with a value
        glued to punctuation on both sides (GLUED), each a real value or,
        where the label has look-alikes, a look-alike (`—ali@@mail.az!`)."""
        pq = self.q["punct"]
        reg = spec["register"]
        labels = self.rng.sample(sorted(GLUED), self.rng.randint(1, 2))
        if self.rng.random() < 0.5:
            self._neutral(d, reg, used)
            self._sep(d)
        glued = []
        for i, label in enumerate(labels):
            if i:
                self._sep(d)
            t = self._pick_text(d, used, f"GL.{label}", GLUED[label])
            if label in GLUED_KINDS and self.rng.random() < pq["look_alike_rate"]:
                kind = self._least_used_kind([self.kinds[k] for k in GLUED_KINDS[label]])
                v = self._decoy_value(kind)
                fill = lambda dd, v=v, kind=kind: dd.decoy(v, kind.kind, kind.resembles)  # noqa: E731
                glued.append((label, "look-alike"))
            else:
                v = self._mint(label, "prose")
                fill = lambda dd, v=v, label=label: dd.entity(label, v)                  # noqa: E731
                glued.append((label, "real"))
            write(d, t, {"v": fill})
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)
        spec["glued"] = glued

    def _mint_village(self, kend: bool = False) -> str:
        """A village or settlement from the CITY pool (P2-14), not a city; with
        `kend`, not one whose name already ends in `kənd`."""
        for _ in range(60):
            v = self._mint("CITY", "prose")
            if v in self.villages and not (kend and v.casefold().endswith("kənd")):
                return v
        raise BuildError("no village in 60 CITY draws")

    def _family_village(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-34 (D-33f `villages`): one or two village sentences -- the name
        before `kənd` with the suffix on `kənd`, or the name itself suffixed
        -- and one or two controls in the same document: a sentence-initial
        word describing villages or `bağ evi` (`village_descriptor`), a
        kinship noun with a possessive (`kinship_possessive`)."""
        vq = self.q["village"]
        order = ["kend" if self.rng.random() < vq["kend_rate"] else "suffix"
                 for _ in range(self.rng.randint(1, 2))]
        order += ["control" if self.rng.random() < vq["descriptor_rate"] else "kinship"
                  for _ in range(self.rng.randint(1, 2))]
        self.rng.shuffle(order)
        for i, item in enumerate(order):
            if i:
                self._sep(d)
            if item == "kend":
                v = self._mint_village(kend=True)
                write(d, self._pick_text(d, used, "V.kend", VILLAGE_KEND),
                      {"v": lambda dd: dd.entity("CITY", v)})
            elif item == "suffix":
                self._suffix_sentence(d, "CITY", self.rng.choice(VILLAGE_CASES), used, village=True)
            else:
                pool, kind, resembles = ((VILLAGE_CONTROLS, "village_descriptor", "CITY")
                                         if item == "control"
                                         else (KINSHIP_CONTROLS, "kinship_possessive", "GIVENNAME"))
                before, word, after, _side = parse_marked(self._pick_text(d, used, f"V.{item}", pool))
                d.add(before)
                d.decoy(word, kind, resembles)
                d.add(after)
        if self.rng.random() < 0.4:
            self._sep(d)
            self._neutral(d, spec["register"], used)
        spec["village"] = order

    def _family_inflected(self, d: Draft, used: set[str], spec: dict) -> None:
        """P2-4c (RC8): one to three sentences whose name, surname, city or
        street is inflected -- every case, in natural sentences, steered so
        each stays near its target share."""
        reg = spec["register"]
        n = self.rng.choices([1, 2, 3], weights=self.q["suffix"]["sentences_weights"])[0]
        # held near the middle of the 35-40% target, as casing noise is held
        # at its quota: left to chance, a 1,500-document build drifts +/-2.5
        t = self.q["targets"]
        mid = (t["suffixed_min"] + t["suffixed_max"]) / 2
        if self.inflectable_total >= 200:
            share = sum(self.case_counts.values()) / self.inflectable_total
            n = 3 if share < mid - 0.01 else 1 if share > mid + 0.01 else n
        if self.rng.random() < 0.5:
            self._neutral(d, reg, used)
            self._sep(d)
        local: collections.Counter = collections.Counter()
        for i in range(n):
            if i:
                self._sep(d)
            case, label = self._pick_case(local)
            self._suffix_sentence(d, label, case, used)
            local[case] += 1
        if self.rng.random() < 0.6:
            self._sep(d)
            self._neutral(d, reg, used)

    def _family_minimal(self, d: Draft, used: set[str], spec: dict) -> None:
        """P2-4d (RC9): a name, a full name, a greeting or a lone place, one to
        five words. D-10: a capitalised name alone is labelled; a lowercase
        homograph word alone is not (declared as a `homograph_noun` decoy)."""
        mq = self.q["minimal"]
        weights = {k: float(v) for k, v in Q._weights(mq["forms"]).items()}
        form = self.rng.choices(sorted(weights), weights=[weights[k] for k in sorted(weights)])[0]
        items = [(f"M.{form}.{i}", t) for i, t in enumerate(MINIMAL_FORMS[form])]
        fid, template = self._pick_frame(items, used, fid=lambda x: x[0])
        used.add(fid)
        d.frame_ids.append(fid)
        female = self.rng.random() < 0.5
        listed = self.rng.random() < mq["homograph_name_rate"]
        # one person: a foreign given name comes with a surname of its origin (P2-15)
        origin = "" if listed else self.values.name_origin("az")
        if listed:
            given = self.rng.choice(self.homographs.lone_names)
            gender = self.homographs.gender.get(given)
            if gender in ("f", "m"):
                female = gender == "f"
        else:
            given = self._mint("GIVENNAME", "minimal", female, origin)
        writers = {
            "g": lambda dd: dd.entity("GIVENNAME", given),
            "s": lambda dd: dd.entity("SURNAME", self._mint("SURNAME", "minimal", female, origin)),
            "c": lambda dd: dd.entity("CITY", self._mint("CITY", "minimal")),
            "t": lambda dd: dd.entity("STREET", self._mint("STREET", "minimal")),
            "w": lambda dd: dd.decoy(self.rng.choice(self.homographs.lone_words),
                                     "homograph_noun", "GIVENNAME"),
        }
        write(d, template, writers, capitalize=False)
        spec["minimal"] = form
        if listed:
            # from the homograph list, not minted: never in another spelling
            spec["listed_names"] = sum(e["label"] == "GIVENNAME" for e in d.entities)

    def _homograph_sentence(self, d: Draft, name: str, item: tuple, used: set[str]) -> None:
        fid, before, word, after = item
        used.add(fid)
        d.frame_ids.append(fid)
        d.add(before)
        if fid.split(".")[2] == "word":
            d.decoy(word, "homograph_noun", "GIVENNAME")
        elif word == name:
            d.entity("GIVENNAME", word)
        else:
            # an inflected name (`Dənizə`): declared like every inflected word
            case = next((c for c in sorted(SFX.APPLIES["GIVENNAME"])
                         if SFX.inflect(name, c, "GIVENNAME") == word), None)
            if case is None:
                d.entity("GIVENNAME", word)
            else:
                d.suffixed("GIVENNAME", word, SFX.split(word, name), case, "plain")
        d.add(after)

    def _family_homograph(self, d: Draft, used: set[str], spec: dict) -> None:
        """P2-4d (RC9): the same word as a name (labelled) and as the ordinary
        word (a `homograph_noun` decoy) in one document -- `Dəniz zəng etdi`
        and `Dəniz sakit idi` -- so only the meaning tells them apart."""
        reg = spec["register"]
        low = min(self.homograph_counts[n] for n in self.homographs.entries)
        name = self.rng.choice(sorted(n for n in self.homographs.entries
                                      if self.homograph_counts[n] == low))
        sides = self.homographs.entries[name]
        pick = lambda items: self._pick_frame(items, used, fid=lambda x: x[0])  # noqa: E731
        first, second = (("name", "word") if self.rng.random() < 0.5 else ("word", "name"))
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            self._sep(d)
        self._homograph_sentence(d, name, pick(sides[first]), used)
        self._sep(d)
        if self.rng.random() < 0.5:
            self._neutral(d, reg, used)
            self._sep(d)
        self._homograph_sentence(d, name, pick(sides[second]), used)
        if self.rng.random() < 0.4:
            self._sep(d)
            self._neutral(d, reg, used)
        spec["homograph"] = name
        spec["listed_names"] = sum(e["label"] == "GIVENNAME" for e in d.entities)

    # -- D-57: items steered to a count per 25,000 documents -------------------
    def _quota_item(self, counter: str, targets: dict, exclude: tuple[str, ...] = ()) -> str | None:
        """The item furthest behind its target (per 25,000 documents of the
        whole build, so far), or None when every item is on target. The
        accepted counts are in sub_counts[counter] (`_accept`); `local`
        counts of the document being written are added by the caller through
        `exclude` (an item at most once per document)."""
        t = Q._weights(targets)
        have = self.sub_counts[counter]
        scale = (self.written + 1) / 25000
        gaps = {k: v * scale - have[k] for k, v in t.items() if k not in exclude}
        if not gaps:
            return None
        best = max(sorted(gaps), key=lambda k: gaps[k])
        return best if gaps[best] > 0 else None

    # PII-free near misses (M1, and the PII-free part of M5-M7): item -> kinds
    PF_NEAR_KINDS = {"date": ("date_feb_invalid", "date_month_near", "date_impossible_day"),
                     "iban_short": ("iban_short_account",), "iban_bare": ("iban_country_code",),
                     "licence3": ("licence_three_letters",),
                     "time_near": ("time_hour_near", "time_minute_near"),
                     "cvv2": ("cvv_1_2_digits",), "ipv6_bad": ("ipv6_compressed_bad",),
                     "voen9": ("voen_nine_digits",)}

    def _pf_near_value(self, item: str) -> tuple[str, object]:
        kind = self._least_used_kind([self.kinds[k] for k in self.PF_NEAR_KINDS[item]])
        for _ in range(50):
            v = self._decoy_value(kind)
            if (item == "iban_bare" and v != "AZ") or (item == "cvv2" and len(v) != 2):
                continue
            return v, kind
        raise BuildError(f"pf_near {item}: no value in 50 draws")

    def _pf_near(self, d: Draft, used: set[str], spec: dict, k_max: int, line_rate: float | None = None) -> None:
        """D-57 M1: the PII-free documents draw the near-miss kinds directly
        (v4.2: of 2,540 PII-free documents' date look-alikes, 32 were near
        misses; the least-used kind went elsewhere), each in a `Field: value`
        line or in a sentence. Added to the document's other look-alikes,
        never in their place (the far time kinds keep their supply)."""
        pq = self.q["pii_free"]
        rate = pq.get("near_line_rate", 0.5) if line_rate is None else line_rate
        done: list[str] = []
        for _ in range(k_max):
            item = self._quota_item("pf_near", pq.get("near_miss", {}), exclude=tuple(done))
            if item is None:
                break
            v, kind = self._pf_near_value(item)
            if rate and self.rng.random() < rate:
                if d.text and not d.text.endswith("\n"):
                    d.add("\n")
                d.add(f"{self.rng.choice(V42.PF_NEAR_FIELDS[item])}: ")
                d.decoy(v, kind.kind, kind.resembles)
                d.add("\n")
            else:
                if d.text:
                    self._sep(d)
                self._decoy_sentence(d, kind, used, value=v)
            done.append(item)
        if done:
            spec["pf_near"] = spec.get("pf_near", []) + done

    def _family_pii_free(self, d: Draft, used: set[str], spec: dict) -> None:
        reg = spec["register"]
        pq = self.q["pii_free"]
        n_decoys = (self.rng.randint(1, pq["decoys_max"])
                    if self.rng.random() < pq["with_decoys_rate"] else 0)
        n_neutral = self.rng.randint(2, 5)
        slots = ["n"] * n_neutral + ["d"] * n_decoys
        # v4.2 fix list: a block of lines opened by roles and headings, no name
        if self.rng.random() < pq.get("line_start_rate", 0.0):
            slots.append("l")
        self.rng.shuffle(slots)
        for i, s in enumerate(slots):
            if i:
                self._sep(d)
            if s == "l":
                self._line_start_lines(d, used, set(), spec, names=False)
                d.add("\n")
            elif s == "n":
                self._neutral(d, reg, used)
            else:
                # D-42c (D-41d): Run B masked look-alikes in 49.5% of shadow's
                # PII-free documents, mostly broken emails, IPv6, times, dates,
                # tokens and keys -- the labels these documents held fewest of
                kinds = list(self.kinds.values())
                if self.rng.random() < pq["focus_rate"]:
                    # the label first, by weight: global least-used balancing
                    # kept the email kinds (busy in forms and cells) out
                    fw = Q._weights(pq["focus_weights"])
                    labs = sorted(fw)
                    lab = self.rng.choices(labs, weights=[fw[x] for x in labs])[0]
                    if lab == "PRIVATE_KEY" and self.rng.random() < pq["key_placeholder_share"]:
                        # v4.1 A5: the header words of a key block with no key
                        self._key_placeholder_block(d, used)
                        spec.setdefault("key_placeholders", 0)
                        spec["key_placeholders"] += 1
                        continue
                    kinds = [k for k in kinds if k.resembles == lab and k.kind not in PEM_DECOY_KINDS]
                self._decoy_sentence(d, self._least_used_kind(kinds), used)
        # D-57 M1: the near misses, on top of the look-alikes above
        self._pf_near(d, used, spec, pq.get("near_max", 0))
        if d.text.endswith("\n"):
            self._neutral(d, reg, used)

    # -- D-57 S5/S6: real values the new look-alikes must not teach a miss of --
    def _recall_value(self, item: str) -> tuple[str, str]:
        V = self.values
        if item == "token_prose":
            return "ACCESS_TOKEN", V.access_token()
        if item == "cvv_mid":
            return "CARD_SECURITY_CODE", self._mint("CARD_SECURITY_CODE", "prose")
        if item == "card_mid":
            return "PAYMENT_CARD_NUMBER", self._mint("PAYMENT_CARD_NUMBER", "prose")
        if item == "time_radelerinde":
            return "TIME", V.pool.fresh("TIME", lambda: f"{self.rng.randint(6, 22):02d}:"
                                                        f"{self.rng.choice(range(0, 60, 5)):02d}")
        if item == "time_edge":
            # 23:5x and 00:0x, by turns (beside the near misses 24:51, 23:61)
            late = self.sub_counts["recall_edge"]["late"] <= self.sub_counts["recall_edge"]["early"]
            self.sub_counts["recall_edge"]["late" if late else "early"] += 1
            return "TIME", (f"23:{self.rng.randint(50, 59)}" if late else f"00:0{self.rng.randint(0, 9)}")
        if item == "time_2400":
            return "TIME", "24:00"
        # feb29: a leap year's 29 February, as the noun pairs write dates
        year = self.rng.choice([y for y in range(1948, 2028, 4)])
        style = self.rng.choice(V.DATE_STYLES)
        value = {"dmy": f"29.02.{year}", "iso": f"{year}-02-29"}.get(
            style, f"29 {V.loc('az').months[1]} {year}")
        return "DATE", value

    def _family_recall(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-57 S5/S6 (quotas recall.items, weights per 25k): three or four
        sentences, each a real value the near-miss look-alikes must not teach
        the model to miss -- an access token in prose, a CVV or card
        mid-sentence (thinned in v4.2), a time in `saat X radələrində` (331
        look-alikes against 290 real), 23:5x and 00:0x times, `24:00` (a real
        time, D-57), a leap year's 29 February."""
        rq = self.q["recall"]
        reg = spec["register"]
        n = self.rng.randint(rq["items_min"], rq["items_max"])
        local: collections.Counter = collections.Counter()
        weights = Q._weights(rq["items"])
        items: list[str] = []
        for _ in range(n):
            item = self._deficit({k: v for k, v in weights.items() if k not in items},
                                 self.sub_counts["recall"] + local)
            items.append(item)
            local[item] += 1
        if self.rng.random() < 0.3:
            self._neutral(d, reg, used)
            if items[0] in self.RECALL_LINES:
                d.add("\n")
            else:
                self._sep(d)
        seen: set[str] = set()
        for i, item in enumerate(items):
            if i and item not in self.RECALL_LINES:    # a line item starts its own line
                self._sep(d)
            if item in self.RECALL_PROSE:          # a label's own prose frames
                self._prose_sentence(d, self.RECALL_PROSE[item], used)
                continue
            if item == "key_any":                 # a short key in any of the key layouts
                self._pem_sentence(d, used, spec, key=self.values.private_key_ed25519())
                continue
            if item in ("ipv4_prose", "ipv4_label", "mac_label", "city_label", "surname_label",
                        "given_label", "apikey_label", "fin_label"):
                lab = {"mac_label": "MAC_ADDRESS", "city_label": "CITY", "surname_label": "SURNAME",
                       "given_label": "GIVENNAME", "apikey_label": "API_KEY", "fin_label": "AZ_FIN"}.get(
                    item, "IPV4_ADDRESS")
                v = self._town() if lab == "CITY" else self._mint(lab, "prose")
                if item == "ipv4_prose":
                    t = self._pick_text(d, used, "R.ipv4", V4.NET_PROSE["IPV4_ADDRESS"] + V4.IPV4_BOTH)
                    self._ip_write(d, t, lab, v, spec)
                    continue
                if d.text and not d.text.endswith("\n"):
                    d.add("\n")
                d.add(f"{self.rng.choice(V42.RECALL_FIELDS[lab])}: ")
                d.entity(lab, v)
                d.add("\n")
                continue
            if item == "building_word":
                v = self._mint("BUILDINGNUM", "prose")
                t = self._pick_text(d, used, "R.building_word", V42.RECALL["building_word"])
                write(d, t, {"v": lambda dd, v=v: dd.entity("BUILDINGNUM", v)})
                continue
            if item in ("card_line", "iban_line", "id_line", "surname_line", "key_inline"):
                lab = {"card_line": "PAYMENT_CARD_NUMBER", "iban_line": "IBAN", "id_line": "AZ_ID_CARD_NUMBER",
                       "surname_line": "SURNAME", "key_inline": "PRIVATE_KEY"}[item]
                t = self._pick_text(d, used, f"R.{item}", V42.RECALL[item])
                # The review, E: a family is named by the man's form
                # (`Əsgərov ailəsi`, never `Əsgərova ailəsi`)
                v = (" ".join(self.values.private_key_ed25519().split("\n")) if item == "key_inline"
                     else self._mint(lab, "prose", female=False) if "ailəsi" in t
                     else self._mint(lab, "prose"))
                if item != "key_inline" and d.text and not d.text.endswith("\n"):
                    d.add("\n")                    # the value opens its line
                write(d, t, {"v": lambda dd, lab=lab, v=v: dd.entity(lab, v)})
                if item == "key_inline":
                    d.add("\n")
                continue
            lab, v = self._recall_value(item)
            while v in seen:
                lab, v = self._recall_value(item)
            seen.add(v)
            t = self._pick_text(d, used, f"R.{item}", V42.RECALL[item])
            write(d, t, {"v": lambda dd, lab=lab, v=v: dd.entity(lab, v)})
        if self.rng.random() < 0.4 or d.text.endswith("\n"):
            self._sep(d)
            self._neutral(d, reg, used)
        spec["recall"] = items

    # D-57's last rule: labels whose prose count must not go down (their own frames)
    RECALL_PROSE = {"email_prose": "EMAIL", "passport_prose": "AZ_PASSPORT_NUMBER", "iban_prose": "IBAN",
                    "iccid_prose": "ICCID", "phone_prose": "TELEPHONENUM", "url_prose": "URL",
                    "voen_prose": "AZ_VOEN"}
    # the items written on a line of their own (`Field: value`, a value opening the line)
    RECALL_LINES = frozenset({"ipv4_label", "mac_label", "city_label", "surname_label", "given_label",
                              "apikey_label", "fin_label", "card_line", "iban_line", "id_line", "surname_line"})

    # -- D-57 M2 + item 5: business-like PII-free documents -------------------
    def _screened(self, words: list[str], towns_only: bool = False) -> list[str]:
        """Words none of whose parts is in a pool (or on the blocklist). A
        heading word: no city, settlement or given name. A place-like word
        (`towns_only`): no town of az_cities.txt -- a river, plain or range
        that shares its name with a village (`Kür`, `Muğan`) is the lesson of
        D-57 item 5 itself, a place word that is no city in its context, as a
        town word in a brand name is (D-2)."""
        loc = self.values.loc("az")
        if not hasattr(self, "_pool_words"):
            self._town_words = {w.casefold() for w in loc.cities}
            self._pool_words = self._town_words | {w.casefold() for w in [*SETTLEMENTS, *loc.first_names_m,
                                                                         *loc.first_names_f]}
        pool = self._town_words if towns_only else self._pool_words
        out = []
        for w in words:
            parts = [p for p in re.split(r"[\s\-–]+", w) if p]
            if not any(p.casefold() in pool or is_blocked(p) for p in parts):
                out.append(w)
        return out

    def _geo(self) -> dict[str, list[str]]:
        if not hasattr(self, "_geo_pools"):
            self._geo_pools = {k: self._screened(v, towns_only=True) for k, v in V42.GEO.items()}
            empty = [k for k, v in self._geo_pools.items() if not v]
            if empty:
                raise BuildError(f"geography pools left empty by the screen: {empty}")
        return self._geo_pools

    def _family_pii_free_business(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-57 M2: PII-free documents that look like business documents --
        price lists, stock tables, version histories, meeting notes without
        people, technical specs -- with many numbers and codes (v4.2's
        PII-free documents: median 237 characters, no tables, 0.9 numbers
        each; shadow-dev holds 12.4% PII-free). Item 5: texts about
        geography, routes and regions dense with place-like words that are no
        city (one such shadow document had 15 CITY false alarms). Each may
        carry a near-miss line (M1)."""
        bq = self.q["pii_free_business"]
        kind = self._deficit(Q._weights(bq["kinds"]), self.sub_counts["biz"])
        spec["biz"] = kind
        d.add(self._pick_text(d, used, f"BZ.title.{kind}", V42.BIZ_TITLES[kind]) + "\n")
        getattr(self, f"_biz_{kind}")(d, used, spec)
        if self.rng.random() < bq["near_rate"]:
            self._pf_near(d, used, spec, 1, line_rate=1.0)
        if not d.text.endswith("\n"):
            d.add("\n")
        d.add(self._pick_text(d, used, f"BZ.outro.{kind}", V42.BIZ_OUTROS[kind]))

    _CODE_LETTERS = "ABCDEFGHKLMNPRSTVXYZ"

    def _biz_code(self) -> str:
        return (self.rng.choice(self._CODE_LETTERS) + self.rng.choice(self._CODE_LETTERS)
                + f"-{self.rng.randint(100, 9999)}")

    def _biz_intro(self, d: Draft, used: set[str], kind: str) -> None:
        d.add(self._pick_text(d, used, f"BZ.intro.{kind}", V42.BIZ_INTROS[kind]) + "\n")

    def _biz_price_list(self, d: Draft, used: set[str], spec: dict) -> None:
        self._biz_intro(d, used, "price_list")
        d.add("Məhsul | Kod | Vahid | Qiymət (AZN)\n")
        for p in self.rng.sample(V42.BIZ_PRODUCTS, self.rng.randint(3, 6)):
            d.add(f"{p} | {self._biz_code()} | {self.rng.choice(V42.BIZ_UNITS)} | "
                  f"{self.rng.randint(1, 480)},{self.rng.randint(0, 99):02d}\n")

    def _biz_stock(self, d: Draft, used: set[str], spec: dict) -> None:
        self._biz_intro(d, used, "stock")
        d.add("Məhsul;Anbar;Qalıq;Minimum\n")
        for p in self.rng.sample(V42.BIZ_PRODUCTS, self.rng.randint(3, 6)):
            d.add(f"{p};{self.rng.choice(V42.BIZ_STORES)};{self.rng.randint(0, 900)};"
                  f"{self.rng.choice([10, 20, 25, 50, 100])}\n")

    def _biz_versions(self, d: Draft, used: set[str], spec: dict) -> None:
        """Version numbers are declared `date_version_string` look-alikes."""
        self._biz_intro(d, used, "versions")
        major = self.rng.randint(1, 9)
        minor = self.rng.randint(4, 20)
        kind = self.kinds["date_version_string"]
        for change in self.rng.sample(V42.BIZ_CHANGES, self.rng.randint(3, 5)):
            d.decoy(f"v{major}.{minor}.{self.rng.randint(0, 30)}", kind.kind, kind.resembles)
            d.add(f" — {change}\n")
            minor -= self.rng.randint(1, 2)
            if minor < 0:
                major, minor = max(1, major - 1), self.rng.randint(5, 15)

    _DECISION_NUMBERS = [(2, 90, True), (2, 30, False), (8, 72, False), (1, 50, True), (3, 15, False)]

    def _biz_meeting(self, d: Draft, used: set[str], spec: dict) -> None:
        self._biz_intro(d, used, "meeting")
        depts = self.rng.sample(V42.BIZ_DEPARTMENTS, self.rng.randint(2, 4))
        d.add("İştirak edənlər: " + ", ".join(depts) + ".\nGündəlik:\n")
        for i, item in enumerate(self.rng.sample(V42.BIZ_AGENDA, self.rng.randint(2, 4))):
            d.add(f"{i + 1}. {item}\n")
        d.add("Qərarlar:\n")
        for i in self.rng.sample(range(len(V42.BIZ_DECISIONS)), self.rng.randint(2, 3)):
            lo, hi, thousands = self._DECISION_NUMBERS[i]
            n = self.rng.randint(lo, hi)
            d.add("- " + V42.BIZ_DECISIONS[i].format(n=f"{n} 000" if thousands else n) + "\n")

    _SPEC_VALUES = {
        "Ekranın ölçüsü": lambda r: r.choice(["13,3", "14", "15,6", "17,3", "21,5", "27"]) + " düym",
        "Operativ yaddaş": lambda r: f"{r.choice([4, 8, 16, 32, 64])} GB",
        "Çəki": lambda r: f"{r.randint(1, 30)},{r.randint(0, 9)} kq",
        "Gərginlik": lambda r: f"{r.choice([12, 24, 110, 220, 380])} V",
        "Güc": lambda r: f"{r.randint(20, 2000)} Vt",
        "Zəmanət müddəti": lambda r: f"{r.choice([6, 12, 24, 36])} ay",
        "Prosessorun nüvələri": lambda r: str(r.choice([2, 4, 6, 8, 12, 16])),
        "Batareyanın tutumu": lambda r: f"{r.randint(1500, 6000)} mAh",
        "Rəng": lambda r: r.choice(["mavi", "qara", "ağ", "gümüşü"]),
        "Material": lambda r: r.choice(["alüminium", "plastik", "polad"]),
        "Hündürlük": lambda r: f"{r.randint(10, 250)} sm",
        "Eni": lambda r: f"{r.randint(10, 250)} sm",
    }

    def _biz_spec(self, d: Draft, used: set[str], spec: dict) -> None:
        self._biz_intro(d, used, "spec")
        d.add(f"Model kodu: {self._biz_code()}\n")
        for field in self.rng.sample([f for f, _v in V42.BIZ_SPEC], self.rng.randint(4, 6)):
            d.add(f"{field}: {self._SPEC_VALUES[field](self.rng)}\n")

    def _biz_geography(self, d: Draft, used: set[str], spec: dict) -> None:
        """3-5 sentences, each with one to three place-like words (declared
        `place_word_topic`, unlabelled) and drawn numbers."""
        geo = self._geo()
        numbers = {"km": lambda: self.rng.randint(150, 3500), "h": lambda: self.rng.randint(1000, 5640),
                   "pct": lambda: self.rng.randint(2, 40), "n": lambda: self.rng.randint(10, 900)}
        sentences = self.rng.sample(range(len(V42.GEO_SENTENCES)), self.rng.randint(3, 5))
        places = 0
        for j, i in enumerate(sentences):
            fid = f"BZ.geo.{i}"
            used.add(fid)
            d.frame_ids.append(fid)
            t = V42.GEO_SENTENCES[i]
            writers = {}
            region = None
            for key in re.findall(r"\{(\w+)\}", t):
                if key in numbers:
                    writers[key] = lambda dd, f=numbers[key]: dd.add(str(f()))
                else:
                    # The review, G: never a country inside the sentence's region
                    pool = ([c for c in geo[key] if c not in V42.GEO_REGION_MEMBERS.get(region, ())]
                            if key == "c" else geo[key])
                    word = self.rng.choice(pool)
                    if key == "g":
                        region = word
                    writers[key] = lambda dd, w=word: dd.decoy(w, PLACE_WORD.kind, PLACE_WORD.resembles)
                    places += 1
            if j:
                d.add(" ")
            write(d, t, writers)
        spec["place_words"] = places

    # -- D-51h: the v4 targeted families ------------------------------------
    def _pair(self, d: Draft, reg: str, used: set[str], halves: list[Callable[[Draft], None]]) -> None:
        """Two halves (a real value and a look-alike) in either order, with a
        bridging sentence or a neutral one between them (`_between`)."""
        if self.rng.random() < 0.5:
            halves = halves[::-1]
        halves[0](d)
        self._between(d, reg, used, bridge=True)
        halves[1](d)

    def _town(self, consonant_final: bool = False) -> str:
        """A town from az_cities.txt (never a village: these sentences say
        `şəhər`, D-43c), drawn fresh through the value pool."""
        towns = self.values.loc("az").cities
        if consonant_final:
            towns = [t for t in towns if t[-1].lower() not in SFX.VOWELS]
        return self.values.pool.fresh("CITY", lambda: self.rng.choice(towns))

    def _family_cross_anchor(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h items 1-2 (v3 coverage report, section 5): a valid-looking
        shape in ANOTHER label's slot -- short numbers after VÖEN/FİN/vəsiqə/
        token/API-key words, company names and codes after soyad/şəhər/küçə,
        room and door numbers named a `kod`, MAC fragments, IBAN fragments,
        IPv4 look-alikes, ZIP-shaped product codes -- unlabelled, beside a
        real value of the label the slot or the shape suggests."""
        cq = self.q["cross_anchor"]
        sub = self._deficit(Q._weights(cq["subs"]), self.sub_counts["cross_anchor"])
        spec["cross_slot"] = sub
        reg = spec["register"]
        if self.rng.random() < 0.35:
            self._neutral(d, reg, used)
            self._sep(d)
        getattr(self, f"_cross_{sub}")(d, used, spec)
        if self.rng.random() < 0.4:
            self._sep(d)
            self._neutral(d, reg, used)

    def _two_records(self, d: Draft, used: set[str], field: str,
                     fills: list[Callable[[Draft], None]]) -> None:
        """Two records, each a `Field: value` line and a status line."""
        d.add(self._pick_text(d, used, "X.records.intro", V4.RECORD_INTROS) + "\n")
        heads = self.rng.choice(V4.RECORD_HEADS)
        for i, (head, fill) in enumerate(zip(heads, fills)):
            if i:
                d.add("\n\n")
            d.add(f"{head}\n{field}: ")
            fill(d)
            d.add(f"\nStatus: {self.rng.choice(V4.RECORD_STATUS)}")

    def _cross_short_number(self, d: Draft, used: set[str], spec: dict) -> None:
        cq = self.q["cross_anchor"]
        lab = self._deficit(Q._weights(cq["short_labels"]), self.sub_counts["short_label"])
        kind = self.kinds[SHORT_KIND[lab]]
        fake = self._decoy_value(kind)
        real = self._mint(lab, "prose")
        formats = Q._weights(cq["short_formats"]) if lab in V4.SHORT_KEYS else {"prose": 1.0}
        fmt = self.rng.choices(sorted(formats), weights=[formats[k] for k in sorted(formats)])[0]
        spec.update(short_label=lab, short_format=fmt)
        put_real = lambda dd: dd.entity(lab, real)                       # noqa: E731
        put_fake = lambda dd: dd.decoy(fake, kind.kind, lab)             # noqa: E731
        reg = spec["register"]
        if fmt == "prose":
            t = self._pick_text(d, used, f"X.short.{lab}", V4.SHORT_BOTH[lab])
            t2 = (self._pick_text(d, used, f"X.short_only.{lab}", V4.SHORT_ONLY[lab])
                  if self.rng.random() < cq["short_only_rate"] else t)
            self._pair(d, reg, used, [lambda dd: write(dd, t, {"v": put_real}),
                                      lambda dd: write(dd, t2, {"v": put_fake})])
            return
        az, snake = V4.SHORT_KEYS[lab]
        fills = [put_real, put_fake]
        self.rng.shuffle(fills)
        if fmt == "kv":
            self._two_records(d, used, self.rng.choice(az), fills)
            return
        # a CSV column: three rows, one of them the short number
        sep = self.rng.choice([",", ",", ";"])
        d.add(self._pick_text(d, used, "FMT.intro.table", FMT.INTROS["table"]) + "\n")
        d.add(f"{self.rng.choice(snake)}{sep}status\n")
        rows = [put_real, lambda dd: dd.entity(lab, self._mint(lab, "container"))]
        rows.insert(self.rng.randint(0, 2), put_fake)
        for fill in rows:
            fill(d)
            d.add(f"{sep}{self.rng.choice(V4.RECORD_STATUS[:4])}\n")
        self._neutral(d, reg, used)

    def _cross_name_org(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-2 in the name slot: `soyad kimi <Surname> MMC / KRM482`, `şəhər
        olaraq <City> layihəsi`, `küçə kimi <name> haqqında kitab`, next to
        a real surname, town or street in the same sentence."""
        cq = self.q["cross_anchor"]
        lab = self._deficit(Q._weights(cq["name_labels"]), self.sub_counts["name_label"])
        kinds = NAME_SLOT_KINDS[lab]
        kname = self.rng.choices([k for k, _w in kinds], weights=[w for _k, w in kinds])[0]
        kind = self.kinds[kname]
        fake = self._decoy_value(kind)
        for _ in range(20):
            real = self._town() if lab == "CITY" else self._mint(lab, "prose")
            if real not in fake and fake not in real:
                break
        spec.update(name_label=lab, name_kind=kname)
        put_real = lambda dd: dd.entity(lab, real)                       # noqa: E731
        put_fake = lambda dd: dd.decoy(fake, kind.kind, lab)             # noqa: E731
        if self.rng.random() < cq["name_kv_rate"]:
            fills = [put_real, put_fake]
            self.rng.shuffle(fills)
            self._two_records(d, used, self.rng.choice(V4.NAME_SLOT_KEYS[lab]), fills)
            spec["name_format"] = "kv"
            return
        t = self._pick_text(d, used, f"X.name.{lab}", V4.NAME_SLOT[lab])
        self._pair(d, spec["register"], used, [lambda dd: write(dd, t, {"v": put_real}),
                                               lambda dd: write(dd, t, {"v": put_fake})])

    def _cross_room_code(self, d: Draft, used: set[str], spec: dict) -> None:
        """A room or door number named a `kod` (contextual look-alike of a CVV)
        and a real CVV in the same document."""
        door = self.rng.random() < 0.4
        kind = self.kinds["door_code" if door else "room_code"]
        code = self._decoy_value(kind)
        cvv = self._mint("CARD_SECURITY_CODE", "pair")
        while cvv == code:
            cvv = self._mint("CARD_SECURITY_CODE", "pair")
        t = self._pick_text(d, used, "X.door" if door else "X.room", V4.DOOR_CODE if door else V4.ROOM_CODE)
        c = self._pick_text(d, used, "P.cvv", CVV_FRAMES)
        spec["room_kind"] = kind.kind
        self._pair(d, spec["register"], used, [
            lambda dd: write(dd, t, {"v": lambda x: x.decoy(code, kind.kind, kind.resembles)}),
            lambda dd: write(dd, c, {"v": lambda x: x.entity("CARD_SECURITY_CODE", cvv)})])

    def _cross_mac_fragment(self, d: Draft, used: set[str], spec: dict) -> None:
        kind = self.kinds["mac_fragment_dashed"]
        mac = self._mint("MAC_ADDRESS", "prose")
        frag = self._decoy_value(kind)
        while frag.lower() in mac.lower():
            frag = self._decoy_value(kind)
        t = self._pick_text(d, used, "X.mac", V4.MAC_FRAGMENT)
        r = self._pick_text(d, used, "X.mac_real", V4.MAC_REAL)
        self._pair(d, spec["register"], used, [
            lambda dd: write(dd, t, {"v": lambda x: x.decoy(frag, kind.kind, kind.resembles)}),
            lambda dd: write(dd, r, {"v": lambda x: x.entity("MAC_ADDRESS", mac)})])

    def _cross_iban_fragment(self, d: Draft, used: set[str], spec: dict) -> None:
        """`AZ37NAB` (iban_fragment_short) or a ZIP-shaped `AZ1234`
        (zip_shape_in_iban_field) after IBAN/hesab words, in prose or in a
        CSV `iban` column, beside real IBANs."""
        cq = self.q["cross_anchor"]
        # balanced within this family: `iban_fragment_short` is also drawn by
        # other families, so a global least-used choice left it 1 of 90 here
        kname = self._deficit({"iban_fragment_short": 1.0, "zip_shape_in_iban_field": 1.0},
                              self.sub_counts["iban_kind"])
        kind = self.kinds[kname]
        frag = self._decoy_value(kind)
        put_fake = lambda dd: dd.decoy(frag, kind.kind, kind.resembles)  # noqa: E731
        spec["iban_kind"] = kind.kind
        if self.rng.random() < cq["iban_csv_rate"]:
            spec["iban_format"] = "csv"
            sep = self.rng.choice([",", ";"])
            other = self.rng.choice(["GIVENNAME", "SURNAME", None])
            d.add(self._pick_text(d, used, "FMT.intro.table", FMT.INTROS["table"]) + "\n")
            col = self.rng.choice(V4.IBAN_COLUMNS)
            d.add((f"{FMT.field_name(other, 'csv_snake', self.rng)}{sep}" if other else "")
                  + f"{col}{sep}status\n")
            rows: list = [lambda dd: dd.entity("IBAN", self._mint("IBAN", "container")) for _ in range(2)]
            rows.insert(self.rng.randint(0, 2), put_fake)
            for fill in rows:
                if other:
                    d.entity(other, self._mint(other, "container"))
                    d.add(sep)
                fill(d)
                d.add(f"{sep}{self.rng.choice(V4.RECORD_STATUS[:4])}\n")
            self._neutral(d, spec["register"], used)
            return
        iban = self._mint("IBAN", "prose")
        t = self._pick_text(d, used, "X.iban", V4.IBAN_FRAGMENT)
        r = self._pick_text(d, used, "X.iban_real", V4.IBAN_REAL)
        self._pair(d, spec["register"], used, [lambda dd: write(dd, t, {"v": put_fake}),
                                               lambda dd: write(dd, r, {"v": lambda x: x.entity("IBAN", iban)})])

    def _cross_ipv4(self, d: Draft, used: set[str], spec: dict) -> None:
        """An IPv4 look-alike and, in the same document, its valid twin of the
        same pattern (`9.9.9.999` / `9.9.9.99`, `1.2.3.x` / `1.2.3.4`), so
        only the invalid part tells them apart; often a second real IPv4 too.
        v4.1 (#91 items 2-3): the look-alike is never written in
        the real value's sentence, and real values outnumber look-alikes."""
        kind = self._least_used_kind([self.kinds[k] for k in IPV4_KINDS])
        fake = self._decoy_value(kind)
        twin = self._ipv4_twin(fake, kind.kind) or self.values.ipv4_one_digit()
        t = self._pick_text(d, used, "X.ipv4", V4.IPV4_BOTH)
        t2 = (self._pick_text(d, used, "X.ipv4_placeholder", V4.IPV4_PLACEHOLDER)
              if kind.kind == "ipv4_placeholder" and self.rng.random() < 0.5
              else self._pick_text(d, used, "X.ipv4_lookalike", V4.IPV4_LOOKALIKE))
        spec.update(ipv4_kind=kind.kind, ipv4_reals=1)
        self._pair(d, spec["register"], used, [
            lambda dd: self._ip_write(dd, t, "IPV4_ADDRESS", twin, spec),
            lambda dd: write(dd, t2, {"v": lambda x: x.decoy(fake, kind.kind, kind.resembles)})])
        if self.rng.random() < self.q["ipv4"]["second_real_rate"]:
            real = self._mint("IPV4_ADDRESS", "prose")
            while real == twin:
                real = self._mint("IPV4_ADDRESS", "prose")
            t3 = self._pick_text(d, used, "X.ipv4", V4.IPV4_BOTH, avoid=(t,))
            self._between(d, spec["register"], used, bridge=True)
            self._ip_write(d, t3, "IPV4_ADDRESS", real, spec)
            spec["ipv4_reals"] = 2

    def _ip_write(self, d: Draft, t: str, lab: str, v: str, spec: dict) -> None:
        """D-56a (1): an IP sentence that sometimes ends without a period --
        with `;` or nothing -- and then the line ends (v4.1 split IPs there:
        every IP the targeted data added ended with `.`)."""
        end = self._ip_end()
        if end == ".":
            write(d, t, {"v": lambda x: x.entity(lab, v)})
            return
        write(d, t[:-1] + (";" if end == "semicolon" else ""), {"v": lambda x: x.entity(lab, v)})
        d.add("\n")
        spec.setdefault("ip_ends", []).append(end)

    def _ip_end(self) -> str:
        r = self.rng.random()
        rate = self.q["ipv4"]["open_end_rate"]
        if r >= rate:
            return "."
        return "semicolon" if r < rate / 2 else "bare"

    def _ipv4_twin(self, fake: str, kind: str) -> str | None:
        """The valid IPv4 a look-alike would be without its invalid part:
        an octet over 255 loses its last digit, a wildcard becomes a digit, a
        fifth part is dropped, a missing fourth part is added."""
        parts = fake.split(".")
        if kind == "ipv4_three_octets":
            parts.append(str(self.rng.randint(1, 9)))
        parts = parts[:4]
        parts = [str(self.rng.randint(0, 9)) if p in ("x", "X", "*") else p for p in parts]
        fixed = []
        for p in parts:
            n = int(p)
            while n > 255:
                n //= 10
            fixed.append(str(n))
        if fixed[-1] == "0":
            fixed[-1] = str(self.rng.randint(1, 9))
        if fixed[0] == "0":
            fixed[0] = str(self.rng.randint(1, 9))
        twin = ".".join(fixed)
        if twin == fake or not value_valid("IPV4_ADDRESS", twin)[0] or is_blocked(twin) or is_forbidden(twin):
            return None
        return twin

    def _cross_zip_code(self, d: Draft, used: set[str], spec: dict) -> None:
        """Right context: the same `indeks kimi ...` sentence with a real ZIP,
        and with a ZIP-shaped code that the next words make a product code."""
        kind = self.kinds["zip_shape_as_code"]
        code = self._decoy_value(kind)
        z = self.values.zipcode_any_az()
        while z == code:
            z = self.values.zipcode_any_az()
        t = self._pick_text(d, used, "X.zip", V4.ZIP_RIGHT)
        tail = self.rng.choice(V4.ZIP_TAILS)
        self._pair(d, spec["register"], used, [
            lambda dd: write(dd, t, {"v": lambda x: x.entity("ZIPCODE", z), "tail": lambda x: None}),
            lambda dd: write(dd, t, {"v": lambda x: x.decoy(code, kind.kind, kind.resembles),
                                     "tail": lambda x: x.add(tail)})])

    def _family_locative(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h item 3: a value mid-sentence after a document noun in the
        locative, as the last argument before the verb (`Ödəniş səhifəsində
        ⟨card⟩ görünür`), for cards, VÖENs, ID cards, passports and IBANs.
        v3 missed ~100 cards and 27 VÖENs there (exact frames: 0 in
        training). Some documents also hold a look-alike of the same label in
        the same sentence, one whose length or format shows it."""
        lq = self.q["locative"]
        reg = spec["register"]
        weights = Q._weights(lq["label_weights"])
        labels = [self._deficit(weights, self.sub_counts["locative_label"])]
        if self.rng.random() < lq["second_rate"]:
            labels.append(self.rng.choice([lab for lab in sorted(weights) if lab != labels[0]]))
        if self.rng.random() < 0.35:
            self._neutral(d, reg, used)
            self._sep(d)
        spec["locative"] = labels
        for i, lab in enumerate(labels):
            if i:
                self._sep(d)
            t = self._pick_text(d, used, f"LO.{lab}", V4.LOCATIVE[lab])
            value = self._mint(lab, "clerical" if lab == "PAYMENT_CARD_NUMBER" else "prose")
            fill = lambda dd, lab=lab, value=value: dd.entity(lab, value)   # noqa: E731
            if i == 0 and self.rng.random() < lq["look_alike_rate"]:
                kind = self._least_used_kind([self.kinds[k] for k in V4.LOCATIVE_KINDS[lab]])
                fake = self._decoy_value(kind)
                spec["locative_look_alike"] = kind.kind
                self._pair(d, reg, used, [
                    lambda dd, t=t, fill=fill: write(dd, t, {"v": fill}),
                    lambda dd, t=t, kind=kind, fake=fake: write(
                        dd, t, {"v": lambda x: x.decoy(fake, kind.kind, kind.resembles)})])
            else:
                write(d, t, {"v": fill})
        if self.rng.random() < 0.5:
            self._sep(d)
            self._neutral(d, reg, used)

    def _family_slot_invalid(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h item 9 (C4: decoy_time, decoy_age, decoy_date, decoy_fin,
        decoy_card_iccid_iban): an invalid value directly after its label word
        -- an hour over 23 or a minute over 59, a negative or implausible age,
        an impossible date, a hyphenated FIN, a card of the wrong length --
        in a `label: value` line or in prose, and a valid value in the same
        frame."""
        sq = self.q["slot_invalid"]
        reg = spec["register"]
        lab = self._deficit(Q._weights(sq["label_weights"]), self.sub_counts["slot_label"])
        if lab == "ZIPCODE":
            # v4.1: the 2-digit number after a ZIP word (#80) and the protected
            # zip_wrong_length (D-52d) take turns 1 : 1 in this slot
            name = self._deficit({k: 1.0 for k in V4.SLOT_KINDS[lab]}, self.sub_counts["slot_zip_kind"])
            self.sub_counts["slot_zip_kind"][name] += 1
            kind = self.kinds[name]
        else:
            kind = self._least_used_kind([self.kinds[k] for k in V4.SLOT_KINDS[lab]])
        fake = self._decoy_value(kind)
        prose = self.rng.random() < sq["prose_rate"]
        real = self._mint(lab, "prose" if prose else "container")
        while real == fake:
            real = self._mint(lab, "prose" if prose else "container")
        spec.update(slot_label=lab, slot_kind=kind.kind, slot_format="prose" if prose else "kv")
        put_real = lambda dd: dd.entity(lab, real)                       # noqa: E731
        put_fake = lambda dd: dd.decoy(fake, kind.kind, lab)             # noqa: E731
        if prose:
            if self.rng.random() < 0.35:
                self._neutral(d, reg, used)
                self._sep(d)
            t = self._pick_text(d, used, f"SI.{lab}", V4.SLOT_PROSE[lab])
            self._pair(d, reg, used, [lambda dd: write(dd, t, {"v": put_real}),
                                      lambda dd: write(dd, t, {"v": put_fake})])
            if self.rng.random() < 0.4:
                self._sep(d)
                self._neutral(d, reg, used)
            return
        self._neutral(d, reg, used)
        d.add("\n")
        fills = [put_real, put_fake]
        self.rng.shuffle(fills)
        self._two_records(d, used, self.rng.choice(FORM_FIELDS[lab]), fills)

    def _family_place_verbs(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h item 7 (`suffixed_entities`: CITY copula 0/7, instrumental
        0/4, accusative after a consonant 0/3, SURNAME ablative 0/4): a town
        with the copula, the instrumental, the accusative after a consonant or
        the ablative, in sentences whose verbs also take people, a second
        clause saying it is the place; and a surname in the ablative. The
        suffix is inside the span (D-9)."""
        pq = self.q["place_verbs"]
        reg = spec["register"]
        cases = Q._weights(pq["case_weights"])
        items = [self._deficit(cases, self.sub_counts["place_case"] + collections.Counter())]
        if self.rng.random() < pq["second_city_rate"]:
            items.append(self.rng.choice([c for c in sorted(cases) if c != items[0]]))
        if self.rng.random() < pq["surname_rate"]:
            items.insert(self.rng.randint(0, len(items)), "surname")
        spec["place_verbs"] = items
        if self.rng.random() < 0.3:
            self._neutral(d, reg, used)
            self._sep(d)
        for i, item in enumerate(items):
            if i:
                self._sep(d)
            if item == "surname":
                t = self._pick_text(d, used, "PV.surname", V4.SURNAME_ABLATIVE)
                value, inflected = self._mint_inflectable("SURNAME", "abl")
                word, stem, surface = self._surface("SURNAME", value, inflected, "abl")
                write(d, t, {"v": lambda dd, w=word, n=stem, f=surface: dd.suffixed("SURNAME", w, n, "abl", f)})
                continue
            t = self._pick_text(d, used, f"PV.{item}", V4.PLACE_VERBS[item])
            if item == "ins" and self.rng.random() < pq["ins_separate_rate"]:
                city = self._town()
                write(d, t, {"v": lambda dd, c=city: (dd.entity("CITY", c), dd.add(" ilə"))})
                spec.setdefault("ins_separate", 0)
                spec["ins_separate"] += 1
                continue
            for _ in range(20):
                city = self._town(consonant_final=item == "acc")
                try:
                    inflected = self._inflect(city, item, "CITY")
                    break
                except SFX.NotInflectable:
                    continue
            else:
                raise BuildError(f"place_verbs: no town takes {item} in 20 draws")
            word, stem, surface = self._surface("CITY", city, inflected, item)
            write(d, t, {"v": lambda dd, w=word, n=stem, f=surface, c=item: dd.suffixed("CITY", w, n, c, f)})
        if self.rng.random() < 0.4:
            self._sep(d)
            self._neutral(d, reg, used)

    def _family_short_keys(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h item 5: short Ed25519 private keys (PKCS#8, `MC4CAQAw...`),
        often several in one document and sometimes beside an Ed25519 public
        key (a look-alike), so private keys outnumber the public look-alikes
        at least three to one (v3: 166 short public look-alikes vs 77 short
        private keys; the model split private keys at the header)."""
        kq = self.q["short_keys"]
        reg = spec["register"]
        n = self.rng.choices([1, 2, 3], weights=kq["keys_weights"])[0]
        items = ["private"] * n
        if self.rng.random() < kq["public_rate"]:
            items.insert(self.rng.randint(0, n), "public")
        spec["with_private"] = True
        spec["short_keys"] = items
        if n > 1:                       # the intros speak of several keys
            d.add(self._pick_text(d, used, "SK.intro", V4.KEY_SET_INTROS) + "\n")
        for i, item in enumerate(items):
            if i:
                d.add("\n")
            if item == "private":
                self._pem_sentence(d, used, spec, key=self.values.private_key_ed25519())
            else:
                self._public_key_sentence(d, used, spec, key=public_key_ed25519(self.value_rng))
        self._top_up(d, reg, used)

    def _cvv_csv(self, d: Draft, used: set[str], spec: dict) -> None:
        """D-51h item 8: a CSV table with a `cvv` column -- mostly beside a
        `şəxsiyyət_vəsiqəsi` column -- and bare row values. v3's training held
        20 CVVs in CSV rows; CSV recall was its lowest category. A CVV needs
        its `cvv` header within 80 characters (anchors.has_anchor), so the
        column comes first or second and the table keeps the rows whose CVV
        the header still licenses (at least one)."""
        sq = self.q["structured"]
        fmt = self.rng.choice(("csv_header", "csv_snake"))
        spec["format"] = fmt
        spec["cvv_rows"] = True
        columns = ["CARD_SECURITY_CODE"]
        if self.rng.random() < sq["cvv_csv_id_rate"]:
            columns.append("AZ_ID_CARD_NUMBER")
        extra = self.rng.sample(["GIVENNAME", "SURNAME", "PAYMENT_CARD_NUMBER", "TELEPHONENUM"],
                                self.rng.randint(0, 2))
        columns += extra
        first = columns[:2]
        self.rng.shuffle(first)
        columns = first + columns[2:]
        rows = [self._container_row(columns, fmt) for _ in range(3)]
        if self.rng.random() < sq["cvv_csv_decoy_rate"]:
            r = self.rng.randrange(3)
            c = self.rng.choice([i for i, lab in enumerate(columns)
                                 if lab in ("CARD_SECURITY_CODE", "AZ_ID_CARD_NUMBER")])
            lab = columns[c]
            kind = self._least_used_kind([k for k in self.kinds.values() if k.resembles == lab
                                          and not k.contextual and not k.policy])
            rows[r][c] = ("decoy", lab, self._decoy_value(kind), kind.kind)
        pick = lambda items: self._pick_frame(items, used, fid=lambda x: x[0])   # noqa: E731
        state = self.rng.getstate()
        for n_rows in (3, 2, 1):
            self.rng.setstate(state)
            d2 = Draft()
            fids = FMT.render(fmt, d2, columns, rows[:n_rows], self.rng, pick)
            if all(has_anchor(e["label"], d2.text, e["start"], e["end"]) for e in d2.entities
                   if e["label"] == "CARD_SECURITY_CODE"):
                break
        spec["columns"] = columns
        spec["cvv_rows_n"] = n_rows
        self._neutral(d, spec["register"], used)
        d.add("\n")
        _append(d, d2)
        for fid in fids:
            used.add(fid)
            d.frame_ids.append(fid)

    # -- one document -----------------------------------------------------
    # -- TIME with seconds (v3_shadow_shapes.md lead 1) ---------------------
    def _family_time_seconds(self, d: Draft, used: set[str], spec: dict) -> None:
        """v3 missed 72 of 80 `99:99:99` times on shadow-dev: the data had
        seconds only inside unlabelled date+time and line stamps (D-17,
        D-51f). Labelled times with seconds -- `saat 14:05:22` in prose,
        `Saat: 14:05:22` fields, ranges `14:00:00-15:30:00` / `14:00:00 –
        15:30` (both ends TIME, as v4_clean R10) or a time inside a chat line
        -- and, in the same document, chat or log line stamps with seconds
        that stay unlabelled (`time_line_stamp`)."""
        tq = self.q["time_seconds"]
        reg = spec["register"]
        sub = self._deficit(Q._weights(tq["sub_weights"]), self.sub_counts["time_seconds"])
        spec.update(time_sub=sub, time_stamps=0)
        if self.rng.random() < 0.35:
            self._neutral(d, reg, used)
            d.add("\n")
        if sub == "chat":
            self._ts_stamps(d, used, spec, real=True)
        else:
            parts = [lambda dd: self._ts_real(dd, used, sub, spec)]
            if self.rng.random() < tq["stamp_rate"]:
                parts.append(lambda dd: self._ts_stamps(dd, used, spec))
            self.rng.shuffle(parts)
            for i, part in enumerate(parts):
                if i:
                    d.add("\n\n")
                part(d)
        if self.rng.random() < 0.3:
            d.add("\n")
            self._neutral(d, reg, used)

    def _ts_value(self) -> str:
        return self.values.time_with_seconds()

    def _ts_range(self, d: Draft, suffixed: bool = False) -> None:
        """`14:00:00-15:30:00`, `14:00:00 – 15:30`: both ends TIME. v4.2: also
        `14:00:00–15:30:00` and `14:00:00 — 15:30:00`; with `suffixed`, the
        case endings Azerbaijani ranges take, outside the spans
        (`14:00:00-dan 15:30:00-dək`, `14:05:22-dən 16:00:00-a qədər`)."""
        tq = self.q["time_seconds"]
        step = 900 if self.rng.random() < tq["range_round_rate"] else 1
        a = self.values.time_with_seconds(6 * 3600, 20 * 3600, step)
        h, m, s = (int(x) for x in a.split(":"))
        start = h * 3600 + m * 60 + s
        b = self.values.time_with_seconds(start + 900, min(start + 6 * 3600, 86399), step,
                                          seconds=self.rng.random() >= tq["range_short_end_rate"])
        d.entity("TIME", a)
        if suffixed:
            d.add(time_case_suffix(a, "abl") + " ")
            d.entity("TIME", b)
            d.add("-dək" if self.rng.random() < 0.5 else time_case_suffix(b, "dat") + " qədər")
            return
        sep = self.rng.choices(["-", " – ", " - ", "–", " — "], weights=[0.35, 0.3, 0.15, 0.12, 0.08])[0]
        d.add(sep)
        d.entity("TIME", b)

    def _ts_agenda(self, d: Draft, used: set[str]) -> None:
        """v4.2: an agenda, 3-5 lines that open with a range (`09:00 – 09:30
        — Qeydiyyat`). The range starts the line like a chat stamp, but both
        ends are TIME: a stamp marks when a line was written. Native review C:
        consecutive ranges (each starts where the last ended), items in
        programme order from registration or the opening to `Yekun söz`,
        hh:mm."""
        d.add(self._pick_text(d, used, "TS.agenda", V4.TIME_AGENDA_INTROS) + "\n")
        n = self.rng.randint(3, 5)
        middle = sorted(self.rng.sample(range(len(V4.TIME_AGENDA_MIDDLE)), n - 2))
        items = ([self.rng.choice(V4.TIME_AGENDA_FIRST)] + [V4.TIME_AGENDA_MIDDLE[i] for i in middle]
                 + [V4.TIME_AGENDA_LAST])
        start = self.rng.choice([9 * 60, 9 * 60 + 30, 10 * 60, 14 * 60])
        sep = self.rng.choices(["-", " – ", " - ", "–"], weights=[0.35, 0.35, 0.15, 0.15])[0]
        tail = self.rng.choice([" — ", " ", ": "])
        # each item a length it takes; lunch only when it starts 12:00-13:59
        # (else a coffee break, if the programme has none yet)
        lengths = {"Qeydiyyat": (15, 30), "Açılış nitqi": (15, 30), "Kofe fasiləsi": (15, 30),
                   "Nahar fasiləsi": (60,), "Yekun söz": (15, 30)}
        first = True
        for item in items:
            if item == "Nahar fasiləsi" and not 12 * 60 <= start < 14 * 60:
                if "Kofe fasiləsi" in items:
                    continue
                item = "Kofe fasiləsi"
            if not first:
                d.add("\n")
            first = False
            end = start + self.rng.choice(lengths.get(item, (30, 45, 60, 90)))
            d.entity("TIME", f"{start // 60:02d}:{start % 60:02d}")
            d.add(sep)
            d.entity("TIME", f"{end // 60:02d}:{end % 60:02d}")
            d.add(tail + item)
            start = end

    def _ts_real(self, d: Draft, used: set[str], sub: str, spec: dict | None = None) -> None:
        if sub == "prose":
            t = self._pick_text(d, used, "TS.prose", V4.TIME_SECONDS_PROSE)
            v = self._ts_value()
            write(d, t, {"v": lambda dd: dd.entity("TIME", v)})
            return
        tq = self.q["time_seconds"]
        if sub == "range" and self.rng.random() < tq.get("range_agenda_rate", 0.0):
            # an agenda (hh:mm, native review C) comes on top of the range with
            # seconds, which this family is for, not in its place
            self._ts_agenda(d, used)
            if spec is not None:
                spec["time_agenda"] = True
            d.add("\n\n")
        suffixed = sub == "range" and self.rng.random() < tq.get("range_suffix_rate", 0.0)
        if sub == "range" and self.rng.random() < tq["range_prose_rate"]:
            if suffixed:
                t = self._pick_text(d, used, "TS.range_sfx", V4.TIME_RANGE_SUFFIX_PROSE)
                write(d, t, {"r": lambda dd: self._ts_range(dd, suffixed=True)})
            else:
                t = self._pick_text(d, used, "TS.range", V4.TIME_RANGE_PROSE)
                write(d, t, {"r": self._ts_range})
            return
        d.add(self._pick_text(d, used, "TS.intro", V4.TIME_SECONDS_INTROS) + "\n")
        if sub == "range":
            for i, field in enumerate(self.rng.sample(V4.TIME_RANGE_FIELDS, self.rng.randint(1, 2))):
                if i:
                    d.add("\n")
                d.add(f"{field}: ")
                self._ts_range(d, suffixed=suffixed)
            return
        heads = self.rng.choice(V4.RECORD_HEADS)
        for i in range(self.rng.randint(1, 2)):
            if i:
                d.add("\n\n")
            field = "Saat" if self.rng.random() < 0.5 else self.rng.choice(V4.TIME_SECONDS_FIELDS[1:])
            d.add(f"{heads[i]}\n{field}: ")
            d.entity("TIME", self._ts_value())
            d.add(f"\nStatus: {self.rng.choice(V4.RECORD_STATUS)}")

    def _ts_stamps(self, d: Draft, used: set[str], spec: dict, real: bool = False) -> None:
        """2-4 chat or log lines, each opening with a stamp (a declared
        look-alike, unlabelled); with `real`, one agent line holds a labelled
        time (`[14:05:22] Operator: Ödənişiniz saat 14:03:10 olaraq ...`)."""
        tq = self.q["time_seconds"]
        n = self.rng.randint(2, 4)
        style = self.rng.choice(["bracket", "dash", "log"] if not real else ["bracket", "dash"])
        roles = self.rng.choice(V4.STAMP_ROLES)
        agent = self.rng.sample(V4.STAMP_AGENT_LINES, n)
        customer = self.rng.sample(V4.STAMP_CUSTOMER_LINES, n)
        logs = self.rng.sample(V4.STAMP_LOG_LINES, n)
        at = 2 * self.rng.randint(0, (n - 1) // 2) if real else -1       # an agent line
        t = self.rng.randint(7 * 3600, 21 * 3600)
        with_seconds = self.rng.random() >= tq["stamp_no_seconds_rate"]
        bracket_log = self.rng.random() < 0.5
        for i in range(n):
            if i:
                d.add("\n")
            stamp = self._stamp_value(t, with_seconds)
            t += self.rng.randint(5, 240)
            put = lambda dd, s=stamp: dd.decoy(s, TIME_LINE_STAMP.kind, "TIME")   # noqa: E731
            agent_turn = i % 2 == 0
            role = roles[0] if agent_turn else roles[1]
            if style == "log":
                if bracket_log:
                    d.add("[")
                    put(d)
                    d.add("]")
                else:
                    put(d)
                d.add(" {} {}".format(*logs[i]))
            else:
                if style == "bracket":
                    d.add("[")
                    put(d)
                    d.add(f"] {role}: ")
                else:
                    put(d)
                    d.add(f" - {role}: ")
                if i == at:
                    tt = self._pick_text(d, used, "TS.chat", V4.TIME_SECONDS_CHAT)
                    v = self._ts_value()
                    write(d, tt, {"v": lambda dd: dd.entity("TIME", v)})
                else:
                    d.add(agent[i] if agent_turn else customer[i])
            spec["time_stamps"] += 1

    def _stamp_value(self, t: int, seconds: bool) -> str:
        """A line stamp at `t` seconds after midnight (a look-alike, so not
        drawn through the value pool), never a benchmark or shadow value."""
        for _ in range(50):
            h, m, s = t // 3600 % 24, t % 3600 // 60, t % 60
            v = f"{h:02d}:{m:02d}:{s:02d}" if seconds else f"{h:02d}:{m:02d}"
            if not is_forbidden(v):
                return v
            t += self.rng.randint(1, 30)
        return v

    # -- v4.1 (A5): private-key blocks with a placeholder body ----------------
    def _family_key_placeholder(self, d: Draft, used: set[str], spec: dict) -> None:
        """v3_shadow_shapes.md lead 5: v3 masked the header words of
        private-key blocks whose body was a placeholder or redacted (about 80
        false alarms on shadow-dev), and training had no such block. A
        `-----BEGIN ... PRIVATE KEY-----` block with `[REDACTED]`, `***`,
        `<gizli açar>`, ... as its body, as lines or flattened onto one,
        declared and unlabelled as a whole; in about half the documents a real
        private key elsewhere, labelled."""
        kq = self.q["key_placeholder"]
        reg = spec["register"]
        real = self.rng.random() < kq["real_key_rate"]
        one_line = self.rng.random() < kq["one_line_rate"]
        spec.update(key_placeholder={"real_key": real, "one_line": one_line})
        if self.rng.random() < 0.4:
            self._neutral(d, reg, used)
            d.add("\n")

        def placeholder(dd: Draft) -> None:
            self._key_placeholder_block(dd, used, one_line=one_line, after=not real)

        parts = [placeholder]
        if real:
            spec["with_private"] = True
            parts.append(lambda dd: self._pem_sentence(dd, used, spec))
            self.rng.shuffle(parts)
        for i, part in enumerate(parts):
            if i:
                d.add("\n\n")
            part(d)
        if self.rng.random() < 0.3:
            d.add("\n")
            self._neutral(d, reg, used)

    def _key_placeholder_block(self, d: Draft, used: set[str], one_line: bool | None = None,
                               after: bool = True) -> None:
        """An introducing sentence, then a private-key block whose body is a
        placeholder (`[REDACTED]`, `***`, ...), declared and unlabelled; with
        `after`, sometimes a sentence saying the key isn't shown (never beside
        a real key)."""
        if one_line is None:
            one_line = self.rng.random() < self.q["key_placeholder"]["one_line_rate"]
        head = self.rng.choice(V4.KEY_PLACEHOLDER_HEADERS)
        intro = self._pick_text(d, used, "KP.intro", V4.KEY_PLACEHOLDER_INTROS)
        # The native review of #90 (A, B): one story -- removed or template
        story = V4.KEY_PLACEHOLDER_INTRO_STORY[intro]
        if story == "any":
            story = self.rng.choice(("removed", "template"))
        body = self.rng.choice(V4.KEY_PLACEHOLDER_BODY_STORY[story] + V4.KEY_PLACEHOLDER_BODY_STORY["both"])
        block = (" " if one_line else "\n").join([f"-----BEGIN {head}-----", body, f"-----END {head}-----"])
        d.add(intro + "\n")
        d.decoy(block, KEY_PLACEHOLDER.kind, "PRIVATE_KEY")
        if after and self.rng.random() < 0.5:
            other = tuple(a for a, s in V4.KEY_PLACEHOLDER_AFTER_STORY.items() if s not in ("any", story))
            d.add("\n" + self._pick_text(d, used, "KP.after", V4.KEY_PLACEHOLDER_AFTER, avoid=other))

    def _compose(self, family: str) -> tuple[Draft, dict]:
        d, used = Draft(), set()
        spec = {"family": family, "register": self._register()}
        getattr(self, f"_family_{family}")(d, used, spec)
        self._entity_extras(d, spec)
        return d, spec

    def _entity_extras(self, d: Draft, spec: dict) -> None:
        """P2-4b. Record which names were minted in another spelling or
        script, then case-noise some entities in place (RC6), holding the
        accepted share at the quota so it can never pass the cap."""
        # an inflected name is looked up by its stem: `Mammadovun` -> `Mammadov`
        stem_end = {(x["start"], x["end"]): x["stem_end"] for x in d.suffixes}

        def base(e: dict) -> str:
            end = stem_end.get((e["start"], e["end"]))
            return e["text"][:end - e["start"]] if end else e["text"]

        spelled = [i for i, e in enumerate(d.entities) if e["label"] in ("GIVENNAME", "SURNAME")
                   and base(e) in self.values.name_variants]
        variants = [[d.entities[i]["label"], base(d.entities[i]),
                     self.values.name_variants[base(d.entities[i])][1]] for i in spelled]
        if variants:
            spec["name_variants"] = variants
        # D-10 decides a lone word by its capital, and a homograph pair by
        # meaning: casing noise would blur both lessons (P2-4d)
        # D-39b: official name lists are typed in proper case
        # D-57 S2: an ALL-CAPS form keeps its capitals
        if spec["family"] in ("minimal", "homograph", "namelist") or spec.get("format") == "caps_form":
            return
        nq = self.q["noise"]
        rng = self.noise_rng
        budget = nq["case_target_share"] * (self.entity_total + len(d.entities)) - self.case_noised
        # one lesson per value: a name already in another spelling/script
        # is not case-noised as well (`шамсюлгюда`, `binabayim` read wrong)
        # the same for an inflected word already written as `Bakı'da` or
        # ASCII-folded `Qebeledesen`: casing it too read as `QEBeLedESeN`
        respelled = {(x["start"], x["end"]) for x in d.suffixes if x["surface"] != "plain"}
        order = [i for i in range(len(d.entities)) if i not in spelled
                 and (d.entities[i]["start"], d.entities[i]["end"]) not in respelled]
        rng.shuffle(order)
        picked: dict[int, str] = {}
        for i in order:
            p = nq["case_label_prob"].get(d.entities[i]["label"])
            if p and len(picked) + 1 <= budget and rng.random() < p:
                kinds = sorted(nq["case_kinds"])
                picked[i] = rng.choices(kinds, weights=[nq["case_kinds"][k] for k in kinds])[0]
        if not picked:
            return
        text, entities, applied = apply_entity_casing(d.text, d.entities, picked, rng)
        if len(text) != d.length or len(entities) != len(d.entities):
            raise BuildError("entity casing changed the document's length or lost an entity")
        d.parts, d.entities = [text], entities
        if applied:
            spec["case_noise"] = [[entities[i]["label"], entities[i]["text"], k]
                                  for i, k in sorted(applied.items())]

    def _check(self, d: Draft, spec: dict) -> tuple[dict | None, str]:
        text = d.text
        if unicodedata.normalize("NFC", text) != text:
            return None, "not_nfc"
        if text in self.texts:
            return None, "exact_duplicate_text"
        entities = sorted(d.entities, key=lambda e: e["start"])
        decoys = sorted(d.decoys, key=lambda x: x["start"])
        # R4: an ordinary decoy must be invalid as the label it imitates
        for x in decoys:
            kind = ALL_DECOY_KINDS.get(x["kind"])
            if (kind and not kind.policy and not kind.contextual
                    and kind.resembles not in NAME_LABELS
                    and value_valid(kind.resembles, text[x["start"]:x["end"]])[0]):
                return None, f"decoy_valid:{x['kind']}"
        # spans must be exactly what the resolver itself produces
        blocked = [(x["start"], x["end"]) for x in decoys]
        claims = list({(e["label"], e["text"]): None for e in entities})
        again, _ = resolve_claims(text, [{"label": l, "text": v} for l, v in claims],
                                  blocked=blocked)
        again, _ = complete_occurrences(text, again, blocked=blocked)
        if {(e["start"], e["end"], e["label"]) for e in again} != \
                {(e["start"], e["end"], e["label"]) for e in entities}:
            return None, "resolver_disagrees"
        # P2-4c: each inflected word must also resolve from its bare stem,
        # trusted at exactly the declared spans (how the LLM path will meet it)
        suffixes = sorted(d.suffixes, key=lambda x: x["start"])
        if suffixes:
            label_at = {(e["start"], e["end"]): e["label"] for e in entities}
            stems = [{"label": label_at[(x["start"], x["end"])],
                      "text": text[x["start"]:x["stem_end"]]} for x in suffixes]
            got, _ = resolve_claims(text, stems, blocked=blocked,
                                    declared=[(x["start"], x["end"]) for x in suffixes])
            got = {(g["start"], g["end"], g["label"]) for g in got}
            if any((x["start"], x["end"], label_at[(x["start"], x["end"])]) not in got
                   for x in suffixes):
                return None, "suffix_not_resolved_from_stem"
        for e in entities:
            if structural_kind(text, e["start"], e["end"]):
                return None, "structural_number_span"
        # the length band, inclusive at both ends as validate_corpus.py reads
        # it; a document outside every band gets none rather than a wrong one
        n = len(text)
        band = next((b[0] for b in LENGTH_BANDS if b[2] <= n <= b[3]), None)
        family = spec["family"]
        doc_type = {"structured": f"structured_{spec.get('format')}",
                    "contrast": f"contrast_{spec.get('sub')}",
                    "minimal": "minimal_context",
                    "homograph": "homograph_pair"}.get(family, family)
        record = {
            "id": f"targeted_az_{self.written:06d}",
            "text": text,
            "lang": "az",
            "entities": entities,
            "_decoys": decoys,
            "_suffixes": suffixes,
            "_source": "targeted",
            "_gen_version": GEN_VERSION,
            "_frame_ids": sorted(set(d.frame_ids)),
            "_pii_free": not entities,
            "_doc_type": doc_type,
            "_bucket": band,
            "_register": spec["register"],
            "_noise": [],
            "_hard_negatives": len(decoys),
            "_adversarials": sum(1 for x in decoys if (k := ALL_DECOY_KINDS.get(x["kind"]))
                                 and not k.policy and not k.contextual),
            "_spec": {**{k: v for k, v in spec.items() if k != "decoy_phrase"},
                      "decoy_kinds": d.decoy_kinds, "anchor_gaps": d.anchor_gaps,
                      "frames_source": self.frames.source,
                      "frame_version": self.frames.version,
                      "planned": [[e["label"], e["text"]] for e in entities]},
        }
        # The default language threshold for every document, PII-free ones
        # included: prepare_splits.py relaxes it for them, validate_corpus.py
        # does not, and a record must pass both.
        problems = validate_example(record)
        if problems:
            return None, "validation: " + problems[0].split("(")[0].strip()[:60]
        screen = screen_record(record, run_base_gates=False,
                               planned=[(e["label"], e["text"]) for e in entities])
        if screen:
            return None, "quality: " + re.sub(r"\d+", "N", screen[0].split("(")[0].strip())[:60]
        if find_leaked_pii(text, entities, decoy_spans=decoys):
            return None, "unlabeled_pii_leak"
        # the guard's checks 2-3 on the whole text: a value screened alone can
        # still make a benchmark 8-gram with the words around it (D-19e)
        if forbidden_ngrams(text):
            return None, "benchmark_ngram"
        # and its checks 1 and 3 on values inside the text: a minted value can
        # contain a benchmark value between non-word characters (`2001:db8::e486`
        # in `2001:db8::e486:33b:959d`, P4-3)
        if forbidden_values(text):
            return None, "benchmark_value_in_text"
        return record, ""

    def build(self) -> list[dict]:
        records: list[dict] = []
        family_weights = Q.families(self.q)
        while len(records) < self.n_docs:
            family = self._deficit(family_weights, self.family_counts)
            for attempt in range(200):
                d, spec = self._compose(family)
                record, reason = self._check(d, spec)
                if record:
                    break
                where = spec.get("format") or spec.get("sub") or spec.get("group") or family
                self.rejections[f"{family}/{where}: {reason}"] += 1
            else:
                raise BuildError(f"{family}: 200 consecutive documents failed the gates "
                                 f"(last reason: {reason})")
            records.append(record)
            self._accept(record)
        return records

    def _accept(self, record: dict) -> None:
        """Count an accepted document: the shares, caps and steering the next
        documents are chosen by."""
        family = record["_spec"]["family"]
        self.texts.add(record["text"])
        self.written += 1
        self.family_counts[family] += 1
        self.entity_total += len(record["entities"])
        self.case_noised += len(record["_spec"].get("case_noise", ()))
        self.case_counts.update(x["case"] for x in record["_suffixes"])
        self.inflectable_total += sum(e["label"] in SFX.APPLIES for e in record["entities"])
        if family == "homograph":
            self.homograph_counts[record["_spec"]["homograph"]] += 1
        for fid in set(record["_frame_ids"]):
            self.frame_docs[fid] += 1
        for kind in record["_spec"]["decoy_kinds"]:
            self.kind_counts[kind] += 1
        # D-57: the items steered to a count per 25,000 documents
        for key in ("pf_near", "form_extra", "ipv6_extra", "recall"):
            self.sub_counts[key].update(record["_spec"].get(key, ()))
        if family == "pii_free_business":
            self.sub_counts["biz"][record["_spec"]["biz"]] += 1
        if family == "decoy_pair":
            self.sub_counts["decoy_group"][record["_spec"]["group"]] += 1
            if record["_spec"]["group"] == "noun":
                self.sub_counts["noun_label"][ALL_DECOY_KINDS[record["_spec"]["kind"]].resembles] += 1
                if record["_spec"]["kind"] in NOUN_DATE_KINDS:
                    self.sub_counts["noun_date_kind"][record["_spec"]["kind"]] += 1
        elif family == "contrast":
            self.sub_counts["contrast"][record["_spec"]["sub"]] += 1
        elif family == "structured":
            self.sub_counts["format"][record["_spec"]["format"]] += 1
        elif family == "clerical":
            self.sub_counts["clerical_label"][record["_spec"]["clerical"]["label"]] += 1
        elif family == "namelist":
            self.sub_counts["namelist"][record["_spec"]["namelist"]] += 1
        elif family == "cross_anchor":
            sp = record["_spec"]
            self.sub_counts["cross_anchor"][sp["cross_slot"]] += 1
            if "short_label" in sp:
                self.sub_counts["short_label"][sp["short_label"]] += 1
            if "name_label" in sp:
                self.sub_counts["name_label"][sp["name_label"]] += 1
            if "iban_kind" in sp:
                self.sub_counts["iban_kind"][sp["iban_kind"]] += 1
        elif family == "locative":
            self.sub_counts["locative_label"][record["_spec"]["locative"][0]] += 1
        elif family == "slot_invalid":
            self.sub_counts["slot_label"][record["_spec"]["slot_label"]] += 1
        elif family == "time_seconds":
            self.sub_counts["time_seconds"][record["_spec"]["time_sub"]] += 1
        elif family == "place_verbs":
            self.sub_counts["place_case"].update(c for c in record["_spec"]["place_verbs"]
                                                 if c != "surname")
