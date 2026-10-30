# Pelacak Barang Pribadi

Aplikasi Streamlit untuk mencatat di mana barang pribadi disimpan. Tampilannya mengikuti aplikasi Rekap Isian Pekerja: sidebar gelap, kartu ringkasan, login per pengguna, dan Master data.

## Menu

- **Beranda**: ringkasan jumlah barang, grafik per lokasi dan kategori, barang yang terakhir diubah
- **Cari barang**: cari nama, lokasi, kategori, atau catatan, dengan filter lokasi dan kategori
- **Kelola barang**: tambah, ubah, hapus barang
- **Master data** (admin): Lokasi, Sub lokasi, Kategori, Cadangan dan pindah data

Contoh pengisian: lokasi "Lemari kamar", sub lokasi "Kotak 2", barang "Parfum".

## Pasang

1. Buat repo untuk kode (isi `app.py`, `requirements.txt`, `README.md`, `buat_hash.py`).
2. Buat repo **privat** terpisah untuk data, mis. `data-barang`. Isi README saja, `data.json` dibuat otomatis.
3. Buat token GitHub (fine-grained) dengan akses ke repo data saja, izin **Contents: Read and write**.
4. Deploy di share.streamlit.io, file utama `app.py`.
5. Isi Secrets (App > Settings > Secrets):

```toml
sesi_jam = 8
sesi_kunci = "isi-teks-acak-panjang"

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

## Jalankan lokal

```
pip install -r requirements.txt
streamlit run app.py
```

Tanpa secrets, data disimpan ke `data_lokal.json`.

## Pindah dari versi lama

Kalau sudah punya `items.json` dari versi pertama, buka Master data > Cadangan dan pindah data lalu muat filenya. Formatnya otomatis diubah, lokasi dan kategori dibuatkan dari teks lama.
