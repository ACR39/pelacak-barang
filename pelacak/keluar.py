"""Barang yang dijual atau diberikan: keluar dari daftar aktif, tapi harga jual dan penerimanya tetap tercatat."""
import html
import uuid

import streamlit as st

from pelacak.bantu import harga_b, isi_dari, jumlah_b, pinjam_aktif, selesai_simpan, versi
from pelacak.inti import D, fmt_iso, hari_ini, pengguna_nama, rp, sekarang

JENIS = ["Dijual", "Diberikan"]


def _int(v) -> int:
    try:
        return max(int(v or 0), 0)
    except Exception:
        return 0


def lepas_barang(b: dict, jenis: str, tgl: str, harga: int, kepada: str, catatan: str):
    """Pindahkan barang dari daftar aktif ke daftar keluar."""
    for x in isi_dari(b["id"]):
        x.pop("dalam", None)
    D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
    D.setdefault("keluar", []).append(
        {"id": uuid.uuid4().hex[:8], "barang": dict(b), "jenis": jenis.lower(), "tgl": tgl, "harga": int(harga),
         "kepada": kepada.strip(), "catatan": catatan.strip(), "oleh": pengguna_nama()})
    D["aktivitas"].append({"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"),
                           "oleh": pengguna_nama(), "jenis": "ubah", "barang": b["id"], "nama": b["nama"],
                           "rincian": f"{jenis} dan keluar dari daftar" + (f" ({rp(harga)})" if harga else "")})


def kembalikan_barang(k: dict):
    """Masukkan lagi barang ke daftar aktif."""
    b = dict(k["barang"])
    D["barang"].append(b)
    D["keluar"] = [x for x in D["keluar"] if x["id"] != k["id"]]


def halaman_keluar():
    keluar = D.setdefault("keluar", [])
    barang = sorted(D["barang"], key=lambda b: b["nama"].lower())
    by = {b["id"]: b for b in barang}
    with st.container(key="kartu_keluar"):
        if barang:
            with st.expander("Lepas barang (dijual atau diberikan)", expanded=not keluar):
                with st.form(f"form_keluar_{versi()}"):
                    pilih = st.selectbox("Barang", [b["id"] for b in barang], key="kl_pilih",
                                         format_func=lambda i: f'{by[i]["nama"]}'
                                         + (f' · beli {rp(harga_b(by[i]))}' if harga_b(by[i]) else ""))
                    c1, c2 = st.columns(2)
                    jenis = c1.radio("Jenis", JENIS, horizontal=True, key="kl_jenis")
                    tgl = c2.date_input("Tanggal", value=hari_ini(), key="kl_tgl2")
                    c1, c2 = st.columns(2)
                    harga = int(c1.number_input("Harga jual (isi 0 kalau diberikan)", min_value=0, step=1000,
                                                value=0, key="kl_harga"))
                    kepada = c2.text_input("Kepada (opsional)", max_chars=80, key="kl_kepada")
                    cat = st.text_input("Catatan (opsional)", max_chars=200, key="kl_cat2")
                    kirim = st.form_submit_button("Lepas dari daftar", type="primary")
                if kirim:
                    b = by[pilih]
                    if pinjam_aktif(b["id"]) or b.get("dibawa"):
                        st.error("Barang ini sedang dipinjamkan atau dibawa. Selesaikan dulu di menu masing-masing.")
                    else:
                        if jenis == "Diberikan":
                            harga = 0
                        lepas_barang(b, jenis, tgl.isoformat(), harga, kepada, cat)
                        selesai_simpan(f"{b['nama']} dicatat {jenis.lower()} dan dikeluarkan dari daftar.")
        else:
            st.info("Belum ada barang yang bisa dilepas.")
        if not keluar:
            st.caption("Belum ada barang yang dijual atau diberikan.")
            return
        dijual = [k for k in keluar if k.get("jenis") == "dijual"]
        uang = sum(_int(k.get("harga")) for k in dijual)
        modal = sum(harga_b(k["barang"]) * max(jumlah_b(k["barang"]), 1) for k in dijual)
        a, c = st.columns(2)
        a.metric("Uang dari penjualan", rp(uang))
        selisih = uang - modal if modal else None
        c.metric("Selisih dengan harga beli", rp(abs(selisih)) if selisih is not None else "-",
                 delta=None if selisih is None else ("rugi" if selisih < 0 else "untung" if selisih > 0 else "impas"),
                 delta_color="off")
        st.caption(f"{len(dijual)} dijual · {len(keluar) - len(dijual)} diberikan. "
                   "Selisih dihitung dari harga beli dikali jumlah barang, hanya untuk yang dijual.")
        for k in sorted(keluar, key=lambda x: x.get("tgl", ""), reverse=True):
            b = k["barang"]
            with st.container(key=f"item_kel_{k['id']}", border=True):
                st.markdown(f"**{html.escape(b.get('nama', ''))}** · {k.get('jenis', '').capitalize()}")
                bagian = [fmt_iso(k.get("tgl", ""))]
                if _int(k.get("harga")):
                    bagian.append(rp(k["harga"]))
                if k.get("kepada"):
                    bagian.append(f"kepada {k['kepada']}")
                st.caption(" · ".join(bagian))
                if k.get("catatan"):
                    st.caption(k["catatan"])
                if st.session_state.get("kel_hapus") == k["id"]:
                    st.warning("Hapus catatan ini selamanya? Barangnya tidak kembali ke daftar.")
                    y, n = st.columns(2)
                    if y.button("Ya, hapus catatan", key=f"kel_ya_{k['id']}", type="primary"):
                        D["keluar"] = [x for x in keluar if x["id"] != k["id"]]
                        selesai_simpan("Catatan dihapus.", kel_hapus=None)
                    if n.button("Batal", key=f"kel_batal_{k['id']}"):
                        st.session_state.kel_hapus = None
                        st.rerun()
                else:
                    c1, c2 = st.columns(2)
                    if c1.button("Kembalikan ke daftar", key=f"kel_kembali_{k['id']}", use_container_width=True):
                        kembalikan_barang(k)
                        selesai_simpan(f"{b.get('nama', '')} dikembalikan ke daftar.")
                    if c2.button("Hapus catatan", key=f"kel_hapus_{k['id']}", use_container_width=True):
                        st.session_state.kel_hapus = k["id"]
                        st.rerun()
