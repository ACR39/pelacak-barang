"""Riwayat aktivitas dan tempat sampah."""
import html

import streamlit as st

from pelacak.bantu import (
    MASA_SAMPAH, atur, catat, ikut_induk, induk_dari, kartu_barang_html, keturunan, nama_tempat,
    selesai_simpan, semua_berkas, sinkron_isi, sisa_sampah,
)
from pelacak.inti import D, fmt_waktu, hari_ini, sekarang
from pelacak.penyimpanan import hapus_foto


# --------------------------------------------------------- riwayat aktivitas
JENIS_AKT = {"tambah": ("Ditambah", "lc-h"), "ubah": ("Diubah", "lc-b"), "buang": ("Dibuang", "lc-m"),
             "pulih": ("Dipulihkan", "lc-h"), "hapus": ("Dihapus permanen", "lc-r"),
             "data": ("Data dipulihkan", "lc-r")}


def _kosong(v) -> bool:
    return v is None or v is False or v == ""


def kembalikan_perubahan(x: dict) -> tuple:
    """Kembalikan nilai lama dari satu catatan 'ubah'. Bagian yang sudah berubah lagi dilewati."""
    b = next((y for y in D["barang"] if y["id"] == x.get("barang")), None)
    if not b:
        return 0, len(x.get("perubahan", []))

    def sah(k, v) -> bool:
        if _kosong(v):
            return k != "nama"
        if k == "lokasi":
            return any(l["id"] == v for l in D["lokasi"])
        if k == "sublokasi":
            return any(l["id"] == v for l in D["sublokasi"])
        if k == "kategori":
            return any(l["id"] == v for l in D["kategori"])
        if k == "dalam":
            return v != b["id"] and v not in keturunan(b["id"]) and any(y["id"] == v for y in D["barang"])
        return True

    dari_tempat = nama_tempat(b)
    kembali = lewat = 0
    for p in x.get("perubahan", []):
        k, skrg = p["k"], b.get(p["k"])
        skrg = "" if _kosong(skrg) else skrg
        if skrg != p["ke"] or not sah(k, p["dari"]):
            lewat += 1
            continue
        if _kosong(p["dari"]):
            b.pop(k, None)
        else:
            b[k] = p["dari"]
        kembali += 1
    if kembali:
        b["diubah"] = hari_ini().isoformat()
        induk = induk_dari(b)
        if induk:
            ikut_induk(b, induk)
        elif nama_tempat(b) != dari_tempat:
            catat(b["id"], b["nama"], dari_tempat, nama_tempat(b))
        sinkron_isi(b["id"])
        x["dikembalikan"] = sekarang().strftime("%Y-%m-%d %H:%M")
    return kembali, lewat


def halaman_aktivitas():
    log = D.get("aktivitas", [])
    with st.container(key="kartu_barang"):
        if not log:
            st.info("Belum ada aktivitas. Mulai sekarang, setiap barang yang ditambah, diubah, dibuang, "
                    "atau dipulihkan tercatat di sini beserta siapa yang melakukannya.")
            return
        kc, kj = st.columns([3, 2], vertical_alignment="center")
        q = " ".join(kc.text_input("Pencarian", key="ak_q", icon=":material/search:",
                                   placeholder="Cari barang, orang, atau isi perubahan...",
                                   label_visibility="collapsed").lower().split())
        pilihan = ["Semua"] + [v[0] for v in JENIS_AKT.values()]
        jenis = kj.selectbox("Jenis", pilihan, key="ak_jenis", label_visibility="collapsed")
        hasil = sorted(log, key=lambda x: x.get("waktu", ""), reverse=True)
        if jenis != "Semua":
            kode = next(k for k, v in JENIS_AKT.items() if v[0] == jenis)
            hasil = [x for x in hasil if x.get("jenis") == kode]
        if q:
            hasil = [x for x in hasil if q in " ".join(
                [x.get("nama", ""), x.get("oleh", ""), x.get("rincian", "")]).lower()]
        n = st.session_state.get("ak_n", 40)
        st.caption(f"{len(hasil)} dari {len(log)} catatan")
        if not hasil:
            st.info("Tidak ada catatan yang cocok.")
        for x in hasil[:n]:
            lab, kls = JENIS_AKT.get(x.get("jenis"), (x.get("jenis", ""), "lc-b"))
            rin = f'<div class="ar">{html.escape(x["rincian"])}</div>' if x.get("rincian") else ""
            st.markdown(
                f'<div class="akt"><div class="ah">{html.escape(x.get("nama", ""))}'
                f'<span class="lencana {kls}">{lab}</span></div>{rin}'
                f'<div class="am">{fmt_waktu(x.get("waktu", ""))} · oleh {html.escape(x.get("oleh", ""))}'
                + (f' · sudah dikembalikan {fmt_waktu(x["dikembalikan"])}' if x.get("dikembalikan") else "")
                + '</div></div>',
                unsafe_allow_html=True)
            if (x.get("jenis") == "ubah" and x.get("perubahan") and not x.get("dikembalikan")
                    and any(y["id"] == x.get("barang") for y in D["barang"])):
                if st.button("Kembalikan perubahan ini", key=f"kpakai_kb_{x['id']}"):
                    kembali, lewat = kembalikan_perubahan(x)
                    if not kembali:
                        st.warning("Tidak bisa dikembalikan, karena nilainya sudah berubah lagi setelah itu.")
                    else:
                        selesai_simpan("Perubahan dikembalikan."
                                       + (f" {lewat} bagian dilewati karena sudah berubah lagi." if lewat else ""))
        if len(hasil) > n:
            st.button(f"Tampilkan lebih banyak ({len(hasil) - n} lagi)", key="ak_lagi",
                      on_click=atur, args=("ak_n", n + 40))


# ------------------------------------------------------------- tempat sampah
def halaman_sampah():
    lama = [s for s in D["sampah"] if sisa_sampah(s) <= 0]
    if lama:                              # bersihkan yang sudah lewat masa simpan
        fs = [p for s in lama for p in semua_berkas(s["barang"])]
        D["sampah"] = [s for s in D["sampah"] if sisa_sampah(s) > 0]
        selesai_simpan(f"{len(lama)} barang lama dibersihkan dari tempat sampah.",
                       sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p])
    ada = sorted(D["sampah"], key=lambda s: s.get("dihapus", ""), reverse=True)
    with st.container(key="kartu_barang"):
        if not ada:
            st.info(f"Tempat sampah kosong. Barang yang dibuang disimpan di sini {MASA_SAMPAH} hari "
                    "sebelum hilang permanen.")
            return
        st.caption(f"{len(ada)} barang. Setelah {MASA_SAMPAH} hari barang dihapus permanen, termasuk fotonya.")
        for s in ada:
            b = s["barang"]
            with st.container(key=f"item_s_{s['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                st.caption(f"Dibuang {fmt_waktu(s.get('dihapus', ''))} oleh {s.get('oleh', '')} · "
                           f"hilang permanen dalam {max(sisa_sampah(s), 0)} hari")
                e1, e2, _ = st.columns([1.2, 1.8, 1])
                if e1.button("Pulihkan", key=f"kpakai_sp_{s['id']}", use_container_width=True):
                    pulih = dict(b)
                    induk = next((x for x in D["barang"] if x["id"] == pulih.get("dalam")), None)
                    if induk:                 # kembali ke dalam induknya, ikut lokasi induk
                        pulih["lokasi"] = induk.get("lokasi", "")
                        if induk.get("sublokasi"):
                            pulih["sublokasi"] = induk["sublokasi"]
                        else:
                            pulih.pop("sublokasi", None)
                    else:
                        pulih.pop("dalam", None)
                    pulih["diubah"] = hari_ini().isoformat()
                    D["barang"].append(pulih)
                    D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                    catat(pulih["id"], pulih["nama"], "(tempat sampah)", nama_tempat(pulih))
                    selesai_simpan("Barang dipulihkan.")
                e2.button("Hapus permanen", key=f"khapus_sp_{s['id']}", on_click=atur,
                          args=("sp_hapus", s["id"]), use_container_width=True)
                if st.session_state.get("sp_hapus") == s["id"]:
                    st.warning(f"Hapus permanen {b['nama']}? Ini tidak bisa dibatalkan.")
                    y, n, _ = st.columns([1.3, 1, 2])
                    if y.button("Ya, hapus permanen", type="primary", key=f"spya_{s['id']}"):
                        fs = semua_berkas(b)
                        D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                        selesai_simpan("Dihapus permanen.",
                                       sesudah=(lambda fs=fs: [hapus_foto(p) for p in fs]) if fs else None, sp_hapus=None)
                    n.button("Batal", key=f"spbt_{s['id']}", on_click=atur, args=("sp_hapus", None))
        if st.session_state.get("sp_kosong"):
            st.warning("Kosongkan seluruh tempat sampah? Semua barang di dalamnya hilang permanen.")
            y, n, _ = st.columns([1.5, 1, 2])
            if y.button("Ya, kosongkan", type="primary", key="sp_kosong_ya"):
                fs = [p for s in D["sampah"] for p in semua_berkas(s["barang"])]
                D["sampah"] = []
                selesai_simpan("Tempat sampah dikosongkan.",
                               sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p], sp_kosong=False)
            n.button("Batal", key="sp_kosong_bt", on_click=atur, args=("sp_kosong", False))
        else:
            st.button("Kosongkan tempat sampah", key="sp_kosong_btn", on_click=atur, args=("sp_kosong", True))
