"""
=============================================================================
🏆 TRADING BOT M15 PRO V6.0 DUAL-ENGINE — ARSITEKTUR HYBRID DUAL-AGENT
=============================================================================
Arsitektur Komerisal & Hak Paten V6.0:
- Dual-Engine Regime Switching:
    1. HEAD 1: Trend Expansion Engine (65 Fitur Kausal Skripsi)
       * Domain: Momentum kuat (ADX >= 24.0, BB Bandwidth membesar)
       * TP: +$8.50 s/d +$11.00 | SL: -$6.50
    2. HEAD 2: Mean Reversion & Micro-Sniper (77 Fitur Institusional PRO)
       * Domain: Pasar jenuh / sideways / reversal (ADX < 20.0 atau Stoch RSI >= 80 / <= 20)
       * TP: +$9.50 s/d +$12.50 | SL: -$5.00 Ketat (Shockwave Crash Shield)
    3. META-ARBITER GATING:
       * Mengeliminasi 1.454 trade konflik / tabrakan antar model
       * Hanya mengeksekusi sinyal high-conviction (>= 65%) di zona transisi
- Trailing / Lock 2-Tier:
    * Tier 1 (BEP Lock): Floating >= +$2.20 -> Kunci SL ke Entry +$0.30
    * Tier 2 (Profit Lock): Floating >= +$5.50 -> Kunci SL ke Entry +$3.00
- Magic Number: 155701 (Hedging mode, isolasi total dari Bot Skripsi 123242)
- Port Socket Lock: 48903 (Single Instance Safeguard)
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
from datetime import datetime
import MetaTrader5 as mt5
import warnings
warnings.filterwarnings('ignore')

# Auto-Logger forward testing Excel
from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel

_lock_socket = None

class _SafeStream:
    def __init__(self, log_name="bot_m15_pro.log"):
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
TELEMETRY_PATH   = os.path.join(BASE_DIR, "telemetry_m15_pro.json")
EXCEL_PRO_PATH   = os.path.join(BASE_DIR, "Laporan_Forward_Testing_M15_PRO.xlsx")
MODEL_TREND_PATH = os.path.join(BASE_DIR, "model_lightgbm_xauusd.pkl")           # Head 1 (65 Fitur)
MODEL_REV_PATH   = os.path.join(BASE_DIR, "model_m15_pro_77_features.pkl")        # Head 2 (77 Fitur)

INSTANCE_PORT = 48903

def acquire_single_instance_lock():
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', INSTANCE_PORT))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False

# Path MT5
MT5_FALLBACK = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
ACTIVE_MT5_PATH = MT5_FALLBACK

SYMBOL = "XAUUSD"
MAGIC_M15_PRO = 155701
LOT_SIZE = 0.01

# PARAMETER PRO V6 DUAL-ENGINE:
CONF_ENTRY_MIN  = 60.0    # Ambang batas entri selektif
CONF_SNIPER_MIN = 65.0    # Ambang batas sniper high conviction

# 65 FITUR RESMI MODEL SKRIPSI (HEAD 1 - TREND)
FEATURES_65 = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio',
    'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low',
    'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth', 'BB_Pos',
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20',
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear',
    'EMA_9_Cross_26_Bull', 'Dist_EMA9_M15', 'Dist_EMA26_M15', 'Spread_EMA_9_26',
    'Pullback_EMA_Bull', 'Pullback_EMA_Bear',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'DXY_Dist_Resistance', 'DXY_Dist_Support',
    'DXY_At_Supply_POI', 'DXY_At_Demand_POI',
    'DXY_RSI_14', 'DXY_BOS_Bull', 'DXY_BOS_Bear',
    'SMT_Divergence_Bull', 'SMT_Divergence_Bear',
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week'
]

# 77 FITUR RESMI MODEL PROPRIETARY (HEAD 2 - REVERSAL)
FEATURES_77 = FEATURES_65 + [
    'Rejection_Resist_Index', 'Rejection_Support_Index',
    'Stoch_RSI_K', 'Stoch_RSI_D',
    'Stoch_RSI_Overbought', 'Stoch_RSI_Oversold',
    'Stoch_RSI_Cross_Bear', 'Stoch_RSI_Cross_Bull',
    'Shockwave_Crash_12', 'Shockwave_Pump_12',
    'Absorption_Supply_Bear', 'Absorption_Demand_Bull'
]

def log_pro(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts} WIB] [PRO V6 DUAL-ENGINE] {msg}"
    print(formatted, flush=True)

def write_telemetry_pro(data):
    try:
        temp_path = TELEMETRY_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(temp_path, TELEMETRY_PATH)
    except Exception:
        pass

def get_best_filling_mode():
    try:
        s_info = mt5.symbol_info(SYMBOL)
        if s_info:
            if s_info.filling_mode == 1:
                return mt5.ORDER_FILLING_FOK
            elif s_info.filling_mode == 2:
                return mt5.ORDER_FILLING_IOC
            elif s_info.filling_mode == 4:
                return mt5.ORDER_FILLING_RETURN
    except Exception:
        pass
    return mt5.ORDER_FILLING_IOC

def connect_mt5_pro():
    global SYMBOL
    log_pro("Menghubungkan ke Terminal MetaTrader 5...")
    if not mt5.initialize():
        if not mt5.initialize(path=ACTIVE_MT5_PATH):
            log_pro(f"GAGAL Inisialisasi MT5: {mt5.last_error()}")
            return False

    acc = mt5.account_info()
    if acc:
        log_pro(f"🟢 TERHUBUNG MT5 PRO! Akun: {acc.login} | Server: {acc.server} | Saldo: ${acc.balance:.2f} {acc.currency}")
    
    if not mt5.symbol_info(SYMBOL):
        if mt5.symbol_info("XAUUSDm"):
            SYMBOL = "XAUUSDm"
        elif mt5.symbol_info("GOLD"):
            SYMBOL = "GOLD"
    mt5.symbol_select(SYMBOL, True)
    return True

def extract_all_dual_features(df_m15, df_h1, df_h4, df_dxy):
    """Menghitung 77 Fitur Kausal dan Institusional secara simultan untuk kedua Head"""
    df = df_m15.copy()
    range_m15 = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_m15
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_m15
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_m15

    df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
    df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)

    df['Swing_High_20'] = df['high'].shift(1).rolling(20, min_periods=1).max()
    df['Swing_Low_20']  = df['low'].shift(1).rolling(20, min_periods=1).min()
    df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
    df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']

    df['BOS_Bull']  = (df['close'] > df['Swing_High_20']).astype(int)
    df['BOS_Bear']  = (df['close'] < df['Swing_Low_20']).astype(int)

    trend_slow = df['close'].pct_change(20).fillna(0)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
    df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

    is_bear_c = df['close'] < df['open']
    is_bull_c = df['close'] > df['open']
    body_sz = (df['close'] - df['open']).abs()
    avg_body = body_sz.rolling(20, min_periods=1).mean()
    imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
    imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
    df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
    df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

    lookback_fibo = 100
    roll_high = df['high'].rolling(lookback_fibo, min_periods=1).max()
    roll_low  = df['low'].rolling(lookback_fibo, min_periods=1).min()
    roll_range = (roll_high - roll_low) + 1e-6
    df['Fibo_Pos_100'] = (df['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)
    df['Fibo_Dist_382'] = (df['close'] - fibo_382) / df['close']
    df['Fibo_Dist_500'] = (df['close'] - fibo_500) / df['close']
    df['Fibo_Dist_618'] = (df['close'] - fibo_618) / df['close']

    delta15 = df['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(14, min_periods=1).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14, min_periods=1).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

    sma20 = df['close'].rolling(20, min_periods=1).mean()
    std20 = df['close'].rolling(20, min_periods=1).std().fillna(0)
    df['BB_Bandwidth'] = (4 * std20) / (sma20 + 1e-9)
    df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

    df['XAU_Return_1']  = df['close'].pct_change(1).fillna(0)
    df['XAU_Return_3']  = df['close'].pct_change(3).fillna(0)
    df['XAU_Return_5']  = df['close'].pct_change(5).fillna(0)

    is_bull = (df['close'] > df['open']).astype(int)
    is_bear = (df['close'] < df['open']).astype(int)
    df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
    df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

    high_diff = df['high'].diff(); low_diff = -df['low'].diff()
    plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    tr1 = df['high'] - df['low']; tr2 = (df['high'] - df['close'].shift(1)).abs(); tr3 = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr14 = tr.rolling(14, min_periods=1).mean().fillna(1.0)
    df['ATR_14'] = atr14
    plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14, min_periods=1).mean() / (atr14 + 1e-6))
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14, min_periods=1).mean() / (atr14 + 1e-6))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
    df['ADX_14'] = dx.rolling(14, min_periods=1).mean().fillna(20.0)

    vol = df['tick_volume'] if 'tick_volume' in df.columns else df['volume']
    vol_ma20 = vol.rolling(20, min_periods=1).mean()
    df['Volume_Ratio'] = vol / (vol_ma20 + 1e-6)

    # 6 Fitur Spasial
    df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.40)).astype(int)
    df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.40)).astype(int)
    df['Zone_B_Prox_Bull']   = (df['Dist_Support'] <= 0.0010).astype(int)
    df['Zone_B_Prox_Bear']   = (df['Dist_Resistance'] <= 0.0010).astype(int)
    df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0035).astype(int)
    df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0035).astype(int)

    # EMA 9/26
    ema_9_m15  = df['close'].ewm(span=9, adjust=False).mean()
    ema_26_m15 = df['close'].ewm(span=26, adjust=False).mean()
    df['EMA_9_Cross_26_Bull'] = ((ema_9_m15 > ema_26_m15) & (ema_9_m15.shift(1) <= ema_26_m15.shift(1))).astype(int)
    df['Dist_EMA9_M15']   = (df['close'] - ema_9_m15) / df['close']
    df['Dist_EMA26_M15']  = (df['close'] - ema_26_m15) / df['close']
    df['Spread_EMA_9_26'] = (ema_9_m15 - ema_26_m15) / df['close']
    df['Pullback_EMA_Bull'] = ((df['low'] <= ema_9_m15) & (df['close'] > ema_9_m15)).astype(int)
    df['Pullback_EMA_Bear'] = ((df['high'] >= ema_9_m15) & (df['close'] < ema_9_m15)).astype(int)

    # DXY Intermarket
    if df_dxy is not None and len(df_dxy) > 0:
        dxy_aligned = df_dxy.reindex(df.index, method='ffill').fillna(method='bfill')
        dxy_c = dxy_aligned['close']; dxy_h = dxy_aligned['high']; dxy_l = dxy_aligned['low']
    else:
        dxy_c = df['close'] * 0 + 104.0; dxy_h = dxy_c; dxy_l = dxy_c

    df['DXY_Return_1'] = dxy_c.pct_change(1).fillna(0)
    df['DXY_Return_3'] = dxy_c.pct_change(3).fillna(0)
    df['DXY_Trend'] = np.where(dxy_c > dxy_c.rolling(20, min_periods=1).mean(), 1, -1)
    df['XAU_DXY_Ratio_Return'] = (df['close'] / (dxy_c + 1e-6)).pct_change(1).fillna(0)
    dxy_swing_high = dxy_h.shift(1).rolling(20, min_periods=1).max()
    dxy_swing_low  = dxy_l.shift(1).rolling(20, min_periods=1).min()
    df['DXY_Dist_Resistance'] = (dxy_swing_high - dxy_c) / (dxy_c + 1e-6)
    df['DXY_Dist_Support']    = (dxy_c - dxy_swing_low) / (dxy_c + 1e-6)
    df['DXY_At_Supply_POI'] = (df['DXY_Dist_Resistance'] <= 0.0008).astype(int)
    df['DXY_At_Demand_POI'] = (df['DXY_Dist_Support'] <= 0.0008).astype(int)
    dxy_delta = dxy_c.diff()
    dxy_gain = (dxy_delta.where(dxy_delta > 0, 0)).rolling(14, min_periods=1).mean()
    dxy_loss = (-dxy_delta.where(dxy_delta < 0, 0)).rolling(14, min_periods=1).mean()
    df['DXY_RSI_14'] = 100 - (100 / (1 + (dxy_gain / (dxy_loss + 1e-6))))
    df['DXY_BOS_Bull'] = (dxy_c > dxy_swing_high).astype(int)
    df['DXY_BOS_Bear'] = (dxy_c < dxy_swing_low).astype(int)

    xau_ll = df['low'] < df['low'].shift(1).rolling(10, min_periods=1).min()
    dxy_fail_hh = dxy_h <= dxy_h.shift(1).rolling(10, min_periods=1).max()
    df['SMT_Divergence_Bull'] = (xau_ll & dxy_fail_hh).astype(int)
    xau_hh = df['high'] > df['high'].shift(1).rolling(10, min_periods=1).max()
    dxy_fail_ll = dxy_l >= dxy_l.shift(1).rolling(10, min_periods=1).min()
    df['SMT_Divergence_Bear'] = (xau_hh & dxy_fail_ll).astype(int)

    # MTF H1 & H4
    if df_h1 is not None and len(df_h1) > 0:
        h1_close = df_h1['close'].shift(1)
        ema50_h1  = h1_close.ewm(span=50, adjust=False).mean()
        ema200_h1 = h1_close.ewm(span=200, adjust=False).mean()
        df['Trend_H1_Bull']   = (h1_close > ema50_h1).astype(int).reindex(df.index, method='ffill').fillna(0)
        df['Trend_H1_Strong'] = (ema50_h1 > ema200_h1).astype(int).reindex(df.index, method='ffill').fillna(0)
        df['H1_Dist_EMA50']   = ((h1_close - ema50_h1) / (h1_close + 1e-9)).reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H1_Bull'] = 1; df['Trend_H1_Strong'] = 1; df['H1_Dist_EMA50'] = 0.0

    if df_h4 is not None and len(df_h4) > 0:
        h4_close = df_h4['close'].shift(1)
        ema50_h4  = h4_close.ewm(span=50, adjust=False).mean()
        ema200_h4 = h4_close.ewm(span=200, adjust=False).mean()
        df['Trend_H4_Bull']   = (h4_close > ema50_h4).astype(int).reindex(df.index, method='ffill').fillna(0)
        df['Trend_H4_Strong'] = (ema50_h4 > ema200_h4).astype(int).reindex(df.index, method='ffill').fillna(0)
        df['H4_Dist_EMA50']   = ((h4_close - ema50_h4) / (h4_close + 1e-9)).reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H4_Bull'] = 1; df['Trend_H4_Strong'] = 1; df['H4_Dist_EMA50'] = 0.0

    day_of_month = df.index.day; weekday = df.index.weekday
    df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
    df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
    df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

    # 12 FITUR INSTITUSIONAL KHUSUS HEAD 2 (PRO)
    df['Rejection_Resist_Index']  = (df['Upper_Wick_Ratio'] ** 2) / (df['Dist_Resistance'] + 0.0005)
    df['Rejection_Support_Index'] = (df['Lower_Wick_Ratio'] ** 2) / (df['Dist_Support'] + 0.0005)

    rsi_s = df['RSI_14']
    min_r = rsi_s.rolling(14, min_periods=1).min(); max_r = rsi_s.rolling(14, min_periods=1).max()
    stoch_raw = (rsi_s - min_r) / (max_r - min_r + 1e-6) * 100.0
    st_k = stoch_raw.rolling(3, min_periods=1).mean(); st_d = st_k.rolling(3, min_periods=1).mean()
    df['Stoch_RSI_K'] = st_k
    df['Stoch_RSI_D'] = st_d
    df['Stoch_RSI_Overbought'] = (st_k >= 85.0).astype(int)
    df['Stoch_RSI_Oversold']   = (st_k <= 15.0).astype(int)
    df['Stoch_RSI_Cross_Bear'] = ((st_k < st_d) & (st_k.shift(1) >= st_d.shift(1)) & (st_k >= 70.0)).astype(int)
    df['Stoch_RSI_Cross_Bull'] = ((st_k > st_d) & (st_k.shift(1) <= st_d.shift(1)) & (st_k <= 30.0)).astype(int)

    c_range = df['high'] - df['low']
    is_crash = (c_range >= 3.0 * df['ATR_14']) & (df['close'] < df['open'])
    is_pump  = (c_range >= 3.0 * df['ATR_14']) & (df['close'] > df['open'])
    df['Shockwave_Crash_12'] = is_crash.rolling(12, min_periods=1).max().fillna(0).astype(int)
    df['Shockwave_Pump_12']  = is_pump.rolling(12, min_periods=1).max().fillna(0).astype(int)

    vol_h = df['Volume_Ratio'] >= 1.6
    df['Absorption_Supply_Bear'] = (vol_h & (df['Upper_Wick_Ratio'] >= 0.25) & (df['Dist_Resistance'] <= 0.0020)).astype(int)
    df['Absorption_Demand_Bull'] = (vol_h & (df['Lower_Wick_Ratio'] >= 0.25) & (df['Dist_Support'] <= 0.0020)).astype(int)

    return df

def load_dual_models():
    """Memuat kedua model resmi: Head 1 (Trend 65F) & Head 2 (Reversal 77F)"""
    model_trend = None
    model_rev = None

    # 1. Load Head 1 (Trend 65 Fitur)
    if os.path.exists(MODEL_TREND_PATH):
        try:
            model_trend = joblib.load(MODEL_TREND_PATH)
            log_pro(f"✅ Head 1 [Trend Specialist 65 Fitur] berhasil dimuat dari {MODEL_TREND_PATH}")
        except Exception as e:
            log_pro(f"Gagal memuat Model Trend: {e}")

    # 2. Load Head 2 (Reversal 77 Fitur)
    if os.path.exists(MODEL_REV_PATH):
        try:
            model_rev = joblib.load(MODEL_REV_PATH)
            log_pro(f"✅ Head 2 [Reversal Specialist 77 Fitur] berhasil dimuat dari {MODEL_REV_PATH}")
        except Exception as e:
            log_pro(f"Gagal memuat Model Reversal: {e}")

    if model_trend is None or model_rev is None:
        log_pro("❌ FATAL: Salah satu model dual-engine tidak ditemukan!")
        sys.exit(1)

    return model_trend, model_rev

def manage_active_positions_pro():
    """Mengelola Trailing Stop 2-Tier & Auto BEP Lock untuk Posisi M15 PRO V6"""
    try:
        positions = mt5.positions_get(symbol=SYMBOL)
        if not positions:
            return
        for pos in positions:
            if pos.magic != MAGIC_M15_PRO:
                continue
            is_buy = (pos.type == mt5.ORDER_TYPE_BUY)
            tick = mt5.symbol_info_tick(SYMBOL)
            if not tick: continue
            cur_p = tick.bid if is_buy else tick.ask
            floating_usd = (cur_p - pos.price_open) * 1.0 if is_buy else (pos.price_open - cur_p) * 1.0
            
            target_sl = None
            tier_label = ""
            # Tier 2 Profit Lock: floating >= +$5.50 -> Kunci SL ke entry + $3.00
            if floating_usd >= 5.50:
                target_sl = (pos.price_open + 3.00) if is_buy else (pos.price_open - 3.00)
                tier_label = "Tier 2 Profit Lock (+$3.00)"
            # Tier 1 BEP Lock: floating >= +$2.20 -> Kunci SL ke entry + $0.30
            elif floating_usd >= 2.20:
                target_sl = (pos.price_open + 0.30) if is_buy else (pos.price_open - 0.30)
                tier_label = "Tier 1 BEP Lock (+$0.30)"
                
            if target_sl is not None:
                should_update = False
                if is_buy and (pos.sl < target_sl):
                    should_update = True
                elif not is_buy and (pos.sl == 0 or pos.sl > target_sl):
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
                        log_pro(f"🛡️ [SL-LOCK] Tiket PRO #{pos.ticket} diperbarui ke SL ${target_sl:.2f} ({tier_label}) | Floating: +${floating_usd:.2f}")
    except Exception as e:
        log_pro(f"Error manage active positions: {e}")

def execute_market_order_pro_v6(signal_type, tp_points, sl_points, head_name, reason_desc):
    """Eksekusi Order Pasar Riil PRO V6 Dual-Engine pada MT5"""
    tick = mt5.symbol_info_tick(SYMBOL)
    if not tick:
        log_pro("Gagal mengambil harga pasar terkini!")
        return False

    is_buy = (signal_type == "BUY")
    price = tick.ask if is_buy else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL

    point = 0.1  # XAUUSD 1 pt = $0.10 (10 pts = $1.00)
    sl_price = round(price - (sl_points * point) if is_buy else price + (sl_points * point), 2)
    tp_price = round(price + (tp_points * point) if is_buy else price - (tp_points * point), 2)

    comment_str = f"V6_{'TRD' if 'HEAD 1' in head_name else 'REV'}_{signal_type}"

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": 20,
        "magic": MAGIC_M15_PRO,
        "comment": comment_str[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_best_filling_mode(),
    }

    log_pro(f"🚀 [{head_name}] EKSEKUSI {signal_type} @ ${price:.2f} | SL: ${sl_price:.2f} (-${sl_points/10:.2f}) | TP: ${tp_price:.2f} (+${tp_points/10:.2f})")
    log_pro(f"   ↳ Alasan: {reason_desc}")
    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        log_pro(f"✅ ORDER {signal_type} PRO V6 BERHASIL! Ticket: #{result.order}")
        try:
            sync_mt5_trades_to_excel(
                excel_path=EXCEL_PRO_PATH,
                magic_number=MAGIC_M15_PRO,
                model_label=f"PRO V6 Dual-Engine ({head_name})",
                sheet_title="Trade_History_PRO",
                summary_sheet_title="Ringkasan_Statistik_PRO"
            )
        except Exception as e:
            log_pro(f"Error sync Excel PRO: {e}")
        return True
    else:
        err = result.comment if result else mt5.last_error()
        log_pro(f"❌ ORDER PRO V6 GAGAL: {err}")
        return False

def run_m15_pro_v6_loop():
    if not acquire_single_instance_lock():
        log_pro("⚠️ Bot M15 PRO sudah aktif berjalan di latar belakang (port 48903 terkunci). Proses ini keluar otomatis.")
        sys.exit(0)

    log_pro("="*80)
    log_pro("🏆 BOT M15 PRO V6.0 DUAL-ENGINE AKTIF — ARSITEKTUR HYBRID MULTI-REGIME")
    log_pro("="*80)

    if not connect_mt5_pro():
        log_pro("Menunggu 5 detik sebelum coba koneksi ulang...")
        time.sleep(5)
        return

    model_trend, model_rev = load_dual_models()
    last_eval_time = None
    _last_holding_trades = 0

    while True:
        try:
            if mt5.terminal_info() is None:
                log_pro("Koneksi MT5 terputus, mencoba menyambungkan kembali...")
                connect_mt5_pro()
                time.sleep(2)
                continue

            # Kelola trailing stop 2-tier untuk posisi aktif PRO V6
            manage_active_positions_pro()

            # Ambil data candle M15
            rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 350)
            if rates_m15 is None or len(rates_m15) < 310:
                time.sleep(1)
                continue

            last_bar = rates_m15[-1]
            current_bar_time = last_bar['time']
            cur_price = last_bar['close']

            now_ts = int(time.time())
            seconds_in_bar = now_ts % 900
            seconds_left = 900 - seconds_in_bar
            mins_left = seconds_left // 60
            secs_left = seconds_left % 60

            # Cek floating profit & posisi aktif dengan Magic M15 PRO
            positions = mt5.positions_get(symbol=SYMBOL)
            holding_trades = 0
            floating_pnl = 0.0
            if positions:
                for p in positions:
                    if p.magic == MAGIC_M15_PRO:
                        holding_trades += 1
                        floating_pnl += p.profit

            if holding_trades < _last_holding_trades:
                log_pro("Posisi PRO V6 telah tertutup (TP/SL/BEP). Menyinkronkan riwayat transaksi ke Excel PRO...")
                try:
                    sync_mt5_trades_to_excel(
                        excel_path=EXCEL_PRO_PATH,
                        magic_number=MAGIC_M15_PRO,
                        model_label="PRO V6 Dual-Engine (Hybrid Trend & Reversal)",
                        sheet_title="Trade_History_PRO",
                        summary_sheet_title="Ringkasan_Statistik_PRO"
                    )
                except Exception as e:
                    log_pro(f"Error sync Excel PRO: {e}")
            _last_holding_trades = holding_trades

            # Ekstrak seluruh fitur untuk kedua head
            rates_h1 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 100)
            rates_h4 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 50)
            try: rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 100)
            except Exception: rates_dxy = None

            df_m = pd.DataFrame(rates_m15); df_m['time'] = pd.to_datetime(df_m['time'], unit='s'); df_m.set_index('time', inplace=True)
            df_1 = pd.DataFrame(rates_h1) if rates_h1 is not None else None
            if df_1 is not None: df_1['time'] = pd.to_datetime(df_1['time'], unit='s'); df_1.set_index('time', inplace=True)
            df_4 = pd.DataFrame(rates_h4) if rates_h4 is not None else None
            if df_4 is not None: df_4['time'] = pd.to_datetime(df_4['time'], unit='s'); df_4.set_index('time', inplace=True)
            df_x = pd.DataFrame(rates_dxy) if rates_dxy is not None else None
            if df_x is not None: df_x['time'] = pd.to_datetime(df_x['time'], unit='s'); df_x.set_index('time', inplace=True)

            df_feats = extract_all_dual_features(df_m, df_1, df_4, df_x)

            # -------------------------------------------------------------
            # PREDIKSI SIMULTAN KEDUA ENGINE
            # -------------------------------------------------------------
            # 1. Head 1: Trend Expansion Specialist (65 Fitur Skripsi)
            vec_65 = df_feats[FEATURES_65].iloc[-1:]
            probs_h1 = model_trend.predict_proba(vec_65)[0]
            p1_up = round(float(probs_h1[1]) * 100, 1)
            p1_dn = round(float(probs_h1[0]) * 100, 1)

            # 2. Head 2: Mean Reversion / Micro-Sniper (77 Fitur PRO)
            vec_77 = df_feats[FEATURES_77].iloc[-1:]
            probs_h2 = model_rev.predict_proba(vec_77)[0]
            p2_up = round(float(probs_h2[1]) * 100, 1)
            p2_dn = round(float(probs_h2[0]) * 100, 1)

            # -------------------------------------------------------------
            # REGIME DETECTOR & ARBITER PRO V6
            # -------------------------------------------------------------
            adx = round(float(df_feats['ADX_14'].iloc[-1]), 1)
            bb_w = float(df_feats['BB_Bandwidth'].iloc[-1])
            stoch_k = round(float(df_feats['Stoch_RSI_K'].iloc[-1]), 1)
            bb_median = float(df_feats['BB_Bandwidth'].tail(100).median()) if len(df_feats) >= 100 else 0.005

            is_trending = (adx >= 24.0) and (bb_w >= bb_median) and not (stoch_k >= 85.0 or stoch_k <= 15.0)
            is_reversal = (adx < 20.0) or (stoch_k >= 80.0) or (stoch_k <= 20.0)

            signal_candidate = "STANDBY"
            active_engine_name = "STANDBY"
            regime_desc = "NORMAL BUFFER"
            tp_pts = 95.0
            sl_pts = 50.0

            if is_trending:
                regime_desc = f"TRENDING EXPANSION (ADX {adx:.1f} >= 24)"
                active_engine_name = "HEAD 1 (TREND 65F)"
                if p1_up >= CONF_ENTRY_MIN and p1_up > p1_dn:
                    signal_candidate = "BUY"
                    tp_pts = 110.0 if p1_up >= CONF_SNIPER_MIN else 85.0
                    sl_pts = 65.0
                    status_str = f"🟢 AI BUY [{active_engine_name}]: Prob {p1_up:.1f}% >= 60% | TP +${tp_pts/10:.2f} | SL -${sl_pts/10:.2f} | {regime_desc}"
                elif p1_dn >= CONF_ENTRY_MIN and p1_dn > p1_up:
                    signal_candidate = "SELL"
                    tp_pts = 110.0 if p1_dn >= CONF_SNIPER_MIN else 85.0
                    sl_pts = 65.0
                    status_str = f"🔴 AI SELL [{active_engine_name}]: Prob {p1_dn:.1f}% >= 60% | TP +${tp_pts/10:.2f} | SL -${sl_pts/10:.2f} | {regime_desc}"
                else:
                    status_str = f"⚪ STANDBY [{active_engine_name}]: Sinyal {max(p1_up, p1_dn):.1f}% < 60% | {regime_desc}"

            elif is_reversal:
                regime_desc = f"MEAN REVERSION (Stoch {stoch_k:.1f} / ADX {adx:.1f})"
                active_engine_name = "HEAD 2 (REVERSAL 77F)"
                if p2_up >= CONF_ENTRY_MIN and p2_up > p2_dn:
                    signal_candidate = "BUY"
                    tp_pts = 125.0 if p2_up >= CONF_SNIPER_MIN else 95.0
                    sl_pts = 50.0
                    status_str = f"🟢 AI BUY [{active_engine_name}]: Prob {p2_up:.1f}% >= 60% | TP +${tp_pts/10:.2f} | SL -${sl_pts/10:.2f} | {regime_desc}"
                elif p2_dn >= CONF_ENTRY_MIN and p2_dn > p2_up:
                    signal_candidate = "SELL"
                    tp_pts = 125.0 if p2_dn >= CONF_SNIPER_MIN else 95.0
                    sl_pts = 50.0
                    status_str = f"🔴 AI SELL [{active_engine_name}]: Prob {p2_dn:.1f}% >= 60% | TP +${tp_pts/10:.2f} | SL -${sl_pts/10:.2f} | {regime_desc}"
                else:
                    status_str = f"⚪ STANDBY [{active_engine_name}]: Sinyal {max(p2_up, p2_dn):.1f}% < 60% | {regime_desc}"

            else:
                # Zona Transisi (20 <= ADX < 24): Meta-Arbiter (Hanya high conviction >= 65%)
                regime_desc = f"TRANSITION ZONE (ADX {adx:.1f}, Stoch {stoch_k:.1f})"
                active_engine_name = "META-ARBITER"
                max_h1 = max(p1_up, p1_dn)
                max_h2 = max(p2_up, p2_dn)
                if max_h2 >= CONF_SNIPER_MIN and max_h2 >= max_h1:
                    signal_candidate = "BUY" if p2_up > p2_dn else "SELL"
                    tp_pts = 125.0 if max_h2 >= 68.0 else 95.0
                    sl_pts = 50.0
                    status_str = f"{'🟢' if signal_candidate=='BUY' else '🔴'} AI {signal_candidate} [{active_engine_name} - REVERSAL]: High Conviction {max_h2:.1f}% >= 65% | {regime_desc}"
                elif max_h1 >= CONF_SNIPER_MIN:
                    signal_candidate = "BUY" if p1_up > p1_dn else "SELL"
                    tp_pts = 110.0 if max_h1 >= 68.0 else 85.0
                    sl_pts = 65.0
                    status_str = f"{'🟢' if signal_candidate=='BUY' else '🔴'} AI {signal_candidate} [{active_engine_name} - TREND]: High Conviction {max_h1:.1f}% >= 65% | {regime_desc}"
                else:
                    status_str = f"⚪ STANDBY [{active_engine_name}]: Menunggu sinyal konfiden >= 65% (Head1: {max_h1:.1f}%, Head2: {max_h2:.1f}%) | {regime_desc}"

            m15_sup = round(float(df_feats['Swing_Low_20'].iloc[-1]), 2)
            m15_res = round(float(df_feats['Swing_High_20'].iloc[-1]), 2)
            h1_trend_str = "BULLISH" if df_feats['Trend_H1_Bull'].iloc[-1] == 1 else "BEARISH"

            # Eksekusi jika lilin baru M15 terkonfirmasi dan tidak ada posisi aktif PRO
            if last_eval_time != current_bar_time:
                last_eval_time = current_bar_time
                log_pro(f"Lilin M15 Baru: Close ${cur_price:.2f} | H1 (Trend): B {p1_up}%/S {p1_dn}% | H2 (Rev): B {p2_up}%/S {p2_dn}% | {status_str}")
                
                if signal_candidate in ["BUY", "SELL"]:
                    if holding_trades == 0:
                        execute_market_order_pro_v6(signal_candidate, tp_pts, sl_pts, active_engine_name, status_str)
                    else:
                        log_pro(f"Posisi {signal_candidate} ditahan karena ada {holding_trades} trade PRO V6 yang sedang berjalan.")

            # Tulis Telemetri M15 PRO V6 Dual-Engine Real-Time setiap detik
            telemetry_data = {
                "timeframe": "M15 PRO (V6.0 Dual-Engine)",
                "engine_version": "PRO V6.0 DUAL-ENGINE",
                "active_head": active_engine_name,
                "regime_name": regime_desc,
                "prob_buy": p1_up if is_trending else (p2_up if is_reversal else round((p1_up + p2_up)/2, 1)),
                "prob_sell": p1_dn if is_trending else (p2_dn if is_reversal else round((p1_dn + p2_dn)/2, 1)),
                "head1_buy": p1_up,
                "head1_sell": p1_dn,
                "head2_buy": p2_up,
                "head2_sell": p2_dn,
                "adx": adx,
                "stoch_k": stoch_k,
                "h1_trend": h1_trend_str,
                "mins_left": mins_left,
                "secs_left": secs_left,
                "seconds_left": seconds_left,
                "status_str": status_str,
                "ask_p": round(cur_price + 0.15, 2),
                "bid_p": round(cur_price, 2),
                "m15_sup": m15_sup,
                "m15_res": m15_res,
                "holding_trades": holding_trades,
                "floating_pnl": round(floating_pnl, 2),
                "is_pro": True,
                "timestamp": time.time()
            }
            write_telemetry_pro(telemetry_data)

            time.sleep(1)

        except Exception as e:
            log_pro(f"Error loop PRO V6: {e}")
            time.sleep(2)

if __name__ == "__main__":
    run_m15_pro_v6_loop()
