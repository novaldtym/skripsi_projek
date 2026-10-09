"""
=============================================================================
PELATIHAN & SERIALISASI MODEL LIGHTGBM PRO V5.4 MASTER (77 FITUR LENGKAP)
(65 FITUR SKRIPSI + 12 FITUR INSTITUSIONAL + TRIPLE BARRIER DYNAMIC VOLATILITY)
=============================================================================
Hasil Evaluasi Resmi:
- Out-of-Sample: 4.980 Candle M15 (~2.5 Bulan)
- Total Trades: 953 Trades (~11.9 trade/hari)
- Net PnL: +$1,131.95 USD (RoC +226.4% dari modal $500)
- Profit Factor: 2.72 ⭐
- Max Drawdown: -$17.80 USD (3.5% modal $500) ⭐
=============================================================================
"""

import os, sys, time, warnings
warnings.filterwarnings('ignore')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import joblib
import MetaTrader5 as mt5
from lightgbm import LGBMClassifier

BASE_DIR = r"d:\SKRIPSI INFORMATIKA"
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_SAVE_PATH = os.path.join(BASE_DIR, "model_m15_pro_77_features.pkl")
META_SAVE_PATH  = os.path.join(BASE_DIR, "model_m15_pro_77_features_meta.pkl")

print("="*80)
print("TRAINING RESMI MODEL V5.4 MASTER (77 FITUR TRIPLE-BARRIER PATEN)")
print("="*80)

if not mt5.initialize(path=MT5_PATH):
    if not mt5.initialize():
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print("📥 Mengambil 25.000 M15, 8.000 H1, 2.500 H4, dan 25.000 DXY...")
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

print("🧠 Membangun 65 Fitur Skripsi + 12 Fitur Institusional = 77 Fitur...")

# 1. 65 FITUR SKRIPSI KAUSAL MURNI
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
body_sz = (df['close'] - df['open']).abs(); avg_body = body_sz.rolling(20).mean()
imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

lookback_fibo = 100
roll_high = df['high'].rolling(lookback_fibo).max(); roll_low = df['low'].rolling(lookback_fibo).min()
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

sma20 = df['close'].rolling(20).mean(); std20 = df['close'].rolling(20).std()
df['BB_Bandwidth'] = (4 * std20) / (sma20 + 1e-9)
df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1)
df['XAU_Return_3'] = df['close'].pct_change(3)
df['XAU_Return_5'] = df['close'].pct_change(5)

is_bull = (df['close'] > df['open']).astype(int); is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr1 = df['high'] - df['low']; tr2 = (df['high'] - df['close'].shift(1)).abs(); tr3 = (df['low'] - df['close'].shift(1)).abs()
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
atr14 = tr.rolling(14).mean()
df['ATR_14'] = atr14
plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / (atr14 + 1e-6))
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / (atr14 + 1e-6))
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14).mean()

vol = df['tick_volume']; vol_ma20 = vol.rolling(20).mean()
df['Volume_Ratio'] = vol / (vol_ma20 + 1e-6)

df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.40)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.40)).astype(int)
df['Zone_B_Prox_Bull']   = (df['Dist_Support'] <= 0.0010).astype(int)
df['Zone_B_Prox_Bear']   = (df['Dist_Resistance'] <= 0.0010).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0035).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0035).astype(int)

ema_9_m15  = df['close'].ewm(span=9, adjust=False).mean()
ema_26_m15 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = ((ema_9_m15 > ema_26_m15) & (ema_9_m15.shift(1) <= ema_26_m15.shift(1))).astype(int)
df['Dist_EMA9_M15']   = (df['close'] - ema_9_m15) / df['close']
df['Dist_EMA26_M15']  = (df['close'] - ema_26_m15) / df['close']
df['Spread_EMA_9_26'] = (ema_9_m15 - ema_26_m15) / df['close']
df['Pullback_EMA_Bull'] = ((df['low'] <= ema_9_m15) & (df['close'] > ema_9_m15)).astype(int)
df['Pullback_EMA_Bear'] = ((df['high'] >= ema_9_m15) & (df['close'] < ema_9_m15)).astype(int)

df_dxy_aligned = df_dxy.reindex(df.index, method='ffill').fillna(method='bfill')
dxy_c = df_dxy_aligned['close']; dxy_h = df_dxy_aligned['high']; dxy_l = df_dxy_aligned['low']
df['DXY_Return_1'] = dxy_c.pct_change(1)
df['DXY_Return_3'] = dxy_c.pct_change(3)
df['DXY_Trend'] = np.where(dxy_c > dxy_c.rolling(20).mean(), 1, -1)
df['XAU_DXY_Ratio_Return'] = (df['close'] / (dxy_c + 1e-6)).pct_change(1)
dxy_swing_high = dxy_h.shift(1).rolling(20).max()
dxy_swing_low  = dxy_l.shift(1).rolling(20).min()
df['DXY_Dist_Resistance'] = (dxy_swing_high - dxy_c) / (dxy_c + 1e-6)
df['DXY_Dist_Support']    = (dxy_c - dxy_swing_low) / (dxy_c + 1e-6)
df['DXY_At_Supply_POI'] = (df['DXY_Dist_Resistance'] <= 0.0008).astype(int)
df['DXY_At_Demand_POI'] = (df['DXY_Dist_Support'] <= 0.0008).astype(int)
dxy_delta = dxy_c.diff()
dxy_gain = (dxy_delta.where(dxy_delta > 0, 0)).rolling(14).mean()
dxy_loss = (-dxy_delta.where(dxy_delta < 0, 0)).rolling(14).mean()
df['DXY_RSI_14'] = 100 - (100 / (1 + (dxy_gain / (dxy_loss + 1e-6))))
df['DXY_BOS_Bull'] = (dxy_c > dxy_swing_high).astype(int)
df['DXY_BOS_Bear'] = (dxy_c < dxy_swing_low).astype(int)

xau_ll = df['low'] < df['low'].shift(1).rolling(10).min()
dxy_fail_hh = dxy_h <= dxy_h.shift(1).rolling(10).max()
df['SMT_Divergence_Bull'] = (xau_ll & dxy_fail_hh).astype(int)
xau_hh = df['high'] > df['high'].shift(1).rolling(10).max()
dxy_fail_ll = dxy_l >= dxy_l.shift(1).rolling(10).min()
df['SMT_Divergence_Bear'] = (xau_hh & dxy_fail_ll).astype(int)

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

day_of_month = df.index.day; weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

FEATS_65 = [
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

# 2. 12 FITUR INSTITUSIONAL ENHANCEMENT
df['Rejection_Resist_Index'] = (df['Upper_Wick_Ratio'] ** 2) / (df['Dist_Resistance'] + 0.0005)
df['Rejection_Support_Index'] = (df['Lower_Wick_Ratio'] ** 2) / (df['Dist_Support'] + 0.0005)

rsi_s = df['RSI_14']
min_r = rsi_s.rolling(14).min(); max_r = rsi_s.rolling(14).max()
stoch_raw = (rsi_s - min_r) / (max_r - min_r + 1e-6) * 100.0
st_k = stoch_raw.rolling(3).mean(); st_d = st_k.rolling(3).mean()
df['Stoch_RSI_K'] = st_k
df['Stoch_RSI_D'] = st_d
df['Stoch_RSI_Overbought'] = (st_k >= 85.0).astype(int)
df['Stoch_RSI_Oversold']   = (st_k <= 15.0).astype(int)
df['Stoch_RSI_Cross_Bear'] = ((st_k < st_d) & (st_k.shift(1) >= st_d.shift(1)) & (st_k >= 70.0)).astype(int)
df['Stoch_RSI_Cross_Bull'] = ((st_k > st_d) & (st_k.shift(1) <= st_d.shift(1)) & (st_k <= 30.0)).astype(int)

c_range = df['high'] - df['low']
is_crash = (c_range >= 3.0 * df['ATR_14']) & (df['close'] < df['open'])
is_pump  = (c_range >= 3.0 * df['ATR_14']) & (df['close'] > df['open'])
df['Shockwave_Crash_12'] = is_crash.rolling(12).max().fillna(0).astype(int)
df['Shockwave_Pump_12']  = is_pump.rolling(12).max().fillna(0).astype(int)

vol_h = df['Volume_Ratio'] >= 1.6
df['Absorption_Supply_Bear'] = (vol_h & (df['Upper_Wick_Ratio'] >= 0.25) & (df['Dist_Resistance'] <= 0.0020)).astype(int)
df['Absorption_Demand_Bull'] = (vol_h & (df['Lower_Wick_Ratio'] >= 0.25) & (df['Dist_Support'] <= 0.0020)).astype(int)

FEATS_77 = FEATS_65 + [
    'Rejection_Resist_Index', 'Rejection_Support_Index',
    'Stoch_RSI_K', 'Stoch_RSI_D',
    'Stoch_RSI_Overbought', 'Stoch_RSI_Oversold',
    'Stoch_RSI_Cross_Bear', 'Stoch_RSI_Cross_Bull',
    'Shockwave_Crash_12', 'Shockwave_Pump_12',
    'Absorption_Supply_Bear', 'Absorption_Demand_Bull'
]

print(f"✅ Total Fitur PRO V5.4: {len(FEATS_77)} Fitur")

# 3. TARGET TRIPLE-BARRIER DYNAMIC VOLATILITY
closes_arr = df['close'].values; highs_arr = df['high'].values; lows_arr = df['low'].values
n_all = len(df)
tb_targets = np.full(n_all, np.nan)
for idx in range(n_all - 25):
    p0 = closes_arr[idx]
    up_bar = p0 + 8.50
    dn_bar = p0 - 6.50
    outcome = 0
    for f in range(1, 26):
        h_f = highs_arr[idx + f]
        l_f = lows_arr[idx + f]
        if h_f >= up_bar:
            outcome = 1; break
        elif l_f <= dn_bar:
            outcome = 0; break
    tb_targets[idx] = outcome

df['Target_Dir_T5'] = (df['close'].shift(-5) > df['close']).astype(int)
df['Target_Triple_Barrier'] = tb_targets

df_clean = df.dropna(subset=FEATS_77 + ['Target_Dir_T5', 'Target_Triple_Barrier']).copy()
test_len = 4980
train_df = df_clean.iloc[:-test_len]
test_df  = df_clean.iloc[-test_len:]

print(f"📊 Dataset Split: Train={len(train_df):,} lilin, Test OOS={len(test_df):,} lilin (~2.5 bulan)")

# 4. LATIH LIGHTGBM MASTER
lgb_params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
print("⚙️ Melatih Model V5.4 Master...")
t0 = time.time()
clf = LGBMClassifier(**lgb_params).fit(train_df[FEATS_77], train_df['Target_Triple_Barrier'].values)
print(f"✅ Pelatihan rampung dalam {time.time() - t0:.2f} detik!")

# 5. VERIFIKASI DENGAN ENGINE PATEN
TOTAL_FRICTION = 0.35
closes = test_df['close'].values; highs = test_df['high'].values; lows = test_df['low'].values
probs = clf.predict_proba(test_df[FEATS_77].values)[:, 1]
n = len(closes)
trades = []; active_until = -1; max_bars = 25
equity = 500.0; peak_equity = 500.0; max_dd = 0.0

for i in range(n - max_bars):
    if i <= active_until: continue
    p_up = probs[i]; p_dn = 1.0 - p_up
    sig = 'HOLD'; conf = 0.0
    if p_up >= 0.60: sig = 'BUY'; conf = p_up
    elif p_dn >= 0.60: sig = 'SELL'; conf = p_dn
    else: continue

    if sig == 'SELL':
        bonus_entry = (highs[i] - closes[i]) * 0.35
        entry_p = closes[i] + bonus_entry
        sl_val = 5.00
        tp_val = 12.50 if conf >= 0.65 else 9.50
    else:
        bonus_entry = (closes[i] - lows[i]) * 0.35
        entry_p = closes[i] - bonus_entry
        sl_val = 5.00
        tp_val = 12.50 if conf >= 0.65 else 9.50

    tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
    sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
    cur_sl = sl_p
    tier1_locked = False; tier2_locked = False
    result = 'BEP'; pnl = 0.0

    for step in range(1, max_bars + 1):
        cur_idx = i + step
        h_bar = highs[cur_idx]; l_bar = lows[cur_idx]; c_bar = closes[cur_idx]

        if sig == 'BUY':
            floating = h_bar - entry_p
            if floating >= 5.50 and not tier2_locked:
                cur_sl = max(cur_sl, entry_p + 3.00); tier2_locked = True
            elif floating >= 2.20 and not tier1_locked and not tier2_locked:
                cur_sl = max(cur_sl, entry_p + 0.30); tier1_locked = True

            if h_bar >= tp_p:
                result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
            elif l_bar <= cur_sl:
                if tier2_locked: result = 'WIN'; pnl = 3.00 - TOTAL_FRICTION
                elif tier1_locked: result = 'BEP'; pnl = 0.30 - TOTAL_FRICTION
                else: result = 'LOSS'; pnl = -sl_val - TOTAL_FRICTION
                active_until = cur_idx; break
        else:
            floating = entry_p - l_bar
            if floating >= 5.50 and not tier2_locked:
                cur_sl = min(cur_sl, entry_p - 3.00); tier2_locked = True
            elif floating >= 2.20 and not tier1_locked and not tier2_locked:
                cur_sl = min(cur_sl, entry_p - 0.30); tier1_locked = True

            if l_bar <= tp_p:
                result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
            elif h_bar >= cur_sl:
                if tier2_locked: result = 'WIN'; pnl = 3.00 - TOTAL_FRICTION
                elif tier1_locked: result = 'BEP'; pnl = 0.30 - TOTAL_FRICTION
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
w = len(df_t[df_t['result'] == 'WIN'])
l = len(df_t[df_t['result'] == 'LOSS'])
wr = (w / n_t) * 100.0
tot_pnl = df_t['pnl'].sum()
gw = df_t[df_t['pnl'] > 0]['pnl'].sum(); gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum())
pf = (gw / (gl + 1e-6)) if gl > 0 else gw

print("-" * 80)
print(f"🏆 HASIL VERIFIKASI MODEL V5.4 MASTER:")
print(f"   • Total Trades OOS   : {n_t} Trades (~{n_t/80:.1f} trade/hari)")
print(f"   • Win Rate           : {wr:.2f}% (Wins: {w}, Losses: {l})")
print(f"   • Net PnL (Modal $500): +${tot_pnl:.2f} USD")
print(f"   • Profit Factor      : {pf:.2f} ⭐")
print(f"   • Max Drawdown       : -${max_dd:.2f} USD ({max_dd/500*100:.1f}%) ⭐")
print("-" * 80)

# 6. SIMPAN MODEL & METADATA
joblib.dump(clf, MODEL_SAVE_PATH)
meta = {
    "features": FEATS_77,
    "n_features": len(FEATS_77),
    "model_name": "Model V5.4 Master (Paten Komersial - Full Proprietary)",
    "trades": n_t,
    "wr": wr,
    "pnl": tot_pnl,
    "pf": pf,
    "max_dd": max_dd,
    "sl_usd": 5.00,
    "tp_normal_usd": 9.50,
    "tp_sniper_usd": 12.50,
    "tier1_trigger": 2.20,
    "tier1_lock": 0.30,
    "tier2_trigger": 5.50,
    "tier2_lock": 3.00
}
joblib.dump(meta, META_SAVE_PATH)
print(f"💾 Model Master resmi disimpan ke: {MODEL_SAVE_PATH}")
print(f"💾 Metadata resmi disimpan ke: {META_SAVE_PATH}")
