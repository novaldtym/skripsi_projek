# Terjemahan & Analisis Mendalam: Gold Price Prediction System Using the Random Forest Method

**File Asli:** `6.+173-Kurnia+A.pdf`  
**Penulis:** Kurnia Agung Prastyo, Hidayatus Sibyan, Nur Hasanah  
**Institusi:** Universitas Sains Al-Qur'an (UNSIQ), Wonosobo, Jawa Tengah, Indonesia  
**Publikasi:** *Clean Energy and Smart Technology* (CEST), Vol. 4, No. 1, Hal. 39–44 (Oktober 2025)  
**DOI:** `https://doi.org/10.58641/cest.v4i1.173`  
**Jumlah Halaman:** 6 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Emas merupakan salah satu komoditas terpenting yang berfungsi sebagai instrumen investasi sekaligus lindung nilai (*hedging*) terhadap inflasi. Tingginya volatilitas harga emas menuntut tersedianya prediksi yang akurat untuk mendukung pengambilan keputusan investasi. Penelitian ini bertujuan untuk mengembangkan sistem prediksi harga emas menggunakan metode *Random Forest* berbasis *machine learning*. 

Dataset yang digunakan terdiri dari data harga emas harian yang diunduh dari Yahoo Finance untuk rentang periode tahun 2020 hingga 2024. Tahapan penelitian mencakup pengumpulan data, pra-pemrosesan (*preprocessing*), pelatihan model, evaluasi, dan implementasi ke dalam sistem aplikasi berbasis situs web interaktif (Streamlit). 

Hasil evaluasi menunjukkan nilai **MAE sebesar USD 329.31**, **MSE sebesar 148,599.40**, **RMSE sebesar USD 385.49**, dan **nilai $R^2$ bernilai negatif (-1.97)**. Nilai metrik ini mengindikasikan bahwa model Random Forest yang dibangun belum mencapai tingkat akurasi yang memuaskan dan gagal mengungguli estimasi rata-rata sederhana pada data uji. Meskipun demikian, sistem aplikasi yang dibangun berhasil memberikan visualisasi umum mengenai arah pergerakan harga emas. Penulis menyarankan perlunya peningkatan arsitektur model melalui integrasi variabel eksternal yang lebih kompleks serta penerapan algoritma ensemble yang lebih canggih seperti **XGBoost atau LightGBM**.

**Kata Kunci:** Prediksi harga emas, Random Forest, machine learning, investasi, Streamlit

---

### I. Pendahuluan
Perkembangan teknologi finansial (Fintech) telah mempermudah investor ritel dalam mengakses berbagai instrumen keuangan. Di tengah ketidakpastian pasar saham dan kripto, emas tetap menjadi aset favorit karena reputasinya sebagai instrumen penyimpan nilai yang aman (*safe haven*). Namun, harga emas dunia bergerak dengan volatilitas yang cukup dinamis, dipengaruhi oleh suku bunga The Fed, inflasi global, dan dinamika geopolitik.

Beberapa penelitian sebelumnya menunjukkan keberhasilan Random Forest dalam memprediksi harga komoditas (seperti Wahyuningsih, 2024; Hutagalung et al., 2023). Hal ini mendorong penulis untuk membangun purwarupa (*prototype*) sistem informasi prediksi harga emas yang dapat diakses secara mudah oleh masyarakat umum melalui antarmuka web interaktif.

---

### II. Metodologi Penelitian & Pemrosesan Data

#### A. Pengumpulan Data
Data harga emas harian diperoleh dari Yahoo Finance dengan ticker emas fisik dunia, mencakup periode Januari 2020 hingga awal 2024. Variabel yang digunakan mencakup Open, High, Low, Close, dan Volume harian.

#### B. Pipeline Pra-pemrosesan & Pemodelan
1. **Pembersihan Data:** Memeriksa *missing values* dan format tanggal.
2. **Pembagian Data:** Data dibagi menjadi data latih (*training set*) sebesar 80% dan data uji (*testing set*) sebesar 20% secara kronologis waktu.
3. **Pelatihan Random Forest:** Menggunakan pustaka Scikit-Learn dengan parameter default dan variasi jumlah pohon (*n_estimators*).
4. **Pengembangan Sistem:** Sistem antarmuka dibangun menggunakan kerangka kerja Python Streamlit yang menyediakan visualisasi grafik aktual vs prediksi serta unduh data ke Excel.

---

### III. Hasil Pengujian, Evaluasi, dan Pembahasan

Evaluasi dilakukan menggunakan data uji out-of-sample dengan metrik standar:
- **Mean Absolute Error (MAE):** 329.31 USD
- **Root Mean Squared Error (RMSE):** 385.49 USD
- **Mean Squared Error (MSE):** 148,599.40
- **Koefisien Determinasi ($R^2$):** **-1.97**

#### Pembahasan Kegagalan Model ($R^2$ Negatif):
Penulis secara transparan dan jujur menganalisis penyebab mengapa model Random Forest menghasilkan $R^2$ negatif (-1.97):
1. **Kelemahan Inheren Random Forest terhadap Tren Finansial:** Random Forest melakukan prediksi berdasarkan rata-rata nilai pada daun pohon keputusan (*decision tree leaf averaging*). Model ini secara matematis tidak mampu memprediksi nilai yang berada di luar rentang nilai historis yang pernah dilihat pada data latih. Ketika harga emas pada periode uji (2023-2024) melonjak menembus rekor harga tertinggi baru di atas 2.000-2.400 USD/oz, Random Forest memotong prediksinya (*plateau effect*) pada harga tertinggi data latih, menyebabkan deviasi galat yang sangat masif!
2. **Ketiadaan Fitur Transformasi & Indikator Teknikal:** Model hanya dilatih menggunakan harga nominal mentah tanpa diferensiasi (stasioneritas) dan tanpa fitur indikator teknikal momentum (seperti RSI atau MACD).
3. **Ketiadaan Variabel Makroekonomi:** Model tidak mempertimbangkan faktor eksternal seperti pergerakan kurs dolar AS atau suku bunga.

---

### IV. Kesimpulan & Rekomendasi Penulis
Meskipun sistem website berhasil diimplementasikan dengan baik, kinerja prediktif Random Forest pada harga emas dinilai tidak memadai karena galat yang tinggi dan $R^2$ negatif.
Penulis memberikan rekomendasi kritis untuk penelitian selanjutnya:
1. Menambahkan variabel prediktor yang lebih kompleks seperti tingkat inflasi, suku bunga, dan nilai tukar mata uang.
2. Melakukan optimasi hiperparameter secara sistematis dengan Grid Search atau Bayesian Optimization.
3. **Mengganti atau mengimplementasikan algoritma ensemble yang lebih responsif dan canggih, seperti XGBoost atau LightGBM, untuk meningkatkan sensitivitas terhadap volatilitas pasar emas.**

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Studi dari peneliti Indonesia (UNSIQ, Oktober 2025) ini membangun sistem prediksi harga emas berbasis web (Streamlit) menggunakan algoritma Random Forest pada data harian 2020–2024. Hasil evaluasi empiris membuktikan bahwa **Random Forest pada data harga nominal mentah mengalami kegagalan fatal dengan $R^2$ bernilai negatif (-1.97) dan RMSE sangat besar (385.49 USD)** karena ketidakmampuannya mengekstrapolasi tren harga baru yang menembus rekor historis. Penulis secara eksplisit merekomendasikan penggunaan **LightGBM / XGBoost** dan penambahan indikator teknikal/makroekonomi sebagai solusi utama.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kegagalan Ekstrapolasi Model Pohon Bagging pada Data Non-Stasioner:** Sebagian besar penelitian yang mengklaim Random Forest berhasil pada harga emas menguji model pada data yang terdistribusi acak (shuffled split), bukan pengujian urutan waktu murni (*time-series split*). Ketika diuji secara realistis pada periode harga menembus tren baru (*all-time high*), model pohon bagging menghasilkan prediksi horizontal yang menghasilkan galat raksasa ($R^2 < 0$).
2. **Kebutuhan Transformasi Target & Model Boosting:** Belum diterapkannya transformasi stasioneritas (selisih harga/return) dan pemodelan gradient boosting (LightGBM) yang memodelkan residu galat dinamis.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Menguji kelayakan algoritma Random Forest untuk sistem peramalan harga emas bagi investor dan menganalisis keterbatasan model saat terjadi lonjakan harga.
- **Dataset:** Harga harian emas Yahoo Finance periode 2020–2024.
- **Variabel:** Open, High, Low, Close, Volume.
- **Metrik:** MAE, MSE, RMSE, $R^2$.

### D. Solusi dari Penelitian & Saran Solusi
- Penulis merekomendasikan transisi dari Random Forest ke algoritma **LightGBM atau XGBoost**.
- Mengintegrasikan fitur indikator makroekonomi dan indikator teknikal untuk memberi sinyal momentum kepada model.
- Mengoptimalkan hiperparameter menggunakan algoritma pencarian sistematis.

### E. Relevansi & Nilai Emas untuk Skripsi XAUUSD Anda (Sangat Krusial!)
1. **Bukti Pembenaran Ilmiah (Justifikasi Masalah di Bab 1):** Ini adalah salah satu paper terpenting untuk skripsi Anda! Anda dapat mengutip kegagalan empiris paper Kurnia et al. (2025) ini di Bab 1 untuk menjelaskan: *"Penelitian terbaru oleh Prastyo et al. (2025) menunjukkan bahwa algoritma Random Forest menghasilkan nilai $R^2$ negatif (-1.97) dan RMSE sebesar 385.49 saat memprediksi harga emas karena ketidakmampuannya beradaptasi dengan volatilitas dan tren rekor harga baru. Oleh karena itu, penelitian ini mengusulkan penggunaan algoritma LightGBM yang dilengkapi dengan rekayasa fitur indikator teknikal..."*
2. **Kutipan Rekomendasi Langsung:** Penulis paper ini secara eksplisit menyebutkan dalam kesimpulannya bahwa LightGBM adalah model yang direkomendasikan untuk memecahkan kelemahan tersebut. Anda adalah peneliti yang merealisasikan solusi yang mereka rekomendasikan!
