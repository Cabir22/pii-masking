"""m1 audit: minimal MAC reproductions (separate from the benchmark). One factor changes at a time:
the frame (3 failing benchmark frames, plus a 'MAC:' label line), the value's first character,
its case, its separator. Track M for v4.2 and m1; writes mac_repro.md."""
import json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1] / "model")]
import torch; torch.set_num_threads(4)
import predict
FRAMES = {"profil": "Şəbəkə profilində {v} görünür; həmin məlumat arxivdə saxlanılır.",
          "router": "Router qeydində {v} qeyd olunub; surəti arxivdədir.",
          "mac_unvani": "MAC ünvanı {v} kimi göstərilib; hesab çıxarışı əlavə olunub.",
          "label_line": "MAC: {v}"}
VALUES = {"digit-first upper (failed)": "4D:9D:F6:17:07:D3", "same, letter first": "D4:9D:F6:17:07:D3",
          "digit-first upper 2 (failed)": "16:85:DB:32:0C:52", "same, letter first 2": "A6:85:DB:32:0C:52",
          "letter-first upper (failed)": "FA:1B:0C:DC:28:6B", "same, lower case": "fa:1b:0c:dc:28:6b",
          "digit-first, lower case": "4d:9d:f6:17:07:d3", "digit-first, dashes": "4D-9D-F6-17-07-D3",
          "digits only": "16:85:23:32:01:52"}
models = {"v4.2": ("your-hf-org/masking-az-runb-v4.2-seed42", "223e54e8799dc60f6f6b19362191cf7c10c774c7"),
          "m1": ("your-hf-org/masking-multi-m1-seed42", "d7493a1634f3aadc4dab5cd3b8103cf070e5eff0")}
res = {}
for mk, (m, r) in models.items():
    model, tok, i2l = predict.load_model(m, revision=r)
    for fk, f in FRAMES.items():
        for vk, v in VALUES.items():
            t = f.format(v=v); s = t.index(v)
            P = predict._detect_entities_word_consistent(t, model, tok, i2l)
            hit = [p for p in P if p["start"] < s + len(v) and s < p["end"]]
            exact = any(p["start"] == s and p["end"] == s + len(v) and p["label"] == "MAC_ADDRESS" for p in P)
            cov = sum(1 for c in range(s, s + len(v)) if any(p["start"] <= c < p["end"] for p in hit))
            res[(mk, fk, vk)] = "exact" if exact else ("missed" if not hit else f"partly {cov}/{len(v)} " + "/".join(sorted({p['label'] for p in hit})))
            time.sleep(0.2)
    del model
L = ["# Minimal MAC reproductions (track M)", "", "| Frame | Value | v4.2 | m1 |", "|---|---|---|---|"]
for fk in FRAMES:
    for vk, v in VALUES.items():
        L.append(f"| {fk} | {vk} `{v}` | {res[('v4.2', fk, vk)]} | {res[('m1', fk, vk)]} |")
(HERE / "mac_repro.md").write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
