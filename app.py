import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="?", layout="wide")
st.title("? Uye Aidat Net Liste")
st.markdown("Excel dosyan?z? yukleyin, sutunlar? secin ve temiz listeyi indirin.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
def load_data_safely(file):
    """Dosyay? okur ve hata varsa yakalar."""
    try:
        if file.name.lower().endswith(('.xlsx', '.xls')):
            # header=None ile okuyoruz ki ba?l?k nerede olursa olsun gorelim
            return pd.read_excel(file, header=None), None
        else:
            file.seek(0)
            for enc in ["utf-8", "cp1254", "latin1"]:
                try:
                    return pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'), None
                except: continue
            return None, "CSV format? desteklenmiyor."
    except Exception as e:
        return None, str(e)

def clean_tc(val):
    """TC'yi temizler ve 11 hane kontrolu yapar."""
    try:
        # Bilimsel gosterim (1.23E+10) sorununu cozmek icin once float->int->str
        s = str(int(float(val))) 
    except:
        s = str(val)
    
    digits = re.sub(r"\D", "", s) # Sadece rakamlar? al
    return digits if len(digits) == 11 and digits[0] != "0" else None

def clean_money(val):
    """Para birimini temizler (TL, bo?luk vs atar)."""
    if pd.isna(val): return 0.0
    s = str(val).replace("?", "").replace("TL", "").replace(" ", "")
    # 1.000,50 format? icin noktay? sil
    if "," in s and "." in s: s = s.replace(".", "")
    s = s.replace(",", ".")
    try: return float(s)
    except: return 0.0

def get_preview_label(df, col_idx):
    """Kullan?c?ya sutunun icinde ne oldu?unu gostermek icin etiket olu?turur."""
    # Sutundaki ilk dolu ve anlaml? veriyi bul (Ba?l?klar? atla)
    valid_vals = df[col_idx].dropna().astype(str)
    sample = "Bo?"
    for v in valid_vals.head(20):
        if len(v) > 1 and v.lower() not in ["s?ra", "ad?", "tc", "uye", "tutar"]:
            sample = v
            break
    if len(sample) > 20: sample = sample[:17] + "..."
    return f"Sutun {col_idx} ({sample})"

# ------------------ ANA AKI? ------------------
uploaded_file = st.file_uploader("Dosya Yukle", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df, error = load_data_safely(uploaded_file)

    if error:
        st.error(f"Hata: {error}")
    elif df is not None:
        
        # --- 1. SUTUN SEC?M? (DROPDOWN) ---
        st.info("?? A?a??daki kutulardan hangi verinin nerede oldu?unu secin.")
        
        # Secenekleri haz?rla (Sadece dolu sutunlar)
        col_options = ["Seciniz..."]
        col_map_index = {} # Etiket -> Index
        
        for col in df.columns:
            if df[col].notna().sum() > 0: # Bo? sutunlar? gizle
                label = get_preview_label(df, col)
                col_options.append(label)
                col_map_index[label] = col
        
        c1, c2, c3 = st.columns(3)
        with c1:
            sel_tc = st.selectbox("TC Kimlik No", col_options)
            sel_aidat = st.selectbox("Aidat Tutar?", col_options)
        with c2:
            sel_ad = st.selectbox("Ad?", col_options)
            sel_soyad = st.selectbox("Soyad?", col_options)
        with c3:
            sel_uye = st.selectbox("Uye No (Varsa)", col_options)

        # --- 2. L?STEY? OLU?TUR ---
        if st.button("Listeyi Haz?rla ??", type="primary"):
            if "Seciniz" in [sel_tc, sel_aidat, sel_ad, sel_soyad]:
                st.warning("Lutfen TC, Aidat, Ad ve Soyad alanlar?n? seciniz.")
            else:
                try:
                    out = pd.DataFrame()
                    
                    # Verileri cek
                    out["TC Kimlik No"] = df[col_map_index[sel_tc]]
                    out["Aidat Tutar?"] = df[col_map_index[sel_aidat]]
                    out["Ad?"] = df[col_map_index[sel_ad]]
                    out["Soyad?"] = df[col_map_index[sel_soyad]]
                    
                    if sel_uye != "Seciniz...":
                        out["Uye No"] = df[col_map_index[sel_uye]]
                    else:
                        out["Uye No"] = ""

                    # Temizlik
                    out["TC Kimlik No"] = out["TC Kimlik No"].apply(clean_tc)
                    out = out.dropna(subset=["TC Kimlik No"]) # Gecersiz sat?rlar? at
                    
                    out["Aidat Tutar?"] = out["Aidat Tutar?"].apply(clean_money)
                    out["Uye No"] = out["Uye No"].astype(str).str.split(".").str[0].replace("nan", "")

                    # S?ra No Ekle
                    out.insert(0, "S?ra No", range(1, len(out) + 1))

                    # Sonuc Goster
                    st.success(f"? {len(out)} kay?t ba?ar?yla duzenlendi.")
                    st.dataframe(out, use_container_width=True)

                    # ?ndir
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                        out.to_excel(writer, index=False)
                    
                    st.download_button(
                        "?? Excel ?ndir",
                        buffer.getvalue(),
                        "Net_Liste.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                except Exception as e:
                    st.error(f"??lem s?ras?nda hata: {e}")