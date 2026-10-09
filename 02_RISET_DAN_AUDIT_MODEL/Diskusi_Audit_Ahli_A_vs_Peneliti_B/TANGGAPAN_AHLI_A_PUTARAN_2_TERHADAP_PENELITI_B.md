# TANGGAPAN AHLI A TERHADAP PEMBELAAN PENELITI B
## Putaran Audit Ke-2: Evaluasi, Koreksi, Putusan, dan Pertanyaan Balik

**Judul Penelitian:**

> **Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi**

**Peran Dokumen:**
- **Ahli A:** Auditor metodologi / penelaah kritis
- **Peneliti B:** Perancang dan pengembang sistem
- **Tujuan:** Menguji ulang jawaban Peneliti B, menerima argumen yang valid, menolak klaim yang belum terbukti, serta menghasilkan pertanyaan balik yang harus dijawab secara gamblang sebelum penelitian dianggap final.

---

# 1. PUTUSAN UMUM AHLI A

Setelah membaca respons resmi Peneliti B, saya menilai kualitas pembelaan B **jauh lebih matang dibandingkan kondisi proyek sebelum audit**.

Beberapa kritik penting dari audit sebelumnya sudah dijawab dengan bukti implementasi yang cukup konkret, terutama:

- koreksi *lookahead bias* pada Order Block;
- pembentukan `Est_RRR_Buy`, `Est_RRR_Sell`, dan `Nearest_Clearance` secara causal;
- penggunaan rolling regression untuk pola;
- penggunaan data historis untuk double top/bottom;
- penggunaan closed-candle alignment pada H1/H4;
- penghapusan retraining dan continuous learning dari metodologi;
- penggunaan frozen model saat forward testing;
- koreksi istilah “probabilitas terkalibrasi” menjadi “estimasi probabilitas”.

Respons B juga berhasil memperkuat argumen bahwa **57 fitur secara konsep masih berada dalam ruang lingkup judul**, selama fitur tersebut diposisikan sebagai representasi kondisi internal XAUUSD, konteks multi-timeframe, intermarket DXY, dan makroekonomi.

Namun saya **belum menyatakan penelitian lulus audit sepenuhnya**.

Masih terdapat beberapa bagian yang baru berbentuk klaim dan belum didukung bukti eksperimen yang cukup, serta terdapat beberapa inkonsistensi angka yang harus diselesaikan sebelum data dimasukkan ke skripsi.

### Status sementara:

- **Desain penelitian:** 8/10
- **Validitas metodologis:** 6,5/10
- **Konsistensi dokumentasi:** 5,5/10
- **Potensi penelitian:** tinggi, tetapi klaim harus dibatasi sesuai bukti

---

# 2. HAL YANG SAYA TERIMA DARI PEMBELAAN PENELITI B

## 2.1 Order Block: Koreksi *Lookahead Bias* Diterima

Peneliti B mengakui bahwa kode lama:

```python
impulse_up = (df['close'].shift(-2) - df['close']) > ...
impulse_dn = (df['close'] - df['close'].shift(-2)) > ...
```

menggunakan candle masa depan.

Saya menerima pengakuan tersebut.

Penggunaan:

```python
impulse_confirmed_bull =
    (df['close'] - df['close'].shift(2)) > ...
```

merupakan pendekatan yang secara konsep jauh lebih benar, karena OB baru dianggap aktif setelah displacement dapat dikonfirmasi dari informasi yang sudah tersedia.

### Putusan Ahli A:

**DITERIMA.**

Konsep:

> **Delayed Activation of Confirmed Historical Structure**

merupakan cara yang tepat untuk menghindari retroactive future labeling.

### Namun masih dibutuhkan satu bukti:

B perlu menunjukkan tabel timestamp konkret, misalnya:

| Time | Open | High | Low | Close | Candidate OB | Confirmation | OB Active |
|---|---:|---:|---:|---:|---|---|---|
| t-2 | ... | ... | ... | ... | Ya | Belum | Tidak |
| t-1 | ... | ... | ... | ... | Ya | Belum | Tidak |
| t | ... | ... | ... | ... | - | Terkonfirmasi | Ya |

Tujuannya untuk membuktikan bahwa pada setiap timestamp, model hanya melihat informasi yang tersedia sampai timestamp tersebut.

---

# 3. EST_RRR DAN NEAREST_CLEARANCE: SAYA TERIMA SEBAGAI FITUR ML

Sebelumnya saya sempat menilai fitur RRR dan Clearance terlalu dekat dengan execution rule. Setelah melihat bukti kode B, posisi saya direvisi.

Kode:

```python
df['Swing_High_20'] = df['high'].shift(1).rolling(20).max()
df['Swing_Low_20']  = df['low'].shift(1).rolling(20).min()

df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']

df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)

df['Nearest_Clearance'] = df[['Dist_Support', 'Dist_Resistance']].min(axis=1) - 0.0018
```

secara prinsip hanya memakai data historis.

### Putusan:

**DITERIMA sebagai fitur prediktif**, dengan satu catatan terminologis.

Sebaiknya istilahnya diperjelas menjadi:

> **Estimated Structural Risk-to-Reward Ratio**

atau:

> **Structural RRR Proxy**

karena variabel tersebut bukan RRR transaksi aktual yang dihitung dari TP/SL final.

Model dapat mempelajari hubungan:

```text
momentum
+
trend
+
structural space
+
clearance
+
structural RRR
→
probability of direction
```

Ini adalah logika penelitian yang masuk akal.

---

# 4. PATTERN SLOPE: DITERIMA SECARA KAUSAL

Peneliti B menunjukkan penggunaan rolling regression:

```python
series.rolling(window).apply(...)
```

untuk window 35 candle.

Secara konsep:

```text
[t-34 ... t]
```

dan tidak menggunakan `t+1`, `t+2`, dst.

### Putusan:

**DITERIMA.**

Tetapi tetap perlu audit apakah seluruh fitur turunan pattern benar-benar menggunakan output rolling regression yang sama causal dan tidak ada tahap lain yang memakai future-confirmed pivot.

---

# 5. DOUBLE TOP / DOUBLE BOTTOM: DITERIMA SEMENTARA

B menunjukkan:

```python
roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
```

yang membandingkan dua kelompok puncak historis.

### Putusan:

**DITERIMA SEMENTARA.**

Namun B perlu menjelaskan apakah “Double Top” yang dimaksud benar-benar pola geometrik double top atau hanya ukuran kedekatan dua rolling maxima.

Karena:

> fitur `Double_Top_Dist`

belum tentu sama dengan:

> pola Double Top yang telah tervalidasi.

Lebih aman jika di skripsi disebut:

> **historical double-peak distance feature**

jika memang hanya mengukur jarak dua puncak historis.

---

# 6. KLAIM “57 FITUR TERBUKTI MEMBAWA SINYAL MURNI” SAYA TOLAK

Peneliti B menyatakan bahwa karena 4 dari 13 fitur baru masuk Top-10 feature importance, maka fitur tersebut membuktikan membawa “sinyal murni” dan bukan noise.

### Saya tidak menerima klaim tersebut.

Feature importance hanya menunjukkan bahwa model menggunakan fitur tersebut dalam pembentukan keputusan pohon.

Feature importance tidak otomatis membuktikan:

- generalisasi;
- causal effect;
- non-noise;
- stabilitas antar-periode;
- atau peningkatan out-of-sample.

Sebuah fitur dapat memiliki importance tinggi pada dataset tertentu tetapi tetap menghasilkan generalisasi buruk.

### Formulasi yang saya setujui:

> “Feature importance menunjukkan bahwa fitur tersebut digunakan secara signifikan oleh model dalam pembentukan prediksi pada dataset pengujian yang digunakan.”

### Formulasi yang saya tolak:

> “Feature importance membuktikan fitur tersebut merupakan sinyal murni dan bukan noise.”

Untuk membuktikan bahwa 57 lebih baik dari 44, perlu eksperimen:

```text
44 features
vs
57 features
```

dengan split yang sama dan evaluasi out-of-sample.

---

# 7. MASALAH TERBESAR SEKARANG: THRESHOLD 65%

Peneliti B menyatakan:

> threshold 65% dipilih dari validation set.

Ini secara metodologis adalah keputusan yang benar.

Namun terdapat **inkonsistensi angka** yang wajib diselesaikan.

Dokumen sebelumnya pernah memberikan:

- threshold ≥65%
- directional accuracy 73,97%
- coverage 13,5%

Sedangkan respons B terbaru menyebut:

- threshold ≥65%
- directional accuracy 73,97%
- coverage 18,4%

Selain itu, dokumen sebelumnya pernah menyebut test set 20%, sedangkan pembelaan terbaru menyebut:

```text
Train      = 70%
Validation = 15%
Test       = 15%
```

### Ini harus dibereskan.

Pertanyaan utama:

> **73,97% itu hasil validation atau test?**

Dan:

> **Coverage 13,5% atau 18,4%?**

Ini bukan masalah kosmetik.

Ini menentukan validitas pemilihan threshold.

---

# 8. TABEL YANG WAJIB DISIAPKAN

Saya meminta Peneliti B membuat tabel resmi:

| Dataset | N | Threshold | Accuracy | Coverage |
|---|---:|---:|---:|---:|
| Train | ... | 50–75% | ... | ... |
| Validation | ... | 50–75% | ... | ... |
| Test | ... | 50–75% | ... | ... |

Kemudian dengan tegas dinyatakan:

> **Threshold 65% dipilih berdasarkan validation.**

Setelah threshold 65% dipilih, test set tidak lagi digunakan untuk memilih threshold.

Dengan begitu:

```text
TRAIN
↓
MODEL

VALIDATION
↓
TUNING + THRESHOLD SELECTION

FREEZE

TEST
↓
FINAL EVALUATION

FORWARD TEST
↓
DEPLOYMENT VALIDATION
```

Ini adalah alur yang saya anggap kuat.

---

# 9. “PARETO OPTIMAL 65%” BELUM TERBUKTI

B menyebut 65% sebagai:

> “Titik Pareto Optimal”.

Saya belum menerima istilah tersebut.

Jika dua objective adalah:

- maximizing accuracy;
- maximizing coverage;

maka perlu dibuktikan frontier trade-off-nya.

Lebih aman di skripsi:

> **“Threshold 65% dipilih sebagai kompromi antara directional accuracy dan coverage pada validation set.”**

Tidak perlu menyebut “Pareto optimal” kecuali benar-benar ada perhitungan Pareto frontier.

---

# 10. DEFINISI CONFIDENCE B PERLU DIPERHALUS

B menggunakan:

```text
Confidence = max(P(Up), 1-P(Up))
```

Secara operasional saya setuju.

Tetapi saya tidak menyarankan penjelasan:

> confidence mengukur jarak titik data terhadap decision boundary.

Kalimat itu terlalu spesifik untuk definisi yang dipakai.

Lebih aman:

> **Confidence merupakan nilai probabilitas kelas tertinggi yang dihasilkan model dan digunakan sebagai ukuran keyakinan relatif terhadap salah satu kelas.**

Dengan definisi tersebut:

```text
P(UP) = 0.73
P(DOWN) = 0.27

Confidence = 0.73
Signal = UP
```

---

# 11. KALIBRASI PROBABILITAS: B SUDAH BENAR

Saya menerima koreksi B bahwa `predict_proba()` saja belum cukup untuk disebut probabilitas terkalibrasi.

Jika belum ada:

- Platt Scaling;
- Isotonic Regression;
- Brier Score;
- Reliability Diagram;

maka istilah yang digunakan harus:

> **Estimasi Probabilitas Arah**

bukan:

> Probabilitas Terkalibrasi.

Jika B ingin menyatakan calibration, maka harus ada evaluasi khusus calibration.

---

# 12. HORIZON 75 MENIT: JANGAN DISEBUT “OPTIMAL” TANPA EKSPERIMEN

B menyebut 75 menit sebagai:

> “titik optimal”.

Saya belum menerima klaim tersebut.

75 menit dapat menjadi horizon **yang dipilih**, tetapi belum tentu **optimal secara statistik**.

Untuk membuktikan optimal perlu perbandingan beberapa horizon, misalnya:

- 15 menit;
- 30 menit;
- 45 menit;
- 60 menit;
- 75 menit;
- 90 menit;
- 120 menit.

Karena skripsi tidak perlu melakukan semua itu, saya merekomendasikan bahasa:

> **“75 menit dipilih sebagai horizon prediksi berdasarkan karakteristik timeframe M15 dan tujuan penelitian intraday.”**

Jangan mengklaim “optimal” kecuali memang ada eksperimen pembanding horizon.

---

# 13. BINARY VS TERNARY: ARGUMEN B DAPAT DITERIMA

Saya menerima alasan:

- kategori flat membutuhkan threshold tambahan;
- threshold flat dapat menjadi arbitrer;
- pendekatan biner dipadukan dengan reject option.

Namun harus konsisten:

> model tetap hanya memiliki dua kelas.

Ketika confidence rendah:

> **abstain / no trade**

bukan:

> “model memprediksi kelas flat”.

---

# 14. MULTI-TIMEFRAME ALIGNMENT: SAYA TERIMA PRINSIPNYA

B menggunakan:

```python
close.shift(1)
```

pada H1/H4 sebelum forward-fill ke M15.

Ini merupakan pendekatan yang tepat untuk mencegah model menggunakan candle H1/H4 yang belum selesai.

### Saya terima.

Namun tetap perlu audit:

> bagaimana forward-fill bekerja pada weekend, market closure, dan gap panjang?

Causal belum tentu berarti optimal jika stale value dipertahankan terlalu lama.

---

# 15. DXY: PRINSIP ALIGNMENT DITERIMA, TETAPI FFILL PERLU DIAUDIT

B menyebut missing bar DXY ditangani dengan forward-fill.

Secara causal itu tidak otomatis salah.

Namun perlu dijawab:

> Berapa lama nilai DXY boleh dianggap masih valid?

Misalnya missing 1 jam berbeda dengan missing 12 jam.

Pertanyaan yang perlu dijawab:

- Apakah ada maximum stale duration?
- Apa yang terjadi bila gap panjang?
- Apakah missing value menjadi NaN atau tetap di-fill?
- Apakah return DXY menjadi distorsi karena stale price?

---

# 16. MACROECONOMIC CALENDAR: ARAH B SUDAH TEPAT

Saya menerima penggunaan:

- `Is_NFP_Week`
- `Is_CPI_Day`
- `Is_FOMC_Week`

jika fitur tersebut hanya menggunakan **jadwal yang diketahui sebelum event**.

Yang perlu ditegaskan:

> penelitian tidak menggunakan nilai actual NFP/CPI/FOMC sebagai input ketika nilai tersebut belum tersedia.

Ini bagus untuk menghindari leakage.

---

# 17. SAYA MENOLAK KLAIM “ZERO-ERROR”

Ini harus dihapus.

Peneliti B menulis bahwa forward testing membuktikan sistem bekerja di bawah friksi pasar riil dengan:

> “zero-error”.

Saya tidak menerima klaim ini.

Bahkan sistem trading dapat mengalami:

- prediction error;
- execution error;
- rejected order;
- slippage;
- latency;
- stop loss;
- take profit;
- drawdown.

Jika maksudnya adalah tidak terjadi crash / error software, gunakan:

> “tidak ditemukan kegagalan sistemik pada proses inferensi dan eksekusi selama periode pengujian”

dan hanya jika log memang membuktikannya.

---

# 18. 57 FITUR: SAYA TERIMA SEBAGAI KANDIDAT FINAL

Saya sekarang tidak menolak penggunaan 57 fitur.

Saya justru melihat logika penambahan fitur cukup menarik:

> model 44 fitur dapat menangkap momentum, tetapi kurang mengetahui ruang pergerakan terhadap major resistance/support.

Tambahan fitur:

- Dist_Major_Demand;
- Dist_Major_Supply;
- Pattern_Convergence;
- structural distances;

dapat memberikan representasi konteks yang sebelumnya hilang.

### Namun:

**57 fitur tidak otomatis lebih baik karena jumlahnya lebih banyak.**

Yang perlu dibuktikan:

```text
44 features
vs
57 features
```

dengan:

- dataset sama;
- preprocessing sama;
- split sama;
- configuration sama;
- validation sama;
- independent test sama.

---

# 19. EKSPERIMEN 44 VS 57 YANG SAYA MINTA

Minimal:

| Model | AUC | Log Loss | Brier | F1 | Accuracy | Coverage ≥65% |
|---|---:|---:|---:|---:|---:|---:|
| LightGBM 44 | ... | ... | ... | ... | ... | ... |
| LightGBM 57 | ... | ... | ... | ... | ... | ... |

Dengan demikian dapat dijawab:

> “Apa sebenarnya yang meningkat ketika 13 fitur tambahan dimasukkan?”

Bisa jadi:

- accuracy meningkat;
- AUC meningkat;
- Log Loss turun;
- Brier membaik;
- selective accuracy meningkat;
- atau hanya feature importance yang berubah.

Kita harus mengetahui yang mana.

---

# 20. FAIR BENCHMARK: B PERLU MEMASTIKAN COMPARATOR JUGA DITUNING

B menyatakan:

- LightGBM;
- XGBoost;
- Random Forest

semuanya memakai 57 fitur dan split yang sama.

Bagus.

Tetapi saya masih ingin tahu:

> Apakah XGBoost dan Random Forest juga di-tuning?

Jika:

```text
LightGBM = tuned
XGBoost = default
RF = default
```

maka klaim:

> “LightGBM lebih baik”

tidak sepenuhnya fair.

Lebih aman:

> “Konfigurasi LightGBM yang diuji menghasilkan performa lebih baik daripada konfigurasi model pembanding yang digunakan.”

Kalau ingin membandingkan algoritma, prosedur tuning comparator harus dibuat seadil mungkin.

---

# 21. FEATURE IMPORTANCE HARUS DIINTERPRETASIKAN DENGAN BENAR

Saya tertarik dengan temuan bahwa fitur tambahan masuk ke Top-10 importance.

Tetapi B wajib menjelaskan:

> importance metric apa?

Apakah:

- gain;
- split count;
- permutation importance;
- SHAP?

Angka seperti:

```text
H4_Dist_EMA50 = 1.602
Dist_Major_Demand = 1.253
...
```

harus punya definisi metric yang jelas.

Dan sekali lagi:

> importance tinggi ≠ feature causal importance.

---

# 22. CLASS WEIGHTED PROBABILITY JUGA PERLU DIEKSPLORASI

B menggunakan:

> `class_weight='balanced'`

Saya ingin B menjawab apakah class imbalance memang signifikan.

Jika:

```text
Up ≈ 51%
Down ≈ 49%
```

maka alasan penggunaan `balanced` perlu dijelaskan.

Selain itu, weighting dapat memengaruhi probability output.

Ini menimbulkan pertanyaan penelitian yang menarik:

> **Apakah class weighting meningkatkan kemampuan klasifikasi sekaligus mempertahankan kualitas estimasi probabilitas?**

Ini perlu ditinjau melalui:

- Brier Score;
- calibration curve;
- class distribution;
- prediction distribution.

---

# 23. FORWARD TESTING DAN FROZEN MODEL: SAYA SANGAT SETUJU

Keputusan ini saya anggap sangat baik.

Alurnya:

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

Model tidak berubah selama forward test.

Ini jauh lebih baik untuk eksperimen yang ingin direplikasi.

Retraining manual setiap beberapa bulan boleh dijadikan:

> **rencana pasca-skripsi**

tetapi jangan dimasukkan ke metodologi penelitian saat ini.

---

# 24. POSISI AHLI A TERHADAP SCOPE SKRIPSI

Saya tetap merekomendasikan:

### Fokus utama:
- LightGBM;
- 57 fitur causal;
- directional probability;
- M15;
- H1/H4;
- DXY;
- macro;
- model comparison;
- test;
- forward test.

### Bukan fokus utama:
- automated retraining;
- continuous learning;
- scenario blacklist;
- portfolio management;
- dashboard sebagai novelty;
- M5;
- zero-latency;
- klaim menghapus bias psikologis.

---

# 25. KONSEP INTI YANG MENURUT SAYA PALING KUAT

Saya menyarankan B memposisikan penelitian bukan sebagai:

> “Saya membuat bot trading dengan banyak fitur.”

Tetapi sebagai:

> **“Penelitian ini menguji apakah representasi kondisi pasar yang lebih kaya dapat membantu LightGBM menghasilkan estimasi probabilitas arah XAUUSD yang lebih selektif dan berguna untuk pengambilan keputusan intraday.”**

Strukturnya:

```text
Market Data
↓
Feature Engineering
↓
57 Causal Features
↓
LightGBM
↓
P(UP) / P(DOWN)
↓
Confidence Threshold
↓
Trading Context
↓
Forward Testing
```

Ini jauh lebih kuat secara akademik.

---

# 26. TABEL PUTUSAN AHLI A

| Isu | Putusan |
|---|---|
| OB lookahead | ✅ Diterima setelah koreksi |
| RRR causal | ✅ Diterima |
| Clearance causal | ✅ Diterima |
| Regression slope causal | ✅ Diterima |
| Double Top causal | ⚠️ Diterima sementara |
| FVG causal | ⚠️ Konsep diterima, perlu bukti kode/timestamp |
| MTF causal | ✅ Prinsip diterima |
| DXY alignment | ⚠️ Prinsip diterima, stale FFILL harus diaudit |
| Macro schedule | ✅ Diterima secara prinsip |
| 57 fitur | ✅ Layak sebagai kandidat final |
| Feature importance = bukti “sinyal murni” | ❌ Ditolak |
| 65% Pareto optimal | ⚠️ Belum terbukti |
| 73,97% = calibrated probability | ❌ Ditolak |
| 73,97% = selective directional accuracy | ✅ Dapat diterima bila split jelas |
| Frozen model | ✅ Diterima |
| No retraining | ✅ Diterima |
| M5 dihapus | ✅ Diterima |
| Post-Trade Engine sebagai novelty | ❌ Tidak direkomendasikan |
| Zero-error | ❌ Harus dihapus |
| LightGBM unggul karena tuning | ⚠️ Harus ada benchmark tuning yang fair |

---

# 27. PERTANYAAN BALIK PUTARAN KE-2 UNTUK PENELITI B

Bagian berikut adalah pertanyaan yang saya anggap **wajib dijawab B sebelum penelitian disebut final**.

## A. Pertanyaan tentang 57 fitur

1. Tunjukkan daftar final 57 fitur yang benar-benar masuk `X_train`.
2. Tunjukkan bahwa 57 fitur tersebut adalah feature set yang benar-benar digunakan oleh model final terbaru.
3. Apakah preprocessing 57 fitur identik untuk LightGBM, XGBoost, dan Random Forest?
4. Berapa hasil validation **44 vs 57 fitur**?
5. Apakah 57 fitur dipilih sebelum independent test?
6. Dari 13 fitur tambahan, berapa yang benar-benar meningkatkan validation performance?
7. Apakah ada fitur tambahan yang sebenarnya tidak memberikan kontribusi?

## B. Pertanyaan tentang threshold 65%

8. Berikan tabel validation `threshold vs accuracy vs coverage`.
9. Berikan tabel test `threshold vs accuracy vs coverage`.
10. Mana dataset yang menghasilkan angka 73,97%?
11. Mana yang menghasilkan coverage 13,5%?
12. Mana yang menghasilkan coverage 18,4%?
13. Mengapa angka coverage berbeda?
14. Kapan tepatnya threshold 65% diputuskan?
15. Siapa/apa dasar pemilihan 65%?
16. Apakah 65% pernah diganti-ganti setelah melihat hasil test?
17. Apakah threshold sudah dibekukan sebelum test?

## C. Pertanyaan tentang calibration

18. Berapa Brier Score model tuned?
19. Apakah ada reliability diagram?
20. Apakah calibration curve dilakukan pada validation atau test?
21. Apakah `class_weight='balanced'` memengaruhi probability output?
22. Apakah model default dan tuned memiliki kualitas probability yang berbeda?
23. Apakah istilah “calibrated” sudah dihapus jika memang tidak ada calibration procedure?

## D. Pertanyaan tentang target 75 menit

24. Mengapa memilih 75 menit?
25. Apakah 75 menit dipilih sebelum eksperimen?
26. Apakah ada eksperimen horizon lain?
27. Apa dasar menyebut 75 menit “optimal”?
28. Bagaimana label jika `Close(t+5) == Close(t)`?
29. Mengapa binary lebih relevan daripada ternary dalam konteks data yang digunakan?

## E. Pertanyaan tentang OB

30. Pada timestamp berapa OB mulai aktif?
31. Apakah timestamp aktivasi selalu lebih besar/equal dari timestamp konfirmasi?
32. Apakah OB yang sudah terkonfirmasi pernah ditulis kembali ke candle masa lalu?
33. Bagaimana status OB setelah mitigasi?
34. Apakah OB pernah dihitung menggunakan future outcome?
35. Berikan contoh dataframe candle-by-candle.

## F. Pertanyaan tentang FVG

36. Kapan FVG dianggap terbentuk?
37. Kapan FVG dianggap aktif?
38. Apa definisi partial fill?
39. Apa definisi full fill?
40. Apa definisi invalid?
41. Apakah fill percentage hanya dihitung sampai t?
42. Jika ada beberapa FVG aktif sekaligus, mana yang digunakan?
43. Apakah status FVG pernah memakai future outcome?

## G. Pertanyaan tentang RRR dan Clearance

44. Apakah `Est_RRR` merupakan structural proxy atau actual trade RRR?
45. Apakah support/resistance selalu berasal dari data sebelum t?
46. Apa yang terjadi bila resistance tidak ditemukan?
47. Bagaimana jika nilai Dist_Support mendekati nol?
48. Mengapa ditambahkan epsilon `1e-5`?
49. Apa dasar angka `0.0018` pada clearance?
50. Apakah 0.0018 tetap valid di seluruh kondisi spread broker?
51. Apakah clearance dihitung berbeda untuk BUY dan SELL?

## H. Pertanyaan tentang pattern

52. Apa definisi formal `Pattern_Type_Code`?
53. Apakah kategori benar-benar diperlakukan sebagai categorical?
54. Mengapa kategori 6/7 tidak berurutan?
55. Apakah slope menggunakan price level atau normalized price?
56. Apakah pattern recognition mempunyai dependency lain yang memakai future-confirmed pivot?

## I. Pertanyaan tentang H1/H4

57. Apakah hanya candle H1/H4 yang sudah close yang digunakan?
58. Apa yang terjadi pada M15 yang terjadi di tengah candle H1?
59. Berapa lama H1/H4 values di-forward-fill?
60. Apa yang terjadi saat weekend?
61. Apakah EMA H1/H4 dihitung sebelum atau sesudah shift?

## J. Pertanyaan tentang DXY

62. Berapa maksimum stale duration DXY?
63. Apa yang terjadi ketika DXY missing lama?
64. Apakah forward-fill dilakukan pada price maupun return?
65. Apakah timestamp XAUUSD dan DXY berada pada timezone yang sama?

## K. Pertanyaan tentang macro

66. Apakah hanya jadwal event yang digunakan?
67. Apakah actual release value pernah digunakan?
68. Bagaimana timezone kalender disesuaikan dengan broker?
69. Apa alasan NFP/FOMC memakai week sementara CPI memakai day?
70. Apakah definisi “week” konsisten sepanjang tahun?

## L. Pertanyaan tentang benchmark

71. Apakah XGBoost dituning?
72. Apakah Random Forest dituning?
73. Apakah class weighting comparator sama?
74. Apakah semua memakai 57 fitur yang sama?
75. Apakah semua menggunakan split yang sama?
76. Apakah random seed sama?
77. Apakah preprocessing identik?

## M. Pertanyaan tentang forward testing

78. Apakah threshold tidak berubah selama forward test?
79. Apakah hyperparameter tidak berubah?
80. Apakah model benar-benar frozen?
81. Berapa periode forward testing?
82. Berapa jumlah transaksi final?
83. Bagaimana spread dan slippage dihitung?
84. Bagaimana BEP dikategorikan?
85. Bagaimana drawdown dihitung?
86. Bagaimana Profit Factor dihitung jika terdapat BEP?
87. Apakah semua trade dicatat tanpa seleksi?

---

# 28. ARGUMEN YANG HARUS DIHINDARI DALAM NASKAH

Peneliti B disarankan **tidak menggunakan** klaim berikut kecuali benar-benar dibuktikan:

### Hindari:
> “57 fitur terbukti bukan noise.”

### Ganti:
> “57 fitur menghasilkan performa out-of-sample yang lebih baik pada eksperimen yang dilakukan.”

---

### Hindari:
> “Confidence 73% berarti profit probability 73%.”

### Ganti:
> “Confidence 73% menunjukkan estimasi probabilitas kelas arah tertentu pada target yang didefinisikan.”

---

### Hindari:
> “65% adalah threshold terbaik karena test accuracy 73,97%.”

### Ganti:
> “65% dipilih berdasarkan validation trade-off antara directional accuracy dan coverage.”

---

### Hindari:
> “75 menit adalah horizon optimal.”

### Ganti:
> “75 menit dipilih sebagai horizon prediksi penelitian.”

---

### Hindari:
> “Probabilitas sudah terkalibrasi.”

### Ganti:
> “Model menghasilkan estimasi probabilitas arah.”

---

### Hindari:
> “Forward testing zero-error.”

### Ganti:
> “Forward testing digunakan untuk mengevaluasi penerapan model di bawah kondisi pasar berjalan dan friksi eksekusi.”

---

# 29. PENILAIAN AKHIR AHLI A

Setelah pembelaan B, posisi saya semakin positif.

Saya sekarang:

### Menerima:
- technical features;
- SMC;
- ICT-style structure;
- Fibonacci;
- pattern;
- S/R;
- RRR;
- clearance;
- MTF;
- DXY;
- macro;
- 57 candidate features;
- LightGBM tuned;
- confidence threshold;
- frozen model;
- forward testing.

### Tetapi saya belum menerima:
- klaim feature importance = bukti non-noise;
- klaim 65% Pareto optimal;
- klaim calibration tanpa calibration analysis;
- klaim 75 menit optimal;
- klaim zero-error;
- angka coverage yang tidak konsisten;
- perbandingan model jika comparator ternyata tidak dituning secara seimbang.

---

# 30. KESIMPULAN AUDIT PUTARAN KE-2

Penelitian ini **bukan perlu dirombak dari nol**.

Sebaliknya, fondasinya sudah cukup kuat.

Namun sebelum skripsi dikunci, prioritas utama adalah:

## PRIORITAS 1
**Audit lengkap pipeline 57 fitur dari raw data sampai X_train.**

## PRIORITAS 2
**Pisahkan dengan tegas validation vs test.**

## PRIORITAS 3
**Buktikan pemilihan threshold 65% menggunakan validation.**

## PRIORITAS 4
**Samakan seluruh angka coverage, split, dan hasil evaluasi.**

## PRIORITAS 5
**Bandingkan 44 vs 57 secara out-of-sample.**

## PRIORITAS 6
**Pastikan benchmark XGBoost dan Random Forest fair.**

## PRIORITAS 7
**Audit calibration/probability terminology.**

Jika tujuh hal tersebut sudah selesai, maka penelitian memiliki dasar yang jauh lebih kuat untuk dipresentasikan sebagai skripsi Informatika.

---

# 31. PUTUSAN STATUS

> ## STATUS: CONDITIONAL APPROVAL
>
> Penelitian dapat dilanjutkan dengan arsitektur 57 fitur dan frozen LightGBM, tetapi finalisasi skripsi belum direkomendasikan sebelum isu validation/test split, threshold selection, konsistensi coverage, benchmark fairness, dan audit causal seluruh fitur diselesaikan.

---

# 32. PERMINTAAN TERAKHIR KEPADA PENELITI B

Untuk putaran jawaban berikutnya, saya tidak lagi meminta penjelasan konseptual umum.

Saya meminta B memberikan **bukti** untuk lima hal utama:

1. **Pipeline split yang sebenarnya** — train/validation/test beserta jumlah observasi.
2. **Tabel threshold validation** — accuracy + coverage.
3. **Tabel threshold test** — accuracy + coverage.
4. **Eksperimen 44 vs 57 fitur** — validation dan independent test.
5. **Audit causal 57 fitur** — khususnya OB, FVG, S/R, RRR, clearance, MTF, DXY, dan pattern.

Jika kelima bukti tersebut dapat ditunjukkan dengan jelas, maka sebagian besar keberatan Ahli A terhadap desain penelitian dapat dinyatakan selesai.
