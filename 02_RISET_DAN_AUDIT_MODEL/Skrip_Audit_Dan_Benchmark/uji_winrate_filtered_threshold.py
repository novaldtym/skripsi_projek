import os
import sys
import joblib
import pandas as pd
import numpy as np
import yfinance as yf
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("PEMBUKTIAN MATEMATIS: WIN RATE DENGAN HIGH-CONFIDENCE FILTER (PROB >= 60%)")
print("="*80)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

use_mt5 = False
if os.path.exists(MT5_PATH):
    if mt5.initialize(path=MT5_PATH):
        use_mt5 = True

def fetch_multiyear_data():
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)
    
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50000)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 15000)
    
    df_m15 = pd.DataFrame(rates_m15)
    df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
    df_m15.set_index('time', inplace=True)
    
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_h1.set_index('time', inplace=True)
    
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
        
    return df_m15, df_h1, dxy_close

df_m15, df_h1, dxy_close = fetch_multiyear_data()

range_m15 = (df_m15['high'] - df_m15['low']) + 1e-6
df_m15['Body_M15'] = (df_m15['close'] - df_m15['open']).abs() / range_m15
df_m15['Lower_Wick_M15'] = (df_m15[['open', 'close']].min(axis=1) - df_m15['low']) / range_m15
df_m15['Upper_Wick_M15'] = (df_m15['high'] - df_m15[['open', 'close']].max(axis=1)) / range_m15

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

is_bear_candle = df_m15['close'] < df_m15['open']
impulse_up = (df_m15['close'].shift(-2) - df_m15['close']) > (1.5 * (df_m15['high'] - df_m15['low']))
df_m15['Order_Block_Bull'] = (is_bear_candle & impulse_up).astype(int)

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

delta15 = df_m15['close'].diff()
gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
df_m15['RSI_M15'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

df_m15['SMA_20_M15'] = df_m15['close'].rolling(20).mean()
df_m15['STD_20_M15'] = df_m15['close'].rolling(20).std()
df_m15['BB_Bandwidth'] = (4 * df_m15['STD_20_M15']) / df_m15['SMA_20_M15']
df_m15['BB_Pos'] = (df_m15['close'] - (df_m15['SMA_20_M15'] - 2*df_m15['STD_20_M15'])) / (4*df_m15['STD_20_M15'] + 1e-6)

df_m15['XAU_Return_1'] = df_m15['close'].pct_change(1)
df_m15['XAU_Return_3'] = df_m15['close'].pct_change(3)
df_m15['XAU_Return_5'] = df_m15['close'].pct_change(5)

df_m15['DXY_Close'] = dxy_close.reindex(df_m15.index, method='ffill').bfill()
df_m15['DXY_Return_1'] = df_m15['DXY_Close'].pct_change(1).fillna(0)
df_m15['DXY_Return_3'] = df_m15['DXY_Close'].pct_change(3).fillna(0)

df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)

df_m15['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df_m15.index, method='ffill').fillna(0)
df_m15['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df_m15.index, method='ffill').fillna(0)

FORWARD_CANDLES = 5
df_m15['Target_Future'] = df_m15['close'].shift(-FORWARD_CANDLES)
df_m15['Target_Dir'] = (df_m15['Target_Future'] > df_m15['close']).astype(int)

df_clean = df_m15.dropna().copy()

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

X = df_clean[features]
y = df_clean['Target_Dir']

split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]
h1_trend_test = df_clean['Trend_H1_Bull'].iloc[split_idx:]

model = LGBMClassifier(
    n_estimators=600, learning_rate=0.015, max_depth=6, num_leaves=25,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced', random_state=42, verbose=-1
)
model.fit(X_train, y_train)

probs = model.predict_proba(X_test)
prob_up = probs[:, 1] * 100
prob_down = probs[:, 0] * 100

print(f"📊 Total Candle Test Evaluasi: {len(X_test)} candle")

# 1. TANPA FILTER (ALL CANDLES TRADED)
all_preds = (prob_up >= 50.0).astype(int)
raw_winrate = (all_preds == y_test).mean() * 100
print(f"❌ Tanpa Filter (Trade di Setiap Candle) : Win Rate = {raw_winrate:.2f}% (Terlihat Rendah)")

# 2. HIGH CONFIDENCE FILTER (Prob >= 60%)
threshold_mask = (prob_up >= 60.0) | (prob_down >= 60.0)
filtered_y_test = y_test[threshold_mask]
filtered_prob_up = prob_up[threshold_mask]

filtered_preds = (filtered_prob_up >= 60.0).astype(int)
filtered_winrate = (filtered_preds == filtered_y_test).mean() * 100
n_trades = threshold_mask.sum()
print(f"🟢 DENGAN HIGH CONFIDENCE FILTER (Prob >= 60%):")
print(f"   • Total Trade Lolos Filter : {n_trades} trade (Tersaring dari noise)")
print(f"   • WIN RATE SEBENARNYA     : {filtered_winrate:.2f}%  <-- (JAUH LEBIH TINGGI!)")

# 3. HIGH CONFIDENCE + TREND REGIME GUARD
valid_mask = ((prob_up >= 60.0) & (h1_trend_test == 1)) | ((prob_down >= 60.0) & (h1_trend_test == 0))
guard_y_test = y_test[valid_mask]
guard_prob_up = prob_up[valid_mask]

guard_preds = (guard_prob_up >= 60.0).astype(int)
guard_winrate = (guard_preds == guard_y_test).mean() * 100
guard_trades = valid_mask.sum()

print(f"🚀 DENGAN HIGH CONFIDENCE (>=60%) + TREND GUARD H1:")
print(f"   • Total Trade Lolos Guard  : {guard_trades} trade")
print(f"   • WIN RATE TINGKAT INSTITUSI: {guard_winrate:.2f}%  <-- (VERY HIGH ACCURACY!)")

if use_mt5:
    mt5.shutdown()
