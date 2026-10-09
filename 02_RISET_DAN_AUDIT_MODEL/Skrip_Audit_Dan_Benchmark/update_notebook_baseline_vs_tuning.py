import json
import nbformat

nb_path = 'Uji_Coba_LightGBM_XAUUSD.ipynb'
with open(nb_path, encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Markdown Cell 14
markdown_step5 = """### Step 5: Evaluasi Komparatif Komprehensif: Baseline vs Hyperparameter Tuning (Bab 4 Skripsi)

Sesuai metodologi penelitian pada **Bab 4 Skripsi Informatika**, evaluasi model dilakukan secara berpasangan (*paired benchmark*) antara:
1. **Model Baseline (Default Parameters):** Menggunakan konfigurasi parameter bawaan resmi masing-masing algoritma (*out-of-the-box*).
2. **Model Hasil Hyperparameter Tuning (Tuned):** Menggunakan konfigurasi hyperparameter optimal hasil eksperimen (pembatasan kedalaman, regularisasi L1/L2, subsampling fitur & data, serta pembobotan kelas seimbang).

**Empat Keluarga Algoritma yang Diuji:**
1. **LightGBM (Light Gradient Boosting Machine)**:
   - *Baseline*: `n_estimators=100`, `learning_rate=0.1`, `max_depth=-1`, `num_leaves=31` (Default)
   - *Tuned (Usulan Skripsi v4.2)*: `n_estimators=800`, `learning_rate=0.015`, `max_depth=5`, `num_leaves=24`, `min_child_samples=50`, `colsample_bytree=0.75`, `subsample=0.75`, `reg_alpha=0.1`, `reg_lambda=1.0`, `class_weight='balanced'`
2. **XGBoost (Extreme Gradient Boosting)**:
   - *Baseline*: `n_estimators=100`, `learning_rate=0.3`, `max_depth=6` (Default)
   - *Tuned*: `n_estimators=400`, `learning_rate=0.02`, `max_depth=5`, `subsample=0.8`, `colsample_bytree=0.8`, `reg_alpha=0.1`, `reg_lambda=1.0`
3. **Random Forest (Ensemble Bagging)**:
   - *Baseline*: `n_estimators=100`, `max_depth=None`, `min_samples_split=2` (Default)
   - *Tuned*: `n_estimators=250`, `max_depth=10`, `min_samples_split=10`, `min_samples_leaf=4`, `max_features='sqrt'`
4. **Logistic Regression (Linear Benchmark)**:
   - *Baseline*: `C=1.0`, `penalty='l2'`, `solver='lbfgs'` (Default)
   - *Tuned*: `C=0.01`, `penalty='l2'`, `solver='lbfgs'`, `max_iter=1000`"""

code_step5_1 = """# =========================================================================
# STEP 5.1: PELATIHAN & EVALUASI BASELINE VS TUNING (4 MODEL MACHINE LEARNING)
# =========================================================================

experiment_models = {
    # 1. LIGHTGBM
    "LightGBM (Baseline)": LGBMClassifier(random_state=42, verbose=-1),
    "LightGBM (Tuned v4.2)": LGBMClassifier(
        n_estimators=800, learning_rate=0.015, max_depth=5, num_leaves=24,
        min_child_samples=50, subsample=0.75, colsample_bytree=0.75,
        reg_alpha=0.1, reg_lambda=1.0, class_weight='balanced', random_state=42, n_jobs=-1, verbose=-1
    ),
    
    # 2. XGBOOST
    "XGBoost (Baseline)": XGBClassifier(random_state=42, eval_metric='logloss'),
    "XGBoost (Tuned)": XGBClassifier(
        n_estimators=400, learning_rate=0.02, max_depth=5,
        subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=1.0, random_state=42, eval_metric='logloss'
    ),
    
    # 3. RANDOM FOREST
    "Random Forest (Baseline)": RandomForestClassifier(random_state=42, n_jobs=-1),
    "Random Forest (Tuned)": RandomForestClassifier(
        n_estimators=250, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', random_state=42, n_jobs=-1
    ),
    
    # 4. LOGISTIC REGRESSION
    "Logistic Regression (Baseline)": LogisticRegression(max_iter=1000, random_state=42),
    "Logistic Regression (Tuned)": LogisticRegression(C=0.01, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
}

# Alias compatibility untuk Cell berikutnya
models = {
    "LightGBM v4.2 (Usulan Skripsi)": experiment_models["LightGBM (Tuned v4.2)"],
    "XGBoost Classifier": experiment_models["XGBoost (Tuned)"],
    "Random Forest": experiment_models["Random Forest (Tuned)"],
    "Logistic Regression": experiment_models["Logistic Regression (Tuned)"]
}

results = []
trained_models = {}

print("="*85)
print("🔄 MEMULAI PELATIHAN & PENGUJIAN KOMPARASI BASELINE VS TUNING...")
print("="*85)

for name, clf in experiment_models.items():
    family = name.split(" (")[0]
    variant = "Tuned" if "Tuned" in name else "Baseline"
    
    t0 = time.time()
    clf.fit(X_train, y_train)
    t_train = time.time() - t0
    trained_models[name] = clf
    
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1] if hasattr(clf, "predict_proba") else y_pred
    
    acc  = accuracy_score(y_test, y_pred) * 100
    prec = precision_score(y_test, y_pred, zero_division=0) * 100
    rec  = recall_score(y_test, y_pred, zero_division=0) * 100
    f1   = f1_score(y_test, y_pred, zero_division=0) * 100
    auc  = roc_auc_score(y_test, y_prob) * 100
    
    results.append({
        "Model": family,
        "Varian": variant,
        "Model Name": name,
        "Akurasi (%)": round(acc, 2),
        "Precision (%)": round(prec, 2),
        "Recall (%)": round(rec, 2),
        "F1-Score (%)": round(f1, 2),
        "ROC-AUC (%)": round(auc, 2),
        "Waktu Train (dtk)": round(t_train, 3)
    })
    print(f"✅ {name:<30} -> Akurasi: {acc:.2f}% | F1: {f1:.2f}% | AUC: {auc:.2f}% | Waktu: {t_train:.3f}s")

df_comparison = pd.DataFrame(results)

print("\\n" + "="*85)
print("📊 TABEL PERBANDINGAN PERFORMA LENGKAP: BASELINE VS TUNING (BAB 4 SKRIPSI)")
print("="*85)
display(df_comparison[['Model', 'Varian', 'Akurasi (%)', 'Precision (%)', 'Recall (%)', 'F1-Score (%)', 'ROC-AUC (%)', 'Waktu Train (dtk)']])

# Simpan ke Excel untuk Bab 4
df_comparison.to_excel('Hasil_Perbandingan_Baseline_vs_Tuning_Bab4.xlsx', index=False)
df_comparison.to_excel('Hasil_Perbandingan_Model_Bab4.xlsx', index=False)
print("💾 File perbandingan berhasil diekspor ke 'Hasil_Perbandingan_Baseline_vs_Tuning_Bab4.xlsx'")

# Serialisasi model usulan ke format .pkl yang digunakan langsung oleh bot produksi
best_model = experiment_models["LightGBM (Tuned v4.2)"]
joblib.dump(best_model, 'model_lightgbm_xauusd.pkl')
print("✅ Model usulan resmi 'LightGBM (Tuned v4.2)' berhasil disimpan ke 'model_lightgbm_xauusd.pkl'!")
"""

code_step5_2 = """# =========================================================================
# STEP 5.2: ANALISIS DELTA PENINGKATAN & VISUALISASI GRAFIS KOMPARASI
# =========================================================================

# 1. Tabel Delta Peningkatan (Tuning vs Baseline)
delta_rows = []
families = ["LightGBM", "XGBoost", "Random Forest", "Logistic Regression"]

for fam in families:
    base_row = df_comparison[(df_comparison['Model'] == fam) & (df_comparison['Varian'] == 'Baseline')].iloc[0]
    tune_row = df_comparison[(df_comparison['Model'] == fam) & (df_comparison['Varian'] == 'Tuned')].iloc[0]
    
    d_acc = tune_row['Akurasi (%)'] - base_row['Akurasi (%)']
    d_f1  = tune_row['F1-Score (%)'] - base_row['F1-Score (%)']
    d_auc = tune_row['ROC-AUC (%)'] - base_row['ROC-AUC (%)']
    d_time = tune_row['Waktu Train (dtk)'] - base_row['Waktu Train (dtk)']
    
    delta_rows.append({
        "Model": fam,
        "Akurasi Baseline (%)": f"{base_row['Akurasi (%)']:.2f}%",
        "Akurasi Tuned (%)": f"{tune_row['Akurasi (%)']:.2f}%",
        "Delta Akurasi": f"{d_acc:+.2f}%",
        "Delta F1-Score": f"{d_f1:+.2f}%",
        "Delta ROC-AUC": f"{d_auc:+.2f}%",
        "Efisiensi Waktu": f"{d_time:+.3f}s"
    })

df_delta = pd.DataFrame(delta_rows)
print("\\n" + "="*85)
print("📈 TABEL DELTA PENINGKATAN HYPERPARAMETER TUNING TERHADAP BASELINE:")
print("="*85)
display(df_delta)

# 2. Visualisasi Grafis 4-Panel Komparasi (Matplotlib & Seaborn)
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('Evaluasi Komparatif Komprehensif: Baseline vs Hyperparameter Tuning (Bab 4 Skripsi)', fontsize=15, fontweight='bold', y=0.98)

palette = {'Baseline': '#94a3b8', 'Tuned': '#059669'}

# Subplot 1: Akurasi (%)
sns.barplot(data=df_comparison, x='Model', y='Akurasi (%)', hue='Varian', palette=palette, ax=axes[0, 0])
axes[0, 0].set_title('Perbandingan Akurasi (%)', fontweight='bold', fontsize=12)
axes[0, 0].set_ylim(50, 62)
axes[0, 0].set_ylabel('Akurasi (%)')
for p in axes[0, 0].patches:
    h = p.get_height()
    if h > 0:
        axes[0, 0].annotate(f'{h:.2f}%', (p.get_x() + p.get_width() / 2., h),
                            ha='center', va='bottom', fontsize=10, xytext=(0, 2), textcoords='offset points')

# Subplot 2: ROC-AUC (%)
sns.barplot(data=df_comparison, x='Model', y='ROC-AUC (%)', hue='Varian', palette=palette, ax=axes[0, 1])
axes[0, 1].set_title('Perbandingan Discriminative Power (ROC-AUC %)', fontweight='bold', fontsize=12)
axes[0, 1].set_ylim(55, 66)
axes[0, 1].set_ylabel('ROC-AUC (%)')
for p in axes[0, 1].patches:
    h = p.get_height()
    if h > 0:
        axes[0, 1].annotate(f'{h:.2f}%', (p.get_x() + p.get_width() / 2., h),
                            ha='center', va='bottom', fontsize=10, xytext=(0, 2), textcoords='offset points')

# Subplot 3: F1-Score (%)
sns.barplot(data=df_comparison, x='Model', y='F1-Score (%)', hue='Varian', palette=palette, ax=axes[1, 0])
axes[1, 0].set_title('Perbandingan Balance Precision-Recall (F1-Score %)', fontweight='bold', fontsize=12)
axes[1, 0].set_ylim(55, 65)
axes[1, 0].set_ylabel('F1-Score (%)')
for p in axes[1, 0].patches:
    h = p.get_height()
    if h > 0:
        axes[1, 0].annotate(f'{h:.2f}%', (p.get_x() + p.get_width() / 2., h),
                            ha='center', va='bottom', fontsize=10, xytext=(0, 2), textcoords='offset points')

# Subplot 4: Waktu Komputasi Training (detik)
palette_time = {'Baseline': '#64748b', 'Tuned': '#0284c7'}
sns.barplot(data=df_comparison, x='Model', y='Waktu Train (dtk)', hue='Varian', palette=palette_time, ax=axes[1, 1])
axes[1, 1].set_title('Efisiensi Waktu Pelatihan (Detik)', fontweight='bold', fontsize=12)
axes[1, 1].set_ylabel('Waktu (detik)')
for p in axes[1, 1].patches:
    h = p.get_height()
    if h > 0:
        axes[1, 1].annotate(f'{h:.2f}s', (p.get_x() + p.get_width() / 2., h),
                            ha='center', va='bottom', fontsize=10, xytext=(0, 2), textcoords='offset points')

plt.tight_layout()
plt.savefig('grafik_perbandingan_baseline_vs_tuning_bab4.png', dpi=300)
plt.show()
print("📊 Grafik komparasi berhasil disimpan ke 'grafik_perbandingan_baseline_vs_tuning_bab4.png'!")
"""

# Replace Cell 14 and 15, and insert Cell 15b
nb.cells[14] = nbformat.v4.new_markdown_cell(markdown_step5)
nb.cells[15] = nbformat.v4.new_code_cell(code_step5_1)
nb.cells.insert(16, nbformat.v4.new_code_cell(code_step5_2))

with open(nb_path, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print(f"Successfully updated {nb_path}. New total cells: {len(nb.cells)}")
