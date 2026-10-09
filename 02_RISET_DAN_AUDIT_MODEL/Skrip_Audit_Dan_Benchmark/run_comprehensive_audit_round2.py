import os
import sys
import numpy as np
import pandas as pd
import openpyxl
from sklearn.metrics import (
    accuracy_score, roc_auc_score, log_loss, brier_score_loss, f1_score, precision_score, recall_score
)
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
import MetaTrader5 as mt5
import yfinance as yf
import time

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

print("="*80)
print("RUNNING COMPREHENSIVE EMPIRICAL AUDIT EXPERIMENTS (ROUND 2)")
print("="*80)

# 1. FETCH DATA
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Failed to initialize")
    sys.exit(1)

sym = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Mengambil data {sym} dari MT5...")
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

# DXY
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
print("Data raw berhasil diambil. Memproses feature engineering...")

# 2. FEATURE ENGINEERING (STRICTLY CAUSAL)
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

# CAUSAL ORDER BLOCK (NO FUTURE SHIFT! DELAYED CONFIRMATION AT t):
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

# H1 / H4 (STRICTLY CAUSAL: shift(1) on closed bar!)
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

# 13 FITUR TAMBAHAN (PROMPT M15 PRO)
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
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

df_clean = df.dropna().copy()
print(f"Total bar bersih pasca pembersihan: {len(df_clean)} candle.")

# DEFINISI FITUR
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
    'Trend_H1_Bull', 'Trend_H1_Strong',
    'Trend_H4_Bull', 'Trend_H4_Strong',
    'H1_Dist_EMA50', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ADX_14', 'Volume_Ratio',
    'XAU_Return_10', 'XAU_Return_20'
]

features_57 = features_44 + [
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

# 3. PIPELINE SPLIT: 70% Train, 15% Validation, 15% Test
N = len(df_clean)
train_end = int(N * 0.70)
val_end   = int(N * 0.85)

train_df = df_clean.iloc[:train_end]
val_df   = df_clean.iloc[train_end:val_end]
test_df  = df_clean.iloc[val_end:]

print(f"\n--- DATASET SPLIT ---")
print(f"Train set      : {len(train_df)} bar ({train_df.index[0]} s/d {train_df.index[-1]})")
print(f"Validation set : {len(val_df)} bar ({val_df.index[0]} s/d {val_df.index[-1]})")
print(f"Test set       : {len(test_df)} bar ({test_df.index[0]} s/d {test_df.index[-1]})")

# 4. EKSPERIMEN 1: 44 vs 57 FITUR PADA VALIDATION & TEST
def evaluate_model(model, X_tr, y_tr, X_ev, y_ev):
    model.fit(X_tr, y_tr)
    probs = model.predict_proba(X_ev)[:, 1]
    preds = (probs >= 0.5).astype(int)
    
    auc = roc_auc_score(y_ev, probs)
    loss = log_loss(y_ev, probs)
    brier = brier_score_loss(y_ev, probs)
    acc = accuracy_score(y_ev, preds)
    f1 = f1_score(y_ev, preds)
    
    # Selective accuracy at >=65%
    conf = np.maximum(probs, 1 - probs)
    mask65 = conf >= 0.65
    cov65 = mask65.mean() * 100
    if mask65.sum() > 0:
        sel_preds = (probs[mask65] >= 0.5).astype(int)
        sel_acc = accuracy_score(y_ev[mask65], sel_preds) * 100
    else:
        sel_acc = 0.0
        
    return {
        'AUC': auc, 'LogLoss': loss, 'Brier': brier, 'Accuracy': acc*100,
        'F1': f1*100, 'Acc_65': sel_acc, 'Cov_65': cov65, 'N_65': mask65.sum()
    }

print("\n--- EKSPERIMEN 1: 44 VS 57 FITUR ---")
lgb_tuned_params = dict(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)

model_44 = LGBMClassifier(**lgb_tuned_params)
model_57 = LGBMClassifier(**lgb_tuned_params)

res_44_val = evaluate_model(model_44, train_df[features_44], train_df['Target_Dir'], val_df[features_44], val_df['Target_Dir'])
res_57_val = evaluate_model(model_57, train_df[features_57], train_df['Target_Dir'], val_df[features_57], val_df['Target_Dir'])

res_44_test = evaluate_model(model_44, train_df[features_44], train_df['Target_Dir'], test_df[features_44], test_df['Target_Dir'])
res_57_test = evaluate_model(model_57, train_df[features_57], train_df['Target_Dir'], test_df[features_57], test_df['Target_Dir'])

print(f"Validation 44 Fitur: AUC={res_44_val['AUC']:.4f}, LogLoss={res_44_val['LogLoss']:.4f}, Brier={res_44_val['Brier']:.4f}, Acc@65={res_44_val['Acc_65']:.2f}% (Cov={res_44_val['Cov_65']:.1f}%, N={res_44_val['N_65']})")
print(f"Validation 57 Fitur: AUC={res_57_val['AUC']:.4f}, LogLoss={res_57_val['LogLoss']:.4f}, Brier={res_57_val['Brier']:.4f}, Acc@65={res_57_val['Acc_65']:.2f}% (Cov={res_57_val['Cov_65']:.1f}%, N={res_57_val['N_65']})")

print(f"Test Set 44 Fitur  : AUC={res_44_test['AUC']:.4f}, LogLoss={res_44_test['LogLoss']:.4f}, Brier={res_44_test['Brier']:.4f}, Acc@65={res_44_test['Acc_65']:.2f}% (Cov={res_44_test['Cov_65']:.1f}%, N={res_44_test['N_65']})")
print(f"Test Set 57 Fitur  : AUC={res_57_test['AUC']:.4f}, LogLoss={res_57_test['LogLoss']:.4f}, Brier={res_57_test['Brier']:.4f}, Acc@65={res_57_test['Acc_65']:.2f}% (Cov={res_57_test['Cov_65']:.1f}%, N={res_57_test['N_65']})")

# 5. EKSPERIMEN 2: TABEL THRESHOLD VALIDATION & TEST UNTUK 57 FITUR
thresholds = [0.50, 0.52, 0.55, 0.58, 0.60, 0.63, 0.65, 0.68, 0.70, 0.75]

def get_threshold_table(model, X_ev, y_ev):
    probs = model.predict_proba(X_ev)[:, 1]
    conf = np.maximum(probs, 1 - probs)
    rows = []
    for th in thresholds:
        mask = conf >= th
        n = mask.sum()
        cov = (n / len(y_ev)) * 100
        if n > 0:
            sel_preds = (probs[mask] >= 0.5).astype(int)
            acc = accuracy_score(y_ev[mask], sel_preds) * 100
        else:
            acc = 0.0
        rows.append({'Threshold': f">={int(th*100)}%", 'Accuracy': f"{acc:.2f}%", 'Signals': n, 'Coverage': f"{cov:.2f}%"})
    return pd.DataFrame(rows)

val_th_df  = get_threshold_table(model_57, val_df[features_57], val_df['Target_Dir'])
test_th_df = get_threshold_table(model_57, test_df[features_57], test_df['Target_Dir'])

print("\n--- TABEL THRESHOLD VALIDATION (57 Fitur) ---")
print(val_th_df.to_string(index=False))

print("\n--- TABEL THRESHOLD TEST SET (57 Fitur) ---")
print(test_th_df.to_string(index=False))

# 6. EKSPERIMEN 3: FAIR BENCHMARK (COMPARATOR MODELS TUNED)
print("\n--- EKSPERIMEN 3: FAIR BENCHMARK COMPARATOR (57 FITUR) ---")
xgb_model = XGBClassifier(
    n_estimators=600, learning_rate=0.015, max_depth=5, subsample=0.75, colsample_bytree=0.75,
    random_state=42, n_jobs=-1, eval_metric='logloss'
)
rf_model = RandomForestClassifier(
    n_estimators=300, max_depth=8, min_samples_leaf=20, class_weight='balanced',
    random_state=42, n_jobs=-1
)
lr_model = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)

res_xgb = evaluate_model(xgb_model, train_df[features_57], train_df['Target_Dir'], test_df[features_57], test_df['Target_Dir'])
res_rf  = evaluate_model(rf_model, train_df[features_57], train_df['Target_Dir'], test_df[features_57], test_df['Target_Dir'])
res_lr  = evaluate_model(lr_model, train_df[features_57], train_df['Target_Dir'], test_df[features_57], test_df['Target_Dir'])

benchmark_summary = pd.DataFrame([
    {'Model': 'LightGBM (Tuned)', 'AUC': f"{res_57_test['AUC']:.4f}", 'LogLoss': f"{res_57_test['LogLoss']:.4f}", 'Brier': f"{res_57_test['Brier']:.4f}", 'Acc Global': f"{res_57_test['Accuracy']:.2f}%", 'F1': f"{res_57_test['F1']:.2f}%", 'Acc@65%': f"{res_57_test['Acc_65']:.2f}%", 'Cov@65%': f"{res_57_test['Cov_65']:.2f}%"},
    {'Model': 'XGBoost (Tuned)',  'AUC': f"{res_xgb['AUC']:.4f}",     'LogLoss': f"{res_xgb['LogLoss']:.4f}",     'Brier': f"{res_xgb['Brier']:.4f}",     'Acc Global': f"{res_xgb['Accuracy']:.2f}%",     'F1': f"{res_xgb['F1']:.2f}%",     'Acc@65%': f"{res_xgb['Acc_65']:.2f}%",     'Cov@65%': f"{res_xgb['Cov_65']:.2f}%"},
    {'Model': 'Random Forest (Tuned)', 'AUC': f"{res_rf['AUC']:.4f}", 'LogLoss': f"{res_rf['LogLoss']:.4f}",  'Brier': f"{res_rf['Brier']:.4f}",  'Acc Global': f"{res_rf['Accuracy']:.2f}%",  'F1': f"{res_rf['F1']:.2f}%",  'Acc@65%': f"{res_rf['Acc_65']:.2f}%",  'Cov@65%': f"{res_rf['Cov_65']:.2f}%"},
    {'Model': 'Logistic Regression (Tuned)', 'AUC': f"{res_lr['AUC']:.4f}", 'LogLoss': f"{res_lr['LogLoss']:.4f}", 'Brier': f"{res_lr['Brier']:.4f}", 'Acc Global': f"{res_lr['Accuracy']:.2f}%", 'F1': f"{res_lr['F1']:.2f}%", 'Acc@65%': f"{res_lr['Acc_65']:.2f}%", 'Cov@65%': f"{res_lr['Cov_65']:.2f}%"}
])
print(benchmark_summary.to_string(index=False))

# SIMPAN KE EXCEL
out_file = r"d:\SKRIPSI INFORMATIKA\Hasil_Audit_Putaran_2_Empiris.xlsx"
with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
    pd.DataFrame([
        {'Fitur Set': '44 Fitur (Validation)', **res_44_val},
        {'Fitur Set': '57 Fitur (Validation)', **res_57_val},
        {'Fitur Set': '44 Fitur (Independent Test)', **res_44_test},
        {'Fitur Set': '57 Fitur (Independent Test)', **res_57_test}
    ]).to_excel(writer, sheet_name='44_vs_57_Fitur', index=False)
    
    val_th_df.to_excel(writer, sheet_name='Threshold_Validation', index=False)
    test_th_df.to_excel(writer, sheet_name='Threshold_Test', index=False)
    benchmark_summary.to_excel(writer, sheet_name='Fair_Benchmark_57', index=False)

print(f"\n[SUKSES] Seluruh data eksperimen audit empiris disimpan ke: {out_file}")
