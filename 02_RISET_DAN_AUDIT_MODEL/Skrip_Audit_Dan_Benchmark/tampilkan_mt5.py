import sys
import ctypes
import ctypes.wintypes
import psutil

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

user32 = ctypes.windll.user32
h_default = user32.OpenDesktopW("Default", 0, False, 0x01FF)
if h_default:
    user32.SetThreadDesktop(h_default)

class POINT(ctypes.Structure):
    _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ('length', ctypes.c_uint),
        ('flags', ctypes.c_uint),
        ('showCmd', ctypes.c_uint),
        ('ptMinPosition', POINT),
        ('ptMaxPosition', POINT),
        ('rcNormalPosition', RECT)
    ]

mt5_pids = [p.pid for p in psutil.process_iter(['pid', 'name']) if 'terminal' in (p.info['name'] or '').lower()]

def callback(hwnd, extra):
    pid = ctypes.wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in mt5_pids:
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        # Jendela utama biasanya memuat nama broker / nomor akun / simbol
        if ("exness" in title.lower() or "metatrader" in title.lower() or "xauusd" in title.lower()):
            wp = WINDOWPLACEMENT()
            wp.length = ctypes.sizeof(WINDOWPLACEMENT)
            user32.GetWindowPlacement(hwnd, ctypes.byref(wp))
            wp.showCmd = 3 # SW_SHOWMAXIMIZED
            wp.rcNormalPosition.left = 0
            wp.rcNormalPosition.top = 0
            wp.rcNormalPosition.right = 1536
            wp.rcNormalPosition.bottom = 816
            user32.SetWindowPlacement(hwnd, ctypes.byref(wp))
            user32.ShowWindow(hwnd, 9) # SW_RESTORE
            user32.ShowWindow(hwnd, 3) # SW_MAXIMIZE
            user32.SetForegroundWindow(hwnd)
            print(f"✅ Jendela MT5 ditemukan ({title}) dan berhasil dimunculkan ke layar!")
    return True

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumDesktopWindows(h_default, WNDENUMPROC(callback), 0)
