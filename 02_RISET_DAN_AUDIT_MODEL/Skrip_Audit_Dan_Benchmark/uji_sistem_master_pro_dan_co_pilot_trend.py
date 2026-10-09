"""
====================================================================================================
SIMULASI SISTEM TUNGGAL MUTUAL EXCLUSIVE: MASTER PRO V5.4 + AUXILIARY TREND CO-PILOT
====================================================================================================
Arsitektur Sistem Terpadu (Ringkas, Zero Collision, On/Off State Machine):
1. Engine 1: Master PRO Sniper Reversal (V5.4 Full Proprietary)
   - Status: PRIORITAS UTAMA (KING)
   - Kondisi On: Kapan pun sinyal PRO >= 60.0% aktif.
   - Karakteristik: SL $5.00, TP $9.50 / $12.50, Wick Micro-Trigger (35%), Trailing 2-Tier, Max 25 Bar.
2. Engine 2: Auxiliary Trend Co-Pilot (65 Fitur Trend Runner)
   - Status: CADANGAN PENGISI WAKTU IDLE (ON HANYA JIKA PRO OFF)
   - Kondisi On: Hanya aktif jika PRO OFF (tidak ada posisi aktif & sinyal PRO diam) DAN ADX >= 25.
   - Karakteristik: Membeli di ayunan tren (Wick Dip), SL $5.50, TP $12.00, Trailing 2-Tier, Max 8 Bar.
====================================================================================================
"""

import os, sys, warnings, joblib
warnings.filterwarnings('ignore')
if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'): sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

from uji_komparasi_pro_v6_dual_engine_vs_portofolio_terpisah import df_test, prob_skripsi, prob_pro

closes = df_test['close'].values
highs  = df_test['high'].values
lows   = df_test['low'].values
opens  = df_test['open'].values
n = len(closes)
TOTAL_FRICTION = 0.35

print("="*95)
print("🏆 HASIL SIMULASI SISTEM TUNGGAL TERPADU: MASTER PRO + TREND CO-PILOT (ON/OFF STATE MACHINE)")
print("="*95)

results = []

for trend_conf_thresh in [60.0, 65.0, 68.0]:
    trades = []
    active_pos = None
    equity_curve = [500.0]
    balance = 500.0
    
    for i in range(n - 25):
        h_next = highs[i+1]; l_next = lows[i+1]; c_next = closes[i+1]; o_next = opens[i+1]
        
        # 1. Kelola posisi aktif
        if active_pos is not None:
            active_pos['bars_held'] += 1
            pos_type = active_pos['type']
            entry_p = active_pos['entry_price']
            sl_p = active_pos['sl']
            tp_p = active_pos['tp']
            cfg = active_pos['cfg']
            max_limit = active_pos['max_limit']
            
            cur_float = (h_next - entry_p) - TOTAL_FRICTION if pos_type == 'BUY' else (entry_p - l_next) - TOTAL_FRICTION
            if cur_float > active_pos['peak_float']:
                active_pos['peak_float'] = cur_float
            
            # Trailing Profit Locks
            if cfg == 'pro':
                if active_pos['peak_float'] >= 2.20:
                    bep_sl = entry_p + 0.30 if pos_type == 'BUY' else entry_p - 0.30
                    sl_p = max(sl_p, bep_sl) if pos_type == 'BUY' else min(sl_p, bep_sl)
                if active_pos['peak_float'] >= 5.50:
                    t2_sl = entry_p + 3.00 if pos_type == 'BUY' else entry_p - 3.00
                    sl_p = max(sl_p, t2_sl) if pos_type == 'BUY' else min(sl_p, t2_sl)
            else: # Trend Co-pilot
                if active_pos['peak_float'] >= 2.50:
                    bep_sl = entry_p + 0.50 if pos_type == 'BUY' else entry_p - 0.50
                    sl_p = max(sl_p, bep_sl) if pos_type == 'BUY' else min(sl_p, bep_sl)
                if active_pos['peak_float'] >= 5.00:
                    t2_sl = entry_p + 3.00 if pos_type == 'BUY' else entry_p - 3.00
                    sl_p = max(sl_p, t2_sl) if pos_type == 'BUY' else min(sl_p, t2_sl)
            active_pos['sl'] = sl_p
            
            closed = False; pnl = 0.0
            if pos_type == 'BUY':
                if h_next >= tp_p:
                    closed = True; pnl = tp_p - entry_p - TOTAL_FRICTION
                elif l_next <= sl_p:
                    closed = True; pnl = sl_p - entry_p - TOTAL_FRICTION
            else:
                if l_next <= tp_p:
                    closed = True; pnl = entry_p - tp_p - TOTAL_FRICTION
                elif h_next >= sl_p:
                    closed = True; pnl = entry_p - sl_p - TOTAL_FRICTION
            
            if not closed and active_pos['bars_held'] >= max_limit:
                closed = True
                diff = (c_next - entry_p) if pos_type == 'BUY' else (entry_p - c_next)
                pnl = diff - TOTAL_FRICTION
            
            if closed:
                balance += pnl
                equity_curve.append(balance)
                trades.append({'cfg': cfg, 'pnl': float(pnl), 'win': pnl > 0.25})
                active_pos = None
                continue
                
        # 2. Logika On/Off State Machine Seleksi Entry
        if active_pos is None:
            # Periksa Master Engine (PRO) terlebih dahulu
            p_up_pr = prob_pro[i, 1] * 100.0; p_dn_pr = prob_pro[i, 0] * 100.0
            pro_act = None; pro_conf = 0.0
            if p_up_pr >= 60.0 and p_up_pr > p_dn_pr: pro_act = 'BUY'; pro_conf = p_up_pr
            elif p_dn_pr >= 60.0 and p_dn_pr > p_up_pr: pro_act = 'SELL'; pro_conf = p_dn_pr
            
            if pro_act is not None:
                # PRO ON (MASTER MODE BEROPERASI)
                if pro_act == 'SELL': bonus = (highs[i] - closes[i]) * 0.35; entry_p = closes[i] + bonus
                else: bonus = (closes[i] - lows[i]) * 0.35; entry_p = closes[i] - bonus
                sl_dist = 5.00; tp_dist = 12.50 if pro_conf >= 65.0 else 9.50
                tp_p = entry_p + tp_dist if pro_act == 'BUY' else entry_p - tp_dist
                sl_p = entry_p - sl_dist if pro_act == 'BUY' else entry_p + sl_dist
                active_pos = {
                    'type': pro_act, 'entry_price': entry_p, 'sl': sl_p, 'tp': tp_p,
                    'peak_float': 0.0, 'bars_held': 0, 'cfg': 'pro', 'max_limit': 25
                }
            else:
                # PRO OFF! (IDLE STATE -> AKTIFKAN AUXILIARY TREND CO-PILOT)
                p_up_sk = prob_skripsi[i, 1] * 100.0; p_dn_sk = prob_skripsi[i, 0] * 100.0
                adx_val = df_test['ADX_14'].iloc[i]
                
                # Hanya aktif jika ada tren nyata (ADX >= 25)
                if adx_val >= 25.0:
                    tr_act = None
                    if p_up_sk >= trend_conf_thresh and p_up_sk > p_dn_sk: tr_act = 'BUY'
                    elif p_dn_sk >= trend_conf_thresh and p_dn_sk > p_up_sk: tr_act = 'SELL'
                    
                    if tr_act is not None:
                        # Masuk saat ayunan sumbu ke arah tren
                        if tr_act == 'SELL': bonus = (highs[i] - closes[i]) * 0.35; entry_p = closes[i] + bonus
                        else: bonus = (closes[i] - lows[i]) * 0.35; entry_p = closes[i] - bonus
                        sl_dist = 5.50; tp_dist = 12.00
                        tp_p = entry_p + tp_dist if tr_act == 'BUY' else entry_p - tp_dist
                        sl_p = entry_p - sl_dist if tr_act == 'BUY' else entry_p + sl_dist
                        active_pos = {
                            'type': tr_act, 'entry_price': entry_p, 'sl': sl_p, 'tp': tp_p,
                            'peak_float': 0.0, 'bars_held': 0, 'cfg': 'trend', 'max_limit': 8
                        }
                        
    df_tr = pd.DataFrame(trades)
    tot = df_tr['pnl'].sum()
    pro_df = df_tr[df_tr['cfg'] == 'pro']
    trend_df = df_tr[df_tr['cfg'] == 'trend']
    
    wins = df_tr[df_tr['pnl'] > 0.25]
    losses = df_tr[df_tr['pnl'] < 0.0]
    wr = len(wins) / (len(wins) + len(losses)) * 100.0 if (len(wins) + len(losses)) > 0 else 0.0
    gw = wins['pnl'].sum(); gl = abs(losses['pnl'].sum())
    pf = gw / gl if gl > 0 else 99.0
    eq = pd.Series(equity_curve)
    peak = eq.cummax()
    mdd = (peak - eq).max()
    mdd_pct = ((peak - eq)/peak).max() * 100.0
    
    results.append({
        'Threshold': f'Trend Conf >= {trend_conf_thresh}%',
        'Net_Profit': round(tot, 2),
        'RoC': round(tot / 500.0 * 100.0, 1),
        'Total_Trades': len(df_tr),
        'PRO_Trades': len(pro_df),
        'PRO_PnL': round(pro_df['pnl'].sum(), 2),
        'Trend_Trades': len(trend_df),
        'Trend_PnL': round(trend_df['pnl'].sum(), 2),
        'Win_Rate': round(wr, 2),
        'Profit_Factor': round(pf, 2),
        'Max_Drawdown_USD': round(mdd, 2),
        'Max_Drawdown_Pct': round(mdd_pct, 2)
    })

df_res = pd.DataFrame(results)
print(df_res.to_string(index=False))

# Simpan ke CSV
out_path = os.path.join(r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI", "Hasil_Sistem_Tunggal_Master_PRO_Plus_Trend_CoPilot.csv")
df_res.to_csv(out_path, index=False)
print(f"\n💾 Disimpan ke: {out_path}")
