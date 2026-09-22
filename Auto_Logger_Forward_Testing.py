import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Path Excel Baru (Khusus Model Terbaru LightGBM SMC/ICT)
EXCEL_PATH_NEW_MODEL = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx"
EXCEL_PATH_M5        = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_M5_Scalping.xlsx"
EXCEL_PATH_ARCHIVE   = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_100_Trade.xlsx"

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MAGIC_NEW_MODEL = 123230
MAGIC_M5_SCALP   = 123236

# CUTOFF WAKTU VERSI 3.7 (Reset Saldo Awal $500 pada 18 September 2026 21:55:00 WIB - Sniper Direct Entry)
V37_START_TIME = datetime(2026, 9, 18, 21, 55, 0)
STARTING_BALANCE_DEFAULT = 500.00


def sync_mt5_trades_to_excel(
    excel_path=EXCEL_PATH_NEW_MODEL, 
    filter_new_model_only=True,
    magic_number=123230,
    comment_filter=None,
    model_label=None,
    sheet_title=None,
    summary_sheet_title=None,
    threshold_label=None,
    start_date=V37_START_TIME,
    starting_balance=STARTING_BALANCE_DEFAULT,
    silent=False
):
    """
    Menyinkronkan data trade MT5 Versi 3.7 ke tab khusus di Excel secara otomatis.
    - Menjaga tab arsip (v3.6 dan v3.5) tetap utuh tanpa terhapus.
    - Menghitung perkembangan Saldo ($ USD) dari modal awal $500.00.
    - Menghitung ROI (%) dan Profit Factor secara real-time.
    """
    is_m5 = (magic_number in [123236, 123235]) or ("m5" in os.path.basename(excel_path).lower())

    if model_label is None:
        model_label = "LightGBM M5 v3.7 (36 Fitur Makro+SMC+H4)" if is_m5 else "LightGBM M15 v3.7 (36 Fitur Makro+SMC+H4)"
    if threshold_label is None:
        threshold_label = "Versi 3.7 Multi-Zone Scalper (Wide SL + Macro)" if is_m5 else "Versi 3.7 (Wide SL + RRR 2.5 + Sniper)"

    # Tetapkan nama sheet khusus v3.7
    if sheet_title is None or "v3.7" not in sheet_title:
        sheet_title = "Trade Log M5 Scalping (v3.7)" if is_m5 else "Trade Log Model Terbaru (v3.7)"
    if summary_sheet_title is None or "v3.7" not in summary_sheet_title:
        summary_sheet_title = "Ringkasan Statistik (v3.7)"

    archive_log_name = "Trade Log M5 (Arsip v3.6)" if is_m5 else "Trade Log M15 (Arsip v3.6)"
    archive_stat_name = "Ringkasan Statistik (v3.6)"

    if not mt5.initialize(path=MT5_PATH):
        if not silent:
            print("⚠️ Gagal terhubung ke MT5 untuk sync history trade.")
        return None

    # Ambil history deal sejak cutoff Versi 3.6
    from_date = start_date - timedelta(hours=1)
    to_date = datetime.now() + timedelta(hours=1)
    deals = mt5.history_deals_get(from_date, to_date)
    
    trade_records = []

    if deals is not None and len(deals) > 0:
        # Kelompokkan deal berdasarkan position_id
        positions = {}
        for d in deals:
            pos_id = d.position_id
            if pos_id == 0:
                continue
                
            if pos_id not in positions:
                positions[pos_id] = {'in': None, 'out': None}
                
            if d.entry == 0:  # DEAL_ENTRY_IN (Open)
                positions[pos_id]['in'] = d
            elif d.entry in [1, 2]:  # DEAL_ENTRY_OUT (Close)
                positions[pos_id]['out'] = d

        for pos_id, p in positions.items():
            deal_in = p['in']
            deal_out = p['out']
            
            if deal_in is not None and deal_out is not None:
                # Filter deal HANYA yang dibuka SETELAH cutoff Versi 3.6
                if datetime.fromtimestamp(deal_in.time) < start_date:
                    continue

                # Filter khusus model/magic
                if filter_new_model_only:
                    if deal_in.magic != magic_number:
                        continue
                    if comment_filter is not None and comment_filter.lower() not in (deal_in.comment or '').lower():
                        continue

                open_time_dt = datetime.fromtimestamp(deal_in.time)
                close_time_dt = datetime.fromtimestamp(deal_out.time)
                open_time = open_time_dt.strftime('%Y-%m-%d %H:%M:%S')
                close_time = close_time_dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Durasi Trade
                dur_seconds = int((close_time_dt - open_time_dt).total_seconds())
                hours = dur_seconds // 3600
                mins = (dur_seconds % 3600) // 60
                secs = dur_seconds % 60
                dur_str = f"{hours}j {mins}m" if hours > 0 else f"{mins}m {secs}d"
                
                symbol = deal_in.symbol
                trade_type = "BUY" if deal_in.type == 0 else "SELL"
                lot_size = deal_in.volume
                open_price = deal_in.price
                close_price = deal_out.price
                profit = deal_out.profit + deal_out.swap + deal_out.commission
                
                # Ambil detail SL dan TP dari order history
                orders = mt5.history_orders_get(position=pos_id)
                sl_price = 0.0
                tp_price = 0.0
                if orders:
                    for o in orders:
                        if o.sl > 0: sl_price = o.sl
                        if o.tp > 0: tp_price = o.tp
                
                # Alasan penutupan
                cmt_low = (deal_out.comment or '').lower()
                if "[tp" in cmt_low:
                    close_reason = "Hit Take Profit (TP)"
                elif "[sl" in cmt_low:
                    close_reason = "Hit Stop Loss (SL)"
                elif "scalp tp" in cmt_low:
                    close_reason = "Bot Dynamic Scalp TP"
                elif "trailing" in cmt_low:
                    close_reason = "Bot Trailing Profit Lock"
                elif "cut-loss" in cmt_low or "invalidation" in cmt_low or "reversal" in cmt_low:
                    close_reason = "AI Early Cut-Loss (Reversal)"
                elif "be" in cmt_low:
                    close_reason = "Hit Break-Even"
                else:
                    close_reason = deal_out.comment if deal_out.comment else "Bot Market Close"

                if trade_type == "BUY":
                    pips = (close_price - open_price) * 10.0
                else:
                    pips = (open_price - close_price) * 10.0
                    
                status = "WIN" if profit > 0 else ("LOSS" if profit < 0 else "BEP")
                
                trade_records.append({
                    'Ticket Posisi': pos_id,
                    'Waktu Open': open_time,
                    'Waktu Close': close_time,
                    'Durasi': dur_str,
                    'Simbol': symbol,
                    'Tipe': trade_type,
                    'Lot': lot_size,
                    'Harga Entry': open_price,
                    'Stop Loss (SL)': sl_price,
                    'Take Profit (TP)': tp_price,
                    'Harga Exit': close_price,
                    'Pips (P/L)': round(pips, 1),
                    'Profit ($ USD)': round(profit, 2),
                    'Hasil': status,
                    'Keterangan / Alasan Exit': close_reason,
                    'Model AI': model_label
                })

    mt5.shutdown()

    # Evaluasi mendalam otomatis setiap trade tertutup ke Scenario Evaluator Engine
    if len(trade_records) > 0:
        try:
            import Scenario_Evaluator_Engine as scenario_eval
            has_new_eval = False
            for tr_rec in trade_records:
                res = scenario_eval.evaluate_and_record_trade(tr_rec, sync_excel=False)
                if res is not None:
                    has_new_eval = True
            if has_new_eval:
                scenario_eval.sync_scenario_evaluation_to_excel()
        except Exception:
            pass

    # Hitung saldo kumulatif dan metrik
    headers = [
        'Trade Ke-', 'Ticket Posisi', 'Waktu Open', 'Waktu Close', 'Durasi',
        'Simbol', 'Tipe', 'Lot', 'Harga Entry', 'Stop Loss (SL)', 'Take Profit (TP)',
        'Harga Exit', 'Pips (P/L)', 'Profit ($ USD)', 'Saldo ($ USD)', 'Hasil',
        'Keterangan / Alasan Exit', 'Model AI'
    ]

    running_balance = starting_balance
    if len(trade_records) > 0:
        df_trades = pd.DataFrame(trade_records)
        df_trades.sort_values(by='Waktu Close', ascending=True, inplace=True)
        df_trades.reset_index(drop=True, inplace=True)
        df_trades.insert(0, 'Trade Ke-', df_trades.index + 1)
        
        # Tambahkan kolom Saldo ($ USD)
        saldo_list = []
        for pnl in df_trades['Profit ($ USD)']:
            running_balance += pnl
            saldo_list.append(round(running_balance, 2))
        
        # Sisipkan sebelum kolom 'Hasil'
        insert_idx = df_trades.columns.get_loc('Hasil')
        df_trades.insert(insert_idx, 'Saldo ($ USD)', saldo_list)

        total_trades = len(df_trades)
        wins = len(df_trades[df_trades['Profit ($ USD)'] > 0])
        losses = len(df_trades[df_trades['Profit ($ USD)'] < 0])
        win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
        total_pnl = df_trades['Profit ($ USD)'].sum()
        roi = (total_pnl / starting_balance) * 100.0
        
        total_win_dollars = df_trades[df_trades['Profit ($ USD)'] > 0]['Profit ($ USD)'].sum()
        total_loss_dollars = abs(df_trades[df_trades['Profit ($ USD)'] < 0]['Profit ($ USD)'].sum())
        profit_factor = (total_win_dollars / total_loss_dollars) if total_loss_dollars > 0 else (total_win_dollars if total_win_dollars > 0 else 1.0)
        avg_profit = total_pnl / total_trades if total_trades > 0 else 0.0
        pf_str = f"{profit_factor:.2f}" if total_loss_dollars > 0 else ("Maksimal (100% Win, 0 Loss)" if wins > 0 else "-")
    else:
        df_trades = pd.DataFrame(columns=headers)
        total_trades = 0
        wins = 0
        losses = 0
        win_rate = 0.0
        total_pnl = 0.0
        roi = 0.0
        avg_profit = 0.0
        pf_str = "-"

    summary_df = pd.DataFrame([
        {'Metrik Evaluasi Forward Testing': 'Nama Model', 'Nilai Evaluasi': f"{model_label} (28 Fitur SMC/ICT + DXY + MTF)"},
        {'Metrik Evaluasi Forward Testing': 'Metode Eksekusi', 'Nilai Evaluasi': 'Otomatis 0-Delay (MetaTrader 5 API)'},
        {'Metrik Evaluasi Forward Testing': 'Ambang Batas Keyakinan (Threshold)', 'Nilai Evaluasi': threshold_label},
        {'Metrik Evaluasi Forward Testing': 'Target Forward Testing Skripsi', 'Nilai Evaluasi': '100 Trade'},
        {'Metrik Evaluasi Forward Testing': 'Saldo Awal Evaluasi', 'Nilai Evaluasi': f"${starting_balance:.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Saldo Terkini', 'Nilai Evaluasi': f"${running_balance:.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Total Trade Otomatis Selesai', 'Nilai Evaluasi': f"{total_trades} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Progres Evaluasi (%)', 'Nilai Evaluasi': f"{(total_trades / 100.0) * 100:.1f}%"},
        {'Metrik Evaluasi Forward Testing': 'Jumlah Trade WIN (Profit)', 'Nilai Evaluasi': f"{wins} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Jumlah Trade LOSS (Rugi)', 'Nilai Evaluasi': f"{losses} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Win Rate (%)', 'Nilai Evaluasi': f"{win_rate:.2f}%"},
        {'Metrik Evaluasi Forward Testing': 'Total Akumulasi Profit ($ USD)', 'Nilai Evaluasi': f"${total_pnl:+.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Return on Investment (ROI)', 'Nilai Evaluasi': f"{roi:+.2f}%"},
        {'Metrik Evaluasi Forward Testing': 'Rata-rata Profit per Trade', 'Nilai Evaluasi': f"${avg_profit:+.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Profit Factor', 'Nilai Evaluasi': pf_str},
        {'Metrik Evaluasi Forward Testing': 'Waktu Pembaruan Terakhir', 'Nilai Evaluasi': datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}
    ])

    try:
        if not os.path.exists(excel_path):
            wb = openpyxl.Workbook()
            # remove default sheet
            wb.remove(wb.active)
        else:
            wb = openpyxl.load_workbook(excel_path)

        # 1. Pastikan tab arsip v3.5 dinamai dengan benar dan aman
        old_default_log = "Trade Log M5 Scalping" if is_m5 else "Trade Log Model Terbaru"
        if old_default_log in wb.sheetnames and archive_log_name not in wb.sheetnames:
            wb[old_default_log].title = archive_log_name
        if "Ringkasan Statistik" in wb.sheetnames and archive_stat_name not in wb.sheetnames:
            wb["Ringkasan Statistik"].title = archive_stat_name

        # 2. Kelola Sheet Log v3.6
        if sheet_title in wb.sheetnames:
            ws_log = wb[sheet_title]
            ws_log.delete_rows(1, ws_log.max_row + 1)
        else:
            ws_log = wb.create_sheet(title=sheet_title, index=0)

        # 3. Kelola Sheet Statistik v3.6
        if summary_sheet_title in wb.sheetnames:
            ws_stat = wb[summary_sheet_title]
            ws_stat.delete_rows(1, ws_stat.max_row + 1)
        else:
            ws_stat = wb.create_sheet(title=summary_sheet_title, index=1)

        # Styling
        header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        win_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        loss_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
        thin_border = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )

        # Isi Header Log
        for col_idx, col_name in enumerate(headers, 1):
            c = ws_log.cell(row=1, column=col_idx, value=col_name)
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")

        # Isi Data Log
        for r_idx, row in df_trades.iterrows():
            row_num = r_idx + 2
            status_val = str(row.get('Hasil', ''))
            row_fill = win_fill if status_val == "WIN" else (loss_fill if status_val == "LOSS" else None)
            
            for c_idx, col_name in enumerate(headers, 1):
                val = row.get(col_name, '')
                cell = ws_log.cell(row=row_num, column=c_idx, value=val)
                cell.border = thin_border
                if row_fill:
                    cell.fill = row_fill
                if c_idx in [1, 2, 5, 6, 7, 13, 15, 16]:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                elif c_idx in [8, 9, 10, 11, 12, 14, 15]:
                    cell.alignment = Alignment(horizontal="right", vertical="center")

        # Auto width Log
        for col in ws_log.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_log.column_dimensions[col_letter].width = max(max_len + 4, 13)

        # Isi Data Summary
        c1_head = ws_stat.cell(row=1, column=1, value="Metrik Evaluasi Forward Testing")
        c2_head = ws_stat.cell(row=1, column=2, value="Nilai Evaluasi")
        for c in [c1_head, c2_head]:
            c.fill = header_fill
            c.font = header_font
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border

        for r_idx, (_, r_data) in enumerate(summary_df.iterrows(), 2):
            c1 = ws_stat.cell(row=r_idx, column=1, value=r_data['Metrik Evaluasi Forward Testing'])
            c2 = ws_stat.cell(row=r_idx, column=2, value=r_data['Nilai Evaluasi'])
            c1.border = thin_border
            c2.border = thin_border
            c1.font = Font(name="Calibri", size=11, bold=True)
            c2.alignment = Alignment(horizontal="left", vertical="center")

        # Auto width Summary
        for col in ws_stat.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws_stat.column_dimensions[col_letter].width = max(max_len + 4, 25)

        # Jadikan tab Log v3.6 sebagai active sheet
        wb.active = ws_log
        wb.save(excel_path)
        if not silent:
            print(f"✅ Rekap Forward Testing Versi 3.6 Berhasil Disinkronkan ke:")
            print(f"   📁 {excel_path} [Tab: {sheet_title}]")
    except Exception as e:
        if not silent:
            print(f"⚠️ Catatan Sync Excel ({os.path.basename(excel_path)}): {e}")

    return summary_df, df_trades


if __name__ == "__main__":
    print("Memperbarui Excel M15...")
    sync_mt5_trades_to_excel(
        excel_path=EXCEL_PATH_NEW_MODEL,
        filter_new_model_only=True,
        magic_number=MAGIC_NEW_MODEL,
        model_label="LightGBM M15 v3.7 (Wide SL + RRR 2.5 + Sniper)"
    )
    print("Memperbarui Excel M5...")
    sync_mt5_trades_to_excel(
        excel_path=EXCEL_PATH_M5,
        filter_new_model_only=True,
        magic_number=MAGIC_M5_SCALP,
        model_label="LightGBM M5 v3.7 (Wide SL + Macro Scalp + Sniper)"
    )
