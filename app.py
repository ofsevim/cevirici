import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA ------------------
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

# ------------------ YARDIMCI ------------------

def read_csv_hardcore(uploaded_file):
    raw = uploaded_file.getvalue()  # ?? UTF-8 bypass
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

# ------------------ ANA AKI? ------------------

if uploaded_file:
    try:
        # DOSYA OKU
        if uploaded_file.name.lower().endswith(".csv"):
            df = read_csv_hardcore(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        # SUTUN E?LEME (? girinti hatas? yok)
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
                col_map["TC"] = c

            elif "aidat" in key or "tutar" in key:
                col_map["Aidat"] = c

        required = {"Uye No", "Adi", "Soyadi", "TC", "Aidat"}
        missing = required - col_map.keys()
        if missing:
            st.error(f"Eksik alanlar: {', '.join(missing)}")
            st.stop()

        # NET TABLO
        out = pd.DataFrame()
        out["Uye No"] = df[col_map["Uye No"]].astype(str).str.split(".").str[0]
        out["Ad?"] = df[col_map["Adi"]]
        out["Soyad?"] = df[col_map["Soyadi"]]
        out["TC Kimlik No"] = df[col_map["TC"]].apply(clean_tc)
        out["Aidat Tutar?"] = df[col_map["Aidat"]].apply(clean_money)

        out = out.dropna(subset=["TC Kimlik No"])
        out.insert(0, "S?ra No", range(1, len
