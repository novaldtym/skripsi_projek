# TANGGAPAN AHLI A — PUTARAN KE-3
## Audit Lanjutan terhadap Pembuktian Empiris Peneliti B

**Judul Penelitian**

> **Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi**

**Peran**
- Ahli A: Auditor metodologi dan penelaah kritis
- Peneliti B: Perancang/pengembang sistem
- Dokumen ini: Tanggapan putaran ketiga setelah Peneliti B memberikan bukti empiris, tabel evaluasi, split dataset, pembandingan 44 vs 57 fitur, benchmark model, dan walkthrough kausalitas fitur.

---

# 1. PUTUSAN UMUM

Putaran kedua Peneliti B jauh lebih kuat daripada dua respons sebelumnya karena sudah memberikan:

- pembagian train/validation/test;
- jumlah observasi;
- rentang waktu;
- kurva threshold validation dan test;
- koreksi terhadap angka 73,97%;
- eksperimen 44 vs 57 fitur;
- pembuktian timestamp untuk Order Block;
- bukti causalitas RRR/Clearance;
- benchmark LightGBM vs XGBoost vs Random Forest vs Logistic Regression;
- penjelasan MTF, DXY, macro dan frozen model.

Karena sekarang sudah tersedia bukti empiris, standar audit juga harus dinaikkan.

## Status saya sekarang

> **CONDITIONAL APPROVAL — BELUM FINAL**

Penelitian sudah cukup kuat untuk dilanjutkan, tetapi masih ada beberapa isu yang harus dibereskan sebelum angka dan klaim tersebut dianggap final untuk skripsi.

Prioritas tertinggi yang muncul dari audit putaran ini:

1. memastikan seluruh boundary split tidak terkena overlap target (*purge/embargo*);
2. menjelaskan secara formal mengapa threshold 65% dipilih;
3. menafsirkan hasil 44 vs 57 secara jujur;
4. tidak menyebut 57,81% sebagai “edge sangat kokoh” tanpa uji robustness/significance yang tepat;
5. membuat baseline probabilitas untuk Log Loss/Brier;
6. memastikan klaim “LightGBM terbaik” sesuai dengan metrik yang sebenarnya;
7. memeriksa unit dan makna konstanta `0.0018`;
8. memisahkan kontribusi pure ML dari filter/risk engine pada forward testing.

---

# 2. TEMUAN PALING PENTING: ANGKA 73,97% HARUS DIHAPUS DARI HASIL FINAL

Peneliti B mengakui bahwa angka 73,97% berasal dari evaluasi lama yang masih menggunakan:

```python
shift(-2)
```

pada fitur Order Block.

Artinya angka tersebut terkontaminasi *lookahead bias*.

## Putusan Ahli A

### 73,97% LAMA = TIDAK SAH SEBAGAI HASIL FINAL

Angka tersebut tidak boleh lagi digunakan sebagai:

- bukti utama performa;
- bukti calibration;
- bukti edge;
- klaim novelty;
- kesimpulan;
- angka pada abstrak;
- angka pada slide sidang.

Hasil baru yang seharusnya menjadi rujukan adalah hasil **57 fitur kausal** pada independent test set.

---

# 3. HASIL FINAL YANG SAAT INI LEBIH LAYAK DIGUNAKAN

B memberikan hasil:

- 7.455 bar independent test;
- threshold >=65%;
- 474 sinyal;
- coverage 6,36%;
- directional accuracy 57,81%.

Ini jauh lebih kredibel daripada 73,97% yang ternyata berasal dari data leakage.

## Argumen Ahli A

Saya justru lebih menyukai hasil 57,81% yang jujur.

Dalam penelitian finansial, hasil yang lebih rendah tetapi bebas leakage jauh lebih bernilai daripada angka tinggi yang ternyata tidak valid.

Narasi penelitian sebaiknya berubah dari:

> “Model memiliki akurasi sangat tinggi.”

menjadi:

> “Model menunjukkan peningkatan directional accuracy pada subset prediksi dengan confidence tinggi, meskipun akurasi keseluruhan tetap dekat dengan tingkat acak.”

Itu lebih realistis dan lebih kuat secara ilmiah.

---

# 4. 57,81% JANGAN DISEBUT “STATISTICAL EDGE YANG SANGAT KOKOH”

Peneliti B sebelumnya menyebut:

> 57,81% sebagai statistical edge yang sangat kokoh dan realistis.

Saya menolak kata **“sangat kokoh”**.

Mengapa?

Karena angka 57,81% berasal dari hanya:

> 474 sinyal

dari:

> 7.455 observasi test

atau coverage:

> 6,36%.

Kalau secara sederhana diperlakukan sebagai Bernoulli independen, proporsinya memang berada di atas 50%. Namun data financial time series bukan sekumpulan observasi independen sempurna.

Ada kemungkinan:

- autocorrelation;
- clustering;
- overlapping horizon;
- market regime dependency.

Karena target memakai horizon 5 candle:

```text
Y_t = Close(t+5) > Close(t)
```

maka observasi target antar-candle dapat saling tumpang tindih.

## Formulasi yang lebih aman

> **“Hasil pengujian menunjukkan adanya indikasi predictive edge pada subset sinyal dengan confidence tinggi.”**

Bukan:

> “membuktikan statistical edge yang sangat kokoh.”

---

# 5. PERMASALAHAN BARU: OVERLAPPING LABEL PADA TIME SERIES

Ini salah satu isu yang sekarang justru menjadi sangat penting.

Target:

```text
Y_t = Close(t+5) > Close(t)
```

berarti:

```text
Y_t     memakai Close(t+5)
Y_t+1   memakai Close(t+6)
Y_t+2   memakai Close(t+7)
...
```

Target antar-observasi saling overlap.

Ini berarti asumsi observasi independen sangat lemah.

## Implikasi

Kalau B menggunakan:

- simple binomial significance test;
- standard confidence interval biasa;
- standard random sampling assumptions;

maka hasil signifikansi dapat terlalu optimistis.

## Saran Ahli A

Jika ingin menyebut statistical significance, gunakan pendekatan yang memperhitungkan dependence, misalnya:

- block bootstrap;
- time-series bootstrap;
- atau minimal analisis stabilitas per blok waktu.

Tidak harus menjadikan ini eksperimen utama skripsi, tetapi klaim statistik harus disesuaikan dengan struktur data.

---

# 6. MASALAH PALING PENTING BERIKUTNYA: PURGE 5 CANDLE PADA BOUNDARY SPLIT

B membagi:

```text
Train      70%
Validation 15%
Test       15%
```

Ini secara kronologis sudah benar.

Namun target membutuhkan:

> lima candle setelah waktu prediksi.

Misalnya observasi terakhir Train berada di t:

```text
X_t
Y_t = Close(t+5) > Close(t)
```

maka label tersebut memerlukan data sampai t+5.

Kalau t+1 ... t+5 berada di Validation, maka boundary train/validation mengandung overlap target.

Hal serupa terjadi pada Validation/Test.

## Saya meminta B melakukan:

### Purge = 5 candle

di masing-masing boundary.

Konsep:

```text
TRAIN
████████████████
[PURGE 5 CANDLE]
VALIDATION
██████████
[PURGE 5 CANDLE]
TEST
██████████
```

Tujuannya memastikan:

> tidak ada satu label target pada satu split yang memerlukan data harga yang berada di split berikutnya.

## Status

> **INI ADALAH AUDIT PRIORITAS TERTINGGI YANG BELUM TERJAWAB.**

---

# 7. 65%: SEKARANG SAYA MEMPERTANYAKAN PEMILIHAN THRESHOLD LEBIH KERAS

Kurva validation yang diberikan B:

| Threshold | Accuracy Validation | Coverage Validation |
|---:|---:|---:|
| >=50% | 51,01% | 100% |
| >=52% | 51,12% | 82,00% |
| >=55% | 51,72% | 57,01% |
| >=58% | 53,21% | 37,36% |
| >=60% | 52,52% | 28,17% |
| >=63% | 51,38% | 17,49% |
| >=65% | 51,43% | 12,62% |
| >=68% | 51,71% | 7,47% |
| >=70% | 53,93% | 4,95% |
| >=75% | 57,89% | 1,78% |

Data ini justru membuat saya bertanya:

> Mengapa 65% dipilih?

Karena pada validation:

- 70% memiliki accuracy lebih tinggi;
- 75% memiliki accuracy paling tinggi;
- 65% memiliki coverage lebih besar.

Jadi “kompromi” harus punya definisi formal.

---

# 8. CARA MEMBENARKAN 65% SECARA ILMIAH

Ada beberapa cara yang sah.

## Opsi A — A priori

65% memang ditetapkan dari awal karena desain penelitian.

Kalimat:

> “Threshold 65% ditetapkan sebelum evaluasi independent test sebagai aturan selective prediction.”

Ini sangat sederhana.

## Opsi B — Validation optimization dengan constraint

Misalnya:

> pilih threshold yang memaksimalkan accuracy dengan coverage >=10%.

Maka:

- 65% = coverage 12,62% → memenuhi;
- 68% = 7,47% → tidak memenuhi;
- 70% = 4,95% → tidak memenuhi;
- 75% = 1,78% → tidak memenuhi.

Maka 65% memiliki dasar formal.

## Opsi C — Objective trade-off

Bisa dibuat fungsi:

```text
Score(theta) =
Accuracy(theta) × Coverage(theta)^alpha
```

dengan alpha ditentukan sebelum eksperimen.

Namun untuk skripsi S1, ini mungkin terlalu rumit.

### Rekomendasi Ahli A

Gunakan **Opsi A atau B**.

Jangan lagi menggunakan istilah:

> “65% adalah threshold terbaik.”

Gunakan:

> **“Threshold 65% dipilih berdasarkan aturan selective prediction yang telah ditetapkan pada validation set, dengan mempertimbangkan keseimbangan antara directional accuracy dan coverage.”**

---

# 9. 44 VS 57: HASIL SUDAH CUKUP MENARIK, TETAPI JANGAN OVERCLAIM

B memberikan:

## Validation

### 44
- AUC 0,5093
- Log Loss 0,7033
- Brier 0,2549
- selective accuracy 56,67%
- coverage 7,24%

### 57
- AUC 0,5160
- Log Loss 0,7084
- Brier 0,2570
- selective accuracy 51,43%
- coverage 12,62%

## Independent Test

### 44
- AUC 0,5083
- Log Loss 0,7043
- Brier 0,2553
- selective accuracy 50,39%
- coverage 5,11%

### 57
- AUC 0,5202
- Log Loss 0,7016
- Brier 0,2540
- selective accuracy 57,81%
- coverage 6,36%

## Interpretasi Ahli A

### Validation:
57 tidak menang pada semua metrik.

Justru:

- Log Loss lebih buruk;
- Brier lebih buruk;
- selective accuracy lebih rendah.

### Test:
57 menang pada seluruh metrik yang dilaporkan.

Jadi kesimpulan yang saya terima:

> **“Pada independent test set, konfigurasi 57 fitur memberikan performa yang lebih baik daripada konfigurasi 44 fitur pada metrik yang dilaporkan.”**

Yang saya tolak:

> “57 fitur terbukti selalu lebih baik.”

Karena validation belum mendukung klaim yang universal.

---

# 10. PERTANYAAN LEBIH DALAM: APAKAH 57 FITUR STABIL?

Karena test set hanya satu blok periode waktu:

> 11 Juni 2026 s/d 2 Oktober 2026

kita belum tahu apakah keunggulan 57 fitur terjadi secara konsisten.

Bisa jadi:

> 57 lebih cocok untuk regime Juni–Oktober 2026.

## Saran

Pecah independent test menjadi beberapa blok waktu:

- Block 1;
- Block 2;
- Block 3;
- Block 4.

Kemudian hitung:

- AUC;
- accuracy;
- selective accuracy;
- coverage.

Tujuannya bukan membuat penelitian baru.

Tujuannya menjawab:

> **apakah improvement 57 fitur stabil lintas waktu?**

---

# 11. BASELINE PROBABILITAS HARUS DIPERJELAS

LightGBM 57 test:

- AUC 0,5202
- Log Loss 0,7016
- Brier 0,2540

Ini berarti overall predictive strength masih sangat dekat dengan random.

Saya ingin ada baseline sederhana:

## Baseline 50/50

```text
P(UP)   = 0,5
P(DOWN) = 0,5
```

dan jika kelas tidak 50/50:

## Baseline class-prior

```text
P(UP) = proporsi UP pada train
P(DOWN) = proporsi DOWN pada train
```

Kemudian bandingkan:

- Log Loss;
- Brier.

Baru bisa dijawab:

> apakah probability output model memang lebih informatif daripada predictor sederhana?

---

# 12. JANGAN MENYATAKAN LIGHTGBM “TERBAIK” DI SEMUA HAL

Benchmark B:

| Model | AUC | Log Loss | Brier | Selective Accuracy |
|---|---:|---:|---:|---:|
| LightGBM | **0,5202** | 0,7016 | 0,2540 | 57,81% |
| XGBoost | 0,5199 | 0,7085 | 0,2573 | 50,66% |
| RF | 0,5136 | **0,6941** | **0,2505** | 60,00%* |
| Logistic | 0,5139 | **0,6956** | **0,2512** | 0,00%* |

## Analisis Ahli A

LightGBM:

- AUC tertinggi;
- selective accuracy cukup baik;
- menghasilkan cukup banyak high-confidence signals.

Tetapi:

- bukan Log Loss terendah;
- bukan Brier terendah.

RF punya 60% selective accuracy, tetapi hanya dari:

> **5 sinyal.**

Itu terlalu kecil untuk dijadikan klaim superioritas.

### Jadi definisi “terbaik” harus dipersempit:

> **LightGBM memiliki discrimination terbaik menurut ROC-AUC dan menghasilkan selective high-confidence signals yang lebih usable dibandingkan comparator pada threshold yang digunakan.**

Bukan:

> “LightGBM paling baik dalam seluruh aspek probabilitas.”

---

# 13. SAYA MENYARANKAN MATCHED-COVERAGE COMPARISON

Threshold 65% menghasilkan coverage berbeda untuk tiap model.

Itu membuat comparison tidak sepenuhnya apple-to-apple.

Tambahkan analisis opsional:

> **Top-k% confidence comparison**

Misalnya semua model dipaksa memberikan:

> top 6% observasi dengan confidence tertinggi.

Kemudian bandingkan:

- accuracy;
- precision;
- F1.

Ini akan menjawab:

> “Jika semua model diberi jumlah peluang yang sama, siapa yang memilih peluang lebih baik?”

Tidak wajib menjadi eksperimen utama, tetapi sangat bagus sebagai robustness check.

---

# 14. AUDIT UNIT `0.0018`: INI MASALAH NYATA

B menulis:

> 0,0018 × 4150 ≈ $0,74.

Ini secara aritmatika tidak benar.

```text
0,0018 × 4150 = 7,47
```

Bukan:

> 0,74.

Jadi saya meminta B mengaudit ulang:

- apakah `0.0018` adalah percentage ratio;
- apakah seharusnya `0.00018`;
- apakah satuannya point/pip;
- apakah harga XAUUSD menggunakan skala tertentu;
- apa sebenarnya arti 18 points/7,4 points.

## Ini penting karena:

`Nearest_Clearance` menggunakan:

```python
min(Dist_Support, Dist_Resistance) - 0.0018
```

Maka kesalahan unit akan langsung memengaruhi fitur model.

---

# 15. KLAIM “0.0018 = SPREAD + KOMISI + SLIPPAGE” JUGA HARUS DIBUKTIKAN

Kalau 0,0018 adalah konstanta tetap, lebih aman menyebutnya:

> **fixed execution-friction buffer**

daripada menyebutnya:

> “rata-rata spread + commission + slippage”

kecuali tersedia data historis aktual yang mendasari konstanta itu.

Karena spread:

- dinamis;
- tergantung jam;
- tergantung volatilitas;
- tergantung kondisi broker.

---

# 16. FORWARD TESTING HARUS DIPISAHKAN DARI KEMAMPUAN PREDIKSI

B menyebut win rate 64,8%–74,8% di akun riil sebagai hasil dari:

> Dynamic ATR SL/TP + BEP + filter.

Saya tidak menolak hasilnya.

Tetapi kata:

> **“berkat”**

harus hati-hati.

Karena manajemen risiko dapat meningkatkan:

- trade outcome;
- loss containment;
- profit factor;
- drawdown.

Tetapi itu bukan bukti bahwa:

> **model ML menjadi lebih pintar.**

---

# 17. SAYA SARANKAN MEMBUAT TIGA LAPIS EVALUASI

Ini menurut saya akan menjadi salah satu struktur Bab IV terbaik.

## Layer 1 — Pure ML

```text
LightGBM probability
↓
confidence >=65
↓
directional outcome
```

Metric:

- Accuracy;
- Precision;
- Recall;
- F1;
- AUC;
- Log Loss;
- Brier.

## Layer 2 — ML + Structural Filter

Tambahkan:

- trend;
- clearance;
- structural RRR;
- S/R.

Metric:

- accuracy;
- coverage;
- win rate.

## Layer 3 — Full Execution

Tambahkan:

- ATR SL;
- TP;
- BEP;
- trailing;
- spread constraints.

Metric:

- Win Rate;
- Profit Factor;
- Drawdown;
- ROI.

Dengan begitu benar-benar terlihat:

> bagian mana yang meningkatkan predictive performance dan bagian mana yang meningkatkan trading outcome.

---

# 18. BEP DAN PROFIT FACTOR

B menyatakan:

> Profit Factor = Gross Profit termasuk BEP / Gross Loss.

Ini boleh secara matematika **hanya jika BEP benar-benar net positive**.

Jika +$0,20 belum dikurangi biaya transaksi, maka ia belum tentu profit bersih.

Saya menyarankan:

> gunakan **Net PnL setelah biaya**

dan tetap beri label operasional:

- WIN;
- BEP;
- LOSS.

---

# 19. FROZEN MODEL: DITERIMA

Saya menerima penuh keputusan:

```text
Train
↓
Tune
↓
Validate
↓
Freeze
↓
Test
↓
Forward Test
```

Tidak ada:

- retraining;
- perubahan hyperparameter;
- perubahan threshold.

Ini sangat baik untuk validitas eksperimen.

---

# 20. OB DAN FVG: STATUS AUDIT

## Order Block

Walkthrough B:

```text
10:00 → candle acuan bearish
10:15 → belum ada displacement
10:30 → displacement terkonfirmasi
```

dan:

```text
OB_Bull_t = f(Candle(t-2), Candle(t))
```

saya terima secara konsep.

## FVG

```text
FVG_Bull_t = Low_t > High_t-2
```

juga causal.

### Tetapi:

Untuk FVG saya masih ingin implementasi state yang lebih lengkap bila fitur tersebut menyebut:

- active;
- mitigated;
- filled;
- invalid.

Semua status tersebut harus dihitung sampai t, bukan dari outcome masa depan.

---

# 21. MTF: SAYA TERIMA, TETAPI FFILL TETAP HARUS DIAUDIT

H1/H4 yang menggunakan closed candle dan shift satu periode saya terima.

Tetapi tetap perlu dijawab:

> berapa lama nilai H1/H4 boleh di-forward-fill?

Causal tidak otomatis berarti informasi selalu relevan.

---

# 22. DXY: MAXIMUM STALE DURATION BAGUS, TETAPI HARUS KONSISTEN

B sekarang menetapkan:

> maksimum stale 1 jam.

Ini jauh lebih baik daripada forward-fill tanpa batas.

Tetapi harus ada penjelasan:

> mengapa 1 jam?

Apakah:

- threshold teknis;
- berdasarkan market overlap;
- berdasarkan karakteristik dataset?

Tidak harus kompleks, tetapi harus dijelaskan.

---

# 23. MACRO: METODOLOGI SUDAH CUKUP KUAT

Saya menerima:

- NFP Week;
- CPI Day;
- FOMC Week;

selama hanya memakai schedule yang tersedia sebelum rilis.

Saya setuju bahwa tidak menggunakan actual release value membantu mencegah post-event leakage.

---

# 24. INTERPRETASI CONFIDENCE

Definisi:

```text
Confidence = max(P(Up), 1-P(Up))
```

boleh.

Tetapi jangan mengatakan confidence:

> “mengukur jarak data dari decision boundary.”

Lebih aman:

> **confidence adalah probabilitas kelas tertinggi yang diberikan model.**

Dan:

> confidence bukan otomatis probabilitas profit.

---

# 25. SELECTIVE CLASSIFICATION ADALAH KONSEP YANG MENURUT SAYA PALING KUAT

Setelah angka final 57,81%, saya justru berpikir bahwa penelitianmu lebih menarik bila diposisikan sebagai:

> **selective prediction dengan reject option**

bukan:

> “model harus akurat pada setiap candle.”

Karena:

```text
Low confidence
→ abstain
```

dan:

```text
High confidence
→ signal candidate
```

Ini sangat masuk akal untuk pasar yang noisy.

---

# 26. COVERAGE 6,36% BUKAN OTOMATIS BURUK

Bisa saja coverage 6,36% masih berguna.

Pertanyaan yang lebih penting:

> Berapa rata-rata sinyal per hari?

Contoh:

```text
0,2 signal/day
```

mungkin terlalu sedikit.

Sedangkan:

```text
2–3 signal/day
```

masih sangat mungkin berguna.

Jadi B perlu menghitung:

> average signals/day, signals/week, dan distribution by market session.

---

# 27. PERTANYAAN BALIK PUTARAN KE-3

## A. Split & Leakage

1. Apakah sudah dilakukan purge 5 candle di boundary Train → Validation?
2. Apakah sudah dilakukan purge 5 candle di boundary Validation → Test?
3. Jika belum, berapa banyak bar yang overlap?
4. Apakah target terakhir pada Train memerlukan close dari Validation?
5. Apakah target terakhir pada Validation memerlukan close dari Test?

## B. Threshold

6. Apa aturan formal pemilihan 65%?
7. Apakah 65% ditentukan a priori atau dioptimasi?
8. Jika dioptimasi, objective function-nya apa?
9. Mengapa tidak 70% atau 75%?
10. Apakah 65% dipilih dengan minimum coverage constraint?

## C. 44 vs 57

11. Mengapa 57 dipilih jika validation selective accuracy lebih rendah?
12. Apakah 57 dipilih sebelum melihat test?
13. Apakah improvement test 57 stabil per blok waktu?
14. Apakah ada ablation terhadap 13 fitur tambahan?

## D. Statistical Edge

15. Apakah ada confidence interval untuk 57,81%?
16. Apakah digunakan block bootstrap?
17. Apakah hasil stabil per bulan?
18. Berapa signal/day?
19. Apakah sinyal-sinyal tersebut memiliki autocorrelation tinggi?

## E. Probability Baseline

20. Berapa proporsi kelas Up/Down di Train?
21. Berapa Log Loss baseline 50/50?
22. Berapa Brier baseline 50/50?
23. Berapa Log Loss baseline class prior?
24. Apakah LightGBM benar-benar mengungguli baseline probability?

## F. Model Comparator

25. Mengapa LightGBM disebut terbaik kalau RF punya Log Loss/Brier lebih rendah?
26. Apakah matched-coverage comparison sudah dilakukan?
27. Mengapa RF hanya menghasilkan 5 signal?
28. Apakah probabilitas comparator perlu calibration sebelum thresholding?

## G. RRR / Clearance

29. Apa satuan 0,0018?
30. Mengapa 0,0018 × 4150 disebut 0,74?
31. Apakah seharusnya 7,47?
32. Apakah `0.0018` relative percentage, point, atau pip?
33. Apa sumber data empiris untuk angka 0,0018?
34. Apakah spread historis benar-benar dihitung dari broker?

## H. Forward Test

35. Berapa win rate pure ML tanpa filter?
36. Berapa win rate setelah structural filter?
37. Berapa win rate setelah ATR/TP/BEP?
38. Berapa jumlah trade untuk angka 64,8–74,8%?
39. Berapa average signal/day?
40. Apakah PnL sudah net biaya?
41. Apakah BEP +$0,20 sudah net dari biaya?

---

# 28. ARGUMEN AHLI A TERHADAP POTENSI PEMBELAAN B

## Bila B berkata:

> “57 fitur memiliki AUC lebih tinggi, jadi pasti lebih baik.”

### Jawaban A:

Tidak cukup.

Validation dan test harus dibaca bersama. 57 menunjukkan peningkatan pada independent test, tetapi validation tidak menunjukkan peningkatan pada semua metrik.

---

## Bila B berkata:

> “57,81% berarti model sudah memiliki edge yang sangat kuat.”

### Jawaban A:

Belum.

57,81% adalah indikasi edge pada subset high-confidence. Robustness terhadap waktu dan dependence harus diperiksa.

---

## Bila B berkata:

> “65% dipilih karena cukup tinggi.”

### Jawaban A:

Tidak cukup ilmiah.

Harus ada:

- a priori rationale;
- atau validation optimization rule.

---

## Bila B berkata:

> “RF 60% lebih buruk karena hanya 5 signal.”

### Jawaban A:

Saya setuju.

Karena itu jangan bandingkan angka 60% tersebut sebagai performance estimator yang setara.

Gunakan matched coverage atau minimal confidence interval.

---

## Bila B berkata:

> “Brier 0,254 sudah bagus.”

### Jawaban A:

Belum tahu.

Brier harus dibandingkan dengan baseline yang sesuai class prior.

---

# 29. HAL YANG PALING SAYA SUKAI DARI HASIL BARU INI

Saya justru melihat penelitianmu menjadi lebih ilmiah setelah angka 73,97% gugur.

Sekarang narasinya:

```text
Model overall
≈ near random

BUT

Confidence filtering
↓
hanya memilih subset tertentu
↓
directional accuracy meningkat
```

Ini adalah konsep:

> **Selective prediction / abstention under uncertainty**

Dan menurut saya ini jauh lebih realistis untuk financial machine learning daripada klaim:

> “akurasi model 70–80%.”

---

# 30. STRUKTUR BAB IV YANG DIREKOMENDASIKAN

## 4.1 Dataset dan Split

- 49.700 clean bars;
- 70/15/15;
- purge 5 candle jika diterapkan.

## 4.2 Validasi Feature Engineering

- 44 vs 57;
- analisis kontribusi 13 fitur tambahan.

## 4.3 Hasil Training

- LightGBM;
- XGBoost;
- Random Forest;
- Logistic Regression jika tetap digunakan.

## 4.4 Evaluasi Probability

- AUC;
- Log Loss;
- Brier;
- Reliability Curve bila dilakukan.

## 4.5 Selective Prediction

- threshold vs accuracy;
- threshold vs coverage;
- threshold 65%.

## 4.6 Robustness Test

- performance per time block;
- optional block bootstrap.

## 4.7 Forward Testing

- pure ML;
- structural filter;
- risk engine.

## 4.8 Discussion

- kapan model bekerja;
- kapan model abstain;
- sumber kesalahan;
- batasan penelitian.

Ini jauh lebih kuat daripada hanya menampilkan satu angka win rate.

---

# 31. STATUS FINAL SEMENTARA

## Diterima

- 57 fitur sebagai candidate/final model;
- RRR sebagai predictor;
- Clearance sebagai predictor;
- delayed OB activation;
- causal FVG;
- causal MTF;
- macro schedule;
- DXY stale handling;
- frozen model;
- no retraining;
- selective prediction.

## Masih bersyarat

- threshold 65%;
- superiority 57 vs 44;
- probability quality;
- benchmark “best model”;
- statistical edge;
- forward-test attribution.

## Harus diperbaiki

- klaim 73,97% lama;
- klaim “very strong edge”;
- “Pareto optimal”;
- “75 menit optimal”;
- “zero-error”;
- unit 0,0018;
- baseline Log Loss/Brier;
- purge boundary.

---

# 32. PUTUSAN AHLI A

> ## CONDITIONAL APPROVAL — REVISI TERARAH

Saya **tidak menyarankan proyek kembali ke 44 fitur**.

Saya juga **tidak menyarankan menambah fitur baru lagi**.

Pada titik ini, penelitian sudah memiliki cukup banyak fitur.

Yang dibutuhkan sekarang bukan:

> **lebih banyak fitur.**

Yang dibutuhkan:

> **lebih banyak validasi terhadap desain yang sudah ada.**

Prioritas saya:

### 1.
**Purge 5 candle di boundary split.**

### 2.
**Tetapkan aturan formal threshold 65%.**

### 3.
**Audit unit `0.0018`.**

### 4.
**Tambahkan baseline probability untuk Log Loss/Brier.**

### 5.
**Uji stability 57,81% per blok waktu.**

### 6.
**Pisahkan pure ML vs structural filter vs risk execution.**

Jika enam hal tersebut dapat dibuktikan, maka penelitian menurut saya sudah mendekati:

> **METHODOLOGICALLY ACCEPTABLE FOR FINAL THESIS TESTING**

dan tidak perlu lagi melebar ke retraining, continuous learning, M5, atau fitur-fitur tambahan.

---

# 33. ARGUMEN PENUTUP AHLI A

Skripsi ini menurut saya seharusnya tidak dijual sebagai:

> “AI trading bot yang bisa menghasilkan profit tinggi.”

Skripsi ini sebaiknya dijual sebagai:

> **“Sebuah studi penerapan LightGBM untuk selective directional prediction XAUUSD, yang mengintegrasikan informasi teknikal, struktur pasar, multi-timeframe, DXY, dan kalender makroekonomi, kemudian diuji secara out-of-sample dan forward testing dengan frozen model.”**

Dengan framing tersebut:

- 57 fitur masuk akal;
- confidence threshold masuk akal;
- abstention masuk akal;
- MT5 masuk akal;
- forward testing masuk akal;
- dan keterbatasan performa 57,81% tidak menjadi kelemahan yang harus disembunyikan.

Justru transparansi bahwa overall model hanya sedikit di atas random tetapi menjadi lebih selektif pada high-confidence subset dapat menjadi bagian paling menarik dari hasil penelitian.
