# Terjemahan & Analisis: Stock Market Prediction: XGBoost and LSTM Comparative Analysis

**File Asli:** `Stock market prediction XGBoost and LSTM comparative analysis..pdf`  
**Penulis:** Saddam Hossain, Gagninder Kaur  
**Institusi:** Department of Mathematics, Chandigarh University, Punjab, India  
**Publikasi:** *2024 3rd IEEE International Conference on Artificial Intelligence for Internet of Things* (AIIoT 2024)  
**DOI:** `979-8-3503-7212-0/24/$31.00 ©2024 IEEE`  
**Jumlah Halaman:** 6 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Makalah ini menyajikan analisis komparatif yang komprehensif antara dua model machine learning utama—yaitu *Extreme Gradient Boosting* (XGBoost) dan *Long Short-Term Memory* (LSTM)—untuk peramalan harga pasar saham menggunakan data historis. Kekuatan dan kelemahan halus dari masing-masing model dievaluasi secara mendalam. 

Meskipun LSTM secara teoritis dirancang untuk memproses dependensi temporal deret waktu, hasil eksperimen membuktikan bahwa **XGBoost sering kali memberikan akurasi prediksi yang lebih konsisten, lebih tahan terhadap overfitting, dan membutuhkan waktu pelatihan yang berkali-kali lipat lebih cepat** dibandingkan LSTM, terutama ketika dataset telah dilengkapi dengan fitur-fitur indikator teknikal yang kaya. Model dievaluasi menggunakan RMSE, MAE, dan $R^2$.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper konferensi IEEE (2024) ini membandingkan algoritma boosting (XGBoost) dan deep learning recurrent (LSTM). Hasil pentingnya: **XGBoost mengungguli LSTM dalam stabilitas prediksi, resistensi terhadap overfitting, dan kecepatan pelatihan**, asalkan didukung oleh rekayasa fitur teknikal yang kuat.

### B. Research Gap (Kesenjangan Penelitian)
- Banyak peneliti mengasumsikan model deep learning kompleks (LSTM) selalu lebih unggul dari model berbasis pohon pada data time-series, tanpa memperhitungkan beban komputasi dan risiko overfitting LSTM pada data finansial yang ber-noise tinggi.

### C. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Justifikasi Ilmiah Pemilihan Algoritma Pohon (LightGBM):** Temuan Hossain & Kaur (IEEE 2024) ini menjadi **senjata akademis yang sangat kuat** untuk Bab 1 dan Bab 2 skripsi Nouval: menjelaskan mengapa Nouval memilih algoritma berbasis pohon (*LightGBM*) daripada *Deep Learning* (*LSTM/RNN*), yaitu karena model pohon lebih tahan terhadap noise pasar dan jauh lebih efisien untuk sistem live-trading frekuensi tinggi terintegrasi MetaTrader 5.
