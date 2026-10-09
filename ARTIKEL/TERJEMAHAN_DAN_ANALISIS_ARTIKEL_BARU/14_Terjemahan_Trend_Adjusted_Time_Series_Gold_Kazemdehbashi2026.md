# Terjemahan & Analisis: Trend-Adjusted Time Series Models with an Application to Gold Price Forecasting

**File Asli:** `Trend_Adjusted_Time_Series_Models_Gold_Price_Forecasting_arXiv_2026.pdf`  
**Penulis:** Sina Kazemdehbashi  
**Institusi:** Department of Industrial and Systems Engineering, Wayne State University, Detroit, MI, USA  
**Publikasi:** arXiv:2601.12706 (Januari 2026)  
**Jumlah Halaman:** 13 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Data deret waktu memainkan peran penting di berbagai bidang, termasuk keuangan, kesehatan, pemasaran, dan teknik. Berbagai teknik—mulai dari model statistik klasik hingga pendekatan jaringan saraf seperti *Long Short-Term Memory* (LSTM)—telah banyak dikembangkan untuk meramalkan tren deret waktu. Namun, deret waktu finansial seperti harga emas kerap memperlihatkan sifat non-stasioneritas yang ekstrem, volatilitas tinggi, dan pergeseran tren yang mendadak. 

Dalam studi ini, kami mengusulkan kerangka kerja baru yang disebut **Trend-Adjusted Time Series (TATS)** yang memisahkan proses peramalan menjadi dua sub-tugas terkoordinasi: 
1. Klasifikasi arah tren harga (*trend direction classification*).
2. Penyesuaian besaran magnitudo (*magnitude adjustment*).

Kerangka kerja TATS dievaluasi menggunakan data historis harga emas spot global harian dan dibandingkan dengan model benchmark standar termasuk ARIMA, LSTM murni, dan Bi-LSTM. Hasil empiris membuktikan bahwa memisahkan prediksi arah tren dari estimasi magnitudo nominal secara dramatis menurunkan galat kuadrat terkecil (MSE dan RMSE) serta secara signifikan meningkatkan akurasi arah (*directional accuracy* / AUC) peramalan harga emas.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Naskah ilmiah terbaru (Januari 2026) dari Wayne State University ini memperkenalkan metodologi **Trend-Adjusted Time Series (TATS)** untuk peramalan harga emas. Terobosan metodologis paper ini adalah mendekonstruksi masalah peramalan harga menjadi **klasifikasi arah tren** terlebih dahulu, baru kemudian menyesuaikan besaran perubahannya. Hasilnya membuktikan pemisahan ini jauh lebih akurat daripada memprediksi harga nominal secara langsung dengan LSTM atau ARIMA.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kegagalan Model Regresi Tunggal pada Deret Non-Stasioner:** Model regresi langsung (baik statistik maupun neural net) cenderung meniru level harga terakhir dan terlambat merespons saat terjadi pembalikan arah tren (*trend reversal*).
2. **Kebutuhan Pendekatan Modular Berbasis Klasifikasi Arah:** Diperlukan kerangka kerja yang terlebih dahulu memfokuskan model pada pemisahan sinyal arah (*directional signal*) sebelum mengestimasi nilai nominal.

### C. Apa yang Dibahas
- **Objek:** Harga emas spot global harian.
- **Metode:** Trend-Adjusted Time Series (TATS) yang menggabungkan pengklasifikasi arah dengan model sekuensial deret waktu.
- **Metrik:** MSE, RMSE, MAE, dan Directional Accuracy (DA).

### D. Solusi dari Penelitian
- Memformulasikan target awal sebagai klasifikasi biner arah tren (Naik vs Turun).
- Mengintegrasikan hasil probabilitas klasifikasi arah untuk mengalibrasi prediksi besaran perubahan harga.
- **Temuan Kunci:** Pendekatan berbasis klasifikasi arah mampu melipatgandakan ketahanan model terhadap *false breakout* dan guncangan harga emas.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian Sangat Kuat:** Paper ini menjadi rujukan utama pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 4).
- **Penguatan Landasan Teori Nouval:** Temuan Kazemdehbashi (2026) ini adalah **pembenaran teoretis paling solid** mengapa skripsi Nouval merumuskan masalah sebagai **klasifikasi probabilitas arah (LGBMClassifier 5 candle ke depan)** dan bukan regresi harga nominal! Argumen ini memperkuat paragraf 7 pada sub-bab 1.1 skripsi Nouval.
