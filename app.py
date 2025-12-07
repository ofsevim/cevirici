import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="??", layout="wide")
st.title("?? Gorsel Kontrollu Liste Duzenleyici")
st.markdown("Dosyan?z? yukleyin, **onizleme tablosuna bakarak** do?ru sutunlar? secin.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
@st.cache_data
def load_data_safely(file):
    """Dosyay? okur, hem Excel hem CSV dener."""
    try:
        # Dosya Excel mi?
        if file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, header=None), None
        
        # Dosya CSV mi?
        file.seek(0)
        encodings = ["utf-8", "cp1254", "latin1", "iso-8859-9"]
        for enc in encodings:
            try:
                file.seek(0)
                return pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'), None
            except: continue
            
        return None, "Dosya format? desteklenmiyor veya bozuk."
    except Exception as e:
        return None, str(e)

def clean_tc(val):
    """TC temizler (1.23E+11 gibi bilimsel gosterimleri de duzeltir)"""
    try:
        if pd.isna(val): return None
        s = str(val)
        # E?er float/bilimsel geldiyse (12345.0) once int yap
        if isinstance(val, float) or '.' in s:
            try: s = str(int(float(s)))
            except: pass
            
        digits = re.sub(r"\D", "", s) # Sadece rakamlar? al
        return digits if len(digits) == 11 and digits[0] != "0" else None
    except: return None

def clean_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace("?", "").replace("TL", "").replace(" ", "")
    if "," in s and "." in s: s = s.replace(".", "") # 1.000,50 -> 1000,50
    s = s.replace(",", ".") # 1000,50 -> 1000.50
    try: return float(s)
    except: return 0.0

def get_col_label(df, col_idx):
    """Dropdown icin 'Sutun 5 (Ahmet)' gibi etiket olu?turur."""
    # O sutundaki ilk dolu ve anlaml? veriyi bul
    try:
        series = df[col_idx].astype(str)
        # Ba?l?k kelimelerini ve bo?luklar? atla
        valid = series[~series.str.lower().isin(['nan', 'none', '', ' ', 's?ra', 'ad?', 'soyad?', 'tc', 'tutar'])]
        if len(valid) > 0:
            sample = valid.iloc[0]
            if len(sample) > 20: sample = sample[:17] + "..."
            return f"Sutun {col_idx} ?? {sample}"
    except: pass
    return f"Sutun {col_idx} (Bo?)"

# ------------------ ANA AKI? ------------------
uploaded_file = st.file_uploader("Excel veya CSV Dosyas? Yukleyin", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df, error = load_data_safely(uploaded_file)

    if error:
        st.error(f"Dosya okunamad?: {error}")
    elif df is not None:
        
        # --- 1. ON?ZLEME (BURASI EKLEND?) ---
        st.divider()
        st.subheader("?? Dosya Onizleme")
        st.info("A?a??daki tabloya bakarak hangi verinin hangi sutunda oldu?unu inceleyin.")
        
        # ?lk 50 sat?r? goster (Cok buyuk dosyalar kasmas?n diye)
        st.dataframe(df.head(50), use_container_width=True)
        
        st.divider()
        st.subheader("?? Sutunlar? E?le?tir")

        # --- 2. DROPDOWN SECENEKLER? ---
        # Sadece dolu sutunlar? listeye ekleyelim
        col_options = ["Seciniz..."]
        col_map = {} # Etiket -> Index
        
        for col in df.columns:
            # Sutun tamamen bo? mu kontrol et
            if df[col].notna().sum() > 0:
                label = get_col_label(df, col)
                col_options.append(label)
                col_map[label] = col
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("##### Zorunlu Alanlar")
            sel_tc = st.selectbox("TC Kimlik No", col_options)
            sel_aidat = st.selectbox("Aidat Tutar?", col_options)
        
        with c2:
            st.markdown("##### ?sim Bilgisi")
            sel_ad = st.selectbox("Ad?", col_options)
            sel_soyad = st.selectbox("Soyad?", col_options)
            
        with c3:
            st.markdown("##### Opsiyonel")
            sel_uye = st.selectbox("Uye No", col_options)

        # --- 3. ??LEM BUTONU ---
        if st.button("Listeyi Olu?tur ??", type="primary"):
            if "Seciniz..." in [sel_tc, sel_aidat, sel_ad, sel_soyad]:
                st.warning("?? Lutfen TC, Aidat, Ad ve Soyad sutunlar?n? seciniz.")
            else:
                try:
                    out = pd.DataFrame()
                    
                    # Verileri al
                    out["TC Kimlik No"] = df[col_map[sel_tc]]
                    out["Aidat Tutar?"] = df[col_map[sel_aidat]]
                    out["Ad?"] = df[col_map[sel_ad]]
                    out["Soyad?"] = df[col_map[sel_soyad]]
                    
                    if sel_uye != "Seciniz...":
                        out["Uye No"] = df[col_map[sel_uye]]
                    else:
                        out["Uye No"] = ""

                    # Temizlik
                    # 1. TC Temizli?i
                    out["TC Kimlik No"] = out["TC Kimlik No"].apply(clean_tc)
                    out = out.dropna(subset=["TC Kimlik No"]) # Gecersiz sat?rlar? sil
                    
                    # 2. Para Temizli?i
                    out["Aidat Tutar?"] = out["Aidat Tutar?"].apply(clean_money)
                    
                    # 3. Uye No Temizli?i (Varsa)
                    if not out.empty:
                        out["Uye No"] = out["Uye No"].astype(str).str.split(".").str[0].replace("nan", "")

                    # 4. S?ra No Ekle
                    out.insert(0, "S?ra No", range(1, len(out) + 1))

                    if out.empty:
                        st.error("? Hicbir gecerli kay?t bulunamad?! TC Kimlik sutununu do?ru secti?inizden emin olun.")
                    else:
                        st.success(f"? ??lem Tamam! {len(out)} ki?i listelendi.")
                        st.dataframe(out, use_container_width=True)

                        # ?ndir
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                            out.to_excel(writer, index=False)
                        
                        st.download_button(
                            "?? Excel ?ndir",
                            buffer.getvalue(),
                            "Duzenlenmis_Liste.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                except Exception as e:
                    st.error(f"Hata olu?tu: {e}")