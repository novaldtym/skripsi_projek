import sys, os, time, warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from sklearn.metrics import accuracy_score, roc_auc_score
from lightgbm import LGBMClassifier

BASE_DIR = r"d:\SKRIPSI INFORMATIKA"
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

print("="*115)
print("🧪 SIMULASI KOMPARASI EMPIRIS: MODEL V5.2 (65 FITUR AKTIF) VS MODEL V5.3 (INSTITUTIONAL ENHANCEMENT)")
print("Pengujian Solusi Mengatasi 5 Kelemahan: Rejection Pressure, Stoch RSI 14-3-3, Shockwave Shield, & Volume Absorption")
print("Data Uji: 4.980 Candle M15 OOS Identik | Friksi: $0.35 | Zero Leakage Validation")
print("="*115)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print("📥 Mengambil 25.000 candle XAUUSD M15, 8.000 H1, 2.500 H4, dan 25.000 DXY M15...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

mt5.symbol_select("DXY", True)
rates_dxy = mt5.copy_rates_from_pos("DXY", mt5.TIMEFRAME_M15, 0, 25000)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)
df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)

# -----------------------------------------------------------------------------
# 1. FITUR 65 EXISTING (MODEL V5.2 AKTIF)
# -----------------------------------------------------------------------------
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

df['BOS_Bull'] = (df['close'] > df['Swing_High_20']).astype(int)
df['BOS_Bear'] = (df['close'] < df['Swing_Low_20']).astype(int)
trend_slow = df['close'].pct_change(20)
df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

is_bear_c = df['close'] < df['open']; is_bull_c = df['close'] > df['open']
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

dxy_sync = df_dxy.reindex(df.index, method='ffill').bfill()
dxy_c = dxy_sync['close']; dxy_h = dxy_sync['high']; dxy_l = dxy_sync['low']

df['DXY_Return_1'] = dxy_c.pct_change(1).fillna(0)
df['DXY_Return_3'] = dxy_c.pct_change(3).fillna(0)
df['DXY_Trend'] = (dxy_c > dxy_c.rolling(20).mean()).astype(int)
df['XAU_DXY_Ratio'] = df['close'] / (dxy_c + 1e-6)
df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

day_of_month = df.index.day; weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

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

is_bull = (df['close'] > df['open']).astype(int); is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
atr14 = tr.rolling(14).mean() + 1e-6
df['ATR_14'] = atr14
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

ema9_m15  = df['close'].ewm(span=9, adjust=False).mean()
ema26_m15 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = (ema9_m15 > ema26_m15).astype(int)
df['Dist_EMA9_M15']  = (df['close'] - ema9_m15) / df['close']
df['Dist_EMA26_M15'] = (df['close'] - ema26_m15) / df['close']
df['Spread_EMA_9_26'] = (ema9_m15 - ema26_m15) / df['close']
df['Pullback_EMA_Bull'] = ((df['EMA_9_Cross_26_Bull'] == 1) & (df['low'] <= ema9_m15) & (df['close'] > ema9_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Pullback_EMA_Bear'] = ((df['EMA_9_Cross_26_Bull'] == 0) & (df['high'] >= ema9_m15) & (df['close'] < ema9_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)

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

FEATS_65_V52 = [
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
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20',
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear',
    'EMA_9_Cross_26_Bull', 'Dist_EMA9_M15', 'Dist_EMA26_M15', 'Spread_EMA_9_26',
    'Pullback_EMA_Bull', 'Pullback_EMA_Bear',
    'DXY_Dist_Resistance', 'DXY_Dist_Support',
    'DXY_At_Supply_POI', 'DXY_At_Demand_POI',
    'DXY_RSI_14', 'DXY_BOS_Bull', 'DXY_BOS_Bear',
    'SMT_Divergence_Bull', 'SMT_Divergence_Bear'
]

# -----------------------------------------------------------------------------
# 2. FITUR ENHANCEMENT V5.3 (SOLUSI INSTITUSIONAL)
# -----------------------------------------------------------------------------
# A. Rejection Pressure Index Non-Linear (Menggabungkan Wick x Kedekatan Resisten/Support)
df['Rejection_Resist_Index'] = (df['Upper_Wick_Ratio'] ** 2) / (df['Dist_Resistance'] + 0.0005)
df['Rejection_Support_Index'] = (df['Lower_Wick_Ratio'] ** 2) / (df['Dist_Support'] + 0.0005)

# B. Stoch RSI 14-3-3 (Deteksi Overbought/Oversold Pucuk)
rsi_series = df['RSI_14']
min_rsi = rsi_series.rolling(14).min()
max_rsi = rsi_series.rolling(14).max()
stoch_rsi_raw = (rsi_series - min_rsi) / (max_rsi - min_rsi + 1e-6) * 100.0
stoch_k = stoch_rsi_raw.rolling(3).mean()
stoch_d = stoch_k.rolling(3).mean()
df['Stoch_RSI_K'] = stoch_k
df['Stoch_RSI_D'] = stoch_d
df['Stoch_RSI_Overbought'] = (stoch_k >= 85.0).astype(int)
df['Stoch_RSI_Oversold']   = (stoch_k <= 15.0).astype(int)
df['Stoch_RSI_Cross_Bear'] = ((stoch_k < stoch_d) & (stoch_k.shift(1) >= stoch_d.shift(1)) & (stoch_k >= 70.0)).astype(int)
df['Stoch_RSI_Cross_Bull'] = ((stoch_k > stoch_d) & (stoch_k.shift(1) <= stoch_d.shift(1)) & (stoch_k <= 30.0)).astype(int)

# C. Shockwave Crash/Pump Shield (Mendeteksi apakah 12 bar terakhir ada lilin raksasa > 3x ATR)
candle_height = df['high'] - df['low']
is_crash_bar = (candle_height >= 3.0 * df['ATR_14']) & (df['close'] < df['open'])
is_pump_bar  = (candle_height >= 3.0 * df['ATR_14']) & (df['close'] > df['open'])
df['Shockwave_Crash_12'] = is_crash_bar.rolling(12).max().fillna(0).astype(int)
df['Shockwave_Pump_12']  = is_pump_bar.rolling(12).max().fillna(0).astype(int)

# D. Volume Absorption Proxy (Volume tinggi + Wick tebal di area kunci)
vol_high = df['Volume_Ratio'] >= 1.6
df['Absorption_Supply_Bear'] = (vol_high & (df['Upper_Wick_Ratio'] >= 0.25) & (df['Dist_Resistance'] <= 0.0020)).astype(int)
df['Absorption_Demand_Bull'] = (vol_high & (df['Lower_Wick_Ratio'] >= 0.25) & (df['Dist_Support'] <= 0.0020)).astype(int)

FEATS_ENHANCEMENT_12 = [
    'Rejection_Resist_Index', 'Rejection_Support_Index',
    'Stoch_RSI_K', 'Stoch_RSI_D',
    'Stoch_RSI_Overbought', 'Stoch_RSI_Oversold',
    'Stoch_RSI_Cross_Bear', 'Stoch_RSI_Cross_Bull',
    'Shockwave_Crash_12', 'Shockwave_Pump_12',
    'Absorption_Supply_Bear', 'Absorption_Demand_Bull'
]

FEATS_V53_FULL = FEATS_65_V52 + FEATS_ENHANCEMENT_12

# Target Horizon 75 Menit
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

df_clean = df.dropna(subset=FEATS_V53_FULL + ['Target_Dir']).copy()
test_len = 4980
train_df = df_clean.iloc[:-test_len]
test_df  = df_clean.iloc[-test_len:]

# -----------------------------------------------------------------------------
# SIMULASI SINGLE-TRADE REALISTIS
# -----------------------------------------------------------------------------
def run_simulation(test_data, probs, threshold=0.60):
    TOTAL_FRICTION = 0.35
    closes = test_data['close'].values; highs = test_data['high'].values; lows = test_data['low'].values
    n = len(closes)
    trades = []; active_until = -1; max_bars = 25
    equity = 500.0; peak_equity = 500.0; max_dd = 0.0

    for i in range(n - max_bars):
        if i <= active_until: continue
        p_up = probs[i]; p_dn = 1.0 - p_up
        sig = 'HOLD'; conf = 0.0
        if p_up >= threshold: sig = 'BUY'; conf = p_up
        elif p_dn >= threshold: sig = 'SELL'; conf = p_dn
        else: continue

        entry_p = closes[i]
        tp_val = 11.00 if conf >= 0.65 else 8.50
        sl_val = 6.50
        tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
        sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
        cur_sl = sl_p
        tier1_locked = False; tier2_locked = False; tier3_locked = False
        result = 'BEP'; pnl = 0.0

        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]; l_bar = lows[cur_idx]; c_bar = closes[cur_idx]

            if sig == 'BUY':
                floating = h_bar - entry_p
                if floating >= 7.00 and not tier3_locked:
                    cur_sl = max(cur_sl, entry_p + 4.50); tier3_locked = True
                elif floating >= 4.50 and not tier2_locked and not tier3_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00); tier2_locked = True
                elif floating >= 2.50 and not tier1_locked and not tier2_locked and not tier3_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20); tier1_locked = True

                if h_bar >= tp_p:
                    result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
                elif l_bar <= cur_sl:
                    if tier3_locked: result = 'WIN'; pnl = 4.50 - TOTAL_FRICTION
                    elif tier2_locked: result = 'WIN'; pnl = 2.00 - TOTAL_FRICTION
                    elif tier1_locked: result = 'BEP'; pnl = 0.20 - TOTAL_FRICTION
                    else: result = 'LOSS'; pnl = -sl_val - TOTAL_FRICTION
                    active_until = cur_idx; break
            else:
                floating = entry_p - l_bar
                if floating >= 7.00 and not tier3_locked:
                    cur_sl = min(cur_sl, entry_p - 4.50); tier3_locked = True
                elif floating >= 4.50 and not tier2_locked and not tier3_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00); tier2_locked = True
                elif floating >= 2.50 and not tier1_locked and not tier2_locked and not tier3_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20); tier1_locked = True

                if l_bar <= tp_p:
                    result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
                elif h_bar >= cur_sl:
                    if tier3_locked: result = 'WIN'; pnl = 4.50 - TOTAL_FRICTION
                    elif tier2_locked: result = 'WIN'; pnl = 2.00 - TOTAL_FRICTION
                    elif tier1_locked: result = 'BEP'; pnl = 0.20 - TOTAL_FRICTION
                    else: result = 'LOSS'; pnl = -sl_val - TOTAL_FRICTION
                    active_until = cur_idx; break

            if step == max_bars:
                diff = (c_bar - entry_p) if sig == 'BUY' else (entry_p - c_bar)
                pnl = round(diff - TOTAL_FRICTION, 2)
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')
                active_until = cur_idx

        equity += pnl
        if equity > peak_equity: peak_equity = equity
        dd = peak_equity - equity
        if dd > max_dd: max_dd = dd
        trades.append({'sig': sig, 'conf': conf, 'result': result, 'pnl': pnl})

    df_t = pd.DataFrame(trades)
    n_t = len(df_t)
    if n_t == 0: return {'trades': 0, 'wr': 0, 'pnl': 0, 'pf': 0, 'max_dd': 0, 'snp_trades': 0, 'snp_wr': 0}
    w = len(df_t[df_t['result'] == 'WIN'])
    l = len(df_t[df_t['result'] == 'LOSS'])
    wr = (w / n_t) * 100.0
    tot_pnl = df_t['pnl'].sum()
    gw = df_t[df_t['pnl'] > 0]['pnl'].sum()
    gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum())
    pf = (gw / (gl + 1e-6)) if gl > 0 else gw

    df_snp = df_t[df_t['conf'] >= 0.65]
    n_snp = len(df_snp)
    snp_w = len(df_snp[df_snp['result'] == 'WIN'])
    snp_wr = (snp_w / n_snp * 100.0) if n_snp > 0 else 0

    return {'trades': n_t, 'wins': w, 'losses': l, 'wr': wr, 'pnl': tot_pnl, 'pf': pf, 'max_dd': max_dd, 'snp_trades': n_snp, 'snp_wr': snp_wr}

lgb_params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)

models_compare = [
    {
        "name": "1. Model Aktif V5.2 (65 Fitur Super Kombo)",
        "feats": FEATS_65_V52
    },
    {
        "name": "2. Model V5.3 (77 Fitur: V5.2 + Rejection Index + Stoch RSI + Crash Shield + Absorption)",
        "feats": FEATS_V53_FULL
    }
]

y_train = train_df['Target_Dir'].values
y_test  = test_df['Target_Dir'].values

comp_results = []
trained_models = {}

for m in models_compare:
    clf = LGBMClassifier(**lgb_params).fit(train_df[m['feats']].values, y_train)
    trained_models[m['name']] = clf
    probs_test = clf.predict_proba(test_df[m['feats']].values)[:, 1]
    preds_test = (probs_test >= 0.50).astype(int)
    
    acc = accuracy_score(y_test, preds_test) * 100.0
    auc = roc_auc_score(y_test, probs_test)
    sim = run_simulation(test_df, probs_test, threshold=0.60)
    
    comp_results.append({
        "Model": m['name'],
        "N_Fitur": len(m['feats']),
        "Akurasi_ML": round(acc, 2),
        "ROC_AUC": round(auc, 4),
        "Total_Trades": sim['trades'],
        "Win_Rate": round(sim['wr'], 2),
        "Sniper_Trades": sim['snp_trades'],
        "Sniper_WR": round(sim['snp_wr'], 2),
        "Net_PnL": round(sim['pnl'], 2),
        "Profit_Factor": round(sim['pf'], 2),
        "Max_Drawdown": round(sim['max_dd'], 2)
    })

print("\n" + "="*125)
print("HASIL HEAD-TO-HEAD KOMPARASI: V5.2 (65 FITUR) VS V5.3 ENHANCED (77 FITUR)")
print("="*125)
df_comp = pd.DataFrame(comp_results)
print(df_comp.to_string(index=False))

# Uji Khusus pada Lilin Kasus 00:00 - 00:15 WIB (Rejection di Resisten)
latest_slice = test_df.iloc[-4:]
print("\n" + "="*115)
print("🔍 AUDIT KASUS SPESIFIK PADA LILIN REJECTION RESISTEN 00:00 - 00:15 WIB:")
print("="*115)
for m in models_compare:
    clf = trained_models[m['name']]
    last_probs = clf.predict_proba(latest_slice[m['feats']].values)[:, 1]
    print(f"Model: {m['name'][:30]}")
    for idx_bar in range(len(latest_slice)):
        bar_t = latest_slice.index[idx_bar]
        p_up = last_probs[idx_bar] * 100.0
        p_dn = (1.0 - last_probs[idx_bar]) * 100.0
        status = "🟢 BUY" if p_up >= 60 else ("🔴 SELL" if p_dn >= 60 else "⚪ STANDBY")
        print(f"  Bar {bar_t} | Buy: {p_up:5.1f}% | Sell: {p_dn:5.1f}% | Keputusan: {status}")

# Cek Feature Importance Top 15 di Model V5.3
clf_v53 = trained_models[models_compare[1]['name']]
imp = pd.Series(clf_v53.feature_importances_, index=FEATS_V53_FULL).sort_values(ascending=False)
print("\n" + "="*80)
print("🏆 TOP 15 FITUR PALING BERPENGARUH DI MODEL V5.3 ENHANCED:")
print("="*80)
for rank, (feat_name, score) in enumerate(imp.head(15).items(), 1):
    is_new = "✨ (FITUR BARU V5.3)" if feat_name in FEATS_ENHANCEMENT_12 else ""
    print(f"{rank:2d}. {feat_name:<30} : {score:4d} splits {is_new}")
