# Terjemahan & Analisis Mendalam: Short Term Forecasting of Base Metals Prices Using a LightGBM and a LightGBM - ARIMA Ensemble

**File Asli:** Short term forecasting of base metals prices using a LightGBM and a LightGBM - ARIMA ensemble.pdf  
**Penulis:** Konstantinos Oikonomou, Dimitris Damigos  
**Institusi:** School of Mining & Metallurgical Engineering, National Technical University of Athens, Yunani  
**Publikasi:** *Mineral Economics* (Springer), Vol. 38, Hal. 37–49 (2025)  
**DOI:** https://doi.org/10.1007/s13563-024-00437-y  
**Jumlah Halaman:** 13 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Logam dasar (*base metals*) merupakan material kunci bagi berbagai sektor industri seperti elektronika, konstruksi, dan manufaktur. Harga jual logam sangat menentukan profitabilitas perusahaan pertambangan dan metalurgi yang memproduksi dan memperdagangkannya, serta bagi negara-negara yang perekonomiannya bergantung pada ekspor komoditas ini sebagai sumber pendapatan nasional. Prediksi pergerakan harga komoditas di masa depan dapat berfungsi sebagai instrumen mitigasi risiko dan perencanaan anggaran yang lebih baik. 

Dalam penelitian ini, *logarithmic returns* (imbal hasil logaritmik) dari harga logam dasar diramalkan menggunakan model *autoregressive Light Gradient Boosting Machine* (AutoReg-LightGBM) serta model *ensemble* yang menggabungkan algoritma LightGBM dengan model peramalan deret waktu klasik (*Autoregressive Integrated Moving Average* / ARIMA). Kedua model ini kemudian dibandingkan dengan tiga model *benchmark* univariat yang lebih sederhana, yaitu model *Global Mean* (GM), model *Exponential Smoothing* (ES), dan model ARIMA murni. 

Berdasarkan evaluasi metrik RMSE, model AutoReg-LightGBM mengungguli ketiga model benchmark dan model ensemble dalam memprediksi *returns* aluminium dan nikel hingga 6 bulan ke depan. Sementara itu, *returns* tembaga (*copper*) dan seng (*zinc*) berhasil diramalkan dengan lebih akurat oleh model *ensemble* LightGBM-ARIMA. Namun demikian, tidak ada satupun dari model machine learning yang diusulkan mampu mengalahkan model ARIMA sederhana ketika memprediksi timbal (*lead*) dan timah (*tin*). Temuan ini mengindikasikan bahwa model kompleks berbasis machine learning bukanlah obat mujarab (*panacea*) untuk semua masalah peramalan, dan dalam kondisi dinamika pasar tertentu, penggabungan aspek linear (ARIMA) dan non-linear (LightGBM) memberikan keunggulan terbaik.

---

### I. Pendahuluan & Latar Belakang Komoditas Logam
Logam dasar seperti tembaga, aluminium, timbal, nikel, timah, dan seng diperdagangkan di bursa global seperti *London Metal Exchange* (LME). Harga komoditas ini terbentuk dari dinamika penawaran (*supply shocks*, gangguan rantai pasok, bencana alam) dan permintaan (*demand*, siklus ekspansi atau resesi global). Selama dekade terakhir, harga komoditas logam memperlihatkan volatilitas luar biasa, terutama selama krisis subprime mortgage 2008, pandemi COVID-19, dan transisi energi bersih dunia.

Bagi negara produsen (misalnya Chile dan Peru untuk tembaga, Indonesia untuk nikel), fluktuasi harga komoditas berdampak langsung pada penerimaan pajak dan devisa ekspor. Di sisi industri, fluktuasi harga menjadi risiko biaya bahan baku yang kritis. Oleh karena itu, kemampuan meramal tren harga jangka pendek menjadi kebutuhan fundamental.

---

### II. Landasan Teori & Arsitektur Model

#### A. Keterbatasan Model Deret Waktu Klasik (ARIMA)
Model ARIMA telah menjadi standar de facto dalam ekonometrika keuangan. Namun ARIMA memiliki asumsi linearitas yang ketat dan mengasumsikan stasioneritas setelah diferensiasi. ARIMA unggul dalam menangkap struktur autokorelasi temporal linear, namun gagal total ketika berhadapan dengan pergeseran rezim non-linear (*regime shifts*) dan lonjakan volatilitas mendadak.

#### B. Algoritma LightGBM sebagai Model Autoregressive
LightGBM merupakan algoritma berbasis *gradient boosting decision tree* yang mampu memetakan interaksi non-linear yang sangat rumit antar-variabel *lag* tanpa memerlukan asumsi distribusi data. Dalam penelitian ini, LightGBM dikonstruksi secara *autoregressive* (AutoReg-LightGBM), di mana fitur input adalah nilai *lag* imbal hasil historis:
r_t = \ln\left(rac{P_t}{P_{t-1}}ight)
Fitur: $[r_{t-1}, r_{t-2}, \dots, r_{t-p}]$

#### C. Arsitektur Ensemble Hybrid: LightGBM + ARIMA
Model hybrid menggabungkan keunggulan pemodelan linear dari ARIMA dan pemodelan non-linear dari LightGBM. Dua pendekatan ensemble yang diuji:
1. **Weighted Average Combination:** Menggabungkan prediksi linier ARIMA ($\hat{y}_{ARIMA}$) dan prediksi non-linear LightGBM ($\hat{y}_{LGBM}$) menggunakan pembobotan berbasis varians galat.
2. **Residual Modeling:** ARIMA memodelkan komponen linier dari deret waktu, kemudian residual (galat sisa) yang bersifat non-linear dimodelkan dan diprediksi menggunakan LightGBM.

---

### III. Data, Eksperimen, dan Hasil Pengujian

- **Komoditas yang Diuji:** 6 Logam Dasar LME (Aluminium, Tembaga/Copper, Timbal/Lead, Nikel, Timah/Tin, Seng/Zinc).
- **Periode Data:** Data harga bulanan historis jangka panjang (puluhan tahun hingga 2023).
- **Horizon Peramalan:** 1 bulan hingga 6 bulan ke depan (*multi-step forecasting*).
- **Metrik Evaluasi:** *Root Mean Squared Error* (RMSE) dan *Root Mean Squared Scaled Error* (RMSSE).

#### Ringkasan Kinerja Model:
1. **Aluminium & Nikel:** Model **AutoReg-LightGBM murni** meraih performa terbaik, melampaui seluruh model benchmark klasik dan ensemble. Hal ini disebabkan oleh tingginya non-linearitas dan sensitivitas nikel/aluminium terhadap disrupsi pasar modern (baterai EV dan transisi energi).
2. **Tembaga & Seng:** Model **Ensemble Hybrid (LightGBM + ARIMA)** keluar sebagai pemenang dengan RMSE terendah. Kombinasi sinergi antara tren siklikal linier (makroekonomi) dan non-linearitas jangka pendek menghasilkan akurasi tertinggi.
3. **Timbal & Timah:** Model **ARIMA klasik** justru memberikan performa yang lebih stabil dan galat lebih kecil dibandingkan LightGBM. Sifat deret waktu timbal dan timah cenderung lebih stasioner dengan struktur autokorelasi linier yang dominan, sehingga model machine learning yang terlalu fleksibel rentan terhadap *over-fitting*.

---

### IV. Kesimpulan Penulis
Penelitian ini membuktikan secara empiris bahwa:
1. Mengintegrasikan LightGBM dengan ARIMA (Ensemble) menghasilkan peramalan komoditas yang lebih superior ketika data memiliki campuran komponen linear dan non-linear.
2. Tidak ada satu model tunggal yang selalu menang untuk semua komoditas (*No Free Lunch Theorem*).
3. Pemodelan berbasis *returns* logaritmik jauh lebih superior dan stabil dibandingkan memodelkan harga nominal secara langsung.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Studi ini membandingkan kinerja model machine learning modern (AutoReg-LightGBM), model ekonometrika klasik (ARIMA, Exponential Smoothing, Global Mean), dan model gabungan (Ensemble Hybrid LightGBM-ARIMA) untuk meramal harga 6 komoditas logam dasar LME dalam horizon 1 hingga 6 bulan. Hasilnya membuktikan bahwa pada komoditas yang sarat volatilitas non-linear (Aluminium, Nikel, Tembaga, Seng), LightGBM dan Ensemble LightGBM-ARIMA secara signifikan mengalahkan model klasik, sementara pada komoditas yang lebih linier, ARIMA tetap kompetitif.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Tunggal pada Komoditas:** Model statistik univariat klasik (ARIMA/GARCH) gagal menangkap pergeseran non-linear yang tajam, sedangkan model ML modern (seperti XGBoost/LightGBM) sering kali mengabaikan autokorelasi linier dasar deret waktu sehingga rentan *overfitting*.
2. **Minimnya Studi Benchmark Komparatif Multi-Komoditas:** Sebagian besar literatur hanya menguji satu aset komoditas saja. Belum ada penelitian komprehensif yang secara sistematis membandingkan LightGBM mandiri vs Hybrid Ensemble LightGBM-ARIMA pada spektrum komoditas logam dengan berbagai tingkat volatilitas.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Evaluasi apakah algoritma LightGBM dan hybrid ensemble mampu mengatasi keterbatasan model ekonometrika klasik dalam meramal volatilitas harga komoditas logam.
- **Dataset:** Data historis 6 komoditas logam (Aluminium, Copper, Lead, Nickel, Tin, Zinc) dari *London Metal Exchange* (LME).
- **Variabel Input:** Imbal hasil logaritmik ($) beserta lag waktu (-1$ hingga -p$).
- **Horizon Prediksi:** 1, 2, 3, hingga 6 bulan ke depan.

### D. Solusi dari Penelitian
- Mengusulkan arsitektur **AutoReg-LightGBM** dan **Hybrid Ensemble LightGBM-ARIMA**.
- Mengonversi data harga mentah menjadi **log-returns** untuk memastikan kestasioneran sebelum pelatihan pohon keputusan.
- Mengombinasikan estimasi linier ARIMA dengan fleksibilitas non-linear LightGBM.
- **Hasil:** Penurunan RMSE signifikan pada 4 dari 6 komoditas logam (Aluminium, Nikel, Tembaga, Seng).

### E. Relevansi & Rekomendasi untuk Skripsi XAUUSD Anda
1. **Emas (XAUUSD) Merupakan Komoditas Logam Mulia:** Logika pasar logam dasar pada paper ini sangat mirip dengan XAUUSD, di mana harga dipengaruhi oleh tren makroekonomi jangka panjang dan guncangan volatilitas jangka pendek.
2. **Pertimbangan Arsitektur Hybrid / Residual:** Anda dapat mengadopsi ide dari paper ini: gunakan model deret waktu untuk menangkap komponen linier/tren dasar XAUUSD, lalu gunakan **LightGBM** untuk menangkap residual non-linear dan lonjakan volatilitas.
3. **Peringatan Overfitting:** Paper ini secara jujur menunjukkan bahwa model ML yang sangat kompleks bisa kalah jika hiperparameter tidak dituning dengan hati-hati terhadap data finansial yang ber-noise tinggi.
