"""Riwayat perpindahan dan Jelajah lokasi."""
import html

import streamlit as st

from pelacak.bantu import (
    daftar_lokasi, induk_dari, isi_dari, jumlah_b, lencana, nama_lok, saring_barang, sub_dari,
)
from pelacak.inti import D, TANPA, TGL_MAX, TGL_MIN, fmt_waktu


# ------------------------------------------------------------------- riwayat
def halaman_riwayat():
    r = D["riwayat"]
    with st.container(key="kartu_tabel"):
        if not r:
            st.info("Belum ada perpindahan. Riwayat tercatat otomatis saat barang ditambah, "
                    "lokasinya diubah, atau dipindah massal.")
            return
        q = " ".join(st.text_input("Pencarian", key="rw_q", icon=":material/search:",
                                   placeholder="Cari nama barang atau lokasi...",
                                   label_visibility="collapsed").lower().split())
        d1, d2 = st.columns(2)
        t_dari = d1.date_input("Dari tanggal (boleh kosong)", value=None, key="rw_dari",
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        t_sampai = d2.date_input("Sampai tanggal (boleh kosong)", value=None, key="rw_sampai",
                                 min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        hasil = sorted(r, key=lambda x: x.get("waktu", ""), reverse=True)
        if q:
            hasil = [x for x in hasil if q in " ".join(
                [x.get("nama", ""), x.get("dari", ""), x.get("ke", "")]).lower()]
        if t_dari and t_sampai and t_dari > t_sampai:
            st.warning("Tanggal awal lebih besar dari tanggal akhir, jadi tidak ada yang cocok.")
        if t_dari:
            hasil = [x for x in hasil if x.get("waktu", "")[:10] >= t_dari.isoformat()]
        if t_sampai:
            hasil = [x for x in hasil if x.get("waktu", "")[:10] <= t_sampai.isoformat()]
        st.caption(f"{len(hasil)} dari {len(r)} catatan" + (" (200 terbaru ditampilkan)" if len(hasil) > 200 else ""))
        lebar = [2.2, 3.5, 3.5, 3.5, 1.6]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Waktu", "Barang", "Dari", "Ke", "Oleh"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for x in hasil[:200]:
            k = st.columns(lebar, vertical_alignment="center")
            k[0].write(fmt_waktu(x.get("waktu", "")))
            k[1].markdown(f'<div class="brg">{html.escape(x.get("nama", ""))}</div>', unsafe_allow_html=True)
            k[2].write(x.get("dari") or "(barang baru)")
            k[3].write(x.get("ke") or "—")
            k[4].write(x.get("oleh", ""))
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# ----------------------------------------------------------- jelajah lokasi
def _hitung_n(b: dict, dalam: int = 0) -> int:
    return 1 + (sum(_hitung_n(x, dalam + 1) for x in isi_dari(b["id"])) if dalam < 4 else 0)


def _html_barang(b: dict, dalam: int = 0) -> str:
    h = (f'<div class="pi" style="margin-left:{dalam * 14}px"><span class="pn">{html.escape(b["nama"])}</span>'
         f'{lencana(b)}<span class="pj">{jumlah_b(b)}</span></div>')
    if dalam < 4:
        h += "".join(_html_barang(x, dalam + 1) for x in isi_dari(b["id"]))
    return h


def _html_grup(judul: str, isi: list, buka: bool, anak: str = "", n_anak: int = 0, dalam_lok: bool = False) -> str:
    n = sum(_hitung_n(b) for b in isi) + n_anak
    badan = "".join(_html_barang(b) for b in isi) + anak
    if not badan:
        badan = '<div class="pk">Belum ada barang.</div>'
    kls = "pl" if dalam_lok else "pt"
    return (f'<details class="{kls}"{" open" if buka else ""}><summary><span>{html.escape(judul)}</span>'
            f'<span class="pc">{n} barang</span></summary><div class="pb">{badan}</div></details>')


def _html_denah(l: dict, barang: list) -> str:
    """Denah satu lokasi: satu kotak per petak, lalu kotak barang yang belum ditempatkan."""
    petak = l.get("petak", [])
    milik = [b for b in barang if b.get("lokasi") == l["id"]]

    def baris(b):
        sl = sub_dari(b)
        ket = f' <small>· {html.escape(sl["nama"])}</small>' if sl else ""
        return f'<div class="db"><span>{html.escape(b["nama"])}{ket}</span><b>{jumlah_b(b)}</b></div>'

    def kotak(judul, isi, kls=""):
        n = sum(jumlah_b(b) for b in isi)
        badan = "".join(baris(b) for b in isi) or '<div class="dk">Kosong</div>'
        kelas = (" " + kls if kls else "") + (" kosong" if not isi and not kls else "")
        return (f'<div class="dpt{kelas}"><div class="dh1"><div>{html.escape(judul)}</div>'
                f'<span>{n}</span></div>{badan}</div>')

    h = [kotak(p, [b for b in milik if b.get("petak") == p]) for p in petak]
    sisa = [b for b in milik if b.get("petak") not in petak]
    if sisa or not petak:
        h.append(kotak("Belum ditempatkan" if petak else "Isi lokasi", sisa, "lain"))
    return f'<div class="denah">{"".join(h)}</div>'


def _tampil_denah(atas: list, q: str):
    lok = sorted(daftar_lokasi(), key=lambda l: (not l.get("petak"), nama_lok(l).lower()))
    if not lok:
        st.info("Belum ada lokasi. Buat dulu di Pengaturan > Tempat dan lokasi.")
        return
    peta = {l["id"]: l for l in lok}
    if st.session_state.get("jl_lok") not in peta:
        st.session_state.jl_lok = lok[0]["id"]
    pid = st.selectbox("Lokasi", list(peta), key="jl_lok",
                       format_func=lambda i: nama_lok(peta[i]) + (f" · {len(peta[i]['petak'])} petak" if peta[i].get("petak") else ""))
    l = peta[pid]
    if not l.get("petak"):
        st.caption("Lokasi ini belum punya petak, jadi semua isinya ada di satu kotak. "
                   "Tambahkan petak lewat Pengaturan > Tempat dan lokasi > Lokasi > Ubah.")
    elif q:
        st.caption("Hanya barang yang cocok dengan pencarian yang tampil di denah.")
    st.markdown(_html_denah(l, atas), unsafe_allow_html=True)


def halaman_jelajah():
    atas = [b for b in D["barang"] if not induk_dari(b)]      # isi barang ditampilkan di bawah induknya
    with st.container(key="kartu_barang"):
        kq, kb = st.columns([3, 2], vertical_alignment="center")
        q = " ".join(kq.text_input("Pencarian", key="jl_q", icon=":material/search:",
                                   placeholder="Cari barang di semua lokasi...",
                                   label_visibility="collapsed").lower().split())
        mode = st.segmented_control("Tampilan", ["Daftar", "Denah"], default="Daftar", key="jl_mode",
                                    label_visibility="collapsed") or "Daftar"
        buka_semua = kb.toggle("Buka semua", key="jl_buka", disabled=mode == "Denah")
        if q:
            atas, _mirip_n = saring_barang(atas, q)
        if mode == "Denah":
            _tampil_denah(atas, q)
            return
        buka = bool(q) or buka_semua
        if not D["tempat"] and not D["lokasi"]:
            st.info("Belum ada tempat atau lokasi. Buat dulu di menu Pengaturan.")
            return
        bagian = []

        def blok_lokasi(l: dict) -> str:
            milik = [b for b in atas if b.get("lokasi") == l["id"]]
            langsung = [b for b in milik if sub_dari(b) is None]
            anak, n_anak = "", 0
            for sl in sorted((x for x in D["sublokasi"] if x["lokasi"] == l["id"]), key=lambda x: x["nama"].lower()):
                ang = [b for b in milik if b.get("sublokasi") == sl["id"]]
                if q and not ang:
                    continue
                anak += _html_grup(sl["nama"], ang, buka, dalam_lok=True)
                n_anak += sum(_hitung_n(b) for b in ang)
            if q and not milik:
                return ""
            return _html_grup(l["nama"], langsung, buka, anak, n_anak, dalam_lok=True)

        id_tempat = {t["id"] for t in D["tempat"]}
        for t in sorted(D["tempat"], key=lambda t: t["nama"].lower()):
            lok = sorted((l for l in D["lokasi"] if l.get("tempat") == t["id"]), key=lambda l: l["nama"].lower())
            isi_l = "".join(blok_lokasi(l) for l in lok)
            if q and not isi_l:
                continue
            n = sum(_hitung_n(b) for b in atas if b.get("lokasi") in {l["id"] for l in lok})
            bagian.append(f'<details class="pt"{" open" if buka else ""}><summary><span>{html.escape(t["nama"])}</span>'
                          f'<span class="pc">{n} barang</span></summary><div class="pb">'
                          f'{isi_l or "<div class=pk>Belum ada lokasi di tempat ini.</div>"}</div></details>')
        lok_lain = [l for l in D["lokasi"] if l.get("tempat") not in id_tempat]
        isi_lain = "".join(blok_lokasi(l) for l in sorted(lok_lain, key=lambda l: l["nama"].lower()))
        if isi_lain:
            bagian.append(f'<details class="pt"{" open" if buka else ""}><summary><span>Tanpa tempat</span></summary>'
                          f'<div class="pb">{isi_lain}</div></details>')
        id_lok = {l["id"] for l in D["lokasi"]}
        tanpa = [b for b in atas if b.get("lokasi") not in id_lok]
        if tanpa:
            bagian.append(_html_grup(TANPA, tanpa, buka))
        total = sum(_hitung_n(b) for b in atas)
        st.caption(f"{total} barang" + (" cocok dengan pencarian" if q else " di semua lokasi")
                   + ". Sentuh nama tempat atau lokasi untuk membuka isinya.")
        if not bagian:
            st.info("Tidak ada barang yang cocok.")
        else:
            st.markdown(f'<div class="pohon">{"".join(bagian)}</div>', unsafe_allow_html=True)
