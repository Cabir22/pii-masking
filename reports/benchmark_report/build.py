"""Builds the Run B benchmark report in English and Azerbaijani from data.json.

Every number comes from data.json (extracted from reports/scoreboard/*.json and
the benchmark file) or from the repo documents named in the text, so both
languages always show the same figures.
"""
import json, html, sys
from pathlib import Path

HERE = Path(__file__).parent
D = json.load(open(HERE / "data.json"))
LANG = sys.argv[1]  # "en" or "az"


def T(en, az):
    return en if LANG == "en" else az


def pct(x, d=1):
    return f"{x * 100:.{d}f}" if x <= 1.0000001 else f"{x:.{d}f}"


def num(n):
    s = f"{n:,}"
    return s if LANG == "en" else s.replace(",", "\u00a0")


def dec(x, d=1):
    s = f"{x:.{d}f}"
    return s if LANG == "en" else s.replace(".", ",")


def P(x, d=1):  # percentage-point value formatted for the language
    return dec(x * 100 if abs(x) <= 1.0000001 else x, d)


O = D["overall"]
c1, cm, rb, rm = O["ckpt1"], O["ckpt1_M"], O["runb"], O["runb_M"]
L = D["labels"]
LABELS = sorted(L, key=lambda k: L[k]["ckpt1"]["f1"])

# ---------------------------------------------------------------- charts (SVG)
C_OLD, C_NEW, C_BAD = "#9aa5b1", "#1f6f8b", "#c2410c"


def dumbbell(rows, title, width=720, row_h=19, left=210, maxv=100, note=None):
    """rows: (label, before, after) in percent."""
    h = 40 + row_h * len(rows) + 30
    x = lambda v: left + (width - left - 60) * v / maxv
    s = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img" aria-label="{html.escape(title)}">']
    for g in range(0, maxv + 1, 20):
        s.append(f'<line x1="{x(g):.1f}" y1="28" x2="{x(g):.1f}" y2="{h-26}" stroke="#e5e7eb"/>'
                 f'<text x="{x(g):.1f}" y="{h-10}" class="ax" text-anchor="middle">{g}</text>')
    for i, (lab, a, b) in enumerate(rows):
        y = 40 + i * row_h
        col = C_BAD if b < a - 1 else C_NEW
        s.append(f'<text x="{left-8}" y="{y+4}" class="lb" text-anchor="end">{html.escape(lab)}</text>'
                 f'<line x1="{x(a):.1f}" y1="{y}" x2="{x(b):.1f}" y2="{y}" stroke="{col}" stroke-width="2.5" opacity=".55"/>'
                 f'<circle cx="{x(a):.1f}" cy="{y}" r="4.2" fill="{C_OLD}"/>'
                 f'<circle cx="{x(b):.1f}" cy="{y}" r="4.6" fill="{col}"/>'
                 f'<text x="{x(max(a,b))+9:.1f}" y="{y+4}" class="vl">{dec(a)} → {dec(b)}</text>')
    s.append(f'<circle cx="{left}" cy="16" r="4.2" fill="{C_OLD}"/><text x="{left+9}" y="20" class="lg">{T("Checkpoint 1","Checkpoint 1")}</text>'
             f'<circle cx="{left+120}" cy="16" r="4.6" fill="{C_NEW}"/><text x="{left+129}" y="20" class="lg">Run B</text>'
             f'<circle cx="{left+190}" cy="16" r="4.6" fill="{C_BAD}"/><text x="{left+199}" y="20" class="lg">{T("Run B, worse","Run B, pisləşib")}</text>')
    s.append("</svg>")
    return "".join(s)


def bars(rows, title, width=720, row_h=22, left=230, maxv=100, fmt=lambda v: dec(v)):
    """rows: (label, before, after) grouped bars."""
    h = 34 + row_h * len(rows) + 26
    x = lambda v: (width - left - 70) * v / maxv
    s = [f'<svg viewBox="0 0 {width} {h}" class="chart" role="img" aria-label="{html.escape(title)}">']
    s.append(f'<rect x="{left}" y="8" width="10" height="10" fill="{C_OLD}"/><text x="{left+15}" y="17" class="lg">Checkpoint 1</text>'
             f'<rect x="{left+120}" y="8" width="10" height="10" fill="{C_NEW}"/><text x="{left+135}" y="17" class="lg">Run B</text>')
    for i, (lab, a, b) in enumerate(rows):
        y = 30 + i * row_h
        s.append(f'<text x="{left-8}" y="{y+13}" class="lb" text-anchor="end">{html.escape(lab)}</text>'
                 f'<rect x="{left}" y="{y+2}" width="{x(a):.1f}" height="8" fill="{C_OLD}"/>'
                 f'<rect x="{left}" y="{y+11}" width="{x(b):.1f}" height="8" fill="{C_NEW}"/>'
                 f'<text x="{left+x(max(a,b))+6:.1f}" y="{y+14}" class="vl">{fmt(a)} → {fmt(b)}</text>')
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- helpers
def table(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def delta(a, b, d=1, good_up=True):
    v = (b - a) * (100 if abs(a) <= 1.0000001 and abs(b) <= 1.0000001 else 1)
    cls = "up" if (v > 0) == good_up else ("dn" if v != 0 else "")
    sign = "+" if v > 0 else ("−" if v < 0 else "±")
    return f'<span class="{cls}">{sign}{dec(abs(v), d)}</span>'


m1, mb = c1["micro"], rb["micro"]
mm1, mmb = cm["micro"], rm["micro"]

# ---------------------------------------------------------------- sections
CAT_NAMES = {
    "hard_negative": T("Hard negatives", "Çətin neqativlər"),
    "mixed": T("Mixed", "Qarışıq"),
    "natural_variant_hard_negative": T("Natural variant, hard negative", "Təbii variant, çətin neqativ"),
    "natural_variant_positive": T("Natural variant, positive", "Təbii variant, pozitiv"),
    "anchor_variant_hard_negative": T("Anchor variant, hard negative", "Lövbər variantı, çətin neqativ"),
    "anchor_variant_positive": T("Anchor variant, positive", "Lövbər variantı, pozitiv"),
    "positive_control": T("Positive control", "Pozitiv nəzarət"),
    "structured_pipe_table": T("Structured: pipe table", "Strukturlu: | cədvəli"),
    "structured_json_config": T("Structured: JSON config", "Strukturlu: JSON"),
    "structured_dialogue": T("Structured: dialogue", "Strukturlu: dialoq"),
    "structured_csv": T("Structured: CSV", "Strukturlu: CSV"),
    "structured_technical_log": T("Structured: technical log", "Strukturlu: texniki log"),
    "corrected_hard_negative": T("Corrected hard negative", "Düzəldilmiş çətin neqativ"),
}

bench = D["bench"]
cats = bench["categories"]
sl = D["slices"]["_benchmark_category"]
cat_rows = []
for k, n in cats:
    a, b = sl["ckpt1"].get(k), sl["runb"].get(k)
    if not a or not b:
        continue
    cat_rows.append((CAT_NAMES.get(k, k), a["exact"]["f1"] * 100, b["exact"]["f1"] * 100, n,
                     a["exact"]["recall"], b["exact"]["recall"], a["exact"]["precision"], b["exact"]["precision"]))

dg = D["diag"]
cvv_plain, cvv_dash = dg["cvv"]["plain digits"], dg["cvv"]["dashed (99-9)"]
fin_other, fin_word = dg["fin"]["after other words"], dg["fin"]["right after the word FIN"]

drops = [(k, L[k]["ckpt1"]["recall"], L[k]["runb"]["recall"]) for k in L if L[k]["runb"]["recall"] < L[k]["ckpt1"]["recall"] - 0.01]
drops.sort(key=lambda r: r[2] - r[1])

GEMMA = [("ACCESS_TOKEN", 0.0, 0.0), ("PRIVATE_KEY", 90.7, 3.4), ("DATE", 57.5, 29.1), ("IPV6_ADDRESS", 18.0, 73.4),
         ("AZ_DRIVER_LICENSE_NUMBER", 40.4, 59.3), ("EMAIL", 92.8, 66.3), ("CITY", 79.7, 57.9), ("GIVENNAME", 75.1, 91.0)]

PROBES = [
    ("contrast_ipv6_mac", T("IPv6 recall 53.8; MAC 63.6; IPv6 read as MAC 15.4%", "IPv6 recall 53,8; MAC 63,6; IPv6-nın MAC kimi oxunması 15,4%"), T("IPv6 and MAC ≥ 80", "IPv6 və MAC ≥ 80")),
    ("contrast_token_key", T("ACCESS_TOKEN recall 25.0; token read as key 62.5%", "ACCESS_TOKEN recall 25,0; tokenin açar kimi oxunması 62,5%"), T("≥ 80; confusion < 10%", "≥ 80; qarışdırma < 10%")),
    ("contrast_licence_id", T("licence recall 33.3; licence read as ID 58.3%", "vəsiqə recall 33,3; vəsiqənin ŞV kimi oxunması 58,3%"), T("confusion < 5%", "qarışdırma < 5%")),
    ("noisy_suffixes", T("recall 45.8", "recall 45,8"), "≥ 85"),
    ("homograph_pairs", T("recall 68.8; ordinary words masked 43.8%", "recall 68,8; adi sözlərin maskalanması 43,8%"), T("≥ 90; < 10%", "≥ 90; < 10%")),
    ("date_vs_timestamp", T("DATE recall 93.8; timestamps tagged DATE 22.2%", "DATE recall 93,8; zaman damğalarının DATE kimi işarələnməsi 22,2%"), T("trigger < 15%", "tətik < 15%")),
    ("villages", T("recall 57.7", "recall 57,7"), "≥ 80"),
    ("foreign_names", T("recall 65.0 (Georgian 50, Russian 60)", "recall 65,0 (gürcü 50, rus 60)"), "≥ 80"),
]

css = """
@page { size: A4; margin: 16mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, "Helvetica Neue", Helvetica, Arial, sans-serif; color: #1f2933; font-size: 10.2pt; line-height: 1.5; margin: 0; }
h1 { font-size: 25pt; line-height: 1.15; margin: 0 0 6mm; color: #0f3d4c; letter-spacing: -.3px; }
h2 { break-after: avoid; page-break-after: avoid; font-size: 15pt; color: #0f3d4c; margin: 0 0 3mm; padding-top: 1mm; border-bottom: 2px solid #1f6f8b; padding-bottom: 1.5mm; }
h3 { font-size: 11.5pt; color: #1f6f8b; margin: 4mm 0 1.6mm; break-after: avoid; page-break-after: avoid; }
p { margin: 0 0 2.6mm; }
section { page-break-before: always; }
section.first { page-break-before: auto; }
.cover { height: 255mm; display: flex; flex-direction: column; justify-content: space-between; }
.kicker { font-size: 9pt; letter-spacing: 1.6px; text-transform: uppercase; color: #1f6f8b; font-weight: 700; margin-bottom: 4mm; }
.sub { font-size: 12.5pt; color: #52606d; max-width: 150mm; }
.meta { font-size: 9pt; color: #52606d; border-top: 1px solid #cbd2d9; padding-top: 3mm; }
.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; margin: 6mm 0; }
.kpi { background: #f0f6f8; border-radius: 6px; padding: 4mm; }
.kpi .v { font-size: 20pt; font-weight: 700; color: #0f3d4c; line-height: 1.1; }
.kpi .v small { font-size: 11pt; color: #7b8794; font-weight: 600; }
.kpi .k { font-size: 8.6pt; color: #52606d; margin-top: 1mm; }
.kpi.bad { background: #fff4ed; } .kpi.bad .v { color: #c2410c; }
table { width: 100%; border-collapse: collapse; margin: 1.5mm 0 3mm; font-size: 8.5pt; page-break-inside: auto; }
th { text-align: left; background: #f0f4f8; color: #334e68; font-weight: 600; padding: 1.3mm 2mm; border-bottom: 1px solid #bcccdc; }
td { padding: 1.05mm 2mm; border-bottom: 1px solid #e4e7eb; vertical-align: top; }
tr { page-break-inside: avoid; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.up { color: #1f7a4d; font-weight: 600; } .dn { color: #c2410c; font-weight: 600; }
.box { background: #f7f9fa; border-left: 3px solid #1f6f8b; padding: 3mm 4mm; margin: 3mm 0 4mm; page-break-inside: avoid; }
.box.warn { border-left-color: #c2410c; background: #fff8f3; }
.box p:last-child { margin-bottom: 0; }
.chart { width: 100%; height: auto; margin: 2mm 0 3mm; font-family: inherit; }
.chart .lb { font-size: 10.5px; fill: #334e68; } .chart .vl { font-size: 9.5px; fill: #52606d; }
.chart .ax { font-size: 9px; fill: #9aa5b1; } .chart .lg { font-size: 10px; fill: #52606d; }
.cap { font-size: 8.5pt; color: #7b8794; margin: -1mm 0 4mm; }
code { font-family: "SF Mono", Menlo, monospace; font-size: 8.6pt; background: #f0f4f8; padding: 0 1mm; border-radius: 2px; }
ul { margin: 0 0 3mm; padding-left: 5mm; } li { margin-bottom: 1mm; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 6mm; }
.small { font-size: 8.8pt; color: #52606d; }
.toc li { margin-bottom: .6mm; }
table.app { font-size: 7.6pt; } table.app td, table.app th { white-space: nowrap; padding: .85mm 1.3mm; }
"""

H = []
add = H.append

# ---- cover
add(f"""<section class="first cover"><div>
<div class="kicker">{T("PII masking · Azerbaijani · Remediation sprint", "Şəxsi məlumatların maskalanması · Azərbaycan dili · Düzəliş sprinti")}</div>
<h1>{T("Benchmark report:<br>checkpoint 1 vs Run B", "Benchmark hesabatı:<br>checkpoint 1 və Run B")}</h1>
<p class="sub">{T("What the benchmark measures, how we scored it, what changed between the two models, and where Run B still falls short.",
                  "Benchmarkın nəyi ölçdüyü, onu necə qiymətləndirdiyimiz, iki model arasında nəyin dəyişdiyi və Run B-nin hələ harada geri qaldığı.")}</p>
<div class="kpis">
 <div class="kpi"><div class="v">{dec(m1['f1']*100)} <small>→</small> {dec(mb['f1']*100)}</div><div class="k">{T(f"Exact micro F1, track R (track M: {dec(mm1['f1']*100)} → {dec(mmb['f1']*100)})", f"Dəqiq micro F1, R izi (M izi: {dec(mm1['f1']*100)} → {dec(mmb['f1']*100)})")}</div></div>
 <div class="kpi"><div class="v">{dec(c1['decoys']['rate_same_label']*100)}% <small>→</small> {dec(rb['decoys']['rate_same_label']*100)}%</div><div class="k">{T("Look-alikes masked with the label they imitate", "Təqlid etdiyi etiketlə maskalanan oxşar dəyərlər")}</div></div>
 <div class="kpi"><div class="v">{dec(c1['docs']['pii_free_fp_rate']*100)}% <small>→</small> {dec(rb['docs']['pii_free_fp_rate']*100)}%</div><div class="k">{T("PII-free documents with a false alarm", "Yalançı siqnal alan PII-siz sənədlər")}</div></div>
 <div class="kpi"><div class="v">{dec(c1['leak']*100)}% <small>→</small> {dec(rb['leak']*100)}%</div><div class="k">{T("PII characters left unmasked", "Maskalanmamış qalan PII simvolları")}</div></div>
 <div class="kpi"><div class="v">{dec(c1['docs']['perfect_rate']*100)}% <small>→</small> {dec(rb['docs']['perfect_rate']*100)}%</div><div class="k">{T("Documents with every value exactly right", "Bütün dəyərləri tam düzgün olan sənədlər")}</div></div>
 <div class="kpi bad"><div class="v">{dec(drops[0][1]*100)} <small>→</small> {dec(drops[0][2]*100)}</div><div class="k">{T("AZ_FIN recall: one of two labels that got worse", "AZ_FIN recall: pisləşən iki etiketdən biri")}</div></div>
</div></div>
<div class="meta">{T("Prepared for the team, 9 October 2026. Model compared: <code>your-hf-org/masking-az-runb-v2-seed42-2ep</code> @ <code>937f29d</code> against checkpoint 1 <code>your-hf-org/masking-multilingual</code> @ <code>3a0a6e5</code>. Benchmark: first 5,000 documents of <code>benchmark_v3</code>. Sources: <code>reports/scoreboard/</code>, <code>docs/go_no_go.md</code>. No figure from the private shadow, sealed or real-text sets appears here.",
 "Komanda üçün hazırlanıb, 9 oktyabr 2026. Müqayisə olunan model: <code>your-hf-org/masking-az-runb-v2-seed42-2ep</code> @ <code>937f29d</code>, checkpoint 1 isə <code>your-hf-org/masking-multilingual</code> @ <code>3a0a6e5</code>. Benchmark: <code>benchmark_v3</code> faylının ilk 5 000 sənədi. Mənbələr: <code>reports/scoreboard/</code>, <code>docs/go_no_go.md</code>. Şəxsi shadow, sealed və real mətn dəstlərindən heç bir rəqəm burada yoxdur.")}</div>
</section>""")

# ---- contents + summary
add(f"""<section><h2>{T("Summary", "Xülasə")}</h2>
<p>{T(f"Run B is the model the team trained this sprint: <b>XLM-RoBERTa-large, trained from scratch on Azerbaijani data only</b>, using the training data rebuilt during the sprint. On the same 5,000 benchmark documents, scored with the same scorer, it reaches <b>{dec(mb['f1']*100)} exact micro F1 against checkpoint 1's {dec(m1['f1']*100)}</b>. Precision rises from {dec(m1['precision']*100)} to {dec(mb['precision']*100)} and recall from {dec(m1['recall']*100)} to {dec(mb['recall']*100)}. On track M, the product's own decoding, it reaches <b>{dec(mmb['f1']*100)} against {dec(mm1['f1']*100)}</b>.",
 f"Run B bu sprintdə komandanın öyrətdiyi modeldir: <b>XLM-RoBERTa-large, sıfırdan və yalnız Azərbaycan dilində məlumatla öyrədilib</b>, sprint ərzində yenidən qurulmuş təlim məlumatından istifadə olunub. Eyni 5 000 benchmark sənədində, eyni qiymətləndirici ilə o, <b>checkpoint 1-in {dec(m1['f1']*100)} göstəricisinə qarşı {dec(mb['f1']*100)} dəqiq micro F1</b> əldə edir. Precision {dec(m1['precision']*100)}-dən {dec(mb['precision']*100)}-ə, recall isə {dec(m1['recall']*100)}-dən {dec(mb['recall']*100)}-ə yüksəlir. Məhsulun öz dekodlaması olan M izində o, <b>{dec(mm1['f1']*100)} göstəricisinə qarşı {dec(mmb['f1']*100)}</b> əldə edir.")}</p>
<p>{T("The labels the sprint targeted improved the most: ACCESS_TOKEN from 0 to 98.7, IPv6 from 18.0 to 95.3, the driver's licence from 40.4 to 92.9, API keys from 49.7 to 98.0, dates from 57.5 to 88.1. Look-alike values that must not be masked are now triggered 4.1% of the time instead of 17.0%.",
 "Sprintin hədəf aldığı etiketlər ən çox yaxşılaşıb: ACCESS_TOKEN 0-dan 98,7-yə, IPv6 18,0-dan 95,3-ə, sürücülük vəsiqəsi 40,4-dən 92,9-a, API açarları 49,7-dən 98,0-a, tarixlər 57,5-dən 88,1-ə. Maskalanmamalı olan oxşar dəyərlər artıq 17,0% əvəzinə 4,1% hallarda tətiklənir.")}</p>
<div class="box warn"><p><b>{T("Two labels got worse.", "İki etiket pisləşib.")}</b> {T(
 f"AZ_FIN recall fell from {dec(drops[0][1]*100)} to {dec(drops[0][2]*100)} and CARD_SECURITY_CODE recall from {dec(drops[1][1]*100)} to {dec(drops[1][2]*100)}. ZIPCODE fell by 1.04 points, just over the limit. The team's go/no-go rules (D-29) block any label whose recall drops more than one point below checkpoint 1's, because a missed value is worse than a false alarm. Section 6 traces both drops to the training data.",
 f"AZ_FIN recall {dec(drops[0][1]*100)}-dən {dec(drops[0][2]*100)}-ə, CARD_SECURITY_CODE recall isə {dec(drops[1][1]*100)}-dən {dec(drops[1][2]*100)}-ə düşüb. ZIPCODE 1,04 bal düşüb, həddən bir az çox. Komandanın buraxılış qaydaları (D-29) recall-u checkpoint 1-dən bir baldan çox düşən hər etiketi bloklayır, çünki buraxılmış dəyər yalançı siqnaldan pisdir. 6-cı bölmə hər iki düşüşü təlim məlumatına qədər izləyir.")}</p></div>
<p>{T("This report covers the public benchmark only. The independent shadow set, the sealed set, the real-text set and the probe families decide the release (section 9), and Run B has not yet been scored on them.",
 "Bu hesabat yalnız açıq benchmarkı əhatə edir. Buraxılış barədə qərarı komandanın müstəqil shadow dəsti, sealed dəst, real mətn dəsti və probe ailələri verir (9-cu bölmə); Run B hələ onlarda qiymətləndirilməyib.")}</p>
<h3>{T("Contents", "Mündəricat")}</h3>
<ol class="toc">
<li>{T("Why there was a sprint", "Sprint niyə lazım oldu")}</li>
<li>{T("The benchmark", "Benchmark")}</li>
<li>{T("How scoring works", "Qiymətləndirmə necə aparılır")}</li>
<li>{T("What changed between the two models", "İki model arasında nə dəyişdi")}</li>
<li>{T("Results", "Nəticələr")}</li>
<li>{T("The two labels that got worse", "Pisləşən iki etiket")}</li>
<li>{T("Same data, different model: Gemma", "Eyni məlumat, fərqli model: Gemma")}</li>
<li>{T("Other measurements", "Digər ölçmələr")}</li>
<li>{T("How the release is decided", "Buraxılış necə qərara alınır")}</li>
<li>{T("Limits of this report and next steps", "Hesabatın hüdudları və növbəti addımlar")}</li>
<li>{T("Appendix: every label", "Əlavə: bütün etiketlər")}</li>
</ol></section>""")

# ---- 1 background
add(f"""<section><h2>1. {T("Why there was a sprint", "Sprint niyə lazım oldu")}</h2>
<p>{T("Checkpoint 1 (<code>your-hf-org/masking-multilingual</code>) is the production model. It labels personal data in text (names, card numbers, IBANs, Azerbaijani IDs, addresses, keys) so the text can be masked. On its own held-out test it scored 98.6%. An outside team then built an Azerbaijani benchmark it had never seen, and it scored <b>68.4</b> (68.7 with our scorer, see section 3).",
 "Checkpoint 1 (<code>your-hf-org/masking-multilingual</code>) istehsalatda olan modeldir. O, mətndəki şəxsi məlumatları (adlar, kart nömrələri, IBAN-lar, Azərbaycan şəxsiyyət sənədləri, ünvanlar, açarlar) işarələyir ki, mətn maskalana bilsin. Öz test dəstində 98,6% göstərmişdi. Sonra kənar komanda onun heç görmədiyi Azərbaycan dilində benchmark hazırladı və model <b>68,4</b> göstərdi (bizim qiymətləndirici ilə 68,7, bax 3-cü bölmə).")}</p>
<p>{T("The gap had one main cause: the model's own test came from the same generator as its training data, so it rewarded memorised patterns. The team traced the failures to nine root causes:",
 "Bu fərqin əsas səbəbi bir idi: modelin öz testi təlim məlumatı ilə eyni generatordan gəlirdi, ona görə də əzbərlənmiş nümunələri mükafatlandırırdı. Komanda uğursuzluqları doqquz əsas səbəbə bağladı:")}</p>
{table([T("Root cause","Əsas səbəb"), T("What went wrong","Nə səhv getdi")], [
 ["RC1", T("It masked look-alikes. The training data had none, by a deliberate setting (<code>hard_negative_rate = 0</code>).", "Oxşar dəyərləri maskalayırdı. Təlim məlumatında qəsdən bir ayarla (<code>hard_negative_rate = 0</code>) onlar yox idi.")],
 ["RC2", T("It judged by shape, not by the surrounding words (<code>otaq 247</code> masked as a building number).", "Ətraf sözlərə deyil, formaya görə qərar verirdi (<code>otaq 247</code> bina nömrəsi kimi maskalanırdı).")],
 ["RC3", T("It confused look-alike types: token vs API key, IPv6 vs MAC, licence vs ID card.", "Oxşar tipləri qarışdırırdı: token və API açarı, IPv6 və MAC, sürücülük vəsiqəsi və şəxsiyyət vəsiqəsi.")],
 ["RC4", T("It missed values in unfamiliar sentences and structured formats.", "Tanış olmayan cümlələrdə və strukturlu formatlarda dəyərləri buraxırdı.")],
 ["RC5", T("It cut long values into pieces (PEM keys, spaced phone and card numbers).", "Uzun dəyərləri hissələrə bölürdü (PEM açarları, boşluqlu telefon və kart nömrələri).")],
 ["RC6", T("It missed noisy text: lower case, missing Azerbaijani letters.", "Səs-küylü mətni buraxırdı: kiçik hərflər, Azərbaycan hərfləri olmadan yazılış.")],
 ["RC7", T("Its own test shared a generator with training, so it could not see RC1–RC6.", "Öz testi təlimlə eyni generatoru paylaşırdı, ona görə RC1–RC6-nı görə bilmirdi.")],
 ["RC8", T("Names, cities and streets almost never carried a case suffix (7–12% of mentions).", "Adlar, şəhərlər və küçələr demək olar ki, hal şəkilçisi almırdı (hallarının 7–12%-i).")],
 ["RC9", T("It missed names standing alone and confused names that are also ordinary words.", "Tək duran adları buraxır, eyni zamanda adi söz olan adları qarışdırırdı.")],
])}
<p>{T("A separate finding came later in the sprint: the benchmark labels every standalone date, while our old data left most of them unlabelled (D-17). That taught the model to skip dates.",
 "Ayrıca bir tapıntı sprintin sonrakı mərhələsində gəldi: benchmark hər müstəqil tarixi işarələyir, köhnə məlumatımız isə onların əksəriyyətini işarələnməmiş qoyurdu (D-17). Bu, modelə tarixləri keçməyi öyrədirdi.")}</p>
</section>""")

# ---- 2 benchmark
lab_counts = dict(bench["labels"])
add(f"""<section><h2>2. {T("The benchmark", "Benchmark")}</h2>
<p>{T(f"<code>benchmark_v3</code> was written by an outside team: 9,780 synthetic Azerbaijani documents with every personal value marked by character position. Following decision D-6, we score the <b>first 5,000 documents</b>. They contain <b>{num(bench['gold'])} labelled values</b> across 27 labels, <b>{num(bench['pii_free'])} documents with no personal data at all</b>, and <b>9,304 planted look-alikes</b>: strings shaped like a card, a time or a FIN that are deliberately not personal data and must not be masked.",
 f"<code>benchmark_v3</code> kənar komanda tərəfindən hazırlanıb: hər şəxsi dəyəri simvol mövqeyi ilə işarələnmiş 9 780 sintetik Azərbaycan dilli sənəd. D-6 qərarına əsasən biz <b>ilk 5 000 sənədi</b> qiymətləndiririk. Onlarda 27 etiket üzrə <b>{num(bench['gold'])} işarələnmiş dəyər</b>, <b>heç bir şəxsi məlumat olmayan {num(bench['pii_free'])} sənəd</b> və <b>9 304 yerləşdirilmiş oxşar dəyər</b> var: kart, saat və ya FIN kimi görünən, amma qəsdən şəxsi məlumat olmayan və maskalanmamalı olan sətirlər.")}</p>
<div class="two"><div>
<h3>{T("The 27 labels", "27 etiket")}</h3>
<p class="small">{T("People: GIVENNAME, SURNAME. Places: CITY, STREET, BUILDINGNUM, ZIPCODE. Contact: TELEPHONENUM, EMAIL, URL. Time: DATE, TIME, AGE. Azerbaijani IDs: AZ_FIN, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, AZ_VOEN, AZ_DRIVER_LICENSE_NUMBER. Money and network: PAYMENT_CARD_NUMBER, IBAN, CARD_SECURITY_CODE, ICCID, IPV4_ADDRESS, IPV6_ADDRESS, MAC_ADDRESS. Secrets: API_KEY, ACCESS_TOKEN, PRIVATE_KEY. Each label has 300–450 values, so every label counts roughly equally.",
 "İnsanlar: GIVENNAME, SURNAME. Yerlər: CITY, STREET, BUILDINGNUM, ZIPCODE. Əlaqə: TELEPHONENUM, EMAIL, URL. Zaman: DATE, TIME, AGE. Azərbaycan sənədləri: AZ_FIN, AZ_ID_CARD_NUMBER, AZ_PASSPORT_NUMBER, AZ_VOEN, AZ_DRIVER_LICENSE_NUMBER. Pul və şəbəkə: PAYMENT_CARD_NUMBER, IBAN, CARD_SECURITY_CODE, ICCID, IPV4_ADDRESS, IPV6_ADDRESS, MAC_ADDRESS. Gizli məlumatlar: API_KEY, ACCESS_TOKEN, PRIVATE_KEY. Hər etiketin 300–450 dəyəri var, ona görə etiketlər təxminən bərabər çəkiyə malikdir.")}</p>
</div><div>
<h3>{T("Document categories", "Sənəd kateqoriyaları")}</h3>
{table([T("Category","Kateqoriya"), T("Docs","Sənəd")], [[CAT_NAMES.get(k,k), f'<span style="float:right">{num(n)}</span>'] for k,n in cats], "")}
</div></div>
<p>{T("The categories are built to test specific failures: <i>hard negatives</i> are documents full of look-alikes; <i>anchor variants</i> change the word that introduces a value (<code>tarixini</code>, <code>FİN kodum</code>); <i>natural variants</i> add typos, missing Azerbaijani letters and odd casing; the <i>structured</i> categories put values in tables, JSON, CSV, logs and dialogue.",
 "Kateqoriyalar konkret uğursuzluqları yoxlamaq üçün qurulub: <i>çətin neqativlər</i> oxşar dəyərlərlə dolu sənədlərdir; <i>lövbər variantları</i> dəyəri təqdim edən sözü dəyişir (<code>tarixini</code>, <code>FİN kodum</code>); <i>təbii variantlar</i> yazı səhvləri, Azərbaycan hərflərinin olmaması və qeyri-adi böyük-kiçik hərflər əlavə edir; <i>strukturlu</i> kateqoriyalar dəyərləri cədvəllərə, JSON, CSV, loglara və dialoqa yerləşdirir.")}</p>
<div class="box"><p><b>{T("It never touched training.", "Təlimə heç vaxt toxunmayıb.")}</b> {T("The leakage guard (<code>eval/leakage_guard.py</code>) checks every training file against every benchmark value and every eight-word sequence before training. Run B's corpus passed with 0 matches. The builder also rejects any generated document that would match, which caught one URL and one IPv6 address during the sprint.",
 "Sızma qoruyucusu (<code>eval/leakage_guard.py</code>) təlimdən əvvəl hər təlim faylını hər benchmark dəyəri və hər səkkiz sözlük ardıcıllıqla müqayisə edir. Run B-nin korpusu 0 uyğunluqla keçdi. Generator da uyğun gələcək hər yaradılmış sənədi rədd edir; sprint ərzində bu, bir URL və bir IPv6 ünvanını tutdu.")}</p></div>
</section>""")

# ---- 3 scoring
add(f"""<section><h2>3. {T("How scoring works", "Qiymətləndirmə necə aparılır")}</h2>
<p>{T("the team wrote the scorer, <code>eval/scoreboard.py</code>. It runs a model over the documents, compares every prediction with the marked values and writes a report. The main rules:",
 "Qiymətləndiricini komanda yazıb: <code>eval/scoreboard.py</code>. O, modeli sənədlər üzərində işə salır, hər proqnozu işarələnmiş dəyərlərlə müqayisə edir və hesabat yazır. Əsas qaydalar:")}</p>
{table([T("Measure","Ölçü"), T("What it means","Mənası")], [
 [T("<b>Exact</b> precision, recall, F1","<b>Dəqiq</b> precision, recall, F1"), T("A prediction counts only if the label, the start and the end all match. A date cut one character short is wrong. This is the headline number.", "Proqnoz yalnız etiket, başlanğıc və son tam uyğun gəldikdə sayılır. Bir simvol qısa kəsilmiş tarix səhvdir. Əsas rəqəm budur.")],
 [T("<b>Micro</b> vs <b>macro</b> F1","<b>Micro</b> və <b>macro</b> F1"), T("Micro pools every value; macro averages the 27 labels equally.", "Micro bütün dəyərləri birləşdirir; macro 27 etiketin orta qiymətini bərabər çəki ilə götürür.")],
 [T("<b>Overlap</b> F1","<b>Üst-üstə düşmə</b> F1"), T("Any shared character with the right label counts. More lenient; shows how much is boundary error.", "Düzgün etiketlə istənilən ortaq simvol sayılır. Daha yumşaqdır; xətanın nə qədərinin sərhəd səhvi olduğunu göstərir.")],
 [T("<b>Look-alike trigger rate</b>","<b>Oxşar dəyər tətik dərəcəsi</b>"), T("Share of the 9,304 planted look-alikes masked with the label they imitate (any label in brackets).", "9 304 yerləşdirilmiş oxşar dəyərdən təqlid etdiyi etiketlə maskalananların payı (mötərizədə istənilən etiket).")],
 [T("<b>PII-free false alarms</b>","<b>PII-siz yalançı siqnallar</b>"), T("Share of the 612 documents with no personal data that still get a prediction.", "Heç bir şəxsi məlumat olmayan 612 sənəddən yenə də proqnoz alanların payı.")],
 [T("<b>Character leakage</b>","<b>Simvol sızması</b>"), T("Share of personal-data characters left unmasked: the privacy view.", "Maskalanmamış qalan şəxsi məlumat simvollarının payı: məxfilik baxımı.")],
])}
<h3>{T("Two tracks", "İki iz")}</h3>
<p>{T("<b>Track R</b> runs the raw Hugging Face pipeline, exactly the path the benchmark team used; every gate uses it. <b>Track M</b> uses the product's own decoding (model only, no regex): closer to what users get. Both models are scored on both tracks.",
 "<b>R izi</b> xam Hugging Face pipeline-ını işə salır, benchmark komandasının istifadə etdiyi yolun eynisi; bütün meyarlar ondan istifadə edir. <b>M izi</b> məhsulun öz dekodlamasından istifadə edir (yalnız model, regex yoxdur): istifadəçinin aldığına daha yaxındır. Hər iki model hər iki izdə qiymətləndirilib.")}</p>
<h3>{T("Checking the scorer", "Qiymətləndiricinin yoxlanması")}</h3>
<p>{T("Before trusting any comparison, the scorer had to reproduce the benchmark team's own result for checkpoint 1. It reproduced 94 of the 94 errors listed in their report, and gave 68.7 exact micro F1 against their 68.4; our copy of the file carries the team's corrections (10,518 values here, 10,438 in their report).",
 "Hər hansı müqayisəyə etibar etməzdən əvvəl qiymətləndirici benchmark komandasının checkpoint 1 üçün öz nəticəsini təkrarlamalı idi. O, onların hesabatında sadalanan 94 xətanın 94-ünü təkrarladı və onların 68,4 göstəricisinə qarşı 68,7 dəqiq micro F1 verdi; bizim fayl nüsxəmizdə komandanın düzəlişləri var (burada 10 518, onların hesabatında 10 438 dəyər).")}</p>
<h3>{T("How the two models were run", "İki model necə işə salındı")}</h3>
{table([T("","" ), T("Checkpoint 1","Checkpoint 1"), "Run B"], [
 [T("Model","Model"), "<code>your-hf-org/masking-multilingual</code> @ <code>3a0a6e5</code>", "<code>your-hf-org/masking-az-runb-v2-seed42-2ep</code> @ <code>937f29d</code>"],
 [T("Who ran it, where","Kim, harada işə salıb"), T("the team, laptop CPU, 7 Oct","Komanda, noutbuk CPU, 7 okt"), T("the team, MacBook Air (Apple GPU), 9 Oct","Komanda, MacBook Air (Apple GPU), 9 okt")],
 [T("Documents, tracks","Sənədlər, izlər"), T("first 5,000; R and M","ilk 5 000; R və M"), T("first 5,000; R and M","ilk 5 000; R və M")],
 [T("Report","Hesabat"), "<code>baseline_ckpt1_benchmark.md</code>", "<code>runb_az_v2_seed42_2ep.md</code>"],
])}
</section>""")

# ---- 4 what changed
add(f"""<section><h2>4. {T("What changed between the two models", "İki model arasında nə dəyişdi")}</h2>
<p>{T("Only two things changed: the training data, and the decision to train from the base model on Azerbaijani only (D-23). The model type stayed XLM-RoBERTa-large (D-24).",
 "Yalnız iki şey dəyişdi: təlim məlumatı və baza modeldən yalnız Azərbaycan dilində öyrətmək qərarı (D-23). Model tipi XLM-RoBERTa-large olaraq qaldı (D-24).")}</p>
{table([T("","" ), T("Checkpoint 1","Checkpoint 1"), "Run B"], [
 [T("Starting point","Başlanğıc nöqtəsi"), "XLM-RoBERTa-large", T("XLM-RoBERTa-large, from scratch","XLM-RoBERTa-large, sıfırdan")],
 [T("Languages","Dillər"), T("Azerbaijani, English, Turkish, Russian (personal data always Azerbaijani)","Azərbaycan, ingilis, türk, rus (şəxsi məlumat həmişə Azərbaycan dilində)"), T("Azerbaijani only","Yalnız Azərbaycan dili")],
 [T("Training documents","Təlim sənədləri"), T("about 333,000","təxminən 333 000"), num(127439)],
 [T("Look-alikes in training","Təlimdə oxşar dəyərlər"), T("none","yoxdur"), T("in 36.7% of new documents","yeni sənədlərin 36,7%-ində")],
 [T("Standalone dates","Müstəqil tarixlər"), T("mostly unlabelled","əsasən işarələnməmiş"), T("all labelled (D-17)","hamısı işarələnib (D-17)")],
 [T("Settings","Ayarlar"), "—", T("2 epochs, LR 2e-5, cosine, warmup 0.1, batch 32, bf16, seed 42, RTX 5090","2 epoxa, LR 2e-5, cosine, warmup 0,1, batch 32, bf16, seed 42, RTX 5090")],
])}
<h3>{T("Run B's training data (<code>runb-az-v2</code>, D-28)", "Run B-nin təlim məlumatı (<code>runb-az-v2</code>, D-28)")}</h3>
{table([T("Source","Mənbə"), T("Train","Təlim"), T("Val","Val"), T("Test","Test"), T("What it is","Nədir")], [
 [T("Old corpus","Köhnə korpus"), num(72152), num(8979), num(8935), T("The original Azerbaijani documents, after an audit dropped 15,347 that failed today's checks","Orijinal Azərbaycan sənədləri; audit bugünkü yoxlamalardan keçməyən 15 347 sənədi çıxardıqdan sonra")],
 [T("LLM-written","LLM ilə yazılmış"), num(35210), num(4419), num(4461), T("Five batches written by an LLM from planned briefs, then audited and cleaned","Planlaşdırılmış təsvirlərdən LLM ilə yazılmış beş partiya, sonra audit edilib və təmizlənib")],
 [T("Targeted","Hədəfli"), num(20077), num(2484), num(2439), T("Template documents aimed at each failure: look-alike pairs, contrast pairs, structured formats, suffixes, homographs, full-length keys","Hər uğursuzluğa yönəlmiş şablon sənədlər: oxşar dəyər cütləri, kontrast cütləri, strukturlu formatlar, şəkilçilər, omoqraflar, tam uzunluqlu açarlar")],
 [f"<b>{T('Total','Cəmi')}</b>", f"<b>{num(127439)}</b>", f"<b>{num(15882)}</b>", f"<b>{num(15835)}</b>", T("New data is 43.4% of train","Yeni məlumat təlimin 43,4%-idir")],
])}
<h3>{T("The data fixes, by root cause", "Əsas səbəbə görə məlumat düzəlişləri")}</h3>
{table([T("Fix","Düzəliş"), T("Addresses","Hədəfi"), T("Decision","Qərar")], [
 [T("Look-alike decoys next to real values; 10% documents with no personal data","Real dəyərlərin yanında oxşar dəyərlər; heç bir şəxsi məlumat olmayan 10% sənəd"), "RC1, RC2", "D-1"],
 [T("New value formats: <code>at_</code>/<code>bearer_</code> tokens, <code>::</code>-compressed IPv6, licence prefixes","Yeni dəyər formatları: <code>at_</code>/<code>bearer_</code> tokenlər, <code>::</code> ilə qısaldılmış IPv6, vəsiqə prefiksləri"), "RC3", "P2-1"],
 [T("Contrast pairs in one document: token+key, IPv6+MAC, licence+ID","Bir sənəddə kontrast cütləri: token+açar, IPv6+MAC, vəsiqə+ŞV"), "RC3", "P2-6"],
 [T("419 sentence frames, inflected anchors, anchors at a distance; structured layouts","419 cümlə çərçivəsi, hallanmış lövbərlər, uzaqdakı lövbərlər; strukturlu tərtibatlar"), "RC4", "P4-1, P2-4"],
 [T("Case suffixes on names, cities and streets (labelled with the suffix), noisy suffixes","Adlarda, şəhərlərdə və küçələrdə hal şəkilçiləri (şəkilçi ilə birlikdə işarələnir), səhv şəkilçilər"), "RC8", "D-9, P2-4c"],
 [T("Bare names and 56 homograph names (Bayram, Ümid, Dəniz)","Tək adlar və 56 omoqraf ad (Bayram, Ümid, Dəniz)"), "RC9", "D-10, P4-2"],
 [T("Every standalone date labelled; timestamps left unlabelled","Hər müstəqil tarix işarələnib; zaman damğaları işarələnməyib"), T("dates","tarixlər"), "D-17, D-18"],
 [T("4,414 Azerbaijani settlements and foreign cities (was 97 cities)","4 414 Azərbaycan yaşayış məntəqəsi və xarici şəhərlər (əvvəl 97 şəhər)"), "CITY", "D-23c"],
 [T("Foreign names for 10–15% of people","İnsanların 10–15%-i üçün xarici adlar"), T("names","adlar"), "D-23d"],
 [T("Full-length RSA keys (was 134 characters at the median)","Tam uzunluqlu RSA açarları (əvvəl median uzunluq 134 simvol idi)"), "RC5", "D-27"],
 [T("Old corpus audited: 15,347 documents dropped","Köhnə korpus audit edildi: 15 347 sənəd çıxarıldı"), T("label quality","etiket keyfiyyəti"), "D-23b"],
])}
<p class="small">{T("Every data file was rebuilt on four machines with byte-identical SHA-256 checksums before training, so Run B trained on exactly the verified data.",
 "Təlimdən əvvəl hər məlumat faylı dörd maşında bayt-bayt eyni SHA-256 yoxlama cəmləri ilə yenidən quruldu; beləliklə Run B dəqiq yoxlanmış məlumat üzərində öyrədildi.")}</p>
</section>""")


def mrow(name, key, sub=None, pct_=True, good_up=True, fmtn=None):
    vals = []
    for o in (c1, rb, cm, rm):
        v = o[key] if sub is None else o[key][sub]
        vals.append(v)
    f = (lambda v: dec(v*100)+("%" if pct_=="%" else "")) if fmtn is None else fmtn
    return [name, f(vals[0]), f"<b>{f(vals[1])}</b>", f(vals[2]), f"<b>{f(vals[3])}</b>"]

# ---- 5 results
def rcol(k, w):
    return L[k][w]
f1rows = [(k, L[k]["ckpt1"]["f1"] * 100, L[k]["runb"]["f1"] * 100) for k in sorted(L, key=lambda k: L[k]["runb"]["f1"] - L[k]["ckpt1"]["f1"], reverse=True)]
r1, rb_ = c1["recall"], rb["recall"]
add(f"""<section><h2>5. {T("Results", "Nəticələr")}</h2>
{table([T("Measure (track R)","Ölçü (R izi)"), T("Checkpoint 1","Checkpoint 1"), "Run B", T("Change","Dəyişiklik")], [
 [T("Exact micro F1","Dəqiq micro F1"), dec(m1['f1']*100), f"<b>{dec(mb['f1']*100)}</b>", delta(m1['f1'], mb['f1'])],
 [T("Exact precision","Dəqiq precision"), dec(m1['precision']*100), dec(mb['precision']*100), delta(m1['precision'], mb['precision'])],
 [T("Exact recall","Dəqiq recall"), dec(m1['recall']*100), dec(mb['recall']*100), delta(m1['recall'], mb['recall'])],
 [T("Macro F1","Macro F1"), dec(c1['macro']*100), dec(rb['macro']*100), delta(c1['macro'], rb['macro'])],
 [T("Overlap micro F1","Üst-üstə micro F1"), dec(c1['overlap']['f1']*100), dec(rb['overlap']['f1']*100), delta(c1['overlap']['f1'], rb['overlap']['f1'])],
 [T("Look-alikes triggered, same label","Tətiklənən oxşar dəyərlər, eyni etiket"), dec(c1['decoys']['rate_same_label']*100)+"%", dec(rb['decoys']['rate_same_label']*100)+"%", delta(c1['decoys']['rate_same_label'], rb['decoys']['rate_same_label'], good_up=False)],
 [T("Look-alikes triggered, any label","Tətiklənən oxşar dəyərlər, istənilən etiket"), dec(c1['decoys']['rate_any_label']*100)+"%", dec(rb['decoys']['rate_any_label']*100)+"%", delta(c1['decoys']['rate_any_label'], rb['decoys']['rate_any_label'], good_up=False)],
 [T("PII-free documents with a false alarm","Yalançı siqnal alan PII-siz sənədlər"), f"{num(c1['docs']['pii_free_with_fp'])} / 612", f"{num(rb['docs']['pii_free_with_fp'])} / 612", delta(c1['docs']['pii_free_fp_rate'], rb['docs']['pii_free_fp_rate'], good_up=False)],
 [T("PII characters left unmasked","Maskalanmamış PII simvolları"), dec(c1['leak']*100)+"%", dec(rb['leak']*100)+"%", delta(c1['leak'], rb['leak'], good_up=False)],
 [T("Perfect documents","Tam düzgün sənədlər"), f"{num(c1['docs']['perfect_documents'])}", f"{num(rb['docs']['perfect_documents'])}", delta(c1['docs']['perfect_rate'], rb['docs']['perfect_rate'])],
], "")}
<h3>{T("Where the 10,518 values went", "10 518 dəyərin taleyi")}</h3>
{table([T("Outcome","Nəticə"), T("Checkpoint 1","Checkpoint 1"), "Run B"], [
 [T("Found exactly","Dəqiq tapılıb"), num(r1['exact_hits']), num(rb_['exact_hits'])],
 [T("Found with the right label, wrong boundary","Düzgün etiketlə, səhv sərhədlə"), num(r1['partial']), num(rb_['partial'])],
 [T("&nbsp;&nbsp;of which split into pieces","&nbsp;&nbsp;bunlardan hissələrə bölünmüş"), num(r1['split']), num(rb_['split'])],
 [T("Found with the wrong label","Səhv etiketlə tapılıb"), num(r1['wrong_label']), num(rb_['wrong_label'])],
 [T("Missed entirely","Tamamilə buraxılıb"), num(r1['missed']), num(rb_['missed'])],
])}
<p>{T(f"Wrong-label errors fell from {num(r1['wrong_label'])} to {num(rb_['wrong_label'])}: the type confusions (token as key, IPv6 as MAC, licence as ID) are almost gone. Missed values fell from {num(r1['missed'])} to {num(rb_['missed'])}. Boundary errors barely moved ({num(r1['partial'])} to {num(rb_['partial'])}); values split into pieces (RC5) remain a weakness.",
 f"Səhv etiket xətaları {num(r1['wrong_label'])}-dən {num(rb_['wrong_label'])}-ə düşüb: tip qarışıqlıqları (token açar kimi, IPv6 MAC kimi, vəsiqə ŞV kimi) demək olar ki, aradan qalxıb. Buraxılmış dəyərlər {num(r1['missed'])}-dən {num(rb_['missed'])}-ə düşüb. Sərhəd xətaları az dəyişib ({num(r1['partial'])}-dən {num(rb_['partial'])}-ə); hissələrə bölünmüş dəyərlər (RC5) zəif nöqtə olaraq qalır.")}</p>
</section>
<section><h2>5. {T("Results by label", "Etiketlər üzrə nəticələr")}</h2>
<p>{T("Exact F1 per label, sorted by the size of the change. Orange marks a label whose F1 fell.", "Hər etiket üzrə dəqiq F1, dəyişikliyin böyüklüyünə görə sıralanıb. Narıncı rəng F1-i düşən etiketi göstərir.")}</p>
{dumbbell(f1rows, T("Exact F1 per label","Etiket üzrə dəqiq F1"))}
<p class="cap">{T("Exact F1, track R, first 5,000 benchmark documents. Full numbers in the appendix.", "Dəqiq F1, R izi, benchmarkın ilk 5 000 sənədi. Tam rəqəmlər əlavədədir.")}</p>
</section>""")


add(f"""<section><h2>5. {T("Track M: the product path", "M izi: məhsul yolu")}</h2>
<p>{T("Track R is the official number for the rules. Track M decodes the same model's output with the product's own code, the way <code>pii_guard</code> masks text (model only, no regex), so it is closer to what users get. Both models were scored on both tracks with the same documents and scorer.",
 "R izi qaydalar üçün rəsmi rəqəmdir. M izi eyni modelin çıxışını məhsulun öz kodu ilə dekodlayır, <code>pii_guard</code>-ın mətni maskaladığı kimi (yalnız model, regex yoxdur), ona görə istifadəçinin aldığına daha yaxındır. Hər iki model eyni sənədlər və qiymətləndirici ilə hər iki izdə qiymətləndirilib.")}</p>
{table([T("Measure","Ölçü"), T("Checkpoint 1, R","Checkpoint 1, R"), "Run B, R", T("Checkpoint 1, M","Checkpoint 1, M"), "Run B, M"], [
 mrow(T("Exact micro F1","Dəqiq micro F1"), "micro", "f1"),
 mrow(T("Exact precision","Dəqiq precision"), "micro", "precision"),
 mrow(T("Exact recall","Dəqiq recall"), "micro", "recall"),
 mrow(T("Macro F1","Macro F1"), "macro"),
 mrow(T("Values missed","Buraxılmış dəyərlər"), "recall", "missed", fmtn=num),
 mrow(T("Values with the wrong label","Səhv etiketli dəyərlər"), "recall", "wrong_label", fmtn=num),
 mrow(T("Values with a wrong boundary or split","Səhv sərhədli və ya bölünmüş dəyərlər"), "recall", "partial", fmtn=num),
 [T("Look-alikes triggered, same label","Tətiklənən oxşar dəyərlər, eyni etiket")] + [dec(o["decoys"]["rate_same_label"]*100)+"%" for o in (c1, rb, cm, rm)],
 [T("PII-free documents with a false alarm","Yalançı siqnal alan PII-siz sənədlər")] + [dec(o["docs"]["pii_free_fp_rate"]*100)+"%" for o in (c1, rb, cm, rm)],
 [T("PII characters left unmasked","Maskalanmamış PII simvolları")] + [dec(o["leak"]*100)+"%" for o in (c1, rb, cm, rm)],
 [T("Perfect documents","Tam düzgün sənədlər")] + [num(o["docs"]["perfect_documents"]) for o in (c1, rb, cm, rm)],
])}
<p>{T(f"On track M, Run B reaches <b>{dec(mmb['f1']*100)}</b> against checkpoint 1's {dec(mm1['f1']*100)}. The difference from track R is almost all boundaries: values with a wrong boundary or split fall from {num(rb['recall']['partial'])} on R to {num(rm['recall']['partial'])} on M, because the product's decoding keeps a long value in one piece. Missed values ({num(rb['recall']['missed'])} → {num(rm['recall']['missed'])}) and wrong labels ({num(rb['recall']['wrong_label'])} on both) barely change: those come from the model, not the decoding.",
 f"M izində Run B checkpoint 1-in {dec(mm1['f1']*100)} göstəricisinə qarşı <b>{dec(mmb['f1']*100)}</b> əldə edir. R izindən fərq demək olar ki, tamamilə sərhədlərdədir: səhv sərhədli və ya bölünmüş dəyərlər R-də {num(rb['recall']['partial'])}-dən M-də {num(rm['recall']['partial'])}-ə düşür, çünki məhsulun dekodlaması uzun dəyəri bir hissədə saxlayır. Buraxılmış dəyərlər ({num(rb['recall']['missed'])} → {num(rm['recall']['missed'])}) və səhv etiketlər (hər ikisində {num(rb['recall']['wrong_label'])}) az dəyişir: onlar dekodlamadan yox, modeldən gəlir.")}</p>
<div class="box warn"><p><b>{T("The same three recall drops appear on track M.", "Eyni üç recall düşüşü M izində də görünür.")}</b> {T(
 f"AZ_FIN {dec(L['AZ_FIN']['ckpt1_M']['recall']*100)} → {dec(L['AZ_FIN']['runb_M']['recall']*100)}, CARD_SECURITY_CODE {dec(L['CARD_SECURITY_CODE']['ckpt1_M']['recall']*100)} → {dec(L['CARD_SECURITY_CODE']['runb_M']['recall']*100)}, ZIPCODE {dec(L['ZIPCODE']['ckpt1_M']['recall']*100)} → {dec(L['ZIPCODE']['runb_M']['recall']*100)}. A better decoding does not fix them, which confirms that their cause is in the training data (section 6).",
 f"AZ_FIN {dec(L['AZ_FIN']['ckpt1_M']['recall']*100)} → {dec(L['AZ_FIN']['runb_M']['recall']*100)}, CARD_SECURITY_CODE {dec(L['CARD_SECURITY_CODE']['ckpt1_M']['recall']*100)} → {dec(L['CARD_SECURITY_CODE']['runb_M']['recall']*100)}, ZIPCODE {dec(L['ZIPCODE']['ckpt1_M']['recall']*100)} → {dec(L['ZIPCODE']['runb_M']['recall']*100)}. Daha yaxşı dekodlama onları düzəltmir; bu, səbəblərinin təlim məlumatında olduğunu təsdiq edir (6-cı bölmə).")}</p></div>
</section>""")

# recall chart + decoys
rec_rows = [(k, L[k]["ckpt1"]["recall"] * 100, L[k]["runb"]["recall"] * 100) for k in sorted(L, key=lambda k: L[k]["runb"]["recall"] - L[k]["ckpt1"]["recall"], reverse=True)]
dec_rows = []
for k in L:
    a, b = L[k]["dec1"], L[k]["decb"]
    if a and a["decoys"] >= 150:
        dec_rows.append((k, a["rate_same_label"] * 100, b["rate_same_label"] * 100, a["decoys"]))
dec_rows.sort(key=lambda r: -r[1])
add(f"""<section><h2>5. {T("Recall: what each model finds", "Recall: hər modelin tapdığı")}</h2>
<p>{T("Recall matters most for a privacy tool: a missed value is leaked. The go/no-go rules block any label whose recall falls more than one point below checkpoint 1's.",
 "Məxfilik aləti üçün ən vacibi recall-dur: buraxılmış dəyər sızmış dəyərdir. Buraxılış qaydaları recall-u checkpoint 1-dən bir baldan çox düşən hər etiketi bloklayır.")}</p>
{dumbbell(rec_rows, T("Exact recall per label","Etiket üzrə dəqiq recall"))}
<p class="cap">{T("Exact recall, track R. Three labels fall more than one point: AZ_FIN, CARD_SECURITY_CODE and ZIPCODE.", "Dəqiq recall, R izi. Üç etiket bir baldan çox düşür: AZ_FIN, CARD_SECURITY_CODE və ZIPCODE.")}</p>
</section>
<section><h2>5. {T("Look-alikes: what each model wrongly masks", "Oxşar dəyərlər: hər modelin səhvən maskaladığı")}</h2>
<p>{T("Share of the planted look-alikes masked with the label they imitate (labels with at least 150 look-alikes). Lower is better. This was checkpoint 1's largest error class (RC1).",
 "Yerləşdirilmiş oxşar dəyərlərdən təqlid etdiyi etiketlə maskalananların payı (ən azı 150 oxşar dəyəri olan etiketlər). Aşağı olması yaxşıdır. Bu, checkpoint 1-in ən böyük xəta sinfi idi (RC1).")}</p>
{bars([(k, a, b) for k, a, b, n in dec_rows], T("Look-alike trigger rate","Oxşar dəyər tətik dərəcəsi"), maxv=max(r[1] for r in dec_rows)+8, fmt=lambda v: dec(v)+"%")}
<p class="cap">{T("Trigger with the same label, %. A planted look-alike is a string the benchmark declares as not personal data.", "Eyni etiketlə tətik, %. Yerləşdirilmiş oxşar dəyər benchmarkın şəxsi məlumat olmadığını bildirdiyi sətirdir.")}</p>
</section>""")

# categories
add(f"""<section><h2>5. {T("Results by document category", "Sənəd kateqoriyalarına görə nəticələr")}</h2>
{bars([(n, a, b) for n, a, b, *_ in cat_rows], T("Exact F1 by category","Kateqoriya üzrə dəqiq F1"))}
{table([T("Category","Kateqoriya"), T("Docs","Sənəd"), T("F1 before → after","F1 əvvəl → sonra"), T("Recall","Recall"), T("Precision","Precision")],
 [[n, f'<span style="float:right">{num(d)}</span>', f"{dec(a)} → <b>{dec(b)}</b>", f"{dec(ra*100)} → {dec(rb2*100)}", f"{dec(pa*100)} → {dec(pb*100)}"] for n, a, b, d, ra, rb2, pa, pb in cat_rows])}
<p>{T("Every category improved. The hardest remain the structured CSV documents and the hard negatives, where look-alikes sit next to real values.",
 "Bütün kateqoriyalar yaxşılaşıb. Ən çətin olanlar strukturlu CSV sənədləri və oxşar dəyərlərin real dəyərlərin yanında durduğu çətin neqativlər olaraq qalır.")}</p>
</section>""")

# ---- 6 regressions
add(f"""<section><h2>6. {T("The two labels that got worse", "Pisləşən iki etiket")}</h2>
<p>{T("Run B's saved predictions for every benchmark value were checked against the training data. Both drops have a clear cause in the data, which a fix round can address.",
 "Run B-nin hər benchmark dəyəri üçün yadda saxlanmış proqnozları təlim məlumatı ilə yoxlanıldı. Hər iki düşüşün məlumatda aydın səbəbi var və onu düzəliş mərhələsində həll etmək olar.")}</p>
<h3>CARD_SECURITY_CODE: {T("recall", "recall")} {dec(drops[1][1]*100)} → {dec(drops[1][2]*100)}</h3>
{table([T("CVV written as","CVV-nin yazılışı"), T("Values","Dəyərlər"), T("Run B finds","Run B tapır")], [
 [T("plain digits, e.g. <code>123</code>","adi rəqəmlər, məs. <code>123</code>"), num(cvv_plain[0]), f"{dec(cvv_plain[1]/cvv_plain[0]*100)}%"],
 [T("with a dash, e.g. <code>00-5</code>","tire ilə, məs. <code>00-5</code>"), num(cvv_dash[0]), f'<span class="dn">{dec(cvv_dash[1]/cvv_dash[0]*100)}%</span>'],
])}
<p>{T(f"Plain codes are fine. The benchmark also writes 80 codes with a dash, and Run B finds only 4 of them. <b>Run B's training data contains {num(dg['train_cvv_total'])} CVV values and none with a dash.</b> Checkpoint 1 masked any number after the word CVV; Run B learned to be more careful and so skips a format it has never seen.",
 f"Adi kodlarda problem yoxdur. Benchmark 80 kodu da tire ilə yazır və Run B onlardan yalnız 4-nü tapır. <b>Run B-nin təlim məlumatında {num(dg['train_cvv_total'])} CVV dəyəri var və heç biri tire ilə deyil.</b> Checkpoint 1 CVV sözündən sonra gələn istənilən rəqəmi maskalayırdı; Run B daha ehtiyatlı olmağı öyrənib və ona görə heç görmədiyi formatı keçir.")}</p>
<h3>AZ_FIN: {T("recall", "recall")} {dec(drops[0][1]*100)} → {dec(drops[0][2]*100)}</h3>
{table([T("FIN appears","FIN-in yeri"), T("Values","Dəyərlər"), T("Run B finds","Run B tapır")], [
 [T("right after the word <code>FİN</code> / <code>fin</code>","birbaşa <code>FİN</code> / <code>fin</code> sözündən sonra"), num(fin_word[0]), f'<span class="dn">{dec(fin_word[1]/fin_word[0]*100)}%</span>'],
 [T("after other words (<code>olaraq</code>, <code>kodu</code>, <code>sahəsində</code>…)","başqa sözlərdən sonra (<code>olaraq</code>, <code>kodu</code>, <code>sahəsində</code>…)"), num(fin_other[0]), f"{dec(fin_other[1]/fin_other[0]*100)}%"],
])}
<p>{T(f"In the training data, the values placed directly after the word FİN are <b>{num(dg['train_fin_after_word_decoy'])} look-alikes and only {num(dg['train_fin_after_word_true'])} real FINs</b>: 59% of those examples say “do not mask”. The model learned that a value right after FİN is usually a look-alike. This is strong evidence, not yet proof; a retrain with rebalanced data will confirm it.",
 f"Təlim məlumatında birbaşa FİN sözündən sonra yerləşdirilmiş dəyərlər <b>{num(dg['train_fin_after_word_decoy'])} oxşar dəyər və cəmi {num(dg['train_fin_after_word_true'])} real FIN-dir</b>: bu nümunələrin 59%-i “maskalama” deyir. Model FİN-dən dərhal sonra gələn dəyərin adətən oxşar dəyər olduğunu öyrənib. Bu, güclü sübutdur, amma hələ isbat deyil; balanslaşdırılmış məlumatla yenidən təlim bunu təsdiq edəcək.")}</p>
<p class="small">{T(f"Track M shows the same: AZ_FIN recall {dec(L['AZ_FIN']['runb_M']['recall']*100)}, CARD_SECURITY_CODE {dec(L['CARD_SECURITY_CODE']['runb_M']['recall']*100)} (checkpoint 1 on M: {dec(L['AZ_FIN']['ckpt1_M']['recall']*100)} and {dec(L['CARD_SECURITY_CODE']['ckpt1_M']['recall']*100)}).", f"M izi də eynisini göstərir: AZ_FIN recall {dec(L['AZ_FIN']['runb_M']['recall']*100)}, CARD_SECURITY_CODE {dec(L['CARD_SECURITY_CODE']['runb_M']['recall']*100)} (checkpoint 1 M-də: {dec(L['AZ_FIN']['ckpt1_M']['recall']*100)} və {dec(L['CARD_SECURITY_CODE']['ckpt1_M']['recall']*100)}).")}</p>
<h3>ZIPCODE</h3>
<p>{T("Recall fell from 80.5 to 79.5 on track R (−1.04 points), just over the limit, while precision rose from 55.1 to 74.1. On track M the drop is larger, 87.0 to 82.6. The error browser shows the cause: 63 codes of the form <code>AA9999</code> (for example <code>AZ1000</code>) are missed. It is checked again after the fix round.",
 "R izində recall 80,5-dən 79,5-ə düşüb (−1,04 bal), həddən bir az artıq; precision isə 55,1-dən 74,1-ə yüksəlib. M izində düşüş daha böyükdür: 87,0-dan 82,6-ya. Xəta bələdçisi səbəbi göstərir: <code>AA9999</code> formalı 63 kod (məsələn, <code>AZ1000</code>) buraxılıb. Düzəliş mərhələsindən sonra yenidən yoxlanılacaq.")}</p>
<div class="box"><p><b>{T("The fix", "Düzəliş")}</b>: {T("add dashed and other written CVV formats as real values (shapes only, never benchmark values); place more real FINs directly after the word FİN and fewer or more distinct look-alikes there; recheck the ZIP look-alikes. Then retrain with two seeds and judge on the shadow and real-text sets, not on this benchmark again.",
 "tire ilə və digər yazılışlı CVV formatlarını real dəyər kimi əlavə etmək (yalnız forma, heç vaxt benchmark dəyərləri); birbaşa FİN sözündən sonra daha çox real FIN, orada isə daha az və ya daha fərqli oxşar dəyər yerləşdirmək; ZIP oxşar dəyərlərini yenidən yoxlamaq. Sonra iki seed ilə yenidən öyrətmək və bu benchmarkla yox, shadow və real mətn dəstləri ilə qiymətləndirmək.")}</p></div>
</section>""")

# ---- 7 gemma
add(f"""<section><h2>7. {T("Same data, different model: Gemma", "Eyni məlumat, fərqli model: Gemma")}</h2>
<p>{T("The team asked whether a small generative model (an SLM) would do better than XLM-R. The team trained <code>google/gemma-4-E2B</code> as a token classifier on exactly checkpoint 1's training data, and it was scored on the benchmark (all 9,780 documents, its own scorer). The comparison changes the model and keeps the data.",
 "Komanda kiçik generativ modelin (SLM) XLM-R-dən yaxşı olub-olmayacağını soruşdu. Komanda <code>google/gemma-4-E2B</code> modelini dəqiq checkpoint 1-in təlim məlumatı üzərində token təsnifatçısı kimi öyrətdi, başqa üzv isə onu benchmarkda qiymətləndirdi (bütün 9 780 sənəd, öz qiymətləndiricisi). Müqayisə modeli dəyişir, məlumatı saxlayır.")}</p>
{table([T("Label","Etiket"), T("XLM-R checkpoint 1","XLM-R checkpoint 1"), "Gemma"], [[k, dec(a), dec(b)] for k, a, b in GEMMA] + [[f"<b>{T('Exact micro F1','Dəqiq micro F1')}</b>", "<b>68,7</b>" if LANG=="az" else "<b>68.7</b>", "<b>62,5</b>" if LANG=="az" else "<b>62.5</b>"]])}
<p>{T("XLM-R wins overall by about six points and is roughly ten times faster. Both score 0 on ACCESS_TOKEN: same data, same blind spot. Gemma is far better on IPv6 and the licence, and far worse on long PEM keys and dates. The team kept XLM-R (D-24) and fixed the data; Run B then reached 95.3 on IPv6, so the IPv6 gap was in the data.",
 "XLM-R ümumilikdə təxminən altı bal qalib gəlir və təxminən on dəfə sürətlidir. Hər ikisi ACCESS_TOKEN-də 0 göstərir: eyni məlumat, eyni kor nöqtə. Gemma IPv6 və vəsiqədə xeyli yaxşı, uzun PEM açarlarında və tarixlərdə isə xeyli zəifdir. Komanda XLM-R-də qaldı (D-24) və məlumatı düzəltdi; Run B sonra IPv6-da 95,3-ə çatdı, deməli IPv6 boşluğu məlumatda idi.")}</p>
<p class="small">{T("Caveat: Gemma was scored on all 9,780 documents, the XLM-R numbers on the first 5,000; both halves have nearly the same category mix, so the comparison holds roughly, not to the decimal.",
 "Qeyd: Gemma bütün 9 780 sənəddə, XLM-R rəqəmləri isə ilk 5 000 sənəddə qiymətləndirilib; hər iki yarının kateqoriya tərkibi demək olar ki, eynidir, ona görə müqayisə ondalıq dəqiqliyi ilə yox, təxmini olaraq doğrudur.")}</p>
</section>""")

# ---- 8 other measurements
add(f"""<section><h2>8. {T("Other measurements", "Digər ölçmələr")}</h2>
<h3>{T("Run B's own test split", "Run B-nin öz test hissəsi")}</h3>
<p>{T("Run B's training corpus has a held-out test split of 15,835 documents. Training reported <b>98.9</b> F1 on it (validation 98.5). This is an internal number from the same generators as the training data: checkpoint 1 also scored 98.6 on its own test before scoring 68.7 on the benchmark. It shows the training worked, not that the model generalises.",
 "Run B-nin təlim korpusunun 15 835 sənədlik ayrılmış test hissəsi var. Təlim onda <b>98,9</b> F1 bildirdi (validasiya 98,5). Bu, təlim məlumatı ilə eyni generatorlardan gələn daxili rəqəmdir: checkpoint 1 də benchmarkda 68,7 göstərməzdən əvvəl öz testində 98,6 göstərmişdi. O, təlimin işlədiyini göstərir, modelin ümumiləşdirdiyini yox.")}</p>
<p>{T("the team scored checkpoint 1 on the same split (track R): <b>81.3</b> overall, 84.1 on the old-corpus documents and 77.0 on the new documents, where 44.8% of PII-free documents got a false alarm (0.4% on old documents). Run B has not yet been scored on it with the same scorer.",
 "Komanda checkpoint 1-i eyni hissədə qiymətləndirdi (R izi): ümumilikdə <b>81,3</b>, köhnə korpus sənədlərində 84,1, yeni sənədlərdə isə 77,0; yeni sənədlərdə PII-siz sənədlərin 44,8%-i yalançı siqnal alıb (köhnə sənədlərdə 0,4%). Run B hələ eyni qiymətləndirici ilə bu hissədə qiymətləndirilməyib.")}</p>
<h3>{T("Probe families (checkpoint 1)", "Probe ailələri (checkpoint 1)")}</h3>
<p>{T("Probes are small sets written by hand by the team, independently of the training generator, one per failure family. These are checkpoint 1's results on the eight families that test what Run B's data adds. Every family failed its target, as a probe should before the fix; Run B's probe results come next.",
 "Probe-lar komanda tərəfindən təlim generatorundan asılı olmayaraq əl ilə yazılmış, hər uğursuzluq ailəsi üçün bir olan kiçik dəstlərdir. Aşağıda checkpoint 1-in Run B məlumatının əlavə etdiklərini yoxlayan səkkiz ailədəki nəticələri verilib. Hər ailə hədəfini keçmədi, düzəlişdən əvvəl probe-dan gözlənildiyi kimi; Run B-nin probe nəticələri növbətidir.")}</p>
{table([T("Family","Ailə"), T("Checkpoint 1","Checkpoint 1"), T("Target","Hədəf")], [[f"<code>{a}</code>", b, c] for a, b, c in PROBES])}
</section>""")

# ---- 9 decision
add(f"""<section><h2>9. {T("How the release is decided", "Buraxılış necə qərara alınır")}</h2>
<p>{T("the team wrote the go/no-go rules (<code>docs/go_no_go.md</code>) before reading any Run B result, and the team agreed them as D-29. Every threshold names its source document. The rules that block a release:",
 "Buraxılış qaydalarını (<code>docs/go_no_go.md</code>) komanda Run B-nin heç bir nəticəsini oxumazdan əvvəl yazıb, komanda isə onları D-29 kimi qəbul edib. Hər hədd öz mənbə sənədini göstərir. Buraxılışı bloklayan qaydalar:")}</p>
{table([T("Rule","Qayda"), T("Threshold","Hədd"), T("Set","Dəst"), T("Run B so far","Run B indiyədək")], [
 ["A1–A5 " + T("Sprint-2 gates","Sprint-2 meyarları"), T("micro F1 ≥ 82; weakest label ≥ 65; token, IPv6, licence ≥ 75; look-alikes < 8%; PII-free false alarms < 15%","micro F1 ≥ 82; ən zəif etiket ≥ 65; token, IPv6, vəsiqə ≥ 75; oxşar dəyərlər < 8%; PII-siz yalançı siqnallar < 15%"), "shadow-dev", T("not yet scored","hələ qiymətləndirilməyib")],
 ["A6 / B2 " + T("recall guard","recall qoruyucusu"), T("no label's recall more than 1 point below checkpoint 1","heç bir etiketin recall-u checkpoint 1-dən 1 baldan çox aşağı deyil"), T("shadow-dev, benchmark","shadow-dev, benchmark"), f'<span class="dn">{T("fails on the benchmark: AZ_FIN, CVV, ZIPCODE","benchmarkda keçmir: AZ_FIN, CVV, ZIPCODE")}</span>'],
 ["B1 " + T("beat checkpoint 1","checkpoint 1-i keçmək"), "≥ 70,7" if LANG=="az" else "≥ 70.7", "benchmark", f'<span class="up">{T("passes: 88.9","keçir: 88,9")}</span>'],
 ["C1–C4 " + T("probe targets","probe hədəfləri"), T("token, IPv6, licence contrasts and look-alike families meet their targets","token, IPv6, vəsiqə kontrastları və oxşar dəyər ailələri hədəflərinə çatır"), "probes", T("not yet scored","hələ qiymətləndirilməyib")],
 ["C13 " + T("no family worse","heç bir ailə pis deyil"), T("no probe family worse than checkpoint 1 by more than 10 points or 3 documents","heç bir probe ailəsi checkpoint 1-dən 10 bal və ya 3 sənəddən çox pis deyil"), "probes", T("not yet scored","hələ qiymətləndirilməyib")],
])}
<p>{T("Also reported, not blocking: Run B's own test split, real text (with raw counts), and a template-overfitting check that flags a gap of more than 15 points between Run B's own test and the benchmark or real text. One seed is enough for a first decision; a second is needed before release. The sealed set runs once, on the final candidate.",
 "Həmçinin bildirilir, amma bloklamır: Run B-nin öz test hissəsi, real mətn (xam saylarla) və Run B-nin öz testi ilə benchmark və ya real mətn arasında 15 baldan çox fərqi qeyd edən şablona həddən artıq uyğunlaşma yoxlaması. İlk qərar üçün bir seed kifayətdir; buraxılışdan əvvəl ikincisi lazımdır. Sealed dəst bir dəfə, yekun namizəd üzərində işə salınır.")}</p>
<div class="box"><p><b>{T("Why the sets are kept apart.", "Dəstlər niyə ayrı saxlanılır.")}</b> {T("Only the team holds and runs the shadow and sealed sets; the people who built the training data never see them (rule A2.5). That is what stops the checkpoint 1 mistake, a test that shares a generator with training, from happening again. The benchmark has now been used to find the CVV and FIN problems, so the next model is judged on shadow-dev and real text.",
 "Shadow və sealed dəstləri yalnız komanda saxlayır və işə salır; təlim məlumatını quranlar onları heç vaxt görmür (A2.5 qaydası). Checkpoint 1-in səhvinin, yəni təlimlə eyni generatoru paylaşan testin təkrarlanmasının qarşısını alan budur. Benchmark artıq CVV və FIN problemlərini tapmaq üçün istifadə olunub, ona görə növbəti model shadow-dev və real mətn üzərində qiymətləndirilir.")}</p></div>
</section>""")

# ---- 10 limits & next
add(f"""<section><h2>10. {T("Limits of this report and next steps", "Hesabatın hüdudları və növbəti addımlar")}</h2>
<h3>{T("What this report does not show", "Bu hesabat nəyi göstərmir")}</h3>
<ul>
<li>{T("<b>One benchmark, synthetic text.</b> It does not measure real documents; the real-text set does.", "<b>Bir benchmark, sintetik mətn.</b> O, real sənədləri ölçmür; bunu real mətn dəsti edir.")}</li>
<li>{T("<b>One seed, two epochs.</b> Run B was trained once (seed 42, 2 of the allowed 3 epochs). Without a second seed, small per-label differences cannot be told from chance.", "<b>Bir seed, iki epoxa.</b> Run B bir dəfə öyrədilib (seed 42, icazə verilən 3 epoxadan 2-si). İkinci seed olmadan etiket üzrə kiçik fərqləri təsadüfdən ayırmaq olmur.")}</li>
<li>{T("<b>Track R decides.</b> The rules use track R; track M (section 5) is reported next to it as the product view.", "<b>Qərarı R izi verir.</b> Qaydalar R izindən istifadə edir; M izi (5-ci bölmə) məhsul baxışı kimi onun yanında verilir.")}</li>
<li>{T("<b>Different hardware.</b> Checkpoint 1 ran on a CPU, Run B on an Apple GPU. Predictions can differ in rare edge cases between devices; this does not affect a 20-point gap.", "<b>Fərqli avadanlıq.</b> Checkpoint 1 CPU-da, Run B Apple GPU-da işə salınıb. Proqnozlar nadir hallarda cihazlar arasında fərqlənə bilər; bu, 20 ballıq fərqə təsir etmir.")}</li>
<li>{T("<b>Azerbaijani only.</b> Run B has no English, Turkish or Russian training data, so it cannot replace the multilingual production model yet (D-23a).", "<b>Yalnız Azərbaycan dili.</b> Run B-nin ingilis, türk və ya rus dilində təlim məlumatı yoxdur, ona görə o, hələ çoxdilli istehsal modelini əvəz edə bilməz (D-23a).")}</li>
</ul>
<h3>{T("Next steps", "Növbəti addımlar")}</h3>
{table([T("Who","Kim"), T("What","Nə"), T("Why","Niyə")], [
 [T("The team","Komanda"), T("Run <code>scripts/score_runb.sh</code> on Run B: probes, Run B's test split, real text, shadow-dev","Run B üzərində <code>scripts/score_runb.sh</code> işə salmaq: probe-lar, Run B-nin test hissəsi, real mətn, shadow-dev"), T("the official evaluation and the go/no-go","rəsmi qiymətləndirmə və buraxılış qərarı")],
 [T("The team","Komanda"), T("Fix the data: dashed CVV formats, real FINs after the word FİN, ZIP look-alikes","Məlumatı düzəltmək: tireli CVV formatları, FİN sözündən sonra real FIN-lər, ZIP oxşar dəyərləri"), T("the three recall drops","üç recall düşüşü")],
 [T("The team","Komanda"), T("Rebuild the corpus (<code>runb-az-v3</code>) and verify checksums","Korpusu yenidən qurmaq (<code>runb-az-v3</code>) və yoxlama cəmlərini yoxlamaq"), T("a reproducible training set","təkrarlana bilən təlim dəsti")],
 [T("The team","Komanda"), T("Get a GPU; retrain with two seeds, ideally three epochs","GPU tapmaq; iki seed ilə, ideal halda üç epoxa ilə yenidən öyrətmək"), T("the release needs two seeds","buraxılış üçün iki seed lazımdır")],
])}
<p>{T("Production keeps checkpoint 1 until the go/no-go passes. A multilingual model comes after Azerbaijani results are good: the fixed data is translated into English, Turkish and Russian, and the model is trained again.",
 "Buraxılış qərarı müsbət olana qədər istehsalatda checkpoint 1 qalır. Çoxdilli model Azərbaycan dilində nəticələr yaxşı olduqdan sonra gəlir: düzəldilmiş məlumat ingilis, türk və rus dillərinə tərcümə olunur və model yenidən öyrədilir.")}</p>
</section>""")

# ---- appendix
app_rows = []
for k in sorted(L):
    a, b = L[k]["ckpt1"], L[k]["runb"]
    n = a["tp"] + a["fn"]
    app_rows.append([k, f'<span style="float:right">{num(n)}</span>',
                     f"{dec(a['precision']*100)} / {dec(a['recall']*100)} / <b>{dec(a['f1']*100)}</b>",
                     f"{dec(b['precision']*100)} / {dec(b['recall']*100)} / <b>{dec(b['f1']*100)}</b>",
                     delta(a["f1"], b["f1"]), delta(a["recall"], b["recall"]),
                     f"{dec(L[k]['ckpt1_M']['f1']*100)} → <b>{dec(L[k]['runb_M']['f1']*100)}</b>"])
add(f"""<section><h2>11. {T("Appendix: every label", "Əlavə: bütün etiketlər")}</h2>
<p class="small">{T("Exact precision / recall / F1, track R, first 5,000 benchmark documents; the last column is exact F1 on track M. Gold = values of that label in the set.", "Dəqiq precision / recall / F1, R izi, benchmarkın ilk 5 000 sənədi; son sütun M izində dəqiq F1-dir. Gold = dəstdə həmin etiketin dəyərləri.")}</p>
{table([T("Label","Etiket"), "Gold", T("Checkpoint 1: P / R / F1","Checkpoint 1: P / R / F1"), "Run B: P / R / F1", T("F1 change","F1 dəyişikliyi"), T("Recall change","Recall dəyişikliyi"), T("F1, track M","F1, M izi")], app_rows, "app")}
<h3>{T("Glossary", "Lüğət")}</h3>
{table([T("Term","Termin"), T("Meaning","Mənası")], [
 ["Precision", T("Of the values the model masked, the share that were right.","Modelin maskaladığı dəyərlərdən düzgün olanların payı.")],
 ["Recall", T("Of the real values, the share the model found.","Real dəyərlərdən modelin tapdıqlarının payı.")],
 ["F1", T("The balance of precision and recall (their harmonic mean).","Precision və recall-un balansı (harmonik ortası).")],
 [T("Look-alike (decoy)","Oxşar dəyər (decoy)"), T("A string shaped like personal data that is not personal data and must stay unmasked.","Şəxsi məlumata bənzəyən, amma şəxsi məlumat olmayan və maskalanmamalı olan sətir.")],
 [T("Anchor","Lövbər"), T("The word that introduces a value: <code>FİN</code>, <code>tarixi</code>, <code>CVV kodu</code>.","Dəyəri təqdim edən söz: <code>FİN</code>, <code>tarixi</code>, <code>CVV kodu</code>.")],
 [T("Seed","Seed"), T("The random starting state of a training run. Two seeds show how much a result varies by chance.","Təlimin təsadüfi başlanğıc vəziyyəti. İki seed nəticənin təsadüfən nə qədər dəyişdiyini göstərir.")],
 ["Shadow / sealed", T("the private, independent test sets; sealed runs once, at the end.","komandanın şəxsi, müstəqil test dəstləri; sealed sonda bir dəfə işə salınır.")],
])}
</section>""")

doc = f"""<!doctype html><html lang="{LANG}"><head><meta charset="utf-8">
<title>{T("Benchmark report: checkpoint 1 vs Run B", "Benchmark hesabatı: checkpoint 1 və Run B")}</title>
<style>{css}</style></head><body>{''.join(H)}</body></html>"""
(HERE / f"report_{LANG}.html").write_text(doc, encoding="utf-8")
print("wrote", HERE / f"report_{LANG}.html")
