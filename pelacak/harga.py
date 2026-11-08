"""Riwayat harga beli: catat tiap pembelian, lihat termurah, rata-rata, dan tren."""
import uuid
from datetime import timedelta

import pandas as pd
import streamlit as st

from pelacak.bantu import harga_asli_b, harga_b, jumlah_b, nama_kat, nama_tempat, selesai_simpan, versi
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
              "toko": b.get("toko", ""), "jumlah": max(jumlah_b(b), 1), "catatan": ""}]
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
                               "harga_asli": harga_asli_b(b), "toko": b.get("toko", ""),
                               "jumlah": max(jumlah_b(b), 1), "catatan": ""}]
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


# ------------------------------------------------------------------ pengeluaran
def semua_pembelian() -> list:
    """Semua pembelian semua barang: [(barang, entri)] termasuk barang yang harganya hanya di data utama."""
    hasil = []
    for b in D["barang"]:
        for x in riwayat_b(b):
            hasil.append((b, x))
    return hasil


def halaman_pengeluaran():
    beli = semua_pembelian()
    if not beli:
        st.info("Belum ada harga beli. Isi harga di Kelola barang atau catat pembelian di Belanja > Riwayat harga.")
        return
    tahun = sorted({(x.get("tgl") or "")[:4] for _, x in beli if (x.get("tgl") or "")[:4].isdigit()}, reverse=True)
    with st.container(key="kartu_pengeluaran"):
        pil = st.selectbox("Periode", ["Semua"] + tahun, key="pg_tahun",
                           format_func=lambda t: "Semua waktu" if t == "Semua" else f"Tahun {t}")
        pakai = [(b, x) for b, x in beli if pil == "Semua" or (x.get("tgl") or "")[:4] == pil]
        tanpa_tgl = [(b, x) for b, x in pakai if not x.get("tgl")]

        def total(x):
            return _int(x["harga"]) * (_int(x.get("jumlah")) or 1)

        jumlah_total = sum(total(x) for _, x in pakai)
        hemat = sum(max(_int(x.get("harga_asli")) - _int(x["harga"]), 0) * (_int(x.get("jumlah")) or 1)
                    for _, x in pakai if _int(x.get("harga_asli")))
        a, c = st.columns(2)
        a.metric("Total pengeluaran", rp(jumlah_total))
        c.metric("Hemat dari diskon", rp(hemat))
        st.caption(f"{len(pakai)} pembelian"
                   + (f" · {len(tanpa_tgl)} tanpa tanggal tidak masuk grafik bulanan" if tanpa_tgl else ""))

        bln = {}
        for b, x in pakai:
            k = (x.get("tgl") or "")[:7]
            if len(k) == 7:
                bln[k] = bln.get(k, 0) + total(x)
        if bln:
            st.markdown("**Per bulan**")
            urut = sorted(bln)
            st.bar_chart(pd.DataFrame({"Bulan": urut, "Pengeluaran": [bln[k] for k in urut]}),
                         x="Bulan", y="Pengeluaran", color="#2b7a57", height=240)

        def grup(fungsi):
            h = {}
            for b, x in pakai:
                k = fungsi(b, x) or "Tidak diisi"
                h[k] = h.get(k, 0) + total(x)
            return sorted(h.items(), key=lambda kv: -kv[1])[:10]

        for judul, fn in (("Per kategori", lambda b, x: nama_kat(b) if b.get("kategori") else ""),
                          ("Per toko", lambda b, x: (x.get("toko") or "").strip())):
            baris = grup(fn)
            st.markdown(f"**{judul}**")
            st.dataframe(pd.DataFrame([{"Nama": k, "Total": rp(v),
                                        "Porsi": f"{round(v * 100 / jumlah_total)}%" if jumlah_total else "-"}
                                       for k, v in baris]), hide_index=True, width="stretch")


# --------------------------------------------------------------- perkiraan habis
def perkiraan_habis(b: dict):
    """Perkirakan kapan stok habis dari kecepatan pembelian. None kalau datanya belum cukup.
    Pemakaian = semua yang dibeli kecuali pembelian terakhir, dibagi selang hari dari pembelian pertama
    sampai terakhir. Hasil: {"per_hari","sisa_hari","tanggal","n"}."""
    r = [x for x in riwayat_b(b) if iso_ke_date(x.get("tgl"))]
    if len(r) < 2:
        return None
    selang = (iso_ke_date(r[-1]["tgl"]) - iso_ke_date(r[0]["tgl"])).days
    terpakai = sum((_int(x.get("jumlah")) or 1) for x in r[:-1])
    if selang <= 0 or terpakai <= 0:
        return None
    per_hari = terpakai / selang
    sisa = jumlah_b(b) / per_hari
    return {"per_hari": per_hari, "sisa_hari": int(sisa), "tanggal": hari_ini() + timedelta(days=int(sisa)), "n": len(r)}


def halaman_perkiraan():
    hasil = [(perkiraan_habis(b), b) for b in D["barang"]]
    hasil = sorted([(p, b) for p, b in hasil if p], key=lambda x: x[0]["sisa_hari"])
    with st.container(key="kartu_perkiraan"):
        if not hasil:
            st.info("Belum ada barang dengan 2 pembelian bertanggal atau lebih. Catat pembelian di tab Riwayat harga, "
                    "nanti di sini muncul perkiraan kapan barang habis.")
            return
        st.caption("Perkiraan dari kecepatan beli sebelumnya dan jumlah stok sekarang. Hasilnya akurat kalau jumlah "
                   "stok selalu kamu perbarui saat barang dipakai.")
        for p, b in hasil:
            per = p["per_hari"] * 30
            status = ("sudah habis" if p["sisa_hari"] <= 0 else f"habis sekitar {fmt_iso(p['tanggal'].isoformat())}"
                      f" ({p['sisa_hari']} hari lagi)")
            ikon = "🔴" if p["sisa_hari"] <= 7 else "🟡" if p["sisa_hari"] <= 30 else "🟢"
            st.markdown(f"{ikon} **{b['nama']}** · {status}")
            st.caption(f"Stok {jumlah_b(b)} · pemakaian sekitar {per:.1f} per bulan · dari {p['n']} pembelian")
