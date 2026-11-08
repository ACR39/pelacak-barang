# Pengingat lewat Telegram

Pesan harian dikirim GitHub Actions, jadi PC tidak perlu menyala. Isinya: kedaluwarsa, garansi (30 hari), waktu ganti, waktu cek, pinjaman jatuh tempo, dan barang yang perlu dibeli. Kalau tidak ada yang perlu diperhatikan, tidak ada pesan.

## Siapkan sekali
1. Di Telegram, chat **@BotFather**, kirim `/newbot`, ikuti langkahnya. Simpan **token** bot.
2. Buka bot barumu, tekan **Start**, kirim satu pesan apa saja.
3. Buka `https://api.telegram.org/bot<TOKEN>/getUpdates` di peramban. Cari `"chat":{"id": ...}`. Angka itu **chat ID**.
4. Di GitHub: repositori data, **Settings > Secrets and variables > Actions > New repository secret**. Buat dua secret:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
5. Salin folder `.github/` ke repositori (yang berisi `data.json`), lalu push.
6. Kalau nama berkas data bukan `data.json`, ubah `DATA_FILE` di `.github/workflows/pengingat-telegram.yml`.

## Uji
Tab **Actions > Pengingat Telegram > Run workflow**. Untuk melihat isi pesan tanpa mengirim, jalankan lokal:
`KERING=1 DATA_FILE=data.json python .github/scripts/kirim_pengingat.py`
Tambahkan `KIRIM_KOSONG=1` bila ingin tetap dikirimi pesan walau kosong.

## Catatan
- Jadwal 07:00 WIB (`0 0 * * *` UTC). Jam bisa meleset beberapa menit.
- GitHub menonaktifkan jadwal setelah 60 hari repositori tanpa aktivitas. Karena aplikasi menyimpan data ke repositori yang sama, ini jarang terjadi. Kalau terjadi, aktifkan lagi di tab Actions.
- Repositori data harus berisi workflow ini. Kalau repositori data privat, Actions privat tetap gratis dalam batas bulanan.
- Aturan di skrip meniru aplikasi. Kalau aturan di aplikasi berubah, perbarui `kirim_pengingat.py`.
