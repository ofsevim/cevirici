import streamlit as st
import pandas as pd
import io

# Sayfa Ayarlar?
st.set_page_config(page_title="Manuel Sendika Listesi", page_icon="??", layout="wide")

st.title("?? Manuel Sutun Secimi")
st.markdown("""
Otomatik alg?lama hata veriyorsa en iyisi **elle secmektir**.
1. Dosyan?z? yukleyin.
2. A?a??da ac?lan tablodan sutunlar?n harflerine (veya say?lar?na) bak?n.
3. **"TC Kimlik No Hangi Sutunda?"** gibi sorular? cevaplay?n.
""")

uploaded_file = st.file_uploader("Dosyay? Yukleyin", type=["xls", "xlsx", "csv"])

def load_data(file):
    file_name = file.name.lower()
    df = None
    try:
        if file_name.endswith('.xlsx'):
            df = pd.read_excel(file, header=None, engine='openpyxl')
        elif file_name.endswith('.xls'):
            try: df = pd.read_excel(file, header=None, engine='xlrd')
            except: pass
        if df is None: # CSV dene
            file.seek(0)
            for enc in ['utf-8', 'cp1254', 'latin1']:
                try: df = pd.read_csv(file, header=None, encoding=enc, sep=None, engine='python'); break
                except: continue
    except Exception as e: return None, str(e)
    return df, None

def clean_money(val):
    if pd.isna(val): return 0.0
    s = str(val).replace('TL', '').replace(' ', '')
    if ',' in s and '.' in s: s = s.replace('.', '')
    s = s.replace(',', '.')
    try: return float(s)
    except: return 0.0

if uploaded_file:
    df, error = load_data(uploaded_file)
    
    if error:
        st.error(f"Dosya okunamad?: {error}")
    elif df is not None:
        # Onizleme icin sutun isimlerini 0, 1, 2... yerine Kolon 0, Kolon 1 yapal?m
        # Kullan?c?n?n secmesi kolay olsun
        preview_df = df.head(20).copy() # ?lk 20 sat?r? goster
        preview_df.columns = [f"Sutun {i}" for i in range(df.shape[1])]
        
        st.info("A?a??daki tablodan verilerin hangi sutunda oldu?unu inceleyin.")
        st.dataframe(preview_df)

        st.divider()
        st.subheader("?? Sutunlar? E?le?tirin")

        # Secim Kutular?
        col_options = ["Seciniz..."] + list(preview_df.columns)
        
        c1, c2 = st.columns(2)
        with c1:
            col_tc = st.selectbox("TC Kimlik No Hangi Sutunda?", col_options)
            col_aidat = st.selectbox("Aidat Tutar? Hangi Sutunda?", col_options)
            col_uye = st.selectbox("Uye No Hangi Sutunda? (Opsiyonel)", col_options)
        
        with c2:
            isim_tipi = st.radio("?sim Format? Nas?l?", ["Ayr? Sutunlarda (Ad ve Soyad ayr?)", "Birle?ik (Ad? Soyad? tek sutunda)"])
            
            if isim_tipi.startswith("Ayr?"):
                col_ad = st.selectbox("Ad? Hangi Sutunda?", col_options)
                col_soyad = st.selectbox("Soyad? Hangi Sutunda?", col_options)
                col_birlesik = None
            else:
                col_birlesik = st.selectbox("Ad? Soyad? Hangi Sutunda?", col_options)
                col_ad = None
                col_soyad = None

        # ??LE BUTONU
        if st.button("Listeyi Olu?tur ve ?ndir", type="primary"):
            if col_tc == "Seciniz..." or col_aidat == "Seciniz...":
                st.error("Lutfen en az TC Kimlik ve Aidat sutunlar?n? secin.")
            else:
                try:
                    # Secilen 'Sutun X' stringini index numaras?na cevir
                    # "Sutun 5" -> 5
                    idx_tc = int(col_tc.split(' ')[1])
                    idx_aidat = int(col_aidat.split(' ')[1])
                    idx_uye = int(col_uye.split(' ')[1]) if col_uye != "Seciniz..." else None
                    
                    new_df = pd.DataFrame()
                    new_df['TC Kimlik No'] = df.iloc[:, idx_tc]
                    new_df['Aidat Tutari'] = df.iloc[:, idx_aidat]
                    
                    if idx_uye is not None:
                        new_df['Uye No'] = df.iloc[:, idx_uye]
                    else:
                        new_df['Uye No'] = ""

                    # ?simleri al
                    if col_birlesik and col_birlesik != "Seciniz...":
                        idx_birlesik = int(col_birlesik.split(' ')[1])
                        # Birle?ik ismi ay?r
                        full_names = df.iloc[:, idx_birlesik].astype(str)
                        new_df['Adi'] = full_names.apply(lambda x: " ".join(x.split()[:-1]) if len(x.split()) > 1 else x)
                        new_df['Soyadi'] = full_names.apply(lambda x: x.split()[-1] if len(x.split()) > 1 else "")
                    
                    elif col_ad and col_soyad and col_ad != "Seciniz..." and col_soyad != "Seciniz...":
                        idx_ad = int(col_ad.split(' ')[1])
                        idx_soyad = int(col_soyad.split(' ')[1])
                        new_df['Adi'] = df.iloc[:, idx_ad]
                        new_df['Soyadi'] = df.iloc[:, idx_soyad]
                    else:
                        new_df['Adi'] = ""
                        new_df['Soyadi'] = ""

                    # --- TEM?ZL?K VE FORMATLAMA ---
                    
                    # 1. TC Kimlik gecerli olanlar? filtrele (Ba?l?klar? atar)
                    def is_valid_row(val):
                        s = str(val).split('.')[0].strip()
                        return s.isdigit() and len(s) == 11 and s[0] != '0'
                    
                    new_df = new_df[new_df['TC Kimlik No'].apply(is_valid_row)].copy()
                    
                    # 2. Formatla
                    new_df['Aidat Tutari'] = new_df['Aidat Tutari'].apply(clean_money)
                    new_df['TC Kimlik No'] = new_df['TC Kimlik No'].astype(str).str.split('.').str[0]
                    new_df['Uye No'] = new_df['Uye No'].astype(str).str.split('.').str[0]
                    
                    # 3. S?ra No ekle
                    new_df.insert(0, 'Sira No', range(1, len(new_df) + 1))
                    
                    st.success(f"??lem Ba?ar?l?! Toplam {len(new_df)} kay?t bulundu.")
                    st.dataframe(new_df.head())
                    
                    # ?ndirme
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                        new_df.to_excel(writer, index=False)
                        
                    st.download_button("?? Excel ?ndir", buffer.getvalue(), "Manuel_Duzenlenmis_Liste.xlsx", "application/vnd.ms-excel")

                except Exception as e:
                    st.error(f"Bir hata olu?tu: {e}")