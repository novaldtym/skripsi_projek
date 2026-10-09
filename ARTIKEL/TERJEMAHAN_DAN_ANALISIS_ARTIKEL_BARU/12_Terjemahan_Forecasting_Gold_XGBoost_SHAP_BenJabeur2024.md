# Terjemahan & Analisis: Forecasting Gold Price with the XGBoost Algorithm and SHAP Interaction Value

**File Asli:** `Forecasting gold price with the XGBoost algorithm and SHAP interaction value..pdf`  
**Penulis:** Sami Ben Jabeur, Rania Mseddi, Zied Ftiti  
**Publikasi:** *Annals of Operations Research* (Springer, Scopus Q1), Vol. 334, Hal. 679–705 (2024)  
**DOI:** `https://doi.org/10.1007/s10479-021-04187-w`  
**Jumlah Halaman:** 21 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Lembaga keuangan, investor, dan industri pertambangan membutuhkan model peramalan yang efektif dan akurat untuk memeriksa fluktuasi harga emas guna mengambil keputusan yang tepat. Makalah ini mengusulkan pendekatan inovatif untuk meramalkan harga emas secara akurat menggunakan algoritma *Extreme Gradient Boosting* (XGBoost) yang dikombinasikan dengan teknik interpretasi *SHapley Additive exPlanations* (SHAP) dan nilai interaksi SHAP (*SHAP interaction values*). 

Model dievaluasi menggunakan data historis yang mencakup indeks risiko geopolitik (GPR), volatilitas pasar modal (VIX), harga minyak mentah, serta indikator pasar valuta asing. Analisis interaksi SHAP memungkinkan peneliti membuka "kotak hitam" (*black box*) algoritma boosting dan menyingkap bagaimana variabel makroekonomi dan geopolitik berinteraksi secara non-linear dalam memengaruhi pergerakan harga emas. 

Hasil empiris membuktikan bahwa XGBoost secara signifikan mengungguli model regresi linier, Random Forest, dan Support Vector Regression (SVR). Selain itu, analisis nilai interaksi SHAP membuktikan bahwa interaksi antara guncangan geopolitik dan penguatan dolar AS merupakan faktor pemicu non-linear paling dominan terhadap lonjakan volatilitas harga emas.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Artikel Q1 Springer Annals of Operations Research (2024) ini mendemonstrasikan keunggulan algoritma gradient boosting (XGBoost) dalam memprediksi harga emas global dengan mengintegrasikan indeks risiko geopolitik (GPR), indeks volatilitas (VIX), dan harga komoditas lain. Keunggulan metodologinya terletak pada penerapan **SHAP Interaction Values** untuk menguraikan interaksi non-linear antar-fitur.

### B. Research Gap (Kesenjangan Penelitian)
1. **Sifat Black-Box Algoritma Boosting:** Meskipun algoritma gradient tree boosting sangat akurat, model ini sering dikritik karena tidak dapat dijelaskan secara transparan (*unexplainable*).
2. **Pengabaian Efek Interaksi Non-Linear Antarvariabel:** Sebagian besar studi terdahulu hanya melihat pengaruh masing-masing variabel secara terisolasi tanpa memodelkan bagaimana variabel makro (misal Dolar vs Minyak vs Geopolitik) berinteraksi secara dinamis.

### C. Apa yang Dibahas
- **Objek:** Harga emas spot dunia harian.
- **Variabel Masukan:** Indeks Geopolitik (GPR), Indeks VIX, Dolar AS, Minyak Mentah, dan indikator teknikal.
- **Metodologi:** XGBoost Regressor dengan optimasi hiperparameter + SHAP values dan SHAP interaction matrix.

### D. Solusi dari Penelitian
- Menerapkan pohon boosting XGBoost untuk menangkap non-linearitas ekstrem pada harga emas.
- Menjelaskan kontribusi setiap fitur dan interaksi silang antar-fitur menggunakan teori kooperatif permainan Shapley (SHAP).
- **Temuan Kunci:** XGBoost mengungguli seluruh model pembanding, dan interaksi antara Dolar AS dan ketidakpastian pasar global menjadi determinan terkuat harga emas.

### E. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian Langsung:** Paper ini menjadi rujukan utama pada Tabel 1.1 Bab 1 skripsi Nouval (Baris 2).
- **Perbandingan dengan Skripsi Nouval:** 
  1. Ben Jabeur et al. menggunakan XGBoost untuk regresi harga nominal, sedangkan Nouval menggunakan **LightGBM Classifier** untuk memprediksi probabilitas arah (Naik/Turun) yang terbebas dari jebakan autokorelasi harga.
  2. Ben Jabeur et al. menggunakan SHAP harian, sementara Nouval mengimplementasikan *Feature Importance* pada 36 variabel multi-timeframe (M15, M5, H4) dan siklus berita NFP.
