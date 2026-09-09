import sys
import os
import joblib
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from lightgbm import LGBMClassifier
import MetaTrader5 as mt5

from Auto_Logger_Forward_Testing import sync_mt5_trades_to_excel

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# =========================================================================
# ⚙️ PENGATURAN FLEKSIBEL & MANAJEMEN RISIKO DINAMIS
# =========================================================================
CHOSEN_TF = "M15"      # Pilihan TF Eksekusi Utama: "M15", "M30", "H1", "H4"
FORWARD_CANDLES = 5    # Horizon Prediksi: 5 candle ke depan (M15 = 75 menit)
LOT_SIZE   = 0.01       # Ukuran Lot: 0.01

# 🎯 MANAJEMEN RISIKO FLEKSIBEL (SMART INTRADAY)
# Pilihan Mode: "SMART_INTRADAY" (Rekomendasi), "FIXED_DOLLAR", "ATR_DYNAMIC"
SL_TP_MODE = "SMART_INTRADAY" 
RRR_RATIO  = 1.5        # Risk-to-Reward Ratio (1 : 1.5) -> TP cepat tersentuh di $7.5 - $10 USD!
TARGET_SL_USD = 5.0     # Target SL Standar ($5.00 / 50 pips)
TARGET_TP_USD = 7.5     # Target TP Standar ($7.50 / 75 pips)
LIVE_TICKER_COUNTDOWN = True  # Fitur Timer Detik Real-time Otomatis



MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MODEL_FILE_PATH = r"d:\SKRIPSI INFORMATIKA\model_lightgbm_xauusd.pkl"

tf_map_mt5 = {
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1":  mt5.TIMEFRAME_H1,
    "H4":  mt5.TIMEFRAME_H4
}

tf_minutes_map = {
    "M15": 15,
    "M30": 30,
    "H1":  60,
    "H4":  240
}

print("="*65)
print(f"MESIN PREDIKSI REAL-TIME XAUUSD (ATR DYNAMIC SL PROTECTION)")
print("="*65)

use_mt5 = False
if os.path.exists(MT5_PATH):
    if mt5.initialize(path=MT5_PATH):
        use_mt5 = True
        print(f"✅ Terhubung ke Exness MT5 (TF: {CHOSEN_TF} | Lot: {LOT_SIZE} | RRR: 1:{RRR_RATIO:.1f})")
    else:
        print("⚠️ MT5 tidak aktif, menggunakan backup data yfinance.")
else:
    print("⚠️ Path MT5 tidak ditemukan.")

def get_multi_tf_data(selected_tf_str):
    if use_mt5:
        symbol = "XAUUSD"
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            symbol = "XAUUSDm"
        mt5.symbol_select(symbol, True)
        
        mt5_tf_enum = tf_map_mt5.get(selected_tf_str, mt5.TIMEFRAME_M15)
        
        rates_main = mt5.copy_rates_from_pos(symbol, mt5_tf_enum, 0, 1000)
        rates_h1   = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1000)
        rates_h4   = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 1000)
        
        df_main = pd.DataFrame(rates_main)
        df_main['time'] = pd.to_datetime(df_main['time'], unit='s')
        df_main.set_index('time', inplace=True)
        
        df_h1 = pd.DataFrame(rates_h1)
        df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
        df_h1.set_index('time', inplace=True)
        
        df_h4 = pd.DataFrame(rates_h4)
        df_h4['time'] = pd.to_datetime(df_h4['time'], unit='s')
        df_h4.set_index('time', inplace=True)
        
        dxy_df = yf.download("DX-Y.NYB", period="10d", interval="15m", progress=False)
        dxy_close = dxy_df['Close'].iloc[:, 0] if isinstance(dxy_df['Close'], pd.DataFrame) else dxy_df['Close']
        if dxy_close.index.tz is not None:
            dxy_close.index = dxy_close.index.tz_localize(None)
        
        tick = mt5.symbol_info_tick(symbol)
        live_price = tick.bid if tick is not None else df_main['close'].iloc[-1]
        live_time_str = datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S') if tick is not None else df_main.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        
        return df_main, df_h1, df_h4, dxy_close, symbol, live_price, live_time_str
    else:
        yf_interval = selected_tf_str.lower()
        if yf_interval == "h1": yf_interval = "1h"
        elif yf_interval == "h4": yf_interval = "1h"
        elif yf_interval == "m30": yf_interval = "30m"
        elif yf_interval == "m15": yf_interval = "15m"
        
        gold_main = yf.download("GC=F", period="10d", interval=yf_interval, progress=False)
        gold_h1   = yf.download("GC=F", period="30d", interval="1h", progress=False)
        gold_h4   = yf.download("GC=F", period="60d", interval="1h", progress=False)
        dxy_m15   = yf.download("DX-Y.NYB", period="10d", interval="15m", progress=False)
        
        def clean_yf(df_raw):
            if isinstance(df_raw.columns, pd.MultiIndex):
                res = pd.DataFrame({
                    'open': df_raw['Open'].iloc[:, 0],
                    'high': df_raw['High'].iloc[:, 0],
                    'low': df_raw['Low'].iloc[:, 0],
                    'close': df_raw['Close'].iloc[:, 0],
                    'tick_volume': df_raw['Volume'].iloc[:, 0]
                })
            else:
                res = pd.DataFrame({
                    'open': df_raw['Open'],
                    'high': df_raw['High'],
                    'low': df_raw['Low'],
                    'close': df_raw['Close'],
                    'tick_volume': df_raw['Volume']
                })
            if res.index.tz is not None:
                res.index = res.index.tz_localize(None)
            return res
            
        main_clean = clean_yf(gold_main)
        h1_clean   = clean_yf(gold_h1)
        h4_clean   = clean_yf(gold_h4)
        dxy_close  = dxy_m15['Close'].iloc[:, 0] if isinstance(dxy_m15['Close'], pd.DataFrame) else dxy_m15['Close']
        if dxy_close.index.tz is not None:
            dxy_close.index = dxy_close.index.tz_localize(None)
        
        live_p = main_clean['close'].iloc[-1]
        live_t = main_clean.index[-1].strftime('%Y-%m-%d %H:%M:%S')
        return main_clean, h1_clean, h4_clean, dxy_close, "GC=F", live_p, live_t

df_main, df_h1, df_h4, dxy_close, active_symbol, live_price, live_time_str = get_multi_tf_data(CHOSEN_TF)

# =========================================================================
# FEATURE ENGINEERING & VOLATILITY (ATR)
# =========================================================================
range_main = (df_main['high'] - df_main['low']) + 1e-6
df_main['Body_M15'] = (df_main['close'] - df_main['open']).abs() / range_main
df_main['Lower_Wick_M15'] = (df_main[['open', 'close']].min(axis=1) - df_main['low']) / range_main
df_main['Upper_Wick_M15'] = (df_main['high'] - df_main[['open', 'close']].max(axis=1)) / range_main

# Average True Range (ATR 14) untuk Volatilitas Emas
df_main['TR'] = np.maximum(
    df_main['high'] - df_main['low'],
    np.maximum(
        (df_main['high'] - df_main['close'].shift()).abs(),
        (df_main['low'] - df_main['close'].shift()).abs()
    )
)
df_main['ATR_14'] = df_main['TR'].rolling(14).mean()

delta = df_main['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
df_main['RSI_M15'] = 100 - (100 / (1 + (gain / (loss + 1e-6))))

df_main['SMA_20_M15'] = df_main['close'].rolling(20).mean()
df_main['STD_20_M15'] = df_main['close'].rolling(20).std()
df_main['BB_Bandwidth'] = (4 * df_main['STD_20_M15']) / df_main['SMA_20_M15']
df_main['BB_Pos'] = (df_main['close'] - (df_main['SMA_20_M15'] - 2*df_main['STD_20_M15'])) / (4*df_main['STD_20_M15'] + 1e-6)

df_main['XAU_Return_1'] = df_main['close'].pct_change(1)
df_main['XAU_Return_3'] = df_main['close'].pct_change(3)
df_main['XAU_Return_5'] = df_main['close'].pct_change(5)

df_main['DXY_Close'] = dxy_close.reindex(df_main.index, method='ffill')
df_main['DXY_Return_1'] = df_main['DXY_Close'].pct_change(1).fillna(0)
df_main['DXY_Return_3'] = df_main['DXY_Close'].pct_change(3).fillna(0)

df_h1['SMA_20_H1'] = df_h1['close'].rolling(20).mean()
df_h1['Trend_H1'] = (df_h1['close'] > df_h1['SMA_20_H1']).astype(int)

df_h4['SMA_50_H4'] = df_h4['close'].rolling(50).mean()
df_h4['Trend_H4'] = (df_h4['close'] > df_h4['SMA_50_H4']).astype(int)

df_main['Trend_H1'] = df_h1['Trend_H1'].reindex(df_main.index, method='ffill').fillna(0)
df_main['Trend_H4'] = df_h4['Trend_H4'].reindex(df_main.index, method='ffill').fillna(0)

# Target: apakah harga N candle ke depan lebih tinggi dari sekarang?
# Ini menyelaraskan horizon prediksi dengan horizon trade (SL/TP butuh multi-candle)
df_main['Target_Future'] = df_main['close'].shift(-FORWARD_CANDLES)
df_main['Target_Dir'] = (df_main['Target_Future'] > df_main['close']).astype(int)

df_clean = df_main.dropna().copy()

features = [
    'Body_M15', 'Lower_Wick_M15', 'Upper_Wick_M15', 
    'RSI_M15', 'BB_Bandwidth', 'BB_Pos',
    'XAU_Return_1', 'XAU_Return_3', 'XAU_Return_5',
    'DXY_Return_1', 'DXY_Return_3',
    'Trend_H1', 'Trend_H4'
]

X = df_clean[features]
y = df_clean['Target_Dir']

X_train = X.iloc[:-1]
y_train = y.iloc[:-1]

latest_completed_candle = X.iloc[[-1]]
last_candle_time = df_clean.index[-1].strftime('%Y-%m-%d %H:%M:%S')

# 🎯 KALKULASI SL & TP DINAMIS FLEKSIBEL
latest_atr = df_clean['ATR_14'].iloc[-1]

if SL_TP_MODE == "SMART_INTRADAY":
    # Mode Scalping/Intraday Presisi: SL ~50 Pips ($5.00), TP ~75 Pips ($7.50 - $10.00)
    SL_PIPS = max(40.0, round(latest_atr * 10.0 * 0.6, 0))
    TP_PIPS = round(SL_PIPS * RRR_RATIO, 0)
elif SL_TP_MODE == "FIXED_DOLLAR":
    # Mode Fixed Pips Sesuai Keinginan User
    SL_PIPS = TARGET_SL_USD * 10.0
    TP_PIPS = TARGET_TP_USD * 10.0
else:
    # Mode ATR Full Dynamic
    SL_PIPS = max(50.0, round(latest_atr * 10.0 * 1.0, 0))
    TP_PIPS = round(SL_PIPS * RRR_RATIO, 0)


if os.path.exists(MODEL_FILE_PATH):
    model = joblib.load(MODEL_FILE_PATH)
    print(f"✅ Model Robust Terkait ({MODEL_FILE_PATH}) Berhasil Dimuat.")
else:
    print("⚠️ Model pkl tidak ditemukan, melatih model sementara...")
    model = LGBMClassifier(
        n_estimators=300,
        learning_rate=0.02,
        max_depth=6,
        num_leaves=15,
        min_child_samples=40,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight='balanced',
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)
    joblib.dump(model, MODEL_FILE_PATH)

prob_up = model.predict_proba(latest_completed_candle)[0][1] * 100
prob_down = 100 - prob_up


entry_price = float(live_price)

# HITUNG MUNDUR SISA WAKTU MENUJU PERGANTIAN CANDLE BARU
now = datetime.now()
tf_min = tf_minutes_map.get(CHOSEN_TF, 15)
minutes_past = now.minute % tf_min
seconds_past = minutes_past * 60 + now.second
total_tf_seconds = tf_min * 60
seconds_left = total_tf_seconds - seconds_past
next_candle_time = now + timedelta(seconds=seconds_left)
next_candle_str = next_candle_time.strftime('%H:%M:00')

print("\n" + "-"*65)
print(f"HASIL PREDIKSI EXNESS MT5 (TF EKSEKUSI: {CHOSEN_TF})")
print(f"Horizon Prediksi          : {FORWARD_CANDLES} candle ke depan ({FORWARD_CANDLES * tf_min} menit)")
print(f"Volatilitas ATR 14        : ${latest_atr:.2f} / oz (Noise Emas)")
print(f"Jarak Stop-Loss Dinamis   : {SL_PIPS:.0f} Pips (${SL_PIPS/10:.2f}) -> Aman dari Spreading Noise")
print(f"Jarak Take-Profit Dinamis : {TP_PIPS:.0f} Pips (${TP_PIPS/10:.2f}) -> Target Rasio 1:{RRR_RATIO:.1f}")
print(f"Candle Acuan (Baru Tutup) : {last_candle_time}")
print(f"Harga Open Live saat ini  : ${entry_price:.2f} / oz")
print("-"*65)
print(f"⏳ SISA WAKTU MENUJU CANDLE BARU ({next_candle_str}): {seconds_left // 60:02d}m {seconds_left % 60:02d}s")
if seconds_left <= 30:
    print("🔔 STATUS: SANGAT IDEAL UTK SIAP-SIAP ENTRY (Kurang dari 30 detik lagi pergantian candle!)")
elif seconds_left >= (total_tf_seconds - 60):
    print("🟢 STATUS: MURNI DETIK AWAL PERGANTIAN CANDLE BARU! (SANGAT PRESISI UTK ENTRY)")
else:
    print(f"⚠️ STATUS: Candle {CHOSEN_TF} sedang berjalan di tengah. Idealnya tunggu sisa 00m 05s!")
print("-"*65)

print(f"Probabilitas Periode Depan NAIK (BUY)  : {prob_up:.2f}%")
print(f"Probabilitas Periode Depan TURUN (SELL): {prob_down:.2f}%")
print("-"*65)

pip_value_usd = LOT_SIZE * 10.0
dollar_risk = SL_PIPS * pip_value_usd
dollar_reward = TP_PIPS * pip_value_usd

if prob_up >= 55.0:
    sl_price = entry_price - (SL_PIPS / 10.0)
    tp_price = entry_price + (TP_PIPS / 10.0)
    print(f"🟢 REKOMENDASI POSISI: BUY XAUUSD ({CHOSEN_TF})")
    print(f"   • Lot Size        : {LOT_SIZE} Lot")
    print(f"   • Price Entry     : ${entry_price:.2f}")
    print(f"   • Stop Loss (SL)  : ${sl_price:.2f} ({SL_PIPS:.0f} pips -> Risiko: -${dollar_risk:.2f} USD)")
    print(f"   • Take Profit (TP): ${tp_price:.2f} ({TP_PIPS:.0f} pips -> Potensi Gain: +${dollar_reward:.2f} USD)")
    print(f"   • Risk:Reward     : 1 : {RRR_RATIO:.1f}")

elif prob_down >= 55.0:
    sl_price = entry_price + (SL_PIPS / 10.0)
    tp_price = entry_price - (TP_PIPS / 10.0)
    print(f"🔴 REKOMENDASI POSISI: SELL XAUUSD ({CHOSEN_TF})")
    print(f"   • Lot Size        : {LOT_SIZE} Lot")
    print(f"   • Price Entry     : ${entry_price:.2f}")
    print(f"   • Stop Loss (SL)  : ${sl_price:.2f} ({SL_PIPS:.0f} pips -> Risiko: -${dollar_risk:.2f} USD)")
    print(f"   • Take Profit (TP): ${tp_price:.2f} ({TP_PIPS:.0f} pips -> Potensi Gain: +${dollar_reward:.2f} USD)")
    print(f"   • Risk:Reward     : 1 : {RRR_RATIO:.1f}")

else:
    print(f"🟡 REKOMENDASI POSISI: WAIT / NO TRADE ({CHOSEN_TF})")
    print("   (Sinyal Netral. Tingkat kepastian < 55%. Jangan entry dulu untuk menjaga modal).")

print("="*65)

# SYNC OTOMATIS HISTORI TRADE DARI MT5 KE EXCEL FORWARD TESTING
print("\n" + "-"*65)
print("📊 AUTOMATIC FORWARD-TESTING EXCEL LOGGER")
print("-"*65)
res = sync_mt5_trades_to_excel()
if res is not None:
    summary_df, df_trades = res
    print(f"Total Trade Terbaca  : {summary_df['Total Trade Terbaca'].iloc[0]} / 100 Trade")
    print(f"Progres Skripsi      : {summary_df['Progres Trade (%)'].iloc[0]}")
    print(f"Win Rate             : {summary_df['Win Rate (%)'].iloc[0]}")
    print(f"Total Profit/Loss    : {summary_df['Total Cumulative P&L ($ USD)'].iloc[0]}")
    print(f"Profit Factor        : {summary_df['Profit Factor'].iloc[0]}")
print("="*65)

# HITUNG MUNDUR DETIK REAL-TIME (TICK-BY-TICK COUNTDOWN)
if LIVE_TICKER_COUNTDOWN:
    import time
    print("\n" + "="*65)
    print(f"⏱️ LIVE COUNTDOWN DETIK REAL-TIME (TF: {CHOSEN_TF})")
    print("Petunjuk: Biarkan terminal ini terbuka. Saat sisa 00m 05s, segera entry!")
    print("Tekan Ctrl+C jika ingin menghentikan countdown.")
    print("="*65)
    try:
        while True:
            n_now = datetime.now()
            m_past = n_now.minute % tf_min
            s_past = m_past * 60 + n_now.second
            tot_sec = tf_min * 60
            sec_rem = tot_sec - s_past
            
            mins = sec_rem // 60
            secs = sec_rem % 60
            
            if sec_rem <= 5:
                status_msg = "🔥 ENTRY SEKARANG! (5 Detik Terakhir)"
            elif sec_rem <= 30:
                status_msg = "⚡ Siap-siap pasang posisi..."
            else:
                status_msg = "Tunggu..."
                
            sys.stdout.write(f"\r⏳ SISA WAKTU: {mins:02d}m {secs:02d}s | Status: {status_msg}   ")
            sys.stdout.flush()
            
            if sec_rem == 0:
                print("\n🔔 CANDLE BARU TERBENTUK! Dapatkan sinyal baru dengan re-run skrip.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nCountdown dihentikan oleh user.")

if use_mt5:
    mt5.shutdown()

