import streamlit as st
import pandas as pd
from io import BytesIO
import unicodedata

st.set_page_config(page_title="Uye Aidat Bilgileri", layout="wide")
st.title("?? Uye Aidat Bilgileri")

uploaded_file = st.file_uploader(
    "Excel dosyas?n? yukleyin (.xlsx / .xls)",
    type=["xlsx", "xls"]
)

def normalize(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        original_columns = list(df.columns)
        normalized_columns = {normalize(c): c for c in original_columns}

        def find_col(keywords):
            for norm, original in normalized_columns.items():
                if any(k in norm for k in keywords):
                    return original
            return None

        col_uye   = find_col(["uye", "sicil", "no"])
        col_ad    = find_col(["ad", "isim"])
        col_soyad = find_col(["soyad"])
        col_tc    = find_col(["tc", "kimlik"])
        col_aidat = find_col(["aidat", "tutar", "kesinti"])

        if not any([col_uye, col_ad, col_soyad, col_tc, col_aidat]):
            st.error("? Gerekli kolonlar bulunamad?. Excel ba?l?klar?n? kontrol edin.")
            st.stop()

        result = pd.DataFrame()

        if col_uye:
            result["Uye No"] = df[col_uye]
        if col_ad:
            result["Ad"] = df[col_ad]
        if col_soyad:
            result["Soyad"] = df[col_soyad]
        if col_tc:
            result["TC Kimlik No"] = df[col_tc]
        if col_aidat:
            result["Aidat Tutar?"] = df[col_aidat]

        result = result.dropna(how="all")
        result.insert(0, "S?ra No", range(1, len(result) + 1))

        st.success("? Veriler ba?ar?yla al?nd?")
        st.dataframe(result, use_container_width=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, index=False, sheet_name="AidatListesi")
        buffer.seek(0)

        st.download_button(
            "?? Excel olarak indir",
            data=buffer,
            file_name="uye_aidat_listesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error("? Dosya okunurken hata olu?tu")
        st.exception(e)
