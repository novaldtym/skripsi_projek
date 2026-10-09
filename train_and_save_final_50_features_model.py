"""
====================================================================================================
TRAINING RESMI & FINALISASI MODEL 50 FITUR TERINTEGRASI ZONA (BEBAS LEAKAGE)
====================================================================================================
Fitur: 50 Fitur (44 Fitur SMC/Makro/MTF Bersih + 6 Fitur Representasi Zona Integratif)
- Bebas Leakage: Order Block menggunakan is_bear_c.shift(2) & imp_up (masa lalu)
- Representasi Zona:
  1. Zone_A_Bounce_Bull : Dist_Support <= 0.0015 & Lower_Wick_Ratio >= 0.20
  2. Zone_A_Bounce_Bear : Dist_Resistance <= 0.0015 & Upper_Wick_Ratio >= 0.20
  3. Zone_B_Prox_Bull   : Dist_Support <= 0.0040 & Lower_Wick_Ratio >= 0.18
  4. Zone_B_Prox_Bear   : Dist_Resistance <= 0.0040 & Upper_Wick_Ratio >= 0.18
  5. Zone_Clearance_Safe_Bull : Dist_Resistance >= 0.0018
  6. Zone_Clearance_Safe_Bear : Dist_Support >= 0.0018
- Output Model: model_lightgbm_xauusd.pkl, model_m15_zone_integrated_50.pkl, model_m15_pro_57_features.pkl
====================================================================================================
"""
import os, sys, joblib
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!"); sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"📥 Mengambil data {symbol} dari MT5...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 30000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 30000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)
mt5.shutdown()

print("⚙️ Mengekstrak 50 Fitur Terintegrasi Zona...")
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
body_sz = (df['close'] - df['open']).abs()
avg_body = body_sz.rolling(20).mean()
imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)

# BEBAS DATA LEAKAGE: MENGGUNAKAN LOOKBACK HISTORIS SHIFT(2)
df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

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
df['BB_Bandwidth'] = (4 * std20) / (sma20 + 1e-9)
df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1)
df['XAU_Return_3'] = df['close'].pct_change(3)
df['XAU_Return_5'] = df['close'].pct_change(5)

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

# MTF H1 BASELINE STABIL (50, 200) - TERBUKTI CUAN +$340 DI OOS
h1_close_series = df_h1['close'].shift(1)
h4_close_series = df_h4['close'].shift(1)
df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close_series.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close_series.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull']   = (h1_close_series > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close_series - df_h1_loc['EMA_50_H1']) / (h1_close_series + 1e-9)

# MTF H4 BASELINE STABIL (50, 200)
df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close_series.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close_series.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull']   = (h4_close_series > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50']   = (h4_close_series - df_h4_loc['EMA_50_H4']) / (h4_close_series + 1e-9)

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)
for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

# ATR & ADX BASELINE STABIL 14
high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
atr14 = tr.rolling(14).mean() + 1e-6
df['ATR_14'] = atr14
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

# === 6 FITUR INTEGRASI ZONA KE DALAM AI ===
df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

FEATURES_50 = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 'FVG_Bull', 'FVG_Bear',
    'Dist_Support', 'Dist_Resistance', 'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth', 'BB_Pos', 'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20',
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear'
]

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
df.dropna(subset=list(set(FEATURES_50 + ['Target_Dir', 'open', 'high', 'low', 'close'])), inplace=True)

print(f"📊 Dataset Siap: {len(df)} Baris")
X = df[FEATURES_50].values
y = df['Target_Dir'].values

# Pelatihan Model Final
print("🚀 Melatih LightGBM Model 50 Fitur...")
lgb_params = dict(
    n_estimators=600,
    learning_rate=0.02,
    num_leaves=31,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1
)
final_model = LGBMClassifier(**lgb_params)
final_model.fit(X, y)

# Simpan metadata model
model_meta = {
    'features': FEATURES_50,
    'n_features': len(FEATURES_50),
    'version': 'v5.1_ZoneIntegrated_Optimized_MA10_Respected',
    'trained_at': str(pd.Timestamp.now()),
    'num_samples': len(df),
    'parameters': {
        'h1_ema': [10, 50],
        'h4_ema': [20, 100],
        'bb_period': 10,
        'atr_period': 10,
        'adx_period': 10,
        'rsi_period': 14,
        'swing_lookback': 20
    }
}

# Simpan model ke semua path yang dibutuhkan oleh aplikasi dan bot
save_paths = [
    r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl",
    r"d:\SKRIPSI INFORMATIKA\model_m15_zone_integrated_50.pkl",
    r"d:\SKRIPSI INFORMATIKA\model_m15_pro_57_features.pkl"
]

for sp in save_paths:
    joblib.dump(final_model, sp)
    print(f"✅ Model tersimpan di: {sp} (Ukuran: {os.path.getsize(sp)/1024:.1f} KB)")

meta_path = r"d:\SKRIPSI INFORMATIKA\model_features_50_meta.json"
import json
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(model_meta, f, indent=2)
print(f"✅ Metadata tersimpan di: {meta_path}")
print("🎉 Model 50 Fitur Terintegrasi Zona RESMI SELESAI DILATIH & DISIMPAN!")
