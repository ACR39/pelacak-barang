"""Pelacak Barang Pribadi (Streamlit).

Mencatat di mana barang pribadi disimpan (lokasi dan sub lokasi), memudahkan
pencarian, dan memantau pinjaman, belanja, kedaluwarsa/garansi, serta nilai barang.
Data disimpan sebagai satu file JSON di repositori GitHub (disarankan repositori
privat terpisah); foto disimpan sebagai berkas terpisah di folder fotos/.
Kalau pengaturan GitHub tidak ada, aplikasi memakai file lokal untuk uji coba.
"""
import base64
import copy
import hashlib
import hmac
import html
import io
import json
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Pelacak Barang", page_icon="📦", layout="wide")

st.markdown("""
<style>
.block-container{padding:2.6rem 2rem 4rem;max-width:1600px}
[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"]{display:none !important}
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
[data-testid="stSidebar"] [data-testid="stExpander"] summary{font-weight:600;font-size:.92rem;padding:.55rem .5rem;border-radius:8px}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{background:rgba(255,255,255,.05)}
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
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"]{background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  padding:1.1rem 1.2rem;box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:.9rem}
[data-testid="stExpander"]{background:#fff;border-radius:14px !important;box-shadow:0 1px 3px rgba(16,24,40,.06)}
.statcard{display:flex;flex-wrap:wrap;background:#fff;border:1px solid #e3e7ee;border-radius:16px;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin:.2rem 0 .6rem;overflow:hidden}
.sc-kiri{flex:2 1 280px;padding:1rem 1.2rem}
.sc-judul{font-size:1.35rem;font-weight:800;color:#111827;margin-top:.5rem}
.sc-ket{font-size:.85rem;color:#6b7280;margin-top:.15rem}
.tag{display:inline-block;background:#e8f3ec;color:#1f6b49;font-size:.72rem;font-weight:700;border-radius:999px;
  padding:.15rem .65rem;margin:.1rem .35rem .1rem 0}
.tag-m{background:#fff4d6;color:#8a5a00}
.tag-r{background:#fde8e6;color:#b42318}
.tag-b{background:#e0ecff;color:#1d4ed8}
.sc-stat{flex:1 1 90px;border-left:1px solid #eef0f4;text-align:center;padding:1rem .4rem}
.sc-lab{font-size:.7rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:#6b7280}
.sc-val{font-size:1.5rem;font-weight:800;color:#111827;margin-top:.2rem}
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
</style>
""", unsafe_allow_html=True)

TANPA = "Tanpa lokasi"
TANPA_KAT = "Tanpa kategori"
BATAS_HARI = 30                      # peringatan kedaluwarsa/garansi (hari)
FOLDER_FOTO = "fotos"
FOLDER_FOTO_LOKAL = "fotos_lokal"
FILE_LOKAL = os.environ.get("BARANG_DATA_FILE", "data_lokal.json")


# ---------------------------------------------------------------- waktu
def _zona():
    try:
        return timezone(timedelta(hours=float(st.secrets.get("zona_jam", 8))))
    except Exception:
        return timezone(timedelta(hours=8))


def sekarang() -> datetime:
    return datetime.now(_zona())


def hari_ini() -> date:
    return sekarang().date()


def fmt_iso(s: str) -> str:
    try:
        return date.fromisoformat(s).strftime("%d/%m/%Y")
    except Exception:
        return s or ""


def fmt_waktu(s: str) -> str:
    try:
        return datetime.fromisoformat(s).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return s or ""


def sisa_hari(iso):
    """Selisih hari dari hari ini ke tanggal iso (negatif = sudah lewat); None kalau kosong."""
    if not iso:
        return None
    try:
        return (date.fromisoformat(iso) - hari_ini()).days
    except Exception:
        return None


def rp(n) -> str:
    return "Rp " + f"{int(n or 0):,}".replace(",", ".")


def data_kosong() -> dict:
    return {
        "lokasi": [],     # [{"id","nama"}]  contoh: Lemari kamar, Kotak pensil biru
        "sublokasi": [],  # [{"id","nama","lokasi"(id lokasi induk)}]  contoh: Kotak 2
        "kategori": [],   # [{"id","nama"}]
        "barang": [],     # [{"id","nama","lokasi","sublokasi","kategori","jumlah","catatan","diubah",
                          #   "harga","kedaluwarsa","garansi","perlu_beli","foto"}]
        "pinjam": [],     # [{"id","arah"(keluar|masuk),"barang","nama","orang","tgl","jatuh_tempo","kembali","catatan"}]
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
             "diubah": it.get("diubah") or date.today().isoformat()}
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


def transaksi(fn, pesan: str = "Perbarui data barang") -> bool:
    """Ubah data lewat fn(data), simpan, dan kembalikan ke keadaan semula kalau gagal.
    Dipakai oleh tombol (on_click), hasil galat ditampilkan lewat pesan_isian."""
    data = st.session_state.data
    lama = copy.deepcopy(data)
    fn(data)
    try:
        simpan(data, f"{pesan} (oleh {pengguna_nama()})")
        st.session_state.pesan_isian = None
        return True
    except Bentrok:
        muat_ke_sesi()
        st.session_state.pesan_isian = ("Data sudah diubah dari tempat lain. Data terbaru sudah "
                                        "dimuat, silakan ulangi.")
    except Exception as e:
        data.clear()
        data.update(lama)
        st.session_state.pesan_isian = f"Gagal menyimpan: {e}"
    return False


# ---------------------------------------------------------------------- foto
def kompres_foto(raw: bytes) -> bytes:
    from PIL import Image, ImageOps
    im = Image.open(io.BytesIO(raw))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((900, 900))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=78, optimize=True)
    return buf.getvalue()


def simpan_foto(bid: str, raw: bytes) -> str:
    jpg = kompres_foto(raw)
    path = f"{FOLDER_FOTO}/{bid}.jpg"
    c = cfg_github()
    if c:
        url = _gh_url(c, path)
        sha = None
        r = requests.get(url, headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
        if r.status_code == 200:
            sha = r.json()["sha"]
        body = {"message": f"Foto barang {bid}", "branch": c["branch"],
                "content": base64.b64encode(jpg).decode("ascii")}
        if sha:
            body["sha"] = sha
        requests.put(url, headers=_gh_headers(c), json=body, timeout=40).raise_for_status()
    else:
        os.makedirs(FOLDER_FOTO_LOKAL, exist_ok=True)
        with open(os.path.join(FOLDER_FOTO_LOKAL, f"{bid}.jpg"), "wb") as f:
            f.write(jpg)
    return path


def hapus_foto(path: str):
    """Hapus foto (sebisanya; kegagalan diabaikan)."""
    if not path:
        return
    try:
        c = cfg_github()
        if c:
            url = _gh_url(c, path)
            r = requests.get(url, headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=20)
            if r.status_code == 200:
                requests.delete(url, headers=_gh_headers(c), timeout=30,
                                json={"message": f"Hapus {path}", "sha": r.json()["sha"],
                                      "branch": c["branch"]})
        else:
            f = os.path.join(FOLDER_FOTO_LOKAL, os.path.basename(path))
            if os.path.exists(f):
                os.remove(f)
    except Exception:
        pass


@st.cache_data(ttl=3600, show_spinner=False)
def ambil_foto(path: str, versi_: str) -> bytes:
    c = cfg_github()
    if c:
        r = requests.get(_gh_url(c, path), params={"ref": c["branch"]}, timeout=30,
                         headers={**_gh_headers(c), "Accept": "application/vnd.github.raw+json"})
        r.raise_for_status()
        return r.content
    with open(os.path.join(FOLDER_FOTO_LOKAL, os.path.basename(path)), "rb") as f:
        return f.read()


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


# ---------------------------------------------------------------- bantu data
def atur(kunci: str, nilai):
    st.session_state[kunci] = nilai


def versi() -> int:
    return st.session_state.get("ver", 0)


def selesai_simpan(pesan: str, **setelah):
    """Simpan ke penyimpanan. Kalau berhasil, atur keadaan halaman lalu muat ulang."""
    if commit(pesan):
        for k, v in setelah.items():
            st.session_state[k] = v
        st.session_state.ver = versi() + 1
        st.rerun()


def ada_kembar(nama_nama) -> bool:
    kecil = [n.lower() for n in nama_nama]
    return len(set(kecil)) != len(kecil)


def idx(daftar, nilai) -> int:
    return daftar.index(nilai) if nilai in daftar else 0


def jml(b: dict) -> int:
    try:
        return int(b.get("jumlah", 1) or 0)
    except Exception:
        return 0


def lokasi_dari(b: dict):
    return next((x for x in D["lokasi"] if x["id"] == b.get("lokasi")), None)


def sub_dari(b: dict):
    """Sub lokasi barang kalau valid dan masih di bawah lokasinya, kalau tidak None."""
    sid = b.get("sublokasi")
    if not sid:
        return None
    return next((x for x in D["sublokasi"] if x["id"] == sid and x["lokasi"] == b.get("lokasi")), None)


def nama_lokasi(b: dict) -> str:
    x = lokasi_dari(b)
    return x["nama"] if x else TANPA


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
    for l in D["lokasi"]:
        milik = [b for b in brg if b.get("lokasi") == l["id"]]
        langsung = [b for b in milik if sub_dari(b) is None]
        if langsung:
            hasil.append((l["nama"], langsung))
        for s in D["sublokasi"]:
            if s["lokasi"] != l["id"]:
                continue
            ang = [b for b in milik if b.get("sublokasi") == s["id"]]
            if ang:
                hasil.append((f"{l['nama']} › {s['nama']}", ang))
    ids = {l["id"] for l in D["lokasi"]}
    lain = [b for b in brg if b.get("lokasi") not in ids]
    if lain:
        hasil.append((TANPA, lain))
    return hasil


def judul_grup(nama, jumlah):
    st.markdown(f'<div class="bidang">{html.escape(nama)} · {jumlah} barang</div>', unsafe_allow_html=True)


def catat_riwayat(data: dict, bid: str, nama: str, dari: str, ke: str):
    data.setdefault("riwayat", []).append(
        {"id": uuid.uuid4().hex[:8], "barang": bid, "nama": nama, "dari": dari, "ke": ke,
         "waktu": sekarang().replace(tzinfo=None).isoformat(timespec="minutes"), "oleh": pengguna_nama()})
    data["riwayat"] = data["riwayat"][-1500:]


def pinjam_keluar(bid: str):
    """Catatan pinjaman aktif (barang dipinjamkan ke orang lain) untuk barang ini."""
    return next((p for p in D["pinjam"]
                 if p.get("barang") == bid and not p.get("kembali") and p.get("arah") == "keluar"), None)


def perlu_beli(b: dict) -> bool:
    return bool(b.get("perlu_beli")) or jml(b) == 0


def exp_dekat(b: dict) -> bool:
    s = sisa_hari(b.get("kedaluwarsa"))
    return s is not None and s <= BATAS_HARI


def gar_dekat(b: dict) -> bool:
    s = sisa_hari(b.get("garansi"))
    return s is not None and 0 <= s <= BATAS_HARI


def tanda(b: dict) -> str:
    """Penanda status barang dalam bentuk HTML."""
    t = []
    s = sisa_hari(b.get("kedaluwarsa"))
    if s is not None:
        if s < 0:
            t.append(("Kedaluwarsa", "tag-r"))
        elif s <= BATAS_HARI:
            t.append((f"Kedaluwarsa {s} hari lagi", "tag-m"))
    s = sisa_hari(b.get("garansi"))
    if s is not None and 0 <= s <= BATAS_HARI:
        t.append((f"Garansi habis {s} hari lagi", "tag-m"))
    if perlu_beli(b):
        t.append(("Perlu beli", "tag-r"))
    p = pinjam_keluar(b["id"])
    if p:
        t.append((f"Dipinjam {p.get('orang', '')}".strip(), "tag-b"))
    return "".join(f'<span class="tag {k}">{html.escape(x)}</span>' for x, k in t)


@st.dialog("Detail barang")
def dialog_detail(bid: str):
    b = next((x for x in D["barang"] if x["id"] == bid), None)
    if not b:
        st.write("Barang tidak ditemukan.")
        return
    if b.get("foto"):
        try:
            st.image(ambil_foto(b["foto"], b.get("diubah", "")), use_container_width=True)
        except Exception:
            st.caption("Foto tidak bisa dimuat.")
    st.markdown(f"### {b['nama']}")
    st.markdown(tanda(b), unsafe_allow_html=True)
    st.write(f"**Lokasi:** {nama_tempat(b)}")
    st.write(f"**Jumlah:** {jml(b)}")
    if b.get("kategori"):
        st.write(f"**Kategori:** {nama_kat(b)}")
    if b.get("harga"):
        st.write(f"**Harga satuan:** {rp(b['harga'])} (nilai {rp(b['harga'] * jml(b))})")
    if b.get("kedaluwarsa"):
        st.write(f"**Kedaluwarsa:** {fmt_iso(b['kedaluwarsa'])}")
    if b.get("garansi"):
        st.write(f"**Garansi sampai:** {fmt_iso(b['garansi'])}")
    if b.get("catatan"):
        st.write(f"**Catatan:** {b['catatan']}")
    st.caption(f"Terakhir diubah {fmt_iso(b.get('diubah', ''))}")


# ----------------------------------------------------------- tautan dari QR
_qp = st.query_params
if _qp.get("lokasi"):
    _lid = _qp.get("lokasi")
    if any(l["id"] == _lid for l in D["lokasi"]):
        st.session_state.halaman = "Cari barang"
        st.session_state["cari_lok"] = _lid
        _sid = _qp.get("sub")
        if _sid and any(s["id"] == _sid and s["lokasi"] == _lid for s in D["sublokasi"]):
            st.session_state[f"cari_sub_{_lid}"] = _sid
    st.query_params.clear()

# ------------------------------------------------------------------- tampilan
if not cfg_github():
    st.warning("Mode uji coba: data disimpan di file lokal dan bisa hilang saat aplikasi "
               "dimulai ulang. Isi pengaturan GitHub (lihat README) agar data permanen.")

UTAMA = ["Cari barang", "Kelola barang", "Pindah massal", "Riwayat perpindahan"]
PANTAU = ["Pinjam-meminjam", "Daftar belanja", "Kedaluwarsa dan garansi", "Nilai barang"]
MASTER = ["Lokasi", "Sub lokasi", "Kategori", "Label QR", "Cadangan dan pindah data"]
HALAMAN = ["Beranda"] + UTAMA + PANTAU + (MASTER if adalah_admin() else [])
if st.session_state.get("halaman") not in HALAMAN:
    st.session_state.halaman = "Beranda"
halaman = st.session_state.halaman
IKON = {"Beranda": "home", "Cari barang": "search", "Kelola barang": "inventory_2",
        "Pindah massal": "drive_file_move", "Riwayat perpindahan": "history",
        "Pinjam-meminjam": "handshake", "Daftar belanja": "shopping_cart",
        "Kedaluwarsa dan garansi": "schedule", "Nilai barang": "payments",
        "Lokasi": "place", "Sub lokasi": "account_tree", "Kategori": "sell",
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

    def tombol_nav(h):
        st.button(h, key=f"nav_{h}", use_container_width=True, icon=f":material/{IKON[h]}:",
                  type="primary" if h == halaman else "secondary", on_click=atur, args=("halaman", h))

    st.markdown('<div class="grup">UTAMA</div>', unsafe_allow_html=True)
    tombol_nav("Beranda")
    st.markdown('<div class="grup">MENU</div>', unsafe_allow_html=True)
    with st.expander("Barang", icon=":material/inventory_2:", expanded=halaman in UTAMA):
        for h in UTAMA:
            tombol_nav(h)
    with st.expander("Pantauan", icon=":material/monitoring:", expanded=halaman in PANTAU):
        for h in PANTAU:
            tombol_nav(h)
    if adalah_admin():
        with st.expander("Master data", icon=":material/database:", expanded=halaman in MASTER):
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
        st.caption(f"Masuk sebagai **{u['nama']}** ({u['peran']})")
        st.button("Keluar", key="nav_keluar", use_container_width=True,
                  icon=":material/logout:", on_click=keluar)

DESKRIPSI = {
    "Beranda": "Ringkasan barang, hal yang perlu perhatian, lokasi, dan kategori.",
    "Cari barang": "Cari barang berdasarkan nama, lokasi, kategori, atau catatan.",
    "Kelola barang": "Tambah, ubah, atau hapus barang beserta lokasi, foto, dan detailnya.",
    "Pindah massal": "Pindahkan beberapa barang sekaligus ke lokasi baru.",
    "Riwayat perpindahan": "Catatan kapan dan ke mana barang dipindahkan.",
    "Pinjam-meminjam": "Barang yang kamu pinjamkan ke orang lain atau pinjam dari orang lain.",
    "Daftar belanja": "Barang yang habis atau ditandai perlu dibeli lagi.",
    "Kedaluwarsa dan garansi": "Barang yang akan kedaluwarsa atau garansinya akan habis.",
    "Nilai barang": "Perkiraan nilai barang berdasarkan harga beli dan jumlahnya.",
    "Lokasi": "Tempat penyimpanan, misalnya lemari kamar atau kotak pensil biru.",
    "Sub lokasi": "Bagian di dalam lokasi, misalnya kotak 2 atau rak atas.",
    "Kategori": "Pengelompokan jenis barang.",
    "Label QR": "Cetak kode QR untuk tiap lokasi; dipindai untuk melihat isinya.",
    "Cadangan dan pindah data": "Unduh cadangan data atau muat data dari berkas.",
}
_grup = ("MASTER" if halaman in MASTER else "PANTAUAN" if halaman in PANTAU
         else "RINGKASAN" if halaman == "Beranda" else "BARANG")
_u = st.session_state.get("user")
_chip = ""
if _u:
    _chip = (f'<div class="pengguna"><div class="av">{html.escape(_u["nama"][:1].upper())}</div><div>'
             f'<div class="nm">{html.escape(_u["nama"])}</div><div class="pr">{html.escape(_u["peran"])}</div></div></div>')
st.markdown(f'<div class="kepala"><div><div class="eyebrow">{_grup}</div>'
            f'<div class="judul-hal">{html.escape(halaman)}</div>'
            f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div>{_chip}</div>',
            unsafe_allow_html=True)
if st.session_state.get("pesan_isian"):
    st.error(st.session_state.pesan_isian)

# -------------------------------------------------------------------- beranda
if halaman == "Beranda":
    brg = D["barang"]
    if not brg:
        st.info("Belum ada barang. Tambahkan lewat menu Barang > Kelola barang.")
    else:
        total_jml = sum(jml(b) for b in brg)
        nilai_total = sum(int(b.get("harga", 0) or 0) * jml(b) for b in brg)
        lok_dipakai = len({b.get("lokasi") for b in brg if lokasi_dari(b)})
        tanpa_lok = sum(1 for b in brg if lokasi_dari(b) is None)
        n_beli = sum(1 for b in brg if perlu_beli(b))
        n_exp = sum(1 for b in brg if exp_dekat(b))
        n_pinjam = sum(1 for p in D["pinjam"] if not p.get("kembali"))
        st.markdown(
            '<div class="statcard"><div class="sc-kiri"><span class="tag">Ringkasan</span>'
            f'<div class="sc-judul">{len(brg)} jenis barang</div>'
            f'<div class="sc-ket">{total_jml} buah di {lok_dipakai} lokasi · nilai {rp(nilai_total)}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Lokasi</div><div class="sc-val">{len(D["lokasi"])}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Perlu beli</div><div class="sc-val m">{n_beli}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Segera kedaluwarsa</div><div class="sc-val m">{n_exp}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Pinjaman aktif</div><div class="sc-val">{n_pinjam}</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Tanpa lokasi</div><div class="sc-val m">{tanpa_lok}</div></div>'
            '</div>', unsafe_allow_html=True)

        telat = [p for p in D["pinjam"] if not p.get("kembali") and (sisa_hari(p.get("jatuh_tempo")) or 0) < 0
                 and p.get("jatuh_tempo")]
        n_gar = sum(1 for b in brg if gar_dekat(b))
        if n_beli or n_exp or n_gar or telat:
            with st.container(key="kartu_perhatian"):
                st.markdown("**Perlu perhatian**")
                for teks, n, hal in [
                        ("barang kedaluwarsa atau segera kedaluwarsa", n_exp, "Kedaluwarsa dan garansi"),
                        ("barang garansinya segera habis", n_gar, "Kedaluwarsa dan garansi"),
                        ("barang perlu dibeli lagi", n_beli, "Daftar belanja"),
                        ("pinjaman melewati jatuh tempo", len(telat), "Pinjam-meminjam")]:
                    if n:
                        k = st.columns([6, 1.4], vertical_alignment="center")
                        k[0].write(f"**{n}** {teks}")
                        k[1].button("Lihat", key=f"ph_{hal}_{teks}", on_click=atur, args=("halaman", hal))

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
            c1, c2, c3 = st.columns(3)
            pl = {l["id"]: l["nama"] for l in D["lokasi"]}
            f_lok = c1.selectbox("Lokasi", ["semua"] + list(pl), key="cari_lok",
                                 format_func=lambda i: "Semua lokasi" if i == "semua" else pl[i])
            f_sub = "semua"
            if f_lok != "semua":
                subs = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == f_lok}
                if subs:
                    f_sub = c2.selectbox("Sub lokasi", ["semua"] + list(subs), key=f"cari_sub_{f_lok}",
                                         format_func=lambda i: "Semua sub lokasi" if i == "semua" else subs[i])
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            f_kat = c3.selectbox("Kategori", ["semua"] + list(pk), key="cari_kat",
                                 format_func=lambda i: "Semua kategori" if i == "semua" else pk[i])
        hasil = D["barang"]
        if f_lok != "semua":
            hasil = [b for b in hasil if b.get("lokasi") == f_lok]
        if f_sub != "semua":
            hasil = [b for b in hasil if b.get("sublokasi") == f_sub]
        if f_kat != "semua":
            hasil = [b for b in hasil if b.get("kategori") == f_kat]
        if q:
            hasil = [b for b in hasil if q in " ".join(
                [b["nama"], b.get("catatan", ""), nama_tempat(b), nama_kat(b)]).lower()]
        st.caption(f"{len(hasil)} dari {len(D['barang'])} barang")
        if not hasil:
            st.info("Tidak ada barang yang cocok.")
        else:
            with st.container(key="kartu_tabel"):
                lebar = [4.4, 1, 2.2, 3.4, 1.3]
                kep = st.columns(lebar, vertical_alignment="top")
                for kol, judul in zip(kep, ["Barang", "Jumlah", "Kategori", "Catatan", "Detail"]):
                    kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                for judul, anggota in kelompok(hasil):
                    judul_grup(judul, len(anggota))
                    for b in sorted(anggota, key=lambda x: x["nama"].lower()):
                        k = st.columns(lebar, vertical_alignment="center")
                        k[0].markdown(f'<div class="brg">{"📷 " if b.get("foto") else ""}'
                                      f'{html.escape(b["nama"])}</div>' + tanda(b), unsafe_allow_html=True)
                        k[1].write(jml(b))
                        k[2].write(nama_kat(b) if b.get("kategori") else "")
                        k[3].write(b.get("catatan", ""))
                        if k[4].button("Lihat", key=f"lihat_{b['id']}"):
                            dialog_detail(b["id"])
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)


# --------------------------------------------------------------- kelola barang
def hapus_barang(bid: str):
    b = next((x for x in D["barang"] if x["id"] == bid), None)
    if not b:
        return
    hapus_foto(b.get("foto", ""))
    catat_riwayat(D, bid, b["nama"], nama_tempat(b), "(dihapus)")
    D["barang"] = [x for x in D["barang"] if x["id"] != bid]


def halaman_barang():
    by_id = {b["id"]: b for b in D["barang"]}
    mode = st.session_state.get("br_mode")          # None (daftar), "baru", atau id barang
    if mode not in (None, "baru") and mode not in by_id:
        mode = None
    with st.container(key="kartu_barang"):
        if not mode:
            st.button("Tambah barang", type="primary", key="br_tambah", on_click=atur, args=("br_mode", "baru"))
            if not D["barang"]:
                st.write("Belum ada barang.")
            cari = " ".join(st.text_input("Pencarian", key="br_cari", icon=":material/search:",
                                          placeholder="Cari nama, lokasi, atau kategori...",
                                          label_visibility="collapsed").lower().split())
            lebar = [0.8, 4.4, 3.2, 2.2, 1, 1.7]
            kep = st.columns(lebar)
            for kol, judul in zip(kep, ["No.", "Barang", "Lokasi", "Kategori", "Jml", "#"]):
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
                k[1].markdown(f'<div class="brg">{"📷 " if b.get("foto") else ""}{html.escape(b["nama"])}</div>'
                              + tanda(b), unsafe_allow_html=True)
                k[2].write(nama_tempat(b))
                k[3].write(nama_kat(b) if b.get("kategori") else "")
                k[4].write(jml(b))
                t1, t2 = k[5].columns(2)
                t1.button("✏️", key=f"bredit_{b['id']}", help="Ubah", on_click=atur, args=("br_mode", b["id"]))
                t2.button("🗑️", key=f"brhapus_{b['id']}", help="Hapus", on_click=atur, args=("br_hapus", b["id"]))
                if st.session_state.get("br_hapus") == b["id"]:
                    st.warning(f"Hapus {b['nama']}? Fotonya ikut terhapus.")
                    y, n, _ = st.columns([1, 1, 4])
                    if y.button("Ya, hapus", type="primary", key=f"brya_{b['id']}"):
                        hapus_barang(b["id"])
                        selesai_simpan("Dihapus.", br_hapus=None)
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
                st.caption("Minta admin menambahkan lokasi di Master data.")
            c2.button("Kembali", on_click=atur, args=("br_mode", None))
            return
        if b.get("foto"):
            try:
                st.image(ambil_foto(b["foto"], b.get("diubah", "")), width=220)
            except Exception:
                st.caption("Foto tidak bisa dimuat.")
        with st.form(f"form_br_{mode}_{versi()}"):
            f1, f2 = st.columns([4, 1])
            nama = f1.text_input("Nama barang", value=b.get("nama", ""), placeholder="Contoh: Parfum")
            jumlah = f2.number_input("Jumlah", min_value=0, value=jml(b) if b else 1, step=1)
            pl = {l["id"]: l["nama"] for l in D["lokasi"]}
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
            catatan = st.text_area("Catatan", value=b.get("catatan", ""))
            st.markdown("**Detail tambahan (semua boleh kosong)**")
            d1, d2, d3 = st.columns(3)
            harga = d1.number_input("Harga satuan (Rp)", min_value=0, value=int(b.get("harga", 0) or 0), step=1000)
            exp = d2.date_input("Tanggal kedaluwarsa", format="DD/MM/YYYY",
                                value=date.fromisoformat(b["kedaluwarsa"]) if b.get("kedaluwarsa") else None)
            gar = d3.date_input("Garansi sampai", format="DD/MM/YYYY",
                                value=date.fromisoformat(b["garansi"]) if b.get("garansi") else None)
            beli = st.checkbox("Perlu dibeli lagi", value=bool(b.get("perlu_beli")))
            foto_baru = st.file_uploader("Foto barang", type=["jpg", "jpeg", "png", "webp"])
            hapus_f = st.checkbox("Hapus foto yang ada") if b.get("foto") else False
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
                    baru = dict(b) if mode != "baru" else {"id": uuid.uuid4().hex[:8]}
                    dari = nama_tempat(b) if mode != "baru" else "—"
                    try:
                        if foto_baru is not None:
                            baru["foto"] = simpan_foto(baru["id"], foto_baru.getvalue())
                        elif hapus_f and b.get("foto"):
                            hapus_foto(b["foto"])
                            baru.pop("foto", None)
                    except Exception as e:
                        st.error(f"Foto gagal diproses: {e}")
                        st.stop()
                    isi = {"nama": nama, "lokasi": lok, "sublokasi": sub, "kategori": kat,
                           "catatan": catatan.strip(),
                           "kedaluwarsa": exp.isoformat() if exp else "",
                           "garansi": gar.isoformat() if gar else ""}
                    for kunci, v in isi.items():
                        if v or kunci in ("nama", "lokasi"):
                            baru[kunci] = v
                        else:
                            baru.pop(kunci, None)
                    baru["jumlah"] = int(jumlah)
                    if harga > 0:
                        baru["harga"] = int(harga)
                    else:
                        baru.pop("harga", None)
                    if beli:
                        baru["perlu_beli"] = True
                    else:
                        baru.pop("perlu_beli", None)
                    baru["diubah"] = hari_ini().isoformat()
                    ke = nama_tempat(baru)
                    if mode == "baru":
                        catat_riwayat(D, baru["id"], nama, dari, ke)
                        D["barang"].append(baru)
                    else:
                        if dari != ke:
                            catat_riwayat(D, baru["id"], nama, dari, ke)
                        D["barang"] = [baru if x["id"] == mode else x for x in D["barang"]]
                    selesai_simpan("Tersimpan.", br_mode=None)


if halaman == "Kelola barang":
    halaman_barang()


# --------------------------------------------------------------- pindah massal
def cb_pindah(asal: str):
    kb = f"pm_barang_{asal}"
    ids = st.session_state.get(kb, [])
    lok = st.session_state.get("pm_lok")
    sub = st.session_state.get(f"pm_sub_{lok}", "")
    if not ids or not lok:
        st.session_state.pesan_isian = "Pilih barang yang mau dipindahkan dan lokasi tujuannya."
        return

    def fn(data):
        for b in data["barang"]:
            if b["id"] in ids:
                dari = nama_tempat(b)
                b["lokasi"] = lok
                if sub:
                    b["sublokasi"] = sub
                else:
                    b.pop("sublokasi", None)
                b["diubah"] = hari_ini().isoformat()
                ke = nama_tempat(b)
                if dari != ke:
                    catat_riwayat(data, b["id"], b["nama"], dari, ke)
    if transaksi(fn, "Pindah massal"):
        st.session_state[kb] = []
        st.session_state.pesan_ok = f"{len(ids)} barang dipindahkan."


if halaman == "Pindah massal":
    if not D["barang"] or not D["lokasi"]:
        st.info("Belum ada barang atau lokasi.")
    else:
        if st.session_state.get("pesan_ok"):
            st.success(st.session_state.pop("pesan_ok"))
        with st.container(key="kartu_filter"):
            pl = {l["id"]: l["nama"] for l in D["lokasi"]}
            asal = st.selectbox("Ambil dari lokasi", ["semua"] + list(pl), key="pm_asal",
                                format_func=lambda i: "Semua lokasi" if i == "semua" else pl[i])
            pool = sorted([b for b in D["barang"] if asal == "semua" or b.get("lokasi") == asal],
                          key=lambda x: x["nama"].lower())
            st.multiselect("Barang yang dipindahkan", [b["id"] for b in pool], key=f"pm_barang_{asal}",
                           format_func=lambda i: next(f"{b['nama']} — {nama_tempat(b)}" for b in pool if b["id"] == i),
                           placeholder="Pilih satu atau lebih barang")
            t1, t2 = st.columns(2)
            tujuan = t1.selectbox("Pindahkan ke lokasi", list(pl), key="pm_lok", format_func=lambda i: pl[i])
            subs = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == tujuan}
            if subs:
                t2.selectbox("Sub lokasi (boleh kosong)", [""] + list(subs), key=f"pm_sub_{tujuan}",
                             format_func=lambda i: "Tanpa sub lokasi" if not i else subs[i])
            st.button("Pindahkan", type="primary", key="pm_go", on_click=cb_pindah, args=(asal,))

# ------------------------------------------------------- riwayat perpindahan
if halaman == "Riwayat perpindahan":
    if not D["riwayat"]:
        st.info("Belum ada riwayat. Perpindahan tercatat otomatis saat barang ditambah, dipindah, atau dihapus.")
    else:
        with st.container(key="kartu_filter"):
            q = " ".join(st.text_input("Pencarian", key="rw_q", icon=":material/search:",
                                       placeholder="Cari nama barang atau lokasi...",
                                       label_visibility="collapsed").lower().split())
        rows = sorted(D["riwayat"], key=lambda r: r["waktu"], reverse=True)
        if q:
            rows = [r for r in rows if q in " ".join([r["nama"], r["dari"], r["ke"]]).lower()]
        st.caption(f"{len(rows)} catatan (ditampilkan maksimal 300 terbaru)")
        st.dataframe(pd.DataFrame({
            "Waktu": [fmt_waktu(r["waktu"]) for r in rows[:300]],
            "Barang": [r["nama"] for r in rows[:300]],
            "Dari": [r["dari"] for r in rows[:300]],
            "Ke": [r["ke"] for r in rows[:300]],
            "Oleh": [r.get("oleh", "") for r in rows[:300]]}),
            hide_index=True, use_container_width=True)


# ------------------------------------------------------------ pinjam-meminjam
def cb_kembali(pid: str):
    def fn(data):
        for p in data["pinjam"]:
            if p["id"] == pid:
                p["kembali"] = hari_ini().isoformat()
    transaksi(fn, "Tandai kembali")


def cb_hapus_pinjam(pid: str):
    transaksi(lambda data: data.__setitem__("pinjam", [p for p in data["pinjam"] if p["id"] != pid]),
              "Hapus catatan pinjam")


if halaman == "Pinjam-meminjam":
    aktif = [p for p in D["pinjam"] if not p.get("kembali")]
    selesai = [p for p in D["pinjam"] if p.get("kembali")]
    tab1, tab2, tab3 = st.tabs([f"Sedang berjalan ({len(aktif)})", "Catat baru", f"Riwayat ({len(selesai)})"])
    with tab1:
        if not aktif:
            st.info("Tidak ada pinjaman yang sedang berjalan.")
        else:
            with st.container(key="kartu_tabel"):
                lebar = [3.4, 2.2, 2.2, 2.4, 1.6]
                kep = st.columns(lebar)
                for kol, judul in zip(kep, ["Barang", "Arah", "Orang", "Tanggal", "#"]):
                    kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                for p in sorted(aktif, key=lambda x: x.get("jatuh_tempo") or "9999"):
                    st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                    k = st.columns(lebar, vertical_alignment="center")
                    k[0].markdown(f'<div class="brg">{html.escape(p["nama"])}</div>'
                                  + (f'<div class="sub">{html.escape(p["catatan"])}</div>' if p.get("catatan") else ""),
                                  unsafe_allow_html=True)
                    k[1].write("Dipinjamkan ke orang" if p["arah"] == "keluar" else "Saya pinjam dari orang")
                    k[2].write(p.get("orang", ""))
                    s = sisa_hari(p.get("jatuh_tempo"))
                    ket = f"Sejak {fmt_iso(p.get('tgl', ''))}"
                    if p.get("jatuh_tempo"):
                        label = ("terlambat " + str(-s) + " hari") if s < 0 else f"{s} hari lagi"
                        warna = "tag-r" if s < 0 else ("tag-m" if s <= 3 else "")
                        k[3].markdown(f'{ket}<br><span class="tag {warna}">Jatuh tempo {fmt_iso(p["jatuh_tempo"])} '
                                      f'({label})</span>', unsafe_allow_html=True)
                    else:
                        k[3].write(ket)
                    k[4].button("Sudah kembali", key=f"kmb_{p['id']}", on_click=cb_kembali, args=(p["id"],))
    with tab2:
        with st.form(f"form_pinjam_{versi()}"):
            arah = st.radio("Jenis", ["Saya pinjamkan ke orang", "Saya pinjam dari orang"], horizontal=True)
            opsi = [""] + [b["id"] for b in sorted(D["barang"], key=lambda x: x["nama"].lower())]
            peta = {b["id"]: f"{b['nama']} — {nama_tempat(b)}" for b in D["barang"]}
            pilih = st.selectbox("Barang dari daftar", opsi,
                                 format_func=lambda i: "(Tidak ada di daftar, ketik di bawah)" if not i else peta[i])
            manual = st.text_input("Atau nama barang", placeholder="Isi kalau barangnya tidak ada di daftar")
            orang = st.text_input("Nama orang")
            p1, p2 = st.columns(2)
            tgl = p1.date_input("Tanggal", value=hari_ini(), format="DD/MM/YYYY")
            tempo = p2.date_input("Jatuh tempo (boleh kosong)", value=None, format="DD/MM/YYYY")
            cat = st.text_input("Catatan (boleh kosong)")
            if st.form_submit_button("Simpan", type="primary"):
                nama_b = manual.strip() or (next((b["nama"] for b in D["barang"] if b["id"] == pilih), ""))
                if not nama_b:
                    st.error("Pilih barang atau ketik namanya.")
                elif not orang.strip():
                    st.error("Nama orang wajib diisi.")
                else:
                    D["pinjam"].append({
                        "id": uuid.uuid4().hex[:8], "arah": "keluar" if arah.startswith("Saya pinjamkan") else "masuk",
                        "barang": pilih if not manual.strip() else "", "nama": nama_b, "orang": orang.strip(),
                        "tgl": tgl.isoformat(), "jatuh_tempo": tempo.isoformat() if tempo else "",
                        "kembali": "", "catatan": cat.strip()})
                    selesai_simpan("Tersimpan.")
    with tab3:
        if not selesai:
            st.info("Belum ada riwayat pinjaman.")
        else:
            rows = sorted(selesai, key=lambda x: x["kembali"], reverse=True)
            st.dataframe(pd.DataFrame({
                "Barang": [p["nama"] for p in rows],
                "Jenis": ["Dipinjamkan" if p["arah"] == "keluar" else "Saya pinjam" for p in rows],
                "Orang": [p.get("orang", "") for p in rows],
                "Tanggal": [fmt_iso(p.get("tgl", "")) for p in rows],
                "Kembali": [fmt_iso(p["kembali"]) for p in rows]}),
                hide_index=True, use_container_width=True)
            with st.expander("Hapus catatan riwayat"):
                for p in rows[:20]:
                    k = st.columns([6, 1.6], vertical_alignment="center")
                    k[0].write(f"{p['nama']} · {p.get('orang', '')} · {fmt_iso(p['kembali'])}")
                    k[1].button("Hapus", key=f"hpp_{p['id']}", on_click=cb_hapus_pinjam, args=(p["id"],))


# ------------------------------------------------------------- daftar belanja
def cb_beli(bid: str):
    qty = int(st.session_state.get(f"bel_qty_{bid}", 1))

    def fn(data):
        for b in data["barang"]:
            if b["id"] == bid:
                b["jumlah"] = jml(b) + qty
                b.pop("perlu_beli", None)
                b["diubah"] = hari_ini().isoformat()
    transaksi(fn, "Sudah dibeli")


if halaman == "Daftar belanja":
    daftar = sorted([b for b in D["barang"] if perlu_beli(b)], key=lambda x: x["nama"].lower())
    if not daftar:
        st.success("Tidak ada barang yang perlu dibeli. Tandai lewat Kelola barang > Perlu dibeli lagi, "
                   "atau otomatis kalau jumlahnya 0.")
    else:
        st.caption(f"{len(daftar)} barang. Barang berjumlah 0 otomatis masuk daftar ini.")
        st.download_button("Unduh daftar (teks)", "\n".join(f"- {b['nama']} (sisa {jml(b)})" for b in daftar),
                           file_name="daftar-belanja.txt", mime="text/plain")
        with st.container(key="kartu_tabel"):
            lebar = [3.6, 3, 1.2, 1.6, 1.8]
            kep = st.columns(lebar)
            for kol, judul in zip(kep, ["Barang", "Lokasi", "Sisa", "Jumlah beli", "#"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for b in daftar:
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                k[1].write(nama_tempat(b))
                k[2].write(jml(b))
                k[3].number_input("Jumlah beli", min_value=1, value=1, step=1, key=f"bel_qty_{b['id']}",
                                  label_visibility="collapsed")
                k[4].button("Sudah dibeli", key=f"beli_{b['id']}", on_click=cb_beli, args=(b["id"],))

# ------------------------------------------------------ kedaluwarsa dan garansi
if halaman == "Kedaluwarsa dan garansi":
    with st.container(key="kartu_filter"):
        jendela = st.selectbox("Tampilkan yang jatuh tempo dalam", [30, 60, 90, 365, 0], key="kd_win",
                               format_func=lambda n: "Semua" if n == 0 else f"{n} hari ke depan (termasuk yang sudah lewat)")

    def _daftar(kunci, judul, hanya_depan):
        item = []
        for b in D["barang"]:
            s = sisa_hari(b.get(kunci))
            if s is None or (hanya_depan and s < 0):
                continue
            if jendela and s > jendela:
                continue
            item.append((s, b))
        st.markdown(f"#### {judul} ({len(item)})")
        if not item:
            st.caption("Tidak ada.")
            return
        with st.container(key=f"kartu_g_{kunci}"):
            for s, b in sorted(item, key=lambda x: x[0]):
                k = st.columns([4, 3, 2.2, 2.6], vertical_alignment="center")
                k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                k[1].write(nama_tempat(b))
                k[2].write(fmt_iso(b[kunci]))
                if s < 0:
                    k[3].markdown(f'<span class="tag tag-r">Lewat {-s} hari</span>', unsafe_allow_html=True)
                else:
                    k[3].markdown(f'<span class="tag {"tag-m" if s <= BATAS_HARI else ""}">{s} hari lagi</span>',
                                  unsafe_allow_html=True)
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)

    _daftar("kedaluwarsa", "Kedaluwarsa", False)
    _daftar("garansi", "Garansi berakhir", True)
    if not any(b.get("kedaluwarsa") or b.get("garansi") for b in D["barang"]):
        st.info("Belum ada tanggal yang diisi. Isi di Kelola barang > Detail tambahan.")

# ----------------------------------------------------------------- nilai barang
if halaman == "Nilai barang":
    ada_harga = [b for b in D["barang"] if b.get("harga")]
    if not ada_harga:
        st.info("Belum ada harga yang diisi. Isi di Kelola barang > Detail tambahan.")
    else:
        nilai = lambda b: int(b.get("harga", 0) or 0) * jml(b)  # noqa: E731
        total = sum(nilai(b) for b in ada_harga)
        st.markdown(
            '<div class="statcard"><div class="sc-kiri"><span class="tag">Perkiraan</span>'
            f'<div class="sc-judul">{rp(total)}</div>'
            f'<div class="sc-ket">dari {len(ada_harga)} barang yang ada harganya</div></div>'
            f'<div class="sc-stat"><div class="sc-lab">Belum ada harga</div>'
            f'<div class="sc-val m">{len(D["barang"]) - len(ada_harga)}</div></div></div>',
            unsafe_allow_html=True)
        g1, g2 = st.columns(2)
        with g1.container(key="kartu_g1"):
            st.markdown("**Nilai per lokasi (Rp)**")
            per = {}
            for b in ada_harga:
                per[nama_lokasi(b)] = per.get(nama_lokasi(b), 0) + nilai(b)
            st.bar_chart(pd.DataFrame({"Lokasi": list(per), "Nilai": list(per.values())}),
                         x="Lokasi", y="Nilai", horizontal=True, sort="-Nilai", color="#2b7a57", height=300)
        with g2.container(key="kartu_g2"):
            st.markdown("**Nilai per kategori (Rp)**")
            per = {}
            for b in ada_harga:
                per[nama_kat(b)] = per.get(nama_kat(b), 0) + nilai(b)
            st.bar_chart(pd.DataFrame({"Kategori": list(per), "Nilai": list(per.values())}),
                         x="Kategori", y="Nilai", horizontal=True, sort="-Nilai", color="#2f5d9e", height=300)
        urut = sorted(ada_harga, key=nilai, reverse=True)
        st.dataframe(pd.DataFrame({
            "Barang": [b["nama"] for b in urut], "Lokasi": [nama_tempat(b) for b in urut],
            "Jumlah": [jml(b) for b in urut], "Harga satuan": [rp(b["harga"]) for b in urut],
            "Nilai": [rp(nilai(b)) for b in urut]}), hide_index=True, use_container_width=True)


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
                n_pakai = sum(1 for b in D["barang"] if b.get(kunci) == x["id"])
                c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_pakai} barang jadi tanpa {judul.lower()})"
                                                       if n_pakai else ""))
                c3.button("Batal", key=f"bh_{kunci}_{x['id']}", on_click=atur, args=(k_hapus, None))
                if c2.button("Ya, hapus", key=f"yh_{kunci}_{x['id']}", type="primary"):
                    D[kunci] = [y for y in D[kunci] if y["id"] != x["id"]]
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
    peta = {l["id"]: l["nama"] for l in D["lokasi"]}
    with st.expander(f"Sub lokasi ({len(D['sublokasi'])})", expanded=True):
        st.caption("Sub lokasi berada di bawah satu lokasi (misalnya Kotak 2 di Lemari kamar). "
                   "Menghapus sub lokasi tidak menghapus barangnya.")
        for l in D["lokasi"]:
            milik = [x for x in D["sublokasi"] if x["lokasi"] == l["id"]]
            st.markdown(f'<div class="bidang">{html.escape(l["nama"])} · {len(milik)} sub lokasi</div>',
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


def png_qr(teks: str, skala: int = 8) -> bytes:
    import segno
    buf = io.BytesIO()
    segno.make(teks, error="m").save(buf, kind="png", scale=skala, border=2)
    return buf.getvalue()


def halaman_label_qr():
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di menu Lokasi.")
        return
    try:
        base = str(st.secrets.get("app_url", "")).strip()
    except Exception:
        base = ""
    with st.container(key="kartu_filter"):
        if not base:
            base = st.text_input("Alamat aplikasi (URL)", key="qr_url", placeholder="https://namaapp.streamlit.app",
                                 help="Bisa diisi permanen di Secrets sebagai app_url.").strip()
        else:
            st.caption(f"Alamat aplikasi: {base}")
        item = {}
        for l in D["lokasi"]:
            item[f"l:{l['id']}"] = (l["nama"], {"lokasi": l["id"]})
            for s in D["sublokasi"]:
                if s["lokasi"] == l["id"]:
                    item[f"s:{s['id']}"] = (f"{l['nama']} › {s['nama']}", {"lokasi": l["id"], "sub": s["id"]})
        awal = [k for k in item if k.startswith("l:")]
        pilih = st.multiselect("Label yang dibuat", list(item), default=awal, key="qr_pilih",
                               format_func=lambda k: item[k][0])
    if not base:
        st.info("Isi alamat aplikasi dulu supaya kode QR bisa dibuat.")
        return
    if not pilih:
        return
    try:
        kartu, cols = [], st.columns(4)
        for i, k in enumerate(pilih):
            label, par = item[k]
            png = png_qr(f"{base.rstrip('/')}/?{urlencode(par)}")
            kartu.append((label, png))
            with cols[i % 4]:
                st.image(png, width=150, caption=label)
                st.download_button("Unduh PNG", png, file_name=f"qr-{k.replace(':', '-')}.png",
                                   mime="image/png", key=f"dlqr_{k}")
    except ImportError:
        st.error("Paket segno belum terpasang. Tambahkan `segno` di requirements.txt.")
        return
    sel = "".join(f'<div class="k"><img src="data:image/png;base64,{base64.b64encode(p).decode()}">'
                  f'<div>{html.escape(n)}</div></div>' for n, p in kartu)
    dok = ("<!doctype html><meta charset='utf-8'><title>Label QR</title><style>"
           "body{font-family:sans-serif}.g{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}"
           ".k{border:1px dashed #999;padding:8px;text-align:center;break-inside:avoid;font-size:13px}"
           "img{width:100%;max-width:160px}</style>" + f"<div class='g'>{sel}</div>")
    st.download_button("Unduh lembar label (HTML untuk dicetak)", dok, file_name="label-qr.html",
                       mime="text/html", type="primary")
    st.caption("Buka file HTML itu di peramban lalu cetak (Ctrl+P). Tempel labelnya di kotak atau lemari. "
               "Memindainya membuka aplikasi dan menampilkan isi lokasi tersebut (perlu login).")


def cadangan():
    with st.expander("Cadangan dan pindah data", expanded=True):
        st.caption("Unduh seluruh data sebagai file, atau muat file data dari tempat lain. "
                   "Memuat file akan **mengganti semua data** yang ada sekarang. "
                   "Foto tidak ikut dalam file ini; foto tersimpan di folder fotos/ pada repo data. "
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


if adalah_admin() and halaman == "Lokasi":
    daftar_sederhana("Lokasi", "lokasi", "Tempat penyimpanan, misalnya lemari atau kotak. "
                     "Menghapus lokasi ikut menghapus sub lokasinya. Barangnya tidak terhapus.")
if adalah_admin() and halaman == "Sub lokasi":
    halaman_sublokasi()
if adalah_admin() and halaman == "Kategori":
    daftar_sederhana("Kategori", "kategori", "Pengelompokan jenis barang, misalnya pakaian atau perawatan diri. "
                     "Boleh dikosongkan kalau tidak diperlukan.")
if adalah_admin() and halaman == "Label QR":
    halaman_label_qr()
if adalah_admin() and halaman == "Cadangan dan pindah data":
    cadangan()
