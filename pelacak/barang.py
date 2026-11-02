"""Kelola barang: daftar, form tambah dan ubah, aksi massal, dan salinan."""
import html
import re
import uuid

import streamlit as st

from pelacak.bantu import (
    ATRIBUT, MAKS_GALERI, MAKS_LAMPIRAN, MAKS_LAMPIRAN_MB, _norm_nama, atur, buang_barang,
    catat, daftar_lokasi, daftar_pemilik, daftar_tag, harga_b, idx, induk_dari, isi_dari,
    jumlah_b, kartu_barang_html, keturunan, lencana, lokasi_dari, minimum_b, nama_kat, nama_lok,
    nama_tempat, peringatan_serupa, pesan_hapus_barang, saring_barang, selesai_simpan,
    sinkron_isi, sub_dari, tampil_foto_kecil, tampil_galeri, tampil_lampiran, tempat_dari_lok,
    versi,
)
from pelacak.beranda import CEK_OPSI, cek_tiap_b
from pelacak.inti import (
    D, TANPA_KAT, TGL_MAX, TGL_MIN, adalah_admin, hari_ini, iso_ke_date, teks_cek,
)
from pelacak.penyimpanan import _tulis_foto, ambil_foto, hapus_foto, simpan_foto


# --------------------------------------------------------------- kelola barang
def _dengan_isi(b: dict) -> list:
    return [b] + [x for x in D["barang"] if x["id"] in keturunan(b["id"])]


def tandai_dibawa(b: dict, ke: str = ""):
    """Tandai barang (dan isinya) sedang dibawa keluar. Lokasi aslinya tidak diubah."""
    for x in _dengan_isi(b):
        x["dibawa"] = hari_ini().isoformat()
        if ke:
            x["dibawa_ke"] = ke
        else:
            x.pop("dibawa_ke", None)
        x["diubah"] = hari_ini().isoformat()


def kembalikan_dibawa(b: dict):
    for x in _dengan_isi(b):
        x.pop("dibawa", None)
        x.pop("dibawa_ke", None)
        x["diubah"] = hari_ini().isoformat()


def tandai_hilang(b: dict, di: str = "", tgl=None):
    b["hilang"] = (tgl or hari_ini()).isoformat()
    if di:
        b["hilang_di"] = di
    else:
        b.pop("hilang_di", None)
    b["diubah"] = hari_ini().isoformat()


def tandai_ketemu(b: dict, lok_baru: str = ""):
    """Barang ketemu. Kalau lok_baru diisi (dan barang tidak ada di dalam barang lain), lokasinya dipindah."""
    dari = nama_tempat(b)
    b.pop("hilang", None)
    b.pop("hilang_di", None)
    if lok_baru and lok_baru != b.get("lokasi") and not induk_dari(b):
        b["lokasi"] = lok_baru
        b.pop("sublokasi", None)
    b["diubah"] = hari_ini().isoformat()
    if nama_tempat(b) != dari:
        catat(b["id"], b["nama"], dari, nama_tempat(b))
        sinkron_isi(b["id"])


def form_cepat():
    """Formulir mini: nama, jumlah, lokasi. Lokasi diingat untuk barang berikutnya."""
    st.markdown("#### Tambah cepat")
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di Pengaturan > Lokasi sebelum menambah barang.")
        st.button("Kembali", key="cp_kembali_kosong", on_click=atur, args=("br_mode", None))
        return
    st.caption("Isi nama dan jumlah saja. Lokasi diingat untuk barang berikutnya. "
               "Detail lain bisa dilengkapi nanti lewat Edit.")
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    if st.session_state.get("cepat_lok") not in pl:
        st.session_state.cepat_lok = next(iter(pl))
    lok = st.selectbox("Lokasi", list(pl), key="cepat_lok", format_func=lambda i: pl[i])
    subs = {x["id"]: x["nama"] for x in D["sublokasi"] if x["lokasi"] == lok}
    ops_s = [""] + list(subs)
    if st.session_state.get("cepat_sub", "") not in ops_s:
        st.session_state.cepat_sub = ""
    sub = st.selectbox("Sub lokasi (boleh kosong)", ops_s, key="cepat_sub",
                       format_func=lambda i: "Tanpa sub lokasi" if not i else subs[i])
    with st.form(f"form_cepat_{versi()}"):
        nama = st.text_input("Nama barang", placeholder="Contoh: Charger")
        jumlah = st.number_input("Jumlah", min_value=0, value=1, step=1)
        kat = ""
        if D["kategori"]:
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            ops_k = [""] + list(pk)
            kat = st.selectbox("Kategori (boleh kosong)", ops_k,
                               format_func=lambda i: TANPA_KAT if not i else pk[i])
        c1, c2 = st.columns(2)
        lagi = c1.form_submit_button("Simpan, tambah lagi", type="primary")
        selesai = c2.form_submit_button("Simpan, selesai")
    st.button("Kembali", key="cp_kembali", on_click=atur, args=("br_mode", None))
    if lagi or selesai:
        nama = nama.strip()
        if not nama:
            st.error("Nama barang wajib diisi.")
            return
        if peringatan_serupa(nama):
            return
        b = {"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": lok, "jumlah": int(jumlah),
             "diubah": hari_ini().isoformat()}
        if sub:
            b["sublokasi"] = sub
        if kat:
            b["kategori"] = kat
        catat(b["id"], nama, "", nama_tempat(b))
        D["barang"].append(b)
        selesai_simpan(f"{nama} ditambahkan.", br_mode=None if selesai else "cepat")


def salin_barang(b: dict) -> dict:
    """Buat salinan barang (tanpa foto, nomor seri, dan tanda pakai), lalu catat sebagai barang baru."""
    s = {k: v for k, v in b.items() if k not in ("id", "foto", "galeri", "dipakai", "habis", "seri", "dibawa", "dibawa_ke", "hilang", "hilang_di", "barcode", "cek_terakhir", "lampiran", "perawatan", "kondisi", "kondisi_sejak", "kondisi_ket")}
    s["id"] = uuid.uuid4().hex[:8]
    s["nama"] = f"{b['nama']} (salinan)"
    s["diubah"] = hari_ini().isoformat()
    catat(s["id"], s["nama"], "", nama_tempat(s))
    D["barang"].append(s)
    return s


def kunci_pilih(i: str) -> str:
    return f"pl_{i}_{versi()}"


def set_pilihan(ids: list, nilai: bool):
    for i in ids:
        st.session_state[kunci_pilih(i)] = nilai


AKSI_MASSAL = ["Ubah kategori", "Ubah pemilik", "Tambah label", "Tandai favorit", "Batal favorit", "Tandai sedang dibawa",
              "Tandai perlu beli", "Batal tandai perlu beli", "Buang ke tempat sampah"]


def aksi_massal(urut: list):
    """Panel aksi untuk barang yang dicentang di daftar Kartu."""
    ids = [b["id"] for b in urut]
    dipilih = [b for b in urut if st.session_state.get(kunci_pilih(b["id"]))]
    n = len(dipilih)
    c1, c2 = st.columns(2)
    c1.button(f"Pilih semua ({len(ids)})", key="bm_semua", use_container_width=True,
              on_click=set_pilihan, args=(ids, True))
    c2.button("Kosongkan", key="bm_kosong", use_container_width=True,
              on_click=set_pilihan, args=(ids, False))
    st.caption(f"{n} barang dipilih")
    if not n:
        return
    aksi = st.selectbox("Aksi untuk barang terpilih", AKSI_MASSAL, key="bm_aksi")
    if aksi == "Ubah kategori":
        if not D["kategori"]:
            st.info("Belum ada kategori. Tambahkan dulu di Pengaturan > Kategori.")
            return
        pk = {k["id"]: k["nama"] for k in D["kategori"]}
        ops = [""] + list(pk)
        kat = st.selectbox("Kategori baru", ops, key=f"bm_kat_{versi()}",
                           format_func=lambda i: TANPA_KAT if not i else pk[i])
        if st.button(f"Ubah kategori {n} barang", type="primary", key="bm_ubah"):
            for b in dipilih:
                if kat:
                    b["kategori"] = kat
                else:
                    b.pop("kategori", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"Kategori {n} barang diubah.")
    elif aksi == "Ubah pemilik":
        ops = [""] + daftar_pemilik() + ["__baru__"]
        pem = st.selectbox("Pemilik baru", ops, key=f"bm_pem_{versi()}",
                           format_func=lambda x: "Tanpa pemilik" if not x else "➕ Pemilik baru..." if x == "__baru__" else x)
        if pem == "__baru__":
            pem = st.text_input("Nama pemilik baru", key=f"bm_pem_baru_{versi()}", max_chars=40).strip()
        if st.button(f"Ubah pemilik {n} barang", type="primary", key="bm_pemilik"):
            for b in dipilih:
                if pem:
                    b["pemilik"] = pem
                else:
                    b.pop("pemilik", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"Pemilik {n} barang diubah.")
    elif aksi == "Tambah label":
        tag_baru = st.multiselect("Label yang ditambahkan", daftar_tag(), key=f"bm_tag_{versi()}", accept_new_options=True)
        if st.button(f"Tambah label ke {n} barang", type="primary", key="bm_tag_go"):
            tags = list(dict.fromkeys(t.strip()[:30] for t in tag_baru if t.strip()))
            if not tags:
                st.error("Pilih atau ketik minimal satu label.")
            else:
                for b in dipilih:
                    b["tag"] = list(dict.fromkeys(list(b.get("tag", [])) + tags))[:8]
                    b["diubah"] = hari_ini().isoformat()
                selesai_simpan(f"Label ditambahkan ke {n} barang.")
    elif aksi in ("Tandai favorit", "Batal favorit"):
        if st.button(f"{aksi} ({n} barang)", type="primary", key="bm_fav"):
            for b in dipilih:
                if aksi == "Tandai favorit":
                    b["favorit"] = True
                else:
                    b.pop("favorit", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"{n} barang diubah.")
    elif aksi == "Tandai sedang dibawa":
        ke = st.text_input("Dibawa ke mana atau untuk apa (boleh kosong)", key=f"bm_ke_{versi()}", max_chars=60).strip()
        if st.button(f"Tandai {n} barang sedang dibawa", type="primary", key="bm_bawa"):
            for b in dipilih:
                tandai_dibawa(b, ke)
            selesai_simpan(f"{n} barang ditandai sedang dibawa.")
    elif aksi in ("Tandai perlu beli", "Batal tandai perlu beli"):
        tandai = aksi == "Tandai perlu beli"
        if st.button(f"{aksi} ({n} barang)", type="primary", key="bm_habis"):
            for b in dipilih:
                if tandai:
                    b["habis"] = True
                else:
                    b.pop("habis", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"{n} barang ditandai." if tandai else f"Tanda perlu beli {n} barang dibatalkan.")
    else:
        if not st.session_state.get("bm_buang"):
            st.button(f"Buang {n} barang", type="primary", key="bm_buang_btn",
                      on_click=atur, args=("bm_buang", True))
        else:
            lepas = sum(len([x for x in isi_dari(b["id"]) if x["id"] not in {p["id"] for p in dipilih}])
                        for b in dipilih)
            st.warning(f"Pindahkan {n} barang ke tempat sampah?"
                       + (f" {lepas} barang di dalamnya akan dilepas dari induknya." if lepas else "")
                       + " Masih bisa dipulihkan selama 30 hari.")
            y, t, _ = st.columns([1.3, 1, 1])
            if y.button("Ya, buang", type="primary", key="bm_buang_ya"):
                for b in dipilih:
                    buang_barang(b)
                selesai_simpan(f"{n} barang dipindahkan ke tempat sampah.", bm_buang=False)
            t.button("Batal", key="bm_buang_batal", on_click=atur, args=("bm_buang", False))


def halaman_barang():
    by_id = {b["id"]: b for b in D["barang"]}
    mode = st.session_state.get("br_mode")          # None (daftar), "baru", atau id barang
    if mode not in (None, "baru", "cepat") and mode not in by_id:
        mode = None
    with st.container(key="kartu_barang"):
        if mode == "cepat":
            form_cepat()
            return
        if not mode:
            with st.container(key="baris_cari"):
                kc, kt = st.columns([5, 2], vertical_alignment="center")
                cari = " ".join(kc.text_input("Pencarian", key="br_cari", icon=":material/search:",
                                              placeholder="Cari nama, merek, lokasi, atau kategori...",
                                              label_visibility="collapsed").lower().split())
                kt.button("Tambah", type="primary", key="br_tambah", icon=":material/add:",
                          use_container_width=True, on_click=atur, args=("br_mode", "baru"))
            tm1, tm2 = st.columns([3, 2], vertical_alignment="center")
            mode_tampil = tm1.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                                key="tampilan", label_visibility="collapsed") or "Kartu"
            tm2.button("Tambah cepat", key="br_cepat", icon=":material/bolt:", use_container_width=True,
                       on_click=atur, args=("br_mode", "cepat"),
                       help="Form mini: cukup nama, jumlah, dan lokasi")
            if not D["barang"]:
                st.write("Belum ada barang.")
            if mode_tampil == "Kartu":
                urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
                if cari:
                    urut, _mirip_n = saring_barang(urut, cari)
                    if not urut:
                        st.info("Tidak ada barang yang cocok dengan pencarian.")
                pilih_on = bool(urut) and st.toggle("Pilih banyak", key="br_pilih",
                                                    help="Centang beberapa barang lalu ubah kategori, tandai, atau buang sekaligus")
                if pilih_on:
                    aksi_massal(urut)
                for b in urut:
                    with st.container(key=f"item_k_{b['id']}"):
                        st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                        tampil_galeri(b)
                        tampil_lampiran(b)
                        if pilih_on:
                            st.checkbox("Pilih barang ini", key=kunci_pilih(b["id"]))
                            continue
                        e1, e2, e3, e4 = st.columns([1, 1, 1.5, 1.5])
                        e1.button("Edit", key=f"kedit_{b['id']}", on_click=atur, args=("br_mode", b["id"]),
                                  use_container_width=True)
                        e2.button("Hapus", key=f"khapus_{b['id']}", on_click=atur, args=("br_hapus", b["id"]),
                                  use_container_width=True)
                        if e3.button("Dipakai", key=f"kpakai_{b['id']}", use_container_width=True,
                                     help="Catat bahwa barang ini dipakai hari ini"):
                            b["dipakai"] = hari_ini().isoformat()
                            selesai_simpan("Dicatat dipakai hari ini.")
                        if e4.button("Salin", key=f"ksalin_{b['id']}", use_container_width=True,
                                     help="Buat salinan barang ini, lalu ubah detailnya"):
                            baru_s = salin_barang(b)
                            selesai_simpan("Salinan dibuat. Ubah nama dan detailnya di formulir.", br_mode=baru_s["id"])
                        if st.session_state.get("br_hapus") == b["id"]:
                            st.warning(pesan_hapus_barang(b))
                            y, n, _ = st.columns([1, 1, 2])
                            if y.button("Ya, buang", type="primary", key=f"brya_{b['id']}"):
                                buang_barang(b)
                                selesai_simpan("Dipindahkan ke tempat sampah.", br_hapus=None)
                            n.button("Batal", key=f"brbatal_{b['id']}", on_click=atur, args=("br_hapus", None))
                return
            lebar = [0.8, 1.2, 4, 3.4, 2.2, 1, 1.7]
            kep = st.columns(lebar)
            for kol, judul in zip(kep, ["No.", "Foto", "Barang", "Lokasi", "Kategori", "Jml", "#"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            if cari:
                urut, _mirip_n = saring_barang(urut, cari)
                if not urut:
                    st.info("Tidak ada barang yang cocok dengan pencarian.")
            for no, b in enumerate(urut, 1):
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                k[0].write(f"{no}.")
                tampil_foto_kecil(b, k[1])
                k[2].markdown(f'<div class="brg">{html.escape(b["nama"])}{lencana(b)}</div>',
                              unsafe_allow_html=True)
                k[3].write(nama_tempat(b))
                k[4].write(nama_kat(b) if b.get("kategori") else "")
                k[5].write(b.get("jumlah", 1))
                t1, t2 = k[6].columns(2)
                t1.button("✏️", key=f"bredit_{b['id']}", help="Ubah", on_click=atur, args=("br_mode", b["id"]))
                t2.button("🗑️", key=f"brhapus_{b['id']}", help="Hapus", on_click=atur, args=("br_hapus", b["id"]))
                if st.session_state.get("br_hapus") == b["id"]:
                    st.warning(pesan_hapus_barang(b))
                    y, n, _ = st.columns([1, 1, 4])
                    if y.button("Ya, buang", type="primary", key=f"brya_{b['id']}"):
                        buang_barang(b)
                        selesai_simpan("Dipindahkan ke tempat sampah.", br_hapus=None)
                    n.button("Batal", key=f"brbatal_{b['id']}", on_click=atur, args=("br_hapus", None))
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            return

        b = by_id.get(mode, {})
        st.markdown("#### Form Barang")
        if not D["lokasi"]:
            st.info("Buat lokasi dulu (misalnya \"Lemari kamar\") sebelum menambah barang.")
            c1, c2 = st.columns([1, 1])
            if adalah_admin():
                c1.button("Buka menu Lokasi", on_click=lambda: st.session_state.update(halaman="Lokasi"))
            else:
                st.caption("Minta admin menambahkan lokasi di Pengaturan.")
            c2.button("Kembali", on_click=atur, args=("br_mode", None))
            return
        kandidat = [x for x in sorted(D["barang"], key=lambda x: x["nama"].lower())
                    if x["id"] != b.get("id") and x["id"] not in keturunan(b.get("id", "-"))]
        induk, peta_i = "", {x["id"]: x for x in kandidat}
        if kandidat:
            ops_i = [""] + list(peta_i)
            induk = st.selectbox("Disimpan di dalam barang lain (boleh kosong)", ops_i,
                                 index=idx(ops_i, b.get("dalam", "")), key=f"br_dalam_{mode}_{versi()}",
                                 format_func=lambda i: "Tidak, simpan langsung di lokasi" if not i
                                 else f'{peta_i[i]["nama"]} ({nama_tempat(peta_i[i])})',
                                 help="Contoh: plester disimpan di dalam Tas P3K. Lokasinya otomatis mengikuti barang itu.")
        if induk:
            p_induk = peta_i[induk]
            lok, sub = p_induk.get("lokasi", ""), p_induk.get("sublokasi", "")
            st.caption(f"Lokasi mengikuti {p_induk['nama']}: {nama_tempat(p_induk)}")
        else:
            # Pilihan tempat ada di luar form supaya daftar lokasi di bawahnya langsung ikut berubah.
            f_tem = ""
            if D["tempat"]:
                ptem = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
                ops_t = [""] + list(ptem)
                awal_t = (tempat_dari_lok(lokasi_dari(b)) or {}).get("id", "") if lokasi_dari(b) else ""
                f_tem = st.selectbox("Tempat", ops_t, index=idx(ops_t, awal_t), key=f"br_tempat_{mode}_{versi()}",
                                     format_func=lambda i: "Semua tempat" if not i else ptem[i],
                                     help="Pilih tempat dulu supaya daftar lokasi di bawah hanya menampilkan isi tempat itu.")
            pl = {l["id"]: (l["nama"] if f_tem else nama_lok(l)) for l in daftar_lokasi()
                  if not f_tem or l.get("tempat") == f_tem}
            if not pl:
                st.info("Tempat ini belum punya lokasi. Pilih tempat lain, atau tambahkan lokasinya di Pengaturan > Lokasi.")
                st.button("Kembali", key="br_kembali_kosong", on_click=atur, args=("br_mode", None))
                return
            ids_l = list(pl)
            k_lok = f"br_lok_{mode}_{versi()}_{f_tem or 'semua'}"
            lok = st.selectbox("Lokasi", ids_l, index=idx(ids_l, b.get("lokasi", "")), key=k_lok,
                               format_func=lambda i: pl[i])
            sub = ""
            psub_f = {x["id"]: x["nama"] for x in D["sublokasi"] if x["lokasi"] == lok}
            if psub_f:
                ops_s = [""] + list(psub_f)
                awal_s = b.get("sublokasi", "") if (sub_dari(b) and b.get("lokasi") == lok) else ""
                sub = st.selectbox("Sub lokasi (boleh kosong)", ops_s, index=idx(ops_s, awal_s),
                                   key=f"br_sub_{mode}_{versi()}_{lok}",
                                   format_func=lambda i: "Tanpa sub lokasi" if not i else psub_f[i])
        ops_pem = [""] + daftar_pemilik() + ["__baru__"]
        pem_sel = st.selectbox("Pemilik (boleh kosong)", ops_pem, index=idx(ops_pem, b.get("pemilik", "")),
                               key=f"br_pem_{mode}_{versi()}",
                               format_func=lambda x: "Tanpa pemilik" if not x else "➕ Pemilik baru..." if x == "__baru__" else x,
                               help="Untuk barang bersama, misalnya milik teman kos atau keluarga.")
        pemilik = (st.text_input("Nama pemilik baru", key=f"br_pem_baru_{mode}_{versi()}", max_chars=40).strip()
                   if pem_sel == "__baru__" else pem_sel)
        with st.form(f"form_br_{mode}_{versi()}"):
            f1, f2 = st.columns([4, 1])
            nama = f1.text_input("Nama barang", value=b.get("nama", ""), placeholder="Contoh: Parfum")
            jumlah = f2.number_input("Jumlah", min_value=0, value=jumlah_b(b) if b else 1, step=1)
            kat = ""
            if D["kategori"]:
                pk = {k["id"]: k["nama"] for k in D["kategori"]}
                ops_k = [""] + list(pk)
                kat = st.selectbox("Kategori (boleh kosong)", ops_k, index=idx(ops_k, b.get("kategori", "")),
                                   format_func=lambda i: TANPA_KAT if not i else pk[i])
            h1, h2 = st.columns(2)
            harga = h1.number_input("Harga beli per buah (Rp)", min_value=0, value=harga_b(b), step=1000,
                                    help="Isi 0 kalau belum tahu. Dipakai di Statistik (tab Nilai barang).")
            tb = h2.date_input("Tanggal pembelian (boleh kosong)", value=iso_ke_date(b.get("dibeli")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY",
                               help="Berguna untuk menghitung masa garansi dan umur barang.")
            h3, h4 = st.columns(2)
            kd = h3.date_input("Kedaluwarsa (boleh kosong)", value=iso_ke_date(b.get("kedaluwarsa")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            gr = h4.date_input("Garansi sampai (boleh kosong)", value=iso_ke_date(b.get("garansi")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            habis = st.checkbox("Habis / perlu beli lagi", value=bool(b.get("habis")))
            fav = st.checkbox("Favorit", value=bool(b.get("favorit")), help="Barang favorit tampil di Beranda dan di urutan atas pencarian.")
            tag_pil = st.multiselect("Label (boleh kosong)", sorted(set(daftar_tag()) | set(b.get("tag", [])), key=str.lower),
                                     default=b.get("tag", []), accept_new_options=True,
                                     help="Ketik untuk membuat label baru, misalnya musim hujan atau naik gunung.")
            minimum = st.number_input("Stok minimum", min_value=0, value=minimum_b(b), step=1,
                                      help="Kalau jumlah sudah sampai angka ini atau kurang, barang otomatis "
                                           "masuk daftar Perlu beli. Isi 0 kalau tidak dipantau.")
            with st.expander("Detail tambahan (merek, ukuran, warna, nomor seri, barcode, cek berkala)",
                             expanded=any(b.get(k) for k, _ in ATRIBUT) or bool(b.get("barcode") or b.get("cek_tiap"))):
                a1, a2 = st.columns(2)
                a3, a4 = st.columns(2)
                nilai_atr = {}
                for kol, (kunci, label) in zip((a1, a2, a3, a4), ATRIBUT):
                    nilai_atr[kunci] = kol.text_input(label, value=b.get(kunci, ""), max_chars=60,
                                                      help="Nomor seri berguna untuk klaim garansi." if kunci == "seri" else None)
                a5, a6 = st.columns(2)
                barcode_in = a5.text_input("Barcode", value=b.get("barcode", ""), max_chars=40,
                                           help="Atau pasang lewat menu Scan barcode.")
                cek_in = a6.selectbox("Cek berkala", CEK_OPSI, index=idx(CEK_OPSI, cek_tiap_b(b)), format_func=teks_cek,
                                      help="Muncul di Beranda saat sudah waktunya dicek.")
            foto_lama = b.get("foto", "")
            if foto_lama:
                dat = ambil_foto(foto_lama)
                if dat:
                    st.image(dat, width=140)
            upl = st.file_uploader("Foto barang (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                   help="Foto dikecilkan otomatis supaya hemat tempat.")
            hapus_cb = st.checkbox("Hapus foto yang sekarang") if foto_lama else False
            galeri_lama, hapus_g = list(b.get("galeri", [])), []
            lamp_lama, hapus_l = list(b.get("lampiran", [])), []
            if galeri_lama:
                st.caption("Foto tambahan yang ada. Centang untuk menghapus.")
                kg = st.columns(3)
                for i, p in enumerate(galeri_lama):
                    with kg[i % 3]:
                        dat = ambil_foto(p)
                        if dat:
                            st.image(dat, use_container_width=True)
                        if st.checkbox("Hapus", key=f"hg_{mode}_{i}_{versi()}"):
                            hapus_g.append(p)
            upl_g = st.file_uploader("Foto tambahan (boleh banyak)", type=["jpg", "jpeg", "png", "webp"],
                                     accept_multiple_files=True, key=f"upl_g_{mode}_{versi()}",
                                     help=f"Misalnya foto nota atau nomor seri. Maksimal {MAKS_GALERI} foto tambahan per barang.")
            for j, x in enumerate(lamp_lama):
                if st.checkbox(f"Hapus lampiran: {x.get('nama', 'dokumen')}", key=f"hl_{mode}_{j}_{versi()}"):
                    hapus_l.append(x["path"])
            upl_l = st.file_uploader("Lampiran dokumen PDF (boleh banyak)", type=["pdf"], accept_multiple_files=True,
                                     key=f"upl_l_{mode}_{versi()}",
                                     help=f"Nota, buku manual, atau kartu garansi. Maksimal {MAKS_LAMPIRAN} berkas, masing-masing {MAKS_LAMPIRAN_MB} MB.")
            catatan = st.text_area("Catatan", value=b.get("catatan", ""),
                                   help="Alamat web yang kamu tulis di sini otomatis bisa diklik.")
            tautan = st.text_area("Tautan (satu per baris, boleh kosong)", value=b.get("tautan", ""), height=90,
                                  placeholder="https://toko.example/nota-123",
                                  help="Misalnya nota online, buku manual, atau halaman toko.")
            t1, t2, _ = st.columns([1, 1, 4])
            simpan_ = t1.form_submit_button("Simpan", type="primary")
            kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.br_mode = None
                st.rerun()
            if simpan_:
                nama = nama.strip()
                if not nama:
                    st.error("Nama barang wajib diisi.")
                elif sub and next(x for x in D["sublokasi"] if x["id"] == sub)["lokasi"] != lok:
                    st.error("Sub lokasi yang dipilih bukan bagian dari lokasi di atas.")
                elif tautan.strip() and any(not re.match(r"https?://", s.strip(), re.IGNORECASE)
                                            for s in tautan.splitlines() if s.strip()):
                    st.error("Setiap baris tautan harus diawali http:// atau https://")
                elif (mode == "baru" or _norm_nama(nama) != _norm_nama(b.get("nama", ""))) and \
                        peringatan_serupa(nama, b.get("id", "")):
                    pass
                else:
                    id_ = b.get("id") or uuid.uuid4().hex[:8]
                    foto_baru, galat = "", ""
                    sumber = upl
                    if sumber is not None:
                        try:
                            foto_baru = simpan_foto(id_, sumber.getvalue())
                        except Exception as e:
                            galat = f"Foto gagal diunggah: {e}"
                    sisa_g = [p for p in galeri_lama if p not in hapus_g]
                    galeri_baru = []
                    if not galat and len(sisa_g) + len(upl_g or []) > MAKS_GALERI:
                        galat = f"Foto tambahan maksimal {MAKS_GALERI} per barang."
                    if not galat:
                        for f in (upl_g or []):
                            try:
                                galeri_baru.append(simpan_foto(id_, f.getvalue()))
                            except Exception as e:
                                galat = f"Foto tambahan gagal diunggah: {e}"
                                break
                    sisa_l = [x for x in lamp_lama if x["path"] not in hapus_l]
                    lamp_baru = []
                    if not galat and len(sisa_l) + len(upl_l or []) > MAKS_LAMPIRAN:
                        galat = f"Lampiran maksimal {MAKS_LAMPIRAN} berkas per barang."
                    if not galat:
                        for f in (upl_l or []):
                            isi_f = f.getvalue()
                            if len(isi_f) > MAKS_LAMPIRAN_MB * 1024 * 1024:
                                galat = f"{f.name} lebih dari {MAKS_LAMPIRAN_MB} MB."
                                break
                            try:
                                lamp_baru.append({"path": _tulis_foto(id_, isi_f, "pdf"), "nama": f.name[:80]})
                            except Exception as e:
                                galat = f"Lampiran gagal diunggah: {e}"
                                break
                    if galat:
                        for x in lamp_baru:
                            hapus_foto(x["path"])
                        st.error(galat)
                    else:
                        baru = dict(b) if mode != "baru" else {"id": id_}
                        isi = {"nama": nama, "lokasi": lok, "sublokasi": sub, "kategori": kat,
                               "catatan": catatan.strip(), "harga": int(harga),
                               "tautan": "\n".join(s.strip() for s in tautan.splitlines() if s.strip()),
                               "dibeli": tb.isoformat() if tb else "",
                               "kedaluwarsa": kd.isoformat() if kd else "",
                               "garansi": gr.isoformat() if gr else "", "habis": bool(habis),
                               "minimum": int(minimum), "dalam": induk, "pemilik": pemilik, "favorit": bool(fav),
                               "tag": list(dict.fromkeys(t.strip()[:30] for t in tag_pil if t.strip()))[:8],
                               "barcode": barcode_in.strip(), "cek_tiap": int(cek_in)}
                        isi.update({k: v.strip() for k, v in nilai_atr.items()})
                        for kunci, v in isi.items():
                            if v or kunci in ("nama", "lokasi"):
                                baru[kunci] = v
                            else:
                                baru.pop(kunci, None)
                        baru["jumlah"] = int(jumlah)
                        baru["diubah"] = hari_ini().isoformat()
                        if baru.get("cek_tiap"):
                            baru.setdefault("cek_terakhir", hari_ini().isoformat())
                        else:
                            baru.pop("cek_terakhir", None)
                        fotos_hapus = list(hapus_g)
                        if foto_baru:
                            baru["foto"] = foto_baru
                            if foto_lama:
                                fotos_hapus.append(foto_lama)
                        elif hapus_cb:
                            if foto_lama:
                                fotos_hapus.append(foto_lama)
                            baru.pop("foto", None)
                        fotos_hapus += hapus_l
                        lamp_akhir = sisa_l + lamp_baru
                        if lamp_akhir:
                            baru["lampiran"] = lamp_akhir
                        else:
                            baru.pop("lampiran", None)
                        galeri_akhir = sisa_g + galeri_baru
                        if galeri_akhir:
                            baru["galeri"] = galeri_akhir
                        else:
                            baru.pop("galeri", None)
                        tempat_baru = nama_tempat(baru)
                        if mode == "baru":
                            catat(id_, nama, "", tempat_baru)
                            D["barang"].append(baru)
                        else:
                            if nama_tempat(b) != tempat_baru:
                                catat(id_, nama, nama_tempat(b), tempat_baru)
                            D["barang"] = [baru if x["id"] == mode else x for x in D["barang"]]
                        sinkron_isi(id_)
                        selesai_simpan("Tersimpan.",
                                       sesudah=(lambda fs=fotos_hapus: [hapus_foto(p) for p in fs]) if fotos_hapus else None,
                                       br_mode=None)
