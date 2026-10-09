import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*115)
print("SIMULASI KOMPARATIF: MODEL V4.2 VS MODEL V5.0 DENGAN FITUR PENYELAMAT PROFIT (LIVE SETUP)")
print("DAN ANALISIS REALISTIS FINANCIAL TRADING SCALPING (LOT 0.01 VS LOT 0.05 VS LOT 0.10)")
print("="*115)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik 25.000 Candle M15 ({symbol}) dari MT5...")
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

print(f"Dataset: {len(df_raw)} candle ({df_raw.index[0]} s/d {df_raw.index[-1]})")
print(f"Harga Emas Saat Ini: ${df_raw['close'].iloc[-1]:.2f} USD")
print(f"Rekor Tertinggi (ATH) Emas dalam Database: ${df_raw['high'].max():.2f} USD")

# Ekstraksi Fitur Bersih (Causal Zero Leakage)
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

# 13 Fitur Geometri Spasial Tambahan (Total 57 Fitur)
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

features_44 = [
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
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20'
]

features_57 = features_44[:-1] + [
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply', 'Nearest_Clearance',
    'Est_RRR_Buy', 'Est_RRR_Sell', 'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence',
    'Pattern_Type_Code', 'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

df.dropna(subset=features_57 + ['Target_Dir'], inplace=True)

test_len = int(len(df) * 0.20)
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

# Fitur Juara: 57 Fitur DIKURANGI 4 Fitur Racun (XAU_Return_10, Pattern_Slope_High, Nearest_Clearance, Double_Bottom_Dist)
poison = ['XAU_Return_10', 'Pattern_Slope_High', 'Nearest_Clearance', 'Double_Bottom_Dist']
features_juara = [f for f in features_57 if f not in poison]

# Train Models
lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
model_v42 = LGBMClassifier(**lgb_params).fit(train_df[features_44].values, train_df['Target_Dir'].values)
probs_v42 = model_v42.predict_proba(test_df[features_44].values)[:, 1]

model_v50 = LGBMClassifier(**lgb_params).fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_v50 = model_v50.predict_proba(test_df[features_57].values)[:, 1]

model_juara = LGBMClassifier(**lgb_params).fit(train_df[features_juara].values, train_df['Target_Dir'].values)
probs_juara = model_juara.predict_proba(test_df[features_juara].values)[:, 1]

# ENGINE EKSEKUSI CERDAS DENGAN FITUR PENYELAMAT PROFIT (PERSIS DENGAN BOT LIVE V4.2)
def run_live_style_simulation(test_data, probs, is_v42=True, lot_size=0.01, tp_val=6.50, sl_val=6.50):
    SPREAD = 0.20
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    opens  = test_data['open'].values
    dist_s = test_data['Dist_Support'].values
    dist_r = test_data['Dist_Resistance'].values
    l_wick = test_data['Lower_Wick_Ratio'].values
    u_wick = test_data['Upper_Wick_Ratio'].values
    n = len(closes)
    
    trades = []
    trade_outcomes = []
    active_until = -1
    max_bars = 25 # ~6 jam
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        p_up = probs[i]
        p_dn = 1.0 - p_up
        
        sig = 'HOLD'
        # Multi-Zone Adaptive Entry Logic (Sesuai Eksekusi_Otomatis_Trading_Bot.py)
        # Zona A: Boundary Bounce (Jarak <= 0.15% dari SNR + Rejection Wick >= 0.20 + Prob >= 0.58)
        if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20 and p_up >= 0.58:
            sig = 'BUY'
        elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20 and p_dn >= 0.58:
            sig = 'SELL'
        # Zona B: Proximity Rebound (Jarak 0.15% - 0.40% + Wick >= 0.18 + Prob >= 0.60)
        elif sig == 'HOLD' and dist_s[i] <= 0.0040 and l_wick[i] >= 0.18 and p_up >= 0.60:
            sig = 'BUY'
        elif sig == 'HOLD' and dist_r[i] <= 0.0040 and u_wick[i] >= 0.18 and p_dn >= 0.60:
            sig = 'SELL'
        # Zona C: Strong Trend / High Conviction (> 0.40% + Prob >= 0.65)
        elif sig == 'HOLD' and p_up >= 0.65:
            sig = 'BUY'
        elif sig == 'HOLD' and p_dn >= 0.65:
            sig = 'SELL'
            
        if sig == 'HOLD':
            continue
            
        entry_p = closes[i]
        tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
        sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
        cur_sl = sl_p
        
        # Status Penyelamat Profit
        bep_locked = False
        trailing_locked = False
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            c_bar = closes[cur_idx]
            
            # 1. SMART TRAILING LOCK (Kunci Cuan +$2.00 jika profit mencapai >= +$3.50)
            if sig == 'BUY':
                floating = h_bar - entry_p
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00)
                    trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20)
                    bep_locked = True
                    
                # Cek hit TP / SL
                if h_bar >= tp_p:
                    outcome = "TP_FULL"
                    pnl_gross = tp_val
                    held_bars = step
                    break
                elif l_bar <= cur_sl:
                    if trailing_locked:
                        outcome = "TRAILING_LOCK"
                        pnl_gross = 2.00
                    elif bep_locked:
                        outcome = "BEP_SAVE"
                        pnl_gross = 0.20
                    else:
                        outcome = "FULL_SL"
                        pnl_gross = -sl_val
                    held_bars = step
                    break
            else: # SELL
                floating = entry_p - l_bar
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00)
                    trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20)
                    bep_locked = True
                    
                if l_bar <= tp_p:
                    outcome = "TP_FULL"
                    pnl_gross = tp_val
                    held_bars = step
                    break
                elif h_bar >= cur_sl:
                    if trailing_locked:
                        outcome = "TRAILING_LOCK"
                        pnl_gross = 2.00
                    elif bep_locked:
                        outcome = "BEP_SAVE"
                        pnl_gross = 0.20
                    else:
                        outcome = "FULL_SL"
                        pnl_gross = -sl_val
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            outcome = "AUTO_TIMEOUT"
            
        pnl_net = (pnl_gross * 100.0 * lot_size) - (SPREAD * 100.0 * lot_size)
        trades.append(pnl_net)
        trade_outcomes.append(outcome)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    if n_tr == 0:
        return 0, 0, 0, 0, 0, {}
    wins = (trades > 0).sum()
    wr = (wins / n_tr) * 100.0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    
    out_counts = pd.Series(trade_outcomes).value_counts().to_dict()
    return n_tr, wr, tot_pnl, pf, dd, out_counts

# Uji Simulasi Head-to-Head
print("\n" + "="*115)
print("1. KOMPARASI HEAD-TO-HEAD MODEL V4.2 VS MODEL V5.0 (DENGAN FITUR PENYELAMAT PROFIT LIVE)")
print("="*115)

tr42, wr42, pnl42, pf42, dd42, stat42 = run_live_style_simulation(test_df, probs_v42, is_v42=True, lot_size=0.01)
tr50, wr50, pnl50, pf50, dd50, stat50 = run_live_style_simulation(test_df, probs_v50, is_v42=False, lot_size=0.01)
tr_j, wr_j, pnl_j, pf_j, dd_j, stat_j = run_live_style_simulation(test_df, probs_juara, is_v42=False, lot_size=0.01)

print(f"{'Metrik Pengujian':<26} | {'V4.2 (44 Fitur)':<24} | {'V5.0 (57 Fitur)':<24} | {'Model Juara (53 Fitur)':<24}")
print("-"*105)
print(f"{'Total Trades (2.5 Bulan)':<26} | {tr42:<24} | {tr50:<24} | {tr_j:<24}")
print(f"{'Frekuensi Trade / Hari':<26} | {f'{tr42/75:.1f} trade/hari':<24} | {f'{tr50/75:.1f} trade/hari':<24} | {f'{tr_j/75:.1f} trade/hari':<24}")
print(f"{'Win Rate (%)':<26} | {f'{wr42:.2f}%':<24} | {f'{wr50:.2f}%':<24} | {f'{wr_j:.2f}%':<24}")
print(f"{'Net PnL (Lot 0.01)':<26} | {f'+${pnl42:.2f} USD':<24} | {f'+${pnl50:.2f} USD':<24} | {f'+${pnl_j:.2f} USD':<24}")
print(f"{'Profit Factor':<26} | {f'{pf42:.2f}':<24} | {f'{pf50:.2f}':<24} | {f'{pf_j:.2f}':<24}")
print(f"{'Max Drawdown':<26} | {f'${dd42:.2f} USD':<24} | {f'${dd50:.2f} USD':<24} | {f'${dd_j:.2f} USD':<24}")
print("-"*105)
print(f"{'Rincian TP Penuh':<26} | {stat42.get('TP_FULL', 0):<24} | {stat50.get('TP_FULL', 0):<24} | {stat_j.get('TP_FULL', 0):<24}")
print(f"{'Rincian Trailing Lock':<26} | {stat42.get('TRAILING_LOCK', 0):<24} | {stat50.get('TRAILING_LOCK', 0):<24} | {stat_j.get('TRAILING_LOCK', 0):<24}")
print(f"{'Rincian BEP Selamat':<26} | {stat42.get('BEP_SAVE', 0):<24} | {stat50.get('BEP_SAVE', 0):<24} | {stat_j.get('BEP_SAVE', 0):<24}")
print(f"{'Rincian Full Loss (Kena SL)':<26} | {stat42.get('FULL_SL', 0):<24} | {stat50.get('FULL_SL', 0):<24} | {stat_j.get('FULL_SL', 0):<24}")

# 2. ANALISIS REALISTIS LAPANGAN: LOT 0.01 VS LOT 0.05 VS LOT 0.10
print("\n" + "="*115)
print("2. ANALISIS REALISTIS FINANCIAL TRADING LAPANGAN: MENGAPA TRADER MANUAL BISA CUAN JUTAAN?")
print("Simulasi Modal $500 USD di Pasar Riil XAUUSD Lintas Ukuran Lot (Kurs Rp 16.000 / USD)")
print("="*115)

lots = [0.01, 0.02, 0.05, 0.10]
lot_rows = []

for l in lots:
    tr, wr, pnl, pf, dd, _ = run_live_style_simulation(test_df, probs_v42, is_v42=True, lot_size=l)
    pnl_idr = pnl * 16000
    pnl_monthly_usd = pnl / 2.5
    pnl_monthly_idr = pnl_monthly_usd * 16000
    roc_pct = (pnl / 500.0) * 100.0
    lot_rows.append({
        "Ukuran_Lot": l,
        "Margin_Dipakai": f"${l * 4150 * 100 / 2000:.2f} USD",
        "Net_PnL_2_5_Bulan_USD": f"+${pnl:.2f}",
        "Net_PnL_2_5_Bulan_IDR": f"+Rp {pnl_idr:,.0f}",
        "Estimasi_Cuan_Per_Bulan": f"+Rp {pnl_monthly_idr:,.0f} / bln",
        "Return_Modal_500": f"+{roc_pct:.1f}%",
        "Max_Drawdown": f"${dd:.2f} USD ({dd/500*100:.1f}%)",
        "Tingkat_Risiko": "Sangat Konservatif (Skripsi)" if l == 0.01 else ("Aman Proporsional" if l <= 0.02 else ("Agresif Harian" if l == 0.05 else "Full Scalper Indonesia"))
    })

df_lot = pd.DataFrame(lot_rows)
print(df_lot.to_string(index=False))

excel_out = r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Hasil_Simulasi_V42_vs_V50_Live_Penyelamat_Profit.xlsx"
df_lot.to_excel(excel_out, index=False)
print(f"\n[OK] Berkas Excel berhasil disimpan ke: {excel_out}")
