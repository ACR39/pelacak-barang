"""Dibawa, hilang, rusak dan diservis, serta catatan perawatan."""
import html
import uuid
from datetime import date

import streamlit as st

from pelacak.bantu import (
    KONDISI, atur, daftar_lokasi, html_tautan, induk_dari, kartu_barang_html, nama_lok,
    nama_tempat, selesai_simpan, versi,
)
from pelacak.barang import kembalikan_dibawa, tandai_dibawa, tandai_hilang, tandai_ketemu
from pelacak.beranda import cek_tiap_b
from pelacak.inti import D, TGL_MAX, TGL_MIN, fmt_iso, hari_ini, rp, teks_cek


# ------------------------------------------------------------ dibawa dan hilang
def _hari_sejak(iso: str) -> int:
    try:
        return (hari_ini() - date.fromisoformat(iso)).days
    except Exception:
        return 0


def tab_dibawa():
    by = {b["id"]: b for b in D["barang"]}
    aktif = sorted([b for b in D["barang"] if b.get("dibawa")], key=lambda b: b["dibawa"])
    atas = [b for b in aktif if not (induk_dari(b) and induk_dari(b).get("dibawa"))]
    with st.container(key="kartu_g_dibawa"):
        if st.session_state.get("db_mode"):
            st.markdown("#### Bawa barang")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower())
                     if not b.get("dibawa") and not b.get("hilang")]
            if not calon:
                st.info("Semua barang sudah ditandai.")
                st.button("Kembali", key="db_kembali_kosong", on_click=atur, args=("db_mode", False))
                return
            with st.form(f"form_bawa_{versi()}"):
                pil = st.multiselect("Barang yang dibawa", [b["id"] for b in calon],
                                     format_func=lambda i: f'{by[i]["nama"]} ({nama_tempat(by[i])})')
                ke = st.text_input("Dibawa ke mana atau untuk apa (boleh kosong)", max_chars=60,
                                   placeholder="Contoh: Kantor, atau Naik gunung")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai dibawa", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.db_mode = False
                st.rerun()
            if ok:
                if not pil:
                    st.error("Pilih minimal satu barang.")
                else:
                    for i in pil:
                        tandai_dibawa(by[i], ke.strip())
                    selesai_simpan(f"{len(pil)} barang ditandai sedang dibawa.", db_mode=False)
            return
        st.button("Bawa barang", type="primary", key="db_tambah", icon=":material/add:",
                  on_click=atur, args=("db_mode", True))
        if not atas:
            st.info("Tidak ada barang yang sedang dibawa. Tandai barang yang kamu bawa keluar, misalnya ke kantor "
                    "atau saat bepergian. Lokasi aslinya diingat, jadi pulangnya tinggal satu sentuhan.")
            return
        st.caption(f"{len(atas)} barang sedang dibawa.")
        for b in atas:
            with st.container(key=f"item_db_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                h = _hari_sejak(b["dibawa"])
                st.caption(f"Lokasi asal: {nama_tempat(b)} · " + (f"sudah {h} hari" if h else "sejak hari ini"))
                if st.button("Sudah kembali ke tempatnya", key=f"kpakai_db_{b['id']}"):
                    kembalikan_dibawa(b)
                    selesai_simpan(f"{b['nama']} dikembalikan ke lokasi asalnya.")
        if len(atas) > 1 and st.button(f"Kembalikan semua ({len(atas)})", key="db_semua"):
            for b in atas:
                kembalikan_dibawa(b)
            selesai_simpan("Semua barang dikembalikan ke lokasi asalnya.")


def tab_hilang():
    hl = sorted([b for b in D["barang"] if b.get("hilang")], key=lambda b: b["hilang"])
    with st.container(key="kartu_g_hilang"):
        if st.session_state.get("hl_mode"):
            st.markdown("#### Tandai barang hilang")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if not b.get("hilang")]
            if not calon:
                st.info("Belum ada barang.")
                st.button("Kembali", key="hl_kembali_kosong", on_click=atur, args=("hl_mode", False))
                return
            by = {b["id"]: b for b in calon}
            with st.form(f"form_hilang_{versi()}"):
                i = st.selectbox("Barang", list(by), format_func=lambda x: f'{by[x]["nama"]} ({nama_tempat(by[x])})')
                di = st.text_input("Terakhir terlihat di (boleh kosong)", max_chars=80,
                                   placeholder="Contoh: meja kerja, atau tas ransel")
                tgl = st.date_input("Terakhir terlihat tanggal", value=hari_ini(), min_value=TGL_MIN,
                                    max_value=TGL_MAX, format="DD/MM/YYYY")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai hilang", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.hl_mode = False
                st.rerun()
            if ok:
                tandai_hilang(by[i], di.strip(), tgl)
                selesai_simpan(f"{by[i]['nama']} ditandai hilang.", hl_mode=False)
            return
        st.button("Tandai hilang", type="primary", key="hl_tambah", icon=":material/add:",
                  on_click=atur, args=("hl_mode", True))
        if not hl:
            st.info("Tidak ada barang yang hilang. Kalau ada barang yang tidak ketemu, tandai di sini supaya tidak "
                    "terlupa dan tempat terakhir terlihatnya tercatat.")
            return
        st.caption(f"{len(hl)} barang belum ketemu.")
        for b in hl:
            with st.container(key=f"item_hl_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                st.button("Sudah ketemu", key=f"kpakai_hl_{b['id']}", on_click=atur, args=("hl_ketemu", b["id"]))
                if st.session_state.get("hl_ketemu") == b["id"]:
                    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
                    if induk_dari(b) or not pl:
                        lok = ""
                        st.caption(f"Barang ini disimpan di dalam {induk_dari(b)['nama']}, jadi tetap di lokasi itu."
                                   if induk_dari(b) else "")
                    else:
                        lok = st.selectbox("Ketemu di lokasi mana?", [""] + list(pl), key=f"hl_lok_{b['id']}",
                                           format_func=lambda x, b=b: f"Tetap di lokasi semula ({nama_tempat(b)})"
                                           if not x else pl[x])
                    y, n, _ = st.columns([1, 1, 2])
                    if y.button("Simpan", type="primary", key=f"hl_ya_{b['id']}"):
                        tandai_ketemu(b, lok)
                        selesai_simpan(f"{b['nama']} sudah ketemu.", hl_ketemu=None)
                    n.button("Batal", key=f"hl_batal_{b['id']}", on_click=atur, args=("hl_ketemu", None))


# ------------------------------------------------------------ catatan perawatan
JENIS_RAWAT = ["Servis", "Perbaikan", "Ganti suku cadang", "Pembersihan", "Pengecekan", "Lainnya"]


def catat_perawatan(b: dict, tgl: date, jenis: str, catatan: str = "", biaya: int = 0):
    """Tambah satu catatan perawatan ke barang. Kalau barang punya pengingat berkala, jadwal cek ikut diperbarui."""
    b.setdefault("perawatan", []).append({"id": uuid.uuid4().hex[:8], "tgl": tgl.isoformat(), "jenis": jenis,
                                          "catatan": catatan.strip(), "biaya": max(int(biaya or 0), 0)})
    b["perawatan"] = b["perawatan"][-200:]
    if jenis != "Lainnya" and cek_tiap_b(b) and tgl.isoformat() >= (b.get("cek_terakhir") or ""):
        b["cek_terakhir"] = tgl.isoformat()
    b["diubah"] = hari_ini().isoformat()


def html_rawat(x: dict, nama_barang: str = "") -> str:
    judul = html.escape(x.get("jenis", "")) + (f" · {html.escape(nama_barang)}" if nama_barang else "")
    cat = f'<div class="ar">{html_tautan(x["catatan"])}</div>' if x.get("catatan") else ""
    biaya = f" · {rp(x['biaya'])}" if x.get("biaya") else ""
    return (f'<div class="akt"><div class="ah">{judul}</div>{cat}'
            f'<div class="am">{fmt_iso(x.get("tgl", ""))}{biaya}</div></div>')


def halaman_perawatan():
    t1, t2 = st.tabs(["Per barang", "Terbaru"])
    with t1:
        with st.container(key="kartu_g_rawat"):
            if not D["barang"]:
                st.info("Belum ada barang.")
                return
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            by = {b["id"]: b for b in urut}
            if st.session_state.get("rwt_barang") not in by:
                st.session_state.rwt_barang = urut[0]["id"]
            pid = st.selectbox("Barang", list(by), key="rwt_barang",
                               format_func=lambda i: f'{by[i]["nama"]} ({nama_tempat(by[i])})')
            b = by[pid]
            riw = sorted(b.get("perawatan", []), key=lambda x: x.get("tgl", ""), reverse=True)
            total = sum(int(x.get("biaya", 0) or 0) for x in riw)
            st.caption(f"{len(riw)} catatan" + (f" · terakhir {fmt_iso(riw[0]['tgl'])}" if riw else "")
                       + (f" · total biaya {rp(total)}" if total else ""))
            with st.form(f"form_rawat_{versi()}"):
                f1, f2 = st.columns(2)
                tgl = f1.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                jenis = f2.selectbox("Jenis", JENIS_RAWAT)
                catatan = st.text_area("Catatan (boleh kosong)", height=80, max_chars=500,
                                       placeholder="Contoh: ganti oli, filter air diganti")
                biaya = st.number_input("Biaya (Rp, boleh 0)", min_value=0, value=0, step=1000)
                kirim = st.form_submit_button("Tambah catatan", type="primary")
            if kirim:
                catat_perawatan(b, tgl, jenis, catatan, int(biaya))
                selesai_simpan("Catatan perawatan ditambahkan.")
            if b.get("cek_tiap"):
                st.caption(f"Barang ini punya pengingat berkala ({teks_cek(b['cek_tiap']).lower()}). "
                           "Menambah catatan selain Lainnya ikut memperbarui tanggal terakhir dicek.")
            for x in riw:
                st.markdown(html_rawat(x), unsafe_allow_html=True)
                if st.session_state.get("rt_hapus") == x["id"]:
                    st.warning("Hapus catatan ini?")
                    y, n, _ = st.columns([1, 1, 3])
                    if y.button("Ya, hapus", type="primary", key=f"rtya_{x['id']}"):
                        b["perawatan"] = [r for r in b["perawatan"] if r["id"] != x["id"]]
                        if not b["perawatan"]:
                            b.pop("perawatan", None)
                        selesai_simpan("Catatan dihapus.", rt_hapus=None)
                    n.button("Batal", key=f"rtbt_{x['id']}", on_click=atur, args=("rt_hapus", None))
                else:
                    st.button("Hapus", key=f"khapus_rt_{x['id']}", on_click=atur, args=("rt_hapus", x["id"]))
    with t2:
        with st.container(key="kartu_g_rawat2"):
            semua = [(x, b) for b in D["barang"] for x in b.get("perawatan", [])]
            if not semua:
                st.info("Belum ada catatan perawatan. Tambahkan lewat tab Per barang.")
            else:
                st.caption(f"{len(semua)} catatan di {len({b['id'] for _, b in semua})} barang. 30 terbaru ditampilkan.")
                for x, b in sorted(semua, key=lambda t: t[0].get("tgl", ""), reverse=True)[:30]:
                    st.markdown(html_rawat(x, b["nama"]), unsafe_allow_html=True)


# ------------------------------------------------------------ rusak dan sedang diservis
def tandai_kondisi(b: dict, kondisi: str, ket: str = "", tgl=None):
    if not b.get("kondisi_sejak") or tgl:
        b["kondisi_sejak"] = (tgl or hari_ini()).isoformat()
    b["kondisi"] = kondisi
    if ket:
        b["kondisi_ket"] = ket
    else:
        b.pop("kondisi_ket", None)
    b["diubah"] = hari_ini().isoformat()


def kondisi_beres(b: dict, ket: str = "", biaya: int = 0):
    """Barang sudah baik lagi. Dicatat otomatis sebagai catatan perawatan."""
    if b.get("kondisi") in KONDISI:
        catat_perawatan(b, hari_ini(), "Perbaikan" if b["kondisi"] == "rusak" else "Servis",
                        ket or b.get("kondisi_ket", ""), biaya)
    for k in ("kondisi", "kondisi_sejak", "kondisi_ket"):
        b.pop(k, None)
    b["diubah"] = hari_ini().isoformat()


def tab_rusak():
    rs = sorted([b for b in D["barang"] if b.get("kondisi") in KONDISI], key=lambda b: b.get("kondisi_sejak", ""))
    with st.container(key="kartu_g_rusak"):
        if st.session_state.get("rs_mode"):
            st.markdown("#### Tandai rusak atau diservis")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if not b.get("kondisi")]
            if not calon:
                st.info("Semua barang sudah ditandai.")
                st.button("Kembali", key="rs_kembali_kosong", on_click=atur, args=("rs_mode", False))
                return
            by = {b["id"]: b for b in calon}
            with st.form(f"form_rusak_{versi()}"):
                i = st.selectbox("Barang", list(by), format_func=lambda x: f'{by[x]["nama"]} ({nama_tempat(by[x])})')
                kd = st.radio("Kondisi", ["Rusak", "Sedang diservis"], horizontal=True)
                ket = st.text_input("Keterangan (boleh kosong)", max_chars=100,
                                    placeholder="Contoh: layar retak, atau dikirim ke toko servis")
                tgl = st.date_input("Sejak", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.rs_mode = False
                st.rerun()
            if ok:
                tandai_kondisi(by[i], "rusak" if kd == "Rusak" else "servis", ket.strip(), tgl)
                selesai_simpan(f"{by[i]['nama']} ditandai {kd.lower()}.", rs_mode=False)
            return
        st.button("Tandai rusak atau diservis", type="primary", key="rs_tambah", icon=":material/add:",
                  on_click=atur, args=("rs_mode", True))
        if not rs:
            st.info("Tidak ada barang yang rusak atau sedang diservis. Tandai di sini supaya tidak terlupa, "
                    "dan saat sudah beres otomatis tercatat di Catatan perawatan.")
            return
        st.caption(f"{len(rs)} barang belum beres.")
        for b in rs:
            with st.container(key=f"item_rs_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                e1, e2, _ = st.columns([1.6, 1.8, 0.4])
                lain = "servis" if b["kondisi"] == "rusak" else "rusak"
                if e1.button("Sudah beres", key=f"kpakai_rs_{b['id']}", use_container_width=True,
                             on_click=atur, args=("rs_beres", b["id"])):
                    pass
                if e2.button(f"Ubah ke {KONDISI[lain].lower()}", key=f"kedit_rs_{b['id']}", use_container_width=True):
                    tandai_kondisi(b, lain, b.get("kondisi_ket", ""))
                    selesai_simpan(f"{b['nama']} ditandai {KONDISI[lain].lower()}.")
                if st.session_state.get("rs_beres") == b["id"]:
                    ct = st.text_input("Catatan hasil (boleh kosong)", key=f"rs_ct_{b['id']}", max_chars=200,
                                       placeholder="Contoh: ganti layar, garansi toko")
                    bi = st.number_input("Biaya (Rp, boleh 0)", min_value=0, value=0, step=1000, key=f"rs_bi_{b['id']}")
                    y, n, _ = st.columns([1.2, 1, 1.4])
                    if y.button("Simpan", type="primary", key=f"rs_ya_{b['id']}"):
                        kondisi_beres(b, ct.strip(), int(bi))
                        selesai_simpan(f"{b['nama']} sudah beres dan dicatat di perawatan.", rs_beres=None)
                    n.button("Batal", key=f"rs_bt_{b['id']}", on_click=atur, args=("rs_beres", None))


def halaman_dibawa():
    t1, t2, t3 = st.tabs(["Sedang dibawa", "Hilang", "Rusak dan servis"])
    with t1:
        tab_dibawa()
    with t2:
        tab_hilang()
    with t3:
        tab_rusak()
