"""Pengaturan tampilan Beranda dan kartu barang."""
import streamlit as st

from pelacak.akses import js_cookie
from pelacak.bantu import (
    COOKIE_KARTU, SEKSI_KARTU, atur_kartu, kartu_barang_html, muat_kartu_sembunyi,
    pindah_halaman, selesai_simpan, ubah_kartu,
)
from pelacak.beranda import (
    COOKIE_BERANDA, SEKSI_BERANDA, atur_beranda, muat_beranda_sembunyi, ubah_beranda,
)
from pelacak.inti import D


# ------------------------------------------------------------ tampilan Beranda (Pengaturan)
def simpan_bersama(kunci: str, daftar: list):
    D.setdefault("pengaturan", {})[kunci] = list(daftar)
    selesai_simpan("Disimpan sebagai bawaan untuk semua perangkat.")


def tombol_bersama(kunci: str, daftar: list, pakai):
    """Dua tombol: simpan pilihan perangkat ini sebagai bawaan bersama, atau ambil bawaan bersama ke perangkat ini."""
    st.markdown("**Semua perangkat**")
    st.caption("Pilihan di atas hanya berlaku di perangkat ini. Simpan sebagai bawaan bersama supaya perangkat lain "
               "(atau HP baru, atau setelah cookie terhapus) ikut memakainya.")
    ada = kunci in D.get("pengaturan", {})
    c1, c2 = st.columns(2)
    if c1.button("Simpan untuk semua perangkat", key=f"bersama_{kunci}", type="primary", use_container_width=True):
        simpan_bersama(kunci, daftar)
    c2.button("Pakai bawaan bersama", key=f"ambil_{kunci}", use_container_width=True, disabled=not ada,
              on_click=pakai, args=(list(D.get("pengaturan", {}).get(kunci, [])),),
              help=None if ada else "Belum ada bawaan bersama yang disimpan.")


def halaman_tampilan():
    muat_beranda_sembunyi()
    sembunyi = set(st.session_state.beranda_sembunyi)
    with st.container(key="kartu_barang"):
        st.markdown("**Kartu yang tampil di Beranda**")
        st.caption("Centang kartu yang ingin ditampilkan. Pilihan ini berlaku di perangkat ini.")
        for k, lab in SEKSI_BERANDA:
            st.checkbox(lab, value=k not in sembunyi, key=f"bs_{k}", on_change=ubah_beranda)
        c1, c2, c3 = st.columns(3)
        c1.button("Tampilkan semua", key="bs_semua", on_click=atur_beranda, args=([],), use_container_width=True)
        c2.button("Hanya ringkasan", key="bs_min", on_click=atur_beranda,
                  args=([k for k, _ in SEKSI_BERANDA if k != "ringkasan"],), use_container_width=True)
        c3.button("Lihat Beranda", key="bs_lihat", on_click=pindah_halaman, args=("Beranda",),
                  type="primary", use_container_width=True)
        tombol_bersama("beranda", st.session_state.beranda_sembunyi, atur_beranda)
    if st.session_state.pop("beranda_ubah", False):
        js_cookie(",".join(st.session_state.beranda_sembunyi) or "-", 31536000, COOKIE_BERANDA)


def halaman_tampilan_kartu():
    sembunyi = muat_kartu_sembunyi()
    with st.container(key="kartu_g_tkartu"):
        st.markdown("**Keterangan yang tampil di kartu barang**")
        st.caption("Centang keterangan yang ingin ditampilkan di kartu barang (Cari barang, Kelola barang, dan menu lain). "
                   "Nama, foto, dan lencana status tetap tampil. Pilihan ini berlaku di perangkat ini.")
        for k, lab in SEKSI_KARTU:
            st.checkbox(lab, value=k not in sembunyi, key=f"ks_{k}", on_change=ubah_kartu)
        c1, c2, c3 = st.columns(3)
        c1.button("Tampilkan semua", key="ks_semua", on_click=atur_kartu, args=([],), use_container_width=True)
        c2.button("Lokasi dan harga saja", key="ks_lh", on_click=atur_kartu,
                  args=([k for k, _ in SEKSI_KARTU if k not in ("lokasi", "harga", "jumlah")],), use_container_width=True)
        c3.button("Hanya lokasi", key="ks_l", on_click=atur_kartu,
                  args=([k for k, _ in SEKSI_KARTU if k != "lokasi"],), use_container_width=True)
        tombol_bersama("kartu", st.session_state.kartu_sembunyi, atur_kartu)
        st.markdown("**Contoh tampilan**")
        if not D["barang"]:
            st.caption("Belum ada barang untuk dijadikan contoh.")
        else:
            def lengkap(b):
                return sum(1 for k in ("kategori", "harga", "catatan", "tautan", "tag", "pemilik", "merek", "dibeli", "dalam") if b.get(k))
            contoh = max(D["barang"], key=lengkap)
            with st.container(key="item_contoh"):
                st.markdown(kartu_barang_html(contoh), unsafe_allow_html=True)
    if st.session_state.pop("kartu_ubah", False):
        js_cookie(",".join(st.session_state.kartu_sembunyi) or "-", 31536000, COOKIE_KARTU)
