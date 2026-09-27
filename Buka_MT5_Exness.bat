@echo off
title Buka dan Tampilkan MetaTrader 5 Exness
cd /d "%~dp0"

:: Cek apakah MT5 sudah berjalan
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [INFO] MT5 terdeteksi aktif, memunculkan jendela ke layar...
    python tampilkan_mt5.py
) else (
    echo [INFO] Menjalankan MetaTrader 5 Exness...
    start "" "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
    timeout /t 3 /nobreak >nul
    python tampilkan_mt5.py
)
exit
