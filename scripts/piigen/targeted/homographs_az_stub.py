"""Homograph names: a starter list until the `homographs_az.py` (P4-2).

The builder imports `homographs_az` when it exists and this stub otherwise,
so nothing changes on the builder side when the file lands. That file
must export the same names:

    HOMOGRAPHS: dict[str, dict]
        name -> {"gender": "f" | "m" (optional; makes a full name agree),
                 "az": meaning in Azerbaijani, "en": meaning in English,
                 "name": [sentences using it as a NAME],
                 "word": [sentences using it as the ORDINARY WORD]}
    LONE_NAMES: list[str]   # D-10: a capitalised name alone -> labelled
    LONE_WORDS: list[str]   # D-10: a lowercase ordinary word alone -> not labelled
    HOMOGRAPHS_VERSION: str

Markers (agreed in P4-2), exactly one per sentence:
    [[...]]  the name, labelled GIVENNAME          `[[Dəniz]] zəng etdi.`
    <<...>>  the ordinary word, a decoy of kind     `<<Dəniz>> sakit idi.`
             `homograph_noun`, never labelled
An inflected word is marked whole (D-9): `[[Dənizə]]`, `<<dənizə>>`.

Per name: at least 3 + 3 sentences; on each side at least one sentence
starting with the word (where a capital is no signal) and one inflected use;
lowercase and capitalised ordinary-word uses mixed. No digits, no other PII.
These 12 come from the task document's own examples; the team checks and
extends them to 50+.
"""

HOMOGRAPHS_VERSION = "stub-2026-10-02"

HOMOGRAPHS: dict[str, dict] = {
    "Dəniz": {"gender": "f", "az": "dəniz", "en": "sea",
              "name": ["[[Dəniz]] zəng etdi.", "Bu gün [[Dənizə]] məktub yazdım.",
                       "Sənədləri [[Dəniz]] gətirib."],
              "word": ["<<Dəniz>> sakit idi.", "Uşaqlar sahildə oturub <<dənizə>> baxırdı.",
                       "Bu yay <<dənizdə>> çox çimdik."]},
    "Bahar": {"gender": "f", "az": "bahar", "en": "spring",
              "name": ["[[Bahar]] xanım gəldi.", "Hesabatı [[Bahara]] göndərin.",
                       "Müqaviləni [[Bahar]] imzalayıb."],
              "word": ["<<Bahar>> gəldi, hava isindi.", "<<Baharda>> ağaclar çiçəkləyir.",
                       "Bu il <<bahar>> tez gəldi."]},
    "Ümid": {"gender": "m", "az": "ümid", "en": "hope",
             "name": ["[[Ümid]] bu gün işə gəlmədi.", "Dünən [[Ümidə]] yazdım.",
                      "Layihəni [[Ümid]] idarə edir."],
             "word": ["<<Ümid>> edirəm ki, hər şey yaxşı olacaq.",
                      "Həkimlər hələ <<ümidlərini>> itirməyib.", "Bu xəbər bizə <<ümid>> verdi."]},
    "Fidan": {"gender": "f", "az": "fidan", "en": "sapling",
              "name": ["[[Fidan]] sənədləri gətirdi.", "İclasda [[Fidana]] təşəkkür etdik.",
                       "Bu məktubu [[Fidan]] yazıb."],
              "word": ["<<Fidanlar>> bu il yaxşı bitib.", "Bağa yeni <<fidan>> əkdik.",
                       "Hər <<fidana>> ayrıca su verilir."]},
    "Aydın": {"gender": "m", "az": "aydın", "en": "clear",
              "name": ["[[Aydın]] zəng etdi.", "Sabah [[Aydına]] mesaj göndərərəm.",
                       "Müqaviləni [[Aydın]] yoxlayıb."],
              "word": ["<<Aydın>> məsələdir, uzatmağa ehtiyac yoxdur.", "Bu gün hava <<aydın>> idi.",
                       "Hər şey indi <<aydındır>>."]},
    "Lalə": {"gender": "f", "az": "lalə", "en": "tulip",
             "name": ["[[Lalə]] iclasa gəldi.", "[[Lalənin]] ərizəsi qəbul olundu.",
                      "Hesabatı [[Lalə]] hazırlayıb."],
             "word": ["<<Lalələr>> artıq açıb.", "Bağçada qırmızı <<lalə>> bitib.",
                      "Bu il <<lalələrə>> çox qulluq etdik."]},
    "Ulduz": {"gender": "f", "az": "ulduz", "en": "star",
              "name": ["[[Ulduz]] bu gün növbədədir.", "Zəhmət olmasa, [[Ulduza]] zəng edin.",
                       "Sənədi [[Ulduz]] göndərib."],
              "word": ["<<Ulduzlar>> gecə parlayır.", "Göydə bir <<ulduz>> axdı.",
                       "Uşaq <<ulduzlara>> baxırdı."]},
    "Günəş": {"gender": "f", "az": "günəş", "en": "sun",
              "name": ["[[Günəş]] xanım gəldi.", "Bu məlumatı [[Günəşə]] çatdırın.",
                       "Layihəni [[Günəş]] təqdim etdi."],
              "word": ["<<Günəş>> çıxdı, hava isindi.", "Bu gün <<günəş>> çox yandırır.",
                       "Pəncərədən <<günəşə>> baxdıq."]},
    "Səma": {"gender": "f", "az": "səma", "en": "sky",
             "name": ["[[Səma]] bu gün ofisdə deyil.", "Axşam [[Səmaya]] yazdım.",
                      "Hesabatı [[Səma]] yoxlayıb."],
             "word": ["<<Səma>> buludsuz idi.", "Quşlar <<səmada>> uçur.", "Axşam <<səma>> qızardı."]},
    "Polad": {"gender": "m", "az": "polad", "en": "steel",
              "name": ["[[Polad]] müqaviləni imzaladı.", "Sabah [[Polada]] zəng edin.",
                       "Sifarişi [[Polad]] qəbul edib."],
              "word": ["<<Polad>> zavodda əridilir.", "Bu körpü <<poladdan>> tikilib.",
                       "Anbarda <<polad>> qalmayıb."]},
    "Arzu": {"gender": "f", "az": "arzu", "en": "wish",
             "name": ["[[Arzu]] bu gün gəlməyəcək.", "Hamımız [[Arzuya]] təşəkkür etdik.",
                      "Sənədləri [[Arzu]] toplayıb."],
             "word": ["<<Arzu>> etmək asandır, çalışmaq çətindir.", "Bu, uşaqlıq <<arzum>> idi.",
                      "Hər kəsin bir <<arzusu>> var."]},
    "Sevinc": {"gender": "f", "az": "sevinc", "en": "joy",
               "name": ["[[Sevinc]] iclasa gecikdi.", "Dünən [[Sevincə]] mesaj yazdım.",
                        "Hesabatı [[Sevinc]] göndərib."],
               "word": ["<<Sevinc>> hissi hamını bürüdü.", "Xəbər hamıya <<sevinc>> gətirdi.",
                        "Onun <<sevincinin>> həddi yox idi."]},
}

LONE_NAMES: list[str] = sorted(HOMOGRAPHS)
LONE_WORDS: list[str] = sorted(v["az"] for v in HOMOGRAPHS.values())
