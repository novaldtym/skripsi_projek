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
# ⚙️ PENGATURAN ROBOT TRADING OTOMATIS & MANAJEMEN RISIKO (SMC/ICT ENHANCED)
# =========================================================================
CHOSEN_TF        = "M15"      # Timeframe Utama: M15
FORWARD_CANDLES  = 5        # Horizon Prediksi: 5 Candle (75 menit)
LOT_SIZE         = 0.01     # Lot Size Eksekusi
PROB_THRESHOLD   = 60.0     # Ambang Keyakinan Minimum Model (60% untuk Sinyal Valid)

SL_TP_MODE       = "SMART_INTRADAY"
RRR_RATIO        = 1.5      # Risk-to-Reward Ratio (1 : 1.5)
AUTO_EXECUTE     = True     # Set True untuk Eksekusi Otomatis ke MT5!
ENABLE_BREAKEVEN = True     # Pindahkan SL ke Break-Even (Risk-Free) jika profit >= +$4.00 USD

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"

print("="*75)
print("🤖 ROBOT TRADING OTOMATIS LIGHTGBM XAUUSD (SMC / ICT & FIBONACCI ENHANCED)")
print("Fitur: FVG + OB + BOS + CHoCH + Liquidity Sweep + SNR + Fibo + DXY Live")
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
            return 50.0, 50.0, False, False, 8.0, 0.0, 0.0

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

    # 2. SUPPORT & RESISTANCE (SNR SWING HIGH/LOW 20 WINDOW)
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
    
    tick = mt5.symbol_info_tick(symbol)
    live_ask = tick.ask if tick else df_clean['close'].iloc[-1]
    live_bid = tick.bid if tick else df_clean['close'].iloc[-1]
    
    return prob_up, prob_down, h1_bull, h1_strong_bull, latest_atr, live_ask, live_bid

MAGIC_NUMBER = 123230

def manage_open_positions():
    """Mengelola posisi terbuka: Auto Break-Even Stop Loss saat profit >= +$4.00 USD"""
    if not ENABLE_BREAKEVEN:
        return
    all_positions = mt5.positions_get(symbol=symbol)
    if all_positions:
        positions = [p for p in all_positions if p.magic == MAGIC_NUMBER]
        for pos in positions:
            entry_p = pos.price_open
            current_p = pos.price_current
            pos_type = pos.type # 0 = BUY, 1 = SELL
            sl = pos.sl
            
            if pos_type == mt5.ORDER_TYPE_BUY:
                profit_usd = (current_p - entry_p) * pos.volume * 100.0
                if profit_usd >= 4.0 and (sl < entry_p):
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
            elif pos_type == mt5.ORDER_TYPE_SELL:
                profit_usd = (entry_p - current_p) * pos.volume * 100.0
                if profit_usd >= 4.0 and (sl == 0 or sl > entry_p):
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
        "magic": 123230,
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
    print("🤖 ROBOT TRADING BERJALAN OTOMATIS (SMC / ICT ENHANCED)")
    print("Tekan Ctrl+C untuk menghentikan Robot.")
    print("="*75)

    # Sinkronisasi awal saat bot pertama kali dinyalakan
    print(f"{COLOR_CYAN}🔄 Memeriksa & menyinkronkan seluruh riwayat trade M15 ke Excel...{COLOR_RESET}")
    try:
        sync_mt5_trades_to_excel()
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi awal Excel: {e}")

    tf_min = 15
    last_analyzed_candle = None
    prev_positions_count = 0
    last_periodic_sync = time.time()

    try:
        while True:
            manage_open_positions()

            # Deteksi apakah ada posisi M15 yang baru saja tertutup (Hit SL/TP/BE)
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

            # Sinkronisasi berkala ke Excel setiap 60 detik (Real-time safety)
            if time.time() - last_periodic_sync >= 60:
                last_periodic_sync = time.time()
                try:
                    sync_mt5_trades_to_excel()
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
            
            # Status tampilan di console (Kuning untuk Netral, Hijau untuk Buy, Merah untuk Sell)
            if cur_count > 0:
                p_type = cur_positions[0].type
                if p_type == mt5.ORDER_TYPE_BUY:
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}HOLDING BUY #{cur_positions[0].ticket}{COLOR_RESET}"
                else:
                    status_str = f"{COLOR_RED}{COLOR_BOLD}HOLDING SELL #{cur_positions[0].ticket}{COLOR_RESET}"
            else:
                status_str = f"{COLOR_YELLOW}NETRAL/WAIT{COLOR_RESET}"

            sys.stdout.write(f"\r⏳ [BOT M15 MONITORING]: Sisa Waktu Candle ({CHOSEN_TF}): {mins:02d}m {secs:02d}s | Status: {status_str}   ")
            sys.stdout.flush()
            
            # Trigger tepat 5 detik sebelum tutup candle M15 (0-delay sebelum pembentukan candle baru)
            if seconds_left <= 5 and last_analyzed_candle != current_candle_time:
                last_analyzed_candle = current_candle_time
                print("\n" + "-"*75)
                print(f"⚡ MENJELANG TUTUP CANDLE M15 ({now.strftime('%H:%M:%S')})! MELAKUKAN ANALISIS SMC/ICT & TREND GUARD...")
                
                prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p = analyze_market_and_predict()
                
                sl_pips = max(40.0, round(atr_val * 10.0 * 0.6, 0))
                tp_pips = round(sl_pips * RRR_RATIO, 0)
                
                print(f"📊 Probabilitas Model: BUY={prob_up:.1f}% | SELL={prob_down:.1f}%")
                print(f"🛡️ Tren H1: {'BULLISH (Up)' if h1_bull else 'BEARISH (Down)'}")
                
                final_signal = "WAIT"
                
                if prob_up >= PROB_THRESHOLD:
                    if h1_bull:
                        final_signal = "BUY"
                        print(f"{COLOR_GREEN}{COLOR_BOLD}🟢 SINYAL BUY VALID: Keyakinan {prob_up:.1f}% >= {PROB_THRESHOLD}% (Searah Tren H1 Bullish){COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}⚠️ TREND GUARD FILTER: Sinyal BUY ({prob_up:.1f}%) Dibatalkan karena Tren H1 Bearish (Hindari Trapping).{COLOR_RESET}")
                elif prob_down >= PROB_THRESHOLD:
                    if not h1_bull:
                        final_signal = "SELL"
                        print(f"{COLOR_RED}{COLOR_BOLD}🔴 SINYAL SELL VALID: Keyakinan {prob_down:.1f}% >= {PROB_THRESHOLD}% (Searah Tren H1 Bearish){COLOR_RESET}")
                    else:
                        print(f"{COLOR_YELLOW}⚠️ TREND GUARD FILTER: Sinyal SELL ({prob_down:.1f}%) Dibatalkan karena Tren H1 Bullish Kuat (Hindari Trapping).{COLOR_RESET}")
                else:
                    print(f"{COLOR_YELLOW}🟡 SINYAL NETRAL: Kepastian ({max(prob_up, prob_down):.1f}%) < Ambang Batas {PROB_THRESHOLD}%.{COLOR_RESET}")
                    
                if final_signal in ["BUY", "SELL"]:
                    entry_p = ask_p if final_signal == "BUY" else bid_p
                    if AUTO_EXECUTE:
                        execute_auto_trade(final_signal, entry_p, sl_pips, tp_pips)
                
                try:
                    sync_mt5_trades_to_excel()
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel: {sync_err}")
                print("-"*75)
                
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nRobot Trading Dihentikan oleh User.")
        mt5.shutdown()

if __name__ == "__main__":
    main()
