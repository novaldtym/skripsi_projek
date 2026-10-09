# Teori Belajar ICT (Inner Circle Trader) - Pipsikologi

Kompilasi rangkuman dan analisis materi pembelajaran metode ICT berdasarkan seri video kanal YouTube **Pipsikologi**, disusun secara utuh, sistematis, dan tanpa penambahan maupun pengurangan konteks materi aslinya.

---

## Bagian 1: Panduan Memilih FVG dengan Probabilitas Tinggi (High Probability FVG)

### 1. Tujuan dan Konteks Analisis
Tujuan utama materi ini adalah memfilter banyaknya *Fair Value Gap* (FVG) yang muncul di chart agar trader tidak asal memilih area untuk entry.
* **Pendekatan Multi-Time Frame (2 Time Frame):**
  * **HTF (*Higher Time Frame*):** Menggunakan time frame **Daily (D1)** untuk menentukan FVG sebagai **POI (*Point of Interest*)** utama.
  * **LTF (*Lower Time Frame*):** Menggunakan time frame **H1** untuk mencari konfirmasi setup dan trigger entry.

### 2. Empat Kriteria FVG Probabilitas Tinggi
1. **Searah dengan Tren (Trend Following):**
   * Jika tren sedang **Bearish**, prioritaskan hanya FVG Bearish untuk mencari peluang sell.
   * Jika tren sedang **Bullish**, prioritaskan FVG Bullish untuk mencari peluang buy.
   * Pemula disarankan untuk tidak melawan tren (*counter-trend*) dan fokus mengambil pergerakan dari *internal to external liquidity*.
2. **Berada di Area Premium atau Discount:**
   * Berdasarkan kebiasaan pergerakan pasar (*market behavior*), harga umumnya melakukan *pullback/retracement* ke area diskon atau premium.
   * **Aturan Area:**
     * Tren Bearish $\rightarrow$ Pilih FVG di area **Premium** (di atas level 0.5 Fibonacci).
     * Tren Bullish $\rightarrow$ Pilih FVG di area **Discount** (di bawah level 0.5 Fibonacci).
   * **Pengaturan Fibonacci:** Ditarik dari *Swing High* ke *Swing Low* (atau sebaliknya) dengan level: `0`, `0.25`, `0.5`, `0.75`, dan `1`.
3. **Melakukan Tugas Penting (Break of Structure / Break Swing):**
   * FVG yang bernilai tinggi adalah FVG yang terbentuk bersamaan dengan aksi harga menembus level penting, seperti memecahkan struktur pasar (*Break of Structure* / BOS) atau menembus *Swing Low/High*.
   * FVG jenis ini tetap memiliki bobot tinggi untuk dijadikan POI meski posisinya kadang berada di luar zona ideal premium/discount.
4. **FVG yang Belum Termitigasi (*Unmitigated / Fresh*):**
   * FVG yang belum pernah tersentuh sama sekali (*fresh*) memiliki probabilitas reaksi awal paling tinggi.
   * **Prinsip Mitigasi:** FVG yang sudah pernah tersentuh (termitigasi 1, 2, atau 3 kali) **masih tetap valid dan dapat digunakan**, asalkan **belum ditembus oleh penutupan badan candle (*body close*) pada HTF**. Selama hanya ekor candle (*wick*) yang masuk, area tersebut belum rusak.

### 3. Mekanisme Eksekusi & Konfirmasi Entry di LTF (H1)
Saat harga masuk ke area HTF FVG (POI), **dilarang langsung membuka posisi tanpa konfirmasi**. Entry harus menunggu checklist setup terpenuhi di LTF:
1. **Liquidity Sweep:** Terjadi sapuan likuiditas (*sweep*). Prioritaskan jika *sweep* terbentuk dari level Daily (HTF), meskipun *sweep* di H1 tetap dapat digunakan.
2. **Pembalikan Struktur (MSS atau CISD):**
   * **MSS (*Market Structure Shift*):** Penembusan level *Swing Low/High* struktural; konfirmasi ini lebih kuat/konservatif.
   * **CISD (*Change in State of Delivery*):** Bersifat lebih agresif, ditandai dengan ditembusnya *open candle* pertama yang mendorong terjadinya *liquidity sweep* (konsepnya serupa dengan *Order Block*).
3. **LTF FVG:** Terbentuk FVG baru di H1 setelah MSS/CISD terjadi sebagai area pijakan entry.

* **Aturan Open Posisi & Manajemen Risiko:**
  * **Entry:** Di batas awal FVG LTF (*early FVG* / ujung candle ke-3 pembentuk FVG) atau pada FVG yang bertepatan dengan garis CISD.
  * **Stop Loss (SL):** Diletakkan di atas/bawah *swing high/low* yang melakukan *liquidity sweep*.
  * **Take Profit (TP):** Menggunakan *Risk to Reward Ratio* (RR) ideal **1:2** atau menargetkan *external liquidity* terdekat.

### 4. Mindset Trading
Analisis teknikal bukan segalanya dan tidak ada yang tahu pasti ke mana arah market akan bergerak. Fungsi utama analisis hanyalah sebagai alat bantu objektif untuk mengambil keputusan: apakah saat ini kita harus mencari posisi *Buy* atau *Sell*, serta menjaga disiplin dengan selalu memasang *Stop Loss*.

---

## Bagian 2: Tabel Checklist Praktis FVG & Konfirmasi Entry

### 1. Checklist Seleksi FVG di HTF (Daily / D1) — Penentuan POI

| No | Parameter | Kriteria Validasi | Catatan / Kondisi |
| :---: | :--- | :--- | :--- |
| **1** | **Arah Tren** | Searah dengan struktur tren utama HTF | • Tren Bearish $\rightarrow$ FVG Bearish<br>• Tren Bullish $\rightarrow$ FVG Bullish |
| **2** | **Zona Harga** | Berada di zona Premium atau Discount | • Bearish: FVG di atas level 0.5 Fibonacci (Premium)<br>• Bullish: FVG di bawah level 0.5 Fibonacci (Discount) |
| **3** | **Tugas Penting** | Berhasil memecahkan struktur pasar | Menghasilkan *Break of Structure* (BOS) atau menembus *Swing Low/High* |
| **4** | **Status Mitigasi** | *Fresh* (belum tersentuh) atau belum ditembus body | Selama belum ada penutupan *body candle* HTF yang menembus FVG, area tetap valid digunakan |

### 2. Checklist Konfirmasi & Eksekusi di LTF (H1) — Trigger Entry

| Urutan | Tahapan Konfirmasi | Indikator yang Harus Muncul | Tindakan Trader |
| :---: | :--- | :--- | :--- |
| **1** | **Reaksi POI** | Harga masuk (*tap*) ke dalam area HTF FVG terpilih | Jangan langsung entry; tunggu respon harga di H1 |
| **2** | **Liquidity Sweep** | Terjadi sapuan likuiditas (*sweep*) pada *swing point* | Prioritaskan *sweep* Daily; jika tidak ada, gunakan *sweep* H1 |
| **3** | **Pembalikan Arah** | Muncul salah satu konfirmasi:<br>• **MSS** (konservatif): tembus *swing low/high* struktural<br>• **CISD** (agresif): tembus open candle pemicu sweep | Jika hanya ada sweep tanpa MSS/CISD, **jangan entry** (risiko harga lanjut tembus) |
| **4** | **Setup Entry** | Terbentuk FVG baru di H1 setelah MSS / CISD | Pasang limit/eksekusi di batas awal (*early*) FVG H1 |
| **5** | **Stop Loss (SL)** | Ujung *swing high/low* yang melakukan *liquidity sweep* | Wajib dipasang untuk proteksi modal |
| **6** | **Take Profit (TP)** | Minimal Risk:Reward **1:2** atau ke *external liquidity* terdekat | Jaga kedisiplinan rasio risiko dan target profit |

---

## Bagian 3: Seri Pembelajaran "ICT Dari Nol" (Chapter 1 – Chapter 7)

### Chapter 1: Dasar-Dasar yang Wajib Dipahami (Filosofi, Waktu, dan Sesi)
1. **Filosofi ICT vs Retail Tradisional:**
   * Metode retail tradisional cenderung mekanikal kaku (sentuh resistance sell, support buy, pola candlestick langsung eksekusi).
   * ICT membangun **narasi logis**: memahami market itu *dari mana*, *mau ke mana*, dan *sedang ingin melakukan apa*.
2. **Dua Tugas Pokok Algoritma Pasar:**
   * **Mencari Likuiditas (*Liquidity to Liquidity*):** Mengambil order stop loss dan pending order trader retail (*external liquidity* dan *internal liquidity*).
   * **Menyeimbangkan Ketidakseimbangan (*Rebalance Imbalance*):** Mengisi kembali kekosongan harga/area yang tidak seimbang di pasar.
3. **Prinsip Time and Price (Waktu dan Harga):**
   * *Time then Price*: Waktu terlebih dahulu, baru kemudian harga. Harga baru memiliki makna penting jika bereaksi pada waktu yang tepat. Jika waktunya salah, setup entry akan gagal.
4. **Pengaturan Zona Waktu (*New York Local Time*):**
   * Chart wajib diubah ke zona waktu **UTC-4 (New York Local Time)** saat musim panas, dan otomatis bergeser ke **UTC-5** saat musim dingin (*Daylight Saving Time*).
5. **Tiga Garis Acuan Waktu (*Time References*):**
   * **True Day Open:** Garis vertikal tepat pada pukul **00.00 tengah malam NYT** setiap hari (Senin - Jumat) untuk memisahkan siklus harian.
   * **Midnight Open:** Garis horizontal dari harga *open* candle pukul **00.00 NYT** ditarik ke kanan hingga pukul 00.00 hari berikutnya.
     * Di atas Midnight Open: Area **Premium** (zona cari SELL).
     * Di bawah Midnight Open: Area **Discount** (zona cari BUY).
   * **Weekly Open:** Garis horizontal dari harga *open* candle pertama di awal minggu (Senin) ditarik hingga Jumat.
     * Di atas Weekly Open = Premium mingguan; di bawah = Discount mingguan.
   * *Catatan:* Pergerakan impulsif di awal pembukaan yang menembus garis acuan sering kali merupakan manipulasi (*Judas Swing*) sebelum berbalik arah.
6. **ICT Kill Zones (Waktu Emas Eksekusi):**
   * **Asia Kill Zone (20.00 – 00.00 NYT):** Profil Akumulasi (*Accumulation*). Pasar bergerak konsolidasi membangun likuiditas (*liquidity engineering*).
   * **London Kill Zone (02.00 – 05.00 NYT):** Profil Manipulasi (*Manipulation / Judas Swing*). Membuat pergerakan menipu untuk menyapu likuiditas Asia.
   * **New York Kill Zone (07.00 – 10.00 NYT):** Profil Distribusi (*Distribution*). Arah pasar sebenarnya terkonfirmasi (*real move*), menjadi jendela terbaik untuk eksekusi.

---

### Chapter 2: Liquidity Concept (Sweep, Internal & External Liquidity)
1. **Definisi Likuiditas:** Kumpulan uang/order di pasar yang mencakup *Stop Loss*, *Buy Stop*, *Sell Stop*, dan posisi trader retail yang menjadi bahan bakar algoritma.
2. **Titik Likuiditas Berbobot Tinggi:**
   * *Session High & Low* (terutama Asia High/Low dan London High/Low).
   * *Previous Daily High (PDH)* dan *Previous Daily Low (PDL)*.
   * Level *Weekly High/Low* dan *Monthly High/Low*.
3. **Mekanisme Liquidity Sweep:**
   * Terjadi ketika harga mencoba menembus level likuiditas penting namun **gagal menutup badan candle (*body candle*)** di luar level tersebut (hanya menyisakan ekor/sumbu *wick*).
   * Bertujuan menjebak trader breakout dan membersihkan tumpukan order.
   * **Validasi Sweep:** Sweep baru valid jika telah memicu perubahan struktur (*Market Structure Shift / MSS*).
4. **Aliran Pergerakan Pasar:**
   * **External Liquidity:** Likuiditas di luar batas struktur (*swing high/low*).
   * **Internal Liquidity:** Likuiditas di dalam struktur, umumnya berwujud zona **PD Array** (FVG atau *Order Block*).
   * Algoritma bergerak bolak-balik: dari *External Liquidity* menuju *Internal Liquidity*, lalu kembali menembus *External Liquidity* baru.

---

### Chapter 3: MSS (Market Structure Shift) dan BOS (Break of Structure)
1. **Definisi & Perbedaan:**
   * **MSS (*Market Structure Shift* / CHoCH):** Sinyal awal perubahan arah tren pasar dari *bullish* menjadi *bearish* atau sebaliknya.
   * **BOS (*Break of Structure* / BMS):** Penembusan level struktur yang menandakan bahwa tren dominan masih berlanjut (*trend continuation*).
2. **Kriteria Validasi MSS:**
   * Garis MSS ditarik secara spesifik dari **Swing High/Low terakhir yang mendorong terjadinya Liquidity Sweep**, bukan sembarang swing.
   * Titik swing idealnya terdiri atas formasi 3 candle.
   * Penembusan harus dilakukan oleh lilin momentum agresif (*displacement candle*) yang meninggalkan celah FVG.
3. **Mekanisme BOS:**
   * Terjadi saat harga menembus *swing high/low* terkini dengan *displacement candle* dan mencetak level *high* atau *low* baru sebagai konfirmasi penerusan tren.

---

### Chapter 4: PD Array Matrix (FVG, Order Block, Breaker Block)
1. **Definisi PD Array Matrix:** Matriks zona harga terstruktur tempat Smart Money melakukan transaksi, terbagi atas area Premium (> 0.5 Fibonacci) untuk Sell dan Discount (< 0.5 Fibonacci) untuk Buy.
2. **Tiga PD Array Esensial:**
   * **Fair Value Gap (FVG):** Ketidakseimbangan (*imbalance*) akibat pergerakan tajam 3 candle di mana ekor candle ke-1 dan ke-3 tidak saling bersentuhan.
   * **Order Block (OB):** Deretan lilin terakhir yang memicu sapuan likuiditas, lalu ditembus oleh pergerakan *displacement* yang menghasilkan MSS dan FVG.
   * **Breaker Block (BB):** Order Block yang gagal menahan harga (tertembus/rusak), sehingga polaritas fungsinya berbalik arah.
     * **Unicorn Setup:** Setup A+ ketika Breaker Block bertumpuk (*overlap*) di level yang sama dengan FVG.
3. **Pengaturan Fibonacci OTE (*Optimal Trade Entry*):**
   * Ditarik dari ujung *Swing High* ke *Swing Low*.
   * Titik entry favorit berada di rasio **0.705 (70.5%)** atau **0.786 (78.6%)**, Stop Loss di level **1.02**, dan Take Profit di level **0**.

---

### Chapter 5: OLHC/OHLC, PO3 (AMD), dan Killzone
1. **Anatomi Perilaku Candle:**
   * Bullish Candle: **OLHC** (*Open $\rightarrow$ Low $\rightarrow$ High $\rightarrow$ Close*).
   * Bearish Candle: **OHLC** (*Open $\rightarrow$ High $\rightarrow$ Low $\rightarrow$ Close*).
   * Pembentukan Low pada candle bullish atau High pada candle bearish sesaat setelah Open adalah fase manipulasi algoritma untuk menjebak retail.
2. **Korelasi PO3 / AMD dengan Killzone:**
   * **Asia Killzone (20.00 – 00.00 NYT) $\rightarrow$ Akumulasi (A):** Rekayasa likuiditas; harga bolak-balik dalam range.
   * **London Killzone (02.00 – 05.00 NYT) $\rightarrow$ Manipulasi (M):** Terjadi *Judas Swing* menyapu level Asia.
   * **New York Killzone (07.00 – 10.00 NYT) $\rightarrow$ Distribusi (D):** Pergerakan nyata (*real move*) dan ekspansi tren; waktu terbaik eksekusi.
3. **Multi-Time Frame (MTF):**
   * Gunakan kombinasi time frame (misal: H1 untuk arah/HTF dan M15 untuk eksekusi/LTF). Penembusan di M15 sering kali hanya berupa *sweep* di H1 jika badan candle H1 ditutup di dalam level.

---

### Chapter 6: Daily Bias (Memahami Arah Harian)
1. **Definisi Daily Bias:** Arah dominan harian untuk menentukan fokus objektif: apakah hari ini hanya mencari posisi *Buy* atau *Sell*.
2. **Metode Penentuan Arah Menggunakan *Mother of Candle* (Candle D1 Sebelumnya):**
   * Tandai level **Previous Daily High (PDH)** dan **Previous Daily Low (PDL)**.
   * **Penerusan Tren (*Continuation*):**
     * Penutupan badan candle (*body close*) di atas PDH $\rightarrow$ Bias hari berikutnya **Bullish**.
     * Penutupan badan candle (*body close*) di bawah PDL $\rightarrow$ Bias hari berikutnya **Bearish**.
     * Status *mother candle* berpindah ke candle penembus tersebut.
   * **Pembalikan Arah (*Reversal*):**
     * Jika PDH/PDL hanya tersapu oleh ekor (*sweep*) tanpa *body close*, terutama jika bertepatan dengan POI HTF (FVG Daily/Weekly), bias berpotensi berbalik arah (*reversal*). Status *mother candle* tidak berpindah.
3. **Kondisi Dilarang Trading (Libur):**
   * Terjadi sapuan di kedua sisi (*double sweep*) atau candle berada di dalam rentang tanpa penembusan *body* yang tegas. Hindari market yang *sideways*.

---

### Chapter 7: Setup Entry Komprehensif (Swing Trading System)
1. **Filosofi Eksekusi:** Gunakan alat analisis secukupnya sesuai kebutuhan tanpa membuat chart rumit. Kerugian (*loss*) adalah hal wajar yang dikendalikan melalui rasio risiko dan kedisiplinan sistem.
2. **Prosedur 4 Langkah Analisis & Entry:**
   * **Langkah 1 (D1 Alignment):** Tren struktur H4 harus selaras dengan tren D1.
   * **Langkah 2 (D1 Liquidity Sweep):** Memastikan level likuiditas eksternal D1 telah tersapu (*sweep*) agar siap bergerak menuju likuiditas internal.
   * **Langkah 3 (H4 Market Structure):** Muncul konfirmasi struktur di H4 berupa MSS dan BOS yang valid.
   * **Langkah 4 (PD Array / FVG in Premium/Discount):** Tarik Fibonacci dari swing high ke low; pastikan ada FVG di area Premium (Sell) atau Discount (Buy).
3. **Parameter Eksekusi Posisi:**
   * **Entry:** Pasang Limit Order pada rasio OTE **0.705 (70.5%)**.
   * **Stop Loss (SL):** Di level Fibonacci **1.02**.
   * **Take Profit (TP):** Di level Fibonacci **0**.
   * *Aturan Pembatalan:* Jika TP tersentuh terlebih dahulu sebelum order terjemput, order wajib dibatalkan (*hangus*).
4. **Pencatatan Jurnal Trading:** Wajib mencatat tanggal, instrumen (*pair*), tipe posisi, screenshot sebelum & sesudah, kondisi emosi, dan hasil PnL untuk evaluasi berkala.

---

## Bagian 4: Diagram Alur Logika Sistem Trading ICT (Chapter 1 – 7)

```text
[ TAHAP 1: PENGATURAN WAKTU & BIAS UTAMA (Ch. 1 & Ch. 6) ]
  │
  ├── 1. Kalibrasi Chart ke UTC-4 (New York Local Time)
  │      └── Penentuan level acuan: Midnight Open (00.00 NYT) & Weekly Open (Senin)
  │
  └── 2. Penentuan Daily Bias melalui "Mother of Candle" (Daily / D1)
         ├── Kasus A: PDH/PDL ditembus Body Close ──> Bias Continuation (Ikuti tren penembusan)
         ├── Kasus B: PDH/PDL terkena Sweep + Tap HTF POI ──> Bias Reversal (Peluang balik arah)
         └── Kasus C: Double Sweep / Berada di tengah range ──> Market Sideways (NO TRADE / LIBUR)
  │
  ▼
[ TAHAP 2: VALIDASI LIKUIDITAS & STRUKTUR HTF (Ch. 2 & Ch. 3) ]
  │
  ├── 1. Pembacaan Aliran Likuiditas: External to Internal
  │      └── Cek apakah External Liquidity (PDH/PDL atau Session High/Low) sudah terkena Sweep
  │
  └── 2. Konfirmasi Validitas Sweep & Struktur
         ├── Sweep baru dianggap VALID jika memicu pembalikan struktur (MSS)
         └── Garis MSS ditarik tepat dari Swing terakhir pemicu terjadinya Liquidity Sweep
  │
  ▼
[ TAHAP 3: PEMILIHAN POI / ZONA REAKSI (Ch. 4 & Video Bonus FVG) ]
  │
  ├── 1. Pemetaan Zona Harga dengan Fibonacci
  │      ├── Di atas 0.5 = Premium (Khusus mencari peluang Sell)
  │      └── Di bawah 0.5 = Discount (Khusus mencari peluang Buy)
  │
  └── 2. Filter High Probability PD Array (Fokus FVG)
         ├── Searah tren (Trend Following)
         ├── Berada di zona Premium/Discount
         ├── Melakukan tugas penting (memicu BOS / break swing)
         └── Fresh / Unmitigated (atau belum ditembus Body Close pada HTF)
  │
  ▼
[ TAHAP 4: KONFIRMASI ENTRY & EKSEKUSI (Ch. 5 & Ch. 7) ]
  │
  ├── Mode A: Intraday / Day Trading (Memanfaatkan Siklus PO3 / AMD & Killzone)
  │      ├── Asia (20.00 - 00.00 NYT)   ──> Accumulation (Bangun likuiditas, wait & see)
  │      ├── London (02.00 - 05.00 NYT) ──> Manipulation (Judas Swing menyapu High/Low Asia)
  │      └── New York (07.00 - 10.00 NYT)──> Distribution (Eksekusi entry searah distribusi)
  │             └── Trigger LTF (H1/M15): Sweep ──> MSS/CISD ──> Entry di FVG LTF
  │
  └── Mode B: Swing Trading System (Setup H4 & D1 Narator)
         ├── 1. D1 Alignment (Tren H4 & D1 selaras)
         ├── 2. D1 Liquidity Sweep terkonfirmasi
         ├── 3. Struktur H4 terkonfirmasi (BOS/MSS)
         ├── 4. Tarik Fibonacci dari Swing High ke Swing Low
         │      ├── Titik Entry : Rasio OTE 0.705 (70.5%)
         │      ├── Stop Loss   : Level 1.02
         │      └── Take Profit : Level 0 (External Liquidity)
         └── 5. Aturan Pembatalan: Jika TP tersentuh sebelum order terjemput ──> Setup Batal
  │
  ▼
[ TAHAP 5: EVALUASI & JURNAL (Ch. 7) ]
  │
  └── Input ke Jurnal Trading (Wajib):
         ├── Tanggal, Pair, Arah Posisi
         ├── Checklist Probabilitas (Alignment, Sweep, MSS/BOS, FVG)
         ├── Screenshot Chart sebelum & sesudah eksekusi
         └── Catatan emosi/psikologi serta hasil akhir PnL
```

---

## Bagian 5: Matriks Komparasi Sistem (Setup Intraday vs Swing)

| Elemen Sistem | Setup Intraday (Chapter 5) | Setup Swing (Chapter 7) |
| :--- | :--- | :--- |
| **Time Frame Acuan** | H1 (HTF) dan M15 (LTF) | D1 (HTF) dan H4 (LTF) |
| **Filter Waktu** | Wajib berada di **ICT Killzone** (fokus New York) | Fleksibel / tidak tergantung Killzone |
| **Konsep Siklus** | Mengikuti template **OLHC/OHLC** dan siklus **PO3/AMD** | Mengikuti siklus **External $\rightarrow$ Internal Liquidity** |
| **Pemicu Entry** | Terbentuknya **CISD / MSS** diikuti **LTF FVG** | Pasang Limit Order di area **Fibonacci 0.705 (OTE)** |
| **Penempatan SL** | Di atas/bawah *swing wick* yang melakukan sweep | Di level **Fibonacci 1.02** |
| **Target TP** | Risk to Reward **1:2** atau ke liquidity terdekat | Di level **Fibonacci 0** |