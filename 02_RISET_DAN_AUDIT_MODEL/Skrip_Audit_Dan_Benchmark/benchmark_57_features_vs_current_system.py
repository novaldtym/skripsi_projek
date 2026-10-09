import os
import sys
import time
import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import MetaTrader5 as mt5

print("="*85)
print("EKSPERIMEN RISET: MODEL HYBRID (44 FITUR + FILTER BOT) VS MODEL END-TO-END (57 FITUR)")
print("="*85)

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
# 1. 44 FITUR DASAR EKSISTING
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
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

# -------------------------------------------------------------
# 2. 13 VARIABEL INPUT BARU: POLA GRAFIK, SPASIAL SNR & RISIKO
# -------------------------------------------------------------
print("Mengekstrak 13 Variabel Input Baru (Geometri Pola, Spasial SNR 300 Bar, & RRR)...")

# A. Spasial Multi-Horizon SNR 300 Bar (~3 Hari)
df['Major_Demand_300'] = df['low'].rolling(300).min()
df['Major_Supply_300'] = df['high'].rolling(300).max()
df['Dist_Major_Demand'] = (df['close'] - df['Major_Demand_300']) / df['close']
df['Dist_Major_Supply'] = (df['Major_Supply_300'] - df['close']) / df['close']

# B. Jarak Clearance Benturan (Anti-Collision Clearance)
nearest_min_dist = df[['Dist_Support', 'Dist_Resistance']].min(axis=1)
df['Nearest_Clearance'] = nearest_min_dist - 0.0018  # > 0 berarti aman

# C. Estimasi Risk-to-Reward Ratio (Spasial)
df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)

# D. Kualitas Penolakan Ekor Lilin (Pinbar Rejection Ratio)
df['Pinbar_Ratio'] = df[['Lower_Wick_Ratio', 'Upper_Wick_Ratio']].max(axis=1) / (df['Body_Ratio'] + 1e-5)

# E. Pola Geometri Garis OLS (Slope High & Slope Low over 35 Bars)
# Menghitung sudut kemiringan atap dan lantai secara rolling
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
        
        # OLS fit
        sh, ih = np.polyfit(x, sub_h, 1)
        sl, il = np.polyfit(x, sub_l, 1)
        slope_h[i] = sh
        slope_l[i] = sl
        
        # Convergence
        spread_s = ih - il
        spread_e = (sh * window + ih) - (sl * window + il)
        is_converging = 1.0 if spread_e < (spread_s * 0.75) else 0.0
        conv[i] = (spread_s - spread_e) / (spread_s + 1e-5)
        
        # Pattern Code:
        # 1: Ascending Triangle, 2: Descending Triangle, 3: Symmetrical Triangle, 4: Falling Wedge, 5: Rising Wedge, 6: Channel
        if sl > 0.06 and abs(sh) <= 0.15:
            p_code[i] = 1 # Ascending Triangle
        elif sh < -0.06 and abs(sl) <= 0.15:
            p_code[i] = 2 # Descending Triangle
        elif sh < -0.08 and sl > 0.08:
            p_code[i] = 3 # Symmetrical Triangle
        elif is_converging and sl < -0.30 and sh > -0.30:
            p_code[i] = 4 # Falling Wedge
        elif is_converging and sh > 0.30 and sl < 0.30:
            p_code[i] = 5 # Rising Wedge
        elif sh > 0.10 and sl > 0.10:
            p_code[i] = 6 # Ascending Channel
        elif sh < -0.10 and sl < -0.10:
            p_code[i] = 7 # Descending Channel
        else:
            p_code[i] = 0 # Sideways / Range
            
    return slope_h, slope_l, conv, p_code

sh, sl, conv, p_code = calc_rolling_slopes(df['high'], df['low'], window=35)
df['Pattern_Slope_High'] = sh
df['Pattern_Slope_Low']  = sl
df['Pattern_Convergence'] = conv
df['Pattern_Type_Code']   = p_code

# F. Double Top & Double Bottom Distance
roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']

roll_min1 = df['low'].shift(1).rolling(20).min()
roll_min2 = df['low'].shift(21).rolling(20).min()
df['Double_Bottom_Dist'] = (roll_min1 - roll_min2).abs() / df['close']

# TARGET A: Directional 75m (T+5)
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

df_clean = df.dropna().copy()
print(f"Dataset Bersih: {len(df_clean)} bar M15")

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

new_13_features = [
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20' # Anchor
]

features_57 = features_44 + [
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

print(f"Total Fitur Eksisting: {len(features_44)} Fitur")
print(f"Total Fitur Baru Terintegrasi: {len(features_57)} Fitur (+13 Fitur Baru)")

# TRAIN-TEST SPLIT (80% Train, 20% Test)
split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

# SEQUENTIAL TRADE RESOLUTION ENGINE
def simulate_sequential_trades(df_sub, signal_series, trade_type_series):
    trades = []
    active_until = -1
    
    indices = list(range(len(df_sub) - 40))
    for i in indices:
        if i <= active_until:
            continue
            
        sig = signal_series[i]
        if not sig:
            continue
            
        ttype = trade_type_series[i]
        entry_p = df_sub['close'].iloc[i]
        
        tp_p = entry_p + 6.50 if ttype == 'BUY' else entry_p - 6.50
        sl_p = entry_p - 8.50 if ttype == 'BUY' else entry_p + 8.50
        bep_active = False
        
        res_outcome = 'TIMEOUT'
        res_pnl = 0.0
        
        for j in range(1, 41):
            bar = df_sub.iloc[i + j]
            h, l = bar['high'], bar['low']
            
            if ttype == 'BUY':
                if not bep_active and (h - entry_p) >= 4.00:
                    bep_active = True
                    sl_p = entry_p + 0.20
                if h >= tp_p:
                    res_outcome = 'WIN'
                    res_pnl = 6.50
                    active_until = i + j
                    break
                if l <= sl_p:
                    res_outcome = 'BEP' if bep_active else 'LOSS'
                    res_pnl = 0.20 if bep_active else -8.50
                    active_until = i + j
                    break
            else:
                if not bep_active and (entry_p - l) >= 4.00:
                    bep_active = True
                    sl_p = entry_p - 0.20
                if l <= tp_p:
                    res_outcome = 'WIN'
                    res_pnl = 6.50
                    active_until = i + j
                    break
                if h >= sl_p:
                    res_outcome = 'BEP' if bep_active else 'LOSS'
                    res_pnl = 0.20 if bep_active else -8.50
                    active_until = i + j
                    break
                    
        if res_outcome != 'TIMEOUT':
            trades.append({
                'type': ttype,
                'outcome': res_outcome,
                'pnl': res_pnl,
                'is_win': (res_outcome == 'WIN')
            })
            
    return pd.DataFrame(trades)

# =========================================================================
# MODEL A: SISTEM AKTIF SAAT INI (44 FITUR + FILTER BOT MANUAL)
# =========================================================================
print("\n[A] Melatih Model A (44 Fitur - Sistem Aktif Saat Ini)...")
mA = LGBMClassifier(n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24, class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1)
mA.fit(train_df[features_44], train_df['Target_Dir'])

probs_mA = mA.predict_proba(test_df[features_44])[:, 1]
signals_mA = []
types_mA = []

for i in range(len(test_df)):
    row = test_df.iloc[i]
    pb = probs_mA[i]
    ps = 1.0 - pb
    
    # Filter Manual Bot
    min_snr = min(row['Dist_Support'], row['Dist_Resistance'])
    safe = (min_snr - 0.0018) > 0
    wl = row['Lower_Wick_Ratio']
    wu = row['Upper_Wick_Ratio']
    h4 = row['Trend_H4_Bull']
    
    sig = False
    tt = 'BUY'
    
    if pb >= 0.70 and safe and h4: sig, tt = True, 'BUY'
    elif min_snr <= 0.0015 and pb >= 0.58 and wl >= 0.20 and safe: sig, tt = True, 'BUY'
    elif min_snr <= 0.0040 and pb >= 0.60 and wl >= 0.18 and safe: sig, tt = True, 'BUY'
    elif min_snr > 0.0040 and pb >= 0.65 and h4 and safe: sig, tt = True, 'BUY'
    
    elif ps >= 0.70 and safe and not h4: sig, tt = True, 'SELL'
    elif min_snr <= 0.0015 and ps >= 0.58 and wu >= 0.20 and safe: sig, tt = True, 'SELL'
    elif min_snr <= 0.0040 and ps >= 0.60 and wu >= 0.18 and safe: sig, tt = True, 'SELL'
    elif min_snr > 0.0040 and ps >= 0.65 and not h4 and safe: sig, tt = True, 'SELL'
    
    signals_mA.append(sig)
    types_mA.append(tt)

tdf_A = simulate_sequential_trades(test_df, signals_mA, types_mA)

# =========================================================================
# MODEL B: MODEL END-TO-END 57 FITUR (SEMUA DI MODEL, BOT MURNI EKSEKUTOR)
# =========================================================================
print("\n[B] Melatih Model B (57 Fitur - Pola Grafik & Risiko di dalam Model)...")
mB = LGBMClassifier(n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24, class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1)
mB.fit(train_df[features_57], train_df['Target_Dir'])

probs_mB = mB.predict_proba(test_df[features_57])[:, 1]

# Uji Model B pada threshold keyakinan 58%, 60%, dan 65% (TANPA FILTER BOT SAMA SEKALI)
res_mB = {}
for th in [0.58, 0.60, 0.65]:
    sig_mB = []
    typ_mB = []
    for i in range(len(test_df)):
        pb = probs_mB[i]
        ps = 1.0 - pb
        if pb >= th and pb > ps:
            sig_mB.append(True)
            typ_mB.append('BUY')
        elif ps >= th and ps > pb:
            sig_mB.append(True)
            typ_mB.append('SELL')
        else:
            sig_mB.append(False)
            typ_mB.append('NONE')
    res_mB[th] = simulate_sequential_trades(test_df, sig_mB, typ_mB)

# =========================================================================
# OUTPUT PERBANDINGAN KOMPREHENSIF
# =========================================================================
print("\n" + "="*85)
print("HASIL KOMPARASI STATISTIK EMPIRIS (DATA PASAR M15 XAUUSD)")
print("="*85)

def get_stats(name, df_t):
    n = len(df_t)
    if n == 0:
        return {"Model": name, "Trades": 0, "Win": 0, "BEP": 0, "Loss": 0, "WinRate (%)": 0.0, "Net Profit ($)": 0.0, "Profit Factor": 0.0}
    w = (df_t['outcome'] == 'WIN').sum()
    b = (df_t['outcome'] == 'BEP').sum()
    l = (df_t['outcome'] == 'LOSS').sum()
    wr = (w / (w + l) * 100) if (w + l) > 0 else 0.0
    pnl = round(df_t['pnl'].sum(), 2)
    gw = df_t[df_t['pnl'] > 0]['pnl'].sum()
    gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum())
    pf = round((gw / gl), 2) if gl > 0 else 99.0
    return {"Model": name, "Trades": n, "Win": w, "BEP": b, "Loss": l, "WinRate (%)": round(wr, 1), "Net Profit ($)": pnl, "Profit Factor": pf}

rows = [
    get_stats("Sistem Aktif (44 Fitur + Filter Bot)", tdf_A),
    get_stats("End-to-End 57 Fitur (Threshold >= 58%)", res_mB[0.58]),
    get_stats("End-to-End 57 Fitur (Threshold >= 60%)", res_mB[0.60]),
    get_stats("End-to-End 57 Fitur (Threshold >= 65%)", res_mB[0.65])
]

df_report = pd.DataFrame(rows)
print(df_report.to_string(index=False))

# FEATURE IMPORTANCE TOP 15 DARI 57 FITUR
fi = pd.DataFrame({'Feature': features_57, 'Importance': mB.feature_importances_})
fi = fi.sort_values(by='Importance', ascending=False).reset_index(drop=True)
print("\n" + "="*85)
print("TOP 15 FITUR PALING BERPENGARUH DARI 57 FITUR (MODEL END-TO-END)")
print("="*85)
print(fi.head(15).to_string())

df_report.to_excel("Hasil_Uji_Coba_57_Fitur_vs_44_Fitur.xlsx", index=False)
fi.to_excel("Feature_Importance_57_Fitur.xlsx", index=False)
print("\n[OK] Hasil uji coba diexport ke 'Hasil_Uji_Coba_57_Fitur_vs_44_Fitur.xlsx' dan 'Feature_Importance_57_Fitur.xlsx'")
