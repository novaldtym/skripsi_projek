# Terjemahan & Analisis Mendalam: Research on Gold Futures Price Prediction Based on Text Sentiment Analysis and LightGBM-LSTM Model

**File Asli:** `7a17d6db896926b050cd3a83f82fbfc7.pdf`  
**Judul Asli (Mandarin):** 基于文本情感分析和LightGBM-LSTM模型的黄金期货价格预测研究  
**Penulis:** 孙景云 (Sun Jingyun), 魏琛 (Wei Chen)  
**Institusi:** School of Statistics and Data Science, Lanzhou University of Finance and Economics, Lanzhou, China  
**Publikasi:** *Journal of Nanjing University of Information Science and Technology* (CNKI: 20241102001, 2024 / 2025)  
**Didanai oleh:** National Natural Science Foundation of China (No. 72061020)  
**Jumlah Halaman:** 1 Halaman (Format Pra-publikasi / Naskah Jurnal Ilmiah CNKI)  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Di pasar finansial, harga kontrak berjangka emas (*gold futures*) dipengaruhi oleh berbagai faktor yang sangat kompleks. Meramalkan harga emas secara akurat memiliki signifikansi yang sangat besar bagi stabilitas ekonomi dan keamanan aset keuangan nasional. 

Penelitian ini memadukan data multi-sumber (*multi-source data fusion*) dan mengusulkan sebuah model peramalan harga emas berjangka baru yang mengintegrasikan metode seleksi fitur **LightGBM** (*Light Gradient Boosting Machine*) dengan arsitektur jaringan saraf **LSTM** (*Long Short-Term Memory*). 

Pertama-tama, data indikator makroekonomi dan indikator teknikal yang diperoleh dilakukan tahap pra-pemrosesan (*preprocessing*). Untuk data tidak terstruktur berupa judul-judul berita finansial (*unstructured financial news headlines*), kami menerapkan metode analisis sentimen teks untuk memberi label tendensi sentimen, yang kemudian dikonstruksi menjadi **Indeks Sentimen Terbobot** (*Weighted Sentiment Index*). Selain itu, volume pencarian kata kunci digabungkan menjadi Indeks Pencarian Komprehensif Baidu. 

Kedua, metode **LightGBM digunakan untuk melakukan perankingan kepentingan fitur (*feature importance ranking*)** secara terpisah terhadap indikator makroekonomi dan indikator teknikal guna menyaring dan mengekstrak fitur-fitur yang paling kritis serta mengeliminasi variabel yang redundan dan ber-noise tinggi. 

Terakhir, fitur-fitur terpilih dari LightGBM tersebut bersama dengan Indeks Sentimen Terbobot dan Indeks Pencarian dimasukkan sebagai variabel input ke dalam model prediksi LSTM. 

Hasil empiris membuktikan bahwa model **LightGBM-LSTM yang memadukan multi-sumber data ini menunjukkan performa yang sangat unggul**, mencatat nilai galat prediksi terendah, dan mampu menghasilkan peramalan harga penutupan emas berjangka yang jauh lebih presisi dibandingkan model-model pembanding (*benchmark*).

**Kata Kunci:** Emas Berjangka; Fusi Multi-Sumber Data; Judul Berita; Seleksi Fitur; LightGBM; Long Short-Term Memory (LSTM)

---

### I. Pendahuluan & Latar Belakang Masalah
Seiring dengan meningkatnya ketidakpastian ekonomi global, emas berjangka sebagai instrumen derivatif finansial utama memegang peranan krusial dalam sistem ekonomi dunia. Karakteristik deret waktu harga emas berjangka memiliki sifat non-linear, non-stasioner, dan dipenuhi tingkat *noise* yang tinggi.

Model ekonometrika tradisional seperti ARIMA, GARCH, dan VAR tidak mampu menangkap perubahan harga yang disebabkan oleh sentimen kepanikan pasar atau berita mendadak. Di sisi lain, model machine learning tunggal seperti SVR, MLP, dan BP-NN sering kali mengalami keterbatasan dalam menangani dependensi temporal jangka panjang.

Meskipun LSTM telah banyak digunakan untuk menangani dependensi deret waktu, memasukkan terlalu banyak variabel mentah (indikator teknikal + indikator makro + data teks) ke dalam LSTM secara langsung akan menyebabkan fenomena *curse of dimensionality* (kutukan dimensi) dan *overfitting*, sehingga menurunkan kemampuan generalisasi model. Oleh karena itu, diperlukan mekanisme **seleksi fitur cerdas** sebelum data dimasukkan ke dalam model sekuensial.

---

### II. Arsitektur Model: Fusi Multi-Sumber LightGBM-LSTM

Arsitektur model yang diusulkan terdiri dari 3 tahapan utama:

```
[Data Berita Finansial] -> [Analisis Sentimen Teks] -> [Indeks Sentimen Terbobot]
                                                                  |
[Indikator Makroekonomi] \                                         |
                          -> [Seleksi Fitur via LightGBM] --------> [Model LSTM] -> [Prediksi Harga Emas]
[Indikator Teknikal]     /    (Menyaring Fitur Terbaik)           |
                                                                  |
[Data Tren Pencarian Internet] -----------------------------------+
```

#### A. Rekayasa Fitur & Analisis Sentimen Teks
1. **Data Berita:** Judul berita finansial diekstraksi dan dianalisis menggunakan kamus sentimen domain keuangan untuk menghasilkan skor sentimen positif, netral, atau negatif.
2. **Indeks Pencarian:** Mengukur atensi publik (*investor attention*) terhadap volatilitas emas.
3. **Indikator Teknikal:** MA, RSI, MACD, KDJ, Bollinger Bands.
4. **Indikator Makroekonomi:** Indeks Dolar AS, suku bunga, tingkat inflasi global.

#### B. Seleksi Fitur Berbasis LightGBM
Alih-alih melatih model dengan ratusan variabel, LightGBM digunakan sebagai *feature selector*:
- LightGBM menghitung skor kepentingan fitur (*feature importance gain* dan *split frequency*) secara efisien.
- Fitur dengan skor kontribusi rendah atau berkorelasi ganda dibuang.
- Hanya subset fitur yang paling relevan secara statistik yang diloloskan ke tahap prediksi.

#### C. Prediksi Sekuensial LSTM
Subset fitur optimal bersama dengan sinyal sentimen dimasukkan ke dalam sel memori LSTM untuk mempelajari korelasi temporal dan memprediksi harga penutupan emas.

---

### III. Temuan Kunci & Keunggulan Model

1. **LightGBM sebagai Filter Noise yang Sangat Efektif:** Menggunakan LightGBM untuk memfilter fitur teknikal dan makroekonomi terbukti memangkas dimensi data tanpa kehilangan informasi penting, mencegah LSTM dari *overfitting*.
2. **Sentimen Berita Meningkatkan Akurasi Secara Nyata:** Menyertakan indeks sentimen berita finansial terbukti secara signifikan menurunkan galat prediksi saat terjadi gejolak pasar ekstrem (*black swan events*).
3. **Sinergi Model:** Kombinasi LightGBM (kecepatan seleksi fitur non-linear) dan LSTM (daya ingat dependensi deret waktu) mencetak RMSE dan MAE paling minim di antara semua model yang diuji.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper dari Tiongkok (National Natural Science Foundation) ini mengusulkan kerangka kerja fusi data multi-sumber untuk memprediksi harga kontrak berjangka emas dengan menggabungkan analisis sentimen teks berita, **LightGBM untuk seleksi fitur terbaik**, dan LSTM untuk peramalan sekuensial deret waktu. Eksperimen membuktikan bahwa model terintegrasi ini menghasilkan galat terkecil dan akurasi arah tren terbaik dibandingkan model acuan lainnya.

### B. Research Gap (Kesenjangan Penelitian)
1. **Pengabaian Sentimen Berita pada Model Kuantitatif:** Sebagian besar penelitian peramalan emas hanya mengandalkan data numerik harga historis, mengabaikan fakta empiris bahwa emas digerakkan secara masif oleh kepanikan dan sentimen investor dari berita global.
2. **Kutukan Dimensi pada Input Jaringan Saraf (LSTM):** Ketika peneliti mencoba memasukkan banyak indikator teknikal dan makroekonomi ke dalam model sekuensial seperti LSTM, model sering kali gagal belajar secara stabil karena terlalu banyak variabel redundan (*noise*). Belum banyak studi yang memanfaatkan LightGBM sebagai algoritma seleksi fitur non-linear sebelum masuk ke jaringan saraf peramalan emas.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Bagaimana merancang sistem peramalan harga emas berjangka yang mengintegrasikan data terstruktur (makroekonomi & teknikal) dan data tidak terstruktur (sentimen teks berita) secara efektif tanpa *overfitting*.
- **Dataset:** Harga emas berjangka, indikator makroekonomi, indikator teknikal, judul berita finansial, dan indeks pencarian internet.
- **Variabel:** Fitur makro, indikator teknikal momentum/volatilitas, skor sentimen berita.

### D. Solusi dari Penelitian
- Mengonstruksi **Indeks Sentimen Terbobot** dari teks berita finansial.
- Menggunakan **LightGBM Feature Importance Ranking** untuk menyeleksi variabel makro dan teknikal yang paling berdampak secara non-linear.
- Memasukkan variabel terpilih ke **LSTM** untuk peramalan harga penutupan.
- **Hasil:** Penurunan galat prediksi secara drastis dibandingkan model tanpa seleksi fitur atau tanpa sentimen.

### E. Relevansi & Rekomendasi untuk Skripsi XAUUSD Anda
1. **Gunakan LightGBM untuk Feature Importance / Feature Selection:** Pada bab hasil dan analisis skripsi Anda, Anda dapat memanfaatkan fungsi bawaan `lightgbm.plot_importance` untuk menunjukkan indikator teknikal mana yang paling berpengaruh terhadap pergerakan XAUUSD (misalnya RSI vs MACD vs ATR).
2. **Kesesuaian dengan Karakteristik Berita Finansial (NFP / CPI):** Skripsi Anda memiliki fokus pada peristiwa rilis berita ekonomi seperti NFP (Non-Farm Payroll). Paper ini menjadi rujukan akademis yang sangat kuat bahwa sentimen dan informasi berita makroekonomi memang terbukti secara ilmiah mampu meningkatkan daya ramal harga emas secara signifikan!
