@echo off
title Hentikan Server Web Monitoring
cd /d "%~dp0"
color 0c
cls

echo ===============================================================================
echo            MENGHENTIKAN SERVER WEB MONITORING & CLOUDFLARE TUNNEL
echo ===============================================================================
echo.

echo [1/2] Menutup proses Cloudflare Tunnel...
taskkill /F /IM cloudflared.exe 2>nul

echo [2/2] Menutup proses Web Dashboard Server (Port 5000)...
powershell -Command "Stop-Process -Id (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue).OwningProcess -Force -ErrorAction SilentlyContinue" 2>nul
powershell -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Web_Dashboard_Server.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" 2>nul

echo.
echo ===============================================================================
echo ✅ Server Web Dashboard & Cloudflare Tunnel telah berhasil dimatikan!
echo ===============================================================================
echo.
timeout /t 3
exit
