# PANDUAN STRUKTUR DIREKTORI & INDEKS REPOSITORI SKRIPSI INFORMATIKA

**Peneliti**: Nouval Ditya Maheswara (NIM: 123230165)  
**Jurusan / Fakultas**: Informatika / Fakultas Teknik Industri, UPN "Veteran" Yogyakarta  
**Judul Skripsi**:  
> *"Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi"*

---

## 📌 GAMBARAN UMUM STRUKTUR DIREKTORI (SETELAH DIRAPIKAN)

Untuk menjaga performa kerja, kerapihan dokumentasi akademik, serta mencegah penumpukan file pengujian (yang mencapai 200+ file), repositori ini telah ditata ke dalam 4 folder kategori utama yang rapi, modular, dan terisolasi:

```text
d:\SKRIPSI INFORMATIKA\
│
├── 📂 01_DOKUMEN_SKRIPSI/                 # Seluruh Naskah, Proposal, Draft Word/PDF & Rangkuman Markdown
│   ├── 📂 Naskah_Draf_Utama/             # Berkas resmi Word & PDF Bab 1 terkini, Buku Panduan, & Tabel Jurnal
│   ├── 📂 Arsip_Revisi_Lama/             # Rekam jejak revisi naskah terdahulu (v1, v2, v3, backup)
│   └── 📂 Panduan_Dan_Catatan_Markdown/  # Pedoman sidang, rangkuman audit ilmiah, dan kerangka kerja
│
├── 📂 02_RISET_DAN_AUDIT_MODEL/           # Forensik Kebocoran (Leakage), Skrip Benchmark & Eksperimen
│   ├── 📂 Diskusi_Audit_Ahli_A_vs_Peneliti_B/ # Dokumen telaah kritis metodologi Ahli A vs Peneliti B (Putaran 1–3)
│   ├── 📂 Skrip_Audit_Dan_Benchmark/      # Skrip pengujian resmi konsensus (57 Fitur, komparasi horizon kausal)
│   └── 📂 Eksperimen_Scratch_Scripts/     # 50+ skrip scratch pengujian, evaluasi, dan plotting historis
│       └── 📂 Temp_Dump_Files/           # Berkas teks temporary & dump ekstraksi
│
├── 📂 03_DATA_DAN_HASIL_EVALUASI/         # Seluruh Laporan Kinerja Excel (.xlsx) & CSV
│   ├── 📂 Hasil_Eksperimen_Excel/         # Excel komparasi model, grid search RRR, horizon test, dan feature importance
│   └── 📂 Arsip_Backup_Forward_Testing/  # Cadangan berkas forward testing dan evaluasi skenario lama
│
├── 📂 04_ARSIP_MODEL_DAN_NOTEBOOK/        # Model Cadangan (.pkl), Notebook Lama, & Skrip Training
│   └── 📂 Backup_Model_Dan_Notebook/     # Cadangan model v3.7, notebook v3/v4, serta skrip latih terisolasi
│
├── 📂 ARTIKEL/                            # Naskah Terjemahan & Bedah Kritis Paper Referensi (arXiv, SINTA, Scopus)
├── 📂 PRA TA/                             # Berkas Berita Acara, Lembar Konsultasi, & Proposal Awal Pra-TA
│
└── 🚀 [AREA SISTEM PRODUKSI & RUNTIME BOT AKTIF DI ROOT]
    ├── JALANKAN_BOT_ANTI_ERROR_24JAM.bat  # Launcher utama pengawas bot otonom (Supervisor)
    ├── Buka_Aplikasi_Trading_Bot.bat      # Launcher aplikasi dashboard desktop
    ├── Buka_Link_Web_HP.bat               # Launcher pemantauan via smartphone (Cloudflare)
    ├── Supervisor_Trading_Bot.py          # Watchdog & auto-restart bot 24 jam
    ├── Eksekusi_Otomatis_Trading_Bot.py   # Bot produksi M15 (Smart Money Concepts)
    ├── Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py # Bot produksi M5 (Scalper)
    ├── Web_Dashboard_Server.py            # Server monitoring web port 5000
    ├── Desktop_App_Modern.py              # GUI antarmuka desktop modern
    ├── Trading_Bot_GUI_App.py             # GUI cadangan
    ├── model_lightgbm_xauusd.pkl          # Model aktif produksi M15 (57 Fitur v5.0)
    ├── model_lightgbm_xauusd_m5.pkl       # Model aktif produksi M5
    ├── Uji_Coba_LightGBM_XAUUSD.ipynb     # Jupyter Notebook Utama
    ├── Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx # Rekap log riil bot M15 aktif
    ├── Laporan_Forward_Testing_Model_M5_Scalping.xlsx # Rekap log riil bot M5 aktif
    └── Evaluasi_Skenario_Trade.xlsx       # Database evaluasi multi-skenario
```

---

## 📂 RINCIAN LENGKAP ISI TIAP FOLDER

### 1. `01_DOKUMEN_SKRIPSI/`
Menyimpan seluruh dokumen karya tulis ilmiah yang siap digunakan untuk bimbingan dan sidang:
* **`Naskah_Draf_Utama/`**:
  * [`DRAF_BAB_1_SKRIPSI_NOUVAL_TERBARU_STANDAR_UPNVY.docx`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Naskah_Draf_Utama/DRAF_BAB_1_SKRIPSI_NOUVAL_TERBARU_STANDAR_UPNVY.docx) — Naskah Bab 1 terbaru berstandar UPNVY.
  * [`DRAF_BAB_1_SKRIPSI_REVISI_FINAL V4.pdf`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Naskah_Draf_Utama/DRAF_BAB_1_SKRIPSI_REVISI_FINAL%20V4.pdf) — Naskah Bab 1 siap cetak.
  * [`BUKU_PANDUAN_INSIGHT_DAN_DEFENSE_SKRIPSI_NOUVAL.docx`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Naskah_Draf_Utama/BUKU_PANDUAN_INSIGHT_DAN_DEFENSE_SKRIPSI_NOUVAL.docx) — Panduan argumentasi sidang.
  * [`TABEL_PENELITIAN_TERDAHULU_BAB_2.docx`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Naskah_Draf_Utama/TABEL_PENELITIAN_TERDAHULU_BAB_2.docx) — Matriks komparasi riset terdahulu.
* **`Panduan_Dan_Catatan_Markdown/`**:
  * [`TEMUAN_AUDIT_PNL_LEAKAGE_DAN_STRATEGI_EXIT_REALISTIS.md`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Panduan_Dan_Catatan_Markdown/TEMUAN_AUDIT_PNL_LEAKAGE_DAN_STRATEGI_EXIT_REALISTIS.md) — Temuan penting audit kebocoran data dan pemenang riil TP $12/SL $6.
  * [`RANGKUMAN_LENGKAP_AUDIT_DAN_STRATEGI_SKRIPSI.md`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Panduan_Dan_Catatan_Markdown/RANGKUMAN_LENGKAP_AUDIT_DAN_STRATEGI_SKRIPSI.md) — Rangkuman menyeluruh evolusi model dari v1.0 s/d v5.0.
  * [`RANGKUMAN_TANYA_JAWAB_METODOLOGI_DAN_SIDANG_SKRIPSI.md`](file:///d:/SKRIPSI%20INFORMATIKA/01_DOKUMEN_SKRIPSI/Panduan_Dan_Catatan_Markdown/RANGKUMAN_TANYA_JAWAB_METODOLOGI_DAN_SIDANG_SKRIPSI.md) — Bank tanya-jawab penguji.

---

### 2. `02_RISET_DAN_AUDIT_MODEL/`
Menyimpan seluruh bukti empiris investigasi kebocoran data dan pembuktian sains finansial:
* **`Diskusi_Audit_Ahli_A_vs_Peneliti_B/`**:
  * Berkas notula dialektika akademik putaran 1, 2, dan 3 yang membongkar jebakan *lookahead bias* dan melahirkan konsensus 57 Fitur.
* **`Skrip_Audit_Dan_Benchmark/`**:
  * Skrip Python resmi pengujian model: `audit_resmi_komparasi_horizon_bebas_leakage.py`, `benchmark_all_4_models_57_features.py`, `jalankan_perbandingan_model_skripsi.py`, dll.
* **`Eksperimen_Scratch_Scripts/`**:
  * Lebih dari 50 skrip `scratch_*.py` yang digunakan selama eksperimen iteratif (misal evaluasi BEP, kalibrasi ambang batas probabilitas, analisis gap harga, dan diagnostik latensi).

---

### 3. `03_DATA_DAN_HASIL_EVALUASI/`
Menyimpan seluruh rekaman data tabular (Excel dan CSV):
* **`Hasil_Eksperimen_Excel/`**:
  * Berkas Excel penting: `Hasil_Komparasi_4_Model_57_Fitur_Adaptive_Sniper.xlsx`, `Hasil_Simulasi_Profit_Horizon_2_3_5.xlsx`, `Hasil_Uji_Bersih_Adaptive_Sniper_vs_AutoClose.xlsx`, `Feature_Importance_57_Fitur.xlsx`, dll.
* **`Arsip_Backup_Forward_Testing/`**:
  * Berkas cadangan transaksi MT5 sebelum reset saldo modal $500, arsip 46 trade, arsip 99 trade, dan checkpoint versi terdahulu.

---

### 4. `04_ARSIP_MODEL_DAN_NOTEBOOK/`
Menyimpan arsip versi terdahulu agar tidak membingungkan sistem produksi:
* Cadangan model machine learning: `model_lightgbm_xauusd_v37_backup.pkl`, `model_lightgbm_xauusd_m5_v37_backup.pkl`.
* Cadangan notebook riset: `Uji_Coba_LightGBM_XAUUSD_Backup_Sebelum_V3.ipynb` dan `V4.ipynb`.
* Skrip pelatihan model terdahulu.

---

## 🛡️ JAMINAN INTEGRITAS SISTEM PRODUKSI

1. **Jalur Peluncur (.bat / .vbs) Tetap 100% Berfungsi Normal**:  
   Semua file peluncur utama (`JALANKAN_BOT_ANTI_ERROR_24JAM.bat`, `Buka_Aplikasi_Trading_Bot.bat`, dll.) tetap berada di root folder dan memanggil skrip bot yang aktif di root, sehingga tidak ada jalur eksekusi yang terputus.
2. **Database Transaksi Aktif Tetap Sinkron**:  
   Bot eksekusi MT5 dan web monitoring dashboard tetap membaca dan menulis ke berkas aktif di root:  
   * `Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx`
   * `Laporan_Forward_Testing_Model_M5_Scalping.xlsx`
   * `Evaluasi_Skenario_Trade.xlsx`
3. **Penyelamatan 150+ File**:  
   Root folder kini menjadi sangat bersih, ringan, dan profesional (dari 212 file menjadi ~35 file aktif terawat), sehingga memudahkan navigasi bagi Anda dan dosen pembimbing.
