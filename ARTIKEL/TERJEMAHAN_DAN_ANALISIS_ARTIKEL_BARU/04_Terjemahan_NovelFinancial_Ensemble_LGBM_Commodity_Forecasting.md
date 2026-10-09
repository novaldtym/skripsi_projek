# Terjemahan & Analisis Mendalam: Novel Financial Applications of Machine Learning and Deep Learning (Fokus: Bab 9 & 10 Ensemble LightGBM untuk Komoditas)

**File Asli:** `NovelFinancial.pdf`  
**Buku / Prosiding:** *Novel Financial Applications of Machine Learning and Deep Learning Algorithms, Product Modeling, and Sentiment Analysis*  
**Editor Buku:** Mohammad Zoynul Abedin, Petr Hajek  
**Penerbit:** Springer Nature (*International Series in Operations Research & Management Science*, Vol. 336, 2023)  
**Bab Kunci Terpilih:**
- **Bab 9:** *An Ensemble LGBM (Light Gradient Boosting Machine) Approach for Crude Oil Price Prediction* (Sad Wadi Sajid, Mahmudul Hasan, Md. Fazle Rabbi, Mohammad Zoynul Abedin, Hal. 160–172)
- **Bab 10:** *Model Development for Predicting the Crude Oil Price: Comparative Evaluation of Ensemble and Machine Learning Methods* (Mahmudul Hasan, Ushna Das, Rony Kumar Datta, Mohammad Zoynul Abedin, Hal. 173–185)  
**Jumlah Halaman Total Buku:** 235 Halaman  

---

## 1. Terjemahan Lengkap Bab Terpilih (Bab 9 & 10: Pemodelan Komoditas dengan LightGBM & Ensemble)

### Abstrak Bab 9 (An Ensemble LGBM Approach for Crude Oil Price Prediction)
Minyak mentah merupakan salah satu sumber daya paling penting di dunia saat ini, yang memiliki dampak sistemik sangat besar terhadap stabilitas ekonomi global. Pasar minyak mentah sangat likuid namun dipenuhi ketidakpastian (*uncertainty*) dan lonjakan volatilitas. Peramalan harga pasar komoditas minyak mentah telah menjadi kebutuhan mendesak bagi pemerintah, industri energi, maupun investor individual. Memprediksi harga minyak secara akurat dapat mendukung pengambilan keputusan ekonomi yang berkelanjutan.

Tujuan dari studi ini adalah meramalkan harga pasar minyak mentah seakurat mungkin menggunakan metodologi *machine learning* dan *ensemble learning*. Dalam penelitian ini, kami mengusulkan model peramalan berbasis *Light Gradient Boosting Machine* (LGBM), yang dibandingkan dengan algoritma *Random Forest*, *Lasso Regression*, dan *Decision Tree*. Data deret waktu minyak mentah jenis Brent digunakan untuk analisis pemodelan. Kurva perbandingan dan evaluasi metrik kesalahan membuktikan bahwa LGBM memberikan hasil prediksi yang paling akurat, stabil, dan efisien. Hasil ini divalidasi melalui metrik *Root Mean Squared Error* (RMSE), *Mean Absolute Percentage Error* (MAPE), *Mean Squared Error* (MSE), dan *Mean Absolute Error* (MAE), di mana model LGBM secara konsisten mengungguli model-model lainnya.

---

### I. Pendahuluan & Karakteristik Komoditas Energi
Pasar komoditas energi (seperti minyak mentah) dan logam mulia memiliki kemiripan mendasar: keduanya merupakan aset lindung nilai (*hedging*) global yang sangat sensitif terhadap peristiwa geopolitik, perang, keputusan OPEC/kebijakan moneter, dan inflasi. Fluktuasi harga yang tajam dan perilaku deret waktu non-linear menyulitkan model statistik linear klasik untuk menghasilkan estimasi yang presisi.

Machine learning hadir sebagai paradigma baru dalam ekonometrika keuangan kuantitatif. Model-model ensemble, khususnya algoritma *gradient boosting*, terbukti sangat ampuh dalam mengekstrak sinyal-sinyal prediktif dari data time-series yang ber-noise tinggi.

---

### II. Metodologi & Algoritma Ensemble LightGBM

#### A. Arsitektur LightGBM pada Deret Waktu Komoditas
LightGBM mengatasi kelemahan mendasar dari model pohon keputusan tradisional dan algoritma GBDT konvensional. Fitur kunci yang ditekankan dalam buku ini:
1. **Pemisahan Daun Berorientasi Kedalaman Maksimal Loss (Leaf-wise Tree Split):** Berbeda dengan *level-wise* yang membagi semua cabang secara simetris, LightGBM memotong daun yang memaksimalkan penurunan varians galat. Hal ini memungkinkan model menangkap dinamika lonjakan harga ekstrem (*sharp price spikes*) yang khas pada komoditas.
2. **Histogram-based Binning:** Mengelompokkan nilai-nilai kontinu ke dalam bin diskret (misal 256 bin), yang menurunkan kebutuhan memori hingga 80% dan mempercepat proses pencarian titik pisah secara drastis.
3. **Penanganan Outlier & Fitur Multivariat:** LightGBM secara inheren tahan terhadap titik data pencilan (*outliers*) akibat rilis berita fundamental mendadak.

#### B. Model Pembanding (Bab 9 & 10)
- **Lasso Regression:** Model linear dengan regularisasi L1 untuk seleksi fitur dan mitigasi multikolinearitas.
- **Decision Tree Regression (CART):** Model pohon regresi tunggal non-parametrik.
- **Random Forest Regression:** Model ensemble berbasis *bagging* (penggabungan pohon acak paralel).
- **AdaBoost Regression (Bab 10):** Algoritma boosting adaptif yang memusatkan bobot pada sampel-sampel dengan galat terbesar.
- **Support Vector Regression (SVR):** Model berbasis *kernel trick* untuk memetakan regresi ke ruang dimensi tinggi.

---

### III. Hasil Eksperimen Kuantitatif & Temuan

- **Dataset:** Deret waktu harian harga minyak mentah Brent (*Brent Crude Oil*) historis yang mencakup periode pra dan pasca guncangan ekonomi global (termasuk era COVID-19).
- **Temuan Kunci Bab 9:**
  - Model **LightGBM (LGBM)** meraih galat terendah di seluruh metrik: RMSE terendah, MAE terendah, dan MAPE terendah dibandingkan Random Forest, Lasso, dan Decision Tree.
  - Decision Tree tunggal mengalami *overfitting* parah dengan varians prediksi yang tidak stabil.
  - Lasso Regression memiliki bias linier yang tinggi sehingga gagal memprediksi pembalikan arah harga (*trend reversal*).
  - Random Forest menghasilkan prediksi yang cukup baik namun kurva prediksinya cenderung mengalami efek "penghalusan berlebih" (*over-smoothing*) pada puncak-puncak harga ekstrem.
- **Temuan Kunci Bab 10:**
  - Algoritma ensemble berbasis *boosting* (AdaBoost & Gradient Boosting) secara signifikan mengungguli SVR dan Bagging Lasso dalam metrik $R^2$ score dan responsivitas terhadap volatilitas dinamis.

---

### IV. Kesimpulan Buku
Kompilasi penelitian dalam buku Springer ini menegaskan bahwa untuk komoditas pasar global yang sarat gejolak ekonomi, algoritma ensemble modern—khususnya keluarga *Gradient Boosting* seperti LightGBM—menyediakan arsitektur terbaik yang menggabungkan akurasi peramalan tingkat tinggi, kemampuan menangkap fluktuasi non-linear, dan efisiensi waktu komputasi.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Buku monograf akademik Springer (2023) yang diedit oleh Abedin & Hajek ini menyajikan aplikasi machine learning mutakhir pada risiko finansial dan peramalan deret waktu. Secara khusus, Bab 9 dan Bab 10 mendemonstrasikan keunggulan algoritma **LightGBM dan Ensemble Boosting** dalam meramalkan harga komoditas global yang sangat volatil (Brent Crude Oil). Eksperimen empiris menunjukkan LightGBM menghasilkan galat (RMSE, MAE, MAPE) paling minim dibandingkan Random Forest, SVR, Decision Tree, dan Lasso Regression.

### B. Research Gap (Kesenjangan Penelitian)
1. **Ketidakmampuan Model Tradisional Menghadapi Guncangan Ekstrem:** Model ekonometrika linear dan pohon keputusan tunggal gagal memodelkan deret waktu komoditas saat terjadi guncangan makroekonomi/geopolitik besar (seperti perang atau pandemi), karena hubungan antarvariabel bersifat sangat dinamis dan non-linear.
2. **Kebutuhan Evaluasi Multi-Model Komprehensif pada Komoditas:** Masih dibutuhkannya studi komparatif terstruktur yang membandingkan berbagai kelas model (linear regularized, single tree, bagging ensemble, dan modern gradient boosting) pada dataset komoditas riil.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Mengidentifikasi model ensemble machine learning paling efektif untuk memprediksi harga komoditas strategis yang sarat volatilitas tinggi.
- **Dataset:** Data deret waktu harga harian komoditas Brent Crude Oil.
- **Variabel:** Harga Open, High, Low, Close, serta lag waktu historis.
- **Metrik:** MSE, RMSE, MAE, MAPE, Variance Score, dan $R^2$.

### D. Solusi dari Penelitian
- Mengimplementasikan **LightGBM Regressor** dengan optimasi struktur pohon *leaf-wise*.
- Membandingkan performa terhadap 5 algoritma pembanding (Lasso, Decision Tree, Random Forest, AdaBoost, SVR).
- **Solusi Utama:** Menunjukkan bahwa strategi penumbuhan daun berorientasi penurunan galat pada LightGBM secara khusus sangat adaptif untuk menangkap fluktuasi tajam komoditas tanpa membutuhkan waktu pelatihan yang lama.

### E. Relevansi & Nilai Tambah untuk Skripsi XAUUSD Anda
1. **Referensi Buku Teks Bergengsi (Springer):** Mengutip buku Springer Series ini di Bab 2 skripsi Anda memberikan bobot akademis yang sangat kuat dan kredibel untuk menjustifikasi penggunaan LightGBM pada komoditas.
2. **Kemiripan Perilaku Emas & Minyak:** Emas (XAUUSD) dan minyak mentah adalah dua komoditas global utama yang memiliki dinamika volatilitas serupa terhadap berita makroekonomi (misalnya rilis data inflasi NFP, suku bunga The Fed, dan krisis geopolitik). Bukti bahwa LightGBM unggul pada minyak mentah memperkuat hipotesis Anda bahwa LightGBM adalah model terbaik untuk emas.
