"""
Uji Kombinasi Parameter Pemenang (H1 EMA 10/50 + BB10 + RSI10 dll)
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

print("Mengambil data MT5...")
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
    {'name': '1. Baseline (Current Default: H1 50/200, BB20, RSI14)',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (50,200), 'h4': (50,200)},

    {'name': '2. Top #1: H1 EMA 10/50 (User Insight MA10 Respect)',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},

    {'name': '3. Top #2: H1 EMA 20/100',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (20,100), 'h4': (50,200)},

    {'name': '4. Combo: H1 10/50 + BB 10 (Dual Responsiveness)',
     'swing': 20, 'rsi': 14, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},

    {'name': '5. Combo: H1 10/50 + RSI 10 (Faster Momentum Filter)',
     'swing': 20, 'rsi': 10, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},

    {'name': '6. Combo: H1 10/50 + BB 10 + RSI 10 (Triple Responsive)',
     'swing': 20, 'rsi': 10, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (50,200)},

    {'name': '7. Combo: H1 10/50 + H4 20/100 (Responsive H1 + Balanced H4)',
     'swing': 20, 'rsi': 14, 'bb': 20, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (20,100)},

    {'name': '8. Combo: H1 10/50 + BB 10 + H4 20/100',
     'swing': 20, 'rsi': 14, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (20,100)},

    {'name': '9. Combo: H1 10/50 + BB 10 + RSI 10 + H4 20/100 (Full Optimized Synthesis)',
     'swing': 20, 'rsi': 10, 'bb': 10, 'fibo': 100, 'atr': 14, 'h1': (10,50), 'h4': (20,100)},
]

print("\n" + "="*95)
print("PENGUJIAN KOMBINASI PARAMETER TOP CANDIDATES")
print("="*95)

results = []
for c_idx, c in enumerate(combos, 1):
    t0 = time.time()
    df_feat, FEATS = extract_features(
        df, df_h1, df_h4,
        swing_lb=c['swing'], rsi_p=c['rsi'], bb_p=c['bb'],
        fibo_lb=c['fibo'], atr_p=c['atr'],
        h1_ema=c['h1'], h4_ema=c['h4']
    )
    df_feat['Target_Dir'] = (df_feat['close'].shift(-5) > df_feat['close']).astype(int)
    df_clean = df_feat.dropna(subset=FEATS + ['Target_Dir'])

    n_total = len(df_clean)
    n_train = int(n_total * 0.70)
    train_df = df_clean.iloc[:n_train]
    test_df = df_clean.iloc[n_train:]

    X_train, y_train = train_df[FEATS], train_df['Target_Dir']
    X_test, y_test = test_df[FEATS], test_df['Target_Dir']

    clf = LGBMClassifier(
        n_estimators=100, max_depth=5, learning_rate=0.05,
        num_leaves=31, subsample=0.8, colsample_bytree=0.8,
        random_state=42, verbose=-1, n_jobs=-1
    )
    clf.fit(X_train, y_train)

    probs = clf.predict_proba(X_test)
    test_res = test_df.copy()
    test_res['p_buy'] = probs[:, 1]
    test_res['p_sell'] = probs[:, 0]

    CONF_THRESH = 0.58
    TP_DIST = 8.50
    SL_DIST = 6.50
    COMMISSION = 0.35

    wins = 0; losses = 0; beps = 0; net_pnl = 0.0; total_trades = 0
    test_idx = list(test_res.index)

    for i in range(len(test_idx) - 40):
        row = test_res.iloc[i]
        p_b = row['p_buy']
        p_s = row['p_sell']

        if p_b < CONF_THRESH and p_s < CONF_THRESH:
            continue
        direction = 'BUY' if p_b >= p_s else 'SELL'
        entry_price = row['close']
        future_slice = test_res.iloc[i+1 : i+40]

        hit_tp = False; hit_sl = False; pnl = 0.0; result = 'HOLD'

        if direction == 'BUY':
            tp = entry_price + TP_DIST
            sl = entry_price - SL_DIST
            for _, f_row in future_slice.iterrows():
                if f_row['low'] <= sl:
                    hit_sl = True; pnl = -SL_DIST - COMMISSION; break
                elif f_row['high'] >= tp:
                    hit_tp = True; pnl = TP_DIST - COMMISSION; break
            if not hit_tp and not hit_sl:
                exit_p = future_slice.iloc[-1]['close']
                pnl = (exit_p - entry_price) - COMMISSION
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')
            else:
                result = 'WIN' if hit_tp else 'LOSS'
        else:
            tp = entry_price - TP_DIST
            sl = entry_price + SL_DIST
            for _, f_row in future_slice.iterrows():
                if f_row['high'] >= sl:
                    hit_sl = True; pnl = -SL_DIST - COMMISSION; break
                elif f_row['low'] <= tp:
                    hit_tp = True; pnl = TP_DIST - COMMISSION; break
            if not hit_tp and not hit_sl:
                exit_p = future_slice.iloc[-1]['close']
                pnl = (entry_price - exit_p) - COMMISSION
                result = 'WIN' if pnl > 0.5 else ('LOSS' if pnl < -0.5 else 'BEP')
            else:
                result = 'WIN' if hit_tp else 'LOSS'

        total_trades += 1
        net_pnl += pnl
        if result == 'WIN': wins += 1
        elif result == 'LOSS': losses += 1
        else: beps += 1

    wr = (wins / total_trades * 100) if total_trades > 0 else 0
    pnl_str = f"{'+$' if net_pnl >= 0 else '-$'}{abs(net_pnl):.2f}"
    elapsed = time.time() - t0
    print(f"[{c_idx}/{len(combos)}] {c['name']:<55} | Trades: {total_trades:>4} | WR: {wr:>5.1f}% | Net PnL: {pnl_str:>10} ({elapsed:.1f}s)")
    results.append({'name': c['name'], 'trades': total_trades, 'wins': wins, 'losses': losses, 'beps': beps, 'wr': wr, 'pnl': net_pnl})

print("\n" + "="*95)
print("KLASEMEN AKHIR KOMBINASI PARAMETER")
print("="*95)
df_rank = pd.DataFrame(results).sort_values('pnl', ascending=False)
for r, (_, row) in enumerate(df_rank.iterrows(), 1):
    p_str = f"{'+$' if row['pnl'] >= 0 else '-$'}{abs(row['pnl']):.2f}"
    marker = " 🏆 TERBAIK!" if r == 1 else ""
    print(f"#{r} | {row['name']:<55} | WR: {row['wr']:>5.1f}% | PnL: {p_str:>10} | Trades: {row['trades']}{marker}")
