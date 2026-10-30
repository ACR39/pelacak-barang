"""Membuat hash kata sandi untuk Streamlit Secrets.

Jalankan:  python buat_hash.py
Lalu tempel hasilnya ke password_hash pengguna di Secrets.
"""
import getpass
import hashlib
import os

sandi = getpass.getpass("Kata sandi: ")
garam = os.urandom(16)
iterasi = 200_000
h = hashlib.pbkdf2_hmac("sha256", sandi.encode("utf-8"), garam, iterasi)
print(f"pbkdf2${iterasi}${garam.hex()}${h.hex()}")
