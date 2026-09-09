@echo off
title AI Trading Bot GUI Launcher
cd /d "%~dp0"

:: Jalankan Aplikasi Desktop GUI menggunakan pythonw (tanpa jendela CMD hitam)
set PYTHONW_EXE=C:\Users\nouval\AppData\Local\Programs\Python\Python313\pythonw.exe
if not exist "%PYTHONW_EXE%" set PYTHONW_EXE=pythonw

start "" "%PYTHONW_EXE%" Trading_Bot_GUI_App.py
exit
