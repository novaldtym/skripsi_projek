# Terjemahan & Analisis Mendalam: Gold and Bitcoin Price Prediction Based on KNN, XGBoost, and LightGBM Model

**File Asli:** `Gold_and_Bitcoin_Price_Prediction_based_on_KNN_XGB.pdf`  
**Penulis:** Ziyang Yuan  
**Institusi:** Hohai University, Nanjing 210098, China  
**Publikasi:** *Highlights in Science, Engineering and Technology* (CMLAI 2023), Vol. 39, Hal. 720–725  
**Jumlah Halaman:** 6 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Dalam beberapa dekade terakhir, permintaan perdagangan aset keuangan berbasis bantuan *machine learning* semakin meningkat pesat. Saat ini, pasar *cryptocurrency* (Bitcoin) dan pasar emas telah berkembang sangat dinamis dengan fluktuasi harga yang luar biasa dramatis. Penelitian ini bertujuan untuk mempelajari dinamika pola perdagangan harga Bitcoin dan Emas berbasis skenario *machine learning* untuk meramalkan harga kedua aset tersebut di masa mendatang. 

Secara spesifik, studi ini memberikan telaah mendalam mengenai penerapan metode yang memadukan tiga algoritma terkemuka: *K-Nearest Neighbors* (KNN), *eXtreme Gradient Boosting* (XGBoost), dan *Light Gradient Boosting Machine* (LightGBM) untuk memprediksi harga emas (XAU) dan Bitcoin (CME) berdasarkan data historis dari rentang tahun 2017 hingga 2022. Berdasarkan analisis, penelitian ini menunjukkan perbedaan karakteristik performa dari ketiga model, tingkat akurasi masing-masing algoritma, dan pembuktian metrik evaluasi yang relevan untuk meramal harga Emas dan Bitcoin. Secara keseluruhan, hasil penelitian ini memberikan panduan strategis bagi para investor dalam membuat keputusan rasional serta membuka wawasan baru bagi eksplorasi peramalan harga berbasis pendekatan *machine learning*.

---

### I. Pendahuluan
Bitcoin adalah mata uang kripto pertama yang diperkenalkan pada tahun 2009 berbasis teknologi blockchain yang terdesentralisasi tanpa otoritas tunggal bank sentral. Di sisi lain, Emas adalah elemen alami sekaligus instrumen moneter global tertua. Terdapat korelasi unik antara emas, minyak, dan instrumen lindung nilai (*safe haven*) terhadap inflasi. Pergerakan harga emas dalam jangka panjang bersifat non-stasioner dan memiliki kompleksitas tinggi.

Berbagai pendekatan telah diteliti dalam literatur sebelumnya:
- Guha dan Bandyopadhyay menggunakan pendekatan ARIMA untuk memprediksi emas selama rentang 10 tahun, namun menemukan bahwa ARIMA hanya efektif untuk jangka pendek (*short run*) dalam mendeteksi variasi kecil.
- Peneliti lain menggunakan LSTM dan arsitektur hybrid CNN-LSTM untuk memprediksi harga aset digital yang mampu meningkatkan akurasi namun menuntut kapasitas komputasi tinggi.
- Faghih dan Heidari mengaplikasikan Grey Model GM(1,1).

Namun, perbandingan langsung antara algoritma berbasis jarak (KNN) dengan algoritma ensemble *gradient boosting* generasi baru (XGBoost dan LightGBM) secara simultan pada emas dan Bitcoin masih sangat jarang diteliti secara empiris.

---

### II. Data & Metodologi Penelitian

#### A. Sumber Data & Karakteristik
Data yang digunakan adalah harga penutupan harian (*daily closing price*) untuk **Bitcoin (CME)** dan **Emas (XAU)** dari Oktober 2017 hingga Oktober 2022 yang dikumpulkan dari *Investing.com*.
- Total sampel valid: **1.302 hari bursa untuk Emas (XAU)** dan **1.584 hari untuk Bitcoin**.
- Data dibagi menjadi data latih (*training set*) dan data uji (*testing set*).

#### B. Fitur Variabel Independen
Fitur yang diekstraksi dari data historis meliputi:
1. Tanggal bursa / indeks waktu deret waktu.
2. Tingkat perubahan harga harian (*daily price changing rate*).
3. Volume transaksi (*transaction quantities*).
4. Selisih harga antar hari berturut-turut (*day-to-day price differences*).

#### C. Algoritma yang Dibandingkan
1. **KNN (K-Nearest Neighbors Regression):** Algoritma non-parametrik berbasis instans yang memprediksi harga baru berdasarkan rata-rata terbobot dari $K$ tetangga terdekat dalam ruang Euclidean.
2. **XGBoost (Extreme Gradient Boosting):** Algoritma ensemble pohon keputusan yang menggunakan ekspansi deret Taylor orde kedua pada fungsi loss dan menerapkan penalti regularisasi L1/L2 secara ketat dengan penumbuhan pohon berbasis level (*level-wise*).
3. **LightGBM (Light Gradient Boosting Machine):** Algoritma gradient boosting efisien yang menggunakan pemisahan berbasis daun (*leaf-wise tree growth*), histogram-based binning, dan Gradient-based One-Side Sampling (GOSS).

---

### III. Hasil Eksperimen Kuantitatif

Evaluasi performa dilakukan menggunakan metrik: *Mean Squared Error* (MSE), *Root Mean Squared Error* (RMSE), *Mean Absolute Error* (MAE), *Mean Absolute Percentage Error* (MAPE), dan Koefisien Determinasi ($R^2$).

#### Tabel Perbandingan Kinerja Pengujian (Data Uji / Out-of-Sample Testing):

| Aset | Algoritma | MSE | RMSE | MAE | MAPE (%) | $R^2$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Emas (XAU)** | KNN | 205.093 | 14.321 | 11.104 | 0.642% | 0.994 |
| **Emas (XAU)** | XGBoost | 13.036 | 3.611 | 2.550 | 0.151% | 0.996 |
| **Emas (XAU)** | **LightGBM** | **11.041** | **3.323** | **2.014** | **0.119%** | **0.997** |
| Bitcoin | KNN | 1,114,513 | 1,055.70 | 678.04 | 2.477% | 0.997 |
| Bitcoin | XGBoost | 1,755,292 | 1,324.87 | 806.18 | 3.174% | 0.995 |
| Bitcoin | LightGBM | 14,043.28 | 118.50 | 85.09 | 7.887% | 0.834 |

#### Analisis Hasil untuk Emas (XAU):
1. **LightGBM Menjadi Pemenang Mutlak pada Emas (XAU):** 
   - LightGBM meraih galat terendah di seluruh metrik: **RMSE hanya 3.323 USD**, **MAE 2.014 USD**, dan **MAPE hanya 0.119%**, dengan **$R^2$ tertinggi 0.997**.
   - Kinerja LightGBM secara konsisten mengalahkan XGBoost (RMSE 3.611) dan jauh melampaui KNN (RMSE 14.321).
2. **Efisiensi dan Kecepatan Komputasi:**
   - LightGBM beroperasi jauh lebih cepat dan hemat memori dibandingkan XGBoost berkat strategi pemisahan pohon *leaf-wise* dan histogram binning.
3. **Resistensi terhadap Overfitting:**
   - XGBoost pada data latih emas menunjukkan nilai sempurna ($R^2 = 1.0$), namun pada data uji performanya sedikit terdistorsi dibandingkan LightGBM, menunjukkan bahwa struktur regularisasi dan pemangkasan daun LightGBM lebih adaptif terhadap deret waktu emas.

---

### IV. Kesimpulan Penulis
Model regresi LightGBM beroperasi sangat cepat, efisien, dan memberikan akurasi paling superior dalam memprediksi harga emas (XAU). Baik LightGBM maupun XGBoost mengungguli model berbasis jarak (KNN). Bagi para pelaku pasar emas, LightGBM terbukti menjadi instrumen pemodelan prediktif yang sangat andal.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian ini melakukan studi komparatif kuantitatif antara tiga paradigma algoritma machine learning (KNN, XGBoost, dan LightGBM) untuk peramalan harga harian Emas (XAU) dan Bitcoin (CME) periode 2017–2022. Hasil eksperimen membuktikan secara empiris bahwa **LightGBM meraih performa terbaik di antara seluruh model pada harga Emas**, dengan RMSE terendah (3.323), MAE terendah (2.014), MAPE terendah (0.119%), dan $R^2$ tertinggi (0.997), serta kecepatan proses yang mengungguli XGBoost.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kurangnya Komparasi Langsung Aset Tradisional vs Digital:** Emas dan Bitcoin sering diperdebatkan sebagai instrumen lindung nilai alternatif, namun studi yang secara serentak membandingkan model tree-boosting modern (XGBoost vs LightGBM) pada kedua instrumen ini dengan arsitektur fitur seragam masih sangat minim.
2. **Validasi Empiris Superioritas LightGBM atas XGBoost pada XAU:** Meskipun XGBoost sangat populer dalam kompetisi sains data, studi yang membuktikan secara kuantitatif apakah LightGBM mampu mengungguli XGBoost pada data deret waktu harga emas masih terbatas.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Menguji dan membuktikan algoritma machine learning mana yang paling akurat, stabil, dan efisien dalam memodelkan harga komoditas emas dan mata uang kripto.
- **Dataset:** Data harian Investing.com untuk Emas (XAU, 1.302 data) dan Bitcoin (CME, 1.584 data) periode Oktober 2017 hingga Oktober 2022.
- **Variabel:** Harga penutupan harian, laju perubahan harga, volume transaksi, dan selisih diferensial harga.

### D. Solusi dari Penelitian
- Mengimplementasikan pipeline pemodelan terpadu dengan normalisasi data dan ekstraksi fitur deret waktu.
- Melatih dan menguji model KNN, XGBoost, dan LightGBM dengan metrik komprehensif (MSE, RMSE, MAE, MAPE, $R^2$).
- **Solusi Utama:** Menetapkan LightGBM sebagai algoritma optimal untuk peramalan harga emas karena menghasilkan akurasi prediktif tertinggi dengan waktu komputasi yang jauh lebih ringkas.

### E. Relevansi & Nilai Tambah untuk Skripsi XAUUSD Anda
1. **Bukti Validasi Primer untuk Pemilihan LightGBM:** Paper ini adalah bukti literatur yang sangat kuat dan relevan langsung untuk Bab 1 dan Bab 2 skripsi Anda. Anda dapat secara eksplisit mengutip hasil paper ini: *"Yuan (2023) membuktikan bahwa LightGBM mengungguli XGBoost dan KNN dalam memprediksi harga emas (XAU) dengan menghasilkan RMSE terendah 3.323 dan MAPE terendah 0.119%."*
2. **Justifikasi Efisiensi Komputasi:** Menjadi argumen kuat bahwa skripsi Anda memilih LightGBM bukan hanya karena akurasinya yang tinggi, tetapi juga karena efisiensi komputasi dan pemisahan pohon *leaf-wise* yang sangat cocok untuk data keuangan.
