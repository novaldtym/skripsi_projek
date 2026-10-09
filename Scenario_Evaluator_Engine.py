import os
import sys
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import MetaTrader5 as mt5

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    openpyxl = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_EVAL_PATH = os.path.join(BASE_DIR, "Evaluasi_Skenario_Trade.xlsx")
CSV_EVAL_PATH   = os.path.join(BASE_DIR, "evaluasi_skenario_trade.csv")
CSV_ML_PATH     = os.path.join(BASE_DIR, "dataset_skenario_ml_retrain.csv")
JSON_SCENARIO_STATS = os.path.join(BASE_DIR, "matriks_performa_skenario.json")

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"

# Ambang Batas Pengujian Skenario
MIN_TESTS_EVALUATION       = 5
MAX_TESTS_BENCHMARK        = 10
WINRATE_AVOID_THRESHOLD    = 40.0
WINRATE_PRIORITY_THRESHOLD = 60.0

# BEP Zone: profit dalam rentang ini dianggap BEP, bukan WIN murni
BEP_MAX_PROFIT = 0.50   # Profit <= $0.50 dianggap BEP zone
BEP_MIN_LOSS   = -0.50  # Loss >= -$0.50 dianggap BEP zone (komisi saja)

# Milestone tracker threshold
MILESTONE_THRESHOLD = 10

_active_entry_context = {}


# ===========================================================================
# HELPER: Ambil harga close candle M15 ke-5 (75 menit setelah entry)
# ===========================================================================

def get_price_at_75min(symbol, open_time_dt, ticket=None):
    """
    Mengambil harga CLOSE & EXCURSION bar M15 yang berakhir ~75 menit setelah waktu open posisi.
    Menggunakan epoch integer timestamps untuk reliabilitas MT5 100%.
    Return dict {'close', 'high', 'low', 'max_high', 'min_low', 'time'} atau None.
    """
    try:
        if not mt5.initialize(path=MT5_PATH):
            if not mt5.initialize():
                return None
        sym = symbol if mt5.symbol_info(symbol) else (
            "XAUUSD" if mt5.symbol_info("XAUUSD") else (
                "XAUUSDm" if mt5.symbol_info("XAUUSDm") else symbol
            )
        )
        
        start_ts = None
        # Prioritas 1: Ambil timestamp deal open asli dari MT5 jika ticket ada
        if ticket:
            try:
                deals = mt5.history_deals_get(position=int(ticket))
                if deals and len(deals) > 0:
                    start_ts = int(deals[0].time)
            except Exception:
                pass
                
        # Prioritas 2: Dari open_time_dt
        if start_ts is None and open_time_dt is not None:
            if isinstance(open_time_dt, datetime):
                start_ts = int(open_time_dt.timestamp())
            elif isinstance(open_time_dt, str):
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%d/%m/%Y %H:%M:%S']:
                    try:
                        start_ts = int(datetime.strptime(open_time_dt, fmt).timestamp())
                        break
                    except Exception:
                        continue

        if start_ts is None:
            return None

        target_ts = start_ts + (75 * 60)
        # Ambil rates dari open hingga 95 menit setelah open
        rates = mt5.copy_rates_range(
            sym, mt5.TIMEFRAME_M15,
            start_ts,
            target_ts + (20 * 60)
        )
        if rates is None or len(rates) == 0:
            return None

        max_high = max(float(r['high']) for r in rates)
        min_low  = min(float(r['low']) for r in rates)
        best = min(rates, key=lambda r: abs(r['time'] - target_ts))
        return {
            'close':    round(float(best['close']), 2),
            'high':     round(float(best['high']),  2),
            'low':      round(float(best['low']),   2),
            'max_high': round(max_high, 2),
            'min_low':  round(min_low, 2),
            'time':     datetime.fromtimestamp(best['time']).strftime('%Y-%m-%d %H:%M')
        }
    except Exception:
        return None


def classify_bep_result(entry_price, trade_type, price_75m_data):
    """
    BEP_REBOUND: harga candle ke-5 (75m) bergerak searah prediksi model,
                 ATAU dalam rentang 75m harga sempat melaju signifikan searah prediksi (>= 5 pips)
                 sebelum retracement ke BEP.
    BEP_NETRAL : harga berbalik atau stagnan tanpa ada momentum searah prediksi.
    """
    if not price_75m_data:
        return 'BEP_NETRAL'
    c75   = price_75m_data.get('close', entry_price)
    max_h = price_75m_data.get('max_high', entry_price)
    min_l = price_75m_data.get('min_low', entry_price)

    is_buy = str(trade_type).upper() == 'BUY'
    if is_buy:
        # Untuk BUY: Jika harga 75m di atas entry, ATAU harga sempat naik >= 5 pips ($0.50)
        if c75 > entry_price or (max_h - entry_price) >= 0.50:
            return 'BEP_REBOUND'
        else:
            return 'BEP_NETRAL'
    else:
        # Untuk SELL: Jika harga 75m di bawah entry, ATAU harga sempat turun >= 5 pips ($0.50)
        if c75 < entry_price or (entry_price - min_l) >= 0.50:
            return 'BEP_REBOUND'
        else:
            return 'BEP_NETRAL'


# ===========================================================================
# ENTRY CONTEXT
# ===========================================================================

def record_entry_context(ticket, symbol, timeframe, scenario_type, setup_details, features_dict=None):
    """Merekam kondisi pasar dan skenario saat bot membuka posisi baru."""
    global _active_entry_context
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ctx = {
        'ticket': int(ticket), 'symbol': symbol, 'timeframe': timeframe,
        'scenario_type': scenario_type, 'entry_time': now_str,
        'setup_details': setup_details, 'features': features_dict or {}
    }
    _active_entry_context[int(ticket)] = ctx
    cache_file = os.path.join(BASE_DIR, "entry_context_cache.json")
    try:
        data = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        data[str(ticket)] = ctx
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def get_entry_context(ticket):
    """Mengambil data konteks entry yang tersimpan saat posisi dibuka."""
    global _active_entry_context
    ticket = int(ticket)
    if ticket in _active_entry_context:
        return _active_entry_context[ticket]
    cache_file = os.path.join(BASE_DIR, "entry_context_cache.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if str(ticket) in data:
                _active_entry_context[ticket] = data[str(ticket)]
                return data[str(ticket)]
        except Exception:
            pass
    return None


# ===========================================================================
# DIAGNOSA DINAMIS — Non-template, setiap kalimat disesuaikan data riil trade
# ===========================================================================

def diagnose_trade_outcome(trade_record, entry_ctx=None, price_75m_data=None):
    """
    Menghasilkan diagnosa kontekstual yang 100% dinamis berdasarkan data riil:
    pips, durasi, harga, tren H4/DXY, probabilitas model, nama skenario, dan candle 75m.
    Empat status: WIN, LOSS, BEP_REBOUND, BEP_NETRAL.
    """
    status       = str(trade_record.get('Hasil', 'UNKNOWN')).upper()
    pnl          = float(trade_record.get('Profit ($ USD)', 0.0))
    pips         = float(trade_record.get('Pips (P/L)', 0.0))
    close_reason = str(trade_record.get('Keterangan / Alasan Exit', ''))
    trade_type   = str(trade_record.get('Tipe', 'BUY')).upper()
    entry_price  = float(trade_record.get('Harga Entry', 0.0))
    exit_price   = float(trade_record.get('Harga Exit', 0.0))
    sl_price     = float(trade_record.get('Stop Loss (SL)', 0.0))
    tp_price     = float(trade_record.get('Take Profit (TP)', 0.0))
    durasi_str   = str(trade_record.get('Durasi', '—'))

    ctx       = entry_ctx or {}
    setup     = ctx.get('setup_details', {})
    scenario  = ctx.get('scenario_type', 'GENERAL_ENTRY')
    macro_info = setup.get('macro_news', 'NORMAL')
    h4_trend  = setup.get('h4_trend', 'UNKNOWN')
    dxy_trend = setup.get('dxy_trend', 'UNKNOWN')
    prob      = float(setup.get('model_prob', 50.0))
    zone      = setup.get('zone', 'ZONA_UNKNOWN')

    aligned_h4 = (
        (trade_type == 'BUY'  and h4_trend in ['BULL', 'BULLISH', 'NAIK']) or
        (trade_type == 'SELL' and h4_trend in ['BEAR', 'BEARISH', 'TURUN'])
    )
    against_h4 = (
        (trade_type == 'BUY'  and h4_trend in ['BEAR', 'BEARISH', 'TURUN']) or
        (trade_type == 'SELL' and h4_trend in ['BULL', 'BULLISH', 'NAIK'])
    )
    aligned_dxy = (
        (trade_type == 'BUY'  and dxy_trend in ['BEAR', 'BEARISH', 'LEMAH']) or
        (trade_type == 'SELL' and dxy_trend in ['BULL', 'BULLISH', 'KUAT'])
    )
    sl_pips = abs(entry_price - sl_price) * 10.0 if sl_price > 0 else 0.0

    close_75m_price = price_75m_data.get('close') if price_75m_data else None
    close_75m_time  = price_75m_data.get('time', '75m setelah entry') if price_75m_data else '75m setelah entry'

    def pfmt(v): return f"${v:.2f}"
    def pipsfmt(v): return f"{v:+.1f} pip"

    # ── WIN: Profit murni di atas BEP zone ──────────────────────────────────
    if status == 'WIN':
        parts = []
        cr = close_reason.lower()
        if 'tp' in cr or 'take profit' in cr:
            parts.append(
                f"Target Take Profit (TP) {pfmt(tp_price)} tercapai penuh"
                + (f" dalam {durasi_str}" if durasi_str != '—' else '')
            )
        elif 'trailing' in cr:
            parts.append(
                f"Trailing profit lock berhasil mengamankan {pipsfmt(pips)} "
                f"(exit di {pfmt(exit_price)}) sebelum harga berbalik"
            )
        elif 'scalp tp' in cr:
            parts.append(
                f"Dynamic scalp TP tersentuh — exit cepat di {pfmt(exit_price)} "
                f"({pipsfmt(pips)} dari entry)"
            )
        else:
            parts.append(
                f"Posisi ditutup profit {pfmt(pnl)} di {pfmt(exit_price)} "
                f"({pipsfmt(pips)} dari entry {pfmt(entry_price)})"
            )
        if aligned_h4:
            parts.append(f"Entry searah tren H4 ({h4_trend}) — konfluensi institusional mendukung momentum")
        if aligned_dxy:
            parts.append(f"Korelasi invers DXY ({dxy_trend}) memperkuat tekanan harga emas")
        if 'ZONA_A' in scenario or 'DEMAND' in scenario or 'SNIPER' in scenario:
            parts.append(f"Entry presisi dari area kunci skenario '{scenario}' — model tervalidasi akurat")
        if prob >= 65.0:
            parts.append(f"Keyakinan model tinggi ({prob:.1f}%) — threshold confidence terpenuhi optimal")

        if close_75m_price is not None and entry_price > 0:
            if trade_type == 'BUY':
                selaras_75m = close_75m_price > entry_price
                delta_75m = (close_75m_price - entry_price) * 10.0
            else:
                selaras_75m = close_75m_price < entry_price
                delta_75m = (entry_price - close_75m_price) * 10.0
            if selaras_75m:
                parts.append(f"Validasi Model 75M: SELARAS BERHASIL (Close bar-5: {pfmt(close_75m_price)}, deviasi {delta_75m:+.1f} pip searah {trade_type})")
            else:
                parts.append(f"Validasi Model 75M: TIDAK SELARAS (Close bar-5: {pfmt(close_75m_price)}, pembalikan {abs(delta_75m):.1f} pip)")

        diag_text = "✅ [WIN — Kemenangan Target]: " + " | ".join(parts) + "."
        lesson_learned = (
            f"Skenario {scenario} terbukti valid (H4={h4_trend}, DXY={dxy_trend}). "
            "Pertahankan konfluensi multi-timeframe dan disiplin hold hingga TP."
        )

    # ── LOSS: Kerugian riil ──────────────────────────────────────────────────
    elif status == 'LOSS':
        parts = []
        cr = close_reason.lower()
        if 'sl' in cr or 'stop loss' in cr:
            parts.append(
                f"Stop Loss {pfmt(sl_price)} tersentuh — harga bergerak {abs(pips):.1f} pip melawan posisi"
                + (f" dalam {durasi_str}" if durasi_str != '—' else '')
            )
        elif 'cut-loss' in cr or 'reversal' in cr or 'invalidation' in cr:
            parts.append(
                f"AI Early Cut-Loss diaktifkan di {pfmt(exit_price)} — "
                "sinyal pembalikan arah terdeteksi sebelum SL penuh tersentuh"
            )
        else:
            parts.append(
                f"Posisi ditutup rugi {pfmt(pnl)} di {pfmt(exit_price)} "
                f"({pipsfmt(pips)} dari entry {pfmt(entry_price)})"
            )
        if against_h4:
            parts.append(
                f"KESALAHAN KONFLUENSI: Entry {trade_type} saat H4 menunjukkan tren {h4_trend} "
                "(melawan tren institusional)"
            )
        if sl_pips < 30.0 and sl_pips > 0:
            parts.append(f"SL terlalu tipis ({sl_pips:.1f} pip) — rentan tersapu wick noise lilin emas")
        if any(x in macro_info.upper() for x in ['FREEZE', 'NEAR', 'NFP', 'CPI']):
            parts.append(f"Volatilitas makroekonomi ({macro_info}) kemungkinan membalik sentimen")
        if prob < 60.0:
            parts.append(f"Keyakinan model di batas bawah ({prob:.1f}%) — entry berisiko tanpa konfluensi penuh")
        if len(parts) < 2:
            parts.append(f"Momentum pasar tidak melanjutkan prediksi model pada skenario {scenario}")

        diag_text = "❌ [LOSS — Analisis Kesalahan]: " + " | ".join(parts) + "."
        lesson_learned = (
            f"Untuk skenario {scenario}: Pastikan konfluensi H4 searah sebelum entry. "
            "SL minimal 35-50 pip dari entry. Hindari entry jika probabilitas model < 62%."
        )

    # ── BEP REBOUND: BEP tersentuh, arah prediksi model terbukti benar ──────
    elif status == 'BEP_REBOUND':
        delta_75m = 0.0
        dir_desc = "data tidak tersedia"
        if close_75m_price and entry_price > 0:
            delta_75m = abs(close_75m_price - entry_price) * 10.0
            if trade_type == 'BUY':
                dir_desc = f"close {pfmt(close_75m_price)} (di ATAS entry {pfmt(entry_price)}, +{delta_75m:.1f} pip)"
            else:
                dir_desc = f"close {pfmt(close_75m_price)} (di BAWAH entry {pfmt(entry_price)}, +{delta_75m:.1f} pip)"

        parts = [
            f"Posisi terkena Auto Break-Even (+{pnl:.2f}) akibat proteksi BEP, "
            f"namun PREDIKSI MODEL TERBUKTI VALID: pada candle ke-5 ({close_75m_time}), "
            f"harga {dir_desc}"
        ]
        if aligned_h4:
            parts.append(f"Tren H4 ({h4_trend}) mendukung prediksi — volatilitas sementara menyentuh BEP, bukan kegagalan model")
        if 'trailing' in close_reason.lower():
            parts.append("Trailing lock mengamankan modal sebelum retracement sesaat; harga melanjutkan arah")
        parts.append(f"Skenario '{scenario}' secara ARAH dinilai BERHASIL meski exit lebih awal karena BEP")

        diag_text = "🔄 [BEP REBOUND — Berhasil Arah, Exit Dini]: " + " | ".join(parts) + "."
        lesson_learned = (
            f"Model prediksi AKURAT secara arah pada skenario {scenario}. "
            "Pertimbangkan SL sedikit lebih lebar agar BEP tidak aktif terlalu dini "
            "pada kondisi volatile yang tetap bearah prediksi."
        )

    # ── BEP NETRAL: BEP menyelamatkan, harga memang berbalik melawan prediksi ─
    elif status == 'BEP_NETRAL':
        delta_75m = 0.0
        dir_desc = "data tidak tersedia"
        if close_75m_price and entry_price > 0:
            delta_75m = abs(close_75m_price - entry_price) * 10.0
            if trade_type == 'BUY':
                dir_desc = f"close {pfmt(close_75m_price)} (di BAWAH entry {pfmt(entry_price)}, -{delta_75m:.1f} pip)"
            else:
                dir_desc = f"close {pfmt(close_75m_price)} (di ATAS entry {pfmt(entry_price)}, -{delta_75m:.1f} pip)"

        parts = [
            f"Auto Break-Even (+{pnl:.2f}) MENYELAMATKAN dari potensi kerugian: "
            f"pada candle ke-5 ({close_75m_time}), harga {dir_desc} "
            f"— berlawanan dengan prediksi model"
        ]
        if against_h4:
            parts.append(
                f"Tren H4 ({h4_trend}) berlawanan dengan arah entry ({trade_type}) — "
                "model mungkin membaca momentum jangka pendek yang tidak bertahan"
            )
        if any(x in macro_info.upper() for x in ['NEAR', 'FREEZE', 'NFP']):
            parts.append(f"Kondisi makro ({macro_info}) kemungkinan membalik sentimen setelah entry")
        parts.append(f"Fitur Auto-BEP berfungsi optimal sebagai shield pelindung modal — skenario {scenario}")

        diag_text = "🛡️ [BEP NETRAL — Penyelamat Modal, Arah Gagal]: " + " | ".join(parts) + "."
        lesson_learned = (
            f"Pada skenario {scenario}, prediksi model tidak terkonfirmasi dalam 75 menit. "
            "Evaluasi kondisi masuk: pastikan momentum H4 lebih kuat. "
            "Auto-BEP berhasil melindungi modal dari kerugian yang lebih besar."
        )

    # ── FALLBACK ─────────────────────────────────────────────────────────────
    else:
        diag_text = (
            f"⚪ [BEP — Impas]: Posisi ditutup pada break-even (profit {pfmt(pnl)}). "
            f"Exit di {pfmt(exit_price)} dari entry {pfmt(entry_price)}."
        )
        lesson_learned = "Posisi diamankan ke BEP tanpa kerugian finansial."

    return {
        'scenario':         scenario,
        'diagnostic_text':  diag_text,
        'lesson_learned':   lesson_learned,
        'h4_trend':         h4_trend,
        'dxy_trend':        dxy_trend,
        'macro_info':       macro_info,
        'zone':             zone,
        'model_prob':       prob,
        'close_75m':        close_75m_price if 'close_75m_price' in dir() else None
    }


# ===========================================================================
# EVALUASI & PENCATATAN TRADE
# ===========================================================================

def evaluate_and_record_trade(trade_record, orders_history=None, sync_excel=True):
    """
    Mencatat hasil trade dengan klasifikasi baru (WIN/LOSS/BEP_REBOUND/BEP_NETRAL),
    menjalankan diagnosa dinamis non-template, memperbarui matriks skenario,
    dan menyimpan ke Excel dan CSV.
    """
    ticket_raw = trade_record.get('Ticket Posisi', 0)
    ticket = str(ticket_raw).strip()
    if not ticket or ticket in ['0', 'None', 'nan', '']:
        return None

    pnl = float(trade_record.get('Profit ($ USD)', 0.0))
    close_reason_low = str(trade_record.get('Keterangan / Alasan Exit', '')).lower()
    is_bep_exit = ('break-even' in close_reason_low or ' be' in close_reason_low
                   or 'bep' in close_reason_low or 'trailing' in close_reason_low
                   or ('sl' in close_reason_low and abs(pnl) <= BEP_MAX_PROFIT))

    # Klasifikasi status berdasarkan PnL riil dan alasan exit
    if is_bep_exit and abs(pnl) <= BEP_MAX_PROFIT:
        classified_status = 'BEP_PENDING'
    elif pnl > BEP_MAX_PROFIT:
        classified_status = 'WIN'
    elif pnl < BEP_MIN_LOSS:
        classified_status = 'LOSS'
    else:
        classified_status = 'BEP_PENDING'

    # Fast-path deduplikasi: lewati HANYA jika sudah dievaluasi dengan status final
    if os.path.exists(CSV_EVAL_PATH):
        try:
            df_old_check = pd.read_csv(CSV_EVAL_PATH)
            if 'Ticket Posisi' in df_old_check.columns:
                existing = df_old_check['Ticket Posisi'].dropna().astype(str).str.strip().values
                if ticket in existing:
                    match = df_old_check[df_old_check['Ticket Posisi'].astype(str).str.strip() == ticket]
                    if len(match) > 0:
                        old_status = str(match.iloc[-1].get('Hasil', '')).upper()
                        old_pnl = float(match.iloc[-1].get('Profit ($ USD)', 0.0))
                        old_diag = str(match.iloc[-1].get('Analisis Diagnostik (Menang/Kalah)', ''))
                        has_75m = ('Validasi Model 75M' in match.iloc[-1]) and pd.notna(match.iloc[-1].get('Close Candle 75m ($)'))
                        if has_75m:
                            # Jika sudah memiliki diagnosa v2.0 definitif dan evaluasi 75m
                            if old_status in ['BEP_REBOUND', 'BEP_NETRAL'] and 'Exit profit positif' not in old_diag:
                                return None
                            if old_status == 'WIN' and old_pnl > BEP_MAX_PROFIT and 'Exit profit positif' not in old_diag:
                                return None
                            if old_status == 'LOSS' and old_pnl < BEP_MIN_LOSS:
                                return None
        except Exception:
            pass

    # Evaluasi candle ke-5 (75m horizon) untuk validasi arah model murni (WIN, LOSS, maupun BEP)
    symbol = str(trade_record.get('Simbol', 'XAUUSDm'))
    open_time_str = str(trade_record.get('Waktu Open', ''))
    open_time_dt = None
    for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M']:
        try:
            open_time_dt = datetime.strptime(open_time_str, fmt)
            break
        except Exception:
            continue

    price_75m_data = get_price_at_75min(symbol, open_time_dt, ticket=ticket)
    entry_price = float(trade_record.get('Harga Entry', 0.0))
    trade_type  = str(trade_record.get('Tipe', 'BUY')).upper()

    if classified_status == 'BEP_PENDING':
        classified_status = classify_bep_result(entry_price, trade_type, price_75m_data)

    trade_record['Hasil'] = classified_status

    # Hitung validasi arah murni model 75 menit (5 candle)
    c75 = price_75m_data.get('close') if price_75m_data else None
    status_75m = 'MENUNGGU (BELUM 75M)'
    pips_75m = 0.0
    if c75 is not None and entry_price > 0:
        if trade_type == 'BUY':
            selaras_75m = c75 > entry_price
            pips_75m = (c75 - entry_price) * 10.0
        else:
            selaras_75m = c75 < entry_price
            pips_75m = (entry_price - c75) * 10.0
        status_75m = "BERHASIL (SELARAS)" if selaras_75m else "GAGAL (TIDAK SELARAS)"

    entry_ctx = get_entry_context(ticket)
    diag = diagnose_trade_outcome(trade_record, entry_ctx, price_75m_data)

    # Gabungkan data lengkap
    record_full = dict(trade_record)
    record_full['Ticket Posisi']                      = ticket
    record_full['Hasil']                              = classified_status
    record_full['Skenario Entry']                     = diag['scenario']
    record_full['Zona Entry']                         = diag['zone']
    record_full['Tren H4 Entry']                      = diag['h4_trend']
    record_full['Tren DXY Entry']                     = diag['dxy_trend']
    record_full['Kondisi Makro News']                 = diag['macro_info']
    record_full['Probabilitas Model (%)']             = diag['model_prob']
    record_full['Close Candle 75m ($)']               = c75
    record_full['Validasi Model 75M']                 = status_75m
    record_full['Pips Model 75M']                     = round(pips_75m, 1)
    record_full['Analisis Diagnostik (Menang/Kalah)'] = diag['diagnostic_text']
    record_full['Evaluasi & Pembelajaran']            = diag['lesson_learned']
    record_full['Tanggal Evaluasi']                   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Simpan ke CSV
    df_new = pd.DataFrame([record_full])
    if os.path.exists(CSV_EVAL_PATH):
        try:
            df_old = pd.read_csv(CSV_EVAL_PATH)
            df_old['Ticket Posisi'] = df_old['Ticket Posisi'].astype(str).str.strip()
            if ticket not in df_old['Ticket Posisi'].values:
                pd.concat([df_old, df_new], ignore_index=True).to_csv(CSV_EVAL_PATH, index=False)
            else:
                idx = df_old.index[df_old['Ticket Posisi'] == ticket]
                for col in df_new.columns:
                    if col not in df_old.columns:
                        df_old[col] = None
                    df_old.loc[idx, col] = df_new.iloc[0][col]
                df_old.to_csv(CSV_EVAL_PATH, index=False)
        except Exception:
            df_new.to_csv(CSV_EVAL_PATH, index=False)
    else:
        df_new.to_csv(CSV_EVAL_PATH, index=False)

    # 2. Dataset retraining ML
    if entry_ctx and 'features' in entry_ctx and len(entry_ctx['features']) > 0:
        ml_row = dict(entry_ctx['features'])
        ml_row['Ticket']         = ticket
        ml_row['Outcome_Target'] = 1 if classified_status in ['WIN', 'BEP_REBOUND'] else 0
        ml_row['Profit_USD']     = pnl
        ml_row['Scenario']       = diag['scenario']
        ml_row['Time']           = trade_record.get('Waktu Close', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        df_ml = pd.DataFrame([ml_row])
        if os.path.exists(CSV_ML_PATH):
            try:
                df_ml_old = pd.read_csv(CSV_ML_PATH)
                df_ml_old['Ticket'] = df_ml_old['Ticket'].astype(str).str.strip()
                if ticket not in df_ml_old['Ticket'].values:
                    pd.concat([df_ml_old, df_ml], ignore_index=True).to_csv(CSV_ML_PATH, index=False)
            except Exception:
                df_ml.to_csv(CSV_ML_PATH, index=False)
        else:
            df_ml.to_csv(CSV_ML_PATH, index=False)

    # 3. Update matriks + milestone tracker
    update_scenario_performance_matrix()

    # 4. Sync ke Excel jika diminta
    if sync_excel:
        sync_scenario_evaluation_to_excel()

    return record_full


# ===========================================================================
# MATRIKS PERFORMA SKENARIO + MILESTONE TRACKER 10x
# ===========================================================================

def update_scenario_performance_matrix():
    """
    Mengelompokkan riwayat trade berdasarkan skenario.
    Win Rate Efektif = (WIN + BEP_REBOUND) / Total.
    Milestone 10x: badge ANDAL (>= 10 win valid) atau RETRAIN (>= 10 loss).
    """
    if not os.path.exists(CSV_EVAL_PATH):
        return pd.DataFrame()
    try:
        df = pd.read_csv(CSV_EVAL_PATH)
    except Exception:
        return pd.DataFrame()
    if len(df) == 0 or 'Skenario Entry' not in df.columns:
        return pd.DataFrame()

    summary_list = []
    matrix_dict  = {}
    grouped = df.groupby('Skenario Entry')

    for scenario_name, group in grouped:
        total_tested = len(group)
        wins_murni   = len(group[group['Hasil'] == 'WIN'])
        losses       = len(group[group['Hasil'] == 'LOSS'])
        bep_rebound  = len(group[group['Hasil'] == 'BEP_REBOUND'])
        bep_netral   = len(group[group['Hasil'] == 'BEP_NETRAL'])
        bep_old      = len(group[~group['Hasil'].isin(['WIN', 'LOSS', 'BEP_REBOUND', 'BEP_NETRAL'])])

        wins_efektif = wins_murni + bep_rebound
        win_rate     = (wins_efektif / total_tested * 100.0) if total_tested > 0 else 0.0
        total_pnl    = round(float(group['Profit ($ USD)'].sum()), 2)
        avg_pnl      = round(float(group['Profit ($ USD)'].mean()), 2)

        # Milestone 10x
        milestone_win  = wins_efektif >= MILESTONE_THRESHOLD
        milestone_loss = losses >= MILESTONE_THRESHOLD
        milestone_label = ""
        if milestone_win:
            milestone_label = f"🌟 ANDAL (>={MILESTONE_THRESHOLD}x Win Valid)"
        elif milestone_loss:
            milestone_label = f"⚠️ RETRAIN DIPERLUKAN (>={MILESTONE_THRESHOLD}x Loss)"

        # Status skenario
        if total_tested >= MIN_TESTS_EVALUATION:
            if win_rate >= WINRATE_PRIORITY_THRESHOLD and total_pnl > 0:
                status_skenario = "🌟 SKENARIO UNGGULAN (Rekomendasi Entry)"
                action = "ALLOW_AND_BOOST"
            elif win_rate < WINRATE_AVOID_THRESHOLD or total_pnl < -10.0:
                status_skenario = "⛔ SKENARIO DIHINDARI (Banyak Loss / Dilarang)"
                action = "BLACKLIST_AVOID"
            else:
                status_skenario = "⚖️ SKENARIO NETRAL (Pertimbangan Ketat)"
                action = "ALLOW_STRICT"
        else:
            status_skenario = f"⏳ DALAM PENGUJIAN ({total_tested}/{MIN_TESTS_EVALUATION} Trade)"
            action = "ALLOW_TESTING"

        win_progress  = f"[{wins_efektif}/{MILESTONE_THRESHOLD} Win]"
        loss_progress = f"[{losses}/{MILESTONE_THRESHOLD} Loss]"

        summary_list.append({
            'Skenario Entry':             scenario_name,
            'Total Diuji':                total_tested,
            'Menang Murni (WIN)':         wins_murni,
            'BEP Rebound (Arah Valid)':   bep_rebound,
            'BEP Netral (Shield)':        bep_netral,
            'Kalah (LOSS)':               losses,
            'Win Rate Efektif (%)':       round(win_rate, 1),
            'Total PnL ($ USD)':          total_pnl,
            'Rata-rata PnL ($)':          avg_pnl,
            'Tracker Win 10x':            win_progress,
            'Tracker Loss 10x':           loss_progress,
            'Milestone':                  milestone_label,
            'Status Evaluasi Skenario':   status_skenario,
            'Tindakan Bot':               action
        })
        matrix_dict[scenario_name] = {
            'total_tested':    total_tested,
            'wins_murni':      wins_murni,
            'bep_rebound':     bep_rebound,
            'bep_netral':      bep_netral,
            'losses':          losses,
            'wins_efektif':    wins_efektif,
            'win_rate':        round(win_rate, 1),
            'total_pnl':       total_pnl,
            'milestone_win':   milestone_win,
            'milestone_loss':  milestone_loss,
            'milestone_label': milestone_label,
            'status':          status_skenario,
            'action':          action
        }

    matrix_df = pd.DataFrame(summary_list)
    if len(matrix_df) > 0:
        matrix_df.sort_values(by=['Total Diuji', 'Win Rate Efektif (%)'], ascending=[False, False], inplace=True)

    try:
        with open(JSON_SCENARIO_STATS, "w", encoding="utf-8") as f:
            json.dump(matrix_dict, f, indent=2)
    except Exception:
        pass
    return matrix_df


def can_trade_scenario(scenario_name, timeframe="M15", context=None):
    """
    Guard untuk Bot Live: memeriksa apakah skenario diizinkan atau dihindari.
    """
    if not os.path.exists(JSON_SCENARIO_STATS):
        return True, "OK: Skenario belum memiliki riwayat evaluasi (Boleh diuji)."
    try:
        with open(JSON_SCENARIO_STATS, "r", encoding="utf-8") as f:
            matrix = json.load(f)
        if scenario_name in matrix:
            sc_info = matrix[scenario_name]
            if sc_info.get('action') == "BLACKLIST_AVOID":
                wr  = sc_info.get('win_rate', 0.0)
                n   = sc_info.get('total_tested', 0)
                pnl = sc_info.get('total_pnl', 0.0)
                ml  = sc_info.get('milestone_label', '')
                return False, (
                    f"⛔ SKENARIO DIHINDARI: '{scenario_name}' Win Rate rendah "
                    f"({wr}% dari {n} uji, Net PnL: ${pnl:.2f}). {ml} Entry dibatalkan."
                )
            elif sc_info.get('action') == "ALLOW_AND_BOOST":
                wr = sc_info.get('win_rate', 0.0)
                n  = sc_info.get('total_tested', 0)
                ml = sc_info.get('milestone_label', '')
                return True, f"🌟 SKENARIO UNGGULAN: '{scenario_name}' ({wr}% Win Rate dari {n} uji). {ml}"
    except Exception:
        pass
    return True, "OK: Skenario diizinkan dieksekusi."


# ===========================================================================
# SYNC KE EXCEL
# ===========================================================================

def sync_scenario_evaluation_to_excel():
    """
    Menyinkronkan seluruh riwayat evaluasi dan matriks skenario ke Excel.
    Sheet 1: Matriks Evaluasi + Milestone Tracker 10x.
    Sheet 2: Log Rinci Per Trade dengan color-coding 4 status baru.
    """
    if openpyxl is None:
        return
    if not os.path.exists(CSV_EVAL_PATH):
        return
    try:
        df_eval = pd.read_csv(CSV_EVAL_PATH)
    except Exception:
        return

    matrix_df = update_scenario_performance_matrix()
    wb = openpyxl.Workbook()

    navy_fill   = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    gold_fill   = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
    green_fill  = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    red_fill    = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    blue_fill   = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
    orange_fill = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
    gray_fill   = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")

    header_font  = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font   = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    regular_font = Font(name="Calibri", size=10)
    thin_border  = Border(
        left=Side(style='thin',   color='D1D5DB'), right=Side(style='thin',  color='D1D5DB'),
        top=Side(style='thin',    color='D1D5DB'), bottom=Side(style='thin', color='D1D5DB')
    )

    # ── Sheet 1: Matriks Evaluasi Skenario ──────────────────────────────────
    ws_matrix = wb.active
    ws_matrix.title = "Matriks Evaluasi Skenario"
    ws_matrix["A1"] = "📊 MATRIKS EVALUASI PERFORMA SKENARIO (BEP 75m + Tracker WIN/LOSS 10x)"
    ws_matrix["A1"].font = title_font
    ws_matrix["A2"] = ("WIN Efektif = WIN Murni + BEP Rebound (arah prediksi terbukti). "
                       "Milestone 10x: 🌟 ANDAL atau ⚠️ RETRAIN DIPERLUKAN.")
    ws_matrix["A2"].font = Font(name="Calibri", size=10, italic=True, color="6B7280")

    if len(matrix_df) > 0:
        headers = list(matrix_df.columns)
        for c_idx, col in enumerate(headers, 1):
            cell = ws_matrix.cell(row=4, column=c_idx, value=col)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        font_unggul = Font(name="Calibri", size=10, bold=True, color="15803D")
        font_hindar = Font(name="Calibri", size=10, bold=True, color="B91C1C")
        font_andal  = Font(name="Calibri", size=10, bold=True, color="1D4ED8")
        font_retrain= Font(name="Calibri", size=10, bold=True, color="DC2626")

        for r_idx, row in matrix_df.iterrows():
            cur_row = 5 + r_idx
            for c_idx, val in enumerate(row, 1):
                cell = ws_matrix.cell(row=cur_row, column=c_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                cell.alignment = Alignment(
                    horizontal="center" if c_idx in [2,3,4,5,6,7,8] else "left",
                    vertical="center"
                )
                val_str = str(val)
                if "UNGGULAN" in val_str:
                    cell.fill = green_fill; cell.font = font_unggul
                elif "DIHINDARI" in val_str:
                    cell.fill = red_fill;   cell.font = font_hindar
                elif "ANDAL" in val_str:
                    cell.fill = blue_fill;  cell.font = font_andal
                elif "RETRAIN" in val_str:
                    cell.fill = orange_fill; cell.font = font_retrain
                elif "PENGUJIAN" in val_str:
                    cell.fill = gray_fill

        ws_matrix.row_dimensions[4].height = 30
        for col in ws_matrix.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            ws_matrix.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 3, 14)

    # ── Sheet 2: Log Rinci Per Trade ─────────────────────────────────────────
    ws_log = wb.create_sheet(title="Log Rinci Evaluasi Trade")
    ws_log["A1"] = "📝 LOG ANALISIS MENDALAM PER TRADE (WIN / LOSS / BEP REBOUND / BEP NETRAL)"
    ws_log["A1"].font = title_font
    ws_log["A2"] = "Diagnosa dinamis kontekstual: evaluasi candle ke-5 (75m), tren H4/DXY, makroekonomi, milestone tracker 10x."
    ws_log["A2"].font = Font(name="Calibri", size=10, italic=True, color="6B7280")

    if len(df_eval) > 0:
        log_headers = list(df_eval.columns)
        for c_idx, col in enumerate(log_headers, 1):
            cell = ws_log.cell(row=4, column=c_idx, value=col)
            cell.fill = gold_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        STATUS_STYLES = {
            'WIN':         (green_fill,  Font(name="Calibri", size=10, bold=True, color="15803D")),
            'LOSS':        (red_fill,    Font(name="Calibri", size=10, bold=True, color="B91C1C")),
            'BEP_REBOUND': (blue_fill,   Font(name="Calibri", size=10, bold=True, color="1D4ED8")),
            'BEP_NETRAL':  (gray_fill,   Font(name="Calibri", size=10, bold=True, color="6B7280")),
        }

        df_display = df_eval.tail(200) if len(df_eval) > 200 else df_eval
        for r_idx, (_, row) in enumerate(df_display.iterrows()):
            cur_row = 5 + r_idx
            for c_idx, val in enumerate(row, 1):
                cell = ws_log.cell(row=cur_row, column=c_idx, value=val)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                val_str = str(val)
                if val_str in STATUS_STYLES:
                    st_fill, st_font = STATUS_STYLES[val_str]
                    cell.fill = st_fill; cell.font = st_font
                else:
                    cell.font = regular_font

        ws_log.row_dimensions[4].height = 30
        for col in ws_log.columns:
            max_len = max(len(str(c.value or '')) for c in col)
            ws_log.column_dimensions[get_column_letter(col[0].column)].width = min(max(max_len + 3, 14), 55)

    try:
        wb.save(EXCEL_EVAL_PATH)
    except Exception:
        pass


# ===========================================================================
# MAIN TEST
# ===========================================================================

if __name__ == "__main__":
    print("="*80)
    print("TESTING SCENARIO EVALUATOR ENGINE v2.0 (BEP 75m + Milestone 10x)")
    print("="*80)

    dummy_win = {
        'Ticket Posisi': 990001,
        'Waktu Open': '2026-09-15 10:00:00',
        'Waktu Close': '2026-09-15 10:45:00',
        'Durasi': '45m 0d',
        'Simbol': 'XAUUSDm',
        'Tipe': 'BUY',
        'Lot': 0.01,
        'Harga Entry': 4410.50,
        'Stop Loss (SL)': 4404.00,
        'Take Profit (TP)': 4424.00,
        'Harga Exit': 4424.00,
        'Pips (P/L)': 135.0,
        'Profit ($ USD)': 13.50,
        'Hasil': 'WIN',
        'Keterangan / Alasan Exit': 'Hit Take Profit (TP)',
        'Model AI': 'LightGBM M15 v4.1',
        'Timeframe': 'M15'
    }
    dummy_bep = {
        'Ticket Posisi': 990002,
        'Waktu Open': '2026-09-15 12:00:00',
        'Waktu Close': '2026-09-15 12:18:00',
        'Durasi': '18m 0d',
        'Simbol': 'XAUUSDm',
        'Tipe': 'BUY',
        'Lot': 0.01,
        'Harga Entry': 4415.00,
        'Stop Loss (SL)': 4408.50,
        'Take Profit (TP)': 4428.00,
        'Harga Exit': 4415.02,
        'Pips (P/L)': 0.2,
        'Profit ($ USD)': 0.20,
        'Hasil': 'BEP',
        'Keterangan / Alasan Exit': 'Hit Break-Even',
        'Model AI': 'LightGBM M15 v4.1',
        'Timeframe': 'M15'
    }

    record_entry_context(
        ticket=990001, symbol="XAUUSDm", timeframe="M15",
        scenario_type="M15_ZONA_A_Demand_BUY",
        setup_details={'macro_news': 'NORMAL', 'h4_trend': 'BULL', 'dxy_trend': 'BEAR',
                       'model_prob': 67.5, 'zone': 'Zona A'}
    )
    record_entry_context(
        ticket=990002, symbol="XAUUSDm", timeframe="M15",
        scenario_type="M15_ZONA_B_BUY",
        setup_details={'macro_news': 'NORMAL', 'h4_trend': 'BULL', 'dxy_trend': 'BEAR',
                       'model_prob': 63.2, 'zone': 'Zona B'}
    )

    res_win = evaluate_and_record_trade(dummy_win, sync_excel=False)
    print(f"\nDiagnosa WIN:\n{res_win['Analisis Diagnostik (Menang/Kalah)']}\n{res_win['Evaluasi & Pembelajaran']}")

    res_bep = evaluate_and_record_trade(dummy_bep, sync_excel=False)
    print(f"\nDiagnosa BEP (75m check):\n{res_bep['Analisis Diagnostik (Menang/Kalah)']}")
    print(f"Status akhir: {res_bep['Hasil']}")

    sync_scenario_evaluation_to_excel()
    can_tr, msg = can_trade_scenario("M15_ZONA_A_Demand_BUY")
    print(f"\nStatus Skenario: can_trade={can_tr} | {msg}")
    print("="*80)
    print("✅ Testing Scenario Evaluator Engine v2.0 Berhasil!")
