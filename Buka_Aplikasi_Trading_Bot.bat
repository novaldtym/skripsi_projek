@echo off
title AI Trading Bot GUI Launcher
cd /d "%~dp0"

:: Set encoding lingkungan ke UTF-8
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:: Jalankan Aplikasi Desktop GUI menggunakan pythonw (tanpa jendela CMD hitam)
set PYTHONW_EXE=
if exist "C:\Program Files\Python313\pythonw.exe" (
    set "PYTHONW_EXE=C:\Program Files\Python313\pythonw.exe"
) else if exist "%LocalAppData%\Programs\Python\Python313\pythonw.exe" (
    set "PYTHONW_EXE=%LocalAppData%\Programs\Python\Python313\pythonw.exe"
) else if exist "C:\Python314\pythonw.exe" (
    set "PYTHONW_EXE=C:\Python314\pythonw.exe"
) else (
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

start "" "%PYTHONW_EXE%" Desktop_App_Modern.py
exit
