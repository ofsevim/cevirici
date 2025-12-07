import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(
    page_title="Uye Aidat Net Liste",
    page_icon="??",
    layout="wide"
)

st.title("?? Uye Aidat Net Liste")

uploaded_file = st.file_uploader(
    "Excel / CSV Dosyas? Yukleyin",
    type=["xlsx", "xls", "csv"]
)

# =================== YARDIMCI ===================

def read_csv_hardcore(uploaded_file):
    raw = uploaded_file.getvalue()   # <<< KR?T?K SATIR
    for enc in ["utf-8", "cp1254", "latin1"]:
        try:
            text = raw.decode(enc)
            return pd.read_csv(io.StringIO(text))
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV dosyas?n?n karakter kodlamas? cozulemedi.")

def normalize(txt):
    return str(txt).lower().replace(" ", "").replace("_", "")

def clean_tc(val):
    digits = re.sub(r"\D", "", str(val))
    return digits if len(digits) == 11 and digits[0] != "0" else None

def clean_money(val):
    if pd.isna(val):
        return 0.0
    s = (
        str(val)
        .replace("?", "")
        .replace("TL", "")
        .replace(" ", "")
    )
    if "," in s and "." in s:
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

# =================== ANA AKI? ===================

if uploaded_file:
    try:
        # DOSYA OKUMA (?? UTF-8 HATASI ARTIK OLU)
        if uploaded_file.name.lower().endswith(".csv"):
            df = read_csv_hardcore(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # SUTUNLARI BUL
        col_map = {}
        for c in df.columns:
            key = normalize(c)
            if "uye" in key and "no" in key:
                col_map["Uye No"] = c
            elif key in ["ad", "adi", "isim"]:
                col_map["Adi"] = c
            elif "soyad" in key:
                col_map["Soyadi"] = c
            elif "tc" in key:
