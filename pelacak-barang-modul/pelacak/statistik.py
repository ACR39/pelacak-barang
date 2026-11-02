"""Statistik sederhana."""
import html

import pandas as pd
import streamlit as st

from pelacak.bantu import (
    daftar_pemilik, harga_b, jumlah_b, lokasi_dari, nama_lokasi, nama_tempat, semua_foto,
)
from pelacak.inti import D, hari_ini, rp


# ------------------------------------------------------------------ statistik
def _baris_stat(judul: str, ket: str) -> str:
    return (f'<div class="perhatian"><div class="brg">{html.escape(judul)}</div>'
            f'<div class="sub">{ket}</div></div>')


def halaman_statistik():
    brg = D["barang"]
    if not brg:
        st.info("Belum ada barang, jadi belum ada yang bisa dihitung.")
        return
    pindah = [x for x in D["riwayat"] if x.get("dari")]
    with st.container(key="kartu_g_s2"):
        st.markdown("**Barang yang paling sering pindah**")
        hitung = {}
        for x in pindah:
            kunci = x.get("barang") or x.get("nama", "")
            hitung[kunci] = hitung.get(kunci, [0, x.get("nama", "")])
            hitung[kunci][0] += 1
        st.caption(f"{len(pindah)} perpindahan tercatat" if pindah else "Belum ada barang yang pernah dipindah.")
        by = {b["id"]: b for b in brg}
        for kunci, (n, nama) in sorted(hitung.items(), key=lambda kv: -kv[1][0])[:8]:
            b = by.get(kunci)
            st.markdown(_baris_stat(b["nama"] if b else nama,
                                    f"{n} kali pindah" + (f" · sekarang di {html.escape(nama_tempat(b))}" if b else " · sudah dihapus")),
                        unsafe_allow_html=True)

    with st.container(key="kartu_g_s3"):
        st.markdown("**Jumlah buah per lokasi**")
        per = {}
        for b in brg:
            p = per.setdefault(nama_lokasi(b), [0, 0])
            p[0] += 1
            p[1] += jumlah_b(b)
        top = sorted(per.items(), key=lambda kv: -kv[1][1])[:10]
        st.bar_chart(pd.DataFrame({"Lokasi": [k for k, _ in top], "Jumlah buah": [v[1] for _, v in top]}),
                     x="Lokasi", y="Jumlah buah", horizontal=True, sort="-Jumlah buah", color="#2b7a57",
                     height=max(160, 38 * len(top)))
        st.caption(f"Total {sum(v[1] for v in per.values())} buah di {len(per)} lokasi. "
                   "Jumlah jenis barang per lokasi ada di grafik Beranda.")

    with st.container(key="kartu_g_s5"):
        st.markdown("**Aktivitas 6 bulan terakhir**")
        h = hari_ini()
        bulan = []
        for i in range(5, -1, -1):
            y, m = h.year, h.month - i
            while m <= 0:
                y, m = y - 1, m + 12
            bulan.append(f"{y}-{m:02d}")
        cacah = {b: 0 for b in bulan}
        orang = {}
        for x in D["aktivitas"]:
            if x.get("waktu", "")[:7] in cacah:
                cacah[x["waktu"][:7]] += 1
            orang[x.get("oleh", "")] = orang.get(x.get("oleh", ""), 0) + 1
        st.caption(f"{len(D['aktivitas'])} aktivitas tercatat seluruhnya.")
        if not any(cacah.values()):
            st.caption("Belum ada aktivitas dalam 6 bulan terakhir.")
        else:
            st.bar_chart(pd.DataFrame({"Bulan": list(cacah), "Aktivitas": list(cacah.values())}),
                         x="Bulan", y="Aktivitas", color="#2f5d9e", height=220)
        if orang:
            st.caption("Paling aktif: " + ", ".join(f"{k} ({v})" for k, v in sorted(orang.items(), key=lambda kv: -kv[1])[:5]))

    if daftar_pemilik():
        with st.container(key="kartu_g_s7"):
            st.markdown("**Per pemilik**")
            per = {}
            for b in brg:
                p = per.setdefault(b.get("pemilik") or "Tanpa pemilik", [0, 0, 0])
                p[0] += 1
                p[1] += jumlah_b(b)
                p[2] += harga_b(b) * max(jumlah_b(b), 0)
            for nama_p, (j, bh, nl) in sorted(per.items(), key=lambda kv: -kv[1][0]):
                st.markdown(_baris_stat(nama_p, f"{j} jenis, {bh} buah" + (f" · nilai {rp(nl)}" if nl else "")),
                            unsafe_allow_html=True)

    with st.container(key="kartu_g_s6"):
        st.markdown("**Kelengkapan data**")
        n = len(brg)
        kurang = [("Belum ada foto", sum(1 for b in brg if not semua_foto(b))),
                  ("Belum ada kategori", sum(1 for b in brg if not b.get("kategori"))),
                  ("Belum ada harga", sum(1 for b in brg if not harga_b(b))),
                  ("Belum ada lokasi", sum(1 for b in brg if lokasi_dari(b) is None)),
                  ("Belum pernah diinventarisasi", sum(1 for b in brg if not b.get("opname")))]
        st.markdown("".join(_baris_stat(lab, f"{c} dari {n} barang ({round(c * 100 / n)}%)") for lab, c in kurang),
                    unsafe_allow_html=True)
