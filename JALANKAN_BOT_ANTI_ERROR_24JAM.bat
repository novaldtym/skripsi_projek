@echo off
title SUPERVISOR TRADING BOT 24 JAM (ANTI-CRASH & AUTO-RECOVERY)
cd /d "%~dp0"
color 0a
cls

echo ===============================================================================
echo          SUPERVISOR TRADING BOT 24 JAM (ANTI-ERROR ^& AUTO-RELOAD)
echo ===============================================================================
echo.
echo Sistem ini akan:
echo 1. Memastikan MetaTrader 5 menyala otomatis.
echo 2. Menyalakan Web Dashboard Monitoring (Port 5000 + Cloudflare HP).
echo 3. Menyalakan Bot M15 (Eksekusi_Otomatis_Trading_Bot.py).
echo 4. Otomatis ME-RESTART bot dalam 3 detik jika terjadi crash / terputus!
echo.
echo Jendela ini dapat dibiarkan berjalan di latar belakang (minimize).
echo ===============================================================================
echo.

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

:: Cari Python yang valid
set PY_EXE=
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python313\python.exe"
) else if exist "C:\Program Files\Python313\python.exe" (
    set "PY_EXE=C:\Program Files\Python313\python.exe"
) else (
    set "PY_EXE=python"
)

"%PY_EXE%" Supervisor_Trading_Bot.py

pause
