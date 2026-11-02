"""Data master: label QR, tempat, lokasi, sub lokasi, kategori, pemilik, label, dan cadangan data."""
import hashlib
import html
import io
import json
import uuid

import streamlit as st

from pelacak.bantu import (
    ada_kembar, atur, daftar_lokasi, daftar_pemilik, daftar_tag, html_nama_foto, idx, isi_dari,
    nama_lok, nama_lokasi, perbarui_terdaftar, selesai_simpan, tempat_dari_lok, tombol_tambah,
    tutup_tambah,
)
from pelacak.inti import D, data_kosong, konversi_lama, segno
from pelacak.penyimpanan import hapus_foto, simpan_foto


# --------------------------------------------------------------------- label QR
LABEL_CSS = """
body{font-family:Arial,Helvetica,sans-serif;margin:16px}
.qrg{display:flex;flex-wrap:wrap;gap:10px}
.qrl{border:1px dashed #94a3b8;border-radius:6px;padding:8px;width:__CM__cm;text-align:center;break-inside:avoid}
.qrl img{width:100%;image-rendering:pixelated}
.qrt{font-weight:700;font-size:12pt;margin-top:4px}
.qrs{font-size:9pt;color:#555}
@media print{body{margin:0}.qrl{border:1px dashed #bbb}}
"""


def _target_label(semua_barang: bool = False):
    hasil = []
    for t in sorted(D["tempat"], key=lambda t: t["nama"].lower()):
        hasil.append({"kode": t["id"], "judul": t["nama"], "sub": "", "q": f"tempat={t['id']}"})
    for l in daftar_lokasi():
        tem = tempat_dari_lok(l)
        hasil.append({"kode": l["id"], "judul": l["nama"], "sub": tem["nama"] if tem else "",
                      "q": f"lokasi={l['id']}"})
        for s in D["sublokasi"]:
            if s["lokasi"] == l["id"]:
                hasil.append({"kode": s["id"], "judul": s["nama"], "sub": nama_lok(l),
                              "q": f"lokasi={l['id']}&sub={s['id']}"})
    for b in sorted(D["barang"], key=lambda x: x["nama"].lower()):
        if semua_barang or isi_dari(b["id"]):
            hasil.append({"kode": b["id"], "judul": b["nama"], "sub": "Barang · " + nama_lokasi(b), "q": f"barang={b['id']}"})
    return hasil


def halaman_label():
    if segno is None:
        st.error("Pustaka label QR (segno) belum terpasang. Tambahkan `segno` ke requirements.txt.")
        return
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di menu Lokasi, lalu cetak labelnya di sini.")
        return
    try:
        app_url = str(st.secrets.get("app_url", ""))
    except Exception:
        app_url = ""
    st.session_state.setdefault("qr_url", app_url)
    targets = _target_label(bool(st.session_state.get("qr_semua_b")))
    semua = [t["kode"] for t in targets]
    peta = {t["kode"]: t for t in targets}
    if "qr_pilih" not in st.session_state:
        st.session_state.qr_pilih = list(semua)
    else:
        st.session_state.qr_pilih = [i for i in st.session_state.qr_pilih if i in peta]
    with st.container(key="kartu_barang"):
        url = st.text_input("Alamat aplikasi", key="qr_url", placeholder="https://namaapp.streamlit.app",
                            help="Alamat aplikasi ini di internet. Dipasang di dalam kode QR.").strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        st.checkbox("Sertakan juga barang yang tidak berisi barang lain", key="qr_semua_b",
                    help="Secara bawaan hanya barang yang berisi barang lain (misalnya Tas P3K) yang dibuatkan label.")
        pilih = st.multiselect("Label yang dicetak", semua, key="qr_pilih",
                               format_func=lambda i: peta[i]["judul"] if not peta[i]["sub"]
                               else f'{peta[i]["sub"]} › {peta[i]["judul"]}')
        ukuran = st.selectbox("Ukuran label", ["Kecil (3 cm)", "Sedang (4,5 cm)", "Besar (6 cm)"], index=1)
        cm = {"Kecil (3 cm)": 3, "Sedang (4,5 cm)": 4.5, "Besar (6 cm)": 6}[ukuran]
        if not url:
            st.info("Isi alamat aplikasi dulu supaya kode QR bisa membuka aplikasi saat dipindai. "
                    "Alamat itu muncul di bilah alamat peramban setelah aplikasi berhasil di-deploy. "
                    "Biar tidak perlu mengetik lagi, simpan di Secrets: app_url = \"https://...\".")
            return
        if not pilih:
            st.caption("Pilih minimal satu label.")
            return
        sel, kartu = [], []
        for kode in pilih:
            t = peta[kode]
            qr = segno.make(f"{url}/?{t['q']}", error="m")
            buf = io.BytesIO()
            qr.save(buf, kind="png", scale=8, border=2)
            kartu.append((buf.getvalue(), t["judul"] if not t["sub"] else f'{t["sub"]} › {t["judul"]}'))
            sel.append(f'<div class="qrl"><img src="{qr.png_data_uri(scale=8, border=2)}" alt="QR">'
                       f'<div class="qrt">{html.escape(t["judul"])}</div>'
                       + (f'<div class="qrs">{html.escape(t["sub"])}</div>' if t["sub"] else "") + "</div>")
        dokumen = ('<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Label QR</title><style>'
                   + LABEL_CSS.replace("__CM__", str(cm)) + '</style></head><body><div class="qrg">'
                   + "".join(sel) + "</div></body></html>")
        st.download_button("Unduh lembar label (HTML)", dokumen, file_name="label-qr.html", mime="text/html",
                           type="primary", help="Buka file ini di peramban, lalu tekan Ctrl+P untuk mencetak.")
        st.caption("Buka file hasil unduhan di peramban, lalu cetak (Ctrl+P). Gunakan kertas stiker kalau mau "
                   "langsung ditempel.")
        for i in range(0, len(kartu), 4):
            kol = st.columns(4)
            for j, (png, teks) in enumerate(kartu[i:i + 4]):
                kol[j].image(png, caption=teks, width=150)


# ---------------------------------------------------------------- master data
def kepala_daftar(judul: str, n: int, hint: str):
    st.markdown(f'<div class="dh"><span class="dt">{html.escape(judul)}</span><span class="dn">{n}</span></div>'
                f'<div class="dd">{html.escape(hint)}</div>', unsafe_allow_html=True)


def daftar_sederhana(judul: str, kunci: str, hint: str):
    """Daftar nama dengan tombol Ubah nama dan Hapus per baris, dan kolom tambah di bawah."""
    k_edit, k_hapus = f"edit_{kunci}", f"hapus_{kunci}"
    with st.container(key=f"kartu_g_daftar_{kunci}"):
        kepala_daftar(judul, len(D[kunci]), hint)
        if not D[kunci]:
            st.caption("Belum ada. Tambahkan lewat kolom di bawah.")
        for x in D[kunci]:
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get(k_edit) == x["id"]:
                baru = c1.text_input("Nama", value=x["nama"], key=f"nm_{kunci}_{x['id']}",
                                     label_visibility="collapsed")
                c3.button("Batal", key=f"bt_{kunci}_{x['id']}", on_click=atur, args=(k_edit, None))
                if c2.button("Simpan", key=f"sv_{kunci}_{x['id']}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif ada_kembar([y["nama"] for y in D[kunci] if y["id"] != x["id"]] + [baru]):
                        st.error("Nama itu sudah ada.")
                    else:
                        x["nama"] = baru
                        selesai_simpan("Nama diubah.", **{k_edit: None})
            elif st.session_state.get(k_hapus) == x["id"]:
                if kunci == "tempat":
                    n_pakai = sum(1 for l in D["lokasi"] if l.get("tempat") == x["id"])
                    akibat = "lokasi jadi tanpa tempat"
                else:
                    n_pakai = sum(1 for b in D["barang"] if b.get(kunci) == x["id"])
                    akibat = f"barang jadi tanpa {judul.lower()}"
                c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_pakai} {akibat})" if n_pakai else ""))
                c3.button("Batal", key=f"bh_{kunci}_{x['id']}", on_click=atur, args=(k_hapus, None))
                if c2.button("Ya, hapus", key=f"yh_{kunci}_{x['id']}", type="primary"):
                    D[kunci] = [y for y in D[kunci] if y["id"] != x["id"]]
                    if kunci == "tempat":     # lokasi di dalamnya tetap ada, hanya lepas dari tempat
                        for l in D["lokasi"]:
                            if l.get("tempat") == x["id"]:
                                l.pop("tempat", None)
                    if kunci == "lokasi":     # sub lokasi di bawahnya ikut hilang
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["lokasi"] != x["id"]]
                    selesai_simpan("Dihapus.", **{k_hapus: None})
            else:
                c1.write(x["nama"])
                c2.button("Ubah", key=f"ub_{kunci}_{x['id']}", icon=":material/edit:", on_click=atur, args=(k_edit, x["id"]))
                c3.button("Hapus", key=f"hp_{kunci}_{x['id']}", icon=":material/delete:", on_click=atur, args=(k_hapus, x["id"]))
        if tombol_tambah(kunci, f"Tambah {judul.lower()}"):
            with st.form(f"tambah_{kunci}", clear_on_submit=True):
                nama = st.text_input(f"Nama {judul.lower()} baru", placeholder="Nama baru")
                s1, s2 = st.columns(2)
                simpan = s1.form_submit_button("Simpan", type="primary", icon=":material/check:", use_container_width=True)
                batal = s2.form_submit_button("Batal", use_container_width=True)
            if batal:
                tutup_tambah(kunci)
            if simpan:
                nama = nama.strip()
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar([y["nama"] for y in D[kunci]] + [nama]):
                    st.error("Nama itu sudah ada.")
                else:
                    D[kunci].append({"id": uuid.uuid4().hex[:8], "nama": nama})
                    selesai_simpan("Ditambahkan.", **{f"tb_{kunci}": False})


def halaman_sublokasi():
    """Sub lokasi selalu berada di bawah satu lokasi."""
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di menu Lokasi, lalu tambahkan sub lokasinya di sini.")
        return
    peta = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    with st.container(key="kartu_g_daftar_sub"):
        kepala_daftar("Sub lokasi", len(D["sublokasi"]), "Sub lokasi berada di bawah satu lokasi (misalnya Laci 2 di Lemari kamar). "
                      "Menghapus sub lokasi tidak menghapus barangnya.")
        for l in daftar_lokasi():
            milik = [x for x in D["sublokasi"] if x["lokasi"] == l["id"]]
            st.markdown(f'<div class="dgrup">{html.escape(nama_lok(l))}<span>{len(milik)} sub lokasi</span></div>',
                        unsafe_allow_html=True)
            if not milik:
                st.caption("Belum ada sub lokasi.")
            for x in milik:
                foto_up, hapus_f = None, False
                if st.session_state.get("edit_sub") == x["id"]:
                    foto_up = st.file_uploader(f"Foto {x['nama']} (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                               key=f"fu_sub_{x['id']}")
                    if x.get("foto"):
                        hapus_f = st.checkbox("Hapus foto yang sekarang", key=f"fh_sub_{x['id']}")
                c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
                if st.session_state.get("edit_sub") == x["id"]:
                    baru = c1.text_input("Nama", value=x["nama"], key=f"nm_sub_{x['id']}",
                                         label_visibility="collapsed")
                    c3.button("Batal", key=f"bt_sub_{x['id']}", on_click=atur, args=("edit_sub", None))
                    if c2.button("Simpan", key=f"sv_sub_{x['id']}", type="primary"):
                        baru = baru.strip()
                        if not baru:
                            st.error("Nama tidak boleh kosong.")
                        elif ada_kembar([y["nama"] for y in milik if y["id"] != x["id"]] + [baru]):
                            st.error("Nama itu sudah ada di lokasi ini.")
                        else:
                            galat, foto_lama = "", x.get("foto", "")
                            if foto_up is not None:
                                try:
                                    x["foto"] = simpan_foto(x["id"], foto_up.getvalue())
                                except Exception as e:
                                    galat = f"Foto gagal diunggah: {e}"
                            elif hapus_f:
                                x.pop("foto", None)
                            if galat:
                                st.error(galat)
                            else:
                                x["nama"] = baru
                                ganti = foto_lama if x.get("foto", "") != foto_lama else ""
                                selesai_simpan("Sub lokasi diubah.",
                                               sesudah=(lambda p=ganti: hapus_foto(p)) if ganti else None,
                                               edit_sub=None)
                elif st.session_state.get("hapus_sub") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("sublokasi") == x["id"])
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_b} barang jadi tanpa sub lokasi)" if n_b else ""))
                    c3.button("Batal", key=f"bh_sub_{x['id']}", on_click=atur, args=("hapus_sub", None))
                    if c2.button("Ya, hapus", key=f"yh_sub_{x['id']}", type="primary"):
                        foto_sub = x.get("foto", "")
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["id"] != x["id"]]
                        for b in D["barang"]:
                            if b.get("sublokasi") == x["id"]:
                                b.pop("sublokasi", None)
                        selesai_simpan("Dihapus.", sesudah=(lambda p=foto_sub: hapus_foto(p)) if foto_sub else None,
                                       hapus_sub=None)
                else:
                    c1.markdown(html_nama_foto(x), unsafe_allow_html=True)
                    c2.button("Ubah", key=f"ub_sub_{x['id']}", icon=":material/edit:", on_click=atur, args=("edit_sub", x["id"]))
                    c3.button("Hapus", key=f"hp_sub_{x['id']}", icon=":material/delete:", on_click=atur, args=("hapus_sub", x["id"]))
        if tombol_tambah("sub", "Tambah sub lokasi"):
            with st.form("tambah_sub", clear_on_submit=True):
                f1, f2 = st.columns([2, 3])
                induk = f1.selectbox("Di bawah lokasi", list(peta), format_func=lambda i: peta[i])
                nama = f2.text_input("Nama sub lokasi", placeholder="Nama baru")
                s1, s2 = st.columns(2)
                simpan = s1.form_submit_button("Simpan", type="primary", icon=":material/check:", use_container_width=True)
                batal = s2.form_submit_button("Batal", use_container_width=True)
            if batal:
                tutup_tambah("sub")
            if simpan:
                nama = nama.strip()
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar([y["nama"] for y in D["sublokasi"] if y["lokasi"] == induk] + [nama]):
                    st.error("Nama itu sudah ada di lokasi ini.")
                else:
                    D["sublokasi"].append({"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": induk})
                    selesai_simpan("Ditambahkan.", tb_sub=False)


def halaman_lokasi():
    """Lokasi (lemari, rak, kotak) berada di dalam satu tempat (rumah, kantor)."""
    pt = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
    ops = [""] + list(pt)

    def fmt(i):
        return "Tanpa tempat" if not i else pt[i]

    if not pt:
        st.info("Isi dulu nama tempat (misalnya Rumah A, Rumah B, Kantor) di menu Tempat. "
                "Lokasi tanpa tempat tetap bisa dipakai.")
    with st.container(key="kartu_g_daftar_lok"):
        kepala_daftar("Lokasi", len(D["lokasi"]), "Lokasi adalah lemari, rak, atau kotak di dalam satu tempat (misalnya Lemari kamar di Rumah A). "
                      "Menghapus lokasi ikut menghapus sub lokasinya. Barangnya tidak terhapus.")
        urut = sorted(D["lokasi"], key=lambda l: l["nama"].lower())
        for tid, tnama in list(pt.items()) + [("", "Belum diatur tempatnya")]:
            milik = [x for x in urut if (x.get("tempat") == tid if tid else x.get("tempat") not in pt)]
            if not tid and not milik:
                continue
            st.markdown(f'<div class="dgrup">{html.escape(tnama)}<span>{len(milik)} lokasi</span></div>',
                        unsafe_allow_html=True)
            if not milik:
                st.caption("Belum ada lokasi.")
            for x in milik:
                foto_up, hapus_f = None, False
                if st.session_state.get("edit_lokasi") == x["id"]:
                    foto_up = st.file_uploader(f"Foto {x['nama']} (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                               key=f"fu_lok_{x['id']}")
                    if x.get("foto"):
                        hapus_f = st.checkbox("Hapus foto yang sekarang", key=f"fh_lok_{x['id']}")
                c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
                if st.session_state.get("edit_lokasi") == x["id"]:
                    e1, e2 = c1.columns([3, 2])
                    baru = e1.text_input("Nama", value=x["nama"], key=f"nm_lok_{x['id']}",
                                         label_visibility="collapsed")
                    awal = x.get("tempat") if x.get("tempat") in pt else ""
                    tbaru = e2.selectbox("Tempat", ops, index=idx(ops, awal), key=f"tm_lok_{x['id']}",
                                         format_func=fmt, label_visibility="collapsed")
                    c3.button("Batal", key=f"bt_lok_{x['id']}", on_click=atur, args=("edit_lokasi", None))
                    if c2.button("Simpan", key=f"sv_lok_{x['id']}", type="primary"):
                        baru = baru.strip()
                        sama = [y["nama"] for y in D["lokasi"]
                                if y["id"] != x["id"] and (y.get("tempat") or "") == tbaru]
                        if not baru:
                            st.error("Nama tidak boleh kosong.")
                        elif ada_kembar(sama + [baru]):
                            st.error("Nama itu sudah ada di tempat ini.")
                        else:
                            galat, foto_lama = "", x.get("foto", "")
                            if foto_up is not None:
                                try:
                                    x["foto"] = simpan_foto(x["id"], foto_up.getvalue())
                                except Exception as e:
                                    galat = f"Foto gagal diunggah: {e}"
                            elif hapus_f:
                                x.pop("foto", None)
                            if galat:
                                st.error(galat)
                            else:
                                x["nama"] = baru
                                if tbaru:
                                    x["tempat"] = tbaru
                                else:
                                    x.pop("tempat", None)
                                ganti = foto_lama if x.get("foto", "") != foto_lama else ""
                                selesai_simpan("Lokasi diubah.",
                                               sesudah=(lambda p=ganti: hapus_foto(p)) if ganti else None,
                                               edit_lokasi=None)
                elif st.session_state.get("hapus_lokasi") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("lokasi") == x["id"])
                    n_s = sum(1 for s in D["sublokasi"] if s["lokasi"] == x["id"])
                    akibat = ", ".join(([f"{n_b} barang jadi tanpa lokasi"] if n_b else [])
                                       + ([f"{n_s} sub lokasi ikut terhapus"] if n_s else []))
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({akibat})" if akibat else ""))
                    c3.button("Batal", key=f"bh_lok_{x['id']}", on_click=atur, args=("hapus_lokasi", None))
                    if c2.button("Ya, hapus", key=f"yh_lok_{x['id']}", type="primary"):
                        fs = [x.get("foto", "")] + [s.get("foto", "") for s in D["sublokasi"] if s["lokasi"] == x["id"]]
                        D["lokasi"] = [y for y in D["lokasi"] if y["id"] != x["id"]]
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["lokasi"] != x["id"]]
                        selesai_simpan("Dihapus.", sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p],
                                       hapus_lokasi=None)
                else:
                    c1.markdown(html_nama_foto(x), unsafe_allow_html=True)
                    c2.button("Ubah", key=f"ub_lok_{x['id']}", icon=":material/edit:", on_click=atur, args=("edit_lokasi", x["id"]))
                    c3.button("Hapus", key=f"hp_lok_{x['id']}", icon=":material/delete:", on_click=atur, args=("hapus_lokasi", x["id"]))
        if tombol_tambah("lokasi", "Tambah lokasi"):
            with st.form("tambah_lokasi", clear_on_submit=True):
                f1, f2 = st.columns([2, 3])
                tem = f1.selectbox("Di tempat", ops, format_func=fmt)
                nama = f2.text_input("Nama lokasi", placeholder="Contoh: Lemari kamar")
                s1, s2 = st.columns(2)
                simpan = s1.form_submit_button("Simpan", type="primary", icon=":material/check:", use_container_width=True)
                batal = s2.form_submit_button("Batal", use_container_width=True)
            if batal:
                tutup_tambah("lokasi")
            if simpan:
                nama = nama.strip()
                sama = [y["nama"] for y in D["lokasi"] if (y.get("tempat") or "") == tem]
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar(sama + [nama]):
                    st.error("Nama itu sudah ada di tempat ini.")
                else:
                    baru = {"id": uuid.uuid4().hex[:8], "nama": nama}
                    if tem:
                        baru["tempat"] = tem
                    D["lokasi"].append(baru)
                    selesai_simpan("Ditambahkan.", tb_lokasi=False)


def semua_barang_pemilik() -> list:
    """Barang aktif dan barang di tempat sampah, supaya nama pemilik ikut berubah di keduanya."""
    return D["barang"] + [x["barang"] for x in D["sampah"]]


def tambah_nama_daftar(kunci: str, kunci_d: str, judul: str, maks: int, ada: list):
    """Tombol dan form tambah pemilik atau label langsung dari Pengaturan."""
    if not tombol_tambah(kunci, f"Tambah {judul.lower()}"):
        return
    with st.form(f"tambah_{kunci}_daftar", clear_on_submit=True):
        nama = st.text_input(f"Nama {judul.lower()} baru", max_chars=maks, placeholder="Nama baru")
        s1, s2 = st.columns(2)
        simpan = s1.form_submit_button("Simpan", type="primary", icon=":material/check:", use_container_width=True)
        batal = s2.form_submit_button("Batal", use_container_width=True)
    if batal:
        tutup_tambah(kunci)
    if simpan:
        nama = nama.strip()
        if not nama:
            st.error("Nama tidak boleh kosong.")
        elif nama.lower() in {x.lower() for x in ada}:
            st.error("Nama itu sudah ada.")
        else:
            D.setdefault(kunci_d, []).append(nama)
            selesai_simpan(f"{judul} ditambahkan.", **{f"tb_{kunci}": False})


def halaman_kelola_label():
    """Daftar label diambil dari barang. Di sini label bisa diubah nama, digabung, atau dilepas dari barangnya."""
    nama_nama = daftar_tag()
    with st.container(key="kartu_g_daftar_tag"):
        kepala_daftar("Label", len(nama_nama), "Label bisa ditambah di sini atau muncul otomatis dari barang. Mengubah nama ikut mengganti semua barangnya. "
                   "Kalau namanya sama dengan label lain, keduanya digabung. Menghapus label tidak menghapus barangnya.")
        if not nama_nama:
            st.caption("Belum ada label. Tambahkan di bawah, atau lewat Kelola barang.")
        for nm in nama_nama:
            n_b = sum(1 for b in D["barang"] if nm in b.get("tag", []))
            kunci = hashlib.md5(nm.encode("utf-8")).hexdigest()[:10]
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get("edit_tag") == nm:
                baru = c1.text_input("Nama", value=nm, key=f"nm_tag_{kunci}", label_visibility="collapsed", max_chars=30)
                c3.button("Batal", key=f"bt_tag_{kunci}", on_click=atur, args=("edit_tag", None))
                if c2.button("Simpan", key=f"sv_tag_{kunci}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif baru == nm:
                        st.session_state.edit_tag = None
                        st.rerun()
                    else:
                        lain = next((x for x in nama_nama if x != nm and x.lower() == baru.lower()), None)
                        akhir = lain or baru
                        for b in semua_barang_pemilik():
                            if nm in b.get("tag", []):
                                b["tag"] = list(dict.fromkeys(akhir if t == nm else t for t in b["tag"]))[:8]
                        perbarui_terdaftar("label_daftar", nm, akhir)
                        selesai_simpan(f"Digabung ke {akhir}." if lain else "Nama label diubah.", edit_tag=None)
            elif st.session_state.get("hapus_tag") == nm:
                c1.write(f"Hapus label **{nm}**?" + (f" ({n_b} barang kehilangan label ini)" if n_b else ""))
                c3.button("Batal", key=f"bh_tag_{kunci}", on_click=atur, args=("hapus_tag", None))
                if c2.button("Ya, hapus", key=f"yh_tag_{kunci}", type="primary"):
                    for b in semua_barang_pemilik():
                        if nm in b.get("tag", []):
                            sisa = [t for t in b["tag"] if t != nm]
                            if sisa:
                                b["tag"] = sisa
                            else:
                                b.pop("tag", None)
                    perbarui_terdaftar("label_daftar", nm)
                    selesai_simpan("Label dihapus.", hapus_tag=None)
            else:
                c1.write(f"{nm} · {n_b} barang")
                c2.button("Ubah", key=f"ub_tag_{kunci}", icon=":material/edit:", on_click=atur, args=("edit_tag", nm))
                c3.button("Hapus", key=f"hp_tag_{kunci}", icon=":material/delete:", on_click=atur, args=("hapus_tag", nm))
        tambah_nama_daftar("label", "label_daftar", "Label", 30, nama_nama)


def halaman_pemilik():
    """Daftar pemilik diambil dari barang. Di sini nama bisa diubah, digabung, atau dilepas dari barangnya."""
    nama_nama = daftar_pemilik()
    with st.container(key="kartu_g_daftar_pem"):
        kepala_daftar("Pemilik", len(nama_nama), "Pemilik bisa ditambah di sini atau muncul otomatis dari barang. Mengubah nama ikut mengganti semua barangnya. "
                   "Kalau namanya sama dengan pemilik lain, keduanya digabung. Menghapus pemilik tidak menghapus barangnya.")
        if not nama_nama:
            st.caption("Belum ada pemilik. Tambahkan di bawah, atau isi lewat Kelola barang.")
        for nm in nama_nama:
            n_b = sum(1 for b in D["barang"] if b.get("pemilik") == nm)
            kunci = hashlib.md5(nm.encode("utf-8")).hexdigest()[:10]
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get("edit_pemilik") == nm:
                baru = c1.text_input("Nama", value=nm, key=f"nm_pem_{kunci}", label_visibility="collapsed", max_chars=40)
                c3.button("Batal", key=f"bt_pem_{kunci}", on_click=atur, args=("edit_pemilik", None))
                if c2.button("Simpan", key=f"sv_pem_{kunci}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif baru == nm:
                        st.session_state.edit_pemilik = None
                        st.rerun()
                    else:
                        lain = next((x for x in nama_nama if x != nm and x.lower() == baru.lower()), None)
                        akhir = lain or baru          # kalau sudah ada pemilik serupa, pakai ejaan yang sudah ada
                        for b in semua_barang_pemilik():
                            if b.get("pemilik") == nm:
                                b["pemilik"] = akhir
                        perbarui_terdaftar("pemilik_daftar", nm, akhir)
                        selesai_simpan(f"Digabung ke {akhir}." if lain else "Nama pemilik diubah.", edit_pemilik=None)
            elif st.session_state.get("hapus_pemilik") == nm:
                c1.write(f"Hapus pemilik **{nm}**?" + (f" ({n_b} barang jadi tanpa pemilik)" if n_b else ""))
                c3.button("Batal", key=f"bh_pem_{kunci}", on_click=atur, args=("hapus_pemilik", None))
                if c2.button("Ya, hapus", key=f"yh_pem_{kunci}", type="primary"):
                    for b in semua_barang_pemilik():
                        if b.get("pemilik") == nm:
                            b.pop("pemilik", None)
                    perbarui_terdaftar("pemilik_daftar", nm)
                    selesai_simpan("Pemilik dihapus.", hapus_pemilik=None)
            else:
                c1.write(f"{nm} · {n_b} barang")
                c2.button("Ubah", key=f"ub_pem_{kunci}", icon=":material/edit:", on_click=atur, args=("edit_pemilik", nm))
                c3.button("Hapus", key=f"hp_pem_{kunci}", icon=":material/delete:", on_click=atur, args=("hapus_pemilik", nm))
        tambah_nama_daftar("pemilik", "pemilik_daftar", "Pemilik", 40, nama_nama)


def cadangan():
    with st.container(key="kartu_g_cadangan"):
        st.caption("Unduh seluruh data sebagai file, atau muat file data dari tempat lain. "
                   "Memuat file akan **mengganti semua data** yang ada sekarang. "
                   "Foto tidak ikut di file ini, foto tersimpan terpisah di folder foto/ pada repositori data. "
                   "File lama berisi daftar barang (items.json) juga bisa dimuat dan otomatis diubah formatnya.")
        st.download_button("Unduh data.json", json.dumps(D.data, ensure_ascii=False, indent=1, sort_keys=True),
                           file_name="data.json", mime="application/json")
        with st.form("impor"):
            berkas = st.file_uploader("File data.json", type=["json"])
            yakin = st.checkbox("Ya, ganti semua data dengan isi file ini")
            if st.form_submit_button("Muat file"):
                if berkas is None:
                    st.error("Pilih filenya dulu.")
                elif not yakin:
                    st.error("Centang dulu \"Ya, ganti semua data\".")
                else:
                    try:
                        baru = json.load(berkas)
                        if isinstance(baru, list):
                            baru = konversi_lama(baru)
                        assert isinstance(baru, dict)
                        assert isinstance(baru.get("barang"), list)
                        assert isinstance(baru.get("lokasi", []), list)
                    except Exception:
                        st.error("File tidak dikenali sebagai data barang.")
                    else:
                        for kunci, awal in data_kosong().items():
                            baru.setdefault(kunci, awal)
                        st.session_state.data = baru
                        selesai_simpan("Data dimuat.")
