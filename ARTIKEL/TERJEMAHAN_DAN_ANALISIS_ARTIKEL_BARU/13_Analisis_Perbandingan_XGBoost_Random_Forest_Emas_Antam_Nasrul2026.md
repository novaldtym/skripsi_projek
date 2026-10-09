# Analisis Mendalam: Perbandingan Algoritma XGBoost dan Random Forest dalam Peramalan Harga Emas Antam Menggunakan Indikator Teknikal

**File Asli:** `Perbandingan algoritma XGBoost dan Random Forest dalam peramalan harga emas Antam menggunakan indikator teknikal.pdf`  
**Penulis:** Nasrul Fadhila Akbar  
**Publikasi:** *Prosiding Seminar Nasional Indonesia* (Sociohum), Vol. 4, No. 1, Hal. 77–87 (2026)  
**Bahasa Asli:** Bahasa Indonesia  
**Jumlah Halaman:** 11 Halaman  

---

## 1. Ulasan Lengkap Struktur & Isi Makalah

### Abstrak
Emas merupakan instrumen investasi yang diminati luas karena sifatnya sebagai penyimpan nilai dan aset lindung nilai (*hedging*). Namun fluktuasi harga emas yang dinamis menuntut adanya pendekatan peramalan yang mampu memperkirakan tren pergerakan harga di masa depan. Penelitian ini bertujuan untuk membandingkan kinerja algoritma *eXtreme Gradient Boosting* (XGBoost) dan *Random Forest Regressor* dalam meramalkan harga penutupan harian emas Antam di Indonesia. 

Data historis yang digunakan dilengkapi dengan serangkaian indikator teknikal konvensional, seperti *Exponential Moving Average* (EMA), *Relative Strength Index* (RSI), dan *Moving Average Convergence Divergence* (MACD). Model dievaluasi menggunakan metrik *Mean Absolute Error* (MAE), *Root Mean Squared Error* (RMSE), dan *Mean Absolute Percentage Error* (MAPE). 

Hasil penelitian menunjukkan bahwa **algoritma XGBoost menghasilkan performa yang lebih unggul dibandingkan Random Forest**. XGBoost mencatatkan nilai MAPE sebesar **0.78%**, sementara Random Forest mencatatkan nilai MAPE sebesar **1.14%**. Keunggulan ini disebabkan oleh mekanisme optimasi gradien pada XGBoost yang secara bertahap memperbaiki galat residual dari pohon sebelumnya, sedangkan Random Forest hanya melakukan perataan independen (*bagging*).

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian nasional (2026) ini menguji perbandingan antara algoritma ensemble bagging (Random Forest) dan boosting (XGBoost) dalam meramalkan harga harian emas fisik Antam berbasis fitur indikator teknikal (EMA, RSI, MACD). Hasilnya membuktikan secara konsisten bahwa algoritma boosting (XGBoost) lebih unggul dalam menekan galat persentase (MAPE 0.78% vs 1.14%).

### B. Research Gap (Kesenjangan Penelitian)
1. **Minimnya Benchmark Komparasi Tree-Ensemble di Pasar Emas Indonesia:** Sebagian besar literatur emas domestik masih menggunakan ARIMA atau regresi sederhana. Studi ini mengisi celah dengan mengadu dua raja algoritma pohon: Random Forest vs XGBoost.
2. **Keterbatasan Cakupan Fitur:** Penelitian ini masih terbatas pada data harga emas domestik tunggal dan indikator teknikal dasar tanpa memasukkan variabel eksternal makro global (seperti kurs USD/IDR atau Indeks Dolar DXY).

### C. Apa yang Dibahas
- **Objek:** Harga penutupan harian emas Antam (Logam Mulia Indonesia).
- **Variabel Masukan:** Open, High, Low, Close, serta indikator teknikal EMA, RSI, dan MACD.
- **Model:** XGBoost Regressor vs Random Forest Regressor.

### D. Solusi dari Penelitian
- Mengonstruksi pipeline rekayasa fitur berbasis indikator teknikal.
- Melatih model dengan validasi silang deret waktu.
- **Temuan Kunci:** XGBoost unggul secara signifikan atas Random Forest karena mampu memodelkan residual galat secara sekuensial.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian Langsung:** Paper ini menjadi rujukan nasional pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 3).
- **Perbandingan dengan Skripsi Nouval:** 
  1. Akbar (2026) membandingkan XGBoost vs Random Forest pada emas fisik harian; Nouval melangkah lebih jauh dengan menguji **LightGBM** (yang terbukti lebih cepat dan akurat dibanding XGBoost) dan mengujinya pada time-series frekuensi tinggi M15/M5.
  2. Akbar hanya menggunakan 3 indikator teknikal dasar, sementara Nouval mengintegrasikan 36 fitur multi-source (Smart Money Concepts/SMC, Fibo, Anchor H4, Kanal DXY, dan Siklus Berita NFP).
