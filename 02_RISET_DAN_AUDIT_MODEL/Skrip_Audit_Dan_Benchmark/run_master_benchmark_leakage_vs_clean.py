import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import MetaTrader5 as mt5
import yfinance as yf

print("="*105)
print("MASTER EXPERIMENT BENCHMARK SKRIPSI INFORMATIKA")
print("KOMPARASI HEAD-TO-HEAD: DENGAN KEBOCORAN (LEAKAGE) VS 100% BEBAS KEBOCORAN (CLEAN)")
print("4 ALGORITMA (LightGBM, XGBoost, Random Forest, Logistic Regression) x 2 VARIAN (Baseline vs Tuned)")
print("STANDAR RISET SKRIPSI: MODAL $500, LOT 0.01 ($1.0/point), SPREAD $0.20")
print("="*105)

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("MT5 Gagal Inisialisasi!")
    sys.exit(1)

symbol = "XAUUSDm" if mt5.symbol_info("XAUUSDm") else "XAUUSD"
print(f"Mengambil 25,000 candle historis {symbol} dari MT5...")
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
    print("Mengambil DXY dari Yahoo Finance...")
    dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
    dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
    if dxy_close.index.tz is not None:
        dxy_close.index = dxy_close.index.tz_localize(None)

mt5.shutdown()
print(f"Data M15 berhasil dimuat: {len(df_raw)} candle ({df_raw.index[0]} s/d {df_raw.index[-1]}).")

def extract_features(df_in, df_h1_in, df_h4_in, dxy_in, use_leakage=False):
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
    
    if use_leakage:
        # Rumus lama: shift(-2) mengintip 2 candle masa depan
        impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
        impulse_dn = (df['close'] - df['close'].shift(-2)) > (1.5 * (df['high'] - df['low']))
        df['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
        df['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)
    else:
        # Rumus kausal murni: shift(2) ke masa lalu
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

    h1_close_series = df_h1_loc['close'] if use_leakage else df_h1_loc['close'].shift(1)
    h4_close_series = df_h4_loc['close'] if use_leakage else df_h4_loc['close'].shift(1)
    
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

    features = [
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

    h = 5 # Horizon 75 Menit
    df['Target_Dir'] = (df['close'].shift(-h) > df['close']).astype(int)
    df_clean = df.dropna(subset=features + ['Target_Dir', 'ATR_14']).copy()

    split_idx = int(len(df_clean) * 0.80)
    # Purging boundary h lilin
    train_df = df_clean.iloc[:split_idx - h].copy()
    test_df  = df_clean.iloc[split_idx:].copy()

    return train_df, test_df, features

# ENGINE SIMULASI TRADING REALISTIS (MODAL $500, LOT 0.01, SPREAD $0.20)
def simulate_trading(test_df, probs, thresh=0.65, mode="sniper_rrr2"):
    LOT_SIZE = 0.01
    SPREAD = 0.20
    closes = test_df['close'].values
    highs  = test_df['high'].values
    lows   = test_df['low'].values
    atrs   = test_df['ATR_14'].values
    n = len(closes)
    
    trades = []
    active_until = -1
    max_bars = 30
    
    for i in range(n - max_bars):
        if i <= active_until:
            continue
            
        pb = probs[i]
        ps = 1.0 - pb
        conf = max(pb, ps)
        
        if conf < thresh:
            continue
            
        sig = 'BUY' if pb >= 0.5 else 'SELL'
        entry_p = closes[i]
        atr = atrs[i]
        
        # Konfigurasi Exit:
        if mode == "sniper_rrr2":
            # TP $12.00, SL $6.00 (RRR 1:2.0)
            tp_dist = 12.00
            sl_dist = 6.00
        elif mode == "adaptive_bab4":
            # AI Adaptive Sniper: Conf >= 65% -> TP $11, SL $6.50; Else -> TP $8.50, SL $6.50
            tp_dist = 11.00 if conf >= 0.65 else 8.50
            sl_dist = 6.50
        elif mode == "pure_75m":
            # Auto-Close tepat di lilin ke-5 (75 menit) tanpa TP/SL
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
                if h_bar >= tp_p:
                    outcome, pnl_gross, held_bars = "WIN", tp_dist, step
                    break
                if l_bar <= sl_p:
                    outcome, pnl_gross, held_bars = "LOSS", -sl_dist, step
                    break
            else:
                if l_bar <= tp_p:
                    outcome, pnl_gross, held_bars = "WIN", tp_dist, step
                    break
                if h_bar >= sl_p:
                    outcome, pnl_gross, held_bars = "LOSS", -sl_dist, step
                    break
                    
        if outcome == "TIMEOUT":
            exit_p = closes[min(i + max_bars, n - 1)]
            pnl_gross = (exit_p - entry_p) if sig == 'BUY' else (entry_p - exit_p)
            
        pnl_net = (pnl_gross * 1.0) - SPREAD
        trades.append(pnl_net)
        active_until = i + held_bars
        
    n_tr = len(trades)
    if n_tr == 0:
        return 0, 0.0, 0.0, 0.0, 0.0, 0.0
        
    wins = [p for p in trades if p > 0]
    losses = [p for p in trades if p <= 0]
    wr = (len(wins) / n_tr * 100) if n_tr > 0 else 0.0
    net_pnl = sum(trades)
    gw = sum(wins)
    gl = abs(sum(losses))
    pf = (gw / gl) if gl > 0 else 99.0
    
    eq = pd.Series(trades).cumsum()
    dd = (eq.cummax() - eq).max() if len(eq) > 0 else 0.0
    ev = net_pnl / n_tr if n_tr > 0 else 0.0
    
    return n_tr, wr, net_pnl, pf, dd, ev

# DAFTAR 8 MODEL (4 ALGORITMA x 2 VARIAN)
def get_models():
    return {
        # 1. LIGHTGBM
        ("LightGBM", "Baseline"): LGBMClassifier(random_state=42, verbose=-1),
        ("LightGBM", "Tuned v4.2"): LGBMClassifier(
            n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
            min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
            reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced',
            random_state=42, n_jobs=-1, verbose=-1
        ),
        
        # 2. XGBOOST
        ("XGBoost", "Baseline"): XGBClassifier(random_state=42, eval_metric='logloss'),
        ("XGBoost", "Tuned"): XGBClassifier(
            n_estimators=400, learning_rate=0.02, max_depth=5,
            subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0,
            random_state=42, eval_metric='logloss'
        ),
        
        # 3. RANDOM FOREST
        ("Random Forest", "Baseline"): RandomForestClassifier(random_state=42, n_jobs=-1),
        ("Random Forest", "Tuned"): RandomForestClassifier(
            n_estimators=250, max_depth=10, min_samples_split=10, min_samples_leaf=4,
            max_features='sqrt', random_state=42, n_jobs=-1
        ),
        
        # 4. LOGISTIC REGRESSION
        ("Logistic Regression", "Baseline"): make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
        ("Logistic Regression", "Tuned"): make_pipeline(StandardScaler(), LogisticRegression(C=0.01, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42))
    }

master_records = []

for env_name, is_leaking in [("DENGAN LEAKAGE shift(-2)", True), ("100% BEBAS LEAKAGE (Clean)", False)]:
    print(f"\n{'='*45} MEMULAI EVALUASI: {env_name.upper()} {'='*45}")
    train_df, test_df, features_57 = extract_features(df_raw, df_h1, df_h4, dxy_close, use_leakage=is_leaking)
    
    X_train = train_df[features_57]
    y_train = train_df['Target_Dir']
    X_test  = test_df[features_57]
    y_test  = test_df['Target_Dir']
    
    print(f"Data: Train={len(X_train)} bar, Test={len(X_test)} bar ({test_df.index[0]} s/d {test_df.index[-1]})")
    
    models_dict = get_models()
    
    for (algo, variant), clf in models_dict.items():
        t0 = time.time()
        clf.fit(X_train, y_train)
        dur = time.time() - t0
        
        probs = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else clf.predict(X_test)
        preds = (probs >= 0.5).astype(int)
        conf = np.maximum(probs, 1.0 - probs)
        
        # 1. Metrik ML Global
        acc_global = accuracy_score(y_test, preds) * 100
        auc_score = roc_auc_score(y_test, probs) * 100
        f1 = f1_score(y_test, preds, zero_division=0) * 100
        
        # 2. Metrik ML Ambang Batas 65% (Sniper)
        mask65 = conf >= 0.65
        n65 = mask65.sum()
        acc65 = (accuracy_score(y_test[mask65], (probs[mask65] >= 0.5).astype(int)) * 100) if n65 > 0 else 0.0
        
        # 3. Simulasi Trading Realistis (Fixed Sniper RRR 1:2: TP $12, SL $6)
        tr_n, tr_wr, tr_pnl, tr_pf, tr_dd, tr_ev = simulate_trading(test_df, probs, thresh=0.65, mode="sniper_rrr2")
        
        # 4. Simulasi Trading Auto-Close 75m
        _, _, pnl_75m, pf_75m, _, _ = simulate_trading(test_df, probs, thresh=0.65, mode="pure_75m")
        
        print(f"[{algo} - {variant}] Acc_50={acc_global:.2f}% | AUC={auc_score:.2f}% | Acc_65={acc65:.2f}% ({n65} sig) | RRR1:2 PnL=${tr_pnl:+,.2f} (WR {tr_wr:.1f}%, PF {tr_pf:.2f}) | 75m PnL=${pnl_75m:+,.2f}")
        
        master_records.append({
            'Environment': env_name,
            'Integritas_Data': 'Terkontaminasi Leakage' if is_leaking else '100% Bebas Leakage (Clean)',
            'Algoritma': algo,
            'Varian': variant,
            'Akurasi_Global_50%': acc_global,
            'ROC_AUC_%': auc_score,
            'F1_Score_%': f1,
            'Akurasi_Sniper_65%': acc65,
            'Sinyal_Sniper_65%': n65,
            'Trades_Realistis_RRR2': tr_n,
            'WinRate_Trading_%': tr_wr,
            'Net_PnL_Realistis ($)': tr_pnl,
            'Profit_Factor_RRR2': tr_pf,
            'Max_Drawdown ($)': tr_dd,
            'EV_per_Trade ($)': tr_ev,
            'Net_PnL_AutoClose_75m ($)': pnl_75m,
            'Profit_Factor_75m': pf_75m,
            'Waktu_Latih_s': round(dur, 2)
        })

df_master = pd.DataFrame(master_records)

print("\n" + "="*125)
print("TABEL RINGKASAN MASTER BENCHMARK: LEAKAGE VS CLEAN (SEMUA MODEL BASELINE & TUNED)")
print("="*125)
cols_view = ['Environment', 'Algoritma', 'Varian', 'Akurasi_Sniper_65%', 'Sinyal_Sniper_65%', 'WinRate_Trading_%', 'Net_PnL_Realistis ($)', 'Profit_Factor_RRR2', 'Max_Drawdown ($)', 'Net_PnL_AutoClose_75m ($)']
print(df_master[cols_view].to_string(index=False))

out_excel = r"03_DATA_DAN_HASIL_EVALUASI\Hasil_Eksperimen_Excel\Hasil_Master_Komparasi_Leakage_vs_Clean_All_Models.xlsx"
df_master.to_excel(out_excel, index=False)
print(f"\n✅ Berkas Master Komparasi berhasil disimpan ke: {out_excel}")
