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

        # Tombol Buka Excel M15
        btn_excel_m15 = tk.Button(left_panel, text="📊 Buka Laporan Excel M15", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#1e293b", activebackground="#334155", activeforeground="#38bdf8", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else messagebox.showerror("File Error", "File Excel M15 belum ditemukan!"), pady=6)
        btn_excel_m15.pack(fill="x", padx=15, side="bottom", pady=15)

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

        # Tombol Buka Excel M5
        btn_excel_m5 = tk.Button(left_panel, text="⚡ Buka Laporan Excel M5", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#1e293b", activebackground="#334155", activeforeground="#10b981", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else messagebox.showerror("File Error", "File Excel M5 belum ditemukan!"), pady=6)
        btn_excel_m5.pack(fill="x", padx=15, side="bottom", pady=15)

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
    def setup_rekap_tab(self):
        container = tk.Frame(self.tab_rekap, bg="#0b0f19")
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Kartu Rekap Atas
        cards_frame = tk.Frame(container, bg="#0b0f19")
        cards_frame.pack(fill="x", pady=(0, 20))

        # Kartu M15
        card_m15 = tk.Frame(cards_frame, bg="#161f30", relief="solid", bd=1, padx=20, pady=15)
        card_m15.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(card_m15, text="PORTOFOLIO MODEL M15 (KONSERVATIF)", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#161f30").pack(anchor="w")
        self.lbl_rekap_m15 = tk.Label(card_m15, text="Memuat riwayat MT5...", font=("Consolas", 10), fg="#f8fafc", bg="#161f30", justify="left")
        self.lbl_rekap_m15.pack(anchor="w", pady=(8, 10))
        tk.Button(card_m15, text="Buka File Excel M15 (.xlsx)", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else None).pack(anchor="w")

        # Kartu M5
        card_m5 = tk.Frame(cards_frame, bg="#161f30", relief="solid", bd=1, padx=20, pady=15)
        card_m5.pack(side="right", fill="both", expand=True, padx=(10, 0))
        tk.Label(card_m5, text="PORTOFOLIO MODEL M5 (SCALPING DYNAMIC)", font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#161f30").pack(anchor="w")
        self.lbl_rekap_m5 = tk.Label(card_m5, text="Memuat riwayat MT5...", font=("Consolas", 10), fg="#f8fafc", bg="#161f30", justify="left")
        self.lbl_rekap_m5.pack(anchor="w", pady=(8, 10))
        tk.Button(card_m5, text="Buka File Excel M5 (.xlsx)", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#059669", activebackground="#047857", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else None).pack(anchor="w")

        # Tabel Riwayat Transaksi Terakhir
        table_frame = tk.Frame(container, bg="#161f30", relief="solid", bd=1, padx=15, pady=15)
        table_frame.pack(fill="both", expand=True)

        tbl_top = tk.Frame(table_frame, bg="#161f30")
        tbl_top.pack(fill="x", pady=(0, 10))
        tk.Label(tbl_top, text="DAFTAR 15 TRANSAKSI MT5 TERAKHIR (LIVE SYNC)", font=("Segoe UI", 10, "bold"), fg="#f8fafc", bg="#161f30").pack(side="left")
        tk.Button(tbl_top, text="🔄 Refresh Data", font=("Segoe UI", 8), fg="#38bdf8", bg="#1e293b", relief="flat", cursor="hand2", command=self.refresh_rekap_data).pack(side="right")

        columns = ("waktu", "magic", "tipe", "lot", "open_p", "close_p", "profit", "comment")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        
        self.tree.heading("waktu", text="Waktu Selesai (WIB)")
        self.tree.heading("magic", text="Model")
        self.tree.heading("tipe", text="Arah")
        self.tree.heading("lot", text="Lot")
        self.tree.heading("open_p", text="Harga Masuk")
        self.tree.heading("close_p", text="Harga Keluar")
        self.tree.heading("profit", text="Profit (USD)")
        self.tree.heading("comment", text="Alasan Exit")

        self.tree.column("waktu", width=140, anchor="center")
        self.tree.column("magic", width=110, anchor="center")
        self.tree.column("tipe", width=70, anchor="center")
        self.tree.column("lot", width=60, anchor="center")
        self.tree.column("open_p", width=95, anchor="center")
        self.tree.column("close_p", width=95, anchor="center")
        self.tree.column("profit", width=100, anchor="center")
        self.tree.column("comment", width=220, anchor="w")

        self.tree.pack(fill="both", expand=True)

        self.refresh_rekap_data()

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
            self.proc_m15 = subprocess.Popen(
                [PYTHON_EXE, "-u", SCRIPT_M15],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            threading.Thread(target=self.reader_thread, args=(self.proc_m15, self.queue_m15), daemon=True).start()

            self.m15_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m15.config(state="disabled", bg="#064e3b")
            self.btn_stop_m15.config(state="normal", bg="#ef4444")
            self.append_log(self.log_text_m15, "🚀 [SYSTEM] Bot M15 Konservatif Berhasil Dinyalakan!\n", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyalakan Bot M15: {e}")

    def stop_bot_m15(self):
        if self.proc_m15 is not None and self.proc_m15.poll() is None:
            try:
                self.proc_m15.terminate()
                self.proc_m15.wait(timeout=2)
            except Exception:
                self.proc_m15.kill()

        self.proc_m15 = None
        self.m15_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m15.config(state="normal", bg="#10b981")
        self.btn_stop_m15.config(state="disabled", bg="#7f1d1d")
        self.append_log(self.log_text_m15, "\n🛑 [SYSTEM] Bot M15 Telah Dihentikan oleh Pengguna.\n", "red")

    def start_bot_m5(self):
        if self.proc_m5 is not None and self.proc_m5.poll() is None:
            messagebox.showinfo("Info", "Bot M5 sudah dalam keadaan berjalan!")
            return

        try:
            self.proc_m5 = subprocess.Popen(
                [PYTHON_EXE, "-u", SCRIPT_M5],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=BASE_DIR,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            threading.Thread(target=self.reader_thread, args=(self.proc_m5, self.queue_m5), daemon=True).start()

            self.m5_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
            self.btn_start_m5.config(state="disabled", bg="#064e3b")
            self.btn_stop_m5.config(state="normal", bg="#ef4444")
            self.append_log(self.log_text_m5, "🚀 [SYSTEM] Bot M5 Level Bounce Scalper Berhasil Dinyalakan!\n", "green")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyalakan Bot M5: {e}")

    def stop_bot_m5(self):
        if self.proc_m5 is not None and self.proc_m5.poll() is None:
            try:
                self.proc_m5.terminate()
                self.proc_m5.wait(timeout=2)
            except Exception:
                self.proc_m5.kill()

        self.proc_m5 = None
        self.m5_status_badge.config(text="○ STATUS: NONAKTIF / STANDBY", fg="#ef4444", bg="#223049")
        self.btn_start_m5.config(state="normal", bg="#10b981")
        self.btn_stop_m5.config(state="disabled", bg="#7f1d1d")
        self.append_log(self.log_text_m5, "\n🛑 [SYSTEM] Bot M5 Telah Dihentikan oleh Pengguna.\n", "red")

    def reader_thread(self, proc, out_queue):
        try:
            for line in iter(proc.stdout.readline, ''):
                if not line:
                    break
                out_queue.put(line)
        except Exception:
            pass
        finally:
            proc.stdout.close()

    def process_log_queues(self):
        # Proses antrian log M15
        while not self.queue_m15.empty():
            line = self.queue_m15.get_nowait()
            self.parse_and_insert_log(self.log_text_m15, line)

        # Cek jika proses M15 tiba-tiba keluar
        if self.proc_m15 is not None and self.proc_m15.poll() is not None:
            self.stop_bot_m15()

        # Proses antrian log M5
        while not self.queue_m5.empty():
            line = self.queue_m5.get_nowait()
            self.parse_and_insert_log(self.log_text_m5, line)

        # Cek jika proses M5 tiba-tiba keluar
        if self.proc_m5 is not None and self.proc_m5.poll() is not None:
            self.stop_bot_m5()

        self.root.after(100, self.process_log_queues)

    def parse_and_insert_log(self, text_widget, raw_line):
        # Jika carriage return '\r' dari baris countdown timer
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

        # Update tampilan
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

    def refresh_rekap_data(self):
        try:
            if not mt5.initialize(path=MT5_PATH):
                return
            
            # Ambil deals 3 hari terakhir
            deals = mt5.history_deals_get(datetime.now() - timedelta(days=3), datetime.now())
            if not deals:
                return

            # Clear Treeview
            for item in self.tree.get_children():
                self.tree.delete(item)

            deals_out = [d for d in deals if d.entry == 1 and d.magic in [123230, 123235]]
            deals_out.sort(key=lambda x: x.time, reverse=True)

            m15_wins, m15_loss, m15_pnl = 0, 0, 0.0
            m5_wins,  m5_loss,  m5_pnl  = 0, 0, 0.0

            for d in deals_out:
                if d.magic == 123230:
                    m15_pnl += d.profit
                    if d.profit > 0: m15_wins += 1
                    elif d.profit < 0: m15_loss += 1
                elif d.magic == 123235:
                    m5_pnl += d.profit
                    if d.profit > 0: m5_wins += 1
                    elif d.profit < 0: m5_loss += 1

            # Update Label Rekap M15
            m15_tot = m15_wins + m15_loss
            m15_wr = (m15_wins / m15_tot * 100) if m15_tot > 0 else 0
            self.lbl_rekap_m15.config(
                text=f"Total Trade : {m15_tot} Transaksi\nWin / Loss  : {m15_wins} WIN / {m15_loss} LOSS\nWin Rate    : {m15_wr:.1f}%\nNet PnL     : ${m15_pnl:+.2f} USD"
            )

            # Update Label Rekap M5
            m5_tot = m5_wins + m5_loss
            m5_wr = (m5_wins / m5_tot * 100) if m5_tot > 0 else 0
            self.lbl_rekap_m5.config(
                text=f"Total Trade : {m5_tot} Transaksi\nWin / Loss  : {m5_wins} WIN / {m5_loss} LOSS\nWin Rate    : {m5_wr:.1f}%\nNet PnL     : ${m5_pnl:+.2f} USD"
            )

            # Isi Treeview 15 transaksi terakhir
            for d in deals_out[:15]:
                dt_str = datetime.fromtimestamp(d.time).strftime("%d/%m/%y %H:%M:%S")
                model_name = "M15 Konservatif" if d.magic == 123230 else "M5 Scalper"
                dir_str = "BUY" if d.type == 0 else "SELL"
                pnl_str = f"${d.profit:+.2f}"

                self.tree.insert("", "end", values=(
                    dt_str, model_name, dir_str, f"{d.volume:.2f}",
                    f"${d.price:.2f}", f"${d.price:.2f}", pnl_str, d.comment
                ))

        except Exception as e:
            print(f"Error refresh rekap: {e}")

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
