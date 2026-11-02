"""Stok menipis, rencana beli, dan daftar bawaan (paket)."""
import html
import uuid

import streamlit as st

from pelacak.bantu import (
    ada_kembar, atur, harga_b, idx, jumlah_b, kartu_barang_html, minimum_b, nama_tempat,
    perlu_beli, selesai_simpan, versi,
)
from pelacak.barang import kembalikan_dibawa, tandai_dibawa
from pelacak.inti import D, fmt_iso, hari_ini, rp


# ----------------------------------------------------------------- perlu beli
def halaman_beli():
    by_id = {b["id"]: b for b in D["barang"]}
    perlu = sorted([b for b in D["barang"] if perlu_beli(b)], key=lambda x: x["nama"].lower())
    lain = sorted([b for b in D["barang"] if not perlu_beli(b)], key=lambda x: x["nama"].lower())
    with st.container(key="kartu_barang"):
        if st.session_state.get("bl_mode") and lain:
            st.markdown("#### Tandai barang yang habis")
            with st.form(f"form_beli_{versi()}"):
                pilih = st.selectbox("Barang", [b["id"] for b in lain],
                                     format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                t1, t2, _ = st.columns([1.6, 1, 2])
                kirim = t1.form_submit_button("Tandai perlu beli", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.bl_mode = False
                st.rerun()
            if kirim:
                by_id[pilih]["habis"] = True
                by_id[pilih]["diubah"] = hari_ini().isoformat()
                selesai_simpan("Ditandai perlu beli.", bl_mode=False)
            return
        if lain:
            st.button("Tandai habis", type="primary", key="bl_tambah", icon=":material/add:",
                      on_click=atur, args=("bl_mode", True),
                      help="Tandai barang yang sudah habis supaya masuk daftar belanja")
        st.markdown(f"#### Stok menipis atau habis ({len(perlu)})")
        if not perlu:
            st.caption("Tidak ada barang yang perlu dibeli.")
            return
        total = 0
        for b in perlu:
            m = minimum_b(b)
            with st.container(key=f"item_b_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                c1, c2 = st.columns([1, 1.6], vertical_alignment="bottom")
                n_beli = int(c1.number_input("Jumlah beli", min_value=1, step=1, key=f"bl_n_{b['id']}",
                                             value=max(m - jumlah_b(b) + 1, 1) if m else 1))
                total += harga_b(b) * n_beli
                if c2.button("Sudah dibeli", key=f"kpakai_bl_{b['id']}", icon=":material/check:", use_container_width=True):
                    b.pop("habis", None)
                    b["jumlah"] = jumlah_b(b) + n_beli
                    b["dibeli"] = hari_ini().isoformat()
                    b["diubah"] = hari_ini().isoformat()
                    selesai_simpan("Stok ditambah dan dicoret dari daftar belanja.")
        st.caption(f"Perkiraan total: {rp(total)} (harga beli terakhir × jumlah yang dibeli).")
        teks = "\n".join(f"- {b['nama']} ({nama_tempat(b)})" + (f" ± {rp(harga_b(b))}" if harga_b(b) else "")
                         for b in perlu)
        st.download_button("Unduh daftar belanja (.txt)", teks, file_name="daftar-belanja.txt", mime="text/plain")


# ------------------------------------------------------- kedaluwarsa & garansi
# ------------------------------------------------------------- rencana beli
PRIORITAS = ["Tinggi", "Sedang", "Rendah"]


LC_PRIORITAS = {"Tinggi": "lc-r", "Sedang": "lc-m", "Rendah": "lc-b"}


def _hapus_rencana(x):
    if st.session_state.get("rc_hapus") == x["id"]:
        st.warning(f"Hapus rencana {x['nama']}?")
        y, n, _ = st.columns([1, 1, 4])
        if y.button("Ya, hapus", type="primary", key=f"rcya_{x['id']}"):
            D["rencana"] = [r for r in D["rencana"] if r["id"] != x["id"]]
            selesai_simpan("Dihapus.", rc_hapus=None)
        n.button("Batal", key=f"rcbt_{x['id']}", on_click=atur, args=("rc_hapus", None))


def kartu_rencana_html(x: dict) -> str:
    """Kartu satu rencana beli: huruf awal, nama + prioritas, keterangan, jumlah besar di kanan."""
    pri = x.get("prioritas") if x.get("prioritas") in PRIORITAS else "Sedang"
    jml = int(x.get("jumlah", 1) or 1)
    harga = int(x.get("harga", 0) or 0)
    meta = []
    if harga:
        meta.append(f"{rp(harga)} per buah")
        if jml > 1:
            meta.append(f"total {rp(harga * jml)}")
    mt = f'<div class="mt">{html.escape(" • ".join(meta))}</div>' if meta else ""
    cat = f'<div class="cat">{html.escape(x["catatan"])}</div>' if x.get("catatan") else ""
    ic = html.escape((x["nama"].strip()[:1] or "?").upper())
    return (f'<div class="itm"><div class="ic">{ic}</div><div class="isi"><div class="jd">{html.escape(x["nama"])}'
            f'<span class="lencana {LC_PRIORITAS[pri]}">{pri}</span></div>{mt}{cat}</div>'
            f'<div class="qt"><b>{jml}</b><span>buah</span></div></div>')


def halaman_rencana():
    aktif = [x for x in D["rencana"] if not x.get("dibeli")]
    selesai = [x for x in D["rencana"] if x.get("dibeli")]
    mode = st.session_state.get("rc_mode")          # None (daftar), "baru", atau id rencana
    e = next((x for x in aktif if x["id"] == mode), {})
    if mode not in (None, "baru") and not e:
        mode = None
    with st.container(key="kartu_g_rencana"):
        if mode:
            st.markdown("#### Ubah rencana" if e else "#### Tambah rencana")
            with st.form(f"form_rc_{e.get('id', 'baru')}_{versi()}"):
                f1, f2 = st.columns([4, 1])
                nama = f1.text_input("Nama barang", value=e.get("nama", ""), placeholder="Contoh: Sepatu lari")
                jml = f2.number_input("Jumlah", min_value=1, value=int(e.get("jumlah", 1) or 1), step=1)
                g1, g2 = st.columns(2)
                harga = g1.number_input("Perkiraan harga per buah (Rp)", min_value=0, step=1000,
                                        value=int(e.get("harga", 0) or 0))
                pri = g2.selectbox("Prioritas", PRIORITAS, index=idx(PRIORITAS, e.get("prioritas", "Sedang")))
                catatan = st.text_input("Catatan atau tautan toko (boleh kosong)", value=e.get("catatan", ""))
                t1, t2, _ = st.columns([1, 1, 4])
                kirim = t1.form_submit_button("Simpan", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.rc_mode = None
                st.rerun()
            if kirim:
                nama = nama.strip()
                if not nama:
                    st.error("Nama barang wajib diisi.")
                else:
                    isi = {"nama": nama, "jumlah": int(jml), "harga": int(harga), "prioritas": pri,
                           "catatan": catatan.strip()}
                    if e:
                        e.update(isi)
                    else:
                        D["rencana"].append({"id": uuid.uuid4().hex[:8], "dibuat": hari_ini().isoformat(), **isi})
                    selesai_simpan("Rencana disimpan.", rc_mode=None)
            return

        with st.container(key="baris_cari"):
            kc, kt = st.columns([5, 2], vertical_alignment="center")
            cari = " ".join(kc.text_input("Pencarian", key="rc_cari", icon=":material/search:",
                                          placeholder="Cari nama atau catatan...",
                                          label_visibility="collapsed").lower().split())
            kt.button("Tambah", type="primary", key="rc_tambah", icon=":material/add:",
                      use_container_width=True, on_click=atur, args=("rc_mode", "baru"))
        mode_tampil = st.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                           key="tampilan", label_visibility="collapsed") or "Kartu"
        urut = sorted(aktif, key=lambda x: (PRIORITAS.index(x["prioritas"]) if x.get("prioritas") in PRIORITAS
                                            else 1, x["nama"].lower()))
        if cari:
            urut = [x for x in urut if cari in " ".join([x["nama"], x.get("catatan", "")]).lower()]
        if not aktif:
            st.write("Belum ada rencana pembelian. Tekan Tambah untuk membuat yang pertama.")
        elif not urut:
            st.info("Tidak ada rencana yang cocok dengan pencarian.")
        else:
            st.caption(f"{len(urut)} dari {len(aktif)} rencana")
        total = sum(int(x.get("harga", 0) or 0) * int(x.get("jumlah", 1) or 1) for x in urut)

        if urut and mode_tampil == "Kartu":
            for x in urut:
                with st.container(key=f"item_r_{x['id']}"):
                    st.markdown(kartu_rencana_html(x), unsafe_allow_html=True)
                    e1, e2, e3, _ = st.columns([2, 1, 1, 1])
                    if e1.button("Sudah dibeli", key=f"kpakai_rc_{x['id']}", use_container_width=True):
                        x["dibeli"] = hari_ini().isoformat()
                        selesai_simpan("Dicoret dari rencana.")
                    e2.button("Edit", key=f"kedit_rc_{x['id']}", on_click=atur, args=("rc_mode", x["id"]),
                              use_container_width=True)
                    e3.button("Hapus", key=f"khapus_rc_{x['id']}", on_click=atur, args=("rc_hapus", x["id"]),
                              use_container_width=True)
                    _hapus_rencana(x)
        elif urut:
            lebar = [4.6, 1.2, 2.6, 3.6]
            kep = st.columns(lebar, vertical_alignment="top")
            for kol, judul in zip(kep, ["Barang", "Jml", "Perkiraan", "Aksi"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for x in urut:
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                pri = x.get("prioritas") if x.get("prioritas") in PRIORITAS else "Sedang"
                cat = f'<div class="sub">{html.escape(x["catatan"])}</div>' if x.get("catatan") else ""
                k[0].markdown(f'<div class="brg">{html.escape(x["nama"])}'
                              f'<span class="lencana {LC_PRIORITAS[pri]}">{pri}</span></div>{cat}',
                              unsafe_allow_html=True)
                k[1].write(int(x.get("jumlah", 1) or 1))
                est = int(x.get("harga", 0) or 0) * int(x.get("jumlah", 1) or 1)
                k[2].write(rp(est) if est else "—")
                a1, a2, a3 = k[3].columns([4, 1.2, 1.2])
                if a1.button("Sudah dibeli", key=f"rcbeli_{x['id']}"):
                    x["dibeli"] = hari_ini().isoformat()
                    selesai_simpan("Dicoret dari rencana.")
                a2.button("✏️", key=f"rcedit_{x['id']}", help="Ubah", on_click=atur, args=("rc_mode", x["id"]))
                a3.button("🗑️", key=f"rchapus_{x['id']}", help="Hapus", on_click=atur, args=("rc_hapus", x["id"]))
                _hapus_rencana(x)
        if urut:
            st.caption(f"Perkiraan total: {rp(total)}")
            teks = "\n".join(f"- {x['nama']} x{int(x.get('jumlah', 1) or 1)} ({x.get('prioritas', 'Sedang')})"
                             for x in urut)
            st.download_button("Unduh daftar rencana (.txt)", teks, file_name="rencana-beli.txt", mime="text/plain")
        with st.expander(f"Sudah dibeli ({len(selesai)})"):
            if not selesai:
                st.caption("Belum ada.")
            for x in sorted(selesai, key=lambda r: r.get("dibeli", ""), reverse=True):
                k = st.columns([4, 2.4, 1.2], vertical_alignment="center")
                k[0].write(x["nama"])
                k[1].write(fmt_iso(x.get("dibeli", "")))
                k[2].button("🗑️", key=f"rchapus2_{x['id']}", help="Hapus", on_click=atur, args=("rc_hapus", x["id"]))
                _hapus_rencana(x)


# -------------------------------------------------------------------- belanja
def halaman_belanja():
    """Satu menu belanja: stok yang menipis (otomatis) dan rencana barang baru."""
    t1, t2 = st.tabs(["Stok menipis", "Barang baru"])
    with t1:
        halaman_beli()
    with t2:
        halaman_rencana()


# -------------------------------------------------------------- daftar bawaan
def halaman_paket():
    by_id = {b["id"]: b for b in D["barang"]}
    if st.session_state.get("pk_baru"):
        st.session_state.pk_pilih = st.session_state.pop("pk_baru")
    with st.container(key="kartu_barang"):
        ids = [p["id"] for p in D["paket"]]
        nm = {p["id"]: p["nama"] for p in D["paket"]}
        if ids:
            if st.session_state.get("pk_pilih") not in ids:
                st.session_state.pk_pilih = ids[0]
            pid = st.selectbox("Daftar bawaan", ids, key="pk_pilih", format_func=lambda i: nm[i])
        else:
            pid = None
            st.info('Belum ada daftar bawaan. Buat dulu di bawah, misalnya "Liburan" atau "Pindah kos".')
        with st.expander("Buat daftar baru", expanded=not ids):
            with st.form(f"form_pk_baru_{versi()}"):
                nama_baru = st.text_input("Nama daftar", placeholder="Contoh: Pulang kampung")
                kirim = st.form_submit_button("Buat daftar")
            if kirim:
                nama_baru = nama_baru.strip()
                if not nama_baru:
                    st.error("Nama daftar wajib diisi.")
                elif ada_kembar([p["nama"] for p in D["paket"]] + [nama_baru]):
                    st.error("Nama itu sudah ada.")
                else:
                    baru = {"id": uuid.uuid4().hex[:8], "nama": nama_baru, "isi": []}
                    D["paket"].append(baru)
                    selesai_simpan("Daftar dibuat.", pk_baru=baru["id"])
        if not pid:
            return
        p = next(x for x in D["paket"] if x["id"] == pid)
        isi = p.setdefault("isi", [])
        slot = st.empty()
        t_siap, t_bawa, t_isi, t_atur = st.tabs(["Siapkan", "Bawa", "Isi daftar", "Atur"])

        with t_siap:
            if not isi:
                st.info('Daftar ini masih kosong. Buka tab "Isi daftar" untuk menambah barang.')
            else:
                st.caption("Centang barang yang sudah masuk tas, lalu tekan Simpan.")
            centang = {}
            for it in isi:
                kb = by_id.get(it.get("barang"))
                label = f"{it['nama']} ×{it.get('jumlah', 1)}" + (f" — {nama_tempat(kb)}" if kb else "")
                centang[it["id"]] = st.checkbox(label, value=bool(it.get("siap")), key=f"pkc_{it['id']}_{versi()}")
            if isi:
                siap = sum(1 for v in centang.values() if v)
                slot.progress(siap / len(isi), text=f"{siap} dari {len(isi)} sudah disiapkan")
                b1, b2 = st.columns(2)
                if b1.button("Simpan centang", type="primary", key="pk_simpan"):
                    for it in isi:
                        it["siap"] = bool(centang[it["id"]])
                    selesai_simpan("Centang disimpan.")
                if b2.button("Hapus semua centang", key="pk_reset"):
                    for it in isi:
                        it["siap"] = False
                    selesai_simpan("Semua centang dihapus.")

        with t_bawa:
            terkait = [by_id[i["barang"]] for i in isi if i.get("barang") in by_id and not by_id[i["barang"]].get("hilang")]
            if not terkait:
                st.info("Belum ada barang dari daftar barang di sini. Tambahkan lewat tab \"Isi daftar\".")
            else:
                sedang = [b for b in terkait if b.get("dibawa")]
                st.caption(f"{len(sedang)} dari {len(terkait)} barang sedang dibawa. "
                           "Barang akan ditandai \"Sedang dibawa\" di menu Dibawa, hilang, rusak.")
                ke = st.text_input("Dibawa ke mana? (boleh kosong)", value=p["nama"], key=f"pk_ke_{p['id']}_{versi()}")
                c1, c2 = st.columns(2)
                if c1.button("Bawa semua", type="primary", key="pk_bawa"):
                    for b in terkait:
                        if not b.get("dibawa"):
                            tandai_dibawa(b, ke.strip())
                    selesai_simpan(f"{len(terkait)} barang ditandai sedang dibawa.")
                if c2.button("Kembalikan semua", key="pk_balik", disabled=not sedang):
                    for b in sedang:
                        kembalikan_dibawa(b)
                    selesai_simpan("Semua barang di daftar ini sudah dikembalikan.")
                if len(terkait) < len(isi):
                    st.caption("Item yang diketik manual atau sedang hilang dilewati.")

        with t_isi:
            with st.form(f"form_pk_item_{p['id']}_{versi()}"):
                urut = [b["id"] for b in sorted(D["barang"], key=lambda x: x["nama"].lower())]
                pil = st.multiselect("Pilih dari daftar barang", urut,
                                     format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                manual = st.text_input("Atau ketik nama barang (boleh kosong)")
                jml = st.number_input("Jumlah (untuk barang yang diketik)", min_value=1, value=1, step=1)
                tambah = st.form_submit_button("Tambahkan", type="primary")
            if tambah:
                ada = {i.get("barang") for i in isi if i.get("barang")}
                n0 = len(isi)
                for bid in pil:
                    if bid not in ada:
                        isi.append({"id": uuid.uuid4().hex[:8], "nama": by_id[bid]["nama"], "barang": bid,
                                    "jumlah": 1, "siap": False})
                if manual.strip():
                    isi.append({"id": uuid.uuid4().hex[:8], "nama": manual.strip(), "barang": "",
                                "jumlah": int(jml), "siap": False})
                if len(isi) == n0:
                    st.error("Pilih barang atau ketik namanya dulu.")
                else:
                    selesai_simpan("Ditambahkan ke daftar.")
            if isi:
                st.markdown("**Hapus dari daftar**")
                with st.form(f"form_pk_hapus_{p['id']}_{versi()}"):
                    peta = {i["id"]: i["nama"] for i in isi}
                    hp = st.multiselect("Pilih yang dihapus", list(peta), format_func=lambda i: peta[i])
                    hapus = st.form_submit_button("Hapus terpilih")
                if hapus and hp:
                    p["isi"] = [i for i in isi if i["id"] not in hp]
                    selesai_simpan("Dihapus dari daftar.")

        with t_atur:
            if st.session_state.get("pk_hapus") == p["id"]:
                st.warning(f"Hapus daftar {p['nama']}?")
                y, n, _ = st.columns([1, 1, 3])
                if y.button("Ya, hapus", type="primary", key="pk_ya"):
                    D["paket"] = [x for x in D["paket"] if x["id"] != p["id"]]
                    selesai_simpan("Daftar dihapus.", pk_hapus=None)
                n.button("Batal", key="pk_bt", on_click=atur, args=("pk_hapus", None))
            else:
                st.caption("Menghapus daftar tidak menghapus barangnya.")
                st.button("Hapus daftar ini", key="pk_hp", on_click=atur, args=("pk_hapus", p["id"]))
