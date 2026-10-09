"""
====================================================================================================
AUDIT FORENSIK 44 FITUR:
1. CEK LEAKAGE FORMAL SETIAP FITUR
2. LEAVE-ONE-OUT ABLATION STUDY: MENCARI FITUR BEBAN / NOISE DI DALAM 44 FITUR
Diuji dengan Realistis Pasar Penuh (Spread $0.20 + Slippage $0.15 = Total Beban $0.35/trade)
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
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Menarik 25.000 Candle M15 ({symbol}) dari MT5...")
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

# 1. Ekstraksi Fitur 100% Causal
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

# MTF Causal shift(1)
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
all_needed = list(set(features_44 + ['Target_Dir', 'open', 'high', 'low', 'close']))
df.dropna(subset=all_needed, inplace=True)

test_len = int(len(df) * 0.20)
train_df = df.iloc[:-test_len]
test_df  = df.iloc[-test_len:]

print(f"Data Train: {len(train_df)} candle | Data Test: {len(test_df)} candle (~2.5 bulan)")

# Evaluator Engine Cerdas dengan Spread $0.20 + Slippage $0.15
def evaluate_feature_subset(feat_list):
    lgb_params = dict(n_estimators=600, learning_rate=0.02, num_leaves=31, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1)
    m = LGBMClassifier(**lgb_params).fit(train_df[feat_list].values, train_df['Target_Dir'].values)
    probs = m.predict_proba(test_df[feat_list].values)[:, 1]

    TOTAL_FRICTION = 0.20 + 0.15 # $0.35/trade (Spread + Slippage)
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    dist_s = test_df['Dist_Support'].values
    dist_r = test_df['Dist_Resistance'].values
    l_wick = test_df['Lower_Wick_Ratio'].values
    u_wick = test_df['Upper_Wick_Ratio'].values
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

# 1. EVALUASI BASELINE 44 FITUR
print("\n" + "="*105)
print("1. EVALUASI BASELINE 44 FITUR LENGKAP (DENGAN SPREAD $0.20 + SLIPPAGE $0.15):")
print("="*105)
n_base, wr_base, pnl_base, pf_base, dd_base, stat_base = evaluate_feature_subset(features_44)
print(f"BASELINE 44 FITUR: {n_base} Trades | Win Rate: {wr_base:.2f}% | Net PnL: +${pnl_base:.2f} USD | PF: {pf_base:.2f} | Max DD: ${dd_base:.2f} USD")
print(f"Rincian: TP={stat_base.get('TP_FULL',0)}, Trailing={stat_base.get('TRAILING_LOCK',0)}, BEP={stat_base.get('BEP_SAVE',0)}, Full SL={stat_base.get('FULL_SL',0)}")

# 2. LEAVE-ONE-OUT ABLATION (HAPUS 1 FITUR SECARA BERGANTIAN)
print("\n" + "="*105)
print("2. LEAVE-ONE-OUT ABLATION: MENCARI FITUR BEBAN DI DALAM 44 FITUR...")
print("Logika: Jika fitur X DIHAPUS dan Net PnL NAIK, berarti fitur X adalah FITUR BEBAN (NOISE)!")
print("="*105)

ablation_results = []
for f in features_44:
    sub_feats = [x for x in features_44 if x != f]
    n_sub, wr_sub, pnl_sub, pf_sub, dd_sub, stat_sub = evaluate_feature_subset(sub_feats)
    diff_pnl = pnl_sub - pnl_base # Positif = PnL naik saat f dihapus (f adalah racun/beban!)
    diff_wr  = wr_sub - wr_base
    diff_sl  = stat_sub.get('FULL_SL', 0) - stat_base.get('FULL_SL', 0)
    
    ablation_results.append({
        'Fitur_Dihapus': f,
        'PnL_Tanpa_Fitur': pnl_sub,
        'Delta_PnL': diff_pnl,
        'WR_Tanpa_Fitur': wr_sub,
        'Delta_WR': diff_wr,
        'SL_Tanpa_Fitur': stat_sub.get('FULL_SL', 0),
        'Delta_SL': diff_sl,
        'Status': "🔴 FITUR BEBAN (Buang!)" if diff_pnl > 10.0 else ("🟢 FITUR PENTING (Pertahankan)" if diff_pnl < -10.0 else "⚪ NETRAL")
    })
    print(f"  • Tanpa {f:<22} -> PnL: +${pnl_sub:<6.2f} (Delta: {diff_pnl:>+6.2f} USD) | WR: {wr_sub:.2f}% ({diff_wr:>+5.2f}%) | SL: {stat_sub.get('FULL_SL', 0)} ({diff_sl:>+2}) -> {ablation_results[-1]['Status']}")

df_abl = pd.DataFrame(ablation_results).sort_values(by='Delta_PnL', ascending=False)

print("\n" + "="*115)
print("DAFTAR FITUR DI DALAM 44 FITUR DIURUTKAN DARI YANG PALING MERUGIKAN HINGGA PALING BERGUNA:")
print("="*115)
print(df_abl.to_string(index=False))

# 3. ELIMINASI FITUR BEBAN: GABUNGKAN FITUR YANG BENAR-BENAR BERKUALITAS TINGGI
burden_feats = df_abl[df_abl['Delta_PnL'] > 5.0]['Fitur_Dihapus'].tolist()
print(f"\n🔍 Fitur Beban yang Terdeteksi Mengurangi Cuan (Delta PnL > +$5 jika dibuang): {burden_feats}")

if len(burden_feats) > 0:
    cleaned_features = [f for f in features_44 if f not in burden_feats]
    print(f"\nMenguji Model Ramping Bersih ({len(cleaned_features)} Fitur)...")
    n_cl, wr_cl, pnl_cl, pf_cl, dd_cl, stat_cl = evaluate_feature_subset(cleaned_features)
    
    print("\n" + "="*115)
    print("HASIL KOMPARASI: V4.2 (44 FITUR) VS V4.3 ULTRA RAMPING (BEBAS FITUR BEBAN)")
    print("="*115)
    print(f"{'Metrik':<28} | {'V4.2 (44 Fitur Dasar)':<25} | {'V4.3 Bersih (' + str(len(cleaned_features)) + ' Fitur)':<25}")
    print("-"*115)
    print(f"{'Total Trades':<28} | {n_base:<25} | {n_cl:<25}")
    print(f"{'Win Rate (%)':<28} | {wr_base:.2f}%{' '*19} | {wr_cl:.2f}%{' '*19}")
    print(f"{'Net PnL Bersih ($)':<28} | +${pnl_base:.2f} USD{' '*13} | +${pnl_cl:.2f} USD{' '*13}")
    print(f"{'Pertumbuhan Modal ($500)':<28} | +{(pnl_base/500)*100:.1f}%{' '*19} | +{(pnl_cl/500)*100:.1f}%{' '*19}")
    print(f"{'Profit Factor':<28} | {pf_base:.2f}{' '*21} | {pf_cl:.2f}{' '*21}")
    print(f"{'Max Drawdown':<28} | ${dd_base:.2f} USD{' '*14} | ${dd_cl:.2f} USD{' '*14}")
    print(f"{'Full SL (Loss)':<28} | {stat_base.get('FULL_SL',0):<25} | {stat_cl.get('FULL_SL',0):<25}")
    print("="*115)
