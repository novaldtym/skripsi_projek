import os
import sys
sys.path.insert(0, r"d:\SKRIPSI INFORMATIKA")
import numpy as np
import pandas as pd
import joblib
import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    mt5.initialize()

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print("Mengambil data MT5...")
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

# 1. EVALUASI MODEL SKRIPSI (65 FITUR)
from Eksekusi_Otomatis_Trading_Bot import extract_50_features, FEATURES_65
df_skripsi = extract_50_features(df_m, df_1, df_4, df_x).dropna()
model_skripsi = joblib.load(r"d:\SKRIPSI INFORMATIKA\model_m15_zone_integrated_50.pkl")

# Test on last 4940 bars (~4.5 months)
test_bars = 4940
test_skripsi = df_skripsi.iloc[-test_bars:].copy()
probs_skripsi = model_skripsi.predict_proba(test_skripsi[FEATURES_65])

c_skr = test_skripsi['close'].values; h_skr = test_skripsi['high'].values; l_skr = test_skripsi['low'].values
times_skr = test_skripsi.index

trades_skr = []
active_until = -1
for i in range(len(c_skr) - 25):
    if i <= active_until: continue
    pb = probs_skripsi[i, 1]; ps = probs_skripsi[i, 0]
    conf = max(pb, ps)
    if conf < 0.60: continue
    
    is_buy = (pb >= ps)
    entry = c_skr[i]
    tp_val = 11.00 if conf >= 0.65 else 8.50
    sl_val = 6.50
    tp_p = entry + tp_val if is_buy else entry - tp_val
    sl_p = entry - sl_val if is_buy else entry + sl_val
    
    held = 5 # Horizon skripsi: 5 candle (75m)
    pnl = 0.0
    for s in range(1, 6):
        cur = i + s
        hb = h_skr[cur]; lb = l_skr[cur]
        flt = (hb - entry) if is_buy else (entry - lb)
        cur_sl = (entry + 0.20) if (flt >= 2.50 and is_buy) else sl_p
        if not is_buy and flt >= 2.50:
            cur_sl = entry - 0.20
            
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
        # Horizon close at bar 5 (75m)
        exit_p = c_skr[i + 5]
        pnl = ((exit_p - entry) if is_buy else (entry - exit_p)) - 0.20
        
    trades_skr.append(pnl)
    active_until = i + held

trades_skr = np.array(trades_skr)
n_skr = len(trades_skr)
win_skr = (trades_skr > 0.50).sum()
bep_skr = ((trades_skr >= -0.10) & (trades_skr <= 0.50)).sum()
loss_skr = (trades_skr < -0.10).sum()
wr_skr = (win_skr / max(1, win_skr + loss_skr)) * 100
gw_skr = trades_skr[trades_skr > 0].sum()
gl_skr = abs(trades_skr[trades_skr < 0].sum())
pf_skr = gw_skr / max(0.01, gl_skr)
net_skr = trades_skr.sum()
cum_skr = np.cumsum(trades_skr)
dd_skr = np.maximum.accumulate(np.insert(cum_skr, 0, 0)) - np.insert(cum_skr, 0, 0)
max_dd_skr = dd_skr.max()

total_days_skr = (times_skr[-1] - times_skr[0]).days
tpd_skr = n_skr / max(1, (total_days_skr * 5 / 7))
days_100_skr = 100 / max(0.1, tpd_skr)

# 2. EVALUASI MODEL PRO (77 FITUR - V5.4 ICT & TRIPLE-BARRIER SNIPER)
from Eksekusi_Otomatis_Trading_Bot_M15_PRO import extract_77_features, FEATURES_77
df_pro = extract_77_features(df_m, df_1, df_4, df_x).dropna()
model_pro = joblib.load(r"d:\SKRIPSI INFORMATIKA\model_m15_pro_77_features.pkl")
test_pro = df_pro.iloc[-test_bars:].copy()
probs_pro = model_pro.predict_proba(test_pro[FEATURES_77])

c_pro = test_pro['close'].values; h_pro = test_pro['high'].values; l_pro = test_pro['low'].values
shock_pro = test_pro['Shockwave_Extreme_Vol'].values
times_pro = test_pro.index

# Model PRO Full Adaptive Sniper (Conf >= 60% with sniper >= 65%)
trades_pro = []
active_until = -1
for i in range(len(c_pro) - 25):
    if i <= active_until: continue
    if shock_pro[i] == 1: continue # Shockwave Shield
    pb = probs_pro[i, 1]; ps = probs_pro[i, 0]
    conf = max(pb, ps)
    if conf < 0.60: continue
    
    is_buy = (pb >= ps)
    entry = c_pro[i]
    is_sniper = (conf >= 0.65)
    tp_val = 11.00 if is_sniper else 8.50
    sl_val = 6.50
    tp_p = entry + tp_val if is_buy else entry - tp_val
    sl_p = entry - sl_val if is_buy else entry + sl_val
    
    held = 25
    pnl = 0.0
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
    active_until = i + held

trades_pro = np.array(trades_pro)
n_pro = len(trades_pro)
win_pro = (trades_pro > 0.50).sum()
bep_pro = ((trades_pro >= -0.10) & (trades_pro <= 0.50)).sum()
loss_pro = (trades_pro < -0.10).sum()
wr_pro = (win_pro / max(1, win_pro + loss_pro)) * 100
gw_pro = trades_pro[trades_pro > 0].sum()
gl_pro = abs(trades_pro[trades_pro < 0].sum())
pf_pro = gw_pro / max(0.01, gl_pro)
net_pro = trades_pro.sum()
cum_pro = np.cumsum(trades_pro)
dd_pro = np.maximum.accumulate(np.insert(cum_pro, 0, 0)) - np.insert(cum_pro, 0, 0)
max_dd_pro = dd_pro.max()

total_days_pro = (times_pro[-1] - times_pro[0]).days
tpd_pro = n_pro / max(1, (total_days_pro * 5 / 7))
days_100_pro = 100 / max(0.1, tpd_pro)

# Hitung juga khusus Sniper-Only (>= 65% confidence)
trades_sniper = []
active_until = -1
for i in range(len(c_pro) - 25):
    if i <= active_until: continue
    if shock_pro[i] == 1: continue
    pb = probs_pro[i, 1]; ps = probs_pro[i, 0]
    conf = max(pb, ps)
    if conf < 0.65: continue # Pure Sniper >= 65%
    
    is_buy = (pb >= ps)
    entry = c_pro[i]
    tp_val = 11.00
    sl_val = 6.50
    tp_p = entry + tp_val if is_buy else entry - tp_val
    sl_p = entry - sl_val if is_buy else entry + sl_val
    
    held = 25
    pnl = 0.0
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
        
    trades_sniper.append(pnl)
    active_until = i + held

trades_sniper = np.array(trades_sniper)
n_snp = len(trades_sniper)
win_snp = (trades_sniper > 0.50).sum()
bep_snp = ((trades_sniper >= -0.10) & (trades_sniper <= 0.50)).sum()
loss_snp = (trades_sniper < -0.10).sum()
wr_snp = (win_snp / max(1, win_snp + loss_snp)) * 100
gw_snp = trades_sniper[trades_sniper > 0].sum()
gl_snp = abs(trades_sniper[trades_sniper < 0].sum())
pf_snp = gw_snp / max(0.01, gl_snp)
net_snp = trades_sniper.sum()

# Max consecutive losses
def get_max_loss_streak(t_arr):
    max_streak = 0
    cur_streak = 0
    for t in t_arr:
        if t < -0.10:
            cur_streak += 1
            if cur_streak > max_streak:
                max_streak = cur_streak
        elif t > 0.50:
            cur_streak = 0
    return max_streak

print("\n" + "="*80)
print("📊 HASIL KOMPARASI HEAD-TO-HEAD RESMI (DATA UJI REALISTIS LOT 0.01)")
print("="*80)
print(f"{'METRIK EVALUASI':<32} | {'BOT SKRIPSI (V5.2 65F)':<20} | {'BOT PRO (V5.4 77F SNIPER)':<24}")
print("-"*80)
print(f"{'Jumlah Fitur':<32} | {'65 Fitur (Kausal Murni)':<20} | {'77 Fitur (ICT + Shockwave)':<24}")
print(f"{'Profit Factor':<32} | {pf_skr:<20.2f} | {pf_snp:<24.2f} ⭐")
print(f"{'Win Rate Riil (Excl BEP)':<32} | {wr_skr:<19.1f}% | {wr_snp:<23.1f}%")
print(f"{'Net PnL (Modal $500 Lot 0.01)':<32} | +${net_skr:<18.2f} | +${net_snp:<22.2f}")
print(f"{'Return on Capital (RoC)':<32} | +{net_skr/500*100:<18.1f}% | +{net_snp/500*100:<22.1f}%")
print(f"{'Maksimum Drawdown (USD)':<32} | ${max_dd_skr:<19.2f} | ${max_dd_pro:<23.2f}")
print(f"{'Maksimum Drawdown (%)':<32} | {max_dd_skr/500*100:<19.1f}% | {max_dd_pro/500*100:<23.1f}%")
print(f"{'Frekuensi Trade per Hari':<32} | {tpd_skr:<19.2f} trade/hari | {n_snp/max(1,(total_days_pro*5/7)):<23.2f} trade/hari")
print(f"{'100 Trade Tercapai Dalam':<32} | {days_100_skr:<19.1f} hari kerja | {100/(n_snp/max(1,(total_days_pro*5/7))):<23.1f} hari kerja")
print(f"{'Estimasi Waktu Kalender 100 T':<32} | ~{days_100_skr/21:<18.1f} bulan | ~{(100/(n_snp/max(1,(total_days_pro*5/7))))/21:<22.1f} bulan")
print(f"{'Total Trade Sample OOS':<32} | {n_skr:<20} | {n_snp:<24}")
print(f"{'Komposisi Win / BEP / Loss':<32} | {win_skr}W / {bep_skr}B / {loss_skr}L      | {win_snp}W / {bep_snp}B / {loss_snp}L")
print(f"{'Skenario Terburuk (Max Loss 1T)':<32} | -${abs(trades_skr.min()):<18.2f} | -${abs(trades_sniper.min()):<22.2f}")
print(f"{'Runtun Loss Beruntun Terburuk':<32} | {get_max_loss_streak(trades_skr):<19} trade berturut | {get_max_loss_streak(trades_sniper):<23} trade berturut")
print(f"{'Rugi Maks Beruntun Akumulasi':<32} | -${get_max_loss_streak(trades_skr)*6.70:<18.2f} | -${get_max_loss_streak(trades_sniper)*6.70:<22.2f}")
print(f"{'Cuan Terkecil (Min Win)':<32} | +${trades_skr[trades_skr > 0].min():<18.2f} | +${trades_sniper[trades_sniper > 0].min():<22.2f}")
print(f"{'Cuan Terbesar (Max Win)':<32} | +${trades_skr.max():<18.2f} | +${trades_sniper.max():<22.2f}")
print(f"{'Rata-rata Cuan per Win':<32} | +${gw_skr/max(1, win_skr):<18.2f} | +${gw_snp/max(1, win_snp):<22.2f}")
print("="*80)
