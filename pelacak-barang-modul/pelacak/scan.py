"""Scan barcode."""
import re
import uuid

import requests
import streamlit as st

from pelacak.bantu import (
    catat, daftar_lokasi, kartu_barang_html, nama_lok, nama_tempat, peringatan_serupa,
    selesai_simpan, versi,
)
from pelacak.beranda import cek_tiap_b
from pelacak.inti import D, TANPA_KAT, hari_ini


# ------------------------------------------------------------ scan barcode
@st.cache_data(show_spinner=False, max_entries=8)
def baca_barcode(data: bytes):
    """Daftar kode yang terbaca dari foto. None kalau pustaka pembaca belum terpasang."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    sisi = max(img.shape[:2])
    if sisi > 1600:
        img = cv2.resize(img, None, fx=1600 / sisi, fy=1600 / sisi, interpolation=cv2.INTER_AREA)
    kelas = getattr(cv2, "barcode_BarcodeDetector", None) or getattr(getattr(cv2, "barcode", None), "BarcodeDetector", None)
    bd = kelas() if kelas else None

    def kumpul(res, ke):
        for x in res:
            if isinstance(x, str) and x.strip():
                ke.append(x.strip())
            elif isinstance(x, (tuple, list)):
                for y in x:
                    if isinstance(y, str) and y.strip():
                        ke.append(y.strip())

    for putar in (None, cv2.ROTATE_90_CLOCKWISE):
        dasar = img if putar is None else cv2.rotate(img, putar)
        for skala in (1.0, 0.75, 0.5, 0.35, 0.25, 1.5, 2.0):
            im = cv2.resize(dasar, None, fx=skala, fy=skala,
                            interpolation=cv2.INTER_AREA if skala < 1 else cv2.INTER_CUBIC)
            if min(im.shape[:2]) < 60:
                continue
            ketemu = []
            try:
                if bd is not None:
                    kumpul(bd.detectAndDecode(im), ketemu)
                if not ketemu:
                    kumpul(cv2.QRCodeDetector().detectAndDecode(im), ketemu)
            except Exception:
                continue
            if ketemu:
                return list(dict.fromkeys(ketemu))
    return []


@st.cache_data(ttl=86400, show_spinner=False)
def cari_produk(kode: str) -> dict:
    """Nama produk dari basis data terbuka. Melempar galat kalau tidak ada yang bisa dihubungi."""
    galat = False
    for host in ("world.openfoodfacts.org", "world.openbeautyfacts.org", "world.openproductsfacts.org"):
        try:
            r = requests.get(f"https://{host}/api/v2/product/{kode}.json",
                             params={"fields": "product_name,brands,quantity"},
                             headers={"User-Agent": "PelacakBarang/1.0 (pribadi)"}, timeout=6)
            if r.status_code != 200:
                continue
            j = r.json()
            p = j.get("product", {}) if j.get("status") == 1 else {}
            nama = (p.get("product_name") or "").strip()
            if nama:
                return {"nama": nama, "merek": (p.get("brands") or "").split(",")[0].strip(),
                        "ukuran": (p.get("quantity") or "").strip()}
        except Exception:
            galat = True
    if galat:
        raise RuntimeError("tidak terhubung")
    return {}


def form_scan_baru(kode: str, n: int):
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di Pengaturan > Lokasi sebelum menambah barang.")
        return
    info = {}
    try:
        info = cari_produk(kode)
        if info:
            st.caption("Nama dan merek diambil dari basis data produk terbuka (Open Food Facts). Periksa dulu, ubah kalau perlu.")
        else:
            st.caption("Kode ini belum ada di basis data produk, jadi isi namanya sendiri.")
    except Exception:
        st.caption("Basis data produk tidak bisa dihubungi sekarang, jadi isi namanya sendiri.")
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    if st.session_state.get("cepat_lok") not in pl:
        st.session_state.cepat_lok = next(iter(pl))
    lok = st.selectbox("Disimpan di", list(pl), key="cepat_lok", format_func=lambda i: pl[i])
    with st.form(f"form_scan_{kode}_{versi()}"):
        nama = st.text_input("Nama barang", value=info.get("nama", ""))
        a1, a2 = st.columns(2)
        merek = a1.text_input("Merek", value=info.get("merek", ""))
        ukuran = a2.text_input("Ukuran", value=info.get("ukuran", ""))
        jumlah = st.number_input("Jumlah", min_value=0, value=1, step=1)
        kat = ""
        if D["kategori"]:
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            ops_k = [""] + list(pk)
            kat = st.selectbox("Kategori (boleh kosong)", ops_k, format_func=lambda i: TANPA_KAT if not i else pk[i])
        kirim = st.form_submit_button("Simpan barang", type="primary")
    if kirim:
        nama = nama.strip()
        if not nama:
            st.error("Nama barang wajib diisi.")
            return
        if peringatan_serupa(nama):
            return
        b = {"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": lok, "jumlah": int(jumlah), "barcode": kode,
             "diubah": hari_ini().isoformat()}
        for kunci, v in (("merek", merek), ("ukuran", ukuran), ("kategori", kat)):
            if v and v.strip():
                b[kunci] = v.strip()
        catat(b["id"], nama, "", nama_tempat(b))
        D["barang"].append(b)
        selesai_simpan(f"{nama} ditambahkan.", sc_n=n + 1)


def halaman_scan():
    n = st.session_state.get("sc_n", 0)
    kode, galat = "", ""
    with st.container(key="kartu_barang"):
        st.caption("Foto barcode di kemasan barang. Kalau barangnya sudah pernah dicatat, langsung muncul. "
                   "Kalau belum, kamu bisa menambahkannya dan namanya dicari otomatis.")
        cara = st.segmented_control("Cara", ["Kamera", "Unggah foto", "Ketik kode"], default="Kamera",
                                    key="sc_cara", label_visibility="collapsed") or "Kamera"
        foto = None
        if cara == "Kamera":
            foto = st.camera_input("Arahkan kamera ke barcode, dekat dan terang", key=f"sc_cam_{n}")
        elif cara == "Unggah foto":
            foto = st.file_uploader("Foto barcode", type=["jpg", "jpeg", "png", "webp"], key=f"sc_up_{n}")
        else:
            with st.form(f"form_sc_ketik_{n}"):
                ketik = st.text_input("Kode barcode", placeholder="Contoh: 8991234567890")
                st.form_submit_button("Cari kode", type="primary")
            kode = re.sub(r"\s+", "", ketik or "")
        if foto is not None:
            hasil = baca_barcode(foto.getvalue())
            if hasil is None:
                galat = "Pembaca barcode belum terpasang. Tambahkan opencv-python-headless ke requirements.txt, atau ketik kodenya."
            elif not hasil:
                galat = "Barcode belum terbaca. Dekatkan, pastikan terang dan tegak lurus, atau ketik kodenya."
            elif len(hasil) == 1:
                kode = hasil[0]
            else:
                kode = st.selectbox("Beberapa kode terbaca, pilih satu", hasil, key=f"sc_pilih_{n}")
        if galat:
            st.warning(galat)
    if not kode:
        return
    if not re.fullmatch(r"[A-Za-z0-9\-\.\/\+ ]{3,40}", kode):
        st.warning("Kode ini tidak terlihat seperti barcode barang.")
        return
    with st.container(key="kartu_tgl_scan"):
        st.markdown(f"**Kode terbaca:** `{kode}`")
        ada = [b for b in D["barang"] if b.get("barcode") == kode]
        if ada:
            st.success(f"Ditemukan {len(ada)} barang dengan kode ini.")
            for b in ada:
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Dipakai hari ini", key=f"sc_pakai_{b['id']}"):
                    b["dipakai"] = hari_ini().isoformat()
                    selesai_simpan("Dicatat dipakai hari ini.", sc_n=n + 1)
                if cek_tiap_b(b) and c2.button("Sudah dicek", key=f"sc_cek_{b['id']}"):
                    b["cek_terakhir"] = hari_ini().isoformat()
                    selesai_simpan("Dicatat sudah dicek.", sc_n=n + 1)
            with st.expander("Tambah barang lain dengan kode ini"):
                form_scan_baru(kode, n)
        else:
            st.info("Belum ada barang dengan kode ini.")
            form_scan_baru(kode, n)
            polos = sorted([b for b in D["barang"] if not b.get("barcode")], key=lambda x: x["nama"].lower())
            if polos:
                with st.expander("Atau pasang kode ini ke barang yang sudah ada"):
                    pid = st.selectbox("Barang", [b["id"] for b in polos], key=f"sc_pasang_{n}",
                                       format_func=lambda i: next(x["nama"] for x in polos if x["id"] == i))
                    if st.button("Pasang kode", key=f"sc_pasang_go_{n}"):
                        next(x for x in polos if x["id"] == pid)["barcode"] = kode
                        selesai_simpan("Kode dipasang.", sc_n=n + 1)
