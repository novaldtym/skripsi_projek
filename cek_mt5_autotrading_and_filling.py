import MetaTrader5 as mt5
import sys
try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print(f"❌ Gagal terhubung ke MT5. Error: {mt5.last_error()}")
    exit()

account = mt5.account_info()
print(f"👤 Account Login      : {account.login}")
print(f"🏦 Account Server     : {account.server}")
print(f"💰 Account Balance    : ${account.balance:.2f}")
print(f"⚡ AlgoTrading Allowed: {account.trade_allowed}")
print(f"🤖 EA Trade Allowed  : {account.trade_expert}")

symbol = "XAUUSD"
if mt5.symbol_info(symbol) is None:
    symbol = "XAUUSDm"
s_info = mt5.symbol_info(symbol)

print(f"\n📊 Symbol            : {symbol}")
print(f" Filling Modes Flags  : {s_info.filling_mode}")
# Flags: 1 = FOK, 2 = IOC, 3 = FOK+IOC, 4 = RETURN

mt5.shutdown()
