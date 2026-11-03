"""Ekspor daftar barang ke Excel dan PDF."""
import io

import streamlit as st

from pelacak.bantu import (
    daftar_tautan, diskon_persen, harga_asli_b, harga_b, jumlah_b, lokasi_dari, nama_kat, nama_lokasi, nama_tempat,
    perlu_beli, sub_dari, umur_teks, versi,
)
from pelacak.inti import D, fmt_iso, hari_ini, rp


# ------------------------------------------------------------ ekspor daftar
def _status_b(b: dict) -> str:
    s = []
    if b.get("hilang"):
        s.append("Hilang")
    if b.get("dibawa"):
        s.append("Sedang dibawa")
    if perlu_beli(b):
        s.append("Perlu beli")
    return ", ".join(s)


# kunci: (judul kolom, pengambil nilai, bobot lebar di PDF, angka?)
KOLOM_EKSPOR = {
    "nama": ("Nama barang", lambda b: b["nama"], 5, False),
    "jumlah": ("Jumlah", jumlah_b, 1.5, True),
    "disimpan": ("Disimpan di", nama_tempat, 4.5, False),
    "kategori": ("Kategori", nama_kat, 2.6, False),
    "pemilik": ("Pemilik", lambda b: b.get("pemilik", ""), 2.2, False),
    "merek": ("Merek", lambda b: b.get("merek", ""), 2.2, False),
    "ukuran": ("Ukuran", lambda b: b.get("ukuran", ""), 1.8, False),
    "warna": ("Warna", lambda b: b.get("warna", ""), 1.8, False),
    "seri": ("Nomor seri", lambda b: b.get("seri", ""), 2.6, False),
    "barcode": ("Barcode", lambda b: b.get("barcode", ""), 2.8, False),
    "dibeli": ("Tanggal beli", lambda b: fmt_iso(b.get("dibeli", "")), 2.2, False),
    "harga_asli": ("Harga asli", lambda b: harga_asli_b(b) or "", 2.4, True),
    "harga": ("Harga setelah diskon", lambda b: harga_b(b) or "", 2.4, True),
    "diskon": ("Diskon", lambda b: f"{diskon_persen(b)}%" if diskon_persen(b) else "", 1.6, True),
    "toko": ("Beli di", lambda b: b.get("toko", ""), 2.6, False),
    "nota": ("Nomor nota", lambda b: b.get("nota", ""), 2.4, False),
    "umur": ("Umur", lambda b: umur_teks(b), 1.8, False),
    "kedaluwarsa": ("Kedaluwarsa", lambda b: fmt_iso(b.get("kedaluwarsa", "")), 2.2, False),
    "garansi": ("Garansi sampai", lambda b: fmt_iso(b.get("garansi", "")), 2.2, False),
    "catatan": ("Catatan", lambda b: b.get("catatan", ""), 5, False),
    "tautan": ("Tautan", lambda b: " ".join(daftar_tautan(b)), 4, False),
    "tag": ("Label", lambda b: ", ".join(b.get("tag", [])), 2.6, False),
    "status": ("Status", _status_b, 2.6, False),
}


KOLOM_AWAL = ["nama", "jumlah", "disimpan", "kategori", "catatan"]


NAMA_GRUP = {"lokasi": "Lokasi", "kategori": "Kategori", "tanpa": "Tanpa pengelompokan"}


def _kelompok_b(b: dict, grup: str) -> str:
    return nama_lokasi(b) if grup == "lokasi" else nama_kat(b) if grup == "kategori" else ""


def _judul_kol(k: str, grup: str) -> str:
    return "Sub lokasi" if (k == "disimpan" and grup == "lokasi") else KOLOM_EKSPOR[k][0]


def _nilai_kol(k: str, b: dict, grup: str):
    """Kalau sudah dikelompokkan menurut lokasi, kolom 'Disimpan di' cukup menampilkan sub lokasinya."""
    if k == "disimpan" and grup == "lokasi":
        s = sub_dari(b)
        return s["nama"] if s else ""
    return KOLOM_EKSPOR[k][1](b)


def _kolom_efektif(kolom: list, grup: str) -> list:
    sisa = [k for k in kolom if not (grup == "kategori" and k == "kategori")]
    return sisa or kolom


def _urut_ekspor(daftar: list, grup: str) -> list:
    return sorted(daftar, key=lambda b: (_kelompok_b(b, grup).lower(), b["nama"].lower()))


def buat_xlsx(daftar: list, kolom: list, grup: str, cek: bool, judul: str) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.properties import PageSetupProperties

    daftar = _urut_ekspor(daftar, grup)
    kolom = _kolom_efektif(kolom, grup)
    wb = Workbook()
    ws = wb.active
    ws.title = "Daftar barang"
    kepala = ([NAMA_GRUP[grup]] if grup != "tanpa" else []) + [_judul_kol(k, grup) for k in kolom] + (["Dicek"] if cek else [])
    ws.append(kepala)
    for b in daftar:
        baris = ([_kelompok_b(b, grup)] if grup != "tanpa" else []) + [_nilai_kol(k, b, grup) for k in kolom] + ([""] if cek else [])
        ws.append(baris)
    tipis = Side(style="thin", color="D9DEE5")
    garis = Border(left=tipis, right=tipis, top=tipis, bottom=tipis)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F5C44")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = garis
    ws.row_dimensions[1].height = 26
    for i, nm in enumerate(kepala, start=1):
        angka = nm in ("Jumlah", "Harga asli", "Harga setelah diskon", "Diskon")
        lebar = max([len(str(nm))] + [len(str(ws.cell(r, i).value or "")) for r in range(2, ws.max_row + 1)])
        ws.column_dimensions[get_column_letter(i)].width = max(9, min(lebar + 3, 46 if nm != "Catatan" else 56))
        for r in range(2, ws.max_row + 1):
            c = ws.cell(r, i)
            c.border = garis
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="right" if angka else "left")
            if nm in ("Harga asli", "Harga setelah diskon") and c.value != "":
                c.number_format = '"Rp" #,##0'
            elif nm == "Dicek":
                c.alignment = Alignment(horizontal="center", vertical="top")
            if r % 2 == 1:
                c.fill = PatternFill("solid", fgColor="F6F8F7")
    ws.freeze_panes = "A2"
    if ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.print_title_rows = "1:1"
    ws.oddFooter.center.text = "Halaman &P dari &N"
    ws.oddHeader.left.text = judul

    rs = wb.create_sheet("Ringkasan")
    rs["A1"] = judul
    rs["A1"].font = Font(bold=True, size=14)
    rs["A2"] = f"Dibuat {hari_ini().strftime('%d/%m/%Y')}"
    rs["A4"], rs["B4"] = "Jenis barang", len(daftar)
    rs["A5"], rs["B5"] = "Total buah", sum(jumlah_b(b) for b in daftar)
    nilai = sum(harga_b(b) * max(jumlah_b(b), 0) for b in daftar)
    if nilai:
        rs["A6"], rs["B6"] = "Total nilai (setelah diskon)", nilai
        rs["B6"].number_format = '"Rp" #,##0'
    if grup != "tanpa":
        rs["A8"], rs["B8"], rs["C8"] = NAMA_GRUP[grup], "Jenis", "Buah"
        for c in rs[8]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F5C44")
        per = {}
        for b in daftar:
            g = _kelompok_b(b, grup)
            per.setdefault(g, [0, 0])
            per[g][0] += 1
            per[g][1] += jumlah_b(b)
        for g, (j, bh) in per.items():
            rs.append([g, j, bh])
    rs.column_dimensions["A"].width = 38
    rs.column_dimensions["B"].width = 18
    rs.column_dimensions["C"].width = 12
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def buat_pdf(daftar: list, kolom: list, grup: str, cek: bool, judul: str, sub: str) -> bytes:
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    def bersih(t) -> str:
        return escape(str(t).encode("cp1252", "replace").decode("cp1252"))

    daftar = _urut_ekspor(daftar, grup)
    kolom = _kolom_efektif(kolom, grup)
    hijau = colors.HexColor("#1F5C44")
    ukuran = landscape(A4) if len(kolom) + (1 if cek else 0) >= 6 else A4
    lebar_total = ukuran[0] - 30 * mm
    st_sel = ParagraphStyle("sel", fontName="Helvetica", fontSize=8.5, leading=10.5)
    st_angka = ParagraphStyle("angka", parent=st_sel, alignment=2)
    st_kep = ParagraphStyle("kep", fontName="Helvetica-Bold", fontSize=8.5, leading=10.5, textColor=colors.white)
    st_grup = ParagraphStyle("grup", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=hijau)

    bobot = [KOLOM_EKSPOR[k][2] for k in kolom] + ([1.4] if cek else [])
    lebar = [lebar_total * w / sum(bobot) for w in bobot]
    kepala = [Paragraph(bersih(_judul_kol(k, grup)), st_kep) for k in kolom] + ([Paragraph("Dicek", st_kep)] if cek else [])
    baris, gaya, grup_ini, nomor = [kepala], [], None, 0
    for b in daftar:
        g = _kelompok_b(b, grup)
        if grup != "tanpa" and g != grup_ini:
            grup_ini = g
            jml = sum(1 for x in daftar if _kelompok_b(x, grup) == g)
            baris.append([Paragraph(f"{bersih(g)} ({jml} jenis)", st_grup)] + [""] * (len(kepala) - 1))
            r = len(baris) - 1
            gaya += [("SPAN", (0, r), (-1, r)), ("BACKGROUND", (0, r), (-1, r), colors.HexColor("#E6F0EB"))]
            nomor = 0
        sel = []
        for k in kolom:
            v = _nilai_kol(k, b, grup)
            if k in ("harga", "harga_asli") and v != "":
                v = rp(v)
            sel.append(Paragraph(bersih(v), st_angka if KOLOM_EKSPOR[k][3] else st_sel))
        if cek:
            sel.append(Paragraph("[   ]", ParagraphStyle("c", parent=st_sel, alignment=1)))
        baris.append(sel)
        nomor += 1
        if nomor % 2 == 0:
            gaya.append(("BACKGROUND", (0, len(baris) - 1), (-1, len(baris) - 1), colors.HexColor("#F6F8F7")))

    tabel = Table(baris, colWidths=lebar, repeatRows=1)
    tabel.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), hijau), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9DEE5")),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)] + gaya))

    class Bernomor(rl_canvas.Canvas):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self._hal = []

        def showPage(self):
            self._hal.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._hal)
            for h in self._hal:
                self.__dict__.update(h)
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#6B7280"))
                self.drawRightString(ukuran[0] - 15 * mm, 9 * mm, f"Halaman {self._pageNumber} dari {total}")
                self.drawString(15 * mm, 9 * mm, bersih(judul).replace("&amp;", "&"))
                super().showPage()
            super().save()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=ukuran, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=14 * mm, bottomMargin=16 * mm, title=judul)
    total_buah = sum(jumlah_b(b) for b in daftar)
    isi = [Paragraph(bersih(judul), ParagraphStyle("j", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=hijau)),
           Paragraph(bersih(f"{sub} · {len(daftar)} jenis barang, {total_buah} buah · dibuat {hari_ini().strftime('%d/%m/%Y')}"),
                     ParagraphStyle("s", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.HexColor("#6B7280"))),
           Spacer(1, 6 * mm), tabel]
    doc.build(isi, canvasmaker=Bernomor)
    return buf.getvalue()


def halaman_ekspor():
    if not D["barang"]:
        st.info("Belum ada barang.")
        return
    with st.container(key="kartu_barang"):
        pt = {t["id"]: t["nama"] for t in sorted(D["tempat"], key=lambda t: t["nama"].lower())}
        pk = {k["id"]: k["nama"] for k in sorted(D["kategori"], key=lambda k: k["nama"].lower())}
        if st.session_state.get("ek_tempat", "semua") not in ["semua"] + list(pt):
            st.session_state.ek_tempat = "semua"
        c1, c2 = st.columns(2)
        f_tem = c1.selectbox("Tempat", ["semua"] + list(pt), key="ek_tempat",
                             format_func=lambda i: "Semua tempat" if i == "semua" else pt[i])
        f_kat = c2.multiselect("Kategori (kosong = semua)", list(pk), key="ek_kat", format_func=lambda i: pk[i])
        grup = st.selectbox("Kelompokkan menurut", list(NAMA_GRUP), key="ek_grup", format_func=NAMA_GRUP.get)
        kolom = st.multiselect("Kolom yang disertakan", list(KOLOM_EKSPOR), default=KOLOM_AWAL, key="ek_kolom",
                               format_func=lambda k: KOLOM_EKSPOR[k][0])
        cek = st.checkbox("Tambah kolom kotak centang untuk dicentang tangan setelah dicetak", key="ek_cek")
        daftar = [b for b in D["barang"]
                  if (f_tem == "semua" or (lokasi_dari(b) or {}).get("tempat") == f_tem)
                  and (not f_kat or b.get("kategori") in f_kat)]
        st.caption(f"{len(daftar)} jenis barang akan diekspor.")
        if not daftar:
            st.info("Tidak ada barang yang cocok dengan pilihan ini.")
            return
        if not kolom:
            st.warning("Pilih minimal satu kolom.")
            return
        kolom = [k for k in KOLOM_EKSPOR if k in kolom]      # urutan tetap seperti daftar kolom
        judul = "Daftar Barang" + (f" - {pt[f_tem]}" if f_tem != "semua" else "")
        sub = ", ".join(pk[i] for i in f_kat) if f_kat else "Semua kategori"
        sig = repr((f_tem, tuple(f_kat), grup, tuple(kolom), cek, versi()))
        b1, b2 = st.columns(2)
        try:
            if b1.button("Buat file Excel", key="ek_bx", type="primary", use_container_width=True):
                st.session_state.ek_xlsx = (sig, buat_xlsx(daftar, kolom, grup, cek, judul))
            if b2.button("Buat file PDF", key="ek_bp", type="primary", use_container_width=True):
                st.session_state.ek_pdf = (sig, buat_pdf(daftar, kolom, grup, cek, judul, sub))
        except ImportError as e:
            st.error(f"Pustaka belum terpasang ({e.name}). Tambahkan openpyxl dan reportlab ke requirements.txt.")
        tgl = hari_ini().isoformat()
        for kunci, label, nama_file, mime in (
                ("ek_xlsx", "Unduh Excel", f"daftar-barang-{tgl}.xlsx",
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("ek_pdf", "Unduh PDF", f"daftar-barang-{tgl}.pdf", "application/pdf")):
            v = st.session_state.get(kunci)
            if v and v[0] == sig:
                st.download_button(label, v[1], file_name=nama_file, mime=mime, key=f"dl_{kunci}",
                                   icon=":material/download:", use_container_width=True)
            elif v:
                st.caption(f"Pilihan berubah, buat ulang file {label.split()[-1]}.")
