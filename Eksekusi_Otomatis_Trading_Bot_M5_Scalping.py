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

# Variabel lock socket global untuk proteksi single instance saat main() dijalankan
_lock_socket = None

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
# ⚙️ PENGATURAN ROBOT TRADING M5 MULTI-ZONE ADAPTIVE SCALPER
# =========================================================================
CHOSEN_TF              = "M5"        # Timeframe Utama: M5 (5 Menit)
FORWARD_CANDLES        = 5           # Horizon Prediksi: 5 Candle (25 menit)
LOT_SIZE               = 0.01        # Lot Size Eksekusi
MAGIC_NUMBER           = 123236      # Magic ID Unik M5 v3.0 (Fresh Forward Testing)
MAX_STACKED_POSITIONS  = 2           # Batas Maksimal Layer Posisi
AUTO_EXECUTE           = True        # Eksekusi Otomatis ke MT5

# --- SMC MULTI-ZONE ADAPTIVE PARAMETERS (VERSI 3.0) ---
# Zona A: Boundary Bounce (Perbatasan Ekstrem Demand/Supply)
ZONE_A_THRESHOLD       = 0.0012      # Jarak <= 0.12% (~$5) dari Level SNR
ZONE_A_PROB_MIN        = 56.0        # Ambang AI batas ekstrem
ZONE_A_WICK_MIN        = 0.25        # Minimal 25% ekor penolakan

# Zona B: Proximity Opportunity (Mepet Garis / Rebound Struktur M5)
ZONE_B_THRESHOLD       = 0.0030      # Jarak 0.12% s/d 0.30% (~$5 - $13)
ZONE_B_PROB_MIN        = 62.0        # Ambang AI Zona B (62%)
ZONE_B_WICK_MIN        = 0.20        # Minimal 20% ekor penolakan atau Higher Low/Lower High

# Zona C: High-Probability Trend Scalp (Area Antara / Momentum Kuat)
ZONE_C_PROB_MIN        = 66.0        # Ambang AI Sangat Kuat (>= 66%) + Konfirmasi BOS/Trend

# --- TARGET DYNAMIC REAL-TIME EXIT PER ZONA ---
QUICK_TP_USD           = 3.00        # Target Scalping Seimbang ($3.00 USD / 30 pips)
MAX_CUTLOSS_USD        = 2.40        # Cut-Loss Terukur & Ketat ($2.40 USD / 24 pips)
TRAILING_TRIGGER_USD   = 2.40        # Aktifkan Trailing Lock saat profit mencapai >= +$2.40 USD
TRAILING_LOCK_USD      = 1.80        # Kunci profit minimal +$1.80 USD (seimbang dengan risiko, tidak tipis)
EMERGENCY_SL_USD       = 3.20        # Hard SL Pengaman Darurat di Broker ($3.20 USD)

# --- IDENTITAS VERSI DAN LOGGING ---
BOT_VERSION            = "Versi 3.4 (Technical Confluence Suite: Descending Triangle, Anti-Falling Knife & Symmetric RRR)"
MODEL_LABEL_EXCEL      = "LightGBM M5 v3.4 (Confluence)"
THRESHOLD_LABEL_EXCEL  = "Technical Confluence (Stoch RSI + Patterns v3.4)"
ORDER_COMMENT          = "LightGBM M5 v3.4"
COLLISION_DISTANCE_MIN = 0.0018      # Jarak minimal 0.18% (~$8) dari Lantai Demand / Atap Supply Mayor

MT5_PATH               = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH        = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd_m5.pkl"
EXCEL_M5_PATH          = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_M5_Scalping.xlsx"

print("="*85)
print(f"⚡ ROBOT TRADING M5 MULTI-ZONE SCALPER [{BOT_VERSION}]")
print(f"Pembeda Utama: Multi-Zone Entry (A:Boundary, B:Proximity, C:Trend) + Structure HL/LH")
print(f"Fitur: Target Quick TP ${QUICK_TP_USD:.2f} | Hard Cut-Loss -${MAX_CUTLOSS_USD:.2f} | Magic: {MAGIC_NUMBER}")
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
                threshold_label="SMC Level Bounce (TP $2.00 / Cut-Loss $1.80)",
                silent=True
            )
        except Exception:
            pass
        return True
    else:
        print(f"⚠️ Gagal Market Close #{pos.ticket}. Code: {res.retcode} ({res.comment})")
        return False

# Pelacak Puncak Profit per Tiket untuk Trailing Lock
peak_profits = {}

def manage_open_positions(latest_prob_up=50.0, latest_prob_down=50.0, channel_data=None, pattern_data=None, struct_data=None, m30_bull=False, h1_bull=False):
    """
    Pemantauan Real-Time Setiap Detik (Versi 3.2 Adaptive Runner Exit Engine):
    1. Evaluasi Momentum (Sempit vs Kuat/Runner):
       - Momentum Sempit (Konsolidasi/Sideways): Ambil profit cepat Quick Scalp TP (+$2.00 USD)
       - Momentum Kuat (Breakdown/Impulsif/Kanal Miring Tajam): Aktifkan RUNNER MODE (Let Profit Run)!
         Tidak ditutup kaku di $2.00, melainkan mengikuti harga dengan Dynamic Trailing Buffer ($1.00 s/d $2.00 USD).
    2. Trailing Profit Lock Awal:
       - Jika profit sempat >= $1.20, beri proteksi profit minimal agar tidak hangus jadi minus.
    3. Hard Scalp Cut-Loss Terukur (-$1.80 USD) -> Menjaga RRR 1:1 Sehat.
    4. Smart AI Early Cut-Loss (Jika arah sinyal berbalik tajam >= 60%).
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

        # Update puncak profit yang pernah dicapai posisi ini
        if pos.ticket not in peak_profits:
            peak_profits[pos.ticket] = profit_usd
        else:
            if profit_usd > peak_profits[pos.ticket]:
                peak_profits[pos.ticket] = profit_usd

        cur_peak = peak_profits[pos.ticket]

        # -----------------------------------------------------------------
        # 🧠 ANALISIS MOMENTUM REAL-TIME: MOMENTUM SEMPIT vs MOMENTUM KUAT (RUNNER)
        # -----------------------------------------------------------------
        comment = pos.comment.upper() if pos.comment else ""
        slope = channel_data.get('slope', 0.0) if channel_data else 0.0
        ch_type = channel_data.get('channel_type', 'HORIZONTAL') if channel_data else 'HORIZONTAL'
        pattern = pattern_data.get('pattern', '').upper() if pattern_data else ''
        regime = struct_data.get('market_regime', 'SIDEWAYS') if struct_data else 'SIDEWAYS'

        is_strong_momentum = False
        if pos_type == mt5.ORDER_TYPE_SELL:
            # SELL berada dalam momentum kuat jika didukung kanal turun tajam, breakdown pola, atau tren makro
            if (
                slope < -0.12 or 
                "DESCENDING" in ch_type or 
                "FALLING" in pattern or 
                "DESCENDING" in pattern or 
                (not m30_bull and not h1_bull) or 
                latest_prob_down >= 58.0 or 
                "Z-C" in comment or 
                regime == 'TRENDING_BEAR'
            ):
                is_strong_momentum = True
        else: # BUY
            # BUY berada dalam momentum kuat jika didukung kanal naik tajam, breakout pola, atau tren makro
            if (
                slope > 0.12 or 
                "ASCENDING" in ch_type or 
                "RISING" in pattern or 
                "ASCENDING" in pattern or 
                (m30_bull and h1_bull) or 
                latest_prob_up >= 58.0 or 
                "Z-C" in comment or 
                regime == 'TRENDING_BULL'
            ):
                is_strong_momentum = True

        # -----------------------------------------------------------------
        # 1. KONDISI A: ADAPTIVE RUNNER MODE (MOMENTUM BAGUS - LET PROFIT RUN!)
        # -----------------------------------------------------------------
        if is_strong_momentum and cur_peak >= QUICK_TP_USD:
            # Mode Runner Aktif! Jangan keluar di $2.00, ikuti gerakan pasar sejauh mungkin!
            if cur_peak >= 8.00:
                trailing_buffer = 2.00  # Profit raksasa (>= $8.00), buffer $2.00 untuk ruang ayunan
            elif cur_peak >= 4.00:
                trailing_buffer = 1.40  # Profit menengah (>= $4.00), buffer $1.40
            else:
                trailing_buffer = 1.00  # Profit awal ($2.00 - $4.00), buffer $1.00

            runner_floor = max(1.20, cur_peak - trailing_buffer)

            # Jika harga retrace menyentuh batas trailing floor runner
            if profit_usd <= runner_floor:
                if close_position_market(pos, f"Runner TP (+${profit_usd:.2f}) [Peak: ${cur_peak:.2f}]"):
                    peak_profits.pop(pos.ticket, None)
                    continue

        # -----------------------------------------------------------------
        # 2. KONDISI B: QUICK SCALP TP (MOMENTUM SEMPIT / KONSOLIDASI)
        # -----------------------------------------------------------------
        elif (not is_strong_momentum) and profit_usd >= QUICK_TP_USD:
            # Ambil sedikit tidak apa-apa karena ruang gerak sempit
            if close_position_market(pos, f"Scalp TP (+${profit_usd:.2f}) [Konsolidasi Sempit]"):
                peak_profits.pop(pos.ticket, None)
                continue

        # -----------------------------------------------------------------
        # 3. KONDISI C: TRAILING PROFIT LOCK AWAL ($1.20 - $2.00)
        # -----------------------------------------------------------------
        if cur_peak >= TRAILING_TRIGGER_USD and cur_peak < QUICK_TP_USD:
            # Jika momentum kuat, beri buffer retrace lebih toleran ($0.70) agar tidak terbuang oleh ekor kecil
            retrace_limit = 0.70 if is_strong_momentum else TRAILING_LOCK_USD
            if profit_usd <= retrace_limit:
                if close_position_market(pos, f"Trailing Lock (+${profit_usd:.2f})"):
                    peak_profits.pop(pos.ticket, None)
                    continue

        # -----------------------------------------------------------------
        # 4. KONDISI D: HARD SCALP CUT-LOSS TERUKUR (-$1.80 USD) -> RRR 1:1 Sehat
        # -----------------------------------------------------------------
        if profit_usd <= -MAX_CUTLOSS_USD:
            if close_position_market(pos, f"Scalp Cut-Loss (-${abs(profit_usd):.2f})"):
                peak_profits.pop(pos.ticket, None)
                continue

        # -----------------------------------------------------------------
        # 5. KONDISI E: SMART AI EARLY CUT-LOSS (Sinyal M5 Berbalik Tajam >= 60%)
        # -----------------------------------------------------------------
        if pos_type == mt5.ORDER_TYPE_BUY and latest_prob_down >= 60.0:
            if close_position_market(pos, f"AI Cut-Loss (Reversal SELL {latest_prob_down:.1f}%)"):
                peak_profits.pop(pos.ticket, None)
                continue
        elif pos_type == mt5.ORDER_TYPE_SELL and latest_prob_up >= 60.0:
            if close_position_market(pos, f"AI Cut-Loss (Reversal BUY {latest_prob_up:.1f}%)"):
                peak_profits.pop(pos.ticket, None)
                continue

def calc_dynamic_channel(df_data, lookback=40):
    """
    Menghitung Kanal Regresi Linear Dinamis M5 (Support & Resisten Miring):
    - slope: Sudut kemiringan tren M5 ($/candle). Positif = Uptrend Channel, Negatif = Downtrend Channel
    - dyn_support: Batas garis bawah (Support Miring / Ascending Trendline Support)
    - dyn_resistance: Batas garis atas (Resisten Miring / Ascending Trendline Resistance)
    - channel_type: 'UPTREND_CHANNEL' (Kanal Naik), 'DOWNTREND_CHANNEL' (Kanal Turun), 'HORIZONTAL'
    """
    if len(df_data) < lookback:
        sub = df_data.copy()
    else:
        sub = df_data.tail(lookback).copy()
        
    N = len(sub)
    if N < 10:
        c = float(sub['close'].iloc[-1])
        return 0.0, c * 0.995, c * 1.005, 'HORIZONTAL', 0.01, 0.01
        
    x = np.arange(N)
    y = sub['close'].values
    slope, intercept = np.polyfit(x, y, 1)
    
    residuals = y - (slope * x + intercept)
    support_offset = np.percentile(residuals, 5)
    resistance_offset = np.percentile(residuals, 95)
    
    curr_x = N - 1
    midline = slope * curr_x + intercept
    dyn_support = float(midline + support_offset)
    dyn_resistance = float(midline + resistance_offset)
    
    curr_close = float(sub['close'].iloc[-1])
    dist_dyn_sup = float(abs(curr_close - dyn_support) / curr_close)
    dist_dyn_res = float(abs(dyn_resistance - curr_close) / curr_close)
    
    if slope > 0.10:
        channel_type = 'UPTREND_CHANNEL'
    elif slope < -0.10:
        channel_type = 'DOWNTREND_CHANNEL'
    else:
        channel_type = 'HORIZONTAL'
        
    return float(slope), dyn_support, dyn_resistance, channel_type, dist_dyn_sup, dist_dyn_res

def detect_multi_horizon_snr_and_patterns(df_data, lookback_multiday=700, lookback_pattern=60):
    """
    Analisis Multi-Horizon SNR & Pola Grafik Teknikal Lanjutan (Versi 3.2):
    1. Multi-Day Structural SNR (Lookback 2-4 Hari / ~600-800 lilin M5):
       - major_demand: Lantai terendah multi-day
       - major_supply: Atap tertinggi multi-day
       - nearest_sup: Level swing support terdekat di bawah harga
       - nearest_res: Level swing resistance terdekat di atas harga
       - dist_near_sup: Jarak persentase ke lantai terdekat
       - dist_near_res: Jarak persentase ke atap terdekat
    2. Pola Grafik Teknikal (Wedge & Channels):
       - RISING_WEDGE: Baji Naik (Kedua garis naik, menyempit ke atas -> Potensi Reversal Bearish)
       - FALLING_WEDGE: Baji Turun (Kedua garis turun, menyempit ke bawah -> Potensi Reversal Bullish)
       - ASCENDING_CHANNEL: Kanal Miring Naik (Kedua garis naik paralel)
       - DESCENDING_CHANNEL: Kanal Miring Turun (Kedua garis turun paralel)
       - HORIZONTAL_RANGE: Konsolidasi Datar
       - SYMMETRICAL_TRIANGLE: Segitiga Simetris
    3. Anti-Collision Guard:
       - can_sell_safely: True jika jarak ke support terdekat > 0.18% (~$8)
       - can_buy_safely: True jika jarak ke resistance terdekat > 0.18% (~$8)
    """
    n = len(df_data)
    curr_close = float(df_data['close'].iloc[-1])
    
    # 1. Multi-Day Lookback (2-4 Hari)
    lb_multi = min(n, lookback_multiday)
    sub_multi = df_data.tail(lb_multi).copy()
    
    major_demand = float(sub_multi['low'].min())
    major_supply = float(sub_multi['high'].max())
    
    # Swing Pivots terdekat
    roll_lows = sub_multi['low'].rolling(12, center=True).min()
    roll_highs = sub_multi['high'].rolling(12, center=True).max()
    
    swing_lows = sub_multi[sub_multi['low'] == roll_lows]['low'].values
    swing_highs = sub_multi[sub_multi['high'] == roll_highs]['high'].values
    
    # Dynamic Swing Levels & Flip Zones (Breakdown/Breakout Adaptive)
    sups_below = [float(s) for s in swing_lows if s < curr_close - 1.0]
    res_above  = [float(r) for r in swing_highs if r > curr_close + 1.0]
    
    struct_sup_cand = float(df_data['low'].shift(1).tail(120).min()) if len(df_data) >= 120 else major_demand
    struct_res_cand = float(df_data['high'].shift(1).tail(120).max()) if len(df_data) >= 120 else major_supply
    if struct_sup_cand < curr_close - 1.0:
        sups_below.append(struct_sup_cand)
    if struct_res_cand > curr_close + 1.0:
        res_above.append(struct_res_cand)
        
    nearest_sup = max(sups_below) if len(sups_below) > 0 else major_demand
    nearest_res = min(res_above) if len(res_above) > 0 else major_supply
    
    dist_near_sup = max(0.0, (curr_close - nearest_sup) / curr_close)
    dist_near_res = max(0.0, (nearest_res - curr_close) / curr_close)
    
    # 2. Pola Grafik Teknikal (Lookback 60 lilin)
    lb_pat = min(n, lookback_pattern)
    sub_pat = df_data.tail(lb_pat)
    x = np.arange(lb_pat)
    
    slope_high, int_high = np.polyfit(x, sub_pat['high'].values, 1)
    slope_low, int_low   = np.polyfit(x, sub_pat['low'].values, 1)
    
    spread_start = int_high - int_low
    spread_end = (slope_high * lb_pat + int_high) - (slope_low * lb_pat + int_low)
    is_converging = spread_end < (spread_start * 0.75)
    
    if slope_high > 0.08 and slope_low > 0.08:
        if is_converging or (slope_low - slope_high > 0.06):
            pattern = "RISING_WEDGE (Baji Naik - Potensi Reversal Bearish)"
            bias = "BEARISH_REVERSAL"
        else:
            pattern = "ASCENDING_CHANNEL (Kanal Miring Naik)"
            bias = "BULLISH_TREND"
    elif slope_high < -0.08 and slope_low < -0.08:
        if is_converging or (slope_high - slope_low > 0.06):
            pattern = "FALLING_WEDGE (Baji Turun - Potensi Reversal Bullish)"
            bias = "BULLISH_REVERSAL"
        else:
            pattern = "DESCENDING_CHANNEL (Kanal Miring Turun)"
            bias = "BEARISH_TREND"
    elif slope_high < -0.06 and slope_low > 0.06:
        pattern = "SYMMETRICAL_TRIANGLE (Segitiga Simetris)"
        bias = "BREAKOUT_PENDING"
    else:
        pattern = "HORIZONTAL_RANGE (Konsolidasi Datar)"
        bias = "SIDEWAYS"
        
    can_sell_safely = dist_near_sup > COLLISION_DISTANCE_MIN
    can_buy_safely  = dist_near_res > COLLISION_DISTANCE_MIN
    
    return {
        'major_demand': major_demand,
        'major_supply': major_supply,
        'nearest_sup': nearest_sup,
        'nearest_res': nearest_res,
        'dist_near_sup': dist_near_sup,
        'dist_near_res': dist_near_res,
        'pattern': pattern,
        'pattern_bias': bias,
        'slope_high': float(slope_high),
        'slope_low': float(slope_low),
        'can_sell_safely': can_sell_safely,
        'can_buy_safely': can_buy_safely
    }

def calc_technical_indicators(df_data):
    """
    Menghitung Indikator Teknikal Lengkap untuk Konfluensi Keputusan Trading:
    1. Stochastic RSI (14, 14, 3, 3) -> Deteksi Overbought/Oversold & Golden/Death Cross
    2. Relative Strength Index (RSI 14) -> Momentum Pasar
    3. Bollinger Bands (20, 2) -> Posisi terhadap Upper, Middle, Lower Band
    4. EMA Trend (EMA 20 & EMA 50) -> Arah Tren Dinamis
    """
    if len(df_data) < 35:
        return {
            'rsi': 50.0, 'stoch_k': 50.0, 'stoch_d': 50.0,
            'prev_stoch_k': 50.0, 'prev_stoch_d': 50.0,
            'bb_pos': 0.5, 'bb_bandwidth': 0.002,
            'ema_20': float(df_data['close'].iloc[-1]) if len(df_data) > 0 else 0.0,
            'ema_50': float(df_data['close'].iloc[-1]) if len(df_data) > 0 else 0.0,
            'is_ema_bull': True,
            'stoch_oversold': False, 'stoch_overbought': False,
            'stoch_bull_cross': False, 'stoch_bear_cross': False,
            'summary_desc': 'Data terbatas'
        }
    
    close = df_data['close']
    
    # 1. RSI 14
    delta = close.diff()
    gain = (delta.where(delta > 0, 0.0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
    rs = gain / (loss + 1e-9)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))
    
    # 2. Stochastic RSI (14, 14, 3, 3)
    rsi_min = rsi_series.rolling(14).min()
    rsi_max = rsi_series.rolling(14).max()
    stoch_rsi = (rsi_series - rsi_min) / ((rsi_max - rsi_min) + 1e-9) * 100.0
    stoch_k = stoch_rsi.rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()
    
    cur_k = float(stoch_k.iloc[-1]) if not pd.isna(stoch_k.iloc[-1]) else 50.0
    cur_d = float(stoch_d.iloc[-1]) if not pd.isna(stoch_d.iloc[-1]) else 50.0
    prev_k = float(stoch_k.iloc[-2]) if not pd.isna(stoch_k.iloc[-2]) else cur_k
    prev_d = float(stoch_d.iloc[-2]) if not pd.isna(stoch_d.iloc[-2]) else cur_d
    
    # 3. Bollinger Bands (20, 2)
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    bb_upper = sma_20 + (2.0 * std_20)
    bb_lower = sma_20 - (2.0 * std_20)
    bb_bw = float(((4.0 * std_20) / sma_20).iloc[-1]) if not pd.isna(std_20.iloc[-1]) else 0.002
    bb_pos = float(((close - bb_lower) / ((bb_upper - bb_lower) + 1e-9)).iloc[-1]) if not pd.isna(bb_upper.iloc[-1]) else 0.5
    
    # 4. EMA 20 & EMA 50
    ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
    is_ema_bull = ema_20 > ema_50
    
    # Kondisi Turunan
    stoch_oversold = cur_k <= 25.0
    stoch_overbought = cur_k >= 75.0
    stoch_bull_cross = (cur_k > cur_d) and (prev_k <= prev_d)
    stoch_bear_cross = (cur_k < cur_d) and (prev_k >= prev_d)
    
    cur_rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else 50.0
    
    summary_desc = (
        f"Stoch RSI: %K={cur_k:.1f}, %D={cur_d:.1f} "
        f"({'OVERSOLD 🟢' if stoch_oversold else ('OVERBOUGHT 🔴' if stoch_overbought else 'NETRAL')}) | "
        f"RSI: {cur_rsi:.1f} | BB Pos: {bb_pos*100:.1f}% | EMA20/50: {'BULL' if is_ema_bull else 'BEAR'}"
    )
    
    return {
        'rsi': cur_rsi,
        'stoch_k': cur_k,
        'stoch_d': cur_d,
        'prev_stoch_k': prev_k,
        'prev_stoch_d': prev_d,
        'bb_pos': bb_pos,
        'bb_bandwidth': bb_bw,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'is_ema_bull': is_ema_bull,
        'stoch_oversold': stoch_oversold,
        'stoch_overbought': stoch_overbought,
        'stoch_bull_cross': stoch_bull_cross,
        'stoch_bear_cross': stoch_bear_cross,
        'summary_desc': summary_desc
    }

def detect_candle_structure(df_clean):
    """
    Menganalisis struktur candlestick 3-5 candle terakhir (SMC Scalping):
    - Pola Higher Low (HL): Rebound bullish dari area demand
    - Pola Lower High (LH): Rejection bearish dari area supply
    - Breakout Structure (BOS / CHoCH baru)
    - Market State: 'TRENDING_BULL', 'TRENDING_BEAR', 'SIDEWAYS_TIGHT', 'SIDEWAYS_WIDE'
    """
    if len(df_clean) < 5:
        return {
            'is_higher_low': False, 'is_lower_high': False,
            'bos_bull_recent': False, 'bos_bear_recent': False,
            'choch_bull_recent': False, 'choch_bear_recent': False,
            'market_regime': 'SIDEWAYS', 'fibo_pos': 0.5,
            'structure_desc': 'Data terbatas'
        }
    
    c0_low  = float(df_clean['low'].iloc[-1])
    c1_low  = float(df_clean['low'].iloc[-2])
    c2_low  = float(df_clean['low'].iloc[-3])
    
    c0_high = float(df_clean['high'].iloc[-1])
    c1_high = float(df_clean['high'].iloc[-2])
    c2_high = float(df_clean['high'].iloc[-3])
    
    c0_close = float(df_clean['close'].iloc[-1])
    c1_close = float(df_clean['close'].iloc[-2])
    
    is_higher_low = (c0_low > c1_low) or (c1_low > c2_low and c0_close > c1_close)
    is_lower_high = (c0_high < c1_high) or (c1_high < c2_high and c0_close < c1_close)
    
    bos_bull_recent = bool(df_clean['BOS_Bull'].iloc[-3:].max() == 1)
    bos_bear_recent = bool(df_clean['BOS_Bear'].iloc[-3:].max() == 1)
    choch_bull_recent = bool(df_clean['CHoCH_Bull'].iloc[-3:].max() == 1)
    choch_bear_recent = bool(df_clean['CHoCH_Bear'].iloc[-3:].max() == 1)
    
    # Deteksi Lilin Impulsif (Breakout / Breakdown News Momentum)
    cur_range = (float(df_clean['high'].iloc[-1]) - float(df_clean['low'].iloc[-1])) + 1e-6
    cur_body  = abs(float(df_clean['close'].iloc[-1]) - float(df_clean['open'].iloc[-1]))
    body_ratio = cur_body / cur_range
    is_impulse_bear = bool(float(df_clean['close'].iloc[-1]) < float(df_clean['open'].iloc[-1]) and body_ratio >= 0.55)
    is_impulse_bull = bool(float(df_clean['close'].iloc[-1]) > float(df_clean['open'].iloc[-1]) and body_ratio >= 0.55)

    bb_bw = float(df_clean['BB_Bandwidth'].iloc[-1])
    ret_5 = float(df_clean['XAU_Return_5'].iloc[-1]) if 'XAU_Return_5' in df_clean.columns else 0.0
    fibo_pos = float(df_clean['Fibo_Pos_100'].iloc[-1]) if 'Fibo_Pos_100' in df_clean.columns else 0.5
    
    if bb_bw < 0.0020:
        market_regime = 'SIDEWAYS_TIGHT'
    elif ret_5 > 0.0025:
        market_regime = 'TRENDING_BULL'
    elif ret_5 < -0.0025:
        market_regime = 'TRENDING_BEAR'
    else:
        market_regime = 'SIDEWAYS_WIDE'
        
    structure_desc = f"Regime: {market_regime} | HL: {is_higher_low} | LH: {is_lower_high} | Fibo: {fibo_pos*100:.1f}%"
    
    return {
        'is_higher_low': is_higher_low,
        'is_lower_high': is_lower_high,
        'bos_bull_recent': bos_bull_recent,
        'bos_bear_recent': bos_bear_recent,
        'choch_bull_recent': choch_bull_recent,
        'choch_bear_recent': choch_bear_recent,
        'is_impulse_bear': is_impulse_bear,
        'is_impulse_bull': is_impulse_bull,
        'market_regime': market_regime,
        'fibo_pos': fibo_pos,
        'structure_desc': structure_desc
    }

def analyze_market_and_predict():
    rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 500)
    rates_m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 500)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
    
    fallback_struct = {
        'is_higher_low': False, 'is_lower_high': False,
        'bos_bull_recent': False, 'bos_bear_recent': False,
        'choch_bull_recent': False, 'choch_bear_recent': False,
        'is_impulse_bear': False, 'is_impulse_bull': False,
        'market_regime': 'SIDEWAYS', 'fibo_pos': 0.5,
        'structure_desc': 'Fallback MT5 Disconnect'
    }
    fallback_channel = {
        'slope': 0.0, 'dyn_sup': 0.0, 'dyn_res': 9999.0,
        'dyn_support': 0.0, 'dyn_resistance': 9999.0,
        'channel_type': 'HORIZONTAL',
        'dist_dyn_sup': 0.01, 'dist_dyn_res': 0.01
    }
    fallback_pattern = {
        'major_demand': 0.0, 'major_supply': 9999.0,
        'nearest_sup': 0.0, 'nearest_res': 9999.0,
        'dist_near_sup': 0.01, 'dist_near_res': 0.01,
        'pattern': 'HORIZONTAL_RANGE (Konsolidasi Datar)',
        'pattern_bias': 'SIDEWAYS',
        'slope_high': 0.0, 'slope_low': 0.0,
        'can_sell_safely': True, 'can_buy_safely': True
    }
    fallback_tech = {
        'rsi': 50.0, 'stoch_k': 50.0, 'stoch_d': 50.0,
        'prev_stoch_k': 50.0, 'prev_stoch_d': 50.0,
        'bb_pos': 0.5, 'bb_bandwidth': 0.002,
        'ema_20': 0.0, 'ema_50': 0.0,
        'is_ema_bull': True,
        'stoch_oversold': False, 'stoch_overbought': False,
        'stoch_bull_cross': False, 'stoch_bear_cross': False,
        'summary_desc': 'Fallback MT5 Disconnect'
    }

    if rates_m5 is None or len(rates_m5) == 0 or rates_h1 is None or len(rates_h1) == 0:
        mt5.initialize(path=MT5_PATH)
        rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 1000)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 500)
        rates_m30 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M30, 0, 500)
        rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
        if rates_m5 is None or len(rates_m5) == 0:
            return 50.0, 50.0, False, False, 5.0, 0.0, 0.0, 0.01, 0.01, 0.0, 0.0, False, False, 0.0, 0.0, fallback_struct, fallback_channel, fallback_pattern, fallback_tech

    df_m5 = pd.DataFrame(rates_m5)
    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
    df_m5.set_index('time', inplace=True)

    # Guarding Multi-TF DataFrames
    m30_bull = False
    if rates_m30 is not None and len(rates_m30) > 0:
        try:
            df_m30 = pd.DataFrame(rates_m30)
            df_m30['time'] = pd.to_datetime(df_m30['time'], unit='s')
            df_m30.set_index('time', inplace=True)
            df_m30['EMA_50_M30'] = df_m30['close'].ewm(span=50, adjust=False).mean()
            m30_bull = bool(df_m30['close'].iloc[-1] > df_m30['EMA_50_M30'].iloc[-1])
        except Exception:
            m30_bull = False

    h1_bull = False
    if rates_h1 is not None and len(rates_h1) > 0:
        try:
            df_h1 = pd.DataFrame(rates_h1)
            df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
            df_h1.set_index('time', inplace=True)
            df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
            df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
            df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
            df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
            df_m5['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m5.index, method='ffill').fillna(0)
            df_m5['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m5.index, method='ffill').fillna(0)
            h1_bull = bool(df_h1['Trend_H1_Bull'].iloc[-1] == 1)
        except Exception:
            df_m5['Trend_H1_Bull'] = 0
            df_m5['Trend_H1_Strong'] = 0
            h1_bull = False
    else:
        df_m5['Trend_H1_Bull'] = 0
        df_m5['Trend_H1_Strong'] = 0
        h1_bull = False

    # Level Struktural Multi-Day dari M15 (Lookback 40 candle = 10 jam)
    m15_sup = float(df_m5['low'].min())
    m15_res = float(df_m5['high'].max())
    if rates_m15 is not None and len(rates_m15) > 0:
        try:
            df_m15 = pd.DataFrame(rates_m15)
            df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
            df_m15.set_index('time', inplace=True)
            df_m15['M15_Resistance'] = df_m15['high'].shift(1).rolling(40).max()
            df_m15['M15_Support']    = df_m15['low'].shift(1).rolling(40).min()
            df_m5['M15_Resistance'] = df_m15['M15_Resistance'].reindex(df_m5.index, method='ffill')
            df_m5['M15_Support']    = df_m15['M15_Support'].reindex(df_m5.index, method='ffill')
            if not df_m5['M15_Support'].dropna().empty:
                m15_sup = float(df_m5['M15_Support'].dropna().iloc[-1])
            if not df_m5['M15_Resistance'].dropna().empty:
                m15_res = float(df_m5['M15_Resistance'].dropna().iloc[-1])
        except Exception:
            pass

    # DXY MT5 0-Delay
    try:
        mt5.symbol_select('DXY', True)
        rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M5, 0, 1000)
        if rates_dxy is not None and len(rates_dxy) > 0:
            df_dxy = pd.DataFrame(rates_dxy)
            df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
            df_dxy.set_index('time', inplace=True)
            dxy_close = df_dxy['close']
        else:
            dxy_close = pd.Series(100.0, index=df_m5.index)
    except Exception:
        dxy_close = pd.Series(100.0, index=df_m5.index)

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
        return 50.0, 50.0, False, False, 5.0, 0.0, 0.0, 0.01, 0.01, 0.0, 0.0, False, False, 0.0, 0.0, fallback_struct, fallback_channel, fallback_pattern, fallback_tech

    latest_row = df_clean[features].iloc[[-1]].astype(float)
    probs = model.predict_proba(latest_row)[0]
    prob_down = probs[0] * 100.0
    prob_up   = probs[1] * 100.0

    latest_atr = df_clean['ATR_14'].iloc[-1]
    if pd.isna(latest_atr) or latest_atr <= 0:
        latest_atr = 5.0

    h1_bull = df_clean['Trend_H1_Bull'].iloc[-1] == 1
    
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
    
    struct_data = detect_candle_structure(df_clean)
    
    # Deteksi Kanal Regresi Linear Dinamis M5 (Support & Resisten Miring / Dynamic Trendlines)
    slope, dyn_sup, dyn_res, channel_type, dist_dyn_sup, dist_dyn_res = calc_dynamic_channel(df_clean, lookback=40)
    channel_data = {
        'slope': slope,
        'dyn_sup': dyn_sup,
        'dyn_res': dyn_res,
        'dyn_support': dyn_sup,
        'dyn_resistance': dyn_res,
        'channel_type': channel_type,
        'dist_dyn_sup': dist_dyn_sup,
        'dist_dyn_res': dist_dyn_res
    }
    
    # Deteksi Multi-Horizon SNR & Pola Grafik Teknikal M5 (Lookback 700 lilin / ~58 jam)
    pattern_data = detect_multi_horizon_snr_and_patterns(df_m5, lookback_multiday=700, lookback_pattern=60)
    
    # Deteksi Indikator Teknikal Lengkap (Stochastic RSI, RSI, BB, EMA)
    tech_data = calc_technical_indicators(df_m5)
    
    return prob_up, prob_down, m30_bull, h1_bull, latest_atr, live_ask, live_bid, dist_m15_sup, dist_m15_res, lower_wick, upper_wick, is_bull_candle, is_bear_candle, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data

def evaluate_multi_zone_m5_decision(prob_up, prob_down, m30_bull, h1_bull, atr_val, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data=None, pattern_data=None, tech_data=None):
    """
    Evaluasi Keputusan Multi-Zone Adaptive Scalping M5 (Versi 3.3 - Technical Confluence Suite):
    - Konfluensi Lengkap: Stochastic RSI (14,14,3,3), RSI(14), Bollinger Bands, EMA 20/50
    - Anti-Oversold Guard: DILARANG SELL jika Stoch RSI <= 25% (Mencegah kerugian entry prematur di dasar)
    - Anti-Overbought Guard: DILARANG BUY jika Stoch RSI >= 75% (Mencegah beli di pucuk jenuh)
    - Confluence Booster: Turunkan batas AI ke >= 50% saat Stoch Overbought di resisten atau Oversold di support
    - Multi-Horizon SNR (2-4 Hari) + Chart Patterns (Wedge/Channels)
    - Anti-Collision Guard: DILARANG SELL mepet Lantai Demand (<= 0.18%), DILARANG BUY mepet Atap Supply (<= 0.18%)
    - Zona A: Boundary Bounce (dist <= 0.12%)
    - Zona B: Proximity Opportunity (0.12% < dist <= 0.30%)
    - Zona C: High-Prob Trend Scalp (> 0.30%)
    """
    slope = channel_data.get('slope', 0.0) if channel_data else 0.0
    dyn_sup = channel_data.get('dyn_sup', m15_sup) if channel_data else m15_sup
    dyn_res = channel_data.get('dyn_res', m15_res) if channel_data else m15_res
    dist_dyn_sup = channel_data.get('dist_dyn_sup', 999.0) if channel_data else 999.0
    dist_dyn_res = channel_data.get('dist_dyn_res', 999.0) if channel_data else 999.0
    channel_type = channel_data.get('channel_type', 'HORIZONTAL') if channel_data else 'HORIZONTAL'
    
    # Ekstraksi Indikator Teknikal Lengkap
    stoch_k = tech_data.get('stoch_k', 50.0) if tech_data else 50.0
    stoch_d = tech_data.get('stoch_d', 50.0) if tech_data else 50.0
    rsi_val = tech_data.get('rsi', 50.0) if tech_data else 50.0
    bb_pos = tech_data.get('bb_pos', 0.5) if tech_data else 0.5
    is_ema_bull = tech_data.get('is_ema_bull', True) if tech_data else True
    stoch_oversold = tech_data.get('stoch_oversold', False) if tech_data else False
    stoch_overbought = tech_data.get('stoch_overbought', False) if tech_data else False
    stoch_bull_cross = tech_data.get('stoch_bull_cross', False) if tech_data else False
    stoch_bear_cross = tech_data.get('stoch_bear_cross', False) if tech_data else False
    
    has_sell_confluence = stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or ('BEARISH' in (pattern_data.get('pattern_bias', '') if pattern_data else ''))
    has_buy_confluence  = stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or ('BULLISH' in (pattern_data.get('pattern_bias', '') if pattern_data else ''))
    
    # 1. EVALUASI DEMAND/SUPPORT (BUY):
    if abs(slope) > 0.06 and dist_dyn_sup < dist_sup:
        effective_dist_sup = dist_dyn_sup
        sup_type = "Support Miring"
        sup_label = f"Support Miring (${dyn_sup:.2f})"
        is_diag_sup = True
    else:
        effective_dist_sup = dist_sup
        sup_type = "Demand Horizontal"
        sup_label = f"Demand Horizontal (${m15_sup:.2f})"
        is_diag_sup = False
        
    # 2. EVALUASI SUPPLY/RESISTEN (SELL):
    if abs(slope) > 0.06 and dist_dyn_res < dist_res:
        effective_dist_res = dist_dyn_res
        res_type = "Resisten Miring"
        res_label = f"Resisten Miring (${dyn_res:.2f})"
        is_diag_res = True
    else:
        effective_dist_res = dist_res
        res_type = "Supply Horizontal"
        res_label = f"Supply Horizontal (${m15_res:.2f})"
        is_diag_res = False

    # -----------------------------------------------------------------
    # A. EVALUASI KANDIDAT SELL (ATAP SUPPLY / RESISTENSI)
    # -----------------------------------------------------------------
    sell_candidate = None
    
    # 🛡️ ANTI-OVERSOLD GUARD: Dilarang SELL jika Stoch RSI sudah di dasar jenuh jual (<= 25%)
    # KECUALI jika terjadi Breakdown Impulsif / Tembus Level Mayor dengan lilin Marubozu solid!
    if stoch_oversold and not (is_bear_c and (upper_w <= 0.15 or struct_data.get('is_impulse_bear', False))):
        sell_candidate = ("WAIT", "OVERSOLD", 0, 0, f"🛑 OVERSOLD FILTER: SELL Dibatalkan! Stoch RSI di dasar (%K={stoch_k:.1f} <= 25). Risiko pantulan rebound tinggi!")
    elif effective_dist_res <= ZONE_A_THRESHOLD:
        # Konfluensi Indikator Overbought di Resisten: turunkan ambang batas AI
        has_sell_confluence = stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or ('BEARISH' in pattern_data.get('pattern_bias', ''))
        confluence_tag = f" [Stoch Overbought: %K={stoch_k:.1f}]" if stoch_overbought else (f" [Stoch Bear Cross]" if stoch_bear_cross else (f" [BB Atap: {bb_pos*100:.0f}%]" if bb_pos >= 0.75 else ""))
        
        if has_sell_confluence:
            min_p_sell = 50.0  # Konfluensi teknikal kuat di resisten! Model cukup konfirmasi >= 50%
        elif (is_diag_res or upper_w >= 0.30):
            min_p_sell = 54.0
        else:
            min_p_sell = ZONE_A_PROB_MIN

        if prob_down >= min_p_sell:
            if ((upper_w >= 0.18) or (is_bear_c and (has_sell_confluence or struct_data.get('is_impulse_bear', False) or 'TRIANGLE' in pattern_data.get('pattern', '')))):
                if pattern_data and not pattern_data.get('can_sell_safely', True):
                    near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                    dist_sup_pct = pattern_data.get('dist_near_sup', 0.0) * 100
                    sell_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona A Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f}, Jarak {dist_sup_pct:.2f}% <= {COLLISION_DISTANCE_MIN*100:.2f}%). Risiko Pantulan Kuat!")
                else:
                    zone_tag = "A-Diag" if is_diag_res else "A-Horiz"
                    sell_candidate = ("SELL", zone_tag, QUICK_TP_USD, MAX_CUTLOSS_USD, f"🔴 ZONA A SELL: Penolakan Valid di {res_label}{confluence_tag} (Kanal {channel_type}, Slope ${slope:.2f})! Wick {upper_w*100:.1f}%, Prob {prob_down:.1f}%.")
            else:
                sell_candidate = ("WAIT", "A", 0, 0, f"Zona A {res_type}: Menunggu Ekor Rejection Atas ({upper_w*100:.1f}% < 20%)")
        else:
            sell_candidate = ("WAIT", "A", 0, 0, f"Zona A {res_type}: Prob SELL ({prob_down:.1f}%) < {min_p_sell:.0f}%")

    elif effective_dist_res <= ZONE_B_THRESHOLD:
        has_sell_confluence = stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or ('BEARISH' in pattern_data.get('pattern_bias', ''))
        confluence_tag = f" [Stoch Overbought: %K={stoch_k:.1f}]" if stoch_overbought else (f" [Stoch Bear Cross]" if stoch_bear_cross else "")
        
        if has_sell_confluence:
            min_p_sell = 52.0
        elif (upper_w >= 0.30 or is_diag_res):
            min_p_sell = 58.0
        else:
            min_p_sell = ZONE_B_PROB_MIN

        if prob_down >= min_p_sell:
            has_wick = upper_w >= ZONE_B_WICK_MIN
            has_lh   = struct_data.get('is_lower_high', False) or is_bear_c or has_sell_confluence
            if (has_wick or has_lh) and not (is_bull_c and upper_w < 0.15):
                if pattern_data and not pattern_data.get('can_sell_safely', True):
                    near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                    dist_sup_pct = pattern_data.get('dist_near_sup', 0.0) * 100
                    sell_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona B Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f}, Jarak {dist_sup_pct:.2f}%).")
                else:
                    zone_tag = "B-Diag" if is_diag_res else "B-Horiz"
                    sell_candidate = ("SELL", zone_tag, 1.80, 1.50, f"🔴 ZONA B SELL (PROXIMITY): Struktur Lower High / Rejection Dekat {res_label}{confluence_tag}! Prob {prob_down:.1f}%.")
            else:
                sell_candidate = ("WAIT", "B", 0, 0, f"Zona B {res_type}: Menunggu konfirmasi pola candle / Lower High (Ekor {upper_w*100:.1f}% < 15%)")
        else:
            sell_candidate = ("WAIT", "B", 0, 0, f"Zona B {res_type}: Prob SELL ({prob_down:.1f}%) < {min_p_sell:.0f}%")

    # -----------------------------------------------------------------
    # B. EVALUASI KANDIDAT BUY (LANTAI DEMAND / SUPPORT)
    # -----------------------------------------------------------------
    buy_candidate = None
    
    # 🛡️ ANTI-OVERBOUGHT GUARD: Dilarang BUY jika Stoch RSI sudah di pucuk jenuh beli (>= 75%)
    # KECUALI jika terjadi Breakout Impulsif tembus atap mayor!
    if stoch_overbought and not (is_bull_c and (lower_w <= 0.15 or struct_data.get('is_impulse_bull', False))):
        buy_candidate = ("WAIT", "OVERBOUGHT", 0, 0, f"🛑 OVERBOUGHT FILTER: BUY Dibatalkan! Stoch RSI di puncak (%K={stoch_k:.1f} >= 75). Risiko pembalikan drop tinggi!")
    elif effective_dist_sup <= ZONE_A_THRESHOLD:
        # Konfluensi Indikator Oversold di Support: turunkan ambang batas AI
        has_buy_confluence = stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or ('BULLISH' in pattern_data.get('pattern_bias', ''))
        confluence_tag = f" [Stoch Oversold: %K={stoch_k:.1f}]" if stoch_oversold else (f" [Stoch Bull Cross]" if stoch_bull_cross else (f" [BB Dasar: {bb_pos*100:.0f}%]" if bb_pos <= 0.25 else ""))
        
        if has_buy_confluence:
            min_p_buy = 50.0  # Konfluensi teknikal kuat di support! Model cukup konfirmasi >= 50%
        elif (is_diag_sup or lower_w >= 0.30):
            min_p_buy = 54.0
        else:
            min_p_buy = ZONE_A_PROB_MIN

        if prob_up >= min_p_buy:
            if lower_w >= 0.20 and (is_bull_c or lower_w >= 0.30 or has_buy_confluence):
                if pattern_data and not pattern_data.get('can_buy_safely', True):
                    near_res_val = pattern_data.get('nearest_res', m15_res)
                    dist_res_pct = pattern_data.get('dist_near_res', 0.0) * 100
                    buy_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona A Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f}, Jarak {dist_res_pct:.2f}% <= {COLLISION_DISTANCE_MIN*100:.2f}%). Risiko Benturan Plafon!")
                else:
                    zone_tag = "A-Diag" if is_diag_sup else "A-Horiz"
                    buy_candidate = ("BUY", zone_tag, QUICK_TP_USD, MAX_CUTLOSS_USD, f"🟢 ZONA A BUY: Pantulan Valid di {sup_label}{confluence_tag} (Kanal {channel_type}, Slope +${slope:.2f})! Wick {lower_w*100:.1f}%, Prob {prob_up:.1f}%.")
            else:
                buy_candidate = ("WAIT", "A", 0, 0, f"Zona A {sup_type}: Menunggu Ekor Rejection Bawah ({lower_w*100:.1f}% < 20%)")
        else:
            buy_candidate = ("WAIT", "A", 0, 0, f"Zona A {sup_type}: Prob BUY ({prob_up:.1f}%) < {min_p_buy:.0f}%")

    elif effective_dist_sup <= ZONE_B_THRESHOLD:
        has_buy_confluence = stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or ('BULLISH' in pattern_data.get('pattern_bias', ''))
        confluence_tag = f" [Stoch Oversold: %K={stoch_k:.1f}]" if stoch_oversold else (f" [Stoch Bull Cross]" if stoch_bull_cross else "")
        
        if has_buy_confluence:
            min_p_buy = 52.0
        elif (lower_w >= 0.30 or is_diag_sup):
            min_p_buy = 58.0
        else:
            min_p_buy = ZONE_B_PROB_MIN

        # 🛡️ ANTI-FALLING-KNIFE GUARD M5: Dilarang Buy di tengah pisau jatuh saat kanal crash
        is_steep_crash = (slope < -0.30) or (struct_data.get('market_regime') == 'TRENDING_BEAR')
        has_knife_reversal = (lower_w >= 0.35) or (is_bull_c and (has_buy_confluence or struct_data.get('is_impulse_bull', False)))

        if prob_up >= min_p_buy:
            if is_steep_crash and not has_knife_reversal:
                buy_candidate = ("WAIT", "FALLING_KNIFE", 0, 0, f"🛑 ANTI-FALLING-KNIFE: BUY Zona B Dibatalkan! Downtrend Curam (Slope ${slope:.2f}). Dilarang Buy lilin merah tanpa Bullish Hammer (Ekor {lower_w*100:.1f}% < 35%)!")
            else:
                has_wick = lower_w >= ZONE_B_WICK_MIN
                has_hl   = struct_data.get('is_higher_low', False) or is_bull_c or has_buy_confluence
                if (has_wick or has_hl) and not (is_bear_c and lower_w < 0.15):
                    if pattern_data and not pattern_data.get('can_buy_safely', True):
                        near_res_val = pattern_data.get('nearest_res', m15_res)
                        dist_res_pct = pattern_data.get('dist_near_res', 0.0) * 100
                        buy_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona B Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f}, Jarak {dist_res_pct:.2f}%).")
                    else:
                        zone_tag = "B-Diag" if is_diag_sup else "B-Horiz"
                        buy_candidate = ("BUY", zone_tag, 1.80, 1.50, f"🟢 ZONA B BUY (PROXIMITY): Struktur Higher Low / Rebound Dekat {sup_label}{confluence_tag}! Prob {prob_up:.1f}%.")
                else:
                    buy_candidate = ("WAIT", "B", 0, 0, f"Zona B {sup_type}: Menunggu konfirmasi pola candle / Higher Low (Ekor {lower_w*100:.1f}% < 15%)")
        else:
            buy_candidate = ("WAIT", "B", 0, 0, f"Zona B {sup_type}: Prob BUY ({prob_up:.1f}%) < {min_p_buy:.0f}%")

    # -----------------------------------------------------------------
    # C. SELEKSI KEPUTUSAN TERBAIK BERDASARKAN MODEL-BIASED PRIORITY
    # (Hanya return jika ADA SINYAL EKSEKUSI REAL. Jangan batalkan Zona C karena pesan WAIT!)
    # -----------------------------------------------------------------
    if prob_down >= prob_up:
        if sell_candidate and sell_candidate[0] == "SELL":
            return sell_candidate
        if buy_candidate and buy_candidate[0] == "BUY":
            return buy_candidate
    else:
        if buy_candidate and buy_candidate[0] == "BUY":
            return buy_candidate
        if sell_candidate and sell_candidate[0] == "SELL":
            return sell_candidate

    # -----------------------------------------------------------------
    # D. EVALUASI ZONA C: HIGH-PROB TREND SCALP (> 0.30%)
    # -----------------------------------------------------------------
    is_tight = struct_data.get('market_regime') == 'SIDEWAYS_TIGHT'
    min_c_buy  = 54.0 if (has_buy_confluence or 'BULLISH' in pattern_data.get('pattern_bias', '')) else ZONE_C_PROB_MIN
    min_c_sell = 54.0 if (has_sell_confluence or 'BEARISH' in pattern_data.get('pattern_bias', '')) else ZONE_C_PROB_MIN

    if prob_up >= min_c_buy and not is_tight:
        if stoch_overbought:
            return "WAIT", "OVERBOUGHT", 0, 0, f"🛑 OVERBOUGHT FILTER: BUY Zona C Dibatalkan! Stoch RSI di puncak (%K={stoch_k:.1f} >= 75)."
        has_structure = (
            struct_data.get('bos_bull_recent', False) or 
            struct_data.get('choch_bull_recent', False) or 
            struct_data.get('market_regime') == 'TRENDING_BULL' or
            is_ema_bull
        )
        if (m30_bull or h1_bull) and has_structure and is_bull_c:
            if pattern_data and not pattern_data.get('can_buy_safely', True):
                near_res_val = pattern_data.get('nearest_res', m15_res)
                return "WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona C Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f})."
            return "BUY", "C", 1.60, 1.40, f"🟢 ZONA C BUY (TREND SCALP): Keyakinan AI Sangat Kuat ({prob_up:.1f}%) + Momentum Bullish M30/H1 + Konfirmasi EMA/Structure!"
        else:
            return "WAIT", "C", 0, 0, f"Zona C Mid: BUY {prob_up:.1f}% menunggu konfirmasi candle/tren M30/H1"

    elif prob_down >= min_c_sell and not is_tight:
        if stoch_oversold:
            return "WAIT", "OVERSOLD", 0, 0, f"🛑 OVERSOLD FILTER: SELL Zona C Dibatalkan! Stoch RSI di dasar (%K={stoch_k:.1f} <= 25)."
        has_structure = (
            struct_data.get('bos_bear_recent', False) or 
            struct_data.get('choch_bear_recent', False) or 
            struct_data.get('market_regime') == 'TRENDING_BEAR' or
            not is_ema_bull
        )
        if ((not m30_bull) or (not h1_bull)) and has_structure and is_bear_c:
            if pattern_data and not pattern_data.get('can_sell_safely', True):
                near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                return "WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona C Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f})."
            return "SELL", "C", 1.60, 1.40, f"🔴 ZONA C SELL (TREND SCALP): Keyakinan AI Sangat Kuat ({prob_down:.1f}%) + Momentum Bearish M30/H1 + Konfirmasi EMA/Structure!"
        else:
            return "WAIT", "C", 0, 0, f"Zona C Mid: SELL {prob_down:.1f}% menunggu konfirmasi candle/tren M30/H1"

    else:
        max_p = max(prob_up, prob_down)
        channel_desc = f"Kanal {channel_type} (Slope ${slope:.2f})"
        pattern_desc = f" | Pola: {pattern_data.get('pattern', 'None')}" if pattern_data else ""
        stoch_desc = f" | Stoch: %K={stoch_k:.0f}"
        return "WAIT", "C", 0, 0, f"TERTAHAN MID-ZONE: Area antara {sup_label} & {res_label} [{channel_desc}{pattern_desc}{stoch_desc}]. AI ({max_p:.1f}%) < {ZONE_C_PROB_MIN:.0f}%."

def execute_auto_trade(signal_type, entry_price, zone_type="A"):
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
        if pnl_recent <= 0.40:
            print(f"⚠️ STACKING DITAHAN: Posisi sebelumnya (#{pos_recent.ticket}) belum profit aman (Floating: ${pnl_recent:+.2f}). Dilarang Averaging Down!")
            return

    layer_num = len(my_positions) + 1
    if layer_num > 1:
        print(f"🔥 SAFE STACKING LAYER #{layer_num} ({signal_type} ZONA {zone_type}): Menambah layer posisi saat posisi lama sudah profit!")

    order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if signal_type == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    # Emergency Broker Disaster Stop Loss (-$2.50 USD / 25 pips di broker)
    emergency_dist = EMERGENCY_SL_USD / (LOT_SIZE * 100.0)
    sl = price - emergency_dist if signal_type == "BUY" else price + emergency_dist
    tp = price + 10.0 if signal_type == "BUY" else price - 10.0
        
    filling_mode = get_best_filling_mode(symbol)
    order_comment_zone = f"M5 v3.2 Z-{zone_type}"
        
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
        "comment": order_comment_zone,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    color_order = COLOR_GREEN if signal_type == "BUY" else COLOR_RED
    print(f"{color_order}{COLOR_BOLD}🚀 [OPEN {signal_type} - ZONA {zone_type}] MENGIRIM ORDER SCALPING M5: {signal_type} {LOT_SIZE} Lot XAUUSD @ ${price:.2f} (SL: ${sl:.2f}){COLOR_RESET}")
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{color_order}{COLOR_BOLD}🎉 ORDER M5 SCALPING {signal_type} (ZONA {zone_type}) BERHASIL! (Layer {layer_num}/{MAX_STACKED_POSITIONS}){COLOR_RESET}")
    else:
        print(f"❌ Gagal Eksekusi Order M5. Retcode: {result.retcode} ({result.comment})")

def main():
    global _lock_socket
    # Proteksi Single Instance: Mencegah 2 script berjalan sekaligus dengan auto-reuse
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _lock_socket.bind(("127.0.0.1", 41235))
    except socket.error:
        # Cek apakah proses lain benar-benar aktif atau hanya port TIME_WAIT sesaat
        import psutil
        curr_pid = os.getpid()
        other_running = False
        for p in psutil.process_iter(['pid', 'cmdline']):
            try:
                if p.info['pid'] != curr_pid and p.info['cmdline']:
                    cmd_s = " ".join(p.info['cmdline'])
                    if "Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py" in cmd_s:
                        other_running = True
                        break
            except Exception:
                pass
        if other_running:
            print("\n❌ [SINGLE INSTANCE PROTECTION] Bot M5 sudah berjalan di proses lain!")
            print("Mencegah eksekusi ganda yang dapat menyebabkan over-trading/drawdown.")
            sys.exit(0)
        else:
            # Port hanya tertahan TIME_WAIT sesaat, tunggu 1 detik dan bind ulang
            time.sleep(1)
            try:
                _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                _lock_socket.bind(("127.0.0.1", 41235))
            except Exception:
                pass

    print("\n" + "="*85)
    print(f"🤖 ROBOT TRADING M5 MULTI-ZONE SCALPER [{BOT_VERSION}]")
    print("Fitur: 3 Zona Entry (A:Boundary, B:Proximity, C:Trend) + Candle Structure HL/LH")
    print(f"Target Scalp: TP Dinamis ($1.50 - $2.00) | Hard Cut-Loss (-$1.20 s/d -$1.80)")
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
            model_label=MODEL_LABEL_EXCEL,
            sheet_title="Trade Log M5 Scalping",
            threshold_label=THRESHOLD_LABEL_EXCEL
        )
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi awal Excel M5: {e}")

    # Audit awal kondisi pasar & prediksi model M5 saat pertama kali dibuka
    print(f"\n{COLOR_CYAN}🔍 MELAKUKAN AUDIT AWAL STRUKTUR SMC & PREDIKSI MODEL M5 SCALPER...{COLOR_RESET}")
    res_audit = analyze_market_and_predict()
    latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data = res_audit
    
    init_sig, init_zone, init_tp, init_cl, init_reason = evaluate_multi_zone_m5_decision(
        latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val,
        dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c,
        m15_sup, m15_res, struct_data, channel_data=channel_data, pattern_data=pattern_data, tech_data=tech_data
    )

    slope_val = channel_data['slope']
    channel_str = f"{channel_data['channel_type']} (Slope: ${slope_val:+.2f}/candle)"
    dyn_sup_str = f"${channel_data['dyn_sup']:.2f} (Jarak: {channel_data['dist_dyn_sup']*100:.2f}%)"
    dyn_res_str = f"${channel_data['dyn_res']:.2f} (Jarak: {channel_data['dist_dyn_res']*100:.2f}%)"

    print("="*85)
    print(f"📊 HASIL AUDIT STRUKTUR PASAR M5 (TECHNICAL CONFLUENCE SCALPER v3.3):")
    print(f"• Probabilitas AI M5       : BUY = {latest_prob_up:.1f}%  |  SELL = {latest_prob_down:.1f}% (A:56%, B:62%, C:66%)")
    print(f"• Indikator Teknikal       : {tech_data['summary_desc']}")
    print(f"• Tren Pendukung Multi-TF  : M30={'BULL' if m30_bull else 'BEAR'} | H1={'BULL' if h1_bull else 'BEAR'}")
    print(f"• Pola Grafik Teknikal     : {pattern_data['pattern']}")
    print(f"• Kanal Regresi Dinamis M5 : {channel_str}")
    print(f"• Support Miring (Kanal)   : {dyn_sup_str}")
    print(f"• Resisten Miring (Kanal)  : {dyn_res_str}")
    print(f"• Lantai Demand Multi-Day  : ${pattern_data['major_demand']:.2f} | Atap Supply Multi-Day: ${pattern_data['major_supply']:.2f}")
    print(f"• Pivot Terdekat (1-2 Hari): Swing Sup = ${pattern_data['nearest_sup']:.2f} ({pattern_data['dist_near_sup']*100:.2f}%) | Swing Res = ${pattern_data['nearest_res']:.2f} ({pattern_data['dist_near_res']*100:.2f}%)")
    print(f"• Anti-Collision Guard     : Aman BUY? {'✅ Ya' if pattern_data['can_buy_safely'] else '🛑 Bahaya (Dekat Atap)'} | Aman SELL? {'✅ Ya' if pattern_data['can_sell_safely'] else '🛑 Bahaya (Dekat Lantai)'}")
    print(f"• Karakteristik Candle M5  : Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}%")
    print(f"• Pola Struktur & Regime   : {struct_data['structure_desc']}")
    print(f"• Status Evaluasi Pasar    : {init_reason}")
    print(f"• Waktu Eksekusi Order     : Menunggu 5 detik sebelum tutup candle ({CHOSEN_TF})")
    print("="*85 + "\n")

    tf_min = 5
    last_analyzed_candle = None
    prev_m5_count = 0
    last_periodic_sync = time.time()
    last_prob_refresh = time.time()

    # --- 🚀 STARTUP CATCH-UP SCAN M5 (Tidak buang waktu tunggu jika PC baru dinyalakan) ---
    now = datetime.now()
    minutes_past = now.minute % tf_min
    seconds_past = minutes_past * 60 + now.second
    current_candle_time = now.replace(second=0, microsecond=0) - timedelta(minutes=minutes_past)

    print(f"{COLOR_CYAN}🔎 [STARTUP CATCH-UP SCAN M5] Memeriksa Peluang Segar Candle Terakhir...{COLOR_RESET}")
    all_positions = mt5.positions_get(symbol=symbol)
    my_cur_pos = [p for p in (all_positions or []) if p.magic == MAGIC_NUMBER]
    
    if len(my_cur_pos) > 0:
        print(f"ℹ️ Sedang ada posisi aktif M5 ({len(my_cur_pos)} posisi). Startup scan melewati eksekusi baru.")
    else:
        if init_sig in ["BUY", "SELL"] and seconds_past <= 60:
            print(f"{COLOR_GREEN}{COLOR_BOLD}⚡ [STARTUP CATCH-UP TRIGGER M5]: Candle baru berjalan {seconds_past}s dan terdeteksi Sinyal Valid {init_sig} (Zona {init_zone})!{COLOR_RESET}")
            print(f"   Alasan: {init_reason}")
            if AUTO_EXECUTE:
                entry_p = ask_p if init_sig == "BUY" else bid_p
                execute_auto_trade(init_sig, entry_p, zone_type=init_zone)
                last_analyzed_candle = current_candle_time
        elif init_sig in ["BUY", "SELL"]:
            print(f"ℹ️ Sinyal {init_sig} terdeteksi, namun candle M5 sudah berjalan {minutes_past}m {now.second}s (>1 menit). Menunggu tutup candle untuk presisi.")
        else:
            print(f"ℹ️ Status saat startup M5: {init_reason}. Bot standby memantau real-time.")

    while True:
        try:
            # 1. LOOP REAL-TIME: Pantau exit dinamis setiap detik
            manage_open_positions(
                latest_prob_up, latest_prob_down,
                channel_data=channel_data,
                pattern_data=pattern_data,
                struct_data=struct_data,
                m30_bull=m30_bull,
                h1_bull=h1_bull
            )

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
                        model_label=MODEL_LABEL_EXCEL,
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=THRESHOLD_LABEL_EXCEL
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel M5: {sync_err}")

            prev_m5_count = active_m5_count

            # Sinkronisasi berkala ke Excel setiap 60 detik (Real-time safety, mode silent)
            if time.time() - last_periodic_sync >= 60:
                last_periodic_sync = time.time()
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_M5_PATH,
                        filter_new_model_only=True,
                        magic_number=MAGIC_NUMBER,
                        comment_filter=None,
                        model_label=MODEL_LABEL_EXCEL,
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=THRESHOLD_LABEL_EXCEL,
                        silent=True
                    )
                except Exception:
                    pass

            # Perbarui probabilitas live setiap 15 detik untuk audit transparan
            if time.time() - last_prob_refresh >= 15:
                last_prob_refresh = time.time()
                try:
                    res_audit = analyze_market_and_predict()
                    latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data = res_audit
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
            
            # Format probabilitas live berwarna
            prob_color = COLOR_GREEN if latest_prob_up >= ZONE_A_PROB_MIN else (COLOR_RED if latest_prob_down >= ZONE_A_PROB_MIN else COLOR_YELLOW)
            prob_display = f"{prob_color}BUY:{latest_prob_up:.1f}% | SELL:{latest_prob_down:.1f}%{COLOR_RESET}"

            # Status tampilan di console
            if active_m5_count > 0:
                pos_dir = "BUY" if my_pos[0].type == 0 else "SELL"
                if pos_dir == "BUY":
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}ACTIVE BUY ({active_m5_count}/{MAX_STACKED_POSITIONS}){COLOR_RESET}{pnl_str}"
                else:
                    status_str = f"{COLOR_RED}{COLOR_BOLD}ACTIVE SELL ({active_m5_count}/{MAX_STACKED_POSITIONS}){COLOR_RESET}{pnl_str}"
            else:
                live_sig, live_zone, _, _, live_reason = evaluate_multi_zone_m5_decision(
                    latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val,
                    dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c,
                    m15_sup, m15_res, struct_data, channel_data=channel_data, pattern_data=pattern_data, tech_data=tech_data
                )
                if live_sig == "BUY":
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}SIAP BUY (ZONA {live_zone}){COLOR_RESET}"
                elif live_sig == "SELL":
                    status_str = f"{COLOR_RED}{COLOR_BOLD}SIAP SELL (ZONA {live_zone}){COLOR_RESET}"
                else:
                    if "COLLISION" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}ANTI-COLLISION (MEPET SNR){COLOR_RESET}"
                    elif "MIRING" in live_reason.upper() or "KANAL" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}KANAL MIRING (TUNGGU SETUP){COLOR_RESET}"
                    elif "PROXIMITY" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}PROXIMITY (TUNGGU STRUKTUR){COLOR_RESET}"
                    elif "DEMAND" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}DEMAND (TUNGGU WICK){COLOR_RESET}"
                    elif "SUPPLY" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}SUPPLY (TUNGGU WICK){COLOR_RESET}"
                    else:
                        status_str = f"{COLOR_YELLOW}TERTAHAN MID-ZONE{COLOR_RESET}"

            stoch_k_val = tech_data.get('stoch_k', 50.0) if tech_data else 50.0
            stoch_disp = f"Stoch:{stoch_k_val:.0f}"
            sys.stdout.write(f"\r⏳ [{CHOSEN_TF}]: {mins:02d}m {secs:02d}s | {prob_display} | {stoch_disp} | Status: {status_str}   ")
            sys.stdout.flush()
            
            # 2. TRIGGER CANDLE: Tepat 5 detik sebelum tutup candle M5 (0-delay)
            if seconds_left <= 5 and last_analyzed_candle != current_candle_time:
                last_analyzed_candle = current_candle_time
                print("\n" + "="*85)
                print(f"⚡ CANDLE M5 TUTUP ({now.strftime('%H:%M:%S')})! EVALUASI MULTI-ZONE SCALPING M5:")
                
                res_audit = analyze_market_and_predict()
                latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data = res_audit
                
                final_sig, final_zone, final_tp, final_cl, final_reason = evaluate_multi_zone_m5_decision(
                    latest_prob_up, latest_prob_down, m30_bull, h1_bull, atr_val,
                    dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c,
                    m15_sup, m15_res, struct_data, channel_data=channel_data, pattern_data=pattern_data, tech_data=tech_data
                )
                
                print(f"📊 Probabilitas Model : BUY = {latest_prob_up:.1f}%  |  SELL = {latest_prob_down:.1f}%")
                print(f"📈 Indikator Teknikal : {tech_data['summary_desc']}")
                print(f"📐 Struktur Level SNR : Lantai Demand = ${m15_sup:.2f} ({dist_sup*100:.2f}%) | Atap Supply = ${m15_res:.2f} ({dist_res*100:.2f}%)")
                print(f"🛡️ Level Pivot Mayor  : Swing Sup = ${pattern_data['nearest_sup']:.2f} ({pattern_data['dist_near_sup']*100:.2f}%) | Swing Res = ${pattern_data['nearest_res']:.2f} ({pattern_data['dist_near_res']*100:.2f}%)")
                print(f"🕯️ Karakter Candlestick: Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}%")
                print(f"📈 Pola Struktur SMC  : {struct_data['structure_desc']}")
                print(f"📐 Pola Grafik Teknikal: {pattern_data['pattern']}")
                sup_miring_val = channel_data.get('dyn_sup', channel_data.get('dyn_support', 0.0))
                res_miring_val = channel_data.get('dyn_res', channel_data.get('dyn_resistance', 0.0))
                slope_m5_val = channel_data.get('slope', 0.0)
                ch_type_m5 = channel_data.get('channel_type', 'HORIZONTAL')
                print(f"📐 Kanal Regresi M5   : {ch_type_m5} (Slope: {slope_m5_val:+.3f} $/c, Sup Miring: ${sup_miring_val:.2f}, Res Miring: ${res_miring_val:.2f})")
                print(f"🛡️ Anti-Collision Guard: Safe BUY? {'✅ Ya' if pattern_data['can_buy_safely'] else '🛑 Tidak (Dekat Atap)'} | Safe SELL? {'✅ Ya' if pattern_data['can_sell_safely'] else '🛑 Tidak (Dekat Lantai)'}")
                
                if final_sig in ["BUY", "SELL"]:
                    color_sig = COLOR_GREEN if final_sig == "BUY" else COLOR_RED
                    print(f"{color_sig}{COLOR_BOLD}🎯 KEPUTUSAN {final_sig} (ZONA {final_zone}): {final_reason}{COLOR_RESET}")
                    entry_p = ask_p if final_sig == "BUY" else bid_p
                    if AUTO_EXECUTE:
                        execute_auto_trade(final_sig, entry_p, zone_type=final_zone)
                else:
                    print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN: {final_reason}{COLOR_RESET}")
                
                # Sinkronisasi ke Excel khusus M5 Scalping
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_M5_PATH,
                        filter_new_model_only=True,
                        magic_number=MAGIC_NUMBER,
                        comment_filter=None,
                        model_label=MODEL_LABEL_EXCEL,
                        sheet_title="Trade Log M5 Scalping",
                        threshold_label=THRESHOLD_LABEL_EXCEL
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel M5: {sync_err}")
                print("="*85)
                
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nRobot Trading M5 Scalping Dihentikan oleh User.")
            mt5.shutdown()
            break
        except Exception as loop_err:
            print(f"\n⚠️ [SHIELD M5] Gangguan loop sementara: {loop_err}. Memulihkan dalam 2 detik...")
            time.sleep(2)

if __name__ == "__main__":
    main()
