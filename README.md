# Skripsi Informatika: Forecasting XAUUSD & Algorithmic Trading Bot Menggunakan LightGBM dan Smart Money Concepts (SMC/ICT)

Repositori ini berisi seluruh kode sumber (*source code*), model kecerdasan buatan (*trained models*), data pelaporan *forward testing*, serta dokumen proposal/tugas akhir untuk penelitian:
> **"Penerapan Model LightGBM Berbasis Smart Money Concepts (SMC/ICT) dan Analisis Multi-Timeframe untuk Peramalan Arah Pergerakan Harga Emas (XAU/USD)"**

---

## 📌 Gambaran Umum Sistem

Proyek ini mengintegrasikan **Machine Learning (LightGBM)** dengan konsep likuiditas institusional **Smart Money Concepts (SMC/ICT)**, Fibonacci Optimal Trade Entry (OTE), serta korelasi indeks Dolar AS (DXY) secara *real-time* dengan eksekusi 0-delay ke terminal **MetaTrader 5 (Exness)**.

Sistem terdiri dari dua arsitektur bot yang berjalan secara independen dan paralel:

1. **Bot 1: M15 Konservatif (Swing / Intraday)**
   - **File:** `Eksekusi_Otomatis_Trading_Bot.py`
   - **Model:** `model_lightgbm_xauusd.pkl`
   - **Ambang Batas Keyakinan:** $\ge 60.0\%$
   - **Filter Tren:** EMA 50 H1 (Makro)
   - **Manajemen Posisi:** *Single Position* (Maks. 1 posisi aktif)
   - **Auto Break-Even:** Aktif pada floating profit $\ge +$4.00 USD
   - **Log Rekap Excel:** `Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx`
   - **Magic Number:** `123230`

2. **Bot 2: M5 Full Dynamic Scalper (Fast Aggressive Scalping)**
   - **File:** `Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py`
   - **Model:** `model_lightgbm_xauusd_m5.pkl`
   - **Ambang Batas Keyakinan:** $\ge 58.0\%$ (Pullback Scalp: $\ge 70.0\%$)
   - **Filter Tren:** EMA 50 M30 (Lokal Responsif)
   - **Manajemen Exit:** *Bot-Managed Dynamic Exit* (Quick Scalp TP +$1.50 USD, Trailing Lock, & AI Early Cut-Loss)
   - **Manajemen Posisi:** *Safe Pyramiding Stacking* (Maks. 3 layer, hanya jika posisi sebelumnya sudah profit)
   - **Log Rekap Excel:** `Laporan_Forward_Testing_Model_M5_Scalping.xlsx`
   - **Magic Number:** `123235`

---

## 🧠 Fitur Rekayasa Fitur (28 Fitur SMC/ICT & Indikator)

1. **Struktur Candle:** `Body_M15`, `Lower_Wick_M15`, `Upper_Wick_M15`
2. **Likuiditas & Ketidakseimbangan:** `FVG_Bull`, `FVG_Bear`, `Liquidity_Sweep_High`, `Liquidity_Sweep_Low`
3. **Struktur Pasar:** `BOS_Bull`, `BOS_Bear`, `CHoCH_Bull`, `CHoCH_Bear`, `Order_Block_Bull`
4. **Jarak Support / Resistance:** `Dist_Support`, `Dist_Resistance`
5. **Fibonacci OTE:** `Fibo_Pos_100`, `Fibo_Dist_382`, `Fibo_Dist_500`, `Fibo_Dist_618`
6. **Momentum & Volatilitas:** `RSI_M15`, `BB_Bandwidth`, `BB_Pos`
7. **Return Momentum:** `XAU_Return_1`, `XAU_Return_3`, `XAU_Return_5`
8. **Korelasi Makro:** `DXY_Return_1`, `DXY_Return_3`
9. **Multi-Timeframe Macro:** `Trend_H1_Bull`, `Trend_H1_Strong`

---

## 📂 Struktur Repositori

```text
├── Buka_Aplikasi_Trading_Bot.bat                  # [UTAMA] Launcher Desktop GUI Dashboard satu-klik
├── Trading_Bot_GUI_App.py                         # Aplikasi Desktop GUI Dashboard (M15, M5, Excel Viewer)
├── Eksekusi_Otomatis_Trading_Bot.py               # Bot trading otomatis M15 (SMC & Multi-Zone Swing)
├── Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py   # Bot trading otomatis M5 Scalper (Technical Confluence)
├── Macro_Economic_News_Engine.py                  # Engine kalender berita makroekonomi real-time (CPI, PPI, NFP, FOMC)
├── Auto_Logger_Forward_Testing.py                 # Engine sinkronisasi trade MT5 ke Excel
├── train_model_lightgbm_m5.py                     # Script pelatihan model M5
├── jalankan_perbandingan_model_skripsi.py         # Benchmark Bab 4 (LightGBM vs XGBoost vs RF)
├── jalankan_kedua_bot_paralel.bat                 # Launcher konsol ganda otomatis (.bat)
├── jalankan_kedua_bot_paralel.py                  # Launcher konsol ganda Python (.py)
├── setup_auto_start.bat                           # Skrip konfigurasi auto-start bot saat PC menyala
├── hapus_auto_start.bat                           # Skrip penghapus auto-start bot
├── model_lightgbm_xauusd.pkl                      # Master Model LightGBM (Timeframe M15)
├── model_lightgbm_xauusd_m5.pkl                   # Master Model LightGBM (Timeframe M5)
├── Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx # Rekap forward testing bot M15
├── Laporan_Forward_Testing_Model_M5_Scalping.xlsx # Rekap forward testing bot M5
├── Hasil_Perbandingan_Model_Bab4.xlsx             # Data hasil uji komparasi Bab 4
├── PTA_Nouval_FIX.docx                            # Proposal Tugas Akhir (Word)
├── PTA_Nouval_FIX.pdf                             # Proposal Tugas Akhir (PDF Siap Cetak)
└── README.md                                      # Dokumentasi repositori
```

---

## 🚀 Cara Menjalankan

### 1. Prasyarat Sistem
- Python 3.10+ (disarankan Python 3.11 s/d 3.13)
- MetaTrader 5 (Exness Terminal) terinstall dan terhubung ke akun aktif
- Izinkan opsi **"Allow Algo Trading"** pada terminal MetaTrader 5

### 2. Instalasi Dependensi
```bash
pip install -r requirements.txt
# atau
pip install MetaTrader5 lightgbm scikit-learn pandas numpy openpyxl yfinance psutil
```

### 3. Menjalankan Aplikasi (Metode Rekomendasi: GUI Dashboard)
Cukup klik ganda (*double click*) file utama:
```cmd
Buka_Aplikasi_Trading_Bot.bat
```
Atau via terminal:
```bash
python Trading_Bot_GUI_App.py
```
Aplikasi GUI Dashboard akan terbuka dengan fitur:
- Kontrol independen untuk Bot M15 dan Bot M5 (Tombol Mulai / Hentikan).
- Stopwatch durasi bot, Donut Chart probabilitas real-time, dan Riwayat Keputusan live.
- *In-App Excel Data Viewer* untuk memeriksa dan memfilter riwayat transaksi M15, M5, serta statistik perbandingan tanpa perlu menutup bot.

### 4. Alternatif: Menjalankan via Konsol CLI
Jika ingin menjalankan lewat konsol terminal tanpa GUI:
```cmd
jalankan_kedua_bot_paralel.bat
```

---

## 📊 Hasil Evaluasi Forward Testing

Hasil pengujian langsung (*forward testing*) pada akun riil Exness:
- **Bot M15 Konservatif:** Win Rate **75.0%**, Profit Factor **5.58**, Net Profit Positif.
- **Bot M5 Dynamic Scalper:** Win Rate **50%–60%**, Net Profit Positif dengan RRR 1:1.5 dan Dynamic Scalp TP +$1.50 USD.
- Log transaksi terbarui secara otomatis pada file Excel masing-masing setiap kali candle ditutup.
