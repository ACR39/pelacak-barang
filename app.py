import base64
import json
import uuid
from datetime import date

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Pelacak Barang", page_icon="📦", layout="wide")

DATA_FILE = "items.json"
LOCAL_FALLBACK = "items_local.json"


# ---------- Penyimpanan: GitHub (utama) atau file lokal (cadangan) ----------
def gh_conf():
    try:
        s = st.secrets["github"]
        return s["token"], s["repo"], s.get("branch", "main")
    except Exception:
        return None


def load_items():
    conf = gh_conf()
    if conf:
        token, repo, branch = conf
        r = requests.get(
            f"https://api.github.com/repos/{repo}/contents/{DATA_FILE}",
            headers={"Authorization": f"Bearer {token}"},
            params={"ref": branch},
            timeout=20,
        )
        if r.status_code == 200:
            j = r.json()
            st.session_state["sha"] = j["sha"]
            return json.loads(base64.b64decode(j["content"]).decode("utf-8"))
        if r.status_code == 404:
            st.session_state["sha"] = None
            return []
        st.error(f"Gagal membaca GitHub: {r.status_code} {r.text[:200]}")
        return []
    try:
        with open(LOCAL_FALLBACK, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_items(items, message="Update barang"):
    conf = gh_conf()
    if conf:
        token, repo, branch = conf
        payload = {
            "message": message,
            "content": base64.b64encode(
                json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8")
            ).decode(),
            "branch": branch,
        }
        if st.session_state.get("sha"):
            payload["sha"] = st.session_state["sha"]
        r = requests.put(
            f"https://api.github.com/repos/{repo}/contents/{DATA_FILE}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=20,
        )
        if r.status_code in (200, 201):
            st.session_state["sha"] = r.json()["content"]["sha"]
        else:
            st.error(f"Gagal menyimpan ke GitHub: {r.status_code} {r.text[:200]}")
    else:
        with open(LOCAL_FALLBACK, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)


# ---------- Login sederhana (opsional) ----------
def check_password():
    try:
        pw = st.secrets["app_password"]
    except Exception:
        return True
    if st.session_state.get("auth"):
        return True
    entered = st.text_input("Kata sandi", type="password")
    if entered:
        if entered == pw:
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Kata sandi salah")
    return False


if not check_password():
    st.stop()

# ---------- Data ----------
if "items" not in st.session_state:
    st.session_state["items"] = load_items()
items = st.session_state["items"]

st.title("📦 Pelacak Barang Pribadi")
if not gh_conf():
    st.warning(
        "Mode lokal: data belum disimpan ke GitHub (secrets belum diatur). "
        "Di Streamlit Cloud, data lokal bisa hilang saat aplikasi restart."
    )

tab_cari, tab_tambah, tab_kelola = st.tabs(["🔍 Cari", "➕ Tambah", "🛠️ Kelola"])

# ---------- Cari ----------
with tab_cari:
    q = st.text_input("Cari barang atau lokasi", placeholder="mis. parfum, lemari kamar")
    kategori_all = sorted({i.get("kategori", "") for i in items if i.get("kategori")})
    lokasi_all = sorted({i.get("lokasi", "") for i in items if i.get("lokasi")})
    c1, c2 = st.columns(2)
    f_kat = c1.multiselect("Kategori", kategori_all)
    f_lok = c2.multiselect("Lokasi", lokasi_all)

    hasil = items
    if q:
        ql = q.lower()
        hasil = [
            i for i in hasil
            if ql in i["nama"].lower()
            or ql in i.get("lokasi", "").lower()
            or ql in i.get("catatan", "").lower()
        ]
    if f_kat:
        hasil = [i for i in hasil if i.get("kategori") in f_kat]
    if f_lok:
        hasil = [i for i in hasil if i.get("lokasi") in f_lok]

    st.caption(f"{len(hasil)} dari {len(items)} barang")
    if hasil:
        df = pd.DataFrame(hasil)[["nama", "lokasi", "kategori", "jumlah", "catatan", "diubah"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada barang yang cocok.")

    if items:
        st.subheader("Ringkasan per lokasi")
        per_lok = {}
        for i in items:
            per_lok.setdefault(i.get("lokasi", "-"), []).append(i["nama"])
        for lok, names in sorted(per_lok.items()):
            with st.expander(f"{lok} ({len(names)})"):
                st.write(", ".join(sorted(names)))

# ---------- Tambah ----------
with tab_tambah:
    with st.form("tambah", clear_on_submit=True):
        nama = st.text_input("Nama barang*")
        lokasi = st.text_input("Lokasi*", placeholder="mis. Lemari kotak 2")
        c1, c2 = st.columns(2)
        kategori = c1.text_input("Kategori", placeholder="mis. Pakaian")
        jumlah = c2.number_input("Jumlah", min_value=1, value=1, step=1)
        catatan = st.text_area("Catatan")
        if st.form_submit_button("Simpan"):
            if not nama.strip() or not lokasi.strip():
                st.error("Nama dan lokasi wajib diisi.")
            else:
                items.append({
                    "id": uuid.uuid4().hex[:8],
                    "nama": nama.strip(),
                    "lokasi": lokasi.strip(),
                    "kategori": kategori.strip(),
                    "jumlah": int(jumlah),
                    "catatan": catatan.strip(),
                    "diubah": date.today().isoformat(),
                })
                save_items(items, f"Tambah {nama.strip()}")
                st.success("Tersimpan!")

# ---------- Kelola ----------
with tab_kelola:
    if not items:
        st.info("Belum ada barang.")
    else:
        opsi = {f'{i["nama"]} — {i.get("lokasi","")} ({i["id"]})': i for i in items}
        pilih = st.selectbox("Pilih barang", list(opsi.keys()))
        it = opsi[pilih]
        with st.form("edit"):
            nama_e = st.text_input("Nama", it["nama"])
            lokasi_e = st.text_input("Lokasi", it.get("lokasi", ""))
            c1, c2 = st.columns(2)
            kat_e = c1.text_input("Kategori", it.get("kategori", ""))
            jml_e = c2.number_input("Jumlah", min_value=0, value=int(it.get("jumlah", 1)), step=1)
            cat_e = st.text_area("Catatan", it.get("catatan", ""))
            simpan = st.form_submit_button("Perbarui")
        if simpan:
            it.update(nama=nama_e.strip(), lokasi=lokasi_e.strip(), kategori=kat_e.strip(),
                      jumlah=int(jml_e), catatan=cat_e.strip(), diubah=date.today().isoformat())
            save_items(items, f"Ubah {it['nama']}")
            st.success("Diperbarui!")
            st.rerun()
        if st.button("🗑️ Hapus barang ini"):
            items[:] = [i for i in items if i["id"] != it["id"]]
            save_items(items, f"Hapus {it['nama']}")
            st.rerun()

    st.divider()
    st.download_button(
        "⬇️ Unduh cadangan (JSON)",
        json.dumps(items, ensure_ascii=False, indent=2),
        file_name="barang.json",
        mime="application/json",
    )
