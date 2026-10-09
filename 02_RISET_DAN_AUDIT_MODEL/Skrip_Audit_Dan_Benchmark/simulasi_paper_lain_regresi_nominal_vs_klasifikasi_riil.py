import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
from lightgbm import LGBMRegressor, LGBMClassifier
from xgboost import XGBRegressor, XGBClassifier
from sklearn.ensemble import RandomForestRegressor
import MetaTrader5 as mt5
import yfinance as yf

print("="*110)
print("EKSPERIMEN KRITIS SKRIPSI INFORMATIKA: ILUSI REGRESI HARGA NOMINAL VS KLASIFIKASI ARAH RIIL")
print("MENJAWAB PERTANYAAN: 'BAGAIMANA JIKA MODEL DARI PAPER PENELITIAN LAIN DIUJI LANGSUNG DI PASAR MT5?'")
print("STANDAR PENGUJIAN: DATA INDEPENDEN 4.940 CANDLE M15, MODAL $500 USD, LOT 0.01, SPREAD $0.20 USD")
print("="*110)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 25000)
rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 8000)
rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 2500)

df_raw = pd.DataFrame(rates_m15)
df_raw['time'] = pd.to_datetime(df_raw['time'], unit='s')
df_raw.set_index('time', inplace=True)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
df_h1.set_index('time', inplace=True)

df_h4 = pd.DataFrame(rates_h4)
df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
df_h4.set_index('time', inplace=True)

mt5.symbol_select('DXY', True)
rates_dxy = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 25000)
if rates_dxy is not None and len(rates_dxy) > 0:
    df_dxy = pd.DataFrame(rates_dxy)
    df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s')
    df_dxy.set_index('time', inplace=True)
    dxy_close = df_dxy['close']
else:
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()

def extract_features_clean(df_in, df_h1_in, df_h4_in, dxy_in):
    df = df_in.copy()
    df_h1_loc = df_h1_in.copy()
    df_h4_loc = df_h4_in.copy()
    
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
    
    impulse_up = (df['close'] - df['close'].shift(2)) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
    impulse_dn = (df['close'].shift(2) - df['close']) > (1.5 * (df['high'].shift(2) - df['low'].shift(2)))
    df['Order_Block_Bull'] = (is_bear_c.shift(2).fillna(False) & impulse_up.fillna(False)).astype(int)
    df['Order_Block_Bear'] = (is_bull_c.shift(2).fillna(False) & impulse_dn.fillna(False)).astype(int)

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

    df['DXY_Close'] = dxy_in.reindex(df.index, method='ffill').bfill()
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

    h1_close_series = df_h1_loc['close'].shift(1)
    h4_close_series = df_h4_loc['close'].shift(1)
    
    df_h1_loc['EMA_50_H1']  = h1_close_series.ewm(span=50, adjust=False).mean()
    df_h1_loc['EMA_200_H1'] = h1_close_series.ewm(span=200, adjust=False).mean()
    df_h1_loc['Trend_H1_Bull']   = (h1_close_series > df_h1_loc['EMA_50_H1']).astype(int)
    df_h1_loc['Trend_H1_Strong'] = (df_h1_loc['EMA_50_H1'] > df_h1_loc['EMA_200_H1']).astype(int)
    df_h1_loc['H1_Dist_EMA50']   = (h1_close_series - df_h1_loc['EMA_50_H1']) / h1_close_series

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

    # Fitur Geometris & Struktural v5.0
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
        elif sh[i] < -0.06 and abs(sh[i]) <= 0.15: p_code[i] = 2
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

    # TARGET 1: Target Klasifikasi Arah 75 Menit (Skripsi Nouval)
    h = 5
    df['Target_Dir'] = (df['close'].shift(-h) > df['close']).astype(int)
    
    # TARGET 2: Target Regresi Harga Nominal 75 Menit (Paper Yuan 2023, Ben Jabeur 2024, Landge 2024)
    df['Target_Nominal_75M'] = df['close'].shift(-h)
    
    # TARGET 3: Target Regresi Harga Nominal 1 Bar / 15 Menit (Santoso 2025, Prastyo 2025)
    df['Target_Nominal_1Bar'] = df['close'].shift(-1)
    
    return df

df_clean = extract_features_clean(df_raw, df_h1, df_h4, dxy_close)

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

h = 5
df_valid = df_clean.dropna(subset=features_57 + ['Target_Dir', 'Target_Nominal_75M', 'Target_Nominal_1Bar', 'ATR_14']).copy()
split_idx = int(len(df_valid) * 0.80)
train_df = df_valid.iloc[:split_idx - h].copy()
test_df  = df_valid.iloc[split_idx:].copy()

print(f"Data Siap: Train={len(train_df)} bar, Test={len(test_df)} bar.")

# ENGINE SIMULASI TRADING DARI SINYAL REGRESI MAUPUN KLASIFIKASI
def simulate_trading_generic(test_df, signals, mode="sniper_rrr2"):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    n = len(closes)
    
    trades = []
    active_until = -1
    max_bars = 30
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        sig = signals[i] # 'BUY', 'SELL', atau 'HOLD'
        if sig not in ['BUY', 'SELL']:
            continue
            
        entry_p = closes[i]
        
        if mode == "sniper_rrr2":
            tp_dist = 12.00
            sl_dist = 6.00
        elif mode == "pure_75m":
            exit_p = closes[min(i + 5, n - 1)]
            pnl_gross = (exit_p - entry_p) if sig == 'BUY' else (entry_p - exit_p)
            pnl_net = (pnl_gross * 1.0) - SPREAD
            trades.append(pnl_net)
            active_until = i + 5
            continue
            
        tp_p = entry_p + tp_dist if sig == 'BUY' else entry_p - tp_dist
        sl_p = entry_p - sl_dist if sig == 'BUY' else entry_p + sl_dist
        
        outcome = "TIMEOUT"
        pnl_gross = 0.0
        held_bars = max_bars
        
        for step in range(1, max_bars + 1):
            cur_idx = i + step
            h_bar = highs[cur_idx]
            l_bar = lows[cur_idx]
            
            if sig == 'BUY':
                hit_tp = h_bar >= tp_p
                hit_sl = l_bar <= sl_p
                if hit_tp and hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
            else:
                hit_tp = l_bar <= tp_p
                hit_sl = h_bar >= sl_p
                if hit_tp and hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                elif hit_tp:
                    outcome = "WIN"
                    pnl_gross = tp_dist
                    held_bars = step
                    break
                elif hit_sl:
                    outcome = "LOSS"
                    pnl_gross = -sl_dist
                    held_bars = step
                    break
                    
        if outcome == "TIMEOUT":
            last_p = closes[i + max_bars]
            pnl_gross = (last_p - entry_p) if sig == 'BUY' else (entry_p - last_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    trades = np.array(trades)
    n_trades = len(trades)
    if n_trades == 0:
        return 0, 0.0, 0.0, 0.0, 0.0
        
    wins = (trades > 0).sum()
    wr = (wins / n_trades) * 100.0
    tot_pnl = trades.sum()
    
    gross_win = trades[trades > 0].sum()
    gross_loss = abs(trades[trades < 0].sum())
    pf = (gross_win / gross_loss) if gross_loss > 0 else 99.0
    
    equity = np.cumsum(np.insert(trades, 0, 0))
    peak = np.maximum.accumulate(equity)
    dd = equity - peak
    max_dd = abs(dd.min())
    
    return n_trades, wr, tot_pnl, pf, max_dd

# DAFTAR MODEL YANG DIUJI:
# 1. NAIVE LAGGER: Tebak harga masa depan = harga sekarang
# 2. REGRESI NOMINAL LIGHTGBM 75M (Pendekatan Yuan 2023)
# 3. REGRESI NOMINAL XGBOOST 75M (Pendekatan Ben Jabeur 2024)
# 4. REGRESI NOMINAL RANDOM FOREST 75M (Pendekatan Landge 2024 & Prastyo 2025)
# 5. REGRESI DELTA HARGA LIGHTGBM (Pendekatan Santoso et al. Telkom 2025)
# 6. KLASIFIKASI PROBABILITAS ARAH V5.0 TUNED THRESHOLD >= 65% (SKRIPSI NOUVAL)

y_test_nominal_75m = test_df['Target_Nominal_75M'].values
current_price_test = test_df['close'].values

results_comparative = []

print("\n--- 1. NAIVE BENCHMARK: TEBAK HARGA SAMA DENGAN HARGA SAAT INI (P_t+h = P_t) ---")
naive_preds = current_price_test
r2_naive = r2_score(y_test_nominal_75m, naive_preds)
rmse_naive = np.sqrt(mean_squared_error(y_test_nominal_75m, naive_preds))
mae_naive = mean_absolute_error(y_test_nominal_75m, naive_preds)
mape_naive = mean_absolute_percentage_error(y_test_nominal_75m, naive_preds) * 100.0
print(f"Naive Baseline: R2 = {r2_naive:.4f}, RMSE = ${rmse_naive:.2f}, MAE = ${mae_naive:.2f}, MAPE = {mape_naive:.2f}%")
results_comparative.append({
    "Pendekatan_Model": "Naive Baseline (Identity Lag P_t)",
    "Fokus_Paper_Rujukan": "Ekonometrika Dasar (Random Walk)",
    "Target_Model": "Harga Nominal 75M",
    "R2_Score": round(r2_naive, 4),
    "RMSE_USD": round(rmse_naive, 2),
    "MAE_USD": round(mae_naive, 2),
    "MAPE_Pct": round(mape_naive, 2),
    "Directional_Accuracy_Pct": 50.0,
    "Trades": 0,
    "WinRate_Sniper_Pct": 0.0,
    "PnL_Sniper_USD": 0.0,
    "MaxDD_Sniper_USD": 0.0,
    "PnL_Pure75M_USD": 0.0
})

print("\n--- 2. REGRESI NOMINAL LIGHTGBM (Yuan 2023 / Springer 2023) ---")
lgb_reg = LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=31, random_state=42, n_jobs=-1, verbose=-1)
lgb_reg.fit(train_df[features_57].values, train_df['Target_Nominal_75M'].values)
lgb_reg_preds = lgb_reg.predict(test_df[features_57].values)

r2_lgb_reg = r2_score(y_test_nominal_75m, lgb_reg_preds)
rmse_lgb_reg = np.sqrt(mean_squared_error(y_test_nominal_75m, lgb_reg_preds))
mae_lgb_reg = mean_absolute_error(y_test_nominal_75m, lgb_reg_preds)
mape_lgb_reg = mean_absolute_percentage_error(y_test_nominal_75m, lgb_reg_preds) * 100.0

# Sinyal Trading: Jika Prediksi Harga Masa Depan > Harga Sekarang + Buffer $0.50 -> BUY, else SELL
pred_diff_lgb = lgb_reg_preds - current_price_test
signals_lgb_reg = np.where(pred_diff_lgb > 1.0, 'BUY', np.where(pred_diff_lgb < -1.0, 'SELL', 'HOLD'))
tr_lgb_r, wr_lgb_r, pnl_lgb_r, pf_lgb_r, dd_lgb_r = simulate_trading_generic(test_df, signals_lgb_reg, mode="sniper_rrr2")
tr_lgb_r75, wr_lgb_r75, pnl_lgb_r75, pf_lgb_r75, dd_lgb_r75 = simulate_trading_generic(test_df, signals_lgb_reg, mode="pure_75m")

acc_dir_lgb_r = (np.sign(lgb_reg_preds - current_price_test) == np.sign(y_test_nominal_75m - current_price_test)).mean() * 100.0
print(f"LGBM Regresi: R2 = {r2_lgb_reg:.4f}, MAE = ${mae_lgb_reg:.2f}, MAPE = {mape_lgb_reg:.2f}%")
print(f" -> Trading Sniper RRR 1:2: PnL = ${pnl_lgb_r:+.2f} USD | WR = {wr_lgb_r:.1f}% | DD = ${dd_lgb_r:.2f}")

results_comparative.append({
    "Pendekatan_Model": "LightGBM Regresi Nominal 75M",
    "Fokus_Paper_Rujukan": "Ziyang Yuan (2023) / NovelFinancial (2023)",
    "Target_Model": "Harga Nominal 75M",
    "R2_Score": round(r2_lgb_reg, 4),
    "RMSE_USD": round(rmse_lgb_reg, 2),
    "MAE_USD": round(mae_lgb_reg, 2),
    "MAPE_Pct": round(mape_lgb_reg, 2),
    "Directional_Accuracy_Pct": round(acc_dir_lgb_r, 2),
    "Trades": tr_lgb_r,
    "WinRate_Sniper_Pct": round(wr_lgb_r, 2),
    "PnL_Sniper_USD": round(pnl_lgb_r, 2),
    "MaxDD_Sniper_USD": round(dd_lgb_r, 2),
    "PnL_Pure75M_USD": round(pnl_lgb_r75, 2)
})

print("\n--- 3. REGRESI NOMINAL XGBOOST (Ben Jabeur et al. 2024 / Shuo Liu 2024) ---")
xgb_reg = XGBRegressor(n_estimators=500, learning_rate=0.03, max_depth=5, random_state=42, n_jobs=-1)
xgb_reg.fit(train_df[features_57].values, train_df['Target_Nominal_75M'].values)
xgb_reg_preds = xgb_reg.predict(test_df[features_57].values)

r2_xgb_reg = r2_score(y_test_nominal_75m, xgb_reg_preds)
rmse_xgb_reg = np.sqrt(mean_squared_error(y_test_nominal_75m, xgb_reg_preds))
mae_xgb_reg = mean_absolute_error(y_test_nominal_75m, xgb_reg_preds)
mape_xgb_reg = mean_absolute_percentage_error(y_test_nominal_75m, xgb_reg_preds) * 100.0

pred_diff_xgb = xgb_reg_preds - current_price_test
signals_xgb_reg = np.where(pred_diff_xgb > 1.0, 'BUY', np.where(pred_diff_xgb < -1.0, 'SELL', 'HOLD'))
tr_xgb_r, wr_xgb_r, pnl_xgb_r, pf_xgb_r, dd_xgb_r = simulate_trading_generic(test_df, signals_xgb_reg, mode="sniper_rrr2")
tr_xgb_r75, wr_xgb_r75, pnl_xgb_r75, pf_xgb_r75, dd_xgb_r75 = simulate_trading_generic(test_df, signals_xgb_reg, mode="pure_75m")

acc_dir_xgb_r = (np.sign(xgb_reg_preds - current_price_test) == np.sign(y_test_nominal_75m - current_price_test)).mean() * 100.0
print(f"XGBoost Regresi: R2 = {r2_xgb_reg:.4f}, MAE = ${mae_xgb_reg:.2f}, MAPE = {mape_xgb_reg:.2f}%")
print(f" -> Trading Sniper RRR 1:2: PnL = ${pnl_xgb_r:+.2f} USD | WR = {wr_xgb_r:.1f}% | DD = ${dd_xgb_r:.2f}")

results_comparative.append({
    "Pendekatan_Model": "XGBoost Regresi Nominal 75M",
    "Fokus_Paper_Rujukan": "Ben Jabeur (Springer 2024)",
    "Target_Model": "Harga Nominal 75M",
    "R2_Score": round(r2_xgb_reg, 4),
    "RMSE_USD": round(rmse_xgb_reg, 2),
    "MAE_USD": round(mae_xgb_reg, 2),
    "MAPE_Pct": round(mape_xgb_reg, 2),
    "Directional_Accuracy_Pct": round(acc_dir_xgb_r, 2),
    "Trades": tr_xgb_r,
    "WinRate_Sniper_Pct": round(wr_xgb_r, 2),
    "PnL_Sniper_USD": round(pnl_xgb_r, 2),
    "MaxDD_Sniper_USD": round(dd_xgb_r, 2),
    "PnL_Pure75M_USD": round(pnl_xgb_r75, 2)
})

print("\n--- 4. REGRESI NOMINAL RANDOM FOREST (Landge et al. 2024 / Prastyo et al. CEST 2025) ---")
rf_reg = RandomForestRegressor(n_estimators=200, max_depth=8, random_state=42, n_jobs=-1)
rf_reg.fit(train_df[features_57].values, train_df['Target_Nominal_75M'].values)
rf_reg_preds = rf_reg.predict(test_df[features_57].values)

r2_rf_reg = r2_score(y_test_nominal_75m, rf_reg_preds)
rmse_rf_reg = np.sqrt(mean_squared_error(y_test_nominal_75m, rf_reg_preds))
mae_rf_reg = mean_absolute_error(y_test_nominal_75m, rf_reg_preds)
mape_rf_reg = mean_absolute_percentage_error(y_test_nominal_75m, rf_reg_preds) * 100.0

pred_diff_rf = rf_reg_preds - current_price_test
signals_rf_reg = np.where(pred_diff_rf > 1.0, 'BUY', np.where(pred_diff_rf < -1.0, 'SELL', 'HOLD'))
tr_rf_r, wr_rf_r, pnl_rf_r, pf_rf_r, dd_rf_r = simulate_trading_generic(test_df, signals_rf_reg, mode="sniper_rrr2")
tr_rf_r75, wr_rf_r75, pnl_rf_r75, pf_rf_r75, dd_rf_r75 = simulate_trading_generic(test_df, signals_rf_reg, mode="pure_75m")

acc_dir_rf_r = (np.sign(rf_reg_preds - current_price_test) == np.sign(y_test_nominal_75m - current_price_test)).mean() * 100.0
print(f"Random Forest Regresi: R2 = {r2_rf_reg:.4f}, MAE = ${mae_rf_reg:.2f}, MAPE = {mape_rf_reg:.2f}%")
print(f" -> Trading Sniper RRR 1:2: PnL = ${pnl_rf_r:+.2f} USD | WR = {wr_rf_r:.1f}% | DD = ${dd_rf_r:.2f}")

results_comparative.append({
    "Pendekatan_Model": "Random Forest Regresi Nominal 75M",
    "Fokus_Paper_Rujukan": "Landge (2024) / Prastyo (CEST 2025)",
    "Target_Model": "Harga Nominal 75M",
    "R2_Score": round(r2_rf_reg, 4),
    "RMSE_USD": round(rmse_rf_reg, 2),
    "MAE_USD": round(mae_rf_reg, 2),
    "MAPE_Pct": round(mape_rf_reg, 2),
    "Directional_Accuracy_Pct": round(acc_dir_rf_r, 2),
    "Trades": tr_rf_r,
    "WinRate_Sniper_Pct": round(wr_rf_r, 2),
    "PnL_Sniper_USD": round(pnl_rf_r, 2),
    "MaxDD_Sniper_USD": round(dd_rf_r, 2),
    "PnL_Pure75M_USD": round(pnl_rf_r75, 2)
})

print("\n--- 5. REGRESI DELTA TARGET HARGA (Santoso et al. Telkom University 2025) ---")
train_delta = train_df['Target_Nominal_75M'] - train_df['close']
test_delta  = test_df['Target_Nominal_75M'] - test_df['close']

lgb_delta = LGBMRegressor(n_estimators=500, learning_rate=0.03, num_leaves=31, random_state=42, n_jobs=-1, verbose=-1)
lgb_delta.fit(train_df[features_57].values, train_delta.values)
pred_delta = lgb_delta.predict(test_df[features_57].values)
pred_reconstruct = current_price_test + pred_delta

r2_delta = r2_score(test_delta, pred_delta) # R2 pada perubahan murni
r2_reconst = r2_score(y_test_nominal_75m, pred_reconstruct) # R2 harga rekonstruksi
mae_delta = mean_absolute_error(test_delta, pred_delta)
acc_dir_delta = (np.sign(pred_delta) == np.sign(test_delta)).mean() * 100.0

signals_delta = np.where(pred_delta > 1.0, 'BUY', np.where(pred_delta < -1.0, 'SELL', 'HOLD'))
tr_dlt, wr_dlt, pnl_dlt, pf_dlt, dd_dlt = simulate_trading_generic(test_df, signals_delta, mode="sniper_rrr2")
tr_dlt75, wr_dlt75, pnl_dlt75, pf_dlt75, dd_dlt75 = simulate_trading_generic(test_df, signals_delta, mode="pure_75m")

print(f"LGBM Delta (Santoso): R2 Delta Murni = {r2_delta:.4f}, R2 Rekonstruksi = {r2_reconst:.4f}, Acc Arah = {acc_dir_delta:.2f}%")
print(f" -> Trading Sniper RRR 1:2: PnL = ${pnl_dlt:+.2f} USD | WR = {wr_dlt:.1f}% | DD = ${dd_dlt:.2f}")

results_comparative.append({
    "Pendekatan_Model": "LightGBM Delta Target (Delta Rekonstruksi)",
    "Fokus_Paper_Rujukan": "Santoso et al. (Telkom University 2025)",
    "Target_Model": "Delta Harga (P_t+h - P_t)",
    "R2_Score": round(r2_reconst, 4),
    "RMSE_USD": round(np.sqrt(mean_squared_error(y_test_nominal_75m, pred_reconstruct)), 2),
    "MAE_USD": round(mae_delta, 2),
    "MAPE_Pct": round(mean_absolute_percentage_error(y_test_nominal_75m, pred_reconstruct)*100, 2),
    "Directional_Accuracy_Pct": round(acc_dir_delta, 2),
    "Trades": tr_dlt,
    "WinRate_Sniper_Pct": round(wr_dlt, 2),
    "PnL_Sniper_USD": round(pnl_dlt, 2),
    "MaxDD_Sniper_USD": round(dd_dlt, 2),
    "PnL_Pure75M_USD": round(pnl_dlt75, 2)
})

print("\n--- 6. KLASIFIKASI PROBABILITAS ARAH SELEKTIF V5.0 (PENELITIAN SKRIPSI NOUVAL) ---")
lgb_clf = LGBMClassifier(
    n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
    min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
    reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
    random_state=42, n_jobs=-1, verbose=-1
)
lgb_clf.fit(train_df[features_57].values, train_df['Target_Dir'].values)
probs_clf = lgb_clf.predict_proba(test_df[features_57].values)[:, 1]

# Sinyal Selektif >= 65%
conf_clf = np.maximum(probs_clf, 1.0 - probs_clf)
signals_clf = np.where(conf_clf >= 0.65, np.where(probs_clf >= 0.5, 'BUY', 'SELL'), 'HOLD')

mask65 = conf_clf >= 0.65
acc65 = accuracy_score(test_df['Target_Dir'].values[mask65], (probs_clf[mask65] >= 0.5).astype(int)) * 100.0

tr_clf, wr_clf, pnl_clf, pf_clf, dd_clf = simulate_trading_generic(test_df, signals_clf, mode="sniper_rrr2")
tr_clf75, wr_clf75, pnl_clf75, pf_clf75, dd_clf75 = simulate_trading_generic(test_df, signals_clf, mode="pure_75m")

print(f"Skripsi Nouval (Klasifikasi Selektif >=65%): Acc Selective = {acc65:.2f}%")
print(f" -> Trading Sniper RRR 1:2: PnL = ${pnl_clf:+.2f} USD | WR = {wr_clf:.1f}% | DD = ${dd_clf:.2f}")
print(f" -> Trading Pure 75M Exit : PnL = ${pnl_clf75:+.2f} USD | PF = {pf_clf75:.2f}")

results_comparative.append({
    "Pendekatan_Model": "LightGBM Klasifikasi Probabilitas Selektif (>=65%)",
    "Fokus_Paper_Rujukan": "Skripsi Nouval Ditya M. (UPN Veteran Yogyakarta)",
    "Target_Model": "Probabilitas Arah Biner + Reject Option",
    "R2_Score": "-", # Not Applicable for Classification
    "RMSE_USD": "-",
    "MAE_USD": "-",
    "MAPE_Pct": "-",
    "Directional_Accuracy_Pct": round(acc65, 2),
    "Trades": tr_clf,
    "WinRate_Sniper_Pct": round(wr_clf, 2),
    "PnL_Sniper_USD": round(pnl_clf, 2),
    "MaxDD_Sniper_USD": round(dd_clf, 2),
    "PnL_Pure75M_USD": round(pnl_clf75, 2)
})

df_comp = pd.DataFrame(results_comparative)
excel_out = r"d:\SKRIPSI INFORMATIKA\03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Komparasi_HeadToHead_PaperLain_RegresiNominal_vs_SkripsiNouval.xlsx"
df_comp.to_excel(excel_out, index=False)

print("\n" + "="*110)
print("HASIL KOMPARASI HEAD-TO-HEAD: REGRESI NOMINAL PAPER LAIN VS KLASIFIKASI SKRIPSI NOUVAL")
print("="*110)
print(df_comp[["Pendekatan_Model", "R2_Score", "MAE_USD", "Directional_Accuracy_Pct", "WinRate_Sniper_Pct", "PnL_Sniper_USD", "PnL_Pure75M_USD"]].to_string(index=False))
print(f"\nExport Excel Selesai ke:\n{excel_out}")
