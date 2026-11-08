"""Kirim ringkasan pengingat Pelacak Barang ke Telegram. Dijalankan GitHub Actions, tanpa Streamlit.

Variabel lingkungan:
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID   wajib (kecuali KERING=1)
  DATA_FILE        berkas data JSON (bawaan: data.json)
  TELEGRAM_API_BASE  untuk uji (bawaan: https://api.telegram.org)
  KERING=1         cetak pesan saja, tidak mengirim
  KIRIM_KOSONG=1   tetap kirim walau tidak ada yang perlu diperhatikan
"""
import html
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))
BATAS = 4096


def hari_ini() -> date:
    return datetime.now(WIB).date()


def tgl(s):
    try:
        return date.fromisoformat(s) if s else None
    except Exception:
        return None


def sisa(s):
    d = tgl(s)
    return (d - hari_ini()).days if d else None


def angka(b, k, bawaan=0):
    try:
        return max(int(b.get(k, bawaan) or 0), 0)
    except Exception:
        return bawaan


def fmt(s):
    d = tgl(s)
    return d.strftime("%d/%m/%Y") if d else ""


def perkiraan_sisa_hari(b: dict):
    """Meniru perkiraan_habis() di pelacak/harga.py. None kalau datanya belum cukup."""
    r = [x for x in b.get("riwayat_harga", []) if angka(x, "harga")]
    if not r and angka(b, "harga"):
        r = [{"tgl": b.get("dibeli"), "jumlah": max(angka(b, "jumlah", 1), 1)}]
    r = sorted([x for x in r if tgl(x.get("tgl"))], key=lambda x: x["tgl"])
    if len(r) < 2:
        return None
    selang = (tgl(r[-1]["tgl"]) - tgl(r[0]["tgl"])).days
    terpakai = sum(angka(x, "jumlah", 1) or 1 for x in r[:-1])
    if selang <= 0 or terpakai <= 0:
        return None
    return int(angka(b, "jumlah", 1) / (terpakai / selang))


def kumpulkan(d: dict) -> list:
    """Kembalikan [(judul, [baris])] sesuai aturan di aplikasi."""
    barang = [b for b in d.get("barang", []) if isinstance(b, dict)]
    h = hari_ini()
    bagian = []

    def tambah(judul, baris):
        if baris:
            bagian.append((judul, baris))

    lewat, dekat, gar, ganti, cek = [], [], [], [], []
    for b in sorted(barang, key=lambda x: str(x.get("nama", "")).lower()):
        nama = b.get("nama", "?")
        s = sisa(b.get("kedaluwarsa"))
        if s is not None:
            if s < 0:
                lewat.append(f"{nama} (lewat {-s} hari)")
            elif s <= 30:
                dekat.append(f"{nama} ({'hari ini' if s == 0 else f'{s} hari lagi'})")
        g = sisa(b.get("garansi"))
        if g is not None and 0 <= g <= 30:
            gar.append(f"{nama} (garansi habis {fmt(b['garansi'])})")
        n = angka(b, "ganti_tiap")
        if n:
            ref = tgl(b.get("diganti")) or tgl(b.get("dibeli")) or tgl(b.get("diubah")) or h
            r = (ref + timedelta(days=n) - h).days
            if r <= 30:
                ganti.append(f"{nama} ({f'telat {-r} hari' if r < 0 else f'{r} hari lagi'})")
        n = angka(b, "cek_tiap")
        if n:
            ref = tgl(b.get("cek_terakhir")) or tgl(b.get("diubah")) or h
            r = (ref + timedelta(days=n) - h).days
            if r <= 0:
                cek.append(f"{nama} ({f'telat {-r} hari' if r < 0 else 'hari ini'})")
    tambah("⛔ Sudah kedaluwarsa", lewat)
    tambah("⏳ Kedaluwarsa dalam 30 hari", dekat)
    tambah("🛡 Garansi habis dalam 30 hari", gar)
    tambah("🔧 Waktunya diganti", ganti)
    tambah("🔍 Waktunya dicek", cek)

    pinjam = []
    for p in d.get("pinjam", []):
        s = sisa(p.get("tenggat"))
        if p.get("kembali") or s is None or s > 0:
            continue
        status = "hari ini" if s == 0 else f"lewat {-s} hari"
        if p.get("arah") == "keluar":
            pinjam.append(f"{p.get('orang', '?')} belum mengembalikan {p.get('nama', '?')} ({status})")
        else:
            pinjam.append(f"Kembalikan {p.get('nama', '?')} ke {p.get('orang', '?')} ({status})")
    tambah("🤝 Pinjaman jatuh tempo", pinjam)

    klaim = []
    for k in d.get("klaim", []):
        t = tgl(k.get("tgl"))
        if k.get("status") in ("Diajukan", "Diproses") and t and (hari_ini() - t).days >= 14:
            klaim.append(f"{k.get('nama', '?')} ({k['status'].lower()}, {(hari_ini() - t).days} hari)")
    tambah("📨 Klaim garansi belum selesai (lebih dari 14 hari)", klaim)

    beli, hampir = [], []
    for b in barang:
        if not (b.get("habis") or angka(b, "jumlah", 1) == 0):
            p = perkiraan_sisa_hari(b)
            if p is not None and p <= 14:
                hampir.append(f"{b.get('nama', '?')} ({'sudah habis' if p <= 0 else f'habis sekitar {p} hari lagi'})")
        m, j = angka(b, "minimum"), angka(b, "jumlah", 1)
        if b.get("habis") or j == 0 or (m > 0 and j <= m):
            beli.append(f"{b.get('nama', '?')} (sisa {j})")
    tambah("🛒 Perlu dibeli", sorted(beli, key=str.lower))
    tambah("📉 Diperkirakan habis dalam 14 hari", sorted(hampir, key=str.lower))
    return bagian


def susun(bagian: list) -> list:
    """Ubah ke pesan HTML Telegram, dipecah per baris kalau melebihi batas 4096 karakter."""
    baris = [f"<b>Pengingat Pelacak Barang</b> · {hari_ini().strftime('%d/%m/%Y')}"]
    for judul, isi in bagian:
        baris.append(f"\n<b>{html.escape(judul)}</b>")
        baris += [f"• {html.escape(x)[:500]}" for x in isi]
    pesan, kini = [], ""
    for x in baris:
        tambah = x if not kini else "\n" + x
        if kini and len(kini) + len(tambah) > BATAS - 50:
            pesan.append(kini)
            kini = "<i>(lanjutan)</i>\n" + x.lstrip("\n")
        else:
            kini += tambah
    pesan.append(kini)
    return pesan


def kirim(token: str, chat: str, teks: str):
    dasar = os.environ.get("TELEGRAM_API_BASE", "https://api.telegram.org").rstrip("/")
    isi = json.dumps({"chat_id": chat, "text": teks, "parse_mode": "HTML",
                      "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"{dasar}/bot{token}/sendMessage", data=isi,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        j = json.loads(r.read().decode())
    if not j.get("ok"):
        raise RuntimeError(f"Telegram menolak: {j}")


def main() -> int:
    berkas = os.environ.get("DATA_FILE", "data.json")
    try:
        with open(berkas, encoding="utf-8") as f:
            d = json.load(f)
    except FileNotFoundError:
        print(f"Berkas data tidak ditemukan: {berkas}")
        return 1
    if not isinstance(d, dict):
        print("Format data lama (daftar), buka aplikasi sekali supaya dikonversi.")
        return 1
    bagian = kumpulkan(d)
    if not bagian and os.environ.get("KIRIM_KOSONG") != "1":
        print("Tidak ada yang perlu diperhatikan. Tidak mengirim pesan.")
        return 0
    pesan = susun(bagian) if bagian else [f"<b>Pengingat Pelacak Barang</b> · {hari_ini().strftime('%d/%m/%Y')}\n\nTidak ada yang perlu diperhatikan hari ini 🌿"]
    if os.environ.get("KERING") == "1":
        print("\n--- pesan berikutnya ---\n".join(pesan))
        return 0
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print("TELEGRAM_BOT_TOKEN dan TELEGRAM_CHAT_ID belum diisi.")
        return 1
    for p in pesan:
        kirim(token, chat, p)
    print(f"Terkirim: {len(pesan)} pesan.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
