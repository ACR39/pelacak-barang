"""Pindah massal beserta pembatalannya."""
import html
import uuid

import streamlit as st

from pelacak.bantu import (
    atur, catat, daftar_lokasi, keturunan, lokasi_dari, nama_lok, nama_tempat, selesai_simpan,
    sinkron_isi, sub_dari,
)
from pelacak.inti import D, TANPA, fmt_waktu, hari_ini, pengguna_nama, sekarang


# -------------------------------------------------------------- pindah massal
def pindahkan_barang(pilih: list, by_id: dict, tl: str, ts: str) -> int:
    """Pindahkan barang (daftar id) ke lokasi/sub lokasi tujuan. Kembalikan jumlah yang benar-benar pindah."""
    dipindah = 0
    item = []
    for i in pilih:
        b = by_id[i]
        dari = nama_tempat(b)
        asal = {"lokasi": b.get("lokasi", ""), "sublokasi": b.get("sublokasi", ""), "dalam": b.get("dalam", ""),
                "petak": b.get("petak", "")}
        if b.get("lokasi") != tl:
            b.pop("petak", None)          # petak milik lokasi lama
        b["lokasi"] = tl
        if ts:
            b["sublokasi"] = ts
        else:
            b.pop("sublokasi", None)
        ke = nama_tempat(b)
        if dari != ke:
            b["diubah"] = hari_ini().isoformat()
            if b.get("dalam") and b["dalam"] not in pilih:
                b.pop("dalam", None)       # dipindah sendirian: keluar dari barang induknya
            catat(i, b["nama"], dari, ke)
            item.append({"id": i, "nama": b["nama"], "dari": asal})
            dipindah += 1
    for i in pilih:
        sinkron_isi(i)                      # isi barang ikut pindah bersama induknya
    if item:
        pm = D.setdefault("pindah_massal", [])
        pm.append({"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(),
                   "tujuan": {"lokasi": tl, "sublokasi": ts or ""}, "tujuan_nama": nama_tempat(by_id[item[0]["id"]]),
                   "item": item})
        D["pindah_massal"] = pm[-10:]
    return dipindah


def batalkan_pindah(batch: dict) -> tuple:
    """Kembalikan barang dari satu pindah massal ke tempat asalnya. Barang yang sudah dipindah lagi dilewati."""
    by = {b["id"]: b for b in D["barang"]}
    tujuan = batch["tujuan"]
    kembali = lewat = 0
    ids = []
    for it in batch["item"]:
        b = by.get(it["id"])
        d = it["dari"]
        if (not b or b.get("lokasi") != tujuan["lokasi"] or (b.get("sublokasi") or "") != tujuan["sublokasi"]
                or not any(l["id"] == d["lokasi"] for l in D["lokasi"])):
            lewat += 1
            continue
        dari = nama_tempat(b)
        b["lokasi"] = d["lokasi"]
        if d.get("petak"):
            b["petak"] = d["petak"]
        else:
            b.pop("petak", None)
        if d["sublokasi"] and any(s["id"] == d["sublokasi"] and s["lokasi"] == d["lokasi"] for s in D["sublokasi"]):
            b["sublokasi"] = d["sublokasi"]
        else:
            b.pop("sublokasi", None)
        if d["dalam"] and d["dalam"] in by and d["dalam"] != b["id"] and d["dalam"] not in keturunan(b["id"]):
            b["dalam"] = d["dalam"]
        b["diubah"] = hari_ini().isoformat()
        if dari != nama_tempat(b):
            catat(b["id"], b["nama"], dari, nama_tempat(b))
        ids.append(b["id"])
        kembali += 1
    for i in ids:
        sinkron_isi(i)
    if kembali:
        batch["dibatalkan"] = sekarang().strftime("%Y-%m-%d %H:%M")
    return kembali, lewat


def panel_batal_pindah():
    riw = D.get("pindah_massal", [])
    if not riw:
        return
    with st.expander(f"Pindah massal terakhir ({min(len(riw), 5)})"):
        for x in reversed(riw[-5:]):
            nama = ", ".join(i["nama"] for i in x["item"][:6]) + (f" dan {len(x['item']) - 6} lainnya" if len(x["item"]) > 6 else "")
            tanda = ('<span class="lencana lc-h">Sudah dibatalkan</span>' if x.get("dibatalkan") else "")
            st.markdown(f'<div class="akt"><div class="ah">{len(x["item"])} barang → {html.escape(x.get("tujuan_nama", ""))}{tanda}</div>'
                        f'<div class="ar">{html.escape(nama)}</div>'
                        f'<div class="am">{fmt_waktu(x.get("waktu", ""))} · oleh {html.escape(x.get("oleh", ""))}'
                        + (f' · dibatalkan {fmt_waktu(x["dibatalkan"])}' if x.get("dibatalkan") else "") + '</div></div>',
                        unsafe_allow_html=True)
            if x.get("dibatalkan"):
                continue
            if st.session_state.get("pm_batal") == x["id"]:
                st.warning("Kembalikan semua barang ini ke tempat asalnya? Barang yang sudah dipindah lagi setelah itu dilewati.")
                y, n, _ = st.columns([1.3, 1, 1.4])
                if y.button("Ya, batalkan", type="primary", key=f"pmby_{x['id']}"):
                    kembali, lewat = batalkan_pindah(x)
                    if not kembali:
                        st.warning("Tidak ada yang bisa dikembalikan, karena semua barangnya sudah dipindah lagi atau dihapus.")
                    else:
                        selesai_simpan(f"{kembali} barang dikembalikan." + (f" {lewat} dilewati." if lewat else ""),
                                       pm_batal=None)
                n.button("Tidak", key=f"pmbt_{x['id']}", on_click=atur, args=("pm_batal", None))
            else:
                st.button("Batalkan pindah ini", key=f"kpakai_pmb_{x['id']}", on_click=atur, args=("pm_batal", x["id"]))


def pilih_tujuan(pl: dict):
    """Dua pilihan tujuan (lokasi dan sub lokasi). Kembalikan (id lokasi, id sub lokasi atau kosong)."""
    if st.session_state.get("pm_lok") not in pl:
        st.session_state.pm_lok = next(iter(pl))
    d1, d2 = st.columns(2)
    tl = d1.selectbox("Lokasi tujuan", list(pl), key="pm_lok", format_func=lambda i: pl[i])
    psub = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == tl}
    ops = [""] + list(psub)
    if st.session_state.get("pm_sub") not in ops:
        st.session_state.pm_sub = ""
    ts = d2.selectbox("Sub lokasi tujuan (boleh kosong)", ops, key="pm_sub",
                      format_func=lambda i: "Tanpa sub lokasi" if not i else psub[i])
    return tl, ts


def halaman_pindah():
    panel_batal_pindah()
    if not D["barang"]:
        st.info("Belum ada barang.")
        return
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di Pengaturan > Lokasi.")
        return
    if st.session_state.pop("pm_reset", False):
        st.session_state.pm_pilih = []
    by_id = {b["id"]: b for b in D["barang"]}
    urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    st.session_state.pm_pilih = [i for i in st.session_state.get("pm_pilih", []) if i in by_id]
    with st.container(key="kartu_barang"):
        cara = st.segmented_control("Cara memindahkan", ["Pilih barang", "Seluruh isi lokasi"], default="Pilih barang",
                                    key="pm_cara", label_visibility="collapsed") or "Pilih barang"
        if cara == "Seluruh isi lokasi":
            st.markdown("#### 1. Pilih isi yang dipindahkan")
            if st.session_state.get("pm_src_lok") not in pl:
                st.session_state.pm_src_lok = next(iter(pl))
            sl = st.selectbox("Pindahkan semua isi dari lokasi", list(pl), key="pm_src_lok",
                              format_func=lambda i: pl[i])
            ssub = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == sl}
            ops_s = ["semua", "langsung"] + list(ssub)
            if st.session_state.get("pm_src_sub") not in ops_s:
                st.session_state.pm_src_sub = "semua"
            ss = st.selectbox("Bagian lokasi", ops_s, key="pm_src_sub",
                              format_func=lambda i: "Seluruh lokasi, termasuk semua sub lokasi" if i == "semua"
                              else "Hanya yang langsung di lokasi (tanpa sub lokasi)" if i == "langsung" else ssub[i])
            if ss == "semua":
                isi = [b for b in urut if b.get("lokasi") == sl]
            elif ss == "langsung":
                isi = [b for b in urut if b.get("lokasi") == sl and sub_dari(b) is None]
            else:
                isi = [b for b in urut if b.get("lokasi") == sl and b.get("sublokasi") == ss]
            st.caption(f"{len(isi)} barang akan ikut dipindahkan.")
            if isi:
                st.markdown("<br>".join(html.escape(f"• {b['nama']} ({nama_tempat(b)})") for b in isi[:12])
                            + (f"<br>…dan {len(isi) - 12} lainnya" if len(isi) > 12 else ""), unsafe_allow_html=True)
            st.markdown("#### 2. Pilih tujuan")
            tl, ts = pilih_tujuan(pl)
            sama = ss != "semua" and sl == tl and ss == (ts or "langsung")
            if isi and sama:
                st.info("Asal dan tujuannya sama, jadi tidak ada yang perlu dipindah.")
            if st.button(f"Pindahkan {len(isi)} barang", type="primary", disabled=not isi or sama, key="pm_go_isi"):
                dipindah = pindahkan_barang([b["id"] for b in isi], by_id, tl, ts)
                if not dipindah:
                    st.info("Semua barang sudah berada di tujuan itu.")
                else:
                    selesai_simpan(f"{dipindah} barang dipindahkan ke {pl[tl]}.", pm_reset=True)
            return
        st.markdown("#### 1. Pilih barang")
        c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
        asal = c1.selectbox("Pilih cepat: semua barang dari", ["semua"] + list(pl) + ["tanpa"], key="pm_asal",
                            format_func=lambda i: ("Semua lokasi" if i == "semua" else TANPA if i == "tanpa" else pl[i]))

        def cocok(b):
            return (asal == "semua" or (asal == "tanpa" and lokasi_dari(b) is None) or b.get("lokasi") == asal)

        c2.button("Pilih semuanya", key="pm_semua", on_click=atur,
                  args=("pm_pilih", [b["id"] for b in urut if cocok(b)]))
        pilih = st.multiselect("Barang yang dipindahkan", [b["id"] for b in urut], key="pm_pilih",
                               format_func=lambda i: f'{by_id[i]["nama"]} — {nama_tempat(by_id[i])}',
                               placeholder="Ketik untuk mencari barang...")
        st.markdown("#### 2. Pilih tujuan")
        tl, ts = pilih_tujuan(pl)
        if st.button(f"Pindahkan {len(pilih)} barang", type="primary", disabled=not pilih, key="pm_go"):
            dipindah = pindahkan_barang(list(pilih), by_id, tl, ts)
            if not dipindah:
                st.info("Semua barang yang dipilih sudah berada di tujuan itu.")
            else:
                selesai_simpan(f"{dipindah} barang dipindahkan.", pm_reset=True)
