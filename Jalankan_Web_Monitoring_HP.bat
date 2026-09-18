@echo off
title WEB DASHBOARD MONITORING TRADING BOT (MOBILE & PC)
cd /d "%~dp0"
color 0b
cls

echo ===============================================================================
echo        MENYALAKAN SERVER WEB MONITORING TRADING BOT (MOBILE-FIRST)
echo ===============================================================================
echo.
echo Sedang menyiapkan server Flask dan Cloudflare HTTPS Tunnel...
echo Catatan: Jendela ini berjalan mandiri di Windows.
echo Anda bebas menutup Antigravity IDE tanpa mematikan web monitoring ini.
echo.

:: Tutup instance lama jika ada
taskkill /F /IM cloudflared.exe 2>nul
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue" 2>nul

:: Jalankan server Python
python Web_Dashboard_Server.py

pause
