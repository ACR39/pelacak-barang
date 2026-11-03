"""Foto sebelum dan sesudah merapikan lokasi."""
import uuid

import streamlit as st

from pelacak.bantu import atur, daftar_lokasi, nama_lok, selesai_simpan, tombol_tambah, tutup_tambah, versi
from pelacak.inti import D, TGL_MAX, TGL_MIN, fmt_iso, hari_ini
from pelacak.penyimpanan import ambil_foto, hapus_foto, simpan_foto

MAKS_RAPI = 30
TIPE_FOTO = ["jpg", "jpeg", "png", "webp"]


def _pasangan(x: dict):
    """Foto sebelum dan sesudah berdampingan."""
    c1, c2 = st.columns(2)
    for kol, judul, kunci in ((c1, "Sebelum", "sebelum"), (c2, "Sesudah", "sesudah")):
        kol.caption(judul)
        dat = ambil_foto(x[kunci]) if x.get(kunci) else None
        if dat:
            kol.image(dat, use_container_width=True)
        else:
            kol.markdown('<div class="dpt kosong"><div class="dk">Belum ada foto</div></div>', unsafe_allow_html=True)


def _simpan_semua(unggahan: list) -> tuple:
    """Simpan beberapa foto. Kalau ada yang gagal, yang sudah terunggah dihapus lagi. Kembalikan (daftar path, galat)."""
    hasil = []
    for f in unggahan:
        if f is None:
            hasil.append("")
            continue
        try:
            hasil.append(simpan_foto("rapi", f.getvalue()))
        except Exception as e:
            for p in hasil:
                hapus_foto(p)
            return [], f"Foto gagal diunggah: {e}"
    return hasil, ""


def tampil_rapi():
    """Riwayat foto sebelum dan sesudah merapikan, per lokasi."""
    lok = sorted(daftar_lokasi(), key=lambda l: nama_lok(l).lower())
    if not lok:
        st.info("Belum ada lokasi. Buat dulu di Pengaturan > Tempat dan lokasi.")
        return
    peta = {l["id"]: l for l in lok}
    if st.session_state.get("rp_lok") not in peta:
        st.session_state.rp_lok = lok[0]["id"]
    pid = st.selectbox("Lokasi", list(peta), key="rp_lok", format_func=lambda i: nama_lok(peta[i]))
    milik = sorted([x for x in D.get("rapi", []) if x.get("lokasi") == pid], key=lambda x: x.get("tgl", ""), reverse=True)
    st.caption("Foto lemari atau kotak sebelum dan sesudah dibereskan, lengkap dengan tanggalnya. "
               f"Maksimal {MAKS_RAPI} catatan per lokasi.")
    if tombol_tambah("rapi", "Catat merapikan") and len(milik) >= MAKS_RAPI:
        st.warning(f"Sudah {MAKS_RAPI} catatan di lokasi ini. Hapus yang lama dulu.")
        if st.button("Tutup", key="rp_tutup"):
            tutup_tambah("rapi")
    elif st.session_state.get("tb_rapi"):
        with st.form(f"form_rapi_{versi()}", clear_on_submit=True):
            tgl = st.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            f_sebelum = st.file_uploader("Foto sebelum", type=TIPE_FOTO, key=f"rp_s_{versi()}")
            f_sesudah = st.file_uploader("Foto sesudah (boleh menyusul nanti)", type=TIPE_FOTO, key=f"rp_t_{versi()}")
            catatan = st.text_input("Catatan (boleh kosong)", max_chars=120, placeholder="Contoh: pisahkan kabel dan charger")
            s1, s2 = st.columns(2)
            simpan = s1.form_submit_button("Simpan", type="primary", icon=":material/check:", use_container_width=True)
            batal = s2.form_submit_button("Batal", use_container_width=True)
        if batal:
            tutup_tambah("rapi")
        if simpan:
            if f_sebelum is None and f_sesudah is None:
                st.error("Pilih minimal satu foto.")
            else:
                path, galat = _simpan_semua([f_sebelum, f_sesudah])
                if galat:
                    st.error(galat)
                else:
                    D.setdefault("rapi", []).append({"id": uuid.uuid4().hex[:8], "lokasi": pid, "tgl": tgl.isoformat(),
                                                     "sebelum": path[0], "sesudah": path[1], "catatan": catatan.strip()})
                    selesai_simpan("Catatan merapikan disimpan.", tb_rapi=False)
    if not milik:
        st.caption("Belum ada catatan untuk lokasi ini.")
    for x in milik:
        with st.container(key=f"item_rp_{x['id']}"):
            st.markdown(f"**{fmt_iso(x.get('tgl', ''))}**" + (f" · {x['catatan']}" if x.get("catatan") else ""))
            _pasangan(x)
            if not x.get("sesudah") or not x.get("sebelum"):
                kurang = "sesudah" if not x.get("sesudah") else "sebelum"
                f = st.file_uploader(f"Tambah foto {kurang}", type=TIPE_FOTO, key=f"rp_u_{x['id']}_{versi()}")
                if f is not None and st.button(f"Simpan foto {kurang}", key=f"kpakai_rpf_{x['id']}"):
                    path, galat = _simpan_semua([f])
                    if galat:
                        st.error(galat)
                    else:
                        x[kurang] = path[0]
                        selesai_simpan("Foto ditambahkan.")
            if st.session_state.get("rp_hapus") == x["id"]:
                st.warning("Hapus catatan dan fotonya?")
                y, n, _ = st.columns([1.2, 1, 2])
                if y.button("Ya, hapus", type="primary", key=f"rpya_{x['id']}"):
                    fs = [p for p in (x.get("sebelum"), x.get("sesudah")) if p]
                    D["rapi"] = [r for r in D["rapi"] if r["id"] != x["id"]]
                    selesai_simpan("Dihapus.", sesudah=lambda fs=fs: [hapus_foto(p) for p in fs], rp_hapus=None)
                n.button("Batal", key=f"rpbt_{x['id']}", on_click=atur, args=("rp_hapus", None))
            else:
                st.button("Hapus", key=f"khapus_rp_{x['id']}", on_click=atur, args=("rp_hapus", x["id"]))
