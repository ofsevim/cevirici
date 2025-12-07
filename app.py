import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="?", layout="wide")
st.title("? Tertemiz Liste Duzenleyici")
st.markdown("Bo? sutunlar, 'None' yaz?lar? gizlendi. Sadece verisi olan sutunlar? sec.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
def load_data_safely(file):
    try:
        if file.name.lower().endswith((".xlsx", ".xls")):
            return pd.read_excel(file), None

        file.seek(0)
        for enc in ["utf-8", "cp1254", "latin1", "iso-8859-9"]:
            try:
                file.seek(0)
                return pd.read_csv(
                    file, encoding=enc, sep=None, engine="python"
                ), None
            except:
                continue

        return None, "Dosya format? desteklenmiyor."
    except Exception as e:
        return None, str(e)

def clean_tc(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    s = re.sub(r"\D", "", s)
    return s if len(s) == 11 and s[0] != "0" else None

def clean_money(val):
    if pd.isna(val):
        return 0.0
    s = str(val).replace("?", "").replace("TL", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def get_clean_col_options(df):
    options = ["Seciniz..."]
    mapping = {}

    blacklist = ["nan", "none", "nat", "null", "", "0", "0.0", "-", "_"]

    for col in df.columns:
        series = df[col].astype(str).str.strip()
        valid = series[~series.str.lower().isin(blacklist)]

        if valid.empty:
            continue

        sample = valid.iloc[0]
        if len(sample) > 20:
            sample = sample[:17] + "..."

        label = f"Sutun {col} ?? {sample}"
        options.append(label)
        mapping[label] = col

    return options, mapping

# ------------------ ANA AKI? ------------------
uploaded_file = st.file_uploader("Dosya Yukle", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df, error = load_data_safely(uploaded_file)

    if error:
        st.error(error)
    else:
        st.dataframe(df.head(50), use_container_width=True)

        col_options, col_map = get_clean_col_options(df)

        c1, c2, c3 = st.columns(3)
        with c1:
            sel_tc = st.selectbox("TC Kimlik No", col_options)
            sel_aidat = st.selectbox("Aidat Tutar?", col_options)
        with c2:
            sel_ad = st.selectbox("Ad?", col_options)
            sel_soyad = st.selectbox("Soyad?", col_options)
        with c3:
            sel_uye = st.selectbox("Uye No (Opsiyonel)", col_options)

        if st.button("L?STEY? OLU?TUR ??", type="primary"):
            if (
                sel_tc == "Seciniz..."
                or sel_aidat == "Seciniz..."
                or sel_ad == "Seciniz..."
                or sel_soyad == "Seciniz..."
            ):
                st.warning("TC, Aidat, Ad ve Soyad secimi zorunludur.")
            else:
                out = pd.DataFrame()
                out["TC Kimlik No"] = df[col_map[sel_tc]].apply(clean_tc)
                out["Aidat Tutar?"] = df[col_map[sel_aidat]].apply(clean_money)
                out["Ad?"] = df[col_map[sel_ad]]
                out["Soyad?"] = df[col_map[sel_soyad]]

                if sel_uye != "Seciniz...":
                    out["Uye No"] = df[col_map[sel_uye]]
                else:
                    out["Uye No"] = ""

                out = out.dropna(subset=["TC Kimlik No"])
                out.insert(0, "S?ra No", range(1, len(out) + 1))

                st.success(f"? {len(out)} kay?t olu?turuldu")
                st.dataframe(out, use_container_width=True)

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    out.to_excel(writer, index=False)

                st.download_button(
                    "?? Excel Olarak ?ndir",
                    buffer.getvalue(),
                    "Temiz_Liste.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
