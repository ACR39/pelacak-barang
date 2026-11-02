"""Pelacak Barang Pribadi (Streamlit).

Mencatat di mana barang pribadi disimpan (lokasi dan sub lokasi) dan memudahkan
pencarian. Data disimpan sebagai satu file JSON di repositori GitHub (disarankan
repositori privat terpisah), foto disimpan di folder foto/ pada repositori yang sama.
Kalau pengaturan GitHub tidak ada, aplikasi memakai file lokal untuk uji coba.

Kode aplikasi ada di paket pelacak/ (satu modul per bagian).
"""
import streamlit as st

st.set_page_config(page_title="Pelacak Barang", page_icon="📦", layout="wide")

from pelacak.rangka import jalankan  # noqa: E402

jalankan()
