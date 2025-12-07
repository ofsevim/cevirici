import streamlit as st
import pandas as pd
import io
import re

st.set_page_config("Uye Aidat Listesi", "??", layout="wide")
st.title("?? Uye ¡V Aidat Net Liste")

uploaded_file = st.file_uploader(
    "Excel / CSV Dosyas? Yukleyin",
    type=["xlsx", "xls", "csv"]
)

def normalize(col):
    return str(col).lower().replace(" ", "").replace("_", "")

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

if uploaded_file:
    # OKUMA
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # SUTUN E?LEME (OTOMAT?K)
    col_map = {}
    for c in df.columns:
        key = normalize(c)
        if "uye" in key and "no" in key:
            col_map["Uye No"] = c
        elif key in ["ad","adi","isim"]:
            col_map["Adi"] = c
        elif "soyad" in key:
            col_map["Soyadi"] = c
        elif "tc" in key:
            col_map["TC Kimlik No"] = c
        elif "aidat" in key or "tutar" in key:
            col_map["Aidat Tutar?"] = c

    missing = {"Uye No","Adi","Soyadi","TC Kimlik No","Aidat Tutar?"} - col_map.keys()

    if missing:
        st.error(f"Eksik alanlar bulundu: {', '.join(missing)}")
        st.stop()

    # YEN? TABLO
    out = pd.DataFrame()
    out["Uye No"] = df[col_map["Uye No"]].astype(str).str.split(".").str[0]
    out["Ad?"] = df[col_map["Adi"]]
    out["Soyad?"] = df[col_map["Soyadi"]]
    out["TC Kimlik No"] = df[col_map["TC Kimlik No"]].apply(clean_tc)
    out["Aidat Tutar?"] = df[col_map["Aidat Tutar?"]].apply(clean_money)

    # TEM?ZL?K
    out = out.dropna(subset=["TC Kimlik No"])
    out.insert(0, "S?ra No", range(1, len(out) + 1))

    # GORUNTULE
    st.success(f"? {len(out)} kay?t haz?r")
    st.dataframe(out, use_container_width=True)

    # ?ND?R
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        out.to_excel(writer, index=False)
    buffer.seek(0)

    st.download_button(
        "?? Excel Olarak ?ndir",
        buffer.getvalue(),
        "Uye_Aidat_Listesi.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
