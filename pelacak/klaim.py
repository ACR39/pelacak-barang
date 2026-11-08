"""Klaim garansi: catat barang yang sedang diklaim dan perkembangannya."""
import html
import uuid

import streamlit as st

from pelacak.bantu import nama_tempat, selesai_simpan, versi
from pelacak.inti import D, fmt_iso, hari_ini, iso_ke_date, sisa_hari

STATUS = ["Diajukan", "Diproses", "Selesai", "Ditolak"]
AKTIF = ("Diajukan", "Diproses")
IKON = {"Diajukan": "📨", "Diproses": "🛠️", "Selesai": "✅", "Ditolak": "❌"}


def klaim_berjalan() -> list:
    return [k for k in D.setdefault("klaim", []) if k.get("status") in AKTIF]


def halaman_klaim():
    klaim = D.setdefault("klaim", [])
    barang = sorted(D["barang"], key=lambda b: b["nama"].lower())
    by = {b["id"]: b for b in barang}
    with st.container(key="kartu_klaim"):
        if barang:
            with st.expander("Catat klaim baru", expanded=not klaim):
                # barang yang masih bergaransi ditaruh paling atas
                urut = sorted(barang, key=lambda b: (sisa_hari(b.get("garansi")) is None
                                                     or sisa_hari(b.get("garansi")) < 0, b["nama"].lower()))
                with st.form(f"form_klaim_{versi()}"):
                    pilih = st.selectbox("Barang", [b["id"] for b in urut], key="kl_barang",
                                         format_func=lambda i: by[i]["nama"] + (
                                             f" (garansi sampai {fmt_iso(by[i]['garansi'])})"
                                             if by[i].get("garansi") else ""))
                    c1, c2 = st.columns(2)
                    tgl = c1.date_input("Tanggal diajukan", value=hari_ini(), key="kl_tgl")
                    nomor = c2.text_input("Nomor klaim atau tiket (opsional)", max_chars=60, key="kl_no")
                    masalah = st.text_area("Masalahnya", max_chars=400, key="kl_masalah", height=80)
                    kirim = st.form_submit_button("Simpan klaim", type="primary")
                if kirim:
                    if not masalah.strip():
                        st.error("Tulis masalahnya dulu.")
                    else:
                        g = iso_ke_date(by[pilih].get("garansi"))
                        if g and tgl > g:
                            st.warning("Catatan: tanggal klaim sudah melewati masa garansi barang ini.")
                        klaim.append({"id": uuid.uuid4().hex[:8], "barang": pilih, "nama": by[pilih]["nama"],
                                      "tgl": tgl.isoformat(), "masalah": masalah.strip(), "status": "Diajukan",
                                      "nomor": nomor.strip(), "catatan": ""})
                        selesai_simpan("Klaim garansi dicatat.")
        else:
            st.info("Belum ada barang.")
        if not klaim:
            st.caption("Belum ada klaim garansi.")
            return
        st.markdown(f"#### Klaim berjalan ({len(klaim_berjalan())})")
        for k in sorted(klaim, key=lambda x: (x.get("status") not in AKTIF, x.get("tgl", "")), reverse=False):
            b = by.get(k.get("barang"))
            lama = (hari_ini() - iso_ke_date(k["tgl"])).days if iso_ke_date(k.get("tgl")) else 0
            with st.container(key=f"item_kl_{k['id']}", border=True):
                st.markdown(f"**{IKON.get(k.get('status'), '')} {html.escape(k.get('nama', ''))}** · {k.get('status')}",
                            unsafe_allow_html=True)
                st.caption(f"Diajukan {fmt_iso(k.get('tgl', ''))}" + (f" · {lama} hari lalu" if k.get("status") in AKTIF else "")
                           + (f" · No. {k['nomor']}" if k.get("nomor") else "")
                           + (f" · di {nama_tempat(b)}" if b else ""))
                st.write(k.get("masalah", ""))
                if k.get("catatan"):
                    st.caption("Catatan: " + k["catatan"])
                c1, c2 = st.columns([1.4, 1], vertical_alignment="bottom")
                st_baru = c1.selectbox("Status", STATUS, index=STATUS.index(k["status"]) if k.get("status") in STATUS else 0,
                                       key=f"kl_st_{k['id']}")
                cat = st.text_input("Catatan perkembangan", value=k.get("catatan", ""), max_chars=200,
                                    key=f"kl_cat_{k['id']}")
                s1, s2 = st.columns(2)
                if s1.button("Simpan perubahan", key=f"kl_simpan_{k['id']}", use_container_width=True):
                    k["status"], k["catatan"] = st_baru, cat.strip()
                    if st_baru in AKTIF:
                        k.pop("selesai", None)
                    elif not k.get("selesai"):
                        k["selesai"] = hari_ini().isoformat()
                    selesai_simpan("Klaim diperbarui.")
                if s2.button("Hapus", key=f"kl_hapus_{k['id']}", use_container_width=True):
                    D["klaim"] = [x for x in klaim if x["id"] != k["id"]]
                    selesai_simpan("Klaim dihapus.")
