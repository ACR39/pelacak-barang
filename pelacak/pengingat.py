"""Pengingat berkala (cek rutin)."""
import html

import streamlit as st

from pelacak.bantu import jadwal_ganti, nama_tempat, selesai_simpan, status_sisa, umur_teks, versi
from pelacak.beranda import CEK_OPSI, jadwal_cek
from pelacak.inti import D, GANTI_OPSI, fmt_iso, hari_ini, teks_cek, teks_ganti


# ------------------------------------------------------------ pengingat berkala
def halaman_pengingat():
    t1, t2 = st.tabs(["Jadwal", "Atur pengingat"])
    with t1:
        with st.container(key="kartu_tgl_cek"):
            jd = jadwal_cek()
            if not jd:
                st.info('Belum ada barang yang diberi pengingat. Buka tab "Atur pengingat".')
            else:
                f = st.selectbox("Tampilkan", ["Semua", "Sudah waktunya (7 hari ke depan)"], key="pb_f")
                if f != "Semua":
                    jd = [x for x in jd if x[0] <= 7]
                if not jd:
                    st.caption("Tidak ada barang yang perlu dicek dalam 7 hari ke depan.")
                else:
                    lebar = [3.4, 3.2, 2.2, 2.6, 2.2]
                    kep = st.columns(lebar, vertical_alignment="top")
                    for kol, judul in zip(kep, ["Barang", "Disimpan di", "Terakhir dicek", "Berikutnya", "Aksi"]):
                        kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                    for s, b in jd:
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                        k = st.columns(lebar, vertical_alignment="center")
                        k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                        k[1].write(nama_tempat(b))
                        k[2].write(fmt_iso(b["cek_terakhir"]) if b.get("cek_terakhir") else "Belum pernah")
                        k[3].markdown(f'{status_sisa(s)}<div class="sub">{teks_cek(b["cek_tiap"])}</div>',
                                      unsafe_allow_html=True)
                        if k[4].button("Sudah dicek", key=f"pb_{b['id']}"):
                            b["cek_terakhir"] = hari_ini().isoformat()
                            selesai_simpan(f"{b['nama']} dicatat sudah dicek.")
    with t2:
        with st.container(key="kartu_barang"):
            if not D["barang"]:
                st.info("Belum ada barang.")
                return
            st.caption("Cocok untuk barang yang perlu dicek rutin: baterai cadangan, alat P3K, tabung pemadam, "
                       "filter air, atau obat yang mendekati kedaluwarsa.")
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            with st.form(f"form_pb_{versi()}"):
                pil = st.multiselect("Barang", [b["id"] for b in urut],
                                     format_func=lambda i: next(x["nama"] for x in urut if x["id"] == i))
                n = st.selectbox("Seberapa sering dicek", CEK_OPSI[1:], index=2, format_func=teks_cek)
                ok = st.form_submit_button("Pasang pengingat", type="primary")
            if ok:
                if not pil:
                    st.error("Pilih minimal satu barang.")
                else:
                    peta = {b["id"]: b for b in D["barang"]}
                    for i in pil:
                        peta[i]["cek_tiap"] = int(n)
                        if not peta[i].get("cek_terakhir"):
                            peta[i]["cek_terakhir"] = hari_ini().isoformat()
                    selesai_simpan(f"Pengingat dipasang untuk {len(pil)} barang.")
            ada = [b for _, b in jadwal_cek()]
            if ada:
                st.markdown("**Hentikan pengingat**")
                with st.form(f"form_pb_stop_{versi()}"):
                    stop = st.multiselect("Barang", [b["id"] for b in ada], key="pb_stop",
                                          format_func=lambda i: next(x["nama"] for x in ada if x["id"] == i))
                    oks = st.form_submit_button("Hentikan")
                if oks and stop:
                    for b in ada:
                        if b["id"] in stop:
                            b.pop("cek_tiap", None)
                            b.pop("cek_terakhir", None)
                    selesai_simpan("Pengingat dihentikan.")


# ------------------------------------------------------------ pengingat ganti
def halaman_ganti():
    t1, t2 = st.tabs(["Jadwal", "Atur pengingat"])
    with t1:
        with st.container(key="kartu_tgl_ganti"):
            jd = jadwal_ganti()
            if not jd:
                st.info('Belum ada barang yang diberi pengingat ganti. Buka tab "Atur pengingat" '
                        'atau isi "Pengingat ganti" di Kelola barang.')
            else:
                f = st.selectbox("Tampilkan", ["Semua", "Sudah waktunya (30 hari ke depan)"], key="gt_f")
                if f != "Semua":
                    jd = [x for x in jd if x[0] <= 30]
                if not jd:
                    st.caption("Tidak ada barang yang perlu diganti dalam 30 hari ke depan.")
                else:
                    lebar = [3.2, 2.2, 1.8, 2.4, 2.6, 2.2]
                    kep = st.columns(lebar, vertical_alignment="top")
                    for kol, judul in zip(kep, ["Barang", "Disimpan di", "Umur", "Terakhir diganti", "Berikutnya", "Aksi"]):
                        kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                    for s, b in jd:
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                        k = st.columns(lebar, vertical_alignment="center")
                        k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                        k[1].write(nama_tempat(b))
                        k[2].write(umur_teks(b) or "—")
                        k[3].write(fmt_iso(b["diganti"]) if b.get("diganti")
                                   else ("Belum pernah" + (f" (dibeli {fmt_iso(b['dibeli'])})" if b.get("dibeli") else "")))
                        k[4].markdown(f'{status_sisa(s)}<div class="sub">{teks_ganti(b["ganti_tiap"])}</div>',
                                      unsafe_allow_html=True)
                        if k[5].button("Sudah diganti", key=f"gt_{b['id']}"):
                            b["diganti"] = hari_ini().isoformat()
                            selesai_simpan(f"{b['nama']} dicatat sudah diganti.")
    with t2:
        with st.container(key="kartu_barang_ganti"):
            if not D["barang"]:
                st.info("Belum ada barang.")
                return
            st.caption("Cocok untuk barang yang lazim diganti berkala: sikat gigi, filter air, baterai, "
                       "sarung bantal, atau pisau cukur. Hitungannya dari tanggal terakhir diganti, "
                       "atau tanggal beli kalau belum pernah diganti.")
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            with st.form(f"form_gt_{versi()}"):
                pil = st.multiselect("Barang", [b["id"] for b in urut],
                                     format_func=lambda i: next(x["nama"] for x in urut if x["id"] == i))
                n = st.selectbox("Seberapa sering diganti", GANTI_OPSI[1:], index=2, format_func=teks_ganti)
                ok = st.form_submit_button("Pasang pengingat ganti", type="primary")
            if ok:
                if not pil:
                    st.error("Pilih minimal satu barang.")
                else:
                    peta = {b["id"]: b for b in D["barang"]}
                    for i in pil:
                        peta[i]["ganti_tiap"] = int(n)
                    selesai_simpan(f"Pengingat ganti dipasang untuk {len(pil)} barang.")
            ada = [b for _, b in jadwal_ganti()]
            if ada:
                st.markdown("**Hentikan pengingat ganti**")
                with st.form(f"form_gt_stop_{versi()}"):
                    stop = st.multiselect("Barang", [b["id"] for b in ada], key="gt_stop",
                                          format_func=lambda i: next(x["nama"] for x in ada if x["id"] == i))
                    oks = st.form_submit_button("Hentikan")
                if oks and stop:
                    for b in ada:
                        if b["id"] in stop:
                            b.pop("ganti_tiap", None)
                    selesai_simpan("Pengingat ganti dihentikan.")
