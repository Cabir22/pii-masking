# Data Schema

## Synthetic example format (JSONL)

```json
{"text": "Zəng edin: +994501234567 və ya e-poçt: john.doe@acme.com", "lang": "az", "entities": [{"start": 11, "end": 24, "label": "TELEPHONENUM"}, {"start": 34, "end": 52, "label": "EMAIL"}]}
```

- `start`/`end` are character offsets into `text` (end-exclusive).
- `lang` is `az` for the current phase. English/Russian/Turkish are future
  work, once the Azerbaijani model is good.
- Entities must not overlap within a single example.
- Generated records may carry extra `_`-prefixed fields; consumers must pass them
  through (`_decoys`, `_suffixes`, `_gen_version`, `_source`, `_frame_ids`,
  `_pii_free`: `docs/dataset_reference.md` §2). A match inside a declared
  `_decoys` span is deliberately not PII.

## Entity taxonomy (v2.0.0, locked)

Source: `Claude.pdf`, "PII Taxonomy — Final Reference" (30 candidate labels).
**27 labels included, 3 removed.** Changing this list requires explicit
confirmation (taxonomy/scope creep is a known risk).

### Removed (do not generate, validate, balance, evaluate, or export)

Kept here for traceability only — never reintroduce:

- `PASSWORD` — no fixed structure, subsumed by anchor/context detection elsewhere
- `AZ_BIRTH_CERTIFICATE_NUMBER` — no findable fixed format
- `AZ_PROPERTY_REGISTER_NUMBER` — no findable fixed format

### Detection tiers

Every label belongs to exactly one tier. This determines how it's generated
and validated — never pattern-generate an `anchor_required` or `ml_context`
label as if it had a fixed shape.

| Tier | Meaning |
|---|---|
| `pattern` | Deterministic generator, independent regex/checksum validator |
| `hybrid` | Some variants are `pattern`, others `anchor_required` (see notes) |
| `anchor_required` | No standalone signal — carrier text must contain a nearby Azerbaijani context anchor or the record is invalid |
| `ml_context` | No value-level pattern at all — sampled from a curated pool, NER-only |

### GLOBAL (22 labels)

| Label | Tier | Format | Example |
|---|---|---|---|
| `API_KEY` | pattern | Issuer prefix + high-entropy tail (`sk_live_`, `ghp_`, `AKIA`, …) or a vendor-neutral prefix (`key_`, `api_`, `apikey_`, `svc_`, `sk-live-`, `sk-test-`) + 20–64 alphanumerics. Never an ACCESS_TOKEN prefix | `key_a1B2c3D4...` |
| `ACCESS_TOKEN` | pattern | One of: 3 base64url segments (JWT); a token prefix (`at_`, `bearer_`, `tok_`, `oauth_`, `sess_`, `atk-`, `pat_`) + 20–64 base64url/hex characters; a bare 32–64-character base64url (mixed case, with a digit) or lower-case hex token. Never a valid API_KEY. Widened 2026-09-30: the benchmark's real tokens are prefixed, so the JWT-only definition was wrong | `at_Xk3...`, `eyJhbGciOiJIUzI1NiJ9...` |
| `PRIVATE_KEY` | pattern | PEM/OpenSSH armour block | `-----BEGIN PRIVATE KEY-----...` |
| `PAYMENT_CARD_NUMBER` | pattern | 13–19 digits, Luhn + BIN | `4111 1111 1111 1111` |
| `IBAN` | pattern | Country-specific length/structure, mod-97-10 checksum | `AZ21NABZ00000000137010001944` |
| `CARD_SECURITY_CODE` | anchor_required | 3–4 digits, no structure | `047` |
| `IPV4_ADDRESS` | pattern | Dotted quad | `192.168.1.20` |
| `IPV6_ADDRESS` | pattern | Colon-hex, full or `::`-compressed (start/middle/end), IPv4-embedded `::ffff:a.b.c.d`, any case | `2001:db8::1` |
| `MAC_ADDRESS` | pattern | 6 hex pairs (`:` or `-`) or Cisco dotted `aabb.ccdd.eeff`, any case, IEEE OUI-checkable | `00:1A:2B:3C:4D:5E` |
| `URL` | pattern | RFC 3986 (parse for embedded secrets/PII in query params) | `https://api.example.com/user/123` |
| `ICCID` | pattern | `89` + 18 digits, Luhn | `8994...` (20 digits) |
| `GIVENNAME` | ml_context | No pattern — NER only | `Əli`, `Aysel` |
| `SURNAME` | ml_context | No pattern — NER only | `Hüseynli`, `Məmmədova` |
| `EMAIL` | pattern | RFC 5322 | `user@example.com` |
| `TELEPHONENUM` | hybrid | E.164 or national format | `+994501234567` |
| `DATE` | anchor_required | Various formats — context needed to confirm PII-relevance (e.g. DOB) | `21.02.1956` |
| `TIME` | anchor_required | Various formats | `14:30` |
| `AGE` | anchor_required | Bare number — context-dependent | `34` |
| `CITY` | ml_context | No pattern — gazetteer/NER | `Bakı` |
| `STREET` | ml_context | No pattern — NER | `Nizami küçəsi` |
| `BUILDINGNUM` | anchor_required | Bare number — context-dependent | `23` |
| `ZIPCODE` | hybrid | Country-specific; AZ format: `AZ` + 4 digits | `AZ 1132` |

### LOCAL — Azerbaijan-specific (5 labels)

| Label | Tier | Format | Regex | Example |
|---|---|---|---|---|
| `AZ_FIN` | pattern | Personal Identification Number (also social insurance number — same value since 2021) | `^[ABCDEFGHJKLMNPQRSTUVWXYZ0-9]{7}$` (excludes I/O) | `30LJV5Z` |
| `AZ_ID_CARD_NUMBER` | pattern | Citizen ID / residence card number (D-51h: any two-letter prefix; the 7-digit body tells it from a licence's 6) | `^(?:[A-Z]{2}\|DYI\|MYI)\d{7}$` | `AA1014572`, `KT3071958` |
| `AZ_PASSPORT_NUMBER` | pattern | International passport number | `^[A-Z]\d{8}$` (full alphabet, includes I/O) | `X05000971` |
| `AZ_VOEN` | pattern | Tax ID — **check digit (position 9) unverified, do not invent a checksum** | `^\d{10}(\d{5})?$` | `1503613621` |
| `AZ_DRIVER_LICENSE_NUMBER` | pattern | Driving licence number — all 676 letter pairs, `AA`/`AB` oversampled (≥ 35%) because ID cards share them; 6 digits vs. the ID card's 7 | `^[A-Z]{2}\d{6}$` | `BA154675` |

### Notes

- **`AZ_FIN` and `AZ_PASSPORT_NUMBER` must never share an alphabet.** FIN
  excludes I/O; passport includes them.
- **Hybrid collisions:** `ZIPCODE`'s bare 4-digit domestic form is
  indistinguishable from `BUILDINGNUM` and is `anchor_required`, while the
  `AZ`-prefixed international form is `pattern`. `TELEPHONENUM`'s bare
  national form (e.g. `0501234567`, exactly 10 digits) is simultaneously a
  valid `AZ_VOEN` shape — a documented, unresolved-by-ordering collision; both
  carry anchors.
- **`AZ_FIN` / order-code collision:** a 7-character uppercase alphanumeric
  string from the same alphabet as `AZ_FIN` is a deliberate hard-negative
  target (order IDs, Git short SHAs).

## BIO tagging

Each entity type gets `B-<TYPE>` / `I-<TYPE>` tags plus `O` for non-entity
tokens. Escalate to BIOES (`E-`, `S-`) only if error analysis shows adjacent
same-type entities merging incorrectly under plain BIO.
