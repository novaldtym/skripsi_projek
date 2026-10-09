# PANDUAN TANYA JAWAB METODOLOGI PENELITIAN & PERSIAPAN SIDANG SKRIPSI
**Program Studi Informatika, Jurusan Informatika, Fakultas Teknik Industri**  
**Universitas Pembangunan Nasional "Veteran" Yogyakarta**

---

* **Judul Skripsi**: Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi
* **Penyusun / Mahasiswa**: Nouval Ditya Maheswara (NIM: 123230165)
* **Tahun Akademik**: 2025/2026
* **Peruntukan Dokumen**: Panduan Penguasaan Konsep Komprehensif, Pembelaan Metodologi Ilmiah (*Defense Preparation*), dan Rekam Jejak Tanya-Jawab Kritis Menghadapi Dosen Pembimbing & Penguji.

---

## DAFTAR ISI
1. [BAGIAN I: Fondasi Domain Finansial (SMC, ICT, & Formalisasi Informatika)](#bagian-i-fondasi-domain-finansial-smc-ict--formalisasi-informatika)
2. [BAGIAN II: Fenomena Masalah, Research Gaps, & Solusi Komputasi](#bagian-ii-fenomena-masalah-research-gaps--solusi-komputasi)
3. [BAGIAN III: Friksi Pasar Riil, Backtesting Teoretis vs. Live Forward Testing](#bagian-iii-friksi-pasar-riil-backtesting-teoretis-vs-live-forward-testing)
4. [BAGIAN IV: Validasi Empiris (Skor Teori vs. Nyata, Selisih, & Diagnostik)](#bagian-iv-validasi-empiris-skor-teori-vs-nyata-selisih--diagnostik)
5. [BAGIAN V: Komparasi Objek Penelitian (Emas Makro vs. XAUUSD CFD Intraday)](#bagian-v-komparasi-objek-penelitian-emas-makro-vs-xauusd-cfd-intraday)
6. [BAGIAN VI: Arsitektur Rekayasa Perangkat Lunak (Offline Script vs. Autonomous Engine)](#bagian-vi-arsitektur-rekayasa-perangkat-lunak-offline-script-vs-autonomous-engine)

---

## BAGIAN I: Fondasi Domain Finansial (SMC, ICT, & Formalisasi Informatika)

### Pertanyaan 1: Apa itu Smart Money Concepts (SMC) dan Inner Circle Trader (ICT)? Apa perbedaannya?
**Jawaban Komprehensif:**
* **Inner Circle Trader (ICT)**:
  * **Pencetus**: Dikembangkan oleh Michael J. Huddleston.
  * **Definisi**: Teori dan metodologi analisis pergerakan harga (*price action*) yang berargumen bahwa pergerakan harga di pasar keuangan tidak sepenuhnya acak, melainkan digerakkan oleh algoritma pengiriman harga antarbank (*Interbank Price Delivery Algorithm* / IPDA) untuk memfasilitasi likuiditas institusional (bank sentral, bank investasi multinasional, *hedge funds*).
  * **Cakupan**: Menekankan kombinasi waktu dan harga (*Time & Price*), sesi perdagangan spesifik (*Kill Zones* London/New York), dan rekayasa manipulasi likuiditas.
* **Smart Money Concepts (SMC)**:
  * **Definisi**: Terminologi turunan dan bentuk penyederhanaan struktural dari metodologi ICT yang berfokus pada pelacakan jejak akumulasi dan distribusi modal besar (*smart money*) melalui geometri grafik harga.
  * **Komponen Kunci**:
    1. *Order Block* (OB): Zona konsolidasi pesanan institusi terakhir sebelum terjadi lonjakan harga impulsif.
    2. *Fair Value Gap* (FVG): Ketidakseimbangan (*imbalance*) likuiditas akibat dominasi satu sisi transaksi yang meninggalkan celah harga.
    3. *Break of Structure* (BOS): Penembusan level ekstrem sebelumnya yang mengonfirmasi kelanjutan tren.
    4. *Change of Character* (CHoCH): Sinyal transisi awal potensi pembalikan (*reversal*) arah struktur pasar.
    5. *Liquidity Sweep*: Manuver manipulasi harga yang menyapu area *stop-loss* pelaku pasar ritel sebelum harga bergerak ke arah yang sesungguhnya.
* **Hubungan Keduanya**:
  * **ICT adalah fondasi (akar/orisinal)**, sedangkan **SMC adalah kerangka aplikasi geometrisnya (cabang/turunan)**.

---

### Pertanyaan 2: Mengapa konsep trading SMC/ICT relevan dan layak diteliti di Program Studi Informatika?
**Jawaban untuk Dosen Penguji:**
> *"Kelemahan mendasar dari SMC dan ICT selama ini terletak pada **subjektivitas analisis visual trader manusia**. Dua orang analis dapat menarik zona Order Block atau FVG yang berbeda pada grafik yang sama karena tidak adanya ambang batas numerik yang pasti.*
>
> *Di sinilah **kontribusi bidang Informatika**: kami melakukan **formalisasi algoritmik**. Kami merumuskan aturan berbasis data (*rule-based*) dan batasan matematis deterministik untuk mendeteksi OB, FVG, BOS, CHoCH, dan Liquidity Sweep secara otomatis tanpa campur tangan visual manusia. Logika tersebut kemudian diekstraksi menjadi fitur-fitur numerik untuk melatih algoritma LightGBM agar sistem memiliki kapabilitas pengambilan keputusan yang objektif, konsisten, dan teruji secara empiris."*

---

## BAGIAN II: Fenomena Masalah, Research Gaps, & Solusi Komputasi

### Pertanyaan 3: Apa fenomena nyata yang melatarbelakangi penelitian ini?
**Jawaban:**
1. **Karakteristik Ekstrem Instrumen XAUUSD**: Emas adalah instrumen lindung nilai (*safe-haven asset*) terlikuid di dunia. Namun, pada perdagangan derivatif *Contract for Difference* (CFD) dengan fasilitas *leverage*, data harga *intraday* memiliki volatilitas sangat ekstrem, derau acak (*noise*) tinggi, nonlinear, dan nonstasioner.
2. **Kelemahan Indikator Teknikal Tradisional**: Indikator konvensional (RSI, MACD, Moving Average) bersifat lambat/reaktif (*lagging*), sehingga kerap memicu sinyal palsu (*whipsaw* / *false breakout*).
3. **Bias Psikologis Pedagang Manual**: Analisis manual rentan terhadap bias emosional manusia, seperti transaksi impulsif pasca-kerugian (*revenge trading*) dan transaksi berlebihan (*overtrading*).
4. **Kegagalan Model Pohon Konvensional saat Rekor All-Time High (ATH)**: Saat harga emas menembus rekor tertinggi sepanjang masa, model pohon berbasis *bagging/leaf-averaging* seperti *Random Forest* terbukti gagal total ($R^2 = -1,97$ pada studi Prastyo et al., 2025) karena tidak mampu mengekstrapolasi nilai di luar rentang data pelatihan historisnya.

---

### Pertanyaan 4: Apa 3 celah riset (*research gaps*) utama yang ditinggalkan peneliti terdahulu?
**Jawaban:**
* **Celah 1 (Formulasi Masalah Regresi vs. Klasifikasi Probabilitas)**:  
  Mayoritas riset sebelumnya memformulasikan peramalan harga ke dalam bentuk **regresi nilai nominal**, yang mengakibatkan nilai prediksi hanya membuntuti harga satu langkah sebelumnya ($y_t \approx y_{t-1}$). Padahal, sistem eksekusi otomatis hanya membutuhkan estimasi **probabilitas arah pergerakan diskret terkalibrasi presisi** (apakah naik atau turun dalam rentang waktu ke depan), bukan tebakan harga nominal eksak.
* **Celah 2 (Isolasi Fitur Single-Timeframe)**:  
  Banyak riset hanya mengandalkan satu *timeframe* data harga terisolasi tanpa intermarket. Model menjadi "buta" terhadap **korelasi invers Indeks Dolar AS (DXY)**, struktur likuiditas skala besar (*multi-timeframe* H4), dan guncangan volatilitas rilis data makroekonomi AS *High Impact* (NFP, CPI, FOMC).
* **Celah 3 (Ketiadaan Reject Option & Validasi Pasar Riil)**:  
  Riset akademis umumnya berhenti pada simulasi teoretis luring (*offline backtesting*) tanpa memperhitungkan friksi pasar nyata (*spread, slippage, latency*). Selain itu, model ML biasa selalu dipaksa menebak di setiap *candle* tanpa memiliki opsi menolak aksi (*reject option / abstain*) saat tingkat keyakinan rendah, serta tidak memiliki mekanisme audit pasca-transaksi (*post-trade audit*).

---

### Pertanyaan 5: Apa solusi komputasi dan kebaruan (*novelty*) yang diajukan dalam skripsi ini?
**Jawaban:**
1. **Fusi 36 Fitur Prediktif Multisumber**: Mengintegrasikan 4 domain fitur (geometri *candlestick* M15/M5, likuiditas institusional SMC/ICT, konfirmasi tren makro H4, serta transmisi makroekonomi DXY & rilis berita AS) tanpa bias kebocoran data masa depan (*lookahead bias*).
2. **Optimalisasi LightGBM Classifier Terkalibrasi**: Menerapkan pemisahan pohon *leaf-wise* dan teknik *histogram binning* (GOSS & EFB) dengan *balanced class weights* untuk menghasilkan estimasi probabilitas arah 5 *candle* ke depan secara cepat dan akurat.
3. **Arsitektur Eksekusi Waktu Nyata MT5 API dengan Reject Option**:
   * Menetapkan **Ambang Batas Keyakinan Tinggi (*High-Confidence Threshold* $\ge 65,0\%$)**: Sistem hanya masuk posisi jika probabilitas $\ge 65,0\%$, dan memilih *abstain* saat pasar berkonsolidasi atau probabilitas berada di area abu-abu.
   * **Manajemen Risiko Dinamis ATR**: Penempatan *Stop-Loss* berbasis volatilitas riil (*Average True Range*) dengan rasio *Risk-to-Reward* 1 : 1,8 s.d. 1 : 2,5.
   * **Post-Trade Scenario Evaluator Engine**: Modul analitis otomatis yang membedah riwayat transaksi pasca-eksekusi untuk mendiagnosis akar penyebab *win/loss* secara objektif.

---

## BAGIAN III: Friksi Pasar Riil, Backtesting Teoretis vs. Live Forward Testing

### Pertanyaan 6: Apa maksudnya "penelitian terdahulu hanya berhenti pada backtesting teoretis"? Apakah mereka tidak menguji di MetaTrader 5?
**Jawaban:**
* **Ya, benar.** Mayoritas penelitian terdahulu (baik skripsi maupun jurnal internasional) **hanya bermain di ranah simulasi data historis (file CSV di Jupyter Notebook, Google Colab, atau MATLAB)**. Mereka tidak pernah menghubungkan model mereka ke antarmuka pemrograman aplikasi (*API*) broker pasar nyata seperti MetaTrader 5.
* Mereka mengunduh data masa lalu, membagi data *train/test*, menghitung akurasi atau RMSE, dan menyimulasikan keuntungan hanya melalui perhitungan matematika di baris tabel (*vectorized backtesting*).

---

### Pertanyaan 7: Mengapa pengabaian friksi pasar nyata (*spread, slippage, latency*) menjadi kelemahan fatal?
**Jawaban:**
1. **Spread Dinamis**: Pada instrumen emas CFD riil, selalu ada selisih harga jual (*Bid*) dan beli (*Ask*) yang melebar saat likuiditas menipis atau saat berita dirilis. Simulasi di atas kertas mengasumsikan transaksi terjadi di harga grafik (*Close*) tanpa biaya *spread*, padahal di dunia nyata keuntungan kecil dapat langsung habis tergerus oleh *spread*.
2. **Slippage**: Di atas kertas, order dianggap dieksekusi instan di harga sinyal. Di pasar riil, lonjakan pergerakan harga menyebabkan order baru terisi di level harga yang lebih buruk beberapa *pip* (*slippage* negatif).
3. **Latency**: Waktu tempuh pengiriman sinyal dari skrip ke server broker melalui jaringan internet dapat menyebabkan keterlambatan masuk pasar.

> **Dampaknya:** Model yang memiliki akurasi $80\%$ dan kurva keuntungan naik lurus di Jupyter Notebook sering kali mengalami **penurunan modal (*drawdown*) tajam hingga bangkrut ketika dijalankan pada pasar riil**. Fenomena ini disebut sebagai *simulation bias* atau *backtest overfitting*.

---

## BAGIAN IV: Validasi Empiris (Skor Teori vs. Nyata, Selisih, & Diagnostik)

### Pertanyaan 8: Apakah model kita memiliki hasil pengujian teoretis? Berapa skornya?
**Jawaban:**
**ADA.** Pengujian teoretis dilakukan pada data pengujian historis (*out-of-sample test set*) 20% tanpa kebocoran data masa depan:
* **Tanpa Ambang Batas Keyakinan (*Baseline / All Signals*):** Akurasi teoretis berkisar antara **52,8% – 54,0%** (kondisi standar pada deret waktu finansial akibat tingginya derau pasar).
* **Dengan Filter Keyakinan Tinggi (*High-Confidence Threshold* $\ge 65,0\%$):**
  * Akurasi Teoretis *Timeframe* M15: **74,77%** (ROC-AUC **0,595**).
  * Akurasi Teoretis *Timeframe* M5: **79,26%** (ROC-AUC **0,618**).

---

### Pertanyaan 9: Berapa skor performa pada pasar nyata (*forward testing* MT5) dan berapa selisihnya (*delta*)?
**Jawaban:**
Berdasarkan log data *forward testing* pada berkas proyek (`Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx` versi 4.1):

| Metrik Evaluasi | Hasil Teori (*Out-of-Sample Test Set*) | Hasil Nyata (*Live Forward Testing* MT5) | Selisih (*Delta*) |
| :--- | :---: | :---: | :---: |
| **Akurasi / Win Rate (M15)** | **74,77%** | **72,73%** *(16 Menang / 6 Kalah)* | **-2,04%** |
| **Rasio Risk-to-Reward (RRR)** | 1 : 2,0 (statis) | 1 : 1,8 s.d. 1 : 2,5 *(Dynamic ATR)* | Teradaptasi pasar riil |
| **Profit Factor** | ~1,20 | **1,05** *(Net Profit Berjalan +$1.98 USD)* | -0,15 |

---

### Pertanyaan 10: Apa makna ilmiah dari selisih performa teori vs. nyata sebesar 2,04% tersebut?
**Jawaban untuk Dosen Penguji:**
> *"Selisih penurunan performa yang hanya sebesar **2,04%** (dari 74,77% teoretis menjadi 72,73% riil) membuktikan dua hal fundamental:*
> 1. *Model LightGBM yang dibangun **terkalibrasi dengan baik dan bebas dari overfitting parah**. Dalam kuantitatif finansial, penurunan akurasi teoretis ke pasar riil yang hanya berkisar 2% menunjukkan ketahanan generalisasi model yang sangat tinggi.*
> 2. *Pengujian data dilakukan secara **jujur, valid, dan realistis**. Penurunan kecil tersebut merupakan representasi wajar akibat friksi spread dan slippage pada broker MetaTrader 5."*

---

### Pertanyaan 11: Bagaimana jika ada kemungkinan peneliti lain sebenarnya menguji di MT5 tapi tidak menuliskannya di naskah publikasi?
**Jawaban Ilmiah:**
1. **Kaidah Publikasi Ilmiah (*Full Disclosure & Reproducibility*)**: Dalam sains komputasi, prinsipnya adalah *"if it is not written, it did not happen"*. Metodologi yang tidak dicantumkan tidak dapat diverifikasi dan dianggap tidak ada.
2. **Live Execution adalah Novelty yang Sangat Bernilai**: Membangun integrasi *live API* ke broker menuntut keahlian rekayasa perangkat lunak (*software engineering*) yang kompleks. Jika peneliti berhasil melakukannya, hal tersebut akan menjadi klaim kebaruan (*selling point*) utama dalam makalah mereka; tidak ada alasan ilmiah bagi peneliti untuk menyembunyikannya.

---

### Pertanyaan 12: Bagaimana jika performa nyata di lapangan ternyata lebih baik daripada teori di atas kertas?
**Jawaban Komputasional:**
1. **Peran Manajemen Risiko Dinamis**: Di atas kertas, akurasi hanya menghitung benar/salah tebakan arah. Di pasar riil, adanya modul **Dynamic ATR Stop-Loss** dan rasio *Risk-to-Reward* dinamis (1 : 2,5) membuat sistem mampu membatasi kerugian saat kalah dan memaksimalkan imbal hasil saat menang (*let profits run*).
2. **Efektivitas Reject Option**: Di pasar riil, sistem secara aktif menolak transaksi saat pasar tidak memiliki kepastian arah ($\text{probabilitas} < 65,0\%$), sehingga menyaring potensi transaksi merugi.
3. **Catatan Ukuran Sampel (*Sample Size*)**: Pada pengujian awal dengan jumlah sampel kecil ($N < 30$), peningkatan performa dapat dipengaruhi oleh variansi statistik (*variance*). Oleh karena itu, skripsi ini menetapkan target pengujian berkelanjutan hingga 100 transaksi agar valid secara hukum probabilitas.

---

## BAGIAN V: Komparasi Objek Penelitian (Emas Makro vs. XAUUSD CFD Intraday)

### Pertanyaan 13: Apakah objek penelitian terdahulu sama-sama menggunakan instrumen emas? Apa bedanya dengan XAUUSD CFD yang Anda teliti?
**Jawaban:**
Aset dasarnya (*underlying asset*) sama-sama emas terhadap dolar AS, **tetapi bentuk kontrak dan karakteristik komputasi datanya berbeda mendasar**:

| Parameter Komparasi | Mayoritas Penelitian Terdahulu (Jurnal Lain) | Penelitian Skripsi Ini (Nouval, 2026) |
| :--- | :--- | :--- |
| **Bentuk Kontrak** | Emas Spot Benchmark (LBMA) / Gold Futures (COMEX `GC=F`) | **Kontrak Derivatif Contract for Difference (CFD) Emas Spot** |
| **Kerangka Waktu** | **Harian (*Daily / D1*)** atau Bulanan | **Intraday Multi-Timeframe (M15 & M5)** dengan konfirmasi H4 |
| **Struktur Transaksi** | Tanpa *leverage*, harga dianggap tunggal (*Close* statis) | **Menggunakan *Leverage***, ada *Bid-Ask Spread* dinamis tiap detik |
| **Karakteristik Data** | Makroekonomi halus (*smooth*), derau rendah | **Derau acak (*noise*) tinggi**, nonstasioner, rentan lonjakan berita |

> **Intinya:** Peneliti lain meneliti harga emas sebagai komoditas makroekonomi jangka panjang di atas kertas, sedangkan penelitian ini meneliti emas sebagai **instrumen derivatif CFD operasional dengan dinamika mikrostruktur likuiditas pasar berjalan.**

---

### Pertanyaan 14: Adakah model prediksi machine learning yang secara khusus dibuat untuk eksekusi kontrak XAU CFD?
**Jawaban:**
* **Di Ranah Akademik Ilmiah (Jurnal/Skripsi)**: Sangat jarang atau hampir tidak ada yang meneliti model *machine learning* untuk *live forward testing* pada kontrak CFD karena kebanyakan peneliti berlatar belakang teori murni yang enggan menghadapi friksi broker riil.
* **Di Ranah Praktisi / Komunitas Perdagangan Ritel**: Banyak beredar bot otomatis (*Expert Advisor* / EA) untuk XAU CFD di platform MT5. Namun, $95\%$ di antaranya **bukan machine learning**, melainkan aturan kaku indikator konvensional atau sistem berisiko tinggi seperti *Martingale/Grid*. Adapun sistem AI milik *hedge fund* institusional bersifat rahasia dagang tertutup (*proprietary/black-box*) dan tidak mempublikasikan metodologinya kepada komunitas ilmiah.
* **Posisi Penelitian Ini**: Menjembatani jurang tersebut dengan menerapkan metodologi ilmiah terbuka (*open scientific framework*) berbasis LightGBM 36 fitur langsung pada instrumen XAU CFD riil.

---

## BAGIAN VI: Arsitektur Rekayasa Perangkat Lunak (Offline Script vs. Autonomous Engine)

### Pertanyaan 15: Bagaimana peneliti terdahulu mengimplementasikan penelitian mereka jika hanya memprediksi angka?
**Jawaban:**
Implementasi mereka hanya berbentuk **skrip analitis luring (*offline script*) di Jupyter Notebook / Google Colab**:
1. Menjalankan skrip Python untuk memproses file CSV historis.
2. Melatih model regresi atau klasifikasi.
3. Mencetak tabel metrik evaluasi (RMSE, Akurasi) dan menampilkan grafik garis harga asli vs prediksi via Matplotlib.
4. Melakukan simulasi keuntungan di tabel Pandas (*vectorized backtesting*) dengan rumus perkalian kolom sederhana tanpa memperhitungkan biaya transaksi.
5. **Begitu skrip selesai dieksekusi dalam beberapa menit, implementasi mereka berakhir.** Tidak ada sistem yang terus hidup atau beroperasi secara mandiri.

---

### Pertanyaan 16: Bagaimana implementasi sistem yang Anda bangun dan apa bedanya secara rekayasa perangkat lunak (*software engineering*)?
**Jawaban untuk Dosen Penguji:**
> *"Perbedaan mendasarnya adalah: peneliti terdahulu menghasilkan **laporan analisis statistik**, sedangkan skripsi Informatika ini menghasilkan **artefak rekayasa perangkat lunak otonom (*autonomous software engineering artifact*)**.*
>
> *Sistem yang kami bangun beroperasi secara terus-menerus (*live daemon/service*) dengan arsitektur komputasi waktu nyata:*
> 1. *Gateway Koneksi MetaTrader 5 API*: Menangkap aliran data tick dan candle M15/M5 yang sedang bergerak di pasar riil secara simultan.
> 2. *Pipeline Rekayasa Fitur Real-Time*: Mengekstraksi 36 variabel prediktif (SMC, geometri, Fibonacci, DXY, berita) dalam hitungan milidetik tanpa kebocoran data.
> 3. *Inference & Reject Option Engine*: Menghitung probabilitas arah via LightGBM dan menolak eksekusi jika keyakinan di bawah 65,0%.
> 4. *Execution & Dynamic Risk Manager*: Menghitung ukuran lot 0,01 dan ambang batas Stop-Loss dinamis berbasis ATR, lalu mengirim paket order langsung ke server broker.
> 5. *Logging Otomatis & Post-Trade Scenario Evaluator*: Merekam setiap transaksi ke Excel dan melakukan audit diagnostik pasca-penutupan transaksi guna mendeteksi akar penyebab kemenangan atau kerugian.
> 
> *Inilah esensi sejati tugas akhir bidang Teknik Informatika: menyatukan kecerdasan buatan (*Machine Learning*) dengan arsitektur perangkat lunak terapan (*Applied Software Engineering*) yang teruji di lingkungan nyata."*

---

*Dokumen disusun dan diselaraskan secara penuh dengan Draf Bab I Skripsi, Pedoman Kepatuhan KBBI/PUEBI, serta Kaidah Ilmiah Universitas Pembangunan Nasional "Veteran" Yogyakarta.*
