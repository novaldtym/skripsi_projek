"""
=============================================================================
PELATIHAN MODEL KHUSUS: LIGHTGBM XAUUSD M15 (ICT ENHANCED - 70 FITUR)
=============================================================================
Peneliti: Nouval Ditya Maheswara (NIM: 123230165)
Inkorporasi Teori Belajar ICT (Pipsikologi):
1. Killzones (London, New York, Asia) - Time & Price
2. Previous Daily High/Low (PDH / PDL) + Wick Sweep Liquidity
3. Premium vs Discount Zones & Fibonacci OTE (0.705 / 0.786)
4. Unmitigated Fresh FVG Buffer (Stateful Memory POI)
5. Market Structure Shift (MSS) dengan Displacement Candle
6. Daily Bias & External-to-Internal Liquidity Flow
=============================================================================
"""

import os
import sys
import time
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
SYMBOL = "XAUUSD"

print("="*85)
print("🚀 PELATIHAN & KOMPARASI: MODEL BASELINE 57 FITUR VS MODEL ICT-ENHANCED 70 FITUR")
print("="*85)

if not mt5.initialize(path=MT5_PATH):
    if not mt5.initialize():
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)

if mt5.symbol_info(SYMBOL) is None:
    SYMBOL = "XAUUSDm"
mt5.symbol_select(SYMBOL, True)

print(f"📥 Mengambil 50.000 candle M15, 10.000 H1, dan 5.000 H4 dari MT5 ({SYMBOL})...")
rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 50000)
rates_h1  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 5000)

if rates_m15 is None or len(rates_m15) == 0:
    print("❌ Data M15 kosong!")
    sys.exit(1)

df_m15 = pd.DataFrame(rates_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
df_m15.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

print(f"✅ Data Terambil: M15={len(df_m15)} bar ({df_m15.index[0]} s/d {df_m15.index[-1]})")

# Import 57 fitur kanonikal yang sudah ada
sys.path.append(r"d:\SKRIPSI INFORMATIKA")
from Eksekusi_Otomatis_Trading_Bot import extract_57_features, FEATURES_57

print("⚙️ Mengekstrak 57 Fitur Kanonikal Baseline...")
df_full = extract_57_features(df_m15, df_h1, df_h4, None)

# =====================================================================
# INKORPORASI 13 FITUR ICT BARU (BERDASARKAN TEORI_BELAJAR_ICT.MD)
# =====================================================================
print("🧠 Memproses 13 Fitur ICT Tingkat Lanjut (Killzones, PDH/PDL Sweep, OTE, Unmitigated FVG)...")

# 1. ICT TIME & PRICE (Killzones)
# Di MT5 Exness (server time biasanya UTC+2/UTC+3):
# London Killzone: ~08:00 - 12:00 Server Time
# NY Killzone:     ~13:00 - 17:00 Server Time
# Asia Killzone:   ~01:00 - 06:00 Server Time
hours = df_full.index.hour
df_full['ICT_London_Killzone'] = ((hours >= 8) & (hours <= 12)).astype(int)
df_full['ICT_NY_Killzone']     = ((hours >= 13) & (hours <= 17)).astype(int)
df_full['ICT_Asia_Killzone']   = ((hours >= 1) & (hours <= 6)).astype(int)

# 2. PREVIOUS DAILY HIGH/LOW (PDH / PDL) & LIQUIDITY SWEEP (96 candle M15 = 24 Jam)
lookback_day = 96
pdh = df_full['high'].shift(1).rolling(lookback_day).max()
pdl = df_full['low'].shift(1).rolling(lookback_day).min()

df_full['ICT_Dist_PDH']  = (pdh - df_full['close']) / df_full['close']
df_full['ICT_Dist_PDL']  = (df_full['close'] - pdl) / df_full['close']
df_full['ICT_Sweep_PDH'] = ((df_full['high'] > pdh) & (df_full['close'] < pdh)).astype(int)
df_full['ICT_Sweep_PDL'] = ((df_full['low'] < pdl) & (df_full['close'] > pdl)).astype(int)

# 3. PREMIUM VS DISCOUNT ZONES (Fibonacci > 0.5 vs < 0.5)
df_full['ICT_In_Discount'] = (df_full['Fibo_Pos_100'] < 0.50).astype(int)
df_full['ICT_In_Premium']  = (df_full['Fibo_Pos_100'] > 0.50).astype(int)

# 4. OPTIMAL TRADE ENTRY (OTE) FIBONACCI GOLDEN ZONE (0.618 - 0.786)
# Discount OTE (Area Beli Murah: harga retrace 61.8% s/d 78.6% dari High ke Low)
df_full['ICT_In_OTE_Buy']  = ((df_full['Fibo_Pos_100'] >= 0.214) & (df_full['Fibo_Pos_100'] <= 0.382)).astype(int)
# Premium OTE (Area Jual Mahal: harga retrace 61.8% s/d 78.6% dari Low ke High)
df_full['ICT_In_OTE_Sell'] = ((df_full['Fibo_Pos_100'] >= 0.618) & (df_full['Fibo_Pos_100'] <= 0.786)).astype(int)

# 5. MARKET STRUCTURE SHIFT (MSS) DENGAN DISPLACEMENT (Badan Lilin Besar)
avg_body = (df_full['close'] - df_full['open']).abs().rolling(14).mean() + 1e-6
body_now = (df_full['close'] - df_full['open']).abs()
is_displacement = body_now > (1.5 * avg_body)

df_full['ICT_MSS_Bull_Displacement'] = (df_full['BOS_Bull'] == 1) & is_displacement & (df_full['close'] > df_full['open'])
df_full['ICT_MSS_Bear_Displacement'] = (df_full['BOS_Bear'] == 1) & is_displacement & (df_full['close'] < df_full['open'])
df_full['ICT_MSS_Bull_Displacement'] = df_full['ICT_MSS_Bull_Displacement'].astype(int)
df_full['ICT_MSS_Bear_Displacement'] = df_full['ICT_MSS_Bear_Displacement'].astype(int)

# 6. UNMITIGATED / FRESH FVG MEMORY TRACKER (Stateful Rolling Buffer)
print("🧠 Menghitung Unmitigated Fresh FVG Memory Buffer...")
unmitigated_bull_fvg = []
unmitigated_bear_fvg = []
dist_fresh_bull = []
dist_fresh_bear = []

high_vals = df_full['high'].values
low_vals  = df_full['low'].values
close_vals = df_full['close'].values

for i in range(len(df_full)):
    c_p = close_vals[i]
    h_p = high_vals[i]
    l_p = low_vals[i]
    
    # Deteksi pembentukan FVG baru
    if i >= 2:
        if low_vals[i] > high_vals[i-2]: # Bullish FVG
            unmitigated_bull_fvg.append((low_vals[i], high_vals[i-2])) # top, bot
        if high_vals[i] < low_vals[i-2]: # Bearish FVG
            unmitigated_bear_fvg.append((low_vals[i-2], high_vals[i])) # top, bot

    # Evaluasi mitigasi (jika harga sudah menembus/mengisi zona)
    # Hapus FVG Bull jika low menembus dasar FVG
    unmitigated_bull_fvg = [f for f in unmitigated_bull_fvg if l_p > f[1]][-5:]
    # Hapus FVG Bear jika high menembus puncak FVG
    unmitigated_bear_fvg = [f for f in unmitigated_bear_fvg if h_p < f[0]][-5:]

    # Hitung jarak terdekat ke Fresh FVG
    if len(unmitigated_bull_fvg) > 0:
        nearest_b = min(abs(c_p - f[0]) for f in unmitigated_bull_fvg) / c_p
    else:
        nearest_b = 0.05
    dist_fresh_bull.append(nearest_b)

    if len(unmitigated_bear_fvg) > 0:
        nearest_s = min(abs(c_p - f[1]) for f in unmitigated_bear_fvg) / c_p
    else:
        nearest_s = 0.05
    dist_fresh_bear.append(nearest_s)

df_full['ICT_Dist_Fresh_Bull_FVG'] = dist_fresh_bull
df_full['ICT_Dist_Fresh_Bear_FVG'] = dist_fresh_bear

ICT_FEATURES_13 = [
    'ICT_London_Killzone', 'ICT_NY_Killzone', 'ICT_Asia_Killzone',
    'ICT_Dist_PDH', 'ICT_Dist_PDL', 'ICT_Sweep_PDH', 'ICT_Sweep_PDL',
    'ICT_In_Discount', 'ICT_In_Premium', 'ICT_In_OTE_Buy', 'ICT_In_OTE_Sell',
    'ICT_MSS_Bull_Displacement', 'ICT_MSS_Bear_Displacement',
    'ICT_Dist_Fresh_Bull_FVG', 'ICT_Dist_Fresh_Bear_FVG'
]

ALL_FEATURES_72 = FEATURES_57 + ICT_FEATURES_13
print(f"✅ Total Fitur Tergabung: {len(ALL_FEATURES_72)} Fitur (57 Baseline + 15 ICT Features)")

# Target Horizon: 5 Candle M15 (75 Menit / T+5)
FORWARD_CANDLES = 5
df_full['Target_Future'] = df_full['close'].shift(-FORWARD_CANDLES)
df_full['Target_Dir'] = (df_full['Target_Future'] > df_full['close']).astype(int)

price_cols = ['open', 'high', 'low', 'close']
df_clean = df_full[ALL_FEATURES_72 + ['Target_Dir'] + price_cols].dropna().copy()

# Split 80% Train, 20% Test secara Kronologis Murni (Tanpa Kebocoran Masa Depan)
split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

print(f"\n📊 DATASET: Total={len(df_clean)} bars | Train={len(train_df)} | Test={len(test_df)} bars (Out-of-Sample)")

# =====================================================================
# 1. EVALUASI MODEL BASELINE (57 FITUR)
# =====================================================================
print("\n" + "="*85)
print("1️⃣ MELATIH MODEL 1: BASELINE (57 FITUR KANONIKAL)")
print("="*85)

X_train_base, y_train_base = train_df[FEATURES_57], train_df['Target_Dir']
X_test_base,  y_test_base  = test_df[FEATURES_57],  test_df['Target_Dir']

model_baseline = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    subsample=0.75, colsample_bytree=0.75, min_child_samples=50,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1
)
model_baseline.fit(X_train_base, y_train_base)

y_pred_base = model_baseline.predict(X_test_base)
y_prob_base = model_baseline.predict_proba(X_test_base)[:, 1]

acc_base = accuracy_score(y_test_base, y_pred_base)
prec_base = precision_score(y_test_base, y_pred_base)
rec_base = recall_score(y_test_base, y_pred_base)
f1_base = f1_score(y_test_base, y_pred_base)
auc_base = roc_auc_score(y_test_base, y_prob_base)

print(f"• Baseline Accuracy  : {acc_base*100:.2f}%")
print(f"• Baseline Precision : {prec_base*100:.2f}%")
print(f"• Baseline F1-Score  : {f1_base*100:.2f}%")
print(f"• Baseline ROC-AUC   : {auc_base:.4f}")

# Threshold >= 60%
probs_test_base = model_baseline.predict_proba(X_test_base)
p_max_base = np.maximum(probs_test_base[:, 0], probs_test_base[:, 1])
mask_60_base = p_max_base >= 0.60
pred_60_base = np.where(probs_test_base[:, 1] >= probs_test_base[:, 0], 1, 0)[mask_60_base]
y_true_60_base = y_test_base.values[mask_60_base]
acc_60_base = accuracy_score(y_true_60_base, pred_60_base)
print(f"🎯 Threshold >= 60% Win Rate: {acc_60_base*100:.2f}% ({len(pred_60_base)} sinyal terpilih)")

# =====================================================================
# 2. EVALUASI MODEL BARU (72 FITUR: 57 FITUR + ICT ENGINE)
# =====================================================================
print("\n" + "="*85)
print("2️⃣ MELATIH MODEL 2: PROPOSED (72 FITUR KANONIKAL + ICT KNOWLEDGE)")
print("="*85)

X_train_ict, y_train_ict = train_df[ALL_FEATURES_72], train_df['Target_Dir']
X_test_ict,  y_test_ict  = test_df[ALL_FEATURES_72],  test_df['Target_Dir']

model_ict = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    subsample=0.75, colsample_bytree=0.75, min_child_samples=50,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1
)
model_ict.fit(X_train_ict, y_train_ict)

y_pred_ict = model_ict.predict(X_test_ict)
y_prob_ict = model_ict.predict_proba(X_test_ict)[:, 1]

acc_ict = accuracy_score(y_test_ict, y_pred_ict)
prec_ict = precision_score(y_test_ict, y_pred_ict)
rec_ict = recall_score(y_test_ict, y_pred_ict)
f1_ict = f1_score(y_test_ict, y_pred_ict)
auc_ict = roc_auc_score(y_test_ict, y_prob_ict)

print(f"• ICT-Enhanced Accuracy  : {acc_ict*100:.2f}%")
print(f"• ICT-Enhanced Precision : {prec_ict*100:.2f}%")
print(f"• ICT-Enhanced F1-Score  : {f1_ict*100:.2f}%")
print(f"• ICT-Enhanced ROC-AUC   : {auc_ict:.4f}")

probs_test_ict = model_ict.predict_proba(X_test_ict)
p_max_ict = np.maximum(probs_test_ict[:, 0], probs_test_ict[:, 1])
mask_60_ict = p_max_ict >= 0.60
pred_60_ict = np.where(probs_test_ict[:, 1] >= probs_test_ict[:, 0], 1, 0)[mask_60_ict]
y_true_60_ict = y_test_ict.values[mask_60_ict]
acc_60_ict = accuracy_score(y_true_60_ict, pred_60_ict)
print(f"🎯 Threshold >= 60% Win Rate: {acc_60_ict*100:.2f}% ({len(pred_60_ict)} sinyal terpilih)")

# Simpan model baru
OUTPUT_MODEL = r"d:\SKRIPSI INFORMATIKA\model_m15_ict_enhanced.pkl"
joblib.dump(model_ict, OUTPUT_MODEL)
print(f"\n💾 Model ICT-Enhanced Berhasil Disimpan ke: {OUTPUT_MODEL}")

# Top 10 Feature Importance
imp = pd.Series(model_ict.feature_importances_, index=ALL_FEATURES_72).sort_values(ascending=False)
print("\n🏆 TOP 15 FITUR PALING BERPENGARUH PADA MODEL ICT-ENHANCED:")
print(imp.head(15))

# =====================================================================
# 3. BACKTEST FINANCIAL COMPARISON PADA TEST SET (OUT-OF-SAMPLE)
# =====================================================================
print("\n" + "="*85)
print("3️⃣ BACKTEST FINANSIAL PADA DATA TEST MURNI (OUT-OF-SAMPLE 10.000 BAR)")
print("="*85)

test_indices = test_df.index
test_closes  = test_df['close'].values
test_highs   = test_df['high'].values
test_lows    = test_df['low'].values

SL_POINTS = 6.50
TP_POINTS = 8.50
SPREAD_COST = 0.20

def simulate_trades(test_probs):
    trades = []
    in_trade = False
    side = 0
    e_p = 0.0
    e_i = 0
    sl = 0.0
    tp = 0.0

    for i in range(len(test_closes) - 10):
        c = test_closes[i]
        h = test_highs[i]
        l = test_lows[i]
        p_b = test_probs[i, 1]
        p_s = test_probs[i, 0]

        if in_trade:
            closed = False
            pnl = 0.0
            if side == 1:
                if l <= sl:
                    pnl = -SL_POINTS - SPREAD_COST; closed = True
                elif h >= tp:
                    pnl = TP_POINTS - SPREAD_COST; closed = True
                elif (i - e_i) >= 5:
                    pnl = (c - e_p) - SPREAD_COST; closed = True
            elif side == -1:
                if h >= sl:
                    pnl = -SL_POINTS - SPREAD_COST; closed = True
                elif l <= tp:
                    pnl = TP_POINTS - SPREAD_COST; closed = True
                elif (i - e_i) >= 5:
                    pnl = (e_p - c) - SPREAD_COST; closed = True
            if closed:
                trades.append(pnl)
                in_trade = False
            continue

        if p_b >= 0.60:
            in_trade = True; side = 1; e_p = c; e_i = i
            sl = e_p - SL_POINTS; tp = e_p + TP_POINTS
        elif p_s >= 0.60:
            in_trade = True; side = -1; e_p = c; e_i = i
            sl = e_p + SL_POINTS; tp = e_p - TP_POINTS

    trades = np.array(trades)
    if len(trades) == 0:
        return 0, 0.0, 0.0, 0.0
    wins = trades[trades > 0]
    wr = len(wins) / len(trades) * 100
    p_sum = wins.sum()
    l_sum = abs(trades[trades <= 0].sum()) + 1e-6
    pf = p_sum / l_sum
    net = trades.sum()
    return len(trades), wr, pf, net

n_base, wr_b, pf_b, net_b = simulate_trades(probs_test_base)
n_ict, wr_i, pf_i, net_i = simulate_trades(probs_test_ict)

print(f"\n📊 HASIL KOMPARASI FINANCIAL TEST SET:")
print(f"   • BASELINE (57 Fitur)      : {n_base} Trades | Win Rate = {wr_b:.2f}% | PF = {pf_b:.2f} | Net Profit = ${net_b:.2f}")
print(f"   • ICT-ENHANCED (72 Fitur)  : {n_ict} Trades | Win Rate = {wr_i:.2f}% | PF = {pf_i:.2f} | Net Profit = ${net_i:.2f}")

mt5.shutdown()
