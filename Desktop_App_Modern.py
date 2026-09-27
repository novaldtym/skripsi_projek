"""
=============================================================================
QUANTLGB MODERN DESKTOP APP — FIGMA EDITION (v4.2)
Teknologi: PyWebView (Edge WebView2 Chromium Engine) + Flask + Poppins UI
Arsitektur Standalone: Single Process / Multi-Threaded, No Console Window
=============================================================================
"""

import os
import sys
import time
import socket
import subprocess
import threading
import webview

PORT = 5000

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVER_SCRIPT = os.path.join(BASE_DIR, "Web_Dashboard_Server.py")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def ensure_server_running():
    """Menjalankan server backend secara langsung dalam thread jika belum aktif"""
    if is_port_in_use(PORT):
        print(f"[Desktop App] Backend Server sudah terdeteksi aktif di port {PORT}.")
        return None

    print(f"[Desktop App] Menyalakan Backend Server QuantLGB di port {PORT}...")
    try:
        def run_flask_thread():
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)
            from Web_Dashboard_Server import app
            app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)

        server_thread = threading.Thread(target=run_flask_thread, daemon=True)
        server_thread.start()
    except Exception as e:
        print(f"[Desktop App] Thread start fallback ke subprocess: {e}")
        import shutil
        py_exec = (
            r"C:\Program Files\Python313\python.exe" if os.path.exists(r"C:\Program Files\Python313\python.exe")
            else shutil.which("pythonw") or shutil.which("python") or sys.executable
        )
        proc = subprocess.Popen(
            [py_exec, SERVER_SCRIPT],
            cwd=BASE_DIR,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return proc

    # Tunggu port terbuka maksimal 10 detik
    for _ in range(25):
        time.sleep(0.4)
        if is_port_in_use(PORT):
            print(f"[Desktop App] Backend Server berhasil menyala di port {PORT}!")
            break

    return None

def main():
    server_process = ensure_server_running()

    window_title = "QuantLGB — AI Trading Bot Dashboard (Figma Edition)"
    target_url = f"http://127.0.0.1:{PORT}"

    print(f"[Desktop App] Membuka jendela desktop WebView2: {target_url}")

    webview.settings['ALLOW_DOWNLOADS'] = True
    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False

    window = webview.create_window(
        title=window_title,
        url=target_url,
        width=1440,
        height=900,
        min_size=(1024, 680),
        resizable=True,
        fullscreen=False,
        background_color='#f8fafc',
        easy_drag=False
    )

    try:
        webview.start(gui='winforms', debug=False)
    except Exception as e:
        print(f"[Desktop App] Fallback start webview: {e}")
        try:
            webview.start(debug=False)
        except Exception as e2:
            print(f"[Desktop App] Gagal membuka webview: {e2}")
    finally:
        print("[Desktop App] Jendela desktop ditutup.")
        if server_process:
            try:
                server_process.kill()
            except Exception:
                pass

if __name__ == '__main__':
    main()
