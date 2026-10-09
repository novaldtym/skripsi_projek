import os
import sys
import time
import joblib
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

print("="*85)
print("🚀 PELATIHAN MODEL KHUSUS: LIGHTGBM XAUUSD TIMEFRAME M15 (VERSI 4.0)")
print("44 Fitur Multi-Domain: Makroekonomi News + DXY Ratio + SMC Lengkap + H4 Anchor + ADX + Volume")
print("="*85)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not os.path.exists(MT5_PATH):
    print("❌ MT5 Path tidak ditemukan!")
    sys.exit(1)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5!")
    sys.exit(1)

symbol = "XAUUSD"
if mt5.symbol_info(symbol) is None:
    symbol = "XAUUSDm"
mt5.symbol_select(symbol, True)

print(f"📥 Mengambil 50.000 candle M15, 10.000 H1, dan 5.000 H4 dari MT5 ({symbol})...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 5000)

if rates_m15 is None or len(rates_m15) == 0:
    print("❌ Gagal menarik candle M15 dari MT5!")
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

# Ambil data DXY
print("📥 Mengambil data DXY Intermarket...")
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

print(f"✅ Data M15 Siap: {len(df_m15)} candle ({df_m15.index[0]} s/d {df_m15.index[-1]})")

# =====================================================================
# FEATURE ENGINEERING: 44 FITUR MULTI-DOMAIN (VERSI 4.0)
# =====================================================================
print("⚙️ Memproses 44 Fitur Multi-Domain (Makroekonomi + SMC + MTF H1/H4 + DXY + ADX + Volume)...")

# 1. Geometri Candlestick
range_m15 = (df_m15['high'] - df_m15['low']) + 1e-6
df_m15['Body_Ratio']       = (df_m15['close'] - df_m15['open']).abs() / range_m15
df_m15['Lower_Wick_Ratio'] = (df_m15[['open', 'close']].min(axis=1) - df_m15['low']) / range_m15
df_m15['Upper_Wick_Ratio'] = (df_m15['high'] - df_m15[['open', 'close']].max(axis=1)) / range_m15

# 2. Smart Money Concepts (SMC / ICT)
df_m15['FVG_Bull'] = (df_m15['low'] > df_m15['high'].shift(2)).astype(int)
df_m15['FVG_Bear'] = (df_m15['high'] < df_m15['low'].shift(2)).astype(int)

df_m15['Swing_High_20'] = df_m15['high'].shift(1).rolling(20).max()
df_m15['Swing_Low_20']  = df_m15['low'].shift(1).rolling(20).min()
df_m15['Dist_Support']    = (df_m15['close'] - df_m15['Swing_Low_20']) / df_m15['close']
df_m15['Dist_Resistance'] = (df_m15['Swing_High_20'] - df_m15['close']) / df_m15['close']

df_m15['BOS_Bull']  = (df_m15['close'] > df_m15['Swing_High_20']).astype(int)
df_m15['BOS_Bear']  = (df_m15['close'] < df_m15['Swing_Low_20']).astype(int)

trend_slow = df_m15['close'].pct_change(20)
df_m15['CHoCH_Bull'] = ((df_m15['close'] > df_m15['Swing_High_20']) & (trend_slow < 0)).astype(int)
df_m15['CHoCH_Bear'] = ((df_m15['close'] < df_m15['Swing_Low_20']) & (trend_slow > 0)).astype(int)

df_m15['Liquidity_Sweep_High'] = ((df_m15['high'] > df_m15['Swing_High_20']) & (df_m15['close'] < df_m15['Swing_High_20'])).astype(int)
df_m15['Liquidity_Sweep_Low']  = ((df_m15['low'] < df_m15['Swing_Low_20']) & (df_m15['close'] > df_m15['Swing_Low_20'])).astype(int)

is_bear_c = df_m15['close'] < df_m15['open']
is_bull_c = df_m15['close'] > df_m15['open']
impulse_up = (df_m15['close'].shift(-2) - df_m15['close']) > (1.5 * (df_m15['high'] - df_m15['low']))
impulse_dn = (df_m15['close'] - df_m15['close'].shift(-2)) > (1.5 * (df_m15['high'] - df_m15['low']))
df_m15['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
df_m15['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)

# 3. Fibonacci Retracement
lookback_fibo = 100
roll_high = df_m15['high'].rolling(lookback_fibo).max()
roll_low  = df_m15['low'].rolling(lookback_fibo).min()
roll_range = (roll_high - roll_low) + 1e-6

df_m15['Fibo_Pos_100'] = (df_m15['close'] - roll_low) / roll_range
fibo_382 = roll_high - (roll_range * 0.382)
fibo_500 = roll_high - (roll_range * 0.500)
fibo_618 = roll_high - (roll_range * 0.618)

df_m15['Fibo_Dist_382'] = (df_m15['close'] - fibo_382) / df_m15['close']
df_m15['Fibo_Dist_500'] = (df_m15['close'] - fibo_500) / df_m15['close']
df_m15['Fibo_Dist_618'] = (df_m15['close'] - fibo_618) / df_m15['close']

# 4. Momentum & Volatilitas Teknikal
delta15 = df_m15['close'].diff()
gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
df_m15['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

df_m15['SMA_20'] = df_m15['close'].rolling(20).mean()
df_m15['STD_20'] = df_m15['close'].rolling(20).std()
df_m15['BB_Bandwidth'] = (4 * df_m15['STD_20']) / df_m15['SMA_20']
df_m15['BB_Pos'] = (df_m15['close'] - (df_m15['SMA_20'] - 2*df_m15['STD_20'])) / (4*df_m15['STD_20'] + 1e-6)

df_m15['XAU_Return_1'] = df_m15['close'].pct_change(1)
df_m15['XAU_Return_3'] = df_m15['close'].pct_change(3)
df_m15['XAU_Return_5'] = df_m15['close'].pct_change(5)

# 5. DXY Intermarket & Makroekonomi
df_m15['DXY_Close'] = dxy_close.reindex(df_m15.index, method='ffill').bfill()
df_m15['DXY_Return_1'] = df_m15['DXY_Close'].pct_change(1).fillna(0)
df_m15['DXY_Return_3'] = df_m15['DXY_Close'].pct_change(3).fillna(0)
df_m15['DXY_Trend'] = (df_m15['DXY_Close'] > df_m15['DXY_Close'].rolling(20).mean()).astype(int)
df_m15['XAU_DXY_Ratio_Return'] = (df_m15['close'] / df_m15['DXY_Close']).pct_change(1).fillna(0)

# Makroekonomi News Calendar Proxies
dates = df_m15.index
df_m15['Is_NFP_Week'] = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
df_m15['Is_CPI_Day']  = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
df_m15['Is_FOMC_Week'] = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)

# 6. Multi-Timeframe Trend H1 & H4
df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
df_m15['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
df_m15['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

df_h4['EMA_50_H4'] = df_h4['close'].ewm(span=50, adjust=False).mean()
df_h4['EMA_200_H4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull'] = (df_h4['close'] > df_h4['EMA_50_H4']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)
df_m15['Trend_H4_Bull'] = df_h4['Trend_H4_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
df_m15['Trend_H4_Strong'] = df_h4['Trend_H4_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

# 7. FITUR BARU v4.0: Jarak Numerik dari EMA (bukan binary!) — menangkap KEKUATAN tren
df_h1['H1_Dist_EMA50_raw'] = (df_h1['close'] - df_h1['EMA_50_H1']) / df_h1['close']
df_m15['H1_Dist_EMA50'] = df_h1['H1_Dist_EMA50_raw'].reindex(df_m15.index, method='ffill').fillna(0)

df_h4['H4_Dist_EMA50_raw'] = (df_h4['close'] - df_h4['EMA_50_H4']) / df_h4['close']
df_m15['H4_Dist_EMA50'] = df_h4['H4_Dist_EMA50_raw'].reindex(df_m15.index, method='ffill').fillna(0)

# 8. FITUR BARU v4.0: Consecutive Bullish/Bearish Candle Count — menangkap momentum beruntun
is_bull_seq = (df_m15['close'] > df_m15['open']).astype(int)
is_bear_seq = (df_m15['close'] < df_m15['open']).astype(int)

# Hitung jumlah candle bearish/bullish berturut-turut (streak counter)
consec_bull = []
consec_bear = []
bull_count = 0
bear_count = 0
for i in range(len(df_m15)):
    if is_bull_seq.iloc[i] == 1:
        bull_count += 1
        bear_count = 0
    elif is_bear_seq.iloc[i] == 1:
        bear_count += 1
        bull_count = 0
    else:
        bull_count = 0
        bear_count = 0
    consec_bull.append(bull_count)
    consec_bear.append(bear_count)
df_m15['Consecutive_Bull'] = consec_bull
df_m15['Consecutive_Bear'] = consec_bear

# 9. FITUR BARU v4.0: ADX (Average Directional Index) — kekuatan tren 0-100
tr_m15 = np.maximum(
    df_m15['high'] - df_m15['low'],
    np.maximum(
        (df_m15['high'] - df_m15['close'].shift(1)).abs(),
        (df_m15['low'] - df_m15['close'].shift(1)).abs()
    )
)
plus_dm = np.where(
    (df_m15['high'] - df_m15['high'].shift(1)) > (df_m15['low'].shift(1) - df_m15['low']),
    np.maximum(df_m15['high'] - df_m15['high'].shift(1), 0), 0
)
minus_dm = np.where(
    (df_m15['low'].shift(1) - df_m15['low']) > (df_m15['high'] - df_m15['high'].shift(1)),
    np.maximum(df_m15['low'].shift(1) - df_m15['low'], 0), 0
)
atr_adx = pd.Series(tr_m15, index=df_m15.index).rolling(14).mean()
plus_di = 100 * pd.Series(plus_dm, index=df_m15.index).rolling(14).mean() / (atr_adx + 1e-6)
minus_di = 100 * pd.Series(minus_dm, index=df_m15.index).rolling(14).mean() / (atr_adx + 1e-6)
dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6)
df_m15['ADX_14'] = dx.rolling(14).mean()

# 10. FITUR BARU v4.0: Volume Ratio — konfirmasi breakout/fakeout
if 'tick_volume' in df_m15.columns:
    df_m15['Volume_Ratio'] = df_m15['tick_volume'] / (df_m15['tick_volume'].rolling(20).mean() + 1e-6)
else:
    df_m15['Volume_Ratio'] = 1.0

# 11. FITUR BARU v4.0: Medium/Long-term Returns — menangkap momentum jangka menengah
df_m15['XAU_Return_10'] = df_m15['close'].pct_change(10)
df_m15['XAU_Return_20'] = df_m15['close'].pct_change(20)

# Target Horizon: 5 Candle M15 (75 Menit)
FORWARD_CANDLES = 5
df_m15['Target_Future'] = df_m15['close'].shift(-FORWARD_CANDLES)
df_m15['Target_Dir'] = (df_m15['Target_Future'] > df_m15['close']).astype(int)

features = [
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
    # --- 8 FITUR BARU v4.0 (Trend Strength + Momentum + Volume) ---
    'H1_Dist_EMA50', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ADX_14', 'Volume_Ratio',
    'XAU_Return_10', 'XAU_Return_20'
]

print(f"Total Fitur yang Didaftarkan: {len(features)} Fitur")

df_clean = df_m15[features + ['Target_Dir']].dropna().copy()
df_clean[features] = df_clean[features].astype(float)

# Split 80% Train, 20% Test secara Kronologis
split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

X_train, y_train = train_df[features], train_df['Target_Dir']
X_test,  y_test  = test_df[features],  test_df['Target_Dir']

print(f"📊 Dataset Siap: Total={len(df_clean)} | Train={len(X_train)} | Test={len(X_test)}")

# Training LightGBM v4.0 (Tuned Hyperparameters untuk generalisasi lebih baik)
print("🔥 Melatih LightGBM Classifier M15 v4.0 (Tuned)...")
lgb_m15 = LGBMClassifier(
    n_estimators=800,          # Naik dari 500 untuk lebih banyak boosting rounds
    learning_rate=0.015,       # Turun dari 0.02 untuk konvergensi lebih halus
    max_depth=5,               # Turun dari 6 untuk mencegah overfitting pada noise
    num_leaves=24,             # Turun dari 31 untuk tree yang lebih general
    subsample=0.75,            # Turun sedikit untuk regularisasi
    colsample_bytree=0.75,     # Turun sedikit untuk regularisasi
    min_child_samples=50,      # BARU: Minimal 50 sampel per leaf untuk mencegah overfitting
    reg_alpha=0.1,             # BARU: L1 regularization
    reg_lambda=1.0,            # BARU: L2 regularization
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

lgb_m15.fit(X_train, y_train)

# Evaluasi pada Test Set
y_pred = lgb_m15.predict(X_test)
y_prob = lgb_m15.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_prob)

print("\n" + "="*50)
print("📈 HASIL EVALUASI MODEL LIGHTGBM M15 (TEST SET):")
print("="*50)
print(f"• Accuracy  : {acc*100:.2f}%")
print(f"• Precision : {prec*100:.2f}%")
print(f"• Recall    : {rec*100:.2f}%")
print(f"• F1-Score  : {f1*100:.2f}%")
print(f"• ROC-AUC   : {auc:.4f}")

# Uji Threshold Keyakinan Model
probs_test = lgb_m15.predict_proba(X_test)
p_max = np.maximum(probs_test[:, 0], probs_test[:, 1])

for th in [0.55, 0.58, 0.60, 0.65]:
    mask_th = p_max >= th
    pred_th = np.where(probs_test[:, 1] >= probs_test[:, 0], 1, 0)[mask_th]
    y_test_th = y_test.values[mask_th]
    if len(pred_th) > 0:
        acc_th = accuracy_score(y_test_th, pred_th)
        print(f"🎯 Threshold >= {int(th*100)}%: Win Rate = {acc_th*100:.2f}% ({len(pred_th)} sinyal / {len(y_test)} candle)")

# Simpan Model Baru
output_model_path = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"
joblib.dump(lgb_m15, output_model_path)
print(f"\n💾 Model LightGBM M15 Berhasil Disimpan ke:")
print(f"   📁 {output_model_path}")

mt5.shutdown()
