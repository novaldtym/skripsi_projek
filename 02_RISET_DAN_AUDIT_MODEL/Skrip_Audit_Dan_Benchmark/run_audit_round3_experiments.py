import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, roc_auc_score, log_loss, brier_score_loss, f1_score, precision_score, recall_score
)
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import MetaTrader5 as mt5
import yfinance as yf

print("="*80)
print("RUNNING ROUND 3 AUDIT EXPERIMENTS: PURGING, BLOCK ROBUSTNESS, MATCHED COVERAGE")
print("="*80)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Failed to initialize")
    sys.exit(1)

sym = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
rates_m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 50000)
rates_h1  = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 15000)
rates_h4  = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 5000)

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 50000)
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

# FEATURE ENGINEERING
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

# CAUSAL ORDER BLOCK
is_bear_c = df['close'] < df['open']
is_bull_c = df['close'] > df['open']
impulse_up_causal = (df['close'] - df['close'].shift(2)) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
impulse_dn_causal = (df['close'].shift(2) - df['close']) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up_causal.fillna(False)).astype(int)
df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn_causal.fillna(False)).astype(int)

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

# H1 / H4 CAUSAL
df_h1['EMA_50_H1']  = df_h1['close'].shift(1).ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].shift(1).ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull']   = (df_h1['close'].shift(1) > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
df_h1['H1_Dist_EMA50']   = (df_h1['close'].shift(1) - df_h1['EMA_50_H1']) / df_h1['close'].shift(1)

df_h4['EMA_50_H4']  = df_h4['close'].shift(1).ewm(span=50, adjust=False).mean()
df_h4['EMA_200_H4'] = df_h4['close'].shift(1).ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull']   = (df_h4['close'].shift(1) > df_h4['EMA_50_H4']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)
df_h4['H4_Dist_EMA50']   = (df_h4['close'].shift(1) - df_h4['EMA_50_H4']) / df_h4['close'].shift(1)

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1[c].reindex(df.index, method='ffill').fillna(0)

for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4[c].reindex(df.index, method='ffill').fillna(0)

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

# 13 FITUR TAMBAHAN
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

# Target 75 Menit
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

df_clean = df.dropna().copy()
print(f"Total bar bersih: {len(df_clean)} candle.")

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

# =========================================================================
# 1. PURGE 5 CANDLES AT BOUNDARIES
# =========================================================================
N = len(df_clean)
raw_train_end = int(N * 0.70)
raw_val_end   = int(N * 0.85)

# Train without last 5 candles (so target doesn't peek into Validation)
train_df = df_clean.iloc[:raw_train_end - 5].copy()
# Validation without last 5 candles (so target doesn't peek into Test)
val_df   = df_clean.iloc[raw_train_end : raw_val_end - 5].copy()
# Test set without last 5 candles (so target Close(t+5) exists)
test_df  = df_clean.iloc[raw_val_end : N - 5].copy()

print(f"\n[PURGED SPLIT]")
print(f"Train Set      : {len(train_df)} bar ({train_df.index[0]} s/d {train_df.index[-1]})")
print(f"Validation Set : {len(val_df)} bar ({val_df.index[0]} s/d {val_df.index[-1]})")
print(f"Test Set       : {len(test_df)} bar ({test_df.index[0]} s/d {test_df.index[-1]})")

# Train LightGBM Tuned
lgb_params = dict(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)
model = LGBMClassifier(**lgb_params)
model.fit(train_df[features_57], train_df['Target_Dir'])

# =========================================================================
# 2. PROBABILITY BASELINES (50/50 & CLASS PRIOR)
# =========================================================================
y_train = train_df['Target_Dir']
p_prior_train = y_train.mean()
print(f"\nTrain Class Distribution: UP = {p_prior_train*100:.2f}%, DOWN = {(1-p_prior_train)*100:.2f}%")

y_test = test_df['Target_Dir']
y_test_pred_prior = np.full(len(y_test), p_prior_train)
y_test_pred_5050  = np.full(len(y_test), 0.50)

logloss_prior = log_loss(y_test, y_test_pred_prior)
brier_prior   = brier_score_loss(y_test, y_test_pred_prior)
logloss_5050  = log_loss(y_test, y_test_pred_5050)
brier_5050    = brier_score_loss(y_test, y_test_pred_5050)

test_probs = model.predict_proba(test_df[features_57])[:, 1]
test_preds = (test_probs >= 0.5).astype(int)
test_auc   = roc_auc_score(y_test, test_probs)
test_ll    = log_loss(y_test, test_probs)
test_brier = brier_score_loss(y_test, test_probs)
test_acc   = accuracy_score(y_test, test_preds)

print(f"\n--- PROBABILITY BASELINE COMPARISON ON TEST SET ---")
print(f"Baseline 50/50       : LogLoss = {logloss_5050:.4f}, Brier = {brier_5050:.4f}")
print(f"Baseline Class Prior : LogLoss = {logloss_prior:.4f}, Brier = {brier_prior:.4f}")
print(f"LightGBM 57 Fitur    : LogLoss = {test_ll:.4f}, Brier = {test_brier:.4f}, AUC = {test_auc:.4f}")

# Threshold curve test
test_conf = np.maximum(test_probs, 1 - test_probs)
mask65 = test_conf >= 0.65
acc65 = accuracy_score(y_test[mask65], (test_probs[mask65] >= 0.5).astype(int)) * 100
cov65 = mask65.mean() * 100
n65   = mask65.sum()

print(f"Purged Test Acc@65%: {acc65:.2f}% (Coverage: {cov65:.2f}%, N={n65} sinyal)")

# =========================================================================
# 3. TIME-BLOCK ROBUSTNESS OF TEST SET (4 BLOCKS)
# =========================================================================
test_df_eval = test_df.copy()
test_df_eval['prob'] = test_probs
test_df_eval['conf'] = test_conf
test_df_eval['pred'] = (test_probs >= 0.5).astype(int)
test_df_eval['is_correct'] = (test_df_eval['pred'] == test_df_eval['Target_Dir']).astype(int)

block_size = len(test_df_eval) // 4
print(f"\n--- TIME-BLOCK ROBUSTNESS ON TEST SET (4 BLOCKS) ---")
for b in range(4):
    start_idx = b * block_size
    end_idx = (b + 1) * block_size if b < 3 else len(test_df_eval)
    sub = test_df_eval.iloc[start_idx:end_idx]
    
    sub_auc = roc_auc_score(sub['Target_Dir'], sub['prob'])
    sub_acc_global = accuracy_score(sub['Target_Dir'], sub['pred']) * 100
    
    sub_mask65 = sub['conf'] >= 0.65
    sub_cov65 = sub_mask65.mean() * 100
    sub_n65 = sub_mask65.sum()
    if sub_n65 > 0:
        sub_acc65 = accuracy_score(sub['Target_Dir'][sub_mask65], sub['pred'][sub_mask65]) * 100
    else:
        sub_acc65 = 0.0
        
    date_start = sub.index[0].strftime('%Y-%m-%d')
    date_end   = sub.index[-1].strftime('%Y-%m-%d')
    days = (sub.index[-1] - sub.index[0]).days or 1
    sig_per_day = sub_n65 / (days * (5/7)) # trading days
    
    print(f"Block {b+1} ({date_start} s/d {date_end}): N={len(sub)} | AUC={sub_auc:.4f} | Acc Global={sub_acc_global:.2f}% | Sinyal@65%={sub_n65} ({sub_cov65:.1f}%, {sig_per_day:.1f}/hari) | Acc@65%={sub_acc65:.2f}%")

# =========================================================================
# 4. MATCHED-COVERAGE COMPARISON (TOP 6.36% CONFIDENCE ACROSS ALL MODELS)
# =========================================================================
print(f"\n--- MATCHED-COVERAGE COMPARISON (TOP 6.36% / N={n65} BARS) ---")

xgb = XGBClassifier(
    n_estimators=600, learning_rate=0.015, max_depth=5, subsample=0.75, colsample_bytree=0.75,
    random_state=42, n_jobs=-1, eval_metric='logloss'
)
rf = RandomForestClassifier(
    n_estimators=300, max_depth=8, min_samples_leaf=20, class_weight='balanced',
    random_state=42, n_jobs=-1
)
lr = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)

xgb.fit(train_df[features_57], train_df['Target_Dir'])
rf.fit(train_df[features_57], train_df['Target_Dir'])
lr.fit(train_df[features_57], train_df['Target_Dir'])

models = {
    'LightGBM (Tuned)': model,
    'XGBoost (Tuned)': xgb,
    'Random Forest (Tuned)': rf,
    'Logistic Regression': lr
}

for name, m in models.items():
    p = m.predict_proba(test_df[features_57])[:, 1]
    c = np.maximum(p, 1 - p)
    # Get top n65 highest confidence indices
    top_indices = np.argsort(c)[-n65:]
    
    matched_preds = (p[top_indices] >= 0.5).astype(int)
    matched_y     = y_test.iloc[top_indices]
    matched_acc   = accuracy_score(matched_y, matched_preds) * 100
    matched_auc   = roc_auc_score(y_test, p)
    print(f"{name:25s}: Matched Acc (Top {n65} bar / 6.36%) = {matched_acc:.2f}% | ROC-AUC = {matched_auc:.4f}")

# Overall signal frequency:
total_test_days = (test_df.index[-1] - test_df.index[0]).days
test_trading_days = total_test_days * (5/7)
print(f"\nTotal Test Days: {total_test_days:.0f} calendar days (~{test_trading_days:.0f} trading days)")
print(f"Total High-Confidence Signals (>=65%): {n65} signals")
print(f"Average Signals per Trading Day: {n65 / test_trading_days:.2f} signals/day (~{n65 / (test_trading_days/5):.1f} signals/week)")

print("\n[SELESAI] Eksekusi eksperimen putaran 3 berhasil.")
