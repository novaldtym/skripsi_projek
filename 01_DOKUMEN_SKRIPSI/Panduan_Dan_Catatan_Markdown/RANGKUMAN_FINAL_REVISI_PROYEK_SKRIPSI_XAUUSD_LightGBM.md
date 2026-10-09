# RANGKUMAN FINAL & REVISI PROYEK SKRIPSI
## Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi

Dokumen ini merupakan rangkuman terpadu kondisi proyek setelah dilakukan penyederhanaan ruang lingkup penelitian, penyelarasan Bab I, serta penetapan bahwa model yang digunakan pada tahap *forward testing* adalah **model LightGBM versi final/tuned yang dibekukan (*frozen model*) tanpa retraining**.

---

# A. ARAH FINAL PENELITIAN

## A.1 Fokus utama

Penelitian difokuskan sebagai penelitian **Machine Learning / Financial Time-Series Classification** pada Program Studi Informatika.

Fokus utama bukan membangun platform trading yang sangat kompleks, melainkan:

1. membangun data prediktif dari beberapa sumber informasi;
2. menerapkan dan mengoptimalkan LightGBM untuk klasifikasi probabilitas arah harga XAUUSD;
3. membandingkan LightGBM dengan XGBoost dan Random Forest;
4. menguji penerapan model final melalui *forward testing* MetaTrader 5.

## A.2 Objek

Objek penelitian adalah XAUUSD sebagai instrumen emas terhadap dolar Amerika Serikat pada perdagangan intraday.

## A.3 Timeframe final

- **M15** = timeframe operasional/prediksi utama.
- **H1** = sumber informasi tren.
- **H4** = sumber informasi tren.
- **M5 dihapus dari ruang lingkup penelitian final.** Tidak ada lagi eksperimen scalping 25 menit.

## A.4 Target prediksi

Target berupa klasifikasi biner arah harga pada horizon **75 menit**, yaitu lima candle M15.

- Label `1` = `Close(t+5) > Close(t)` → arah naik (*bullish*).
- Label `0` = `Close(t+5) <= Close(t)` → arah turun (*bearish*).

Definisi tersebut harus dipakai konsisten pada Bab I, Bab III, kode, dan Bab IV.

## A.5 Model

- **Model utama:** LightGBM Classifier.
- **Model pembanding:** XGBoost dan Random Forest.
- Logistic Regression **tidak digunakan** dalam ruang lingkup final, kecuali kemudian diwajibkan oleh dosen.

## A.6 Model final dan retraining

Model final yang digunakan untuk *forward testing* adalah **LightGBM versi tuned/final** yang telah dipilih setelah proses pelatihan dan optimasi.

Model tersebut kemudian disimpan dan digunakan sebagai **frozen model** selama pengujian.

Tidak ada:

- automated retraining;
- online learning;
- continuous learning;
- auto-blacklist skenario;
- perubahan bobot model akibat hasil transaksi live.

Tujuannya agar objek yang diuji tetap merupakan model yang sama dari awal hingga akhir tahap *forward testing*.

---

# B. CATATAN PENTING TENTANG HASIL LIGHTGBM FINAL

Pada rangkuman proyek awal terdapat *LightGBM baseline* dengan performa uji sekitar **50,8% akurasi**, sedangkan versi tuned menghasilkan performa yang lebih baik pada analisis berbasis *confidence threshold*.

Hasil yang tercatat menunjukkan:

| Threshold Confidence | Directional Accuracy M15 | Coverage |
|---|---:|---:|
| ≥ 50% | 54,20% | 100,0% |
| ≥ 55% | 56,95% | 59,5% |
| ≥ 58% | 60,13% | 38,6% |
| ≥ 60% | 63,08% | 28,1% |
| **≥ 65%** | **73,97%** | **13,5%** |
| ≥ 70% | 82,24% | 9,2% |
| ≥ 75% | 87,89% | 7,4% |

## Hal yang harus ditulis dengan benar

Pernyataan bahwa model tuned “membuat skor confidence menjadi 73% dari 50,8%” perlu diperbaiki secara istilah.

**73,97% bukan nilai confidence model.** Angka tersebut adalah **directional accuracy pada subset prediksi yang memiliki confidence ≥65%**.

Sementara angka sekitar **50,8%** merupakan akurasi uji dari konfigurasi baseline LightGBM pada hasil eksperimen yang terdokumentasi.

Jadi kalimat akademik yang lebih tepat adalah:

> **“Optimasi konfigurasi LightGBM menghasilkan peningkatan kemampuan prediksi dibandingkan konfigurasi baseline. Pada evaluasi berbasis confidence threshold, prediksi dengan tingkat keyakinan ≥65% mencapai directional accuracy sebesar 73,97% pada horizon 75 menit, dibandingkan akurasi sekitar 50,8% pada hasil pengujian baseline.”**

Jangan menyatakan bahwa model “menghasilkan confidence 73,97%”. Confidence adalah nilai probabilitas keluaran model, sedangkan 73,97% pada tabel tersebut adalah akurasi aktual terhadap subset prediksi yang lolos threshold.

## Klaim kalibrasi

Kata **“terkalibrasi”** jangan digunakan sebagai klaim utama kecuali penelitian benar-benar melakukan metode *probability calibration* seperti Platt scaling atau isotonic calibration dan mengevaluasi calibration curve/Brier score/ECE secara formal.

Untuk versi penelitian saat ini, istilah yang lebih aman adalah:

- estimasi probabilitas;
- confidence score;
- evaluasi confidence threshold;
- hubungan antara threshold dan directional accuracy.

---

# C. ARSITEKTUR PENELITIAN FINAL

```text
DATA XAUUSD M15
       │
       ├── Data tren H1
       ├── Data tren H4
       ├── Data DXY
       └── Kalender NFP / CPI / FOMC
       │
       ▼
PREPROCESSING & TIMESTAMP ALIGNMENT
       │
       ▼
FEATURE ENGINEERING
44 FITUR PREDIKTIF
       │
       ▼
LABELING
Close(t+5) vs Close(t)
Horizon = 75 menit
       │
       ▼
CHRONOLOGICAL SPLIT
Train / Validation / Test
       │
       ▼
LIGHTGBM TUNING
       │
       ├── Model final LightGBM (frozen)
       ├── XGBoost
       └── Random Forest
       │
       ▼
PROBABILITY OUTPUT
P(Up), P(Down)
       │
       ▼
CONFIDENCE THRESHOLD
       │
       ▼
STATISTICAL EVALUATION
ROC-AUC / Log Loss / Precision / Recall / F1
       │
       ▼
FORWARD TESTING
MetaTrader 5
       │
       ▼
TRADING METRICS
Win Rate / Profit Factor / Drawdown / ROI
```

---

# D. MASTER RUANG LINGKUP FITUR

Penelitian menggunakan **44 fitur prediktif** yang secara konseptual berasal dari beberapa kelompok informasi:

1. geometri candlestick;
2. Smart Money Concepts (SMC);
3. indikator teknikal, momentum, dan volatilitas;
4. dinamika volume;
5. persistensi momentum;
6. tren multi-timeframe H1/H4;
7. Indeks Dolar AS (DXY);
8. informasi kalender makroekonomi.

## Catatan konsistensi yang wajib diselesaikan

Dokumen proyek sebelumnya memiliki ketidaksesuaian pembagian jumlah fitur:

- diagram: 3 + 16 + 10 + 7 + 8 = 44;
- bagian lain menyebut kelompok terakhir sebagai 18 fitur.

Karena itu, sebelum Bab III dikunci, harus dibuat satu **Master List 44 Fitur** yang menjadi satu-satunya referensi resmi.

Format yang disarankan:

| No | Nama Fitur | Kelompok | Timeframe | Rumus/Logika | Sumber Data | Risiko Lookahead |
|---:|---|---|---|---|---|---|
| 1 | ... | ... | ... | ... | ... | ... |
| ... | ... | ... | ... | ... | ... | ... |
| 44 | ... | ... | ... | ... | ... | ... |

Jumlah akhir setiap kelompok harus benar-benar menjumlah **44**.

---

# E. PRINSIP PENCEGAHAN LOOKAHEAD BIAS

Semua fitur pada waktu `t` hanya boleh menggunakan informasi yang sudah tersedia pada waktu `t`.

Karena target menggunakan `Close(t+5)`, nilai masa depan tersebut hanya digunakan untuk membentuk label, bukan sebagai masukan fitur.

Contoh prinsip:

```text
Informasi tersedia sampai candle t
              │
              ▼
        Feature vector X_t
              │
              ▼
        Model prediction
              │
              ▼
Target Y_t = Close(t+5) vs Close(t)
```

Untuk data H1/H4, DXY, dan kalender berita, penyelarasan timestamp harus memastikan bahwa informasi yang belum tersedia pada saat prediksi tidak ikut masuk ke fitur.

---

# F. MODEL LIGHTGBM FINAL

## F.1 Peran LightGBM

LightGBM menjadi model utama karena penelitian berfokus pada algoritma *gradient boosting decision tree* untuk data tabular multisumber.

Konsep yang dipertahankan:

- leaf-wise tree growth;
- histogram-based learning;
- pembobotan kelas seimbang (*balanced class weights*);
- hyperparameter tuning sistematis.

## F.2 Konfigurasi tuned yang terdokumentasi

Versi proyek saat ini mencatat konfigurasi tuned:

```text
n_estimators = 800
learning_rate = 0.015
max_depth = 5
num_leaves = 24
min_child_samples = 50
reg_alpha = 0.1
reg_lambda = 1.0
class_weight = 'balanced'
```

Konfigurasi final ini harus disesuaikan dengan hasil eksperimen final jika nanti terdapat perubahan setelah validasi ulang.

## F.3 Baseline vs tuned

Rangkuman proyek mencatat baseline LightGBM dengan konfigurasi default dan tuned LightGBM dengan konfigurasi hasil optimasi.

Tujuan pembahasan:

- menunjukkan perbedaan performa baseline dan tuned;
- menjelaskan bahwa tuning merupakan bagian dari proses pemodelan;
- tidak menyatakan bahwa setiap parameter tertentu sendirian menyebabkan peningkatan kecuali telah diuji secara terkontrol.

Kalimat aman:

> “Hasil pengujian menunjukkan bahwa konfigurasi tuned memberikan performa yang lebih baik dibandingkan konfigurasi baseline pada skema pengujian yang digunakan.”

Hindari:

> “Balanced class weights membuktikan secara tunggal menyebabkan peningkatan performa.”

karena untuk klaim kausal tersebut diperlukan eksperimen isolasi parameter.

---

# G. CONFIDENCE THRESHOLD

Confidence tetap digunakan sebagai **mekanisme penyaringan sinyal**, bukan sebagai bagian dari algoritma LightGBM.

Model menghasilkan:

```text
P(Up)
P(Down)
```

Confidence dapat didefinisikan sebagai probabilitas kelas yang lebih tinggi:

```text
Confidence = max(P(Up), P(Down))
```

Pada penelitian final, threshold digunakan dengan aturan yang telah ditetapkan sebelum pengujian.

## Rekomendasi ruang lingkup

Jangan lagi menjadikan **Adaptive Multi-Zone Confidence Threshold 58%–70%** sebagai komponen utama penelitian.

Gunakan satu ambang selektif utama, misalnya:

```text
Confidence >= 65%
```

Nilai threshold tersebut kemudian dianalisis pada tahap evaluasi melalui hubungan antara:

- threshold;
- jumlah sinyal/coverage;
- directional accuracy.

Threshold tidak boleh diubah-ubah setelah melihat hasil forward testing karena dapat menyebabkan bias evaluasi.

---

# H. PEMISAHAN MODEL ML DAN BOT

## Lapisan 1 — Machine Learning

LightGBM hanya bertugas:

- menerima 44 fitur;
- menghasilkan probabilitas arah.

Model tidak bertugas menentukan:

- lot;
- saldo;
- stop loss;
- take profit;
- manajemen risiko.

## Lapisan 2 — Execution/Rule Layer

Sistem MetaTrader 5 dapat menerapkan aturan:

- confidence threshold;
- filter tren H1;
- pembatasan berita bila digunakan;
- ATR Stop-Loss;
- Risk-to-Reward;
- batas kerugian harian;
- aturan cooldown bila memang dipertahankan dalam implementasi.

Aturan tersebut merupakan **parameter sistem eksekusi**, bukan fitur yang dipelajari oleh LightGBM.

---

# I. FORWARD TESTING FINAL

Forward testing digunakan untuk melihat bagaimana model yang sudah ditetapkan bekerja ketika diterapkan pada kondisi pasar berjalan.

## Prinsip penting

Model yang dipakai harus tetap:

> **Frozen Model — no retraining.**

Artinya:

```text
Training + tuning
       │
       ▼
Final LightGBM
       │
       ▼
Simpan model
       │
       ▼
Forward Testing
       │
       └── tidak ada retraining
```

## Metrik yang dapat digunakan

### Metrik klasifikasi

- ROC-AUC
- Log Loss
- Precision
- Recall
- F1-Score

### Metrik forward testing

- Win Rate
- Profit Factor
- Maximum Drawdown
- Return on Investment (ROI)

Forward testing berfungsi sebagai pengujian penerapan model, bukan sebagai sarana memperbarui model.

---

# J. KOMPONEN YANG DIHAPUS DARI VERSI FINAL

Agar penelitian tidak terlalu melebar, komponen berikut tidak lagi menjadi fokus penelitian:

1. M5 / eksperimen scalping 25 menit.
2. Adaptive Multi-Zone Confidence Threshold 58%–70% sebagai sistem adaptif utama.
3. Post-Trade Scenario Evaluator Engine sebagai objek penelitian.
4. Continuous learning.
5. Automated retraining.
6. Auto-blacklist skenario.
7. Logistic Regression sebagai model pembanding.
8. GUI monitoring PyWebView/Flask sebagai objek utama penelitian.
9. Klaim “zero latency” atau “zero-delay”.
10. Klaim bahwa sistem “menghilangkan bias psikologis” pengguna.

Komponen yang masih dapat digunakan sebagai implementasi pendukung tidak perlu diangkat menjadi rumusan masalah tersendiri.

---

# K. BAB I FINAL — VERSI REVISI

## 1.1 Latar Belakang Masalah

Kontrak derivatif *Contract for Difference* (CFD) emas terhadap dolar Amerika Serikat (XAUUSD) merupakan salah satu instrumen finansial yang memiliki aktivitas perdagangan tinggi dan karakteristik pergerakan harga yang dinamis. Sebagai aset yang banyak digunakan dalam diversifikasi dan perlindungan terhadap ketidakpastian ekonomi, harga emas dipengaruhi oleh berbagai faktor yang berasal dari kondisi pasar keuangan global. Pada interval *intraday*, pergerakan XAUUSD dapat menunjukkan volatilitas tinggi, pola yang tidak linear, serta tingkat derau yang besar sehingga hubungan antara kondisi pasar saat ini dan arah pergerakan harga berikutnya menjadi tidak sederhana (Al-Thaqeb *et al.*, 2026; Kazemdehbashi, 2026).

Dalam praktik perdagangan, analisis teknikal konvensional masih banyak digunakan sebagai dasar identifikasi arah pergerakan harga. Indikator seperti *Relative Strength Index* (RSI), *Moving Average Convergence Divergence* (MACD), *Bollinger Bands*, dan *Simple Moving Average* (SMA) umumnya dibentuk berdasarkan informasi historis harga. Sifat tersebut menyebabkan sebagian indikator bersifat reaktif terhadap perubahan kondisi pasar yang telah terjadi. Pada kondisi volatilitas tinggi atau perubahan momentum secara tiba-tiba, penggunaan indikator secara terpisah dapat menghasilkan sinyal yang kurang konsisten dan membutuhkan interpretasi tambahan dari pengguna.

Selain indikator teknikal, pendekatan *Smart Money Concepts* (SMC) berkembang sebagai salah satu metode analisis *price action* yang berfokus pada struktur pergerakan harga dan area likuiditas. Konsep seperti *Order Block* (OB), *Fair Value Gap* (FVG), *Break of Structure* (BOS), *Change of Character* (CHoCH), dan *Liquidity Sweep* digunakan untuk merepresentasikan karakteristik tertentu dari struktur pasar. Meskipun konsep tersebut dapat diterjemahkan ke dalam aturan kuantitatif, penerapannya secara manual masih bergantung pada interpretasi pengguna. Kondisi tersebut menunjukkan adanya peluang untuk mengubah informasi struktur harga menjadi variabel prediktif yang dapat diproses secara sistematis menggunakan pendekatan *machine learning*.

Perkembangan *machine learning* memberikan pendekatan alternatif untuk mempelajari hubungan non-linear antara sejumlah variabel prediktif dan arah pergerakan harga. Berbagai algoritma seperti *Support Vector Machine* (SVM), *Random Forest*, *Artificial Neural Network* (ANN), dan XGBoost telah digunakan dalam penelitian terkait prediksi instrumen finansial (Ben Jabeur *et al.*, 2024; Gono *et al.*, 2023; Nasrul *et al.*, 2026). Namun, pemanfaatan algoritma *machine learning* pada data finansial tetap menghadapi tantangan berupa nonstasioneritas, derau pasar, dan perubahan karakteristik data dari waktu ke waktu.

Salah satu aspek yang perlu diperhatikan adalah formulasi target prediksi. Sejumlah penelitian terdahulu menggunakan regresi untuk memperkirakan harga nominal pada periode berikutnya (Gono *et al.*, 2023; Nasrul *et al.*, 2026; Li, 2023). Pendekatan tersebut berbeda dengan kebutuhan penelitian ini yang berfokus pada arah pergerakan harga. Prediksi diarahkan menjadi permasalahan klasifikasi biner untuk menentukan probabilitas pergerakan naik atau turun pada horizon waktu tertentu. Pendekatan probabilistik tersebut memungkinkan hasil prediksi tidak hanya berupa kelas arah, tetapi juga nilai probabilitas yang dapat digunakan sebagai dasar penyaringan sinyal.

Permasalahan berikutnya berkaitan dengan keterbatasan penggunaan satu sumber informasi dalam membangun model prediksi. Pergerakan XAUUSD tidak hanya ditentukan oleh data harga XAUUSD itu sendiri, tetapi juga dapat berhubungan dengan kondisi pasar lain, khususnya Indeks Dolar AS (DXY), serta kondisi makroekonomi Amerika Serikat. Perubahan DXY dapat memberikan informasi tambahan mengenai kondisi pasar dolar, sedangkan informasi jadwal rilis indikator ekonomi berdampak tinggi seperti Non-Farm Payrolls (NFP), Consumer Price Index (CPI), dan keputusan Federal Open Market Committee (FOMC) dapat digunakan untuk merepresentasikan periode ketika pasar berpotensi mengalami perubahan volatilitas yang signifikan (Nguyen *et al.*, 2025; KC *et al.*, 2024; Sayegh & Accary, 2026).

Informasi dari *timeframe* yang berbeda juga dapat digunakan untuk memberikan konteks terhadap pergerakan harga pada *timeframe* operasional. Dalam penelitian ini, M15 digunakan sebagai *timeframe* utama untuk prediksi, sedangkan H1 dan H4 digunakan sebagai sumber informasi tren dengan tujuan memberikan konteks pergerakan pada skala waktu yang lebih tinggi. Dengan demikian, informasi yang digunakan model tidak hanya berasal dari kondisi *intraday* pada M15, tetapi juga mencakup struktur tren pada H1 dan H4 serta informasi eksternal berupa DXY dan jadwal berita makroekonomi.

Berdasarkan permasalahan tersebut, penelitian ini menerapkan algoritma *Light Gradient Boosting Machine* (LightGBM) untuk memprediksi probabilitas arah pergerakan harga XAUUSD. LightGBM merupakan algoritma *gradient boosting decision tree* yang sesuai untuk pengolahan data tabular dengan sejumlah fitur prediktif. Mekanisme *leaf-wise tree growth* dan penggunaan *histogram-based learning* mendukung proses pembentukan model yang efisien pada data tabular (Ke *et al.*, 2017). Dalam penelitian ini, LightGBM digunakan sebagai model utama dan dibandingkan dengan XGBoost serta *Random Forest* menggunakan dataset dan skema pengujian yang sama.

Model dibangun menggunakan 44 fitur prediktif yang berasal dari beberapa sumber informasi, yaitu geometri *candlestick* dan momentum M15, struktur pasar berbasis SMC, indikator teknikal, dinamika volume, informasi tren H1 dan H4, pergerakan DXY, serta penanda jadwal rilis berita makroekonomi. Seluruh fitur dibentuk hanya berdasarkan informasi yang tersedia pada saat prediksi untuk menjaga pemisahan antara informasi masa lalu dan target masa depan serta mencegah terjadinya *lookahead bias*. Target penelitian berupa arah pergerakan harga lima *candle* M15 ke depan atau horizon 75 menit, dengan kelas naik dan turun berdasarkan perbandingan harga penutupan pada waktu prediksi dan harga penutupan pada akhir horizon tersebut.

Selain pengujian statistik menggunakan metrik klasifikasi, hasil probabilitas model digunakan sebagai dasar penyaringan sinyal dengan ambang keyakinan yang telah ditetapkan sebelum proses pengujian. Penerapan tersebut kemudian diintegrasikan ke dalam sistem pengujian berbasis MetaTrader 5 untuk memperoleh gambaran performa model ketika digunakan pada kondisi pasar yang berjalan. Pengujian dilakukan menggunakan model yang telah dilatih dan ditetapkan sebelumnya tanpa proses *retraining* selama periode *forward testing*, sehingga model yang dievaluasi tetap sama sepanjang tahap pengujian.

Dengan pendekatan tersebut, penelitian ini diarahkan untuk menghasilkan model prediksi probabilitas arah XAUUSD yang memanfaatkan integrasi data *multi-timeframe*, Indeks Dolar AS (DXY), dan informasi makroekonomi. Penelitian selanjutnya mengevaluasi kemampuan LightGBM melalui metrik statistik klasifikasi dan membandingkannya dengan XGBoost serta *Random Forest*, kemudian menguji penerapan model tersebut melalui *forward testing* pada MetaTrader 5. Dengan demikian, penelitian diharapkan dapat memberikan gambaran empiris mengenai penerapan LightGBM untuk klasifikasi probabilitas arah harga XAUUSD berbasis informasi multisumber.

---

## 1.2 Rumusan Masalah

1. Sejauh mana arsitektur *Multi-Source Feature Fusion* yang mengintegrasikan 44 fitur dari data XAUUSD *timeframe* M15, tren *multi-timeframe* H1/H4, Indeks Dolar AS (DXY), dan informasi makroekonomi dapat diterapkan untuk membangun data prediktif tanpa menimbulkan *lookahead bias*?

2. Sejauh mana penerapan dan optimasi algoritma LightGBM dapat menghasilkan estimasi probabilitas arah pergerakan harga XAUUSD pada horizon 75 menit, serta bagaimana kinerjanya dibandingkan dengan algoritma XGBoost dan *Random Forest* berdasarkan metrik evaluasi klasifikasi?

3. Sejauh mana model LightGBM yang telah ditetapkan dengan ambang keyakinan tertentu dapat mempertahankan kinerja prediksi ketika diterapkan pada *forward testing* melalui MetaTrader 5 berdasarkan metrik klasifikasi dan metrik kinerja perdagangan?

### Catatan

Rumusan masalah dibuat dalam bentuk **pertanyaan substantif tanpa menggunakan tanda tanya**, sesuai arahan revisi. Ketiga rumusan dirancang sebagai tiga fokus utama:

1. data dan fitur;
2. model dan optimasi;
3. evaluasi dan penerapan.

---

## 1.3 Batasan Masalah

Agar penelitian tetap terfokus dan sesuai dengan ruang lingkup keilmuan Teknik Informatika, batasan masalah dalam penelitian ini ditetapkan sebagai berikut:

1. Objek penelitian dibatasi pada pasangan harga emas terhadap dolar Amerika Serikat (XAUUSD) yang digunakan untuk memprediksi arah pergerakan harga dalam kondisi pasar intraday.

2. Data utama yang digunakan merupakan data historis *candlestick* XAUUSD yang diperoleh melalui MetaTrader 5 sebanyak 50.000 *candle* pada *timeframe* M15 sebagai *timeframe* operasional. Informasi *multi-timeframe* H1 dan H4 digunakan sebagai fitur konfirmasi tren, sedangkan data pendukung berasal dari Indeks Dolar AS (DXY) dan kalender berita makroekonomi berdampak tinggi yang mencakup NFP, CPI, dan FOMC.

3. Variabel masukan dibatasi pada 44 fitur prediktif yang mencakup informasi *candlestick*, struktur harga berbasis *Smart Money Concepts* (SMC), indikator momentum dan volatilitas, dinamika volume, persistensi pergerakan harga, tren *multi-timeframe* H1/H4, pergerakan DXY, serta informasi jadwal rilis berita makroekonomi. Seluruh fitur dibentuk berdasarkan informasi yang tersedia pada saat prediksi untuk mencegah *lookahead bias*.

4. Algoritma utama yang digunakan adalah *Light Gradient Boosting Machine* (LightGBM), sedangkan XGBoost dan *Random Forest* digunakan sebagai algoritma pembanding dalam tahap evaluasi kinerja model.

5. Target prediksi berupa klasifikasi biner arah pergerakan harga XAUUSD pada horizon 75 menit atau lima *candle* M15. Label 1 menunjukkan bahwa harga penutupan pada waktu t+5 lebih tinggi daripada harga penutupan pada waktu t, sedangkan label 0 menunjukkan kondisi sebaliknya. Luaran model berupa probabilitas kelas yang digunakan sebagai dasar penyaringan sinyal dengan ambang keyakinan yang ditetapkan sebelum pengujian.

6. Pengujian penerapan model dilakukan melalui *forward testing* menggunakan MetaTrader 5 dengan konfigurasi manajemen risiko yang ditetapkan secara tetap sebelum pengujian, termasuk ukuran posisi, *stop-loss*, *take-profit*, rasio *Risk-to-Reward*, serta batas kerugian harian. Model yang telah dilatih tidak mengalami proses *retraining* selama tahap pengujian.

7. Implementasi penelitian menggunakan bahasa pemrograman Python dengan pustaka utama yang meliputi LightGBM, scikit-learn, MetaTrader5, pandas, dan NumPy.

---

## 1.4 Tujuan Penelitian

Tujuan yang hendak dicapai dalam penelitian skripsi ini adalah:

1. Menerapkan algoritma *Light Gradient Boosting Machine* (LightGBM) untuk memprediksi probabilitas arah pergerakan harga XAUUSD pada *timeframe* M15 dengan memanfaatkan integrasi fitur teknikal, *multi-timeframe* H1/H4, Indeks Dolar AS (DXY), dan informasi berita makroekonomi secara terstruktur serta tanpa kebocoran data masa depan (*lookahead bias*).

2. Menganalisis kemampuan model LightGBM setelah proses optimasi dalam menghasilkan estimasi probabilitas arah pergerakan harga XAUUSD pada horizon waktu 75 menit serta membandingkan kinerjanya dengan algoritma XGBoost dan *Random Forest* berdasarkan metrik evaluasi klasifikasi.

3. Mengevaluasi kinerja model LightGBM menggunakan ambang keyakinan yang telah ditetapkan dan menguji penerapannya melalui *forward testing* pada MetaTrader 5 berdasarkan metrik klasifikasi dan metrik kinerja perdagangan.

---

## 1.5 Manfaat Penelitian

### 1. Manfaat Teoritis

1. Memberikan referensi dalam penerapan algoritma LightGBM untuk permasalahan klasifikasi probabilitas arah pergerakan harga pada data deret waktu finansial yang memiliki karakteristik dinamis dan nonstasioner.

2. Memberikan gambaran mengenai penggunaan kombinasi fitur teknikal, *multi-timeframe*, Indeks Dolar AS (DXY), dan informasi makroekonomi dalam membangun model prediksi arah harga XAUUSD.

3. Menjadi referensi bagi penelitian selanjutnya dalam membandingkan kinerja algoritma *gradient boosting* dan algoritma *ensemble tree-based* pada permasalahan prediksi arah harga instrumen finansial.

### 2. Manfaat Praktis (Praktisi dan Pengembang Sistem)

1. Menyediakan model prediksi berbasis *machine learning* yang dapat memberikan estimasi probabilitas arah pergerakan harga XAUUSD sebagai informasi pendukung dalam proses pengambilan keputusan perdagangan secara lebih objektif dan terukur.

2. Memberikan contoh penerapan integrasi data harga XAUUSD, informasi *multi-timeframe*, Indeks Dolar AS (DXY), dan informasi makroekonomi ke dalam sistem prediksi berbasis LightGBM yang dapat diuji secara terstruktur.

3. Menjadi referensi bagi pengembang sistem dalam menerapkan hasil prediksi model *machine learning* ke dalam proses pengujian perdagangan melalui integrasi dengan MetaTrader 5 dan penerapan aturan manajemen risiko yang telah ditentukan.

---

## 1.6 Keaslian Penelitian dan *Research Gap*

Keaslian penelitian ini didasarkan pada penelusuran dan perbandingan terhadap penelitian terdahulu yang membahas penerapan *machine learning* pada prediksi harga dan arah pergerakan instrumen finansial, khususnya emas. Berdasarkan kajian tersebut, penelitian terdahulu memiliki variasi dalam pemilihan algoritma, sumber data, *timeframe*, variabel prediktor, dan bentuk target prediksi. Sebagian penelitian menggunakan data harga historis sebagai sumber utama, sedangkan integrasi informasi lintas *timeframe*, hubungan dengan Indeks Dolar AS (DXY), dan informasi jadwal rilis berita makroekonomi belum selalu digunakan secara bersamaan dalam satu model prediksi.

*Research gap* yang menjadi dasar penelitian ini adalah kebutuhan akan model prediksi arah harga XAUUSD yang memanfaatkan informasi dari beberapa sumber secara terintegrasi, yaitu data teknikal pada *timeframe* M15, informasi tren pada *timeframe* H1 dan H4, pergerakan Indeks Dolar AS (DXY), serta informasi jadwal rilis berita makroekonomi berdampak tinggi. Integrasi tersebut digunakan sebagai masukan dalam algoritma LightGBM untuk menghasilkan probabilitas arah pergerakan harga pada horizon waktu 75 menit.

Keaslian penelitian terletak pada penerapan integrasi berbagai sumber fitur tersebut dalam satu model LightGBM untuk permasalahan klasifikasi probabilitas arah harga XAUUSD, serta evaluasi kinerja model menggunakan pengujian yang sama dengan algoritma pembanding XGBoost dan *Random Forest*. Dengan demikian, penelitian tidak hanya mengevaluasi kemampuan model dalam melakukan klasifikasi arah harga, tetapi juga menguji penerapannya melalui *forward testing* pada kondisi pengujian yang telah ditentukan.

### Catatan penggunaan klaim novelty

Hindari kalimat absolut seperti:

> “Belum ada penelitian yang melakukan ...”

kecuali tabel penelitian terdahulu sudah membuktikan pernyataan tersebut secara kuat.

Gunakan formulasi:

> “Berdasarkan penelusuran literatur yang dilakukan, ...”

atau:

> “Penelitian terdahulu yang ditinjau belum menunjukkan integrasi ... dalam konfigurasi yang sama.”

---

## 1.7 Tahapan Penelitian

Penelitian skripsi ini dilaksanakan melalui tahapan yang sistematis dengan mengadaptasi *Cross-Industry Standard Process for Data Mining* (CRISP-DM) sesuai dengan kebutuhan penelitian prediksi arah harga XAUUSD. Tahapan penelitian yang dilakukan adalah sebagai berikut:

### 1. Fase Studi Literatur dan Identifikasi Masalah

Melakukan kajian terhadap literatur yang berkaitan dengan karakteristik pergerakan harga XAUUSD, algoritma *machine learning* berbasis *tree ensemble* khususnya LightGBM, XGBoost, dan *Random Forest*, penggunaan data *multi-timeframe*, hubungan XAUUSD dan DXY, serta informasi makroekonomi. Tahap ini juga dilakukan untuk mengidentifikasi *research gap* dan menentukan pendekatan penelitian.

### 2. Fase Pengumpulan Data (*Data Collection*)

Mengumpulkan data historis *candlestick* XAUUSD melalui MetaTrader 5 pada *timeframe* M15 sebagai *timeframe* operasional serta H1 dan H4 sebagai sumber informasi tren. Data pendukung berupa data Indeks Dolar AS (DXY) dan jadwal rilis berita makroekonomi berdampak tinggi yang meliputi NFP, CPI, dan FOMC turut dikumpulkan untuk digunakan sebagai sumber fitur prediktif.

### 3. Fase Pra-pengolahan Data dan Rekayasa Fitur (*Data Preparation & Feature Engineering*)

Melakukan pembersihan data, penanganan nilai hilang, penyelarasan *timestamp* antar-sumber data, serta pembentukan 44 fitur prediktif yang berasal dari data teknikal, *multi-timeframe*, DXY, dan informasi makroekonomi. Selanjutnya dilakukan pembentukan label biner arah pergerakan harga dengan horizon 75 menit atau lima *candle* M15. Seluruh proses pembentukan fitur dan label dilakukan berdasarkan informasi yang tersedia pada waktu prediksi untuk mencegah *lookahead bias*. Dataset kemudian dibagi secara kronologis menjadi data latih, validasi, dan data uji.

### 4. Fase Pemodelan dan Optimasi (*Modeling*)

Melatih model LightGBM menggunakan data latih dan melakukan optimasi *hyperparameter* berdasarkan data validasi. Model XGBoost dan *Random Forest* juga dilatih menggunakan pembagian data dan fitur yang sama sebagai model pembanding. Setelah model final ditetapkan, model tersebut digunakan untuk tahap pengujian tanpa dilakukan *retraining* selama proses evaluasi dan *forward testing*.

### 5. Fase Evaluasi Model

Mengevaluasi kemampuan model LightGBM dan model pembanding berdasarkan metrik klasifikasi yang meliputi ROC-AUC, *Log Loss*, *Precision*, *Recall*, dan F1-Score. Selain itu, dilakukan analisis terhadap hubungan antara confidence threshold, jumlah sinyal yang dipilih, dan directional accuracy.

### 6. Fase Forward Testing dan Dokumentasi

Menerapkan model yang telah ditetapkan pada proses *forward testing* melalui integrasi dengan MetaTrader 5 berdasarkan aturan eksekusi dan manajemen risiko yang telah ditentukan sebelumnya. Hasil prediksi dan transaksi dicatat untuk memperoleh metrik kinerja pengujian seperti *Win Rate*, *Profit Factor*, *Maximum Drawdown*, dan *Return on Investment*. Seluruh hasil penelitian kemudian dianalisis dan didokumentasikan dalam laporan skripsi.

---

## 1.8 Sistematika Penulisan

### 1. BAB I PENDAHULUAN

Bab ini memuat latar belakang masalah penelitian terkait prediksi arah pergerakan harga XAUUSD, identifikasi *research gap*, rumusan masalah, batasan masalah, tujuan penelitian, manfaat penelitian, keaslian penelitian, tahapan penelitian, serta sistematika penulisan laporan skripsi.

### 2. BAB II TINJAUAN PUSTAKA

Bab ini membahas landasan teori dan penelitian terdahulu yang berkaitan dengan XAUUSD, Indeks Dolar AS (DXY), konsep analisis *multi-timeframe*, informasi makroekonomi, rekayasa fitur data finansial, algoritma LightGBM, XGBoost, *Random Forest*, klasifikasi probabilitas, serta metrik evaluasi yang digunakan dalam penelitian.

### 3. BAB III METODE PENELITIAN

Bab ini menjelaskan metode penelitian yang digunakan, meliputi sumber dan proses pengumpulan data, pra-pengolahan data, pembentukan label, rekayasa 44 fitur prediktif, pembagian dataset secara kronologis, pembangunan dan optimasi model LightGBM, model pembanding, mekanisme prediksi probabilitas, serta rancangan *forward testing* melalui MetaTrader 5 dan manajemen risiko.

### 4. BAB IV HASIL DAN PEMBAHASAN

Bab ini menyajikan hasil pra-pengolahan dan rekayasa fitur, hasil pelatihan dan optimasi model, hasil evaluasi LightGBM dibandingkan dengan XGBoost dan *Random Forest*, analisis contribution/feature importance yang benar-benar didukung metode pengujian, analisis confidence threshold, serta hasil *forward testing* berdasarkan metrik klasifikasi dan metrik kinerja perdagangan yang telah ditentukan.

### 5. BAB V KESIMPULAN DAN SARAN

Bab ini memuat kesimpulan berdasarkan hasil penelitian yang menjawab seluruh rumusan masalah serta saran untuk pengembangan penelitian selanjutnya.

---

# L. HASIL EKSPERIMEN YANG SUDAH TERDOKUMENTASI

## L.1 Perbandingan model pada dataset uji

Rangkuman proyek terdokumentasi mencatat hasil berikut:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC | Waktu Training |
|---|---:|---:|---:|---:|---:|---:|
| LightGBM Tuned | 53,07% | 51,73% | 53,30% | 52,50% | 55,67% | 3,761 s |
| XGBoost | 51,97% | 50,42% | 79,45% | 61,69% | 56,01% | 1,219 s |
| Random Forest | 51,52% | 50,12% | 83,55% | 62,65% | 55,59% | 4,859 s |

Catatan: tabel ini merupakan hasil eksperimen yang sudah terdokumentasi dalam rangkuman proyek dan harus diverifikasi kembali terhadap file hasil eksperimen final sebelum dimasukkan ke Bab IV.

## L.2 Interpretasi yang aman

Boleh ditulis:

> “Pada skema pengujian yang digunakan, LightGBM Tuned memperoleh Accuracy 53,07%, Precision 51,73%, Recall 53,30%, F1-Score 52,50%, dan ROC-AUC 55,67%.”

Boleh dianalisis:

> “LightGBM menunjukkan Precision dan Recall yang relatif lebih seimbang dibandingkan XGBoost dan Random Forest pada eksperimen tersebut.”

Jangan langsung ditulis:

> “LightGBM terbukti paling unggul.”

karena evaluasi tidak boleh disederhanakan menjadi satu skor keseluruhan dan penelitian telah diarahkan untuk menyajikan fakta empiris secara netral.

---

# M. FORWARD TESTING YANG TERDOKUMENTASI SAAT INI

Rangkuman proyek mencatat 7 transaksi awal:

| No | Tipe | Entry | Exit | P/L | Status |
|---:|---|---:|---:|---:|---|
| 1 | SELL | 4198,93 | 4192,43 | +$6,50 | WIN |
| 2 | SELL | 4190,56 | 4184,06 | +$6,50 | WIN |
| 3 | SELL | 4155,97 | 4155,77 | +$0,20 | BEP_REBOUND |
| 4 | SELL | 4148,34 | 4154,84 | -$6,50 | LOSS |
| 5 | SELL | 4154,31 | 4154,11 | +$0,20 | BEP_REBOUND |
| 6 | SELL | 4162,72 | 4156,22 | +$6,50 | WIN |
| 7 | SELL | 4156,53 | 4165,03 | -$8,50 | LOSS |

Ringkasan saat itu:

- 7 transaksi selesai;
- 3 WIN penuh;
- 2 BEP protected;
- 2 LOSS;
- Win Rate murni non-BEP: 60,0% (3 WIN dari 5 transaksi non-BEP);
- saldo terdokumentasi: $504,90 dari $500 awal.

## Catatan metodologis

Tujuh transaksi tersebut adalah **hasil awal**, bukan kesimpulan final penelitian.

Jangan menulis bahwa 7 transaksi sudah membuktikan keandalan sistem. Hasil final harus didasarkan pada periode *forward testing* yang sudah ditentukan dan seluruh transaksi yang dihasilkan selama periode tersebut.

---

# N. KOMPONEN TEKNIS YANG MASIH PERLU DIBERESKAN SEBELUM BAB III/IV FINAL

## 1. Master List 44 Fitur

Ini adalah pekerjaan teknis paling penting. Pastikan:

- jumlah tepat 44;
- nama fitur konsisten;
- timeframe sumber jelas;
- rumus/logika jelas;
- setiap fitur tidak menggunakan data masa depan.

## 2. Definisi split data

Tetapkan secara final:

- periode train;
- periode validation;
- periode test;
- periode forward testing.

Semua harus kronologis.

## 3. Definisi tuning

Catat:

- parameter yang dituning;
- rentang nilai;
- metode pencarian;
- metrik optimasi;
- data yang digunakan untuk tuning.

Test set tidak boleh digunakan untuk memilih hyperparameter.

## 4. Definisi threshold

Tetapkan threshold sebelum forward testing.

Analisis threshold 50%, 55%, 58%, 60%, 65%, 70%, 75% dapat ditampilkan sebagai analisis evaluasi, tetapi keputusan sistem forward testing harus ditentukan terlebih dahulu.

## 5. Probability calibration

Pastikan istilah di naskah sesuai implementasi.

Jika tidak ada metode calibration khusus:

> “estimasi probabilitas”

lebih tepat daripada:

> “probabilitas terkalibrasi”.

## 6. Manajemen risiko

Parameter seperti:

- lot;
- ATR multiplier;
- RRR;
- daily loss limit;
- cooldown;

harus memiliki satu konfigurasi final dan tidak berubah-ubah antarbagian dokumen.

## 7. Forward testing

Tentukan secara resmi:

- akun demo/real/evaluation sesuai kebijakan penelitian;
- saldo awal;
- periode;
- aturan entry;
- aturan exit;
- biaya/spread/slippage yang diperhitungkan;
- kapan sistem boleh membuka posisi;
- bagaimana posisi dicatat.

---

# O. CHECKLIST KONSISTENSI SELURUH SKRIPSI

Sebelum proposal/skripsi dikunci, semua bagian harus mematuhi checklist berikut:

| Item | Status Final yang Diinginkan |
|---|---|
| Judul | LightGBM + Multi-Timeframe + DXY + Makroekonomi |
| Operasional timeframe | M15 |
| Konfirmasi tren | H1 dan H4 |
| M5 | Dihapus |
| Horizon | 75 menit / 5 candle M15 |
| Fitur | 44 fitur |
| Model utama | LightGBM Tuned |
| Model pembanding | XGBoost + Random Forest |
| Logistic Regression | Dihapus dari ruang lingkup |
| Confidence | Dipakai sebagai threshold penyaringan |
| Threshold utama | Satu nilai yang ditetapkan sebelum testing, direkomendasikan ≥65% |
| Multi-Zone 58–70% | Dihapus dari desain inti |
| Retraining | Tidak ada |
| Continuous learning | Tidak ada |
| Post-Trade Scenario Engine | Tidak menjadi objek penelitian |
| Forward testing | Ya |
| MetaTrader 5 | Media implementasi/pengujian |
| Evaluasi klasifikasi | ROC-AUC, Log Loss, Precision, Recall, F1 |
| Evaluasi trading | Win Rate, Profit Factor, Max Drawdown, ROI |
| Klaim calibration | Hanya jika benar-benar diuji dengan metode calibration |
| Klaim zero latency | Dihapus |
| Klaim menghilangkan bias psikologis | Dihapus |

---

# P. POSISI PENELITIAN DALAM SATU KALIMAT

> **Penelitian ini menerapkan dan mengoptimalkan LightGBM untuk menghasilkan estimasi probabilitas arah pergerakan harga XAUUSD selama 75 menit dengan memanfaatkan 44 fitur yang berasal dari data M15, tren H1/H4, DXY, dan informasi makroekonomi, kemudian mengevaluasi kinerjanya melalui metrik klasifikasi, membandingkannya dengan XGBoost dan Random Forest, serta menguji model final yang dibekukan melalui forward testing MetaTrader 5 tanpa retraining.**

---

# Q. CATATAN AKHIR PEMBIMBING

Arah penelitian setelah revisi sebaiknya dipertahankan pada satu garis besar:

**Multi-Source Feature Fusion → LightGBM Tuned → Probability Prediction → Confidence Threshold → Comparative Evaluation → Frozen Forward Testing.**

Kekuatan penelitian bukan pada banyaknya modul trading, melainkan pada konsistensi antara:

**masalah → data → fitur → model → target → evaluasi → pengujian.**

Semakin sedikit komponen di luar inti tersebut, semakin mudah penelitian dipertanggungjawabkan dalam seminar proposal dan sidang.
