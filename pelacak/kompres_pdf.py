"""Kompres lampiran PDF saat diunggah.

- Di bawah batas (5 MB): kompres tanpa mengubah isi (lossless): aliran isi halaman dipadatkan dan objek kembar digabung.
- Di atas batas: gambar di dalam PDF diperkecil dan dikompres ulang (kualitas turun sedikit), bertahap sampai muat.
Kalau PDF tidak bisa diproses (dikunci sandi, rusak, atau pypdf tidak terpasang), berkas dikembalikan apa adanya.
"""
import io

BATAS_BYTE = 5 * 1024 * 1024
# (sisi terpanjang gambar dalam piksel, mutu JPEG), dicoba berurutan sampai ukuran muat
TAHAP_PERKECIL = [(1800, 65), (1400, 50), (1000, 40)]
GAMBAR_MIN_BYTE = 50 * 1024      # gambar yang lebih kecil dari ini dibiarkan


def _mb(n: int) -> str:
    return f"{n / 1024 / 1024:.1f}".replace(".", ",") + " MB"


def _tulis(w) -> bytes:
    for p in w.pages:
        p.compress_content_streams()
    w.compress_identical_objects(remove_identicals=True, remove_orphans=True)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _lossless(data: bytes) -> bytes:
    from pypdf import PdfReader, PdfWriter
    return _tulis(PdfWriter(clone_from=PdfReader(io.BytesIO(data))))


def _perkecil_gambar(data: bytes, sisi_maks: int, mutu: int) -> bytes:
    from PIL import Image
    from pypdf import PdfReader, PdfWriter
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(data)))
    sudah = set()
    for p in w.pages:
        for img in p.images:
            try:
                kunci = getattr(getattr(img, "indirect_reference", None), "idnum", None)
                if kunci is not None and kunci in sudah:
                    continue
                if len(img.data) < GAMBAR_MIN_BYTE:
                    continue
                pil = img.image
                if pil is None or pil.mode in ("1", "RGBA", "LA", "PA") or "transparency" in pil.info:
                    continue                        # bitmap hitam putih dan gambar transparan dibiarkan
                if pil.mode not in ("RGB", "L"):
                    pil = pil.convert("RGB")
                if max(pil.size) > sisi_maks:
                    pil = pil.copy()
                    pil.thumbnail((sisi_maks, sisi_maks), Image.LANCZOS)
                img.replace(pil, quality=mutu)
                if kunci is not None:
                    sudah.add(kunci)
            except Exception:
                continue
    return _tulis(w)


def _sah(asli: bytes, hasil: bytes) -> bool:
    """Hasil harus bisa dibuka dan jumlah halamannya sama."""
    from pypdf import PdfReader
    try:
        return len(PdfReader(io.BytesIO(hasil)).pages) == len(PdfReader(io.BytesIO(asli)).pages)
    except Exception:
        return False


def kompres_lampiran(data: bytes, batas: int = BATAS_BYTE):
    """Kembalikan (isi_pdf, keterangan). Keterangan kosong kalau tidak ada yang diubah."""
    asli = len(data)
    try:
        import PIL  # noqa: F401
        import pypdf  # noqa: F401
    except ImportError:
        return data, ""
    try:
        if asli < batas:
            hasil = _lossless(data)
            if len(hasil) < asli and _sah(data, hasil):
                hemat_berarti = len(hasil) <= asli * 0.95
                return hasil, (f"dikompres tanpa mengubah isi, {_mb(asli)} jadi {_mb(len(hasil))}"
                               if hemat_berarti else "")
            return data, ""
        terbaik = data
        for sisi, mutu in TAHAP_PERKECIL:
            hasil = _perkecil_gambar(data, sisi, mutu)
            if len(hasil) < len(terbaik) and _sah(data, hasil):
                terbaik = hasil
            if len(terbaik) <= batas:
                break
        if len(terbaik) < asli:
            return terbaik, f"gambar diperkecil, {_mb(asli)} jadi {_mb(len(terbaik))}"
        return data, ""
    except Exception:
        return data, ""
