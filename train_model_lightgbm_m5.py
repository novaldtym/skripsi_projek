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

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*85)
print("🚀 PELATIHAN MODEL KHUSUS: LIGHTGBM XAUUSD TIMEFRAME M5 (SCALPING AGRESIF)")
print("28 Fitur SMC/ICT + Fibo + DXY + Trend Guard H1 (Target Horizon: 5 Candle M5 / 25 Menit)")
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

print(f"📥 Mengambil 50.000 candle M5 dan 10.000 candle H1 dari MT5 ({symbol})...")
rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50000)
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)

if rates_m5 is None or len(rates_m5) == 0:
    print("❌ Gagal menarik candle M5 dari MT5!")
    sys.exit(1)

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
df_m5.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

# Ambil data DXY
print("📥 Mengambil data DXY...")
mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M5, 0, 50000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="5m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

print(f"✅ Data berhasil diambil: {len(df_m5)} candle M5 ({df_m5.index[0]} s/d {df_m5.index[-1]})")

# =====================================================================
# FEATURE ENGINEERING: 28 FITUR SMC / ICT & INDIKATOR PADA M5
# =====================================================================
print("⚙️ Melakukan Feature Engineering 28 Fitur SMC/ICT pada Timeframe M5...")

range_m5 = (df_m5['high'] - df_m5['low']) + 1e-6
df_m5['Body_M15'] = (df_m5['close'] - df_m5['open']).abs() / range_m5
df_m5['Lower_Wick_M15'] = (df_m5[['open', 'close']].min(axis=1) - df_m5['low']) / range_m5
df_m5['Upper_Wick_M15'] = (df_m5['high'] - df_m5[['open', 'close']].max(axis=1)) / range_m5

df_m5['FVG_Bull'] = (df_m5['low'] > df_m5['high'].shift(2)).astype(int)
df_m5['FVG_Bear'] = (df_m5['high'] < df_m5['low'].shift(2)).astype(int)

df_m5['Swing_High_20'] = df_m5['high'].shift(1).rolling(20).max()
df_m5['Swing_Low_20']  = df_m5['low'].shift(1).rolling(20).min()
df_m5['Dist_Support']    = (df_m5['close'] - df_m5['Swing_Low_20']) / df_m5['close']
df_m5['Dist_Resistance'] = (df_m5['Swing_High_20'] - df_m5['close']) / df_m5['close']

df_m5['BOS_Bull']  = (df_m5['close'] > df_m5['Swing_High_20']).astype(int)
df_m5['BOS_Bear']  = (df_m5['close'] < df_m5['Swing_Low_20']).astype(int)

trend_slow = df_m5['close'].pct_change(20)
df_m5['CHoCH_Bull'] = ((df_m5['close'] > df_m5['Swing_High_20']) & (trend_slow < 0)).astype(int)
df_m5['CHoCH_Bear'] = ((df_m5['close'] < df_m5['Swing_Low_20']) & (trend_slow > 0)).astype(int)

df_m5['Liquidity_Sweep_High'] = ((df_m5['high'] > df_m5['Swing_High_20']) & (df_m5['close'] < df_m5['Swing_High_20'])).astype(int)
df_m5['Liquidity_Sweep_Low']  = ((df_m5['low'] < df_m5['Swing_Low_20']) & (df_m5['close'] > df_m5['Swing_Low_20'])).astype(int)

is_bear_candle = df_m5['close'] < df_m5['open']
impulse_up = (df_m5['close'].shift(-2) - df_m5['close']) > (1.5 * (df_m5['high'] - df_m5['low']))
df_m5['Order_Block_Bull'] = (is_bear_candle & impulse_up).astype(int)

lookback_fibo = 100
roll_high = df_m5['high'].rolling(lookback_fibo).max()
roll_low  = df_m5['low'].rolling(lookback_fibo).min()
roll_range = (roll_high - roll_low) + 1e-6

df_m5['Fibo_Pos_100'] = (df_m5['close'] - roll_low) / roll_range
fibo_382 = roll_high - (roll_range * 0.382)
fibo_500 = roll_high - (roll_range * 0.500)
fibo_618 = roll_high - (roll_range * 0.618)

df_m5['Fibo_Dist_382'] = (df_m5['close'] - fibo_382) / df_m5['close']
df_m5['Fibo_Dist_500'] = (df_m5['close'] - fibo_500) / df_m5['close']
df_m5['Fibo_Dist_618'] = (df_m5['close'] - fibo_618) / df_m5['close']

delta5 = df_m5['close'].diff()
gain5 = (delta5.where(delta5 > 0, 0)).rolling(14).mean()
loss5 = (-delta5.where(delta5 < 0, 0)).rolling(14).mean()
df_m5['RSI_M15'] = 100 - (100 / (1 + (gain5 / (loss5 + 1e-6))))

df_m5['SMA_20_M15'] = df_m5['close'].rolling(20).mean()
df_m5['STD_20_M15'] = df_m5['close'].rolling(20).std()
df_m5['BB_Bandwidth'] = (4 * df_m5['STD_20_M15']) / df_m5['SMA_20_M15']
df_m5['BB_Pos'] = (df_m5['close'] - (df_m5['SMA_20_M15'] - 2*df_m5['STD_20_M15'])) / (4*df_m5['STD_20_M15'] + 1e-6)

df_m5['XAU_Return_1'] = df_m5['close'].pct_change(1)
df_m5['XAU_Return_3'] = df_m5['close'].pct_change(3)
df_m5['XAU_Return_5'] = df_m5['close'].pct_change(5)

df_m5['DXY_Close'] = dxy_close.reindex(df_m5.index, method='ffill').bfill()
df_m5['DXY_Return_1'] = df_m5['DXY_Close'].pct_change(1).fillna(0)
df_m5['DXY_Return_3'] = df_m5['DXY_Close'].pct_change(3).fillna(0)

df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)

df_m5['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m5.index, method='ffill').fillna(0)
df_m5['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m5.index, method='ffill').fillna(0)

# Target Horizon: 5 candle M5 (25 menit ke depan)
FORWARD_CANDLES = 5
df_m5['Target_Future'] = df_m5['close'].shift(-FORWARD_CANDLES)
df_m5['Target_Dir'] = (df_m5['Target_Future'] > df_m5['close']).astype(int)

features = [
    'Body_M15', 'Lower_Wick_M15', 'Upper_Wick_M15', 
    'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_M15', 'BB_Bandwidth', 'BB_Pos',
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3',
    'Trend_H1_Bull', 'Trend_H1_Strong'
]

df_clean = df_m5[features + ['Target_Dir']].dropna().copy()
df_clean[features] = df_clean[features].astype(float)

# Pembagian data Time-Series (80% Train, 20% Test)
split_idx = int(len(df_clean) * 0.8)
train_df = df_clean.iloc[:split_idx]
test_df  = df_clean.iloc[split_idx:]

X_train, y_train = train_df[features], train_df['Target_Dir']
X_test,  y_test  = test_df[features],  test_df['Target_Dir']

print(f"📊 Dataset Siap: Total = {len(df_clean)} | Train = {len(X_train)} | Test = {len(X_test)}")

# Pelatihan Model LightGBM M5
print("🔥 Melatih LightGBM Classifier M5...")
lgb_m5 = LGBMClassifier(
    n_estimators=300,
    learning_rate=0.03,
    max_depth=6,
    num_leaves=31,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbose=-1
)

lgb_m5.fit(X_train, y_train)

# Evaluasi pada data uji (Test Set)
y_pred = lgb_m5.predict(X_test)
y_prob = lgb_m5.predict_proba(X_test)[:, 1]

acc = accuracy_score(y_test, y_pred)
prec = precision_score(y_test, y_pred)
rec = recall_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_prob)

print("\n" + "="*50)
print("📈 HASIL EVALUASI MODEL LIGHTGBM M5 (TEST SET):")
print("="*50)
print(f"• Accuracy  : {acc*100:.2f}%")
print(f"• Precision : {prec*100:.2f}%")
print(f"• Recall    : {rec*100:.2f}%")
print(f"• F1-Score  : {f1*100:.2f}%")
print(f"• ROC-AUC   : {auc:.4f}")
print("="*50)

# Uji Threshold >= 55% pada data uji M5
probs_test = lgb_m5.predict_proba(X_test)
p_max = np.maximum(probs_test[:, 0], probs_test[:, 1])
mask_55 = p_max >= 0.55
pred_55 = np.where(probs_test[:, 1] >= probs_test[:, 0], 1, 0)[mask_55]
y_test_55 = y_test.values[mask_55]

acc_55 = accuracy_score(y_test_55, pred_55)
print(f"🎯 Akurasi Khusus Sinyal Probabilitas >= 55%: {acc_55*100:.2f}% (Total {len(pred_55)} sinyal dari {len(y_test)} candle uji)")

# Simpan Model ke file terpisah
output_model_path = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd_m5.pkl"
joblib.dump(lgb_m5, output_model_path)
print(f"\n💾 Model LightGBM M5 Berhasil Disimpan ke:")
print(f"   📁 {output_model_path}")

mt5.shutdown()
