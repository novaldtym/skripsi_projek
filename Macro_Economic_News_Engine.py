import os
import json
import urllib.request
from datetime import datetime, timezone, timedelta

# Lokasi cache kalender ekonomi lokal
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(BASE_DIR, "economic_calendar_cache.json")
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Daftar kata kunci berita berdampak sangat besar (High Impact)
CRITICAL_NEWS_KEYWORDS = [
    "CPI", "CORE CPI", "PPI", "CORE PPI", "NON-FARM", "PAYROLLS", "UNEMPLOYMENT",
    "FOMC", "FED", "INTEREST RATE", "POWELL", "GDP", "RETAIL SALES"
]

_memory_cache = None
_last_fetch_time = None

def fetch_economic_calendar(force_refresh=False):
    """
    Mengambil data kalender ekonomi mingguan dari server feed (ForexFactory JSON API).
    Menggunakan caching lokal (berlaku 4 jam) agar tidak membebani koneksi internet.
    """
    global _memory_cache, _last_fetch_time
    now = datetime.now(timezone.utc)

    # 1. Cek memory cache (jika baru diambil < 1 jam)
    if not force_refresh and _memory_cache is not None and _last_fetch_time is not None:
        if (now - _last_fetch_time).total_seconds() < 3600:
            return _memory_cache

    # 2. Cek disk cache jika ada dan masih segar (< 4 jam)
    if not force_refresh and os.path.exists(CACHE_FILE):
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE), tz=timezone.utc)
            if (now - mod_time).total_seconds() < 14400: # 4 jam
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _memory_cache = json.load(f)
                    _last_fetch_time = now
                    return _memory_cache
        except Exception:
            pass

    # 3. Download data kalender baru via HTTP
    try:
        req = urllib.request.Request(
            CALENDAR_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw_data = resp.read().decode("utf-8")
            data = json.loads(raw_data)
            
            # Simpan ke cache disk
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                f.write(raw_data)
                
            _memory_cache = data
            _last_fetch_time = now
            return data
    except Exception as e:
        # Jika gagal koneksi, coba fallback ke file cache yang ada
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    _memory_cache = json.load(f)
                    return _memory_cache
            except Exception:
                pass
        return []

def get_parsed_usd_events():
    """
    Mengekstrak seluruh berita ekonomi USD berdampak High & Medium dan mengonversi waktu ke UTC datetime.
    """
    raw_events = fetch_economic_calendar()
    parsed = []
    
    for ev in raw_events:
        if ev.get("country") != "USD":
            continue
        impact = ev.get("impact", "")
        if impact not in ["High", "Medium"]:
            continue
            
        date_str = ev.get("date", "")
        if not date_str:
            continue
            
        try:
            # Format contoh: 2026-09-11T08:30:00-04:00
            ev_time = datetime.fromisoformat(date_str)
            # Konversi ke UTC timezone-aware
            ev_time_utc = ev_time.astimezone(timezone.utc)
            
            title = ev.get("title", "")
            is_critical = any(kw in title.upper() for kw in CRITICAL_NEWS_KEYWORDS) or impact == "High"
            
            parsed.append({
                "title": title,
                "country": "USD",
                "impact": impact,
                "is_critical": is_critical,
                "time_utc": ev_time_utc,
                "forecast": ev.get("forecast", ""),
                "previous": ev.get("previous", "")
            })
        except Exception:
            continue
            
    # Urutkan berdasarkan waktu rilis
    parsed.sort(key=lambda x: x["time_utc"])
    return parsed

def check_news_guard(window_before_min=10, window_after_min=15):
    """
    Memeriksa status rilis berita makroekonomi saat ini.
    Returns:
        is_news_freeze (bool): True jika berada di jendela bahaya berita (dilarang entry scalping sembrono).
        news_status_desc (str): Penjelasan status makro saat ini.
        nearest_event (dict): Detail berita terdekat (jika ada).
    """
    events = get_parsed_usd_events()
    now_utc = datetime.now(timezone.utc)
    
    freeze_active = False
    status_desc = "NORMAL: Tidak ada rilis berita High-Impact dalam rentang waktu dekat."
    active_event = None
    
    for ev in events:
        diff_sec = (ev["time_utc"] - now_utc).total_seconds()
        diff_min = diff_sec / 60.0
        
        # 1. Menjelang Berita (Pre-News window): -window_before_min s/d 0
        if 0 <= diff_min <= window_before_min and ev["is_critical"]:
            freeze_active = True
            status_desc = f"🛑 PRE-NEWS FREEZE: Berita {ev['title']} ({ev['impact']}) rilis dalam {int(diff_min)} menit! Dilarang open posisi baru."
            active_event = ev
            break
            
        # 2. Sedang Rilis / Pasca Berita (Post-News window): 0 s/d +window_after_min
        elif -window_after_min <= diff_min < 0 and ev["is_critical"]:
            mins_ago = int(abs(diff_min))
            freeze_active = True
            status_desc = f"⚠️ POST-NEWS VOLATILITY: Berita {ev['title']} baru saja rilis {mins_ago}m lalu! Volatilitas tinggi, dilarang counter-trend."
            active_event = ev
            break
            
        # 3. Info Mendatang (dalam 60 menit) untuk informasi
        elif 0 < diff_min <= 60 and ev["is_critical"]:
            if not active_event:
                status_desc = f"ℹ️ INFO MAKRO: {ev['title']} ({ev['impact']}) rilis dalam {int(diff_min)}m (Forecast: {ev['forecast'] or '-'} | Prev: {ev['previous'] or '-'})."
                active_event = ev

    return freeze_active, status_desc, active_event

if __name__ == "__main__":
    print("="*75)
    print("TESTING ENGINE BERITA MAKROEKONOMI REAL-TIME")
    print("="*75)
    events = get_parsed_usd_events()
    print(f"Total Berita High/Medium USD minggu ini: {len(events)}")
    for e in events[:10]:
        print(f"[{e['time_utc'].strftime('%Y-%m-%d %H:%M UTC')}] [{e['impact']}] {e['title']} | Fcst: {e['forecast']} | Prev: {e['previous']}")
        
    freeze, desc, ev = check_news_guard()
    print(f"\nStatus Guard Saat Ini: Freeze={freeze}")
    print(f"Deskripsi: {desc}")
