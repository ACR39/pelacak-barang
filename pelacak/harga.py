"""Riwayat harga beli: catat tiap pembelian, lihat termurah, rata-rata, dan tren."""
import uuid

import pandas as pd
import streamlit as st

from pelacak.bantu import harga_asli_b, harga_b, jumlah_b, nama_tempat, selesai_simpan, versi
from pelacak.inti import D, fmt_iso, hari_ini, iso_ke_date, rp


def _int(v) -> int:
    try:
        return max(int(v or 0), 0)
    except Exception:
        return 0


def riwayat_b(b: dict) -> list:
    """Daftar pembelian barang, urut tanggal naik. Kalau belum ada catatan tetapi ada harga atau tanggal beli
    di data utama, pembelian itu ditampilkan sebagai satu entri (tanpa mengubah data)."""
    r = [dict(x) for x in b.get("riwayat_harga", []) if _int(x.get("harga"))]
    if not r and harga_b(b):
        r = [{"id": "awal", "tgl": b.get("dibeli") or "", "harga": harga_b(b), "harga_asli": harga_asli_b(b),
              "toko": b.get("toko", ""), "jumlah": 1, "catatan": ""}]
    return sorted(r, key=lambda x: (x.get("tgl") or "0000-00-00"))


def ringkas(b: dict):
    """Ringkasan harga per buah, atau None kalau belum ada harga."""
    r = riwayat_b(b)
    if not r:
        return None
    hrg = [_int(x["harga"]) for x in r]
    murah = min(r, key=lambda x: _int(x["harga"]))
    tren = ""
    if len(r) >= 2:
        sebelum, akhir = hrg[-2], hrg[-1]
        if akhir > sebelum:
            tren = f"naik {rp(akhir - sebelum)} dari pembelian sebelumnya"
        elif akhir < sebelum:
            tren = f"turun {rp(sebelum - akhir)} dari pembelian sebelumnya"
        else:
            tren = "sama dengan pembelian sebelumnya"
    return {"n": len(r), "terakhir": r[-1], "termurah": murah, "tertinggi": max(hrg),
            "rata": sum(hrg) / len(hrg), "tren": tren, "daftar": r}


def sinkron_utama(b: dict):
    """Samakan data utama barang dengan pembelian terbaru di riwayat."""
    r = sorted(b.get("riwayat_harga", []), key=lambda x: (x.get("tgl") or "0000-00-00"))
    b["riwayat_harga"] = r
    if not r:
        return
    t = r[-1]
    b["harga"] = _int(t.get("harga"))
    if _int(t.get("harga_asli")):
        b["harga_asli"] = _int(t["harga_asli"])
    else:
        b.pop("harga_asli", None)
    if t.get("toko"):
        b["toko"] = t["toko"]
    if t.get("tgl"):
        b["dibeli"] = t["tgl"]


def catat_pembelian(b: dict, tgl: str, harga: int, harga_asli: int, toko: str, jumlah: int, catatan: str,
                    tambah_stok: bool):
    """Tambah satu pembelian ke barang. Pembelian awal dari data utama dijadikan entri pertama."""
    if not b.get("riwayat_harga") and harga_b(b):
        b["riwayat_harga"] = [{"id": uuid.uuid4().hex[:8], "tgl": b.get("dibeli") or "", "harga": harga_b(b),
                               "harga_asli": harga_asli_b(b), "toko": b.get("toko", ""), "jumlah": 1,
                               "catatan": ""}]
    b.setdefault("riwayat_harga", []).append(
        {"id": uuid.uuid4().hex[:8], "tgl": tgl, "harga": int(harga), "harga_asli": int(harga_asli or 0),
         "toko": toko.strip(), "jumlah": int(jumlah), "catatan": catatan.strip()})
    sinkron_utama(b)
    if tambah_stok:
        b["jumlah"] = jumlah_b(b) + int(jumlah)
        b.pop("habis", None)
    b["diubah"] = hari_ini().isoformat()


def halaman_harga():
    if not D["barang"]:
        st.info("Belum ada barang.")
        return
    barang = sorted(D["barang"], key=lambda x: x["nama"].lower())
    by_id = {b["id"]: b for b in barang}
    with st.container(key="kartu_harga"):
        pilih = st.selectbox("Barang", [b["id"] for b in barang], key="rh_pilih",
                             format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
        b = by_id[pilih]
        s = ringkas(b)
        if s:
            a, c = st.columns(2)
            a.metric("Terakhir dibeli", rp(_int(s["terakhir"]["harga"])),
                     help=(s["terakhir"].get("toko") or "") + (" · " + fmt_iso(s["terakhir"]["tgl"])
                                                               if s["terakhir"].get("tgl") else ""))
            c.metric("Termurah", rp(_int(s["termurah"]["harga"])))
            a, c = st.columns(2)
            a.metric("Rata-rata", rp(s["rata"]))
            c.metric("Tertinggi", rp(s["tertinggi"]))
            m = s["termurah"]
            detail = " · ".join(x for x in [m.get("toko"), fmt_iso(m["tgl"]) if m.get("tgl") else ""] if x)
            if detail:
                st.caption(f"Termurah: {detail}")
            if s["tren"]:
                st.caption(f"Harga terakhir {s['tren']}.")
            if s["n"] >= 2:
                df = pd.DataFrame([{
                    "Tanggal": fmt_iso(x["tgl"]) if x.get("tgl") else "-",
                    "Toko": x.get("toko") or "-",
                    "Jumlah": _int(x.get("jumlah")) or 1,
                    "Harga asli": rp(_int(x["harga_asli"])) if _int(x.get("harga_asli")) else "-",
                    "Harga bayar": rp(_int(x["harga"])),
                } for x in reversed(s["daftar"])])
                st.dataframe(df, hide_index=True, width="stretch")
            else:
                st.caption("Baru satu pembelian tercatat. Catat pembelian berikutnya untuk membandingkan.")
        else:
            st.caption("Belum ada harga beli untuk barang ini.")

        with st.expander("Catat pembelian", expanded=not s):
            with st.form(f"form_rh_{versi()}_{pilih}"):
                c1, c2 = st.columns(2)
                tgl = c1.date_input("Tanggal beli", value=hari_ini(), key=f"rh_t_{pilih}")
                jml = int(c2.number_input("Jumlah", min_value=1, step=1, value=1, key=f"rh_j_{pilih}"))
                c1, c2 = st.columns(2)
                asli = int(c1.number_input("Harga asli per buah (opsional)", min_value=0, step=1000, value=0,
                                           key=f"rh_a_{pilih}"))
                bayar = int(c2.number_input("Harga bayar per buah", min_value=0, step=1000, value=0,
                                            key=f"rh_b_{pilih}"))
                toko = st.text_input("Beli di", key=f"rh_k_{pilih}")
                cat = st.text_input("Catatan (opsional)", key=f"rh_c_{pilih}")
                stok = st.checkbox("Tambahkan jumlah ini ke stok", value=True, key=f"rh_s_{pilih}")
                kirim = st.form_submit_button("Simpan pembelian", type="primary")
            if kirim:
                if bayar <= 0:
                    st.error("Isi harga bayar.")
                elif asli and bayar > asli:
                    st.error("Harga bayar tidak boleh lebih besar dari harga asli.")
                else:
                    catat_pembelian(b, tgl.isoformat(), bayar, asli, toko, jml, cat, stok)
                    selesai_simpan(f"Pembelian {b['nama']} dicatat.")

        banding = [(ringkas(x), x) for x in barang]
        banding = [(r, x) for r, x in banding if r and r["n"] >= 2]
        if banding:
            st.markdown("#### Perbandingan harga")
            st.dataframe(pd.DataFrame([{
                "Barang": x["nama"], "Pembelian": r["n"], "Terakhir": rp(_int(r["terakhir"]["harga"])),
                "Termurah": rp(_int(r["termurah"]["harga"])), "Rata-rata": rp(r["rata"]),
                "Tren": r["tren"].split(" dari")[0] or "-"} for r, x in banding]),
                hide_index=True, width="stretch")
