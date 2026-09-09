import MetaTrader5 as mt5

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
if not mt5.initialize(path=MT5_PATH):
    print("❌ Gagal terhubung ke MT5")
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
