"""
==========================================================================
🔬 EVALUASI LAYER 2: IDEAL EXECUTION TEST (MODEL + DIRECT ENTRY BACKTEST)
==========================================================================
Tujuan: Simulasi backtest jika bot LANGSUNG entry saat model memberi sinyal.
        TANPA candle confirmation, TANPA H1 filter, TANPA structure check.
        Hanya: Model Signal + ATR-based SL/TP + RRR.

Pertanyaan yang dijawab:
  "Jika bot langsung eksekusi setiap sinyal model, apakah profitable?"

Output:
  - Win Rate, Profit Factor, Expectancy per Trade
  - Max Drawdown, Sharpe Ratio
  - Equity Curve
  - Perbandingan langsung dengan Layer 3 (forward testing aktual)
  - Export ke Excel untuk lampiran skripsi
==========================================================================
"""

import os
import sys
import joblib
import pandas as pd
import numpy as np
import MetaTrader5 as mt5
import yfinance as yf
from datetime import datetime

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# =========================================================================
# KONFIGURASI
# =========================================================================
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_M15_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"
MODEL_M5_PATH  = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd_m5.pkl"
OUTPUT_EXCEL   = r"d:\SKRIPSI INFORMATIKA\Hasil_Evaluasi_Ideal_Execution.xlsx"

# Excel forward testing aktual (Layer 3) untuk perbandingan
LAYER3_EXCEL_M15 = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx"
LAYER3_EXCEL_M5  = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_M5_Scalping.xlsx"

# Trading Parameters (identik dengan bot asli)
LOT_SIZE = 0.01
SPREAD_COST_USD = 0.35  # Estimasi spread XAUUSD per 0.01 lot (3.5 pips × $0.10)

# RRR Configurations untuk pengujian
RRR_CONFIGS = {
    'M15': [
        {'name': 'RRR 1:1.5', 'rrr': 1.5, 'atr_sl_mult': 1.5},
        {'name': 'RRR 1:2.0', 'rrr': 2.0, 'atr_sl_mult': 1.5},
        {'name': 'RRR 1:2.5', 'rrr': 2.5, 'atr_sl_mult': 1.5},
        {'name': 'RRR 1:3.0', 'rrr': 3.0, 'atr_sl_mult': 1.5},
    ],
    'M5': [
        {'name': 'RRR 1:1.5', 'rrr': 1.5, 'atr_sl_mult': 1.2},
        {'name': 'RRR 1:2.0', 'rrr': 2.0, 'atr_sl_mult': 1.2},
        {'name': 'RRR 1:2.5', 'rrr': 2.5, 'atr_sl_mult': 1.2},
    ],
}

FORWARD_CANDLES_M15 = 5
FORWARD_CANDLES_M5  = 5
EVAL_CANDLES_M15 = 8640   # ~3 bulan
EVAL_CANDLES_M5  = 25920  # ~3 bulan

# Probability thresholds untuk diuji
PROB_THRESHOLDS = [0.50, 0.55, 0.58, 0.60, 0.65, 0.70]

FEATURES = [
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
    'Trend_H4_Bull', 'Trend_H4_Strong'
]


def init_mt5():
    if not os.path.exists(MT5_PATH):
        print("❌ MT5 Path tidak ditemukan!")
        sys.exit(1)
    if not mt5.initialize(path=MT5_PATH):
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)
    print("✅ Terhubung ke MT5.")


def get_symbol():
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)
    return symbol


def build_features(df_tf, df_h1, df_h4, dxy_close, tf_label="M15"):
    """Bangun fitur identik dengan training (copy dari Layer 1)."""
    df = df_tf.copy()

    range_hl = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_hl
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_hl
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_hl

    df['FVG_Bull'] = (df['low'] > df['high'].shift(2)).astype(int)
    df['FVG_Bear'] = (df['high'] < df['low'].shift(2)).astype(int)
    df['Swing_High_20'] = df['high'].shift(1).rolling(20).max()
    df['Swing_Low_20']  = df['low'].shift(1).rolling(20).min()
    df['Dist_Support']    = (df['close'] - df['Swing_Low_20']) / df['close']
    df['Dist_Resistance'] = (df['Swing_High_20'] - df['close']) / df['close']
    df['BOS_Bull'] = (df['close'] > df['Swing_High_20']).astype(int)
    df['BOS_Bear'] = (df['close'] < df['Swing_Low_20']).astype(int)
    trend_slow = df['close'].pct_change(20)
    df['CHoCH_Bull'] = ((df['close'] > df['Swing_High_20']) & (trend_slow < 0)).astype(int)
    df['CHoCH_Bear'] = ((df['close'] < df['Swing_Low_20']) & (trend_slow > 0)).astype(int)
    df['Liquidity_Sweep_High'] = ((df['high'] > df['Swing_High_20']) & (df['close'] < df['Swing_High_20'])).astype(int)
    df['Liquidity_Sweep_Low']  = ((df['low'] < df['Swing_Low_20']) & (df['close'] > df['Swing_Low_20'])).astype(int)
    is_bear_c = df['close'] < df['open']
    is_bull_c = df['close'] > df['open']
    impulse_up = (df['close'].shift(-2) - df['close']) > (1.5 * (df['high'] - df['low']))
    impulse_dn = (df['close'] - df['close'].shift(-2)) > (1.5 * (df['high'] - df['low']))
    df['Order_Block_Bull'] = (is_bear_c & impulse_up).astype(int)
    df['Order_Block_Bear'] = (is_bull_c & impulse_dn).astype(int)

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

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI_14'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['STD_20'] = df['close'].rolling(20).std()
    df['BB_Bandwidth'] = (4 * df['STD_20']) / df['SMA_20']
    df['BB_Pos'] = (df['close'] - (df['SMA_20'] - 2*df['STD_20'])) / (4*df['STD_20'] + 1e-6)
    df['XAU_Return_1'] = df['close'].pct_change(1)
    df['XAU_Return_3'] = df['close'].pct_change(3)
    df['XAU_Return_5'] = df['close'].pct_change(5)

    df['DXY_Close'] = dxy_close.reindex(df.index, method='ffill').bfill()
    df['DXY_Return_1'] = df['DXY_Close'].pct_change(1).fillna(0)
    df['DXY_Return_3'] = df['DXY_Close'].pct_change(3).fillna(0)
    df['DXY_Trend'] = (df['DXY_Close'] > df['DXY_Close'].rolling(20).mean()).astype(int)
    df['XAU_DXY_Ratio_Return'] = (df['close'] / df['DXY_Close']).pct_change(1).fillna(0)

    dates = df.index
    df['Is_NFP_Week'] = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
    df['Is_CPI_Day']  = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    df['Is_FOMC_Week'] = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)

    df_h1_c = df_h1.copy()
    df_h1_c['EMA_50_H1']  = df_h1_c['close'].ewm(span=50, adjust=False).mean()
    df_h1_c['EMA_200_H1'] = df_h1_c['close'].ewm(span=200, adjust=False).mean()
    df_h1_c['Trend_H1_Bull']   = (df_h1_c['close'] > df_h1_c['EMA_50_H1']).astype(int)
    df_h1_c['Trend_H1_Strong'] = (df_h1_c['EMA_50_H1'] > df_h1_c['EMA_200_H1']).astype(int)
    df['Trend_H1_Bull']   = df_h1_c['Trend_H1_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H1_Strong'] = df_h1_c['Trend_H1_Strong'].reindex(df.index, method='ffill').fillna(0)

    df_h4_c = df_h4.copy()
    df_h4_c['EMA_50_H4']  = df_h4_c['close'].ewm(span=50, adjust=False).mean()
    df_h4_c['EMA_200_H4'] = df_h4_c['close'].ewm(span=200, adjust=False).mean()
    df_h4_c['Trend_H4_Bull']   = (df_h4_c['close'] > df_h4_c['EMA_50_H4']).astype(int)
    df_h4_c['Trend_H4_Strong'] = (df_h4_c['EMA_50_H4'] > df_h4_c['EMA_200_H4']).astype(int)
    df['Trend_H4_Bull']   = df_h4_c['Trend_H4_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H4_Strong'] = df_h4_c['Trend_H4_Strong'].reindex(df.index, method='ffill').fillna(0)

    # ATR untuk dynamic SL
    df['ATR_14'] = df['high'].sub(df['low']).rolling(14).mean()

    return df


def simulate_trades(df, model, features, tf_label, eval_candles, prob_threshold, rrr_config):
    """
    Simulasi backtest per-candle:
    - Setiap candle: cek prediksi model
    - Jika probabilitas >= threshold → entry di close candle saat ini
    - SL = ATR × multiplier, TP = SL × RRR
    - Cek apakah dalam FORWARD_CANDLES berikutnya harga menyentuh TP atau SL duluan
    - Tidak boleh ada 2 posisi bersamaan (1 trade at a time)
    """
    fwd = FORWARD_CANDLES_M15 if tf_label == "M15" else FORWARD_CANDLES_M5
    rrr = rrr_config['rrr']
    atr_mult = rrr_config['atr_sl_mult']

    df_eval = df.tail(eval_candles + 200).copy()
    df_clean = df_eval[features + ['ATR_14', 'close', 'high', 'low']].dropna().copy()
    df_clean[features] = df_clean[features].astype(float)

    if len(df_clean) < fwd + 10:
        return None

    # Generate predictions for all candles
    X = df_clean[features].values
    probs = model.predict_proba(X)
    prob_buy  = probs[:, 1]
    prob_sell = probs[:, 0]
    prob_max  = np.maximum(prob_buy, prob_sell)

    closes = df_clean['close'].values
    highs  = df_clean['high'].values
    lows   = df_clean['low'].values
    atrs   = df_clean['ATR_14'].values
    times  = df_clean.index

    trades = []
    i = 0
    in_trade_until = 0  # Index setelah trade selesai

    while i < len(df_clean) - fwd:
        if i < in_trade_until:
            i += 1
            continue

        p_buy  = prob_buy[i]
        p_sell = prob_sell[i]
        p_max_i = prob_max[i]

        if p_max_i < prob_threshold:
            i += 1
            continue

        # Tentukan arah
        direction = "BUY" if p_buy >= p_sell else "SELL"
        entry_price = closes[i]
        atr = atrs[i]

        if atr < 0.5:  # ATR terlalu kecil, skip
            i += 1
            continue

        sl_distance = atr * atr_mult
        tp_distance = sl_distance * rrr

        if direction == "BUY":
            sl_price = entry_price - sl_distance
            tp_price = entry_price + tp_distance
        else:
            sl_price = entry_price + sl_distance
            tp_price = entry_price - tp_distance

        # Simulasi: cek candle-candle berikutnya
        result = "TIMEOUT"
        exit_price = closes[min(i + fwd, len(closes) - 1)]
        exit_candle = fwd

        for j in range(1, fwd + 1):
            idx = i + j
            if idx >= len(df_clean):
                break

            h = highs[idx]
            l = lows[idx]

            if direction == "BUY":
                if l <= sl_price:
                    result = "SL"
                    exit_price = sl_price
                    exit_candle = j
                    break
                elif h >= tp_price:
                    result = "TP"
                    exit_price = tp_price
                    exit_candle = j
                    break
            else:  # SELL
                if h >= sl_price:
                    result = "SL"
                    exit_price = sl_price
                    exit_candle = j
                    break
                elif l <= tp_price:
                    result = "TP"
                    exit_price = tp_price
                    exit_candle = j
                    break

        # Hitung profit
        if direction == "BUY":
            profit_pips = exit_price - entry_price
        else:
            profit_pips = entry_price - exit_price

        profit_usd = profit_pips * LOT_SIZE * 100 - SPREAD_COST_USD

        trades.append({
            'time': str(times[i]),
            'direction': direction,
            'probability': float(p_max_i * 100),
            'entry_price': float(entry_price),
            'sl_price': float(sl_price),
            'tp_price': float(tp_price),
            'sl_distance': float(sl_distance),
            'tp_distance': float(tp_distance),
            'exit_price': float(exit_price),
            'result': result,
            'exit_candle': exit_candle,
            'profit_usd': float(profit_usd),
            'atr': float(atr),
        })

        in_trade_until = i + exit_candle + 1
        i += 1

    return trades


def analyze_trades(trades, tf_label, rrr_name, prob_threshold):
    """Analisis hasil trade dan hitung metrik trading."""
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    total = len(df_trades)
    wins = len(df_trades[df_trades['profit_usd'] > 0])
    losses = len(df_trades[df_trades['profit_usd'] <= 0])
    win_rate = wins / total * 100 if total > 0 else 0

    total_profit = df_trades[df_trades['profit_usd'] > 0]['profit_usd'].sum()
    total_loss = abs(df_trades[df_trades['profit_usd'] <= 0]['profit_usd'].sum())
    profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

    net_pnl = df_trades['profit_usd'].sum()
    expectancy = net_pnl / total if total > 0 else 0

    # Equity curve & drawdown
    equity_curve = df_trades['profit_usd'].cumsum()
    peak = equity_curve.cummax()
    drawdown = equity_curve - peak
    max_drawdown = drawdown.min()

    # Sharpe Ratio (daily approximation)
    returns = df_trades['profit_usd'].values
    if len(returns) > 1 and np.std(returns) > 0:
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)  # Annualized
    else:
        sharpe = 0

    # TP/SL/Timeout breakdown
    tp_count = len(df_trades[df_trades['result'] == 'TP'])
    sl_count = len(df_trades[df_trades['result'] == 'SL'])
    timeout_count = len(df_trades[df_trades['result'] == 'TIMEOUT'])

    avg_win = total_profit / wins if wins > 0 else 0
    avg_loss = total_loss / losses if losses > 0 else 0

    return {
        'tf': tf_label,
        'rrr_name': rrr_name,
        'prob_threshold': f"≥{prob_threshold*100:.0f}%",
        'total_trades': total,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_pnl': net_pnl,
        'expectancy': expectancy,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe,
        'tp_count': tp_count,
        'sl_count': sl_count,
        'timeout_count': timeout_count,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'equity_curve': equity_curve.values.tolist(),
        'df_trades': df_trades,
    }


def print_results(result):
    """Print hasil analisis single configuration."""
    if result is None:
        return

    pf_str = f"{result['profit_factor']:.2f}" if result['profit_factor'] != float('inf') else "∞"
    status = "✅ PROFIT" if result['net_pnl'] > 0 else "❌ RUGI"

    print(f"\n   {'─'*55}")
    print(f"   📊 {result['tf']} | {result['rrr_name']} | Threshold {result['prob_threshold']}")
    print(f"   {'─'*55}")
    print(f"   Total Trade    : {result['total_trades']}")
    print(f"   Win / Loss     : {result['wins']} / {result['losses']}  (WR: {result['win_rate']:.1f}%)")
    print(f"   TP / SL / Tout : {result['tp_count']} / {result['sl_count']} / {result['timeout_count']}")
    print(f"   Net P&L        : ${result['net_pnl']:+.2f} {status}")
    print(f"   Profit Factor  : {pf_str}")
    print(f"   Expectancy     : ${result['expectancy']:+.2f}/trade")
    print(f"   Max Drawdown   : ${result['max_drawdown']:.2f}")
    print(f"   Sharpe Ratio   : {result['sharpe_ratio']:.2f}")
    print(f"   Avg Win / Loss : ${result['avg_win']:.2f} / ${result['avg_loss']:.2f}")


def export_all_results(all_results):
    """Export semua konfigurasi ke Excel."""
    print(f"\n{'='*70}")
    print(f"💾 MENYIMPAN KE EXCEL: {OUTPUT_EXCEL}")
    print(f"{'='*70}")

    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:

        # Summary comparison table
        summary_rows = []
        for r in all_results:
            if r is None:
                continue
            pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
            summary_rows.append({
                'Timeframe': r['tf'],
                'RRR': r['rrr_name'],
                'Threshold': r['prob_threshold'],
                'Total_Trade': r['total_trades'],
                'Win_Rate': f"{r['win_rate']:.1f}%",
                'Net_PnL': f"${r['net_pnl']:+.2f}",
                'Profit_Factor': pf_str,
                'Expectancy': f"${r['expectancy']:+.2f}",
                'Max_Drawdown': f"${r['max_drawdown']:.2f}",
                'Sharpe_Ratio': f"{r['sharpe_ratio']:.2f}",
                'Avg_Win': f"${r['avg_win']:.2f}",
                'Avg_Loss': f"${r['avg_loss']:.2f}",
            })

        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Perbandingan Semua', index=False)

        # Individual trade logs for best configs
        for r in all_results:
            if r is None or r['df_trades'] is None:
                continue
            sheet_name = f"{r['tf']}_{r['rrr_name']}_{r['prob_threshold']}"
            # Truncate sheet name to 31 chars (Excel limit)
            sheet_name = sheet_name[:31].replace('≥', 'min').replace('%', 'p')
            try:
                r['df_trades'].to_excel(writer, sheet_name=sheet_name, index=False)
            except Exception:
                pass

    print(f"✅ Berhasil disimpan: {OUTPUT_EXCEL}")


def main():
    print("="*85)
    print("🔬 EVALUASI LAYER 2: IDEAL EXECUTION TEST (MODEL + DIRECT ENTRY BACKTEST)")
    print("   Simulasi: Jika bot LANGSUNG entry di sinyal model, berapa profitnya?")
    print("="*85)

    init_mt5()
    symbol = get_symbol()

    # Load models
    print(f"\n📦 Memuat model...")
    model_m15 = joblib.load(MODEL_M15_PATH)
    model_m5  = joblib.load(MODEL_M5_PATH)
    print(f"   ✅ Model M15 & M5 dimuat.")

    # Download data
    print(f"\n📥 Mengambil data dari MT5 ({symbol})...")
    rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50000)
    rates_m5  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5,  0, 50000)
    rates_h1  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1,  0, 10000)
    rates_h4  = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4,  0, 5000)

    for name, data in [("M15", rates_m15), ("M5", rates_m5), ("H1", rates_h1), ("H4", rates_h4)]:
        if data is None or len(data) == 0:
            print(f"❌ Gagal ambil data {name}!")
            mt5.shutdown()
            sys.exit(1)

    df_m15 = pd.DataFrame(rates_m15); df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s'); df_m15.set_index('time', inplace=True)
    df_m5  = pd.DataFrame(rates_m5);  df_m5['time']  = pd.to_datetime(df_m5['time'], unit='s');  df_m5.set_index('time', inplace=True)
    df_h1  = pd.DataFrame(rates_h1);  df_h1['time']  = pd.to_datetime(df_h1['time'], unit='s');  df_h1.set_index('time', inplace=True)
    df_h4  = pd.DataFrame(rates_h4);  df_h4['time']  = pd.to_datetime(df_h4['time'], unit='s');  df_h4.set_index('time', inplace=True)

    # DXY
    mt5.symbol_select('DXY', True)
    rates_dxy_m15 = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 50000)
    rates_dxy_m5  = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M5, 0, 50000)

    if rates_dxy_m15 is not None and len(rates_dxy_m15) > 0:
        df_dxy = pd.DataFrame(rates_dxy_m15); df_dxy['time'] = pd.to_datetime(df_dxy['time'], unit='s'); df_dxy.set_index('time', inplace=True)
        dxy_close_m15 = df_dxy['close']
    else:
        dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
        dxy_close_m15 = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
        if dxy_close_m15.index.tz is not None: dxy_close_m15.index = dxy_close_m15.index.tz_localize(None)

    if rates_dxy_m5 is not None and len(rates_dxy_m5) > 0:
        df_dxy_m5 = pd.DataFrame(rates_dxy_m5); df_dxy_m5['time'] = pd.to_datetime(df_dxy_m5['time'], unit='s'); df_dxy_m5.set_index('time', inplace=True)
        dxy_close_m5 = df_dxy_m5['close']
    else:
        dxy_close_m5 = dxy_close_m15.copy()

    print(f"   ✅ Data siap: M15={len(df_m15):,} | M5={len(df_m5):,}")

    # Build features
    print("\n⚙️ Membangun fitur...")
    df_m15_feat = build_features(df_m15, df_h1, df_h4, dxy_close_m15, "M15")
    df_m5_feat  = build_features(df_m5,  df_h1, df_h4, dxy_close_m5,  "M5")

    # Run all simulations
    all_results = []

    for tf_label, model, df_feat, eval_candles in [
        ("M15", model_m15, df_m15_feat, EVAL_CANDLES_M15),
        ("M5",  model_m5,  df_m5_feat,  EVAL_CANDLES_M5),
    ]:
        print(f"\n{'='*70}")
        print(f"🔄 SIMULASI BACKTEST — {tf_label}")
        print(f"{'='*70}")

        configs = RRR_CONFIGS[tf_label]

        for rrr_config in configs:
            for prob_th in PROB_THRESHOLDS:
                trades = simulate_trades(df_feat, model, FEATURES, tf_label, eval_candles, prob_th, rrr_config)
                if trades:
                    result = analyze_trades(trades, tf_label, rrr_config['name'], prob_th)
                    if result:
                        print_results(result)
                        all_results.append(result)
                else:
                    print(f"   ⚠️ Tidak ada trade: {tf_label} {rrr_config['name']} ≥{prob_th*100:.0f}%")

    # Export
    export_all_results(all_results)

    # --- Kesimpulan ---
    print(f"\n{'='*70}")
    print(f"📋 KESIMPULAN LAYER 2 — IDEAL EXECUTION TEST")
    print(f"{'='*70}")

    if all_results:
        # Find best configuration per timeframe
        for tf in ["M15", "M5"]:
            tf_results = [r for r in all_results if r['tf'] == tf and r['total_trades'] >= 10]
            if tf_results:
                best = max(tf_results, key=lambda x: x['net_pnl'])
                worst = min(tf_results, key=lambda x: x['net_pnl'])
                print(f"\n   {tf} TERBAIK: {best['rrr_name']} @ {best['prob_threshold']}")
                print(f"      → Net PnL: ${best['net_pnl']:+.2f} | WR: {best['win_rate']:.1f}% | PF: {best['profit_factor']:.2f}")
                print(f"   {tf} TERBURUK: {worst['rrr_name']} @ {worst['prob_threshold']}")
                print(f"      → Net PnL: ${worst['net_pnl']:+.2f} | WR: {worst['win_rate']:.1f}% | PF: {worst['profit_factor']:.2f}")

    print(f"\n   📝 Bandingkan hasil ini dengan Layer 3 (Forward Testing Excel)")
    print(f"      M15: {LAYER3_EXCEL_M15}")
    print(f"      M5:  {LAYER3_EXCEL_M5}")
    print(f"   Jika Layer 2 >> Layer 3: Filter bot merusak performa → kurangi filter!")
    print(f"   Jika Layer 2 ≈ Layer 3: Filter seimbang, model yang perlu diperbaiki.")

    mt5.shutdown()
    print(f"\n{'='*70}")
    print("🏁 EVALUASI LAYER 2 SELESAI.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
