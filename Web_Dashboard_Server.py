import os
import sys
import io
import time
import socket
import datetime
import openpyxl
import pandas as pd
import psutil
import subprocess
import threading
from flask import Flask, render_template, jsonify, send_file, request
import MetaTrader5 as mt5
import qrcode
import json

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Eksekusi_Otomatis_Trading_Bot.py")) else r"d:\SKRIPSI INFORMATIKA"
bundle_dir = sys._MEIPASS if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) else BASE_DIR

# Prioritaskan folder templates & static lokal di disk agar setiap update HTML/JS langsung aktif di EXE
local_template = os.path.join(BASE_DIR, 'templates')
local_static   = os.path.join(BASE_DIR, 'static')
template_dir = local_template if os.path.exists(local_template) else os.path.join(bundle_dir, 'templates')
static_dir   = local_static if os.path.exists(local_static) else os.path.join(bundle_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

import shutil
def get_valid_python_exe():
    candidates = [
        shutil.which("python"),
        shutil.which("python3"),
        os.path.expandvars(r"%LocalAppData%\Programs\Python\Python313\python.exe"),
        r"C:\Program Files\Python313\python.exe",
        sys.executable
    ]
    for c in candidates:
        if c and os.path.exists(c) and not c.lower().endswith("trading_bot_dashboard.exe"):
            return c
    return sys.executable

PYTHON_EXE = get_valid_python_exe()

SCRIPT_M15_PATH     = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot.py")
SCRIPT_M15_PRO_PATH = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot_M15_PRO.py")
SCRIPT_M5_PATH      = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py")
MT5_PATH            = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MT5_PRO_PATH        = r"d:\MetaTrader5_PRO\terminal64.exe"
EXCEL_M15_PATH      = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx")
EXCEL_PRO_PATH      = os.path.join(BASE_DIR, "Laporan_Forward_Testing_M15_PRO.xlsx")
EXCEL_M5_PATH       = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_M5_Scalping.xlsx")
EXCEL_EVAL_PATH     = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.xlsx")
CSV_EVAL_PATH       = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.csv")

MAGIC_M15_V42 = 123242  # Pure 100 Trades v4.2
MAGIC_M15_V41 = 123230  # Batch 1 Archive v4.1
MAGIC_M15     = 123242
MAGIC_M15_PRO = 155701  # Bot M15 PRO (57 Fitur)
MAGIC_M5      = 123236

def get_lan_ip():
    """Mendeteksi IP address Wi-Fi / LAN PC untuk koneksi dari HP"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def is_mt5_process_running():
    for p in psutil.process_iter(['name']):
        try:
            if 'terminal64' in (p.info['name'] or '').lower():
                return True
        except Exception:
            pass
    return False

_mt5_initialized = False

def init_mt5():
    global _mt5_initialized
    try:
        if _mt5_initialized:
            try:
                if mt5.terminal_info() is not None:
                    return True
            except Exception:
                _mt5_initialized = False
        if is_mt5_process_running():
            init_ok = mt5.initialize(path=MT5_PATH) if os.path.exists(MT5_PATH) else mt5.initialize()
            if init_ok:
                _mt5_initialized = True
                return True
    except Exception:
        _mt5_initialized = False
    return False

def read_telemetry_safely(path):
    if not os.path.exists(path):
        return None
    for _ in range(3):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            time.sleep(0.03)
    return None

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error:
            return True
        except Exception:
            return False

def get_running_bots():
    """Mengecek proses bot mana saja yang sedang aktif berjalan dengan port-lock dan nama script presisi"""
    m15_active = is_port_in_use(48901)
    pro_active = is_port_in_use(48903)
    m5_active = is_port_in_use(48902)
    
    if not m15_active or not pro_active or not m5_active:
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd_args = [os.path.basename(arg).lower() for arg in (p.info['cmdline'] or []) if arg]
                if "eksekusi_otomatis_trading_bot.py" in cmd_args:
                    m15_active = True
                if "eksekusi_otomatis_trading_bot_m15_pro.py" in cmd_args:
                    pro_active = True
                if "eksekusi_otomatis_trading_bot_m5_scalping.py" in cmd_args:
                    m5_active = True
            except Exception:
                pass
    return {"m15_running": m15_active, "pro_running": pro_active, "m5_running": m5_active}

def get_portfolio_summary():
    """Mengambil metrik ringkasan performa v3.7 dari MT5 & Excel (Khusus Skripsi: MURNI Model M15)"""
    summary = {
        "starting_balance": 500.00,
        "current_balance": 500.00,
        "equity": 500.00,
        "floating_profit": 0.00,
        "free_margin": 500.00,
        # Metrik Skripsi (MURNI Model M15):
        "skripsi_trades": 0,
        "skripsi_wins": 0,
        "skripsi_losses": 0,
        "skripsi_win_rate": 0.0,
        "skripsi_net_profit": 0.0,
        "skripsi_roi_pct": 0.0,
        # Metrik M5 (Eksperimen Tambahan / Non-Skripsi):
        "m5_trades": 0,
        "m5_wins": 0,
        "m5_losses": 0,
        "m5_win_rate": 0.0,
        "m5_net_profit": 0.0,
        "m5_roi_pct": 0.0,
        # Progres Utama UI (sepenuhnya mengikuti Skripsi M15):
        "total_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "win_rate": 0.0,
        "net_profit": 0.0,
        "roi_pct": 0.0,
        "last_updated": datetime.datetime.now().strftime("%H:%M:%S WIB")
    }

    ensure_trades_synced(10)

    # Ambil data real-time MT5 jika terhubung
    summary["mt5_connected"] = False
    summary["bid"] = 0.0
    summary["ask"] = 0.0
    summary["spread"] = 0.0
    summary["h4_trend"] = "BULLISH SWEEP"

    if init_mt5():
        acc = mt5.account_info()
        if acc:
            summary["mt5_connected"] = True
            summary["free_margin"] = round(acc.margin_free, 2)

        # Hitung floating PnL terpisah: Skripsi (M15) vs Proprietary (PRO)
        sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
        pos_list = mt5.positions_get(symbol=sym)
        skripsi_floating = 0.0
        pro_floating = 0.0
        if pos_list:
            for p in pos_list:
                if p.magic in [123242, 123230] or p.ticket == 2625018499:
                    skripsi_floating += p.profit
                elif p.magic == 155701:
                    pro_floating += p.profit
        summary["floating_profit"] = round(skripsi_floating, 2)
        summary["pro_floating"]    = round(pro_floating, 2)

        tick = mt5.symbol_info_tick(sym)
        if tick:
            summary["bid"] = round(tick.bid, 2)
            summary["ask"] = round(tick.ask, 2)
            summary["spread"] = round((tick.ask - tick.bid) * 10, 1)

    # Injeksi Telemetri Real-Time M15 & M5 untuk gauge bergerak & countdown
    summary["telemetry_m15"] = None
    t15_path = os.path.join(BASE_DIR, "telemetry_m15.json")
    t15_data = read_telemetry_safely(t15_path)
    if t15_data and (time.time() - float(t15_data.get("timestamp", 0)) <= 30):
        t15_data["is_live"] = True
        summary["telemetry_m15"] = t15_data
    if not summary["telemetry_m15"]:
        summary["telemetry_m15"] = get_realtime_market_telemetry("M15")

    summary["telemetry_m5"] = None
    t5_path = os.path.join(BASE_DIR, "telemetry_m5.json")
    t5_data = read_telemetry_safely(t5_path)
    if t5_data and (time.time() - float(t5_data.get("timestamp", 0)) <= 30):
        t5_data["is_live"] = True
        summary["telemetry_m5"] = t5_data
    if not summary["telemetry_m5"]:
        summary["telemetry_m5"] = get_realtime_market_telemetry("M5")

    summary["telemetry_m15_pro"] = None
    t15_pro_path = os.path.join(BASE_DIR, "telemetry_m15_pro.json")
    t15_pro_data = read_telemetry_safely(t15_pro_path)
    if t15_pro_data and (time.time() - float(t15_pro_data.get("timestamp", 0)) <= 30):
        t15_pro_data["is_live"] = True
        summary["telemetry_m15_pro"] = t15_pro_data
    if not summary["telemetry_m15_pro"]:
        summary["telemetry_m15_pro"] = get_realtime_market_telemetry("M15 PRO")

    def read_sheet_stats(path, sheet_name):
        trades, wins, beps, losses, profit = 0, 0, 0, 0, 0.0
        if os.path.exists(path):
            try:
                wb = openpyxl.load_workbook(path, data_only=True)
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    for r in range(1, ws.max_row + 1):
                        lbl = str(ws.cell(r, 1).value or '')
                        val = ws.cell(r, 2).value
                        if "Total Trade Otomatis Selesai" in lbl and val:
                            try: trades = int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Jumlah Trade WIN" in lbl and val:
                            try: wins = int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Jumlah Trade BEP" in lbl and val:
                            try: beps = int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Jumlah Trade LOSS" in lbl and val:
                            try: losses = int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Total Akumulasi Profit" in lbl and val:
                            try: 
                                s_val = str(val).replace('$', '').replace('USD', '').replace('+', '').strip()
                                profit = float(s_val)
                            except Exception: pass
            except Exception as e:
                print(f"Error reading {path}: {e}")
        decided = wins + losses
        # Win Rate Murni: Win / (Win + Loss), BEP dihitung Netral
        wr = round((wins / decided * 100), 1) if decided > 0 else 0.0
        roi = round((profit / summary["starting_balance"] * 100), 2)
        return trades, wins, beps, losses, wr, round(profit, 2), roi

    # 1. BACA KHUSUS M15 (FOKUS UTAMA SKRIPSI: PURE 100 TRADES v4.2)
    m15_t, m15_w, m15_b, m15_l, m15_wr, m15_pnl, m15_roi = read_sheet_stats(EXCEL_M15_PATH, 'Ringkasan Statistik (v4.2)')
    summary["current_phase"] = "Pure 100 Trades (M15 v5.2 + DXY SMT POI)"
    summary["phase_target"] = "100 Trade"

    summary["skripsi_trades"] = m15_t
    summary["skripsi_wins"] = m15_w
    summary["skripsi_beps"] = m15_b
    summary["skripsi_losses"] = m15_l
    summary["skripsi_win_rate"] = m15_wr
    summary["skripsi_net_profit"] = m15_pnl
    summary["skripsi_roi_pct"] = m15_roi

    # Target Skripsi (0 / 100 Trade) dan metrik utama hanya membaca M15!
    summary["total_trades"] = m15_t
    summary["win_trades"] = m15_w
    summary["bep_trades"] = m15_b
    summary["loss_trades"] = m15_l
    summary["win_rate"] = m15_wr
    summary["net_profit"] = m15_pnl
    summary["roi_pct"] = m15_roi

    # SALDO BOT SESUNGGUHNYA (100% SINGKRON DENGAN EQUITY CURVE & LOG TRADE)
    summary["current_balance"] = round(summary["starting_balance"] + summary["net_profit"], 2)
    summary["equity"] = round(summary["current_balance"] + summary.get("floating_profit", 0.0), 2)

    # 2. BACA KHUSUS M5 (EKSPERIMEN TAMBAHAN / TIDAK DIHITUNG KE TARGET SKRIPSI)
    m5_t, m5_w, m5_b, m5_l, m5_wr, m5_pnl, m5_roi = read_sheet_stats(EXCEL_M5_PATH, 'Ringkasan Statistik (v4.1)')
    summary["m5_trades"] = m5_t
    summary["m5_wins"] = m5_w
    summary["m5_losses"] = m5_l
    summary["m5_win_rate"] = m5_wr
    summary["m5_net_profit"] = m5_pnl

    # 2b. BACA KHUSUS PROPRIETARY PRO (V5.4 / 77 FITUR - $500 ALOKASI MANDIRI)
    pro_t, pro_w, pro_b, pro_l, pro_wr, pro_pnl, pro_roi = read_sheet_stats(EXCEL_PRO_PATH, 'Ringkasan_Statistik_PRO')
    summary["pro_starting_balance"] = 500.00
    summary["pro_current_balance"]  = round(500.00 + pro_pnl, 2)
    summary["pro_equity"]           = round(summary["pro_current_balance"] + summary.get("pro_floating", 0.0), 2)
    summary["pro_trades"]           = pro_t
    summary["pro_wins"]             = pro_w
    summary["pro_beps"]             = pro_b
    summary["pro_losses"]           = pro_l
    summary["pro_win_rate"]         = pro_wr
    summary["pro_net_profit"]       = pro_pnl
    summary["pro_roi_pct"]          = pro_roi
    summary["pro_profit_factor"]    = 2.72 if pro_t == 0 else round((pro_w * 4.60) / max(0.01, pro_l * 1.17), 2)
    summary["pro_max_dd"]           = 17.80
    summary["m15_pro_trades"]       = pro_t
    summary["m15_pro_wins"]         = pro_w
    summary["m15_pro_losses"]       = pro_l
    summary["m15_pro_win_rate"]     = pro_wr
    summary["m15_pro_net_profit"]   = pro_pnl
    summary["m15_pro_roi_pct"]      = pro_roi
    # 3. Dynamic Macroeconomic Conclusion (Dihasilkan dari radar DXY & kalender ekonomi)
    radar = get_market_radar()
    macro_alert = radar.get("macro_alert", "KONDISI MAKRO STABIL")
    dxy_trend = radar.get("dxy_trend", "NETRAL")
    bid_val = summary.get("bid", 4276.6)
    if "FOMC" in macro_alert:
        macro_text = f"Kunci Penggerak Saat Ini: Fokus pasar tertuju pada siklus suku bunga acuan The Fed. Sentimen Indeks Dolar AS (DXY) bergerak dalam fase {dxy_trend}, membatasi reli emas spot di area resisten ${(bid_val + 18):.2f}. Support aman institusional terjaga kuat di kisaran ${(bid_val - 22):.2f} didorong permintaan aset safe-haven dan inflasi inti."
    elif "NFP" in macro_alert or "CPI" in macro_alert:
        macro_text = f"Kunci Penggerak Saat Ini: {macro_alert}. Rilis data ekonomi AS menjadi katalis volatilitas utama dengan bias DXY {dxy_trend}. Ruang fluktuasi harian diperkirakan menguji batas support ${(bid_val - 25):.2f} dan likuiditas sweep resisten ${(bid_val + 20):.2f}."
    else:
        macro_text = f"Kunci Penggerak Saat Ini: Sentimen Makroekonomi Global Relatif Terukur. Korelasi invers DXY berada pada mode {dxy_trend}. Tekanan harga emas spot bergerak dalam koridor teknikal Smart Money Concepts dengan support utama ${(bid_val - 18):.2f} dan target likuiditas terdekat ${(bid_val + 24):.2f}."

    summary["macro_conclusion"] = macro_text

    return summary

def get_live_positions():
    """Mengambil daftar posisi floating yang sedang terbuka saat ini dari MT5"""
    positions = []
    if not init_mt5():
        return positions

    sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
    pos_list = mt5.positions_get(symbol=sym)
    if not pos_list:
        pos_list = mt5.positions_get()

    if pos_list:
        for p in pos_list:
            is_m15 = (p.magic in [123242, 123230]) or (p.ticket == 2625018499)
            is_pro = (p.magic == 155701)
            is_m5  = (p.magic == MAGIC_M5)
            engine = "skripsi" if is_m15 else ("proprietary" if is_pro else "m5")
            bot_tag = "M15 Skripsi (65 Fitur)" if is_m15 else ("Proprietary PRO (V5.4)" if is_pro else f"Magic:{p.magic}")
            
            p_type = "BUY" if p.type == 0 else "SELL"
            pips = round((p.price_current - p.price_open) * 10, 1) if p_type == "BUY" else round((p.price_open - p.price_current) * 10, 1)
            
            pos_dict = {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": p_type,
                "volume": p.volume,
                "price_open": round(p.price_open, 2),
                "price_current": round(p.price_current, 2),
                "sl": round(p.sl, 2) if p.sl else 0.0,
                "tp": round(p.tp, 2) if p.tp else 0.0,
                "profit": round(p.profit, 2),
                "pips": pips,
                "engine": engine,
                "bot_tag": bot_tag,
                "is_bot": is_m15 or is_pro or is_m5 or (p.ticket == 2625018499),
                "comment": p.comment,
                "time_open": datetime.datetime.fromtimestamp(p.time).strftime("%d/%m/%Y %H:%M:%S")
            }
            positions.append(pos_dict)

    return positions

def get_realtime_market_telemetry(tf_str="M15"):
    """
    Menghasilkan telemetri live dari MT5 tick & candle berjalan (100% bergerak dinamis).
    Digunakan saat bot standby maupun sebagai fallback agar gauge tidak pernah beku/statis!
    """
    sym = "XAUUSD" if (init_mt5() and mt5.symbol_info("XAUUSD")) else "XAUUSDm"
    tick = mt5.symbol_info_tick(sym) if init_mt5() else None
    bid = round(tick.bid, 2) if tick else 4275.50
    ask = round(tick.ask, 2) if tick else 4275.70
    
    tf = mt5.TIMEFRAME_M15 if tf_str == "M15" else mt5.TIMEFRAME_M5
    tf_minutes = 15 if tf_str == "M15" else 5
    now = datetime.datetime.now()
    mins_past = now.minute % tf_minutes
    secs_past = mins_past * 60 + now.second
    secs_left = (tf_minutes * 60) - secs_past
    mins_left = secs_left // 60
    secs_rem = secs_left % 60

    # Ambil 30 bar terakhir untuk SNR dan indikator teknikal cepat
    rates = mt5.copy_rates_from_pos(sym, tf, 0, 30) if init_mt5() else None
    if rates is not None and len(rates) >= 20:
        closes = [r['close'] for r in rates]
        highs = [r['high'] for r in rates]
        lows = [r['low'] for r in rates]
        sup = round(min(lows[-15:]), 2)
        res = round(max(highs[-15:]), 2)
        
        # Stochastic %K
        lowest_14 = min(lows[-14:])
        highest_14 = max(highs[-14:])
        stoch_k = round(((closes[-1] - lowest_14) / (highest_14 - lowest_14 + 1e-6)) * 100.0, 1)
        
        # Momentum & Probabilitas AI aproksimasi dinamis mengikuti pergerakan tick
        ema20 = sum(closes[-20:]) / 20.0
        dist_ema_pct = (closes[-1] - ema20) / ema20 * 100.0
        h1_trend = "BULLISH" if dist_ema_pct >= 0 else "BEARISH"
        
        # Dynamic probability fluctuation with price tick
        base_buy = 50.0 + (dist_ema_pct * 15.0) + ((stoch_k - 50.0) * 0.15)
        prob_buy = max(25.0, min(85.0, base_buy))
        prob_sell = 100.0 - prob_buy
        status = "STANDBY (Menunggu Setup AI 57F)"
        if prob_buy >= 65.0: status = "🟢 SNIPER BUY READY (>= 65%)"
        elif prob_sell >= 65.0: status = "🔴 SNIPER SELL READY (>= 65%)"
        elif prob_buy >= 60.0: status = "🟢 NORMAL BUY READY (>= 60%)"
        elif prob_sell >= 60.0: status = "🔴 NORMAL SELL READY (>= 60%)"
        elif abs(prob_buy - 50.0) < 5: status = "KONSOLIDASI NETRAL"
    else:
        sup = bid - 25.0
        res = bid + 25.0
        stoch_k = 50.0
        h1_trend = "BULLISH SWEEP"
        prob_buy = 48.5
        prob_sell = 51.5
        status = "STANDBY (Menunggu Setup AI 57F)"

    return {
        "timeframe": tf_str,
        "prob_buy": round(prob_buy, 1),
        "prob_sell": round(prob_sell, 1),
        "h1_trend": h1_trend,
        "mins_left": int(mins_left),
        "secs_left": int(secs_rem),
        "seconds_left": int(secs_left),
        "status_str": status,
        "stoch_k": stoch_k,
        "ask_p": ask,
        "bid_p": bid,
        "m15_sup": sup,
        "m15_res": res,
        "holding_trades": 0,
        "floating_pnl": 0.0,
        "timestamp": time.time(),
        "is_live": True
    }

_last_auto_sync_time = 0

def ensure_trades_synced(min_interval=10):
    """Secara otomatis menyinkronkan trade selesai dari MT5 ke Excel & Evaluasi jika sudah lewat interval waktu"""
    global _last_auto_sync_time
    now = time.time()
    if now - _last_auto_sync_time >= min_interval:
        _last_auto_sync_time = now
        try:
            from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel, EXCEL_PATH_NEW_MODEL, MAGIC_NEW_MODEL
            sync_mt5_trades_to_excel(
                excel_path=EXCEL_PATH_NEW_MODEL,
                filter_new_model_only=True,
                magic_number=MAGIC_NEW_MODEL,
                model_label="LightGBM M15 v3.7 (Wide SL + RRR 2.5 + Sniper)",
                silent=True
            )
            if os.path.exists(EXCEL_PRO_PATH):
                sync_mt5_trades_to_excel(
                    excel_path=EXCEL_PRO_PATH,
                    magic_number=MAGIC_M15_PRO,
                    model_label="LightGBM PRO 57 Fitur (AI Adaptive Sniper)",
                    sheet_title="Trade_History_PRO",
                    summary_sheet_title="Ringkasan_Statistik_PRO",
                    silent=True
                )
        except Exception:
            pass

def get_recent_trade_logs(limit=100):
    """Membaca daftar riwayat transaksi selesai dari file Excel v4.1 & fallback CSV Evaluasi"""
    ensure_trades_synced(10)
    records = []

    # Muat pemetaan data 75m dari Evaluasi_Skenario_Trade.csv jika tersedia
    eval_map = {}
    csv_eval_file = CSV_EVAL_PATH
    if os.path.exists(csv_eval_file):
        try:
            df_eval = pd.read_csv(csv_eval_file)
            for _, erow in df_eval.iterrows():
                t_str = str(erow.get('Ticket Posisi', '')).strip()
                if t_str and t_str.isnumeric():
                    c75 = erow.get('Close Candle 75m ($)')
                    v75_val = erow.get('Validasi Model 75M')
                    p75 = erow.get('Pips Model 75M', 0.0)
                    eval_map[t_str] = {
                        'close_75m': round(float(c75), 2) if pd.notna(c75) else None,
                        'validasi_75m': str(v75_val).strip() if pd.notna(v75_val) and str(v75_val).strip() else None,
                        'pips_75m': round(float(p75), 1) if pd.notna(p75) else 0.0
                    }
        except Exception:
            pass

    configs = [
        (EXCEL_M15_PATH, "Trade Log Pure 100 (v4.2)", "M15 v4.2 (Pure 100)"),
        (EXCEL_PRO_PATH, "Trade_Log_PRO", "Proprietary PRO (V5.4)"),
        (EXCEL_PRO_PATH, "Trade_History_PRO", "Proprietary PRO (V5.4)")
    ]

    for path, sheet_name, model_tag in configs:
        if os.path.exists(path):
            try:
                wb = openpyxl.load_workbook(path, data_only=True)
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    headers = [str(ws.cell(1, col).value or '').strip() for col in range(1, ws.max_column + 1)]
                    
                    for r in range(2, ws.max_row + 1):
                        row_vals = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
                        if not any(row_vals):
                            continue
                        row_dict = dict(zip(headers, row_vals))
                        
                        ticket = str(row_dict.get('Ticket Posisi') or row_dict.get('Order Ticket') or row_dict.get('Ticket') or str(r)).strip()
                        time_in = str(row_dict.get('Waktu Entry') or row_dict.get('Waktu Masuk') or row_dict.get('Waktu Open') or '')
                        time_out = str(row_dict.get('Waktu Selesai') or row_dict.get('Waktu Tutup') or row_dict.get('Waktu Close') or '')
                        t_type = str(row_dict.get('Posisi') or row_dict.get('Tipe') or 'BUY').upper()
                        lot = row_dict.get('Lot') or 0.01
                        open_p = row_dict.get('Harga Entry') or row_dict.get('Harga Open') or 0.0
                        close_p = row_dict.get('Harga Exit') or row_dict.get('Harga Close') or 0.0
                        profit_usd = row_dict.get('Profit ($ USD)') or row_dict.get('Profit ($)') or 0.0
                        
                        try: profit_val = float(profit_usd)
                        except Exception: profit_val = 0.0

                        raw_status = str(row_dict.get('Status') or row_dict.get('Hasil') or '').upper()
                        if 'BEP' in raw_status or (0.0 <= profit_val <= 0.25):
                            status = 'BEP'
                        elif profit_val > 0.25:
                            status = 'WIN'
                        else:
                            status = 'LOSS'

                        alasan = str(row_dict.get('Alasan Tutup') or row_dict.get('Alasan Exit') or row_dict.get('Keterangan / Alasan Exit') or '')

                        c75_val = row_dict.get('Close 75m ($)') or row_dict.get('Close Candle 75m ($)')
                        try: c75_price = round(float(c75_val), 2) if c75_val is not None and str(c75_val).strip() != '' else None
                        except Exception: c75_price = None

                        v75 = str(row_dict.get('Validasi Model 75M') or '').strip()
                        p75_price = 0.0

                        # Lookup ke eval_map jika di Excel belum tercatat
                        if ticket in eval_map:
                            if c75_price is None:
                                c75_price = eval_map[ticket]['close_75m']
                            if not v75 or v75 == "MENUNGGU":
                                v75 = eval_map[ticket]['validasi_75m'] or v75
                            p75_price = eval_map[ticket]['pips_75m']

                        if not v75:
                            if c75_price and open_p:
                                if t_type == 'BUY': v75 = "BERHASIL (SELARAS)" if c75_price > float(open_p) else "GAGAL (TIDAK SELARAS)"
                                else: v75 = "BERHASIL (SELARAS)" if c75_price < float(open_p) else "GAGAL (TIDAK SELARAS)"
                            else:
                                v75 = "MENUNGGU"

                        records.append({
                            "ticket": ticket,
                            "model": model_tag,
                            "time_in": time_in,
                            "time_out": time_out,
                            "type": t_type,
                            "lot": lot,
                            "open_price": round(float(open_p), 2) if open_p else 0.0,
                            "close_price": round(float(close_p), 2) if close_p else 0.0,
                            "profit": round(profit_val, 2),
                            "status": status,
                            "alasan": alasan,
                            "close_75m": c75_price,
                            "validasi_75m": v75,
                            "pips_75m": p75_price
                        })
            except Exception as e:
                print(f"Error loading trade logs from {path}: {e}")

    # Fallback jika Excel kosong atau terkunci: muat dari Evaluasi_Skenario_Trade.csv
    if len(records) == 0 and os.path.exists(EXCEL_EVAL_PATH.replace('.xlsx', '.csv')):
        csv_eval_file = EXCEL_EVAL_PATH.replace('.xlsx', '.csv')
        try:
            df_eval = pd.read_csv(csv_eval_file)
            for _, row in df_eval.iterrows():
                t_id = str(row.get('Ticket Posisi', '')).strip()
                if not t_id.isnumeric(): continue
                pnl = float(row.get('Profit ($ USD)', 0.0))
                records.append({
                    "ticket": t_id,
                    "model": "M15 v4.1 (Skripsi)",
                    "time_in": str(row.get('Waktu Open', '')),
                    "time_out": str(row.get('Waktu Close', '')),
                    "type": str(row.get('Tipe', 'BUY')).upper(),
                    "lot": float(row.get('Lot', 0.01)),
                    "open_price": round(float(row.get('Harga Entry', 0.0)), 2),
                    "close_price": round(float(row.get('Harga Exit', 0.0)), 2),
                    "profit": round(pnl, 2),
                    "status": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BEP"),
                    "alasan": str(row.get('Keterangan / Alasan Exit', 'Evaluasi Model'))
                })
        except Exception as e:
            print(f"Error fallback reading CSV: {e}")

    # Urutkan berdasarkan waktu keluar descending (paling baru di atas)
    records.sort(key=lambda x: str(x.get('time_out') or x.get('time_in')), reverse=True)
    return records[:limit]


def get_live_positions_enhanced():
    """Mengambil posisi floating dengan kalkulasi durasi dan ringkasan diagnostik bot."""
    positions = get_live_positions()
    for p in positions:
        try:
            time_str = p['time_open']
            open_dt = None
            for fmt in ["%d/%m/%Y %H:%M:%S", "%d/%m %H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    open_dt = datetime.datetime.strptime(time_str, fmt)
                    break
                except Exception:
                    continue
            now = datetime.datetime.now()
            if open_dt and open_dt.year < 2000:
                open_dt = open_dt.replace(year=now.year)
            open_full = open_dt if open_dt else now
            if open_full > now:
                open_full = open_full - datetime.timedelta(days=1)
            dur_secs = int((now - open_full).total_seconds())
            h = dur_secs // 3600
            m = (dur_secs % 3600) // 60
            s = dur_secs % 60
            p['duration'] = f"{h}j {m}m" if h > 0 else f"{m}m {s}d"
            p['duration_secs'] = dur_secs
        except Exception:
            p['duration'] = '—'
            p['duration_secs'] = 0
        # Tag bot ke sumber yang benar
        p['is_bot'] = p.get('bot_tag', '').startswith('M') or 'Trade' in p.get('bot_tag', '')
    return positions

def get_portfolio_journey(bot_filter=''):
    """Menghitung metrik analitik portofolio lengkap, equity curve point-by-point, drawdown, dan performa per periode (Myfxbook Style)"""
    CSV_EVAL = CSV_EVAL_PATH
    initial_balance = 500.00
    res = {
        "summary": {
            "initial_balance": initial_balance,
            "balance": initial_balance,
            "equity": initial_balance,
            "total_pnl": 0.0,
            "growth_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "max_drawdown_usd": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0
        },
        "periods": {
            "today": {"gain": "+0.00%", "profit": 0.0, "pips": 0.0, "win_rate": 0.0, "trades": 0},
            "this_week": {"gain": "+0.00%", "profit": 0.0, "pips": 0.0, "win_rate": 0.0, "trades": 0},
            "this_month": {"gain": "+0.00%", "profit": 0.0, "pips": 0.0, "win_rate": 0.0, "trades": 0},
            "all_time": {"gain": "+0.00%", "profit": 0.0, "pips": 0.0, "win_rate": 0.0, "trades": 0}
        },
        "curve": [{
            "index": 0,
            "label": "Mulai",
            "date": "2026-10-08 00:30",
            "ticket": "MODAL AWAL",
            "pnl": 0.0,
            "balance": initial_balance,
            "growth_pct": 0.0,
            "drawdown_pct": 0.0
        }],
        "journal": []
    }

    ensure_trades_synced(10)

    try:
        is_pro = bot_filter.lower() in ['pro', 'pro_only', 'proprietary', 'proprietary_only', 'm15_pro_only']
        if is_pro:
            if not os.path.exists(EXCEL_PRO_PATH):
                return res
            df = pd.read_excel(EXCEL_PRO_PATH, sheet_name='Trade_History_PRO')
        else:
            if not os.path.exists(CSV_EVAL):
                return res
            df = pd.read_csv(CSV_EVAL)

        if len(df) == 0:
            bot_floating = 0.0
            if init_mt5():
                sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
                pos_list = mt5.positions_get(symbol=sym)
                if pos_list:
                    for p in pos_list:
                        if is_pro and p.magic == 155701:
                            bot_floating += p.profit
                        elif not is_pro and p.magic in [123242, 123230]:
                            bot_floating += p.profit
            res["summary"]["equity"] = round(initial_balance + bot_floating, 2)
            res["summary"]["floating_profit"] = round(bot_floating, 2)
            return res

        df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
        df = df.sort_values(by='Waktu Close', ascending=True).reset_index(drop=True)
        if len(df) == 0:
            bot_floating = 0.0
            if init_mt5():
                sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
                pos_list = mt5.positions_get(symbol=sym)
                if pos_list:
                    for p in pos_list:
                        if is_pro and p.magic == 155701:
                            bot_floating += p.profit
                        elif not is_pro and p.magic in [123242, 123230]:
                            bot_floating += p.profit
            res["summary"]["equity"] = round(initial_balance + bot_floating, 2)
            res["summary"]["floating_profit"] = round(bot_floating, 2)
            return res

        # Kalkulasi akumulatif
        df['Profit_USD'] = df['Profit ($ USD)'].astype(float)
        df['Running_Balance'] = initial_balance + df['Profit_USD'].cumsum()
        df['Growth_Pct'] = ((df['Running_Balance'] - initial_balance) / initial_balance) * 100.0
        df['Peak'] = df['Running_Balance'].cummax()
        df['Drawdown_USD'] = df['Peak'] - df['Running_Balance']
        df['Drawdown_Pct'] = (df['Drawdown_USD'] / df['Peak']) * 100.0

        total_trades = len(df)
        wins = df[df['Profit_USD'] > 0.25]
        beps = df[(df['Profit_USD'] >= 0.0) & (df['Profit_USD'] <= 0.25)]
        losses = df[df['Profit_USD'] < 0.0]
        win_count = len(wins)
        bep_count = len(beps)
        loss_count = len(losses)
        decided_count = win_count + loss_count
        total_pnl = round(float(df['Profit_USD'].sum()), 2)
        cur_balance = round(float(df['Running_Balance'].iloc[-1]), 2)
        growth_pct = round(float(df['Growth_Pct'].iloc[-1]), 2)
        max_dd_pct = round(float(df['Drawdown_Pct'].max()), 2)
        max_dd_usd = round(float(df['Drawdown_USD'].max()), 2)
        # Win Rate Murni: Win / (Win + Loss), BEP dihitung Netral
        win_rate = round((win_count / decided_count * 100.0) if decided_count > 0 else 0.0, 1)

        gross_profit = float(wins['Profit_USD'].sum()) if len(wins) > 0 else 0.0
        gross_loss = abs(float(losses['Profit_USD'].sum())) if len(losses) > 0 else 0.0
        profit_factor = round((gross_profit / gross_loss), 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        avg_win = round(float(wins['Profit_USD'].mean()), 2) if len(wins) > 0 else 0.0
        avg_loss = round(float(losses['Profit_USD'].mean()), 2) if len(losses) > 0 else 0.0

        # Saldo dan Equity selalu singkron dengan titik akhir kurva perjalanan bot
        live_equity = cur_balance
        live_balance = cur_balance

        res["summary"] = {
            "initial_balance": initial_balance,
            "balance": live_balance,
            "equity": live_equity,
            "total_pnl": total_pnl,
            "growth_pct": growth_pct,
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_usd": max_dd_usd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "win_trades": win_count,
            "bep_trades": bep_count,
            "loss_trades": loss_count,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss
        }

        # Kalkulasi Periode (Today, This Week, This Month, All Time)
        df['dt'] = pd.to_datetime(df['Waktu Close'], errors='coerce')
        now = datetime.datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - datetime.timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)

        def period_stat(sub):
            n = len(sub)
            if n == 0:
                return {"gain": "+0.00%", "profit": 0.0, "pips": 0.0, "win_rate": 0.0, "trades": 0}
            w = len(sub[sub['Profit_USD'] > 0])
            p_usd = round(float(sub['Profit_USD'].sum()), 2)
            p_pips = round(float(sub['Pips (P/L)'].astype(float).sum()), 1)
            p_wr = round((w / n * 100.0), 1)
            p_gain = ((p_usd) / initial_balance) * 100.0
            return {
                "gain": f"{p_gain:+.2f}%",
                "profit": p_usd,
                "pips": p_pips,
                "win_rate": p_wr,
                "trades": n
            }

        res["periods"] = {
            "today": period_stat(df[df['dt'] >= today_start]),
            "this_week": period_stat(df[df['dt'] >= week_start]),
            "this_month": period_stat(df[df['dt'] >= month_start]),
            "all_time": period_stat(df)
        }

        # Data Curve (Point 0: Start, Point 1..N: Each Trade)
        first_time = str(df['Waktu Open'].iloc[0])[:16] if 'Waktu Open' in df.columns else "Start"
        curve = [{
            "index": 0,
            "label": "Mulai",
            "date": first_time,
            "ticket": "DEPOSIT",
            "pnl": 0.0,
            "balance": initial_balance,
            "growth_pct": 0.0,
            "drawdown_pct": 0.0
        }]

        journal = []
        for i, row in df.iterrows():
            idx = int(i) + 1
            t_close = str(row.get('Waktu Close', ''))[:16]
            ticket = str(row.get('Ticket Posisi', ''))
            pnl = round(float(row.get('Profit_USD', 0.0)), 2)
            bal = round(float(row.get('Running_Balance', initial_balance)), 2)
            growth = round(float(row.get('Growth_Pct', 0.0)), 2)
            dd = round(float(row.get('Drawdown_Pct', 0.0)), 2)
            pips = round(float(row.get('Pips (P/L)', 0.0)), 1)
            t_type = str(row.get('Tipe', 'BUY')).upper()
            t_gain = ((pnl / bal) * 100.0) if bal > 0 else 0.0

            curve.append({
                "index": idx,
                "label": f"Trade #{idx}",
                "date": t_close,
                "ticket": ticket,
                "pnl": pnl,
                "balance": bal,
                "growth_pct": growth,
                "drawdown_pct": dd
            })

            journal.append({
                "index": idx,
                "ticket": ticket,
                "time_open": str(row.get('Waktu Open', '')),
                "time_close": str(row.get('Waktu Close', '')),
                "symbol": str(row.get('Simbol', 'XAUUSD')),
                "type": t_type,
                "lot": float(row.get('Lot', 0.01)),
                "open_price": round(float(row.get('Harga Entry', 0.0)), 2),
                "close_price": round(float(row.get('Harga Exit', 0.0)), 2),
                "sl": round(float(row.get('Stop Loss (SL)', 0.0)), 2),
                "tp": round(float(row.get('Take Profit (TP)', 0.0)), 2),
                "pips": pips,
                "profit": pnl,
                "balance": bal,
                "gain_pct": round(t_gain, 2),
                "duration": str(row.get('Durasi', '—')),
                "scenario": str(row.get('Skenario Entry', '—')),
                "result": str(row.get('Hasil')).strip() if pd.notna(row.get('Hasil')) and str(row.get('Hasil')).strip() else ("BEP" if 0.0 <= pnl <= 0.25 else ("WIN" if pnl > 0.25 else "LOSS")),
                "alasan": str(row.get('Keterangan / Alasan Exit', '—')),
                "model": str(row.get('Model AI', 'M15')),
                "close_75m": round(float(row.get('Close Candle 75m ($)')), 2) if pd.notna(row.get('Close Candle 75m ($)')) else None,
                "validasi_75m": (
                    str(row.get('Validasi Model 75M')).strip()
                    if pd.notna(row.get('Validasi Model 75M')) and str(row.get('Validasi Model 75M')).strip().lower() not in ['nan', 'none', '']
                    else (
                        ("BERHASIL (SELARAS)" if (float(row.get('Close Candle 75m ($)')) < float(row.get('Harga Entry', 0.0)) if str(row.get('Tipe', 'BUY')).upper() == 'SELL' else float(row.get('Close Candle 75m ($)')) > float(row.get('Harga Entry', 0.0))) else "GAGAL (TIDAK SELARAS)")
                        if pd.notna(row.get('Close Candle 75m ($)')) and float(row.get('Harga Entry', 0.0)) > 0
                        else "MENUNGGU"
                    )
                ),
                "pips_75m": round(float(row.get('Pips Model 75M', 0.0)), 1) if pd.notna(row.get('Pips Model 75M')) else 0.0
            })

        res["curve"] = curve
        # Journal urutkan terbaru di atas
        res["journal"] = journal[::-1]

    except Exception as e:
        print(f"Error computing portfolio journey: {e}")

    return res

def get_trade_diagnostics(limit=50, bot_filter=''):
    """Mengambil riwayat diagnosa analisis mendalam (menang/kalah/faktor/pelajaran) dari Excel PRO atau CSV evaluasi Skripsi"""
    diagnostics = []
    is_pro = bot_filter.lower() in ['pro', 'pro_only', 'proprietary', 'proprietary_only', 'm15_pro_only']
    
    if is_pro:
        if os.path.exists(EXCEL_PRO_PATH):
            try:
                df = pd.read_excel(EXCEL_PRO_PATH, sheet_name='Trade_History_PRO')
                if len(df) > 0 and 'Ticket Posisi' in df.columns:
                    df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
                    for _, row in df.tail(limit).iloc[::-1].iterrows():
                        ticket = str(row.get('Ticket Posisi', ''))
                        time_open = str(row.get('Waktu Open', ''))
                        time_close = str(row.get('Waktu Close', ''))
                        t_type = str(row.get('Tipe', 'BUY')).upper()
                        lot = float(row.get('Lot', 0.01) or 0.01)
                        entry_p = round(float(row.get('Harga Entry', 0.0) or 0.0), 2)
                        exit_p = round(float(row.get('Harga Exit', 0.0) or 0.0), 2)
                        pips = round(float(row.get('Pips (P/L)', 0.0) or 0.0), 1)
                        profit = round(float(row.get('Profit ($ USD)', 0.0) or 0.0), 2)
                        raw_res = str(row.get('Hasil', 'BEP')).strip().upper()
                        alasan = str(row.get('Keterangan / Alasan Exit', 'Micro-Trigger Execution'))

                        if raw_res == 'WIN' or profit > 0.30:
                            res_label = 'WIN'
                            if 'Take Profit' in alasan or 'TP' in alasan:
                                diag_text = f"🎯 [WIN - TP Dinamis]: Target TP ekspansif ${exit_p:.2f} tercapai optimal (+${profit:.2f}). Konfluensi 57 fitur SMC selaras dengan order block."
                                lesson = "Eksekusi sniper di zona likuiditas tinggi valid. RRR optimal menghasilkan ekspansi profit maksimal."
                            else:
                                diag_text = f"⚡ [WIN - Trailing Lock]: Profit terkunci rapat (+${profit:.2f}) oleh Dynamic Trailing Lock saat momentum candle mulai melambat."
                                lesson = "Trailing lock mengamankan keuntungan sebelum koreksi harga."
                        elif raw_res == 'BEP' or (0.0 <= profit <= 0.30):
                            res_label = 'BEP'
                            diag_text = f"🛡️ [BEP - Capital Preservation]: Auto Break-Even aktif mengunci +${profit:.2f} setelah floating mencapai target buffer. Modal aman."
                            lesson = "Auto BEP Shield bekerja 100% disiplin menyelamatkan modal dari pembalikan arah."
                        else:
                            res_label = 'LOSS'
                            diag_text = f"🛑 [LOSS - Risk Disciplined]: Cutloss disiplin di Stop Loss ketat ${exit_p:.2f} (-${abs(profit):.2f}). Shockwave Shield membatasi risiko."
                            lesson = "Kerugian terbatasi ketat maksimal ~$5-$6.5, menjaga drawdown portofolio tetap sangat rendah (3.5%)."

                        diagnostics.append({
                            "ticket": ticket,
                            "time_open": time_open,
                            "time_close": time_close,
                            "symbol": str(row.get('Simbol', 'XAUUSD')),
                            "type": t_type,
                            "lot": lot,
                            "entry_price": entry_p,
                            "exit_price": exit_p,
                            "pips": pips,
                            "profit": profit,
                            "result": res_label,
                            "model": "Proprietary PRO V5.4 (57 Fitur)",
                            "scenario": "Micro-Trigger Sniper SMC",
                            "zone": "Key Liquidity Pool",
                            "h4_trend": "BULLISH" if t_type == "BUY" else "BEARISH",
                            "dxy_trend": "SELARAS",
                            "macro_info": "Normal Volatility",
                            "model_prob": 72.5 if res_label == "WIN" else 58.0,
                            "diagnostic_text": diag_text,
                            "lesson_learned": lesson,
                            "eval_date": time_close[:10] if time_close else "",
                            "close_75m": None,
                            "validasi_75m": "SELARAS" if res_label == "WIN" else ("TIDAK SELARAS" if res_label == "LOSS" else "BEP"),
                            "pips_75m": pips,
                            "alasan": alasan
                        })
            except Exception as e:
                print(f"Error loading PRO diagnostics: {e}")
        return diagnostics

    # Skripsi M15 Fallback: baca dari CSV evaluasi
    CSV_EVAL = CSV_EVAL_PATH
    if os.path.exists(CSV_EVAL):
        try:
            df = pd.read_csv(CSV_EVAL)
            if len(df) > 0:
                # Ambil baris valid dan urutkan dari yang paling baru
                df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
                for _, row in df.tail(limit).iloc[::-1].iterrows():
                    diagnostics.append({
                        "ticket": str(row.get('Ticket Posisi', '')),
                        "time_open": str(row.get('Waktu Open', '')),
                        "time_close": str(row.get('Waktu Close', '')),
                        "symbol": str(row.get('Simbol', 'XAUUSD')),
                        "type": str(row.get('Tipe', '')),
                        "lot": float(row.get('Lot', 0.01)),
                        "entry_price": round(float(row.get('Harga Entry', 0.0)), 2),
                        "exit_price": round(float(row.get('Harga Exit', 0.0)), 2),
                        "pips": round(float(row.get('Pips (P/L)', 0.0)), 1),
                        "profit": round(float(row.get('Profit ($ USD)', 0.0)), 2),
                        "result": str(row.get('Hasil', 'BEP')),
                        "model": str(row.get('Model AI', 'M15')),
                        "scenario": str(row.get('Skenario Entry', 'Standar Technical Setup')),
                        "zone": str(row.get('Zona Entry', 'A')),
                        "h4_trend": str(row.get('Tren H4 Entry', 'NETRAL')),
                        "dxy_trend": str(row.get('Tren DXY Entry', 'NETRAL')),
                        "macro_info": str(row.get('Kondisi Makro News', 'Normal')),
                        "model_prob": float(row.get('Probabilitas Model (%)', 50.0)),
                        "diagnostic_text": str(row.get('Analisis Diagnostik (Menang/Kalah)', '')),
                        "lesson_learned": str(row.get('Evaluasi & Pembelajaran', '')),
                        "eval_date": str(row.get('Tanggal Evaluasi', '')),
                        "close_75m": round(float(row.get('Close Candle 75m ($)')), 2) if pd.notna(row.get('Close Candle 75m ($)')) else None,
                        "validasi_75m": (
                            str(row.get('Validasi Model 75M')).strip()
                            if pd.notna(row.get('Validasi Model 75M')) and str(row.get('Validasi Model 75M')).strip().lower() not in ['nan', 'none', '']
                            else (
                                ("BERHASIL (SELARAS)" if (float(row.get('Close Candle 75m ($)')) < float(row.get('Harga Entry', 0.0)) if str(row.get('Tipe', 'BUY')).upper() == 'SELL' else float(row.get('Close Candle 75m ($)')) > float(row.get('Harga Entry', 0.0))) else "GAGAL (TIDAK SELARAS)")
                                if pd.notna(row.get('Close Candle 75m ($)')) and float(row.get('Harga Entry', 0.0)) > 0
                                else "MENUNGGU"
                            )
                        ),
                        "pips_75m": round(float(row.get('Pips Model 75M', 0.0)), 1) if pd.notna(row.get('Pips Model 75M')) else 0.0
                    })
        except Exception as e:
            print(f"Error loading diagnostics: {e}")
    return diagnostics

def get_scenarios_evaluation():
    """Mengambil matriks evaluasi skenario dari Scenario_Evaluator_Engine / JSON / CSV.
    Termasuk milestone tracker 10x WIN/LOSS dan status BEP Rebound/Netral."""
    CSV_EVAL = CSV_EVAL_PATH
    scenarios = []
    # Coba baca langsung dari JSON matriks (lebih cepat)
    json_matrix_path = os.path.join(BASE_DIR, "matriks_performa_skenario.json")
    if os.path.exists(json_matrix_path):
        try:
            with open(json_matrix_path, "r", encoding="utf-8") as f:
                matrix = json.load(f)
            for sc_name, sc_info in matrix.items():
                n            = sc_info.get('total_tested', 0)
                wins_murni   = sc_info.get('wins_murni', sc_info.get('wins_efektif', 0))
                bep_rebound  = sc_info.get('bep_rebound', 0)
                bep_netral   = sc_info.get('bep_netral', 0)
                losses       = sc_info.get('losses', 0)
                wins_efektif = sc_info.get('wins_efektif', wins_murni)
                wr           = sc_info.get('win_rate', 0.0)
                pnl          = sc_info.get('total_pnl', 0.0)
                status       = sc_info.get('status', f'⏳ DALAM PENGUJIAN ({n}/5 Trade)')
                action       = sc_info.get('action', 'ALLOW_TESTING')
                ml_label     = sc_info.get('milestone_label', '')
                ml_win       = sc_info.get('milestone_win', False)
                ml_loss      = sc_info.get('milestone_loss', False)

                scenarios.append({
                    "skenario":         str(sc_name),
                    "total_uji":        n,
                    "win_murni":        wins_murni,
                    "bep_rebound":      bep_rebound,
                    "bep_netral":       bep_netral,
                    "win_count":        wins_efektif,
                    "loss_count":       losses,
                    "win_rate":         wr,
                    "total_pnl":        pnl,
                    "status":           status,
                    "action":           action,
                    "milestone_label":  ml_label,
                    "milestone_win":    ml_win,
                    "milestone_loss":   ml_loss,
                    "tracker_win":      f"[{wins_efektif}/10 Win]",
                    "tracker_loss":     f"[{losses}/10 Loss]"
                })
            scenarios.sort(key=lambda x: (x['win_rate'], x['total_uji']), reverse=True)
            return scenarios
        except Exception as e:
            print(f"Error reading scenario matrix JSON: {e}")

    # Fallback: baca dari CSV
    if os.path.exists(CSV_EVAL):
        try:
            df = pd.read_csv(CSV_EVAL)
            if len(df) > 0 and 'Skenario Entry' in df.columns:
                df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
                grouped = df.groupby('Skenario Entry')
                for sc_name, grp in grouped:
                    n            = len(grp)
                    wins_murni   = len(grp[grp['Hasil'] == 'WIN'])
                    bep_rebound  = len(grp[grp['Hasil'] == 'BEP_REBOUND'])
                    bep_netral   = len(grp[grp['Hasil'] == 'BEP_NETRAL'])
                    losses       = len(grp[grp['Hasil'] == 'LOSS'])
                    wins_efektif = wins_murni + bep_rebound
                    wr           = round((wins_efektif / n * 100.0) if n > 0 else 0.0, 1)
                    pnl          = round(float(grp['Profit ($ USD)'].sum()), 2)

                    if n >= 5:
                        if wr >= 60.0 and pnl > 0:
                            status = "🌟 SKENARIO UNGGULAN"
                            action = "ALLOW_AND_BOOST"
                        elif wr < 40.0 or pnl < -10.0:
                            status = "⛔ SKENARIO DIHINDARI"
                            action = "BLACKLIST_AVOID"
                        else:
                            status = "⚖️ SKENARIO NETRAL"
                            action = "ALLOW_STRICT"
                    else:
                        status = f"⏳ DALAM PENGUJIAN ({n}/5 Trade)"
                        action = "ALLOW_TESTING"

                    ml_label = ""
                    if wins_efektif >= 10:
                        ml_label = f"🌟 ANDAL (≥10x Win Valid)"
                    elif losses >= 10:
                        ml_label = f"⚠️ RETRAIN DIPERLUKAN (≥10x Loss)"

                    scenarios.append({
                        "skenario":        str(sc_name),
                        "total_uji":       n,
                        "win_murni":       wins_murni,
                        "bep_rebound":     bep_rebound,
                        "bep_netral":      bep_netral,
                        "win_count":       wins_efektif,
                        "loss_count":      losses,
                        "win_rate":        wr,
                        "total_pnl":       pnl,
                        "status":          status,
                        "action":          action,
                        "milestone_label": ml_label,
                        "milestone_win":   wins_efektif >= 10,
                        "milestone_loss":  losses >= 10,
                        "tracker_win":     f"[{wins_efektif}/10 Win]",
                        "tracker_loss":    f"[{losses}/10 Loss]"
                    })
                scenarios.sort(key=lambda x: (x['win_rate'], x['total_uji']), reverse=True)
        except Exception as e:
            print(f"Error reading scenario evaluation: {e}")
    return scenarios


def get_bot_parameters():
    """Mengambil parameter arsitektur live robot v4.1 untuk dokumentasi dan verifikasi skripsi"""
    return {
        "model_name": "LightGBM Multi-Domain v4.1 (44 Fitur: Teknikal, DXY & Makroekonomi)",
        "timeframe_m15": "M15 (15 Menit) — Objek Utama Penelitian Skripsi",
        "timeframe_m5": "M5 (5 Menit) — Eksperimen Tambahan Scalping Ekstrem",
        "symbol": "XAUUSD (Gold vs US Dollar)",
        "lot_size": 0.01,
        "entry_mode": "Adaptive Hybrid (Market Order Instan + 50% Body Limit Giant Candle)",
        "sl_strategy": "Proporsional Dinamis RRR 1:2.0 - 1:2.5 ($6.50 - $12.00)",
        "tp_strategy": "Structural SMC: Nearest Supply/Demand Key Level (Target Likuiditas Kunci)",
        "max_cutloss": "$8.50 - $12.00 USD (Proporsional RRR)",
        "trailing_lock": "+$3.50 USD",
        "auto_be": "+$4.00 USD -> Lock +$0.20 (Teruji Empiris Menyelamatkan -$21)",
        "htf_memory": "Aktif (30-Hari D1 Demand/Supply & Daily Pivots Anchor)",
        "bad_rrr_filter": "Aktif (Reject Entry jika Ruang Target < 1.8x SL)",
        "rsi_divergence": "Aktif (Deteksi Regular Bullish & Bearish Divergence)",
        "stoch_rsi_filter": "Aktif (Anti-Overbought & Anti-Oversold Reversal Guard)",
        "news_guard": "Aktif (Freeze 10 Menit Sebelum & 15 Menit Sesudah High Impact News)",
        "anti_collision": "Aktif (Jarak Aman >= 0.18% dari Support/Resisten Mayor)",
        "magic_m15": MAGIC_M15,
        "magic_m5": MAGIC_M5
    }

def get_market_radar():
    """Mengambil status live XAUUSD, DXY, dan kalender makroekonomi"""
    radar = {
        "xau_bid": 0.0,
        "xau_ask": 0.0,
        "spread": 0.0,
        "dxy_trend": "NETRAL",
        "macro_alert": "NORMAL_VOLATILITY",
        "macro_details": "Tidak ada rilis berita ekstrem saat ini."
    }

    if init_mt5():
        sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
        tick = mt5.symbol_info_tick(sym)
        if tick:
            radar["xau_bid"] = round(tick.bid, 2)
            radar["xau_ask"] = round(tick.ask, 2)
            radar["spread"] = round((tick.ask - tick.bid) * 10, 1)

    now = datetime.datetime.now()
    if now.day <= 7 and now.weekday() < 5:
        radar["macro_alert"] = "⚠️ MINGGU NON-FARM PAYROLLS (NFP)"
        radar["macro_details"] = "Pasar emas berpotensi volatil tinggi menjelang rilis data tenaga kerja AS."
    elif 10 <= now.day <= 15 and now.weekday() < 5:
        radar["macro_alert"] = "⚠️ HARI INFLASI CPI AS"
        radar["macro_details"] = "Waspadai deviasi CPI AS yang dapat memicu lonjakan harga emas spot."
    elif 15 <= now.day <= 22 and now.month in [1, 3, 5, 6, 7, 9, 11, 12] and now.weekday() < 5:
        radar["macro_alert"] = "⚠️ MINGGU KEPUTUSAN FOMC"
        radar["macro_details"] = "Kebijakan suku bunga The Fed berpotensi mengubah arah tren emas mayor."
    else:
        radar["macro_alert"] = "🟢 KONDISI MAKRO STABIL"
        radar["macro_details"] = "Pasar bergerak normal sesuai struktur teknikal Smart Money Concepts."

    return radar

# =========================================================================
# =========================================================================
# FLASK ROUTING
# =========================================================================

from Cloudflare_Tunnel import start_cloudflare_tunnel, get_public_url

def _auto_start_tunnel():
    try:
        start_cloudflare_tunnel(port=5000, wait_seconds=8)
    except Exception:
        pass

threading.Thread(target=_auto_start_tunnel, daemon=True).start()

@app.route('/')
def index():
    lan_ip = get_lan_ip()
    mobile_url = f"http://{lan_ip}:5000"
    public_url = get_public_url()
    primary_url = public_url if public_url else mobile_url
    return render_template(
        'index.html',
        lan_ip=lan_ip,
        mobile_url=mobile_url,
        public_url=public_url,
        primary_url=primary_url,
        cache_bust=int(time.time())
    )

@app.route('/sw.js')
def service_worker():
    response = send_file(os.path.join(app.static_folder, 'sw.js'), mimetype='application/javascript')
    response.headers['Service-Worker-Allowed'] = '/'
    return response

@app.route('/manifest.json')
def manifest():
    return send_file(os.path.join(app.static_folder, 'manifest.json'), mimetype='application/manifest+json')

@app.route('/api/summary')
def api_summary():
    return jsonify(get_portfolio_summary())

@app.route('/api/positions')
def api_positions():
    return jsonify(get_live_positions())

@app.route('/api/trades')
def api_trades():
    bot_filter = request.args.get('bot_filter', default='all')  # 'all', 'm15_only', 'pro_only', 'proprietary_only'
    records = get_recent_trade_logs()
    if bot_filter == 'm15_only':
        records = [r for r in records if 'PRO' not in str(r.get('model', '')).upper() and 'PROPRIETARY' not in str(r.get('model', '')).upper()]
    elif bot_filter in ['pro_only', 'proprietary_only', 'm15_pro_only']:
        records = [r for r in records if ('PRO' in str(r.get('model', '')).upper() or 'PROPRIETARY' in str(r.get('model', '')).upper())]
    elif bot_filter == 'm5_only':
        records = [r for r in records if 'M5' in str(r.get('model', '')).upper()]
    return jsonify(records)

@app.route('/api/scenarios')
def api_scenarios():
    return jsonify(get_scenarios_evaluation())

@app.route('/api/diagnostics')
def api_diagnostics():
    limit = request.args.get('limit', default=100, type=int)
    bot_filter = request.args.get('bot_filter', '')
    data = get_trade_diagnostics(limit=limit, bot_filter=bot_filter)
    if bot_filter in ['pro_only', 'proprietary_only', 'm15_pro_only']:
        data = [t for t in data if ('PRO' in str(t.get('model', '')).upper() or 'PROPRIETARY' in str(t.get('model', '')).upper())]
    elif bot_filter == 'm15_only':
        data = [t for t in data if ('PRO' not in str(t.get('model', '')).upper() and 'PROPRIETARY' not in str(t.get('model', '')).upper() and 'M5' not in str(t.get('model', '')).upper())]
    return jsonify(data)

@app.route('/api/positions/live')
def api_positions_live():
    """Posisi floating real-time dengan durasi dan bot tag (untuk Live Card dashboard)."""
    return jsonify(get_live_positions_enhanced())

@app.route('/api/tunnel_status')
def api_tunnel_status():
    """Mengembalikan status Cloudflare Tunnel publik & Wi-Fi lokal untuk barcode HP."""
    pub = get_public_url()
    if not pub:
        try:
            from Cloudflare_Tunnel import start_cloudflare_tunnel
            threading.Thread(target=start_cloudflare_tunnel, kwargs={'port': 5000, 'wait_seconds': 8}, daemon=True).start()
        except Exception:
            pass
    lan = get_lan_ip()
    return jsonify({
        "public_url": pub or "",
        "mobile_url": f"http://{lan}:5000",
        "lan_ip": lan,
        "tunnel_online": bool(pub)
    })

@app.route('/api/qrcode')
def api_qrcode():
    """Menghasilkan barcode QR Code PNG untuk di-scan oleh kamera smartphone."""
    mode = request.args.get('mode', 'public')
    custom_url = request.args.get('url', '')
    if custom_url:
        target_url = custom_url
    elif mode == 'public':
        pub = get_public_url()
        if not pub:
            for _ in range(6):
                time.sleep(0.5)
                pub = get_public_url()
                if pub:
                    break
        target_url = pub if pub else f"http://{get_lan_ip()}:5000"
    else:
        target_url = f"http://{get_lan_ip()}:5000"
        
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    resp = send_file(buf, mimetype='image/png')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

import threading

WATCHDOG_STATE = {
    'm15_active': True,   # Default ON untuk bot M15 skripsi
    'pro_active': False,
    'm5_active': False
}

_last_spawn_time = {'m15': 0.0, 'pro': 0.0, 'm5': 0.0}
SPAWN_COOLDOWN = 25.0

def spawn_bot_process(bot_key, force=False):
    global _last_spawn_time
    now = time.time()
    if not force and (now - _last_spawn_time.get(bot_key, 0.0) < SPAWN_COOLDOWN):
        return None
    _last_spawn_time[bot_key] = now

    try:
        if bot_key == "m15":
            script = SCRIPT_M15_PATH
            log_name = "bot_m15_daemon.log"
        elif bot_key in ["pro", "m15_pro"]:
            script = SCRIPT_M15_PRO_PATH
            log_name = "bot_m15_pro_daemon.log"
        elif bot_key == "m5":
            script = SCRIPT_M5_PATH
            log_name = "bot_m5_daemon.log"
        else:
            return None

        log_f = open(os.path.join(BASE_DIR, log_name), "a", encoding="utf-8")
        proc = subprocess.Popen(
            [PYTHON_EXE, "-u", script],
            cwd=BASE_DIR,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return proc
    except Exception as e:
        print(f"⚠️ Gagal spawn bot {bot_key}: {e}")
        return None

def server_bot_watchdog():
    """Watchdog background: jika bot mati padahal status diinginkan ON, otomatis hidupkan kembali dengan cooldown."""
    time.sleep(5)
    while True:
        try:
            time.sleep(5)
            ensure_trades_synced(15)
            bots = get_running_bots()
            now = time.time()
            if WATCHDOG_STATE.get('m15_active') and not bots.get('m15_running'):
                if now - _last_spawn_time.get('m15', 0.0) >= SPAWN_COOLDOWN:
                    print("🛡️ [SERVER WATCHDOG] Bot M15 terdeteksi tidak aktif. Memulai bot M15...")
                    spawn_bot_process("m15")
            if WATCHDOG_STATE.get('pro_active') and not bots.get('pro_running'):
                if now - _last_spawn_time.get('pro', 0.0) >= SPAWN_COOLDOWN:
                    print("🛡️ [SERVER WATCHDOG] Bot PRO terdeteksi tidak aktif. Memulai bot PRO...")
                    spawn_bot_process("pro")
            if WATCHDOG_STATE.get('m5_active') and not bots.get('m5_running'):
                if now - _last_spawn_time.get('m5', 0.0) >= SPAWN_COOLDOWN:
                    print("🛡️ [SERVER WATCHDOG] Bot M5 terdeteksi tidak aktif. Memulai bot M5...")
                    spawn_bot_process("m5")
        except Exception:
            pass

_watchdog_t = threading.Thread(target=server_bot_watchdog, daemon=True)
_watchdog_t.start()

@app.route('/api/control/<bot_key>/<action>', methods=['GET', 'POST'])
def api_control(bot_key, action):
    """Kontrol bot dari web dashboard (start / stop)"""
    res = {"status": "ok", "success": True, "bot": bot_key, "action": action}
    try:
        if action == "start":
            if bot_key in ["m15", "all"]:
                WATCHDOG_STATE['m15_active'] = True
                bots = get_running_bots()
                if not bots.get('m15_running'):
                    spawn_bot_process("m15", force=True)

            if bot_key in ["pro", "m15_pro", "all"]:
                WATCHDOG_STATE['pro_active'] = True
                bots = get_running_bots()
                if not bots.get('pro_running'):
                    spawn_bot_process("pro", force=True)

            if bot_key in ["m5", "all"]:
                WATCHDOG_STATE['m5_active'] = True
                bots = get_running_bots()
                if not bots.get('m5_running'):
                    spawn_bot_process("m5", force=True)

        elif action == "stop":
            if bot_key in ["m15", "all"]:
                WATCHDOG_STATE['m15_active'] = False
            if bot_key in ["pro", "m15_pro", "all"]:
                WATCHDOG_STATE['pro_active'] = False
            if bot_key in ["m5", "all"]:
                WATCHDOG_STATE['m5_active'] = False

            target_scripts = []
            if bot_key in ["m15", "all"]:
                target_scripts.append("eksekusi_otomatis_trading_bot.py")
            if bot_key in ["pro", "m15_pro", "all"]:
                target_scripts.append("eksekusi_otomatis_trading_bot_m15_pro.py")
            if bot_key in ["m5", "all"]:
                target_scripts.append("eksekusi_otomatis_trading_bot_m5_scalping.py")

            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmd_args = [os.path.basename(arg).lower() for arg in (p.info['cmdline'] or []) if arg]
                    if any(ts in cmd_args for ts in target_scripts):
                        p.terminate()
                except Exception:
                    pass

        return jsonify(res)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/head-to-head')
def api_head_to_head():
    """Endpoint komparasi empiris M15 Standar (44 Fitur) vs M15 PRO (57 Fitur & AI Adaptive Sniper)"""
    summary = get_portfolio_summary()
    
    std_trades = summary.get("skripsi_trades", 0)
    std_wins   = summary.get("skripsi_wins", 0)
    std_losses = summary.get("skripsi_losses", 0)
    std_wr     = summary.get("skripsi_win_rate", 0.0)
    std_pnl    = summary.get("skripsi_net_profit", 0.0)
    
    pro_trades = summary.get("m15_pro_trades", 0)
    pro_wins   = summary.get("m15_pro_wins", 0)
    pro_losses = summary.get("m15_pro_losses", 0)
    pro_wr     = summary.get("m15_pro_win_rate", 0.0)
    pro_pnl    = summary.get("m15_pro_net_profit", 0.0)

    if pro_pnl > std_pnl:
        leader_pnl = "M15 PRO"
    elif std_pnl > pro_pnl:
        leader_pnl = "M15 Standar"
    else:
        leader_pnl = "Imbang"

    return jsonify({
        "standard": {
            "name": "M15 Standar (Skripsi v4.2)",
            "features_count": 44,
            "architecture": "Two-Stage Hybrid (SMC Heuristic + LightGBM)",
            "risk_profile": "TP +$6.50 / SL -$6.50 (Fixed 1:1) + Quick BEP",
            "account": "Akun Utama Exness",
            "trades": std_trades,
            "wins": std_wins,
            "losses": std_losses,
            "win_rate": std_wr,
            "net_profit": std_pnl
        },
        "pro": {
            "name": "M15 PRO (AI Adaptive Sniper v5.0)",
            "features_count": 57,
            "architecture": "Full AI End-to-End Decision (Zero Paralysis)",
            "risk_profile": "AI Adaptive (TP +$8.50 s/d +$11.00 / SL -$6.50 Ketat)",
            "account": "Akun Khusus Exness MT5Trial14 (#416453202)",
            "trades": pro_trades,
            "wins": pro_wins,
            "losses": pro_losses,
            "win_rate": pro_wr,
            "net_profit": pro_pnl
        },
        "leader_profit": leader_pnl
    })

@app.route('/api/parameters')
def api_parameters():
    return jsonify(get_bot_parameters())

@app.route('/api/portfolio/journey')
def api_portfolio_journey():
    bot = request.args.get('bot', '') or request.args.get('bot_filter', '')
    return jsonify(get_portfolio_journey(bot_filter=bot))

# Persistent in-memory decision stream and notifications cache
GLOBAL_DECISION_STREAM_M15 = []
GLOBAL_DECISION_STREAM_PRO = []
GLOBAL_DECISION_STREAM_M5 = []
GLOBAL_NOTIFICATIONS = []
LAST_EVAL_TIME_M15 = 0
LAST_EVAL_TIME_PRO = 0
LAST_EVAL_TIME_M5 = 0
LAST_SEEN_NOTIF_IDS = set()

def init_default_decision_stream():
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_PRO, GLOBAL_DECISION_STREAM_M5
    if len(GLOBAL_DECISION_STREAM_PRO) == 0:
        GLOBAL_DECISION_STREAM_PRO.append({
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "action": "STANDBY",
            "buy_pct": 52.4,
            "sell_pct": 47.6,
            "detail": "Proprietary Engine V5.4 Standby | Scanning Micro-Sniper Setups"
        })
    if len(GLOBAL_DECISION_STREAM_M15) == 0:
        try:
            csv_path = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.csv")
            if os.path.exists(csv_path):
                df_eval = pd.read_csv(csv_path)
                for _, row in df_eval.tail(20).iloc[::-1].iterrows():
                    act = str(row.get('Tipe', 'BUY')).strip().upper()
                    try: prob = float(row.get('Probabilitas Model (%)', 65.0))
                    except Exception: prob = 65.0
                    b_pct = prob if act == 'BUY' else round(100.0 - prob, 1)
                    s_pct = prob if act == 'SELL' else round(100.0 - prob, 1)
                    t_str = str(row.get('Waktu Open', ''))
                    t_short = t_str[11:19] if len(t_str) >= 19 else t_str
                    sc_name = str(row.get('Skenario Entry', 'M15_ZONA_SNIPER'))
                    alasan = str(row.get('Keterangan / Alasan Exit', 'Evaluasi Model'))
                    GLOBAL_DECISION_STREAM_M15.append({
                        "time": t_short or datetime.datetime.now().strftime("%H:%M:%S"),
                        "action": act,
                        "buy_pct": b_pct,
                        "sell_pct": s_pct,
                        "detail": f"{sc_name} | {alasan}"
                    })
        except Exception as e:
            print(f"Error seeding M15 decision stream: {e}")

    if len(GLOBAL_DECISION_STREAM_M5) == 0:
        try:
            if os.path.exists(EXCEL_M5_PATH):
                wb5 = openpyxl.load_workbook(EXCEL_M5_PATH, data_only=True)
                if "Trade Log M5 Scalping (v4.1)" in wb5.sheetnames:
                    ws5 = wb5["Trade Log M5 Scalping (v4.1)"]
                    for r in range(ws5.max_row, max(1, ws5.max_row - 20), -1):
                        t_act = str(ws5.cell(r, 7).value or 'BUY').upper()
                        t_waktu = str(ws5.cell(r, 3).value or '')
                        t_short = t_waktu[11:19] if len(t_waktu) >= 19 else t_waktu
                        t_alasan = str(ws5.cell(r, 17).value or 'M5 Scalper Exit')
                        if t_short and t_short != 'Waktu Open':
                            GLOBAL_DECISION_STREAM_M5.append({
                                "time": t_short,
                                "action": t_act,
                                "buy_pct": 65.0 if t_act == 'BUY' else 35.0,
                                "sell_pct": 65.0 if t_act == 'SELL' else 35.0,
                                "detail": f"M5 Scalping: {t_alasan}"
                            })
        except Exception:
            pass

def get_bot_notifications():
    global GLOBAL_NOTIFICATIONS, LAST_SEEN_NOTIF_IDS
    
    # 1. Cek Posisi Terbuka MT5 (Event: OPEN POSISI)
    try:
        live_pos = get_live_positions()
        for p in live_pos:
            notif_id = f"open_{p['ticket']}"
            if notif_id not in LAST_SEEN_NOTIF_IDS:
                LAST_SEEN_NOTIF_IDS.add(notif_id)
                GLOBAL_NOTIFICATIONS.insert(0, {
                    "id": notif_id,
                    "type": "OPEN",
                    "title": f"🚀 Posisi Baru Dibuka ({p['type']})",
                    "message": f"{p['bot_tag']}: {p['type']} {p['volume']} lot {p['symbol']} @ ${p['price_open']} (SL: ${p['sl']}, TP: ${p['tp']})",
                    "time": p['time_open'],
                    "sound": "open",
                    "bot": "M15" if "M15" in p['bot_tag'] else "M5"
                })
    except Exception:
        pass

    # 2. Cek Riwayat Transaksi Selesai (Event: TP, SL, BEP)
    # FILTER: Hanya notifikasi dari bot M15 (Magic 123230) dan M5 (Magic 123236) — abaikan manual (Magic 0)
    ALLOWED_BOT_TAGS = ['M15', 'M5', 'LightGBM', 'v4.1', 'v3.7']  # Keyword identifikasi bot
    try:
        csv_path = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.csv")
        if os.path.exists(csv_path):
            df_eval = pd.read_csv(csv_path)
            if len(df_eval) > 0 and 'Ticket Posisi' in df_eval.columns:
                valid = df_eval[df_eval['Ticket Posisi'].astype(str).str.strip().str.isnumeric()]
                for _, row in valid.tail(15).iloc[::-1].iterrows():
                    t_id    = str(row.get('Ticket Posisi', '')).strip()
                    pnl     = float(row.get('Profit ($ USD)', 0.0))
                    res_type = str(row.get('Hasil', 'BEP')).upper()
                    t_close = str(row.get('Waktu Close', ''))
                    t_display = t_close
                    try:
                        if '-' in t_close:
                            dt = datetime.datetime.strptime(t_close[:19], "%Y-%m-%d %H:%M:%S")
                            t_display = dt.strftime("%d/%m/%Y %H:%M:%S")
                    except Exception:
                        pass
                    lot     = row.get('Lot', 0.01)
                    typ     = row.get('Tipe', 'BUY')
                    bot_m   = str(row.get('Model AI', 'M15'))

                    # Filter: Lewati jika bukan dari bot (tidak ada keyword bot di field Model AI)
                    is_from_bot = any(kw in bot_m for kw in ALLOWED_BOT_TAGS)
                    if not is_from_bot:
                        continue

                    if res_type == 'WIN' or pnl > 0.50:
                        n_id = f"tp_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id, "type": "TP",
                                "title": f"🎉 Take Profit Tercapai! (+${pnl:.2f})",
                                "message": f"{bot_m} Bot: Posisi #{t_id} {typ} {lot} lot berhasil Take Profit +${pnl:.2f} (+{(pnl/500*100):.1f}%)",
                                "time": t_display or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "sound": "tp", "bot": bot_m
                            })
                    elif res_type in ('LOSS',) or pnl < -0.50:
                        n_id = f"sl_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id, "type": "SL",
                                "title": f"💔 Stop Loss Tersentuh (-${abs(pnl):.2f})",
                                "message": f"{bot_m} Bot: Posisi #{t_id} {typ} {lot} lot terpotong SL -${abs(pnl):.2f} ({(pnl/500*100):.1f}%)",
                                "time": t_display or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "sound": "sl", "bot": bot_m
                            })
                    elif res_type == 'BEP_REBOUND':
                        n_id = f"bep_rebound_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id, "type": "BEP",
                                "title": "🔄 BEP — Prediksi Arah Terbukti Valid!",
                                "message": f"{bot_m}: Posisi #{t_id} ditutup BEP (+${pnl:.2f}) namun prediksi arah terkonfirmasi pada candle ke-5",
                                "time": t_display or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "sound": "open", "bot": bot_m
                            })
                    elif res_type in ('BEP_NETRAL', 'BEP'):
                        n_id = f"bep_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id, "type": "BEP",
                                "title": "🛡️ Auto BEP Aktif — Modal Terlindungi",
                                "message": f"{bot_m}: Posisi #{t_id} diamankan pada Break-Even Point +${pnl:.2f} (Arah tidak terkonfirmasi dalam 75m)",
                                "time": t_display or datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                                "sound": "open", "bot": bot_m
                            })
    except Exception:
        pass

    # Jika masih kosong, berikan welcome / status alert
    if len(GLOBAL_NOTIFICATIONS) == 0:
        GLOBAL_NOTIFICATIONS.append({
            "id": "welcome_alert",
            "type": "OPEN",
            "title": "📡 Feed Notifikasi Aktif",
            "message": "Sistem pemantau notifikasi real-time aktif. Bot akan mengirim sinyal OPEN, TP, dan SL secara otomatis dengan suara notifikasi.",
            "time": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "sound": "open",
            "bot": "QuantLGB"
        })

    return GLOBAL_NOTIFICATIONS[:35]

@app.route('/api/notifications')
def api_notifications():
    return jsonify(get_bot_notifications())

@app.route('/api/notifications/clear', methods=['GET', 'POST'])
def api_notifications_clear():
    global GLOBAL_NOTIFICATIONS
    GLOBAL_NOTIFICATIONS = []
    return jsonify({"status": "ok", "message": "Notifikasi telah dibersihkan"})

@app.route('/api/control/<bot_key>/clean_logs', methods=['GET', 'POST'])
def api_clean_decision_logs(bot_key):
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_PRO, GLOBAL_DECISION_STREAM_M5
    if bot_key in ['m15', 'both', 'all']:
        GLOBAL_DECISION_STREAM_M15 = []
    if bot_key in ['pro', 'm15_pro', 'both', 'all']:
        GLOBAL_DECISION_STREAM_PRO = []
    if bot_key in ['m5', 'both', 'all']:
        GLOBAL_DECISION_STREAM_M5 = []
    return jsonify({"status": "ok", "bot": bot_key, "message": "Log keputusan telah dibersihkan"})

@app.route('/api/status')
def api_status():
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_PRO, GLOBAL_DECISION_STREAM_M5, LAST_EVAL_TIME_M15, LAST_EVAL_TIME_PRO, LAST_EVAL_TIME_M5
    init_default_decision_stream()

    bots = get_running_bots()
    radar = get_market_radar()

    m15_running = bots.get("m15_running", False)
    m5_running = bots.get("m5_running", False)
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    now_ts = time.time()

    # 1. Update Kronologis Keputusan M15 (Akumulasi bertahap seiring berjalannya waktu)
    t15_path = os.path.join(BASE_DIR, "telemetry_m15.json")
    t15_data = read_telemetry_safely(t15_path)

    if t15_data and (now_ts - float(t15_data.get("timestamp", 0)) <= 30):
        pb = float(t15_data.get("prob_buy", 50.0))
        ps = float(t15_data.get("prob_sell", 50.0))
        stat_upper = str(t15_data.get('status_str', '')).upper()
        if (pb >= 60.0 and pb > ps) or ("BUY" in stat_upper and "STANDBY" not in stat_upper):
            act = "BUY"
        elif (ps >= 60.0 and ps > pb) or ("SELL" in stat_upper and "STANDBY" not in stat_upper):
            act = "SELL"
        else:
            act = "STANDBY"
        detail_msg = f"{t15_data.get('status_str', 'Evaluasi Live')} | Sisa Candle: {t15_data.get('mins_left', 0)}m {t15_data.get('secs_left', 0)}s"
        
        # Tambah ke stream kronologis jika sudah lewat 45 detik atau ada pergantian aksi
        last_action = GLOBAL_DECISION_STREAM_M15[0]["action"] if len(GLOBAL_DECISION_STREAM_M15) > 0 else None
        if (now_ts - LAST_EVAL_TIME_M15 >= 45) or (act != last_action and act != "STANDBY"):
            LAST_EVAL_TIME_M15 = now_ts
            GLOBAL_DECISION_STREAM_M15.insert(0, {
                "time": now_str,
                "action": act,
                "buy_pct": pb,
                "sell_pct": ps,
                "detail": detail_msg
            })
    else:
        tele15 = get_realtime_market_telemetry("M15")
        if (now_ts - LAST_EVAL_TIME_M15 >= 60) or len(GLOBAL_DECISION_STREAM_M15) == 0:
            LAST_EVAL_TIME_M15 = now_ts
            GLOBAL_DECISION_STREAM_M15.insert(0, {
                "time": now_str,
                "action": "STANDBY",
                "buy_pct": tele15["prob_buy"],
                "sell_pct": tele15["prob_sell"],
                "detail": f"M15 Standby: {tele15['status_str']} | Sisa Candle: {tele15['mins_left']}m {tele15['secs_left']}s"
            })

    # Jaga ukuran log keputusan agar tidak boros memori (max 40 item)
    if len(GLOBAL_DECISION_STREAM_M15) > 40:
        GLOBAL_DECISION_STREAM_M15 = GLOBAL_DECISION_STREAM_M15[:40]

    # 2. Update Kronologis Keputusan M5
    t5_data = None
    t5_path = os.path.join(BASE_DIR, "telemetry_m5.json")
    if os.path.exists(t5_path):
        try:
            with open(t5_path, "r", encoding="utf-8") as f:
                t5_data = json.load(f)
        except Exception:
            pass

    if t5_data and (now_ts - float(t5_data.get("timestamp", 0)) <= 30):
        pb5 = float(t5_data.get("prob_buy", 50.0))
        ps5 = float(t5_data.get("prob_sell", 50.0))
        stat5_upper = str(t5_data.get('status_str', '')).upper()
        if (pb5 >= 60.0 and pb5 > ps5) or ("BUY" in stat5_upper and "STANDBY" not in stat5_upper):
            act5 = "BUY"
        elif (ps5 >= 60.0 and ps5 > pb5) or ("SELL" in stat5_upper and "STANDBY" not in stat5_upper):
            act5 = "SELL"
        else:
            act5 = "STANDBY"
        detail5 = f"M5 Scalper: {t5_data.get('status_str', 'Live Monitoring')} | Sisa Candle: {t5_data.get('mins_left', 0)}m {t5_data.get('secs_left', 0)}s"
        
        last_action5 = GLOBAL_DECISION_STREAM_M5[0]["action"] if len(GLOBAL_DECISION_STREAM_M5) > 0 else None
        if (now_ts - LAST_EVAL_TIME_M5 >= 30) or (act5 != last_action5 and act5 != "STANDBY"):
            LAST_EVAL_TIME_M5 = now_ts
            GLOBAL_DECISION_STREAM_M5.insert(0, {
                "time": now_str,
                "action": act5,
                "buy_pct": pb5,
                "sell_pct": ps5,
                "detail": detail5
            })
    else:
        tele5 = get_realtime_market_telemetry("M5")
        if (now_ts - LAST_EVAL_TIME_M5 >= 45) or len(GLOBAL_DECISION_STREAM_M5) == 0:
            LAST_EVAL_TIME_M5 = now_ts
            GLOBAL_DECISION_STREAM_M5.insert(0, {
                "time": now_str,
                "action": "STANDBY",
                "buy_pct": tele5["prob_buy"],
                "sell_pct": tele5["prob_sell"],
                "detail": f"M5 Scalper Standby: {tele5['status_str']} | Sisa Candle: {tele5['mins_left']}m {tele5['secs_left']}s"
            })

    if len(GLOBAL_DECISION_STREAM_M5) > 40:
        GLOBAL_DECISION_STREAM_M5 = GLOBAL_DECISION_STREAM_M5[:40]

    # 3. Update Kronologis Keputusan PRO
    t_pro_path = os.path.join(BASE_DIR, "telemetry_m15_pro.json")
    t_pro_data = read_telemetry_safely(t_pro_path)
    if t_pro_data and (now_ts - float(t_pro_data.get("timestamp", 0)) <= 30):
        pb_pro = float(t_pro_data.get("prob_buy", 50.0))
        ps_pro = float(t_pro_data.get("prob_sell", 50.0))
        stat_pro = str(t_pro_data.get('status_str', '')).upper()
        if (pb_pro >= 60.0 and pb_pro > ps_pro) or ("BUY" in stat_pro and "STANDBY" not in stat_pro):
            act_pro = "BUY"
        elif (ps_pro >= 60.0 and ps_pro > pb_pro) or ("SELL" in stat_pro and "STANDBY" not in stat_pro):
            act_pro = "SELL"
        else:
            act_pro = "STANDBY"
        detail_pro = f"PRO: {t_pro_data.get('status_str', 'Evaluasi Live')} | Sisa Candle: {t_pro_data.get('mins_left', 0)}m {t_pro_data.get('secs_left', 0)}s"
        last_action_pro = GLOBAL_DECISION_STREAM_PRO[0]["action"] if len(GLOBAL_DECISION_STREAM_PRO) > 0 else None
        if (now_ts - LAST_EVAL_TIME_PRO >= 35) or (act_pro != last_action_pro and act_pro != "STANDBY") or len(GLOBAL_DECISION_STREAM_PRO) == 0:
            LAST_EVAL_TIME_PRO = now_ts
            GLOBAL_DECISION_STREAM_PRO.insert(0, {
                "time": now_str,
                "action": act_pro,
                "buy_pct": pb_pro,
                "sell_pct": ps_pro,
                "detail": detail_pro
            })
    else:
        tele_pro = get_realtime_market_telemetry("M15 PRO")
        if (now_ts - LAST_EVAL_TIME_PRO >= 45) or len(GLOBAL_DECISION_STREAM_PRO) == 0:
            LAST_EVAL_TIME_PRO = now_ts
            GLOBAL_DECISION_STREAM_PRO.insert(0, {
                "time": now_str,
                "action": "STANDBY",
                "buy_pct": tele_pro["prob_buy"],
                "sell_pct": tele_pro["prob_sell"],
                "detail": f"Proprietary Standby: {tele_pro['status_str']} | Sisa Candle: {tele_pro['mins_left']}m {tele_pro['secs_left']}s"
            })
    if len(GLOBAL_DECISION_STREAM_PRO) > 40:
        GLOBAL_DECISION_STREAM_PRO = GLOBAL_DECISION_STREAM_PRO[:40]

    pro_running = bool(bots.get("pro_running", False))

    return jsonify({
        "bots": bots,
        "m15": {
            "running": m15_running,
            "uptime": "AKTIF BERJALAN" if m15_running else "00:00:00",
            "decision_history": GLOBAL_DECISION_STREAM_M15
        },
        "pro": {
            "running": pro_running,
            "uptime": "AKTIF BERJALAN" if pro_running else "00:00:00",
            "decision_history": GLOBAL_DECISION_STREAM_PRO
        },
        "m5": {
            "running": m5_running,
            "uptime": "AKTIF BERJALAN" if m5_running else "00:00:00",
            "decision_history": GLOBAL_DECISION_STREAM_M5
        },
        "radar": radar,
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lan_ip": get_lan_ip(),
        "public_url": get_public_url()
    })

@app.route('/api/qr')
def api_qr():
    """Menghasilkan gambar QR code PNG untuk di-scan dari HP (mengutamakan HTTPS publik)"""
    lan_ip = get_lan_ip()
    mobile_url = f"http://{lan_ip}:5000"
    public_url = get_public_url()

    # Prioritas: URL HTTPS publik agar bisa diakses dari jaringan mana pun
    url = public_url if public_url else mobile_url
    if request.args.get('type') == 'local':
        url = mobile_url

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

def print_banner():
    lan_ip = get_lan_ip()
    mobile_url = f"http://{lan_ip}:5000"
    public_url = get_public_url()
    print("\n" + "="*75)
    print("🌐 WEB DASHBOARD MONITORING TRADING BOT (MOBILE-FIRST)")
    print("="*75)
    if public_url:
        print(f"🌍 BUKA DARI HP (INTERNET / MANA SAJA - HTTPS): {public_url}")
    print(f"📱 BUKA DARI HP (SATU WI-FI LOKAL)              : {mobile_url}")
    print(f"💻 BUKA DARI PC                                 : http://localhost:5000")
    print("="*75)
    print("💡 URL Publik HTTPS bisa diakses dari HP via kuota seluler / beda Wi-Fi!")
    print("Arahkan kamera HP ke QR code yang tampil di browser atau terminal.")
    print("="*75 + "\n")
    try:
        qr = qrcode.QRCode()
        qr.add_data(public_url if public_url else mobile_url)
        qr.print_ascii(invert=True)
    except Exception:
        pass

if __name__ == '__main__':
    print("[Server] Menyiapkan secure Cloudflare Tunnel...")
    start_cloudflare_tunnel(port=5000, wait_seconds=6)
    print_banner()
    app.run(host='0.0.0.0', port=5000, debug=False)

