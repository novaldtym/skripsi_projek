import os
import sys
import time
import socket
import joblib
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import MetaTrader5 as mt5

from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel

# Proteksi Single Instance: Mencegah 2 script berjalan sekaligus
try:
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _lock_socket.bind(("127.0.0.1", 41230))
except socket.error:
    print("\n❌ [SINGLE INSTANCE PROTECTION] Bot M15 sudah berjalan di proses lain!")
    print("Mencegah eksekusi ganda yang dapat menyebabkan over-trading.")
    sys.exit(0)

os.system('') # Aktifkan ANSI escape Virtual Terminal di Windows CMD
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
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
# ⚙️ PENGATURAN ROBOT TRADING OTOMATIS M15 (SMC LEVEL BOUNCE & PRECISION)
# =========================================================================
CHOSEN_TF              = "M15"      # Timeframe Utama: M15
FORWARD_CANDLES        = 5          # Horizon Prediksi: 5 Candle (75 menit)
LOT_SIZE               = 0.01       # Lot Size Eksekusi
PROB_THRESHOLD         = 60.0       # Ambang Keyakinan Minimum Model (60% untuk Sinyal Valid)
MAGIC_NUMBER           = 123230     # Magic ID Unik M15

SL_TP_MODE             = "SMART_INTRADAY"
RRR_RATIO              = 1.5        # Risk-to-Reward Ratio (1 : 1.5)
AUTO_EXECUTE           = True       # Set True untuk Eksekusi Otomatis ke MT5!

# --- SMC STRUCTURAL KEY-LEVEL & WICK REJECTION GUARDS ---
ZONE_THRESHOLD         = 0.0025     # Batas Zona Demand/Supply Struktural (~$10-11 dari Support/Resistance 10 jam)
WICK_MIN_RATIO         = 0.25       # Minimal 25% Ekor Penolakan (Rejection Wick / Pinbar)
PROXIMITY_GUARD        = True       # Anti-Sell di Lantai Demand & Anti-Buy di Atap Resistance

# --- DYNAMIC PROFIT PROTECTION & AI EXIT (M15 SWING) ---
ENABLE_BREAKEVEN       = True       # Pindahkan SL ke Break-Even (+ $0.20) jika profit >= +$4.00 USD
ENABLE_TRAILING_LOCK   = True       # Kunci profit minimal jika floating profit pernah naik tinggi
TRAILING_TRIGGER_USD   = 3.00       # Aktifkan trailing lock saat profit mencapai >= +$3.00 USD
TRAILING_LOCK_USD      = 1.50       # Kunci profit minimal +$1.50 USD jika harga berbalik retrace
ENABLE_AI_CUTLOSS      = True       # AI Early Cut-Loss jika sinyal candle M15 berbalik tajam >= 65%
AI_CUTLOSS_REV_PROB    = 65.0       # Ambang batas pembalikan arah AI untuk cut-loss dini

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"

print("="*75)
print("🤖 ROBOT TRADING OTOMATIS LIGHTGBM XAUUSD (SMC LEVEL BOUNCE & PRECISION)")
print("Fitur: Multi-Hour SNR 10J + Rejection Wick Guard + Trailing Lock + AI Cut-Loss")
print("="*75)

if not os.path.exists(MT5_PATH):
    print("❌ MT5 Path tidak ditemukan! Pastikan Exness MT5 terinstall.")
    sys.exit(1)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke Exness MT5!")
    sys.exit(1)

print("✅ Terhubung ke Exness MT5 secara otomatis!")

if not os.path.exists(MODEL_FILE_PATH):
    print("❌ Model PKL tidak ditemukan!")
    sys.exit(1)

model = joblib.load(MODEL_FILE_PATH)
print(f"✅ Master Model LightGBM SMC/ICT ({MODEL_FILE_PATH}) Berhasil Dimuat.")

def get_symbol_name():
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)
    return symbol

symbol = get_symbol_name()

def analyze_market_and_predict():
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1000)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
    
    if rates_m15 is None or len(rates_m15) == 0 or rates_h1 is None or len(rates_h1) == 0:
        print("\n⚠️ Koneksi data MT5 terputus sesaat. Mencoba Re-initialize MT5...")
        mt5.initialize(path=MT5_PATH)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1000)
        rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
        if rates_m15 is None or len(rates_m15) == 0:
            print("❌ Gagal menarik data dari MT5. Melewati candle ini...")
            return 50.0, 50.0, False, False, 8.0, 0.0, 0.0, 0.01, 0.01, 0.0, 0.0, False, False, 0.0, 0.0

    df_m15 = pd.DataFrame(rates_m15)
    df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
    df_m15.set_index('time', inplace=True)
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_h1.set_index('time', inplace=True)

    # DXY 0-Delay dari MT5
    mt5.symbol_select('DXY', True)
    rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 1000)
    if rates_dxy is not None and len(rates_dxy) > 0:
        df_dxy = pd.DataFrame(rates_dxy)
        df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
        df_dxy.set_index('time', inplace=True)
        dxy_close = df_dxy['close']
    else:
        dxy_df = yf.download("DX-Y.NYB", period="10d", interval="15m", progress=False)
        dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
        if dxy_close.index.tz is not None:
            dxy_close.index = dxy_close.index.tz_localize(None)

    range_m15 = (df_m15['high'] - df_m15['low']) + 1e-6
    df_m15['Body_M15'] = (df_m15['close'] - df_m15['open']).abs() / range_m15
    df_m15['Lower_Wick_M15'] = (df_m15[['open', 'close']].min(axis=1) - df_m15['low']) / range_m15
    df_m15['Upper_Wick_M15'] = (df_m15['high'] - df_m15[['open', 'close']].max(axis=1)) / range_m15

    # 1. FAIR VALUE GAP (FVG / IMBALANCE)
    df_m15['FVG_Bull'] = (df_m15['low'] > df_m15['high'].shift(2)).astype(int)
    df_m15['FVG_Bear'] = (df_m15['high'] < df_m15['low'].shift(2)).astype(int)

    # 2. SUPPORT & RESISTANCE (SNR SWING HIGH/LOW 20 WINDOW UNTUK 28 FITUR MODEL)
    df_m15['Swing_High_20'] = df_m15['high'].shift(1).rolling(20).max()
    df_m15['Swing_Low_20']  = df_m15['low'].shift(1).rolling(20).min()
    df_m15['Dist_Support']    = (df_m15['close'] - df_m15['Swing_Low_20']) / df_m15['close']
    df_m15['Dist_Resistance'] = (df_m15['Swing_High_20'] - df_m15['close']) / df_m15['close']

    # 3. BREAK OF STRUCTURE (BOS) & CHANGE OF CHARACTER (CHoCH)
    df_m15['BOS_Bull']  = (df_m15['close'] > df_m15['Swing_High_20']).astype(int)
    df_m15['BOS_Bear']  = (df_m15['close'] < df_m15['Swing_Low_20']).astype(int)

    trend_slow = df_m15['close'].pct_change(20)
    df_m15['CHoCH_Bull'] = ((df_m15['close'] > df_m15['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df_m15['CHoCH_Bear'] = ((df_m15['close'] < df_m15['Swing_Low_20']) & (trend_slow > 0)).astype(int)

    # 4. LIQUIDITY SWEEP (STOP-LOSS HUNT WICK)
    df_m15['Liquidity_Sweep_High'] = ((df_m15['high'] > df_m15['Swing_High_20']) & (df_m15['close'] < df_m15['Swing_High_20'])).astype(int)
    df_m15['Liquidity_Sweep_Low']  = ((df_m15['low'] < df_m15['Swing_Low_20']) & (df_m15['close'] > df_m15['Swing_Low_20'])).astype(int)

    # 5. ORDER BLOCK PROXIMITY (OB)
    is_bear_candle = df_m15['close'] < df_m15['open']
    impulse_up = (df_m15['close'].shift(-2) - df_m15['close']) > (1.5 * (df_m15['high'] - df_m15['low']))
    df_m15['Order_Block_Bull'] = (is_bear_candle & impulse_up).astype(int)

    # 6. FIBONACCI RETRACEMENT
    lookback_fibo = 100
    roll_high = df_m15['high'].rolling(lookback_fibo).max()
    roll_low  = df_m15['low'].rolling(lookback_fibo).min()
    roll_range = (roll_high - roll_low) + 1e-6

    df_m15['Fibo_Pos_100'] = (df_m15['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)

    df_m15['Fibo_Dist_382'] = (df_m15['close'] - fibo_382) / df_m15['close']
    df_m15['Fibo_Dist_500'] = (df_m15['close'] - fibo_500) / df_m15['close']
    df_m15['Fibo_Dist_618'] = (df_m15['close'] - fibo_618) / df_m15['close']

    delta15 = df_m15['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
    df_m15['RSI_M15'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

    df_m15['SMA_20_M15'] = df_m15['close'].rolling(20).mean()
    df_m15['STD_20_M15'] = df_m15['close'].rolling(20).std()
    df_m15['BB_Bandwidth'] = (4 * df_m15['STD_20_M15']) / df_m15['SMA_20_M15']
    df_m15['BB_Pos'] = (df_m15['close'] - (df_m15['SMA_20_M15'] - 2*df_m15['STD_20_M15'])) / (4*df_m15['STD_20_M15'] + 1e-6)

    df_m15['XAU_Return_1'] = df_m15['close'].pct_change(1)
    df_m15['XAU_Return_3'] = df_m15['close'].pct_change(3)
    df_m15['XAU_Return_5'] = df_m15['close'].pct_change(5)

    df_m15['DXY_Close'] = dxy_close.reindex(df_m15.index, method='ffill').bfill()
    df_m15['DXY_Return_1'] = df_m15['DXY_Close'].pct_change(1).fillna(0)
    df_m15['DXY_Return_3'] = df_m15['DXY_Close'].pct_change(3).fillna(0)

    df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
    df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
    df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
    df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)

    df_m15['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
    df_m15['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

    df_m15['TR'] = np.maximum(
        df_m15['high'] - df_m15['low'],
        np.maximum(
            (df_m15['high'] - df_m15['close'].shift()).abs(),
            (df_m15['low'] - df_m15['close'].shift()).abs()
        )
    )
    df_m15['ATR_14'] = df_m15['TR'].rolling(14).mean()

    df_clean = df_m15.dropna().copy()
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

    latest_candle = df_clean[features].iloc[[-1]]
    latest_atr = df_clean['ATR_14'].iloc[-1]
    
    prob_up = model.predict_proba(latest_candle)[0][1] * 100
    prob_down = 100 - prob_up
    
    h1_bull = df_clean['Trend_H1_Bull'].iloc[-1] == 1
    h1_strong_bull = df_clean['Trend_H1_Strong'].iloc[-1] == 1
    
    # Level Struktural Multi-Hour M15 (Lookback 40 candle = 10 jam)
    df_m15['M15_Resistance'] = df_m15['high'].shift(1).rolling(40).max()
    df_m15['M15_Support']    = df_m15['low'].shift(1).rolling(40).min()
    m15_sup = float(df_m15['M15_Support'].dropna().iloc[-1]) if not df_m15['M15_Support'].dropna().empty else float(df_clean['low'].min())
    m15_res = float(df_m15['M15_Resistance'].dropna().iloc[-1]) if not df_m15['M15_Resistance'].dropna().empty else float(df_clean['high'].max())

    cur_close = float(df_clean['close'].iloc[-1])
    cur_open  = float(df_clean['open'].iloc[-1])
    dist_m15_sup = float((cur_close - m15_sup) / cur_close)
    dist_m15_res = float((m15_res - cur_close) / cur_close)

    lower_wick = float(df_clean['Lower_Wick_M15'].iloc[-1])
    upper_wick = float(df_clean['Upper_Wick_M15'].iloc[-1])
    is_bull_candle = cur_close > cur_open
    is_bear_candle = cur_close < cur_open

    tick = mt5.symbol_info_tick(symbol)
    live_ask = tick.ask if tick else cur_close
    live_bid = tick.bid if tick else cur_close
    
    return prob_up, prob_down, h1_bull, h1_strong_bull, latest_atr, live_ask, live_bid, dist_m15_sup, dist_m15_res, lower_wick, upper_wick, is_bull_candle, is_bear_candle, m15_sup, m15_res

peak_profits = {}

def close_position_market(pos, comment_reason="Market Close"):
    """Tutup posisi di harga market dengan filling mode aman."""
    order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(pos.symbol)
    if not tick:
        return False
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
        print(f"{color_res}{COLOR_BOLD}🎯 DYNAMIC EXIT M15 SUKSES (#{pos.ticket}): {comment_reason} | Hasil: ${profit_final:+.2f} USD @ ${price:.2f}{COLOR_RESET}")
        try:
            sync_mt5_trades_to_excel()
        except Exception:
            pass
        return True
    else:
        print(f"⚠️ Gagal Market Close #{pos.ticket}. Code: {res.retcode} ({res.comment})")
        return False

def manage_open_positions(latest_prob_up=50.0, latest_prob_down=50.0):
    """
    Mengelola posisi terbuka M15 secara real-time:
    1. Trailing Profit Lock: Jika profit pernah >= +$3.00 lalu retrace <= +$1.50
    2. Auto Break-Even: Pindahkan SL ke entry + $0.20 saat profit >= +$4.00
    3. Smart AI Early Cut-Loss: Jika arah prediksi M15 berbalik tajam >= 65%
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
        entry_p = pos.price_open
        sl = pos.sl
        
        profit_usd = (current_p - entry_p) * pos.volume * 100.0 if pos_type == mt5.ORDER_TYPE_BUY else (entry_p - current_p) * pos.volume * 100.0

        # Update peak profit
        if pos.ticket not in peak_profits:
            peak_profits[pos.ticket] = profit_usd
        else:
            if profit_usd > peak_profits[pos.ticket]:
                peak_profits[pos.ticket] = profit_usd

        # 1. KONDISI A: Trailing Profit Lock (Pernah >= $3.00, kini retrace turun <= $1.50)
        if ENABLE_TRAILING_LOCK and peak_profits.get(pos.ticket, 0.0) >= TRAILING_TRIGGER_USD and profit_usd <= TRAILING_LOCK_USD:
            if close_position_market(pos, f"Trailing Lock (+${profit_usd:.2f})"):
                peak_profits.pop(pos.ticket, None)
                continue

        # 2. KONDISI B: Auto Break-Even Stop Loss (Risk-Free jika profit >= +$4.00 USD)
        if ENABLE_BREAKEVEN:
            if pos_type == mt5.ORDER_TYPE_BUY and profit_usd >= 4.0 and (sl < entry_p):
                new_sl = entry_p + 0.20
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": new_sl,
                    "tp": pos.tp
                }
                res = mt5.order_send(request)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🛡️ AUTO BREAK-EVEN GUARD (M15): SL posisi BUY #{pos.ticket} dipindahkan ke Profit Lock ${new_sl:.2f} (BE)")
            elif pos_type == mt5.ORDER_TYPE_SELL and profit_usd >= 4.0 and (sl == 0 or sl > entry_p):
                new_sl = entry_p - 0.20
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": new_sl,
                    "tp": pos.tp
                }
                res = mt5.order_send(request)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"🛡️ AUTO BREAK-EVEN GUARD (M15): SL posisi SELL #{pos.ticket} dipindahkan ke Profit Lock ${new_sl:.2f} (BE)")

        # 3. KONDISI C: Smart AI Early Cut-Loss (Sinyal M15 Berbalik Tajam >= 65% saat posisi floating rugi)
        if ENABLE_AI_CUTLOSS and profit_usd < 0:
            if pos_type == mt5.ORDER_TYPE_BUY and latest_prob_down >= AI_CUTLOSS_REV_PROB:
                if close_position_market(pos, f"AI Cut-Loss (Reversal SELL {latest_prob_down:.1f}%)"):
                    peak_profits.pop(pos.ticket, None)
                    continue
            elif pos_type == mt5.ORDER_TYPE_SELL and latest_prob_up >= AI_CUTLOSS_REV_PROB:
                if close_position_market(pos, f"AI Cut-Loss (Reversal BUY {latest_prob_up:.1f}%)"):
                    peak_profits.pop(pos.ticket, None)
                    continue

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

def execute_auto_trade(signal_type, entry_price, sl_pips, tp_pips):
    all_positions = mt5.positions_get(symbol=symbol)
    positions = [p for p in (all_positions or []) if p.magic == MAGIC_NUMBER]
    if len(positions) > 0:
        print(f"⚠️ Masih ada posisi aktif M15 (Ticket: {positions[0].ticket}). Menunggu trade selesai (No Over-Trading).")
        return
        
    order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if signal_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    if signal_type == "BUY":
        sl = price - (sl_pips / 10.0)
        tp = price + (tp_pips / 10.0)
    else:
        sl = price + (sl_pips / 10.0)
        tp = price - (tp_pips / 10.0)
        
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
        "comment": "LightGBM SMC Auto-Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    color_order = COLOR_GREEN if signal_type == "BUY" else COLOR_RED
    print(f"{color_order}{COLOR_BOLD}🚀 [OPEN {signal_type}] MENGIRIM ORDER OTOMATIS KE MT5: {signal_type} {LOT_SIZE} Lot XAUUSD @ ${price:.2f} (SL: ${sl:.2f}, TP: ${tp:.2f}){COLOR_RESET}")
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{color_order}{COLOR_BOLD}🎉 ORDER {signal_type} BERHASIL DIEKSEKUSI OTOMATIS DENGAN PRESISI 0-DELAY!{COLOR_RESET}")
    else:
        print(f"❌ Gagal Eksekusi Order. Retcode Error: {result.retcode} (Comment: {result.comment})")

def main():
    print("\n" + "="*75)
    print("🤖 ROBOT TRADING M15 SMC LEVEL BOUNCE & PRECISION BERJALAN OTOMATIS")
    print(f"Threshold: >={PROB_THRESHOLD}% | SNR 10 Jam | Rejection Wick >= {WICK_MIN_RATIO*100:.0f}% | Trailing Lock: ${TRAILING_TRIGGER_USD:.2f}")
    print("Tekan Ctrl+C untuk menghentikan Robot.")
    print("="*75)

    # Sinkronisasi awal saat bot pertama kali dinyalakan
    print(f"{COLOR_CYAN}🔄 Memeriksa & menyinkronkan riwayat trade M15 ke Excel...{COLOR_RESET}")
    try:
        sync_mt5_trades_to_excel()
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi awal Excel: {e}")

    # Audit awal kondisi pasar & prediksi model saat pertama kali dibuka
    print(f"\n{COLOR_CYAN}🔍 MELAKUKAN AUDIT AWAL STRUKTUR SMC & PREDIKSI MODEL M15 SAAT INI...{COLOR_RESET}")
    res_audit = analyze_market_and_predict()
    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res = res_audit
    print("="*75)
    print(f"📊 HASIL AUDIT MODEL M15 (REAL-TIME LIVE):")
    print(f"• Probabilitas AI          : BUY = {prob_up:.1f}%  |  SELL = {prob_down:.1f}% (Threshold: >= {PROB_THRESHOLD:.1f}%)")
    print(f"• Arah Tren Makro H1       : {'BULLISH (Up)' if h1_bull else 'BEARISH (Down)'}")
    print(f"• Lantai Demand (10 Jam)   : ${m15_sup:.2f} (Jarak: {dist_sup*100:.2f}%, Batas Zona <= {ZONE_THRESHOLD*100:.2f}%)")
    print(f"• Atap Supply (10 Jam)     : ${m15_res:.2f} (Jarak: {dist_res*100:.2f}%, Batas Zona <= {ZONE_THRESHOLD*100:.2f}%)")
    print(f"• Karakter Candlestick M15 : Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}% (Min Wick: {WICK_MIN_RATIO*100:.0f}%)")
    
    if dist_sup <= ZONE_THRESHOLD:
        if lower_w >= WICK_MIN_RATIO and (is_bull_c or lower_w >= 0.35) and prob_up >= PROB_THRESHOLD and h1_bull:
            audit_note = f"{COLOR_GREEN}{COLOR_BOLD}🟢 AREA DEMAND + REJECTION WICK BAWAH ({lower_w*100:.1f}%). SIAP BUY PANTULAN!{COLOR_RESET}"
        elif prob_up >= PROB_THRESHOLD and not h1_bull:
            audit_note = f"{COLOR_YELLOW}🟡 AREA DEMAND: BUY {prob_up:.1f}% ditahan karena Tren Makro H1 Bearish{COLOR_RESET}"
        else:
            audit_note = f"{COLOR_YELLOW}🟡 DI AREA DEMAND: Menunggu Ekor Rejection Bawah ({lower_w*100:.1f}% < {WICK_MIN_RATIO*100:.0f}%){COLOR_RESET}"
    elif dist_res <= ZONE_THRESHOLD:
        if upper_w >= WICK_MIN_RATIO and (is_bear_c or upper_w >= 0.35) and prob_down >= PROB_THRESHOLD and not h1_bull:
            audit_note = f"{COLOR_RED}{COLOR_BOLD}🔴 AREA SUPPLY + REJECTION WICK ATAS ({upper_w*100:.1f}%). SIAP SELL PANTULAN!{COLOR_RESET}"
        elif prob_down >= PROB_THRESHOLD and h1_bull:
            audit_note = f"{COLOR_YELLOW}🟡 AREA SUPPLY: SELL {prob_down:.1f}% ditahan karena Tren Makro H1 Bullish{COLOR_RESET}"
        else:
            audit_note = f"{COLOR_YELLOW}🟡 DI AREA SUPPLY: Menunggu Ekor Rejection Atas ({upper_w*100:.1f}% < {WICK_MIN_RATIO*100:.0f}%){COLOR_RESET}"
    else:
        audit_note = f"{COLOR_YELLOW}🟡 AREA TENGAH (MID-TREND): Harga di antara Demand & Supply. Dilarang open posisi di tengah jalan.{COLOR_RESET}"
        
    print(f"• Status Evaluasi Pasar     : {audit_note}")
    print(f"• Waktu Eksekusi Order      : Menunggu 5 detik sebelum tutup candle ({CHOSEN_TF})")
    print("="*75 + "\n")

    tf_min = 15
    last_analyzed_candle = None
    prev_positions_count = 0
    last_periodic_sync = time.time()
    last_prob_refresh = time.time()

    try:
        while True:
            # 1. LOOP REAL-TIME: Pantau trailing lock, break-even, & AI cut-loss setiap detik
            manage_open_positions(prob_up, prob_down)

            # Deteksi apakah ada posisi M15 yang baru saja tertutup (Hit SL/TP/BE/Cut-Loss)
            all_pos = mt5.positions_get(symbol=symbol)
            cur_positions = [p for p in (all_pos or []) if p.magic == MAGIC_NUMBER]
            cur_count = len(cur_positions)

            if prev_positions_count > 0 and cur_count == 0:
                print(f"\n{COLOR_CYAN}🔔 [DETEKSI EXIT]: Posisi M15 baru saja ditutup. Menyinkronkan update Win/Loss ke Excel...{COLOR_RESET}")
                try:
                    sync_mt5_trades_to_excel()
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel: {sync_err}")

            prev_positions_count = cur_count

            # Sinkronisasi berkala ke Excel setiap 60 detik (Real-time safety, mode silent agar tidak merusak tampilan)
            if time.time() - last_periodic_sync >= 60:
                last_periodic_sync = time.time()
                try:
                    sync_mt5_trades_to_excel(silent=True)
                except Exception:
                    pass

            # Perbarui probabilitas live setiap 30 detik agar audit persentase selalu aktual
            if time.time() - last_prob_refresh >= 30:
                last_prob_refresh = time.time()
                try:
                    res_audit = analyze_market_and_predict()
                    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res = res_audit
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
            
            # Hitung total floating PnL M15 saat ini
            live_pnl = sum([p.profit for p in cur_positions])
            pnl_str = f" | Floating: ${live_pnl:+.2f}" if cur_count > 0 else ""

            # Format probabilitas live berwarna
            prob_color = COLOR_GREEN if prob_up >= PROB_THRESHOLD else (COLOR_RED if prob_down >= PROB_THRESHOLD else COLOR_YELLOW)
            prob_display = f"{prob_color}BUY:{prob_up:.1f}% | SELL:{prob_down:.1f}%{COLOR_RESET}"
            h1_display = "H1:Bull" if h1_bull else "H1:Bear"

            # Status tampilan di console
            if cur_count > 0:
                p_type = cur_positions[0].type
                if p_type == mt5.ORDER_TYPE_BUY:
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}HOLDING BUY #{cur_positions[0].ticket}{COLOR_RESET}{pnl_str}"
                else:
                    status_str = f"{COLOR_RED}{COLOR_BOLD}HOLDING SELL #{cur_positions[0].ticket}{COLOR_RESET}{pnl_str}"
            else:
                if dist_sup <= ZONE_THRESHOLD:
                    if lower_w >= WICK_MIN_RATIO and (is_bull_c or lower_w >= 0.35) and prob_up >= PROB_THRESHOLD and h1_bull:
                        status_str = f"{COLOR_GREEN}{COLOR_BOLD}SIAP BUY DEMAND{COLOR_RESET}"
                    elif prob_up >= PROB_THRESHOLD and not h1_bull:
                        status_str = f"{COLOR_YELLOW}TERFILTER H1{COLOR_RESET}"
                    else:
                        status_str = f"{COLOR_YELLOW}DEMAND (TUNGGU WICK){COLOR_RESET}"
                elif dist_res <= ZONE_THRESHOLD:
                    if upper_w >= WICK_MIN_RATIO and (is_bear_c or upper_w >= 0.35) and prob_down >= PROB_THRESHOLD and not h1_bull:
                        status_str = f"{COLOR_RED}{COLOR_BOLD}SIAP SELL SUPPLY{COLOR_RESET}"
                    elif prob_down >= PROB_THRESHOLD and h1_bull:
                        status_str = f"{COLOR_YELLOW}TERFILTER H1{COLOR_RESET}"
                    else:
                        status_str = f"{COLOR_YELLOW}SUPPLY (TUNGGU WICK){COLOR_RESET}"
                else:
                    status_str = f"{COLOR_YELLOW}TERTAHAN MID-TREND{COLOR_RESET}"

            sys.stdout.write(f"\r⏳ [{CHOSEN_TF}]: {mins:02d}m {secs:02d}s | {prob_display} ({h1_display}) | Status: {status_str}   ")
            sys.stdout.flush()
            
            # 2. TRIGGER CANDLE: Tepat 5 detik sebelum tutup candle M15 (0-delay)
            if seconds_left <= 5 and last_analyzed_candle != current_candle_time:
                last_analyzed_candle = current_candle_time
                print("\n" + "="*75)
                print(f"⚡ CANDLE M15 MENJELANG TUTUP ({now.strftime('%H:%M:%S')})! KEPUTUSAN EKSEKUSI MODEL SMC PRECISION:")
                
                res_audit = analyze_market_and_predict()
                prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res = res_audit
                
                sl_pips = max(40.0, round(atr_val * 10.0 * 0.6, 0))
                tp_pips = round(sl_pips * RRR_RATIO, 0)
                
                print(f"📊 Probabilitas Final  : BUY = {prob_up:.1f}%  |  SELL = {prob_down:.1f}% (Threshold: >={PROB_THRESHOLD}%)")
                print(f"🛡️ Tren Makro H1        : {'BULLISH (Up)' if h1_bull else 'BEARISH (Down)'}")
                print(f"📐 Struktur Level SNR   : Lantai Demand = ${m15_sup:.2f} ({dist_sup*100:.2f}%) | Atap Supply = ${m15_res:.2f} ({dist_res*100:.2f}%)")
                print(f"🕯️ Karakter Candlestick : Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}% (Batas Rejection >= {WICK_MIN_RATIO*100:.0f}%)")
                
                final_signal = "WAIT"
                
                # 1. EVALUASI ZONA LANTAI DEMAND (POTENSI BUY PANTULAN)
                if dist_sup <= ZONE_THRESHOLD:
                    if prob_up >= PROB_THRESHOLD:
                        if not h1_bull:
                            print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN (FILTER H1): Sinyal BUY ({prob_up:.1f}%) di Demand ditahan karena Tren Makro H1 Bearish (Hindari False Breakout).{COLOR_RESET}")
                        elif lower_w >= WICK_MIN_RATIO and (is_bull_c or lower_w >= 0.35):
                            final_signal = "BUY"
                            print(f"{COLOR_GREEN}{COLOR_BOLD}🟢 KEPUTUSAN BUY M15: Rejection Terkonfirmasi di Lantai Demand (${m15_sup:.2f})! Ekor Bawah {lower_w*100:.1f}% >= {WICK_MIN_RATIO*100:.0f}%, Probabilitas BUY {prob_up:.1f}%, H1 Bullish. Membuka order BUY...{COLOR_RESET}")
                        else:
                            print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN (DEMAND WICK): Harga di Lantai Demand (${m15_sup:.2f}), namun belum ada Ekor Bawah Rejection Valid ({lower_w*100:.1f}% < {WICK_MIN_RATIO*100:.0f}%). Menghindari false bounce.{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}🟡 KEPUTUSAN DITAHAN: Harga di Lantai Demand (${m15_sup:.2f}) tapi keyakinan AI BUY ({prob_up:.1f}%) belum mencapai {PROB_THRESHOLD}%.{COLOR_RESET}")

                # 2. EVALUASI ZONA ATAP SUPPLY (POTENSI SELL PANTULAN)
                elif dist_res <= ZONE_THRESHOLD:
                    if prob_down >= PROB_THRESHOLD:
                        if h1_bull:
                            print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN (FILTER H1): Sinyal SELL ({prob_down:.1f}%) di Supply ditahan karena Tren Makro H1 Bullish (Hindari False Breakout).{COLOR_RESET}")
                        elif upper_w >= WICK_MIN_RATIO and (is_bear_c or upper_w >= 0.35):
                            final_signal = "SELL"
                            print(f"{COLOR_RED}{COLOR_BOLD}🔴 KEPUTUSAN SELL M15: Rejection Terkonfirmasi di Atap Supply (${m15_res:.2f})! Ekor Atas {upper_w*100:.1f}% >= {WICK_MIN_RATIO*100:.0f}%, Probabilitas SELL {prob_down:.1f}%, H1 Bearish. Membuka order SELL...{COLOR_RESET}")
                        else:
                            print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN (SUPPLY WICK): Harga di Atap Supply (${m15_res:.2f}), namun belum ada Ekor Atas Rejection Valid ({upper_w*100:.1f}% < {WICK_MIN_RATIO*100:.0f}%). Menghindari false rejection.{COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}🟡 KEPUTUSAN DITAHAN: Harga di Atap Supply (${m15_res:.2f}) tapi keyakinan AI SELL ({prob_down:.1f}%) belum mencapai {PROB_THRESHOLD}%.{COLOR_RESET}")

                # 3. EVALUASI AREA TENGAH (MID-TREND / NO-MAN'S LAND)
                else:
                    cur_p = (ask_p + bid_p) / 2.0
                    print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN (TERTAHAN MID-TREND): Harga (${cur_p:.2f}) berada di tengah rentang (Demand: ${m15_sup:.2f}, Supply: ${m15_res:.2f}). Dilarang membuka posisi di tengah jalan! Menunggu harga menjemput batas level.{COLOR_RESET}")
                    
                if final_signal in ["BUY", "SELL"]:
                    entry_p = ask_p if final_signal == "BUY" else bid_p
                    if AUTO_EXECUTE:
                        execute_auto_trade(final_signal, entry_p, sl_pips, tp_pips)
                
                try:
                    sync_mt5_trades_to_excel()
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel: {sync_err}")
                print("="*75)
                
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nRobot Trading Dihentikan oleh User.")
        mt5.shutdown()

if __name__ == "__main__":
    main()
