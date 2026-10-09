# Terjemahan & Analisis Mendalam: Gold Price Prediction Using Random Forest Algorithm

**File Asli:** `Gold-Price-Prediction-using-Random-Forest-Algorithm.pdf`  
**Penulis:** Utkarsh Landge, Ojas Phokmare, Nikhil Borane, Prof. Priya Shelke  
**Institusi:** Department of Information Technology, Vishwakarma Institute of Information Technology, Pune, India  
**Tahun:** 2023 / 2024  
**Jumlah Halaman:** 6 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Harga emas merupakan salah satu faktor paling penting dan berpengaruh bagi perekonomian suatu negara maupun pasar modalnya. Penelitian ini melakukan studi ekstensif untuk menginterpretasikan korelasi antara harga emas dengan serangkaian parameter pasar keuangan lainnya. Parameter yang dipertimbangkan dalam studi ini meliputi: Tanggal, SPX (Indeks Saham S&P 500), USO (Indeks Harga Minyak Mentah Amerika Serikat), SLV (Harga Perak), EUR/USD (Nilai Tukar Mata Uang Euro terhadap Dolar AS), dan GLD (Harga Emas fisik/ETF). 

Di antara seluruh parameter tersebut, variabel target yang diprediksi adalah GLD (harga emas pada tanggal tertentu) yang bergantung pada faktor-faktor pasar lainnya. SPX mencakup sekitar 500 perusahaan terbesar di bursa saham AS. USO merepresentasikan pergerakan harga minyak mentah AS. SLV adalah harga perak pada hari tertentu. Pasangan mata uang EUR/USD mencerminkan kekuatan nilai tukar dolar terhadap euro. 

Kami melatih model *Random Forest* untuk memprediksi harga emas berdasarkan nilai interaksi dari SPX, USO, SLV, dan EUR/USD. Model dievaluasi dan dibandingkan dengan algoritma pembanding tradisional seperti regresi linear dan model deret waktu ARIMA untuk membuktikan efektivitas pemodelan multi-aset berbasis machine learning.

---

### I. Pendahuluan & Korelasi Antar-Aset Pasar Finansial
Kemampuan meramalkan tren harga emas di masa depan sangat penting dalam sektor finansial. Perbaikan kecil sekalipun dalam akurasi peramalan dapat menghasilkan keuntungan signifikan atau menghindari kerugian besar dalam manajemen portofolio.
Emas dipengaruhi oleh berbagai faktor fundamental:
1. **Inflasi:** Emas menjadi instrumen penyimpan nilai utama saat daya beli mata uang fiat tergerus.
2. **Kekuatan Dolar AS (USD):** Karena emas dihargai dalam dolar AS, penguatan dolar umumnya menekan harga emas, dan sebaliknya (korelasi negatif).
3. **Komoditas Lain (Perak & Minyak):** Perak (SLV) bergerak sejalan dengan emas sebagai logam mulia, sementara minyak (USO) mencerminkan biaya energi global yang mendorong inflasi.
4. **Pasar Saham (SPX):** Mencerminkan sentimen risiko pasar (*risk-on* vs *risk-off*). Ketika pasar saham jatuh, modal berpindah ke emas sebagai aset perlindungan (*safe haven*).

---

### II. Landasan Teori & Metodologi

#### A. Dataset & Fitur Multi-Pasar
Dataset historis mencakup periode perdagangan multivariat dengan atribut:
- `SPX`: S&P 500 Index (Ekuitas)
- `USO`: United States Oil Fund (Komoditas Energi)
- `SLV`: iShares Silver Trust (Logam Mulia)
- `EUR/USD`: Kurs mata uang utama dunia (Forex)
- `GLD`: SPDR Gold Shares (Target Emas)

#### B. Algoritma Random Forest Regressor
Random Forest adalah algoritma ensemble berbasis *bagging* (Bootstrap Aggregating) yang membangun kumpulan pohon keputusan secara acak.
Kelebihan utama Random Forest dalam studi ini:
1. Mampu menangkap hubungan korelasi non-linear yang rumit antar-pasar (inter-market analysis) tanpa asumsi linearitas.
2. Kebal terhadap masalah multikolinearitas antar variabel makro/komoditas.
3. Memberikan estimasi *feature importance* (tingkat kepentingan fitur) untuk melihat aset mana yang paling mendikte harga emas.

---

### III. Hasil Eksperimen Kuantitatif

Penelitian mengevaluasi Random Forest dan membandingkannya dengan model ARIMA, Regresi Linier, dan Support Vector Machine (SVM kernel Polinomial):

#### Temuan Kunci:
1. **Korelasi Perak (SLV) Paling Dominan:** Analisis korelasi membuktikan bahwa harga perak (SLV) memiliki korelasi positif terkuat dengan harga emas (GLD) dengan koefisien korelasi melebihi 0.85.
2. **Kelemahan ARIMA:** Model ARIMA (2,1,2) hanya bergantung pada harga masa lalu dan gagal beradaptasi ketika terjadi pergeseran tren yang didorong oleh guncangan pasar eksternal (menghasilkan RMSE tinggi 36.1795 dan $R^2$ 86%).
3. **Kinerja Random Forest:** Random Forest berhasil memetakan interaksi multi-pasar dengan akurasi sangat tinggi ($R^2 > 98\%$), menunjukkan bahwa menyertakan variabel pasar eksternal (minyak, perak, bursa saham, kurs dolar) secara dramatis meningkatkan daya prediksi dibandingkan pemodelan univariat semata.
4. **Keterbatasan Random Forest:** Meskipun akurat pada data dalam rentang sampel, Random Forest mengalami kesulitan ekstrapolasi jika harga emas menembus rekor tertinggi baru (*all-time high*) di luar rentang nilai data latih.

---

### IV. Kesimpulan Penulis
Mengintegrasikan parameter ekonomi multi-pasar (SPX, USO, SLV, EUR/USD) ke dalam model machine learning berbasis pohon seperti Random Forest menghasilkan pemodelan harga emas yang jauh lebih superior dibandingkan model time-series klasik univariat seperti ARIMA.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian ini membuktikan efektivitas pemodelan harga emas (GLD) menggunakan algoritma **Random Forest** dengan memanfaatkan fitur korelasi multi-pasar (*inter-market features*), yaitu indeks saham AS (SPX), harga minyak (USO), harga perak (SLV), dan nilai tukar mata uang (EUR/USD). Hasilnya menunjukkan bahwa fitur multi-aset eksternal secara drastis meningkatkan akurasi model ($R^2 > 98\%$) dan mengungguli model univariat konvensional (ARIMA) yang memiliki galat besar (RMSE 36.1795).

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Univariat Tradisional:** Sebagian besar studi peramalan emas hanya mengandalkan data historis harga emas itu sendiri (univariat), mengabaikan kenyataan bahwa emas sangat berkorelasi dengan dinamika aset global lain (dolar, perak, minyak, dan ekuitas).
2. **Keterbatasan Ekstrapolasi Random Forest:** Meskipun Random Forest mampu memodelkan korelasi multi-aset, algoritma bagging ini memiliki kelemahan matematis fundamental yaitu ketidakmampuan mengekstrapolasi tren di luar batas nilai daun (*leaf boundaries*). Kesenjangan ini membuka peluang bagi model gradient boosting (seperti LightGBM) yang memodelkan residu gradien untuk menangkap tren dinamis lebih baik.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Mengetahui sejauh mana parameter eksternal multi-pasar mampu meningkatkan akurasi prediksi harga emas.
- **Dataset:** Data historis pasar finansial harian meliputi SPX, USO, SLV, EUR/USD, dan GLD.
- **Variabel Independen:** Nilai pasar SPX, USO, SLV, EUR/USD.
- **Variabel Dependen:** Nilai GLD (harga emas).

### D. Solusi dari Penelitian
- Mengonstruksi dataset multivariat antar-pasar.
- Melatih Random Forest Regressor untuk memetakan interaksi non-linear multi-aset ke harga emas.
- **Solusi Utama:** Menunjukkan bahwa perak (SLV) dan kurs dolar (EUR/USD) merupakan prediktor paling signifikan terhadap harga emas, dan model pohon keputusan ensemble jauh lebih tangguh daripada ARIMA univariat.

### E. Relevansi & Rekomendasi untuk Skripsi XAUUSD Anda
1. **Fitur Korelasi Wajib untuk Skripsi:** Dalam memprediksi XAUUSD, jangan hanya mengandalkan harga XAUUSD semata! Anda dapat memasukkan data instrumen berkorelasi seperti DXY (US Dollar Index), US10Y (Yield Obligasi AS), atau harga perak/minyak sebagai fitur eksogen.
2. **Justifikasi Memilih LightGBM Dibandingkan Random Forest:** Anda dapat mengutip keterbatasan Random Forest dari paper ini untuk memperkuat alasan mengapa skripsi Anda memilih **LightGBM**: LightGBM menggunakan *gradient-based boosting* dan *leaf-wise growth* yang lebih responsif terhadap perubahan tren baru dibandingkan Random Forest yang bersifat statis averaging.
