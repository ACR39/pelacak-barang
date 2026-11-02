"""Impor barang dari Excel atau CSV."""
import io
import re
import uuid
from datetime import datetime

import pandas as pd
import streamlit as st

from pelacak.bantu import RE_URL, _norm_nama, _url_aman, catat, nama_tempat, selesai_simpan, versi
from pelacak.inti import D, TGL_MAX, TGL_MIN, adalah_admin, hari_ini


# ------------------------------------------------------------ impor dari Excel / CSV
KOLOM_IMPOR = [("nama", "Nama barang"), ("jumlah", "Jumlah"), ("tempat", "Tempat"), ("lokasi", "Lokasi"),
               ("sub", "Sub lokasi"), ("kategori", "Kategori"), ("pemilik", "Pemilik"), ("merek", "Merek"),
               ("ukuran", "Ukuran"), ("warna", "Warna"), ("seri", "Nomor seri"), ("barcode", "Barcode"),
               ("harga", "Harga beli"), ("dibeli", "Tanggal beli"), ("kedaluwarsa", "Kedaluwarsa"),
               ("garansi", "Garansi sampai"), ("label", "Label"), ("catatan", "Catatan"), ("tautan", "Tautan"),
               ("favorit", "Favorit")]


ALIAS_IMPOR = {"nama": ["nama", "barang"], "sub": ["sublokasi", "sub"], "harga": ["harga"], "dibeli": ["dibeli"],
               "garansi": ["garansi"], "seri": ["seri", "no seri"], "label": ["tag", "labels"],
               "kedaluwarsa": ["expired", "exp"]}


MAKS_IMPOR = 1000


def _s(v) -> str:
    s = "" if v is None else str(v).strip()
    return "" if s.lower() in ("nan", "nat", "none") else s


def _angka_impor(s: str):
    """Bilangan bulat dari teks seperti '1.500.000', 'Rp 25000', atau '3.0'. None kalau tidak terbaca."""
    s = _s(s)
    if not s:
        return None
    if re.fullmatch(r"\d+\.0+", s):
        return int(float(s))
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def _tgl_impor(s: str):
    """(iso, galat). Terima 2026-01-31, 31/01/2026, 31-01-2026, 31.01.2026."""
    s = _s(s)
    if not s:
        return "", ""
    s = s.split(" ")[0] if re.match(r"\d{4}-\d{2}-\d{2}", s) else s
    for f in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            d = datetime.strptime(s, f).date()
        except ValueError:
            continue
        if TGL_MIN <= d <= TGL_MAX:
            return d.isoformat(), ""
        break
    return "", f"tanggal '{s}' tidak dikenali (pakai format 31/01/2026)"


def baca_tabel(berkas) -> pd.DataFrame:
    nama = berkas.name.lower()
    if nama.endswith((".xlsx", ".xlsm")):
        xl = pd.ExcelFile(io.BytesIO(berkas.getvalue()), engine="openpyxl")
        sheet = "Barang" if "Barang" in xl.sheet_names else xl.sheet_names[0]
        return xl.parse(sheet, dtype=str)
    mentah = berkas.getvalue()
    try:
        teks = mentah.decode("utf-8-sig")
    except UnicodeDecodeError:
        teks = mentah.decode("latin-1")
    return pd.read_csv(io.StringIO(teks), dtype=str, sep=None, engine="python")


def _cari_m(M: dict, kunci: str, nama: str, **kond) -> list:
    n = _norm_nama(nama)
    return [x for x in M[kunci] if _norm_nama(x["nama"]) == n and all((x.get(k) or "") == v for k, v in kond.items())]


def selesaikan_m(M: dict, r: dict, buat: bool):
    """Cocokkan nama tempat/lokasi/sub lokasi/kategori sebuah baris dengan data master M (dibuat kalau perlu).
    Mengembalikan (ids, galat, dibuat)."""
    dibuat = []

    def ambil(kunci, nama, label, **kond):
        c = _cari_m(M, kunci, nama, **kond)
        if len(c) > 1 and kunci == "lokasi" and "tempat" not in kond:
            return None, f"lokasi '{nama}' ada di beberapa tempat, isi kolom Tempat"
        if c:
            return c[0]["id"], ""
        if not buat:
            return None, f"{label} '{nama}' belum ada"
        x = {"id": uuid.uuid4().hex[:8], "nama": nama, **{k: v for k, v in kond.items() if v}}
        M[kunci].append(x)
        dibuat.append(f"{label} {nama}")
        return x["id"], ""

    tid = ""
    if r["tempat"]:
        tid, g = ambil("tempat", r["tempat"], "tempat")
        if g:
            return None, g, dibuat
    kond = {"tempat": tid} if tid else {}
    lid, g = ambil("lokasi", r["lokasi"], "lokasi", **kond)
    if g:
        return None, g, dibuat
    ids = {"lokasi": lid, "sublokasi": "", "kategori": ""}
    if r["sub"]:
        ids["sublokasi"], g = ambil("sublokasi", r["sub"], "sub lokasi", lokasi=lid)
        if g:
            return None, g, dibuat
    if r["kategori"]:
        ids["kategori"], g = ambil("kategori", r["kategori"], "kategori")
        if g:
            return None, g, dibuat
    return ids, "", dibuat


def _ada_kembar_b(M_ids: dict, nama: str) -> bool:
    n = _norm_nama(nama)
    return any(_norm_nama(b["nama"]) == n and b.get("lokasi") == M_ids["lokasi"]
               and (b.get("sublokasi") or "") == M_ids["sublokasi"] for b in D["barang"])


def urai_impor(df: pd.DataFrame, buat: bool):
    """Baca tabel jadi daftar baris yang sudah divalidasi, tanpa mengubah data.
    Mengembalikan (baris, galat_umum, akan_dibuat)."""
    import copy
    kepala = {_norm_nama(c): c for c in df.columns}
    peta = {}
    for kunci, label in KOLOM_IMPOR:
        for a in [label] + ALIAS_IMPOR.get(kunci, []):
            if _norm_nama(a) in kepala:
                peta[kunci] = kepala[_norm_nama(a)]
                break
    if "nama" not in peta or "lokasi" not in peta:
        return None, "Kolom wajib 'Nama barang' dan 'Lokasi' tidak ditemukan di baris pertama file.", []
    M = {k: copy.deepcopy(D[k]) for k in ("tempat", "lokasi", "sublokasi", "kategori")}
    baris, akan = [], []
    for no, (_, row) in enumerate(df.iterrows(), start=2):
        v = {k: _s(row[c]) for k, c in peta.items()}
        if not any(v.values()):
            continue
        r = {k: v.get(k, "") for k, _ in KOLOM_IMPOR}
        galat = []
        if not r["nama"]:
            galat.append("nama kosong")
        if not r["lokasi"]:
            galat.append("lokasi kosong")
        jml = 1
        if r["jumlah"]:
            jml = _angka_impor(r["jumlah"])
            if jml is None:
                galat.append(f"jumlah '{r['jumlah']}' bukan angka")
                jml = 1
        harga = 0
        if r["harga"]:
            harga = _angka_impor(r["harga"])
            if harga is None:
                galat.append(f"harga '{r['harga']}' bukan angka")
                harga = 0
        tgl = {}
        for k in ("dibeli", "kedaluwarsa", "garansi"):
            tgl[k], g = _tgl_impor(r[k])
            if g:
                galat.append(f"{k}: {g}")
        urls = []
        if r["tautan"]:
            urls = list(dict.fromkeys(_url_aman(m.group(0)) for m in RE_URL.finditer(r["tautan"])))
            urls = [u for u in urls if u]
            if not urls:
                galat.append("tautan harus diawali http:// atau https://")
        label = list(dict.fromkeys(t.strip()[:30] for t in re.split(r"[,;]", r["label"]) if t.strip()))[:8]
        info = {"no": no, "nama": r["nama"], "lokasi_txt": " › ".join(x for x in (r["tempat"], r["lokasi"], r["sub"]) if x),
                "r": r, "jumlah": jml, "harga": harga or 0, "tgl": tgl, "tautan": "\n".join(urls), "label": label,
                "favorit": r["favorit"].lower() in ("ya", "y", "1", "true", "x", "★", "iya"),
                "galat": galat, "dup": False}
        if not galat:
            ids, g, dibuat = selesaikan_m(M, r, buat)
            if g:
                info["galat"].append(g)
            else:
                akan += [x for x in dibuat if x not in akan]
                info["dup"] = _ada_kembar_b(ids, r["nama"])
        baris.append(info)
    return baris, "", akan


def terapkan_impor(baris: list, buat: bool, lewati: bool):
    baru = lewat = 0
    for info in baris:
        if info["galat"]:
            continue
        r = info["r"]
        ids, g, _ = selesaikan_m(D, r, buat)
        if g:
            continue
        if lewati and _ada_kembar_b(ids, r["nama"]):
            lewat += 1
            continue
        b = {"id": uuid.uuid4().hex[:8], "nama": r["nama"][:120], "lokasi": ids["lokasi"], "jumlah": info["jumlah"],
             "diubah": hari_ini().isoformat()}
        for k in ("sublokasi", "kategori"):
            if ids[k]:
                b[k] = ids[k]
        for k in ("pemilik", "merek", "ukuran", "warna", "seri", "barcode", "catatan"):
            if r[k]:
                b[k] = r[k]
        if info["harga"]:
            b["harga"] = info["harga"]
        for k, v in info["tgl"].items():
            if v:
                b[k] = v
        if info["tautan"]:
            b["tautan"] = info["tautan"]
        if info["label"]:
            b["tag"] = info["label"]
        if info["favorit"]:
            b["favorit"] = True
        catat(b["id"], b["nama"], "", nama_tempat(b))
        D["barang"].append(b)
        baru += 1
    return baru, lewat


def buat_templat_impor() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Barang"
    ws.append([lab for _, lab in KOLOM_IMPOR])
    for i, (k, lab) in enumerate(KOLOM_IMPOR, start=1):
        c = ws.cell(1, i)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F5C44" if k in ("nama", "lokasi") else "5B6573")
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[c.column_letter].width = max(14, len(lab) + 4)
    ws.freeze_panes = "A2"
    pt = wb.create_sheet("Petunjuk")
    for baris in ("Isi satu barang per baris di lembar Barang. Kolom hijau (Nama barang, Lokasi) wajib diisi.",
                  "Tempat, Lokasi, Sub lokasi, dan Kategori ditulis dengan nama. Kalau belum ada, admin bisa membuatnya otomatis saat impor.",
                  "Jumlah kosong dianggap 1. Harga beli boleh ditulis 1500000 atau 1.500.000.",
                  "Tanggal ditulis 31/01/2026 atau 2026-01-31.",
                  "Label boleh lebih dari satu, pisahkan dengan koma. Favorit diisi Ya kalau ingin ditandai.",
                  "Tautan harus diawali http:// atau https://.",
                  "Contoh baris: Charger | 2 | Rumah A | Lemari kamar | Laci 2 | Elektronik | | Anker | | Hitam"):
        pt.append([baris])
    pt.column_dimensions["A"].width = 120
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def halaman_impor():
    with st.container(key="kartu_g_impor"):
        st.caption("Isi daftar barang di Excel atau CSV, lalu unggah di sini. Kamu akan melihat pratinjau dulu "
                   "sebelum apa pun disimpan.")
        try:
            st.download_button("Unduh templat Excel", buat_templat_impor(), file_name="templat-impor-barang.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               icon=":material/download:")
        except ImportError:
            st.warning("Pustaka openpyxl belum terpasang, jadi templat tidak bisa dibuat. File CSV tetap bisa diunggah.")
        buat = False
        if adalah_admin():
            buat = st.checkbox("Buat tempat, lokasi, sub lokasi, dan kategori yang belum ada", value=True, key="im_buat")
        else:
            st.caption("Nama tempat, lokasi, dan kategori harus sudah ada. Minta admin menambahkannya kalau belum.")
        lewati = st.checkbox("Lewati barang yang sudah ada (nama sama di lokasi yang sama)", value=True, key="im_lewati")
        berkas = st.file_uploader("File Excel atau CSV", type=["xlsx", "xlsm", "csv"], key=f"im_up_{versi()}")
        if berkas is None:
            return
        try:
            df = baca_tabel(berkas)
        except Exception as e:
            st.error(f"File tidak bisa dibaca: {e}")
            return
        if len(df) > MAKS_IMPOR:
            st.error(f"Terlalu banyak baris ({len(df)}). Maksimal {MAKS_IMPOR} baris sekali impor.")
            return
        baris, galat_umum, akan = urai_impor(df, buat)
        if galat_umum:
            st.error(galat_umum)
            return
        if not baris:
            st.info("Tidak ada baris yang berisi data.")
            return
        salah = [x for x in baris if x["galat"]]
        kembar = [x for x in baris if not x["galat"] and x["dup"] and lewati]
        siap = [x for x in baris if not x["galat"] and not (x["dup"] and lewati)]
        st.markdown(f"**{len(siap)} siap diimpor** · {len(kembar)} sudah ada (dilewati) · {len(salah)} bermasalah")
        if akan:
            st.caption("Akan dibuat: " + ", ".join(akan[:12]) + (f" dan {len(akan) - 12} lainnya" if len(akan) > 12 else ""))
        tabel = []
        for x in baris:
            status = ("Bermasalah: " + "; ".join(x["galat"]) if x["galat"]
                      else "Sudah ada, dilewati" if x["dup"] and lewati else "Siap")
            tabel.append({"Baris": x["no"], "Barang": x["nama"], "Jumlah": x["jumlah"], "Lokasi": x["lokasi_txt"], "Status": status})
        st.dataframe(pd.DataFrame(tabel).head(150), hide_index=True, use_container_width=True)
        if len(tabel) > 150:
            st.caption(f"Pratinjau menampilkan 150 baris pertama dari {len(tabel)}.")
        if salah:
            st.warning("Baris yang bermasalah tidak ikut diimpor. Perbaiki di file lalu unggah ulang, atau lanjutkan "
                       "untuk baris yang siap.")
        if st.button(f"Impor {len(siap)} barang", type="primary", disabled=not siap, key="im_go"):
            n, lewat = terapkan_impor(baris, buat, lewati)
            selesai_simpan(f"{n} barang diimpor." + (f" {lewat} dilewati karena sudah ada." if lewat else ""))
