"""Inventaris ulang (opname)."""
import html

import streamlit as st

from pelacak.bantu import (
    atur, daftar_lokasi, jumlah_b, nama_lok, nama_tempat, selesai_simpan, sub_dari, versi,
)
from pelacak.barang import tandai_hilang, tandai_ketemu
from pelacak.inti import D, fmt_iso, hari_ini


# ------------------------------------------------------------ inventaris ulang (opname)
def set_opname(ids: list, nilai: bool):
    for i in ids:
        st.session_state[f"op_ada_{i}_{versi()}"] = nilai


def terapkan_opname(r: dict):
    by = {b["id"]: b for b in D["barang"]}
    hari = hari_ini().isoformat()
    ketemu = 0
    for i, n in r["ada"]:
        b = by.get(i)
        if not b:
            continue
        if b.get("hilang"):
            tandai_ketemu(b)
            ketemu += 1
        if n != jumlah_b(b):
            b["jumlah"] = n
        b["opname"] = hari
        b["diubah"] = hari
    hilang = 0
    if r["aksi"] == "Tandai hilang":
        for i in r["tidak"]:
            b = by.get(i)
            if b and not b.get("hilang"):
                tandai_hilang(b, nama_tempat(b))
                hilang += 1
    bagian = [f"{len(r['ada'])} barang dicocokkan"]
    if ketemu:
        bagian.append(f"{ketemu} ketemu kembali")
    if hilang:
        bagian.append(f"{hilang} ditandai hilang")
    selesai_simpan("Inventaris ulang selesai: " + ", ".join(bagian) + ".", op_rencana=None)


def halaman_opname():
    if not D["lokasi"] or not D["barang"]:
        st.info("Buat lokasi dan barang dulu sebelum melakukan inventaris ulang.")
        return
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    with st.container(key="kartu_barang"):
        st.caption("Cocokkan catatan dengan keadaan sebenarnya. Pilih satu lokasi, centang barang yang benar-benar "
                   "ada di sana, dan koreksi jumlahnya kalau berbeda. Barang yang sedang dibawa tidak ikut diperiksa.")
        if st.session_state.get("op_lok") not in pl:
            st.session_state.op_lok = next(iter(pl))
        sl = st.selectbox("Lokasi yang diperiksa", list(pl), key="op_lok", format_func=lambda i: pl[i])
        ssub = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == sl}
        ops_s = ["semua", "langsung"] + list(ssub)
        if st.session_state.get("op_sub") not in ops_s:
            st.session_state.op_sub = "semua"
        ss = st.selectbox("Bagian lokasi", ops_s, key="op_sub",
                          format_func=lambda i: "Seluruh lokasi" if i == "semua"
                          else "Hanya yang langsung di lokasi (tanpa sub lokasi)" if i == "langsung" else ssub[i])
        milik = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if b.get("lokasi") == sl
                 and (ss == "semua" or (ss == "langsung" and sub_dari(b) is None) or b.get("sublokasi") == ss)]
        items = [b for b in milik if not b.get("dibawa")]
        n_bawa = len(milik) - len(items)
        if not items:
            st.info("Tidak ada barang yang perlu diperiksa di bagian ini."
                    + (f" ({n_bawa} barang sedang dibawa.)" if n_bawa else ""))
            return
        st.caption(f"{len(items)} barang untuk diperiksa" + (f", {n_bawa} sedang dibawa dilewati." if n_bawa else "."))
        terakhir = [b["opname"] for b in items if b.get("opname")]
        st.caption(("Pemeriksaan terakhir: " + fmt_iso(max(terakhir))) if terakhir else "Belum pernah diinventarisasi.")
        ids = [b["id"] for b in items]
        c1, c2 = st.columns(2)
        c1.button("Centang semua", key="op_semua", use_container_width=True, on_click=set_opname, args=(ids, True))
        c2.button("Kosongkan", key="op_kosong", use_container_width=True, on_click=set_opname, args=(ids, False))
        aksi = st.radio("Barang yang tidak dicentang", ["Tandai hilang", "Biarkan saja"], key="op_aksi",
                        horizontal=True, help="Tandai hilang memasukkannya ke menu Dibawa, hilang, rusak. "
                                              "Bisa dibatalkan lewat Riwayat (tab Aktivitas).")
        with st.form(f"form_op_{versi()}"):
            for b in items:
                k1, k2 = st.columns([4, 1.5], vertical_alignment="center")
                info = f"tercatat {jumlah_b(b)}" + (f" · terakhir diperiksa {fmt_iso(b['opname'])}" if b.get("opname") else "")
                if b.get("hilang"):
                    info += " · sebelumnya hilang"
                k1.checkbox(f"{b['nama']} ({info})", key=f"op_ada_{b['id']}_{versi()}")
                k2.number_input("Jumlah ditemukan", min_value=0, value=jumlah_b(b), step=1,
                                key=f"op_jml_{b['id']}_{versi()}", label_visibility="collapsed")
            kirim = st.form_submit_button("Lihat ringkasan", type="primary")
        sig = (sl, ss)
        if kirim:
            ada = [(b["id"], int(st.session_state.get(f"op_jml_{b['id']}_{versi()}", jumlah_b(b))))
                   for b in items if st.session_state.get(f"op_ada_{b['id']}_{versi()}")]
            if not ada and aksi == "Tandai hilang":
                st.session_state.pop("op_rencana", None)
                st.error("Belum ada barang yang dicentang. Centang yang ada, atau ubah pilihan ke Biarkan saja.")
            else:
                dicek = {i for i, _ in ada}
                st.session_state.op_rencana = {"sig": sig, "ada": ada, "aksi": aksi,
                                               "tidak": [b["id"] for b in items if b["id"] not in dicek and not b.get("hilang")]}
        r = st.session_state.get("op_rencana")
        if r and r.get("sig") != sig:
            st.session_state.pop("op_rencana", None)
            r = None
        if r:
            by = {b["id"]: b for b in D["barang"]}
            selisih = [(by[i], n) for i, n in r["ada"] if i in by and n != jumlah_b(by[i])]
            ketemu = [by[i] for i, _ in r["ada"] if i in by and by[i].get("hilang")]
            tidak = [by[i] for i in r["tidak"] if i in by]
            st.markdown("**Ringkasan**")
            st.markdown(f'<div class="perhatian"><div class="brg">Ditemukan</div><div class="sub">{len(r["ada"])} barang</div></div>',
                        unsafe_allow_html=True)
            if selisih:
                st.markdown('<div class="perhatian"><div class="brg">Jumlah dikoreksi</div><div class="sub">'
                            + "<br>".join(html.escape(f"{b['nama']}: {jumlah_b(b)} → {n}") for b, n in selisih[:10])
                            + (f"<br>…dan {len(selisih) - 10} lainnya" if len(selisih) > 10 else "") + "</div></div>",
                            unsafe_allow_html=True)
            if ketemu:
                st.markdown('<div class="perhatian"><div class="brg">Ketemu kembali</div><div class="sub">'
                            + html.escape(", ".join(b["nama"] for b in ketemu[:10])) + "</div></div>", unsafe_allow_html=True)
            if tidak:
                akibat = "akan ditandai hilang" if r["aksi"] == "Tandai hilang" else "dibiarkan"
                st.markdown(f'<div class="perhatian"><div class="brg">Tidak ditemukan ({akibat})</div><div class="sub">'
                            + html.escape(", ".join(b["nama"] for b in tidak[:10]))
                            + (f" dan {len(tidak) - 10} lainnya" if len(tidak) > 10 else "") + "</div></div>",
                            unsafe_allow_html=True)
            y, n_, _ = st.columns([1.4, 1, 1.4])
            if y.button("Terapkan", type="primary", key="op_ya"):
                terapkan_opname(r)
            n_.button("Batal", key="op_batal", on_click=atur, args=("op_rencana", None))
