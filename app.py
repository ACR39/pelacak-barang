"""Pelacak Barang Pribadi (Streamlit).

Mencatat di mana barang pribadi disimpan (lokasi dan sub lokasi) dan memudahkan
pencarian. Data disimpan sebagai satu file JSON di repositori GitHub (disarankan
repositori privat terpisah), foto disimpan di folder foto/ pada repositori yang sama.
Kalau pengaturan GitHub tidak ada, aplikasi memakai file lokal untuk uji coba.
"""
import base64
import hashlib
import hmac
import html
import io
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

try:
    import segno
except Exception:          # pustaka label QR belum terpasang
    segno = None
try:
    from PIL import Image, ImageOps
except Exception:          # Pillow belum terpasang
    Image = ImageOps = None

st.set_page_config(page_title="Pelacak Barang", page_icon="📦", layout="wide")

st.markdown("""
<style>
.block-container{padding:1rem 2rem 4rem;max-width:1600px}
[data-testid="stToolbarActions"],[data-testid="stMainMenu"],[data-testid="stAppDeployButton"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none !important}
[data-testid="stHeader"]{background:transparent}
.eyebrow{font-size:.72rem;font-weight:700;letter-spacing:.09em;color:#2b7a57}
.judul-hal{font-size:1.6rem;font-weight:700;color:#111827;margin:.1rem 0 .15rem;letter-spacing:-.01em}
.kepala{display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;
  background:#fff;border:1px solid #e5e7eb;border-left:4px solid #2b7a57;border-radius:12px;
  padding:1rem 1.3rem;margin:0 0 1.4rem;box-shadow:0 1px 3px rgba(15,23,42,.05)}
.kepala .desk{font-size:.86rem;color:#64748b;max-width:62ch}
.pengguna{display:flex;align-items:center;gap:.6rem;background:#f1f5f9;border-radius:999px;padding:.35rem .9rem .35rem .4rem}
.pengguna .av{width:30px;height:30px;border-radius:50%;background:linear-gradient(135deg,#34a874,#1f6b49);
  color:#fff;font-weight:700;font-size:.85rem;display:flex;align-items:center;justify-content:center}
.pengguna .nm{font-size:.84rem;font-weight:600;color:#0f172a;line-height:1.15}
.pengguna .pr{font-size:.7rem;color:#64748b;text-transform:capitalize}
.pengguna.sb{background:rgba(255,255,255,.07);margin:.2rem 0 .6rem;border-radius:12px;padding:.5rem .7rem .5rem .5rem}
[data-testid="stSidebar"] .pengguna.sb .nm{color:#fff;font-size:.88rem}
[data-testid="stSidebar"] .pengguna.sb .pr{color:#94a3b8}
[data-testid="stSidebar"]{background:#0b1220}
[data-testid="stSidebar"] *{color:#e5e7eb}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#94a3b8}
.brand{display:flex;align-items:center;gap:.7rem;padding:.3rem .2rem 1.1rem;border-bottom:1px solid rgba(255,255,255,.08);margin-bottom:.4rem}
.brand .b1{font-weight:700;font-size:1.05rem;color:#fff;line-height:1.2}
.brand .b2{font-size:.76rem;color:#94a3b8;margin-top:.1rem}
.sp{height:1.2rem}
.grup{font-size:.66rem;font-weight:700;letter-spacing:.12em;color:#64748b;margin:1rem 0 .35rem .3rem}
[data-testid="stSidebar"] [data-testid="stExpander"]{background:transparent;border:0;box-shadow:none;margin-bottom:.2rem}
[data-testid="stSidebar"] [data-testid="stExpander"] details{border:0}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{font-weight:600;font-size:.92rem;padding:.55rem .5rem;border-radius:8px;background:transparent !important;color:#e5e7eb !important}
[data-testid="stSidebar"] [data-testid="stExpander"] details[open] > summary,[data-testid="stSidebar"] [data-testid="stExpander"] summary:focus,[data-testid="stSidebar"] [data-testid="stExpander"] summary:active{background:transparent !important}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.06) !important}
[data-testid="stSidebar"] [data-testid="stExpanderDetails"]{padding:.1rem 0 .3rem .5rem;border-left:1px solid rgba(255,255,255,.1);margin-left:1rem}
[class*="st-key-nav_"] button{justify-content:flex-start !important;text-align:left !important;border:0 !important;
  border-radius:8px;min-height:2.4rem;background:transparent !important;color:#cbd5e1 !important;
  font-weight:500;font-size:.9rem;box-shadow:inset 3px 0 0 transparent}
[class*="st-key-nav_"] button:hover{background:rgba(255,255,255,.06) !important;color:#fff !important}
[class*="st-key-nav_"] button[kind="primary"]{background:rgba(52,168,116,.18) !important;color:#fff !important;
  font-weight:600;box-shadow:inset 3px 0 0 #34d399}
[class*="st-key-nav_"] button > div,[class*="st-key-nav_"] button [data-testid="stMarkdownContainer"],
[class*="st-key-nav_"] button p{text-align:left !important;justify-content:flex-start !important}
[class*="st-key-nav_muat"] button{border:1px solid rgba(255,255,255,.12) !important;justify-content:center !important}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"]{background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  padding:1.1rem 1.2rem;box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.9rem}
[data-testid="stExpander"]{background:#fff;border-radius:14px !important;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.statcard{display:flex;flex-wrap:wrap;background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin:.2rem 0 .6rem;overflow:hidden}
.sc-kiri{flex:2 1 280px;padding:1rem 1.2rem}
.sc-judul{font-size:1.35rem;font-weight:800;color:#111827;margin-top:.5rem}
.sc-ket{font-size:.85rem;color:#6b7280;margin-top:.15rem}
.tag{display:inline-block;background:#e8f3ec;color:#1f6b49;font-size:.72rem;font-weight:700;border-radius:999px;
  padding:.15rem .65rem;margin-right:.4rem}
.tag-m{background:#fff4d6;color:#8a5a00}
.sc-stat{flex:1 1 90px;border-left:1px solid #eef0f4;text-align:center;padding:1rem .4rem}
.sc-lab{font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#6b7280}
.sc-val{font-size:1.7rem;font-weight:800;color:#111827;margin-top:.2rem}
.sc-val.g{color:#166534}.sc-val.m{color:#b42318}
[data-testid="stMetric"]{border:1px solid #d9dee7;border-radius:8px;padding:.8rem 1rem;background:#fff}
[data-testid="stForm"]{border-radius:8px;border-color:#d9dee7;background:#fff}
[data-testid="InputInstructions"]{display:none}
.thead-s{background:#256b4a;color:#fff;font-weight:650;font-size:.7rem;letter-spacing:.03em;text-transform:uppercase;text-align:center;padding:.3rem .25rem;border-radius:4px;height:3rem;min-height:3rem;box-sizing:border-box;line-height:1.15;display:flex;align-items:center;justify-content:center}
[class*="st-key-bredit_"] button,[class*="st-key-brhapus_"] button{min-height:2rem;padding:.1rem .5rem;border:0 !important;color:#fff !important}
[class*="st-key-bredit_"] button{background:#2f5d9e !important}
[class*="st-key-brhapus_"] button{background:#b42318 !important}
.garis{border-top:1px solid #e3e7ee;margin:.3rem 0}
.brg{font-weight:650}
.sub{font-size:.85rem;color:#5b6573}
.bidang{font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#256b4a;background:#e8f3ec;border-left:3px solid #256b4a;padding:.35rem .7rem;border-radius:4px;margin:1rem 0 .4rem}
.st-ok{color:#166534;font-weight:600}.st-warn{color:#8a5a00;font-weight:600}.st-bad{color:#b42318;font-weight:600}
.lencana{display:inline-block;font-size:.66rem;font-weight:700;border-radius:999px;padding:.05rem .5rem;margin-left:.4rem;vertical-align:middle}
.lc-m{background:#fff4d6;color:#8a5a00}.lc-r{background:#fde8e6;color:#b42318}.lc-b{background:#e6eefb;color:#2f5d9e}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"],.statcard,.kepala,[data-testid="stForm"]{color:#111827 !important}
.kepala .desk,.sc-ket,.sc-lab,.eyebrow{color:#475569 !important}
.perhatian{padding:.45rem 0;border-bottom:1px solid #eef0f4;font-size:.92rem;color:#1f2937}
.perhatian:last-child{border-bottom:0}
@media (max-width:768px){
  .block-container{padding:3rem 1rem 4rem}
  .kepala{padding:.9rem 1rem}
  .judul-hal{font-size:1.35rem}
}
/* Di HP tabel tidak ditumpuk ke bawah, tapi dilebarkan dan bisa digeser ke samping */
@media (max-width:640px){
  .st-key-kartu_tabel,.st-key-kartu_barang,[class*="st-key-kartu_tgl"]{overflow-x:auto;-webkit-overflow-scrolling:touch}
  [data-testid="stHorizontalBlock"]:has(.brg),[data-testid="stHorizontalBlock"]:has(.thead-s){flex-wrap:nowrap !important;min-width:780px}
  [data-testid="stHorizontalBlock"]:has(.brg) > [data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has(.thead-s) > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;min-width:0 !important}
  [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  .st-key-kartu_tabel .garis,.st-key-kartu_barang .garis,[class*="st-key-kartu_tgl"] .garis{min-width:780px}
}
/* Tampilan kartu barang */
[class*="st-key-item_"]{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.8rem 1rem;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.6rem;color:#111827 !important}
.itm{display:flex;align-items:center;gap:.85rem}
.itm .ic{flex:0 0 52px;width:52px;height:52px;border-radius:50%;background:#e8f3ec;color:#256b4a;font-weight:800;
  font-size:1.25rem;display:flex;align-items:center;justify-content:center;overflow:hidden}
.itm .ic img{width:100%;height:100%;object-fit:cover}
.itm .isi{flex:1 1 auto;min-width:0}
.itm .jd{font-weight:700;font-size:1.02rem;color:#111827;word-break:break-word}
.itm .mt{font-size:.82rem;color:#5b6573;margin-top:.1rem;word-break:break-word}
.itm .cat{font-size:.82rem;color:#374151;margin-top:.15rem;word-break:break-word}
.itm .qt{flex:0 0 auto;text-align:right;min-width:48px}
.itm .qt b{display:block;font-size:1.7rem;font-weight:800;line-height:1.1;color:#111827}
.itm .qt b.merah{color:#b42318}
.itm .qt span{font-size:.72rem;color:#6b7280}
[class*="st-key-kedit_"] button,[class*="st-key-khapus_"] button{min-height:2rem;padding:.1rem .9rem;background:#fff !important;font-weight:600}
[class*="st-key-kedit_"] button{border:1px solid #256b4a !important;color:#256b4a !important}
[class*="st-key-khapus_"] button{border:1px solid #b42318 !important;color:#b42318 !important}
.st-key-baris_cari [data-testid="stHorizontalBlock"],[class*="st-key-item_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;align-items:center}
.st-key-baris_cari [data-testid="stColumn"]:first-child{min-width:0 !important;flex:1 1 auto !important;width:auto !important}
.st-key-baris_cari [data-testid="stColumn"]:last-child,[class*="st-key-item_"] [data-testid="stColumn"]{min-width:0 !important;flex:0 0 auto !important;width:auto !important}
.st-key-baris_cari button,[class*="st-key-item_"] button{white-space:nowrap}
.st-key-baris_cari button p,[class*="st-key-item_"] button p{white-space:nowrap}
</style>
""", unsafe_allow_html=True)

TANPA = "Tanpa lokasi"
TANPA_KAT = "Tanpa kategori"
FILE_LOKAL = os.environ.get("BARANG_DATA_FILE", "data_lokal.json")
FOTO_LOKAL = os.environ.get("BARANG_FOTO_DIR", "foto_lokal")
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
MAKS_RIWAYAT = 1000
WIB = timezone(timedelta(hours=7))


def sekarang() -> datetime:
    return datetime.now(WIB)


def hari_ini() -> date:
    return sekarang().date()


def fmt_iso(s: str) -> str:
    try:
        return date.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s or ""


def fmt_waktu(s: str) -> str:
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s or ""


def iso_ke_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except Exception:
        return None


def sisa_hari(s):
    """Selisih hari dari hari ini ke tanggal s (negatif = sudah lewat), None kalau kosong."""
    d = iso_ke_date(s)
    return (d - hari_ini()).days if d else None


def rp(n) -> str:
    return "Rp " + f"{int(round(n)):,}".replace(",", ".")


def data_kosong() -> dict:
    return {
        "tempat": [],     # [{"id","nama"}]  tingkat 1, contoh: Rumah A, Rumah B, Kantor
        "lokasi": [],     # [{"id","nama","tempat"(id tempat, boleh kosong)}]  tingkat 2, contoh: Lemari kamar
        "sublokasi": [],  # [{"id","nama","lokasi"(id lokasi induk)}]  contoh: Kotak 2
        "kategori": [],   # [{"id","nama"}]
        "barang": [],     # [{"id","nama","lokasi","sublokasi","kategori","jumlah","catatan","diubah",
                          #   "harga","kedaluwarsa","garansi","habis","foto"}]
        "pinjam": [],     # [{"id","arah"("keluar"|"masuk"),"barang","nama","orang","tanggal","tenggat","catatan","kembali"}]
        "riwayat": [],    # [{"id","barang","nama","dari","ke","waktu","oleh"}]
    }


def konversi_lama(lama: list) -> dict:
    """Ubah daftar barang versi awal (lokasi berupa teks) ke format baru."""
    d = data_kosong()

    def cari(kunci, nama):
        nama = (nama or "").strip()
        if not nama:
            return ""
        for x in d[kunci]:
            if x["nama"].lower() == nama.lower():
                return x["id"]
        baru = {"id": uuid.uuid4().hex[:8], "nama": nama}
        d[kunci].append(baru)
        return baru["id"]

    for it in lama:
        if not isinstance(it, dict) or not it.get("nama"):
            continue
        try:
            jml = int(it.get("jumlah", 1))
        except Exception:
            jml = 1
        b = {"id": it.get("id") or uuid.uuid4().hex[:8], "nama": it["nama"], "jumlah": jml,
             "diubah": it.get("diubah") or hari_ini().isoformat()}
        lok, kat = cari("lokasi", it.get("lokasi")), cari("kategori", it.get("kategori"))
        if lok:
            b["lokasi"] = lok
        if kat:
            b["kategori"] = kat
        if it.get("catatan"):
            b["catatan"] = it["catatan"]
        d["barang"].append(b)
    return d


# ---------------------------------------------------------------- penyimpanan
class Bentrok(Exception):
    """Data di GitHub sudah berubah sejak terakhir dimuat."""


def cfg_github():
    try:
        g = st.secrets["github"]
        return {"token": g["token"], "repo": g["repo"],
                "path": g.get("path", "data.json"), "branch": g.get("branch", "main")}
    except Exception:
        return None


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


def muat_ke_sesi():
    st.session_state.data, st.session_state.sha = muat()


def commit(pesan_ok: str | None = None) -> bool:
    """Simpan st.session_state.data. Tampilkan hasilnya ke pengguna."""
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
    isi = proses_foto(mentah)
    path = f"foto/{id_barang}_{int(time.time())}.jpg"
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


# -------------------------------------------------------------------- akses
# Akun disimpan di Streamlit Secrets, satu bagian per pengguna:
#   [users.budi]
#   nama = "Budi Santoso"
#   peran = "admin"                 # "admin" (boleh ubah master data) atau "pengisi"
#   password_hash = "pbkdf2$..."    # buat dengan buat_hash.py
# Kalau tidak ada bagian [users], dipakai kata sandi tunggal (secret "password")
# atau, kalau itu juga tidak ada, tanpa login (uji coba).
PERAN = ("admin", "pengisi")
MAKS_GAGAL = 5
KUNCI_DETIK = 60
COOKIE = "barang_sesi"


def _akun() -> dict:
    try:
        return {str(k): dict(v) for k, v in st.secrets["users"].items()}
    except Exception:
        return {}


def cocok_hash(sandi: str, tersimpan: str) -> bool:
    """Cocokkan sandi dengan hash berformat pbkdf2$iterasi$garam_hex$hash_hex."""
    try:
        skema, iterasi, garam, h = str(tersimpan).split("$")
        if skema != "pbkdf2":
            return False
        calon = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), bytes.fromhex(garam), int(iterasi))
        return hmac.compare_digest(calon.hex(), h)
    except Exception:
        return False


def pengguna_nama() -> str:
    u = st.session_state.get("user")
    return u["username"] if u else "tamu"


def adalah_admin() -> bool:
    u = st.session_state.get("user")
    return u is None or u.get("peran") == "admin"   # tanpa login = mode uji coba


def _jam_sesi() -> float:
    try:
        return float(st.secrets.get("sesi_jam", 8))
    except Exception:
        return 8.0


def _kunci_sesi(a: dict) -> bytes:
    try:
        ekstra = str(st.secrets.get("sesi_kunci", ""))
    except Exception:
        ekstra = ""
    return f"{ekstra}|{a.get('password_hash', '')}|{cfg_github() and cfg_github()['token'] or ''}".encode()


def buat_token(uname: str, a: dict) -> str:
    isi = base64.urlsafe_b64encode(
        f"{uname}|{int(time.time() + _jam_sesi() * 3600)}".encode()).decode().rstrip("=")
    tanda = hmac.new(_kunci_sesi(a), isi.encode(), hashlib.sha256).hexdigest()
    return f"{isi}.{tanda}"


def baca_token(token: str, akun: dict):
    """Kembalikan username kalau token sah dan belum kedaluwarsa, kalau tidak None."""
    try:
        isi, tanda = token.split(".")
        uname, exp = base64.urlsafe_b64decode(isi + "=" * (-len(isi) % 4)).decode().split("|")
        a = akun.get(uname)
        if not a or int(exp) < time.time():
            return None
        benar = hmac.new(_kunci_sesi(a), isi.encode(), hashlib.sha256).hexdigest()
        return uname if hmac.compare_digest(benar, tanda) else None
    except Exception:
        return None


def js_cookie(nilai: str, detik: int):
    """Pasang (atau hapus, detik=0) cookie sesi di peramban lewat komponen tak terlihat."""
    import streamlit.components.v1 as components
    components.html(
        f"""<script>
        const d = window.parent.document;
        const aman = window.parent.location.protocol === 'https:' ? '; Secure' : '';
        d.cookie = "{COOKIE}={nilai}; Max-Age={detik}; Path=/; SameSite=Lax" + aman;
        </script>""", height=0)


def keluar():
    for k in ("user", "masuk", "data", "sha"):
        st.session_state.pop(k, None)
    st.session_state.hapus_cookie = True
    st.session_state.cookie_dicek = True


def cek_login():
    akun = _akun()
    if not akun:                       # kata sandi tunggal / uji coba
        try:
            sandi = st.secrets["password"]
        except Exception:
            return
        if st.session_state.get("masuk"):
            return
        with st.form("login"):
            x = st.text_input("Kata sandi", type="password")
            if st.form_submit_button("Masuk"):
                if hmac.compare_digest(x, str(sandi)):
                    st.session_state.masuk = True
                    st.rerun()
                st.error("Kata sandi salah.")
        st.stop()
    if st.session_state.get("user"):
        return
    if st.session_state.pop("hapus_cookie", False):
        js_cookie("", 0)
    if not st.session_state.get("cookie_dicek"):          # pulihkan sesi setelah refresh
        st.session_state.cookie_dicek = True
        try:
            u = baca_token(st.context.cookies.get(COOKIE, ""), akun)
        except Exception:
            u = None
        if u:
            st.session_state.user = {"username": u, "nama": akun[u].get("nama", u),
                                     "peran": akun[u].get("peran", "pengisi")}
            st.rerun()
    st.markdown("""
<style>
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],[data-testid="stToolbar"],
[data-testid="stHeader"]{display:none !important}
[data-testid="stApp"]{background:linear-gradient(160deg,#eef4f0 0%,#f3f4f8 55%,#e6ecf5 100%)}
.block-container{max-width:440px !important;padding:12vh 1.2rem 3rem !important}
.lg-kepala{text-align:center;margin-bottom:1.4rem}
.lg-kepala svg{filter:drop-shadow(0 6px 14px rgba(31,107,73,.28))}
.lg-judul{font-size:1.55rem;font-weight:700;color:#0b1220;margin:.9rem 0 .2rem;letter-spacing:-.01em}
.lg-sub{font-size:.88rem;color:#64748b}
[data-testid="stForm"]{background:#fff;border:1px solid #e2e8f0 !important;border-radius:16px !important;
  padding:1.6rem 1.5rem 1.4rem !important;box-shadow:0 10px 30px rgba(15,23,42,.08)}
[data-testid="stForm"] label p{font-size:.82rem;font-weight:600;color:#334155}
[data-testid="stForm"] input{border-radius:10px}
[data-testid="stForm"] button[kind="secondaryFormSubmit"],[data-testid="stForm"] button[kind="primaryFormSubmit"]{
  background:linear-gradient(135deg,#34a874,#1f6b49) !important;color:#fff !important;border:0 !important;
  border-radius:10px !important;height:2.8rem;font-weight:600;margin-top:.4rem}
[data-testid="stForm"] button:disabled{opacity:.5}
.lg-kaki{text-align:center;font-size:.76rem;color:#94a3b8;margin-top:1.2rem}
</style>
<div class="lg-kepala">
<svg width="56" height="56" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg"><defs>
<linearGradient id="gl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#34a874"/>
<stop offset="1" stop-color="#1f6b49"/></linearGradient></defs>
<rect width="38" height="38" rx="10" fill="url(#gl)"/>
<path d="M19 8l9 4.5v11L19 28l-9-4.5v-11z" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>
<path d="M10 12.5l9 4.5 9-4.5M19 17v11" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>
<div class="lg-judul">Pelacak Barang</div>
<div class="lg-sub">Masuk untuk melanjutkan</div></div>
""", unsafe_allow_html=True)
    terkunci = st.session_state.get("kunci_sampai", 0) - time.time()
    with st.form("login"):
        uname = st.text_input("Username", placeholder="Masukkan username").strip().lower()
        x = st.text_input("Kata sandi", type="password", placeholder="Masukkan kata sandi")
        kirim = st.form_submit_button("Masuk", use_container_width=True, disabled=terkunci > 0)
    if terkunci > 0:
        st.error(f"Terlalu banyak percobaan. Coba lagi dalam {int(terkunci) + 1} detik.")
    elif kirim:
        a = akun.get(uname)
        # hitung hash walau username tidak ada, supaya waktu responsnya sama
        ok = cocok_hash(x, a["password_hash"] if a and "password_hash" in a else "pbkdf2$1$00$00")
        if a and ok and a.get("peran", "pengisi") in PERAN:
            st.session_state.user = {"username": uname, "nama": a.get("nama", uname),
                                     "peran": a.get("peran", "pengisi")}
            st.session_state.gagal = 0
            st.session_state.pasang_cookie = buat_token(uname, a)
            st.rerun()
        st.session_state.gagal = st.session_state.get("gagal", 0) + 1
        if st.session_state.gagal >= MAKS_GAGAL:
            st.session_state.gagal = 0
            st.session_state.kunci_sampai = time.time() + KUNCI_DETIK
            st.rerun()
        st.error("Username atau kata sandi salah.")
    st.markdown('<div class="lg-kaki">Lupa sandi? Hubungi admin aplikasi.</div>', unsafe_allow_html=True)
    st.stop()


cek_login()
if st.session_state.get("pasang_cookie"):
    js_cookie(st.session_state.pop("pasang_cookie"), int(_jam_sesi() * 3600))

if "data" not in st.session_state:
    try:
        muat_ke_sesi()
    except Exception as e:
        st.error(f"Data tidak bisa dimuat: {e}")
        st.stop()

D = st.session_state.data
for kunci, awal in data_kosong().items():
    D.setdefault(kunci, awal)

# Dibuka dari pindaian label QR: ?lokasi=<id>&sub=<id> langsung membuka daftar isi tempat itu.
_qp_lok = st.query_params.get("lokasi")
_qp_tem = st.query_params.get("tempat")
if _qp_lok or _qp_tem:
    _lok_qr = next((x for x in D["lokasi"] if x["id"] == _qp_lok), None) if _qp_lok else None
    if _lok_qr:
        _qp_sub = st.query_params.get("sub", "")
        st.session_state.halaman = "Cari barang"
        st.session_state.cari_tempat = _lok_qr.get("tempat") or "semua"
        st.session_state.cari_lok = _qp_lok
        st.session_state.cari_sub = _qp_sub if any(
            x["id"] == _qp_sub and x["lokasi"] == _qp_lok for x in D["sublokasi"]) else "semua"
        st.session_state.cari_kat = "semua"
        st.session_state.cari_q = ""
    elif _qp_tem and any(t["id"] == _qp_tem for t in D["tempat"]):
        st.session_state.halaman = "Cari barang"
        st.session_state.cari_tempat = _qp_tem
        st.session_state.cari_lok = "semua"
        st.session_state.cari_sub = "semua"
        st.session_state.cari_kat = "semua"
        st.session_state.cari_q = ""
    st.query_params.clear()


# ---------------------------------------------------------------- bantu data
def atur(kunci: str, nilai):
    st.session_state[kunci] = nilai


def pindah_halaman(h: str):
    """Ganti menu sekaligus tutup form/konfirmasi yang masih terbuka."""
    st.session_state.halaman = h
    for k in ("br_mode", "br_hapus", "pj_hapus",
              "edit_tempat", "hapus_tempat", "edit_kategori", "hapus_kategori",
              "edit_lokasi", "hapus_lokasi", "edit_sub", "hapus_sub"):
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


def perlu_beli(b: dict) -> bool:
    return bool(b.get("habis")) or jumlah_b(b) == 0


def pinjam_aktif(id_barang: str):
    """Catatan peminjaman yang masih berjalan untuk barang milik sendiri (dipinjamkan ke orang lain)."""
    return next((p for p in D["pinjam"] if p.get("barang") == id_barang and p.get("arah") == "keluar"
                 and not p.get("kembali")), None)


def lencana(b: dict) -> str:
    h = ""
    if perlu_beli(b):
        h += '<span class="lencana lc-r">Perlu beli</span>'
    p = pinjam_aktif(b["id"])
    if p:
        h += f'<span class="lencana lc-m">Dipinjam {html.escape(p.get("orang", ""))}</span>'
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


def kartu_barang_html(b: dict, foto: bool = True) -> str:
    """Satu kartu barang: ikon/foto bulat, nama, keterangan, jumlah besar di kanan."""
    ic = html.escape((b["nama"].strip()[:1] or "?").upper())
    if foto and b.get("foto"):
        dat = ambil_foto(b["foto"])
        if dat:
            try:
                ic = f'<img src="{_uri_bulat(b["foto"], dat)}" alt="">'
            except Exception:
                pass
    meta = [nama_tempat(b)]
    if b.get("kategori"):
        meta.append(nama_kat(b))
    if harga_b(b):
        meta.append("Rp " + f"{harga_b(b):,}".replace(",", "."))
    ekstra = []
    for lab, kunci in (("Kedaluwarsa", "kedaluwarsa"), ("Garansi", "garansi")):
        s = sisa_hari(b.get(kunci))
        if s is not None:
            ekstra.append(f"{lab}: {status_sisa(s)}")
    cat = ""
    if b.get("catatan"):
        cat += f'<div class="cat">{html.escape(b["catatan"])}</div>'
    if ekstra:
        cat += f'<div class="cat">{" · ".join(ekstra)}</div>'
    merah = " merah" if perlu_beli(b) else ""
    return (f'<div class="itm"><div class="ic">{ic}</div><div class="isi">'
            f'<div class="jd">{html.escape(b["nama"])}{lencana(b)}</div>'
            f'<div class="mt">{html.escape(" • ".join(meta))}</div>{cat}</div>'
            f'<div class="qt"><b class="{merah.strip()}">{jumlah_b(b)}</b><span>buah</span></div></div>')


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


# ------------------------------------------------------------------- tampilan
if not cfg_github():
    st.warning("Mode uji coba: data disimpan di file lokal dan bisa hilang saat aplikasi "
               "dimulai ulang. Isi pengaturan GitHub (lihat README) agar data permanen.")

UTAMA = ["Cari barang", "Kelola barang", "Pindah massal", "Riwayat perpindahan"]
PANTAU = ["Pinjam-meminjam", "Perlu beli", "Kedaluwarsa dan garansi", "Nilai barang"]
MASTER = ["Tempat", "Lokasi", "Sub lokasi", "Kategori", "Label QR", "Cadangan dan pindah data"]
HALAMAN = ["Beranda"] + UTAMA + PANTAU + (MASTER if adalah_admin() else [])
if st.session_state.get("halaman") not in HALAMAN:
    st.session_state.halaman = "Beranda"
halaman = st.session_state.halaman
IKON = {"Beranda": "home", "Cari barang": "search", "Kelola barang": "inventory_2",
        "Pindah massal": "swap_horiz", "Riwayat perpindahan": "history",
        "Pinjam-meminjam": "handshake", "Perlu beli": "shopping_cart",
        "Kedaluwarsa dan garansi": "event_busy", "Nilai barang": "payments",
        "Tempat": "home_work", "Lokasi": "place", "Sub lokasi": "account_tree", "Kategori": "sell",
        "Label QR": "qr_code_2", "Cadangan dan pindah data": "backup"}
LOGO = ('<svg width="38" height="38" viewBox="0 0 38 38" xmlns="http://www.w3.org/2000/svg">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#34a874"/><stop offset="1" stop-color="#1f6b49"/></linearGradient></defs>'
        '<rect width="38" height="38" rx="10" fill="url(#g)"/>'
        '<path d="M19 8l9 4.5v11L19 28l-9-4.5v-11z" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M10 12.5l9 4.5 9-4.5M19 17v11" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/></svg>')
with st.sidebar:
    st.markdown(f'<div class="brand">{LOGO}<div><div class="b1">Pelacak Barang</div>'
                '<div class="b2">Di mana barangku?</div></div></div>', unsafe_allow_html=True)
    _us = st.session_state.get("user")
    if _us:
        st.markdown(f'<div class="pengguna sb"><div class="av">{html.escape(_us["nama"][:1].upper())}</div><div>'
                    f'<div class="nm">{html.escape(_us["nama"])}</div>'
                    f'<div class="pr">{html.escape(_us["peran"])}</div></div></div>', unsafe_allow_html=True)

    def tombol_nav(h):
        st.button(h, key=f"nav_{h}", use_container_width=True, icon=f":material/{IKON[h]}:",
                  type="primary" if h == halaman else "secondary", on_click=pindah_halaman, args=(h,))

    st.markdown('<div class="grup">UTAMA</div>', unsafe_allow_html=True)
    tombol_nav("Beranda")
    st.markdown('<div class="grup">MENU</div>', unsafe_allow_html=True)
    with st.expander("Barang", icon=":material/inventory_2:", expanded=halaman in UTAMA):
        for h in UTAMA:
            tombol_nav(h)
    with st.expander("Pantau", icon=":material/monitoring:", expanded=halaman in PANTAU):
        for h in PANTAU:
            tombol_nav(h)
    if adalah_admin():
        with st.expander("Pengaturan", icon=":material/settings:", expanded=halaman in MASTER):
            for h in MASTER:
                tombol_nav(h)
    st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
    if st.button("Muat ulang", key="nav_muat", use_container_width=True, icon=":material/refresh:",
                 help="Ambil data terbaru dari penyimpanan"):
        muat_ke_sesi()
        st.rerun()
    if cfg_github():
        st.caption(f"Data: {cfg_github()['repo']}")
    if st.session_state.get("user"):
        u = st.session_state.user
        st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
        st.button("Keluar", key="nav_keluar", use_container_width=True,
                  icon=":material/logout:", on_click=keluar)

DESKRIPSI = {
    "Beranda": "Ringkasan barang, hal yang perlu perhatian, dan grafik.",
    "Cari barang": "Cari barang berdasarkan nama, lokasi, kategori, atau catatan.",
    "Kelola barang": "Tambah, ubah, atau hapus barang beserta lokasi, foto, dan tanggalnya.",
    "Pindah massal": "Pindahkan banyak barang sekaligus ke lokasi lain, misalnya saat membereskan kotak.",
    "Riwayat perpindahan": "Catatan otomatis kapan dan dari mana ke mana barang dipindah.",
    "Pinjam-meminjam": "Catat barang yang kamu pinjamkan atau yang kamu pinjam, lengkap dengan tenggatnya.",
    "Perlu beli": "Barang yang habis atau jumlahnya nol, jadi daftar belanja.",
    "Kedaluwarsa dan garansi": "Pantau tanggal kedaluwarsa dan masa garansi.",
    "Nilai barang": "Total nilai barang berdasarkan harga beli.",
    "Tempat": "Tingkat pertama: rumah atau kantor tempat barang disimpan.",
    "Lokasi": "Tingkat kedua: lemari, rak, atau kotak di dalam satu tempat.",
    "Sub lokasi": "Tingkat ketiga: bagian di dalam lokasi, misalnya laci 2 atau rak atas.",
    "Kategori": "Pengelompokan jenis barang.",
    "Label QR": "Cetak label QR untuk ditempel di lemari atau kotak. Dipindai, langsung muncul isinya.",
    "Cadangan dan pindah data": "Unduh cadangan data atau muat data dari berkas.",
}
_grup = ("PENGATURAN" if halaman in MASTER else "RINGKASAN" if halaman == "Beranda"
         else "PANTAU" if halaman in PANTAU else "BARANG")
st.markdown(f'<div class="kepala"><div><div class="eyebrow">{_grup}</div>'
            f'<div class="judul-hal">{html.escape(halaman)}</div>'
            f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div></div>',
            unsafe_allow_html=True)

# -------------------------------------------------------------------- beranda
if halaman == "Beranda":
    brg = D["barang"]
    if not brg:
        st.info("Belum ada barang. Tambahkan lewat menu Barang > Kelola barang.")
    else:
        total_jml = sum(jumlah_b(b) for b in brg)
        lok_dipakai = len({b.get("lokasi") for b in brg if lokasi_dari(b)})
        tanpa_lok = sum(1 for b in brg if lokasi_dari(b) is None)
        n_beli = sum(1 for b in brg if perlu_beli(b))
        n_pinjam = sum(1 for p in D["pinjam"] if not p.get("kembali"))
        st.markdown(
            '<div class="statcard"><div class="sc-kiri"><span class="tag">Ringkasan</span>'
            f'<div class="sc-judul">{len(brg)} jenis barang</div>'
            f'<div class="sc-ket">{total_jml} buah di {lok_dipakai} lokasi</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Tempat</div><div class="sc-val">{len(D["tempat"])}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Lokasi</div><div class="sc-val">{len(D["lokasi"])}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Sub lokasi</div><div class="sc-val">{len(D["sublokasi"])}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Kategori</div><div class="sc-val">{len(D["kategori"])}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Tanpa lokasi</div><div class="sc-val m">{tanpa_lok}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Perlu beli</div><div class="sc-val m">{n_beli}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Sedang dipinjam</div><div class="sc-val">{n_pinjam}</div></div>'
            '</div>', unsafe_allow_html=True)

        with st.container(key="kartu_perhatian"):
            st.markdown("**Perlu perhatian**")
            hal = kumpul_perhatian()
            if hal:
                for h in hal:
                    st.markdown(f'<div class="perhatian">{h}</div>', unsafe_allow_html=True)
            else:
                st.caption("Tidak ada yang perlu diperhatikan sekarang.")

        g1, g2 = st.columns(2)
        with g1.container(key="kartu_g1"):
            st.markdown("**Jenis barang per lokasi**")
            per = {}
            for b in brg:
                per[nama_lokasi(b)] = per.get(nama_lokasi(b), 0) + 1
            st.bar_chart(pd.DataFrame({"Lokasi": list(per), "Jenis barang": list(per.values())}),
                         x="Lokasi", y="Jenis barang", horizontal=True, sort="-Jenis barang",
                         color="#2b7a57", height=300)
        with g2.container(key="kartu_g2"):
            st.markdown("**Jenis barang per kategori**")
            per = {}
            for b in brg:
                per[nama_kat(b)] = per.get(nama_kat(b), 0) + 1
            st.bar_chart(pd.DataFrame({"Kategori": list(per), "Jenis barang": list(per.values())}),
                         x="Kategori", y="Jenis barang", horizontal=True, sort="-Jenis barang",
                         color="#2f5d9e", height=300)

        with st.container(key="kartu_tabel"):
            st.markdown("**Terakhir diubah**")
            for b in sorted(brg, key=lambda x: x.get("diubah", ""), reverse=True)[:8]:
                k = st.columns([4, 4, 2], vertical_alignment="center")
                k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                k[1].write(nama_tempat(b))
                k[2].write(fmt_iso(b.get("diubah", "")))
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- cari barang
if halaman == "Cari barang":
    if not D["barang"]:
        st.info("Belum ada barang. Tambahkan lewat menu Barang > Kelola barang.")
    else:
        with st.container(key="kartu_filter"):
            q = " ".join(st.text_input("Pencarian", icon=":material/search:", key="cari_q",
                                       placeholder="Cari nama, lokasi, kategori, atau catatan...",
                                       label_visibility="collapsed").lower().split())
            c0, c1, c2, c3 = st.columns(4)
            pt = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
            if st.session_state.get("cari_tempat", "semua") not in ["semua"] + list(pt):
                st.session_state.cari_tempat = "semua"
            f_tem = c0.selectbox("Tempat", ["semua"] + list(pt), key="cari_tempat",
                                 format_func=lambda i: "Semua tempat" if i == "semua" else pt[i])
            pl = {l["id"]: (l["nama"] if f_tem != "semua" else nama_lok(l)) for l in daftar_lokasi()
                  if f_tem == "semua" or l.get("tempat") == f_tem}
            if st.session_state.get("cari_lok", "semua") not in ["semua"] + list(pl):
                st.session_state.cari_lok = "semua"
            f_lok = c1.selectbox("Lokasi", ["semua"] + list(pl), key="cari_lok",
                                 format_func=lambda i: "Semua lokasi" if i == "semua" else pl[i])
            psub = {s["id"]: (s["nama"] if f_lok != "semua" else f"{pl[s['lokasi']]} › {s['nama']}")
                    for s in D["sublokasi"] if s["lokasi"] in pl and (f_lok == "semua" or s["lokasi"] == f_lok)}
            if st.session_state.get("cari_sub", "semua") not in ["semua"] + list(psub):
                st.session_state.cari_sub = "semua"
            f_sub = c2.selectbox("Sub lokasi", ["semua"] + list(psub), key="cari_sub",
                                 format_func=lambda i: "Semua sub lokasi" if i == "semua" else psub[i])
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            if st.session_state.get("cari_kat", "semua") not in ["semua"] + list(pk):
                st.session_state.cari_kat = "semua"
            f_kat = c3.selectbox("Kategori", ["semua"] + list(pk), key="cari_kat",
                                 format_func=lambda i: "Semua kategori" if i == "semua" else pk[i])
            tv1, tv2 = st.columns([2, 3], vertical_alignment="center")
            mode_tampil = tv1.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                                key="tampilan", label_visibility="collapsed") or "Kartu"
            tampil_foto = tv2.toggle("Tampilkan foto", value=True, key="cari_foto")
        hasil = D["barang"]
        if f_tem != "semua":
            hasil = [b for b in hasil if (lokasi_dari(b) or {}).get("tempat") == f_tem]
        if f_lok != "semua":
            hasil = [b for b in hasil if b.get("lokasi") == f_lok]
        if f_sub != "semua":
            hasil = [b for b in hasil if (sub_dari(b) or {}).get("id") == f_sub]
        if f_kat != "semua":
            hasil = [b for b in hasil if b.get("kategori") == f_kat]
        if q:
            hasil = [b for b in hasil if q in " ".join(
                [b["nama"], b.get("catatan", ""), nama_tempat(b), nama_kat(b)]).lower()]
        st.caption(f"{len(hasil)} dari {len(D['barang'])} barang")
        if not hasil:
            st.info("Tidak ada barang yang cocok.")
        elif mode_tampil == "Kartu":
            for judul, anggota in kelompok(hasil):
                judul_grup(judul, len(anggota))
                for b in sorted(anggota, key=lambda x: x["nama"].lower()):
                    with st.container(key=f"item_c_{b['id']}"):
                        st.markdown(kartu_barang_html(b, tampil_foto), unsafe_allow_html=True)
        else:
            with st.container(key="kartu_tabel"):
                lebar = [4, 1.2, 2.4, 4, 2]
                judul_kol = ["Barang", "Jumlah", "Kategori", "Catatan", "Diubah"]
                if tampil_foto:
                    lebar, judul_kol = [1.1] + lebar, ["Foto"] + judul_kol
                kep = st.columns(lebar, vertical_alignment="top")
                for kol, judul in zip(kep, judul_kol):
                    kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                for judul, anggota in kelompok(hasil):
                    judul_grup(judul, len(anggota))
                    for b in sorted(anggota, key=lambda x: x["nama"].lower()):
                        k = st.columns(lebar, vertical_alignment="center")
                        o = 0
                        if tampil_foto:
                            tampil_foto_kecil(b, k[0])
                            o = 1
                        k[o].markdown(f'<div class="brg">{html.escape(b["nama"])}{lencana(b)}</div>',
                                      unsafe_allow_html=True)
                        k[o + 1].write(b.get("jumlah", 1))
                        k[o + 2].write(nama_kat(b) if b.get("kategori") else "")
                        k[o + 3].write(b.get("catatan", ""))
                        k[o + 4].write(fmt_iso(b.get("diubah", "")))
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# --------------------------------------------------------------- kelola barang
def halaman_barang():
    by_id = {b["id"]: b for b in D["barang"]}
    mode = st.session_state.get("br_mode")          # None (daftar), "baru", atau id barang
    if mode not in (None, "baru") and mode not in by_id:
        mode = None
    with st.container(key="kartu_barang"):
        if not mode:
            with st.container(key="baris_cari"):
                kc, kt = st.columns([5, 2], vertical_alignment="center")
                cari = " ".join(kc.text_input("Pencarian", key="br_cari", icon=":material/search:",
                                              placeholder="Cari nama, lokasi, atau kategori...",
                                              label_visibility="collapsed").lower().split())
                kt.button("Tambah", type="primary", key="br_tambah", icon=":material/add:",
                          use_container_width=True, on_click=atur, args=("br_mode", "baru"))
            mode_tampil = st.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                               key="tampilan", label_visibility="collapsed") or "Kartu"
            if not D["barang"]:
                st.write("Belum ada barang.")
            if mode_tampil == "Kartu":
                urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
                if cari:
                    urut = [x for x in urut if cari in " ".join(
                        [x["nama"], x.get("catatan", ""), nama_tempat(x), nama_kat(x)]).lower()]
                    if not urut:
                        st.info("Tidak ada barang yang cocok dengan pencarian.")
                for b in urut:
                    with st.container(key=f"item_k_{b['id']}"):
                        st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                        e1, e2, _ = st.columns([1, 1, 3])
                        e1.button("Edit", key=f"kedit_{b['id']}", on_click=atur, args=("br_mode", b["id"]),
                                  use_container_width=True)
                        e2.button("Hapus", key=f"khapus_{b['id']}", on_click=atur, args=("br_hapus", b["id"]),
                                  use_container_width=True)
                        if st.session_state.get("br_hapus") == b["id"]:
                            st.warning(f"Hapus {b['nama']}?")
                            y, n, _ = st.columns([1, 1, 2])
                            if y.button("Ya, hapus", type="primary", key=f"brya_{b['id']}"):
                                foto_lama = b.get("foto", "")
                                D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
                                selesai_simpan("Dihapus.",
                                               sesudah=(lambda p=foto_lama: hapus_foto(p)) if foto_lama else None,
                                               br_hapus=None)
                            n.button("Batal", key=f"brbatal_{b['id']}", on_click=atur, args=("br_hapus", None))
                return
            lebar = [0.8, 1.2, 4, 3.4, 2.2, 1, 1.7]
            kep = st.columns(lebar)
            for kol, judul in zip(kep, ["No.", "Foto", "Barang", "Lokasi", "Kategori", "Jml", "#"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            if cari:
                urut = [x for x in urut if cari in " ".join(
                    [x["nama"], x.get("catatan", ""), nama_tempat(x), nama_kat(x)]).lower()]
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
                    st.warning(f"Hapus {b['nama']}?")
                    y, n, _ = st.columns([1, 1, 4])
                    if y.button("Ya, hapus", type="primary", key=f"brya_{b['id']}"):
                        foto_lama = b.get("foto", "")
                        D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
                        selesai_simpan("Dihapus.", sesudah=(lambda p=foto_lama: hapus_foto(p)) if foto_lama else None,
                                       br_hapus=None)
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
        with st.form(f"form_br_{mode}_{versi()}"):
            f1, f2 = st.columns([4, 1])
            nama = f1.text_input("Nama barang", value=b.get("nama", ""), placeholder="Contoh: Parfum")
            jumlah = f2.number_input("Jumlah", min_value=0, value=jumlah_b(b) if b else 1, step=1)
            ids_l = list(pl)
            lok = st.selectbox("Lokasi", ids_l, index=idx(ids_l, b.get("lokasi", "")),
                               format_func=lambda i: pl[i])
            sub = ""
            if D["sublokasi"]:
                ops = [""] + [x["id"] for x in D["sublokasi"] if x["lokasi"] in pl]
                pt = {x["id"]: f"{pl[x['lokasi']]} › {x['nama']}" for x in D["sublokasi"] if x["lokasi"] in pl}
                awal = b.get("sublokasi", "") if sub_dari(b) else ""
                sub = st.selectbox("Sub lokasi (boleh kosong)", ops, index=idx(ops, awal),
                                   format_func=lambda i: "Tanpa sub lokasi" if not i else pt[i],
                                   help="Pilih sub lokasi yang berada di bawah lokasi di atas.")
            kat = ""
            if D["kategori"]:
                pk = {k["id"]: k["nama"] for k in D["kategori"]}
                ops_k = [""] + list(pk)
                kat = st.selectbox("Kategori (boleh kosong)", ops_k, index=idx(ops_k, b.get("kategori", "")),
                                   format_func=lambda i: TANPA_KAT if not i else pk[i])
            h1, h2, h3 = st.columns(3)
            harga = h1.number_input("Harga beli per buah (Rp)", min_value=0, value=harga_b(b), step=1000,
                                    help="Isi 0 kalau belum tahu. Dipakai di menu Nilai barang.")
            kd = h2.date_input("Kedaluwarsa (boleh kosong)", value=iso_ke_date(b.get("kedaluwarsa")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            gr = h3.date_input("Garansi sampai (boleh kosong)", value=iso_ke_date(b.get("garansi")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            habis = st.checkbox("Habis / perlu beli lagi", value=bool(b.get("habis")))
            foto_lama = b.get("foto", "")
            if foto_lama:
                dat = ambil_foto(foto_lama)
                if dat:
                    st.image(dat, width=140)
            upl = st.file_uploader("Foto barang (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                   help="Foto dikecilkan otomatis supaya hemat tempat.")
            with st.expander("Atau ambil foto dengan kamera"):
                kam = st.camera_input("Kamera", label_visibility="collapsed",
                                      help="Izinkan akses kamera di peramban. Kalau ada foto dari kamera, itu yang dipakai.")
            hapus_cb = st.checkbox("Hapus foto yang sekarang") if foto_lama else False
            catatan = st.text_area("Catatan", value=b.get("catatan", ""))
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
                else:
                    id_ = b.get("id") or uuid.uuid4().hex[:8]
                    foto_baru, galat = "", ""
                    sumber = kam if kam is not None else upl
                    if sumber is not None:
                        try:
                            foto_baru = simpan_foto(id_, sumber.getvalue())
                        except Exception as e:
                            galat = f"Foto gagal diunggah: {e}"
                    if galat:
                        st.error(galat)
                    else:
                        baru = dict(b) if mode != "baru" else {"id": id_}
                        isi = {"nama": nama, "lokasi": lok, "sublokasi": sub, "kategori": kat,
                               "catatan": catatan.strip(), "harga": int(harga),
                               "kedaluwarsa": kd.isoformat() if kd else "",
                               "garansi": gr.isoformat() if gr else "", "habis": bool(habis)}
                        for kunci, v in isi.items():
                            if v or kunci in ("nama", "lokasi"):
                                baru[kunci] = v
                            else:
                                baru.pop(kunci, None)
                        baru["jumlah"] = int(jumlah)
                        baru["diubah"] = hari_ini().isoformat()
                        foto_hapus = ""
                        if foto_baru:
                            foto_hapus, baru["foto"] = foto_lama, foto_baru
                        elif hapus_cb:
                            foto_hapus = foto_lama
                            baru.pop("foto", None)
                        tempat_baru = nama_tempat(baru)
                        if mode == "baru":
                            catat(id_, nama, "", tempat_baru)
                            D["barang"].append(baru)
                        else:
                            if nama_tempat(b) != tempat_baru:
                                catat(id_, nama, nama_tempat(b), tempat_baru)
                            D["barang"] = [baru if x["id"] == mode else x for x in D["barang"]]
                        selesai_simpan("Tersimpan.",
                                       sesudah=(lambda p=foto_hapus: hapus_foto(p)) if foto_hapus else None,
                                       br_mode=None)


# -------------------------------------------------------------- pindah massal
def halaman_pindah():
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
        if st.button(f"Pindahkan {len(pilih)} barang", type="primary", disabled=not pilih, key="pm_go"):
            dipindah = 0
            for i in pilih:
                b = by_id[i]
                dari = nama_tempat(b)
                b["lokasi"] = tl
                if ts:
                    b["sublokasi"] = ts
                else:
                    b.pop("sublokasi", None)
                ke = nama_tempat(b)
                if dari != ke:
                    b["diubah"] = hari_ini().isoformat()
                    catat(i, b["nama"], dari, ke)
                    dipindah += 1
            if not dipindah:
                st.info("Semua barang yang dipilih sudah berada di tujuan itu.")
            else:
                selesai_simpan(f"{dipindah} barang dipindahkan.", pm_reset=True)


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
        hasil = sorted(r, key=lambda x: x.get("waktu", ""), reverse=True)
        if q:
            hasil = [x for x in hasil if q in " ".join(
                [x.get("nama", ""), x.get("dari", ""), x.get("ke", "")]).lower()]
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


# ------------------------------------------------------------ pinjam-meminjam
def _baris_hapus_pinjam(p):
    """Tampilkan konfirmasi hapus kalau baris ini sedang dikonfirmasi."""
    if st.session_state.get("pj_hapus") == p["id"]:
        st.warning(f"Hapus catatan {p.get('nama', '')}?")
        y, n, _ = st.columns([1, 1, 4])
        if y.button("Ya, hapus", type="primary", key=f"pjya_{p['id']}"):
            D["pinjam"] = [x for x in D["pinjam"] if x["id"] != p["id"]]
            selesai_simpan("Dihapus.", pj_hapus=None)
        n.button("Batal", key=f"pjbatal_{p['id']}", on_click=atur, args=("pj_hapus", None))


def halaman_pinjam():
    by_id = {b["id"]: b for b in D["barang"]}
    aktif = [p for p in D["pinjam"] if not p.get("kembali")]
    selesai = [p for p in D["pinjam"] if p.get("kembali")]
    hari = hari_ini()
    with st.container(key="kartu_barang"):
        st.markdown("#### Catat peminjaman")
        with st.form(f"form_pinjam_{versi()}"):
            arah = st.radio("Jenis", ["Saya pinjamkan ke orang lain", "Saya meminjam dari orang lain"],
                            horizontal=True)
            ids = [""] + [b["id"] for b in sorted(D["barang"], key=lambda x: x["nama"].lower())]
            pilih = st.selectbox("Barang dari daftar (boleh kosong)", ids,
                                 format_func=lambda i: "— tidak dari daftar —" if not i
                                 else f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
            manual = st.text_input("Nama barang (kalau tidak dari daftar)")
            c1, c2, c3 = st.columns(3)
            orang = c1.text_input("Nama orang")
            tgl = c2.date_input("Tanggal", value=hari, min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            tenggat = c3.date_input("Tenggat kembali (boleh kosong)", value=None,
                                    min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            catatan = st.text_input("Catatan (boleh kosong)")
            kirim = st.form_submit_button("Catat", type="primary")
        if kirim:
            keluar_ = arah.startswith("Saya pinjamkan")
            nama = by_id[pilih]["nama"] if pilih else manual.strip()
            if not nama:
                st.error("Pilih barang dari daftar atau ketik namanya.")
            elif not orang.strip():
                st.error("Nama orang wajib diisi.")
            elif tenggat and tenggat < tgl:
                st.error("Tenggat tidak boleh sebelum tanggal pinjam.")
            elif pilih and keluar_ and pinjam_aktif(pilih):
                st.error(f"Barang itu masih tercatat dipinjam {pinjam_aktif(pilih).get('orang', '')}.")
            else:
                D["pinjam"].append({"id": uuid.uuid4().hex[:8], "arah": "keluar" if keluar_ else "masuk",
                                    "barang": pilih, "nama": nama, "orang": orang.strip(),
                                    "tanggal": tgl.isoformat(), "tenggat": tenggat.isoformat() if tenggat else "",
                                    "catatan": catatan.strip(), "kembali": ""})
                selesai_simpan("Peminjaman dicatat.")

        st.markdown(f"#### Sedang berjalan ({len(aktif)})")
        if not aktif:
            st.caption("Tidak ada peminjaman yang sedang berjalan.")
        else:
            lebar = [3.4, 2.2, 1.8, 2.2, 2.8]
            kep = st.columns(lebar, vertical_alignment="top")
            for kol, judul in zip(kep, ["Barang", "Dengan siapa", "Sejak", "Tenggat", "Aksi"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for p in sorted(aktif, key=lambda x: (x.get("tenggat") or "9999-12-31", x.get("tanggal", ""))):
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                tanda = ('<span class="lencana lc-m">Dipinjamkan</span>' if p.get("arah") == "keluar"
                         else '<span class="lencana lc-b">Saya pinjam</span>')
                k[0].markdown(f'<div class="brg">{html.escape(p.get("nama", ""))}{tanda}</div>',
                              unsafe_allow_html=True)
                k[1].write(p.get("orang", ""))
                k[2].write(fmt_iso(p.get("tanggal", "")))
                k[3].markdown(f'{fmt_iso(p["tenggat"])}<br>{status_sisa(sisa_hari(p["tenggat"]))}'
                              if p.get("tenggat") else "—", unsafe_allow_html=True)
                a1, a2 = k[4].columns([3, 1])
                if a1.button("Sudah kembali", key=f"pjkembali_{p['id']}"):
                    p["kembali"] = hari.isoformat()
                    selesai_simpan("Dicatat sudah kembali.")
                a2.button("🗑️", key=f"pjhapus_{p['id']}", help="Hapus catatan", on_click=atur,
                          args=("pj_hapus", p["id"]))
                _baris_hapus_pinjam(p)
        with st.expander(f"Sudah kembali ({len(selesai)})"):
            if not selesai:
                st.caption("Belum ada.")
            for p in sorted(selesai, key=lambda x: x.get("kembali", ""), reverse=True):
                k = st.columns([3.4, 2.2, 2.2, 2.2, 1], vertical_alignment="center")
                k[0].write(p.get("nama", ""))
                k[1].write(p.get("orang", ""))
                k[2].write(f"{fmt_iso(p.get('tanggal', ''))} → {fmt_iso(p.get('kembali', ''))}")
                k[3].write("Dipinjamkan" if p.get("arah") == "keluar" else "Saya pinjam")
                k[4].button("🗑️", key=f"pjhapus2_{p['id']}", help="Hapus catatan", on_click=atur,
                            args=("pj_hapus", p["id"]))
                _baris_hapus_pinjam(p)


# ----------------------------------------------------------------- perlu beli
def halaman_beli():
    by_id = {b["id"]: b for b in D["barang"]}
    perlu = sorted([b for b in D["barang"] if perlu_beli(b)], key=lambda x: x["nama"].lower())
    lain = sorted([b for b in D["barang"] if not perlu_beli(b)], key=lambda x: x["nama"].lower())
    with st.container(key="kartu_barang"):
        if lain:
            with st.form(f"form_beli_{versi()}"):
                pilih = st.selectbox("Tandai barang yang habis", [b["id"] for b in lain],
                                     format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                kirim = st.form_submit_button("Tandai perlu beli", type="primary")
            if kirim:
                by_id[pilih]["habis"] = True
                by_id[pilih]["diubah"] = hari_ini().isoformat()
                selesai_simpan("Ditandai perlu beli.")
        st.markdown(f"#### Daftar belanja ({len(perlu)})")
        if not perlu:
            st.caption("Tidak ada barang yang perlu dibeli.")
            return
        lebar = [4, 3.4, 2.4, 2.2]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Biasanya disimpan di", "Harga terakhir", "Aksi"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        total = 0
        for b in perlu:
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            h = harga_b(b)
            total += h
            k[2].write(rp(h) if h else "—")
            if k[3].button("Sudah dibeli", key=f"bl_{b['id']}"):
                b.pop("habis", None)
                if jumlah_b(b) == 0:
                    b["jumlah"] = 1
                b["diubah"] = hari_ini().isoformat()
                selesai_simpan("Dicoret dari daftar belanja.")
        st.caption(f"Perkiraan total: {rp(total)} (dari harga beli terakhir, satu buah per barang).")
        teks = "\n".join(f"- {b['nama']} ({nama_tempat(b)})" + (f" ± {rp(harga_b(b))}" if harga_b(b) else "")
                         for b in perlu)
        st.download_button("Unduh daftar belanja (.txt)", teks, file_name="daftar-belanja.txt", mime="text/plain")


# ------------------------------------------------------- kedaluwarsa & garansi
def _tabel_tanggal(kunci: str, judul_tgl: str):
    ada = [(sisa_hari(b.get(kunci)), b) for b in D["barang"] if sisa_hari(b.get(kunci)) is not None]
    with st.container(key=f"kartu_tgl_{kunci}"):
        if not ada:
            st.info(f"Belum ada barang yang diisi tanggal {judul_tgl.lower()}. Isi lewat Kelola barang.")
            return
        f = st.selectbox("Tampilkan", ["Semua", "Sudah lewat", "Dalam 30 hari", "Dalam 90 hari"],
                         key=f"tg_{kunci}")
        if f == "Sudah lewat":
            ada = [x for x in ada if x[0] < 0]
        elif f == "Dalam 30 hari":
            ada = [x for x in ada if 0 <= x[0] <= 30]
        elif f == "Dalam 90 hari":
            ada = [x for x in ada if 0 <= x[0] <= 90]
        if not ada:
            st.caption("Tidak ada yang cocok.")
            return
        lebar = [4, 4, 2.2, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Tempat", judul_tgl, "Status"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for s, b in sorted(ada, key=lambda x: x[0]):
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(fmt_iso(b[kunci]))
            k[3].markdown(status_sisa(s), unsafe_allow_html=True)


def halaman_tanggal():
    t1, t2 = st.tabs(["Kedaluwarsa", "Garansi"])
    with t1:
        _tabel_tanggal("kedaluwarsa", "Kedaluwarsa")
    with t2:
        _tabel_tanggal("garansi", "Garansi sampai")


# ---------------------------------------------------------------- nilai barang
def halaman_nilai():
    ber = [b for b in D["barang"] if harga_b(b)]
    if not ber:
        st.info("Belum ada harga yang diisi. Isi \"Harga beli per buah\" di Kelola barang.")
        return

    def nilai(b):
        return harga_b(b) * max(jumlah_b(b), 0)

    total = sum(nilai(b) for b in ber)
    kosong = len(D["barang"]) - len(ber)
    st.markdown(
        '<div class="statcard"><div class="sc-kiri"><span class="tag">Total nilai</span>'
        f'<div class="sc-judul">{rp(total)}</div>'
        f'<div class="sc-ket">dari {len(ber)} jenis barang yang sudah diisi harganya</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Rata-rata per jenis</div><div class="sc-val">{rp(total / len(ber))}</div></div>'
        f'<div class="sc-stat"><div class="sc-lab">Belum diisi harga</div><div class="sc-val m">{kosong}</div></div>'
        '</div>', unsafe_allow_html=True)
    g1, g2 = st.columns(2)
    with g1.container(key="kartu_g1"):
        st.markdown("**Nilai per lokasi (Rp)**")
        per = {}
        for b in ber:
            per[nama_lokasi(b)] = per.get(nama_lokasi(b), 0) + nilai(b)
        st.bar_chart(pd.DataFrame({"Lokasi": list(per), "Nilai": list(per.values())}),
                     x="Lokasi", y="Nilai", horizontal=True, sort="-Nilai", color="#2b7a57", height=300)
    with g2.container(key="kartu_g2"):
        st.markdown("**Nilai per kategori (Rp)**")
        per = {}
        for b in ber:
            per[nama_kat(b)] = per.get(nama_kat(b), 0) + nilai(b)
        st.bar_chart(pd.DataFrame({"Kategori": list(per), "Nilai": list(per.values())}),
                     x="Kategori", y="Nilai", horizontal=True, sort="-Nilai", color="#2f5d9e", height=300)
    with st.container(key="kartu_tabel"):
        st.markdown("**20 barang bernilai tertinggi**")
        lebar = [4, 3.4, 2.2, 1.2, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Tempat", "Harga satuan", "Jml", "Nilai"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for b in sorted(ber, key=nilai, reverse=True)[:20]:
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(rp(harga_b(b)))
            k[3].write(jumlah_b(b))
            k[4].write(rp(nilai(b)))


# --------------------------------------------------------------------- label QR
LABEL_CSS = """
body{font-family:Arial,Helvetica,sans-serif;margin:16px}
.qrg{display:flex;flex-wrap:wrap;gap:10px}
.qrl{border:1px dashed #94a3b8;border-radius:6px;padding:8px;width:__CM__cm;text-align:center;break-inside:avoid}
.qrl img{width:100%;image-rendering:pixelated}
.qrt{font-weight:700;font-size:12pt;margin-top:4px}
.qrs{font-size:9pt;color:#555}
@media print{body{margin:0}.qrl{border:1px dashed #bbb}}
"""


def _target_label():
    hasil = []
    for t in sorted(D["tempat"], key=lambda t: t["nama"].lower()):
        hasil.append({"kode": t["id"], "judul": t["nama"], "sub": "", "q": f"tempat={t['id']}"})
    for l in daftar_lokasi():
        tem = tempat_dari_lok(l)
        hasil.append({"kode": l["id"], "judul": l["nama"], "sub": tem["nama"] if tem else "",
                      "q": f"lokasi={l['id']}"})
        for s in D["sublokasi"]:
            if s["lokasi"] == l["id"]:
                hasil.append({"kode": s["id"], "judul": s["nama"], "sub": nama_lok(l),
                              "q": f"lokasi={l['id']}&sub={s['id']}"})
    return hasil


def halaman_label():
    if segno is None:
        st.error("Pustaka label QR (segno) belum terpasang. Tambahkan `segno` ke requirements.txt.")
        return
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di menu Lokasi, lalu cetak labelnya di sini.")
        return
    try:
        app_url = str(st.secrets.get("app_url", ""))
    except Exception:
        app_url = ""
    st.session_state.setdefault("qr_url", app_url)
    targets = _target_label()
    semua = [t["kode"] for t in targets]
    peta = {t["kode"]: t for t in targets}
    if "qr_pilih" not in st.session_state:
        st.session_state.qr_pilih = list(semua)
    else:
        st.session_state.qr_pilih = [i for i in st.session_state.qr_pilih if i in peta]
    with st.container(key="kartu_barang"):
        url = st.text_input("Alamat aplikasi", key="qr_url", placeholder="https://namaapp.streamlit.app",
                            help="Alamat aplikasi ini di internet. Dipasang di dalam kode QR.").strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        pilih = st.multiselect("Label yang dicetak", semua, key="qr_pilih",
                               format_func=lambda i: peta[i]["judul"] if not peta[i]["sub"]
                               else f'{peta[i]["sub"]} › {peta[i]["judul"]}')
        ukuran = st.selectbox("Ukuran label", ["Kecil (3 cm)", "Sedang (4,5 cm)", "Besar (6 cm)"], index=1)
        cm = {"Kecil (3 cm)": 3, "Sedang (4,5 cm)": 4.5, "Besar (6 cm)": 6}[ukuran]
        if not url:
            st.info("Isi alamat aplikasi dulu supaya kode QR bisa membuka aplikasi saat dipindai. "
                    "Alamat itu muncul di bilah alamat peramban setelah aplikasi berhasil di-deploy. "
                    "Biar tidak perlu mengetik lagi, simpan di Secrets: app_url = \"https://...\".")
            return
        if not pilih:
            st.caption("Pilih minimal satu label.")
            return
        sel, kartu = [], []
        for kode in pilih:
            t = peta[kode]
            qr = segno.make(f"{url}/?{t['q']}", error="m")
            buf = io.BytesIO()
            qr.save(buf, kind="png", scale=8, border=2)
            kartu.append((buf.getvalue(), t["judul"] if not t["sub"] else f'{t["sub"]} › {t["judul"]}'))
            sel.append(f'<div class="qrl"><img src="{qr.png_data_uri(scale=8, border=2)}" alt="QR">'
                       f'<div class="qrt">{html.escape(t["judul"])}</div>'
                       + (f'<div class="qrs">{html.escape(t["sub"])}</div>' if t["sub"] else "") + "</div>")
        dokumen = ('<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Label QR</title><style>'
                   + LABEL_CSS.replace("__CM__", str(cm)) + '</style></head><body><div class="qrg">'
                   + "".join(sel) + "</div></body></html>")
        st.download_button("Unduh lembar label (HTML)", dokumen, file_name="label-qr.html", mime="text/html",
                           type="primary", help="Buka file ini di peramban, lalu tekan Ctrl+P untuk mencetak.")
        st.caption("Buka file hasil unduhan di peramban, lalu cetak (Ctrl+P). Gunakan kertas stiker kalau mau "
                   "langsung ditempel.")
        for i in range(0, len(kartu), 4):
            kol = st.columns(4)
            for j, (png, teks) in enumerate(kartu[i:i + 4]):
                kol[j].image(png, caption=teks, width=150)


# ---------------------------------------------------------------- master data
def daftar_sederhana(judul: str, kunci: str, hint: str):
    """Daftar nama dengan tombol Ubah nama dan Hapus per baris, dan kolom tambah di bawah."""
    k_edit, k_hapus = f"edit_{kunci}", f"hapus_{kunci}"
    with st.expander(f"{judul} ({len(D[kunci])})", expanded=True):
        st.caption(hint)
        if not D[kunci]:
            st.write("Belum ada.")
        for x in D[kunci]:
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get(k_edit) == x["id"]:
                baru = c1.text_input("Nama", value=x["nama"], key=f"nm_{kunci}_{x['id']}",
                                     label_visibility="collapsed")
                c3.button("Batal", key=f"bt_{kunci}_{x['id']}", on_click=atur, args=(k_edit, None))
                if c2.button("Simpan", key=f"sv_{kunci}_{x['id']}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif ada_kembar([y["nama"] for y in D[kunci] if y["id"] != x["id"]] + [baru]):
                        st.error("Nama itu sudah ada.")
                    else:
                        x["nama"] = baru
                        selesai_simpan("Nama diubah.", **{k_edit: None})
            elif st.session_state.get(k_hapus) == x["id"]:
                if kunci == "tempat":
                    n_pakai = sum(1 for l in D["lokasi"] if l.get("tempat") == x["id"])
                    akibat = "lokasi jadi tanpa tempat"
                else:
                    n_pakai = sum(1 for b in D["barang"] if b.get(kunci) == x["id"])
                    akibat = f"barang jadi tanpa {judul.lower()}"
                c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_pakai} {akibat})" if n_pakai else ""))
                c3.button("Batal", key=f"bh_{kunci}_{x['id']}", on_click=atur, args=(k_hapus, None))
                if c2.button("Ya, hapus", key=f"yh_{kunci}_{x['id']}", type="primary"):
                    D[kunci] = [y for y in D[kunci] if y["id"] != x["id"]]
                    if kunci == "tempat":     # lokasi di dalamnya tetap ada, hanya lepas dari tempat
                        for l in D["lokasi"]:
                            if l.get("tempat") == x["id"]:
                                l.pop("tempat", None)
                    if kunci == "lokasi":     # sub lokasi di bawahnya ikut hilang
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["lokasi"] != x["id"]]
                    selesai_simpan("Dihapus.", **{k_hapus: None})
            else:
                c1.write(x["nama"])
                c2.button("Ubah nama", key=f"ub_{kunci}_{x['id']}", on_click=atur, args=(k_edit, x["id"]))
                c3.button("Hapus", key=f"hp_{kunci}_{x['id']}", on_click=atur, args=(k_hapus, x["id"]))
        with st.form(f"tambah_{kunci}", clear_on_submit=True):
            nama = st.text_input(f"Tambah {judul.lower()}", placeholder="Nama baru")
            if st.form_submit_button("Tambah"):
                nama = nama.strip()
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar([y["nama"] for y in D[kunci]] + [nama]):
                    st.error("Nama itu sudah ada.")
                else:
                    D[kunci].append({"id": uuid.uuid4().hex[:8], "nama": nama})
                    selesai_simpan("Ditambahkan.")


def halaman_sublokasi():
    """Sub lokasi selalu berada di bawah satu lokasi."""
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di menu Lokasi, lalu tambahkan sub lokasinya di sini.")
        return
    peta = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    with st.expander(f"Sub lokasi ({len(D['sublokasi'])})", expanded=True):
        st.caption("Sub lokasi berada di bawah satu lokasi (misalnya Laci 2 di Lemari kamar). "
                   "Menghapus sub lokasi tidak menghapus barangnya.")
        for l in daftar_lokasi():
            milik = [x for x in D["sublokasi"] if x["lokasi"] == l["id"]]
            st.markdown(f'<div class="bidang">{html.escape(nama_lok(l))} · {len(milik)} sub lokasi</div>',
                        unsafe_allow_html=True)
            if not milik:
                st.caption("Belum ada sub lokasi.")
            for x in milik:
                c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
                if st.session_state.get("edit_sub") == x["id"]:
                    baru = c1.text_input("Nama", value=x["nama"], key=f"nm_sub_{x['id']}",
                                         label_visibility="collapsed")
                    c3.button("Batal", key=f"bt_sub_{x['id']}", on_click=atur, args=("edit_sub", None))
                    if c2.button("Simpan", key=f"sv_sub_{x['id']}", type="primary"):
                        baru = baru.strip()
                        if not baru:
                            st.error("Nama tidak boleh kosong.")
                        elif ada_kembar([y["nama"] for y in milik if y["id"] != x["id"]] + [baru]):
                            st.error("Nama itu sudah ada di lokasi ini.")
                        else:
                            x["nama"] = baru
                            selesai_simpan("Nama diubah.", edit_sub=None)
                elif st.session_state.get("hapus_sub") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("sublokasi") == x["id"])
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_b} barang jadi tanpa sub lokasi)" if n_b else ""))
                    c3.button("Batal", key=f"bh_sub_{x['id']}", on_click=atur, args=("hapus_sub", None))
                    if c2.button("Ya, hapus", key=f"yh_sub_{x['id']}", type="primary"):
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["id"] != x["id"]]
                        for b in D["barang"]:
                            if b.get("sublokasi") == x["id"]:
                                b.pop("sublokasi", None)
                        selesai_simpan("Dihapus.", hapus_sub=None)
                else:
                    c1.write(x["nama"])
                    c2.button("Ubah nama", key=f"ub_sub_{x['id']}", on_click=atur, args=("edit_sub", x["id"]))
                    c3.button("Hapus", key=f"hp_sub_{x['id']}", on_click=atur, args=("hapus_sub", x["id"]))
        with st.form("tambah_sub", clear_on_submit=True):
            f1, f2 = st.columns([2, 3])
            induk = f1.selectbox("Di bawah lokasi", list(peta), format_func=lambda i: peta[i])
            nama = f2.text_input("Nama sub lokasi", placeholder="Nama baru")
            if st.form_submit_button("Tambah sub lokasi"):
                nama = nama.strip()
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar([y["nama"] for y in D["sublokasi"] if y["lokasi"] == induk] + [nama]):
                    st.error("Nama itu sudah ada di lokasi ini.")
                else:
                    D["sublokasi"].append({"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": induk})
                    selesai_simpan("Ditambahkan.")


def halaman_lokasi():
    """Lokasi (lemari, rak, kotak) berada di dalam satu tempat (rumah, kantor)."""
    pt = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
    ops = [""] + list(pt)

    def fmt(i):
        return "Tanpa tempat" if not i else pt[i]

    if not pt:
        st.info("Isi dulu nama tempat (misalnya Rumah A, Rumah B, Kantor) di menu Tempat. "
                "Lokasi tanpa tempat tetap bisa dipakai.")
    with st.expander(f"Lokasi ({len(D['lokasi'])})", expanded=True):
        st.caption("Lokasi adalah lemari, rak, atau kotak di dalam satu tempat (misalnya Lemari kamar di Rumah A). "
                   "Menghapus lokasi ikut menghapus sub lokasinya. Barangnya tidak terhapus.")
        urut = sorted(D["lokasi"], key=lambda l: l["nama"].lower())
        for tid, tnama in list(pt.items()) + [("", "Belum diatur tempatnya")]:
            milik = [x for x in urut if (x.get("tempat") == tid if tid else x.get("tempat") not in pt)]
            if not tid and not milik:
                continue
            st.markdown(f'<div class="bidang">{html.escape(tnama)} · {len(milik)} lokasi</div>',
                        unsafe_allow_html=True)
            if not milik:
                st.caption("Belum ada lokasi.")
            for x in milik:
                c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
                if st.session_state.get("edit_lokasi") == x["id"]:
                    e1, e2 = c1.columns([3, 2])
                    baru = e1.text_input("Nama", value=x["nama"], key=f"nm_lok_{x['id']}",
                                         label_visibility="collapsed")
                    awal = x.get("tempat") if x.get("tempat") in pt else ""
                    tbaru = e2.selectbox("Tempat", ops, index=idx(ops, awal), key=f"tm_lok_{x['id']}",
                                         format_func=fmt, label_visibility="collapsed")
                    c3.button("Batal", key=f"bt_lok_{x['id']}", on_click=atur, args=("edit_lokasi", None))
                    if c2.button("Simpan", key=f"sv_lok_{x['id']}", type="primary"):
                        baru = baru.strip()
                        sama = [y["nama"] for y in D["lokasi"]
                                if y["id"] != x["id"] and (y.get("tempat") or "") == tbaru]
                        if not baru:
                            st.error("Nama tidak boleh kosong.")
                        elif ada_kembar(sama + [baru]):
                            st.error("Nama itu sudah ada di tempat ini.")
                        else:
                            x["nama"] = baru
                            if tbaru:
                                x["tempat"] = tbaru
                            else:
                                x.pop("tempat", None)
                            selesai_simpan("Lokasi diubah.", edit_lokasi=None)
                elif st.session_state.get("hapus_lokasi") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("lokasi") == x["id"])
                    n_s = sum(1 for s in D["sublokasi"] if s["lokasi"] == x["id"])
                    akibat = ", ".join(([f"{n_b} barang jadi tanpa lokasi"] if n_b else [])
                                       + ([f"{n_s} sub lokasi ikut terhapus"] if n_s else []))
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({akibat})" if akibat else ""))
                    c3.button("Batal", key=f"bh_lok_{x['id']}", on_click=atur, args=("hapus_lokasi", None))
                    if c2.button("Ya, hapus", key=f"yh_lok_{x['id']}", type="primary"):
                        D["lokasi"] = [y for y in D["lokasi"] if y["id"] != x["id"]]
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["lokasi"] != x["id"]]
                        selesai_simpan("Dihapus.", hapus_lokasi=None)
                else:
                    c1.write(x["nama"])
                    c2.button("Ubah", key=f"ub_lok_{x['id']}", on_click=atur, args=("edit_lokasi", x["id"]))
                    c3.button("Hapus", key=f"hp_lok_{x['id']}", on_click=atur, args=("hapus_lokasi", x["id"]))
        with st.form("tambah_lokasi", clear_on_submit=True):
            f1, f2 = st.columns([2, 3])
            tem = f1.selectbox("Di tempat", ops, format_func=fmt)
            nama = f2.text_input("Nama lokasi", placeholder="Contoh: Lemari kamar")
            if st.form_submit_button("Tambah lokasi"):
                nama = nama.strip()
                sama = [y["nama"] for y in D["lokasi"] if (y.get("tempat") or "") == tem]
                if not nama:
                    st.error("Nama tidak boleh kosong.")
                elif ada_kembar(sama + [nama]):
                    st.error("Nama itu sudah ada di tempat ini.")
                else:
                    baru = {"id": uuid.uuid4().hex[:8], "nama": nama}
                    if tem:
                        baru["tempat"] = tem
                    D["lokasi"].append(baru)
                    selesai_simpan("Ditambahkan.")


def cadangan():
    with st.expander("Cadangan dan pindah data", expanded=True):
        st.caption("Unduh seluruh data sebagai file, atau muat file data dari tempat lain. "
                   "Memuat file akan **mengganti semua data** yang ada sekarang. "
                   "Foto tidak ikut di file ini, foto tersimpan terpisah di folder foto/ pada repositori data. "
                   "File lama berisi daftar barang (items.json) juga bisa dimuat dan otomatis diubah formatnya.")
        st.download_button("Unduh data.json", json.dumps(D, ensure_ascii=False, indent=1, sort_keys=True),
                           file_name="data.json", mime="application/json")
        with st.form("impor"):
            berkas = st.file_uploader("File data.json", type=["json"])
            yakin = st.checkbox("Ya, ganti semua data dengan isi file ini")
            if st.form_submit_button("Muat file"):
                if berkas is None:
                    st.error("Pilih filenya dulu.")
                elif not yakin:
                    st.error("Centang dulu \"Ya, ganti semua data\".")
                else:
                    try:
                        baru = json.load(berkas)
                        if isinstance(baru, list):
                            baru = konversi_lama(baru)
                        assert isinstance(baru, dict)
                        assert isinstance(baru.get("barang"), list)
                        assert isinstance(baru.get("lokasi", []), list)
                    except Exception:
                        st.error("File tidak dikenali sebagai data barang.")
                    else:
                        for kunci, awal in data_kosong().items():
                            baru.setdefault(kunci, awal)
                        st.session_state.data = baru
                        selesai_simpan("Data dimuat.")


if halaman == "Kelola barang":
    halaman_barang()
if halaman == "Pindah massal":
    halaman_pindah()
if halaman == "Riwayat perpindahan":
    halaman_riwayat()
if halaman == "Pinjam-meminjam":
    halaman_pinjam()
if halaman == "Perlu beli":
    halaman_beli()
if halaman == "Kedaluwarsa dan garansi":
    halaman_tanggal()
if halaman == "Nilai barang":
    halaman_nilai()
if adalah_admin() and halaman == "Tempat":
    daftar_sederhana("Tempat", "tempat", "Tempat besar yang menyimpan barang, misalnya Rumah A, Rumah B, atau Kantor. "
                     "Menghapus tempat tidak menghapus lokasinya, hanya melepasnya dari tempat itu.")
if adalah_admin() and halaman == "Lokasi":
    halaman_lokasi()
if adalah_admin() and halaman == "Sub lokasi":
    halaman_sublokasi()
if adalah_admin() and halaman == "Kategori":
    daftar_sederhana("Kategori", "kategori", "Pengelompokan jenis barang, misalnya pakaian atau perawatan diri. "
                     "Boleh dikosongkan kalau tidak diperlukan.")
if adalah_admin() and halaman == "Label QR":
    halaman_label()
if adalah_admin() and halaman == "Cadangan dan pindah data":
    cadangan()
