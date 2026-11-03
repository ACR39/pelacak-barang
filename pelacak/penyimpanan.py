"""Penyimpanan data (GitHub atau file lokal), versi data, riwayat aktivitas otomatis, dan penyimpanan foto."""
import base64
import io
import json
import os
import time
import uuid
from datetime import datetime, timezone

import requests
import streamlit as st

from pelacak.inti import (
    FILE_LOKAL, FOTO_LOKAL, Image, ImageOps, MAKS_AKTIVITAS, WIB, cfg_github, data_kosong,
    fmt_iso, konversi_lama, pengguna_nama, sekarang, teks_cek, teks_ganti,
)


# ---------------------------------------------------------------- penyimpanan
class Bentrok(Exception):
    """Data di GitHub sudah berubah sejak terakhir dimuat."""


def _gh_url(c, path=None):
    return f"https://api.github.com/repos/{c['repo']}/contents/{path or c['path']}"


def _gh_headers(c):
    return {"Authorization": f"Bearer {c['token']}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def muat():
    """Kembalikan (data, sha). sha dipakai GitHub untuk mendeteksi bentrok."""
    c = cfg_github()
    if c:
        r = requests.get(_gh_url(c), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
        if r.status_code == 404:
            return data_kosong(), None
        r.raise_for_status()
        j = r.json()
        isi = json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        return (konversi_lama(isi) if isinstance(isi, list) else isi), j["sha"]
    if os.path.exists(FILE_LOKAL):
        with open(FILE_LOKAL, encoding="utf-8") as f:
            isi = json.load(f)
        return (konversi_lama(isi) if isinstance(isi, list) else isi), None
    return data_kosong(), None


def simpan(data: dict, pesan: str = "Perbarui data barang"):
    c = cfg_github()
    teks = json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)
    if c:
        body = {"message": pesan, "branch": c["branch"],
                "content": base64.b64encode(teks.encode("utf-8")).decode("ascii")}
        if st.session_state.sha:
            body["sha"] = st.session_state.sha
        r = requests.put(_gh_url(c), headers=_gh_headers(c), json=body, timeout=30)
        if r.status_code in (409, 422):
            raise Bentrok()
        r.raise_for_status()
        st.session_state.sha = r.json()["content"]["sha"]
    else:
        with open(FILE_LOKAL, "w", encoding="utf-8") as f:
            f.write(teks)
        try:                                   # salinan tiap versi, untuk Titik pulih
            dv = FILE_LOKAL + ".versi"
            os.makedirs(dv, exist_ok=True)
            nama_v = sekarang().strftime("%Y%m%d-%H%M%S-%f") + ".json"
            with open(os.path.join(dv, nama_v), "w", encoding="utf-8") as f:
                json.dump({"waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "pesan": pesan, "data": data},
                          f, ensure_ascii=False)
            for lama_v in sorted(os.listdir(dv))[:-30]:
                os.remove(os.path.join(dv, lama_v))
        except Exception:
            pass


def daftar_versi(batas: int = 30) -> list:
    """Versi data sebelumnya, terbaru dulu: [{id, waktu 'YYYY-MM-DD HH:MM' (WIB), pesan}]."""
    c = cfg_github()
    if c:
        r = requests.get(f"https://api.github.com/repos/{c['repo']}/commits", headers=_gh_headers(c),
                         params={"path": c["path"], "sha": c["branch"], "per_page": batas}, timeout=30)
        r.raise_for_status()
        hasil = []
        for x in r.json():
            t = datetime.strptime(x["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ")
            wkt = t.replace(tzinfo=timezone.utc).astimezone(WIB).strftime("%Y-%m-%d %H:%M")
            hasil.append({"id": x["sha"], "waktu": wkt, "pesan": x["commit"]["message"].split("\n")[0]})
        return hasil
    dv = FILE_LOKAL + ".versi"
    if not os.path.isdir(dv):
        return []
    hasil = []
    for n in sorted(os.listdir(dv), reverse=True)[:batas]:
        try:
            with open(os.path.join(dv, n), encoding="utf-8") as f:
                j = json.load(f)
            hasil.append({"id": n, "waktu": j.get("waktu", ""), "pesan": j.get("pesan", "")})
        except Exception:
            continue
    return hasil


@st.cache_data(show_spinner=False, max_entries=20)
def _versi_gh(sha: str, repo: str, path: str, token: str):
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/{path}", timeout=40,
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                              "X-GitHub-Api-Version": "2022-11-28"}, params={"ref": sha})
    r.raise_for_status()
    return json.loads(r.content.decode("utf-8"))


def ambil_versi(id_versi: str) -> dict:
    c = cfg_github()
    if c:
        isi = _versi_gh(id_versi, c["repo"], c["path"], c["token"])
        return konversi_lama(isi) if isinstance(isi, list) else isi
    with open(os.path.join(FILE_LOKAL + ".versi", os.path.basename(id_versi)), encoding="utf-8") as f:
        return json.load(f)["data"]


def muat_ke_sesi():
    st.session_state.data, st.session_state.sha = muat()


LABEL_FIELD = {"nama": "Nama", "jumlah": "Jumlah", "kategori": "Kategori", "lokasi": "Lokasi",
               "sublokasi": "Sub lokasi", "catatan": "Catatan", "harga": "Harga setelah diskon", "harga_asli": "Harga asli", "dibeli": "Tanggal beli", "kedaluwarsa": "Kedaluwarsa",
               "garansi": "Garansi", "habis": "Perlu beli", "minimum": "Stok minimum", "dalam": "Di dalam",
               "foto": "Foto", "dipakai": "Dipakai", "merek": "Merek", "ukuran": "Ukuran", "warna": "Warna",
               "seri": "Nomor seri", "pemilik": "Pemilik", "galeri": "Foto tambahan", "petak": "Petak", "barcode": "Barcode",
               "cek_tiap": "Cek berkala", "cek_terakhir": "Terakhir dicek", "toko": "Beli di", "nota": "Nomor nota",
               "ganti_tiap": "Pengingat ganti", "diganti": "Terakhir diganti",
               "dibawa": "Sedang dibawa sejak", "dibawa_ke": "Dibawa ke", "hilang": "Hilang sejak",
               "hilang_di": "Terakhir terlihat di", "tautan": "Tautan", "opname": "Terakhir diinventarisasi", "favorit": "Favorit", "tag": "Label"}


def ambil_snap() -> dict:
    """Foto keadaan data di awal proses, untuk dibandingkan saat menyimpan."""
    d = st.session_state.data
    return {"barang": {b["id"]: dict(b) for b in d["barang"]},
            "sampah": {x["barang"]["id"]: x["barang"].get("nama", "") for x in d.get("sampah", [])}}


def _tampil_nilai(d: dict, kunci: str, v, nama_barang: dict | None = None) -> str:
    if kunci == "habis":
        return "ya" if v else "tidak"
    if v is None or v == "" or v is False:
        return "kosong"
    if v is True:
        return "ya"
    if kunci == "dalam":
        return (nama_barang or {}).get(v, "(barang yang sudah dihapus)")
    peta = {"kategori": d.get("kategori", []), "lokasi": d.get("lokasi", []), "sublokasi": d.get("sublokasi", [])}
    if kunci in peta:
        return next((x["nama"] for x in peta[kunci] if x["id"] == v), "(sudah dihapus)")
    if kunci == "foto":
        return "ada"
    if kunci in ("harga", "harga_asli"):
        return "Rp " + f"{int(v):,}".replace(",", ".")
    if kunci == "galeri":
        return f"{len(v)} foto" if v else "kosong"
    if kunci == "tag":
        return ", ".join(v) if v else "kosong"
    if kunci == "cek_tiap":
        return teks_cek(v)
    if kunci == "ganti_tiap":
        return teks_ganti(v)
    if kunci in ("kedaluwarsa", "garansi", "dipakai", "dibeli", "dibawa", "hilang", "cek_terakhir", "diganti"):
        return fmt_iso(str(v))
    t = str(v).replace("\n", " ")
    return t if len(t) <= 40 else t[:39] + "…"


def catat_aktivitas():
    """Bandingkan data sekarang dengan keadaan di awal proses, lalu catat apa yang berubah."""
    snap = st.session_state.get("_snap")
    if not snap:
        return
    d = st.session_state.data
    lama, baru = snap["barang"], {b["id"]: b for b in d["barang"]}
    sampah_baru = {x["barang"]["id"] for x in d.get("sampah", [])}
    log = d.setdefault("aktivitas", [])
    nama_b = {i: b.get("nama", "") for i, b in lama.items()}
    nama_b.update({i: b["nama"] for i, b in baru.items()})
    waktu, oleh = sekarang().strftime("%Y-%m-%d %H:%M"), pengguna_nama()

    def tambah(jenis, id_, nama, rincian="", perubahan=None):
        log.append({"id": uuid.uuid4().hex[:8], "waktu": waktu, "oleh": oleh, "jenis": jenis,
                    "barang": id_, "nama": nama, "rincian": rincian})
        if perubahan:
            log[-1]["perubahan"] = perubahan

    for i, b in baru.items():
        if i not in lama:
            tambah("pulih" if i in snap["sampah"] else "tambah", i, b["nama"])
            continue
        bagian, perub = [], []
        for k in sorted(set(lama[i]) | set(b), key=lambda x: list(LABEL_FIELD).index(x) if x in LABEL_FIELD else 99):
            if k in ("id", "diubah"):
                continue
            lv, bv = lama[i].get(k), b.get(k)
            lv = "" if lv is None or lv is False else lv
            bv = "" if bv is None or bv is False else bv
            if lv != bv:
                bagian.append(f"{LABEL_FIELD.get(k, k.capitalize())}: {_tampil_nilai(d, k, lv, nama_b)} → {_tampil_nilai(d, k, bv, nama_b)}")
                if k not in ("foto", "galeri", "lampiran", "perawatan"):
                    perub.append({"k": k, "dari": lv, "ke": bv})
        if bagian:
            tambah("ubah", i, b["nama"], "; ".join(bagian), perub)
    for i, b in lama.items():
        if i not in baru and i in sampah_baru:
            tambah("buang", i, b["nama"])
    for i, nama in snap["sampah"].items():
        if i not in sampah_baru and i not in baru:
            tambah("hapus", i, nama, "dihapus permanen dari tempat sampah")
    if len(log) > MAKS_AKTIVITAS:
        d["aktivitas"] = log[-MAKS_AKTIVITAS:]


def commit(pesan_ok: str | None = None) -> bool:
    """Simpan st.session_state.data. Tampilkan hasilnya ke pengguna."""
    try:
        catat_aktivitas()
    except Exception:
        pass            # pencatatan riwayat tidak boleh menggagalkan penyimpanan
    pesan = f"{pesan_ok or 'Perbarui data barang'} (oleh {pengguna_nama()})"
    try:
        simpan(st.session_state.data, pesan)
    except Bentrok:
        muat_ke_sesi()
        st.error("Data sudah diubah dari tempat lain. Data terbaru sudah dimuat, "
                 "silakan ulangi perubahan Anda.")
        return False
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")
        return False
    if pesan_ok:
        st.toast(pesan_ok, icon="✅")
    return True


# ----------------------------------------------------------------------- foto
def proses_foto(mentah: bytes) -> bytes:
    """Kecilkan foto (maks 900 px) dan simpan sebagai JPEG supaya repositori tidak cepat besar."""
    if Image is None:
        raise RuntimeError("Pustaka Pillow belum terpasang.")
    if len(mentah) > 15 * 1024 * 1024:
        raise ValueError("Ukuran foto terlalu besar (maksimal 15 MB).")
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    im.thumbnail((900, 900))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=78, optimize=True)
    return out.getvalue()


def simpan_foto(id_barang: str, mentah: bytes) -> str:
    """Simpan foto, kembalikan path-nya. Nama file unik supaya tidak perlu menimpa."""
    return _tulis_foto(id_barang, proses_foto(mentah))


def _tulis_foto(id_barang: str, isi: bytes, ext: str = "jpg") -> str:
    """Tulis berkas foto yang sudah jadi ke penyimpanan, kembalikan path-nya."""
    path = f"foto/{id_barang}_{int(time.time())}{uuid.uuid4().hex[:4]}.{ext}"
    c = cfg_github()
    if c:
        body = {"message": f"Foto barang {id_barang}", "branch": c["branch"],
                "content": base64.b64encode(isi).decode("ascii")}
        r = requests.put(_gh_url(c, path), headers=_gh_headers(c), json=body, timeout=40)
        r.raise_for_status()
    else:
        os.makedirs(FOTO_LOKAL, exist_ok=True)
        with open(os.path.join(FOTO_LOKAL, os.path.basename(path)), "wb") as f:
            f.write(isi)
    return path


def hapus_foto(path: str):
    """Hapus file foto lama. Kalau gagal dibiarkan saja, tidak mengganggu data."""
    if not path:
        return
    try:
        c = cfg_github()
        if c:
            r = requests.get(_gh_url(c, path), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
            if r.status_code == 200:
                requests.delete(_gh_url(c, path), headers=_gh_headers(c), timeout=30,
                                json={"message": "Hapus foto lama", "sha": r.json()["sha"], "branch": c["branch"]})
        else:
            os.remove(os.path.join(FOTO_LOKAL, os.path.basename(path)))
    except Exception:
        pass


@st.cache_data(show_spinner=False, max_entries=300)
def _foto_gh(path: str, repo: str, branch: str, token: str):
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/{path}", timeout=20,
                     headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json",
                              "X-GitHub-Api-Version": "2022-11-28"}, params={"ref": branch})
    return r.content if r.status_code == 200 else None


def ambil_foto(path: str):
    """Isi foto (bytes) atau None kalau tidak ditemukan."""
    if not path:
        return None
    try:
        c = cfg_github()
        if c:
            return _foto_gh(path, c["repo"], c["branch"], c["token"])
        with open(os.path.join(FOTO_LOKAL, os.path.basename(path)), "rb") as f:
            return f.read()
    except Exception:
        return None
