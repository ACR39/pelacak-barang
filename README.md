# Pelacak Barang Pribadi

Aplikasi Streamlit untuk mencatat di mana barang pribadi disimpan. Data disimpan di file `items.json` pada repo GitHub (privat), jadi tidak hilang saat aplikasi restart.

## Cara pasang

1. Buat repo GitHub **privat**, mis. `pelacak-barang`. Unggah `app.py`, `requirements.txt`, `README.md`.
2. Buat token: GitHub → Settings → Developer settings → Fine-grained tokens. Beri akses hanya ke repo ini, izin **Contents: Read and write**.
3. Buka https://share.streamlit.io, pilih repo, file utama `app.py`.
4. Di Streamlit Cloud: App → Settings → Secrets, isi:

```toml
app_password = "kata-sandi-kamu"

[github]
token = "github_pat_xxx"
repo = "usernamekamu/pelacak-barang"
branch = "main"
```

`app_password` opsional, tapi disarankan agar aplikasi tidak bisa dibuka orang lain.

## Jalankan lokal

```
pip install -r requirements.txt
streamlit run app.py
```

Tanpa secrets, data disimpan ke `items_local.json`.

## Fitur

- Cari berdasarkan nama, lokasi, atau catatan, plus filter kategori dan lokasi
- Tambah, ubah, hapus barang
- Ringkasan isi per lokasi
- Unduh cadangan JSON
