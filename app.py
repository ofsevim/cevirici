import streamlit as st
import pandas as pd
import io
import re

# ------------------ SAYFA AYARLARI ------------------
st.set_page_config(page_title="Rontgen Modu", page_icon="??", layout="wide")
st.title("?? Dosya Rontgeni")
st.markdown("Sutunlar?n harflerini (A, B, C) ve verinin hangi sat?rda bulundu?unu gosterir.")

# ------------------ YARDIMCI FONKS?YONLAR ------------------
@st.cache_data
def load_data_safely(file):
    try:
        if file.name.lower().endswith(('.xlsx', '.xls')):
            return pd.read_excel(file, header=None), None
        
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

def get_excel_col_name(n):
    """0 -> A, 1 -> B, 26 -> AA cevirimi yapar"""
    string = ""
    n += 1 # 1-based adjustment
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

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

def get_detailed_options(df, show_all):
    """
    Hem Sutun Indexini, Hem Excel Harfini, Hem de Ornek Veriyi ve Yerini gosterir.
    """
    options = ["Seciniz..."]
    mapping = {}
    
    for col_idx in df.columns:
        # Excel Harfi (0=A, 1=B...)
        col_letter = get_excel_col_name(col_idx)
        
        # Sutun Verisi
        series = df[col_idx]
        
        # Tamamen bo? mu?
        if series.isna().all():
            if show_all:
                label = f"[{col_idx}] Sutun {col_letter} ?? (TAMAMEN BO?)"
                options.append(label)
                mapping[label] = col_idx
            continue

        # Dolu verileri al
        valid_series = series.dropna().astype(str)
        valid_series = valid_series[valid_series.str.strip() != ""] # Bo?luklar? at
        
        # ?cinde "nan", "0" gibi ?eyler varsa ele (ama kullan?c? istiyorsa goster)
        trash_list = ['nan', 'none', '0', '0.0', '.', '-', '_']
        meaningful_data = valid_series[~valid_series.str.lower().isin(trash_list)]
        
        if meaningful_data.empty:
            if show_all:
                label = f"[{col_idx}] Sutun {col_letter} ?? (Sadece Cop Veri Var)"
                options.append(label)
                mapping[label] = col_idx
            continue

        # Ornek Veri Bul
        sample_val = "Bulunamad?"
        found_row = -1
        
        # ?lk anlaml? veriyi bul (Ba?l?k olmayan)
        for idx, val in meaningful_data.items():
            v_lower = val.lower()
            if v_lower not in ["s?ra", "no", "ad?", "soyad?", "tc", "kimlik", "tutar", "aidat", "uye"]:
                sample_val = val
                found_row = idx + 1 # Excel sat?r numaras? (1-based)
                break
        
        # E?er hepsi ba?l?ksa ilkini al
        if found_row == -1:
            sample_val = meaningful_data.iloc[0]
            found_row = meaningful_data.index[0] + 1

        # Etiketi Haz?rla
        if len(sample_val) > 15: sample_val = sample_val[:12] + "..."
        
        # Format: [2] Sutun C ?? "Ahmet" (Sat?r 5)
        label = f"[{col_idx}] Sutun {col_letter} ?? \"{sample_val}\" (Sat?r {found_row})"
        
        options.append(label)
        mapping[label] = col_idx
        
    return options, mapping

# ------------------ ANA AKI? ------------------
# Yan menu ayar?
with st.sidebar:
    st.header("Ayarlar")
    show_all_cols = st.checkbox("Butun Sutunlar? Goster (Bo?lar Dahil)", value=False)
    st.info("E?er arad???n?z sutunu listede bulam?yorsan?z yukar?daki kutuyu i?aretleyin.")

uploaded_file = st.file_uploader("Dosya Yukle", type=["xlsx", "xls", "csv"])

if uploaded_file:
    df, error = load_data_safely(uploaded_file)

    if error:
        st.error(f"Hata: {error}")
    elif df is not None:
        
        # --- 1. ON?ZLEME ---
        with st.expander("?? Dosya Onizlemesi (Geni?let)", expanded=True):
            st.dataframe(df.head(50), use_container_width=True)
            st.caption("Not: Tablodaki 0, 1, 2... ba?l?klar? Python indeksidir. A, B, C harfleri a?a??da yazar.")
        
        # --- 2. SECENEKLER ---
        col_options, col_map = get_detailed_options(df, show_all_cols)
        
        if len(col_options) == 1:
            st.warning("Gorunurde dolu sutun yok. Yan menuden 'Butun Sutunlar? Goster'i secmeyi deneyin.")
        else:
            st.success(f"Toplam {len(col_options)-1} adet veri iceren sutun listelendi.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("##### 1. Zorunlu")
                sel_tc = st.selectbox("TC Kimlik No", col_options)
                sel_aidat = st.selectbox("Aidat Tutar?", col_options)
            
            with c2:
                st.markdown("##### 2. ?sim")
                sel_ad = st.selectbox("Ad?", col_options)
                sel_soyad = st.selectbox("Soyad?", col_options)
                
            with c3:
                st.markdown("##### 3. Opsiyonel")
                sel_uye = st.selectbox("Uye No", col_options)

            st.divider()

            # --- 3. ??LEM ---
            if st.button("L?STEY? OLU?TUR ??", type="primary"):
                if "Seciniz" in [sel_tc, sel_aidat, sel_ad, sel_soyad]:
                    st.warning("Lutfen TC, Aidat, Ad ve Soyad seciniz.")
                else:
                    try:
                        out = pd.DataFrame()
                        
                        out["TC Kimlik No"] = df[col_map[sel_tc]]
                        out["Aidat Tutar?"] = df[col_map[sel_aidat]]
                        out["Ad?"] = df[col_map[sel_ad]]
                        out["Soyad?"] = df[col_map[sel_soyad]]
                        
                        if sel_uye != "Seciniz...":
                            out["Uye No"] = df[col_map[sel_uye]]
                        else:
                            out["Uye No"] = ""

                        # Temizlik
                        out["TC Kimlik No"] = out["TC Kimlik No"].apply(clean_tc)
                        out = out.dropna(subset=["TC Kimlik No"])
                        
                        out["Aidat Tutar?"] = out["Aidat Tutar?"].apply(clean_money)
                        
                        if not out.empty:
                            out["Uye No"] = out["Uye No"].astype(str).str.split(".").str[0].replace("nan", "")

                        out.insert(0, "S?ra No", range(1, len(out) + 1))

                        if out.empty:
                            st.error("Kay?t bulunamad?. Secti?iniz sutunlar?n do?ru oldu?undan emin misiniz?")
                        else:
                            st.success(f"? {len(out)} kay?t bulundu.")
                            st.dataframe(out, use_container_width=True)

                            buffer = io.BytesIO()
                            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                                out.to_excel(writer, index=False)
                            
                            st.download_button(
                                "?? ?ndir",
                                buffer.getvalue(),
                                "Net_Liste.xlsx",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )

                    except Exception as e:
                        st.error(f"Hata: {e}")