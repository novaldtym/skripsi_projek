import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import os

def set_cell_border(cell, **kwargs):
    """
    Set cell borders: top, bottom, left, right
    kwargs: top={"sz": 12, "val": "single", "color": "000000"}
    """
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'single'))
            element.set(qn('w:sz'), str(edge_data.get('sz', 4)))
            element.set(qn('w:space'), '0')
            element.set(qn('w:color'), edge_data.get('color', 'auto'))
            tcBorders.append(element)
    tcPr.append(tcBorders)

def set_cell_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def create_bab1_document():
    doc = docx.Document()

    # 1. Page Margins (Standar Skripsi: Top 4cm, Left 4cm, Bottom 3cm, Right 3cm)
    # 4 cm = 1.575 in, 3 cm = 1.181 in
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.575)
        section.left_margin = Inches(1.575)
        section.bottom_margin = Inches(1.181)
        section.right_margin = Inches(1.181)
        section.page_width = Inches(8.27)   # A4
        section.page_height = Inches(11.69) # A4

    # 2. Styles
    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Times New Roman'
    style_normal.font.size = Pt(12)
    style_normal.font.color.rgb = RGBColor(0, 0, 0)
    style_normal.paragraph_format.line_spacing = 1.5
    style_normal.paragraph_format.space_after = Pt(0)
    style_normal.paragraph_format.space_before = Pt(0)

    def add_title(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.space_before = Pt(12)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(14)
        run.font.name = 'Times New Roman'
        return p

    def add_heading(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.space_before = Pt(12)
        run = p.add_run(text)
        run.bold = True
        run.font.size = Pt(12)
        run.font.name = 'Times New Roman'
        return p

    def add_body_p(text, indent=True):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(6)
        if indent:
            p.paragraph_format.first_line_indent = Inches(0.39) # 1 cm indent
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    # --- COVER / HEADER ---
    add_title("BAB I\nPENDAHULUAN")

    # --- 1.1 LATAR BELAKANG MASALAH ---
    add_heading("1.1 Latar Belakang Masalah")
    
    add_body_p(
        "Pasar perdagangan komoditas Emas dunia terhadap Dolar Amerika Serikat (XAUUSD) merupakan salah "
        "satu instrumen derivatif dan safe-haven asset paling likuid dan aktif di dunia dengan volume transaksi "
        "harian global melampaui ratusan miliar dolar AS. Karakteristik safe-haven menjadikan emas sebagai instrumen "
        "utama lindung nilai terhadap lonjakan inflasi, ketidakstabilan geopolitik, dan devaluasi mata uang fiat. "
        "Namun demikian, tingginya likuiditas dan keterlibatan pelaku pasar global berskala institusional "
        "(seperti bank sentral, hedge funds, dan liquidity providers) mengakibatkan pergerakan harga emas di pasar spot "
        "memiliki tingkat volatilitas yang sangat ekstrem, bersifat non-linear, non-stasioner, serta dipenuhi oleh "
        "derau acak (high noise density) pada horizon waktu intraday (Al-Thaqeb et al., 2026; Kazemdehbashi, 2026)."
    )

    add_body_p(
        "Dalam menghadapi dinamika pasar tersebut, mayoritas pelaku pasar retail secara tradisional mengandalkan "
        "analisis teknikal konvensional yang berbasis pada indikator-indikator lagging seperti Relative Strength Index (RSI), "
        "Moving Average Convergence Divergence (MACD), Bollinger Bands, maupun Simple Moving Average (SMA). "
        "Kelemahan mendasar dari indikator-indikator matematis konvensional tersebut adalah sifatnya yang reaktif "
        "dan bersumber murni dari rata-rata pergerakan harga masa lalu, sehingga kerap terlambat merespons perubahan momentum "
        "pasar secara mendadak. Akibatnya, trader retail sangat rentan mengalami kerugian akibat sinyal palsu (false breakout) "
        "dan perangkap likuiditas (liquidity hunt / stop run) yang sengaja dipicu oleh algoritma perdagangan institusional "
        "skala besar (Smart Money)."
    )

    add_body_p(
        "Untuk membaca perilaku aliran dana institusional tersebut, berkembang metodologi Smart Money Concepts (SMC) "
        "dan Inner Circle Trader (ICT) dalam analisis pergerakan harga (price action). Konsep ini mengidentifikasi jejak "
        "akumulasi dan distribusi modal institusi melalui struktur geometri pasar yang spesifik, antara lain: Order Block (OB) "
        "sebagai jejak konsolidasi order institusional terakhir sebelum terjadinya ekspansi harga yang agresif; "
        "Fair Value Gap (FVG) sebagai area ketidakseimbangan harga (price imbalance) akibat agresivitas satu sisi pasar "
        "yang cenderung akan ditutup kembali (rebalance); serta struktur Break of Structure (BOS) dan Change of Character (CHoCH) "
        "sebagai sinyal pergeseran struktur tren pasar (market structure shift). Meskipun metodologi SMC memiliki landasan "
        "logika pasar yang rasional, penerapannya oleh trader retail selama ini masih dilakukan secara manual, subjektif, "
        "dan sarat dengan bias psikologis emosional (seperti fear of missing out dan balas dendam pasar pasca-loss), "
        "sehingga menyulitkan tercapainya konsistensi performa jangka panjang."
    )

    add_body_p(
        "Di sisi lain, perkembangan pesat teknologi kecerdasan buatan (Artificial Intelligence) dan Machine Learning "
        "membuka peluang besar untuk mentransformasi analisis teknikal dan SMC menjadi sistem kuantitatif yang objektif, "
        "terukur, dan beroperasi otomatis tanpa bias manusia. Berbagai algoritma pembelajaran mesin populer seperti "
        "Support Vector Machine (SVM), Random Forest (RF), Artificial Neural Network (ANN), dan Extreme Gradient Boosting (XGBoost) "
        "telah banyak diteliti untuk peramalan harga komoditas (Ben Jabeur et al., 2024; Gono et al., 2023; Nasrul et al., 2026). "
        "Namun demikian, telaah kritis terhadap literatur penelitian terkini mengungkap adanya tiga celah permasalahan mendasar "
        "(research gaps) yang belum terjawab secara tuntas:"
    )

    add_body_p(
        "Pertama, orientasi formulasi masalah yang keliru antara regresi harga nominal versus klasifikasi probabilitas arah pergerakan diskrit. "
        "Sebagian besar penelitian terdahulu (misalnya Gono et al., 2023; Nasrul et al., 2026; Li, 2023) memformulasikan peramalan harga "
        "ke dalam tugas regresi nominal (memprediksi nilai dolar atau rupiah emas esok hari). Dalam domain perdagangan riil berfrekuensi tinggi, "
        "prediksi harga nominal mengalami galat kumulatif (error accumulation) dan lagging bias, di mana nilai prediksi hari ini cenderung "
        "hanya membuntuti harga penutupan candle sebelumnya. Pendekatan ini tidak memberikan arahan keputusan yang dapat dieksekusi secara presisi. "
        "Sebagaimana ditegaskan oleh Kazemdehbashi (2026) serta Al-Thaqeb et al. (2026), peramalan finansial yang aplikatif memerlukan pemisahan "
        "ke arah prediksi probabilitas tren diskrit (directional probability) yang terkalibrasi presisi dengan ambang batas keyakinan tinggi "
        "(high-conviction threshold ≥ 65%) agar sistem mampu menyaring dan menahan diri saat kondisi pasar tidak menentu (choppy/sideways)."
    )

    add_body_p(
        "Kedua, isolasi data internal dan pengabaian intermarket analysis multi-timeframe serta guncangan berita makroekonomi. "
        "Mayoritas model yang dikembangkan dalam literatur hanya memanfaatkan data internal single-asset pada single-timeframe harian (D1) "
        "atau intraday tunggal. Model tersebut mengabaikan korelasi intermarket global yang krusial, khususnya hubungan keterbalikan yang sangat kuat "
        "antara harga emas spot dan Indeks Dolar AS (DXY) (Sayegh & Accary, 2026). Ketika DXY menguat secara tajam, emas hampir selalu mengalami "
        "tekanan jual masif, dan sebaliknya. Selain itu, pasar emas sangat rentan terhadap guncangan volatilitas mendadak akibat rilis data "
        "makroekonomi Amerika Serikat yang berdampak tinggi (High-Impact Economic News), seperti laporan ketenagakerjaan Non-Farm Payrolls (NFP), "
        "Consumer Price Index (CPI), dan keputusan tingkat suku bunga Federal Open Market Committee (FOMC) (Nguyen et al., 2025; KC et al., 2024). "
        "Model peramalan yang buta terhadap jadwal berita makro dan struktur tren pada timeframe yang lebih tinggi (higher timeframe trend alignment H4/H1) "
        "pasti akan mengalami serangkaian kekalahan beruntun (whipsaw / black swan loss) ketika rilis fundamental ekonomi membalikkan struktur harga intraday."
    )

    add_body_p(
        "Ketiga, ketiadaan validasi forward testing secara riil dengan arsitektur manajemen risiko adaptif dan mesin evaluasi pasca-trade. "
        "Hampir seluruh penelitian terdahulu berhenti pada evaluasi backtesting statis berbasis train-test split historis. "
        "Metrik performa teoritis seperti RMSE, MAE, atau akurasi in-sample sering kali mengalami optimisme semu (overfitting) dan runtuh "
        "ketika dihadapkan pada friksi eksekusi pasar riil, seperti spread broker dinamis, slippage, latency jaringan, serta penolakan order kuotasi. "
        "Lebih lanjut, belum ada penelitian yang mengintegrasikan model machine learning dengan mesin diagnosa pasca-transaksi (Scenario Evaluator Engine) "
        "yang secara sistematis menguji ketahanan setiap kondisi skenario pasar sebanyak 5 hingga 10 kali guna membedakan skenario unggulan "
        "dari skenario yang harus dihindari (auto-blacklist) demi perbaikan berkelanjutan (continuous learning) model di masa depan."
    )

    add_body_p(
        "Guna mengatasi ketiga keterbatasan mendasar tersebut, penelitian ini mengusulkan penerapan algoritma Light Gradient Boosting Machine (LightGBM) "
        "yang diintegrasikan ke dalam arsitektur Multi-Source Feature Fusion 36 variabel terstandarisasi. Algoritma LightGBM dipilih karena memiliki "
        "keunggulan arsitektural mutakhir dibandingkan model tree-based konvensional lainnya seperti Random Forest dan XGBoost. "
        "LightGBM menerapkan teknik Gradient-based One-Side Sampling (GOSS) untuk menyaring instans data berdasarkan gradien kesalahan "
        "serta Exclusive Feature Bundling (EFB) untuk mereduksi dimensi fitur tanpa kehilangan informasi esensial (Ke et al., 2017). "
        "Selain itu, strategi pertumbuhan pohon berbasis daun (Leaf-wise Tree Growth with Depth Limitation) memungkinkan LightGBM mencapai "
        "konvergensi loss yang jauh lebih dalam dengan kecepatan komputasi 10 hingga 20 kali lebih cepat dan efisiensi memori yang jauh lebih unggul "
        "dibandingkan XGBoost maupun arsitektur Deep Learning (Zhou et al., 2025; Du et al., 2023). Karakteristik komputasi ultra-cepat ini sangat krusial "
        "untuk sistem perdagangan terotomasi yang menuntut inferensi probabilitas real-time dengan latensi nol (zero-delay) pada penutupan candle M15 dan M5."
    )

    add_body_p(
        "Sistem yang dibangun dalam penelitian ini mengonstruksi 36 variabel fitur prediktif yang menggabungkan empat pilar domain: "
        "(1) Geometri Candlestick dan Momentum Intraday (M15 dan M5); (2) Struktur Geometri Institusional Smart Money Concepts "
        "(Order Block Bullish/Bearish, Fair Value Gap Bullish/Bearish, Break of Structure, Change of Character, Liquidity Sweep, dan Fibonacci Retracement); "
        "(3) Jangkar Tren Multi-Timeframe Makro H4 dan H1 (EMA 50 dan EMA 200); serta (4) Kanal Makroekonomi & Intermarket DXY "
        "(rasio return XAU/DXY, tren DXY, dan siklus rilis berita berdampak tinggi NFP, CPI, serta FOMC). "
        "Model LightGBM dilatih dengan pembobotan kelas seimbang (balanced class weights) untuk menghasilkan estimasi probabilitas arah pergerakan "
        "yang terkalibrasi halus (0.0% – 100.0%). Keputusan eksekusi transaksi hanya dipicu apabila probabilitas model melampaui ambang batas "
        "keyakinan tinggi (confidence threshold ≥ 65%), dan langsung dihubungkan dengan terminal MetaTrader 5 API yang dipersenjatai manajemen risiko "
        "ketat berbasis Average True Range (ATR), rasio Risk-to-Reward (RRR) terukur 1 : 2.5, pembatasan kerugian harian maksimum (Max Daily Losses), "
        "cooldown period, serta pencatatan log evaluasi skenario perdagangan secara otomatis."
    )

    add_body_p(
        "Melalui pendekatan komprehensif ini, penelitian ini diharapkan dapat memberikan kontribusi nyata dalam bidang Informatika dan Computational Finance, "
        "membuktikan secara empiris kemampuan algoritma LightGBM dalam memprediksi probabilitas arah pergerakan harga emas XAUUSD, "
        "serta menghasilkan artefak sistem trading algoritmik yang andal, disiplin, dan teruji pada kondisi pasar keuangan global yang sebenarnya."
    )

    # --- 1.2 RUMUSAN MASALAH ---
    add_heading("1.2 Rumusan Masalah")
    add_body_p(
        "Berdasarkan uraian latar belakang masalah di atas, rumusan masalah dalam penelitian tugas akhir ini dirumuskan sebagai berikut:",
        indent=False
    )
    rm_items = [
        "Bagaimana merancang dan mengimplementasikan arsitektur Multi-Source Feature Fusion yang mengintegrasikan 36 variabel heterogen mencakup geometri candlestick, Smart Money Concepts (Order Block, FVG, BOS, CHoCH), korelasi intermarket Indeks Dolar AS (DXY), siklus berita makroekonomi (NFP, CPI, FOMC), serta jangkar tren multi-timeframe H4/H1 tanpa menimbulkan bias kebocoran data masa depan (lookahead bias / data leakage)?",
        "Bagaimana menerapkan dan mengoptimasi algoritma LightGBM Classifier dengan skema Leaf-wise Tree Growth, pembobotan kelas seimbang (balanced class weights), dan hyperparameter tuning sistematis guna menghasilkan estimasi probabilitas arah pergerakan harga XAUUSD yang terkalibrasi presisi pada timeframe M15 dan M5?",
        "Bagaimana merancang arsitektur sistem eksekusi otomatis zero-delay terintegrasi MetaTrader 5 API yang menerapkan filter ambang batas keyakinan tinggi (high-conviction threshold ≥ 65%), filter tren multi-timeframe H4, serta manajemen risiko kuantitatif dinamis (Dynamic ATR Stop-Loss, Risk-to-Reward Ratio 1 : 2.5, Max Daily Losses, dan Cooldown Period)?",
        "Bagaimana membangun Post-Trade Scenario Evaluator Engine untuk mendiagnosa akar penyebab keberhasilan (Take Profit) maupun kegagalan (Stop Loss) pada setiap transaksi tertutup, serta menguji ketahanan setiap skenario pasar sebanyak 5 hingga 10 kali transaksi sebagai mekanisme evaluasi berkelanjutan (continuous learning) dan backtesting model?",
        "Bagaimana efektivitas dan kinerja model LightGBM yang dibangun jika dibandingkan dengan algoritma machine learning pembanding (XGBoost dan Random Forest) berdasarkan metrik evaluasi klasifikasi statistik (ROC-AUC, Log Loss, Precision, Recall, F1-Score) serta metrik profitabilitas forward testing pasar nyata (Win Rate, Profit Factor, Drawdown, dan Return on Investment)?"
    ]
    for i, item in enumerate(rm_items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Inches(0.39)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(4)
        run_num = p.add_run(f"{i}. ")
        run_num.bold = True
        run_num.font.name = 'Times New Roman'
        run_num.font.size = Pt(12)
        run_text = p.add_run(item)
        run_text.font.name = 'Times New Roman'
        run_text.font.size = Pt(12)

    # --- 1.3 BATASAN MASALAH ---
    add_heading("1.3 Batasan Masalah")
    add_body_p(
        "Agar pembahasan dalam penelitian ini tetap terfokus, mendalam, dan terarah sesuai dengan ruang lingkup keilmuan Teknik Informatika, "
        "ditetapkan sejumlah batasan masalah sebagai berikut:",
        indent=False
    )
    bm_items = [
        "Objek instrumen keuangan yang diteliti dibatasi secara spesifik pada pasangan mata uang komoditas Emas spot terhadap Dolar Amerika Serikat (XAUUSD).",
        "Data historis yang digunakan untuk pelatihan dan validasi model bersumber dari penarikan candle real-time MetaTrader 5 broker teregulasi sebanyak 50.000 candle pada timeframe operasional M15 (Intraday Swing) dan M5 (High-Precision Scalping), dengan data konfirmasi tren makro pada timeframe H1 dan H4.",
        "Variabel masukan (fitur independen) dibatasi pada 36 variabel terstandarisasi yang mencakup: Geometri Candlestick, Smart Money Concepts (Order Block Bullish & Bearish, Fair Value Gap, Break of Structure, Change of Character, Liquidity Sweep), Fibonacci Retracement (rasio 0.382, 0.500, 0.618), Indikator Momentum (RSI 14, Bollinger Bands Bandwidth, ATR 14), Korelasi Intermarket Indeks Dolar AS (DXY), serta fitur biner indikator kalender makroekonomi (minggu rilis NFP, hari rilis CPI, dan minggu rilis FOMC).",
        "Algoritma machine learning utama yang diimplementasikan adalah LightGBM (Light Gradient Boosting Machine) Classifier, dengan model pembanding terbatas pada Extreme Gradient Boosting (XGBoost) dan Random Forest (RF).",
        "Target luaran model merupakan probabilitas klasifikasi biner arah pergerakan harga 5 candle ke depan (label 1 untuk kenaikan harga di atas ambang ATR, dan label 0 untuk penurunan/stagnan) dengan penerapan ambang batas keyakinan tinggi (confidence threshold) ≥ 65.0%.",
        "Pengujian operasional sistem (live forward testing) dilakukan secara otomatis melalui koneksi MetaTrader 5 Python API pada akun forward testing dengan saldo evaluasi awal terstandarisasi sebesar $500.00 USD, menerapkan ukuran lot terkontrol (0.01 lot), rasio Risk-to-Reward minimal 1 : 2.5, batas maksimal posisi terbuka bertumpuk (max stacked positions = 2), serta batas toleransi kerugian harian maksimum (max daily losses = 5 trade).",
        "Lingkungan pengembangan perangkat lunak menggunakan bahasa pemrograman Python 3.13 dengan pustaka utama: lightgbm, scikit-learn, MetaTrader5, pandas, numpy, dan openpyxl."
    ]
    for i, item in enumerate(bm_items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Inches(0.39)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(4)
        run_num = p.add_run(f"{i}. ")
        run_num.bold = True
        run_num.font.name = 'Times New Roman'
        run_num.font.size = Pt(12)
        run_text = p.add_run(item)
        run_text.font.name = 'Times New Roman'
        run_text.font.size = Pt(12)

    # --- 1.4 TUJUAN PENELITIAN ---
    add_heading("1.4 Tujuan Penelitian")
    add_body_p("Tujuan yang hendak dicapai dalam penelitian tugas akhir ini adalah:", indent=False)
    tp_items = [
        "Membangun dan menguji pipeline Multi-Source Feature Fusion yang mampu mengintegrasikan 36 variabel prediktif heterogen (geometri candle, Smart Money Concepts, momentum, tren H4, intermarket DXY, dan rilis berita makroekonomi) secara sinkron tanpa kebocoran data masa depan (lookahead bias).",
        "Mengembangkan model klasifikasi probabilitas terkalibrasi berbasis algoritma LightGBM yang mampu memprediksi arah pergerakan harga XAUUSD secara akurat dan menyaring kondisi pasar konsolidasi (noise/sideways) melalui penetapan ambang keyakinan tinggi (≥ 65%).",
        "Mengimplementasikan sistem eksekusi perdagangan terotomasi zero-delay terintegrasi MetaTrader 5 API yang dilengkapi modul manajemen risiko adaptif (Dynamic ATR SL, RRR 1 : 2.5, batas kerugian harian, dan jeda cooldown pasca-loss).",
        "Mengembangkan Post-Trade Scenario Evaluator Engine untuk mendokumentasikan, mendiagnosa, dan mengevaluasi akar penyebab profit dan loss setiap transaksi pasar secara transparan ke dalam spreadsheet laporan terstruktur, serta menguji ketahanan skenario pasar 5–10 kali sebagai landasan continuous learning model.",
        "Mengevaluasi dan membandingkan performa model LightGBM terhadap algoritma pembanding (XGBoost dan Random Forest) berdasarkan metrik evaluasi klasifikasi statistik (ROC-AUC, Precision, Recall, Log Loss) serta metrik finansial riil (Win Rate, Profit Factor, Maksimum Drawdown, dan Return on Investment) pada pengujian forward testing pasar nyata."
    ]
    for i, item in enumerate(tp_items, 1):
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.left_indent = Inches(0.39)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        p.paragraph_format.space_after = Pt(4)
        run_num = p.add_run(f"{i}. ")
        run_num.bold = True
        run_num.font.name = 'Times New Roman'
        run_num.font.size = Pt(12)
        run_text = p.add_run(item)
        run_text.font.name = 'Times New Roman'
        run_text.font.size = Pt(12)

    # --- 1.5 MANFAAT PENELITIAN ---
    add_heading("1.5 Manfaat Penelitian")
    add_body_p(
        "Hasil dari penelitian tugas akhir ini diharapkan dapat memberikan manfaat yang signifikan, baik secara teoritis maupun praktis, sebagai berikut:",
        indent=False
    )
    
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("1. Manfaat Teoritis (Akademik & Keilmuan Informatika):")
    r.bold = True
    r.font.name = 'Times New Roman'
    add_body_p(
        "a. Memberikan kontribusi ilmiah dalam bidang Applied Machine Learning dan Data Mining pada deret waktu finansial (Financial Time Series), "
        "khususnya mengenai efektivitas algoritma Gradient Boosting berbasis histogram (LightGBM) dalam memproses data tabular berdimensi tinggi "
        "dan berkarakteristik non-stasioner.",
        indent=True
    )
    add_body_p(
        "b. Menyajikan bukti empiris mengenai pentingnya integrasi data lintas-domain (Multi-Source Feature Fusion) yang menggabungkan struktur "
        "geometri pasar institusional (Smart Money Concepts), tren multi-timeframe, dan variabel makroekonomi eksternal (Indeks DXY dan High-Impact News) "
        "dalam meningkatkan akurasi dan ketahanan model peramalan prediktif terhadap guncangan pasar.",
        indent=True
    )
    add_body_p(
        "c. Menjadi referensi akademik bagi peneliti dan mahasiswa program studi Informatika dalam mengimplementasikan kalibrasi probabilitas "
        "klasifikasi untuk pengambilan keputusan kuantitatif di bawah ketidakpastian (decision making under uncertainty).",
        indent=True
    )

    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run("2. Manfaat Praktis (Praktisi, Trader Retail, & Industri Finansial):")
    r.bold = True
    r.font.name = 'Times New Roman'
    add_body_p(
        "a. Menyediakan sistem pendukung keputusan (Decision Support System) dan alat bantu perdagangan otomatis yang objektif, rasional, dan disiplin "
        "bagi para trader retail guna mengeliminasi faktor bias psikologis (seperti keserakahan, kepanikan, dan revenge trading) yang selama ini "
        "menjadi penyebab utama kegagalan akun retail.",
        indent=True
    )
    add_body_p(
        "b. Menghadirkan model mitigasi risiko modal yang teruji melalui penerapan filter ambang batas keyakinan (high-conviction threshold ≥ 65%), "
        "manajemen ukuran risiko dinamis berbasis Average True Range (ATR), serta proteksi pembatasan kerugian harian maksimum (Max Daily Losses).",
        indent=True
    )
    add_body_p(
        "c. Menyediakan modul otomatisasi evaluasi pasca-trade (Scenario Evaluator Engine) yang memudahkan praktisi dalam menganalisis matriks keberhasilan "
        "dan kegagalan transaksi secara transparan dan terdata untuk keperluan audit kinerja portofolio investasi.",
        indent=True
    )

    # --- 1.6 KEASLIAN PENELITIAN & RESEARCH GAP ---
    add_heading("1.6 Keaslian Penelitian dan Research Gap")
    add_body_p(
        "Keaslian penelitian ini didasarkan pada perbandingan komprehensif terhadap sejumlah penelitian terdahulu yang relevan di bidang "
        "peramalan harga emas, algoritma pembelajaran mesin pada instrumen finansial, dan pemodelan data deret waktu kuantitatif. "
        "Penelitian terdahulu yang dijadikan rujukan mencakup artikel jurnal internasional bereputasi (Scopus Q1/Q2), artikel jurnal nasional "
        "terakreditasi SINTA, serta naskah ilmiah mutakhir (arXiv 2024–2026). "
        "Berdasarkan kajian terhadap literatur tersebut, belum ditemukan penelitian yang mengintegrasikan algoritma LightGBM dengan 36 variabel "
        "Multi-Source Feature Fusion (SMC + Multi-Timeframe + Makroekonomi DXY/News), klasifikasi probabilitas terkalibrasi tinggi (≥ 65%), "
        "serta eksekusi forward testing real-time berbasis MetaTrader 5 yang dilengkapi Post-Trade Scenario Evaluator Engine. "
        "Ringkasan komparasi antara penelitian terdahulu dan posisi orisinalitas penelitian ini disajikan pada Tabel 1.1.",
        indent=True
    )

    # --- TABEL 1.1 MATRIKS KOMPARASI PENELITIAN TERKAIT ---
    p_tab_title = doc.add_paragraph()
    p_tab_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_tab_title.paragraph_format.space_before = Pt(8)
    p_tab_title.paragraph_format.space_after = Pt(4)
    r = p_tab_title.add_run("Tabel 1.1 Matriks Komparasi Penelitian Terdahulu dan Kontribusi Penelitian Ini")
    r.bold = True
    r.font.name = 'Times New Roman'
    r.font.size = Pt(11)

    # Define literature data
    lit_matrix = [
        (
            "Al-Thaqeb et al. (2026)",
            "J. of Risk and Financial Management (Scopus Q2)",
            "XAUUSD (Harian / D1)",
            "Random Forest, SVM, Artificial Neural Network (ANN)",
            "Harga OHLCV historis dan indikator makroekonomi (suku bunga, minyak dunia, kurs valuta).",
            "Random Forest mencapai akurasi arah tertinggi (~68.2%).",
            "Hanya menggunakan data harian (D1), tidak memodelkan geometri mikrostruktur institusional (Order Block/FVG), tidak menguji eksekusi real-time forward testing intraday, dan ketiadaan manajemen risiko dinamis ATR."
        ),
        (
            "Ben Jabeur et al. (2024)",
            "Annals of Operations Research (Scopus Q1)",
            "Emas Spot Global (Harian)",
            "Extreme Gradient Boosting (XGBoost) + SHAP Interaction Values",
            "Indeks ketidakpastian geopolitik (GPR), volatilitas pasar modal (VIX), dan harga komoditas global.",
            "XGBoost mengungguli model linear dan ANN dalam regresi harga nominal dengan penjelasan atribusi fitur via SHAP.",
            "Berorientasi pada regresi nominal jangka panjang, tidak menghasilkan probabilitas klasifikasi terkalibrasi untuk trigger order trading, tidak memanfaatkan struktur SMC intraday, dan pelatihan pohon XGBoost lambat."
        ),
        (
            "Nasrul Fadhila Akbar (2026)",
            "Prosiding Seminar Nasional Indonesia (Sociohum)",
            "Harga Emas Fisik Antam (Domestik Indonesia)",
            "Perbandingan XGBoost vs. Random Forest Regressor",
            "Indikator teknikal konvensional (EMA, RSI, MACD) berbasis data historis penutupan harian.",
            "Random Forest menghasilkan MAE lebih rendah dibandingkan XGBoost pada peramalan harga nominal emas Antam.",
            "Hanya meneliti komoditas emas fisik domestik harian, fitur terbatas pada indikator lagging konvensional, mengabaikan intermarket Indeks Dolar AS (DXY) dan rilis berita ekonomi AS, serta tidak ada otomasi trading."
        ),
        (
            "Kazemdehbashi (2026)",
            "arXiv:2601.12706 (Pre-print Januari 2026)",
            "Data Deret Waktu Emas Harian",
            "Trend-Adjusted Time Series (TATS) Hibrida Klasifikasi Arah + LSTM/Bi-LSTM",
            "Data sekuensial deret waktu harga emas harian.",
            "Pemisahan prediksi tren arah diskrit terbukti menurunkan galat peramalan finansial dibanding model time-series murni.",
            "Mengandalkan arsitektur Deep Learning (LSTM) yang lambat untuk inferensi real-time, tidak menguji pada timeframe intraday (M15/M5), tidak memasukkan intermarket DXY, dan belum diuji pada eksekusi forward testing pasar nyata."
        ),
        (
            "Gono et al. (2023)",
            "Mathematics (MDPI, Scopus Q1)",
            "Harga Komoditas Logam Perak / Silver",
            "Extreme Gradient Boosting (XGBoost) Regressor",
            "Data harga historis komoditas logam perak.",
            "Nilai koefisien determinasi (R-squared) mencapai > 0.95 pada dataset pengujian.",
            "Pendekatan regresi nominal menghasilkan efek lagging bias (prediksi hanya membuntuti harga kemarin), tidak memberikan sinyal eksekusi beli/jual yang aplikatif, dan tidak mengintegrasikan market structure institusional."
        ),
        (
            "Subeesh et al. (2025)",
            "Int. J. of Financial Studies (Scopus Q2)",
            "Emas Spot Dunia (Harian)",
            "Hibrida ARIMA + Random Forest / SVR dengan Data Fusion Multimodal",
            "Indikator teknikal dasar, indeks sentimen berita finansial, inflasi AS, dan yield obligasi.",
            "Fusi data multimodal meningkatkan akurasi arah sebesar ~5.2% dibanding model teknikal murni.",
            "Skala waktu harian tanpa arsitektur multi-timeframe intraday (M15-M5-H4), pipeline data terlalu lambat untuk eksekusi intraday, dan ketiadaan confidence guard untuk menyaring kondisi pasar konsolidasi (choppy market)."
        ),
        (
            "Zhou et al. (2025)",
            "Systems (MDPI, Scopus Q2)",
            "Pasar Saham Global",
            "Hibrida ARIMA, Recurrent Neural Network (RNN), dan LightGBM",
            "Multi-lag returns, volume perdagangan, dan indikator volatilitas historis.",
            "LightGBM terbukti unggul telak dalam efisiensi komputasi (kecepatan latih 15x lebih cepat) dan mencapai F1-score tertinggi pada data besar.",
            "Objek berupa saham konvensional (bukan komoditas emas ber-leverage tinggi yang sensitif DXY), tidak memodelkan geometri likuiditas Smart Money Concepts (SMC), dan tidak ada integrasi eksekusi pasar riil MetaTrader."
        ),
        (
            "Sayegh & Accary (2026)",
            "Economies (MDPI, Scopus Q2)",
            "Imbal Hasil Emas Spot dan Indeks Dolar AS (DXY)",
            "Analisis Ekonometrika Deret Waktu & Transmisi Kanal Dolar AS (2000–2025)",
            "Data return harian XAUUSD dan Indeks Dolar AS (DXY).",
            "Membuktikan secara empiris bahwa Indeks Dolar AS (DXY) merupakan determinan paling dominan terhadap dinamika imbal hasil emas secara konsisten.",
            "Analisis bersifat retrospektif statistik tanpa membangun model machine learning prediktif otomatis, tidak memanfaatkan timeframe intraday untuk mendeteksi divergensi jangka pendek, dan tidak ada sistem trading."
        ),
        (
            "Research on SMC / Order Blocks (2024–2025)",
            "Financial Time Series Microstructure (arXiv:2402.14728)",
            "Pasar Valuta Asing dan Komoditas",
            "Algoritma Deteksi Geometris Smart Money Concepts (SMC/ICT)",
            "Order Block (OB), Fair Value Gap (FVG), Break of Structure (BOS), Change of Character (CHoCH).",
            "Validasi bahwa area Order Block dan FVG memiliki probabilitas pantulan (bounce rate) signifikan lebih tinggi dibanding support/resistance konvensional.",
            "Hanya berfokus pada deteksi pola geometris statis tanpa diintegrasikan dengan model pembelajaran mesin ensemble (LightGBM) untuk mengukur probabilitas keberhasilan secara kuantitatif, serta tanpa filter makroekonomi DXY."
        ),
        (
            "Penelitian Ini (Nouval Ditya Maheswara, 2026)",
            "Tugas Akhir Teknik Informatika UPN 'Veteran' Yogyakarta",
            "XAUUSD Pasar Spot Riil (Multi-Timeframe M15 & M5 dengan konfirmasi H4)",
            "LightGBM Classifier Teroptimasi dengan Balanced Class Weights & Confidence Guard (>= 65%)",
            "36 Variabel Multi-Source Feature Fusion: Geometri M15/M5, SMC (Order Block Bull & Bear, FVG Bull & Bear, BOS, CHoCH, Sweep), Fibo 100 candle, Jangkar Tren H4 (EMA 50/200), Kanal DXY (XAU/DXY Return, Tren DXY), dan Fitur Siklus Berita Makro (NFP, CPI, FOMC).",
            "Akurasi Sinyal High-Conviction (>= 65%) mencapai 74.77% pada M15 (ROC-AUC 0.595) dan 79.26% pada M5 (ROC-AUC 0.618). Live forward testing otomatis menghasilkan eksekusi presisi dengan RRR 1 : 2.5.",
            "MENGISI SELURUH GAP PENELITIAN: Memadukan 4 domain fitur heterogen (SMC + MTF H4 + DXY + Berita Makro), mengusung klasifikasi probabilitas terkalibrasi tinggi (>= 65%) berbasis LightGBM ultra-cepat, eksekusi real-time zero-delay via MetaTrader 5 API dengan Dynamic ATR SL, serta dilengkapi Post-Trade Scenario Evaluator Engine untuk continuous learning dan evaluasi 5–10x skenario."
        )
    ]

    table = doc.add_table(rows=len(lit_matrix) + 1, cols=7)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    headers = [
        "Peneliti & Tahun",
        "Publikasi / Jurnal",
        "Objek Penelitian",
        "Metode / Algoritma",
        "Variabel / Fitur Masukan",
        "Hasil & Metrik Performa",
        "Kelemahan / Research Gap yang Ditinggalkan"
    ]
    
    col_widths = [Inches(1.0), Inches(1.0), Inches(0.9), Inches(1.1), Inches(1.2), Inches(1.1), Inches(1.5)]

    # Style Header Row
    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].width = col_widths[i]
        set_cell_shading(hdr_cells[i], "D9E1F2") # soft blue/gray header
        set_cell_border(hdr_cells[i], top={"sz": 12, "val": "single", "color": "000000"},
                                      bottom={"sz": 12, "val": "single", "color": "000000"})
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.0
        for r in p.runs:
            r.bold = True
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.5)

    # Populate Data Rows
    for row_idx, data in enumerate(lit_matrix, start=1):
        row_cells = table.rows[row_idx].cells
        is_current_study = (row_idx == len(lit_matrix))
        bg_color = "E2EFDA" if is_current_study else ("FFFFFF" if row_idx % 2 == 1 else "F9F9F9")

        for col_idx, text in enumerate(data):
            row_cells[col_idx].text = text
            row_cells[col_idx].width = col_widths[col_idx]
            set_cell_shading(row_cells[col_idx], bg_color)
            
            # borders
            b_bottom = {"sz": 12, "val": "single", "color": "000000"} if is_current_study else {"sz": 4, "val": "single", "color": "D0D0D0"}
            set_cell_border(row_cells[col_idx], bottom=b_bottom)
            
            p = row_cells[col_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if col_idx > 1 else WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.15
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(9.0)
                if is_current_study:
                    r.bold = (col_idx == 0 or col_idx == 3 or col_idx == 6)

    # Concluding text
    add_body_p(
        "Berdasarkan pemetaan matriks penelitian terkait pada Tabel 1.1 di atas, tampak jelas bahwa penelitian ini "
        "menghadirkan terobosan metodologis yang komprehensif. Kebaruan (novelty) dan kontribusi utama penelitian ini "
        "terletak pada sintesis holistik empat domain prediktif dalam satu kesatuan arsitektur LightGBM yang teroptimasi, "
        "penggunaan filter probabilitas keyakinan tinggi (high-conviction threshold ≥ 65%) untuk mengeliminasi false signals "
        "pada kondisi pasar bergejolak, serta pengujian forward testing pasar nyata yang dilengkapi mesin evaluasi skenario "
        "pasca-transaksi (Scenario Evaluator Engine) demi transparansi dan keandalan sistem trading algoritmik.",
        indent=True
    )

    out_path = r"d:\SKRIPSI INFORMATIKA\DRAF_BAB_1_SKRIPSI_NOUVAL.docx"
    doc.save(out_path)
    print(f"[SUCCESS] Document saved successfully to: {out_path}")
    return out_path

if __name__ == '__main__':
    create_bab1_document()
