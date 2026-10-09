"""
=============================================================================
SUPERVISOR TRADING BOT 24 JAM — ANTI-ERROR & AUTO-RECOVERY (v4.3)
Sistem Pengawas Otonom:
1. Memastikan MetaTrader 5 (Exness) selalu berjalan.
2. Memastikan Web Dashboard Server (Port 5000 & Cloudflare) selalu online.
3. Memastikan Bot Eksekusi M15 (Eksekusi_Otomatis_Trading_Bot.py) selalu aktif.
4. Auto-Restart seketika (3 detik) jika ada script yang crash, terputus, atau mati.
5. Pembersihan socket TIME_WAIT otomatis dan proteksi single-instance.
=============================================================================
"""

import os
import sys
import time
import socket
import datetime
import subprocess
import psutil
import shutil

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "supervisor.log")
MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

def log_event(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] {msg}"
    print(formatted)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def get_python_exe():
    candidates = [
        shutil.which("python"),
        shutil.which("python3"),
        os.path.expandvars(r"%LocalAppData%\Programs\Python\Python313\python.exe"),
        r"C:\Program Files\Python313\python.exe",
        sys.executable
    ]
    for c in candidates:
        if c and os.path.exists(c) and not c.lower().endswith("trading_bot_dashboard.exe"):
            return c
    return sys.executable

PYTHON_EXE = get_python_exe()

def is_mt5_running():
    for p in psutil.process_iter(['name']):
        try:
            if 'terminal64' in (p.info['name'] or '').lower():
                return True
        except Exception:
            pass
    return False

def ensure_mt5_running():
    if not is_mt5_running():
        if os.path.exists(MT5_PATH):
            log_event("🚀 [SUPERVISOR] MetaTrader 5 belum menyala. Menjalankan MT5 Exness...")
            subprocess.Popen([MT5_PATH])
            time.sleep(5)
        else:
            log_event("⚠️ [SUPERVISOR] File MT5 terminal64.exe tidak ditemukan di lokasi standar.")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', port))
            return False
        except socket.error:
            return True
        except Exception:
            return False

def is_script_running(script_name):
    script_name = script_name.lower()
    if script_name == "eksekusi_otomatis_trading_bot.py" and is_port_in_use(48901):
        return True
    if script_name == "eksekusi_otomatis_trading_bot_m15_pro.py" and is_port_in_use(48903):
        return True
    if script_name == "web_dashboard_server.py" and is_port_in_use(5000):
        return True

    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd_args = [os.path.basename(arg).lower() for arg in (p.info['cmdline'] or []) if arg]
            if script_name in cmd_args:
                return True
        except Exception:
            pass
    return False

def start_script_process(script_rel_path, log_name):
    script_path = os.path.join(BASE_DIR, script_rel_path)
    log_path = os.path.join(BASE_DIR, log_name)
    try:
        log_f = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [PYTHON_EXE, "-u", script_path],
            cwd=BASE_DIR,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        log_event(f"✅ [SUPERVISOR] Berhasil menyalakan '{script_rel_path}' (PID: {proc.pid})")
        return proc
    except Exception as e:
        log_event(f"❌ [SUPERVISOR] Gagal menjalankan '{script_rel_path}': {e}")
        return None

def main():
    log_event("="*75)
    log_event("🛡️ SUPERVISOR TRADING BOT 24 JAM DIAKTIFKAN (SKRIPSI + PRO V6 DUAL-ENGINE)")
    log_event(f"📁 Direktori: {BASE_DIR}")
    log_event(f"🐍 Python Exe: {PYTHON_EXE}")
    log_event("="*75)

    # 1. Pastikan MT5 Aktif
    ensure_mt5_running()

    restart_counters = {
        "m15": 0,
        "pro": 0,
        "server": 0
    }
    last_restart_time = {
        "m15": 0.0,
        "pro": 0.0,
        "server": 0.0
    }
    COOLDOWN = 20.0

    while True:
        try:
            now = time.time()

            # A. Pantau MT5
            ensure_mt5_running()

            # B. Pantau Web Dashboard Server
            if not is_script_running("Web_Dashboard_Server.py"):
                if now - last_restart_time["server"] >= COOLDOWN:
                    last_restart_time["server"] = now
                    restart_counters["server"] += 1
                    log_event(f"⚠️ [WATCHDOG] Web Dashboard Server mati! Me-restart server (Ke-{restart_counters['server']})...")
                    start_script_process("Web_Dashboard_Server.py", "server_run.log")

            # C. Pantau Bot M15 Utama (Skripsi)
            if not is_script_running("Eksekusi_Otomatis_Trading_Bot.py"):
                if now - last_restart_time["m15"] >= COOLDOWN:
                    last_restart_time["m15"] = now
                    restart_counters["m15"] += 1
                    log_event(f"🚨 [WATCHDOG] Bot M15 Utama mati! Me-restart Bot M15 (Ke-{restart_counters['m15']})...")
                    start_script_process("Eksekusi_Otomatis_Trading_Bot.py", "bot_m15_daemon.log")

            # D. Pantau Bot PRO V6 Dual-Engine
            if not is_script_running("Eksekusi_Otomatis_Trading_Bot_M15_PRO.py"):
                if now - last_restart_time["pro"] >= COOLDOWN:
                    last_restart_time["pro"] = now
                    restart_counters["pro"] += 1
                    log_event(f"🏆 [WATCHDOG] Bot PRO V6 Dual-Engine belum aktif! Menyalakan Bot PRO V6 (Ke-{restart_counters['pro']})...")
                    start_script_process("Eksekusi_Otomatis_Trading_Bot_M15_PRO.py", "bot_m15_pro_daemon.log")

            time.sleep(5)

        except KeyboardInterrupt:
            log_event("🛑 [SUPERVISOR] Dimatikan oleh pengguna.")
            break
        except Exception as e:
            log_event(f"⚠️ [SUPERVISOR LOOP EXCEPTION]: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
