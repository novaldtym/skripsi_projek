import os
import sys
import json
import urllib.request
from datetime import datetime, timezone, timedelta

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

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

def compute_macro_features(df_index):
    """
    Menghitung fitur makroekonomi berbasis kalender & proxy untuk time-series candle.
    Digunakan secara konsisten baik pada tahap pelatihan model maupun inferensi live.
    """
    import pandas as pd
    import numpy as np
    
    dates = pd.to_datetime(df_index)
    
    # 1. Is_NFP_Week: Pekan rilis Non-Farm Payrolls (Jumat pertama setiap bulan, aktif Rabu-Jumat)
    is_nfp_week = ((dates.day <= 7) & (dates.dayofweek >= 2) & (dates.dayofweek <= 4)).astype(int)
    
    # 2. Is_CPI_Day: Jendela rilis CPI inflasi AS (tanggal 10 s/d 15 setiap bulan)
    is_cpi_day = ((dates.day >= 10) & (dates.day <= 15) & (dates.dayofweek < 5)).astype(int)
    
    # 3. Is_FOMC_Week: Pekan pengumuman suku bunga The Fed (pertengahan bulan di bulan FOMC)
    fomc_months = [1, 3, 5, 6, 7, 9, 11, 12]
    is_fomc_week = ((dates.day >= 14) & (dates.day <= 22) & (dates.month.isin(fomc_months)) & (dates.dayofweek < 5)).astype(int)
    
    return pd.DataFrame({
        'Is_NFP_Week': is_nfp_week,
        'Is_CPI_Day': is_cpi_day,
        'Is_FOMC_Week': is_fomc_week
    }, index=df_index)

def parse_macro_numeric_value(val_str):
    """
    Mengonversi nilai string kalender ekonomi seperti '16.3K', '3.5%', '-0.5M' menjadi angka float.
    """
    if not val_str or not isinstance(val_str, str):
        return None
    s = val_str.strip().replace('%', '').replace('+', '')
    multiplier = 1.0
    if s.endswith('K') or s.endswith('k'):
        multiplier = 1e3
        s = s[:-1]
    elif s.endswith('M') or s.endswith('m'):
        multiplier = 1e6
        s = s[:-1]
    elif s.endswith('B') or s.endswith('b'):
        multiplier = 1e9
        s = s[:-1]
    try:
        return float(s) * multiplier
    except Exception:
        return None

def get_dynamic_macro_factors(current_time_utc=None):
    """
    Menghitung faktor makroekonomi kuantitatif dinamis secara real-time:
    1. minutes_to_high_news: Hitung mundur menit menuju rilis berita High/Medium-Impact terdekat.
    2. macro_expectation_bias: Arah bias konsensus terhadap EMAS (XAUUSD):
       - +1: Bullish Emas (Ekspektasi ekonomi AS melemah / data negatif bagi Dolar).
       - -1: Bearish Emas (Ekspektasi ekonomi AS menguat / data positif bagi Dolar).
       -  0: Netral atau tidak ada deviasi signifikan.
    3. news_impact_weight: Bobot dampak numerik (High=3, Medium=2, Low=1, None=0).
    4. nearest_event_title: Judul berita terdekat.
    """
    if current_time_utc is None:
        current_time_utc = datetime.now(timezone.utc)
    elif current_time_utc.tzinfo is None:
        current_time_utc = current_time_utc.replace(tzinfo=timezone.utc)

    events = get_parsed_usd_events()
    
    nearest_event = None
    min_diff_sec = 999999999
    
    for ev in events:
        diff_sec = (ev["time_utc"] - current_time_utc).total_seconds()
        # Cari berita mendatang atau yang baru saja rilis (jendela -15m s/d 48 jam ke depan)
        if -900 <= diff_sec <= (48 * 3600):
            if diff_sec >= -900 and abs(diff_sec) < abs(min_diff_sec):
                min_diff_sec = diff_sec
                nearest_event = ev
                
    if not nearest_event:
        return {
            'minutes_to_high_news': 9999.0,
            'macro_expectation_bias': 0,
            'news_impact_weight': 0,
            'nearest_event_title': "None",
            'forecast_str': "-",
            'previous_str': "-"
        }
        
    diff_min = round(min_diff_sec / 60.0, 1)
    impact = nearest_event.get("impact", "Low")
    impact_weight = 3 if impact == "High" else (2 if impact == "Medium" else 1)
    
    # Hitung bias ekspektasi konsensus (Forecast vs Previous)
    fcst_num = parse_macro_numeric_value(nearest_event.get("forecast", ""))
    prev_num = parse_macro_numeric_value(nearest_event.get("previous", ""))
    
    bias = 0
    if fcst_num is not None and prev_num is not None:
        title_upper = nearest_event.get("title", "").upper()
        # Berita pengangguran/klaim tunjangan (Unemployment Rate / Jobless Claims):
        # Angka naik = ekonomi memburuk = Dolar melemah = EMAS NAIK (+1)
        if any(kw in title_upper for kw in ["UNEMPLOYMENT", "JOBLESS", "CLAIMS"]):
            if fcst_num > prev_num:
                bias = 1  # Bullish Emas
            elif fcst_num < prev_num:
                bias = -1 # Bearish Emas
        else:
            # Berita pertumbuhan / tenaga kerja / inflasi umum (NFP, GDP, CPI, PPI, Retail Sales, PMI):
            # Angka naik = ekonomi kuat = Dolar menguat = EMAS TURUN (-1)
            if fcst_num > prev_num:
                bias = -1 # Bearish Emas (USD kuat)
            elif fcst_num < prev_num:
                bias = 1  # Bullish Emas (USD lemah)
                
    return {
        'minutes_to_high_news': diff_min,
        'macro_expectation_bias': bias,
        'news_impact_weight': impact_weight,
        'nearest_event_title': nearest_event.get("title", "Unknown"),
        'forecast_str': nearest_event.get("forecast", "-") or "-",
        'previous_str': nearest_event.get("previous", "-") or "-"
    }

def get_macro_snapshot_for_trade():
    """
    Mengambil snapshot kondisi makroekonomi saat entry posisi untuk pencatatan skenario evaluasi.
    """
    freeze, desc, ev = check_news_guard(window_before_min=30, window_after_min=30)
    factors = get_dynamic_macro_factors()
    now_utc = datetime.now(timezone.utc)
    
    event_title = factors['nearest_event_title']
    impact = ev['impact'] if ev else ("High" if factors['news_impact_weight'] == 3 else "Medium")
    mins_to_event = factors['minutes_to_high_news']
    
    if freeze:
        status_tag = "NEWS_FREEZE_ACTIVE"
    elif abs(mins_to_event) <= 45 and factors['news_impact_weight'] >= 2:
        status_tag = "PRE_NEWS_CAUTION"
    elif abs(mins_to_event) <= 90:
        status_tag = "NEAR_HIGH_IMPACT_NEWS"
    else:
        status_tag = "NORMAL_MARKET"
        
    return {
        'status_tag': status_tag,
        'desc': desc,
        'nearest_event': event_title,
        'event_impact': impact,
        'mins_to_event': mins_to_event,
        'macro_expectation_bias': factors['macro_expectation_bias'],
        'news_impact_weight': factors['news_impact_weight'],
        'forecast': factors['forecast_str'],
        'previous': factors['previous_str']
    }

if __name__ == "__main__":
    print("="*75)
    print("TESTING ENGINE BERITA MAKROEKONOMI REAL-TIME (DENGAN FAKTOR DINAMIS)")
    print("="*75)
    events = get_parsed_usd_events()
    print(f"Total Berita High/Medium USD minggu ini: {len(events)}")
    for e in events[:8]:
        print(f"[{e['time_utc'].strftime('%Y-%m-%d %H:%M UTC')}] [{e['impact']}] {e['title']} | Fcst: {e['forecast']} | Prev: {e['previous']}")
        
    freeze, desc, ev = check_news_guard()
    print(f"\nStatus Guard Saat Ini: Freeze={freeze}")
    print(f"Deskripsi: {desc}")
    
    dyn_factors = get_dynamic_macro_factors()
    print(f"\n📊 Dynamic Macro Factors:")
    print(f"  • Berita Terdekat : {dyn_factors['nearest_event_title']}")
    print(f"  • Hitung Mundur   : {dyn_factors['minutes_to_high_news']} menit")
    print(f"  • Bobot Dampak    : {dyn_factors['news_impact_weight']} (1=Low, 2=Medium, 3=High)")
    print(f"  • Bias Ekspektasi : {dyn_factors['macro_expectation_bias']} (+1=Bullish Gold, -1=Bearish Gold, 0=Neutral)")
    print(f"  • Forecast / Prev : {dyn_factors['forecast_str']} / {dyn_factors['previous_str']}")
    
    snap = get_macro_snapshot_for_trade()
    print(f"\n📸 Macro Trade Snapshot:\n  {snap}")

