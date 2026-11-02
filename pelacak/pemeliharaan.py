"""Ukuran data dan titik pulih."""
import html
import io
import json
import os
import uuid

import requests
import streamlit as st

from pelacak.bantu import atur, selesai_simpan, semua_berkas
from pelacak.inti import (
    D, FOTO_LOKAL, Image, ImageOps, cfg_github, data_kosong, fmt_waktu, pengguna_nama, sekarang,
)
from pelacak.penyimpanan import (
    _gh_headers, _gh_url, _tulis_foto, ambil_foto, ambil_versi, daftar_versi, hapus_foto,
)


# -------------------------------------------------------------- ukuran data
def _kb(n) -> str:
    n = float(n)
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")
    return f"{n / 1024:.1f} KB".replace(".", ",")


def daftar_foto_repo():
    """[(path, ukuran_byte)] semua berkas di folder foto penyimpanan, atau None kalau gagal dibaca."""
    c = cfg_github()
    try:
        if c:
            r = requests.get(_gh_url(c, "foto"), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=30)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            return [(x["path"], int(x.get("size", 0))) for x in r.json() if x.get("type") == "file"]
        if not os.path.isdir(FOTO_LOKAL):
            return []
        return [(f"foto/{n}", os.path.getsize(os.path.join(FOTO_LOKAL, n))) for n in sorted(os.listdir(FOTO_LOKAL))]
    except Exception:
        return None


def foto_terpakai() -> set:
    pakai = set()
    for b in D["barang"] + [x["barang"] for x in D["sampah"]]:
        pakai.update(semua_berkas(b))
    for x in D["lokasi"] + D["sublokasi"]:
        if x.get("foto"):
            pakai.add(x["foto"])
    return pakai


def ganti_path_foto(lama: str, baru: str):
    for b in D["barang"] + [x["barang"] for x in D["sampah"]]:
        if b.get("foto") == lama:
            b["foto"] = baru
        if lama in b.get("galeri", []):
            b["galeri"] = [baru if p == lama else p for p in b["galeri"]]
    for x in D["lokasi"] + D["sublokasi"]:
        if x.get("foto") == lama:
            x["foto"] = baru


def kecilkan_jpeg(mentah: bytes, sisi: int) -> bytes:
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    im.thumbnail((sisi, sisi))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=65, optimize=True)
    return out.getvalue()


def halaman_ukuran():
    teks = json.dumps(D.data, ensure_ascii=False, indent=1, sort_keys=True)
    ukuran_data = len(teks.encode("utf-8"))
    rinci = sorted(((k, len(json.dumps(v, ensure_ascii=False, indent=1).encode("utf-8"))) for k, v in D.items()),
                   key=lambda x: -x[1])
    fotos = daftar_foto_repo()
    pakai = foto_terpakai()
    with st.container(key="kartu_barang"):
        st.markdown("#### Data (data.json)")
        st.markdown(f"**{_kb(ukuran_data)}** · {len(D['barang'])} barang")
        for k, n in rinci[:6]:
            persen = int(round(n * 100 / max(ukuran_data, 1)))
            st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(k)}</div>'
                        f'<div class="sub">{_kb(n)} · {persen}%</div></div>', unsafe_allow_html=True)
        st.markdown("#### Foto")
        if fotos is None:
            st.warning("Folder foto tidak bisa dibaca saat ini. Coba lagi nanti.")
            return
        total_foto = sum(n for _, n in fotos)
        yatim = [(p, n) for p, n in fotos if p not in pakai]
        st.markdown(f"**{len(fotos)} foto** · {_kb(total_foto)}")
        total = ukuran_data + total_foto
        st.progress(min(1.0, total / (1024 ** 3)), text=f"Total {_kb(total)} dari sekitar 1 GB batas nyaman repositori")
        besar = sorted([f for f in fotos if f[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))], key=lambda x: -x[1])[:8]
        if besar:
            st.markdown("**Foto terbesar**")
            for p, n in besar:
                c1, c2 = st.columns([1, 3], vertical_alignment="center")
                dat = ambil_foto(p)
                if dat:
                    c1.image(dat, width=56)
                c2.markdown(f"{_kb(n)}" + ("" if p in pakai else " · tidak terpakai"))

        st.markdown("#### Foto tidak terpakai")
        if not yatim:
            st.caption("Tidak ada. Semua foto di penyimpanan masih dipakai oleh barang atau lokasi.")
        else:
            st.caption(f"{len(yatim)} foto ({_kb(sum(n for _, n in yatim))}) tidak dipakai barang, lokasi, "
                       "maupun tempat sampah. Biasanya sisa dari unggahan yang tidak jadi disimpan.")
            if not st.session_state.get("uk_yatim"):
                st.button(f"Hapus {len(yatim)} foto tidak terpakai", key="uk_yatim_btn",
                          on_click=atur, args=("uk_yatim", True))
            else:
                st.warning("Hapus foto-foto ini dari penyimpanan? Ini tidak bisa dibatalkan.")
                y, n_, _ = st.columns([1.2, 1, 1])
                if y.button("Ya, hapus", type="primary", key="uk_yatim_ya"):
                    for p, _n in yatim:
                        hapus_foto(p)
                    st.session_state.uk_yatim = False
                    st.toast(f"{len(yatim)} foto dihapus.", icon="🧹")
                    st.rerun()
                n_.button("Batal", key="uk_yatim_bt", on_click=atur, args=("uk_yatim", False))

        st.markdown("#### Kecilkan foto")
        st.caption("Foto dikecilkan lagi dan disimpan sebagai berkas baru, lalu yang lama dihapus. "
                   "Dikerjakan maksimal 10 foto sekali jalan.")
        k1, k2 = st.columns(2)
        sisi = k1.selectbox("Sisi terpanjang (px)", [700, 500, 900], key="uk_sisi")
        ambang = k2.number_input("Hanya yang lebih besar dari (KB)", min_value=20, value=120, step=10, key="uk_ambang")
        kandidat = [(p, n) for p, n in fotos if p in pakai and n > ambang * 1024 and p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        st.caption(f"{len(kandidat)} foto memenuhi syarat.")
        if kandidat and Image is not None and st.button(f"Kecilkan {min(len(kandidat), 10)} foto", key="uk_kecil"):
            hapus_lama, hemat = [], 0
            bar = st.progress(0.0, text="Memproses...")
            batch = sorted(kandidat, key=lambda x: -x[1])[:10]
            for i, (p, n) in enumerate(batch):
                bar.progress((i + 1) / len(batch), text=f"Memproses {i + 1} dari {len(batch)}")
                dat = ambil_foto(p)
                if not dat:
                    continue
                try:
                    isi = kecilkan_jpeg(dat, int(sisi))
                    if len(isi) >= n * 0.9:
                        continue
                    baru_p = _tulis_foto(os.path.splitext(os.path.basename(p))[0].split("_")[0], isi)
                except Exception:
                    continue
                ganti_path_foto(p, baru_p)
                hapus_lama.append(p)
                hemat += n - len(isi)
            if hapus_lama:
                st.session_state["_snap"] = None          # penggantian berkas tidak dicatat di riwayat aktivitas
                selesai_simpan(f"{len(hapus_lama)} foto dikecilkan, hemat {_kb(hemat)}.",
                               sesudah=lambda fs=hapus_lama: [hapus_foto(p) for p in fs])
            else:
                st.info("Tidak ada foto yang bisa diperkecil lagi dengan pengaturan ini.")


# --------------------------------------------------------------- titik pulih
def halaman_pulih():
    with st.container(key="kartu_barang"):
        st.caption("Setiap perubahan tersimpan sebagai satu versi. Pilih versi lama untuk melihat perbedaannya, "
                   "lalu pulihkan seluruh data ke versi itu. Foto yang sudah dihapus tidak ikut kembali.")
        try:
            daftar = daftar_versi()
        except Exception as e:
            st.error(f"Riwayat versi tidak bisa dibaca: {e}")
            return
        if not daftar:
            st.info("Belum ada versi tersimpan. Versi pertama tercatat saat ada perubahan data berikutnya.")
            return
        peta = {v["id"]: v for v in daftar}
        pilih = st.selectbox("Versi", list(peta), key="pl_versi",
                             format_func=lambda i: f"{fmt_waktu(peta[i]['waktu'])} · {peta[i]['pesan'][:55]}")
        try:
            lama = ambil_versi(pilih)
        except Exception as e:
            st.error(f"Versi ini tidak bisa dibuka: {e}")
            return
        for k, v in data_kosong().items():
            lama.setdefault(k, v)
        kini_id = {b["id"]: b for b in D["barang"]}
        lama_id = {b["id"]: b for b in lama["barang"]}
        hilang_n = [b["nama"] for i, b in kini_id.items() if i not in lama_id]
        muncul_n = [b["nama"] for i, b in lama_id.items() if i not in kini_id]
        berubah_n = sum(1 for i, b in lama_id.items() if i in kini_id and kini_id[i] != b)
        st.markdown("**Perbandingan** (sekarang → versi ini)")
        for lab, kunci in (("Barang", "barang"), ("Tempat", "tempat"), ("Lokasi", "lokasi"),
                           ("Kategori", "kategori"), ("Tempat sampah", "sampah")):
            st.markdown(f'<div class="perhatian"><div class="brg">{lab}</div><div class="sub">'
                        f'{len(D.get(kunci, []))} → {len(lama.get(kunci, []))}</div></div>', unsafe_allow_html=True)

        def ringkas(nama_nama):
            return html.escape(", ".join(nama_nama[:8]) + (f" dan {len(nama_nama) - 8} lainnya" if len(nama_nama) > 8 else ""))
        if hilang_n:
            st.markdown(f"**Akan hilang dari daftar ({len(hilang_n)}):** {ringkas(hilang_n)}")
        if muncul_n:
            st.markdown(f"**Akan muncul kembali ({len(muncul_n)}):** {ringkas(muncul_n)}")
        if berubah_n:
            st.markdown(f"**Akan kembali ke isi lama:** {berubah_n} barang")
        sama = json.dumps(lama, sort_keys=True) == json.dumps(D.data, sort_keys=True)
        if sama:
            st.info("Versi ini sama persis dengan data sekarang, tidak ada yang perlu dipulihkan.")
            return
        yakin = st.checkbox("Ya, ganti seluruh data sekarang dengan versi ini", key=f"pl_yakin_{pilih}")
        if st.button("Pulihkan ke versi ini", type="primary", disabled=not yakin, key="pl_go"):
            lama.setdefault("aktivitas", []).append(
                {"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(),
                 "jenis": "data", "barang": "", "nama": "Seluruh data",
                 "rincian": f"Dipulihkan ke versi {fmt_waktu(peta[pilih]['waktu'])}: {peta[pilih]['pesan'][:80]}"})
            st.session_state.data = lama
            st.session_state["_snap"] = None
            selesai_simpan(f"Data dipulihkan ke versi {fmt_waktu(peta[pilih]['waktu'])}.")
