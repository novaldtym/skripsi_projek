# Terjemahan & Analisis: Learning When to Say 'I Don't Know': High-Confidence Classification with Reject Option

**File Asli:** `High_Frequency_Trading_Reinforcement_Learning_Microstructure_arXiv.pdf`  
**Penulis:** Nicholas Kashani Motlagh, Jim Davis, Tim Anderson, Jeremy Gwinnup  
**Institusi:** Department of Computer Science and Engineering, Ohio State University & Air Force Research Laboratory (AFRL), USA  
**Publikasi:** arXiv / Machine Learning Research  
**Jumlah Halaman:** 14 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Kami mengusulkan teknik baru bernama *Reject Option Classification* untuk mengidentifikasi dan mengeliminasi area ketidakpastian (*regions of uncertainty*) dalam ruang keputusan model klasifikasi. Dalam banyak aplikasi berisiko tinggi (*high-stakes decision making*), kesalahan prediksi memiliki biaya yang sangat fatal, sementara menolak untuk membuat keputusan (*abstain / say "I don't know"*) adalah tindakan yang jauh lebih aman. 

Formulasi yang kami kembangkan melatih model untuk menetapkan ambang batas seleksi keyakinan tinggi (*high-confidence threshold*). Ketika tingkat keyakinan probabilitas model berada di bawah ambang batas kritis, model menolak untuk bertindak (*defer action*). 

Eksperimen membuktikan bahwa dengan menerapkan opsi penolakan pada sampel-sampel yang meragukan, akurasi pada sampel yang dieksekusi meningkat secara dramatis, tingkat kesalahan fatal ditekan mendekati nol, dan efisiensi pengambilan keputusan secara keseluruhan meningkat signifikan.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Paper dari Ohio State University dan AFRL ini membahas teori matematis dan algoritma **Reject Option Classification**: sebuah strategi di mana model cerdas dilatih untuk **tidak mengambil keputusan ketika probabilitas keyakinan rendah**.

### B. Research Gap (Kesenjangan Penelitian)
1. **Paksaan Klasifikasi Biner Konvensional:** Mayoritas model klasifikasi standar memaksa model untuk selalu memilih kelas 0 atau 1 meskipun probabilitasnya hanya 50.1% (hampir murni tebak-tebakan acak).
2. **Kebutuhan Ambang Batas Keyakinan (*Confidence Guard*):** Pada sistem berisiko tinggi (seperti transaksi finansial), mengambil tindakan pada keyakinan rendah mengakibatkan kehancuran modal (*capital drawdown*).

### C. Komparasi & Keterkaitan dengan Skripsi Nouval (SANGAT KRUSIAL!)
- **Landasan Teori Mutlak untuk "Confidence Guard $\ge 65\%$":** 
  Dalam skripsi Nouval, salah satu inovasi proteksi modal utama adalah aturan: **Sistem hanya membuka posisi trading jika probabilitas prediksi LightGBM $\ge 65\%$**. Jika probabilitas berada di antara 35% – 65% (area abu-abu), sistem memilih **HOLD / Abstain (tidak membuka posisi)**.
- Paper Motlagh et al. ini adalah **rujukan ilmiah sempurna** untuk menjustifikasi arsitektur *Confidence Guard* Nouval di Bab 1 dan Bab 3 skripsi! Anda dapat mengutip paper ini untuk menjelaskan bahwa secara teoretis, memberikan opsi penolakan (*reject option / confidence thresholding*) adalah standar emas dalam *safe machine learning* untuk menekan false signals dan drawdown.
