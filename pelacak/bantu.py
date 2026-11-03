"""Pembantu data: lokasi, barang, tag, pencarian, kartu barang, galeri, lampiran, dan teks peringatan."""
import base64
import html
import io
import re
import uuid
from datetime import datetime
from difflib import SequenceMatcher

import streamlit as st

from pelacak.inti import (
    D, MAKS_RIWAYAT, TANPA, TANPA_KAT, WIB, fmt_iso, hari_ini, pengguna_nama, sekarang,
    sisa_hari,
)
from pelacak.penyimpanan import ambil_foto, commit


# ---------------------------------------------------------------- bantu data
def atur(kunci: str, nilai):
    st.session_state[kunci] = nilai


def pindah_halaman(h: str):
    """Ganti menu sekaligus tutup form/konfirmasi yang masih terbuka."""
    st.session_state.halaman = h
    for k in ("br_mode", "br_hapus", "sp_hapus", "sp_kosong", "pj_hapus", "pj_mode", "pj_kembali", "rp_hapus", "rc_mode", "rc_hapus", "bl_mode", "bm_buang", "db_mode", "hl_mode", "hl_ketemu", "pk_hapus", "sc_n", "op_rencana", "serupa_ok",
              "edit_tempat", "hapus_tempat", "edit_kategori", "hapus_kategori",
              "edit_lokasi", "hapus_lokasi", "edit_sub", "hapus_sub", "edit_pemilik", "hapus_pemilik"):
        st.session_state.pop(k, None)
    for k in [k for k in st.session_state if str(k).startswith("tb_")]:
        st.session_state.pop(k, None)


def versi() -> int:
    return st.session_state.get("ver", 0)


def selesai_simpan(pesan: str, sesudah=None, **setelah):
    """Simpan ke penyimpanan. Kalau berhasil, jalankan `sesudah`, atur keadaan halaman, lalu muat ulang."""
    if commit(pesan):
        if sesudah:
            try:
                sesudah()
            except Exception:
                pass
        for k, v in setelah.items():
            st.session_state[k] = v
        st.session_state.pop("serupa_ok", None)
        st.session_state.ver = versi() + 1
        st.rerun()


def ada_kembar(nama_nama) -> bool:
    kecil = [n.lower() for n in nama_nama]
    return len(set(kecil)) != len(kecil)


def idx(daftar, nilai) -> int:
    return daftar.index(nilai) if nilai in daftar else 0


def lokasi_dari(b: dict):
    return next((x for x in D["lokasi"] if x["id"] == b.get("lokasi")), None)


def sub_dari(b: dict):
    """Sub lokasi barang kalau valid dan masih di bawah lokasinya, kalau tidak None."""
    sid = b.get("sublokasi")
    if not sid:
        return None
    return next((x for x in D["sublokasi"] if x["id"] == sid and x["lokasi"] == b.get("lokasi")), None)


def tempat_dari_lok(l: dict):
    """Tempat (rumah, kantor, dst.) dari sebuah lokasi, atau None kalau belum diatur."""
    return next((t for t in D["tempat"] if t["id"] == l.get("tempat")), None)


def nama_lok(l: dict) -> str:
    """Nama lokasi lengkap dengan tempatnya: 'Rumah A › Lemari kamar'."""
    t = tempat_dari_lok(l)
    return f"{t['nama']} › {l['nama']}" if t else l["nama"]


def daftar_lokasi():
    return sorted(D["lokasi"], key=lambda l: nama_lok(l).lower())


def nama_lokasi(b: dict) -> str:
    x = lokasi_dari(b)
    return nama_lok(x) if x else TANPA


def nama_kat(b: dict) -> str:
    x = next((k for k in D["kategori"] if k["id"] == b.get("kategori")), None)
    return x["nama"] if x else TANPA_KAT


def nama_tempat(b: dict) -> str:
    """Lokasi, ditambah sub lokasi kalau ada. Dipakai untuk tampilan dan pencarian."""
    s = sub_dari(b)
    return f"{nama_lokasi(b)} › {s['nama']}" if s else nama_lokasi(b)


def kelompok(brg):
    """Bagi barang per lokasi, lalu per sub lokasi di dalamnya."""
    hasil = []
    for l in daftar_lokasi():
        milik = [b for b in brg if b.get("lokasi") == l["id"]]
        langsung = [b for b in milik if sub_dari(b) is None]
        if langsung:
            hasil.append((nama_lok(l), langsung))
        for s in D["sublokasi"]:
            if s["lokasi"] != l["id"]:
                continue
            ang = [b for b in milik if b.get("sublokasi") == s["id"]]
            if ang:
                hasil.append((f"{nama_lok(l)} › {s['nama']}", ang))
    ids = {l["id"] for l in D["lokasi"]}
    lain = [b for b in brg if b.get("lokasi") not in ids]
    if lain:
        hasil.append((TANPA, lain))
    return hasil


def judul_grup(nama, jumlah):
    st.markdown(f'<div class="bidang">{html.escape(nama)} · {jumlah} barang</div>', unsafe_allow_html=True)


def jumlah_b(b: dict) -> int:
    try:
        return int(b.get("jumlah", 1) or 0)
    except Exception:
        return 1


def harga_b(b: dict) -> int:
    try:
        return max(int(b.get("harga", 0) or 0), 0)
    except Exception:
        return 0


def harga_asli_b(b: dict) -> int:
    """Harga sebelum diskon per buah. 0 kalau tidak diisi."""
    try:
        return max(int(b.get("harga_asli", 0) or 0), 0)
    except Exception:
        return 0


def diskon_persen(b: dict) -> int:
    """Persen diskon dibulatkan. 0 kalau harga asli atau harga beli kosong, atau tidak ada potongan."""
    asli, beli = harga_asli_b(b), harga_b(b)
    if not asli or not beli or beli >= asli:
        return 0
    return int(round((asli - beli) * 100 / asli))


def minimum_b(b: dict) -> int:
    try:
        return max(int(b.get("minimum", 0) or 0), 0)
    except Exception:
        return 0


def stok_menipis(b: dict) -> bool:
    """Stok minimum diisi (lebih dari 0) dan jumlah sudah turun sampai batas itu."""
    m = minimum_b(b)
    return m > 0 and jumlah_b(b) <= m


def perlu_beli(b: dict) -> bool:
    return bool(b.get("habis")) or jumlah_b(b) == 0 or stok_menipis(b)


def pinjam_aktif(id_barang: str):
    """Catatan peminjaman yang masih berjalan untuk barang milik sendiri (dipinjamkan ke orang lain)."""
    return next((p for p in D["pinjam"] if p.get("barang") == id_barang and p.get("arah") == "keluar"
                 and not p.get("kembali")), None)


def lencana(b: dict) -> str:
    h = '<span class="lencana lc-m">★ Favorit</span>' if b.get("favorit") else ""
    if perlu_beli(b):
        menipis = stok_menipis(b) and not b.get("habis") and jumlah_b(b) > 0
        h += f'<span class="lencana lc-r">{"Stok menipis" if menipis else "Perlu beli"}</span>'
    p = pinjam_aktif(b["id"])
    if p:
        h += f'<span class="lencana lc-m">Dipinjam {html.escape(p.get("orang", ""))}</span>'
    if b.get("kondisi") in KONDISI:
        h += f'<span class="lencana {"lc-r" if b["kondisi"] == "rusak" else "lc-m"}">{KONDISI[b["kondisi"]]}</span>'
    if b.get("hilang"):
        h += '<span class="lencana lc-r">Hilang</span>'
    if b.get("dibawa"):
        h += '<span class="lencana lc-b">Sedang dibawa</span>'
    n_isi = len(isi_dari(b["id"]))
    if n_isi:
        h += f'<span class="lencana lc-b">Berisi {n_isi}</span>'
    return h


def status_sisa(s) -> str:
    if s is None:
        return ""
    if s < 0:
        return f'<span class="st-bad">Lewat {-s} hari</span>'
    if s == 0:
        return '<span class="st-warn">Hari ini</span>'
    if s <= 30:
        return f'<span class="st-warn">{s} hari lagi</span>'
    return f'<span class="st-ok">{s} hari lagi</span>'


ATRIBUT = (("merek", "Merek"), ("ukuran", "Ukuran"), ("warna", "Warna"), ("seri", "Nomor seri"))


MASA_SAMPAH = 30   # hari barang disimpan di tempat sampah sebelum hilang permanen


def isi_dari(id_barang: str) -> list:
    """Barang yang disimpan langsung di dalam barang ini (satu tingkat)."""
    return [x for x in D["barang"] if x.get("dalam") == id_barang]


def keturunan(id_barang: str) -> set:
    """Semua barang di dalam barang ini, termasuk isi dari isinya."""
    hasil, antre = set(), [id_barang]
    while antre:
        sekarang_id = antre.pop(0)
        for x in D["barang"]:
            if x.get("dalam") == sekarang_id and x["id"] not in hasil:
                hasil.add(x["id"])
                antre.append(x["id"])
    return hasil


def induk_dari(b: dict):
    return next((x for x in D["barang"] if x["id"] == b.get("dalam")), None) if b.get("dalam") else None


def ikut_induk(x: dict, induk: dict) -> bool:
    """Samakan lokasi barang x dengan barang induknya. True kalau lokasinya berubah."""
    dari = nama_tempat(x)
    x["lokasi"] = induk.get("lokasi", "")
    if induk.get("sublokasi"):
        x["sublokasi"] = induk["sublokasi"]
    else:
        x.pop("sublokasi", None)
    ke = nama_tempat(x)
    if dari == ke:
        return False
    x["diubah"] = hari_ini().isoformat()
    catat(x["id"], x["nama"], dari, ke)
    return True


def sinkron_isi(id_induk: str, lihat=None):
    """Isi barang selalu ikut lokasi induknya, juga isi dari isinya."""
    lihat = lihat if lihat is not None else set()
    if id_induk in lihat:
        return
    lihat.add(id_induk)
    induk = next((x for x in D["barang"] if x["id"] == id_induk), None)
    if not induk:
        return
    for x in isi_dari(id_induk):
        ikut_induk(x, induk)
        sinkron_isi(x["id"], lihat)


def pesan_hapus_barang(b: dict) -> str:
    n = len(isi_dari(b["id"]))
    return (f"Pindahkan {b['nama']} ke tempat sampah?"
            + (f" {n} barang di dalamnya akan dilepas dari barang ini." if n else ""))


def buang_barang(b: dict):
    """Pindahkan barang ke tempat sampah. Barang di dalamnya dilepas dari barang ini."""
    for x in isi_dari(b["id"]):
        x.pop("dalam", None)
    D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
    D["sampah"].append({"id": uuid.uuid4().hex[:8], "barang": dict(b),
                        "dihapus": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama()})


def sisa_sampah(s: dict) -> int:
    """Berapa hari lagi sebelum catatan sampah dihapus permanen."""
    try:
        t = datetime.strptime(s.get("dihapus", ""), "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
        return MASA_SAMPAH - (sekarang() - t).days
    except Exception:
        return MASA_SAMPAH


def teks_cari(b: dict) -> str:
    """Teks yang dicocokkan saat mencari barang, termasuk nama barang induk dan isinya."""
    induk = induk_dari(b)
    return " ".join([b["nama"], b.get("catatan", ""), b.get("tautan", ""), nama_tempat(b), nama_kat(b), b.get("pemilik", ""), b.get("barcode", ""),
                     induk["nama"] if induk else ""] + [b.get(k, "") for k, _ in ATRIBUT]
                    + list(b.get("tag", [])) + [x["nama"] for x in isi_dari(b["id"])]).lower()


def _mirip(t: str, w: str) -> bool:
    """Dua kata dianggap mirip kalau hanya beda satu dua huruf (salah ketik)."""
    if abs(len(t) - len(w)) > 2:
        return False
    if SequenceMatcher(None, t, w).ratio() >= 0.78:
        return True
    return len(w) > len(t) and SequenceMatcher(None, t, w[:len(t)]).ratio() >= 0.85


def skor_cocok(q: str, teks: str) -> int:
    """2 = semua kata pencarian ada di teks, 1 = cocok dengan toleransi salah ketik, 0 = tidak cocok."""
    skor, kata = 2, None
    for t in q.split():
        if t in teks:
            continue
        if len(t) < 4:                      # kata pendek harus persis, supaya tidak ngawur
            return 0
        if kata is None:
            kata = set(re.findall(r"\w+", teks))
        if any(_mirip(t, w) for w in kata):
            skor = 1
        else:
            return 0
    return skor


def saring_barang(daftar: list, q: str):
    """Barang yang cocok dengan pencarian. Yang cocok persis lebih dulu, lalu yang mirip.
    Mengembalikan (hasil, jumlah_yang_hanya_mirip)."""
    if not q:
        return list(daftar), 0
    tepat, mirip = [], []
    for b in daftar:
        sk = skor_cocok(q, teks_cari(b))
        if sk == 2:
            tepat.append(b)
        elif sk == 1:
            mirip.append(b)
    return tepat + mirip, len(mirip)


def daftar_pemilik() -> list:
    return sorted({b["pemilik"] for b in D["barang"] if b.get("pemilik")} | set(D.get("pemilik_daftar", [])), key=str.lower)


def daftar_tag() -> list:
    return sorted({t for b in D["barang"] for t in b.get("tag", [])} | set(D.get("label_daftar", [])), key=str.lower)


def perbarui_terdaftar(kunci: str, lama: str, baru=None):
    """Ikutkan perubahan nama (atau penghapusan kalau baru kosong) ke daftar yang ditambah manual."""
    d = D.get(kunci, [])
    d = [baru if x == lama else x for x in d] if baru else [x for x in d if x != lama]
    D[kunci] = list(dict.fromkeys(d))


def tombol_tambah(kunci: str, label: str) -> bool:
    """Form tambah baru baru muncul setelah tombolnya ditekan."""
    if st.session_state.get(f"tb_{kunci}"):
        return True
    st.button(label, key=f"tbtn_{kunci}", icon=":material/add:", type="primary", on_click=atur, args=(f"tb_{kunci}", True))
    return False


def tutup_tambah(kunci: str):
    st.session_state[f"tb_{kunci}"] = False
    st.rerun()


RE_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _url_aman(u: str) -> str:
    """Buang tanda baca di ujung tautan dan pastikan skemanya http(s)."""
    u = u.rstrip(".,;:!?)]}")
    return u if u.lower().startswith(("http://", "https://")) else ""


def html_tautan(teks: str) -> str:
    """Escape teks, lalu ubah alamat web di dalamnya jadi tautan yang bisa diklik."""
    keluar, pos = [], 0
    for m in RE_URL.finditer(teks or ""):
        u = _url_aman(m.group(0))
        if not u:
            continue
        akhir = m.start() + len(u)
        keluar.append(html.escape(teks[pos:m.start()]))
        keluar.append(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(u)}</a>')
        pos = akhir
    keluar.append(html.escape((teks or "")[pos:]))
    return "".join(keluar)


def daftar_tautan(b: dict) -> list:
    """Alamat web dari field tautan barang (satu per baris), tanpa duplikat."""
    hasil = []
    for m in RE_URL.finditer(b.get("tautan", "") or ""):
        u = _url_aman(m.group(0))
        if u and u not in hasil:
            hasil.append(u)
    return hasil


def label_tautan(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", u, flags=re.IGNORECASE).split("/")[0][:40] or u


def html_daftar_tautan(b: dict) -> str:
    return " · ".join(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">'
                      f'{html.escape(label_tautan(u))}</a>' for u in daftar_tautan(b))


def _norm_nama(s: str) -> str:
    return " ".join((s or "").lower().split())


def cari_serupa(nama: str, kecuali: str = "") -> list:
    """Barang lain yang namanya sama atau sangat mirip dengan `nama` (untuk peringatan sebelum menambah)."""
    n = _norm_nama(nama)
    if not n:
        return []
    hasil = []
    for b in D["barang"]:
        if b["id"] == kecuali:
            continue
        w = _norm_nama(b["nama"])
        if w == n or (len(n) >= 4 and len(w) >= 4 and (n in w or w in n)) or _mirip(n, w):
            hasil.append(b)
    return hasil


def peringatan_serupa(nama: str, kecuali: str = "") -> bool:
    """True kalau penyimpanan sebaiknya ditunda: ada barang serupa dan pengguna belum mengonfirmasi.
    Konfirmasinya: menekan tombol simpan lagi dengan nama yang sama."""
    serupa = cari_serupa(nama, kecuali)
    if not serupa or st.session_state.get("serupa_ok") == _norm_nama(nama):
        return False
    st.session_state.serupa_ok = _norm_nama(nama)
    daftar = ", ".join(f"{b['nama']} ({nama_tempat(b)})" for b in serupa[:3]) + (
        f" dan {len(serupa) - 3} lainnya" if len(serupa) > 3 else "")
    st.warning(f"Sudah ada barang yang mirip: {daftar}. Kalau memang barang yang berbeda, "
               "tekan tombol simpan sekali lagi untuk tetap menambahkan.")
    return True


MAKS_GALERI = 6


KONDISI = {"rusak": "Rusak", "servis": "Sedang diservis"}


MAKS_LAMPIRAN, MAKS_LAMPIRAN_MB = 5, 5


def semua_berkas(b: dict) -> list:
    """Semua path berkas barang: foto, foto tambahan, dan lampiran dokumen."""
    return semua_foto(b) + [x["path"] for x in b.get("lampiran", []) if x.get("path")]


def semua_foto(b: dict) -> list:
    """Semua path foto sebuah barang: foto utama, lalu foto tambahan."""
    return ([b["foto"]] if b.get("foto") else []) + list(b.get("galeri", []))


def tampil_lampiran(b: dict):
    """Tombol unduh untuk dokumen terlampir (nota, manual, kartu garansi)."""
    for x in b.get("lampiran", []):
        dat = ambil_foto(x.get("path", ""))
        if not dat:
            continue
        st.session_state["_n_lamp"] = st.session_state.get("_n_lamp", 0) + 1
        st.download_button(f"📄 {x.get('nama', 'dokumen')}", dat, file_name=x.get("nama", "dokumen.pdf"),
                           mime="application/pdf", key=f"dl_lamp_{st.session_state['_n_lamp']}", use_container_width=True)


def tampil_galeri(b: dict):
    """Lipatan 'Lihat N foto' kalau barang punya lebih dari satu foto."""
    fs = semua_foto(b)
    if len(fs) < 2:
        return
    with st.expander(f"Lihat {len(fs)} foto"):
        kol = st.columns(2)
        for i, p in enumerate(fs):
            dat = ambil_foto(p)
            if dat:
                kol[i % 2].image(dat, use_container_width=True)


def catat(id_barang: str, nama: str, dari: str, ke: str):
    """Tambah catatan riwayat perpindahan."""
    D["riwayat"].append({"id": uuid.uuid4().hex[:8], "barang": id_barang, "nama": nama, "dari": dari, "ke": ke,
                         "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama()})
    if len(D["riwayat"]) > MAKS_RIWAYAT:
        D["riwayat"] = D["riwayat"][-MAKS_RIWAYAT:]


def tampil_foto_kecil(b: dict, kolom):
    dat = ambil_foto(b.get("foto", "")) if b.get("foto") else None
    if dat:
        kolom.image(dat, width=64)
    else:
        kolom.write("")


@st.cache_data(show_spinner=False, max_entries=300)
def _uri_bulat(path: str, dat: bytes) -> str:
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(dat))).convert("RGB")
    im = ImageOps.fit(im, (104, 104))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def html_nama_foto(x: dict) -> str:
    """Nama lokasi/sub lokasi, dengan foto bulat kecil di kirinya kalau ada."""
    nama = html.escape(x["nama"])
    dat = ambil_foto(x["foto"]) if x.get("foto") else None
    if dat:
        try:
            return (f'<div class="itm"><div class="ic"><img src="{_uri_bulat(x["foto"], dat)}" alt=""></div>'
                    f'<div class="isi"><div class="jd" style="font-weight:600">{nama}</div></div></div>')
        except Exception:
            pass
    return f'<div style="padding:.3rem 0">{nama}</div>'


SEKSI_KARTU = [("lokasi", "Lokasi"), ("kategori", "Kategori"), ("harga", "Harga setelah diskon (harga yang dibayar)"),
               ("harga_asli", "Harga asli (sebelum diskon) dan persen diskon"),
               ("jumlah", "Jumlah (angka besar di kanan)"), ("tanggal", "Tanggal (dibeli, kedaluwarsa, garansi, dipakai, diinventarisasi)"),
               ("pemilik", "Pemilik"), ("atribut", "Merek, ukuran, warna, nomor seri"),
               ("hubungan", "Di dalam atau berisi barang lain"), ("catatan", "Catatan"), ("tautan", "Tautan"), ("label", "Label")]


COOKIE_KARTU = "barang_kartu"


def muat_kartu_sembunyi() -> set:
    """Bagian kartu barang yang disembunyikan. Pilihan diingat di perangkat ini lewat cookie."""
    if "kartu_sembunyi" not in st.session_state:
        try:
            ck = st.context.cookies.get(COOKIE_KARTU)
        except Exception:
            ck = None
        if not isinstance(ck, str):            # perangkat ini belum punya pilihan sendiri: pakai bawaan bersama
            ck = ",".join(D.get("pengaturan", {}).get("kartu", []))
        sah = {k for k, _ in SEKSI_KARTU}
        st.session_state.kartu_sembunyi = [k for k in ck.split(",") if k in sah]
    return set(st.session_state.kartu_sembunyi)


def ubah_kartu():
    st.session_state.kartu_sembunyi = [k for k, _ in SEKSI_KARTU if not st.session_state.get(f"ks_{k}", True)]
    st.session_state.kartu_ubah = True


def atur_kartu(sembunyi: list):
    for k, _ in SEKSI_KARTU:
        st.session_state[f"ks_{k}"] = k not in sembunyi
    ubah_kartu()


def _rp_titik(n: int) -> str:
    return "Rp " + f"{n:,}".replace(",", ".")


def _teks_harga(b: dict, tampil_beli: bool, tampil_asli: bool) -> str:
    """Teks harga di kartu: setelah diskon saja, asli saja, atau keduanya (dengan persen diskon)."""
    beli, asli = harga_b(b), harga_asli_b(b)
    if not (beli or asli):
        return ""
    if tampil_beli and tampil_asli:
        if beli and asli and diskon_persen(b):
            return f"{_rp_titik(beli)} (asli {_rp_titik(asli)}, diskon {diskon_persen(b)}%)"
        return _rp_titik(beli or asli)
    if tampil_beli:
        return _rp_titik(beli) if beli else ""
    if tampil_asli:
        return _rp_titik(asli or beli)       # tanpa harga asli, harga yang dibayar dianggap harga asli
    return ""


def kartu_barang_html(b: dict, foto: bool = True) -> str:
    """Satu kartu barang: ikon/foto bulat, nama, keterangan, jumlah besar di kanan."""
    sb = muat_kartu_sembunyi()
    ic = html.escape((b["nama"].strip()[:1] or "?").upper())
    if foto and b.get("foto"):
        dat = ambil_foto(b["foto"])
        if dat:
            try:
                ic = f'<img src="{_uri_bulat(b["foto"], dat)}" alt="">'
            except Exception:
                pass
    meta = [nama_tempat(b) + (f" › {b['petak']}" if b.get("petak") else "")] if "lokasi" not in sb else []
    if b.get("kategori") and "kategori" not in sb:
        meta.append(nama_kat(b))
    teks_h = _teks_harga(b, "harga" not in sb, "harga_asli" not in sb)
    if teks_h:
        meta.append(teks_h)
    ekstra = []
    if b.get("dibeli") and "tanggal" not in sb:
        ekstra.append(f"Dibeli: {fmt_iso(b['dibeli'])}")
    for lab, kunci in (("Kedaluwarsa", "kedaluwarsa"), ("Garansi", "garansi")):
        s = sisa_hari(b.get(kunci))
        if s is not None and "tanggal" not in sb:
            ekstra.append(f"{lab}: {status_sisa(s)}")
    if b.get("dipakai") and "tanggal" not in sb:
        ekstra.append(f"Dipakai: {fmt_iso(b['dipakai'])}")
    if b.get("pemilik") and "pemilik" not in sb:
        ekstra.append(f"Milik: {html.escape(b['pemilik'])}")
    if b.get("dibawa"):
        ekstra.append(f"Dibawa sejak {fmt_iso(b['dibawa'])}"
                      + (f" ke {html.escape(b['dibawa_ke'])}" if b.get("dibawa_ke") else ""))
    if b.get("hilang"):
        ekstra.append(f"Hilang sejak {fmt_iso(b['hilang'])}"
                      + (f", terakhir terlihat di {html.escape(b['hilang_di'])}" if b.get("hilang_di") else ""))
    atr = [f"{lab}: {html.escape(b[k])}" for k, lab in ATRIBUT if b.get(k)]
    if atr and "atribut" not in sb:
        ekstra.append(" · ".join(atr))
    induk = induk_dari(b)
    if induk and "hubungan" not in sb:
        ekstra.append(f"Di dalam: {html.escape(induk['nama'])}")
    isi = isi_dari(b["id"])
    if isi and "hubungan" not in sb:
        ekstra.append("Berisi: " + html.escape(", ".join(x["nama"] for x in isi[:5]))
                      + (f" +{len(isi) - 5} lagi" if len(isi) > 5 else ""))
    cat = ""
    if b.get("catatan") and "catatan" not in sb:
        cat += f'<div class="cat">{html_tautan(b["catatan"])}</div>'
    if daftar_tautan(b) and "tautan" not in sb:
        cat += f'<div class="cat">Tautan: {html_daftar_tautan(b)}</div>'
    if b.get("tag") and "label" not in sb:
        cat += '<div class="cat">' + "".join(f'<span class="tag">{html.escape(t)}</span>' for t in b["tag"]) + '</div>'
    if b.get("opname") and "tanggal" not in sb:
        ekstra.append(f"Diinventarisasi: {fmt_iso(b['opname'])}")
    if ekstra:
        cat += f'<div class="cat">{" · ".join(ekstra)}</div>'
    merah = " merah" if perlu_beli(b) else ""
    mt = f'<div class="mt">{html.escape(" • ".join(meta))}</div>' if meta else ""
    qt = (f'<div class="qt"><b class="{merah.strip()}">{jumlah_b(b)}</b><span>buah</span></div>'
          if "jumlah" not in sb else "")
    return (f'<div class="itm"><div class="ic">{ic}</div><div class="isi">'
            f'<div class="jd">{html.escape(b["nama"])}{lencana(b)}</div>{mt}{cat}</div>{qt}</div>')


def kumpul_perhatian():
    """Daftar hal yang perlu diperhatikan: (kelas, teks html)."""
    def daftar(nama_nama, maks=5):
        n = [html.escape(x) for x in nama_nama[:maks]]
        lebih = len(nama_nama) - maks
        return ", ".join(n) + (f" dan {lebih} lainnya" if lebih > 0 else "")

    exp_lewat, exp_dekat, gar_dekat = [], [], []
    for b in D["barang"]:
        s = sisa_hari(b.get("kedaluwarsa"))
        if s is not None:
            if s < 0:
                exp_lewat.append(b["nama"])
            elif s <= 30:
                exp_dekat.append(b["nama"])
        g = sisa_hari(b.get("garansi"))
        if g is not None and 0 <= g <= 30:
            gar_dekat.append(b["nama"])
    telat = []
    for p in D["pinjam"]:
        s = sisa_hari(p.get("tenggat"))
        if not p.get("kembali") and s is not None and s < 0:
            telat.append(f"{p.get('nama', '')} ({p.get('orang', '')})")
    beli = [b["nama"] for b in D["barang"] if perlu_beli(b)]
    hasil = []
    if exp_lewat:
        hasil.append(f"⛔ <b>Sudah kedaluwarsa:</b> {daftar(exp_lewat)}")
    if exp_dekat:
        hasil.append(f"⏰ <b>Kedaluwarsa dalam 30 hari:</b> {daftar(exp_dekat)}")
    if gar_dekat:
        hasil.append(f"🛡️ <b>Garansi berakhir dalam 30 hari:</b> {daftar(gar_dekat)}")
    if telat:
        hasil.append(f"🔁 <b>Pinjaman lewat tenggat:</b> {daftar(telat)}")
    if beli:
        hasil.append(f"🛒 <b>Perlu dibeli:</b> {daftar(beli)}")
    return hasil
