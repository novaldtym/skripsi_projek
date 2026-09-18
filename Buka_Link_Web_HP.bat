@echo off
title LINK MONITORING BOT TRADING AI (HP & PC)
cd /d "%~dp0"
color 0a
cls

set /p CURRENT_URL=<public_url.txt

echo ===============================================================================
echo            LINK MONITORING BOT TRADING AI (AKTIF DI MANA SAJA)
echo ===============================================================================
echo.
echo  Link Publik HP (HTTPS) : %CURRENT_URL%
echo  Link Wi-Fi Lokal        : http://localhost:5000
echo.
echo ===============================================================================
echo  [1] Link HTTPS di atas telah otomatis DISALIN ke Clipboard Anda!
echo      (Tinggal tekan CTRL+V / Paste untuk kirim ke WhatsApp / HP).
echo.
echo  [2] Membuka link di browser PC...
echo ===============================================================================

echo %CURRENT_URL%| clip
start "" "%CURRENT_URL%"

echo.
echo Tekan sembarang tombol untuk menutup jendela ini...
pause >nul
exit
