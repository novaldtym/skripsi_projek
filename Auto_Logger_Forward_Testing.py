import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Path Excel Baru (Khusus Model Terbaru LightGBM SMC/ICT)
EXCEL_PATH_NEW_MODEL = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_Model_Terbaru_SMC.xlsx"
# Path Excel Arsip Gabungan Sebelumnya
EXCEL_PATH_ARCHIVE = r"d:\SKRIPSI INFORMATIKA\Laporan_Forward_Testing_100_Trade.xlsx"

MT5_PATH = r"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
MAGIC_NEW_MODEL = 123230

def sync_mt5_trades_to_excel(
    excel_path=EXCEL_PATH_NEW_MODEL, 
    filter_new_model_only=True,
    magic_number=123230,
    comment_filter=None,
    model_label="LightGBM SMC/ICT",
    sheet_title="Trade Log Model Terbaru",
    threshold_label=">= 60.0% + Trend Guard H1"
):
    """
    Menyinkronkan data trade MT5 ke Excel secara otomatis.
    Dapat disesuaikan untuk model M15 Konservatif (Magic 123230)
    maupun model M5 Scalping (Magic 123235).
    """
    if not mt5.initialize(path=MT5_PATH):
        print("⚠️ Gagal terhubung ke MT5 untuk sync history trade.")
        return None

    # Ambil history deal 30 hari terakhir
    from_date = datetime.now() - timedelta(days=30)
    to_date = datetime.now() + timedelta(days=1)
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals is None or len(deals) == 0:
        print("ℹ️ Belum ada history trade ditemukan di akun MT5 Anda.")
        mt5.shutdown()
        return None

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

    trade_records = []
    for pos_id, p in positions.items():
        deal_in = p['in']
        deal_out = p['out']
        
        if deal_in is not None and deal_out is not None:
            # Filter khusus model jika diminta
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
            if hours > 0:
                dur_str = f"{hours}j {mins}m"
            else:
                dur_str = f"{mins}m {secs}d"
            
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

    if len(trade_records) == 0:
        print("ℹ️ Belum ada posisi tertutup untuk filter ini.")
        return None

    df_trades = pd.DataFrame(trade_records)
    df_trades.sort_values(by='Waktu Close', ascending=True, inplace=True)
    df_trades.reset_index(drop=True, inplace=True)
    df_trades.insert(0, 'Trade Ke-', df_trades.index + 1)

    total_trades = len(df_trades)
    wins = len(df_trades[df_trades['Profit ($ USD)'] > 0])
    losses = len(df_trades[df_trades['Profit ($ USD)'] < 0])
    win_rate = (wins / total_trades) * 100.0 if total_trades > 0 else 0.0
    total_pnl = df_trades['Profit ($ USD)'].sum()
    
    total_win_dollars = df_trades[df_trades['Profit ($ USD)'] > 0]['Profit ($ USD)'].sum()
    total_loss_dollars = abs(df_trades[df_trades['Profit ($ USD)'] < 0]['Profit ($ USD)'].sum())
    profit_factor = (total_win_dollars / total_loss_dollars) if total_loss_dollars > 0 else (total_win_dollars if total_win_dollars > 0 else 1.0)
    avg_profit = total_pnl / total_trades if total_trades > 0 else 0.0

    summary_df = pd.DataFrame([
        {'Metrik Evaluasi Forward Testing': 'Nama Model', 'Nilai': f"{model_label} (28 Fitur SMC/ICT + DXY + MTF)"},
        {'Metrik Evaluasi Forward Testing': 'Metode Eksekusi', 'Nilai': 'Otomatis 0-Delay (MetaTrader 5 API)'},
        {'Metrik Evaluasi Forward Testing': 'Ambang Batas Keyakinan (Threshold)', 'Nilai': threshold_label},
        {'Metrik Evaluasi Forward Testing': 'Target Forward Testing Skripsi', 'Nilai': '100 Trade'},
        {'Metrik Evaluasi Forward Testing': 'Total Trade Otomatis Selesai', 'Nilai': f"{total_trades} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Progres Evaluasi (%)', 'Nilai': f"{(total_trades / 100.0) * 100:.1f}%"},
        {'Metrik Evaluasi Forward Testing': 'Jumlah Trade WIN (Profit)', 'Nilai': f"{wins} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Jumlah Trade LOSS (Rugi)', 'Nilai': f"{losses} Trade"},
        {'Metrik Evaluasi Forward Testing': 'Win Rate (%)', 'Nilai': f"{win_rate:.2f}%"},
        {'Metrik Evaluasi Forward Testing': 'Total Akumulasi Profit ($ USD)', 'Nilai': f"${total_pnl:+.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Rata-rata Profit per Trade', 'Nilai': f"${avg_profit:+.2f} USD"},
        {'Metrik Evaluasi Forward Testing': 'Profit Factor', 'Nilai': f"{profit_factor:.2f}" if profit_factor != total_win_dollars else "Maksimal (100% Win, 0 Loss)"},
        {'Metrik Evaluasi Forward Testing': 'Waktu Pembaruan Terakhir', 'Nilai': datetime.now().strftime('%Y-%m-%d %H:%M:%S WIB')}
    ])

    try:
        # Tulis ke Excel dengan styling profesional openpyxl
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_trades.to_excel(writer, sheet_name=sheet_title, index=False)
            summary_df.to_excel(writer, sheet_name='Ringkasan Statistik', index=False)

        # Styling Workbook
        wb = openpyxl.load_workbook(excel_path)
        
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

        # Sheet 1: Trade Log
        ws1 = wb[sheet_title]
        for col_idx in range(1, len(df_trades.columns) + 1):
            cell = ws1.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_idx in range(2, len(df_trades) + 2):
            status_val = ws1.cell(row=row_idx, column=14).value  # Kolom Hasil
            row_fill = win_fill if status_val == "WIN" else (loss_fill if status_val == "LOSS" else None)
            for col_idx in range(1, len(df_trades.columns) + 1):
                c = ws1.cell(row=row_idx, column=col_idx)
                c.border = thin_border
                if row_fill:
                    c.fill = row_fill
                if col_idx in [1, 2, 5, 6, 7, 12, 14]:
                    c.alignment = Alignment(horizontal="center", vertical="center")

        # Auto-fit column width
        for col in ws1.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws1.column_dimensions[col_letter].width = max(max_len + 3, 12)

        # Sheet 2: Summary
        ws2 = wb['Ringkasan Statistik']
        for col_idx in range(1, len(summary_df.columns) + 1):
            cell = ws2.cell(row=1, column=col_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        for row_idx in range(2, len(summary_df) + 2):
            c1 = ws2.cell(row=row_idx, column=1)
            c2 = ws2.cell(row=row_idx, column=2)
            c1.border = thin_border
            c2.border = thin_border
            c1.font = Font(name="Calibri", size=11, bold=True)
            c2.alignment = Alignment(horizontal="left", vertical="center")

        for col in ws2.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws2.column_dimensions[col_letter].width = max(max_len + 4, 25)

        wb.save(excel_path)
        print(f"✅ Rekap Forward Testing Berhasil Disinkronkan ke:")
        print(f"   📁 {excel_path}")
    except Exception as e:
        print(f"⚠️ Catatan Sync Excel ({os.path.basename(excel_path)}): {e}. Sinkronisasi akan diulang di candle berikutnya.")
    return summary_df, df_trades

if __name__ == "__main__":
    sync_mt5_trades_to_excel()
