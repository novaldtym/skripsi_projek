# Analisis Mendalam & Panduan Baca: Analisis dan Perbandingan Algoritma SVR, XGBoost, dan LightGBM dalam Prediksi Cryptocurrency Ethereum

**File Asli:** `535220114_Ridhwan+Ardiyansyah+-+RIDHWAN+ARDIYANSYAH.pdf`  
**Penulis:** Ryan Anthony, Jechenthia Maria Taso, Stephen Yohanes Christopher, Ridhwan Ardiyansyah  
**Institusi:** Program Studi Teknik Informatika, Fakultas Teknologi Informasi, Universitas Tarumanagara (UNTAR), Jakarta, Indonesia  
**Publikasi:** *Jurnal Ilmu Komputer dan Sistem Informasi* (JIRSI), Vol. 12 / 2024  
**Bahasa Asli:** Bahasa Indonesia  
**Jumlah Halaman:** 9 Halaman  

---

## 1. Ulasan Lengkap Struktur & Isi Makalah

### Abstrak
Penelitian ini bertujuan untuk menganalisis dan membandingkan kinerja tiga algoritma machine learning, yaitu *Support Vector Regression* (SVR) dengan kernel linear, *eXtreme Gradient Boosting* (XGBoost), dan *Light Gradient Boosting Machine* (LightGBM) dalam memprediksi harga aset digital yang sangat berfluktuasi (*cryptocurrency Ethereum*) berdasarkan data historis harian. 

Penelitian menggunakan dataset harga Ethereum dalam satuan USD selama lima tahun terakhir yang diperoleh dari situs Investing.com. Variabel yang digunakan adalah harga Close, Open, High, dan Low. Penelitian menguji dua skenario pembagian data, yaitu 80% data latih : 20% data uji, serta 70% data latih : 30% data uji. Penelitian ini juga menggunakan variasi *time step* (jendela waktu ketergantungan deret waktu) untuk menguji pengaruh dependensi temporal terhadap performa algoritma. 

Hasil penelitian menunjukkan bahwa **algoritma LightGBM memiliki kinerja paling unggul** dibandingkan dua algoritma lainnya. Pada pembagian 80:20, nilai rata-rata MAE LightGBM untuk harga High adalah **75.486**, dibandingkan XGBoost sebesar **77.314** dan SVR sebesar **115.590**. Pada pembagian 70:30, LightGBM tetap mempertahankan keunggulannya dengan nilai rata-rata MAE **78.228**, dibandingkan XGBoost sebesar **83.573** dan SVR sebesar **104.356**. Evaluasi lainnya seperti RMSE dan $R^2$ juga menegaskan keunggulan LightGBM. Dalam aspek efisiensi komputasi, LightGBM menunjukkan kecepatan pemrosesan yang jauh lebih efisien dibandingkan XGBoost.

**Kata Kunci:** Ethereum, LightGBM, SVR, XGBoost, Time Step, MAE, RMSE

---

### I. Pendahuluan
Pasar aset finansial digital mengalami pertumbuhan pesat namun memiliki sifat pergerakan harga yang sangat liar dan tidak stabil (*extreme volatility*). Ethereum merupakan salah satu aset kripto terpenting yang menopang ekosistem aplikasi terdesentralisasi (*dApps*) dan *smart contract*.

Prediksi harga instrumen yang volatil seperti ini memerlukan algoritma machine learning yang mampu menangani hubungan non-linear dan tidak rentan terhadap pencilan (*outliers*). Tiga model yang sering dijadikan kandidat utama adalah:
1. **SVR (Support Vector Regression):** Model klasik yang meminimalkan galat dalam batas margin $\epsilon$-tube.
2. **XGBoost:** Model gradient boosting terpopuler berbasis pemisahan level (*level-wise*).
3. **LightGBM:** Model gradient boosting generasi baru berbasis pemisahan daun (*leaf-wise*) yang dirancang untuk kecepatan dan skala data besar.

Penelitian ini membandingkan ketiga algoritma ini secara objektif menggunakan variasi jendela *time step* dan rasio pembagian data.

---

### II. Metodologi & Tahapan Eksperimen

#### A. Dataset & Fitur
- **Sumber Data:** Data historis harian Ethereum (ETH/USD) dari Investing.com rentang 5 tahun (2018–2023).
- **Fitur Masukan:** Harga Open, High, Low, Close (OHLC).
- **Target Prediksi:** Memprediksi harga penutupan dan harga tertinggi (High) pada periode waktu berikutnya.
- **Variasi Time Step:** Menggunakan variasi jendela waktu ($lag = 1, 3, 7$ hari) untuk melihat sejauh mana riwayat hari sebelumnya memengaruhi keakuratan estimasi.

#### B. Skenario Pengujian Data
1. **Skenario 1:** 80% Data Latih (Training) dan 20% Data Uji (Testing).
2. **Skenario 2:** 70% Data Latih (Training) dan 30% Data Uji (Testing).

---

### III. Hasil Pengujian Kuantitatif & Pembahasan

#### Tabel Ringkasan Rata-Rata MAE Prediksi:
| Rasio Data (Latih : Uji) | Algoritma SVR (Linear) | Algoritma XGBoost | Algoritma LightGBM | Pemenang |
| :---: | :---: | :---: | :---: | :---: |
| **80% : 20%** | 115.590 | 77.314 | **75.486** | **LightGBM (Galat Terendah)** |
| **70% : 30%** | 104.356 | 83.573 | **78.228** | **LightGBM (Galat Terendah)** |

#### Analisis Komparatif:
1. **LightGBM vs SVR:** SVR dengan kernel linier mengalami galat sangat besar (MAE > 100) karena ketidakmampuannya menangkap dinamika non-linear dari aset yang berfluktuasi tajam. Meskipun waktu pelatihan SVR linier singkat, kualitas prediksinya tidak memadai untuk pengambilan keputusan finansial.
2. **LightGBM vs XGBoost:** LightGBM secara konsisten mengalahkan XGBoost pada kedua skenario rasio data. Pada rasio 70:30 (data latih lebih sedikit), selisih keunggulan LightGBM semakin melebar (MAE 78.228 vs 83.573), membuktikan bahwa mekanisme *leaf-wise growth* pada LightGBM lebih adaptif dalam mengekstrak pola fitur saat sampel data lebih terbatas.
3. **Waktu Komputasi & Efisiensi:** XGBoost membutuhkan waktu eksekusi yang signifikan lebih lama karena proses pencarian titik pemisahan (*exact greedy algorithm*) pada setiap level cabang pohon, sedangkan LightGBM menggunakan *histogram binning* yang memproses perhitungan dalam waktu sepersekian detik.

---

### IV. Kesimpulan Penulis
Model **LightGBM terbukti menjadi algoritma terbaik** dalam memprediksi harga instrumen yang memiliki volatilitas tinggi, mengungguli XGBoost dan SVR baik dari segi akurasi galat (MAE, RMSE) maupun stabilitas terhadap variasi partisi data dan dependensi *time step*.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Makalah dari Universitas Tarumanagara (UNTAR) ini membandingkan kinerja algoritma SVR, XGBoost, dan LightGBM pada data harian instrumen keuangan yang sangat volatil (Ethereum) selama 5 tahun. Melalui pengujian partisi data (80:20 vs 70:30) dan variasi *time step*, penelitian membuktikan secara konsisten bahwa **LightGBM mencatatkan performa terbaik dengan MAE paling rendah (75.486 pada 80:20 dan 78.228 pada 70:30)** serta efisiensi waktu komputasi yang jauh lebih unggul dibandingkan XGBoost.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Berbasis Batas Margin (SVR) pada Volatilitas Ekstrem:** SVR sering dianggap model standar untuk regresi time-series, namun kinerjanya merosot drastis pada aset dengan fluktuasi non-linear tinggi.
2. **Kebutuhan Uji Komparasi Objektif Antara Varian Tree-Boosting:** Di Indonesia, banyak penelitian skripsi masih terpaku pada SVR atau Random Forest, dan belum banyak studi komparatif lokal yang membuktikan secara empiris keunggulan LightGBM atas XGBoost pada deret waktu keuangan dengan variasi partisi data dan time step.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Mengetahui algoritma mana di antara SVR, XGBoost, dan LightGBM yang paling akurat dan efisien untuk memprediksi harga aset finansial berisiko tinggi.
- **Dataset:** Data historis 5 tahun harga harian Ethereum dari Investing.com.
- **Variabel:** Open, High, Low, Close.
- **Variasi Eksperimen:** Rasio split (80:20 vs 70:30) dan variasi time step.

### D. Solusi dari Penelitian
- Mengimplementasikan pipeline pemodelan terstandarisasi untuk SVR, XGBoost, dan LightGBM.
- Menguji pengaruh jendela geser (*sliding window/time step*).
- **Solusi Utama:** Menunjukkan bahwa LightGBM adalah model terbaik untuk deret waktu keuangan volatil karena memadukan ketahanan non-linear, nilai galat terendah, dan konsumsi memori yang sangat efisien.

### E. Relevansi & Nilai Tambah untuk Skripsi XAUUSD Anda
1. **Rujukan Nasional Berbahasa Indonesia:** Paper ini sangat bermanfaat untuk disitir di Bab 2 skripsi Anda sebagai bukti penelitian terdahulu tingkat nasional (Jurnal Ilmu Komputer dan Sistem Informasi) yang membandingkan LightGBM vs XGBoost vs SVR.
2. **Metodologi Pengujian Partisi Data & Time Step:** Anda dapat mengadopsi rancangan pengujian skripsi Anda dengan menguji performa model pada beberapa variasi split data (misalnya 80:20) dan jendela waktu (*time step / lag*) seperti yang dilakukan oleh peneliti UNTAR ini.
