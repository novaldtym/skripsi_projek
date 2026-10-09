import os
import sys
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, roc_auc_score, log_loss, brier_score_loss, f1_score, precision_score, recall_score
)
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*85)
print("AUDIT RESMI & ILMIAH: KOMPARASI PREDICTION HORIZON (h=2, h=3, h=5)")
print("STANDAR KONSENSUS AHLI A & PENELITI B (BEBAS LEAKAGE 100%, 57 FITUR V5)")
print("="*85)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

sym = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Mengambil data historis {sym} dari MT5...")
rates_m15 = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 50000)
rates_h1  = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 15000)
rates_h4  = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H4, 0, 5000)

df = pd.DataFrame(rates_m15)
df['time'] = pd.to_datetime(df['time'], unit='s')
df.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 50000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    print("Mengambil DXY dari Yahoo Finance...")
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()
print(f"Data M15 berhasil dimuat: {len(df)} candle ({df.index[0]} s/d {df.index[-1]}).")

# =========================================================================
# REKAYASA FITUR 100% STERIL & KAUSAL (AUDITED VERSION 5.0)
# =========================================================================
print("\nMembangun 57 Fitur Bersih (Causal Delayed-Confirmed, Shifted MTF, Non-Leaking)...")

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

# 1. ORDER BLOCK 100% KAUSAL (BEBAS DARI shift(-2)!)
is_bear_c = df['close'] < df['open']
is_bull_c = df['close'] > df['open']
impulse_up_causal = (df['close'] - df['close'].shift(2)) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
impulse_dn_causal = (df['close'].shift(2) - df['close']) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up_causal.fillna(False)).astype(int)
df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn_causal.fillna(False)).astype(int)

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
df['XAU_Return_10'] = df['close'].pct_change(10)
df['XAU_Return_20'] = df['close'].pct_change(20)

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

# 2. MULTI-TIMEFRAME KAUSAL (SHIFT 1 PERIODE PENUH)
df_h1['EMA_50_H1']  = df_h1['close'].shift(1).ewm(span=50, adjust=False).mean()
df_h1['EMA_200_H1'] = df_h1['close'].shift(1).ewm(span=200, adjust=False).mean()
df_h1['Trend_H1_Bull']   = (df_h1['close'].shift(1) > df_h1['EMA_50_H1']).astype(int)
df_h1['Trend_H1_Strong'] = (df_h1['EMA_50_H1'] > df_h1['EMA_200_H1']).astype(int)
df_h1['H1_Dist_EMA50']   = (df_h1['close'].shift(1) - df_h1['EMA_50_H1']) / df_h1['close'].shift(1)

df_h4['EMA_50_H4']  = df_h4['close'].shift(1).ewm(span=50, adjust=False).mean()
df_h4['EMA_200_H4'] = df_h4['close'].shift(1).ewm(span=200, adjust=False).mean()
df_h4['Trend_H4_Bull']   = (df_h4['close'].shift(1) > df_h4['EMA_50_H4']).astype(int)
df_h4['Trend_H4_Strong'] = (df_h4['EMA_50_H4'] > df_h4['EMA_200_H4']).astype(int)
df_h4['H4_Dist_EMA50']   = (df_h4['close'].shift(1) - df_h4['EMA_50_H4']) / df_h4['close'].shift(1)

for c in ['Trend_H1_Bull', 'Trend_H1_Strong', 'H1_Dist_EMA50']:
    df[c] = df_h1[c].reindex(df.index, method='ffill').fillna(0)

for c in ['Trend_H4_Bull', 'Trend_H4_Strong', 'H4_Dist_EMA50']:
    df[c] = df_h4[c].reindex(df.index, method='ffill').fillna(0)

is_bull = (df['close'] > df['open']).astype(int)
is_bear = (df['close'] < df['open']).astype(int)
df['Consecutive_Bull'] = is_bull.groupby((is_bull != is_bull.shift()).cumsum()).cumsum()
df['Consecutive_Bear'] = is_bear.groupby((is_bear != is_bear.shift()).cumsum()).cumsum()

high_diff = df['high'].diff()
low_diff  = -df['low'].diff()
plus_dm  = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
tr = pd.concat([
    df['high'] - df['low'],
    (df['high'] - df['close'].shift()).abs(),
    (df['low']  - df['close'].shift()).abs()
], axis=1).max(axis=1)

atr14 = tr.rolling(14).mean() + 1e-6
df['ATR_14'] = atr14
plus_di  = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).mean() / atr14)
minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).mean() / atr14)
dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di + 1e-6))
df['ADX_14'] = dx.rolling(14).mean()

vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
df['Volume_Ratio'] = df[vol_col] / (df[vol_col].rolling(20).mean() + 1e-6)

# 3. FITUR STRUKTURAL & GEOMETRIS TAMBAHAN (V5.0)
df['Major_Demand_300'] = df['low'].shift(1).rolling(300).min()
df['Major_Supply_300'] = df['high'].shift(1).rolling(300).max()
df['Dist_Major_Demand'] = (df['close'] - df['Major_Demand_300']) / df['close']
df['Dist_Major_Supply'] = (df['Major_Supply_300'] - df['close']) / df['close']

nearest_min_dist = df[['Dist_Support', 'Dist_Resistance']].min(axis=1)
df['Nearest_Clearance'] = nearest_min_dist - 0.0018
df['Est_RRR_Buy']  = (df['Dist_Resistance'] + 1e-5) / (df['Dist_Support'] + 1e-5)
df['Est_RRR_Sell'] = (df['Dist_Support'] + 1e-5) / (df['Dist_Resistance'] + 1e-5)
df['Pinbar_Ratio'] = df[['Lower_Wick_Ratio', 'Upper_Wick_Ratio']].max(axis=1) / (df['Body_Ratio'] + 1e-5)

def fast_rolling_slope(series, window=35):
    x = np.arange(window)
    x_mean = x.mean()
    x_var = ((x - x_mean)**2).sum()
    weights = (x - x_mean) / x_var
    return series.rolling(window).apply(lambda y: np.dot(y, weights), raw=True)

df['Pattern_Slope_High'] = fast_rolling_slope(df['high'], 35).fillna(0)
df['Pattern_Slope_Low']  = fast_rolling_slope(df['low'], 35).fillna(0)
spread_35 = (df['high'] - df['low']).rolling(35).mean() + 1e-5
df['Pattern_Convergence'] = (df['Pattern_Slope_Low'] - df['Pattern_Slope_High']) / spread_35

p_code = np.zeros(len(df))
sh = df['Pattern_Slope_High'].values
sl = df['Pattern_Slope_Low'].values
for i in range(len(df)):
    if sl[i] > 0.06 and abs(sh[i]) <= 0.15: p_code[i] = 1
    elif sh[i] < -0.06 and abs(sl[i]) <= 0.15: p_code[i] = 2
    elif sh[i] < -0.08 and sl[i] > 0.08: p_code[i] = 3
    elif sh[i] > 0.10 and sl[i] > 0.10: p_code[i] = 6
    elif sh[i] < -0.10 and sl[i] < -0.10: p_code[i] = 7
    else: p_code[i] = 0
df['Pattern_Type_Code'] = p_code

roll_max1 = df['high'].shift(1).rolling(20).max()
roll_max2 = df['high'].shift(21).rolling(20).max()
df['Double_Top_Dist'] = (roll_max1 - roll_max2).abs() / df['close']

roll_min1 = df['low'].shift(1).rolling(20).min()
roll_min2 = df['low'].shift(21).rolling(20).min()
df['Double_Bottom_Dist'] = (roll_min1 - roll_min2).abs() / df['close']

features_57 = [
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
    'XAU_Return_10', 'XAU_Return_20',
    'Dist_Major_Demand', 'Dist_Major_Supply',
    'Nearest_Clearance', 'Est_RRR_Buy', 'Est_RRR_Sell',
    'Pinbar_Ratio',
    'Pattern_Slope_High', 'Pattern_Slope_Low', 'Pattern_Convergence', 'Pattern_Type_Code',
    'Double_Top_Dist', 'Double_Bottom_Dist',
    'Swing_High_20'
]

print(f"Total fitur valid: {len(features_57)} fitur.")

# =========================================================================
# EKSPERIMEN MULTI-HORIZON DENGAN BOUNDARY PURGING KETAT
# =========================================================================
horizons = [2, 3, 5]
results = []

lgb_params = dict(
    n_estimators=600, learning_rate=0.02, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)

for h in horizons:
    print(f"\n" + "-"*65)
    print(f"EVALUASI PREDICTION HORIZON h = {h} CANDLE ({h * 15} MENIT)")
    print(f"-"*65)
    
    # 1. Target Definisi
    df_h_exp = df.copy()
    df_h_exp['Target_Dir'] = (df_h_exp['close'].shift(-h) > df_h_exp['close']).astype(int)
    
    # Bersihkan NaN
    df_clean = df_h_exp.dropna(subset=features_57 + ['Target_Dir']).copy()
    N = len(df_clean)
    
    raw_train_end = int(N * 0.70)
    raw_val_end   = int(N * 0.85)
    
    # BOUNDARY PURGING TEPAT h BAR
    train_df = df_clean.iloc[:raw_train_end - h].copy()
    val_df   = df_clean.iloc[raw_train_end : raw_val_end - h].copy()
    test_df  = df_clean.iloc[raw_val_end : N - h].copy()
    
    print(f"Train Set      : {len(train_df)} bar (Purged {h} bar at boundary)")
    print(f"Validation Set : {len(val_df)} bar (Purged {h} bar at boundary)")
    print(f"Test Set       : {len(test_df)} bar ({test_df.index[0]} s/d {test_df.index[-1]})")
    
    # Melatih Model
    model = LGBMClassifier(**lgb_params)
    model.fit(train_df[features_57], train_df['Target_Dir'])
    
    # Prediksi Test Set
    y_test = test_df['Target_Dir']
    test_probs = model.predict_proba(test_df[features_57])[:, 1]
    test_preds = (test_probs >= 0.5).astype(int)
    test_conf  = np.maximum(test_probs, 1 - test_probs)
    
    # Metrik Akademik ML
    global_acc = accuracy_score(y_test, test_preds) * 100
    auc_score  = roc_auc_score(y_test, test_probs)
    ll_score   = log_loss(y_test, test_probs)
    brier      = brier_score_loss(y_test, test_probs)
    
    # Seleksi Ambang Batas 65%
    mask65 = test_conf >= 0.65
    cov65  = mask65.mean() * 100
    n65    = mask65.sum()
    
    if n65 > 0:
        acc65 = accuracy_score(y_test[mask65], (test_probs[mask65] >= 0.5).astype(int)) * 100
    else:
        acc65 = 0.0
        
    # Baseline Class Prior & 50/50
    p_prior = train_df['Target_Dir'].mean()
    brier_prior = brier_score_loss(y_test, np.full(len(y_test), p_prior))
    brier_5050  = brier_score_loss(y_test, np.full(len(y_test), 0.50))
    
    # Simulasi Trading Realistis pada Sinyal >= 65%
    # Standar Riset Skripsi: Modal $500, Lot 0.01 ($1.0/point), Spread 0.20 ($0.20/trade)
    # Holding period = h candles, evaluasi Close(t+h) vs Close(t)
    trades_pnl = []
    win_count = 0
    loss_count = 0
    
    test_signals = test_df[mask65].copy()
    test_signals['prob'] = test_probs[mask65]
    test_signals['pred'] = (test_probs[mask65] >= 0.5).astype(int)
    
    # Cari index posisi harga saat t+h
    test_indices = np.where(mask65)[0]
    for idx in test_indices:
        entry_row = test_df.iloc[idx]
        exit_idx = min(idx + h, len(test_df) - 1)
        exit_row  = test_df.iloc[exit_idx]
        
        entry_price = entry_row['close']
        exit_price  = exit_row['close']
        direction = 1 if test_probs[idx] >= 0.5 else 0
        
        # Hitung PnL kotor (0.01 lot: $1.0 per 1 poin pergerakan emas)
        if direction == 1:
            price_diff = exit_price - entry_price
        else:
            price_diff = entry_price - exit_price
            
        gross_pnl = price_diff * 1.0 # 0.01 lot
        net_pnl = gross_pnl - 0.20   # potongan spread/komisi $0.20 (0.01 lot)
        trades_pnl.append(net_pnl)
        if net_pnl > 0:
            win_count += 1
        else:
            loss_count += 1
            
    total_trades = len(trades_pnl)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
    total_pnl = sum(trades_pnl)
    gross_wins = sum([p for p in trades_pnl if p > 0])
    gross_losses = abs(sum([p for p in trades_pnl if p <= 0]))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else 99.0
    
    cum_pnl = np.cumsum(trades_pnl)
    peak = np.maximum.accumulate(cum_pnl) if len(cum_pnl) > 0 else [0]
    drawdown = peak - cum_pnl if len(cum_pnl) > 0 else [0]
    max_dd = np.max(drawdown) if len(drawdown) > 0 else 0.0
    
    print(f"Hasil Evaluasi Akademik (Test Set):")
    print(f"  - Akurasi Global (50%) : {global_acc:.2f}%")
    print(f"  - ROC-AUC              : {auc_score:.4f}")
    print(f"  - Brier Score          : {brier:.4f} (Baseline Prior: {brier_prior:.4f})")
    print(f"  - Akurasi @ >=65%      : {acc65:.2f}%")
    print(f"  - Cakupan (Coverage)   : {cov65:.2f}% ({n65} sinyal)")
    print(f"Hasil Evaluasi Trading Realistis (Holding {h} candle):")
    print(f"  - Total Trades         : {total_trades}")
    print(f"  - Trade Win Rate       : {win_rate:.2f}%")
    print(f"  - Total Net PnL        : ${total_pnl:,.2f}")
    print(f"  - Profit Factor        : {profit_factor:.2f}")
    print(f"  - Max Drawdown         : ${max_dd:,.2f}")
    
    results.append({
        'Horizon_Candle': h,
        'Horizon_Minutes': h * 15,
        'Global_Acc': global_acc,
        'ROC_AUC': auc_score,
        'Brier_Score': brier,
        'Acc_at_65': acc65,
        'Coverage_65': cov65,
        'Total_Signals': n65,
        'Trading_WinRate': win_rate,
        'Total_Net_PnL': total_pnl,
        'Profit_Factor': profit_factor,
        'Max_Drawdown': max_dd
    })

res_df = pd.DataFrame(results)
print("\n" + "="*85)
print("TABEL RINGKASAN RESMI KOMPARASI PREDICTION HORIZON (BEBAS LEAKAGE 100%)")
print("="*85)
print(res_df.to_string(index=False))

res_df.to_csv("hasil_audit_komparasi_horizon_bebas_leakage.csv", index=False)
print("\nHasil tersimpan di: hasil_audit_komparasi_horizon_bebas_leakage.csv")
