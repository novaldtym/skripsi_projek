@echo off
title LAUNCHER DUA ROBOT TRADING (M15 & M5)

set PYTHON_EXE=C:\Users\nouval\AppData\Local\Programs\Python\Python313\python.exe
if not exist "%PYTHON_EXE%" set PYTHON_EXE=python

echo ===============================================================================
echo MEMULAI DUA ROBOT TRADING OTOMATIS LIGHTGBM XAUUSD SECARA PARALEL
echo ===============================================================================
echo.
echo [1] Bot M15 Konservatif: Threshold 60%% ^| Single Position ^| Magic 123230
echo     File: Eksekusi_Otomatis_Trading_Bot.py
echo     Excel: Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx
echo.
echo [2] Bot M5 Scalping    : Threshold 55%% ^| Stacking Max 3   ^| Magic 123235
echo     File: Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py
echo     Excel: Laporan_Forward_Testing_Model_M5_Scalping.xlsx
echo.
echo ===============================================================================
echo Membuka kedua bot di jendela konsol terpisah...
echo.

start "Bot 1: M15 Konservatif" /D "d:\SKRIPSI INFORMATIKA" "%PYTHON_EXE%" Eksekusi_Otomatis_Trading_Bot.py

timeout /t 2 /nobreak > nul

start "Bot 2: M5 Scalping" /D "d:\SKRIPSI INFORMATIKA" "%PYTHON_EXE%" Eksekusi_Otomatis_Trading_Bot_M5_Scalping.py

echo.
echo KEDUA ROBOT TELAH BERHASIL DIBUKA DI JENDELA MASING-MASING!
echo Anda dapat memantau aktivitas keduanya secara real-time.
echo Jendela ini dapat ditutup.
echo.
pause
