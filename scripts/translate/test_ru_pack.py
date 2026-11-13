"""The Russian language pack, exercised through the SHARED harness.

The spec's coordination rule is that the harness is not forked: a language is
a pack that plugs into `scripts/translate/`, never a copy of it. These tests
assert that Russian is reachable the same way English is -- same renderer
registry, same anchor interface, same prompt builder -- so a divergence shows
up here rather than as two incompatible corpora at merge time.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from translate.lang import ANCHORS  # noqa: E402
anchors_en, anchors_ru = ANCHORS["en"], ANCHORS["ru"]
from translate.prompt import system_prompt  # noqa: E402
from translate.render import RENDERERS, render_value  # noqa: E402
from translate.validate import ANCHOR_MODULES  # noqa: E402

PASS = FAIL = 0


def check(name: str, got: object, want: object) -> None:
    global PASS, FAIL
    if got == want:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL {name}\n     got  {got!r}\n     want {want!r}")


def truthy(name: str, got: object, want: bool) -> None:
    check(name, bool(got), want)


# --------------------------------------------------------------------------- #
# registration: ru is reachable exactly like en
# --------------------------------------------------------------------------- #
truthy("ru has a renderer", "ru" in RENDERERS, True)
truthy("ru has an anchor module", "ru" in ANCHOR_MODULES, True)
check("ru anchor module is the shared one",
      ANCHOR_MODULES["ru"].__name__, "translate.lang.ru.anchors")
truthy("ru has a prompt", "Russian" in system_prompt("ru"), True)

# the anchor packs present the same surface
for _name in ("has_anchor", "anchor_failures", "ANCHOR_REQUIRED",
              "SELF_SIGNALLING", "DEFAULT_WINDOW"):
    truthy(f"anchors_ru exposes {_name}", hasattr(anchors_ru, _name), True)
    truthy(f"anchors_en exposes {_name}", hasattr(anchors_en, _name), True)

# --------------------------------------------------------------------------- #
# orthography: names and places become Cyrillic, structured values never move
# --------------------------------------------------------------------------- #
_rng = random.Random(20260906)
for _label, _value, _want in [
    ("CITY", "Gəncə", "Гянджа"),          # exonym table
    ("CITY", "Bakı", "Баку"),
    ("SURNAME", "Hüseynov", "Гюсейнов"),  # h->г, ü->ю, not a naive char map
    ("GIVENNAME", "Əli", "Али"),
]:
    check(f"render {_label} {_value!r}", render_value(_label, _value, "ru", _rng),
          _want)

# "Structured values are never transformed in any language" -- the spec is
# explicit, and every character in these is load-bearing.
for _label, _value in [
    ("TELEPHONENUM", "+994512345678"),
    ("EMAIL", "elchin.mammadov@sirket.az"),
    ("IBAN", "AZ21NABZ00000000137010001944"),
    ("AZ_FIN", "A1B2C3D"),
    ("IPV4_ADDRESS", "10.37.101.98"),
    ("MAC_ADDRESS", "3D:F2:C9:A6:B3:4F"),
    ("URL", "https://portal.sirket.az/giris"),
    ("PAYMENT_CARD_NUMBER", "4169710926000236"),
    ("ZIPCODE", "AZ1045"),
    ("AZ_VOEN", "1700123456"),
]:
    check(f"structured {_label} untouched",
          render_value(_label, _value, "ru", _rng), _value)

# DATE and TIME are minted by the carrier locale and must not be touched again
for _label, _value in [("DATE", "13 февраля 1977 г."), ("TIME", "14:30")]:
    check(f"carrier-minted {_label} untouched",
          render_value(_label, _value, "ru", _rng), _value)

# --------------------------------------------------------------------------- #
# anchors: Russian context licenses the five bare-shape labels
# --------------------------------------------------------------------------- #
_licensed = "Дата рождения: 12.05.1988, возраст 34 года, дом 17, кв. 5"
truthy("anchor: DATE licensed by 'дата рождения'",
       anchors_ru.has_anchor("DATE", _licensed, 15, 25), True)
truthy("anchor: AGE licensed by 'возраст'",
       anchors_ru.has_anchor("AGE", _licensed, 34, 36), True)
check("anchor: an unlicensed bare number fails",
      anchors_ru.has_anchor("AGE", "просто 34 здесь", 7, 9), False)
check("anchor: a label with no anchor requirement passes",
      anchors_ru.has_anchor("EMAIL", "нет контекста", 0, 3), True)
check("anchor: anchor_failures is empty on a licensed document",
      anchors_ru.anchor_failures(
          _licensed, [{"label": "DATE", "start": 15, "end": 25},
                      {"label": "AGE", "start": 34, "end": 36}]), [])

# Wahoo leaves the occasional Azerbaijani table header in an otherwise Russian
# document; the Azerbaijani fallback keeps that row rather than invalidating
# five labels inside it.
truthy("anchor: falls back to the Azerbaijani word in a leftover header",
       anchors_ru.has_anchor("AGE", "ID;SOYAD;AD;YAŞ 34;", 16, 18), True)

print("=" * 60)
print(f"PASSED {PASS}   FAILED {FAIL}")
print("=" * 60)
sys.exit(1 if FAIL else 0)
