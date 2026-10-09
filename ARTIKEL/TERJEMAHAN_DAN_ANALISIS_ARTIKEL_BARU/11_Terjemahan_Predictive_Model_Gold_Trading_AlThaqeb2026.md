# Terjemahan & Analisis: Predictive Model Based on Machine Learning to Determine Gold Price Fluctuation and Improve Trading Decisions

**File Asli:** `Predictive Model Based on Machine Learning to Determine Gold Price Fluctuation and Improve Trading Decisions.pdf`  
**Penulis:** Saud Al-Thaqeb, Mohammad Algharabali, Abdullah Alanezi  
**Publikasi:** *Journal of Risk and Financial Management* (MDPI, Scopus Q2), Vol. 19, No. 7, Juli 2026  
**DOI:** `https://doi.org/10.3390/jrfm19070388`  
**Jumlah Halaman:** 28 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Harga emas mencerminkan interaksi dinamis antara kanal mata uang (*currency channel*), biaya peluang (*opportunity-cost channel*), dan kanal lindung nilai (*safe-haven channel*) yang kekuatannya bergeser secara dinamis di berbagai rezim pasar. Hal ini memotivasi perlunya pendekatan peramalan berbasis data (*data-driven*) secara empiris. 

Penelitian ini mengembangkan sistem peramalan harga emas menggunakan model machine learning—khususnya Random Forest (RF), Support Vector Machine (SVM), dan Artificial Neural Network (ANN)—yang diintegrasikan dengan kerangka kerja pendukung keputusan perdagangan (*trading decision support*). Variabel masukan mencakup indikator ekonomi makro, imbal hasil obligasi, indeks volatilitas pasar modal, dan data harga historis.

Hasil pengujian membuktikan bahwa model machine learning mampu menangkap transmisi guncangan ekonomi terhadap fluktuasi emas secara jauh lebih unggul dibandingkan model regresi deret waktu tradisional. Penggabungan sinyal prediksi ke dalam strategi perdagangan terbukti mampu meningkatkan rasio imbal hasil terhadap risiko (*risk-adjusted returns*), mengurangi *drawdown*, dan mengoptimalkan waktu eksekusi posisi.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian komprehensif 28 halaman dari MDPI JRFM (Juli 2026) ini membangun kerangka kerja prediktif berbasis machine learning (RF, SVM, ANN) untuk memodelkan pergeseran harga emas di bawah pengaruh kanal makroekonomi (kurs dolar, suku bunga riil, dan persepsi risiko pasar). Studi ini membuktikan bahwa machine learning yang diperkaya variabel makro mampu memandu keputusan trading dengan drawdown yang jauh lebih rendah daripada strategi pasif.

### B. Research Gap (Kesenjangan Penelitian)
1. **Kelemahan Model Ekonometrika Statis:** Model statistik konvensional mengasumsikan kekuatan pengaruh suku bunga dan kurs dolar terhadap emas bersifat konstan, padahal secara empiris kekuatan transmisi kanal makro bergeser secara tajam di antara rezim *risk-on* dan *risk-off*.
2. **Ketiadaan Validasi Keputusan Perdagangan Riil:** Mayoritas studi akademis berhenti pada metrik galat statistik (RMSE/MAE) tanpa menguji apakah sinyal tersebut mampu menghasilkan keputusan perdagangan yang aman dari risiko likuidasi atau drawdown besar.

### C. Apa yang Dibahas
- **Objek:** Harga emas global dan keputusan perdagangan.
- **Variabel Masukan:** Kurs mata uang global, inflasi, yield obligasi US Treasury, indeks volatilitas VIX, dan data OHLCV historis.
- **Model:** Random Forest, SVM, Artificial Neural Network (ANN).

### D. Solusi dari Penelitian
- Mengintegrasikan indikator makroekonomi sebagai fitur transisi rezim.
- Menghubungkan luaran prediksi model langsung ke dalam logika eksekusi trading untuk mengevaluasi *drawdown* dan imbal hasil portofolio.
- **Temuan Kunci:** Machine learning berbasis ensemble dan jaringan saraf mampu mengidentifikasi titik belok tren emas saat rilis data makro ekonomi terjadi.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian Sempurna:** Paper ini menjadi rujukan primer pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 1).
- **Nilai Tambah untuk Skripsi:** Nouval melangkah lebih maju: jika Al-Thaqeb et al. menggunakan horizon bulanan/harian makro, Nouval membawa integrasi makroekonomi (DXY dan Siklus Berita NFP/CPI/FOMC) langsung ke timeframe intraday M15 dan M5 dengan LightGBM, serta menambahkan proteksi Dynamic ATR Stop-Loss.
