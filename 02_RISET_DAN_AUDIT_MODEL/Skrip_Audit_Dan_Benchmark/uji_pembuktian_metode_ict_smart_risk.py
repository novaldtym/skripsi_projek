"""
=============================================================================
PENGUJIAN METODE ICT CERDAS (SMART RISK):
1. Raw Gap vs Trend-Filtered Gap
2. ATR-Normalized FVG (1/3 ATR s/d 2 ATR)
3. Inversion FVG (IFVG) Polarization
=============================================================================
"""
import sys, os
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
SYMBOL = "XAUUSD"

print("="*85)
print("🔬 AUDIT METODE ICT GAP: RAW GAPS VS TREND-FILTERED & ATR STANDARDIZED")
print("="*85)

if not mt5.initialize(path=MT5_PATH):
    mt5.initialize()

if mt5.symbol_info(SYMBOL) is None:
    SYMBOL = "XAUUSDm"
mt5.symbol_select(SYMBOL, True)

# Tarik 10.000 candle M15
rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 10000)
df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

# Hitung ATR 14
tr = pd.concat([
    df['high'] - df['low'],
    (df['high'] - df['close'].shift()).abs(),
    (df['low'] - df['close'].shift()).abs()
], axis=1).max(axis=1)
df['ATR_14'] = tr.rolling(14).mean()

# 1. DETEKSI FVG MURNI (RAW FVG)
df['FVG_Bull_Raw'] = (df['low'] > df['high'].shift(2)).astype(int)
df['FVG_Bear_Raw'] = (df['high'] < df['low'].shift(2)).astype(int)

# 2. FILTER UKURAN GAP DENGAN ATR (SMART RISK CRITERIA)
gap_size_bull = df['low'] - df['high'].shift(2)
gap_size_bear = df['low'].shift(2) - df['high']

valid_size_bull = (gap_size_bull >= (0.33 * df['ATR_14'])) & (gap_size_bull <= (2.0 * df['ATR_14']))
valid_size_bear = (gap_size_bear >= (0.33 * df['ATR_14'])) & (gap_size_bear <= (2.0 * df['ATR_14']))

df['FVG_Bull_ATR'] = (df['FVG_Bull_Raw'] & valid_size_bull).astype(int)
df['FVG_Bear_ATR'] = (df['FVG_Bear_Raw'] & valid_size_bear).astype(int)

# 3. FILTER TREN (EMA 50 & EMA 200)
df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['Uptrend'] = (df['close'] > df['EMA_50']) & (df['EMA_50'] > df['EMA_200'])
df['Downtrend'] = (df['close'] < df['EMA_50']) & (df['EMA_50'] < df['EMA_200'])

# UJI SIMULASI 3 TAHAP:
# Tahap 1: Raw FVG Buta (Tanpa Filter Tren)
# Tahap 2: FVG + Standarisasi ATR (Smart Risk)
# Tahap 3: FVG + Standarisasi ATR + Filter Tren & Struktur

def test_fvg_strategy(name, bull_col, bear_col, use_trend_filter=False):
    trades = []
    for i in range(200, len(df) - 10):
        c = df['close'].iloc[i]
        h = df['high'].iloc[i+1:i+6].max()
        l = df['low'].iloc[i+1:i+6].min()
        atr = df['ATR_14'].iloc[i]

        sl_dist = 0.5 * atr
        tp_dist = 1.0 * atr # RR 1:2 (Risk 0.5 ATR, Reward 1.0 ATR)

        if df[bull_col].iloc[i] == 1:
            if not use_trend_filter or df['Uptrend'].iloc[i]:
                # Buy trade
                if l <= (c - sl_dist):
                    trades.append(-sl_dist)
                elif h >= (c + tp_dist):
                    trades.append(tp_dist)
                else:
                    trades.append(df['close'].iloc[i+5] - c)

        elif df[bear_col].iloc[i] == 1:
            if not use_trend_filter or df['Downtrend'].iloc[i]:
                # Sell trade
                if h >= (c + sl_dist):
                    trades.append(-sl_dist)
                elif l <= (c - tp_dist):
                    trades.append(tp_dist)
                else:
                    trades.append(c - df['close'].iloc[i+5])

    trades = np.array(trades)
    if len(trades) == 0: return
    wins = trades[trades > 0]
    wr = len(wins) / len(trades) * 100
    pf = wins.sum() / (abs(trades[trades <= 0].sum()) + 1e-6)
    print(f"\n📊 {name}:")
    print(f"   • Total Sinyal : {len(trades)} trade")
    print(f"   • Win Rate     : {wr:.2f}% ({len(wins)} Win / {len(trades)-len(wins)} Loss)")
    print(f"   • Profit Factor: {pf:.2f}")
    print(f"   • Net PnL (pts): {trades.sum():.2f}")

test_fvg_strategy("1. METODE BUTA: RAW FVG TANPA FILTER", 'FVG_Bull_Raw', 'FVG_Bear_Raw', use_trend_filter=False)
test_fvg_strategy("2. FILTER ATR: FVG DENGAN BATAS 1/3 - 2 ATR", 'FVG_Bull_ATR', 'FVG_Bear_ATR', use_trend_filter=False)
test_fvg_strategy("3. METODE CERDAS: FVG + STANDARISASI ATR + FILTER TREN", 'FVG_Bull_ATR', 'FVG_Bear_ATR', use_trend_filter=True)

mt5.shutdown()
