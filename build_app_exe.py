import subprocess
import os
import shutil
import sys

print("[BUILD] Menjalankan PyInstaller untuk QuantLGB Modern Desktop App...")

BASE_DIR = r"d:\SKRIPSI INFORMATIKA"

cmd = [
    sys.executable,
    "-m",
    "PyInstaller",
    "--noconsole",
    "--onefile",
    "--noconfirm",
    "--name=Trading_Bot_Dashboard",
    "--icon=app_icon.ico",
    "--add-data=templates;templates",
    "--add-data=static;static",
    "--hidden-import=webview",
    "--hidden-import=clr",
    "--hidden-import=openpyxl",
    "--hidden-import=pandas",
    "--hidden-import=qrcode",
    "--hidden-import=psutil",
    "--hidden-import=MetaTrader5",
    "--hidden-import=Macro_Economic_News_Engine",
    "--hidden-import=Scenario_Evaluator_Engine",
    "--hidden-import=Auto_Logger_Forward_Testing",
    "--hidden-import=Web_Dashboard_Server",
    "--exclude-module=torch",
    "--exclude-module=torchvision",
    "--exclude-module=torchaudio",
    "--exclude-module=scipy",
    "--exclude-module=matplotlib",
    "--exclude-module=IPython",
    "--exclude-module=nbformat",
    "--exclude-module=zmq",
    "Desktop_App_Modern.py"
]

proc = subprocess.Popen(cmd, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
for line in proc.stdout:
    if line.strip():
        if any(w in line for w in ["INFO", "Building", "checking", "Copying", "Appending", "analyzing", "WARNING", "ERROR"]):
            print(line.strip())
proc.wait()

if proc.returncode != 0:
    print(f"[ERROR] PyInstaller gagal dengan kode: {proc.returncode}")
else:
    print("[SUCCESS] PyInstaller selesai!")
    dist_exe = os.path.join(BASE_DIR, "dist", "Trading_Bot_Dashboard.exe")
    root_exe = os.path.join(BASE_DIR, "Trading_Bot_Dashboard.exe")
    if os.path.exists(dist_exe):
        try:
            shutil.copyfile(dist_exe, root_exe)
            size_mb = os.path.getsize(root_exe) / (1024 * 1024)
            print(f"[INFO] Executable siap: {root_exe} ({size_mb:.2f} MB)")
            print("[INFO] Bebas console .bat hitam, full standalone Windows GUI EXE!")
        except PermissionError:
            size_mb = os.path.getsize(dist_exe) / (1024 * 1024)
            print(f"[INFO] File Trading_Bot_Dashboard.exe sedang aktif dibuka. Hasil build terbaru tersimpan di: {dist_exe} ({size_mb:.2f} MB)")
            print("[INFO] Tutup aplikasi EXE yang sedang berjalan untuk memperbarui file utama.")
