"""Rangka aplikasi: menyiapkan sesi, memilih halaman, menggambar sidebar dan kepala, lalu memanggil halaman yang dipilih."""
import html

import streamlit as st

from pelacak.akses import COOKIE_TEMA, _jam_sesi, cek_login, js_cookie, keluar
from pelacak.aktivitas import halaman_aktivitas, halaman_sampah
from pelacak.bantu import atur, pindah_halaman
from pelacak.barang import halaman_barang
from pelacak.belanja import halaman_belanja, halaman_paket
from pelacak.beranda import halaman_beranda, pesan_tenggat
from pelacak.cari import halaman_cari
from pelacak.ekspor import halaman_ekspor
from pelacak.impor import halaman_impor
from pelacak.inti import CSS_GELAP, D, adalah_admin, cfg_github, data_kosong, pasang_css
from pelacak.jarang_nilai import _tabel_tanggal, halaman_jarang, halaman_nilai
from pelacak.jelajah import halaman_jelajah, halaman_riwayat
from pelacak.master import (
    cadangan, daftar_sederhana, halaman_kelola_label, halaman_label, halaman_lokasi,
    halaman_pemilik, halaman_sublokasi,
)
from pelacak.opname import halaman_opname
from pelacak.pemeliharaan import halaman_pulih, halaman_ukuran
from pelacak.pengingat import halaman_pengingat
from pelacak.penyimpanan import ambil_snap, muat_ke_sesi
from pelacak.pindah import halaman_pindah
from pelacak.pinjam import halaman_pinjam
from pelacak.scan import halaman_scan
from pelacak.statistik import halaman_statistik
from pelacak.status import halaman_dibawa, halaman_perawatan
from pelacak.tampilan import halaman_tampilan, halaman_tampilan_kartu


UTAMA = ["Cari barang", "Scan barcode", "Jelajah lokasi", "Kelola barang", "Pindah massal", "Inventaris ulang", "Riwayat",
         "Tempat sampah"]
PANTAU = ["Pinjam-meminjam", "Dibawa, hilang, rusak", "Belanja", "Daftar bawaan", "Jarang dipakai",
          "Jatuh tempo", "Catatan perawatan", "Statistik"]
MASTER = ["Tempat dan lokasi", "Kategori dan label", "Label QR", "Ukuran data", "Cadangan dan pulihkan"]
IKON = {"Beranda": "home", "Cari barang": "search", "Kelola barang": "inventory_2", "Scan barcode": "barcode_scanner",
        "Jelajah lokasi": "account_tree", "Pindah massal": "swap_horiz", "Inventaris ulang": "fact_check",
        "Riwayat": "history", "Tempat sampah": "delete",
        "Pinjam-meminjam": "handshake", "Dibawa, hilang, rusak": "backpack", "Belanja": "shopping_cart",
        "Daftar bawaan": "luggage", "Jarang dipakai": "schedule", "Jatuh tempo": "event_busy",
        "Catatan perawatan": "build", "Statistik": "bar_chart",
        "Tampilan": "tune", "Ekspor dan impor": "import_export",
        "Tempat dan lokasi": "home_work", "Kategori dan label": "sell", "Label QR": "qr_code_2",
        "Ukuran data": "database", "Cadangan dan pulihkan": "backup"}
LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#34a874"/><stop offset="1" stop-color="#1f6b49"/></linearGradient></defs>'
        '<rect width="38" height="38" rx="10" fill="url(#g)"/>'
        '<path d="M19 8l9 4.5v11L19 28l-9-4.5v-11z" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M10 12.5l9 4.5 9-4.5M19 17v11" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>')
DESKRIPSI = {
    "Riwayat": "Perpindahan barang dan aktivitas (tambah, ubah, buang, pulihkan) yang tercatat otomatis.",
    "Jatuh tempo": "Pantau kedaluwarsa, masa garansi, dan barang yang perlu dicek rutin.",
    "Statistik": "Barang yang sering pindah, jumlah per lokasi, aktivitas bulanan, per pemilik, kelengkapan data, dan nilai barang.",
    "Tampilan": "Pilih kartu di Beranda dan keterangan di kartu barang. Bisa disimpan untuk semua perangkat.",
    "Tempat dan lokasi": "Tiga tingkat penyimpanan: tempat, lokasi, dan sub lokasi.",
    "Kategori dan label": "Kelola kategori, pemilik, dan label barang: ubah nama atau gabungkan yang ganda.",
    "Cadangan dan pulihkan": "Unduh cadangan data, muat dari berkas, atau pulihkan ke versi sebelumnya.",
    "Beranda": "Ringkasan barang, hal yang perlu perhatian, dan grafik.",
    "Cari barang": "Cari barang berdasarkan nama, lokasi, kategori, atau catatan.",
    "Kelola barang": "Tambah, ubah, atau hapus barang beserta lokasi, foto, dan tanggalnya.",
    "Pindah massal": "Pindahkan banyak barang sekaligus ke lokasi lain, misalnya saat membereskan kotak.",
    "Inventaris ulang": "Cocokkan isi satu lokasi dengan keadaan sebenarnya: centang yang ada, koreksi jumlah, tandai yang hilang.",
    "Dibawa, hilang, rusak": "Barang yang sedang dibawa keluar, belum ketemu, rusak, atau sedang diservis.",
    "Catatan perawatan": "Riwayat servis, perbaikan, dan perawatan tiap barang beserta biayanya.",
    "Ukuran data": "Pantau besar data dan foto di penyimpanan, dan bersihkan foto yang tidak terpakai.",
    "Jelajah lokasi": "Telusuri isi tiap tempat, lokasi, dan sub lokasi, lengkap dengan jumlah barangnya.",
    "Tempat sampah": "Barang yang dibuang disimpan 30 hari di sini, bisa dipulihkan sebelum hilang permanen.",
    "Pinjam-meminjam": "Catat barang yang kamu pinjamkan atau yang kamu pinjam, lengkap dengan tenggatnya.",
    "Belanja": "Stok menipis atau habis (otomatis) dan rencana barang baru yang ingin dibeli, dalam satu daftar belanja.",
    "Daftar bawaan": "Daftar barang untuk dibawa (liburan, pindahan, dll.) yang bisa dicentang satu per satu.",
    "Jarang dipakai": "Barang yang sudah lama tidak dipakai, untuk bahan membereskan atau melepas barang.",
    "Scan barcode": "Foto barcode di kemasan untuk menemukan barang, atau menambahkannya dengan nama yang terisi otomatis.",
    "Ekspor dan impor": "Unduh daftar barang sebagai Excel atau PDF untuk dicetak, atau tambah banyak barang sekaligus dari file Excel atau CSV.",
    "Label QR": "Cetak label QR untuk ditempel di lemari atau kotak. Dipindai, langsung muncul isinya.",
}


def siapkan_sesi():
    """Login, muat data ke sesi, tema, dan pembukaan lewat tautan QR."""
    cek_login()
    if st.session_state.get("pasang_cookie"):
        js_cookie(st.session_state.pop("pasang_cookie"), int(_jam_sesi() * 3600))

    if "data" not in st.session_state:
        try:
            muat_ke_sesi()
        except Exception as e:
            st.error(f"Data tidak bisa dimuat: {e}")
            st.stop()

    for kunci, awal in data_kosong().items():
        D.setdefault(kunci, awal)

    st.session_state["_snap"] = ambil_snap()

    # Mode gelap: pilihan terakhir diingat lewat cookie peramban.
    if "gelap" not in st.session_state:
        try:
            st.session_state.gelap = st.context.cookies.get(COOKIE_TEMA, "") == "gelap"
        except Exception:
            st.session_state.gelap = False
    if st.session_state.gelap:
        st.markdown(CSS_GELAP, unsafe_allow_html=True)

    # Dibuka dari pindaian label QR: ?lokasi=<id>&sub=<id> langsung membuka daftar isi tempat itu.
    _qp_brg = st.query_params.get("barang")
    if _qp_brg:
        _brg_qr = next((x for x in D["barang"] if x["id"] == _qp_brg), None)
        if _brg_qr:
            st.session_state.halaman = "Cari barang"
            for _k in ("cari_tempat", "cari_lok", "cari_sub", "cari_kat"):
                st.session_state[_k] = "semua"
            st.session_state.cari_q = _brg_qr["nama"].lower()
            st.session_state.cari_fav = False
            st.session_state.cari_tag = []
        st.query_params.clear()
    _qp_lok = st.query_params.get("lokasi")
    _qp_tem = st.query_params.get("tempat")
    if _qp_lok or _qp_tem:
        _lok_qr = next((x for x in D["lokasi"] if x["id"] == _qp_lok), None) if _qp_lok else None
        if _lok_qr:
            _qp_sub = st.query_params.get("sub", "")
            st.session_state.halaman = "Cari barang"
            st.session_state.cari_tempat = _lok_qr.get("tempat") or "semua"
            st.session_state.cari_lok = _qp_lok
            st.session_state.cari_sub = _qp_sub if any(
                x["id"] == _qp_sub and x["lokasi"] == _qp_lok for x in D["sublokasi"]) else "semua"
            st.session_state.cari_kat = "semua"
            st.session_state.cari_q = ""
        elif _qp_tem and any(t["id"] == _qp_tem for t in D["tempat"]):
            st.session_state.halaman = "Cari barang"
            st.session_state.cari_tempat = _qp_tem
            st.session_state.cari_lok = "semua"
            st.session_state.cari_sub = "semua"
            st.session_state.cari_kat = "semua"
            st.session_state.cari_q = ""
        st.query_params.clear()


def peringatan_uji():
    # ------------------------------------------------------------------- tampilan
    if not cfg_github():
        st.warning("Mode uji coba: data disimpan di file lokal dan bisa hilang saat aplikasi "
                   "dimulai ulang. Isi pengaturan GitHub (lihat README) agar data permanen.")


def pilih_halaman():
    """Daftar menu Pengaturan (admin melihat lebih banyak) dan halaman yang sedang dibuka."""
    PENGATURAN = ["Tampilan", "Ekspor dan impor"] + (MASTER if adalah_admin() else [])
    HALAMAN = ["Beranda"] + UTAMA + PANTAU + PENGATURAN
    if st.session_state.get("halaman") not in HALAMAN:
        st.session_state.halaman = "Beranda"
    halaman = st.session_state.halaman
    return PENGATURAN, halaman


def tampilkan_sidebar(halaman, PENGATURAN):
    with st.sidebar:
        st.markdown(f'<div class="brand">{LOGO}<div><div class="b1">Pelacak Barang</div>'
                    '<div class="b2">Di mana barangku?</div></div></div>', unsafe_allow_html=True)
        def tombol_nav(h):
            st.button(h, key=f"nav_{h}", use_container_width=True, icon=f":material/{IKON[h]}:",
                      type="primary" if h == halaman else "secondary", on_click=pindah_halaman, args=(h,))

        st.markdown('<div class="grup">UTAMA</div>', unsafe_allow_html=True)
        tombol_nav("Beranda")
        st.markdown('<div class="grup">MENU</div>', unsafe_allow_html=True)
        with st.expander("Barang", icon=":material/inventory_2:", expanded=halaman in UTAMA):
            for h in UTAMA:
                tombol_nav(h)
        with st.expander("Pantau", icon=":material/monitoring:", expanded=halaman in PANTAU):
            for h in PANTAU:
                tombol_nav(h)
        with st.expander("Pengaturan", icon=":material/settings:", expanded=halaman in PENGATURAN):
            for h in PENGATURAN:
                tombol_nav(h)
        st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
        st.toggle("Mode gelap", key="gelap", on_change=atur, args=("tema_ubah", True))
        if st.session_state.pop("tema_ubah", False):
            js_cookie("gelap" if st.session_state.gelap else "terang", 31536000, COOKIE_TEMA)
        if st.button("Muat ulang", key="nav_muat", use_container_width=True, icon=":material/refresh:",
                     help="Ambil data terbaru dari penyimpanan"):
            muat_ke_sesi()
            st.rerun()
        if cfg_github():
            st.caption(f"Data: {cfg_github()['repo']}")
        _us = st.session_state.get("user")
        if _us:
            st.markdown(f'<div class="pengguna sb"><div class="av">{html.escape(_us["nama"][:1].upper())}</div><div>'
                        f'<div class="nm">{html.escape(_us["nama"])}</div>'
                        f'<div class="pr">{html.escape(_us["peran"])}</div></div></div>', unsafe_allow_html=True)
            st.button("Keluar", key="nav_keluar", use_container_width=True,
                      icon=":material/logout:", on_click=keluar)


def tampilkan_kepala(halaman, PENGATURAN):
    _grup = ("PENGATURAN" if halaman in PENGATURAN else "RINGKASAN" if halaman == "Beranda"
             else "PANTAU" if halaman in PANTAU else "BARANG")
    st.markdown(f'<div class="kepala"><div><div class="eyebrow">{_grup}</div>'
                f'<div class="judul-hal">{html.escape(halaman)}</div>'
                f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div></div>',
                unsafe_allow_html=True)


def tampilkan_tenggat(halaman):
    tenggat = pesan_tenggat()
    if tenggat and halaman in ("Beranda", "Pinjam-meminjam"):
        st.warning("🔔 **Tenggat pengembalian hari ini**\n\n" + "\n".join(f"- {t}" for t in tenggat))
    if tenggat and not st.session_state.get("toast_tenggat"):
        st.session_state.toast_tenggat = True
        st.toast(f"{len(tenggat)} peminjaman jatuh tempo hari ini", icon="🔔")


def tampilkan_halaman(halaman):
    st.session_state["_n_lamp"] = 0
    if halaman == "Beranda":
        halaman_beranda()
    if halaman == "Cari barang":
        halaman_cari()
    if halaman == "Kelola barang":
        halaman_barang()
    if halaman == "Inventaris ulang":
        halaman_opname()
    if halaman == "Pindah massal":
        halaman_pindah()
    if halaman == "Jelajah lokasi":
        halaman_jelajah()
    if halaman == "Tempat sampah":
        halaman_sampah()
    if halaman == "Dibawa, hilang, rusak":
        halaman_dibawa()
    if halaman == "Catatan perawatan":
        halaman_perawatan()
    if halaman == "Pinjam-meminjam":
        halaman_pinjam()
    if halaman == "Belanja":
        halaman_belanja()
    if halaman == "Scan barcode":
        halaman_scan()
    if halaman == "Ekspor dan impor":
        t_ekspor, t_impor = st.tabs(["Ekspor", "Impor"])
        with t_ekspor:
            halaman_ekspor()
        with t_impor:
            halaman_impor()
    if halaman == "Daftar bawaan":
        halaman_paket()
    if halaman == "Jarang dipakai":
        halaman_jarang()
    if halaman == "Riwayat":
        t_p, t_a = st.tabs(["Perpindahan", "Aktivitas"])
        with t_p:
            halaman_riwayat()
        with t_a:
            halaman_aktivitas()
    if halaman == "Statistik":
        t_s, t_n = st.tabs(["Ringkasan", "Nilai barang"])
        with t_s:
            halaman_statistik()
        with t_n:
            halaman_nilai()
    if halaman == "Jatuh tempo":
        t_k, t_g, t_c = st.tabs(["Kedaluwarsa", "Garansi", "Cek berkala"])
        with t_k:
            _tabel_tanggal("kedaluwarsa", "Kedaluwarsa")
        with t_g:
            _tabel_tanggal("garansi", "Garansi sampai")
        with t_c:
            halaman_pengingat()
    if halaman == "Tampilan":
        t_b, t_k = st.tabs(["Beranda", "Kartu barang"])
        with t_b:
            halaman_tampilan()
        with t_k:
            halaman_tampilan_kartu()
    if adalah_admin() and halaman == "Tempat dan lokasi":
        t_t, t_l, t_s = st.tabs(["Tempat", "Lokasi", "Sub lokasi"])
        with t_t:
            daftar_sederhana("Tempat", "tempat", "Tempat besar yang menyimpan barang, misalnya Rumah A, Rumah B, atau Kantor. "
                             "Menghapus tempat tidak menghapus lokasinya, hanya melepasnya dari tempat itu.")
        with t_l:
            halaman_lokasi()
        with t_s:
            halaman_sublokasi()
    if adalah_admin() and halaman == "Kategori dan label":
        t_k, t_p, t_l = st.tabs(["Kategori", "Pemilik", "Label"])
        with t_k:
            daftar_sederhana("Kategori", "kategori", "Pengelompokan jenis barang, misalnya pakaian atau perawatan diri. "
                             "Boleh dikosongkan kalau tidak diperlukan.")
        with t_p:
            halaman_pemilik()
        with t_l:
            halaman_kelola_label()
    if adalah_admin() and halaman == "Label QR":
        halaman_label()
    if adalah_admin() and halaman == "Ukuran data":
        halaman_ukuran()
    if adalah_admin() and halaman == "Cadangan dan pulihkan":
        t_c, t_p = st.tabs(["Cadangan", "Titik pulih"])
        with t_c:
            cadangan()
        with t_p:
            halaman_pulih()


def jalankan():
    pasang_css()
    siapkan_sesi()
    peringatan_uji()
    PENGATURAN, halaman = pilih_halaman()
    tampilkan_sidebar(halaman, PENGATURAN)
    tampilkan_kepala(halaman, PENGATURAN)
    tampilkan_tenggat(halaman)
    tampilkan_halaman(halaman)
