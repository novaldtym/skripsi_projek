# Terjemahan & Analisis: Silver Price Forecasting Using Extreme Gradient Boosting (XGBoost) Method

**File Asli:** `Silver price forecasting using Extreme Gradient Boosting (XGBoost) method..pdf`  
**Penulis:** D.N. Gono, H. Napitupulu, Firdaniza  
**Institusi:** Department of Mathematics, Universitas Padjadjaran (UNPAD), Bandung, Indonesia  
**Publikasi:** *Mathematics* (MDPI, Scopus Q1), Vol. 11, No. 18, Artikel 3813 (2023)  
**DOI:** `https://doi.org/10.3390/math11183813`  
**Jumlah Halaman:** 15 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Artikel ini menyajikan studi mengenai peramalan harga logam mulia perak (*silver*) menggunakan metode machine learning *Extreme Gradient Boosting* (XGBoost) dengan optimasi hiperparameter. Perak, sebagai logam mulia berharga yang digunakan secara luas di berbagai industri dan instrumen investasi, memperlihatkan fluktuasi harga yang sangat dinamis akibat permintaan pasar dan kondisi makroekonomi global. 

Penelitian ini menggunakan data deret waktu harga perak harian selama periode multi-tahun. Kami menerapkan teknik optimasi *Grid Search* dan *Random Search* untuk menyetel parameter kunci XGBoost (seperti laju pembelajaran, kedalaman pohon maksimal, dan rasio subsampel). Model dievaluasi menggunakan metrik RMSE, MAE, dan MAPE, serta dibandingkan dengan metode peramalan deret waktu konvensional (ARIMA) dan Support Vector Regression (SVR). 

Hasil eksperimen menunjukkan bahwa **model XGBoost yang dioptimasi menghasilkan akurasi peramalan yang sangat tinggi dengan nilai MAPE di bawah 1.5%**, jauh melampaui kemampuan model ARIMA dan SVR. Penelitian ini membuktikan bahwa algoritma gradient boosting berbasis pohon merupakan alat komputasi yang sangat andal untuk memodelkan deret waktu komoditas logam mulia.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Artikel ilmiah Q1 MDPI Mathematics (2023) dari peneliti Universitas Padjadjaran ini mendokumentasikan keunggulan algoritma XGBoost yang dioptimasi hiperparameternya dalam memprediksi harga komoditas logam mulia (perak). Hasilnya membuktikan XGBoost mencapai MAPE sangat rendah (< 1.5%) dan mengungguli ARIMA dan SVR.

### B. Research Gap (Kesenjangan Penelitian)
1. **Sensitivitas Hiperparameter pada Model Boosting Logam Mulia:** Algoritma gradient boosting sangat sensitif terhadap kombinasi parameter regularisasi dan kedalaman pohon; studi ini mengisi celah dengan mengevaluasi secara ketat dampak penyetelan parameter terhadap galat peramalan logam mulia.
2. **Keterbatasan Linearitas Model Finansial Tradisional:** Menguji apakah model non-linear pohon mampu menangani struktur fluktuasi logam mulia yang dipenuhi ketidakpastian.

### C. Apa yang Dibahas
- **Objek:** Harga harian komoditas logam mulia (Perak / Silver).
- **Model:** XGBoost dengan tuning vs ARIMA vs SVR.
- **Metrik:** RMSE, MAE, MAPE.

### D. Solusi dari Penelitian
- Menerapkan optimasi hiperparameter terstruktur pada XGBoost.
- Menunjukkan bahwa perpaduan regularisasi L1/L2 pada pohon boosting mencegah overfitting pada deret waktu logam mulia.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian:** Paper ini dikutip pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 5).
- **Relevansi:** Emas dan perak adalah dua logam mulia kembar (*precious metals*). Bukti bahwa gradient boosting mengungguli ARIMA dan SVR pada perak semakin memperkuat justifikasi Nouval menggunakan keluarga gradient boosting (**LightGBM**) pada emas XAUUSD.
