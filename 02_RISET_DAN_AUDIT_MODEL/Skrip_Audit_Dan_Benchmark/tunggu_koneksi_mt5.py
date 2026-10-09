import os
import sys
import time
import subprocess
import MetaTrader5 as mt5

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

print("==========================================================================")
print("⏳ MENUNGGU KONEKSI METATRADER 5 (EXNESS)...")
print("==========================================================================")
print("Silakan buka aplikasi MetaTrader 5 di desktop Anda dan lakukan login.")
print("Pastikan indikator koneksi di pojok kanan bawah MT5 berwarna hijau/biru.")
print("==========================================================================\n")

connected = False
for attempt in range(1, 101):
    try:
        # Coba inisialisasi MT5
        is_init = False
        if mt5.initialize():
            is_init = True
        elif os.path.exists(MT5_PATH) and mt5.initialize(path=MT5_PATH):
            is_init = True

        if is_init:
            acc = mt5.account_info()
            if acc is not None and acc.login > 0:
                print("\n" + "="*60)
                print("🎉 KONEKSI MT5 BERHASIL!")
                print(f"👤 Login Akun      : {acc.login}")
                print(f"🏦 Server Broker   : {acc.server}")
                print(f"💰 Saldo (Balance) : ${acc.balance:,.2f}")
                print(f"⚡ AlgoTrading     : {'AKTIF ✅' if acc.trade_allowed else 'NONAKTIF ❌ (Klik tombol AlgoTrading di MT5)'}")
                print(f"🤖 EA Trade Flag   : {'DIIZINKAN ✅' if acc.trade_expert else 'DITOLAK ❌'}")
                print("="*60 + "\n")
                
                symbol = "XAUUSD"
                if mt5.symbol_info(symbol) is None:
                    symbol = "XAUUSDm"
                s_info = mt5.symbol_info(symbol)
                if s_info is not None:
                    print(f"📊 Simbol Ditemukan: {symbol} (Bid: {s_info.bid} | Ask: {s_info.ask})")
                
                connected = True
                break
            else:
                mt5.shutdown()
    except Exception as e:
        pass

    sys.stdout.write(f"\rMenunggu login MT5... (Percobaan ke-{attempt}/100) ")
    sys.stdout.flush()
    time.sleep(3)

if not connected:
    print("\n❌ Waktu tunggu habis. Belum terdeteksi login aktif di MT5.")
    sys.exit(1)

print("\n🚀 Membuka Dashboard Aplikasi EA Trading Bot...")
base_dir = os.path.dirname(os.path.abspath(__file__))
py_exe = sys.executable

# Jalankan Desktop App
subprocess.Popen([py_exe, os.path.join(base_dir, "Desktop_App_Modern.py")], cwd=base_dir)
print("✅ Aplikasi EA Trading Bot berhasil dibuka!")
