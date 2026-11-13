# English (golden_en, 217 documents): every m1 prediction that is not an exact gold match

Track M. Counts are **predicted spans (occurrences)**, not unique values or documents.

## m1

| Label | Category | Spans |
|---|---|---|
| DATE | standalone date unlabelled in gold (D-17: DATE) | 192 |
| GIVENNAME | GIVENNAME with no gold overlap | 81 |
| SURNAME | SURNAME with no gold overlap | 20 |
| DATE | DATE on other text | 8 |
| CITY | CITY with no gold overlap | 6 |
| AGE | AGE with no gold overlap | 3 |
| ACCESS_TOKEN | ACCESS_TOKEN with no gold overlap | 3 |
| BUILDINGNUM | BUILDINGNUM with no gold overlap | 3 |
| DATE | boundary (same label, other span) | 2 |
| STREET | STREET with no gold overlap | 2 |
| STREET | boundary (same label, other span) | 2 |
| GIVENNAME | wrong type (gold SURNAME) | 2 |
| TIME | TIME with no gold overlap | 2 |
| EMAIL | EMAIL with no gold overlap | 2 |
| AGE | MISSED gold | 2 |
| CITY | MISSED gold | 2 |
| IPV4_ADDRESS | IPV4_ADDRESS with no gold overlap | 1 |
| GIVENNAME | MISSED gold | 1 |
| BUILDINGNUM | MISSED gold | 1 |

## ckpt1

| Label | Category | Spans |
|---|---|---|
| TIME | TIME with no gold overlap | 7 |
| AGE | AGE with no gold overlap | 3 |
| GIVENNAME | GIVENNAME with no gold overlap | 2 |
| DATE | boundary (same label, other span) | 2 |
| SURNAME | SURNAME with no gold overlap | 2 |
| AGE | MISSED gold | 2 |
| STREET | boundary (same label, other span) | 1 |
| GIVENNAME | wrong type (gold SURNAME) | 1 |
| CITY | CITY with no gold overlap | 1 |
| CARD_SECURITY_CODE | CARD_SECURITY_CODE with no gold overlap | 1 |
| GIVENNAME | MISSED gold | 1 |
| SURNAME | MISSED gold | 1 |
| CITY | MISSED gold | 1 |

## m1 examples per category (first 12)

**DATE — standalone date unlabelled in gold (D-17: DATE)** (192)
- `15.05.2020` … ccount. ⏎  ⏎ Amount;Currency;Date;Status ⏎ 500;AZN;15.05.2020;Successful ⏎  ⏎ Transaction proce
- `12 March 2025` … Online Banking Malfunction ⏎ Application Date: 12 March 2025 ⏎  ⏎ Dear Bank Management, ⏎  ⏎ I am 
- `2017-09-15` … ) has been delayed. ⏎ Account_No;Amount;Status ⏎ 2017-09-15;340 AZN;Delayed
- `2022-04-12` … og: ⏎ `ID_772;Lalə;Kürənzadə;MYI6151239;ACTIVE;2022-04-12` ⏎  ⏎ --- ⏎  ⏎ ### Error Codes: ⏎ | Cod
- `12 May 2026` … Bug Report ⏎ ID: BUG-2026-941 ⏎ Date: 12 May 2026 ⏎  ⏎ Subject: Unsubscribe link no
- `10.03.2026` … dev_ops_team                       | ⏎ | Date: 10.03.2026                              
- `14 May 2015` … – DIGITAL SERVICES AND SECURITY LETTER ⏎ Date: 14 May 2015 ⏎ Subject: Important notice reg
- `10.01.2015` … ;DATE;STATUS ⏎ AZ-99281-X;MONEY_OUTFLOW;450.00;10.01.2015;SUCCESSFUL ⏎ AZ-11023-B;MONEY_I
- `12.01.2015` … 5;SUCCESSFUL ⏎ AZ-11023-B;MONEY_INFLOW;1200.00;12.01.2015;SUCCESSFUL ⏎ AZ-44901-Z;AMOUNT_
- `13.01.2015` … ;SUCCESSFUL ⏎ AZ-44901-Z;AMOUNT_TRANSFER;50.00;13.01.2015;PENDING ⏎  ⏎ A summary regarding 
- `14.05.2015` … rent Account  | 4,560.20 AZN    | AZN      | 14.05.2015  | Active      | ⏎ | Pension Ac
- `10.05.2015` … sion Account  | 1,200.00 AZN    | AZN      | 10.05.2015  | Active      | ⏎ | Foreign Cu

**GIVENNAME — GIVENNAME with no gold overlap** (81)
- `Sakam` … Operator: Sakam, I am recording your driver's
- `Elmira` … ning, what did I do? System error detected. ⏎  ⏎ Elmira Kerimova ⏎ pirmemmedxosgunov@ka
- `Leyla` … f a call center is heard in the background) ⏎  ⏎ Leyla: Hello, welcome! I am Leyla, 
- `Leyla` … the background) ⏎  ⏎ Leyla: Hello, welcome! I am Leyla, how can I help you? Have a s
- `Nizami` …  how can I help you? Have a successful day! ⏎  ⏎ Nizami: Hello... eee, I am saying Ni
- `Nizami` … sful day! ⏎  ⏎ Nizami: Hello... eee, I am saying Nizami. I have a bit of... mmm... co
- `Leyla` … an, it is as if everything is not in order. ⏎  ⏎ Leyla: Do not worry, Mr. Nizami, I 
- `Nizami` … g is not in order. ⏎  ⏎ Leyla: Do not worry, Mr. Nizami, I am here to help you. I und
- `Nizami` … em. Could you please tell me your FIN code? ⏎  ⏎ Nizami: FIN code? Hmm, one minute, I
- `Leyla` … found it. Here it is, my FIN code: 9NPMX8F. ⏎  ⏎ Leyla: Thank you very much, Mr. Niz
- `Nizami` … e: 9NPMX8F. ⏎  ⏎ Leyla: Thank you very much, Mr. Nizami. Wait a moment, I am... mmm..
- `Nizami` … ed. Which transaction are you referring to? ⏎  ⏎ Nizami: I... I am saying that I made

**SURNAME — SURNAME with no gold overlap** (20)
- `Kerimova` … hat did I do? System error detected. ⏎  ⏎ Elmira Kerimova ⏎ pirmemmedxosgunov@kaspitrade.
- `Kamilov` … This agreement was signed in 2023 between L. Kamilov (tezail.hacibababeyov@yandex.
- `Besirov` … errors at this level. ⏎  ⏎ Respectfully, ⏎  ⏎ Zarifa Besirov ⏎ Senior Software Engineer ⏎ hace
- `Rasulov` … 05.2022 ⏎ Responsible Sales Representative: A. Rasulov ⏎  ⏎ --- ⏎  ⏎ CUSTOMER ACTIVITY HISTO
- `Garayev` … rtment ⏎ Date: 15.03.2024 ⏎ Subject: CV Update - Garayev ⏎ -----------------------------
- `Eliyev` … doing this to me? Help is needed! ⏎  ⏎ --- ⏎ Murad Eliyev ⏎ Junior Data Entry ⏎ murad@hal—x
- `Rahimli` … ed in this report? I have never known Amalya Rahimli and have never had any connec
- `Urfanov` … ---------------------- ⏎ Name/Surname: Mubariz Urfanov ⏎ E-mail: zamile_alverdiyev@azs
- `Mammadov` … 24 ⏎ Report No: 2024-LAB-009827 ⏎ Technician: A. Mammadov ⏎  ⏎ ----------------------------
- `Mammadov` … ff and the patient. ⏎  ⏎ Respectfully, ⏎ Dr. Elnur Mammadov ⏎ Cardiologist
- `Sukurova` … This needs to be clarified with accounting. ⏎  ⏎ Sukurova provided a number to establis
- `Safiyev` … F THE AGREEMENT: ⏎ Tenant: Rayila ⏎ Landlord: M. Safiyev ⏎ Location: apartment located a

**DATE — DATE on other text** (8)
- `15` … Complaint and Final Warning ⏎  ⏎ Date: 15 August 2021 ⏎  ⏎ Dear management 
- `2021` … Complaint and Final Warning ⏎  ⏎ Date: 15 August 2021 ⏎  ⏎ Dear management and relevant
- `2023` … a and Recruitment Protocol ⏎ Date: October 15, 2023 ⏎  ⏎ The following information ha
- `03.2020` …      | Rental       | 1100.00      | Paid ⏎ 12.03.2020    | Fuel supply (A–95)      
- `10` … ss)     | Rental       | 1100.00      | Paid ⏎ 10.04.2020    | Fuel supply (a–9
- `04` …      | Rental       | 1100.00      | Paid ⏎ 10.04.2020    | Fuel supply (a–95) 
- `30` …  | Parking fee              | Other        | 30.00        | Paid ⏎ 05.08.2020  
- `2026` … wn. ⏎ [2026-12-31 23:59:59] [INFO] Last log of 2026. ⏎ [2026-12-31 23:59:59] [INFO]

**CITY — CITY with no gold overlap** (6)
- `Baku` …              | ⏎ | City                      | Baku                           | ⏎  ⏎ 
- `Baku` … gibat ⏎ Contact number: 994558196977 ⏎ Location: Baku city ⏎  ⏎ LESSEE: ⏎ Name: Karimat ⏎ S
- `Hamburg` … porter): "Euro-Supply" LTD ⏎ Country: Germany, Hamburg. ⏎ Address: Speicherstadt 4, 20
- `Hamburg` … ny, Hamburg. ⏎ Address: Speicherstadt 4, 20457 Hamburg. ⏎ TIN/VAT: DE123456789 ⏎  ⏎ --- ⏎  ⏎ I
- `Goranboy` …  I am Bəzrin Güloğlanzadə, I am writing from Goranboy. Suddenly I saw a strange wri
- `Baku` … --------------------- ⏎ Name: Gülnisə ⏎ Address: Baku city, Narimanov district, bui

**AGE — AGE with no gold overlap** (3)
- `74` … te of Birth: Wednesday, 14 October 1981 ⏎ Age: 74 ⏎ City: Kurdamir ⏎ Postal Code: A
- `35` … ess. ⏎  ⏎ Customer support note: ⏎ Customer age is 35. Payment completed. Contact w
- `81` … ynov has fallen here. That customer's age is 81. This is not related to your 

**ACCESS_TOKEN — ACCESS_TOKEN with no gold overlap** (3)
- `99rAmaNek6OtRYGJUJh7iAJCC` … n against me? ⏎ 4. How is the "key" parameter (99rAmaNek6OtRYGJUJh7iAJCC) in this link related to my p
- `CCfIjwfOJf9uALWA2bEd9dHo8wU54EYCwwVG` … r digital signature. The token starting with CCfIjwfOJf9uALWA2bEd9dHo8wU54EYCwwVG... ensures the security of yo
- `*` … digits of the card registered in our system: ****3873 ⏎    (Based on security 

**BUILDINGNUM — BUILDINGNUM with no gold overlap** (3)
- `4` … ullukhanim ⏎ Address: 38-ji Gala St., building 4 ⏎ Contact: 055 564 85-57 ⏎ E-mail
- `15` … s: Sumgait city, 2nd microdistrict, building 15. (Note: Address must be clari
- `122` … LLC ⏎ Address: Baku city, Heydar Aliyev avenue 122 ⏎ Contact person: Finance direc

**DATE — boundary (same label, other span)** (2)
- `Thursday, 16 May 1963` … Mahyaz ⏎ - Surname: Afandiyev ⏎ - Date of birth: Thursday, 16 May 1963 ⏎ - Residential address: Ibrahi
- `Wednesday, 14 October 1981` … Name, Surname: [Confidential] ⏎ Date of Birth: Wednesday, 14 October 1981 ⏎ Age: 74 ⏎ City: Kurdamir ⏎ Postal

**STREET — STREET with no gold overlap** (2)
- `Mushfiq Qafarov street` … rror): ⏎ - Balaxatin registration completed. ⏎ - Mushfiq Qafarov street address verified. ⏎  ⏎ Job respon
- `Heydar Aliyev avenue` … "Absheron Logistika" LLC ⏎ Address: Baku city, Heydar Aliyev avenue 122 ⏎ Contact person: Finance d

**STREET — boundary (same label, other span)** (2)
- `Link to` … Cavadxan, last warning! ⏎ * Link to beajh St. ⏎ * Debt: 150 AZN ⏎ Pay
- `beajh St.` … Cavadxan, last warning! ⏎ * Link to beajh St. ⏎ * Debt: 150 AZN ⏎ Payment is ov

**GIVENNAME — wrong type (gold SURNAME)** (2)
- `Gulli` … ect and Admin Tasks ⏎  ⏎ Attendees: ⏎ - Alijanov ⏎ - Gulli ⏎ - Irade (safiye_gulmalili@bak
- `Gulli` … w project's documents and technical aspects. Gulli said that the new contracts a

**TIME — TIME with no gold overlap** (2)
- `11:32 PM` … someone? I am in complete confusion... It is 11:32 PM and everywhere is very dark. 
- `04:08 AM` …  our system is a bit 'sleepy', because it is 04:08 AM right now. But I am checking 

**EMAIL — EMAIL with no gold overlap** (2)
- `info@baküenerji.az` … and confirmed. ⏎  ⏎ For any technical questions: info@baküenerji.az or +994 12 498 00 00. ⏎  ⏎ Seal a
- `destek@servis.az` … ever, the link you sent me still... ⏎  ⏎ > From: destek@servis.az ⏎ > Date: 11 October 2022 ⏎ > Sub

**AGE — MISSED gold** (2)
- `54` … er: Hello, I placed an order. ⏎ [12.05.2025 10:54] Agent: Hello, your order has
- `59` … IN;AGE ⏎ 9921;Məmmədhüseynov;ACTIVE;2025828269;59 ⏎  ⏎ Agent: You see, the informat

**CITY — MISSED gold** (2)
- `Sahil` … C OF AZERBAIJAN MINISTRY OF INTERNAL AFFAIRS ⏎ Sahil District Police Department ⏎ DE
- `Sahil` … manner with all relevant institutions by the Sahil District Police Department. L

**IPV4_ADDRESS — IPV4_ADDRESS with no gold overlap** (1)
- `100.22.14.01` … C0NF1RMED ⏎ M0DUL: TR4NSP0RT-V2 ⏎ Rout1ng_P0int: 100.22.14.01 ⏎ S0urce_N0de: AZ-SUM-01 ⏎  ⏎ [Syst

**GIVENNAME — MISSED gold** (1)
- `Zamiyla` … e their subscription status. ⏎  ⏎ Affected user: Zamiyla Lazimov ⏎ Contact email: bmeras

**BUILDINGNUM — MISSED gold** (1)
- `28` …       | Hyundai Tucson | ⏎ | Storage location| 28           | ⏎ | Status         

