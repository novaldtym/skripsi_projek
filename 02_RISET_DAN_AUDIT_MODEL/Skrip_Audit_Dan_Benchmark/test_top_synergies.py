"""
Uji Sinergi Parameter Terpilih dengan Evaluasi Identik Optimasi
"""
import sys, os, time, warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
mt5.initialize(path=MT5_PATH)
symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"

rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 30000)
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
mt5.shutdown()

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

def extract_features(df_raw, df_h1_raw, df_h4_raw,
                     swing_lb=20, rsi_p=14, bb_p=20, fibo_lb=100,
                     atr_p=14, h1_ema=(50,200), h4_ema=(50,200)):
    d = df_raw.copy()
    range_m15 = (d['high'] - d['low']) + 1e-6
    d['Body_Ratio'] = (d['close'] - d['open']).abs() / range_m15
    d['Lower_Wick_Ratio'] = (d[['open', 'close']].min(axis=1) - d['low']) / range_m15
    d['Upper_Wick_Ratio'] = (d['high'] - d[['open', 'close']].max(axis=1)) / range_m15

    d['FVG_Bull'] = (d['low'] > d['high'].shift(2)).astype(int)
    d['FVG_Bear'] = (d['high'] < d['low'].shift(2)).astype(int)

    d['Swing_High'] = d['high'].shift(1).rolling(swing_lb).max()
    d['Swing_Low'] = d['low'].shift(1).rolling(swing_lb).min()
    d['Dist_Support'] = (d['close'] - d['Swing_Low']) / d['close']
    d['Dist_Resistance'] = (d['Swing_High'] - d['close']) / d['close']

    d['BOS_Bull'] = (d['close'] > d['Swing_High']).astype(int)
    d['BOS_Bear'] = (d['close'] < d['Swing_Low']).astype(int)
    trend_slow = d['close'].pct_change(swing_lb)
    d['CHoCH_Bull'] = ((d['close'] > d['Swing_High']) & (trend_slow < 0)).astype(int)
    d['CHoCH_Bear'] = ((d['close'] < d['Swing_Low']) & (trend_slow > 0)).astype(int)
    d['Liquidity_Sweep_High'] = ((d['high'] > d['Swing_High']) & (d['close'] < d['Swing_High'])).astype(int)
    d['Liquidity_Sweep_Low'] = ((d['low'] < d['Swing_Low']) & (d['close'] > d['Swing_Low'])).astype(int)

    is_bear_c = d['close'] < d['open']; is_bull_c = d['close'] > d['open']
    body_sz = (d['close'] - d['open']).abs()
    avg_body = body_sz.rolling(swing_lb).mean()
    imp_up = (d['close'] > d['open']) & (body_sz > 1.5 * avg_body)
    imp_dn = (d['close'] < d['open']) & (body_sz > 1.5 * avg_body)
    d['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & imp_up.fillna(False)).astype(int)
    d['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & imp_dn.fillna(False)).astype(int)

    roll_high = d['high'].rolling(fibo_lb).max()
    roll_low = d['low'].rolling(fibo_lb).min()
    roll_range = (roll_high - roll_low) + 1e-6
    d['Fibo_Pos_100'] = (d['close'] - roll_low) / roll_range
    fibo_382 = roll_high - (roll_range * 0.382)
    fibo_500 = roll_high - (roll_range * 0.500)
    fibo_618 = roll_high - (roll_range * 0.618)
    d['Fibo_Dist_382'] = (d['close'] - fibo_382) / d['close']
    d['Fibo_Dist_500'] = (d['close'] - fibo_500) / d['close']
    d['Fibo_Dist_618'] = (d['close'] - fibo_618) / d['close']

    delta = d['close'].diff()
    gain = delta.where(delta > 0, 0.0).rolling(rsi_p).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(rsi_p).mean()
    rs = gain / (loss + 1e-9)
    d['RSI'] = 100 - (100 / (1 + rs))

    bb_mid = d['close'].rolling(bb_p).mean()
    bb_std = d['close'].rolling(bb_p).std()
    d['BB_Pos'] = (d['close'] - (bb_mid - 2*bb_std)) / (4*bb_std + 1e-9)
    d['BB_Width'] = (4*bb_std) / bb_mid

    tr1 = d['high'] - d['low']
    tr2 = (d['high'] - d['close'].shift(1)).abs()
    tr3 = (d['low'] - d['close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    d['ATR'] = tr.rolling(atr_p).mean()
    d['ATR_Pct'] = d['ATR'] / d['close']

    d['hour'] = d.index.hour
    d['dayofweek'] = d.index.dayofweek
    d['is_london'] = ((d['hour'] >= 7) & (d['hour'] < 16)).astype(int)
    d['is_ny'] = ((d['hour'] >= 12) & (d['hour'] < 21)).astype(int)
    d['is_overlap'] = ((d['hour'] >= 12) & (d['hour'] < 16)).astype(int)
    d['is_asia'] = ((d['hour'] >= 0) & (d['hour'] < 7)).astype(int)
    d['volatility_regime'] = (d['ATR'] > d['ATR'].rolling(50).mean()).astype(int)

    # MTF H1
    h1 = df_h1_raw.copy()
    h1['EMA_fast'] = h1['close'].ewm(span=h1_ema[0]).mean()
    h1['EMA_slow'] = h1['close'].ewm(span=h1_ema[1]).mean()
    h1['H1_Trend'] = (h1['EMA_fast'] > h1['EMA_slow']).astype(int)
    h1['H1_Dist_EMA_fast'] = (h1['close'] - h1['EMA_fast']) / h1['close']
    h1['H1_Dist_EMA_slow'] = (h1['close'] - h1['EMA_slow']) / h1['close']
    h1_feat = h1[['H1_Trend', 'H1_Dist_EMA_fast', 'H1_Dist_EMA_slow']].shift(1)
    d = pd.merge_asof(d.sort_index(), h1_feat.sort_index(), left_index=True, right_index=True, direction='backward')

    # MTF H4
    h4 = df_h4_raw.copy()
    h4['EMA_fast'] = h4['close'].ewm(span=h4_ema[0]).mean()
    h4['EMA_slow'] = h4['close'].ewm(span=h4_ema[1]).mean()
    h4['H4_Trend'] = (h4['EMA_fast'] > h4['EMA_slow']).astype(int)
    h4['H4_Dist_EMA_fast'] = (h4['close'] - h4['EMA_fast']) / h4['close']
    h4['H4_Dist_EMA_slow'] = (h4['close'] - h4['EMA_slow']) / h4['close']
    h4_feat = h4[['H4_Trend', 'H4_Dist_EMA_fast', 'H4_Dist_EMA_slow']].shift(1)
    d = pd.merge_asof(d.sort_index(), h4_feat.sort_index(), left_index=True, right_index=True, direction='backward')

    # Macro Proxy
    d['Roll_Max_H4'] = d['high'].rolling(16).max()
    d['Roll_Min_H4'] = d['low'].rolling(16).min()
    d['Dist_Max_H4'] = (d['Roll_Max_H4'] - d['close']) / d['close']
    d['Dist_Min_H4'] = (d['close'] - d['Roll_Min_H4']) / d['close']
    d['Roll_Max_D1'] = d['high'].rolling(96).max()
    d['Roll_Min_D1'] = d['low'].rolling(96).min()
    d['Dist_Max_D1'] = (d['Roll_Max_D1'] - d['close']) / d['close']
    d['Dist_Min_D1'] = (d['close'] - d['Roll_Min_D1']) / d['close']

    # Zone Features
    d['Zone_Type_Enc'] = 0
    d.loc[(d['Dist_Support'] < 0.003) & (d['FVG_Bull'] == 1), 'Zone_Type_Enc'] = 1
    d.loc[(d['Dist_Resistance'] < 0.003) & (d['FVG_Bear'] == 1), 'Zone_Type_Enc'] = 2
    d.loc[(d['Dist_Support'] < 0.003) & (d['Order_Block_Bull'] == 1), 'Zone_Type_Enc'] = 3
    d.loc[(d['Dist_Resistance'] < 0.003) & (d['Order_Block_Bear'] == 1), 'Zone_Type_Enc'] = 4
    d['Dist_To_Zone'] = d[['Dist_Support', 'Dist_Resistance']].min(axis=1)
    d['Zone_Is_Premium'] = (d['Fibo_Pos_100'] > 0.5).astype(int)
    d['Zone_Reaction_Strength'] = d['Body_Ratio'] * (d['ATR'] / (d['ATR'].rolling(20).mean() + 1e-9))

    feats = [
        'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio',
        'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
        'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
        'Liquidity_Sweep_High', 'Liquidity_Sweep_Low',
        'Order_Block_Bull', 'Order_Block_Bear',
        'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
        'RSI', 'BB_Pos', 'BB_Width', 'ATR_Pct',
        'hour', 'dayofweek', 'is_london', 'is_ny', 'is_overlap', 'is_asia', 'volatility_regime',
        'H1_Trend', 'H1_Dist_EMA_fast', 'H1_Dist_EMA_slow',
        'H4_Trend', 'H4_Dist_EMA_fast', 'H4_Dist_EMA_slow',
        'Dist_Max_H4', 'Dist_Min_H4', 'Dist_Max_D1', 'Dist_Min_D1',
        'Zone_Type_Enc', 'Dist_To_Zone', 'Zone_Is_Premium', 'Zone_Reaction_Strength'
    ]
    return d, feats

combos = [
    {'name': 'Baseline (H1 50/200, BB 20, RSI 14, H4 50/200)',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': (50,200)},
    {'name': 'Juara #1: H1 10/50 (Responsive H1)',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},
    {'name': 'Juara #2: H1 20/100',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (20,100), 'h4': (50,200)},
    {'name': 'Sinergi A: H1 10/50 + BB 10',
     'swing': 20, 'rsi': 14, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},
    {'name': 'Sinergi B: H1 10/50 + BB 10 + RSI 10',
     'swing': 20, 'rsi': 10, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},
    {'name': 'Sinergi C: H1 10/50 + H4 20/100',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (20,100)},
    {'name': 'Sinergi D: H1 10/50 + BB 10 + H4 20/100',
     'swing': 20, 'rsi': 14, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (20,100)},
    {'name': 'Sinergi E: H1 20/100 + BB 10',
     'swing': 20, 'rsi': 14, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (20,100), 'h4': (50,200)},
]

results = []
for c_idx, cfg in enumerate(combos, 1):
    t0 = time.time()
    df_feat, FEATS = extract_features(
        df, df_h1, df_h4,
        swing_lb=cfg['swing'], rsi_p=cfg['rsi'], bb_p=cfg['bb'],
        fibo_lb=cfg['fibo'], atr_p=cfg['atr'],
        h1_ema=cfg['h1'], h4_ema=cfg['h4']
    )
    df_feat['Target_Dir'] = (df_feat['close'].shift(-5) > df_feat['close']).astype(int)
    df_clean = df_feat.dropna(subset=FEATS + ['Target_Dir']).copy()

    split_idx = int(len(df_clean) * 0.80)
    train = df_clean.iloc[:split_idx]
    test = df_clean.iloc[split_idx:]

    X_train = train[FEATS].values; y_train = train['Target_Dir'].values
    X_test = test[FEATS].values; y_test = test['Target_Dir'].values

    model = LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)
    prob_up = probs[:, 1] * 100.0
    prob_down = probs[:, 0] * 100.0

    test = test.copy()
    test['prob_up'] = prob_up
    test['prob_down'] = prob_down

    total_trades = 0; wins = 0; losses = 0; beps = 0; net_pnl = 0.0
    test_rows = test.reset_index()
    df_all_rows = df_clean.reset_index()
    test_start_iloc = split_idx

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

        global_i = test_start_iloc + i
        result = 'BEP'
        pnl = 0.0
        for j in range(1, 6):
            if global_i + j >= len(df_all_rows):
                break
            bar = df_all_rows.iloc[global_i + j]
            bar_h, bar_l, bar_c = bar['high'], bar['low'], bar['close']
            if is_buy:
                if bar_l <= sl_p:
                    result = 'LOSS'; pnl = -sl_delta; break
                if bar_h >= tp_p:
                    result = 'WIN'; pnl = tp_delta; break
            else:
                if bar_h >= sl_p:
                    result = 'LOSS'; pnl = -sl_delta; break
                if bar_l <= tp_p:
                    result = 'WIN'; pnl = tp_delta; break
            if j == 5:
                diff = (bar_c - entry_p) if is_buy else (entry_p - bar_c)
                pnl = round(diff, 2)
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')

        total_trades += 1
        net_pnl += pnl
        if result == 'WIN': wins += 1
        elif result == 'LOSS': losses += 1
        else: beps += 1

    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    pnl_str = f"{'+$' if net_pnl >= 0 else '-$'}{abs(net_pnl):.2f}"
    elapsed = time.time() - t0
    print(f"[{c_idx}/{len(combos)}] {cfg['name']:<50} | Trades: {total_trades:>4} | WR: {wr:>5.1f}% | PnL: {pnl_str:>10} ({elapsed:.1f}s)")
    results.append({'name': cfg['name'], 'trades': total_trades, 'wins': wins, 'losses': losses, 'beps': beps, 'wr': wr, 'pnl': net_pnl})

print("\n" + "="*95)
print("HASIL KOMPARASI SINERGI PARAMETER")
print("="*95)
df_rank = pd.DataFrame(results).sort_values('pnl', ascending=False)
for r, (_, row) in enumerate(df_rank.iterrows(), 1):
    p_str = f"{'+$' if row['pnl'] >= 0 else '-$'}{abs(row['pnl']):.2f}"
    marker = " 👑 TERBAIK" if r == 1 else ""
    print(f"#{r} | {row['name']:<50} | WR: {row['wr']:>5.1f}% | PnL: {p_str:>10} | Trades: {row['trades']}{marker}")
