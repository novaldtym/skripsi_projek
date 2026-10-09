"""
==========================================================================
🔬 EVALUASI LAYER 1: PURE MODEL ACCURACY (SIGNAL-ONLY TEST)
==========================================================================
Tujuan: Mengukur akurasi MURNI prediksi arah model LightGBM,
        TANPA filter bot, TANPA SL/TP, TANPA eksekusi.

Pertanyaan yang dijawab:
  "Apakah model LightGBM benar-benar bisa memprediksi arah harga?"

Output:
  - Directional Accuracy (Hit Rate)
  - ROC-AUC, Precision, Recall, F1-Score
  - Confusion Matrix
  - Hit Rate per Threshold (55%, 60%, 65%, 70%, 75%)
  - Analisis per Jam (kapan model paling akurat?)
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
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

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
OUTPUT_EXCEL   = r"d:\SKRIPSI INFORMATIKA\Hasil_Evaluasi_Pure_Model_Accuracy.xlsx"

FORWARD_CANDLES_M15 = 5   # Horizon 75 menit
FORWARD_CANDLES_M5  = 5   # Horizon 25 menit

# Hanya evaluasi 3 bulan terakhir (Out-of-Sample)
EVAL_CANDLES_M15 = 8640   # ~3 bulan M15 (96 candle/hari × 90 hari)
EVAL_CANDLES_M5  = 25920  # ~3 bulan M5 (288 candle/hari × 90 hari)

FEATURES_M15 = [
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

# M5 memiliki fitur yang sama (36 fitur, tapi model dilatih dengan 36 fitur)
FEATURES_M5 = FEATURES_M15.copy()


def init_mt5():
    """Inisialisasi koneksi MT5."""
    if not os.path.exists(MT5_PATH):
        print("❌ MT5 Path tidak ditemukan!")
        sys.exit(1)
    if not mt5.initialize(path=MT5_PATH):
        print("❌ Gagal terhubung ke MT5!")
        sys.exit(1)
    print("✅ Terhubung ke MT5.")


def get_symbol():
    """Ambil nama simbol XAUUSD yang aktif."""
    symbol = "XAUUSD"
    if mt5.symbol_info(symbol) is None:
        symbol = "XAUUSDm"
    mt5.symbol_select(symbol, True)
    return symbol


def build_features(df_tf, df_h1, df_h4, dxy_close, tf_label="M15"):
    """
    Bangun fitur-fitur yang identik dengan training.
    Menerima DataFrame timeframe utama + H1, H4, DXY.
    """
    df = df_tf.copy()

    # 1. Geometri Candlestick
    range_hl = (df['high'] - df['low']) + 1e-6
    df['Body_Ratio']       = (df['close'] - df['open']).abs() / range_hl
    df['Lower_Wick_Ratio'] = (df[['open', 'close']].min(axis=1) - df['low']) / range_hl
    df['Upper_Wick_Ratio'] = (df['high'] - df[['open', 'close']].max(axis=1)) / range_hl

    # 2. Smart Money Concepts (SMC / ICT)
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

    # 3. Fibonacci Retracement
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

    # 4. Momentum & Volatilitas
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

    # 5. DXY Intermarket & Makroekonomi
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

    # 6. Multi-Timeframe Trend H1 & H4
    df_h1_copy = df_h1.copy()
    df_h1_copy['EMA_50_H1']  = df_h1_copy['close'].ewm(span=50, adjust=False).mean()
    df_h1_copy['EMA_200_H1'] = df_h1_copy['close'].ewm(span=200, adjust=False).mean()
    df_h1_copy['Trend_H1_Bull']   = (df_h1_copy['close'] > df_h1_copy['EMA_50_H1']).astype(int)
    df_h1_copy['Trend_H1_Strong'] = (df_h1_copy['EMA_50_H1'] > df_h1_copy['EMA_200_H1']).astype(int)
    df['Trend_H1_Bull']   = df_h1_copy['Trend_H1_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H1_Strong'] = df_h1_copy['Trend_H1_Strong'].reindex(df.index, method='ffill').fillna(0)

    df_h4_copy = df_h4.copy()
    df_h4_copy['EMA_50_H4']  = df_h4_copy['close'].ewm(span=50, adjust=False).mean()
    df_h4_copy['EMA_200_H4'] = df_h4_copy['close'].ewm(span=200, adjust=False).mean()
    df_h4_copy['Trend_H4_Bull']   = (df_h4_copy['close'] > df_h4_copy['EMA_50_H4']).astype(int)
    df_h4_copy['Trend_H4_Strong'] = (df_h4_copy['EMA_50_H4'] > df_h4_copy['EMA_200_H4']).astype(int)
    df['Trend_H4_Bull']   = df_h4_copy['Trend_H4_Bull'].reindex(df.index, method='ffill').fillna(0)
    df['Trend_H4_Strong'] = df_h4_copy['Trend_H4_Strong'].reindex(df.index, method='ffill').fillna(0)

    # Target: Arah harga di t + FORWARD_CANDLES
    fwd = FORWARD_CANDLES_M15 if tf_label == "M15" else FORWARD_CANDLES_M5
    df['Target_Future'] = df['close'].shift(-fwd)
    df['Target_Dir'] = (df['Target_Future'] > df['close']).astype(int)
    df['Price_Change'] = df['Target_Future'] - df['close']

    return df


def evaluate_model(model, df, features, tf_label, eval_candles):
    """
    Evaluasi MURNI: prediksi model vs arah aktual.
    Return dictionary berisi semua metrik.
    """
    print(f"\n{'='*70}")
    print(f"🔬 EVALUASI PURE MODEL ACCURACY — {tf_label}")
    print(f"{'='*70}")

    # Ambil hanya data evaluasi (N candle terakhir)
    df_eval = df.tail(eval_candles + 10).copy()  # +10 buffer untuk NaN
    df_clean = df_eval[features + ['Target_Dir', 'Price_Change']].dropna().copy()
    df_clean[features] = df_clean[features].astype(float)

    if len(df_clean) == 0:
        print("❌ Tidak ada data bersih untuk evaluasi!")
        return None

    X = df_clean[features]
    y_true = df_clean['Target_Dir'].values
    price_change = df_clean['Price_Change'].values

    # Prediksi
    y_prob = model.predict_proba(X)
    prob_buy = y_prob[:, 1]   # Probabilitas naik
    prob_sell = y_prob[:, 0]  # Probabilitas turun
    prob_max = np.maximum(prob_buy, prob_sell)
    y_pred = (prob_buy >= 0.5).astype(int)

    # --- Metrik Utama ---
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, prob_buy)
    cm = confusion_matrix(y_true, y_pred)

    print(f"\n📊 Periode Evaluasi: {df_clean.index[0]} s/d {df_clean.index[-1]}")
    print(f"   Total Candle Dievaluasi: {len(df_clean):,}")
    print(f"\n{'─'*50}")
    print(f"📈 METRIK KESELURUHAN:")
    print(f"{'─'*50}")
    print(f"   Directional Accuracy : {acc*100:.2f}%")
    print(f"   Precision (BUY)      : {prec*100:.2f}%")
    print(f"   Recall (BUY)         : {rec*100:.2f}%")
    print(f"   F1-Score             : {f1*100:.2f}%")
    print(f"   ROC-AUC              : {auc:.4f}")
    print(f"\n   Confusion Matrix:")
    print(f"              Pred SELL  Pred BUY")
    print(f"   Act SELL:  {cm[0][0]:>8}  {cm[0][1]:>8}")
    print(f"   Act BUY:   {cm[1][0]:>8}  {cm[1][1]:>8}")

    # --- Hit Rate per Threshold ---
    print(f"\n{'─'*50}")
    print(f"🎯 HIT RATE PER THRESHOLD KEYAKINAN:")
    print(f"{'─'*50}")

    threshold_results = []
    for th in [0.52, 0.55, 0.58, 0.60, 0.63, 0.65, 0.68, 0.70, 0.75]:
        mask = prob_max >= th
        if mask.sum() > 0:
            y_pred_th = (prob_buy[mask] >= 0.5).astype(int)
            y_true_th = y_true[mask]
            acc_th = accuracy_score(y_true_th, y_pred_th)
            coverage = mask.sum() / len(y_true) * 100
            avg_change = np.mean(np.abs(price_change[mask]))
            print(f"   ≥{th*100:>5.0f}%: Akurasi={acc_th*100:.1f}%  |  Sinyal={mask.sum():>5}/{len(y_true)}  |  Coverage={coverage:.1f}%  |  Avg |ΔP|=${avg_change:.2f}")
            threshold_results.append({
                'Threshold': f"≥{th*100:.0f}%",
                'Akurasi': f"{acc_th*100:.2f}%",
                'Jumlah_Sinyal': int(mask.sum()),
                'Total_Candle': len(y_true),
                'Coverage': f"{coverage:.1f}%",
                'Avg_Price_Change': f"${avg_change:.2f}"
            })
        else:
            print(f"   ≥{th*100:>5.0f}%: Tidak ada sinyal")

    # --- Analisis per Jam ---
    print(f"\n{'─'*50}")
    print(f"⏰ AKURASI PER JAM (Jam Server MT5):")
    print(f"{'─'*50}")

    hours = df_clean.index.hour
    hourly_results = []
    for h in sorted(hours.unique()):
        mask_h = hours == h
        if mask_h.sum() >= 20:  # Minimal 20 sampel
            acc_h = accuracy_score(y_true[mask_h], y_pred[mask_h])
            avg_prob = np.mean(prob_max[mask_h])
            emoji = "🟢" if acc_h > 0.55 else ("🟡" if acc_h > 0.50 else "🔴")
            print(f"   {emoji} Jam {h:02d}:00 — Akurasi: {acc_h*100:.1f}%  |  Avg Prob: {avg_prob*100:.1f}%  |  N={mask_h.sum()}")
            hourly_results.append({
                'Jam': f"{h:02d}:00",
                'Akurasi': f"{acc_h*100:.2f}%",
                'Avg_Prob': f"{avg_prob*100:.1f}%",
                'Jumlah_Sampel': int(mask_h.sum()),
                'Status': 'BAIK' if acc_h > 0.55 else ('NETRAL' if acc_h > 0.50 else 'BURUK')
            })

    # --- Analisis BUY vs SELL Bias ---
    print(f"\n{'─'*50}")
    print(f"📊 ANALISIS BIAS ARAH:")
    print(f"{'─'*50}")

    buy_preds = (y_pred == 1).sum()
    sell_preds = (y_pred == 0).sum()
    actual_buy = (y_true == 1).sum()
    actual_sell = (y_true == 0).sum()
    print(f"   Model Prediksi BUY : {buy_preds:>6} ({buy_preds/len(y_true)*100:.1f}%)")
    print(f"   Model Prediksi SELL: {sell_preds:>6} ({sell_preds/len(y_true)*100:.1f}%)")
    print(f"   Aktual Naik (BUY)  : {actual_buy:>6} ({actual_buy/len(y_true)*100:.1f}%)")
    print(f"   Aktual Turun (SELL): {actual_sell:>6} ({actual_sell/len(y_true)*100:.1f}%)")

    # BUY-only dan SELL-only accuracy
    buy_mask = y_pred == 1
    sell_mask = y_pred == 0
    if buy_mask.sum() > 0:
        buy_acc = accuracy_score(y_true[buy_mask], y_pred[buy_mask])
        print(f"   Akurasi saat prediksi BUY : {buy_acc*100:.1f}%")
    if sell_mask.sum() > 0:
        sell_acc = accuracy_score(y_true[sell_mask], y_pred[sell_mask])
        print(f"   Akurasi saat prediksi SELL: {sell_acc*100:.1f}%")

    return {
        'tf': tf_label,
        'period_start': str(df_clean.index[0]),
        'period_end': str(df_clean.index[-1]),
        'total_candles': len(df_clean),
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'confusion_matrix': cm,
        'threshold_results': threshold_results,
        'hourly_results': hourly_results,
        'df_clean': df_clean,
        'y_pred': y_pred,
        'prob_buy': prob_buy,
        'prob_max': prob_max,
    }


def export_to_excel(results_m15, results_m5):
    """Export semua hasil ke Excel untuk lampiran skripsi."""
    print(f"\n{'='*70}")
    print(f"💾 MENYIMPAN HASIL KE EXCEL: {OUTPUT_EXCEL}")
    print(f"{'='*70}")

    with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
        for res in [results_m15, results_m5]:
            if res is None:
                continue
            tf = res['tf']

            # Sheet 1: Metrik Utama
            summary_data = {
                'Metrik': ['Directional Accuracy', 'Precision (BUY)', 'Recall (BUY)',
                          'F1-Score', 'ROC-AUC', 'Total Candle Evaluasi',
                          'Periode Mulai', 'Periode Akhir'],
                'Nilai': [
                    f"{res['accuracy']*100:.2f}%",
                    f"{res['precision']*100:.2f}%",
                    f"{res['recall']*100:.2f}%",
                    f"{res['f1']*100:.2f}%",
                    f"{res['auc']:.4f}",
                    str(res['total_candles']),
                    res['period_start'],
                    res['period_end']
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name=f'{tf} - Ringkasan', index=False)

            # Sheet 2: Confusion Matrix
            cm = res['confusion_matrix']
            cm_df = pd.DataFrame(cm, 
                                 index=['Aktual SELL', 'Aktual BUY'],
                                 columns=['Prediksi SELL', 'Prediksi BUY'])
            cm_df.to_excel(writer, sheet_name=f'{tf} - Confusion Matrix')

            # Sheet 3: Hit Rate per Threshold
            if res['threshold_results']:
                pd.DataFrame(res['threshold_results']).to_excel(
                    writer, sheet_name=f'{tf} - Threshold', index=False
                )

            # Sheet 4: Analisis per Jam
            if res['hourly_results']:
                pd.DataFrame(res['hourly_results']).to_excel(
                    writer, sheet_name=f'{tf} - Per Jam', index=False
                )

    print(f"✅ Berhasil disimpan ke: {OUTPUT_EXCEL}")


def main():
    print("="*85)
    print("🔬 EVALUASI LAYER 1: PURE MODEL ACCURACY (SIGNAL-ONLY TEST)")
    print("   Mengukur akurasi murni prediksi arah LightGBM TANPA bot eksekusi")
    print("="*85)

    init_mt5()
    symbol = get_symbol()

    # --- Load Models ---
    print(f"\n📦 Memuat model...")
    model_m15 = joblib.load(MODEL_M15_PATH)
    print(f"   ✅ Model M15 dimuat: {MODEL_M15_PATH}")
    model_m5 = joblib.load(MODEL_M5_PATH)
    print(f"   ✅ Model M5 dimuat:  {MODEL_M5_PATH}")

    # --- Download Data ---
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
    print("📥 Mengambil data DXY...")
    mt5.symbol_select('DXY', True)
    rates_dxy_m15 = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M15, 0, 50000)
    rates_dxy_m5  = mt5.copy_rates_from_pos('DXY', mt5.TIMEFRAME_M5, 0, 50000)

    if rates_dxy_m15 is not None and len(rates_dxy_m15) > 0:
        df_dxy_m15 = pd.DataFrame(rates_dxy_m15)
        df_dxy_m15['time'] = pd.to_datetime(df_dxy_m15['time'], unit='s')
        df_dxy_m15.set_index('time', inplace=True)
        dxy_close_m15 = df_dxy_m15['close']
    else:
        dxy_df = yf.download("DX-Y.NYB", period="60d", interval="15m", progress=False)
        dxy_close_m15 = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
        if dxy_close_m15.index.tz is not None:
            dxy_close_m15.index = dxy_close_m15.index.tz_localize(None)

    if rates_dxy_m5 is not None and len(rates_dxy_m5) > 0:
        df_dxy_m5 = pd.DataFrame(rates_dxy_m5)
        df_dxy_m5['time'] = pd.to_datetime(df_dxy_m5['time'], unit='s')
        df_dxy_m5.set_index('time', inplace=True)
        dxy_close_m5 = df_dxy_m5['close']
    else:
        dxy_close_m5 = dxy_close_m15.copy()  # Fallback

    print(f"   ✅ M15: {len(df_m15):,} candle | M5: {len(df_m5):,} candle")
    print(f"   ✅ H1: {len(df_h1):,} candle | H4: {len(df_h4):,} candle")

    # --- Build Features & Evaluate ---
    print("\n⚙️ Membangun fitur M15...")
    df_m15_feat = build_features(df_m15, df_h1, df_h4, dxy_close_m15, "M15")
    results_m15 = evaluate_model(model_m15, df_m15_feat, FEATURES_M15, "M15", EVAL_CANDLES_M15)

    print("\n⚙️ Membangun fitur M5...")
    df_m5_feat = build_features(df_m5, df_h1, df_h4, dxy_close_m5, "M5")
    results_m5 = evaluate_model(model_m5, df_m5_feat, FEATURES_M5, "M5", EVAL_CANDLES_M5)

    # --- Export ---
    export_to_excel(results_m15, results_m5)

    # --- Kesimpulan ---
    print(f"\n{'='*70}")
    print(f"📋 KESIMPULAN LAYER 1 — PURE MODEL ACCURACY")
    print(f"{'='*70}")

    for res in [results_m15, results_m5]:
        if res is None:
            continue
        tf = res['tf']
        acc = res['accuracy']
        auc = res['auc']
        status = "✅ EFEKTIF" if acc > 0.53 and auc > 0.55 else ("⚠️ MARGINAL" if acc > 0.50 else "❌ TIDAK EFEKTIF")
        print(f"\n   {tf}: Accuracy={acc*100:.2f}% | AUC={auc:.4f} → {status}")

        if acc > 0.53:
            print(f"   → Model {tf} memiliki daya prediksi di atas random (coin flip).")
            print(f"   → Lanjut ke Layer 2 (Ideal Execution) untuk cek profitabilitas.")
        elif acc > 0.50:
            print(f"   → Model {tf} sedikit di atas random. Perlu perbaikan feature/retrain.")
        else:
            print(f"   → Model {tf} TIDAK lebih baik dari tebak acak. Perlu redesign.")

    mt5.shutdown()
    print(f"\n{'='*70}")
    print("🏁 EVALUASI LAYER 1 SELESAI.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
