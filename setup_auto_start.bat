@echo off
title Setup Auto-Start Robot Trading saat PC Dinyalakan
chcp 65001 >nul
cls

echo =========================================================================
echo    ⚡ SETUP AUTO-START ROBOT TRADING AI (WINDOWS TASK SCHEDULER)
echo =========================================================================
echo.
echo Script ini akan mendaftarkan Task Scheduler Windows agar aplikasi
echo Robot Trading otomatis menyala dan siap monitoring setiap kali
echo Anda menyalakan PC / Login Windows (tanpa perlu klik manual).
echo.

set TASK_NAME=AITradingBot_AutoStart
set BAT_PATH=d:\SKRIPSI INFORMATIKA\Buka_Aplikasi_Trading_Bot.bat

echo [*] Mendaftarkan Task Scheduler: %TASK_NAME%...
schtasks /create /tn "%TASK_NAME%" /tr "\"%BAT_PATH%\"" /sc onlogon /rl highest /f >nul 2>&1

if %errorlevel% equ 0 (
    echo.
    echo =========================================================================
    echo  ✅ AUTO-START BERHASIL DIAKTIFKAN!
    echo =========================================================================
    echo  Nama Task : %TASK_NAME%
    echo  Target    : %BAT_PATH%
    echo  Pemicu    : Otomatis berjalan setiap kali Login Windows (On Logon)
    echo.
    echo  Kini Anda tidak perlu khawatir kehilangan sinyal saat PC baru dinyalakan.
    echo  Bot juga dilengkapi fitur "Startup Catch-Up Scan" untuk langsung
    echo  menangkap peluang candle terbaru begitu PC aktif!
    echo =========================================================================
) else (
    echo.
    echo ⚠️ Gagal mendaftarkan task secara otomatis (Perlu Hak Administrator).
    echo Silakan klik kanan file ini dan pilih "Run as Administrator" / "Jalankan sebagai administrator".
)

echo.
echo Tekan tombol apa saja untuk keluar...
pause >nul
