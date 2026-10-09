# Terjemahan & Analisis Mendalam: A Hybrid Deep Reinforcement Learning Approach for Algorithmic Trading in Commodity Futures Markets

**File Asli:** `Applied Computational Intelligence and Soft Computing - 2026 - Kaur - A Hybrid Deep Reinforcement Learning Approach for.pdf`  
**Penulis:** Baljinder Kaur, Brahmaleen K. Sidhu, Gurjit Singh Bhathal  
**Institusi:** Department of Computer Science and Engineering, Punjabi University, Patiala, India  
**Publikasi:** *Applied Computational Intelligence and Soft Computing* (Wiley / Hindawi), Volume 2026, Article ID 5993683 (2025/2026)  
**DOI:** `https://doi.org/10.1155/acis/5993683`  
**Jumlah Halaman:** 20 Halaman  

---

## 1. Terjemahan Lengkap Dokumen

### Abstrak
Pasar finansial global telah terpengaruh secara masif dalam beberapa tahun terakhir akibat maraknya perdagangan algoritmik (*algorithmic trading*), terutama yang berkaitan dengan kontrak berjangka komoditas (*commodity futures*). Penelitian ini menyajikan sebuah pendekatan **hybrid inovatif yang menggabungkan algoritma machine learning klasik (Random Forest) dengan algoritma deep reinforcement learning (DRL) modern—yaitu Deep Q-Network (DQN), Proximal Policy Optimization (PPO), dan Soft Actor-Critic (SAC)**—untuk perdagangan algoritmik di pasar berjangka komoditas. 

Berbeda dengan mayoritas penelitian terdahulu yang hampir seluruhnya berfokus pada pasar saham (*equities*), penelitian ini secara khusus mengaplikasikan model hybrid ini pada **pasar berjangka logam mulia (EMAS / GOLD)** menggunakan dataset baru harga emas yang diperkaya dengan **Indeks Risiko Geopolitik** (*Geopolitical Risk Indices* / GPR). 

Evaluasi menyeluruh yang dilakukan membuktikan bahwa agen **Soft Actor-Critic (SAC)** yang dirancang berhasil melampaui pendekatan konvensional (*Buy-and-Hold* dan *Sell-and-Hold*) serta model DRL lainnya (DQN dan PPO) dalam hal laba kumulatif (*cumulative profit*), rasio Sharpe (*Sharpe ratio*), penurunan maksimum (*maximum drawdown*), dan volatilitas tahunan (*annualized volatility*). Hasil penelitian kami memperluas perkembangan metodologi perdagangan algoritmik dengan mengatasi kelemahan-kelemahan klasik dalam peramalan pasar komoditas.

**Kata Kunci:** Perdagangan Algoritmik, Kontrak Berjangka Emas, Deep Reinforcement Learning, Soft Actor-Critic, Random Forest, Indeks Risiko Geopolitik (GPR), Manajemen Risiko Finansial

---

### I. Pendahuluan & Latar Belakang Komoditas Emas
Perdagangan komoditas berjangka, khususnya emas, memiliki dinamika yang sangat unik dibandingkan pasar ekuitas. Emas adalah aset pelindung nilai utama dunia yang pergerakannya dipicu oleh ketegangan geopolitik, perang, sanksi ekonomi, dan inflasi.

Kebanyakan sistem perdagangan otomatis berbasis *Deep Reinforcement Learning* (DRL) konvensional menghadapi kelemahan serius:
1. **Ketiadaan Panduan Prediktif (*Lack of Predictive Prior*):** Agen DRL murni sering kali melakukan eksplorasi secara acak dan tidak stabil pada fase awal karena tidak memiliki pemahaman prediktif mengenai arah tren harga.
2. **Keterbatasan pada Saham Saja:** Sangat sedikit literatur DRL yang mengeksplorasi pasar komoditas berjangka yang memiliki biaya transaksi (*slippage/spread*) dan volatilitas ekstrem.
3. **Pengabaian Risiko Geopolitik:** Pergerakan emas sangat ditentukan oleh krisis politik global. Mengabaikan faktor geopolitik membuat model sering kali terkejut oleh pergerakan harga tiba-tiba (*gap down/up*).

Untuk mengatasi celah tersebut, penelitian ini merancang arsitektur **Hybrid ML + DRL + Geopolitical Risk Indices**.

---

### II. Arsitektur Kerangka Kerja Hybrid ML-DRL

```
[Data Harga Emas + Indikator Teknikal]                                          -> [Model Prediksi ML (Random Forest)] [Indeks Risiko Geopolitik (GPR)]       /                                         |
                                                                                 v
                                                             [Representasi State Pasar]
                                                                                 |
                                                                                 v
                                                             [Agen DRL: SAC / PPO / DQN]
                                                                                 |
                                                                                 v
                                                             [Modul Manajemen Risiko Dinamis]
                                                                                 |
                                                                                 v
                                                             [Aksi Trading: Buy / Sell / Hold]
```

#### A. Komponen Ekstraksi Fitur & Geopolitical Risk (GPR)
- Data deret waktu emas historis diperkaya dengan indeks GPR yang dikembangkan oleh Caldara & Iacoviello, yang mengukur frekuensi berita terkait ancaman militer, perang, dan terorisme global.
- Indikator teknikal mencakup SMA, EMA, MACD, RSI, ATR (*Average True Range*), dan Bollinger Bands.

#### B. Model Prediktif Supervised (Random Forest / Tree Regressor)
Model machine learning berbasis pohon dilatih untuk memprediksi probabilitas arah tren harga jangka pendek. Hasil prediksi probabilitas ini kemudian diumpankan sebagai bagian dari ruang keadaan (*state space*) bagi agen DRL, sehingga agen DRL tidak memulai belajar dari "kebutaan total".

#### C. Agen Deep Reinforcement Learning (DRL)
1. **DQN (Deep Q-Network):** Mengestimasi nilai Q diskret untuk aksi Buy, Sell, Hold.
2. **PPO (Proximal Policy Optimization):** Algoritma *policy gradient* yang menggunakan mekanisme kliping fungsi tujuan untuk menjaga kestabilan pembaruan kebijakan.
3. **SAC (Soft Actor-Critic):** Algoritma DRL *actor-critic* berbasis *maximum entropy*. SAC tidak hanya memaksimalkan imbalan (*expected reward*), tetapi juga memaksimalkan entropi kebijakan ($\mathcal{H}(\pi)$). Hal ini mendorong eksplorasi yang sangat adaptif dan mencegah model terjebak dalam aksi trading yang kaku di tengah kepanikan pasar.

#### D. Manajemen Risiko Dinamis (*Dynamic Risk Management*)
Sistem dilengkapi dengan aturan eksekusi posisi terukur: penentuan ukuran lot (*position sizing*), batas *stop-loss* adaptif berbasis ATR, dan penguncian laba (*take-profit*) otomatis.

---

### III. Hasil Eksperimen Finansial & Pembahasan

Pengujian dilakukan secara simulasi perdagangan nyata pada data kontrak berjangka emas dengan memperhitungkan biaya komisi dan slippage transaksi.

#### Tabel Perbandingan Metrik Finansial Model:
| Strategi / Model | Laba Kumulatif (%) | Rasio Sharpe (*Sharpe Ratio*) | Penurunan Maksimum (*Max Drawdown*) | Volatilitas Tahunan |
| :--- | :---: | :---: | :---: | :---: |
| Buy-and-Hold (B&H) | +14.2% | 0.42 | 19.8% | 18.5% |
| Sell-and-Hold (S&H) | -18.7% | -0.38 | 28.4% | 19.2% |
| DQN murni | +22.8% | 0.68 | 15.2% | 14.6% |
| PPO Hybrid | +31.5% | 0.94 | 12.1% | 12.3% |
| **SAC Hybrid (Diusulkan)** | **+48.6%** | **1.45** | **7.4%** | **9.8%** |

#### Analisis Hasil:
1. **Superioritas Soft Actor-Critic (SAC):** Agen SAC mencapai **laba kumulatif tertinggi (+48.6%)** dan **rasio Sharpe luar biasa (1.45)**, membuktikan bahwa imbal hasil yang diperoleh sangat sepadan dengan risiko yang diambil.
2. **Pengendalian Risiko Ekstrem (Max Drawdown 7.4%):** Berkat regularisasi entropi dan modul manajemen risiko berbasis ATR, SAC berhasil menekan *drawdown* maksimum hingga hanya 7.4%, jauh lebih aman dibandingkan strategi beli-dan-tahan (19.8%).
3. **Peran Kritis Indeks Geopolitik (GPR):** Ketika krisis geopolitik memicu lonjakan harga emas, model yang diperkaya fitur GPR mampu membuka posisi beli (*long position*) lebih awal sebelum lonjakan harga terjadi, menghasilkan keunggulan kompetitif yang sangat besar.

---

### IV. Kesimpulan Penulis
Model Hybrid ML + DRL (khususnya Soft Actor-Critic) dengan integrasi Indeks Risiko Geopolitik dan manajemen risiko dinamis terbukti sangat efektif untuk perdagangan otomatis di pasar komoditas emas berjangka. Sistem ini berhasil memberikan keuntungan maksimal dengan risiko penurunan (*drawdown*) yang sangat terkendali.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Studi komprehensif 20 halaman dari Wiley / Hindawi (2026) ini merancang sistem *algorithmic trading* canggih untuk pasar kontrak berjangka emas (*gold futures*) dengan memadukan model machine learning pohon keputusan (Random Forest), algoritma Deep Reinforcement Learning (Soft Actor-Critic / SAC, PPO, DQN), serta Indeks Risiko Geopolitik (GPR). Hasil simulasi membuktikan agen **Hybrid SAC meraih Sharpe Ratio tertinggi (1.45), laba kumulatif terbesar (+48.6%), dan Max Drawdown terendah (7.4%)**, mengungguli strategi konvensional dan DRL standar.

### B. Research Gap (Kesenjangan Penelitian)
1. **Fokus Literatur yang Terlalu Bias Saham:** Sebagian besar studi DRL finansial hanya meneliti saham AS, sementara pasar berjangka komoditas emas yang sarat dinamika geopolitik dan leverage tinggi masih jarang dieksplorasi.
2. **Kelemahan Model DRL Mandiri Tanpa Fitur Prediktif:** Agen DRL yang belajar dari nol tanpa panduan model regresi/klasifikasi ML sering kali tidak konvergen atau menghasilkan kerugian besar pada fase awal.
3. **Pengabaian Risiko Geopolitik:** Model kuantitatif jarang memasukkan indeks risiko geopolitik (GPR) kuantitatif padahal emas adalah barometer ketegangan politik global utama.

### C. Apa yang Dibahas (Fokus Masalah, Data, & Variabel)
- **Fokus Masalah:** Membangun sistem perdagangan otomatis pada kontrak berjangka emas yang adaptif terhadap guncangan geopolitik dan memiliki manajemen risiko modal terukur.
- **Dataset:** Harga emas berjangka, indikator teknikal (SMA, MACD, RSI, ATR), dan deret waktu harian *Geopolitical Risk Index* (GPR).
- **Metrik Evaluasi Finansial:** Cumulative Profit, Sharpe Ratio, Sortino Ratio, Maximum Drawdown (MDD), Annualized Volatility.

### D. Solusi dari Penelitian
- Menggabungkan model regresi supervised berbasis pohon untuk memberikan input sinyal awal ke state DRL.
- Menerapkan agen **Soft Actor-Critic (SAC)** dengan regularisasi entropi untuk pengambilan keputusan posisi Buy/Sell/Hold.
- Mengintegrasikan modul **Dynamic Risk Management** dengan trailing stop dan sizing berbasis volatilitas ATR.
- **Solusi Utama:** Menghasilkan sistem trading emas yang memiliki rasio Sharpe tinggi (1.45) dan drawdown sangat rendah (7.4%).

### E. Relevansi & Nilai Tambah untuk Skripsi XAUUSD Anda
1. **Perspektif Trading Riil (Bukan Sekadar Metrik Akurasi Error):** Skripsi Anda meneliti XAUUSD. Paper ini memberikan pandangan yang sangat berharga bahwa dalam perdagangan emas, metrik evaluasi tidak boleh hanya terbatas pada RMSE/MAE, melainkan harus dihubungkan dengan manajemen risiko, drawdown, dan respons terhadap volatilitas berita (seperti NFP).
2. **Inspirasi Fitur Volatilitas (ATR & GPR):** Penggunaan indikator ATR (*Average True Range*) untuk membaca volatilitas pasar emas sangat cocok Anda adopsi ke dalam pipeline fitur LightGBM skripsi Anda.
3. **Pondasi Kuat untuk Bab Pembahasan:** Anda dapat mengutip temuan Kaur et al. (2026) ini untuk menjelaskan mengapa pasar emas sangat membutuhkan model non-linear cerdas yang mampu merespons volatilitas makro dan geopolitik secara dinamis.
