# Terjemahan & Analisis Mendalam: Stock Price Prediction Using LightGBM Method with Technical Indicators

**File Asli:** Stock-Price-Prediction-Using-LightGBM-Method-with-Technical-Indicators.pdf  
**Penulis:** Ajax Falak Santoso, Putu Harry Gunawan, Indwiarti  
**Institusi:** School of Computing, Telkom University, Bandung, Indonesia  
**Tahun:** 2025 / 2026  
**Jumlah Halaman:** 5 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Investasi saham menawarkan potensi keuntungan yang tinggi tetapi disertai dengan risiko signifikan akibat volatilitas pasar. Pergerakan harga yang dinamis menjadikan peramalan harga saham sebagai tantangan sekaligus peluang strategis bagi para investor. Penelitian ini bertujuan untuk memprediksi harga saham NVIDIA Corporation (NVDA) menggunakan metode *Light Gradient Boosting Machine* (LightGBM). LightGBM dipilih karena kinerjanya yang sangat tangguh pada data deret waktu (*time-series*) dan efisiensi komputasinya yang tinggi. Data historis saham diperoleh dari Yahoo Finance yang mencakup periode tahun 2020 hingga 2025. 

Untuk meningkatkan performa prediksi, beberapa indikator teknikal diintegrasikan sebagai fitur tambahan, meliputi *Relative Strength Index* (RSI), *Rate of Change* (ROC), *Stochastic Oscillator*, *Moving Average Convergence Divergence* (MACD), dan *Bollinger Bands*. Model dilatih menggunakan pendekatan target berbasis selisih (*delta-based target approach*), yang memprediksi perubahan harga harian lalu merekonstruksi kembali harga penutupan untuk dievaluasi menggunakan *Root Mean Squared Error* (RMSE), *Mean Absolute Error* (MAE), dan Koefisien Determinasi (^2$). 

Hasil eksperimen membuktikan bahwa model LightGBM yang telah dioptimasi hiperparameternya (*hyperparameter tuned*) secara efektif mampu menangkap pola pergerakan harga, mencapai RMSE uji sebesar **3.5196** dan ^2$ sebesar **0.9823**, yang merupakan skenario terbaik di antara tiga skenario pengujian. Kinerja ini mengonfirmasi bahwa LightGBM merupakan kerangka kerja yang akurat dan efisien yang sangat cocok untuk tugas peramalan harga saham di dunia nyata.

---

### I. Pendahuluan
Pasar saham merupakan komponen vital dalam sistem keuangan global yang memfasilitasi arus modal dan keputusan investasi yang mencerminkan stabilitas ekonomi serta sentimen investor. Menurut Frank K. Reilly, kemampuan menganalisis dan memperkirakan pergerakan harga saham sangat fundamental dalam mendukung manajemen portofolio yang rasional dan meminimalkan risiko investasi. Di pasar modern, perilaku harga saham dipengaruhi oleh faktor ekonomi dan perilaku yang kompleks seperti inflasi, kepercayaan investor, dan sentimen pasar. 

Model time-series tradisional seperti ARIMA dan ARIMA–GARCH, serta arsitektur deep learning termasuk LSTM dan MLP, telah banyak digunakan dalam peramalan harga saham. Meskipun model-model tersebut efektif, mereka sering kali membutuhkan dataset yang sangat besar dan sumber daya komputasi yang substansial, sehingga kurang praktis untuk sistem peramalan yang ringan (*lightweight*) atau *real-time*. Metode *ensemble learning*, khususnya *Gradient Boosting Decision Trees* (GBDT), menawarkan pendekatan alternatif yang unggul. LightGBM, yang diperkenalkan oleh Ke et al., adalah varian efisien dari GBDT yang memberikan performa luar biasa pada data tabular dan time-series dengan biaya komputasi yang jauh lebih hemat.

---

### II. Landasan Teori & Metode

#### A. Algoritma LightGBM
LightGBM adalah algoritma turunan gradient boosting berbasis pohon keputusan yang menggunakan dua teknik inovatif:
1. **GOSS (Gradient-based One-Side Sampling):** Mengeliminasi instans data dengan gradien kecil (sudah terestimasi dengan baik) dan mempertahankan instans dengan gradien besar, sehingga mengurangi ukuran sampel data pelatihan tanpa mengorbankan akurasi estimasi gradien.
2. **EFB (Exclusive Feature Bundling):** Menggabungkan fitur-fitur yang bersifat *mutually exclusive* (jarang bernilai bukan nol secara bersamaan) ke dalam satu fitur gabungan padat, sehingga mengurangi dimensi fitur secara drastis.
3. **Leaf-wise Tree Growth:** Berbeda dengan XGBoost yang menumbuhkan pohon per level (*level-wise/depth-wise*), LightGBM menumbuhkan pohon secara *leaf-wise* (memilih daun dengan penurunan loss terbesar), menghasilkan galat yang lebih rendah dan konvergensi lebih cepat.

#### B. Fitur Indikator Teknikal yang Digunakan
1. **Relative Strength Index (RSI):** Mengukur kecepatan dan perubahan pergerakan harga pada rentang 0-100 untuk mengidentifikasi kondisi jenuh beli (*overbought*) dan jenuh jual (*oversold*).
2. **Rate of Change (ROC):** Mengukur persentase perubahan harga antara harga penutupan saat ini dengan harga $ periode sebelumnya untuk mengukur momentum.
3. **Stochastic Oscillator (%K dan %D):** Membandingkan harga penutupan dengan rentang harga tinggi-rendah selama periode tertentu.
4. **Moving Average Convergence Divergence (MACD):** Menghitung selisih antara EMA 12-hari dan EMA 26-hari, dilengkapi dengan garis sinyal EMA 9-hari untuk mendeteksi pembalikan tren.
5. **Bollinger Bands:** Pita volatilitas yang dibentuk oleh SMA 20-hari ditambah/dikurang dua kali deviasi standar.

#### C. Pendekatan Formulasi Target: Delta-Based Target
Sebuah masalah krusial dalam peramalan harga finansial adalah fenomena **autokorelasi kuat** pada tingkat harga absolut ( pprox y_{t-1}$). Jika model langsung memprediksi harga absolut, model cenderung jatuh ke dalam jebakan *naive persistence* (hanya menebak harga kemarin), menghasilkan nilai ^2$ yang tampak tinggi semu padahal kemampuan prediktif sebenarnya rendah.
Untuk mengatasi jebakan ini, penelitian ini merumuskan target sebagai selisih harga harian ($\Delta y_t$):
\Delta y_t = y_t - y_{t-1}
Model dilatih untuk memprediksi perubahan $\Delta y_t$, dan harga penutupan yang diprediksi kemudian direkonstruksi melalui:
\hat{y}_t = y_{t-1} + \Delta \hat{y}_t

---

### III. Eksperimen, Skenario, dan Hasil Evaluasi

Penelitian membandingkan 3 skenario:
- **Skenario 1 (Baseline):** LightGBM default hanya menggunakan data harga historis (Open, High, Low, Close, Volume).
- **Skenario 2:** LightGBM dengan integrasi indikator teknikal (RSI, ROC, Stochastic, MACD, Bollinger Bands).
- **Skenario 3 (Tuned LightGBM):** LightGBM dengan indikator teknikal ditambah optimasi hiperparameter (pencarian nilai *learning rate*, *num_leaves*, *max_depth*, *min_child_samples*, dan *n_estimators*).

#### Hasil Kuantitatif:
| Skenario | RMSE | MAE | ^2$ |
| :--- | :---: | :---: | :---: |
| Skenario 1 (Data Mentah) | 6.8421 | 5.1204 | 0.9312 |
| Skenario 2 (+ Indikator Teknikal) | 4.3182 | 3.2845 | 0.9687 |
| **Skenario 3 (Tuned LightGBM + Indikator)** | **3.5196** | **2.6410** | **0.9823** |

Penambahan indikator teknikal berhasil menurunkan RMSE dari 6.8421 menjadi 4.3182 (penurunan galat sebesar 36.8%). Optimasi hiperparameter menyempurnakannya lebih lanjut menjadi **3.5196** dengan ^2$ mencapai **0.9823**.

---

### IV. Kesimpulan Penulis
Model LightGBM dengan rekayasa fitur indikator teknikal dan pendekatan *delta-based target* terbukti sangat efektif, stabil, dan cepat dalam memprediksi harga saham yang memiliki volatilitas tinggi. Fitur teknikal memberikan representasi momentum dan volatilitas yang tidak dapat ditangkap oleh data harga mentah semata.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian ini memvalidasi keunggulan algoritma LightGBM dalam meramal harga saham berfluktuasi tinggi (NVDA 2020-2025) dengan memanfaatkan fitur indikator teknikal momentum dan volatilitas (RSI, ROC, Stochastic, MACD, Bollinger Bands). Model menggunakan pendekatan cerdas *delta-based target* untuk menghindari jebakan *naive persistence* akibat autokorelasi harga, dan membuktikan bahwa tuning hiperparameter LightGBM menghasilkan akurasi tinggi (RMSE 3.5196, ^2$ 0.9823) dengan efisiensi komputasi yang jauh lebih unggul daripada arsitektur deep learning.

### B. Research Gap (Kesenjangan Penelitian)
1. **Jebakan Autokorelasi Harga Absolut:** Sebagian besar literatur peramalan time-series finansial langsung memprediksi nilai harga absolut ($), yang sering kali menghasilkan ilusi akurasi semu karena model hanya mempelajari fungsi identitas ( pprox y_{t-1}$). Belum banyak studi peramalan berbasis boosting yang mengimplementasikan formulasi target selisih (*delta-based*) yang kemudian direkonstruksi kembali ke harga asli.
2. **Keterbatasan Komputasi Model Deep Learning:** Model seperti LSTM dan Transformer memerlukan beban pelatihan dan komputasi yang sangat masif, sementara model statistik linear (ARIMA) gagal menangkap interaksi non-linear indikator teknikal. Ada kesenjangan kebutuhan akan model ensemble pohon yang ringan, cepat, namun setara atau melebihi akurasi deep learning.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Bagaimana merancang sistem peramalan harga instrumen volatil yang akurat, tidak terjebak prediksi persisten semu, dan hemat komputasi.
- **Dataset:** Harga harian saham NVIDIA (NVDA) dari Yahoo Finance periode 2020-2025.
- **Variabel Input:** Open, High, Low, Close, Volume, serta indikator teknikal turunan (RSI, ROC, Stochastic Oscillator %K & %D, MACD & Signal Line, Bollinger Bands Upper/Lower/Bandwidth).
- **Target:** Perubahan harga harian ($\Delta Close_t$).

### D. Solusi dari Penelitian
- Menerapkan arsitektur **LightGBM** berbasis penumbuhan *leaf-wise* yang dipadukan dengan teknik GOSS dan EFB.
- Memformulasikan target prediksi sebagai **Delta Target ($\Delta y_t$)**, kemudian merekonstruksi harga prediksi ($\hat{y}_t = y_{t-1} + \Delta \hat{y}_t$).
- Melakukan optimasi hiperparameter untuk menghindari *overfitting* pada *leaf-wise tree*.
- **Hasil:** Penurunan RMSE hingga 3.5196 dan peningkatan ^2$ menjadi 0.9823, membuktikan solusi integrasi indikator teknikal pada LightGBM sangat efektif.

### E. Relevansi & Rekomendasi untuk Skripsi XAUUSD Anda
1. **Adopsi Delta-Target / Return Target:** Terapkan pendekatan peramalan selisih harga ($\Delta Close$) atau log-return untuk peramalan harga emas XAUUSD. Ini akan mencegah model LightGBM Anda hanya meniru harga candle sebelumnya.
2. **Kombinasi Fitur Teknikal:** Jadikan kombinasi indikator momentum (RSI, Stochastic), tren (MACD, MA), dan volatilitas (Bollinger Bands, ATR) sebagai fitur wajib dalam pipeline rekayasa fitur skripsi Anda.
3. **Rujukan Validitas LightGBM:** Gunakan paper ini di Bab 2 skripsi Anda sebagai bukti akademis bahwa LightGBM telah terbukti unggul untuk memodelkan harga instrumen yang memiliki volatilitas tinggi.
