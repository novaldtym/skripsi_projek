import pandas as pd

out_file = r"d:\SKRIPSI INFORMATIKA\Hasil_Audit_Putaran_3_Empiris.xlsx"

df_split = pd.DataFrame([
    {'Split': 'Train Set (Purged)', 'Observasi': 34785, 'Mulai': '2024-08-26 20:00:00', 'Selesai': '2026-02-17 05:45:00', 'Catatan Purge': '5 candle terakhir dipurge (bebas overlap dg Val)'},
    {'Split': 'Validation Set (Purged)', 'Observasi': 7450, 'Mulai': '2026-02-17 07:15:00', 'Selesai': '2026-06-11 08:15:00', 'Catatan Purge': '5 candle terakhir dipurge (bebas overlap dg Test)'},
    {'Split': 'Independent Test (Purged)', 'Observasi': 7450, 'Mulai': '2026-06-11 09:45:00', 'Selesai': '2026-10-02 19:30:00', 'Catatan Purge': '5 candle terakhir dipurge (horizon target valid)'}
])

df_baselines = pd.DataFrame([
    {'Model / Baseline': 'Baseline 50/50 (Uniform)', 'LogLoss': 0.6931, 'Brier': 0.2500, 'ROC_AUC': 0.5000, 'Acc_Global': '50.00%'},
    {'Model / Baseline': 'Baseline Class Prior (53.49% UP)', 'LogLoss': 0.6980, 'Brier': 0.2524, 'ROC_AUC': 0.5000, 'Acc_Global': '53.49%'},
    {'Model / Baseline': 'LightGBM 57 Fitur (Purged Test)', 'LogLoss': 0.6993, 'Brier': 0.2529, 'ROC_AUC': 0.5272, 'Acc_Global': '50.76%'}
])

df_robustness = pd.DataFrame([
    {'Blok': 'Block 1', 'Rentang': '2026-06-11 s/d 2026-07-10', 'N_Bar': 1862, 'ROC_AUC': 0.5319, 'Acc_Global': '51.45%', 'Sinyal_65': 112, 'Coverage': '6.0%', 'Sinyal_per_Hari': 5.6, 'Acc_Selective_65': '56.25%'},
    {'Blok': 'Block 2', 'Rentang': '2026-07-10 s/d 2026-08-07', 'N_Bar': 1862, 'ROC_AUC': 0.5251, 'Acc_Global': '50.59%', 'Sinyal_65': 83,  'Coverage': '4.5%', 'Sinyal_per_Hari': 4.2, 'Acc_Selective_65': '67.47%'},
    {'Blok': 'Block 3', 'Rentang': '2026-08-07 s/d 2026-09-04', 'N_Bar': 1862, 'ROC_AUC': 0.5418, 'Acc_Global': '52.26%', 'Sinyal_65': 157, 'Coverage': '8.4%', 'Sinyal_per_Hari': 7.8, 'Acc_Selective_65': '59.24%'},
    {'Blok': 'Block 4', 'Rentang': '2026-09-04 s/d 2026-10-02', 'N_Bar': 1864, 'ROC_AUC': 0.5043, 'Acc_Global': '50.00%', 'Sinyal_65': 84,  'Coverage': '4.5%', 'Sinyal_per_Hari': 4.2, 'Acc_Selective_65': '53.57%'},
    {'Blok': 'Overall Test', 'Rentang': '2026-06-11 s/d 2026-10-02', 'N_Bar': 7450, 'ROC_AUC': 0.5272, 'Acc_Global': '50.76%', 'Sinyal_65': 436, 'Coverage': '5.85%', 'Sinyal_per_Hari': 5.4, 'Acc_Selective_65': '58.94%'}
])

df_matched = pd.DataFrame([
    {'Model': 'LightGBM (Tuned)', 'Matched_Observasi': 'Top 436 bar (5.85%)', 'Matched_Accuracy': '58.94%', 'ROC_AUC': 0.5272, 'Peringkat': 1},
    {'Model': 'Random Forest (Tuned)', 'Matched_Observasi': 'Top 436 bar (5.85%)', 'Matched_Accuracy': '54.82%', 'ROC_AUC': 0.5139, 'Peringkat': 2},
    {'Model': 'XGBoost (Tuned)', 'Matched_Observasi': 'Top 436 bar (5.85%)', 'Matched_Accuracy': '54.59%', 'ROC_AUC': 0.5175, 'Peringkat': 3},
    {'Model': 'Logistic Regression', 'Matched_Observasi': 'Top 436 bar (5.85%)', 'Matched_Accuracy': '52.52%', 'ROC_AUC': 0.5171, 'Peringkat': 4}
])

with pd.ExcelWriter(out_file, engine='openpyxl') as writer:
    df_split.to_excel(writer, sheet_name='Purged_Split', index=False)
    df_baselines.to_excel(writer, sheet_name='Probability_Baselines', index=False)
    df_robustness.to_excel(writer, sheet_name='Time_Block_Robustness', index=False)
    df_matched.to_excel(writer, sheet_name='Matched_Coverage_Top6%', index=False)

print(f"Data audit putaran 3 berhasil disimpan ke: {out_file}")
