"""
========================================================================================
EKSPERIMEN EMPIRIS: INTEGRASI FITUR PANTULAN MA 10 & PERSILANGAN EMA 9/26 PADA M15
========================================================================================
Menguji hipotesis visual user:
1. Pantulan lilin saat menyentuh MA 10 (Dynamic Support/Resistance M15)
2. Persilangan & Pullback EMA 9 & EMA 26 (TradingView M15 Setup)
Diuji secara out-of-sample 2.5 bulan (4.980 candle M15) melawan Model V5.0 Baseline.
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

print("📥 Mengambil data 25.000 candle M15, H1, H4 dari MT5...")
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
# 1. FITUR BASELINE V5.0 (50 FITUR LENGKAP)
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
df_h1_loc['Trend_H1_Bull']   = (h1_close > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close - df_h1_loc['EMA_50_H1']) / (h1_close + 1e-9)

# H4 Baseline (50, 200)
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

# 6 Fitur Zona Spasial V5.0
df['Zone_A_Bounce_Bull'] = ((df['Dist_Support'] <= 0.0015) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_A_Bounce_Bear'] = ((df['Dist_Resistance'] <= 0.0015) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Zone_B_Prox_Bull']   = ((df['Dist_Support'] <= 0.0040) & (df['Lower_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_B_Prox_Bear']   = ((df['Dist_Resistance'] <= 0.0040) & (df['Upper_Wick_Ratio'] >= 0.18)).astype(int)
df['Zone_Clearance_Safe_Bull'] = (df['Dist_Resistance'] >= 0.0018).astype(int)
df['Zone_Clearance_Safe_Bear'] = (df['Dist_Support'] >= 0.0018).astype(int)

features_v50 = [
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

# -----------------------------------------------------------------------------
# 2. FITUR BARU USULAN USER:
#    A. MA 10 PADA TIMEFRAME M15 (FOTO 1)
#    B. PERSILANGAN & PULLBACK EMA 9 & EMA 26 PADA M15 (FOTO 2)
# -----------------------------------------------------------------------------
# A. MA 10 M15
ema10_m15 = df['close'].ewm(span=10, adjust=False).mean()
df['Dist_EMA10_M15'] = (df['close'] - ema10_m15) / df['close']
# Pantulan MA 10: low/high menyentuh EMA 10 dan terjadi penolakan ekor
df['Bounce_MA10_Bull'] = ((df['low'] <= ema10_m15) & (df['close'] > ema10_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)
df['Bounce_MA10_Bear'] = ((df['high'] >= ema10_m15) & (df['close'] < ema10_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)

features_ma10 = features_v50 + ['Dist_EMA10_M15', 'Bounce_MA10_Bull', 'Bounce_MA10_Bear']

# B. PERSILANGAN EMA 9 & EMA 26 M15 (TRADINGVIEW FOTO 2)
ema9_m15  = df['close'].ewm(span=9, adjust=False).mean()
ema26_m15 = df['close'].ewm(span=26, adjust=False).mean()
df['EMA_9_Cross_26_Bull'] = (ema9_m15 > ema26_m15).astype(int)
df['Dist_EMA9_M15']  = (df['close'] - ema9_m15) / df['close']
df['Dist_EMA26_M15'] = (df['close'] - ema26_m15) / df['close']
df['Spread_EMA_9_26'] = (ema9_m15 - ema26_m15) / df['close']
# Pullback Rejection di EMA 9/26 saat tren bearish kuat (persis gambar 2)
df['Pullback_EMA_Bear'] = ((df['EMA_9_Cross_26_Bull'] == 0) & (df['high'] >= ema9_m15) & (df['close'] < ema9_m15) & (df['Upper_Wick_Ratio'] >= 0.20)).astype(int)
df['Pullback_EMA_Bull'] = ((df['EMA_9_Cross_26_Bull'] == 1) & (df['low'] <= ema9_m15) & (df['close'] > ema9_m15) & (df['Lower_Wick_Ratio'] >= 0.20)).astype(int)

features_ema9_26 = features_v50 + [
    'EMA_9_Cross_26_Bull', 'Dist_EMA9_M15', 'Dist_EMA26_M15', 'Spread_EMA_9_26',
    'Pullback_EMA_Bull', 'Pullback_EMA_Bear'
]

# C. KOMBO LENGKAP (V5.0 + MA10 + PERSILANGAN EMA 9/26)
features_combo = list(dict.fromkeys(features_ma10 + features_ema9_26))

print(f"Jumlah Fitur V5.0 Baseline      : {len(features_v50)}")
print(f"Jumlah Fitur + MA10 M15         : {len(features_ma10)} (+3 Fitur)")
print(f"Jumlah Fitur + EMA 9/26 M15     : {len(features_ema9_26)} (+6 Fitur)")
print(f"Jumlah Fitur + Kombo Lengkap    : {len(features_combo)} (+9 Fitur)")

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
all_cols = list(set(features_combo + ['Target_Dir', 'open', 'high', 'low', 'close']))
df_clean = df.dropna(subset=all_cols).copy()

test_len = 4980
train_df = df_clean.iloc[:-test_len]
test_df  = df_clean.iloc[-test_len:]

t_start = test_df.index[0].strftime("%d %b %Y")
t_end   = test_df.index[-1].strftime("%d %b %Y")
print(f"📊 Dataset Siap! Train: {len(train_df)} | Test OOS: {len(test_df)} (~2.5 Bulan: {t_start} s/d {t_end})\n")

def simulate_real(test_data, probs, threshold=0.60):
    TOTAL_FRICTION = 0.35
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    n = len(closes)

    trades = []
    active_until = -1
    max_bars = 25
    tp_val = 6.50
    sl_val = 6.50
    equity = 500.0; peak_equity = 500.0; max_dd = 0.0

    for i in range(n - max_bars):
        if i <= active_until: continue
        p_up = probs[i]; p_dn = 1.0 - p_up
        sig = 'HOLD'
        if p_up >= threshold: sig = 'BUY'
        elif p_dn >= threshold: sig = 'SELL'
        if sig == 'HOLD': continue

        entry_p = closes[i]
        tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
        sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
        cur_sl = sl_p
        bep_locked = False; trailing_locked = False; pnl = 0.0; result = 'HOLD'

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
    if n_t == 0: return {'trades': 0, 'wr': 0, 'pnl': 0, 'pf': 0, 'max_dd': 0}
    w = len(df_t[df_t['result'] == 'WIN'])
    l = len(df_t[df_t['result'] == 'LOSS'])
    b = len(df_t[df_t['result'] == 'BEP'])
    wr = (w / n_t) * 100.0
    tot_pnl = df_t['pnl'].sum()
    gw = df_t[df_t['pnl'] > 0]['pnl'].sum()
    gl = abs(df_t[df_t['pnl'] < 0]['pnl'].sum())
    pf = (gw / (gl + 1e-6)) if gl > 0 else gw
    return {'trades': n_t, 'wins': w, 'losses': l, 'beps': b, 'wr': wr, 'pnl': tot_pnl, 'pf': pf, 'max_dd': max_dd}

models_test = [
    {'name': '1. V5.0 Baseline Kemarin (50 Fitur)', 'feats': features_v50, 'desc': 'Baseline 50 fitur tanpa MA M15'},
    {'name': '2. V5.0 + MA 10 M15 Bounce (53 Fitur)',  'feats': features_ma10, 'desc': 'Ditambah fitur pantulan MA 10 M15 (Foto 1)'},
    {'name': '3. V5.0 + Persilangan EMA 9/26 (56 Fitur)', 'feats': features_ema9_26, 'desc': 'Ditambah persilangan & pullback EMA 9/26 (Foto 2)'},
    {'name': '4. V5.0 + MA 10 & EMA 9/26 Kombo (59 Fitur)', 'feats': features_combo, 'desc': 'Kombo lengkap MA 10 + EMA 9/26 M15'}
]

lgb_params = dict(n_estimators=400, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)

results_summary = []
print("="*115)
print("HASIL PENGUJIAN KOMPARASI FITUR PANTULAN MA10 & PERSILANGAN EMA 9/26 (THRESHOLD 0.60)")
print("="*115)

for m in models_test:
    t0 = time.time()
    clf = LGBMClassifier(**lgb_params)
    clf.fit(train_df[m['feats']].values, train_df['Target_Dir'].values)

    probs = clf.predict_proba(test_df[m['feats']].values)[:, 1]
    y_true = test_df['Target_Dir'].values

    acc = accuracy_score(y_true, (probs >= 0.50).astype(int)) * 100.0
    auc = roc_auc_score(y_true, probs) * 100.0

    sim_60 = simulate_real(test_df, probs, threshold=0.60)
    sim_65 = simulate_real(test_df, probs, threshold=0.65)

    dur = time.time() - t0
    pnl_s = f"{'+$' if sim_60['pnl'] >= 0 else '-$'}{abs(sim_60['pnl']):.2f}"
    print(f"▶ {m['name']:<46} | ML Acc: {acc:>5.2f}% | AUC: {auc:>5.2f}% | Trades: {sim_60['trades']:>4} | WR: {sim_60['wr']:>5.2f}% | PnL: {pnl_s:>10} | Max DD: ${sim_60['max_dd']:>5.2f} ({dur:.1f}s)")

    results_summary.append({
        'Model': m['name'],
        'Fitur': len(m['feats']),
        'ML Acc': f"{acc:.2f}%",
        'AUC': f"{auc:.2f}%",
        'Trades': sim_60['trades'],
        'Win Rate': f"{sim_60['wr']:.2f}%",
        'Net PnL': sim_60['pnl'],
        'Profit Factor': f"{sim_60['pf']:.2f}",
        'Max Drawdown': f"${sim_60['max_dd']:.2f}",
        'Sniper WR (0.65)': f"{sim_65['wr']:.2f}%",
        'Sniper PnL': f"{'+$' if sim_65['pnl']>=0 else '-$'}{abs(sim_65['pnl']):.2f}"
    })

print("\n" + "="*115)
print("📊 KLASEMEN AKHIR PENGUJIAN MA 10 & PERSILANGAN EMA 9/26 M15")
print("="*115)
df_res = pd.DataFrame(results_summary)
for _, r in df_res.iterrows():
    pnl_str = f"{'+$' if r['Net PnL'] >= 0 else '-$'}{abs(r['Net PnL']):.2f}"
    print(f"{r['Model']:<46} | WR: {r['Win Rate']:<7} | Net PnL: {pnl_str:<10} | PF: {r['Profit Factor']:<5} | Max DD: {r['Max Drawdown']:<8} | Sniper WR: {r['Sniper WR (0.65)']}")
print("="*115)

# Cek Feature Importance dari model pemenang
best_idx = df_res['Net PnL'].idxmax()
best_m = models_test[best_idx]
clf_best = LGBMClassifier(**lgb_params).fit(train_df[best_m['feats']].values, train_df['Target_Dir'].values)
imps = pd.Series(clf_best.feature_importances_, index=best_m['feats']).sort_values(ascending=False)
print(f"\nTop 15 Feature Importances Model Terbaik ({best_m['name']}):")
for f_n, val in imps.head(15).items():
    star = " 🌟 [FITUR USULAN USER]" if any(k in f_n for k in ['EMA', 'MA', 'Bounce', 'Cross', 'Pullback']) and ('H1' not in f_n and 'H4' not in f_n) else ""
    print(f"  - {f_n:<30}: {val}{star}")
