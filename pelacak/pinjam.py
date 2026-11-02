"""Pinjam-meminjam."""
import html
import uuid

import streamlit as st

from pelacak.bantu import atur, nama_tempat, pinjam_aktif, selesai_simpan, status_sisa, versi
from pelacak.inti import D, TGL_MAX, TGL_MIN, fmt_iso, hari_ini, sisa_hari


# ------------------------------------------------------------ pinjam-meminjam
def _baris_hapus_pinjam(p):
    """Tampilkan konfirmasi hapus kalau baris ini sedang dikonfirmasi."""
    if st.session_state.get("pj_hapus") == p["id"]:
        st.warning(f"Hapus catatan {p.get('nama', '')}?")
        y, n, _ = st.columns([1, 1, 4])
        if y.button("Ya, hapus", type="primary", key=f"pjya_{p['id']}"):
            D["pinjam"] = [x for x in D["pinjam"] if x["id"] != p["id"]]
            selesai_simpan("Dihapus.", pj_hapus=None)
        n.button("Batal", key=f"pjbatal_{p['id']}", on_click=atur, args=("pj_hapus", None))


def kartu_pinjam_html(p: dict) -> str:
    """Kartu satu peminjaman: huruf awal, nama + lencana arah, orang dan tanggal, tenggat di kanan."""
    tanda = ('<span class="lencana lc-m">Dipinjamkan</span>' if p.get("arah") == "keluar"
             else '<span class="lencana lc-b">Saya pinjam</span>')
    orang = html.escape(p.get("orang", ""))
    kata = "dengan" if p.get("arah") == "keluar" else "dari"
    mt = f'<div class="mt">{kata} {orang} • sejak {fmt_iso(p.get("tanggal", ""))}</div>'
    cat = f'<div class="cat">{html.escape(p["catatan"])}</div>' if p.get("catatan") else ""
    ic = html.escape((p.get("nama", "").strip()[:1] or "?").upper())
    if p.get("tenggat"):
        kanan = (f'<div class="qt"><span>Tenggat</span><span>{fmt_iso(p["tenggat"])}</span>'
                 f'{status_sisa(sisa_hari(p["tenggat"]))}</div>')
    else:
        kanan = '<div class="qt"><span>Tanpa tenggat</span></div>'
    return (f'<div class="itm pj"><div class="ic">{ic}</div><div class="isi"><div class="jd">'
            f'{html.escape(p.get("nama", ""))}{tanda}</div>{mt}{cat}</div>{kanan}</div>')


def halaman_pinjam():
    by_id = {b["id"]: b for b in D["barang"]}
    aktif = [p for p in D["pinjam"] if not p.get("kembali")]
    selesai = [p for p in D["pinjam"] if p.get("kembali")]
    hari = hari_ini()
    with st.container(key="kartu_barang"):
        if st.session_state.get("pj_mode") == "baru":
            st.markdown("#### Catat peminjaman")
            with st.form(f"form_pinjam_{versi()}"):
                arah = st.radio("Jenis", ["Saya pinjamkan ke orang lain", "Saya meminjam dari orang lain"],
                                horizontal=True)
                ids = [""] + [b["id"] for b in sorted(D["barang"], key=lambda x: x["nama"].lower())]
                pilih = st.selectbox("Barang dari daftar (boleh kosong)", ids,
                                     format_func=lambda i: "— tidak dari daftar —" if not i
                                     else f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                manual = st.text_input("Nama barang (kalau tidak dari daftar)")
                c1, c2, c3 = st.columns(3)
                orang = c1.text_input("Nama orang")
                tgl = c2.date_input("Tanggal", value=hari, min_value=TGL_MIN, max_value=TGL_MAX,
                                    format="DD/MM/YYYY")
                tenggat = c3.date_input("Tenggat kembali (boleh kosong)", value=None,
                                        min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                catatan = st.text_input("Catatan (boleh kosong)")
                t1, t2, _ = st.columns([1, 1, 4])
                kirim = t1.form_submit_button("Catat", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.pj_mode = None
                st.rerun()
            if kirim:
                keluar_ = arah.startswith("Saya pinjamkan")
                nama = by_id[pilih]["nama"] if pilih else manual.strip()
                if not nama:
                    st.error("Pilih barang dari daftar atau ketik namanya.")
                elif not orang.strip():
                    st.error("Nama orang wajib diisi.")
                elif tenggat and tenggat < tgl:
                    st.error("Tenggat tidak boleh sebelum tanggal pinjam.")
                elif pilih and keluar_ and pinjam_aktif(pilih):
                    st.error(f"Barang itu masih tercatat dipinjam {pinjam_aktif(pilih).get('orang', '')}.")
                else:
                    D["pinjam"].append({"id": uuid.uuid4().hex[:8], "arah": "keluar" if keluar_ else "masuk",
                                        "barang": pilih, "nama": nama, "orang": orang.strip(),
                                        "tanggal": tgl.isoformat(),
                                        "tenggat": tenggat.isoformat() if tenggat else "",
                                        "catatan": catatan.strip(), "kembali": ""})
                    selesai_simpan("Peminjaman dicatat.", pj_mode=None)
            return

        with st.container(key="baris_cari"):
            kc, kt = st.columns([5, 2], vertical_alignment="center")
            cari = " ".join(kc.text_input("Pencarian", key="pj_cari", icon=":material/search:",
                                          placeholder="Cari barang atau nama orang...",
                                          label_visibility="collapsed").lower().split())
            kt.button("Tambah", type="primary", key="pj_tambah", icon=":material/add:",
                      use_container_width=True, on_click=atur, args=("pj_mode", "baru"))
        mode_tampil = st.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                           key="tampilan", label_visibility="collapsed") or "Kartu"
        urut = sorted(aktif, key=lambda x: (x.get("tenggat") or "9999-12-31", x.get("tanggal", "")))
        if cari:
            urut = [p for p in urut if cari in " ".join([p.get("nama", ""), p.get("orang", ""),
                                                          p.get("catatan", "")]).lower()]
        st.markdown(f"#### Sedang berjalan ({len(aktif)})")
        if not aktif:
            st.caption("Tidak ada peminjaman yang sedang berjalan. Tekan Tambah untuk mencatat.")
        elif not urut:
            st.info("Tidak ada peminjaman yang cocok dengan pencarian.")
        elif mode_tampil == "Kartu":
            for p in urut:
                with st.container(key=f"item_p_{p['id']}"):
                    st.markdown(kartu_pinjam_html(p), unsafe_allow_html=True)
                    e1, e2, _ = st.columns([2, 1, 1])
                    if e1.button("Sudah kembali", key=f"kpakai_pj_{p['id']}", use_container_width=True):
                        p["kembali"] = hari.isoformat()
                        selesai_simpan("Dicatat sudah kembali.")
                    e2.button("Hapus", key=f"khapus_pj_{p['id']}", on_click=atur, args=("pj_hapus", p["id"]),
                              use_container_width=True)
                    _baris_hapus_pinjam(p)
        else:
            lebar = [3.4, 2.2, 1.8, 2.2, 2.8]
            kep = st.columns(lebar, vertical_alignment="top")
            for kol, judul in zip(kep, ["Barang", "Dengan siapa", "Sejak", "Tenggat", "Aksi"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for p in urut:
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                tanda = ('<span class="lencana lc-m">Dipinjamkan</span>' if p.get("arah") == "keluar"
                         else '<span class="lencana lc-b">Saya pinjam</span>')
                k[0].markdown(f'<div class="brg">{html.escape(p.get("nama", ""))}{tanda}</div>',
                              unsafe_allow_html=True)
                k[1].write(p.get("orang", ""))
                k[2].write(fmt_iso(p.get("tanggal", "")))
                k[3].markdown(f'{fmt_iso(p["tenggat"])}<br>{status_sisa(sisa_hari(p["tenggat"]))}'
                              if p.get("tenggat") else "—", unsafe_allow_html=True)
                a1, a2 = k[4].columns([3, 1])
                if a1.button("Sudah kembali", key=f"pjkembali_{p['id']}"):
                    p["kembali"] = hari.isoformat()
                    selesai_simpan("Dicatat sudah kembali.")
                a2.button("🗑️", key=f"pjhapus_{p['id']}", help="Hapus catatan", on_click=atur,
                          args=("pj_hapus", p["id"]))
                _baris_hapus_pinjam(p)
        with st.expander(f"Sudah kembali ({len(selesai)})"):
            if not selesai:
                st.caption("Belum ada.")
            for p in sorted(selesai, key=lambda x: x.get("kembali", ""), reverse=True):
                k = st.columns([3.4, 2.2, 2.2, 2.2, 1], vertical_alignment="center")
                k[0].write(p.get("nama", ""))
                k[1].write(p.get("orang", ""))
                k[2].write(f"{fmt_iso(p.get('tanggal', ''))} → {fmt_iso(p.get('kembali', ''))}")
                k[3].write("Dipinjamkan" if p.get("arah") == "keluar" else "Saya pinjam")
                k[4].button("🗑️", key=f"pjhapus2_{p['id']}", help="Hapus catatan", on_click=atur,
                            args=("pj_hapus", p["id"]))
                _baris_hapus_pinjam(p)
