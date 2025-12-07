import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="?", layout="wide")
st.title("? Tertemiz Liste Duzenleyici")
st.markdown("Bo? sutunlar, 'None' yaz?lar? gizlendi. Sadece verisi olan sutunlar? sec.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
@st.cache_data
def load_data_safely(file):
    try:
        # Excel
        if file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, header=None), None
        
        # CSV
        file.seek(0)
        encodings = ["utf-8", "cp1254", "latin1", "iso-8859-9"]
        for enc in encodings:
            try:
                file.seek(0)
                return pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'), None
            except: continue
            
        return None, "Dosya format? desteklenmiyor."
    except Exception as e:
        return None, str(e)

def clean_tc(val):
    try:
        if pd.isna(val): return None
        s = str(val)
        if isinstance(val, float) or '.' in s:
            try: s = str(int(float(s)))
            except: pass
        digits = re.sub(r"\D", "", s)
        return digits if len(digits) == 11 and digits[0] != "0" else None
    except: return None

def clean_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace("?", "").replace("TL", "").replace(" ", "")
    if "," in s and "." in s: s = s.replace(".", "")
    s = s.replace(",", ".")
    try: return float(s)
    except: return 0.0

def get_clean_col_options(df):
    """Sadece gercek veri iceren sutunlar? listeler. None/nan icerenleri eler."""
    options = ["Seciniz..."]
    mapping = {}
    
    for col in df.columns:
        # Sutundaki verileri string'e cevir ve bo?luklar? sil
        series = df[col].astype(str).str.strip()
        
        # S?YAH L?STE: Bunlar? veri olarak kabul etme
        blacklist = ['nan', 'none', 'nat', 'null', '', '0', '0.0', '.', '-', '_']
        
        # Siyah listede OLMAYAN verileri bul
        # case=False buyuk kucuk harf duyars?z yapar (NaN, nan, NAN hepsi gider)
        valid_data = series[~series.str.lower().isin(blacklist)]
        
        # E?er gecerli veri yoksa bu sutunu seceneklere EKLEME
        if valid_data.empty:
            continue
            
        # Ornek veri bulma (Ba?l?k olmayan bir ?ey bulmaya cal??)
        sample = "Veri"
        found_sample = False
        
        # ?lk 100 gecerli veriye bak
        for val in valid_data.head(100):
            v_lower = val.lower()
            # Ba?l?k kelimelerine benzemeyen bir ?ey bul
            if v_lower not in ["s?ra", "no", "ad?", "soyad?", "tc", "kimlik", "tutar", "aidat", "uye"]:
                sample = val
                found_sample = True
                break
        
        # E?er ba?l?k d???nda bir ?ey bulamad?ysa ilk gecerli veriyi al
        if not found_sample:
            sample = valid_data.iloc[0]
            
        # Cok uzunsa k?salt
        if len(sample) > 20: sample = sample[:17] + "..."
        
        label = f"Sutun {col} ?? {sample}"
        options.append(label)
        mapping[label] = col
        
    return options, mapping

# ------------------ ANA AKI? ------------------
uploaded_file = st.file_uploader("Dosya Yukle", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df, error = load_data_safely(uploaded_file)

    if error:
        st.error(f"Hata: {error}")
    elif df is not None:
        
        # --- 1. ON?ZLEME ---
        with st.expander("Dosya Onizlemesini Goster/Gizle", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)
        
        # --- 2. TEM?Z SECENEKLER? OLU?TUR ---
        col_options, col_map = get_clean_col_options(df)
        
        if len(col_options) == 1:
            st.error("?? Dosyada anlaml? veri iceren hicbir sutun bulunamad?!")
        else:
            st.info("?? A?a??daki listelerde **sadece dolu sutunlar** gosterilmektedir.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("##### 1. Zorunlu Alanlar")
                sel_tc = st.selectbox("TC Kimlik No", col_options)
                sel_aidat = st.selectbox("Aidat Tutar?", col_options)
            
            with c2:
                st.markdown("##### 2. ?sim Bilgisi")
                sel_ad = st.selectbox("Ad?", col_options)
                sel_soyad = st.selectbox("Soyad?", col_options)
                
            with c3:
                st.markdown("##### 3. Opsiyonel")
                sel_uye = st.selectbox("Uye No", col_options)

            st.divider()

            # --- 3. L?STEY? OLU?TUR ---
            if st.button("L?STEY? OLU?TUR ??", type="primary"):
                # Basit do?rulama
                if "Seciniz" in [sel_tc, sel_aidat, sel_ad, sel_soyad]:
                    st.warning("TC, Aidat, Ad ve Soyad secimi zorunludur.")
                else:
                    try:
                        out = pd.DataFrame()
                        
                        # Sutunlar? haritadan bulup cek
                        out["TC Kimlik No"] = df[col_map[sel_tc]]
                        out["Aidat Tutar?"] = df[col_map[sel_aidat]]
                        out["Ad?"] = df[col_map[sel_ad]]
                        out["Soyad?"] = df[col_map[sel_soyad]]
                        
                        if sel_uye != "Seciniz...":
                            out["Uye No"] = df[col_map[sel_uye]]
                        else:
                            out["Uye No"] = ""

                        # --- TEM?ZL?K ---
                        
                        # TC
                        out["TC Kimlik No"] = out["TC Kimlik No"].apply(clean_tc)
                        out = out.dropna(subset=["TC Kimlik No"]) # Bo? TC'leri sil
                        
                        # Para
                        out["Aidat Tutar?"] = out["Aidat Tutar?"].apply(clean_money)
                        
                        # Uye No
                        if not out.empty:
                            out["Uye No"] = out["Uye No"].astype(str).str.split(".").str[0].replace("nan", "")

                        # S?ra No Ekle
                        out.insert(0, "S?ra No", range(1, len(out) + 1))

                        if out.empty:
                            st.error("? Kay?t bulunamad?. TC Kimlik sutununu do?ru secti?inizden emin olun.")
                        else:
                            st.success(f"? {len(out)} kay?t ba?ar?yla olu?turuldu.")
                            st.dataframe(out, use_container_width=True)

                            # ?ndir
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                out.to_excel(writer, index=False)
                            
                            st.download_button(
                                "?? Excel Olarak ?ndir",
                                buffer.getvalue(),
                                "Temiz_Liste.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                    except Exception as e:
                        st.error(f"Bir hata olu?tu: {e}")