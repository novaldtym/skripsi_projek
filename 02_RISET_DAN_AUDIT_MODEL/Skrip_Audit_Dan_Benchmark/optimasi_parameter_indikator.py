"""
======================================================================================
OPTIMASI PARAMETER INDIKATOR — GRID SEARCH VARIASI FITUR TERBAIK
======================================================================================
Menguji semua kombinasi parameter indikator kunci untuk menemukan settingan
yang menghasilkan Win Rate & Net PnL TERTINGGI secara realistis.

Parameter yang Diuji:
1. Swing Lookback  : [10, 15, 20, 30]     (Anda lihat MA10 lebih di-respect)
2. RSI Period      : [7, 10, 14, 21]
3. BB Period       : [10, 15, 20, 30]
4. Fibo Lookback   : [50, 75, 100, 150]
5. ATR Period      : [7, 10, 14, 21]
6. H1 EMA Pair     : [(10,50), (20,100), (50,200)]
7. H4 EMA Pair     : [(10,50), (20,100), (50,200)]

Evaluasi: Walk-Forward + Simulasi TP/SL Realistis (TP +$8.50, SL -$6.50)
======================================================================================
"""
import sys, os, time, warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from lightgbm import LGBMClassifier
from itertools import product

# ===================
# 1. AMBIL DATA MT5
# ===================
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
mt5.initialize(path=MT5_PATH)
symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"

print("Mengambil data M15, H1, H4 dari MT5...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 30000)
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

print(f"Dataset M15: {len(df)} baris | H1: {len(df_h1)} | H4: {len(df_h4)}")

# ===================
# 2. FUNGSI EKSTRAKSI FITUR PARAMETRIK
# ===================
def extract_features_parametric(df_raw, df_h1_raw, df_h4_raw,
                                 swing_lb=20, rsi_p=14, bb_p=20, fibo_lb=100,
                                 atr_p=14, h1_ema=(50,200), h4_ema=(50,200)):
    df = df_raw.copy()
    range_m15 = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio'] = (df['close'] - df['open']).abs() / range_m15
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_m15
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_m15

    df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
    df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)

    # SWING LOOKBACK (PARAMETER UTAMA YANG DITES)
    df['Swing_High'] = df['high'].shift(1).rolling(swing_lb).max()
    df['Swing_Low'] = df['low'].shift(1).rolling(swing_lb).min()
    df['Dist_Support'] = (df['close'] - df['Swing_Low']) / df['close']
    df['Dist_Resistance'] = (df['Swing_High'] - df['close']) / df['close']

    df['BOS_Bull'] = (df['close'] > df['Swing_High']).astype(int)
    df['BOS_Bear'] = (df['close'] < df['Swing_Low']).astype(int)
    trend_slow = df['close'].pct_change(swing_lb)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High']) & (trend_slow < 0)).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low']) & (trend_slow > 0)).astype(int)
    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High']) & (df['close'] < df['Swing_High'])).astype(int)
    df['Liquidity_Sweep_Low'] = ((df['low'] < df['Swing_Low']) & (df['close'] > df['Swing_Low'])).astype(int)

    is_bear_c = df['close'] < df['open']; is_bull_c = df['close'] > df['open']
    body_sz = (df['close'] - df['open']).abs()
    avg_body = body_sz.rolling(swing_lb).mean()
    imp_up = (df['close'] > df['open']) & (body_sz > 1.5 * avg_body)
    imp_dn = (df['close'] < df['open']) & (body_sz > 1.5 * avg_body)
    df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
    df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

    # FIBONACCI LOOKBACK
    roll_high = df['high'].rolling(fibo_lb).max()
    roll_low = df['low'].rolling(fibo_lb).min()
    roll_range = (roll_high - roll_low) + 1e-6
    df['Fibo_Pos_100'] = (df['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)
    df['Fibo_Dist_382'] = (df['close'] - fibo_382) / df['close']
    df['Fibo_Dist_500'] = (df['close'] - fibo_500) / df['close']
    df['Fibo_Dist_618'] = (df['close'] - fibo_618) / df['close']

    # RSI PERIOD
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(rsi_p).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(rsi_p).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

    # BOLLINGER BANDS PERIOD
    sma_bb = df['close'].rolling(bb_p).mean()
    std_bb = df['close'].rolling(bb_p).std()
    df['BB_Bandwidth'] = (4 * std_bb) / sma_bb
    df['BB_Pos'] = (df['close'] - (sma_bb - 2*std_bb)) / (4*std_bb + 1e-6)

    df['XAU_Return_1'] = df['close'].pct_change(1)
    df['XAU_Return_3'] = df['close'].pct_change(3)
    df['XAU_Return_5'] = df['close'].pct_change(5)

    df['DXY_Return_1'] = 0.0; df['DXY_Return_3'] = 0.0; df['DXY_Trend'] = 0
    df['XAU_DXY_Ratio_Return'] = 0.0
    df['Is_NFP_Week'] = ((df.index.day <= 7) & (df.index.weekday == 4)).astype(int)
    df['Is_CPI_Day'] = ((df.index.day >= 10) & (df.index.day <= 15)).astype(int)
    df['Is_FOMC_Week'] = ((df.index.day >= 15) & (df.index.day <= 22) & (df.index.weekday == 2)).astype(int)

    # H1 MTF TREND (EMA PAIR PARAMETRIK)
    if df_h1_raw is not None and len(df_h1_raw) > 0:
        h1_c = df_h1_raw['close'].shift(1)
        ema_fast_h1 = h1_c.ewm(span=h1_ema[0], adjust=False).mean()
        ema_slow_h1 = h1_c.ewm(span=h1_ema[1], adjust=False).mean()
        h1_bull = (h1_c > ema_fast_h1).astype(int)
        h1_strong = (ema_fast_h1 > ema_slow_h1).astype(int)
        h1_dist = (h1_c - ema_fast_h1) / h1_c
        df['Trend_H1_Bull'] = h1_bull.reindex(df.index, method='ffill').fillna(0)
        df['Trend_H1_Strong'] = h1_strong.reindex(df.index, method='ffill').fillna(0)
        df['H1_Dist_EMA'] = h1_dist.reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H1_Bull'] = 1; df['Trend_H1_Strong'] = 1; df['H1_Dist_EMA'] = 0.0

    # H4 MTF TREND (EMA PAIR PARAMETRIK)
    if df_h4_raw is not None and len(df_h4_raw) > 0:
        h4_c = df_h4_raw['close'].shift(1)
        ema_fast_h4 = h4_c.ewm(span=h4_ema[0], adjust=False).mean()
        ema_slow_h4 = h4_c.ewm(span=h4_ema[1], adjust=False).mean()
        h4_bull = (h4_c > ema_fast_h4).astype(int)
        h4_strong = (ema_fast_h4 > ema_slow_h4).astype(int)
        h4_dist = (h4_c - ema_fast_h4) / h4_c
        df['Trend_H4_Bull'] = h4_bull.reindex(df.index, method='ffill').fillna(0)
        df['Trend_H4_Strong'] = h4_strong.reindex(df.index, method='ffill').fillna(0)
        df['H4_Dist_EMA'] = h4_dist.reindex(df.index, method='ffill').fillna(0)
    else:
        df['Trend_H4_Bull'] = 1; df['Trend_H4_Strong'] = 1; df['H4_Dist_EMA'] = 0.0

    is_bull = (df['close'] > df['open']).astype(int); is_bear = (df['close'] < df['open']).astype(int)
    df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
    df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

    high_diff = df['high'].diff(); low_diff = -df['low'].diff()
    plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_p).mean() + 1e-6
    df['ATR'] = atr
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(atr_p).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(atr_p).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
    df['ADX'] = dx.rolling(atr_p).mean()

    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(swing_lb).mean() + 1e-6)

    df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_B_Prox_Bull'] = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_B_Prox_Bear'] = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
    df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

    FEATS = [
        'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 'FVG_Bull', 'FVG_Bear',
        'Dist_Support', 'Dist_Resistance', 'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
        'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 'Order_Block_Bull', 'Order_Block_Bear',
        'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
        'RSI', 'BB_Bandwidth', 'BB_Pos', 'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
        'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
        'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
        'Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA',
        'Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA',
        'Consecutive_Bull', 'Consecutive_Bear',
        'ATR', 'ADX', 'Volume_Ratio', 'Swing_High',
        'Zone_A_Bounce_Bull', 'Zone_A_Bounce_Bear',
        'Zone_B_Prox_Bull', 'Zone_B_Prox_Bear',
        'Zone_Clearance_Safe_Bull', 'Zone_Clearance_Safe_Bear'
    ]
    df.rename(columns={'Swing_High': 'Swing_High'}, inplace=True)
    df['Swing_High'] = df['Swing_High']  # alias for column

    return df, FEATS

# ===================
# 3. GRID SEARCH PARAMETER
# ===================
swing_options  = [10, 15, 20, 30]
rsi_options    = [7, 10, 14, 21]
bb_options     = [10, 15, 20, 30]
fibo_options   = [50, 75, 100, 150]
atr_options    = [7, 10, 14, 21]
h1_ema_options = [(10, 50), (20, 100), (50, 200)]
h4_ema_options = [(10, 50), (20, 100), (50, 200)]

# Focused search: variasi per dimensi (bukan full cartesian yang terlalu besar)
# Baseline: swing=20, rsi=14, bb=20, fibo=100, atr=14, h1=(50,200), h4=(50,200)
configs = []

# A. Variasi Swing Lookback (paling penting, kamu notice MA10 lebih bagus)
for sw in swing_options:
    configs.append({'swing': sw, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': (50,200),
                    'label': f'Swing={sw}'})

# B. Variasi RSI Period
for rp in rsi_options:
    if rp == 14: continue
    configs.append({'swing': 20, 'rsi': rp, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': (50,200),
                    'label': f'RSI={rp}'})

# C. Variasi BB Period
for bp in bb_options:
    if bp == 20: continue
    configs.append({'swing': 20, 'rsi': 14, 'bb': bp, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': (50,200),
                    'label': f'BB={bp}'})

# D. Variasi Fibo Lookback
for fb in fibo_options:
    if fb == 100: continue
    configs.append({'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': fb, 'atr': 14, 'h1': (50,200), 'h4': (50,200),
                    'label': f'Fibo={fb}'})

# E. Variasi ATR Period
for ap in atr_options:
    if ap == 14: continue
    configs.append({'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': ap, 'h1': (50,200), 'h4': (50,200),
                    'label': f'ATR={ap}'})

# F. Variasi H1 EMA
for h1e in h1_ema_options:
    if h1e == (50,200): continue
    configs.append({'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': h1e, 'h4': (50,200),
                    'label': f'H1_EMA={h1e[0]}/{h1e[1]}'})

# G. Variasi H4 EMA
for h4e in h4_ema_options:
    if h4e == (50,200): continue
    configs.append({'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': h4e,
                    'label': f'H4_EMA={h4e[0]}/{h4e[1]}'})

# H. KOMBINASI KANDIDAT TOP (Swing=10 + variasi EMA pendek)
for h1e in h1_ema_options:
    for h4e in h4_ema_options:
        configs.append({'swing': 10, 'rsi': 14, 'bb': 15, 'fibo': 75, 'atr': 14, 'h1': h1e, 'h4': h4e,
                        'label': f'COMBO:Sw10_BB15_Fb75_H1{h1e[0]}_H4{h4e[0]}'})

print(f"Total Konfigurasi: {len(configs)}")

# ===================
# 4. TRAIN + EVALUATE EACH CONFIG (Walk-Forward)
# ===================
results = []

for cfg_idx, cfg in enumerate(configs, 1):
    t0 = time.time()
    label = cfg['label']

    df_feat, FEATS = extract_features_parametric(
        df, df_h1, df_h4,
        swing_lb=cfg['swing'], rsi_p=cfg['rsi'], bb_p=cfg['bb'],
        fibo_lb=cfg['fibo'], atr_p=cfg['atr'],
        h1_ema=cfg['h1'], h4_ema=cfg['h4']
    )

    df_feat['Target_Dir'] = (df_feat['close'].shift(-5) > df_feat['close']).astype(int)
    df_clean = df_feat.dropna(subset=FEATS + ['Target_Dir']).copy()

    if len(df_clean) < 5000:
        print(f"  [{cfg_idx}/{len(configs)}] {label} — Data kurang ({len(df_clean)}), skip.")
        continue

    # Walk-Forward Split: Train 80% awal, Test 20% terakhir
    split_idx = int(len(df_clean) * 0.80)
    train = df_clean.iloc[:split_idx]
    test = df_clean.iloc[split_idx:]

    X_train = train[FEATS].values; y_train = train['Target_Dir'].values
    X_test = test[FEATS].values; y_test = test['Target_Dir'].values

    model = LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
    model.fit(X_train, y_train)

    # Predict prob
    probs = model.predict_proba(X_test)
    prob_up = probs[:, 1] * 100.0
    prob_down = probs[:, 0] * 100.0

    test = test.copy()
    test['prob_up'] = prob_up
    test['prob_down'] = prob_down

    # Simulasi trading realistis (TP/SL candle-based, >=60% threshold)
    total_trades = 0; wins = 0; losses = 0; beps = 0; net_pnl = 0.0

    test_rows = test.reset_index()
    df_all_rows = df_clean.reset_index()
    test_start_iloc = split_idx  # Dalam df_clean

    for i in range(len(test_rows)):
        pu = test_rows.loc[i, 'prob_up']
        pd_val = test_rows.loc[i, 'prob_down']

        if pu >= 60.0 and pu > pd_val:
            sig = 'BUY'
        elif pd_val >= 60.0 and pd_val > pu:
            sig = 'SELL'
        else:
            continue

        entry_p = test_rows.loc[i, 'close']
        is_buy = (sig == 'BUY')
        tp_delta = 8.50 if pu < 65 and pd_val < 65 else 11.0
        sl_delta = 6.50
        tp_p = entry_p + tp_delta if is_buy else entry_p - tp_delta
        sl_p = entry_p - sl_delta if is_buy else entry_p + sl_delta

        # Walk forward candles (max 5)
        global_i = test_start_iloc + i
        result = 'BEP'
        pnl = 0.0
        for j in range(1, 6):
            if global_i + j >= len(df_all_rows):
                break
            bar = df_all_rows.iloc[global_i + j]
            h, l, c = bar['high'], bar['low'], bar['close']
            if is_buy:
                if l <= sl_p:
                    result = 'LOSS'; pnl = -sl_delta; break
                if h >= tp_p:
                    result = 'WIN'; pnl = tp_delta; break
            else:
                if h >= sl_p:
                    result = 'LOSS'; pnl = -sl_delta; break
                if l <= tp_p:
                    result = 'WIN'; pnl = tp_delta; break
            if j == 5:
                diff = (c - entry_p) if is_buy else (entry_p - c)
                pnl = round(diff, 2)
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')

        total_trades += 1
        net_pnl += pnl
        if result == 'WIN': wins += 1
        elif result == 'LOSS': losses += 1
        else: beps += 1

    elapsed = time.time() - t0
    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    results.append({
        'config': label,
        'swing': cfg['swing'], 'rsi': cfg['rsi'], 'bb': cfg['bb'],
        'fibo': cfg['fibo'], 'atr': cfg['atr'],
        'h1_ema': f"{cfg['h1'][0]}/{cfg['h1'][1]}", 'h4_ema': f"{cfg['h4'][0]}/{cfg['h4'][1]}",
        'trades': total_trades, 'wins': wins, 'losses': losses, 'beps': beps,
        'wr': wr, 'net_pnl': net_pnl
    })

    wr_str = f"{wr:.1f}%"
    pnl_str = f"{'+$' if net_pnl >= 0 else '-$'}{abs(net_pnl):.2f}"
    print(f"  [{cfg_idx:>2}/{len(configs)}] {label:<35} | {total_trades:>4} trades | WR: {wr_str:>6} | PnL: {pnl_str:>10} | ({elapsed:.1f}s)")

# ===================
# 5. RANKING HASIL
# ===================
df_res = pd.DataFrame(results)
df_res.sort_values('net_pnl', ascending=False, inplace=True)

print("\n" + "="*110)
print("RANKING KONFIGURASI PARAMETER INDIKATOR (BERDASARKAN NET PNL)")
print("="*110)
print(f"{'Rank':<5} | {'Config':<35} | {'Trades':<6} | {'W':<3} | {'L':<3} | {'B':<3} | {'WR':<7} | {'Net PnL':<12}")
print("-"*110)

for rank, (_, row) in enumerate(df_res.iterrows(), 1):
    pnl_str = f"{'+$' if row['net_pnl'] >= 0 else '-$'}{abs(row['net_pnl']):.2f}"
    marker = " <-- JUARA" if rank == 1 else (" <-- #2" if rank == 2 else (" <-- #3" if rank == 3 else ""))
    print(f"{rank:<5} | {row['config']:<35} | {row['trades']:<6} | {row['wins']:<3} | {row['losses']:<3} | {row['beps']:<3} | {row['wr']:>5.1f}% | {pnl_str:<12}{marker}")

print("="*110)

# Detail Juara
best = df_res.iloc[0]
print(f"\nJUARA 1: {best['config']}")
print(f"  Swing Lookback  : {best['swing']}")
print(f"  RSI Period      : {best['rsi']}")
print(f"  BB Period       : {best['bb']}")
print(f"  Fibo Lookback   : {best['fibo']}")
print(f"  ATR Period      : {best['atr']}")
print(f"  H1 EMA Pair     : {best['h1_ema']}")
print(f"  H4 EMA Pair     : {best['h4_ema']}")
print(f"  Win Rate        : {best['wr']:.1f}%")
print(f"  Net PnL         : {'+$' if best['net_pnl'] >= 0 else '-$'}{abs(best['net_pnl']):.2f} USD")

# Simpan CSV
csv_path = r"d:\SKRIPSI INFORMATIKA\02_RISET_DAN_AUDIT_MODEL\hasil_optimasi_parameter_indikator.csv"
os.makedirs(os.path.dirname(csv_path), exist_ok=True)
df_res.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\nHasil tersimpan di: {csv_path}")
