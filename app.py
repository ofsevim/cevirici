import streamlit as st
import pandas as pd
import io
import re

# Sayfa Ayarlar?
st.set_page_config(page_title="Ak?ll? Secim Arac?", page_icon="?", layout="wide")

st.title("? Ak?ll? Sutun E?le?tirme")
st.markdown("""
Sistem sutunlar? sizin icin **otomatik secti**.
1. A?a??daki tablodan kontrol edin.
2. Do?ruysa direkt **"Listeyi Olu?tur"** butonuna bas?n.
3. Yanl??sa kutucuktan do?ru sutunu secin.
""")

uploaded_file = st.file_uploader("Dosyan?z? Yukleyin", type=["xls", "xlsx", "csv"])

# --- YARDIMCI FONKS?YONLAR ---
def load_data(file):
    try:
        if file.name.lower().endswith('.xlsx'): df = pd.read_excel(file, header=None, engine='openpyxl')
        elif file.name.lower().endswith('.xls'): 
            try: df = pd.read_excel(file, header=None, engine='xlrd')
            except: pass
        else: # CSV
            file.seek(0)
            for enc in ['utf-8', 'cp1254', 'latin1']:
                try: df = pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'); break
                except: continue
        return df, None
    except Exception as e: return None, str(e)

def analyze_columns(df):
    """Sutunlar?n ne oldu?unu tahmin eder ve index numaras?n? dondurur."""
    # Sadece dolu ve anlaml? sutunlar? al (Bo?luklar? ele)
    valid_cols = []
    for col in df.columns:
        if df[col].notna().sum() > 1: # En az 2 dolu sat?r? olanlar
            valid_cols.append(col)
            
    sample = df[valid_cols].dropna(thresh=2).sample(n=min(50, len(df)), random_state=42).reset_index(drop=True)
    
    scores = {'TC': {}, 'Aidat': {}, 'Text': {}, 'UyeNo': {}}
    
    for col in valid_cols:
        tc=0; money=0; text=0; uyeno=0; total=0
        for val in sample[col]:
            s = str(val).strip()
            if not s: continue
            total += 1
            
            # TC
            clean_s = s.split('.')[0]
            if clean_s.isdigit() and len(clean_s) == 11 and clean_s[0] != '0': tc += 1
            # Uye No
            if clean_s.isdigit() and 3 < len(clean_s) < 8: uyeno += 1
            # Para
            s_money = s.replace('TL', '').replace('.', '').replace(',', '')
            if not clean_s.isdigit() and len(s_money) < 10 and any(c.isdigit() for c in s): money += 1
            # Metin
            if not any(c.isdigit() for c in s) and len(s) > 2: text += 1
        
        if total > 0:
            scores['TC'][col] = tc/total
            scores['Aidat'][col] = money/total
            scores['Text'][col] = text/total
            scores['UyeNo'][col] = uyeno/total

    # En iyileri sec
    suggestions = {}
    used = set()
    
    # TC
    best_tc = max(scores['TC'], key=scores['TC'].get, default=None)
    if best_tc is not None and scores['TC'][best_tc] > 0.3:
        suggestions['TC'] = best_tc
        used.add(best_tc)
    
    # Aidat
    filtered_aidat = {k:v for k,v in scores['Aidat'].items() if k not in used}
    best_aidat = max(filtered_aidat, key=filtered_aidat.get, default=None)
    if best_aidat is not None:
        suggestions['Aidat'] = best_aidat
        used.add(best_aidat)

    # ?simler
    texts = sorted([c for c in scores['Text'] if c not in used and scores['Text'][c] > 0.4])
    if len(texts) >= 2:
        suggestions['Ad'] = texts[0]
        suggestions['Soyad'] = texts[1]
    elif len(texts) == 1:
        suggestions['AdSoyad'] = texts[0]
        
    # Uye No
    filtered_uye = {k:v for k,v in scores['UyeNo'].items() if k not in used}
    best_uye = max(filtered_uye, key=filtered_uye.get, default=None)
    if best_uye is not None and scores['UyeNo'][best_uye] > 0.2:
        suggestions['UyeNo'] = best_uye

    return suggestions, valid_cols

# --- ARAYUZ ---
if uploaded_file:
    df, error = load_data(uploaded_file)
    
    if df is not None:
        # 1. Analiz Yap
        suggestions, valid_cols = analyze_columns(df)
        
        # 2. Sutun ?simlerini Kullan?c? Dostu Yap (Sutun A, Sutun B... veya ornek veri)
        # Sadece dolu sutunlar? listele
        col_map = {} # {GercekIndex: "Gorunen?sim"}
        col_options = ["Seciniz..."]
        
        preview_data = df.iloc[:5, valid_cols].copy() # Sadece gecerli sutunlar?n onizlemesi
        
        # Sutunlara ornek veri iceren isimler verelim: "Sutun 5 (Ahmet)"
        for col in valid_cols:
            first_val = df[col].dropna().astype(str).values
            sample_val = first_val[0] if len(first_val) > 0 else "Bo?"
            if len(sample_val) > 15: sample_val = sample_val[:12] + "..."
            
            label = f"Sutun {col} (Orn: {sample_val})"
            col_map[col] = label
            col_options.append(label)

        # 3. Varsay?lan De?erleri Belirle
        def get_index(key):
            if key in suggestions:
                val = suggestions[key]
                label = col_map.get(val)
                if label in col_options:
                    return col_options.index(label)
            return 0

        # --- SEC?M EKRANI ---
        st.info("? Yapay zeka sutunlar? tahmin etti. Lutfen kontrol edin.")
        
        c1, c2 = st.columns(2)
        with c1:
            sel_tc = st.selectbox("TC Kimlik No", col_options, index=get_index('TC'))
            sel_aidat = st.selectbox("Aidat Tutar?", col_options, index=get_index('Aidat'))
            sel_uye = st.selectbox("Uye No (Varsa)", col_options, index=get_index('UyeNo'))
        
        with c2:
            # ?sim mant??? (Tek mi Cift mi tahminine gore radio butonunu ayarla)
            mode_index = 1 if 'AdSoyad' in suggestions else 0
            isim_mod = st.radio("?sim Yap?s?", ["Ad ve Soyad Ayr? Sutunlarda", "Ad Soyad Birle?ik"], index=mode_index)
            
            if isim_mod == "Ad ve Soyad Ayr? Sutunlarda":
                sel_ad = st.selectbox("Ad?", col_options, index=get_index('Ad'))
                sel_soyad = st.selectbox("Soyad?", col_options, index=get_index('Soyad'))
            else:
                sel_birlesik = st.selectbox("Ad? ve Soyad?", col_options, index=get_index('AdSoyad'))

        st.write("---")
        st.write("### ?? Veri Onizlemesi (Sadece Dolu Sutunlar)")
        st.dataframe(preview_data)

        # --- ??LEM ---
        if st.button("Listeyi Olu?tur ??", type="primary"):
            try:
                # Secimden Index Bulma Fonksiyonu
                def get_real_col(label):
                    if label == "Seciniz...": return None
                    # Label'dan orijinal column indexini bulmam?z laz?m (Ters arama)
                    for k, v in col_map.items():
                        if v == label: return k
                    return None

                col_tc_idx = get_real_col(sel_tc)
                col_aidat_idx = get_real_col(sel_aidat)
                
                if col_tc_idx is None or col_aidat_idx is None:
                    st.error("TC ve Aidat alanlar? zorunludur!")
                else:
                    new_df = pd.DataFrame()
                    new_df['Sira No'] = range(1, len(df)+1)
                    
                    # Uye No
                    u_idx = get_real_col(sel_uye)
                    new_df['Uye No'] = df[u_idx] if u_idx is not None else ""
                    
                    # ?simler
                    if isim_mod.startswith("Ad ve Soyad Ayr?"):
                        ad_idx = get_real_col(sel_ad)
                        soyad_idx = get_real_col(sel_soyad)
                        new_df['Adi'] = df[ad_idx] if ad_idx is not None else ""
                        new_df['Soyadi'] = df[soyad_idx] if soyad_idx is not None else ""
                    else:
                        b_idx = get_real_col(sel_birlesik)
                        if b_idx is not None:
                            full = df[b_idx].astype(str)
                            new_df['Adi'] = full.apply(lambda x: " ".join(x.split()[:-1]) if len(x.split())>1 else x)
                            new_df['Soyadi'] = full.apply(lambda x: x.split()[-1] if len(x.split())>1 else "")
                        else:
                            new_df['Adi'] = ""; new_df['Soyadi'] = ""

                    new_df['TC Kimlik No'] = df[col_tc_idx]
                    new_df['Aidat Tutari'] = df[col_aidat_idx]
                    
                    # Temizlik
                    def clean_tc(val):
                        s = str(val).split('.')[0].strip()
                        return s if (s.isdigit() and len(s)==11 and s[0]!='0') else None
                        
                    def clean_money(val):
                        if pd.isna(val): return 0.0
                        s = str(val).replace('TL','').replace(' ','')
                        if ',' in s and '.' in s: s = s.replace('.','')
                        s = s.replace(',', '.')
                        try: return float(s)
                        except: return 0.0

                    # 1. Gecersiz sat?rlar? at
                    new_df['TC Kimlik No'] = new_df['TC Kimlik No'].apply(clean_tc)
                    new_df = new_df.dropna(subset=['TC Kimlik No'])
                    
                    # 2. Format
                    new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money)
                    
                    if u_idx is not None:
                         new_df['Uye No'] = new_df['Uye No'].astype(str).str.split('.').str[0]
                    
                    # 3. S?ra No Yenile
                    new_df['Sira No'] = range(1, len(new_df)+1)
                    
                    st.success(f"Donu?turme Ba?ar?l?! {len(new_df)} kay?t bulundu.")
                    
                    # ?ndir
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        new_df.to_excel(writer, index=False)
                    st.download_button("?? ?ndir", buffer.getvalue(), "Hazir_Liste.xlsx", "application/vnd.ms-excel")
                    
            except Exception as e:
                st.error(f"Hata: {str(e)}")