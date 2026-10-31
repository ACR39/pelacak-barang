# Pelacak Barang Pribadi

Aplikasi Streamlit untuk mencatat di mana barang pribadi disimpan. Data tersimpan di repo GitHub privat, jadi tidak hilang saat aplikasi restart.

## Menu

**Beranda**: ringkasan, daftar hal yang perlu perhatian (kedaluwarsa, garansi, pinjaman lewat tenggat, perlu beli), grafik.

**Barang**
- **Cari barang**: cari nama, lokasi, kategori, catatan. Filter tempat, lokasi, sub lokasi, kategori. Tampilan **Kartu** (foto bulat, jumlah besar di kanan) atau **Tabel**, dengan penanda "Perlu beli" atau "Dipinjam".
- **Kelola barang**: tambah, ubah, hapus (tampilan Kartu atau Tabel). Isian: lokasi, sub lokasi, kategori, jumlah, harga beli, tanggal kedaluwarsa, garansi, tanda habis, foto, catatan.
- **Pindah massal**: pilih banyak barang, pindahkan sekaligus ke lokasi lain.
- **Riwayat perpindahan**: tercatat otomatis (dari mana ke mana, kapan, oleh siapa).

**Pantau**
- **Pinjam-meminjam**: barang yang kamu pinjamkan atau yang kamu pinjam, tenggat, tombol "Sudah kembali".
- **Perlu beli**: barang bertanda habis atau berjumlah nol, jadi daftar belanja yang bisa diunduh.
- **Kedaluwarsa dan garansi**: urut dari yang paling dekat, dengan filter 30 dan 90 hari.
- **Nilai barang**: total nilai (harga x jumlah), per lokasi dan kategori.

**Master data** (admin): Tempat, Lokasi, Sub lokasi, Kategori, **Label QR**, Cadangan dan pindah data.

## Label QR

1. Buat lokasi dan sub lokasi dulu.
2. Buka Master data > Label QR, isi alamat aplikasi (atau simpan di Secrets sebagai `app_url`).
3. Unduh lembar label, buka di peramban, cetak (Ctrl+P), tempel di lemari atau kotak.
4. Pindai dengan kamera HP: aplikasi terbuka (setelah login) langsung ke daftar isi tempat itu.

## Pasang

1. Buat repo untuk kode (isi `app.py`, `requirements.txt`, `README.md`, `buat_hash.py`).
2. Buat repo **privat** terpisah untuk data, mis. `data-barang`. Isi README saja. `data.json` dan folder `foto/` dibuat otomatis.
3. Buat token GitHub (fine-grained) dengan akses ke repo data saja, izin **Contents: Read and write**.
4. Deploy di share.streamlit.io, file utama `app.py`.
5. Isi Secrets (App > Settings > Secrets):

```toml
sesi_jam = 8
sesi_kunci = "isi-teks-acak-panjang"
app_url = "https://namaapp.streamlit.app"

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

Buat `password_hash` dengan `python buat_hash.py`, lalu tempel hasilnya. `app_url` boleh diisi belakangan setelah alamat aplikasi diketahui.

Tanpa bagian `[users]`, aplikasi memakai kata sandi tunggal dari secret `password = "..."`. Tanpa keduanya, aplikasi terbuka tanpa login (hanya untuk uji coba).

## Catatan

- Foto dikecilkan otomatis (maks 900 px, JPEG) dan disimpan di folder `foto/` pada repo data. Cadangan `data.json` tidak memuat foto.
- Waktu pencatatan memakai WIB.
- Riwayat perpindahan menyimpan maksimal 1000 catatan terakhir.
- Data lama tetap terbaca: kolom baru (harga, kedaluwarsa, garansi, foto, pinjam, riwayat) kosong sampai diisi.

## Jalankan lokal

```
pip install -r requirements.txt
streamlit run app.py
```

Tanpa secrets, data disimpan ke `data_lokal.json` dan foto ke folder `foto_lokal/`.
