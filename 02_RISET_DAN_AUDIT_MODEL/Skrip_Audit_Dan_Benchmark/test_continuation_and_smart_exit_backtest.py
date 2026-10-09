import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

if not mt5.initialize():
    print("❌ MT5 Failed to initialize")
    sys.exit(1)

print("📥 Mengambil data historis XAUUSD M15, M5, H1, H4 dari MT5...")
# Ambil 3000 candle M15 (~1 bulan trading aktif, mencakup masa drop September 2026)
rates_m15 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 3000)
rates_m5  = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M5, 0, 9000)
rates_h1  = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 1500)
rates_h4  = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H4, 0, 800)
mt5.shutdown()

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
df_m5.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

print(f"✅ Data M15: {len(df)} candles ({df.index[0]} s/d {df.index[-1]})")

# Load model LightGBM
model = joblib.load('model_lightgbm_xauusd.pkl')
feature_cols = model.feature_name_

# 1. Hitung Fitur Dasar Model & Indikator
range_m15 = (df['high'] - df['low']) + 1e-6
df['Body_Ratio'] = (df['close'] - df['open']).abs() / range_m15
df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_m15
df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_m15
df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)
df['Swing_Low'] = df['low'].shift(1).rolling(20).min()
df['Swing_High'] = df['high'].shift(1).rolling(20).max()
df['Dist_Support'] = (df['close'] - df['Swing_Low']) / df['close']
df['Dist_Resistance'] = (df['Swing_High'] - df['close']) / df['close']
df['BOS_Bull'] = (df['close'] > df['Swing_High']).astype(int)
df['BOS_Bear'] = (df['close'] < df['Swing_Low']).astype(int)
trend_slow = df['close'].pct_change(20)
df['CHoCH_Bull'] = ((df['close'] > df['Swing_High']) & (trend_slow < 0)).astype(int)
df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low']) & (trend_slow > 0)).astype(int)
df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High']) & (df['close'] < df['Swing_High'])).astype(int)
df['Liquidity_Sweep_Low'] = ((df['low'] < df['Swing_Low']) & (df['close'] > df['Swing_Low'])).astype(int)

# H1 & H4 Trend
df_h1['EMA_50'] = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50'] > df_h1['EMA_200']).astype(int)
df['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(df.index, method='ffill').fillna(0)
df['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(df.index, method='ffill').fillna(0)
df['H1_Dist_EMA50'] = ((df_h1['close'] - df_h1['EMA_50']) / df_h1['close']).reindex(df.index, method='ffill').fillna(0)

df_h4['EMA_50'] = df_h4['close'].ewm(span=50, adjust=False).mean()
df_h4['EMA_200'] = df_h4['close'].ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull'] = (df_h4['close'] > df_h4['EMA_50']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50'] > df_h4['EMA_200']).astype(int)
df['Trend_H4_Bull'] = df_h4['Trend_H4_Bull'].reindex(df.index, method='ffill').fillna(0)
df['Trend_H4_Strong'] = df_h4['Trend_H4_Strong'].reindex(df.index, method='ffill').fillna(0)
df['H4_Dist_EMA50'] = ((df_h4['close'] - df_h4['EMA_50']) / df_h4['close']).reindex(df.index, method='ffill').fillna(0)

df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()

df['tr'] = np.maximum(df['high'] - df['low'],
                      np.maximum((df['high'] - df['close'].shift(1)).abs(),
                                 (df['low'] - df['close'].shift(1)).abs()))
df['atr'] = df['tr'].rolling(14).mean()

# RSI & Stochastic RSI
delta = df['close'].diff()
gain = delta.where(delta > 0, 0.0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
rs = gain / (loss + 1e-9)
df['rsi'] = 100.0 - (100.0 / (1.0 + rs))
rsi_min = df['rsi'].rolling(14).min()
rsi_max = df['rsi'].rolling(14).max()
stoch_rsi = (df['rsi'] - rsi_min) / ((rsi_max - rsi_min) + 1e-9) * 100.0
df['stoch_k'] = stoch_rsi.rolling(3).mean()

# Predict Model Probabilities
for col in feature_cols:
    if col not in df.columns: df[col] = 0.0

X = df[feature_cols].fillna(0)
probs = model.predict_proba(X)
df['prob_down'] = probs[:, 0] * 100
df['prob_up'] = probs[:, 1] * 100

# Deteksi RSI Divergence
bull_div_list = [False] * len(df)
bear_div_list = [False] * len(df)
for i in range(25, len(df)):
    sub = df.iloc[:i+1]
    curr_low = float(sub['low'].iloc[-1])
    curr_high = float(sub['high'].iloc[-1])
    cur_rsi = float(sub['rsi'].iloc[-1])
    prev_lows = sub['low'].iloc[-20:-3]
    prev_highs = sub['high'].iloc[-20:-3]
    if len(prev_lows) > 0 and len(prev_highs) > 0:
        min_prev_low = float(prev_lows.min())
        rsi_at_prev_low = float(sub.loc[prev_lows.idxmin(), 'rsi'])
        max_prev_high = float(prev_highs.max())
        rsi_at_prev_high = float(sub.loc[prev_highs.idxmax(), 'rsi'])
        if (curr_low <= min_prev_low + 1.0) and (cur_rsi >= rsi_at_prev_low + 3.0) and (cur_rsi <= 48.0):
            bull_div_list[i] = True
        elif (curr_high >= max_prev_high - 1.0) and (cur_rsi <= rsi_at_prev_high - 3.0) and (cur_rsi >= 52.0):
            bear_div_list[i] = True
df['bull_div'] = bull_div_list
df['bear_div'] = bear_div_list

LOT = 0.01

def run_simulation(mode="BASELINE"):
    """
    mode:
      - 'BASELINE': As-Is system (Zone A/B bounce only, high TP 150p, single BEP at +$4, SELL blocked when oversold/collision).
      - 'ENHANCED': v4.2 (Trend Continuation SELL allowed, Hybrid Smart-Exit: TP $5.00, Dynamic Trailing, 75m auto-close).
    """
    trades = []
    active_until_time = None
    
    for i in range(50, len(df) - 30):
        c_time = df.index[i]
        if active_until_time is not None and c_time < active_until_time:
            continue
            
        c = df.iloc[i]
        atr = c['atr']
        if pd.isna(atr) or atr < 1.0: continue
        
        prob_up = c['prob_up']
        prob_down = c['prob_down']
        dist_res = c['Dist_Resistance']
        dist_sup = c['Dist_Support']
        lower_w = c['Lower_Wick_Ratio']
        upper_w = c['Upper_Wick_Ratio']
        is_bull_c = c['close'] > c['open']
        is_bear_c = c['close'] < c['open']
        stoch_k = c['stoch_k']
        bull_div = c['bull_div']
        bear_div = c['bear_div']
        h1_bull = c['Trend_H1_Bull'] == 1
        h4_bull = c['Trend_H4_Bull'] == 1
        close_p = c['close']
        
        sig = None
        zone = None
        
        if mode == "BASELINE":
            # 1. BASELINE ENTRY: Hanya Zona A/B Reversal
            # BUY: dekat support
            if dist_sup <= 0.0035 and (stoch_k <= 25 or bull_div or lower_w >= 0.20):
                if prob_up >= 50.0 and (is_bull_c or lower_w >= 0.25):
                    sig = 'BUY'; zone = 'A_B_BOUNCE'
            # SELL: dekat resistensi (dan TIDAK oversold, TIDAK dekat support)
            elif dist_res <= 0.0035 and stoch_k > 25 and not bull_div and dist_sup > 0.0018:
                if prob_down >= 50.0 and (is_bear_c or upper_w >= 0.20):
                    sig = 'SELL'; zone = 'A_B_BOUNCE'
                    
        elif mode == "ENHANCED":
            # 2. ENHANCED ENTRY: Zona A/B Reversal + TREND CONTINUATION ENGINE
            # A. Standar Reversal Setup
            if dist_sup <= 0.0035 and (stoch_k <= 25 or bull_div or lower_w >= 0.20):
                if prob_up >= 50.0 and (is_bull_c or lower_w >= 0.25):
                    sig = 'BUY'; zone = 'A_B_BOUNCE'
            elif dist_res <= 0.0035 and (stoch_k >= 75 or bear_div or upper_w >= 0.20):
                if prob_down >= 50.0 and (is_bear_c or upper_w >= 0.25):
                    sig = 'SELL'; zone = 'A_B_BOUNCE'
                    
            # B. TREND CONTINUATION ENGINE (Peluang SELL saat Tren Turun Kuat):
            if sig is None:
                # Kondisi Makro Bearish: H1 & H4 Bearish atau harga di bawah EMA 20 & 50
                is_macro_bear = (not h1_bull) or (not h4_bull)
                is_ema_bear = (close_p < c['EMA_20']) and (c['EMA_20'] < c['EMA_50'])
                
                if is_macro_bear and is_ema_bear and not bull_div:
                    # Pullback/retest kecil ke EMA 20 atau FVG bear lalu ditolak
                    is_pullback_rejection = (c['high'] >= c['EMA_20'] - 0.50) and (is_bear_c or upper_w >= 0.20)
                    is_breakdown = c['BOS_Bear'] == 1 and is_bear_c
                    
                    if (is_pullback_rejection or is_breakdown) and prob_down >= 50.0:
                        sig = 'SELL'; zone = 'TREND_CONTINUATION'
                        
                # Kondisi Makro Bullish (Trend Continuation BUY saat Bullish kuat):
                is_macro_bull = h1_bull and h4_bull
                is_ema_bull = (close_p > c['EMA_20']) and (c['EMA_20'] > c['EMA_50'])
                if is_macro_bull and is_ema_bull and not bear_div:
                    is_pullback_bounce = (c['low'] <= c['EMA_20'] + 0.50) and (is_bull_c or lower_w >= 0.20)
                    is_breakout = c['BOS_Bull'] == 1 and is_bull_c
                    if (is_pullback_bounce or is_breakout) and prob_up >= 50.0:
                        sig = 'BUY'; zone = 'TREND_CONTINUATION'

        if sig is None:
            continue
            
        entry_p = close_p
        base_sl_dist = max(6.5, min(8.5, atr * 1.20))
        sl_p = entry_p - base_sl_dist if sig == 'BUY' else entry_p + base_sl_dist
        
        if mode == "BASELINE":
            tp_dist = base_sl_dist * 2.2 # ~150-180 pips
            tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        else: # ENHANCED
            tp_dist = 5.0 # Realistic TP 50 pips ($5.00 USD)
            tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
            
        # Simulasi Bar-by-Bar ke depan (maksimal 40 candle M15 = 10 jam)
        fut_m15 = df.iloc[i+1 : min(len(df), i+41)]
        cur_sl = sl_p
        peak_profit = 0.0
        pnl = None
        exit_reason = None
        
        for k in range(len(fut_m15)):
            bar = fut_m15.iloc[k]
            candle_num = k + 1
            age_min = candle_num * 15
            
            # Profit bar ini
            if sig == 'BUY':
                high_prof = (bar['high'] - entry_p) * 100 * LOT
                low_prof  = (bar['low'] - entry_p) * 100 * LOT
                close_prof = (bar['close'] - entry_p) * 100 * LOT
            else:
                high_prof = (entry_p - bar['low']) * 100 * LOT
                low_prof  = (entry_p - bar['high']) * 100 * LOT
                close_prof = (entry_p - bar['close']) * 100 * LOT
                
            if high_prof > peak_profit: peak_profit = high_prof
            
            if mode == "BASELINE":
                # Single BEP at +$4.00 -> Lock +$0.20
                if peak_profit >= 4.0:
                    bep_val = entry_p + 0.20 if sig == 'BUY' else entry_p - 0.20
                    if sig == 'BUY' and bep_val > cur_sl: cur_sl = bep_val
                    elif sig == 'SELL' and bep_val < cur_sl: cur_sl = bep_val
                    
                # Cek SL / TP
                if sig == 'BUY':
                    if bar['low'] <= cur_sl:
                        pnl = (cur_sl - entry_p) * 100 * LOT
                        exit_reason = 'BEP' if abs(pnl - 0.20) < 0.1 else 'SL'
                        active_until_time = bar.name; break
                    elif bar['high'] >= tp_p:
                        pnl = tp_dist * 100 * LOT
                        exit_reason = 'TP'
                        active_until_time = bar.name; break
                else:
                    if bar['high'] >= cur_sl:
                        pnl = (entry_p - cur_sl) * 100 * LOT
                        exit_reason = 'BEP' if abs(pnl - 0.20) < 0.1 else 'SL'
                        active_until_time = bar.name; break
                    elif bar['low'] <= tp_p:
                        pnl = tp_dist * 100 * LOT
                        exit_reason = 'TP'
                        active_until_time = bar.name; break
                        
            elif mode == "ENHANCED":
                # 1. Realistic TP $5.00
                if high_prof >= 5.0:
                    pnl = 5.0
                    exit_reason = 'TP_REALISTIC'
                    active_until_time = bar.name; break
                    
                # 2. Dynamic Trailing Multi-Tier
                # Tier 1: Peak >= $2.50 -> Lock +$0.20
                if peak_profit >= 2.50 and peak_profit < 4.50:
                    t1_sl = entry_p + 0.20 if sig == 'BUY' else entry_p - 0.20
                    if sig == 'BUY' and t1_sl > cur_sl: cur_sl = t1_sl
                    elif sig == 'SELL' and t1_sl < cur_sl: cur_sl = t1_sl
                # Tier 2: Peak >= $4.50 -> Lock +$2.00
                elif peak_profit >= 4.50:
                    t2_sl = entry_p + 2.00 if sig == 'BUY' else entry_p - 2.00
                    if sig == 'BUY' and t2_sl > cur_sl: cur_sl = t2_sl
                    elif sig == 'SELL' and t2_sl < cur_sl: cur_sl = t2_sl
                    
                # 3. Horizon 75-Menit Auto-Close (Candle 5 M15 sesuai Skripsi):
                if candle_num >= 5 and close_prof > 0.50:
                    pnl = close_prof
                    exit_reason = '75M_AUTO_CLOSE'
                    active_until_time = bar.name; break
                    
                # Cek SL / Trailing Hit
                if sig == 'BUY' and bar['low'] <= cur_sl:
                    pnl = (cur_sl - entry_p) * 100 * LOT
                    exit_reason = 'BEP' if abs(pnl - 0.20) < 0.1 else ('TRAIL_LOCK' if pnl > 0.5 else 'SL')
                    active_until_time = bar.name; break
                elif sig == 'SELL' and bar['high'] >= cur_sl:
                    pnl = (entry_p - cur_sl) * 100 * LOT
                    exit_reason = 'BEP' if abs(pnl - 0.20) < 0.1 else ('TRAIL_LOCK' if pnl > 0.5 else 'SL')
                    active_until_time = bar.name; break
                    
        if pnl is None:
            last_bar = fut_m15.iloc[-1]
            diff = (last_bar['close'] - entry_p) if sig == 'BUY' else (entry_p - last_bar['close'])
            pnl = diff * 100 * LOT
            exit_reason = 'TIMEOUT'
            active_until_time = last_bar.name
            
        trades.append({
            'time': c_time,
            'sig': sig,
            'zone': zone,
            'entry': entry_p,
            'pnl': pnl,
            'exit_reason': exit_reason
        })
        
    df_res = pd.DataFrame(trades)
    return df_res

print("\n" + "="*85)
print("🚀 MENJALANKAN BACKTEST SIMULASI KOMPARATIF (1 BULAN HISTORIS M15)")
print("="*85)

df_base = run_simulation("BASELINE")
df_enh  = run_simulation("ENHANCED")

def print_stats(name, d):
    tot = len(d)
    if tot == 0:
        print(f"❌ {name}: Tidak ada trade")
        return
    buys = len(d[d['sig'] == 'BUY'])
    sells = len(d[d['sig'] == 'SELL'])
    wins = len(d[d['pnl'] > 0])
    losses = len(d[d['pnl'] < 0])
    beps = len(d[abs(d['pnl'] - 0.20) < 0.1])
    wr = wins / tot * 100
    net_pnl = d['pnl'].sum()
    gross_p = d[d['pnl'] > 0]['pnl'].sum()
    gross_l = abs(d[d['pnl'] < 0]['pnl'].sum())
    pf = (gross_p / gross_l) if gross_l > 0 else 999.0
    
    d['cum'] = d['pnl'].cumsum()
    d['peak'] = d['cum'].cummax()
    d['dd'] = d['peak'] - d['cum']
    max_dd = d['dd'].max()
    
    print(f"\n📊 --- {name} ---")
    print(f"  • Total Trade     : {tot} Trade (BUY: {buys} | SELL: {sells})")
    print(f"  • Rasio Buy:Sell  : {buys/tot*100:.1f}% BUY vs {sells/tot*100:.1f}% SELL")
    print(f"  • Win Rate        : {wr:.1f}% ({wins} Win / {losses} Loss)")
    print(f"  • Trade BEP (+0.2): {beps} Trade")
    print(f"  • Total Net PnL   : ${net_pnl:+.2f} USD")
    print(f"  • Profit Factor   : {pf:.2f}")
    print(f"  • Max Drawdown    : ${max_dd:.2f} USD")
    
    # Detail Exit Reason
    reasons = d['exit_reason'].value_counts()
    print("  • Breakdown Exit  :")
    for r_name, r_cnt in reasons.items():
        print(f"      - {r_name:<16}: {r_cnt} trade ({r_cnt/tot*100:.1f}%)")

print_stats("1. SISTEM BASELINE (AKTUAL SAAT INI)", df_base)
print_stats("2. SISTEM ENHANCED v4.2 (TREND CONTINUATION + HYBRID SMART-EXIT)", df_enh)

print("\n" + "="*85)
print("💡 PERBANDINGAN DELTA HEAD-TO-HEAD:")
print("="*85)
pnl_diff = df_enh['pnl'].sum() - df_base['pnl'].sum()
wr_diff  = (len(df_enh[df_enh['pnl'] > 0])/len(df_enh)*100) - (len(df_base[df_base['pnl'] > 0])/len(df_base)*100)
print(f"  • Peningkatan Net Profit : ${pnl_diff:+.2f} USD")
print(f"  • Peningkatan Win Rate   : {wr_diff:+.1f}%")
print(f"  • Rasio Eksekusi SELL    : Dari {len(df_base[df_base['sig']=='SELL'])} trade menjadi {len(df_enh[df_enh['sig']=='SELL'])} trade!")
print("="*85)
