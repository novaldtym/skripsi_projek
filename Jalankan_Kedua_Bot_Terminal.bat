@echo off
title Launcher Dua Bot Trading AI v3.7
cd /d "%~dp0"

echo =========================================================================
echo 🚀 MEMULAI DUA BOT TRADING OTOMATIS (M15 SWING & M5 SCALPING v3.7)
echo =========================================================================

echo [1/2] Menjalankan Bot M15 (Magic 123230)...
start "Bot 1: M15 Swing v3.7 (Magic 123230)" cmd /k "python Eksekusi_Otomatis_Trading_Bot.py"

timeout /t 3 /nobreak >nul

echo [2/2] Menjalankan Bot M5 Scalper (Magic 123236)...
start "Bot 2: M5 Scalper v3.7 (Magic 123236)" cmd /k "python Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py"

echo =========================================================================
echo ✅ Kedua bot v3.7 telah berhasil dijalankan dalam konsol terpisah!
echo =========================================================================
timeout /t 3
exit
