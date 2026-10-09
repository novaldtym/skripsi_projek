"""
=============================================================================
AUDIT FORENSIK KEBOCORAN (LEAKAGE-FREE AUDIT):
1. Verifikasi Kebocoran shift(-2) vs Kausal Murni shift(2)
2. Perbandingan Model Bersih: Clean Baseline 57 vs Clean ICT 72
=============================================================================
"""
import sys, os
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import accuracy_score, precision_score, f1_score, roc_auc_score
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
SYMBOL = "XAUUSD"

print("="*85)
print("[AUDIT FORENSIK] DETEKSI KEBOCORAN SHIFT(-2) & BENCHMARK KAUSAL BERSIH")
print("="*85)

if not mt5.initialize(path=MT5_PATH):
    mt5.initialize()

if mt5.symbol_info(SYMBOL) is None:
    SYMBOL = "XAUUSDm"
mt5.symbol_select(SYMBOL, True)

print("📥 Mengambil 50.000 candle M15, 10.000 H1, 5.000 H4...")
rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 50000)
rates_h1  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 5000)

df_m15 = pd.DataFrame(rates_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
df_m15.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

sys.path.append(r"d:\SKRIPSI INFORMATIKA")
from Eksekusi_Otomatis_Trading_Bot import extract_57_features, FEATURES_57

df_full = extract_57_features(df_m15, df_h1, df_h4, None)

# CEK APAKAH ADA KEBOCORAN DI ORDER BLOCK
print("\n🔎 MEMERIKSA RUMUS ORDER BLOCK SAAT INI:")
is_bear_c = df_full['close'] < df_full['open']
is_bull_c = df_full['close'] > df_full['open']

# Rumus di Eksekusi_Otomatis_Trading_Bot:
# impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
# INI JELAS SHIFT(-2) = MENGINTIP 2 CANDLE KE DEPAN!

print("⚠️ TEMUAN: Di Eksekusi_Otomatis_Trading_Bot.py line 201-202:")
print("   impulse_up = (df['close'].shift(-2) - df['close']) > ...")
print("   ❌ Fitur Order Block menggunakan shift(-2) -> Mengintip 30 menit ke masa depan!")

# Sekarang kita bersihkan (KAUSAL MURNI TANPA BOCOR):
print("\n🧹 MEMBERSIHKAN KEBOCORAN (MENGUBAH KE KAUSAL MURNI shift(2) DARI MASA LALU)...")
impulse_up_clean = (df_full['close'] - df_full['close'].shift(2)) > (1.5 * (df_full['high'].shift(2) - df_full['low'].shift(2)))
impulse_dn_clean = (df_full['close'].shift(2) - df_full['close']) > (1.5 * (df_full['high'].shift(2) - df_full['low'].shift(2)))
df_full['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up_clean.fillna(False)).astype(int)
df_full['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn_clean.fillna(False)).astype(int)

# Tambahkan Fitur ICT Kausal
hours = df_full.index.hour
df_full['ICT_London_Killzone'] = ((hours >= 8) & (hours <= 12)).astype(int)
df_full['ICT_NY_Killzone']     = ((hours >= 13) & (hours <= 17)).astype(int)
df_full['ICT_Asia_Killzone']   = ((hours >= 1) & (hours <= 6)).astype(int)

lookback_day = 96
pdh = df_full['high'].shift(1).rolling(lookback_day).max()
pdl = df_full['low'].shift(1).rolling(lookback_day).min()

df_full['ICT_Dist_PDH']  = (pdh - df_full['close']) / df_full['close']
df_full['ICT_Dist_PDL']  = (df_full['close'] - pdl) / df_full['close']
df_full['ICT_Sweep_PDH'] = ((df_full['high'] > pdh) & (df_full['close'] < pdh)).astype(int)
df_full['ICT_Sweep_PDL'] = ((df_full['low'] < pdl) & (df_full['close'] > pdl)).astype(int)

df_full['ICT_In_Discount'] = (df_full['Fibo_Pos_100'] < 0.50).astype(int)
df_full['ICT_In_Premium']  = (df_full['Fibo_Pos_100'] > 0.50).astype(int)
df_full['ICT_In_OTE_Buy']  = ((df_full['Fibo_Pos_100'] >= 0.214) & (df_full['Fibo_Pos_100'] <= 0.382)).astype(int)
df_full['ICT_In_OTE_Sell'] = ((df_full['Fibo_Pos_100'] >= 0.618) & (df_full['Fibo_Pos_100'] <= 0.786)).astype(int)

ICT_FEATURES = [
    'ICT_London_Killzone', 'ICT_NY_Killzone', 'ICT_Asia_Killzone',
    'ICT_Dist_PDH', 'ICT_Dist_PDL', 'ICT_Sweep_PDH', 'ICT_Sweep_PDL',
    'ICT_In_Discount', 'ICT_In_Premium', 'ICT_In_OTE_Buy', 'ICT_In_OTE_Sell'
]

ALL_FEATURES_CLEAN = FEATURES_57 + ICT_FEATURES

FORWARD_CANDLES = 5
df_full['Target_Future'] = df_full['close'].shift(-FORWARD_CANDLES)
df_full['Target_Dir'] = (df_full['Target_Future'] > df_full['close']).astype(int)

price_cols = ['open', 'high', 'low', 'close']
df_clean = df_full[ALL_FEATURES_CLEAN + ['Target_Dir'] + price_cols].dropna().copy()

split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

print(f"📊 Dataset Bersih: Train={len(train_df)} | Test={len(test_df)}")

# 1. LATIH MODEL CLEAN BASELINE 57 FITUR
print("\n🏋️ Melatih Model 1: CLEAN BASELINE (57 Fitur Tanpa Leakage)...")
m_base_clean = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    subsample=0.75, colsample_bytree=0.75, min_child_samples=50,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1
)
m_base_clean.fit(train_df[FEATURES_57], train_df['Target_Dir'])

# 2. LATIH MODEL CLEAN ICT 68 FITUR
print("🏋️ Melatih Model 2: CLEAN ICT-ENHANCED (68 Fitur Tanpa Leakage)...")
m_ict_clean = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    subsample=0.75, colsample_bytree=0.75, min_child_samples=50,
    reg_alpha=0.1, reg_lambda=1.0, random_state=42, n_jobs=-1, verbose=-1
)
m_ict_clean.fit(train_df[ALL_FEATURES_CLEAN], train_df['Target_Dir'])

# EVALUASI ML OUT-OF-SAMPLE
y_test = test_df['Target_Dir']
p_base = m_base_clean.predict_proba(test_df[FEATURES_57])
p_ict  = m_ict_clean.predict_proba(test_df[ALL_FEATURES_CLEAN])

auc_b = roc_auc_score(y_test, p_base[:, 1])
auc_i = roc_auc_score(y_test, p_ict[:, 1])

print(f"\n📈 HASIL ROC-AUC PADA DATA BERSIH KAUSAL:")
print(f"   • Clean Baseline 57 Fitur : ROC-AUC = {auc_b:.4f}")
print(f"   • Clean ICT 68 Fitur       : ROC-AUC = {auc_i:.4f}")

# BACKTEST FINANSIAL REALISTIS
SL_POINTS = 6.50
TP_POINTS = 8.50
SPREAD_COST = 0.20

test_closes = test_df['close'].values
test_highs  = test_df['high'].values
test_lows   = test_df['low'].values

def simulate_real(probs):
    trades = []
    in_trade = False
    side = 0
    e_p = 0.0
    e_i = 0
    sl = 0.0
    tp = 0.0

    for i in range(len(test_closes) - 10):
        c = test_closes[i]; h = test_highs[i]; l = test_lows[i]
        p_b = probs[i, 1]; p_s = probs[i, 0]

        if in_trade:
            closed = False
            pnl = 0.0
            if side == 1:
                if l <= sl: pnl = -SL_POINTS - SPREAD_COST; closed = True
                elif h >= tp: pnl = TP_POINTS - SPREAD_COST; closed = True
                elif (i - e_i) >= 5: pnl = (c - e_p) - SPREAD_COST; closed = True
            elif side == -1:
                if h >= sl: pnl = -SL_POINTS - SPREAD_COST; closed = True
                elif l <= tp: pnl = TP_POINTS - SPREAD_COST; closed = True
                elif (i - e_i) >= 5: pnl = (e_p - c) - SPREAD_COST; closed = True
            if closed:
                trades.append(pnl)
                in_trade = False
            continue

        if p_b >= 0.60:
            in_trade = True; side = 1; e_p = c; e_i = i; sl = e_p - SL_POINTS; tp = e_p + TP_POINTS
        elif p_s >= 0.60:
            in_trade = True; side = -1; e_p = c; e_i = i; sl = e_p + SL_POINTS; tp = e_p - TP_POINTS

    trades = np.array(trades)
    if len(trades) == 0: return 0, 0, 0, 0
    wins = trades[trades > 0]
    wr = len(wins) / len(trades) * 100
    pf = wins.sum() / (abs(trades[trades <= 0].sum()) + 1e-6)
    net = trades.sum()
    return len(trades), wr, pf, net

n_b, wr_b, pf_b, net_b = simulate_real(p_base)
n_i, wr_i, pf_i, net_i = simulate_real(p_ict)

print(f"\n📊 HASIL BACKTEST FINANSIAL PADA DATA MURNI KAUSAL (BEBAS BOCOR):")
print(f"   • Clean Baseline (57 Fitur) : {n_b} Trades | WR = {wr_b:.2f}% | PF = {pf_b:.2f} | Net = ${net_b:.2f}")
print(f"   • Clean ICT (68 Fitur)      : {n_i} Trades | WR = {wr_i:.2f}% | PF = {pf_i:.2f} | Net = ${net_i:.2f}")

mt5.shutdown()
