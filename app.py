import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="Uye Aidat Listesi",
    layout="wide"
)

st.title("?? Uye Aidat Bilgileri")

uploaded_file = st.file_uploader(
    "Excel dosyas?n? yukleyin (.xlsx / .xls)",
    type=["xlsx", "xls"]
)

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)

        # Kolon adlar?n? normalize et
        df.columns = [str(c).strip().lower() for c in df.columns]

        def find_col(keywords):
            for c in df.columns:
                if any(k in c for k in keywords):
                    return c
            return None

        col_uye = find_col(["uye", "uye", "sicil", "no"])
        col_ad = find_col(["ad", "ad?", "isim"])
        col_soyad = find_col(["soyad", "soyad?"])
        col_tc = find_col(["tc", "tckn", "kimlik"])
        col_aidat = find_col(["aidat", "tutar", "kesinti"])

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

        # ===== EXCEL DOWNLOAD (DO?RU YOL) =====
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            result.to_excel(writer, index=False, sheet_name="AidatListesi")
        buffer.seek(0)

        st.download_button(
            label="?? Excel olarak indir",
            data=buffer,
            file_name="uye_aidat_listesi.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error("? Dosya okunurken hata olu?tu")
        st.exception(e)
