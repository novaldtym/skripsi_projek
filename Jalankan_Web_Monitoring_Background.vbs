' Script VBS untuk menjalankan Web Dashboard Server di latar belakang (Background)
' Tanpa jendela Command Prompt hitam.
' Menutup Antigravity IDE TIDAK AKAN menghentikan web monitoring ini.

Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd.exe /c ""cd /d D:\SKRIPSI INFORMATIKA && python Web_Dashboard_Server.py""", 0, False
