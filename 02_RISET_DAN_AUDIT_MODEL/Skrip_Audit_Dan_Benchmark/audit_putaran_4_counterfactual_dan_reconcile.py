import os
import sys
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*120)
print("AUDIT PUTARAN 4: COUNTERFACTUAL BEP, REKONSILIASI FINANSIAL KANONIKAL, & BOOTSTRAP PAIR DELTA ACCURACY")
print("="*120)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

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
    if dxy_close.index.tz is not None: dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()

# 57 Fitur Causal
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

# ENGINE EKSEKUSI COUNTERFACTUAL: DENGAN BEP VS TANPA BEP
def run_counterfactual_bep(test_data, probs, enable_bep=True):
    SPREAD = 0.20
    lot_size = 0.01
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    dist_s = test_data['Dist_Support'].values
    dist_r = test_data['Dist_Resistance'].values
    l_wick = test_data['Lower_Wick_Ratio'].values
    u_wick = test_data['Upper_Wick_Ratio'].values
    n = len(closes)
    
    trades = []
    trade_details = []
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
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            if sig == 'BUY':
                floating = h_bar - entry_p
                # Trailing Lock
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00)
                    trailing_locked = True
                # BEP Protection (jika aktif)
                elif enable_bep and floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20)
                    bep_locked = True
                    
                if h_bar >= tp_p:
                    outcome = "WIN_TP"
                    pnl_gross = tp_val
                    held_bars = step
                    break
                elif l_bar <= cur_sl:
                    if trailing_locked:
                        outcome = "WIN_TRAILING"
                        pnl_gross = 2.00
                    elif bep_locked:
                        outcome = "BEP"
                        pnl_gross = 0.20
                    else:
                        outcome = "LOSS_SL"
                        pnl_gross = -sl_val
                    held_bars = step
                    break
            else:
                floating = entry_p - l_bar
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00)
                    trailing_locked = True
                elif enable_bep and floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20)
                    bep_locked = True
                    
                if l_bar <= tp_p:
                    outcome = "WIN_TP"
                    pnl_gross = tp_val
                    held_bars = step
                    break
                elif h_bar >= cur_sl:
                    if trailing_locked:
                        outcome = "WIN_TRAILING"
                        pnl_gross = 2.00
                    elif bep_locked:
                        outcome = "BEP"
                        pnl_gross = 0.20
                    else:
                        outcome = "LOSS_SL"
                        pnl_gross = -sl_val
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            outcome = "WIN_TIMEOUT" if pnl_gross > 0 else "LOSS_TIMEOUT"
            
        pnl_net = (pnl_gross * 1.0) - SPREAD # Lot 0.01 ($1/point)
        trades.append(pnl_net)
        trade_details.append(outcome)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    
    # Hitung Kategori Transaksi
    n_win_tp = sum(1 for x in trade_details if x == 'WIN_TP')
    n_win_tr = sum(1 for x in trade_details if x == 'WIN_TRAILING')
    n_bep    = sum(1 for x in trade_details if x == 'BEP')
    n_loss   = sum(1 for x in trade_details if 'LOSS' in x)
    
    # Pure Win adalah WIN_TP + WIN_TRAILING
    n_pure_win = n_win_tp + n_win_tr
    n_non_loss = n_pure_win + n_bep
    
    pure_wr = (n_pure_win / n_tr) * 100.0
    bep_rate = (n_bep / n_tr) * 100.0
    non_loss_rate = (n_non_loss / n_tr) * 100.0
    
    tot_pnl = trades.sum()
    gross_win = trades[trades > 0].sum()
    gross_loss = abs(trades[trades < 0].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0
    
    avg_win = trades[trades > 0].mean() if len(trades[trades > 0]) > 0 else 0.0
    avg_loss = abs(trades[trades < 0].mean()) if len(trades[trades < 0]) > 0 else 0.0
    expectancy = ( (pure_wr/100.0) * avg_win ) - ( ((100.0 - non_loss_rate)/100.0) * avg_loss )
    
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    
    res_dict = {
        "Total_Trades": n_tr,
        "Pure_Win_N": n_pure_win,
        "Pure_Win_Pct": round(pure_wr, 2),
        "TP_Full_N": n_win_tp,
        "Trailing_Lock_N": n_win_tr,
        "BEP_N": n_bep,
        "BEP_Pct": round(bep_rate, 2),
        "Loss_N": n_loss,
        "Loss_Pct": round((n_loss/n_tr)*100.0, 2),
        "Non_Loss_Pct": round(non_loss_rate, 2),
        "Gross_Profit_USD": round(gross_win, 2),
        "Gross_Loss_USD": round(gross_loss, 2),
        "Net_PnL_USD": round(tot_pnl, 2),
        "Avg_Win_USD": round(avg_win, 2),
        "Avg_Loss_USD": round(avg_loss, 2),
        "Expectancy_USD": round(expectancy, 2),
        "Profit_Factor": round(pf, 2),
        "Max_Drawdown_USD": round(dd, 2)
    }
    return res_dict

res_with_bep = run_counterfactual_bep(test_df, probs_v50, enable_bep=True)
res_no_bep   = run_counterfactual_bep(test_df, probs_v50, enable_bep=False)

print("\n" + "="*120)
print("HASIL AUDIT COUNTERFACTUAL: KONTRIBUSI KAUSAL FITUR BEP (583 TRADES PADA MODEL V5.0)")
print("="*120)
print(f"{'Metrik Evaluasi':<32} | {'A. DENGAN BEP (Live Sistem)':<35} | {'B. TANPA BEP (Counterfactual)':<35}")
print("-"*120)
print(f"{'Total Trades':<32} | {res_with_bep['Total_Trades']:<35} | {res_no_bep['Total_Trades']:<35}")
print(f"{'Pure Win (TP + Trailing)':<32} | {res_with_bep['Pure_Win_N']} trade ({res_with_bep['Pure_Win_Pct']}%) | {res_no_bep['Pure_Win_N']} trade ({res_no_bep['Pure_Win_Pct']}%)")
print(f"{'BEP (+20 sen)':<32} | {res_with_bep['BEP_N']} trade ({res_with_bep['BEP_Pct']}%) | {res_no_bep['BEP_N']} trade ({res_no_bep['BEP_Pct']}%)")
print(f"{'Full Loss (Kena SL)':<32} | {res_with_bep['Loss_N']} trade ({res_with_bep['Loss_Pct']}%) | {res_no_bep['Loss_N']} trade ({res_no_bep['Loss_Pct']}%)")
print(f"{'Non-Loss Rate (Win + BEP)':<32} | {res_with_bep['Non_Loss_Pct']}% | {res_no_bep['Non_Loss_Pct']}%")
print(f"{'Gross Profit ($)':<32} | ${res_with_bep['Gross_Profit_USD']} USD | ${res_no_bep['Gross_Profit_USD']} USD")
print(f"{'Gross Loss ($)':<32} | ${res_with_bep['Gross_Loss_USD']} USD | ${res_no_bep['Gross_Loss_USD']} USD")
print(f"{'Net PnL Bersih ($)':<32} | +${res_with_bep['Net_PnL_USD']} USD | +${res_no_bep['Net_PnL_USD']} USD")
print(f"{'Rasio Profit Factor (PF)':<32} | {res_with_bep['Profit_Factor']} | {res_no_bep['Profit_Factor']}")
print(f"{'Max Drawdown':<32} | ${res_with_bep['Max_Drawdown_USD']} USD | ${res_no_bep['Max_Drawdown_USD']} USD")
print(f"{'Average Winner':<32} | +${res_with_bep['Avg_Win_USD']} USD | +${res_no_bep['Avg_Win_USD']} USD")
print(f"{'Average Loser':<32} | -${res_with_bep['Avg_Loss_USD']} USD | -${res_no_bep['Avg_Loss_USD']} USD")
print(f"{'Expectancy per Trade':<32} | +${res_with_bep['Expectancy_USD']} USD / trade | +${res_no_bep['Expectancy_USD']} USD / trade")

out_excel = r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Audit_Putaran_4_Counterfactual_BEP_dan_Metrik_Finansial.xlsx"
df_cf = pd.DataFrame([
    {"Parameter": "Total Trades", "Dengan_BEP": res_with_bep['Total_Trades'], "Tanpa_BEP": res_no_bep['Total_Trades']},
    {"Parameter": "Pure Win Count", "Dengan_BEP": res_with_bep['Pure_Win_N'], "Tanpa_BEP": res_no_bep['Pure_Win_N']},
    {"Parameter": "Pure Win Rate (%)", "Dengan_BEP": res_with_bep['Pure_Win_Pct'], "Tanpa_BEP": res_no_bep['Pure_Win_Pct']},
    {"Parameter": "BEP Count", "Dengan_BEP": res_with_bep['BEP_N'], "Tanpa_BEP": res_no_bep['BEP_N']},
    {"Parameter": "BEP Rate (%)", "Dengan_BEP": res_with_bep['BEP_Pct'], "Tanpa_BEP": res_no_bep['BEP_Pct']},
    {"Parameter": "Loss Count", "Dengan_BEP": res_with_bep['Loss_N'], "Tanpa_BEP": res_no_bep['Loss_N']},
    {"Parameter": "Loss Rate (%)", "Dengan_BEP": res_with_bep['Loss_Pct'], "Tanpa_BEP": res_no_bep['Loss_Pct']},
    {"Parameter": "Non-Loss Rate (%)", "Dengan_BEP": res_with_bep['Non_Loss_Pct'], "Tanpa_BEP": res_no_bep['Non_Loss_Pct']},
    {"Parameter": "Gross Profit (USD)", "Dengan_BEP": res_with_bep['Gross_Profit_USD'], "Tanpa_BEP": res_no_bep['Gross_Profit_USD']},
    {"Parameter": "Gross Loss (USD)", "Dengan_BEP": res_with_bep['Gross_Loss_USD'], "Tanpa_BEP": res_no_bep['Gross_Loss_USD']},
    {"Parameter": "Net PnL (USD)", "Dengan_BEP": res_with_bep['Net_PnL_USD'], "Tanpa_BEP": res_no_bep['Net_PnL_USD']},
    {"Parameter": "Profit Factor", "Dengan_BEP": res_with_bep['Profit_Factor'], "Tanpa_BEP": res_no_bep['Profit_Factor']},
    {"Parameter": "Max Drawdown (USD)", "Dengan_BEP": res_with_bep['Max_Drawdown_USD'], "Tanpa_BEP": res_no_bep['Max_Drawdown_USD']},
    {"Parameter": "Expectancy (USD)", "Dengan_BEP": res_with_bep['Expectancy_USD'], "Tanpa_BEP": res_no_bep['Expectancy_USD']},
])
df_cf.to_excel(out_excel, index=False)
print(f"\n[OK] Excel audit berhasil disimpan ke: {out_excel}")
