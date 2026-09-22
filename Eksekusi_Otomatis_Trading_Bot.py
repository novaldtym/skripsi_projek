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
import Macro_Economic_News_Engine as macro_news
import Scenario_Evaluator_Engine as scenario_eval

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
# ⚙️ PENGATURAN ROBOT TRADING OTOMATIS M15 (MULTI-ZONE ADAPTIVE ENTRY)
# =========================================================================
CHOSEN_TF              = "M15"      # Timeframe Utama: M15
FORWARD_CANDLES        = 5          # Horizon Prediksi: 5 Candle (75 menit)
LOT_SIZE               = 0.01       # Lot Size Eksekusi
MAGIC_NUMBER           = 123230     # Magic ID Unik M15

SL_TP_MODE             = "SMART_INTRADAY"
RRR_RATIO              = 2.5        # Risk-to-Reward Ratio (1 : 2.5) → TP lebih besar, cukup WR 40% untuk profit
AUTO_EXECUTE           = True       # Set True untuk Eksekusi Otomatis ke MT5!

# --- SMC MULTI-ZONE ADAPTIVE ENTRY PARAMETERS (VERSI 3.3 CONFLUENCE & BREAKDOWN ENGINE) ---
# Zona A: Boundary Bounce & Key Level Reversal (<= 0.15% dari Support / Resistance)
ZONE_A_THRESHOLD       = 0.0015     # Jarak <= 0.15% (~$6.60) dari Support / Resistance
ZONE_A_PROB_MIN        = 58.0       # Ambang AI dasar (dinaikkan dari 54% untuk filter entry lebih ketat)
WICK_MIN_RATIO         = 0.20       # Minimal 20% Ekor Penolakan (Rejection Wick / Pinbar)

# Zona B: Proximity Opportunity & Structure HL/LH (0.15% - 0.40%)
ZONE_B_THRESHOLD       = 0.0040     # Jarak 0.15% s/d 0.40% (~$6.60 - $17.60)
ZONE_B_PROB_MIN        = 60.0       # Ambang AI Zona B (dinaikkan dari 58% untuk entry lebih selektif)
ZONE_B_WICK_MIN        = 0.18       # Minimal 18% Ekor Penolakan atau Higher Low / Lower High

# Zona C: High-Probability Trend & Breakout / Breakdown PDL (> 0.40%)
ZONE_C_PROB_MIN        = 65.0       # Ambang AI Zona C (dinaikkan dari 62% untuk Zona C hanya saat sangat yakin)

# --- SNIPER DIRECT ENTRY (BYPASS FILTER SAAT HIGH-CONVICTION) ---
# Berdasarkan hasil Layer 2 Backtest: saat prob >= 70%, direct entry menghasilkan
# WR 83.2%, PF 10.74 di M15. Filter heuristik justru merusak performa.
SNIPER_DIRECT_PROB_MIN = 70.0       # Bypass semua filter saat AI >= 70%

# --- DYNAMIC PROFIT PROTECTION & AI EXIT (M15 SWING) ---
ENABLE_BREAKEVEN       = True       # Pindahkan SL ke Break-Even (+ $0.20) jika profit >= +$4.00 USD
ENABLE_TRAILING_LOCK   = True       # Kunci profit minimal jika floating profit pernah naik tinggi
TRAILING_TRIGGER_USD   = 5.00       # Aktifkan trailing lock saat profit mencapai >= +$5.00 USD (dinaikkan agar tidak lock terlalu dini)
TRAILING_LOCK_USD      = 3.50       # Kunci profit minimal +$3.50 USD (naik dari $2.50 agar profit pulang lebih besar)
MAX_CUTLOSS_USD        = 8.50       # Batas risiko rugi terukur diperlebar dari $6.00 ke $8.50 agar tidak terjilat wick normal XAUUSD
ENABLE_AI_CUTLOSS      = True       # AI Early Cut-Loss jika sinyal candle M15 berbalik tajam >= 65%
AI_CUTLOSS_REV_PROB    = 65.0       # Ambang batas pembalikan arah AI untuk cut-loss dini

# --- IDENTITAS VERSI DAN LOGGING ---
BOT_VERSION            = "Versi 3.7 (Pure Market Order + Noise-Immune Wide SL + High RRR)"
MODEL_LABEL_EXCEL      = "LightGBM M15 v3.7 (Wide SL + RRR 2.5 + Sniper)"
THRESHOLD_LABEL_EXCEL  = "Versi 3.7 (Wide SL + RRR 2.5 + Sniper Entry)"
ORDER_COMMENT          = "LightGBM M15 v3.7"
EXCEL_M15_PATH         = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx"
SHEET_TITLE_M15        = "Trade Log Model Terbaru (v3.7)"
SUMMARY_TITLE_M15      = "Ringkasan Statistik (v3.7)"
COLLISION_DISTANCE_MIN = 0.0018      # Jarak minimal 0.18% (~$8) dari Lantai Demand / Atap Supply Mayor

# --- PURE MARKET ORDER CONFIGURATION (VERSI 3.7) ---
ENABLE_ADAPTIVE_HYBRID_ENTRY  = False  # Set False untuk mempertahankan Pure Market Order 100% (Sinyal langsung dieksekusi)
GIANT_CANDLE_ATR_RATIO        = 1.35   # Parameter fallback
PENDING_ORDER_TIMEOUT_CANDLES = 3      # Parameter fallback

# --- RISK MANAGEMENT: LOSS COOLDOWN & DAILY LIMIT (REVISI v3.7) ---
MAX_DAILY_LOSSES       = 5           # Maks 5x loss per hari (sesuai revisi user agar tidak membatasi peluang)
LOSS_COOLDOWN_CANDLES  = 2           # Tunggu 2 candle M15 (30 menit) sebelum entry baru setelah loss
AREA_LOCKOUT_RANGE     = 12.0        # Lockout area +/-$12 dari entry terakhir yang loss selama 30 menit
MAX_BROKER_SL_USD      = 10.00       # Batas absolut SL broker M15

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"

print("="*75)
print(f"🤖 ROBOT TRADING OTOMATIS LIGHTGBM XAUUSD [{BOT_VERSION}]")
print("Pembeda Utama: Multi-Zone Entry (A:Boundary, B:Proximity, C:Trend) + Candle Structure")
print("Manajemen Exit: Dynamic Trailing Lock ($1.50) + AI Early Cut-Loss (>= 65%)")
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

def calc_dynamic_channel(df_data, lookback=35):
    """
    Menghitung Kanal Regresi Linear Dinamis (Support & Resisten Miring):
    - slope: Sudut kemiringan tren ($/candle). Positif = Uptrend Channel, Negatif = Downtrend Channel
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
    
    if slope > 0.15:
        channel_type = 'UPTREND_CHANNEL'
    elif slope < -0.15:
        channel_type = 'DOWNTREND_CHANNEL'
    else:
        channel_type = 'HORIZONTAL'
        
    return float(slope), dyn_support, dyn_resistance, channel_type, dist_dyn_sup, dist_dyn_res

def detect_multi_horizon_snr_and_patterns(df_data, lookback_multiday=300, lookback_pattern=40):
    """
    Analisis Multi-Horizon SNR & Pola Grafik Teknikal Lanjutan M15 (Versi 3.2):
    1. Multi-Day Structural SNR (Lookback 2-4 Hari / ~300 lilin M15 = ~75 jam):
       - major_demand: Lantai terendah multi-day
       - major_supply: Atap tertinggi multi-day
       - nearest_sup: Level swing support terdekat di bawah harga
       - nearest_res: Level swing resistance terdekat di atas harga
       - dist_near_sup: Jarak persentase ke lantai terdekat
       - dist_near_res: Jarak persentase ke atap terdekat
    2. Pola Grafik Teknikal (Wedge & Channels):
       - RISING_WEDGE: Baji Naik (Kedua garis naik menyempit -> Potensi Reversal Bearish)
       - FALLING_WEDGE: Baji Turun (Kedua garis turun menyempit -> Potensi Reversal Bullish)
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
    
    # 1. Multi-Day Lookback (Lookback 300 lilin M15 = ~75 jam / 3 hari)
    lb_multi = min(n, lookback_multiday)
    sub_multi = df_data.tail(lb_multi).copy()
    
    major_demand = float(sub_multi['low'].min())
    major_supply = float(sub_multi['high'].max())
    
    # Rolling swing pivots window 8 (~2 jam)
    roll_lows = sub_multi['low'].rolling(8, center=True).min()
    roll_highs = sub_multi['high'].rolling(8, center=True).max()
    
    swing_lows = sub_multi[sub_multi['low'] == roll_lows]['low'].values
    swing_highs = sub_multi[sub_multi['high'] == roll_highs]['high'].values
    
    # Dynamic Swing Levels & Flip Zones (Breakdown/Breakout Adaptive M15)
    sups_below = [float(s) for s in swing_lows if s < curr_close - 1.0]
    res_above  = [float(r) for r in swing_highs if r > curr_close + 1.0]
    
    struct_sup_cand = float(df_data['low'].shift(1).tail(40).min()) if len(df_data) >= 40 else major_demand
    struct_res_cand = float(df_data['high'].shift(1).tail(40).max()) if len(df_data) >= 40 else major_supply
    if struct_sup_cand < curr_close - 1.0:
        sups_below.append(struct_sup_cand)
    if struct_res_cand > curr_close + 1.0:
        res_above.append(struct_res_cand)
        
    nearest_sup = max(sups_below) if len(sups_below) > 0 else major_demand
    nearest_res = min(res_above) if len(res_above) > 0 else major_supply
    
    dist_near_sup = max(0.0, (curr_close - nearest_sup) / curr_close)
    dist_near_res = max(0.0, (nearest_res - curr_close) / curr_close)
    
    # 2. Pola Grafik Teknikal Multi-Scale (Lookback 24 lilin ~6 jam & 40 lilin ~10 jam)
    pattern = "HORIZONTAL_RANGE (Konsolidasi Datar)"
    bias = "SIDEWAYS"
    best_slope_h, best_slope_l = 0.0, 0.0
    
    for lb_pat in [24, min(n, lookback_pattern)]:
        sub_pat = df_data.tail(lb_pat)
        x = np.arange(len(sub_pat))
        sh, ih = np.polyfit(x, sub_pat['high'].values, 1)
        sl, il = np.polyfit(x, sub_pat['low'].values, 1)
        spread_s = ih - il
        spread_e = (sh * len(sub_pat) + ih) - (sl * len(sub_pat) + il)
        is_conv = spread_e < (spread_s * 0.75)
        
        # A. DESCENDING TRIANGLE (Atap miring turun menekan lantai support flat / horizontal - Bias Bearish Continuation)
        if sh < -0.06 and (abs(sl) <= 0.15 or (sl < 0 and sh < sl - 0.15 and abs(sl) < 0.35)):
            pattern = "DESCENDING_TRIANGLE (Segitiga Turun - Bias Bearish Continuation)"
            bias = "BEARISH_CONTINUATION"
            best_slope_h, best_slope_l = sh, sl
            break
        # B. ASCENDING TRIANGLE (Lantai miring naik menekan plafon resisten flat / horizontal - Bias Bullish Continuation)
        elif sl > 0.06 and (abs(sh) <= 0.15 or (sh > 0 and sl > sh + 0.15 and abs(sh) < 0.35)):
            pattern = "ASCENDING_TRIANGLE (Segitiga Naik - Bias Bullish Continuation)"
            bias = "BULLISH_CONTINUATION"
            best_slope_h, best_slope_l = sh, sl
            break
        # C. SYMMETRICAL TRIANGLE (Penyempitan dua arah - Breakout Pending)
        elif sh < -0.08 and sl > 0.08:
            pattern = "SYMMETRICAL_TRIANGLE (Segitiga Simetris - Breakout Pending)"
            bias = "BREAKOUT_PENDING"
            best_slope_h, best_slope_l = sh, sl
            break
        elif lb_pat >= 35:
            if sh < -0.10 and sl < -0.10:
                if is_conv and sl < -0.40 and sh > -0.30:
                    pattern = "FALLING_WEDGE (Baji Turun - Potensi Reversal Bullish)"
                    bias = "BULLISH_REVERSAL"
                else:
                    pattern = "DESCENDING_CHANNEL (Kanal Miring Turun)"
                    bias = "BEARISH_TREND"
            elif sh > 0.10 and sl > 0.10:
                if is_conv and sh > 0.40 and sl < 0.30:
                    pattern = "RISING_WEDGE (Baji Naik - Potensi Reversal Bearish)"
                    bias = "BEARISH_REVERSAL"
                else:
                    pattern = "ASCENDING_CHANNEL (Kanal Miring Naik)"
                    bias = "BULLISH_TREND"
            best_slope_h, best_slope_l = sh, sl
            
    slope_high, slope_low = best_slope_h, best_slope_l
        
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
            'bull_div': False, 'bear_div': False, 'div_desc': 'Data terbatas',
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
    
    # 5. Deteksi RSI Divergence (Regular Bullish & Bearish Divergence)
    bull_div = False
    bear_div = False
    div_desc = "Netral"
    
    if len(df_data) >= 25 and 'low' in df_data.columns and 'high' in df_data.columns:
        curr_low = float(df_data['low'].iloc[-1])
        curr_high = float(df_data['high'].iloc[-1])
        
        # Ambil swing extrema 4 s/d 20 candle sebelumnya
        prev_lows = df_data['low'].iloc[-20:-3]
        prev_highs = df_data['high'].iloc[-20:-3]
        
        if len(prev_lows) > 0 and len(prev_highs) > 0:
            min_prev_low = float(prev_lows.min())
            min_prev_low_idx = prev_lows.idxmin()
            rsi_at_prev_low = float(rsi_series.loc[min_prev_low_idx]) if min_prev_low_idx in rsi_series.index else 50.0
            
            max_prev_high = float(prev_highs.max())
            max_prev_high_idx = prev_highs.idxmax()
            rsi_at_prev_high = float(rsi_series.loc[max_prev_high_idx]) if max_prev_high_idx in rsi_series.index else 50.0
            
            # Regular Bullish Divergence: Harga Lower Low (atau retest dasar), tapi RSI naik (+3.0 pts) di area < 48
            if (curr_low <= min_prev_low + 1.0) and (cur_rsi >= rsi_at_prev_low + 3.0) and (cur_rsi <= 48.0):
                bull_div = True
                div_desc = f"Bullish Div 🟢 (Low ${curr_low:.1f} vs ${min_prev_low:.1f} | RSI {cur_rsi:.1f} > {rsi_at_prev_low:.1f})"
            # Regular Bearish Divergence: Harga Higher High (atau retest atap), tapi RSI turun (-3.0 pts) di area > 52
            elif (curr_high >= max_prev_high - 1.0) and (cur_rsi <= rsi_at_prev_high - 3.0) and (cur_rsi >= 52.0):
                bear_div = True
                div_desc = f"Bearish Div 🔴 (High ${curr_high:.1f} vs ${max_prev_high:.1f} | RSI {cur_rsi:.1f} < {rsi_at_prev_high:.1f})"
    
    div_str = f" | {div_desc}" if div_desc != "Netral" else ""
    summary_desc = (
        f"Stoch RSI: %K={cur_k:.1f}, %D={cur_d:.1f} "
        f"({'OVERSOLD 🟢' if stoch_oversold else ('OVERBOUGHT 🔴' if stoch_overbought else 'NETRAL')}) | "
        f"RSI: {cur_rsi:.1f}{div_str} | BB Pos: {bb_pos*100:.1f}% | EMA20/50: {'BULL' if is_ema_bull else 'BEAR'}"
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
        'bull_div': bull_div,
        'bear_div': bear_div,
        'div_desc': div_desc,
        'summary_desc': summary_desc
    }

def detect_candle_structure(df_clean):
    """
    Menganalisis struktur candlestick 3-5 candle terakhir (SMC Price Action v3.7):
    - Pola Higher Low (HL): Rebound bullish dari area demand
    - Pola Lower High (LH): Rejection bearish dari area supply
    - Breakout Structure (BOS / CHoCH baru)
    - Market State: 'TRENDING_BULL', 'TRENDING_BEAR', 'SIDEWAYS_TIGHT', 'SIDEWAYS_WIDE'
    - Market Structure Shift (MSS): Perubahan dari HH/HL → LH/LL atau sebaliknya
    - FVG/Imbalance Zone Proximity: Jarak harga ke zona FVG terdekat yang belum terisi
    - Order Block Bearish: Deteksi candle bullish sebelum impulse turun
    - PDH/PDL: Previous Day High / Low sebagai level kunci
    """
    fallback = {
        'is_higher_low': False,
        'is_lower_high': False,
        'bos_bull_recent': False,
        'bos_bear_recent': False,
        'choch_bull_recent': False,
        'choch_bear_recent': False,
        'market_regime': 'SIDEWAYS',
        'fibo_pos': 0.5,
        'structure_desc': 'Data historis terbatas',
        'is_impulse_bear': False,
        'is_impulse_bull': False,
        'mss_bullish': False,
        'mss_bearish': False,
        'near_unfilled_fvg_bull': False,
        'near_unfilled_fvg_bear': False,
        'near_ob_bear_zone': False,
        'pdh': 0.0,
        'pdl': 0.0,
        'dist_pdh_pct': 0.0,
        'dist_pdl_pct': 0.0,
        'c0_open': 0.0,
        'c0_close': 0.0,
        'c0_high': 0.0,
        'c0_low': 0.0,
        'cur_range': 0.0,
        'cur_body': 0.0,
    }
    if len(df_clean) < 10:
        return fallback
    
    # Ambil 5 candle terakhir
    c0_low  = float(df_clean['low'].iloc[-1])
    c1_low  = float(df_clean['low'].iloc[-2])
    c2_low  = float(df_clean['low'].iloc[-3])
    c3_low  = float(df_clean['low'].iloc[-4])
    c4_low  = float(df_clean['low'].iloc[-5])
    
    c0_high = float(df_clean['high'].iloc[-1])
    c1_high = float(df_clean['high'].iloc[-2])
    c2_high = float(df_clean['high'].iloc[-3])
    c3_high = float(df_clean['high'].iloc[-4])
    c4_high = float(df_clean['high'].iloc[-5])
    
    c0_close = float(df_clean['close'].iloc[-1])
    c1_close = float(df_clean['close'].iloc[-2])
    c0_open  = float(df_clean['open'].iloc[-1])
    
    # 1. Pola Higher Low (HL): Low candle terbaru lebih tinggi, atau candle sebelumnya rebound
    is_higher_low = (c0_low > c1_low) or (c1_low > c2_low and c0_close > c1_close)
    
    # 2. Pola Lower High (LH): High candle terbaru lebih rendah, atau candle sebelumnya rejected
    is_lower_high = (c0_high < c1_high) or (c1_high < c2_high and c0_close < c1_close)
    
    # 3. BOS & CHoCH dalam 3 candle terakhir
    bos_bull_recent = bool(df_clean['BOS_Bull'].iloc[-3:].max() == 1)
    bos_bear_recent = bool(df_clean['BOS_Bear'].iloc[-3:].max() == 1)
    choch_bull_recent = bool(df_clean['CHoCH_Bull'].iloc[-3:].max() == 1)
    choch_bear_recent = bool(df_clean['CHoCH_Bear'].iloc[-3:].max() == 1)
    
    # 4. Market Regime: Sideways vs Trending (via BB Bandwidth & Retur akumulatif)
    # Deteksi Lilin Impulsif (Breakout / Breakdown News Momentum)
    cur_range = (float(df_clean['high'].iloc[-1]) - float(df_clean['low'].iloc[-1])) + 1e-6
    cur_body  = abs(float(df_clean['close'].iloc[-1]) - float(df_clean['open'].iloc[-1]))
    body_ratio = cur_body / cur_range
    is_impulse_bear = bool(float(df_clean['close'].iloc[-1]) < float(df_clean['open'].iloc[-1]) and body_ratio >= 0.55)
    is_impulse_bull = bool(float(df_clean['close'].iloc[-1]) > float(df_clean['open'].iloc[-1]) and body_ratio >= 0.55)

    bb_bw = float(df_clean['BB_Bandwidth'].iloc[-1])
    ret_5 = float(df_clean['XAU_Return_5'].iloc[-1]) if 'XAU_Return_5' in df_clean.columns else 0.0
    fibo_pos = float(df_clean['Fibo_Pos_100'].iloc[-1]) if 'Fibo_Pos_100' in df_clean.columns else 0.5
    
    if bb_bw < 0.0025:
        market_regime = 'SIDEWAYS_TIGHT'
    elif ret_5 > 0.003:
        market_regime = 'TRENDING_BULL'
    elif ret_5 < -0.003:
        market_regime = 'TRENDING_BEAR'
    else:
        market_regime = 'SIDEWAYS_WIDE'
    
    # ===== FITUR BARU v3.7 =====
    
    # 5. MARKET STRUCTURE SHIFT (MSS): Perubahan karakter swing points
    # Bullish MSS: Pola LH/LL berubah ke HL/HH (swing low terakhir > swing low sebelumnya + break high)
    # Bearish MSS: Pola HH/HL berubah ke LH/LL (swing high terakhir < swing high sebelumnya + break low)
    swing_lows_5 = [c4_low, c3_low, c2_low, c1_low, c0_low]
    swing_highs_5 = [c4_high, c3_high, c2_high, c1_high, c0_high]
    
    # Bullish MSS: Sebelumnya LL (low semakin turun), sekarang HL (low naik) + close break above prev high
    was_making_ll = (c3_low < c4_low) and (c2_low < c3_low)
    now_making_hl = (c1_low > c2_low) or (c0_low > c1_low)
    mss_bullish = bool(was_making_ll and now_making_hl and c0_close > c1_high)
    
    # Bearish MSS: Sebelumnya HH (high semakin naik), sekarang LH (high turun) + close break below prev low
    was_making_hh = (c3_high > c4_high) and (c2_high > c3_high)
    now_making_lh = (c1_high < c2_high) or (c0_high < c1_high)
    mss_bearish = bool(was_making_hh and now_making_lh and c0_close < c1_low)
    
    # 6. FVG / IMBALANCE ZONE PROXIMITY (bukan hanya binary ada/tidak)
    # Cari FVG terdekat yang belum terisi dalam 20 candle terakhir
    near_unfilled_fvg_bull = False
    near_unfilled_fvg_bear = False
    try:
        lookback_fvg = min(20, len(df_clean) - 3)
        for i in range(2, lookback_fvg):
            # Bullish FVG: gap antara candle[-i-2].high dan candle[-i].low
            gap_low = float(df_clean['high'].iloc[-i-2])
            gap_high = float(df_clean['low'].iloc[-i])
            if gap_high > gap_low + 0.5:  # FVG zone exists (min $0.50 gap)
                # Cek apakah harga saat ini mendekati zona FVG (dalam $3)
                if gap_low - 3.0 <= c0_close <= gap_high + 1.0:
                    near_unfilled_fvg_bull = True
                    break
        
        for i in range(2, lookback_fvg):
            # Bearish FVG: gap antara candle[-i].high dan candle[-i-2].low
            gap_high_bear = float(df_clean['low'].iloc[-i-2])
            gap_low_bear = float(df_clean['high'].iloc[-i])
            if gap_high_bear > gap_low_bear + 0.5:  # Bearish FVG zone
                if gap_low_bear - 1.0 <= c0_close <= gap_high_bear + 3.0:
                    near_unfilled_fvg_bear = True
                    break
    except Exception:
        pass
    
    # 7. BEARISH ORDER BLOCK PROXIMITY (candle bullish sebelum impulse turun)
    near_ob_bear_zone = False
    try:
        for i in range(3, min(15, len(df_clean) - 3)):
            ob_open = float(df_clean['open'].iloc[-i])
            ob_close = float(df_clean['close'].iloc[-i])
            ob_high = float(df_clean['high'].iloc[-i])
            # Candle bullish (close > open) diikuti impulse turun besar
            if ob_close > ob_open:
                # Cek impulse down setelahnya (2 candle berikutnya drop signifikan)
                if i >= 3:
                    post_low = float(df_clean['low'].iloc[-i+1:-i+3].min())
                    impulse_drop = ob_close - post_low
                    if impulse_drop > 1.5 * (ob_high - float(df_clean['low'].iloc[-i])):
                        # Zona Bearish OB = area dari open ke high candle bullish
                        if ob_open <= c0_close <= ob_high + 2.0:
                            near_ob_bear_zone = True
                            break
    except Exception:
        pass
    
    # 8. PDH/PDL (Previous Day High / Low)
    pdh = 0.0
    pdl = 0.0
    dist_pdh_pct = 0.0
    dist_pdl_pct = 0.0
    try:
        if df_clean.index.dtype != 'datetime64[ns]':
            dates = pd.to_datetime(df_clean.index)
        else:
            dates = df_clean.index
        today = dates[-1].date()
        prev_day_data = df_clean[dates.date < today]
        if len(prev_day_data) > 0:
            last_day = prev_day_data.index[-1]
            if hasattr(last_day, 'date'):
                last_day_date = last_day.date() if not isinstance(last_day, str) else pd.to_datetime(last_day).date()
            else:
                last_day_date = pd.to_datetime(last_day).date()
            day_data = prev_day_data[pd.to_datetime(prev_day_data.index).date == last_day_date]
            if len(day_data) > 0:
                pdh = float(day_data['high'].max())
                pdl = float(day_data['low'].min())
                dist_pdh_pct = (pdh - c0_close) / c0_close if c0_close > 0 else 0.0
                dist_pdl_pct = (c0_close - pdl) / c0_close if c0_close > 0 else 0.0
    except Exception:
        pass
    
    structure_desc = f"Regime: {market_regime} | HL: {is_higher_low} | LH: {is_lower_high} | Fibo: {fibo_pos*100:.1f}% | MSS: {'Bull' if mss_bullish else ('Bear' if mss_bearish else 'None')} | FVG: {'Bull' if near_unfilled_fvg_bull else ''}/{'Bear' if near_unfilled_fvg_bear else ''} | OB_Bear: {near_ob_bear_zone}"
    
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
        'structure_desc': structure_desc,
        'mss_bullish': mss_bullish,
        'mss_bearish': mss_bearish,
        'near_unfilled_fvg_bull': near_unfilled_fvg_bull,
        'near_unfilled_fvg_bear': near_unfilled_fvg_bear,
        'near_ob_bear_zone': near_ob_bear_zone,
        'pdh': pdh,
        'pdl': pdl,
        'dist_pdh_pct': dist_pdh_pct,
        'dist_pdl_pct': dist_pdl_pct,
        'c0_open': c0_open,
        'c0_close': c0_close,
        'c0_high': c0_high,
        'c0_low': c0_low,
        'cur_range': cur_range,
        'cur_body': cur_body,
    }


def analyze_market_and_predict():
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1000)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
    rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 100)
    
    fallback_struct = {
        'is_higher_low': False, 'is_lower_high': False,
        'bos_bull_recent': False, 'bos_bear_recent': False,
        'choch_bull_recent': False, 'choch_bear_recent': False,
        'market_regime': 'SIDEWAYS', 'fibo_pos': 0.5, 'structure_desc': 'Fallback MT5 Disconnect',
        'c0_open': 0.0, 'c0_close': 0.0, 'c0_high': 0.0, 'c0_low': 0.0, 'cur_range': 0.0, 'cur_body': 0.0
    }
    fallback_pattern = {
        'major_demand': 0.0, 'major_supply': 9999.0,
        'nearest_sup': 0.0, 'nearest_res': 9999.0,
        'dist_near_sup': 0.01, 'dist_near_res': 0.01,
        'pattern': 'HORIZONTAL_RANGE (Konsolidasi Datar)', 'pattern_bias': 'SIDEWAYS',
        'slope_high': 0.0, 'slope_low': 0.0,
        'can_sell_safely': True, 'can_buy_safely': True
    }

    if rates_m15 is None or len(rates_m15) == 0 or rates_h1 is None or len(rates_h1) == 0:
        print("\n⚠️ Koneksi data MT5 terputus sesaat. Mencoba Re-initialize MT5...")
        mt5.initialize(path=MT5_PATH)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1000)
        rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
        rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 100)
        if rates_m15 is None or len(rates_m15) == 0:
            print("❌ Gagal menarik data dari MT5. Melewati candle ini...")
            fallback_channel = {'slope': 0.0, 'dyn_sup': 0.0, 'dyn_res': 0.0, 'dyn_support': 0.0, 'dyn_resistance': 0.0, 'channel_type': 'HORIZONTAL', 'dist_dyn_sup': 0.01, 'dist_dyn_res': 0.01}
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
            return 50.0, 50.0, False, False, 8.0, 0.0, 0.0, 0.01, 0.01, 0.0, 0.0, False, False, 0.0, 0.0, fallback_struct, fallback_channel, fallback_pattern, fallback_tech

    df_m15 = pd.DataFrame(rates_m15)
    df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
    df_m15.set_index('time', inplace=True)
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_h1.set_index('time', inplace=True)

    df_h4 = pd.DataFrame(rates_h4) if rates_h4 is not None and len(rates_h4) > 0 else df_h1.copy()
    df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
    df_h4.set_index('time', inplace=True)

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
    df_m15['Body_Ratio']       = (df_m15['close'] - df_m15['open']).abs() / range_m15
    df_m15['Lower_Wick_Ratio'] = (df_m15[['open', 'close']].min(axis=1) - df_m15['low']) / range_m15
    df_m15['Upper_Wick_Ratio'] = (df_m15['high'] - df_m15[['open', 'close']].max(axis=1)) / range_m15
    df_m15['Body_M15']         = df_m15['Body_Ratio']
    df_m15['Lower_Wick_M15']   = df_m15['Lower_Wick_Ratio']
    df_m15['Upper_Wick_M15']   = df_m15['Upper_Wick_Ratio']

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

    # 5. ORDER BLOCK PROXIMITY (Bullish & Bearish OB)
    is_bear_c = df_m15['close'] < df_m15['open']
    is_bull_c = df_m15['close'] > df_m15['open']
    impulse_up = (df_m15['close'].shift(-2) - df_m15['close']) > (1.5 * (df_m15['high'] - df_m15['low']))
    impulse_dn = (df_m15['close'] - df_m15['close'].shift(-2)) > (1.5 * (df_m15['high'] - df_m15['low']))
    df_m15['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
    df_m15['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)

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

    # 7. MOMENTUM & VOLATILITAS
    delta15 = df_m15['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
    df_m15['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))
    df_m15['RSI_M15'] = df_m15['RSI_14']

    df_m15['SMA_20'] = df_m15['close'].rolling(20).mean()
    df_m15['STD_20'] = df_m15['close'].rolling(20).std()
    df_m15['BB_Bandwidth'] = (4 * df_m15['STD_20']) / df_m15['SMA_20']
    df_m15['BB_Pos'] = (df_m15['close'] - (df_m15['SMA_20'] - 2*df_m15['STD_20'])) / (4*df_m15['STD_20'] + 1e-6)

    df_m15['XAU_Return_1'] = df_m15['close'].pct_change(1)
    df_m15['XAU_Return_3'] = df_m15['close'].pct_change(3)
    df_m15['XAU_Return_5'] = df_m15['close'].pct_change(5)

    # 8. DXY INTERMARKET & MAKROEKONOMI
    df_m15['DXY_Close'] = dxy_close.reindex(df_m15.index, method='ffill').bfill()
    df_m15['DXY_Return_1'] = df_m15['DXY_Close'].pct_change(1).fillna(0)
    df_m15['DXY_Return_3'] = df_m15['DXY_Close'].pct_change(3).fillna(0)
    df_m15['DXY_Trend'] = (df_m15['DXY_Close'] > df_m15['DXY_Close'].rolling(20).mean()).astype(int)
    df_m15['XAU_DXY_Ratio_Return'] = (df_m15['close'] / df_m15['DXY_Close']).pct_change(1).fillna(0)

    dates = df_m15.index
    df_m15['Is_NFP_Week'] = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
    df_m15['Is_CPI_Day']  = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    df_m15['Is_FOMC_Week'] = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)

    # 9. MULTI-TIMEFRAME TREND (H1 & H4)
    df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
    df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
    df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
    df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
    df_m15['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
    df_m15['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

    df_h4['EMA_50_H4'] = df_h4['close'].ewm(span=50, adjust=False).mean()
    df_h4['EMA_200_H4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
    df_h4['Trend_H4_Bull'] = (df_h4['close'] > df_h4['EMA_50_H4']).astype(int)
    df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)
    df_m15['Trend_H4_Bull'] = df_h4['Trend_H4_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
    df_m15['Trend_H4_Strong'] = df_h4['Trend_H4_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

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
        'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 
        'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
        'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
        'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 
        'Order_Block_Bull', 'Order_Block_Bear',
        'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
        'RSI_14', 'BB_Bandwidth', 'BB_Pos',
        'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
        'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
        'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
        'Trend_H1_Bull', 'Trend_H1_Strong',
        'Trend_H4_Bull', 'Trend_H4_Strong'
    ]

    latest_candle = df_clean[features].iloc[[-1]]
    latest_atr = df_clean['ATR_14'].iloc[-1]
    
    global last_features_dict
    last_features_dict = latest_candle.iloc[0].to_dict()
    
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
    
    # Deteksi pola struktur candlestick & market regime
    struct_data = detect_candle_structure(df_clean)

    # Deteksi Kanal Regresi Linear Dinamis (Support & Resisten Miring / Dynamic Trendlines)
    slope, dyn_sup, dyn_res, channel_type, dist_dyn_sup, dist_dyn_res = calc_dynamic_channel(df_clean, lookback=35)
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

    # Deteksi Multi-Horizon SNR & Pola Grafik Teknikal M15 (Lookback 300 lilin / ~75 jam / ~3.1 hari)
    pattern_data = detect_multi_horizon_snr_and_patterns(df_m15, lookback_multiday=300, lookback_pattern=40)

    # Deteksi Indikator Teknikal Lengkap (Stochastic RSI, RSI, BB, EMA)
    tech_data = calc_technical_indicators(df_m15)

    # ANALISIS KONTEKS H4 (FIX A)
    h4_context = {
        'h4_slope': 0.0, 'h4_upper': 9999.0, 'h4_lower': 0.0, 'h4_mid': cur_close,
        'h4_position_pct': 50.0, 'h4_channel': 'UNKNOWN', 'h4_range_2d': 0.0,
        'range_pos_pct': 50.0
    }
    try:
        if rates_h4 is not None and len(rates_h4) >= 20:
            df_h4 = pd.DataFrame(rates_h4)
            df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
            h4_sub = df_h4.tail(20)
            x_h4 = np.arange(len(h4_sub))
            slope_h4_close, _ = np.polyfit(x_h4, h4_sub['close'].values, 1)
            slope_h4_high, int_h4_high = np.polyfit(x_h4, h4_sub['high'].values, 1)
            slope_h4_low, int_h4_low = np.polyfit(x_h4, h4_sub['low'].values, 1)
            curr_x_h4 = len(h4_sub) - 1
            h4_upper = float(slope_h4_high * curr_x_h4 + int_h4_high)
            h4_lower = float(slope_h4_low * curr_x_h4 + int_h4_low)
            h4_mid = (h4_upper + h4_lower) / 2.0
            h4_range = max(1.0, h4_upper - h4_lower)
            h4_position_pct = max(0.0, min(100.0, ((cur_close - h4_lower) / h4_range) * 100.0))
            if slope_h4_close < -1.5:
                h4_channel = 'DESCENDING_H4'
            elif slope_h4_close > 1.5:
                h4_channel = 'ASCENDING_H4'
            else:
                h4_channel = 'HORIZONTAL_H4'
            h4_2d = df_h4.tail(12)
            range_2d = float(h4_2d['high'].max()) - float(h4_2d['low'].min())
            range_pos_pct = max(0.0, min(100.0, ((cur_close - float(h4_2d['low'].min())) / max(1.0, range_2d)) * 100.0))
            h4_context = {
                'h4_slope': float(slope_h4_close), 'h4_upper': h4_upper, 'h4_lower': h4_lower,
                'h4_mid': h4_mid, 'h4_position_pct': h4_position_pct, 'h4_channel': h4_channel,
                'h4_range_2d': range_2d, 'range_pos_pct': range_pos_pct
            }
    except Exception:
        pass

    return prob_up, prob_down, h1_bull, h1_strong_bull, latest_atr, live_ask, live_bid, dist_m15_sup, dist_m15_res, lower_wick, upper_wick, is_bull_candle, is_bear_candle, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data, h4_context

def evaluate_multi_zone_decision(prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data=None, pattern_data=None, tech_data=None, h4_context=None):
    """
    Evaluasi Keputusan Multi-Zone Adaptive Entry M15 (Versi 3.6 - H4 Context + Range Guard):
    - Konfluensi Lengkap: Stochastic RSI (14,14,3,3), RSI(14), Bollinger Bands, EMA 20/50
    - Anti-Oversold Guard: DILARANG SELL jika Stoch RSI <= 25% (Mencegah kerugian entry prematur di dasar)
    - Anti-Overbought Guard: DILARANG BUY jika Stoch RSI >= 75% (Mencegah beli di pucuk jenuh)
    - Confluence Booster: Turunkan ambang AI ke >= 50% saat Stoch Overbought di resisten atau Oversold di support
    - Multi-Horizon SNR (2-4 Hari) + Chart Patterns (Wedge/Channels)
    - Anti-Collision Guard: DILARANG SELL mepet Lantai Demand (<= 0.18%), DILARANG BUY mepet Atap Supply (<= 0.18%)
    - Zona A: Boundary Bounce (<= 0.15% dari Support/Resisten)
    - Zona B: Proximity Opportunity (0.15% - 0.40%)
    - Zona C: High-Probability Trend (> 0.40%)
    """
    # 🛡️ KALKULASI SL KEBAL WICK NOISE (REVISI v3.7 ANTI-SWEEP):
    # Menggunakan 1.20x ATR (rentang $6.50 - $8.50 USD / 65-85 pips)
    # Menjamin jarak SL berada di luar jangkauan noise wick normal M15 Gold (mencegah case Trade 3 tersapu dini)
    base_sl = max(65.0, min(85.0, round(atr_val * 10.0 * 1.20, 0)))
    
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
    bull_div = tech_data.get('bull_div', False) if tech_data else False
    bear_div = tech_data.get('bear_div', False) if tech_data else False
    div_desc = tech_data.get('div_desc', 'Netral') if tech_data else 'Netral'
    
    # 🛡️ KALENDER BERITA MAKROEKONOMI (NEWS GUARD M15)
    is_news_freeze, news_desc, _ = macro_news.check_news_guard(window_before_min=10, window_after_min=15)
    if is_news_freeze:
        return "WAIT", "NEWS_FREEZE", 0, 0, news_desc

    is_strong_bull_trend = h1_bull or (slope > 0.08) or (channel_type == 'UPTREND_CHANNEL')
    is_strong_bear_trend = not h1_bull or (slope < -0.08) or (channel_type == 'DOWNTREND_CHANNEL')

    has_sell_confluence = (stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or bear_div or ('BEARISH' in (pattern_data.get('pattern_bias', '') if pattern_data else ''))) and not is_strong_bull_trend
    has_buy_confluence  = (stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or bull_div or ('BULLISH' in (pattern_data.get('pattern_bias', '') if pattern_data else ''))) and not is_strong_bear_trend
    
    # 1. EVALUASI DUAL DEMAND/SUPPORT (BUY):
    if abs(slope) > 0.08 and dist_dyn_sup < dist_sup:
        effective_dist_sup = dist_dyn_sup
        sup_type = "Support Miring"
        sup_label = f"Support Miring (${dyn_sup:.2f})"
        is_diag_sup = True
    else:
        effective_dist_sup = dist_sup
        sup_type = "Demand Horizontal"
        sup_label = f"Demand Horizontal (${m15_sup:.2f})"
        is_diag_sup = False
        
    # 2. EVALUASI DUAL SUPPLY/RESISTEN (SELL):
    if abs(slope) > 0.08 and dist_dyn_res < dist_res:
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
    
    # 🛡️ ANTI-OVERSOLD / BULLISH DIVERGENCE GUARD: Dilarang SELL jika Stoch RSI oversold atau ada Bullish Divergence!
    if (stoch_oversold or bull_div) and not (is_bear_c and (upper_w <= 0.15 or struct_data.get('is_impulse_bear', False))):
        reason_div = f"Bullish Divergence aktif ({div_desc})" if bull_div else f"Stoch RSI di dasar (%K={stoch_k:.1f} <= 25)"
        sell_candidate = ("WAIT", "OVERSOLD_OR_DIV", 0, 0, f"🛑 REVERSAL FILTER: SELL Dibatalkan! {reason_div}. Risiko pantulan rebound tinggi!")
    elif effective_dist_res <= ZONE_A_THRESHOLD:
        has_sell_confluence = stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or bear_div
        confluence_tag = f" [{div_desc}]" if bear_div else (f" [Stoch Overbought: %K={stoch_k:.1f}]" if stoch_overbought else (f" [Stoch Bear Cross]" if stoch_bear_cross else (f" [BB Atap: {bb_pos*100:.0f}%]" if bb_pos >= 0.75 else "")))
        
        if has_sell_confluence:
            min_p_sell = 50.0  # Konfluensi teknikal kuat di resisten! Model cukup konfirmasi >= 50%
        elif (is_diag_res or upper_w >= 0.30):
            min_p_sell = 55.0
        else:
            min_p_sell = ZONE_A_PROB_MIN

        if prob_down >= min_p_sell:
            if h1_bull and not is_diag_res and not has_sell_confluence:
                sell_candidate = ("WAIT", "A", 0, 0, f"Zona A {res_type}: SELL {prob_down:.1f}% ditahan karena Tren Makro H1 Bullish")
            elif ((upper_w >= 0.18) or (is_bear_c and (has_sell_confluence or struct_data.get('is_impulse_bear', False) or "TRIANGLE" in pattern_data.get('pattern', '')))):
                if pattern_data and not pattern_data.get('can_sell_safely', True):
                    near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                    dist_sup_pct = pattern_data.get('dist_near_sup', 0.0) * 100
                    sell_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona A Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f}, Jarak {dist_sup_pct:.2f}% <= {COLLISION_DISTANCE_MIN*100:.2f}%). Risiko Pantulan Kuat!")
                else:
                    sl = base_sl
                    tp = round(sl * RRR_RATIO, 0)
                    zone_tag = "A-Diag" if is_diag_res else "A-Horiz"
                    sell_candidate = ("SELL", zone_tag, sl, tp, f"🔴 ZONA A SELL: Penolakan Valid di {res_label}{confluence_tag} (Kanal {channel_type}, Slope ${slope:.2f})! Ekor {upper_w*100:.1f}%, Prob {prob_down:.1f}%.")
            else:
                sell_candidate = ("WAIT", "A", 0, 0, f"Zona A {res_type}: Menunggu Ekor Rejection Atas ({upper_w*100:.1f}% < 20%)")
        else:
            sell_candidate = ("WAIT", "A", 0, 0, f"Zona A {res_type}: Prob SELL ({prob_down:.1f}%) belum mencapai {min_p_sell:.0f}%")

    elif effective_dist_res <= ZONE_B_THRESHOLD:
        has_sell_confluence = stoch_overbought or stoch_bear_cross or (bb_pos >= 0.75) or bear_div
        confluence_tag = f" [{div_desc}]" if bear_div else (f" [Stoch Overbought: %K={stoch_k:.1f}]" if stoch_overbought else (f" [Stoch Bear Cross]" if stoch_bear_cross else ""))
        
        if has_sell_confluence:
            min_p_sell = 52.0
        elif (upper_w >= 0.30 or is_diag_res):
            min_p_sell = 60.0
        else:
            min_p_sell = ZONE_B_PROB_MIN

        if prob_down >= min_p_sell:
            if h1_bull and not is_diag_res and not has_sell_confluence:
                sell_candidate = ("WAIT", "B", 0, 0, f"Zona B {res_type}: SELL {prob_down:.1f}% ditahan karena Tren H1 Bullish")
            else:
                has_wick = upper_w >= ZONE_B_WICK_MIN
                has_lh   = struct_data.get('is_lower_high', False) or is_bear_c or has_sell_confluence
                if (has_wick or has_lh or (is_bear_c and has_sell_confluence)) and not (is_bull_c and upper_w < 0.15):
                    if pattern_data and not pattern_data.get('can_sell_safely', True):
                        near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                        dist_sup_pct = pattern_data.get('dist_near_sup', 0.0) * 100
                        sell_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona B Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f}, Jarak {dist_sup_pct:.2f}%).")
                    else:
                        sl = max(55.0, round(base_sl * 0.90, 0))
                        tp = round(sl * 2.0, 0)
                        zone_tag = "B-Diag" if is_diag_res else "B-Horiz"
                        sell_candidate = ("SELL", zone_tag, sl, tp, f"🔴 ZONA B SELL (PROXIMITY): Struktur Lower High / Rejection Terkonfirmasi Dekat {res_label}{confluence_tag}! Prob {prob_down:.1f}%.")
                else:
                    sell_candidate = ("WAIT", "B", 0, 0, f"Zona B {res_type}: Menunggu konfirmasi pola candle / Lower High (Ekor {upper_w*100:.1f}% < 15%)")
        else:
            sell_candidate = ("WAIT", "B", 0, 0, f"Zona B {res_type}: Prob SELL ({prob_down:.1f}%) belum mencapai {min_p_sell:.0f}%")

    # -----------------------------------------------------------------
    # B. EVALUASI KANDIDAT BUY (LANTAI DEMAND / SUPPORT)
    # -----------------------------------------------------------------
    buy_candidate = None
    
    # 🛡️ ANTI-OVERBOUGHT / BEARISH DIVERGENCE GUARD: Dilarang BUY jika Stoch RSI jenuh beli atau ada Bearish Divergence!
    if (stoch_overbought or bear_div) and not (is_bull_c and (lower_w <= 0.15 or struct_data.get('is_impulse_bull', False))):
        reason_div = f"Bearish Divergence aktif ({div_desc})" if bear_div else f"Stoch RSI di puncak (%K={stoch_k:.1f} >= 75)"
        buy_candidate = ("WAIT", "OVERBOUGHT_OR_DIV", 0, 0, f"🛑 REVERSAL FILTER: BUY Dibatalkan! {reason_div}. Risiko pembalikan drop tinggi!")
    elif effective_dist_sup <= ZONE_A_THRESHOLD:
        has_buy_confluence = stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or bull_div
        confluence_tag = f" [{div_desc}]" if bull_div else (f" [Stoch Oversold: %K={stoch_k:.1f}]" if stoch_oversold else (f" [Stoch Bull Cross]" if stoch_bull_cross else (f" [BB Dasar: {bb_pos*100:.0f}%]" if bb_pos <= 0.25 else "")))
        
        if has_buy_confluence:
            min_p_buy = 50.0  # Konfluensi teknikal kuat di support! Model cukup konfirmasi >= 50%
        elif (is_diag_sup or lower_w >= 0.30):
            min_p_buy = 55.0
        else:
            min_p_buy = ZONE_A_PROB_MIN

        # 🛡️ ANTI-FALLING-KNIFE: Cegah Buy di tengah pisau jatuh saat kanal crash curam
        is_steep_crash = (slope < -0.35) or (struct_data.get('market_regime') == 'TRENDING_BEAR' and not h1_bull)
        has_knife_reversal = (lower_w >= 0.35) or (is_bull_c and (has_buy_confluence or struct_data.get('is_impulse_bull', False)))

        if prob_up >= min_p_buy:
            if is_steep_crash and not has_knife_reversal:
                buy_candidate = ("WAIT", "FALLING_KNIFE", 0, 0, f"🛑 ANTI-FALLING-KNIFE: BUY Zona A Dibatalkan! Downtrend Curam (Slope ${slope:.2f}). Dilarang Buy lilin merah tanpa Bullish Hammer (Ekor {lower_w*100:.1f}% < 35%)!")
            elif not h1_bull and not is_diag_sup and not has_buy_confluence:
                buy_candidate = ("WAIT", "A", 0, 0, f"Zona A {sup_type}: BUY {prob_up:.1f}% ditahan karena Tren Makro H1 Bearish")
            elif lower_w >= 0.20 and (is_bull_c or lower_w >= 0.30 or has_buy_confluence):
                if pattern_data and not pattern_data.get('can_buy_safely', True):
                    near_res_val = pattern_data.get('nearest_res', m15_res)
                    dist_res_pct = pattern_data.get('dist_near_res', 0.0) * 100
                    buy_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona A Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f}, Jarak {dist_res_pct:.2f}% <= {COLLISION_DISTANCE_MIN*100:.2f}%). Risiko Benturan Plafon!")
                else:
                    sl = base_sl
                    tp = round(sl * RRR_RATIO, 0)
                    zone_tag = "A-Diag" if is_diag_sup else "A-Horiz"
                    buy_candidate = ("BUY", zone_tag, sl, tp, f"🟢 ZONA A BUY: Pantulan Valid di {sup_label}{confluence_tag} (Kanal {channel_type}, Slope +${slope:.2f})! Ekor {lower_w*100:.1f}%, Prob {prob_up:.1f}%.")
            else:
                buy_candidate = ("WAIT", "A", 0, 0, f"Zona A {sup_type}: Menunggu Ekor Rejection Bawah ({lower_w*100:.1f}% < 20%)")
        else:
            buy_candidate = ("WAIT", "A", 0, 0, f"Zona A {sup_type}: Prob BUY ({prob_up:.1f}%) belum mencapai {min_p_buy:.0f}%")

    elif effective_dist_sup <= ZONE_B_THRESHOLD:
        has_buy_confluence = stoch_oversold or stoch_bull_cross or (bb_pos <= 0.25) or bull_div
        confluence_tag = f" [{div_desc}]" if bull_div else (f" [Stoch Oversold: %K={stoch_k:.1f}]" if stoch_oversold else (f" [Stoch Bull Cross]" if stoch_bull_cross else ""))
        
        if has_buy_confluence:
            min_p_buy = 52.0
        elif (lower_w >= 0.30 or is_diag_sup):
            min_p_buy = 60.0
        else:
            min_p_buy = ZONE_B_PROB_MIN

        # 🛡️ ANTI-FALLING-KNIFE: Cegah Buy di tengah pisau jatuh saat kanal crash curam
        is_steep_crash = (slope < -0.35) or (struct_data.get('market_regime') == 'TRENDING_BEAR' and not h1_bull)
        has_knife_reversal = (lower_w >= 0.35) or (is_bull_c and (has_buy_confluence or struct_data.get('is_impulse_bull', False)))

        if prob_up >= min_p_buy:
            if is_steep_crash and not has_knife_reversal:
                buy_candidate = ("WAIT", "FALLING_KNIFE", 0, 0, f"🛑 ANTI-FALLING-KNIFE: BUY Zona B Dibatalkan! Downtrend Curam (Slope ${slope:.2f}). Dilarang Buy lilin merah tanpa Bullish Hammer (Ekor {lower_w*100:.1f}% < 35%)!")
            elif not h1_bull and not is_diag_sup and not has_buy_confluence:
                buy_candidate = ("WAIT", "B", 0, 0, f"Zona B {sup_type}: BUY {prob_up:.1f}% ditahan karena Tren H1 Bearish")
            else:
                has_wick = lower_w >= ZONE_B_WICK_MIN
                has_hl   = struct_data.get('is_higher_low', False) or is_bull_c or has_buy_confluence
                if (has_wick or has_hl) and not (is_bear_c and lower_w < 0.15):
                    if pattern_data and not pattern_data.get('can_buy_safely', True):
                        near_res_val = pattern_data.get('nearest_res', m15_res)
                        dist_res_pct = pattern_data.get('dist_near_res', 0.0) * 100
                        buy_candidate = ("WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona B Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f}, Jarak {dist_res_pct:.2f}%).")
                    else:
                        sl = max(55.0, round(base_sl * 0.90, 0))
                        tp = round(sl * 2.0, 0)
                        zone_tag = "B-Diag" if is_diag_sup else "B-Horiz"
                        buy_candidate = ("BUY", zone_tag, sl, tp, f"🟢 ZONA B BUY (PROXIMITY): Struktur Higher Low / Rebound Terkonfirmasi Dekat {sup_label}{confluence_tag}! Prob {prob_up:.1f}%.")
                else:
                    buy_candidate = ("WAIT", "B", 0, 0, f"Zona B {sup_type}: Menunggu konfirmasi pola candle / Higher Low (Ekor {lower_w*100:.1f}% < 15%)")
        else:
            buy_candidate = ("WAIT", "B", 0, 0, f"Zona B {sup_type}: Prob BUY ({prob_up:.1f}%) belum mencapai {min_p_buy:.0f}%")

    # -----------------------------------------------------------------
    # C. SELEKSI KEPUTUSAN TERBAIK BERDASARKAN MODEL-BIASED PRIORITY
    # (Hanya return jika ADA SINYAL EKSEKUSI REAL. Jangan batalkan Zona C karena pesan WAIT!)
    # -----------------------------------------------------------------
    def check_candidate_scenario(cand):
        if not cand or cand[0] not in ["BUY", "SELL"]:
            return cand
        c_sig, c_zone, c_sl, c_tp, c_desc = cand
        sc_key = f"M15_ZONA_{c_zone}_{c_sig}"
        can_tr, sc_msg = scenario_eval.can_trade_scenario(sc_key, "M15")
        if not can_tr:
            return ("WAIT", "BLACKLIST", 0, 0, sc_msg)
        return cand

    if prob_down >= prob_up:
        if sell_candidate and sell_candidate[0] == "SELL":
            return check_candidate_scenario(sell_candidate)
        if buy_candidate and buy_candidate[0] == "BUY":
            return check_candidate_scenario(buy_candidate)
    else:
        if buy_candidate and buy_candidate[0] == "BUY":
            return check_candidate_scenario(buy_candidate)
        if sell_candidate and sell_candidate[0] == "SELL":
            return check_candidate_scenario(sell_candidate)

    # -----------------------------------------------------------------
    # D. EVALUASI ZONA C: HIGH-PROBABILITY TREND / BREAKOUT (> 0.40%)
    # -----------------------------------------------------------------
    is_tight = struct_data.get('market_regime') == 'SIDEWAYS_TIGHT'
    min_c_buy  = 54.0 if (has_buy_confluence or 'BULLISH' in pattern_data.get('pattern_bias', '') or 'UPTREND' in channel_type) else ZONE_C_PROB_MIN
    min_c_sell = 54.0 if (has_sell_confluence or 'BEARISH' in pattern_data.get('pattern_bias', '') or 'BREAKOUT' in pattern_data.get('pattern_bias', '') or 'DOWNTREND' in channel_type) else ZONE_C_PROB_MIN

    # -----------------------------------------------------------------
    # D.0. SNIPER DIRECT ENTRY: Bypass semua filter saat AI >= 70%
    #      Berdasarkan Layer 2 Backtest: WR 83.2%, PF 10.74 pada M15
    #      Filter heuristik (candle, H1, structure) justru menghambat
    #      entry dan menyebabkan bot masuk terlambat → kena SL.
    # -----------------------------------------------------------------
    if prob_up >= SNIPER_DIRECT_PROB_MIN and not is_tight:
        sl = base_sl
        tp = round(sl * RRR_RATIO, 0)
        sniper_desc = f"🎯 SNIPER DIRECT BUY: AI Conviction Sangat Tinggi ({prob_up:.1f}% >= {SNIPER_DIRECT_PROB_MIN:.0f}%)! Bypass filter, langsung entry."
        return check_candidate_scenario(("BUY", "C_SNIPER", sl, tp, sniper_desc))
    elif prob_down >= SNIPER_DIRECT_PROB_MIN and not is_tight:
        sl = base_sl
        tp = round(sl * RRR_RATIO, 0)
        sniper_desc = f"🎯 SNIPER DIRECT SELL: AI Conviction Sangat Tinggi ({prob_down:.1f}% >= {SNIPER_DIRECT_PROB_MIN:.0f}%)! Bypass filter, langsung entry."
        return check_candidate_scenario(("SELL", "C_SNIPER", sl, tp, sniper_desc))

    # -----------------------------------------------------------------
    # D.1. ZONA C REGULER (dengan filter H1, Structure, Candle)
    # -----------------------------------------------------------------
    if prob_up >= min_c_buy and not is_tight:
        if stoch_overbought:
            return "WAIT", "OVERBOUGHT", 0, 0, f"🛑 OVERBOUGHT FILTER: BUY Zona C Dibatalkan! Stoch RSI di puncak (%K={stoch_k:.1f} >= 75)."
        has_structure = (
            struct_data.get('bos_bull_recent', False) or 
            struct_data.get('choch_bull_recent', False) or 
            struct_data.get('market_regime') == 'TRENDING_BULL' or
            is_ema_bull
        )
        if h1_bull and has_structure and is_bull_c:
            if pattern_data and not pattern_data.get('can_buy_safely', True):
                near_res_val = pattern_data.get('nearest_res', m15_res)
                return "WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: BUY Zona C Dibatalkan! Terlalu Dekat Atap Resisten (${near_res_val:.2f})."
            sl = base_sl
            tp = round(sl * 1.5, 0)
            return "BUY", "C", sl, tp, f"🟢 ZONA C BUY (TREND): Keyakinan AI Sangat Kuat ({prob_up:.1f}%) + Tren Makro H1 Bullish + Validasi Structure/EMA!"
        else:
            return "WAIT", "C", 0, 0, f"Zona C Mid: BUY {prob_up:.1f}% menunggu konfirmasi candle/tren H1"

    elif prob_down >= min_c_sell and not is_tight:
        if stoch_oversold:
            return "WAIT", "OVERSOLD", 0, 0, f"🛑 OVERSOLD FILTER: SELL Zona C Dibatalkan! Stoch RSI di dasar (%K={stoch_k:.1f} <= 25)."
        has_structure = (
            struct_data.get('bos_bear_recent', False) or 
            struct_data.get('choch_bear_recent', False) or 
            struct_data.get('market_regime') == 'TRENDING_BEAR' or
            not is_ema_bull
        )
        if (not h1_bull) and has_structure and is_bear_c:
            if pattern_data and not pattern_data.get('can_sell_safely', True):
                near_sup_val = pattern_data.get('nearest_sup', m15_sup)
                return "WAIT", "COLLISION", 0, 0, f"🛑 ANTI-COLLISION: SELL Zona C Dibatalkan! Terlalu Dekat Lantai Support (${near_sup_val:.2f})."
            sl = base_sl
            tp = round(sl * 1.5, 0)
            return "SELL", "C", sl, tp, f"🔴 ZONA C SELL (TREND): Keyakinan AI Sangat Kuat ({prob_down:.1f}%) + Tren Makro H1 Bearish + Validasi Structure/EMA!"
        else:
            return "WAIT", "C", 0, 0, f"Zona C Mid: SELL {prob_down:.1f}% menunggu konfirmasi candle/tren H1"

    else:
        max_p = max(prob_up, prob_down)
        channel_desc = f"Kanal {channel_type} (Slope ${slope:.2f})"
        pattern_desc = f" | Pola: {pattern_data.get('pattern', 'None')}" if pattern_data else ""
        stoch_desc = f" | Stoch: %K={stoch_k:.0f}"
        return "WAIT", "C", 0, 0, f"TERTAHAN MID-ZONE: Area antara {sup_label} & {res_label} [{channel_desc}{pattern_desc}{stoch_desc}]. AI ({max_p:.1f}%) < {ZONE_C_PROB_MIN:.0f}%."
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
            sync_mt5_trades_to_excel(
                model_label=MODEL_LABEL_EXCEL,
                threshold_label=THRESHOLD_LABEL_EXCEL,
                silent=True
            )
        except Exception:
            pass
        return True
    else:
        print(f"⚠️ Gagal Market Close #{pos.ticket}. Code: {res.retcode} ({res.comment})")
        return False

def manage_open_positions(latest_prob_up=50.0, latest_prob_down=50.0, channel_data=None, pattern_data=None, struct_data=None, h1_bull=False):
    """
    Mengelola posisi terbuka M15 secara real-time (Versi 3.2 Adaptive Runner Engine):
    1. Runner Mode vs Boundary Exit:
       - Jika momentum tren makro kuat (Kanal miring tajam / BOS / Pola breakdown), biarkan profit berjalan (Let Profit Run) dengan Dynamic Trailing Buffer ($1.80 s/d $2.50 USD).
       - Jika momentum sempit/konsolidasi, kunci profit pada Trailing Lock (+$1.50) saat retrace.
    2. Auto Break-Even: Pindahkan SL ke entry + $0.20 saat profit >= +$4.00 USD
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

        cur_peak = peak_profits[pos.ticket]

        comment = pos.comment.upper() if pos.comment else ""
        slope = channel_data.get('slope', 0.0) if channel_data else 0.0
        ch_type = channel_data.get('channel_type', 'HORIZONTAL') if channel_data else 'HORIZONTAL'
        pattern = pattern_data.get('pattern', '').upper() if pattern_data else ''
        regime = struct_data.get('market_regime', 'SIDEWAYS') if struct_data else 'SIDEWAYS'

        is_strong_momentum = False
        if pos_type == mt5.ORDER_TYPE_SELL:
            if (
                slope < -0.15 or 
                "DESCENDING" in ch_type or 
                "FALLING" in pattern or 
                "DESCENDING" in pattern or 
                (not h1_bull) or 
                latest_prob_down >= 60.0 or 
                "Z-C" in comment or 
                regime == 'TRENDING_BEAR'
            ):
                is_strong_momentum = True
        else: # BUY
            if (
                slope > 0.15 or 
                "ASCENDING" in ch_type or 
                "RISING" in pattern or 
                "ASCENDING" in pattern or 
                h1_bull or 
                latest_prob_up >= 60.0 or 
                "Z-C" in comment or 
                regime == 'TRENDING_BULL'
            ):
                is_strong_momentum = True

        # 1. RUNNER MODE M15 (MOMENTUM KUAT: LET PROFIT RUN):
        if is_strong_momentum and cur_peak >= 5.00:
            trailing_buffer = 2.50 if cur_peak >= 10.0 else 1.80
            runner_floor = max(3.50, cur_peak - trailing_buffer)
            if profit_usd <= runner_floor:
                if close_position_market(pos, f"Runner TP (+${profit_usd:.2f}) [Peak: ${cur_peak:.2f}]"):
                    peak_profits.pop(pos.ticket, None)
                    continue

        # 2. TRAILING PROFIT LOCK M15 STANDARD (Pernah >= $3.50, kunci minimal $2.50):
        elif ENABLE_TRAILING_LOCK and cur_peak >= TRAILING_TRIGGER_USD and cur_peak < 5.00:
            retrace_limit = max(TRAILING_LOCK_USD, cur_peak - 1.20)
            if profit_usd <= retrace_limit:
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

def manage_pending_orders(sym):
    """
    Memantau pending limit order M15:
    Jika order tidak terjemput dalam PENDING_ORDER_TIMEOUT_CANDLES (45 menit),
    batalkan order otomatis agar tidak tertinggal siklus pergerakan harga baru.
    """
    try:
        pending_orders = mt5.orders_get(symbol=sym)
        if not pending_orders:
            return
        now_ts = time.time()
        max_lifetime_sec = PENDING_ORDER_TIMEOUT_CANDLES * 15 * 60
        for o in pending_orders:
            if o.magic == MAGIC_NUMBER:
                order_age = now_ts - o.time_setup
                if order_age > max_lifetime_sec:
                    print(f"\n⏳ [TIMEOUT] Pending Order #{o.ticket} ({o.comment}) telah aktif {int(order_age/60)} menit (> {int(max_lifetime_sec/60)}m). Membatalkan order agar tidak tersangkut siklus lama...")
                    req = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": o.ticket,
                    }
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"✅ Pending Order #{o.ticket} berhasil dibatalkan otomatis.")
                    else:
                        c = res.comment if res else 'None'
                        print(f"⚠️ Gagal membatalkan pending order #{o.ticket}: {c}")
    except Exception:
        pass

def execute_auto_trade(signal_type, entry_price, sl_pips, tp_pips, zone_type="A", prob_val=50.0, reason_str="", features_dict=None, struct_data=None, atr_val=None):
    all_positions = mt5.positions_get(symbol=symbol)
    positions = [p for p in (all_positions or []) if p.magic == MAGIC_NUMBER]
    if len(positions) > 0:
        print(f"⚠️ Masih ada posisi aktif M15 (Ticket: {positions[0].ticket}). Menunggu trade selesai (No Over-Trading).")
        return

    all_pending = mt5.orders_get(symbol=symbol)
    pending_orders = [o for o in (all_pending or []) if o.magic == MAGIC_NUMBER]
    if len(pending_orders) > 0:
        print(f"⚠️ Masih ada Pending Order aktif M15 (Ticket: #{pending_orders[0].ticket}). Menunggu terjemput atau kedaluwarsa.")
        return

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print("❌ Gagal mengambil tick harga MT5 XAUUSD.")
        return

    # Evaluasi Mode Eksekusi Adaptif (Hybrid):
    # Giant Candle (> 1.35 * ATR) -> Pending Limit Order di 50% Body Retracement
    # Normal Candle (<= 1.35 * ATR) -> Market Order Instan (0-Delay)
    use_pending_limit = False
    exec_price = tick.ask if signal_type == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL
    order_action = mt5.TRADE_ACTION_DEAL
    trade_mode_str = "MARKET ORDER INSTAN (Pure Price Action v3.7)"
    order_comment_zone = f"M15 v3.7 Z-{zone_type}"

    if ENABLE_ADAPTIVE_HYBRID_ENTRY and struct_data and atr_val and atr_val > 0:
        c_range = struct_data.get('cur_range', 0.0)
        c_open  = struct_data.get('c0_open', 0.0)
        c_close = struct_data.get('c0_close', 0.0)
        
        if c_range > (GIANT_CANDLE_ATR_RATIO * atr_val) and c_open > 0 and c_close > 0:
            calc_50 = round((c_open + c_close) / 2.0, 3)
            if signal_type == "BUY" and calc_50 < tick.ask:
                use_pending_limit = True
                exec_price = calc_50
                order_action = mt5.TRADE_ACTION_PENDING
                order_type = mt5.ORDER_TYPE_BUY_LIMIT
                trade_mode_str = f"BUY LIMIT 50% RETRACEMENT (Giant Candle ${c_range:.2f} > {GIANT_CANDLE_ATR_RATIO}x ATR)"
                order_comment_zone = f"M15 v3.8 Z-{zone_type}_50LMT"
            elif signal_type == "SELL" and calc_50 > tick.bid:
                use_pending_limit = True
                exec_price = calc_50
                order_action = mt5.TRADE_ACTION_PENDING
                order_type = mt5.ORDER_TYPE_SELL_LIMIT
                trade_mode_str = f"SELL LIMIT 50% RETRACEMENT (Giant Candle ${c_range:.2f} > {GIANT_CANDLE_ATR_RATIO}x ATR)"
                order_comment_zone = f"M15 v3.8 Z-{zone_type}_50LMT"

    if signal_type == "BUY":
        sl = exec_price - (sl_pips / 10.0)
        tp = exec_price + (tp_pips / 10.0)
    else:
        sl = exec_price + (sl_pips / 10.0)
        tp = exec_price - (tp_pips / 10.0)
        
    filling_mode = get_best_filling_mode(symbol)
        
    request = {
        "action": order_action,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": exec_price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": order_comment_zone,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    color_order = COLOR_GREEN if signal_type == "BUY" else COLOR_RED
    print(f"{color_order}{COLOR_BOLD}🚀 [OPEN {signal_type} - ZONA {zone_type} | {trade_mode_str}] MENGIRIM ORDER KE MT5: {signal_type} {LOT_SIZE} Lot XAUUSD @ ${exec_price:.2f} (SL: ${sl:.2f}, TP: ${tp:.2f} | {sl_pips}pips){COLOR_RESET}")
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f"{color_order}{COLOR_BOLD}🎉 ORDER {signal_type} (ZONA {zone_type} | {trade_mode_str}) BERHASIL DIEKSEKUSI! Ticket: #{result.order}{COLOR_RESET}")
        try:
            sc_key = f"M15_ZONA_{zone_type}_{signal_type}"
            f_dict = features_dict if features_dict is not None else globals().get('last_features_dict', {})
            h4_tr = "BULL" if ('h4_context' in globals() and globals()['h4_context'].get('h4_slope', 0) > 0) else "BEAR"
            scenario_eval.record_entry_context(
                ticket=result.order,
                symbol=symbol,
                timeframe="M15",
                scenario_type=sc_key,
                setup_details={
                    'zone': f"Zona {zone_type}",
                    'mode': trade_mode_str,
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'price': exec_price,
                    'action': signal_type,
                    'model_prob': float(prob_val),
                    'entry_reason': reason_str,
                    'h4_trend': h4_tr
                },
                features_dict=f_dict
            )
        except Exception:
            pass
    else:
        ret_code = result.retcode if result else 'NO_RESPONSE'
        comment = result.comment if result else 'Unknown error / None response'
        print(f"❌ Gagal Eksekusi Order. Retcode Error: {ret_code} (Comment: {comment})")

def main():
    global _lock_socket
    # Proteksi Single Instance: Mencegah 2 script berjalan sekaligus
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", 41230))
    except socket.error:
        print("\n❌ [SINGLE INSTANCE PROTECTION] Bot M15 sudah berjalan di proses lain!")
        print("Mencegah eksekusi ganda yang dapat menyebabkan over-trading.")
        sys.exit(0)

    print("\n" + "="*75)
    print(f"🤖 ROBOT TRADING M15 MULTI-ZONE ADAPTIVE [{BOT_VERSION}]")
    print(f"Pembeda Utama : 3 Zona Bertingkat (A:Boundary, B:Proximity, C:Trend) + Candle Structure")
    print(f"Target Exit   : Trailing Lock (+${TRAILING_LOCK_USD:.2f}) | Auto Break-Even (+${4.00:.2f}) | AI Cut-Loss ({AI_CUTLOSS_REV_PROB:.0f}%)")
    print("Tekan Ctrl+C untuk menghentikan Robot.")
    print("="*75)

    # Sinkronisasi awal saat bot pertama kali dinyalakan
    print(f"{COLOR_CYAN}🔄 Memeriksa & menyinkronkan riwayat trade M15 ke Excel...{COLOR_RESET}")
    try:
        sync_mt5_trades_to_excel(
            model_label=MODEL_LABEL_EXCEL,
            threshold_label=THRESHOLD_LABEL_EXCEL
        )
    except Exception as e:
        print(f"⚠️ Gagal sinkronisasi awal Excel: {e}")

    # Audit awal kondisi pasar & prediksi model saat pertama kali dibuka
    print(f"\n{COLOR_CYAN}🔍 MELAKUKAN AUDIT AWAL STRUKTUR SMC & PREDIKSI MODEL M15 SAAT INI...{COLOR_RESET}")
    res_audit = analyze_market_and_predict()
    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data, h4_context = res_audit
    
    init_sig, init_zone, init_sl, init_tp, init_reason = evaluate_multi_zone_decision(
        prob_up, prob_down, h1_bull, h1_strong_bull, atr_val,
        dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c,
        m15_sup, m15_res, struct_data, channel_data=channel_data, pattern_data=pattern_data, tech_data=tech_data, h4_context=h4_context
    )

    slope_val = channel_data['slope']
    channel_str = f"{channel_data['channel_type']} (Slope: ${slope_val:+.2f}/candle)"
    dyn_sup_str = f"${channel_data['dyn_sup']:.2f} (Jarak: {channel_data['dist_dyn_sup']*100:.2f}%)"
    dyn_res_str = f"${channel_data['dyn_res']:.2f} (Jarak: {channel_data['dist_dyn_res']*100:.2f}%)"

    print("="*75)
    print(f"📊 HASIL AUDIT MODEL M15 (TECHNICAL CONFLUENCE LIVE v3.3):")
    print(f"• Probabilitas AI          : BUY = {prob_up:.1f}%  |  SELL = {prob_down:.1f}% (A:58%, B:65%, C:68%)")
    print(f"• Indikator Teknikal       : {tech_data['summary_desc']}")
    print(f"• Arah Tren Makro H1       : {'BULLISH (Up)' if h1_bull else 'BEARISH (Down)'} (Kuat: {h1_strong_bull})")
    print(f"• Pola Grafik Teknikal     : {pattern_data['pattern']}")
    print(f"• Kanal Regresi Dinamis    : {channel_str}")
    print(f"• Support Miring (Kanal)   : {dyn_sup_str}")
    print(f"• Resisten Miring (Kanal)  : {dyn_res_str}")
    print(f"• Lantai Demand Multi-Day  : ${pattern_data['major_demand']:.2f} | Atap Supply Multi-Day: ${pattern_data['major_supply']:.2f}")
    print(f"• Pivot Terdekat (1-3 Hari): Swing Sup = ${pattern_data['nearest_sup']:.2f} ({pattern_data['dist_near_sup']*100:.2f}%) | Swing Res = ${pattern_data['nearest_res']:.2f} ({pattern_data['dist_near_res']*100:.2f}%)")
    print(f"• Anti-Collision Guard     : Aman BUY? {'✅ Ya' if pattern_data['can_buy_safely'] else '🛑 Bahaya (Dekat Atap)'} | Aman SELL? {'✅ Ya' if pattern_data['can_sell_safely'] else '🛑 Bahaya (Dekat Lantai)'}")
    print(f"• Lantai Demand Horizontal : ${m15_sup:.2f} (Jarak: {dist_sup*100:.2f}%)")
    print(f"• Atap Supply Horizontal   : ${m15_res:.2f} (Jarak: {dist_res*100:.2f}%)")
    print(f"• Karakter Candlestick M15 : Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}%")
    print(f"• Pola Struktur & Regime   : {struct_data['structure_desc']}")
    print(f"• Status Evaluasi Zona     : {init_reason}")
    print(f"• Waktu Eksekusi Order      : Menunggu 5 detik sebelum tutup candle ({CHOSEN_TF})")
    print("="*75 + "\n")

    tf_min = 15
    last_analyzed_candle = None
    
    # Risk Management Tracking (FIX D)
    daily_loss_count = 0
    last_loss_time = 0
    last_loss_price = 0.0
    loss_cooldown_until = 0
    today_date = datetime.now().date()
    prev_positions_count = 0
    last_periodic_sync = time.time()
    last_prob_refresh = time.time()

    # --- 🚀 STARTUP CATCH-UP SCAN (Tidak buang waktu tunggu jika PC baru dinyalakan) ---
    now = datetime.now()
    minutes_past = now.minute % tf_min
    seconds_past = minutes_past * 60 + now.second
    current_candle_time = now.replace(second=0, microsecond=0) - timedelta(minutes=minutes_past)

    print(f"{COLOR_CYAN}🔎 [STARTUP CATCH-UP SCAN] Memeriksa Peluang Segar Candle Terakhir...{COLOR_RESET}")
    all_positions = mt5.positions_get(symbol=symbol)
    my_cur_pos = [p for p in (all_positions or []) if p.magic == MAGIC_NUMBER]
    
    if len(my_cur_pos) > 0:
        print(f"ℹ️ Sedang ada posisi aktif M15 (#{my_cur_pos[0].ticket}). Startup scan melewati eksekusi baru.")
    else:
        if init_sig in ["BUY", "SELL"] and seconds_past <= 180:
            print(f"{COLOR_GREEN}{COLOR_BOLD}⚡ [STARTUP CATCH-UP TRIGGER]: Candle baru berjalan {seconds_past}s dan terdeteksi Sinyal Valid {init_sig} (Zona {init_zone})!{COLOR_RESET}")
            print(f"   Alasan: {init_reason}")
            if AUTO_EXECUTE:
                entry_p = ask_p if init_sig == "BUY" else bid_p
                execute_auto_trade(
                    init_sig, entry_p, init_sl, init_tp, zone_type=init_zone,
                    prob_val=prob_up if init_sig == "BUY" else prob_down,
                    reason_str=init_reason,
                    features_dict=globals().get('last_features_dict', {}),
                    struct_data=struct_data,
                    atr_val=atr_val
                )
                last_analyzed_candle = current_candle_time
        elif init_sig in ["BUY", "SELL"]:
            print(f"ℹ️ Sinyal {init_sig} terdeteksi, namun candle sudah berjalan {minutes_past}m {now.second}s (>3 menit). Menunggu penutupan candle untuk presisi 0-delay.")
        else:
            print(f"ℹ️ Status saat startup: {init_reason}. Bot standby memantau real-time.")

    while True:
        try:
            # 1. LOOP REAL-TIME: Pantau trailing lock, break-even, AI cut-loss, & pending order expiry setiap detik
            manage_open_positions(
                prob_up, prob_down,
                channel_data=channel_data,
                pattern_data=pattern_data,
                struct_data=struct_data,
                h1_bull=h1_bull
            )
            manage_pending_orders(symbol)

            # Deteksi apakah ada posisi M15 yang baru saja tertutup (Hit SL/TP/BE/Cut-Loss)
            all_pos = mt5.positions_get(symbol=symbol)
            cur_positions = [p for p in (all_pos or []) if p.magic == MAGIC_NUMBER]
            cur_count = len(cur_positions)

            if prev_positions_count > 0 and cur_count == 0:
                # FIX D: Cek apakah posisi terakhir ditutup dengan loss -> update cooldown
                try:
                    from datetime import timedelta as _td
                    recent_deals = mt5.history_deals_get(datetime.now() - _td(minutes=5), datetime.now())
                    if recent_deals:
                        for deal in reversed(recent_deals):
                            if deal.magic == MAGIC_NUMBER and deal.symbol == symbol and deal.profit != 0:
                                if deal.profit < 0:
                                    daily_loss_count += 1
                                    last_loss_time = time.time()
                                    last_loss_price = deal.price
                                    loss_cooldown_until = time.time() + (LOSS_COOLDOWN_CANDLES * tf_min * 60)
                                    print(f"\n{COLOR_RED}⚠️ [LOSS DETECTED M15] Loss ${deal.profit:.2f} terdeteksi! Loss hari ini: {daily_loss_count}/{MAX_DAILY_LOSSES}. Cooldown {LOSS_COOLDOWN_CANDLES} candle aktif.{COLOR_RESET}")
                                break
                except Exception:
                    pass

                print(f"\n{COLOR_CYAN}🔔 [DETEKSI EXIT]: Posisi M15 baru saja ditutup. Menyinkronkan update Win/Loss ke Excel...{COLOR_RESET}")
                try:
                    sync_mt5_trades_to_excel(
                        model_label=MODEL_LABEL_EXCEL,
                        threshold_label=THRESHOLD_LABEL_EXCEL
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel: {sync_err}")

            prev_positions_count = cur_count

            # Sinkronisasi berkala ke Excel setiap 180 detik (Real-time safety, mode silent agar tidak merusak tampilan)
            if time.time() - last_periodic_sync >= 180:
                last_periodic_sync = time.time()
                try:
                    sync_mt5_trades_to_excel(
                        model_label=MODEL_LABEL_EXCEL,
                        threshold_label=THRESHOLD_LABEL_EXCEL,
                        silent=True
                    )
                except Exception:
                    pass

            # Perbarui probabilitas live setiap 20 detik agar audit persentase selalu aktual
            if time.time() - last_prob_refresh >= 20:
                last_prob_refresh = time.time()
                try:
                    res_audit = analyze_market_and_predict()
                    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data, h4_context = res_audit
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
            prob_color = COLOR_GREEN if prob_up >= ZONE_A_PROB_MIN else (COLOR_RED if prob_down >= ZONE_A_PROB_MIN else COLOR_YELLOW)
            prob_display = f"{prob_color}BUY:{prob_up:.1f}% | SELL:{prob_down:.1f}%{COLOR_RESET}"
            h1_display = "H1:Bull" if h1_bull else "H1:Bear"

            # Evaluasi status tampilan real-time
            if cur_count > 0:
                p_type = cur_positions[0].type
                if p_type == mt5.ORDER_TYPE_BUY:
                    status_str = f"{COLOR_GREEN}{COLOR_BOLD}HOLDING BUY #{cur_positions[0].ticket}{COLOR_RESET}{pnl_str}"
                else:
                    status_str = f"{COLOR_RED}{COLOR_BOLD}HOLDING SELL #{cur_positions[0].ticket}{COLOR_RESET}{pnl_str}"
            else:
                live_sig, live_zone, _, _, live_reason = evaluate_multi_zone_decision(
                    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val,
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
                    elif "MIRING" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}KANAL MIRING (TUNGGU SETUP){COLOR_RESET}"
                    elif "PROXIMITY" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}PROXIMITY (TUNGGU STRUKTUR){COLOR_RESET}"
                    elif "DEMAND" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}DEMAND (TUNGGU WICK){COLOR_RESET}"
                    elif "SUPPLY" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}SUPPLY (TUNGGU WICK){COLOR_RESET}"
                    elif "H1" in live_reason.upper():
                        status_str = f"{COLOR_YELLOW}TERFILTER TREN H1{COLOR_RESET}"
                    else:
                        status_str = f"{COLOR_YELLOW}TERTAHAN MID-ZONE{COLOR_RESET}"

            stoch_k_val = tech_data.get('stoch_k', 50.0) if tech_data else 50.0
            stoch_disp = f"Stoch:{stoch_k_val:.0f}"
            sys.stdout.write(f"\r⏳ [{CHOSEN_TF}]: {mins:02d}m {secs:02d}s | {prob_display} | {stoch_disp} | Status: {status_str}   ")
            sys.stdout.flush()
            
            # 2. TRIGGER CANDLE: Tepat 5 detik sebelum tutup candle M15 (0-delay)
            if seconds_left <= 5 and last_analyzed_candle != current_candle_time:
                last_analyzed_candle = current_candle_time
                print("\n" + "="*75)
                print(f"⚡ CANDLE M15 MENJELANG TUTUP ({now.strftime('%H:%M:%S')})! EVALUASI MULTI-ZONE ADAPTIVE ENTRY:")
                
                res_audit = analyze_market_and_predict()
                prob_up, prob_down, h1_bull, h1_strong_bull, atr_val, ask_p, bid_p, dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c, m15_sup, m15_res, struct_data, channel_data, pattern_data, tech_data, h4_context = res_audit
                
                final_sig, final_zone, sl_pips, tp_pips, final_reason = evaluate_multi_zone_decision(
                    prob_up, prob_down, h1_bull, h1_strong_bull, atr_val,
                    dist_sup, dist_res, lower_w, upper_w, is_bull_c, is_bear_c,
                    m15_sup, m15_res, struct_data, channel_data=channel_data, pattern_data=pattern_data, tech_data=tech_data
                )
                
                print(f"📊 Probabilitas Final  : BUY = {prob_up:.1f}%  |  SELL = {prob_down:.1f}%")
                print(f"📈 Indikator Teknikal  : {tech_data['summary_desc']}")
                print(f"🛡️ Tren Makro H1        : {'BULLISH' if h1_bull else 'BEARISH'} (Kuat: {h1_strong_bull})")
                print(f"📐 Pola Grafik Teknikal : {pattern_data['pattern']}")
                print(f"📐 Struktur Level SNR   : Lantai Demand = ${m15_sup:.2f} ({dist_sup*100:.2f}%) | Atap Supply = ${m15_res:.2f} ({dist_res*100:.2f}%)")
                print(f"🛡️ Level Pivot Mayor    : Swing Sup = ${pattern_data['nearest_sup']:.2f} ({pattern_data['dist_near_sup']*100:.2f}%) | Swing Res = ${pattern_data['nearest_res']:.2f} ({pattern_data['dist_near_res']*100:.2f}%)")
                print(f"🛡️ Anti-Collision Guard : Safe BUY? {'✅ Ya' if pattern_data['can_buy_safely'] else '🛑 Tidak (Dekat Atap)'} | Safe SELL? {'✅ Ya' if pattern_data['can_sell_safely'] else '🛑 Tidak (Dekat Lantai)'}")
                print(f"🕯️ Karakter Candlestick : Ekor Bawah = {lower_w*100:.1f}% | Ekor Atas = {upper_w*100:.1f}%")
                print(f"📈 Pola Struktur SMC    : {struct_data['structure_desc']}")
                
                if final_sig in ["BUY", "SELL"]:
                    color_sig = COLOR_GREEN if final_sig == "BUY" else COLOR_RED
                    print(f"{color_sig}{COLOR_BOLD}🎯 KEPUTUSAN {final_sig} (ZONA {final_zone}): {final_reason}{COLOR_RESET}")
                    entry_p = ask_p if final_sig == "BUY" else bid_p
                    # Reset daily loss counter jika hari berganti
                    if datetime.now().date() != today_date:
                        today_date = datetime.now().date()
                        daily_loss_count = 0
                    
                    if daily_loss_count >= MAX_DAILY_LOSSES:
                        print(f"DAILY LOSS LIMIT: Sudah {daily_loss_count}x loss hari ini. Bot WAIT sisa hari!")
                    elif time.time() < loss_cooldown_until:
                        remaining = int(loss_cooldown_until - time.time())
                        print(f"LOSS COOLDOWN: Menunggu {remaining}s lagi sebelum entry baru.")
                    elif last_loss_price > 0 and abs(entry_p - last_loss_price) < AREA_LOCKOUT_RANGE and (time.time() - last_loss_time) < 3600:
                        print(f"AREA LOCKOUT: Area ${last_loss_price:.2f} masih terkunci.")
                    elif AUTO_EXECUTE:
                        execute_auto_trade(
                            final_sig, entry_p, sl_pips, tp_pips, zone_type=final_zone,
                            prob_val=prob_up if final_sig == "BUY" else prob_down,
                            reason_str=final_reason,
                            features_dict=globals().get('last_features_dict', {}),
                            struct_data=struct_data,
                            atr_val=atr_val
                        )
                else:
                    print(f"{COLOR_YELLOW}⚠️ KEPUTUSAN DITAHAN: {final_reason}{COLOR_RESET}")
                    
                try:
                    sync_mt5_trades_to_excel(
                        model_label=MODEL_LABEL_EXCEL,
                        threshold_label=THRESHOLD_LABEL_EXCEL
                    )
                except Exception as sync_err:
                    print(f"⚠️ Gagal sinkronisasi Excel: {sync_err}")
                print("="*75)
                
            time.sleep(1)

        except KeyboardInterrupt:
            print("\nRobot Trading Dihentikan oleh User.")
            mt5.shutdown()
            break
        except Exception as loop_err:
            print(f"\n⚠️ [SHIELD M15] Gangguan loop sementara: {loop_err}. Memulihkan dalam 2 detik...")
            time.sleep(2)

if __name__ == "__main__":
    main()
