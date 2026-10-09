# Terjemahan & Analisis: Slow Momentum with Fast Reversion: A Trading Strategy Using Deep Learning and Changepoint Detection

**File Asli:** `Deep_Reinforcement_Learning_Financial_Trading_Dynamic_Risk.pdf`  
**Penulis:** Kieran Wood, Stephen Roberts, Stefan Zohren  
**Institusi:** Oxford-Man Institute of Quantitative Finance, University of Oxford, UK  
**Jumlah Halaman:** 14 Halaman  

---

## 1. Terjemahan Lengkap

### Abstrak
Strategi momentum merupakan bagian penting dari investasi alternatif dan berada di jantung pengelolaan dana oleh *Commodity Trading Advisors* (CTA). Namun, strategi ini terbukti mengalami kesulitan besar dalam beradaptasi dengan perubahan kondisi pasar yang cepat dan mendadak (*market regime shifts*). 

Dalam makalah ini, kami mengusulkan kerangka kerja baru yang menggabungkan pembelajaran mendalam (*deep learning*) dengan algoritma deteksi titik perubahan rezim (*changepoint detection*). Sistem ini mengidentifikasi transisi antara rezim tren jangka panjang (*slow momentum*) dan rezim pembalikan cepat (*fast mean-reversion*). 

Pengujian pada kontrak berjangka komoditas membuktikan bahwa menambahkan deteksi titik perubahan secara dinamis mampu mengurangi kerugian tajam saat terjadi *trend crash* dan meningkatkan rasio Sharpe secara substansial.

---

## 2. Analisis Struktur & Metodologi Penelitian

### A. Rangkuman Eksekutif (Summary)
Penelitian dari Oxford-Man Institute ini mengatasi masalah kerapuhan strategi tren saat terjadi pembalikan harga mendadak dengan menerapkan **Changepoint Detection**. Ketika titik belok terdeteksi, sistem secara otomatis beralih dari strategi *trend-following* ke *mean-reversion*.

### B. Komparasi & Keterkaitan dengan Skripsi Nouval
- **Kesesuaian Sangat Kuat dengan Konsep SMC:** Konsep *Change of Character* (CHoCH) dan *Break of Structure* (BOS) dari Smart Money Concepts yang dimasukkan Nouval ke dalam 36 fiturnya pada dasarnya adalah deteksi titik perubahan rezim (*changepoint detection*) berbasis struktur pasar!
- Paper Oxford ini memberikan pembenaran akademik yang sangat elegan mengapa fitur SMC (CHoCH dan BOS) sangat krusial dimasukkan ke dalam model LightGBM Nouval untuk mendeteksi pembalikan tren harga XAUUSD.
