"""Halaman Cari barang."""
import html

import streamlit as st

from pelacak.bantu import (
    daftar_lokasi, daftar_pemilik, daftar_tag, judul_grup, kartu_barang_html, kelompok, lencana,
    lokasi_dari, nama_kat, nama_lok, saring_barang, sub_dari, tampil_foto_kecil, tampil_galeri,
    tampil_lampiran,
)
from pelacak.inti import D, fmt_iso
from pelacak.penyimpanan import ambil_foto


# ---------------------------------------------------------------- cari barang
def halaman_cari():
    if not D["barang"]:
        st.info("Belum ada barang. Tambahkan lewat menu Barang > Kelola barang.")
    else:
        with st.container(key="kartu_filter"):
            q = " ".join(st.text_input("Pencarian", icon=":material/search:", key="cari_q",
                                       placeholder="Cari nama, lokasi, kategori, atau catatan...",
                                       label_visibility="collapsed").lower().split())
            c0, c1, c2, c3 = st.columns(4)
            pt = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
            if st.session_state.get("cari_tempat", "semua") not in ["semua"] + list(pt):
                st.session_state.cari_tempat = "semua"
            f_tem = c0.selectbox("Tempat", ["semua"] + list(pt), key="cari_tempat",
                                 format_func=lambda i: "Semua tempat" if i == "semua" else pt[i])
            pl = {l["id"]: (l["nama"] if f_tem != "semua" else nama_lok(l)) for l in daftar_lokasi()
                  if f_tem == "semua" or l.get("tempat") == f_tem}
            if st.session_state.get("cari_lok", "semua") not in ["semua"] + list(pl):
                st.session_state.cari_lok = "semua"
            f_lok = c1.selectbox("Lokasi", ["semua"] + list(pl), key="cari_lok",
                                 format_func=lambda i: "Semua lokasi" if i == "semua" else pl[i])
            psub = {s["id"]: (s["nama"] if f_lok != "semua" else f"{pl[s['lokasi']]} › {s['nama']}")
                    for s in D["sublokasi"] if s["lokasi"] in pl and (f_lok == "semua" or s["lokasi"] == f_lok)}
            if st.session_state.get("cari_sub", "semua") not in ["semua"] + list(psub):
                st.session_state.cari_sub = "semua"
            f_sub = c2.selectbox("Sub lokasi", ["semua"] + list(psub), key="cari_sub",
                                 format_func=lambda i: "Semua sub lokasi" if i == "semua" else psub[i])
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            if st.session_state.get("cari_kat", "semua") not in ["semua"] + list(pk):
                st.session_state.cari_kat = "semua"
            f_kat = c3.selectbox("Kategori", ["semua"] + list(pk), key="cari_kat",
                                 format_func=lambda i: "Semua kategori" if i == "semua" else pk[i])
            f_pem = "semua"
            if daftar_pemilik():
                ops_pem = ["semua", "__tanpa__"] + daftar_pemilik()
                if st.session_state.get("cari_pem", "semua") not in ops_pem:
                    st.session_state.cari_pem = "semua"
                f_pem = st.selectbox("Pemilik", ops_pem, key="cari_pem",
                                     format_func=lambda x: "Semua pemilik" if x == "semua"
                                     else "Tanpa pemilik" if x == "__tanpa__" else x)
            f_tag = []
            if daftar_tag():
                st.session_state.cari_tag = [t for t in st.session_state.get("cari_tag", []) if t in daftar_tag()]
                f_tag = st.multiselect("Label", daftar_tag(), key="cari_tag", placeholder="Semua label")
            tv1, tv2, tv3 = st.columns([2, 2, 2], vertical_alignment="center")
            mode_tampil = tv1.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                                key="tampilan", label_visibility="collapsed") or "Kartu"
            tampil_foto = tv2.toggle("Tampilkan foto", value=True, key="cari_foto")
            f_fav = tv3.toggle("Hanya favorit", key="cari_fav")
        hasil = D["barang"]
        if f_tem != "semua":
            hasil = [b for b in hasil if (lokasi_dari(b) or {}).get("tempat") == f_tem]
        if f_lok != "semua":
            hasil = [b for b in hasil if b.get("lokasi") == f_lok]
        if f_sub != "semua":
            hasil = [b for b in hasil if (sub_dari(b) or {}).get("id") == f_sub]
        if f_kat != "semua":
            hasil = [b for b in hasil if b.get("kategori") == f_kat]
        if f_pem == "__tanpa__":
            hasil = [b for b in hasil if not b.get("pemilik")]
        elif f_pem != "semua":
            hasil = [b for b in hasil if b.get("pemilik") == f_pem]
        if f_fav:
            hasil = [b for b in hasil if b.get("favorit")]
        if f_tag:
            hasil = [b for b in hasil if all(t in b.get("tag", []) for t in f_tag)]
        hasil, n_mirip = saring_barang(hasil, q)
        _l = next((l for l in D["lokasi"] if l["id"] == f_lok), None) if f_lok != "semua" else None
        _s = next((s for s in D["sublokasi"] if s["id"] == f_sub), None) if f_sub != "semua" else None
        _fotos = []
        for _o, _cap in ((_l, nama_lok(_l) if _l else ""), (_s, _s["nama"] if _s else "")):
            _dat = ambil_foto(_o["foto"]) if _o and _o.get("foto") else None
            if _dat:
                _fotos.append((_dat, _cap))
        if _fotos:
            for _kol, (_dat, _cap) in zip(st.columns(len(_fotos)), _fotos):
                _kol.image(_dat, caption=_cap, use_container_width=True)
        st.caption(f"{len(hasil)} dari {len(D['barang'])} barang"
                   + (f" · termasuk {n_mirip} hasil yang mirip dengan ketikanmu" if n_mirip else ""))
        if not hasil:
            st.info("Tidak ada barang yang cocok.")
        elif mode_tampil == "Kartu":
            for judul, anggota in kelompok(hasil):
                judul_grup(judul, len(anggota))
                for b in sorted(anggota, key=lambda x: (not x.get("favorit"), x["nama"].lower())):
                    with st.container(key=f"item_c_{b['id']}"):
                        st.markdown(kartu_barang_html(b, tampil_foto), unsafe_allow_html=True)
                        tampil_galeri(b)
                        tampil_lampiran(b)
        else:
            with st.container(key="kartu_tabel"):
                lebar = [4, 1.2, 2.4, 4, 2]
                judul_kol = ["Barang", "Jumlah", "Kategori", "Catatan", "Diubah"]
                if tampil_foto:
                    lebar, judul_kol = [1.1] + lebar, ["Foto"] + judul_kol
                kep = st.columns(lebar, vertical_alignment="top")
                for kol, judul in zip(kep, judul_kol):
                    kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                for judul, anggota in kelompok(hasil):
                    judul_grup(judul, len(anggota))
                    for b in sorted(anggota, key=lambda x: x["nama"].lower()):
                        k = st.columns(lebar, vertical_alignment="center")
                        o = 0
                        if tampil_foto:
                            tampil_foto_kecil(b, k[0])
                            o = 1
                        k[o].markdown(f'<div class="brg">{html.escape(b["nama"])}{lencana(b)}</div>',
                                      unsafe_allow_html=True)
                        k[o + 1].write(b.get("jumlah", 1))
                        k[o + 2].write(nama_kat(b) if b.get("kategori") else "")
                        k[o + 3].write(b.get("catatan", ""))
                        k[o + 4].write(fmt_iso(b.get("diubah", "")))
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
