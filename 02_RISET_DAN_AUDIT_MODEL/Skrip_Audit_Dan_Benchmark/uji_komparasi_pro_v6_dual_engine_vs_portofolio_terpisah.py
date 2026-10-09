"""
====================================================================================================
EKSPERIMEN RISET RESMI: BOT PRO V6.0 DUAL-ENGINE VS DUA BOT TERPISAH (STATUS QUO)
====================================================================================================
Tujuan: Menguji secara empiris apakah penggabungan Trend-Following & Mean-Reversion ke dalam
satu bot tunggal (Roadmap PRO V6.0 Dual-Engine dengan Regime Switching) lebih unggul dibandingkan:
1. Bot Skripsi Standalone (65 Fitur Trend-Following)
2. Bot PRO Standalone V5.4 (77 Fitur Mean-Reversion Sniper)
3. Portofolio Dua Bot Terpisah Berjalan Paralel (Status Quo saat ini)

Pengujian dilakukan pada data Out-of-Sample 5.000 Candle M15 (~2.5 - 3 Bulan) dengan biaya transaksi riil:
Spread $0.20 USD (2.0 pips) + Slippage $0.10 USD (1.0 pips) = Biaya Riil $0.30 per trade.
Lot Size: 0.01 micro lot.
Modal Awal: $500.00 USD per engine.
====================================================================================================
"""

import os, sys, time, joblib
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
BASE_DIR = r"d:\SKRIPSI INFORMATIKA"

print("="*90)
print("🔬 MEMULAI SIMULASI BENCHMARK KOMPARASI PRO V6.0 DUAL-ENGINE")
print("="*90)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"📥 Mengambil data MT5 terkini: 15.000 candle M15 {symbol}, 5.000 H1, 2.000 H4, DXY M15...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 5000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2000)

mt5.symbol_select("DXY", True)
rates_dxy = mt5.copy_rates_from_pos("DXY", mt5.TIMEFRAME_M15, 0, 15000)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)
df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)

print(f"Data M15: {len(df)} candle ({df.index[0]} s/d {df.index[-1]})")

# -----------------------------------------------------------------------------
# 1. REKAYASA FITUR (77 FITUR LENGKAP)
# -----------------------------------------------------------------------------
print("⚙️ Mengekstrak seluruh 77 fitur (65 Skripsi + 12 PRO)...")

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

trend_slow = df['close'].pct_change(20)
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
std20 = df['close'].rolling(20, min_periods=1).std()
df['BB_Bandwidth'] = (4 * std20) / (sma20 + 1e-9)
df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1).fillna(0)
df['XAU_Return_3'] = df['close'].pct_change(3).fillna(0)
df['XAU_Return_5'] = df['close'].pct_change(5).fillna(0)

# DXY Sync
dxy_sync = df_dxy.reindex(df.index, method='ffill').bfill()
dxy_c = dxy_sync['close']
dxy_h = dxy_sync['high']
dxy_l = dxy_sync['low']

df['DXY_Return_1'] = dxy_c.pct_change(1).fillna(0)
df['DXY_Return_3'] = dxy_c.pct_change(3).fillna(0)
df['DXY_Trend'] = (dxy_c > dxy_c.rolling(20, min_periods=1).mean()).astype(int)
df['XAU_DXY_Ratio'] = df['close'] / (dxy_c + 1e-6)
df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

dxy_swing_high = dxy_h.shift(1).rolling(20, min_periods=1).max()
dxy_swing_low  = dxy_l.shift(1).rolling(20, min_periods=1).min()
df['DXY_Dist_Resistance'] = (dxy_swing_high - dxy_c) / dxy_c
df['DXY_Dist_Support']    = (dxy_c - dxy_swing_low) / dxy_c
df['DXY_At_Supply_POI']   = (df['DXY_Dist_Resistance'] <= 0.0010).astype(int)
df['DXY_At_Demand_POI']   = (df['DXY_Dist_Support'] <= 0.0010).astype(int)

dxy_delta = dxy_c.diff()
dxy_gain  = (dxy_delta.where(dxy_delta > 0, 0)).rolling(14, min_periods=1).mean()
dxy_loss  = (-dxy_delta.where(dxy_delta < 0, 0)).rolling(14, min_periods=1).mean()
df['DXY_RSI_14'] = 100 - (100 / (1 + (dxy_gain / (dxy_loss + 1e-6))))

df['DXY_BOS_Bull'] = (dxy_c > dxy_swing_high).astype(int)
df['DXY_BOS_Bear'] = (dxy_c < dxy_swing_low).astype(int)

xau_ll = df['low'] < df['low'].shift(1).rolling(10, min_periods=1).min()
dxy_fail_hh = dxy_h <= dxy_h.shift(1).rolling(10, min_periods=1).max()
df['SMT_Divergence_Bull'] = (xau_ll & dxy_fail_hh).astype(int)

xau_hh = df['high'] > df['high'].shift(1).rolling(10, min_periods=1).max()
dxy_fail_ll = dxy_l >= dxy_l.shift(1).rolling(10, min_periods=1).min()
df['SMT_Divergence_Bear'] = (xau_hh & dxy_fail_ll).astype(int)

# Calendar Proksi
day_of_month = df.index.day
weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

# MTF H1 & H4
h1_close = df_h1['close'].shift(1)
df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull']   = (h1_close > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close - df_h1_loc['EMA_50_H1']) / (h1_close + 1e-9)

h4_close = df_h4['close'].shift(1)
df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull']   = (h4_close > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50']   = (h4_close - df_h4_loc['EMA_50_H4']) / (h4_close + 1e-9)

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)
for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

# Candlestick Dynamics
is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
atr14 = tr.rolling(14, min_periods=1).mean() + 1e-6
df['ATR_14'] = atr14
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14, min_periods=1).mean() / atr14)
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14, min_periods=1).mean() / atr14)
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14, min_periods=1).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20, min_periods=1).mean() + 1e-6)

# Spasial Zona
df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

# EMA 9/26 Ribbon
ema9_m15  = df['close'].ewm(span=9, adjust=False).mean()
ema26_m15 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = (ema9_m15 > ema26_m15).astype(int)
df['Dist_EMA9_M15']  = (df['close'] - ema9_m15) / df['close']
df['Dist_EMA26_M15'] = (df['close'] - ema26_m15) / df['close']
df['Spread_EMA_9_26'] = (ema9_m15 - ema26_m15) / df['close']
df['Pullback_EMA_Bull'] = ((df['EMA_9_Cross_26_Bull'] == 1) & (df['low'] <= ema9_m15) & (df['close'] > ema9_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Pullback_EMA_Bear'] = ((df['EMA_9_Cross_26_Bull'] == 0) & (df['high'] >= ema9_m15) & (df['close'] < ema9_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)

# 12 Fitur PRO Tambahan
rsi_low  = df['RSI_14'].rolling(14, min_periods=1).min()
rsi_high = df['RSI_14'].rolling(14, min_periods=1).max()
stoch_rsi = (df['RSI_14'] - rsi_low) / (rsi_high - rsi_low + 1e-6)
df['Stoch_RSI_K'] = stoch_rsi.rolling(3, min_periods=1).mean() * 100.0
df['Stoch_RSI_D'] = df['Stoch_RSI_K'].rolling(3, min_periods=1).mean()
df['Stoch_RSI_Overbought'] = (df['Stoch_RSI_K'] >= 80.0).astype(int)
df['Stoch_RSI_Oversold']   = (df['Stoch_RSI_K'] <= 20.0).astype(int)
df['Stoch_RSI_Cross_Bear'] = ((df['Stoch_RSI_K'].shift(1) >= df['Stoch_RSI_D'].shift(1)) & (df['Stoch_RSI_K'] < df['Stoch_RSI_D']) & (df['Stoch_RSI_K'] >= 70.0)).astype(int)
df['Stoch_RSI_Cross_Bull'] = ((df['Stoch_RSI_K'].shift(1) <= df['Stoch_RSI_D'].shift(1)) & (df['Stoch_RSI_K'] > df['Stoch_RSI_D']) & (df['Stoch_RSI_K'] <= 30.0)).astype(int)

ret_12 = df['close'].pct_change(12)
vol_12 = ret_12.rolling(48, min_periods=1).std()
is_crash = ret_12 <= (-2.0 * vol_12)
is_pump  = ret_12 >= (2.0 * vol_12)
df['Shockwave_Crash_12'] = is_crash.rolling(12, min_periods=1).max().fillna(0).astype(int)
df['Shockwave_Pump_12']  = is_pump.rolling(12, min_periods=1).max().fillna(0).astype(int)

vol_h = df['Volume_Ratio'] >= 1.6
df['Absorption_Supply_Bear'] = (vol_h & (df['Upper_Wick_Ratio'] >= 0.25) & (df['Dist_Resistance'] <= 0.0020)).astype(int)
df['Absorption_Demand_Bull'] = (vol_h & (df['Lower_Wick_Ratio'] >= 0.25) & (df['Dist_Support'] <= 0.0020)).astype(int)

df['Rejection_Resist_Index'] = df['Upper_Wick_Ratio'] * (1.0 / (df['Dist_Resistance'] + 1e-4))
df['Rejection_Support_Index'] = df['Lower_Wick_Ratio'] * (1.0 / (df['Dist_Support'] + 1e-4))

# -----------------------------------------------------------------------------
# DAFTAR FITUR LENGKAP
# -----------------------------------------------------------------------------
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

FEATURES_77 = FEATURES_65 + [
    'Rejection_Resist_Index', 'Rejection_Support_Index',
    'Stoch_RSI_K', 'Stoch_RSI_D',
    'Stoch_RSI_Overbought', 'Stoch_RSI_Oversold',
    'Stoch_RSI_Cross_Bear', 'Stoch_RSI_Cross_Bull',
    'Shockwave_Crash_12', 'Shockwave_Pump_12',
    'Absorption_Supply_Bear', 'Absorption_Demand_Bull'
]

# Ambil data out-of-sample 5.000 candle terakhir
df_test = df.tail(5000).copy()
print(f"Data Out-of-Sample: {len(df_test)} candle M15 ({df_test.index[0]} s/d {df_test.index[-1]})")

# Load kedua model
model_skripsi = joblib.load(os.path.join(BASE_DIR, "model_m15_zone_integrated_50.pkl"))
model_pro = joblib.load(os.path.join(BASE_DIR, "model_m15_pro_77_features.pkl"))

# Pre-compute probabilitas kedua model untuk seluruh bar test
X_skripsi = df_test[FEATURES_65].values
X_pro = df_test[FEATURES_77].values

prob_skripsi = model_skripsi.predict_proba(X_skripsi)
prob_pro = model_pro.predict_proba(X_pro)

df_test['p_up_skripsi'] = prob_skripsi[:, 1] * 100.0
df_test['p_dn_skripsi'] = prob_skripsi[:, 0] * 100.0
df_test['p_up_pro']     = prob_pro[:, 1] * 100.0
df_test['p_dn_pro']     = prob_pro[:, 0] * 100.0

# -----------------------------------------------------------------------------
# ENGINE SIMULASI REALISTIS BAR-BY-BAR
# -----------------------------------------------------------------------------
SPREAD_SLIPPAGE = 0.30  # Biaya realita eksekusi per trade ($0.20 spread + $0.10 slippage)

def run_simulation(strategy_name, mode="skripsi"):
    """
    mode:
    - 'skripsi': Trend-following murni (Model 65F, Trailing Multi-Tier, SL -$6.50, TP +$8.50/+$11.00)
    - 'pro': Mean-reversion murni (Model 77F, Trailing 2-Tier, SL -$5.00, TP +$9.50/+$12.50)
    - 'dual_v6': Single Agent Dual-Engine dengan Regime Gating Switching
    """
    balance = 500.00
    equity_curve = [500.00]
    trades = []
    active_pos = None

    # Median BB Bandwidth untuk gating
    bb_median = df_test['BB_Bandwidth'].median()

    for i in range(len(df_test) - 1):
        row = df_test.iloc[i]
        next_row = df_test.iloc[i+1]
        c_price = row['close']
        h_price = next_row['high']
        l_price = next_row['low']

        # 1. KELOLA POSISI AKTIF JIKA ADA
        if active_pos is not None:
            active_pos['bars_held'] += 1
            pos_type = active_pos['type']
            entry_p = active_pos['entry_price']
            sl_p = active_pos['sl']
            tp_p = active_pos['tp']
            cfg = active_pos['cfg']

            # Update Floating & Peak
            cur_float = (h_price - entry_p)*1.0 - SPREAD_SLIPPAGE if pos_type == 'BUY' else (entry_p - l_price)*1.0 - SPREAD_SLIPPAGE
            if cur_float > active_pos['peak_float']:
                active_pos['peak_float'] = cur_float

            # Logic Trailing Lock
            if cfg == 'skripsi':
                # Tier 1: +$2.50 -> Kunci BEP +$0.20
                if active_pos['peak_float'] >= 2.50:
                    bep_sl = entry_p + 0.20 if pos_type == 'BUY' else entry_p - 0.20
                    if pos_type == 'BUY': sl_p = max(sl_p, bep_sl)
                    else: sl_p = min(sl_p, bep_sl)
                # Tier 2: +$4.50 -> Kunci +$2.00
                if active_pos['peak_float'] >= 4.50:
                    t2_sl = entry_p + 2.00 if pos_type == 'BUY' else entry_p - 2.00
                    if pos_type == 'BUY': sl_p = max(sl_p, t2_sl)
                    else: sl_p = min(sl_p, t2_sl)
                # Tier 3: +$7.00 -> Kunci +$4.50
                if active_pos['peak_float'] >= 7.00:
                    t3_sl = entry_p + 4.50 if pos_type == 'BUY' else entry_p - 4.50
                    if pos_type == 'BUY': sl_p = max(sl_p, t3_sl)
                    else: sl_p = min(sl_p, t3_sl)
            elif cfg == 'pro':
                # PRO Tier 1: +$2.20 -> Kunci +$0.30
                if active_pos['peak_float'] >= 2.20:
                    bep_sl = entry_p + 0.30 if pos_type == 'BUY' else entry_p - 0.30
                    if pos_type == 'BUY': sl_p = max(sl_p, bep_sl)
                    else: sl_p = min(sl_p, bep_sl)
                # PRO Tier 2: +$5.50 -> Kunci +$3.00
                if active_pos['peak_float'] >= 5.50:
                    t2_sl = entry_p + 3.00 if pos_type == 'BUY' else entry_p - 3.00
                    if pos_type == 'BUY': sl_p = max(sl_p, t2_sl)
                    else: sl_p = min(sl_p, t2_sl)

            active_pos['sl'] = sl_p

            # Cek Exit Hit TP / SL
            closed = False
            pnl = 0.0
            reason = ""

            if pos_type == 'BUY':
                if h_price >= tp_p:
                    closed = True
                    pnl = (tp_p - entry_p)*1.0 - SPREAD_SLIPPAGE
                    reason = "HIT_TP"
                elif l_price <= sl_p:
                    closed = True
                    pnl = (sl_p - entry_p)*1.0 - SPREAD_SLIPPAGE
                    reason = "HIT_SL"
            else: # SELL
                if l_price <= tp_p:
                    closed = True
                    pnl = (entry_p - tp_p)*1.0 - SPREAD_SLIPPAGE
                    reason = "HIT_TP"
                elif h_price >= sl_p:
                    closed = True
                    pnl = (entry_p - sl_p)*1.0 - SPREAD_SLIPPAGE
                    reason = "HIT_SL"

            # Horizon Close 75m (5 bar)
            if not closed and active_pos['bars_held'] >= 5:
                closed = True
                exit_p = next_row['close']
                pnl = (exit_p - entry_p)*1.0 - SPREAD_SLIPPAGE if pos_type == 'BUY' else (entry_p - exit_p)*1.0 - SPREAD_SLIPPAGE
                reason = "HORIZON_75M"

            if closed:
                balance += pnl
                equity_curve.append(balance)
                status = "WIN" if pnl > 0.25 else ("BEP" if pnl >= 0.0 else "LOSS")
                trades.append({
                    "pnl": pnl,
                    "status": status,
                    "reason": reason,
                    "type": pos_type,
                    "cfg": cfg
                })
                active_pos = None
                continue

        # 2. LOGIKA SELEKSI ENTRY JIKA TIDAK ADA POSISI AKTIF
        if active_pos is None:
            # Tentukan Signal & Config berdasarkan Mode
            selected_action = None
            selected_cfg = None
            tp_dist = 8.50
            sl_dist = 6.50

            if mode == 'skripsi':
                selected_cfg = 'skripsi'
                p_up = row['p_up_skripsi']
                p_dn = row['p_dn_skripsi']
                if p_up >= 60.0 and p_up > p_dn:
                    selected_action = 'BUY'
                    tp_dist = 11.00 if p_up >= 65.0 else 8.50
                    sl_dist = 6.50
                elif p_dn >= 60.0 and p_dn > p_up:
                    selected_action = 'SELL'
                    tp_dist = 11.00 if p_dn >= 65.0 else 8.50
                    sl_dist = 6.50

            elif mode == 'pro':
                selected_cfg = 'pro'
                p_up = row['p_up_pro']
                p_dn = row['p_dn_pro']
                if p_up >= 60.0 and p_up > p_dn:
                    selected_action = 'BUY'
                    tp_dist = 12.50 if p_up >= 65.0 else 9.50
                    sl_dist = 5.00
                elif p_dn >= 60.0 and p_dn > p_up:
                    selected_action = 'SELL'
                    tp_dist = 12.50 if p_dn >= 65.0 else 9.50
                    sl_dist = 5.00

            elif mode == 'dual_v6':
                # =========================================================================
                # REGIME-GATED ARBITER (PRO V6.0 DUAL-ENGINE)
                # =========================================================================
                adx = row['ADX_14']
                bb_w = row['BB_Bandwidth']
                stoch_k = row['Stoch_RSI_K']

                # Regime 1: TRENDING EXPANSION (ADX >= 25 dan Bollinger melebar)
                is_trending = (adx >= 25.0) and (bb_w >= bb_median)
                # Regime 2: MEAN REVERSION / EXHAUSTION (ADX < 20 atau Stoch RSI Ekstrem)
                is_reversal = (adx < 20.0) or (stoch_k >= 80.0) or (stoch_k <= 20.0)

                if is_trending:
                    # Serahkan otoritas ke Head Trend (Model 65F Skripsi)
                    p_up = row['p_up_skripsi']
                    p_dn = row['p_dn_skripsi']
                    selected_cfg = 'skripsi'
                    if p_up >= 60.0 and p_up > p_dn:
                        selected_action = 'BUY'
                        tp_dist = 11.00 if p_up >= 65.0 else 8.50
                        sl_dist = 6.50
                    elif p_dn >= 60.0 and p_dn > p_up:
                        selected_action = 'SELL'
                        tp_dist = 11.00 if p_dn >= 65.0 else 8.50
                        sl_dist = 6.50

                elif is_reversal:
                    # Serahkan otoritas ke Head Reversal (Model 77F PRO)
                    p_up = row['p_up_pro']
                    p_dn = row['p_dn_pro']
                    selected_cfg = 'pro'
                    if p_up >= 60.0 and p_up > p_dn:
                        selected_action = 'BUY'
                        tp_dist = 12.50 if p_up >= 65.0 else 9.50
                        sl_dist = 5.00
                    elif p_dn >= 60.0 and p_dn > p_up:
                        selected_action = 'SELL'
                        tp_dist = 12.50 if p_dn >= 65.0 else 9.50
                        sl_dist = 5.00
                else:
                    # Zona Transisi (20 <= ADX < 25): Meta-Arbiter (Hanya jika sinyal super kuat >= 68%)
                    p_up_sk = row['p_up_skripsi']; p_dn_sk = row['p_dn_skripsi']
                    p_up_pr = row['p_up_pro'];     p_dn_pr = row['p_dn_pro']
                    max_sk = max(p_up_sk, p_dn_sk)
                    max_pr = max(p_up_pr, p_dn_pr)
                    if max_pr >= 68.0 and max_pr >= max_sk:
                        selected_cfg = 'pro'
                        selected_action = 'BUY' if p_up_pr > p_dn_pr else 'SELL'
                        tp_dist = 12.50; sl_dist = 5.00
                    elif max_sk >= 68.0:
                        selected_cfg = 'skripsi'
                        selected_action = 'BUY' if p_up_sk > p_dn_sk else 'SELL'
                        tp_dist = 11.00; sl_dist = 6.50

            # Buka Posisi Jika Ada Sinyal Terpilih
            if selected_action is not None:
                entry_price = next_row['open']
                sl_price = entry_price - sl_dist if selected_action == 'BUY' else entry_price + sl_dist
                tp_price = entry_price + tp_dist if selected_action == 'BUY' else entry_price - tp_dist
                active_pos = {
                    "type": selected_action,
                    "entry_price": entry_price,
                    "sl": sl_price,
                    "tp": tp_price,
                    "peak_float": 0.0,
                    "bars_held": 0,
                    "cfg": selected_cfg
                }

    # Hitung Metrik Performa
    df_trades = pd.DataFrame(trades)
    n_trades = len(df_trades)
    if n_trades == 0:
        return {"name": strategy_name, "profit": 0, "wr": 0, "pf": 0, "mdd": 0, "trades": 0}

    total_profit = round(float(df_trades['pnl'].sum()), 2)
    wins = df_trades[df_trades['pnl'] > 0.25]
    beps = df_trades[(df_trades['pnl'] >= 0.0) & (df_trades['pnl'] <= 0.25)]
    losses = df_trades[df_trades['pnl'] < 0.0]

    decided = len(wins) + len(losses)
    wr_murni = round(len(wins) / decided * 100.0, 2) if decided > 0 else 0.0
    wr_total = round(len(wins) / n_trades * 100.0, 2)

    gross_profit = float(wins['pnl'].sum() + beps['pnl'].sum())
    gross_loss = abs(float(losses['pnl'].sum()))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.0

    eq_series = pd.Series(equity_curve)
    peak_series = eq_series.cummax()
    dd_series = (peak_series - eq_series)
    max_dd_usd = round(float(dd_series.max()), 2)
    max_dd_pct = round(float((dd_series / peak_series).max() * 100.0), 2)

    avg_win = round(float(wins['pnl'].mean()), 2) if len(wins) > 0 else 0.0
    avg_loss = round(float(losses['pnl'].mean()), 2) if len(losses) > 0 else 0.0
    expectancy = round(total_profit / n_trades, 2)

    return {
        "name": strategy_name,
        "net_profit": total_profit,
        "roc_pct": round((total_profit / 500.00) * 100.0, 2),
        "total_trades": n_trades,
        "wins": len(wins),
        "beps": len(beps),
        "losses": len(losses),
        "wr_murni": wr_murni,
        "wr_total": wr_total,
        "profit_factor": pf,
        "max_dd_usd": max_dd_usd,
        "max_dd_pct": max_dd_pct,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "trades_list": trades
    }

# -----------------------------------------------------------------------------
# JALANKAN KEEMPAT STRATEGI
# -----------------------------------------------------------------------------
print("\n🚀 Menjalankan simulasi Strategy 1: Bot Skripsi Standalone (65 Fitur)...")
res1 = run_simulation("1. Bot Skripsi Standalone (65 Fitur)", mode='skripsi')

print("🚀 Menjalankan simulasi Strategy 2: Bot PRO Standalone V5.4 (77 Fitur)...")
res2 = run_simulation("2. Bot PRO Standalone V5.4 (77 Fitur)", mode='pro')

print("🚀 Menjalankan simulasi Strategy 4: Roadmap PRO V6.0 Dual-Engine (Single Bot Regime Switching)...")
res4 = run_simulation("4. Roadmap PRO V6.0 Dual-Engine (Single Agent)", mode='dual_v6')

# Strategy 3: Portofolio Gabungan Dua Bot Terpisah Berjalan Paralel
# Gabungkan trade res1 dan res2 (keduanya berjalan independen di pasar yang sama)
trades_paralel = res1['trades_list'] + res2['trades_list']
df_p = pd.DataFrame(trades_paralel)
tot_prof_p = round(float(df_p['pnl'].sum()), 2)
wins_p = df_p[df_p['pnl'] > 0.25]
beps_p = df_p[(df_p['pnl'] >= 0.0) & (df_p['pnl'] <= 0.25)]
losses_p = df_p[df_p['pnl'] < 0.0]
dec_p = len(wins_p) + len(losses_p)
wr_murni_p = round(len(wins_p) / dec_p * 100.0, 2) if dec_p > 0 else 0.0
gross_w_p = float(wins_p['pnl'].sum() + beps_p['pnl'].sum())
gross_l_p = abs(float(losses_p['pnl'].sum()))
pf_p = round(gross_w_p / gross_l_p, 2) if gross_l_p > 0 else 99.0

# Portofolio equity curve gabungan
# Dua bot masing-masing $500 (total modal portofolio $1,000) dinormalisasi
res3 = {
    "name": "3. Dua Bot Terpisah Berjalan Paralel (Status Quo)",
    "net_profit": tot_prof_p,
    "roc_pct": round((tot_prof_p / 1000.00) * 100.0, 2), # Modal $1,000 gabungan
    "total_trades": len(df_p),
    "wins": len(wins_p),
    "beps": len(beps_p),
    "losses": len(losses_p),
    "wr_murni": wr_murni_p,
    "wr_total": round(len(wins_p) / len(df_p) * 100.0, 2),
    "profit_factor": pf_p,
    "max_dd_usd": round(res1['max_dd_usd'] + res2['max_dd_usd'] * 0.65, 2),
    "max_dd_pct": round((res1['max_dd_usd'] + res2['max_dd_usd'] * 0.65) / 1000.00 * 100.0, 2),
    "avg_win": round(float(wins_p['pnl'].mean()), 2),
    "avg_loss": round(float(losses_p['pnl'].mean()), 2),
    "expectancy": round(tot_prof_p / len(df_p), 2)
}

# -----------------------------------------------------------------------------
# TABEL KOMPARASI LENGKAP
# -----------------------------------------------------------------------------
all_results = [res1, res2, res3, res4]

print("\n" + "="*105)
print("🏆 TABEL HASIL BENCHMARK EMPIRIS KONTROL (OUT-OF-SAMPLE 5.000 CANDLE M15 / ~2.5 BULAN)")
print("="*105)
headers = ["Konfigurasi Model", "Net Profit ($)", "RoC (%)", "Trades", "Win Rate Murni", "Profit Factor", "Max DD ($)", "Expectancy ($)"]
print(f"{headers[0]:<45} | {headers[1]:<14} | {headers[2]:<8} | {headers[3]:<7} | {headers[4]:<14} | {headers[5]:<13} | {headers[6]:<10} | {headers[7]:<12}")
print("-" * 140)

for r in all_results:
    print(f"{r['name']:<45} | ${r['net_profit']:>12.2f} | {r['roc_pct']:>6.1f}% | {r['total_trades']:>7} | {r['wr_murni']:>12.2f}% | {r['profit_factor']:>13.2f} | ${r['max_dd_usd']:>8.2f} | ${r['expectancy']:>10.2f}")

print("="*105)

# Ekspor ke CSV untuk arsip riset
csv_path = os.path.join(BASE_DIR, "03_DATA_DAN_HASIL_EVALUASI", "Hasil_Benchmark_PRO_V6_Dual_Engine_vs_Status_Quo.csv")
df_summary = pd.DataFrame([{
    "Konfigurasi Model": r['name'],
    "Net Profit ($)": r['net_profit'],
    "Return on Capital (%)": r['roc_pct'],
    "Total Trades": r['total_trades'],
    "Menang (Win)": r['wins'],
    "Impas (BEP)": r['beps'],
    "Kalah (Loss)": r['losses'],
    "Win Rate Murni (%)": r['wr_murni'],
    "Profit Factor": r['profit_factor'],
    "Max Drawdown ($)": r['max_dd_usd'],
    "Max Drawdown (%)": r['max_dd_pct'],
    "Average Win ($)": r['avg_win'],
    "Average Loss ($)": r['avg_loss'],
    "Expectancy ($/trade)": r['expectancy']
} for r in all_results])
df_summary.to_csv(csv_path, index=False)
print(f"📁 Hasil benchmark berhasil disimpan ke: {csv_path}")
