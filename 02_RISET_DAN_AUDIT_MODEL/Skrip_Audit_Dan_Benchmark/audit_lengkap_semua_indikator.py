"""
AUDIT MENYELURUH SEMUA INDIKATOR (RSI, BB, ATR, ADX, H1 EMA, H4 EMA, SWING, VOLUME)
Menguji secara sistematis apakah ada parameter yang lebih optimal dari seluruh indikator.
"""
import sys, os, time, warnings
warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
mt5.initialize(path=MT5_PATH)
symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"

print("📥 Mengunduh data pasar (M15, H1, H4)...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 30000)
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 10000)
rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 3000)
mt5.shutdown()

df_raw = pd.DataFrame(rates_m15); df_raw['time'] = pd.to_datetime(df_raw['time'], unit='s'); df_raw.set_index('time', inplace=True)
df_h1_raw = pd.DataFrame(rates_h1); df_h1_raw['time'] = pd.to_datetime(df_h1_raw['time'], unit='s'); df_h1_raw.set_index('time', inplace=True)
df_h4_raw = pd.DataFrame(rates_h4); df_h4_raw['time'] = pd.to_datetime(df_h4_raw['time'], unit='s'); df_h4_raw.set_index('time', inplace=True)

# DXY Proxy
try:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)
except Exception:
    dxy_close = df_raw['close'] * 0 + 104.0

def build_features(df_m15, df_h1, df_h4,
                   rsi_period=14,
                   bb_period=10,
                   atr_period=14,
                   adx_period=14,
                   h1_fast=10, h1_slow=50,
                   h4_fast=20, h4_slow=100,
                   swing_lb=20,
                   vol_roll=20):
    df = df_m15.copy()
    range_m15 = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_m15
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_m15
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_m15

    df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
    df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)

    df['Swing_High_20'] = df['high'].shift(1).rolling(swing_lb).max()
    df['Swing_Low_20']  = df['low'].shift(1).rolling(swing_lb).min()
    df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
    df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']

    df['BOS_Bull'] = (df['close'] > df['Swing_High_20']).astype(int)
    df['BOS_Bear'] = (df['close'] < df['Swing_Low_20']).astype(int)
    trend_slow = df['close'].pct_change(swing_lb)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
    df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

    is_bear_c = df['close'] < df['open']; is_bull_c = df['close'] > df['open']
    body_sz = (df['close'] - df['open']).abs()
    avg_body = body_sz.rolling(swing_lb).mean()
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

    # RSI
    delta15 = df['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(rsi_period).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(rsi_period).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))

    # Bollinger Bands
    sma_bb = df['close'].rolling(bb_period).mean()
    std_bb = df['close'].rolling(bb_period).std()
    df['BB_Bandwidth'] = (4 * std_bb) / (sma_bb + 1e-9)
    df['BB_Pos'] = (df['close'] - (sma_bb - 2*std_bb)) / (4*std_bb + 1e-6)

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

    # MTF H1
    h1_close = df_h1['close'].shift(1)
    df_h1_loc = df_h1.copy()
    df_h1_loc['EMA_fast_H1'] = h1_close.ewm(span=h1_fast, adjust=False).mean()
    df_h1_loc['EMA_slow_H1'] = h1_close.ewm(span=h1_slow, adjust=False).mean()
    df_h1_loc['Trend_H1_Bull']   = (h1_close > df_h1_loc['EMA_fast_H1']).astype(int)
    df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_fast_H1'] > df_h1_loc['EMA_slow_H1']).astype(int)
    df_h1_loc['H1_Dist_EMA50']   = (h1_close - df_h1_loc['EMA_fast_H1']) / (h1_close + 1e-9)

    # MTF H4
    h4_close = df_h4['close'].shift(1)
    df_h4_loc = df_h4.copy()
    df_h4_loc['EMA_fast_H4'] = h4_close.ewm(span=h4_fast, adjust=False).mean()
    df_h4_loc['EMA_slow_H4'] = h4_close.ewm(span=h4_slow, adjust=False).mean()
    df_h4_loc['Trend_H4_Bull']   = (h4_close > df_h4_loc['EMA_fast_H4']).astype(int)
    df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_fast_H4'] > df_h4_loc['EMA_slow_H4']).astype(int)
    df_h4_loc['H4_Dist_EMA50']   = (h4_close - df_h4_loc['EMA_fast_H4']) / (h4_close + 1e-9)

    for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
        df[c] = df_h1_loc[c].reindex(df.index, method='ffill').fillna(0)
    for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
        df[c] = df_h4_loc[c].reindex(df.index, method='ffill').fillna(0)

    is_bull = (df['close'] > df['open']).astype(int)
    is_bear = (df['close'] < df['open']).astype(int)
    df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
    df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

    # ATR & ADX
    high_diff = df['high'].diff(); low_diff = -df['low'].diff()
    plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
    minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
    tr = pd.concat([df['high'] - df['low'], (df['high'] - df['close'].shift()).abs(), (df['low'] - df['close'].shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean() + 1e-6
    df['ATR_14'] = atr
    plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(adx_period).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(adx_period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
    df['ADX_14'] = dx.rolling(adx_period).mean()

    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(vol_roll).mean() + 1e-6)

    # 6 Fitur Zona
    df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
    df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
    df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
    df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

    feats = [
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
    return df, feats

def evaluate_config(cfg):
    df_feat, feats = build_features(
        df_raw, df_h1_raw, df_h4_raw,
        rsi_period=cfg.get('rsi', 14),
        bb_period=cfg.get('bb', 10),
        atr_period=cfg.get('atr', 14),
        adx_period=cfg.get('adx', 14),
        h1_fast=cfg.get('h1', (10, 50))[0], h1_slow=cfg.get('h1', (10, 50))[1],
        h4_fast=cfg.get('h4', (20, 100))[0], h4_slow=cfg.get('h4', (20, 100))[1],
        swing_lb=cfg.get('swing', 20),
        vol_roll=cfg.get('vol', 20)
    )

    df_feat['Target_Dir'] = (df_feat['close'].shift(-5) > df_feat['close']).astype(int)
    df_clean = df_feat.dropna(subset=feats + ['Target_Dir']).copy()

    split_idx = int(len(df_clean) * 0.80)
    train = df_clean.iloc[:split_idx]
    test = df_clean.iloc[split_idx:]

    X_train = train[feats].values; y_train = train['Target_Dir'].values
    X_test = test[feats].values; y_test = test['Target_Dir'].values

    model = LGBMClassifier(n_estimators=400, learning_rate=0.02, num_leaves=31,
                           subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
    model.fit(X_train, y_train)

    probs = model.predict_proba(X_test)
    test = test.copy()
    test['prob_up'] = probs[:, 1] * 100.0
    test['prob_down'] = probs[:, 0] * 100.0

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
    return {
        'name': cfg['name'],
        'trades': total_trades,
        'wins': wins, 'losses': losses, 'beps': beps,
        'wr': wr, 'pnl': net_pnl
    }

# DAFTAR PENGUJIAN DETAIL PER INDIKATOR
test_suites = [
    # Baseline & Current Winner
    {'name': '1. Baseline Saat Ini (H1 50/200, H4 50/200, BB 20, RSI 14)',
     'rsi': 14, 'bb': 20, 'atr': 14, 'adx': 14, 'h1': (50, 200), 'h4': (50, 200), 'swing': 20, 'vol': 20},
    {'name': '2. Juara Terkini Sinergi D (H1 10/50, H4 20/100, BB 10, RSI 14)',
     'rsi': 14, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},

    # Variasi RSI di atas Juara Sinergi D
    {'name': '3. Sinergi D + RSI 9 (Fast RSI)',
     'rsi': 9,  'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '4. Sinergi D + RSI 12 (Intermediate RSI)',
     'rsi': 12, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '5. Sinergi D + RSI 16 (Smoothed RSI)',
     'rsi': 16, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '6. Sinergi D + RSI 21 (Long-period RSI)',
     'rsi': 21, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},

    # Variasi BB di atas Juara Sinergi D
    {'name': '7. Sinergi D + BB 8 (Ultra-fast BB)',
     'rsi': 14, 'bb': 8,  'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '8. Sinergi D + BB 12 (Balanced BB)',
     'rsi': 14, 'bb': 12, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '9. Sinergi D + BB 14 (Standard 14 BB)',
     'rsi': 14, 'bb': 14, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},

    # Variasi ATR & ADX
    {'name': '10. Sinergi D + ATR 10 / ADX 10 (Fast Volatility)',
     'rsi': 14, 'bb': 10, 'atr': 10, 'adx': 10, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '11. Sinergi D + ATR 20 / ADX 20 (Smoothed Volatility)',
     'rsi': 14, 'bb': 10, 'atr': 20, 'adx': 20, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 20},

    # Variasi H1 EMA fine-tuning
    {'name': '12. Sinergi D + H1 (8, 34) (Fibonacci EMA Pair)',
     'rsi': 14, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (8, 34),  'h4': (20, 100), 'swing': 20, 'vol': 20},
    {'name': '13. Sinergi D + H1 (12, 48) (Exact 3h/12h Cycle)',
     'rsi': 14, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (12, 48), 'h4': (20, 100), 'swing': 20, 'vol': 20},

    # Variasi Volume Ratio Rolling
    {'name': '14. Sinergi D + Volume Window 10 (Fast Spike)',
     'rsi': 14, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 10},
    {'name': '15. Sinergi D + Volume Window 30 (Broad Spike)',
     'rsi': 14, 'bb': 10, 'atr': 14, 'adx': 14, 'h1': (10, 50), 'h4': (20, 100), 'swing': 20, 'vol': 30},
]

print("\n" + "="*95)
print("MEMULAI AUDIT MENYELURUH 15 VARIASI PARAMETER DETAIL")
print("="*95)

all_results = []
for idx, cfg in enumerate(test_suites, 1):
    t0 = time.time()
    res = evaluate_config(cfg)
    pnl_str = f"{'+$' if res['pnl'] >= 0 else '-$'}{abs(res['pnl']):.2f}"
    dur = time.time() - t0
    print(f"[{idx:>2}/{len(test_suites)}] {res['name']:<58} | WR: {res['wr']:>5.1f}% | PnL: {pnl_str:>10} ({dur:.1f}s)")
    all_results.append(res)

print("\n" + "="*95)
print("HASIL LENGKAP PERINGKAT PARAMETER TERBAIK (FINAL)")
print("="*95)
df_final = pd.DataFrame(all_results).sort_values('pnl', ascending=False)
for r, (_, row) in enumerate(df_final.iterrows(), 1):
    p_str = f"{'+$' if row['pnl'] >= 0 else '-$'}{abs(row['pnl']):.2f}"
    marker = " 👑 ABSOLUTE BEST" if r == 1 else ""
    print(f"#{r:>2} | {row['name']:<58} | WR: {row['wr']:>5.1f}% | PnL: {p_str:>10} | Trades: {row['trades']}{marker}")

# Simpan hasil ke file CSV
csv_out = r"d:\SKRIPSI INFORMATIKA\02_RISET_DAN_AUDIT_MODEL\hasil_audit_detail_semua_indikator.csv"
df_final.to_csv(csv_out, index=False, encoding='utf-8-sig')
print(f"\nHasil tersimpan di: {csv_out}")
