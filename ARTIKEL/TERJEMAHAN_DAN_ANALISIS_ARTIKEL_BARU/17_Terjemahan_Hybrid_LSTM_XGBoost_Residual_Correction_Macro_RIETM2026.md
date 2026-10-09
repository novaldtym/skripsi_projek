# Terjemahan & Analisis: Hybrid LSTM–XGBoost Model with Residual Error Correction for Multivariate Gold Price Forecasting Using Macroeconomic Indicators

**File Asli:** `Hybrid LSTM–XGBoost model with residual error correction for multivariate gold price forecasting using macroeconomic indicators..pdf`  
**Publikasi:** *Research in Education, Technology, and Multiculture* (RIETM), Vol. 5, No. 1, Hal. 60–74, Maret 2026  
**DOI:** `https://doi.org/10.61436/rietm.2026.5.1.60`  
**Jumlah Halaman:** 15 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Emas memainkan peran penting dalam pasar keuangan global dan dipandang luas sebagai aset pelindung nilai (*hedge*) serta tempat berlindung yang aman (*safe haven*) selama periode ketidakpastian ekonomi. Oleh karena itu, peramalan harga emas yang akurat sangat penting untuk strategi investasi, alokasi portofolio, dan manajemen risiko. Namun, harga emas memperlihatkan sifat non-linearitas, non-stasioneritas, dan sensitivitas tinggi terhadap variabel makroekonomi yang kompleks. 

Penelitian ini mengusulkan sebuah model peramalan harga emas multivariat baru, yaitu **Hybrid LSTM–XGBoost dengan Koreksi Galat Residual (*Residual Error Correction*)**. Kerangka kerja ini memanfaatkan model *Long Short-Term Memory* (LSTM) untuk menangkap dependensi temporal jangka panjang dan tren sekuensial harga emas berdasarkan indikator makroekonomi (inflasi, suku bunga, dan nilai tukar dolar). Selanjutnya, komponen galat residual yang tidak tertangkap oleh LSTM dimodelkan dan dikoreksi menggunakan algoritma *Extreme Gradient Boosting* (XGBoost). 

Hasil eksperimen membuktikan bahwa model hibrida dengan koreksi galat residual ini secara signifikan mengungguli model LSTM tunggal, XGBoost tunggal, dan model autoregresif klasik dalam metrik RMSE, MAE, dan MAPE.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Artikel ilmiah Maret 2026 ini merancang arsitektur **Hybrid LSTM–XGBoost** di mana LSTM memprediksi tren temporal primer dari variabel makroekonomi, kemudian XGBoost digunakan untuk mengoreksi galat sisa (*residual error correction*). Hasilnya membuktikan kombinasi ini memangkas galat secara signifikan dibanding model tunggal mana pun.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Deep Learning Murni pada Residual Galat:** Jaringan saraf seperti LSTM cenderung menghasilkan bias sisa yang berkorelasi ketika berhadapan dengan data keuangan ber-noise tinggi.
2. **Ketiadaan Mekanisme Koreksi Galat:** Belum banyak studi yang secara terstruktur menggunakan algoritma gradient tree boosting untuk mengekstrak pola dari residu model sekuensial.

### C. Apa yang Dibahas
- **Objek:** Harga emas spot global multivariat.
- **Variabel:** Harga emas dan indikator makroekonomi (suku bunga, inflasi, indeks dolar).
- **Model:** LSTM (pemodel tren) + XGBoost (korektor residual).

### D. Solusi dari Penelitian
- Membangun mekanisme dua tahap: estimasi tren dasar dengan LSTM, lalu pemodelan galat $e_t = y_t - \hat{y}_{LSTM}$ menggunakan XGBoost.
- Menghasilkan prediksi akhir: $\hat{y}_{final} = \hat{y}_{LSTM} + \hat{e}_{XGBoost}$.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian:** Paper ini memperkuat justifikasi skripsi Nouval bahwa keluarga **Gradient Boosting** memiliki kemampuan superior dalam menangkap pola non-linear dan residual pasar yang tidak bisa ditangkap oleh model sekuensial sederhana.
