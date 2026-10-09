# AUDIT MENDALAM & DEBAT METODOLOGIS PROYEK SKRIPSI XAUUSD
## Perspektif Ahli A sebagai Auditor terhadap Peneliti B

**Judul penelitian:**

> **Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi**

---

# 0. Tujuan Dokumen

Dokumen ini dibuat sebagai dokumen kerja untuk mengaudit ulang rancangan, implementasi, hasil eksperimen, dan arah penulisan skripsi dari sudut pandang **Ahli A**, yang berperan sebagai penguji metodologi terhadap **Peneliti B**, yaitu pihak/agen yang sebelumnya membangun sistem penelitian.

Tujuan audit bukan sekadar mencari kesalahan. Tujuan utamanya adalah:

1. memisahkan bagian yang secara metodologis sudah kuat dari bagian yang masih lemah;
2. menguji apakah klaim penelitian benar-benar didukung oleh eksperimen;
3. memastikan fitur yang dipakai model tidak menyebabkan *lookahead bias*;
4. menentukan apakah 44 atau 57 fitur layak dijadikan konfigurasi final;
5. memastikan arti probabilitas/confidence tidak salah ditafsirkan;
6. memastikan judul, rumusan masalah, batasan masalah, tujuan, metodologi, implementasi, dan hasil benar-benar konsisten;
7. menyediakan daftar pertanyaan kritis yang harus dapat dijawab Peneliti B secara gamblang;
8. mencegah skripsi berkembang menjadi proyek yang terlalu luas seperti *continuous learning*, *autonomous trading platform*, atau portfolio management.

Dokumen ini adalah **audit konseptual dan metodologis berdasarkan bahan proyek yang tersedia**, bukan klaim bahwa seluruh kode telah dijalankan ulang dari nol.

---

# 1. Posisi Awal Ahli A

## 1.1 Penilaian umum

Secara konsep, penelitian ini **menarik dan layak dijadikan skripsi Informatika**, bahkan cukup kuat karena menggabungkan:

- data XAUUSD;
- fitur teknikal;
- struktur pasar/SMC;
- informasi multi-timeframe;
- DXY sebagai variabel intermarket;
- indikator kalender makroekonomi;
- LightGBM;
- model pembanding;
- prediksi probabilitas;
- dan *forward testing*.

Masalah utama penelitian ini bukan kekurangan ide.

Sebaliknya, masalah utamanya adalah **terlalu banyak ide yang ingin dimasukkan sekaligus**.

Versi awal proyek membawa:

- 44 fitur;
- kemudian berkembang menjadi 57 fitur;
- Multi-Timeframe;
- DXY;
- makroekonomi;
- SMC/ICT;
- Fibonacci;
- pola regresi;
- S/R;
- RRR;
- confidence threshold;
- filter bot;
- ATR risk manager;
- MetaTrader 5;
- Post-Trade Scenario Evaluator;
- continuous learning;
- retraining;
- dashboard;
- dan live forward testing.

Bagi proyek software mungkin itu terlihat sangat lengkap.

Bagi skripsi S1, kelengkapan tersebut justru dapat menjadi kelemahan bila tidak ada hirarki yang jelas.

---

# 2. Posisi Ahli A terhadap Peneliti B

Saya tidak berpendapat bahwa rancangan Peneliti B harus dibuang.

Saya justru mempertahankan gagasan dasarnya dengan perubahan berikut:

> **LightGBM adalah objek penelitian utama.**
>
> **Fitur teknikal, SMC, struktur harga, RRR, clearance, momentum, multi-timeframe, DXY, dan makroekonomi adalah informasi yang dapat digunakan sebagai variabel prediktif selama seluruhnya tersedia secara kausal pada waktu prediksi.**
>
> **MetaTrader 5 dan manajemen risiko adalah sarana penerapan/forward testing, bukan pusat novelty.**
>
> **Model final dibekukan setelah pemilihan model, hyperparameter, dan threshold selesai. Tidak ada retraining selama forward testing.**

Dengan posisi ini, saya tidak menolak eksperimen 57 fitur. Saya justru menganggap 57 fitur **layak dipertahankan sebagai kandidat final** apabila prosedur pemilihannya benar dan tidak menggunakan test set sebagai alat seleksi.

---

# 3. Apakah 57 Fitur Masih Sesuai dengan Judul?

## Jawaban Ahli A: Ya, masih sesuai.

Judul tidak berarti seluruh fitur input harus disebutkan.

Judul menjelaskan fokus utama penelitian:

- XAUUSD;
- LightGBM;
- Multi-Timeframe;
- DXY;
- Makroekonomi.

Sedangkan fitur teknikal dan struktur pasar dapat diposisikan sebagai **variabel internal XAUUSD** yang memperkaya representasi kondisi pasar.

Pembagian konseptual yang lebih rapi:

### A. Kondisi internal XAUUSD
- Candlestick;
- SMC/ICT-style structure;
- Fibonacci;
- RSI;
- Bollinger Bands;
- ADX;
- volume;
- return;
- consecutive candle;
- support/resistance;
- pattern geometry.

### B. Konteks multi-timeframe
- H1;
- H4.

### C. Konteks intermarket
- DXY.

### D. Konteks makroekonomi
- NFP;
- CPI;
- FOMC.

Dengan framing tersebut, 57 fitur **tidak membuat penelitian keluar dari judul**.

Yang harus dihindari adalah menjadikan seluruh istilah tersebut sebagai topik penelitian yang berdiri sendiri.

---

# 4. 44 Fitur vs 57 Fitur

## 4.1 Kondisi sekarang

Daftar yang diberikan Peneliti B memiliki:

- fitur 1–44 dari sembilan kelompok pertama;
- fitur 45–57 dari 13 fitur tambahan.

Artinya:

> **44 + 13 = 57 fitur.**

Jadi bila versi skripsi masih menulis “44 fitur”, sedangkan model final benar-benar menggunakan 57 fitur, dokumen penelitian menjadi tidak konsisten.

## 4.2 Pendapat Ahli A

Saya tidak menyarankan memaksa model kembali menjadi 44 hanya karena proposal awal menggunakan angka 44.

Jika eksperimen 57 fitur memang menunjukkan performa lebih baik, maka 57 boleh menjadi **candidate final feature set**.

Tetapi ada syarat:

### 57 tidak boleh dipilih hanya karena test set memberikan angka yang paling bagus.

Prosedur yang benar:

```text
Data
  ↓
Train
  ↓
Validation
  ↓
Eksperimen 44 vs 57
  ↓
Tetapkan 57 bila memang lebih baik
  ↓
Freeze model + preprocessing + threshold
  ↓
Independent Test
  ↓
Forward Testing
```

Jika 57 dipilih setelah melihat performa test set, maka test set telah ikut dipakai untuk seleksi model.

Itu melemahkan klaim generalisasi.

---

# 5. Audit Terhadap Est_RRR_Buy dan Est_RRR_Sell

## 5.1 Posisi Ahli A

Saya **mengoreksi pendapat sebelumnya**:

> `Est_RRR_Buy` dan `Est_RRR_Sell` tidak otomatis harus dikeluarkan dari ML.

Keduanya **boleh menjadi fitur prediktif**.

Alasannya sederhana:

Model bukan hanya perlu belajar:

> “Apakah harga lima candle lagi lebih tinggi atau lebih rendah?”

Model juga dapat mempelajari:

> “Dalam kondisi seperti ini, bagaimana karakteristik ruang pergerakan yang tersedia?”

Contoh:

```text
Harga saat ini = 4150
Support       = 4140
Resistance    = 4170

Clearance BUY = 20
Risk basis    = 10

Estimated Structural RRR = 2.0
```

Informasi tersebut tersedia pada saat prediksi jika support/resistance dibentuk dari data historis.

Model dapat mempelajari bahwa kombinasi:

- confidence tinggi;
- trend mendukung;
- resistance jauh;
- structural RRR tinggi

mungkin memiliki karakteristik hasil yang berbeda dari:

- confidence tinggi;
- resistance sangat dekat;
- structural RRR rendah.

## 5.2 Mengapa sebelumnya saya menyebutnya dekat dengan keputusan trading?

Karena RRR sering digunakan sebagai **kriteria eksekusi**, bukan sebagai target prediksi.

Namun itu tidak berarti RRR tidak boleh menjadi predictor.

Perbedaannya adalah:

> **“Sebagai fitur ML” menjelaskan kondisi pasar.**
>
> **“Sebagai rule execution” menentukan apakah sinyal hasil model benar-benar dieksekusi.**

Satu variabel bahkan dapat digunakan untuk tujuan yang berbeda selama definisinya jelas.

## 5.3 Titik kritis

Yang paling penting:

`Est_RRR` harus dihitung **secara kausal pada waktu t**.

Tidak boleh:

```text
Entry t
↓
melihat resistance t+5
↓
menghitung reward
↓
memasukkan nilai tersebut sebagai fitur di t
```

Yang boleh:

```text
Data sampai t
↓
deteksi support/resistance yang sudah diketahui
↓
hitung structural clearance / structural RRR
↓
masuk ke model
```

## 5.4 Pertanyaan wajib untuk Peneliti B

1. Bagaimana tepatnya `Est_RRR_Buy` dihitung?
2. Dari mana `Dist_Resistance` diperoleh?
3. Apakah resistance memakai rolling historical maximum atau pivot yang memerlukan candle masa depan?
4. Apakah reward menggunakan TP aktual atau hanya structural resistance?
5. Apakah `Est_RRR` pernah menggunakan data setelah timestamp prediksi?
6. Jika model target adalah arah, apa alasan empiris memasukkan RRR?
7. Apakah performa RRR feature diuji melalui ablation atau feature importance?
8. Apakah fitur RRR tetap tersedia bila tidak ada resistance/target yang jelas?

Jika jawaban B tidak dapat menjelaskan hal-hal tersebut secara matematis, fitur tersebut belum siap masuk naskah final.

---

# 6. Audit Terhadap Nearest_Clearance

## 6.1 Posisi Ahli A

`Nearest_Clearance` juga **sah menjadi fitur prediktif**.

Logikanya:

```text
BUY dekat resistance
        vs
BUY jauh dari resistance
```

adalah dua kondisi pasar yang berbeda.

Model dapat mempelajari apakah sinyal arah tertentu lebih sering berhasil ketika ruang gerak cukup luas.

Dengan demikian:

> `Nearest_Clearance` merepresentasikan konteks geometrik ruang pergerakan harga.

Ini tidak harus diperlakukan sebagai execution-only variable.

## 6.2 Tetapi ada syarat yang sama

Jangan membentuk clearance dari future structure.

Contoh yang bermasalah:

> Swing High yang baru diketahui setelah candle kanan terbentuk.

Contoh yang aman:

> resistance historical yang sudah diketahui sampai candle t.

## 6.3 Pertanyaan wajib

1. Apa definisi matematis `Nearest_Clearance`?
2. Apakah clearance dihitung ke S/R terdekat saja?
3. Apakah spread broker sudah dikurangkan?
4. Apakah clearance berbeda untuk BUY dan SELL?
5. Bagaimana menangani kondisi tidak ada resistance/support yang valid?
6. Apakah threshold clearance merupakan parameter model atau hanya fitur kontinu?
7. Apakah fitur ini tersedia secara penuh pada waktu t?

---

# 7. Confidence Tidak Sama dengan Probabilitas Profit

Ini salah satu audit paling penting.

Misalnya model menghasilkan:

```text
P(UP) = 0.73
P(DOWN) = 0.27
```

Jika target adalah:

```text
Close(t+5) > Close(t)
```

maka angka tersebut secara konseptual berkaitan dengan:

> peluang kelas UP dalam definisi target yang digunakan model.

Itu **bukan otomatis** berarti:

> peluang TP terkena = 73%.

Harga bisa:

```text
Entry
 ↓
SL terkena terlebih dahulu
 ↓
kemudian harga naik
 ↓
Close(t+5) > Entry
```

Dalam kasus tersebut:

- target arah 75 menit bisa benar;
- tetapi trade tetap rugi.

Karena itu, naskah harus membedakan:

### Probability of Direction

dan
### Probability / Expected Outcome of Trade

## 7.1 Tetapi confidence tetap bisa dipakai untuk menentukan kelayakan

Saya setuju dengan argumen Peneliti B bahwa confidence harus berguna untuk penyaringan sinyal.

Contohnya:

```text
LightGBM
 ↓
P(UP) = 73%
 ↓
Confidence threshold
 ↓
Structural context
 ↓
Trend H1/H4
 ↓
DXY
 ↓
Macro condition
 ↓
Trade / No Trade
```

Jadi confidence adalah **komponen penting dalam keputusan**, tetapi jangan secara matematis disamakan dengan probabilitas profit.

## 7.2 Pertanyaan wajib

1. Apa sebenarnya arti `73%` menurut target label yang dipakai?
2. Apakah `73%` merupakan probabilitas yang terkalibrasi atau hanya `predict_proba()`?
3. Apakah pernah dilakukan Brier Score, reliability curve, calibration curve, atau metode kalibrasi khusus?
4. Threshold 65% dipilih dari train, validation, atau test?
5. Jika threshold dipilih setelah melihat test, bagaimana menghindari selection bias?
6. Apakah threshold ditetapkan sekali lalu dibekukan?

---

# 8. Baseline 50,8% vs Tuned 73,97%

Ini harus ditulis dengan sangat hati-hati.

## Salah

> “Tuning LightGBM meningkatkan confidence dari 50,8% menjadi 73%.”

Angka tersebut mencampur dua metrik berbeda.

## Yang lebih tepat

- model awal/default memiliki performa arah sekitar 50,8%;
- model tuned menunjukkan kemampuan seleksi confidence yang lebih baik;
- pada subset prediksi dengan confidence ≥65%, directional accuracy mencapai 73,97%.

Data proyek memang menunjukkan kenaikan directional accuracy ketika threshold diperketat.

## 8.1 Yang sebenarnya menarik dari eksperimen ini

Hasil tersebut mendukung pertanyaan penelitian:

> apakah nilai confidence model dapat digunakan sebagai mekanisme penyaringan sinyal?

Namun hasil tersebut **belum otomatis membuktikan kalibrasi probabilitas**.

Kenaikan:

```text
54,20%
56,95%
60,13%
63,08%
73,97%
82,24%
87,89%
```

seiring threshold naik juga perlu dilihat bersama:

> accuracy + coverage.

Karena semakin ketat threshold, semakin sedikit prediksi yang dipilih.

Maka analisis penting adalah:

> **Accuracy vs Coverage**

serta jika memungkinkan:

> **Precision vs Coverage**

bukan accuracy saja.

---

# 9. Audit Terhadap Order Block

## 9.1 Posisi Ahli A

Saya setuju dengan Peneliti B bahwa OB yang telah terbentuk di masa lalu **dapat menjadi informasi untuk prediksi saat ini**.

Konsepnya bukan:

> “model harus menebak candle ini akan menjadi OB.”

Tetapi:

> “model mengetahui bahwa area tertentu sebelumnya telah membentuk OB yang sudah terkonfirmasi, lalu menilai kondisi harga sekarang terhadap area tersebut.”

Contoh:

```text
t-10 : candle bearish
t-9  : displacement bullish
t-8  : continuation
...
t   : harga kembali mendekati area
```

Pada t, informasi bahwa area tersebut memiliki karakteristik historical OB dapat digunakan.

## 9.2 Masalah metodologis yang harus dibenahi

Jika definisi OB membutuhkan:

```text
Close(t+2)
```

untuk menetapkan candle t sebagai OB, maka candle t **tidak boleh diberi label OB tersebut saat t**.

Yang benar:

```text
t    : kandidat OB
t+1  : konfirmasi
t+2  : informasi lengkap
t+2+ : OB aktif dalam feature state
```

Jadi bukan:

> retroactively assigning future knowledge.

Melainkan:

> **delayed activation of confirmed historical structure.**

## 9.3 Konsep ini justru dapat menjadi kekuatan penelitian

Model dapat menggunakan:

- posisi OB;
- jarak ke OB;
- umur OB;
- apakah OB sudah dimitigasi;
- berapa kali disentuh;
- arah OB;
- strength score;

selama semua dihitung dari histori yang tersedia.

## 9.4 Pertanyaan wajib

1. Kapan OB dianggap resmi “terbentuk”?
2. Kapan OB dianggap “confirmed”?
3. Informasi apa yang dibutuhkan untuk konfirmasi?
4. Pada timestamp berapa fitur OB mulai bernilai 1?
5. Apakah OB masih aktif setelah disentuh?
6. Apa definisi mitigasi?
7. Apakah strength OB pernah dihitung menggunakan hasil trade masa depan?
8. Apakah OB dari H1/H4 juga dipakai?
9. Jika ya, bagaimana alignment H1/H4 terhadap M15?

---

# 10. Audit Terhadap FVG

## 10.1 Posisi Ahli A

Saya juga setuju dengan prinsip Peneliti B bahwa model bukan hanya perlu tahu:

```text
FVG_Bull = 1
```

tetapi dapat mengetahui **state** FVG.

Contoh:

```text
FVG terbentuk
      ↓
Fresh
      ↓
Partially filled
      ↓
Fully filled / mitigated
      ↓
Invalid
```

Semua itu bisa menjadi informasi historis.

## 10.2 State FVG yang berpotensi berguna

Secara desain, candidate features dapat mencakup:

- FVG_Bull/FVG_Bear;
- distance to FVG;
- FVG size;
- FVG age;
- fill percentage;
- touch count;
- active/inactive;
- mitigated/not mitigated.

Tidak berarti semuanya harus ditambahkan.

Intinya:

> **FVG bukan sekadar flag.**

## 10.3 Batas utama

Masalah terjadi bila model pada t mengetahui:

> “FVG ini berhasil memantulkan harga.”

padahal pantulan itu baru diketahui pada t+3.

Artinya tidak boleh ada “validation strength” yang dihitung menggunakan future outcome lalu ditempel kembali ke t.

Yang sah adalah:

> status FVG berdasarkan histori sampai t.

## 10.4 Pertanyaan wajib

1. Bagaimana FVG terbentuk secara tepat?
2. Kapan FVG dianggap valid?
3. Apa definisi full fill?
4. Apa definisi partial fill?
5. Apa definisi invalid?
6. Apakah touch count dihitung hanya sampai t?
7. Apakah “FVG strength” memakai hasil masa depan?
8. Bagaimana jika ada beberapa FVG aktif sekaligus?
9. FVG mana yang dianggap paling relevan?
10. Apakah model menerima hanya FVG terdekat atau seluruh state?

---

# 11. SMC/ICT dalam Judul

## Posisi Ahli A

Tidak perlu memasukkan “SMC” atau “ICT” ke judul.

Judul tetap konsisten selama:

> SMC/ICT diposisikan sebagai cara membentuk fitur struktur pasar.

Lebih aman mengatakan:

> **“fitur struktur pasar berbasis Smart Money Concepts (SMC)”**

daripada mengklaim:

> “model mendeteksi aktivitas institusional.”

Model berbasis OHLC/tick volume tidak secara langsung mengobservasi order bank sentral, hedge fund, atau liquidity provider.

Yang digunakan adalah **proxy berbasis price action dan struktur harga**.

Ini akan membuat narasi lebih ilmiah.

---

# 12. Audit 57 Fitur

## 12.1 Daftar yang diaudit

### I. Candlestick M15 — 4
1. Body_Ratio
2. Lower_Wick_Ratio
3. Upper_Wick_Ratio
4. Pinbar_Ratio

### II. SMC — 10
5. FVG_Bull
6. FVG_Bear
7. BOS_Bull
8. BOS_Bear
9. CHoCH_Bull
10. CHoCH_Bear
11. Liquidity_Sweep_High
12. Liquidity_Sweep_Low
13. Order_Block_Bull
14. Order_Block_Bear

### III. Fibonacci — 4
15. Fibo_Pos_100
16. Fibo_Dist_382
17. Fibo_Dist_500
18. Fibo_Dist_618

### IV. Momentum/Volatility/Volume — 6
19. RSI_14
20. BB_Bandwidth
21. BB_Pos
22. ADX_14
23. Volume_Ratio
24. Swing_High_20

### V. Multiscale Returns — 5
25. XAU_Return_1
26. XAU_Return_3
27. XAU_Return_5
28. XAU_Return_10
29. XAU_Return_20

### VI. DXY — 4
30. DXY_Return_1
31. DXY_Return_3
32. DXY_Trend
33. XAU_DXY_Ratio_Return

### VII. Makro — 3
34. Is_NFP_Week
35. Is_CPI_Day
36. Is_FOMC_Week

### VIII. Multi-Timeframe H1/H4 — 6
37. Trend_H1_Bull
38. Trend_H1_Strong
39. H1_Dist_EMA50
40. Trend_H4_Bull
41. Trend_H4_Strong
42. H4_Dist_EMA50

### IX. Consecutive Candle — 2
43. Consecutive_Bull
44. Consecutive_Bear

### X. Fitur Tambahan — 13
45. Dist_Support
46. Dist_Resistance
47. Dist_Major_Demand
48. Dist_Major_Supply
49. Nearest_Clearance
50. Est_RRR_Buy
51. Est_RRR_Sell
52. Pattern_Slope_High
53. Pattern_Slope_Low
54. Pattern_Convergence
55. Pattern_Type_Code
56. Double_Top_Dist
57. Double_Bottom_Dist

---

# 13. Fitur yang Menjadi Fokus Audit Lookahead

Kelompok paling berisiko:

### Risiko tinggi
- Order_Block
- BOS/CHoCH jika menggunakan pivot yang membutuhkan candle setelahnya
- Swing High/Low
- Pattern recognition
- Major Demand/Supply
- Double Top/Bottom
- Pattern slope/pattern type jika memakai future-confirmed pivot

### Risiko sedang
- FVG active/mitigated state
- Fibonacci swing
- Nearest_Clearance
- Estimated structural RRR

### Relatif mudah dibuat causal
- candle ratios
- RSI
- BB
- ADX
- returns
- volume ratio
- DXY returns
- EMA H1/H4
- calendar flags

---

# 14. Master Rule Anti-Lookahead

Untuk setiap fitur harus dapat ditulis:

> **Feature_t = f(Data_<=t)**

dan TIDAK boleh:

> **Feature_t = f(Data_>t)**

Bahkan jika secara intuitif fitur tersebut “berasal dari pola historis”, pembentukan datanya harus tetap causal.

## Contoh

### Tidak valid

```text
OB_t memakai Close(t+2)
```

### Valid

```text
OB confirmed pada t+2
↓
OB feature aktif mulai t+2
```

---

# 15. Fitur yang Terlihat “Prediktif” tetapi Berpotensi Circular

Ini juga harus diaudit:

- Est_RRR_Buy
- Est_RRR_Sell
- Nearest_Clearance
- Dist_Resistance
- Dist_Support

Pertanyaannya bukan apakah fitur tersebut boleh digunakan.

Pertanyaannya:

> **apakah fitur tersebut dibentuk independen dari target dan hanya dari state pasar pada t?**

Jika target adalah:

```text
Close(t+5) > Close(t)
```

maka fitur tidak boleh diam-diam menggunakan:

```text
High/Low/Close t+1 ... t+5
```

---

# 16. Pattern_Type_Code

`Pattern_Type_Code` adalah fitur yang menarik, tetapi secara encoding perlu diperiksa.

Jika:

```text
0 = Neutral
1 = Ascending
2 = Descending
3 = Wedge
```

model dapat membaca angka sebagai nilai yang memiliki urutan.

Padahal secara semantik:

> Ascending ≠ Descending ≠ Wedge

Bila fitur bersifat nominal/kategorikal, metodologi harus menjelaskan bagaimana LightGBM menangani encoding tersebut.

Pertanyaan untuk B:

1. Apakah `Pattern_Type_Code` diperlakukan numeric atau categorical?
2. Mengapa memilih integer code?
3. Apa konsekuensi encoding tersebut?
4. Apakah feature importance berubah bila encoding berbeda?

---

# 17. Redundansi Fitur

57 fitur bukan otomatis lebih baik.

Ada kemungkinan beberapa fitur membawa informasi yang sangat mirip:

- XAU_Return_1 dengan Body_Ratio;
- Dist_Support dengan Nearest_Clearance;
- Dist_Resistance dengan Nearest_Clearance;
- Trend_H1_Bull dengan H1_Dist_EMA50;
- Trend_H4_Bull dengan H4_Dist_EMA50;
- BOS dengan CHoCH;
- RSI dengan momentum return;
- Fibo_Pos_100 dengan beberapa Fibo_Distance.

LightGBM memang mampu menangani hubungan non-linear dan interaksi, tetapi menambahkan fitur tetap dapat menambah:

- noise;
- redundancy;
- variance;
- peluang overfitting.

Karena itu, klaim:

> “57 lebih banyak, maka otomatis lebih baik”

tidak dapat diterima.

Yang harus dibuktikan:

> “57 memberikan generalisasi lebih baik pada validation/independent test yang dirancang dengan benar.”

---

# 18. Apakah 57 Fitur Layak Dipertahankan?

## Keputusan sementara Ahli A

**Ya, sebagai kandidat final.**

Tetapi saya memberi status:

> **CONDITIONAL APPROVAL**

Syaratnya:

1. semua 57 fitur causal;
2. definisinya terdokumentasi;
3. 57 dipilih tanpa membocorkan test;
4. preprocessing konsisten;
5. model final benar-benar menggunakan 57;
6. hasil pembanding memakai feature basis yang adil;
7. feature importance tidak dijadikan bukti sebab-akibat;
8. tidak ada target leakage melalui RRR/structure features.

---

# 19. Model Tuned: Apa yang Sebenarnya Dibuktikan?

Model proyek saat ini memiliki tuned LightGBM dengan parameter seperti:

- n_estimators = 800
- learning_rate = 0.015
- max_depth = 5
- num_leaves = 24
- min_child_samples = 50
- reg_alpha = 0.1
- reg_lambda = 1.0
- class_weight = balanced

Hasil proyek menunjukkan model tuned lebih baik digunakan untuk confidence filtering dibanding konfigurasi awal.

Namun:

> **parameter tuning harus dinilai berdasarkan validation, bukan test.**

Dan jika ingin menyatakan parameter tertentu “menyebabkan” peningkatan:

> harus ada eksperimen yang mengisolasi pengaruh parameter tersebut.

Lebih aman mengatakan:

> “konfigurasi tuned yang digunakan menghasilkan performa lebih baik.”

---

# 20. Perbandingan dengan XGBoost dan Random Forest

Model proyek sebelumnya menunjukkan hasil yang berbeda antara LightGBM, XGBoost, dan Random Forest.

Yang perlu dipertahankan adalah **fair comparison**.

Semua model harus:

- memakai dataset yang sama;
- target yang sama;
- train/validation/test split yang sama;
- preprocessing yang sama jika relevan;
- tidak memakai informasi test dalam tuning;
- dievaluasi pada test yang sama.

Jika LightGBM memakai 57 fitur tetapi benchmark memakai 44 fitur, perbandingan tidak lagi murni membandingkan algoritma.

Pertanyaan wajib:

> Apakah XGBoost dan Random Forest juga menggunakan feature set final yang sama dengan LightGBM?

Jika jawabannya tidak, desain benchmark harus diperbaiki atau alasan perbedaannya harus dijelaskan.

---

# 21. Forward Testing

Forward testing merupakan bagian yang baik untuk penelitian karena menguji penerapan model pada data yang datang setelah fase pelatihan.

Tetapi angka transaksi harus diperlakukan dengan hati-hati.

Data proyek yang tersedia saat ini baru menunjukkan beberapa transaksi awal.

Jangan menyimpulkan:

> sistem terbukti sangat efektif

berdasarkan sampel yang masih sedikit.

Metrik final harus dihitung setelah periode forward testing yang sudah ditetapkan.

---

# 22. Tidak Ada Retraining

Ini keputusan yang saya dukung penuh.

Model final harus:

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

Bukan:

```text
Train
 ↓
Trade
 ↓
Retrain
 ↓
Trade
 ↓
Retrain
```

Jika retraining otomatis dilakukan selama forward test, model tidak lagi sama dengan model yang dievaluasi sebelumnya.

Untuk penelitian komparatif, *frozen model* jauh lebih mudah dipertanggungjawabkan.

---

# 23. Komponen yang Sebaiknya Tidak Dijadikan Fokus Utama

Saya menyarankan hal berikut tidak dijadikan novelty utama:

- Post-Trade Scenario Evaluator Engine;
- continuous learning;
- automatic blacklist scenario;
- automated retraining;
- GUI monitoring;
- “zero latency”;
- klaim menghilangkan bias psikologis;
- portfolio management.

Komponen tersebut boleh ada sebagai implementasi pendukung bila sudah terlanjur dibuat, tetapi jangan sampai menjadi pertanyaan penelitian baru.

---

# 24. Confidence Threshold 65%

Saya menganggap threshold ≥65% masuk akal sebagai **decision threshold**, tetapi metodologinya harus jelas.

Jangan menulis:

> “65% adalah threshold terbaik”

jika 65% dipilih setelah melihat test set.

Yang lebih aman:

> threshold ditetapkan menggunakan validation data atau ditentukan a priori, kemudian dibekukan sebelum test/forward testing.

Jika ingin membandingkan:

```text
50%
55%
58%
60%
65%
70%
75%
```

itu dapat dijadikan analisis **confidence-coverage trade-off**.

Tetapi jangan menjadikan semua threshold sebagai hyperparameter yang bebas dipilih setelah melihat test.

---

# 25. Apakah Probabilitas LightGBM Benar-Benar “Terkalibrasi”?

Pertanyaan ini harus dijawab secara eksplisit.

`predict_proba()` menghasilkan estimasi probabilitas.

Tetapi:

> probability output ≠ automatically calibrated probability.

Jika penelitian tidak melakukan:

- Platt scaling;
- isotonic regression;
- calibration curve;
- Brier Score analysis;
- atau metode calibration lain,

lebih aman memakai istilah:

> **estimasi probabilitas**

daripada:

> **probabilitas terkalibrasi**.

## Pertanyaan untuk B

1. Metode calibration apa yang digunakan?
2. Data calibration memakai subset mana?
3. Calibration dilakukan sebelum test atau setelah melihat test?
4. Apakah Brier Score dihitung?
5. Apakah reliability diagram dibuat?
6. Apakah confidence 70% benar-benar berarti sekitar 70% outcome terjadi sesuai definisi target?

Jika tidak ada jawaban yang kuat, hapus kata “terkalibrasi” dari klaim utama skripsi.

---

# 26. Rumusan Masalah yang Paling Aman

Setelah seluruh audit ini, saya merekomendasikan tiga fokus:

## 1. Rekayasa data dan feature fusion

> Sejauh mana arsitektur *Multi-Source Feature Fusion* yang mengintegrasikan fitur teknikal, struktur pasar, *multi-timeframe* H1/H4, DXY, dan makroekonomi dapat diterapkan sebagai data prediktif XAUUSD tanpa *lookahead bias*?

## 2. Pemodelan dan perbandingan algoritma

> Sejauh mana penerapan dan optimasi LightGBM menghasilkan estimasi probabilitas arah XAUUSD pada horizon 75 menit serta bagaimana kinerjanya dibandingkan dengan XGBoost dan Random Forest?

## 3. Evaluasi penerapan

> Sejauh mana model LightGBM yang telah ditetapkan dengan confidence threshold tertentu mempertahankan kinerjanya pada pengujian independen dan *forward testing* melalui MetaTrader 5 berdasarkan metrik klasifikasi dan metrik perdagangan?

Rumusan ini tidak menuntut:

- retraining;
- continuous learning;
- Post-Trade Engine;
- ablation setiap fitur;
- atau pengembangan portfolio.

---

# 27. Struktur Tujuan Penelitian

Harus 1:1 dengan rumusan masalah:

1. membangun dan memastikan validitas feature pipeline;
2. menerapkan, mengoptimasi, dan membandingkan LightGBM;
3. mengevaluasi model pada test dan forward testing.

Tidak perlu 5 tujuan.

---

# 28. Struktur Penelitian Final yang Saya Rekomendasikan

```text
DATA
├── XAUUSD M15
├── H1
├── H4
├── DXY
└── Macro Calendar
       ↓
FEATURE ENGINEERING
       ↓
57 CANDIDATE FEATURES
       ↓
CAUSAL / ANTI-LOOKAHEAD AUDIT
       ↓
TRAIN / VALIDATION / TEST
       ↓
FEATURE SET SELECTION
(44 vs 57 bila memang diuji)
       ↓
LIGHTGBM TUNED
       ↓
FROZEN MODEL
       ↓
PROBABILITY P(UP/DOWN)
       ↓
CONFIDENCE THRESHOLD
       ↓
OPTIONAL TRADING CONTEXT
(RRR / Clearance / Trend / News)
       ↓
FORWARD TESTING MT5
       ↓
EVALUATION
```

---

# 29. Pertanyaan Besar untuk Peneliti B

Bagian ini sengaja dibuat sebagai **daftar interogasi metodologis**. Peneliti B seharusnya dapat menjawab semua pertanyaan ini tanpa jawaban samar.

## A. Tentang target

1. Mengapa memilih horizon 75 menit?
2. Mengapa lima candle M15?
3. Mengapa bukan 30, 60, atau 90 menit?
4. Mengapa targetnya Close(t+5) dibanding Close(t)?
5. Bagaimana label jika nilainya sama persis?
6. Apakah target seimbang?
7. Mengapa menggunakan binary classification, bukan ternary (up/flat/down)?

## B. Tentang confidence

8. Confidence sebenarnya mengukur apa?
9. Apakah confidence 65% berarti probabilitas arah atau probabilitas profit?
10. Dari mana threshold 65% berasal?
11. Apakah threshold dipilih dari validation atau test?
12. Apa hubungan confidence dengan coverage?
13. Mengapa semakin tinggi threshold accuracy naik?
14. Apakah kenaikan accuracy terjadi karena model memang lebih yakin atau karena hanya memilih kasus ekstrem?
15. Apakah probabilitas benar-benar calibrated?

## C. Tentang 57 fitur

16. Mengapa 13 fitur tambahan ditambahkan?
17. Apakah improvement 57 dibanding 44 diuji pada validation?
18. Apakah semua 13 fitur ditambahkan sekaligus?
19. Fitur mana yang paling berkontribusi?
20. Apakah ada fitur redundant?
21. Apakah ada fitur yang sebenarnya execution rule?
22. Apakah feature importance stabil antar-periode?

## D. Tentang RRR

23. Mengapa RRR dijadikan input?
24. Bagaimana structural RRR dihitung?
25. Apakah resistance/support future-confirmed?
26. Apakah RRR sudah mencerminkan SL/TP aktual?
27. Jika bukan, mengapa diberi nama RRR?
28. Apakah RRR feature menyebabkan data leakage?

## E. Tentang Clearance

29. Apa yang dimaksud “ruang gerak”?
30. Bagaimana support/resistance ditentukan?
31. Bagaimana major demand/supply ditentukan?
32. Apa yang terjadi bila ada banyak resistance?
33. Apakah clearance hanya fitur geometrik atau filter execution?
34. Apakah clearance tersedia tepat pada candle keputusan?

## F. Tentang OB

35. Kapan OB dianggap terbentuk?
36. Kapan OB dianggap valid?
37. Apakah konfirmasi membutuhkan future candles?
38. Kapan OB mulai aktif sebagai fitur?
39. Apakah OB masih aktif setelah disentuh?
40. Bagaimana OB dimitigasi?
41. Apakah strength OB berasal dari histori atau future outcome?

## G. Tentang FVG

42. Kapan FVG terbentuk?
43. Kapan FVG dianggap valid?
44. Bagaimana partial fill dihitung?
45. Bagaimana full fill dihitung?
46. Apa definisi invalid?
47. Apakah touch count hanya sampai t?
48. Jika ada beberapa FVG, mana yang digunakan?
49. Apakah model tahu lokasi FVG atau hanya status 0/1?

## H. Tentang Multi-Timeframe

50. Bagaimana candle H1/H4 disejajarkan dengan M15?
51. Apakah candle H1/H4 yang belum selesai pernah digunakan?
52. Apakah EMA H1/H4 dihitung hanya dari candle closed?
53. Apa yang terjadi saat M15 berada di tengah candle H1?
54. Apakah informasi H1/H4 mengalami hidden lookahead?

## I. Tentang DXY

55. Apakah timestamp XAUUSD dan DXY benar-benar sejajar?
56. Bagaimana jika salah satu pasar memiliki missing candle?
57. Mengapa menggunakan return 1 dan 3?
58. Mengapa ratio XAU/DXY diperlukan jika return DXY sudah ada?
59. Apakah hubungan DXY-XAU stabil sepanjang periode?

## J. Tentang Makro

60. Mengapa NFP memakai week, tetapi CPI memakai day?
61. Mengapa FOMC memakai week?
62. Apakah informasi kalender tersedia sebelum event?
63. Apakah sistem mengetahui berita setelah event terjadi?
64. Apakah timezone broker dan timezone kalender sudah diselaraskan?
65. Apakah holiday/weekend mengubah definisi week?

## K. Tentang model

66. Mengapa LightGBM?
67. Apa alasan memilih XGBoost sebagai comparator?
68. Mengapa Random Forest?
69. Mengapa tidak Logistic Regression?
70. Apakah semua model menggunakan feature set yang sama?
71. Apakah tuning comparator juga dilakukan?
72. Apakah class imbalance benar-benar ada?
73. Mengapa menggunakan balanced class weights?
74. Apakah tuning dilakukan memakai validation?
75. Bagaimana mencegah overfitting hyperparameter?

## L. Tentang evaluasi

76. Mengapa accuracy tetap dipakai?
77. Mengapa ROC-AUC?
78. Mengapa Log Loss?
79. Mengapa Precision dan Recall?
80. Mengapa F1?
81. Mengapa financial metrics juga diperlukan?
82. Apakah profit factor dihitung dari seluruh trade?
83. Bagaimana BEP dihitung?
84. Bagaimana drawdown dihitung?
85. Apakah spread dan slippage dimasukkan?

## M. Tentang forward testing

86. Apakah forward testing benar-benar out-of-sample?
87. Apakah model pernah dilatih ulang?
88. Apakah threshold diubah selama forward testing?
89. Apakah parameter bot berubah?
90. Berapa durasi forward test?
91. Berapa jumlah trade?
92. Bagaimana menentukan kapan cukup?
93. Apakah satu akun dipakai?
94. Apakah broker-specific behavior menjadi faktor?
95. Seberapa generalizable hasil ke broker lain?

---

# 30. Argumen Ahli A terhadap Kemungkinan Argumen Peneliti B

## B mungkin mengatakan:

> “Fitur semakin banyak semakin bagus.”

### Jawaban A:

Tidak.

Fitur tambahan hanya bagus bila meningkatkan informasi yang dapat digeneralisasi.

57 fitur harus menang karena **informasinya lebih kaya**, bukan karena jumlahnya lebih banyak.

---

## B mungkin mengatakan:

> “Accuracy 73,97% membuktikan model sangat bagus.”

### Jawaban A:

Belum cukup.

73,97% terjadi pada subset dengan confidence ≥65%. Coverage subset tersebut jauh lebih kecil.

Maka yang harus dilihat adalah:

> accuracy + coverage + number of signals + calibration/error characteristics.

---

## B mungkin mengatakan:

> “Model sudah menghasilkan probabilitas, jadi otomatis calibrated.”

### Jawaban A:

Tidak.

`predict_proba()` bukan bukti bahwa probability calibration telah tervalidasi.

---

## B mungkin mengatakan:

> “OB berasal dari candle masa lalu, jadi aman.”

### Jawaban A:

Secara konsep iya.

Tetapi implementasi harus membuktikan kapan OB **diketahui**.

Jika penetapannya menggunakan future confirmation dan label dipasang ke candle sebelumnya, terjadi lookahead.

---

## B mungkin mengatakan:

> “FVG harus tahu apakah masih valid.”

### Jawaban A:

Setuju.

Tetapi status “valid sampai t” harus dihitung hanya dari histori sampai t.

Jangan menggunakan eventual success/failure sebagai status pada masa lalu.

---

## B mungkin mengatakan:

> “RRR adalah fitur supaya model tahu trade mana yang layak.”

### Jawaban A:

Saya setuju.

Tetapi definisinya harus menjelaskan:

> apakah RRR merepresentasikan kondisi pasar atau hasil simulasi trade.

Dan asal support/resistance harus causal.

---

## B mungkin mengatakan:

> “Forward testing saja sudah cukup membuktikan.”

### Jawaban A:

Tidak.

Forward testing adalah lapisan validasi penerapan.

Model tetap harus punya evaluasi statistik yang independen.

---

# 31. Hal yang Saya Anggap Sudah Kuat dari Proyek B

1. Penggunaan LightGBM sebagai model utama masuk akal untuk data tabular.
2. Adanya model pembanding adalah keputusan ilmiah yang baik.
3. Target directional classification lebih langsung daripada regresi harga nominal untuk tujuan sinyal arah.
4. H1/H4, DXY, dan makro memang memberi konteks yang berbeda.
5. Usaha memisahkan model ML dari execution engine adalah arsitektur yang sehat.
6. Keputusan membekukan model saat forward testing sangat baik untuk menjaga interpretasi eksperimen.
7. Eksperimen 44 vs 57 fitur berpotensi menjadi kontribusi metodologis yang menarik bila proses seleksinya benar.
8. RRR, clearance, OB, dan FVG berpotensi memperkaya representasi state pasar bila semua causal.

---

# 32. Kelemahan Utama yang Harus Diselesaikan

Prioritas tertinggi:

### LEVEL 1 — Wajib

1. Audit lookahead seluruh 57 fitur.
2. Tetapkan feature set final: 44 atau 57.
3. Pastikan 57 dipilih tanpa memakai test set.
4. Selaraskan semua bab dengan angka fitur final.
5. Tentukan definisi confidence dengan benar.
6. Jangan menyebut probabilitas “calibrated” tanpa metode calibration.
7. Pastikan benchmark memakai dataset/features yang fair.
8. Tetapkan threshold sebelum test/forward testing.

### LEVEL 2 — Sangat penting

9. Jelaskan causal definition OB.
10. Jelaskan causal state FVG.
11. Jelaskan structural RRR.
12. Jelaskan clearance.
13. Audit Multi-Timeframe alignment.
14. Audit macro-event timestamps.
15. Audit DXY/XAU timestamp synchronization.

### LEVEL 3 — Penyederhanaan skripsi

16. Hapus retraining.
17. Hapus continuous learning.
18. Jangan jadikan Post-Trade Engine novelty.
19. Hapus M5.
20. Hindari zero latency.
21. Hindari klaim menghilangkan bias psikologis.
22. Hindari portfolio/investment management framing.

---

# 33. Posisi Final Ahli A

Setelah seluruh argumen dipertimbangkan, saya **tidak menolak arah penelitian Peneliti B**.

Saya justru menyimpulkan:

> **Arsitektur penelitian ini secara konsep layak dipertahankan, tetapi harus dibuat lebih disiplin secara metodologis.**

Saya menerima:

- technical features;
- SMC;
- ICT-style structure;
- Fibonacci;
- pattern;
- S/R;
- RRR;
- clearance;
- Multi-Timeframe;
- DXY;
- macro;
- 57 features;
- LightGBM tuned;
- confidence threshold;
- MetaTrader 5;
- forward testing.

Tetapi saya menetapkan syarat:

> **Semua feature harus causal.**
>
> **Semua pemilihan model/threshold harus memakai validation, bukan test.**
>
> **Test harus benar-benar independen.**
>
> **Forward testing harus memakai frozen model.**
>
> **Confidence tidak boleh dipasarkan sebagai probability of profit.**
>
> **RRR/clearance boleh menjadi predictor, tetapi formulanya wajib jelas.**
>
> **OB/FVG boleh menggunakan historical confirmed structure, tetapi tidak boleh retroactive future labeling.**

---

# 34. Kalimat Posisi Penelitian yang Saya Rekomendasikan

Bila harus menjelaskan penelitian kepada dosen dalam satu paragraf:

> Penelitian ini menerapkan LightGBM untuk memprediksi probabilitas arah pergerakan harga XAUUSD pada horizon 75 menit menggunakan representasi kondisi pasar yang dibentuk dari fitur teknikal dan struktur harga, konteks tren multi-timeframe H1/H4, hubungan intermarket DXY, serta informasi kalender makroekonomi. Fitur tambahan seperti support/resistance, clearance, dan estimasi structural RRR digunakan sebagai representasi kondisi ruang pergerakan dan kualitas setup selama nilainya dapat diketahui pada waktu prediksi. Model LightGBM dibandingkan dengan XGBoost dan Random Forest pada skema pengujian yang sama, kemudian model final dibekukan dan diterapkan pada forward testing tanpa retraining. Confidence model digunakan sebagai ukuran keyakinan terhadap arah yang diprediksi dan sebagai dasar penyaringan sinyal, sedangkan kelayakan transaksi tetap mempertimbangkan konteks risiko dan kondisi pasar.

---

# 35. Checklist Sebelum Peneliti B Menjawab “FINAL”

Penelitian sebaiknya belum diberi status final sebelum B dapat menjawab YA untuk seluruh pertanyaan berikut:

- [ ] Semua 57 fitur sudah memiliki definisi matematis.
- [ ] Semua 57 fitur causal.
- [ ] Tidak ada future pivot masuk ke historical feature.
- [ ] OB confirmation tidak retroaktif.
- [ ] FVG state tidak menggunakan future outcome.
- [ ] Support/resistance tidak future-confirmed.
- [ ] Structural RRR tidak memakai future price.
- [ ] Clearance tidak memakai future information.
- [ ] H1/H4 hanya menggunakan candle closed.
- [ ] DXY/XAU timestamp sudah align.
- [ ] Macro timestamp sudah align.
- [ ] 57 feature selection dilakukan berdasarkan validation.
- [ ] Test benar-benar belum disentuh.
- [ ] Threshold sudah dibekukan sebelum test.
- [ ] Tidak ada retraining saat forward test.
- [ ] LightGBM/XGBoost/RF diuji secara fair.
- [ ] Confidence tidak disebut probability of profit.
- [ ] Klaim calibration didukung metode calibration.
- [ ] Semua angka feature count sama di seluruh bab.
- [ ] M5 sudah dihapus dari penelitian utama.
- [ ] Post-Trade Scenario Evaluator bukan fokus novelty.
- [ ] Tidak ada klaim zero-latency.
- [ ] Forward-testing sample size dan periode telah ditentukan secara jelas.

---

# 36. Putusan Audit

## Status:

> **LAYAK DITERUSKAN DENGAN REVISI METODOLOGIS**

Bukan:

> “proyek salah”.

Dan bukan juga:

> “semua sudah benar”.

Kesimpulan audit saya:

### Secara konsep
**Kuat.**

### Secara ruang lingkup
**Masih bisa dipertahankan dalam judul.**

### Secara metodologi
**Masih membutuhkan audit causal yang serius.**

### Secara statistik
**Klaim confidence/calibration harus diperketat.**

### Secara engineering
**57 fitur dapat menjadi final feature set, tetapi harus dipilih secara valid.**

### Secara skripsi S1
**Lebih baik mengecilkan fokus ke model + evaluasi, bukan menambah fitur sistem seperti retraining dan continuous learning.**

### Risiko terbesar penelitian
Bukan LightGBM-nya.

Risiko terbesar adalah:

> **lookahead bias, selection bias pada threshold/feature selection, dan overclaim terhadap probabilitas/confidence.**

Jika tiga masalah tersebut dapat diselesaikan, penelitian ini jauh lebih mudah dipertahankan di depan dosen penguji.

---

# 37. Instruksi untuk Peneliti B

Peneliti B diminta menjawab seluruh pertanyaan kritis dalam dokumen ini secara eksplisit, terutama:

1. mengapa 57 fitur ditambahkan;
2. bagaimana 57 dipilih tanpa test leakage;
3. bagaimana setiap fitur dibentuk secara causal;
4. bagaimana OB dan FVG diketahui pada timestamp tertentu;
5. bagaimana RRR dan Clearance dihitung;
6. apa sebenarnya arti probability/confidence;
7. bagaimana threshold dipilih;
8. apakah probabilitas benar-benar calibrated;
9. apakah benchmark fair;
10. apakah frozen model benar-benar digunakan selama forward testing.

Jawaban Peneliti B harus berupa **formula, contoh timestamp, pseudo-code, atau bukti eksperimen** jika memungkinkan, bukan hanya alasan konseptual.
