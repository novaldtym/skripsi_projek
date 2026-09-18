"""
=============================================================================
CLOUDFLARE TUNNEL MANAGER (GRATIS & RESMI)
Menyediakan URL Publik HTTPS aman agar dashboard bot trading dapat diakses
dari HP di mana saja (luar rumah, paket data kuota, kampus, kafe).
=============================================================================
"""

import os
import re
import sys
import time
import atexit
import threading
import subprocess

CF_PROCESS = None
PUBLIC_URL = None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXE_PATH = os.path.join(BASE_DIR, "cloudflared.exe")
URL_FILE = os.path.join(BASE_DIR, "public_url.txt")

def cleanup_tunnel():
    """Menghentikan proses cloudflared jika server ditutup"""
    global CF_PROCESS
    if CF_PROCESS and CF_PROCESS.poll() is None:
        try:
            print("[Cloudflare] Menutup secure tunnel...")
            CF_PROCESS.terminate()
            CF_PROCESS.wait(timeout=3)
        except Exception:
            try:
                CF_PROCESS.kill()
            except Exception:
                pass
    CF_PROCESS = None

def kill_existing_cloudflared():
    """Memastikan tidak ada instance cloudflared lama yang menggantung"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "cloudflared.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)
    except Exception:
        pass

def run_tunnel_thread(port=5000):
    global CF_PROCESS, PUBLIC_URL
    if not os.path.exists(EXE_PATH):
        print(f"[Cloudflare] WARNING: {EXE_PATH} tidak ditemukan.")
        return

    kill_existing_cloudflared()

    cmd = [EXE_PATH, "tunnel", "--url", f"http://127.0.0.1:{port}"]
    try:
        CF_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="ignore"
        )

        # Cari URL trycloudflare.com dari output
        for line in CF_PROCESS.stderr:
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                PUBLIC_URL = match.group(0)
                print(f"\n[Cloudflare] Tunnel Aktif! URL Publik: {PUBLIC_URL}")
                try:
                    with open(URL_FILE, "w", encoding="utf-8") as f:
                        f.write(PUBLIC_URL)
                except Exception:
                    pass
                break
    except Exception as e:
        print(f"[Cloudflare] Error saat menjalankan tunnel: {e}")

def start_cloudflare_tunnel(port=5000, wait_seconds=8):
    """
    Memulai Cloudflare Tunnel di background thread dan menunggu hingga URL terbentuk
    """
    t = threading.Thread(target=run_tunnel_thread, args=(port,), daemon=True)
    t.start()

    # Tunggu sebentar hingga URL didapatkan
    start_time = time.time()
    while time.time() - start_time < wait_seconds:
        if PUBLIC_URL:
            return PUBLIC_URL
        time.sleep(0.5)

    return PUBLIC_URL

def get_public_url():
    """Mengambil URL publik aktif saat ini"""
    global PUBLIC_URL
    if PUBLIC_URL:
        return PUBLIC_URL
    if os.path.exists(URL_FILE):
        try:
            with open(URL_FILE, "r", encoding="utf-8") as f:
                url = f.read().strip()
                if url.startswith("https://"):
                    return url
        except Exception:
            pass
    return None
