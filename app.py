import streamlit as st
import pandas as pd
import io
import re

# Sayfa Ayarlar?
st.set_page_config(page_title="Ak?ll? Sendika Listesi", page_icon="??", layout="wide")

st.title("?? Yapay Zeka Destekli Liste Duzenleyici")
st.markdown("""
Dosyan?z? yukleyin. Sutunlar? otomatik bulur. 
**E?er Ad ve Soyad kar???rsa, sol menudeki 'Ad/Soyad Yer De?i?tir' kutusunu kullan?n.**
""")

# --- YAN MENU ---
st.sidebar.header("Ayarlar")
swap_names = st.sidebar.checkbox("Ad ve Soyad? Yer De?i?tir", value=False, help="E?er listede Ad yerine Soyad, Soyad yerine Ad goruyorsan?z bunu i?aretleyin.")

uploaded_file = st.file_uploader("Excel veya CSV dosyan?z? buraya b?rak?n", type=["xls", "xlsx", "csv"])

# --- YARDIMCI ANAL?Z FONKS?YONLARI ---

def is_tc_potential(val):
    try:
        s = str(val).split('.')[0].strip()
        return s.isdigit() and len(s) == 11 and s[0] != '0'
    except: return False

def clean_money_value(x):
    if pd.isna(x): return 0.0
    x = str(x).replace('TL', '').replace(' ', '')
    if ',' in x and '.' in x: x = x.replace('.', '') 
    x = x.replace(',', '.')
    try: return float(x)
    except: return 0.0

def find_header_row(df):
    """
    ?lk 20 sat?r? tarar ve icinde 'Ad?', 'Soyad?', 'TC' gecen ba?l?k sat?r?n? arar.
    Varsa o sat?r?n indeksini ve sutun yerlerini dondurur.
    """
    for i in range(min(20, len(df))):
        row_vals = [str(v).lower() for v in df.iloc[i].values]
        
        # Anahtar kelimeler o sat?rda var m??
        has_ad = any(x in ['ad?', 'ad', 'isim', 'personel ad?'] for x in row_vals)
        has_soyad = any(x in ['soyad?', 'soyad', 'soyisim'] for x in row_vals)
        has_tc = any('tc' in x or 'kimlik' in x for x in row_vals)
        
        if has_ad and has_soyad and has_tc:
            # Ba?l?k sat?r? bulundu! Sutun indekslerini c?karal?m.
            mapping = {}
            for col_idx, val in enumerate(df.iloc[i]):
                val_str = str(val).lower()
                if val_str in ['ad?', 'ad', 'isim']: mapping['Adi'] = df.columns[col_idx]
                elif val_str in ['soyad?', 'soyad']: mapping['Soyadi'] = df.columns[col_idx]
                elif 'kimlik' in val_str or 'tc' in val_str: mapping['TC Kimlik No'] = df.columns[col_idx]
                elif 'aidat' in val_str or 'tutar' in val_str: mapping['Aidat Tutari'] = df.columns[col_idx]
                elif 'uye' in val_str and 'no' in val_str: mapping['Uye No'] = df.columns[col_idx]
            return mapping
            
    return None

def analyze_columns_content(df):
    """
    E?er ba?l?k yoksa iceri?e bakarak tahmin eder.
    """
    sample_rows = df.dropna(thresh=2).sample(n=min(50, len(df)), random_state=42).reset_index(drop=True)
    
    scores = {'TC': {}, 'Aidat': {}, 'Text': {}, 'UyeNo': {}}
    cols = df.columns
    
    for col in cols:
        tc_hits = 0; money_hits = 0; text_hits = 0; uyeno_hits = 0; valid_count = 0
        
        for val in sample_rows[col]:
            if pd.isna(val) or str(val).strip() == "": continue
            valid_count += 1
            
            if is_tc_potential(val): tc_hits += 1
            
            s_val = str(val).split('.')[0]
            if s_val.isdigit() and 3 < len(s_val) < 8: uyeno_hits += 1

            # Para kontrolu (TC ve Uye No de?ilse ve icinde say? varsa)
            s_clean = str(val).replace('TL', '').replace('.', '').replace(',', '')
            if not is_tc_potential(val) and len(s_clean) < 10 and any(c.isdigit() for c in str(val)):
                if ',' in str(val) or '.' in str(val): money_hits += 1
                
            # Metin kontrolu (?cinde say? yoksa)
            s_text = str(val).strip()
            if not any(char.isdigit() for char in s_text) and len(s_text) > 1:
                text_hits += 1

        if valid_count > 0:
            scores['TC'][col] = tc_hits / valid_count
            scores['Aidat'][col] = money_hits / valid_count
            scores['Text'][col] = text_hits / valid_count
            scores['UyeNo'][col] = uyeno_hits / valid_count

    # --- EN ?Y? SUTUNLARI SEC ---
    mapping = {}
    used_cols = set()

    # 1. TC Kimlik No
    tc_col = max(scores['TC'], key=scores['TC'].get, default=None)
    if tc_col is not None and scores['TC'][tc_col] > 0.3:
        mapping['TC Kimlik No'] = tc_col
        used_cols.add(tc_col)
    
    # 2. Aidat
    filtered_aidat = {k:v for k,v in scores['Aidat'].items() if k not in used_cols}
    aidat_col = max(filtered_aidat, key=filtered_aidat.get, default=None)
    if aidat_col is not None:
        mapping['Aidat Tutari'] = aidat_col
        used_cols.add(aidat_col)

    # 3. Ad ve Soyad (Metin sutunlar?)
    potential_text_cols = sorted(
        [c for c in scores['Text'] if c not in used_cols and scores['Text'][c] > 0.4],
        key=lambda x: x # ?ndeks s?ras?na gore (Genelde Ad solda, Soyad sa?da olur)
    )

    if len(potential_text_cols) >= 2:
        mapping['Adi'] = potential_text_cols[0]
        mapping['Soyadi'] = potential_text_cols[1]
    elif len(potential_text_cols) == 1:
        mapping['Adi'] = potential_text_cols[0]
        mapping['Soyadi'] = None

    # 4. Uye No
    filtered_uyeno = {k:v for k,v in scores['UyeNo'].items() if k not in used_cols}
    uye_col = max(filtered_uyeno, key=filtered_uyeno.get, default=None)
    if uye_col is not None and scores['UyeNo'][uye_col] > 0.2:
         mapping['Uye No'] = uye_col
    
    return mapping

def process_file(file, swap_names_flag):
    # Dosya okuma
    df = None
    file_name = file.name.lower()
    try:
        if file_name.endswith('.xlsx'): df = pd.read_excel(file, header=None, engine='openpyxl')
        elif file_name.endswith('.xls'): 
            try: df = pd.read_excel(file, header=None, engine='xlrd')
            except: pass
        if df is None:
            file.seek(0)
            for encoding in ['utf-8', 'cp1254', 'latin1']:
                try: df = pd.read_csv(file, header=None, encoding=encoding, sep=None, engine='python'); break
                except: continue
        if df is None: return None, "Dosya okunamad?."
    except Exception as e: return None, f"Okuma hatas?: {e}"

    # Analiz Ba?lat (Once Ba?l?k Ara, Yoksa ?ceri?e Bak)
    mapping = find_header_row(df)
    
    if mapping is None or 'TC Kimlik No' not in mapping:
        mapping = analyze_columns_content(df)
        
    if 'TC Kimlik No' not in mapping or 'Aidat Tutari' not in mapping:
        return None, "TC Kimlik veya Aidat sutunu tespit edilemedi."

    # Yeni tabloyu olu?tur
    new_df = pd.DataFrame()
    new_df['Sira No'] = range(1, len(df) + 1)
    
    # E?le?meleri ata
    new_df['Uye No'] = df[mapping['Uye No']] if mapping.get('Uye No') is not None else ""
    new_df['TC Kimlik No'] = df[mapping['TC Kimlik No']]
    new_df['Aidat Tutari'] = df[mapping['Aidat Tutari']]

    # AD SOYAD MANTI?I (Swap Kontrolu Burada)
    col_adi = mapping.get('Adi')
    col_soyadi = mapping.get('Soyadi')

    # Kullan?c? yer de?i?tir dediyse ters al
    if swap_names_flag and col_adi is not None and col_soyadi is not None:
        new_df['Adi'] = df[col_soyadi]
        new_df['Soyadi'] = df[col_adi]
    else:
        new_df['Adi'] = df[col_adi] if col_adi is not None else ""
        new_df['Soyadi'] = df[col_soyadi] if col_soyadi is not None else ""

    # Temizlik
    def row_filter(val): return is_tc_potential(val)
    new_df = new_df[new_df['TC Kimlik No'].apply(row_filter)].copy()
    
    new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money_value)
    new_df['TC Kimlik No'] = new_df['TC Kimlik No'].astype(str).str.split('.').str[0]
    new_df['Uye No'] = new_df['Uye No'].astype(str).str.split('.').str[0]
    
    new_df['Sira No'] = range(1, len(new_df) + 1)
    new_df.reset_index(drop=True, inplace=True)
    
    return new_df, None

# --- ARAYUZ ---
if uploaded_file:
    with st.spinner('Analiz yap?l?yor...'):
        # Checkbox durumunu fonksiyona gonderiyoruz
        df_sonuc, error = process_file(uploaded_file, swap_names)
        
        if error:
            st.error(f"Hata: {error}")
        else:
            st.success(f"Analiz Tamamland?! {len(df_sonuc)} ki?i bulundu.")
            
            # Onizleme
            st.write("### Onizleme (?lk 5 Ki?i)")
            st.dataframe(df_sonuc.head())
            
            if swap_names:
                st.info("?? 'Ad' ve 'Soyad' sutunlar? yer de?i?tirildi.")
            
            # ?ndirme Butonu
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_sonuc.to_excel(writer, index=False)
            
            st.download_button(
                label="?? Duzenlenmi? Excel'i ?ndir",
                data=buffer.getvalue(),
                file_name="Duzenlenmis_Liste.xlsx",
                mime="application/vnd.ms-excel"
            )