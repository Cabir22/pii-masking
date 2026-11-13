"""D-51h review: each item of the v4 task sheet checked on a targeted build.

For every item: how many documents carry it, and whether it is labelled and
paired as specified (the real value labelled, the look-alike declared in
`_decoys` and unlabelled, both in the same document).

    python reports/v4_generator/check_d51h.py BUILD.jsonl [--json OUT]
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from piigen import checksums as CK  # noqa: E402
from piigen.locales.az import year_suffix  # noqa: E402
from piigen.targeted.builder import SHORT_KIND, NAME_SLOT_KINDS, IPV4_KINDS  # noqa: E402

ID_RE = re.compile(r"^(?:[A-Z]{2}|DYI|MYI)\d{7}$")
LIC_RE = re.compile(r"^[A-Z]{2}\d{6}$")
CHECKSUM_ONLY = {"card_luhn_invalid", "tracking_code_15_16", "LOYALTY_CARD_LUHN_BAD", "IBAN_BAD_CHECKSUM"}


def span(r, x):
    return r["text"][x["start"]:x["end"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("build", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    recs = [json.loads(l) for l in args.build.open(encoding="utf-8")]
    fam = collections.defaultdict(list)
    for r in recs:
        fam[r["_spec"]["family"]].append(r)
    rows, problems = [], collections.defaultdict(list)

    def paired(r, label, kinds):
        has_real = any(e["label"] == label for e in r["entities"])
        has_fake = any(x["kind"] in kinds for x in r["_decoys"])
        return has_real and has_fake

    def overlap(r):
        """a declared look-alike overlapping a labelled span (it must stay unlabelled)"""
        return any(x["start"] < e["end"] and e["start"] < x["end"] for x in r["_decoys"] for e in r["entities"])

    cross = collections.defaultdict(list)
    for r in fam["cross_anchor"]:
        cross[r["_spec"]["cross_slot"]].append(r)
        if overlap(r):
            problems["cross_anchor: look-alike inside a label"].append(r["id"])

    # 1. short numbers
    c = collections.Counter()
    for r in cross["short_number"]:
        lab = r["_spec"]["short_label"]
        ok = paired(r, lab, {SHORT_KIND[lab]})
        fakes = [span(r, x) for x in r["_decoys"] if x["kind"] == SHORT_KIND[lab]]
        ok &= all(re.fullmatch(r"\d{2,3}", f) for f in fakes)
        c[f"{lab}/{r['_spec']['short_format']}"] += 1
        if not ok:
            problems["1 short number not paired / not 2-3 digits"].append(r["id"])
    rows.append(("1 Short numbers after VÖEN/FİN/vəsiqə/token/API words, paired", len(cross["short_number"]), dict(c)))

    # 2. name slots
    c = collections.Counter()
    for r in cross["name_org"]:
        lab, kind = r["_spec"]["name_label"], r["_spec"]["name_kind"]
        c[f"{lab}/{kind}/{r['_spec'].get('name_format', 'prose')}"] += 1
        if not paired(r, lab, {kind}):
            problems["2 name slot not paired"].append(r["id"])
    rows.append(("2 Company/project/brand names and codes in soyad/şəhər/küçə slots, paired", len(cross["name_org"]), dict(c)))

    # 3. right context + room codes
    c = collections.Counter()
    for r in cross["zip_code"]:
        x = next(x for x in r["_decoys"] if x["kind"] == "zip_shape_as_code")
        tail = r["text"][x["end"]:x["end"] + 14]
        c["zip_code (… məhsul/anbar/partiya kodu)"] += 1
        if not (paired(r, "ZIPCODE", {"zip_shape_as_code"}) and re.match(r" (məhsul|anbar|partiya) kodu", tail)):
            problems["3 zip right-context not paired"].append(r["id"])
    for r in cross["room_code"]:
        c[r["_spec"]["room_kind"]] += 1
        if not paired(r, "CARD_SECURITY_CODE", {"room_code", "door_code"}):
            problems["3 room/door code not paired with a CVV"].append(r["id"])
    rows.append(("3 Right-context look-alikes (… məhsul kodu, … qapı kodu) and room numbers + kodu", len(cross["zip_code"]) + len(cross["room_code"]), dict(c)))

    # 4. MAC / IBAN / IPv4
    c = collections.Counter()
    for r in cross["mac_fragment"]:
        c["mac_fragment_dashed"] += 1
        fr = [span(r, x) for x in r["_decoys"] if x["kind"] == "mac_fragment_dashed"]
        if not (paired(r, "MAC_ADDRESS", {"mac_fragment_dashed"}) and all(CK.date_valid(f) is False for f in fr)):
            problems["4 MAC fragment not paired or a valid date"].append(r["id"])
    for r in cross["iban_fragment"]:
        c[f"{r['_spec']['iban_kind']}/{r['_spec'].get('iban_format', 'prose')}"] += 1
        if not paired(r, "IBAN", {"iban_fragment_short", "zip_shape_in_iban_field"}):
            problems["4 IBAN fragment not paired"].append(r["id"])
    for r in cross["ipv4"]:
        c[r["_spec"]["ipv4_kind"]] += 1
        if not paired(r, "IPV4_ADDRESS", set(IPV4_KINDS)):
            problems["4 IPv4 look-alike not paired"].append(r["id"])
    rows.append(("4 MAC fragments, IBAN fragments (incl. CSV iban cells), IPv4 short/3-part/placeholder", len(cross["mac_fragment"]) + len(cross["iban_fragment"]) + len(cross["ipv4"]), dict(c)))

    # 5. locative + verb
    c = collections.Counter(e["label"] for r in fam["locative"] for e in r["entities"])
    lk = collections.Counter(x["kind"] for r in fam["locative"] for x in r["_decoys"])
    if any(k in CHECKSUM_ONLY for k in lk):
        problems["5 a checksum-only look-alike in the locative frame"].append(str(lk))
    rows.append(("5 Locative + verb frame with real values", len(fam["locative"]), {**dict(c), "look-alikes": dict(lk)}))

    # 6. ID cards / licences
    ids = [span(r, e) for r in recs for e in r["entities"] if e["label"] == "AZ_ID_CARD_NUMBER"]
    lics = [span(r, e) for r in recs for e in r["entities"] if e["label"] == "AZ_DRIVER_LICENSE_NUMBER"]
    pre = collections.Counter("DYI/MYI" if i[:3].upper() in ("DYI", "MYI") else ("AA/AB" if i[:2].upper() in ("AA", "AB") else "other")
                              for i in ids)
    bad_id = [i for i in ids if not ID_RE.match(i.strip().upper())]
    bad_lic = [l for l in lics if not LIC_RE.match(l.strip().upper())]
    if bad_id or bad_lic:
        problems["6 ID/licence shape"].append(f"{bad_id[:3]} {bad_lic[:3]}")
    keys = collections.Counter()
    for r in recs:
        fmt = r["_spec"].get("format")
        for k in ("şəxsiyyət_vəsiqəsi", "sürücülük_vəsiqəsi"):
            if fmt and k in r["text"]:
                keys[f"{k}/{fmt}"] += 1
    side = sum(1 for r in recs if r["_spec"].get("id_and_licence"))
    rows.append(("6 ID-card prefixes; licences 2+6, IDs 2+7; snake_case keys", len(ids),
                 {"prefixes": dict(pre), "licences": len(lics), "id+licence side by side docs": side,
                  "snake_case keys by format": dict(sorted(keys.items()))}))

    # 7. Ed25519
    keys_ = [span(r, e) for r in recs for e in r["entities"] if e["label"] == "PRIVATE_KEY"]
    pubs = [span(r, x) for r in recs for x in r["_decoys"] if x["kind"] in ("public_key_block", "public_key_ssh")]
    priv = sum("MC4CAQAw" in k for k in keys_)
    pub_pem = sum("MCowBQYDK2VwAyEA" in p for p in pubs)
    pub_ssh = sum(p.startswith("ssh-ed25519") for p in pubs)
    rows.append(("7 Short Ed25519 private keys >= 3 per public look-alike", priv,
                 {"private": priv, "public PEM": pub_pem, "ratio PEM": round(priv / max(pub_pem, 1), 2),
                  "public ssh-ed25519 lines": pub_ssh, "ratio incl. ssh": round(priv / max(pub_pem + pub_ssh, 1), 2)}))

    # 8. name-list controls
    nl = collections.Counter(x["kind"] for r in fam["namelist"] for x in r["_decoys"]
                             if x["kind"] in ("namelist_control", "role_word_control", "signature_title_only"))
    for r in fam["namelist"]:
        if overlap(r):
            problems["8 control inside a label"].append(r["id"])
    rows.append(("8 Non-name controls in the name-list frames", sum(nl.values()), dict(nl)))

    # 9. suffixed cities / ablative surnames
    pv = collections.Counter()
    for r in fam["place_verbs"]:
        for s in r["_suffixes"]:
            lab = next((e["label"] for e in r["entities"] if e["start"] == s["start"]), "?")
            ent = next((e for e in r["entities"] if e["start"] == s["start"]), None)
            pv[f"{lab}/{s['case']}"] += 1
            if ent is None or ent["end"] != s["end"] or s["end"] <= s["stem_end"]:
                problems["9 suffix outside the span"].append(r["id"])
    rows.append(("9 Suffixed cities in person-like verb frames; ablative surnames", len(fam["place_verbs"]), dict(pv)))

    # 10. CSV cvv
    cv = [r for r in recs if r["_spec"].get("cvv_rows")]
    rows.append(("10 CSV rows with cvv and şəxsiyyət_vəsiqəsi columns", len(cv),
                 {"with an ID column": sum("AZ_ID_CARD_NUMBER" in r["_spec"]["columns"] for r in cv),
                  "CVVs": sum(e["label"] == "CARD_SECURITY_CODE" for r in cv for e in r["entities"]),
                  "ID cards": sum(e["label"] == "AZ_ID_CARD_NUMBER" for r in cv for e in r["entities"])}))

    # 11. invalid in the label slot
    si = collections.Counter()
    for r in fam["slot_invalid"]:
        lab = r["_spec"]["slot_label"]
        si[f"{lab}/{r['_spec']['slot_kind']}/{r['_spec']['slot_format']}"] += 1
        if not paired(r, lab, {r["_spec"]["slot_kind"]}):
            problems["11 slot invalid not paired"].append(r["id"])
    rows.append(("11 Invalid times/ages/dates/FINs, wrong-length cards in the label slot, paired", len(fam["slot_invalid"]), dict(si)))

    # 12. D-51d
    ck = collections.Counter(x["kind"] for r in recs for x in r["_decoys"] if x["kind"] in CHECKSUM_ONLY)
    imei = [span(r, x) for r in recs for x in r["_decoys"] if x["kind"] == "IMEI_BAD_LUHN"]
    imei_card = sum(CK.card_brand_ok(re.sub(r"\D", "", v)) for v in imei)
    rows.append(("12 D-51d: no checksum-only kinds; IMEI never card-shaped", sum(ck.values()),
                 {"checksum-only written": dict(ck) or 0, "IMEI_BAD_LUHN": len(imei), "IMEI card-shaped": imei_card}))
    if ck or imei_card:
        problems["12 D-51d"].append(str(ck))

    # 13. D-51i
    inside = outside = wrong = 0
    for r in recs:
        for e in r["entities"]:
            if e["label"] != "DATE":
                continue
            v = span(r, e)
            if re.search(r"-c[ıiuü]\b", v) or v.endswith(" il"):
                inside += 1
            m = re.match(r"(-c[ıiuü]) il\b", r["text"][e["end"]:e["end"] + 6])
            if m:
                outside += 1
                y = re.search(r"(\d{4})$", v)
                if not y or m.group(1) != year_suffix(int(y.group(1))):
                    wrong += 1
                    problems["13 suffix not harmonised"].append(f"{r['id']}: {v}{m.group(1)}")
    rows.append(("13 D-51i: no `-ci il` inside DATE; the suffix outside harmonised", outside,
                 {"inside": inside, "outside": outside, "not harmonised": wrong}))

    for name, n, detail in rows:
        print(f"{name}\n   documents/values: {n:,}\n   {json.dumps(detail, ensure_ascii=False)}")
    print("\nPROBLEMS:", {k: (len(v), v[:3]) for k, v in problems.items()} or "none")
    if args.json:
        args.json.write_text(json.dumps({"items": [{"item": a, "n": b, "detail": c} for a, b, c in rows],
                                         "problems": {k: v[:20] for k, v in problems.items()}},
                                        ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
