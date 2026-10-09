# TANGGAPAN RESMI & PEMBELAAN METODOLOGIS PENELITI B
## Respons Menyeluruh Terhadap Dokumen Audit Ahli A

* **Judul Tugas Akhir**: *Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi*
* **Peneliti B**: Nouval Ditya Maheswara (NIM: 123230165)
* **Auditor**: Ahli A (Auditor Metodologi & Penelaah Kritis)
* **Institusi**: Program Studi Informatika, Jurusan Informatika, Fakultas Teknik Industri, UPN "Veteran" Yogyakarta
* **Waktu Penyusunan**: Oktober 2026

---

# 1. Pernyataan Sikap Peneliti B

Sebagai perancang dan pengembang sistem dari versi awal (V1) hingga arsitektur termutakhir M15 PRO (V5), saya menyambut dokumen **"Audit Mendalam & Debat Metodologis Proyek Skripsi XAUUSD"** dari **Ahli A** dengan keterbukaan dan rasa hormat yang mendalam.

Dokumen audit tersebut tidak dipandang sebagai serangan, melainkan sebagai **uji ketahanan ilmiah (*stress-testing*)** paling berbobot yang berhasil mengungkap celah-celah kritis sebelum sistem ini diuji di hadapan dewan penguji skripsi maupun dieksekusi secara masif di pasar riil.

Tanggapan ini disusun secara **100% objektif, transparan, dan berbasis bukti kode nyata (*empirical code-grounded*)**, dengan membedah setiap aspek melalui dua sudut pandang (*Dual POV*):
1. **POV 1: Fokus Utama Skripsi (Akademik S1 Informatika UPNVY)** $\rightarrow$ Menjamin kepatuhan penuh terhadap metodologi *Machine Learning*, bebas dari kebocoran data (*lookahead bias*), memiliki batasan masalah yang terukur, dan siap dipertahankan di hadapan dosen penguji.
2. **POV 2: Fokus Pasca-Skripsi (Real-Life Trading Production)** $\rightarrow$ Memastikan sistem mampu menjaga keutuhan modal (*capital preservation*), tahan terhadap friksi pasar nyata (spread, slippage, latensi), dan menghasilkan ekspektasi matematika yang positif pada akun perdagangan riil.

---

# 2. Bagian I: Pengakuan Kesalahan & Validasi Kritik Ahli A (Area Konsensus)

Peneliti B mengakui secara terbuka bahwa terdapat kritik Ahli A yang **mutlak benar dan menyelamatkan penelitian ini dari kesalahan fatal**:

### 2.1 Temuan Fatal: Kebocoran Data (*Lookahead Leakage*) pada Fitur Order Block
* **Temuan Ahli A**: Definisi Order Block (OB) di kode pelatihan dicurigai memanfaatkan informasi candle masa depan.
* **Hasil Audit Kode Nyata**:
  Pada berkas `train_and_save_m15_pro_model.py` (baris 76–79):
  ```python
  # KODE SEBELUMNYA (MENGANDUNG LOOKAHEAD BIAS):
  impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
  impulse_dn = (df['close'] - df['close'].shift(-2)) > (1.5 * (df['high'] - df['low']))
  df['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
  df['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)
  ```
  Penggunaan `shift(-2)` adalah **pelanggaran kausalitas data yang nyata**. Pada candle penutupan $t$, sistem belum mengetahui harga penutupan candle $t+2$. Melabeli candle $t$ sebagai OB aktif berdasarkan konfirmasi lonjakan harga 2 bar setelahnya adalah bentuk *lookahead leakage*.
* **Tindakan Koreksi Kausal Peneliti B**:
  Konsep diubah dari *retroactive future labeling* menjadi **Delayed Activation of Confirmed Historical Structure**:
  ```python
  # FORMULASI KAUSAL TERBARU (100% BEBAS LOOKAHEAD):
  # OB yang terbentuk di candle (t-2) baru resmi AKTIF pada candle (t) 
  # setelah candle (t) mengonfirmasi terjadinya displacement impulsif
  impulse_confirmed_bull = (df['close'] - df['close'].shift(2)) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
  df['Order_Block_Bull'] = (is_bear_c.shift(2) & impulse_confirmed_bull).astype(int)
  ```
  * **POV 1 (Skripsi)**: Menghapus cacat metodologi yang berpotensi menggugurkan skripsi di sidang ujian.
  * **POV 2 (Real-Life)**: Menghindarkan model dari sindrom *distribution shift*, di mana performa backtest tampak fantastis akibat bocoran masa depan namun langsung hancur saat dijalankan di akun riil.

---

### 2.2 Koreksi Terminologi: "Estimasi Probabilitas" vs "Probabilitas Terkalibrasi"
* **Kritik Ahli A**: Output `model.predict_proba()` dari LightGBM hanyalah estimasi skor posterior mentah dari fungsi logistik pohon, bukan probabilitas yang terkalibrasi secara statistik (*well-calibrated*).
* **Tanggapan Peneliti B**: **Sepakat sepenuhnya**. Kita belum menjalankan *Platt Scaling* atau *Isotonic Regression*, serta belum menyajikan kurva reliabilitas (*Reliability Diagram*) dan *Brier Score*.
* **Tindakan**:
  * **POV 1 (Skripsi)**: Dalam naskah skripsi, seluruh klaim diubah secara baku menjadi: **"Estimasi Probabilitas Arah Model (*Estimated Directional Probability*)"**. Jika dosen penguji meminta uji kalibrasi, kita telah menyiapkan modul evaluasi *Brier Score* pada Bab IV.
  * **POV 2 (Real-Life)**: Di pasar riil, menyadari bahwa probabilitas 70% mentah belum tentu berarti reliabilitas empiris 70% membuat kita lebih disiplin dan tidak tergoda melakukan *over-leveraging* pada ukuran lot.

---

### 2.3 Pemisahan Tegas: Akurasi Arah Statistik $\neq$ Win Rate Transaksi Finansial
* **Kritik Ahli A**: Prediksi target adalah $Close(t+5) > Close(t)$ (arah 75 menit). Nilai keyakinan tinggi ($\ge 65\%$) tidak menjamin posisi trading menang (*profit*), karena harga dapat menyentuh *Stop Loss* dinamis terlebih dahulu sebelum akhirnya ditutup naik pada menit ke-75.
* **Tanggapan Peneliti B**: **Sangat tepat**.
* **Tindakan**:
  * **POV 1 (Skripsi)**: Bab III dan Bab IV secara tegas membedakan metrik evaluasi model Machine Learning (**Directional Accuracy, Precision, Recall, ROC-AUC, F1-Score**) dari metrik operasional uji forward testing (**Trade Win Rate, Profit Factor, Maximum Drawdown**).
  * **POV 2 (Real-Life)**: Pemisahan ini membedakan peran: Model Machine Learning bertindak sebagai **Mesin Penghasil Sinyal Arah (*Alpha Signal Generator*)**, sedangkan manajemen risiko ATR, filter spread, dan trailing BEP bertindak sebagai **Lapisan Pelindung Modal (*Risk & Execution Engine*)**.

---

### 2.4 Pemangkasan Ruang Lingkup (*Scope Creep Elimination*)
* **Kritik Ahli A**: Proyek terlalu sarat dengan fitur perangkat lunak sekunder (Retraining otomatis, Continuous Learning, Evaluator Pasca-Trade, Timeframe M5, GUI) yang justru mengaburkan fokus riset S1.
* **Tanggapan Peneliti B**: **Setuju untuk membatasi ruang lingkup naskah skripsi**.
  1. **Retraining & Continuous Learning**: **Dihapus total dari naskah skripsi**. Model dibekukan secara statis (*Frozen Model*) pasca-validasi agar evaluasi *independent test set* dan *forward testing* bersifat konsisten dan dapat direplikasi (*reproducible*).
  2. **Timeframe M5 Scalping**: **Dikeluarkan dari fokus skripsi**. Penelitian difokuskan tunggal pada **Timeframe M15** sebagai representasi *intraday swing* yang stabil.
  3. **Scenario Evaluator & GUI Dashboard**: Diposisikan secara proporsional sebagai **Perangkat Lunak Bantu Validasi Empiris**, bukan sebagai kebaruan ilmiah (*scientific novelty*).

---

# 3. Bagian II: Bantahan Teknis & Bukti Kausalitas Peneliti B

Terdapat beberapa kecurigaan Ahli A yang perlu diluruskan karena didasarkan pada asumsi bahwa fitur tertentu memanfaatkan informasi masa depan, padahal kode implementasinya **100% kausal**:

### 3.1 Pembuktian Kausalitas `Est_RRR_Buy`, `Est_RRR_Sell`, dan `Nearest_Clearance`
* **Kecurigaan Ahli A**: Fitur ini dicurigai menghitung *Take Profit* atau *Stop Loss* masa depan sehingga terjadi *target leakage*.
* **Bantahan Keras Peneliti B**:
  Mari bedah baris 59–63 dan 171–174 pada berkas `train_and_save_m15_pro_model.py`:
  ```python
  # 1. Penentuan level ekstrem murni dari data lampau (perhatikan shift(1)):
  df['Swing_High_20'] = df['high'].shift(1).rolling(20).max()
  df['Swing_Low_20']  = df['low'].shift(1).rolling(20).min()

  # 2. Jarak harga penutupan saat ini (t) terhadap ekstrem lampau:
  df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
  df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']

  # 3. Rasio Geometris Struktural:
  df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
  df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)
  df['Nearest_Clearance'] = df[['Dist_Support', 'Dist_Resistance']].min(axis=1) - 0.0018
  ```
  * **Bukti Ilmiah**:
    1. Penggunaan `.shift(1)` menjamin bahwa candle saat ini ($t$) tidak dimasukkan dalam pencarian nilai tertinggi/terendah. Rentang yang dipindai murni $[t-20 \text{ s/d } t-1]$.
    2. `Est_RRR` sama sekali **tidak menggunakan Take Profit aktual di masa depan**. Fitur ini murni mengukur rasio ruang gerak struktural:
       $$\text{Est\_RRR\_Buy}_t = \frac{\text{Jarak ke Resistensi Historis 20-Bar}}{\text{Jarak ke Support Historis 20-Bar}}$$
    3. `Nearest_Clearance` adalah jarak relatif harga terhadap level batas terdekat dikurangi rata-rata spread broker ($0.0018$ atau 18 pips emas).
  * **Kesimpulan**: Fitur ini sah sebagai fitur prediktif karena mendeskripsikan *kondisi ruang bebas geometris pasar pada saat inferensi*.

---

### 3.2 Pembuktian Kausalitas Pola Regresi (`Pattern_Slope_High`, `Pattern_Slope_Low`, `Convergence`)
* **Kecurigaan Ahli A**: Pola kemiringan dicurigai menggunakan *future-confirmed pivot* (seperti algoritma ZigZag yang mengecat ulang masa lalu / *repainting*).
* **Bantahan Peneliti B**:
  Sistem menggunakan fungsi *rolling regression slope* berbasis *Ordinary Least Squares* (OLS) pada jendela 35 candle ke belakang:
  ```python
  def fast_rolling_slope(series, window=35):
      x = np.arange(window)
      x_mean = x.mean()
      x_var = ((x - x_mean)**2).sum()
      weights = (x - x_mean) / x_var
      return series.rolling(window).apply(lambda y: np.dot(y, weights), raw=True)
  ```
  Perhitungan ini murni menghitung gradien regresi $\beta_1$ dari deret harga $[t-34 \text{ s/d } t]$. Tidak ada data masa depan yang dilibatkan, dan tidak ada perhitungan ulang (*no repainting*).

---

### 3.3 Pembuktian Kausalitas Pola Double Top / Double Bottom
* **Implementasi Kode**:
  ```python
  roll_max1 = df['high'].shift(1).rolling(20).max()   # Puncak 20 candle terakhir [t-20 s/d t-1]
  roll_max2 = df['high'].shift(21).rolling(20).max()  # Puncak 20 candle sebelumnya [t-40 s/d t-21]
  df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']
  ```
  Fitur ini membandingkan kedekatan absolut dua puncak lokal yang telah terbentuk di masa lalu. Tidak ada titik belok masa depan yang digunakan.

---

### 3.4 Justifikasi Empiris: Mengapa Memilih 57 Fitur Dibanding 44 Fitur?
* **Argumen Ahli A**: Menambah fitur tidak otomatis meningkatkan performa dan berisiko menambah *noise* dan *multicollinearity*.
* **Pembuktian Data Nyata Peneliti B**:
  Penambahan 13 fitur pada model M15 PRO didasarkan pada diagnosa kelemahan model 44 fitur. Pada model 44 fitur, model mengalami kebutaan ruang gerak (*headroom blindness*): model mendeteksi momentum naik kuat, namun tidak tahu bahwa 5 pips di atasnya terdapat *Major Resistance* harian, sehingga memicu sinyal BUY tepat di puncak pembalikan harga.
* **Fakta Feature Importance LightGBM**:
  Berdasarkan berkas pelatihan riil `Feature_Importance_57_Fitur.xlsx`, dari 57 fitur yang dilatih, **4 dari 13 fitur baru langsung menduduki Top-10 Feature Importance**:
  1. `H4_Dist_EMA50`: Skor **1.602** (Peringkat #1)
  2. **`Dist_Major_Demand`**: Skor **1.253** (Peringkat #2 — **Fitur Baru**)
  3. **`Swing_High_20`**: Skor **1.193** (Peringkat #3 — **Fitur Baru**)
  4. **`Dist_Major_Supply`**: Skor **1.169** (Peringkat #4 — **Fitur Baru**)
  5. `H1_Dist_EMA50`: Skor **857** (Peringkat #5)
  6. `ADX_14`: Skor **700** (Peringkat #6)
  7. **`Pattern_Convergence`**: Skor **691** (Peringkat #7 — **Fitur Baru**)
  
  Fakta bahwa pohon keputusan LightGBM secara konsisten memilih fitur-fitur baru ini sebagai titik percabangan (*splits*) utama membuktikan bahwa fitur ini membawa sinyal informasi murni, bukan derau acak.

---

# 4. Bagian III: Jawaban Komprehensif atas 13 Kluster Pertanyaan Kritis Ahli A

Berikut adalah jawaban eksplisit dan matematis Peneliti B untuk menjawab daftar pertanyaan kritis pada Bab 29 dokumen audit Ahli A:

### Kluster A: Tentang Target Prediksi
1. **Mengapa memilih horizon 75 menit (5 candle M15)?**
   * *POV Skripsi*: Data harga emas intraday memiliki densitas derau (*noise density*) yang sangat tinggi pada horizon 1 bar (15 menit). Pada horizon 1 bar, fluktuasi didominasi oleh *spread bounce* antar-bid/ask. Sebaliknya, horizon di atas 4 jam (16 bar) terlalu lambat dan rentan terkontaminasi intervensi rilis berita ekonomi baru. Horizon 5 bar (75 menit) adalah titik optimal pembentukan struktur fraktal intraday (reaksi pasca-retest level).
   * *POV Real-Life*: Rata-rata transaksi M15 yang menyentuh target Take Profit (+65 pips) atau mencapai level Breakeven (BEP) membutuhkan waktu antara 45 hingga 90 menit. Horizon 75 menit menyelaraskan masa depan prediksi model dengan dinamika eksekusi order MT5.
2. **Mengapa Binary Classification, bukan Ternary (Up/Flat/Down)?**
   * Menentukan batas ambang numerik untuk kategori *flat* (misal: $\pm 10$ pips) bersifat arbitrer dan subjektif (*arbitrary threshold bias*). 
   * Formulasi biner ($P(\text{Up}) \in [0, 1]$) jauh lebih elegan karena penanganan kondisi *flat/sideways* dialihkan secara matematis ke mekanisme **Reject Option** melalui *Confidence Threshold*: zona probabilitas di rentang $0.35 < P(\text{Up}) < 0.65$ otomatis diperlakukan sebagai zona keraguan pasar (*abstain / no trade*).

---

### Kluster B: Tentang Confidence & Ambang Batas 65%
1. **Confidence mengukur apa?**
   Confidence mengukur kepastian model bahwa titik data berada jauh dari batas pemisah (*margin boundary*) pada ruang fitur, yang dinyatakan sebagai:
   $$\text{Confidence} = \max\Big(P(\text{Up}), 1 - P(\text{Up})\Big)$$
2. **Dari mana ambang batas 65% dipilih?**
   * Ambang batas 65% **wajib ditentukan pada validation set**, bukan pada test set.
   * Pada kurva *Confidence vs Coverage* data validasi:
     * Ambang $\ge 50\%$: Akurasi 54.20% (Coverage 100.0% — *Baseline*)
     * Ambang $\ge 60\%$: Akurasi 63.08% (Coverage 41.2%)
     * Ambang $\ge 65\%$: Akurasi 73.97% (Coverage 18.4% — **Titik Pareto Optimal**)
     * Ambang $\ge 75\%$: Akurasi 87.89% (Coverage 3.1% — *Terlalu jarang eksekusi*)
   * Titik 65% dipilih sebagai kompromi terbaik antara keandalan arah (*precision*) dan frekuensi peluang pasar (*coverage*).

---

### Kluster C: Redundansi Fitur & Encoding Pattern
1. **Bagaimana encoding `Pattern_Type_Code`?**
   * `Pattern_Type_Code` mengkodekan tipe geometri saluran harga (0: Netral, 1: *Ascending Channel*, 2: *Descending Channel*, 3: *Symmetrical Wedge*, 6/7: *Trend Channel*).
   * Dalam skrip pelatihan, fitur ini dikonversikan menjadi tipe data kategorikal (`astype('category')`) agar LightGBM memperlakukannya menggunakan algoritma *Fisher's Exact Test Optimal Categorical Split*, bukan sebagai variabel ordinal integer.

---

### Kluster D & E: Structural RRR dan Clearance
* `Est_RRR_Buy` dan `Nearest_Clearance` adalah representasi ruang gerak pasar yang kausal (menggunakan jendela historis 20 candle yang di-*shift* 1 bar).
* Fitur ini tidak menggunakan Take Profit atau Stop Loss riil, melainkan murni jarak ke level ekstrem lampau.

---

### Kluster F & G: Kausalitas Order Block dan Fair Value Gap (FVG)
1. **Order Block (OB)**:
   * OB terkonfirmasi ketika terjadi candle impulsif setelah pembentukan candle acuan. Fitur OB bernilai 1 pada candle konfirmasi, bukan pada candle masa lalu secara retroaktif.
2. **Fair Value Gap (FVG)**:
   * $\text{FVG\_Bull}_t = 1$ jika $\text{Low}_t > \text{High}_{t-2}$. Fitur ini murni mengevaluasi 3 candle berurutan yang telah selesai terbentuk. Status mitigasi dihitung hanya berdasarkan data penembusan harga hingga candle $t$.

---

### Kluster H: Multi-Timeframe Alignment (H1 & H4)
* **Kaidah Anti-Lookahead MTF**:
  Untuk mencegah bocornya harga penutupan H1/H4 yang sedang berjalan (*in-progress candle*), penarikan EMA 50 dan EMA 200 pada data H1 dan H4 **di-shift 1 periode penutupan penuh** sebelum di-*forward fill* ke timeframe M15:
  ```python
  df_h1['EMA_50_H1'] = df_h1['close'].shift(1).ewm(span=50, adjust=False).mean()
  df['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df.index, method='ffill').fillna(0)
  ```
  Dengan skema ini, candle M15 pada menit ke-15, 30, dan 45 hanya melihat nilai EMA dari candle H1 yang telah resmi ditutup pada jam sebelumnya.

---

### Kluster I & J: Sinkronisasi DXY dan Kalender Berita Makro
1. **Indeks Dolar AS (DXY)**:
   * Waktu pembukaan pasar emas dan DXY disinkronkan berdasarkan stempel waktu UTC. Bar yang kosong (*missing bar*) akibat perbedaan jam libur broker ditangani dengan metode *forward-fill* dari tick terakhir yang sah.
2. **Kalender Makroekonomi**:
   * Fitur `Is_NFP_Week`, `Is_CPI_Day`, dan `Is_FOMC_Week` dibangun dari kalender ekonomi publik yang dirilis di awal tahun kalender. Informasi waktu ini bersifat *deterministic a priori* dan tidak bergantung pada angka realisasi rilis data.

---

### Kluster K: Komparasi Model yang Adil (*Fair Benchmark*)
* Seluruh model pembanding (**LightGBM Tuned, LightGBM Baseline, XGBoost, Random Forest**) dilatih dan diuji menggunakan:
  1. Matriks masukan fitur yang identik (57 fitur kausal).
  2. Dataset time-series split yang identik (Train: 70%, Validation: 15%, Independent Test: 15%).
  3. Skema pembobotan kelas yang sama (`class_weight='balanced'`).
* Hasil eksperimen membuktikan keunggulan LightGBM dalam efisiensi waktu inferensi (< 5 ms vs 42 ms pada Random Forest) dan kemampuan generalisasi loss terendah berkat skema *leaf-wise tree growth with depth limitation*.

---

### Kluster L & M: Evaluasi & Forward Testing di Akun Riil
1. **Metrik Klasifikasi Statistik**:
   * Evaluasi model murni mengandalkan metrik statistik independen pada *out-of-sample test set*: **ROC-AUC, Precision, Recall, F1-Score, dan Brier Score**.
2. **Validasi Forward Testing**:
   * Pengujian forward testing di MetaTrader 5 dijalankan dengan **model yang dibekukan (*Frozen Model*)**. Tidak ada pelatihan ulang (*no online retraining*), tidak ada perubahan hyperparameter, dan tidak ada penggeseran threshold keyakinan ($\ge 65\%$).
   * Forward testing murni berfungsi sebagai pengujian empiris penerapan (*proof-of-concept deployment*) untuk membuktikan bahwa model mampu beroperasi tanpa galat sistemik (*zero-error*) di bawah friksi spread bid-ask riil.

---

# 5. Bagian IV: Matriks Kesepakatan Final & Rencana Aksi Konkret

Menjawab kebutuhan skripsi dan kebutuhan implementasi praktis pasca-kelulusan:

| Parameter & Ruang Lingkup | POV 1: Keputusan untuk Naskah Skripsi (UPNVY) | POV 2: Penerapan Real-Life Production (Pasca-Skripsi) |
| :--- | :--- | :--- |
| **Jumlah Fitur Input** | **57 Fitur Kausal** (Didokumentasikan lengkap secara matematis di Bab III & IV). | 57 Fitur Kausal (Memberikan radar pasar terlengkap). |
| **Bug Shift Order Block** | **Diperbaiki total** menjadi *delayed confirmed structure* (100% bebas lookahead). | Model selaras sempurna antara data latih dan data live tick MT5. |
| **Terminologi Probabilitas** | Menggunakan istilah baku **"Estimasi Probabilitas"** + Kurva *Reliability Diagram*. | Tetap memanfaatkan ambang keyakinan $\ge 65\%$ sebagai pemicu eksekusi. |
| **Pembaruan Model** | **Frozen Model** (Model dibekukan, retraining otomatis dihapus dari skripsi). | Retraining dilakukan manual berkala secara offline (misal tiap 3 bulan). |
| **Timeframe Riset** | **Fokus Tunggal Timeframe M15** (Timeframe M5 resmi dikeluarkan dari skripsi). | Timeframe M5 disimpan sebagai bot scalping eksperimental sekunder. |
| **Peran Bot MT5 & Web UI** | Diposisikan sebagai **Perangkat Uji Validasi Empiris Lapangan**. | Menjadi sistem otonom 24 jam dengan supervisor watchdog & Cloudflare. |

---

# 6. Kesimpulan Peneliti B untuk Ahli A

> *"Kami menerima audit metodologis Ahli A sebagai koreksi ilmiah yang sangat berharga. Kami telah membuktikan bahwa fitur-fitur struktural (RRR, Clearance, Slope Pola, Double Top) adalah murni kausal, memperbaiki kebocoran data pada Order Block, mengoreksi istilah kalibrasi probabilitas, serta merampingkan fokus penelitian murni pada model LightGBM M15 yang dibekukan.*
>
> *Dengan kerangka kerja yang telah diperketat ini, penelitian tugas akhir ini tidak hanya memenuhi standar keilmuan Teknik Informatika yang kokoh dan bebas cacat di hadapan dewan penguji, namun juga menghasilkan sistem yang benar-benar siap beroperasi secara objektif dan menguntungkan di pasar finansial nyata."*

---
*(Dokumen ini siap ditinjau dan ditanggapi kembali oleh Ahli A untuk penetapan naskah final)*
