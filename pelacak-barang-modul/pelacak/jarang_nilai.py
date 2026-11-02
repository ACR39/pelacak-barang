"""Barang jarang dipakai dan nilai barang."""
import html

import pandas as pd
import streamlit as st

from pelacak.bantu import (
    harga_b, jumlah_b, lencana, nama_kat, nama_lokasi, nama_tempat, selesai_simpan, status_sisa,
)
from pelacak.inti import D, fmt_iso, hari_ini, iso_ke_date, rp, sisa_hari


# -------------------------------------------------------------- jarang dipakai
def halaman_jarang():
    if not D["barang"]:
        st.info("Belum ada barang.")
        return
    with st.container(key="kartu_barang"):
        batas = st.selectbox("Tampilkan barang yang tidak dipakai selama", [30, 60, 90, 180, 365], index=2,
                             key="jr_batas", format_func=lambda n: f"{n} hari atau lebih")
        hasil = []
        for b in D["barang"]:
            ref = iso_ke_date(b.get("dipakai")) or iso_ke_date(b.get("diubah"))
            if ref and (hari_ini() - ref).days >= batas:
                hasil.append(((hari_ini() - ref).days, b))
        st.caption("Tanggal dipakai dicatat lewat tombol Dipakai di Kelola barang. Barang yang belum pernah "
                   "dicatat dihitung sejak terakhir diubah.")
        if not hasil:
            st.info("Tidak ada barang yang cocok. Semua barang masih sering dipakai.")
            return
        lebar = [3.6, 3.4, 2.4, 1.6, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Disimpan di", "Terakhir dipakai", "Lama", "Aksi"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for hari, b in sorted(hasil, key=lambda x: -x[0]):
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}{lencana(b)}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(fmt_iso(b["dipakai"]) if b.get("dipakai") else "Belum tercatat")
            k[3].write(f"{hari} hari")
            if k[4].button("Dipakai hari ini", key=f"jr_{b['id']}"):
                b["dipakai"] = hari_ini().isoformat()
                selesai_simpan("Dicatat dipakai hari ini.")


def _tabel_tanggal(kunci: str, judul_tgl: str):
    ada = [(sisa_hari(b.get(kunci)), b) for b in D["barang"] if sisa_hari(b.get(kunci)) is not None]
    with st.container(key=f"kartu_tgl_{kunci}"):
        if not ada:
            st.info(f"Belum ada barang yang diisi tanggal {judul_tgl.lower()}. Isi lewat Kelola barang.")
            return
        f = st.selectbox("Tampilkan", ["Semua", "Sudah lewat", "Dalam 30 hari", "Dalam 90 hari"],
                         key=f"tg_{kunci}")
        if f == "Sudah lewat":
            ada = [x for x in ada if x[0] < 0]
        elif f == "Dalam 30 hari":
            ada = [x for x in ada if 0 <= x[0] <= 30]
        elif f == "Dalam 90 hari":
            ada = [x for x in ada if 0 <= x[0] <= 90]
        if not ada:
            st.caption("Tidak ada yang cocok.")
            return
        lebar = [4, 4, 2.2, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Tempat", judul_tgl, "Status"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for s, b in sorted(ada, key=lambda x: x[0]):
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(fmt_iso(b[kunci]))
            k[3].markdown(status_sisa(s), unsafe_allow_html=True)


def halaman_tanggal():
    t1, t2 = st.tabs(["Kedaluwarsa", "Garansi"])
    with t1:
        _tabel_tanggal("kedaluwarsa", "Kedaluwarsa")
    with t2:
        _tabel_tanggal("garansi", "Garansi sampai")


# ---------------------------------------------------------------- nilai barang
def halaman_nilai():
    ber = [b for b in D["barang"] if harga_b(b)]
    if not ber:
        st.info("Belum ada harga yang diisi. Isi \"Harga beli per buah\" di Kelola barang.")
        return

    def nilai(b):
        return harga_b(b) * max(jumlah_b(b), 0)

    total = sum(nilai(b) for b in ber)
    kosong = len(D["barang"]) - len(ber)
    st.markdown(
        '<div class="statcard"><div class="sc-kiri"><span class="tag">Total nilai</span>'
        f'<div class="sc-judul">{rp(total)}</div>'
        f'<div class="sc-ket">dari {len(ber)} jenis barang yang sudah diisi harganya</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Rata-rata per jenis</div><div class="sc-val">{rp(total / len(ber))}</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Belum diisi harga</div><div class="sc-val m">{kosong}</div></div>'
        '</div>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1.container(key="kartu_g1"):
        st.markdown("**Nilai per lokasi (Rp)**")
        per = {}
        for b in ber:
            per[nama_lokasi(b)] = per.get(nama_lokasi(b), 0) + nilai(b)
        st.bar_chart(pd.DataFrame({"Lokasi": list(per), "Nilai": list(per.values())}),
                     x="Lokasi", y="Nilai", horizontal=True, sort="-Nilai", color="#2b7a57", height=300)
    with g2.container(key="kartu_g2"):
        st.markdown("**Nilai per kategori (Rp)**")
        per = {}
        for b in ber:
            per[nama_kat(b)] = per.get(nama_kat(b), 0) + nilai(b)
        st.bar_chart(pd.DataFrame({"Kategori": list(per), "Nilai": list(per.values())}),
                     x="Kategori", y="Nilai", horizontal=True, sort="-Nilai", color="#2f5d9e", height=300)
    with st.container(key="kartu_tabel"):
        st.markdown("**20 barang bernilai tertinggi**")
        lebar = [4, 3.4, 2.2, 1.2, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Tempat", "Harga satuan", "Jml", "Nilai"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for b in sorted(ber, key=nilai, reverse=True)[:20]:
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(rp(harga_b(b)))
            k[3].write(jumlah_b(b))
            k[4].write(rp(nilai(b)))
