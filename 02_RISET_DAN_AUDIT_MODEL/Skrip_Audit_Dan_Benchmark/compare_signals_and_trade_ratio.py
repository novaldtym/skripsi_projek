import os
import sys
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5!")
    sys.exit(1)

symbol = "XAUUSD"
if mt5.symbol_info(symbol) is None:
    symbol = "XAUUSDm"
mt5.symbol_select(symbol, True)

print("="*85)
print("📊 SIMULASI KOMPARATIF: FREKUENSI SINYAL & RASIO TRADE MODEL LAMA VS MODEL BARU (v3.7)")
print("="*85)

def build_features(df_main, df_h1, df_h4, dxy_close=None):
    df = df_main.copy()
    
    # 1. Geometri Candlestick
    range_c = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_c
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_c
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_c

    # 2. Smart Money Concepts (SMC / ICT)
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

    # 3. Fibonacci Retracement
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

    # 4. Momentum & Volatilitas Teknikal
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

    df['SMA_20'] = df['close'].rolling(20).mean()
    df['STD_20'] = df['close'].rolling(20).std()
    df['BB_Bandwidth'] = (4 * df['STD_20']) / df['SMA_20']
    df['BB_Pos'] = (df['close'] - (df['SMA_20'] - 2*df['STD_20'])) / (4*df['STD_20'] + 1e-6)

    df['XAU_Return_1'] = df['close'].pct_change(1)
    df['XAU_Return_3'] = df['close'].pct_change(3)
    df['XAU_Return_5'] = df['close'].pct_change(5)

    # 5. DXY Intermarket & Makroekonomi
    if dxy_close is not None:
        df['DXY_Close'] = dxy_close.reindex(df.index, method='ffill').bfill()
        df['DXY_Return_1'] = df['DXY_Close'].pct_change(1).fillna(0)
        df['DXY_Return_3'] = df['DXY_Close'].pct_change(3).fillna(0)
        df['DXY_Trend'] = (df['DXY_Close'] > df['DXY_Close'].rolling(20).mean()).astype(int)
        df['XAU_DXY_Ratio_Return'] = (df['close'] / df['DXY_Close']).pct_change(1).fillna(0)
    else:
        df['DXY_Return_1'] = -df['XAU_Return_1']
        df['DXY_Return_3'] = -df['XAU_Return_3']
        df['DXY_Trend'] = (df['XAU_Return_3'] < 0).astype(int)
        df['XAU_DXY_Ratio_Return'] = 2 * df['XAU_Return_1']

    # Makro News Calendar Proxies
    dates = df.index
    df['Is_NFP_Week'] = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
    df['Is_CPI_Day']  = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    df['Is_FOMC_Week'] = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)

    # 6. Multi-Timeframe Trend H1 & H4
    df_h1_c = df_h1.copy()
    df_h1_c['EMA_50_H1'] = df_h1_c['close'].ewm(span=50, adjust=False).mean()
    df_h1_c['EMA_200_H1'] = df_h1_c['close'].ewm(span=200, adjust=False).mean()
    df_h1_c['Trend_H1_Bull'] = (df_h1_c['close'] > df_h1_c['EMA_50_H1']).astype(int)
    df_h1_c['Trend_H1_Strong'] = (df_h1_c['EMA_50_H1'] > df_h1_c['EMA_200_H1']).astype(int)
    df['Trend_H1_Bull'] = df_h1_c['Trend_H1_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H1_Strong'] = df_h1_c['Trend_H1_Strong'].reindex(df.index, method='ffill').fillna(0)

    df_h4_c = df_h4.copy()
    df_h4_c['EMA_50_H4'] = df_h4_c['close'].ewm(span=50, adjust=False).mean()
    df_h4_c['EMA_200_H4'] = df_h4_c['close'].ewm(span=200, adjust=False).mean()
    df_h4_c['Trend_H4_Bull'] = (df_h4_c['close'] > df_h4_c['EMA_50_H4']).astype(int)
    df_h4_c['Trend_H4_Strong'] = (df_h4_c['EMA_50_H4'] > df_h4_c['EMA_200_H4']).astype(int)
    df['Trend_H4_Bull'] = df_h4_c['Trend_H4_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H4_Strong'] = df_h4_c['Trend_H4_Strong'].reindex(df.index, method='ffill').fillna(0)

    # Target 5 candle ke depan
    df['Target_Future'] = df['close'].shift(-5)
    df['Target_Dir'] = (df['Target_Future'] > df['close']).astype(int)

    return df

# Ambil data MT5
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 5000)
rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 10000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 2000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1000)

df_m15 = pd.DataFrame(rates_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
df_m15.set_index('time', inplace=True)

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
df_m5.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

# DXY
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 5000)
dxy_close = None
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']

# =============================================================
# EVALUASI M15
# =============================================================
print("\n" + "="*80)
print("1️⃣ ANALISIS FREKUENSI SINYAL DAN RASIO TRADE TIMEFRAME M15:")
print("="*80)

m15_feat_df = build_features(df_m15, df_h1, df_h4, dxy_close)
model_m15 = joblib.load(r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl")
feats_m15 = model_m15.feature_name_

clean_m15 = m15_feat_df[feats_m15 + ['Target_Dir']].dropna().copy()
X_m15 = clean_m15[feats_m15]
y_m15 = clean_m15['Target_Dir']

probs_m15 = model_m15.predict_proba(X_m15)
prob_buy_m15 = probs_m15[:, 1]
prob_sell_m15 = probs_m15[:, 0]
p_max_m15 = np.maximum(prob_buy_m15, prob_sell_m15)
predicted_dir_m15 = np.where(prob_buy_m15 >= prob_sell_m15, 1, 0)

total_c_m15 = len(clean_m15)
days_m15 = total_c_m15 / 96.0  # 96 candle per hari M15 (24 jam)

print(f"Total Candle M15 Dianalisis : {total_c_m15:,} Candle")
print(f"Estimasi Durasi Pasar      : ~{days_m15:.1f} Hari Bursa ({days_m15/5:.1f} Minggu)")
print("-" * 80)
print(f"{'Konfigurasi / Threshold':<32} | {'Jml Sinyal':<10} | {'Sinyal/1k':<10} | {'Sinyal/Hari':<12} | {'Akurasi/WR'}")
print("-" * 80)

for th, label in [
    (0.50, "Baseline (>= 50% Tanpa Filter)"),
    (0.54, "Model v3.5 Lama (>= 54%)"),
    (0.56, "Model v3.6 Lama (>= 56%)"),
    (0.58, "Model v3.7 Zona A (>= 58%)"),
    (0.60, "Model v3.7 Zona B (>= 60%)"),
    (0.65, "Model v3.7 Sniper (>= 65%)")
]:
    mask = p_max_m15 >= th
    cnt = np.sum(mask)
    per_1k = (cnt / total_c_m15) * 1000
    per_day = cnt / days_m15
    wr = np.mean(predicted_dir_m15[mask] == y_m15.values[mask]) * 100 if cnt > 0 else 0.0
    print(f"{label:<32} | {cnt:<10} | {per_1k:<10.1f} | {per_day:<12.1f} | {wr:.2f}%")

# =============================================================
# EVALUASI M5
# =============================================================
print("\n" + "="*80)
print("2️⃣ ANALISIS FREKUENSI SINYAL DAN RASIO TRADE TIMEFRAME M5 (SCALPING):")
print("="*80)

m5_feat_df = build_features(df_m5, df_h1, df_h4, dxy_close)
model_m5 = joblib.load(r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd_m5.pkl")
feats_m5 = model_m5.feature_name_

clean_m5 = m5_feat_df[feats_m5 + ['Target_Dir']].dropna().copy()
X_m5 = clean_m5[feats_m5]
y_m5 = clean_m5['Target_Dir']

probs_m5 = model_m5.predict_proba(X_m5)
prob_buy_m5 = probs_m5[:, 1]
prob_sell_m5 = probs_m5[:, 0]
p_max_m5 = np.maximum(prob_buy_m5, prob_sell_m5)
predicted_dir_m5 = np.where(prob_buy_m5 >= prob_sell_m5, 1, 0)

total_c_m5 = len(clean_m5)
days_m5 = total_c_m5 / 288.0  # 288 candle per hari M5 (24 jam)

print(f"Total Candle M5 Dianalisis  : {total_c_m5:,} Candle")
print(f"Estimasi Durasi Pasar      : ~{days_m5:.1f} Hari Bursa ({days_m5/5:.1f} Minggu)")
print("-" * 80)
print(f"{'Konfigurasi / Threshold':<32} | {'Jml Sinyal':<10} | {'Sinyal/1k':<10} | {'Sinyal/Hari':<12} | {'Akurasi/WR'}")
print("-" * 80)

for th, label in [
    (0.50, "Baseline (>= 50% Tanpa Filter)"),
    (0.56, "Model v3.5 Lama (>= 56%)"),
    (0.60, "Model v3.7 Zona A (>= 60%)"),
    (0.64, "Model v3.7 Zona B (>= 64%)"),
    (0.68, "Model v3.7 Sniper (>= 68%)")
]:
    mask = p_max_m5 >= th
    cnt = np.sum(mask)
    per_1k = (cnt / total_c_m5) * 1000
    per_day = cnt / days_m5
    wr = np.mean(predicted_dir_m5[mask] == y_m5.values[mask]) * 100 if cnt > 0 else 0.0
    print(f"{label:<32} | {cnt:<10} | {per_1k:<10.1f} | {per_day:<12.1f} | {wr:.2f}%")

mt5.shutdown()
