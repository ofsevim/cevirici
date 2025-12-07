import streamlit as st
import pandas as pd
import io
import re

# Sayfa Ayarlar?
st.set_page_config(page_title="Ak?ll? Sendika Listesi", page_icon="??", layout="wide")

st.title("?? Yapay Zeka Destekli Liste Duzenleyici (V3)")
st.markdown("""
Bu arac ?unlar? otomatik yapar:
1. **Sutunlar? Bulur:** S?ras? kar???k olsa bile TC, Aidat, Ad, Soyad'? tan?r.
2. **Birle?ik ?simleri Ay?r?r:** E?er "Ad? Soyad?" tek sutundaysa, onu Ad ve Soyad olarak ikiye boler.
3. **Temizler:** Gereksiz sat?rlar? ve ba?l?klar? atar.
""")

# --- YAN MENU ---
st.sidebar.header("Manuel Mudahale")
swap_names = st.sidebar.checkbox("Ad ve Soyad? Yer De?i?tir", value=False, help="Ad sutununda Soyadlar, Soyad sutununda Adlar varsa i?aretleyin.")

uploaded_file = st.file_uploader("Dosyan?z? buraya b?rak?n", type=["xls", "xlsx", "csv"])

# --- YARDIMCI ANAL?Z FONKS?YONLARI ---

def is_tc_potential(val):
    try:
        s = str(val).split('.')[0].strip()
        # 11 haneli say?, 0 ile ba?lamaz
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
    """Ba?l?k sat?r?n? arar."""
    for i in range(min(25, len(df))):
        row_vals = [str(v).lower() for v in df.iloc[i].values]
        
        mapping = {}
        # Anahtar kelime kontrolu
        for col_idx, val in enumerate(df.iloc[i]):
            val_str = str(val).lower().strip()
            
            if val_str in ['ad?', 'ad', 'isim', 'personel ad?']: mapping['Adi'] = df.columns[col_idx]
            elif val_str in ['soyad?', 'soyad', 'soyisim']: mapping['Soyadi'] = df.columns[col_idx]
            elif val_str in ['ad? soyad?', 'ad soyad', 'isim soyisim', 'ad ve soyad']: mapping['AdSoyad_Birlesik'] = df.columns[col_idx]
            elif 'kimlik' in val_str or 'tc' in val_str: mapping['TC Kimlik No'] = df.columns[col_idx]
            elif 'aidat' in val_str or 'tutar' in val_str: mapping['Aidat Tutari'] = df.columns[col_idx]
            elif 'uye' in val_str and 'no' in val_str: mapping['Uye No'] = df.columns[col_idx]
            
        # E?er kritik alanlar bulunduysa don
        if 'TC Kimlik No' in mapping and ('Adi' in mapping or 'AdSoyad_Birlesik' in mapping):
            return mapping
            
    return None

def analyze_columns_content(df):
    """Ba?l?k yoksa icerik analizi yapar."""
    sample_rows = df.dropna(thresh=2).sample(n=min(50, len(df)), random_state=42).reset_index(drop=True)
    
    scores = {'TC': {}, 'Aidat': {}, 'Text': {}, 'CombinedName': {}, 'UyeNo': {}}
    cols = df.columns
    
    for col in cols:
        tc_hits = 0; money_hits = 0; text_hits = 0; combined_hits = 0; uyeno_hits = 0; valid_count = 0
        
        for val in sample_rows[col]:
            if pd.isna(val) or str(val).strip() == "": continue
            valid_count += 1
            s_val = str(val).strip()
            
            # 1. TC Kontrol
            if is_tc_potential(val): tc_hits += 1
            
            # 2. Uye No (K?sa say?)
            clean_s = s_val.split('.')[0]
            if clean_s.isdigit() and 3 < len(clean_s) < 8: uyeno_hits += 1

            # 3. Para Kontrol
            s_money = s_val.replace('TL', '').replace('.', '').replace(',', '')
            if not is_tc_potential(val) and len(s_money) < 10 and any(c.isdigit() for c in s_val):
                if ',' in s_val or '.' in s_val: money_hits += 1
                
            # 4. Metin Kontrolu (?cinde say? yoksa)
            if not any(char.isdigit() for char in s_val) and len(s_val) > 1:
                text_hits += 1
                # Birle?ik isim kontrolu (?cinde bo?luk var m?? "Ali Y?lmaz")
                if ' ' in s_val.strip():
                    combined_hits += 1

        if valid_count > 0:
            scores['TC'][col] = tc_hits / valid_count
            scores['Aidat'][col] = money_hits / valid_count
            scores['Text'][col] = text_hits / valid_count
            scores['CombinedName'][col] = combined_hits / valid_count
            scores['UyeNo'][col] = uyeno_hits / valid_count

    # --- EN ?Y? SUTUNLARI SEC ---
    mapping = {}
    used_cols = set()

    # TC Kimlik
    tc_col = max(scores['TC'], key=scores['TC'].get, default=None)
    if tc_col is not None and scores['TC'][tc_col] > 0.3:
        mapping['TC Kimlik No'] = tc_col
        used_cols.add(tc_col)
    
    # Aidat
    filtered_aidat = {k:v for k,v in scores['Aidat'].items() if k not in used_cols}
    aidat_col = max(filtered_aidat, key=filtered_aidat.get, default=None)
    if aidat_col is not None:
        mapping['Aidat Tutari'] = aidat_col
        used_cols.add(aidat_col)

    # ?sim Sutunlar? Karar?: Ayr? m? Birle?ik mi?
    potential_text_cols = sorted(
        [c for c in scores['Text'] if c not in used_cols and scores['Text'][c] > 0.4],
        key=lambda x: scores['Text'][x], reverse=True
    )
    
    # Birle?ik ?sim Aday? (En yuksek puanl? ve icinde bo?luk olan)
    combined_candidate = max(scores['CombinedName'], key=scores['CombinedName'].get, default=None)
    combined_score = scores['CombinedName'][combined_candidate] if combined_candidate else 0

    if combined_score > 0.5 and combined_candidate not in used_cols:
        # Tek sutun "Ad? Soyad?" gibi duruyor
        mapping['AdSoyad_Birlesik'] = combined_candidate
    elif len(potential_text_cols) >= 2:
        # ?ki ayr? metin sutunu var
        potential_text_cols.sort() # Sola Ad, Sa?a Soyad gelsin
        mapping['Adi'] = potential_text_cols[0]
        mapping['Soyadi'] = potential_text_cols[1]
    elif len(potential_text_cols) == 1:
        # Sadece tek metin buldu, muhtemelen ad soyad birle?ik ama bo?luksuz yaz?lmam??
        mapping['AdSoyad_Birlesik'] = potential_text_cols[0]

    # Uye No
    filtered_uyeno = {k:v for k,v in scores['UyeNo'].items() if k not in used_cols}
    uye_col = max(filtered_uyeno, key=filtered_uyeno.get, default=None)
    if uye_col is not None and scores['UyeNo'][uye_col] > 0.2:
         mapping['Uye No'] = uye_col
    
    return mapping

def process_file(file, swap_names_flag):
    # Dosya Okuma
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

    # ANAL?Z ET
    mapping = find_header_row(df)
    if mapping is None or 'TC Kimlik No' not in mapping:
        mapping = analyze_columns_content(df)
        
    if 'TC Kimlik No' not in mapping or 'Aidat Tutari' not in mapping:
        return None, "TC Kimlik veya Aidat sutunu tespit edilemedi. Dosya bo? veya hatal? olabilir."

    # TABLOYU OLU?TUR
    new_df = pd.DataFrame()
    new_df['Sira No'] = range(1, len(df) + 1)
    
    new_df['Uye No'] = df[mapping['Uye No']] if mapping.get('Uye No') is not None else ""
    new_df['TC Kimlik No'] = df[mapping['TC Kimlik No']]
    new_df['Aidat Tutari'] = df[mapping['Aidat Tutari']]

    # --- ?S?M AYRI?TIRMA MANTI?I ---
    if 'AdSoyad_Birlesik' in mapping:
        # Tek sutunu parcala
        full_names = df[mapping['AdSoyad_Birlesik']].astype(str)
        new_df['Adi'] = full_names.apply(lambda x: " ".join(x.split()[:-1]) if len(x.split()) > 1 else x)
        new_df['Soyadi'] = full_names.apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "")
    else:
        # Ayr? sutunlar
        col_adi = mapping.get('Adi')
        col_soyadi = mapping.get('Soyadi')

        if swap_names_flag and col_adi and col_soyadi:
            new_df['Adi'] = df[col_soyadi]
            new_df['Soyadi'] = df[col_adi]
        else:
            new_df['Adi'] = df[col_adi] if col_adi else ""
            new_df['Soyadi'] = df[col_soyadi] if col_soyadi else ""

    # F?LTRELEME & TEM?ZL?K
    def row_filter(val): return is_tc_potential(val)
    new_df = new_df[new_df['TC Kimlik No'].apply(row_filter)].copy()
    
    new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money_value)
    new_df['TC Kimlik No'] = new_df['TC Kimlik No'].astype(str).str.split('.').str[0]
    new_df['Uye No'] = new_df['Uye No'].astype(str).str.split('.').str[0]
    
    # S?ra No guncelle
    new_df['Sira No'] = range(1, len(new_df) + 1)
    new_df.reset_index(drop=True, inplace=True)
    
    return new_df, None

# --- ARAYUZ ---
if uploaded_file:
    with st.spinner('Yapay zeka analiz ediyor...'):
        df_sonuc, error = process_file(uploaded_file, swap_names)
        
        if error:
            st.error(f"Hata: {error}")
        else:
            st.success(f"Analiz Tamamland?! {len(df_sonuc)} ki?i listelendi.")
            
            # Onizleme
            st.write("### Sonuc Onizleme")
            st.dataframe(df_sonuc.head())
            
            if swap_names: st.info("?? 'Ad' ve 'Soyad' yer de?i?tirildi.")
            
            # ?ndirme
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_sonuc.to_excel(writer, index=False)
            
            st.download_button("?? Excel Olarak ?ndir", buffer.getvalue(), "Duzenlenmis_Liste.xlsx", "application/vnd.ms-excel")