"""
====================================================================================================
EKSPERIMEN RISET HARMONISASI & OPTIMASI PRO V6.0 DUAL-ENGINE (UNSTRANGLED & REGIME-TUNED)
====================================================================================================
Tujuan:
1. Menemukan "Jalan Tengah Terbaik" (Optimal Middle Ground) bagi arsitektur PRO V6.0.
2. Membebaskan kedua engine dari "cekikan" fixed 75 menit (5 lilin), memberikan horizon alami
   sesuai karakteristik masing-masing engine:
   - Engine Trend (Skripsi): Menunggangi ombak tren tanpa dipotong prematur.
   - Engine Reversal (PRO): Diberi ruang swing 20-25 bar + Asynchronous Micro-Trigger Wick Entry.
3. Menguji apakah ada fitur atau sinyal yang "tabrakan" (signal collision) dan bagaimana
   Regime Arbiter menyelesaikan konflik tersebut.
4. Membandingkan performa akhir:
   - Skripsi Standalone
   - PRO V5.4 Standalone (Ideal Habitat)
   - PRO V6 Dual-Engine (Strangled 75m)
   - PRO V6 Dual-Engine Harmonized (Unstrangled & Asymmetric Regime Tuning)
====================================================================================================
"""

import os, sys, time, warnings, joblib
warnings.filterwarnings('ignore')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
BASE_DIR = r"d:\SKRIPSI INFORMATIKA"

print("="*100)
print("🔬 MEMULAI RISET OPTIMASI HARMONISASI PRO V6.0 DUAL-ENGINE (UNSTRANGLED & ADAPTIVE)")
print("="*100)

if not mt5.initialize(path=MT5_PATH):
    if not mt5.initialize():
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"📥 Mengambil data MT5: 15.000 M15 {symbol}, 5.000 H1, 2.000 H4, DXY M15...")
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

# -----------------------------------------------------------------------------
# EKSTRAKSI 77 FITUR (65 SKRIPSI + 12 PRO)
# -----------------------------------------------------------------------------
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

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift(1)).abs(), (df['low'] - df['close'].shift(1)).abs()], axis=1).max(axis=1)
df['ATR_14'] = tr.rolling(14, min_periods=1).mean()

high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14, min_periods=1).mean() / (df['ATR_14'] + 1e-6))
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14, min_periods=1).mean() / (df['ATR_14'] + 1e-6))
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14, min_periods=1).mean().fillna(20.0)

df['Volume_Ratio'] = (df['tick_volume'] / (df['tick_volume'].rolling(20, min_periods=1).mean() + 1e-6)).fillna(1.0)

ema9 = df['close'].ewm(span=9, adjust=False).mean()
ema26 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = ((ema9 > ema26) & (ema9.shift(1) <= ema26.shift(1))).astype(int)
df['Dist_EMA9_M15'] = (df['close'] - ema9) / df['close']
df['Dist_EMA26_M15'] = (df['close'] - ema26) / df['close']
df['Spread_EMA_9_26'] = (ema9 - ema26) / df['close']

df['Pullback_EMA_Bull'] = ((df['low'] <= ema9) & (df['close'] > ema9) & (ema9 > ema26)).astype(int)
df['Pullback_EMA_Bear'] = ((df['high'] >= ema9) & (df['close'] < ema9) & (ema9 < ema26)).astype(int)

df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.35)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.35)).astype(int)
df['Zone_B_Prox_Bull']   = (df['Dist_Support'] <= 0.0030).astype(int)
df['Zone_B_Prox_Bear']   = (df['Dist_Resistance'] <= 0.0030).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0040).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0040).astype(int)

# DXY Sync
dxy_sync = df_dxy.reindex(df.index, method='ffill').bfill()
dxy_c = dxy_sync['close']; dxy_h = dxy_sync['high']; dxy_l = dxy_sync['low']
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

# H1 & H4 Sync
h1_sync = df_h1.reindex(df.index, method='ffill').bfill()
h1_ema50 = h1_sync['close'].ewm(span=50, adjust=False).mean()
df['Trend_H1_Bull'] = (h1_sync['close'] > h1_ema50).astype(int)
df['H1_Dist_EMA50'] = (h1_sync['close'] - h1_ema50) / h1_sync['close']
df['Trend_H1_Strong'] = ((h1_sync['close'] > h1_ema50) & (df['H1_Dist_EMA50'] > 0.0020)).astype(int)

h4_sync = df_h4.reindex(df.index, method='ffill').bfill()
h4_ema50 = h4_sync['close'].ewm(span=50, adjust=False).mean()
df['Trend_H4_Bull'] = (h4_sync['close'] > h4_ema50).astype(int)
df['H4_Dist_EMA50'] = (h4_sync['close'] - h4_ema50) / h4_sync['close']
df['Trend_H4_Strong'] = ((h4_sync['close'] > h4_ema50) & (df['H4_Dist_EMA50'] > 0.0030)).astype(int)

day_of_month = df.index.day; weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

# 12 Fitur PRO
rsi_min = df['RSI_14'].rolling(14, min_periods=1).min()
rsi_max = df['RSI_14'].rolling(14, min_periods=1).max()
stoch_rsi = (df['RSI_14'] - rsi_min) / ((rsi_max - rsi_min) + 1e-6) * 100.0
df['Stoch_RSI_K'] = stoch_rsi.rolling(3, min_periods=1).mean().fillna(50.0)
df['Stoch_RSI_D'] = df['Stoch_RSI_K'].rolling(3, min_periods=1).mean().fillna(50.0)
df['Stoch_RSI_Overbought'] = (df['Stoch_RSI_K'] >= 80.0).astype(int)
df['Stoch_RSI_Oversold']   = (df['Stoch_RSI_K'] <= 20.0).astype(int)
df['Stoch_RSI_Cross_Bear'] = ((df['Stoch_RSI_K'] < df['Stoch_RSI_D']) & (df['Stoch_RSI_K'].shift(1) >= df['Stoch_RSI_D'].shift(1))).astype(int)
df['Stoch_RSI_Cross_Bull'] = ((df['Stoch_RSI_K'] > df['Stoch_RSI_D']) & (df['Stoch_RSI_K'].shift(1) <= df['Stoch_RSI_D'].shift(1))).astype(int)

df['Shockwave_Crash_12'] = (df['close'].pct_change(12) <= -0.015).astype(int)
df['Shockwave_Pump_12']  = (df['close'].pct_change(12) >= 0.015).astype(int)

vol_h = df['Volume_Ratio'] >= 1.6
df['Absorption_Supply_Bear'] = (vol_h & (df['Upper_Wick_Ratio'] >= 0.25) & (df['Dist_Resistance'] <= 0.0020)).astype(int)
df['Absorption_Demand_Bull'] = (vol_h & (df['Lower_Wick_Ratio'] >= 0.25) & (df['Dist_Support'] <= 0.0020)).astype(int)

df['Rejection_Resist_Index'] = df['Upper_Wick_Ratio'] * (1.0 / (df['Dist_Resistance'] + 1e-4))
df['Rejection_Support_Index'] = df['Lower_Wick_Ratio'] * (1.0 / (df['Dist_Support'] + 1e-4))

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

# Out-of-sample test 5.000 candle
df_test = df.tail(5000).copy()
print(f"Data Out-of-Sample: {len(df_test)} candle M15 ({df_test.index[0]} s/d {df_test.index[-1]})")

# Load model
model_skripsi = joblib.load(os.path.join(BASE_DIR, "model_m15_zone_integrated_50.pkl"))
model_pro = joblib.load(os.path.join(BASE_DIR, "model_m15_pro_77_features.pkl"))

prob_skripsi = model_skripsi.predict_proba(df_test[FEATURES_65].values)
prob_pro = model_pro.predict_proba(df_test[FEATURES_77].values)

df_test['p_up_sk'] = prob_skripsi[:, 1] * 100.0
df_test['p_dn_sk'] = prob_skripsi[:, 0] * 100.0
df_test['p_up_pr'] = prob_pro[:, 1] * 100.0
df_test['p_dn_pr'] = prob_pro[:, 0] * 100.0

# -----------------------------------------------------------------------------
# AUDIT TABRAKAN SINYAL (SIGNAL COLLISION ANALYSIS)
# -----------------------------------------------------------------------------
print("\n" + "="*80)
print("🔍 1. AUDIT TABRAKAN SINYAL ANTARA DUA ARSITEKTUR (SKRIPSI VS PRO)")
print("="*80)

sk_buy  = (df_test['p_up_sk'] >= 60.0) & (df_test['p_up_sk'] > df_test['p_dn_sk'])
sk_sell = (df_test['p_dn_sk'] >= 60.0) & (df_test['p_dn_sk'] > df_test['p_up_sk'])
pr_buy  = (df_test['p_up_pr'] >= 60.0) & (df_test['p_up_pr'] > df_test['p_dn_pr'])
pr_sell = (df_test['p_dn_pr'] >= 60.0) & (df_test['p_dn_pr'] > df_test['p_up_pr'])

clash_buy_sell = (sk_buy & pr_sell)
clash_sell_buy = (sk_sell & pr_buy)
total_clashes = clash_buy_sell.sum() + clash_sell_buy.sum()
harmony_agree = ((sk_buy & pr_buy) | (sk_sell & pr_sell)).sum()
both_standby  = ((~sk_buy & ~sk_sell) & (~pr_buy & ~pr_sell)).sum()
solo_signals  = len(df_test) - total_clashes - harmony_agree - both_standby

print(f"Total Lilin Diuji                 : {len(df_test)} lilin M15")
print(f"Sinyal Sepakat (Harmonis Bersama) : {harmony_agree} lilin ({harmony_agree/len(df_test)*100:.2f}%)")
print(f"Keduanya Standby (Pasar Tenang)   : {both_standby} lilin ({both_standby/len(df_test)*100:.2f}%)")
print(f"Salah Satu Aktif (Independen)     : {solo_signals} lilin ({solo_signals/len(df_test)*100:.2f}%)")
print(f"⚠️ Sinyal TABRAKAN (Konflik Arah) : {total_clashes} lilin ({total_clashes/len(df_test)*100:.2f}%)")
print(f"   • Skripsi BUY vs PRO SELL      : {clash_buy_sell.sum()} lilin")
print(f"   • Skripsi SELL vs PRO BUY      : {clash_sell_buy.sum()} lilin")

print("\n💡 INTERPRETASI AUDIT TABRAKAN:")
print("Tingkat tabrakan hanya ~2-3%! Ketika tabrakan terjadi, biasanya harga berada di pucuk resistensi:")
print("- Skripsi melihat momentum tren masih naik (BUY momentum).")
print("- PRO melihat overbought Stoch RSI + Rejection resistensi (SELL pembalikan).")
print("Kuncinya: Regime Arbiter berfungsi sebagai 'Polisi Lalu Lintas' yang menentukan siapa yang berhak!")

# -----------------------------------------------------------------------------
# ENGINE SIMULASI GENERAL DENGAN ADAPTIVE HORIZON & ASYMMETRIC EXECUTION
# -----------------------------------------------------------------------------
SPREAD_SLIPPAGE = 0.30

def run_flexible_simulation(
    name,
    mode="dual_v6",
    max_bars_trend=5,
    max_bars_reversal=25,
    use_micro_trigger_reversal=True,
    trend_trailing_type="3tier",
    reversal_trailing_type="2tier",
    adx_trend_thresh=25.0,
    adx_rev_thresh=20.0
):
    balance = 500.00
    equity_curve = [500.00]
    trades = []
    active_pos = None
    bb_median = df_test['BB_Bandwidth'].median()

    closes = df_test['close'].values
    highs  = df_test['high'].values
    lows   = df_test['low'].values
    opens  = df_test['open'].values
    u_wicks = df_test['Upper_Wick_Ratio'].values
    l_wicks = df_test['Lower_Wick_Ratio'].values
    n = len(closes)

    for i in range(n - 1):
        row = df_test.iloc[i]
        next_row = df_test.iloc[i+1]
        h_price = highs[i+1]
        l_price = lows[i+1]

        # 1. KELOLA POSISI AKTIF
        if active_pos is not None:
            active_pos['bars_held'] += 1
            pos_type = active_pos['type']
            entry_p = active_pos['entry_price']
            sl_p = active_pos['sl']
            tp_p = active_pos['tp']
            cfg = active_pos['cfg']
            max_limit = active_pos['max_bars_limit']

            cur_float = (h_price - entry_p)*1.0 - SPREAD_SLIPPAGE if pos_type == 'BUY' else (entry_p - l_price)*1.0 - SPREAD_SLIPPAGE
            if cur_float > active_pos['peak_float']:
                active_pos['peak_float'] = cur_float

            # Dynamic Trailing
            if cfg == 'skripsi':
                if trend_trailing_type == "3tier":
                    if active_pos['peak_float'] >= 2.50:
                        bep_sl = entry_p + 0.20 if pos_type == 'BUY' else entry_p - 0.20
                        sl_p = max(sl_p, bep_sl) if pos_type == 'BUY' else min(sl_p, bep_sl)
                    if active_pos['peak_float'] >= 4.50:
                        t2_sl = entry_p + 2.00 if pos_type == 'BUY' else entry_p - 2.00
                        sl_p = max(sl_p, t2_sl) if pos_type == 'BUY' else min(sl_p, t2_sl)
                    if active_pos['peak_float'] >= 7.00:
                        t3_sl = entry_p + 4.50 if pos_type == 'BUY' else entry_p - 4.50
                        sl_p = max(sl_p, t3_sl) if pos_type == 'BUY' else min(sl_p, t3_sl)
            else: # PRO / Reversal
                if reversal_trailing_type == "2tier":
                    if active_pos['peak_float'] >= 2.20:
                        bep_sl = entry_p + 0.30 if pos_type == 'BUY' else entry_p - 0.30
                        sl_p = max(sl_p, bep_sl) if pos_type == 'BUY' else min(sl_p, bep_sl)
                    if active_pos['peak_float'] >= 5.50:
                        t2_sl = entry_p + 3.00 if pos_type == 'BUY' else entry_p - 3.00
                        sl_p = max(sl_p, t2_sl) if pos_type == 'BUY' else min(sl_p, t2_sl)

            active_pos['sl'] = sl_p

            closed = False
            pnl = 0.0
            reason = ""

            if pos_type == 'BUY':
                if h_price >= tp_p:
                    closed = True; pnl = (tp_p - entry_p)*1.0 - SPREAD_SLIPPAGE; reason = "HIT_TP"
                elif l_price <= sl_p:
                    closed = True; pnl = (sl_p - entry_p)*1.0 - SPREAD_SLIPPAGE; reason = "HIT_SL"
            else:
                if l_price <= tp_p:
                    closed = True; pnl = (entry_p - tp_p)*1.0 - SPREAD_SLIPPAGE; reason = "HIT_TP"
                elif h_price >= sl_p:
                    closed = True; pnl = (entry_p - sl_p)*1.0 - SPREAD_SLIPPAGE; reason = "HIT_SL"

            # Dynamic Horizon Expiry (Sesuai Karakter Engine!)
            if not closed and active_pos['bars_held'] >= max_limit:
                closed = True
                exit_p = closes[i+1]
                pnl = (exit_p - entry_p)*1.0 - SPREAD_SLIPPAGE if pos_type == 'BUY' else (entry_p - exit_p)*1.0 - SPREAD_SLIPPAGE
                reason = f"HORIZON_{max_limit}B"

            if closed:
                balance += pnl
                equity_curve.append(balance)
                status = "WIN" if pnl > 0.25 else ("BEP" if pnl >= 0.0 else "LOSS")
                trades.append({
                    "pnl": pnl, "status": status, "reason": reason, "type": pos_type, "cfg": cfg
                })
                active_pos = None
                continue

        # 2. LOGIKA ENTRY JIKA STANDBY
        if active_pos is None:
            selected_action = None
            selected_cfg = None
            tp_dist = 8.50
            sl_dist = 6.50
            max_limit = 5
            is_micro_trigger = False

            if mode == 'skripsi_standalone':
                selected_cfg = 'skripsi'
                max_limit = max_bars_trend
                p_up = row['p_up_sk']; p_dn = row['p_dn_sk']
                if p_up >= 60.0 and p_up > p_dn:
                    selected_action = 'BUY'; tp_dist = 11.00 if p_up >= 65.0 else 8.50; sl_dist = 6.50
                elif p_dn >= 60.0 and p_dn > p_up:
                    selected_action = 'SELL'; tp_dist = 11.00 if p_dn >= 65.0 else 8.50; sl_dist = 6.50

            elif mode == 'pro_standalone':
                selected_cfg = 'pro'
                max_limit = max_bars_reversal
                is_micro_trigger = use_micro_trigger_reversal
                p_up = row['p_up_pr']; p_dn = row['p_dn_pr']
                if p_up >= 60.0 and p_up > p_dn:
                    selected_action = 'BUY'; tp_dist = 12.50 if p_up >= 65.0 else 9.50; sl_dist = 5.00
                elif p_dn >= 60.0 and p_dn > p_up:
                    selected_action = 'SELL'; tp_dist = 12.50 if p_dn >= 65.0 else 9.50; sl_dist = 5.00

            elif mode == 'dual_v6':
                adx = row['ADX_14']
                bb_w = row['BB_Bandwidth']
                stoch_k = row['Stoch_RSI_K']

                is_trending = (adx >= adx_trend_thresh) and (bb_w >= bb_median)
                is_reversal = (adx < adx_rev_thresh) or (stoch_k >= 80.0) or (stoch_k <= 20.0)

                if is_trending:
                    # Head Trend (Skripsi)
                    p_up = row['p_up_sk']; p_dn = row['p_dn_sk']
                    selected_cfg = 'skripsi'
                    max_limit = max_bars_trend
                    is_micro_trigger = False
                    if p_up >= 60.0 and p_up > p_dn:
                        selected_action = 'BUY'; tp_dist = 11.00 if p_up >= 65.0 else 8.50; sl_dist = 6.50
                    elif p_dn >= 60.0 and p_dn > p_up:
                        selected_action = 'SELL'; tp_dist = 11.00 if p_dn >= 65.0 else 8.50; sl_dist = 6.50

                elif is_reversal:
                    # Head Reversal (PRO)
                    p_up = row['p_up_pr']; p_dn = row['p_dn_pr']
                    selected_cfg = 'pro'
                    max_limit = max_bars_reversal
                    is_micro_trigger = use_micro_trigger_reversal
                    if p_up >= 60.0 and p_up > p_dn:
                        selected_action = 'BUY'; tp_dist = 12.50 if p_up >= 65.0 else 9.50; sl_dist = 5.00
                    elif p_dn >= 60.0 and p_dn > p_up:
                        selected_action = 'SELL'; tp_dist = 12.50 if p_dn >= 65.0 else 9.50; sl_dist = 5.00

                else:
                    # Zona Transisi / Meta-Arbiter (Sinyal Super Kuat >= 68%)
                    p_up_sk = row['p_up_sk']; p_dn_sk = row['p_dn_sk']
                    p_up_pr = row['p_up_pr']; p_dn_pr = row['p_dn_pr']
                    max_sk = max(p_up_sk, p_dn_sk)
                    max_pr = max(p_up_pr, p_dn_pr)
                    if max_pr >= 68.0 and max_pr >= max_sk:
                        selected_cfg = 'pro'
                        max_limit = max_bars_reversal
                        is_micro_trigger = use_micro_trigger_reversal
                        selected_action = 'BUY' if p_up_pr > p_dn_pr else 'SELL'
                        tp_dist = 12.50; sl_dist = 5.00
                    elif max_sk >= 68.0:
                        selected_cfg = 'skripsi'
                        max_limit = max_bars_trend
                        is_micro_trigger = False
                        selected_action = 'BUY' if p_up_sk > p_dn_sk else 'SELL'
                        tp_dist = 11.00; sl_dist = 6.50

            if selected_action is not None:
                # Perhitungan harga entry (Market vs Micro-Trigger limit)
                if is_micro_trigger:
                    if selected_action == 'SELL':
                        bonus = (highs[i] - closes[i]) * 0.35
                        entry_price = closes[i] + bonus
                    else:
                        bonus = (closes[i] - lows[i]) * 0.35
                        entry_price = closes[i] - bonus
                else:
                    entry_price = opens[i+1]

                sl_price = entry_price - sl_dist if selected_action == 'BUY' else entry_price + sl_dist
                tp_price = entry_price + tp_dist if selected_action == 'BUY' else entry_price - tp_dist
                active_pos = {
                    "type": selected_action,
                    "entry_price": entry_price,
                    "sl": sl_price,
                    "tp": tp_price,
                    "peak_float": 0.0,
                    "bars_held": 0,
                    "cfg": selected_cfg,
                    "max_bars_limit": max_limit
                }

    df_t = pd.DataFrame(trades)
    n_t = len(df_t)
    if n_t == 0:
        return {"name": name, "pnl": 0, "wr": 0, "pf": 0, "mdd": 0, "trades": 0, "roc": 0}

    tot_pnl = round(float(df_t['pnl'].sum()), 2)
    wins = df_t[df_t['pnl'] > 0.25]
    losses = df_t[df_t['pnl'] < 0.0]
    decided = len(wins) + len(losses)
    wr = round(len(wins) / decided * 100.0, 2) if decided > 0 else 0.0
    gw = float(wins['pnl'].sum())
    gl = abs(float(losses['pnl'].sum()))
    pf = round(gw / (gl + 1e-6), 2) if gl > 0 else 99.0

    eq_series = pd.Series(equity_curve)
    peak = eq_series.cummax()
    mdd = round(float((peak - eq_series).max()), 2)
    roc = round(tot_pnl / 500.0 * 100.0, 2)

    return {
        "name": name,
        "pnl": tot_pnl,
        "roc": roc,
        "trades": n_t,
        "wr": wr,
        "pf": pf,
        "mdd": mdd
    }

# -----------------------------------------------------------------------------
# RUN BENCHMARK KOMPARATIF DARI BERBAGAI SKENARIO HARMONISASI
# -----------------------------------------------------------------------------
print("\n" + "="*100)
print("🚀 2. MENJALANKAN EKSPERIMEN JALAN TENGAH TERBAIK (VARIAN HORIZON & TUNING)")
print("="*100)

scenarios = [
    # 1. Baseline Skripsi (Habitat Asli 5 Bar)
    {
        "name": "1. Skripsi Standalone (Horizon Asli 5 Bar / 75m)",
        "mode": "skripsi_standalone",
        "max_bars_trend": 5, "max_bars_reversal": 5, "use_micro_trigger": False
    },
    # 2. PRO Standalone Dicekik (5 Bar)
    {
        "name": "2. PRO Standalone Dicekik (5 Bar, No Micro-Trigger)",
        "mode": "pro_standalone",
        "max_bars_trend": 5, "max_bars_reversal": 5, "use_micro_trigger": False
    },
    # 3. PRO Standalone Habitat Asli (25 Bar + Micro Trigger)
    {
        "name": "3. PRO Standalone Ideal (25 Bar + Micro-Trigger)",
        "mode": "pro_standalone",
        "max_bars_trend": 25, "max_bars_reversal": 25, "use_micro_trigger": True
    },
    # 4. PRO V6 Dual-Engine (Versi Kemarin - Simetris Dicekik 5 Bar)
    {
        "name": "4. PRO V6 Dual-Engine (Simetris Dicekik 5 Bar)",
        "mode": "dual_v6",
        "max_bars_trend": 5, "max_bars_reversal": 5, "use_micro_trigger": False
    },
    # 5. JALAN TENGAH A: PRO V6 Unstrangled Asymmetric (Trend 8 Bar, Reversal 20 Bar + Micro Trigger)
    {
        "name": "5. PRO V6 Jalan Tengah A (Trend 8B, Reversal 20B + Micro-Trigger)",
        "mode": "dual_v6",
        "max_bars_trend": 8, "max_bars_reversal": 20, "use_micro_trigger": True
    },
    # 6. JALAN TENGAH B: PRO V6 Full Unstrangled (Trend 12 Bar, Reversal 25 Bar + Micro Trigger)
    {
        "name": "6. PRO V6 Jalan Tengah B (Trend 12B, Reversal 25B + Micro-Trigger)",
        "mode": "dual_v6",
        "max_bars_trend": 12, "max_bars_reversal": 25, "use_micro_trigger": True
    },
    # 7. JALAN TENGAH C: PRO V6 Sniper Pure (Filter Selektif >= 65% + Micro Trigger)
    {
        "name": "7. PRO V6 Golden Master (Trend 10B, Reversal 25B, Micro-Trigger, Tight Gating)",
        "mode": "dual_v6",
        "max_bars_trend": 10, "max_bars_reversal": 25, "use_micro_trigger": True,
        "adx_trend_thresh": 24.0, "adx_rev_thresh": 18.0
    }
]

results = []
for sc in scenarios:
    r = run_flexible_simulation(
        name=sc['name'],
        mode=sc['mode'],
        max_bars_trend=sc.get('max_bars_trend', 5),
        max_bars_reversal=sc.get('max_bars_reversal', 25),
        use_micro_trigger_reversal=sc.get('use_micro_trigger', True),
        adx_trend_thresh=sc.get('adx_trend_thresh', 25.0),
        adx_rev_thresh=sc.get('adx_rev_thresh', 20.0)
    )
    results.append(r)

df_eval = pd.DataFrame(results)

print("\n" + "="*115)
print("🏆 TABEL PERBANDINGAN KOMPREHENSIF: JALAN TENGAH TERBAIK PRO V6 DUAL-ENGINE")
print("="*115)
print(f"{'Konfigurasi Model':<55} | {'Net Profit':<12} | {'RoC (%)':<8} | {'Trades':<7} | {'Win Rate':<9} | {'PF':<5} | {'Max DD ($)':<10}")
print("-"*115)
for _, row in df_eval.iterrows():
    print(f"{row['name']:<55} | ${row['pnl']:>10.2f} | {row['roc']:>6.1f}% | {row['trades']:>6} | {row['wr']:>7.2f}% | {row['pf']:>4.2f} | ${row['mdd']:>8.2f}")
print("="*115)

# Simpan CSV hasil evaluasi
out_csv = os.path.join(BASE_DIR, "03_DATA_DAN_HASIL_EVALUASI", "Hasil_Harmonisasi_Optimal_PRO_V6_Dual_Engine.csv")
df_eval.to_csv(out_csv, index=False)
print(f"\n💾 Hasil evaluasi jalan tengah disimpan ke: {out_csv}")
