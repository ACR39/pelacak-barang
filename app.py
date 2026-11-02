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
import re
import time
import uuid
from difflib import SequenceMatcher
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
.pengguna.sb{background:transparent;margin:.9rem 0 .5rem;border-radius:0;border-top:1px solid rgba(255,255,255,.08);padding:.9rem .2rem 0}
[data-testid="stSidebar"] .pengguna.sb .nm{color:#fff;font-size:.88rem}
[data-testid="stSidebar"] .pengguna.sb .pr{color:#94a3b8}
[data-testid="stSidebar"]{background:#0b1220}
[data-testid="stSidebarHeader"]{position:absolute;top:.5rem;right:.5rem;width:auto;height:auto;padding:0;margin:0;z-index:5}
[data-testid="stSidebarUserContent"]{padding-top:1.1rem}
[data-testid="stSidebar"] *{color:#e5e7eb}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *{color:#94a3b8}
.brand{display:flex;align-items:center;gap:.7rem;padding:.3rem .2rem 1.1rem;border-bottom:1px solid rgba(255,255,255,.08);margin-bottom:.4rem}
.brand .b1{font-weight:700;font-size:1.05rem;color:#fff;line-height:1.2}
.brand .b2{font-size:.76rem;color:#94a3b8;margin-top:.1rem}
.sp{height:1.2rem}
[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"] > style:only-child){display:none}
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
.bidang{font-weight:700;font-size:.78rem;text-transform:uppercase;letter-spacing:.07em;color:#256b4a;background:#e8f3ec;border-left:3px solid #256b4a;padding:.35rem .7rem;border-radius:4px;margin:.4rem 0 -.3rem}
.st-ok{color:#166534;font-weight:600}.st-warn{color:#8a5a00;font-weight:600}.st-bad{color:#b42318;font-weight:600}
.lencana{display:inline-block;font-size:.66rem;font-weight:700;border-radius:999px;padding:.05rem .5rem;margin-left:.4rem;vertical-align:middle}
.lc-m{background:#fff4d6;color:#8a5a00}.lc-r{background:#fde8e6;color:#b42318}.lc-b{background:#e6eefb;color:#2f5d9e}.lc-h{background:#e3f3ea;color:#166534}
.akt{border:1px solid #e3e7ee;border-radius:10px;padding:.55rem .8rem;margin:.45rem 0;background:#fff}
.akt .ah{font-weight:650;line-height:1.5}.akt .ar{font-size:.86rem;color:#3d4655;margin-top:.15rem;line-height:1.5;word-break:break-word}.akt .am{font-size:.76rem;color:#6b7280;margin-top:.25rem}
.pohon details{border:1px solid #e3e7ee;border-radius:10px;margin:.4rem 0;background:#fff}
.pohon details.pl{border:0;border-left:2px solid #cfe3d6;border-radius:0;margin:.3rem 0 .3rem .3rem;background:transparent}
.pohon summary{cursor:pointer;padding:.55rem .7rem;font-weight:650;list-style:none;display:flex;align-items:center;gap:.5rem}
.pohon summary::-webkit-details-marker{display:none}
.pohon summary::before{content:"▸";color:#256b4a;flex:0 0 auto;transition:transform .15s}
.pohon details[open] > summary::before{transform:rotate(90deg)}
.pohon details.pl > summary{font-weight:600;padding:.4rem .5rem}
.pohon .pc{margin-left:auto;font-weight:600;font-size:.72rem;background:#e8f3ec;color:#256b4a;border-radius:999px;padding:.05rem .55rem;white-space:nowrap}
.pohon .pb{padding:0 .7rem .5rem 1.1rem}
.pohon .pi{display:flex;align-items:center;gap:.4rem;padding:.3rem 0;border-bottom:1px dashed #e8ebf0;font-size:.92rem;flex-wrap:wrap}
.pohon .pn{font-weight:550;word-break:break-word}
.pohon .pj{margin-left:auto;font-weight:700}
.pohon .pk{color:#6b7280;font-size:.82rem;padding:.3rem 0}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"],.statcard,.kepala,[data-testid="stForm"]{color:#111827 !important}
.kepala .desk,.sc-ket,.sc-lab,.eyebrow{color:#475569 !important}
.perhatian{padding:.45rem 0;border-bottom:1px solid #eef0f4;font-size:.92rem;color:#1f2937}
.perhatian:last-child{border-bottom:0}
.itm a,.perhatian a,.akt a{color:#2f5d9e;text-decoration:underline;word-break:break-all}
@media (max-width:768px){
  .block-container{padding:2.7rem 1rem 4rem}
  [data-testid="stHeader"]{height:2.4rem;min-height:0}
  [data-testid="stSidebarCollapsedControl"]{top:.35rem;left:.5rem}
  .kepala{padding:.9rem 1rem}
  .judul-hal{font-size:1.35rem}
}
/* Di HP tabel tidak ditumpuk ke bawah, tapi dilebarkan dan bisa digeser ke samping */
@media (max-width:640px){
  .st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_g_rencana,[class*="st-key-kartu_tgl"]{overflow-x:auto;-webkit-overflow-scrolling:touch}
  [data-testid="stHorizontalBlock"]:has(.brg),[data-testid="stHorizontalBlock"]:has(.thead-s){flex-wrap:nowrap !important;min-width:780px}
  [data-testid="stHorizontalBlock"]:has(.brg) > [data-testid="stColumn"],[data-testid="stHorizontalBlock"]:has(.thead-s) > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;min-width:0 !important}
  [data-testid="stHorizontalBlock"]:has(.brg) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{min-width:0 !important;width:auto !important}
  .st-key-kartu_tabel .garis,.st-key-kartu_barang .garis,.st-key-kartu_g_rencana .garis,[class*="st-key-kartu_tgl"] .garis{min-width:780px}
}
/* Tampilan kartu barang */
[class*="st-key-item_"]{background:#fff;border:1px solid #e3e7ee;border-radius:14px;padding:.8rem 1rem;
  box-shadow:0 1px 3px rgba(16,24,40,.06);margin-bottom:-.35rem;color:#111827 !important;gap:.45rem !important}
[class*="st-key-item_"] [data-testid="stMarkdown"],[class*="st-key-item_"] [data-testid="stMarkdownContainer"]{margin-bottom:0 !important}
@media (max-width:640px){
  [class*="st-key-item_"]{padding:.7rem .85rem}
  .itm{gap:.7rem}
  .itm .ic{flex-basis:44px;width:44px;height:44px;font-size:1.1rem}
  .itm .jd{font-size:.98rem;line-height:1.25}
  .itm .mt,.itm .cat{font-size:.78rem;line-height:1.35}
  .itm .qt{min-width:40px}
  .itm .qt b{font-size:1.45rem}
}
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
.itm .qt span{display:block;font-size:.72rem;color:#6b7280;white-space:nowrap}
.itm .qt .st-ok,.itm .qt .st-warn,.itm .qt .st-bad{font-size:.78rem}
.lencana{white-space:nowrap}
.itm.pj{flex-wrap:wrap}
.itm.pj .isi{flex:1 1 180px}
.itm.pj .qt{text-align:right}
@media (max-width:640px){
  .itm.pj .qt{flex:1 1 100%;text-align:left;padding-left:calc(44px + .7rem);display:flex;flex-wrap:wrap;gap:.1rem .5rem;align-items:baseline}
}
[class*="st-key-kedit_"] button,[class*="st-key-khapus_"] button,[class*="st-key-kpakai_"] button,[class*="st-key-ksalin_"] button{min-height:2rem;padding:.1rem .6rem;background:#fff !important;font-weight:600}
[class*="st-key-ksalin_"] button{border:1px solid #6b7280 !important;color:#374151 !important}
[class*="st-key-kpakai_"] button{border:1px solid #2f5d9e !important;color:#2f5d9e !important}
[class*="st-key-kedit_"] button{border:1px solid #256b4a !important;color:#256b4a !important}
[class*="st-key-khapus_"] button{border:1px solid #b42318 !important;color:#b42318 !important}
.st-key-baris_cari [data-testid="stHorizontalBlock"],[class*="st-key-item_"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;align-items:center}
.st-key-baris_cari [data-testid="stColumn"]:first-child{min-width:0 !important;flex:1 1 auto !important;width:auto !important}
.st-key-baris_cari [data-testid="stColumn"]:last-child,[class*="st-key-item_"] [data-testid="stColumn"]{min-width:0 !important;flex:0 0 auto !important;width:auto !important}
.st-key-baris_cari button,[class*="st-key-item_"] button{white-space:nowrap}
.st-key-baris_cari button p,[class*="st-key-item_"] button p{white-space:nowrap}
[class*="st-key-item_b_"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;gap:.5rem !important}
[class*="st-key-item_b_"] [data-testid="stColumn"]{flex:1 1 130px !important;width:auto !important;min-width:130px !important}
</style>
""", unsafe_allow_html=True)

CSS_GELAP = """
<style>
:root{color-scheme:dark}
[data-testid="stApp"],[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:#0f1722 !important}
[data-testid="stApp"]{color:#e5e7eb}
[data-testid="stHeader"]{background:transparent !important}
[data-testid="stSidebarCollapsedControl"] *,[data-testid="stExpandSidebarButton"] *{color:#e5e7eb !important}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,[data-testid="stMain"] [data-testid="stMarkdownContainer"] li,
[data-testid="stMain"] h1,[data-testid="stMain"] h2,[data-testid="stMain"] h3,[data-testid="stMain"] h4,
[data-testid="stMain"] [data-testid="stWidgetLabel"] p,[data-testid="stMain"] [data-testid="stCaptionContainer"],
[data-testid="stMain"] [data-testid="stCaptionContainer"] p,[data-testid="stMain"] [data-testid="stExpander"] summary p,
[data-testid="stMain"] [data-testid="stRadio"] label p,[data-testid="stMain"] [data-testid="stCheckbox"] label p,
[data-testid="stMain"] [data-testid="stToggle"] label p,[data-testid="stMain"] [data-testid="stTab"] p{color:#e5e7eb !important}
[data-testid="stMain"] [data-testid="stCaptionContainer"],[data-testid="stMain"] [data-testid="stCaptionContainer"] p{color:#94a3b8 !important}
.eyebrow{color:#5ccf9c !important}
.judul-hal{color:#f1f5f9 !important}
.kepala{background:#172131 !important;border-color:#2a3547 !important;border-left-color:#34a874 !important;box-shadow:none !important;color:#e5e7eb !important}
.kepala .desk,.sc-ket,.sc-lab{color:#94a3b8 !important}
.st-key-kartu_filter,.st-key-kartu_tabel,.st-key-kartu_barang,.st-key-kartu_perhatian,[class*="st-key-kartu_g"],[class*="st-key-kartu_tgl"],
.statcard,[data-testid="stForm"],[data-testid="stExpander"],[data-testid="stMetric"],[class*="st-key-item_"]{
  background:#172131 !important;border-color:#2a3547 !important;box-shadow:none !important;color:#e5e7eb !important}
[data-testid="stExpander"] details{border-color:#2a3547 !important}
.sc-judul,.sc-val,.itm .jd,.itm .qt b,.perhatian,.brg{color:#f1f5f9 !important}
.sc-val.m,.itm .qt b.merah{color:#f87171 !important}
.sc-val.g{color:#4ade80 !important}
.sc-stat{border-left-color:#2a3547 !important}
.sub,.itm .mt,.itm .cat,.itm .qt span{color:#9aa7b8 !important}
.perhatian{border-bottom-color:#2a3547 !important}
.itm a,.perhatian a,.akt a{color:#93c5fd !important}
.garis{border-top-color:#2a3547 !important}
.itm .ic{background:#1f3a2f !important;color:#5ccf9c !important}
.tag{background:#1f3a2f;color:#5ccf9c}
.tag-m{background:#3b3010;color:#fcd34d}
.bidang{background:#1b2d27 !important;color:#5ccf9c !important;border-left-color:#34a874 !important}
.st-ok{color:#4ade80 !important}.st-warn{color:#fbbf24 !important}.st-bad{color:#f87171 !important}
.lc-m{background:#3b3010 !important;color:#fcd34d !important}
.lc-r{background:#431a17 !important;color:#fca5a5 !important}
.lc-b{background:#14284a !important;color:#93c5fd !important}
.lc-h{background:#12301f !important;color:#86efac !important}
.akt{background:#172131 !important;border-color:#2a3547 !important}
.akt .ah{color:#f1f5f9 !important}.akt .ar{color:#cbd5e1 !important}.akt .am{color:#94a3b8 !important}
.pohon details{background:#172131 !important;border-color:#2a3547 !important}
.pohon details.pl{background:transparent !important;border-left-color:#2f5d4a !important}
.pohon summary{color:#f1f5f9 !important}
.pohon .pc{background:#1f3a2f !important;color:#5ccf9c !important}
.pohon .pi{border-bottom-color:#2a3547 !important}
.pohon .pn,.pohon .pj{color:#e5e7eb !important}
.pohon .pk{color:#94a3b8 !important}
[class*="st-key-kedit_"] button,[class*="st-key-khapus_"] button,[class*="st-key-kpakai_"] button,[class*="st-key-ksalin_"] button{background:#1e293b !important}
[class*="st-key-ksalin_"] button{border-color:#94a3b8 !important;color:#cbd5e1 !important}
[class*="st-key-kedit_"] button{border-color:#34a874 !important;color:#5ccf9c !important}
[class*="st-key-khapus_"] button{border-color:#f87171 !important;color:#f87171 !important}
[class*="st-key-kpakai_"] button{border-color:#60a5fa !important;color:#93c5fd !important}
[data-testid="stMain"] button[kind="secondary"],[data-testid="stMain"] button[kind="secondaryFormSubmit"],[data-testid="stMain"] [data-testid="stDownloadButton"] button{
  background:#1e293b;border-color:#334155;color:#e5e7eb}
[data-testid="stMain"] button[kind="secondary"] p,[data-testid="stMain"] button[kind="secondaryFormSubmit"] p,[data-testid="stMain"] [data-testid="stDownloadButton"] button p{color:inherit !important}
[data-testid="stMain"] button[kind="primary"] p,[data-testid="stMain"] button[kind="primaryFormSubmit"] p{color:#fff !important}
[data-testid="stSelectbox"] [role="group"],[data-testid="stMultiSelect"] [role="group"],[data-testid="stDateInput"] [role="group"],
[data-testid="stDateInputField"],[data-testid="stNumberInputContainer"],[data-testid="stTextInputRootElement"],[data-testid="stTextAreaRootElement"],
[data-testid="stFileUploaderDropzone"],[data-testid="stCameraInput"]{background:#0f1722 !important;border-color:#334155 !important}
[data-testid="stSelectbox"] [role="group"] *,[data-testid="stMultiSelect"] [role="group"] *,[data-testid="stDateInput"] [role="group"] *,
[data-testid="stNumberInputContainer"] *,[data-testid="stTextInputRootElement"] input,[data-testid="stTextAreaRootElement"] textarea,
[data-testid="stTextInputField"],[data-testid="stFileUploaderDropzone"] *{color:#e5e7eb !important;-webkit-text-fill-color:#e5e7eb !important}
[data-testid="stSelectbox"] [role="group"] svg,[data-testid="stMultiSelect"] [role="group"] svg,[data-testid="stDateInput"] svg,
[data-testid="stTextInputIcon"] svg,[data-testid="stFileUploaderDropzone"] svg{fill:#94a3b8 !important;color:#94a3b8 !important}
input::placeholder,textarea::placeholder{color:#94a3b8 !important;-webkit-text-fill-color:#94a3b8 !important;opacity:1 !important}
[data-testid="stNumberInputContainer"] button{background:#1e293b !important}
/* daftar pilihan (dropdown) tampil di luar halaman utama, lewat portal */
[data-testid="stSelectboxVirtualDropdown"],[data-testid="stSelectboxVirtualDropdown"] [role="listbox"],
[data-testid="portal"] [role="listbox"],[data-testid="portal"] ul{background:#172131 !important}
[role="listbox"] [role="option"],[role="listbox"] [role="option"] *,[data-testid="portal"] li,[data-testid="portal"] li *{color:#e5e7eb !important;-webkit-text-fill-color:#e5e7eb !important}
[role="listbox"] [role="option"]:hover,[role="listbox"] [role="option"][aria-selected="true"],[role="listbox"] [role="option"][data-focused="true"]{background:#24324a !important}
[data-testid="stMultiSelect"] [data-testid="stTag"],[data-testid="stMultiSelect"] [role="row"] > div{background:#24324a !important}
[data-testid="stButtonGroup"] button[aria-checked="false"]{background:#0f1722 !important;color:#e5e7eb !important;border-color:#334155 !important}
[data-testid="stButtonGroup"] button p{color:inherit !important}
[data-testid="stAlertContainer"]{background:rgba(148,163,184,.14) !important;color:#e5e7eb !important}
[data-testid="stAlertContainer"] p,[data-testid="stAlertContainer"] li{color:#e5e7eb !important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{border-bottom-color:#2a3547}
[data-testid="stArrowVegaLiteChart"],[data-testid="stVegaLiteChart"]{filter:invert(1) hue-rotate(180deg)}
[data-testid="stImage"] img{border-radius:8px}
[data-testid="stProgress"] p{color:#e5e7eb !important}
</style>
"""

TANPA = "Tanpa lokasi"
TANPA_KAT = "Tanpa kategori"
FILE_LOKAL = os.environ.get("BARANG_DATA_FILE", "data_lokal.json")
FOTO_LOKAL = os.environ.get("BARANG_FOTO_DIR", "foto_lokal")
TGL_MIN, TGL_MAX = date(2000, 1, 1), date(2100, 12, 31)
MAKS_RIWAYAT = 1000
MAKS_AKTIVITAS = 1500
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
        "rencana": [],    # [{"id","nama","jumlah","harga","prioritas","catatan","dibuat","dibeli"}]
        "paket": [],      # [{"id","nama","isi":[{"id","nama","barang","jumlah","siap"}]}]  daftar bawaan
        "aktivitas": [],  # [{"id","waktu","oleh","jenis","barang","nama","rincian"}]  riwayat aktivitas
        "pengaturan": {},  # {"kartu":[bagian yang disembunyikan],"beranda":[...]}  bawaan bersama semua perangkat
        "pindah_massal": [],  # [{"id","waktu","oleh","tujuan":{lokasi,sublokasi},"tujuan_nama","item":[{id,nama,dari:{lokasi,sublokasi,dalam}}],"dibatalkan"}]
        "sampah": [],     # [{"id","barang":{...data barang...},"dihapus":"YYYY-MM-DD HH:MM","oleh"}]  tempat sampah
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
               "sublokasi": "Sub lokasi", "catatan": "Catatan", "harga": "Harga beli", "dibeli": "Tanggal beli", "kedaluwarsa": "Kedaluwarsa",
               "garansi": "Garansi", "habis": "Perlu beli", "minimum": "Stok minimum", "dalam": "Di dalam",
               "foto": "Foto", "dipakai": "Dipakai", "merek": "Merek", "ukuran": "Ukuran", "warna": "Warna",
               "seri": "Nomor seri", "pemilik": "Pemilik", "galeri": "Foto tambahan", "barcode": "Barcode",
               "cek_tiap": "Cek berkala", "cek_terakhir": "Terakhir dicek",
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
    if kunci == "harga":
        return "Rp " + f"{int(v):,}".replace(",", ".")
    if kunci == "galeri":
        return f"{len(v)} foto" if v else "kosong"
    if kunci == "tag":
        return ", ".join(v) if v else "kosong"
    if kunci == "cek_tiap":
        return teks_cek(v)
    if kunci in ("kedaluwarsa", "garansi", "dipakai", "dibeli", "dibawa", "hilang", "cek_terakhir"):
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
COOKIE_TEMA = "barang_tema"


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


def js_cookie(nilai: str, detik: int, nama: str = COOKIE):
    """Pasang (atau hapus, detik=0) cookie sesi di peramban lewat komponen tak terlihat."""
    import streamlit.components.v1 as components
    components.html(
        f"""<script>
        const d = window.parent.document;
        const aman = window.parent.location.protocol === 'https:' ? '; Secure' : '';
        d.cookie = "{nama}={nilai}; Max-Age={detik}; Path=/; SameSite=Lax" + aman;
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

st.session_state["_snap"] = ambil_snap()

# Mode gelap: pilihan terakhir diingat lewat cookie peramban.
if "gelap" not in st.session_state:
    try:
        st.session_state.gelap = st.context.cookies.get(COOKIE_TEMA, "") == "gelap"
    except Exception:
        st.session_state.gelap = False
if st.session_state.gelap:
    st.markdown(CSS_GELAP, unsafe_allow_html=True)

# Dibuka dari pindaian label QR: ?lokasi=<id>&sub=<id> langsung membuka daftar isi tempat itu.
_qp_brg = st.query_params.get("barang")
if _qp_brg:
    _brg_qr = next((x for x in D["barang"] if x["id"] == _qp_brg), None)
    if _brg_qr:
        st.session_state.halaman = "Cari barang"
        for _k in ("cari_tempat", "cari_lok", "cari_sub", "cari_kat"):
            st.session_state[_k] = "semua"
        st.session_state.cari_q = _brg_qr["nama"].lower()
        st.session_state.cari_fav = False
        st.session_state.cari_tag = []
    st.query_params.clear()
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
    for k in ("br_mode", "br_hapus", "sp_hapus", "sp_kosong", "pj_hapus", "pj_mode", "rc_mode", "rc_hapus", "bl_mode", "bm_buang", "db_mode", "hl_mode", "hl_ketemu", "pk_hapus", "sc_n", "op_rencana", "serupa_ok",
              "edit_tempat", "hapus_tempat", "edit_kategori", "hapus_kategori",
              "edit_lokasi", "hapus_lokasi", "edit_sub", "hapus_sub", "edit_pemilik", "hapus_pemilik"):
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
        st.session_state.pop("serupa_ok", None)
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


def minimum_b(b: dict) -> int:
    try:
        return max(int(b.get("minimum", 0) or 0), 0)
    except Exception:
        return 0


def stok_menipis(b: dict) -> bool:
    """Stok minimum diisi (lebih dari 0) dan jumlah sudah turun sampai batas itu."""
    m = minimum_b(b)
    return m > 0 and jumlah_b(b) <= m


def perlu_beli(b: dict) -> bool:
    return bool(b.get("habis")) or jumlah_b(b) == 0 or stok_menipis(b)


def pinjam_aktif(id_barang: str):
    """Catatan peminjaman yang masih berjalan untuk barang milik sendiri (dipinjamkan ke orang lain)."""
    return next((p for p in D["pinjam"] if p.get("barang") == id_barang and p.get("arah") == "keluar"
                 and not p.get("kembali")), None)


def lencana(b: dict) -> str:
    h = '<span class="lencana lc-m">★ Favorit</span>' if b.get("favorit") else ""
    if perlu_beli(b):
        menipis = stok_menipis(b) and not b.get("habis") and jumlah_b(b) > 0
        h += f'<span class="lencana lc-r">{"Stok menipis" if menipis else "Perlu beli"}</span>'
    p = pinjam_aktif(b["id"])
    if p:
        h += f'<span class="lencana lc-m">Dipinjam {html.escape(p.get("orang", ""))}</span>'
    if b.get("kondisi") in KONDISI:
        h += f'<span class="lencana {"lc-r" if b["kondisi"] == "rusak" else "lc-m"}">{KONDISI[b["kondisi"]]}</span>'
    if b.get("hilang"):
        h += '<span class="lencana lc-r">Hilang</span>'
    if b.get("dibawa"):
        h += '<span class="lencana lc-b">Sedang dibawa</span>'
    n_isi = len(isi_dari(b["id"]))
    if n_isi:
        h += f'<span class="lencana lc-b">Berisi {n_isi}</span>'
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


ATRIBUT = (("merek", "Merek"), ("ukuran", "Ukuran"), ("warna", "Warna"), ("seri", "Nomor seri"))


MASA_SAMPAH = 30   # hari barang disimpan di tempat sampah sebelum hilang permanen


def isi_dari(id_barang: str) -> list:
    """Barang yang disimpan langsung di dalam barang ini (satu tingkat)."""
    return [x for x in D["barang"] if x.get("dalam") == id_barang]


def keturunan(id_barang: str) -> set:
    """Semua barang di dalam barang ini, termasuk isi dari isinya."""
    hasil, antre = set(), [id_barang]
    while antre:
        sekarang_id = antre.pop(0)
        for x in D["barang"]:
            if x.get("dalam") == sekarang_id and x["id"] not in hasil:
                hasil.add(x["id"])
                antre.append(x["id"])
    return hasil


def induk_dari(b: dict):
    return next((x for x in D["barang"] if x["id"] == b.get("dalam")), None) if b.get("dalam") else None


def ikut_induk(x: dict, induk: dict) -> bool:
    """Samakan lokasi barang x dengan barang induknya. True kalau lokasinya berubah."""
    dari = nama_tempat(x)
    x["lokasi"] = induk.get("lokasi", "")
    if induk.get("sublokasi"):
        x["sublokasi"] = induk["sublokasi"]
    else:
        x.pop("sublokasi", None)
    ke = nama_tempat(x)
    if dari == ke:
        return False
    x["diubah"] = hari_ini().isoformat()
    catat(x["id"], x["nama"], dari, ke)
    return True


def sinkron_isi(id_induk: str, lihat=None):
    """Isi barang selalu ikut lokasi induknya, juga isi dari isinya."""
    lihat = lihat if lihat is not None else set()
    if id_induk in lihat:
        return
    lihat.add(id_induk)
    induk = next((x for x in D["barang"] if x["id"] == id_induk), None)
    if not induk:
        return
    for x in isi_dari(id_induk):
        ikut_induk(x, induk)
        sinkron_isi(x["id"], lihat)


def pesan_hapus_barang(b: dict) -> str:
    n = len(isi_dari(b["id"]))
    return (f"Pindahkan {b['nama']} ke tempat sampah?"
            + (f" {n} barang di dalamnya akan dilepas dari barang ini." if n else ""))


def buang_barang(b: dict):
    """Pindahkan barang ke tempat sampah. Barang di dalamnya dilepas dari barang ini."""
    for x in isi_dari(b["id"]):
        x.pop("dalam", None)
    D["barang"] = [x for x in D["barang"] if x["id"] != b["id"]]
    D["sampah"].append({"id": uuid.uuid4().hex[:8], "barang": dict(b),
                        "dihapus": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama()})


def sisa_sampah(s: dict) -> int:
    """Berapa hari lagi sebelum catatan sampah dihapus permanen."""
    try:
        t = datetime.strptime(s.get("dihapus", ""), "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
        return MASA_SAMPAH - (sekarang() - t).days
    except Exception:
        return MASA_SAMPAH


def teks_cari(b: dict) -> str:
    """Teks yang dicocokkan saat mencari barang, termasuk nama barang induk dan isinya."""
    induk = induk_dari(b)
    return " ".join([b["nama"], b.get("catatan", ""), b.get("tautan", ""), nama_tempat(b), nama_kat(b), b.get("pemilik", ""), b.get("barcode", ""),
                     induk["nama"] if induk else ""] + [b.get(k, "") for k, _ in ATRIBUT]
                    + list(b.get("tag", [])) + [x["nama"] for x in isi_dari(b["id"])]).lower()


def _mirip(t: str, w: str) -> bool:
    """Dua kata dianggap mirip kalau hanya beda satu dua huruf (salah ketik)."""
    if abs(len(t) - len(w)) > 2:
        return False
    if SequenceMatcher(None, t, w).ratio() >= 0.78:
        return True
    return len(w) > len(t) and SequenceMatcher(None, t, w[:len(t)]).ratio() >= 0.85


def skor_cocok(q: str, teks: str) -> int:
    """2 = semua kata pencarian ada di teks, 1 = cocok dengan toleransi salah ketik, 0 = tidak cocok."""
    skor, kata = 2, None
    for t in q.split():
        if t in teks:
            continue
        if len(t) < 4:                      # kata pendek harus persis, supaya tidak ngawur
            return 0
        if kata is None:
            kata = set(re.findall(r"\w+", teks))
        if any(_mirip(t, w) for w in kata):
            skor = 1
        else:
            return 0
    return skor


def saring_barang(daftar: list, q: str):
    """Barang yang cocok dengan pencarian. Yang cocok persis lebih dulu, lalu yang mirip.
    Mengembalikan (hasil, jumlah_yang_hanya_mirip)."""
    if not q:
        return list(daftar), 0
    tepat, mirip = [], []
    for b in daftar:
        sk = skor_cocok(q, teks_cari(b))
        if sk == 2:
            tepat.append(b)
        elif sk == 1:
            mirip.append(b)
    return tepat + mirip, len(mirip)


def daftar_pemilik() -> list:
    return sorted({b["pemilik"] for b in D["barang"] if b.get("pemilik")}, key=str.lower)


def daftar_tag() -> list:
    return sorted({t for b in D["barang"] for t in b.get("tag", [])}, key=str.lower)


RE_URL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


def _url_aman(u: str) -> str:
    """Buang tanda baca di ujung tautan dan pastikan skemanya http(s)."""
    u = u.rstrip(".,;:!?)]}")
    return u if u.lower().startswith(("http://", "https://")) else ""


def html_tautan(teks: str) -> str:
    """Escape teks, lalu ubah alamat web di dalamnya jadi tautan yang bisa diklik."""
    keluar, pos = [], 0
    for m in RE_URL.finditer(teks or ""):
        u = _url_aman(m.group(0))
        if not u:
            continue
        akhir = m.start() + len(u)
        keluar.append(html.escape(teks[pos:m.start()]))
        keluar.append(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">{html.escape(u)}</a>')
        pos = akhir
    keluar.append(html.escape((teks or "")[pos:]))
    return "".join(keluar)


def daftar_tautan(b: dict) -> list:
    """Alamat web dari field tautan barang (satu per baris), tanpa duplikat."""
    hasil = []
    for m in RE_URL.finditer(b.get("tautan", "") or ""):
        u = _url_aman(m.group(0))
        if u and u not in hasil:
            hasil.append(u)
    return hasil


def label_tautan(u: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", u, flags=re.IGNORECASE).split("/")[0][:40] or u


def html_daftar_tautan(b: dict) -> str:
    return " · ".join(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener noreferrer">'
                      f'{html.escape(label_tautan(u))}</a>' for u in daftar_tautan(b))


def _norm_nama(s: str) -> str:
    return " ".join((s or "").lower().split())


def cari_serupa(nama: str, kecuali: str = "") -> list:
    """Barang lain yang namanya sama atau sangat mirip dengan `nama` (untuk peringatan sebelum menambah)."""
    n = _norm_nama(nama)
    if not n:
        return []
    hasil = []
    for b in D["barang"]:
        if b["id"] == kecuali:
            continue
        w = _norm_nama(b["nama"])
        if w == n or (len(n) >= 4 and len(w) >= 4 and (n in w or w in n)) or _mirip(n, w):
            hasil.append(b)
    return hasil


def peringatan_serupa(nama: str, kecuali: str = "") -> bool:
    """True kalau penyimpanan sebaiknya ditunda: ada barang serupa dan pengguna belum mengonfirmasi.
    Konfirmasinya: menekan tombol simpan lagi dengan nama yang sama."""
    serupa = cari_serupa(nama, kecuali)
    if not serupa or st.session_state.get("serupa_ok") == _norm_nama(nama):
        return False
    st.session_state.serupa_ok = _norm_nama(nama)
    daftar = ", ".join(f"{b['nama']} ({nama_tempat(b)})" for b in serupa[:3]) + (
        f" dan {len(serupa) - 3} lainnya" if len(serupa) > 3 else "")
    st.warning(f"Sudah ada barang yang mirip: {daftar}. Kalau memang barang yang berbeda, "
               "tekan tombol simpan sekali lagi untuk tetap menambahkan.")
    return True


MAKS_GALERI = 6


KONDISI = {"rusak": "Rusak", "servis": "Sedang diservis"}
MAKS_LAMPIRAN, MAKS_LAMPIRAN_MB = 5, 5


def semua_berkas(b: dict) -> list:
    """Semua path berkas barang: foto, foto tambahan, dan lampiran dokumen."""
    return semua_foto(b) + [x["path"] for x in b.get("lampiran", []) if x.get("path")]


def semua_foto(b: dict) -> list:
    """Semua path foto sebuah barang: foto utama, lalu foto tambahan."""
    return ([b["foto"]] if b.get("foto") else []) + list(b.get("galeri", []))


_n_lamp = [0]


def tampil_lampiran(b: dict):
    """Tombol unduh untuk dokumen terlampir (nota, manual, kartu garansi)."""
    for x in b.get("lampiran", []):
        dat = ambil_foto(x.get("path", ""))
        if not dat:
            continue
        _n_lamp[0] += 1
        st.download_button(f"📄 {x.get('nama', 'dokumen')}", dat, file_name=x.get("nama", "dokumen.pdf"),
                           mime="application/pdf", key=f"dl_lamp_{_n_lamp[0]}", use_container_width=True)


def tampil_galeri(b: dict):
    """Lipatan 'Lihat N foto' kalau barang punya lebih dari satu foto."""
    fs = semua_foto(b)
    if len(fs) < 2:
        return
    with st.expander(f"Lihat {len(fs)} foto"):
        kol = st.columns(2)
        for i, p in enumerate(fs):
            dat = ambil_foto(p)
            if dat:
                kol[i % 2].image(dat, use_container_width=True)


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


def html_nama_foto(x: dict) -> str:
    """Nama lokasi/sub lokasi, dengan foto bulat kecil di kirinya kalau ada."""
    nama = html.escape(x["nama"])
    dat = ambil_foto(x["foto"]) if x.get("foto") else None
    if dat:
        try:
            return (f'<div class="itm"><div class="ic"><img src="{_uri_bulat(x["foto"], dat)}" alt=""></div>'
                    f'<div class="isi"><div class="jd" style="font-weight:600">{nama}</div></div></div>')
        except Exception:
            pass
    return f'<div style="padding:.3rem 0">{nama}</div>'


SEKSI_KARTU = [("lokasi", "Lokasi"), ("kategori", "Kategori"), ("harga", "Harga beli"),
               ("jumlah", "Jumlah (angka besar di kanan)"), ("tanggal", "Tanggal (dibeli, kedaluwarsa, garansi, dipakai, diinventarisasi)"),
               ("pemilik", "Pemilik"), ("atribut", "Merek, ukuran, warna, nomor seri"),
               ("hubungan", "Di dalam atau berisi barang lain"), ("catatan", "Catatan"), ("tautan", "Tautan"), ("label", "Label")]
COOKIE_KARTU = "barang_kartu"


def muat_kartu_sembunyi() -> set:
    """Bagian kartu barang yang disembunyikan. Pilihan diingat di perangkat ini lewat cookie."""
    if "kartu_sembunyi" not in st.session_state:
        try:
            ck = st.context.cookies.get(COOKIE_KARTU)
        except Exception:
            ck = None
        if not isinstance(ck, str):            # perangkat ini belum punya pilihan sendiri: pakai bawaan bersama
            ck = ",".join(D.get("pengaturan", {}).get("kartu", []))
        sah = {k for k, _ in SEKSI_KARTU}
        st.session_state.kartu_sembunyi = [k for k in ck.split(",") if k in sah]
    return set(st.session_state.kartu_sembunyi)


def ubah_kartu():
    st.session_state.kartu_sembunyi = [k for k, _ in SEKSI_KARTU if not st.session_state.get(f"ks_{k}", True)]
    st.session_state.kartu_ubah = True


def atur_kartu(sembunyi: list):
    for k, _ in SEKSI_KARTU:
        st.session_state[f"ks_{k}"] = k not in sembunyi
    ubah_kartu()


def kartu_barang_html(b: dict, foto: bool = True) -> str:
    """Satu kartu barang: ikon/foto bulat, nama, keterangan, jumlah besar di kanan."""
    sb = muat_kartu_sembunyi()
    ic = html.escape((b["nama"].strip()[:1] or "?").upper())
    if foto and b.get("foto"):
        dat = ambil_foto(b["foto"])
        if dat:
            try:
                ic = f'<img src="{_uri_bulat(b["foto"], dat)}" alt="">'
            except Exception:
                pass
    meta = [nama_tempat(b)] if "lokasi" not in sb else []
    if b.get("kategori") and "kategori" not in sb:
        meta.append(nama_kat(b))
    if harga_b(b) and "harga" not in sb:
        meta.append("Rp " + f"{harga_b(b):,}".replace(",", "."))
    ekstra = []
    if b.get("dibeli") and "tanggal" not in sb:
        ekstra.append(f"Dibeli: {fmt_iso(b['dibeli'])}")
    for lab, kunci in (("Kedaluwarsa", "kedaluwarsa"), ("Garansi", "garansi")):
        s = sisa_hari(b.get(kunci))
        if s is not None and "tanggal" not in sb:
            ekstra.append(f"{lab}: {status_sisa(s)}")
    if b.get("dipakai") and "tanggal" not in sb:
        ekstra.append(f"Dipakai: {fmt_iso(b['dipakai'])}")
    if b.get("pemilik") and "pemilik" not in sb:
        ekstra.append(f"Milik: {html.escape(b['pemilik'])}")
    if b.get("dibawa"):
        ekstra.append(f"Dibawa sejak {fmt_iso(b['dibawa'])}"
                      + (f" ke {html.escape(b['dibawa_ke'])}" if b.get("dibawa_ke") else ""))
    if b.get("hilang"):
        ekstra.append(f"Hilang sejak {fmt_iso(b['hilang'])}"
                      + (f", terakhir terlihat di {html.escape(b['hilang_di'])}" if b.get("hilang_di") else ""))
    atr = [f"{lab}: {html.escape(b[k])}" for k, lab in ATRIBUT if b.get(k)]
    if atr and "atribut" not in sb:
        ekstra.append(" · ".join(atr))
    induk = induk_dari(b)
    if induk and "hubungan" not in sb:
        ekstra.append(f"Di dalam: {html.escape(induk['nama'])}")
    isi = isi_dari(b["id"])
    if isi and "hubungan" not in sb:
        ekstra.append("Berisi: " + html.escape(", ".join(x["nama"] for x in isi[:5]))
                      + (f" +{len(isi) - 5} lagi" if len(isi) > 5 else ""))
    cat = ""
    if b.get("catatan") and "catatan" not in sb:
        cat += f'<div class="cat">{html_tautan(b["catatan"])}</div>'
    if daftar_tautan(b) and "tautan" not in sb:
        cat += f'<div class="cat">Tautan: {html_daftar_tautan(b)}</div>'
    if b.get("tag") and "label" not in sb:
        cat += '<div class="cat">' + "".join(f'<span class="tag">{html.escape(t)}</span>' for t in b["tag"]) + '</div>'
    if b.get("opname") and "tanggal" not in sb:
        ekstra.append(f"Diinventarisasi: {fmt_iso(b['opname'])}")
    if ekstra:
        cat += f'<div class="cat">{" · ".join(ekstra)}</div>'
    merah = " merah" if perlu_beli(b) else ""
    mt = f'<div class="mt">{html.escape(" • ".join(meta))}</div>' if meta else ""
    qt = (f'<div class="qt"><b class="{merah.strip()}">{jumlah_b(b)}</b><span>buah</span></div>'
          if "jumlah" not in sb else "")
    return (f'<div class="itm"><div class="ic">{ic}</div><div class="isi">'
            f'<div class="jd">{html.escape(b["nama"])}{lencana(b)}</div>{mt}{cat}</div>{qt}</div>')


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

UTAMA = ["Cari barang", "Scan barcode", "Jelajah lokasi", "Kelola barang", "Pindah massal", "Inventaris ulang", "Riwayat",
         "Tempat sampah"]
PANTAU = ["Pinjam-meminjam", "Dibawa, hilang, rusak", "Belanja", "Daftar bawaan", "Jarang dipakai",
          "Jatuh tempo", "Catatan perawatan", "Statistik"]
MASTER = ["Tempat dan lokasi", "Kategori dan label", "Label QR", "Ukuran data", "Cadangan dan pulihkan"]
PENGATURAN = ["Tampilan", "Ekspor dan impor"] + (MASTER if adalah_admin() else [])
HALAMAN = ["Beranda"] + UTAMA + PANTAU + PENGATURAN
if st.session_state.get("halaman") not in HALAMAN:
    st.session_state.halaman = "Beranda"
halaman = st.session_state.halaman
IKON = {"Beranda": "home", "Cari barang": "search", "Kelola barang": "inventory_2", "Scan barcode": "barcode_scanner",
        "Jelajah lokasi": "account_tree", "Pindah massal": "swap_horiz", "Inventaris ulang": "fact_check",
        "Riwayat": "history", "Tempat sampah": "delete",
        "Pinjam-meminjam": "handshake", "Dibawa, hilang, rusak": "backpack", "Belanja": "shopping_cart",
        "Daftar bawaan": "luggage", "Jarang dipakai": "schedule", "Jatuh tempo": "event_busy",
        "Catatan perawatan": "build", "Statistik": "bar_chart",
        "Tampilan": "tune", "Ekspor dan impor": "import_export",
        "Tempat dan lokasi": "home_work", "Kategori dan label": "sell", "Label QR": "qr_code_2",
        "Ukuran data": "database", "Cadangan dan pulihkan": "backup"}
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
    with st.expander("Pengaturan", icon=":material/settings:", expanded=halaman in PENGATURAN):
        for h in PENGATURAN:
            tombol_nav(h)
    st.markdown('<div class="sp"></div>', unsafe_allow_html=True)
    st.toggle("Mode gelap", key="gelap", on_change=atur, args=("tema_ubah", True))
    if st.session_state.pop("tema_ubah", False):
        js_cookie("gelap" if st.session_state.gelap else "terang", 31536000, COOKIE_TEMA)
    if st.button("Muat ulang", key="nav_muat", use_container_width=True, icon=":material/refresh:",
                 help="Ambil data terbaru dari penyimpanan"):
        muat_ke_sesi()
        st.rerun()
    if cfg_github():
        st.caption(f"Data: {cfg_github()['repo']}")
    _us = st.session_state.get("user")
    if _us:
        st.markdown(f'<div class="pengguna sb"><div class="av">{html.escape(_us["nama"][:1].upper())}</div><div>'
                    f'<div class="nm">{html.escape(_us["nama"])}</div>'
                    f'<div class="pr">{html.escape(_us["peran"])}</div></div></div>', unsafe_allow_html=True)
        st.button("Keluar", key="nav_keluar", use_container_width=True,
                  icon=":material/logout:", on_click=keluar)

DESKRIPSI = {
    "Riwayat": "Perpindahan barang dan aktivitas (tambah, ubah, buang, pulihkan) yang tercatat otomatis.",
    "Jatuh tempo": "Pantau kedaluwarsa, masa garansi, dan barang yang perlu dicek rutin.",
    "Statistik": "Barang yang sering pindah, jumlah per lokasi, aktivitas bulanan, per pemilik, kelengkapan data, dan nilai barang.",
    "Tampilan": "Pilih kartu di Beranda dan keterangan di kartu barang. Bisa disimpan untuk semua perangkat.",
    "Tempat dan lokasi": "Tiga tingkat penyimpanan: tempat, lokasi, dan sub lokasi.",
    "Kategori dan label": "Kelola kategori, pemilik, dan label barang: ubah nama atau gabungkan yang ganda.",
    "Cadangan dan pulihkan": "Unduh cadangan data, muat dari berkas, atau pulihkan ke versi sebelumnya.",
    "Beranda": "Ringkasan barang, hal yang perlu perhatian, dan grafik.",
    "Cari barang": "Cari barang berdasarkan nama, lokasi, kategori, atau catatan.",
    "Kelola barang": "Tambah, ubah, atau hapus barang beserta lokasi, foto, dan tanggalnya.",
    "Pindah massal": "Pindahkan banyak barang sekaligus ke lokasi lain, misalnya saat membereskan kotak.",
    "Inventaris ulang": "Cocokkan isi satu lokasi dengan keadaan sebenarnya: centang yang ada, koreksi jumlah, tandai yang hilang.",
    "Dibawa, hilang, rusak": "Barang yang sedang dibawa keluar, belum ketemu, rusak, atau sedang diservis.",
    "Catatan perawatan": "Riwayat servis, perbaikan, dan perawatan tiap barang beserta biayanya.",
    "Ukuran data": "Pantau besar data dan foto di penyimpanan, dan bersihkan foto yang tidak terpakai.",
    "Jelajah lokasi": "Telusuri isi tiap tempat, lokasi, dan sub lokasi, lengkap dengan jumlah barangnya.",
    "Tempat sampah": "Barang yang dibuang disimpan 30 hari di sini, bisa dipulihkan sebelum hilang permanen.",
    "Pinjam-meminjam": "Catat barang yang kamu pinjamkan atau yang kamu pinjam, lengkap dengan tenggatnya.",
    "Belanja": "Stok menipis atau habis (otomatis) dan rencana barang baru yang ingin dibeli, dalam satu daftar belanja.",
    "Daftar bawaan": "Daftar barang untuk dibawa (liburan, pindahan, dll.) yang bisa dicentang satu per satu.",
    "Jarang dipakai": "Barang yang sudah lama tidak dipakai, untuk bahan membereskan atau melepas barang.",
    "Scan barcode": "Foto barcode di kemasan untuk menemukan barang, atau menambahkannya dengan nama yang terisi otomatis.",
    "Ekspor dan impor": "Unduh daftar barang sebagai Excel atau PDF untuk dicetak, atau tambah banyak barang sekaligus dari file Excel atau CSV.",
    "Label QR": "Cetak label QR untuk ditempel di lemari atau kotak. Dipindai, langsung muncul isinya.",
}
_grup = ("PENGATURAN" if halaman in PENGATURAN else "RINGKASAN" if halaman == "Beranda"
         else "PANTAU" if halaman in PANTAU else "BARANG")
st.markdown(f'<div class="kepala"><div><div class="eyebrow">{_grup}</div>'
            f'<div class="judul-hal">{html.escape(halaman)}</div>'
            f'<div class="desk">{html.escape(DESKRIPSI.get(halaman, ""))}</div></div></div>',
            unsafe_allow_html=True)

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


_tenggat = pesan_tenggat()
if _tenggat and halaman in ("Beranda", "Pinjam-meminjam"):
    st.warning("🔔 **Tenggat pengembalian hari ini**\n\n" + "\n".join(f"- {t}" for t in _tenggat))
if _tenggat and not st.session_state.get("toast_tenggat"):
    st.session_state.toast_tenggat = True
    st.toast(f"{len(_tenggat)} peminjaman jatuh tempo hari ini", icon="🔔")

# ------------------------------------------------------------ pengingat berkala (pembantu)
CEK_OPSI = [0, 30, 60, 90, 180, 365]


def teks_cek(n) -> str:
    return {0: "Tidak ada", 30: "Tiap 1 bulan", 60: "Tiap 2 bulan", 90: "Tiap 3 bulan",
            180: "Tiap 6 bulan", 365: "Tiap 1 tahun"}.get(int(n or 0), f"Tiap {int(n or 0)} hari")


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


if halaman == "Beranda":
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
            f_pem = "semua"
            if daftar_pemilik():
                ops_pem = ["semua", "__tanpa__"] + daftar_pemilik()
                if st.session_state.get("cari_pem", "semua") not in ops_pem:
                    st.session_state.cari_pem = "semua"
                f_pem = st.selectbox("Pemilik", ops_pem, key="cari_pem",
                                     format_func=lambda x: "Semua pemilik" if x == "semua"
                                     else "Tanpa pemilik" if x == "__tanpa__" else x)
            f_tag = []
            if daftar_tag():
                st.session_state.cari_tag = [t for t in st.session_state.get("cari_tag", []) if t in daftar_tag()]
                f_tag = st.multiselect("Label", daftar_tag(), key="cari_tag", placeholder="Semua label")
            tv1, tv2, tv3 = st.columns([2, 2, 2], vertical_alignment="center")
            mode_tampil = tv1.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                                key="tampilan", label_visibility="collapsed") or "Kartu"
            tampil_foto = tv2.toggle("Tampilkan foto", value=True, key="cari_foto")
            f_fav = tv3.toggle("Hanya favorit", key="cari_fav")
        hasil = D["barang"]
        if f_tem != "semua":
            hasil = [b for b in hasil if (lokasi_dari(b) or {}).get("tempat") == f_tem]
        if f_lok != "semua":
            hasil = [b for b in hasil if b.get("lokasi") == f_lok]
        if f_sub != "semua":
            hasil = [b for b in hasil if (sub_dari(b) or {}).get("id") == f_sub]
        if f_kat != "semua":
            hasil = [b for b in hasil if b.get("kategori") == f_kat]
        if f_pem == "__tanpa__":
            hasil = [b for b in hasil if not b.get("pemilik")]
        elif f_pem != "semua":
            hasil = [b for b in hasil if b.get("pemilik") == f_pem]
        if f_fav:
            hasil = [b for b in hasil if b.get("favorit")]
        if f_tag:
            hasil = [b for b in hasil if all(t in b.get("tag", []) for t in f_tag)]
        hasil, n_mirip = saring_barang(hasil, q)
        _l = next((l for l in D["lokasi"] if l["id"] == f_lok), None) if f_lok != "semua" else None
        _s = next((s for s in D["sublokasi"] if s["id"] == f_sub), None) if f_sub != "semua" else None
        _fotos = []
        for _o, _cap in ((_l, nama_lok(_l) if _l else ""), (_s, _s["nama"] if _s else "")):
            _dat = ambil_foto(_o["foto"]) if _o and _o.get("foto") else None
            if _dat:
                _fotos.append((_dat, _cap))
        if _fotos:
            for _kol, (_dat, _cap) in zip(st.columns(len(_fotos)), _fotos):
                _kol.image(_dat, caption=_cap, use_container_width=True)
        st.caption(f"{len(hasil)} dari {len(D['barang'])} barang"
                   + (f" · termasuk {n_mirip} hasil yang mirip dengan ketikanmu" if n_mirip else ""))
        if not hasil:
            st.info("Tidak ada barang yang cocok.")
        elif mode_tampil == "Kartu":
            for judul, anggota in kelompok(hasil):
                judul_grup(judul, len(anggota))
                for b in sorted(anggota, key=lambda x: (not x.get("favorit"), x["nama"].lower())):
                    with st.container(key=f"item_c_{b['id']}"):
                        st.markdown(kartu_barang_html(b, tampil_foto), unsafe_allow_html=True)
                        tampil_galeri(b)
                        tampil_lampiran(b)
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
def _dengan_isi(b: dict) -> list:
    return [b] + [x for x in D["barang"] if x["id"] in keturunan(b["id"])]


def tandai_dibawa(b: dict, ke: str = ""):
    """Tandai barang (dan isinya) sedang dibawa keluar. Lokasi aslinya tidak diubah."""
    for x in _dengan_isi(b):
        x["dibawa"] = hari_ini().isoformat()
        if ke:
            x["dibawa_ke"] = ke
        else:
            x.pop("dibawa_ke", None)
        x["diubah"] = hari_ini().isoformat()


def kembalikan_dibawa(b: dict):
    for x in _dengan_isi(b):
        x.pop("dibawa", None)
        x.pop("dibawa_ke", None)
        x["diubah"] = hari_ini().isoformat()


def tandai_hilang(b: dict, di: str = "", tgl=None):
    b["hilang"] = (tgl or hari_ini()).isoformat()
    if di:
        b["hilang_di"] = di
    else:
        b.pop("hilang_di", None)
    b["diubah"] = hari_ini().isoformat()


def tandai_ketemu(b: dict, lok_baru: str = ""):
    """Barang ketemu. Kalau lok_baru diisi (dan barang tidak ada di dalam barang lain), lokasinya dipindah."""
    dari = nama_tempat(b)
    b.pop("hilang", None)
    b.pop("hilang_di", None)
    if lok_baru and lok_baru != b.get("lokasi") and not induk_dari(b):
        b["lokasi"] = lok_baru
        b.pop("sublokasi", None)
    b["diubah"] = hari_ini().isoformat()
    if nama_tempat(b) != dari:
        catat(b["id"], b["nama"], dari, nama_tempat(b))
        sinkron_isi(b["id"])


def form_cepat():
    """Formulir mini: nama, jumlah, lokasi. Lokasi diingat untuk barang berikutnya."""
    st.markdown("#### Tambah cepat")
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di Pengaturan > Lokasi sebelum menambah barang.")
        st.button("Kembali", key="cp_kembali_kosong", on_click=atur, args=("br_mode", None))
        return
    st.caption("Isi nama dan jumlah saja. Lokasi diingat untuk barang berikutnya. "
               "Detail lain bisa dilengkapi nanti lewat Edit.")
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    if st.session_state.get("cepat_lok") not in pl:
        st.session_state.cepat_lok = next(iter(pl))
    lok = st.selectbox("Lokasi", list(pl), key="cepat_lok", format_func=lambda i: pl[i])
    subs = {x["id"]: x["nama"] for x in D["sublokasi"] if x["lokasi"] == lok}
    ops_s = [""] + list(subs)
    if st.session_state.get("cepat_sub", "") not in ops_s:
        st.session_state.cepat_sub = ""
    sub = st.selectbox("Sub lokasi (boleh kosong)", ops_s, key="cepat_sub",
                       format_func=lambda i: "Tanpa sub lokasi" if not i else subs[i])
    with st.form(f"form_cepat_{versi()}"):
        nama = st.text_input("Nama barang", placeholder="Contoh: Charger")
        jumlah = st.number_input("Jumlah", min_value=0, value=1, step=1)
        kat = ""
        if D["kategori"]:
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            ops_k = [""] + list(pk)
            kat = st.selectbox("Kategori (boleh kosong)", ops_k,
                               format_func=lambda i: TANPA_KAT if not i else pk[i])
        c1, c2 = st.columns(2)
        lagi = c1.form_submit_button("Simpan, tambah lagi", type="primary")
        selesai = c2.form_submit_button("Simpan, selesai")
    st.button("Kembali", key="cp_kembali", on_click=atur, args=("br_mode", None))
    if lagi or selesai:
        nama = nama.strip()
        if not nama:
            st.error("Nama barang wajib diisi.")
            return
        if peringatan_serupa(nama):
            return
        b = {"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": lok, "jumlah": int(jumlah),
             "diubah": hari_ini().isoformat()}
        if sub:
            b["sublokasi"] = sub
        if kat:
            b["kategori"] = kat
        catat(b["id"], nama, "", nama_tempat(b))
        D["barang"].append(b)
        selesai_simpan(f"{nama} ditambahkan.", br_mode=None if selesai else "cepat")


def salin_barang(b: dict) -> dict:
    """Buat salinan barang (tanpa foto, nomor seri, dan tanda pakai), lalu catat sebagai barang baru."""
    s = {k: v for k, v in b.items() if k not in ("id", "foto", "galeri", "dipakai", "habis", "seri", "dibawa", "dibawa_ke", "hilang", "hilang_di", "barcode", "cek_terakhir", "lampiran", "perawatan", "kondisi", "kondisi_sejak", "kondisi_ket")}
    s["id"] = uuid.uuid4().hex[:8]
    s["nama"] = f"{b['nama']} (salinan)"
    s["diubah"] = hari_ini().isoformat()
    catat(s["id"], s["nama"], "", nama_tempat(s))
    D["barang"].append(s)
    return s


def kunci_pilih(i: str) -> str:
    return f"pl_{i}_{versi()}"


def set_pilihan(ids: list, nilai: bool):
    for i in ids:
        st.session_state[kunci_pilih(i)] = nilai


AKSI_MASSAL = ["Ubah kategori", "Ubah pemilik", "Tambah label", "Tandai favorit", "Batal favorit", "Tandai sedang dibawa",
              "Tandai perlu beli", "Batal tandai perlu beli", "Buang ke tempat sampah"]


def aksi_massal(urut: list):
    """Panel aksi untuk barang yang dicentang di daftar Kartu."""
    ids = [b["id"] for b in urut]
    dipilih = [b for b in urut if st.session_state.get(kunci_pilih(b["id"]))]
    n = len(dipilih)
    c1, c2 = st.columns(2)
    c1.button(f"Pilih semua ({len(ids)})", key="bm_semua", use_container_width=True,
              on_click=set_pilihan, args=(ids, True))
    c2.button("Kosongkan", key="bm_kosong", use_container_width=True,
              on_click=set_pilihan, args=(ids, False))
    st.caption(f"{n} barang dipilih")
    if not n:
        return
    aksi = st.selectbox("Aksi untuk barang terpilih", AKSI_MASSAL, key="bm_aksi")
    if aksi == "Ubah kategori":
        if not D["kategori"]:
            st.info("Belum ada kategori. Tambahkan dulu di Pengaturan > Kategori.")
            return
        pk = {k["id"]: k["nama"] for k in D["kategori"]}
        ops = [""] + list(pk)
        kat = st.selectbox("Kategori baru", ops, key=f"bm_kat_{versi()}",
                           format_func=lambda i: TANPA_KAT if not i else pk[i])
        if st.button(f"Ubah kategori {n} barang", type="primary", key="bm_ubah"):
            for b in dipilih:
                if kat:
                    b["kategori"] = kat
                else:
                    b.pop("kategori", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"Kategori {n} barang diubah.")
    elif aksi == "Ubah pemilik":
        ops = [""] + daftar_pemilik() + ["__baru__"]
        pem = st.selectbox("Pemilik baru", ops, key=f"bm_pem_{versi()}",
                           format_func=lambda x: "Tanpa pemilik" if not x else "➕ Pemilik baru..." if x == "__baru__" else x)
        if pem == "__baru__":
            pem = st.text_input("Nama pemilik baru", key=f"bm_pem_baru_{versi()}", max_chars=40).strip()
        if st.button(f"Ubah pemilik {n} barang", type="primary", key="bm_pemilik"):
            for b in dipilih:
                if pem:
                    b["pemilik"] = pem
                else:
                    b.pop("pemilik", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"Pemilik {n} barang diubah.")
    elif aksi == "Tambah label":
        tag_baru = st.multiselect("Label yang ditambahkan", daftar_tag(), key=f"bm_tag_{versi()}", accept_new_options=True)
        if st.button(f"Tambah label ke {n} barang", type="primary", key="bm_tag_go"):
            tags = list(dict.fromkeys(t.strip()[:30] for t in tag_baru if t.strip()))
            if not tags:
                st.error("Pilih atau ketik minimal satu label.")
            else:
                for b in dipilih:
                    b["tag"] = list(dict.fromkeys(list(b.get("tag", [])) + tags))[:8]
                    b["diubah"] = hari_ini().isoformat()
                selesai_simpan(f"Label ditambahkan ke {n} barang.")
    elif aksi in ("Tandai favorit", "Batal favorit"):
        if st.button(f"{aksi} ({n} barang)", type="primary", key="bm_fav"):
            for b in dipilih:
                if aksi == "Tandai favorit":
                    b["favorit"] = True
                else:
                    b.pop("favorit", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"{n} barang diubah.")
    elif aksi == "Tandai sedang dibawa":
        ke = st.text_input("Dibawa ke mana atau untuk apa (boleh kosong)", key=f"bm_ke_{versi()}", max_chars=60).strip()
        if st.button(f"Tandai {n} barang sedang dibawa", type="primary", key="bm_bawa"):
            for b in dipilih:
                tandai_dibawa(b, ke)
            selesai_simpan(f"{n} barang ditandai sedang dibawa.")
    elif aksi in ("Tandai perlu beli", "Batal tandai perlu beli"):
        tandai = aksi == "Tandai perlu beli"
        if st.button(f"{aksi} ({n} barang)", type="primary", key="bm_habis"):
            for b in dipilih:
                if tandai:
                    b["habis"] = True
                else:
                    b.pop("habis", None)
                b["diubah"] = hari_ini().isoformat()
            selesai_simpan(f"{n} barang ditandai." if tandai else f"Tanda perlu beli {n} barang dibatalkan.")
    else:
        if not st.session_state.get("bm_buang"):
            st.button(f"Buang {n} barang", type="primary", key="bm_buang_btn",
                      on_click=atur, args=("bm_buang", True))
        else:
            lepas = sum(len([x for x in isi_dari(b["id"]) if x["id"] not in {p["id"] for p in dipilih}])
                        for b in dipilih)
            st.warning(f"Pindahkan {n} barang ke tempat sampah?"
                       + (f" {lepas} barang di dalamnya akan dilepas dari induknya." if lepas else "")
                       + " Masih bisa dipulihkan selama 30 hari.")
            y, t, _ = st.columns([1.3, 1, 1])
            if y.button("Ya, buang", type="primary", key="bm_buang_ya"):
                for b in dipilih:
                    buang_barang(b)
                selesai_simpan(f"{n} barang dipindahkan ke tempat sampah.", bm_buang=False)
            t.button("Batal", key="bm_buang_batal", on_click=atur, args=("bm_buang", False))


def halaman_barang():
    by_id = {b["id"]: b for b in D["barang"]}
    mode = st.session_state.get("br_mode")          # None (daftar), "baru", atau id barang
    if mode not in (None, "baru", "cepat") and mode not in by_id:
        mode = None
    with st.container(key="kartu_barang"):
        if mode == "cepat":
            form_cepat()
            return
        if not mode:
            with st.container(key="baris_cari"):
                kc, kt = st.columns([5, 2], vertical_alignment="center")
                cari = " ".join(kc.text_input("Pencarian", key="br_cari", icon=":material/search:",
                                              placeholder="Cari nama, merek, lokasi, atau kategori...",
                                              label_visibility="collapsed").lower().split())
                kt.button("Tambah", type="primary", key="br_tambah", icon=":material/add:",
                          use_container_width=True, on_click=atur, args=("br_mode", "baru"))
            tm1, tm2 = st.columns([3, 2], vertical_alignment="center")
            mode_tampil = tm1.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                                key="tampilan", label_visibility="collapsed") or "Kartu"
            tm2.button("Tambah cepat", key="br_cepat", icon=":material/bolt:", use_container_width=True,
                       on_click=atur, args=("br_mode", "cepat"),
                       help="Form mini: cukup nama, jumlah, dan lokasi")
            if not D["barang"]:
                st.write("Belum ada barang.")
            if mode_tampil == "Kartu":
                urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
                if cari:
                    urut, _mirip_n = saring_barang(urut, cari)
                    if not urut:
                        st.info("Tidak ada barang yang cocok dengan pencarian.")
                pilih_on = bool(urut) and st.toggle("Pilih banyak", key="br_pilih",
                                                    help="Centang beberapa barang lalu ubah kategori, tandai, atau buang sekaligus")
                if pilih_on:
                    aksi_massal(urut)
                for b in urut:
                    with st.container(key=f"item_k_{b['id']}"):
                        st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                        tampil_galeri(b)
                        tampil_lampiran(b)
                        if pilih_on:
                            st.checkbox("Pilih barang ini", key=kunci_pilih(b["id"]))
                            continue
                        e1, e2, e3, e4 = st.columns([1, 1, 1.5, 1.5])
                        e1.button("Edit", key=f"kedit_{b['id']}", on_click=atur, args=("br_mode", b["id"]),
                                  use_container_width=True)
                        e2.button("Hapus", key=f"khapus_{b['id']}", on_click=atur, args=("br_hapus", b["id"]),
                                  use_container_width=True)
                        if e3.button("Dipakai", key=f"kpakai_{b['id']}", use_container_width=True,
                                     help="Catat bahwa barang ini dipakai hari ini"):
                            b["dipakai"] = hari_ini().isoformat()
                            selesai_simpan("Dicatat dipakai hari ini.")
                        if e4.button("Salin", key=f"ksalin_{b['id']}", use_container_width=True,
                                     help="Buat salinan barang ini, lalu ubah detailnya"):
                            baru_s = salin_barang(b)
                            selesai_simpan("Salinan dibuat. Ubah nama dan detailnya di formulir.", br_mode=baru_s["id"])
                        if st.session_state.get("br_hapus") == b["id"]:
                            st.warning(pesan_hapus_barang(b))
                            y, n, _ = st.columns([1, 1, 2])
                            if y.button("Ya, buang", type="primary", key=f"brya_{b['id']}"):
                                buang_barang(b)
                                selesai_simpan("Dipindahkan ke tempat sampah.", br_hapus=None)
                            n.button("Batal", key=f"brbatal_{b['id']}", on_click=atur, args=("br_hapus", None))
                return
            lebar = [0.8, 1.2, 4, 3.4, 2.2, 1, 1.7]
            kep = st.columns(lebar)
            for kol, judul in zip(kep, ["No.", "Foto", "Barang", "Lokasi", "Kategori", "Jml", "#"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            if cari:
                urut, _mirip_n = saring_barang(urut, cari)
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
                    st.warning(pesan_hapus_barang(b))
                    y, n, _ = st.columns([1, 1, 4])
                    if y.button("Ya, buang", type="primary", key=f"brya_{b['id']}"):
                        buang_barang(b)
                        selesai_simpan("Dipindahkan ke tempat sampah.", br_hapus=None)
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
        kandidat = [x for x in sorted(D["barang"], key=lambda x: x["nama"].lower())
                    if x["id"] != b.get("id") and x["id"] not in keturunan(b.get("id", "-"))]
        induk, peta_i = "", {x["id"]: x for x in kandidat}
        if kandidat:
            ops_i = [""] + list(peta_i)
            induk = st.selectbox("Disimpan di dalam barang lain (boleh kosong)", ops_i,
                                 index=idx(ops_i, b.get("dalam", "")), key=f"br_dalam_{mode}_{versi()}",
                                 format_func=lambda i: "Tidak, simpan langsung di lokasi" if not i
                                 else f'{peta_i[i]["nama"]} ({nama_tempat(peta_i[i])})',
                                 help="Contoh: plester disimpan di dalam Tas P3K. Lokasinya otomatis mengikuti barang itu.")
        if induk:
            p_induk = peta_i[induk]
            lok, sub = p_induk.get("lokasi", ""), p_induk.get("sublokasi", "")
            st.caption(f"Lokasi mengikuti {p_induk['nama']}: {nama_tempat(p_induk)}")
        else:
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
            ids_l = list(pl)
            k_lok = f"br_lok_{mode}_{versi()}_{f_tem or 'semua'}"
            lok = st.selectbox("Lokasi", ids_l, index=idx(ids_l, b.get("lokasi", "")), key=k_lok,
                               format_func=lambda i: pl[i])
            sub = ""
            psub_f = {x["id"]: x["nama"] for x in D["sublokasi"] if x["lokasi"] == lok}
            if psub_f:
                ops_s = [""] + list(psub_f)
                awal_s = b.get("sublokasi", "") if (sub_dari(b) and b.get("lokasi") == lok) else ""
                sub = st.selectbox("Sub lokasi (boleh kosong)", ops_s, index=idx(ops_s, awal_s),
                                   key=f"br_sub_{mode}_{versi()}_{lok}",
                                   format_func=lambda i: "Tanpa sub lokasi" if not i else psub_f[i])
        ops_pem = [""] + daftar_pemilik() + ["__baru__"]
        pem_sel = st.selectbox("Pemilik (boleh kosong)", ops_pem, index=idx(ops_pem, b.get("pemilik", "")),
                               key=f"br_pem_{mode}_{versi()}",
                               format_func=lambda x: "Tanpa pemilik" if not x else "➕ Pemilik baru..." if x == "__baru__" else x,
                               help="Untuk barang bersama, misalnya milik teman kos atau keluarga.")
        pemilik = (st.text_input("Nama pemilik baru", key=f"br_pem_baru_{mode}_{versi()}", max_chars=40).strip()
                   if pem_sel == "__baru__" else pem_sel)
        with st.form(f"form_br_{mode}_{versi()}"):
            f1, f2 = st.columns([4, 1])
            nama = f1.text_input("Nama barang", value=b.get("nama", ""), placeholder="Contoh: Parfum")
            jumlah = f2.number_input("Jumlah", min_value=0, value=jumlah_b(b) if b else 1, step=1)
            kat = ""
            if D["kategori"]:
                pk = {k["id"]: k["nama"] for k in D["kategori"]}
                ops_k = [""] + list(pk)
                kat = st.selectbox("Kategori (boleh kosong)", ops_k, index=idx(ops_k, b.get("kategori", "")),
                                   format_func=lambda i: TANPA_KAT if not i else pk[i])
            h1, h2 = st.columns(2)
            harga = h1.number_input("Harga beli per buah (Rp)", min_value=0, value=harga_b(b), step=1000,
                                    help="Isi 0 kalau belum tahu. Dipakai di Statistik (tab Nilai barang).")
            tb = h2.date_input("Tanggal pembelian (boleh kosong)", value=iso_ke_date(b.get("dibeli")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY",
                               help="Berguna untuk menghitung masa garansi dan umur barang.")
            h3, h4 = st.columns(2)
            kd = h3.date_input("Kedaluwarsa (boleh kosong)", value=iso_ke_date(b.get("kedaluwarsa")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            gr = h4.date_input("Garansi sampai (boleh kosong)", value=iso_ke_date(b.get("garansi")),
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
            habis = st.checkbox("Habis / perlu beli lagi", value=bool(b.get("habis")))
            fav = st.checkbox("Favorit", value=bool(b.get("favorit")), help="Barang favorit tampil di Beranda dan di urutan atas pencarian.")
            tag_pil = st.multiselect("Label (boleh kosong)", sorted(set(daftar_tag()) | set(b.get("tag", [])), key=str.lower),
                                     default=b.get("tag", []), accept_new_options=True,
                                     help="Ketik untuk membuat label baru, misalnya musim hujan atau naik gunung.")
            minimum = st.number_input("Stok minimum", min_value=0, value=minimum_b(b), step=1,
                                      help="Kalau jumlah sudah sampai angka ini atau kurang, barang otomatis "
                                           "masuk daftar Perlu beli. Isi 0 kalau tidak dipantau.")
            with st.expander("Detail tambahan (merek, ukuran, warna, nomor seri, barcode, cek berkala)",
                             expanded=any(b.get(k) for k, _ in ATRIBUT) or bool(b.get("barcode") or b.get("cek_tiap"))):
                a1, a2 = st.columns(2)
                a3, a4 = st.columns(2)
                nilai_atr = {}
                for kol, (kunci, label) in zip((a1, a2, a3, a4), ATRIBUT):
                    nilai_atr[kunci] = kol.text_input(label, value=b.get(kunci, ""), max_chars=60,
                                                      help="Nomor seri berguna untuk klaim garansi." if kunci == "seri" else None)
                a5, a6 = st.columns(2)
                barcode_in = a5.text_input("Barcode", value=b.get("barcode", ""), max_chars=40,
                                           help="Atau pasang lewat menu Scan barcode.")
                cek_in = a6.selectbox("Cek berkala", CEK_OPSI, index=idx(CEK_OPSI, cek_tiap_b(b)), format_func=teks_cek,
                                      help="Muncul di Beranda saat sudah waktunya dicek.")
            foto_lama = b.get("foto", "")
            if foto_lama:
                dat = ambil_foto(foto_lama)
                if dat:
                    st.image(dat, width=140)
            upl = st.file_uploader("Foto barang (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                   help="Foto dikecilkan otomatis supaya hemat tempat.")
            hapus_cb = st.checkbox("Hapus foto yang sekarang") if foto_lama else False
            galeri_lama, hapus_g = list(b.get("galeri", [])), []
            lamp_lama, hapus_l = list(b.get("lampiran", [])), []
            if galeri_lama:
                st.caption("Foto tambahan yang ada. Centang untuk menghapus.")
                kg = st.columns(3)
                for i, p in enumerate(galeri_lama):
                    with kg[i % 3]:
                        dat = ambil_foto(p)
                        if dat:
                            st.image(dat, use_container_width=True)
                        if st.checkbox("Hapus", key=f"hg_{mode}_{i}_{versi()}"):
                            hapus_g.append(p)
            upl_g = st.file_uploader("Foto tambahan (boleh banyak)", type=["jpg", "jpeg", "png", "webp"],
                                     accept_multiple_files=True, key=f"upl_g_{mode}_{versi()}",
                                     help=f"Misalnya foto nota atau nomor seri. Maksimal {MAKS_GALERI} foto tambahan per barang.")
            for j, x in enumerate(lamp_lama):
                if st.checkbox(f"Hapus lampiran: {x.get('nama', 'dokumen')}", key=f"hl_{mode}_{j}_{versi()}"):
                    hapus_l.append(x["path"])
            upl_l = st.file_uploader("Lampiran dokumen PDF (boleh banyak)", type=["pdf"], accept_multiple_files=True,
                                     key=f"upl_l_{mode}_{versi()}",
                                     help=f"Nota, buku manual, atau kartu garansi. Maksimal {MAKS_LAMPIRAN} berkas, masing-masing {MAKS_LAMPIRAN_MB} MB.")
            catatan = st.text_area("Catatan", value=b.get("catatan", ""),
                                   help="Alamat web yang kamu tulis di sini otomatis bisa diklik.")
            tautan = st.text_area("Tautan (satu per baris, boleh kosong)", value=b.get("tautan", ""), height=90,
                                  placeholder="https://toko.example/nota-123",
                                  help="Misalnya nota online, buku manual, atau halaman toko.")
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
                elif tautan.strip() and any(not re.match(r"https?://", s.strip(), re.IGNORECASE)
                                            for s in tautan.splitlines() if s.strip()):
                    st.error("Setiap baris tautan harus diawali http:// atau https://")
                elif (mode == "baru" or _norm_nama(nama) != _norm_nama(b.get("nama", ""))) and \
                        peringatan_serupa(nama, b.get("id", "")):
                    pass
                else:
                    id_ = b.get("id") or uuid.uuid4().hex[:8]
                    foto_baru, galat = "", ""
                    sumber = upl
                    if sumber is not None:
                        try:
                            foto_baru = simpan_foto(id_, sumber.getvalue())
                        except Exception as e:
                            galat = f"Foto gagal diunggah: {e}"
                    sisa_g = [p for p in galeri_lama if p not in hapus_g]
                    galeri_baru = []
                    if not galat and len(sisa_g) + len(upl_g or []) > MAKS_GALERI:
                        galat = f"Foto tambahan maksimal {MAKS_GALERI} per barang."
                    if not galat:
                        for f in (upl_g or []):
                            try:
                                galeri_baru.append(simpan_foto(id_, f.getvalue()))
                            except Exception as e:
                                galat = f"Foto tambahan gagal diunggah: {e}"
                                break
                    sisa_l = [x for x in lamp_lama if x["path"] not in hapus_l]
                    lamp_baru = []
                    if not galat and len(sisa_l) + len(upl_l or []) > MAKS_LAMPIRAN:
                        galat = f"Lampiran maksimal {MAKS_LAMPIRAN} berkas per barang."
                    if not galat:
                        for f in (upl_l or []):
                            isi_f = f.getvalue()
                            if len(isi_f) > MAKS_LAMPIRAN_MB * 1024 * 1024:
                                galat = f"{f.name} lebih dari {MAKS_LAMPIRAN_MB} MB."
                                break
                            try:
                                lamp_baru.append({"path": _tulis_foto(id_, isi_f, "pdf"), "nama": f.name[:80]})
                            except Exception as e:
                                galat = f"Lampiran gagal diunggah: {e}"
                                break
                    if galat:
                        for x in lamp_baru:
                            hapus_foto(x["path"])
                        st.error(galat)
                    else:
                        baru = dict(b) if mode != "baru" else {"id": id_}
                        isi = {"nama": nama, "lokasi": lok, "sublokasi": sub, "kategori": kat,
                               "catatan": catatan.strip(), "harga": int(harga),
                               "tautan": "\n".join(s.strip() for s in tautan.splitlines() if s.strip()),
                               "dibeli": tb.isoformat() if tb else "",
                               "kedaluwarsa": kd.isoformat() if kd else "",
                               "garansi": gr.isoformat() if gr else "", "habis": bool(habis),
                               "minimum": int(minimum), "dalam": induk, "pemilik": pemilik, "favorit": bool(fav),
                               "tag": list(dict.fromkeys(t.strip()[:30] for t in tag_pil if t.strip()))[:8],
                               "barcode": barcode_in.strip(), "cek_tiap": int(cek_in)}
                        isi.update({k: v.strip() for k, v in nilai_atr.items()})
                        for kunci, v in isi.items():
                            if v or kunci in ("nama", "lokasi"):
                                baru[kunci] = v
                            else:
                                baru.pop(kunci, None)
                        baru["jumlah"] = int(jumlah)
                        baru["diubah"] = hari_ini().isoformat()
                        if baru.get("cek_tiap"):
                            baru.setdefault("cek_terakhir", hari_ini().isoformat())
                        else:
                            baru.pop("cek_terakhir", None)
                        fotos_hapus = list(hapus_g)
                        if foto_baru:
                            baru["foto"] = foto_baru
                            if foto_lama:
                                fotos_hapus.append(foto_lama)
                        elif hapus_cb:
                            if foto_lama:
                                fotos_hapus.append(foto_lama)
                            baru.pop("foto", None)
                        fotos_hapus += hapus_l
                        lamp_akhir = sisa_l + lamp_baru
                        if lamp_akhir:
                            baru["lampiran"] = lamp_akhir
                        else:
                            baru.pop("lampiran", None)
                        galeri_akhir = sisa_g + galeri_baru
                        if galeri_akhir:
                            baru["galeri"] = galeri_akhir
                        else:
                            baru.pop("galeri", None)
                        tempat_baru = nama_tempat(baru)
                        if mode == "baru":
                            catat(id_, nama, "", tempat_baru)
                            D["barang"].append(baru)
                        else:
                            if nama_tempat(b) != tempat_baru:
                                catat(id_, nama, nama_tempat(b), tempat_baru)
                            D["barang"] = [baru if x["id"] == mode else x for x in D["barang"]]
                        sinkron_isi(id_)
                        selesai_simpan("Tersimpan.",
                                       sesudah=(lambda fs=fotos_hapus: [hapus_foto(p) for p in fs]) if fotos_hapus else None,
                                       br_mode=None)


# -------------------------------------------------------------- pindah massal
def pindahkan_barang(pilih: list, by_id: dict, tl: str, ts: str) -> int:
    """Pindahkan barang (daftar id) ke lokasi/sub lokasi tujuan. Kembalikan jumlah yang benar-benar pindah."""
    dipindah = 0
    item = []
    for i in pilih:
        b = by_id[i]
        dari = nama_tempat(b)
        asal = {"lokasi": b.get("lokasi", ""), "sublokasi": b.get("sublokasi", ""), "dalam": b.get("dalam", "")}
        b["lokasi"] = tl
        if ts:
            b["sublokasi"] = ts
        else:
            b.pop("sublokasi", None)
        ke = nama_tempat(b)
        if dari != ke:
            b["diubah"] = hari_ini().isoformat()
            if b.get("dalam") and b["dalam"] not in pilih:
                b.pop("dalam", None)       # dipindah sendirian: keluar dari barang induknya
            catat(i, b["nama"], dari, ke)
            item.append({"id": i, "nama": b["nama"], "dari": asal})
            dipindah += 1
    for i in pilih:
        sinkron_isi(i)                      # isi barang ikut pindah bersama induknya
    if item:
        pm = D.setdefault("pindah_massal", [])
        pm.append({"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(),
                   "tujuan": {"lokasi": tl, "sublokasi": ts or ""}, "tujuan_nama": nama_tempat(by_id[item[0]["id"]]),
                   "item": item})
        D["pindah_massal"] = pm[-10:]
    return dipindah


def batalkan_pindah(batch: dict) -> tuple:
    """Kembalikan barang dari satu pindah massal ke tempat asalnya. Barang yang sudah dipindah lagi dilewati."""
    by = {b["id"]: b for b in D["barang"]}
    tujuan = batch["tujuan"]
    kembali = lewat = 0
    ids = []
    for it in batch["item"]:
        b = by.get(it["id"])
        d = it["dari"]
        if (not b or b.get("lokasi") != tujuan["lokasi"] or (b.get("sublokasi") or "") != tujuan["sublokasi"]
                or not any(l["id"] == d["lokasi"] for l in D["lokasi"])):
            lewat += 1
            continue
        dari = nama_tempat(b)
        b["lokasi"] = d["lokasi"]
        if d["sublokasi"] and any(s["id"] == d["sublokasi"] and s["lokasi"] == d["lokasi"] for s in D["sublokasi"]):
            b["sublokasi"] = d["sublokasi"]
        else:
            b.pop("sublokasi", None)
        if d["dalam"] and d["dalam"] in by and d["dalam"] != b["id"] and d["dalam"] not in keturunan(b["id"]):
            b["dalam"] = d["dalam"]
        b["diubah"] = hari_ini().isoformat()
        if dari != nama_tempat(b):
            catat(b["id"], b["nama"], dari, nama_tempat(b))
        ids.append(b["id"])
        kembali += 1
    for i in ids:
        sinkron_isi(i)
    if kembali:
        batch["dibatalkan"] = sekarang().strftime("%Y-%m-%d %H:%M")
    return kembali, lewat


def panel_batal_pindah():
    riw = D.get("pindah_massal", [])
    if not riw:
        return
    with st.expander(f"Pindah massal terakhir ({min(len(riw), 5)})"):
        for x in reversed(riw[-5:]):
            nama = ", ".join(i["nama"] for i in x["item"][:6]) + (f" dan {len(x['item']) - 6} lainnya" if len(x["item"]) > 6 else "")
            tanda = ('<span class="lencana lc-h">Sudah dibatalkan</span>' if x.get("dibatalkan") else "")
            st.markdown(f'<div class="akt"><div class="ah">{len(x["item"])} barang → {html.escape(x.get("tujuan_nama", ""))}{tanda}</div>'
                        f'<div class="ar">{html.escape(nama)}</div>'
                        f'<div class="am">{fmt_waktu(x.get("waktu", ""))} · oleh {html.escape(x.get("oleh", ""))}'
                        + (f' · dibatalkan {fmt_waktu(x["dibatalkan"])}' if x.get("dibatalkan") else "") + '</div></div>',
                        unsafe_allow_html=True)
            if x.get("dibatalkan"):
                continue
            if st.session_state.get("pm_batal") == x["id"]:
                st.warning("Kembalikan semua barang ini ke tempat asalnya? Barang yang sudah dipindah lagi setelah itu dilewati.")
                y, n, _ = st.columns([1.3, 1, 1.4])
                if y.button("Ya, batalkan", type="primary", key=f"pmby_{x['id']}"):
                    kembali, lewat = batalkan_pindah(x)
                    if not kembali:
                        st.warning("Tidak ada yang bisa dikembalikan, karena semua barangnya sudah dipindah lagi atau dihapus.")
                    else:
                        selesai_simpan(f"{kembali} barang dikembalikan." + (f" {lewat} dilewati." if lewat else ""),
                                       pm_batal=None)
                n.button("Tidak", key=f"pmbt_{x['id']}", on_click=atur, args=("pm_batal", None))
            else:
                st.button("Batalkan pindah ini", key=f"kpakai_pmb_{x['id']}", on_click=atur, args=("pm_batal", x["id"]))


def pilih_tujuan(pl: dict):
    """Dua pilihan tujuan (lokasi dan sub lokasi). Kembalikan (id lokasi, id sub lokasi atau kosong)."""
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
    return tl, ts


def halaman_pindah():
    panel_batal_pindah()
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
        cara = st.segmented_control("Cara memindahkan", ["Pilih barang", "Seluruh isi lokasi"], default="Pilih barang",
                                    key="pm_cara", label_visibility="collapsed") or "Pilih barang"
        if cara == "Seluruh isi lokasi":
            st.markdown("#### 1. Pilih isi yang dipindahkan")
            if st.session_state.get("pm_src_lok") not in pl:
                st.session_state.pm_src_lok = next(iter(pl))
            sl = st.selectbox("Pindahkan semua isi dari lokasi", list(pl), key="pm_src_lok",
                              format_func=lambda i: pl[i])
            ssub = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == sl}
            ops_s = ["semua", "langsung"] + list(ssub)
            if st.session_state.get("pm_src_sub") not in ops_s:
                st.session_state.pm_src_sub = "semua"
            ss = st.selectbox("Bagian lokasi", ops_s, key="pm_src_sub",
                              format_func=lambda i: "Seluruh lokasi, termasuk semua sub lokasi" if i == "semua"
                              else "Hanya yang langsung di lokasi (tanpa sub lokasi)" if i == "langsung" else ssub[i])
            if ss == "semua":
                isi = [b for b in urut if b.get("lokasi") == sl]
            elif ss == "langsung":
                isi = [b for b in urut if b.get("lokasi") == sl and sub_dari(b) is None]
            else:
                isi = [b for b in urut if b.get("lokasi") == sl and b.get("sublokasi") == ss]
            st.caption(f"{len(isi)} barang akan ikut dipindahkan.")
            if isi:
                st.markdown("<br>".join(html.escape(f"• {b['nama']} ({nama_tempat(b)})") for b in isi[:12])
                            + (f"<br>…dan {len(isi) - 12} lainnya" if len(isi) > 12 else ""), unsafe_allow_html=True)
            st.markdown("#### 2. Pilih tujuan")
            tl, ts = pilih_tujuan(pl)
            sama = ss != "semua" and sl == tl and ss == (ts or "langsung")
            if isi and sama:
                st.info("Asal dan tujuannya sama, jadi tidak ada yang perlu dipindah.")
            if st.button(f"Pindahkan {len(isi)} barang", type="primary", disabled=not isi or sama, key="pm_go_isi"):
                dipindah = pindahkan_barang([b["id"] for b in isi], by_id, tl, ts)
                if not dipindah:
                    st.info("Semua barang sudah berada di tujuan itu.")
                else:
                    selesai_simpan(f"{dipindah} barang dipindahkan ke {pl[tl]}.", pm_reset=True)
            return
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
        tl, ts = pilih_tujuan(pl)
        if st.button(f"Pindahkan {len(pilih)} barang", type="primary", disabled=not pilih, key="pm_go"):
            dipindah = pindahkan_barang(list(pilih), by_id, tl, ts)
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
        d1, d2 = st.columns(2)
        t_dari = d1.date_input("Dari tanggal (boleh kosong)", value=None, key="rw_dari",
                               min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        t_sampai = d2.date_input("Sampai tanggal (boleh kosong)", value=None, key="rw_sampai",
                                 min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
        hasil = sorted(r, key=lambda x: x.get("waktu", ""), reverse=True)
        if q:
            hasil = [x for x in hasil if q in " ".join(
                [x.get("nama", ""), x.get("dari", ""), x.get("ke", "")]).lower()]
        if t_dari and t_sampai and t_dari > t_sampai:
            st.warning("Tanggal awal lebih besar dari tanggal akhir, jadi tidak ada yang cocok.")
        if t_dari:
            hasil = [x for x in hasil if x.get("waktu", "")[:10] >= t_dari.isoformat()]
        if t_sampai:
            hasil = [x for x in hasil if x.get("waktu", "")[:10] <= t_sampai.isoformat()]
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


# ----------------------------------------------------------- jelajah lokasi
def _hitung_n(b: dict, dalam: int = 0) -> int:
    return 1 + (sum(_hitung_n(x, dalam + 1) for x in isi_dari(b["id"])) if dalam < 4 else 0)


def _html_barang(b: dict, dalam: int = 0) -> str:
    h = (f'<div class="pi" style="margin-left:{dalam * 14}px"><span class="pn">{html.escape(b["nama"])}</span>'
         f'{lencana(b)}<span class="pj">{jumlah_b(b)}</span></div>')
    if dalam < 4:
        h += "".join(_html_barang(x, dalam + 1) for x in isi_dari(b["id"]))
    return h


def _html_grup(judul: str, isi: list, buka: bool, anak: str = "", n_anak: int = 0, dalam_lok: bool = False) -> str:
    n = sum(_hitung_n(b) for b in isi) + n_anak
    badan = "".join(_html_barang(b) for b in isi) + anak
    if not badan:
        badan = '<div class="pk">Belum ada barang.</div>'
    kls = "pl" if dalam_lok else "pt"
    return (f'<details class="{kls}"{" open" if buka else ""}><summary><span>{html.escape(judul)}</span>'
            f'<span class="pc">{n} barang</span></summary><div class="pb">{badan}</div></details>')


def halaman_jelajah():
    atas = [b for b in D["barang"] if not induk_dari(b)]      # isi barang ditampilkan di bawah induknya
    with st.container(key="kartu_barang"):
        kq, kb = st.columns([3, 2], vertical_alignment="center")
        q = " ".join(kq.text_input("Pencarian", key="jl_q", icon=":material/search:",
                                   placeholder="Cari barang di semua lokasi...",
                                   label_visibility="collapsed").lower().split())
        buka_semua = kb.toggle("Buka semua", key="jl_buka")
        if q:
            atas, _mirip_n = saring_barang(atas, q)
        buka = bool(q) or buka_semua
        if not D["tempat"] and not D["lokasi"]:
            st.info("Belum ada tempat atau lokasi. Buat dulu di menu Pengaturan.")
            return
        bagian = []

        def blok_lokasi(l: dict) -> str:
            milik = [b for b in atas if b.get("lokasi") == l["id"]]
            langsung = [b for b in milik if sub_dari(b) is None]
            anak, n_anak = "", 0
            for sl in sorted((x for x in D["sublokasi"] if x["lokasi"] == l["id"]), key=lambda x: x["nama"].lower()):
                ang = [b for b in milik if b.get("sublokasi") == sl["id"]]
                if q and not ang:
                    continue
                anak += _html_grup(sl["nama"], ang, buka, dalam_lok=True)
                n_anak += sum(_hitung_n(b) for b in ang)
            if q and not milik:
                return ""
            return _html_grup(l["nama"], langsung, buka, anak, n_anak, dalam_lok=True)

        id_tempat = {t["id"] for t in D["tempat"]}
        for t in sorted(D["tempat"], key=lambda t: t["nama"].lower()):
            lok = sorted((l for l in D["lokasi"] if l.get("tempat") == t["id"]), key=lambda l: l["nama"].lower())
            isi_l = "".join(blok_lokasi(l) for l in lok)
            if q and not isi_l:
                continue
            n = sum(_hitung_n(b) for b in atas if b.get("lokasi") in {l["id"] for l in lok})
            bagian.append(f'<details class="pt"{" open" if buka else ""}><summary><span>{html.escape(t["nama"])}</span>'
                          f'<span class="pc">{n} barang</span></summary><div class="pb">'
                          f'{isi_l or "<div class=pk>Belum ada lokasi di tempat ini.</div>"}</div></details>')
        lok_lain = [l for l in D["lokasi"] if l.get("tempat") not in id_tempat]
        isi_lain = "".join(blok_lokasi(l) for l in sorted(lok_lain, key=lambda l: l["nama"].lower()))
        if isi_lain:
            bagian.append(f'<details class="pt"{" open" if buka else ""}><summary><span>Tanpa tempat</span></summary>'
                          f'<div class="pb">{isi_lain}</div></details>')
        id_lok = {l["id"] for l in D["lokasi"]}
        tanpa = [b for b in atas if b.get("lokasi") not in id_lok]
        if tanpa:
            bagian.append(_html_grup(TANPA, tanpa, buka))
        total = sum(_hitung_n(b) for b in atas)
        st.caption(f"{total} barang" + (" cocok dengan pencarian" if q else " di semua lokasi")
                   + ". Sentuh nama tempat atau lokasi untuk membuka isinya.")
        if not bagian:
            st.info("Tidak ada barang yang cocok.")
        else:
            st.markdown(f'<div class="pohon">{"".join(bagian)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------ dibawa dan hilang
def _hari_sejak(iso: str) -> int:
    try:
        return (hari_ini() - date.fromisoformat(iso)).days
    except Exception:
        return 0


def tab_dibawa():
    by = {b["id"]: b for b in D["barang"]}
    aktif = sorted([b for b in D["barang"] if b.get("dibawa")], key=lambda b: b["dibawa"])
    atas = [b for b in aktif if not (induk_dari(b) and induk_dari(b).get("dibawa"))]
    with st.container(key="kartu_g_dibawa"):
        if st.session_state.get("db_mode"):
            st.markdown("#### Bawa barang")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower())
                     if not b.get("dibawa") and not b.get("hilang")]
            if not calon:
                st.info("Semua barang sudah ditandai.")
                st.button("Kembali", key="db_kembali_kosong", on_click=atur, args=("db_mode", False))
                return
            with st.form(f"form_bawa_{versi()}"):
                pil = st.multiselect("Barang yang dibawa", [b["id"] for b in calon],
                                     format_func=lambda i: f'{by[i]["nama"]} ({nama_tempat(by[i])})')
                ke = st.text_input("Dibawa ke mana atau untuk apa (boleh kosong)", max_chars=60,
                                   placeholder="Contoh: Kantor, atau Naik gunung")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai dibawa", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.db_mode = False
                st.rerun()
            if ok:
                if not pil:
                    st.error("Pilih minimal satu barang.")
                else:
                    for i in pil:
                        tandai_dibawa(by[i], ke.strip())
                    selesai_simpan(f"{len(pil)} barang ditandai sedang dibawa.", db_mode=False)
            return
        st.button("Bawa barang", type="primary", key="db_tambah", icon=":material/add:",
                  on_click=atur, args=("db_mode", True))
        if not atas:
            st.info("Tidak ada barang yang sedang dibawa. Tandai barang yang kamu bawa keluar, misalnya ke kantor "
                    "atau saat bepergian. Lokasi aslinya diingat, jadi pulangnya tinggal satu sentuhan.")
            return
        st.caption(f"{len(atas)} barang sedang dibawa.")
        for b in atas:
            with st.container(key=f"item_db_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                h = _hari_sejak(b["dibawa"])
                st.caption(f"Lokasi asal: {nama_tempat(b)} · " + (f"sudah {h} hari" if h else "sejak hari ini"))
                if st.button("Sudah kembali ke tempatnya", key=f"kpakai_db_{b['id']}"):
                    kembalikan_dibawa(b)
                    selesai_simpan(f"{b['nama']} dikembalikan ke lokasi asalnya.")
        if len(atas) > 1 and st.button(f"Kembalikan semua ({len(atas)})", key="db_semua"):
            for b in atas:
                kembalikan_dibawa(b)
            selesai_simpan("Semua barang dikembalikan ke lokasi asalnya.")


def tab_hilang():
    hl = sorted([b for b in D["barang"] if b.get("hilang")], key=lambda b: b["hilang"])
    with st.container(key="kartu_g_hilang"):
        if st.session_state.get("hl_mode"):
            st.markdown("#### Tandai barang hilang")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if not b.get("hilang")]
            if not calon:
                st.info("Belum ada barang.")
                st.button("Kembali", key="hl_kembali_kosong", on_click=atur, args=("hl_mode", False))
                return
            by = {b["id"]: b for b in calon}
            with st.form(f"form_hilang_{versi()}"):
                i = st.selectbox("Barang", list(by), format_func=lambda x: f'{by[x]["nama"]} ({nama_tempat(by[x])})')
                di = st.text_input("Terakhir terlihat di (boleh kosong)", max_chars=80,
                                   placeholder="Contoh: meja kerja, atau tas ransel")
                tgl = st.date_input("Terakhir terlihat tanggal", value=hari_ini(), min_value=TGL_MIN,
                                    max_value=TGL_MAX, format="DD/MM/YYYY")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai hilang", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.hl_mode = False
                st.rerun()
            if ok:
                tandai_hilang(by[i], di.strip(), tgl)
                selesai_simpan(f"{by[i]['nama']} ditandai hilang.", hl_mode=False)
            return
        st.button("Tandai hilang", type="primary", key="hl_tambah", icon=":material/add:",
                  on_click=atur, args=("hl_mode", True))
        if not hl:
            st.info("Tidak ada barang yang hilang. Kalau ada barang yang tidak ketemu, tandai di sini supaya tidak "
                    "terlupa dan tempat terakhir terlihatnya tercatat.")
            return
        st.caption(f"{len(hl)} barang belum ketemu.")
        for b in hl:
            with st.container(key=f"item_hl_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                st.button("Sudah ketemu", key=f"kpakai_hl_{b['id']}", on_click=atur, args=("hl_ketemu", b["id"]))
                if st.session_state.get("hl_ketemu") == b["id"]:
                    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
                    if induk_dari(b) or not pl:
                        lok = ""
                        st.caption(f"Barang ini disimpan di dalam {induk_dari(b)['nama']}, jadi tetap di lokasi itu."
                                   if induk_dari(b) else "")
                    else:
                        lok = st.selectbox("Ketemu di lokasi mana?", [""] + list(pl), key=f"hl_lok_{b['id']}",
                                           format_func=lambda x, b=b: f"Tetap di lokasi semula ({nama_tempat(b)})"
                                           if not x else pl[x])
                    y, n, _ = st.columns([1, 1, 2])
                    if y.button("Simpan", type="primary", key=f"hl_ya_{b['id']}"):
                        tandai_ketemu(b, lok)
                        selesai_simpan(f"{b['nama']} sudah ketemu.", hl_ketemu=None)
                    n.button("Batal", key=f"hl_batal_{b['id']}", on_click=atur, args=("hl_ketemu", None))


# ------------------------------------------------------------ catatan perawatan
JENIS_RAWAT = ["Servis", "Perbaikan", "Ganti suku cadang", "Pembersihan", "Pengecekan", "Lainnya"]


def catat_perawatan(b: dict, tgl: date, jenis: str, catatan: str = "", biaya: int = 0):
    """Tambah satu catatan perawatan ke barang. Kalau barang punya pengingat berkala, jadwal cek ikut diperbarui."""
    b.setdefault("perawatan", []).append({"id": uuid.uuid4().hex[:8], "tgl": tgl.isoformat(), "jenis": jenis,
                                          "catatan": catatan.strip(), "biaya": max(int(biaya or 0), 0)})
    b["perawatan"] = b["perawatan"][-200:]
    if jenis != "Lainnya" and cek_tiap_b(b) and tgl.isoformat() >= (b.get("cek_terakhir") or ""):
        b["cek_terakhir"] = tgl.isoformat()
    b["diubah"] = hari_ini().isoformat()


def html_rawat(x: dict, nama_barang: str = "") -> str:
    judul = html.escape(x.get("jenis", "")) + (f" · {html.escape(nama_barang)}" if nama_barang else "")
    cat = f'<div class="ar">{html_tautan(x["catatan"])}</div>' if x.get("catatan") else ""
    biaya = f" · {rp(x['biaya'])}" if x.get("biaya") else ""
    return (f'<div class="akt"><div class="ah">{judul}</div>{cat}'
            f'<div class="am">{fmt_iso(x.get("tgl", ""))}{biaya}</div></div>')


def halaman_perawatan():
    t1, t2 = st.tabs(["Per barang", "Terbaru"])
    with t1:
        with st.container(key="kartu_g_rawat"):
            if not D["barang"]:
                st.info("Belum ada barang.")
                return
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            by = {b["id"]: b for b in urut}
            if st.session_state.get("rwt_barang") not in by:
                st.session_state.rwt_barang = urut[0]["id"]
            pid = st.selectbox("Barang", list(by), key="rwt_barang",
                               format_func=lambda i: f'{by[i]["nama"]} ({nama_tempat(by[i])})')
            b = by[pid]
            riw = sorted(b.get("perawatan", []), key=lambda x: x.get("tgl", ""), reverse=True)
            total = sum(int(x.get("biaya", 0) or 0) for x in riw)
            st.caption(f"{len(riw)} catatan" + (f" · terakhir {fmt_iso(riw[0]['tgl'])}" if riw else "")
                       + (f" · total biaya {rp(total)}" if total else ""))
            with st.form(f"form_rawat_{versi()}"):
                f1, f2 = st.columns(2)
                tgl = f1.date_input("Tanggal", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                jenis = f2.selectbox("Jenis", JENIS_RAWAT)
                catatan = st.text_area("Catatan (boleh kosong)", height=80, max_chars=500,
                                       placeholder="Contoh: ganti oli, filter air diganti")
                biaya = st.number_input("Biaya (Rp, boleh 0)", min_value=0, value=0, step=1000)
                kirim = st.form_submit_button("Tambah catatan", type="primary")
            if kirim:
                catat_perawatan(b, tgl, jenis, catatan, int(biaya))
                selesai_simpan("Catatan perawatan ditambahkan.")
            if b.get("cek_tiap"):
                st.caption(f"Barang ini punya pengingat berkala ({teks_cek(b['cek_tiap']).lower()}). "
                           "Menambah catatan selain Lainnya ikut memperbarui tanggal terakhir dicek.")
            for x in riw:
                st.markdown(html_rawat(x), unsafe_allow_html=True)
                if st.session_state.get("rt_hapus") == x["id"]:
                    st.warning("Hapus catatan ini?")
                    y, n, _ = st.columns([1, 1, 3])
                    if y.button("Ya, hapus", type="primary", key=f"rtya_{x['id']}"):
                        b["perawatan"] = [r for r in b["perawatan"] if r["id"] != x["id"]]
                        if not b["perawatan"]:
                            b.pop("perawatan", None)
                        selesai_simpan("Catatan dihapus.", rt_hapus=None)
                    n.button("Batal", key=f"rtbt_{x['id']}", on_click=atur, args=("rt_hapus", None))
                else:
                    st.button("Hapus", key=f"khapus_rt_{x['id']}", on_click=atur, args=("rt_hapus", x["id"]))
    with t2:
        with st.container(key="kartu_g_rawat2"):
            semua = [(x, b) for b in D["barang"] for x in b.get("perawatan", [])]
            if not semua:
                st.info("Belum ada catatan perawatan. Tambahkan lewat tab Per barang.")
            else:
                st.caption(f"{len(semua)} catatan di {len({b['id'] for _, b in semua})} barang. 30 terbaru ditampilkan.")
                for x, b in sorted(semua, key=lambda t: t[0].get("tgl", ""), reverse=True)[:30]:
                    st.markdown(html_rawat(x, b["nama"]), unsafe_allow_html=True)


# ------------------------------------------------------------ rusak dan sedang diservis
def tandai_kondisi(b: dict, kondisi: str, ket: str = "", tgl=None):
    if not b.get("kondisi_sejak") or tgl:
        b["kondisi_sejak"] = (tgl or hari_ini()).isoformat()
    b["kondisi"] = kondisi
    if ket:
        b["kondisi_ket"] = ket
    else:
        b.pop("kondisi_ket", None)
    b["diubah"] = hari_ini().isoformat()


def kondisi_beres(b: dict, ket: str = "", biaya: int = 0):
    """Barang sudah baik lagi. Dicatat otomatis sebagai catatan perawatan."""
    if b.get("kondisi") in KONDISI:
        catat_perawatan(b, hari_ini(), "Perbaikan" if b["kondisi"] == "rusak" else "Servis",
                        ket or b.get("kondisi_ket", ""), biaya)
    for k in ("kondisi", "kondisi_sejak", "kondisi_ket"):
        b.pop(k, None)
    b["diubah"] = hari_ini().isoformat()


def tab_rusak():
    rs = sorted([b for b in D["barang"] if b.get("kondisi") in KONDISI], key=lambda b: b.get("kondisi_sejak", ""))
    with st.container(key="kartu_g_rusak"):
        if st.session_state.get("rs_mode"):
            st.markdown("#### Tandai rusak atau diservis")
            calon = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if not b.get("kondisi")]
            if not calon:
                st.info("Semua barang sudah ditandai.")
                st.button("Kembali", key="rs_kembali_kosong", on_click=atur, args=("rs_mode", False))
                return
            by = {b["id"]: b for b in calon}
            with st.form(f"form_rusak_{versi()}"):
                i = st.selectbox("Barang", list(by), format_func=lambda x: f'{by[x]["nama"]} ({nama_tempat(by[x])})')
                kd = st.radio("Kondisi", ["Rusak", "Sedang diservis"], horizontal=True)
                ket = st.text_input("Keterangan (boleh kosong)", max_chars=100,
                                    placeholder="Contoh: layar retak, atau dikirim ke toko servis")
                tgl = st.date_input("Sejak", value=hari_ini(), min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                c1, c2 = st.columns(2)
                ok = c1.form_submit_button("Tandai", type="primary")
                kb = c2.form_submit_button("Kembali")
            if kb:
                st.session_state.rs_mode = False
                st.rerun()
            if ok:
                tandai_kondisi(by[i], "rusak" if kd == "Rusak" else "servis", ket.strip(), tgl)
                selesai_simpan(f"{by[i]['nama']} ditandai {kd.lower()}.", rs_mode=False)
            return
        st.button("Tandai rusak atau diservis", type="primary", key="rs_tambah", icon=":material/add:",
                  on_click=atur, args=("rs_mode", True))
        if not rs:
            st.info("Tidak ada barang yang rusak atau sedang diservis. Tandai di sini supaya tidak terlupa, "
                    "dan saat sudah beres otomatis tercatat di Catatan perawatan.")
            return
        st.caption(f"{len(rs)} barang belum beres.")
        for b in rs:
            with st.container(key=f"item_rs_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                e1, e2, _ = st.columns([1.6, 1.8, 0.4])
                lain = "servis" if b["kondisi"] == "rusak" else "rusak"
                if e1.button("Sudah beres", key=f"kpakai_rs_{b['id']}", use_container_width=True,
                             on_click=atur, args=("rs_beres", b["id"])):
                    pass
                if e2.button(f"Ubah ke {KONDISI[lain].lower()}", key=f"kedit_rs_{b['id']}", use_container_width=True):
                    tandai_kondisi(b, lain, b.get("kondisi_ket", ""))
                    selesai_simpan(f"{b['nama']} ditandai {KONDISI[lain].lower()}.")
                if st.session_state.get("rs_beres") == b["id"]:
                    ct = st.text_input("Catatan hasil (boleh kosong)", key=f"rs_ct_{b['id']}", max_chars=200,
                                       placeholder="Contoh: ganti layar, garansi toko")
                    bi = st.number_input("Biaya (Rp, boleh 0)", min_value=0, value=0, step=1000, key=f"rs_bi_{b['id']}")
                    y, n, _ = st.columns([1.2, 1, 1.4])
                    if y.button("Simpan", type="primary", key=f"rs_ya_{b['id']}"):
                        kondisi_beres(b, ct.strip(), int(bi))
                        selesai_simpan(f"{b['nama']} sudah beres dan dicatat di perawatan.", rs_beres=None)
                    n.button("Batal", key=f"rs_bt_{b['id']}", on_click=atur, args=("rs_beres", None))


def halaman_dibawa():
    t1, t2, t3 = st.tabs(["Sedang dibawa", "Hilang", "Rusak dan servis"])
    with t1:
        tab_dibawa()
    with t2:
        tab_hilang()
    with t3:
        tab_rusak()


# -------------------------------------------------------------- ukuran data
def _kb(n) -> str:
    n = float(n)
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")
    return f"{n / 1024:.1f} KB".replace(".", ",")


def daftar_foto_repo():
    """[(path, ukuran_byte)] semua berkas di folder foto penyimpanan, atau None kalau gagal dibaca."""
    c = cfg_github()
    try:
        if c:
            r = requests.get(_gh_url(c, "foto"), headers=_gh_headers(c), params={"ref": c["branch"]}, timeout=30)
            if r.status_code == 404:
                return []
            r.raise_for_status()
            return [(x["path"], int(x.get("size", 0))) for x in r.json() if x.get("type") == "file"]
        if not os.path.isdir(FOTO_LOKAL):
            return []
        return [(f"foto/{n}", os.path.getsize(os.path.join(FOTO_LOKAL, n))) for n in sorted(os.listdir(FOTO_LOKAL))]
    except Exception:
        return None


def foto_terpakai() -> set:
    pakai = set()
    for b in D["barang"] + [x["barang"] for x in D["sampah"]]:
        pakai.update(semua_berkas(b))
    for x in D["lokasi"] + D["sublokasi"]:
        if x.get("foto"):
            pakai.add(x["foto"])
    return pakai


def ganti_path_foto(lama: str, baru: str):
    for b in D["barang"] + [x["barang"] for x in D["sampah"]]:
        if b.get("foto") == lama:
            b["foto"] = baru
        if lama in b.get("galeri", []):
            b["galeri"] = [baru if p == lama else p for p in b["galeri"]]
    for x in D["lokasi"] + D["sublokasi"]:
        if x.get("foto") == lama:
            x["foto"] = baru


def kecilkan_jpeg(mentah: bytes, sisi: int) -> bytes:
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(mentah))).convert("RGB")
    im.thumbnail((sisi, sisi))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=65, optimize=True)
    return out.getvalue()


def halaman_ukuran():
    teks = json.dumps(D, ensure_ascii=False, indent=1, sort_keys=True)
    ukuran_data = len(teks.encode("utf-8"))
    rinci = sorted(((k, len(json.dumps(v, ensure_ascii=False, indent=1).encode("utf-8"))) for k, v in D.items()),
                   key=lambda x: -x[1])
    fotos = daftar_foto_repo()
    pakai = foto_terpakai()
    with st.container(key="kartu_barang"):
        st.markdown("#### Data (data.json)")
        st.markdown(f"**{_kb(ukuran_data)}** · {len(D['barang'])} barang")
        for k, n in rinci[:6]:
            persen = int(round(n * 100 / max(ukuran_data, 1)))
            st.markdown(f'<div class="perhatian"><div class="brg">{html.escape(k)}</div>'
                        f'<div class="sub">{_kb(n)} · {persen}%</div></div>', unsafe_allow_html=True)
        st.markdown("#### Foto")
        if fotos is None:
            st.warning("Folder foto tidak bisa dibaca saat ini. Coba lagi nanti.")
            return
        total_foto = sum(n for _, n in fotos)
        yatim = [(p, n) for p, n in fotos if p not in pakai]
        st.markdown(f"**{len(fotos)} foto** · {_kb(total_foto)}")
        total = ukuran_data + total_foto
        st.progress(min(1.0, total / (1024 ** 3)), text=f"Total {_kb(total)} dari sekitar 1 GB batas nyaman repositori")
        besar = sorted([f for f in fotos if f[0].lower().endswith((".jpg", ".jpeg", ".png", ".webp"))], key=lambda x: -x[1])[:8]
        if besar:
            st.markdown("**Foto terbesar**")
            for p, n in besar:
                c1, c2 = st.columns([1, 3], vertical_alignment="center")
                dat = ambil_foto(p)
                if dat:
                    c1.image(dat, width=56)
                c2.markdown(f"{_kb(n)}" + ("" if p in pakai else " · tidak terpakai"))

        st.markdown("#### Foto tidak terpakai")
        if not yatim:
            st.caption("Tidak ada. Semua foto di penyimpanan masih dipakai oleh barang atau lokasi.")
        else:
            st.caption(f"{len(yatim)} foto ({_kb(sum(n for _, n in yatim))}) tidak dipakai barang, lokasi, "
                       "maupun tempat sampah. Biasanya sisa dari unggahan yang tidak jadi disimpan.")
            if not st.session_state.get("uk_yatim"):
                st.button(f"Hapus {len(yatim)} foto tidak terpakai", key="uk_yatim_btn",
                          on_click=atur, args=("uk_yatim", True))
            else:
                st.warning("Hapus foto-foto ini dari penyimpanan? Ini tidak bisa dibatalkan.")
                y, n_, _ = st.columns([1.2, 1, 1])
                if y.button("Ya, hapus", type="primary", key="uk_yatim_ya"):
                    for p, _n in yatim:
                        hapus_foto(p)
                    st.session_state.uk_yatim = False
                    st.toast(f"{len(yatim)} foto dihapus.", icon="🧹")
                    st.rerun()
                n_.button("Batal", key="uk_yatim_bt", on_click=atur, args=("uk_yatim", False))

        st.markdown("#### Kecilkan foto")
        st.caption("Foto dikecilkan lagi dan disimpan sebagai berkas baru, lalu yang lama dihapus. "
                   "Dikerjakan maksimal 10 foto sekali jalan.")
        k1, k2 = st.columns(2)
        sisi = k1.selectbox("Sisi terpanjang (px)", [700, 500, 900], key="uk_sisi")
        ambang = k2.number_input("Hanya yang lebih besar dari (KB)", min_value=20, value=120, step=10, key="uk_ambang")
        kandidat = [(p, n) for p, n in fotos if p in pakai and n > ambang * 1024 and p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        st.caption(f"{len(kandidat)} foto memenuhi syarat.")
        if kandidat and Image is not None and st.button(f"Kecilkan {min(len(kandidat), 10)} foto", key="uk_kecil"):
            hapus_lama, hemat = [], 0
            bar = st.progress(0.0, text="Memproses...")
            batch = sorted(kandidat, key=lambda x: -x[1])[:10]
            for i, (p, n) in enumerate(batch):
                bar.progress((i + 1) / len(batch), text=f"Memproses {i + 1} dari {len(batch)}")
                dat = ambil_foto(p)
                if not dat:
                    continue
                try:
                    isi = kecilkan_jpeg(dat, int(sisi))
                    if len(isi) >= n * 0.9:
                        continue
                    baru_p = _tulis_foto(os.path.splitext(os.path.basename(p))[0].split("_")[0], isi)
                except Exception:
                    continue
                ganti_path_foto(p, baru_p)
                hapus_lama.append(p)
                hemat += n - len(isi)
            if hapus_lama:
                st.session_state["_snap"] = None          # penggantian berkas tidak dicatat di riwayat aktivitas
                selesai_simpan(f"{len(hapus_lama)} foto dikecilkan, hemat {_kb(hemat)}.",
                               sesudah=lambda fs=hapus_lama: [hapus_foto(p) for p in fs])
            else:
                st.info("Tidak ada foto yang bisa diperkecil lagi dengan pengaturan ini.")


# --------------------------------------------------------------- titik pulih
def halaman_pulih():
    with st.container(key="kartu_barang"):
        st.caption("Setiap perubahan tersimpan sebagai satu versi. Pilih versi lama untuk melihat perbedaannya, "
                   "lalu pulihkan seluruh data ke versi itu. Foto yang sudah dihapus tidak ikut kembali.")
        try:
            daftar = daftar_versi()
        except Exception as e:
            st.error(f"Riwayat versi tidak bisa dibaca: {e}")
            return
        if not daftar:
            st.info("Belum ada versi tersimpan. Versi pertama tercatat saat ada perubahan data berikutnya.")
            return
        peta = {v["id"]: v for v in daftar}
        pilih = st.selectbox("Versi", list(peta), key="pl_versi",
                             format_func=lambda i: f"{fmt_waktu(peta[i]['waktu'])} · {peta[i]['pesan'][:55]}")
        try:
            lama = ambil_versi(pilih)
        except Exception as e:
            st.error(f"Versi ini tidak bisa dibuka: {e}")
            return
        for k, v in data_kosong().items():
            lama.setdefault(k, v)
        kini_id = {b["id"]: b for b in D["barang"]}
        lama_id = {b["id"]: b for b in lama["barang"]}
        hilang_n = [b["nama"] for i, b in kini_id.items() if i not in lama_id]
        muncul_n = [b["nama"] for i, b in lama_id.items() if i not in kini_id]
        berubah_n = sum(1 for i, b in lama_id.items() if i in kini_id and kini_id[i] != b)
        st.markdown("**Perbandingan** (sekarang → versi ini)")
        for lab, kunci in (("Barang", "barang"), ("Tempat", "tempat"), ("Lokasi", "lokasi"),
                           ("Kategori", "kategori"), ("Tempat sampah", "sampah")):
            st.markdown(f'<div class="perhatian"><div class="brg">{lab}</div><div class="sub">'
                        f'{len(D.get(kunci, []))} → {len(lama.get(kunci, []))}</div></div>', unsafe_allow_html=True)

        def ringkas(nama_nama):
            return html.escape(", ".join(nama_nama[:8]) + (f" dan {len(nama_nama) - 8} lainnya" if len(nama_nama) > 8 else ""))
        if hilang_n:
            st.markdown(f"**Akan hilang dari daftar ({len(hilang_n)}):** {ringkas(hilang_n)}")
        if muncul_n:
            st.markdown(f"**Akan muncul kembali ({len(muncul_n)}):** {ringkas(muncul_n)}")
        if berubah_n:
            st.markdown(f"**Akan kembali ke isi lama:** {berubah_n} barang")
        sama = json.dumps(lama, sort_keys=True) == json.dumps(D, sort_keys=True)
        if sama:
            st.info("Versi ini sama persis dengan data sekarang, tidak ada yang perlu dipulihkan.")
            return
        yakin = st.checkbox("Ya, ganti seluruh data sekarang dengan versi ini", key=f"pl_yakin_{pilih}")
        if st.button("Pulihkan ke versi ini", type="primary", disabled=not yakin, key="pl_go"):
            lama.setdefault("aktivitas", []).append(
                {"id": uuid.uuid4().hex[:8], "waktu": sekarang().strftime("%Y-%m-%d %H:%M"), "oleh": pengguna_nama(),
                 "jenis": "data", "barang": "", "nama": "Seluruh data",
                 "rincian": f"Dipulihkan ke versi {fmt_waktu(peta[pilih]['waktu'])}: {peta[pilih]['pesan'][:80]}"})
            st.session_state.data = lama
            st.session_state["_snap"] = None
            selesai_simpan(f"Data dipulihkan ke versi {fmt_waktu(peta[pilih]['waktu'])}.")


# --------------------------------------------------------- riwayat aktivitas
JENIS_AKT = {"tambah": ("Ditambah", "lc-h"), "ubah": ("Diubah", "lc-b"), "buang": ("Dibuang", "lc-m"),
             "pulih": ("Dipulihkan", "lc-h"), "hapus": ("Dihapus permanen", "lc-r"),
             "data": ("Data dipulihkan", "lc-r")}


def _kosong(v) -> bool:
    return v is None or v is False or v == ""


def kembalikan_perubahan(x: dict) -> tuple:
    """Kembalikan nilai lama dari satu catatan 'ubah'. Bagian yang sudah berubah lagi dilewati."""
    b = next((y for y in D["barang"] if y["id"] == x.get("barang")), None)
    if not b:
        return 0, len(x.get("perubahan", []))

    def sah(k, v) -> bool:
        if _kosong(v):
            return k != "nama"
        if k == "lokasi":
            return any(l["id"] == v for l in D["lokasi"])
        if k == "sublokasi":
            return any(l["id"] == v for l in D["sublokasi"])
        if k == "kategori":
            return any(l["id"] == v for l in D["kategori"])
        if k == "dalam":
            return v != b["id"] and v not in keturunan(b["id"]) and any(y["id"] == v for y in D["barang"])
        return True

    dari_tempat = nama_tempat(b)
    kembali = lewat = 0
    for p in x.get("perubahan", []):
        k, skrg = p["k"], b.get(p["k"])
        skrg = "" if _kosong(skrg) else skrg
        if skrg != p["ke"] or not sah(k, p["dari"]):
            lewat += 1
            continue
        if _kosong(p["dari"]):
            b.pop(k, None)
        else:
            b[k] = p["dari"]
        kembali += 1
    if kembali:
        b["diubah"] = hari_ini().isoformat()
        induk = induk_dari(b)
        if induk:
            ikut_induk(b, induk)
        elif nama_tempat(b) != dari_tempat:
            catat(b["id"], b["nama"], dari_tempat, nama_tempat(b))
        sinkron_isi(b["id"])
        x["dikembalikan"] = sekarang().strftime("%Y-%m-%d %H:%M")
    return kembali, lewat


def halaman_aktivitas():
    log = D.get("aktivitas", [])
    with st.container(key="kartu_barang"):
        if not log:
            st.info("Belum ada aktivitas. Mulai sekarang, setiap barang yang ditambah, diubah, dibuang, "
                    "atau dipulihkan tercatat di sini beserta siapa yang melakukannya.")
            return
        kc, kj = st.columns([3, 2], vertical_alignment="center")
        q = " ".join(kc.text_input("Pencarian", key="ak_q", icon=":material/search:",
                                   placeholder="Cari barang, orang, atau isi perubahan...",
                                   label_visibility="collapsed").lower().split())
        pilihan = ["Semua"] + [v[0] for v in JENIS_AKT.values()]
        jenis = kj.selectbox("Jenis", pilihan, key="ak_jenis", label_visibility="collapsed")
        hasil = sorted(log, key=lambda x: x.get("waktu", ""), reverse=True)
        if jenis != "Semua":
            kode = next(k for k, v in JENIS_AKT.items() if v[0] == jenis)
            hasil = [x for x in hasil if x.get("jenis") == kode]
        if q:
            hasil = [x for x in hasil if q in " ".join(
                [x.get("nama", ""), x.get("oleh", ""), x.get("rincian", "")]).lower()]
        n = st.session_state.get("ak_n", 40)
        st.caption(f"{len(hasil)} dari {len(log)} catatan")
        if not hasil:
            st.info("Tidak ada catatan yang cocok.")
        for x in hasil[:n]:
            lab, kls = JENIS_AKT.get(x.get("jenis"), (x.get("jenis", ""), "lc-b"))
            rin = f'<div class="ar">{html.escape(x["rincian"])}</div>' if x.get("rincian") else ""
            st.markdown(
                f'<div class="akt"><div class="ah">{html.escape(x.get("nama", ""))}'
                f'<span class="lencana {kls}">{lab}</span></div>{rin}'
                f'<div class="am">{fmt_waktu(x.get("waktu", ""))} · oleh {html.escape(x.get("oleh", ""))}'
                + (f' · sudah dikembalikan {fmt_waktu(x["dikembalikan"])}' if x.get("dikembalikan") else "")
                + '</div></div>',
                unsafe_allow_html=True)
            if (x.get("jenis") == "ubah" and x.get("perubahan") and not x.get("dikembalikan")
                    and any(y["id"] == x.get("barang") for y in D["barang"])):
                if st.button("Kembalikan perubahan ini", key=f"kpakai_kb_{x['id']}"):
                    kembali, lewat = kembalikan_perubahan(x)
                    if not kembali:
                        st.warning("Tidak bisa dikembalikan, karena nilainya sudah berubah lagi setelah itu.")
                    else:
                        selesai_simpan("Perubahan dikembalikan."
                                       + (f" {lewat} bagian dilewati karena sudah berubah lagi." if lewat else ""))
        if len(hasil) > n:
            st.button(f"Tampilkan lebih banyak ({len(hasil) - n} lagi)", key="ak_lagi",
                      on_click=atur, args=("ak_n", n + 40))


# ------------------------------------------------------------- tempat sampah
def halaman_sampah():
    lama = [s for s in D["sampah"] if sisa_sampah(s) <= 0]
    if lama:                              # bersihkan yang sudah lewat masa simpan
        fs = [p for s in lama for p in semua_berkas(s["barang"])]
        D["sampah"] = [s for s in D["sampah"] if sisa_sampah(s) > 0]
        selesai_simpan(f"{len(lama)} barang lama dibersihkan dari tempat sampah.",
                       sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p])
    ada = sorted(D["sampah"], key=lambda s: s.get("dihapus", ""), reverse=True)
    with st.container(key="kartu_barang"):
        if not ada:
            st.info(f"Tempat sampah kosong. Barang yang dibuang disimpan di sini {MASA_SAMPAH} hari "
                    "sebelum hilang permanen.")
            return
        st.caption(f"{len(ada)} barang. Setelah {MASA_SAMPAH} hari barang dihapus permanen, termasuk fotonya.")
        for s in ada:
            b = s["barang"]
            with st.container(key=f"item_s_{s['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                st.caption(f"Dibuang {fmt_waktu(s.get('dihapus', ''))} oleh {s.get('oleh', '')} · "
                           f"hilang permanen dalam {max(sisa_sampah(s), 0)} hari")
                e1, e2, _ = st.columns([1.2, 1.8, 1])
                if e1.button("Pulihkan", key=f"kpakai_sp_{s['id']}", use_container_width=True):
                    pulih = dict(b)
                    induk = next((x for x in D["barang"] if x["id"] == pulih.get("dalam")), None)
                    if induk:                 # kembali ke dalam induknya, ikut lokasi induk
                        pulih["lokasi"] = induk.get("lokasi", "")
                        if induk.get("sublokasi"):
                            pulih["sublokasi"] = induk["sublokasi"]
                        else:
                            pulih.pop("sublokasi", None)
                    else:
                        pulih.pop("dalam", None)
                    pulih["diubah"] = hari_ini().isoformat()
                    D["barang"].append(pulih)
                    D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                    catat(pulih["id"], pulih["nama"], "(tempat sampah)", nama_tempat(pulih))
                    selesai_simpan("Barang dipulihkan.")
                e2.button("Hapus permanen", key=f"khapus_sp_{s['id']}", on_click=atur,
                          args=("sp_hapus", s["id"]), use_container_width=True)
                if st.session_state.get("sp_hapus") == s["id"]:
                    st.warning(f"Hapus permanen {b['nama']}? Ini tidak bisa dibatalkan.")
                    y, n, _ = st.columns([1.3, 1, 2])
                    if y.button("Ya, hapus permanen", type="primary", key=f"spya_{s['id']}"):
                        fs = semua_berkas(b)
                        D["sampah"] = [x for x in D["sampah"] if x["id"] != s["id"]]
                        selesai_simpan("Dihapus permanen.",
                                       sesudah=(lambda fs=fs: [hapus_foto(p) for p in fs]) if fs else None, sp_hapus=None)
                    n.button("Batal", key=f"spbt_{s['id']}", on_click=atur, args=("sp_hapus", None))
        if st.session_state.get("sp_kosong"):
            st.warning("Kosongkan seluruh tempat sampah? Semua barang di dalamnya hilang permanen.")
            y, n, _ = st.columns([1.5, 1, 2])
            if y.button("Ya, kosongkan", type="primary", key="sp_kosong_ya"):
                fs = [p for s in D["sampah"] for p in semua_berkas(s["barang"])]
                D["sampah"] = []
                selesai_simpan("Tempat sampah dikosongkan.",
                               sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p], sp_kosong=False)
            n.button("Batal", key="sp_kosong_bt", on_click=atur, args=("sp_kosong", False))
        else:
            st.button("Kosongkan tempat sampah", key="sp_kosong_btn", on_click=atur, args=("sp_kosong", True))


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


def kartu_pinjam_html(p: dict) -> str:
    """Kartu satu peminjaman: huruf awal, nama + lencana arah, orang dan tanggal, tenggat di kanan."""
    tanda = ('<span class="lencana lc-m">Dipinjamkan</span>' if p.get("arah") == "keluar"
             else '<span class="lencana lc-b">Saya pinjam</span>')
    orang = html.escape(p.get("orang", ""))
    kata = "dengan" if p.get("arah") == "keluar" else "dari"
    mt = f'<div class="mt">{kata} {orang} • sejak {fmt_iso(p.get("tanggal", ""))}</div>'
    cat = f'<div class="cat">{html.escape(p["catatan"])}</div>' if p.get("catatan") else ""
    ic = html.escape((p.get("nama", "").strip()[:1] or "?").upper())
    if p.get("tenggat"):
        kanan = (f'<div class="qt"><span>Tenggat</span><span>{fmt_iso(p["tenggat"])}</span>'
                 f'{status_sisa(sisa_hari(p["tenggat"]))}</div>')
    else:
        kanan = '<div class="qt"><span>Tanpa tenggat</span></div>'
    return (f'<div class="itm pj"><div class="ic">{ic}</div><div class="isi"><div class="jd">'
            f'{html.escape(p.get("nama", ""))}{tanda}</div>{mt}{cat}</div>{kanan}</div>')


def halaman_pinjam():
    by_id = {b["id"]: b for b in D["barang"]}
    aktif = [p for p in D["pinjam"] if not p.get("kembali")]
    selesai = [p for p in D["pinjam"] if p.get("kembali")]
    hari = hari_ini()
    with st.container(key="kartu_barang"):
        if st.session_state.get("pj_mode") == "baru":
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
                tgl = c2.date_input("Tanggal", value=hari, min_value=TGL_MIN, max_value=TGL_MAX,
                                    format="DD/MM/YYYY")
                tenggat = c3.date_input("Tenggat kembali (boleh kosong)", value=None,
                                        min_value=TGL_MIN, max_value=TGL_MAX, format="DD/MM/YYYY")
                catatan = st.text_input("Catatan (boleh kosong)")
                t1, t2, _ = st.columns([1, 1, 4])
                kirim = t1.form_submit_button("Catat", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.pj_mode = None
                st.rerun()
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
                                        "tanggal": tgl.isoformat(),
                                        "tenggat": tenggat.isoformat() if tenggat else "",
                                        "catatan": catatan.strip(), "kembali": ""})
                    selesai_simpan("Peminjaman dicatat.", pj_mode=None)
            return

        with st.container(key="baris_cari"):
            kc, kt = st.columns([5, 2], vertical_alignment="center")
            cari = " ".join(kc.text_input("Pencarian", key="pj_cari", icon=":material/search:",
                                          placeholder="Cari barang atau nama orang...",
                                          label_visibility="collapsed").lower().split())
            kt.button("Tambah", type="primary", key="pj_tambah", icon=":material/add:",
                      use_container_width=True, on_click=atur, args=("pj_mode", "baru"))
        mode_tampil = st.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                           key="tampilan", label_visibility="collapsed") or "Kartu"
        urut = sorted(aktif, key=lambda x: (x.get("tenggat") or "9999-12-31", x.get("tanggal", "")))
        if cari:
            urut = [p for p in urut if cari in " ".join([p.get("nama", ""), p.get("orang", ""),
                                                          p.get("catatan", "")]).lower()]
        st.markdown(f"#### Sedang berjalan ({len(aktif)})")
        if not aktif:
            st.caption("Tidak ada peminjaman yang sedang berjalan. Tekan Tambah untuk mencatat.")
        elif not urut:
            st.info("Tidak ada peminjaman yang cocok dengan pencarian.")
        elif mode_tampil == "Kartu":
            for p in urut:
                with st.container(key=f"item_p_{p['id']}"):
                    st.markdown(kartu_pinjam_html(p), unsafe_allow_html=True)
                    e1, e2, _ = st.columns([2, 1, 1])
                    if e1.button("Sudah kembali", key=f"kpakai_pj_{p['id']}", use_container_width=True):
                        p["kembali"] = hari.isoformat()
                        selesai_simpan("Dicatat sudah kembali.")
                    e2.button("Hapus", key=f"khapus_pj_{p['id']}", on_click=atur, args=("pj_hapus", p["id"]),
                              use_container_width=True)
                    _baris_hapus_pinjam(p)
        else:
            lebar = [3.4, 2.2, 1.8, 2.2, 2.8]
            kep = st.columns(lebar, vertical_alignment="top")
            for kol, judul in zip(kep, ["Barang", "Dengan siapa", "Sejak", "Tenggat", "Aksi"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for p in urut:
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
        if st.session_state.get("bl_mode") and lain:
            st.markdown("#### Tandai barang yang habis")
            with st.form(f"form_beli_{versi()}"):
                pilih = st.selectbox("Barang", [b["id"] for b in lain],
                                     format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                t1, t2, _ = st.columns([1.6, 1, 2])
                kirim = t1.form_submit_button("Tandai perlu beli", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.bl_mode = False
                st.rerun()
            if kirim:
                by_id[pilih]["habis"] = True
                by_id[pilih]["diubah"] = hari_ini().isoformat()
                selesai_simpan("Ditandai perlu beli.", bl_mode=False)
            return
        if lain:
            st.button("Tandai habis", type="primary", key="bl_tambah", icon=":material/add:",
                      on_click=atur, args=("bl_mode", True),
                      help="Tandai barang yang sudah habis supaya masuk daftar belanja")
        st.markdown(f"#### Stok menipis atau habis ({len(perlu)})")
        if not perlu:
            st.caption("Tidak ada barang yang perlu dibeli.")
            return
        total = 0
        for b in perlu:
            m = minimum_b(b)
            with st.container(key=f"item_b_{b['id']}"):
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                c1, c2 = st.columns([1, 1.6], vertical_alignment="bottom")
                n_beli = int(c1.number_input("Jumlah beli", min_value=1, step=1, key=f"bl_n_{b['id']}",
                                             value=max(m - jumlah_b(b) + 1, 1) if m else 1))
                total += harga_b(b) * n_beli
                if c2.button("Sudah dibeli", key=f"kpakai_bl_{b['id']}", use_container_width=True):
                    b.pop("habis", None)
                    b["jumlah"] = jumlah_b(b) + n_beli
                    b["dibeli"] = hari_ini().isoformat()
                    b["diubah"] = hari_ini().isoformat()
                    selesai_simpan("Stok ditambah dan dicoret dari daftar belanja.")
        st.caption(f"Perkiraan total: {rp(total)} (harga beli terakhir × jumlah yang dibeli).")
        teks = "\n".join(f"- {b['nama']} ({nama_tempat(b)})" + (f" ± {rp(harga_b(b))}" if harga_b(b) else "")
                         for b in perlu)
        st.download_button("Unduh daftar belanja (.txt)", teks, file_name="daftar-belanja.txt", mime="text/plain")


# ------------------------------------------------------- kedaluwarsa & garansi
# ------------------------------------------------------------- rencana beli
PRIORITAS = ["Tinggi", "Sedang", "Rendah"]
LC_PRIORITAS = {"Tinggi": "lc-r", "Sedang": "lc-m", "Rendah": "lc-b"}


def _hapus_rencana(x):
    if st.session_state.get("rc_hapus") == x["id"]:
        st.warning(f"Hapus rencana {x['nama']}?")
        y, n, _ = st.columns([1, 1, 4])
        if y.button("Ya, hapus", type="primary", key=f"rcya_{x['id']}"):
            D["rencana"] = [r for r in D["rencana"] if r["id"] != x["id"]]
            selesai_simpan("Dihapus.", rc_hapus=None)
        n.button("Batal", key=f"rcbt_{x['id']}", on_click=atur, args=("rc_hapus", None))


def kartu_rencana_html(x: dict) -> str:
    """Kartu satu rencana beli: huruf awal, nama + prioritas, keterangan, jumlah besar di kanan."""
    pri = x.get("prioritas") if x.get("prioritas") in PRIORITAS else "Sedang"
    jml = int(x.get("jumlah", 1) or 1)
    harga = int(x.get("harga", 0) or 0)
    meta = []
    if harga:
        meta.append(f"{rp(harga)} per buah")
        if jml > 1:
            meta.append(f"total {rp(harga * jml)}")
    mt = f'<div class="mt">{html.escape(" • ".join(meta))}</div>' if meta else ""
    cat = f'<div class="cat">{html.escape(x["catatan"])}</div>' if x.get("catatan") else ""
    ic = html.escape((x["nama"].strip()[:1] or "?").upper())
    return (f'<div class="itm"><div class="ic">{ic}</div><div class="isi"><div class="jd">{html.escape(x["nama"])}'
            f'<span class="lencana {LC_PRIORITAS[pri]}">{pri}</span></div>{mt}{cat}</div>'
            f'<div class="qt"><b>{jml}</b><span>buah</span></div></div>')


def halaman_rencana():
    aktif = [x for x in D["rencana"] if not x.get("dibeli")]
    selesai = [x for x in D["rencana"] if x.get("dibeli")]
    mode = st.session_state.get("rc_mode")          # None (daftar), "baru", atau id rencana
    e = next((x for x in aktif if x["id"] == mode), {})
    if mode not in (None, "baru") and not e:
        mode = None
    with st.container(key="kartu_g_rencana"):
        if mode:
            st.markdown("#### Ubah rencana" if e else "#### Tambah rencana")
            with st.form(f"form_rc_{e.get('id', 'baru')}_{versi()}"):
                f1, f2 = st.columns([4, 1])
                nama = f1.text_input("Nama barang", value=e.get("nama", ""), placeholder="Contoh: Sepatu lari")
                jml = f2.number_input("Jumlah", min_value=1, value=int(e.get("jumlah", 1) or 1), step=1)
                g1, g2 = st.columns(2)
                harga = g1.number_input("Perkiraan harga per buah (Rp)", min_value=0, step=1000,
                                        value=int(e.get("harga", 0) or 0))
                pri = g2.selectbox("Prioritas", PRIORITAS, index=idx(PRIORITAS, e.get("prioritas", "Sedang")))
                catatan = st.text_input("Catatan atau tautan toko (boleh kosong)", value=e.get("catatan", ""))
                t1, t2, _ = st.columns([1, 1, 4])
                kirim = t1.form_submit_button("Simpan", type="primary")
                kembali = t2.form_submit_button("Kembali")
            if kembali:
                st.session_state.rc_mode = None
                st.rerun()
            if kirim:
                nama = nama.strip()
                if not nama:
                    st.error("Nama barang wajib diisi.")
                else:
                    isi = {"nama": nama, "jumlah": int(jml), "harga": int(harga), "prioritas": pri,
                           "catatan": catatan.strip()}
                    if e:
                        e.update(isi)
                    else:
                        D["rencana"].append({"id": uuid.uuid4().hex[:8], "dibuat": hari_ini().isoformat(), **isi})
                    selesai_simpan("Rencana disimpan.", rc_mode=None)
            return

        with st.container(key="baris_cari"):
            kc, kt = st.columns([5, 2], vertical_alignment="center")
            cari = " ".join(kc.text_input("Pencarian", key="rc_cari", icon=":material/search:",
                                          placeholder="Cari nama atau catatan...",
                                          label_visibility="collapsed").lower().split())
            kt.button("Tambah", type="primary", key="rc_tambah", icon=":material/add:",
                      use_container_width=True, on_click=atur, args=("rc_mode", "baru"))
        mode_tampil = st.segmented_control("Tampilan", ["Kartu", "Tabel"], default="Kartu",
                                           key="tampilan", label_visibility="collapsed") or "Kartu"
        urut = sorted(aktif, key=lambda x: (PRIORITAS.index(x["prioritas"]) if x.get("prioritas") in PRIORITAS
                                            else 1, x["nama"].lower()))
        if cari:
            urut = [x for x in urut if cari in " ".join([x["nama"], x.get("catatan", "")]).lower()]
        if not aktif:
            st.write("Belum ada rencana pembelian. Tekan Tambah untuk membuat yang pertama.")
        elif not urut:
            st.info("Tidak ada rencana yang cocok dengan pencarian.")
        else:
            st.caption(f"{len(urut)} dari {len(aktif)} rencana")
        total = sum(int(x.get("harga", 0) or 0) * int(x.get("jumlah", 1) or 1) for x in urut)

        if urut and mode_tampil == "Kartu":
            for x in urut:
                with st.container(key=f"item_r_{x['id']}"):
                    st.markdown(kartu_rencana_html(x), unsafe_allow_html=True)
                    e1, e2, e3, _ = st.columns([2, 1, 1, 1])
                    if e1.button("Sudah dibeli", key=f"kpakai_rc_{x['id']}", use_container_width=True):
                        x["dibeli"] = hari_ini().isoformat()
                        selesai_simpan("Dicoret dari rencana.")
                    e2.button("Edit", key=f"kedit_rc_{x['id']}", on_click=atur, args=("rc_mode", x["id"]),
                              use_container_width=True)
                    e3.button("Hapus", key=f"khapus_rc_{x['id']}", on_click=atur, args=("rc_hapus", x["id"]),
                              use_container_width=True)
                    _hapus_rencana(x)
        elif urut:
            lebar = [4.6, 1.2, 2.6, 3.6]
            kep = st.columns(lebar, vertical_alignment="top")
            for kol, judul in zip(kep, ["Barang", "Jml", "Perkiraan", "Aksi"]):
                kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
            for x in urut:
                st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                k = st.columns(lebar, vertical_alignment="center")
                pri = x.get("prioritas") if x.get("prioritas") in PRIORITAS else "Sedang"
                cat = f'<div class="sub">{html.escape(x["catatan"])}</div>' if x.get("catatan") else ""
                k[0].markdown(f'<div class="brg">{html.escape(x["nama"])}'
                              f'<span class="lencana {LC_PRIORITAS[pri]}">{pri}</span></div>{cat}',
                              unsafe_allow_html=True)
                k[1].write(int(x.get("jumlah", 1) or 1))
                est = int(x.get("harga", 0) or 0) * int(x.get("jumlah", 1) or 1)
                k[2].write(rp(est) if est else "—")
                a1, a2, a3 = k[3].columns([4, 1.2, 1.2])
                if a1.button("Sudah dibeli", key=f"rcbeli_{x['id']}"):
                    x["dibeli"] = hari_ini().isoformat()
                    selesai_simpan("Dicoret dari rencana.")
                a2.button("✏️", key=f"rcedit_{x['id']}", help="Ubah", on_click=atur, args=("rc_mode", x["id"]))
                a3.button("🗑️", key=f"rchapus_{x['id']}", help="Hapus", on_click=atur, args=("rc_hapus", x["id"]))
                _hapus_rencana(x)
        if urut:
            st.caption(f"Perkiraan total: {rp(total)}")
            teks = "\n".join(f"- {x['nama']} x{int(x.get('jumlah', 1) or 1)} ({x.get('prioritas', 'Sedang')})"
                             for x in urut)
            st.download_button("Unduh daftar rencana (.txt)", teks, file_name="rencana-beli.txt", mime="text/plain")
        with st.expander(f"Sudah dibeli ({len(selesai)})"):
            if not selesai:
                st.caption("Belum ada.")
            for x in sorted(selesai, key=lambda r: r.get("dibeli", ""), reverse=True):
                k = st.columns([4, 2.4, 1.2], vertical_alignment="center")
                k[0].write(x["nama"])
                k[1].write(fmt_iso(x.get("dibeli", "")))
                k[2].button("🗑️", key=f"rchapus2_{x['id']}", help="Hapus", on_click=atur, args=("rc_hapus", x["id"]))
                _hapus_rencana(x)


# -------------------------------------------------------------------- belanja
def halaman_belanja():
    """Satu menu belanja: stok yang menipis (otomatis) dan rencana barang baru."""
    t1, t2 = st.tabs(["Stok menipis", "Barang baru"])
    with t1:
        halaman_beli()
    with t2:
        halaman_rencana()


# -------------------------------------------------------------- daftar bawaan
def halaman_paket():
    by_id = {b["id"]: b for b in D["barang"]}
    if st.session_state.get("pk_baru"):
        st.session_state.pk_pilih = st.session_state.pop("pk_baru")
    with st.container(key="kartu_barang"):
        ids = [p["id"] for p in D["paket"]]
        nm = {p["id"]: p["nama"] for p in D["paket"]}
        if ids:
            if st.session_state.get("pk_pilih") not in ids:
                st.session_state.pk_pilih = ids[0]
            pid = st.selectbox("Daftar bawaan", ids, key="pk_pilih", format_func=lambda i: nm[i])
        else:
            pid = None
            st.info('Belum ada daftar bawaan. Buat dulu di bawah, misalnya "Liburan" atau "Pindah kos".')
        with st.expander("Buat daftar baru", expanded=not ids):
            with st.form(f"form_pk_baru_{versi()}"):
                nama_baru = st.text_input("Nama daftar", placeholder="Contoh: Pulang kampung")
                kirim = st.form_submit_button("Buat daftar")
            if kirim:
                nama_baru = nama_baru.strip()
                if not nama_baru:
                    st.error("Nama daftar wajib diisi.")
                elif ada_kembar([p["nama"] for p in D["paket"]] + [nama_baru]):
                    st.error("Nama itu sudah ada.")
                else:
                    baru = {"id": uuid.uuid4().hex[:8], "nama": nama_baru, "isi": []}
                    D["paket"].append(baru)
                    selesai_simpan("Daftar dibuat.", pk_baru=baru["id"])
        if not pid:
            return
        p = next(x for x in D["paket"] if x["id"] == pid)
        isi = p.setdefault("isi", [])
        slot = st.empty()
        t_siap, t_bawa, t_isi, t_atur = st.tabs(["Siapkan", "Bawa", "Isi daftar", "Atur"])

        with t_siap:
            if not isi:
                st.info('Daftar ini masih kosong. Buka tab "Isi daftar" untuk menambah barang.')
            else:
                st.caption("Centang barang yang sudah masuk tas, lalu tekan Simpan.")
            centang = {}
            for it in isi:
                kb = by_id.get(it.get("barang"))
                label = f"{it['nama']} ×{it.get('jumlah', 1)}" + (f" — {nama_tempat(kb)}" if kb else "")
                centang[it["id"]] = st.checkbox(label, value=bool(it.get("siap")), key=f"pkc_{it['id']}_{versi()}")
            if isi:
                siap = sum(1 for v in centang.values() if v)
                slot.progress(siap / len(isi), text=f"{siap} dari {len(isi)} sudah disiapkan")
                b1, b2 = st.columns(2)
                if b1.button("Simpan centang", type="primary", key="pk_simpan"):
                    for it in isi:
                        it["siap"] = bool(centang[it["id"]])
                    selesai_simpan("Centang disimpan.")
                if b2.button("Hapus semua centang", key="pk_reset"):
                    for it in isi:
                        it["siap"] = False
                    selesai_simpan("Semua centang dihapus.")

        with t_bawa:
            terkait = [by_id[i["barang"]] for i in isi if i.get("barang") in by_id and not by_id[i["barang"]].get("hilang")]
            if not terkait:
                st.info("Belum ada barang dari daftar barang di sini. Tambahkan lewat tab \"Isi daftar\".")
            else:
                sedang = [b for b in terkait if b.get("dibawa")]
                st.caption(f"{len(sedang)} dari {len(terkait)} barang sedang dibawa. "
                           "Barang akan ditandai \"Sedang dibawa\" di menu Dibawa, hilang, rusak.")
                ke = st.text_input("Dibawa ke mana? (boleh kosong)", value=p["nama"], key=f"pk_ke_{p['id']}_{versi()}")
                c1, c2 = st.columns(2)
                if c1.button("Bawa semua", type="primary", key="pk_bawa"):
                    for b in terkait:
                        if not b.get("dibawa"):
                            tandai_dibawa(b, ke.strip())
                    selesai_simpan(f"{len(terkait)} barang ditandai sedang dibawa.")
                if c2.button("Kembalikan semua", key="pk_balik", disabled=not sedang):
                    for b in sedang:
                        kembalikan_dibawa(b)
                    selesai_simpan("Semua barang di daftar ini sudah dikembalikan.")
                if len(terkait) < len(isi):
                    st.caption("Item yang diketik manual atau sedang hilang dilewati.")

        with t_isi:
            with st.form(f"form_pk_item_{p['id']}_{versi()}"):
                urut = [b["id"] for b in sorted(D["barang"], key=lambda x: x["nama"].lower())]
                pil = st.multiselect("Pilih dari daftar barang", urut,
                                     format_func=lambda i: f'{by_id[i]["nama"]} ({nama_tempat(by_id[i])})')
                manual = st.text_input("Atau ketik nama barang (boleh kosong)")
                jml = st.number_input("Jumlah (untuk barang yang diketik)", min_value=1, value=1, step=1)
                tambah = st.form_submit_button("Tambahkan", type="primary")
            if tambah:
                ada = {i.get("barang") for i in isi if i.get("barang")}
                n0 = len(isi)
                for bid in pil:
                    if bid not in ada:
                        isi.append({"id": uuid.uuid4().hex[:8], "nama": by_id[bid]["nama"], "barang": bid,
                                    "jumlah": 1, "siap": False})
                if manual.strip():
                    isi.append({"id": uuid.uuid4().hex[:8], "nama": manual.strip(), "barang": "",
                                "jumlah": int(jml), "siap": False})
                if len(isi) == n0:
                    st.error("Pilih barang atau ketik namanya dulu.")
                else:
                    selesai_simpan("Ditambahkan ke daftar.")
            if isi:
                st.markdown("**Hapus dari daftar**")
                with st.form(f"form_pk_hapus_{p['id']}_{versi()}"):
                    peta = {i["id"]: i["nama"] for i in isi}
                    hp = st.multiselect("Pilih yang dihapus", list(peta), format_func=lambda i: peta[i])
                    hapus = st.form_submit_button("Hapus terpilih")
                if hapus and hp:
                    p["isi"] = [i for i in isi if i["id"] not in hp]
                    selesai_simpan("Dihapus dari daftar.")

        with t_atur:
            if st.session_state.get("pk_hapus") == p["id"]:
                st.warning(f"Hapus daftar {p['nama']}?")
                y, n, _ = st.columns([1, 1, 3])
                if y.button("Ya, hapus", type="primary", key="pk_ya"):
                    D["paket"] = [x for x in D["paket"] if x["id"] != p["id"]]
                    selesai_simpan("Daftar dihapus.", pk_hapus=None)
                n.button("Batal", key="pk_bt", on_click=atur, args=("pk_hapus", None))
            else:
                st.caption("Menghapus daftar tidak menghapus barangnya.")
                st.button("Hapus daftar ini", key="pk_hp", on_click=atur, args=("pk_hapus", p["id"]))


# -------------------------------------------------------------- jarang dipakai
def halaman_jarang():
    if not D["barang"]:
        st.info("Belum ada barang.")
        return
    with st.container(key="kartu_barang"):
        batas = st.selectbox("Tampilkan barang yang tidak dipakai selama", [30, 60, 90, 180, 365], index=2,
                             key="jr_batas", format_func=lambda n: f"{n} hari atau lebih")
        hasil = []
        for b in D["barang"]:
            ref = iso_ke_date(b.get("dipakai")) or iso_ke_date(b.get("diubah"))
            if ref and (hari_ini() - ref).days >= batas:
                hasil.append(((hari_ini() - ref).days, b))
        st.caption("Tanggal dipakai dicatat lewat tombol Dipakai di Kelola barang. Barang yang belum pernah "
                   "dicatat dihitung sejak terakhir diubah.")
        if not hasil:
            st.info("Tidak ada barang yang cocok. Semua barang masih sering dipakai.")
            return
        lebar = [3.6, 3.4, 2.4, 1.6, 2.4]
        kep = st.columns(lebar, vertical_alignment="top")
        for kol, judul in zip(kep, ["Barang", "Disimpan di", "Terakhir dipakai", "Lama", "Aksi"]):
            kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
        for hari, b in sorted(hasil, key=lambda x: -x[0]):
            st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
            k = st.columns(lebar, vertical_alignment="center")
            k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}{lencana(b)}</div>', unsafe_allow_html=True)
            k[1].write(nama_tempat(b))
            k[2].write(fmt_iso(b["dipakai"]) if b.get("dipakai") else "Belum tercatat")
            k[3].write(f"{hari} hari")
            if k[4].button("Dipakai hari ini", key=f"jr_{b['id']}"):
                b["dipakai"] = hari_ini().isoformat()
                selesai_simpan("Dicatat dipakai hari ini.")


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


def _target_label(semua_barang: bool = False):
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
    for b in sorted(D["barang"], key=lambda x: x["nama"].lower()):
        if semua_barang or isi_dari(b["id"]):
            hasil.append({"kode": b["id"], "judul": b["nama"], "sub": "Barang · " + nama_lokasi(b), "q": f"barang={b['id']}"})
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
    targets = _target_label(bool(st.session_state.get("qr_semua_b")))
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
        st.checkbox("Sertakan juga barang yang tidak berisi barang lain", key="qr_semua_b",
                    help="Secara bawaan hanya barang yang berisi barang lain (misalnya Tas P3K) yang dibuatkan label.")
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
                foto_up, hapus_f = None, False
                if st.session_state.get("edit_sub") == x["id"]:
                    foto_up = st.file_uploader(f"Foto {x['nama']} (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                               key=f"fu_sub_{x['id']}")
                    if x.get("foto"):
                        hapus_f = st.checkbox("Hapus foto yang sekarang", key=f"fh_sub_{x['id']}")
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
                            galat, foto_lama = "", x.get("foto", "")
                            if foto_up is not None:
                                try:
                                    x["foto"] = simpan_foto(x["id"], foto_up.getvalue())
                                except Exception as e:
                                    galat = f"Foto gagal diunggah: {e}"
                            elif hapus_f:
                                x.pop("foto", None)
                            if galat:
                                st.error(galat)
                            else:
                                x["nama"] = baru
                                ganti = foto_lama if x.get("foto", "") != foto_lama else ""
                                selesai_simpan("Sub lokasi diubah.",
                                               sesudah=(lambda p=ganti: hapus_foto(p)) if ganti else None,
                                               edit_sub=None)
                elif st.session_state.get("hapus_sub") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("sublokasi") == x["id"])
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({n_b} barang jadi tanpa sub lokasi)" if n_b else ""))
                    c3.button("Batal", key=f"bh_sub_{x['id']}", on_click=atur, args=("hapus_sub", None))
                    if c2.button("Ya, hapus", key=f"yh_sub_{x['id']}", type="primary"):
                        foto_sub = x.get("foto", "")
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["id"] != x["id"]]
                        for b in D["barang"]:
                            if b.get("sublokasi") == x["id"]:
                                b.pop("sublokasi", None)
                        selesai_simpan("Dihapus.", sesudah=(lambda p=foto_sub: hapus_foto(p)) if foto_sub else None,
                                       hapus_sub=None)
                else:
                    c1.markdown(html_nama_foto(x), unsafe_allow_html=True)
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
                foto_up, hapus_f = None, False
                if st.session_state.get("edit_lokasi") == x["id"]:
                    foto_up = st.file_uploader(f"Foto {x['nama']} (boleh kosong)", type=["jpg", "jpeg", "png", "webp"],
                                               key=f"fu_lok_{x['id']}")
                    if x.get("foto"):
                        hapus_f = st.checkbox("Hapus foto yang sekarang", key=f"fh_lok_{x['id']}")
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
                            galat, foto_lama = "", x.get("foto", "")
                            if foto_up is not None:
                                try:
                                    x["foto"] = simpan_foto(x["id"], foto_up.getvalue())
                                except Exception as e:
                                    galat = f"Foto gagal diunggah: {e}"
                            elif hapus_f:
                                x.pop("foto", None)
                            if galat:
                                st.error(galat)
                            else:
                                x["nama"] = baru
                                if tbaru:
                                    x["tempat"] = tbaru
                                else:
                                    x.pop("tempat", None)
                                ganti = foto_lama if x.get("foto", "") != foto_lama else ""
                                selesai_simpan("Lokasi diubah.",
                                               sesudah=(lambda p=ganti: hapus_foto(p)) if ganti else None,
                                               edit_lokasi=None)
                elif st.session_state.get("hapus_lokasi") == x["id"]:
                    n_b = sum(1 for b in D["barang"] if b.get("lokasi") == x["id"])
                    n_s = sum(1 for s in D["sublokasi"] if s["lokasi"] == x["id"])
                    akibat = ", ".join(([f"{n_b} barang jadi tanpa lokasi"] if n_b else [])
                                       + ([f"{n_s} sub lokasi ikut terhapus"] if n_s else []))
                    c1.write(f"Hapus **{x['nama']}**?" + (f" ({akibat})" if akibat else ""))
                    c3.button("Batal", key=f"bh_lok_{x['id']}", on_click=atur, args=("hapus_lokasi", None))
                    if c2.button("Ya, hapus", key=f"yh_lok_{x['id']}", type="primary"):
                        fs = [x.get("foto", "")] + [s.get("foto", "") for s in D["sublokasi"] if s["lokasi"] == x["id"]]
                        D["lokasi"] = [y for y in D["lokasi"] if y["id"] != x["id"]]
                        D["sublokasi"] = [y for y in D["sublokasi"] if y["lokasi"] != x["id"]]
                        selesai_simpan("Dihapus.", sesudah=lambda fs=fs: [hapus_foto(p) for p in fs if p],
                                       hapus_lokasi=None)
                else:
                    c1.markdown(html_nama_foto(x), unsafe_allow_html=True)
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


def semua_barang_pemilik() -> list:
    """Barang aktif dan barang di tempat sampah, supaya nama pemilik ikut berubah di keduanya."""
    return D["barang"] + [x["barang"] for x in D["sampah"]]


def halaman_kelola_label():
    """Daftar label diambil dari barang. Di sini label bisa diubah nama, digabung, atau dilepas dari barangnya."""
    nama_nama = daftar_tag()
    with st.expander(f"Label barang ({len(nama_nama)})", expanded=True):
        st.caption("Label muncul otomatis dari barang yang diberi label. Mengubah nama ikut mengganti semua barangnya. "
                   "Kalau namanya sama dengan label lain, keduanya digabung. Menghapus label tidak menghapus barangnya.")
        if not nama_nama:
            st.write("Belum ada label. Tambahkan lewat Kelola barang atau aksi massal Tambah label.")
        for nm in nama_nama:
            n_b = sum(1 for b in D["barang"] if nm in b.get("tag", []))
            kunci = hashlib.md5(nm.encode("utf-8")).hexdigest()[:10]
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get("edit_tag") == nm:
                baru = c1.text_input("Nama", value=nm, key=f"nm_tag_{kunci}", label_visibility="collapsed", max_chars=30)
                c3.button("Batal", key=f"bt_tag_{kunci}", on_click=atur, args=("edit_tag", None))
                if c2.button("Simpan", key=f"sv_tag_{kunci}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif baru == nm:
                        st.session_state.edit_tag = None
                        st.rerun()
                    else:
                        lain = next((x for x in nama_nama if x != nm and x.lower() == baru.lower()), None)
                        akhir = lain or baru
                        for b in semua_barang_pemilik():
                            if nm in b.get("tag", []):
                                b["tag"] = list(dict.fromkeys(akhir if t == nm else t for t in b["tag"]))[:8]
                        selesai_simpan(f"Digabung ke {akhir}." if lain else "Nama label diubah.", edit_tag=None)
            elif st.session_state.get("hapus_tag") == nm:
                c1.write(f"Hapus label **{nm}**?" + (f" ({n_b} barang kehilangan label ini)" if n_b else ""))
                c3.button("Batal", key=f"bh_tag_{kunci}", on_click=atur, args=("hapus_tag", None))
                if c2.button("Ya, hapus", key=f"yh_tag_{kunci}", type="primary"):
                    for b in semua_barang_pemilik():
                        if nm in b.get("tag", []):
                            sisa = [t for t in b["tag"] if t != nm]
                            if sisa:
                                b["tag"] = sisa
                            else:
                                b.pop("tag", None)
                    selesai_simpan("Label dihapus.", hapus_tag=None)
            else:
                c1.write(f"{nm} · {n_b} barang")
                c2.button("Ubah nama", key=f"ub_tag_{kunci}", on_click=atur, args=("edit_tag", nm))
                c3.button("Hapus", key=f"hp_tag_{kunci}", on_click=atur, args=("hapus_tag", nm))


def halaman_pemilik():
    """Daftar pemilik diambil dari barang. Di sini nama bisa diubah, digabung, atau dilepas dari barangnya."""
    nama_nama = daftar_pemilik()
    with st.expander(f"Pemilik ({len(nama_nama)})", expanded=True):
        st.caption("Pemilik muncul otomatis dari barang yang diisi pemiliknya. Mengubah nama ikut mengganti semua barangnya. "
                   "Kalau namanya sama dengan pemilik lain, keduanya digabung. Menghapus pemilik tidak menghapus barangnya.")
        if not nama_nama:
            st.write("Belum ada pemilik. Isi pemilik lewat Kelola barang.")
        for nm in nama_nama:
            n_b = sum(1 for b in D["barang"] if b.get("pemilik") == nm)
            kunci = hashlib.md5(nm.encode("utf-8")).hexdigest()[:10]
            c1, c2, c3 = st.columns([5, 1.8, 1.6], vertical_alignment="center")
            if st.session_state.get("edit_pemilik") == nm:
                baru = c1.text_input("Nama", value=nm, key=f"nm_pem_{kunci}", label_visibility="collapsed", max_chars=40)
                c3.button("Batal", key=f"bt_pem_{kunci}", on_click=atur, args=("edit_pemilik", None))
                if c2.button("Simpan", key=f"sv_pem_{kunci}", type="primary"):
                    baru = baru.strip()
                    if not baru:
                        st.error("Nama tidak boleh kosong.")
                    elif baru == nm:
                        st.session_state.edit_pemilik = None
                        st.rerun()
                    else:
                        lain = next((x for x in nama_nama if x != nm and x.lower() == baru.lower()), None)
                        akhir = lain or baru          # kalau sudah ada pemilik serupa, pakai ejaan yang sudah ada
                        for b in semua_barang_pemilik():
                            if b.get("pemilik") == nm:
                                b["pemilik"] = akhir
                        selesai_simpan(f"Digabung ke {akhir}." if lain else "Nama pemilik diubah.", edit_pemilik=None)
            elif st.session_state.get("hapus_pemilik") == nm:
                c1.write(f"Hapus pemilik **{nm}**?" + (f" ({n_b} barang jadi tanpa pemilik)" if n_b else ""))
                c3.button("Batal", key=f"bh_pem_{kunci}", on_click=atur, args=("hapus_pemilik", None))
                if c2.button("Ya, hapus", key=f"yh_pem_{kunci}", type="primary"):
                    for b in semua_barang_pemilik():
                        if b.get("pemilik") == nm:
                            b.pop("pemilik", None)
                    selesai_simpan("Pemilik dihapus.", hapus_pemilik=None)
            else:
                c1.write(f"{nm} · {n_b} barang")
                c2.button("Ubah nama", key=f"ub_pem_{kunci}", on_click=atur, args=("edit_pemilik", nm))
                c3.button("Hapus", key=f"hp_pem_{kunci}", on_click=atur, args=("hapus_pemilik", nm))


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


# ------------------------------------------------------------ tampilan Beranda (Pengaturan)
def simpan_bersama(kunci: str, daftar: list):
    D.setdefault("pengaturan", {})[kunci] = list(daftar)
    selesai_simpan("Disimpan sebagai bawaan untuk semua perangkat.")


def tombol_bersama(kunci: str, daftar: list, pakai):
    """Dua tombol: simpan pilihan perangkat ini sebagai bawaan bersama, atau ambil bawaan bersama ke perangkat ini."""
    st.markdown("**Semua perangkat**")
    st.caption("Pilihan di atas hanya berlaku di perangkat ini. Simpan sebagai bawaan bersama supaya perangkat lain "
               "(atau HP baru, atau setelah cookie terhapus) ikut memakainya.")
    ada = kunci in D.get("pengaturan", {})
    c1, c2 = st.columns(2)
    if c1.button("Simpan untuk semua perangkat", key=f"bersama_{kunci}", type="primary", use_container_width=True):
        simpan_bersama(kunci, daftar)
    c2.button("Pakai bawaan bersama", key=f"ambil_{kunci}", use_container_width=True, disabled=not ada,
              on_click=pakai, args=(list(D.get("pengaturan", {}).get(kunci, [])),),
              help=None if ada else "Belum ada bawaan bersama yang disimpan.")


def halaman_tampilan():
    muat_beranda_sembunyi()
    sembunyi = set(st.session_state.beranda_sembunyi)
    with st.container(key="kartu_barang"):
        st.markdown("**Kartu yang tampil di Beranda**")
        st.caption("Centang kartu yang ingin ditampilkan. Pilihan ini berlaku di perangkat ini.")
        for k, lab in SEKSI_BERANDA:
            st.checkbox(lab, value=k not in sembunyi, key=f"bs_{k}", on_change=ubah_beranda)
        c1, c2, c3 = st.columns(3)
        c1.button("Tampilkan semua", key="bs_semua", on_click=atur_beranda, args=([],), use_container_width=True)
        c2.button("Hanya ringkasan", key="bs_min", on_click=atur_beranda,
                  args=([k for k, _ in SEKSI_BERANDA if k != "ringkasan"],), use_container_width=True)
        c3.button("Lihat Beranda", key="bs_lihat", on_click=pindah_halaman, args=("Beranda",),
                  type="primary", use_container_width=True)
        tombol_bersama("beranda", st.session_state.beranda_sembunyi, atur_beranda)
    if st.session_state.pop("beranda_ubah", False):
        js_cookie(",".join(st.session_state.beranda_sembunyi) or "-", 31536000, COOKIE_BERANDA)


def halaman_tampilan_kartu():
    sembunyi = muat_kartu_sembunyi()
    with st.container(key="kartu_g_tkartu"):
        st.markdown("**Keterangan yang tampil di kartu barang**")
        st.caption("Centang keterangan yang ingin ditampilkan di kartu barang (Cari barang, Kelola barang, dan menu lain). "
                   "Nama, foto, dan lencana status tetap tampil. Pilihan ini berlaku di perangkat ini.")
        for k, lab in SEKSI_KARTU:
            st.checkbox(lab, value=k not in sembunyi, key=f"ks_{k}", on_change=ubah_kartu)
        c1, c2, c3 = st.columns(3)
        c1.button("Tampilkan semua", key="ks_semua", on_click=atur_kartu, args=([],), use_container_width=True)
        c2.button("Lokasi dan harga saja", key="ks_lh", on_click=atur_kartu,
                  args=([k for k, _ in SEKSI_KARTU if k not in ("lokasi", "harga", "jumlah")],), use_container_width=True)
        c3.button("Hanya lokasi", key="ks_l", on_click=atur_kartu,
                  args=([k for k, _ in SEKSI_KARTU if k != "lokasi"],), use_container_width=True)
        tombol_bersama("kartu", st.session_state.kartu_sembunyi, atur_kartu)
        st.markdown("**Contoh tampilan**")
        if not D["barang"]:
            st.caption("Belum ada barang untuk dijadikan contoh.")
        else:
            def lengkap(b):
                return sum(1 for k in ("kategori", "harga", "catatan", "tautan", "tag", "pemilik", "merek", "dibeli", "dalam") if b.get(k))
            contoh = max(D["barang"], key=lengkap)
            with st.container(key="item_contoh"):
                st.markdown(kartu_barang_html(contoh), unsafe_allow_html=True)
    if st.session_state.pop("kartu_ubah", False):
        js_cookie(",".join(st.session_state.kartu_sembunyi) or "-", 31536000, COOKIE_KARTU)


# ------------------------------------------------------------ pengingat berkala
def halaman_pengingat():
    t1, t2 = st.tabs(["Jadwal", "Atur pengingat"])
    with t1:
        with st.container(key="kartu_tgl_cek"):
            jd = jadwal_cek()
            if not jd:
                st.info('Belum ada barang yang diberi pengingat. Buka tab "Atur pengingat".')
            else:
                f = st.selectbox("Tampilkan", ["Semua", "Sudah waktunya (7 hari ke depan)"], key="pb_f")
                if f != "Semua":
                    jd = [x for x in jd if x[0] <= 7]
                if not jd:
                    st.caption("Tidak ada barang yang perlu dicek dalam 7 hari ke depan.")
                else:
                    lebar = [3.4, 3.2, 2.2, 2.6, 2.2]
                    kep = st.columns(lebar, vertical_alignment="top")
                    for kol, judul in zip(kep, ["Barang", "Disimpan di", "Terakhir dicek", "Berikutnya", "Aksi"]):
                        kol.markdown(f'<div class="thead-s">{judul}</div>', unsafe_allow_html=True)
                    for s, b in jd:
                        st.markdown('<div class="garis"></div>', unsafe_allow_html=True)
                        k = st.columns(lebar, vertical_alignment="center")
                        k[0].markdown(f'<div class="brg">{html.escape(b["nama"])}</div>', unsafe_allow_html=True)
                        k[1].write(nama_tempat(b))
                        k[2].write(fmt_iso(b["cek_terakhir"]) if b.get("cek_terakhir") else "Belum pernah")
                        k[3].markdown(f'{status_sisa(s)}<div class="sub">{teks_cek(b["cek_tiap"])}</div>',
                                      unsafe_allow_html=True)
                        if k[4].button("Sudah dicek", key=f"pb_{b['id']}"):
                            b["cek_terakhir"] = hari_ini().isoformat()
                            selesai_simpan(f"{b['nama']} dicatat sudah dicek.")
    with t2:
        with st.container(key="kartu_barang"):
            if not D["barang"]:
                st.info("Belum ada barang.")
                return
            st.caption("Cocok untuk barang yang perlu dicek rutin: baterai cadangan, alat P3K, tabung pemadam, "
                       "filter air, atau obat yang mendekati kedaluwarsa.")
            urut = sorted(D["barang"], key=lambda x: x["nama"].lower())
            with st.form(f"form_pb_{versi()}"):
                pil = st.multiselect("Barang", [b["id"] for b in urut],
                                     format_func=lambda i: next(x["nama"] for x in urut if x["id"] == i))
                n = st.selectbox("Seberapa sering dicek", CEK_OPSI[1:], index=2, format_func=teks_cek)
                ok = st.form_submit_button("Pasang pengingat", type="primary")
            if ok:
                if not pil:
                    st.error("Pilih minimal satu barang.")
                else:
                    peta = {b["id"]: b for b in D["barang"]}
                    for i in pil:
                        peta[i]["cek_tiap"] = int(n)
                        if not peta[i].get("cek_terakhir"):
                            peta[i]["cek_terakhir"] = hari_ini().isoformat()
                    selesai_simpan(f"Pengingat dipasang untuk {len(pil)} barang.")
            ada = [b for _, b in jadwal_cek()]
            if ada:
                st.markdown("**Hentikan pengingat**")
                with st.form(f"form_pb_stop_{versi()}"):
                    stop = st.multiselect("Barang", [b["id"] for b in ada], key="pb_stop",
                                          format_func=lambda i: next(x["nama"] for x in ada if x["id"] == i))
                    oks = st.form_submit_button("Hentikan")
                if oks and stop:
                    for b in ada:
                        if b["id"] in stop:
                            b.pop("cek_tiap", None)
                            b.pop("cek_terakhir", None)
                    selesai_simpan("Pengingat dihentikan.")


# ------------------------------------------------------------ scan barcode
@st.cache_data(show_spinner=False, max_entries=8)
def baca_barcode(data: bytes):
    """Daftar kode yang terbaca dari foto. None kalau pustaka pembaca belum terpasang."""
    try:
        import cv2
        import numpy as np
    except Exception:
        return None
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    sisi = max(img.shape[:2])
    if sisi > 1600:
        img = cv2.resize(img, None, fx=1600 / sisi, fy=1600 / sisi, interpolation=cv2.INTER_AREA)
    kelas = getattr(cv2, "barcode_BarcodeDetector", None) or getattr(getattr(cv2, "barcode", None), "BarcodeDetector", None)
    bd = kelas() if kelas else None

    def kumpul(res, ke):
        for x in res:
            if isinstance(x, str) and x.strip():
                ke.append(x.strip())
            elif isinstance(x, (tuple, list)):
                for y in x:
                    if isinstance(y, str) and y.strip():
                        ke.append(y.strip())

    for putar in (None, cv2.ROTATE_90_CLOCKWISE):
        dasar = img if putar is None else cv2.rotate(img, putar)
        for skala in (1.0, 0.75, 0.5, 0.35, 0.25, 1.5, 2.0):
            im = cv2.resize(dasar, None, fx=skala, fy=skala,
                            interpolation=cv2.INTER_AREA if skala < 1 else cv2.INTER_CUBIC)
            if min(im.shape[:2]) < 60:
                continue
            ketemu = []
            try:
                if bd is not None:
                    kumpul(bd.detectAndDecode(im), ketemu)
                if not ketemu:
                    kumpul(cv2.QRCodeDetector().detectAndDecode(im), ketemu)
            except Exception:
                continue
            if ketemu:
                return list(dict.fromkeys(ketemu))
    return []


@st.cache_data(ttl=86400, show_spinner=False)
def cari_produk(kode: str) -> dict:
    """Nama produk dari basis data terbuka. Melempar galat kalau tidak ada yang bisa dihubungi."""
    galat = False
    for host in ("world.openfoodfacts.org", "world.openbeautyfacts.org", "world.openproductsfacts.org"):
        try:
            r = requests.get(f"https://{host}/api/v2/product/{kode}.json",
                             params={"fields": "product_name,brands,quantity"},
                             headers={"User-Agent": "PelacakBarang/1.0 (pribadi)"}, timeout=6)
            if r.status_code != 200:
                continue
            j = r.json()
            p = j.get("product", {}) if j.get("status") == 1 else {}
            nama = (p.get("product_name") or "").strip()
            if nama:
                return {"nama": nama, "merek": (p.get("brands") or "").split(",")[0].strip(),
                        "ukuran": (p.get("quantity") or "").strip()}
        except Exception:
            galat = True
    if galat:
        raise RuntimeError("tidak terhubung")
    return {}


def form_scan_baru(kode: str, n: int):
    if not D["lokasi"]:
        st.info("Buat lokasi dulu di Pengaturan > Lokasi sebelum menambah barang.")
        return
    info = {}
    try:
        info = cari_produk(kode)
        if info:
            st.caption("Nama dan merek diambil dari basis data produk terbuka (Open Food Facts). Periksa dulu, ubah kalau perlu.")
        else:
            st.caption("Kode ini belum ada di basis data produk, jadi isi namanya sendiri.")
    except Exception:
        st.caption("Basis data produk tidak bisa dihubungi sekarang, jadi isi namanya sendiri.")
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    if st.session_state.get("cepat_lok") not in pl:
        st.session_state.cepat_lok = next(iter(pl))
    lok = st.selectbox("Disimpan di", list(pl), key="cepat_lok", format_func=lambda i: pl[i])
    with st.form(f"form_scan_{kode}_{versi()}"):
        nama = st.text_input("Nama barang", value=info.get("nama", ""))
        a1, a2 = st.columns(2)
        merek = a1.text_input("Merek", value=info.get("merek", ""))
        ukuran = a2.text_input("Ukuran", value=info.get("ukuran", ""))
        jumlah = st.number_input("Jumlah", min_value=0, value=1, step=1)
        kat = ""
        if D["kategori"]:
            pk = {k["id"]: k["nama"] for k in D["kategori"]}
            ops_k = [""] + list(pk)
            kat = st.selectbox("Kategori (boleh kosong)", ops_k, format_func=lambda i: TANPA_KAT if not i else pk[i])
        kirim = st.form_submit_button("Simpan barang", type="primary")
    if kirim:
        nama = nama.strip()
        if not nama:
            st.error("Nama barang wajib diisi.")
            return
        if peringatan_serupa(nama):
            return
        b = {"id": uuid.uuid4().hex[:8], "nama": nama, "lokasi": lok, "jumlah": int(jumlah), "barcode": kode,
             "diubah": hari_ini().isoformat()}
        for kunci, v in (("merek", merek), ("ukuran", ukuran), ("kategori", kat)):
            if v and v.strip():
                b[kunci] = v.strip()
        catat(b["id"], nama, "", nama_tempat(b))
        D["barang"].append(b)
        selesai_simpan(f"{nama} ditambahkan.", sc_n=n + 1)


def halaman_scan():
    n = st.session_state.get("sc_n", 0)
    kode, galat = "", ""
    with st.container(key="kartu_barang"):
        st.caption("Foto barcode di kemasan barang. Kalau barangnya sudah pernah dicatat, langsung muncul. "
                   "Kalau belum, kamu bisa menambahkannya dan namanya dicari otomatis.")
        cara = st.segmented_control("Cara", ["Kamera", "Unggah foto", "Ketik kode"], default="Kamera",
                                    key="sc_cara", label_visibility="collapsed") or "Kamera"
        foto = None
        if cara == "Kamera":
            foto = st.camera_input("Arahkan kamera ke barcode, dekat dan terang", key=f"sc_cam_{n}")
        elif cara == "Unggah foto":
            foto = st.file_uploader("Foto barcode", type=["jpg", "jpeg", "png", "webp"], key=f"sc_up_{n}")
        else:
            with st.form(f"form_sc_ketik_{n}"):
                ketik = st.text_input("Kode barcode", placeholder="Contoh: 8991234567890")
                st.form_submit_button("Cari kode", type="primary")
            kode = re.sub(r"\s+", "", ketik or "")
        if foto is not None:
            hasil = baca_barcode(foto.getvalue())
            if hasil is None:
                galat = "Pembaca barcode belum terpasang. Tambahkan opencv-python-headless ke requirements.txt, atau ketik kodenya."
            elif not hasil:
                galat = "Barcode belum terbaca. Dekatkan, pastikan terang dan tegak lurus, atau ketik kodenya."
            elif len(hasil) == 1:
                kode = hasil[0]
            else:
                kode = st.selectbox("Beberapa kode terbaca, pilih satu", hasil, key=f"sc_pilih_{n}")
        if galat:
            st.warning(galat)
    if not kode:
        return
    if not re.fullmatch(r"[A-Za-z0-9\-\.\/\+ ]{3,40}", kode):
        st.warning("Kode ini tidak terlihat seperti barcode barang.")
        return
    with st.container(key="kartu_tgl_scan"):
        st.markdown(f"**Kode terbaca:** `{kode}`")
        ada = [b for b in D["barang"] if b.get("barcode") == kode]
        if ada:
            st.success(f"Ditemukan {len(ada)} barang dengan kode ini.")
            for b in ada:
                st.markdown(kartu_barang_html(b), unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("Dipakai hari ini", key=f"sc_pakai_{b['id']}"):
                    b["dipakai"] = hari_ini().isoformat()
                    selesai_simpan("Dicatat dipakai hari ini.", sc_n=n + 1)
                if cek_tiap_b(b) and c2.button("Sudah dicek", key=f"sc_cek_{b['id']}"):
                    b["cek_terakhir"] = hari_ini().isoformat()
                    selesai_simpan("Dicatat sudah dicek.", sc_n=n + 1)
            with st.expander("Tambah barang lain dengan kode ini"):
                form_scan_baru(kode, n)
        else:
            st.info("Belum ada barang dengan kode ini.")
            form_scan_baru(kode, n)
            polos = sorted([b for b in D["barang"] if not b.get("barcode")], key=lambda x: x["nama"].lower())
            if polos:
                with st.expander("Atau pasang kode ini ke barang yang sudah ada"):
                    pid = st.selectbox("Barang", [b["id"] for b in polos], key=f"sc_pasang_{n}",
                                       format_func=lambda i: next(x["nama"] for x in polos if x["id"] == i))
                    if st.button("Pasang kode", key=f"sc_pasang_go_{n}"):
                        next(x for x in polos if x["id"] == pid)["barcode"] = kode
                        selesai_simpan("Kode dipasang.", sc_n=n + 1)


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
    "harga": ("Harga beli", lambda b: harga_b(b) or "", 2.4, True),
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
        angka = nm in ("Jumlah", "Harga beli")
        lebar = max([len(str(nm))] + [len(str(ws.cell(r, i).value or "")) for r in range(2, ws.max_row + 1)])
        ws.column_dimensions[get_column_letter(i)].width = max(9, min(lebar + 3, 46 if nm != "Catatan" else 56))
        for r in range(2, ws.max_row + 1):
            c = ws.cell(r, i)
            c.border = garis
            c.alignment = Alignment(vertical="top", wrap_text=True, horizontal="right" if angka else "left")
            if nm == "Harga beli" and c.value != "":
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
        rs["A6"], rs["B6"] = "Total nilai (harga beli)", nilai
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
            if k == "harga" and v != "":
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


# ------------------------------------------------------------ inventaris ulang (opname)
def set_opname(ids: list, nilai: bool):
    for i in ids:
        st.session_state[f"op_ada_{i}_{versi()}"] = nilai


def terapkan_opname(r: dict):
    by = {b["id"]: b for b in D["barang"]}
    hari = hari_ini().isoformat()
    ketemu = 0
    for i, n in r["ada"]:
        b = by.get(i)
        if not b:
            continue
        if b.get("hilang"):
            tandai_ketemu(b)
            ketemu += 1
        if n != jumlah_b(b):
            b["jumlah"] = n
        b["opname"] = hari
        b["diubah"] = hari
    hilang = 0
    if r["aksi"] == "Tandai hilang":
        for i in r["tidak"]:
            b = by.get(i)
            if b and not b.get("hilang"):
                tandai_hilang(b, nama_tempat(b))
                hilang += 1
    bagian = [f"{len(r['ada'])} barang dicocokkan"]
    if ketemu:
        bagian.append(f"{ketemu} ketemu kembali")
    if hilang:
        bagian.append(f"{hilang} ditandai hilang")
    selesai_simpan("Inventaris ulang selesai: " + ", ".join(bagian) + ".", op_rencana=None)


def halaman_opname():
    if not D["lokasi"] or not D["barang"]:
        st.info("Buat lokasi dan barang dulu sebelum melakukan inventaris ulang.")
        return
    pl = {l["id"]: nama_lok(l) for l in daftar_lokasi()}
    with st.container(key="kartu_barang"):
        st.caption("Cocokkan catatan dengan keadaan sebenarnya. Pilih satu lokasi, centang barang yang benar-benar "
                   "ada di sana, dan koreksi jumlahnya kalau berbeda. Barang yang sedang dibawa tidak ikut diperiksa.")
        if st.session_state.get("op_lok") not in pl:
            st.session_state.op_lok = next(iter(pl))
        sl = st.selectbox("Lokasi yang diperiksa", list(pl), key="op_lok", format_func=lambda i: pl[i])
        ssub = {s["id"]: s["nama"] for s in D["sublokasi"] if s["lokasi"] == sl}
        ops_s = ["semua", "langsung"] + list(ssub)
        if st.session_state.get("op_sub") not in ops_s:
            st.session_state.op_sub = "semua"
        ss = st.selectbox("Bagian lokasi", ops_s, key="op_sub",
                          format_func=lambda i: "Seluruh lokasi" if i == "semua"
                          else "Hanya yang langsung di lokasi (tanpa sub lokasi)" if i == "langsung" else ssub[i])
        milik = [b for b in sorted(D["barang"], key=lambda x: x["nama"].lower()) if b.get("lokasi") == sl
                 and (ss == "semua" or (ss == "langsung" and sub_dari(b) is None) or b.get("sublokasi") == ss)]
        items = [b for b in milik if not b.get("dibawa")]
        n_bawa = len(milik) - len(items)
        if not items:
            st.info("Tidak ada barang yang perlu diperiksa di bagian ini."
                    + (f" ({n_bawa} barang sedang dibawa.)" if n_bawa else ""))
            return
        st.caption(f"{len(items)} barang untuk diperiksa" + (f", {n_bawa} sedang dibawa dilewati." if n_bawa else "."))
        terakhir = [b["opname"] for b in items if b.get("opname")]
        st.caption(("Pemeriksaan terakhir: " + fmt_iso(max(terakhir))) if terakhir else "Belum pernah diinventarisasi.")
        ids = [b["id"] for b in items]
        c1, c2 = st.columns(2)
        c1.button("Centang semua", key="op_semua", use_container_width=True, on_click=set_opname, args=(ids, True))
        c2.button("Kosongkan", key="op_kosong", use_container_width=True, on_click=set_opname, args=(ids, False))
        aksi = st.radio("Barang yang tidak dicentang", ["Tandai hilang", "Biarkan saja"], key="op_aksi",
                        horizontal=True, help="Tandai hilang memasukkannya ke menu Dibawa, hilang, rusak. "
                                              "Bisa dibatalkan lewat Riwayat (tab Aktivitas).")
        with st.form(f"form_op_{versi()}"):
            for b in items:
                k1, k2 = st.columns([4, 1.5], vertical_alignment="center")
                info = f"tercatat {jumlah_b(b)}" + (f" · terakhir diperiksa {fmt_iso(b['opname'])}" if b.get("opname") else "")
                if b.get("hilang"):
                    info += " · sebelumnya hilang"
                k1.checkbox(f"{b['nama']} ({info})", key=f"op_ada_{b['id']}_{versi()}")
                k2.number_input("Jumlah ditemukan", min_value=0, value=jumlah_b(b), step=1,
                                key=f"op_jml_{b['id']}_{versi()}", label_visibility="collapsed")
            kirim = st.form_submit_button("Lihat ringkasan", type="primary")
        sig = (sl, ss)
        if kirim:
            ada = [(b["id"], int(st.session_state.get(f"op_jml_{b['id']}_{versi()}", jumlah_b(b))))
                   for b in items if st.session_state.get(f"op_ada_{b['id']}_{versi()}")]
            if not ada and aksi == "Tandai hilang":
                st.session_state.pop("op_rencana", None)
                st.error("Belum ada barang yang dicentang. Centang yang ada, atau ubah pilihan ke Biarkan saja.")
            else:
                dicek = {i for i, _ in ada}
                st.session_state.op_rencana = {"sig": sig, "ada": ada, "aksi": aksi,
                                               "tidak": [b["id"] for b in items if b["id"] not in dicek and not b.get("hilang")]}
        r = st.session_state.get("op_rencana")
        if r and r.get("sig") != sig:
            st.session_state.pop("op_rencana", None)
            r = None
        if r:
            by = {b["id"]: b for b in D["barang"]}
            selisih = [(by[i], n) for i, n in r["ada"] if i in by and n != jumlah_b(by[i])]
            ketemu = [by[i] for i, _ in r["ada"] if i in by and by[i].get("hilang")]
            tidak = [by[i] for i in r["tidak"] if i in by]
            st.markdown("**Ringkasan**")
            st.markdown(f'<div class="perhatian"><div class="brg">Ditemukan</div><div class="sub">{len(r["ada"])} barang</div></div>',
                        unsafe_allow_html=True)
            if selisih:
                st.markdown('<div class="perhatian"><div class="brg">Jumlah dikoreksi</div><div class="sub">'
                            + "<br>".join(html.escape(f"{b['nama']}: {jumlah_b(b)} → {n}") for b, n in selisih[:10])
                            + (f"<br>…dan {len(selisih) - 10} lainnya" if len(selisih) > 10 else "") + "</div></div>",
                            unsafe_allow_html=True)
            if ketemu:
                st.markdown('<div class="perhatian"><div class="brg">Ketemu kembali</div><div class="sub">'
                            + html.escape(", ".join(b["nama"] for b in ketemu[:10])) + "</div></div>", unsafe_allow_html=True)
            if tidak:
                akibat = "akan ditandai hilang" if r["aksi"] == "Tandai hilang" else "dibiarkan"
                st.markdown(f'<div class="perhatian"><div class="brg">Tidak ditemukan ({akibat})</div><div class="sub">'
                            + html.escape(", ".join(b["nama"] for b in tidak[:10]))
                            + (f" dan {len(tidak) - 10} lainnya" if len(tidak) > 10 else "") + "</div></div>",
                            unsafe_allow_html=True)
            y, n_, _ = st.columns([1.4, 1, 1.4])
            if y.button("Terapkan", type="primary", key="op_ya"):
                terapkan_opname(r)
            n_.button("Batal", key="op_batal", on_click=atur, args=("op_rencana", None))


# ------------------------------------------------------------------ statistik
def _baris_stat(judul: str, ket: str) -> str:
    return (f'<div class="perhatian"><div class="brg">{html.escape(judul)}</div>'
            f'<div class="sub">{ket}</div></div>')


def halaman_statistik():
    brg = D["barang"]
    if not brg:
        st.info("Belum ada barang, jadi belum ada yang bisa dihitung.")
        return
    pindah = [x for x in D["riwayat"] if x.get("dari")]
    with st.container(key="kartu_g_s2"):
        st.markdown("**Barang yang paling sering pindah**")
        hitung = {}
        for x in pindah:
            kunci = x.get("barang") or x.get("nama", "")
            hitung[kunci] = hitung.get(kunci, [0, x.get("nama", "")])
            hitung[kunci][0] += 1
        st.caption(f"{len(pindah)} perpindahan tercatat" if pindah else "Belum ada barang yang pernah dipindah.")
        by = {b["id"]: b for b in brg}
        for kunci, (n, nama) in sorted(hitung.items(), key=lambda kv: -kv[1][0])[:8]:
            b = by.get(kunci)
            st.markdown(_baris_stat(b["nama"] if b else nama,
                                    f"{n} kali pindah" + (f" · sekarang di {html.escape(nama_tempat(b))}" if b else " · sudah dihapus")),
                        unsafe_allow_html=True)

    with st.container(key="kartu_g_s3"):
        st.markdown("**Jumlah buah per lokasi**")
        per = {}
        for b in brg:
            p = per.setdefault(nama_lokasi(b), [0, 0])
            p[0] += 1
            p[1] += jumlah_b(b)
        top = sorted(per.items(), key=lambda kv: -kv[1][1])[:10]
        st.bar_chart(pd.DataFrame({"Lokasi": [k for k, _ in top], "Jumlah buah": [v[1] for _, v in top]}),
                     x="Lokasi", y="Jumlah buah", horizontal=True, sort="-Jumlah buah", color="#2b7a57",
                     height=max(160, 38 * len(top)))
        st.caption(f"Total {sum(v[1] for v in per.values())} buah di {len(per)} lokasi. "
                   "Jumlah jenis barang per lokasi ada di grafik Beranda.")

    with st.container(key="kartu_g_s5"):
        st.markdown("**Aktivitas 6 bulan terakhir**")
        h = hari_ini()
        bulan = []
        for i in range(5, -1, -1):
            y, m = h.year, h.month - i
            while m <= 0:
                y, m = y - 1, m + 12
            bulan.append(f"{y}-{m:02d}")
        cacah = {b: 0 for b in bulan}
        orang = {}
        for x in D["aktivitas"]:
            if x.get("waktu", "")[:7] in cacah:
                cacah[x["waktu"][:7]] += 1
            orang[x.get("oleh", "")] = orang.get(x.get("oleh", ""), 0) + 1
        st.caption(f"{len(D['aktivitas'])} aktivitas tercatat seluruhnya.")
        if not any(cacah.values()):
            st.caption("Belum ada aktivitas dalam 6 bulan terakhir.")
        else:
            st.bar_chart(pd.DataFrame({"Bulan": list(cacah), "Aktivitas": list(cacah.values())}),
                         x="Bulan", y="Aktivitas", color="#2f5d9e", height=220)
        if orang:
            st.caption("Paling aktif: " + ", ".join(f"{k} ({v})" for k, v in sorted(orang.items(), key=lambda kv: -kv[1])[:5]))

    if daftar_pemilik():
        with st.container(key="kartu_g_s7"):
            st.markdown("**Per pemilik**")
            per = {}
            for b in brg:
                p = per.setdefault(b.get("pemilik") or "Tanpa pemilik", [0, 0, 0])
                p[0] += 1
                p[1] += jumlah_b(b)
                p[2] += harga_b(b) * max(jumlah_b(b), 0)
            for nama_p, (j, bh, nl) in sorted(per.items(), key=lambda kv: -kv[1][0]):
                st.markdown(_baris_stat(nama_p, f"{j} jenis, {bh} buah" + (f" · nilai {rp(nl)}" if nl else "")),
                            unsafe_allow_html=True)

    with st.container(key="kartu_g_s6"):
        st.markdown("**Kelengkapan data**")
        n = len(brg)
        kurang = [("Belum ada foto", sum(1 for b in brg if not semua_foto(b))),
                  ("Belum ada kategori", sum(1 for b in brg if not b.get("kategori"))),
                  ("Belum ada harga", sum(1 for b in brg if not harga_b(b))),
                  ("Belum ada lokasi", sum(1 for b in brg if lokasi_dari(b) is None)),
                  ("Belum pernah diinventarisasi", sum(1 for b in brg if not b.get("opname")))]
        st.markdown("".join(_baris_stat(lab, f"{c} dari {n} barang ({round(c * 100 / n)}%)") for lab, c in kurang),
                    unsafe_allow_html=True)


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


if halaman == "Kelola barang":
    halaman_barang()
if halaman == "Inventaris ulang":
    halaman_opname()
if halaman == "Pindah massal":
    halaman_pindah()
if halaman == "Jelajah lokasi":
    halaman_jelajah()
if halaman == "Tempat sampah":
    halaman_sampah()
if halaman == "Dibawa, hilang, rusak":
    halaman_dibawa()
if halaman == "Catatan perawatan":
    halaman_perawatan()
if halaman == "Pinjam-meminjam":
    halaman_pinjam()
if halaman == "Belanja":
    halaman_belanja()
if halaman == "Scan barcode":
    halaman_scan()
if halaman == "Ekspor dan impor":
    t_ekspor, t_impor = st.tabs(["Ekspor", "Impor"])
    with t_ekspor:
        halaman_ekspor()
    with t_impor:
        halaman_impor()
if halaman == "Daftar bawaan":
    halaman_paket()
if halaman == "Jarang dipakai":
    halaman_jarang()
if halaman == "Riwayat":
    t_p, t_a = st.tabs(["Perpindahan", "Aktivitas"])
    with t_p:
        halaman_riwayat()
    with t_a:
        halaman_aktivitas()
if halaman == "Statistik":
    t_s, t_n = st.tabs(["Ringkasan", "Nilai barang"])
    with t_s:
        halaman_statistik()
    with t_n:
        halaman_nilai()
if halaman == "Jatuh tempo":
    t_k, t_g, t_c = st.tabs(["Kedaluwarsa", "Garansi", "Cek berkala"])
    with t_k:
        _tabel_tanggal("kedaluwarsa", "Kedaluwarsa")
    with t_g:
        _tabel_tanggal("garansi", "Garansi sampai")
    with t_c:
        halaman_pengingat()
if halaman == "Tampilan":
    t_b, t_k = st.tabs(["Beranda", "Kartu barang"])
    with t_b:
        halaman_tampilan()
    with t_k:
        halaman_tampilan_kartu()
if adalah_admin() and halaman == "Tempat dan lokasi":
    t_t, t_l, t_s = st.tabs(["Tempat", "Lokasi", "Sub lokasi"])
    with t_t:
        daftar_sederhana("Tempat", "tempat", "Tempat besar yang menyimpan barang, misalnya Rumah A, Rumah B, atau Kantor. "
                         "Menghapus tempat tidak menghapus lokasinya, hanya melepasnya dari tempat itu.")
    with t_l:
        halaman_lokasi()
    with t_s:
        halaman_sublokasi()
if adalah_admin() and halaman == "Kategori dan label":
    t_k, t_p, t_l = st.tabs(["Kategori", "Pemilik", "Label"])
    with t_k:
        daftar_sederhana("Kategori", "kategori", "Pengelompokan jenis barang, misalnya pakaian atau perawatan diri. "
                         "Boleh dikosongkan kalau tidak diperlukan.")
    with t_p:
        halaman_pemilik()
    with t_l:
        halaman_kelola_label()
if adalah_admin() and halaman == "Label QR":
    halaman_label()
if adalah_admin() and halaman == "Ukuran data":
    halaman_ukuran()
if adalah_admin() and halaman == "Cadangan dan pulihkan":
    t_c, t_p = st.tabs(["Cadangan", "Titik pulih"])
    with t_c:
        cadangan()
    with t_p:
        halaman_pulih()
