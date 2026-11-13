# D-51h · New Azerbaijani text in the v4 targeted data: native check for the team

Every new sentence, phrase and key the v4 generator writes (`scripts/piigen/targeted/frames_v4.py`, new anchor phrases in `negatives.py`, new CSV keys in `formats.py`). `⟨value⟩` is where a value goes: a real one (masked) or a look-alike (left unmasked). Section 3 shows real documents from the 25,000-document build.

**Please mark** any sentence that reads unnatural or wrong, and give the fix. Sentences marked ⚑ are the ones I'd like a second look at.

## 1. Sentences (`frames_v4.py`)

### SHORT_BOTH[AZ_VOEN]

1. Formanın VÖEN sahəsində ⟨value⟩ göstərilib.
2. Hesab-fakturada VÖEN kimi ⟨value⟩ yazılıb.
3. Sorğuda vergi nömrəsi olaraq ⟨value⟩ daxil edilib.
4. Ərizədə şirkətin VÖEN-i ⟨value⟩ kimi qeyd olunub.
5. Müqavilənin rekvizitlərində VÖEN ⟨value⟩ olaraq əks olunub.

### SHORT_BOTH[AZ_FIN]

6. Ərizədə FİN kodu ⟨value⟩ kimi göstərilib.
7. Formanın FİN sahəsində ⟨value⟩ yazılıb.
8. Sistemdə FİN olaraq ⟨value⟩ daxil edilib.
9. Arayışda şəxsin FİN kodu ⟨value⟩ olaraq qeyd olunub.

### SHORT_BOTH[AZ_ID_CARD_NUMBER]

10. Ərizədə şəxsiyyət vəsiqəsinin nömrəsi ⟨value⟩ kimi göstərilib.
11. Formanın vəsiqə nömrəsi sahəsində ⟨value⟩ yazılıb.
12. Qeydiyyatda vəsiqə nömrəsi olaraq ⟨value⟩ daxil edilib.
13. Müqavilədə tərəfin şəxsiyyət vəsiqəsinin nömrəsi ⟨value⟩ kimi qeyd olunub.

### SHORT_BOTH[ACCESS_TOKEN]

14. Sorğunun başlığında token ⟨value⟩ kimi göstərilib.
15. Jurnalda sessiya tokeni olaraq ⟨value⟩ yazılıb.
16. Konfiqurasiyada giriş tokeni ⟨value⟩ kimi saxlanılır.

### SHORT_BOTH[API_KEY]

17. Konfiqurasiyada API açarı ⟨value⟩ kimi yazılıb.
18. İnteqrasiya sorğusunda API açarı olaraq ⟨value⟩ göndərilib.
19. Tərəfdaşın panelində API açarı ⟨value⟩ kimi göstərilib.

### SHORT_ONLY[AZ_VOEN]

20. Bu rüb həmin VÖEN ⟨value⟩ dəfə yoxlanılıb.
21. Vergi nömrəsi ⟨value⟩ saylı sorğu ilə yoxlanılıb.
22. Reyestrdə VÖEN ⟨value⟩ nömrəli sətirdə göstərilib.

### SHORT_ONLY[AZ_FIN]

23. FİN kodu ⟨value⟩ saylı müraciətdə tələb olunub.
24. Bu həftə FİN kodu ⟨value⟩ dəfə səhv daxil edilib.

### SHORT_ONLY[AZ_ID_CARD_NUMBER]

25. Şəxsiyyət vəsiqəsi ⟨value⟩ saylı arayışla birlikdə təqdim olunub.
26. Vəsiqə nömrəsi ⟨value⟩ saylı qovluqda saxlanılır.

### SHORT_ONLY[ACCESS_TOKEN]

27. Sessiya tokeni ⟨value⟩ simvoldan ibarətdir.
28. Bu gün token ⟨value⟩ dəfə yenilənib.
29. Hər istifadəçi üçün token ⟨value⟩ dəqiqə ərzində etibarlıdır.

### SHORT_ONLY[API_KEY]

30. Xidmətin API açarı ⟨value⟩ sorğudan sonra müvəqqəti bloklanır.
31. API açarı ⟨value⟩ gündən bir yenilənir.

### NAME_SLOT[SURNAME]

32. Anketdə soyad kimi ⟨value⟩ göstərilib.
33. Qeydiyyat formasında soyad olaraq ⟨value⟩ yazılıb.
34. Sistemin soyad sahəsində ⟨value⟩ qeyd olunub.
35. Müraciətdə soyad kimi ⟨value⟩ daxil edilib.
36. Siyahıda soyad olaraq ⟨value⟩ əks olunub.

### NAME_SLOT[CITY]

37. Anketdə şəhər kimi ⟨value⟩ göstərilib.
38. Qeydiyyat formasında şəhər olaraq ⟨value⟩ seçilib.
39. Ünvan blokunun şəhər sahəsində ⟨value⟩ yazılıb.
40. Sifarişdə şəhər kimi ⟨value⟩ qeyd olunub.

### NAME_SLOT[STREET]

41. Anketdə küçə kimi ⟨value⟩ göstərilib.
42. Çatdırılma formasında küçə olaraq ⟨value⟩ yazılıb.
43. Ünvanın küçə sahəsində ⟨value⟩ qeyd olunub.

### LOCATIVE[PAYMENT_CARD_NUMBER]

44. Ödəniş səhifəsində ⟨value⟩ görünür.
45. Müştərinin ödəniş profilində ⟨value⟩ saxlanılır.
46. Kart məlumatları bölməsində ⟨value⟩ əks olunub.
47. Hesab çıxarışında ⟨value⟩ göstərilib.
48. Mobil tətbiqin pul kisəsində ⟨value⟩ görünür.
49. Abunə parametrlərində ⟨value⟩ seçilib.
50. Sifariş formasında ⟨value⟩ qeyd olunub.
51. Ödəniş formasına ⟨value⟩ daxil edilib.

### LOCATIVE[AZ_VOEN]

52. Şirkət profilində ⟨value⟩ göstərilib.
53. Rekvizitlər cədvəlində ⟨value⟩ yazılıb.
54. Vergi bəyannaməsində ⟨value⟩ əks olunub.
55. Hesab-fakturanın başlığında ⟨value⟩ qeyd edilib.
56. Tender ərizəsində ⟨value⟩ göstərilib.
57. Dövlət reyestrindən çıxarışda ⟨value⟩ görünür.
58. Vergi uçotu kartında ⟨value⟩ qeyd olunub.

### LOCATIVE[AZ_ID_CARD_NUMBER]

59. Müraciət kartında ⟨value⟩ qeyd olunub.
60. Qonaqların qeydiyyat jurnalında ⟨value⟩ yazılıb.
61. Kredit ərizəsində ⟨value⟩ göstərilib.
62. Notariat aktında ⟨value⟩ əks olunub.
63. Bank anketində ⟨value⟩ daxil edilib.

### LOCATIVE[AZ_PASSPORT_NUMBER]

64. Bilet sifarişində ⟨value⟩ göstərilib.
65. Viza ərizəsində ⟨value⟩ yazılıb.
66. Sərnişin siyahısında ⟨value⟩ görünür.
67. Mehmanxananın qeydiyyat kartında ⟨value⟩ qeyd olunub.

### LOCATIVE[IBAN]

68. Ödəniş tapşırığında ⟨value⟩ göstərilib.
69. Müqavilənin bank rekvizitlərində ⟨value⟩ yazılıb.
70. Əmək haqqı cədvəlində ⟨value⟩ qeyd olunub.
71. Hesab-fakturanın sonunda ⟨value⟩ əks olunub.
72. Geri ödəniş ərizəsində ⟨value⟩ göstərilib.

### SLOT_PROSE[TIME]

73. Qəbul saatı ⟨value⟩ olaraq göstərilib.
74. Cədvəldə görüş vaxtı ⟨value⟩ kimi yazılıb.
75. Sistemdə növbənin başlama vaxtı ⟨value⟩ olaraq qeyd olunub.
76. Bildirişdə iclasın vaxtı ⟨value⟩ kimi göstərilib.

### SLOT_PROSE[AGE]

77. Anketdə müştərinin yaşı ⟨value⟩ kimi göstərilib.
78. Sistemdə pasiyentin yaşı ⟨value⟩ olaraq qeyd olunub.
79. Formada iştirakçının yaşı ⟨value⟩ kimi yazılıb.

### SLOT_PROSE[DATE]

80. Ərizədə doğum tarixi ⟨value⟩ kimi göstərilib.
81. Sistemdə müqavilənin tarixi ⟨value⟩ olaraq qeyd olunub.
82. Arayışda verilmə tarixi ⟨value⟩ kimi yazılıb.

### SLOT_PROSE[AZ_FIN]

83. Ərizəçinin FİN kodu ⟨value⟩ kimi göstərilib.
84. Sistemdə FİN ⟨value⟩ olaraq qeyd olunub.
85. Müraciətdə FİN kodu ⟨value⟩ kimi yazılıb.

### SLOT_PROSE[PAYMENT_CARD_NUMBER]

86. Ödəniş formasında kart nömrəsi ⟨value⟩ kimi daxil edilib.
87. Sifarişdə bank kartının nömrəsi ⟨value⟩ olaraq göstərilib.
88. Müştərinin kart nömrəsi ⟨value⟩ kimi qeyd olunub.

### PLACE_VERBS[cop]

89. Turnirin ev sahibi ⟨value⟩, oyunlar şəhərin yeni stadionunda keçiriləcək.
90. Bu layihənin əsas tərəfdaşı ⟨value⟩, şəhərin bələdiyyəsi maliyyəni öz üzərinə götürüb.
91. Ən çox darıxdığım şəhər ⟨value⟩, oranın küçələri yadımdan çıxmır.
92. Komandamızın əsas rəqibi ⟨value⟩, oranın klubu bu il çox güclüdür.

### PLACE_VERBS[ins]

93. Bu gün ⟨value⟩ danışdım, oradakı filial sənədləri sabah göndərəcək. ⚑ *a town with the instrumental (`Gəncəylə danışdım`): natural, or only with `ilə` separate?*
94. Mərkəzi ofis ⟨value⟩ əlaqə saxlayıb, şəhərin bələdiyyəsi cavab verib.
95. Biz ⟨value⟩ uzun müddətdir əməkdaşlıq edirik, oradakı zavod əsas təchizatçımızdır.
96. Səhər iclasında ⟨value⟩ videobağlantı quruldu, oranın nümayəndələri də qoşuldu.

### PLACE_VERBS[acc]

97. Uşaqlıqdan ⟨value⟩ çox sevirəm, oranın havası başqadır.
98. Keçən il ⟨value⟩ ilk dəfə gördüm və şəhərin küçələri xoşuma gəldi.
99. Biz ⟨value⟩ yaxşı tanıyırıq, orada uzun illər yaşamışıq.
100. Tələbələr ⟨value⟩ yaxından tanımaq üçün şəhərin muzeylərini gəziblər.

### PLACE_VERBS[abl]

101. ⟨value⟩ zəng etdilər, oradakı ofis sifarişi təsdiqləyib.
102. Səhər ⟨value⟩ xəbər gəldi ki, şəhərdə yollar təmir olunur.
103. ⟨value⟩ rəsmi məktub aldıq, oranın icra hakimiyyəti görüşə razılıq verib.
104. Bu həftə ⟨value⟩ çoxlu sifariş gəlib, oranın mağazaları yenidən açılıb.

### RECORD_INTROS

105. Yoxlama üçün sistemdən iki qeyd seçilib:
106. Müraciətlər bazasından çıxarış:
107. Operatorun yoxladığı qeydlər:
108. Arxivdən bərpa olunmuş qeydlər:
109. Düzəliş tələb olunan qeydlərin siyahısı:

### ROOM_CODE

110. Otaq kartında ⟨value⟩ kodu ilə göstərilən zal təmirdədir.
111. Mərtəbə planında ⟨value⟩ kodu iclas otağına aiddir.
112. Rezervasiya məlumatında ⟨value⟩ kodu ilə qeyd olunan otaq artıq tutulub.
113. Ofis sxemində ⟨value⟩ kodu altında arxiv otağı göstərilib.
114. Mehmanxana sistemində ⟨value⟩ kodu ilə yazılan otaq yenidən açılıb.
115. Təmir siyahısında ⟨value⟩ kodu ilə qeyd olunan otaqda kondisioner dəyişdirilib.

### DOOR_CODE

116. Anbarın girişində ⟨value⟩ qapı kodu istifadə olunur.
117. Server otağı üçün ⟨value⟩ qapı kodu təyin edilib.
118. Arxa giriş ⟨value⟩ qapı kodu ilə açılır.
119. Yeni əməkdaşlara ⟨value⟩ qapı kodu bildirilib.

### MAC_FRAGMENT

120. Şəbəkə jurnalında MAC ünvanı ⟨value⟩ ilə bitən cihaz qeydə alınıb.
121. MAC filtrində ⟨value⟩ prefiksi olan cihazlar bloklanıb.
122. Şəbəkə kartının MAC ünvanı ⟨value⟩ ilə başlayır.
123. Routerin siyahısında MAC ünvanının son hissəsi ⟨value⟩ kimi göstərilib.
124. Şəbəkə hesabatında istehsalçı prefiksi ⟨value⟩ olan qurğular ayrıca sayılıb.

### MAC_REAL

125. Cihazın MAC ünvanı ⟨value⟩ olaraq qeyd olunub.
126. Şəbəkə jurnalında MAC ünvanı ⟨value⟩ olan cihaz qeydə alınıb.
127. Routerin siyahısında MAC ünvanı ⟨value⟩ kimi göstərilib.
128. Şəbəkə kartının tam MAC ünvanı ⟨value⟩ kimi yazılıb.

### IBAN_FRAGMENT

129. Hesabın IBAN kodu ⟨value⟩ ilə başlayır.
130. Formanın IBAN sahəsinə yalnız ⟨value⟩ yazılıb, qalan hissə boş qalıb.
131. Müştəri hesab nömrəsinin əvvəlini ⟨value⟩ kimi bildirib.
132. Çıxarışda IBAN qısaldılmış formada ⟨value⟩ kimi göstərilib.

### IBAN_REAL

133. Formanın IBAN sahəsinə ⟨value⟩ yazılıb.
134. Ödəniş ⟨value⟩ hesabına köçürülüb.
135. Müştərinin IBAN-ı ⟨value⟩ kimi qeyd olunub.
136. Çıxarışda hesab nömrəsi ⟨value⟩ olaraq göstərilib.

### IPV4_BOTH

137. Sorğu qeydində IP ünvanı ⟨value⟩ kimi yazılıb.
138. Formanın IP sahəsində ⟨value⟩ göstərilib.
139. Jurnalda mənbə IP ünvanı olaraq ⟨value⟩ qeyd olunub.
140. Hesabatda serverin IP ünvanı ⟨value⟩ kimi əks olunub.

### IPV4_PLACEHOLDER

141. Təlimatda IP ünvanı kimi ⟨value⟩ şablonu verilib.
142. Nümunə konfiqurasiyada IP ünvanı yerinə ⟨value⟩ yazılıb.

### ZIP_RIGHT

143. Qaimədə indeks kimi ⟨value⟩⟨ məhsul kodu⟩ göstərilib. ⚑ *with the tail: `indeks kimi 4821 məhsul kodu` -- does `indeks kimi` + a product code read as a contradiction?*
144. Bağlamanın etiketində indeks olaraq ⟨value⟩⟨ məhsul kodu⟩ yazılıb.
145. Sənəddə poçt indeksi kimi ⟨value⟩⟨ məhsul kodu⟩ qeyd olunub.
146. Sifariş formasının indeks sahəsində ⟨value⟩⟨ məhsul kodu⟩ göstərilib.

### SURNAME_ABLATIVE

147. ⟨value⟩ zəng gəldi, sənədləri sabah gətirəcəyini bildirdi.
148. Dünən ⟨value⟩ məktub aldım, o, iclasa gələ bilməyəcəyini yazıb.
149. Müdir ⟨value⟩ hesabatı tələb edib, o isə sabaha qədər vaxt istəyib.
150. ⟨value⟩ cavab gözləyirik, o, sənədləri hələ imzalamayıb.

### CONTROL_DEPARTMENTS

151. Maliyyə şöbəsi
152. Hüquqi təminat şöbəsi
153. Kadrlar şöbəsi
154. Təchizat bölməsi
155. Mətbuat xidməti
156. Ümumi şöbə
157. Texniki xidmət bölməsi
158. Mühasibatlıq
159. Arxiv bölməsi
160. Kargüzarlıq şöbəsi

### CONTROL_POSITIONS

161. Baş mühasib
162. Şöbə müdiri
163. Aparıcı mütəxəssis
164. Baş məsləhətçi
165. Kargüzar
166. Hüquqşünas
167. Sistem inzibatçısı
168. Layihə rəhbəri

### CONTROL_DOCUMENTS

169. Ərizə forması
170. Kollektiv müqavilə
171. Daxili nizamnamə
172. İllik hesabat
173. Vəzifə təlimatı
174. Hesabat forması
175. Ezamiyyə vərəqəsi

### CONTROL_ORGS

176. «Mərkəzi Anbar» MMC
177. «Mərkəzi Tikinti» ASC
178. «Birlik Servis» MMC
179. «Təmiz Su» MMC
180. «Etibarlı Yol» ASC
181. «Cənub Logistika» MMC

### ROLE_CONTROL_SENTENCES

182. İclasda müdir **Maliyyə Şöbəsinin** illik hesabatını təqdim edib. ⚑ *role word right before a department in the genitive: word order natural?*
183. Layihəyə rəis **Texniki Xidmət Bölməsi** ilə birlikdə nəzarət edir.
184. Sənədləri katib **Ümumi Şöbədən** alıb.
185. Toplantıda nümayəndə **İctimai Şuranın** mövqeyini açıqlayıb.
186. Məlumatı mühasib **Mərkəzi Anbarın** qaimələrinə əsasən hazırlayıb.
187. Təklifi direktor **Müşahidə Şurasına** təqdim edib.
188. Müqaviləni vəkil **Hüquqi Təminat Departamentinin** adından imzalayıb.
189. Qərarı sədr **Direktorlar Şurasının** iclasında elan edib.

### SIGNATURE_ONLY_TITLES

190. Direktor
191. Baş mühasib
192. Komissiya katibliyi
193. Şöbə müdiri
194. Kadrlar şöbəsi
195. Mətbuat xidməti
196. Müştəri xidmətləri

### ADDRESSEE

197. Hörmətli {g} {s},
198. Hörmətli {g} {h},

### KEY_SET_INTROS

199. Repozitoriyanın yoxlanışı zamanı bir neçə şəxsi açar tapılıb.
200. Test serverinin konfiqurasiya qovluğunda aşağıdakı açarlar saxlanılır.
201. Tərtibatçılar açarları iş yazışmasında paylaşıb.
202. Köhnə deploy skriptlərində aşağıdakı açarlar aşkarlanıb.
203. Təhlükəsizlik auditində tapılan açarlar aşağıda verilib.

### RECORD_HEADS

204. Birinci qeyd: / İkinci qeyd:
205. Birinci müraciət: / İkinci müraciət:
206. Əvvəlki versiya: / Yenilənmiş versiya:
207. Köhnə qeyd: / Yeni qeyd:

### RECORD_STATUS

208. təsdiqlənib
209. yoxlanılır
210. natamam
211. gözləmədə
212. düzəliş tələb olunur

### ZIP_TAILS

213. məhsul kodu
214. anbar kodu
215. partiya kodu

### CONTROL_LISTS

216. Komissiyanın işinə cəlb olunan qurumlar:
217. Müsabiqəyə təqdim olunmalı sənədlər:
218. Ştat cədvəlinə əlavə edilən vəzifələr:
219. İclasda hesabat verəcək struktur bölmələr:

## 2. Short phrases and keys

Anchor phrases of the new look-alike kinds (`negatives.py`), used inside other sentences:

220. `room_code` (CARD_SECURITY_CODE): otağın kodu ⟨value⟩ · ⟨value⟩ kodlu otaq · kabinetin kodu ⟨value⟩
221. `door_code` (CARD_SECURITY_CODE): ⟨value⟩ qapı kodu · qapının kodu ⟨value⟩ · giriş qapısının kodu ⟨value⟩
222. `fin_short_number` (AZ_FIN): FİN kodu ⟨value⟩ · FİN: ⟨value⟩ · şəxsiyyət vəsiqəsinin FİN kodu ⟨value⟩
223. `voen_short_number` (AZ_VOEN): VÖEN ⟨value⟩ · VÖEN: ⟨value⟩ · VÖEN nömrəsi ⟨value⟩ · vergi nömrəsi ⟨value⟩
224. `id_card_short_number` (AZ_ID_CARD_NUMBER): şəxsiyyət vəsiqəsinin nömrəsi ⟨value⟩ · vəsiqə nömrəsi ⟨value⟩ · şəxsiyyət vəsiqəsi: ⟨value⟩ · sənədin nömrəsi ⟨value⟩
225. `ipv4_short_over_255` (IPV4_ADDRESS): IP ünvanı ⟨value⟩ · server IP: ⟨value⟩ · mənbə IP ⟨value⟩
226. `ipv4_three_octets` (IPV4_ADDRESS): IP ünvanı ⟨value⟩ · server IP: ⟨value⟩ · mənbə IP ⟨value⟩
227. `ipv4_placeholder` (IPV4_ADDRESS): IP ünvanı ⟨value⟩ · server IP: ⟨value⟩ · mənbə IP ⟨value⟩ · IP ünvanı şablonu ⟨value⟩
228. `mac_fragment_dashed` (MAC_ADDRESS): MAC ünvanı ⟨value⟩ · cihazın MAC ünvanı ⟨value⟩ · MAC: ⟨value⟩
229. `card_wrong_length` (PAYMENT_CARD_NUMBER): kart nömrəsi ⟨value⟩ · bank kartının nömrəsi ⟨value⟩ · kart: ⟨value⟩
230. `iban_fragment_short` (IBAN): IBAN ⟨value⟩ · hesab nömrəsi (IBAN) ⟨value⟩
231. `api_key_short_number` (API_KEY): API açarı ⟨value⟩ · api key: ⟨value⟩ · inteqrasiya açarı ⟨value⟩
232. `token_short_number` (ACCESS_TOKEN): token ⟨value⟩ · token: ⟨value⟩ · sessiya tokeni ⟨value⟩
233. `code_in_name_slot` (SURNAME): ⟨value⟩ kodu · layihə kodu ⟨value⟩ · məhsul kodu ⟨value⟩
234. New snake_case keys in CSV/JSON/log/config: `şəxsiyyət_vəsiqəsi`, `sürücülük_vəsiqəsi`
235. D-51i: a spelled date before `tarixində` now ends `… 2016-cı il tarixində` (`-cı/-ci/-cu/-cü` by the year's last spoken word, as you confirmed for numbers); the date span stops at the year

## 3. Examples from the build (one per family; the masked values in **bold**, look-alikes in _italics_)

**cross_anchor/short_number** (`targeted_az_008888`)

> Məlumat bazasından seçilmiş sətirlər:
> fin_kodu,status
> **JFV0H6C**,gözləmədə
> **K3JL0T1**,gözləmədə
> _131_,təsdiqlənib
> Jurnal faylları arxivə köçürülüb.

**cross_anchor/name_org** (`targeted_az_000510`)

> Qeydiyyat formasında soyad olaraq **Kəngərli** yazılıb. Sənədin surətində isə başqa məlumat var. Qeydiyyat formasında soyad olaraq _GCY256_ yazılıb.

**cross_anchor/room_code** (`targeted_az_018510`)

> Zəhmət olmasa, cavabımızı gözləyin. Ödəniş zamanı CVV kodu **052** olaraq daxil edilib. Mərtəbə planında _514_ kodu iclas otağına aiddir.

**cross_anchor/zip_code** (`targeted_az_001612`)

> Cavab göndərilib. Sənəddə poçt indeksi kimi _AZ5416_ partiya kodu qeyd olunub. Əməkdaş hər iki qeydi yoxlayıb. Sənəddə poçt indeksi kimi **AZ1574** qeyd olunub. Sorğu növbəyə salınıb.

**cross_anchor/mac_fragment** (`targeted_az_006363`)

> Zəhmət olmasa, əlavə sənədləri e-poçt vasitəsilə göndərin. Şəbəkə kartının tam MAC ünvanı **70:85:c2:4c:93:87** kimi yazılıb. Sonradan məlumat dəqiqləşdirilib.
> Şəbəkə hesabatında istehsalçı prefiksi _41-47-42_ olan qurğular ayrıca sayılıb. Suallarınızı dəstək xidmətinə ünvanlaya bilərsiniz.

**cross_anchor/iban_fragment** (`targeted_az_008412`)

> Formanın IBAN sahəsinə **AZ49 AYZP 7911 7260 3217 9565 1840** yazılıb. Sinxronizasiya bir neçə dəqiqə çəkə bilər. Çıxarışda IBAN qısaldılmış formada _AZ55HVZ_ kimi göstərilib.

**cross_anchor/ipv4** (`targeted_az_000665`)

> Hesabatda serverin IP ünvanı _5.0.1.751_ kimi əks olunub.
> Sistemdə ikinci qeyd də mövcuddur. Hesabatda serverin IP ünvanı **48.83.216.16** kimi əks olunub.

**locative** (`targeted_az_001730`)

> Hörmətli həmkarlar, məlumat üçün bildiririk ki, iclas təxirə salınıb. Viza ərizəsində **S97903256** yazılıb. Müraciətinizlə bağlı işlər davam etdirilir. Viza ərizəsində _H1687238_ yazılıb. Xidmətimizin keyfiyyətini artırmaq üçün rəyinizi gözləyirik.

**slot_invalid** (`targeted_az_006040`)

> Formada iştirakçının yaşı **29** kimi yazılıb.
> Sonradan məlumat dəqiqləşdirilib. Formada iştirakçının yaşı _-22_ kimi yazılıb.
> Hörmətli həmkarlar, məlumat üçün bildiririk ki, iclas təxirə salınıb.

**place_verbs** (`targeted_az_021930`)

> Turnirin ev sahibi **Bakidir**, oyunlar şəhərin yeni stadionunda keçiriləcək.
> **Malluhidən** cavab gözləyirik, o, sənədləri hələ imzalamayıb.

**short_keys** (`targeted_az_017931`)

> Repozitoriyanın yoxlanışı zamanı bir neçə şəxsi açar tapılıb.
> Tikətə əlavə olunan açar **-----BEGIN PRIVATE KEY----- MC4CAQAwBQYDK2VwBCIEIfuY0LPCKYQQB9JqxvyOSZYXv3vBM1oioGTvgBnTD6+l -----END PRIVATE KEY-----** Açar dərhal ləğv edilməlidir.
> Tərtibatçı bu açarı yazışmada paylaşıb: "**-----BEGIN PRIVATE KEY-----
> MC4CAQAwBQYDK2VwBCIEILM3qKIClqUM31Q8FqlnHNDFKba5LYW7PZ0RORD9WiTv
> -----END PRIVATE KEY-----**".

**namelist with controls** (`targeted_az_009716`)

> Müsabiqədə iştirak üçün qeydiyyatdan keçmiş şəxslərin siyahısı:
> **Nurvinova** **Hubeyda** **Heybətalı** qızı
> **Əsədağayev** **Dalğıc** **Döyüş** oğlu
> _Hüquqşünas_ (vakant)
> Komissiyanın işinə cəlb olunan qurumlar:
> _«Mərkəzi Anbar» MMC_
> _Mühasibatlıq_
> _Arxiv bölməsi_
> Əlavə məlumat almaq istəyənlər müvafiq şöbəyə müraciət edə bilər.

**namelist with controls** (`targeted_az_006286`)

> Hörmətli **Nuşi** bəy,
> Müvafiq komissiya sənədlərə yenidən baxıb. 
> Hörmətlə,
> _Baş mühasib_

