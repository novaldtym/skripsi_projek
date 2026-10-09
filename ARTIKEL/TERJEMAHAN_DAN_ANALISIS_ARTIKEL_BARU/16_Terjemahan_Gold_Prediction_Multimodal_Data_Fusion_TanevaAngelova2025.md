# Terjemahan & Analisis: A Framework for Gold Price Prediction Combining Classical and Intelligent Methods with Financial, Economic, and Sentiment Data Fusion

**File Asli:** `A framework for gold price prediction combining classical and intelligent methods with financial, economic, and sentiment data fusion..pdf`  
**Penulis:** Gergana Taneva-Angelova, Subeesh et al.  
**Publikasi:** *International Journal of Financial Studies* / MDPI (Scopus Q2), Vol. 13, Juni 2025  
**DOI:** `https://doi.org/10.3390/ijfs13020045`  
**Jumlah Halaman:** 25 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Peramalan harga emas yang akurat sangat penting untuk pengambilan keputusan finansial yang tepat, mengingat emas sangat sensitif terhadap faktor ekonomi, politik, dan sosial. Penelitian ini menyajikan **kerangka kerja hibrida untuk prediksi harga emas multivariat yang mengintegrasikan metode klasik dan metode kecerdasan buatan dengan fusi data finansial, ekonomi, dan sentimen**. 

Kerangka kerja yang diusulkan menggabungkan model ARIMA dengan algoritma machine learning (Random Forest dan Support Vector Regression) untuk memanfaatkan kekuatan kedua pendekatan: menangkap struktur autokorelasi linier sekaligus memetakan hubungan non-linear yang kompleks. Data yang digunakan diperkaya melalui peleburan data multimodal (*multimodal data fusion*), meliputi indikator teknikal pasar emas, indikator makroekonomi (inflasi AS, yield obligasi, indeks dolar), serta skor sentimen berita finansial global. 

Hasil evaluasi eksperimental membuktikan bahwa model hibrida fusi data ini secara konsisten mengungguli model-model univariat tunggal dalam hal RMSE dan MAE. Penggabungan data sentimen dan variabel ekonomi makro terbukti memberikan kontribusi prediktif yang signifikan, terutama selama periode turbulensi pasar yang ekstrem.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper 25 halaman terbitan MDPI (Juni 2025) ini membangun sistem prediksi harga emas berbasis **Multimodal Data Fusion** yang memadukan data finansial teknikal, data makroekonomi (inflasi, yield obligasi AS, dolar), dan sentimen berita global dengan model hibrida ARIMA + ML. Hasilnya membuktikan fusi data multi-domain menghasilkan akurasi yang jauh lebih superior daripada model internal univariat.

### B. Research Gap (Kesenjangan Penelitian)
1. **Isolasi Data Internal:** Mayoritas model prediksi emas hanya menggunakan data harga masa lalu dan mengabaikan fakta bahwa emas adalah aset makro yang bereaksi instan terhadap berita inflasi dan sentimen global.
2. **Kelemahan Model Tunggal:** Model ekonometrika klasik gagal menangkap non-linearitas sentimen berita, sedangkan model ML murni sering kali kehilangan tren dasar jangka panjang.

### C. Apa yang Dibahas
- **Objek:** Harga spot emas global.
- **Fitur Masukan:** Data teknikal harga emas, indikator inflasi AS, yield obligasi US Treasury, kurs mata uang, dan indeks sentimen teks berita finansial.
- **Model:** Hibrida ARIMA + Random Forest / SVR.

### D. Solusi dari Penelitian
- Membangun pipeline **Data Fusion Multimodal** yang menyatukan data numerik pasar dan data makro/sentimen.
- Mengombinasikan model statistik linier dengan model pohon keputusan non-linear.
- **Temuan Kunci:** Integrasi variabel makroekonomi dan sentimen berita terbukti secara empiris meningkatkan daya tahan model terhadap guncangan pasar tak terduga (*market shocks*).

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian:** Paper ini menjadi rujukan utama pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 6).
- **Relevansi untuk Skripsi:** Ini adalah landasan ilmiah langsung bagi pilar fitur **Multi-Source Feature Fusion** skripsi Nouval! Nouval merealisasikan fusi ini secara teknis ke dalam 36 variabel yang mencakup: Indeks Dolar AS (DXY Channel), Siklus Berita Makro (NFP, CPI, FOMC), geometri harga M15/M5, dan Smart Money Concepts (SMC).
