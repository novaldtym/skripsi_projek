import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score, log_loss, brier_score_loss
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*110)
print("AUDIT RISET SKRIPSI: EVOLUSI GENERASI LIGHTGBM (V1.0 s/d V5.0) & ABLASI FITUR ORDER BLOCK (OB)")
print("PENGUJIAN HEAD-TO-HEAD: LEAKAGE vs CLEAN vs DROP OB (TANPA FITUR OB)")
print("METRIK ML LENGKAP & METRIK FINANSIAL RIIL (MODAL $500 USD, LOT 0.01, SPREAD $0.20)")
print("="*110)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Mengambil 25,000 candle historis {symbol} dari MT5...")
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
    print("Mengambil DXY dari Yahoo Finance...")
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()
print(f"Data M15 berhasil dimuat: {len(df_raw)} candle ({df_raw.index[0]} s/d {df_raw.index[-1]}).")

def extract_features(df_in, df_h1_in, df_h4_in, dxy_in, use_leakage=False):
    df = df_in.copy()
    df_h1_loc = df_h1_in.copy()
    df_h4_loc = df_h4_in.copy()
    
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
    
    if use_leakage:
        # Rumus lama: shift(-2) mengintip 2 candle masa depan
        impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
        impulse_dn = (df['close'] - df['close'].shift(-2)) > (1.5 * (df['high'] - df['low']))
        df['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
        df['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)
    else:
        # Rumus kausal murni: shift(2) ke masa lalu
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

    df['DXY_Close'] = dxy_in.reindex(df.index, method='ffill').bfill()
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

    h1_close_series = df_h1_loc['close'] if use_leakage else df_h1_loc['close'].shift(1)
    h4_close_series = df_h4_loc['close'] if use_leakage else df_h4_loc['close'].shift(1)
    
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

    # Fitur Geometris & Struktural v5.0
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
        elif sh[i] < -0.06 and abs(sl[i]) <= 0.15: p_code[i] = 2
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

    # Target 75 Menit (5 lilin M15)
    h = 5
    df['Target_Dir'] = (df['close'].shift(-h) > df['close']).astype(int)
    
    return df

print("\n[1/3] Menyiapkan Dataset Bersih (Clean) dan Bocor (Leakage)...")
df_clean_all = extract_features(df_raw, df_h1, df_h4, dxy_close, use_leakage=False)
df_leak_all  = extract_features(df_raw, df_h1, df_h4, dxy_close, use_leakage=True)

# Definisi Fitur Bertingkat (Generasi V1 s/d V5)
v1_cols = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio',
    'RSI_14', 'BB_Bandwidth', 'BB_Pos',
    'XAU_Return_1', 'XAU_Return_3', 'Volume_Ratio', 'ATR_14'
]

v2_cols = v1_cols + [
    'XAU_Return_5', 'XAU_Return_10',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear', 'ADX_14'
]

v3_cols = v2_cols + [
    'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week'
]

v4_cols = v3_cols + [
    'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'XAU_Return_20'
]

v5_cols = v4_cols + [
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

# Ablasi: V5 TANPA Order Block
v5_no_ob_cols = [c for c in v5_cols if c not in ['Order_Block_Bull', 'Order_Block_Bear']]

print(f"Jumlah Fitur V1      : {len(v1_cols)}")
print(f"Jumlah Fitur V2      : {len(v2_cols)}")
print(f"Jumlah Fitur V3      : {len(v3_cols)}")
print(f"Jumlah Fitur V4      : {len(v4_cols)}")
print(f"Jumlah Fitur V5      : {len(v5_cols)}")
print(f"Jumlah Fitur V5-NoOB : {len(v5_no_ob_cols)}")

# Bersihkan Bar NaN
h = 5
df_clean_valid = df_clean_all.dropna(subset=v5_cols + ['Target_Dir', 'ATR_14']).copy()
df_leak_valid  = df_leak_all.dropna(subset=v5_cols + ['Target_Dir', 'ATR_14']).copy()

# Sync index
common_idx = df_clean_valid.index.intersection(df_leak_valid.index)
df_clean_valid = df_clean_valid.loc[common_idx]
df_leak_valid  = df_leak_valid.loc[common_idx]

split_idx = int(len(df_clean_valid) * 0.80)
train_clean = df_clean_valid.iloc[:split_idx - h].copy()
test_clean  = df_clean_valid.iloc[split_idx:].copy()

train_leak = df_leak_valid.iloc[:split_idx - h].copy()
test_leak  = df_leak_valid.iloc[split_idx:].copy()

print(f"Data Bersih: Train={len(train_clean)}, Test={len(test_clean)}")
print(f"Data Bocor : Train={len(train_leak)}, Test={len(test_leak)}")

# ENGINE TRADING STANDAR SKRIPSI (MODAL $500, LOT 0.01, SPREAD $0.20)
def simulate_trading(test_df, probs, thresh=0.65, mode="sniper_rrr2"):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    n = len(closes)
    
    trades = []
    active_until = -1
    max_bars = 30
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        pb = probs[i]
        ps = 1.0 - pb
        conf = max(pb, ps)
        
        if conf < thresh:
            continue
            
        sig = 'BUY' if pb >= 0.5 else 'SELL'
        entry_p = closes[i]
        
        if mode == "sniper_rrr2":
            tp_dist = 12.00
            sl_dist = 6.00
        elif mode == "pure_75m":
            exit_p = closes[min(i + 5, n - 1)]
            pnl_gross = (exit_p - entry_p) if sig == 'BUY' else (entry_p - exit_p)
            pnl_net = (pnl_gross * 1.0) - SPREAD
            trades.append(pnl_net)
            active_until = i + 5
            continue
            
        tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        sl_p = entry_p - sl_dist if sig == 'BUY' else entry_p + sl_dist
        
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            if sig == 'BUY':
                hit_tp = h_bar >= tp_p
                hit_sl = l_bar <= sl_p
                if hit_tp and hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
            else:
                hit_tp = l_bar <= tp_p
                hit_sl = h_bar >= sl_p
                if hit_tp and hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_trades = len(trades)
    if n_trades == 0:
        return 0, 0.0, 0.0, 0.0, 0.0
        
    wins = (trades > 0).sum()
    wr = (wins / n_trades) * 100.0
    tot_pnl = trades.sum()
    
    gross_win = trades[trades > 0].sum()
    gross_loss = abs(trades[trades < 0].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0
    
    equity = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min())
    
    return n_trades, wr, tot_pnl, pf, max_dd

# Hyperparameter Tuned
lgb_tuned_params = dict(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)

xgb_tuned_params = dict(
    n_estimators=800, learning_rate=0.015, max_depth=4,
    subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, scale_pos_weight=1.0,
    random_state=42, n_jobs=-1, eval_metric='logloss'
)

rf_tuned_params = dict(
    n_estimators=500, max_depth=8, min_samples_split=20,
    min_samples_leaf=10, max_features='sqrt',
    class_weight='balanced', random_state=42, n_jobs=-1
)

logreg_tuned_params = dict(
    C=0.01, penalty='l2', class_weight='balanced',
    solver='liblinear', random_state=42
)

# DAFTAR EKSPERIMEN LENGKAP
experiments = [
    # --- EVOLUSI GENERASI LIGHTGBM ---
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V1.0 (Baseline Awal)",
        "Features_Name": "10 Fitur Dasar",
        "Features": v1_cols,
        "Type": "Baseline",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V2.0 (Indikator + MTF)",
        "Features_Name": "25 Fitur Klasik",
        "Features": v2_cols,
        "Type": "Baseline",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V3.0 (SMC Awal + News)",
        "Features_Name": "37 Fitur SMC",
        "Features": v3_cols,
        "Type": "Early Tuned",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31, random_state=42, n_jobs=-1, verbose=-1),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V4.0 (Leakage 44 Fitur)",
        "Features_Name": "44 Fitur (OB Bocor)",
        "Features": v4_cols,
        "Type": "Tuned",
        "Data_Type": "Leakage",
        "Estimator": LGBMClassifier(**lgb_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V4.2 (Clean 44 Fitur)",
        "Features_Name": "44 Fitur (OB Kausal)",
        "Features": v4_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(**lgb_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V5.0 (Clean 57 Fitur)",
        "Features_Name": "57 Fitur End-to-End",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(**lgb_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Evolusi LightGBM",
        "Model_Name": "LightGBM V5.0 (Leakage 57 Fitur)",
        "Features_Name": "57 Fitur (OB Bocor)",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Leakage",
        "Estimator": LGBMClassifier(**lgb_tuned_params),
        "Is_Pipeline": False
    },
    # --- ABLASI FITUR ORDER BLOCK (OB) ---
    {
        "Group": "Ablasi Fitur OB",
        "Model_Name": "LightGBM V5.0 Tanpa OB (Ablasi)",
        "Features_Name": "55 Fitur (OB Dihapus)",
        "Features": v5_no_ob_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": LGBMClassifier(**lgb_tuned_params),
        "Is_Pipeline": False
    },
    # --- MODEL PEMBANDING LAIN (BASELINE & TUNED) ---
    {
        "Group": "Model Pembanding",
        "Model_Name": "XGBoost Baseline (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Baseline",
        "Data_Type": "Clean",
        "Estimator": XGBClassifier(random_state=42, n_jobs=-1, eval_metric='logloss'),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "XGBoost Tuned (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": XGBClassifier(**xgb_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "XGBoost Tuned (Leakage)",
        "Features_Name": "57 Fitur Leakage",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Leakage",
        "Estimator": XGBClassifier(**xgb_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Random Forest Baseline (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Baseline",
        "Data_Type": "Clean",
        "Estimator": RandomForestClassifier(random_state=42, n_jobs=-1),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Random Forest Tuned (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": RandomForestClassifier(**rf_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Random Forest Tuned (Leakage)",
        "Features_Name": "57 Fitur Leakage",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Leakage",
        "Estimator": RandomForestClassifier(**rf_tuned_params),
        "Is_Pipeline": False
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Logistic Regression Baseline (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Baseline",
        "Data_Type": "Clean",
        "Estimator": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
        "Is_Pipeline": True
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Logistic Regression Tuned (Clean)",
        "Features_Name": "57 Fitur Clean",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Clean",
        "Estimator": make_pipeline(StandardScaler(), LogisticRegression(**logreg_tuned_params)),
        "Is_Pipeline": True
    },
    {
        "Group": "Model Pembanding",
        "Model_Name": "Logistic Regression Tuned (Leakage)",
        "Features_Name": "57 Fitur Leakage",
        "Features": v5_cols,
        "Type": "Tuned",
        "Data_Type": "Leakage",
        "Estimator": make_pipeline(StandardScaler(), LogisticRegression(**logreg_tuned_params)),
        "Is_Pipeline": True
    }
]

print(f"\n[2/3] Memulai Pelatihan dan Evaluasi {len(experiments)} Konfigurasi Eksperimen...")

results_summary = []
ob_importance_records = []

for idx, exp in enumerate(experiments, 1):
    m_name   = exp["Model_Name"]
    g_name   = exp["Group"]
    feats    = exp["Features"]
    d_type   = exp["Data_Type"]
    clf      = exp["Estimator"]
    
    print(f"\n[{idx:02d}/{len(experiments):02d}] Melatih: {m_name} ({len(feats)} fitur, {d_type})...")
    
    # Pilih dataset
    if d_type == "Leakage":
        tr_df = train_leak
        ts_df = test_leak
    else:
        tr_df = train_clean
        ts_df = test_clean
        
    X_train = tr_df[feats].values
    y_train = tr_df['Target_Dir'].values
    X_test  = ts_df[feats].values
    y_test  = ts_df['Target_Dir'].values
    
    t0 = time.time()
    clf.fit(X_train, y_train)
    t_train = time.time() - t0
    
    probs = clf.predict_proba(X_test)[:, 1]
    preds = (probs >= 0.5).astype(int)
    
    # Metrik ML
    acc_glob = accuracy_score(y_test, preds) * 100.0
    auc = roc_auc_score(y_test, probs)
    loss = log_loss(y_test, probs)
    brier = brier_score_loss(y_test, probs)
    
    # Selektif >= 65%
    conf = np.maximum(probs, 1.0 - probs)
    mask65 = conf >= 0.65
    cov65 = mask65.mean() * 100.0
    n65   = int(mask65.sum())
    if n65 > 0:
        sel_preds = (probs[mask65] >= 0.5).astype(int)
        acc65 = accuracy_score(y_test[mask65], sel_preds) * 100.0
    else:
        acc65 = 0.0
        
    # Metrik Trading (Sniper RRR 1:2)
    tr_snp, wr_snp, pnl_snp, pf_snp, dd_snp = simulate_trading(ts_df, probs, thresh=0.65, mode="sniper_rrr2")
    
    # Metrik Trading (Pure 75M Horizon Exit)
    tr_75m, wr_75m, pnl_75m, pf_75m, dd_75m = simulate_trading(ts_df, probs, thresh=0.65, mode="pure_75m")
    
    # Feature Importance jika Tree Model
    ob_imp_pct = 0.0
    if not exp["Is_Pipeline"] and hasattr(clf, "feature_importances_"):
        imps = clf.feature_importances_
        tot_imp = imps.sum()
        if tot_imp > 0 and 'Order_Block_Bull' in feats and 'Order_Block_Bear' in feats:
            idx_b = feats.index('Order_Block_Bull')
            idx_s = feats.index('Order_Block_Bear')
            ob_imp = imps[idx_b] + imps[idx_s]
            ob_imp_pct = (ob_imp / tot_imp) * 100.0
            
            # Cari rank OB
            sorted_indices = np.argsort(imps)[::-1]
            rank_b = int(np.where(sorted_indices == idx_b)[0][0]) + 1
            rank_s = int(np.where(sorted_indices == idx_s)[0][0]) + 1
            ob_importance_records.append({
                "Model": m_name,
                "Data_Type": d_type,
                "OB_Total_Importance_Pct": ob_imp_pct,
                "OB_Bull_Rank": rank_b,
                "OB_Bear_Rank": rank_s
            })

    results_summary.append({
        "Kelompok": g_name,
        "Model": m_name,
        "Jumlah_Fitur": len(feats),
        "Tipe_Data": d_type,
        "Varian": exp["Type"],
        "ROC_AUC": round(auc, 4),
        "Log_Loss": round(loss, 4),
        "Brier_Score": round(brier, 4),
        "Akurasi_Global_Pct": round(acc_glob, 2),
        "Akurasi_65_Pct": round(acc65, 2),
        "Cakupan_65_Pct": round(cov65, 2),
        "Jumlah_Bar_65": n65,
        "OB_Importance_Pct": round(ob_imp_pct, 2) if ob_imp_pct > 0 else "-",
        # Trading Sniper RRR 1:2
        "Sniper_Trades": tr_snp,
        "Sniper_WR_Pct": round(wr_snp, 2),
        "Sniper_PnL_USD": round(pnl_snp, 2),
        "Sniper_Profit_Factor": round(pf_snp, 2),
        "Sniper_MaxDD_USD": round(dd_snp, 2),
        # Trading Pure 75M
        "Pure75M_Trades": tr_75m,
        "Pure75M_WR_Pct": round(wr_75m, 2),
        "Pure75M_PnL_USD": round(pnl_75m, 2),
        "Pure75M_Profit_Factor": round(pf_75m, 2),
        "Pure75M_MaxDD_USD": round(dd_75m, 2)
    })
    
    print(f"   -> ML: Acc@65={acc65:.2f}% (Cov={cov65:.1f}%), AUC={auc:.4f}, LogLoss={loss:.4f}")
    print(f"   -> Trading Sniper RRR 1:2: PnL=${pnl_snp:+.2f} USD | WR={wr_snp:.1f}% | PF={pf_snp:.2f} | DD=${dd_snp:.2f}")

print("\n" + "="*110)
print("[3/3] EXPORT DAN VISUALISASI HASIL BENCHMARK")
print("="*110)

df_res = pd.DataFrame(results_summary)
print(df_res[["Model", "Jumlah_Fitur", "Tipe_Data", "ROC_AUC", "Akurasi_65_Pct", "OB_Importance_Pct", "Sniper_WR_Pct", "Sniper_PnL_USD", "Pure75M_PnL_USD"]].to_string(index=False))

# Export Excel
excel_out = r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Komparasi_Lengkap_V1_sd_V5_dan_Ablasi_OrderBlock.xlsx"
with pd.ExcelWriter(excel_out, engine='openpyxl') as writer:
    df_res.to_excel(writer, sheet_name="Master_Komparasi_V1_V5_Ablasi", index=False)
    if ob_importance_records:
        pd.DataFrame(ob_importance_records).to_excel(writer, sheet_name="Ablasi_Order_Block_Importance", index=False)

print(f"\n✅ Berkas Excel berhasil disimpan di:\n   {excel_out}")
