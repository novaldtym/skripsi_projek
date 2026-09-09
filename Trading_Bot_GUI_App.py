import os
import sys
import time
import subprocess
import threading
import queue
import re
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox
import MetaTrader5 as mt5
import pandas as pd

# Path konfigurasi
BASE_DIR = r"d:\SKRIPSI INFORMATIKA"
PYTHON_EXE = sys.executable
SCRIPT_M15 = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot.py")
SCRIPT_M5  = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py")
EXCEL_M15  = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx")
EXCEL_M5   = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_M5_Scalping.xlsx")
MT5_PATH   = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

# ANSI regex untuk konversi warna terminal ke teks GUI
ANSI_PATTERN = re.compile(r'\033\[(?P<code>\d+(?:;\d+)*)m')

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ AI Trading Bot Dashboard - SMC / ICT LightGBM (M15 & M5)")
        self.root.geometry("1200x820")
        self.root.minsize(1050, 700)
        self.root.configure(bg="#0b0f19")

        # Status proses bot
        self.proc_m15 = None
        self.proc_m5  = None
        self.queue_m15 = queue.Queue()
        self.queue_m5  = queue.Queue()

        # Data & Mode Rekap Excel In-App
        self.current_rekap_mode = "m15"
        self.current_filter_status = "ALL"
        self.search_var = tk.StringVar()
        self.current_data_rows = []

        self.setup_styles()
        self.create_header()
        self.create_tabs()
        self.create_footer()

        # Mulai loop background polling
        self.root.after(100, self.process_log_queues)
        self.root.after(1000, self.update_live_market_ticker)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Styling Notebook Tabs
        style.configure("TNotebook", background="#0b0f19", borderwidth=0)
        style.configure("TNotebook.Tab", 
                        background="#161f30", 
                        foreground="#94a3b8", 
                        padding=[20, 10], 
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0)
        style.map("TNotebook.Tab", 
                  background=[("selected", "#0284c7"), ("active", "#1e293b")],
                  foreground=[("selected", "#ffffff"), ("active", "#38bdf8")])

        style.configure("TFrame", background="#0b0f19")
        style.configure("Card.TFrame", background="#161f30", relief="solid", borderwidth=1)

        # Styling Treeview Dark Theme
        style.configure("Treeview", 
                        background="#0f172a", 
                        foreground="#f8fafc", 
                        fieldbackground="#0f172a",
                        rowheight=26,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", 
                        background="#1e293b", 
                        foreground="#38bdf8", 
                        font=("Segoe UI", 9, "bold"),
                        padding=[6, 6])
        style.map("Treeview.Heading", 
                  background=[("active", "#334155")])
        style.map("Treeview", 
                  background=[("selected", "#0284c7")],
                  foreground=[("selected", "#ffffff")])

    def create_header(self):
        header_frame = tk.Frame(self.root, bg="#111827", height=80, relief="solid", bd=1)
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        # Judul & Subjudul
        title_box = tk.Frame(header_frame, bg="#111827")
        title_box.pack(side="left", padx=20, pady=12)

        lbl_title = tk.Label(title_box, text="⚡ AI TRADING BOT DASHBOARD", font=("Segoe UI", 16, "bold"), fg="#38bdf8", bg="#111827")
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(title_box, text="Smart Money Concepts (SMC) & LightGBM Machine Learning | XAUUSD", font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
        lbl_sub.pack(anchor="w")

        # Panel Kanan: Status MT5 & Live Ticker
        ticker_box = tk.Frame(header_frame, bg="#111827")
        ticker_box.pack(side="right", padx=20, pady=12)

        self.lbl_mt5_status = tk.Label(ticker_box, text="● MEMERIKSA MT5...", font=("Segoe UI", 9, "bold"), fg="#f59e0b", bg="#1f2937", padx=10, pady=3)
        self.lbl_mt5_status.pack(anchor="e")

        self.lbl_ticker = tk.Label(ticker_box, text="XAUUSD: Menghubungkan...", font=("Consolas", 11, "bold"), fg="#f8fafc", bg="#111827")
        self.lbl_ticker.pack(anchor="e", pady=(4, 0))

    def create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # TAB 1: BOT M15
        self.tab_m15 = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_m15, text="  📊 Bot M15 (SMC Konservatif)  ")
        self.setup_m15_tab()

        # TAB 2: BOT M5
        self.tab_m5 = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_m5, text="  ⚡ Bot M5 (SMC Level Bounce Scalper)  ")
        self.setup_m5_tab()

        # TAB 3: REKAP EXCEL & PORTOFOLIO
        self.tab_rekap = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_rekap, text="  📈 Rekap Transaksi & Hub Excel  ")
        self.setup_rekap_tab()

    # =========================================================================
    # TAB 1: BOT M15
    # =========================================================================
    def setup_m15_tab(self):
        paned = tk.PanedWindow(self.tab_m15, orient="horizontal", bg="#0b0f19", bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # Panel Kiri: Kontrol & Parameter
        left_panel = tk.Frame(paned, bg="#161f30", width=340, relief="solid", bd=1)
        paned.add(left_panel, minsize=320)

        lbl_panel_title = tk.Label(left_panel, text="KONTROL OPERASIONAL M15", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#161f30")
        lbl_panel_title.pack(anchor="w", padx=15, pady=(15, 10))

        # Status Pill
        self.m15_status_badge = tk.Label(left_panel, text="○ STATUS: NONAKTIF / STANDBY", font=("Segoe UI", 10, "bold"), fg="#ef4444", bg="#223049", padx=12, pady=6)
        self.m15_status_badge.pack(fill="x", padx=15, pady=(0, 15))

        # Tombol Start & Stop
        btn_frame = tk.Frame(left_panel, bg="#161f30")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_start_m15 = tk.Button(btn_frame, text="▶ AKTIFKAN BOT M15", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#10b981", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.start_bot_m15, pady=8)
        self.btn_start_m15.pack(fill="x", pady=(0, 8))

        self.btn_stop_m15 = tk.Button(btn_frame, text="⏹ HENTIKAN BOT M15", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#ef4444", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.stop_bot_m15, pady=8, state="disabled")
        self.btn_stop_m15.pack(fill="x")

        # Info Parameter Card
        info_box = tk.LabelFrame(left_panel, text=" Parameter Bot M15 ", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#161f30", padx=10, pady=10)
        info_box.pack(fill="x", padx=15, pady=(0, 15))

        params_text = (
            "• Timeframe       : M15 (15 Menit)\n"
            "• Model AI        : LightGBM (28 Fitur SMC)\n"
            "• Ambang Batas    : >= 60.0% Keyakinan\n"
            "• Filter Tren     : Tren Makro H1 EMA 50\n"
            "• Target TP / SL  : Dinamis ATR 14 (RRR 1:1.5)\n"
            "• Proximity Guard : Aktif (Jarak >= 0.25%)\n"
            "• Magic Number    : 123230\n"
            "• Lot Size        : 0.01 Lot"
        )
        tk.Label(info_box, text=params_text, font=("Consolas", 8), fg="#cbd5e1", bg="#161f30", justify="left").pack(anchor="w")

        # Tombol Buka & Lihat Excel M15
        excel_btns_m15 = tk.Frame(left_panel, bg="#161f30")
        excel_btns_m15.pack(fill="x", padx=15, side="bottom", pady=15)

        btn_view_m15 = tk.Button(excel_btns_m15, text="👁️ Tampilkan Tabel Excel M15", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.switch_to_rekap_tab("m15"), pady=7)
        btn_view_m15.pack(fill="x", pady=(0, 6))

        btn_excel_m15 = tk.Button(excel_btns_m15, text="📂 Buka di Aplikasi Excel (.xlsx)", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#334155", activeforeground="#38bdf8", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else messagebox.showerror("File Error", "File Excel M15 belum ditemukan!"), pady=5)
        btn_excel_m15.pack(fill="x")

        # Panel Kanan: Console Log
        right_panel = tk.Frame(paned, bg="#050811", relief="solid", bd=1)
        paned.add(right_panel)

        log_header = tk.Frame(right_panel, bg="#111827", height=35)
        log_header.pack(fill="x")
        tk.Label(log_header, text="TERMINAL MONITORING LIVE M15", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827").pack(side="left", padx=10, pady=5)
        tk.Button(log_header, text="Bersihkan Log", font=("Segoe UI", 8), fg="#94a3b8", bg="#1f2937", relief="flat", command=lambda: self.log_text_m15.delete('1.0', tk.END)).pack(side="right", padx=10, pady=5)

        self.log_text_m15 = tk.Text(right_panel, bg="#050811", fg="#f8fafc", font=("Consolas", 9), wrap="word", relief="flat", padx=10, pady=10)
        self.log_text_m15.pack(fill="both", expand=True)

        scroll_m15 = tk.Scrollbar(self.log_text_m15, command=self.log_text_m15.yview)
        scroll_m15.pack(side="right", fill="y")
        self.log_text_m15.configure(yscrollcommand=scroll_m15.set)

        self.setup_text_tags(self.log_text_m15)

    # =========================================================================
    # TAB 2: BOT M5
    # =========================================================================
    def setup_m5_tab(self):
        paned = tk.PanedWindow(self.tab_m5, orient="horizontal", bg="#0b0f19", bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True, padx=5, pady=5)

        # Panel Kiri: Kontrol & Parameter
        left_panel = tk.Frame(paned, bg="#161f30", width=340, relief="solid", bd=1)
        paned.add(left_panel, minsize=320)

        lbl_panel_title = tk.Label(left_panel, text="KONTROL OPERASIONAL M5", font=("Segoe UI", 11, "bold"), fg="#10b981", bg="#161f30")
        lbl_panel_title.pack(anchor="w", padx=15, pady=(15, 10))

        # Status Pill
        self.m5_status_badge = tk.Label(left_panel, text="○ STATUS: NONAKTIF / STANDBY", font=("Segoe UI", 10, "bold"), fg="#ef4444", bg="#223049", padx=12, pady=6)
        self.m5_status_badge.pack(fill="x", padx=15, pady=(0, 15))

        # Tombol Start & Stop
        btn_frame = tk.Frame(left_panel, bg="#161f30")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_start_m5 = tk.Button(btn_frame, text="▶ AKTIFKAN BOT M5", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#10b981", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.start_bot_m5, pady=8)
        self.btn_start_m5.pack(fill="x", pady=(0, 8))

        self.btn_stop_m5 = tk.Button(btn_frame, text="⏹ HENTIKAN BOT M5", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#ef4444", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.stop_bot_m5, pady=8, state="disabled")
        self.btn_stop_m5.pack(fill="x")

        # Info Parameter Card
        info_box = tk.LabelFrame(left_panel, text=" Strategi SMC Level Bounce M5 ", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#161f30", padx=10, pady=10)
        info_box.pack(fill="x", padx=15, pady=(0, 15))

        params_text = (
            "• Timeframe       : M5 (Scalping Cepat)\n"
            "• Strategi        : SMC Level Bounce & Wick\n"
            "• Level Anchor    : Lantai/Atap M15 10-Jam\n"
            "• Rejection Wick  : Minimal >= 35% Ekor\n"
            "• Quick Scalp TP  : +$2.00 USD (+20 pips)\n"
            "• Hard Cut-Loss   : -$1.80 USD (RRR 1:1)\n"
            "• Trailing Lock   : Trigger $1.20, Lock $0.80\n"
            "• Anti-Mid Trend  : Dilarang Entry di Tengah\n"
            "• Magic Number    : 123235"
        )
        tk.Label(info_box, text=params_text, font=("Consolas", 8), fg="#cbd5e1", bg="#161f30", justify="left").pack(anchor="w")

        # Tombol Buka & Lihat Excel M5
        excel_btns_m5 = tk.Frame(left_panel, bg="#161f30")
        excel_btns_m5.pack(fill="x", padx=15, side="bottom", pady=15)

        btn_view_m5 = tk.Button(excel_btns_m5, text="👁️ Tampilkan Tabel Excel M5", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#059669", activebackground="#047857", relief="flat", cursor="hand2", command=lambda: self.switch_to_rekap_tab("m5"), pady=7)
        btn_view_m5.pack(fill="x", pady=(0, 6))

        btn_excel_m5 = tk.Button(excel_btns_m5, text="📂 Buka di Aplikasi Excel (.xlsx)", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#334155", activeforeground="#10b981", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else messagebox.showerror("File Error", "File Excel M5 belum ditemukan!"), pady=5)
        btn_excel_m5.pack(fill="x")

        # Panel Kanan: Console Log
        right_panel = tk.Frame(paned, bg="#050811", relief="solid", bd=1)
        paned.add(right_panel)

        log_header = tk.Frame(right_panel, bg="#111827", height=35)
        log_header.pack(fill="x")
        tk.Label(log_header, text="TERMINAL MONITORING LIVE M5 SCALPER", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827").pack(side="left", padx=10, pady=5)
        tk.Button(log_header, text="Bersihkan Log", font=("Segoe UI", 8), fg="#94a3b8", bg="#1f2937", relief="flat", command=lambda: self.log_text_m5.delete('1.0', tk.END)).pack(side="right", padx=10, pady=5)

        self.log_text_m5 = tk.Text(right_panel, bg="#050811", fg="#f8fafc", font=("Consolas", 9), wrap="word", relief="flat", padx=10, pady=10)
        self.log_text_m5.pack(fill="both", expand=True)

        scroll_m5 = tk.Scrollbar(self.log_text_m5, command=self.log_text_m5.yview)
        scroll_m5.pack(side="right", fill="y")
        self.log_text_m5.configure(yscrollcommand=scroll_m5.set)

        self.setup_text_tags(self.log_text_m5)

    # =========================================================================
    # TAB 3: REKAP EXCEL & HUB PORTOFOLIO
    # =========================================================================
    # =========================================================================
    # TAB 3: REKAP EXCEL & HUB PORTOFOLIO (INTERACTIVE IN-APP EXCEL VIEWER)
    # =========================================================================
    def setup_rekap_tab(self):
        container = tk.Frame(self.tab_rekap, bg="#0b0f19")
        container.pack(fill="both", expand=True, padx=15, pady=12)

        # Kartu Rekap Atas
        cards_frame = tk.Frame(container, bg="#0b0f19")
        cards_frame.pack(fill="x", pady=(0, 12))

        # Kartu M15
        card_m15 = tk.Frame(cards_frame, bg="#161f30", relief="solid", bd=1, padx=15, pady=10)
        card_m15.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(card_m15, text="PORTOFOLIO MODEL M15 (KONSERVATIF)", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#161f30").pack(anchor="w")
        self.lbl_rekap_m15 = tk.Label(card_m15, text="Memuat riwayat...", font=("Consolas", 9), fg="#f8fafc", bg="#161f30", justify="left")
        self.lbl_rekap_m15.pack(anchor="w", pady=(4, 8))

        btn_box_15 = tk.Frame(card_m15, bg="#161f30")
        btn_box_15.pack(fill="x")
        self.btn_card_view_m15 = tk.Button(btn_box_15, text="👁️ Tampilkan Tabel Excel M15", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m15"), padx=10, pady=5)
        self.btn_card_view_m15.pack(side="left", padx=(0, 6))
        tk.Button(btn_box_15, text="📂 Buka di Excel (.xlsx)", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#334155", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else messagebox.showerror("File Error", "File Excel M15 belum ditemukan!"), padx=8, pady=5).pack(side="left")

        # Kartu M5
        card_m5 = tk.Frame(cards_frame, bg="#161f30", relief="solid", bd=1, padx=15, pady=10)
        card_m5.pack(side="right", fill="both", expand=True, padx=(6, 0))
        tk.Label(card_m5, text="PORTOFOLIO MODEL M5 (SCALPING DYNAMIC)", font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#161f30").pack(anchor="w")
        self.lbl_rekap_m5 = tk.Label(card_m5, text="Memuat riwayat...", font=("Consolas", 9), fg="#f8fafc", bg="#161f30", justify="left")
        self.lbl_rekap_m5.pack(anchor="w", pady=(4, 8))

        btn_box_5 = tk.Frame(card_m5, bg="#161f30")
        btn_box_5.pack(fill="x")
        self.btn_card_view_m5 = tk.Button(btn_box_5, text="👁️ Tampilkan Tabel Excel M5", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#059669", activebackground="#047857", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m5"), padx=10, pady=5)
        self.btn_card_view_m5.pack(side="left", padx=(0, 6))
        tk.Button(btn_box_5, text="📂 Buka di Excel (.xlsx)", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#334155", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else messagebox.showerror("File Error", "File Excel M5 belum ditemukan!"), padx=8, pady=5).pack(side="left")

        # Panel Tabel Interaktif Terpadu
        table_frame = tk.Frame(container, bg="#161f30", relief="solid", bd=1, padx=12, pady=10)
        table_frame.pack(fill="both", expand=True)

        # Header Bar Tabel
        tbl_top = tk.Frame(table_frame, bg="#161f30")
        tbl_top.pack(fill="x", pady=(0, 8))

        title_box = tk.Frame(tbl_top, bg="#161f30")
        title_box.pack(side="left")

        self.lbl_table_title = tk.Label(title_box, text="DAFTAR TRANSAKSI EXCEL M15", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#161f30")
        self.lbl_table_title.pack(anchor="w")

        self.lbl_table_subtitle = tk.Label(title_box, text="Memuat ringkasan data...", font=("Segoe UI", 8), fg="#94a3b8", bg="#161f30")
        self.lbl_table_subtitle.pack(anchor="w")

        # Tombol Navigasi Mode Data
        nav_box = tk.Frame(tbl_top, bg="#161f30")
        nav_box.pack(side="right")

        self.btn_nav_m15 = tk.Button(nav_box, text="📊 Excel M15", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m15"), padx=8, pady=4)
        self.btn_nav_m15.pack(side="left", padx=2)

        self.btn_nav_m5 = tk.Button(nav_box, text="⚡ Excel M5", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1e293b", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m5"), padx=8, pady=4)
        self.btn_nav_m5.pack(side="left", padx=2)

        self.btn_nav_stat = tk.Button(nav_box, text="📈 Perbandingan Statistik", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1e293b", activebackground="#6366f1", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("stat"), padx=8, pady=4)
        self.btn_nav_stat.pack(side="left", padx=2)

        self.btn_nav_mt5 = tk.Button(nav_box, text="🔄 Live MT5 Deals", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#1e293b", activebackground="#334155", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("mt5"), padx=8, pady=4)
        self.btn_nav_mt5.pack(side="left", padx=2)

        self.btn_nav_popup = tk.Button(nav_box, text="🔍 Jendela Penuh", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#1e293b", activebackground="#d97706", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.open_excel_viewer_modal, padx=8, pady=4)
        self.btn_nav_popup.pack(side="left", padx=2)

        self.btn_nav_refresh = tk.Button(nav_box, text="🔄 Refresh", font=("Segoe UI", 8), fg="#38bdf8", bg="#1e293b", activebackground="#334155", relief="flat", cursor="hand2", command=self.refresh_current_view, padx=8, pady=4)
        self.btn_nav_refresh.pack(side="left", padx=(2, 0))

        # Filter & Search Strip
        self.filter_strip = tk.Frame(table_frame, bg="#111827", relief="solid", bd=1, padx=8, pady=5)
        self.filter_strip.pack(fill="x", pady=(0, 8))

        filter_left = tk.Frame(self.filter_strip, bg="#111827")
        filter_left.pack(side="left")

        tk.Label(filter_left, text="🔍 Cari:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#111827").pack(side="left", padx=(0, 4))
        
        self.entry_search = tk.Entry(filter_left, textvariable=self.search_var, font=("Segoe UI", 8), bg="#1e293b", fg="#f8fafc", insertbackground="#38bdf8", relief="flat", width=22)
        self.entry_search.pack(side="left", padx=(0, 10), ipady=2)
        self.search_var.trace_add("write", lambda *args: self.render_table_rows())

        tk.Label(filter_left, text="Filter:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#111827").pack(side="left", padx=(5, 4))

        self.btn_filter_all = tk.Button(filter_left, text="Semua", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("ALL"), padx=8, pady=2)
        self.btn_filter_all.pack(side="left", padx=2)

        self.btn_filter_win = tk.Button(filter_left, text="Hanya WIN", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("WIN"), padx=8, pady=2)
        self.btn_filter_win.pack(side="left", padx=2)

        self.btn_filter_loss = tk.Button(filter_left, text="Hanya LOSS", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("LOSS"), padx=8, pady=2)
        self.btn_filter_loss.pack(side="left", padx=2)

        self.lbl_row_count = tk.Label(self.filter_strip, text="Menampilkan 0 baris", font=("Segoe UI", 8), fg="#94a3b8", bg="#111827")
        self.lbl_row_count.pack(side="right")

        # Container Treeview dengan Scrollbar Ganda (Vertikal & Horizontal)
        tree_container = tk.Frame(table_frame, bg="#161f30")
        tree_container.pack(fill="both", expand=True)

        self.scroll_y = ttk.Scrollbar(tree_container, orient="vertical")
        self.scroll_y.pack(side="right", fill="y")

        self.scroll_x = ttk.Scrollbar(tree_container, orient="horizontal")
        self.scroll_x.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(
            tree_container,
            columns=("no", "ticket", "w_open", "w_close", "durasi", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "hasil", "alasan"),
            show="headings",
            yscrollcommand=self.scroll_y.set,
            xscrollcommand=self.scroll_x.set
        )
        self.tree.pack(fill="both", expand=True)

        self.scroll_y.config(command=self.tree.yview)
        self.scroll_x.config(command=self.tree.xview)

        # Tree Tags
        self.tree.tag_configure("win", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("loss", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("normal", foreground="#f8fafc", font=("Consolas", 9))
        self.tree.tag_configure("stat_title", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("stat_num", foreground="#f8fafc", font=("Consolas", 9))

        # Muat ringkasan portofolio & data default (M15)
        self.update_portfolio_summary_labels()
        self.load_excel_view(mode="m15")

    def setup_text_tags(self, text_widget):
        text_widget.tag_configure("green", foreground="#10b981", font=("Consolas", 9, "bold"))
        text_widget.tag_configure("red", foreground="#ef4444", font=("Consolas", 9, "bold"))
        text_widget.tag_configure("yellow", foreground="#f59e0b")
        text_widget.tag_configure("cyan", foreground="#38bdf8")
        text_widget.tag_configure("white", foreground="#f8fafc")

    def create_footer(self):
        footer = tk.Frame(self.root, bg="#0b0f19", height=25)
        footer.pack(fill="x", padx=15, pady=(0, 8))
        tk.Label(footer, text="💡 Tip: Anda dapat menyalakan Bot M15 dan Bot M5 secara independen. Data log dan Excel selalu tersinkronisasi otomatis.", font=("Segoe UI", 8), fg="#64748b", bg="#0b0f19").pack(side="left")

    # =========================================================================
    # LOGIKA KONTROL PROSES (START & STOP)
    # =========================================================================
    def start_bot_m15(self):
        if self.proc_m15 is not None and self.proc_m15.poll() is None:
            messagebox.showinfo("Info", "Bot M15 sudah dalam keadaan berjalan!")
            return

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            self.proc_m15 = subprocess.Popen(
                [PYTHON_EXE, "-u", SCRIPT_M15],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=env
            )
            threading.Thread(target=self.reader_thread, args=(self.proc_m15, self.queue_m15), daemon=True).start()

            self.m15_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m15.config(state="disabled", bg="#064e3b")
            self.btn_stop_m15.config(state="normal", bg="#ef4444")
            self.append_log(self.log_text_m15, "🚀 [SYSTEM] Bot M15 Konservatif Berhasil Dinyalakan!\n", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyalakan Bot M15: {e}")

    def stop_bot_m15(self, manual=True):
        exit_code = None
        if self.proc_m15 is not None:
            exit_code = self.proc_m15.poll()
            if exit_code is None:
                try:
                    self.proc_m15.terminate()
                    self.proc_m15.wait(timeout=2)
                except Exception:
                    try:
                        self.proc_m15.kill()
                    except Exception:
                        pass
                exit_code = self.proc_m15.poll()

        self.proc_m15 = None
        self.m15_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m15.config(state="normal", bg="#10b981")
        self.btn_stop_m15.config(state="disabled", bg="#7f1d1d")
        if manual:
            self.append_log(self.log_text_m15, "\n🛑 [SYSTEM] Bot M15 Telah Dihentikan oleh Pengguna.\n", "red")
        else:
            self.append_log(self.log_text_m15, f"\n⚠️ [SYSTEM] Bot M15 Terhenti Otomatis (Exit Code: {exit_code}).\n", "yellow")

    def start_bot_m5(self):
        if self.proc_m5 is not None and self.proc_m5.poll() is None:
            messagebox.showinfo("Info", "Bot M5 sudah dalam keadaan berjalan!")
            return

        try:
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUTF8"] = "1"
            self.proc_m5 = subprocess.Popen(
                [PYTHON_EXE, "-u", SCRIPT_M5],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=env
            )
            threading.Thread(target=self.reader_thread, args=(self.proc_m5, self.queue_m5), daemon=True).start()

            self.m5_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m5.config(state="disabled", bg="#064e3b")
            self.btn_stop_m5.config(state="normal", bg="#ef4444")
            self.append_log(self.log_text_m5, "🚀 [SYSTEM] Bot M5 Level Bounce Scalper Berhasil Dinyalakan!\n", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyalakan Bot M5: {e}")

    def stop_bot_m5(self, manual=True):
        exit_code = None
        if self.proc_m5 is not None:
            exit_code = self.proc_m5.poll()
            if exit_code is None:
                try:
                    self.proc_m5.terminate()
                    self.proc_m5.wait(timeout=2)
                except Exception:
                    try:
                        self.proc_m5.kill()
                    except Exception:
                        pass
                exit_code = self.proc_m5.poll()

        self.proc_m5 = None
        self.m5_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m5.config(state="normal", bg="#10b981")
        self.btn_stop_m5.config(state="disabled", bg="#7f1d1d")
        if manual:
            self.append_log(self.log_text_m5, "\n🛑 [SYSTEM] Bot M5 Telah Dihentikan oleh Pengguna.\n", "red")
        else:
            self.append_log(self.log_text_m5, f"\n⚠️ [SYSTEM] Bot M5 Terhenti Otomatis (Exit Code: {exit_code}).\n", "yellow")

    def reader_thread(self, proc, out_queue):
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                out_queue.put(line)
        except Exception as e:
            out_queue.put(f"⚠️ [SYSTEM LOG ERROR] Reader thread error: {e}\n")
        finally:
            try:
                proc.stdout.close()
            except Exception:
                pass

    def process_log_queues(self):
        # Proses antrian log M15
        while not self.queue_m15.empty():
            line = self.queue_m15.get_nowait()
            self.parse_and_insert_log(self.log_text_m15, line)

        # Cek jika proses M15 tiba-tiba keluar
        if self.proc_m15 is not None and self.proc_m15.poll() is not None:
            self.stop_bot_m15(manual=False)

        # Proses antrian log M5
        while not self.queue_m5.empty():
            line = self.queue_m5.get_nowait()
            self.parse_and_insert_log(self.log_text_m5, line)

        # Cek jika proses M5 tiba-tiba keluar
        if self.proc_m5 is not None and self.proc_m5.poll() is not None:
            self.stop_bot_m5(manual=False)

        self.root.after(100, self.process_log_queues)

    def parse_and_insert_log(self, text_widget, raw_line):
        is_carriage = raw_line.startswith('\r') or raw_line.startswith('⏳ [')
        clean_text = ANSI_PATTERN.sub('', raw_line)
        
        # Deteksi tag warna
        tag = "white"
        if "BUY" in clean_text or "PROFIT" in clean_text or "BERHASIL" in clean_text:
            tag = "green"
        elif "SELL" in clean_text or "LOSS" in clean_text or "GAGAL" in clean_text or "Cut-Loss" in clean_text:
            tag = "red"
        elif "TERTAHAN" in clean_text or "WAIT" in clean_text or "NETRAL" in clean_text or "TERFILTER" in clean_text or "⚠️" in clean_text:
            tag = "yellow"
        elif "SYNC" in clean_text or "INFO" in clean_text or "AUDIT" in clean_text or "🔄" in clean_text:
            tag = "cyan"

        if is_carriage:
            clean_text = clean_text.lstrip('\r').strip() + "\n"
            try:
                last_line_idx = text_widget.index("end-1c linestart")
                last_line_text = text_widget.get(last_line_idx, "end-1c")
                if "⏳" in last_line_text:
                    text_widget.delete(last_line_idx, "end")
            except Exception:
                pass
            text_widget.insert(tk.END, clean_text, tag)
            text_widget.see(tk.END)
            return

        # Update tampilan normal
        text_widget.insert(tk.END, clean_text, tag)
        text_widget.see(tk.END)

    def append_log(self, text_widget, text, tag="white"):
        text_widget.insert(tk.END, text, tag)
        text_widget.see(tk.END)

    # =========================================================================
    # LIVE TICKER & REKAP DATA
    # =========================================================================
    def update_live_market_ticker(self):
        try:
            if not mt5.initialize(path=MT5_PATH):
                self.lbl_mt5_status.config(text="● MT5 DISCONNECTED", fg="#ef4444", bg="#450a0a")
                self.lbl_ticker.config(text="XAUUSD: MT5 Tidak Terhubung")
            else:
                self.lbl_mt5_status.config(text="● MT5 CONNECTED (EXNESS)", fg="#10b981", bg="#064e3b")
                sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
                tick = mt5.symbol_info_tick(sym)
                if tick:
                    spread_pips = (tick.ask - tick.bid) * 10.0
                    self.lbl_ticker.config(text=f"XAUUSD: Bid ${tick.bid:.2f} | Ask ${tick.ask:.2f} (Spread: {spread_pips:.1f} pips)")
        except Exception:
            pass
        self.root.after(2000, self.update_live_market_ticker)

    def switch_to_rekap_tab(self, mode="m15"):
        self.notebook.select(self.tab_rekap)
        self.load_excel_view(mode)

    def set_filter_status(self, status):
        self.current_filter_status = status
        self.btn_filter_all.config(
            bg="#0284c7" if status == "ALL" else "#1e293b",
            fg="#ffffff" if status == "ALL" else "#94a3b8",
            font=("Segoe UI", 8, "bold" if status == "ALL" else "normal")
        )
        self.btn_filter_win.config(
            bg="#059669" if status == "WIN" else "#1e293b",
            fg="#ffffff" if status == "WIN" else "#94a3b8",
            font=("Segoe UI", 8, "bold" if status == "WIN" else "normal")
        )
        self.btn_filter_loss.config(
            bg="#dc2626" if status == "LOSS" else "#1e293b",
            fg="#ffffff" if status == "LOSS" else "#94a3b8",
            font=("Segoe UI", 8, "bold" if status == "LOSS" else "normal")
        )
        self.render_table_rows()

    def refresh_current_view(self):
        self.update_portfolio_summary_labels()
        self.load_excel_view(self.current_rekap_mode)

    def refresh_rekap_data(self):
        # Dipanggil secara berkala untuk sinkronisasi otomatis
        self.update_portfolio_summary_labels()
        if self.current_rekap_mode == "mt5":
            self.load_excel_view("mt5")

    def update_portfolio_summary_labels(self):
        # Update M15 dari file Excel
        if os.path.exists(EXCEL_M15):
            try:
                df = pd.read_excel(EXCEL_M15, sheet_name="Trade Log Model Terbaru")
                tot = len(df)
                pnl = float(df["Profit ($ USD)"].sum()) if "Profit ($ USD)" in df else 0.0
                wins = len(df[df["Hasil"] == "WIN"]) if "Hasil" in df else 0
                loss = len(df[df["Hasil"] == "LOSS"]) if "Hasil" in df else 0
                wr = (wins / tot * 100) if tot > 0 else 0.0
                self.lbl_rekap_m15.config(
                    text=f"Total Trade : {tot} Transaksi\nWin / Loss  : {wins} WIN / {loss} LOSS\nWin Rate    : {wr:.1f}%\nNet PnL     : ${pnl:+.2f} USD"
                )
            except Exception:
                pass

        # Update M5 dari file Excel
        if os.path.exists(EXCEL_M5):
            try:
                df = pd.read_excel(EXCEL_M5, sheet_name="Trade Log M5 Scalping")
                tot = len(df)
                pnl = float(df["Profit ($ USD)"].sum()) if "Profit ($ USD)" in df else 0.0
                wins = len(df[df["Hasil"] == "WIN"]) if "Hasil" in df else 0
                loss = len(df[df["Hasil"] == "LOSS"]) if "Hasil" in df else 0
                wr = (wins / tot * 100) if tot > 0 else 0.0
                self.lbl_rekap_m5.config(
                    text=f"Total Trade : {tot} Transaksi\nWin / Loss  : {wins} WIN / {loss} LOSS\nWin Rate    : {wr:.1f}%\nNet PnL     : ${pnl:+.2f} USD"
                )
            except Exception:
                pass

    def load_excel_view(self, mode="m15"):
        self.current_rekap_mode = mode

        # Update visual tombol nav aktif
        self.btn_nav_m15.config(bg="#0284c7" if mode == "m15" else "#1e293b", fg="#ffffff" if mode == "m15" else "#94a3b8")
        self.btn_nav_m5.config(bg="#059669" if mode == "m5" else "#1e293b", fg="#ffffff" if mode == "m5" else "#94a3b8")
        self.btn_nav_stat.config(bg="#6366f1" if mode == "stat" else "#1e293b", fg="#ffffff" if mode == "stat" else "#94a3b8")
        self.btn_nav_mt5.config(bg="#0284c7" if mode == "mt5" else "#1e293b", fg="#ffffff" if mode == "mt5" else "#94a3b8")

        self.current_data_rows = []

        if mode in ["m15", "m5"]:
            self.filter_strip.pack(fill="x", pady=(0, 8))

            cols = ("no", "ticket", "w_open", "w_close", "durasi", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "hasil", "alasan")
            self.tree["columns"] = cols

            col_defs = [
                ("no", "Trade Ke-", 65, "center"),
                ("ticket", "Ticket", 95, "center"),
                ("w_open", "Waktu Open (WIB)", 135, "center"),
                ("w_close", "Waktu Close (WIB)", 135, "center"),
                ("durasi", "Durasi", 75, "center"),
                ("tipe", "Arah", 60, "center"),
                ("lot", "Lot", 50, "center"),
                ("entry", "Harga Entry", 95, "center"),
                ("sl", "Stop Loss", 95, "center"),
                ("tp", "Take Profit", 95, "center"),
                ("exit", "Harga Exit", 95, "center"),
                ("pips", "Pips", 70, "center"),
                ("profit", "Profit (USD)", 95, "center"),
                ("hasil", "Hasil", 65, "center"),
                ("alasan", "Alasan Exit / Keterangan", 220, "w"),
            ]
            for cid, heading, width, anchor in col_defs:
                self.tree.heading(cid, text=heading)
                self.tree.column(cid, width=width, anchor=anchor, stretch=(cid == "alasan"))

            target_excel = EXCEL_M15 if mode == "m15" else EXCEL_M5
            sheet_name = "Trade Log Model Terbaru" if mode == "m15" else "Trade Log M5 Scalping"
            model_label = "M15 Konservatif" if mode == "m15" else "M5 Scalper"

            if os.path.exists(target_excel):
                try:
                    df = pd.read_excel(target_excel, sheet_name=sheet_name)
                    wins, loss, total_pnl = 0, 0, 0.0
                    for _, r in df.iterrows():
                        pnl = float(r.get("Profit ($ USD)", 0.0))
                        total_pnl += pnl
                        hasil_str = str(r.get("Hasil", "")).strip().upper()
                        if hasil_str == "WIN": wins += 1
                        elif hasil_str == "LOSS": loss += 1

                        sl_val = r.get("Stop Loss (SL)")
                        tp_val = r.get("Take Profit (TP)")
                        row_data = {
                            "vals": (
                                int(r.get("Trade Ke-", 0)),
                                int(r.get("Ticket Posisi", 0)),
                                str(r.get("Waktu Open", "")),
                                str(r.get("Waktu Close", "")),
                                str(r.get("Durasi", "")),
                                str(r.get("Tipe", "")),
                                f"{float(r.get('Lot', 0.01)):.2f}",
                                f"${float(r.get('Harga Entry', 0)):.2f}",
                                f"${float(sl_val):.2f}" if pd.notna(sl_val) and sl_val > 0 else "-",
                                f"${float(tp_val):.2f}" if pd.notna(tp_val) and tp_val > 0 else "-",
                                f"${float(r.get('Harga Exit', 0)):.2f}",
                                f"{float(r.get('Pips (P/L)', 0)):+.1f}",
                                f"${pnl:+.2f}",
                                hasil_str,
                                str(r.get("Keterangan / Alasan Exit", ""))
                            ),
                            "hasil": hasil_str
                        }
                        self.current_data_rows.append(row_data)

                    tot = len(df)
                    wr = (wins / tot * 100) if tot > 0 else 0.0
                    self.lbl_table_title.config(
                        text=f"{'📊' if mode=='m15' else '⚡'} DATA TRANSAKSI EXCEL {model_label.upper()} ({tot} Trade Selesai)",
                        fg="#38bdf8" if mode == "m15" else "#10b981"
                    )
                    self.lbl_table_subtitle.config(
                        text=f"Total: {tot} Trade  |  {wins} WIN / {loss} LOSS (Win Rate: {wr:.1f}%)  |  Net PnL: ${total_pnl:+.2f} USD  |  File: {os.path.basename(target_excel)}"
                    )
                except Exception as e:
                    self.lbl_table_title.config(text=f"⚠️ GAGAL MEMBACA EXCEL {model_label.upper()}")
                    self.lbl_table_subtitle.config(text=f"Error: {e}")
            else:
                self.lbl_table_title.config(text=f"⚠️ FILE EXCEL {model_label.upper()} BELUM ADA")
                self.lbl_table_subtitle.config(text=f"Path: {target_excel}")

        elif mode == "stat":
            self.filter_strip.pack_forget()

            cols = ("metrik", "m15_val", "m5_val")
            self.tree["columns"] = cols
            self.tree.heading("metrik", text="Metrik Evaluasi Forward Testing Skripsi")
            self.tree.heading("m15_val", text="Model M15 Konservatif (TF 15m)")
            self.tree.heading("m5_val", text="Model M5 Level Bounce Scalper (TF 5m)")
            self.tree.column("metrik", width=340, anchor="w")
            self.tree.column("m15_val", width=280, anchor="center")
            self.tree.column("m5_val", width=280, anchor="center")

            self.lbl_table_title.config(text="📈 RINGKASAN STATISTIK & PERBANDINGAN MODEL M15 vs M5", fg="#818cf8")
            self.lbl_table_subtitle.config(text="Perbandingan indikator kinerja forward testing langsung dari lembar Ringkasan Statistik Excel.")

            try:
                s15 = pd.read_excel(EXCEL_M15, sheet_name="Ringkasan Statistik") if os.path.exists(EXCEL_M15) else pd.DataFrame()
                s5 = pd.read_excel(EXCEL_M5, sheet_name="Ringkasan Statistik") if os.path.exists(EXCEL_M5) else pd.DataFrame()

                if not s15.empty and not s5.empty:
                    merged = pd.merge(s15, s5, on="Metrik Evaluasi Forward Testing", suffixes=(" (M15)", " (M5)"), how="outer")
                    for _, r in merged.iterrows():
                        self.current_data_rows.append({
                            "vals": (str(r.iloc[0]), str(r.iloc[1]), str(r.iloc[2])),
                            "hasil": "STAT"
                        })
                elif not s15.empty:
                    for _, r in s15.iterrows():
                        self.current_data_rows.append({
                            "vals": (str(r.iloc[0]), str(r.iloc[1]), "-"),
                            "hasil": "STAT"
                        })
                elif not s5.empty:
                    for _, r in s5.iterrows():
                        self.current_data_rows.append({
                            "vals": (str(r.iloc[0]), "-", str(r.iloc[1])),
                            "hasil": "STAT"
                        })
            except Exception as e:
                self.lbl_table_subtitle.config(text=f"Gagal memuat ringkasan statistik: {e}")

        elif mode == "mt5":
            self.filter_strip.pack(fill="x", pady=(0, 8))

            cols = ("waktu", "magic", "tipe", "lot", "open_p", "close_p", "profit", "comment")
            self.tree["columns"] = cols
            self.tree.heading("waktu", text="Waktu Selesai (WIB)")
            self.tree.heading("magic", text="Model AI")
            self.tree.heading("tipe", text="Arah")
            self.tree.heading("lot", text="Lot")
            self.tree.heading("open_p", text="Harga Masuk")
            self.tree.heading("close_p", text="Harga Keluar")
            self.tree.heading("profit", text="Profit (USD)")
            self.tree.heading("comment", text="Alasan Exit")

            self.tree.column("waktu", width=140, anchor="center")
            self.tree.column("magic", width=130, anchor="center")
            self.tree.column("tipe", width=70, anchor="center")
            self.tree.column("lot", width=60, anchor="center")
            self.tree.column("open_p", width=95, anchor="center")
            self.tree.column("close_p", width=95, anchor="center")
            self.tree.column("profit", width=100, anchor="center")
            self.tree.column("comment", width=220, anchor="w")

            self.lbl_table_title.config(text="🔄 DAFTAR TRANSAKSI BROKER MT5 EXNESS (LIVE SYNC)", fg="#38bdf8")
            self.lbl_table_subtitle.config(text="Riwayat transaksi yang tersimpan langsung di server broker MetaTrader 5.")

            if mt5.initialize(path=MT5_PATH):
                deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
                if deals:
                    deal_ins = {d.position_id: d for d in deals if d.entry == 0 and d.position_id != 0}
                    deals_out = [d for d in deals if d.entry == 1 and d.magic in [123230, 123235]]
                    deals_out.sort(key=lambda x: x.time, reverse=True)

                    for d in deals_out:
                        d_in = deal_ins.get(d.position_id)
                        open_p = d_in.price if d_in else d.price
                        close_p = d.price
                        dir_str = ("BUY" if d_in.type == 0 else "SELL") if d_in else ("BUY" if d.type == 0 else "SELL")
                        model_name = "M15 Konservatif" if d.magic == 123230 else "M5 Scalper"
                        hasil_str = "WIN" if d.profit > 0 else ("LOSS" if d.profit < 0 else "BE")

                        self.current_data_rows.append({
                            "vals": (
                                datetime.fromtimestamp(d.time).strftime("%d/%m/%y %H:%M:%S"),
                                model_name,
                                dir_str,
                                f"{d.volume:.2f}",
                                f"${open_p:.2f}",
                                f"${close_p:.2f}",
                                f"${d.profit:+.2f}",
                                d.comment
                            ),
                            "hasil": hasil_str
                        })

        self.render_table_rows()

    def render_table_rows(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_q = self.search_var.get().strip().lower()
        filter_st = self.current_filter_status

        shown_count = 0
        for item in self.current_data_rows:
            vals = item["vals"]
            hasil = item.get("hasil", "")

            # Filter WIN/LOSS (jika bukan mode STAT)
            if filter_st == "WIN" and hasil != "WIN":
                continue
            if filter_st == "LOSS" and hasil != "LOSS":
                continue

            # Filter search query
            if search_q:
                row_str = " ".join(str(v).lower() for v in vals)
                if search_q not in row_str:
                    continue

            # Tentukan tag warna
            tag = "normal"
            if hasil == "WIN":
                tag = "win"
            elif hasil == "LOSS":
                tag = "loss"
            elif hasil == "STAT":
                tag = "stat_title"

            self.tree.insert("", "end", values=vals, tags=(tag,))
            shown_count += 1

        tot = len(self.current_data_rows)
        self.lbl_row_count.config(text=f"Menampilkan {shown_count} dari {tot} baris data")

    def open_excel_viewer_modal(self, default_tab=0):
        modal = tk.Toplevel(self.root)
        modal.title("📑 In-App Excel Data Viewer - Forward Testing AI Trading Bot")
        modal.geometry("1240x720")
        modal.minsize(1050, 600)
        modal.configure(bg="#0b0f19")

        # Header Bar Modal
        top_bar = tk.Frame(modal, bg="#111827", relief="solid", bd=1, padx=15, pady=10)
        top_bar.pack(fill="x", padx=15, pady=10)

        t_box = tk.Frame(top_bar, bg="#111827")
        t_box.pack(side="left")
        tk.Label(t_box, text="📑 JENDELA LENGKAP EXCEL DATA VIEWER", font=("Segoe UI", 13, "bold"), fg="#38bdf8", bg="#111827").pack(anchor="w")
        tk.Label(t_box, text="Pemantauan log transaksi dan ringkasan forward testing real-time tanpa perlu membuka Microsoft Excel", font=("Segoe UI", 8), fg="#94a3b8", bg="#111827").pack(anchor="w")

        r_box = tk.Frame(top_bar, bg="#111827")
        r_box.pack(side="right")
        tk.Button(r_box, text="📂 Buka Folder Proyek", font=("Segoe UI", 8), fg="#cbd5e1", bg="#1f2937", relief="flat", cursor="hand2", command=lambda: os.startfile(BASE_DIR), padx=10, pady=5).pack(side="left", padx=4)
        tk.Button(r_box, text="🔄 Refresh Semua Tab", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#1e293b", relief="flat", cursor="hand2", command=lambda: self.populate_modal_tabs(modal_nb), padx=10, pady=5).pack(side="left")

        modal_nb = ttk.Notebook(modal)
        modal_nb.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.populate_modal_tabs(modal_nb)
        try:
            modal_nb.select(default_tab)
        except Exception:
            pass

    def populate_modal_tabs(self, modal_nb):
        for tab in modal_nb.tabs():
            modal_nb.forget(tab)

        tab1 = self.build_modal_excel_tab(modal_nb, EXCEL_M15, "Trade Log Model Terbaru", is_stats=False, model_name="M15 Konservatif")
        modal_nb.add(tab1, text="  📊 Trade Log M15  ")

        tab2 = self.build_modal_excel_tab(modal_nb, EXCEL_M5, "Trade Log M5 Scalping", is_stats=False, model_name="M5 Scalper")
        modal_nb.add(tab2, text="  ⚡ Trade Log M5  ")

        tab3 = self.build_modal_excel_tab(modal_nb, EXCEL_M15, "Ringkasan Statistik", is_stats=True, model_name="Statistik M15")
        modal_nb.add(tab3, text="  📈 Ringkasan Statistik M15  ")

        tab4 = self.build_modal_excel_tab(modal_nb, EXCEL_M5, "Ringkasan Statistik", is_stats=True, model_name="Statistik M5")
        modal_nb.add(tab4, text="  📈 Ringkasan Statistik M5  ")

    def build_modal_excel_tab(self, parent, file_path, sheet_name, is_stats=False, model_name=""):
        frame = tk.Frame(parent, bg="#0b0f19")

        bar = tk.Frame(frame, bg="#161f30", padx=12, pady=8)
        bar.pack(fill="x", padx=10, pady=(10, 6))

        info_lbl = tk.Label(bar, text=f"Memuat data {sheet_name}...", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#161f30")
        info_lbl.pack(side="left")

        search_box = tk.Frame(bar, bg="#161f30")
        search_box.pack(side="right")
        tk.Label(search_box, text="🔍 Cari:", font=("Segoe UI", 8, "bold"), fg="#94a3b8", bg="#161f30").pack(side="left", padx=4)
        search_v = tk.StringVar()
        s_entry = tk.Entry(search_box, textvariable=search_v, font=("Segoe UI", 8), bg="#1e293b", fg="#f8fafc", relief="flat", width=20)
        s_entry.pack(side="left", padx=4)

        tree_box = tk.Frame(frame, bg="#161f30")
        tree_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        sy = ttk.Scrollbar(tree_box, orient="vertical")
        sy.pack(side="right", fill="y")
        sx = ttk.Scrollbar(tree_box, orient="horizontal")
        sx.pack(side="bottom", fill="x")

        tree = ttk.Treeview(tree_box, show="headings", yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.pack(fill="both", expand=True)
        sy.config(command=tree.yview)
        sx.config(command=tree.xview)

        tree.tag_configure("win", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        tree.tag_configure("loss", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        tree.tag_configure("normal", foreground="#f8fafc", font=("Consolas", 9))
        tree.tag_configure("stat_k", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))

        rows_data = []

        if os.path.exists(file_path):
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if is_stats:
                    tree["columns"] = ("k", "v")
                    tree.heading("k", text="Metrik Evaluasi")
                    tree.heading("v", text="Nilai Statistik")
                    tree.column("k", width=380, anchor="w")
                    tree.column("v", width=340, anchor="center")

                    for _, r in df.iterrows():
                        rows_data.append({"vals": (str(r.iloc[0]), str(r.iloc[1])), "tag": "stat_k"})

                    info_lbl.config(text=f"📋 Ringkasan Statistik {model_name} ({len(df)} Indikator Evaluasi)")
                else:
                    cols = ("no", "ticket", "w_open", "w_close", "durasi", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "hasil", "alasan")
                    tree["columns"] = cols
                    col_defs = [
                        ("no", "#", 50, "center"),
                        ("ticket", "Ticket", 95, "center"),
                        ("w_open", "Waktu Open", 130, "center"),
                        ("w_close", "Waktu Close", 130, "center"),
                        ("durasi", "Durasi", 70, "center"),
                        ("tipe", "Arah", 60, "center"),
                        ("lot", "Lot", 50, "center"),
                        ("entry", "Entry", 90, "center"),
                        ("sl", "SL", 90, "center"),
                        ("tp", "TP", 90, "center"),
                        ("exit", "Exit", 90, "center"),
                        ("pips", "Pips", 65, "center"),
                        ("profit", "Profit ($)", 90, "center"),
                        ("hasil", "Hasil", 65, "center"),
                        ("alasan", "Keterangan / Alasan Exit", 220, "w"),
                    ]
                    for cid, h, w, a in col_defs:
                        tree.heading(cid, text=h)
                        tree.column(cid, width=w, anchor=a)

                    wins, loss, pnl_tot = 0, 0, 0.0
                    for _, r in df.iterrows():
                        pnl = float(r.get("Profit ($ USD)", 0.0))
                        pnl_tot += pnl
                        h_str = str(r.get("Hasil", "")).strip().upper()
                        if h_str == "WIN": wins += 1
                        elif h_str == "LOSS": loss += 1

                        sl_val = r.get("Stop Loss (SL)")
                        tp_val = r.get("Take Profit (TP)")
                        tag = "win" if h_str == "WIN" else ("loss" if h_str == "LOSS" else "normal")
                        vals = (
                            int(r.get("Trade Ke-", 0)),
                            int(r.get("Ticket Posisi", 0)),
                            str(r.get("Waktu Open", "")),
                            str(r.get("Waktu Close", "")),
                            str(r.get("Durasi", "")),
                            str(r.get("Tipe", "")),
                            f"{float(r.get('Lot', 0.01)):.2f}",
                            f"${float(r.get('Harga Entry', 0)):.2f}",
                            f"${float(sl_val):.2f}" if pd.notna(sl_val) and sl_val > 0 else "-",
                            f"${float(tp_val):.2f}" if pd.notna(tp_val) and tp_val > 0 else "-",
                            f"${float(r.get('Harga Exit', 0)):.2f}",
                            f"{float(r.get('Pips (P/L)', 0)):+.1f}",
                            f"${pnl:+.2f}",
                            h_str,
                            str(r.get("Keterangan / Alasan Exit", ""))
                        )
                        rows_data.append({"vals": vals, "tag": tag})

                    tot = len(df)
                    wr = (wins / tot * 100) if tot > 0 else 0.0
                    info_lbl.config(text=f"📊 {model_name}: {tot} Trade | {wins} WIN / {loss} LOSS ({wr:.1f}%) | Net PnL: ${pnl_tot:+.2f} USD")

            except Exception as e:
                info_lbl.config(text=f"⚠️ Gagal membaca sheet {sheet_name}: {e}")
        else:
            info_lbl.config(text=f"⚠️ File Excel belum ditemukan: {file_path}")

        def filter_modal_rows(*args):
            for itm in tree.get_children():
                tree.delete(itm)
            sq = search_v.get().strip().lower()
            for r in rows_data:
                if sq and sq not in " ".join(str(v).lower() for v in r["vals"]):
                    continue
                tree.insert("", "end", values=r["vals"], tags=(r["tag"],))

        search_v.trace_add("write", filter_modal_rows)
        filter_modal_rows()
        return frame

    def on_close(self):
        if (self.proc_m15 and self.proc_m15.poll() is None) or (self.proc_m5 and self.proc_m5.poll() is None):
            if messagebox.askyesno("Konfirmasi Keluar", "Salah satu atau kedua Bot trading masih aktif berjalan di pasar.\nApakah Anda yakin ingin mematikan semua bot dan keluar?"):
                self.stop_bot_m15()
                self.stop_bot_m5()
                self.root.destroy()
        else:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()
