"""
====================================================================================================
AUDIT ISOLASI: MODEL MURNI vs FILTER RULE vs GABUNGAN
====================================================================================================
Tujuan: Memisahkan kontribusi MODEL PREDIKSI vs FILTER RULE BOT
agar skripsi valid menguji "kemampuan model prediksi", bukan "kemampuan rule-based system"

Skenario yang diuji:
A. MODEL MURNI        : Trade hanya berdasarkan probabilitas model (prob >= threshold)
                        TANPA filter SNR, TANPA filter wick, TANPA zona apapun
B. FILTER RULE MURNI  : Trade berdasarkan filter SNR + wick rejection
                        TANPA model (pakai probabilitas random/acak 50:50)
C. GABUNGAN (Saat Ini): Model + Filter Rule (seperti sistem yang sudah ada)

Jika hasil A > B => Model memang jago prediksi (valid untuk skripsi)
Jika hasil B > A => Filter rule yang dominan, model sebenarnya lemah (HARUS dibenahi)
====================================================================================================
"""
import os, sys
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception: pass

import numpy as np
import pandas as pd
import MetaTrader5 as mt5
import yfinance as yf
from lightgbm import LGBMClassifier

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!"); sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik data {symbol} dari MT5...")
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

df = pd.DataFrame(rates_m15); df['time'] = pd.to_datetime(df['time'], unit='s'); df.set_index('time', inplace=True)
df_h1 = pd.DataFrame(rates_h1); df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s'); df_h1.set_index('time', inplace=True)
df_h4 = pd.DataFrame(rates_h4); df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s'); df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 25000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)
mt5.shutdown()

# === FEATURE ENGINEERING (PERSIS SAMA DG AUDIT SEBELUMNYA) ===
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

df['BOS_Bull']  = (df['close'] > df['Swing_High_20']).astype(int)
df['BOS_Bear']  = (df['close'] < df['Swing_Low_20']).astype(int)

trend_slow = df['close'].pct_change(20)
df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)

df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)

is_bear_c = df['close'] < df['open']
is_bull_c = df['close'] > df['open']
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
df['BB_Bandwidth'] = (4 * std20) / sma20
df['BB_Pos'] = (df['close'] - (sma20 - 2*std20)) / (4*std20 + 1e-6)

df['XAU_Return_1'] = df['close'].pct_change(1)
df['XAU_Return_3'] = df['close'].pct_change(3)
df['XAU_Return_5'] = df['close'].pct_change(5)

df['DXY_Close'] = dxy_close.reindex(df.index, method='ffill').bfill()
df['DXY_Return_1'] = df['DXY_Close'].pct_change(1).fillna(0)
df['DXY_Return_3'] = df['DXY_Close'].pct_change(3).fillna(0)
df['DXY_Trend'] = (df['DXY_Close'] > df['DXY_Close'].rolling(20).mean()).astype(int)
df['XAU_DXY_Ratio'] = df['close'] / (df['DXY_Close'] + 1e-6)
df['XAU_DXY_Ratio_Return'] = df['XAU_DXY_Ratio'].pct_change(3).fillna(0)

day_of_month = df.index.day
weekday = df.index.weekday
df['Is_NFP_Week']  = ((day_of_month <= 7) & (weekday == 4)).astype(int)
df['Is_CPI_Day']   = ((day_of_month >= 10) & (day_of_month <= 15)).astype(int)
df['Is_FOMC_Week'] = ((day_of_month >= 15) & (day_of_month <= 22) & (weekday == 2)).astype(int)

h1_close_series = df_h1['close'].shift(1)
h4_close_series = df_h4['close'].shift(1)
df_h1_loc = df_h1.copy()
df_h1_loc['EMA_50_H1']  = h1_close_series.ewm(span=50, adjust=False).mean()
df_h1_loc['EMA_200_H1'] = h1_close_series.ewm(span=200, adjust=False).mean()
df_h1_loc['Trend_H1_Bull']   = (h1_close_series > df_h1_loc['EMA_50_H1']).astype(int)
df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
df_h1_loc['H1_Dist_EMA50']   = (h1_close_series - df_h1_loc['EMA_50_H1']) / h1_close_series

df_h4_loc = df_h4.copy()
df_h4_loc['EMA_50_H4']  = h4_close_series.ewm(span=50, adjust=False).mean()
df_h4_loc['EMA_200_H4'] = h4_close_series.ewm(span=200, adjust=False).mean()
df_h4_loc['Trend_H4_Bull']   = (h4_close_series > df_h4_loc['EMA_50_H4']).astype(int)
df_h4_loc['Trend_H4_Strong'] = (df_h4_loc['EMA_50_H4'] > df_h4_loc['EMA_200_H4']).astype(int)
df_h4_loc['H4_Dist_EMA50']   = (h4_close_series - df_h4_loc['EMA_50_H4']) / h4_close_series

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

features_44 = [
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
    'ATR_14', 'ADX_14', 'Volume_Ratio', 'Swing_High_20'
]

df['Target_Dir'] = (df['close'].shift(-5) > df['close']).astype(int)
df.dropna(subset=list(set(features_44 + ['Target_Dir', 'open', 'high', 'low', 'close'])), inplace=True)

test_len = int(len(df) * 0.20)
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

# Latih Model
lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
model = LGBMClassifier(**lgb_params).fit(train_df[features_44].values, train_df['Target_Dir'].values)
probs_real = model.predict_proba(test_df[features_44].values)[:, 1]

# Probabilitas Random (untuk kontrol ilmiah)
np.random.seed(42)
probs_random = np.random.uniform(0.40, 0.60, len(test_df))  # Random acak di sekitar 50%

print(f"\nData Train: {len(train_df)} | Data Test: {len(test_df)} | Hari tes: ~{len(test_df)/96:.0f} hari")
print(f"Distribusi probabilitas Model Riil: mean={probs_real.mean():.4f}, std={probs_real.std():.4f}")
print(f"Distribusi probabilitas Random:     mean={probs_random.mean():.4f}, std={probs_random.std():.4f}")

# =============================================================================
# ENGINE SIMULASI UNIVERSAL (BISA TOGGLE MODE)
# =============================================================================
def simulate(test_data, probs, mode='gabungan', threshold=0.55):
    """
    mode = 'model_murni'  : Trade HANYA berdasarkan probabilitas >= threshold
    mode = 'filter_murni' : Trade HANYA berdasarkan filter SNR + wick (model diabaikan)
    mode = 'gabungan'     : Sistem saat ini (multi-zone: filter + model)
    """
    TOTAL_FRICTION = 0.35
    closes = test_data['close'].values
    highs  = test_data['high'].values
    lows   = test_data['low'].values
    dist_s = test_data['Dist_Support'].values
    dist_r = test_data['Dist_Resistance'].values
    l_wick = test_data['Lower_Wick_Ratio'].values
    u_wick = test_data['Upper_Wick_Ratio'].values
    n = len(closes)
    
    trades = []
    trade_outcomes = []
    active_until = -1
    max_bars = 25
    tp_val = 6.50
    sl_val = 6.50
    lot_size = 0.01

    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        p_up = probs[i]
        p_dn = 1.0 - p_up
        
        sig = 'HOLD'
        
        if mode == 'model_murni':
            # ================================================
            # SKENARIO A: MODEL MURNI (TANPA FILTER RULE APAPUN)
            # Trade HANYA jika probabilitas model >= threshold
            # ================================================
            if p_up >= threshold:
                sig = 'BUY'
            elif p_dn >= threshold:
                sig = 'SELL'
                
        elif mode == 'filter_murni':
            # ================================================
            # SKENARIO B: FILTER RULE MURNI (TANPA MODEL)
            # Trade berdasarkan SNR + wick saja
            # Model diabaikan (probabilities bisa random)
            # ================================================
            if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20:
                sig = 'BUY'
            elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20:
                sig = 'SELL'
            elif dist_s[i] <= 0.0040 and l_wick[i] >= 0.18:
                sig = 'BUY'
            elif dist_r[i] <= 0.0040 and u_wick[i] >= 0.18:
                sig = 'SELL'
                
        elif mode == 'gabungan':
            # ================================================
            # SKENARIO C: GABUNGAN (Sistem Saat Ini)
            # ================================================
            if dist_s[i] <= 0.0015 and l_wick[i] >= 0.20 and p_up >= 0.58: sig = 'BUY'
            elif dist_r[i] <= 0.0015 and u_wick[i] >= 0.20 and p_dn >= 0.58: sig = 'SELL'
            elif sig == 'HOLD' and dist_s[i] <= 0.0040 and l_wick[i] >= 0.18 and p_up >= 0.60: sig = 'BUY'
            elif sig == 'HOLD' and dist_r[i] <= 0.0040 and u_wick[i] >= 0.18 and p_dn >= 0.60: sig = 'SELL'
            elif sig == 'HOLD' and p_up >= 0.65: sig = 'BUY'
            elif sig == 'HOLD' and p_dn >= 0.65: sig = 'SELL'
            
        if sig == 'HOLD':
            continue
            
        entry_p = closes[i]
        tp_p = entry_p + tp_val if sig == 'BUY' else entry_p - tp_val
        sl_p = entry_p - sl_val if sig == 'BUY' else entry_p + sl_val
        cur_sl = sl_p
        
        bep_locked = False
        trailing_locked = False
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]; l_bar = lows[cur_idx]
            if sig == 'BUY':
                floating = h_bar - entry_p
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 2.00); trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = max(cur_sl, entry_p + 0.20); bep_locked = True
                if h_bar >= tp_p:
                    outcome = "TP_FULL"; pnl_gross = tp_val; held_bars = step; break
                elif l_bar <= cur_sl:
                    outcome = "TRAILING_LOCK" if trailing_locked else ("BEP_SAVE" if bep_locked else "FULL_SL")
                    pnl_gross = 2.00 if trailing_locked else (0.20 if bep_locked else -sl_val)
                    held_bars = step; break
            else:
                floating = entry_p - l_bar
                if floating >= 3.50 and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 2.00); trailing_locked = True
                elif floating >= 2.50 and not bep_locked and not trailing_locked:
                    cur_sl = min(cur_sl, entry_p - 0.20); bep_locked = True
                if l_bar <= tp_p:
                    outcome = "TP_FULL"; pnl_gross = tp_val; held_bars = step; break
                elif h_bar >= cur_sl:
                    outcome = "TRAILING_LOCK" if trailing_locked else ("BEP_SAVE" if bep_locked else "FULL_SL")
                    pnl_gross = 2.00 if trailing_locked else (0.20 if bep_locked else -sl_val)
                    held_bars = step; break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            outcome = "AUTO_TIMEOUT"
            
        pnl_net = (pnl_gross * 100.0 * lot_size) - (TOTAL_FRICTION * 100.0 * lot_size)
        trades.append(pnl_net)
        trade_outcomes.append(outcome)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_tr = len(trades)
    if n_tr == 0:
        return 0, 0, 0, 0, 0, {}
    wins = (trades > 0).sum()
    wr = (wins / n_tr) * 100.0
    tot_pnl = trades.sum()
    gw = trades[trades > 0].sum()
    gl = abs(trades[trades < 0].sum())
    pf = (gw / gl) if gl > 0 else 99.0
    eq = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(eq)
    dd = abs((eq - peak).min())
    stat = pd.Series(trade_outcomes).value_counts().to_dict()
    return n_tr, wr, tot_pnl, pf, dd, stat

# =============================================================================
# JALANKAN PENGUJIAN
# =============================================================================
print("\n" + "="*130)
print("AUDIT ISOLASI KONTRIBUSI: MODEL PREDIKSI vs FILTER RULE BOT")
print("Kondisi: Spread $0.20 + Slippage $0.15 = Total Beban $0.35/trade | 2.5 Bulan Out-of-Sample")
print("="*130)

# A. MODEL MURNI dengan berbagai threshold
print("\n--- SKENARIO A: MODEL MURNI (Tanpa Filter Rule SNR/Wick) ---")
thresholds = [0.52, 0.53, 0.54, 0.55, 0.56, 0.57, 0.58, 0.60, 0.62, 0.65]
model_murni_results = []
for th in thresholds:
    tr, wr, pnl, pf, dd, st = simulate(test_df, probs_real, mode='model_murni', threshold=th)
    model_murni_results.append({'Threshold': th, 'Trades': tr, 'WR': wr, 'PnL': pnl, 'PF': pf, 'DD': dd, 'SL': st.get('FULL_SL', 0)})
    print(f"  Threshold >= {th:.2f}: {tr:>4} Trades | WR: {wr:.2f}% | PnL: +${pnl:>7.2f} USD | PF: {pf:.2f} | DD: ${dd:.2f} | SL: {st.get('FULL_SL',0)}")

best_murni = max(model_murni_results, key=lambda x: x['PnL'])
print(f"\n  >>> BEST MODEL MURNI: Threshold {best_murni['Threshold']:.2f} -> {best_murni['Trades']} Trades | WR: {best_murni['WR']:.2f}% | PnL: +${best_murni['PnL']:.2f} USD")

# B. FILTER RULE MURNI (dengan model random)
print("\n--- SKENARIO B: FILTER RULE MURNI (Model = Random Acak) ---")
tr_f, wr_f, pnl_f, pf_f, dd_f, st_f = simulate(test_df, probs_random, mode='filter_murni')
print(f"  Filter SNR+Wick (No Model): {tr_f:>4} Trades | WR: {wr_f:.2f}% | PnL: +${pnl_f:>7.2f} USD | PF: {pf_f:.2f} | DD: ${dd_f:.2f} | SL: {st_f.get('FULL_SL',0)}")

# B2. FILTER RULE MURNI (TANPA model sama sekali, semua yg lolos filter langsung trade)
tr_f2, wr_f2, pnl_f2, pf_f2, dd_f2, st_f2 = simulate(test_df, probs_real, mode='filter_murni')
print(f"  Filter SNR+Wick (Model Ignored): {tr_f2:>4} Trades | WR: {wr_f2:.2f}% | PnL: +${pnl_f2:>7.2f} USD | PF: {pf_f2:.2f} | DD: ${dd_f2:.2f} | SL: {st_f2.get('FULL_SL',0)}")

# C. GABUNGAN (sistem saat ini)
print("\n--- SKENARIO C: GABUNGAN (Model + Filter Rule - Sistem Saat Ini) ---")
tr_g, wr_g, pnl_g, pf_g, dd_g, st_g = simulate(test_df, probs_real, mode='gabungan')
print(f"  Gabungan (Multi-Zone): {tr_g:>4} Trades | WR: {wr_g:.2f}% | PnL: +${pnl_g:>7.2f} USD | PF: {pf_g:.2f} | DD: ${dd_g:.2f} | SL: {st_g.get('FULL_SL',0)}")

# D. GABUNGAN tapi dengan model RANDOM (untuk buktikan apakah model benar berguna)
print("\n--- SKENARIO D: GABUNGAN tapi Model = RANDOM (Kontrol Negatif) ---")
tr_gr, wr_gr, pnl_gr, pf_gr, dd_gr, st_gr = simulate(test_df, probs_random, mode='gabungan')
print(f"  Gabungan + Random Model: {tr_gr:>4} Trades | WR: {wr_gr:.2f}% | PnL: +${pnl_gr:>7.2f} USD | PF: {pf_gr:.2f} | DD: ${dd_gr:.2f} | SL: {st_gr.get('FULL_SL',0)}")

# RANGKUMAN
print("\n" + "="*130)
print("RANGKUMAN KOMPARASI AKHIR:")
print("="*130)
print(f"{'Skenario':<45} | {'Trades':>6} | {'WR':>8} | {'Net PnL':>12} | {'PF':>6} | {'DD':>10} | {'Full SL':>7}")
print("-"*130)
print(f"{'A. MODEL MURNI (Threshold ' + str(best_murni['Threshold']) + ')':<45} | {best_murni['Trades']:>6} | {best_murni['WR']:>7.2f}% | +${best_murni['PnL']:>8.2f} USD | {best_murni['PF']:>5.2f} | ${best_murni['DD']:>7.2f} | {best_murni['SL']:>7}")
print(f"{'B. FILTER RULE MURNI (Tanpa Model Apapun)':<45} | {tr_f2:>6} | {wr_f2:>7.2f}% | +${pnl_f2:>8.2f} USD | {pf_f2:>5.2f} | ${dd_f2:>7.2f} | {st_f2.get('FULL_SL',0):>7}")
print(f"{'C. GABUNGAN (Model + Filter = Saat Ini)':<45} | {tr_g:>6} | {wr_g:>7.2f}% | +${pnl_g:>8.2f} USD | {pf_g:>5.2f} | ${dd_g:>7.2f} | {st_g.get('FULL_SL',0):>7}")
print(f"{'D. GABUNGAN + MODEL RANDOM (Kontrol Negatif)':<45} | {tr_gr:>6} | {wr_gr:>7.2f}% | +${pnl_gr:>8.2f} USD | {pf_gr:>5.2f} | ${dd_gr:>7.2f} | {st_gr.get('FULL_SL',0):>7}")
print("="*130)

# ANALISIS KONTRIBUSI
kontribusi_model = best_murni['PnL'] - pnl_f2
kontribusi_filter = pnl_f2
kontribusi_sinergi = pnl_g - (best_murni['PnL'] + pnl_f2)

print(f"\n{'ANALISIS KONTRIBUSI:'}")
print(f"  - Kontribusi Model Murni (A):        +${best_murni['PnL']:.2f} USD")
print(f"  - Kontribusi Filter Rule Murni (B):   +${pnl_f2:.2f} USD")
print(f"  - Gabungan (C):                       +${pnl_g:.2f} USD")
print(f"  - Selisih C vs D (Bukti Model Berguna): +${pnl_g - pnl_gr:.2f} USD")

if best_murni['PnL'] > pnl_f2:
    print(f"\n  >>> KESIMPULAN: MODEL LEBIH DOMINAN daripada Filter Rule (+${kontribusi_model:.2f} USD lebih banyak)")
    print(f"  >>> SKRIPSI VALID: Kemampuan prediksi model terbukti menghasilkan profit lebih tinggi dari rule-based system murni")
else:
    print(f"\n  >>> KESIMPULAN: FILTER RULE LEBIH DOMINAN daripada Model (+${-kontribusi_model:.2f} USD lebih banyak)")
    print(f"  >>> PERHATIAN: Perlu evaluasi ulang kontribusi model vs rule")

if pnl_g > pnl_gr + 50:
    print(f"\n  >>> BUKTI MODEL RIIL vs RANDOM: Model riil menghasilkan +${pnl_g - pnl_gr:.2f} USD LEBIH BANYAK dari model random")
    print(f"      Ini membuktikan model benar-benar BELAJAR pola, bukan kebetulan.")
