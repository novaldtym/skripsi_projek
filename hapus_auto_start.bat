@echo off
title Nonaktifkan Auto-Start Robot Trading
chcp 65001 >nul
cls

echo =========================================================================
echo    ❌ HAPUS AUTO-START ROBOT TRADING AI
echo =========================================================================
echo.

set TASK_NAME=AITradingBot_AutoStart

schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo  ✅ Auto-Start berhasil dinonaktifkan!
    echo  Robot Trading tidak lagi menyala otomatis saat login Windows.
) else (
    echo  ℹ️ Task "%TASK_NAME%" tidak ditemukan atau sudah dinonaktifkan sebelumnya.
)

echo.
echo Tekan tombol apa saja untuk keluar...
pause >nul
