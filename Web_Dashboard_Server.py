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

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

app = Flask(__name__, template_folder='templates', static_folder='static')

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
    if not mt5.initialize(path=MT5_PATH):
        return False
    return True

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
    """Mengambil metrik ringkasan performa v3.7 dari MT5 & Excel"""
    summary = {
        "starting_balance": 500.00,
        "current_balance": 500.00,
        "equity": 500.00,
        "floating_profit": 0.00,
        "free_margin": 500.00,
        "total_trades": 0,
        "win_trades": 0,
        "loss_trades": 0,
        "win_rate": 0.0,
        "net_profit": 0.0,
        "roi_pct": 0.0,
        "last_updated": datetime.datetime.now().strftime("%H:%M:%S WIB")
    }

    # Ambil data real-time MT5 jika terhubung
    if init_mt5():
        acc = mt5.account_info()
        if acc:
            summary["equity"] = round(acc.equity, 2)
            summary["floating_profit"] = round(acc.profit, 2)
            summary["free_margin"] = round(acc.margin_free, 2)

    # Ambil akumulasi trade log v3.7 dari kedua Excel
    tot_trades = 0
    tot_wins = 0
    tot_losses = 0
    net_profit = 0.0

    for path, sheet_name in [(EXCEL_M15_PATH, 'Ringkasan Statistik (v3.7)'), 
                             (EXCEL_M5_PATH, 'Ringkasan Statistik (v3.7)')]:
        if os.path.exists(path):
            try:
                wb = openpyxl.load_workbook(path, data_only=True)
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    for r in range(1, ws.max_row + 1):
                        lbl = str(ws.cell(r, 1).value or '')
                        val = ws.cell(r, 2).value
                        if "Total Trade Otomatis Selesai" in lbl and val:
                            try: tot_trades += int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Jumlah Trade WIN" in lbl and val:
                            try: tot_wins += int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Jumlah Trade LOSS" in lbl and val:
                            try: tot_losses += int(str(val).replace('Trade', '').strip())
                            except Exception: pass
                        elif "Total Akumulasi Profit" in lbl and val:
                            try: 
                                s_val = str(val).replace('$', '').replace('USD', '').replace('+', '').strip()
                                net_profit += float(s_val)
                            except Exception: pass
            except Exception as e:
                print(f"Error reading {path}: {e}")

    summary["total_trades"] = tot_trades
    summary["win_trades"] = tot_wins
    summary["loss_trades"] = tot_losses
    summary["win_rate"] = round((tot_wins / tot_trades * 100), 2) if tot_trades > 0 else 0.0
    summary["net_profit"] = round(net_profit, 2)
    summary["current_balance"] = round(summary["starting_balance"] + net_profit, 2)
    summary["roi_pct"] = round((net_profit / summary["starting_balance"] * 100), 2)

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
            bot_tag = "M15 v3.7 Swing" if is_m15 else ("M5 v3.7 Scalp" if is_m5 else f"Magic:{p.magic}")
            
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

def get_recent_trade_logs(limit=50):
    """Membaca daftar riwayat transaksi selesai dari file Excel v3.7"""
    records = []

    configs = [
        (EXCEL_M15_PATH, "Trade Log Model Terbaru (v3.7)", "M15 v3.7"),
        (EXCEL_M5_PATH,  "Trade Log M5 Scalping (v3.7)",   "M5 v3.7")
    ]

    for path, sheet_name, model_tag in configs:
        if os.path.exists(path):
            try:
                wb = openpyxl.load_workbook(path, data_only=True)
                if sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
                    
                    for r in range(2, ws.max_row + 1):
                        row_vals = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
                        if not any(row_vals):
                            continue
                        row_dict = dict(zip(headers, row_vals))
                        
                        # Standarisasi field
                        ticket = row_dict.get('Order Ticket') or row_dict.get('Ticket') or str(r)
                        time_in = str(row_dict.get('Waktu Entry') or row_dict.get('Waktu Masuk') or '')
                        time_out = str(row_dict.get('Waktu Selesai') or row_dict.get('Waktu Tutup') or '')
                        t_type = str(row_dict.get('Posisi') or row_dict.get('Tipe') or 'BUY').upper()
                        lot = row_dict.get('Lot') or 0.01
                        open_p = row_dict.get('Harga Entry') or 0.0
                        close_p = row_dict.get('Harga Exit') or row_dict.get('Harga Keluar') or 0.0
                        profit_usd = row_dict.get('Profit ($ USD)') or row_dict.get('Profit ($)') or 0.0
                        status = str(row_dict.get('Status') or ('WIN' if profit_usd > 0 else 'LOSS'))
                        alasan = str(row_dict.get('Alasan Tutup') or row_dict.get('Alasan Exit') or '')
                        
                        try: profit_val = float(profit_usd)
                        except Exception: profit_val = 0.0
                        
                        records.append({
                            "ticket": str(ticket),
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

    # Urutkan berdasarkan waktu keluar descending (paling baru di atas)
    records.sort(key=lambda x: x['time_out'], reverse=True)
    return records[:limit]

def get_scenarios_evaluation():
    """Mengambil matriks evaluasi skenario dari Evaluasi_Skenario_Trade.xlsx"""
    scenarios = []
    if os.path.exists(EXCEL_EVAL_PATH):
        try:
            wb = openpyxl.load_workbook(EXCEL_EVAL_PATH, data_only=True)
            if 'Matriks Evaluasi Skenario' in wb.sheetnames:
                ws = wb['Matriks Evaluasi Skenario']
                headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
                for r in range(2, ws.max_row + 1):
                    vals = [ws.cell(r, col).value for col in range(1, ws.max_column + 1)]
                    if not any(vals): continue
                    row_dict = dict(zip(headers, vals))
                    scenarios.append({
                        "skenario": str(row_dict.get('Skenario_Kunci') or ''),
                        "total_uji": row_dict.get('Total_Uji') or 0,
                        "win_count": row_dict.get('Win_Count') or 0,
                        "loss_count": row_dict.get('Loss_Count') or 0,
                        "win_rate": row_dict.get('Win_Rate_Pct') or 0.0,
                        "status": str(row_dict.get('Status_Skenario') or 'PENGUJIAN')
                    })
        except Exception as e:
            print(f"Error reading scenario evaluation: {e}")
    return scenarios

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

@app.route('/api/status')
def api_status():
    bots = get_running_bots()
    radar = get_market_radar()
    return jsonify({
        "bots": bots,
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

