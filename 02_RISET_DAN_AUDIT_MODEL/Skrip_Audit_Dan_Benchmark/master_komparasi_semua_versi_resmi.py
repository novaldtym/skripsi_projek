"""
========================================================================================
MASTER BENCHMARK KOMPARASI SELURUH GENERASI & VERSI MODEL SKRIPSI
========================================================================================
Membandingkan secara Apple-to-Apple pada Rentang Waktu 2.5 Bulan Out-of-Sample (4.980 M15):
1. Versi V4.2 Lama (44 Fitur + Filter Rule Bot Multi-Zona Eksternal)
2. Versi 44 Fitur Pure Model (Tanpa Filter Eksternal)
3. Versi V5.0 Kemarin (50 Fitur Terintegrasi Zona - Parameter Default)
4. Versi V5.1 Teroptimasi Baru (50 Fitur Terintegrasi Zona - H1 10/50, BB10, ATR/ADX10)
5. Versi 57 Fitur (V-PRO Extended Multi-Horizon)
========================================================================================
"""
import sys, os, time, warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
mt5.initialize(path=MT5_PATH)
symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"

print("📥 Mengambil 25.000 candle M15, H1, H4 dari MT5 (Periode 2.5 Bulan OOS)...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

try:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)
except Exception:
    dxy_close = df['close'] * 0 + 104.0

# -----------------------------------------------------------------------------
# FITUR DASAR (44 FITUR)
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

# Baseline BB, RSI, ATR, ADX (Periode 20 & 14)
delta15 = df['close'].diff()
gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
df['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

sma20 = df['close'].rolling(20).mean()
std20 = df['close'].rolling(20).std()
df['BB_Bandwidth_20'] = (4 * std20) / (sma20 + 1e-9)
df['BB_Pos_20'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

# Optimal BB (Periode 10)
sma10 = df['close'].rolling(10).mean()
std10 = df['close'].rolling(10).std()
df['BB_Bandwidth_10'] = (4 * std10) / (sma10 + 1e-9)
df['BB_Pos_10'] = (df['close'] - (sma10 - 2*std10)) / (4*std10 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1)
df['XAU_Return_3'] = df['close'].pct_change(3)
df['XAU_Return_5'] = df['close'].pct_change(5)

dxy_c = dxy_close.reindex(df.index, method='ffill').bfill()
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

# H1 Baseline (50, 200)
h1_close = df_h1['close'].shift(1)
df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull_base']   = (h1_close > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong_base'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50_base']   = (h1_close - df_h1_loc['EMA_50_H1']) / (h1_close + 1e-9)

# H1 Optimal (10, 50)
df_h1_loc['EMA_10_H1'] = h1_close.ewm(span=10, adjust=False).mean()
df_h1_loc['Trend_H1_Bull_opt']   = (h1_close > df_h1_loc['EMA_10_H1']).astype(int)
df_h1_loc['Trend_H1_Strong_opt'] = (df_h1_loc['EMA_10_H1'] > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50_opt']   = (h1_close - df_h1_loc['EMA_10_H1']) / (h1_close + 1e-9)

# H4 Baseline (50, 200) & Optimal (20, 100)
h4_close = df_h4['close'].shift(1)
df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull_base']   = (h4_close > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong_base'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50_base']   = (h4_close - df_h4_loc['EMA_50_H4']) / (h4_close + 1e-9)

df_h4_loc['EMA_20_H4']  = h4_close.ewm(span=20, adjust=False).mean()
df_h4_loc['EMA_100_H4'] = h4_close.ewm(span=100, adjust=False).mean()
df_h4_loc['Trend_H4_Bull_opt']   = (h4_close > df_h4_loc['EMA_20_H4']).astype(int)
df_h4_loc['Trend_H4_Strong_opt'] = (df_h4_loc['EMA_20_H4'] > df_h4_loc['EMA_100_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50_opt']   = (h4_close - df_h4_loc['EMA_20_H4']) / (h4_close + 1e-9)

for c in ['Trend_H1_Bull_base', 'Trend_H1_Strong_base', 'H1_Dist_EMA50_base',
          'Trend_H1_Bull_opt',  'Trend_H1_Strong_opt',  'H1_Dist_EMA50_opt']:
    df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)

for c in ['Trend_H4_Bull_base', 'Trend_H4_Strong_base', 'H4_Dist_EMA50_base',
          'Trend_H4_Bull_opt',  'Trend_H4_Strong_opt',  'H4_Dist_EMA50_opt']:
    df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

high_diff = df['high'].diff(); low_diff = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)

# Baseline ATR/ADX (14)
atr14 = tr.rolling(14).mean() + 1e-6
df['ATR_14'] = atr14
plus_di_14  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
minus_di_14 = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
dx_14 = 100 * ((plus_di_14 - minus_di_14).abs() / (plus_di_14 + minus_di_14 + 1e-6))
df['ADX_14'] = dx_14.rolling(14).mean()

# Optimal ATR/ADX (10)
atr10 = tr.rolling(10).mean() + 1e-6
df['ATR_10'] = atr10
plus_di_10  = 100 * (pd.Series(plus_dm, index=df.index).rolling(10).mean() / atr10)
minus_di_10 = 100 * (pd.Series(minus_dm, index=df.index).rolling(10).mean() / atr10)
dx_10 = 100 * ((plus_di_10 - minus_di_10).abs() / (plus_di_10 + minus_di_10 + 1e-6))
df['ADX_10'] = dx_10.rolling(10).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

# 6 FITUR ZONA INTEGRATIF
df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

# 7 FITUR TAMBAHAN UNTUK 57 FITUR
df['Micro_Return_1'] = df['close'].pct_change(1)
df['Micro_Volatility_5'] = df['close'].pct_change().rolling(5).std()
df['High_Low_Spread'] = (df['high'] - df['low']) / df['close']
df['Upper_Lower_Wick_Ratio'] = (df['Upper_Wick_Ratio'] + 1e-6) / (df['Lower_Wick_Ratio'] + 1e-6)
df['Volume_Surge_Zscore'] = (df[vol_col] - df[vol_col].rolling(20).mean()) / (df[vol_col].rolling(20).std() + 1e-6)
df['H1_Dist_EMA200'] = (h1_close - df_h1_loc['EMA_200_H1']) / (h1_close + 1e-9)
df['H1_Dist_EMA200'] = df['H1_Dist_EMA200'].reindex(df.index, method='ffill').fillna(0)
df['Session_Overlap'] = (((df.index.hour >= 12) & (df.index.hour < 16))).astype(int)

# DAFTAR FITUR TIAP VERSI
f_44 = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 'FVG_Bull', 'FVG_Bear',
    'Dist_Support', 'Dist_Resistance', 'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth_20', 'BB_Pos_20', 'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    'Trend_H1_Bull_base', 'Trend_H1_Strong_base', 'H1_Dist_EMA50_base',
    'Trend_H4_Bull_base', 'Trend_H4_Strong_base', 'H4_Dist_EMA50_base',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20'
]

f_50_v50 = f_44 + [
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear'
]

f_50_v51 = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 'FVG_Bull', 'FVG_Bear',
    'Dist_Support', 'Dist_Resistance', 'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth_10', 'BB_Pos_10', 'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    'Trend_H1_Bull_opt', 'Trend_H1_Strong_opt', 'H1_Dist_EMA50_opt',
    'Trend_H4_Bull_opt', 'Trend_H4_Strong_opt', 'H4_Dist_EMA50_opt',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ATR_10', 'ADX_10', 'Volume_Ratio', 'Swing_High_20',
    'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
    'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
    'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear'
]

f_57 = f_50_v50 + [
    'Micro_Return_1', 'Micro_Volatility_5', 'High_Low_Spread',
    'Upper_Lower_Wick_Ratio', 'Volume_Surge_Zscore', 'H1_Dist_EMA200', 'Session_Overlap'
]

# TARGET DAN DATASET
df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
all_needed = list(set(f_44 + f_50_v50 + f_50_v51 + f_57 + ['Target_Dir', 'open', 'high', 'low', 'close']))
df_clean = df.dropna(subset=all_needed).copy()

# RENTANG WAKTU: OOS = 4.980 BAR (~2.5 BULAN)
test_len = 4980
train_df = df_clean.iloc[:-test_len]
test_df  = df_clean.iloc[-test_len:]

t_start = test_df.index[0].strftime("%d %b %Y")
t_end   = test_df.index[-1].strftime("%d %b %Y")
print(f"📊 Dataset Siap! Train: {len(train_df)} bar | Test (Out-of-Sample): {len(test_df)} bar (~2.5 Bulan: {t_start} s/d {t_end})")

# FUNGSI SIMULASI REALISTIS (SINGLE POSITION + BEP LOCK + TRAILING LOCK)
def simulate_trading(test_data, probs, threshold=0.60, use_external_filter=False):
    TOTAL_FRICTION = 0.35
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    d_supp = test_data['Dist_Support'].values
    d_res  = test_data['Dist_Resistance'].values
    lw_r   = test_data['Lower_Wick_Ratio'].values
    uw_r   = test_data['Upper_Wick_Ratio'].values
    n = len(closes)

    trades = []
    active_until = -1
    max_bars = 25
    tp_val = 6.50
    sl_val = 6.50
    equity = 500.0
    peak_equity = 500.0
    max_dd = 0.0

    for i in range(n - max_bars):
        if i <= active_until:
            continue

        p_up = probs[i]
        p_dn = 1.0 - p_up

        sig = 'HOLD'
        if p_up >= threshold: sig = 'BUY'
        elif p_dn >= threshold: sig = 'SELL'

        if sig == 'HOLD':
            continue

        # Filter Multi-Zona Eksternal Lama (Hanya untuk Versi V4.2 Lama)
        if use_external_filter:
            # Aturan Zona A/B/C dan Anti-Collision kaku luar
            if sig == 'BUY':
                if d_res[i] < 0.0018: continue # Collision
                if d_supp[i] > 0.0040 and p_up < 0.65: continue # Out of zone
            else:
                if d_supp[i] < 0.0018: continue # Collision
                if d_res[i] > 0.0040 and p_dn < 0.65: continue # Out of zone

        entry_p = closes[i]
        tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
        sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
        cur_sl = sl_p

        bep_locked = False
        trailing_locked = False
        pnl = 0.0
        result = 'HOLD'

        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]; l_bar = lows[cur_idx]; c_bar = closes[cur_idx]

            if sig == 'BUY':
                floating = h_bar - entry_p
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00); trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20); bep_locked = True

                if h_bar >= tp_p:
                    result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
                elif l_bar <= cur_sl:
                    if trailing_locked: result = 'WIN'; pnl = 2.00 - TOTAL_FRICTION
                    elif bep_locked: result = 'BEP'; pnl = 0.20 - TOTAL_FRICTION
                    else: result = 'LOSS'; pnl = -sl_val - TOTAL_FRICTION
                    active_until = cur_idx; break
            else:
                floating = entry_p - l_bar
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00); trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20); bep_locked = True

                if l_bar <= tp_p:
                    result = 'WIN'; pnl = tp_val - TOTAL_FRICTION; active_until = cur_idx; break
                elif h_bar >= cur_sl:
                    if trailing_locked: result = 'WIN'; pnl = 2.00 - TOTAL_FRICTION
                    elif bep_locked: result = 'BEP'; pnl = 0.20 - TOTAL_FRICTION
                    else: result = 'LOSS'; pnl = -sl_val - TOTAL_FRICTION
                    active_until = cur_idx; break

            if step == max_bars:
                # Horizon Timeout Close
                diff = (c_bar - entry_p) if sig == 'BUY' else (entry_p - c_bar)
                pnl = round(diff - TOTAL_FRICTION, 2)
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')
                active_until = cur_idx

        equity += pnl
        if equity > peak_equity: peak_equity = equity
        dd = peak_equity - equity
        if dd > max_dd: max_dd = dd

        trades.append({'sig': sig, 'result': result, 'pnl': pnl})

    df_t = pd.DataFrame(trades)
    n_t = len(df_t)
    if n_t == 0:
        return {'trades': 0, 'wr': 0, 'pnl': 0, 'pf': 0, 'max_dd': 0}
    w = len(df_t[df_t['result'] == 'WIN'])
    l = len(df_t[df_t['result'] == 'LOSS'])
    b = len(df_t[df_t['result'] == 'BEP'])
    wr = (w / n_t) * 100.0
    net_pnl = df_t['pnl'].sum()
    gw = df_t[df_t['pnl'] > 0]['pnl'].sum()
    gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum())
    pf = (gw / (gl + 1e-6)) if gl > 0 else gw

    return {'trades': n_t, 'wins': w, 'losses': l, 'beps': b,
            'wr': wr, 'pnl': net_pnl, 'pf': pf, 'max_dd': max_dd}

# EVALUASI 5 MODEL
models_to_test = [
    {'name': '1. V4.2 Lama (44 Fitur + Rule Bot Eksternal)', 'feats': f_44, 'use_ext': True, 'desc': 'Model terpasung rule luar'},
    {'name': '2. 44 Fitur Pure Model (Tanpa Rule Bot)',      'feats': f_44, 'use_ext': False, 'desc': 'Model 44 fitur mandiri'},
    {'name': '3. V5.0 Kemarin (50 Fitur Terintegrasi Zona)', 'feats': f_50_v50, 'use_ext': False, 'desc': 'Settingan baseline kemarin'},
    {'name': '4. V5.1 Baru (50 Fitur + Parameter Optimal)',  'feats': f_50_v51, 'use_ext': False, 'desc': 'MA10 Respected + BB10 + ATR10'},
    {'name': '5. 57 Fitur (V-PRO Extended Multi-Horizon)',   'feats': f_57, 'use_ext': False, 'desc': '57 Fitur mikro volatilitas'}
]

lgb_params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)

benchmark_rows = []
print("\n" + "="*115)
print("MEMULAI EVALUASI 5 MODEL PADA DATASET OUT-OF-SAMPLE 2.5 BULAN (THRESHOLD 0.60)")
print("="*115)

for m in models_to_test:
    t0 = time.time()
    clf = LGBMClassifier(**lgb_params)
    clf.fit(train_df[m['feats']].values, train_df['Target_Dir'].values)

    probs = clf.predict_proba(test_df[m['feats']].values)[:, 1]
    y_true = test_df['Target_Dir'].values

    # Metrik ML
    acc = accuracy_score(y_true, (probs >= 0.50).astype(int)) * 100.0
    auc = roc_auc_score(y_true, probs) * 100.0
    f1  = f1_score(y_true, (probs >= 0.50).astype(int)) * 100.0

    # Metrik Trading
    sim = simulate_trading(test_df, probs, threshold=0.60, use_external_filter=m['use_ext'])
    sim_sniper = simulate_trading(test_df, probs, threshold=0.65, use_external_filter=m['use_ext'])

    elapsed = time.time() - t0
    pnl_str = f"{'+$' if sim['pnl'] >= 0 else '-$'}{abs(sim['pnl']):.2f}"
    print(f"▶ {m['name']:<50} | ML Acc: {acc:>5.2f}% | AUC: {auc:>5.2f}% | Trades: {sim['trades']:>4} | WR: {sim['wr']:>5.1f}% | PnL: {pnl_str:>10} | Max DD: ${sim['max_dd']:>5.2f} ({elapsed:.1f}s)")

    benchmark_rows.append({
        'Model / Versi': m['name'],
        'Deskripsi Arsitektur': m['desc'],
        'ML Acc (%)': f"{acc:.2f}%",
        'ML AUC (%)': f"{auc:.2f}%",
        'Trades (0.60)': sim['trades'],
        'Win Rate (%)': f"{sim['wr']:.2f}%",
        'Net PnL (USD)': sim['pnl'],
        'Profit Factor': f"{sim['pf']:.2f}",
        'Max DD (USD)': f"${sim['max_dd']:.2f}",
        'Sniper WR (0.65)': f"{sim_sniper['wr']:.2f}%",
        'Sniper PnL (USD)': f"{sim_sniper['pnl']:.2f}"
    })

print("\n" + "="*115)
print("📊 TABEL KONSOLIDASI BENCHMARK RESMI SELURUH GENERASI MODEL (RENTANG 2.5 BULAN OOS)")
print("="*115)
df_bm = pd.DataFrame(benchmark_rows)
out_csv = r"d:\SKRIPSI INFORMATIKA\02_RISET_DAN_AUDIT_MODEL\master_benchmark_seluruh_generasi_model.csv"
df_bm.to_csv(out_csv, index=False, encoding='utf-8-sig')

for _, r in df_bm.iterrows():
    pnl_s = f"{'+$' if r['Net PnL (USD)'] >= 0 else '-$'}{abs(r['Net PnL (USD)']):.2f}"
    print(f"{r['Model / Versi']:<48} | WR: {r['Win Rate (%)']:<7} | PnL: {pnl_s:<10} | PF: {r['Profit Factor']:<5} | DD: {r['Max DD (USD)']:<8} | Sniper WR: {r['Sniper WR (0.65)']}")
print("="*115)
print(f"✅ Data tersimpan lengkap di: {out_csv}")
