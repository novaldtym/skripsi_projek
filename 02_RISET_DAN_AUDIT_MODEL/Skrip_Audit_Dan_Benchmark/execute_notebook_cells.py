import nbformat
from nbclient import NotebookClient

nb_path = 'Uji_Coba_LightGBM_XAUUSD.ipynb'

print("Membaca notebook...")
with open(nb_path, encoding='utf-8') as f:
    nb = nbformat.read(f, as_version=4)

# Komentari cell %pip install agar tidak buang waktu download ulang
for cell in nb.cells:
    if cell.cell_type == 'code' and '%pip install' in cell.source:
        cell.source = '# ' + cell.source.replace('\n', '\n# ')
        print("Skipped %pip install cell.")

client = NotebookClient(nb, timeout=600, kernel_name='python3')
print("Menjalankan seluruh sel notebook secara otomatis...")
client.execute()

with open(nb_path, 'w', encoding='utf-8') as f:
    nbformat.write(nb, f)

print("✅ Notebook berhasil dijalankan dan semua output tabel serta visualisasi telah tersimpan ke Uji_Coba_LightGBM_XAUUSD.ipynb!")
