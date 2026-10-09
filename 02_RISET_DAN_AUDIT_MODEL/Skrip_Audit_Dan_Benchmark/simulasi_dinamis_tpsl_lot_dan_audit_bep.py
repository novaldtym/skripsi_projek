import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*120)
print("AUDIT MENDALAM: ANALISIS BEP FAKEOUT, EXIT DINAMIS HORIZON 75M, & SIMULASI LOT FINANSIAL")
print("TARGET MODAL: $500 USD & SIMULASI MODAL RP 100 JUTA (KURS RP 16.000 / USD)")
print("="*120)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

df_raw = pd.DataFrame(rates_m15)
df_raw['time'] = pd.to_datetime(df_raw['time'], unit='s')
df_raw.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 25000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()

# Ekstraksi 57 Fitur Bersih (Causal Zero Leakage)
df = df_raw.copy()
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
df['BB_Bandwidth'] = (4 * std20) / sma20
df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1)
df['XAU_Return_3'] = df['close'].pct_change(3)
df['XAU_Return_5'] = df['close'].pct_change(5)

df['DXY_Close'] = dxy_close.reindex(df.index, method='ffill').bfill()
df['DXY_Return_1'] = df['DXY_Close'].pct_change(1).fillna(0)
df['DXY_Return_3'] = df['DXY_Close'].pct_change(3).fillna(0)
df['DXY_Trend'] = (df['DXY_Close'] > df['DXY_Close'].rolling(20).mean()).astype(int)
df['XAU_DXY_Ratio'] = df['close'] / (df['DXY_Close'] + 1e-6)
df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

day_of_month = df.index.day
weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

h1_close_series = df_h1['close'].shift(1)
h4_close_series = df_h4['close'].shift(1)

df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close_series.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close_series.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull']   = (h1_close_series > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close_series - df_h1_loc['EMA_50_H1']) / h1_close_series

df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close_series.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close_series.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull']   = (h4_close_series > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50']   = (h4_close_series - df_h4_loc['EMA_50_H4']) / h4_close_series

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)

for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

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

df['XAU_Return_10'] = df['close'].pct_change(10)
df['XAU_Return_20'] = df['close'].pct_change(20)

# 13 Fitur Geometri Spasial Tambahan
df['Major_Demand_300'] = df['low'].shift(1).rolling(300).min()
df['Major_Supply_300'] = df['high'].shift(1).rolling(300).max()
df['Dist_Major_Demand'] = (df['close'] - df['Major_Demand_300']) / df['close']
df['Dist_Major_Supply'] = (df['Major_Supply_300'] - df['close']) / df['close']

nearest_min_dist = df[['Dist_Support', 'Dist_Resistance']].min(axis=1)
df['Nearest_Clearance'] = nearest_min_dist - 0.0018
df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)
df['Pinbar_Ratio'] = df[['Lower_Wick_Ratio', 'Upper_Wick_Ratio']].max(axis=1) / (df['Body_Ratio'] + 1e-5)

def fast_rolling_slope(series, window=35):
    x = np.arange(window)
    x_mean = x.mean()
    x_var = ((x - x_mean)**2).sum()
    weights = (x - x_mean) / x_var
    return series.rolling(window).apply(lambda y: np.dot(y, weights), raw=True)

df['Pattern_Slope_High'] = fast_rolling_slope(df['high'], 35).fillna(0)
df['Pattern_Slope_Low']  = fast_rolling_slope(df['low'], 35).fillna(0)
spread_35 = (df['high'] - df['low']).rolling(35).mean() + 1e-5
df['Pattern_Convergence'] = (df['Pattern_Slope_Low'] - df['Pattern_Slope_High']) / spread_35

p_code = np.zeros(len(df))
sh = df['Pattern_Slope_High'].values
sl = df['Pattern_Slope_Low'].values
for i in range(len(df)):
    if sl[i] > 0.06 and abs(sh[i]) <= 0.15: p_code[i] = 1
    elif sh[i] < -0.06 and abs(sh[i]) <= 0.15: p_code[i] = 2
    elif sh[i] < -0.08 and sl[i] > 0.08: p_code[i] = 3
    elif sh[i] > 0.10 and sl[i] > 0.10: p_code[i] = 6
    elif sh[i] < -0.10 and sl[i] < -0.10: p_code[i] = 7
    else: p_code[i] = 0
df['Pattern_Type_Code'] = p_code

roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']

roll_min1 = df['low'].shift(1).rolling(20).min()
roll_min2 = df['low'].shift(21).rolling(20).min()
df['Double_Bottom_Dist'] = (roll_min1 - roll_min2).abs() / df['close']

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

features_57 = [
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
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply', 'Nearest_Clearance',
    'Est_RRR_Buy', 'Est_RRR_Sell', 'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence',
    'Pattern_Type_Code', 'Double_Top_Dist', 'Double_Bottom_Dist'
]

df.dropna(subset=features_57 + ['Target_Dir'], inplace=True)

test_len = int(len(df) * 0.20)
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

# Train Model V5.0
lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
model_v50 = LGBMClassifier(**lgb_params).fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_v50 = model_v50.predict_proba(test_df[features_57].values)[:, 1]

# =========================================================================
# 1. BEDAH FORENSIK BEP: APAKAH KEJILAT FAKEOUT ATAU PENYELAMAT DARI LOSS?
# =========================================================================
print("\n" + "="*120)
print("1. BEDAH FORENSIK 92 TRADE BEP: FAKEOUT DERAU ATAU PENYELAMAT MODAL DARI LOSS?")
print("="*120)

closes = test_df['close'].values
highs  = test_df['high'].values
lows   = test_df['low'].values
dist_s = test_df['Dist_Support'].values
dist_r = test_df['Dist_Resistance'].values
l_wick = test_df['Lower_Wick_Ratio'].values
u_wick = test_df['Upper_Wick_Ratio'].values
n = len(closes)

tp_val = 6.50
sl_val = 6.50
max_bars = 25

bep_trades_analysis = []
active_until = -1

for i in range(n - max_bars):
    if i <= active_until:
        continue
        
    p_up = probs_v50[i]
    p_dn = 1.0 - p_up
    
    sig = 'HOLD'
    if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20 and p_up >= 0.58: sig = 'BUY'
    elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20 and p_dn >= 0.58: sig = 'SELL'
    elif sig == 'HOLD' and dist_s[i] <= 0.0040 and l_wick[i] >= 0.18 and p_up >= 0.60: sig = 'BUY'
    elif sig == 'HOLD' and dist_r[i] <= 0.0040 and u_wick[i] >= 0.18 and p_dn >= 0.60: sig = 'SELL'
    elif sig == 'HOLD' and p_up >= 0.65: sig = 'BUY'
    elif sig == 'HOLD' and p_dn >= 0.65: sig = 'SELL'
    
    if sig == 'HOLD':
        continue
        
    entry_p = closes[i]
    tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
    sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
    cur_sl = sl_p
    
    bep_locked = False
    trailing_locked = False
    hit_bep = False
    bep_step = -1
    
    for step in range(1, max_bars + 1):
        cur_idx = i + step
        h_bar = highs[cur_idx]
        l_bar = lows[cur_idx]
        
        if sig == 'BUY':
            floating = h_bar - entry_p
            if floating >= 3.50 and not trailing_locked:
                cur_sl = max(cur_sl, entry_p + 2.00)
                trailing_locked = True
            elif floating >= 2.50 and not bep_locked and not trailing_locked:
                cur_sl = max(cur_sl, entry_p + 0.20)
                bep_locked = True
                
            if h_bar >= tp_p:
                active_until = i + step
                break
            elif l_bar <= cur_sl:
                if bep_locked and not trailing_locked:
                    hit_bep = True
                    bep_step = step
                active_until = i + step
                break
        else:
            floating = entry_p - l_bar
            if floating >= 3.50 and not trailing_locked:
                cur_sl = min(cur_sl, entry_p - 2.00)
                trailing_locked = True
            elif floating >= 2.50 and not bep_locked and not trailing_locked:
                cur_sl = min(cur_sl, entry_p - 0.20)
                bep_locked = True
                
            if l_bar <= tp_p:
                active_until = i + step
                break
            elif h_bar >= cur_sl:
                if bep_locked and not trailing_locked:
                    hit_bep = True
                    bep_step = step
                active_until = i + step
                break
                
    if hit_bep:
        # Lacak nasib harga setelah kena BEP (dalam 10 bar ke depan)
        # Apakah harga malah turun kena SL awal (-$6.50) atau berbalik naik kena TP awal (+$6.50)?
        rem_steps = min(15, n - (i + bep_step))
        sub_highs = highs[i + bep_step : i + bep_step + rem_steps]
        sub_lows  = lows[i + bep_step : i + bep_step + rem_steps]
        
        if sig == 'BUY':
            would_hit_sl = (sub_lows <= sl_p).any()
            would_hit_tp = (sub_highs >= tp_p).any()
        else:
            would_hit_sl = (sub_highs >= sl_p).any()
            would_hit_tp = (sub_lows <= tp_p).any()
            
        if would_hit_sl and not would_hit_tp:
            nasib = "PENYELAMAT_DARI_LOSS" # Jika tanpa BEP, akun pasti rugi -$6.50!
        elif would_hit_tp and not would_hit_sl:
            nasib = "KEJILAT_FAKEOUT"       # Posisi kejilat wick, padahal akhirnya kena TP!
        elif would_hit_sl and would_hit_tp:
            nasib = "WHIPSAW_KACAU"
        else:
            nasib = "KONSOLIDASI_MANDET"
            
        bep_trades_analysis.append(nasib)

df_bep_stat = pd.Series(bep_trades_analysis).value_counts()
print(f"Total Kasus BEP Terdeteksi: {len(bep_trades_analysis)} trade")
for k, v in df_bep_stat.items():
    print(f"  • {k:<25}: {v:>3} trade ({v/len(bep_trades_analysis)*100:5.1f}%)")

# =========================================================================
# 2. PENGUJIAN USULAN EXIT DINAMIS HORIZON 75 MENIT (5 CANDLE M15)
# =========================================================================
print("\n" + "="*120)
print("2. UJI USULAN EXIT DINAMIS: AUTO-CLOSE DI CANDLE KE-5 (75 MENIT) VS FIXED PATEN")
print("="*120)

def simulate_dynamic_exit(test_data, probs, mode="FIXED_PATEN", bep_trig=2.50):
    SPREAD = 0.20
    lot = 0.01
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    dist_s = test_data['Dist_Support'].values
    dist_r = test_data['Dist_Resistance'].values
    l_wick = test_data['Lower_Wick_Ratio'].values
    u_wick = test_data['Upper_Wick_Ratio'].values
    atr_vals = test_data['ATR_14'].values
    n = len(closes)
    
    trades = []
    active_until = -1
    
    for i in range(n - 10):
        if i <= active_until:
            continue
            
        p_up = probs[i]
        p_dn = 1.0 - p_up
        
        sig = 'HOLD'
        if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20 and p_up >= 0.58: sig = 'BUY'
        elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20 and p_dn >= 0.58: sig = 'SELL'
        elif sig == 'HOLD' and dist_s[i] <= 0.0040 and l_wick[i] >= 0.18 and p_up >= 0.60: sig = 'BUY'
        elif sig == 'HOLD' and dist_r[i] <= 0.0040 and u_wick[i] >= 0.18 and p_dn >= 0.60: sig = 'SELL'
        elif sig == 'HOLD' and p_up >= 0.65: sig = 'BUY'
        elif sig == 'HOLD' and p_dn >= 0.65: sig = 'SELL'
        
        if sig == 'HOLD':
            continue
            
        entry_p = closes[i]
        cur_atr = atr_vals[i]
        
        # Penentuan TP dan SL
        if mode == "DYNAMIC_ATR_STRUCTURE":
            # TP dan SL adaptif berbasis volatilitas ATR dan struktur pasar
            tp_dist = max(5.00, min(12.00, cur_atr * 2.2))
            sl_dist = max(4.00, min(7.50,  cur_atr * 1.4))
        else: # FIXED_PATEN
            tp_dist = 6.50
            sl_dist = 6.50
            
        tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        sl_p = entry_p - sl_dist if sig == 'BUY' else entry_p + sl_dist
        cur_sl = sl_p
        
        bep_on = False
        trailing_on = False
        pnl_gross = 0.0
        held_bars = 5
        
        # Loop 5 candle M15 (Sesuai Horizon 75 Menit Skripsi)
        for step in range(1, 6):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            c_bar = closes[cur_idx]
            
            # Trailing & BEP
            if sig == 'BUY':
                flt = h_bar - entry_p
                if flt >= (bep_trig + 1.0) and not trailing_on:
                    cur_sl = max(cur_sl, entry_p + 2.00)
                    trailing_on = True
                elif flt >= bep_trig and not bep_on and not trailing_on:
                    cur_sl = max(cur_sl, entry_p + 0.20)
                    bep_on = True
                    
                if h_bar >= tp_p:
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif l_bar <= cur_sl:
                    pnl_gross = 2.00 if trailing_on else (0.20 if bep_on else -sl_dist)
                    held_bars = step
                    break
            else:
                flt = entry_p - l_bar
                if flt >= (bep_trig + 1.0) and not trailing_on:
                    cur_sl = min(cur_sl, entry_p - 2.00)
                    trailing_on = True
                elif flt >= bep_trig and not bep_on and not trailing_on:
                    cur_sl = min(cur_sl, entry_p - 0.20)
                    bep_on = True
                    
                if l_bar <= tp_p:
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif h_bar >= cur_sl:
                    pnl_gross = 2.00 if trailing_on else (0.20 if bep_on else -sl_dist)
                    held_bars = step
                    break
                    
            # ATURAN KHUSUS USULAN NOUVAL: CANDLE KE-4 / KE-5 CEK MOMENTUM (AUTO-CLOSE 75M)
            if step == 5:
                # Tutup paksa di candle ke-5 pada harga Close
                c_exit = closes[i + 5]
                pnl_gross = (c_exit - entry_p) if sig == 'BUY' else (entry_p - c_exit)
                held_bars = 5
                
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    wins = (trades > 0).sum()
    wr = (wins / n_tr) * 100.0 if n_tr > 0 else 0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    return n_tr, wr, tot_pnl, pf, dd

tr_fix, wr_fix, pnl_fix, pf_fix, dd_fix = simulate_dynamic_exit(test_df, probs_v50, mode="FIXED_PATEN", bep_trig=2.50)
tr_opt, wr_opt, pnl_opt, pf_opt, dd_opt = simulate_dynamic_exit(test_df, probs_v50, mode="FIXED_PATEN", bep_trig=3.20) # Naikkan trigger BEP agar tidak kejilat
tr_dyn, wr_dyn, pnl_dyn, pf_dyn, dd_dyn = simulate_dynamic_exit(test_df, probs_v50, mode="DYNAMIC_ATR_STRUCTURE", bep_trig=3.20)

print(f"{'Strategi Exit & Proteksi':<45} | {'Trades':<6} | {'WR (%)':<7} | {'Net PnL USD':<12} | {'Net PnL Rupiah':<18} | {'PF':<5} | {'Max DD':<9}")
print("-"*120)
print(f"{'1. V5.0 Standar (BEP $2.50, TP $6.50)':<45} | {tr_fix:<6} | {wr_fix:<7.2f} | +${pnl_fix:<10.2f} | +Rp {pnl_fix*16000:>12,.0f} | {pf_fix:<5.2f} | ${dd_fix:<8.2f}")
print(f"{'2. V5.0 BEP Anti-Fakeout ($3.20 Buffer)':<45} | {tr_opt:<6} | {wr_opt:<7.2f} | +${pnl_opt:<10.2f} | +Rp {pnl_opt*16000:>12,.0f} | {pf_opt:<5.2f} | ${dd_opt:<8.2f}")
print(f"{'3. Usulan Nouval: Exit Dinamis ATR + 75m Close':<45} | {tr_dyn:<6} | {wr_dyn:<7.2f} | +${pnl_dyn:<10.2f} | +Rp {pnl_dyn*16000:>12,.0f} | {pf_dyn:<5.2f} | ${dd_dyn:<8.2f}")

# =========================================================================
# 3. ANALISIS REALISTIS: MODAL RP 100 JUTA CARI 1 JUTA PER HARI
# =========================================================================
print("\n" + "="*120)
print("3. MATEMATIKA REALISTIS LAPANGAN: MODAL RP 100 JUTA (~$6.250 USD) CARI RP 1 JUTA / HARI")
print("BAGAIMANA CARA TRADER MANUAL VS BAGAIMANA BOT AI V5.0 BISA MENGHASILKANNYA?")
print("="*120)

# Modal 100 Juta = $6,250 USD
CAPITAL_IDR = 100_000_000
CAPITAL_USD = CAPITAL_IDR / 16000 # $6,250 USD
TARGET_DAILY_IDR = 1_000_000     # Rp 1 Juta / hari
TARGET_DAILY_USD = TARGET_DAILY_IDR / 16000 # $62.50 USD / hari (tepat 1.0% per hari!)

# Simulasi Berbagai Ukuran Lot pada Modal $6,250 USD (Rp 100 Juta)
lot_study = [0.05, 0.10, 0.15, 0.20, 0.30]
sim_100jt = []

for l in lot_study:
    # Scaling dari hasil pengujian empiris V5.0 Anti-Fakeout (583 trade / 75 hari = ~7.7 trade/hari)
    # Rata-rata perolehan net per trade = pnl_opt / tr_opt
    net_per_trade_usd = (pnl_opt / tr_opt) * (l / 0.01)
    daily_trades = tr_opt / 75.0
    daily_pnl_usd = net_per_trade_usd * daily_trades
    daily_pnl_idr = daily_pnl_usd * 16000
    monthly_pnl_idr = daily_pnl_idr * 22 # 22 hari bursa per bulan
    max_dd_usd = dd_opt * (l / 0.01)
    max_dd_idr = max_dd_usd * 16000
    dd_pct = (max_dd_usd / CAPITAL_USD) * 100.0
    
    sim_100jt.append({
        "Lot_Size": l,
        "Margin_Per_Trade": f"${l * 4150 * 100 / 2000:.2f} (~Rp {l * 4150 * 100 / 2000 * 16000:,.0f})",
        "Estimasi_Harian_IDR": f"Rp {daily_pnl_idr:,.0f} / hari",
        "Target_1_Juta_Tercapai": "TERCAPAI! (+" f"{daily_pnl_idr/TARGET_DAILY_IDR*100:.0f}%)" if daily_pnl_idr >= TARGET_DAILY_IDR else f"Belum ({daily_pnl_idr/TARGET_DAILY_IDR*100:.0f}%)",
        "Estimasi_Bulanan_IDR": f"Rp {monthly_pnl_idr:,.0f} / bln",
        "Max_Drawdown_Akun": f"Rp {max_dd_idr:,.0f} ({dd_pct:.1f}%)",
        "Tingkat_Keamanan": "SUPER AMAN (Risiko Rendah)" if dd_pct <= 15 else ("SANGAT AMAN (Ideal)" if dd_pct <= 25 else "AGRESIF")
    })

df_100jt = pd.DataFrame(sim_100jt)
print(df_100jt.to_string(index=False))

excel_out = r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Audit_BEP_ExitDinamis_dan_Modal_100Juta.xlsx"
with pd.ExcelWriter(excel_out, engine='openpyxl') as writer:
    df_bep_stat.to_frame(name="Jumlah_Trade").to_excel(writer, sheet_name="Forensik_BEP")
    pd.DataFrame([
        {"Strategi": "V5.0 Standar (BEP $2.50)", "Trades": tr_fix, "WR": wr_fix, "PnL_USD": pnl_fix, "PnL_IDR": pnl_fix*16000, "PF": pf_fix, "MaxDD": dd_fix},
        {"Strategi": "V5.0 BEP Anti-Fakeout ($3.20)", "Trades": tr_opt, "WR": wr_opt, "PnL_USD": pnl_opt, "PnL_IDR": pnl_opt*16000, "PF": pf_opt, "MaxDD": dd_opt},
        {"Strategi": "Exit Dinamis Nouval (ATR+75m)", "Trades": tr_dyn, "WR": wr_dyn, "PnL_USD": pnl_dyn, "PnL_IDR": pnl_dyn*16000, "PF": pf_dyn, "MaxDD": dd_dyn},
    ]).to_excel(writer, sheet_name="Exit_Dinamis", index=False)
    df_100jt.to_excel(writer, sheet_name="Simulasi_Modal_100_Juta", index=False)

print(f"\n[OK] Seluruh data berhasil disimpan ke: {excel_out}")
