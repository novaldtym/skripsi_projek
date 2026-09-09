import os
import sys
import time
import joblib
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import MetaTrader5 as mt5

from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel

os.system('') # Aktifkan ANSI escape Virtual Terminal di Windows CMD
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# =========================================================================
# 🎨 KODE WARNA TERMINAL ANSI (Kuning=Netral, Hijau=Buy, Merah=Sell)
# =========================================================================
COLOR_YELLOW = "\033[93m"  # Kuning untuk Sinyal Netral / WAIT
COLOR_GREEN  = "\033[92m"  # Hijau untuk Open Posisi BUY
COLOR_RED    = "\033[91m"  # Merah untuk Open Posisi SELL
COLOR_CYAN   = "\033[96m"  # Cyan untuk Notifikasi Info
COLOR_RESET  = "\033[0m"
COLOR_BOLD   = "\033[1m"

# =========================================================================
# ⚙️ PENGATURAN ROBOT TRADING M5 FULL DYNAMIC SCALPER (AI MANAGED EXIT)
# =========================================================================
CHOSEN_TF              = "M5"        # Timeframe Utama: M5 (5 Menit)
FORWARD_CANDLES        = 5           # Horizon Prediksi: 5 Candle (25 menit)
LOT_SIZE               = 0.01        # Lot Size Eksekusi
PROB_THRESHOLD         = 58.0        # Ambang Batas Standar (Naik dari 55% ke 58% untuk membuang noise)
PULLBACK_THRESHOLD     = 70.0        # Ambang Khusus Pullback Counter-Trend (Sinyal Sangat Kuat >= 70%)
MAGIC_NUMBER           = 123235      # Magic ID Unik M5
MAX_STACKED_POSITIONS  = 3           # Batas Maksimal Layer Posisi
AUTO_EXECUTE           = True        # Eksekusi Otomatis ke MT5

# --- TARGET DYNAMIC REAL-TIME EXIT (BOT-MANAGED) ---
QUICK_TP_USD           = 1.50        # Target Profit Cepat Scalping (+ $1.50 USD per posisi)
TRAILING_TRIGGER_USD   = 1.00        # Aktifkan Trailing Lock saat profit mencapai >= +$1.00 USD
TRAILING_LOCK_USD      = 0.60        # Kunci profit minimal +$0.60 USD jika harga berbalik retrace
EMERGENCY_SL_USD       = 4.00        # Hard SL Pengaman Darurat di Broker (Jaring pengaman jika internet mati)

MT5_PATH               = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH        = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd_m5.pkl"
EXCEL_M5_PATH          = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_M5_Scalping.xlsx"
ORDER_COMMENT          = "LightGBM M5 Scalping"

print("="*85)
print("⚡ ROBOT TRADING M5 FULL DYNAMIC SCALPER (AI REAL-TIME EXIT & M30 MTF)")
print("Fitur: Target Quick TP $1.50 | Smart AI Cut-Loss | Filter M30 | Magic: 123235")
print(f"Log Excel: {EXCEL_M5_PATH}")
print("="*85)

if not os.path.exists(MT5_PATH):
    print("❌ MT5 Path tidak ditemukan! Pastikan Exness MT5 terinstall.")
    sys.exit(1)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke Exness MT5!")
    sys.exit(1)

print("✅ Terhubung ke Exness MT5 secara otomatis!")

if not os.path.exists(MODEL_FILE_PATH):
    print(f"❌ Model PKL M5 tidak ditemukan di {MODEL_FILE_PATH}!")
    sys.exit(1)

model = joblib.load(MODEL_FILE_PATH)
print(f"✅ Master Model LightGBM M5 ({MODEL_FILE_PATH}) Berhasil Dimuat.")

def get_symbol_name():
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)
    return symbol

symbol = get_symbol_name()

def get_best_filling_mode(sym):
    s_info = mt5.symbol_info(sym)
    if s_info is None:
        return mt5.ORDER_FILLING_FOK
    flags = s_info.filling_mode
    if flags & 1:
        return mt5.ORDER_FILLING_FOK
    elif flags & 2:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def close_position_market(pos, comment_reason="Bot Scalp Close"):
    """Menutup posisi langsung di pasar (Market Close) dengan respon 0-delay"""
    tick = mt5.symbol_info_tick(pos.symbol)
    if tick is None:
        return False
        
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
    filling_mode = get_best_filling_mode(pos.symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "price": price,
        "deviation": 25,
        "magic": MAGIC_NUMBER,
        "comment": comment_reason,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    res = mt5.order_send(request)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        profit_final = (price - pos.price_open) * pos.volume * 100.0 if pos.type == 0 else (pos.price_open - price) * pos.volume * 100.0
        color_res = COLOR_GREEN if profit_final > 0 else COLOR_RED
        print(f"{color_res}{COLOR_BOLD}🎯 DYNAMIC EXIT SUKSES (#{pos.ticket}): {comment_reason} | Hasil: ${profit_final:+.2f} USD @ ${price:.2f}{COLOR_RESET}")
        try:
            sync_mt5_trades_to_excel(
                excel_path=EXCEL_M5_PATH,
                filter_new_model_only=True,
                magic_number=MAGIC_NUMBER,
                comment_filter=None,
                model_label="LightGBM M5 Dynamic Scalper",
                sheet_title="Trade Log M5 Scalping",
                threshold_label=">= 58.0% + Dynamic AI Exit ($1.50 TP / AI Cut-Loss)"
            )
        except Exception:
            pass
        return True
    else:
        print(f"⚠️ Gagal Market Close #{pos.ticket}. Code: {res.retcode} ({res.comment})")
        return False

# Pelacak Puncak Profit per Tiket untuk Trailing Lock
peak_profits = {}

def manage_open_positions(latest_prob_up=50.0, latest_prob_down=50.0):
    """
    Pemantauan Real-Time Setiap Detik:
    1. Quick Scalp TP (Amankan profit saat floating >= +$1.50 USD)
    2. Trailing Profit Lock (Jika sempat >= $1.00 lalu retrace ke $0.60, kunci untung)
    3. Smart AI Cut-Loss (Tutup dini jika prediksi candle M5 berbalik arah >= 58%)
    """
    all_positions = mt5.positions_get(symbol=symbol)
    if not all_positions:
        peak_profits.clear()
        return

    my_positions = [p for p in all_positions if p.magic == MAGIC_NUMBER]
    if not my_positions:
        peak_profits.clear()
        return

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return

    for pos in my_positions:
        pos_type = pos.type # 0 = BUY, 1 = SELL
        current_p = tick.bid if pos_type == mt5.ORDER_TYPE_BUY else tick.ask
        
        if pos_type == mt5.ORDER_TYPE_BUY:
            profit_usd = (current_p - pos.price_open) * pos.volume * 100.0
        else:
            profit_usd = (pos.price_open - current_p) * pos.volume * 100.0

        # Update peak profit
        if pos.ticket not in peak_profits:
            peak_profits[pos.ticket] = profit_usd
        else:
            if profit_usd > peak_profits[pos.ticket]:
                peak_profits[pos.ticket] = profit_usd

        # 1. KONDISI A: Quick Scalp TP Tercapai (>= +$1.50 USD)
        if profit_usd >= QUICK_TP_USD:
            if close_position_market(pos, f"Scalp TP (+${profit_usd:.2f})"):
                peak_profits.pop(pos.ticket, None)
                continue

        # 2. KONDISI B: Trailing Profit Lock (Pernah >= $1.00, kini retrace turun <= $0.60)
        if peak_profits.get(pos.ticket, 0.0) >= TRAILING_TRIGGER_USD and profit_usd <= TRAILING_LOCK_USD:
            if close_position_market(pos, f"Trailing Lock (+${profit_usd:.2f})"):
                peak_profits.pop(pos.ticket, None)
                continue

        # 3. KONDISI C: Smart AI Early Cut-Loss (Sinyal Model M5 Berbalik Arah)
        if pos_type == mt5.ORDER_TYPE_BUY and latest_prob_down >= PROB_THRESHOLD:
            if close_position_market(pos, f"AI Cut-Loss (Reversal SELL {latest_prob_down:.1f}%)"):
                peak_profits.pop(pos.ticket, None)
                continue
        elif pos_type == mt5.ORDER_TYPE_SELL and latest_prob_up >= PROB_THRESHOLD:
            if close_position_market(pos, f"AI Cut-Loss (Reversal BUY {latest_prob_up:.1f}%)"):
                peak_profits.pop(pos.ticket, None)
                continue

def analyze_market_and_predict():
    rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
    rates_m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 500)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
    
    if rates_m5 is None or len(rates_m5) == 0 or rates_m30 is None or len(rates_m30) == 0 or rates_h1 is None or len(rates_h1) == 0:
        print("\n⚠️ Koneksi data MT5 terputus sesaat. Mencoba Re-initialize MT5...")
        mt5.initialize(path=MT5_PATH)
        rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
        rates_m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 500)
        rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
        if rates_m5 is None or len(rates_m5) == 0:
            print("❌ Gagal menarik data M5 dari MT5. Melewati candle ini...")
            return 50.0, 50.0, False, False, 5.0, 0.0, 0.0

    df_m5 = pd.DataFrame(rates_m5)
    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
    df_m5.set_index('time', inplace=True)

    df_m30 = pd.DataFrame(rates_m30)
    df_m30['time'] = pd.to_datetime(df_m30['time'], unit='s')
    df_m30.set_index('time', inplace=True)
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_h1.set_index('time', inplace=True)

    # Tren M30 (Responsif)
    df_m30['EMA_50_M30'] = df_m30['close'].ewm(span=50, adjust=False).mean()
    m30_bull = df_m30['close'].iloc[-1] > df_m30['EMA_50_M30'].iloc[-1]

    # Tren H1 (Makro)
    df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
    df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
    df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
    df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)

    df_m5['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m5.index, method='ffill').fillna(0)
    df_m5['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m5.index, method='ffill').fillna(0)

    # DXY 0-Delay dari MT5
    mt5.symbol_select('DXY', True)
    rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M5, 0, 1000)
    if rates_dxy is not None and len(rates_dxy) > 0:
        df_dxy = pd.DataFrame(rates_dxy)
        df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
        df_dxy.set_index('time', inplace=True)
        dxy_close = df_dxy['close']
    else:
        dxy_df = yf.download("DX-Y.NYB", period="10d", interval="5m", progress=False)
        dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
        if dxy_close.index.tz is not None:
            dxy_close.index = dxy_close.index.tz_localize(None)

    range_m5 = (df_m5['high'] - df_m5['low']) + 1e-6
    df_m5['Body_M15'] = (df_m5['close'] - df_m5['open']).abs() / range_m5
    df_m5['Lower_Wick_M15'] = (df_m5[['open', 'close']].min(axis=1) - df_m5['low']) / range_m5
    df_m5['Upper_Wick_M15'] = (df_m5['high'] - df_m5[['open', 'close']].max(axis=1)) / range_m5

    df_m5['FVG_Bull'] = (df_m5['low'] > df_m5['high'].shift(2)).astype(int)
    df_m5['FVG_Bear'] = (df_m5['high'] < df_m5['low'].shift(2)).astype(int)

    df_m5['Swing_High_20'] = df_m5['high'].shift(1).rolling(20).max()
    df_m5['Swing_Low_20']  = df_m5['low'].shift(1).rolling(20).min()
    df_m5['Dist_Support']    = (df_m5['close'] - df_m5['Swing_Low_20']) / df_m5['close']
    df_m5['Dist_Resistance'] = (df_m5['Swing_High_20'] - df_m5['close']) / df_m5['close']

    df_m5['BOS_Bull']  = (df_m5['close'] > df_m5['Swing_High_20']).astype(int)
    df_m5['BOS_Bear']  = (df_m5['close'] < df_m5['Swing_Low_20']).astype(int)

    trend_slow = df_m5['close'].pct_change(20)
    df_m5['CHoCH_Bull'] = ((df_m5['close'] > df_m5['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df_m5['CHoCH_Bear'] = ((df_m5['close'] < df_m5['Swing_Low_20']) & (trend_slow > 0)).astype(int)

    df_m5['Liquidity_Sweep_High'] = ((df_m5['high'] > df_m5['Swing_High_20']) & (df_m5['close'] < df_m5['Swing_High_20'])).astype(int)
    df_m5['Liquidity_Sweep_Low']  = ((df_m5['low'] < df_m5['Swing_Low_20']) & (df_m5['close'] > df_m5['Swing_Low_20'])).astype(int)

    is_bear_candle = df_m5['close'] < df_m5['open']
    impulse_up = (df_m5['close'].shift(-2) - df_m5['close']) > (1.5 * (df_m5['high'] - df_m5['low']))
    df_m5['Order_Block_Bull'] = (is_bear_candle & impulse_up).astype(int)

    lookback_fibo = 100
    roll_high = df_m5['high'].rolling(lookback_fibo).max()
    roll_low  = df_m5['low'].rolling(lookback_fibo).min()
    roll_range = (roll_high - roll_low) + 1e-6

    df_m5['Fibo_Pos_100'] = (df_m5['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)

    df_m5['Fibo_Dist_382'] = (df_m5['close'] - fibo_382) / df_m5['close']
    df_m5['Fibo_Dist_500'] = (df_m5['close'] - fibo_500) / df_m5['close']
    df_m5['Fibo_Dist_618'] = (df_m5['close'] - fibo_618) / df_m5['close']

    delta5 = df_m5['close'].diff()
    gain5 = (delta5.where(delta5 > 0, 0)).rolling(14).mean()
    loss5 = (-delta5.where(delta5 < 0, 0)).rolling(14).mean()
    df_m5['RSI_M15'] = 100 - (100 / (1 + (gain5 / (loss5 + 1e-6))))

    df_m5['SMA_20_M15'] = df_m5['close'].rolling(20).mean()
    df_m5['STD_20_M15'] = df_m5['close'].rolling(20).std()
    df_m5['BB_Bandwidth'] = (4 * df_m5['STD_20_M15']) / df_m5['SMA_20_M15']
    df_m5['BB_Pos'] = (df_m5['close'] - (df_m5['SMA_20_M15'] - 2*df_m5['STD_20_M15'])) / (4*df_m5['STD_20_M15'] + 1e-6)

    df_m5['XAU_Return_1'] = df_m5['close'].pct_change(1)
    df_m5['XAU_Return_3'] = df_m5['close'].pct_change(3)
    df_m5['XAU_Return_5'] = df_m5['close'].pct_change(5)

    df_m5['DXY_Close'] = dxy_close.reindex(df_m5.index, method='ffill').bfill()
    df_m5['DXY_Return_1'] = df_m5['DXY_Close'].pct_change(1).fillna(0)
    df_m5['DXY_Return_3'] = df_m5['DXY_Close'].pct_change(3).fillna(0)

    tr1 = df_m5['high'] - df_m5['low']
    tr2 = (df_m5['high'] - df_m5['close'].shift(1)).abs()
    tr3 = (df_m5['low'] - df_m5['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df_m5['ATR_14'] = tr.rolling(14).mean()

    features = [
        'Body_M15', 'Lower_Wick_M15', 'Upper_Wick_M15', 
        'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
        'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
        'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull',
        'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
        'RSI_M15', 'BB_Bandwidth', 'BB_Pos',
        'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
        'DXY_Return_1', 'DXY_Return_3',
        'Trend_H1_Bull', 'Trend_H1_Strong'
    ]

    df_clean = df_m5.dropna().copy()
    if len(df_clean) == 0:
        return 50.0, 50.0, False, False, 5.0, 0.0, 0.0

    latest_row = df_clean[features].iloc[[-1]].astype(float)
    probs = model.predict_proba(latest_row)[0]
    prob_down = probs[0] * 100.0
    prob_up   = probs[1] * 100.0

    latest_atr = df_clean['ATR_14'].iloc[-1]
    if pd.isna(latest_atr) or latest_atr <= 0:
        latest_atr = 5.0

    h1_bull = df_clean['Trend_H1_Bull'].iloc[-1] == 1
    
    tick = mt5.symbol_info_tick(symbol)
    live_ask = tick.ask if tick else df_clean['close'].iloc[-1]
    live_bid = tick.bid if tick else df_clean['close'].iloc[-1]
    
    return prob_up, prob_down, m30_bull, h1_bull, latest_atr, live_ask, live_bid

def execute_auto_trade(signal_type, entry_price):
    all_positions = mt5.positions_get(symbol=symbol)
    my_positions = [p for p in (all_positions or []) if p.magic == MAGIC_NUMBER]
    
    # 1. Cek batas maksimal layer stacking
    if len(my_positions) >= MAX_STACKED_POSITIONS:
        print(f"⚠️ Batas Stacking M5 Tercapai ({len(my_positions)}/{MAX_STACKED_POSITIONS} Posisi Aktif). Menunggu TP/Exit.")
        return
        
    # 2. Anti-Hedging: Jangan buka posisi berlawanan
    for pos in my_positions:
        pos_dir = "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
        if pos_dir != signal_type:
            print(f"⚠️ Sinyal M5 ({signal_type}) berlawanan dengan posisi floating #{pos.ticket} ({pos_dir}). Melewati eksekusi.")
            return

    # 3. Safe Pyramiding: Stacking HANYA jika posisi sebelumnya sudah PROFIT!
    if len(my_positions) > 0:
        tick = mt5.symbol_info_tick(symbol)
        pos_recent = my_positions[-1]
        cur_price = tick.bid if pos_recent.type == 0 else tick.ask
        pnl_recent = (cur_price - pos_recent.price_open) * pos_recent.volume * 100.0 if pos_recent.type == 0 else (pos_recent.price_open - cur_price) * pos_recent.volume * 100.0
        if pnl_recent <= 0.20:
            print(f"⚠️ STACKING DITAHAN: Posisi sebelumnya (#{pos_recent.ticket}) belum profit (Floating: ${pnl_recent:+.2f}). Dilarang Averaging Down!")
            return

    layer_num = len(my_positions) + 1
    if layer_num > 1:
        print(f"🔥 SAFE STACKING LAYER #{layer_num} ({signal_type}): Menambah layer posisi saat posisi lama sudah profit!")

    order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if signal_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    # Emergency Disaster Stop Loss (-$4.00 USD / 40 pips di broker)
    emergency_dist = EMERGENCY_SL_USD / (LOT_SIZE * 100.0)
    sl = price - emergency_dist if signal_type == "BUY" else price + emergency_dist
    tp = price + 15.0 if signal_type == "BUY" else price - 15.0 # TP broker diset jauh (150 pips) karena bot yang kelola TP $1.50
        
    filling_mode = get_best_filling_mode(symbol)
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": ORDER_COMMENT,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    color_order = COLOR_GREEN if signal_type == "BUY" else COLOR_RED
    print(f"{color_order}{COLOR_BOLD}🚀 [OPEN {signal_type}] MENGIRIM ORDER SCALPING M5: {signal_type} {LOT_SIZE} Lot XAUUSD @ ${price:.2f} (Emergency SL: ${sl:.2f}, Target Bot TP: +${QUICK_TP_USD:.2f}){COLOR_RESET}")
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{color_order}{COLOR_BOLD}🎉 ORDER M5 SCALPING {signal_type} BERHASIL DIEKSEKUSI! (Layer {layer_num}/{MAX_STACKED_POSITIONS}){COLOR_RESET}")
    else:
        print(f"❌ Gagal Eksekusi Order M5. Retcode: {result.retcode} ({result.comment})")

def main():
    print("\n" + "="*85)
    print("🤖 ROBOT TRADING M5 DYNAMIC SCALPER BERJALAN OTOMATIS (AI REAL-TIME EXIT)")
    print("Target TP: +$1.50 USD | Smart AI Cut-Loss | Filter M30 | Emergency SL: -$4.00")
    print("Tekan Ctrl+C untuk menghentikan Robot.")
    print("="*85)

    # Sinkronisasi awal saat bot pertama kali dinyalakan
    print(f"{COLOR_CYAN}🔄 Memeriksa & menyinkronkan seluruh riwayat trade M5 ke Excel...{COLOR_RESET}")
    try:
        sync_mt5_trades_to_excel(
            excel_path=EXCEL_M5_PATH,
            filter_new_model_only=True,
            magic_number=MAGIC_NUMBER,
            comment_filter=None,
            model_label="LightGBM M5 Dynamic Scalper",
            sheet_title="Trade Log M5 Scalping",
            threshold_label=">= 58.0% + Dynamic AI Exit ($1.50 TP / AI Cut-Loss)"
        )
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi awal Excel M5: {e}")

    tf_min = 5
    last_analyzed_candle = None
    latest_prob_up = 50.0
    latest_prob_down = 50.0
    prev_m5_count = 0
    last_periodic_sync = time.time()

    try:
        while True:
            # 1. LOOP REAL-TIME: Pantau exit dinamis setiap detik
            manage_open_positions(latest_prob_up, latest_prob_down)

            all_pos = mt5.positions_get(symbol=symbol)
            my_pos = [p for p in (all_pos or []) if p.magic == MAGIC_NUMBER]
            active_m5_count = len(my_pos)

            # Deteksi jika ada layer/posisi M5 yang baru saja tertutup
            if prev_m5_count > active_m5_count:
                print(f"\n{COLOR_CYAN}🔔 [DETEKSI EXIT M5]: Posisi tertutup terdeteksi. Menyinkronkan update ke Excel M5...{COLOR_RESET}")
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_M5_PATH,
                        filter_new_model_only=True,
                        magic_number=MAGIC_NUMBER,
                        comment_filter=None,
                        model_label="LightGBM M5 Dynamic Scalper",
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=">= 58.0% + Dynamic AI Exit ($1.50 TP / AI Cut-Loss)"
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel M5: {sync_err}")

            prev_m5_count = active_m5_count

            # Sinkronisasi berkala ke Excel setiap 60 detik (Real-time safety)
            if time.time() - last_periodic_sync >= 60:
                last_periodic_sync = time.time()
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_M5_PATH,
                        filter_new_model_only=True,
                        magic_number=MAGIC_NUMBER,
                        comment_filter=None,
                        model_label="LightGBM M5 Dynamic Scalper",
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=">= 58.0% + Dynamic AI Exit ($1.50 TP / AI Cut-Loss)"
                    )
                except Exception:
                    pass
            
            now = datetime.now()
            minutes_past = now.minute % tf_min
            seconds_past = minutes_past * 60 + now.second
            total_tf_seconds = tf_min * 60
            seconds_left = total_tf_seconds - seconds_past
            
            current_candle_time = now.replace(second=0, microsecond=0) - timedelta(minutes=minutes_past)
            
            mins = seconds_left // 60
            secs = seconds_left % 60
            
            # Hitung total floating PnL M5 saat ini
            live_pnl = sum([p.profit for p in my_pos])
            pnl_str = f" | Floating: ${live_pnl:+.2f}" if active_m5_count > 0 else ""
            
            # Status tampilan di console (Kuning untuk Netral, Hijau untuk Buy, Merah untuk Sell)
            if active_m5_count > 0:
                pos_dir = "BUY" if my_pos[0].type == 0 else "SELL"
                if pos_dir == "BUY":
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}ACTIVE BUY ({active_m5_count}/{MAX_STACKED_POSITIONS}){COLOR_RESET}{pnl_str}"
                else:
                    status_str = f"{COLOR_RED}{COLOR_BOLD}ACTIVE SELL ({active_m5_count}/{MAX_STACKED_POSITIONS}){COLOR_RESET}{pnl_str}"
            else:
                status_str = f"{COLOR_YELLOW}NETRAL/WAIT{COLOR_RESET}"

            sys.stdout.write(f"\r⏳ [BOT M5 DYNAMIC SCALPER]: Sisa Candle: {mins:02d}m {secs:02d}s | Status: {status_str}   ")
            sys.stdout.flush()
            
            # 2. TRIGGER CANDLE: Tepat 5 detik sebelum tutup candle M5 (0-delay)
            if seconds_left <= 5 and last_analyzed_candle != current_candle_time:
                last_analyzed_candle = current_candle_time
                print("\n" + "-"*85)
                print(f"⚡ TUTUP CANDLE M5 ({now.strftime('%H:%M:%S')})! ANALISIS MODEL M5 & FILTER ADAPTIF M30...")
                
                latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val, ask_p, bid_p = analyze_market_and_predict()
                
                print(f"📊 Probabilitas M5 : BUY={latest_prob_up:.1f}% | SELL={latest_prob_down:.1f}% (Standar: >={PROB_THRESHOLD}%, Pullback: >={PULLBACK_THRESHOLD}%)")
                print(f"🛡️ Konfirmasi Tren : M30={'BULLISH (Up)' if m30_bull else 'BEARISH (Down)'} | H1 Makro={'BULLISH' if h1_bull else 'BEARISH'}")
                
                final_signal = "WAIT"
                
                if latest_prob_up >= PROB_THRESHOLD:
                    if m30_bull:
                        final_signal = "BUY"
                        print(f"{COLOR_GREEN}{COLOR_BOLD}🟢 SINYAL BUY M5 VALID: Searah Tren M30 Bullish ({latest_prob_up:.1f}%){COLOR_RESET}")
                    elif latest_prob_up >= PULLBACK_THRESHOLD:
                        final_signal = "BUY"
                        print(f"{COLOR_GREEN}{COLOR_BOLD}⚡ SINYAL BUY M5 PULLBACK SCALP: Momentum Sangat Kuat ({latest_prob_up:.1f}% >= {PULLBACK_THRESHOLD}%) Melawan M30!{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}⚠️ FILTER M30: Sinyal BUY ({latest_prob_up:.1f}%) tertahan tren M30 Bearish (Butuh >= {PULLBACK_THRESHOLD}% untuk Pullback Scalp).{COLOR_RESET}")
                        
                elif latest_prob_down >= PROB_THRESHOLD:
                    if not m30_bull:
                        final_signal = "SELL"
                        print(f"{COLOR_RED}{COLOR_BOLD}🔴 SINYAL SELL M5 VALID: Searah Tren M30 Bearish ({latest_prob_down:.1f}%){COLOR_RESET}")
                    elif latest_prob_down >= PULLBACK_THRESHOLD:
                        final_signal = "SELL"
                        print(f"{COLOR_RED}{COLOR_BOLD}⚡ SINYAL SELL M5 PULLBACK SCALP: Momentum Sangat Kuat ({latest_prob_down:.1f}% >= {PULLBACK_THRESHOLD}%) Melawan M30!{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}⚠️ FILTER M30: Sinyal SELL ({latest_prob_down:.1f}%) tertahan tren M30 Bullish (Butuh >= {PULLBACK_THRESHOLD}% untuk Pullback Scalp).{COLOR_RESET}")
                else:
                    print(f"{COLOR_YELLOW}🟡 SINYAL NETRAL M5: Keyakinan ({max(latest_prob_up, latest_prob_down):.1f}%) < Ambang Batas {PROB_THRESHOLD}%.{COLOR_RESET}")
                    
                if final_signal in ["BUY", "SELL"]:
                    entry_p = ask_p if final_signal == "BUY" else bid_p
                    if AUTO_EXECUTE:
                        execute_auto_trade(final_signal, entry_p)
                
                # Sinkronisasi ke Excel khusus M5 Scalping
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_M5_PATH,
                        filter_new_model_only=True,
                        magic_number=MAGIC_NUMBER,
                        comment_filter=None,
                        model_label="LightGBM M5 Dynamic Scalper",
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=">= 58.0% + Dynamic AI Exit ($1.50 TP / AI Cut-Loss)"
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel M5: {sync_err}")
                print("-"*85)
                
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nRobot Trading M5 Scalping Dihentikan oleh User.")
        mt5.shutdown()

if __name__ == "__main__":
    main()
