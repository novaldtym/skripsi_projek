import os
import sys
import time
import math
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

# Regex untuk parsing output bot
RE_PROB_LIVE = re.compile(r'BUY[:\s=]+(\d+\.?\d*)%\s*\|\s*SELL[:\s=]+(\d+\.?\d*)%', re.IGNORECASE)
RE_DECISION_BUY = re.compile(r'KEPUTUSAN BUY', re.IGNORECASE)
RE_DECISION_SELL = re.compile(r'KEPUTUSAN SELL', re.IGNORECASE)
RE_DECISION_NETRAL = re.compile(r'KEPUTUSAN NETRAL', re.IGNORECASE)
RE_DECISION_DITAHAN = re.compile(r'KEPUTUSAN DITAHAN', re.IGNORECASE)
RE_TIMER_LINE = re.compile(r'^[\r\s]*⏳\s*\[')
RE_ORDER_OPEN = re.compile(r'OPEN (BUY|SELL)', re.IGNORECASE)
RE_ORDER_SUCCESS = re.compile(r'ORDER.+BERHASIL', re.IGNORECASE)
RE_BREAK_EVEN = re.compile(r'BREAK-EVEN', re.IGNORECASE)
RE_DETEKSI_EXIT = re.compile(r'DETEKSI EXIT', re.IGNORECASE)
RE_DYNAMIC_EXIT = re.compile(r'DYNAMIC EXIT', re.IGNORECASE)

MAX_HISTORY_ROWS = 200

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ AI Trading Bot Dashboard - SMC / LightGBM v3.3 Technical Confluence (M15 & M5)")
        self.root.geometry("1200x820")
        self.root.minsize(1050, 700)
        self.root.configure(bg="#0b0f19")

        # Status proses bot
        self.proc_m15 = None
        self.proc_m5  = None
        self.queue_m15 = queue.Queue()
        self.queue_m5  = queue.Queue()

        # Stopwatch state
        self.m15_start_time = None
        self.m5_start_time = None

        # Donut chart state
        self.m15_prob_buy = 50.0
        self.m15_prob_sell = 50.0
        self.m5_prob_buy = 50.0
        self.m5_prob_sell = 50.0

        # Last decision state
        self.m15_last_decision = "STANDBY"
        self.m5_last_decision = "STANDBY"

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
        self.root.after(500, self.update_stopwatches)
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

        lbl_title = tk.Label(title_box, text="⚡ AI TRADING BOT DASHBOARD v3.3", font=("Segoe UI", 16, "bold"), fg="#38bdf8", bg="#111827")
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(title_box, text="Multi-Indicator Technical Confluence (Stoch RSI, BB, EMA, SNR & Anti-Collision) | XAUUSD", font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
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
        self.notebook.add(self.tab_m15, text="  📊 Bot M15 (v3.3 Confluence)  ")
        self.setup_m15_tab()

        # TAB 2: BOT M5
        self.tab_m5 = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_m5, text="  ⚡ Bot M5 (v3.3 Confluence Scalper)  ")
        self.setup_m5_tab()

        # TAB 3: REKAP EXCEL & PORTOFOLIO
        self.tab_rekap = tk.Frame(self.notebook, bg="#0b0f19")
        self.notebook.add(self.tab_rekap, text="  📈 Rekap Transaksi & Hub Excel  ")
        self.setup_rekap_tab()

    # =========================================================================
    # DONUT CHART HELPER (Canvas-based ring chart)
    # =========================================================================
    def draw_donut_chart(self, canvas, prob_buy, prob_sell, size=160):
        """Draw a donut/ring chart on the given canvas showing BUY vs SELL probability."""
        canvas.delete("all")
        
        cx, cy = size / 2, size / 2
        outer_r = size / 2 - 8
        inner_r = outer_r * 0.55
        
        # Background circle (dark ring)
        canvas.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, fill="#1e293b", outline="#334155", width=2)
        
        # Draw arcs for BUY (green) and SELL (red)
        total = prob_buy + prob_sell
        if total <= 0:
            total = 100.0
        
        buy_extent = (prob_buy / total) * 360.0
        sell_extent = 360.0 - buy_extent
        
        # Determine dominant color
        if prob_buy >= prob_sell:
            dominant_color = "#10b981"
            secondary_color = "#ef4444"
            dominant_label = "BUY"
            dominant_pct = prob_buy
        else:
            dominant_color = "#ef4444"
            secondary_color = "#10b981"
            dominant_label = "SELL"
            dominant_pct = prob_sell
        
        # Draw SELL arc first (starts at top, goes clockwise)
        if sell_extent > 0.5:
            canvas.create_arc(
                cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                start=90, extent=-sell_extent, fill=secondary_color, outline=""
            )
        
        # Draw BUY arc on top
        if buy_extent > 0.5:
            canvas.create_arc(
                cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                start=90, extent=buy_extent, fill=dominant_color, outline=""
            )
        
        # Inner circle (hole) to create donut effect
        canvas.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r, fill="#0b0f19", outline="#0b0f19")
        
        # Center text: dominant percentage
        canvas.create_text(cx, cy - 8, text=f"{dominant_pct:.1f}%", font=("Segoe UI", 16, "bold"), fill=dominant_color)
        canvas.create_text(cx, cy + 14, text=dominant_label, font=("Segoe UI", 9, "bold"), fill="#94a3b8")

    # =========================================================================
    # DASHBOARD PANEL BUILDER (used by both M15 and M5 tabs)
    # =========================================================================
    def build_dashboard_panel(self, parent, bot_key, accent_color="#38bdf8"):
        """Build the right-side dashboard panel with Timer, Donut, and History Treeview.
        bot_key is 'm15' or 'm5'. Returns dict of widget references."""
        
        right_panel = tk.Frame(parent, bg="#0b0f19", relief="solid", bd=1)
        
        widgets = {}
        
        # ── ZONA 1: STATUS PANEL ATAS (Timer + Status + Last Decision) ──
        status_frame = tk.Frame(right_panel, bg="#111827", relief="solid", bd=1)
        status_frame.pack(fill="x", padx=8, pady=(8, 4))
        
        # Row 1: Title + Stopwatch
        row1 = tk.Frame(status_frame, bg="#111827")
        row1.pack(fill="x", padx=12, pady=(10, 4))
        
        tf_label = "M15 v3.0 MULTI-ZONE" if bot_key == "m15" else "M5 v3.0 SCALPER"
        tk.Label(row1, text=f"⏱️ MONITORING LIVE {tf_label}", font=("Segoe UI", 10, "bold"), fg=accent_color, bg="#111827").pack(side="left")
        
        timer_lbl = tk.Label(row1, text="00:00:00", font=("Consolas", 18, "bold"), fg="#f8fafc", bg="#111827")
        timer_lbl.pack(side="right", padx=(10, 0))
        widgets["timer"] = timer_lbl
        
        # Row 2: Status badge + Last decision
        row2 = tk.Frame(status_frame, bg="#111827")
        row2.pack(fill="x", padx=12, pady=(0, 10))
        
        status_lbl = tk.Label(row2, text="○ STANDBY", font=("Segoe UI", 9, "bold"), fg="#ef4444", bg="#1e293b", padx=10, pady=3)
        status_lbl.pack(side="left")
        widgets["status_lbl"] = status_lbl
        
        decision_lbl = tk.Label(row2, text="Keputusan Terakhir: —", font=("Segoe UI", 9), fg="#94a3b8", bg="#111827")
        decision_lbl.pack(side="right")
        widgets["decision_lbl"] = decision_lbl
        
        # ── ZONA 2: DONUT CHART + PROBABILITAS ──
        chart_frame = tk.Frame(right_panel, bg="#0b0f19")
        chart_frame.pack(fill="x", padx=8, pady=4)
        
        # Left: Donut Canvas
        donut_size = 160
        donut_canvas = tk.Canvas(chart_frame, width=donut_size, height=donut_size, bg="#0b0f19", highlightthickness=0)
        donut_canvas.pack(side="left", padx=(20, 10), pady=8)
        widgets["donut_canvas"] = donut_canvas
        
        # Right: Probability details
        prob_detail = tk.Frame(chart_frame, bg="#0b0f19")
        prob_detail.pack(side="left", fill="both", expand=True, padx=(10, 20), pady=12)
        
        tk.Label(prob_detail, text="PROBABILITAS AI MODEL", font=("Segoe UI", 10, "bold"), fg="#94a3b8", bg="#0b0f19").pack(anchor="w", pady=(0, 8))
        
        # BUY bar
        buy_bar_frame = tk.Frame(prob_detail, bg="#0b0f19")
        buy_bar_frame.pack(fill="x", pady=(0, 4))
        tk.Label(buy_bar_frame, text="🟢 BUY", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#0b0f19", width=8, anchor="w").pack(side="left")
        
        buy_bar_bg = tk.Frame(buy_bar_frame, bg="#1e293b", height=18)
        buy_bar_bg.pack(side="left", fill="x", expand=True, padx=(4, 0))
        buy_bar_bg.pack_propagate(False)
        buy_bar_fill = tk.Frame(buy_bar_bg, bg="#10b981", height=18)
        buy_bar_fill.place(relx=0, rely=0, relwidth=0.5, relheight=1.0)
        widgets["buy_bar_fill"] = buy_bar_fill
        
        buy_pct_lbl = tk.Label(buy_bar_frame, text="50.0%", font=("Consolas", 9, "bold"), fg="#10b981", bg="#0b0f19", width=7, anchor="e")
        buy_pct_lbl.pack(side="right", padx=(6, 0))
        widgets["buy_pct_lbl"] = buy_pct_lbl
        
        # SELL bar
        sell_bar_frame = tk.Frame(prob_detail, bg="#0b0f19")
        sell_bar_frame.pack(fill="x", pady=(0, 8))
        tk.Label(sell_bar_frame, text="🔴 SELL", font=("Segoe UI", 9, "bold"), fg="#ef4444", bg="#0b0f19", width=8, anchor="w").pack(side="left")
        
        sell_bar_bg = tk.Frame(sell_bar_frame, bg="#1e293b", height=18)
        sell_bar_bg.pack(side="left", fill="x", expand=True, padx=(4, 0))
        sell_bar_bg.pack_propagate(False)
        sell_bar_fill = tk.Frame(sell_bar_bg, bg="#ef4444", height=18)
        sell_bar_fill.place(relx=0, rely=0, relwidth=0.5, relheight=1.0)
        widgets["sell_bar_fill"] = sell_bar_fill
        
        sell_pct_lbl = tk.Label(sell_bar_frame, text="50.0%", font=("Consolas", 9, "bold"), fg="#ef4444", bg="#0b0f19", width=7, anchor="e")
        sell_pct_lbl.pack(side="right", padx=(6, 0))
        widgets["sell_pct_lbl"] = sell_pct_lbl
        
        # Trend info label
        trend_lbl = tk.Label(prob_detail, text="Tren H1: Memuat... | SNR: —", font=("Segoe UI", 8), fg="#64748b", bg="#0b0f19")
        trend_lbl.pack(anchor="w")
        widgets["trend_lbl"] = trend_lbl
        
        # Draw initial donut
        self.draw_donut_chart(donut_canvas, 50.0, 50.0, donut_size)
        
        # ── ZONA 3: RIWAYAT KEPUTUSAN (Treeview) ──
        history_frame = tk.Frame(right_panel, bg="#111827", relief="solid", bd=1)
        history_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        
        hist_header = tk.Frame(history_frame, bg="#111827")
        hist_header.pack(fill="x", padx=10, pady=(8, 4))
        
        tk.Label(hist_header, text="📋 RIWAYAT KEPUTUSAN BOT", font=("Segoe UI", 9, "bold"), fg="#94a3b8", bg="#111827").pack(side="left")
        
        hist_count_lbl = tk.Label(hist_header, text="0 entri", font=("Segoe UI", 8), fg="#64748b", bg="#111827")
        hist_count_lbl.pack(side="right", padx=(0, 4))
        widgets["hist_count_lbl"] = hist_count_lbl
        
        btn_clear = tk.Button(hist_header, text="🗑️ Bersihkan", font=("Segoe UI", 8), fg="#94a3b8", bg="#1e293b", relief="flat", cursor="hand2", padx=6, pady=2)
        btn_clear.pack(side="right", padx=4)
        
        # Treeview for history
        tree_box = tk.Frame(history_frame, bg="#111827")
        tree_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        hist_scroll = ttk.Scrollbar(tree_box, orient="vertical")
        hist_scroll.pack(side="right", fill="y")
        
        hist_cols = ("waktu", "aksi", "buy_pct", "sell_pct", "detail")
        hist_tree = ttk.Treeview(tree_box, columns=hist_cols, show="headings", yscrollcommand=hist_scroll.set, height=8)
        hist_tree.pack(fill="both", expand=True)
        hist_scroll.config(command=hist_tree.yview)
        
        hist_tree.heading("waktu", text="Waktu")
        hist_tree.heading("aksi", text="Aksi")
        hist_tree.heading("buy_pct", text="BUY %")
        hist_tree.heading("sell_pct", text="SELL %")
        hist_tree.heading("detail", text="Detail / Alasan")
        
        hist_tree.column("waktu", width=75, anchor="center")
        hist_tree.column("aksi", width=75, anchor="center")
        hist_tree.column("buy_pct", width=60, anchor="center")
        hist_tree.column("sell_pct", width=60, anchor="center")
        hist_tree.column("detail", width=300, anchor="w", stretch=True)
        
        hist_tree.tag_configure("buy", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        hist_tree.tag_configure("sell", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        hist_tree.tag_configure("netral", foreground="#f59e0b", font=("Segoe UI", 9))
        hist_tree.tag_configure("ditahan", foreground="#f59e0b", font=("Segoe UI", 9))
        hist_tree.tag_configure("info", foreground="#38bdf8", font=("Segoe UI", 9))
        hist_tree.tag_configure("system", foreground="#94a3b8", font=("Segoe UI", 8))
        
        widgets["hist_tree"] = hist_tree
        
        # Wire clear button
        btn_clear.config(command=lambda: self._clear_history(hist_tree, hist_count_lbl))
        
        return right_panel, widgets

    def _clear_history(self, tree, count_lbl):
        for item in tree.get_children():
            tree.delete(item)
        count_lbl.config(text="0 entri")

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

        # Panel Kanan: Dashboard (Timer + Donut + History)
        right_panel, self.m15_widgets = self.build_dashboard_panel(paned, "m15", accent_color="#38bdf8")
        paned.add(right_panel)

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

        # Panel Kanan: Dashboard (Timer + Donut + History)
        right_panel, self.m5_widgets = self.build_dashboard_panel(paned, "m5", accent_color="#10b981")
        paned.add(right_panel)

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

    def create_footer(self):
        footer = tk.Frame(self.root, bg="#0b0f19", height=25)
        footer.pack(fill="x", padx=15, pady=(0, 8))
        tk.Label(footer, text="💡 Tip: Anda dapat menyalakan Bot M15 dan Bot M5 secara independen. Data log dan Excel selalu tersinkronisasi otomatis.", font=("Segoe UI", 8), fg="#64748b", bg="#0b0f19").pack(side="left")

    # =========================================================================
    # STOPWATCH TIMER UPDATE (Real-time loop setiap detik)
    # =========================================================================
    def update_stopwatches(self):
        """Update stopwatch timers for both M15 and M5 bots every second."""
        now = time.time()

        # M15 stopwatch
        if self.m15_start_time is not None:
            elapsed = int(now - self.m15_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.m15_widgets["timer"].config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#10b981")
        else:
            self.m15_widgets["timer"].config(text="00:00:00", fg="#64748b")

        # M5 stopwatch
        if self.m5_start_time is not None:
            elapsed = int(now - self.m5_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.m5_widgets["timer"].config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#10b981")
        else:
            self.m5_widgets["timer"].config(text="00:00:00", fg="#64748b")

        self.root.after(1000, self.update_stopwatches)

    # =========================================================================
    # DASHBOARD UPDATE HELPERS
    # =========================================================================
    def update_donut_and_bars(self, bot_key, prob_buy, prob_sell):
        """Update the donut chart and probability bars for the given bot."""
        widgets = self.m15_widgets if bot_key == "m15" else self.m5_widgets

        # Store state
        if bot_key == "m15":
            self.m15_prob_buy = prob_buy
            self.m15_prob_sell = prob_sell
        else:
            self.m5_prob_buy = prob_buy
            self.m5_prob_sell = prob_sell

        # Update donut chart
        self.draw_donut_chart(widgets["donut_canvas"], prob_buy, prob_sell, 160)

        # Update bar fills
        total = prob_buy + prob_sell
        if total <= 0:
            total = 100.0
        buy_ratio = prob_buy / total
        sell_ratio = prob_sell / total

        widgets["buy_bar_fill"].place(relx=0, rely=0, relwidth=max(0.02, buy_ratio), relheight=1.0)
        widgets["sell_bar_fill"].place(relx=0, rely=0, relwidth=max(0.02, sell_ratio), relheight=1.0)

        widgets["buy_pct_lbl"].config(text=f"{prob_buy:.1f}%")
        widgets["sell_pct_lbl"].config(text=f"{prob_sell:.1f}%")

    def add_decision_history(self, bot_key, aksi, detail, prob_buy=None, prob_sell=None, tag="info"):
        """Add a row to the decision history Treeview for the given bot."""
        widgets = self.m15_widgets if bot_key == "m15" else self.m5_widgets
        tree = widgets["hist_tree"]
        count_lbl = widgets["hist_count_lbl"]

        waktu = datetime.now().strftime("%H:%M:%S")
        buy_str = f"{prob_buy:.1f}%" if prob_buy is not None else "—"
        sell_str = f"{prob_sell:.1f}%" if prob_sell is not None else "—"

        # Insert at top (terbaru di atas)
        tree.insert("", 0, values=(waktu, aksi, buy_str, sell_str, detail), tags=(tag,))

        # Update decision label
        decision_color = "#10b981" if tag == "buy" else ("#ef4444" if tag == "sell" else "#f59e0b")
        widgets["decision_lbl"].config(text=f"Keputusan Terakhir: {aksi} ({waktu})", fg=decision_color)

        # Auto-prune jika melebihi batas
        children = tree.get_children()
        if len(children) > MAX_HISTORY_ROWS:
            for old_item in children[MAX_HISTORY_ROWS:]:
                tree.delete(old_item)

        count_lbl.config(text=f"{len(tree.get_children())} entri")

    def update_dashboard_status(self, bot_key, is_active):
        """Update the status label in the dashboard panel."""
        widgets = self.m15_widgets if bot_key == "m15" else self.m5_widgets
        if is_active:
            widgets["status_lbl"].config(text="● AKTIF", fg="#10b981", bg="#064e3b")
        else:
            widgets["status_lbl"].config(text="○ STANDBY", fg="#ef4444", bg="#1e293b")

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

            self.m15_start_time = time.time()
            self.m15_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m15.config(state="disabled", bg="#064e3b")
            self.btn_stop_m15.config(state="normal", bg="#ef4444")
            self.update_dashboard_status("m15", True)
            self.add_decision_history("m15", "SYSTEM", "🚀 Bot M15 Konservatif Berhasil Dinyalakan!", tag="info")
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
        self.m15_start_time = None
        self.m15_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m15.config(state="normal", bg="#10b981")
        self.btn_stop_m15.config(state="disabled", bg="#7f1d1d")
        self.update_dashboard_status("m15", False)
        if manual:
            self.add_decision_history("m15", "STOP", "🛑 Bot M15 Telah Dihentikan oleh Pengguna.", tag="system")
        else:
            self.add_decision_history("m15", "CRASH", f"⚠️ Bot M15 Terhenti Otomatis (Exit Code: {exit_code}).", tag="sell")

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

            self.m5_start_time = time.time()
            self.m5_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m5.config(state="disabled", bg="#064e3b")
            self.btn_stop_m5.config(state="normal", bg="#ef4444")
            self.update_dashboard_status("m5", True)
            self.add_decision_history("m5", "SYSTEM", "🚀 Bot M5 Level Bounce Scalper Berhasil Dinyalakan!", tag="info")
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
        self.m5_start_time = None
        self.m5_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m5.config(state="normal", bg="#10b981")
        self.btn_stop_m5.config(state="disabled", bg="#7f1d1d")
        self.update_dashboard_status("m5", False)
        if manual:
            self.add_decision_history("m5", "STOP", "🛑 Bot M5 Telah Dihentikan oleh Pengguna.", tag="system")
        else:
            self.add_decision_history("m5", "CRASH", f"⚠️ Bot M5 Terhenti Otomatis (Exit Code: {exit_code}).", tag="sell")

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
            self.parse_and_route_output("m15", line)

        # Cek jika proses M15 tiba-tiba keluar
        if self.proc_m15 is not None and self.proc_m15.poll() is not None:
            self.stop_bot_m15(manual=False)

        # Proses antrian log M5
        while not self.queue_m5.empty():
            line = self.queue_m5.get_nowait()
            self.parse_and_route_output("m5", line)

        # Cek jika proses M5 tiba-tiba keluar
        if self.proc_m5 is not None and self.proc_m5.poll() is not None:
            self.stop_bot_m5(manual=False)

        self.root.after(100, self.process_log_queues)

    def parse_and_route_output(self, bot_key, raw_line):
        """Parse bot output and route to appropriate dashboard component.
        
        Routing logic:
        - Timer lines (⏳): Extract BUY/SELL probabilities → update donut chart. Don't show.
        - Decision lines (KEPUTUSAN): Extract action & detail → add to history Treeview.
        - Order lines (OPEN BUY/SELL, BERHASIL): Add to history.
        - Break-even, exit detection: Add to history as info.
        - Other lines: Silently skip (init messages, separator lines, etc.)
        """
        clean_text = ANSI_PATTERN.sub('', raw_line).strip()
        if not clean_text:
            return

        # 1. TIMER LINES: Extract probabilities silently
        if RE_TIMER_LINE.match(raw_line.lstrip()):
            prob_match = RE_PROB_LIVE.search(clean_text)
            if prob_match:
                try:
                    pb = float(prob_match.group(1))
                    ps = float(prob_match.group(2))
                    self.update_donut_and_bars(bot_key, pb, ps)

                    # Also extract trend/status info from the timer line
                    widgets = self.m15_widgets if bot_key == "m15" else self.m5_widgets
                    # Extract H1 trend if present
                    trend_text = ""
                    if "H1:Bull" in clean_text:
                        trend_text = "Tren H1: 📈 BULLISH"
                    elif "H1:Bear" in clean_text:
                        trend_text = "Tren H1: 📉 BEARISH"

                    # Extract status
                    status_text = ""
                    if "HOLDING BUY" in clean_text:
                        status_text = " | 🟢 HOLDING BUY"
                    elif "HOLDING SELL" in clean_text:
                        status_text = " | 🔴 HOLDING SELL"
                    elif "ACTIVE BUY" in clean_text:
                        status_text = " | 🟢 ACTIVE BUY"
                    elif "ACTIVE SELL" in clean_text:
                        status_text = " | 🔴 ACTIVE SELL"
                    elif "SIAP BUY" in clean_text:
                        status_text = " | ⚡ SIAP BUY"
                    elif "SIAP SELL" in clean_text:
                        status_text = " | ⚡ SIAP SELL"
                    elif "TERTAHAN" in clean_text:
                        status_text = " | ⏸️ TERTAHAN"
                    elif "NETRAL" in clean_text or "WAIT" in clean_text:
                        status_text = " | ⏳ NETRAL/WAIT"
                    elif "AREA DEMAND" in clean_text:
                        status_text = " | 📍 AREA DEMAND"
                    elif "AREA SUPPLY" in clean_text:
                        status_text = " | 📍 AREA SUPPLY"
                    elif "MID-TREND" in clean_text:
                        status_text = " | ⏸️ MID-TREND"
                    elif "NEWS" in clean_text or "MAKRO" in clean_text:
                        status_text = " | 🛑 NEWS FREEZE"

                    if trend_text or status_text:
                        widgets["trend_lbl"].config(text=f"{trend_text}{status_text}")
                except (ValueError, IndexError):
                    pass
            return  # Don't add timer lines to history

        # 2. DECISION LINES (KEPUTUSAN BUY/SELL/NETRAL/DITAHAN)
        if RE_DECISION_BUY.search(clean_text):
            prob_match = RE_PROB_LIVE.search(clean_text)
            pb = float(prob_match.group(1)) if prob_match else None
            ps = float(prob_match.group(2)) if prob_match else None
            self.add_decision_history(bot_key, "🟢 BUY", clean_text[:120], prob_buy=pb, prob_sell=ps, tag="buy")
            if bot_key == "m15":
                self.m15_last_decision = "BUY"
            else:
                self.m5_last_decision = "BUY"
            return

        if RE_DECISION_SELL.search(clean_text):
            prob_match = RE_PROB_LIVE.search(clean_text)
            pb = float(prob_match.group(1)) if prob_match else None
            ps = float(prob_match.group(2)) if prob_match else None
            self.add_decision_history(bot_key, "🔴 SELL", clean_text[:120], prob_buy=pb, prob_sell=ps, tag="sell")
            if bot_key == "m15":
                self.m15_last_decision = "SELL"
            else:
                self.m5_last_decision = "SELL"
            return

        if RE_DECISION_NETRAL.search(clean_text):
            prob_match = RE_PROB_LIVE.search(clean_text)
            pb = float(prob_match.group(1)) if prob_match else None
            ps = float(prob_match.group(2)) if prob_match else None
            self.add_decision_history(bot_key, "🟡 NETRAL", clean_text[:120], prob_buy=pb, prob_sell=ps, tag="netral")
            if bot_key == "m15":
                self.m15_last_decision = "NETRAL"
            else:
                self.m5_last_decision = "NETRAL"
            return

        if RE_DECISION_DITAHAN.search(clean_text):
            prob_match = RE_PROB_LIVE.search(clean_text)
            pb = float(prob_match.group(1)) if prob_match else None
            ps = float(prob_match.group(2)) if prob_match else None
            # Extract reason from parentheses
            reason_match = re.search(r'DITAHAN\s*\(([^)]+)\)', clean_text)
            reason = reason_match.group(1) if reason_match else "Filter Aktif"
            self.add_decision_history(bot_key, f"⏸️ DITAHAN", f"[{reason}] {clean_text[:100]}", prob_buy=pb, prob_sell=ps, tag="ditahan")
            return

        # 3. ORDER EXECUTION LINES
        if RE_ORDER_OPEN.search(clean_text):
            order_type = "BUY" if "BUY" in clean_text.upper().split("OPEN")[1][:10] else "SELL"
            tag = "buy" if order_type == "BUY" else "sell"
            self.add_decision_history(bot_key, f"🚀 OPEN {order_type}", clean_text[:120], tag=tag)
            return

        if RE_ORDER_SUCCESS.search(clean_text):
            self.add_decision_history(bot_key, "✅ BERHASIL", clean_text[:120], tag="buy")
            return

        # 4. BREAK-EVEN & EXIT DETECTION
        if RE_BREAK_EVEN.search(clean_text):
            self.add_decision_history(bot_key, "🛡️ BE GUARD", clean_text[:120], tag="info")
            return

        if RE_DETEKSI_EXIT.search(clean_text) or RE_DYNAMIC_EXIT.search(clean_text):
            self.add_decision_history(bot_key, "🔔 EXIT", clean_text[:120], tag="info")
            return

        # 5. PROBABILITY UPDATE LINES (from analysis output, not timer)
        prob_match = RE_PROB_LIVE.search(clean_text)
        if prob_match and ("Probabilitas" in clean_text or "probabilitas" in clean_text):
            try:
                pb = float(prob_match.group(1))
                ps = float(prob_match.group(2))
                self.update_donut_and_bars(bot_key, pb, ps)
                self.add_decision_history(bot_key, "📊 ANALISA", f"BUY={pb:.1f}% SELL={ps:.1f}% {clean_text[:80]}", prob_buy=pb, prob_sell=ps, tag="info")
            except (ValueError, IndexError):
                pass
            return

        # 6. CANDLE TUTUP notification
        if "CANDLE" in clean_text and ("TUTUP" in clean_text or "MENJELANG" in clean_text):
            self.add_decision_history(bot_key, "⚡ CANDLE", clean_text[:120], tag="info")
            return

        # 7. SYNC and other informational lines - show only important ones
        if "SYNC" in clean_text.upper() or "sinkron" in clean_text.lower():
            # Skip silent sync messages, only show explicit ones
            if "silent" not in clean_text.lower() and "Berhasil" in clean_text:
                self.add_decision_history(bot_key, "🔄 SYNC", clean_text[:120], tag="system")
            return

        # 8. Error / failure messages
        if "❌" in clean_text or "Gagal" in clean_text or "ERROR" in clean_text.upper():
            self.add_decision_history(bot_key, "❌ ERROR", clean_text[:120], tag="sell")
            return

        # 9. All other lines are silently consumed (separator lines, init messages, etc.)
        # Only log genuinely important ones
        if any(keyword in clean_text for keyword in ["Terhubung", "Berhasil Dimuat", "ROBOT TRADING"]):
            self.add_decision_history(bot_key, "ℹ️ INFO", clean_text[:120], tag="system")


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
