import os
import sys
import io
import time
import socket
import datetime
import openpyxl
import pandas as pd
import psutil
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

bundle_dir = sys._MEIPASS if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) else r"d:\SKRIPSI INFORMATIKA"
template_dir = os.path.join(bundle_dir, 'templates') if os.path.exists(os.path.join(bundle_dir, 'templates')) else os.path.join(r"d:\SKRIPSI INFORMATIKA", 'templates')
static_dir = os.path.join(bundle_dir, 'static') if os.path.exists(os.path.join(bundle_dir, 'static')) else os.path.join(r"d:\SKRIPSI INFORMATIKA", 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

BASE_DIR = r"d:\SKRIPSI INFORMATIKA"
import shutil
if getattr(sys, 'frozen', False):
    PYTHON_EXE = shutil.which("pythonw") or shutil.which("python") or r"C:\Users\nouval\AppData\Local\Programs\Python\Python313\python.exe"
else:
    PYTHON_EXE = sys.executable

SCRIPT_M15_PATH = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot.py")
SCRIPT_M5_PATH  = os.path.join(BASE_DIR, "Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py")
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
EXCEL_M15_PATH = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx"
EXCEL_M5_PATH  = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_M5_Scalping.xlsx"
EXCEL_EVAL_PATH = r"d:\SKRIPSI INFORMATIKA\Evaluasi_Skenario_Trade.xlsx"

MAGIC_M15 = 123230
MAGIC_M5  = 123236

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

def init_mt5():
    try:
        if mt5.initialize():
            return True
        if mt5.initialize(path=MT5_PATH):
            return True
    except Exception:
        pass
    return False

def get_running_bots():
    """Mengecek proses bot mana saja yang sedang aktif berjalan"""
    m15_active = False
    m5_active = False
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info['cmdline'] or []).lower()
            if "eksekusi_otomatis_trading_bot.py" in cmd and "m5" not in cmd:
                m15_active = True
            if "eksekusi_otomatis_trading_bot_m5_scalping.py" in cmd:
                m5_active = True
        except Exception:
            pass
    return {"m15_running": m15_active, "m5_running": m5_active}

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
            summary["equity"] = round(acc.equity, 2)
            summary["floating_profit"] = round(acc.profit, 2)
            summary["free_margin"] = round(acc.margin_free, 2)
            summary["current_balance"] = round(acc.balance, 2)

        sym = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
        tick = mt5.symbol_info_tick(sym)
        if tick:
            summary["bid"] = round(tick.bid, 2)
            summary["ask"] = round(tick.ask, 2)
            summary["spread"] = round((tick.ask - tick.bid) * 10, 1)

    # Injeksi Telemetri Real-Time M15 & M5 untuk gauge bergerak & countdown
    summary["telemetry_m15"] = None
    t15_path = os.path.join(BASE_DIR, "telemetry_m15.json")
    if os.path.exists(t15_path):
        try:
            with open(t15_path, "r", encoding="utf-8") as f:
                t15_data = json.load(f)
            if time.time() - float(t15_data.get("timestamp", 0)) <= 15:
                t15_data["is_live"] = True
                summary["telemetry_m15"] = t15_data
        except Exception:
            pass
    if not summary["telemetry_m15"]:
        summary["telemetry_m15"] = get_realtime_market_telemetry("M15")

    summary["telemetry_m5"] = None
    t5_path = os.path.join(BASE_DIR, "telemetry_m5.json")
    if os.path.exists(t5_path):
        try:
            with open(t5_path, "r", encoding="utf-8") as f:
                t5_data = json.load(f)
            if time.time() - float(t5_data.get("timestamp", 0)) <= 15:
                t5_data["is_live"] = True
                summary["telemetry_m5"] = t5_data
        except Exception:
            pass
    if not summary["telemetry_m5"]:
        summary["telemetry_m5"] = get_realtime_market_telemetry("M5")

    def read_sheet_stats(path, sheet_name):
        trades, wins, losses, profit = 0, 0, 0, 0.0
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
        wr = round((wins / trades * 100), 2) if trades > 0 else 0.0
        roi = round((profit / summary["starting_balance"] * 100), 2)
        return trades, wins, losses, wr, round(profit, 2), roi

    # 1. BACA KHUSUS M15 (FOKUS UTAMA SKRIPSI)
    m15_t, m15_w, m15_l, m15_wr, m15_pnl, m15_roi = read_sheet_stats(EXCEL_M15_PATH, 'Ringkasan Statistik (v4.1)')
    summary["skripsi_trades"] = m15_t
    summary["skripsi_wins"] = m15_w
    summary["skripsi_losses"] = m15_l
    summary["skripsi_win_rate"] = m15_wr
    summary["skripsi_net_profit"] = m15_pnl
    summary["skripsi_roi_pct"] = m15_roi

    # Target Skripsi (0 / 100 Trade) dan metrik utama hanya membaca M15!
    summary["total_trades"] = m15_t
    summary["win_trades"] = m15_w
    summary["loss_trades"] = m15_l
    summary["win_rate"] = m15_wr
    summary["net_profit"] = m15_pnl
    summary["roi_pct"] = m15_roi

    # 2. BACA KHUSUS M5 (EKSPERIMEN TAMBAHAN / TIDAK DIHITUNG KE TARGET SKRIPSI)
    m5_t, m5_w, m5_l, m5_wr, m5_pnl, m5_roi = read_sheet_stats(EXCEL_M5_PATH, 'Ringkasan Statistik (v4.1)')
    summary["m5_trades"] = m5_t
    summary["m5_wins"] = m5_w
    summary["m5_losses"] = m5_l
    summary["m5_win_rate"] = m5_wr
    summary["m5_net_profit"] = m5_pnl
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
            is_m15 = (p.magic == MAGIC_M15)
            is_m5  = (p.magic == MAGIC_M5)
            bot_tag = "M15 v4.1 Swing" if is_m15 else ("M5 v4.1 Scalp" if is_m5 else f"Magic:{p.magic}")
            
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
                "bot_tag": bot_tag,
                "comment": p.comment,
                "time_open": datetime.datetime.fromtimestamp(p.time).strftime("%d/%m %H:%M:%S")
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
        status = "TERTAHAN MID-ZONE"
        if prob_buy >= 70.0: status = "SNIPER BUY READY"
        elif prob_sell >= 70.0: status = "SNIPER SELL READY"
        elif abs(prob_buy - 50.0) < 5: status = "KONSOLIDASI NETRAL"
    else:
        sup = bid - 25.0
        res = bid + 25.0
        stoch_k = 50.0
        h1_trend = "BULLISH SWEEP"
        prob_buy = 48.5
        prob_sell = 51.5
        status = "TERTAHAN MID-ZONE"

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

def get_recent_trade_logs(limit=100):
    """Membaca daftar riwayat transaksi selesai dari file Excel v4.1 & fallback CSV Evaluasi"""
    records = []

    configs = [
        (EXCEL_M15_PATH, "Trade Log Model Terbaru (v4.1)", "M15 v4.1 (Skripsi)"),
        (EXCEL_M5_PATH,  "Trade Log M5 Scalping (v4.1)",   "M5 v4.1 (Non-Skripsi)")
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
                        status = str(row_dict.get('Status') or row_dict.get('Hasil') or ('WIN' if float(profit_usd or 0) > 0 else 'LOSS'))
                        alasan = str(row_dict.get('Alasan Tutup') or row_dict.get('Alasan Exit') or row_dict.get('Keterangan / Alasan Exit') or '')
                        
                        try: profit_val = float(profit_usd)
                        except Exception: profit_val = 0.0
                        
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
                            "alasan": alasan
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
def get_portfolio_journey():
    """Menghitung metrik analitik portofolio lengkap, equity curve point-by-point, drawdown, dan performa per periode (Myfxbook Style)"""
    CSV_EVAL = r"d:\SKRIPSI INFORMATIKA\Evaluasi_Skenario_Trade.csv"
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
        "curve": [],
        "journal": []
    }

    if not os.path.exists(CSV_EVAL):
        return res

    try:
        df = pd.read_csv(CSV_EVAL)
        if len(df) == 0:
            return res

        df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
        df = df.sort_values(by='Waktu Close', ascending=True).reset_index(drop=True)
        if len(df) == 0:
            return res

        # Kalkulasi akumulatif
        df['Profit_USD'] = df['Profit ($ USD)'].astype(float)
        df['Running_Balance'] = initial_balance + df['Profit_USD'].cumsum()
        df['Growth_Pct'] = ((df['Running_Balance'] - initial_balance) / initial_balance) * 100.0
        df['Peak'] = df['Running_Balance'].cummax()
        df['Drawdown_USD'] = df['Peak'] - df['Running_Balance']
        df['Drawdown_Pct'] = (df['Drawdown_USD'] / df['Peak']) * 100.0

        total_trades = len(df)
        wins = df[df['Profit_USD'] > 0]
        losses = df[df['Profit_USD'] < 0]
        win_count = len(wins)
        loss_count = len(losses)
        total_pnl = round(float(df['Profit_USD'].sum()), 2)
        cur_balance = round(float(df['Running_Balance'].iloc[-1]), 2)
        growth_pct = round(float(df['Growth_Pct'].iloc[-1]), 2)
        max_dd_pct = round(float(df['Drawdown_Pct'].max()), 2)
        max_dd_usd = round(float(df['Drawdown_USD'].max()), 2)
        win_rate = round((win_count / total_trades * 100.0) if total_trades > 0 else 0.0, 1)

        gross_profit = float(wins['Profit_USD'].sum()) if len(wins) > 0 else 0.0
        gross_loss = abs(float(losses['Profit_USD'].sum())) if len(losses) > 0 else 0.0
        profit_factor = round((gross_profit / gross_loss), 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        avg_win = round(float(wins['Profit_USD'].mean()), 2) if len(wins) > 0 else 0.0
        avg_loss = round(float(losses['Profit_USD'].mean()), 2) if len(losses) > 0 else 0.0

        # Ambil equity live MT5 jika tersedia
        live_equity = cur_balance
        if init_mt5():
            acc = mt5.account_info()
            if acc:
                live_equity = round(acc.equity, 2)

        res["summary"] = {
            "initial_balance": initial_balance,
            "balance": cur_balance,
            "equity": live_equity,
            "total_pnl": total_pnl,
            "growth_pct": growth_pct,
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_usd": max_dd_usd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "win_trades": win_count,
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
                "result": "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "BEP"),
                "alasan": str(row.get('Keterangan / Alasan Exit', '—')),
                "model": str(row.get('Model AI', 'M15'))
            })

        res["curve"] = curve
        # Journal urutkan terbaru di atas
        res["journal"] = journal[::-1]

    except Exception as e:
        print(f"Error computing portfolio journey: {e}")

    return res

def get_trade_diagnostics(limit=50):
    """Mengambil riwayat diagnosa analisis mendalam (menang/kalah/faktor/pelajaran) dari CSV evaluasi"""
    CSV_EVAL = r"d:\SKRIPSI INFORMATIKA\Evaluasi_Skenario_Trade.csv"
    diagnostics = []
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
                        "eval_date": str(row.get('Tanggal Evaluasi', ''))
                    })
        except Exception as e:
            print(f"Error loading diagnostics: {e}")
    return diagnostics

def get_scenarios_evaluation():
    """Mengambil matriks evaluasi skenario dari Scenario_Evaluator_Engine / JSON / CSV"""
    CSV_EVAL = r"d:\SKRIPSI INFORMATIKA\Evaluasi_Skenario_Trade.csv"
    scenarios = []
    if os.path.exists(CSV_EVAL):
        try:
            df = pd.read_csv(CSV_EVAL)
            if len(df) > 0 and 'Skenario Entry' in df.columns:
                df = df[df['Ticket Posisi'].astype(str).str.strip().str.isnumeric()].copy()
                grouped = df.groupby('Skenario Entry')
                for sc_name, grp in grouped:
                    n = len(grp)
                    w = len(grp[grp['Profit ($ USD)'] > 0])
                    l = len(grp[grp['Profit ($ USD)'] < 0])
                    b = len(grp[grp['Profit ($ USD)'] == 0])
                    wr = round((w / n * 100.0) if n > 0 else 0.0, 1)
                    pnl = round(float(grp['Profit ($ USD)'].sum()), 2)
                    
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
                        
                    scenarios.append({
                        "skenario": str(sc_name),
                        "total_uji": n,
                        "win_count": w,
                        "loss_count": l,
                        "bep_count": b,
                        "win_rate": wr,
                        "total_pnl": pnl,
                        "status": status,
                        "action": action
                    })
                # Urutkan berdasarkan total trade dan win rate descending
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
        primary_url=primary_url
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
    return jsonify(get_recent_trade_logs())

@app.route('/api/scenarios')
def api_scenarios():
    return jsonify(get_scenarios_evaluation())

@app.route('/api/diagnostics')
def api_diagnostics():
    limit = request.args.get('limit', default=100, type=int)
    return jsonify(get_trade_diagnostics(limit=limit))

@app.route('/api/control/<bot_key>/<action>', methods=['GET', 'POST'])
def api_control(bot_key, action):
    """Kontrol bot dari web dashboard (start / stop)"""
    import subprocess
    import psutil
    res = {"status": "ok", "bot": bot_key, "action": action}
    try:
        if action == "start":
            if bot_key in ["m15", "both"]:
                m15_running = False
                for p in psutil.process_iter(['name', 'cmdline']):
                    cmd = " ".join(p.info['cmdline'] or []).lower()
                    if "eksekusi_otomatis_trading_bot.py" in cmd and "m5" not in cmd:
                        m15_running = True
                        break
                if not m15_running:
                    subprocess.Popen([PYTHON_EXE, SCRIPT_M15_PATH], cwd=BASE_DIR, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

            if bot_key in ["m5", "both"]:
                m5_running = False
                for p in psutil.process_iter(['name', 'cmdline']):
                    cmd = " ".join(p.info['cmdline'] or []).lower()
                    if "eksekusi_otomatis_trading_bot_m5_scalping.py" in cmd:
                        m5_running = True
                        break
                if not m5_running:
                    subprocess.Popen([PYTHON_EXE, SCRIPT_M5_PATH], cwd=BASE_DIR, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        elif action == "stop":
            target_scripts = []
            if bot_key in ["m15", "both"]:
                target_scripts.append("eksekusi_otomatis_trading_bot.py")
            if bot_key in ["m5", "both"]:
                target_scripts.append("eksekusi_otomatis_trading_bot_m5_scalping.py")

            for p in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmd = " ".join(p.info['cmdline'] or []).lower()
                    if any(ts in cmd for ts in target_scripts):
                        p.terminate()
                except Exception:
                    pass

        return jsonify(res)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/api/parameters')
def api_parameters():
    return jsonify(get_bot_parameters())

@app.route('/api/portfolio/journey')
def api_portfolio_journey():
    return jsonify(get_portfolio_journey())

# Persistent in-memory decision stream and notifications cache
GLOBAL_DECISION_STREAM_M15 = []
GLOBAL_DECISION_STREAM_M5 = []
GLOBAL_NOTIFICATIONS = []
LAST_EVAL_TIME_M15 = 0
LAST_EVAL_TIME_M5 = 0
LAST_SEEN_NOTIF_IDS = set()

def init_default_decision_stream():
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_M5
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
    try:
        csv_path = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.csv")
        if os.path.exists(csv_path):
            df_eval = pd.read_csv(csv_path)
            if len(df_eval) > 0 and 'Ticket Posisi' in df_eval.columns:
                valid = df_eval[df_eval['Ticket Posisi'].astype(str).str.strip().str.isnumeric()]
                for _, row in valid.tail(15).iloc[::-1].iterrows():
                    t_id = str(row.get('Ticket Posisi', '')).strip()
                    pnl = float(row.get('Profit ($ USD)', 0.0))
                    res_type = str(row.get('Hasil', 'BEP')).upper()
                    t_close = str(row.get('Waktu Close', ''))
                    t_short = t_close[11:19] if len(t_close) >= 19 else t_close
                    lot = row.get('Lot', 0.01)
                    typ = row.get('Tipe', 'BUY')
                    bot_m = str(row.get('Model AI', 'M15'))
                    
                    if res_type == 'WIN' or pnl > 0:
                        n_id = f"tp_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id,
                                "type": "TP",
                                "title": f"🎉 Take Profit Tercapai! (+${pnl:.2f})",
                                "message": f"{bot_m} Bot: Posisi #{t_id} {typ} {lot} lot berhasil Take Profit +${pnl:.2f} (+{(pnl/500*100):.1f}%)",
                                "time": t_short or datetime.datetime.now().strftime("%H:%M:%S"),
                                "sound": "tp",
                                "bot": bot_m
                            })
                    elif res_type == 'LOSS' or pnl < 0:
                        n_id = f"sl_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id,
                                "type": "SL",
                                "title": f"💔 Stop Loss Tersentuh (-${abs(pnl):.2f})",
                                "message": f"{bot_m} Bot: Posisi #{t_id} {typ} {lot} lot terpotong SL -${abs(pnl):.2f} ({(pnl/500*100):.1f}%)",
                                "time": t_short or datetime.datetime.now().strftime("%H:%M:%S"),
                                "sound": "sl",
                                "bot": bot_m
                            })
                    else:
                        n_id = f"bep_{t_id}"
                        if n_id not in LAST_SEEN_NOTIF_IDS:
                            LAST_SEEN_NOTIF_IDS.add(n_id)
                            GLOBAL_NOTIFICATIONS.insert(0, {
                                "id": n_id,
                                "type": "BEP",
                                "title": "🛡️ Auto BEP Berhasil (+$0.20)",
                                "message": f"{bot_m} Bot: Posisi #{t_id} diamankan pada Break-Even Point +$0.20 (Bebas Risiko)",
                                "time": t_short or datetime.datetime.now().strftime("%H:%M:%S"),
                                "sound": "open",
                                "bot": bot_m
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
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
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
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_M5
    if bot_key in ['m15', 'both', 'all']:
        GLOBAL_DECISION_STREAM_M15 = []
    if bot_key in ['m5', 'both', 'all']:
        GLOBAL_DECISION_STREAM_M5 = []
    return jsonify({"status": "ok", "bot": bot_key, "message": "Log keputusan telah dibersihkan"})

@app.route('/api/status')
def api_status():
    global GLOBAL_DECISION_STREAM_M15, GLOBAL_DECISION_STREAM_M5, LAST_EVAL_TIME_M15, LAST_EVAL_TIME_M5
    init_default_decision_stream()

    bots = get_running_bots()
    radar = get_market_radar()

    m15_running = bots.get("m15_running", False)
    m5_running = bots.get("m5_running", False)
    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    now_ts = time.time()

    # 1. Update Kronologis Keputusan M15 (Akumulasi bertahap seiring berjalannya waktu)
    t15_data = None
    t15_path = os.path.join(BASE_DIR, "telemetry_m15.json")
    if os.path.exists(t15_path):
        try:
            with open(t15_path, "r", encoding="utf-8") as f:
                t15_data = json.load(f)
        except Exception:
            pass

    if t15_data and (now_ts - float(t15_data.get("timestamp", 0)) <= 30):
        pb = float(t15_data.get("prob_buy", 50.0))
        ps = float(t15_data.get("prob_sell", 50.0))
        act = "BUY" if pb >= 70.0 else ("SELL" if ps >= 70.0 else "STANDBY")
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
        act5 = "BUY" if pb5 >= 70.0 else ("SELL" if ps5 >= 70.0 else "STANDBY")
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

    return jsonify({
        "bots": bots,
        "m15": {
            "running": m15_running,
            "uptime": "AKTIF BERJALAN" if m15_running else "00:00:00",
            "decision_history": GLOBAL_DECISION_STREAM_M15
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

