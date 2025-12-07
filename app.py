import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Kesin Cozum", page_icon="??", layout="wide")
st.title("?? Bo? Sutun Savar")
st.markdown("Sutunlarda en az 5 tane gercek veri yoksa listede **gosterilmez**.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
@st.cache_data
def load_data_safely(file):
    try:
        # Excel Okuma
        if file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, header=None), None
        
        # CSV Okuma
        file.seek(0)
        encodings = ["utf-8", "cp1254", "latin1", "iso-8859-9"]
        for enc in encodings:
            try:
                file.seek(0)
                # sep=None otomatik ay?r?c? bulur
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

def get_really_clean_options(df):
    """
    ACIMASIZ F?LTRE:
    1. Sutundaki her ?eyi stringe cevirip temizle.
    2. 'nan', '0', ':', '-', '.' gibi cop verileri yok say.
    3. E?er sutunda EN AZ 5 TANE anlaml? veri kalm?yorsa, o sutunu cope at.
    """
    options = ["Seciniz..."]
    mapping = {}
    
    # Cop Listesi (Bunlar? veri saymayaca??z)
    garbage_values = ['nan', 'none', 'null', 'nat', '', ' ', '0', '0.0', '0,0', '-', '_', '.', ':', ',', 'tl', 'try']

    for col in df.columns:
        # 1. Stringe cevir ve kenar bo?luklar?n? sil, kucuk harfe cevir (kontrol icin)
        series_str = df[col].astype(str).str.strip()
        series_lower = series_str.str.lower()
        
        # 2. Cop olmayanlar?n say?s?n? bul
        # garbage_values listesinde OLMAYAN ve uzunlu?u 1'den buyuk olan veriler
        valid_mask = (~series_lower.isin(garbage_values)) & (series_str.str.len() > 1)
        valid_data = df.loc[valid_mask, col] # Orijinal (buyuk/kucuk harfli) veriyi al
        
        # 3. E??K DE?ER?: E?er sutunda 5'ten az gecerli veri varsa bu sutunu gosterme!
        # (Bu sayede tek bir sayfa numaras? olan bo? sutunlar elenir)
        if len(valid_data) < 5:
            continue
            
        # 4. Ornek Veri Bul (Ba?l?k Olmayan)
        sample = "Veri"
        for val in valid_data.head(50):
            v_str = str(val).strip()
            # Ba?l?k kelimelerine benzemiyorsa ornek olarak al
            if v_str.lower() not in ["s?ra", "no", "ad?", "soyad?", "tc", "kimlik", "uye", "tutar", "aidat", "banka", "sendika"]:
                sample = v_str
                break
        
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
        with st.expander("?? Dosya Onizlemesi (T?kla Ac/Kapa)", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)
        
        # --- 2. ACIMASIZ F?LTREL? SECENEKLER ---
        col_options, col_map = get_really_clean_options(df)
        
        if len(col_options) == 1:
            st.error("?? Dosyada i?lenebilecek dolu bir sutun bulunamad?!")
        else:
            st.success(f"? Gereksiz bo? sutunlar temizlendi. Toplam {len(col_options)-1} dolu sutun bulundu.")
            
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
                if "Seciniz" in [sel_tc, sel_aidat, sel_ad, sel_soyad]:
                    st.warning("Lutfen TC, Aidat, Ad ve Soyad alanlar?n? seciniz.")
                else:
                    try:
                        out = pd.DataFrame()
                        
                        # Verileri Cek
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
                        out = out.dropna(subset=["TC Kimlik No"]) # Gecersiz TC sat?rlar?n? sil
                        
                        # Para
                        out["Aidat Tutar?"] = out["Aidat Tutar?"].apply(clean_money)
                        
                        # Uye No
                        if not out.empty:
                            out["Uye No"] = out["Uye No"].astype(str).str.split(".").str[0].replace("nan", "")

                        # S?ra No
                        out.insert(0, "S?ra No", range(1, len(out) + 1))

                        if out.empty:
                            st.error("? Kay?t bulunamad?. TC Kimlik sutununu do?ru sectiniz mi?")
                        else:
                            st.success(f"? ??lem Tamam! {len(out)} kay?t listelendi.")
                            st.dataframe(out, use_container_width=True)

                            # ?ndir
                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                out.to_excel(writer, index=False)
                            
                            st.download_button(
                                "?? Temiz Excel ?ndir",
                                buffer.getvalue(),
                                "Net_Liste.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                    except Exception as e:
                        st.error(f"Bir hata olu?tu: {e}")