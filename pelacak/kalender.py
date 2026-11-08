"""Kalender (.ics): jatuh tempo barang untuk diimpor ke Google Calendar, kalender HP, atau Outlook."""
from datetime import date, timedelta

import streamlit as st

from pelacak.bantu import ganti_tiap_b
from pelacak.beranda import cek_tiap_b
from pelacak.inti import D, hari_ini, iso_ke_date

JENIS = [("kedaluwarsa", "Kedaluwarsa", True), ("garansi", "Garansi berakhir", True),
         ("ganti", "Waktu ganti", True), ("cek", "Cek berkala", True), ("pinjam", "Tenggat pinjaman", True)]


def _esc(t: str) -> str:
    return (str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\r", "")
            .replace("\n", "\\n"))


def _lipat(baris: str) -> str:
    """Potong baris lebih dari 75 byte sesuai RFC 5545 (lanjutan diawali spasi)."""
    data, hasil = baris.encode("utf-8"), []
    while len(data) > 75:
        potong = 75
        while potong > 0 and (data[potong] & 0xC0) == 0x80:     # jangan memotong di tengah karakter
            potong -= 1
        hasil.append(data[:potong].decode("utf-8"))
        data = b" " + data[potong:]
    hasil.append(data.decode("utf-8"))
    return "\r\n".join(hasil)


def kejadian(jenis: set, hari_maks: int = 365, lewat: int = 0) -> list:
    """[(tanggal, judul, keterangan, uid)] untuk jenis yang dipilih, dari `lewat` hari lalu sampai `hari_maks` ke depan."""
    h = hari_ini()
    awal, akhir = h - timedelta(days=lewat), h + timedelta(days=hari_maks)
    hasil = []

    def tambah(d, judul, ket, uid):
        if d and awal <= d <= akhir:
            hasil.append((d, judul, ket, uid))

    for b in D["barang"]:
        nama = b.get("nama", "?")
        if "kedaluwarsa" in jenis:
            tambah(iso_ke_date(b.get("kedaluwarsa")), f"Kedaluwarsa: {nama}", "Cek dan buang atau pakai barang ini.",
                   f"exp-{b['id']}")
        if "garansi" in jenis:
            tambah(iso_ke_date(b.get("garansi")), f"Garansi berakhir: {nama}",
                   "Ajukan klaim sebelum garansi habis kalau ada masalah.", f"gar-{b['id']}")
        if "ganti" in jenis and ganti_tiap_b(b):
            ref = (iso_ke_date(b.get("diganti")) or iso_ke_date(b.get("dibeli")) or iso_ke_date(b.get("diubah")) or h)
            tambah(ref + timedelta(days=ganti_tiap_b(b)), f"Waktunya ganti: {nama}", "Sesuai pengingat ganti.",
                   f"ganti-{b['id']}")
        if "cek" in jenis and cek_tiap_b(b):
            ref = iso_ke_date(b.get("cek_terakhir")) or iso_ke_date(b.get("diubah")) or h
            tambah(ref + timedelta(days=cek_tiap_b(b)), f"Waktunya cek: {nama}", "Sesuai pengingat cek berkala.",
                   f"cek-{b['id']}")
    if "pinjam" in jenis:
        for p in D["pinjam"]:
            if p.get("kembali"):
                continue
            if p.get("arah") == "keluar":
                j = f"{p.get('orang', '?')} kembalikan {p.get('nama', '?')}"
            else:
                j = f"Kembalikan {p.get('nama', '?')} ke {p.get('orang', '?')}"
            tambah(iso_ke_date(p.get("tenggat")), j, "Tenggat pengembalian.", f"pinjam-{p.get('id', j)}")
    return sorted(hasil, key=lambda x: (x[0], x[1]))


def bangun_ics(daftar: list, pengingat_hari: int = 1) -> str:
    """Teks .ics. Tiap kejadian satu hari penuh, dengan alarm `pengingat_hari` hari sebelumnya (0 = tanpa alarm)."""
    cap = hari_ini().strftime("%Y%m%d") + "T000000Z"
    baris = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Pelacak Barang//ID", "CALSCALE:GREGORIAN",
             "X-WR-CALNAME:Pelacak Barang"]
    for d, judul, ket, uid in daftar:
        baris += ["BEGIN:VEVENT", f"UID:{uid}@pelacak-barang", f"DTSTAMP:{cap}",
                  f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                  f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
                  f"SUMMARY:{_esc(judul)}", f"DESCRIPTION:{_esc(ket)}", "TRANSP:TRANSPARENT"]
        if pengingat_hari:
            baris += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(judul)}",
                      f"TRIGGER:-P{int(pengingat_hari)}D", "END:VALARM"]
        baris.append("END:VEVENT")
    baris.append("END:VCALENDAR")
    return "\r\n".join(_lipat(x) for x in baris) + "\r\n"


def halaman_kalender():
    with st.container(key="kartu_kalender"):
        st.caption("Unduh berkas .ics lalu buka di HP atau impor di Google Calendar (Pengaturan > Impor). "
                   "Berkas ini potret hari ini; unduh lagi kalau ada perubahan.")
        pil = st.multiselect("Yang dimasukkan", [k for k, _, _ in JENIS], default=[k for k, _, a in JENIS if a],
                             format_func=dict((k, n) for k, n, _ in JENIS).get, key="kal_jenis")
        c1, c2 = st.columns(2)
        hari = c1.selectbox("Sampai berapa lama ke depan", [90, 180, 365, 730], index=2, key="kal_hari",
                            format_func=lambda n: f"{n} hari")
        alarm = c2.selectbox("Pengingat sebelum hari H", [0, 1, 3, 7], index=2, key="kal_alarm",
                             format_func=lambda n: "Tanpa pengingat" if n == 0 else f"{n} hari sebelumnya")
        daftar = kejadian(set(pil), hari, lewat=0)
        st.caption(f"{len(daftar)} kejadian akan masuk ke kalender.")
        if not daftar:
            st.info("Belum ada tanggal yang cocok. Isi tanggal kedaluwarsa, garansi, atau pengingat di Kelola barang.")
            return
        st.download_button("Unduh kalender (.ics)", bangun_ics(daftar, alarm), file_name="pelacak-barang.ics",
                           mime="text/calendar", type="primary", icon=":material/calendar_month:")
        for d, judul, _, _ in daftar[:10]:
            st.markdown(f"- {d.strftime('%d/%m/%Y')} · {judul}")
        if len(daftar) > 10:
            st.caption(f"…dan {len(daftar) - 10} kejadian lainnya.")
