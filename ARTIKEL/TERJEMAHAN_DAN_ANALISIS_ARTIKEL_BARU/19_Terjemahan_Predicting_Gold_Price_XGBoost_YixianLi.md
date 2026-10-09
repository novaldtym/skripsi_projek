# Terjemahan & Analisis: Predicting the Gold Price Based on XGBoost

**File Asli:** `Predicting the gold price based on XGBoost..pdf`  
**Penulis:** Yixian Li  
**Institusi:** Ulink College of Shanghai, China  
**Tahun:** 2024  
**Jumlah Halaman:** 5 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Dalam beberapa tahun terakhir, peramalan harga emas yang akurat menjadi semakin penting bagi investor, ekonom, dan pembuat kebijakan moneter. Untuk meningkatkan akurasi peramalan tersebut, berbagai model machine learning telah dieksplorasi secara luas. Makalah ini bertujuan untuk memprediksi harga emas menggunakan algoritma *Extreme Gradient Boosting* (XGBoost). 

Dataset yang digunakan mencakup harga emas historis yang dipadukan dengan beberapa indikator teknikal deret waktu. Kinerja model dievaluasi menggunakan metrik *Mean Squared Error* (MSE) dan koefisien determinasi ($R^2$). Eksperimen menunjukkan bahwa XGBoost mampu memetakan tren volatilitas harga emas dengan tingkat galat yang sangat rendah dan menunjukkan konvergensi yang stabil selama proses pelatihan. Penelitian ini menegaskan potensi besar algoritma ensemble pohon keputusan dalam pemodelan aset komoditas berisiko tinggi.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper (2024) ini mengeksplorasi efektivitas algoritma XGBoost dalam meramalkan harga emas dengan metrik evaluasi MSE dan $R^2$. Hasilnya menunjukkan kemampuan XGBoost dalam memetakan dinamika harga emas dengan galat yang rendah dan keandalan tinggi.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Regresi Linier Standar:** Regresi konvensional gagal menangkap non-linearitas harga komoditas emas.
2. **Kebutuhan Evaluasi Gradient Boosting:** Perlunya pembuktian empiris bahwa model ensemble boosting cocok untuk deret waktu emas.

### C. Solusi Penelitian & Keterkaitan dengan Skripsi Nouval
- Memberikan bukti pendukung bahwa keluarga *Gradient Boosting Decision Tree* (GBDT) merupakan arsitektur yang paling tepat untuk data time-series harga emas. Skripsi Nouval menggunakan **LightGBM** yang merupakan evolusi lanjutan dari XGBoost dengan kecepatan komputasi lebih tinggi dan efisiensi memori yang jauh lebih baik.
