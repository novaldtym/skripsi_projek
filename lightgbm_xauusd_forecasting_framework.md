# Framework LightGBM untuk Prediksi Arah Harga XAU/USD (Forecasting Klasifikasi Dua Arah)

Dokumen ini merangkum arsitektur, metodologi, dan metrik evaluasi model **LightGBM (Light Gradient Boosting Machine)** dalam konteks prediksi arah pergerakan harga komoditas/forex **XAU/USD** dengan kapabilitas eksekusi dua arah (*Buy* & *Sell*). Format dokumen ini distrukturkan agar optimal dibaca dan diproses oleh sistem AI / LLM.

---

## 1. Fondasi & Prinsip Kerja LightGBM

LightGBM adalah algoritma *ensemble learning* berbasis *decision tree* yang mengimplementasikan kerangka *Gradient Boosting Decision Tree (GBDT)*. Model membangun pohon secara sekuensial untuk meminimalkan fungsi kerugian (*loss function*) dengan mengoreksi residu/gradien dari pohon-pohon sebelumnya.

### Karakteristik Utama Algoritma:
* **Leaf-wise (Best-first) Tree Growth:**
  * Berbeda dari algoritma konvensional yang tumbuh sejajar (*level-wise/depth-wise*), LightGBM memotong daun (*leaf*) yang menghasilkan penurunan loss (*loss reduction*) terbesar.
  * *Implikasi Finansial:* Menghasilkan akurasi tinggi lebih cepat, namun membutuhkan regulasi ketat (`max_depth`, `num_leaves`, `min_child_samples`) agar tidak mengalami *overfitting* terhadap *noise* pasar.
* **Histogram-based Binning:**
  * Nilai fitur kontinu dikelompokkan ke dalam bin diskret (umumnya 256 bin).
  * Menurunkan kompleksitas pencarian titik pisah (*split point*) dari $O(	ext{#data} 	imes 	ext{#fitur})$ menjadi $O(	ext{#bin} 	imes 	ext{#fitur})$, menghemat RAM dan mempercepat pelatihan *time series* berukuran gigabyte.
* **GOSS (Gradient-based One-Side Sampling):**
  * Mempertahankan seluruh instans data dengan gradien residual besar (kejadian sulit diprediksi/volatilitas tinggi) dan mengambil sampel acak dari instans dengan gradien kecil.
* **EFB (Exclusive Feature Bundling):**
  * Menggabungkan fitur-fitur yang saling eksklusif (*mutually exclusive*) atau jarang bernilai non-zero bersamaan ke dalam satu bundel untuk mengurangi dimensi tanpa kehilangan densitas informasi.

---

## 2. Pipeline Prediksi Arah Harga XAU/USD

### A. Feature Engineering Input
Data mentah OHLCV (Open, High, Low, Close, Volume) ditransformasi menjadi fitur representatif:
1. **Teknikal & Momentum:** RSI (berbagai periode), MACD (Line, Signal, Histogram), Stochastic, Bollinger Bands (%B dan Bandwidth), ATR (Average True Range untuk volatilitas).
2. **Lagged Price Action & Returns:** Return logaritmik $\ln(P_t / P_{t-k})$ untuk $k \in \{1, 2, 3, 5, 8, 13, 21\}$.
3. **Korelasi Makro & Intermarket (Crucial untuk Emas):**
   * Pergerakan Indeks Dolar AS (DXY / USDX).
   * Imbal Hasil Obligasi AS (*US 10-Year Treasury Yield* / US10Y).
   * Indeks Volatilitas Pasar (CBOE VIX).
   * Harga Minyak Mentah (WTI/Brent) & Indeks Saham Global (S&P 500).
4. **Variabel Temporal & Kalender Ekonomi:**
   * Sesi perdagangan (Asia / Tokyo, London, New York, dan overlap London-NY).
   * Fitur siklus waktu (sinus/cosinus jam dalam hari, hari dalam sepekan).
   * *High-impact news flags* (FOMC, NFP, CPI, PPI).

### B. Validasi Data & Mitigasi Leakage
* **Wajib Menggunakan Walk-Forward / TimeSeriesSplit:**
  * Dilarang menggunakan *Random K-Fold Cross Validation* karena menyebabkan kebocoran masa depan (*lookahead bias / data leakage*).
  * Skema: Training pada rentang $T_0 	o T_n$, validasi pada $T_{n+1} 	o T_{n+k}$.
* **Stationarity Handling:** Data harga mentah dinormalisasi menjadi stasioner (returns, selisih indikator, z-score rolling window).

---

## 3. Matriks Konfusi & Evaluasi Finansial (Eksekusi 2 Arah)

Pada perdagangan derivatif seperti XAU/USD, **posisi Sell (Short) dan Buy (Long) sama-sama merupakan tindakan aktif yang mempertaruhkan modal**.

### A. Skenario 1: Biner Simetris (Always-In-The-Market)
Model dipaksa memilih: $1 = 	ext{Buy}$, $0 = 	ext{Sell}$.

| Simbol | Prediksi Model | Kondisi Pasar Aktual | Konsekuensi Finansial |
| :--- | :--- | :--- | :--- |
| **TP (True Positive)** | Buy (Naik) | Naik | **Profit** dari posisi Long |
| **TN (True Negative)** | Sell (Turun) | Turun | **Profit** dari posisi Short |
| **FP (False Positive)** | Buy (Naik) | Turun | **Loss** (Buy saat harga jatuh) |
| **FN (False Negative)** | Sell (Turun) | Naik | **Loss** (Sell saat harga melonjak) |

> **Analisis:** Dalam biner simetris, FP dan FN sama-sama menyebabkan kerugian modal riil. Fokus optimasi adalah menekan total salah arah $(	ext{FP} + 	ext{FN})$ secara berimbang agar tidak ada bias directional.

---

### B. Skenario 2: Multiclass 3-Arah (Buy / Wait / Sell) — *Rekomendasi Industri*
Menambahkan kelas netral ($0 = 	ext{Hold/Wait}$) untuk menyaring fase konsolidasi (*sideways*) dan menghindari biaya spread saat sinyal tidak jelas.
* **Kelas 1 (Buy):** Expected return $\ge +\delta$
* **Kelas 0 (Wait):** $-\delta < 	ext{Expected return} < +\delta$
* **Kelas 2 (Sell):** Expected return $\le -\delta$

#### Matriks Evaluasi $3 	imes 3$:
| Prediksi \ Aktual | Aktual Buy (Tren Naik) | Aktual Wait (Sideways) | Aktual Sell (Tren Turun) |
| :--- | :--- | :--- | :--- |
| **Prediksi Buy** | **TP Buy (Profit Optimal)** | FP Ringan (Terkikis Spread) | **Fatal FP (Severe Loss)** |
| **Prediksi Wait** | FN Buy (Opportunity Loss) | **TN Netral (Modal Aman)** | FN Sell (Opportunity Loss) |
| **Prediksi Sell** | **Fatal FP (Severe Loss)** | FP Ringan (Terkikis Spread) | **TP Sell (Profit Optimal)** |

---

## 4. Metrik Prioritas & Strategi Threshold

### Metrik Prioritas:
1. **Class-Specific Precision:**
   $$	ext{Precision}_{	ext{Buy}} = rac{	ext{TP}_{	ext{Buy}}}{	ext{Total Sinyal Buy Dikeluarkan}}, \quad 	ext{Precision}_{	ext{Sell}} = rac{	ext{TP}_{	ext{Sell}}}{	ext{Total Sinyal Sell Dikeluarkan}}$$
   *Kedua nilai harus seimbang.* Jika Precision Buy 65% namun Precision Sell hanya 47%, model memiliki bias bull-market yang akan menguras keuntungan saat pasar berbalik.
2. **Off-Diagonal Fatal Error Rate (Sinyal Terbalik 180°):**
   Meminimalkan frekuensi model memprediksi Buy saat pasar dump parah, atau memprediksi Sell saat pasar pump agresif.
3. **Macro $F_{0.5}$-Score:**
   Memberikan bobot penalti lebih besar pada *Precision* dibanding *Recall*, karena eksekusi sinyal salah (FP/Loss) jauh lebih merusak portofolio daripada melewatkan sinyal (FN/Missed Trade).
4. **PR-AUC (Precision-Recall Area Under Curve):**
   Mengevaluasi stabilitas probabilitas model di berbagai tingkatan confidence.

### Strategi Eksekusi Dual-Threshold:
Daripada memicu order pada ambang $0.5$ (yang didominasi noise pasar):
* **Buka Buy:** Jika $P(	ext{Buy}) \ge 	heta_{	ext{high}}$ (misal $\ge 0.65$).
* **Buka Sell:** Jika $P(	ext{Sell}) \ge 	heta_{	ext{high}}$ atau pada model biner $P(	ext{Buy}) \le 	heta_{	ext{low}}$ (misal $\le 0.35$).
* **Wait / No Position:** Jika probabilitas berada di zona abu-abu:
  $$	heta_{	ext{low}} < P < 	heta_{	ext{high}} \quad (0.35 < P < 0.65)$$

---

## 5. Parameter Kunci LightGBM untuk Derivatif Keuangan

| Parameter | Fungsi dalam Kasus XAU/USD | Rekomendasi Nilai Awal |
| :--- | :--- | :--- |
| `objective` | Tipe pembelajaran | `'binary'` atau `'multiclass'` |
| `num_leaves` | Mengontrol kompleksitas pohon | $15 - 31$ (hindari nilai terlalu besar) |
| `max_depth` | Membatasi kedalaman daun | $4 - 6$ (mencegah overfitting) |
| `min_child_samples` | Minimal data per daun | $50 - 200$ (menghindari daun menangkap noise candle) |
| `feature_fraction` | Subsampling fitur per iterasi | $0.6 - 0.8$ (mengurangi korelasi antar-pohon) |
| `bagging_fraction` | Subsampling data per iterasi | $0.7 - 0.9$ |
| `learning_rate` | Langkah gradient descent | $0.01 - 0.05$ (dengan early stopping $50-100$) |
| `lambda_l1` / `lambda_l2` | Regularisasi Lasso / Ridge | $0.1 - 5.0$ (menekan bobot fitur tidak signifikan) |
