"""DatasetAnalyzer -- quality metrics, not just correctness.

The old `RunStats` reported counts. Counts told you the dataset had 53 IBAN
mentions; they did not tell you those 53 mentions were built from 6 distinct
strings, which is the fact that made the label unusable. Every metric here
exists because its absence hid a specific defect found in the audit:

    metric                         defect it would have caught
    ---------------------------------------------------------------------
    structural signature entropy   template memorisation
    top-k value concentration      197x `172.16.254.1`, 76x `34 ABC 123`
    distinct-value ratio           IBAN with 6 distinct values
    length distribution            median 103 chars, nothing above 361
    entity position histogram      entities never at offset 0
    repeat-mention completeness    272 unlabeled repeat occurrences
    placeholder rate               33% test cards, 55x AWS example key
    password keyword share         59% of secrets contained "password"
    private-IP share               88% RFC1918
    adjacency counts               BIO-vs-BIOES decision had no evidence
    PII density                    29.6% of characters were inside a span

`generalization_estimate()` combines them into a single auditable score with
its components shown, so the number can be argued with rather than trusted.
"""

from __future__ import annotations

import collections
import math
import re
import statistics

from . import checksums as CK
from .blocklist import has_password_keyword, is_blocked
from .config import ENTITY_TYPES, LANGUAGES, GeneratorConfig
from .resolver import find_unlabeled_repeats

_DIGIT = re.compile(r"\d+")
_WS = re.compile(r"\s+")


def signature(ex: dict) -> str:
    """Structural fingerprint: entity spans -> <LABEL>, digits -> #."""
    text, ents = ex["text"], sorted(ex["entities"], key=lambda e: e["start"])
    out, last = [], 0
    for e in ents:
        out.append(text[last:e["start"]])
        out.append("<" + e["label"] + ">")
        last = e["end"]
    out.append(text[last:])
    s = _DIGIT.sub("#", "".join(out))
    return _WS.sub(" ", s).strip()


class DatasetAnalyzer:
    def __init__(self, cfg: GeneratorConfig | None = None) -> None:
        self.cfg = cfg or GeneratorConfig()
        self.rows: list[dict] = []

    def add(self, ex: dict) -> None:
        self.rows.append(ex)

    # -- computation ------------------------------------------------------
    def compute(self) -> dict:
        rows = self.rows
        n = len(rows)
        if not n:
            return {}

        lengths = [len(r["text"]) for r in rows]
        lang_counts = collections.Counter(r["lang"] for r in rows)
        label_counts = collections.Counter()
        values = collections.defaultdict(collections.Counter)
        entity_chars = 0
        positions = []
        leading = 0
        adjacent = 0
        same_type_adjacent = 0
        repeat_missing = 0
        docs_with_repeat = 0
        zero_entity = 0
        multi_lang_docs = 0

        for r in rows:
            text, ents = r["text"], sorted(r["entities"], key=lambda e: e["start"])
            if not ents:
                zero_entity += 1
            seen_vals = collections.Counter(e["text"] for e in ents)
            if any(v > 1 for v in seen_vals.values()):
                docs_with_repeat += 1
            for e in ents:
                label_counts[e["label"]] += 1
                values[e["label"]][e["text"]] += 1
                entity_chars += e["end"] - e["start"]
                if len(text) > 1:
                    positions.append(e["start"] / len(text))
            if ents and ents[0]["start"] == 0:
                leading += 1
            for a, b in zip(ents, ents[1:]):
                gap = b["start"] - a["end"]
                if 0 <= gap <= 2:
                    adjacent += 1
                    if a["label"] == b["label"]:
                        same_type_adjacent += 1
            repeat_missing += find_unlabeled_repeats(text, ents)
            if _CYR.search(text) and _LAT.search(text):
                multi_lang_docs += 1

        total_mentions = sum(label_counts.values())
        sigs = collections.Counter(signature(r) for r in rows)

        # value concentration & diversity
        diversity, top10_share, worst_conc = {}, {}, 0.0
        for label in ENTITY_TYPES:
            c = values[label]
            tot = sum(c.values())
            if not tot:
                diversity[label] = 0.0
                top10_share[label] = 0.0
                continue
            diversity[label] = len(c) / tot
            share = sum(v for _, v in c.most_common(10)) / tot
            top10_share[label] = share
            worst_conc = max(worst_conc, share)

        # placeholder / realism probes
        placeholder_hits = sum(
            1 for label in ENTITY_TYPES for v in values[label]
            if is_blocked(v))
        # Both probes below queried labels that do not exist in taxonomy
        # v2.0.0 -- "PASSWORD_SECRET_PRIVATE_KEY" and "IP_ADDRESS" are names
        # from an earlier draft. `values` is a defaultdict, so each lookup
        # silently returned an empty Counter and both metrics read 0.0 for
        # the entire life of the dataset. Repointed at the real labels.
        secretish = collections.Counter()
        for label in ("PRIVATE_KEY", "API_KEY", "ACCESS_TOKEN"):
            secretish.update(values[label])
        pw = list(secretish.elements())
        pw_keyword = (sum(1 for x in pw if has_password_keyword(x)) / len(pw)
                      if pw else 0.0)
        ip_counter = collections.Counter()
        for label in ("IPV4_ADDRESS", "IPV6_ADDRESS"):
            ip_counter.update(values[label])
        ips = list(ip_counter.elements())
        priv_ip = (sum(1 for x in ips if CK.ip_is_private_or_reserved(x)) / len(ips)
                   if ips else 0.0)

        # label entropy (max = log2(15) if perfectly uniform)
        probs = [label_counts[l] / total_mentions for l in ENTITY_TYPES
                 if label_counts[l]]
        entropy = -sum(p * math.log2(p) for p in probs) if probs else 0.0

        return {
            "n": n,
            "lengths": {
                "min": min(lengths), "p25": _pct(lengths, .25),
                "median": statistics.median(lengths), "p75": _pct(lengths, .75),
                "p95": _pct(lengths, .95), "max": max(lengths),
                "mean": statistics.mean(lengths),
                "over_500": sum(1 for x in lengths if x > 500) / n,
                "over_2000": sum(1 for x in lengths if x > 2000) / n,
            },
            "bucket_counts": collections.Counter(
                r.get("_bucket", "?") for r in rows),
            "doc_types": collections.Counter(r.get("_doc_type", "?") for r in rows),
            "lang_counts": lang_counts,
            "label_counts": label_counts,
            "total_mentions": total_mentions,
            "mentions_per_doc": total_mentions / n,
            "diversity": diversity,
            "top10_share": top10_share,
            "worst_concentration": worst_conc,
            "signature_uniqueness": len(sigs) / n,
            "signature_top": sigs.most_common(3),
            "entity_char_share": entity_chars / sum(lengths),
            "position_median": statistics.median(positions) if positions else 0,
            "leading_entity_rate": leading / n,
            "adjacent_pairs": adjacent,
            "same_type_adjacent": same_type_adjacent,
            "repeat_missing": repeat_missing,
            "docs_with_repeat_mentions": docs_with_repeat / n,
            "zero_entity_rate": zero_entity / n,
            "placeholder_values": placeholder_hits,
            "password_keyword_share": pw_keyword,
            "private_ip_share": priv_ip,
            "label_entropy": entropy,
            "max_entropy": math.log2(len(ENTITY_TYPES)),
            "mixed_script_docs": multi_lang_docs / n,
            "hard_negatives": sum(r.get("_hard_negatives", 0) for r in rows),
            "adversarials": sum(r.get("_adversarials", 0) for r in rows),
            "docs_with_hard_neg": sum(
                1 for r in rows if r.get("_hard_negatives", 0)) / n,
            "docs_with_adversarial": sum(
                1 for r in rows if r.get("_adversarials", 0)) / n,
            "noised_docs": sum(1 for r in rows if r.get("_noise")) / n,
        }

    # -- scoring ----------------------------------------------------------
    def generalization_estimate(self, m: dict) -> tuple[float, list[tuple]]:
        """Composite 0-10 with components shown, so it can be argued with."""
        c = []
        L = m["lengths"]

        c.append(("length realism",
                  _band(L["median"], 300, 900) * 0.5 + _band(L["over_500"], .35, .75) * 0.5,
                  f"median {L['median']:.0f}, {L['over_500']*100:.0f}% >500ch"))
        c.append(("template diversity", _band(m["signature_uniqueness"], .95, .995),
                  f"{m['signature_uniqueness']*100:.1f}% unique signatures"))
        worst_div = min(m["diversity"].values()) if m["diversity"] else 0
        c.append(("value diversity", _band(worst_div, .15, .45),
                  f"worst label {worst_div*100:.0f}% distinct"))
        c.append(("value concentration", 1 - _band(m["worst_concentration"], .08, .40),
                  f"worst top-10 = {m['worst_concentration']*100:.0f}% of mentions"))
        min_share = min(m["label_counts"][l] / m["total_mentions"]
                        for l in ENTITY_TYPES) if m["total_mentions"] else 0
        c.append(("tail coverage", _band(min_share, .003, .015),
                  f"rarest label {min_share*100:.2f}% of mentions"))
        c.append(("realism", 1.0 if not m["placeholder_values"] else 0.0,
                  f"{m['placeholder_values']} placeholder values"))
        c.append(("secret realism", 1 - _band(m["password_keyword_share"], .10, .45),
                  f"{m['password_keyword_share']*100:.0f}% keyword passwords"))
        c.append(("IP realism", 1 - _band(m["private_ip_share"], .45, .85),
                  f"{m['private_ip_share']*100:.0f}% private"))
        c.append(("PII density", 1 - _band(m["entity_char_share"], .06, .25),
                  f"{m['entity_char_share']*100:.1f}% of chars are PII"))
        c.append(("repeat completeness", 1.0 if not m["repeat_missing"] else 0.0,
                  f"{m['repeat_missing']} unlabeled repeats"))
        # These two score None (excluded from OVERALL, not penalized) when the
        # config's own rate is 0 -- true-positive-only (2026-08-21) makes 0%
        # the CORRECT value, not a quality gap, so scoring it against a
        # 20-40%/6-16% band would drag OVERALL down for following the policy
        # exactly as configured.
        c.append(("hard negatives",
                  None if self.cfg.hard_negative_rate == 0 else
                  _band(m["docs_with_hard_neg"], .20, .40),
                  f"{m['docs_with_hard_neg']*100:.0f}% of docs"
                  + ("" if self.cfg.hard_negative_rate else " (0% expected: hard_negative_rate=0)")))
        c.append(("adversarials",
                  None if self.cfg.adversarial_rate == 0 else
                  _band(m["docs_with_adversarial"], .06, .16),
                  f"{m['docs_with_adversarial']*100:.0f}% of docs"
                  + ("" if self.cfg.adversarial_rate else " (0% expected: adversarial_rate=0)")))
        c.append(("noise coverage", _band(m["noised_docs"], .08, .20),
                  f"{m['noised_docs']*100:.0f}% of docs"))
        c.append(("BIO boundary cases", _band(m["same_type_adjacent"] / m["n"], .005, .03),
                  f"{m['same_type_adjacent']} same-type adjacent pairs"))
        scored = [x[1] for x in c if x[1] is not None]
        score = sum(scored) / len(scored) * 10 if scored else 0.0
        return score, c

    # -- reporting --------------------------------------------------------
    def report(self) -> str:
        m = self.compute()
        if not m:
            return "no data"
        o, w = [], lambda s="": o.append(s)
        n = m["n"]
        w("=" * 78)
        w("DATASET QUALITY REPORT")
        w("=" * 78)
        w(f"Documents            : {n}")
        w(f"Entity mentions      : {m['total_mentions']}  "
          f"({m['mentions_per_doc']:.1f}/doc)")
        w(f"Zero-entity docs     : {m['zero_entity_rate']*100:.1f}%")
        w("")
        L = m["lengths"]
        w("DOCUMENT LENGTH (chars)")
        w(f"  min {L['min']}  p25 {L['p25']}  median {L['median']:.0f}  "
          f"p75 {L['p75']}  p95 {L['p95']}  max {L['max']}")
        w(f"  >500 chars: {L['over_500']*100:.1f}%    "
          f">2000 chars: {L['over_2000']*100:.1f}%")
        w("  buckets: " + ", ".join(f"{k}={v}" for k, v in
                                    m["bucket_counts"].most_common()))
        w("")
        w("LANGUAGE")
        for lg in LANGUAGES:
            w(f"  {lg}  {m['lang_counts'][lg]:6d}  "
              f"({m['lang_counts'][lg]/n*100:5.1f}%)")
        w("")
        w("ENTITY DISTRIBUTION")
        w(f"  {'label':<30}{'n':>7}{'share':>8}{'target':>8}"
          f"{'distinct':>10}{'div%':>7}{'top10':>7}")
        for lab in ENTITY_TYPES:
            cnt = m["label_counts"][lab]
            share = cnt / m["total_mentions"] if m["total_mentions"] else 0
            w(f"  {lab:<30}{cnt:>7}{share*100:>7.1f}%"
              f"{self.cfg.entity_weights[lab]*100:>7.1f}%"
              f"{int(m['diversity'][lab]*cnt):>10}"
              f"{m['diversity'][lab]*100:>6.0f}%"
              f"{m['top10_share'][lab]*100:>6.0f}%")
        w(f"  label entropy: {m['label_entropy']:.2f} / {m['max_entropy']:.2f}")
        w("")
        w("STRUCTURE & DIVERSITY")
        w(f"  unique structural signatures : {m['signature_uniqueness']*100:.2f}%")
        w(f"  most repeated signature      : {m['signature_top'][0][1]}x")
        w(f"  PII share of characters      : {m['entity_char_share']*100:.1f}%"
          "   (production is typically <5%)")
        w(f"  median entity position       : {m['position_median']:.2f}"
          "   (0=start, 1=end)")
        w(f"  docs starting with an entity : {m['leading_entity_rate']*100:.1f}%")
        w(f"  adjacent entity pairs        : {m['adjacent_pairs']}"
          f"  (same-type: {m['same_type_adjacent']})")
        w(f"  docs with repeat mentions    : {m['docs_with_repeat_mentions']*100:.1f}%")
        w(f"  UNLABELED repeat mentions    : {m['repeat_missing']}"
          "   (must be 0)")
        w("")
        w("REALISM")
        w(f"  placeholder values           : {m['placeholder_values']}  (must be 0)")
        w(f"  password-keyword share       : {m['password_keyword_share']*100:.1f}%"
          f"  (cap {self.cfg.password_keyword_share*100:.0f}%)")
        w(f"  private/reserved IP share    : {m['private_ip_share']*100:.1f}%")
        w(f"  docs with hard negatives     : {m['docs_with_hard_neg']*100:.1f}%")
        w(f"  docs with adversarial values : {m['docs_with_adversarial']*100:.1f}%")
        w(f"  noised docs                  : {m['noised_docs']*100:.1f}%")
        w(f"  mixed-script docs            : {m['mixed_script_docs']*100:.1f}%")
        w("")
        w("DOC TYPES")
        for k, v in m["doc_types"].most_common():
            w(f"  {k:<24}{v:>6}  ({v/n*100:4.1f}%)")
        w("")
        score, comps = self.generalization_estimate(m)
        w("GENERALIZATION ESTIMATE")
        for name, val, detail in comps:
            if val is None:
                w(f"  {name:<22}{'n/a':>5}       {'(by policy)':<20} {detail}")
                continue
            bar = "#" * int(val * 20)
            w(f"  {name:<22}{val*10:>5.1f}/10  {bar:<20} {detail}")
        w(f"  {'OVERALL':<22}{score:>5.1f}/10")
        w("=" * 78)
        return "\n".join(o)


_CYR = re.compile(r"[Ѐ-ӿ]")
_LAT = re.compile(r"[A-Za-z]{3,}")


def _pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))]


def _band(x, lo, hi):
    """0 below lo, 1 above hi, linear between -- keeps scoring legible."""
    if hi == lo:
        return 1.0 if x >= hi else 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))
