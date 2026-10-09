import os
import sys
import time
import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from lightgbm import LGBMClassifier

print("="*100)
print("BENCHMARK ILMIAH: M15 BAR-CLOSE VS M5 INTRA-BAR TRIGGER")
print("Uji Komparasi Kinerja Market (PnL, WR, Trades, RRR, DD) & Performa Sistem Python")
print("="*100)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik Data Historis dari MT5 ({symbol})...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15000)
rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5,  0, 45000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1,  0, 5000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4,  0, 2000)

mt5.shutdown()

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

print(f"Data M15: {len(df_m15)} bars | Data M5: {len(df_m5)} bars")

# Feature Extraction Function
def extract_features(df_in, df_h1_in, df_h4_in, horizon=5):
    df = df_in.copy()
    h1 = df_h1_in.copy()
    h4 = df_h4_in.copy()

    candle_range = (df['high'] - df['low']).replace(0, 1e-5)
    df['Body_Ratio'] = (df['close'] - df['open']).abs() / candle_range
    df['Upper_Wick'] = (df['high'] - df[['close', 'open']].max(axis=1)) / candle_range
    df['Lower_Wick'] = (df[['close', 'open']].min(axis=1) - df['low']) / candle_range

    df['Swing_High_20'] = df['high'].shift(1).rolling(20).max()
    df['Swing_Low_20']  = df['low'].shift(1).rolling(20).min()
    df['Dist_Res'] = (df['Swing_High_20'] - df['close']) / df['close']
    df['Dist_Sup'] = (df['close'] - df['Swing_Low_20']) / df['close']

    # Fibo
    roll_h = df['high'].rolling(50).max()
    roll_l = df['low'].rolling(50).min()
    df['Fibo_Pos'] = (df['close'] - roll_l) / (roll_h - roll_l + 1e-5)

    # RSI
    diff = df['close'].diff()
    gain = diff.where(diff > 0, 0).rolling(14).mean()
    loss = (-diff.where(diff < 0, 0)).rolling(14).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

    # MTF
    h1_ema50 = h1['close'].ewm(span=50, adjust=False).mean()
    h4_ema50 = h4['close'].ewm(span=50, adjust=False).mean()
    df['H1_Dist_EMA50'] = ((h1['close'] - h1_ema50) / h1['close']).reindex(df.index, method='ffill').fillna(0)
    df['H4_Dist_EMA50'] = ((h4['close'] - h4_ema50) / h4['close']).reindex(df.index, method='ffill').fillna(0)

    # Rejection Wick Features (Kunci untuk trigger ekor)
    df['Is_Top_Rejection'] = ((df['Upper_Wick'] > 0.40) & (df['close'] < df['open'])).astype(int)
    df['Is_Bot_Rejection'] = ((df['Lower_Wick'] > 0.40) & (df['close'] > df['open'])).astype(int)

    # Target
    df['Target'] = (df['close'].shift(-horizon) > df['close']).astype(int)
    return df

print("Mengekstrak Fitur M15 dan M5...")
df_m15_feat = extract_features(df_m15, df_h1, df_h4, horizon=5).dropna()
df_m5_feat  = extract_features(df_m5,  df_h1, df_h4, horizon=6).dropna()

feat_cols = ['Body_Ratio', 'Upper_Wick', 'Lower_Wick', 'Dist_Res', 'Dist_Sup', 'Fibo_Pos', 'RSI_14', 'H1_Dist_EMA50', 'H4_Dist_EMA50']

# Split 75% Train, 25% Out-of-Sample Test
split_m15 = int(len(df_m15_feat) * 0.75)
train_m15, test_m15 = df_m15_feat.iloc[:split_m15], df_m15_feat.iloc[split_m15:]

split_m5 = int(len(df_m5_feat) * 0.75)
train_m5, test_m5 = df_m5_feat.iloc[:split_m5], df_m5_feat.iloc[split_m5:]

# Train M15 Model
print("Melatih Model LightGBM M15...")
lgb_m15 = LGBMClassifier(n_estimators=300, learning_rate=0.02, max_depth=5, num_leaves=24, random_state=42, verbose=-1)
lgb_m15.fit(train_m15[feat_cols], train_m15['Target'])
probs_m15 = lgb_m15.predict_proba(test_m15[feat_cols])

# Train M5 Model
print("Melatih Model LightGBM M5...")
lgb_m5 = LGBMClassifier(n_estimators=300, learning_rate=0.02, max_depth=5, num_leaves=24, random_state=42, verbose=-1)
lgb_m5.fit(train_m5[feat_cols], train_m5['Target'])
probs_m5 = lgb_m5.predict_proba(test_m5[feat_cols])

test_m15 = test_m15.copy()
test_m15['Prob_Buy'] = probs_m15[:, 1]
test_m15['Prob_Sell'] = probs_m15[:, 0]

test_m5 = test_m5.copy()
test_m5['Prob_Buy'] = probs_m5[:, 1]
test_m5['Prob_Sell'] = probs_m5[:, 0]

# Align M15 bias into M5 dataframe via ffill
test_m5['M15_Prob_Buy'] = test_m15['Prob_Buy'].reindex(test_m5.index, method='ffill')
test_m5['M15_Prob_Sell'] = test_m15['Prob_Sell'].reindex(test_m5.index, method='ffill')
test_m5['M15_Dist_Res'] = test_m15['Dist_Res'].reindex(test_m5.index, method='ffill')
test_m5['M15_Dist_Sup'] = test_m15['Dist_Sup'].reindex(test_m5.index, method='ffill')
test_m5.dropna(inplace=True)

# SIMULATOR TRADING REALISTIS
def run_simulation(df_eval, signal_col, sl_pts, tp_pts, bep_pts=2.50, bep_lock=0.20):
    SPREAD = 0.20
    closes = df_eval['close'].values
    highs  = df_eval['high'].values
    lows   = df_eval['low'].values
    signals = df_eval[signal_col].values
    n = len(closes)

    trades = []
    active_until = -1
    win_count = 0
    bep_count = 0
    loss_count = 0

    for i in range(n - 40):
        if i <= active_until:
            continue
        sig = signals[i]
        if sig not in ['BUY', 'SELL']:
            continue

        entry_p = closes[i]
        tp_p = entry_p + tp_pts if sig == 'BUY' else entry_p - tp_pts
        sl_p = entry_p - sl_pts if sig == 'BUY' else entry_p + sl_pts
        cur_sl = sl_p
        bep_on = False

        held = 40
        pnl_gross = 0.0

        for step in range(1, 41):
            idx = i + step
            h_bar = highs[idx]
            l_bar = lows[idx]

            # Trailing BEP
            if not bep_on:
                if sig == 'BUY' and (h_bar - entry_p) >= bep_pts:
                    cur_sl = entry_p + bep_lock
                    bep_on = True
                elif sig == 'SELL' and (entry_p - l_bar) >= bep_pts:
                    cur_sl = entry_p - bep_lock
                    bep_on = True

            # Check Hit
            if sig == 'BUY':
                if h_bar >= tp_p:
                    pnl_gross = tp_pts
                    win_count += 1
                    held = step
                    break
                elif l_bar <= cur_sl:
                    pnl_gross = bep_lock if bep_on else -sl_pts
                    if bep_on: bep_count += 1
                    else: loss_count += 1
                    held = step
                    break
            else: # SELL
                if l_bar <= tp_p:
                    pnl_gross = tp_pts
                    win_count += 1
                    held = step
                    break
                elif h_bar >= cur_sl:
                    pnl_gross = bep_lock if bep_on else -sl_pts
                    if bep_on: bep_count += 1
                    else: loss_count += 1
                    held = step
                    break

        if held == 40 and pnl_gross == 0.0:
            last_p = closes[i + 40]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            if pnl_gross > 0: win_count += 1
            else: loss_count += 1

        pnl_net = pnl_gross - SPREAD
        trades.append(pnl_net)
        active_until = i + held

    trades = np.array(trades)
    n_tr = len(trades)
    if n_tr == 0:
        return 0, 0.0, 0.0, 0.0, 0.0, 0, 0, 0

    wr = (win_count / n_tr) * 100.0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    return n_tr, wr, tot_pnl, pf, dd, win_count, bep_count, loss_count

# STRATEGI 1: M15 STANDAR (Bar-Close Confirmation >= 60%)
test_m15['Sig_M15_Close'] = 'HOLD'
mask_buy_m15 = test_m15['Prob_Buy'] >= 0.60
mask_sell_m15 = test_m15['Prob_Sell'] >= 0.60
test_m15.loc[mask_buy_m15, 'Sig_M15_Close'] = 'BUY'
test_m15.loc[mask_sell_m15, 'Sig_M15_Close'] = 'SELL'

tr1, wr1, pnl1, pf1, dd1, w1, b1, l1 = run_simulation(
    test_m15, 'Sig_M15_Close', sl_pts=6.50, tp_pts=8.50, bep_pts=2.50
)

# STRATEGI 2: M5 INTRA-BAR TRIGGER (Konfluensi M15 Bias + M5 Rejection / Reversal)
# Ide: Jika M15 mendeteksi Sell Bias (Prob Sell >= 54% ATAU Dekat Resisten M15 < 0.25%),
# dan di M5 muncul Rejection Candle / M5 Prob Sell >= 60%, OPEN SELL LANGSUNG!
test_m5['Sig_M5_Intra'] = 'HOLD'
m5_sell_cond = (
    ((test_m5['M15_Prob_Sell'] >= 0.54) | (test_m5['M15_Dist_Res'] < 0.0025)) &
    ((test_m5['Prob_Sell'] >= 0.58) | (test_m5['Is_Top_Rejection'] == 1))
)
m5_buy_cond = (
    ((test_m5['M15_Prob_Buy'] >= 0.54) | (test_m5['M15_Dist_Sup'] < 0.0025)) &
    ((test_m5['Prob_Buy'] >= 0.58) | (test_m5['Is_Bot_Rejection'] == 1))
)
test_m5.loc[m5_buy_cond, 'Sig_M5_Intra'] = 'BUY'
test_m5.loc[m5_sell_cond, 'Sig_M5_Intra'] = 'SELL'

# Menggunakan SL lebih ketat ($4.50) dan TP $7.50 karena entri didapat lebih awal di ujung wick!
tr2, wr2, pnl2, pf2, dd2, w2, b2, l2 = run_simulation(
    test_m5, 'Sig_M5_Intra', sl_pts=4.50, tp_pts=7.50, bep_pts=2.00
)

# STRATEGI 3: M5 AGRESSIVE INTRA-BAR (Tanpa tunggu M15, pure M5 trigger saat dekat S/R M15)
test_m5['Sig_M5_Pure'] = 'HOLD'
m5_pure_sell = (test_m5['Prob_Sell'] >= 0.60) | ((test_m5['M15_Dist_Res'] < 0.0020) & (test_m5['Is_Top_Rejection'] == 1))
m5_pure_buy  = (test_m5['Prob_Buy'] >= 0.60)  | ((test_m5['M15_Dist_Sup'] < 0.0020) & (test_m5['Is_Bot_Rejection'] == 1))
test_m5.loc[m5_pure_buy, 'Sig_M5_Pure'] = 'BUY'
test_m5.loc[m5_pure_sell, 'Sig_M5_Pure'] = 'SELL'

tr3, wr3, pnl3, pf3, dd3, w3, b3, l3 = run_simulation(
    test_m5, 'Sig_M5_Pure', sl_pts=4.00, tp_pts=6.50, bep_pts=2.00
)

# UJI PERFORMA KOMPUTASI PYTHON (CPU & Latency)
t0 = time.perf_counter()
for _ in range(100):
    _ = lgb_m15.predict_proba(test_m15[feat_cols].iloc[-1:])
lat_m15 = (time.perf_counter() - t0) / 100 * 1000  # ms

t0 = time.perf_counter()
for _ in range(100):
    _ = lgb_m5.predict_proba(test_m5[feat_cols].iloc[-1:])
lat_m5 = (time.perf_counter() - t0) / 100 * 1000  # ms

print("\n" + "="*105)
print(f"{'Metrik / Indikator Evaluasi':<38} | {'1. M15 Bar-Close (Skrg)':<20} | {'2. M5 Intra Trigger':<20} | {'3. M5 Pure Wick Trigger':<20}")
print("="*105)
print(f"{'Total Transaksi':<38} | {tr1:<20} | {tr2:<20} | {tr3:<20}")
print(f"{'Win Rate Riil (%)':<38} | {wr1:<20.2f} | {wr2:<20.2f} | {wr3:<20.2f}")
print(f"{'Net PnL ($) [Lot 0.01 Modal $500]':<38} | ${pnl1:<19.2f} | ${pnl2:<19.2f} | ${pnl3:<19.2f}")
print(f"{'Profit Factor (PF)':<38} | {pf1:<20.2f} | {pf2:<20.2f} | {pf3:<20.2f}")
print(f"{'Maksimum Drawdown ($)':<38} | ${dd1:<19.2f} | ${dd2:<19.2f} | ${dd3:<19.2f}")
print(f"{'Rincian (TP Full / BEP / SL Full)':<38} | {f'{w1} / {b1} / {l1}':<20} | {f'{w2} / {b2} / {l2}':<20} | {f'{w3} / {b3} / {l3}':<20}")
print(f"{'Rata-rata Stop Loss (Jarak)':<38} | {'$6.50 (65 pips)':<20} | {'$4.50 (45 pips)':<20} | {'$4.00 (40 pips)':<20}")
print(f"{'Inference Latency Python':<38} | {f'{lat_m15:.2f} ms':<20} | {f'{lat_m5:.2f} ms':<20} | {f'{lat_m5:.2f} ms':<20}")
print(f"{'Frekuensi Pengecekan Loop':<38} | {'Tiap 15 Menit':<20} | {'Tiap 5 Menit / Tick':<20} | {'Tiap 5 Menit / Tick':<20}")
print("="*105)
