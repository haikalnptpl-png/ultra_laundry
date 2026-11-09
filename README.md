# 🐧 Ultra Laundry System

Sistem administrasi transaksi laundry (Streamlit + SQLite), 5 entitas relasional, 4 halaman:
Beranda, Kasir & Transaksi, Kategori & Layanan, Data Pelanggan.

## Cara menjalankan

**Cara 1 (paling mudah):** klik dua kali `run.bat`.

**Cara 2 (manual):**
```powershell
cd "D:\SEMESTER 5\PEMROGRAMAN\M5\UltraLaundry_System"
python -m streamlit run app.py
```

Buka browser ke `http://localhost:8501` kalau tidak terbuka otomatis.

## Dependensi
```powershell
pip install -r requirements.txt
```
`plotly` opsional; tanpa plotly grafik tetap tampil memakai chart bawaan Streamlit.

## Database
`ultra_laundry.db` dibuat otomatis di folder ini saat pertama kali dijalankan,
beserta data contoh (3 pelanggan + 2 transaksi).

Untuk memulai dari nol: tutup aplikasi, hapus `ultra_laundry.db`, jalankan lagi.

## Struktur file
```
app.py             -> seluruh aplikasi (logika DB, UI, HTML/CSS)
requirements.txt   -> daftar dependensi
run.bat            -> launcher Windows
ultra_laundry.db   -> database SQLite (dibuat otomatis)
```

## Perbaikan penting
Kode nota otomatis diperbarui setelah transaksi disimpan (flag `reset_kode_nota`),
jadi simpan nota berkali-kali tidak lagi kena error "Data Duplikat Ditolak".
