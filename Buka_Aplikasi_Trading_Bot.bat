@echo off
title AI Trading Bot GUI Launcher
cd /d "%~dp0"

:: Set encoding lingkungan ke UTF-8
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Jalankan Aplikasi Desktop GUI menggunakan pythonw (tanpa jendela CMD hitam)
set PYTHONW_EXE=C:\Users\nouval\AppData\Local\Programs\Python\Python313\pythonw.exe
if not exist "%PYTHONW_EXE%" (
    where pythonw >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHONW_EXE=pythonw
    ) else (
        where pyw >nul 2>nul
        if %errorlevel% equ 0 (
            set PYTHONW_EXE=pyw
        ) else (
            set PYTHONW_EXE=python
        )
    )
)

start "" "%PYTHONW_EXE%" Trading_Bot_GUI_App.py
exit
