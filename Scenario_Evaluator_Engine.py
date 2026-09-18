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
CSV_EVAL_PATH = os.path.join(BASE_DIR, "evaluasi_skenario_trade.csv")
CSV_ML_PATH = os.path.join(BASE_DIR, "dataset_skenario_ml_retrain.csv")
JSON_SCENARIO_STATS = os.path.join(BASE_DIR, "matriks_performa_skenario.json")

# Ambang Batas Pengujian Skenario (5 - 10 kali pengujian)
MIN_TESTS_EVALUATION = 5      # Minimal 5x uji sebelum skenario dinilai valid
MAX_TESTS_BENCHMARK  = 10     # Target 10x uji skenario
WINRATE_AVOID_THRESHOLD = 40.0   # Win Rate < 40% setelah >= 5x uji -> DILARANG / HINDARI
WINRATE_PRIORITY_THRESHOLD = 60.0 # Win Rate >= 60% setelah >= 5x uji -> PRIORITAS UNGGULAN

_active_entry_context = {}


def record_entry_context(ticket, symbol, timeframe, scenario_type, setup_details, features_dict=None):
    """
    Merekam kondisi pasar dan skenario saat bot membuka posisi baru.
    Disimpan dalam memory cache dan file temp agar tidak hilang jika bot restart.
    """
    global _active_entry_context
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    ctx = {
        'ticket': int(ticket),
        'symbol': symbol,
        'timeframe': timeframe,
        'scenario_type': scenario_type,
        'entry_time': now_str,
        'setup_details': setup_details,
        'features': features_dict or {}
    }
    _active_entry_context[int(ticket)] = ctx
    
    # Simpan snapshot ke file cache lokal
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
    """
    Mengambil data konteks entry yang tersimpan saat posisi dibuka.
    """
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


def diagnose_trade_outcome(trade_record, entry_ctx=None):
    """
    Mendiagnosis secara mendalam alasan kemenangan (WIN) atau kesalahan (LOSS)
    berdasarkan aksi harga, struktur SMC, tren H4, DXY, dan kondisi makroekonomi.
    """
    status = trade_record.get('Hasil', 'UNKNOWN')
    pnl = trade_record.get('Profit ($ USD)', 0.0)
    pips = trade_record.get('Pips (P/L)', 0.0)
    close_reason = trade_record.get('Keterangan / Alasan Exit', '')
    trade_type = trade_record.get('Tipe', 'BUY')
    timeframe = trade_record.get('Timeframe', 'M15')
    
    ctx = entry_ctx or {}
    setup = ctx.get('setup_details', {})
    scenario = ctx.get('scenario_type', 'GENERAL_ENTRY')
    macro_info = setup.get('macro_news', 'NORMAL')
    h4_trend = setup.get('h4_trend', 'UNKNOWN')
    dxy_trend = setup.get('dxy_trend', 'UNKNOWN')
    prob = setup.get('model_prob', 50.0)
    zone = setup.get('zone', 'ZONA_UNKNOWN')

    if status == "WIN":
        factors = []
        if "tp" in close_reason.lower():
            factors.append("Target Take Profit (TP) tercapai penuh secara sniper")
        elif "trailing" in close_reason.lower():
            factors.append("Trailing lock berhasil mengamankan profit sebelum harga berbalik")
        else:
            factors.append("Exit profit positif")

        if (trade_type == "BUY" and h4_trend == "BULL") or (trade_type == "SELL" and h4_trend == "BEAR"):
            factors.append("Didukung penuh tren besar H4 (Searah Trend Institusional)")
        if (trade_type == "BUY" and dxy_trend == "BEAR") or (trade_type == "SELL" and dxy_trend == "BULL"):
            factors.append("Konfluensi kuat korelasi terbalik Indeks Dolar (DXY)")
        if "DEMAND" in scenario or "SUPPLY" in scenario or "ZONE_A" in scenario:
            factors.append("Rebound presisi dari batas area likuiditas kunci")

        diag_text = " ✅ [FAKTOR KEMENANGAN]: " + " | ".join(factors)
        lesson_learned = "Skenario ini terbukti efektif. Pertahankan konfluensi multi-timeframe dan disiplin hold hingga target."

    elif status == "LOSS":
        factors = []
        if "sl" in close_reason.lower():
            factors.append("Stop Loss tersentuh")
        elif "cut-loss" in close_reason.lower():
            factors.append("AI Early Cut-Loss mendeteksi pembalikan arah tajam")
        else:
            factors.append("Trade ditutup minus")

        if (trade_type == "BUY" and h4_trend == "BEAR") or (trade_type == "SELL" and h4_trend == "BULL"):
            factors.append("KESALAHAN: Entry melawan arah tren utama H4")
        if (trade_type == "BUY" and dxy_trend == "BULL") or (trade_type == "SELL" and dxy_trend == "BEAR"):
            factors.append("Korelasi DXY berlawanan arah (USD bergerak menekan posisi)")
        if "FREEZE" in macro_info or "NEAR" in macro_info:
            factors.append("Volatilitas berita makroekonomi mengganggu struktur harga")
        if abs(pips) < 35.0:
            factors.append("Kemungkinan tersapu noise/wick normal lilin emas (SL terlalu tipis)")

        if not factors:
            factors.append("Momentum pasar tidak melanjutkan prediksi model")

        diag_text = " ❌ [ANALISIS KESALAHAN]: " + " | ".join(factors)
        lesson_learned = "Hindari entry tanpa konfluensi tren H4, pastikan ruang SL memiliki jarak aman dari noise wick."

    else:
        diag_text = " ⚪ [HASIL IMPAS]: Break-Even Point diamankan."
        lesson_learned = "Posisi diamankan ke BEP, tidak ada kerugian finansial."

    return {
        'scenario': scenario,
        'diagnostic_text': diag_text,
        'lesson_learned': lesson_learned,
        'h4_trend': h4_trend,
        'dxy_trend': dxy_trend,
        'macro_info': macro_info,
        'zone': zone,
        'model_prob': prob
    }


def evaluate_and_record_trade(trade_record, orders_history=None):
    """
    Mencatat hasil trade, menjalankan diagnosis mendalam, memperbarui matriks skenario,
    dan menyimpan ke Excel dan CSV.
    """
    ticket = trade_record.get('Ticket Posisi', 0)
    entry_ctx = get_entry_context(ticket)
    diag = diagnose_trade_outcome(trade_record, entry_ctx)
    
    # Gabungkan data lengkap
    record_full = dict(trade_record)
    record_full['Skenario Entry'] = diag['scenario']
    record_full['Zona Entry'] = diag['zone']
    record_full['Tren H4 Entry'] = diag['h4_trend']
    record_full['Tren DXY Entry'] = diag['dxy_trend']
    record_full['Kondisi Makro News'] = diag['macro_info']
    record_full['Probabilitas Model (%)'] = diag['model_prob']
    record_full['Analisis Diagnostik (Menang/Kalah)'] = diag['diagnostic_text']
    record_full['Evaluasi & Pembelajaran'] = diag['lesson_learned']
    record_full['Tanggal Evaluasi'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Simpan ke CSV Riwayat Trade Evaluasi
    df_new = pd.DataFrame([record_full])
    if os.path.exists(CSV_EVAL_PATH):
        try:
            df_old = pd.read_csv(CSV_EVAL_PATH)
            if ticket not in df_old['Ticket Posisi'].values:
                df_combined = pd.concat([df_old, df_new], ignore_index=True)
                df_combined.to_csv(CSV_EVAL_PATH, index=False)
            else:
                df_old.loc[df_old['Ticket Posisi'] == ticket] = df_new.iloc[0].values
                df_old.to_csv(CSV_EVAL_PATH, index=False)
        except Exception:
            df_new.to_csv(CSV_EVAL_PATH, index=False)
    else:
        df_new.to_csv(CSV_EVAL_PATH, index=False)

    # 2. Jika ada snapshot fitur ML saat entry, simpan ke dataset retraining
    if entry_ctx and 'features' in entry_ctx and len(entry_ctx['features']) > 0:
        ml_row = dict(entry_ctx['features'])
        ml_row['Ticket'] = ticket
        ml_row['Outcome_Target'] = 1 if trade_record.get('Profit ($ USD)', 0) > 0 else 0
        ml_row['Profit_USD'] = trade_record.get('Profit ($ USD)', 0)
        ml_row['Scenario'] = diag['scenario']
        ml_row['Time'] = trade_record.get('Waktu Close', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        df_ml = pd.DataFrame([ml_row])
        if os.path.exists(CSV_ML_PATH):
            try:
                df_ml_old = pd.read_csv(CSV_ML_PATH)
                if ticket not in df_ml_old['Ticket'].values:
                    pd.concat([df_ml_old, df_ml], ignore_index=True).to_csv(CSV_ML_PATH, index=False)
            except Exception:
                df_ml.to_csv(CSV_ML_PATH, index=False)
        else:
            df_ml.to_csv(CSV_ML_PATH, index=False)

    # 3. Perbarui Matriks Evaluasi Skenario (5 - 10 kali pengujian)
    update_scenario_performance_matrix()

    # 4. Tulis ke Excel Workbook yang Rapi
    sync_scenario_evaluation_to_excel()

    return record_full


def update_scenario_performance_matrix():
    """
    Mengelompokkan seluruh riwayat trade berdasarkan skenario.
    Menghitung Win Rate, PnL, dan menetapkan status:
    - SKENARIO_UNGGULAN (>= 5x uji, Win Rate >= 60%)
    - SKENARIO_DIHINDARI / BLACKLIST (>= 5x uji, Win Rate < 40%)
    - DALAM_PENGUJIAN (< 5x uji)
    - SKENARIO_NETRAL (40% - 59%)
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
    grouped = df.groupby('Skenario Entry')
    matrix_dict = {}

    for scenario_name, group in grouped:
        total_tested = len(group)
        wins = len(group[group['Profit ($ USD)'] > 0])
        losses = len(group[group['Profit ($ USD)'] < 0])
        bep = len(group[group['Profit ($ USD)'] == 0])
        win_rate = (wins / total_tested * 100.0) if total_tested > 0 else 0.0
        total_pnl = group['Profit ($ USD)'].sum()
        avg_pnl = group['Profit ($ USD)'].mean()

        # Aturan Status Skenario
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

        summary_list.append({
            'Skenario Entry': scenario_name,
            'Total Diuji': total_tested,
            'Menang (WIN)': wins,
            'Kalah (LOSS)': losses,
            'Impas (BEP)': bep,
            'Win Rate (%)': round(win_rate, 1),
            'Total PnL ($ USD)': round(total_pnl, 2),
            'Rata-rata PnL ($)': round(avg_pnl, 2),
            'Status Evaluasi Skenario': status_skenario,
            'Tindakan Bot': action
        })
        
        matrix_dict[scenario_name] = {
            'total_tested': total_tested,
            'win_rate': round(win_rate, 1),
            'total_pnl': round(total_pnl, 2),
            'status': status_skenario,
            'action': action
        }

    matrix_df = pd.DataFrame(summary_list)
    if len(matrix_df) > 0:
        matrix_df.sort_values(by=['Total Diuji', 'Win Rate (%)'], ascending=[False, False], inplace=True)

    try:
        with open(JSON_SCENARIO_STATS, "w", encoding="utf-8") as f:
            json.dump(matrix_dict, f, indent=2)
    except Exception:
        pass

    return matrix_df


def can_trade_scenario(scenario_name, timeframe="M15", context=None):
    """
    Fungsi Guard untuk Bot Live:
    Memeriksa apakah skenario saat ini diizinkan untuk dieksekusi atau harus dihindari.
    Jika skenario sudah diuji >= 5 kali dan banyak loss (< 40% WR), bot menolak entry.
    """
    if not os.path.exists(JSON_SCENARIO_STATS):
        return True, "OK: Skenario belum memiliki riwayat evaluasi (Boleh diuji)."

    try:
        with open(JSON_SCENARIO_STATS, "r", encoding="utf-8") as f:
            matrix = json.load(f)
            
        if scenario_name in matrix:
            sc_info = matrix[scenario_name]
            if sc_info.get('action') == "BLACKLIST_AVOID":
                wr = sc_info.get('win_rate', 0.0)
                n = sc_info.get('total_tested', 0)
                pnl = sc_info.get('total_pnl', 0.0)
                msg = f"⛔ SKENARIO DIHINDARI: '{scenario_name}' mencatatkan Win Rate rendah ({wr}% dari {n} uji, Net PnL: ${pnl:.2f}). Entry dibatalkan demi keamanan modal."
                return False, msg
            elif sc_info.get('action') == "ALLOW_AND_BOOST":
                wr = sc_info.get('win_rate', 0.0)
                n = sc_info.get('total_tested', 0)
                msg = f"🌟 SKENARIO UNGGULAN: '{scenario_name}' terverifikasi menguntungkan ({wr}% Win Rate dari {n} uji)."
                return True, msg
    except Exception:
        pass

    return True, "OK: Skenario diizinkan dieksekusi."


def sync_scenario_evaluation_to_excel():
    """
    Menyinkronkan seluruh riwayat evaluasi dan matriks skenario ke file Excel
    'Evaluasi_Skenario_Trade.xlsx' dengan format profesional.
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
    
    # Sheet 1: Matriks Evaluasi Skenario (Skripsi & Riset)
    ws_matrix = wb.active
    ws_matrix.title = "Matriks Evaluasi Skenario"
    ws_matrix.views.sheetView[0].showGridLines = True

    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    gold_fill = PatternFill(start_color="D97706", end_color="D97706", fill_type="solid")
    green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    red_fill   = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    gray_fill  = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
    
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font  = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
    regular_font = Font(name="Calibri", size=10)
    
    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'),
        right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'),
        bottom=Side(style='thin', color='D1D5DB')
    )

    ws_matrix["A1"] = "📊 MATRIKS EVALUASI PERFORMA SKENARIO TRADING (PENGUJIAN 5 - 10X)"
    ws_matrix["A1"].font = title_font
    ws_matrix["A2"] = "Sistem cerdas menapis skenario: Pola unggulan dipertahankan, pola yang sering loss otomatis dihindari/diblacklist."
    ws_matrix["A2"].font = Font(name="Calibri", size=10, italic=True, color="6B7280")

    if len(matrix_df) > 0:
        headers = list(matrix_df.columns)
        for c_idx, col in enumerate(headers, 1):
            cell = ws_matrix.cell(row=4, column=c_idx, value=col)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for r_idx, row in matrix_df.iterrows():
            current_row = 5 + r_idx
            for c_idx, val in enumerate(row, 1):
                cell = ws_matrix.cell(row=current_row, column=c_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center" if c_idx in [2,3,4,5,6] else "left", vertical="center")
                
                if "UNGGULAN" in str(val):
                    cell.fill = green_fill
                    cell.font = Font(name="Calibri", size=10, bold=True, color="15803D")
                elif "DIHINDARI" in str(val):
                    cell.fill = red_fill
                    cell.font = Font(name="Calibri", size=10, bold=True, color="B91C1C")
                elif "PENGUJIAN" in str(val):
                    cell.fill = gray_fill

        ws_matrix.row_dimensions[4].height = 28
        for col in ws_matrix.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_matrix.column_dimensions[col_letter].width = max(max_len + 3, 14)

    # Sheet 2: Log Rinci Evaluasi Per Trade
    ws_log = wb.create_sheet(title="Log Rinci Evaluasi Trade")
    ws_log.views.sheetView[0].showGridLines = True

    ws_log["A1"] = "📝 LOG ANALISIS MENDALAM KEMENANGAN & KESALAHAN PER TRADE"
    ws_log["A1"].font = title_font
    ws_log["A2"] = "Mencatat diagnosa teknikal SMC, tren H4, DXY, dan kondisi makroekonomi untuk setiap posisi."
    ws_log["A2"].font = Font(name="Calibri", size=10, italic=True, color="6B7280")

    if len(df_eval) > 0:
        log_headers = list(df_eval.columns)
        for c_idx, col in enumerate(log_headers, 1):
            cell = ws_log.cell(row=4, column=c_idx, value=col)
            cell.fill = gold_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for r_idx, row in df_eval.iterrows():
            current_row = 5 + r_idx
            for c_idx, val in enumerate(row, 1):
                cell = ws_log.cell(row=current_row, column=c_idx, value=val)
                cell.font = regular_font
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
                if str(val) == "WIN":
                    cell.fill = green_fill
                    cell.font = Font(name="Calibri", size=10, bold=True, color="15803D")
                elif str(val) == "LOSS":
                    cell.fill = red_fill
                    cell.font = Font(name="Calibri", size=10, bold=True, color="B91C1C")

        ws_log.row_dimensions[4].height = 28
        for col in ws_log.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_log.column_dimensions[col_letter].width = min(max(max_len + 3, 14), 45)

    try:
        wb.save(EXCEL_EVAL_PATH)
    except Exception:
        pass


if __name__ == "__main__":
    print("="*80)
    print("TESTING SCENARIO EVALUATOR & AUTO-DIAGNOSTICS ENGINE")
    print("="*80)
    
    dummy_win = {
        'Ticket Posisi': 990001,
        'Waktu Open': '2026-09-15 10:00:00',
        'Waktu Close': '2026-09-15 10:45:00',
        'Durasi': '45m 0d',
        'Simbol': 'XAUUSD',
        'Tipe': 'BUY',
        'Lot': 0.01,
        'Harga Entry': 4410.50,
        'Stop Loss (SL)': 4405.00,
        'Take Profit (TP)': 4424.00,
        'Harga Exit': 4424.00,
        'Pips (P/L)': 135.0,
        'Profit ($ USD)': 13.50,
        'Hasil': 'WIN',
        'Keterangan / Alasan Exit': 'Hit Take Profit (TP)',
        'Model AI': 'LightGBM M15 v3.7',
        'Timeframe': 'M15'
    }
    
    record_entry_context(
        ticket=990001,
        symbol="XAUUSD",
        timeframe="M15",
        scenario_type="ZONE_A_DEMAND_BOUNCE_H4BULL",
        setup_details={
            'macro_news': 'NORMAL_MARKET',
            'h4_trend': 'BULL',
            'dxy_trend': 'BEAR',
            'model_prob': 66.5,
            'zone': 'Zona A (Demand Boundary)'
        },
        features_dict={'Dist_Support': 0.0010, 'Trend_H4_Bull': 1, 'RSI_M15': 38.0}
    )
    
    res = evaluate_and_record_trade(dummy_win)
    print(f"Diagnosa WIN:\n{res['Analisis Diagnostik (Menang/Kalah)']}\n{res['Evaluasi & Pembelajaran']}")
    
    can_tr, msg = can_trade_scenario("ZONE_A_DEMAND_BOUNCE_H4BULL")
    print(f"\nStatus Skenario: can_trade={can_tr} | {msg}")
    print("="*80)
    print("✅ Testing Scenario Evaluator Engine Berhasil!")
