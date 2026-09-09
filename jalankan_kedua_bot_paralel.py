import subprocess
import sys
import os
import time

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

print("="*80)
print("🚀 LAUNCHER DUA ROBOT TRADING OTOMATIS: M15 KONSERVATIF & M5 SCALPING")
print("="*80)
print("\n[1] Membuka Bot M15 Konservatif (>= 60%, Magic 123230)...")
p1 = subprocess.Popen(
    ["cmd", "/k", "title Bot 1: M15 Konservatif (>= 60%) && python Eksekusi_Otomatis_Trading_Bot.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    cwd=r"d:\SKRIPSI INFORMATIKA"
)

time.sleep(3)

print("[2] Membuka Bot M5 Scalping Agresif (>= 55%, Stacking, Magic 123235)...")
p2 = subprocess.Popen(
    ["cmd", "/k", "title Bot 2: M5 Scalping Agresif (>= 55%) && python Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py"],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
    cwd=r"d:\SKRIPSI INFORMATIKA"
)

print("\n" + "="*80)
print("✅ KEDUA ROBOT TELAH BERJALAN BERSAMAAN DALAM CONSOLE TERPISAH!")
print("• Bot M15 Konservatif : Magic 123230 | Single Position | Log: Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx")
print("• Bot M5 Scalping     : Magic 123235 | Stacking Max 3   | Log: Laporan_Forward_Testing_Model_M5_Scalping.xlsx")
print("="*80)
