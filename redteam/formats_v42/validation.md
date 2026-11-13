# Formats benchmark: validation

Cases: 200 (192 with expected entities, 8 negative-only); expected occurrences: 315.

| Label | Expected occurrences |
|---|---|
| EMAIL | 63 |
| TELEPHONENUM | 62 |
| GIVENNAME | 49 |
| SURNAME | 43 |
| AZ_FIN | 36 |
| IBAN | 17 |
| AZ_PASSPORT_NUMBER | 10 |
| AZ_VOEN | 9 |
| PAYMENT_CARD_NUMBER | 8 |
| AZ_ID_CARD_NUMBER | 6 |
| IPV4_ADDRESS | 5 |
| IPV6_ADDRESS | 3 |
| MAC_ADDRESS | 2 |
| CITY | 1 |
| URL | 1 |

## Checks

1–5, 8, 10–12 are automatic; 9 is automatic for e-mail/IBAN/+994 shapes and by reading for the rest; 6–7 are automatic.

**Result:** all checks pass.
