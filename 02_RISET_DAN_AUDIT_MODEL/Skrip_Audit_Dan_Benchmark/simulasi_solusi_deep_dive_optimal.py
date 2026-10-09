import os
import sys
import time
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("==============================================================================================================")
print("DEEP DIVE OPTIMASI 3 SOLUSI TINGKAT LANJUT:")
print("Uji Efektivitas Konfluensi Multi-Timeframe M15+M5, Sesi London/NY, dan Hybrid Ensemble")
print("==============================================================================================================")

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik data historis dari MT5 ({symbol})...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5,  0, 75000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1,  0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4,  0, 2500)

df_m15 = pd.DataFrame(rates_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
df_m15.set_index('time', inplace=True)

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
df_m5.set_index('time', inplace=True)

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

def build_features(df_in, df_h1_in, df_h4_in, dxy_series, tf_horizon=5):
    df = df_in.copy()
    df_h1_loc = df_h1_in.copy()
    df_h4_loc = df_h4_in.copy()
    
    candle_range = (df['high'] - df['low']).replace(0, 1e-5)
    body = (df['close'] - df['open']).abs()
    upper_wick = df['high'] - df[['close', 'open']].max(axis=1)
    lower_wick = df[['close', 'open']].min(axis=1) - df['low']
    
    df['Body_Ratio'] = body / candle_range
    df['Upper_Wick_Ratio'] = upper_wick / candle_range
    df['Lower_Wick_Ratio'] = lower_wick / candle_range
    
    df['FVG_Bull'] = ((df['low'] - df['high'].shift(2)) > 0).astype(int)
    df['FVG_Bear'] = ((df['low'].shift(2) - df['high']) > 0).astype(int)
    
    df['Swing_High'] = df['high'].shift(1).rolling(20).max()
    df['Swing_Low']  = df['low'].shift(1).rolling(20).min()
    df['Dist_Resistance'] = (df['Swing_High'] - df['close']) / df['close']
    df['Dist_Support']    = (df['close'] - df['Swing_Low']) / df['close']
    
    df['BOS_Bull'] = (df['close'] > df['Swing_High']).astype(int)
    df['BOS_Bear'] = (df['close'] < df['Swing_Low']).astype(int)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High']) & (df['close'].shift(1) <= df['Swing_High'].shift(1))).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low']) & (df['close'].shift(1) >= df['Swing_Low'].shift(1))).astype(int)
    
    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High']) & (df['close'] < df['Swing_High'])).astype(int)
    df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low']) & (df['close'] > df['Swing_Low'])).astype(int)
    
    body_sz = (df['close'] - df['open']).abs()
    avg_body = body_sz.rolling(20).mean()
    impulse_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
    impulse_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
    is_bear_c = df['close'] < df['open']
    is_bull_c = df['close'] > df['open']
    
    # 100% Causal Zero Leakage
    df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up.fillna(False)).astype(int)
    df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn.fillna(False)).astype(int)
    
    lookback_fibo = 50
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
    df['XAU_Return_10'] = df['close'].pct_change(10)
    df['XAU_Return_20'] = df['close'].pct_change(20)
    
    df['DXY_Close'] = dxy_series.reindex(df.index, method='ffill').bfill()
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
    
    h1_close_series = df_h1_loc['close'].shift(1)
    h4_close_series = df_h4_loc['close'].shift(1)
    
    df_h1_loc['EMA_50_H1']  = h1_close_series.ewm(span=50, adjust=False).mean()
    df_h1_loc['EMA_200_H1'] = h1_close_series.ewm(span=200, adjust=False).mean()
    df_h1_loc['Trend_H1_Bull']   = (h1_close_series > df_h1_loc['EMA_50_H1']).astype(int)
    df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
    df_h1_loc['H1_Dist_EMA50']   = (h1_close_series - df_h1_loc['EMA_50_H1']) / h1_close_series
    
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
    
    # 13 Fitur Geometri Spasial
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
    
    df['Target_Dir'] = (df['close'].shift(-tf_horizon) > df['close']).astype(int)
    return df

print("Mengekstrak 57 fitur...")
df_m15_feat = build_features(df_m15, df_h1, df_h4, dxy_close, tf_horizon=5)
df_m5_feat  = build_features(df_m5,  df_h1, df_h4, dxy_close, tf_horizon=6)

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
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply', 'Nearest_Clearance',
    'Est_RRR_Buy', 'Est_RRR_Sell', 'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence',
    'Pattern_Type_Code', 'Double_Top_Dist', 'Double_Bottom_Dist'
]

df_m15_feat.dropna(subset=features_57 + ['Target_Dir'], inplace=True)
df_m5_feat.dropna(subset=features_57 + ['Target_Dir'], inplace=True)

test_len_m15 = int(len(df_m15_feat) * 0.20)
train_m15 = df_m15_feat.iloc[:-test_len_m15]
test_m15  = df_m15_feat.iloc[-test_len_m15:]

test_len_m5 = int(len(df_m5_feat) * 0.20)
train_m5 = df_m5_feat.iloc[:-test_len_m5]
test_m5  = df_m5_feat.iloc[-test_len_m5:]

# Model parameters
lgb_params = dict(n_estimators=300, learning_rate=0.03, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
lgb_m15 = LGBMClassifier(**lgb_params).fit(train_m15[features_57].values, train_m15['Target_Dir'].values)
probs_lgb_m15 = lgb_m15.predict_proba(test_m15[features_57].values)[:, 1]

lgb_m5 = LGBMClassifier(**lgb_params).fit(train_m5[features_57].values, train_m5['Target_Dir'].values)
probs_lgb_m5 = lgb_m5.predict_proba(test_m5[features_57].values)[:, 1]

# Backtest Engine with Trailing BEP
def backtest_engine(test_df, signals, tp_dist, sl_dist, use_bep=False, bep_trigger=3.0, max_bars=30):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    n = len(closes)
    
    trades = []
    active_until = -1
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        sig = signals[i]
        if sig not in ['BUY', 'SELL']:
            continue
            
        entry_p = closes[i]
        tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        sl_p = entry_p - sl_dist if sig == 'BUY' else entry_p + sl_dist
        cur_sl = sl_p
        bep_on = False
        
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            if use_bep and not bep_on:
                if sig == 'BUY' and (h_bar - entry_p) >= bep_trigger:
                    cur_sl = entry_p + 0.20
                    bep_on = True
                elif sig == 'SELL' and (entry_p - l_bar) >= bep_trigger:
                    cur_sl = entry_p - 0.20
                    bep_on = True
            
            if sig == 'BUY':
                hit_tp = h_bar >= tp_p
                hit_sl = l_bar <= cur_sl
                if hit_tp and hit_sl:
                    outcome = "BEP" if bep_on else "LOSS"
                    pnl_gross = 0.20 if bep_on else -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "BEP" if bep_on else "LOSS"
                    pnl_gross = 0.20 if bep_on else -sl_dist
                    held_bars = step
                    break
            else:
                hit_tp = l_bar <= tp_p
                hit_sl = h_bar >= cur_sl
                if hit_tp and hit_sl:
                    outcome = "BEP" if bep_on else "LOSS"
                    pnl_gross = 0.20 if bep_on else -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "BEP" if bep_on else "LOSS"
                    pnl_gross = 0.20 if bep_on else -sl_dist
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    if n_tr == 0:
        return 0, 0.0, 0.0, 0.0, 0.0
    wins = (trades > 0).sum()
    wr = (wins / n_tr) * 100.0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    return n_tr, wr, tot_pnl, pf, dd

# 1. Baseline Model V5.0 Standar (M15, Thresh >= 65%, TP $12, SL $6)
conf_lgb_m15 = np.maximum(probs_lgb_m15, 1.0 - probs_lgb_m15)
sig_base = np.where(conf_lgb_m15 >= 0.65, np.where(probs_lgb_m15 >= 0.5, 'BUY', 'SELL'), 'HOLD')
tr_b, wr_b, pnl_b, pf_b, dd_b = backtest_engine(test_m15, sig_base, tp_dist=12.00, sl_dist=6.00)

# 2. Sesi London & NY (14:00 - 23:00 WIB / 07:00 - 16:00 UTC) dengan TP $12 / SL $6 (RRR 1:2)
hours_m15 = test_m15.index.hour
is_active_ses_m15 = (hours_m15 >= 7) & (hours_m15 <= 16)
sig_ses_12 = np.where(is_active_ses_m15 & (conf_lgb_m15 >= 0.58), np.where(probs_lgb_m15 >= 0.5, 'BUY', 'SELL'), 'HOLD')
tr_ses, wr_ses, pnl_ses, pf_ses, dd_ses = backtest_engine(test_m15, sig_ses_12, tp_dist=12.00, sl_dist=6.00)

# 3. Sesi London & NY dengan Trailing BEP (TP $12 / SL $6, BEP trigger $4.00)
tr_ses_bep, wr_ses_bep, pnl_ses_bep, pf_ses_bep, dd_ses_bep = backtest_engine(test_m15, sig_ses_12, tp_dist=12.00, sl_dist=6.00, use_bep=True, bep_trigger=4.0)

# 4. Dual-Engine M15 + M5 Confluence
m15_bias_series = pd.Series(np.where(probs_lgb_m15 >= 0.54, 'BUY', np.where(probs_lgb_m15 <= 0.46, 'SELL', 'NEUTRAL')), index=test_m15.index)
m15_bias_m5 = m15_bias_series.reindex(test_m5.index, method='ffill').fillna('NEUTRAL')
conf_lgb_m5 = np.maximum(probs_lgb_m5, 1.0 - probs_lgb_m5)
sig_m5_raw = np.where(conf_lgb_m5 >= 0.58, np.where(probs_lgb_m5 >= 0.5, 'BUY', 'SELL'), 'HOLD')

sig_dual = np.where((sig_m5_raw == 'BUY') & (m15_bias_m5 == 'BUY'), 'BUY',
           np.where((sig_m5_raw == 'SELL') & (m15_bias_m5 == 'SELL'), 'SELL', 'HOLD'))

# Dual Engine Standard Scalp (TP $4.50, SL $2.50)
tr_d1, wr_d1, pnl_d1, pf_d1, dd_d1 = backtest_engine(test_m5, sig_dual, tp_dist=4.50, sl_dist=2.50, max_bars=18)

# Dual Engine RRR 1:2 (TP $6.00, SL $3.00)
tr_d2, wr_d2, pnl_d2, pf_d2, dd_d2 = backtest_engine(test_m5, sig_dual, tp_dist=6.00, sl_dist=3.00, max_bars=24)

# Dual Engine + Filter Sesi London & NY (14:00 - 23:00 WIB)
hours_m5 = test_m5.index.hour
is_active_ses_m5 = (hours_m5 >= 7) & (hours_m5 <= 16)
sig_dual_ses = np.where(is_active_ses_m5, sig_dual, 'HOLD')

tr_d3, wr_d3, pnl_d3, pf_d3, dd_d3 = backtest_engine(test_m5, sig_dual_ses, tp_dist=6.00, sl_dist=3.00, max_bars=24)

# Dual Engine + Sesi London/NY + Trailing BEP ($2.00)
tr_d4, wr_d4, pnl_d4, pf_d4, dd_d4 = backtest_engine(test_m5, sig_dual_ses, tp_dist=6.00, sl_dist=3.00, use_bep=True, bep_trigger=2.50, max_bars=24)

print("\n" + "="*115)
print(f"{'Varian Strategi':<45} | {'Trades':<6} | {'WR (%)':<7} | {'Net PnL':<10} | {'PF':<5} | {'Max DD':<9}")
print("="*115)
print(f"{'1. Baseline V5.0 (M15 Static Thresh 65%)':<45} | {tr_b:<6} | {wr_b:<7.2f} | ${pnl_b:<9.2f} | {pf_b:<5.2f} | ${dd_b:<8.2f}")
print(f"{'2. Sesi London/NY M15 (TP $12/SL $6)':<45} | {tr_ses:<6} | {wr_ses:<7.2f} | ${pnl_ses:<9.2f} | {pf_ses:<5.2f} | ${dd_ses:<8.2f}")
print(f"{'3. Sesi London/NY M15 + BEP Trailing':<45} | {tr_ses_bep:<6} | {wr_ses_bep:<7.2f} | ${pnl_ses_bep:<9.2f} | {pf_ses_bep:<5.2f} | ${dd_ses_bep:<8.2f}")
print(f"{'4. Dual-Engine M15+M5 (TP $4.50/SL $2.50)':<45} | {tr_d1:<6} | {wr_d1:<7.2f} | ${pnl_d1:<9.2f} | {pf_d1:<5.2f} | ${dd_d1:<8.2f}")
print(f"{'5. Dual-Engine M15+M5 RRR 1:2 (TP $6/SL $3)':<45} | {tr_d2:<6} | {wr_d2:<7.2f} | ${pnl_d2:<9.2f} | {pf_d2:<5.2f} | ${dd_d2:<8.2f}")
print(f"{'6. Dual-Engine M15+M5 + Sesi London/NY':<45} | {tr_d3:<6} | {wr_d3:<7.2f} | ${pnl_d3:<9.2f} | {pf_d3:<5.2f} | ${dd_d3:<8.2f}")
print(f"{'7. Dual-Engine M15+M5 + Sesi + BEP Trailing':<45} | {tr_d4:<6} | {wr_d4:<7.2f} | ${pnl_d4:<9.2f} | {pf_d4:<5.2f} | ${dd_d4:<8.2f}")
print("="*115)
