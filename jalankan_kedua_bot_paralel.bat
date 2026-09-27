@echo off
title AI Trading Bot GUI Launcher
cd /d "%~dp0"

:: Jalankan Aplikasi Desktop GUI menggunakan pythonw (tanpa jendela CMD hitam)
set PYTHONW_EXE=
if exist "C:\Program Files\Python313\pythonw.exe" (
    set "PYTHONW_EXE=C:\Program Files\Python313\pythonw.exe"
) else if exist "%LocalAppData%\Programs\Python\Python313\pythonw.exe" (
    set "PYTHONW_EXE=%LocalAppData%\Programs\Python\Python313\pythonw.exe"
) else if exist "C:\Python314\pythonw.exe" (
    set "PYTHONW_EXE=C:\Python314\pythonw.exe"
) else (
    set PYTHONW_EXE=pythonw
)

start "" "%PYTHONW_EXE%" Trading_Bot_GUI_App.py
exit
