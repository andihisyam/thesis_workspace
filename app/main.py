import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Thesis Assistant Home",
    page_icon="??",
    layout="wide",
)

st.title("AI Thesis Writing Assistant")
st.write(
    "App ini sekarang dipisah menjadi dua halaman utama supaya alurnya lebih rapi dan enak dipakai."
)

st.markdown("**Halaman 1: Review Draft**")
st.write(
    "Pakai halaman ini untuk memilih bab atau bagian tertentu, menjalankan review, dan membuat draft revisi terkontrol."
)

st.markdown("**Halaman 2: Compile & Compare**")
st.write(
    "Pakai halaman ini untuk compile versi asli dan versi revisi, lalu membandingkan hasil PDF serta perbedaan teksnya."
)

st.info("Pilih halaman dari sidebar Streamlit di sebelah kiri.")
