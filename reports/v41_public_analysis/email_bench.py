"""v4.1 analysis: the 26 split benchmark emails are all
`bench.userN@synthetic-mailN.invalid` in structured documents. Re-run v4
(track R) with one thing changed: the local part's `bench` word, the
`.invalid` TLD, or the document's own `*_bench_*` token/key values.

    python reports/v41_public_analysis/email_bench.py
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import read_errors as R  # noqa: E402

docs = {d["id"]: d for d in R.load_docs("benchmark")}
res = json.loads((R.OUT / "benchmark_R_EMAIL.json").read_text(encoding="utf-8"))
items = [i for i in res["items"] if i["outcomes"][R.NEW] != "exact"]
eng = R.SB.Engine(*R.MODELS[R.NEW], "cpu", ["R"])


def run(text: str, value: str) -> bool:
    s = text.index(value)
    return any(p["start"] == s and p["end"] == s + len(value) and p["label"] == "EMAIL" for p in eng.run("R", text))


VARIANTS = {
    "as is": lambda t, v: (t, v),
    "bench. -> leyla.": lambda t, v: (t.replace(v, v.replace("bench.", "leyla.")), v.replace("bench.", "leyla.")),
    ".invalid -> .az": lambda t, v: (t.replace(v, v.replace(".invalid", ".az")), v.replace(".invalid", ".az")),
    "both": lambda t, v: (t.replace(v, v.replace("bench.", "leyla.").replace(".invalid", ".az")),
                          v.replace("bench.", "leyla.").replace(".invalid", ".az")),
    "doc *_bench_* -> *_prod_*": lambda t, v: (re.sub(r"_bench_", "_prod_", t), v),
}
hits = {k: 0 for k in VARIANTS}
for i in items:
    t = docs[i["id"]]["text"]
    for k, f in VARIANTS.items():
        hits[k] += run(*f(t, i["value"]))
L = [f"# Split benchmark emails (n = {len(items)}): exact spans {R.NEW} finds after one change (track R)", "",
     "| change | found |", "|---|---|"] + [f"| {k} | {v} |" for k, v in hits.items()]
(R.OUT / "email_bench.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
print("\n".join(L))
