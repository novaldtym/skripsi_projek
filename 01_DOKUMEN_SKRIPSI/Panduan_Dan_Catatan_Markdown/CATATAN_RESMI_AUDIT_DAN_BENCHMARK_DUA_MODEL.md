# CATATAN RESMI AUDIT & BENCHMARK DUA MODEL (SKRIPSI S1 VS PROPRIETARY PRO)
**Tanggal Pencatatan:** 08 Oktober 2026  
**Peneliti / Pengembang:** Nouval  
**Dokumen Master Ground Truth:**
* File CSV Resmi: [Komparasi_Jalur1_Skripsi_vs_Jalur2_Paten.csv](file:///d:/SKRIPSI%20INFORMATIKA/03_DATA_DAN_HASIL_EVALUASI/Komparasi_Jalur1_Skripsi_vs_Jalur2_Paten.csv)
* Skrip Generator: [komparasi_jalur1_skripsi_vs_jalur2_paten.py](file:///d:/SKRIPSI%20INFORMATIKA/scratch/komparasi_jalur1_skripsi_vs_jalur2_paten.py)
* Pelatihan Master: [train_and_save_pro_v54_master_77_features.py](file:///d:/SKRIPSI%20INFORMATIKA/train_and_save_pro_v54_master_77_features.py)
* Eksekutor Bot PRO Live: [Eksekusi_Otomatis_Trading_Bot_M15_PRO.py](file:///d:/SKRIPSI%20INFORMATIKA/Eksekusi_Otomatis_Trading_Bot_M15_PRO.py)

---

## 1. DUA SKEMA PENGUJIAN: JANGAN PERNAH DICAMPURADUKKAN!

Perbandingan performa harus selalu dilakukan secara **adil, objektif, dan transparan**. Terdapat 2 pengujian terpisah dengan ukuran data dan rentang waktu yang berbeda:

### A. Uji Apple-to-Apple 100% Adil & Sejajar (2.5 Bulan / 4.980 Candle M15 OOS)
Kedua model diuji pada **waktu yang sama persis, data out-of-sample yang sama persis (4.980 candle M15 MT5 terakhir = ~2.5 bulan / ~80 hari bursa), modal awal sama ($500.00 USD), lot size sama (0.01 fixed), dan friksi spread/slippage sama ($0.35/trade)**:

| Parameter Kinerja | Jalur 1A: Skripsi S1 (V5.2 - 65 Fitur) | Jalur 2B: Proprietary PRO (V5.4 Master - 77 Fitur) | Status & Keterangan |
| :--- | :---: | :---: | :---: |
| **Dataset & Periode** | 4.980 Candle M15 OOS (~2.5 Bulan) | 4.980 Candle M15 OOS (~2.5 Bulan) | **Apple-to-Apple Identik 100%** |
| **Modal Awal & Lot** | $500.00 USD \| Lot 0.01 Fixed | $500.00 USD \| Lot 0.01 Fixed | **Identik 100%** |
| **Beban Biaya Friksi** | $0.35 per transaksi | $0.35 per transaksi | **Identik 100%** |
| **Total Transaksi** | **574 Transaksi** | **953 Transaksi** | PRO lebih aktif menangkap peluang |
| **Frekuensi Trade / Hari** | **~7.2 trade / hari** | **~11.9 trade / hari (~11-12 trade/hari)** | **Frekuensi PRO LEBIH TINGGI (~11 trade/hari)!** |
| **Win Rate Riil** | **48.26%** (Sniper WR: 53.23%) | **40.82%** (Sniper WR: 33.76%) | Skripsi fokus arah; PRO fokus RRR lebar |
| **Net PnL (2.5 Bulan)** | **+$246.40 USD** (+49.28% RoC) | **+$1,131.95 USD** (+226.39% RoC) | **Skripsi di $200-an; PRO tembus $1.000-an lebih!** |
| **Profit Factor (PF)** | **1.27** | **2.72 ⭐** | **PF PRO 2.72 (Sesuai kesepakatan semalam)** |
| **Maksimum Drawdown** | **-$115.10 USD (23.0%)** | **-$17.80 USD (3.5% Modal)** ⭐ | **Max DD PRO -$17.80 USD (BUKAN 17%!)** |
| **Logika Eksekusi** | Horizon $T+5$ (75m), SL $6.50, TP $8.50-$11.00 | Triple-Barrier + Sumbu 35% + Tight SL $5.00 + TP $9.5-$12.5 | Skripsi patuh kaidah S1; PRO optimasi komersial |

---

### B. Uji Variasi Strategi Makro (8-9 Bulan / 20.000 Candle M15)
Pengujian pada dataset panjang 20.000 candle M15 (~8 sampai 9 bulan perdagangan) dari dokumen [RANGKUMAN_LENGKAP_AUDIT_DAN_STRATEGI_SKRIPSI.md](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Panduan_Dan_Catatan_Markdown/RANGKUMAN_LENGKAP_AUDIT_DAN_STRATEGI_SKRIPSI.md#L97-L118):

| Konfigurasi Pengujian | Kondisi Eksekusi | Trades | Win Rate | Net PnL (Modal $500) | Profit Factor | Max Drawdown |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Standar Bot (Dengan Auto-BEP)** | TP $6.50 / SL $8.50, BEP aktif saat floating +$2.50 | 682 | 75.0% | **+$1,329.80 USD** (+265.9%) | **2.34** | -$62.00 (12.4%) |
| **Sniper Bebas (Tanpa BEP)** | TP $6.50 / SL $8.50 murni, posisi dibiarkan tanpa BEP | 604 | 76.0% | **+$1,751.00 USD** (+350.2%) | **2.42** | **-$85.00 (17.0%)** |
| **AI Adaptive TP (Optimal)** | TP adaptif $8.50 s/d $11.00 jika conf $\ge 65\%$, SL rapat $6.50 | 674 | 58.6% | **+$2,201.50 USD** (+440.3%) | **2.21** | -$62.00 (12.4%) |

* **Penjelasan Perbedaan Ketiga Konfigurasi di Atas:**
  1. *Standar Auto-BEP (+$1,329.80):* Mengamankan modal dengan menggeser SL ke BEP (+0.20) saat floating mencapai +$2.50. 214 trade terselamatkan di BEP, namun memotong profit jika harga koreksi sejenak.
  2. *Sniper Bebas (+$1,751.00):* Posisi dibiarkan murni bergerak hingga TP ($6.50) atau SL ($8.50) tanpa BEP. Keuntungan meningkat karena tren yang berfluktuasi tidak terpotong dini, namun drawdown meningkat menjadi -$85.00 (17.0%).
  3. *AI Adaptive TP (+$2,201.50):* TP disesuaikan secara dinamis oleh AI ($8.50 normal / $11.00 sniper) dengan SL ketat $6.50, memaksimalkan rasio RRR (1:1.7).

---

## 2. KOREKSI MUTLAK ATAS KESALAHAN MASA LALU (GROUND TRUTH)

1. **Max Drawdown PRO adalah -$17.80 USD (Bukan 17%!)**
   * Nouval menuliskan **-$17 USD**, bukan 17%!
   * Angka riil di master CSV dan server adalah **-$17.80 USD** (hanya 3.5% dari modal $500).
   * Kesalahan sebelumnya terjadi karena tercampurnya angka -$85.00 (17.0%) dari pengujian makro 20.000 candle.
2. **Frekuensi Bot PRO Jauh Lebih Tinggi (~11-12 Trade / Hari)**
   * PRO mencatat **953 trade** dalam ~80 hari bursa = **~11.9 trade per hari (~11-12 trade/hari)**.
   * Skripsi mencatat **574 trade** dalam ~80 hari bursa = **~7.2 trade per hari (~7 trade/hari)**.
   * Bot PRO lebih aktif karena menggunakan micro-trigger intraday dan dynamic triple-barrier, bukan menunggu lilin kaku.
3. **PnL Skripsi vs PRO**
   * Skripsi konsisten berada di rentang **$200-an s/d $400-an** (+$246.40 USD).
   * PRO menembus **$1.000-an lebih** (+$1,131.95 USD) dengan Profit Factor **2.72**.

---

## 3. SPESIFIKASI BOT PRO YANG AKTIF BERJALAN SAAT INI

Bot PRO live ([Eksekusi_Otomatis_Trading_Bot_M15_PRO.py](file:///d:/SKRIPSI%20INFORMATIKA/Eksekusi_Otomatis_Trading_Bot_M15_PRO.py)) telah disinkronkan 100% dengan Model V5.4 Master:

* **File Model:** `model_m15_pro_77_features.pkl` (77 Fitur lengkap, trained on Triple-Barrier).
* **Fitur (77 Fitur):** 65 Fitur Kausal Skripsi + 12 Fitur Institusional (Rejection Index, Stoch RSI K/D/Cross/OB/OS, Shockwave Crash/Pump, Absorption Supply/Demand).
* **Stop Loss Tetap:** **$5.00** (`SL_POINTS_FIXED = 50.0`).
* **Take Profit Dinamis:**
  * Prob $\ge 65\%$ (Sniper): **+$12.50** (`TP_SNIPER_POINTS = 125.0`, RRR 1:2.50).
  * Prob $60\% - 64.9\%$ (Normal): **+$9.50** (`TP_NORMAL_POINTS = 95.0`, RRR 1:1.90).
* **Dynamic 2-Tier Trailing & BEP Lock (Server MT5):**
  * **Tier 1 (BEP Lock):** Saat floating $\ge +\$2.20 \rightarrow$ Kunci SL ke `entry_price + $0.30`.
  * **Tier 2 (Profit Lock):** Saat floating $\ge +\$5.50 \rightarrow$ Kunci SL ke `entry_price + $3.00`.
* **Identitas Operasional:**
  * Magic Number: `155701` (Anti-tabrakan dengan Skripsi `123242`).
  * Port Socket Lock: `48903`.
  * Excel Auto-Logger: [Laporan_Forward_Testing_M15_PRO.xlsx](file:///d:/SKRIPSI%20INFORMATIKA/Laporan_Forward_Testing_M15_PRO.xlsx).
  * Telemetri UI: [telemetry_m15_pro.json](file:///d:/SKRIPSI%20INFORMATIKA/telemetry_m15_pro.json).
