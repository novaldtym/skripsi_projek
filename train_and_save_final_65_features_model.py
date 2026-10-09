import sys, os, time, warnings, json
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import joblib
from lightgbm import LGBMClassifier

BASE_DIR = r"d:\SKRIPSI INFORMATIKA"
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

print("="*90)
print("🎯 TRAINING DAN SERIALISASI RESMI: MODEL 65 FITUR KANONIKAL M15")
print("(V5.2: SMC Bebas Leakage + MTF + EMA 9/26 + DXY Price Action & SMT POI)")
print("="*90)

if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"📥 Mengambil data MT5: 25.000 candle {symbol} M15, 8.000 H1, 2.500 H4, 25.000 DXY M15...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

mt5.symbol_select("DXY", True)
rates_dxy = mt5.copy_rates_from_pos("DXY", mt5.TIMEFRAME_M15, 0, 25000)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)
df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)

# -----------------------------------------------------------------------------
# 1. FITUR BASELINE KANONIKAL V5.0 (50 FITUR)
# -----------------------------------------------------------------------------
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

df['BOS_Bull'] = (df['close'] > df['Swing_High_20']).astype(int)
df['BOS_Bear'] = (df['close'] < df['Swing_Low_20']).astype(int)
trend_slow = df['close'].pct_change(20)
df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

is_bear_c = df['close'] < df['open']; is_bull_c = df['close'] > df['open']
body_sz = (df['close'] - df['open']).abs()
avg_body = body_sz.rolling(20).mean()
imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
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

# Sinkronisasi DXY M15
dxy_sync = df_dxy.reindex(df.index, method='ffill').bfill()
dxy_c = dxy_sync['close']
dxy_h = dxy_sync['high']
dxy_l = dxy_sync['low']
dxy_o = dxy_sync['open']

df['DXY_Return_1'] = dxy_c.pct_change(1).fillna(0)
df['DXY_Return_3'] = dxy_c.pct_change(3).fillna(0)
df['DXY_Trend'] = (dxy_c > dxy_c.rolling(20).mean()).astype(int)
df['XAU_DXY_Ratio'] = df['close'] / (dxy_c + 1e-6)
df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

day_of_month = df.index.day
weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

h1_close = df_h1['close'].shift(1)
df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull']   = (h1_close > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close - df_h1_loc['EMA_50_H1']) / (h1_close + 1e-9)

h4_close = df_h4['close'].shift(1)
df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull']   = (h4_close > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50']   = (h4_close - df_h4_loc['EMA_50_H4']) / (h4_close + 1e-9)

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)
for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

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

# 6 Fitur Zona XAUUSD (V5.0)
df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

# -----------------------------------------------------------------------------
# 2. FITUR EMA 9/26 M15 (6 FITUR)
# -----------------------------------------------------------------------------
ema9_m15  = df['close'].ewm(span=9, adjust=False).mean()
ema26_m15 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = (ema9_m15 > ema26_m15).astype(int)
df['Dist_EMA9_M15']  = (df['close'] - ema9_m15) / df['close']
df['Dist_EMA26_M15'] = (df['close'] - ema26_m15) / df['close']
df['Spread_EMA_9_26'] = (ema9_m15 - ema26_m15) / df['close']
df['Pullback_EMA_Bull'] = ((df['EMA_9_Cross_26_Bull'] == 1) & (df['low'] <= ema9_m15) & (df['close'] > ema9_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Pullback_EMA_Bear'] = ((df['EMA_9_Cross_26_Bull'] == 0) & (df['high'] >= ema9_m15) & (df['close'] < ema9_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)

# -----------------------------------------------------------------------------
# 3. FITUR DXY PRICE ACTION & SMT POI (9 FITUR)
# -----------------------------------------------------------------------------
dxy_swing_high = dxy_h.shift(1).rolling(20).max()
dxy_swing_low  = dxy_l.shift(1).rolling(20).min()
df['DXY_Dist_Resistance'] = (dxy_swing_high - dxy_c) / dxy_c
df['DXY_Dist_Support']    = (dxy_c - dxy_swing_low) / dxy_c
df['DXY_At_Supply_POI']   = (df['DXY_Dist_Resistance'] <= 0.0010).astype(int)
df['DXY_At_Demand_POI']   = (df['DXY_Dist_Support'] <= 0.0010).astype(int)

dxy_delta = dxy_c.diff()
dxy_gain  = (dxy_delta.where(dxy_delta > 0, 0)).rolling(14).mean()
dxy_loss  = (-dxy_delta.where(dxy_delta < 0, 0)).rolling(14).mean()
df['DXY_RSI_14'] = 100 - (100 / (1 + (dxy_gain / (dxy_loss + 1e-6))))

df['DXY_BOS_Bull'] = (dxy_c > dxy_swing_high).astype(int)
df['DXY_BOS_Bear'] = (dxy_c < dxy_swing_low).astype(int)

xau_ll = df['low'] < df['low'].shift(1).rolling(10).min()
dxy_fail_hh = dxy_h <= dxy_h.shift(1).rolling(10).max()
df['SMT_Divergence_Bull'] = (xau_ll & dxy_fail_hh).astype(int)

xau_hh = df['high'] > df['high'].shift(1).rolling(10).max()
dxy_fail_ll = dxy_l >= dxy_l.shift(1).rolling(10).min()
df['SMT_Divergence_Bear'] = (xau_hh & dxy_fail_ll).astype(int)

# -----------------------------------------------------------------------------
# DAFTAR LENGKAP 65 FITUR
# -----------------------------------------------------------------------------
FINAL_FEATURES_65 = [
    # 1-3. Geometri Lilin
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio',
    # 4-5. SMC Imbalance
    'FVG_Bull', 'FVG_Bear',
    # 6-7. Struktur SNR
    'Dist_Support', 'Dist_Resistance',
    # 8-11. Struktur Tren
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    # 12-13. Likuiditas Sweep
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low',
    # 14-15. Order Block
    'Order_Block_Bull', 'Order_Block_Bear',
    # 16-19. Fibonacci
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    # 20-22. Osilator & Volatilitas
    'RSI_14', 'BB_Bandwidth', 'BB_Pos',
    # 23-25. Return Historis
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    # 26-29. Intermarket DXY Baseline
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    # 30-32. Kalender Makro
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    # 33-38. MTF H1 & H4
    'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50',
    'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50',
    # 39-44. Dinamika Lilin & Indikator
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20',
    # 45-50. Integrasi Zona Spasial
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear',
    # 51-56. EMA 9/26 M15 Ribbon
    'EMA_9_Cross_26_Bull', 'Dist_EMA9_M15', 'Dist_EMA26_M15', 'Spread_EMA_9_26',
    'Pullback_EMA_Bull', 'Pullback_EMA_Bear',
    # 57-65. DXY Price Action & SMT POI
    'DXY_Dist_Resistance', 'DXY_Dist_Support',
    'DXY_At_Supply_POI', 'DXY_At_Demand_POI',
    'DXY_RSI_14', 'DXY_BOS_Bull', 'DXY_BOS_Bear',
    'SMT_Divergence_Bull', 'SMT_Divergence_Bear'
]

print(f"📊 Total Fitur Final: {len(FINAL_FEATURES_65)}")
assert len(FINAL_FEATURES_65) == 65, f"Ekspektasi 65 fitur, dapat {len(FINAL_FEATURES_65)}"

# Target Horizon 75 Menit (5 Bar M15)
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)

# Hapus bar NaN akibat rolling lookback
df_clean = df.dropna(subset=FINAL_FEATURES_65 + ['Target_Dir']).copy()
print(f"Dataset bersih: {len(df_clean)} candle.")

# Latih pada seluruh data historis untuk produksi bot live
X = df_clean[FINAL_FEATURES_65].values
y = df_clean['Target_Dir'].values

print("🧠 Melatih Model LightGBM Kanonikal 65 Fitur...")
lgb_params = dict(
    n_estimators=400,
    learning_rate=0.02,
    num_leaves=31,
    subsample=0.8,
    subsample_freq=1,      # Mengaktifkan row bagging 80% pada setiap iterasi (audit Peneliti A)
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1
)

model = LGBMClassifier(**lgb_params)
model.fit(X, y)
print("✅ Pelatihan selesai.")

# Simpan ke model_m15_zone_integrated_50.pkl dan model_lightgbm_xauusd.pkl
path_p = os.path.join(BASE_DIR, "model_m15_zone_integrated_50.pkl")
path_f = os.path.join(BASE_DIR, "model_lightgbm_xauusd.pkl")
joblib.dump(model, path_p)
joblib.dump(model, path_f)
print(f"💾 Model berhasil disimpan ke:\n  - {path_p}\n  - {path_f}")

# Simpan metadata JSON fitur
meta = {
    "features": FINAL_FEATURES_65,
    "n_features": 65,
    "version": "v5.2_DXY_PriceAction_SMT_65F",
    "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "num_samples": len(df_clean),
    "feature_groups": {
        "zone_spatial": 6,
        "smc_causal": 15,
        "mtf_indicators": 29,
        "ema_ribbon": 6,
        "dxy_pa_smt": 9
    }
}
meta_path = os.path.join(BASE_DIR, "model_features_50_meta.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2)
print(f"📄 Metadata disimpan ke: {meta_path}")

print("🎉 MODEL 65 FITUR SIAP DIGUNAKAN BOT LIVE!")
