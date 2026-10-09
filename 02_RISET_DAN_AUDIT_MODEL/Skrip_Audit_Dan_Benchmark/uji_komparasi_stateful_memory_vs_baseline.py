"""
=============================================================================
SIMULASI & BENCHMARK KOMPARATIF:
1. BASELINE: Model LightGBM M15 Murni (Stateless Snapshot 57 Fitur)
2. PROPOSED: Model LightGBM M15 + STATEFUL ZONE MEMORY ENGINE (SMC Planner)
=============================================================================
Tujuan: Menguji secara empiris apakah memberikan "Memori Zona & Planning" 
kepada sistem dapat meningkatkan Win Rate, Profit Factor, dan mencegah 
kebingungan model saat menghadapi fase Retest Support/Resistance.
=============================================================================
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib
import MetaTrader5 as mt5
from datetime import datetime

# Setup encoding
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
SYMBOL = "XAUUSD"

print("="*85)
print("🔬 SIMULASI AUDIT: STATELESS LIGHTGBM VS STATEFUL ZONE MEMORY ENGINE")
print("="*85)

if not mt5.initialize(path=MT5_PATH):
    if not mt5.initialize():
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)

if mt5.symbol_info(SYMBOL) is None:
    SYMBOL = "XAUUSDm"
mt5.symbol_select(SYMBOL, True)

print(f"📥 Mengambil 10.000 candle M15 dan 2.500 candle H1 dari MT5 ({SYMBOL})...")
rates_m15 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M15, 0, 10000)
rates_h1  = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1, 0, 2500)

if rates_m15 is None or len(rates_m15) == 0:
    print("❌ Data M15 kosong!")
    sys.exit(1)

df_m15 = pd.DataFrame(rates_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')
df_m15.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

print(f"✅ Data Terambil: M15={len(df_m15)} bars ({df_m15.index[0]} s/d {df_m15.index[-1]})")

# Load model canonical jika ada
MODEL_PATH = r"d:\SKRIPSI INFORMATIKA\model_m15_pro_57_features.pkl"
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"

model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
        print(f"✅ Model AI Loaded dari: {MODEL_PATH}")
    except Exception as e:
        print(f"⚠️ Gagal load model: {e}")

# =====================================================================
# 1. SIMULASI ENGINE MEMORI ZONA H1 (STATEFUL MEMORY BUFFER)
# =====================================================================
print("\n🧠 Membangun Stateful Zone Memory Engine (Melacak Unmitigated S/R H1)...")

class ZoneMemoryEngine:
    def __init__(self, zone_tolerance_points=1.5):
        self.supply_zones = [] # [{'high': h, 'low': l, 'time': t, 'tested': 0}]
        self.demand_zones = []
        self.tol = zone_tolerance_points

    def update_h1_candle(self, h1_time, h, l, c, o, is_swing_high, is_swing_low):
        # Jika swing high H1 terdeteksi, catat zona Supply
        if is_swing_high:
            self.supply_zones.append({
                'high': h,
                'low': min(h, max(o, c)),
                'created_at': h1_time,
                'tested_count': 0,
                'active': True
            })
            # Batasi memori hanya 10 zona aktif terakhir
            if len(self.supply_zones) > 10:
                self.supply_zones.pop(0)

        # Jika swing low H1 terdeteksi, catat zona Demand
        if is_swing_low:
            self.demand_zones.append({
                'high': max(l, min(o, c)),
                'low': l,
                'created_at': h1_time,
                'tested_count': 0,
                'active': True
            })
            if len(self.demand_zones) > 10:
                self.demand_zones.pop(0)

    def evaluate_price_in_zone(self, current_price, current_high, current_low):
        in_supply = False
        in_demand = False
        active_sup_idx = -1
        active_dem_idx = -1

        # Cek Supply Zones
        for idx, z in enumerate(reversed(self.supply_zones)):
            if not z['active']: continue
            # Harga menyentuh atau masuk zona
            if current_high >= (z['low'] - self.tol) and current_low <= (z['high'] + self.tol):
                in_supply = True
                active_sup_idx = len(self.supply_zones) - 1 - idx
                break

        # Cek Demand Zones
        for idx, z in enumerate(reversed(self.demand_zones)):
            if not z['active']: continue
            if current_low <= (z['high'] + self.tol) and current_high >= (z['low'] - self.tol):
                in_demand = True
                active_dem_idx = len(self.demand_zones) - 1 - idx
                break

        return in_supply, in_demand, active_sup_idx, active_dem_idx

# Deteksi Swing High/Low di H1
df_h1['Swing_High'] = (df_h1['high'] == df_h1['high'].rolling(7, center=True).max())
df_h1['Swing_Low']  = (df_h1['low'] == df_h1['low'].rolling(7, center=True).min())

# Hitung Fitur M15 Lengkap
print("⚙️ Mengekstrak Fitur M15 & Mensinkronisasikan State Zone Memory...")
sys.path.append(r"d:\SKRIPSI INFORMATIKA")
from Eksekusi_Otomatis_Trading_Bot import extract_57_features, FEATURES_57

rates_h4 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H4, 0, 1000)
df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

df_feat = extract_57_features(df_m15, df_h1, df_h4, None)

# Inisialisasi Memory Engine
engine = ZoneMemoryEngine(zone_tolerance_points=2.0)

# Sinkronkan state historis secara kronologis
h1_times = df_h1.index
h1_idx = 0
in_supply_series = []
in_demand_series = []
tested_count_series = []

for t, row in df_feat.iterrows():
    # Update engine jika ada candle H1 baru yang sudah closed
    while h1_idx < len(df_h1) and h1_times[h1_idx] <= t:
        h_row = df_h1.iloc[h1_idx]
        engine.update_h1_candle(
            h1_times[h1_idx], 
            h_row['high'], h_row['low'], h_row['close'], h_row['open'],
            h_row['Swing_High'], h_row['Swing_Low']
        )
        h1_idx += 1

    in_sup, in_dem, sup_idx, dem_idx = engine.evaluate_price_in_zone(row['close'], row['high'], row['low'])
    in_supply_series.append(1 if in_sup else 0)
    in_demand_series.append(1 if in_dem else 0)

df_feat['In_HTF_Supply'] = in_supply_series
df_feat['In_HTF_Demand'] = in_demand_series

# =====================================================================
# 2. RUNNING SIMULASI KOMPARASI
# =====================================================================
print("\n" + "="*85)
print("🚀 MENJALANKAN SIMULASI BACKTEST (10.000 CANDLE M15 TERAKHIR)")
print("="*85)

# Siapkan input model
X = df_feat[FEATURES_57].fillna(0)
probs = model.predict_proba(X) if model else np.zeros((len(df_feat), 2))

# Parameter Eksekusi Standar Skripsi
SL_POINTS = 6.50
TP_POINTS = 8.50
SPREAD_COST = 0.20 # $0.20 per trade (2 pips spread Exness)

def run_backtest(strategy_type="baseline"):
    trades = []
    in_trade = False
    trade_side = 0 # 1 Buy, -1 Sell
    entry_price = 0.0
    entry_bar = 0
    sl_price = 0.0
    tp_price = 0.0

    for i in range(100, len(df_feat) - 10):
        current_time = df_feat.index[i]
        c = df_feat['close'].iloc[i]
        h = df_feat['high'].iloc[i]
        l = df_feat['low'].iloc[i]
        p_buy = probs[i, 1] if model else 0.5
        p_sell = probs[i, 0] if model else 0.5
        in_sup = df_feat['In_HTF_Supply'].iloc[i]
        in_dem = df_feat['In_HTF_Demand'].iloc[i]
        upper_wick = df_feat['Upper_Wick_Ratio'].iloc[i]
        lower_wick = df_feat['Lower_Wick_Ratio'].iloc[i]

        # Manage open position
        if in_trade:
            pnl = 0.0
            closed = False
            reason = ""

            if trade_side == 1: # BUY
                if l <= sl_price:
                    pnl = -SL_POINTS - SPREAD_COST
                    closed = True
                    reason = "SL"
                elif h >= tp_price:
                    pnl = TP_POINTS - SPREAD_COST
                    closed = True
                    reason = "TP"
                elif (i - entry_bar) >= 5: # 75-min horizon close
                    pnl = (c - entry_price) - SPREAD_COST
                    closed = True
                    reason = "HORIZON"
            elif trade_side == -1: # SELL
                if h >= sl_price:
                    pnl = -SL_POINTS - SPREAD_COST
                    closed = True
                    reason = "SL"
                elif l <= tp_price:
                    pnl = TP_POINTS - SPREAD_COST
                    closed = True
                    reason = "TP"
                elif (i - entry_bar) >= 5:
                    pnl = (entry_price - c) - SPREAD_COST
                    closed = True
                    reason = "HORIZON"

            if closed:
                trades.append({
                    'entry_time': df_feat.index[entry_bar],
                    'exit_time': current_time,
                    'side': 'BUY' if trade_side == 1 else 'SELL',
                    'pnl': pnl,
                    'reason': reason
                })
                in_trade = False
            continue

        # Signal Logic
        if strategy_type == "baseline":
            # Baseline: Hanya mengandalkan probabilitas LightGBM >= 60% (Stateless)
            if p_buy >= 0.60:
                in_trade = True
                trade_side = 1
                entry_price = c
                entry_bar = i
                sl_price = entry_price - SL_POINTS
                tp_price = entry_price + TP_POINTS
            elif p_sell >= 0.60:
                in_trade = True
                trade_side = -1
                entry_price = c
                entry_bar = i
                sl_price = entry_price + SL_POINTS
                tp_price = entry_price - TP_POINTS

        elif strategy_type == "stateful_planner":
            # Hard Gate: Hanya trade jika di zona
            if in_sup == 1 and upper_wick > 0.25 and p_sell >= 0.55:
                in_trade = True
                trade_side = -1
                entry_price = c
                entry_bar = i
                sl_price = entry_price + SL_POINTS
                tp_price = entry_price - TP_POINTS
            elif in_dem == 1 and lower_wick > 0.25 and p_buy >= 0.55:
                in_trade = True
                trade_side = 1
                entry_price = c
                entry_bar = i
                sl_price = entry_price - SL_POINTS
                tp_price = entry_price + TP_POINTS

        elif strategy_type == "hybrid_confluence":
            # Soft Confluence: AI Tetap Driver Utama, tapi diberi Bobot Tambahan jika di Zona
            # Jika di Zona Supply, probabilitas sell dapat boost +5%, jika di Demand di diskon -5%
            adj_p_buy = p_buy + (0.05 if in_dem == 1 else 0.0) - (0.05 if in_sup == 1 else 0.0)
            adj_p_sell = p_sell + (0.05 if in_sup == 1 else 0.0) - (0.05 if in_dem == 1 else 0.0)

            if adj_p_buy >= 0.60:
                in_trade = True
                trade_side = 1
                entry_price = c
                entry_bar = i
                sl_price = entry_price - SL_POINTS
                tp_price = entry_price + TP_POINTS
            elif adj_p_sell >= 0.60:
                in_trade = True
                trade_side = -1
                entry_price = c
                entry_bar = i
                sl_price = entry_price + SL_POINTS
                tp_price = entry_price - TP_POINTS

    return pd.DataFrame(trades)

print("⏳ Menghitung performa Baseline...")
res_base = run_backtest("baseline")

print("⏳ Menghitung performa Proposed Hard Filter (Zone Memory)...")
res_prop = run_backtest("stateful_planner")

print("⏳ Menghitung performa Proposed Hybrid Confluence (Soft Boost Memory)...")
res_hyb = run_backtest("hybrid_confluence")

def print_metrics(name, df_res):
    if len(df_res) == 0:
        print(f"❌ {name}: Tidak ada trade yang dieksekusi!")
        return
    win_trades = df_res[df_res['pnl'] > 0]
    loss_trades = df_res[df_res['pnl'] <= 0]
    win_rate = len(win_trades) / len(df_res) * 100
    total_profit = win_trades['pnl'].sum()
    total_loss = abs(loss_trades['pnl'].sum()) if len(loss_trades) > 0 else 1e-6
    profit_factor = total_profit / total_loss if total_loss > 0 else 999.0
    net_pnl = df_res['pnl'].sum()

    print(f"\n📊 HASIL PERFORMA: {name}")
    print(f"   • Total Trades  : {len(df_res)} trade")
    print(f"   • Win Rate      : {win_rate:.2f}% ({len(win_trades)} Win / {len(loss_trades)} Loss)")
    print(f"   • Net Profit    : ${net_pnl:.2f} (Basis Lot 0.01 = ${net_pnl*10:.2f})")
    print(f"   • Profit Factor : {profit_factor:.2f}")
    print(f"   • Win/Loss Ratio: {len(win_trades)}:{len(loss_trades)}")

print_metrics("1. BASELINE (STATELESS M15 SNAPSHOT 57 FITUR)", res_base)
print_metrics("2. PROPOSED A (HARD FILTER ZONE MEMORY)", res_prop)
print_metrics("3. PROPOSED B (HYBRID CONFLUENCE BOOST ZONE MEMORY)", res_hyb)


mt5.shutdown()
