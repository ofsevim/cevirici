import streamlit as st
import pandas as pd
import io

# Sayfa Ayarlar?
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="??", layout="wide")

st.title("?? Manuel ve Kesin Cozum")
st.markdown("""
Tahmin yok, hata yok.
1. A?a??daki **Ornek Veri** tablosuna bak?n.
2. Kutucuklardan verilerin oldu?u sutunu secin (?cinde ornek veri yazar).
3. **Listeyi Olu?tur** butonuna bas?n.
""")

uploaded_file = st.file_uploader("Dosyan?z? Yukleyin", type=["xls", "xlsx", "csv"])

# --- DOSYA OKUMA (Hatas?z) ---
def load_data(file):
    try:
        # Once Excel okumay? dene
        if file.name.lower().endswith('.xlsx'):
            return pd.read_excel(file, header=None, engine='openpyxl'), None
        elif file.name.lower().endswith('.xls'):
            try: return pd.read_excel(file, header=None, engine='xlrd'), None
            except: pass
        
        # CSV veya Text okumay? dene
        file.seek(0)
        for enc in ['utf-8', 'cp1254', 'latin1']:
            try: return pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'), None
            except: continue
            
        return None, "Dosya format? desteklenmiyor."
    except Exception as e:
        return None, str(e)

if uploaded_file:
    df, error = load_data(uploaded_file)
    
    if error:
        st.error(f"Dosya okunamad?: {error}")
    elif df is not None:
        
        # --- SUTUN ?S?MLER?N? ORNEK VER?YLE OLU?TUR ---
        # Kullan?c? "Sutun 5"in ne oldu?unu anlamaz, "Sutun 5 (Ahmet)" yazarsa anlar.
        
        col_options = ["Seciniz..."]
        col_mapping = {} # "Gorunen ?sim" -> Gercek Index
        
        # Her sutundan dolu olan ilk veriyi bulup etikete yazal?m
        for col_idx in df.columns:
            # O sutundaki dolu verileri al
            valid_vals = df[col_idx].dropna().astype(str).values
            
            # Ba?l?k sat?rlar?n? (S?ra No, Ad? vb.) atlay?p gercek veriyi bulmaya cal??al?m
            sample_val = "Bo?"
            for val in valid_vals:
                if len(val) > 1 and "S?ra" not in val and "Ad?" not in val:
                    sample_val = val
                    break
            
            # E?er hala "Bo?" veya ba?l?k gibiyse ilk buldu?unu al
            if sample_val == "Bo?" and len(valid_vals) > 0:
                sample_val = valid_vals[0]

            # Etiketi olu?tur
            if len(sample_val) > 20: sample_val = sample_val[:17] + "..."
            label = f"Sutun {col_idx}: {sample_val}"
            
            col_options.append(label)
            col_mapping[label] = col_idx

        # --- ARAYUZ ---
        
        st.info("?? A?a??dan sutunlar? secin. Parantez icindeki verilere dikkat edin.")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("### 1. Zorunlu Alanlar")
            sel_tc = st.selectbox("TC Kimlik No Nerede?", col_options)
            sel_aidat = st.selectbox("Aidat Tutar? Nerede?", col_options)
            
        with c2:
            st.markdown("### 2. ?sim Alanlar?")
            isim_modu = st.radio("?sim Format?", ["Ayr? (Ad ve Soyad ayr? sutun)", "Birle?ik (Ad? Soyad? tek sutun)"])
            
            if isim_modu.startswith("Ayr?"):
                sel_ad = st.selectbox("Ad? Nerede?", col_options)
                sel_soyad = st.selectbox("Soyad? Nerede?", col_options)
                sel_birlesik = "Seciniz..."
            else:
                sel_birlesik = st.selectbox("Ad? Soyad? Nerede?", col_options)
                sel_ad = "Seciniz..."
                sel_soyad = "Seciniz..."
                
        with c3:
            st.markdown("### 3. Di?er (Opsiyonel)")
            sel_uye = st.selectbox("Uye No Nerede?", col_options)

        # ON?ZLEME TABLOSU (Kullan?c? ne secti?ini gorsun diye)
        st.divider()
        st.write("Dosya Onizleme (Referans):")
        st.dataframe(df.head(10))
        
        # --- ??LEME BUTONU ---
        if st.button("L?STEY? OLU?TUR", type="primary"):
            if sel_tc == "Seciniz..." or sel_aidat == "Seciniz...":
                st.error("Lutfen en az TC Kimlik ve Aidat sutunlar?n? secin.")
            else:
                try:
                    new_df = pd.DataFrame()
                    
                    # 1. Verileri Cek
                    new_df['TC Kimlik No'] = df[col_mapping[sel_tc]]
                    new_df['Aidat Tutari'] = df[col_mapping[sel_aidat]]
                    
                    # Uye No
                    if sel_uye != "Seciniz...":
                        new_df['Uye No'] = df[col_mapping[sel_uye]]
                    else:
                        new_df['Uye No'] = ""
                        
                    # ?simler
                    if isim_modu.startswith("Ayr?"):
                        if sel_ad != "Seciniz...": new_df['Adi'] = df[col_mapping[sel_ad]]
                        else: new_df['Adi'] = ""
                        
                        if sel_soyad != "Seciniz...": new_df['Soyadi'] = df[col_mapping[sel_soyad]]
                        else: new_df['Soyadi'] = ""
                    else:
                        # Birle?ik ?sim Ay?rma
                        if sel_birlesik != "Seciniz...":
                            full_names = df[col_mapping[sel_birlesik]].astype(str)
                            new_df['Adi'] = full_names.apply(lambda x: " ".join(x.split()[:-1]) if len(x.split()) > 1 else x)
                            new_df['Soyadi'] = full_names.apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "")
                        else:
                            new_df['Adi'] = ""; new_df['Soyadi'] = ""

                    # 2. TEM?ZL?K (Gereksiz sat?rlar? at)
                    
                    # TC Temizli?i
                    def clean_tc(val):
                        s = str(val).split('.')[0].strip()
                        # Sadece 11 haneli rakamlar? tut
                        if s.isdigit() and len(s) == 11 and s[0] != '0':
                            return s
                        return None
                    
                    new_df['TC Kimlik No'] = new_df['TC Kimlik No'].apply(clean_tc)
                    new_df = new_df.dropna(subset=['TC Kimlik No']) # Bo? olanlar? (ba?l?klar?) at
                    
                    # Para Temizli?i
                    def clean_money(val):
                        if pd.isna(val): return 0.0
                        s = str(val).replace('TL', '').replace(' ', '')
                        if ',' in s and '.' in s: s = s.replace('.', '')
                        s = s.replace(',', '.')
                        try: return float(s)
                        except: return 0.0
                        
                    new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money)
                    
                    # Uye No Temizli?i
                    if sel_uye != "Seciniz...":
                        new_df['Uye No'] = new_df['Uye No'].astype(str).str.split('.').str[0]
                        
                    # S?ra No Ekle
                    new_df.insert(0, 'Sira No', range(1, len(new_df) + 1))
                    
                    # --- SONUC ---
                    st.success(f"Ba?ar?l?! {len(new_df)} kay?t olu?turuldu.")
                    st.dataframe(new_df.head())
                    
                    # ?ndir
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        new_df.to_excel(writer, index=False)
                        
                    st.download_button("?? Excel ?ndir", buffer.getvalue(), "Duzenli_Liste.xlsx", "application/vnd.ms-excel")

                except Exception as e:
                    st.error(f"Hata olu?tu: {str(e)}")