# Analisis & Rangkuman Hasil Pengujian Strategi ICT Gap
**Sumber:** Kanal YouTube *Smart Risk*  
**Judul Video:** *I Tested Every ICT Gap Strategy So You Don't Have To*  
**Aset & Periode Pengujian:** EUR/USD (Timeframe H1) | Periode 3 Bulan (Juni – Agustus 2026)  
**Modal Awal & Risiko:** $1.000 (Risiko 3% per trade | Target Fixed RR 1:2)

---

## 1. Definisi 3 Tipe Gap ICT yang Diuji

| Tipe Gap | Karakteristik Pembentukan | Karakteristik Perilaku |
| :--- | :--- | :--- |
| **Fair Value Gap (FVG)** | Terbentuk dari formasi 3 lilin (*3-candle sequence*) di mana terdapat celah (*gap*) harga antara sumbu lilin ke-1 dan sumbu lilin ke-3. | Menandakan ketidakseimbangan agresif antara *supply* dan *demand*. Harga diharapkan bereaksi saat kembali mengisi (*rebalance*) zona ini. |
| **Breakaway Gap (BAG)** | Varian FVG dengan momentum lebih masif, di mana **lilin ke-3 ditutup (*close body*) melampaui titik ekstrem lilin ke-2**. | Menunjukkan dorongan tren yang jauh lebih kuat; potensi *risk-to-reward* sering kali lebih besar. |
| **Inversion Gap (IFVG)** | FVG atau Breakaway Gap yang **gagal menahan harga** (ditembus secara langsung). | Membalik fungsi zona: *bullish gap* yang jebol berubah menjadi zona penawaran (*supply / resistance*) karena pihak pembeli telah kehilangan kendali pasar. |

---

## 2. Metodologi Standarisasi Objektif (Filter ATR)

Untuk menghilangkan unsur subjektivitas trader ("gap terlalu besar" atau "terlalu kecil"), pengujian menggunakan acuan indikator **ATR (*Average True Range* - periode 14)**:

* **Filter Validitas Ukuran Gap:**
  * Abaikan gap jika ukurannya $< \frac{1}{3} \times \text{ATR}$ (terlalu kecil/tidak signifikan).
  * Abaikan gap jika ukurannya $> 2 \times \text{ATR}$ (terlalu lebar/tidak realistis menjaga RR).
* **Aturan Penempatan Posisi & Risiko:**
  * **Entry:** Di batas awal gap (*boundary*). Khusus gap berukuran relatif besar, entry diletakkan di titik tengah gap (*consequent encroachment / 50%*).
  * **Stop Loss (SL):** Diletakkan sejauh **$0.5 \times \text{ATR}$** di luar batas zona gap.
  * **Take Profit (TP):** Target rasio tetap **1:2 Risk to Reward (RR)**.
  * **Prosedur Pengujian:** Menggunakan fitur *Replay Mode* TradingView tanpa melihat lilin di masa depan.

---

## 3. Data Hasil Pengujian

### Tahap 1: Eksekusi Mentah Tanpa Filter Arah Tren (*Raw Gaps*)
Semua gap yang lolos filter ukuran ATR dieksekusi langsung tanpa mempertimbangkan tren atau struktur market.

| Strategi Gap | Total Trade | Menang / Kalah | Win Rate | Saldo Akhir | PnL Bersih | Max Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fair Value Gap (FVG)** | 29 | 9 Win / 20 Loss | **31,0%** | $940 | **-$60 (-6%)** | 18% ($820) |
| **Breakaway Gap (BAG)** | 45 | 14 Win / 31 Loss | **31,1%** | $910 | **-$90 (-9%)** | 18% ($820) |
| **Inversion Gap (IFVG)** | 27 | 9 Win / 18 Loss | **33,3%** | $1.000 | **$0 (0% / BEP)** | 6% ($940) |

> **Evaluasi Tahap 1:** Menembak setiap sinyal gap secara "buta" tidak menghasilkan keuntungan (*unprofitable*). Jika hasil ini dikurangi beban *spread* dan komisi broker, performa akun akan jauh lebih buruk.

---

### Tahap 2: Eksekusi Berbasis Filter Struktur & Arah Tren (*Market Direction*)
Setup hanya diambil jika searah dengan struktur tren yang dominan.

* **Aturan Filter Tren:**
  * **Uptrend:** Harga konsisten membentuk *Higher Highs* dan menjaga *Higher Lows* (*Protected Lows*). Hanya ambil posisi **Buy**.
  * **Downtrend:** Harga konsisten membentuk *Lower Lows* dan menjaga *Protected Highs*. Hanya ambil posisi **Sell**.
* **Filter Sinyal Pelemahan / Pembalikan Arah:**
  * *Failure to make a new high/low:* Kegagalan mencetak titik ekstrem baru yang diikuti penembusan struktur (*Change of Character / CHoCH*).
  * *Change in State of Delivery (CISD):* Perubahan momentum lilin secara mendadak berlawanan arah yang meninggalkan FVG baru.

*Catatan: Pada tahap kedua, setup FVG dan Breakaway Gap digabungkan menjadi satu kategori karena karakteristik statistik keduanya pada pengujian awal identik.*

| Strategi (+ Filter Tren) | Total Trade | Menang / Kalah | Win Rate | Saldo Akhir | PnL Bersih | Max Drawdown |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Combined (FVG + Breakaway)** | 29 | 14 Win / 15 Loss | **48,3%** | $1.390 | **+$390 (+39%)** | 9% ($90) |
| **Inversion Gap (IFVG)** | 12 | 6 Win / 6 Loss | **50,0%** | $1.180 | **+$180 (+18%)** | 6% ($60) |

---

## 4. Kesimpulan Kunci Analisis

1. **Struktur Pasar Adalah Filter Utama:** Celah harga (*gaps*) bukanlah strategi tunggal yang bisa berdiri sendiri. Menyelaraskan entri dengan struktur tren terbukti mampu membalikkan hasil dari rugi (-6% s.d. -9%) menjadi profit (+18% s.d. +39%).
2. **Kekuatan Risk-to-Reward Ratio (1:2):** Meskipun *win rate* berada di bawah atau setara 50%, akun tetap mampu bertumbuh secara signifikan karena nilai keuntungan per trade menang dua kali lipat dibanding nilai kerugian per trade kalah.
3. **Karakteristik Inversion Gap:** Menghasilkan tingkat ketahanan modal paling stabil dengan *drawdown* terkecil (hanya 6%), namun frekuensi kemunculannya paling jarang dibanding FVG reguler.
4. **Pentingnya Standarisasi ATR:** Mengukur toleransi batas lebar gap dan jarak penempatan Stop Loss menggunakan kelipatan ATR efektif mengeliminasi keraguan mental dan ketidakkonsistenan saat eksekusi live.