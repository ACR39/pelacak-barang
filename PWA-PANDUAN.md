# Pasang Pelacak Barang di layar utama HP (PWA)

## Yang perlu dilakukan sekali
1. Salin folder `static/pwa/` (4 gambar ikon) dan `pelacak/pwa.py` ke repositori, lalu push.
2. Tambahkan ini ke `.streamlit/config.toml` di repositori (gabungkan kalau berkasnya sudah ada):

   ```toml
   [server]
   enableStaticServing = true
   ```
3. Deploy ulang / restart aplikasi.

Tanpa langkah 2 aplikasi tetap jalan normal, hanya ikonnya tidak muncul.

## Memasang di HP
- **Android (Chrome):** buka alamat aplikasi, tekan titik tiga di kanan atas, pilih **Instal aplikasi**. Kalau pilihan itu tidak ada, pilih **Tambahkan ke layar utama**.
- **iPhone (Safari):** tombol Bagikan, lalu **Tambah ke Layar Utama**.

Setelah terpasang, aplikasi terbuka layar penuh tanpa bilah alamat, dengan ikon kotak hijau bergambar pin.

## Catatan
- Aplikasi tetap butuh internet. Streamlit berjalan di server, jadi mode offline tidak tersedia.
- Folder `static/` bisa dibuka siapa saja yang tahu alamatnya. Isinya hanya ikon, tidak ada data barang.
- Mengganti ikon: timpa keempat berkas di `static/pwa/` dengan nama yang sama (192, 512, maskable 512, dan apple-touch-icon 180 piksel). Pasang ulang di HP supaya ikon barunya terbaca.
