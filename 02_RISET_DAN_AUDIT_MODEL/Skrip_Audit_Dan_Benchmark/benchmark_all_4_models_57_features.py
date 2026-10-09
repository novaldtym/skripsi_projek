import os
import sys
import time
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

print("="*105)
print("BENCHMARK MULTI-MODEL KOMPREHENSIF (57 FITUR + PREDIKSI 75M + AI ADAPTIVE SNIPER)")
print("="*105)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Failed")
    sys.exit(1)

symbol = "XAUUSD" if mt5.symbol_info("XAUUSD") else "XAUUSDm"
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 20000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 7000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 20000)
mt5.shutdown()

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_close = df['close'] * 0 + 104.0

# -------------------------------------------------------------
# EKSTRAKSI 57 FITUR LENGKAP
# -------------------------------------------------------------
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
impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
impulse_dn = (df['close'] - df['close'].shift(-2)) > (1.5 * (df['high'] - df['low']))
df['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
df['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)

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

df_h1['EMA_50_H1']  = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull']   = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
df_h1['H1_Dist_EMA50']   = (df_h1['close'] - df_h1['EMA_50_H1']) / df_h1['close']

df_h4['EMA_50_H4']  = df_h4['close'].ewm(span=50, adjust=False).mean()
df_h4['EMA_200_H4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull']   = (df_h4['close'] > df_h4['EMA_50_H4']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)
df_h4['H4_Dist_EMA50']   = (df_h4['close'] - df_h4['EMA_50_H4']) / df_h4['close']

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

# 13 FITUR BARU
df['Major_Demand_300'] = df['low'].rolling(300).min()
df['Major_Supply_300'] = df['high'].rolling(300).max()
df['Dist_Major_Demand'] = (df['close'] - df['Major_Demand_300']) / df['close']
df['Dist_Major_Supply'] = (df['Major_Supply_300'] - df['close']) / df['close']

nearest_min_dist = df[['Dist_Support', 'Dist_Resistance']].min(axis=1)
df['Nearest_Clearance'] = nearest_min_dist - 0.0018
df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)
df['Pinbar_Ratio'] = df[['Lower_Wick_Ratio', 'Upper_Wick_Ratio']].max(axis=1) / (df['Body_Ratio'] + 1e-5)

def calc_rolling_slopes(series_high, series_low, window=35):
    n = len(series_high)
    slope_h = np.zeros(n)
    slope_l = np.zeros(n)
    conv = np.zeros(n)
    p_code = np.zeros(n)
    x = np.arange(window)
    for i in range(window, n):
        sub_h = series_high.iloc[i-window:i].values
        sub_l = series_low.iloc[i-window:i].values
        sh, ih = np.polyfit(x, sub_h, 1)
        sl, il = np.polyfit(x, sub_l, 1)
        slope_h[i] = sh
        slope_l[i] = sl
        spread_s = ih - il
        spread_e = (sh * window + ih) - (sl * window + il)
        is_converging = 1.0 if spread_e < (spread_s * 0.75) else 0.0
        conv[i] = (spread_s - spread_e) / (spread_s + 1e-5)
        if sl > 0.06 and abs(sh) <= 0.15: p_code[i] = 1
        elif sh < -0.06 and abs(sl) <= 0.15: p_code[i] = 2
        elif sh < -0.08 and sl > 0.08: p_code[i] = 3
        elif is_converging and sl < -0.30 and sh > -0.30: p_code[i] = 4
        elif is_converging and sh > 0.30 and sl < 0.30: p_code[i] = 5
        elif sh > 0.10 and sl > 0.10: p_code[i] = 6
        elif sh < -0.10 and sl < -0.10: p_code[i] = 7
        else: p_code[i] = 0
    return slope_h, slope_l, conv, p_code

sh, sl, conv, p_code = calc_rolling_slopes(df['high'], df['low'], window=35)
df['Pattern_Slope_High'] = sh
df['Pattern_Slope_Low']  = sl
df['Pattern_Convergence'] = conv
df['Pattern_Type_Code']   = p_code

roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']

roll_min1 = df['low'].shift(1).rolling(20).min()
roll_min2 = df['low'].shift(21).rolling(20).min()
df['Double_Bottom_Dist'] = (roll_min1 - roll_min2).abs() / df['close']

# TARGET PREDIKSI 5 LILIN (75 MENIT KEDEPAN / T+5)
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
df_clean = df.dropna().copy()

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

split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

X_train = train_df[features_57]
y_train = train_df['Target_Dir']
X_test  = test_df[features_57]
y_test  = test_df['Target_Dir']

print(f"Data Bersih: Train={len(train_df)}, Test={len(test_df)} bar M15")

# -------------------------------------------------------------
# DEFINISI 4 MODEL HASIL HYPERPARAMETER TUNING
# -------------------------------------------------------------
models = {
    "LightGBM (Tuned v4.2)": LGBMClassifier(
        n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
        min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
        reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
        random_state=42, n_jobs=-1, verbose=-1
    ),
    "XGBoost (Tuned)": XGBClassifier(
        n_estimators=500, learning_rate=0.02, max_depth=4,
        subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
        random_state=42, n_jobs=-1, eval_metric='logloss'
    ),
    "Random Forest (Tuned)": RandomForestClassifier(
        n_estimators=300, max_depth=10, min_samples_split=15, min_samples_leaf=5,
        class_weight='balanced', random_state=42, n_jobs=-1
    ),
    "Logistic Regression (Tuned)": make_pipeline(
        StandardScaler(),
        LogisticRegression(C=0.1, penalty='l2', max_iter=1000, random_state=42)
    )
}

# -------------------------------------------------------------
# ENGINE SIMULASI AI ADAPTIVE SNIPER
# (Threshold 60% Entry: Jika Conf >= 65% -> TP $11, SL $6.50; Else -> TP $8.50, SL $6.50)
# -------------------------------------------------------------
def run_sniper_simulation(probs_model):
    active_until = -1
    trades = []
    equity = [0.0]
    
    for i in range(len(test_df) - 40):
        if i <= active_until:
            continue
            
        pb = probs_model[i]
        ps = 1.0 - pb
        
        sig = None
        conf = 0.0
        if pb >= 0.60 and pb > ps:
            sig, conf = 'BUY', pb
        elif ps >= 0.60 and ps > pb:
            sig, conf = 'SELL', ps
            
        if not sig:
            continue
            
        entry_p = test_df['close'].iloc[i]
        
        # Logika AI Adaptive Sniper
        if conf >= 0.65:
            tp_dist = 11.00  # Sniper High-Conviction (RRR 1:1.69)
            sl_dist = 6.50
        else:
            tp_dist = 8.50   # Normal Conviction (RRR 1:1.31)
            sl_dist = 6.50
            
        tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        sl_p = entry_p - sl_dist if sig == 'BUY' else entry_p + sl_dist
        
        outcome = 'TIMEOUT'
        pnl = 0.0
        
        for j in range(1, 41):
            bar = test_df.iloc[i + j]
            h, l = bar['high'], bar['low']
            
            if sig == 'BUY':
                if h >= tp_p:
                    outcome, pnl, active_until = 'WIN', tp_dist, i + j
                    break
                if l <= sl_p:
                    outcome, pnl, active_until = 'LOSS', -sl_dist, i + j
                    break
            else:
                if l <= tp_p:
                    outcome, pnl, active_until = 'WIN', tp_dist, i + j
                    break
                if h >= sl_p:
                    outcome, pnl, active_until = 'LOSS', -sl_dist, i + j
                    break
                    
        if outcome in ['WIN', 'LOSS']:
            trades.append({'outcome': outcome, 'pnl': pnl})
            equity.append(equity[-1] + pnl)
            
    df_t = pd.DataFrame(trades)
    n = len(df_t)
    w = (df_t['outcome'] == 'WIN').sum() if n > 0 else 0
    l = (df_t['outcome'] == 'LOSS').sum() if n > 0 else 0
    wr = (w / n * 100) if n > 0 else 0.0
    net = df_t['pnl'].sum() if n > 0 else 0.0
    gw = df_t[df_t['pnl'] > 0]['pnl'].sum() if n > 0 else 0.0
    gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum()) if n > 0 else 1.0
    pf = (gw / gl) if gl > 0 else 99.0
    
    eq = pd.Series(equity)
    dd = (eq.cummax() - eq).max() if len(eq) > 0 else 0.0
    ev = net / n if n > 0 else 0.0
    
    return n, w, l, wr, net, pf, dd, ev

# -------------------------------------------------------------
# RUN EVALUASI SEMUA MODEL
# -------------------------------------------------------------
results = []

for m_name, model in models.items():
    print(f"\nMelatih & Menguji: {m_name}...")
    t0 = time.time()
    model.fit(X_train, y_train)
    t_train = time.time() - t0
    
    probs = model.predict_proba(X_test)[:, 1]
    
    # 1. Metrik Machine Learning 75M Horizon
    preds_50 = np.where(probs >= 0.5, 1, 0)
    acc_all = accuracy_score(y_test, preds_50) * 100
    auc = roc_auc_score(y_test, probs) * 100
    f1 = f1_score(y_test, preds_50) * 100
    
    # Akurasi pada Zona High-Conviction (P >= 65%)
    max_p = np.maximum(probs, 1.0 - probs)
    mask_65 = max_p >= 0.65
    if mask_65.sum() > 0:
        acc_65 = accuracy_score(y_test[mask_65], preds_50[mask_65]) * 100
        n_65 = mask_65.sum()
    else:
        acc_65 = 0.0
        n_65 = 0
        
    # 2. Eksekusi Finansial Pasar Riil (AI Adaptive Sniper)
    n_tr, w_tr, l_tr, wr_tr, net_pnl, pf, max_dd, ev = run_sniper_simulation(probs)
    
    results.append({
        "Model (57 Fitur)": m_name,
        "Akurasi 75M Global (%)": f"{acc_all:.2f}%",
        "Akurasi Sniper (P>=65%)": f"{acc_65:.2f}% ({n_65} bar)",
        "ROC-AUC (%)": f"{auc:.2f}%",
        "Waktu Train": f"{t_train:.2f}s",
        "Total Trades": n_tr,
        "Win Rate Eksekusi (%)": f"{wr_tr:.1f}%",
        "Menang (WIN)": w_tr,
        "Kalah (LOSS)": l_tr,
        "Net Profit ($)": f"${net_pnl:+8.2f}",
        "Profit Factor": round(pf, 2),
        "Max Drawdown ($)": f"-${max_dd:.2f}",
        "EV / Trade": f"${ev:+.2f}"
    })

df_final = pd.DataFrame(results)
print("\n" + "="*125)
print("HASIL KOMPARASI LENGKAP 4 MODEL (57 FITUR + PREDIKSI 75M + EKSEKUSI AI ADAPTIVE SNIPER)")
print("="*125)
print(df_final.to_string(index=False))

df_final.to_excel("Hasil_Komparasi_4_Model_57_Fitur_Adaptive_Sniper.xlsx", index=False)
print("\n[OK] Seluruh data berhasil diekspor ke 'Hasil_Komparasi_4_Model_57_Fitur_Adaptive_Sniper.xlsx'")
