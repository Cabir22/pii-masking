# m1 release check (track M decides, D-64a)

**Does AZ hold (blocking for m1)? NO.** 13 of 14 Azerbaijani rules pass; not passing: A6.
- A1 shadow-dev F1: v4.2 93.8 → m1 **93.8** (-0.0; limit −1.0: ok)
- B1 benchmark F1: v4.2 97.0 → m1 **96.4** (-0.6; limit −1.0: ok)
- A4: pass, 2.5% (with the policy-list items: 5.6%)
- A5: pass, 6.9% (with the policy-list items: 21.0%; their documents out of the count: 7.9%)
- C4: pass, 0 of 11 families above 15%; overall 0.0%; decoy_cvv: 12345 0/2; random 5-digit 0/5
- E3: pass, (1) 90.4% found ok; (2) CITY 16 vs 12 of 27, GIVENNAME 90 vs 13 of 93, SURNAME 63 vs 15 of 67, TELEPHONENUM 10 vs 10 of 10 ok; (3) precision 92.0% ok

**EN / TR / RU (report for m1; m2 is judged on them):**
- A7 (fail): EN: translated 98.7 → 85.7 FAIL, independent 32.7 → 78.3; TR: translated 89.4 → 93.8, independent 19.7 → 60.9; RU: translated 89.1 → 95.1, no independent set yet: translated only
- A10 (fail): shadow-dev: 6 labels: MAC_ADDRESS 97.0 → 91.5, STREET 94.6 → 89.8, GIVENNAME 96.9 → 94.0, BUILDINGNUM 92.5 → 90.2, AZ_ID_CARD_NUMBER 98.1 → 95.8, ACCESS_TOKEN 96.7 → 95.4; benchmark: 4 labels: MAC_ADDRESS 95.7 → 67.6, BUILDINGNUM 95.3 → 93.7, AZ_ID_CARD_NUMBER 99.0 → 97.7, ZIPCODE 99.7 → 98.4
- B3 (fail): 1 labels: MAC_ADDRESS 95.6 → 74.1 (vs v4.2, policy items out)
- Turkish probes: 12 of 17 families pass (checkpoint 1: 4 of 17), micro F1 92.2

Verdict line of release_check (A7/A10/B3 counted as blocking there; for m1 they are report-only per m1_plan.md): not released, 13 of 17 pass.
