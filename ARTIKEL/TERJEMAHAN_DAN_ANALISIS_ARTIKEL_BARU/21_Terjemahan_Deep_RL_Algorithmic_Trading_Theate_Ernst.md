# Terjemahan & Analisis: An Application of Deep Reinforcement Learning to Algorithmic Trading

**File Asli:** `Deep_Learning_XAUUSD_Algorithmic_Trading_arXiv.pdf`  
**Penulis:** Thibaut Théate, Damien Ernst  
**Institusi:** Montefiore Institute, University of Liège, Belgia  
**Publikasi:** *Expert Systems with Applications* / arXiv  
**Jumlah Halaman:** 19 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Makalah penelitian ilmiah ini menyajikan pendekatan inovatif berbasis *Deep Reinforcement Learning* (DRL) untuk menyelesaikan masalah perdagangan algoritmik (*algorithmic trading*) dalam menentukan posisi perdagangan yang optimal (Long, Neutral, Short) pada setiap titik waktu di pasar keuangan. 

Kami merancang algoritma DRL baru bernama **Trading Deep Q-Network (TDQN)** yang secara khusus disesuaikan dengan kendala operasional pasar keuangan nyata, termasuk biaya komisi transaksi, keterbatasan likuiditas, dan eksekusi posisi diskret. Model dilatih dan diuji pada dataset historis 30 aset saham dan komoditas global. 

Hasil evaluasi empiris membuktikan bahwa agen TDQN mampu menghasilkan keuntungan yang konsisten dan secara signifikan mengungguli strategi *Buy-and-Hold* serta strategi perdagangan berbasis aturan teknikal tradisional, sekaligus membatasi risiko kerugian (*downside risk*).

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper dari University of Liège ini merancang agen *Trading Deep Q-Network* (TDQN) yang mampu mempelajari aksi perdagangan optimal secara otonom pada pasar finansial dengan memperhitungkan biaya komisi dan kendala eksekusi riil.

### B. Research Gap (Kesenjangan Penelitian)
1. **Pengabaian Biaya Transaksi:** Banyak model AI finansial mengklaim profitabilitas tinggi namun gagal total di dunia nyata karena tidak memperhitungkan biaya spread dan komisi broker.
2. **Kebutuhan Logika Posisi Fleksibel:** Model harus mampu mengambil posisi Netral (keluar dari pasar) saat pasar sedang tidak pasti.

### C. Komparasi & Keterkaitan dengan Skripsi Nouval
- Memberikan bukti empiris bahwa sistem trading machine learning wajib memperhitungkan friksi pasar (biaya transaksi, spread, dan slippage).
- Skripsi Nouval merealisasikan hal ini secara nyata melalui integrasi langsung ke **MetaTrader 5 API**, di mana setiap eksekusi order dibatasi oleh spread realistis dan proteksi modal terukur.
