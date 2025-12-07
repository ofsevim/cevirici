import streamlit as st
import pandas as pd
import io

# Sayfa Ayarlar?
st.set_page_config(page_title="Net Liste Duzenleyici", page_icon="????", layout="wide")

st.title("???? Turkce Karakter Dostu Duzenleyici")
st.markdown("""
1. A?a??daki **Ornek Veri** tablosuna bak?n (Turkce karakterler duzelmi? olmal?).
2. Kutucuklardan verilerin oldu?u sutunu secin (**Sadece dolu sutunlar listelenir**).
3. **Listeyi Olu?tur** butonuna bas?n.
""")

uploaded_file = st.file_uploader("Dosyan?z? Yukleyin", type=["xls", "xlsx", "csv"])

# --- DOSYA OKUMA (Turkce Karakter Oncelikli) ---
def load_data(file):
    try:
        file_name = file.name.lower()
        
        # 1. EXCEL (.xlsx / .xls)
        if file_name.endswith('.xlsx'):
            return pd.read_excel(file, header=None, engine='openpyxl'), None
        elif file_name.endswith('.xls'):
            try: return pd.read_excel(file, header=None, engine='xlrd'), None
            except: pass
        
        # 2. CSV (Karakter Sorunu Cozumu)
        # Once 'cp1254' (Windows Turkce) deniyoruz. Genelde devlet daireleri bunu kullan?r.
        file.seek(0)
        encodings_to_try = ['cp1254', 'iso-8859-9', 'utf-8', 'latin1']
        
        for enc in encodings_to_try:
            try:
                file.seek(0)
                # sep=None, python motoruyla ay?r?c?y? (; veya ,) otomatik bulur
                return pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'), None
            except:
                continue
            
        return None, "Dosya format? veya karakter seti desteklenmiyor."
    except Exception as e:
        return None, str(e)

if uploaded_file:
    df, error = load_data(uploaded_file)
    
    if error:
        st.error(f"Dosya okunamad?: {error}")
    elif df is not None:
        
        # --- SUTUN F?LTRELEME (Bo?lar? Gizle) ---
        col_options = ["Seciniz..."]
        col_mapping = {} # "Gorunen ?sim" -> Gercek Index
        
        # Tum sutunlar? gez
        for col_idx in df.columns:
            # Sutundaki verileri al (NaN olanlar? at)
            column_data = df[col_idx].dropna().astype(str)
            
            # E?er sutun tamamen bo?sa veya sadece bo?luklardan olu?uyorsa GOSTERME
            # "nan" stringi pandas okurken bazen string olarak gelebilir, onu da eleyelim
            column_content = column_data[~column_data.isin(['nan', 'NaN', '', ' '])]
            
            if len(column_content) == 0:
                continue # Bu sutun bo?, listeye ekleme
            
            # --- Ornek Veri Bulma (Ba?l?k olmayan gercek bir veri bulal?m) ---
            sample_val = "Veri Yok"
            # ?lk 20 dolu sat?ra bak
            for val in column_content.head(20):
                val_str = str(val).strip()
                # Cok k?sa olmayan ve ba?l?k kelimeleri icermeyen bir ?ey bulmaya cal??
                if len(val_str) > 1 and val_str.lower() not in ["s?ra no", "ad?", "soyad?", "uye no", "tc kimlik"]:
                    sample_val = val_str
                    break
            
            # E?er hala bulamad?ysa ilk dolu veriyi al
            if sample_val == "Veri Yok" and len(column_content) > 0:
                sample_val = column_content.iloc[0]

            # Etiketi olu?tur (Uzunsa k?rp)
            if len(str(sample_val)) > 25: sample_val = str(sample_val)[:22] + "..."
            
            # Excel sutun harfini hesapla (0->A, 1->B, 26->AA gibi) - Gorsellik icin
            # Basitce index kullanal?m, kafa kar??mas?n
            label = f"Sutun {col_idx} ?? {sample_val}"
            
            col_options.append(label)
            col_mapping[label] = col_idx

        # --- ARAYUZ ---
        
        if len(col_options) == 1:
            st.warning("Dosyada dolu sutun bulunamad?!")
        else:
            st.info("?? Sadece veri iceren sutunlar listelenmi?tir.")
            
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("### 1. Zorunlu Alanlar")
                sel_tc = st.selectbox("TC Kimlik No", col_options)
                sel_aidat = st.selectbox("Aidat Tutar?", col_options)
                
            with c2:
                st.markdown("### 2. ?sim Alanlar?")
                isim_modu = st.radio("?sim Format?", ["Ayr? (Ad ve Soyad ayr?)", "Birle?ik (Ad? Soyad? tek)"])
                
                if isim_modu.startswith("Ayr?"):
                    sel_ad = st.selectbox("Ad?", col_options)
                    sel_soyad = st.selectbox("Soyad?", col_options)
                    sel_birlesik = "Seciniz..."
                else:
                    sel_birlesik = st.selectbox("Ad? Soyad? (Tek Sutun)", col_options)
                    sel_ad = "Seciniz..."
                    sel_soyad = "Seciniz..."
                    
            with c3:
                st.markdown("### 3. Opsiyonel")
                sel_uye = st.selectbox("Uye No", col_options)

            # ON?ZLEME TABLOSU
            st.divider()
            st.write("Dosya Onizleme (?lk 10 Sat?r):")
            st.dataframe(df.head(10))
            
            # --- ??LEME ---
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
                            if sel_birlesik != "Seciniz...":
                                full_names = df[col_mapping[sel_birlesik]].astype(str)
                                new_df['Adi'] = full_names.apply(lambda x: " ".join(x.split()[:-1]) if len(x.split()) > 1 else x)
                                new_df['Soyadi'] = full_names.apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "")
                            else:
                                new_df['Adi'] = ""; new_df['Soyadi'] = ""

                        # 2. TEM?ZL?K
                        
                        # TC Temizli?i (Bo?luklar? temizle)
                        def clean_tc(val):
                            s = str(val).split('.')[0].strip()
                            if s.isdigit() and len(s) == 11 and s[0] != '0':
                                return s
                            return None
                        
                        new_df['TC Kimlik No'] = new_df['TC Kimlik No'].apply(clean_tc)
                        new_df = new_df.dropna(subset=['TC Kimlik No'])
                        
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
                            
                        # S?ra No
                        new_df.insert(0, 'Sira No', range(1, len(new_df) + 1))
                        
                        # --- SONUC ---
                        st.success(f"? Ba?ar?l?! {len(new_df)} kay?t bulundu.")
                        st.dataframe(new_df.head())
                        
                        # ?ndir
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            new_df.to_excel(writer, index=False)
                            
                        st.download_button("?? Excel ?ndir", buffer.getvalue(), "Duzenli_Liste.xlsx", "application/vnd.ms-excel")

                    except Exception as e:
                        st.error(f"Hata olu?tu: {str(e)}")