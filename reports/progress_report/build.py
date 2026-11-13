"""Progress report: every model in models.json on the public sets, side by side.

    python reports/progress_report/extract.py    # models.json -> data.json (numbers from the score reports)
    python reports/progress_report/build.py      # data.json -> progress_report.html; open it, Print -> Save as PDF

To add a model: score it (scripts/release_check.sh), add an entry to models.json, run both commands.
Benchmark numbers are track R (raw pipeline) unless marked, exact match, the first 5,000 documents,
policy items left out (as rule B1 counts). Shadow-dev (A1-A6) and real text (E3) come from
The release checks when a model has one; otherwise they are "not scored".
"""
import datetime
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
D = json.load(open(HERE / "data.json", encoding="utf-8"))
K = D["order"]
B, R, MODELS = D["bench"], D["rules"], D["models"]
NAME = {k: MODELS[k]["name"] for k in K}
LAST, PREV, FIRST = K[-1], K[-2] if len(K) > 1 else K[-1], K[0]

RULES = [
    ("A1", "Private test F1 ≥ 82"), ("A2", "Weakest label F1 ≥ 65"), ("A3", "Token, IPv6, licence F1 ≥ 75"),
    ("A4", "Look-alikes masked < 8%"), ("A5", "PII-free documents masked < 15%"),
    ("A6", "No label worse than checkpoint 1 (private)"),
    ("B1", "Benchmark F1 beats checkpoint 1 by 2+"), ("B2", "No benchmark label worse than checkpoint 1"),
    ("C1", "Access token vs API key"), ("C2", "IPv6 vs MAC address"), ("C3", "Licence vs ID card"),
    ("C4", "Look-alikes masked (probes) < 10%"), ("C13", "No probe family much worse than checkpoint 1"),
    ("E3", "Real text: 80% found"),
]


def p(x):
    return f"{x * 100:.1f}"


SHORT_LABEL = {"AZ_DRIVER_LICENSE_NUMBER": "licence", "AZ_ID_CARD_NUMBER": "ID card", "ACCESS_TOKEN": "token",
               "API_KEY": "API key", "IPV6_ADDRESS": "IPv6", "MAC_ADDRESS": "MAC", "PAYMENT_CARD_NUMBER": "card",
               "CARD_SECURITY_CODE": "CVV", "AZ_FIN": "FIN", "ZIPCODE": "ZIP", "PRIVATE_KEY": "private key",
               "AZ_VOEN": "VÖEN", "TIME": "time"}


def short(text, rid="", n=46):
    text = re.sub(r"\s*\(checkpoint 1[^)]*\)|\s*\[saved report[^\]]*\]|\s*\(saved report[^)]*\)", "", text or "")
    if rid == "C4":
        m = re.search(r"(\d+) of 11 families above 15%.*?overall ([\d.]+)%", text)
        return f"{m.group(2)}%, {m.group(1)}/11 kinds over 15%" if m else text[:n]
    text = re.sub(r"\w+ (?:confusion_rate|exact_recall) \[(\w+)(?:→(\w+))?\] ([\d.]+)",
                  lambda m: (f"{m.group(1)} → {m.group(2)} {m.group(3)}%" if m.group(2) else f"{m.group(1)} found {m.group(3)}%"),
                  text)
    for a, b in SHORT_LABEL.items():
        text = text.replace(a, b)
    text = text.split(";")[0].strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def rule_cell(k, rid):
    r = R[k].get(rid)
    if k == "ckpt1" and rid in ("B1", "B2", "A6", "C13"):
        return '<td class="base">baseline</td>'
    if not r or r["status"] in ("not scored", "n/a") or "not scored" in (r.get("result") or ""):
        return '<td class="base">not scored</td>'
    ok = {"pass": True, "fail": False}.get(r["status"])
    cls, mark = {True: ("ok", "✓"), False: ("bad", "✗"), None: ("base", "")}[ok]
    return f'<td class="{cls}"><span class="mk">{mark}</span> {short(r["result"], rid)}</td>'


def passed(k):
    return sum(1 for rid, _ in RULES if R[k].get(rid, {}).get("status") == "pass")


def scored(k):
    return sum(1 for rid, _ in RULES if R[k].get(rid, {}).get("status") in ("pass", "fail"))


def c4_overall(k):
    m = re.search(r"overall ([\d.]+)%", R[k].get("C4", {}).get("result", ""))
    return m.group(1) + "%" if m else "–"


def fams(k):
    m = re.search(r"(\d+) of (\d+) families meet", R[k].get("C12", {}).get("result", ""))
    return m.group(0).replace(" families meet", "") if m else "–"


cards = [
    ("Benchmark F1 (raw pipeline)", [p(B[k]["R"]["f1"]) for k in K]),
    ("Benchmark F1 (product decoding)", [p(B[k]["M"]["f1"]) for k in K]),
    ("Benchmark precision", [p(B[k]["R"]["precision"]) for k in K]),
    ("Benchmark recall", [p(B[k]["R"]["recall"]) for k in K]),
    ("Probe families meeting all targets", [fams(k) for k in K]),
    ("Look-alikes masked (probes)", [c4_overall(k) for k in K]),
]
card_html = "".join(
    f'<div class="card"><div class="ct">{t}</div><div class="cv">'
    + " <span class='ar'>→</span> ".join(f"<span class='{'vl' if i == len(K) - 1 else 'vo'}'>{v}</span>"
                                         for i, v in enumerate(vals))
    + "</div></div>" for t, vals in cards)

head = "".join(f"<th>{NAME[k]}</th>" for k in K)
data_rows = "".join(
    f"<tr><td>{lab}</td>" + "".join(f"<td class='n'>{MODELS[k][f]}</td>" for k in K) + "</tr>"
    for lab, f in (("Training documents (Azerbaijani)", "train_docs"), ("New, audited data in training", "new_share"),
                   ("LLM-written documents (cleaned)", "llm_docs")))
rule_rows = "".join(f"<tr><td class='rid'>{rid}</td><td>{name}</td>" + "".join(rule_cell(k, rid) for k in K) + "</tr>"
                    for rid, name in RULES)
pass_row = ("<tr><td></td><td><b>Rules passed (of those scored)</b></td>"
            + "".join(f"<td><b>{passed(k)} of {scored(k)}</b></td>" if k != "ckpt1" else "<td class='base'>baseline</td>"
                      for k in K) + "</tr>")

labs = sorted(B[FIRST]["labels"], key=lambda l: B[FIRST]["labels"][l]["f1"])


def delta(d):
    cls = "up" if d > 1 else "down" if d < -1 else "same"
    return f"<td class='n {cls}'>{d:+.1f}</td>"


label_rows = []
for l in labs:
    f = [B[k]["labels"].get(l, {}).get("f1", 0) * 100 for k in K]
    label_rows.append(f"<tr><td>{l}</td><td class='n'>{B[LAST]['labels'][l]['n']:,}</td>"
                      + "".join(f"<td class='n'>{v:.1f}</td>" for v in f)
                      + delta(f[-1] - f[0]) + delta(f[-1] - f[-2]) + "</tr>")

failing = [rid for rid, _ in RULES if R[LAST].get(rid, {}).get("status") == "fail"]
unscored = [rid for rid, _ in RULES if R[LAST].get(rid, {}).get("status") not in ("pass", "fail")]
verdict = (f"<b>{NAME[LAST]}</b> passes {passed(LAST)} of the {scored(LAST)} rules scored here"
           + (f"; fails {', '.join(failing)}" if failing else "")
           + (f". Not scored here: {', '.join(unscored)} (private sets)." if unscored else "."))

css = """
@page { size: A4; margin: 14mm 13mm; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif; color: #1d2433; font-size: 10.5px; }
h1 { font-size: 20px; margin: 0 0 2px; } h2 { font-size: 13px; margin: 14px 0 6px; }
.sub { color: #5b6475; margin-bottom: 10px; }
.vo { color: #8a94a6; } .vl { color: #127a4b; font-weight: 700; }
.cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; }
.card { border: 1px solid #dfe3ea; border-radius: 6px; padding: 7px 9px; }
.ct { color: #5b6475; font-size: 9.5px; margin-bottom: 3px; } .cv { font-size: 13px; } .ar { color: #b0b7c3; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
table.rules td, table.rules th { font-size: 9.5px; } table.rules col.rn { width: 150px; } table.rules col.ri { width: 36px; }
td, th { overflow-wrap: anywhere; } th, td { padding: 3.5px 6px; border-bottom: 1px solid #eceff3; text-align: left; }
th { background: #f4f6f9; font-size: 9.5px; color: #4b5466; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
td.ok { color: #127a4b; } td.bad { color: #b42318; } td.base { color: #8a94a6; }
.mk { font-weight: 700; } .rid { font-weight: 700; width: 30px; }
.up { color: #127a4b; font-weight: 600; } .down { color: #b42318; font-weight: 600; } .same { color: #8a94a6; }
.note { color: #5b6475; font-size: 9.5px; margin-top: 5px; }
.verdict { margin-top: 10px; padding: 7px 9px; background: #fff4f2; border-left: 3px solid #b42318; }
.pb { page-break-before: always; }
"""

title = " → ".join(NAME[k] for k in K)
ids = " · ".join(f"{NAME[k]} = <code>{MODELS[k]['id']}</code>" for k in K if k != "ckpt1")
html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>PII model progress</title>
<style>{css}</style></head><body>
<h1>PII model progress: {title}</h1>
<div class="sub">{datetime.date.today():%d %B %Y} · Azerbaijani benchmark (first 5,000 documents) and probes (1,656 documents) · {ids}</div>

<div class="cards">{card_html}</div>

<h2>Training data</h2>
<table><col style="width:190px">{"".join("<col>" for _ in K)}<tr><th></th>{head}</tr>{data_rows}</table>

<h2>Release rules</h2>
<table class="rules"><col class="ri"><col class="rn">{"".join("<col>" for _ in K)}<tr><th>#</th><th>Rule</th>{head}</tr>{rule_rows}{pass_row}</table>
<div class="note">A1–A6 and E3 come from the private sets (shadow-dev, real text) and appear only for models she has checked.
Checkpoint 1 and Run B: rules as judged on 14 October; later models: their own release checks, with the policy items of their day.</div>
<div class="verdict">{verdict}</div>

<h2 class="pb">Benchmark F1 by label (raw pipeline, exact match, policy items left out)</h2>
<table><col style="width:190px"><tr><th>Label</th><th class="n">Values</th>{''.join(f'<th class="n">{NAME[k]}</th>' for k in K)}
<th class="n">{NAME[LAST]} vs {NAME[FIRST]}</th><th class="n">{NAME[LAST]} vs {NAME[PREV]}</th></tr>{''.join(label_rows)}</table>
<div class="note">Sorted by {NAME[FIRST]}'s score, weakest first. Values = gold values of that label in the 5,000 documents.
Green / red = more than 1 point better / worse. Every model scored with the same code, so the policy items are the same for all.</div>
</body></html>"""
(HERE / "progress_report.html").write_text(html, encoding="utf-8")
print("wrote", HERE / "progress_report.html")
