"""D-47a/b detectors (piigen.meta_noise): the examples are caught,
ordinary glosses are not.

    python scripts/piigen/test_meta_noise.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen.meta_noise import explained_typos, is_formal, placeholders, self_corrections  # noqa: E402

PASS = FAIL = 0
FAILURES: list[str] = []


def check(cond: bool, msg: str, detail=None) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        FAILURES.append(msg + (f"  [{detail!r}]"[:300] if detail is not None else ""))


EXPLAINED = [  # D-47a: caught
    "Bu vəziyyit (typo) bizi narahat edir.",
    "Sistem l0st (0/O qarışığı) qeyd edildi.",
    "OCR xətası (məsələn, 0/O və ya 1/l qarışıqlığı) mümkündür.",
    "Müqavile (typo: müqavilə) imzalandı.",
    "Heç bir xəta (xeta -> xəta) aşkar edilmədi.",
    "məlumatlar (malamat -> məlumat) yoxlanıldı",
    "Sistemdəki l0q (OCR) qeydi.",
    "# OCR-style artifact: l0g_level",
    "[OCR Artifact] Hissə nömrəsi: l0552",
    "Məlumat (noise: dropped ə) verildi.",
    "bəlkə də 0 rəqəmi O hərfi ilə qarışıb (0/O).",
]
NOT_EXPLAINED = [  # ordinary text: not caught
    "Sistemdə problem (xəta) yarandı.",
    "Optik simvol tanıma (OCR) sistemi alınacaq.",
    "Doğum tarixi (25/10/1954) qeyd edildi.",
    "GIRIŞ/ÇIXIŞ (I/O) XƏTASI baş verdi.",
    "Sitat düzgün verilib (sic).",
    "Problem (yəni xəta) aradan qaldırıldı.",
    "[Metadata: Signal: High | Noise: Low]",
    "Proses (GET -> POST) dəyişdi.",
    "Kodda bir neçə typo var, onları da sil.",
]
CORRECTED = [  # D-47b: caught
    "Bu iş aparılmalıddır (yox, aparılmalıdır).",
    "Məsələ teclı (yox, təcili) həll edilməlidir.",
    "Əgər hər hansı xəta (xəta... yox, problem) olarsa",
    "melumat (melumat - yox, məlumat) verildi",
    "Cari konfiqürasiyaları (daha doğrusu, konfiqurasiyaları)",
    "Hesab-fakura (düzəliş: Hesab-faktura)",
    "ödəniş (xeyr, ödəniş xətası) qeydə alındı",
    "Sistemdə texnikı (yəni, texniki) nasazlıq aşkar edilmişdir.",
    "Sizə xidmät (yəni xidmət) göstərmək",
]
NOT_CORRECTED = [
    "Cavab: (Bəli / Yox)",
    "Məhkum olunubmu? (yox)",
    "Bu barədə (yəni, ödəniş barədə) məlumat verildi.",
    "Bəyanatdakı texniki xəta (yəni, nasazlıq) aradan qaldırılmalıdır.",
    "Görünür, bu datan (yəni, məlumat) səbəbindən olub.",
    "Düzəliş: 2 saylı əlavə yeni redaksiyada verilir.",
]


PLACEHOLDERS = ["[Məhkəmənin adı] məhkəməsi elan edir.", "[Şirkət Adı] MMC", "[Rayon Adı] rayonu",
                "[Münisipalitet Adı] bələdiyyəsi", "[Rayon] rayon məhkəməsi", "Ünvan: [E-poçt ünvanı]",
                "[MƏHKƏMƏNİN ADI]", "[Mehkemenin adi]", "[Ad Soyad]", "Tarix: [tarix]",
                "[Məhkəmənin adı] [İddiaçı] [Cavabdeh]", "Nam: [Adınız Soyadınız]"]
NOT_PLACEHOLDERS = ["[İmza]", "[Möhür yeri]", "[Möhür və İmza]", "[Elektron İmza]", "[Müştəri]: Salam",
                    "[Səs kəsintisi]", "[Status: OK]", "[role: FİN]", "[redacted]", "[Məlumat yoxdur]",
                    "[Səhv nömrə]", "[Xətalı ünvan]", "[Sistem Logu - 2021 Tarixi]", "[link](https://a.az)",
                    "[ERROR] bağlantı", "[2024-03-12 14:05:33]",
                    "[Tarix]          [Səviyyə] [Modul]    [Mesaj]", "[ZAMAN] ¦ [MODUL] ¦ [KOD]",
                    "[2021-06-10 08:12:46] [INFO] [Email] Şifrə bərpa",
                    "[Sıra] ¦ [Sistem_ID] ¦ [Ad / Soyad] ¦ [Məkan]"]


def test_placeholders() -> None:
    for t in PLACEHOLDERS:
        check(bool(placeholders(t)), "D-47e caught", t)
    for t in NOT_PLACEHOLDERS:
        check(not placeholders(t), "D-47e leaves alone", (t, placeholders(t)))


def test_detectors() -> None:
    for t in EXPLAINED:
        check(bool(explained_typos(t)), "D-47a caught", t)
    for t in NOT_EXPLAINED:
        check(not explained_typos(t), "D-47a leaves alone", (t, explained_typos(t)))
    for t in CORRECTED:
        check(bool(self_corrections(t)), "D-47b caught", t)
    for t in NOT_CORRECTED:
        check(not self_corrections(t), "D-47b leaves alone", (t, self_corrections(t)))


def test_genres() -> None:
    for dt in ("court_filing", "legal_notice", "government_form", "news_article", "invoice", "contract_clause"):
        check(is_formal(dt), "formal", dt)
    for dt in ("live_chat", "whatsapp_thread", "customer_email", "email_thread", "complaint_letter"):
        check(not is_formal(dt), "conversational", dt)


TESTS = [("detectors", test_detectors), ("placeholders (D-47e)", test_placeholders),
         ("formal and conversational types", test_genres)]

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
