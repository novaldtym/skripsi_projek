@echo off
title QuantLGB - AI Trading Bot Dashboard (Figma Edition)
cd /d "%~dp0"

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

set PYTHON_EXE=
if exist "C:\Program Files\Python313\pythonw.exe" (
    set "PYTHON_EXE=C:\Program Files\Python313\pythonw.exe"
) else if exist "%LocalAppData%\Programs\Python\Python313\pythonw.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python313\pythonw.exe"
) else if exist "C:\Python314\pythonw.exe" (
    set "PYTHON_EXE=C:\Python314\pythonw.exe"
) else (
    where pythonw >nul 2>nul
    if %errorlevel% equ 0 (
        set PYTHON_EXE=pythonw
    ) else (
        where pyw >nul 2>nul
        if %errorlevel% equ 0 (
            set PYTHON_EXE=pyw
        ) else (
            set PYTHON_EXE=python
        )
    )
)

echo Membuka QuantLGB Desktop App...
start "" "%PYTHON_EXE%" Desktop_App_Modern.py
exit
