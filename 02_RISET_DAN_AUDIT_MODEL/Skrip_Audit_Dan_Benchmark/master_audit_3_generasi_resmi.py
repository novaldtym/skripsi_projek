"""
================================Master Audit 3 Generasi Resmi=================================
Mengevaluasi V4.2 (44 Fitur) vs V5.0 (57 Fitur) vs Model Baru ICT (68 Fitur)
MENGGUNAKAN SIMULATOR RESMI PERSIS SKRIPSI (Single Position Lock, Trailing $2, BEP $0.20)
==============================================================================================
"""
import os, sys
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
mt5.initialize(path=MT5_PATH)
symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"

# Tarik 25.000 candle
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)
mt5.shutdown()

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

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

df['DXY_Close'] = 104.0
df['DXY_Return_1'] = 0.0
df['DXY_Return_3'] = 0.0
df['DXY_Trend'] = 1
df['XAU_DXY_Ratio_Return'] = 0.0

day_of_month = df.index.day
weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

ema50_h1 = df_h1['close'].ewm(span=50, adjust=False).mean()
ema200_h1 = df_h1['close'].ewm(span=200, adjust=False).mean()
df['Trend_H1_Bull']   = (df_h1['close'] > ema50_h1).astype(int).reindex(df.index, method='ffill').fillna(0)
df['Trend_H1_Strong'] = (ema50_h1 > ema200_h1).astype(int).reindex(df.index, method='ffill').fillna(0)
df['H1_Dist_EMA50']   = ((df_h1['close'] - ema50_h1) / df_h1['close']).reindex(df.index, method='ffill').fillna(0)

ema50_h4 = df_h4['close'].ewm(span=50, adjust=False).mean()
ema200_h4 = df_h4['close'].ewm(span=200, adjust=False).mean()
df['Trend_H4_Bull']   = (df_h4['close'] > ema50_h4).astype(int).reindex(df.index, method='ffill').fillna(0)
df['Trend_H4_Strong'] = (ema50_h4 > ema200_h4).astype(int).reindex(df.index, method='ffill').fillna(0)
df['H4_Dist_EMA50']   = ((df_h4['close'] - ema50_h4) / df_h4['close']).reindex(df.index, method='ffill').fillna(0)

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
df['XAU_Return_10'] = df['close'].pct_change(10)
df['XAU_Return_20'] = df['close'].pct_change(20)

df['Major_Demand_300'] = df['low'].rolling(300).min()
df['Major_Supply_300'] = df['high'].rolling(300).max()
df['Dist_Major_Demand'] = (df['close'] - df['Major_Demand_300']) / df['close']
df['Dist_Major_Supply'] = (df['Major_Supply_300'] - df['close']) / df['close']
df['Nearest_Clearance'] = df[['Dist_Support', 'Dist_Resistance']].min(axis=1) - 0.0018
df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)
df['Pinbar_Ratio'] = df[['Lower_Wick_Ratio', 'Upper_Wick_Ratio']].max(axis=1) / (df['Body_Ratio'] + 1e-5)

x = np.arange(35); x_mean = x.mean(); x_var = ((x - x_mean)**2).sum(); w_slope = (x - x_mean) / x_var
df['Pattern_Slope_High'] = df['high'].rolling(35).apply(lambda y: np.dot(y, w_slope), raw=True).fillna(0)
df['Pattern_Slope_Low']  = df['low'].rolling(35).apply(lambda y: np.dot(y, w_slope), raw=True).fillna(0)
spread_35 = (df['high'] - df['low']).rolling(35).mean() + 1e-5
df['Pattern_Convergence'] = (df['Pattern_Slope_Low'] - df['Pattern_Slope_High']) / spread_35

p_code = np.zeros(len(df))
sh = df['Pattern_Slope_High'].values; sl = df['Pattern_Slope_Low'].values
for i in range(len(df)):
    if sl[i] > 0.06 and abs(sh[i]) <= 0.15: p_code[i] = 1
    elif sh[i] < -0.06 and abs(sl[i]) <= 0.15: p_code[i] = 2
    elif sh[i] < -0.08 and sl[i] > 0.08: p_code[i] = 3
    elif sh[i] > 0.10 and sl[i] > 0.10: p_code[i] = 6
    elif sh[i] < -0.10 and sl[i] < -0.10: p_code[i] = 7
df['Pattern_Type_Code'] = p_code

df['Double_Top_Dist'] = (df['high'].shift(1).rolling(20).max() - df['high'].shift(21).rolling(20).max()).abs() / df['close']
df['Double_Bottom_Dist'] = (df['low'].shift(1).rolling(20).min() - df['low'].shift(21).rolling(20).min()).abs() / df['close']

# Fitur ICT
hours = df.index.hour
df['ICT_London_Killzone'] = ((hours >= 8) & (hours <= 12)).astype(int)
df['ICT_NY_Killzone']     = ((hours >= 13) & (hours <= 17)).astype(int)
df['ICT_Asia_Killzone']   = ((hours >= 1) & (hours <= 6)).astype(int)

lookback_day = 96
pdh = df['high'].shift(1).rolling(lookback_day).max()
pdl = df['low'].shift(1).rolling(lookback_day).min()
df['ICT_Dist_PDH']  = (pdh - df['close']) / df['close']
df['ICT_Dist_PDL']  = (df['close'] - pdl) / df['close']
df['ICT_Sweep_PDH'] = ((df['high'] > pdh) & (df['close'] < pdh)).astype(int)
df['ICT_Sweep_PDL'] = ((df['low'] < pdl) & (df['close'] > pdl)).astype(int)
df['ICT_In_Discount'] = (df['Fibo_Pos_100'] < 0.50).astype(int)
df['ICT_In_Premium']  = (df['Fibo_Pos_100'] > 0.50).astype(int)
df['ICT_In_OTE_Buy']  = ((df['Fibo_Pos_100'] >= 0.214) & (df['Fibo_Pos_100'] <= 0.382)).astype(int)
df['ICT_In_OTE_Sell'] = ((df['Fibo_Pos_100'] >= 0.618) & (df['Fibo_Pos_100'] <= 0.786)).astype(int)

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

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

features_57 = features_44[:-1] + [
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply', 'Nearest_Clearance',
    'Est_RRR_Buy', 'Est_RRR_Sell', 'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence',
    'Pattern_Type_Code', 'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

features_68 = features_57 + [
    'ICT_London_Killzone', 'ICT_NY_Killzone', 'ICT_Asia_Killzone',
    'ICT_Dist_PDH', 'ICT_Dist_PDL', 'ICT_Sweep_PDH', 'ICT_Sweep_PDL',
    'ICT_In_Discount', 'ICT_In_Premium', 'ICT_In_OTE_Buy', 'ICT_In_OTE_Sell'
]

df.dropna(subset=features_68 + ['Target_Dir'], inplace=True)

test_len = 5000 # 2.5 Bulan
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

# Train Models
lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
m_v42 = LGBMClassifier(**lgb_params).fit(train_df[features_44].values, train_df['Target_Dir'].values)
probs_v42 = m_v42.predict_proba(test_df[features_44].values)[:, 1]

m_v50 = LGBMClassifier(**lgb_params).fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_v50 = m_v50.predict_proba(test_df[features_57].values)[:, 1]

m_ict = LGBMClassifier(**lgb_params).fit(train_df[features_68].values, train_df['Target_Dir'].values)
probs_ict = m_ict.predict_proba(test_df[features_68].values)[:, 1]

# ENGINE PERSIS DENGAN simulasi_v42_vs_v5_dengan_penyelamat_profit_dan_lot_realistis.py
def run_official_simulation(test_data, probs):
    SPREAD = 0.20
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
    max_bars = 25 # ~6 jam
    tp_val = 6.50
    sl_val = 6.50
    lot_size = 0.01

    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        p_up = probs[i]
        p_dn = 1.0 - p_up
        
        sig = 'HOLD'
        # Multi-Zone Adaptive Entry Logic (Sesuai Eksekusi_Otomatis_Trading_Bot.py)
        if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20 and p_up >= 0.58:
            sig = 'BUY'
        elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20 and p_dn >= 0.58:
            sig = 'SELL'
        elif sig == 'HOLD' and dist_s[i] <= 0.0040 and l_wick[i] >= 0.18 and p_up >= 0.60:
            sig = 'BUY'
        elif sig == 'HOLD' and dist_r[i] <= 0.0040 and u_wick[i] >= 0.18 and p_dn >= 0.60:
            sig = 'SELL'
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
            else: # SELL
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
            
        pnl_net = (pnl_gross * 100.0 * lot_size) - (SPREAD * 100.0 * lot_size)
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
    out_counts = pd.Series(trade_outcomes).value_counts().to_dict()
    return n_tr, wr, tot_pnl, pf, out_counts

tr42, wr42, pnl42, pf42, st42 = run_official_simulation(test_df, probs_v42)
tr50, wr50, pnl50, pf50, st50 = run_official_simulation(test_df, probs_v50)
trict, wrict, pnlict, pfict, stict = run_official_simulation(test_df, probs_ict)

print("="*105)
print(f"{'Metrik Resmi Skripsi':<26} | {'V4.2 (44 Fitur)':<24} | {'V5.0 (57 Fitur)':<24} | {'Model Baru (68 Fitur ICT)':<24}")
print("="*105)
print(f"{'Total Trade (2.5 Bulan)':<26} | {tr42:<24} | {tr50:<24} | {trict:<24}")
print(f"{'Frekuensi Trade/Hari':<26} | {f'{tr42/75:.1f} trade/hari':<24} | {f'{tr50/75:.1f} trade/hari':<24} | {f'{trict/75:.1f} trade/hari':<24}")
print(f"{'Win Rate Riil (%)':<26} | {f'{wr42:.2f}%':<24} | {f'{wr50:.2f}%':<24} | {f'{wrict:.2f}%':<24}")
print(f"{'Profit Factor':<26} | {f'{pf42:.2f}':<24} | {f'{pf50:.2f}':<24} | {f'{pfict:.2f}':<24}")
print(f"{'Net PnL (Lot 0.01 / $500)':<26} | {f'+${pnl42:.2f} USD':<24} | {f'+${pnl50:.2f} USD':<24} | {f'+${pnlict:.2f} USD':<24}")
print(f"{'Return Modal ($500)':<26} | {f'+{(pnl42/500)*100:.1f}%':<24} | {f'+{(pnl50/500)*100:.1f}%':<24} | {f'+{(pnlict/500)*100:.1f}%':<24}")
print("-"*105)
print(f"{'Rincian TP Penuh':<26} | {st42.get('TP_FULL',0):<24} | {st50.get('TP_FULL',0):<24} | {stict.get('TP_FULL',0):<24}")
print(f"{'Rincian Trailing Lock':<26} | {st42.get('TRAILING_LOCK',0):<24} | {st50.get('TRAILING_LOCK',0):<24} | {stict.get('TRAILING_LOCK',0):<24}")
print(f"{'Rincian BEP Selamat':<26} | {st42.get('BEP_SAVE',0):<24} | {st50.get('BEP_SAVE',0):<24} | {stict.get('BEP_SAVE',0):<24}")
print(f"{'Rincian Full SL (Loss)':<26} | {st42.get('FULL_SL',0):<24} | {st50.get('FULL_SL',0):<24} | {stict.get('FULL_SL',0):<24}")
print("="*105)
