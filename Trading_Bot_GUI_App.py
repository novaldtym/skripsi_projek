import os
import sys
import time
import math
import subprocess
import threading
import queue
import re
import json
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox
import MetaTrader5 as mt5
import pandas as pd
import webbrowser
import socket
from PIL import Image, ImageTk
import qrcode

# Path konfigurasi & Standalone EXE Support
import shutil
if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    BASE_DIR = exe_dir if os.path.exists(os.path.join(exe_dir, "Eksekusi_Otomatis_Trading_Bot.py")) else r"d:\SKRIPSI INFORMATIKA"
    PYTHON_EXE = shutil.which("python") or shutil.which("pythonw") or r"C:\Users\nouval\AppData\Local\Programs\Python\Python313\python.exe"
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Eksekusi_Otomatis_Trading_Bot.py")) else r"d:\SKRIPSI INFORMATIKA"
    PYTHON_EXE = sys.executable
SCRIPT_M15 = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot.py")
SCRIPT_M5  = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py")
SCRIPT_WEB = os.path.join(BASE_DIR, "Web_Dashboard_Server.py")
EXCEL_M15  = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx")
EXCEL_M5   = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_M5_Scalping.xlsx")
CSV_EVAL   = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.csv")
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

def safe_load_excel_sheets(file_path):
    """Membaca sheet Excel secara aman bahkan saat file sedang dibuka/dikunci di Microsoft Excel."""
    if not os.path.exists(file_path):
        return None, []
    try:
        xl = pd.ExcelFile(file_path)
        return xl, list(xl.sheet_names)
    except Exception:
        try:
            import tempfile, shutil
            tmp_path = os.path.join(tempfile.gettempdir(), f"gui_read_{os.path.basename(file_path)}")
            shutil.copyfile(file_path, tmp_path)
            xl = pd.ExcelFile(tmp_path)
            return xl, list(xl.sheet_names)
        except Exception:
            return None, []

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ OBSIDIAN TERMINAL — AI Trading Bot Dashboard v4.1 (M15 & M5)")
        self.root.geometry("1200x820")
        self.root.minsize(1050, 700)
        self.root.configure(bg="#0d0e13")

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

        # Data & Mode Perjalanan Portofolio & Diagnosa
        self.porto_curve_mode = "equity"
        self.porto_points = []
        self.porto_trades = []
        self.diag_data = []
        self.diag_filter_status = "ALL"
        self.diag_filter_skenario = "ALL"
        self.diag_search_var = tk.StringVar()

        self.setup_styles()
        self.create_main_layout()

        # Mulai loop background polling
        self.root.after(100, self.process_log_queues)
        self.root.after(1000, self.update_live_market_ticker)
        self.root.after(500, self.update_stopwatches)
        self.root.after(3000, self.periodic_excel_rekap_refresh)
        self.root.after(500, self.poll_live_telemetry)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background="#0d0e13")
        style.configure("Card.TFrame", background="#13141a", relief="solid", borderwidth=1)

        # Styling Treeview Dark Theme
        style.configure("Treeview", 
                        background="#13141a", 
                        foreground="#ffffff", 
                        fieldbackground="#13141a",
                        rowheight=26,
                        font=("Segoe UI", 9))
        style.configure("Treeview.Heading", 
                        background="#24252c", 
                        foreground="#38bdf8", 
                        font=("Segoe UI", 9, "bold"),
                        padding=[6, 6])
        style.map("Treeview.Heading", 
                  background=[("active", "#2e3038")])
        style.map("Treeview", 
                  background=[("selected", "#0284c7")],
                  foreground=[("selected", "#ffffff")])

    def create_main_layout(self):
        """Membuat tata letak Obsidian Terminal dengan Navigasi Sidebar Kiri Tetap & Area Konten Kanan."""
        self.main_container = tk.Frame(self.root, bg="#0d0e13")
        self.main_container.pack(fill="both", expand=True)

        # 1. SIDEBAR KIRI TETAP (Width: 240px)
        self.create_left_sidebar(self.main_container)

        # 2. CONTAINER KANAN (Header Telemetri + Konten Multi-Pane + Footer)
        self.right_container = tk.Frame(self.main_container, bg="#0d0e13")
        self.right_container.pack(side="left", fill="both", expand=True)

        # Header atas kanan
        self.create_top_header(self.right_container)

        # Container konten untuk 6 panel
        self.content_container = tk.Frame(self.right_container, bg="#0d0e13")
        self.content_container.pack(fill="both", expand=True, padx=12, pady=(0, 4))

        # Footer bawah
        self.create_footer(self.right_container)

        # Inisialisasi 6 Panel Tampilan
        self.panes = {}
        self.tab_m15    = tk.Frame(self.content_container, bg="#0d0e13")
        self.tab_m5     = tk.Frame(self.content_container, bg="#0d0e13")
        self.tab_porto  = tk.Frame(self.content_container, bg="#0d0e13")
        self.tab_diag   = tk.Frame(self.content_container, bg="#0d0e13")
        self.tab_rekap  = tk.Frame(self.content_container, bg="#0d0e13")
        self.tab_params = tk.Frame(self.content_container, bg="#0d0e13")

        self.panes["m15"]    = self.tab_m15
        self.panes["m5"]     = self.tab_m5
        self.panes["porto"]  = self.tab_porto
        self.panes["diag"]   = self.tab_diag
        self.panes["rekap"]  = self.tab_rekap
        self.panes["params"] = self.tab_params

        self.setup_m15_tab()
        self.setup_m5_tab()
        self.setup_porto_tab()
        self.setup_diag_tab()
        self.setup_rekap_tab()
        self.setup_params_tab()

        # Tampilan awal default: Bot M15
        self.switch_nav("m15")

    def create_left_sidebar(self, parent):
        """Membuat panel sidebar kiri Obsidian Terminal dengan Navigasi Vertikal & Status Badges."""
        self.sidebar = tk.Frame(parent, bg="#13141a", width=250, relief="solid", bd=1)
        self.sidebar.pack_propagate(False)
        self.sidebar.pack(side="left", fill="y")

        # Top Branding
        brand_box = tk.Frame(self.sidebar, bg="#13141a", padx=16, pady=16)
        brand_box.pack(fill="x")
        tk.Label(brand_box, text="ALGORITHMIC CORE", font=("Segoe UI", 11, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")
        tk.Label(brand_box, text="v4.1 AUTO EXECUTION", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#13141a").pack(anchor="w", pady=(2, 0))

        sep = tk.Frame(self.sidebar, bg="#24252c", height=1)
        sep.pack(fill="x", padx=12, pady=(0, 10))

        # List Navigasi Vertikal
        nav_box = tk.Frame(self.sidebar, bg="#13141a")
        nav_box.pack(fill="x")
        self.nav_items = {}

        self.m15_sidebar_badge = self.create_nav_item(nav_box, "m15", "Bot M15 (v4.1 SMC RRR)", badge_text="STANDBY", badge_bg="#24252c", badge_fg="#8e9192")
        self.m5_sidebar_badge  = self.create_nav_item(nav_box, "m5", "Bot M5 (v4.1 Scalper)", badge_text="READY", badge_bg="#24252c", badge_fg="#8e9192")
        self.create_nav_item(nav_box, "porto", "Perjalanan Portofolio", badge_text="PRO", badge_bg="#1e293b", badge_fg="#38bdf8")
        self.diag_sidebar_badge = self.create_nav_item(nav_box, "diag", "Diagnosa Menang/Kalah", badge_text="14", badge_bg="#24252c", badge_fg="#c4c7c8")
        self.create_nav_item(nav_box, "rekap", "Rekap Transaksi", badge_text="XLSX", badge_bg="#14532d", badge_fg="#10b981")
        self.create_nav_item(nav_box, "params", "Parameter & Skripsi", badge_text="INFO", badge_bg="#24252c", badge_fg="#8e9192")

        # Bottom Intelligence Widget
        intel_card = tk.Frame(self.sidebar, bg="#1a1b21", relief="solid", bd=1, padx=12, pady=10)
        intel_card.pack(side="bottom", fill="x", padx=12, pady=12)

        i_head = tk.Frame(intel_card, bg="#1a1b21")
        i_head.pack(fill="x", pady=(0, 4))
        tk.Label(i_head, text="CORE INTELLIGENCE", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left")
        tk.Label(i_head, text="⚙", font=("Segoe UI", 9), fg="#8e9192", bg="#1a1b21").pack(side="right")

        tk.Label(intel_card, text="SMC & H4 Bias:", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21").pack(anchor="w")
        tk.Label(intel_card, text="BULLISH SWEEP", font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#1a1b21").pack(anchor="w", pady=(1, 4))

        conf_row = tk.Frame(intel_card, bg="#1a1b21")
        conf_row.pack(fill="x", pady=(0, 8))
        tk.Label(conf_row, text="Confidence:", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21").pack(side="left")
        tk.Label(conf_row, text="95.0%", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#1a1b21").pack(side="right")

        btn_hp = tk.Button(intel_card, text="📱 QR Akses HP", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.open_web_mobile_dialog, pady=4)
        btn_hp.pack(fill="x")

    def create_nav_item(self, parent, key, label, badge_text=None, badge_bg="#24252c", badge_fg="#8e9192"):
        """Item tombol sidebar dengan hover halus dan badge pill."""
        item_frame = tk.Frame(parent, bg="#13141a", cursor="hand2", padx=12, pady=9)
        item_frame.pack(fill="x", padx=6, pady=2)

        accent_bar = tk.Frame(item_frame, bg="#13141a", width=3)
        accent_bar.pack(side="left", fill="y", padx=(0, 8))

        lbl_text = tk.Label(item_frame, text=label, font=("Segoe UI", 9, "bold"), fg="#8e9192", bg="#13141a", cursor="hand2")
        lbl_text.pack(side="left")

        badge_lbl = None
        if badge_text:
            badge_lbl = tk.Label(item_frame, text=badge_text, font=("Segoe UI", 7, "bold"), fg=badge_fg, bg=badge_bg, padx=6, pady=2)
            badge_lbl.pack(side="right")

        def on_click(event=None):
            self.switch_nav(key)

        def on_enter(event=None):
            if getattr(self, "current_active_pane", "") != key:
                item_frame.config(bg="#181920")
                lbl_text.config(bg="#181920", fg="#ffffff")
                accent_bar.config(bg="#181920")

        def on_leave(event=None):
            if getattr(self, "current_active_pane", "") != key:
                item_frame.config(bg="#13141a")
                lbl_text.config(bg="#13141a", fg="#8e9192")
                accent_bar.config(bg="#13141a")

        for widget in (item_frame, lbl_text, accent_bar) + ((badge_lbl,) if badge_lbl else ()):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        self.nav_items[key] = {
            "frame": item_frame,
            "accent": accent_bar,
            "lbl": lbl_text,
            "badge": badge_lbl
        }
        return badge_lbl

    def switch_nav(self, target_key):
        """Berpindah antar panel tampilan secara mulus tanpa reload."""
        self.current_active_pane = target_key

        for key, pane in self.panes.items():
            if key == target_key:
                pane.pack(fill="both", expand=True)
            else:
                pane.pack_forget()

        for key, item in self.nav_items.items():
            if key == target_key:
                item["frame"].config(bg="#1a1b21")
                item["accent"].config(bg="#38bdf8")
                item["lbl"].config(bg="#1a1b21", fg="#ffffff")
            else:
                item["frame"].config(bg="#13141a")
                item["accent"].config(bg="#13141a")
                item["lbl"].config(bg="#13141a", fg="#8e9192")

        if target_key == "porto":
            self.load_porto_data()
        elif target_key == "diag":
            self.load_diag_data()
        elif target_key == "rekap":
            self.load_excel_view(self.current_rekap_mode)

    def create_top_header(self, parent):
        """Header telemetri atas dengan real-time quote, status MT5, dan Emergency Cut."""
        header_frame = tk.Frame(parent, bg="#13141a", relief="solid", bd=1, padx=14, pady=10)
        header_frame.pack(fill="x", padx=12, pady=(10, 8))

        # Kiri: Branding & Keterangan Skripsi
        left_box = tk.Frame(header_frame, bg="#13141a")
        left_box.pack(side="left")

        row_title = tk.Frame(left_box, bg="#13141a")
        row_title.pack(anchor="w")
        tk.Label(row_title, text="AI TRADING BOT V4.1", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#13141a").pack(side="left")
        lbl_tag = tk.Label(row_title, text="TWO-TIER SMC & DYNAMIC RRR", font=("Segoe UI", 7, "bold"), fg="#0d0e13", bg="#38bdf8", padx=6, pady=1)
        lbl_tag.pack(side="left", padx=(8, 0))

        tk.Label(left_box, text="Skripsi Informatika • XAUUSD Multi-Timeframe Multi-Domain Engine", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(anchor="w", pady=(2, 0))

        # Kanan: Aksi & Status Telemetri
        right_box = tk.Frame(header_frame, bg="#13141a")
        right_box.pack(side="right")

        row_top_ctrl = tk.Frame(right_box, bg="#13141a")
        row_top_ctrl.pack(anchor="e")

        self.lbl_mt5_status = tk.Label(row_top_ctrl, text="● MEMERIKSA MT5...", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#1a1b21", padx=8, pady=3, relief="solid", bd=1)
        self.lbl_mt5_status.pack(side="left", padx=4)

        btn_web_sync = tk.Button(row_top_ctrl, text="🔄 Web Monitor Sync", font=("Segoe UI", 8), fg="#c4c7c8", bg="#1a1b21", activebackground="#24252c", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.open_web_browser_sync, padx=8, pady=2)
        btn_web_sync.pack(side="left", padx=3)

        btn_hp_header = tk.Button(row_top_ctrl, text="📱 HP MONITOR", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#24252c", activebackground="#2e3038", relief="flat", cursor="hand2", command=self.open_web_mobile_dialog, padx=8, pady=2)
        btn_hp_header.pack(side="left", padx=3)

        btn_emergency = tk.Button(row_top_ctrl, text="⚠️ EMERGENCY CUT", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#ef4444", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.trigger_emergency_cut, padx=10, pady=2)
        btn_emergency.pack(side="left", padx=(6, 0))

        # Baris Bawah Kanan: Live Price Ticker
        self.lbl_ticker = tk.Label(right_box, text="XAUUSD: Menghubungkan MT5...", font=("Consolas", 10, "bold"), fg="#ffffff", bg="#13141a")
        self.lbl_ticker.pack(anchor="e", pady=(4, 0))

    def trigger_emergency_cut(self):
        """Mematikan seluruh bot trading seketika saat keadaan darurat."""
        if messagebox.askyesno("⚠️ EMERGENCY CUT ALL", 
                               "PERINGATAN DARURAT:\n\n"
                               "Apakah Anda yakin ingin mematikan semua bot trading (M15 & M5) segera?\n\n"
                               "Proses eksekusi bot di background akan dihentikan."):
            self.stop_bot_m15()
            self.stop_bot_m5()
            messagebox.showinfo("Emergency Cut", "Semua bot trading berhasil dihentikan.")

    def open_web_browser_sync(self):
        """Membuka dashboard web di browser eksternal HANYA jika tombol diklik manual oleh pengguna."""
        server_running = False
        import psutil
        for p in psutil.process_iter(['name', 'cmdline']):
            try:
                cmd = " ".join(p.info['cmdline'] or []).lower()
                if "web_dashboard_server.py" in cmd:
                    server_running = True
                    break
            except Exception:
                pass

        if not server_running:
            try:
                subprocess.Popen([PYTHON_EXE, SCRIPT_WEB], cwd=BASE_DIR, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                time.sleep(0.8)
            except Exception as e:
                messagebox.showerror("Error Server", f"Gagal menyalakan server web:\n{e}")

        webbrowser.open("http://localhost:5000")

    def open_web_mobile_dialog(self):
        """Membuka dialog popup QR Code untuk koneksi smartphone di jaringan Wi-Fi lokal."""
        # Dapatkan IP Wi-Fi
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            lan_ip = s.getsockname()[0]
        except Exception:
            lan_ip = '127.0.0.1'
        finally:
            s.close()

        mobile_url = f"http://{lan_ip}:5000"

        # Buat popup dialog QR Code di Tkinter
        top = tk.Toplevel(self.root)
        top.title("📱 Web Monitoring Trading Bot (Akses HP)")
        top.geometry("420x530")
        top.configure(bg="#0d0e13")
        top.resizable(False, False)
        top.grab_set()

        lbl_t = tk.Label(top, text="📱 Buka Dashboard di HP", font=("Segoe UI", 14, "bold"), fg="#38bdf8", bg="#0d0e13")
        lbl_t.pack(pady=(20, 5))

        lbl_info = tk.Label(top, text="Pastikan HP terhubung ke Wi-Fi yang sama dengan PC.\nArahkan kamera HP ke QR Code berikut:", font=("Segoe UI", 9), fg="#8e9192", bg="#0d0e13", justify="center")
        lbl_info.pack(pady=(0, 15))

        try:
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(mobile_url)
            qr.make(fit=True)
            pil_img = qr.make_image(fill_color="black", back_color="white")
            qr_photo = ImageTk.PhotoImage(pil_img)
            lbl_qr = tk.Label(top, image=qr_photo, bg="#ffffff", relief="solid", bd=1)
            lbl_qr.image = qr_photo
            lbl_qr.pack(pady=5)
        except Exception as e:
            lbl_qr = tk.Label(top, text=f"[QR Code Error: {e}]", fg="#f43f5e", bg="#0d0e13")
            lbl_qr.pack(pady=10)

        url_frame = tk.Frame(top, bg="#13141a", padx=10, pady=8, relief="solid", bd=1)
        url_frame.pack(fill="x", padx=30, pady=15)

        lbl_url_title = tk.Label(url_frame, text="URL Akses Wi-Fi:", font=("Segoe UI", 8, "bold"), fg="#5a5c63", bg="#13141a")
        lbl_url_title.pack(anchor="w")

        lbl_url = tk.Label(url_frame, text=mobile_url, font=("Consolas", 11, "bold"), fg="#06b6d4", bg="#13141a")
        lbl_url.pack(anchor="w", pady=(2, 0))

        def copy_url():
            self.root.clipboard_clear()
            self.root.clipboard_append(mobile_url)
            btn_copy.config(text="✓ URL Berhasil Disalin!")
            top.after(2000, lambda: btn_copy.config(text="Salin URL"))

        btn_copy = tk.Button(top, text="Salin URL", font=("Segoe UI", 9, "bold"), bg="#24252c", fg="#ffffff", bd=0, padx=15, pady=6, cursor="hand2", command=copy_url)
        btn_copy.pack(pady=(0, 10))

        btn_close = tk.Button(top, text="Tutup", font=("Segoe UI", 9), bg="#2e3038", fg="#c4c7c8", bd=0, padx=20, pady=5, cursor="hand2", command=top.destroy)
        btn_close.pack()

    def setup_params_tab(self):
        """Membuat panel Parameter & Skripsi yang menampilkan arsitektur model dan aturan penelitian."""
        container = tk.Frame(self.tab_params, bg="#0d0e13")
        container.pack(fill="both", expand=True, padx=15, pady=12)

        head = tk.Frame(container, bg="#13141a", relief="solid", bd=1, padx=15, pady=12)
        head.pack(fill="x", pady=(0, 12))
        tk.Label(head, text="📚 ARSITEKTUR MODEL LIGHTGBM & SPESIFIKASI SKRIPSI", font=("Segoe UI", 12, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")
        tk.Label(head, text="Penerapan Algoritma LightGBM untuk Prediksi Probabilitas Arah Harga XAUUSD Berbasis Multi-Timeframe, Indeks Dolar AS (DXY), dan Makroekonomi", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(anchor="w", pady=(2, 0))

        grid_box = tk.Frame(container, bg="#0d0e13")
        grid_box.pack(fill="both", expand=True)

        # Col 1: 44 Fitur Input Multi-Domain
        c1 = tk.Frame(grid_box, bg="#13141a", relief="solid", bd=1, padx=15, pady=12)
        c1.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(c1, text="🧠 44 FITUR INPUT AI MODEL", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#13141a").pack(anchor="w", pady=(0, 8))
        f_text = (
            "1. Makroekonomi & Sentimen News:\n"
            "   • ForexFactory Scraper (CPI, NFP, FOMC)\n"
            "   • DXY Returns (1, 3 lag) & XAU/DXY Ratio\n"
            "   • Dynamic Minutes-to-News & Pre-News Caution\n"
            "   • Macro Consensus Bias (Forecast vs Previous)\n\n"
            "2. Smart Money Concepts (SMC/ICT):\n"
            "   • Liquidity Sweep High / Low Detection\n"
            "   • Fair Value Gap (FVG) Bullish & Bearish\n"
            "   • Order Block (OB) Bullish & Bearish\n"
            "   • BOS, CHoCH, & Fibonacci OTE (38.2, 50, 61.8%)\n\n"
            "3. Multi-Timeframe Alignment & Momentum:\n"
            "   • H4 & H1 Continuous Distance (%) from EMA50\n"
            "   • H4 Channel Slope (-0.3 Downtrend Threshold)\n"
            "   • ADX 14 Trend Strength & Volume Ratio SMA20\n"
            "   • Consecutive Bull/Bear Candle Streak Counter\n\n"
            "4. Regularized Hyperparameters:\n"
            "   • n_estimators=800, lr=0.015, max_depth=5\n"
            "   • L1/L2 Regularization (alpha=0.1, lambda=1.0)\n"
            "   • min_child_samples=50 (Noise-Resistant Tree)"
        )
        tk.Label(c1, text=f_text, font=("Consolas", 8), fg="#c4c7c8", bg="#13141a", justify="left").pack(anchor="w")

        # Col 2: Aturan Eksekusi & Manajemen Risiko
        c2 = tk.Frame(grid_box, bg="#13141a", relief="solid", bd=1, padx=15, pady=12)
        c2.pack(side="left", fill="both", expand=True, padx=6)
        tk.Label(c2, text="🛡️ MANAJEMEN RISIKO DINAMIS", font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#13141a").pack(anchor="w", pady=(0, 8))
        r_text = (
            "1. Sniper Direct Entry with H4 Guard:\n"
            "   • Eksekusi instan jika AI Confidence >= 70.0%\n"
            "   • BUY Sniper DIBLOKIR saat H4 Descending!\n"
            "   • SELL Sniper DIBLOKIR saat H4 Ascending!\n\n"
            "2. Structural Dynamic RRR & SMC Levels:\n"
            "   • TP Target: Nearest Supply/Demand Kunci\n"
            "   • SL Proporsional Dinamis (RRR >= 1.8 s/d 1:2.5)\n"
            "   • Bad RRR Filter: Ditolak jika ruang < 1.8x SL\n\n"
            "3. Memori HTF 30-Hari & Hybrid Execution:\n"
            "   • D1 Institutional Major Demand/Supply\n"
            "   • Market Order + 50% Body Limit (Giant Candle)\n"
            "   • Order Lifetime Timeout 45 menit (3 Candle)\n\n"
            "4. Dynamic Trailing Lock & Cut-Loss:\n"
            "   • Auto BEP +$0.20 saat profit >= +$4.00 (Save -$21)\n"
            "   • Trailing Lock aman saat terjadi pembalikan\n"
            "   • Early Cut-Loss jika sinyal AI berbalik >= 65%\n\n"
            "5. Pre-News Caution & Spread Guard:\n"
            "   • Filter 35 menit menjelang berita High Impact\n"
            "   • Filter spread maksimal 25 pips"
        )
        tk.Label(c2, text=r_text, font=("Consolas", 8), fg="#c4c7c8", bg="#13141a", justify="left").pack(anchor="w")

        # Col 3: Metadata Penelitian & MT5 Link
        c3 = tk.Frame(grid_box, bg="#13141a", relief="solid", bd=1, padx=15, pady=12)
        c3.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(c3, text="🎓 METADATA PENELITIAN SKRIPSI", font=("Segoe UI", 10, "bold"), fg="#f59e0b", bg="#13141a").pack(anchor="w", pady=(0, 8))
        m_text = (
            "• Judul Skripsi:\n"
            "  Penerapan Algoritma LightGBM untuk Prediksi\n"
            "  Probabilitas Arah Harga XAUUSD Berbasis\n"
            "  Multi-Timeframe, Indeks Dolar AS (DXY),\n"
            "  dan Makroekonomi\n\n"
            "• Pengembang:\n"
            "  Nouval Ditya Maheswara\n"
            "  (NIM: 123230165 - Informatika)\n\n"
            "• Target Uji:\n"
            "  100 Transaksi Forward Testing Real-Time\n\n"
            "• Integrasi Broker:\n"
            "  MetaTrader 5 (Exness Real-2)\n\n"
            "• Magic Numbers:\n"
            "  M15 Swing   : 123230\n"
            "  M5 Scalper  : 123236\n\n"
            "• Log Storage:\n"
            "  Excel (.xlsx) Multi-Sheet + CSV Evaluasi"
        )
        tk.Label(c3, text=m_text, font=("Consolas", 8), fg="#c4c7c8", bg="#13141a", justify="left").pack(anchor="w")


    # =========================================================================
    # DONUT CHART HELPER (Canvas-based ring chart)
    # =========================================================================
    def draw_donut_chart(self, canvas, prob_buy, prob_sell, size=140):
        """Draw a donut/ring chart on the given canvas showing BUY vs SELL probability."""
        canvas.delete("all")
        cx, cy = size / 2, size / 2
        outer_r = size / 2 - 8
        inner_r = outer_r * 0.58

        # Track background
        canvas.create_oval(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, fill="#1a1b21", outline="#2e3038", width=2)

        total = prob_buy + prob_sell
        if total <= 0:
            total = 100.0

        buy_extent = (prob_buy / total) * 360.0
        sell_extent = 360.0 - buy_extent

        if prob_buy >= 70.0:
            dominant_color = "#10b981"
            dominant_label = "SNIPER BUY"
            dominant_pct = prob_buy
        elif prob_sell >= 70.0:
            dominant_color = "#ef4444"
            dominant_label = "SNIPER SELL"
            dominant_pct = prob_sell
        elif prob_buy > prob_sell:
            dominant_color = "#38bdf8"
            dominant_label = "BUY BIAS"
            dominant_pct = prob_buy
        elif prob_sell > prob_buy:
            dominant_color = "#f59e0b"
            dominant_label = "SELL BIAS"
            dominant_pct = prob_sell
        else:
            dominant_color = "#c4c7c8"
            dominant_label = "NETRAL"
            dominant_pct = 50.0

        if sell_extent > 0.5:
            canvas.create_arc(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, start=90, extent=-sell_extent, fill="#ef4444", outline="")
        if buy_extent > 0.5:
            canvas.create_arc(cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r, start=90, extent=buy_extent, fill="#10b981", outline="")

        canvas.create_oval(cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r, fill="#13141a", outline="#13141a")
        canvas.create_text(cx, cy - 8, text=f"{dominant_pct:.1f}%", font=("Segoe UI", 15, "bold"), fill="#ffffff")
        canvas.create_text(cx, cy + 12, text=dominant_label, font=("Segoe UI", 8, "bold"), fill=dominant_color)

    # =========================================================================
    # DASHBOARD PANEL BUILDER (used by both M15 and M5 tabs)
    # =========================================================================
    def build_dashboard_panel(self, parent, bot_key, accent_color="#38bdf8"):
        """Build the right-side dashboard panel with Timer, Donut, and History Treeview."""
        right_panel = tk.Frame(parent, bg="#0d0e13")
        widgets = {}

        # ── KARTU 1: MONITORING LIVE TELEMETRY & GAUGE ──
        card_mon = tk.Frame(right_panel, bg="#13141a", relief="solid", bd=1, padx=12, pady=10)
        card_mon.pack(fill="x", padx=4, pady=(0, 6))

        # Header bar monitoring
        mon_head = tk.Frame(card_mon, bg="#13141a")
        mon_head.pack(fill="x", pady=(0, 8))

        tf_label = "M15 V4.1 SMC RRR" if bot_key == "m15" else "M5 V4.1 SCALPER"
        h_left = tk.Frame(mon_head, bg="#13141a")
        h_left.pack(side="left")
        tk.Label(h_left, text=f"MONITORING LIVE {tf_label}", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")
        tk.Label(h_left, text="Live Ingestion Pipeline Connected", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(anchor="w")

        lbl_active_badge = tk.Label(mon_head, text="ACTIVE EXECUTION", font=("Segoe UI", 7, "bold"), fg="#c4c7c8", bg="#24252c", padx=8, pady=3)
        lbl_active_badge.pack(side="right")
        widgets["active_badge"] = lbl_active_badge

        # Row Metrik: Durasi Sesi & Keputusan Terakhir
        metric_row = tk.Frame(card_mon, bg="#13141a")
        metric_row.pack(fill="x", pady=(0, 10))

        # Box Durasi
        dur_box = tk.Frame(metric_row, bg="#1a1b21", relief="solid", bd=1, padx=10, pady=8)
        dur_box.pack(side="left", fill="both", expand=True, padx=(0, 4))
        tk.Label(dur_box, text="DURASI SESI BOT", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#1a1b21").pack(anchor="w")
        timer_lbl = tk.Label(dur_box, text="00:00:00", font=("Consolas", 15, "bold"), fg="#ffffff", bg="#1a1b21")
        timer_lbl.pack(anchor="w", pady=(2, 0))
        tk.Label(dur_box, text="Waktu Aktif Berjalan", font=("Segoe UI", 7), fg="#5a5c63", bg="#1a1b21").pack(anchor="w")
        widgets["timer"] = timer_lbl

        # Box Keputusan Terakhir
        dec_box = tk.Frame(metric_row, bg="#1a1b21", relief="solid", bd=1, padx=10, pady=8)
        dec_box.pack(side="right", fill="both", expand=True, padx=(4, 0))
        tk.Label(dec_box, text="KEPUTUSAN TERAKHIR BOT", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#1a1b21").pack(anchor="w")
        decision_lbl = tk.Label(dec_box, text="STANDBY", font=("Segoe UI", 12, "bold"), fg="#f59e0b", bg="#1a1b21")
        decision_lbl.pack(anchor="w", pady=(2, 0))
        status_lbl = tk.Label(dec_box, text="--:--:--", font=("Segoe UI", 7), fg="#5a5c63", bg="#1a1b21")
        status_lbl.pack(anchor="w")
        widgets["decision_lbl"] = decision_lbl
        widgets["status_lbl"] = status_lbl

        # Row Gauge & Probabilitas
        gauge_row = tk.Frame(card_mon, bg="#13141a")
        gauge_row.pack(fill="x")

        # Donut Gauge
        donut_box = tk.Frame(gauge_row, bg="#13141a")
        donut_box.pack(side="left", padx=(0, 10))
        donut_size = 140
        donut_canvas = tk.Canvas(donut_box, width=donut_size, height=donut_size, bg="#13141a", highlightthickness=0)
        donut_canvas.pack()
        tk.Label(donut_box, text="AI CONFIDENCE GAUGE", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(pady=(2, 0))
        widgets["donut_canvas"] = donut_canvas

        # Prob Bars Detail
        prob_detail = tk.Frame(gauge_row, bg="#13141a")
        prob_detail.pack(side="left", fill="both", expand=True, padx=(6, 0))

        p_head = tk.Frame(prob_detail, bg="#13141a")
        p_head.pack(fill="x", pady=(0, 6))
        tk.Label(p_head, text="DISTRIBUSI PROBABILITAS LIGHTGBM", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#13141a").pack(side="left")
        tk.Label(p_head, text="44 Fitur Input", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(side="right")

        # BUY Bar
        buy_lbl_row = tk.Frame(prob_detail, bg="#13141a")
        buy_lbl_row.pack(fill="x")
        tk.Label(buy_lbl_row, text="BUY PROBABILITY", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(side="left")
        buy_pct_lbl = tk.Label(buy_lbl_row, text="50.0%", font=("Consolas", 8, "bold"), fg="#ffffff", bg="#13141a")
        buy_pct_lbl.pack(side="right")
        widgets["buy_pct_lbl"] = buy_pct_lbl

        buy_bg = tk.Frame(prob_detail, bg="#24252c", height=10)
        buy_bg.pack(fill="x", pady=(2, 6))
        buy_bg.pack_propagate(False)
        buy_fill = tk.Frame(buy_bg, bg="#10b981", height=10)
        buy_fill.place(relx=0, rely=0, relwidth=0.5, relheight=1.0)
        widgets["buy_bar_fill"] = buy_fill

        # SELL Bar
        sell_lbl_row = tk.Frame(prob_detail, bg="#13141a")
        sell_lbl_row.pack(fill="x")
        tk.Label(sell_lbl_row, text="SELL PROBABILITY", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(side="left")
        sell_pct_lbl = tk.Label(sell_lbl_row, text="50.0%", font=("Consolas", 8, "bold"), fg="#ffffff", bg="#13141a")
        sell_pct_lbl.pack(side="right")
        widgets["sell_pct_lbl"] = sell_pct_lbl

        sell_bg = tk.Frame(prob_detail, bg="#24252c", height=10)
        sell_bg.pack(fill="x", pady=(2, 8))
        sell_bg.pack_propagate(False)
        sell_fill = tk.Frame(sell_bg, bg="#ef4444", height=10)
        sell_fill.place(relx=0, rely=0, relwidth=0.5, relheight=1.0)
        widgets["sell_bar_fill"] = sell_fill

        trend_lbl = tk.Label(prob_detail, text="• Tren H1: EMA 50 Bullish Confirmation\n• SNR Terdekat: Support $4,324.50", font=("Segoe UI", 7), fg="#8e9192", bg="#13141a", justify="left")
        trend_lbl.pack(anchor="w")
        widgets["trend_lbl"] = trend_lbl

        self.draw_donut_chart(donut_canvas, 50.0, 50.0, donut_size)

        # ── KARTU 2: RIWAYAT KEPUTUSAN (INFERENCE LOGS) ──
        history_frame = tk.Frame(right_panel, bg="#13141a", relief="solid", bd=1, padx=12, pady=10)
        history_frame.pack(fill="both", expand=True, padx=4, pady=(6, 0))

        hist_head = tk.Frame(history_frame, bg="#13141a")
        hist_head.pack(fill="x", pady=(0, 6))

        h_title_box = tk.Frame(hist_head, bg="#13141a")
        h_title_box.pack(side="left")
        tk.Label(h_title_box, text=f"RIWAYAT KEPUTUSAN BOT {bot_key.upper()}", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#13141a").pack(side="left")
        tk.Label(h_title_box, text="LIVE FEED", font=("Segoe UI", 7, "bold"), fg="#10b981", bg="#064e3b", padx=6, pady=1).pack(side="left", padx=(8, 0))

        btn_clear = tk.Button(hist_head, text="🗑️ BERSIHKAN", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", padx=6, pady=2)
        btn_clear.pack(side="right")

        hist_count_lbl = tk.Label(hist_head, text="0 entri", font=("Segoe UI", 7), fg="#5a5c63", bg="#13141a")
        hist_count_lbl.pack(side="right", padx=(0, 6))
        widgets["hist_count_lbl"] = hist_count_lbl

        tree_box = tk.Frame(history_frame, bg="#13141a")
        tree_box.pack(fill="both", expand=True)

        scry = ttk.Scrollbar(tree_box, orient="vertical")
        scry.pack(side="right", fill="y")

        hist_cols = ("waktu", "aksi", "buy_pct", "sell_pct", "detail")
        hist_tree = ttk.Treeview(tree_box, columns=hist_cols, show="headings", yscrollcommand=scry.set, height=7)
        hist_tree.pack(fill="both", expand=True)
        scry.config(command=hist_tree.yview)

        hist_tree.heading("waktu", text="WAKTU")
        hist_tree.heading("aksi", text="AKSI")
        hist_tree.heading("buy_pct", text="BUY %")
        hist_tree.heading("sell_pct", text="SELL %")
        hist_tree.heading("detail", text="DETAIL / ALASAN KEPUTUSAN AI")

        hist_tree.column("waktu", width=70, anchor="center")
        hist_tree.column("aksi", width=75, anchor="center")
        hist_tree.column("buy_pct", width=55, anchor="center")
        hist_tree.column("sell_pct", width=55, anchor="center")
        hist_tree.column("detail", width=260, anchor="w", stretch=True)

        hist_tree.tag_configure("buy", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        hist_tree.tag_configure("sell", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        hist_tree.tag_configure("netral", foreground="#f59e0b", font=("Segoe UI", 9))
        hist_tree.tag_configure("ditahan", foreground="#f59e0b", font=("Segoe UI", 9))
        hist_tree.tag_configure("info", foreground="#38bdf8", font=("Segoe UI", 9))
        hist_tree.tag_configure("system", foreground="#8e9192", font=("Segoe UI", 8))

        widgets["hist_tree"] = hist_tree
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
        # Subheader banner
        sub_banner = tk.Frame(self.tab_m15, bg="#13141a", relief="solid", bd=1)
        sub_banner.pack(fill="x", padx=4, pady=(0, 6))

        b_left = tk.Frame(sub_banner, bg="#13141a")
        b_left.pack(side="left", padx=12, pady=6)
        tk.Label(b_left, text="● BOT M15 LIVE ENGINE", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#13141a").pack(side="left")
        tk.Label(b_left, text="  |  TARGET: XAUUSD.spot  |  TIMEFRAME: M15 (15m Sniper)", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(side="left")

        b_right = tk.Frame(sub_banner, bg="#13141a")
        b_right.pack(side="right", padx=12, pady=6)
        tk.Label(b_right, text="MODEL: v4.1-StructuralDynamicRRR  |  INFERENCE: 14ms  |  IPC: CONNECTED", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#13141a").pack(side="right")

        paned = tk.PanedWindow(self.tab_m15, orient="horizontal", bg="#0d0e13", bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Panel Kiri: Kontrol & Parameter (Width: 340)
        left_panel = tk.Frame(paned, bg="#0d0e13", width=340)
        paned.add(left_panel, minsize=320)

        # Card 1: Core Orchestration
        c_orch = tk.Frame(left_panel, bg="#13141a", relief="solid", bd=1, padx=14, pady=12)
        c_orch.pack(fill="x", padx=4, pady=(0, 6))

        o_head = tk.Frame(c_orch, bg="#13141a")
        o_head.pack(fill="x", pady=(0, 6))
        o_title_box = tk.Frame(o_head, bg="#13141a")
        o_title_box.pack(side="left")
        tk.Label(o_title_box, text="CORE ORCHESTRATION", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(anchor="w")
        tk.Label(o_title_box, text="KONTROL OPERASIONAL M15", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")

        self.m15_status_badge = tk.Label(o_head, text="● STANDBY / NONAKTIF", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#24252c", padx=8, pady=3)
        self.m15_status_badge.pack(side="right")

        mode_row = tk.Frame(c_orch, bg="#13141a")
        mode_row.pack(fill="x", pady=(0, 10))
        tk.Label(mode_row, text="Mode Eksekusi:", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(side="left")
        tk.Label(mode_row, text="HYBRID (MARKET + 50% LIMIT)", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#13141a").pack(side="right")

        btn_row = tk.Frame(c_orch, bg="#13141a")
        btn_row.pack(fill="x")
        self.btn_start_m15 = tk.Button(btn_row, text="▶ AKTIFKAN BOT M15", font=("Segoe UI", 9, "bold"), fg="#0d0e13", bg="#ffffff", activebackground="#c4c7c8", activeforeground="#0d0e13", relief="flat", cursor="hand2", command=self.start_bot_m15, pady=7)
        self.btn_start_m15.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_stop_m15 = tk.Button(btn_row, text="⏹ HENTIKAN BOT M15", font=("Segoe UI", 9, "bold"), fg="#8e9192", bg="#24252c", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.stop_bot_m15, pady=7, state="disabled")
        self.btn_stop_m15.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Card 2: Neural Architecture Specs
        c_specs = tk.Frame(left_panel, bg="#13141a", relief="solid", bd=1, padx=14, pady=12)
        c_specs.pack(fill="both", expand=True, padx=4, pady=(6, 0))

        s_head = tk.Frame(c_specs, bg="#13141a")
        s_head.pack(fill="x", pady=(0, 8))
        tk.Label(s_head, text="NEURAL ARCHITECTURE SPECS", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(anchor="w")
        tk.Label(s_head, text="PARAMETER BOT M15 (v4.1)", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")

        specs = [
            ("Timeframe Eksekusi", "M15 (15 Menit)"),
            ("Model AI Machine Learning", "LightGBM v4.1 (44 Fitur)"),
            ("Threshold Sniper Entry", ">= 70.0% Direct Entry"),
            ("Target TP / SL Rasio", "Structural SMC (RRR >= 1.8)"),
            ("Memori HTF Kunci", "30-Hari D1 Demand/Supply"),
            ("Mode Eksekusi Order", "Market + 50% Body Limit"),
            ("Capital Preservation", "Auto BEP +$0.20 (+$4 USD)"),
            ("Magic Number / Lot", "123230 / 0.01 Lot"),
        ]
        for idx, (lbl, val) in enumerate(specs):
            row = tk.Frame(c_specs, bg="#1a1b21" if idx % 2 == 0 else "#13141a", padx=8, pady=5)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=lbl, font=("Segoe UI", 8), fg="#8e9192", bg=row["bg"]).pack(side="left")
            tk.Label(row, text=val, font=("Consolas", 8, "bold"), fg="#ffffff", bg=row["bg"]).pack(side="right")

        excel_btns_m15 = tk.Frame(c_specs, bg="#13141a")
        excel_btns_m15.pack(fill="x", side="bottom", pady=(10, 0))

        btn_view_m15 = tk.Button(excel_btns_m15, text="👁️ Tampilkan Tabel Excel M15", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#1a1b21", activebackground="#24252c", relief="solid", bd=1, cursor="hand2", command=lambda: self.switch_to_rekap_tab("m15"), pady=5)
        btn_view_m15.pack(fill="x", pady=(0, 4))

        btn_excel_m15 = tk.Button(excel_btns_m15, text="📂 Buka di Aplikasi Excel (.xlsx)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else messagebox.showerror("File Error", "File Excel M15 belum ditemukan!"), pady=4)
        btn_excel_m15.pack(fill="x")

        # Panel Kanan: Dashboard (Timer + Donut + History)
        right_panel, self.m15_widgets = self.build_dashboard_panel(paned, "m15", accent_color="#38bdf8")
        paned.add(right_panel)

    # =========================================================================
    # TAB 2: BOT M5
    # =========================================================================
    def setup_m5_tab(self):
        # Subheader banner
        sub_banner = tk.Frame(self.tab_m5, bg="#13141a", relief="solid", bd=1)
        sub_banner.pack(fill="x", padx=4, pady=(0, 6))

        b_left = tk.Frame(sub_banner, bg="#13141a")
        b_left.pack(side="left", padx=12, pady=6)
        tk.Label(b_left, text="● BOT M5 LIVE ENGINE", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#13141a").pack(side="left")
        tk.Label(b_left, text="  |  TARGET: XAUUSD.spot  |  TIMEFRAME: M5 (5m Scalper)", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(side="left")

        b_right = tk.Frame(sub_banner, bg="#13141a")
        b_right.pack(side="right", padx=12, pady=6)
        tk.Label(b_right, text="MODEL: v4.1-ScalperAntiCounterTrend  |  INFERENCE: 12ms  |  IPC: CONNECTED", font=("Segoe UI", 8, "bold"), fg="#10b981", bg="#13141a").pack(side="right")

        paned = tk.PanedWindow(self.tab_m5, orient="horizontal", bg="#0d0e13", bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Panel Kiri: Kontrol & Parameter (Width: 340)
        left_panel = tk.Frame(paned, bg="#0d0e13", width=340)
        paned.add(left_panel, minsize=320)

        # Card 1: Core Orchestration
        c_orch = tk.Frame(left_panel, bg="#13141a", relief="solid", bd=1, padx=14, pady=12)
        c_orch.pack(fill="x", padx=4, pady=(0, 6))

        o_head = tk.Frame(c_orch, bg="#13141a")
        o_head.pack(fill="x", pady=(0, 6))
        o_title_box = tk.Frame(o_head, bg="#13141a")
        o_title_box.pack(side="left")
        tk.Label(o_title_box, text="CORE ORCHESTRATION", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(anchor="w")
        tk.Label(o_title_box, text="KONTROL OPERASIONAL M5", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")

        self.m5_status_badge = tk.Label(o_head, text="● STANDBY / NONAKTIF", font=("Segoe UI", 8, "bold"), fg="#ef4444", bg="#24252c", padx=8, pady=3)
        self.m5_status_badge.pack(side="right")

        mode_row = tk.Frame(c_orch, bg="#13141a")
        mode_row.pack(fill="x", pady=(0, 10))
        tk.Label(mode_row, text="Mode Eksekusi:", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a").pack(side="left")
        tk.Label(mode_row, text="DYNAMIC SCALPER (AI >= 70%)", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#13141a").pack(side="right")

        btn_row = tk.Frame(c_orch, bg="#13141a")
        btn_row.pack(fill="x")
        self.btn_start_m5 = tk.Button(btn_row, text="▶ AKTIFKAN BOT M5", font=("Segoe UI", 9, "bold"), fg="#0d0e13", bg="#ffffff", activebackground="#c4c7c8", activeforeground="#0d0e13", relief="flat", cursor="hand2", command=self.start_bot_m5, pady=7)
        self.btn_start_m5.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.btn_stop_m5 = tk.Button(btn_row, text="⏹ HENTIKAN BOT M5", font=("Segoe UI", 9, "bold"), fg="#8e9192", bg="#24252c", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.stop_bot_m5, pady=7, state="disabled")
        self.btn_stop_m5.pack(side="right", fill="x", expand=True, padx=(4, 0))

        # Card 2: Neural Architecture Specs
        c_specs = tk.Frame(left_panel, bg="#13141a", relief="solid", bd=1, padx=14, pady=12)
        c_specs.pack(fill="both", expand=True, padx=4, pady=(6, 0))

        s_head = tk.Frame(c_specs, bg="#13141a")
        s_head.pack(fill="x", pady=(0, 8))
        tk.Label(s_head, text="NEURAL ARCHITECTURE SPECS", font=("Segoe UI", 7, "bold"), fg="#8e9192", bg="#13141a").pack(anchor="w")
        tk.Label(s_head, text="PARAMETER BOT M5 (v4.1)", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#13141a").pack(anchor="w")

        specs_m5 = [
            ("Timeframe Eksekusi", "M5 (Scalping Cepat)"),
            ("Model AI Machine Learning", "LightGBM v4.1 Scalper (44 Fitur)"),
            ("Threshold Sniper Entry", ">= 70.0% Direct Entry"),
            ("Anti Counter-Trend Guard", "Sniper H4 Channel Guard"),
            ("Target TP / SL Rasio", "Dinamis ATR 14 (RRR 1:2.0)"),
            ("Early Cut-Loss Invalidation", ">= 65.0% Reversal"),
            ("Trailing Profit Lock", "Trigger $1.50, Lock $0.80"),
            ("Magic Number / Lot", "123236 / 0.01 Lot"),
        ]
        for idx, (lbl, val) in enumerate(specs_m5):
            row = tk.Frame(c_specs, bg="#1a1b21" if idx % 2 == 0 else "#13141a", padx=8, pady=5)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=lbl, font=("Segoe UI", 8), fg="#8e9192", bg=row["bg"]).pack(side="left")
            tk.Label(row, text=val, font=("Consolas", 8, "bold"), fg="#ffffff", bg=row["bg"]).pack(side="right")

        excel_btns_m5 = tk.Frame(c_specs, bg="#13141a")
        excel_btns_m5.pack(fill="x", side="bottom", pady=(10, 0))

        btn_view_m5 = tk.Button(excel_btns_m5, text="👁️ Tampilkan Tabel Excel M5", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#1a1b21", activebackground="#24252c", relief="solid", bd=1, cursor="hand2", command=lambda: self.switch_to_rekap_tab("m5"), pady=5)
        btn_view_m5.pack(fill="x", pady=(0, 4))

        btn_excel_m5 = tk.Button(excel_btns_m5, text="📂 Buka di Aplikasi Excel (.xlsx)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else messagebox.showerror("File Error", "File Excel M5 belum ditemukan!"), pady=4)
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
        container = tk.Frame(self.tab_rekap, bg="#0d0e13")
        container.pack(fill="both", expand=True, padx=15, pady=12)

        # Kartu Rekap Atas
        cards_frame = tk.Frame(container, bg="#0d0e13")
        cards_frame.pack(fill="x", pady=(0, 12))

        # Kartu M15
        card_m15 = tk.Frame(cards_frame, bg="#13141a", relief="solid", bd=1, padx=15, pady=10)
        card_m15.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(card_m15, text="PORTOFOLIO MODEL M15 (KONSERVATIF)", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#13141a").pack(anchor="w")
        self.lbl_rekap_m15 = tk.Label(card_m15, text="Memuat riwayat...", font=("Consolas", 9), fg="#ffffff", bg="#13141a", justify="left")
        self.lbl_rekap_m15.pack(anchor="w", pady=(4, 8))

        btn_box_15 = tk.Frame(card_m15, bg="#13141a")
        btn_box_15.pack(fill="x")
        self.btn_card_view_m15 = tk.Button(btn_box_15, text="👁️ Tampilkan Tabel Excel M15", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m15"), padx=10, pady=5)
        self.btn_card_view_m15.pack(side="left", padx=(0, 6))
        tk.Button(btn_box_15, text="📂 Buka di Excel (.xlsx)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M15) if os.path.exists(EXCEL_M15) else messagebox.showerror("File Error", "File Excel M15 belum ditemukan!"), padx=8, pady=5).pack(side="left")

        # Kartu M5
        card_m5 = tk.Frame(cards_frame, bg="#13141a", relief="solid", bd=1, padx=15, pady=10)
        card_m5.pack(side="right", fill="both", expand=True, padx=(6, 0))
        tk.Label(card_m5, text="PORTOFOLIO MODEL M5 (SCALPING DYNAMIC)", font=("Segoe UI", 10, "bold"), fg="#10b981", bg="#13141a").pack(anchor="w")
        self.lbl_rekap_m5 = tk.Label(card_m5, text="Memuat riwayat...", font=("Consolas", 9), fg="#ffffff", bg="#13141a", justify="left")
        self.lbl_rekap_m5.pack(anchor="w", pady=(4, 8))

        btn_box_5 = tk.Frame(card_m5, bg="#13141a")
        btn_box_5.pack(fill="x")
        self.btn_card_view_m5 = tk.Button(btn_box_5, text="👁️ Tampilkan Tabel Excel M5", font=("Segoe UI", 9, "bold"), fg="#ffffff", bg="#059669", activebackground="#047857", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m5"), padx=10, pady=5)
        self.btn_card_view_m5.pack(side="left", padx=(0, 6))
        tk.Button(btn_box_5, text="📂 Buka di Excel (.xlsx)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: os.startfile(EXCEL_M5) if os.path.exists(EXCEL_M5) else messagebox.showerror("File Error", "File Excel M5 belum ditemukan!"), padx=8, pady=5).pack(side="left")

        # Panel Tabel Interaktif Terpadu
        table_frame = tk.Frame(container, bg="#13141a", relief="solid", bd=1, padx=12, pady=10)
        table_frame.pack(fill="both", expand=True)

        # Header Bar Tabel
        tbl_top = tk.Frame(table_frame, bg="#13141a")
        tbl_top.pack(fill="x", pady=(0, 8))

        title_box = tk.Frame(tbl_top, bg="#13141a")
        title_box.pack(side="left")

        self.lbl_table_title = tk.Label(title_box, text="DAFTAR TRANSAKSI EXCEL M15", font=("Segoe UI", 11, "bold"), fg="#38bdf8", bg="#13141a")
        self.lbl_table_title.pack(anchor="w")

        self.lbl_table_subtitle = tk.Label(title_box, text="Memuat ringkasan data...", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a")
        self.lbl_table_subtitle.pack(anchor="w")

        # Tombol Navigasi Mode Data
        nav_box = tk.Frame(tbl_top, bg="#13141a")
        nav_box.pack(side="right")

        self.btn_nav_m15 = tk.Button(nav_box, text="📊 Excel M15", font=("Segoe UI", 8, "bold"), fg="#ffffff", bg="#0284c7", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m15"), padx=8, pady=4)
        self.btn_nav_m15.pack(side="left", padx=2)

        self.btn_nav_m5 = tk.Button(nav_box, text="⚡ Excel M5", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#24252c", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("m5"), padx=8, pady=4)
        self.btn_nav_m5.pack(side="left", padx=2)

        self.btn_nav_stat = tk.Button(nav_box, text="📈 Perbandingan Statistik", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#24252c", activebackground="#6366f1", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("stat"), padx=8, pady=4)
        self.btn_nav_stat.pack(side="left", padx=2)

        self.btn_nav_mt5 = tk.Button(nav_box, text="🔄 Live MT5 Deals", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#24252c", activebackground="#2e3038", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.load_excel_view("mt5"), padx=8, pady=4)
        self.btn_nav_mt5.pack(side="left", padx=2)

        self.btn_nav_popup = tk.Button(nav_box, text="🔍 Jendela Penuh", font=("Segoe UI", 8, "bold"), fg="#f59e0b", bg="#24252c", activebackground="#d97706", activeforeground="#ffffff", relief="flat", cursor="hand2", command=self.open_excel_viewer_modal, padx=8, pady=4)
        self.btn_nav_popup.pack(side="left", padx=2)

        self.btn_nav_refresh = tk.Button(nav_box, text="🔄 Refresh", font=("Segoe UI", 8), fg="#38bdf8", bg="#24252c", activebackground="#2e3038", relief="flat", cursor="hand2", command=self.refresh_current_view, padx=8, pady=4)
        self.btn_nav_refresh.pack(side="left", padx=(2, 0))

        # Filter & Search Strip
        self.filter_strip = tk.Frame(table_frame, bg="#1a1b21", relief="solid", bd=1, padx=8, pady=5)
        self.filter_strip.pack(fill="x", pady=(0, 8))

        filter_left = tk.Frame(self.filter_strip, bg="#1a1b21")
        filter_left.pack(side="left")

        tk.Label(filter_left, text="🔍 Cari:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left", padx=(0, 4))
        
        self.entry_search = tk.Entry(filter_left, textvariable=self.search_var, font=("Segoe UI", 8), bg="#24252c", fg="#ffffff", insertbackground="#38bdf8", relief="flat", width=22)
        self.entry_search.pack(side="left", padx=(0, 10), ipady=2)
        self.search_var.trace_add("write", lambda *args: self.render_table_rows())

        tk.Label(filter_left, text="Filter:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left", padx=(5, 4))

        self.btn_filter_all = tk.Button(filter_left, text="Semua", font=("Segoe UI", 8, "bold"), fg="#0d0e13", bg="#ffffff", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("ALL"), padx=8, pady=2)
        self.btn_filter_all.pack(side="left", padx=2)

        self.btn_filter_win = tk.Button(filter_left, text="Hanya WIN", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("WIN"), padx=8, pady=2)
        self.btn_filter_win.pack(side="left", padx=2)

        self.btn_filter_loss = tk.Button(filter_left, text="Hanya LOSS", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_filter_status("LOSS"), padx=8, pady=2)
        self.btn_filter_loss.pack(side="left", padx=2)

        self.lbl_row_count = tk.Label(self.filter_strip, text="Menampilkan 0 baris", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21")
        self.lbl_row_count.pack(side="right")

        # Container Treeview dengan Scrollbar Ganda (Vertikal & Horizontal)
        tree_container = tk.Frame(table_frame, bg="#13141a")
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
        self.tree.tag_configure("normal", foreground="#ffffff", font=("Consolas", 9))
        self.tree.tag_configure("stat_title", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))
        self.tree.tag_configure("stat_num", foreground="#ffffff", font=("Consolas", 9))

        # Muat ringkasan portofolio & data default (M15)
        self.update_portfolio_summary_labels()
        self.load_excel_view(mode="m15")

    def create_footer(self, parent=None):
        target_parent = parent if parent is not None else self.root
        footer = tk.Frame(target_parent, bg="#0d0e13", height=24)
        footer.pack(fill="x", padx=12, pady=(0, 6), side="bottom")
        tk.Label(footer, text="💡 Tip: Anda dapat menyalakan Bot M15 dan Bot M5 secara independen. Data log dan Excel selalu tersinkronisasi otomatis.", font=("Segoe UI", 8), fg="#5a5c63", bg="#0d0e13").pack(side="left")
        tk.Label(footer, text="Obsidian Terminal v4.1 • Native Desktop App", font=("Segoe UI", 8), fg="#3e4148", bg="#0d0e13").pack(side="right")

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
            self.m15_widgets["timer"].config(text="00:00:00", fg="#5a5c63")

        # M5 stopwatch
        if self.m5_start_time is not None:
            elapsed = int(now - self.m5_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.m5_widgets["timer"].config(text=f"{h:02d}:{m:02d}:{s:02d}", fg="#10b981")
        else:
            self.m5_widgets["timer"].config(text="00:00:00", fg="#5a5c63")

        self.root.after(1000, self.update_stopwatches)

    def poll_live_telemetry(self):
        """Membaca telemetri real-time dari telemetry_m15.json dan telemetry_m5.json untuk audit live bergerak."""
        try:
            now_ts = time.time()
            # 1. Telemetri M15
            t15_file = os.path.join(BASE_DIR, "telemetry_m15.json")
            if os.path.exists(t15_file):
                try:
                    with open(t15_file, "r", encoding="utf-8") as f:
                        t15 = json.load(f)
                    file_age = now_ts - float(t15.get("timestamp", 0))
                    if file_age <= 12.0:  # Data segar (<12 detik)
                        pb = float(t15.get("prob_buy", 50.0))
                        ps = float(t15.get("prob_sell", 50.0))
                        self.update_donut_and_bars("m15", pb, ps)
                        
                        mins = t15.get("mins_left", 0)
                        secs = t15.get("secs_left", 0)
                        status_text = t15.get("status_str", "LIVE MONITORING")
                        h1_trend = t15.get("h1_trend", "NETRAL")
                        sup = t15.get("m15_sup", 0.0)
                        res = t15.get("m15_res", 0.0)
                        stoch = t15.get("stoch_k", 50.0)
                        
                        self.m15_widgets["trend_lbl"].config(
                            text=f"• Tren H1: {h1_trend} | Stoch: {stoch:.0f}\n• SNR: Sup ${sup:.2f} | Res ${res:.2f}\n• Status: {status_text}"
                        )
                        
                        self.m15_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
                        self.m15_widgets["active_badge"].config(text="LIVE PIPELINE SYNCED", fg="#10b981", bg="#064e3b")
                        self.m15_widgets["status_lbl"].config(text=f"Sisa Candle: {mins:02d}m {secs:02d}s", fg="#38bdf8")
                except Exception:
                    pass

            # 2. Telemetri M5
            t5_file = os.path.join(BASE_DIR, "telemetry_m5.json")
            if os.path.exists(t5_file):
                try:
                    with open(t5_file, "r", encoding="utf-8") as f:
                        t5 = json.load(f)
                    file_age5 = now_ts - float(t5.get("timestamp", 0))
                    if file_age5 <= 12.0:
                        pb5 = float(t5.get("prob_buy", 50.0))
                        ps5 = float(t5.get("prob_sell", 50.0))
                        self.update_donut_and_bars("m5", pb5, ps5)
                        
                        mins5 = t5.get("mins_left", 0)
                        secs5 = t5.get("secs_left", 0)
                        status_text5 = t5.get("status_str", "LIVE MONITORING")
                        
                        self.m5_widgets["trend_lbl"].config(text=f"• Status M5: {status_text5}")
                        self.m5_status_badge.config(text="● STATUS: AKTIF & BERJALAN", fg="#10b981", bg="#064e3b")
                        self.m5_widgets["active_badge"].config(text="LIVE PIPELINE SYNCED", fg="#10b981", bg="#064e3b")
                        self.m5_widgets["status_lbl"].config(text=f"Sisa Candle: {mins5:02d}m {secs5:02d}s", fg="#38bdf8")
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.root.after(500, self.poll_live_telemetry)

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
            widgets["status_lbl"].config(text="○ STANDBY", fg="#ef4444", bg="#24252c")

    # =========================================================================
    # LOGIKA KONTROL PROSES (START & STOP)
    # =========================================================================
    def start_bot_m15(self):
        if self.proc_m15 is not None and self.proc_m15.poll() is None:
            messagebox.showinfo("Info", "Bot M15 sudah dalam keadaan berjalan!")
            return

        # Pastikan tidak ada proses zombie M15 lain yang mengunci port / single instance
        try:
            import psutil
            curr_pid = os.getpid()
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if p.info['pid'] != curr_pid and p.info['cmdline']:
                        cmd_s = " ".join(p.info['cmdline']).lower()
                        if "eksekusi_otomatis_trading_bot.py" in cmd_s and "m5" not in cmd_s:
                            p.kill()
                except Exception:
                    pass
            time.sleep(0.5)
        except Exception:
            pass

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

        # Bersihkan setiap proses background M15 yang masih menggantung
        try:
            import psutil
            curr_pid = os.getpid()
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if p.info['pid'] != curr_pid and p.info['cmdline']:
                        cmd_s = " ".join(p.info['cmdline']).lower()
                        if "eksekusi_otomatis_trading_bot.py" in cmd_s and "m5" not in cmd_s:
                            p.kill()
                except Exception:
                    pass
        except Exception:
            pass

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

        # Pastikan tidak ada proses zombie M5 lain yang mengunci port / single instance
        try:
            import psutil
            curr_pid = os.getpid()
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if p.info['pid'] != curr_pid and p.info['cmdline']:
                        cmd_s = " ".join(p.info['cmdline']).lower()
                        if "eksekusi_otomatis_trading_bot_m5_scalping.py" in cmd_s:
                            p.kill()
                except Exception:
                    pass
            time.sleep(0.5)
        except Exception:
            pass

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

        # Bersihkan setiap proses background M5 yang masih menggantung
        try:
            import psutil
            curr_pid = os.getpid()
            for p in psutil.process_iter(['pid', 'cmdline']):
                try:
                    if p.info['pid'] != curr_pid and p.info['cmdline']:
                        cmd_s = " ".join(p.info['cmdline']).lower()
                        if "eksekusi_otomatis_trading_bot_m5_scalping.py" in cmd_s:
                            p.kill()
                except Exception:
                    pass
        except Exception:
            pass

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
            buf = []
            while True:
                ch = proc.stdout.read(1)
                if not ch:
                    break
                if ch in ('\r', '\n'):
                    if buf:
                        out_queue.put("".join(buf) + "\n")
                        buf = []
                else:
                    buf.append(ch)
            if buf:
                out_queue.put("".join(buf) + "\n")
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
        self.switch_nav("rekap")
        self.load_excel_view(mode)

    def set_filter_status(self, status):
        self.current_filter_status = status
        self.btn_filter_all.config(
            bg="#0284c7" if status == "ALL" else "#24252c",
            fg="#ffffff" if status == "ALL" else "#8e9192",
            font=("Segoe UI", 8, "bold" if status == "ALL" else "normal")
        )
        self.btn_filter_win.config(
            bg="#059669" if status == "WIN" else "#24252c",
            fg="#ffffff" if status == "WIN" else "#8e9192",
            font=("Segoe UI", 8, "bold" if status == "WIN" else "normal")
        )
        self.btn_filter_loss.config(
            bg="#dc2626" if status == "LOSS" else "#24252c",
            fg="#ffffff" if status == "LOSS" else "#8e9192",
            font=("Segoe UI", 8, "bold" if status == "LOSS" else "normal")
        )
        self.render_table_rows()

    def periodic_excel_rekap_refresh(self):
        try:
            self.update_portfolio_summary_labels()
            active = getattr(self, "current_active_pane", "m15")
            if active == "rekap" and not self.search_var.get().strip():
                if self.current_rekap_mode in ["m15", "m5"]:
                    self.load_excel_view(self.current_rekap_mode)
            elif active == "porto":
                self.load_porto_data()
            elif active == "diag" and not self.diag_search_var.get().strip():
                self.load_diag_data()
        except Exception:
            pass
        self.root.after(3000, self.periodic_excel_rekap_refresh)

    def refresh_current_view(self):
        self.update_portfolio_summary_labels()
        self.load_excel_view(self.current_rekap_mode)

    def refresh_rekap_data(self):
        # Dipanggil secara berkala untuk sinkronisasi otomatis
        self.update_portfolio_summary_labels()
        if self.current_rekap_mode in ["m15", "m5"]:
            self.load_excel_view(self.current_rekap_mode)
        elif self.current_rekap_mode == "mt5":
            self.load_excel_view("mt5")

    def update_portfolio_summary_labels(self):
        # Update M15 dari file Excel
        if os.path.exists(EXCEL_M15):
            try:
                xl15, sheets15 = safe_load_excel_sheets(EXCEL_M15)
                s_name = next((s for s in sheets15 if "v4.1" in s and "stat" not in s.lower()), None)
                if not s_name:
                    s_name = next((s for s in sheets15 if ("v4.0" in s or "v3.7" in s) and "stat" not in s.lower()), None)
                if not s_name:
                    s_name = next((s for s in sheets15 if "v3.6" in s and "stat" not in s.lower()), None)
                if not s_name and sheets15:
                    s_name = sheets15[0]
                if xl15 and s_name:
                    df = xl15.parse(s_name)
                    tot = len(df)
                    pnl = float(df["Profit ($ USD)"].sum()) if "Profit ($ USD)" in df and not df.empty else 0.0
                    wins = len(df[df["Hasil"] == "WIN"]) if "Hasil" in df and not df.empty else 0
                    loss = len(df[df["Hasil"] == "LOSS"]) if "Hasil" in df and not df.empty else 0
                    wr = (wins / tot * 100) if tot > 0 else 0.0
                    saldo = 500.0 + pnl
                    v_tag = "v4.1" if "v4.1" in s_name else ("v3.7" if "v3.7" in s_name else "v3.6")
                    self.lbl_rekap_m15.config(
                        text=f"Total Trade : {tot} Transaksi ({v_tag})\nWin / Loss  : {wins} WIN / {loss} LOSS\nWin Rate    : {wr:.1f}%\nNet PnL     : ${pnl:+.2f} USD\nSaldo       : ${saldo:.2f} USD"
                    )
            except Exception:
                pass

        # Update M5 dari file Excel
        if os.path.exists(EXCEL_M5):
            try:
                xl5, sheets5 = safe_load_excel_sheets(EXCEL_M5)
                s_name = next((s for s in sheets5 if "v4.1" in s and "stat" not in s.lower()), None)
                if not s_name:
                    s_name = next((s for s in sheets5 if ("v4.0" in s or "v3.7" in s) and "stat" not in s.lower()), None)
                if not s_name:
                    s_name = next((s for s in sheets5 if "v3.6" in s and "stat" not in s.lower()), None)
                if not s_name and sheets5:
                    s_name = sheets5[0]
                if xl5 and s_name:
                    df = xl5.parse(s_name)
                    tot = len(df)
                    pnl = float(df["Profit ($ USD)"].sum()) if "Profit ($ USD)" in df and not df.empty else 0.0
                    wins = len(df[df["Hasil"] == "WIN"]) if "Hasil" in df and not df.empty else 0
                    loss = len(df[df["Hasil"] == "LOSS"]) if "Hasil" in df and not df.empty else 0
                    wr = (wins / tot * 100) if tot > 0 else 0.0
                    saldo = 500.0 + pnl
                    v_tag = "v4.1" if "v4.1" in s_name else ("v3.7" if "v3.7" in s_name else "v3.6")
                    self.lbl_rekap_m5.config(
                        text=f"Total Trade : {tot} Transaksi ({v_tag})\nWin / Loss  : {wins} WIN / {loss} LOSS\nWin Rate    : {wr:.1f}%\nNet PnL     : ${pnl:+.2f} USD\nSaldo       : ${saldo:.2f} USD"
                    )
            except Exception:
                pass

    def load_excel_view(self, mode="m15"):
        self.current_rekap_mode = mode
        if hasattr(self, 'set_filter_status'):
            # Reset filter status ke ALL saat berpindah tab agar tidak menyembunyikan data
            self.set_filter_status("ALL")

        # Update visual tombol nav aktif
        self.btn_nav_m15.config(bg="#ffffff" if mode == "m15" else "#24252c", fg="#0d0e13" if mode == "m15" else "#8e9192")
        self.btn_nav_m5.config(bg="#ffffff" if mode == "m5" else "#24252c", fg="#0d0e13" if mode == "m5" else "#8e9192")
        self.btn_nav_stat.config(bg="#ffffff" if mode == "stat" else "#24252c", fg="#0d0e13" if mode == "stat" else "#8e9192")
        self.btn_nav_mt5.config(bg="#ffffff" if mode == "mt5" else "#24252c", fg="#0d0e13" if mode == "mt5" else "#8e9192")

        self.current_data_rows = []

        if mode in ["m15", "m5"]:
            self.filter_strip.pack(fill="x", pady=(0, 8))

            cols = ("no", "ticket", "w_open", "w_close", "durasi", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "saldo", "hasil", "alasan")
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
                ("saldo", "Saldo ($)", 95, "center"),
                ("hasil", "Hasil", 65, "center"),
                ("alasan", "Alasan Exit / Keterangan", 220, "w"),
            ]
            for cid, heading, width, anchor in col_defs:
                self.tree.heading(cid, text=heading)
                self.tree.column(cid, width=width, anchor=anchor, stretch=(cid == "alasan"))

            target_excel = EXCEL_M15 if mode == "m15" else EXCEL_M5

            if os.path.exists(target_excel):
                try:
                    xl, avail_sheets = safe_load_excel_sheets(target_excel)
                    sheet_name = next((s for s in avail_sheets if "v4.1" in s and "stat" not in s.lower()), None)
                    if not sheet_name:
                        sheet_name = next((s for s in avail_sheets if ("v4.0" in s or "v3.7" in s) and "stat" not in s.lower()), None)
                    if not sheet_name:
                        sheet_name = next((s for s in avail_sheets if "v3.6" in s and "stat" not in s.lower()), None)
                    if not sheet_name and avail_sheets:
                        sheet_name = avail_sheets[0]

                    v_tag = "v4.1" if (sheet_name and "v4.1" in sheet_name) else ("v3.7" if (sheet_name and "v3.7" in sheet_name) else "v3.6")
                    model_label = f"M15 Konservatif ({v_tag})" if mode == "m15" else f"M5 Scalper ({v_tag})"

                    df = xl.parse(sheet_name) if (xl and sheet_name) else pd.DataFrame()
                    wins, loss, total_pnl = 0, 0, 0.0
                    running_bal = 500.0
                    for _, r in df.iterrows():
                        pnl = float(r.get("Profit ($ USD)", 0.0))
                        total_pnl += pnl
                        hasil_str = str(r.get("Hasil", "")).strip().upper()
                        if hasil_str == "WIN": wins += 1
                        elif hasil_str == "LOSS": loss += 1

                        sl_val = r.get("Stop Loss (SL)")
                        tp_val = r.get("Take Profit (TP)")
                        saldo_val = r.get("Saldo ($ USD)")
                        if pd.notna(saldo_val):
                            saldo_disp = f"${float(saldo_val):.2f}"
                        else:
                            running_bal += pnl
                            saldo_disp = f"${running_bal:.2f}"

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
                                saldo_disp,
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
                        text=f"Total: {tot} Trade  |  {wins} WIN / {loss} LOSS (Win Rate: {wr:.1f}%)  |  Net PnL: ${total_pnl:+.2f} USD  |  Saldo: ${500.0 + total_pnl:.2f} USD  |  File: {os.path.basename(target_excel)}"
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

            self.lbl_table_title.config(text="📈 RINGKASAN STATISTIK & PERBANDINGAN MODEL M15 vs M5 (v4.1)", fg="#818cf8")
            self.lbl_table_subtitle.config(text="Perbandingan indikator kinerja forward testing langsung dari lembar Ringkasan Statistik Excel.")

            try:
                xl15, sheets15 = safe_load_excel_sheets(EXCEL_M15)
                s15_name = next((s for s in sheets15 if ("v4.1" in s or "v4.0" in s or "v3.7" in s) and "stat" in s.lower()), None)
                if not s15_name:
                    s15_name = next((s for s in sheets15 if "v3.6" in s and "stat" in s.lower()), None)
                if not s15_name:
                    s15_name = next((s for s in sheets15 if "stat" in s.lower()), None)
                s15 = xl15.parse(s15_name) if (xl15 and s15_name) else pd.DataFrame()

                xl5, sheets5 = safe_load_excel_sheets(EXCEL_M5)
                s5_name = next((s for s in sheets5 if ("v4.1" in s or "v4.0" in s or "v3.7" in s) and "stat" in s.lower()), None)
                if not s5_name:
                    s5_name = next((s for s in sheets5 if "v3.6" in s and "stat" in s.lower()), None)
                if not s5_name:
                    s5_name = next((s for s in sheets5 if "stat" in s.lower()), None)
                s5 = xl5.parse(s5_name) if (xl5 and s5_name) else pd.DataFrame()

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
                else:
                    self.lbl_table_subtitle.config(text="Belum ada data ringkasan statistik.")
            except Exception as e:
                self.lbl_table_subtitle.config(text=f"Gagal memuat statistik: {e}")

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

            # Filter WIN/LOSS (hanya untuk baris transaksi WIN/LOSS/BE, jangan filter baris STAT)
            if hasil in ["WIN", "LOSS", "BE"]:
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
        modal.configure(bg="#0d0e13")

        # Header Bar Modal
        top_bar = tk.Frame(modal, bg="#1a1b21", relief="solid", bd=1, padx=15, pady=10)
        top_bar.pack(fill="x", padx=15, pady=10)

        t_box = tk.Frame(top_bar, bg="#1a1b21")
        t_box.pack(side="left")
        tk.Label(t_box, text="📑 JENDELA LENGKAP EXCEL DATA VIEWER", font=("Segoe UI", 13, "bold"), fg="#38bdf8", bg="#1a1b21").pack(anchor="w")
        tk.Label(t_box, text="Pemantauan log transaksi dan ringkasan forward testing real-time tanpa perlu membuka Microsoft Excel", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21").pack(anchor="w")

        r_box = tk.Frame(top_bar, bg="#1a1b21")
        r_box.pack(side="right")
        tk.Button(r_box, text="📂 Buka Folder Proyek", font=("Segoe UI", 8), fg="#c4c7c8", bg="#1f2937", relief="flat", cursor="hand2", command=lambda: os.startfile(BASE_DIR), padx=10, pady=5).pack(side="left", padx=4)
        tk.Button(r_box, text="🔄 Refresh Semua Tab", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#24252c", relief="flat", cursor="hand2", command=lambda: self.populate_modal_tabs(modal_nb), padx=10, pady=5).pack(side="left")

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

        tab1 = self.build_modal_excel_tab(modal_nb, EXCEL_M15, "Trade Log Model Terbaru (v4.1)", is_stats=False, model_name="M15 v4.1")
        modal_nb.add(tab1, text="  📊 Log M15 (v4.1)  ")

        tab2 = self.build_modal_excel_tab(modal_nb, EXCEL_M5, "Trade Log M5 Scalping (v4.1)", is_stats=False, model_name="M5 v4.1")
        modal_nb.add(tab2, text="  ⚡ Log M5 (v4.1)  ")

        tab3 = self.build_modal_excel_tab(modal_nb, EXCEL_M15, "Ringkasan Statistik (v4.1)", is_stats=True, model_name="Statistik M15 v4.1")
        modal_nb.add(tab3, text="  📈 Statistik M15 (v4.1)  ")

        tab4 = self.build_modal_excel_tab(modal_nb, EXCEL_M5, "Ringkasan Statistik (v4.1)", is_stats=True, model_name="Statistik M5 v4.1")
        modal_nb.add(tab4, text="  📈 Statistik M5 (v4.1)  ")

        tab5 = self.build_modal_excel_tab(modal_nb, EXCEL_M15, "Trade Log Model Terbaru (v3.6)", is_stats=False, model_name="Arsip M15 v3.6")
        modal_nb.add(tab5, text="  📁 Arsip M15 (v3.6)  ")

        tab6 = self.build_modal_excel_tab(modal_nb, EXCEL_M5, "Trade Log M5 Scalping (v3.6)", is_stats=False, model_name="Arsip M5 v3.6")
        modal_nb.add(tab6, text="  📁 Arsip M5 (v3.6)  ")

    def build_modal_excel_tab(self, parent, file_path, sheet_name, is_stats=False, model_name=""):
        frame = tk.Frame(parent, bg="#0d0e13")

        bar = tk.Frame(frame, bg="#13141a", padx=12, pady=8)
        bar.pack(fill="x", padx=10, pady=(10, 6))

        info_lbl = tk.Label(bar, text=f"Memuat data {sheet_name}...", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#13141a")
        info_lbl.pack(side="left")

        search_box = tk.Frame(bar, bg="#13141a")
        search_box.pack(side="right")
        tk.Label(search_box, text="🔍 Cari:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#13141a").pack(side="left", padx=4)
        search_v = tk.StringVar()
        s_entry = tk.Entry(search_box, textvariable=search_v, font=("Segoe UI", 8), bg="#24252c", fg="#ffffff", relief="flat", width=20)
        s_entry.pack(side="left", padx=4)

        tree_box = tk.Frame(frame, bg="#13141a")
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
        tree.tag_configure("normal", foreground="#ffffff", font=("Consolas", 9))
        tree.tag_configure("stat_k", foreground="#38bdf8", font=("Segoe UI", 9, "bold"))

        rows_data = []

        if os.path.exists(file_path):
            try:
                xl, avail_sheets = safe_load_excel_sheets(file_path)
                if xl and sheet_name in avail_sheets:
                    df = xl.parse(sheet_name)
                elif xl and avail_sheets:
                    matched = next((s for s in avail_sheets if sheet_name.lower() in s.lower()), avail_sheets[0])
                    df = xl.parse(matched)
                else:
                    df = pd.DataFrame()

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
                    cols = ("no", "ticket", "w_open", "w_close", "durasi", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "saldo", "hasil", "alasan")
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
                        ("saldo", "Saldo ($)", 90, "center"),
                        ("hasil", "Hasil", 65, "center"),
                        ("alasan", "Keterangan / Alasan Exit", 220, "w"),
                    ]
                    for cid, h, w, a in col_defs:
                        tree.heading(cid, text=h)
                        tree.column(cid, width=w, anchor=a)

                    wins, loss, pnl_tot = 0, 0, 0.0
                    running_bal = 500.0
                    for _, r in df.iterrows():
                        pnl = float(r.get("Profit ($ USD)", 0.0))
                        pnl_tot += pnl
                        h_str = str(r.get("Hasil", "")).strip().upper()
                        if h_str == "WIN": wins += 1
                        elif h_str == "LOSS": loss += 1

                        sl_val = r.get("Stop Loss (SL)")
                        tp_val = r.get("Take Profit (TP)")
                        saldo_val = r.get("Saldo ($ USD)")
                        if pd.notna(saldo_val):
                            saldo_disp = f"${float(saldo_val):.2f}"
                        else:
                            running_bal += pnl
                            saldo_disp = f"${running_bal:.2f}"

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
                            saldo_disp,
                            h_str,
                            str(r.get("Keterangan / Alasan Exit", ""))
                        )
                        rows_data.append({"vals": vals, "tag": tag})

                    tot = len(df)
                    wr = (wins / tot * 100) if tot > 0 else 0.0
                    info_lbl.config(text=f"📊 {model_name}: {tot} Trade | {wins} WIN / {loss} LOSS ({wr:.1f}%) | Net PnL: ${pnl_tot:+.2f} USD | Saldo: ${500.0 + pnl_tot:.2f}")

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

    # =========================================================================
    # TAB 4: PERJALANAN PORTOFOLIO & EQUITY CURVE (PROP FIRM & MYFXBOOK STYLE)
    # =========================================================================
    def setup_porto_tab(self):
        container = tk.Frame(self.tab_porto, bg="#0d0e13")
        container.pack(fill="both", expand=True, padx=12, pady=10)

        # ── 1. PORTFOLIO SUMMARY METRIC CARDS (PROP FIRM STYLE) ──
        cards_outer = tk.Frame(container, bg="#0d0e13")
        cards_outer.pack(fill="x", pady=(0, 10))

        self.porto_card_labels = {}
        metrics = [
            ("initial_bal", "INITIAL BALANCE", "$500.00", "#8e9192"),
            ("balance", "CURRENT BALANCE", "$518.95", "#38bdf8"),
            ("pnl", "TOTAL PnL", "+$18.95", "#10b981"),
            ("growth", "GROWTH", "+3.79%", "#10b981"),
            ("winrate", "WIN RATE", "48.6%", "#f59e0b"),
            ("trades", "TOTAL TRADES", "35 Trades", "#c084fc"),
            ("drawdown", "MAX DRAWDOWN", "5.73%", "#ef4444"),
            ("pf", "PROFIT FACTOR", "1.20", "#38bdf8")
        ]
        
        for k, title, default_v, default_color in metrics:
            c = tk.Frame(cards_outer, bg="#13141a", relief="solid", bd=1, padx=10, pady=8)
            c.pack(side="left", fill="both", expand=True, padx=3)
            tk.Label(c, text=title, font=("Segoe UI", 7, "bold"), fg="#5a5c63", bg="#13141a").pack(anchor="w")
            v_lbl = tk.Label(c, text=default_v, font=("Segoe UI", 12, "bold"), fg=default_color, bg="#13141a")
            v_lbl.pack(anchor="w", pady=(2, 0))
            self.porto_card_labels[k] = v_lbl

        # ── 2. EQUITY CURVE CANVAS & CONTROLS ──
        chart_box = tk.Frame(container, bg="#13141a", relief="solid", bd=1, padx=12, pady=8)
        chart_box.pack(fill="x", pady=(0, 10))

        chart_head = tk.Frame(chart_box, bg="#13141a")
        chart_head.pack(fill="x", pady=(0, 6))

        tk.Label(chart_head, text="📈 EQUITY CURVE & PERJALANAN PORTOFOLIO", font=("Segoe UI", 10, "bold"), fg="#38bdf8", bg="#13141a").pack(side="left")

        mode_box = tk.Frame(chart_head, bg="#13141a")
        mode_box.pack(side="right")

        self.btn_curve_equity = tk.Button(mode_box, text="💰 Saldo ($)", font=("Segoe UI", 8, "bold"), fg="#0d0e13", bg="#ffffff", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.set_porto_curve_mode("equity"), padx=8, pady=2)
        self.btn_curve_equity.pack(side="left", padx=2)

        self.btn_curve_growth = tk.Button(mode_box, text="📈 Pertumbuhan (%)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_porto_curve_mode("growth"), padx=8, pady=2)
        self.btn_curve_growth.pack(side="left", padx=2)

        self.btn_curve_dd = tk.Button(mode_box, text="📉 Drawdown (%)", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_porto_curve_mode("drawdown"), padx=8, pady=2)
        self.btn_curve_dd.pack(side="left", padx=2)

        btn_refresh_curve = tk.Button(mode_box, text="🔄 Refresh", font=("Segoe UI", 8), fg="#38bdf8", bg="#24252c", activebackground="#2e3038", relief="flat", cursor="hand2", command=self.load_porto_data, padx=8, pady=2)
        btn_refresh_curve.pack(side="left", padx=(6, 0))

        # Interactive Canvas with Hover Tooltip
        self.porto_canvas = tk.Canvas(chart_box, bg="#0b1120", height=180, highlightthickness=0)
        self.porto_canvas.pack(fill="x", expand=True)
        self.porto_canvas.bind("<Configure>", lambda e: self.draw_equity_curve_canvas())
        self.porto_canvas.bind("<Motion>", self.on_porto_canvas_motion)
        self.porto_canvas.bind("<Leave>", self.on_porto_canvas_leave)

        # ── 3. LOWER AREA: PERIODS PERFORMANCE & TRADE JOURNAL ──
        lower_paned = tk.PanedWindow(container, orient="vertical", bg="#0d0e13", bd=0, sashwidth=4)
        lower_paned.pack(fill="both", expand=True)

        # Upper child of lower_paned: Periods Table
        periods_frame = tk.Frame(lower_paned, bg="#13141a", relief="solid", bd=1, padx=10, pady=8)
        lower_paned.add(periods_frame, minsize=100)

        p_head = tk.Frame(periods_frame, bg="#13141a")
        p_head.pack(fill="x", pady=(0, 4))
        tk.Label(p_head, text="⏱️ RINGKASAN PERFORMA PERIODE (MYFXBOOK STYLE)", font=("Segoe UI", 9, "bold"), fg="#10b981", bg="#13141a").pack(side="left")

        self.tree_periods = ttk.Treeview(
            periods_frame,
            columns=("periode", "gain", "profit", "trades", "winrate", "status"),
            show="headings",
            height=4
        )
        self.tree_periods.pack(fill="x", expand=True)
        p_cols = [
            ("periode", "Periode", 150, "w"),
            ("gain", "Gain (%)", 100, "center"),
            ("profit", "Net Profit ($)", 120, "center"),
            ("trades", "Total Trades", 100, "center"),
            ("winrate", "Win Rate (%)", 110, "center"),
            ("status", "Kinerja", 180, "w")
        ]
        for cid, h, w, a in p_cols:
            self.tree_periods.heading(cid, text=h)
            self.tree_periods.column(cid, width=w, anchor=a)

        self.tree_periods.tag_configure("green", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.tree_periods.tag_configure("neutral", foreground="#8e9192", font=("Segoe UI", 9))

        # Lower child of lower_paned: Trade Journal
        journal_frame = tk.Frame(lower_paned, bg="#13141a", relief="solid", bd=1, padx=10, pady=8)
        lower_paned.add(journal_frame, minsize=160)

        j_head = tk.Frame(journal_frame, bg="#13141a")
        j_head.pack(fill="x", pady=(0, 4))
        tk.Label(j_head, text="📖 JURNAL TRANSAKSI PORTOFOLIO", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#13141a").pack(side="left")
        self.lbl_journal_count = tk.Label(j_head, text="35 Trades Tercatat", font=("Segoe UI", 8), fg="#8e9192", bg="#13141a")
        self.lbl_journal_count.pack(side="right")

        j_tree_box = tk.Frame(journal_frame, bg="#13141a")
        j_tree_box.pack(fill="both", expand=True)

        j_scry = ttk.Scrollbar(j_tree_box, orient="vertical")
        j_scry.pack(side="right", fill="y")
        j_scrx = ttk.Scrollbar(j_tree_box, orient="horizontal")
        j_scrx.pack(side="bottom", fill="x")

        self.tree_journal = ttk.Treeview(
            j_tree_box,
            columns=("no", "ticket", "w_open", "w_close", "durasi", "simbol", "tipe", "lot", "entry", "sl", "tp", "exit", "pips", "profit", "saldo", "gain", "hasil", "alasan"),
            show="headings",
            yscrollcommand=j_scry.set,
            xscrollcommand=j_scrx.set
        )
        self.tree_journal.pack(fill="both", expand=True)
        j_scry.config(command=self.tree_journal.yview)
        j_scrx.config(command=self.tree_journal.xview)

        j_col_defs = [
            ("no", "#", 40, "center"),
            ("ticket", "Ticket", 95, "center"),
            ("w_open", "Waktu Open", 125, "center"),
            ("w_close", "Waktu Close", 125, "center"),
            ("durasi", "Durasi", 70, "center"),
            ("simbol", "Simbol", 65, "center"),
            ("tipe", "Arah", 55, "center"),
            ("lot", "Lot", 50, "center"),
            ("entry", "Entry", 85, "center"),
            ("sl", "SL", 85, "center"),
            ("tp", "TP", 85, "center"),
            ("exit", "Exit", 85, "center"),
            ("pips", "Pips", 60, "center"),
            ("profit", "Profit ($)", 85, "center"),
            ("saldo", "Saldo ($)", 85, "center"),
            ("gain", "Gain %", 65, "center"),
            ("hasil", "Hasil", 60, "center"),
            ("alasan", "Keterangan Exit", 200, "w"),
        ]
        for cid, h, w, a in j_col_defs:
            self.tree_journal.heading(cid, text=h)
            self.tree_journal.column(cid, width=w, anchor=a)

        self.tree_journal.tag_configure("win", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.tree_journal.tag_configure("loss", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        self.tree_journal.tag_configure("normal", foreground="#ffffff", font=("Consolas", 9))

        self.load_porto_data()

    def set_porto_curve_mode(self, mode):
        self.porto_curve_mode = mode
        for m, btn in [("equity", self.btn_curve_equity), ("growth", self.btn_curve_growth), ("drawdown", self.btn_curve_dd)]:
            if m == mode:
                btn.config(bg="#ffffff" if m != "drawdown" else "#ef4444", fg="#0d0e13" if m != "drawdown" else "#ffffff")
            else:
                btn.config(bg="#24252c", fg="#8e9192")
        self.draw_equity_curve_canvas()

    def load_porto_data(self):
        """Membaca Evaluasi_Skenario_Trade.csv dan menghitung metrik perjalanan portofolio."""
        if not os.path.exists(CSV_EVAL):
            return

        try:
            df = pd.read_csv(CSV_EVAL)
            if df.empty:
                return

            CUTOFF_DATE = "2026-09-18 21:55:00"
            if "Waktu Open" in df.columns:
                df = df[df["Waktu Open"] >= CUTOFF_DATE].copy().reset_index(drop=True)
            if df.empty:
                return

            init_bal = 500.0
            cur_bal = init_bal
            peak_bal = init_bal
            max_dd_dollars = 0.0
            max_dd_pct = 0.0

            points = [{"no": 0, "time": "Initial", "balance": 500.0, "pnl": 0.0, "growth": 0.0, "drawdown": 0.0}]
            trades = []

            wins, losses = 0, 0
            win_dollars, loss_dollars = 0.0, 0.0

            today_str = datetime.now().strftime("%Y-%m-%d")
            today_wins, today_trades, today_pnl = 0, 0, 0.0

            for idx, r in df.iterrows():
                pnl = float(r.get("Profit ($ USD)", 0.0))
                h = str(r.get("Hasil", "")).strip().upper()
                w_close = str(r.get("Waktu Close", ""))

                if h == "WIN":
                    wins += 1
                    win_dollars += pnl
                elif h == "LOSS":
                    losses += 1
                    loss_dollars += abs(pnl)

                cur_bal += pnl
                if cur_bal > peak_bal:
                    peak_bal = cur_bal
                dd_d = max(0.0, peak_bal - cur_bal)
                dd_p = (dd_d / peak_bal * 100.0) if peak_bal > 0 else 0.0
                if dd_d > max_dd_dollars:
                    max_dd_dollars = dd_d
                if dd_p > max_dd_pct:
                    max_dd_pct = dd_p

                growth = ((cur_bal - init_bal) / init_bal) * 100.0

                points.append({
                    "no": idx + 1,
                    "time": w_close.split()[0] if " " in w_close else w_close,
                    "balance": cur_bal,
                    "pnl": pnl,
                    "growth": growth,
                    "drawdown": dd_p
                })

                if today_str in w_close:
                    today_trades += 1
                    today_pnl += pnl
                    if h == "WIN":
                        today_wins += 1

                trades.append({
                    "no": idx + 1,
                    "ticket": int(r.get("Ticket Posisi", 0)),
                    "w_open": str(r.get("Waktu Open", "")),
                    "w_close": w_close,
                    "durasi": str(r.get("Durasi", "")),
                    "simbol": str(r.get("Simbol", "XAUUSD")),
                    "tipe": str(r.get("Tipe", "")),
                    "lot": f"{float(r.get('Lot', 0.01)):.2f}",
                    "entry": f"${float(r.get('Harga Entry', 0)):.2f}",
                    "sl": f"${float(r.get('Stop Loss (SL)', 0)):.2f}" if pd.notna(r.get('Stop Loss (SL)')) and float(r.get('Stop Loss (SL)', 0)) > 0 else "-",
                    "tp": f"${float(r.get('Take Profit (TP)', 0)):.2f}" if pd.notna(r.get('Take Profit (TP)')) and float(r.get('Take Profit (TP)', 0)) > 0 else "-",
                    "exit": f"${float(r.get('Harga Exit', 0)):.2f}",
                    "pips": f"{float(r.get('Pips (P/L)', 0)):+.1f}",
                    "profit": f"${pnl:+.2f}",
                    "saldo": f"${cur_bal:.2f}",
                    "gain": f"{(pnl / init_bal * 100.0):+.2f}%",
                    "hasil": h,
                    "alasan": str(r.get("Keterangan / Alasan Exit", ""))
                })

            tot_trades = len(df)
            wr = (wins / tot_trades * 100.0) if tot_trades > 0 else 0.0
            net_pnl = cur_bal - init_bal
            tot_growth = (net_pnl / init_bal) * 100.0
            pf = (win_dollars / loss_dollars) if loss_dollars > 0 else 0.0

            self.porto_points = points
            self.porto_trades = trades

            # Update Metric Cards
            if hasattr(self, 'porto_card_labels'):
                self.porto_card_labels["initial_bal"].config(text=f"${init_bal:.2f}")
                self.porto_card_labels["balance"].config(text=f"${cur_bal:.2f}", fg="#38bdf8" if cur_bal >= init_bal else "#ef4444")
                self.porto_card_labels["pnl"].config(text=f"{'+' if net_pnl >= 0 else ''}${net_pnl:.2f}", fg="#10b981" if net_pnl >= 0 else "#ef4444")
                self.porto_card_labels["growth"].config(text=f"{'+' if tot_growth >= 0 else ''}{tot_growth:.2f}%", fg="#10b981" if tot_growth >= 0 else "#ef4444")
                self.porto_card_labels["winrate"].config(text=f"{wr:.1f}% ({wins}W / {losses}L)")
                self.porto_card_labels["trades"].config(text=f"{tot_trades} Trades")
                self.porto_card_labels["drawdown"].config(text=f"{max_dd_pct:.2f}% (${max_dd_dollars:.2f})")
                self.porto_card_labels["pf"].config(text=f"{pf:.2f}")

            # Update Periods Table
            if hasattr(self, 'tree_periods'):
                for itm in self.tree_periods.get_children():
                    self.tree_periods.delete(itm)

                periods_data = [
                    ("Hari Ini", f"+{(today_pnl / init_bal * 100.0):.2f}%", f"+${today_pnl:.2f}", f"{today_trades}", f"{(today_wins / today_trades * 100.0) if today_trades > 0 else 0.0:.1f}%", "🔥 All WIN (100% Sempurna)" if today_trades > 0 and today_wins == today_trades else "Stabil"),
                    ("Minggu Ini", f"+{(today_pnl / init_bal * 100.0):.2f}%", f"+${today_pnl:.2f}", f"{today_trades}", f"{(today_wins / today_trades * 100.0) if today_trades > 0 else 0.0:.1f}%", "🔥 Tren Positif"),
                    ("Bulan Ini", f"{'+' if tot_growth >= 0 else ''}{tot_growth:.2f}%", f"{'+' if net_pnl >= 0 else ''}${net_pnl:.2f}", f"{tot_trades}", f"{wr:.1f}%", "✅ Konsisten Profit"),
                    ("Sepanjang Waktu", f"{'+' if tot_growth >= 0 else ''}{tot_growth:.2f}%", f"{'+' if net_pnl >= 0 else ''}${net_pnl:.2f}", f"{tot_trades}", f"{wr:.1f}%", "🏆 Portofolio Bertumbuh")
                ]
                for row in periods_data:
                    tag = "green" if "+" in row[1] else "neutral"
                    self.tree_periods.insert("", "end", values=row, tags=(tag,))

            # Update Journal Table (Terbaru di atas)
            if hasattr(self, 'tree_journal'):
                for itm in self.tree_journal.get_children():
                    self.tree_journal.delete(itm)

                for t in reversed(trades):
                    tag = "win" if t["hasil"] == "WIN" else ("loss" if t["hasil"] == "LOSS" else "normal")
                    vals = (
                        t["no"], t["ticket"], t["w_open"], t["w_close"], t["durasi"], t["simbol"],
                        t["tipe"], t["lot"], t["entry"], t["sl"], t["tp"], t["exit"],
                        t["pips"], t["profit"], t["saldo"], t["gain"], t["hasil"], t["alasan"]
                    )
                    self.tree_journal.insert("", "end", values=vals, tags=(tag,))

            if hasattr(self, 'lbl_journal_count'):
                self.lbl_journal_count.config(text=f"{len(trades)} Trades Tercatat")
            self.draw_equity_curve_canvas()
        except Exception as e:
            print(f"[ERROR load_porto_data]: {e}")

    def draw_equity_curve_canvas(self):
        """Menggambar kurva ekuitas / pertumbuhan di atas Canvas Tkinter dengan styling modern."""
        if not hasattr(self, 'porto_canvas'):
            return
        canvas = self.porto_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w < 50 or h < 50 or not self.porto_points:
            return

        pad_left = 65
        pad_right = 30
        pad_top = 25
        pad_bottom = 30

        plot_w = w - pad_left - pad_right
        plot_h = h - pad_top - pad_bottom

        mode = self.porto_curve_mode
        if mode == "growth":
            values = [p["growth"] for p in self.porto_points]
            val_format = "{:+.1f}%"
            line_color = "#10b981"
            fill_color = "#064e3b"
            base_val = 0.0
        elif mode == "drawdown":
            values = [p["drawdown"] for p in self.porto_points]
            val_format = "-{:.1f}%"
            line_color = "#ef4444"
            fill_color = "#450a0a"
            base_val = 0.0
        else:  # equity
            values = [p["balance"] for p in self.porto_points]
            val_format = "${:.2f}"
            line_color = "#ffffff"
            fill_color = "#161720"
            base_val = 500.0

        min_v = min(values)
        max_v = max(values)
        if mode == "equity":
            min_v = min(min_v, 490.0)
            max_v = max(max_v, 545.0)
        elif mode == "growth":
            min_v = min(min_v, -2.0)
            max_v = max(max_v, 9.0)
        else:
            min_v = 0.0
            max_v = max(max_v, 7.0)

        v_range = max(0.001, max_v - min_v)

        def get_coords(idx, v):
            x = pad_left + (idx / max(1, len(values) - 1)) * plot_w
            y = pad_top + plot_h - ((v - min_v) / v_range) * plot_h
            return x, y

        # Horizontal Gridlines (4 lines)
        for i in range(5):
            val = min_v + (v_range / 4.0) * i
            y = pad_top + plot_h - (i / 4.0) * plot_h
            canvas.create_line(pad_left, y, w - pad_right, y, fill="#24252c", dash=(2, 4))
            canvas.create_text(pad_left - 8, y, text=val_format.format(val), font=("Segoe UI", 7), fill="#5a5c63", anchor="e")

        # Baseline (500 or 0)
        if min_v <= base_val <= max_v:
            _, by = get_coords(0, base_val)
            canvas.create_line(pad_left, by, w - pad_right, by, fill="#475569", width=1, dash=(4, 4))

        # Generate polyline coordinates
        coords = []
        for idx, val in enumerate(values):
            x, y = get_coords(idx, val)
            coords.append((x, y))

        # Polygon fill under the curve
        poly_coords = [pad_left, pad_top + plot_h]
        for x, y in coords:
            poly_coords.extend([x, y])
        poly_coords.extend([pad_left + plot_w, pad_top + plot_h])

        try:
            canvas.create_polygon(poly_coords, fill=fill_color, outline="")
        except Exception:
            pass

        # Draw main curve line
        if len(coords) > 1:
            flat_coords = [coord for pt in coords for coord in pt]
            canvas.create_line(flat_coords, fill=line_color, width=2, smooth=True)

        # Draw dots & markers
        for idx, (x, y) in enumerate(coords):
            p = self.porto_points[idx]
            pnl = p["pnl"]
            dot_color = "#38bdf8" if idx == 0 else ("#ffffff" if pnl >= 0 else "#ef4444")
            r = 3 if idx in (0, len(coords)-1) or values[idx] == max(values) else 2
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=dot_color, outline="#0d0e13")

        # Label start and end
        if coords:
            sx, sy = coords[0]
            canvas.create_text(sx + 5, sy - 10, text="Awal: $500", font=("Segoe UI", 7, "bold"), fill="#8e9192", anchor="w")

            ex, ey = coords[-1]
            canvas.create_text(ex - 5, ey - 10, text=f"Akhir: {val_format.format(values[-1])}", font=("Segoe UI", 8, "bold"), fill=line_color, anchor="e")

        # Simpan parameter koordinat untuk interaktivitas hover
        self.curve_coords = coords
        self.curve_plot_params = (pad_left, pad_top, plot_w, plot_h, val_format)

    def on_porto_canvas_motion(self, event):
        """Menampilkan tooltip dan crosshair interaktif saat kursor mouse di-hover di atas grafik ekuitas."""
        if not hasattr(self, 'porto_canvas'):
            return
        canvas = self.porto_canvas
        canvas.delete("chart_hover")
        if not hasattr(self, 'curve_coords') or not self.curve_coords or not hasattr(self, 'porto_points') or not self.porto_points:
            return

        pad_left, pad_top, plot_w, plot_h, val_format = getattr(self, 'curve_plot_params', (65, 25, 1000, 120, "${:.2f}"))
        if event.x < pad_left - 15 or event.x > pad_left + plot_w + 15:
            return

        # Cari titik koordinat terdekat secara horizontal
        closest_idx = 0
        min_dist = float('inf')
        for idx, (cx, cy) in enumerate(self.curve_coords):
            d = abs(cx - event.x)
            if d < min_dist:
                min_dist = d
                closest_idx = idx

        if closest_idx >= len(self.curve_coords) or closest_idx >= len(self.porto_points):
            return

        x, y = self.curve_coords[closest_idx]
        p = self.porto_points[closest_idx]

        # 1. Gambar garis panduan vertikal (crosshair dashed)
        canvas.create_line(x, pad_top, x, pad_top + plot_h, fill="#38bdf8", dash=(2, 2), width=1, tags="chart_hover")

        # 2. Gambar lingkaran highlight menyala (glow ring)
        canvas.create_oval(x - 7, y - 7, x + 7, y + 7, outline="#38bdf8", width=2, tags="chart_hover")
        canvas.create_oval(x - 4, y - 4, x + 4, y + 4, fill="#ffffff", outline="", tags="chart_hover")

        # 3. Format isi teks tooltip
        t_no = p.get("no", 0)
        t_title = f"Trade #{t_no} ({p.get('time', '-')})" if t_no > 0 else "Titik Awal ($500.00)"
        bal_str = f"Saldo: ${p.get('balance', 500.0):.2f}"
        pnl_val = p.get('pnl', 0.0)
        growth_val = p.get('growth', 0.0)
        pnl_str = f"PnL: {'+' if pnl_val >= 0 else ''}${pnl_val:.2f} ({'+' if growth_val >= 0 else ''}{growth_val:.2f}%)"
        dd_str = f"Max DD: -{p.get('drawdown', 0.0):.2f}%"

        # 4. Tentukan posisi kotak tooltip agar tidak terpotong tepi layar
        can_w = canvas.winfo_width()
        tip_w = 180
        tip_h = 68
        tip_x = x + 15 if x + tip_w + 20 < can_w else x - tip_w - 15
        tip_y = max(pad_top + 5, min(y - 25, pad_top + plot_h - tip_h - 5))

        # 5. Gambar kotak tooltip elegan bergaya obsidian
        canvas.create_rectangle(tip_x, tip_y, tip_x + tip_w, tip_y + tip_h, fill="#13141a", outline="#38bdf8", width=1, tags="chart_hover")
        canvas.create_text(tip_x + 10, tip_y + 12, text=t_title, font=("Segoe UI", 8, "bold"), fill="#38bdf8", anchor="w", tags="chart_hover")
        canvas.create_text(tip_x + 10, tip_y + 28, text=bal_str, font=("Consolas", 8, "bold"), fill="#ffffff", anchor="w", tags="chart_hover")
        pnl_color = "#10b981" if pnl_val >= 0 else ("#ef4444" if pnl_val < 0 else "#8e9192")
        canvas.create_text(tip_x + 10, tip_y + 44, text=pnl_str, font=("Consolas", 7, "bold"), fill=pnl_color, anchor="w", tags="chart_hover")
        canvas.create_text(tip_x + 10, tip_y + 57, text=dd_str, font=("Segoe UI", 7), fill="#8e9192", anchor="w", tags="chart_hover")

    def on_porto_canvas_leave(self, event=None):
        """Menghapus tooltip saat kursor mouse keluar dari area grafik."""
        if hasattr(self, 'porto_canvas'):
            self.porto_canvas.delete("chart_hover")

    # =========================================================================
    # TAB 5: DIAGNOSA & AUTOPSY TRADE (FAKTOR MENANG/KALAH)
    # =========================================================================
    def setup_diag_tab(self):
        container = tk.Frame(self.tab_diag, bg="#0d0e13")
        container.pack(fill="both", expand=True, padx=12, pady=10)

        # ── 1. FILTER STRIP ──
        f_strip = tk.Frame(container, bg="#1a1b21", relief="solid", bd=1, padx=10, pady=6)
        f_strip.pack(fill="x", pady=(0, 8))

        # Filter Hasil
        tk.Label(f_strip, text="Status:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left", padx=(0, 4))
        self.btn_diag_f_all = tk.Button(f_strip, text="Semua", font=("Segoe UI", 8, "bold"), fg="#0d0e13", bg="#ffffff", activebackground="#0369a1", relief="flat", cursor="hand2", command=lambda: self.set_diag_filter_status("ALL"), padx=8, pady=2)
        self.btn_diag_f_all.pack(side="left", padx=2)

        self.btn_diag_f_win = tk.Button(f_strip, text="Hanya WIN", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#059669", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_diag_filter_status("WIN"), padx=8, pady=2)
        self.btn_diag_f_win.pack(side="left", padx=2)

        self.btn_diag_f_loss = tk.Button(f_strip, text="Hanya LOSS", font=("Segoe UI", 8), fg="#8e9192", bg="#24252c", activebackground="#dc2626", activeforeground="#ffffff", relief="flat", cursor="hand2", command=lambda: self.set_diag_filter_status("LOSS"), padx=8, pady=2)
        self.btn_diag_f_loss.pack(side="left", padx=(2, 12))

        # Filter Skenario
        tk.Label(f_strip, text="Skenario:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left", padx=(0, 4))
        self.combo_skenario = ttk.Combobox(f_strip, values=["Semua Skenario", "S1: Aligned Sniper", "S2: Choppy Range", "S3: False Breakout / Trap", "S4: Early Cut-Loss", "S5: Timeout Exit", "GENERAL_ENTRY"], font=("Segoe UI", 8), width=20, state="readonly")
        self.combo_skenario.set("Semua Skenario")
        self.combo_skenario.pack(side="left", padx=(0, 12))
        self.combo_skenario.bind("<<ComboboxSelected>>", lambda e: self.set_diag_filter_skenario(self.combo_skenario.get()))

        # Search Bar
        tk.Label(f_strip, text="🔍 Cari:", font=("Segoe UI", 8, "bold"), fg="#8e9192", bg="#1a1b21").pack(side="left", padx=(0, 4))
        e_search = tk.Entry(f_strip, textvariable=self.diag_search_var, font=("Segoe UI", 8), bg="#24252c", fg="#ffffff", insertbackground="#38bdf8", relief="flat", width=22)
        e_search.pack(side="left", padx=(0, 8), ipady=2)
        self.diag_search_var.trace_add("write", lambda *a: self.render_diag_rows())

        # Refresh
        btn_ref = tk.Button(f_strip, text="🔄 Refresh", font=("Segoe UI", 8), fg="#38bdf8", bg="#24252c", activebackground="#2e3038", relief="flat", cursor="hand2", command=self.load_diag_data, padx=8, pady=2)
        btn_ref.pack(side="left")

        self.lbl_diag_count = tk.Label(f_strip, text="Menampilkan 0 trade", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21")
        self.lbl_diag_count.pack(side="right")

        # ── 2. SPLIT PANE: TABLE ATAS & AUTOPSY INSPECTOR BAWAH ──
        paned = tk.PanedWindow(container, orient="vertical", bg="#0d0e13", bd=0, sashwidth=4)
        paned.pack(fill="both", expand=True)

        # Upper Table Frame
        tbl_frame = tk.Frame(paned, bg="#13141a", relief="solid", bd=1, padx=8, pady=8)
        paned.add(tbl_frame, minsize=180)

        scry = ttk.Scrollbar(tbl_frame, orient="vertical")
        scry.pack(side="right", fill="y")
        scrx = ttk.Scrollbar(tbl_frame, orient="horizontal")
        scrx.pack(side="bottom", fill="x")

        self.diag_tree = ttk.Treeview(
            tbl_frame,
            columns=("no", "ticket", "w_close", "tipe", "hasil", "profit", "pips", "model", "skenario", "h4", "dxy", "alasan"),
            show="headings",
            yscrollcommand=scry.set,
            xscrollcommand=scrx.set
        )
        self.diag_tree.pack(fill="both", expand=True)
        scry.config(command=self.diag_tree.yview)
        scrx.config(command=self.diag_tree.xview)

        diag_cols = [
            ("no", "#", 40, "center"),
            ("ticket", "Ticket", 95, "center"),
            ("w_close", "Waktu Close", 125, "center"),
            ("tipe", "Tipe", 55, "center"),
            ("hasil", "Hasil", 60, "center"),
            ("profit", "Profit ($)", 85, "center"),
            ("pips", "Pips", 60, "center"),
            ("model", "Model AI", 120, "w"),
            ("skenario", "Skenario Entry", 140, "w"),
            ("h4", "Tren H4", 90, "center"),
            ("dxy", "Tren DXY", 85, "center"),
            ("alasan", "Alasan Exit", 180, "w"),
        ]
        for cid, h, w, a in diag_cols:
            self.diag_tree.heading(cid, text=h)
            self.diag_tree.column(cid, width=w, anchor=a)

        self.diag_tree.tag_configure("win", foreground="#10b981", font=("Segoe UI", 9, "bold"))
        self.diag_tree.tag_configure("loss", foreground="#ef4444", font=("Segoe UI", 9, "bold"))
        self.diag_tree.tag_configure("normal", foreground="#ffffff", font=("Consolas", 9))

        self.diag_tree.bind("<<TreeviewSelect>>", self.on_diag_row_select)

        # Lower Detail Inspector Card
        self.card_inspector = tk.Frame(paned, bg="#1a1b21", relief="solid", bd=1, padx=12, pady=10)
        paned.add(self.card_inspector, minsize=180)

        # Header bar of inspector
        insp_head = tk.Frame(self.card_inspector, bg="#1a1b21")
        insp_head.pack(fill="x", pady=(0, 8))

        self.insp_lbl_badge = tk.Label(insp_head, text="PILIH SALAH SATU BARIS TRADE UNTUK MELIHAT AUTOPSY", font=("Segoe UI", 9, "bold"), fg="#38bdf8", bg="#24252c", padx=10, pady=4)
        self.insp_lbl_badge.pack(side="left")

        self.insp_lbl_meta = tk.Label(insp_head, text="", font=("Segoe UI", 8), fg="#8e9192", bg="#1a1b21")
        self.insp_lbl_meta.pack(side="right")

        # Two columns inside inspector
        insp_body = tk.Frame(self.card_inspector, bg="#1a1b21")
        insp_body.pack(fill="both", expand=True)

        # Left column: Context & Factors
        col_left = tk.Frame(insp_body, bg="#13141a", relief="solid", bd=1, padx=10, pady=8)
        col_left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        tk.Label(col_left, text="🔬 ANALISIS DIAGNOSTIK (FAKTOR MENANG / KALAH)", font=("Segoe UI", 8, "bold"), fg="#38bdf8", bg="#13141a").pack(anchor="w", pady=(0, 4))
        self.insp_txt_analisis = tk.Text(col_left, font=("Segoe UI", 9), fg="#ffffff", bg="#13141a", wrap="word", relief="flat", height=5)
        self.insp_txt_analisis.pack(fill="both", expand=True)
        self.insp_txt_analisis.insert("1.0", "Klik salah satu transaksi pada tabel di atas untuk membedah akar penyebab keberhasilan (TP sniper, trailing lock) atau kegagalan (noise wick, false breakout, early cut-loss).")
        self.insp_txt_analisis.config(state="disabled")

        # Right column: Lesson & Thesis Plan
        col_right = tk.Frame(insp_body, bg="#13141a", relief="solid", bd=1, padx=10, pady=8)
        col_right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        tk.Label(col_right, text="💡 EVALUASI & PEMBELAJARAN STRATEGI (SKRIPSI)", font=("Segoe UI", 8, "bold"), fg="#10b981", bg="#13141a").pack(anchor="w", pady=(0, 4))
        self.insp_txt_evaluasi = tk.Text(col_right, font=("Segoe UI", 9), fg="#c4c7c8", bg="#13141a", wrap="word", relief="flat", height=5)
        self.insp_txt_evaluasi.pack(fill="both", expand=True)
        self.insp_txt_evaluasi.insert("1.0", "Rangkuman evaluasi dan tindakan preventif/korektif otomatis untuk perbaikan model LightGBM v4.0.")
        self.insp_txt_evaluasi.config(state="disabled")

        self.load_diag_data()

    def set_diag_filter_status(self, st):
        self.diag_filter_status = st
        for s, btn in [("ALL", self.btn_diag_f_all), ("WIN", self.btn_diag_f_win), ("LOSS", self.btn_diag_f_loss)]:
            if s == st:
                btn.config(bg="#ffffff" if s == "ALL" else ("#10b981" if s == "WIN" else "#ef4444"), fg="#0d0e13" if s == "ALL" else "#ffffff")
            else:
                btn.config(bg="#24252c", fg="#8e9192")
        self.render_diag_rows()

    def set_diag_filter_skenario(self, sk):
        self.diag_filter_skenario = sk
        self.render_diag_rows()

    def load_diag_data(self):
        if not os.path.exists(CSV_EVAL):
            return
        try:
            df = pd.read_csv(CSV_EVAL)
            CUTOFF_DATE = "2026-09-18 21:55:00"
            if "Waktu Open" in df.columns:
                df = df[df["Waktu Open"] >= CUTOFF_DATE].copy().reset_index(drop=True)
            data = []
            for idx, r in df.iterrows():
                pnl = float(r.get("Profit ($ USD)", 0.0))
                h = str(r.get("Hasil", "")).strip().upper()
                data.append({
                    "no": idx + 1,
                    "ticket": int(r.get("Ticket Posisi", 0)),
                    "w_open": str(r.get("Waktu Open", "")),
                    "w_close": str(r.get("Waktu Close", "")),
                    "durasi": str(r.get("Durasi", "")),
                    "tipe": str(r.get("Tipe", "")),
                    "lot": f"{float(r.get('Lot', 0.01)):.2f}",
                    "entry": f"${float(r.get('Harga Entry', 0)):.2f}",
                    "sl": f"${float(r.get('Stop Loss (SL)', 0)):.2f}" if pd.notna(r.get('Stop Loss (SL)')) and float(r.get('Stop Loss (SL)', 0)) > 0 else "-",
                    "tp": f"${float(r.get('Take Profit (TP)', 0)):.2f}" if pd.notna(r.get('Take Profit (TP)')) and float(r.get('Take Profit (TP)', 0)) > 0 else "-",
                    "exit": f"${float(r.get('Harga Exit', 0)):.2f}",
                    "pips": f"{float(r.get('Pips (P/L)', 0)):+.1f}",
                    "profit": f"${pnl:+.2f}",
                    "hasil": h,
                    "model": str(r.get("Model AI", "")),
                    "skenario": str(r.get("Skenario Entry", "GENERAL_ENTRY")),
                    "h4": str(r.get("Tren H4 Entry", "UNKNOWN")),
                    "dxy": str(r.get("Tren DXY Entry", "UNKNOWN")),
                    "news": str(r.get("Kondisi Makro News", "NORMAL")),
                    "prob": f"{float(r.get('Probabilitas Model (%)', 50.0)):.1f}%",
                    "alasan": str(r.get("Keterangan / Alasan Exit", "")),
                    "analisis": str(r.get("Analisis Diagnostik (Menang/Kalah)", "")),
                    "evaluasi": str(r.get("Evaluasi & Pembelajaran", ""))
                })
            self.diag_data = data
            if hasattr(self, 'diag_sidebar_badge') and self.diag_sidebar_badge:
                try:
                    self.diag_sidebar_badge.config(text=str(len(data)))
                except Exception:
                    pass
            self.render_diag_rows()
        except Exception as e:
            print(f"[ERROR load_diag_data]: {e}")

    def render_diag_rows(self):
        for itm in self.diag_tree.get_children():
            self.diag_tree.delete(itm)

        sq = self.diag_search_var.get().strip().lower()
        st_filter = self.diag_filter_status
        sk_filter = self.diag_filter_skenario

        displayed = 0
        for item in reversed(self.diag_data):
            if st_filter != "ALL" and item["hasil"] != st_filter:
                continue
            if sk_filter != "ALL" and sk_filter != "Semua Skenario":
                key = sk_filter.split(":")[0].strip()
                if key not in item["skenario"] and sk_filter not in item["skenario"]:
                    continue
            if sq:
                combined = f"{item['ticket']} {item['tipe']} {item['skenario']} {item['h4']} {item['dxy']} {item['alasan']} {item['analisis']} {item['evaluasi']}".lower()
                if sq not in combined:
                    continue

            tag = "win" if item["hasil"] == "WIN" else ("loss" if item["hasil"] == "LOSS" else "normal")
            vals = (
                item["no"], item["ticket"], item["w_close"], item["tipe"], item["hasil"],
                item["profit"], item["pips"], item["model"], item["skenario"],
                item["h4"], item["dxy"], item["alasan"]
            )
            self.diag_tree.insert("", "end", iid=str(item["ticket"]), values=vals, tags=(tag,))
            displayed += 1

        self.lbl_diag_count.config(text=f"Menampilkan {displayed} dari {len(self.diag_data)} trade")

    def on_diag_row_select(self, event):
        sel = self.diag_tree.selection()
        if not sel:
            return
        ticket_id = sel[0]
        target = None
        for item in self.diag_data:
            if str(item["ticket"]) == str(ticket_id):
                target = item
                break
        if not target:
            return

        h = target["hasil"]
        badge_text = f"✅ {h} ({target['profit']} USD | {target['pips']} Pips) - Ticket #{target['ticket']}" if h == "WIN" else f"❌ {h} ({target['profit']} USD | {target['pips']} Pips) - Ticket #{target['ticket']}"
        badge_bg = "#064e3b" if h == "WIN" else "#450a0a"
        badge_fg = "#10b981" if h == "WIN" else "#ef4444"

        self.insp_lbl_badge.config(text=badge_text, bg=badge_bg, fg=badge_fg)
        meta_str = f"Open: {target['w_open']}  |  Close: {target['w_close']}  |  Durasi: {target['durasi']}  |  H4: {target['h4']}  |  DXY: {target['dxy']}  |  Prob: {target['prob']}"
        self.insp_lbl_meta.config(text=meta_str)

        # Analisis text
        self.insp_txt_analisis.config(state="normal")
        self.insp_txt_analisis.delete("1.0", "end")
        analisis_full = f"Skenario Entry: {target['skenario']}\nAlasan Exit: {target['alasan']}\n\nDiagnosa Akar Masalah:\n{target['analisis']}"
        self.insp_txt_analisis.insert("1.0", analisis_full)
        self.insp_txt_analisis.config(state="disabled")

        # Evaluasi text
        self.insp_txt_evaluasi.config(state="normal")
        self.insp_txt_evaluasi.delete("1.0", "end")
        evaluasi_full = f"Model AI: {target['model']}\nKondisi Makro: {target['news']}\n\nPembelajaran & Tindakan Korektif Skripsi:\n{target['evaluasi']}"
        self.insp_txt_evaluasi.insert("1.0", evaluasi_full)
        self.insp_txt_evaluasi.config(state="disabled")

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
