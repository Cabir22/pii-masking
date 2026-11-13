"""`--stats` for the targeted builder (P2-4): every acceptance item of the task
as PASS/FAIL, the top-20 frame shares, and what was rebuilt and why."""

from __future__ import annotations

import collections

import re

from ..config import ENTITY_TYPES
from ..negatives import ED25519_PUBLIC_LEAD
from ..resolver import resolve_claims
from ..validate import value_valid
from . import suffix as SFX

INFLECTABLE = ("GIVENNAME", "SURNAME", "CITY", "STREET")

RESERVED_TLDS = ("invalid", "test", "example", "local")
OPENERS, CLOSERS = "([{\"«'", ")]}\"»',;:.!?"


def compute_stats(records: list[dict], builder) -> dict:
    n = len(records)
    q = builder.q
    t = q["targets"]

    def share(k: float) -> float:
        return k / n if n else 0.0

    label_mentions = collections.Counter(e["label"] for r in records for e in r["entities"])
    decoy_kinds = collections.Counter(x["kind"] for r in records for x in r["_decoys"])
    frame_docs = collections.Counter(f for r in records for f in set(r["_frame_ids"]))
    families = collections.Counter(r["_spec"]["family"] for r in records)
    groups = collections.Counter(r["_spec"].get("group") for r in records
                                 if r["_spec"]["family"] == "decoy_pair")
    prose_gaps = [g for r in records if r["_spec"]["family"] == "prose"
                  for g in r["_spec"]["anchor_gaps"]]
    near = sum(1 for g in prose_gaps if 2 <= g <= 6)
    token_key = [r for r in records if r["_spec"].get("sub") == "token_key"]
    same_body = sum(1 for r in token_key if r["_spec"].get("same_body"))
    formats = collections.Counter(r["_spec"]["format"] for r in records
                                  if r["_spec"]["family"] == "structured")
    per_format: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for r in records:
        if r["_spec"]["family"] == "structured":
            for e in r["entities"]:
                per_format[r["_spec"]["format"]][e["label"]] += 1
    reserved = sum(1 for r in records for e in r["entities"]
                   if e["label"] == "EMAIL" and e["text"].rsplit(".", 1)[-1] in RESERVED_TLDS)
    decoy_docs = sum(1 for r in records if r["_decoys"])
    pii_free = sum(1 for r in records if not r["entities"])
    single = sum(1 for r in records if len(r["entities"]) == 1)
    expected = set(builder.kinds)
    top = frame_docs.most_common(20)
    gmin = t["name_building_group_min"]

    # P2-4b extras
    n_ents = sum(label_mentions.values())
    case_noise = [x for r in records for x in r["_spec"].get("case_noise", ())]
    # names from the homograph list (P2-4d) are not minted, so never respelled
    listed_names = sum(r["_spec"].get("listed_names", 0) for r in records)
    name_ents = sum(label_mentions[lab] for lab in ("GIVENNAME", "SURNAME")) - listed_names
    variants = [x for r in records for x in r["_spec"].get("name_variants", ())]
    invalid_variants = [v for lab, v, _k in variants if not value_valid(lab, v)[0]]
    pem = [p for r in records for p in r["_spec"].get("pem", ())]
    touch = sum(len(r["_spec"].get("touch", ())) for r in records)
    adjacent = sum(1 for r in records for e in r["entities"]
                   if (e["start"] > 0 and r["text"][e["start"] - 1] in OPENERS)
                   or (e["end"] < len(r["text"]) and r["text"][e["end"]] in CLOSERS + "\n"))
    by_label = lambda lab: [e["text"] for r in records for e in r["entities"] if e["label"] == lab]  # noqa: E731
    grouped = {lab: (sum(" " in v for v in by_label(lab)), len(by_label(lab)))
               for lab in ("TELEPHONENUM", "PAYMENT_CARD_NUMBER", "IBAN")}
    urls = by_label("URL")
    url_query = sum(1 for u in urls if "?" in u and "&" in u.split("?", 1)[1])
    variant_share = len(variants) / name_ents if name_ents else 0.0
    # P2-4c: inflected names, surnames, cities and streets
    inflectable = sum(label_mentions[lab] for lab in INFLECTABLE)
    sfx = [(r, x) for r in records for x in r.get("_suffixes", ())]
    by_case = collections.Counter(x["case"] for _r, x in sfx)
    by_group = collections.Counter(SFX.CASE_GROUP[x["case"]] for _r, x in sfx)
    by_surface = collections.Counter(x["surface"] for _r, x in sfx)
    n_sfx = len(sfx)
    sfx_share = n_sfx / inflectable if inflectable else 0.0
    unresolved = 0
    for r in records:
        xs = r.get("_suffixes") or []
        if not xs:
            continue
        label_at = {(e["start"], e["end"]): e["label"] for e in r["entities"]}
        got, _ = resolve_claims(r["text"], [{"label": label_at[(x["start"], x["end"])],
                                             "text": r["text"][x["start"]:x["stem_end"]]} for x in xs],
                                blocked=[(x["start"], x["end"]) for x in r["_decoys"]],
                                declared=[(x["start"], x["end"]) for x in xs])
        got = {(g["start"], g["end"]) for g in got}
        unresolved += sum((x["start"], x["end"]) not in got for x in xs)
    low_cases = [c for c in SFX.C1_CASES if by_case[c] < t["suffix_case_min"] * n_sfx]
    low_groups = [g for g in SFX.TIER2_GROUPS if by_group[g] < t["suffix_group_min"] * n_sfx]
    surface_share = (by_surface["apostrophe"] + by_surface["folded"]) / n_sfx if n_sfx else 0.0
    noisy_share = by_surface["noisy"] / n_sfx if n_sfx else 0.0

    # P2-4d: minimal-context documents and homograph pairs
    minimal = [r for r in records if r["_spec"]["family"] == "minimal"]
    homograph = [r for r in records if r["_spec"]["family"] == "homograph"]
    both_sides = sum(1 for r in homograph
                     if any(e["label"] == "GIVENNAME" for e in r["entities"])
                     and any(x["kind"] == "homograph_noun" for x in r["_decoys"]))
    labelled_nouns = sum(1 for r in records for x in r["_decoys"] if x["kind"] == "homograph_noun"
                         for e in r["entities"] if e["start"] < x["end"] and x["start"] < e["end"])
    lone_word = [r for r in minimal if r["_spec"].get("minimal") == "lone_word"]
    lone_name = [r for r in minimal if r["_spec"].get("minimal") in ("name_alone", "name_punct")]
    d10_ok = (all(not r["entities"] for r in lone_word)
              and all(any(e["label"] == "GIVENNAME" for e in r["entities"]) for r in lone_name))
    homograph_names = collections.Counter(r["_spec"]["homograph"] for r in homograph)
    tol = t["family_tolerance"]

    # D-39b: every name construction the team listed, and the patronymics
    namelist = [r for r in records if r["_spec"]["family"] == "namelist"]
    nl_subs = collections.Counter(r["_spec"]["namelist"] for r in namelist)
    patronymics = sum(1 for r in namelist for e in r["entities"]
                      if e["label"] == "GIVENNAME" and r["text"][e["end"]:].startswith((" oğlu", " qızı")))

    # D-51h / D-51d / D-51i / D-27
    d51 = d51_counts(records, q)
    v41 = v41_counts(records, q)
    d57 = d57_counts(records, q)
    tq = t

    pem_ok = (len({p["width"] for p in pem}) >= 2 and {"block", "flat"} <= {p["layout"] for p in pem}
              and "newline" in {p["after"] for p in pem}
              and bool({p["after"] for p in pem} - {"newline"}))

    checks = {
        "all 27 labels present":
            (len(label_mentions) == len(ENTITY_TYPES), f"{len(label_mentions)}/{len(ENTITY_TYPES)}"),
        "every decoy kind present":
            (not expected - set(decoy_kinds), f"{len(expected & set(decoy_kinds))}/{len(expected)}"),
        "decoy documents >= 25%":
            (share(decoy_docs) >= t["decoy_docs_min"], f"{share(decoy_docs):.1%}"),
        "PII-free ~10%":
            (abs(share(pii_free) - t["pii_free"]) <= t["pii_free_tolerance"], f"{share(pii_free):.1%}"),
        "single-entity >= 25%":
            (share(single) >= t["single_entity_min"], f"{share(single):.1%}"),
        "structured >= 15%":
            (share(families["structured"]) >= t["structured_min"], f"{share(families['structured']):.1%}"),
        "max frame share <= 3%":
            ((share(top[0][1]) <= q["max_frame_share"]) if top else True,
             f"{share(top[0][1]):.2%} ({top[0][0]})" if top else "-"),
        "name decoys, sentence-initial >= 5%":
            (share(groups["sentence_initial"]) >= gmin, f"{share(groups['sentence_initial']):.1%}"),
        "name decoys, company/project/topic >= 5%":
            (share(groups["policy_names"]) >= gmin, f"{share(groups['policy_names']):.1%}"),
        "building decoys, otaq/mərtəbə by bina >= 5%":
            (share(groups["building"]) >= gmin, f"{share(groups['building']):.1%}"),
        "prose: anchor 2-6 words away >= 1/3":
            ((near / len(prose_gaps) if prose_gaps else 0) >= t["anchor_distance_min"],
             f"{(near / len(prose_gaps) if prose_gaps else 0):.1%} of {len(prose_gaps)} anchored"),
        "token/key with the same body >= 15%":
            ((same_body / len(token_key) if token_key else 0) >= t["same_body_min"],
             f"{(same_body / len(token_key) if token_key else 0):.1%} of {len(token_key)}"),
        "ID card and licence in every format":
            (bool(formats) and all(per_format[f]["AZ_ID_CARD_NUMBER"]
                                   and per_format[f]["AZ_DRIVER_LICENSE_NUMBER"] for f in formats),
             " ".join(f"{f}:{per_format[f]['AZ_ID_CARD_NUMBER']}/"
                      f"{per_format[f]['AZ_DRIVER_LICENSE_NUMBER']}" for f in sorted(formats))),
        # P2-4b
        "casing-noise entities <= 8%":
            (0 < len(case_noise) <= t["case_noise_max"] * n_ents,
             f"{len(case_noise) / n_ents if n_ents else 0:.2%} of {n_ents}"),
        "names in another spelling/script ~10%, all valid":
            (abs(variant_share - t["name_variant"]) <= t["name_variant_tolerance"]
             and not invalid_variants,
             f"{variant_share:.1%} of {name_ents}, {len(invalid_variants)} invalid"
             + (f" ({listed_names} homograph-list names left out)" if listed_names else "")),
        "PEM: 64/76 columns, multi- and one-line, +/- newline":
            (pem_ok, f"{len(pem)} keys, widths {sorted({p['width'] for p in pem})}"),
        "values in brackets or quotes":
            (touch > 0, f"{touch} wrapped; {adjacent / n_ents if n_ents else 0:.1%} of entities touch punctuation or a line break"),
        "URLs with the token in a multi-parameter query":
            (url_query > 0, f"{url_query}/{len(urls)}"),
        "space-grouped phones, cards and IBANs":
            (all(g for g, _n in grouped.values()),
             " ".join(f"{lab.split('_')[0].lower()}:{g}/{n}" for lab, (g, n) in grouped.items())),
        # P2-4c
        "suffixed name/city/street mentions 35-40%":
            (t["suffixed_min"] <= sfx_share <= t["suffixed_max"],
             f"{sfx_share:.1%} ({n_sfx} of {inflectable})"),
        "every C1 case >= 5% of the suffixed ones":
            (n_sfx > 0 and not low_cases, f"lowest {min((by_case[c] for c in SFX.C1_CASES), default=0)}"
             f"/{n_sfx}" + (f"; below: {low_cases}" if low_cases else "")),
        "every tier-2 form group present (>= 1%)":
            (n_sfx > 0 and not low_groups, f"{len(SFX.TIER2_GROUPS) - len(low_groups)}/{len(SFX.TIER2_GROUPS)}"
             + (f"; below: {low_groups}" if low_groups else "")),
        "suffixed spans resolve from the stem":
            (n_sfx > 0 and unresolved == 0, f"{n_sfx - unresolved}/{n_sfx}"),
        "apostrophe / folded forms ~10% of suffixed":
            (abs(surface_share - t["suffix_surface"]) <= t["suffix_surface_tolerance"],
             f"{surface_share:.1%} (apostrophe {by_surface['apostrophe']}, folded {by_surface['folded']})"),
        "noisy suffixes ~5% of suffixed, labelled whole":
            (abs(noisy_share - t["suffix_noisy"]) <= t["suffix_noisy_tolerance"],
             f"{noisy_share:.1%} ({by_surface['noisy']})"),
        # P2-4d
        "minimal-context documents ~5%":
            (abs(share(len(minimal)) - t["minimal"]) <= tol, f"{share(len(minimal)):.1%}"),
        "homograph pairs ~5%, both sides in each":
            (abs(share(len(homograph)) - t["homograph"]) <= tol and both_sides == len(homograph),
             f"{share(len(homograph)):.1%}, {both_sides}/{len(homograph)} with both sides, "
             f"{len(homograph_names)} names"),
        "homograph_noun decoys never labelled":
            (labelled_nouns == 0, f"{labelled_nouns} labelled"),
        "D-10: lone capitalised name labelled, lone lowercase word not":
            (bool(lone_word) and bool(lone_name) and d10_ok,
             f"{len(lone_name)} lone names, {len(lone_word)} lone words"),
        # D-39b
        "D-39b: every name construction present, patronymics labelled":
            (set(nl_subs) >= set(q["namelist"]["subs"]) and patronymics > 0
             and abs(share(len(namelist)) - q["families"]["namelist"]) <= tol,
             f"{share(len(namelist)):.1%}, {patronymics} patronymic fathers, "
             + " ".join(f"{k}:{v}" for k, v in sorted(nl_subs.items()))),
        # D-51h / D-51d / D-51i / D-27
        "D-51h: every v4 construction present":
            (not d51["missing"], "all present" if not d51["missing"] else f"missing {d51['missing']}"),
        "D-51h: Ed25519 private keys >= 3 per Ed25519 public look-alike":
            # the ssh-ed25519 lines are short Ed25519 public look-alikes too
            (d51["ed25519_public"] > 0 and d51["ed25519_private"]
             >= tq["ed25519_private_per_public_min"] * (d51["ed25519_public"] + d51["ssh_ed25519_public"]),
             f"{d51['ed25519_private']} private / {d51['ed25519_public']} public "
             f"(+{d51['ssh_ed25519_public']} ssh-ed25519 lines)"),
        "D-27: real-length private keys (>= 1,500 chars) >= 30%":
            (d51["private_keys"] > 0 and d51["long_private"] >= tq["long_private_key_min"] * d51["private_keys"],
             f"{d51['long_private']}/{d51['private_keys']}"),
        "D-51h: ID-card prefixes varied, DYI/MYI rare":
            (d51["id_cards"] > 0 and d51["id_other_prefix"] >= tq["id_card_other_prefix_min"] * d51["id_cards"]
             and d51["id_dyi_myi"] <= tq["id_card_dyi_myi_max"] * d51["id_cards"],
             f"{d51['id_other_prefix']} other two-letter, {d51['id_aa_ab']} AA/AB, "
             f"{d51['id_dyi_myi']} DYI/MYI of {d51['id_cards']}"),
        "D-51h: CSV tables with a cvv column":
            (d51["cvv_csv_docs"] >= tq["cvv_csv_docs_min"] * n,
             f"{d51['cvv_csv_docs']} documents ({d51['cvv_csv_with_id']} with an ID column), "
             f"{d51['cvv_csv_values']} CVVs"),
        "D-51d: no checksum-only look-alike":
            (not d51["checksum_only"], f"{d51['checksum_only']} written"),
        "D-51i: no `-ci il` inside a DATE span":
            (not d51["year_suffix_inside"], f"{d51['year_suffix_inside']} inside, "
             f"{d51['year_suffix_outside']} outside"),
        # v4.1 (D-52b-d)
        "D-52d: protected quotas (per 25k documents)":
            (not v41["protected_short"],
             "all met" if not v41["protected_short"] else f"short: {v41['protected_short']}"),
        "D-52b item 2: real one-digit-octet IPv4 >= 2 per short look-alike":
            (v41["ipv4_short_lookalikes"] > 0
             and v41["ipv4_one_digit_real"] >= 2 * v41["ipv4_short_lookalikes"],
             f"{v41['ipv4_one_digit_real']} real / {v41['ipv4_short_lookalikes']} short look-alikes"),
        "D-52b item 3: IPv4 real : look-alike >= 2 in prose":
            (v41["ipv4_prose_fake"] > 0 and v41["ipv4_prose_real"] >= 2 * v41["ipv4_prose_fake"],
             f"{v41['ipv4_prose_real']} : {v41['ipv4_prose_fake']}"),
        "D-52c: sequential dummy times written, never labelled":
            (v41["sequential_times"] > 0 and not v41["sequential_labelled"],
             f"{v41['sequential_times']} look-alikes, {v41['sequential_labelled']} labelled"),
        # D-57 (v4.2 final fix list)
        "D-57: every new construction present":
            (not d57["missing"], "all present" if not d57["missing"] else f"missing {d57['missing']}"),
        "D-57: each new look-alike beside a real value of its label":
            (not d57["alone"], f"{d57['alone']} documents without one"),
        "D-57: `24:00` labelled, never a look-alike":
            (d57["t2400_real"] > 0 and not d57["t2400_fake"],
             f"{d57['t2400_real']} labelled, {d57['t2400_fake']} look-alikes"),
    }
    return {
        "documents": n,
        "frames_source": builder.frames.source,
        "frame_version": builder.frames.version,
        "case_frames": builder.frames.case_frames,
        "families": {k: share(v) for k, v in sorted(families.items())},
        "decoy_groups": {k: share(v) for k, v in sorted(groups.items())},
        "formats": dict(sorted(formats.items())),
        "labels": dict(sorted(label_mentions.items())),
        "v41": v41,
        "decoy_kinds": dict(sorted(decoy_kinds.items())),
        "missing_decoy_kinds": sorted(expected - set(decoy_kinds)),
        "reserved_tld_emails": reserved,
        "top_frames": [(f, share(c)) for f, c in top],
        "rejections": dict(builder.rejections.most_common()),
        "case_noise": {"by_label": dict(collections.Counter(x[0] for x in case_noise)),
                       "by_kind": dict(collections.Counter(x[-1] for x in case_noise))},
        "name_variants": dict(collections.Counter(k for *_x, k in variants)),
        "pem": {"by_layout_after": dict(collections.Counter(f"{p['layout']}/{p['after']}" for p in pem)),
                "by_width": dict(collections.Counter(p["width"] for p in pem)),
                "chars": [min((p["chars"] for p in pem), default=0),
                          max((p["chars"] for p in pem), default=0)]},
        "suffix_cases": {c: by_case[c] for c in SFX.FORMS},
        "suffix_labels": dict(collections.Counter(
            next(e["label"] for e in r["entities"] if (e["start"], e["end"]) == (x["start"], x["end"]))
            for r, x in sfx)),
        "d51": {k: v for k, v in d51.items() if k != "missing"},
        "d57": {k: v for k, v in d57.items() if k not in ("missing", "alone")},
        "checks": {k: {"ok": bool(ok), "value": v} for k, (ok, v) in checks.items()},
        "pending": [],
    }


_YEAR_SUFFIX = re.compile(r"\d{4}-c[ıiuü](?:\s+il)?$")

# D-57: a new construction's look-alike and the label of the real value that
# must stand beside it in the same document
_D57_FORM_LABEL = {"voen9": "AZ_VOEN", "cvv5": "CARD_SECURITY_CODE", "cvv2": "CARD_SECURITY_CODE"}
# the recall items D-57 S5/S6 asks for (the rest are backfill margins)
D57_RECALL = ("token_prose", "cvv_mid", "card_mid", "time_radelerinde", "time_edge", "time_2400", "feb29")


def d57_counts(records: list[dict], q: dict) -> dict:
    """What the v4.2 final fix list (D-57) adds, counted on the documents:
    each construction, per 25,000 documents, and the documents where a new
    look-alike has no real value of its label beside it."""
    n = len(records) or 1
    scale = 25000 / n
    c: dict = {}
    sp = [r["_spec"] for r in records]
    kinds = collections.Counter(x["kind"] for r in records for x in r["_decoys"])
    c["age_pairs"] = sum(s.get("group") == "age" for s in sp)
    c["caps_forms"] = sum(s.get("format") == "caps_form" for s in sp)
    c["building_styles"] = dict(collections.Counter(
        ("lines/" if s.get("building_lines") else "") + s["building_style"] for s in sp if "building_style" in s))
    c["business"] = dict(collections.Counter(s["biz"] for s in sp if "biz" in s))
    for key in ("pf_near", "form_extra", "ipv6_extra", "recall"):
        c[key] = {k: round(v * scale) for k, v in sorted(collections.Counter(
            i for s in sp for i in s.get(key, ())).items())}
    c["noun_fin"] = sum(1 for s in sp if s.get("group") == "noun" and s.get("kind", "").startswith("fin_"))
    c["new_kinds"] = {k: kinds[k] for k in ("age_shaped_number", "caps_heading_control", "place_word_topic",
                                            "policy_city_in_brand", "ipv6_compressed_bad", "mac_letters_only",
                                            "voen_nine_digits")}
    times = [(r, e) for r in records for e in r["entities"] if e["label"] == "TIME"]
    c["t2400_real"] = sum(e["text"] in ("24:00", "24:00:00") for _r, e in times)
    c["t2400_fake"] = sum(r["text"][x["start"]:x["end"]] in ("24:00", "24:00:00")
                          for r in records for x in r["_decoys"])
    alone = 0
    for r in records:
        s, labs = r["_spec"], {e["label"] for e in r["entities"]}
        need = set()
        if s.get("group") == "age":
            need.add("AGE")
        if s.get("kind") == "policy_city_in_brand":
            need.add("CITY")
        if s.get("ipv6_extra"):
            need |= {"IPV6_ADDRESS", "MAC_ADDRESS"}
        need |= {_D57_FORM_LABEL[i] for i in s.get("form_extra", ()) if i in _D57_FORM_LABEL}
        alone += bool(need - labs)
    c["alone"] = alone
    missing = [k for k, v in c["new_kinds"].items() if not v]
    missing += [k for k in ("street", "ev", "bina") if not any(x.endswith(k) for x in c["building_styles"])]
    missing += [] if any(x.startswith("lines/") for x in c["building_styles"]) else ["building lines"]
    missing += [k for k in q["pii_free_business"]["kinds"] if not k.startswith("_") and not c["business"].get(k)]
    missing += [f"pf_near/{k}" for k in q["pii_free"]["near_miss"] if not c["pf_near"].get(k)]
    missing += [f"form_extra/{k}" for k in q["form"]["extras"] if not c["form_extra"].get(k)]
    missing += [f"ipv6_extra/{k}" for k in q["contrast"]["ipv6_extras"] if not c["ipv6_extra"].get(k)]
    # the S5/S6 items; the backfill items only keep margins (some are rare)
    missing += [f"recall/{k}" for k in D57_RECALL if not c["recall"].get(k)]
    missing += [k for k in ("age_pairs", "caps_forms", "noun_fin") if not c[k]]
    c["missing"] = missing
    return c


def v41_counts(records: list[dict], q: dict) -> dict:
    """v4.1 (D-52b-d): the protected quotas per 25,000 documents, IPv4 with
    one-digit octets against the short look-alikes, IPv4 real against
    look-alike in prose, and the sequential dummy times (D-52c)."""
    from ..negatives import SEQUENTIAL_TIMES
    n = len(records) or 1
    scale = 25000 / n
    kinds = collections.Counter(x["kind"] for r in records for x in r["_decoys"])
    subs = collections.Counter(r["_spec"].get("sub") for r in records if r["_spec"]["family"] == "contrast")
    time_after = sum(1 for r in records for x in r["_decoys"]
                     # v4.2: the near-miss time kinds (24-29 h, 60-69 min) count too
                     if x["kind"] in ("time_bad_hour", "time_bad_minute", "time_3_digit_minutes",
                                      "time_hour_near", "time_minute_near")
                     and re.search(r"saat|vaxt", r["text"][max(0, x["start"] - 25):x["start"]].lower()))
    disagree = collections.Counter(line.split(":", 1)[1] for r in records
                                   for line in r["_spec"].get("licence_id_lines", []) if line.startswith("disagree"))
    got = {f"contrast.{k}": subs[k] * scale for k in q["protected"]["contrast_subs"] if not k.startswith("_")}
    got.update({k: kinds[k] * scale for k in q["protected"]["kinds"] if not k.startswith("_")})
    got["time look-alike after saat/vaxt"] = time_after * scale
    got["licence_id disagree, each way"] = min(disagree.values(), default=0) * scale
    floors = {f"contrast.{k}": v for k, v in q["protected"]["contrast_subs"].items() if not k.startswith("_")}
    floors.update({k: v for k, v in q["protected"]["kinds"].items() if not k.startswith("_")})
    floors.update({k: v for k, v in q["protected"]["contexts"].items() if not k.startswith("_")})
    # two documents' worth of sampling slack (1.8 per 25k at 28,000 documents;
    # it matters only in the small test builds)
    slack = 2 * scale
    short = {k: f"{got[k]:.0f}<{v}" for k, v in floors.items() if got[k] + slack < v}

    def one_digit(v: str) -> bool:
        return sum(len(p) == 1 for p in v.split(".")) >= 2

    def prose(r: dict, s: int) -> bool:
        if r["_spec"].get("format"):
            return False
        ls = r["text"].rfind("\n", 0, s) + 1
        return not re.fullmatch(r"\s*[\w ./()-]{1,40}:\s*", r["text"][ls:s])

    ip_real = [(r, e) for r in records for e in r["entities"] if e["label"] == "IPV4_ADDRESS"]
    ip_fake = [(r, x) for r in records for x in r["_decoys"]
               if x["kind"] in ("ipv4_octet_over_255", "ipv4_short_over_255", "ipv4_three_octets", "ipv4_placeholder")]
    return {
        "protected": {k: round(v) for k, v in got.items()},
        "protected_short": short,
        "ipv4_one_digit_real": sum(one_digit(e["text"]) for _r, e in ip_real),
        "ipv4_short_lookalikes": kinds["ipv4_short_over_255"] + kinds["ipv4_placeholder"],
        "ipv4_prose_real": sum(prose(r, e["start"]) for r, e in ip_real),
        "ipv4_prose_fake": sum(prose(r, x["start"]) for r, x in ip_fake),
        "sequential_times": kinds["policy_sequential_time"],
        "sequential_labelled": sum(e["label"] == "TIME" and e["text"] in SEQUENTIAL_TIMES
                                   for r in records for e in r["entities"]),
        "net_context_docs": sum(r["_spec"]["family"] == "net_context" for r in records),
        "synthetic_emails": sum(e["label"] == "EMAIL" and bool(re.match(
            r"(test\.user|demo\.user|qa\.tester|sample\.account|trial\.user|user\.test|dev\.tester)\d", e["text"]))
            for r in records for e in r["entities"]),
        "zip_after_zip_word": sum(z == "after ZIP" for r in records for z in r["_spec"].get("zips", [])),
    }


def d51_counts(records: list[dict], q: dict) -> dict:
    """What the v4 targeted data (D-51h, D-51d, D-51i, D-27) adds, counted on
    the documents themselves."""
    c: dict = {}
    fam = lambda name: [r for r in records if r["_spec"]["family"] == name]   # noqa: E731
    keys = [e["text"] for r in records for e in r["entities"] if e["label"] == "PRIVATE_KEY"]
    pubs = [r["text"][x["start"]:x["end"]] for r in records for x in r["_decoys"]
            if x["kind"] in ("public_key_block", "public_key_ssh")]
    c["private_keys"] = len(keys)
    c["long_private"] = sum(len(k) >= 1500 for k in keys)
    c["ed25519_private"] = sum("MC4CAQAw" in k for k in keys)
    c["ed25519_public"] = sum(ED25519_PUBLIC_LEAD in p for p in pubs)
    c["ssh_ed25519_public"] = sum(p.startswith("ssh-ed25519") for p in pubs)
    ids = [e["text"].upper() for r in records for e in r["entities"] if e["label"] == "AZ_ID_CARD_NUMBER"]
    c["id_cards"] = len(ids)
    c["id_dyi_myi"] = sum(i[:3] in ("DYI", "MYI") for i in ids)
    c["id_aa_ab"] = sum(i[:2] in ("AA", "AB") for i in ids)
    c["id_other_prefix"] = c["id_cards"] - c["id_dyi_myi"] - c["id_aa_ab"]
    cvv_csv = [r for r in records if r["_spec"].get("cvv_rows")]
    c["cvv_csv_docs"] = len(cvv_csv)
    c["cvv_csv_with_id"] = sum("AZ_ID_CARD_NUMBER" in r["_spec"]["columns"] for r in cvv_csv)
    c["cvv_csv_values"] = sum(e["label"] == "CARD_SECURITY_CODE" for r in cvv_csv for e in r["entities"])
    c["id_and_licence_docs"] = sum(1 for r in records if r["_spec"].get("id_and_licence"))
    checksum = {"card_luhn_invalid", "tracking_code_15_16", "LOYALTY_CARD_LUHN_BAD", "IBAN_BAD_CHECKSUM"}
    c["checksum_only"] = sum(x["kind"] in checksum for r in records for x in r["_decoys"])
    dates = [(r, e) for r in records for e in r["entities"] if e["label"] == "DATE"]
    c["year_suffix_inside"] = sum(bool(_YEAR_SUFFIX.search(e["text"])) or e["text"].endswith(" il")
                                  for _r, e in dates)
    c["year_suffix_outside"] = sum(bool(re.match(r"-c[ıiuü] il\b", r["text"][e["end"]:e["end"] + 6]))
                                   for r, e in dates)
    # the families and their sub-constructions
    cross = collections.Counter(r["_spec"]["cross_slot"] for r in fam("cross_anchor"))
    c["cross_anchor"] = dict(sorted(cross.items()))
    c["cross_short_labels"] = dict(collections.Counter(
        f"{r['_spec']['short_label']}/{r['_spec']['short_format']}" for r in fam("cross_anchor")
        if "short_label" in r["_spec"]))
    c["cross_name_kinds"] = dict(collections.Counter(
        f"{r['_spec']['name_label']}/{r['_spec']['name_kind']}" for r in fam("cross_anchor")
        if "name_label" in r["_spec"]))
    loc = fam("locative")
    c["locative_values"] = dict(collections.Counter(
        e["label"] for r in loc for e in r["entities"]))
    c["locative_look_alikes"] = sum(len(r["_decoys"]) for r in loc)
    slot = fam("slot_invalid")
    c["slot_invalid"] = dict(collections.Counter(
        f"{r['_spec']['slot_label']}/{r['_spec']['slot_format']}" for r in slot))
    pv = fam("place_verbs")
    c["place_verbs"] = dict(collections.Counter(i for r in pv for i in r["_spec"]["place_verbs"]))
    c["place_verbs_ins_separate"] = sum(r["_spec"].get("ins_separate", 0) for r in pv)
    nl = fam("namelist")
    c["namelist_controls"] = dict(collections.Counter(
        x["kind"] for r in nl for x in r["_decoys"]))
    c["short_key_docs"] = len(fam("short_keys"))
    # v3_shadow_shapes.md lead 1: labelled times with seconds, and the line
    # stamps beside them that stay unlabelled
    ts = fam("time_seconds")
    c["time_seconds"] = dict(collections.Counter(r["_spec"]["time_sub"] for r in ts))
    c["time_with_seconds"] = sum(bool(re.fullmatch(r"\d{2}:\d{2}:\d{2}", e["text"]))
                                 for r in records for e in r["entities"] if e["label"] == "TIME")
    c["time_line_stamps"] = sum(x["kind"] == "time_line_stamp" for r in records for x in r["_decoys"])
    # v4.1 A5: bare ZIPs right after a town, with no index word (postal)
    c["zip_bare_no_word"] = sum(z == "bare, no index word" for r in fam("postal") for z in r["_spec"].get("zips", []))
    # v4.1 A5: private-key blocks with a placeholder body, unlabelled
    c["key_placeholders"] = sum(x["kind"] == "private_key_placeholder" for r in records for x in r["_decoys"])
    c["new_kinds"] = dict(collections.Counter(
        x["kind"] for r in records for x in r["_decoys"] if x["kind"] in D51_KINDS))
    missing = [s for s in q["cross_anchor"]["subs"] if not cross[s]]
    missing += [lab for lab in q["locative"]["label_weights"] if not c["locative_values"].get(lab)]
    missing += [lab for lab in ("TIME", "AGE", "DATE", "AZ_FIN", "PAYMENT_CARD_NUMBER", "ZIPCODE")
                if not any(k.startswith(lab + "/") for k in c["slot_invalid"])]
    missing += [k for k in ("cop", "ins", "acc", "abl", "surname") if not c["place_verbs"].get(k)]
    missing += [k for k in ("namelist_control", "role_word_control", "signature_title_only")
                if not c["namelist_controls"].get(k)]
    missing += [k for k in D51_KINDS if not c["new_kinds"].get(k)]
    if not c["short_key_docs"]:
        missing.append("short_keys")
    missing += [s for s in q["time_seconds"]["sub_weights"] if not c["time_seconds"].get(s)]
    if not c["time_line_stamps"]:
        missing.append("time_line_stamp")
    if not c["key_placeholders"]:
        missing.append("private_key_placeholder")
    if not c["zip_bare_no_word"]:
        missing.append("zip_bare_no_word")
    c["line_start"] = dict(collections.Counter(k for r in fam("namelist")
                                               for k, n in (r["_spec"].get("line_start") or {}).items()
                                               for _ in range(n)))
    if not c["line_start"].get("name") or not c["line_start"].get("role"):
        missing.append("line_start")
    c["missing"] = list(dict.fromkeys(missing))
    return c


# the look-alike kinds D-51h added (negatives.py)
D51_KINDS = ("voen_short_number", "fin_short_number", "id_card_short_number", "token_short_number",
             "api_key_short_number", "code_in_name_slot", "room_code", "door_code",
             "mac_fragment_dashed", "iban_fragment_short", "ipv4_short_over_255",
             "ipv4_three_octets", "ipv4_placeholder", "card_wrong_length",
             "namelist_control", "role_word_control", "signature_title_only",
             "zip_two_digits")


def format_stats(st: dict) -> str:
    out = [f"documents          : {st['documents']}",
           f"frames             : {st['frames_source']} ({st['frame_version']}); "
           f"{st['case_frames']} C1 {{v:CASE}} frames, filled by the suffix renderer",
           "families           : " + ", ".join(f"{k} {v:.1%}" for k, v in st["families"].items()),
           "decoy pair groups  : " + ", ".join(f"{k} {v:.1%}" for k, v in st["decoy_groups"].items()),
           "structured formats : " + ", ".join(f"{k} {v}" for k, v in st["formats"].items()),
           f"reserved-TLD emails: {st['reserved_tld_emails']}",
           f"decoy kinds        : {len(st['decoy_kinds'])} present",
           "", "labels (mentions):"]
    labels = list(st["labels"].items())
    for i in range(0, len(labels), 3):
        out.append("   " + "   ".join(f"{k:26} {v:6}" for k, v in labels[i:i + 3]))
    out += ["", "top-20 frames (share of documents):"]
    out += [f"   {s:6.2%}  {fid}" for fid, s in st["top_frames"]]
    out += ["", "P2-4b extras:",
            "   casing noise by label : " + ", ".join(f"{k} {v}" for k, v in sorted(st["case_noise"]["by_label"].items())),
            "   casing noise by kind  : " + ", ".join(f"{k} {v}" for k, v in sorted(st["case_noise"]["by_kind"].items())),
            "   name variants by kind : " + ", ".join(f"{k} {v}" for k, v in sorted(st["name_variants"].items())),
            "   PEM layout/after      : " + ", ".join(f"{k} {v}" for k, v in sorted(st["pem"]["by_layout_after"].items())),
            f"   PEM widths / chars    : {st['pem']['by_width']} / {st['pem']['chars'][0]}-{st['pem']['chars'][1]}"]
    total = sum(st["suffix_cases"].values())
    out += ["", f"P2-4c suffixed mentions by case ({total}; labels: "
            + ", ".join(f"{k} {v}" for k, v in sorted(st["suffix_labels"].items())) + "):"]
    rows = [(c, n) for c, n in st["suffix_cases"].items()]
    for i in range(0, len(rows), 4):
        out.append("   " + "   ".join(f"{c:11} {n:5} {n / total if total else 0:6.1%}"
                                      for c, n in rows[i:i + 4]))
    out += ["", "D-51h / D-51d / D-51i / D-27 (v4 targeted data):"]
    out += [f"   {k:26} {v}" for k, v in st["d51"].items()]
    out += ["", "D-57 (v4.2 final fix list; steered items per 25k documents):"]
    out += [f"   {k:26} {v}" for k, v in st["d57"].items()]
    out += ["", "rejected while building (each one rebuilt):"]
    out += [f"   {v:6}  {k}" for k, v in st["rejections"].items()] or ["   none"]
    out += ["", "P2-4 checks:"]
    for name, c in st["checks"].items():
        out.append(f"   {'PASS' if c['ok'] else 'FAIL'}  {name:52} {c['value']}")
    if st["missing_decoy_kinds"]:
        out.append(f"   missing decoy kinds: {st['missing_decoy_kinds']}")
    if st["pending"]:
        out += ["", "pending (later sub-tasks):"] + [f"   -  {p}" for p in st["pending"]]
    return "\n".join(out)
