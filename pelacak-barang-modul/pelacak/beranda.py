"""Beranda dan pembantu pengingat berkala."""
import html
from datetime import timedelta

import pandas as pd
import streamlit as st

from pelacak.bantu import (
    induk_dari, jumlah_b, kumpul_perhatian, lokasi_dari, nama_kat, nama_lok, nama_lokasi,
    nama_tempat, perlu_beli, pindah_halaman, status_sisa,
)
from pelacak.inti import D, fmt_iso, hari_ini, iso_ke_date, sisa_hari, teks_cek


# -------------------------------------------------------------------- beranda
def pesan_tenggat() -> list:
    """Peminjaman yang tenggat pengembaliannya jatuh hari ini dan belum dikembalikan."""
    hasil = []
    for p in D["pinjam"]:
        if p.get("kembali") or sisa_hari(p.get("tenggat")) != 0:
            continue
        if p.get("arah") == "keluar":
            hasil.append(f"{p.get('orang', '')} perlu mengembalikan {p.get('nama', '')} hari ini")
        else:
            hasil.append(f"Kembalikan {p.get('nama', '')} ke {p.get('orang', '')} hari ini")
    return hasil


# ------------------------------------------------------------ pengingat berkala (pembantu)
CEK_OPSI = [0, 30, 60, 90, 180, 365]


def cek_tiap_b(b: dict) -> int:
    try:
        return max(int(b.get("cek_tiap", 0) or 0), 0)
    except Exception:
        return 0


def sisa_cek(b: dict):
    """Hari menuju jadwal cek berikutnya (negatif = sudah lewat), None kalau tidak ada pengingat."""
    n = cek_tiap_b(b)
    if not n:
        return None
    ref = iso_ke_date(b.get("cek_terakhir")) or iso_ke_date(b.get("diubah")) or hari_ini()
    return (ref + timedelta(days=n) - hari_ini()).days


def jadwal_cek() -> list:
    return sorted([(sisa_cek(b), b) for b in D["barang"] if cek_tiap_b(b)], key=lambda x: (x[0], x[1]["nama"].lower()))


OPNAME_HARI = 90


def jadwal_opname() -> list:
    """Lokasi yang sudah waktunya diinventarisasi ulang: [(hari sejak pemeriksaan terlama atau None, lokasi, jumlah barang)].
    None berarti ada barang di lokasi itu yang belum pernah diinventarisasi."""
    hasil = []
    for l in D["lokasi"]:
        isi = [b for b in D["barang"] if b.get("lokasi") == l["id"] and not b.get("dibawa")]
        if not isi:
            continue
        tgl = [iso_ke_date(b.get("opname")) for b in isi]
        sejak = None if any(t is None for t in tgl) else (hari_ini() - min(tgl)).days
        if sejak is None or sejak >= OPNAME_HARI:
            hasil.append((sejak, l, len(isi)))
    return sorted(hasil, key=lambda x: (x[0] is not None, -(x[0] or 0), nama_lok(x[1]).lower()))


def buka_opname(id_lokasi: str):
    pindah_halaman("Inventaris ulang")
    st.session_state.op_lok = id_lokasi
    st.session_state.op_sub = "semua"


SEKSI_BERANDA = [("ringkasan", "Ringkasan angka"), ("perhatian", "Perlu perhatian"),
                 ("dibawa", "Sedang dibawa dan hilang"), ("favorit", "Barang favorit"), ("opname", "Lokasi yang perlu diinventarisasi"),
                 ("cek", "Waktunya dicek (pengingat berkala)"), ("pinjam", "Sedang dipinjam"),
                 ("g_lokasi", "Grafik jenis barang per lokasi"), ("g_kategori", "Grafik jenis barang per kategori")]


COOKIE_BERANDA = "barang_beranda"


def ubah_beranda():
    st.session_state.beranda_sembunyi = [k for k, _ in SEKSI_BERANDA if not st.session_state.get(f"bs_{k}", True)]
    st.session_state.beranda_ubah = True


def atur_beranda(sembunyi: list):
    for k, _ in SEKSI_BERANDA:
        st.session_state[f"bs_{k}"] = k not in sembunyi
    ubah_beranda()


def muat_beranda_sembunyi():
    """Pilihan kartu Beranda diingat di perangkat ini lewat cookie."""
    if "beranda_sembunyi" not in st.session_state:
        try:
            ck = st.context.cookies.get(COOKIE_BERANDA)
        except Exception:
            ck = None
        if not isinstance(ck, str):
            ck = ",".join(D.get("pengaturan", {}).get("beranda", []))
        sah = {k for k, _ in SEKSI_BERANDA}
        st.session_state.beranda_sembunyi = [k for k in ck.split(",") if k in sah]


def halaman_beranda():
    muat_beranda_sembunyi()
    sembunyi = set(st.session_state.beranda_sembunyi)
    brg = D["barang"]
    if not brg:
        st.info("Belum ada barang. Tambahkan lewat menu Barang > Kelola barang.")
    else:
        total_jml = sum(jumlah_b(b) for b in brg)
        lok_dipakai = len({b.get("lokasi") for b in brg if lokasi_dari(b)})
        tanpa_lok = sum(1 for b in brg if lokasi_dari(b) is None)
        n_beli = sum(1 for b in brg if perlu_beli(b))
        n_pinjam = sum(1 for p in D["pinjam"] if not p.get("kembali"))
        if "ringkasan" not in sembunyi:
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

        if "perhatian" not in sembunyi:
            with st.container(key="kartu_perhatian"):
                st.markdown("**Perlu perhatian**")
                hal = kumpul_perhatian()
                if hal:
                    for h in hal:
                        st.markdown(f'<div class="perhatian">{h}</div>', unsafe_allow_html=True)
                else:
                    st.caption("Tidak ada yang perlu diperhatikan sekarang.")

        if "dibawa" not in sembunyi:
            dibawa_l = [b for b in brg if b.get("dibawa") and not (induk_dari(b) and induk_dari(b).get("dibawa"))]
            hilang_l = [b for b in brg if b.get("hilang")]
            with st.container(key="kartu_g_dibawa_b"):
                st.markdown("**Sedang dibawa dan hilang**")
                if not dibawa_l and not hilang_l:
                    st.caption("Tidak ada barang yang sedang dibawa atau hilang.")
                for b in dibawa_l:
                    ke = f" ke {html.escape(b['dibawa_ke'])}" if b.get("dibawa_ke") else ""
                    st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(b["nama"])}'
                                f'<span class="lencana lc-b">Sedang dibawa</span></div>'
                                f'<div class="sub">Sejak {fmt_iso(b["dibawa"])}{ke} · asal: '
                                f'{html.escape(nama_tempat(b))}</div></div>', unsafe_allow_html=True)
                for b in hilang_l:
                    di = f", terakhir terlihat di {html.escape(b['hilang_di'])}" if b.get("hilang_di") else ""
                    st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(b["nama"])}'
                                f'<span class="lencana lc-r">Hilang</span></div>'
                                f'<div class="sub">Sejak {fmt_iso(b["hilang"])}{di}</div></div>', unsafe_allow_html=True)

        if "cek" not in sembunyi:
            with st.container(key="kartu_g_cek"):
                st.markdown("**Waktunya dicek**")
                _jt = [(s, b) for s, b in jadwal_cek() if s <= 7]
                if not _jt:
                    st.caption("Tidak ada barang yang perlu dicek dalam 7 hari ke depan.")
                for s, b in _jt[:8]:
                    st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(b["nama"])}</div>'
                                f'<div class="sub">{html.escape(nama_tempat(b))} · {teks_cek(b["cek_tiap"]).lower()} · '
                                f'{status_sisa(s)}</div></div>', unsafe_allow_html=True)
                if len(_jt) > 8:
                    st.caption(f"Dan {len(_jt) - 8} barang lain di menu Jatuh tempo (tab Cek berkala).")

        if "favorit" not in sembunyi:
            fav_l = sorted([b for b in brg if b.get("favorit")], key=lambda x: x["nama"].lower())
            with st.container(key="kartu_g_fav"):
                st.markdown("**Barang favorit**")
                if not fav_l:
                    st.caption("Belum ada favorit. Tandai barang yang sering kamu cari lewat Kelola barang.")
                for b in fav_l[:8]:
                    st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(b["nama"])}</div>'
                                f'<div class="sub">{html.escape(nama_tempat(b))} · {jumlah_b(b)} buah</div></div>',
                                unsafe_allow_html=True)
                if len(fav_l) > 8:
                    st.caption(f"Dan {len(fav_l) - 8} favorit lain. Pakai 'Hanya favorit' di Cari barang.")

        if "opname" not in sembunyi:
            jo = jadwal_opname()
            with st.container(key="kartu_g_opname"):
                st.markdown("**Perlu inventaris ulang**")
                if not jo:
                    st.caption(f"Semua lokasi sudah diinventarisasi dalam {OPNAME_HARI} hari terakhir.")
                for sejak, l, n_isi in jo[:5]:
                    ket = "Ada barang yang belum pernah diinventarisasi" if sejak is None else f"Terakhir {sejak} hari lalu"
                    k1, k2 = st.columns([3, 1.2], vertical_alignment="center")
                    k1.markdown(f'<div class="perhatian"><div class="brg">{html.escape(nama_lok(l))}</div>'
                                f'<div class="sub">{n_isi} barang · {ket}</div></div>', unsafe_allow_html=True)
                    k2.button("Periksa", key=f"kpakai_op_{l['id']}", on_click=buka_opname, args=(l["id"],),
                              use_container_width=True)
                if len(jo) > 5:
                    st.caption(f"Dan {len(jo) - 5} lokasi lain di menu Inventaris ulang.")

        if "pinjam" not in sembunyi:
            with st.container(key="kartu_tgl_pinjam"):
                st.markdown("**Sedang dipinjam**")
                aktif_p = sorted([p for p in D["pinjam"] if not p.get("kembali")],
                                 key=lambda x: (x.get("tenggat") or "9999-12-31", x.get("tanggal", "")))
                if not aktif_p:
                    st.caption("Tidak ada barang yang sedang dipinjam.")
                for p in aktif_p:
                    tanda = ('<span class="lencana lc-m">Dipinjamkan</span>' if p.get("arah") == "keluar"
                             else '<span class="lencana lc-b">Saya pinjam</span>')
                    tgt = (f' · Tenggat {fmt_iso(p["tenggat"])} {status_sisa(sisa_hari(p["tenggat"]))}'
                           if p.get("tenggat") else "")
                    st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(p.get("nama", ""))}{tanda}</div>'
                                f'<div class="sub">{html.escape(p.get("orang", ""))} · sejak '
                                f'{fmt_iso(p.get("tanggal", ""))}{tgt}</div></div>', unsafe_allow_html=True)

        def grafik_lokasi():
            with st.container(key="kartu_g1"):
                st.markdown("**Jenis barang per lokasi**")
                per = {}
                for b in brg:
                    per[nama_lokasi(b)] = per.get(nama_lokasi(b), 0) + 1
                st.bar_chart(pd.DataFrame({"Lokasi": list(per), "Jenis barang": list(per.values())}),
                             x="Lokasi", y="Jenis barang", horizontal=True, sort="-Jenis barang",
                             color="#2b7a57", height=300)

        def grafik_kategori():
            with st.container(key="kartu_g2"):
                st.markdown("**Jenis barang per kategori**")
                per = {}
                for b in brg:
                    per[nama_kat(b)] = per.get(nama_kat(b), 0) + 1
                st.bar_chart(pd.DataFrame({"Kategori": list(per), "Jenis barang": list(per.values())}),
                             x="Kategori", y="Jenis barang", horizontal=True, sort="-Jenis barang",
                             color="#2f5d9e", height=300)

        _grafik = [f for k, f in (("g_lokasi", grafik_lokasi), ("g_kategori", grafik_kategori)) if k not in sembunyi]
        if len(_grafik) == 2:
            _g1, _g2 = st.columns(2)
            with _g1:
                _grafik[0]()
            with _g2:
                _grafik[1]()
        elif _grafik:
            _grafik[0]()
