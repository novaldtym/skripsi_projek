# Master Dokumen: Sintesis Komparatif, Rangkuman, Research Gap, dan Panduan Baca 10 Artikel Baru

Dokumen ini disusun untuk memberikan peta navigasi komprehensif, telaah kritis, dan sintesis teoritis dari **10 artikel ilmiah terbaru** yang baru saja ditambahkan ke dalam direktori `d:\SKRIPSI INFORMATIKA\ARTIKEL`.

Seluruh artikel berbahasa Inggris dan Mandarin telah diterjemahkan secara lengkap ke dalam Bahasa Indonesia dan dianalisis secara mendalam pada file-file individual di folder ini.

---

## 1. Daftar Berkas Terjemahan & Panduan Baca Individual

Berikut adalah berkas terjemahan dan ulasan mendalam yang telah disediakan:

1. [01_Terjemahan_Stock_Price_Prediction_LightGBM_Technical_Indicators.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/01_Terjemahan_Stock_Price_Prediction_LightGBM_Technical_Indicators.md)
   - *Stock Price Prediction Using LightGBM Method with Technical Indicators* (Ajax Falak Santoso et al., Telkom University)
2. [02_Terjemahan_Base_Metals_Forecasting_LightGBM_ARIMA_Ensemble.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/02_Terjemahan_Base_Metals_Forecasting_LightGBM_ARIMA_Ensemble.md)
   - *Short term forecasting of base metals prices using a LightGBM and a LightGBM - ARIMA ensemble* (K. Oikonomou & D. Damigos, *Mineral Economics* Springer 2025)
3. [03_Terjemahan_Gold_Bitcoin_Price_Prediction_KNN_XGBoost_LightGBM.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/03_Terjemahan_Gold_Bitcoin_Price_Prediction_KNN_XGBoost_LightGBM.md)
   - *Gold and Bitcoin Price Prediction based on KNN, XGBoost and LightGBM Model* (Ziyang Yuan, CMLAI 2023)
4. [04_Terjemahan_NovelFinancial_Ensemble_LGBM_Commodity_Forecasting.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/04_Terjemahan_NovelFinancial_Ensemble_LGBM_Commodity_Forecasting.md)
   - *Novel Financial Applications of Machine Learning & Deep Learning: Chapters 9 & 10 Ensemble LGBM for Commodity Forecasting* (Abedin & Hajek, Springer 2023)
5. [05_Terjemahan_Hybrid_LightGBM_XGBoost_Ensemble_Boosting.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/05_Terjemahan_Hybrid_LightGBM_XGBoost_Ensemble_Boosting.md)
   - *A boosting ensemble learning based hybrid light gradient boosting machine and extreme gradient boosting model* (Racheal Sibindi et al., *Engineering Reports* Wiley 2022)
6. [06_Terjemahan_Gold_Price_Prediction_Random_Forest_MultiAsset.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/06_Terjemahan_Gold_Price_Prediction_Random_Forest_MultiAsset.md)
   - *Gold Price Prediction using Random Forest Algorithm with Multi-Market Correlations* (Utkarsh Landge et al., Pune, India)
7. [07_Terjemahan_Prediksi_Emas_LightGBM_LSTM_Analisis_Sentimen.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/07_Terjemahan_Prediksi_Emas_LightGBM_LSTM_Analisis_Sentimen.md)
   - *Research on Gold Futures Price Prediction Based on Text Sentiment Analysis and LightGBM-LSTM Model* (Sun Jingyun & Wei Chen, CNKI / JNUIST 2024)
8. [08_Terjemahan_Sistem_Prediksi_Harga_Emas_Random_Forest_Kurnia.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/08_Terjemahan_Sistem_Prediksi_Harga_Emas_Random_Forest_Kurnia.md)
   - *Gold Price Prediction System Using the Random Forest Method* (Kurnia Agung Prastyo et al., CEST 2025)
9. [09_Analisis_Prediksi_Ethereum_SVR_XGBoost_LightGBM_Untar.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/09_Analisis_Prediksi_Ethereum_SVR_XGBoost_LightGBM_Untar.md)
   - *Analisis dan Perbandingan Algoritma SVR, XGBoost, dan LightGBM dalam Prediksi Cryptocurrency Ethereum* (Ryan Anthony et al., Untar JIRSI 2024)
10. [10_Terjemahan_Hybrid_DRL_Algorithmic_Trading_Commodities_Kaur2026.md](file:///d:/SKRIPSI%20INFORMATIKA/ARTIKEL/TERJEMAHAN_DAN_ANALISIS_ARTIKEL_BARU/10_Terjemahan_Hybrid_DRL_Algorithmic_Trading_Commodities_Kaur2026.md)
    - *A Hybrid Deep Reinforcement Learning Approach for Algorithmic Trading in Commodity Futures Markets* (Baljinder Kaur et al., Wiley 2026)

---

## 2. Matriks Komparasi 10 Artikel Ilmiah

| No | Judul Singkat & Penulis | Objek / Aset | Model yang Dibandingkan | Metrik Evaluasi | Hasil Terbaik & Temuan Kunci | Research Gap Utama |
|:--:|:---|:---|:---|:---|:---|:---|
| **1** | **Stock Price Prediction using LightGBM** (Santoso et al., 2025) | Saham NVIDIA (NVDA) | LightGBM murni vs LightGBM + Fitur Teknikal vs Tuned LightGBM | RMSE, MAE, $R^2$ | **Tuned LightGBM + Indikator Teknikal** meraih RMSE 3.5196 dan $R^2$ 0.9823. Formulasi delta target mencegah akurasi semu. | Jebakan autokorelasi harga absolut ($y_t pprox y_{t-1}$) menghasilkan akurasi semu; perlunya pendekatan *delta target* pada model boosting ringan. |
| **2** | **Base Metals Forecasting** (Oikonomou & Damigos, 2025) | 6 Logam Dasar LME (Al, Cu, Pb, Ni, Sn, Zn) | AutoReg-LightGBM, ARIMA, Ensemble LightGBM-ARIMA, Global Mean, ES | RMSE, RMSSE | **AutoReg-LightGBM** terbaik pada Al & Ni; **Ensemble LightGBM-ARIMA** terbaik pada Cu & Zn. | Keterbatasan model linear murni saat terjadi *shock* volatilitas non-linear pada komoditas, dan risiko overfitting ML murni jika mengabaikan autokorelasi linear. |
| **3** | **Gold & Bitcoin Price Prediction** (Yuan, 2023) | Emas (XAU) & Bitcoin (CME) | KNN Regression, XGBoost, LightGBM | MSE, RMSE, MAE, MAPE, $R^2$ | **LightGBM unggul mutlak pada Emas (XAU)** dengan RMSE 3.323, MAE 2.014, MAPE 0.119%, dan $R^2$ 0.997, mengalahkan XGBoost dan KNN. | Masih minimnya perbandingan langsung antara model berbasis jarak (KNN) vs modern gradient boosting (XGBoost vs LightGBM) pada aset safe haven vs kripto. |
| **4** | **Ensemble LGBM for Crude Oil** (Abedin & Hajek / Sajid et al., 2023) | Minyak Mentah (Brent Crude) | LightGBM, Random Forest, Decision Tree, Lasso, SVR | RMSE, MAE, MSE, MAPE, $R^2$ | **LightGBM Ensemble** memberikan galat terendah dan eksekusi tercepat dalam menangkap gejolak harga energi. | Kerentanan model linier dan pohon tunggal terhadap guncangan geopolitik dan makroekonomi ekstrem pada pasar komoditas. |
| **5** | **Hybrid LightGBM-XGBoost** (Sibindi et al., 2022) | Data Harga Multivariat | LightGBM, XGBoost, AdaBoost, GBM, Hybrid LGBM-XGBoost | MSE, MAE, MAPE | **Hybrid LGBM-XGBoost + Bayesian Optuna** meraih MSE 0.193, MAE 0.285, MAPE 0.156, mengalahkan seluruh model tunggal. | Trade-off: LightGBM cepat (*leaf-wise*) namun rawan overfitting; XGBoost lambat (*level-wise*) namun regularisasi ketat. Perlunya hibridisasi keduanya. |
| **6** | **Gold Price Prediction using RF** (Landge et al., 2024) | Emas (GLD) | Random Forest, Linear Regression, SVM Poly, ARIMA | RMSE, $R^2$ | **Random Forest dengan Fitur Multi-Pasar** (SLV, USO, SPX, EUR/USD) meraih $R^2 > 98\%$, membuktikan peran fitur eksternal. | Keterbatasan model univariat murni (ARIMA) yang mengabaikan korelasi emas terhadap perak, minyak, bursa saham, dan nilai tukar dolar. |
| **7** | **Prediksi Emas Fusi Teks & LightGBM-LSTM** (Sun & Wei, 2024) | Kontrak Berjangka Emas | LightGBM (Feature Selection) + Analisis Sentimen Teks Berita + LSTM | RMSE, MAE, Directional Accuracy | **LightGBM Feature Selection + Sentimen + LSTM** menghasilkan galat terkecil dan akurasi arah tren terbaik. | Pengabaian sentimen berita finansial pada model kuantitatif murni, serta *curse of dimensionality* jika seluruh indikator dimasukkan mentah ke LSTM. |
| **8** | **Sistem Prediksi Emas Random Forest** (Prastyo et al., CEST 2025) | Emas Fisik Harian | Random Forest Regression (Website Streamlit) | MAE, MSE, RMSE, $R^2$ | Model Random Forest **gagal pada data uji out-of-sample ($R^2 = -1.97$, RMSE 385.49 USD)**. Penulis merekomendasikan beralih ke LightGBM / XGBoost. | Kegagalan mendasar model pohon bagging (Random Forest) dalam mengekstrapolasi harga saat emas menembus rekor harga baru (*all-time high*); butuh model gradient boosting. |
| **9** | **Prediksi Ethereum SVR vs XGBoost vs LightGBM** (Anthony et al., UNTAR 2024) | Cryptocurrency Ethereum | SVR Linear, XGBoost, LightGBM | MAE, RMSE, $R^2$, Waktu Komputasi | **LightGBM meraih performa terbaik** (MAE 75.486 pada rasio 80:20 dan 78.228 pada 70:30) serta komputasi jauh lebih cepat dari XGBoost. | Kelemahan model margin SVR pada volatilitas tinggi, serta perlunya pengujian empiris variasi split data dan dependensi time step pada varian boosting. |
| **10** | **Hybrid DRL Algorithmic Trading Commodities** (Kaur et al., Wiley 2026) | Kontrak Berjangka Emas (Gold) | Hybrid Random Forest + Soft Actor-Critic (SAC), DQN, PPO, Buy-and-Hold | Sharpe Ratio, Max Drawdown, Cumulative Profit | **Hybrid SAC + Indeks Risiko Geopolitik (GPR)** meraih Sharpe Ratio 1.45, Profit +48.6%, dan Max Drawdown ditekan hingga 7.4%. | Kurangnya studi DRL pada komoditas emas (didominasi ekuitas), kelemahan DRL murni tanpa model prediktif supervised, dan pengabaian indeks risiko geopolitik. |

---

## 3. Rangkuman Terstruktur dan Research Gap 10 Artikel

### Artikel 1: Stock Price Prediction Using LightGBM Method with Technical Indicators (Santoso et al., Telkom University)
- **Rangkuman:** Mengembangkan model peramalan pergerakan harga saham volatil (NVDA) menggunakan algoritma LightGBM yang diperkaya fitur indikator teknikal (RSI, ROC, Stochastic, MACD, Bollinger Bands) dengan pendekatan target selisih harga (*delta target*).
- **Research Gap:** Model time-series finansial konvensional sering terjebak memprediksi harga absolut secara persisten semu ($y_t pprox y_{t-1}$) yang tampak berakurasi tinggi namun tidak berguna untuk perdagangan riil. Model deep learning juga menuntut biaya komputasi besar.
- **Apa yang Dibahas:** Dataset harian 2020–2025; perbandingan LightGBM mentah vs integrasi indikator teknikal vs LightGBM dengan tuning hiperparameter.
- **Solusi Penelitian:** Mengimplementasikan LightGBM dengan target $\Delta y_t$ lalu merekonstruksi harga penutupan. Penyetelan hiperparameter menghasilkan penurunan RMSE drastis menjadi 3.5196 dan $R^2$ mencapai 0.9823.

### Artikel 2: Short term forecasting of base metals prices using a LightGBM and a LightGBM - ARIMA ensemble (Oikonomou & Damigos, Mineral Economics 2025)
- **Rangkuman:** Menguji kemampuan model machine learning modern (AutoReg-LightGBM) dan model ensemble hybrid (LightGBM-ARIMA) melawan model ekonometrika klasik (ARIMA, Exponential Smoothing, Global Mean) untuk meramal imbal hasil 6 logam dasar LME hingga 6 bulan ke depan.
- **Research Gap:** Keterbatasan model linier univariat dalam merespons kejutan volatilitas dan pergeseran rezim industri logam, serta bahaya *overfitting* model machine learning murni jika mengabaikan korelasi linier deret waktu.
- **Apa yang Dibahas:** Imbal hasil logaritmik bulanan dari tembaga, aluminium, timbal, nikel, timah, dan seng; horizon multi-langkah 1–6 bulan; metrik RMSE dan RMSSE.
- **Solusi Penelitian:** AutoReg-LightGBM unggul mutlak pada nikel dan aluminium; Ensemble LightGBM-ARIMA unggul pada tembaga dan seng; membuktikan bahwa menggabungkan komponen linier dan non-linear menghasilkan estimasi komoditas yang paling kokoh.

### Artikel 3: Gold and Bitcoin Price Prediction based on KNN, XGBoost and LightGBM Model (Ziyang Yuan, CMLAI 2023)
- **Rangkuman:** Studi komparasi empiris antara KNN, XGBoost, dan LightGBM dalam meramalkan harga aset investasi emas (XAU) dan mata uang kripto Bitcoin (CME) periode 2017–2022.
- **Research Gap:** Minimnya studi acuan yang membandingkan langsung kinerja prediktif dan efisiensi algoritma modern gradient boosting (XGBoost vs LightGBM) secara objektif pada data emas.
- **Apa yang Dibahas:** 1.302 sampel harian emas (XAU) dan 1.584 sampel Bitcoin; fitur laju perubahan harga harian, kuantitas volume, dan diferensial waktu; evaluasi MSE, RMSE, MAE, MAPE, $R^2$.
- **Solusi Penelitian:** **LightGBM membuktikan diri sebagai model terbaik untuk Emas (XAU)** dengan RMSE 3.323 USD, MAE 2.014 USD, MAPE 0.119%, dan $R^2$ 0.997, mengungguli XGBoost (RMSE 3.611) dan KNN (RMSE 14.321) dengan kecepatan pemrosesan tertinggi.

### Artikel 4: Novel Financial Applications of Machine Learning & Deep Learning (Abedin & Hajek, Springer 2023 - Bab 9 & 10)
- **Rangkuman:** Mengkaji pemodelan harga komoditas global yang sarat ketidakpastian geopolitik (Minyak Mentah Brent) menggunakan arsitektur Ensemble LightGBM dan membandingkannya dengan Random Forest, SVR, AdaBoost, Decision Tree, dan Lasso Regression.
- **Research Gap:** Model regresi univariat tradisional dan pohon keputusan tunggal gagal menangkap lonjakan tajam saat terjadi guncangan makroekonomi/geopolitik global (seperti pandemi dan krisis perang).
- **Apa yang Dibahas:** Deret waktu harga komoditas Brent; leaf-wise tree splitting; histogram binning; metrik RMSE, MAE, MSE, MAPE, Variance Score.
- **Solusi Penelitian:** Model Ensemble LightGBM mencatatkan akurasi tertinggi dan galat terendah, membuktikan efektivitas pemangkasan berbasis daun dalam menangkap lonjakan tajam komoditas tanpa *over-smoothing*.

### Artikel 5: A boosting ensemble learning based hybrid LightGBM and XGBoost model (Sibindi et al., Engineering Reports Wiley 2022)
- **Rangkuman:** Merancang arsitektur Hybrid Ensemble Boosting yang memadukan keunggulan LightGBM (*leaf-wise*, cepat, galat rendah) dan XGBoost (*level-wise*, regularisasi L1/L2 ketat) dengan optimasi hiperparameter Bayesian (Optuna).
- **Research Gap:** Adanya trade-off: LightGBM sangat efisien namun rawan *overfitting* pada varians tinggi; XGBoost sangat tahan overfitting namun komputasinya lambat. Belum ada model hybrid boosting yang mengintegrasikan keduanya secara optimal.
- **Apa yang Dibahas:** Pembobotan out-of-fold cross validation; optimasi parameter penalti L1/L2 dan `num_leaves`; perbandingan terhadap AdaBoost, GBM, XGBoost, dan LightGBM mandiri.
- **Solusi Penelitian:** Model Hybrid LGBM-XGBoost menghasilkan galat terendah di seluruh metrik (MSE 0.193, MAE 0.285, MAPE 0.156), secara efektif meminimalkan varians dan meningkatkan ketahanan model.

### Artikel 6: Gold Price Prediction using Random Forest Algorithm (Landge et al., Pune, India)
- **Rangkuman:** Memprediksi harga emas (GLD) dengan mengintegrasikan fitur korelasi multi-pasar keuangan, yaitu indeks saham S&P 500 (SPX), minyak mentah (USO), harga perak (SLV), dan kurs EUR/USD menggunakan Random Forest Regressor.
- **Research Gap:** Model statistik time-series klasik (ARIMA) hanya bergantung pada data univariat dan mengabaikan interaksi makro antar-pasar (emas sangat berkorelasi dengan perak, dolar AS, dan minyak).
- **Apa yang Dibahas:** Analisis korelasi Pearson antar-aset; evaluasi komparasi Random Forest vs Polynomial SVM vs Linear Regression vs ARIMA.
- **Solusi Penelitian:** Random Forest dengan fitur multi-aset meraih $R^2 > 98\%$, di mana perak (SLV) dan kurs EUR/USD terbukti menjadi prediktor paling signifikan terhadap harga emas.

### Artikel 7: Research on Gold Futures Price Prediction Based on Text Sentiment Analysis and LightGBM-LSTM Model (Sun & Wei, CNKI / JNUIST 2024)
- **Rangkuman:** Mengusulkan model fusi data multi-sumber untuk memprediksi harga kontrak berjangka emas dengan mengombinasikan analisis sentimen teks berita finansial, seleksi fitur menggunakan LightGBM, dan pemodelan sekuensial menggunakan LSTM.
- **Research Gap:** Model kuantitatif tradisional mengabaikan aspek kepanikan pasar dan sentimen berita, sedangkan memasukkan seluruh variabel mentah ke dalam jaringan saraf seperti LSTM menyebabkan *curse of dimensionality* dan *overfitting*.
- **Apa yang Dibahas:** Indeks Sentimen Terbobot dari judul berita; indeks pencarian Baidu; perankingan *feature importance* dengan LightGBM; peramalan temporal dengan LSTM.
- **Solusi Penelitian:** LightGBM berhasil menyaring fitur-fitur teknikal dan makroekonomi yang paling informatif, membuang *noise*, dan bersama fitur sentimen menghasilkan akurasi prediksi tertinggi pada LSTM.

### Artikel 8: Gold Price Prediction System Using the Random Forest Method (Prastyo, Sibyan, & Hasanah, CEST Oktober 2025)
- **Rangkuman:** Membangun aplikasi web prediksi harga emas harian (2020–2024) berbasis Streamlit menggunakan algoritma Random Forest. Evaluasi out-of-sample menunjukkan model gagal total dengan $R^2$ negatif (-1.97) dan RMSE 385.49 USD.
- **Research Gap:** Model ensemble berbasis *bagging* (Random Forest) tidak memiliki kemampuan mengekstrapolasi nilai di luar batas harga historis data latih (*plateau effect*), sehingga saat emas mencetak rekor harga baru (*all-time high*), galat membesar drastis.
- **Apa yang Dibahas:** Data harian emas Yahoo Finance; kegagalan Random Forest tanpa indikator teknikal/diferensiasi; visualisasi Streamlit.
- **Solusi Penelitian (Rekomendasi Penulis):** Penulis merekomendasikan secara eksplisit untuk beralih dari Random Forest ke **algoritma gradient boosting yang lebih adaptif seperti LightGBM atau XGBoost** serta menambahkan indikator teknikal dan makroekonomi.

### Artikel 9: Analisis dan Perbandingan Algoritma SVR, XGBoost, dan LightGBM dalam Prediksi Cryptocurrency Ethereum (Anthony et al., UNTAR 2024)
- **Rangkuman:** Menguji perbandingan performa SVR (kernel linear), XGBoost, dan LightGBM pada data harian aset kripto yang sangat volatil (Ethereum) selama 5 tahun dengan variasi partisi data (80:20 vs 70:30) dan variasi *time step*.
- **Research Gap:** Kelemahan model berbatas margin kaku (SVR) dalam memodelkan aset volatil, serta minimnya bukti empiris lokal mengenai komparasi efisiensi waktu eksekusi dan akurasi LightGBM vs XGBoost.
- **Apa yang Dibahas:** Variabel OHLC harian; pengujian rasio data dan *lag/time step*; metrik MAE, RMSE, $R^2$, dan waktu latih.
- **Solusi Penelitian:** **LightGBM mencatatkan performa terbaik di seluruh skenario** (MAE 75.486 pada rasio 80:20 dan 78.228 pada 70:30) dan membuktikan kecepatan komputasi yang jauh lebih efisien dibandingkan XGBoost.

### Artikel 10: A Hybrid Deep Reinforcement Learning Approach for Algorithmic Trading in Commodity Futures Markets (Kaur et al., Wiley 2026)
- **Rangkuman:** Mengembangkan kerangka kerja *algorithmic trading* pada kontrak berjangka emas dengan mengombinasikan prediksi machine learning berbasis pohon (Random Forest), algoritma Deep Reinforcement Learning (Soft Actor-Critic / SAC), dan Indeks Risiko Geopolitik (GPR).
- **Research Gap:** Mayoritas literatur DRL berfokus pada saham dan mengabaikan pasar emas berjangka; agen DRL murni lambat belajar tanpa bimbingan sinyal prediktif awal; pengabaian faktor risiko geopolitik dalam perdagangan emas.
- **Apa yang Dibahas:** Data kontrak berjangka emas; indikator volatilitas ATR; indeks berita perang/krisis geopolitik (GPR); simulasi trading riil dengan komisi dan *slippage*.
- **Solusi Penelitian:** Agen Hybrid SAC dengan regularisasi entropi dan manajemen risiko dinamis berbasis ATR mencetak Sharpe Ratio tertinggi (1.45), laba kumulatif terbesar (+48.6%), dan Max Drawdown terendah (7.4%).

---

## 4. Sintesis Strategis & Panduan Pemanfaatan untuk Skripsi XAUUSD Anda

Koleksi 10 artikel baru ini memberikan fondasi akademis yang sempurna dan saling mengunci untuk memperkuat setiap bab skripsi Anda:

```
[Bab 1: Latar Belakang & Identifikasi Masalah]
   ├── Masalah Kegagalan Model Konvensional:
   │     ├── ARIMA univariat gagal tangkap non-linearitas (Oikonomou 2025, Landge 2024)
   │     └── Random Forest gagal ekstrapolasi saat harga cetak rekor ATH (Prastyo et al. 2025, R² = -1.97)
   └── Justifikasi Solusi LightGBM:
         ├── LightGBM terbukti terbaik untuk Emas (Yuan 2023: RMSE 3.323, R² 0.997)
         └── LightGBM unggul atas XGBoost & SVR (Anthony et al. UNTAR 2024)

[Bab 2: Tinjauan Pustaka & Landasan Teori]
   ├── Teori GOSS, EFB, dan Leaf-Wise Splitting LightGBM (Ke et al., Sajid et al. Springer 2023)
   ├── Peran Fitur Indikator Teknikal (RSI, MACD, Stochastic, Bollinger Bands) (Santoso et al. Telkom 2025)
   ├── Pengaruh Berita Makro / Volatilitas Geopolitik pada Emas (Sun & Wei 2024, Kaur et al. Wiley 2026)
   └── Opsi Pengembangan Model Hybrid Ensemble (Sibindi et al. 2022)

[Bab 3: Metodologi Penelitian]
   ├── Formulasi Target Selisih Harga / Return (Delta Target) untuk hindari prediksi semu (Santoso et al. 2025)
   ├── Desain Fitur Multi-Timeframe & Indikator Volatilitas (ATR / Bollinger Bands) (Kaur et al. 2026)
   ├── Seleksi Fitur menggunakan Feature Importance LightGBM (Sun & Wei 2024)
   └── Tuning Hiperparameter Sistematis dengan Bayesian Optimization / Optuna (Sibindi et al. 2022)

[Bab 4: Hasil & Pembahasan]
   ├── Pembuktian empiris keunggulan metrik LightGBM (RMSE, MAE, MAPE, R²)
   ├── Analisis grafik aktual vs prediksi saat terjadi lonjakan berita (NFP News)
   └── Evaluasi Feature Importance untuk melihat indikator teknikal paling berpengaruh
```

Dengan tersedianya berkas-berkas terjemahan dan analisis mendalam ini, Anda kini memiliki rujukan literatur berbobot tinggi (Springer, Wiley, IEEE/CMLAI, CNKI, dan Jurnal Sinta) untuk menyusun naskah skripsi berkualitas prima.
