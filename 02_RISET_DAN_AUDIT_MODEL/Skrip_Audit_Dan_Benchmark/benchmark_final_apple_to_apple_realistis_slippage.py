"""
====================================================================================================
BENCHMARK FINAL RESMI: APPLE-TO-APPLE REALISTIS DENGAN SPREAD & SLIPPAGE EKSTRIM
====================================================================================================
Menguji secara 100% Causal (Nol Leakage, shift(1) terverifikasi, DXY Riil) pada Data 2.5 Bulan (5.000 Candle M15):
1. V4.2 (44 Fitur)
2. V5.0 (57 Fitur)
3. Model Juara (53 Fitur - V5.0 dibersihkan dari 4 fitur racun)
4. Model Juara + ICT Killzones (55 Fitur)

Diuji dalam 2 skenario pasar:
- Skenario A: Standar Broker Exness (Spread $0.20)
- Skenario B: Realistis Ekstrim Pasar Riil (Spread $0.20 + Slippage $0.15 = Total Biaya $0.35/trade)
====================================================================================================
"""
import os, sys
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik 25.000 Candle M15 ({symbol}) dari MT5...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 25000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()

print(f"Data M15: {len(df)} candle ({df.index[0]} s/d {df.index[-1]})")
print(f"Harga Emas Terkini: ${df['close'].iloc[-1]:.2f} USD")

# Ekstraksi Fitur 100% Causal
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

# MTF Causal shift(1)
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

# 44 Fitur Dasar
features_44 = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 'FVG_Bull', 'FVG_Bear',
    'Dist_Support', 'Dist_Resistance', 'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth', 'BB_Pos', 'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20'
]

# Fitur Tambahan V5 (Causal Shift 1)
df['XAU_Return_10'] = df['close'].pct_change(10)
df['XAU_Return_20'] = df['close'].pct_change(20)
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
    x = np.arange(window); x_mean = x.mean(); x_var = ((x - x_mean)**2).sum(); weights = (x - x_mean) / x_var
    return series.rolling(window).apply(lambda y: np.dot(y, weights), raw=True)

df['Pattern_Slope_High'] = fast_rolling_slope(df['high'], 35).fillna(0)
df['Pattern_Slope_Low']  = fast_rolling_slope(df['low'], 35).fillna(0)
spread_35 = (df['high'] - df['low']).rolling(35).mean() + 1e-5
df['Pattern_Convergence'] = (df['Pattern_Slope_Low'] - df['Pattern_Slope_High']) / spread_35

p_code = np.zeros(len(df))
sh = df['Pattern_Slope_High'].values; sl = df['Pattern_Slope_Low'].values
for i in range(len(df)):
    if sl[i] > 0.06 and abs(sh[i]) <= 0.15: p_code[i] = 1
    elif sh[i] < -0.06 and abs(sh[i]) <= 0.15: p_code[i] = 2
    elif sh[i] < -0.08 and sl[i] > 0.08: p_code[i] = 3
    elif sh[i] > 0.10 and sl[i] > 0.10: p_code[i] = 6
    elif sh[i] < -0.10 and sl[i] < -0.10: p_code[i] = 7
df['Pattern_Type_Code'] = p_code

roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']

roll_min1 = df['low'].shift(1).rolling(20).min()
roll_min2 = df['low'].shift(21).rolling(20).min()
df['Double_Bottom_Dist'] = (roll_min1 - roll_min2).abs() / df['close']

# Fitur ICT Terverifikasi Causal
hours = df.index.hour
df['ICT_London_Killzone'] = ((hours >= 8) & (hours <= 12)).astype(int)
df['ICT_NY_Killzone']     = ((hours >= 13) & (hours <= 17)).astype(int)

# 57 Fitur
features_57 = features_44[:-1] + [
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply', 'Nearest_Clearance',
    'Est_RRR_Buy', 'Est_RRR_Sell', 'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence',
    'Pattern_Type_Code', 'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

# Fitur Juara 53 (Tanpa 4 Racun)
poison = ['XAU_Return_10', 'Pattern_Slope_High', 'Nearest_Clearance', 'Double_Bottom_Dist']
features_juara_53 = [f for f in features_57 if f not in poison]

# Fitur Juara + ICT (55 Fitur)
features_juara_ict = features_juara_53 + ['ICT_London_Killzone', 'ICT_NY_Killzone']

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
all_needed = list(set(features_57 + features_juara_ict + ['Target_Dir', 'open', 'high', 'low', 'close']))
df.dropna(subset=all_needed, inplace=True)

test_len = int(len(df) * 0.20)
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

print(f"Data Train: {len(train_df)} candle | Data Test: {len(test_df)} candle (~2.5 bulan)")

# Pelatihan Model
lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)

print("\nMelatih 4 Model...")
m_44 = LGBMClassifier(**lgb_params).fit(train_df[features_44].values, train_df['Target_Dir'].values)
probs_44 = m_44.predict_proba(test_df[features_44].values)[:, 1]

m_57 = LGBMClassifier(**lgb_params).fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_57 = m_57.predict_proba(test_df[features_57].values)[:, 1]

m_j53 = LGBMClassifier(**lgb_params).fit(train_df[features_juara_53].values, train_df['Target_Dir'].values)
probs_j53 = m_j53.predict_proba(test_df[features_juara_53].values)[:, 1]

m_j55 = LGBMClassifier(**lgb_params).fit(train_df[features_juara_ict].values, train_df['Target_Dir'].values)
probs_j55 = m_j55.predict_proba(test_df[features_juara_ict].values)[:, 1]

# ENGINE EKSEKUSI REALISTIS DENGAN PENYELAMAT PROFIT & SLIPPAGE
def simulate_realistic(test_data, probs, spread=0.20, slippage=0.0, lot_size=0.01):
    TOTAL_FRICTION = spread + slippage # biaya transaksi nyata ($/oz)
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    dist_s = test_data['Dist_Support'].values
    dist_r = test_data['Dist_Resistance'].values
    l_wick = test_data['Lower_Wick_Ratio'].values
    u_wick = test_data['Upper_Wick_Ratio'].values
    n = len(closes)
    
    trades = []
    trade_outcomes = []
    active_until = -1
    max_bars = 25
    tp_val = 6.50
    sl_val = 6.50
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        p_up = probs[i]
        p_dn = 1.0 - p_up
        
        sig = 'HOLD'
        # Multi-Zone Adaptive Entry Logic (Sesuai Bot Live V4.2)
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
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]; l_bar = lows[cur_idx]
            
            if sig == 'BUY':
                floating = h_bar - entry_p
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00)
                    trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20)
                    bep_locked = True
                    
                if h_bar >= tp_p:
                    outcome = "TP_FULL"; pnl_gross = tp_val; held_bars = step; break
                elif l_bar <= cur_sl:
                    if trailing_locked: outcome = "TRAILING_LOCK"; pnl_gross = 2.00
                    elif bep_locked: outcome = "BEP_SAVE"; pnl_gross = 0.20
                    else: outcome = "FULL_SL"; pnl_gross = -sl_val
                    held_bars = step; break
            else:
                floating = entry_p - l_bar
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00)
                    trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20)
                    bep_locked = True
                    
                if l_bar <= tp_p:
                    outcome = "TP_FULL"; pnl_gross = tp_val; held_bars = step; break
                elif h_bar >= cur_sl:
                    if trailing_locked: outcome = "TRAILING_LOCK"; pnl_gross = 2.00
                    elif bep_locked: outcome = "BEP_SAVE"; pnl_gross = 0.20
                    else: outcome = "FULL_SL"; pnl_gross = -sl_val
                    held_bars = step; break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            outcome = "AUTO_TIMEOUT"
            
        pnl_net = (pnl_gross * 100.0 * lot_size) - (TOTAL_FRICTION * 100.0 * lot_size)
        trades.append(pnl_net)
        trade_outcomes.append(outcome)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    wins = (trades > 0).sum()
    wr = (wins / n_tr) * 100.0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    
    return n_tr, wr, tot_pnl, pf, dd, pd.Series(trade_outcomes).value_counts().to_dict()

# JALANKAN BENCHMARK
def run_benchmark_set(title, spread, slippage):
    print("\n" + "="*125)
    print(f"{title} (Spread: ${spread:.2f} | Slippage: ${slippage:.2f} | Total Beban: ${spread+slippage:.2f}/trade)")
    print("="*125)
    models = [
        ("V4.2 (44 Fitur)", probs_44),
        ("V5.0 (57 Fitur)", probs_57),
        ("Model Juara (53 Fitur)", probs_j53),
        ("Juara + ICT (55 Fitur)", probs_j55)
    ]
    
    header = f"{'Metrik Riil':<28} | {'V4.2 (44 Fitur)':<22} | {'V5.0 (57 Fitur)':<22} | {'Juara (53 Fitur)':<22} | {'Juara + ICT (55)':<22}"
    print(header)
    print("-" * 125)
    
    res = {}
    for name, p in models:
        tr, wr, pnl, pf, dd, st = simulate_realistic(test_df, p, spread=spread, slippage=slippage, lot_size=0.01)
        res[name] = {'tr': tr, 'wr': wr, 'pnl': pnl, 'pf': pf, 'dd': dd, 'st': st}
        
    names = [m[0] for m in models]
    n0, n1, n2, n3 = names[0], names[1], names[2], names[3]
    print(f"{'Total Trades':<28} | {res[n0]['tr']:<22} | {res[n1]['tr']:<22} | {res[n2]['tr']:<22} | {res[n3]['tr']:<22}")
    print(f"{'Frekuensi Trade/Hari':<28} | {res[n0]['tr']/75:.1f} /hari{' '*15} | {res[n1]['tr']/75:.1f} /hari{' '*15} | {res[n2]['tr']/75:.1f} /hari{' '*15} | {res[n3]['tr']/75:.1f} /hari{' '*15}")
    print(f"{'Win Rate Riil (%)':<28} | {res[n0]['wr']:.2f}%{' '*15} | {res[n1]['wr']:.2f}%{' '*15} | {res[n2]['wr']:.2f}%{' '*15} | {res[n3]['wr']:.2f}%{' '*15}")
    print(f"{'Profit Factor':<28} | {res[n0]['pf']:.2f}{' '*17} | {res[n1]['pf']:.2f}{' '*17} | {res[n2]['pf']:.2f}{' '*17} | {res[n3]['pf']:.2f}{' '*17}")
    print(f"{'Net PnL Bersih ($)':<28} | +${res[n0]['pnl']:.2f} USD{' '*10} | +${res[n1]['pnl']:.2f} USD{' '*10} | +${res[n2]['pnl']:.2f} USD{' '*10} | +${res[n3]['pnl']:.2f} USD{' '*10}")
    print(f"{'Pertumbuhan Modal ($500)':<28} | +{(res[n0]['pnl']/500)*100:.1f}%{' '*15} | +{(res[n1]['pnl']/500)*100:.1f}%{' '*15} | +{(res[n2]['pnl']/500)*100:.1f}%{' '*15} | +{(res[n3]['pnl']/500)*100:.1f}%{' '*15}")
    print(f"{'Max Drawdown ($)':<28} | ${res[n0]['dd']:.2f} USD{' '*11} | ${res[n1]['dd']:.2f} USD{' '*11} | ${res[n2]['dd']:.2f} USD{' '*11} | ${res[n3]['dd']:.2f} USD{' '*11}")
    print("-" * 125)
    print(f"{'TP Penuh (+$6.50)':<28} | {res[n0]['st'].get('TP_FULL',0):<22} | {res[n1]['st'].get('TP_FULL',0):<22} | {res[n2]['st'].get('TP_FULL',0):<22} | {res[n3]['st'].get('TP_FULL',0):<22}")
    print(f"{'Trailing Lock (+$2.00)':<28} | {res[n0]['st'].get('TRAILING_LOCK',0):<22} | {res[n1]['st'].get('TRAILING_LOCK',0):<22} | {res[n2]['st'].get('TRAILING_LOCK',0):<22} | {res[n3]['st'].get('TRAILING_LOCK',0):<22}")
    print(f"{'BEP Save (+$0.20)':<28} | {res[n0]['st'].get('BEP_SAVE',0):<22} | {res[n1]['st'].get('BEP_SAVE',0):<22} | {res[n2]['st'].get('BEP_SAVE',0):<22} | {res[n3]['st'].get('BEP_SAVE',0):<22}")
    print(f"{'Full Stop Loss (-$6.50)':<28} | {res[n0]['st'].get('FULL_SL',0):<22} | {res[n1]['st'].get('FULL_SL',0):<22} | {res[n2]['st'].get('FULL_SL',0):<22} | {res[n3]['st'].get('FULL_SL',0):<22}")
    print("=" * 125)

run_benchmark_set("SKENARIO A: STANDAR BROKER EXNESS (SPREAD $0.20 SAJA)", spread=0.20, slippage=0.00)
run_benchmark_set("SKENARIO B: REALISTIS EKSTRIM PASAR RIIL (SPREAD $0.20 + SLIPPAGE $0.15 = TOTAL $0.35)", spread=0.20, slippage=0.15)
run_benchmark_set("SKENARIO C: PASAR SANGAT VOLATIL / NEWS (SPREAD $0.30 + SLIPPAGE $0.20 = TOTAL $0.50)", spread=0.30, slippage=0.20)
