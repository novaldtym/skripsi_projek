# Terjemahan & Analisis: A Gold and Bitcoin Trading Model Based on XGBoost Prediction

**File Asli:** `A gold and Bitcoin trading model based on XGBoost prediction..pdf`  
**Penulis:** Shuo Liu  
**Institusi:** College of Information Science and Engineering, Northeastern University, Shenyang, China  
**Publikasi:** *Proceedings of the 2024 International Conference on Data Engineering and Artificial Intelligence* (ACM DEAI 2024), Januari 2024  
**DOI:** `https://doi.org/10.1145/3652628.3652635`  
**Jumlah Halaman:** 5 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Transaksi yang melibatkan emas dan Bitcoin telah menarik banyak perhatian di kalangan investor global karena keduanya memiliki potensi pengembalian yang tinggi serta karakteristik lindung nilai yang unik. Namun, volatilitas tinggi pada kedua aset tersebut membawa risiko pasar yang besar. Penelitian ini membangun sebuah model strategi perdagangan kuantitatif untuk emas dan Bitcoin berdasarkan prediksi algoritma *eXtreme Gradient Boosting* (XGBoost). 

Data harga historis harian dikumpulkan dan diproses menggunakan teknik rekayasa fitur moving average dan momentum. Model XGBoost dilatih untuk meramalkan arah perubahan harga harian. Berdasarkan probabilitas keluaran model, kami merancang aturan alokasi portofolio dinamis dengan biaya transaksi riil untuk menentukan kapan harus memegang uang tunai, membeli emas, atau membeli Bitcoin. 

Hasil simulasi pengujian membuktikan bahwa strategi berbasis model XGBoost mampu menghasilkan laba kumulatif yang jauh lebih tinggi dibandingkan strategi *buy-and-hold* tradisional, serta berhasil membatasi *maximum drawdown* saat terjadi koreksi pasar yang tajam.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper dari konferensi internasional ACM (2024) ini mengusulkan sistem perdagangan kuantitatif untuk Emas dan Bitcoin yang ditenagai oleh model prediksi XGBoost. Prediksi arah harga diubah menjadi strategi alokasi aset dinamis yang memperhitungkan biaya komisi transaksi. Hasilnya membuktikan strategi berbasis XGBoost mampu mengalahkan strategi *buy-and-hold* dan menekan *drawdown*.

### B. Research Gap (Kesenjangan Penelitian)
1. **Pemisahan Prediksi dari Eksekusi Portofolio:** Sebagian besar literatur ML hanya berfokus pada akurasi prediksi angka, tanpa merancang aturan trading kuantitatif yang memperhitungkan biaya transaksi (*transaction costs* / slippage).
2. **Kebutuhan Alokasi Aset Dinamis Antara Safe Haven dan Kripto.**

### C. Apa yang Dibahas
- **Objek:** Harga harian Emas (XAU) dan Bitcoin (BTC).
- **Variabel:** Harga Open, High, Low, Close, Moving Averages.
- **Model:** XGBoost Classifier/Regressor + Dynamic Portfolio Rebalancing Engine.

### D. Solusi dari Penelitian
- Mengonversi sinyal prediksi pohon boosting menjadi sinyal perdagangan Buy/Sell/Hold.
- Menerapkan manajemen risiko modal dengan memperhitungkan biaya komisi.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian:** Sangat relevan dengan pilar **Live Execution & Risk Management** skripsi Nouval! Nouval mengadopsi prinsip yang sama namun dalam eksekusi jauh lebih maju: Nouval menggunakan **LightGBM Classifier**, terhubung langsung dengan **MetaTrader 5 API secara real-time**, dan memiliki modul proteksi ketat (**Dynamic ATR Stop-Loss, Risk-Reward 1:1.5, dan Confidence Guard $\ge 65\%$**).
