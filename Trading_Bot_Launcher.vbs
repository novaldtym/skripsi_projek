Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "d:\SKRIPSI INFORMATIKA"
' Menjalankan Trading_Bot_GUI_App.py dengan pythonw (tanpa jendela console/cmd hitam sama sekali)
WshShell.Run "pythonw.exe Trading_Bot_GUI_App.py", 0, False
