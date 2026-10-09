import os
import sys
sys.path.insert(0, r"d:\SKRIPSI INFORMATIKA")
import numpy as np
import pandas as pd
import joblib
import MetaTrader5 as mt5
from sklearn.metrics import accuracy_score, roc_auc_score

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    mt5.initialize()

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 15000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 5000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2000)
try: rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 15000)
except Exception: rates_dxy = None
mt5.shutdown()

df_m = pd.DataFrame(rates_m15); df_m['time'] = pd.to_datetime(df_m['time'], unit='s'); df_m.set_index('time', inplace=True)
df_1 = pd.DataFrame(rates_h1); df_1['time'] = pd.to_datetime(df_1['time'], unit='s'); df_1.set_index('time', inplace=True)
df_4 = pd.DataFrame(rates_h4); df_4['time'] = pd.to_datetime(df_4['time'], unit='s'); df_4.set_index('time', inplace=True)
df_x = pd.DataFrame(rates_dxy) if rates_dxy is not None else None
if df_x is not None: df_x['time'] = pd.to_datetime(df_x['time'], unit='s'); df_x.set_index('time', inplace=True)

# Import feature extractors
from Eksekusi_Otomatis_Trading_Bot_M15_PRO import extract_77_features, FEATURES_77
from train_and_save_final_65_features_model import build_all_65_features, FEATURES_65

df_pro = extract_77_features(df_m, df_1, df_4, df_x).dropna()
# Test sample last 4500 bars (~3 months)
test_bars = 4500
test_pro = df_pro.iloc[-test_bars:].copy()

# Load models
model_pro = joblib.load(r"d:\SKRIPSI INFORMATIKA\model_m15_pro_77_features.pkl")

# Simulation PRO Sniper (>=65% conf)
probs_pro = model_pro.predict_proba(test_pro[FEATURES_77])
c_pro = test_pro['close'].values; h_pro = test_pro['high'].values; l_pro = test_pro['low'].values
shock_pro = test_pro['Shockwave_Extreme_Vol'].values
times_pro = test_pro.index

trades_pro = []
dates_pro = []
active_until = -1
for i in range(len(c_pro) - 25):
    if i <= active_until: continue
    if shock_pro[i] == 1: continue
    pb = probs_pro[i, 1]; ps = probs_pro[i, 0]
    conf = max(pb, ps)
    if conf < 0.65: continue # Sniper mode >= 65%
    
    is_buy = (pb >= ps)
    entry = c_pro[i]
    tp_val = 11.00 # Target $11
    sl_val = 6.50  # SL $6.50
    tp_p = entry + tp_val if is_buy else entry - tp_val
    sl_p = entry - sl_val if is_buy else entry + sl_val
    
    held = 25; pnl = 0.0
    for s in range(1, 26):
        cur = i + s
        hb = h_pro[cur]; lb = l_pro[cur]
        flt = (hb - entry) if is_buy else (entry - lb)
        cur_sl = (entry + 0.30) if (flt >= 2.20 and is_buy) else sl_p
        if not is_buy and flt >= 2.20:
            cur_sl = entry - 0.30
        
        hit_tp = (hb >= tp_p) if is_buy else (lb <= tp_p)
        hit_sl = (lb <= cur_sl) if is_buy else (hb >= cur_sl)
        if hit_tp:
            pnl = tp_val - 0.20
            held = s; break
        elif hit_sl:
            loss = (cur_sl - entry) if is_buy else (entry - cur_sl)
            pnl = loss - 0.20
            held = s; break
    else:
        pnl = ((c_pro[i+25] - entry) if is_buy else (entry - c_pro[i+25])) - 0.20
        
    trades_pro.append(pnl)
    dates_pro.append(times_pro[i])
    active_until = i + held

trades_pro = np.array(trades_pro)
n_pro = len(trades_pro)
win_pro = (trades_pro > 0.50).sum()
bep_pro = ((trades_pro >= -0.10) & (trades_pro <= 0.50)).sum()
loss_pro = (trades_pro < -0.10).sum()
wr_pro = (win_pro / max(1, win_pro + loss_pro)) * 100
gwin_pro = trades_pro[trades_pro > 0].sum()
gloss_pro = abs(trades_pro[trades_pro < 0].sum())
pf_pro = gwin_pro / max(0.01, gloss_pro)
net_pnl_pro = trades_pro.sum()
cum_pro = np.cumsum(trades_pro)
dd_pro = np.maximum.accumulate(np.insert(cum_pro, 0, 0)) - np.insert(cum_pro, 0, 0)
max_dd_pro = dd_pro.max()

# Trading day duration
total_days = (times_pro[-1] - times_pro[0]).days
t_per_day_pro = n_pro / max(1, (total_days * 5 / 7)) # workdays
days_100_pro = 100 / max(0.1, t_per_day_pro)

print("="*60)
print(f"PRO V5.4 (77 FITUR - SNIPER >= 65%):")
print(f"Total Trade: {n_pro} dalam {total_days} hari (~{total_days/30:.1f} bulan)")
print(f"Win: {win_pro}, BEP: {bep_pro}, Loss: {loss_pro}")
print(f"Win Rate (Excl BEP): {wr_pro:.2f}%")
print(f"Profit Factor: {pf_pro:.2f}")
print(f"Net PnL: +${net_pnl_pro:.2f} USD")
print(f"Max Drawdown: ${max_dd_pro:.2f} USD")
print(f"Trade per hari: {t_per_day_pro:.2f} trade/hari")
print(f"100 trade tercapai dalam: {days_100_pro:.1f} hari bursa (~{days_100_pro/20:.1f} bulan)")
print(f"Cuan terkecil: +${trades_pro[trades_pro > 0].min():.2f}")
print(f"Cuan terbesar: +${trades_pro.max():.2f}")
print(f"Rugi terbesar (terburuk): -${abs(trades_pro.min()):.2f}")
print("="*60)
