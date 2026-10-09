"""
=============================================================================
ROBOT TRADING KANONIKAL M15 — 57 FITUR & AI ADAPTIVE SNIPER (v5.0 UNIFIED)
=============================================================================
Single Model Utama Penelitian Skripsi S1 Informatika UPN "Veteran" Yogyakarta:
- Peneliti: Nouval Ditya Maheswara (NIM: 123230165)
- Algoritma: LightGBM Tuned (57 Fitur Kausal: Spasial SMC + MTF H1/H4 + DXY + Volatilitas)
- Horizon Prediksi: 75 Menit (5 Candle M15 / T+5)
- Arsitektur: Full AI End-to-End Decision (Bebas Heuristic Trap "Tertahan Mid-Zone")
- Seleksi Sinyal: Selective Prediction (>= 60% Normal Entry, >= 65% Sniper High-Precision)
- Eksekusi: Lot 0.01 Standard, SL Ketat -$6.50, TP Adaptif +$8.50 s/d +$11.00
- Manajemen Exit: Multi-Tier Trailing Lock, BEP Impas (+ $0.20), & 75-Min Horizon Close
- Sinkronisasi: Terhubung langsung dengan Web Dashboard & Auto-Logger Excel
=============================================================================
"""

import os
import sys
import time
import socket
import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import warnings
warnings.filterwarnings('ignore')

# Auto-Logger forward testing Excel
from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel

_lock_socket = None
INSTANCE_PORT = 48901

def acquire_single_instance_lock():
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', INSTANCE_PORT))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False

class _SafeStream:
    def __init__(self, log_name="bot_m15_unified.log"):
        self.log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_name)
    def write(self, s):
        if not s: return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(s)
        except Exception: pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = _SafeStream()
elif hasattr(sys.stdout, 'reconfigure'):
    try: sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

if sys.stderr is None: sys.stderr = _SafeStream()
elif hasattr(sys.stderr, 'reconfigure'):
    try: sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TELEMETRY_M15_PATH = os.path.join(BASE_DIR, "telemetry_m15.json")
TELEMETRY_PRO_PATH = os.path.join(BASE_DIR, "telemetry_m15_pro.json")
EXCEL_M15_PATH     = os.path.join(BASE_DIR, "Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx")

MODEL_PATH_PRIMARY  = os.path.join(BASE_DIR, "model_m15_zone_integrated_50.pkl")
MODEL_PATH_FALLBACK = os.path.join(BASE_DIR, "model_lightgbm_xauusd.pkl")

# Terminal MT5 Exness Utama (Akun 463897979 / Exness-MT5Trial17)
MT5_EXNESS = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
ACTIVE_MT5_PATH = MT5_EXNESS

SYMBOL = "XAUUSD"
MAGIC_M15 = 123242      # Magic Utama Skripsi v4.2
ACTIVE_MAGICS = [MAGIC_M15, 123230]

LOT_SIZE = 0.01

# Manajemen Resiko & Target
SL_POINTS_FIXED   = 65.0   # Stop Loss Ketat $6.50
TP_NORMAL_POINTS  = 85.0   # Take Profit Normal $8.50 (RRR 1:1.31)
TP_SNIPER_POINTS  = 110.0  # Take Profit Sniper $11.00 (RRR 1:1.69)

CONF_ENTRY_MIN    = 60.0   # Threshold Selective Entry (60%)
CONF_SNIPER_MIN   = 65.0   # Threshold Sniper High-Precision (65%)

# Parameter Trailing & BEP (Hasil Analisis Kausal Counterfactual)
TIER1_TRIGGER_USD = 2.50   # Floating +$2.50 (+25 pips) -> Kunci BEP +$0.20
TIER1_LOCK_USD    = 0.20
TIER2_TRIGGER_USD = 4.50   # Floating +$4.50 (+45 pips) -> Kunci minimal +$2.00
TIER2_LOCK_USD    = 2.00
TIER3_TRIGGER_USD = 7.00   # Floating +$7.00 (+70 pips) -> Kunci minimal +$4.50
TIER3_LOCK_USD    = 4.50
TIER4_TRIGGER_USD = 10.00  # Floating >= $10.00 -> Trailing $2.50 di bawah puncak
TIER4_TRAILING_BUFFER = 2.50

ENABLE_HYBRID_SMART_EXIT = True
ENABLE_75M_HORIZON_CLOSE = True
ENABLE_AI_CUTLOSS        = True
AI_CUTLOSS_REV_PROB      = 65.0

peak_profits = {}

FEATURES_65 = [
    # 1-3. Geometri Lilin
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 
    # 4-5. SMC Imbalance
    'FVG_Bull', 'FVG_Bear', 
    # 6-7. Struktur SNR
    'Dist_Support', 'Dist_Resistance',
    # 8-11. Struktur Tren
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    # 12-13. Likuiditas Sweep
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 
    # 14-15. Order Block Kausal t-2
    'Order_Block_Bull', 'Order_Block_Bear',
    # 16-19. Fibonacci Retracement
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    # 20-22. Osilator & Volatilitas
    'RSI_14', 'BB_Bandwidth', 'BB_Pos',
    # 23-25. Return Historis
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    # 26-29. Intermarket DXY Baseline
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    # 30-32. Kalender Makro
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    # 33-38. MTF H1 & H4
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    # 39-44. Dinamika Lilin & Indikator
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20',
    # 45-50. Integrasi Zona Spasial
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear',
    # 51-56. EMA 9/26 M15 Ribbon
    'EMA_9_Cross_26_Bull', 'Dist_EMA9_M15', 'Dist_EMA26_M15', 'Spread_EMA_9_26',
    'Pullback_EMA_Bull', 'Pullback_EMA_Bear',
    # 57-65. DXY Price Action & SMT POI
    'DXY_Dist_Resistance', 'DXY_Dist_Support',
    'DXY_At_Supply_POI', 'DXY_At_Demand_POI',
    'DXY_RSI_14', 'DXY_BOS_Bull', 'DXY_BOS_Bear',
    'SMT_Divergence_Bull', 'SMT_Divergence_Bear'
]
FEATURES_50 = FEATURES_65
FEATURES_57 = FEATURES_65

def log_m15(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts} WIB] [M15 KANONIKAL] {msg}"
    print(formatted, flush=True)

def write_telemetries(data):
    try:
        temp_path = TELEMETRY_M15_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(temp_path, TELEMETRY_M15_PATH)
    except Exception:
        pass

def connect_mt5():
    global SYMBOL
    log_m15(f"Menghubungkan ke Terminal MT5 Exness di: {ACTIVE_MT5_PATH}...")
    if ACTIVE_MT5_PATH and os.path.exists(ACTIVE_MT5_PATH):
        if not mt5.initialize(path=ACTIVE_MT5_PATH):
            if not mt5.initialize():
                log_m15(f"GAGAL Inisialisasi MT5: {mt5.last_error()}")
                return False
    else:
        if not mt5.initialize():
            log_m15(f"GAGAL Inisialisasi MT5: {mt5.last_error()}")
            return False

    acc = mt5.account_info()
    if acc:
        log_m15(f"🟢 TERHUBUNG MT5! Akun: {acc.login} | Server: {acc.server} | Saldo: ${acc.balance:.2f} {acc.currency}")
    
    ti = mt5.terminal_info()
    if ti and not ti.trade_allowed:
        log_m15("⚠️ PERHATIAN: 'Algo Trading' di Terminal MT5 sedang NONAKTIF (merah)! Klik tombol 'Algo Trading' (Ctrl+E) di toolbar MT5 agar bot diizinkan membuka posisi.")
    
    if not mt5.symbol_info(SYMBOL):
        if mt5.symbol_info("XAUUSDm"):
            SYMBOL = "XAUUSDm"
        elif mt5.symbol_info("GOLD"):
            SYMBOL = "GOLD"
    mt5.symbol_select(SYMBOL, True)
    return True

def extract_50_features(df_m15, df_h1, df_h4, df_dxy):
    """Menghitung 50 Fitur Matematika Spasial & Kausal Bebas Leakage + Integrasi Zona"""
    df = df_m15.copy()
    range_m15 = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_m15
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_m15
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_m15

    df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
    df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)

    df['Swing_High_20'] = df['high'].shift(1).rolling(20).max()
    df['Swing_Low_20']  = df['low'].shift(1).rolling(20).min()
    df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
    df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']

    df['BOS_Bull']  = (df['close'] > df['Swing_High_20']).astype(int)
    df['BOS_Bear']  = (df['close'] < df['Swing_Low_20']).astype(int)

    trend_slow = df['close'].pct_change(20)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
    df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

    # BEBAS LEAKAGE: Order block lookback historis shift(2)
    is_bear_c = df['close'] < df['open']
    is_bull_c = df['close'] > df['open']
    body_sz = (df['close'] - df['open']).abs()
    avg_body = body_sz.rolling(20).mean()
    imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
    imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
    df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
    df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

    lookback_fibo = 100
    roll_high = df['high'].rolling(lookback_fibo).max()
    roll_low  = df['low'].rolling(lookback_fibo).min()
    roll_range = (roll_high - roll_low) + 1e-6
    df['Fibo_Pos_100'] = (df['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)
    df['Fibo_Dist_382'] = (df['close'] - fibo_382) / df['close']
    df['Fibo_Dist_500'] = (df['close'] - fibo_500) / df['close']
    df['Fibo_Dist_618'] = (df['close'] - fibo_618) / df['close']

    delta15 = df['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

    sma20 = df['close'].rolling(20).mean()
    std20 = df['close'].rolling(20).std()
    df['BB_Bandwidth'] = (4 * std20) / (sma20 + 1e-9)
    df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

    df['XAU_Return_1'] = df['close'].pct_change(1)
    df['XAU_Return_3'] = df['close'].pct_change(3)
    df['XAU_Return_5'] = df['close'].pct_change(5)

    if df_dxy is not None and len(df_dxy) > 0:
        dxy_close = df_dxy['close'].reindex(df.index, method='ffill').bfill()
    else:
        dxy_close = df['close'] * 0 + 104.0

    df['DXY_Return_1'] = dxy_close.pct_change(1).fillna(0)
    df['DXY_Return_3'] = dxy_close.pct_change(3).fillna(0)
    df['DXY_Trend'] = (dxy_close > dxy_close.rolling(20).mean()).astype(int)
    df['XAU_DXY_Ratio'] = df['close'] / (dxy_close + 1e-6)
    df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

    day_of_month = df.index.day
    weekday = df.index.weekday
    df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
    df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
    df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

    # MTF H1 BASELINE STABIL (50, 200) - TERBUKTI CUAN +$340 DI OOS
    if df_h1 is not None and len(df_h1) > 0:
        ema50_h1 = df_h1['close'].ewm(span=50, adjust=False).mean()
        ema200_h1 = df_h1['close'].ewm(span=200, adjust=False).mean()
        h1_bull = (df_h1['close'] > ema50_h1).astype(int)
        h1_strong = (ema50_h1 > ema200_h1).astype(int)
        h1_dist = (df_h1['close'] - ema50_h1) / (df_h1['close'] + 1e-9)
        df['Trend_H1_Bull']   = h1_bull.reindex(df.index, method='ffill').fillna(0)
        df['Trend_H1_Strong'] = h1_strong.reindex(df.index, method='ffill').fillna(0)
        df['H1_Dist_EMA50']   = h1_dist.reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H1_Bull'] = 1; df['Trend_H1_Strong'] = 1; df['H1_Dist_EMA50'] = 0.0

    # MTF H4 BASELINE STABIL (50, 200)
    if df_h4 is not None and len(df_h4) > 0:
        ema50_h4 = df_h4['close'].ewm(span=50, adjust=False).mean()
        ema200_h4 = df_h4['close'].ewm(span=200, adjust=False).mean()
        h4_bull = (df_h4['close'] > ema50_h4).astype(int)
        h4_strong = (ema50_h4 > ema200_h4).astype(int)
        h4_dist = (df_h4['close'] - ema50_h4) / (df_h4['close'] + 1e-9)
        df['Trend_H4_Bull']   = h4_bull.reindex(df.index, method='ffill').fillna(0)
        df['Trend_H4_Strong'] = h4_strong.reindex(df.index, method='ffill').fillna(0)
        df['H4_Dist_EMA50']   = h4_dist.reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H4_Bull'] = 1; df['Trend_H4_Strong'] = 1; df['H4_Dist_EMA50'] = 0.0

    is_bull = (df['close'] > df['open']).astype(int)
    is_bear = (df['close'] < df['open']).astype(int)
    df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
    df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

    # ATR & ADX BASELINE STABIL 14
    high_diff = df['high'].diff()
    low_diff  = -df['low'].diff()
    plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low']  - df['close'].shift()).abs()
    ], axis=1).max(axis=1)

    atr14 = tr.rolling(14).mean() + 1e-6
    df['ATR_14'] = atr14
    plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
    df['ADX_14'] = dx.rolling(14).mean()

    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

    # 6 FITUR INTEGRASI ZONA KE DALAM AI (MENGHILANGKAN FILTER KAKU LUAR)
    df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
    df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

    # 6 FITUR EMA 9/26 M15 RIBBON (v5.2)
    ema9_m15  = df['close'].ewm(span=9, adjust=False).mean()
    ema26_m15 = df['close'].ewm(span=26, adjust=False).mean()
    df['EMA_9_Cross_26_Bull'] = (ema9_m15 > ema26_m15).astype(int)
    df['Dist_EMA9_M15']  = (df['close'] - ema9_m15) / df['close']
    df['Dist_EMA26_M15'] = (df['close'] - ema26_m15) / df['close']
    df['Spread_EMA_9_26'] = (ema9_m15 - ema26_m15) / df['close']
    df['Pullback_EMA_Bull'] = ((df['EMA_9_Cross_26_Bull'] == 1) & (df['low'] <= ema9_m15) & (df['close'] > ema9_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
    df['Pullback_EMA_Bear'] = ((df['EMA_9_Cross_26_Bull'] == 0) & (df['high'] >= ema9_m15) & (df['close'] < ema9_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)

    # 9 FITUR STRUKTUR DXY PRICE ACTION & SMT POI (v5.2)
    if df_dxy is not None and len(df_dxy) > 0:
        dxy_sync = df_dxy.reindex(df.index, method='ffill').bfill()
        dxy_c = dxy_sync['close']
        dxy_h = dxy_sync['high']
        dxy_l = dxy_sync['low']
    else:
        dxy_c = pd.Series(104.0, index=df.index)
        dxy_h = pd.Series(104.0, index=df.index)
        dxy_l = pd.Series(104.0, index=df.index)

    dxy_swing_high = dxy_h.shift(1).rolling(20).max().bfill()
    dxy_swing_low  = dxy_l.shift(1).rolling(20).min().bfill()
    df['DXY_Dist_Resistance'] = (dxy_swing_high - dxy_c) / (dxy_c + 1e-6)
    df['DXY_Dist_Support']    = (dxy_c - dxy_swing_low) / (dxy_c + 1e-6)
    df['DXY_At_Supply_POI']   = (df['DXY_Dist_Resistance'] <= 0.0010).astype(int)
    df['DXY_At_Demand_POI']   = (df['DXY_Dist_Support'] <= 0.0010).astype(int)

    dxy_delta = dxy_c.diff()
    dxy_gain  = (dxy_delta.where(dxy_delta > 0, 0)).rolling(14).mean()
    dxy_loss  = (-dxy_delta.where(dxy_delta < 0, 0)).rolling(14).mean()
    df['DXY_RSI_14'] = 100 - (100 / (1 + (dxy_gain / (dxy_loss + 1e-6))))

    df['DXY_BOS_Bull'] = (dxy_c > dxy_swing_high).astype(int)
    df['DXY_BOS_Bear'] = (dxy_c < dxy_swing_low).astype(int)

    xau_ll = df['low'] < df['low'].shift(1).rolling(10).min()
    dxy_fail_hh = dxy_h <= dxy_h.shift(1).rolling(10).max()
    df['SMT_Divergence_Bull'] = (xau_ll & dxy_fail_hh).astype(int)

    xau_hh = df['high'] > df['high'].shift(1).rolling(10).max()
    dxy_fail_ll = dxy_l >= dxy_l.shift(1).rolling(10).min()
    df['SMT_Divergence_Bear'] = (xau_hh & dxy_fail_ll).astype(int)

    return df

extract_57_features = extract_50_features  # Alias backward compatibility
extract_65_features = extract_50_features

def load_canonical_model():
    for p in [MODEL_PATH_PRIMARY, MODEL_PATH_FALLBACK]:
        if os.path.exists(p):
            try:
                m = joblib.load(p)
                n_f = getattr(m, 'n_features_in_', 0)
                if n_f in [65, 50]:
                    log_m15(f"✅ Model Kanonikal {n_f} Fitur (v5.2 SMT POI) Berhasil Dimuat dari: {p}")
                    return m
            except Exception as e:
                log_m15(f"Gagal memuat {p}: {e}")
    log_m15("❌ ERROR: Model kanonikal (65/50 fitur) tidak ditemukan!")
    sys.exit(1)

def get_best_filling_mode():
    """Mendeteksi mode filling order yang didukung broker (Exness FOK = 1, IOC = 2)"""
    try:
        s_info = mt5.symbol_info(SYMBOL)
        if s_info:
            if s_info.filling_mode == 1:
                return mt5.ORDER_FILLING_FOK
            elif s_info.filling_mode == 2:
                return mt5.ORDER_FILLING_IOC
            elif s_info.filling_mode == 4:
                return mt5.ORDER_FILLING_RETURN
            elif s_info.filling_mode & 1:
                return mt5.ORDER_FILLING_FOK
    except Exception:
        pass
    return mt5.ORDER_FILLING_FOK

def close_position_market(pos, reason="Market Close"):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick: return False
    is_buy = (pos.type == mt5.ORDER_TYPE_BUY)
    price = tick.bid if is_buy else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": pos.ticket,
        "symbol": SYMBOL,
        "volume": pos.volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": pos.magic,
        "comment": f"Close_{reason[:20]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_best_filling_mode(),
    }
    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        log_m15(f"🎯 POSISI #{pos.ticket} DITUTUP: {reason} | Harga: ${price:.2f}")
        return True
    return False

_last_auto_sync_ts = 0
_last_active_pos_count = 0

def manage_open_positions(prob_up, prob_down):
    """Manajemen Exit Real-Time: Multi-Tier Trailing, BEP Impas (+ $0.20), & Horizon Close"""
    global peak_profits, _last_auto_sync_ts, _last_active_pos_count
    now_ts = time.time()
    positions = mt5.positions_get(symbol=SYMBOL)
    my_positions = [p for p in (positions or []) if p.magic in ACTIVE_MAGICS]

    # Auto-sync jika posisi baru saja tertutup atau secara berkala
    if (len(my_positions) < _last_active_pos_count) or (now_ts - _last_auto_sync_ts >= 25):
        _last_auto_sync_ts = now_ts
        try:
            sync_mt5_trades_to_excel(
                excel_path=EXCEL_M15_PATH,
                magic_number=MAGIC_M15,
                model_label="LightGBM v5.2 SMC/DXY M15 (65 Fitur)",
                sheet_title="Trade Log Pure 100 (v4.2)",
                summary_sheet_title="Ringkasan Statistik (v4.2)",
                silent=True
            )
        except Exception:
            pass
    _last_active_pos_count = len(my_positions)

    if not my_positions:
        peak_profits.clear()
        return 0, 0.0

    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        return len(my_positions), 0.0

    total_float = 0.0
    now_ts = time.time()

    for pos in my_positions:
        is_buy = (pos.type == mt5.ORDER_TYPE_BUY)
        cur_p = tick.bid if is_buy else tick.ask
        entry_p = pos.price_open
        sl = pos.sl
        
        profit_usd = (cur_p - entry_p) * pos.volume * 100.0 if is_buy else (entry_p - cur_p) * pos.volume * 100.0
        total_float += profit_usd

        # Update peak profit
        if pos.ticket not in peak_profits:
            peak_profits[pos.ticket] = profit_usd
        else:
            if profit_usd > peak_profits[pos.ticket]:
                peak_profits[pos.ticket] = profit_usd

        cur_peak = peak_profits[pos.ticket]
        age_min = (now_ts - pos.time) / 60.0

        # 1. Multi-Tier Dynamic Trailing & BEP Lock
        if ENABLE_HYBRID_SMART_EXIT:
            target_sl = None
            tier_label = ""
            
            # Tier 4: Peak >= $10.00 (+100 pips) -> Trailing $2.50 Buffer di bawah peak
            if cur_peak >= TIER4_TRIGGER_USD:
                target_sl = (cur_p - TIER4_TRAILING_BUFFER) if is_buy else (cur_p + TIER4_TRAILING_BUFFER)
                tier_label = f"Tier 4 Trailing ($2.50 Buffer) @ ${target_sl:.2f}"
            # Tier 3: Peak >= $7.00 (+70 pips) -> Kunci profit minimal +$4.50 (+45 pips)
            elif cur_peak >= TIER3_TRIGGER_USD:
                target_sl = (entry_p + TIER3_LOCK_USD) if is_buy else (entry_p - TIER3_LOCK_USD)
                tier_label = f"Tier 3 Lock (+$4.50) @ ${target_sl:.2f}"
            # Tier 2: Peak >= $4.50 (+45 pips) -> Kunci profit minimal +$2.00 (+20 pips)
            elif cur_peak >= TIER2_TRIGGER_USD:
                target_sl = (entry_p + TIER2_LOCK_USD) if is_buy else (entry_p - TIER2_LOCK_USD)
                tier_label = f"Tier 2 Lock (+$2.00) @ ${target_sl:.2f}"
            # Tier 1: Peak >= $2.50 (+25 pips) -> Pindahkan ke BEP (+ $0.20 buffer penyelamat profit)
            elif cur_peak >= TIER1_TRIGGER_USD:
                target_sl = (entry_p + TIER1_LOCK_USD) if is_buy else (entry_p - TIER1_LOCK_USD)
                tier_label = f"Tier 1 BEP (+ $0.20) @ ${target_sl:.2f}"

            if target_sl is not None:
                should_update = False
                if is_buy and (sl < target_sl):
                    should_update = True
                elif not is_buy and (sl == 0 or sl > target_sl):
                    should_update = True
                
                if should_update:
                    req_sl = {
                        "action": mt5.TRADE_ACTION_SLTP,
                        "position": pos.ticket,
                        "symbol": SYMBOL,
                        "sl": round(target_sl, 2),
                        "tp": pos.tp
                    }
                    res_sl = mt5.order_send(req_sl)
                    if res_sl and res_sl.retcode == mt5.TRADE_RETCODE_DONE:
                        log_m15(f"🛡️ [SL-LOCK] Posisi #{pos.ticket} diperbarui: {tier_label} | Floating: +${profit_usd:.2f}")

        # 2. Thesis Horizon 75-Minute Auto-Close (5 Candle M15)
        if ENABLE_75M_HORIZON_CLOSE and age_min >= 74.0 and profit_usd > 0.50:
            if close_position_market(pos, f"Thesis 75M Horizon Exit (+${profit_usd:.2f}) [Candle 5 ({int(age_min)}m)]"):
                peak_profits.pop(pos.ticket, None)
                continue

        # 3. Smart AI Early Cut-Loss (Sinyal Berbalik Tajam >= 65%)
        if ENABLE_AI_CUTLOSS and profit_usd < -2.00:
            if is_buy and prob_down >= AI_CUTLOSS_REV_PROB:
                if close_position_market(pos, f"AI Cut-Loss (Reversal SELL {prob_down:.1f}%)"):
                    peak_profits.pop(pos.ticket, None)
                    continue
            elif not is_buy and prob_up >= AI_CUTLOSS_REV_PROB:
                if close_position_market(pos, f"AI Cut-Loss (Reversal BUY {prob_up:.1f}%)"):
                    peak_profits.pop(pos.ticket, None)
                    continue

    return len(my_positions), total_float

def execute_market_order(signal_type, tp_points, sl_points, reason_desc):
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        log_m15("Gagal mengambil harga pasar terkini!")
        return False

    is_buy = (signal_type == "BUY")
    price = tick.ask if is_buy else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    point = 0.1  # 1 pt = $0.10
    sl_price = round(price - (sl_points * point) if is_buy else price + (sl_points * point), 2)
    tp_price = round(price + (tp_points * point) if is_buy else price - (tp_points * point), 2)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 20,
        "magic": MAGIC_M15,
        "comment": f"M15_AI_{signal_type}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_best_filling_mode(),
    }

    log_m15(f"🚀 MENGIRIM ORDER {signal_type} @ ${price:.2f} | SL: ${sl_price:.2f} (-${sl_points/10:.2f}) | TP: ${tp_price:.2f} (+${tp_points/10:.2f}) | {reason_desc}")
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log_m15(f"✅ ORDER {signal_type} BERHASIL DIEKSEKUSI! Ticket: #{result.order}")
        # Sinkronkan rekap excel tanpa menghapus hasil sebelumnya
        try:
            sync_mt5_trades_to_excel(
                excel_path=EXCEL_M15_PATH,
                magic_number=MAGIC_M15,
                model_label="LightGBM v5.2 SMC/DXY M15 (65 Fitur)",
                sheet_title="Trade Log Pure 100 (v4.2)",
                summary_sheet_title="Ringkasan Statistik (v4.2)"
            )
        except Exception as sync_e:
            log_m15(f"Gagal sinkronisasi Excel: {sync_e}")
        return True
    else:
        err = result.comment if result else mt5.last_error()
        log_m15(f"❌ ORDER GAGAL: {err}")
        if (result and getattr(result, 'retcode', 0) == 10027) or ("AutoTrading disabled" in str(err)):
            log_m15("⚠️ PENYEBAB: Tombol 'Algo Trading' di toolbar MetaTrader 5 sedang NONAKTIF (merah)! Tekan 'Algo Trading' (Ctrl+E) di MT5 agar diizinkan open posisi.")
        return False

def run_unified_loop():
    if not acquire_single_instance_lock():
        log_m15("⚠️ Bot M15 sudah aktif berjalan di latar belakang (port 48901 terkunci). Proses ini keluar otomatis.")
        sys.exit(0)

    log_m15("="*80)
    log_m15("🚀 BOT M15 AKTIF — 65 FITUR & AI ADAPTIVE SNIPER (v5.2 DXY SMT POI ENGINE)")
    log_m15("Akun Utama: Exness-MT5Trial17 | Port Lock: 48901")
    log_m15("="*80)

    if not connect_mt5():
        log_m15("Menunggu 5 detik sebelum coba koneksi ulang...")
        time.sleep(5)
        return

    model = load_canonical_model()
    last_eval_time = None

    while True:
        try:
            if mt5.terminal_info() is None:
                log_m15("Koneksi MT5 terputus, mencoba menyambungkan kembali...")
                connect_mt5()
                time.sleep(2)
                continue

            rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 350)
            if rates_m15 is None or len(rates_m15) < 310:
                time.sleep(2)
                continue

            last_bar = rates_m15[-1]
            current_bar_time = last_bar['time']
            cur_price = last_bar['close']

            now_ts = int(time.time())
            seconds_in_bar = now_ts % 900
            seconds_left = 900 - seconds_in_bar
            mins_left = seconds_left // 60
            secs_left = seconds_left % 60

            # Ekstrak 65 Fitur (Termasuk M15 EMA Ribbon & DXY PA + SMT POI)
            rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
            rates_h4 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 50)
            try: rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 200)
            except Exception: rates_dxy = None

            df_m = pd.DataFrame(rates_m15); df_m['time'] = pd.to_datetime(df_m['time'], unit='s'); df_m.set_index('time', inplace=True)
            df_1 = pd.DataFrame(rates_h1) if rates_h1 is not None else None
            if df_1 is not None: df_1['time'] = pd.to_datetime(df_1['time'], unit='s'); df_1.set_index('time', inplace=True)
            df_4 = pd.DataFrame(rates_h4) if rates_h4 is not None else None
            if df_4 is not None: df_4['time'] = pd.to_datetime(df_4['time'], unit='s'); df_4.set_index('time', inplace=True)
            df_x = pd.DataFrame(rates_dxy) if rates_dxy is not None else None
            if df_x is not None: df_x['time'] = pd.to_datetime(df_x['time'], unit='s'); df_x.set_index('time', inplace=True)

            df_feats = extract_65_features(df_m, df_1, df_4, df_x)
            latest_vector = df_feats[FEATURES_65].iloc[-1:]

            # Prediksi Probabilitas Pure AI 65 Fitur
            probs = model.predict_proba(latest_vector)[0]
            prob_up = round(float(probs[1]) * 100, 1)
            prob_down = round(float(probs[0]) * 100, 1)

            # Kelola Posisi Aktif (Trailing Lock, BEP, Horizon Exit)
            holding_trades, floating_pnl = manage_open_positions(prob_up, prob_down)

            # Logika AI Adaptive Selective Prediction
            signal_candidate = "STANDBY"
            status_str = f"STANDBY (AI {max(prob_up, prob_down):.1f}% < 60%)"
            tp_pts = TP_NORMAL_POINTS
            sl_pts = SL_POINTS_FIXED

            if prob_up >= CONF_ENTRY_MIN and prob_up > prob_down:
                signal_candidate = "BUY"
                if prob_up >= CONF_SNIPER_MIN:
                    tp_pts = TP_SNIPER_POINTS
                    status_str = f"🟢 AI SNIPER BUY: Prob {prob_up:.1f}% >= 65% | Target TP +$11.00 | SL -$6.50"
                else:
                    tp_pts = TP_NORMAL_POINTS
                    status_str = f"🟢 AI NORMAL BUY: Prob {prob_up:.1f}% >= 60% | Target TP +$8.50 | SL -$6.50"

            elif prob_down >= CONF_ENTRY_MIN and prob_down > prob_up:
                signal_candidate = "SELL"
                if prob_down >= CONF_SNIPER_MIN:
                    tp_pts = TP_SNIPER_POINTS
                    status_str = f"🔴 AI SNIPER SELL: Prob {prob_down:.1f}% >= 65% | Target TP +$11.00 | SL -$6.50"
                else:
                    tp_pts = TP_NORMAL_POINTS
                    status_str = f"🔴 AI NORMAL SELL: Prob {prob_down:.1f}% >= 60% | Target TP +$8.50 | SL -$6.50"

            m15_sup = round(float(df_feats['Swing_Low_20'].iloc[-1]), 2)
            m15_res = round(float(df_feats['Swing_High_20'].iloc[-1]), 2)
            h1_trend_str = "BULLISH" if df_feats['Trend_H1_Bull'].iloc[-1] == 1 else "BEARISH"

            # Eksekusi jika candle baru terkonfirmasi atau pada 5 detik sebelum pergantian candle
            if last_eval_time != current_bar_time:
                last_eval_time = current_bar_time
                log_m15(f"Lilin M15 Baru: Close ${cur_price:.2f} | AI Buy: {prob_up:.1f}%, Sell: {prob_down:.1f}% | {status_str}")
                
                if signal_candidate in ["BUY", "SELL"]:
                    if holding_trades == 0:
                        execute_market_order(signal_candidate, tp_pts, sl_pts, status_str)
                    else:
                        log_m15(f"Posisi {signal_candidate} ditahan karena ada {holding_trades} trade M15 yang sedang berjalan.")

            # Tulis Telemetri Real-Time ke Kedua File Dashboard
            telemetry_payload = {
                "timeframe": "M15",
                "prob_buy": prob_up,
                "prob_sell": prob_down,
                "h1_trend": h1_trend_str,
                "mins_left": mins_left,
                "secs_left": secs_left,
                "seconds_left": seconds_left,
                "status_str": status_str,
                "stoch_k": round(float(df_feats['RSI_14'].iloc[-1]), 1),
                "ask_p": round(cur_price + 0.15, 2),
                "bid_p": round(cur_price, 2),
                "m15_sup": m15_sup,
                "m15_res": m15_res,
                "holding_trades": holding_trades,
                "floating_pnl": round(floating_pnl, 2),
                "is_unified": True,
                "timestamp": time.time()
            }
            write_telemetries(telemetry_payload)

            time.sleep(1)

        except Exception as e:
            log_m15(f"Error loop M15 Kanonikal: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run_unified_loop()
