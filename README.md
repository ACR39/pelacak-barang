# Pelacak Barang Pribadi

Aplikasi Streamlit untuk mencatat di mana barang pribadi disimpan, lengkap dengan pantauan pinjaman, belanja, kedaluwarsa, dan nilai barang. Tampilannya mengikuti aplikasi Rekap Isian Pekerja.

## Menu

**Barang**
- **Cari barang**: cari nama, lokasi, kategori, catatan; filter lokasi, sub lokasi, kategori; tombol Lihat untuk detail dan foto
- **Kelola barang**: tambah, ubah, hapus, termasuk foto, harga, kedaluwarsa, garansi, dan penanda perlu dibeli
- **Pindah massal**: pindahkan banyak barang sekaligus ke lokasi baru
- **Riwayat perpindahan**: tercatat otomatis saat barang ditambah, dipindah, atau dihapus

**Pantauan**
- **Pinjam-meminjam**: barang yang kamu pinjamkan atau pinjam, jatuh tempo, tombol "Sudah kembali"
- **Daftar belanja**: barang yang ditandai perlu dibeli atau jumlahnya 0, bisa diunduh sebagai teks
- **Kedaluwarsa dan garansi**: daftar yang akan atau sudah lewat tanggalnya
- **Nilai barang**: total nilai (harga x jumlah) per lokasi dan kategori

**Master data** (admin): Lokasi, Sub lokasi, Kategori, Label QR, Cadangan dan pindah data

Contoh: lokasi "Lemari kamar", sub lokasi "Kotak 2", barang "Parfum".

## Pasang

1. Buat repo untuk kode (isi `app.py`, `requirements.txt`, `README.md`, `buat_hash.py`).
2. Buat repo **privat** terpisah untuk data, mis. `data-barang`. Isi README saja. `data.json` dan folder `fotos/` dibuat otomatis.
3. Buat token GitHub (fine-grained) dengan akses ke repo data saja, izin **Contents: Read and write**.
4. Deploy di share.streamlit.io, file utama `app.py`.
5. Isi Secrets (App > Settings > Secrets):

```toml
sesi_jam = 8
sesi_kunci = "isi-teks-acak-panjang"
app_url = "https://namaapp.streamlit.app"   # untuk label QR
zona_jam = 8                                # selisih jam dari UTC (WIB 7, WITA 8, WIT 9)

[github]
token = "github_pat_xxx"
repo = "usernamekamu/data-barang"
path = "data.json"
branch = "main"

[users.sumi]
nama = "Nama Kamu"
peran = "admin"
password_hash = "pbkdf2$..."
```

Buat `password_hash` dengan `python buat_hash.py`, lalu tempel hasilnya.

Tanpa bagian `[users]`, aplikasi memakai kata sandi tunggal dari secret `password = "..."`. Tanpa keduanya, aplikasi terbuka tanpa login (hanya untuk uji coba).

## Label QR

Menu Master data > Label QR membuat kode QR untuk tiap lokasi dan sub lokasi. Unduh lembar label (HTML), cetak, lalu tempel di kotak atau lemari. Saat dipindai, aplikasi terbuka dan langsung menampilkan isi lokasi itu (perlu login).

## Jalankan lokal

```
pip install -r requirements.txt
streamlit run app.py
```

Tanpa secrets, data disimpan ke `data_lokal.json` dan foto ke folder `fotos_lokal/`.

## Pindah dari versi lama

Kalau sudah punya `items.json` dari versi pertama, buka Master data > Cadangan dan pindah data lalu muat filenya. Formatnya otomatis diubah.
