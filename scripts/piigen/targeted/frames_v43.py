"""Frames for the extra batch (D-64d, m2): items added after v4.2.

X-BN (23 Oct; B3 in PR #134 flags BUILDINGNUM 90.8 -> 81.6 on v4.2). The same address probes on
v4.1 and v4.2 (track M, task log `extra_batch_buildingnum.md`) show what v4.2 lost:
  * `Ev:` / `Ev nömrəsi:` form lines after a `Küçə:` line (v4.2 has 500 labelled `Bina:` lines, no `Ev:` line,
    beside unlabelled `Otaq:` / `Mərtəbə:` / `Kabinet:` lines);
  * the number, `bina N` or `ev N` before the street (`23, Nizami küçəsi`, read as AGE by v4.2);
  * `№` beside a street (`Nizami küçəsi, №23`), next to the unlabelled `otaq №12` look-alike;
and, in both models, counts beside building words masked as BUILDINGNUM (`9 mərtəbəli`, `3 otaqlı`).
builder._building_v43 writes these, each with its unlabelled look-alike, when quotas `building_v43` is set.
"""

# Field keys of the building line under a `Küçə:` line. `Ev` is a dwelling (D-57 review, D): only
# beside a floor line, never beside a room or an office
FORM_KEYS_EV = ["Ev", "Ev nömrəsi"]
FORM_KEYS_BINA = ["Bina", "Bina nömrəsi"]
# the line above the form (its own pool: V42.BUILDING_LINES_INTROS has 4, too few for a building-only batch)
FORM_INTROS = ["Görüşün keçiriləcəyi yer:", "Çatdırılma ünvanı:", "Ofisin yeni ünvanı:", "Kuryer üçün qeyd:",
               "Qeydiyyat ünvanı:", "Faktiki yaşayış yeri:", "Göndərişin ünvanı:", "Ustanın gedəcəyi ünvan:",
               "Müştərinin ünvanı:", "Sifarişin çatdırılacağı yer:", "Kirayə mənzilin ünvanı:", "Ərizəçinin ünvanı:"]
# the street line's key; `Ünvan:` too (v4.2 misses `Ünvan: Nizami küçəsi` then `Ev: 14`)
FORM_STREET_KEYS = ["Küçə", "Küçə", "Ünvan"]
# a city line above the street, sometimes
FORM_CITY_KEYS = ["Şəhər", "Yaşayış yeri"]

# The address phrase {b}: the number before the street; {v} the building number, {s} the street
NUMBER_FIRST = ["{v}, {s}", "{v} {s}", "bina {v}, {s}"]   # bare forms first: v4.2 reads `23, Nizami küçəsi` as AGE
NUMBER_FIRST_EV = ["ev {v}, {s}"]                 # beside a floor only
# ... and `№` beside the street, before or after it
NUMERO = ["{s}, №{v}", "{s} №{v}", "bina №{v}, {s}", "№{v}, {s}"]
NUMERO_EV = ["{s}, ev №{v}"]

# Sentences around the address phrase {b} and the look-alike phrase {d} (a room, floor or office number).
# The D-57 review, D: `ev` only where people live or receive parcels (EV_FRAMES)
SENTENCES = ["Ofis {b}, {d} ünvanında yerləşir.",
             "Kuryer sifarişi {b}, {d} ünvanına çatdırmalıdır.",
             "Müştəri {b}, {d} ünvanında qeydiyyatdadır.",
             "Arxiv sənədləri {b}, {d} ünvanında saxlanılır.",
             "Bağlama {b}, {d} ünvanına göndərilib.",
             "İcarəçi {b}, {d} ünvanında yaşayır.",
             "Usta sabah {b}, {d} ünvanına gələcək.",
             "Şirkətin nümayəndəliyi {b}, {d} ünvanına köçüb.",
             "Sifarişçi {b}, {d} ünvanını qeyd edib.",
             "Təmir işləri {b}, {d} ünvanında aparılır.",
             "Müraciət edən şəxs {b}, {d} ünvanında qeydiyyatdadır.",
             "Hesab-faktura {b}, {d} ünvanına göndərilməlidir.",
             "Yeni kirayəçi {b}, {d} ünvanına köçüb.",
             "Poçt göndərişi {b}, {d} ünvanına çatdırılıb."]
EV_FRAMES = frozenset({1, 2, 4, 5, 6, 8, 10, 12, 13})   # parcels, residents, visits
# a document number beside a `№` address (unlabelled, written as plain text)
NUMERO_DOC = ["Müqavilə №{n} üzrə sənədlər {b} ünvanına göndərilib.",
              "Qaimə №{n} ilə yük {b} ünvanına çatdırılıb.",
              "Sifariş №{n} {b} ünvanına çatdırılacaq.",
              "Akt №{n} {b} ünvanında tərtib edilib.",
              "Ərizə №{n} üzrə yoxlama {b} ünvanında aparılıb.",
              "Hesab №{n} {b} ünvanına göndərilib."]

# A real address beside a count (unlabelled look-alike {c}): the counts the model masks as BUILDINGNUM.
# Keyed by the pair's look-alike kind; {b} is the street then the number
COUNT_SENTENCES = {
    "floor_number": ["Müştəri {b} ünvanında, {c} mərtəbəli binada yaşayır.",
                     "Ofis {b} ünvanındadır, bina {c} mərtəbəlidir.",
                     "Satılan mənzil {b} ünvanında, {c} mərtəbəli yeni binadadır.",
                     "Kirayəçi {b} ünvanına köçüb, bina {c} mərtəbədən ibarətdir.",
                     "Təmir {b} ünvanındakı {c} mərtəbəli binada aparılır."],
    "room_number": ["Satılan mənzil {b} ünvanındadır, {c} otaqlıdır.",
                    "Kirayə ev {b} ünvanında yerləşir, {c} otaqlıdır.",
                    "Ailə {b} ünvanındakı {c} otaqlı mənzilə köçüb.",
                    "Elan: {b} ünvanında {c} otaqlı mənzil satılır.",
                    "Müştəri {b} ünvanında {c} otaqlı ev axtarır."],
    "office_number": ["Mərkəz {b} ünvanında yerləşir, binada {c} kabinet var.",
                      "Klinika {b} ünvanına köçüb, orada {c} kabinet fəaliyyət göstərir.",
                      "Şirkət {b} ünvanında {c} ofis icarəyə götürüb.",
                      "Biznes mərkəzi {b} ünvanındadır, orada {c} ofis var.",
                      "Poliklinika {b} ünvanında yerləşir, {c} həkim kabineti işləyir."],
}
# the count's range by kind: floors in a building, rooms in a flat, offices in a centre
COUNT_RANGE = {"floor_number": (2, 25), "room_number": (1, 6), "office_number": (2, 60)}

# A count of houses or buildings, the number BEFORE `ev` / `bina` (red-team rule #136: v4.2 masks
# `Kənddə 120 ev var`, `Məhəllədə 30 bina tikilib` as BUILDINGNUM; the other side of the B3 drop: D-57's many
# `bina 7` / `ev 7`), unlabelled, beside a real address {b}. Our own sentences, not the findings' (plan rule 4)
BUILDING_COUNT_SENTENCES = [
    "Kənddə cəmi {c} ev var, müştəri isə {b} ünvanında yaşayır.",
    "Məhəllədə son iki ildə {c} bina tikilib, ofis {b} ünvanındadır.",
    "Zəlzələdə {c} ev zərər çəkib, yardım {b} ünvanından paylanır.",
    "Qəsəbə {c} evdən ibarətdir, poçt şöbəsi {b} ünvanında yerləşir.",
    "Layihə üzrə {c} yaşayış binası tikiləcək, satış ofisi {b} ünvanındadır.",
    "Bu il rayonda {c} ev təmir olunub, komissiya {b} ünvanında qəbul aparır.",
    "Şəhərcikdə {c} çoxmərtəbəli bina var, idarə {b} ünvanında yerləşir.",
    "Sel nəticəsində {c} evə ziyan dəyib, qərargah {b} ünvanında fəaliyyət göstərir.",
    "Kooperativ {c} bina üçün sifariş qəbul edir, müraciətlər {b} ünvanına göndərilir.",
    "Küçədə {c} köhnə ev sökülüb, sakinlərdən biri artıq {b} ünvanına köçüb.",
]
BUILDING_COUNT_RANGE = (3, 400)

# --------------------------------------------------------------------------- #
# X-AGE (red-team rule #136): v4.2 masks any number next to `yaş` as AGE, even when it is not a
# person's age: an age limit (`Pensiya yaşı 65`), a range (`14-17 yaş arası`), an average (`orta yaşı 27`) or
# the age of a thing (`Binanın yaşı 50`). builder._age_v43 writes one of these, unlabelled, beside a real age
# of a person that uses the same word `yaş`. Our own sentences, not the findings' (plan rule 4). No suffix is
# glued to a digit (`34-dür`, `40-dır`): its vowel depends on how the number is read
# --------------------------------------------------------------------------- #
# a real age of a person: (template, (lo, hi))
AGE_REAL = [
    ("Müştəri {v} yaşındadır və ilk dəfə müraciət edir.", (18, 80)),
    ("Ərizəçinin yaşı {v} olaraq göstərilib, sənədləri tamdır.", (18, 75)),
    ("Xəstə {v} yaşlı kişidir, şikayəti baş ağrısıdır.", (25, 85)),
    ("Namizədin yaşı {v}, iş təcrübəsi isə beş ildir.", (22, 55)),
    ("Sürücü {v} yaşında olduğunu bildirib.", (19, 70)),
    ("Qeydiyyat vərəqəsində şikayətçinin yaşı {v} göstərilib.", (18, 90)),
    ("Oğlum {v} yaşındadır, bu il buraxılış imtahanı verəcək.", (16, 17)),
    ("Anam {v} yaşındadır, keçən il pensiyaya çıxıb.", (60, 85)),
    ("Kirayəçi {v} yaşlı gənc oğlandır.", (20, 29)),
    ("Şikayətçi {v} yaşlı qadındır, evdar xanımdır.", (25, 80)),
    ("İşçinin yaşı {v} olaraq anketdə qeyd edilib.", (20, 64)),
    ("Tələbə {v} yaşındadır, ikinci kursda oxuyur.", (18, 22)),
    ("Babam {v} yaşında olsa da, hər səhər gəzintiyə çıxır.", (70, 95)),
    ("Sığortalının yaşı {v}, ona görə məbləğ dəyişməyib.", (18, 70)),
    ("Qonaq {v} yaşında olduğunu dedi.", (18, 80)),
    ("Müraciət edən gənc {v} yaşındadır.", (18, 29)),
]
# the look-alikes, by kind: (template, value range); a range writes {v} and {w}
AGE_LOOKALIKES = {
    "age_limit": [
        ("Pensiya yaşı kişilər üçün {v} olaraq müəyyən edilib.", (60, 67)),
        ("Bu vəzifəyə qəbul üçün yuxarı yaş həddi {v} olaraq göstərilib.", (30, 65)),
        ("Film {v} yaşdan yuxarı tamaşaçılar üçündür.", (12, 18)),
        ("Sürücülük vəsiqəsi {v} yaşdan verilir.", (17, 18)),
        ("Müsabiqəyə {v} yaşa qədər olan gənclər qatıla bilər.", (25, 35)),
        ("Klubda üzvlük üçün minimum yaş {v} olaraq qəbul edilib.", (14, 21)),
    ],
    "age_range": [
        ("Dərnək {v}–{w} yaş arası uşaqlar üçündür.", (7, 14)),
        ("Turnirdə {v}-{w} yaşlı yeniyetmələr iştirak edir.", (13, 17)),
        ("Sorğuda {v}–{w} yaş qrupundan olan respondentlər iştirak edib.", (18, 44)),
        ("Vakansiya {v}–{w} yaş arası namizədlər üçün açıqdır.", (22, 45)),
        ("Kurs {v}-{w} yaşlı böyüklər üçün nəzərdə tutulub.", (25, 60)),
    ],
    "age_average": [
        ("İştirakçıların orta yaşı {v} olub.", (20, 45)),
        ("Komandanın orta yaşı {v} təşkil edir.", (22, 30)),
        ("Şöbədə əməkdaşların orta yaşı {v} olaraq hesablanıb.", (25, 50)),
        ("Sorğuya qatılanların orta yaşı {v} ətrafındadır.", (20, 55)),
    ],
    "object_age": [
        ("Binanın yaşı {v} ildən çoxdur.", (40, 150)),
        ("Bu körpünün yaşı {v} ilə çatır.", (50, 200)),
        ("Həyətdəki çinar ağacının yaşı {v} ildir.", (100, 500)),
        ("Şirkətin yaşı artıq {v} ildir.", (5, 40)),
        ("Maşının yaşı {v} il olduğu üçün sığorta baha başa gəlir.", (3, 25)),
        ("Məktəb binasının yaşı {v} ilə yaxındır.", (30, 120)),
    ],
}
