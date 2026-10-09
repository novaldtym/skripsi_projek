import os
import sys
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("Failed to initialize MT5")
    sys.exit(1)

import Eksekusi_Otomatis_Trading_Bot as bot

symbol = bot.get_symbol_name()

rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 1000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 200)

df_all_m15 = pd.DataFrame(rates_m15)
df_all_m15['time_wib'] = pd.to_datetime(df_all_m15['time'], unit='s') + timedelta(hours=7)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time_dt'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time_dt', inplace=True)
df_h1['EMA_50_H1'] = df_h1['close'].ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull'] = (df_h1['close'] > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time_dt'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time_dt', inplace=True)
df_h4['EMA_50_H4'] = df_h4['close'].ewm(span=50, adjust=False).mean()
df_h4['EMA_200_H4'] = df_h4['close'].ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull'] = (df_h4['close'] > df_h4['EMA_50_H4']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)

# Periode analisis: 03:23 s/d 14:15 WIB (2026-10-02)
mask_target = (df_all_m15['time_wib'] >= '2026-10-02 03:30:00') & (df_all_m15['time_wib'] <= '2026-10-02 14:15:00')
target_indices = df_all_m15[mask_target].index.tolist()

model = bot.model
features_list = [
    'Body_Ratio', 'Lower_Wick_Ratio', 'Upper_Wick_Ratio', 
    'FVG_Bull', 'FVG_Bear', 'Dist_Support', 'Dist_Resistance',
    'BOS_Bull', 'BOS_Bear', 'CHoCH_Bull', 'CHoCH_Bear',
    'Liquidity_Sweep_High', 'Liquidity_Sweep_Low', 
    'Order_Block_Bull', 'Order_Block_Bear',
    'Fibo_Pos_100', 'Fibo_Dist_382', 'Fibo_Dist_500', 'Fibo_Dist_618',
    'RSI_14', 'BB_Bandwidth', 'BB_Pos',
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3', 'DXY_Trend', 'XAU_DXY_Ratio_Return',
    'Is_NFP_Week', 'Is_CPI_Day', 'Is_FOMC_Week',
    'Trend_H1_Bull', 'Trend_H1_Strong',
    'Trend_H4_Bull', 'Trend_H4_Strong',
    'H1_Dist_EMA50', 'H4_Dist_EMA50',
    'Consecutive_Bull', 'Consecutive_Bear',
    'ADX_14', 'Volume_Ratio',
    'XAU_Return_10', 'XAU_Return_20'
]

results = []
signals = []
standby_reasons = {}

for idx in target_indices:
    candle_time = df_all_m15.loc[idx, 'time_wib']
    
    sub_m15 = df_all_m15.loc[:idx].copy()
    sub_m15['time_dt'] = pd.to_datetime(sub_m15['time'], unit='s')
    sub_m15.set_index('time_dt', inplace=True)
    
    range_m15 = (sub_m15['high'] - sub_m15['low']) + 1e-6
    sub_m15['Body_Ratio'] = (sub_m15['close'] - sub_m15['open']).abs() / range_m15
    sub_m15['Lower_Wick_Ratio'] = (sub_m15[['open', 'close']].min(axis=1) - sub_m15['low']) / range_m15
    sub_m15['Upper_Wick_Ratio'] = (sub_m15['high'] - sub_m15[['open', 'close']].max(axis=1)) / range_m15
    sub_m15['Body_M15'] = sub_m15['Body_Ratio']
    sub_m15['Lower_Wick_M15'] = sub_m15['Lower_Wick_Ratio']
    sub_m15['Upper_Wick_M15'] = sub_m15['Upper_Wick_Ratio']
    
    sub_m15['FVG_Bull'] = (sub_m15['low'] > sub_m15['high'].shift(2)).astype(int)
    sub_m15['FVG_Bear'] = (sub_m15['high'] < sub_m15['low'].shift(2)).astype(int)
    sub_m15['Swing_High_20'] = sub_m15['high'].shift(1).rolling(20).max()
    sub_m15['Swing_Low_20'] = sub_m15['low'].shift(1).rolling(20).min()
    sub_m15['Dist_Support'] = (sub_m15['close'] - sub_m15['Swing_Low_20']) / sub_m15['close']
    sub_m15['Dist_Resistance'] = (sub_m15['Swing_High_20'] - sub_m15['close']) / sub_m15['close']
    sub_m15['BOS_Bull'] = (sub_m15['close'] > sub_m15['Swing_High_20']).astype(int)
    sub_m15['BOS_Bear'] = (sub_m15['close'] < sub_m15['Swing_Low_20']).astype(int)
    
    trend_slow = sub_m15['close'].pct_change(20)
    sub_m15['CHoCH_Bull'] = ((sub_m15['close'] > sub_m15['Swing_High_20']) & (trend_slow < 0)).astype(int)
    sub_m15['CHoCH_Bear'] = ((sub_m15['close'] < sub_m15['Swing_Low_20']) & (trend_slow > 0)).astype(int)
    sub_m15['Liquidity_Sweep_High'] = ((sub_m15['high'] > sub_m15['Swing_High_20']) & (sub_m15['close'] < sub_m15['Swing_High_20'])).astype(int)
    sub_m15['Liquidity_Sweep_Low'] = ((sub_m15['low'] < sub_m15['Swing_Low_20']) & (sub_m15['close'] > sub_m15['Swing_Low_20'])).astype(int)
    
    is_bear = sub_m15['close'] < sub_m15['open']
    is_bull = sub_m15['close'] > sub_m15['open']
    impulse_up = (sub_m15['close'].shift(-2) - sub_m15['close']) > (1.5 * (sub_m15['high'] - sub_m15['low']))
    impulse_dn = (sub_m15['close'] - sub_m15['close'].shift(-2)) > (1.5 * (sub_m15['high'] - sub_m15['low']))
    sub_m15['Order_Block_Bull'] = (is_bear & impulse_up).astype(int)
    sub_m15['Order_Block_Bear'] = (is_bull & impulse_dn).astype(int)
    
    lookback_fibo = 100
    roll_high = sub_m15['high'].rolling(lookback_fibo).max()
    roll_low = sub_m15['low'].rolling(lookback_fibo).min()
    roll_range = (roll_high - roll_low) + 1e-6
    sub_m15['Fibo_Pos_100'] = (sub_m15['close'] - roll_low) / roll_range
    sub_m15['Fibo_Dist_382'] = (sub_m15['close'] - (roll_high - roll_range * 0.382)) / sub_m15['close']
    sub_m15['Fibo_Dist_500'] = (sub_m15['close'] - (roll_high - roll_range * 0.500)) / sub_m15['close']
    sub_m15['Fibo_Dist_618'] = (sub_m15['close'] - (roll_high - roll_range * 0.618)) / sub_m15['close']
    
    delta15 = sub_m15['close'].diff()
    gain15 = (delta15.where(delta15 > 0, 0)).rolling(14).mean()
    loss15 = (-delta15.where(delta15 < 0, 0)).rolling(14).mean()
    sub_m15['RSI_14'] = 100 - (100 / (1 + (gain15 / (loss15 + 1e-6))))
    sub_m15['SMA_20'] = sub_m15['close'].rolling(20).mean()
    sub_m15['STD_20'] = sub_m15['close'].rolling(20).std()
    sub_m15['BB_Bandwidth'] = (4 * sub_m15['STD_20']) / sub_m15['SMA_20']
    sub_m15['BB_Pos'] = (sub_m15['close'] - (sub_m15['SMA_20'] - 2*sub_m15['STD_20'])) / (4*sub_m15['STD_20'] + 1e-6)
    
    sub_m15['XAU_Return_1'] = sub_m15['close'].pct_change(1)
    sub_m15['XAU_Return_3'] = sub_m15['close'].pct_change(3)
    sub_m15['XAU_Return_5'] = sub_m15['close'].pct_change(5)
    sub_m15['XAU_Return_10'] = sub_m15['close'].pct_change(10)
    sub_m15['XAU_Return_20'] = sub_m15['close'].pct_change(20)
    
    # Intermarket DXY MT5
    rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 500)
    if rates_dxy is not None and len(rates_dxy) > 0:
        df_dxy = pd.DataFrame(rates_dxy)
        df_dxy['time_dt'] = pd.to_datetime(df_dxy['time'], unit='s')
        df_dxy.set_index('time_dt', inplace=True)
        sub_m15['DXY_Close'] = df_dxy['close'].reindex(sub_m15.index, method='ffill').bfill()
    else:
        sub_m15['DXY_Close'] = 102.5
        
    sub_m15['DXY_Return_1'] = sub_m15['DXY_Close'].pct_change(1).fillna(0)
    sub_m15['DXY_Return_3'] = sub_m15['DXY_Close'].pct_change(3).fillna(0)
    sub_m15['DXY_Trend'] = (sub_m15['DXY_Close'] > sub_m15['DXY_Close'].rolling(20).mean()).astype(int)
    sub_m15['XAU_DXY_Ratio_Return'] = (sub_m15['close'] / sub_m15['DXY_Close']).pct_change(1).fillna(0)
    
    dates = sub_m15.index
    sub_m15['Is_NFP_Week'] = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
    sub_m15['Is_CPI_Day'] = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    sub_m15['Is_FOMC_Week'] = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)
    
    # Reindex real H1 and H4 trends
    sub_m15['Trend_H1_Bull'] = df_h1['Trend_H1_Bull'].reindex(sub_m15.index, method='ffill').fillna(0)
    sub_m15['Trend_H1_Strong'] = df_h1['Trend_H1_Strong'].reindex(sub_m15.index, method='ffill').fillna(0)
    sub_m15['Trend_H4_Bull'] = df_h4['Trend_H4_Bull'].reindex(sub_m15.index, method='ffill').fillna(0)
    sub_m15['Trend_H4_Strong'] = df_h4['Trend_H4_Strong'].reindex(sub_m15.index, method='ffill').fillna(0)
    
    h1_ema50 = df_h1['EMA_50_H1'].reindex(sub_m15.index, method='ffill').fillna(sub_m15['close'])
    h4_ema50 = df_h4['EMA_50_H4'].reindex(sub_m15.index, method='ffill').fillna(sub_m15['close'])
    sub_m15['H1_Dist_EMA50'] = (sub_m15['close'] - h1_ema50) / sub_m15['close']
    sub_m15['H4_Dist_EMA50'] = (sub_m15['close'] - h4_ema50) / sub_m15['close']
    
    is_bull_seq = (sub_m15['close'] > sub_m15['open']).astype(int)
    is_bear_seq = (sub_m15['close'] < sub_m15['open']).astype(int)
    consec_bull = []
    consec_bear = []
    b_c = 0; br_c = 0
    for i in range(len(sub_m15)):
        if is_bull_seq.iloc[i] == 1:
            b_c += 1; br_c = 0
        elif is_bear_seq.iloc[i] == 1:
            br_c += 1; b_c = 0
        else:
            b_c = 0; br_c = 0
        consec_bull.append(b_c)
        consec_bear.append(br_c)
    sub_m15['Consecutive_Bull'] = consec_bull
    sub_m15['Consecutive_Bear'] = consec_bear
    
    sub_m15['TR'] = np.maximum(
        sub_m15['high'] - sub_m15['low'],
        np.maximum((sub_m15['high'] - sub_m15['close'].shift()).abs(), (sub_m15['low'] - sub_m15['close'].shift()).abs())
    )
    sub_m15['ATR_14'] = sub_m15['TR'].rolling(14).mean()
    
    plus_dm = np.where(
        (sub_m15['high'] - sub_m15['high'].shift(1)) > (sub_m15['low'].shift(1) - sub_m15['low']),
        np.maximum(sub_m15['high'] - sub_m15['high'].shift(1), 0), 0
    )
    minus_dm = np.where(
        (sub_m15['low'].shift(1) - sub_m15['low']) > (sub_m15['high'] - sub_m15['high'].shift(1)),
        np.maximum(sub_m15['low'].shift(1) - sub_m15['low'], 0), 0
    )
    atr_adx = pd.Series(sub_m15['TR'].values, index=sub_m15.index).rolling(14).mean()
    plus_di = 100 * pd.Series(plus_dm, index=sub_m15.index).rolling(14).mean() / (atr_adx + 1e-6)
    minus_di = 100 * pd.Series(minus_dm, index=sub_m15.index).rolling(14).mean() / (atr_adx + 1e-6)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6)
    sub_m15['ADX_14'] = dx.rolling(14).mean()
    sub_m15['Volume_Ratio'] = 1.0
    
    df_clean = sub_m15.dropna().copy()
    latest_candle = df_clean[features_list].iloc[[-1]]
    latest_atr = float(df_clean['ATR_14'].iloc[-1])
    
    probs = model.predict_proba(latest_candle)[0]
    prob_down = float(probs[0]) * 100.0
    prob_up = float(probs[1]) * 100.0
    
    c_close = float(df_clean['close'].iloc[-1])
    c_open = float(df_clean['open'].iloc[-1])
    c_high = float(df_clean['high'].iloc[-1])
    c_low = float(df_clean['low'].iloc[-1])
    
    slope, dyn_sup, dyn_res, channel_type, dist_dyn_sup, dist_dyn_res = bot.calc_dynamic_channel(df_clean, lookback=35)
    channel_data = {
        'slope': slope,
        'dyn_sup': dyn_sup,
        'dyn_res': dyn_res,
        'dyn_support': dyn_sup,
        'dyn_resistance': dyn_res,
        'channel_type': channel_type,
        'dist_dyn_sup': dist_dyn_sup,
        'dist_dyn_res': dist_dyn_res
    }
    pattern_data = bot.detect_multi_horizon_snr_and_patterns(sub_m15, lookback_multiday=300, lookback_pattern=40)
    struct_data = bot.detect_candle_structure(df_clean)
    tech_data = bot.calc_technical_indicators(sub_m15)
    
    dist_sup = (c_close - sub_m15['Swing_Low_20'].iloc[-1]) / c_close
    dist_res = (sub_m15['Swing_High_20'].iloc[-1] - c_close) / c_close
    lower_w = float(df_clean['Lower_Wick_Ratio'].iloc[-1])
    upper_w = float(df_clean['Upper_Wick_Ratio'].iloc[-1])
    
    h1_b = bool(df_clean['Trend_H1_Bull'].iloc[-1] == 1)
    h1_sb = bool(df_clean['Trend_H1_Strong'].iloc[-1] == 1)
    
    sig, zone, sl, tp, reason = bot.evaluate_multi_zone_decision(
        prob_up, prob_down, h1_b, h1_sb, latest_atr,
        dist_sup, dist_res, lower_w, upper_w,
        bool(c_close > c_open), bool(c_close < c_open),
        pattern_data['nearest_sup'], pattern_data['nearest_res'],
        struct_data, channel_data=channel_data, pattern_data=pattern_data,
        tech_data=tech_data, h4_context=None
    )
    
    results.append({
        'time': candle_time,
        'open': c_open, 'high': c_high, 'low': c_low, 'close': c_close,
        'prob_up': prob_up, 'prob_down': prob_down,
        'h1_bull': h1_b,
        'sig': sig, 'zone': zone, 'sl': sl, 'tp': tp, 'reason': reason,
        'idx': idx
    })
    
    if sig in ['BUY', 'SELL']:
        signals.append(results[-1])
    else:
        r_head = reason.split('|')[0].strip() if '|' in reason else reason
        standby_reasons[r_head] = standby_reasons.get(r_head, 0) + 1

print("\n" + "="*85)
print(f"HASIL PERSISI CANDLE DEMI CANDLE (03:30 - 14:15 WIB HARI INI):")
print("="*85)
for r in results:
    t_str = r['time'].strftime('%H:%M')
    p_max = max(r['prob_up'], r['prob_down'])
    p_dir = "UP" if r['prob_up'] >= r['prob_down'] else "DN"
    print(f"[{t_str} WIB] O:{r['open']:.2f} H:{r['high']:.2f} L:{r['low']:.2f} C:{r['close']:.2f} | H1_Bull:{r['h1_bull']} | AI:{p_dir} {p_max:.1f}% | Sinyal:{r['sig']} ({r['zone']}) | {r['reason']}")

print("\n" + "="*85)
print(f"RANGKUMAN STATISTIK BOT M15:")
print(f"• Total Candle M15: {len(results)}")
print(f"• Total Sinyal Valid Terbentuk: {len(signals)}")
print(f"• Distribusi Alasan Bot STANDBY / WAIT:")
for r_name, count in sorted(standby_reasons.items(), key=lambda x: x[1], reverse=True):
    print(f"   - {r_name}: {count} candle")

if len(signals) > 0:
    print("\n" + "="*85)
    print("SIMULASI EKSEKUSI SINYAL:")
    total_sim_pnl = 0.0
    for s in signals:
        e_time = s['time'].strftime('%H:%M')
        e_idx = s['idx']
        e_price = s['close']
        e_type = s['sig']
        sl_pts = s['sl'] * 0.1
        tp_pts = s['tp'] * 0.1
        
        tp_level = e_price + tp_pts if e_type == 'BUY' else e_price - tp_pts
        sl_level = e_price - sl_pts if e_type == 'BUY' else e_price + sl_pts
        
        future = df_all_m15.loc[e_idx+1:].copy()
        outcome = "FLOATING"
        pnl = 0.0
        for _, fc in future.iterrows():
            if e_type == 'BUY':
                if fc['high'] >= tp_level:
                    outcome = "HIT TP (WIN 🟢)"
                    pnl = 6.50
                    break
                elif fc['low'] <= sl_level:
                    outcome = "HIT SL (LOSS 🔴)"
                    pnl = -6.50
                    break
            else:
                if fc['low'] <= tp_level:
                    outcome = "HIT TP (WIN 🟢)"
                    pnl = 6.50
                    break
                elif fc['high'] >= sl_level:
                    outcome = "HIT SL (LOSS 🔴)"
                    pnl = -6.50
                    break
        total_sim_pnl += pnl
        print(f"👉 Entry {e_type} [{e_time} WIB] @ {e_price:.2f} | TP: {tp_level:.2f} | SL: {sl_level:.2f} -> {outcome} (PnL: ${pnl:+.2f})")
    print(f"\nTOTAL SIMULASI PnL: ${total_sim_pnl:+.2f}")
else:
    print("\nKESIMPULAN: Tidak ada sinyal entry yang valid memenuhi kriteria strategi model!")

mt5.shutdown()
