import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*110)
print("AUDIT MENDALAM: VERIFIKASI SINYAL BUY VS SELL, TARGET TP $6.50, DAN STRATEGI 300-600 TRADE WR >= 60%")
print("STANDAR DATA: DATA HISTORIS MT5 25.000 CANDLE M15 (HARGA SPOT ~$4.160 USD), MODAL $500, LOT 0.01")
print("="*110)

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

# Ekstraksi Fitur Kausal
df = df_raw.copy()
df_h1_loc = df_h1.copy()
df_h4_loc = df_h4.copy()

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

impulse_up = (df['close'] - df['close'].shift(2)) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
impulse_dn = (df['close'].shift(2) - df['close']) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up.fillna(False)).astype(int)
df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn.fillna(False)).astype(int)

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
df['XAU_Return_10'] = df['close'].pct_change(10)
df['XAU_Return_20'] = df['close'].pct_change(20)

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

h = 5
df['Target_Dir'] = (df['close'].shift(-h) > df['close']).astype(int)

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
    'Trend_H1_Bull', 'Trend_H1_Strong',
    'Trend_H4_Bull', 'Trend_H4_Strong',
    'H1_Dist_EMA50', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ADX_14', 'Volume_Ratio',
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

df_clean = df.dropna(subset=features_57 + ['Target_Dir', 'ATR_14']).copy()
split_idx = int(len(df_clean) * 0.80)
train_df = df_clean.iloc[:split_idx - h].copy()
test_df  = df_clean.iloc[split_idx:].copy()

clf = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)
clf.fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_up = clf.predict_proba(test_df[features_57].values)[:, 1]
probs_dn = 1.0 - probs_up

# 1. ANALISIS RINCIAN BUY VS SELL
conf = np.maximum(probs_up, probs_dn)
mask65 = conf >= 0.65

buy_signals  = (probs_up >= 0.65)
sell_signals = (probs_dn >= 0.65)

print("\n--- 1. VERIFIKASI SEIMBANG PREDIKSI ARAH (BUY VS SELL) ---")
print(f"Total Bar Uji Independen : {len(test_df)} bar")
print(f"Total Sinyal Conf >= 65% : {mask65.sum()} bar ({mask65.mean()*100:.2f}%)")
print(f"  • Sinyal BUY (Naik)    : {buy_signals.sum()} bar ({buy_signals.sum()/mask65.sum()*100:.1f}%)")
print(f"  • Sinyal SELL (Turun)  : {sell_signals.sum()} bar ({sell_signals.sum()/mask65.sum()*100:.1f}%)")

y_true = test_df['Target_Dir'].values
acc_buy  = (y_true[buy_signals] == 1).mean() * 100.0 if buy_signals.sum() > 0 else 0.0
acc_sell = (y_true[sell_signals] == 0).mean() * 100.0 if sell_signals.sum() > 0 else 0.0
print(f"Akurasi Arah Sinyal BUY  : {acc_buy:.2f}%")
print(f"Akurasi Arah Sinyal SELL : {acc_sell:.2f}%")

# 2. SIMULASI TRADING DENGAN RINCIAN BUY VS SELL DAN BERBAGAI TP
def run_detailed_simulation(tp_pts, sl_pts, thresh=0.65, use_bep=False, bep_trigger=4.0):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    n = len(closes)
    
    trades_buy = []
    trades_sell = []
    active_until = -1
    max_bars = 30
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        pb = probs_up[i]
        ps = probs_dn[i]
        c = max(pb, ps)
        
        if c < thresh:
            continue
            
        sig = 'BUY' if pb >= 0.5 else 'SELL'
        entry_p = closes[i]
        
        tp_p = entry_p + tp_pts if sig == 'BUY' else entry_p - tp_pts
        sl_p = entry_p - sl_pts if sig == 'BUY' else entry_p + sl_pts
        
        cur_sl = sl_p
        bep_activated = False
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            # Trailing BEP
            if use_bep and not bep_activated:
                if sig == 'BUY' and (h_bar - entry_p) >= bep_trigger:
                    cur_sl = entry_p + 0.20 # BEP +20 sen
                    bep_activated = True
                elif sig == 'SELL' and (entry_p - l_bar) >= bep_trigger:
                    cur_sl = entry_p - 0.20
                    bep_activated = True
                    
            if sig == 'BUY':
                hit_tp = h_bar >= tp_p
                hit_sl = l_bar <= cur_sl
                if hit_tp and hit_sl:
                    outcome = "LOSS" if not bep_activated else "BEP"
                    pnl_gross = -sl_pts if not bep_activated else 0.20
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_pts
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS" if not bep_activated else "BEP"
                    pnl_gross = -sl_pts if not bep_activated else 0.20
                    held_bars = step
                    break
            else:
                hit_tp = l_bar <= tp_p
                hit_sl = h_bar >= cur_sl
                if hit_tp and hit_sl:
                    outcome = "LOSS" if not bep_activated else "BEP"
                    pnl_gross = -sl_pts if not bep_activated else 0.20
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_pts
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS" if not bep_activated else "BEP"
                    pnl_gross = -sl_pts if not bep_activated else 0.20
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        if sig == 'BUY':
            trades_buy.append(pnl_net)
        else:
            trades_sell.append(pnl_net)
        active_until = i + held_bars
        
    tb = np.array(trades_buy)
    ts = np.array(trades_sell)
    all_t = np.concatenate([tb, ts]) if len(tb) > 0 and len(ts) > 0 else (tb if len(tb) > 0 else ts)
    
    wr_b = (tb > 0).mean() * 100.0 if len(tb) > 0 else 0.0
    wr_s = (ts > 0).mean() * 100.0 if len(ts) > 0 else 0.0
    wr_all = (all_t > 0).mean() * 100.0 if len(all_t) > 0 else 0.0
    
    pnl_b = tb.sum() if len(tb) > 0 else 0.0
    pnl_s = ts.sum() if len(ts) > 0 else 0.0
    tot_pnl = all_t.sum() if len(all_t) > 0 else 0.0
    
    gw = all_t[all_t > 0].sum() if (all_t > 0).sum() > 0 else 0.0
    gl = abs(all_t[all_t < 0].sum()) if (all_t < 0).sum() > 0 else 1.0
    pf = (gw / gl) if gl > 0 else 99.0
    
    eq = np.cumsum(np.insert(all_t, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    
    return len(all_t), len(tb), len(ts), wr_all, wr_b, wr_s, tot_pnl, pnl_b, pnl_s, pf, dd

print("\n--- 2. PENGUJIAN TARGET TP $6.50 VS BERBAGAI VARIAN EXIT ---")
cases = [
    {"Nama": "TP $6.50 / SL $6.50 (RRR 1:1)", "TP": 6.50, "SL": 6.50, "BEP": False},
    {"Nama": "TP $6.50 / SL $8.50 (RRR Asimetris Terbalik)", "TP": 6.50, "SL": 8.50, "BEP": False},
    {"Nama": "TP $6.50 / SL $6.50 + Auto-BEP ($4)", "TP": 6.50, "SL": 6.50, "BEP": True},
    {"Nama": "TP $8.50 / SL $6.50 (Optimal Adaptif)", "TP": 8.50, "SL": 6.50, "BEP": False},
    {"Nama": "TP $12.00 / SL $6.00 (Sniper RRR 1:2)", "TP": 12.00, "SL": 6.00, "BEP": False},
]

for c in cases:
    n_all, nb, ns, wr, wrb, wrs, pnl, pnlb, pnls, pf, dd = run_detailed_simulation(c["TP"], c["SL"], thresh=0.65, use_bep=c["BEP"])
    print(f"{c['Nama']:<45} | Trades={n_all} (B:{nb}, S:{ns}) | WR={wr:5.2f}% (B:{wrb:.1f}%, S:{wrs:.1f}%) | PnL=${pnl:+7.2f} USD (B:${pnlb:+.1f}, S:${pnls:+.1f}) | PF={pf:4.2f} | DD=${dd:5.2f}")

# 3. STRATEGI MENINGKATKAN FREKUENSI TRADING (300-600 TRADES DENGAN WR TINGGI)
print("\n--- 3. EKSPLORASI TEKNIK: BAGAIMANA MENCAPAI 300-600 TRADE DENGAN WR TINGGI? ---")
# Teknik A: Threshold 58% + Filter Jam Sesi London/New York (14:00-23:00 WIB)
hour = test_df.index.hour
is_active_session = ((hour >= 7) & (hour <= 17)) # 07:00-17:00 UTC = 14:00-24:00 WIB

def run_session_adaptive_simulation(thresh=0.58, tp_pts=7.50, sl_pts=5.00):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    sessions = np.array(is_active_session)
    n = len(closes)
    
    trades = []
    active_until = -1
    max_bars = 20
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
        # Hanya trading di Sesi London & New York
        if not sessions[i]:
            continue
            
        pb = probs_up[i]
        ps = probs_dn[i]
        c = max(pb, ps)
        
        if c < thresh:
            continue
            
        sig = 'BUY' if pb >= 0.5 else 'SELL'
        entry_p = closes[i]
        tp_p = entry_p + tp_pts if sig == 'BUY' else entry_p - tp_pts
        sl_p = entry_p - sl_pts if sig == 'BUY' else entry_p + sl_pts
        
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            if sig == 'BUY':
                if h_bar >= tp_p:
                    pnl_gross = tp_pts
                    held_bars = step
                    break
                elif l_bar <= sl_p:
                    pnl_gross = -sl_pts
                    held_bars = step
                    break
            else:
                if l_bar <= tp_p:
                    pnl_gross = tp_pts
                    held_bars = step
                    break
                elif h_bar >= sl_p:
                    pnl_gross = -sl_pts
                    held_bars = step
                    break
                    
        if step == max_bars and pnl_gross == 0.0:
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    trades = np.array(trades)
    wr = (trades > 0).mean() * 100.0 if len(trades) > 0 else 0.0
    tot_pnl = trades.sum() if len(trades) > 0 else 0.0
    return len(trades), wr, tot_pnl

n_tr58, wr58, pnl58 = run_session_adaptive_simulation(thresh=0.58, tp_pts=7.50, sl_pts=5.00)
n_tr55, wr55, pnl55 = run_session_adaptive_simulation(thresh=0.55, tp_pts=6.50, sl_pts=5.00)
print(f"Teknik A (Sesi London/NY, Thresh >= 58%, TP $7.5 / SL $5) : Trades={n_tr58} | Win Rate={wr58:.2f}% | PnL=${pnl58:+.2f} USD")
print(f"Teknik B (Sesi London/NY, Thresh >= 55%, TP $6.5 / SL $5) : Trades={n_tr55} | Win Rate={wr55:.2f}% | PnL=${pnl55:+.2f} USD")
